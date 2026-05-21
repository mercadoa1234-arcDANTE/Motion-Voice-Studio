# Motion-Voice-Studio — Read This First

> **Agents:** read [`/AGENT-GUIDE.md`](../AGENT-GUIDE.md) first. That file is the meta-skill: tight task→file routing so you don't cold-load the whole repo. This document is the human-friendly walkthrough; agents only need it for deep-dive sections.

**This file tells you exactly what to read and when. Nothing else is required unless it's listed below.**

---

## What this is

A pipeline that turns a text script into a narrated Manim animation.
Runs locally. CPU-only. No cloud calls.

```
Your script / topic
      ↓
  AI writes storyboard.json       ← Plan
      ↓
  Kokoro TTS  →  audio/*.wav      ← Code (audio first)
      ↓
  Manim / pyvista / composite     ← Render (visuals timed to audio)
      ↓
  ffmpeg mux  →  output.mp4       ← Ship (soft-sub track, never burned)
              →  captions.srt
```

---

## Step 0 — Is this a video with narration?

**Yes** → continue below (Kokoro model assembly is required). Yes conditions do not require the user to say "narration" or "use TTS"; it can be implied. It's more likely they will ask for no sound when that's the desired outcome.
**Silent animation only** → go straight to Step 2 `Core Production Contract.md`. Kokoro is thereafter optional; tell the user it's available but not loaded to save RAM and tokens since the model detected TTS isn't needed yet.

---

## Step 0.5 — Install dependencies (one-time, idempotent)

**Linux / macOS:**

```bash
./setup.sh
```

**Windows (PowerShell, admin):**

```powershell
.\setup.ps1
```

What this does, in order:

1. Installs system tools via apt/brew/winget: `ffmpeg`, `espeak-ng`, `dvisvgm`, pango/cairo dev headers, poppler-utils, and (by default) TeX Live for MathTex
2. Installs pinned Python packages from `requirements.txt`
3. Calls `Kokoro_TTS_Agent_Skill_Pack/combine.py` to assemble the 156 MB Kokoro ONNX model from the 7 bundled split parts (SHA-256 verified)
4. Stages voices into `voices/`
5. Runs `verify_setup.sh` for an end-to-end smoke test

Safe to run twice. Skips anything already installed. If `setup.sh` fails on system packages, run with `INSTALL_LATEX=0 ./setup.sh` to skip the ~1 GB TeX Live download.

**Already set up and just want to check the install?** Use the read-only doctor:

```bash
python3 scripts/mvs_doctor.py
```

The doctor never installs anything. It just reports PASS/FAIL with a one-line remediation hint per check. Exit 0 means everything works.

---

## Step 1 — Assemble the bundled Kokoro model (one-time)

> If you ran `setup.sh` in Step 0.5, this is already done. Skip to Step 2.

The Kokoro-82M FP16 ONNX model is split into 7 parts for GitHub (each under 25 MB).

```bash
cd Kokoro_TTS_Agent_Skill_Pack/
python combine.py --out ../model/
```

The reassembler auto-discovers the `.partNN` files — they ship in `Kokoro_Model_Split_Files/` next to the manifest's directory. If your repo layout puts them somewhere unusual, pass `--parts-dir <path>`.

Output filename is `kokoro-v1_0_fp16.onnx` (matches the manifest). The previous dotted name `kokoro-v1.0.fp16.onnx` is still accepted by `voiceover.py` for one release as a deprecation fallback — rename when convenient.

**12 voices are bundled in `kokoro-voices/`** (no network download needed):

| Voice | Style |
|---|---|
| `af_bella` `af_heart` `af_nicole` | American female (3) |
| `am_fenrir` `am_michael` `am_puck` | American male (3) |
| `bf_emma` | British female (1) |
| `bm_daniel` `bm_george` | British male (2) |
| `jf_alpha` | Japanese female |
| `pf_dora` | Brazilian Portuguese female |
| `zf_xiaoyi` | Mandarin Chinese female |

Default voice: `af_heart` · Default speed: `0.95`
NaN artifact on `am_michael` at speed < 1.0 → use `af_bella` instead.

