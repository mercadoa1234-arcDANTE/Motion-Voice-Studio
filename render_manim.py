"""
render_v2.py — Improved compositing pipeline for the CAD Animation Voice Studio.

Layers (composited in order):
  0. background + CAD floor grid
  1. CAD mesh (software painter-sort rasterizer or PyVista when available)
  2. explode / assembly guide lines with arrow tips
  3. HUD chrome — title bar, scene indicator   (uses GoldenLayout)
  4. right-panel callout labels + φ-anchored leader lines
  5. bottom subtitle bar + progress arc        (uses GoldenLayout)
  6. manim transparent overlay PNGs (optional — loaded per scene)

Key differences from render_mecha_animation.py (v1):
  - All pixel positions derive from GoldenLayout (φ), not magic numbers.
  - Leader lines use a tick + offset-box pattern instead of draw.line straight
    to the centroid (which always crosses the model silhouette).
  - Guide lines have arrowheads and glow halos for legibility on dark backgrounds.
  - Title typography is φ-scaled: title 32px bold, label 20px, small 12px.
  - Assembly progress steps use a right-edge "breadcrumb stack" at φ_x2.
  - A "layout sketch" mode generates a low-cost φ-grid PNG for early review.
"""
from __future__ import annotations

import sys
import os

# Allow importing from the studio root whether we're run directly or imported.
_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDIO_ROOT = os.path.dirname(_HERE)
for _p in [_STUDIO_ROOT, _HERE]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse
import json
import math
import shutil
import subprocess
import time
from pathlib import Path
from textwrap import wrap
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import mecha_cad_model as model

# ── golden layout imported from the scripts folder ───────────────────────────
try:
    from scripts.golden_layout import GoldenLayout, PHI, INV_PHI, INV_PHI2
except ImportError:
    from golden_layout import GoldenLayout, PHI, INV_PHI, INV_PHI2

Vec = np.ndarray


# ── colour palette (consistent with v1 dark theme) ───────────────────────────
PALETTE = {
    "bg":           (11,  16,  24),
    "title_bg":     ( 7,  10,  16),
    "title_rule":   (52,  78, 110),    # thin rule below title
    "title_accent": (80, 140, 210),    # coloured prefix mark
    "hud_text":     (220, 228, 236),
    "hud_dim":      (140, 158, 178),
    "label_bg":     ( 8,  12,  20),
    "label_border": (60,  82, 108),
    "label_text":   (220, 230, 240),
    "leader":       (180, 200, 220),
    "guide_core":   (236, 190,  82),   # yellow guide lines
    "guide_glow":   ( 60,  46,  12),   # dark glow halo around guides
    "guide_tip":    (245, 214, 110),
    "grid_line":    ( 28,  40,  56),
    "grid_axis_x":  ( 90,  54,  56),
    "grid_axis_y":  ( 46,  76, 100),
    "grid_z_axis":  ( 50,  65,  80),
    "progress_bg":  ( 28,  40,  55),
    "progress_fill":(168, 192, 220),
    "step_done":    ( 42, 100,  72),
    "step_active":  ( 60, 150, 105),
    "step_pending": ( 36,  46,  60),
    "sub_bg":       ( 0,   0,   0),
    "sub_text":     (212, 224, 234),
}


# ── font loader ───────────────────────────────────────────────────────────────

def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold
            else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size=size)
    return ImageFont.load_default()


# ── camera (unchanged from v1) ────────────────────────────────────────────────

class Camera:
    def __init__(self, yaw: float, elev: float, target: Vec, scale: float, width: int, height: int):
        self.width = width
        self.height = height
        self.target = np.array(target, dtype=float)
        self.scale = scale
        pos = self.target + 10.0 * np.array([
            math.cos(yaw) * math.cos(elev),
            math.sin(yaw) * math.cos(elev),
            math.sin(elev),
        ], dtype=float)
        self.pos = pos
        self.look = self.target - self.pos
        self.look = self.look / np.linalg.norm(self.look)
        world_up = np.array([0.0, 0.0, 1.0])
        self.right = np.cross(self.look, world_up)
        if np.linalg.norm(self.right) < 1e-8:
            self.right = np.array([1.0, 0.0, 0.0])
        else:
            self.right = self.right / np.linalg.norm(self.right)
        self.up = np.cross(self.right, self.look)
        self.up = self.up / np.linalg.norm(self.up)

    def project(self, pts: Vec):
        pts = np.asarray(pts, dtype=float)
        rel = pts - self.target
        x = rel @ self.right
        y = rel @ self.up
        depth = (pts - self.pos) @ self.look
        sx = self.width * 0.50 + x * self.scale
        sy = self.height * 0.47 - y * self.scale
        return sx, sy, depth

    def project_one(self, p: Vec):
        sx, sy, depth = self.project(np.asarray([p], dtype=float))
        return float(sx[0]), float(sy[0]), float(depth[0])


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# ── scene / camera helpers (unchanged logic from v1) ─────────────────────────

