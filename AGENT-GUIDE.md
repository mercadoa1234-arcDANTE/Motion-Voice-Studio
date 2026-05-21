# MVS Agent Guide

**Agents: read this file first.** This is the meta-skill for using Motion-Voice-Studio. It tells you what to load when, and what NOT to load.

The rest of the repo is reference material for deeper dives. If you load everything at once, you burn ~25,000 tokens for what most tasks only need ~500 of.

---

## What MVS is (2 lines)

MVS turns a JSON storyboard into a narrated animated video. Local CPU only.
Audio is generated first (Kokoro TTS); frames are timed to match the measured audio.

---

## First-time setup (do once, skip if already done)

```bash
bash setup.sh                          # apt + pip + assembles Kokoro model
python3 scripts/mvs_doctor.py          # confirm health
```

If `mvs_doctor.py` returns any FAIL, fix that first. Each FAIL prints a one-line remediation. After setup, the doctor should return `19 pass · 0 warn · 0 fail`.

---

## Load every time

Just these:

1. **This file** — you're reading it
2. **`examples/smoke.storyboard.json`** — minimal schema reference (~30 lines)
3. The user's storyboard JSON, if they have one

That's the cold-load floor for any video task. Everything below is opt-in by situation.

---

## DO NOT auto-load

These are valid parts of the repo, but loading them up front bloats context for no benefit. Load them only when the user's task explicitly involves them.

| Path | When to load |
|---|---|
| `brain/` | Only when the task is genuinely complex, novel, and you've been stuck >300 tokens. Brain is opt-in cognition. |
| `handoffs/` | Only for SAM3D body/object capture or reconviagen 3D recon tasks. |
| `MVS-README-DOCS-FOR-AGENTS-START-HERE/BROWSER.md` | Only for WebGPU / Hunyuan3D 3D reconstruction. |
| `MVS-README-DOCS-FOR-AGENTS-START-HERE/CAD.md` | Only when scenes need build123d / pyvista 3D mechanism. |
| `scripts/render_cad_v2.py`, `scripts/exploded_view.py`, `scripts/render_orbit.py`, `scripts/render_still.py`, `scripts/assembly_schema.py`, `scripts/drawing_2d.py` | CAD module — only with CAD tasks. |
| `scripts/recon_handoff.py`, `scripts/source_doc_pass.py` | Only with the matching task type. |
| `Kokoro_Model_Split_Files/` | Source artifacts for `combine.py`. Never read these directly. |
| `model/`, `voices/` | Run-time binaries. Never read these directly. |

---

## Storyboard schema (the minimum you need to remember)

```json
{
  "title": "Lesson Title",
  "output": { "basename": "lesson", "dir": "/tmp/lesson-out" },
  "video": { "width": 1280, "height": 720, "fps": 30 },
  "default_voice": "af_bella",
  "default_speed": 1.0,
  "shots": [
    {
      "id": "intro",
      "narration": "Spoken text for this scene. Use commas for natural cadence; one Kokoro call per shot.",
      "voice": "af_bella",
      "speed": 1.0,
      "captions": true,
      "action": {
        "kind": "title",
        "primary": "Hello"
      }
    }
  ]
}
```

`shots` and `scenes` are interchangeable at the top level — code accepts either after the setup-easy patch. Use `shots` in new work to match the function APIs.

---

## The 6 scene kinds (`action.kind`)

| kind | what it does | required action fields | optional |
|---|---|---|---|
| `title` | big title card | `primary` | `secondary`, `subtitle` |
| `formula` | LaTeX equation reveal | `tex` | `annotations`, `position`, `use_mathtex` |
| `bullets` | titled bullet list | `items` (array) | `title` |
| `highlight` | callout box with arrow | `text` | `subtitle`, `position`, `box` |
| `lower_third` | bottom banner | `title`, `subtitle` | — |
| `custom` | raw Manim Scene | `code` (Python string), `scene_name` | — |

