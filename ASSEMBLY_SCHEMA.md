# AI Reconstruction Handoff

The sandbox is 4 GB CPU-only. None of the image/video-to-3D models can run here.
This document specifies the handoff format and the in-sandbox preparation work.

## The pattern (memorize this)

```
[in sandbox]
  prepare inputs → write manifest → bundle into /mnt/user-data/outputs/recon_job/
  present_files(recon_job/RUN.md)

[user, on their GPU or Colab]
  cd recon_job/
  follow RUN.md
  upload the produced mesh back into chat

[in sandbox, resumed]
  load mesh as trimesh → integrate into assembly schema → render/animate/voice
```

The same pattern serves ReconViaGen, SAM 3D Objects, SAM 3D Body, Hunyuan3D 2.0,
TRELLIS, Wonder3D, and any future model. Only the per-model `RUN.md` template
changes.

## Sources (verified as of Jan 2026)

| Model | Repo | VRAM | Best for | Output |
|---|---|---:|---|---|
| **ReconViaGen v0.2** | github.com/GAP-LAB-CUHK-SZ/ReconViaGen | 18–24 GB | 8–16 multi-view photos of an object | mesh + 3DGS splat |
| **SAM 3D Objects** | github.com/facebookresearch/sam-3d-objects | 16–32 GB | Single photo + mask of an object | OBJ + MTL + textures, or Gaussian splat |
| **SAM 3D Body** | github.com/facebookresearch/sam-3d-body | 16 GB | Single photo of a person | MHR rig (→ FBX/glTF) |
| **SAM 3** | github.com/facebookresearch/sam3 | 8–16 GB | Generating segmentation masks (text or click prompts) | masks, boxes, scores |
| **Hunyuan3D 2.0** | github.com/Tencent/Hunyuan3D-2 | 24 GB | Single image, high-res textured mesh | GLB |
| **TRELLIS** | github.com/microsoft/TRELLIS | 16 GB | Single image, multi-format (mesh, NeRF, GS) | GLB or splat |

The skill's job is **not to track the latest model**; it's to (a) emit clean
inputs at the resolutions each model expects and (b) provide a `RUN.md` the user
can follow without thinking.

## In-sandbox preparation work

### Frames from video

```python
# /home/claude/cad-studio/scripts/recon_handoff.py
import subprocess, json, os, math
from pathlib import Path

def extract_frames(video_path: str, out_dir: str, num_frames: int = 16,
                   resolution: int = 512):
    """Extract num_frames evenly-spaced frames from video, square-cropped and resized."""
    os.makedirs(out_dir, exist_ok=True)
    # Probe duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    times = [duration * (i + 0.5) / num_frames for i in range(num_frames)]
    for i, t in enumerate(times):
        subprocess.run([
            "ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", video_path,
            "-frames:v", "1",
            "-vf", f"scale='if(gt(a,1),-2,{resolution})':'if(gt(a,1),{resolution},-2)',crop={resolution}:{resolution}",
            f"{out_dir}/{i:02d}.png",
        ], check=True, capture_output=True)
    return [f"{out_dir}/{i:02d}.png" for i in range(num_frames)]
```

### Smart frame selection (better than even-spacing)

For longer videos, even-spacing wastes frames on static segments. Smarter:
sample with **inter-frame difference**: keep frames whose RGB difference from the
last kept frame exceeds a threshold. This yields views with maximum mutual
information — exactly what multi-view models need.

```python
import cv2, numpy as np

def select_diverse_frames(video_path, num_target=16):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # First pass: sample 4× target candidates uniformly
    candidates = np.linspace(0, total - 1, num_target * 4, dtype=int)
    frames = []
    for idx in candidates:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, f = cap.read()
        if ok: frames.append((idx, cv2.resize(f, (128, 128))))
    cap.release()
    # Greedy max-min diff selection
    kept = [frames[0]]
    while len(kept) < num_target and len(frames) > len(kept):
        best, best_score = None, -1
        for cand in frames:
            if cand in kept: continue
            score = min(np.mean(np.abs(cand[1].astype(int) - k[1].astype(int))) for k in kept)
            if score > best_score:
                best, best_score = cand, score
        kept.append(best)
    kept.sort(key=lambda x: x[0])
    return [k[0] for k in kept]
```

### Mask generation prep (for SAM 3D Objects)

SAM 3D Objects needs an object mask per image. The user runs SAM 3 (or a manual
brush in Photoshop/Krita) to produce the mask. The skill emits a `masks/`
directory with the same filenames as `inputs/` so the user knows where they go.

## Per-model RUN.md templates

These are in `handoffs/*_RUN.md.template`. The skill copies and fills in the
specific paths and parameters.

### ReconViaGen v0.2 — RUN.md template

