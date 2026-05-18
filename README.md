# motion-voice-studio

The unified AI teaching skill. CAD + Manim + Voice + Image Insertion in
one pipeline.

The AI plans all the shots & scripts. Each shot, the AI picks its render engine. The orchestrator dispatches per shot. Audio
is generated first; video timing follows to be synced to audio markers.

---

The ultimate teaching-studio skill. Generate complete narrated educational, scientific, and engineering videos that combine: parametric CAD (build123d) with exploded views and orbital cameras (pyvista), Manim motion graphics and equation reveals, source-document image insertion (PDF page screenshots, Substack post screenshots, photographs, figures), composite overlays, AI-driven 3D reconstruction handoffs, and high-fidelity browser-GPU renders — all narrated with bundled neural Kokoro-82M CPU TTS (seven voices, no network).

## v3 changelog vs v2

The five concrete fixes from May 2026 production review:

1. **Phrase-aware Kokoro chunker.** v2's per-sentence synthesis produced choppy delivery for short phrase rhythms ("Never three. Never six. Never nine." → 3 calls + 320ms silences = stilted). v3 keeps related phrases in one Kokoro call so its prosody handles them naturally. See `references/PHRASE_PACING.md`.

2. **Soft-sub MP4 default.** v2 baked SRT into pixels. v3 ships subtitles as a `mov_text` track inside the MP4 + a sidecar `.srt` alongside the file. User toggles in player. Manim animated text on screen is still part of the picture; only the player-overlay subtitle pixels were removed.

3. **Audio mastering.** v2 shipped raw Kokoro output (variable -23 to -18 LUFS). v3 applies a two-pass loudnorm to -14 LUFS (video) / -16 LUFS (podcast) + `afftdn` denoise + optional subtle reverb. Runs in ffmpeg, no DAW required. See `references/AUDIO_MASTER.md`.

4. **Source-document flow.** v3 adds `scripts/source_doc_pass.py` — ingests a PDF or URL, extracts page screenshots, embedded figures, header metadata, acknowledgements, references. The storyboard references these as `image` shots. Result: a video that SHOWS its sources. See `references/SOURCE_DOC_FLOW.md`.

5. **Image-shot engine.** New render engine (`engine: "image"`) for image-driven shots (source pages, photographs, figures, slides) with letterboxing, optional Ken Burns, fade in/out. See `references/IMAGE_SHOT_ENGINE.md`.

Plus: explicit agent loop discipline (`/brain` plan → `/grill` only when stuck → continue-on-tool-limit). See `references/AGENT_LOOP.md`.

---

## Drag-and-drop install

```bash
# 1. Unzip into the skills directory of your sandbox (or any working dir)
unzip motion-studio-v3.zip
cd motion-studio-v3

# 2. Run setup (idempotent — installs deps, smoke-tests every engine)
bash scripts/verify_setup.sh

# 3. (Optional, if you have a source paper) ingest it
python scripts/source_doc_pass.py path/to/paper.pdf \
    --out /home/claude/production/myproject/assets/source_docs/myref/

# 4. Author your storyboard JSON (see SKILL.md "Unified storyboard schema")
#    OR let Claude write it with /brain after reading your source paper.

# 5. Render
python scripts/storyboard.py /home/claude/production/myproject/storyboard.json \
    --out /home/claude/production/myproject/output

# Output: final.mp4 (with mov_text subtitle track) + final.srt (sidecar)
```

That's it. The pack includes the Kokoro-82M model (163 MB) and 7 voices, so
no network is needed.

---

## What it produces

Narrated educational / engineering MP4s combining any of:

- **Parametric solid CAD** via **build123d** (OCCT-Python, exact STEP/STL)
- **Exploded-view animations** via **pyvista** (offscreen Mesa OpenGL on CPU)
- **Manim motion graphics** — title cards, equation reveals, bullets, lower-thirds
- **Composite shots** — pyvista CAD as base with manim/math/text overlays per-frame
- **2D engineering drawings** → DXF + PDF
- **BOM tables** (matplotlib)
- **Image shots** [v3] — source-paper pages, photographs, figures, slides, with caption + attribution + Ken Burns
- **AI-reconstructed meshes** (ReconViaGen, SAM 3D Objects/Body, Hunyuan3D, TRELLIS) via the handoff protocol

All narrated with **bundled Kokoro-82M** neural CPU TTS (7 voices, no network).
Mastered to **-14 LUFS** with gentle denoise. Subtitles as **soft-sub track + sidecar SRT**.

---

## Sandbox reality

- **4 GB RAM, 1 CPU core, no GPU**
- Everything in the default backbone runs in-sandbox
- Heavy AI 3D reconstruction is handed off to the user's machine
- LaTeX is **optional** (~1 GB); manim falls back to pango `Text()` without it
- PDF tools (`pdftoppm`, `pdftotext`, `pdfimages`, `pdfinfo`) are required for source-doc ingest and present in Anthropic sandbox by default

---

## First-time setup

```bash
bash scripts/verify_setup.sh
```

Checks for: `build123d`, `pyvista`, `manim`, `ffmpeg`, `Pillow`, PDF tools, Kokoro model + voices, voice synthesis smoke test. Idempotent. Run again whenever a sandbox refreshes.

---

## File layout

