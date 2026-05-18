"""
Prepare AI reconstruction handoff bundles (ReconViaGen, SAM 3D, Hunyuan3D, TRELLIS).

The skill cannot run these models in-sandbox. This script prepares the inputs
the user needs on their GPU machine and emits a directory plus a RUN.md plus a
manifest.json. The user runs the recon and drops the result back into chat.
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


MODEL_PROFILES = {
    "reconviagen-v0.2": {
        "input_kind": "multi_view_photos",
        "default_n_views": 16,
        "input_resolution": 512,
        "vram_gb": "18 (no refine) / 24 (refine)",
        "expected_output": "mesh.glb (+ optional splat.ply)",
        "run_template": "reconviagen_RUN.md.template",
    },
    "sam3d-objects": {
        "input_kind": "single_image_with_mask",
        "default_n_views": 1,
        "input_resolution": 1024,
        "vram_gb": "16–32",
        "expected_output": "mesh.glb",
        "run_template": "sam3d_objects_RUN.md.template",
    },
    "sam3d-body": {
        "input_kind": "single_image",
        "default_n_views": 1,
        "input_resolution": 1024,
        "vram_gb": "16",
        "expected_output": "body.glb (converted from MHR)",
        "run_template": "sam3d_body_RUN.md.template",
    },
    "hunyuan3d-2.0": {
        "input_kind": "single_image",
        "default_n_views": 1,
        "input_resolution": 1024,
        "vram_gb": "24",
        "expected_output": "mesh.glb",
        "run_template": None,
    },
    "trellis": {
        "input_kind": "single_image",
        "default_n_views": 1,
        "input_resolution": 1024,
        "vram_gb": "16",
        "expected_output": "mesh.glb (or splat)",
        "run_template": None,
    },
}


def prepare_recon_job(
    inputs,
    out_dir: str,
    model: str = "reconviagen-v0.2",
    num_views: int = None,
    target_resolution: int = None,
    job_id: str = None,
):
    """Prepare an AI reconstruction handoff bundle.

    Args:
        inputs: either a list of image paths, a single video path, or a glob.
        out_dir: where to write the bundle (typically under /mnt/user-data/outputs/).
        model: one of MODEL_PROFILES keys.
        num_views: override default. For video, frames to extract.
        target_resolution: resize edge length (square crop). Default per model.
    """
    if model not in MODEL_PROFILES:
        raise ValueError(f"unknown model: {model}; valid: {list(MODEL_PROFILES)}")
    profile = MODEL_PROFILES[model]
    n = num_views or profile["default_n_views"]
    res = target_resolution or profile["input_resolution"]
    jid = job_id or f"{model.replace('-', '_').replace('.', '_')}_{int(time.time())}"

    out_dir = os.path.abspath(out_dir)
    inputs_dir = os.path.join(out_dir, "inputs")
    masks_dir = os.path.join(out_dir, "masks")
    os.makedirs(inputs_dir, exist_ok=True)
    if profile["input_kind"] == "single_image_with_mask":
        os.makedirs(masks_dir, exist_ok=True)

    # Resolve inputs
    if isinstance(inputs, str):
        if inputs.lower().endswith((".mp4", ".mov", ".webm", ".mkv", ".avi")):
            paths = _extract_frames_from_video(inputs, inputs_dir, n, res)
        else:
            paths = sorted(_glob(inputs))
            _normalize_images(paths, inputs_dir, res)
            paths = sorted([os.path.join(inputs_dir, p) for p in os.listdir(inputs_dir)])
    elif isinstance(inputs, list):
        _normalize_images(inputs, inputs_dir, res)
        paths = sorted([os.path.join(inputs_dir, p) for p in os.listdir(inputs_dir)])
    else:
        raise TypeError("inputs must be str path/glob or list of paths")

    # Manifest
    manifest = {
        "$schema":   "cad-studio/recon-handoff/v1",
        "created":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model":     model,
        "job_id":    jid,
        "vram_gb":   profile["vram_gb"],
        "inputs": {
            "kind":       profile["input_kind"],
            "count":      len(paths),
            "resolution": res,
            "files":      [os.path.relpath(p, out_dir) for p in paths],
        },
        "expected_outputs": {
            "primary":  profile["expected_output"],
        },
        "resume_with": {
            "instruction": (
                f"Run the recon on your GPU per RUN.md. When done, upload the "
                f"resulting mesh file back into the chat."
            ),
        },
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # RUN.md from template, if a template exists
    skill_root = Path(__file__).parent.parent
    template_path = skill_root / "handoffs" / (profile["run_template"] or "")
    if profile["run_template"] and template_path.exists():
        run_md = template_path.read_text()
        # Variable substitution
        run_md = run_md.replace("{{JOB_ID}}", jid)
        run_md = run_md.replace("{{N_VIEWS}}", str(n))
        run_md = run_md.replace("{{RESOLUTION}}", str(res))
        (Path(out_dir) / "RUN.md").write_text(run_md)
    else:
        # Generic fallback
        (Path(out_dir) / "RUN.md").write_text(_generic_run_md(model, jid, profile))

    # WHEN_DONE.md
    (Path(out_dir) / "WHEN_DONE.md").write_text(_when_done_md(jid, profile))

    return {
        "out_dir":   out_dir,
        "manifest":  os.path.join(out_dir, "manifest.json"),
        "inputs":    paths,
        "model":     model,
        "job_id":    jid,
    }


def _extract_frames_from_video(video_path: str, out_dir: str, n: int, res: int):
    """Extract n evenly-spaced frames from video, square-crop to res×res."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    times = [duration * (i + 0.5) / n for i in range(n)]
    paths = []
    for i, t in enumerate(times):
        out = os.path.join(out_dir, f"{i:02d}.png")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{t:.3f}", "-i", video_path,
            "-frames:v", "1",
            "-vf", f"scale='if(gt(a,1),-2,{res})':'if(gt(a,1),{res},-2)',"
                   f"crop={res}:{res}",
            out,
        ], check=True)
        paths.append(out)
    return paths