STAGES = {
    "legs":     (0.05, 0.27),
    "pelvis":   (0.12, 0.32),
    "torso":    (0.25, 0.48),
    "arms":     (0.43, 0.64),
    "head":     (0.58, 0.74),
    "backpack": (0.68, 0.84),
    "shield":   (0.77, 0.94),
    "weapon":   (0.80, 0.96),
}


def group_factor(group: str, scene_id: str, p: float) -> float:
    if scene_id in {"overview_rotation", "final_rotation"}:
        return 0.0
    if scene_id == "exploded_view":
        return smoothstep(p)
    if scene_id == "assembly_sequence":
        start, end = STAGES.get(group, (0.1, 0.9))
        return 1.0 - smoothstep((p - start) / max(1e-6, end - start))
    return 0.0


def camera_for_scene(scene_id: str, p: float, w: int, h: int) -> Camera:
    target = np.array([0.0, -0.02, 1.45])
    if scene_id == "overview_rotation":
        yaw = math.radians(-45 + 215 * p)
        elev = math.radians(17)
        scale = 88.0
    elif scene_id == "exploded_view":
        yaw = math.radians(35 + 45 * p)
        elev = math.radians(18)
        scale = 83.0 - 26.0 * smoothstep(p)
        target = np.array([0.0, -0.05, 1.35])
    elif scene_id == "assembly_sequence":
        yaw = math.radians(70 + 70 * p)
        elev = math.radians(18 + 4 * math.sin(math.pi * p))
        scale = 58.0 + 25.0 * smoothstep(p)
        target = np.array([0.0, -0.05, 1.30])
    else:
        yaw = math.radians(-130 + 365 * p)
        elev = math.radians(17)
        scale = 88.0
    return Camera(yaw, elev, target, scale, w, h)


def scene_for_time(plan, timing, t):
    scenes = plan["scenes"]
    tscenes = timing["scenes"]
    if t < tscenes[0]["start_s"]:
        return scenes[0], tscenes[0], 0.0, 0
    for i, ts in enumerate(tscenes):
        start, end = float(ts["start_s"]), float(ts["end_s"])
        gap_end = end + float(ts.get("gap_after_s", 0.0))
        if start <= t <= gap_end:
            p = clamp((t - start) / max(1e-6, end - start))
            return scenes[i], ts, p, i
    return scenes[-1], tscenes[-1], 1.0, len(scenes) - 1


# ── layer 0 — background + grid ───────────────────────────────────────────────

def draw_grid(draw: ImageDraw.ImageDraw, cam: Camera) -> None:
    z = -1.48
    vals = np.linspace(-4.0, 4.0, 9)
    for v in vals:
        is_ax_x = abs(v) < 1e-6
        for a, b, col, w in [
            (np.array([-4, v, z]), np.array([4, v, z]),
             PALETTE["grid_axis_x"] if is_ax_x else PALETTE["grid_line"], 2 if is_ax_x else 1),
            (np.array([v, -4, z]), np.array([v, 4, z]),
             PALETTE["grid_axis_y"] if is_ax_x else PALETTE["grid_line"], 2 if is_ax_x else 1),
        ]:
            ax, ay, _ = cam.project_one(a)
            bx, by, _ = cam.project_one(b)
            draw.line((ax, ay, bx, by), fill=col, width=w)
    # Vertical z-axis reference line
    z0, z1 = np.array([0, 0, -1.48]), np.array([0, 0, 4.7])
    ax, ay, _ = cam.project_one(z0)
    bx, by, _ = cam.project_one(z1)
    draw.line((ax, ay, bx, by), fill=PALETTE["grid_z_axis"], width=2)


