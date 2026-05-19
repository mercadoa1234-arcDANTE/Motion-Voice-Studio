"""
Render manim scenes to transparent PNG sequences for compositing.

Two modes:

1. **High-level**: render a built-in scene from `scripts/manim_scenes.py` by
   name with parameters. Covers ~80% of teaching overlays without writing
   Python (just the storyboard JSON).

2. **Custom**: render an arbitrary `.py` file with a named `Scene` subclass.
   For the 20% of cases the high-level DSL doesn't cover.

Output is always a directory of `frame_NNNN.png` files at the requested fps,
with true alpha channel. Caller composites them onto CAD frames.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


CACHE_DIR = Path.home() / ".cache" / "motion-studio-manim"


def render_manim_scene(
    scene_file: str,
    scene_name: str,
    out_dir: str,
    quality: str = "ql",        # ql / qm / qh — manim's preset (480p15 / 720p30 / 1080p60)
    fps: int = 30,
    transparent: bool = True,
    disable_caching: bool = True,
    extra_args: list = None,
    cache_key_extra: str = "",
) -> dict:
    """Render a manim scene to a transparent PNG sequence in out_dir.

    Args:
        scene_file: Path to the .py file defining the Scene subclass.
        scene_name: Class name of the Scene to render.
        out_dir:    Destination directory for the PNG sequence.
        quality:    Manim quality preset. ql=480p15, qm=720p30, qh=1080p60.
        fps:        Target frame rate (for the PNG extraction step).
        transparent: Render with alpha channel.
        disable_caching: Skip manim's own cache. Recommended for reproducibility.
        extra_args: List of additional manim CLI args.
        cache_key_extra: Stir into the cache key (e.g. parameter JSON).

    Returns:
        dict with: out_dir, n_frames, mov_path, wall_seconds, cached.
    """
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Cache key
    scene_bytes = Path(scene_file).read_bytes()
    key_input = (scene_bytes + scene_name.encode() +
                 quality.encode() + str(fps).encode() +
                 cache_key_extra.encode())
    ck = hashlib.sha1(key_input).hexdigest()[:16]
    cache_path = CACHE_DIR / f"{ck}.mov"

    t0 = time.time()
    if cache_path.exists() and cache_path.stat().st_size > 1000:
        mov = str(cache_path)
        cached = True
    else:
        # Run manim
        workdir = CACHE_DIR / f"work_{ck}"
        workdir.mkdir(exist_ok=True)
        cmd = ["manim", "render", f"-q{quality[1:]}",
               "--output_file", scene_name,
               "--media_dir", str(workdir)]
        if transparent:
            cmd.append("--transparent")
        if disable_caching:
            cmd.append("--disable_caching")
        if extra_args:
            cmd.extend(extra_args)
        cmd.extend([scene_file, scene_name])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise RuntimeError(f"manim render failed: rc={result.returncode}")

        # Find the produced MOV
        movs = list(workdir.rglob("*.mov"))
        if not movs:
            raise RuntimeError(f"manim produced no .mov in {workdir}")
        # Prefer the one with scene_name in path
        chosen = next((m for m in movs if scene_name in str(m)), movs[0])
        shutil.copy(chosen, cache_path)
        mov = str(cache_path)
        cached = False

    # Extract PNG sequence at target fps with full alpha
    # Note: -vsync vfr to avoid double-frames if source fps < target fps
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", mov,
        "-pix_fmt", "rgba",
        "-vf", f"fps={fps}",
        os.path.join(out_dir, "frame_%04d.png"),
    ], check=True)
    n_frames = len(list(Path(out_dir).glob("frame_*.png")))
    return {
        "out_dir":     out_dir,
        "n_frames":    n_frames,
        "mov_path":    mov,
        "wall_seconds": time.time() - t0,
        "cached":      cached,
        "fps":         fps,
    }


def render_action(action: dict, out_dir: str, fps: int = 30,
                  quality: str = "ql") -> dict:
    """High-level DSL: render a manim_action description.

    See references/MANIM_PATTERNS.md for the DSL. This dispatches to scenes
    defined in scripts/manim_scenes.py.
    """
    from manim_scenes import scene_from_action
    scene_module_path = str(Path(__file__).parent / "manim_scenes.py")

    # Write the action params to a JSON the scene can pick up at module load
    params_path = Path(out_dir) / "_manim_action.json"
    params_path.parent.mkdir(parents=True, exist_ok=True)
    params_path.write_text(json.dumps(action))

    # Use a dynamic wrapper file that builds + subclasses the scene class so
    # the subclass takes this wrapper's __module__ — manim's CLI uses
    # inspect.getmembers filtered by __module__, so a class returned from
    # another module gets skipped. Subclassing inherits behaviour but rehomes
    # the class.
    scene_name = "DynamicSceneFromAction"
    wrapper_path = Path(out_dir) / "_manim_wrapper.py"
    wrapper_path.write_text(f"""\
import sys, json
sys.path.insert(0, {repr(str(Path(__file__).parent))})
from manim import *  # noqa: F401,F403 — manim CLI looks for Scene subclasses
from manim_scenes import build_scene_class

with open({repr(str(params_path))}) as f:
    _action = json.load(f)

_Base = build_scene_class(_action)

class {scene_name}(_Base):
    pass
""")
    return render_manim_scene(
        str(wrapper_path), scene_name, out_dir,
        quality=quality, fps=fps,
        cache_key_extra=json.dumps(action, sort_keys=True),
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_scene = sub.add_parser("scene", help="Render a built scene by file + name")
    p_scene.add_argument("scene_file")
    p_scene.add_argument("scene_name")
    p_scene.add_argument("--out", required=True)
    p_scene.add_argument("-q", "--quality", default="ql", choices=["ql", "qm", "qh"])
    p_scene.add_argument("--fps", type=int, default=30)

    p_action = sub.add_parser("action", help="Render a manim_action JSON description")
    p_action.add_argument("action_json")
    p_action.add_argument("--out", required=True)
    p_action.add_argument("-q", "--quality", default="ql", choices=["ql", "qm", "qh"])
    p_action.add_argument("--fps", type=int, default=30)

    args = ap.parse_args()
    if args.cmd == "scene":
        res = render_manim_scene(args.scene_file, args.scene_name, args.out,
                                 quality=args.quality, fps=args.fps)
    else:
        action = json.loads(Path(args.action_json).read_text())
        res = render_action(action, args.out, fps=args.fps, quality=args.quality)
    print(json.dumps(res, indent=2))
