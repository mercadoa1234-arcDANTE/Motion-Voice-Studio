# Compositing — Golden Ratio Layout Reference

## The philosophy

Good compositing is not about taste; it is about geometry. The golden ratio
φ ≈ 1.6180 gives every pixel position a mathematical justification rooted in
the same self-similar proportion that appears in pentagons, the Fibonacci
sequence, and optimal stopping problems.

Reference: cut-the-knot.org/do_you_know/GoldenRatio.shtml

## GoldenLayout — the one class to use

```python
from scripts.golden_layout import GoldenLayout, PHI

layout = GoldenLayout(1280, 720)
print(layout.focal_point)        # (791, 290) — the eye's natural rest
print(layout.label_anchor(0))    # (799, 290) — first callout label
print(layout.label_anchor(1))    # (799, 429) — second callout label
print(layout.title_height)       # 65 — h/φ⁵
print(layout.font_title)         # 32 — h/36 × φ
```

Never hardcode a pixel. Derive from GoldenLayout.

## Layout derivations

| Property | Formula | Value at 720p |
|---|---|---|
| title_height | h / φ⁵ | 65 px |
| subtitle_height | same as title | 65 px |
| φ_x1 (content edge) | w × (1 − 1/φ) = w × 0.382 | 489 px |
| φ_x2 (label edge) | w × (1/φ) = w × 0.618 | 791 px |
| φ_vy1 (upper focus) | vp_h × 0.382 + title_h | 290 px |
| φ_vy2 (lower focus) | vp_h × 0.618 + title_h | 430 px |
| focal point | (φ_x2, φ_vy1) | (791, 290) |
| label row 0 | panel_y + panel_h × 0.382 | 290 |
| label row 1 | label row 0 + row0 / φ | 429 |
| label row 2 | label row 1 + row0 / φ² | 568 |
| font_title | base × φ (base = h/36) | 32 px |
| font_label | base | 20 px |
| font_small | base / φ | 12 px |
| font_tiny  | base / φ² | 8 px |

## Manim transparent composite — quick reference

### Step 1: render the manim scene with `--transparent`
```bash
manim render -ql --transparent --disable_caching \
             --media_dir /tmp/manim_work \
             scenes.py MySceneClass
# → /tmp/manim_work/videos/.../MySceneClass.mov   (qtrle, argb pixel format)
```

### Step 2: extract to RGBA PNG sequence
```bash
ffmpeg -y -i MySceneClass.mov -pix_fmt rgba -vf fps=24 frame_%04d.png
```

### Step 3: composite in Python (used by compositor.py + render_cad_v2.py)
```python
from PIL import Image
base = Image.open("cad_frame.png").convert("RGBA")
overlay = Image.open("manim_frame.png").convert("RGBA")
if overlay.size != base.size:
    overlay = overlay.resize(base.size, Image.LANCZOS)
base.alpha_composite(overlay)
result = base.convert("RGB")
```

### Step 4: pass to the render pipeline via manim_overlays dict
```python
from render_cad_v2 import render_video
render_video(
    "cad_video.json", "output/final.mp4",
    manim_overlays={
        "overview_rotation": "/path/to/frames/",   # dir of frame_NNNN.png
        "final_rotation":    "/path/to/frames2/",
    }
)
```

## Layout sketch mode — early preview

Before a full render, call:
```bash
python scripts/render_cad_v2.py cad_video.json --sketch
```

This renders ONE φ-grid frame per scene (with the debug overlay showing
the grid lines, focal point, and label row ticks) so you can verify layout
before committing to 3–5 minutes of rendering.

## Callout label rules

1. **Labels go in the right label panel** (x ≥ φ_x2 = 61.8% of width).
   This follows CAD drawing convention and ensures they don't occlude the
   model when it passes through the center of the viewport.

2. **Leader lines go FROM the model surface TO the label box**.
   The label box is in the panel; the anchor dot is where the leader touches
   the model. Never point a leader at the interior centroid of a closed mesh
   (it will always be hidden inside the mesh).

3. **Leader anatomy**: origin dot (5px) → thin line → horizontal tick → label box.
   - Origin dot at the model-surface anchor
   - Thin line from dot to tick point (just left of the label box)
   - 12px horizontal tick into the box
   - Box with dark background and rule border

4. **Three label rows maximum**. More than 3 labels per frame causes visual
   clutter. The φ-row spacing places them at 290/429/568 which maps naturally
   to head/torso/legs of a bipedal figure, or top/mid/bottom of any object.

## Guide line rules (exploded view and assembly sequence)

1. **Show only structurally important parts** (not every bolt). The default
   `important` set contains ~12 key parts.

2. **Anatomy**: halo (4px, dark, for legibility) + core line (2px, gold) +
   arrowhead at displaced tip + origin dot at home position.

3. **Show twice**: once before the mesh, once after. The pre-mesh pass
   (partially occluded) reads as depth; the post-mesh pass (on top) reads
   as annotation.

## Assembly breadcrumb rules

1. One column, right panel, centred vertically on φ_vy1.
2. Completed steps: dark green tint.
3. Active step: bright green highlight.
4. Pending steps: very dark (almost invisible, foreshadowing).
5. Font: `font_small` (12px). Never exceeds the φ_vy1 row as its centre.

## Subtitle bar rules

1. Height = title_height (φ-symmetric with the title bar).
2. Narration wraps to at most 2 lines. Longer text gets truncated at 2 lines —
   write shorter narration or split the scene.
3. Progress bar: width = w × INV_PHI, x_offset = w × INV_PHI2 × 0.5,
   height = max(3, title_height / φ⁴).
4. Background is pure black (0, 0, 0) — maximum contrast for subtitle text
   against any mesh colour.
