"""
text_display.py — Motion-Voice-Studio Text Display Engine
==========================================================
Kerning elegance + overlap detection / avoidance / fixing for Manim scenes.

QUICK TUNING REFERENCE (grep: TUNE or CONFIG)
----------------------------------------------
  KERN_SCALE       float  0.0–0.3   letter spacing multiplier  (0 = natural, 0.05 = slightly open, 0.15 = airy)
  TRACK_EM         float  0.0–0.2   word-level tracking in em units
  OVERLAP_PAD      float  px        minimum gap between any two text bounding boxes  (default 6)
  REFLOW_AXIS      str    "x"|"y"   preferred push direction when fixing overlaps
  MAX_FIX_PASSES   int              overlap fix iterations before giving up (default 8)
  SUBTITLE_MARGIN  float  0.0–1.0   bottom-of-frame margin for subtitles as fraction of height

HOW IT WORKS
------------
  1. kern()          — adjusts per-glyph x offsets for a VGroup of single-char Text
  2. track()         — applies uniform letter-spacing to a whole word/line
  3. detect()        — returns list of (i, j) pairs where bounding boxes overlap
  4. avoid()         — nudges new mob so it doesn't land on existing mobs
  5. fix()           — iteratively resolves all overlaps in a VGroup by pushing apart
  6. place_subtitle()— positions subtitle text at safe bottom margin, never burns in
  7. layout_block()  — places a list of Text mobs in a column with overlap-free gaps

PLAN → CODE → RENDER → ITERATE LOOP (built-in)
------------------------------------------------
  engine = TextDisplayEngine()
  block  = engine.layout_block(texts, anchor=ORIGIN)   # Plan → layout
  scene.add(*block)                                     # Code → add to scene
  # Render → run manim
  # Iterate → adjust KERN_SCALE / OVERLAP_PAD and re-run
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np

# ── Manim import (lazy so this module can be unit-tested standalone) ──────────
try:
    from manim import VGroup, Text, DOWN, UP, LEFT, RIGHT, ORIGIN
    _MANIM = True
except ImportError:
    _MANIM = False


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — every tunable has a comment explaining the effect     (grep: TUNE)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TextDisplayConfig:
    # TUNE: kern — tightens/opens character pairs. 0 = Manim default spacing.
    # Positive opens, negative tightens. Typical range 0.0–0.15.
    kern_scale: float = 0.04

    # TUNE: tracking — uniform em-unit spacing added between every character.
    # Applied on top of kern. 0 = off. 0.05 = slightly open, good for titles.
    track_em: float = 0.0

    # TUNE: minimum gap between any two bounding boxes, in MANIM UNITS.
    # Manim frame is 8 units tall × 14.2 units wide, so:
    #   0.10 = comfortable (recommended default)
    #   0.05 = tight
    #   0.02 = almost touching
    #   0.00 = technically non-overlapping but no breathing room
    overlap_pad: float = 0.10

    # TUNE: preferred axis when pushing overlapping objects apart.
    # "y" = push vertically (good for stacked text blocks)
    # "x" = push horizontally (good for inline labels)
    reflow_axis: str = "y"

    # TUNE: how many overlap-fix passes to run before accepting the layout.
    # More passes = more resolved but more compute. 8 is fine for most scenes.
    max_fix_passes: int = 8

    # TUNE: subtitle bottom margin as fraction of frame height.
    # 0.08 = 8% from the bottom — safe zone for most players.
    subtitle_margin: float = 0.08

    # TUNE: line height multiplier for multi-line blocks.
    # 1.0 = tight, 1.3 = comfortable reading, 1.6 = airy.
    line_height: float = 1.3

    # TUNE: opacity for subtitle text. 1.0 = fully opaque.
    # Never burn in — subtitles are always a separate track. This is UI hint only.
    subtitle_opacity: float = 0.92

    # TUNE: subtitle background opacity. 0 = no background. 0.6 = semi-transparent.
    subtitle_bg_opacity: float = 0.0  # disabled by default (player handles it)


# ══════════════════════════════════════════════════════════════════════════════
# BoundingBox — thin wrapper around (x_min, y_min, x_max, y_max)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2

    def overlaps(self, other: "BBox", pad: float = 0.0) -> bool:
        """True if this box and other overlap (including pad gap requirement)."""
        return (
            self.x_min < other.x_max + pad
            and self.x_max > other.x_min - pad
            and self.y_min < other.y_max + pad
            and self.y_max > other.y_min - pad
        )

    def overlap_vector(self, other: "BBox", pad: float = 0.0) -> Tuple[float, float]:
        """Return (dx, dy) needed to push OTHER away from self so they no longer overlap."""
        cx_s, cy_s = self.center
        cx_o, cy_o = other.center

        # Push direction: away from self's center
        push_x = cx_o - cx_s
        push_y = cy_o - cy_s

        # Penetration depth on each axis
        pen_x = (self.width / 2 + other.width / 2 + pad) - abs(push_x)
        pen_y = (self.height / 2 + other.height / 2 + pad) - abs(push_y)

        if pen_x <= 0 or pen_y <= 0:
            return (0.0, 0.0)  # no overlap

        # Resolve along the shallower penetration axis
        if pen_x < pen_y:
            sign = 1 if push_x >= 0 else -1
            return (sign * pen_x, 0.0)
        else:
            sign = 1 if push_y >= 0 else -1
            return (0.0, sign * pen_y)

    def padded(self, pad: float) -> "BBox":
        return BBox(self.x_min - pad, self.y_min - pad,
                    self.x_max + pad, self.y_max + pad)

    @classmethod
    def from_mob(cls, mob) -> "BBox":
        """Extract BBox from a Manim mobject."""
        c = mob.get_center()
        w = mob.width
        h = mob.height
        return cls(c[0] - w / 2, c[1] - h / 2, c[0] + w / 2, c[1] + h / 2)


# ══════════════════════════════════════════════════════════════════════════════
# TextDisplayEngine
# ══════════════════════════════════════════════════════════════════════════════

class TextDisplayEngine:
    """
    Text display engine for Motion-Voice-Studio.

    Usage (Manim scene):
        engine = TextDisplayEngine()                       # defaults are tuned
        engine.cfg.kern_scale = 0.06                      # TUNE if needed
        title  = engine.kern(Text("Hello World"))          # apply kerning
        block  = engine.layout_block([t1, t2, t3])        # stacked, overlap-free
        sub    = engine.place_subtitle(Text("caption"), scene_height=8)
        pairs  = engine.detect([t1, t2, t3])              # [(0,2)] if overlap
        fixed  = engine.fix([t1, t2, t3])                 # push apart and return

    Iterate workflow:
        1. Adjust cfg fields
        2. Re-call kern / layout_block / fix
        3. Re-render
    """

    def __init__(self, cfg: Optional[TextDisplayConfig] = None):
        self.cfg = cfg or TextDisplayConfig()

    # ── 1. KERNING ────────────────────────────────────────────────────────────

    def kern(self, mob, kern_scale: Optional[float] = None):
        """
        Apply kerning to a Text mobject by shifting each glyph rightward by a
        cumulative offset. Preserves whitespace and original baseline layout.

        For best results, use a monospace or geometric font. Serif fonts have
        built-in optical kerning that this may fight — reduce kern_scale to 0.

        Returns the same mobject (mutated in place — safe to chain).
        """
        if not _MANIM:
            return mob

        ks = kern_scale if kern_scale is not None else self.cfg.kern_scale
        if ks == 0:
            return mob

        submobs = list(mob.submobjects)
        if len(submobs) <= 1:
            return mob

        # Use the max glyph height as the em reference for kern offsets.
        # Skips zero-width chars (spaces) so they don't pull the average down.
        heights = [g.height for g in submobs if g.height > 0.01]
        if not heights:
            return mob
        kern_unit = max(heights) * ks

        # Shift each glyph rightward by cumulative kern_unit.
        # Original whitespace + glyph widths are preserved; we just add gap.
        for i in range(1, len(submobs)):
            submobs[i].shift(np.array([kern_unit * i, 0, 0]))

        # Re-center the whole mob so it stays where it was placed
        # (cumulative shift moved the visual center rightward).
        original_center = mob.get_center()
        mob.move_to(original_center)
        return mob

    def track(self, mob, track_em: Optional[float] = None):
        """
        Apply uniform tracking (letter-spacing) to all characters in mob.
        track_em is in em units (relative to font size).

        Tracking is additive with kern — apply track AFTER kern for display text.
        Useful for titles. Use kern_scale=0, track_em=0.05 for clean title spacing
        without per-glyph adjustment.

        Returns the same mobject (mutated in place).
        """
        if not _MANIM:
            return mob

        te = track_em if track_em is not None else self.cfg.track_em
        if te == 0:
            return mob

        submobs = list(mob.submobjects)
        if len(submobs) <= 1:
            return mob

        # em derived from cap height (roughly 0.7 of total mob height)
        em = mob.height / 0.7
        spacing = te * em

        for i in range(1, len(submobs)):
            submobs[i].shift(np.array([spacing * i, 0, 0]))

        original_center = mob.get_center()
        mob.move_to(original_center)
        return mob

    # ── 2. OVERLAP DETECTION ─────────────────────────────────────────────────

    def detect(self, mobs: list, pad: Optional[float] = None) -> List[Tuple[int, int]]:
        """
        Return list of (i, j) index pairs where mob[i] and mob[j] bounding boxes
        overlap (within pad gap). Pairs are unique: (0,1) is returned, not (1,0).

        Use this BEFORE rendering to catch layout collisions in the plan phase.

            overlaps = engine.detect([label_a, label_b, label_c])
            if overlaps:
                mobs = engine.fix(mobs)  # auto-resolve
        """
        pad = pad if pad is not None else self.cfg.overlap_pad
        boxes = [BBox.from_mob(m) for m in mobs]
        pairs = []
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if boxes[i].overlaps(boxes[j], pad=pad):
                    pairs.append((i, j))
        return pairs

    def detect_raw(self, boxes: List[BBox], pad: float = 0.0) -> List[Tuple[int, int]]:
        """Same as detect() but operates on BBox objects directly (useful for pre-layout checks)."""
        pairs = []
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if boxes[i].overlaps(boxes[j], pad=pad):
                    pairs.append((i, j))
        return pairs

    # ── 3. OVERLAP AVOIDANCE (place NEW mob without hitting existing) ─────────

    def avoid(self, new_mob, existing: list, axis: Optional[str] = None,
              pad: Optional[float] = None):
        """
        Nudge new_mob so it doesn't overlap any mob in existing.
        Returns new_mob (mutated in place) — safe to chain.

        Use this when placing a label near a known-safe anchor:
            annotation = engine.avoid(Text("→ peak"), [curve, x_axis])

        axis: "x" pushes horizontally, "y" pushes vertically, None = auto.
        """
        if not existing:
            return new_mob

        pad = pad if pad is not None else self.cfg.overlap_pad
        axis = axis or self.cfg.reflow_axis

        new_box = BBox.from_mob(new_mob)
        for mob in existing:
            existing_box = BBox.from_mob(mob)
            if new_box.overlaps(existing_box, pad=pad):
                dx, dy = existing_box.overlap_vector(new_box, pad=pad)
                if axis == "x":
                    new_mob.shift(np.array([dx, 0, 0]))
                elif axis == "y":
                    new_mob.shift(np.array([0, dy, 0]))
                else:
                    new_mob.shift(np.array([dx, dy, 0]))
                new_box = BBox.from_mob(new_mob)  # refresh after nudge

        return new_mob

    # ── 4. OVERLAP FIXING (resolve all overlaps in a group) ──────────────────

    def fix(self, mobs: list, axis: Optional[str] = None,
            pad: Optional[float] = None, max_passes: Optional[int] = None) -> list:
        """
        Iteratively push overlapping mobs apart until no overlaps remain
        (or max_fix_passes is reached). Modifies mobs in place.

        Algorithm: for each overlapping pair, compute the minimal push along
        the requested axis (or auto-pick the shallower penetration axis when
        axis=None). Apply half the push to each mob (symmetric). Repeat.

        NOTE: this is a heuristic solver — it converges for typical text
        layouts but may not find a globally optimal solution for pathological
        cases. For those, use layout_block() which avoids collisions by
        construction.
        """
        pad = pad if pad is not None else self.cfg.overlap_pad
        axis = axis or self.cfg.reflow_axis
        max_passes = max_passes if max_passes is not None else self.cfg.max_fix_passes
        # Small overshoot keeps fix() from converging exactly AT the pad boundary,
        # which can leave detect() reporting near-equality overlaps after a fix.
        push_pad = pad * 1.02

        for _ in range(max_passes):
            pairs = self.detect(mobs, pad=pad)
            if not pairs:
                break

            for i, j in pairs:
                bi = BBox.from_mob(mobs[i])
                bj = BBox.from_mob(mobs[j])

                if axis == "x":
                    # Force push along x regardless of which axis is shallower.
                    # Without this override, overlap_vector picks the shallower
                    # axis (often y), returns (0, dy), and we shift by 0 — bug.
                    push_x = bj.center[0] - bi.center[0]
                    sign = 1 if push_x >= 0 else -1
                    needed = (bi.width / 2 + bj.width / 2 + push_pad) - abs(push_x)
                    if needed > 0:
                        dx = sign * needed
                        mobs[i].shift(np.array([-dx / 2, 0, 0]))
                        mobs[j].shift(np.array([dx / 2, 0, 0]))

                elif axis == "y":
                    # Force push along y, same reasoning.
                    push_y = bj.center[1] - bi.center[1]
                    sign = 1 if push_y >= 0 else -1
                    needed = (bi.height / 2 + bj.height / 2 + push_pad) - abs(push_y)
                    if needed > 0:
                        dy = sign * needed
                        mobs[i].shift(np.array([0, -dy / 2, 0]))
                        mobs[j].shift(np.array([0, dy / 2, 0]))

                else:
                    # axis=None → auto-pick shallower axis (original behavior).
                    dx, dy = bi.overlap_vector(bj, pad=push_pad)
                    mobs[i].shift(np.array([-dx / 2, -dy / 2, 0]))
                    mobs[j].shift(np.array([dx / 2, dy / 2, 0]))

        return mobs

    # ── 5. LAYOUT BLOCK (stacked column, overlap-free by construction) ────────

    def layout_block(self, mobs: list, anchor=None,
                     direction=None, line_height: Optional[float] = None) -> list:
        """
        Stack mobs vertically (or horizontally) from anchor, with line_height
        spacing, guaranteed overlap-free by construction (no fix() needed).

        After stacking, runs detect() as a sanity check and fix() if any remain
        (can happen with very wide text that clips its neighbors diagonally).

        direction: DOWN (default), UP, LEFT, RIGHT
        anchor: Manim coordinate (3-array). Default = ORIGIN.

        Returns the same list (mutated).
        """
        if not _MANIM:
            return mobs
        if not mobs:
            return mobs

        lh = line_height if line_height is not None else self.cfg.line_height
        if direction is None:
            direction = DOWN
        if anchor is None:
            anchor = ORIGIN

        # Place first mob at anchor
        mobs[0].move_to(anchor)

        for i in range(1, len(mobs)):
            prev = mobs[i - 1]
            curr = mobs[i]
            # Manim's next_to(buff=X) inserts X gap BETWEEN edges (not center-to-center).
            # We want total line spacing = line_height × font_height, so the gap
            # between edges = (line_height − 1.0) × font_height.
            # line_height=1.0 → edges touching, line_height=1.3 → 0.3 × height gap.
            gap = max(0.0, prev.height * (lh - 1.0))
            curr.next_to(prev, direction, buff=gap)

        # Sanity fix for any diagonal leakage
        remaining = self.detect(mobs, pad=self.cfg.overlap_pad)
        if remaining:
            self.fix(mobs, pad=self.cfg.overlap_pad)

        return mobs

    # ── 6. SUBTITLE PLACEMENT ─────────────────────────────────────────────────

    def place_subtitle(self, mob, scene_height: float = 8.0,
                       margin: Optional[float] = None):
        """
        Place a subtitle text mobject at the safe bottom zone of the frame.

        IMPORTANT: This positions the Text object as a Manim visual element
        (lower-third style). It does NOT burn subtitles into pixels. Subtitles
        for the exported video are always written as a separate .srt file and
        muxed as a mov_text track. This function is for in-scene visual hints
        only (e.g., a speaker label or chapter title overlay).

        margin: fraction of scene_height. Default = cfg.subtitle_margin (0.08).
        """
        if not _MANIM:
            return mob

        m = margin if margin is not None else self.cfg.subtitle_margin
        # Bottom of safe zone
        bottom_y = -scene_height / 2 + scene_height * m
        mob.set_y(bottom_y + mob.height / 2)
        return mob

    # ── 7. SMART LABEL PLACEMENT (avoid a reference object) ──────────────────

    def label_near(self, label_mob, target_mob, preferred_direction=None,
                   existing: Optional[list] = None, pad: Optional[float] = None):
        """
        Place label_mob near target_mob in preferred_direction, then verify
        it doesn't hit any mob in existing. If it does, try the other cardinal
        directions in order: RIGHT, UP, LEFT, DOWN.

        Returns label_mob (mutated).
        """
        if not _MANIM:
            return label_mob

        pad = pad if pad is not None else self.cfg.overlap_pad
        existing = existing or []
        dirs = [RIGHT, UP, LEFT, DOWN]
        if preferred_direction is not None:
            # Put preferred first
            try:
                dirs.remove(preferred_direction)
            except (ValueError, AttributeError):
                pass
            dirs.insert(0, preferred_direction)

        for direction in dirs:
            label_mob.next_to(target_mob, direction, buff=pad / 72)
            if not self.detect([label_mob] + existing, pad=pad):
                return label_mob  # clean placement found

        # Fallback: stay in preferred direction, accept overlap
        if preferred_direction is not None:
            label_mob.next_to(target_mob, preferred_direction, buff=pad / 72)
        return label_mob

    # ── 8. DIAGNOSTIC ────────────────────────────────────────────────────────

    def report(self, mobs: list, pad: Optional[float] = None) -> str:
        """
        Return a human-readable overlap report. Use during iteration:
            print(engine.report([t1, t2, t3]))
        """
        pad = pad if pad is not None else self.cfg.overlap_pad
        pairs = self.detect(mobs, pad=pad)
        if not pairs:
            return "✓ No overlaps detected."
        lines = [f"⚠ {len(pairs)} overlap(s) detected:"]
        for i, j in pairs:
            bi = BBox.from_mob(mobs[i])
            bj = BBox.from_mob(mobs[j])
            lines.append(f"  [{i}] ↔ [{j}]  centers: {bi.center} / {bj.center}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# SRT writer — subtitles are ALWAYS a separate file, never burned in
# ══════════════════════════════════════════════════════════════════════════════

def write_srt(timeline_shots: list, output_path: str) -> None:
    """
    Write a standard SRT subtitle file from the production timeline.

    Each shot entry must have:
        shot["start_time"]   float  seconds
        shot["end_time"]     float  seconds
        shot["narration"]    str    the text spoken in this shot

    NEVER use ffmpeg's -vf subtitles= filter or hardcoded pixel-bake.
    Always mux as:  ffmpeg -i video.mp4 -i narration.wav -i captions.srt
                           -c copy -c:s mov_text output.mp4

    The sidecar .srt file is kept alongside output.mp4 for players that
    don't support embedded mov_text (e.g., QuickTime, some Android players).
    """
    lines = []
    for idx, shot in enumerate(timeline_shots, start=1):
        start = _fmt_srt_time(shot.get("start_time", 0))
        end   = _fmt_srt_time(shot.get("end_time", shot.get("start_time", 0) + 3))
        text  = shot.get("narration", "").strip()
        if not text:
            continue
        lines.extend([str(idx), f"{start} --> {end}", text, ""])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _fmt_srt_time(seconds: float) -> str:
    """Format seconds to SRT HH:MM:SS,mmm"""
    ms  = int(round(seconds * 1000))
    hh  = ms // 3_600_000; ms %= 3_600_000
    mm  = ms // 60_000;    ms %= 60_000
    ss  = ms // 1_000;     ms %= 1_000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


# ══════════════════════════════════════════════════════════════════════════════
# STANDALONE DEMO (python text_display.py)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Pure-Python smoke test (no Manim required)
    print("TextDisplayEngine — BBox overlap tests")

    a = BBox(0, 0, 4, 2)
    b = BBox(3, 1, 7, 3)    # overlaps a
    c = BBox(5, 5, 9, 7)    # does not overlap a or b

    assert a.overlaps(b, pad=0),  "should overlap"
    assert not a.overlaps(c),     "should not overlap"
    dx, dy = a.overlap_vector(b, pad=2)
    print(f"  push b away from a: dx={dx:.2f} dy={dy:.2f}")
    assert dx != 0 or dy != 0,    "non-zero push expected"

    cfg = TextDisplayConfig(kern_scale=0.06, overlap_pad=4)
    eng = TextDisplayEngine(cfg)
    print(f"  engine created, kern_scale={eng.cfg.kern_scale}")

    # SRT write
    shots = [
        {"start_time": 0.0,  "end_time": 3.5,  "narration": "Welcome to the demo."},
        {"start_time": 3.5,  "end_time": 7.2,  "narration": "This shows text kerning."},
        {"start_time": 7.2,  "end_time": 11.0, "narration": "Overlaps are detected and fixed."},
    ]
    write_srt(shots, "/tmp/demo.srt")
    print("  SRT written to /tmp/demo.srt")

    with open("/tmp/demo.srt") as f:
        print(f.read())

    print("All tests passed.")
