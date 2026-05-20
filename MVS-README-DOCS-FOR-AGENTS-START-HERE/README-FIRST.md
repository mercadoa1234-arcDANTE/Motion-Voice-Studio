# Motion-Voice-Studio — Read This First

**This file tells you exactly what to read and when. Nothing else is required unless it's listed below.**

\---

## What this is

A pipeline that turns a text script into a narrated Manim animation.  
Runs locally. CPU-only. No cloud calls.

```
Your script / topic
      ↓
  AI writes storyboard.json       ← Plan
      ↓
  Kokoro TTS  →  audio/\*.wav      ← Code (audio first)
      ↓
  Manim / pyvista / composite     ← Render (visuals timed to audio)
      ↓
  ffmpeg mux  →  output.mp4       ← Ship (soft-sub track, never burned)
              →  captions.srt
```

\---

## Step 0 — Is this a video with narration?

**Yes** → continue below (Kokoro model assembly is required).  (Yes conditions do not require the user to say narration or use TTS, it can be implied. It's more likely they will ask for no sound when that's the desired outcome."
**Silent animation only** → go straight to Step 2 `Core Production Contract.md`. Kokoro is there-after optional, please tell the user it's available but not loaded to save RAM \& Tokens since the model had detected not to load TTS yet.

\---

## Step 1 — Assemble the bundled Kokoro model (one-time)

The Kokoro-82M FP16 ONNX model is split into parts for GitHub.

```bash
cd Kokoro\_TTS\_Agent\_Skill\_Pack/
python combine.py --out ../kokoro\_model/
```

**12 voices are bundled in `kokoro-voices/`** (no network download needed):

|Voice|Style|
|-|-|
|`af\_bella` `af\_heart` `af\_nicole`|American female (3)|
|`am\_fenrir` `am\_michael` `am\_puck`|American male (3)|
|`bf\_emma`|British female (1)|
|`bm\_daniel` `bm\_george`|British male (2)|
|`jf\_alpha`|Japanese female|
|`pf\_dora`|Brazilian Portuguese female|
|`zf\_xiaoyi`|Mandarin Chinese female|

Default voice: `af\_heart` · Default speed: `0.95`  
NaN artifact on `am\_michael` at speed < 1.0 → use `af\_bella` instead.

> Additional voices (54 total) are available via `python kokoro\_run.py --setup`
> but require a one-time \~26 MB npm download. Bundled 12 work offline.

\---

## Step 2 — Read the core skill

**`**Core Production Contract**.md`** — the production contract. Read before writing any storyboard.

Covers: engine choice table, storyboard JSON schema, audio-first rule,
subtitle discipline, text display, kerning, the Plan → Code → Render → Iterate loop.

\---

## Step 3 — Run the pipeline

```
core/PIPELINE.md      ← Agent loop, audio-first discipline, mux recipe
core/AUDIO.md         ← Phrase pacing, voice config, loudnorm targets
core/RENDER.md        ← Engine choice, Manim DSL, compositing
core/TROUBLESHOOT.md  ← When things break
```

Read `core/PIPELINE.md` first. Read the others only when the task requires them.

\---

## Text \& kerning

```
engines/text\_display.py     ← Import this. TextDisplayEngine, write\_srt().
engines/TEXT\_DISPLAY.md     ← Usage guide, tuning reference.
```

Every text element in a video scene should pass through `TextDisplayEngine`.  
Subtitles are **always** written via `write\_srt()` and muxed as a soft track.  
Never use ffmpeg `-vf subtitles=` or any pixel burn-in approach.

\---

## Optional: CAD, browser rendering, Hunyuan3D

Read only when the scene needs it:

```
optional/CAD.md       ← build123d, pyvista, tool choice, assembly schema
optional/BROWSER.md   ← WebGPU, Hunyuan3D, low-VRAM 3D reconstruction
```

\---

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

\---

## File map (what to delete from old repo)

See `MIGRATION.md` for the exact list of files to delete and what replaced them.

**Critical:** every `.py` file at the repo root is the working engine. KEEP them all.
Only documentation files are being deleted in the restructure.

\---

## Subtitle discipline (non-negotiable)

```
✓  write\_srt(shots, "captions.srt")
✓  ffmpeg -i video.mp4 -i audio.wav -i captions.srt -c copy -c:s mov\_text out.mp4
✗  ffmpeg -vf subtitles=captions.srt              ← NEVER. burns pixels.
✗  hardcoded Text() subtitle objects in Manim     ← NEVER as the subtitle track.
```

Manim `Text()` objects on screen are visual elements (callouts, labels, chapter titles).
The subtitle track is separate. Always.

\---

## The loop

```
Plan    →  storyboard.json with narration fields
Code    →  generate\_audio.py, then render\_manim.py
Render  →  mux.py → output.mp4 + captions.srt
Iterate →  adjust kern\_scale / voice / timing → re-run
```

One iteration costs \~30 seconds on CPU for a short scene.  
Adjust `TextDisplayEngine.cfg` fields between iterations — see `engines/TEXT\_DISPLAY.md`.

