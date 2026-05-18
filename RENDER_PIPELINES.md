# Hunyuan3D and low-VRAM recommendations

This skill can incorporate AI-generated 3D assets, but deterministic CAD remains the default for engineered parts.

## Decision gate

Use Hunyuan3D-style generation when:

- The object is organic, decorative, game-like, or concept-level.
- The user supplies an image and wants a mesh preview.
- Exact dimensions and tolerances are not the core requirement.
- The result can be inspected, decimated, retopologized, or replaced.

Do not use it as the primary path when:

- The part must fit, mate, seal, clamp, fasten, or manufacture accurately.
- The user asks for parametric editability.
- Hole centers, threads, tolerances, or wall thickness matter.

## 12 GB VRAM and under

Use these options first:

1. **CAD-only pipeline**: build123d/OpenSCAD + browser/sandbox render. No large AI model required.
2. **Shape-only AI generation**: generate mesh shape, skip local texture generation.
3. **Lower-memory variants**: mini/turbo or reduced-resolution models when available.
4. **Cloud/remote texture pass**: do texture/PBR on a remote GPU, then return GLB/OBJ.
5. **Browser render**: render the finished mesh locally with WebGL/WebGPU at reduced quality.

Avoid trying to run a texture workflow that exceeds available VRAM. Separate shape and texture.

## Practical quality ladder

| Hardware | Suggested path |
|---|---|
| CPU-only / integrated GPU | build123d/OpenSCAD + software preview or browser low quality. |
| 6–8 GB VRAM | Hunyuan3D 2.0/2mini-style shape generation if current tools support it; texture remotely or use simple materials. |
| 10–12 GB VRAM | Shape generation may be possible for newer open models; keep texture resolution low or remote. |
| 16 GB VRAM | Older shape+texture workflows may fit; still use low-vram modes. |
| 24 GB+ VRAM | Production texture workflows become more realistic. |

## Mesh cleanup after AI generation

Run:

- Scale normalization.
- Mesh report.
- Decimation if too heavy for video.
- Watertight repair only if printing/solid view requires it.
- UV/material inspection.
- Optional retopology if animation/deformation is needed.

## Integration into CAD videos

Generated assets should enter the plan as `model.kind = "mesh"` or as secondary props. Use CAD overlays/callouts to distinguish engineered parts from concept meshes.

## Current-info rule

Before recommending a Hunyuan3D version, check current official sources. Model availability, VRAM requirements, open-source status, and hosted demos change quickly.
