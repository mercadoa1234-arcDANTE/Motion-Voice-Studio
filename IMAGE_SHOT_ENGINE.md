# Compositing — overlay manim, motion graphics, and callouts onto CAD scenes

Motion-studio composites in two layers: a **base** (almost always a pyvista CAD
render) and one or more **overlays** (manim transparent scenes, matplotlib
PNGs, or hand-drawn PIL graphics). The overlays make CAD shots teach.

## Three composite paths, from light to heavy

| Path | Use | Install cost | Speed |
|---|---|---|---|
| 1. **matplotlib mathtext + PIL** | Static equations, simple text, lower-thirds | 0 (already installed) | ~50 ms / frame |
| 2. **ffmpeg overlay filter** | Pre-rendered overlay sequences (manim or matplotlib animation) | 0 | Bulk per-shot, fast |
| 3. **manim transparent scenes** | Animated math, transforming equations, abstract motion graphics | ~50 MB pip + 1 GB LaTeX for MathTex | Variable; full manim render time |

The three are not mutually exclusive — most teaching shots use Path 1 for a
static reveal at the top of the screen and Path 3 only for the one scene where
math actually animates.

## Path 1 — matplotlib mathtext as PIL overlay

The lightest and fastest. Use when the overlay is static or only changes
per-shot (not per-frame).

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

def render_math_overlay(latex: str, out_path: str, width: int = 600):
    """Render a LaTeX equation to a transparent PNG via matplotlib mathtext.
    Note: matplotlib's mathtext is a LaTeX subset; no \\frac, but supports most
    operators, fractions via \\dfrac, subscripts/superscripts, Greek, etc."""
    fig = plt.figure(figsize=(width / 200, 1.5), dpi=200)
    fig.text(0.5, 0.5, latex, ha="center", va="center",
             fontsize=24, color="white",
             bbox=dict(facecolor="#0e1116", alpha=0.7, boxstyle="round,pad=0.5",
                       edgecolor="none"))
    fig.patch.set_alpha(0)
    fig.savefig(out_path, transparent=True, dpi=200, bbox_inches="tight",
                pad_inches=0.05)
    plt.close(fig)

# Compose onto a CAD frame
def composite_pil(base_png: str, overlay_png: str, out: str,
                  position=("right", "top"), margin: int = 40):
    base = Image.open(base_png).convert("RGBA")
    overlay = Image.open(overlay_png).convert("RGBA")
    bw, bh = base.size
    ow, oh = overlay.size
    x = margin if position[0] == "left" else (bw - ow - margin)
    y = margin if position[1] == "top" else (bh - oh - margin)
    base.alpha_composite(overlay, (x, y))
    base.convert("RGB").save(out)
```

## Path 2 — ffmpeg overlay filter (per-shot)

The right choice when you have both a CAD shot and an animated overlay rendered
as parallel PNG sequences. ffmpeg does the per-frame composite during the
final shot encode.

```bash
ffmpeg -y \
  -framerate 30 -i shots/explain_ratio/cad_%04d.png \
  -framerate 30 -i overlays/explain_ratio/eqn_%04d.png \
  -filter_complex "[0:v][1:v]overlay=format=auto:x=W-w-40:y=40:enable='between(t,0.5,5.5)'" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 explain_ratio.mp4
```

The `enable='between(t,a,b)'` clause makes the overlay appear from t=a to t=b
seconds — useful for "reveal at 0.5s, hide after 5.5s" style of in/out timing.

## Path 3 — manim transparent scenes

When the overlay itself animates — equation writes itself in, terms transform,
brace appears under a sub-expression — manim is the right tool.

### Setup

```bash
pip install --break-system-packages manim
apt-get install -y libpango1.0-dev libcairo2-dev pkg-config
# For MathTex (LaTeX equations rendered correctly), also:
apt-get install -y texlive-latex-extra dvisvgm
# Without LaTeX, you can still use Text() and MarkupText() — most of manim works.
```

### Rendering a transparent scene

```python
# scenes.py — write a Scene subclass
from manim import *

class GearRatio(Scene):
    def construct(self):
        # transparent background; manim's --transparent flag handles this
        eqn = MathTex(r"\omega_{out} = \omega_{in} \cdot \frac{Z_s}{Z_s + Z_r}",
                      color=WHITE).scale(0.8).to_corner(UR)
        self.play(Write(eqn), run_time=1.5)
        self.wait(1.5)
        self.play(Indicate(eqn[0][9:11]))   # highlight Z_s in numerator
        self.wait(1.0)
