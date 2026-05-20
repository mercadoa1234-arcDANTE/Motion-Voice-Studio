# core/TROUBLESHOOT.md — Troubleshooting

Fast lookup. Symptom → cause → fix.

---

## Audio

| Symptom | Cause | Fix |
|---|---|---|
| Silent WAV (zero RMS), no NaN | Phonemizer dropped text | Spell out numbers/symbols; check `tok.phonemize()` output |
| NaN audio / silent after norm | fp16 overflow | Switch voice to `af_bella`; chunk to ≤60 words |
| Clipping (peak = 1.0) | `loudnorm` pushing to headroom | `alimiter=limit=0.95` before mux |
| Choppy short phrases | Per-sentence synthesis | Merge into one Kokoro call (see `core/AUDIO.md`) |
| Audio shorter than video | `atrim` cut too early | Match trim duration to ffprobe video duration exactly |
| `mux.py` exits silently | Output dir doesn't exist | Use `/mnt/user-data/outputs/` (always exists) |
| "audio total duration mismatch" | `timing.json` out of sync | `rm -rf audio/` → re-run `generate_audio.py` → re-render |

---

## Manim rendering

| Symptom | Cause | Fix |
|---|---|---|
| `dvisvgm not found` | LaTeX backend missing | `apt-get install -y dvisvgm texlive-extra-utils` |
| `pangocairo not found` | Cairo missing | `apt-get install -y libpango1.0-dev libcairo2-dev` |
| `Undefined control sequence \something` | Missing LaTeX package | Replace with simpler macro or wrap in `Tex` not `MathTex` |
| Mobject off-screen | x_range/y_range too tight | Expand range ~20% each side |
| Render > 5 min for 2-min video | Quality too high or heavy 3D | Use `-ql` (480p) or `-qm` (720p); avoid `high_quality` unless required |
| Video shorter than expected | `wait()` missing | Check generated scene file; re-run |

---

## Text display / kerning

| Symptom | Cause | Fix |
|---|---|---|
| Text overlapping after `kern()` | kern_scale too high for font | Reduce `kern_scale` toward 0; serif fonts may need 0 |
| `fix()` not resolving overlap | Dense layout, few passes | Increase `max_fix_passes` to 12–16; switch `reflow_axis` |
| Subtitle in wrong position | `scene_height` mismatch | Pass actual Manim scene height: default 8.0 |
| Subtitle burned into pixels | Wrong mux flags | Use `-c:s mov_text`, never `-vf subtitles=` |

---

## Geometry / CAD

| Symptom | Cause | Fix |
|---|---|---|
| Part is tiny or huge | Unit mismatch | Confirm `units` field; rescale mesh |
| STL has no volume | Non-watertight mesh | Repair CAD source; prefer STEP export |
| STEP export missing | Mesh-only source | State STEP limitation; return STL + note |
| Exploded view moves wrong part | Unnamed components | Map mesh groups to named exports |

---

## Kokoro model assembly

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR: missing part: kokoro-v1_0_fp16.onnx.part00` | Parts in wrong dir | Copy parts next to `manifest.json` before running `combine.py` |
| SHA256 mismatch on final file | Corrupt part | Re-download / re-copy affected part file |
| `Tokenizer has no attribute 'encode'` | Old API call | Use `tok.normalize_text` → `tok.phonemize` → `tok.tokenize` (not `.encode`) |

---

## Setup

| Symptom | Cause | Fix |
|---|---|---|
| `espeak-ng` missing | Not installed | `apt-get install -y espeak-ng espeak-ng-data libespeak-ng1` |
| LaTeX missing for MathTex | Not installed | `apt-get install -y texlive texlive-latex-extra` |
| `manim` install fails on pango | Cairo/pango headers missing | `apt-get install -y libpango1.0-dev libcairo2-dev pkg-config` first |

---

## Disk pressure

- Model bundle: ~156 MB
- `audio/` dir: 5–20 MB
- Manim `media/` dir: 10–50 MB

After render: delete `media/videos/.../partial_movie_files/` — intermediate frames, safe to remove.
