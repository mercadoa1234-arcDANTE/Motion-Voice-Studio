"""
Storyboard orchestrator — audio-first pipeline, multi-engine render dispatch.

Each shot declares its render engine:
- `pyvista`   — CAD scene (parametric assembly or mesh)
- `manim`     — pure manim scene (title cards, math reveals, motion graphics)
- `composite` — pyvista BASE with manim/image overlays per-frame
- `bom`       — matplotlib BOM table card
- `title`     — matplotlib title card

The orchestrator generates narration audio FIRST, measures actual durations,
plans the timeline, and only THEN renders each shot at its timeline-derived
duration. Audio drives video; never the reverse.

Storyboard schema (unified):

    {
      "name": "...",
      "fps": 30,
      "resolution": [1920, 1080],
      "assembly": "path/to/assembly.json",      # (optional, for pyvista shots)
      "voiceover": { "engine": "kokoro", ... },
      "shots": [
        {
          "id": "intro",
          "render": {"engine": "manim", "kind": "title", "primary": "...", "secondary": "..."},
          "narration": "...", "voice": "af_bella"
        },
        {
          "id": "explode",
          "render": {"engine": "pyvista", "camera": "orbit", "explode": "0→1", "from_azim": 30, "to_azim": 60},
          "narration": "..."
        },
        {
          "id": "ratio_overlay",
          "render": {
            "engine": "composite",
            "base":    {"engine": "pyvista", "camera": "orbit", "explode": "hold@1"},
            "overlays": [
              {"kind": "manim", "action": {"kind": "formula", "tex": "..."}, "position": "top-right"},
              {"kind": "math", "latex": "$N=3$", "position": "top-left"}
            ]
          },
          "narration": "..."
        }
      ]
    }
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def render_storyboard(schema_path: str, out_dir: str) -> dict:
    schema = json.loads(Path(schema_path).read_text())
    base = str(Path(schema_path).parent)
    os.makedirs(out_dir, exist_ok=True)

    fps = int(schema.get("fps", 30))
    resolution = tuple(schema.get("resolution", [1280, 720]))
    shots = schema["shots"]
    vo_cfg = schema.get("voiceover", {})

    sys.path.insert(0, str(Path(__file__).parent))

    # ── Phase 1+2: audio + timeline ─────────────────────────────────────
    from voiceover import (generate_narration, plan_timeline, write_srt,
                           mix_audio_timeline, mux_final)
    narration_dir = os.path.join(out_dir, "narration")
    print(f"[storyboard] phase 1 — narration ({len(shots)} shots)", flush=True)
    t_phase = time.time()
    records = generate_narration(
        shots, narration_dir,
        engine=vo_cfg.get("engine", "kokoro"),
        default_voice=vo_cfg.get("default_voice", "af_bella"),
        default_speed=vo_cfg.get("default_speed", 1.0),
        default_lang=vo_cfg.get("default_lang", "en-us"),
    )
    timeline = plan_timeline(shots, records, pacing=vo_cfg.get("pacing"))
    timing_path = os.path.join(out_dir, "timing.json")
    Path(timing_path).write_text(json.dumps(timeline, indent=2))
    print(f"[storyboard] phase 1+2 done in {time.time()-t_phase:.1f}s; "
          f"total timeline {timeline['total_audio_seconds']:.2f}s", flush=True)

    # ── Phase 3: build assembly once if any shot uses pyvista ───────────
    components = None
    asm_schema = None
    if any(_needs_assembly(s) for s in shots) and "assembly" in schema:
        from assembly import build_assembly_from_schema
        asm_path = schema["assembly"] if os.path.isabs(schema["assembly"]) else os.path.join(base, schema["assembly"])
        asm_schema = json.loads(Path(asm_path).read_text())
        components = build_assembly_from_schema(asm_schema, os.path.dirname(asm_path))
        print(f"[storyboard] assembly built: {len(components)} components", flush=True)

    flat_mesh_path = None
    if "mesh" in schema:
        flat_mesh_path = schema["mesh"] if os.path.isabs(schema["mesh"]) else os.path.join(base, schema["mesh"])

    # ── Phase 4: render frames per shot via the right engine ────────────
    print(f"[storyboard] phase 4 — render frames", flush=True)
    t_phase = time.time()
    frames_root = os.path.join(out_dir, "frames")
    os.makedirs(frames_root, exist_ok=True)

    for shot, t_entry in zip(shots, timeline["shots"]):
        sid = shot["id"]
        duration_s = t_entry["video_duration"]
        n_frames = max(1, int(round(duration_s * fps)))
        shot_dir = os.path.join(frames_root, sid)
        os.makedirs(shot_dir, exist_ok=True)

        engine = shot.get("render", {}).get("engine", "pyvista")
        t_shot = time.time()
        try:
            if engine == "pyvista":
                _render_pyvista_shot(asm_schema, components, flat_mesh_path,
                                     shot, shot_dir, fps, resolution, duration_s)
            elif engine == "manim":
                _render_manim_shot(shot, shot_dir, fps, resolution, duration_s)
            elif engine == "composite":
                _render_composite_shot(asm_schema, components, flat_mesh_path,
                                       shot, shot_dir, fps, resolution, duration_s, out_dir)
            elif engine == "bom":
                _render_bom_shot(asm_schema or {}, shot, shot_dir, resolution, n_frames)
            elif engine == "title":
                _render_title_card_shot(shot, shot_dir, resolution, n_frames)
            elif engine == "image":
                # v3: image-driven shot (source-doc page, photo, figure)
                from image_shot import render_image_shot
                r = shot.get("render", {})
                render_image_shot(
                    r["src"], shot_dir,
                    width=resolution[0], height=resolution[1], fps=fps,
                    duration_s=duration_s,
                    caption=r.get("caption"),
                    attribution=r.get("attribution"),
                    ken_burns=r.get("ken_burns"),
                    fade_in_s=r.get("fade_in_s", 0.3),
                    fade_out_s=r.get("fade_out_s", 0.3),
                )
            else:
                raise ValueError(f"unknown render engine for shot '{sid}': {engine}")
        except Exception as e:
            print(f"  ✗ [{sid}] render failed: {e}", flush=True)
            raise
        n_actual = len(list(Path(shot_dir).glob("frame_*.png")))
        print(f"  [{sid}] engine={engine} {n_actual}/{n_frames} frames "
              f"(target {duration_s:.2f}s) in {time.time()-t_shot:.1f}s", flush=True)

    print(f"[storyboard] phase 4 done in {time.time()-t_phase:.1f}s", flush=True)

    # ── Phase 5: concat all frames, mix audio, mux ──────────────────────
    print(f"[storyboard] phase 5 — concat & mux", flush=True)
    final_frames_dir = os.path.join(out_dir, "frames_concat")
    os.makedirs(final_frames_dir, exist_ok=True)
    i = 0
    for s in timeline["shots"]:
        shot_dir = os.path.join(frames_root, s["id"])
        for f in sorted(os.listdir(shot_dir)):
            if not f.endswith(".png"):
                continue
            src = os.path.join(shot_dir, f)
            dst = os.path.join(final_frames_dir, f"frame_{i:05d}.png")
            shutil.copy(src, dst)
            i += 1
    total_frames = i

    has_audio = any(not s["is_silent"] for s in timeline["shots"])
    final_mp4 = os.path.join(out_dir, "final.mp4")
    if has_audio:
        mixed_audio = os.path.join(out_dir, "narration_mixed.wav")
        mix_audio_timeline(timeline, mixed_audio)
        srt_path = os.path.join(out_dir, "captions.srt")
        write_srt(timeline, srt_path)
        video_dur = total_frames / fps
        mux_final(
            os.path.join(final_frames_dir, "frame_%05d.png"),
            fps, mixed_audio, final_mp4,
            captions_srt=srt_path,
            # v3 DEFAULT: soft-sub (mov_text track + sidecar .srt), NOT pixel burn-in.
            # The manim animated text on screen IS part of the picture; the
            # player-overlay subtitle is what we keep selectable/disable-able.
            # Override per-storyboard with voiceover.burn_captions: true if needed.
            burn_in=vo_cfg.get("burn_captions", False),
            video_duration=video_dur,
        )
    else:
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(fps),
            "-i", os.path.join(final_frames_dir, "frame_%05d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-preset", "medium", "-movflags", "+faststart",
            final_mp4,
        ], check=True)

    manifest = {
        "schema":  schema_path,
        "out_dir": out_dir,
        "final":   final_mp4,
        "fps":     fps,
        "resolution": list(resolution),
        "total_frames": total_frames,
        "total_video_seconds": total_frames / fps,
        "total_audio_seconds": timeline["total_audio_seconds"],
        "timeline": timeline,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def _needs_assembly(shot):
    """Does this shot need the assembly to be built (pyvista directly or as composite base)?"""
    r = shot.get("render", {})
    if r.get("engine") == "pyvista":
        return True
    if r.get("engine") == "composite":
        base = r.get("base", {})
        if base.get("engine") == "pyvista":
            return True
    if r.get("engine") == "bom":
        return True
    return False


# ── per-engine renderers ──────────────────────────────────────────────────

def _render_pyvista_shot(asm_schema, components, flat_mesh_path, shot, out_dir, fps, resolution, duration_s):
    rc = shot.get("render", {})
    if components is not None and asm_schema is not None:
        _render_assembly_shot(asm_schema, components, shot, out_dir, fps, resolution, duration_s)
    elif flat_mesh_path:
        from render_orbit import render_orbit
        render_orbit(
            flat_mesh_path, out_dir,
            duration=duration_s, fps=fps,
            resolution=resolution,
            elevation_deg=rc.get("elev", 25.0),
            azimuth_from_deg=rc.get("from_azim", 0.0),
            azimuth_to_deg=rc.get("to_azim", 360.0),
        )
    else:
        raise ValueError("pyvista shot needs either an assembly or a mesh")


def _render_assembly_shot(asm_schema, components, shot, out_dir, fps, resolution, duration_s):
    from exploded_view import render_explode_frames

    rc = shot.get("render", {})
    explode = rc.get("explode", "hold@0")
    if explode == "0→1":
        t_from, t_to = 0.0, 1.0
    elif explode == "1→0":
        t_from, t_to = 1.0, 0.0
    elif explode.startswith("hold@"):
        v = float(explode.split("@")[1])
        t_from = t_to = v
    else:
        t_from = t_to = 0.0

    render_explode_frames(
        asm_schema, components,
        out_dir=out_dir,
        duration=duration_s, fps=fps,
        resolution=resolution,
        camera=rc.get("camera", "orbit"),
        elevation_deg=rc.get("elev", 25.0),
        azim_from=rc.get("from_azim", 30.0),
        azim_to=rc.get("to_azim", 60.0),
        t_from=t_from, t_to=t_to,
        bg=rc.get("bg", "#f5f7fa"),
    )


def _render_manim_shot(shot, out_dir, fps, resolution, duration_s):
    """Render a pure manim shot. The shot's render dict has 'kind' and per-kind args."""
    from render_manim import render_action

    rc = shot.get("render", {})
    action = {k: v for k, v in rc.items() if k not in ("engine",)}
    # Manim's quality presets are 480p15, 720p30, 1080p60. Choose by resolution.
    quality = _quality_for_resolution(resolution)

    tmp_out = out_dir + "_manim_raw"
    os.makedirs(tmp_out, exist_ok=True)
    info = render_action(action, tmp_out, fps=fps, quality=quality)
    # Manim PNGs have transparent BG; for a pure manim shot we want them
    # composited onto a solid background so the video looks right.
    # Pull bg color from action; default to a dark teaching background.
    from PIL import Image
    bg_color = action.get("bg_color", "#0e1116")
    src_frames = sorted(Path(tmp_out).glob("frame_*.png"))
    n_target = max(1, int(round(duration_s * fps)))
    for i in range(n_target):
        src_idx = min(i, len(src_frames) - 1)
        if src_idx < 0:
            base = Image.new("RGBA", resolution, bg_color)
        else:
            ov = Image.open(src_frames[src_idx]).convert("RGBA")
            # Scale to target resolution if needed
            if ov.size != resolution:
                ov = ov.resize(resolution, Image.LANCZOS)
            base = Image.new("RGBA", resolution, bg_color)
            base.alpha_composite(ov)
        base.convert("RGB").save(os.path.join(out_dir, f"frame_{i:04d}.png"))
    shutil.rmtree(tmp_out, ignore_errors=True)