```

```bash
manim render -ql --transparent --disable_caching --output_file=gear_ratio \
             scenes.py GearRatio
# → media/videos/scenes/480p15/gear_ratio.mov  (qtrle, argb pixel format)
```

For higher quality: `-qm` (720p30) or `-qh` (1080p60). The transparent MOV has
real alpha channel (qtrle / argb).

### Extracting transparent PNG sequence

```bash
ffmpeg -y -i media/videos/scenes/480p15/gear_ratio.mov \
       -pix_fmt rgba -vsync 1 alpha_frames/frame_%04d.png
```

Each PNG has true alpha. Composite as in Path 2.

## Coordinate system for overlay placement

Both paths overlay PNG-on-PNG, so the positioning grammar is screen-space pixels
relative to the base render's resolution. Common positions:

- `top-left`, `top-right`, `bottom-left`, `bottom-right` — corners with margin
- `lower-third` — bottom strip at `y = bh * 0.78`, centered horizontally
- `callout` — anchored to a projected 3D component centroid

For `callout` positioning, the assembly schema's `callout.anchor_xyz` is in
world (assembly) coordinates. Project to screen via pyvista:

```python
def project_to_screen(plotter, xyz_world):
    """Return (x, y) pixel coordinates of a world-space point."""
    import vtk
    renderer = plotter.renderer
    renderer.SetWorldPoint(*xyz_world, 1.0)
    renderer.WorldToDisplay()
    dp = renderer.GetDisplayPoint()
    w, h = plotter.window_size
    return int(dp[0]), int(h - dp[1])  # VTK origin is bottom-left; PIL is top-left
```

Then draw a leader line from `(x, y)` to a label box offset 60 px away.

## Style cohesion

When mixing engines, keep typography consistent. The skill's defaults:

- **Title text**: DejaVu Sans Bold (manim's default, also matplotlib default), 44 pt
- **Subtitle**: DejaVu Sans Regular, 22 pt, color `#9aa3ad`
- **Caption (burned-in)**: DejaVu Sans, 22 pt with black box, bottom-center, margin 40
- **Math equations (mathtext or MathTex)**: serif via LaTeX, color white, 24-28 pt
- **Labels on callouts**: DejaVu Sans Bold 18 pt, label box `#0e1116` with `#7aa9d6` border
- **Brand strip / lower-third**: `#1a1d23` panel, `#7aa9d6` accent line at top edge

These defaults are codified in `scripts/styles.py`.

## When to use which path — decision rule

```
   Is the overlay static for the whole shot?
     ├─ Yes → Path 1 (matplotlib mathtext + PIL)
     └─ No
        ├─ Does the overlay itself animate (write, transform, brace, indicate)?
        │     ├─ Yes → Path 3 (manim transparent)
        │     └─ No (overlay just appears/disappears) → Path 1 with ffmpeg time-gating
        └─ Is the overlay data-driven (chart that updates per frame)?
              ├─ Yes → matplotlib animation → PNG sequence → Path 2 ffmpeg overlay
              └─ No → Path 1
```

## Gotchas

- **Manim's `--transparent` only works for the MOV output**, not MP4. Always
  render to MOV when transparency is needed, then extract PNGs with ffmpeg.
- **MathTex requires LaTeX**. Without it, manim falls back to a generic error.
  Test with `Tex()` (single-line LaTeX) first; if that fails, drop to `Text()`
  which renders via pango.
- **Manim's `font_size` scales relative to the scene height in scene units, not
  pixels.** A `font_size=48` at low quality (854×480) reads larger than at high
  quality (1920×1080).
- **The transparent MOV uses pre-multiplied alpha.** PIL handles this correctly
  via `alpha_composite`. If you switch to ffmpeg `overlay` filter, use
  `overlay=format=auto` not `format=rgb` to preserve premultiplication.
- **Compositing inflates wall-clock time linearly with overlay duration.** Plan
  for 1.5× the CAD-only render time when most shots have overlays.
- **PNG sequences scale terribly past 1000 frames per shot.** Use ffmpeg
  intermediates: encode each shot to an h264 MP4, concat MP4s at the end.

## Worked example

`examples/example_planetary_with_math.py` builds the gearbox, renders an
exploded view, overlays the gear ratio equation during the exploded shot via
Path 1, and adds a manim Path 3 reveal of the reduction formula in the final
"explainer" shot. End-to-end runtime on the sandbox: ~3 minutes for a 25 s 720p
video.
