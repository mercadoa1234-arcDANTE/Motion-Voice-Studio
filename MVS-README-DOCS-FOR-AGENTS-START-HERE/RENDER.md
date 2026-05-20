# core/RENDER.md — Render Engines

Engine selection, Manim action DSL, compositing patterns.

---

## Engine selection (quick ref)

| Scene type | Engine | Avoid |
|---|---|---|
| 3D mechanism, orbit, exploded view | `pyvista` | manim 3D |
| Animated math, equations, bullets | `manim` | matplotlib |
| 3D + math overlay | `composite` | either alone |
| Source page, photo, figure | `image` | rendered text |
| BOM table | `bom` | manim Table |
| Title / section break | `title` | full pyvista |

---

## Manim action DSL

Each scene's `actions` array uses `kind` to dispatch:

### `kind: "title"`
```json
{ "kind": "title", "text": "The Golden Ratio", "subtitle": "φ ≈ 1.6180" }
```
Text display: kern with `engine.kern()`. Default: `kern_scale=0.05, track_em=0.04`.

### `kind: "equation"`
```json
{ "kind": "equation", "latex": "c^2 = a^2 + b^2", "label": "Pythagorean theorem" }
```
Use `MathTex`. Requires: `texlive-extra-utils dvisvgm`.

### `kind: "bullet_list"`
```json
{ "kind": "bullet_list", "items": ["First point", "Second point", "Third point"] }
```
Layout via `engine.layout_block()`. Each item reveals on cue.

### `kind: "axes_plot"`
```json
{ "kind": "axes_plot", "func": "x**2", "x_range": [0, 5], "y_range": [0, 25] }
```

### `kind: "right_triangle"` / `kind: "circle"` / `kind: "polygon"`
Geometry primitives with optional label callouts.

### `kind: "waveform"`
Draws audio waveform from numpy array. Used in audio-explaining scenes.

### `kind: "code_block"`
```json
{ "kind": "code_block", "language": "python", "code": "def hello():\n    pass" }
```

### `kind: "custom"`
```json
{ "kind": "custom", "manim_code": "..." }
```
Raw Manim Python code. Last resort for the ~20% of scenes the DSL doesn't cover.

---

## Common fields (every kind)

- `transition_in`: `"fade"` (default) | `"write"` | `"create"` | `"none"`
- `transition_out`: default `"none"` (next scene's transition_in handles handover)
- `palette`: override default color palette for this scene

---

## Image engine (`engine: "image"`)

For source-paper pages, photographs, figures, slides.

```json
{
  "engine": "image",
  "image_path": "source_pages/fig_3.png",
  "caption": "Figure 3 — Canosa 2024",
  "attribution": "https://arxiv.org/...",
  "ken_burns": true,
  "fade_in": 0.5,
  "fade_out": 0.3
}
```

Letterboxes to 16:9, overlays caption via `engine.place_subtitle()` (visual hint, not subtitle track).

---

## Composite shots (pyvista base + manim overlay)

```python
# Step 1: render pyvista scene with alpha
manim render -ql --transparent --disable_caching MyOverlayScene.py MyOverlayClass

# Step 2: extract RGBA frames
ffmpeg -y -i MyOverlayClass.mov -pix_fmt rgba -vf fps=30 frame_%04d.png

# Step 3: alpha-composite per frame
from PIL import Image
base    = Image.open("cad_frame.png").convert("RGBA")
overlay = Image.open("manim_frame.png").convert("RGBA")
if overlay.size != base.size:
    overlay = overlay.resize(base.size, Image.LANCZOS)
base.alpha_composite(overlay)
result = base.convert("RGB")
```

---

## Text display in render

```python
from engines.text_display import TextDisplayEngine
engine = TextDisplayEngine()

# All title text
title = engine.kern(Text("Chapter 1", font_size=48))
engine.cfg.kern_scale = 0.06  # open for display text

# All annotation labels
labels = [Text(s, font_size=20) for s in bullets]
engine.layout_block(labels, anchor=LEFT * 3 + UP)

# Check before rendering
print(engine.report(labels + [title]))
```

---

## PyVista path

Use for engineering visualization, mesh plots, orbital cameras.

```python
import pyvista as pv
pl = pv.Plotter(off_screen=True, window_size=[1280, 720])
pl.add_mesh(mesh, color="#4a9eff", smooth_shading=True)
pl.camera_position = "iso"
pl.open_movie("cad_scene.mp4", framerate=30)
for angle in range(0, 360, 2):
    pl.camera.azimuth = angle
    pl.write_frame()
pl.close()
```

Fallback if EGL/OSMesa unavailable → browser render kit (see `optional/BROWSER.md`).
