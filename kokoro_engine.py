"""
image_shot.py — v3 image-driven shot renderer.

New engine in v3. Renders shots whose visual is a still image (a source-doc
page screenshot, a figure, a photograph) rather than a CAD scene or manim
animation. Optional manim or text overlay on top for figure captions, page
markers, "Figure 3 from Canosa 2024" attribution, etc.

Usage in storyboard:
    {
      "id": "intro_paper",
      "render": {
        "engine": "image",
        "src": "assets/source_docs/canosa_137/page_001.png",
        "caption": "Canosa 2024 · header",
        "ken_burns": {"zoom": 1.08, "pan": [0.0, -0.05]},
        "fade_in_s": 0.4,
        "fade_out_s": 0.4
      },
      "narration": "..."
    }

Output: a frame sequence at the requested FPS for the shot's duration. The
orchestrator concatenates this with all other shots.

Design notes:
- Uses PIL/Pillow only. No GPU. Smooth at 30fps for static or simple Ken
  Burns moves.
- Honors golden-ratio compositing for caption placement (same palette as
  the rest of the studio).
- Image is rescaled-and-letterboxed to the project's resolution; never
  distorted.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# Visual identity tokens shared with the rest of the studio (do not drift)
BG_COLOR = (13, 13, 26)
TEXT_PRIMARY = (240, 240, 240)
TEXT_SECONDARY = (160, 160, 170)
GOLD = (255, 215, 0)


def render_image_shot(
    src: str,
    out_dir: str,
    width: int,
    height: int,
    fps: int,
    duration_s: float,
    caption: Optional[str] = None,
    attribution: Optional[str] = None,
    ken_burns: Optional[dict] = None,
    fade_in_s: float = 0.3,
    fade_out_s: float = 0.3,
    safe_zone_ratio: float = 0.92,
) -> int:
    """Render a still image as a shot, optionally with caption and Ken Burns.

    Returns frame count rendered.
    """
    src = str(src); out_dir = str(out_dir)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    n_frames = max(1, int(round(duration_s * fps)))

    img = Image.open(src).convert('RGB')
    iw, ih = img.size

    # Fit image inside safe-zone with letterboxing (preserve aspect)
    sw, sh = int(width * safe_zone_ratio), int(height * safe_zone_ratio)
    scale = min(sw / iw, sh / ih)
    fit_w, fit_h = int(iw * scale), int(ih * scale)
    img_fit = img.resize((fit_w, fit_h), Image.LANCZOS)

    # Ken Burns parameters
    kb = ken_burns or {}
    zoom_end = float(kb.get('zoom', 1.0))      # final zoom factor
    pan = kb.get('pan', [0.0, 0.0])             # (dx, dy) at end, in fraction of image
    pan_x, pan_y = float(pan[0]), float(pan[1])

    fade_in_frames = int(round(fade_in_s * fps))
    fade_out_frames = int(round(fade_out_s * fps))

    # Try to load a default font
    font_caption = _load_font(size=int(height * 0.030))
    font_attrib = _load_font(size=int(height * 0.020))

    for i in range(n_frames):
        t_norm = i / max(1, n_frames - 1)
        # Lerp zoom & pan
        zoom = 1.0 + (zoom_end - 1.0) * t_norm
        dx = pan_x * t_norm
        dy = pan_y * t_norm

        # Compute zoomed crop region from the fitted image
        cur_w = int(fit_w / zoom)
        cur_h = int(fit_h / zoom)
        cx = int(fit_w / 2 + dx * fit_w)
        cy = int(fit_h / 2 + dy * fit_h)
        l = max(0, min(fit_w - cur_w, cx - cur_w // 2))
        t = max(0, min(fit_h - cur_h, cy - cur_h // 2))
        crop = img_fit.crop((l, t, l + cur_w, t + cur_h)).resize((fit_w, fit_h), Image.LANCZOS)

        # Composite into the canvas
        canvas = Image.new('RGB', (width, height), BG_COLOR)
        ox = (width - fit_w) // 2
        oy = (height - fit_h) // 2
        canvas.paste(crop, (ox, oy))

        # Caption (above image) and attribution (below image)
        draw = ImageDraw.Draw(canvas)
        if caption and font_caption:
            tw = _text_w(draw, caption, font_caption)
            tx = (width - tw) // 2
            ty = max(10, oy - int(font_caption.size * 1.4))
            draw.text((tx, ty), caption, fill=GOLD, font=font_caption)
        if attribution and font_attrib:
            tw = _text_w(draw, attribution, font_attrib)
            tx = (width - tw) // 2
            ty = min(height - int(font_attrib.size * 2),
                     oy + fit_h + int(font_attrib.size * 0.5))
            draw.text((tx, ty), attribution, fill=TEXT_SECONDARY, font=font_attrib)

        # Apply fade in / out by alpha blending toward the BG.
        if i < fade_in_frames:
            alpha = i / max(1, fade_in_frames)
            canvas = _fade_to_bg(canvas, 1.0 - alpha)
        elif i >= n_frames - fade_out_frames:
            alpha = (n_frames - 1 - i) / max(1, fade_out_frames)
            canvas = _fade_to_bg(canvas, 1.0 - alpha)

        canvas.save(os.path.join(out_dir, f'frame_{i:05d}.png'))

    return n_frames


def _load_font(size: int):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _text_w(draw, text, font):
    if hasattr(draw, 'textbbox'):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    return draw.textlength(text, font=font) if hasattr(draw, 'textlength') else len(text) * font.size // 2


def _fade_to_bg(img: Image.Image, frac_bg: float) -> Image.Image:
    """Blend img toward BG_COLOR by frac_bg (0 = no fade, 1 = fully BG)."""
    if frac_bg <= 0:
        return img
    if frac_bg >= 1:
        return Image.new('RGB', img.size, BG_COLOR)
    bg = Image.new('RGB', img.size, BG_COLOR)
    return Image.blend(img, bg, frac_bg)


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out', required=True)
    ap.add_argument('--width', type=int, default=1280)
    ap.add_argument('--height', type=int, default=720)
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--duration', type=float, default=4.0)
    ap.add_argument('--caption', default=None)
    ap.add_argument('--attribution', default=None)
    ap.add_argument('--zoom', type=float, default=1.0)
    ap.add_argument('--pan-x', type=float, default=0.0)
    ap.add_argument('--pan-y', type=float, default=0.0)
    args = ap.parse_args()
    kb = {'zoom': args.zoom, 'pan': [args.pan_x, args.pan_y]} if args.zoom != 1.0 or args.pan_x or args.pan_y else None
    n = render_image_shot(
        args.src, args.out,
        width=args.width, height=args.height, fps=args.fps,
        duration_s=args.duration,
        caption=args.caption, attribution=args.attribution,
        ken_burns=kb,
    )
    print(json.dumps({'frames': n, 'duration_s': args.duration}))


if __name__ == '__main__':
    main()
