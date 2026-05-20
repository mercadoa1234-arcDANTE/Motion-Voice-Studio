# optional/CAD.md — CAD, Tool Choice, Assembly Schema

Read only when a scene requires 3D parametric modeling or AI mesh reconstruction.

---

## Tool choice (pick one)

| Need | Tool | Notes |
|---|---|---|
| Exact parts: tolerances, threads, STEP export | `build123d` | Confirmed working in sandbox. BREP booleans, parametric. |
| Existing `.scad` files / BOSL2 libraries | `SolidPython2 → OpenSCAD` | CSG-style. No STEP. |
| Organic / decorative / game-like mesh | `Hunyuan3D` handoff | See `optional/BROWSER.md`. GPU required (user machine). |
| Scientific data visualization mesh | `PyVista` | NumPy-native, orbital cameras. |
| Quick preview, no precision required | `trimesh` | Load STL/GLB/OBJ, basic render. |

---

## build123d modeling order

1. Clarify units and coordinate frame.
2. Define named parameters at the top.
3. Model core primitives.
4. Add cuts and interfaces.
5. Fillets/chamfers last.
6. Name components used by animation.
7. Export STEP (CAD editability) + STL/GLB (rendering).
8. Validate: scale, watertightness, face count, bounding box.

```python
from build123d import *

PARAMS = {"width": 80, "depth": 45, "base_thickness": 8,
          "upright_height": 48, "hole_radius": 4.2}

def make_model(params=None):
    p = {**PARAMS, **(params or {})}
    with BuildPart() as part:
        Box(p["width"], p["depth"], p["base_thickness"])
        # ... cuts, fillets ...
    return part

# Export
export_step(make_model(), "bracket.step")
export_stl(make_model(), "bracket.stl")
```

---

## Assembly schema (multi-part deliverables)

```json
{
  "$schema": "cad-studio/assembly/v1",
  "name": "planetary_gearbox_v1",
  "units": "mm",
  "components": [
    { "id": "sun_gear",   "file": "sun_gear.stl",   "color": "#4a9eff" },
    { "id": "planet",     "file": "planet.stl",      "color": "#ff9940" }
  ],
  "shots": [
    { "id": "overview",  "type": "orbital", "duration": 4.0 },
    { "id": "exploded",  "type": "explode", "axis": "z",    "duration": 3.0 }
  ]
}
```

Component names in `"id"` must match the animation callouts and exploded-view motion parameters.

---

## AI reconstruction handoff (GPU required on user machine)

When the user has an image and wants a 3D mesh (Hunyuan3D, TRELLIS, Wonder3D, etc.):

```
[In sandbox]
  prepare inputs → write manifest.json → bundle into recon_job/
  present_files(recon_job/RUN.md)

[User, on their GPU / Colab]
  follow RUN.md
  upload the produced mesh back into chat

[In sandbox, resumed]
  load mesh as trimesh → integrate into assembly schema → render/animate/voice
```

RUN.md template varies by model (Hunyuan3D vs TRELLIS vs Wonder3D). Same handoff pattern.

When to use AI reconstruction:
- Organic, decorative, game-like, concept-level object
- User supplies a reference image
- Exact dimensions and tolerances are not required

When NOT to use:
- Part must fit, mate, seal, fasten, or manufacture accurately
- User asks for parametric editability
- Tolerances, threads, or wall thickness matter → use `build123d`

---

## Pipeline skeletons

### P1 — Single parametric part

```python
from build123d import *
# 1. Model
LEN, WID, THK = 80, 60, 10
with BuildPart() as plate:
    Box(LEN, WID, THK)
    fillet(plate.edges().filter_by(Axis.Z), radius=2)
# 2. Export
export_step(plate, "outputs/plate.step")
export_stl(plate, "outputs/plate.stl")
# 3. Render with pyvista (see core/RENDER.md)
```

### P2 — Multi-part exploded view

```python
# Model each component separately with named exports
# → assembly schema JSON
# → render_cad_v2.py with shots=[{type:"explode"}]
```

### P3 — Mesh-only (no CAD source)

```python
import trimesh
mesh = trimesh.load("uploaded.glb")
# validate: mesh.is_watertight, mesh.bounds
# render via pyvista or browser WebGL kit
```
