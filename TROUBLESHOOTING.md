# `cad_video.json` planning contract

`cad_video.json` is the contract for geometry, voiceover, render, browser assistance, and final QA. Write it before generating code or video.

## Top-level schema

```json
{
  "version": 1,
  "topic": "Exploded view of a bracket assembly",
  "audience": "technical buyer, no CAD experience required",
  "units": "mm",
  "output": {
    "directory": "/mnt/data/outputs",
    "basename": "bracket_explainer"
  },
  "video": {
    "width": 1280,
    "height": 720,
    "fps": 30,
    "background": "#101217",
    "duration_policy": "audio_driven"
  },
  "model": {
    "kind": "build123d",
    "entrypoint": "examples/build123d_bracket.py",
    "function": "make_model",
    "exports": ["step", "stl", "glb"],
    "components": ["base", "upright", "gusset"]
  },
  "voiceover": {
    "engine": "auto",
    "voice_id": "narrator",
    "speed": 1.0,
    "leading_silence_ms": 100,
    "post_scene_gap_ms": 180,
    "tail_silence_ms": 500
  },
  "render": {
    "preferred": "auto",
    "fallbacks": ["pyvista", "software", "browser_webgl"],
    "quality": "preview",
    "materials": {
      "default": {"color": "#b8c7d9", "metalness": 0.05, "roughness": 0.45}
    }
  },
  "scenes": [
    {
      "id": "overview",
      "voice_id": "narrator",
      "narration": "The bracket starts as a flat base plate with an upright face that carries the load.",
      "visual": {
        "kind": "turntable",
        "camera": {"azimuth": 35, "elevation": 25, "distance": 2.8},
        "motion": {"orbit_degrees": 70},
        "callouts": [
          {"label": "base plate", "target": "base"},
          {"label": "upright face", "target": "upright"}
        ]
      }
    }
  ]
}
```

## Required fields

| Field | Purpose |
|---|---|
| `version` | Schema version. Current value: `1`. |
| `topic` | One-sentence video subject. |
| `units` | Required. Use `mm`, `cm`, `m`, `in`, or `ft`. |
| `output.directory` | Where generated artifacts go. |
| `output.basename` | File stem for video, reports, exports. |
| `video.width`, `video.height`, `video.fps` | Render dimensions. |
| `model.kind` | `build123d`, `solidpython2`, `openscad`, `mesh`, `hunyuan3d`, or `browser_primitive`. |
| `model.entrypoint` | Script or asset path. |
| `voiceover.engine` | `auto`, `kokoro`, `espeak-ng`, `say`, `external`, `silent`, or `browser_speech`. |
| `scenes[].id` | Unique slug used in filenames. |
| `scenes[].narration` | Spoken text only. No timing markup. |
| `scenes[].visual` | What the viewer sees while the scene’s narration plays. |

## Timing rules

Do not author:

- `start_time`
- `end_time`
- `duration`
- `wait`

These are written to `outputs/audio/timing.json` after audio generation. Scene timing is real audio duration plus configured gap. If a scene must include a deliberate silent beat, split it into a scene with empty narration and a `visual` action.

## Model kinds

### `build123d`

Use for precise parametric CAD. `entrypoint` should be a Python file with:

```python
def make_model():
    """Return a build123d Part/Compound/Shape or a dict of named parts."""
```

Optional:

```python
PARAMS = {"width": 80, "height": 45, "thickness": 8}
```

### `solidpython2`

Use for Python-generated CSG/OpenSCAD. The script should expose:

```python
def make_scad():
    """Return a solid2 object."""
```

The bridge writes a `.scad` file, then uses OpenSCAD CLI if available.

### `openscad`

Use when the user supplies a `.scad` file. Preserve the original file and render to STL with OpenSCAD if available. If OpenSCAD is unavailable, create an instruction packet for the user.

### `mesh`

Use for existing `.stl`, `.obj`, `.ply`, or `.glb`. Run `mesh_report.py` before rendering. Meshes are fine for video; they are not editable CAD unless a source CAD file also exists.

### `hunyuan3d`

Use for image/text-to-3D assets that are decorative, organic, or concept-level. Do not use for tolerance-critical parts unless the output is explicitly treated as a visual placeholder.

### `browser_primitive`

Use when a Web VPython/GlowScript animation can explain the idea better than importing an exact mesh. Good for mechanisms, forces, vectors, and simple shapes.

## Visual action kinds

| `visual.kind` | Use for | Typical parameters |
|---|---|---|
| `turntable` | Overall product reveal | `camera`, `motion.orbit_degrees`, `callouts` |
| `explode` | Assembly/disassembly | `components`, `distance`, `axis`, `stagger` |
| `section` | Interior or hidden feature | `plane`, `offset`, `highlight_edges` |
| `callout_focus` | Narration tied to one feature | `target`, `label`, `camera` |
| `mechanism` | Moving linkages/gears/slides | `joints`, `drivers`, `cycle_count` |
| `manufacturing_step` | CNC/print/assembly process | `operation`, `toolpath`, `before_after` |
| `dimension` | Explain size/tolerance | `measure`, `start`, `end`, `label` |
| `browser_custom` | HTML/WebGL/GlowScript-specific | `script_name`, `params` |

Renderers may support only a subset. If an action is unsupported, degrade gracefully and note what changed.

## Voiceover rules

- Narration should be 8–50 words per scene.
- One idea per scene.
- Plain text only; no `[pause]` tokens.
- Use punctuation for natural pauses.
- For dialogue, define multiple voices in a `voices` array and reference by `voice_id`.
- Avoid extremely long scenes; they are hard to align with visual detail.

## Render quality levels

| Quality | Resolution/frame policy | Use |
|---|---|---|
| `draft` | 720p or lower, simple material, no AA | Fast internal review. |
| `preview` | 720p/1080p, basic shadows, readable labels | User-facing proof. |
| `final` | 1080p/4K, higher samples, material tuning | Deliverable. |
| `browser_high` | User GPU, WebGL/WebGPU, MediaRecorder or frame capture | When sandbox is limited. |

## Authoring checklist

- [ ] Units declared.
- [ ] Output directory and basename declared.
- [ ] Model source kind selected.
- [ ] Requested exports match user needs.
- [ ] Scene narrations are final enough to synthesize.
- [ ] Each scene maps to one visual action.
- [ ] Render path has a fallback.
- [ ] Browser-assist plan exists if sandbox GPU is inadequate.
