# Troubleshooting

Lessons from extensive iteration. When one of these symptoms appears, the cause is almost always one of these.

## Setup phase

### `verify_setup.sh` says model file is missing

The user uploaded weights to `/mnt/user-data/uploads/` but the script didn't find the right filename. Filenames the script accepts (any one of these):

- `kokoro-v1.0.fp16.onnx` (recommended, ~156 MB)
- `model_fp16.onnx` (huggingface upload name, will be renamed)
- `kokoro-v1.0.onnx` (fp32, ~325 MB; works but bigger)

Voice files are accepted as `<voice_id>.pt` only. If they're named differently (e.g., `af_bella_v1.pt`), rename to match.

### `verify_setup.sh` says espeak-ng is missing

Run `apt-get install -y espeak-ng espeak-ng-data libespeak-ng1`. The skill cannot phonemize without it.

### `verify_setup.sh` says LaTeX is missing

Manim's `MathTex` requires a TeX install. On Ubuntu: `apt-get install -y texlive-extra-utils dvisvgm`. If the user is on a system without LaTeX, the renderer falls back to `Tex` for plain text and refuses to render `formula` actions; warn them up front.

## Audio generation phase

### A scene's audio is all NaN / silent / clipped to 1.0

Almost always fp16 overflow. The engine in this skill detects NaN after every `sess.run` and falls back to chunked synthesis. If chunked synthesis still produces NaN:

1. Check the voice's `speed` in the cast — is it `< 1.0` and the voice is `bm_daniel`? Set to 1.0.
2. Check the narration text — is it longer than 50 words in a single sentence? Add periods to break it up.
3. Last resort: switch the scene's voice to `af_bella` which doesn't exhibit the issue.

The issue is documented in the engine code; it's a known fp16 quantization artifact for that specific voice tensor.

### Audio is silent (zero RMS) but no NaN

The phonemizer dropped all characters — usually because the text is in a language espeak-ng didn't recognize, or because the text is pure punctuation/numbers. Inspect the phoneme output:

```python
from phonemizer.backend import EspeakBackend
print(EspeakBackend('en-us').phonemize(['your text here'])[0])
```

If empty, rewrite the narration in plain words. Spell out numbers, math symbols, etc.

### Audio is clipping (peak == 1.0)

The engine peak-normalizes to −1 dBFS before writing. If you still see clipping in the final mux output, it's the `loudnorm` filter pushing levels back up to broadcast targets. That's intended; broadcast loudness IS at the edge of digital headroom.

## Manim render phase

### LaTeX error: "Undefined control sequence \something"

The TeX expression uses a macro your installation doesn't have. Common offenders:

- `\mathbb{...}` requires `amssymb` package.
- `\boldsymbol{...}` requires `amsmath` or `bm`.
- Custom commands you forgot to define.

Replace with a more basic alternative, or wrap the unfamiliar macro in plain Tex.

### Manim says "Mobject ... is off-screen"

The plot's `x_range` / `y_range` is too tight. Recipes default to comfortable framing; if you overrode it, expand by ~20% on each side.

### Manim render is taking forever (> 5 minutes for a 2-minute video)

- Check `quality` setting. Default is `medium_quality`. Don't use `high_quality` unless there's a specific reason.
- Are you using `kind: "custom"` with heavy 3D? Drop to `kind: "axes_plot"`.
- Disk full? Manim's intermediate frames eat space.

### Render produces a video shorter than expected

Some action recipe ran out of animation steps before the audio's `wait()` finished — that's *fine*, the wait fills the gap. If the render is shorter than the audio + gaps, the renderer skipped a `wait()`. Inspect the generated scene file and rerun.

## Mux phase

### "audio total duration mismatches video duration"

The renderer and the audio generator are out of sync — usually because someone edited `audio/timing.json` by hand, or `lesson.json` changed without rerunning generation. Fix:

```bash
rm -rf audio/
python scripts/generate_audio.py lesson.json
python scripts/render_manim.py lesson.json
python scripts/mux.py lesson.json
```

### Final video has no audio stream

The video file existed but `mux.py` failed silently. Check `mux.py`'s exit code. Common cause: output path is in a directory that doesn't exist. Use `/mnt/user-data/outputs/` which is guaranteed.

## Self-check phase

### Self-check reports "audio peak above 0 dBFS"

Should not happen with the current loudnorm settings. If it does, clamp the audio before mux:

```bash
ffmpeg -i input.mp4 -af "alimiter=limit=0.95" -c:v copy clamped.mp4
```

### Self-check reports "long silence at offset N seconds"

Either a missing scene (check the timing.json against lesson.json scene count) or a generated scene with very low RMS. Regenerate that specific scene only:

```bash
rm audio/scene_<id>.wav
python scripts/generate_audio.py lesson.json
```

Cached scenes for unchanged content skip; only the deleted one regenerates.

## Disk pressure

The skill bundle is ~160 MB. The intermediate `audio/` dir adds ~5-20 MB. Manim's `media/` dir adds ~10-50 MB. If the sandbox is tight on disk:

- Delete `media/videos/<scene>/<quality>/partial_movie_files/` after each render — these are intermediate frames Manim needs only during render.
- The `~/.cache/manim-voice-studio/` cache can be cleared between runs without loss (just slower next time).
- Don't keep both fp32 and fp16 model variants. Drop one.

## When in doubt

The pipeline is broken into stages with cached outputs precisely so individual stages can be re-run without redoing upstream work. The right response to almost any failure is:

1. Identify which stage failed (audio gen / render / mux / self-check).
2. Look at the cached outputs of the previous stages — are they good?
3. Re-run only the failing stage.

Avoid the "delete everything and start over" instinct. It wastes time and you'll usually re-hit the same failure.
