# Motion-Voice-Studio

Upload this skill to an AI chat for best results, otherwise paste a link to the repo into chat.

**Turn a question or idea or a math paper into computer animated graphics with AI generated Voiceover!**

**The Ai will then make turn a JSON storyboard version into a narrated animated video. Runs entirely on CPU — no GPU, no cloud, no API keys.**

Audio is synthesized first with [Kokoro TTS](https://github.com/thewh1teagle/kokoro-onnx) (ONNX, fp16, bundled). Frames are timed to match measured audio durations. The output is a soft-subtitled MP4.

Designed to be used by humans and AI agents alike. If you're an agent, read [`AGENT-GUIDE.md`](./AGENT-GUIDE.md) first — it tells you what to load and what to skip.

---

## What it produces

A fully rendered explainer video: Manim animation + Kokoro narration + soft-sub captions, muxed to MP4. One storyboard JSON in, one `final.mp4` out.

Supports 80+ languages via Kokoro's multilingual voice set. Includes optional CAD/3D animation, WebGPU 3D reconstruction, and source-document-to-video pipelines — but none of that is required for a basic lesson.

---

## Requirements

**System** (installed by `setup.sh`)

- ffmpeg
- espeak-ng
- libpangocairo
- dvisvgm
- texlive-latex-extra *(optional — only needed for `MathTex` scenes; set `INSTALL_LATEX=0` to skip)*

**Python 3.10+**

- manim 0.20.1
- onnxruntime ≥ 1.20
- phonemizer-fork ≥ 3.3
- soundfile, numpy < 2.0, scipy, Pillow, opencv-python-headless

Full pinned list: [`requirements.txt`](./requirements.txt)

---

## Install

```bash
git clone https://github.com/mercadoa1234-arcDANTE/Motion-Voice-Studio.git
cd Motion-Voice-Studio
bash setup.sh
```

`setup.sh` does five things in order:

1. Installs system packages (apt / brew / dnf — auto-detected)
2. Installs Python dependencies from `requirements.txt`
3. Assembles the Kokoro fp16 ONNX model from bundled split parts → `model/kokoro-v1_0_fp16.onnx`
4. Stages voices into `voices/`
5. Runs a smoke test

Idempotent — safe to run twice. Already-assembled model and staged voices are skipped.

**Verify the install:**

```bash
python3 scripts/mvs_doctor.py
# Expected: 19 pass · 0 warn · 0 fail
```

Any FAIL prints a one-line fix. Fix it, re-run.

---

## Quick start

**1. Run the smoke storyboard** (verifies the full pipeline end-to-end):

```bash
python3 scripts/voiceover.py examples/smoke.storyboard.json --out-dir /tmp/mvs-smoke
```

Output: `/tmp/mvs-smoke/final.mp4` + `/tmp/mvs-smoke/final.srt`

**2. Write your own storyboard:**

```json
{
  "title": "Your Lesson",
  "output": { "basename": "lesson", "dir": "/tmp/lesson-out" },
  "video": { "width": 1280, "height": 720, "fps": 30 },
  "default_voice": "af_bella",
  "default_speed": 1.0,
  "shots": [
    {
      "id": "intro",
      "narration": "Welcome. Today we cover the basics.",
      "action": { "kind": "title", "primary": "The Basics" }
    },
    {
      "id": "formula",
      "narration": "Here is Euler's identity.",
      "action": { "kind": "formula", "tex": "e^{i\\pi} + 1 = 0" }
    }
  ]
}
```

Save it, then run:

```bash
python3 scripts/voiceover.py my_lesson.json --out-dir /tmp/my-lesson
```

---

## Scene types

| `action.kind` | What it renders | Required fields |
|---|---|---|
| `title` | Full-screen title card | `primary` |
| `formula` | LaTeX equation reveal | `tex` |
| `bullets` | Titled bullet list | `items` (array) |
| `highlight` | Callout box with arrow | `text` |
| `lower_third` | Bottom banner | `title`, `subtitle` |
| `custom` | Raw Manim scene (Python string) | `code`, `scene_name` |

---

## Voices

12 voices bundled, no network required.

| Voice | Notes |
|---|---|
| `af_bella` | NaN-safe default. Use this if unsure. |
| `af_heart` | Warm, slightly slower cadence |
| `af_nicole` | Clear, neutral |
| `am_fenrir` | Deep male |
| `am_michael` | Use speed ≥ 1.0 only — NaN below that threshold |
| `am_puck` | Energetic male |
| `bf_emma` | British female |
| `bm_daniel` | British male |
| `bm_george` | British male, formal |
| `jf_alpha` | Japanese female |
| `pf_dora` | Portuguese female |
| `zf_xiaoyi` | Mandarin female |

Speed range: 0.85–1.15. NaN guard built into `voiceover.py` — falls back to `af_bella` at 1.0 automatically.

---

## How the pipeline works

Audio is the timing source of truth. Never guess durations from word count.

```
1. generate_narration()   → synthesize per-shot WAV files, measure real durations
2. plan_timeline()        → build timeline from measured durations (not estimates)
3. write_srt()            → captions derived from the same durations
4. mix_audio_timeline()   → combine per-shot audio onto one master bus
5. render_action()        → render Manim frames timed to match each shot's duration
6. mux_final()            → frames + audio + soft-sub SRT → final.mp4
```

Subtitles are always soft-sub (togglable). Pixel-burned subtitles are not supported.

Content hash caching means re-rendering an unchanged shot is free. Change one narration line, rebuild only that shot.

---

## Repo layout

```
Motion-Voice-Studio/
├── AGENT-GUIDE.md                        ← agents: start here
├── setup.sh / setup.ps1                  ← one-shot installer (Linux/Mac/Windows)
├── requirements.txt
├── Dockerfile
│
├── scripts/
│   ├── voiceover.py                      ← main pipeline entrypoint
│   ├── render_manim.py                   ← Manim scene renderer
│   ├── manim_scenes.py                   ← scene kind builders
│   ├── mvs_doctor.py                     ← health check
│   └── ...                               ← CAD, recon, source-doc passes
│
├── engines/
│   └── text_display.py                   ← TextDisplayEngine (kerning, overlap detection)
│
├── examples/
│   └── smoke.storyboard.json             ← minimal working storyboard
│
├── Kokoro_TTS_Agent_Skill_Pack/          ← model assembly (combine.py + manifest)
├── Kokoro_Model_Split_Files/             ← split ONNX parts (assembled by setup.sh)
├── kokoro-voices/                        ← .pt voice files
├── brain/                                ← cognitive orchestration skill (opt-in)
├── handoffs/                             ← SAM3D / 3D recon templates
└── MVS-README-DOCS-FOR-AGENTS-START-HERE/
    ├── PIPELINE.md
    ├── AUDIO.md
    ├── RENDER.md
    ├── TEXT_DISPLAY.md
    ├── CAD.md
    ├── BROWSER.md
    └── Core Production Contract - Readme Second.md
```

---

## Common issues

| Symptom | Fix |
|---|---|
| `FileNotFoundError: kokoro-v1_0_fp16.onnx` | `bash setup.sh` — assembles model from split parts |
| `ModuleNotFoundError: manim` | `pip install -r requirements.txt` |
| `pangocairo >= 1.30.0 is required` | `bash setup.sh` — re-runs apt install |
| NaN audio / silence | Switch voice to `af_bella` at speed 1.0 |
| `MathTex` renders blank | `apt install texlive-latex-extra` or use `Text()` instead |
| `KeyError: 'shots'` | Storyboard uses `"scenes"` — both keys are supported post-patch |
| Audio/video length mismatch | You rendered before synthesizing — always audio-first |

Anything else: `python3 scripts/mvs_doctor.py` first.

---

## Docker

```bash
docker build -t mvs .
docker run --rm -v "$PWD/output:/out" mvs \
  python3 scripts/voiceover.py examples/smoke.storyboard.json --out-dir /out
```

---

## Credits

Built on [Manim](https://github.com/ManimCommunity/manim) by 3Blue1Brown's community, [Kokoro TTS](https://github.com/thewh1teagle/kokoro-onnx) ONNX, and the ONNX Runtime team. Code written by Claude Opus 4.7 reasoning May 2026. Initial exposure to the manim-skill concept via Yusuki710. Vibe code prompts, voice & video pipeline design, integration, and agent skill layer by [mercadoa1234-arcDANTE](https://github.com/mercadoa1234-arcDANTE).

MIT License.
