---
name: motion-studio
description: >
  v3 · The ultimate teaching-studio skill. Generate complete narrated
  educational, scientific, and engineering videos that combine: parametric
  CAD (build123d) with exploded views and orbital cameras (pyvista), Manim
  motion graphics and equation reveals, source-document image insertion
  (PDF page screenshots, Substack post screenshots, photographs, figures),
  composite overlays, AI-driven 3D reconstruction handoffs, and high-fidelity
  browser-GPU renders — all narrated with bundled neural Kokoro-82M CPU TTS
  (seven voices, no network). Audio-first pipeline: phrase-aware Kokoro
  chunking gives natural rhythm to short phrase rhythms ("never three, never
  six, never nine") and paragraph-level breath to long sections. Every shot
  picks its render engine (pyvista · manim · composite · image · bom · title)
  and the orchestrator dispatches. Output: soft-sub MP4 (mov_text track +
  sidecar SRT, no pixel burn-in) with -14 LUFS audio mastering, gentle
  denoise, optional subtle reverb. Trigger phrases: "make a teaching video",
  "explain X with animation and narration", "narrate this paper", "adapt
  this Substack post into a video", "3blue1brown style explainer", "CAD
  walkthrough with formulas", "design and animate a part with the math
  overlaid", "build a lesson from this source document".
---

# motion-studio v3 — Manim + CAD + Voice + Image Insertion Teaching Studio

The unified skill. CAD + manim + voice + source-doc imagery in one pipeline.
Every shot picks its render engine; the orchestrator handles the rest.

## v3 changes vs v2 (read first if you used v2)

| What | v2 | v3 |
|---|---|---|
| Kokoro synthesis | one sentence per call OR full shot per call | **phrase-aware chunker**: paragraph-level chunks (4-6 sentences) keep prosody natural; comma-rhythm phrases delivered as ONE call ("never three, never six, never nine"). Blank lines → breath. `<beat>` and `<pause N>` markers for explicit silence. |
| Subtitles | baked into pixels by default | **soft-sub MP4** (mov_text track + sidecar `.srt`) by default. User can toggle in player. Manim animated text on screen is still part of the picture. |
| Audio mastering | none — raw Kokoro out | **-14 LUFS loudness norm + denoise (afftdn) + optional subtle reverb** automatically applied at mux. |
| Source-document flow | manual | **`source_doc_pass.py`** ingests a PDF or URL; extracts pages, figures, header metadata, acknowledgements, references; storyboard references them as `image` shots. |
| Image engine | not available | **`image` render engine** for source-page shots, figure cites, photographs, slides — with caption, attribution, Ken Burns, fade in/out. |
| Agent loop | implicit | **explicit** — `/brain` plan → `/grill` only what's unanswered → adaptive but on-source → "continue" loop on tool-limit. See `references/AGENT_LOOP.md`. |
| Engine reminder | manim-heavy by reach | **CAD is first-class** for mechanism scenes; can blend manim + pyvista in a composite shot for math-over-CAD scenes. Reach for the right engine. |

The full agent loop is documented in `references/AGENT_LOOP.md`. The phrase pacing
discipline that fixed the "no 3, no 6, no 9" choppiness is in `references/PHRASE_PACING.md`.

## What this skill produces

Narrated MP4 deliverables that combine any of:

1. **Parametric CAD scenes** — single parts or multi-part assemblies, exploded
   views, orbital cameras, callouts.
2. **Manim motion graphics** — title cards, equation reveals, bullets,
   lower-thirds, 3blue1brown-style explainers.
3. **Composite shots** — CAD scene as the base with manim/math/text overlays
   per-frame.
4. **2D engineering drawings** — orthographic projections, dimensions, DXF.
5. **BOM tables** — bill-of-materials cards rendered into the video.
6. **AI-reconstructed meshes** — via the handoff protocol when the user runs
   ReconViaGen / SAM 3D on their GPU and brings the result back.
7. **Source-document image shots** [v3] — page screenshots, figure cites, photographs,
   slides. Letterboxed, captioned, optional Ken Burns. See `references/IMAGE_SHOT_ENGINE.md`.

All narrated with bundled **Kokoro-82M** neural CPU TTS, 7 voices included.
Captions ship as a soft-sub track inside the MP4 + a sidecar `.srt` file by default
(user can toggle in player). Burn-in is opt-in for legacy use cases.

## Engine choice: pick the right tool, don't default to manim

A common production failure is reaching for manim for EVERY scene. Use the right engine:

| If the scene is… | Use… | Don't use… |
|---|---|---|
| A 3D mechanism (gears, parts, exploded view, rotation, orbital camera) | **pyvista** (build123d CAD source) | manim 3D (much slower, less polished) |
| Animated math, equation transforms, bullet reveals, title cards | **manim** | matplotlib |
| 3D model + math/text floating over it | **composite** (pyvista base + manim overlay) | manim alone (loses CAD); pyvista alone (no math) |
| A source-paper page, a photograph, a figure, an authored slide | **image** [v3] | manim with rendered text (wastes time + worse quality) |
| A bill of materials table | **bom** (matplotlib) | manim Table |
| Plain title card with primary/secondary text | **title** (manim or matplotlib) | full pyvista scene |

**Mix-and-match is the point.** A 6-minute video might be:
- title (10s) → image (4s, source paper) → manim (45s, math reveal) → pyvista (30s, 3D rotation) → composite (60s, 3D with formula overlay) → manim (40s, follow-up math) → image (5s, acknowledgements) → title (5s, credits).

Pre-composite planning: when manim text + CAD scene should share a frame, plan the
LAYOUT in the storyboard (which side of the frame gets the CAD; which side the
formula; how the φ-grid divides them). See `references/COMPOSITING_GOLDEN.md`.

## Sandbox Reality

- **4 GB RAM, 1 CPU core, no GPU.**
- **build123d, trimesh, pyvista, matplotlib, ezdxf, manim 0.20, ffmpeg,
  ImageMagick, numpy, opencv, onnxruntime, espeak-ng, pango/cairo, PIL/Pillow** are first-class.
- **Kokoro-82M fp16 ONNX TTS model and 7 voices are bundled** under `model/`
  and `voices/` (~160 MB total).
- **Setup script**: `bash scripts/verify_setup.sh` — idempotent. Installs deps,
  stages Kokoro from `/mnt/user-data/uploads/` if needed, runs smoke tests for
  every engine.
- **LaTeX is OPT-IN** (~1 GB). Without it, manim's `MathTex` falls back to
  pango-rendered `Text`. Equations look fine for most teaching purposes.
  Install only if your deliverable needs publication-quality typeset math:
  `apt-get install -y texlive-latex-extra dvisvgm`.
- **GPU-only AI models** (ReconViaGen, SAM 3D, Hunyuan3D, TRELLIS) DO NOT run
  here. The skill prepares inputs, writes per-model `RUN.md`, and resumes when
  the mesh comes back. See `references/AI_HANDOFF.md`.

## Default backbone

```
build123d                    ← parametric solid (BREP, OCCT)
  ↓ export_step / export_stl
trimesh                      ← mesh I/O, repair, GLB assembly
  ↓
Kokoro-82M ONNX (bundled)   ← neural CPU TTS (7 voices, audio-first)
  ↓ measure actual durations
plan_timeline()              ← per-shot video_duration
  ↓
[engine dispatch per shot]
  ├─ pyvista (Xvfb+Mesa)    ← CAD scene render
  ├─ manim                   ← motion graphics / math reveals
  ├─ composite               ← pyvista base + manim/text overlays per-frame
  ├─ bom                     ← matplotlib BOM table card
  └─ title                   ← matplotlib title card
  ↓
ffmpeg                       ← concat shots, mix audio, mux + caption burn-in
```

## Compositing pipeline — golden ratio layout

Every CAD animation frame uses `scripts/golden_layout.py` to derive all pixel
positions from **φ = (√5 + 1)/2 ≈ 1.6180**. No magic pixel values anywhere
in the compositor. Key zones for 1280×720:

```
    0              489            791          1280
    │ φ_x1 (38.2%)  │  φ_x2 (61.8%) │           │
  0 ├───────────────┼───────────────┼───────────┤
    │  title bar    │               │           │
 65 ├───────────────┼───────────────┼───────────┤
    │               │               │           │
290 │   viewport    │   FOCAL  ●────┤ label r0  │  ← φ_vy1 (38.2%)
    │   content     │               ├───────────┤
430 │               │               │ label r1  │  ← φ_vy2 (61.8%)
    │               │               ├───────────┤
568 │               │               │ label r2  │
655 ├───────────────┼───────────────┼───────────┤
    │  subtitle bar │               │           │
720 └───────────────┴───────────────┴───────────┘
```

- **Title bar**: `h / φ⁵ ≈ 65px` at 720p
- **Focal point**: (φ_x2, φ_vy1) — (791, 290) — where the most important
  callout label is anchored
- **Label rows**: φ-subdivisions of the label panel height: 290, 429, 568
- **Font scale ladder**: title = base × φ, label = base, small = base ÷ φ,
  tiny = base ÷ φ²  (base = h/36 ≈ 20px at 720p)
- **Progress bar**: φ-proportioned width and horizontal offset
- **Layout sketch mode**: `render_cad_v2.py --sketch` renders one φ-grid
  frame per scene for immediate layout review before committing to a full render

## Render pipeline (`scripts/render_cad_v2.py`)

Layers composited in order:

```
  0. background solid + CAD floor grid (axis-coloured)
  1. CAD mesh rasterizer (painter-sort, per-face Phong shading)
  2. explode / assembly guide lines — arrowheads + halo + origin dot
  6. manim transparent PNG overlay (optional per scene, from --manim-overlays)
  3. HUD chrome — φ-sized title bar, scene counter, thin rule + accent
  4. φ-positioned callout labels with professional leader lines
     or assembly breadcrumb step stack (for assembly_sequence scene)
  5. subtitle bar + progress bar (φ-sized, φ-proportioned width)
```

For the manim overlay layer, render with `manim render -ql --transparent`
to get `.mov` with alpha, then extract with `ffmpeg -pix_fmt rgba -vf fps=<N>`.
The compositor scales the overlay to the base frame and alpha-composites it.

## QA checklist (`scripts/self_check_v2.py`)

```bash
python scripts/self_check_v2.py output/final.mp4 \
    --plan cad_video.json \
    --timing output/audio/timing.json \
    --geometry-dir output/geometry \
    --tolerance-ms 200
```

Checks:
1. Video stream (h264 expected, codec + resolution + fps logged)
2. Audio stream (aac expected, sample rate + channels logged)
3. Timing drift < 200 ms (actual video duration vs timing.json total)
4. Plan schema: required keys present, no authored durations
5. Geometry exports: assembled STL ✓, assembled OBJ ✓, named-parts GLB ✓,
   individual part STLs ✓ count

## Proven reference example

`examples/gundam/` is the verified reference for this skill. The Gundam-inspired
mecha has 60 named parts, 4 scenes (rotation, explode, assembly, final), and
a QA-verified MP4 with 0.0 ms timing drift.

Original espeak-ng voice → upgraded to **Kokoro bm_daniel** (British male,
professional cadence, bundled neural CPU TTS).

For any teaching deliverable, reason from two angles before writing one line:

**Engineering / design mind:**
- What is the *one* thing this video teaches? Strip everything that isn't load-bearing.
- Which CAD primitives map onto the concepts? (Holes for fasteners, fillets for
  stress relief, mate axes for the kinematic story.)
- Which equations or relationships need on-screen presence? Static or animated?
- What's the medium for each shot — pure CAD, pure manim, or composite?

**Listener / viewer mind:**
- If a smart friend explained this over a beer, how would they phrase it? That's
  the narration tone.
- Where would they pause? Where would they zoom in? Where would they highlight?
- What metaphor anchors the abstract part of the design? Don't reach for a clever
  one if a plain one is clearer.
- What's the closing line that makes the whole thing land?

For vague prompts, make one clear interpretation, state it in one line at the
top, and proceed. The user can redirect mid-stream cheaply.

## Tool Choice (short version — read `references/TOOL_CHOICE.md` for the full)

| Job | Engine | Don't use |
|---|---|---|
| Parametric part / assembly | **build123d** (pyvista engine) | OpenSCAD alone |
| Exploded view + camera animation | **pyvista** | matplotlib 3D |
| Title card, lower-third, equation reveal | **manim** | OBS / Premiere (offline) |
| Math equation pinned over CAD scene | **composite** (pyvista base + math/manim overlay) | rendering math into manim alone (lose the CAD) |
| Animated math (equation transforms, term highlighting) | **manim** (composite for overlay on CAD) | matplotlib mathtext (static only) |
| 2D engineering drawing | **build123d sections + ezdxf** | pure matplotlib |
| BOM table | **matplotlib `ax.table`** | manim |
| Image(s) → 3D mesh | **AI handoff** (user GPU) | anything in-sandbox |
| Real-time / WebGPU PBR render | **browser handoff** | pyvista (CPU only) |

## Hard Truth Gates (don't skip)

1. **Gate A — Geometry**: STEP+STL exist; volume + bbox logged.
2. **Gate B — Still render**: At least one PNG exists, viewed via `view` tool.
3. **Gate C — Animation**: Frame count + first/middle/last frame viewed.
4. **Gate D — Narration**: Audio file exists, RMS in audible range,
   duration ≈ shot duration ±5%.
5. **Gate E — Composite** (if used): At least one composited frame viewed to
   confirm overlay position, opacity, and timing.
6. **Gate F — Bundle**: All artifacts in `/mnt/user-data/outputs/`,
   `present_files` succeeded.

Never describe what an artifact "would look like." Either render it and view, or
say "not done yet."

## Iteration Loop

For any non-trivial job, work this loop in order. Reorder steps only when a
sub-part is genuinely absent.

```
1. INTAKE       — restate the deliverable in one sentence. Declare the natural
                  sub-parts (geometry, animation, equations, narration). Make
                  one engine choice per shot up front.

2. SCAFFOLD     — write the parametric script (build123d). Variables at top.
                  Export STEP+STL. Pass Gate A.

3. STILL SPOT-CHECK — render ONE PNG of the assembly at the canonical iso angle.
                      `view` the PNG. Pass Gate B or fix.

4. STORYBOARD   — write the JSON storyboard with per-shot engine choices,
                  narration, and overlay specs. View one frame of the first
                  composite shot before committing to a full render.

5. NARRATE      — generate Kokoro audio for all shots. Measure durations. Build
                  the timeline. Pass Gate D.

6. RENDER       — orchestrator dispatches per shot. Log frame counts.
                  View first/middle/last frame of any animated shot. Pass Gate C
                  and E (if composite shots).

7. MUX          — concat all frames, mix audio against the timeline, burn
                  captions. Verify total duration. Pass Gate F.

8. DELIVER      — copy to /mnt/user-data/outputs/, call present_files.
```

## Unified storyboard schema

```json
{
  "name": "...",
  "fps": 30,
  "resolution": [1280, 720],
  "assembly": "path/to/assembly.json",
  "source_doc": "assets/source_docs/canosa_137/",
  "voiceover": {
    "engine": "kokoro",
    "default_voice": "af_bella",
    "default_lang": "en-us",
    "burn_captions": false,
    "pacing": { ... overrides ... }
  },
  "audio_master": {
    "target_lufs": -14.0,
    "denoise": true,
    "reverb": "none"
  },
  "shots": [
    {
      "id": "intro_paper",
      "render": {
        "engine": "image",
        "src": "assets/source_docs/canosa_137/page_001.png",
        "caption": "Canosa 2024 · the source",
        "attribution": "Substack · 101E8E8",
        "ken_burns": {"zoom": 1.08, "pan": [0.0, -0.05]},
        "fade_in_s": 0.4, "fade_out_s": 0.4
      },
      "narration": "This series adapts Anthony Canosa's 2024 paper.",
      "voice": "af_bella"
    },
    {
      "id": "title",
      "render": {
        "engine": "manim",
        "kind": "title",
        "primary": "The Cross",
        "secondary": "Why primes after 3 reduce to six digits"
      },
      "narration": "Chapter one. The Cross.",
      "voice": "af_bella"
    },
    {
      "id": "explode",
      "render": {
        "engine": "pyvista",
        "camera": "orbit", "from_azim": 20, "to_azim": 60,
        "elev": 28, "explode": "0→1"
      },
      "narration": "The mechanism. Watch the parts separate."
    },
    {
      "id": "explain_ratio",
      "render": {
        "engine": "composite",
        "base": {
          "engine": "pyvista",
          "camera": "orbit", "explode": "hold@1"
        },
        "overlays": [
          {
            "kind": "manim",
            "action": {
              "kind": "formula",
              "tex": "\\dfrac{50}{50 + 20} \\approx 0.71"
            },
            "position": "bottom-right",
            "start_frame": 30, "end_frame": 90
          }
        ]
      },
      "narration": "The ratio. Inputs to outputs. Six steps, one closed loop."
    },
    {
      "id": "bom",
      "duration": 4.0,
      "render": {"engine": "bom"},
      "narration": "Six parts, 228 grams total."
    },
    {
      "id": "credits",
      "render": {
        "engine": "image",
        "src": "assets/source_docs/canosa_137/page_014.png",
        "caption": "Acknowledgements & references",
        "fade_in_s": 0.5, "fade_out_s": 0.6
      },
      "duration": 5.0,
      "narration": "Acknowledgements. The author thanks his Substack readers."
    }
  ]
}
```

**v3 schema notes:**
- `voiceover.burn_captions` defaults to `false` (soft-sub). Set `true` only for legacy use cases.
- `audio_master` block configures the loudness norm + denoise + reverb pass (defaults `-14 LUFS`, denoise on, no reverb).
- `source_doc` is an optional convenience field — declares the project's source document path.
- `engine: image` (NEW in v3) renders source-doc pages, figures, photographs.
- For phrase-rhythm narration ("never three, never six, never nine"), write ONE sentence with commas; do not split into multiple sentences. The chunker is documented in `references/PHRASE_PACING.md`.

## Engine reference

### `pyvista`
Pure CAD scene. Reads the linked assembly, applies pose + explode rules, orbits
the camera. Wrap with `headless_display()` (handled by the renderers).

### `manim`
Pure manim scene rendered to its own framerate then composited onto a solid
background. Supports `kind`: `title`, `formula`, `bullets`, `highlight`,
`lower_third`, `custom`. See `references/MANIM_PATTERNS.md`.

### `composite`
Both. The `base` is a sub-shot specification (currently `pyvista` is supported).
The `overlays` list contains entries of `kind`: `math` (matplotlib mathtext),
`text` (matplotlib plain), `manim` (full manim scene), `image` (static PNG).
Each overlay has `position`, `opacity`, `scale`, `margin`, and optional
`start_frame`/`end_frame` to time it in and out. See
`references/COMPOSITING.md`.

### `bom`
matplotlib BOM table from the assembly's `bom` entries. Static for the shot's
duration.

### `title`
matplotlib title card (static). For animated titles, use `manim`+`title` instead.

### `image` [v3]
Image-driven shot. Renders a single image (source-paper page screenshot,
photograph, figure, slide) with optional caption, attribution, Ken Burns
zoom/pan, and fade in/out. Letterboxed to project resolution preserving aspect.
Schema: `src` (required path), `caption`, `attribution`, `ken_burns: {zoom, pan}`,
`fade_in_s`, `fade_out_s`. See `references/IMAGE_SHOT_ENGINE.md`.

## Voice-Over (audio-first, Kokoro default — v3 phrase-aware)

- Default engine: **Kokoro-82M** (bundled, neural, CPU-only, 7 voices, ~1× rt).
- Fallback: **gTTS** (online). Last resort: **espeak-ng**.
- Default voice: `af_bella` (American female, warm).
- Multi-voice shots: per-shot `voice` override. Skill auto-uses
  `post_shot_gap_voice_change_ms` (250 ms) between speaker changes for natural
  pacing.
- **[v3] Phrase-aware synthesis**: paragraph-level chunks preserve Kokoro's
  internal prosody. Short phrase rhythms ("never three, never six, never nine")
  delivered as ONE call with natural comma rhythm. Blank lines in source become
  breath gaps. `<beat>` and `<pause N>` markers force explicit silence with
  fresh intonation after.
- **[v3] Soft-sub default**: SRT generated as a track in the MP4 (mov_text) +
  sidecar `.srt` next to the MP4. Burn-in is opt-in.
- **[v3] Audio mastering**: -14 LUFS normalize + denoise (afftdn) + optional
  reverb applied at mux. See `references/AUDIO_MASTER.md`.

See `references/VOICEOVER.md`, `references/PHRASE_PACING.md`, and `references/VOICES.md`.

## Agent Loop (v3, explicit)

For any production run involving a source document:

1. **`/brain` scoring** — 5 axes (Stakes · Clarity · Novelty · Complexity · Depth). 2+ High → both hemispheres. Score is silent.
2. **Plan** — write the storyboard JSON. Decide engine per shot. Plan layout for composite shots.
3. **`/grill`** — ask only what source/plan/prompt cannot answer. ≤ 3 questions max, ordered by impact. Self-grill first; only escalate to user when stuck.
4. **Execute** — audio first → render frames → audio master → soft-sub mux → present.
5. **On tool-limit reached** — checkpoint state. Tell user honestly. Wait for "continue".

Full discipline in `references/AGENT_LOOP.md`.

## AI Reconstruction handoff

For image/video → 3D mesh jobs, the skill prepares inputs and emits a per-model
`RUN.md`. User runs ReconViaGen / SAM 3D / Hunyuan3D / TRELLIS on their GPU and
uploads the resulting GLB back. Skill resumes the pipeline. See
`references/AI_HANDOFF.md` and `scripts/recon_handoff.py`.

## Self-healing patterns

| Symptom | Cause | Fix |
|---|---|---|
| `bad X server connection` | pyvista without Xvfb | Wrap with `headless_display()` |
| Kokoro audio is silent / NaN | fp16 overflow on long sequence | Engine auto-chunks. If still failing, shorten or speed=1.0 |
| Manim render fails with LaTeX error | MathTex requires LaTeX | Install texlive-latex-extra, or use `Text()` instead of `MathTex()` |
| Manim "transparent" output isn't transparent | Wrong format flag | Always use `--transparent` AND output to `.mov` (not `.mp4`) |
| Composite shot has overlay in wrong place | Position spec misinterpreted | See `references/COMPOSITING.md` for position grammar |
| Audio/video drift > 100 ms | Stale frames or cached narration | Delete `out_dir/frames_concat/` and rerun |
| pyvista renders blank | Camera looking the wrong way | Force `plotter.camera_position = "iso"` AFTER `add_mesh` |
| Slow manim renders | Animation too long or quality too high | Drop to `-ql` for drafts; render to `qh` only for delivery |
| `frame_xxxx.png` skipped | Animation step didn't call `plotter.render()` before screenshot | Already fixed in `exploded_view.py` / `render_orbit.py` |

## Red flags

- Claiming a model is "exported and ready" without `view`-ing a render of it.
- Claiming a composite shot works without `view`-ing one composited frame.
- Producing a video without verifying audio duration matches video duration.
- Generating audio AFTER video frames — that's the broken ordering; audio-first.
- Trying to render in-sandbox what only the user's GPU can produce
  (ReconViaGen, SAM 3D).
- Installing LaTeX for a job that only needs plain `Text()`.
- Mixing manim and matplotlib typography across shots (looks unprofessional).

## Quick Reference Index

- `SKILL.md` — this file
- `README.md` — high-level intro + file layout
- `references/`
  - `AGENT_LOOP.md` — [v3 NEW] `/brain` plan → `/grill` → continue loop discipline
  - `PHRASE_PACING.md` — [v3 NEW] Kokoro phrase chunker rules (the fix for choppiness)
  - `AUDIO_MASTER.md` — [v3 NEW] LUFS / denoise / reverb recipe
  - `SOURCE_DOC_FLOW.md` — [v3 NEW] PDF/URL ingest and weaving into video
  - `IMAGE_SHOT_ENGINE.md` — [v3 NEW] image-driven shot reference
  - `TOOL_CHOICE.md` — decision tree for every tool
  - `PIPELINES.md` — copy-paste skeletons per output class
  - `ASSEMBLY_SCHEMA.md` — multi-part assembly format
  - `COMPOSITING.md` — overlay playbook
  - `COMPOSITING_GOLDEN.md` — golden-ratio layout zones
  - `MANIM_PATTERNS.md` — manim_action DSL recipes
  - `TEACHING.md` — pacing and structure for lessons
  - `MANIM_TROUBLESHOOTING.md` — manim-specific failure recovery
  - `VOICEOVER.md` — audio-first pipeline
  - `VOICES.md` — Kokoro voice catalog
  - `AI_HANDOFF.md` — ReconViaGen / SAM 3D templates
  - `WEBGPU_HANDOFF.md` — browser-render handoff
- `scripts/`
  - `verify_setup.sh` — run once per fresh sandbox
  - `kokoro_engine.py` — bundled Kokoro-82M ONNX
  - `phrase_chunker.py` — [v3 NEW] paragraph/phrase splitter for natural Kokoro rhythm
  - `voiceover.py` — audio-first narration + timeline + soft-sub mux
  - `audio_master.py` — [v3 NEW] LUFS norm + denoise + reverb
  - `source_doc_pass.py` — [v3 NEW] PDF/URL ingest (pages, figures, metadata)
  - `image_shot.py` — [v3 NEW] image-driven shot renderer
  - `storyboard.py` — multi-engine orchestrator
  - `render_manim.py` + `manim_scenes.py` — manim DSL + scene builders
  - `compositor.py` — per-frame composite, math overlays, text overlays
  - `exploded_view.py` — schema-driven exploded animation
  - `assembly.py` — schema validator + builder + GLB exporter
  - `render_still.py` / `render_orbit.py` — single PNG / orbital animation
  - `drawing_2d.py` — orthographic drawings → DXF/PNG/PDF
  - `recon_handoff.py` — AI recon job preparer
  - `webgpu_handoff.py` — browser-render handoff
  - `headless.py` — Xvfb display context manager
- `handoffs/` — per-model RUN.md templates + manifest template + browser HTML
- `model/`, `voices/` — bundled Kokoro assets (model 163 MB, 7 voices ~3.7 MB)
- `examples/` — runnable references including the hybrid math-overlay demo