Full builders: `scripts/manim_scenes.py` (~200 lines). Read it when the user wants a kind beyond the defaults.

---

## The 12 voices (bundled, no network)

`af_bella` (NaN-safe default · use this unless asked otherwise) · `af_heart` (warm, default per Core Contract) · `af_nicole` · `am_fenrir` · `am_michael` (use speed ≥ 1.0 only — NaN below) · `am_puck` · `bf_emma` · `bm_daniel` · `bm_george` · `jf_alpha` · `pf_dora` · `zf_xiaoyi`.

Speed range: 0.85–1.15. If a voice produces NaN audio at any speed, fall back to `af_bella` at speed 1.0. The fallback is built into `voiceover.py`'s NaN guard.

---

## Subtitle discipline (non-negotiable)

```
✓  write_srt(timeline, "captions.srt")
✓  ffmpeg ... -c:s mov_text          ← soft-sub track in MP4
✗  ffmpeg -vf subtitles=...           ← NEVER. burns pixels.
✗  hardcoded Manim Text() as subtitles ← NEVER as the caption track.
```

Manim `Text()` objects on screen are visual callouts. The caption track is separate. Always.

Note: there are two `write_srt()` functions in the repo with slightly different signatures:

- `scripts/voiceover.py:write_srt(timeline_dict, path)` — takes the dict returned by `plan_timeline`. **Use this in the standard pipeline.**
- `engines/text_display.py:write_srt(timeline_shots_list, path)` — takes a flat list of shot dicts with `start_time`/`end_time`/`narration` fields. Use only if you're hand-rolling timeline shots.

Default to the `voiceover.py` one. The `text_display.py` one exists for cases where you need to write captions without running the full `plan_timeline`.

---

## The pipeline in code (paste-able)

```python
import sys
sys.path.insert(0, "scripts")
from voiceover import (
    generate_narration, plan_timeline,
    mix_audio_timeline, write_srt, mux_final
)
from render_manim import render_action

shots = storyboard.get("shots") or storyboard.get("scenes")

# 1. AUDIO FIRST — synthesize, measure real durations
records = generate_narration(shots, out_dir="narration/")

# 2. Plan timeline from MEASURED durations (not estimates)
timeline = plan_timeline(shots, records,
                          pacing=storyboard.get("voiceover", {}).get("pacing"))

# 3. SRT now — derived from the same durations
write_srt(timeline, "captions.srt")

# 4. Mix all per-shot audio onto one bus
mix_audio_timeline(timeline, "audio_master.wav")

# 5. Render each shot's frames matching shot["video_duration"]
for ts in timeline["shots"]:
    if ts["is_silent"]:
        continue
    # Build the action's Manim Scene, render to PNG sequence
    render_action(ts_to_action(ts), out_dir=f"frames/{ts['id']}", fps=30, quality="qm")

# 6. Mux — frames + mastered audio + soft-sub SRT
mux_final(
    frames_glob="frames/*/frame_%04d.png",   # adjust to your layout
    fps=30,
    audio_path="audio_master.wav",
    out_path="final.mp4",
    captions_srt="captions.srt",            # soft-sub (default)
    apply_audio_master=True,
    target_lufs=-14.0,
)
```

The `ts_to_action` step is a no-op when shots have an `action` dict — most do. CAD shots have an `engine` field that routes to `pyvista`/`build123d` builders instead; load `CAD.md` only if you're doing that.

---

## Decision tree: load what when

