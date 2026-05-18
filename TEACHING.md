# Pipelines — copy-paste skeletons for each output class

Each pipeline assumes you've already read SKILL.md and TOOL_CHOICE.md. These are
the working starting points; expand from here.

## P1 — Single parametric part with render

```python
# 1) Model
from build123d import *
LEN, WID, THK = 80, 60, 10
HOLE_R, HOLE_GRID = 3, (60, 40)

with BuildPart() as plate:
    Box(LEN, WID, THK)
    with GridLocations(HOLE_GRID[0], HOLE_GRID[1], 2, 2):
        Hole(radius=HOLE_R, depth=THK)
    fillet(plate.edges().filter_by(Axis.Z), radius=2)

# 2) Export — STEP for engineering, STL for render
export_step(plate.part, "/home/claude/plate.step")
export_stl(plate.part, "/home/claude/plate.stl")
print(f"volume={plate.part.volume:.2f} mm³")

# 3) Render
from scripts.headless import headless_display
import pyvista as pv

with headless_display():
    mesh = pv.read("/home/claude/plate.stl")
    p = pv.Plotter(off_screen=True, window_size=(1280, 720))
    p.add_mesh(mesh, color="#7aa9d6", smooth_shading=True,
               specular=0.4, specular_power=20, ambient=0.2)
    p.add_axes()
    p.camera_position = "iso"
    p.screenshot("/home/claude/plate_render.png")

# 4) Verify (Gate A: STL exists + watertight; Gate B: render exists)
# Then `view` the PNG to confirm visually.
```

## P2 — Multi-part assembly (uses ASSEMBLY_SCHEMA)

```python
# Each component lives in parts/<name>.py with a build() that returns a build123d Part.
# An assembly.json describes poses, materials, explode rules, and shots.
# scripts/assembly.py loads the schema, builds each part, exports STEP+STL+GLB.

from scripts.assembly import build_assembly
asm = build_assembly("/home/claude/cad-studio/examples/planetary_gearbox.json")

# build_assembly:
#  - imports each component's build() function
#  - poses them per the schema
#  - exports parts/*.stl, parts/*.step
#  - exports assembled.glb (with hierarchy + materials)
#  - returns a trimesh.Scene for rendering
```

## P3 — Exploded-view animation

```python
from scripts.exploded_view import render_explode

render_explode(
    schema_path="/home/claude/cad-studio/examples/planetary_gearbox.json",
    out_dir="/home/claude/explode_frames/",
    duration=4.0, fps=30,
    camera="orbit", # or "static" with explicit position
    label_components=True,
)
# Produces frame_0000.png ... frame_0119.png at the rate requested.
# Internally:
#   t in [0..1] interpolates each component along its explode axis by
#   easing(t) * explode_distance_at_full.
#   pyvista renders one frame per t; ffmpeg muxes after.
```

Then:

```bash
ffmpeg -framerate 30 -i /home/claude/explode_frames/frame_%04d.png \
       -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
       /home/claude/explode.mp4
```

## P4 — Voice-over narrated CAD walkthrough

The full pipeline lives in `scripts/storyboard.py`. Schema:

```json
{
  "name": "gearbox_walkthrough",
  "fps": 30,
  "resolution": [1920, 1080],
  "shots": [
    {
      "id": "intro",
      "duration": 4.0,
      "render": {"camera": "orbit", "from_azim": 30, "to_azim": 50},
      "narration": "This is a three-stage planetary gearbox with a 27:1 reduction ratio.",
      "captions": true
    },
    {
      "id": "explode",
      "duration": 6.0,
      "render": {"camera": "orbit", "explode": "0→1"},
      "narration": "As we explode the assembly, you can see the sun gear at the center, surrounded by three planet gears, all meshing with the ring gear.",
      "captions": true
    },
    {
      "id": "callout_sun",
      "duration": 5.0,
      "render": {"camera": "closeup", "target": "sun_gear", "callout": "sun_gear"},
      "narration": "The sun gear is the input. Twenty teeth, module 1.5, 8 millimeter bore.",
      "captions": true
    },
    {
      "id": "bom",
      "duration": 4.0,
      "render": {"kind": "bom"},
      "narration": "Total part count: nine. Total mass: 247 grams.",
      "captions": true
    }
  ]
}
```

