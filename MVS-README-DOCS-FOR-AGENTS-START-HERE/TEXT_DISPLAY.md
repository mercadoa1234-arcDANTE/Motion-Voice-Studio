# TEXT_DISPLAY.md — Text Display Engine

Usage guide and tuning reference for `engines/text_display.py`.

---

## Import

```python
from engines.text_display import TextDisplayEngine, TextDisplayConfig, write_srt
```

---

## Quick start

```python
engine = TextDisplayEngine()

# Kern a title
title = engine.kern(Text("Motion-Voice-Studio", font_size=52))

# Stack labels without overlap
labels = engine.layout_block([
    Text("Step 1 — Plan"),
    Text("Step 2 — Code"),
    Text("Step 3 — Render"),
], anchor=UP * 2)

# Detect and fix overlaps
overlaps = engine.detect(labels)   # → [] if clean
engine.fix(labels)                 # push apart if not clean
print(engine.report(labels))       # → "✓ No overlaps detected."

# Place subtitle (visual hint only — real subtitles go in .srt)
sub = engine.place_subtitle(Text("Chapter 1: Foundations", font_size=22))
```

---

## Config fields (grep: TUNE or CONFIG)

```python
cfg = TextDisplayConfig(
    kern_scale     = 0.04,   # letter spacing multiplier. 0=natural, 0.05=open, 0.15=airy
    track_em       = 0.0,    # uniform em tracking. 0=off. Apply AFTER kern for titles.
    overlap_pad    = 6.0,    # minimum px gap between any two bounding boxes
    reflow_axis    = "y",    # push direction on fix(): "x" | "y" | None (both)
    max_fix_passes = 8,      # overlap fix iterations. Raise if layout is dense.
    subtitle_margin= 0.08,   # bottom margin fraction. 0.08 = 8% from bottom edge
    line_height    = 1.3,    # line height multiplier for layout_block(). 1.0=tight
    subtitle_opacity      = 0.92,  # text opacity for place_subtitle()
    subtitle_bg_opacity   = 0.0,   # background opacity. 0=off. 0.6=semi-opaque.
)
engine = TextDisplayEngine(cfg)
```

**Common tuning presets:**

| Use case | kern_scale | track_em | line_height | overlap_pad |
|---|---|---|---|---|
| Title card (large display) | 0.06 | 0.04 | — | 8 |
| Body text (explanation) | 0.03 | 0.0 | 1.35 | 6 |
| Code / monospace | 0.0 | 0.0 | 1.25 | 4 |
| Dense label cloud | 0.02 | 0.0 | 1.15 | 10 |
| Diagram annotation | 0.04 | 0.0 | — | 12 |

---

## API reference

### `kern(mob, kern_scale=None) → VGroup`
Adjusts per-glyph x offsets. Works best with geometric/sans-serif fonts.
For serif fonts, reduce kern_scale toward 0 (their optical kerning fights manual adjustment).

### `track(mob, track_em=None) → VGroup`
Uniform letter-spacing in em units. Apply after kern for display text.
`track_em=0.05` gives a clean open feel for chapter titles.

### `detect(mobs, pad=None) → List[(i,j)]`
Returns index pairs of overlapping mobjects. Run before rendering.
Empty list = layout is clean.

### `avoid(new_mob, existing, axis=None, pad=None) → mob`
Nudge `new_mob` away from all mobs in `existing`. Use when placing labels near curves or annotations near data points.

### `fix(mobs, axis=None, pad=None, max_passes=None) → list`
Iteratively push all overlapping mobs apart. Safe to call after any layout operation as a sanity step. Modifies in place.

### `layout_block(mobs, anchor=None, direction=DOWN, line_height=None) → list`
Stack mobs from anchor with proportional line spacing. Overlap-free by construction + fix() sanity pass.

### `place_subtitle(mob, scene_height=8.0, margin=None) → mob`
Position mob at the bottom safe zone. Visual hint only — always also call `write_srt()` for the actual subtitle track.

### `label_near(label_mob, target_mob, preferred_direction, existing=None, pad=None) → mob`
Smart label placement: tries preferred direction first, then RIGHT → UP → LEFT → DOWN until overlap-free.

### `report(mobs, pad=None) → str`
Diagnostic string. Use during iteration to confirm fixes worked.

---

## Plan → Code → Render → Iterate

```python
# PLAN: design the layout on paper or in pseudocode
# CODE:
engine = TextDisplayEngine()
engine.cfg.kern_scale = 0.06
engine.cfg.overlap_pad = 8

title  = engine.kern(Text("The Golden Ratio", font_size=48, color=WHITE))
sub    = Text("φ ≈ 1.6180", font_size=28, color=GOLD)
body   = engine.layout_block([
    Text("Appears in pentagons", font_size=20),
    Text("Fibonacci sequence", font_size=20),
    Text("Optimal stopping", font_size=20),
], anchor=DOWN * 0.5)

print(engine.report([title, sub] + body))  # check before render

# RENDER: run manim
# ITERATE: if text is too tight → increase kern_scale or line_height and re-run
```

---

## Subtitle workflow

```python
# In generate_audio.py (or wherever you have timing):
write_srt(shots, "/mnt/user-data/outputs/lesson.srt")

# In mux.py:
# ffmpeg -i video.mp4 -i audio.wav -i lesson.srt \
#        -c copy -c:s mov_text lesson_final.mp4
# Also keep lesson.srt alongside lesson_final.mp4
```

**The rule:** Text on screen is visual design. Subtitles are a data track. They are never the same thing.