| User intent / task | Files to load (in addition to this guide) |
|---|---|
| "Make a video / lesson / explainer about X" | `examples/smoke.storyboard.json` only |
| "Make a video from this paper / PDF" | + `scripts/source_doc_pass.py` (header for API) |
| "Show animated 3D mechanism / CAD" | + `MVS-README-DOCS-FOR-AGENTS-START-HERE/CAD.md` + `scripts/render_cad_v2.py` (header) |
| "Use WebGPU / Hunyuan3D for reconstruction" | + `MVS-README-DOCS-FOR-AGENTS-START-HERE/BROWSER.md` + `handoffs/` templates |
| "Capture body or object with SAM3D" | + `handoffs/sam3d_*_RUN.md.template` |
| "I need fine audio control" | + `MVS-README-DOCS-FOR-AGENTS-START-HERE/AUDIO.md` |
| "I need to tune rendering / engines" | + `MVS-README-DOCS-FOR-AGENTS-START-HERE/RENDER.md` |
| "Text overlap / kerning issues" | + `MVS-README-DOCS-FOR-AGENTS-START-HERE/TEXT_DISPLAY.md` |
| "Something is broken" | Run `python3 scripts/mvs_doctor.py`. Read FAIL hints. No docs needed. |
| "Explain the full audio-first pipeline" | + `MVS-README-DOCS-FOR-AGENTS-START-HERE/PIPELINE.md` |
| "What's the full schema?" | + `MVS-README-DOCS-FOR-AGENTS-START-HERE/Core Production Contract - Readme Second.md` |
| Complex, novel, you're stuck >300 tokens | (only then) `brain/SKILL.md` for cognitive orchestration |

If the user's request fits two rows, load the union. If it fits none of these, you probably need only this guide plus the smoke storyboard.

---

## Common failures (fast fixes)

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError: kokoro-v1_0_fp16.onnx` | Model not assembled | `bash setup.sh` (assembles from split parts) |
| `ModuleNotFoundError: manim` (or similar) | pip deps missing | `pip install -r requirements.txt` |
| `pangocairo >= 1.30.0 is required` | apt deps missing | `bash setup.sh` (re-runs apt) |
| `NaN` samples in synthesized audio | Voice/speed combo (e.g. `am_michael` at < 1.0) | Switch to `af_bella` at speed 1.0 |
| `MathTex` renders blank or errors | LaTeX not installed | `apt install texlive-latex-extra` or use `Text()` |
| Storyboard fails `KeyError: 'shots'` | Storyboard uses `"scenes"` key (older docs) | Already supported post-patch; double-check the patch applied |
| Audio doesn't match video length | You rendered first, stretched audio | **Audio-first**: always synthesize, measure, then render to match |

Anything else: `python3 scripts/mvs_doctor.py` first, then read the FAIL hint.

---

## Spirit of MVS (the non-obvious rules)

1. **Audio is the timing source of truth.** Never guess durations from word count. Always synthesize first, measure the WAV, then render frames to match. The whole pipeline is built around this.

2. **Subtitles are always soft-sub.** Pixel-burned subtitles are forbidden. The viewer must be able to toggle them off.

3. **Phrase chunking matters.** "No three. No six. No nine." synthesized as three separate calls breaks prosody. Group related phrases into one Kokoro call so its internal rhythm handles commas. The `phrase_chunker` does this automatically when you use `generate_narration`.

4. **Cache invalidation is by content hash.** Re-rendering the same scene with the same params is free. Changing one word of narration rebuilds only that shot.

5. **Use `TextDisplayEngine` for all text in scenes.** Kerning, overlap detection, bottom-safe subtitle placement. Import: `from engines.text_display import TextDisplayEngine, write_srt`.

6. **One iteration on CPU is ~30s for a short scene.** Tweak narration → re-run audio (cached if unchanged) → re-render frames → re-mux. Adjust `kern_scale` between iterations.

---

## After you've done the task

If you produced a `final.mp4`, the sidecar `final.srt` should sit next to it (auto-created by `mux_final`). If you ran the smoke storyboard end-to-end and got both files, the install is verified for real, not just for audio.

**Iterate, don't restart.** Cache means re-runs are cheap. Don't blow away `~/.cache/cad-studio-voiceover/` unless something's wrong with it.
