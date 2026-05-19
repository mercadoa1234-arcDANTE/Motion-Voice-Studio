---
name: kokoro-tts
description: >
  Full Kokoro v1.0 TTS skill. Triggers on: "speak this", "text to speech", "generate
  audio", "read this aloud", "synthesise speech", "kokoro", "TTS", "voice output", or any
  task requiring spoken audio from text. Handles model reassembly, dependency install,
  voice download, inference, and emotional delivery — all locally, zero API cost.
  Also triggers for model reassembly alone: "combine the parts", "missing .onnx",
  "load Kokoro", or any onnxruntime call that fails because the .onnx is absent.
---

# Kokoro TTS — Agent Skill

Kokoro v1.0 FP16 ONNX. Runs on CPU. 24 kHz output. Zero cloud calls. ~4 GB RAM.

---

## Step 1 — Reassemble the model (one-time)

The 156 MB `.onnx` is split into 7 × 24 MB parts for GitHub compatibility.

```bash
python combine.py          # verifies SHA256 on every part + final file
```

Expected SHA256: `ba4527a874b42b21e35f468c10d326fdff3c7fc8cac1f85e9eb6c0dfc35c334a`

Skip if `kokoro-v1_0_fp16.onnx` already exists and matches that hash.

---

## Step 2 — Install dependencies

```bash
pip install kokoro-onnx onnxruntime soundfile --break-system-packages
```

- `kokoro-onnx` — IPA tokenizer + trim utilities
- `onnxruntime` — ONNX inference (CPU)
- `soundfile` — write WAV files

---

## Step 3 — Download voices (one-time, ~26 MB)

Voices are **not** in the model file. Fetch from npm:

```python
import urllib.request, tarfile, shutil, os
from pathlib import Path

voices_dir = Path("voices")
voices_dir.mkdir(exist_ok=True)

url = "https://registry.npmjs.org/kokoro-js/-/kokoro-js-1.2.1.tgz"
urllib.request.urlretrieve(url, "/tmp/kokoro-js.tgz")

with tarfile.open("/tmp/kokoro-js.tgz") as t:
    for m in t.getmembers():
        if m.name.startswith("package/voices/") and m.name.endswith(".bin"):
            m.name = m.name.replace("package/voices/", "")
            t.extract(m, path=str(voices_dir))

print(f"Downloaded {len(list(voices_dir.glob('*.bin')))} voices")
```

Available voices (54 total):

| Prefix | Description | Examples |
|---|---|---|
| `af_` | American female | `af_heart` `af_bella` `af_sarah` `af_nova` `af_sky` |
| `am_` | American male | `am_adam` `am_michael` `am_echo` `am_liam` |
| `bf_` | British female | `bf_emma` `bf_alice` `bf_lily` |
| `bm_` | British male | `bm_george` `bm_daniel` `bm_lewis` |

---

## Step 4 — Synthesise speech

```python
import json, numpy as np, onnxruntime as ort, soundfile as sf
from pathlib import Path
from kokoro_onnx.tokenizer import Tokenizer

MODEL  = "kokoro-v1_0_fp16.onnx"
CONFIG = "config.json"
VOICES = Path("voices")
SR     = 24000   # sample rate (Hz)

def load_voice(name: str) -> np.ndarray:
    """Returns (510, 256) float32 — one 256-dim embedding per sequence length."""
    raw = np.fromfile(str(VOICES / f"{name}.bin"), dtype=np.float32)
    return raw.reshape(-1, 256)

def speak(text: str, voice="af_heart", speed=1.0) -> np.ndarray:
    """
    text  : natural language string, any punctuation
    voice : voice name (see table above), default af_heart
    speed : 0.5 (slow) – 2.0 (fast), default 1.0
    Returns float32 audio array at 24000 Hz.
    """
    with open(CONFIG) as f:
        vocab = json.load(f)["vocab"]

    tokenizer = Tokenizer(vocab=vocab)
    sess      = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    voice_emb = load_voice(voice)

    phonemes = tokenizer.phonemize(text, lang="en-us")
    tokens   = tokenizer.tokenize(phonemes)

    # style is indexed by sequence length; clip avoids fp16 NaN overflow
    style  = np.clip(voice_emb[len(tokens)], -4.0, 4.0)
    padded = np.array([[0, *tokens, 0]], dtype=np.int64)

    audio = sess.run(None, {
        "input_ids": padded,
        "style":     np.array([style], dtype=np.float32),  # shape (1, 256)
        "speed":     np.array([speed], dtype=np.float32),  # shape (1,)
    })[0]

    if audio.ndim == 2:
        audio = audio[0]

    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    pk    = np.abs(audio).max()
    if pk > 0:
        audio = audio / pk * 0.9    # normalize to -0.9..0.9

    return audio.astype(np.float32)

# --- example ---
if __name__ == "__main__":
    audio = speak("Hello. This is Kokoro running locally.", voice="af_heart", speed=1.0)
    sf.write("output.wav", audio, SR)
    print(f"Saved output.wav  {len(audio)/SR:.2f}s")
```

