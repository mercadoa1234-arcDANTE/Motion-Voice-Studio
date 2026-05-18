# Render pipelines

## Pipeline selection

Choose the highest-quality path that fits the environment and deadline.

```txt
CAD/model source
  ↓
STEP/STL/GLB/OBJ exports
  ↓
mesh report + scale validation
  ↓
audio timing
  ↓
renderer selection
  ├─ PyVista offscreen       → sandbox/local Python video
  ├─ ModernGL local          → custom shader/video capture
  ├─ software fallback       → low-fidelity sandbox preview
  ├─ browser WebGL/WebGPU    → user GPU render kit
  └─ GlowScript/VPython      → browser-native primitive animation
  ↓
ffmpeg mux/check
```

## PyVista path

Use for engineering visualization, mesh plots, sections, scalar overlays, and basic turntables when PyVista/VTK can run offscreen.

Strengths:

- Good mesh loading and camera control.
- Integrates with NumPy/scientific data.
- Can render offscreen in many Linux environments.

Weaknesses:

- Not browser-native.
- Headless rendering may fail without EGL/OSMesa/Xvfb depending on environment.
- Final material quality is limited compared with Blender or custom WebGL/WebGPU shaders.

## ModernGL path

Use when custom shaders matter and local OpenGL is available.

Strengths:

- Fast OpenGL rendering from Python.
- Custom shaders, offscreen framebuffers, effects.

Weaknesses:

- Not browser-native.
- Needs a working OpenGL context.
- Less direct CAD/mesh tooling than PyVista/trimesh.

## Browser WebGL/WebGPU path

Use when the user’s machine can render better than the sandbox. Generate HTML with embedded mesh/camera/audio and a record button.

Strengths:

- Uses user GPU.
- Browser preview is easy to inspect.
- MediaRecorder can produce `.webm` for return.
- Can progressively enhance to Three.js/WebGPU or custom shaders.

Weaknesses:

- MediaRecorder timing may drift slightly.
- Browser codec support varies.
- Full photorealism requires a more sophisticated renderer and material pipeline.

## GlowScript / Web VPython path

Use for conceptual mechanism animations where simple primitives are enough.

Strengths:

- Browser-native.
- Very concise for vectors, rotations, paths, and educational animations.
- Easy for users to modify.

Weaknesses:

- Not ideal for exact imported CAD meshes.
- Lower material/render fidelity than WebGL/WebGPU/Three.js custom pipelines.

## Software fallback path

Use only as a draft/preview when no GPU path is available. It uses triangulated mesh projection and flat shading.

Strengths:

- Works in constrained sandboxes.
- Good enough to check camera framing, narration pacing, and basic shape.

Weaknesses:

- Not production quality.
- Limited materials, no true shadows/reflections.
- Cannot verify final motion quality.

## Camera rules

- Start with a three-quarter view unless the user specifies otherwise.
- Avoid extreme perspective for technical geometry.
- Keep important holes, interfaces, and contact surfaces readable.
- Use section cuts and exploded views instead of hiding geometry.
- Labels should stay outside the part silhouette when possible.

## Motion rules

- Use slow orbit for overview.
- Use deliberate pause on critical features.
- Use exploded motion only after the viewer has seen the assembled object.
- Use ghosted previous/next state for moving mechanisms.
- Avoid fast camera moves during dense narration.

## Render QA

Before final delivery, capture at least one still frame or thumbnail and inspect:

- Is the geometry centered and scaled?
- Are all features visible?
- Are labels readable?
- Does the camera clip the part?
- Does the scene have enough contrast?
- Does video duration match audio timing?