def _quality_for_resolution(resolution):
    w, h = resolution
    if h <= 480:
        return "ql"
    if h <= 720:
        return "qm"
    return "qh"


def _render_composite_shot(asm_schema, components, flat_mesh_path, shot, out_dir, fps, resolution, duration_s, root_out):
    """Render base shot, render overlays, composite per-frame."""
    from compositor import composite_shot, render_math_overlay, render_text_overlay
    from render_manim import render_action

    rc = shot.get("render", {})

    # Render base
    base_shot = {"id": shot["id"], "render": rc.get("base", {})}
    base_dir = out_dir + "_base"
    os.makedirs(base_dir, exist_ok=True)
    _render_pyvista_shot(asm_schema, components, flat_mesh_path,
                         base_shot, base_dir, fps, resolution, duration_s)

    # Resolve each overlay
    overlay_specs = []
    overlay_tmp_root = os.path.join(root_out, "_overlays", shot["id"])
    os.makedirs(overlay_tmp_root, exist_ok=True)

    for i, ov in enumerate(rc.get("overlays", [])):
        kind = ov["kind"]
        if kind == "math":
            png = os.path.join(overlay_tmp_root, f"math_{i}.png")
            render_math_overlay(ov["latex"], png,
                                width_px=ov.get("width_px", 600),
                                fontsize=ov.get("fontsize", 24))
            overlay_specs.append({
                "kind": "image", "path": png,
                "position": ov.get("position", "top-right"),
                "opacity": ov.get("opacity", 1.0),
                "start_frame": ov.get("start_frame", 0),
                "end_frame":   ov.get("end_frame", 999999),
                "scale":       ov.get("scale", 1.0),
                "margin":      ov.get("margin", 40),
            })
        elif kind == "text":
            png = os.path.join(overlay_tmp_root, f"text_{i}.png")
            render_text_overlay(ov["text"], png, fontsize=ov.get("fontsize", 28))
            overlay_specs.append({
                "kind": "image", "path": png,
                "position": ov.get("position", "bottom-left"),
                "opacity": ov.get("opacity", 1.0),
                "start_frame": ov.get("start_frame", 0),
                "end_frame":   ov.get("end_frame", 999999),
                "scale":       ov.get("scale", 1.0),
                "margin":      ov.get("margin", 40),
            })
        elif kind == "manim":
            man_dir = os.path.join(overlay_tmp_root, f"manim_{i}")
            os.makedirs(man_dir, exist_ok=True)
            quality = _quality_for_resolution(resolution)
            info = render_action(ov["action"], man_dir, fps=fps, quality=quality)
            overlay_specs.append({
                "kind": "sequence", "dir": man_dir,
                "prefix": "frame_", "fps": fps,
                "loop": ov.get("loop", False),
                "position": ov.get("position", "top-right"),
                "opacity": ov.get("opacity", 1.0),
                "start_frame": ov.get("start_frame", 0),
                "end_frame":   ov.get("end_frame", 999999),
                "scale":       ov.get("scale", 1.0),
                "margin":      ov.get("margin", 40),
            })
        elif kind == "image":
            overlay_specs.append({
                "kind": "image", "path": ov["path"],
                "position": ov.get("position", "top-right"),
                "opacity": ov.get("opacity", 1.0),
                "start_frame": ov.get("start_frame", 0),
                "end_frame":   ov.get("end_frame", 999999),
                "scale":       ov.get("scale", 1.0),
                "margin":      ov.get("margin", 40),
            })
        else:
            raise ValueError(f"unknown overlay kind: {kind}")

    composite_shot(base_dir, overlay_specs, out_dir,
                   base_prefix="frame_", base_ext=".png")
    shutil.rmtree(base_dir, ignore_errors=True)


