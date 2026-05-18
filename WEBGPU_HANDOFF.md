# Voice-Over and Captions

## The audio-first discipline

**Generate audio first, measure actual durations, drive video timing from there.**
This is the construction guarantee of the pipeline — video duration always
equals (audio duration + planned gaps), never the reverse. The "shot ran out of
frames before narration finished" failure mode is eliminated by construction.

The orchestrator in `scripts/storyboard.py` does this automatically:

1. Generate per-shot narration WAVs.
2. Measure each WAV's actual duration.
3. Compute the timeline with leading silence and inter-shot gaps.
4. Render video frames for each shot at the timeline-derived duration.
5. Concatenate frames, mix audio onto the timeline, mux to MP4.

You can also call the pieces directly:

```python
from voiceover import generate_narration, plan_timeline, mix_audio_timeline, mux_final, write_srt

records  = generate_narration(shots, "narration/", engine="kokoro", default_voice="af_bella")
timeline = plan_timeline(shots, records)                      # gaps, total duration
mix_audio_timeline(timeline, "narration_mixed.wav")
write_srt(timeline, "captions.srt")
# ... after rendering frames per timeline['shots'][i]['video_duration'] ...
mux_final("frames_concat/frame_%05d.png", fps, "narration_mixed.wav", "final.mp4",
          captions_srt="captions.srt", burn_in=True)
```

## Default engine: Kokoro-82M ONNX

The skill ships a 156 MB Kokoro fp16 ONNX model and 7 voice embeddings. **It runs
CPU-only at ~1× realtime on the sandbox** (a 5-second narration generates in
~5 s wall clock). Quality is genuinely neural — beats gTTS in clarity and beats
espeak by a wide margin.

```python
from kokoro_engine import KokoroEngine
eng = KokoroEngine("model/kokoro-v1.0.fp16.onnx", "model/config.json", "voices")
audio, sr = eng.synthesize("Sun gear, twenty teeth.", voice="af_bella")
# audio is a float32 numpy array at 24000 Hz
```

Built-in resilience:
- fp16 overflow on long sequences → automatic chunk-and-retry.
- Phonemizer dropout → quality gate detects near-silent output and warns.
- Voice cache keyed by (text, voice, speed, lang) → re-runs hit the cache instantly.

### Setup

Run `scripts/verify_setup.sh` once. It:
- Installs `onnxruntime`, `phonemizer-fork`, `soundfile`, `espeak-ng` if missing.
- Stages Kokoro assets from `/mnt/user-data/uploads/` if found (for fresh sandboxes).
- Runs a smoke synthesis to confirm the chain works.

If the smoke test fails, the script prints the one upload instruction to fix it.

## Fallback engines

### gTTS (online, MP3)

If the user is offline and Kokoro assets are gone, or if they want a specific
gTTS-only voice (regional `tld`), pass `engine="gtts"` to `generate_narration`:

```python
records = generate_narration(shots, out_dir, engine="gtts", default_lang="en-us")
```

Notes:
- Needs network. May fail in offline sandboxes.
- Single-voice (gTTS has accents via `tld` but no neural voice cast).
- Output is MP3, converted to WAV-24k-mono internally for consistency.

### espeak-ng (offline, robotic)

If both Kokoro and gTTS fail, the synthesizer of last resort. Not exposed as a
first-class engine; you'd call it directly:

```bash
espeak-ng -v en+f3 -s 165 -w shot.wav "Sun gear, twenty teeth."
```

Use only when the pipeline must keep going and quality is acceptable.

## Voice selection

See `references/VOICES.md` for the full catalog. Headline picks:

| Voice | Use |
|---|---|
| **af_bella** ⭐ | Default narrator. Warm, articulate. American female. |
| **bm_daniel** | British male, professor cadence. Great contrast as second voice. |
| **am_onyx** | Documentary American male. Use for serious/technical content. |
| **am_echo** | Conversational American male. Co-host energy. |
| **af_sky** | Lighter American female. Niche. |
| **am_liam** | Younger American male. |
| **pf_dora** | Brazilian Portuguese female. |

### Multi-voice (dialog) shots

Per-shot override:

```json
{
  "id": "exchange",
  "narration": "Why does the planet carrier need bearings here?",
  "voice": "bm_daniel",
  ...
}
```

The next shot can switch back. The pipeline gives the gap between shots the
`post_shot_gap_voice_change_ms` value (default 250 ms — a "speaker change" beat).
Same-voice transitions get 150 ms (natural breath).

## Pacing knobs

Override in the storyboard:

```json
{
  "voiceover": {
    "engine": "kokoro",
    "default_voice": "af_bella",
    "default_lang": "en-us",
    "pacing": {
      "leading_silence_ms": 100,
      "post_shot_gap_same_voice_ms": 150,
      "post_shot_gap_voice_change_ms": 250,
      "tail_silence_ms": 500
    },
    "burn_captions": true
  }
}
```

- **leading_silence_ms** — silence at the very start so visual changes register
  before the voice begins. 100 ms is the sweet spot.
- **post_shot_gap_same_voice_ms** — between shots with the same voice. Reads as
  natural breath.
- **post_shot_gap_voice_change_ms** — between shots with different voices. Gives
  a "speaker change" beat. Increase for slower pacing.
- **tail_silence_ms** — silence after the last shot, before video end. Avoids
  awkward hard-stops.

## Captions

The pipeline always writes a sidecar SRT. With `burn_captions: true` (default),
ffmpeg also burns them into the video.

Burn-in style is monospace-ish, white, 22pt with a black box behind for max
readability on white CAD backgrounds. Override via the ffmpeg
`subtitles=...:force_style=...` argument in `mux_final`.

## Pacing tone (when the user doesn't specify)

For CAD/engineering content:

- Pace: Kokoro's default (~150–165 WPM at speed=1.0) is correct for engineers.
- Tone: declarative, present tense. "The sun gear meshes with the planet gears."
- Numbers: spell out small (one, two); digits for measurements (8 mm, 27:1).
- Units: say them in full. "Forty-two grams" not "42g".
- No exclamations. The audience is engineers.

For entertainment / cinematic content:

- Wider tonal range allowed.
- Two voices is the sweet spot — adds interest without confusing the listener.
- Use `bm_daniel + af_bella` for documentary-narrator + co-host dynamic.

## Self-healing recipes

| Symptom | Cause | Fix |
|---|---|---|
| Kokoro audio is silent | Phonemizer dropped all chars (heavy punctuation, non-Latin) | Strip non-ASCII, simplify punctuation, retry |
| Kokoro audio has NaN | fp16 overflow on long sequence | Engine auto-chunks. If still failing, set `speed: 1.0` and shorten the narration |
| Voice not found | Voice .pt missing from `voices/` | Upload the .pt to `/mnt/user-data/uploads/` and rerun `verify_setup.sh` |
| ONNX init fails | Wrong onnxruntime version | `pip install --break-system-packages 'onnxruntime>=1.18,<2'` |
| Espeak not found | System package missing | `apt-get install -y espeak-ng` |
| Audio/video drift > 100 ms | Stale frames from a previous run | Delete `out_dir/frames_concat/` and rerun storyboard |
| gTTS HTTP error | Network blocked | Use Kokoro (it's the default) or wait and retry |