# ── layer 1 — mesh rasterizer (painter-sort, unchanged algorithm from v1) ────

def shade_color(base, normal: Vec, cam: Camera):
    light = np.array([-0.40, -0.55, 0.78], dtype=float)
    light = light / np.linalg.norm(light)
    n = normal / (np.linalg.norm(normal) + 1e-9)
    diff = max(0.0, float(n @ light))
    rim = 0.18 * max(0.0, 1.0 - abs(float(n @ cam.look)))
    shade = 0.42 + 0.58 * diff + rim
    arr = np.array(base, dtype=float) * shade + np.array([6, 8, 10])
    return tuple(np.clip(arr, 0, 255).astype(np.uint8).tolist())


def draw_model(draw: ImageDraw.ImageDraw, parts, cam: Camera, scene_id: str, p: float,
               width: int) -> dict[str, tuple[float, float]]:
    """Rasterize all parts; return label-name → screen centroid mapping."""
    tris = []
    label_positions: dict[str, tuple[float, float]] = {}
    for part in parts:
        f = group_factor(part.group, scene_id, p)
        verts = part.vertices_local + part.center + part.explode * f
        sx, sy, depth = cam.project(verts)
        if part.label:
            lx, ly, _ = cam.project_one(part.center + part.explode * f)
            label_positions[part.label] = (lx, ly)
        faces = part.faces
        for face in faces:
            pts3 = verts[face]
            normal = np.cross(pts3[1] - pts3[0], pts3[2] - pts3[0])
            norm = np.linalg.norm(normal)
            if norm < 1e-9:
                continue
            xs, ys = sx[face], sy[face]
            if xs.max() < -40 or xs.min() > width + 40 or ys.max() < -40 or ys.min() > 760:
                continue
            pts2 = [(float(sx[i]), float(sy[i])) for i in face]
            col = shade_color(part.color, normal, cam)
            tris.append((float(depth[face].mean()), pts2, col, part.name))
    tris.sort(key=lambda r: r[0], reverse=True)
    edge = PALETTE["bg"]
    for z, pts2, col, name in tris:
        draw.polygon(pts2, fill=col)
        if width >= 1000:
            draw.line(pts2 + [pts2[0]], fill=edge, width=1)
    return label_positions


# ── layer 2 — explode / assembly guide lines ──────────────────────────────────

