"""
Per-frame compositor: combine a base PNG sequence (typically pyvista CAD) with
one or more overlay PNG sequences (typically manim transparent scenes or
matplotlib mathtext overlays).

Two main entrypoints:
    composite_shot()    — given base_dir + overlay_dirs, produces composited frames
    render_math_overlay() — produces a matplotlib mathtext overlay as a single PNG
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

from PIL import Image


# ── Path 1: matplotlib mathtext as static overlay ─────────────────────────

def render_math_overlay(
    latex: str,
    out_path: str,
    width_px: int = 600,
    fontsize: int = 24,
    text_color: str = "white",
    box: bool = True,
    box_color: str = "#0e1116",
    box_alpha: float = 0.7,
) -> str:
    """Render a LaTeX-subset equation to a transparent PNG via matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(width_px / 200, 1.6), dpi=200)
    kwargs = dict(ha="center", va="center", fontsize=fontsize, color=text_color)
    if box:
        kwargs["bbox"] = dict(
            facecolor=box_color, alpha=box_alpha,
            boxstyle="round,pad=0.5", edgecolor="none",
        )
    fig.text(0.5, 0.5, latex, **kwargs)
    fig.patch.set_alpha(0)
    fig.savefig(out_path, transparent=True, dpi=200, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return out_path


def render_text_overlay(
    text: str,
    out_path: str,
    fontsize: int = 28,
    text_color: str = "white",
    box: bool = True,
    box_color: str = "#0e1116",
    box_alpha: float = 0.78,
    weight: str = "bold",
    pad: int = 14,
) -> str:
    """Render plain text to a transparent PNG (no LaTeX required)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(dpi=200)
    kw = dict(ha="left", va="center", fontsize=fontsize, color=text_color,
              weight=weight)
    if box:
        kw["bbox"] = dict(facecolor=box_color, alpha=box_alpha,
                          boxstyle="round,pad=0.5", edgecolor="none")
    fig.text(0.01, 0.5, text, **kw)
    fig.patch.set_alpha(0)
    fig.savefig(out_path, transparent=True, dpi=200,
                bbox_inches="tight", pad_inches=pad / 200.0)
    plt.close(fig)
    return out_path


# ── position resolution ───────────────────────────────────────────────────

def _resolve_position(position, base_size, overlay_size, margin=40):
    """Translate a position spec to (x, y) pixel coordinates.

    position can be:
      - "top-right" / "top-left" / "bottom-right" / "bottom-left" / "center"
      - "lower-third"  → bottom strip
      - "upper-third"  → top strip
      - (x, y) tuple of absolute pixels
      - {"x": "right", "y": "top"} with literal axis values
      - {"x": int, "y": int} absolute
    """
    bw, bh = base_size
    ow, oh = overlay_size

    if isinstance(position, (tuple, list)):
        return int(position[0]), int(position[1])

    if isinstance(position, dict):
        def axis(v, span, ov, m):
            if v == "left":   return m
            if v == "right":  return span - ov - m
            if v in ("top",): return m
            if v == "bottom": return span - ov - m
            if v == "center": return (span - ov) // 2
            if isinstance(v, (int, float)): return int(v)
            return m
        return axis(position.get("x", "right"), bw, ow, margin), axis(position.get("y", "top"), bh, oh, margin)

    if position == "top-right":    return bw - ow - margin, margin
    if position == "top-left":     return margin, margin
    if position == "bottom-right": return bw - ow - margin, bh - oh - margin
    if position == "bottom-left":  return margin, bh - oh - margin
    if position == "center":       return (bw - ow) // 2, (bh - oh) // 2
    if position == "lower-third":  return (bw - ow) // 2, int(bh * 0.78)
    if position == "upper-third":  return (bw - ow) // 2, int(bh * 0.05)
    # default
    return bw - ow - margin, margin


# ── per-frame composite ───────────────────────────────────────────────────

def composite_shot(
    base_dir: str,
    overlays: list,
    out_dir: str,
    base_prefix: str = "frame_",
    base_ext: str = ".png",
) -> dict:
    """Composite a base PNG sequence with one or more overlays.

    `overlays` is a list of dicts. Each dict can be one of:

        {"kind": "image",     "path": ".../still.png",  "position": "...", "opacity": 1.0,
         "start_frame": 0, "end_frame": 9999}

        {"kind": "sequence",  "dir":  ".../alpha_frames/",
         "prefix": "frame_", "fps": 30, "loop": False,
         "position": "...", "opacity": 1.0,
         "start_frame": 0, "end_frame": 9999}

    Returns dict with stats.
    """
    base_files = sorted(f for f in os.listdir(base_dir)
                        if f.startswith(base_prefix) and f.endswith(base_ext))
    os.makedirs(out_dir, exist_ok=True)

    # Pre-resolve overlay sources
    for o in overlays:
        if o["kind"] == "sequence":
            d = o["dir"]
            files = sorted(f for f in os.listdir(d) if f.startswith(o.get("prefix", "frame_")) and f.endswith(".png"))
            o["_files"] = [os.path.join(d, f) for f in files]
            if not o["_files"]:
                raise FileNotFoundError(f"no overlay frames in {d}")

    for i, base_name in enumerate(base_files):
        base_path = os.path.join(base_dir, base_name)
        base_img = Image.open(base_path).convert("RGBA")
        bw, bh = base_img.size

        for o in overlays:
            start = o.get("start_frame", 0)
            end = o.get("end_frame", 999999)
            if not (start <= i <= end):
                continue
            opacity = float(o.get("opacity", 1.0))
            if o["kind"] == "image":
                ov = Image.open(o["path"]).convert("RGBA")
            elif o["kind"] == "sequence":
                files = o["_files"]
                if o.get("loop", False):
                    idx = (i - start) % len(files)
                else:
                    idx = min(max(0, i - start), len(files) - 1)
                ov = Image.open(files[idx]).convert("RGBA")
            else:
                raise ValueError(f"unknown overlay kind: {o['kind']}")

            # Scale overlay if requested
            if "scale" in o:
                sw, sh = ov.size
                s = float(o["scale"])
                ov = ov.resize((int(sw * s), int(sh * s)), Image.LANCZOS)

            x, y = _resolve_position(o.get("position", "top-right"),
                                     base_img.size, ov.size, o.get("margin", 40))

            # Apply opacity if < 1.0
            if opacity < 0.999:
                r, g, b, a = ov.split()
                a = a.point(lambda v, op=opacity: int(v * op))
                ov = Image.merge("RGBA", (r, g, b, a))

            base_img.alpha_composite(ov, (x, y))

        out_path = os.path.join(out_dir, base_name)
        base_img.convert("RGB").save(out_path)

    return {"frames": len(base_files), "out_dir": out_dir}


# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_math = sub.add_parser("math", help="render a mathtext PNG overlay")
    p_math.add_argument("latex")
    p_math.add_argument("--out", required=True)
    p_math.add_argument("--fontsize", type=int, default=24)

    p_text = sub.add_parser("text", help="render a plain text PNG overlay")
    p_text.add_argument("text")
    p_text.add_argument("--out", required=True)
    p_text.add_argument("--fontsize", type=int, default=28)

    p_comp = sub.add_parser("composite", help="composite a shot")
    p_comp.add_argument("--base", required=True)
    p_comp.add_argument("--overlays", required=True, help="JSON list of overlay specs")
    p_comp.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.cmd == "math":
        render_math_overlay(args.latex, args.out, fontsize=args.fontsize)
        print(f"math overlay → {args.out}")
    elif args.cmd == "text":
        render_text_overlay(args.text, args.out, fontsize=args.fontsize)
        print(f"text overlay → {args.out}")
    elif args.cmd == "composite":
        overlays = json.loads(args.overlays)
        res = composite_shot(args.base, overlays, args.out)
        print(json.dumps(res, indent=2))
