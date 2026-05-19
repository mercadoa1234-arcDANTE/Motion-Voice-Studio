# Kokoro v1.0 TTS — GitHub Bundle

Kokoro FP16 ONNX, split for GitHub (7 × 24 MB parts). Runs on CPU, 24 kHz, zero cloud calls.

## Setup (3 steps, one-time)

**1. Reassemble the model**
```bash
python combine.py
```
Verifies SHA256 on every part and the final file. Takes ~10 s.

**2. Install dependencies**
```bash
pip install kokoro-onnx onnxruntime soundfile
```

**3. Download voices (~26 MB)**
```bash
python -c "
import urllib.request, tarfile
from pathlib import Path
voices = Path('voices'); voices.mkdir(exist_ok=True)
urllib.request.urlretrieve('https://registry.npmjs.org/kokoro-js/-/kokoro-js-1.2.1.tgz', '/tmp/k.tgz')
with tarfile.open('/tmp/k.tgz') as t:
    for m in t.getmembers():
        if m.name.startswith('package/voices/') and m.name.endswith('.bin'):
            m.name = m.name.replace('package/voices/', '')
            t.extract(m, path='voices')
print(f'Done — {len(list(voices.glob(\"*.bin\")))} voices downloaded')
"
```

## Use

```python
import json, numpy as np, onnxruntime as ort, soundfile as sf
from pathlib import Path
from kokoro_onnx.tokenizer import Tokenizer

def speak(text, voice="af_heart", speed=1.0):
    vocab     = json.load(open("config.json"))["vocab"]
    tokenizer = Tokenizer(vocab=vocab)
    sess      = ort.InferenceSession("kokoro-v1_0_fp16.onnx", providers=["CPUExecutionProvider"])
    emb       = np.fromfile(f"voices/{voice}.bin", dtype=np.float32).reshape(-1, 256)
    phonemes  = tokenizer.phonemize(text, lang="en-us")
    tokens    = tokenizer.tokenize(phonemes)
    style     = np.clip(emb[len(tokens)], -4.0, 4.0)
    audio     = sess.run(None, {
        "input_ids": np.array([[0, *tokens, 0]], dtype=np.int64),
        "style":     np.array([style], dtype=np.float32),
        "speed":     np.array([speed], dtype=np.float32),
    })[0][0]
    audio     = np.nan_to_num(audio)
    pk        = np.abs(audio).max()
    return (audio / pk * 0.9).astype(np.float32) if pk > 0 else audio

sf.write("out.wav", speak("Hello, this is Kokoro."), 24000)
```

## Voices

| Code | Voice |
|---|---|
| `af_heart` | American female — warm (default) |
| `af_bella` / `af_sarah` / `af_nova` | American female variants |
| `am_adam` / `am_michael` | American male |
| `bf_emma` / `bm_george` | British female / male |

## Emotion via script

Speed and punctuation control delivery — no flags needed:

```python
speak("I can't believe it! This is amazing!", speed=1.3)        # joy
speak("I don't know... it just feels empty.", speed=0.75)       # sadness
speak("No. Stop. I will not accept this.", speed=1.05)          # anger
speak("What really matters here?", speed=0.9)                   # calm
```

## Script length note

One `speak()` call = one inference = one continuous prosody arc.
Multi-sentence scripts (60–100 words) sound **naturally connected**.
Over ~120 words: split at sentence boundaries and concatenate.

## Files

| File | Purpose |
|---|---|
| `kokoro-v1_0_fp16.onnx.part00–06` | Split model (concatenate with `combine.py`) |
| `manifest.json` | SHA256 checksums for verification |
| `config.json` | Vocab + model config |
| `combine.py / .sh / .ps1` | Reassembly scripts |
| `split.py` | Re-chunk for new model versions |
| `SKILL.md` | Full agent reference |