def _glob(pattern: str):
    import glob
    return glob.glob(pattern)


def _normalize_images(in_paths, out_dir: str, res: int):
    """Resize and square-crop input images to res×res, save as PNG in out_dir."""
    from PIL import Image
    for i, p in enumerate(in_paths):
        img = Image.open(p).convert("RGB")
        w, h = img.size
        s = min(w, h)
        img = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
        img = img.resize((res, res), Image.LANCZOS)
        img.save(os.path.join(out_dir, f"{i:02d}.png"))


def _generic_run_md(model: str, job_id: str, profile: dict) -> str:
    return f"""# {model} — Job {job_id}

## What this is
A bundle of inputs prepared by **cad-studio** for you to run on a GPU machine.
This sandbox cannot run the model directly — VRAM requirement is **{profile['vram_gb']} GB**.

## What you need
- A machine with an NVIDIA GPU meeting the VRAM requirement
- The model installed per its official README:
  - `{model}` → check the repo's INSTALL.md / setup script

## What's in this bundle
- `inputs/` — preprocessed images at resolution {profile['input_resolution']}
- `manifest.json` — machine-readable job spec
- `WHEN_DONE.md` — how to send the result back

## How to run
The exact commands depend on the model. Consult the model's official repo for the
inference script invocation. The inputs in `inputs/` are already pre-cropped and
sized to what the model expects.

Common output formats: GLB (mesh + texture), PLY (geometry or Gaussian splat),
OBJ + MTL + textures.

## Output to bring back
The primary expected output is: **{profile['expected_output']}**

Upload it back into the chat and cad-studio will resume.
"""


def _when_done_md(job_id: str, profile: dict) -> str:
    return f"""# When the recon finishes

Upload **{profile['expected_output'].split(' ')[0]}** back into the chat with
a message like:

> Here's the result for job `{job_id}`.

cad-studio will:
- Validate the mesh (watertight check, bbox, vertex count)
- Auto-align coordinate system (Y-up → Z-up if needed) and rescale if you give a reference dimension
- Drop it into your assembly schema as a component, OR animate/render it standalone
- Continue with exploded view, voice-over, or whatever the next step is
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", help="image glob, comma list, or video path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="reconviagen-v0.2", choices=list(MODEL_PROFILES))
    ap.add_argument("--num-views", type=int, default=None)
    ap.add_argument("--resolution", type=int, default=None)
    ap.add_argument("--job-id", default=None)
    args = ap.parse_args()

    inputs = args.inputs
    if "," in inputs:
        inputs = inputs.split(",")
    res = prepare_recon_job(
        inputs, args.out,
        model=args.model,
        num_views=args.num_views,
        target_resolution=args.resolution,
        job_id=args.job_id,
    )
    print(json.dumps(res, indent=2))
