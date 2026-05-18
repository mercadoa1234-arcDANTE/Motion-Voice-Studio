# Image-Shot Engine — v3

A new render engine added in v3. Renders shots whose visual is a still image (a source-doc page, a photograph, a figure, a slide) with optional caption, attribution, Ken Burns motion, and fade in/out.

## When to use

Use `engine: "image"` for shots where the visual is **a pre-existing image** rather than:
- A 3D CAD scene (use `pyvista`)
- An animated math/motion graphic (use `manim`)
- A composite of CAD + overlay (use `composite`)
- A static title card (use `title`)

Typical cases:
- Showing a page from a source paper
- Showing a Substack post screenshot
- Showing a photograph (the actual Great Pyramid, a galaxy NASA photo, a leaf)
- Showing a static infographic produced outside Motion Studio (e.g., a Mathematica figure)
- "Powerpoint-style" slides authored in any tool that produces PNG/JPG

## Schema

```json
{
  "id": "intro_paper",
  "render": {
    "engine": "image",
    "src": "assets/source_docs/canosa_137/page_001.png",
    "caption": "Canosa 2024 · the source",
    "attribution": "Substack · 101E8E8",
    "ken_burns": {
      "zoom": 1.08,
      "pan": [0.0, -0.05]
    },
    "fade_in_s": 0.4,
    "fade_out_s": 0.4
  },
  "narration": "..."
}
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `src` | string | required | Path to image file (PNG/JPG). Relative to project root. |
| `caption` | string | None | Gold text above the image. Optional. |
| `attribution` | string | None | Gray text below the image. Optional. |
| `ken_burns.zoom` | float | 1.0 | Final zoom factor (1.0 = no zoom, 1.1 = subtle, 1.3 = strong). |
| `ken_burns.pan` | [dx, dy] | [0, 0] | Fractional pan; (0.05, 0) = 5% of width right at end. |
| `fade_in_s` | float | 0.3 | Fade in seconds. |
| `fade_out_s` | float | 0.3 | Fade out seconds. |

## Behavior

- Image is **letterboxed** at the project's resolution (default 1280×720) with the safe-zone ratio at 92%. Original aspect preserved.
- Background fills the letterbox with the studio dark color (`#0d0d1a`).
- Caption appears above the image in gold, attribution below in gray. Both use the same fonts as `title` cards (DejaVu Sans).
- Ken Burns zooms toward the image center (or pans to the specified offset) over the full shot duration.
- Fade in and fade out blend toward the studio background color.

## Examples

### Static page reference (no motion, plain attribution)

```json
{
  "id": "show_paper_title",
  "render": {
    "engine": "image",
    "src": "assets/source_docs/canosa/page_001.png",
    "caption": "Canosa · 2024"
  },
  "narration": "From the paper, page one."
}
```

### Slow zoom on a figure

```json
{
  "id": "show_fig_3",
  "render": {
    "engine": "image",
    "src": "assets/source_docs/canosa/figures/fig-003.png",
    "caption": "Figure 3 · the dimensional ladder",
    "ken_burns": {"zoom": 1.15, "pan": [0, -0.1]}
  },
  "narration": "..."
}
```

### Long Substack post (vertical pan)

```json
{
  "id": "scroll_substack",
  "render": {
    "engine": "image",
    "src": "assets/source_docs/canosa_substack/page_001.png",
    "caption": "Substack · 101E8E8 · April 2024",
    "ken_burns": {"zoom": 1.0, "pan": [0, 0.4]},
    "fade_in_s": 0.6,
    "fade_out_s": 0.6
  },
  "narration": "The post runs four screens long and builds the construction step by step."
}
```

The pan `[0, 0.4]` means: end the shot looking at 40% below the top of the image. With `zoom=1.0`, this reveals lower content as the shot plays. (To pan UPWARD use a negative dy.)

## CLI test

```bash
python scripts/image_shot.py path/to/image.png \
    --out /tmp/test_shot \
    --duration 4.0 \
    --caption "Test caption" \
    --attribution "Test attribution" \
    --zoom 1.1
```

This renders one shot's frames to `/tmp/test_shot/`. View the middle frame to verify.

## Composing image-shot + manim overlay

If you want a figure with manim-style annotations (highlighting circles, arrows pointing at parts of the figure), use `engine: "composite"` with the image as base:

```json
{
  "id": "fig_with_annot",
  "render": {
    "engine": "composite",
    "base": {
      "engine": "image",
      "src": "assets/source_docs/canosa/figures/fig-003.png"
    },
    "overlays": [
      {
        "kind": "manim",
        "action": {"kind": "callout", "tex": "$\\alpha^{-1}$", "from": [0.6, 0.4], "to": [0.5, 0.3]},
        "position": "free"
      }
    ]
  },
  "narration": "..."
}
```

(Note: composite-with-image-base requires `composite` to accept `image` as a base engine. As of v3.0 the composite engine accepts pyvista base only; image-base composite is on the v3.1 roadmap. For v3.0, render the image-shot and the annotation as separate adjacent shots.)