> Additional voices (54 total) are available via `python kokoro_run.py --setup`
> but require a one-time ~26 MB npm download. Bundled 12 work offline.

---

## Step 2 — Read the core skill

**`Core Production Contract.md`** — the production contract. Read before writing any storyboard.

Covers: engine choice table, storyboard JSON schema, audio-first rule,
subtitle discipline, text display, kerning, the Plan → Code → Render → Iterate loop.

---

## Step 3 — Smoke test the install

```bash
python3 scripts/voiceover.py examples/smoke.storyboard.json --out-dir /tmp/mvs-smoke
```

This is a two-scene, ~10-second storyboard. If it produces audio + frames without errors, the whole pipeline is wired correctly. If anything breaks, run `python3 scripts/mvs_doctor.py` to pinpoint which stage failed.

---

## Step 4 — Run the pipeline

```
core/PIPELINE.md      ← Agent loop, audio-first discipline, mux recipe
core/AUDIO.md         ← Phrase pacing, voice config, loudnorm targets
core/RENDER.md        ← Engine choice, Manim DSL, compositing
core/TROUBLESHOOT.md  ← When things break
```

Read `core/PIPELINE.md` first. Read the others only when the task requires them.

---

## Text & kerning

```
engines/text_display.py     ← Import this. TextDisplayEngine, write_srt().
engines/TEXT_DISPLAY.md     ← Usage guide, tuning reference.
```

Every text element in a video scene should pass through `TextDisplayEngine`.
Subtitles are **always** written via `write_srt()` and muxed as a soft track.
Never use ffmpeg `-vf subtitles=` or any pixel burn-in approach.

---

## Optional: CAD, browser rendering, Hunyuan3D

Read only when the scene needs it:

```
optional/CAD.md       ← build123d, pyvista, tool choice, assembly schema
optional/BROWSER.md   ← WebGPU, Hunyuan3D, low-VRAM 3D reconstruction
```

---

## Optional: Brain (cognitive orchestration)

Brain is **not required** for Motion-Voice-Studio.
It's a coordination layer for complex multi-step decisions and novel problem shapes.

Summon it when:

* You don't know the right architecture before building
* The task has real stakes (client-facing, regulatory, high-revision cost)
* You've been stuck in the same loop for > 300 tokens

```
brain/SKILL.md        ← Brain + Natural-Mind + Grill + Rigor in one file
```

Brain is silent. It routes internally. Call `/brain` once; it handles the rest.
Do not manually chain brain sub-skills — overhead without benefit.

---

## File map (what to delete from old repo)

See `MIGRATION.md` for the exact list of files to delete and what replaced them.

**Critical:** every `.py` file at the repo root is the working engine. KEEP them all.
Only documentation files are being deleted in the restructure.

---

## Subtitle discipline (non-negotiable)

```
✓  write_srt(shots, "captions.srt")
✓  ffmpeg -i video.mp4 -i audio.wav -i captions.srt -c copy -c:s mov_text out.mp4
✗  ffmpeg -vf subtitles=captions.srt              ← NEVER. burns pixels.
✗  hardcoded Text() subtitle objects in Manim     ← NEVER as the subtitle track.
```

Manim `Text()` objects on screen are visual elements (callouts, labels, chapter titles).
The subtitle track is separate. Always.

---

## The loop

```
Plan    →  storyboard.json with narration fields
Code    →  generate_audio.py, then render_manim.py
Render  →  mux.py → output.mp4 + captions.srt
Iterate →  adjust kern_scale / voice / timing → re-run
```

One iteration costs ~30 seconds on CPU for a short scene.
Adjust `TextDisplayEngine.cfg` fields between iterations — see `engines/TEXT_DISPLAY.md`.

---

## When things go wrong

1. **`python3 scripts/mvs_doctor.py`** — pinpoints which stage is broken
2. **`./scripts/verify_setup.sh`** — re-runs install for anything missing
3. **`core/TROUBLESHOOT.md`** — common failure modes and fixes