def _arrow_tip(draw: ImageDraw.ImageDraw, tip: tuple[float, float],
               base: tuple[float, float], size: int = 5,
               color: tuple = PALETTE["guide_tip"]) -> None:
    """Draw a small arrowhead at `tip` pointing away from `base`."""
    tx, ty = tip
    dx = tx - base[0]
    dy = ty - base[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-3:
        return
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux
    p1 = (tx - ux * size + px * size * 0.5, ty - uy * size + py * size * 0.5)
    p2 = (tx - ux * size - px * size * 0.5, ty - uy * size - py * size * 0.5)
    draw.polygon([tip, p1, p2], fill=color)


def draw_guide_lines(draw: ImageDraw.ImageDraw, parts, cam: Camera,
                     scene_id: str, p: float) -> None:
    """Draw explode / return-to-home guide lines with arrowheads."""
    if scene_id not in {"exploded_view", "assembly_sequence"}:
        return
    important = {
        "head_shell", "chest_core", "pelvis_core",
        "left_shoulder_armor", "right_shoulder_armor",
        "left_forearm", "right_forearm",
        "left_thigh", "right_thigh",
        "backpack_frame", "shield_outer", "rifle_body",
    }
    for part in parts:
        if part.name not in important:
            continue
        f = group_factor(part.group, scene_id, p)
        if f < 0.04:
            continue
        home = part.center
        away = part.center + part.explode * f
        ax, ay, _ = cam.project_one(home)
        bx, by, _ = cam.project_one(away)

        # Halo for legibility against the mesh
        draw.line((ax, ay, bx, by), fill=PALETTE["guide_glow"], width=4)
        # Core guide line
        draw.line((ax, ay, bx, by), fill=PALETTE["guide_core"], width=2)
        # Arrowhead at the displaced end
        _arrow_tip(draw, (bx, by), (ax, ay), size=6, color=PALETTE["guide_tip"])
        # Small dot at the home (origin) end
        r = 3
        draw.ellipse((ax - r, ay - r, ax + r, ay + r), fill=PALETTE["guide_tip"])


# ── layer 3 + 4 — HUD chrome ─────────────────────────────────────────────────

def draw_title_bar(draw: ImageDraw.ImageDraw, layout: GoldenLayout,
                   scene: dict, scene_idx: int, t: float, total: float,
                   fonts: dict) -> None:
    """Title bar occupying the top `layout.title_height` rows."""
    w = layout.width
    th = layout.title_height
    draw.rectangle((0, 0, w, th), fill=PALETTE["title_bg"])
    # Thin decorative rule at the bottom of the title bar
    draw.rectangle((0, th - 2, w, th), fill=PALETTE["title_rule"])
    # φ-accent mark: a small rectangle at x=φ_x1
    draw.rectangle((layout.phi_x1 - 3, 0, layout.phi_x1, th), fill=PALETTE["title_accent"])

    topic = "ORIGINAL CAD MOBILE SUIT  ·  EXPLODED ASSEMBLY"
    scene_label = scene.get("id", "").replace("_", " ")

    fnt_title = fonts["title"]
    fnt_small = fonts["small"]

    # Vertical centre within title bar
    bbox = draw.textbbox((0, 0), topic, font=fnt_title)
    txt_h = bbox[3] - bbox[1]
    ty = (th - txt_h) // 2

    # Title text — left-aligned with φ inset
    tx = max(16, round(w * INV_PHI2 * 0.1))
    draw.text((tx, ty), topic, fill=PALETTE["hud_text"], font=fnt_title)

    # Right-side scene counter — at the φ_x2 column area
    counter = f"SCENE {scene_idx + 1}/4  ·  {scene_label.upper()}  ·  {t:05.2f}s / {total:.1f}s"
    bbox2 = draw.textbbox((0, 0), counter, font=fnt_small)
    cx = w - (bbox2[2] - bbox2[0]) - max(16, round(w * 0.013))
    draw.text((cx, ty + 2), counter, fill=PALETTE["hud_dim"], font=fnt_small)


def _label_box(draw: ImageDraw.ImageDraw, text: str, box_xy: tuple[int, int],
               leader_end: tuple[float, float], font: ImageFont.ImageFont,
               layout: GoldenLayout) -> None:
    """Draw a callout label box + leader line.

    box_xy   — top-left corner of the label box (in φ label panel)
    leader_end — screen-space anchor on or near the model surface
    """
    bx, by = box_xy
    ax, ay = leader_end
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th_txt = bbox[3] - bbox[1]
    pad = max(5, round(layout.font_tiny * 0.7))
    rw = tw + pad * 2
    rh = th_txt + pad * 2

    # Leader: from the model anchor to a tick point just left of the label box.
    tick_x = bx - 12
    tick_y = by + rh // 2
    # Halo + core lines
    draw.line((ax, ay, tick_x, tick_y), fill=(*PALETTE["guide_glow"], 200), width=3)
    draw.line((ax, ay, tick_x, tick_y), fill=PALETTE["leader"], width=1)
    # Horizontal tick into box
    draw.line((tick_x, tick_y, bx, tick_y), fill=PALETTE["leader"], width=1)
    # Small anchor dot on the model
    r = 4
    draw.ellipse((ax - r, ay - r, ax + r, ay + r),
                 fill=PALETTE["leader"], outline=PALETTE["label_bg"], width=1)

    # Label box
    draw.rectangle((bx - pad, by - pad, bx + tw + pad, by + th_txt + pad),
                   fill=PALETTE["label_bg"], outline=PALETTE["label_border"], width=1)
    draw.text((bx, by), text, fill=PALETTE["label_text"], font=font)


def draw_callout_labels(draw: ImageDraw.ImageDraw, layout: GoldenLayout,
                        scene_id: str, label_positions: dict,
                        fonts: dict) -> None:
    """Draw callout labels anchored to φ-derived rows in the label panel."""
    font = fonts["label"]
    scene_labels = {
        "overview_rotation": [
            ("head and sensor block", "HEAD + SENSOR"),
            ("torso frame",           "TORSO FRAME"),
            ("shield mount",          "SHIELD MOUNT"),
        ],
        "exploded_view": [
            ("backpack",         "BACKPACK MODULE"),
            ("left leg module",  "LEG MODULES"),
            ("rifle/tool module","TOOL MODULE"),
        ],
        "assembly_sequence": [],   # handled by the assembly step column
        "final_rotation": [
            ("complete assembly",   "COMPLETE ASSEMBLY"),
            ("color-coded modules", "COLOUR-CODED MODULES"),
        ],
    }
    pairs = scene_labels.get(scene_id, [])
    for i, (model_label, display_text) in enumerate(pairs):
        if model_label not in label_positions:
            continue
        anchor = label_positions[model_label]
        box_xy = layout.label_anchor(i)
        _label_box(draw, display_text, box_xy, anchor, font, layout)


def draw_assembly_steps(draw: ImageDraw.ImageDraw, layout: GoldenLayout,
                        scene_id: str, p: float, fonts: dict) -> None:
    """Assembly sequence: step breadcrumb stack in the right label panel."""
    if scene_id != "assembly_sequence":
        return
    ordered = [
        ("legs",     "01  LEG FRAME"),
        ("pelvis",   "02  PELVIS LOCK"),
        ("torso",    "03  TORSO CORE"),
        ("arms",     "04  ARMS"),
        ("head",     "05  HEAD BLOCK"),
        ("backpack", "06  BACKPACK"),
        ("shield",   "07  SHIELD"),
        ("weapon",   "08  TOOL"),
    ]
    font = fonts["small"]
    bbox_ref = draw.textbbox((0, 0), "XX  TORSO CORE", font=font)
    row_h = (bbox_ref[3] - bbox_ref[1]) + 10
    col_x = layout.label_panel.x + 10
    start_y = layout.phi_vy1 - (len(ordered) * row_h) // 2

    active_group = None
    for g, lbl in ordered:
        s, e = STAGES[g]
        if s <= p <= e:
            active_group = g
            break

    for i, (g, lbl) in enumerate(ordered):
        y = start_y + i * row_h
        s, e = STAGES[g]
        if p > e:
            col = PALETTE["step_done"]
            bg  = (*col[:3], 120)
        elif g == active_group:
            col = PALETTE["step_active"]
            bg  = (*col[:3], 200)
        else:
            col = PALETTE["step_pending"]
            bg  = (*col[:3], 80)
        pad = 6
        draw.rectangle((col_x - pad, y - pad,
                         col_x + (bbox_ref[2] - bbox_ref[0]) + pad, y + row_h - pad),
                        fill=col, outline=PALETTE["label_border"], width=1)
        draw.text((col_x, y), lbl, fill=PALETTE["hud_text"], font=font)


def draw_subtitle_bar(draw: ImageDraw.ImageDraw, layout: GoldenLayout,
                      scene: dict, t: float, total: float,
                      fonts: dict) -> None:
    """Subtitle + progress bar at the bottom of the frame."""
    sh = layout.subtitle_height
    y0 = layout.height - sh
    draw.rectangle((0, y0, layout.width, layout.height), fill=PALETTE["sub_bg"])
    # Thin rule at top of subtitle area
    draw.rectangle((0, y0, layout.width, y0 + 1), fill=PALETTE["title_rule"])

    narration = scene.get("narration", "")
    # Determine max chars based on frame width: ~95 chars per 1280px, scaled by φ
    chars_per_line = max(60, round(95 * layout.width / 1280))
    lines = wrap(narration, width=chars_per_line)

    # Text block — vertically centred above progress bar
    prog_h = layout.progress_height
    text_area_h = sh - prog_h - 4
    fnt = fonts["subtitle"]
    bbox0 = draw.textbbox((0, 0), "Mg", font=fnt)
    line_h = (bbox0[3] - bbox0[1]) + 4
    total_text_h = len(lines[:2]) * line_h
    ty = y0 + (text_area_h - total_text_h) // 2
    pad_x = max(20, round(layout.width * 0.015))
    for ln in lines[:2]:
        draw.text((pad_x, ty), ln, fill=PALETTE["sub_text"], font=fnt)
        ty += line_h

    # Progress bar in the bottom slice of the subtitle area
    pr = layout.progress_rect(clamp(t / total))
    bar_y = layout.height - prog_h - 2
    bar_x = pr.x
    bar_total_w = layout.progress_rect(1.0).w
    # Background track
    draw.rectangle((bar_x, bar_y, bar_x + bar_total_w, bar_y + prog_h),
                   fill=PALETTE["progress_bg"])
    # Fill
    if pr.w > 0:
        draw.rectangle((bar_x, bar_y, bar_x + pr.w, bar_y + prog_h),
                       fill=PALETTE["progress_fill"])
    # Scene ticks at their start positions
    for ts in []:   # ts["start_s"] available if needed
        pass


# ── layer 6 — optional manim transparent overlay ─────────────────────────────

def apply_manim_overlay(base: Image.Image, overlay_path: str) -> Image.Image:
    """Alpha-composite a manim transparent PNG onto the base frame.

    The overlay is PIL RGBA; the base is RGBA for compositing then converted back.
    Scale the overlay to the base size if dimensions differ.
    """
    try:
        ov = Image.open(overlay_path).convert("RGBA")
        base_rgba = base.convert("RGBA")
        if ov.size != base.size:
            ov = ov.resize(base.size, Image.LANCZOS)
        base_rgba.alpha_composite(ov)
        return base_rgba.convert("RGB")
    except Exception as e:
        return base


# ── scene overlay annotation (non-callout info) ───────────────────────────────

def draw_scene_annotation(draw: ImageDraw.ImageDraw, layout: GoldenLayout,
                           scene_id: str, p: float, fonts: dict) -> None:
    """Extra info blocks that aren't callout labels."""
    fnt_sm = fonts["small"]
    fnt_tiny = fonts["tiny"]
    if scene_id == "exploded_view":
        # Tip banner below the φ_x1 line, left side
        tx, ty = 20, layout.phi_vy2 + 8
        msg = "▲  explode axes shown in yellow  ▲"
        bbox = draw.textbbox((0, 0), msg, font=fnt_sm)
        pad = 5
        draw.rectangle((tx - pad, ty - pad,
                         tx + (bbox[2] - bbox[0]) + pad,
                         ty + (bbox[3] - bbox[1]) + pad),
                        fill=PALETTE["label_bg"], outline=PALETTE["guide_core"], width=1)
        draw.text((tx, ty), msg, fill=PALETTE["guide_tip"], font=fnt_sm)
    elif scene_id == "final_rotation":
        tx = 20
        ty = layout.phi_vy2 + 8
        msg = "✓  named modules exported as GLB / STL / OBJ"
        bbox = draw.textbbox((0, 0), msg, font=fnt_sm)
        pad = 5
        draw.rectangle((tx - pad, ty - pad,
                         tx + (bbox[2] - bbox[0]) + pad,
                         ty + (bbox[3] - bbox[1]) + pad),
                        fill=PALETTE["label_bg"], outline=PALETTE["title_accent"], width=1)
        draw.text((tx, ty), msg, fill=PALETTE["hud_text"], font=fnt_sm)


# ── main frame renderer ────────────────────────────────────────────────────────

def render_frame(parts, plan: dict, timing: dict, t: float,
                 fonts: dict,
                 layout: GoldenLayout | None = None,
                 manim_overlays: dict | None = None) -> Image.Image:
    """Render a single composite frame at time `t`."""
    video = plan["video"]
    w, h = int(video["width"]), int(video["height"])
    if layout is None:
        layout = GoldenLayout(w, h)

    scene, ts, p, scene_idx = scene_for_time(plan, timing, t)
    scene_id = scene["id"]
    cam = camera_for_scene(scene_id, p, w, h)

    # Layer 0 — background
    img = Image.new("RGB", (w, h), PALETTE["bg"])
    draw = ImageDraw.Draw(img)
    draw_grid(draw, cam)

    # Layer 1 — mesh
    label_positions = draw_model(draw, parts, cam, scene_id, p, w)

    # Layer 2 — guide lines (drawn again after mesh, and below HUD)
    draw_guide_lines(draw, parts, cam, scene_id, p)
    # Second pass so tips show above mesh triangles
    draw_guide_lines(draw, parts, cam, scene_id, p)

    # Layer 6 — manim overlay (if available for this scene)
    if manim_overlays and scene_id in manim_overlays:
        overlay_dir = manim_overlays[scene_id]
        # Pick the frame for the current p within the scene
        frames = sorted(Path(overlay_dir).glob("frame_*.png"))
        if frames:
            idx = max(0, min(len(frames) - 1, round(p * (len(frames) - 1))))
            img = apply_manim_overlay(img, str(frames[idx]))
            draw = ImageDraw.Draw(img)

    # Layer 3 — title bar
    total = float(timing.get("total_duration_s", 34.4))
    draw_title_bar(draw, layout, scene, scene_idx, t, total, fonts)

    # Layer 4 — callout labels + assembly steps
    draw_callout_labels(draw, layout, scene_id, label_positions, fonts)
    draw_assembly_steps(draw, layout, scene_id, p, fonts)
    draw_scene_annotation(draw, layout, scene_id, p, fonts)

    # Layer 5 — subtitle bar + progress
    draw_subtitle_bar(draw, layout, scene, t, total, fonts)

    return img


def make_fonts(layout: GoldenLayout) -> dict:
    return {
        "title":    load_font(layout.font_title, bold=True),
        "label":    load_font(layout.font_label, bold=True),
        "small":    load_font(layout.font_small),
        "tiny":     load_font(layout.font_tiny),
        "subtitle": load_font(layout.font_label),   # same size as label for subtitles
    }


# ── layout sketch mode ─────────────────────────────────────────────────────────

def render_layout_sketch(plan: dict, timing: dict, parts, layout: GoldenLayout,
                          out_path: str, t: float = 7.0) -> None:
    """Render a single annotated frame showing the φ-grid for early review."""
    fonts = make_fonts(layout)
    img = render_frame(parts, plan, timing, t, fonts, layout)
    # Overlay the φ-grid in debug mode
    draw = ImageDraw.Draw(img)
    layout.debug_overlay(draw)
    # Annotation
    fnt = fonts["small"]
    msg = [
        f"φ = {PHI:.4f}  ·  layout sketch  ·  t = {t:.1f}s",
        f"φ_x2 = {layout.phi_x2}  φ_vy1 = {layout.phi_vy1}  focal = {layout.focal_point}",
        f"title = {layout.title_height}px  labels @ rows {layout.label_anchor(0)[1]}, {layout.label_anchor(1)[1]}",
    ]
    y = layout.viewport.y + 4
    for m in msg:
        draw.text((4, y), m, fill=(180, 215, 100), font=fnt)
        y += layout.font_small + 4
    img.save(out_path)
    print(f"[layout sketch] → {out_path}")


# ── full video render ──────────────────────────────────────────────────────────

def render_video(plan_path: str, out_video: str,
                 manim_overlays: dict | None = None,
                 sketch_only: bool = False) -> None:
    plan = json.loads(Path(plan_path).read_text())
    timing_path = (Path(plan["output"]["directory"]) / "audio" / "timing.json")
    timing = json.loads(timing_path.read_text())
    parts = model.build_parts()
    video = plan["video"]
    w, h, fps = int(video["width"]), int(video["height"]), int(video["fps"])
    total = float(timing["total_duration_s"])
    total_frames = int(round(total * fps))
    layout = GoldenLayout(w, h)
    fonts = make_fonts(layout)

    if sketch_only:
        # Render one frame from each scene for layout review
        for ts in timing["scenes"]:
            mid_t = (float(ts["start_s"]) + float(ts["end_s"])) / 2.0
            sid = ts["id"]
            p_out = Path(plan["output"]["directory"]) / "render" / f"layout_sketch_{sid}.png"
            render_layout_sketch(plan, timing, parts, layout, str(p_out), t=mid_t)
        return

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg required")

    Path(out_video).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_video),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin
    t0 = time.time()
    try:
        for i in range(total_frames):
            t = min(total - 1e-4, i / fps)
            img = render_frame(parts, plan, timing, t, fonts, layout, manim_overlays)
            proc.stdin.write(img.tobytes())
            if i % (fps * 4) == 0:
                pct = 100 * i / total_frames
                eta = (time.time() - t0) / max(i, 1) * (total_frames - i)
                print(f"  [{i}/{total_frames}  {pct:.0f}%  ETA {eta:.0f}s]", flush=True)
    finally:
        proc.stdin.close()
    proc.wait()
    elapsed = time.time() - t0
    print(f"[render_v2] {total_frames} frames → {out_video}  ({elapsed:.1f}s)")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", default=None)
    ap.add_argument("--sketch", action="store_true",
                    help="Render layout-sketch PNGs only (no video)")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    out = args.out or str(Path(plan["output"]["directory"]) / "render" /
                           f"{plan['output']['basename']}_v2_silent.mp4")
    render_video(args.plan, out, sketch_only=args.sketch)
