---
name: motion-voice-studio
description: >
  Narrated teaching-video pipeline. Manim + CAD + Kokoro TTS + source-doc imagery
  in one audio-first pipeline. Trigger: "make a teaching video", "explain X with
  animation", "narrate this paper", "3blue1brown style explainer", "lesson from
  this document", "animate and narrate". Minimum output: Manim animation with
  Kokoro narration unless user explicitly requests silent. Subtitles always soft-sub,
  never burned. Text elements use TextDisplayEngine (engines/text_display.py).
---

# motion-voice-studio — Core Production Contract

Read `README-FIRST.md` first. This file is the production contract for storyboard
generation, engine selection, and the Plan → Code → Render → Iterate loop.

---

## The Loop

```
Plan    →  Write storyboard.json. Narration fields drive everything downstream.
Code    →  generate_audio.py (Kokoro first), then render_manim.py / render_cad.py
Render  →  mux.py → output.mp4 + captions.srt
Iterate →  Adjust cfg, timing, voice, kern_scale. Re-run targeted step only.
```

**Audio first. Always.** Generate WAVs, measure real durations, then render frames
to match. Never hard-code frame counts. Never render first and stretch audio to fit.

---

## Engine choice

| Scene content | Engine | Not this |
|---|---|---|
| 3D mechanism, orbit, exploded view | `pyvista` | manim 3D |
| Animated math, equation reveal, bullets | `manim` | matplotlib |
| 3D + floating formula | `composite` (pyvista base + manim overlay) | either alone |
| Source-paper page, photograph, figure | `image` | rendered text |
| Bill of materials table | `bom` | manim Table |
| Title card, section break | `title` | full pyvista scene |

Mix-and-match. A 6-minute video typically has 5–8 different engines across shots.

---

## Storyboard JSON schema (minimum viable)

```json
{
  "title": "Your Lesson Title",
  "output": { "basename": "lesson_output", "dir": "/mnt/user-data/outputs" },
  "video": { "width": 1280, "height": 720, "fps": 30 },
  "scenes": [
    {
      "id": "intro",
      "engine": "title",
      "narration": "Welcome. Today we cover...",
      "voice": "af_heart",
      "speed": 0.95,
      "actions": [{ "kind": "title", "text": "Your Lesson Title" }]
    },
    {
      "id": "math_reveal",
      "engine": "manim",
      "narration": "The equation relates three quantities...",
      "voice": "af_heart",
      "speed": 0.95,
      "actions": [{ "kind": "equation", "latex": "E = mc^2" }]
    }
  ]
}
```

The `narration` field is the **single source of truth** for timing. Change it → everything downstream adjusts.

---

## Text display (required for all text elements)

```python
from engines.text_display import TextDisplayEngine, write_srt

engine = TextDisplayEngine()
# TUNE: engine.cfg.kern_scale = 0.06   # open up title text
# TUNE: engine.cfg.overlap_pad = 8     # stricter gap enforcement
# TUNE: engine.cfg.line_height = 1.4   # more breathing room in lists

title  = engine.kern(Text("Hello World"))           # kerned title
block  = engine.layout_block([t1, t2, t3])          # stacked, overlap-free
sub    = engine.place_subtitle(Text("caption"))     # bottom-safe placement
pairs  = engine.detect([t1, t2, t3])               # [(i,j)] if any overlap
fixed  = engine.fix([t1, t2, t3])                  # push overlaps apart
print(engine.report([t1, t2, t3]))                  # diagnostic string
```

See `engines/TEXT_DISPLAY.md` for full tuning reference.

---

## Subtitle discipline (enforced)

```python
write_srt(shots, "captions.srt")   # from engines/text_display.py
```

```bash
# Mux: always soft-sub
ffmpeg -i video.mp4 -i audio_master.wav -i captions.srt \
       -c copy -c:s mov_text output.mp4
# Also keep sidecar .srt alongside output.mp4
```

**Never**: `-vf subtitles=`, burn_in=True, or pixel-baked subtitle passes.

---

## Kokoro voices (12 bundled, 0 network required)

| Voice | Style | Notes |
|---|---|---|
| `af_heart` | American female | Warm, default |
| `af_bella` | American female | NaN-safe fallback for any voice issue |
| `af_sarah` | American female | Clear, slightly formal |
| `af_sky` | American female | Energetic |
| `am_adam` | American male | Warm |
| `am_echo` | American male | Neutral |
| `am_liam` | American male | Casual |
| `am_michael` | American male | Use speed ≥ 1.0; NaN below |
| `bf_emma` | British female | Formal |
| `bf_alice` | British female | Clear |
| `bm_george` | British male | Authoritative |
| `bm_daniel` | British male | Neutral |

Speed range: 0.85–1.15. NaN artifact: if audio is silent/zero, switch to `af_bella` and split long text into 60-word chunks.

---

## Audio mastering (runs automatically in mux.py)

```bash
# Applied by mux.py — no manual steps needed
ffmpeg -i video.mp4 -i audio.wav \
  -filter_complex "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k output.mp4
```

Target: **-14 LUFS** for video, **-16 LUFS** for podcast.  
Denoise: `afftdn` 12 dB before loudnorm.  
Reverb: `aecho` — presets: `none` (default), `subtle`, `room`, `hall`.

---

## Phrase pacing (Kokoro discipline)

Group related short sentences into ONE Kokoro call. Never synthesize "No three. No six. No nine." as three separate calls — the prosody breaks. One call, natural cadence.

Chunk size: 60–100 words per Kokoro call. Over 120: split at sentence boundaries, concatenate WAVs.

```python
# Good: one call with natural comma rhythm
narration = "No three, no six, no nine. The pattern holds."

# Bad: three calls with 320ms gaps between each
# kokoro("No three.") + kokoro("No six.") + kokoro("No nine.")
```

---

## Optional modules (read when needed)

| What | Read |
|---|---|
| CAD (build123d, pyvista, assembly schema) | `optional/CAD.md` |
| Browser / WebGPU / Hunyuan3D | `optional/BROWSER.md` |
| Brain (cognitive orchestration) | `brain/SKILL.md` |
| Production pipeline detail | `core/PIPELINE.md` |
| Audio configuration | `core/AUDIO.md` |
| Render engines deep-dive | `core/RENDER.md` |
| Troubleshooting | `core/TROUBLESHOOT.md` |