`render_storyboard(schema)` produces:

- `frames/shot_<id>_<frame>.png` per shot
- `audio/shot_<id>.mp3` (gTTS)
- `captions.srt` (timed against shot durations)
- `final.mp4` (ffmpeg concat + audio mux + caption burn-in)

## P5 — 2D engineering drawing (orthographic + dimensions)

```python
# scripts/drawing_2d.py renders three orthographic views (front, top, side),
# dimensions them, and writes DXF + a PNG preview.
from scripts.drawing_2d import make_drawing
make_drawing(
    step_path="/home/claude/plate.step",
    out_dxf="/home/claude/plate_drawing.dxf",
    out_pdf="/home/claude/plate_drawing.pdf",
    out_png="/home/claude/plate_drawing.png",
    title_block={"part": "Plate", "rev": "A", "drawn_by": "cad-studio"},
)
```

Internally: build123d's section + project workflow extracts edges, ezdxf writes them
to layers (visible / hidden / center / dimension), matplotlib renders a PNG with the
title block as a fallback if the user doesn't have a DXF viewer.

## P6 — AI reconstruction handoff (ReconViaGen)

```python
# In-sandbox: prepare images + frames + manifest
from scripts.recon_handoff import prepare_recon_job

prepare_recon_job(
    inputs=["/mnt/user-data/uploads/img_*.jpg"],  # or a single video file
    out_dir="/mnt/user-data/outputs/recon_job/",
    model="reconviagen-v0.2",  # or "sam3d-objects", "sam3d-body", "hunyuan3d"
    num_views=16,               # for ReconViaGen
    target_resolution=512,
)
# Produces:
#   recon_job/inputs/00.png ... 15.png
#   recon_job/manifest.json
#   recon_job/RUN.md       (commands the user runs on their GPU)
#   recon_job/WHEN_DONE.md (what to upload back)
```

User runs the recon on their GPU, drops the resulting GLB back into chat. We resume:

```python
import trimesh
mesh = trimesh.load("/mnt/user-data/uploads/recon_result.glb")
# Now it's just a mesh — feed into assembly schema as a component with kind="mesh"
```

## P7 — WebGPU browser-render handoff

```python
from scripts.webgpu_handoff import make_render_page

make_render_page(
    glb_path="/home/claude/assembled.glb",
    out_html="/mnt/user-data/outputs/render_browser.html",
    scene_kind="three_pbr",  # or "webgpu_raymarch", "vpython", "openjscad"
    presets=[
        {"id": "iso_front", "azimuth": 30, "elevation": 20, "fov": 35},
        {"id": "orbit",     "kind": "orbit", "duration_s": 6},
    ],
)
# Produces a single self-contained HTML file the user opens in their browser.
# UI exposes: "Render preset", "Record 6s WebM", "Export PNG sequence".
# User uploads the resulting WebM or PNG zip back.
```

## P8 — Mesh-only deliverable (no parametric work needed)

When the user just hands over an .stl/.obj/.glb and wants exploded view + render +
voice-over:

```python
import trimesh
scene = trimesh.load("/mnt/user-data/uploads/their_model.glb")
# If it's a Scene with geometry per node, we can explode by node.
# If it's a single mesh, segment by connected components first:
if isinstance(scene, trimesh.Trimesh):
    parts = scene.split(only_watertight=False)  # connected components
    scene = trimesh.Scene({f"part_{i}": p for i, p in enumerate(parts)})

# Now compute explode directions from centroids relative to scene centroid:
from scripts.exploded_view import auto_explode_directions
schema = auto_explode_directions(scene, axis="radial")  # or "z", "x", etc.
# schema is the standard assembly schema; feed to render_storyboard.
```

## Gate checklist (paste into your log)

```
[ ] Gate A — Geometry: STEP+STL exist, volume logged, watertight or reason
[ ] Gate B — Render:   at least one PNG exists, viewed
[ ] Gate C — Animation: frame count + first/middle/last frame viewed
[ ] Gate D — Narration: audio file exists, duration matches video ±5%
[ ] Gate E — Bundle:   present_files succeeded with primary first
```
