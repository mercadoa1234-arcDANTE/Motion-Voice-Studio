# Assembly Schema

The single source of truth for multi-part assemblies. Every multi-part deliverable
(exploded views, animated walkthroughs, BOM rendering) reads this format.

## Top-level shape

```json
{
  "$schema": "cad-studio/assembly/v1",
  "name": "planetary_gearbox_v1",
  "units": "mm",
  "description": "Single-stage planetary gearbox, 4:1 reduction.",
  "components": [ ... ],
  "constraints": [ ... ],
  "shots": [ ... ],
  "bom": { ... }
}
```

`units` is "mm" by default. All distances in `pose`, `explode`, dimensions, and
camera positions are in these units.

## Component

```json
{
  "id": "sun_gear",
  "label": "Sun gear (20T module 1.5)",

  "source": {
    "kind": "build123d",           // or "openscad", "mesh", "step", "recon"
    "path": "parts/sun_gear.py",
    "fn":   "build",               // callable that returns the part
    "params": { "teeth": 20, "module": 1.5, "bore": 8.0 }
  },

  "pose": {
    "xyz": [0, 0, 0],              // mm, in assembly frame
    "rpy": [0, 0, 0]               // radians (roll, pitch, yaw)
  },

  "material": {
    "color":     [0.65, 0.68, 0.72],   // linear RGB 0..1
    "metallic":  0.92,
    "roughness": 0.28,
    "opacity":   1.0
  },

  "explode": {
    "axis":              [0, 0, 1],     // unit vector in assembly frame
    "distance_at_full":  30,            // mm at t=1
    "order":             0,             // smaller goes first when sequenced
    "easing":            "ease_in_out"  // or "linear", "ease_out"
  },

  "callout": {
    "anchor_xyz": [0, 0, 12],            // tip of the leader, in assembly frame
    "label":      "Sun gear",
    "subtitle":   "20T · m=1.5 · Ø8 bore"
  },

  "bom": {
    "part_number": "SG-20-15-8",
    "qty":         1,
    "material":    "AISI 4140 steel",
    "mass_g":      42
  }
}
```

### `source.kind` options

| kind | meaning |
|---|---|
| `build123d` | Python module + function name. Most common. |
| `openscad`  | A `.scad` file. Either pre-rendered to STL/STEP elsewhere, or rendered in-sandbox if `openscad` binary is installed. |
| `mesh`      | A pre-existing STL/OBJ/PLY/GLB file. No parametric edit possible. |
| `step`      | An imported STEP file. build123d can re-export. |
| `recon`     | A mesh produced by an AI handoff (ReconViaGen, SAM 3D). Treated like `mesh`. |

## Constraints (optional but useful for mate-aware explode)

```json
{
  "kind": "coaxial",
  "from": "sun_gear",
  "to":   "planet_1",
  "axis": [0, 0, 1]
}
```

Supported kinds: `coaxial`, `planar`, `tangent`, `distance`. Constraints are not
required for exploded view to work (each component's `explode` field is
sufficient) but they enable smarter automated explode-axis inference for meshes
that don't have hand-authored explode rules.

## Shots

A shot is a timed segment of the final video. Shots run sequentially.

```json
{
  "id": "explode",
  "duration": 6.0,

  "render": {
    "camera": "orbit",
    "from_azim": 30, "to_azim": 60,
    "elev": 25,
    "explode": "0→1",         // animate explode parameter t from 0 to 1
    "highlight": []           // component ids to brighten
  },

  "narration": "...",
  "captions":  true,
  "overlays":  ["bom_top_right"]   // optional matplotlib-rendered overlay PNGs
}
```

### `render` field

| key | meaning |
|---|---|
| `camera`   | `"orbit"`, `"static"`, `"closeup"`, `"track"`, `"keyframe"` |
| `from_azim`, `to_azim` | orbit start and end azimuth (degrees) |
| `elev`     | constant elevation (degrees) for orbit and closeup |
| `target`   | component id for `closeup` and `track` |
| `keyframes`| list of `{t, position, target, fov}` for `keyframe` cameras |
| `explode`  | `"0→1"`, `"1→0"`, `"hold@0.5"`, or omitted (default 0) |
| `highlight`| list of component ids to render in a brighter color |
| `callout`  | component id whose `callout` field gets a leader+label drawn this shot |
| `kind`     | special shots: `"bom"` (renders BOM table), `"title"` (text title card) |

## BOM

Optional but if present, generates a tabular slide and CSV.

```json
{
  "columns": ["part_number", "label", "qty", "material", "mass_g"],
  "title":   "Bill of Materials",
  "csv_out": "bom.csv"
}
```

## Worked example

`examples/example_planetary_gearbox.json` is a complete, runnable example with five
components, eight shots, and a BOM. Read it before authoring a new assembly.

## Authoring tips

- **One component per file** in `parts/`. Each file exposes a single `build(**params)`
  function returning a `build123d.Part`. This keeps each component testable and
  re-buildable in isolation.
- **Pose is in the assembly frame**, not the part's local frame. Each part is built
  centered at its own origin; `pose.xyz` places it in the assembly.
- **Explode axes default to radial from assembly centroid** when not specified, but
  hand-authored axes look much better — pick the natural disassembly direction.
- **Render times grow linearly with shot duration × fps.** Default to 24 fps for
  drafts, 30 fps for finals. Keep total frame count under ~600 in-sandbox to stay
  under the 5-minute wall-clock budget; if you need more, render in chunks.
- **Always validate the schema** with `scripts/assembly.py --validate <path>` before
  rendering — catches missing component IDs, bad axis vectors, etc.
