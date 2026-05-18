# CAD modeling rules

## Preferred modeling order

1. Clarify units and coordinate frame.
2. Define named parameters.
3. Model core primitives.
4. Add cuts and interfaces.
5. Add fillets/chamfers last.
6. Name components and features used by animation.
7. Export CAD and mesh formats separately.
8. Validate scale, watertightness, face count, and bounding box.

## build123d primary path

Use build123d for dimensioned CAD. Favor simple, readable scripts over clever one-liners.

Recommended structure:

```python
from build123d import *

PARAMS = {
    "width": 80,
    "depth": 45,
    "base_thickness": 8,
    "upright_height": 48,
    "hole_radius": 4.2,
}

def make_model(params=None):
    p = {**PARAMS, **(params or {})}
    # return a Part/Compound or dict of named components
    ...
```

Rules:

- Keep parameters near the top.
- Use named variables for dimensions used in narration.
- Export STEP for CAD editability and STL/GLB/OBJ for rendering.
- Use separate named parts when the animation needs exploded views.
- Avoid relying on view-specific tricks. Geometry should be valid from all angles.

## Assembly naming

A renderable assembly should have stable names:

```json
"components": ["base", "upright", "gusset", "fastener_left", "fastener_right"]
```

These names feed callouts, exploded motion, material overrides, and browser interactivity.

## SolidPython2 / OpenSCAD bridge

Use SolidPython2 when the user thinks in CSG or supplies `.scad` files.

Recommended structure:

```python
from solid2 import *

PARAMS = {"w": 80, "d": 45, "t": 8}

def make_scad(params=None):
    p = {**PARAMS, **(params or {})}
    return cube([p["w"], p["d"], p["t"]], center=True)
```

Bridge policy:

- Preserve the original `.scad` file.
- Generate an intermediate `.scad` file from SolidPython2 scripts.
- Render STL through OpenSCAD CLI when available.
- If OpenSCAD is unavailable, return the `.scad` and ask the user to render locally.
- Treat OpenSCAD exports as mesh outputs for video; keep the `.scad` for editability.

## Mesh import policy

For `.stl`, `.obj`, `.ply`, `.glb`:

- Run `mesh_report.py`.
- Check bounding box against expected units.
- Check watertightness if printing/manufacturing matters.
- Repair only if requested or obviously needed for render.
- Do not claim mesh repairs preserve engineering intent.

## CAD vs concept-asset boundary

Use deterministic CAD for:

- Brackets, mounts, adapters, panels.
- Assemblies with clear interfaces.
- Parts needing dimensions, holes, threads, clearances, or tolerances.
- Manufacturing visuals.

Use generated/concept meshes for:

- Decorative props.
- Organic parts.
- Background assets.
- Concept ideation.

Generated meshes can be included in videos, but they are not substitutes for parametric CAD when fit and function matter.

## Export expectations

| Format | Purpose | Notes |
|---|---|---|
| STEP | CAD handoff/editing | Preferred for engineered models. |
| STL | 3D printing and mesh rendering | No materials; triangulated. |
| GLB | Browser rendering | Best for materials/scene packaging when available. |
| OBJ | Broad compatibility | Can carry simple material references. |
| SCAD | CSG source | Preserve for OpenSCAD users. |

## Geometry report minimums

The report should include:

- Source path and generated paths.
- Units assumption.
- Vertex/face count.
- Bounding box.
- Surface area and volume if available.
- Watertightness.
- Components detected or declared.
- Warnings about scale or degenerate geometry.