def _render_bom_shot(asm, shot, out_dir, resolution, n_frames):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows, headers = [], ["#", "Part", "Qty", "Material", "Mass (g)"]
    for c in asm.get("components", []):
        bom = c.get("bom", {})
        rows.append([
            bom.get("part_number", "—"),
            c.get("label", c["id"]),
            bom.get("qty", 1),
            bom.get("material", "—"),
            bom.get("mass_g", "—"),
        ])

    W, H = resolution
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    ax.set_axis_off()
    ax.set_title("Bill of Materials", fontsize=22, fontweight="bold", pad=20)
    if rows:
        table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="left")
        table.auto_set_font_size(False); table.set_fontsize(14); table.scale(1, 1.8)
    else:
        ax.text(0.5, 0.5, "(no BOM data)", ha="center", va="center", fontsize=18)
    plt.tight_layout()
    bom_png = os.path.join(out_dir, "_bom.png")
    plt.savefig(bom_png, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    for i in range(n_frames):
        shutil.copy(bom_png, os.path.join(out_dir, f"frame_{i:04d}.png"))
    try: os.remove(bom_png)
    except OSError: pass


def _render_title_card_shot(shot, out_dir, resolution, n_frames):
    """Simple matplotlib title card (no manim). For animated titles, use manim engine instead."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    W, H = resolution
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    ax.set_axis_off()
    fig.patch.set_facecolor("#0e1116")
    title = shot.get("render", {}).get("title", shot.get("id", ""))
    subtitle = shot.get("render", {}).get("subtitle", "")
    ax.text(0.5, 0.58, title, ha="center", va="center",
            fontsize=44, fontweight="bold", color="#f0f0f0", transform=ax.transAxes)
    if subtitle:
        ax.text(0.5, 0.44, subtitle, ha="center", va="center",
                fontsize=22, color="#a0a0a0", transform=ax.transAxes)
    plt.tight_layout()
    title_png = os.path.join(out_dir, "_title.png")
    plt.savefig(title_png, dpi=100, facecolor="#0e1116")
    plt.close(fig)
    for i in range(n_frames):
        shutil.copy(title_png, os.path.join(out_dir, f"frame_{i:04d}.png"))
    try: os.remove(title_png)
    except OSError: pass


# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("--out", default="/tmp/motion-studio-out")
    args = ap.parse_args()
    m = render_storyboard(args.storyboard, args.out)
    print(json.dumps({k: v for k, v in m.items() if k != "timeline"}, indent=2))