```markdown
# ReconViaGen v0.2 — How to run on your GPU machine

## Hardware
- NVIDIA GPU, 18 GB VRAM minimum (24 GB if you want refinement).
- CUDA 12.1.
- 32 GB system RAM recommended.
- Linux preferred; WSL2 works.

## Setup (one-time)

```bash
git clone https://github.com/GAP-LAB-CUHK-SZ/ReconViaGen
cd ReconViaGen
./setup.sh --new-env --basic --xformers --flash-attn --spconv --mipgaussian --kaolin --nvdiffrast --demo
conda activate reconviagen
```

## Run

Place the contents of `inputs/` (this folder, 16 PNGs) into `ReconViaGen/inputs/<my_job>/`,
then:

```bash
# without refinement (~18 GB VRAM, ~3 min on RTX 4090)
python app.py --input_dir inputs/<my_job>/ --output_dir outputs/<my_job>/

# with refinement (~24 GB VRAM, ~6 min on RTX 4090, sharper details)
python app_fine.py --input_dir inputs/<my_job>/ --output_dir outputs/<my_job>/
```

## Output to bring back

Upload `outputs/<my_job>/mesh.glb` to the chat. If you also want the Gaussian splat,
upload `outputs/<my_job>/splat.ply`.
```

### SAM 3D Objects — RUN.md template

```markdown
# SAM 3D Objects — How to run on your GPU machine

## Hardware
- NVIDIA GPU, 16 GB VRAM (24+ GB recommended for batch).

## Setup

```bash
git clone https://github.com/facebookresearch/sam-3d-objects
cd sam-3d-objects
conda create -n sam3d python=3.10
conda activate sam3d
pip install -e .
# Download checkpoint per README
```

## Run (one image + one mask)

```python
import sys; sys.path.append("notebook")
from inference import Inference, load_image, load_single_mask
inf = Inference("checkpoints/hf/pipeline.yaml", compile=False)
img = load_image("inputs/00.png")
mask = load_single_mask("masks/", index=0)
out = inf(img, mask, seed=42)
out["mesh"].export("outputs/mesh.glb")  # GLB with texture
out["gs"].save_ply("outputs/splat.ply")   # Gaussian splat
```

## Output to bring back

Upload `outputs/mesh.glb` to the chat.
```

### SAM 3D Body — RUN.md template

```markdown
# SAM 3D Body — How to run on your GPU machine

## Hardware
- NVIDIA GPU, 16 GB VRAM.

## Setup + Run

```bash
git clone https://github.com/facebookresearch/sam-3d-body
cd sam-3d-body
# Follow INSTALL.md, request HuggingFace checkpoint access.
python demo.py --image inputs/00.png --output outputs/
```

## Output to bring back

Upload `outputs/body.glb` (after MHR-to-glTF conversion using their provided tool).
```

## Manifest JSON

Every handoff bundle includes a `manifest.json` so the skill (on resume) knows
what to expect back.

```json
{
  "$schema": "cad-studio/recon-handoff/v1",
  "created":  "2026-05-11T03:35:00Z",
  "model":    "reconviagen-v0.2",
  "job_id":   "gearbox_cover_recon_001",
  "inputs": {
    "kind": "multi_view_photos",
    "count": 16,
    "resolution": 512,
    "files": ["inputs/00.png", "inputs/01.png", "...", "inputs/15.png"]
  },
  "expected_outputs": {
    "primary": "mesh.glb",
    "optional": ["splat.ply"]
  },
  "resume_with": {
    "instruction": "Upload mesh.glb back into chat; cad-studio will load and integrate it.",
    "downstream": "/scripts/assembly.py expects mesh placed under parts/imported/"
  }
}
```

## When the user returns

```python
import trimesh
# The user uploaded /mnt/user-data/uploads/mesh.glb
mesh = trimesh.load("/mnt/user-data/uploads/mesh.glb")
print(f"loaded: {len(mesh.geometry) if hasattr(mesh, 'geometry') else 1} parts, "
      f"bbox={mesh.bounds}, watertight check...")
# If it's a Scene with multiple geometries, that's the component breakdown — drop
# each into the assembly schema as a separate component with source.kind = "mesh".
```

## Failure modes and recovery

- **User's GPU OOMs.** Suggest the 8-view path instead of 16, or the no-refine
  path instead of with-refine.
- **Mesh is hollow / non-watertight.** Trimesh `fill_holes` first; if that fails,
  use `trimesh.repair.broken_faces` to identify and report the bad faces.
- **Mesh scale is wrong.** Ask the user for a reference dimension; rescale by
  ratio. The skill's `scripts/recon_handoff.py` has a `rescale_to_match(mesh,
  known_dimension_mm)` helper.
- **Texture is missing or baked badly.** Re-export with `mesh.export(file_obj,
  include_texture=True)` and report — the user may need to bring back the .png
  texture map alongside the .glb.
- **Coordinate system mismatch (Y-up vs Z-up).** Auto-detect: if the principal
  axis of the mesh's PCA is closer to Y than Z, rotate −90° about X. Log the
  decision.