```
motion-studio-v3/
├── SKILL.md                      Full skill spec — agent reads this first
├── README.md                     This file
├── references/                   Topical guides (read on demand)
│   ├── AGENT_LOOP.md             [v3 NEW] /brain plan → /grill → continue
│   ├── PHRASE_PACING.md          [v3 NEW] Kokoro phrase chunker discipline
│   ├── AUDIO_MASTER.md           [v3 NEW] LUFS + denoise + reverb recipe
│   ├── SOURCE_DOC_FLOW.md        [v3 NEW] PDF/URL ingest → video flow
│   ├── IMAGE_SHOT_ENGINE.md      [v3 NEW] image-driven shot reference
│   ├── TOOL_CHOICE.md            Decision tree for every tool
│   ├── PIPELINES.md              Copy-paste skeletons per output class
│   ├── ASSEMBLY_SCHEMA.md        Multi-part assembly format
│   ├── COMPOSITING.md            Overlay playbook
│   ├── COMPOSITING_GOLDEN.md     Golden-ratio layout zones
│   ├── MANIM_PATTERNS.md         manim_action DSL recipes
│   ├── TEACHING.md               Pacing and structure
│   ├── MANIM_TROUBLESHOOTING.md  manim failure recovery
│   ├── VOICEOVER.md              Audio-first pipeline
│   ├── VOICES.md                 Kokoro voice catalog
│   ├── AI_HANDOFF.md             ReconViaGen / SAM 3D templates
│   ├── WEBGPU_HANDOFF.md         Browser-render handoff
│   └── cav/                      Legacy cad-studio refs (still valid)
├── scripts/
│   ├── verify_setup.sh           Run once per fresh sandbox
│   ├── kokoro_engine.py          Bundled Kokoro-82M ONNX wrapper
│   ├── phrase_chunker.py         [v3 NEW] paragraph/phrase splitter
│   ├── voiceover.py              Audio-first narration + timeline + soft-sub mux
│   ├── audio_master.py           [v3 NEW] LUFS norm + denoise + reverb
│   ├── source_doc_pass.py        [v3 NEW] PDF/URL → pages/figures/metadata
│   ├── image_shot.py             [v3 NEW] image-driven shot renderer
│   ├── storyboard.py             Multi-engine orchestrator
│   ├── render_manim.py           manim render driver
│   ├── manim_scenes.py           manim scene builder library
│   ├── compositor.py             Per-frame composite, overlays
│   ├── exploded_view.py          Schema-driven exploded animation
│   ├── assembly.py               Schema validator + GLB exporter
│   ├── render_still.py           Single iso PNG
│   ├── render_orbit.py           Orbital animation
│   ├── render_cad_v2.py          Golden-ratio composited CAD render
│   ├── self_check_v2.py          QA gates A-F
│   ├── drawing_2d.py             Orthographic → DXF/PNG/PDF
│   ├── recon_handoff.py          AI 3D recon job preparer
│   ├── webgpu_handoff.py         Browser-render handoff
│   ├── golden_layout.py          φ-grid math
│   └── headless.py               Xvfb display context manager
├── handoffs/                     Per-model RUN.md templates
├── model/
│   ├── kokoro-v1.0.fp16.onnx    Bundled Kokoro (~163 MB)
│   └── config.json
├── voices/                       7 .pt voice files (~3.7 MB)
│   ├── af_bella.pt   af_sky.pt
│   ├── am_echo.pt    am_liam.pt   am_onyx.pt
│   ├── bm_daniel.pt  pf_dora.pt
└── examples/                     Runnable references (Gundam-mecha demo)
```

---

## Typical run

A 4-chapter educational series adapting a Substack post takes roughly:

| Phase | Wall-clock (4 GB / 1 CPU sandbox) |
|---|---|
| Source-doc ingest | ~10s for a 14-page PDF |
| Storyboard authoring (by Claude) | depends on complexity, usually 5-10 min |
| Audio synthesis (Kokoro, ~6 min of narration per chapter) | ~4-5 min per chapter |
| Frame rendering (custom Manim + image shots) | ~5-10 min per chapter |
| Audio master + soft-sub mux | ~30s per chapter |
| **Total per chapter** | **~12-18 min** |

Four chapters → ~1 hour. Use the `continue` loop when tool-call limits force a checkpoint.

---

## Agent loop (the way to drive this)

Documented in detail at `references/AGENT_LOOP.md`. Short version:

1. **Drop the source paper + the v3 pack into the sandbox.**
2. **`/brain` scores the task** (silently). For a typical source-paper adaptation, expect 2+ High → Pattern 2 (right hemisphere finds the frame, left hardens it).
3. **`/brain` writes the plan** (storyboard JSON) reading the paper.
4. **`/grill` self-checks** the plan — asks user only if a question genuinely cannot be answered from source + docs.
5. **Execute** — Kokoro audio first, render frames per engine, master audio, mux soft-sub.
6. **On tool-limit reached**, checkpoint, report honestly, wait for "continue".

---

## Trigger phrases that route here

- "make a teaching video"
- "explain X with animation and narration"
- "narrate this paper / Substack post into a video"
- "3blue1brown style explainer"
- "CAD walkthrough with formulas on screen"
- "design and animate a part with the math overlaid"
- "build a lesson from this source document"
- "adapt this PDF into an animated explainer"

---

## License & attribution

Bundled assets:
- **Kokoro-82M** TTS model: given MIT license by the model authors.
- **build123d, pyvista, manim, ffmpeg, Pillow**: open-source, see respective licenses.

All other Motion Voice Studio code is MIT liscensed.