---

## Emotional delivery

Emotion is encoded **in the text itself** — punctuation and word choice are the controls.
No special API flags. The model reads prosodic cues from the phoneme sequence.

| Emotion | Technique | Speed | Example |
|---|---|---|---|
| Joy / excitement | Exclamation marks, energetic words | 1.2–1.4 | `"I can't believe it! This is amazing!"` |
| Sadness | Ellipsis `...`, sparse words, trailing off | 0.7–0.8 | `"I don't know... it just feels empty."` |
| Anger / determination | Short sentences. Periods. No softening. | 1.0–1.1 | `"No. Stop. I will not accept this."` |
| Calm / thoughtful | Questions, measured phrasing | 0.9–1.0 | `"What really matters here?"` |
| Confusion | `Wait,` + questions | 0.8–0.9 | `"Wait, what? Can you explain that again?"` |
| Warmth | Sincere declaratives, soft words | 0.85–0.95 | `"You mean everything to me."` |

---

## Script length and natural prosody

**Key behaviour:** Kokoro processes the entire script in a single inference call.
All sentences share one continuous prosody arc — same pitch baseline, same breath rhythm,
natural sentence-to-sentence flow. This is why multi-sentence scripts sound like a
connected phrase rather than spliced clips.

**Optimal script length: 60–100 words per call** (≈ 60–100 phoneme tokens).

- Under 10 words: works, but prosody is abrupt at boundaries
- 60–100 words: best naturalness — full sentence arcs, breath points, emotional build
- Over ~120 words: model truncates at 500 phoneme tokens; split into chunks

**How to split long scripts for natural sound:**

```python
def speak_long(text, voice="af_heart", speed=1.0, chunk_words=80):
    """Split at sentence boundaries to preserve natural prosody."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, cur = [], []
    for s in sentences:
        cur.append(s)
        if sum(len(c.split()) for c in cur) >= chunk_words:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))

    parts = [speak(chunk, voice=voice, speed=speed) for chunk in chunks]
    return np.concatenate(parts)
```

Concatenated chunks at natural pause boundaries (`.`, `!`, `?`) sound far smoother
than chunks split mid-sentence or at arbitrary character counts.

---

## Batch: generate multiple lines

```python
scripts = [
    ("Joy",      "I just can't believe it! This is absolutely amazing!",  "af_heart", 1.3),
    ("Sadness",  "I don't know... sometimes I feel so lost.",              "af_heart", 0.75),
    ("Anger",    "No. You need to stop. I will not accept this.",          "am_adam",  1.05),
    ("Calm",     "Let's take a moment. What really matters here?",        "am_adam",  0.9),
    ("Confused", "Wait, what? Can you explain that again?",                "af_sarah", 0.85),
    ("Warmth",   "You mean everything to me. I care about you so much.",  "af_nova",  0.9),
]

for label, text, voice, speed in scripts:
    audio = speak(text, voice=voice, speed=speed)
    sf.write(f"{label.lower()}.wav", audio, SR)
    print(f"{label}: {len(audio)/SR:.2f}s")
```

---

## Cost and performance

| Metric | Value |
|---|---|
| Claude API cost per TTS call | $0 (local inference) |
| Inference time (CPU, ~80 tokens) | 3–6 s unoptimised |
| Output sample rate | 24 000 Hz |
| File size (~5 s audio) | ~230 KB WAV |
| RAM required | ~4 GB |
| GPU required | No |

vs. cloud TTS at same volume: Eleven Labs ~$0.30/1M chars = ~$3 000/day at 1 000 req/day.
Kokoro cost: $0.

---

## Reassembly failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `missing part` error | Part file not cloned or LFS-stripped | Re-clone or `git lfs pull` |
| `SHA256 mismatch` on a part | File corrupted in transit | Re-pull that specific part |
| `onnxruntime` errors after combine | Wrong `config.json` or opset mismatch | Confirm `config.json` is in the same directory |
| Audio is static / NaN | Wrong tokenization (raw chars, not IPA) | Use `Tokenizer.phonemize` + `tokenize` — never feed raw ASCII |
| Audio is silent after trim | Trim threshold too aggressive on low-amplitude output | Skip trim or use `top_db=40` |
| `style` dimension mismatch | Wrong shape — model needs `[1, 256]` | `voice_emb[len(tokens)]` gives `(256,)` → wrap in `np.array([...])` |

---

## Re-splitting for new model versions

```bash
python split.py kokoro-v1_0_fp16.onnx        # default 24 MB chunks
python split.py kokoro-v1_0_fp16.onnx --chunk-mb 20  # extra headroom
git add kokoro-v1_0_fp16.onnx.part* manifest.json
git commit -m "update model"
# do NOT commit the full .onnx — only the parts
```
