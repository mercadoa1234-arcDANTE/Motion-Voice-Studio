# core/PIPELINE.md — Production Loop

The discipline for every production run. Read this after SKILL.md.

---

## The agent loop

```
SOURCE (prompt / PDF / URL / topic)
      ↓
  Plan storyboard.json          ← narration fields first, engines second
      ↓
  /grill (self)                 ← ≤ 3 questions, only what source can't answer
      ↓
  generate_audio.py             ← Kokoro TTS, phrase-aware, all scenes
      ↓
  render per shot               ← timed to real audio durations from WAVs
      ↓
  audio_master.py               ← -14 LUFS loudnorm + afftdn denoise
      ↓
  mux.py                        ← video + audio + soft-sub track
      ↓
  self_check.py                 ← duration match, audio peak, silence check
```

**Tool-limit interrupt rule:** if you hit a context/tool limit mid-run, write `state.json`
with `{"completed_scenes": [...], "pending_scenes": [...], "last_file": "..."}` and
report. On resume, load state.json and continue from pending.

---

## Audio-first contract

Generate all narration WAVs before rendering a single frame. Scene duration = WAV duration + configured gap. Never hard-code frame counts.

```python
from voiceover import generate_narration, plan_timeline

records  = generate_narration(shots, "narration/", engine="kokoro", default_voice="af_heart")
timeline = plan_timeline(shots, records)   # derives durations from actual WAV lengths
# → timeline["shots"][i]["video_duration"] is the authoritative frame count for shot i
```

---

## Mux recipe

```bash
# Step 1: normalize audio
ffmpeg -i narration_concat.wav \
  -af "afftdn=nr=12,loudnorm=I=-14:TP=-1.5:LRA=11" \
  audio_master.wav

# Step 2: mux with soft-sub (NEVER burn-in)
ffmpeg -y \
  -i video_silent.mp4 \
  -i audio_master.wav \
  -i captions.srt \
  -c copy -c:a aac -b:a 192k -c:s mov_text \
  output_final.mp4

# Also keep sidecar:
cp captions.srt "$(basename output_final .mp4).srt"
```

---

## Source-document flow

When narrating a paper or post:

1. `python scripts/source_doc_pass.py source.pdf` → extracts pages, figures, metadata
2. Storyboard references pages as `engine: "image"` shots
3. First scene: title page (~4s while narrator says "From Author 2024...")
4. Body shots: specific figure before the explainer animation
5. Final scene: acknowledgements + references as closing cards

---

## Self-check

Run after mux:

```bash
python scripts/self_check.py output_final.mp4 captions.srt
```

Checks: audio peak < 0 dBFS, no long silences > 3s, SRT count matches scene count,
video duration ≈ audio duration ± 0.5s.

If "audio peak above 0 dBFS": clamp with `alimiter=limit=0.95` before mux.  
If "long silence at Ns": regenerate that scene's WAV (cached scenes skip automatically).
