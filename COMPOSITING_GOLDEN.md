# Voiceover and timing

## Audio-first contract

The narration is generated or estimated before rendering. Scene durations are derived from the real audio files.

```txt
cad_video.json scenes
  ↓
generate_audio.py
  ↓
scene wav files + timing.json + full_mix.wav
  ↓
renderer reads timing.json
  ↓
mux.py combines silent video + full_mix.wav
```

## Engines

| Engine | Use when | Notes |
|---|---|---|
| `auto` | Default | Try configured external command, Kokoro assets, OS TTS, then silence/timing estimate. |
| `kokoro` | Offline neural TTS assets are present | Best quality local path when model/voice files are supplied. |
| `espeak-ng` | Linux TTS is installed | Useful for timing and rough narration. |
| `say` | macOS local render | Good for user-side audio preview. |
| `external` | User gives a command or audio files | Use `CAD_VIDEO_TTS_CMD` or scene audio paths. |
| `browser_speech` | Browser-only prototype | Preview only unless captured with browser audio. |
| `silent` | User wants no voice | Generates silence and timing estimates. |

## Scene text rules

- 8–50 words per scene.
- Spoken text only.
- No `[pause]`, stage directions, or SSML unless the configured engine supports it and the plan declares SSML.
- Split long narration into multiple scenes.
- Use a separate no-narration scene for long visual pauses.

## Timing file

`outputs/audio/timing.json`:

```json
{
  "sample_rate": 24000,
  "full_mix": "outputs/audio/full_mix.wav",
  "scenes": [
    {
      "id": "overview",
      "audio": "outputs/audio/scene_overview.wav",
      "duration_s": 8.42,
      "gap_after_s": 0.18,
      "start_s": 0.10,
      "end_s": 8.52
    }
  ],
  "total_duration_s": 9.20
}
```

## External TTS command

Set:

```bash
export CAD_VIDEO_TTS_CMD='my_tts --text {text} --out {out}'
```

`generate_audio.py` will replace `{text}` and `{out}`. The command must write a WAV file.

## Kokoro integration

If a sibling voice skill or supplied model exists, use it. Expected locations:

```txt
cad-animation-voice-studio/model/kokoro-v1.0.fp16.onnx
cad-animation-voice-studio/voices/*.pt
../manim-voice-studio/model/kokoro-v1.0.fp16.onnx
../manim-voice-studio/voices/*.pt
```

If Kokoro assets are missing, do not invent them. Fall back to OS TTS or silent timing and state the limitation.

## Audio QA

Check:

- Every non-empty narration scene has a WAV.
- WAV duration is plausible for word count.
- No NaNs or silent files unless intentional.
- Full mix duration matches sum of scenes plus gaps.
- Final video audio does not clip.

## Narration style

For CAD videos, use operational language:

- “This face carries the load.”
- “The holes locate the bracket before the screws clamp it down.”
- “The exploded view separates the fasteners from the body.”

Avoid generic filler:

- “This is a very interesting model.”
- “As you can see...”
- “Basically...”

## Browser speech caveat

Browser SpeechSynthesis is useful for quick demos but not stable enough for exact final timing across machines. For final synchronized work, capture the browser audio with the video or use a generated WAV in the sandbox.
