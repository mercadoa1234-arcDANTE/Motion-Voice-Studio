#!/usr/bin/env python3
"""
kokoro_run.py — Kokoro v1.0 TTS, ready to use.

FIRST RUN:
  python combine.py                          # reassemble model (once)
  pip install kokoro-onnx onnxruntime soundfile
  python kokoro_run.py --setup               # download 54 voices (~26 MB)

THEN:
  python kokoro_run.py "Your text here."
  python kokoro_run.py "Your text." --voice am_adam --speed 0.9 --out speech.wav

EMOTIONS (via text — no flags needed):
  Joy:      "I can't believe it! This is amazing!"           speed 1.2–1.4
  Sadness:  "I don't know... it just feels empty."           speed 0.7–0.8
  Anger:    "No. Stop. I will not accept this."              speed 1.0–1.1
  Calm:     "What really matters here?"                      speed 0.85–1.0
  Warmth:   "You mean everything to me."                     speed 0.85–0.95

SCRIPT LENGTH:
  One call = one inference = one continuous prosody arc.
  60–100 words per call sounds most natural.
  Over 120 words: script is auto-split at sentence boundaries.
"""

import argparse
import json
import re
import sys
import urllib.request
import tarfile
from pathlib import Path

import numpy as np
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx.tokenizer import Tokenizer

MODEL  = Path("kokoro-v1_0_fp16.onnx")
CONFIG = Path("config.json")
VOICES = Path("voices")
SR     = 24000
MAX_TOKENS = 480   # leave 20-token buffer below model's 500 limit


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_voices():
    """Download all 54 voices from the kokoro-js npm package (~26 MB)."""
    VOICES.mkdir(exist_ok=True)
    url = "https://registry.npmjs.org/kokoro-js/-/kokoro-js-1.2.1.tgz"
    tgz = Path("/tmp/kokoro-js.tgz")
    print("Downloading kokoro-js voices from npm...", end=" ", flush=True)
    urllib.request.urlretrieve(url, tgz)
    print("done.")

    with tarfile.open(tgz) as t:
        for m in t.getmembers():
            if m.name.startswith("package/voices/") and m.name.endswith(".bin"):
                m.name = m.name.replace("package/voices/", "")
                t.extract(m, path=str(VOICES))

    count = len(list(VOICES.glob("*.bin")))
    print(f"Extracted {count} voices to {VOICES}/")
    print("Available:", ", ".join(sorted(p.stem for p in VOICES.glob("*.bin"))))


# ── Core inference ────────────────────────────────────────────────────────────

def _load_resources():
    if not MODEL.exists():
        sys.exit(f"❌ {MODEL} not found. Run: python combine.py")
    if not CONFIG.exists():
        sys.exit(f"❌ {CONFIG} not found.")
    if not VOICES.exists() or not list(VOICES.glob("*.bin")):
        sys.exit("❌ No voices found. Run: python kokoro_run.py --setup")

    vocab     = json.loads(CONFIG.read_text())["vocab"]
    tokenizer = Tokenizer(vocab=vocab)
    sess      = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
    return tokenizer, sess


def _load_voice(name: str) -> np.ndarray:
    path = VOICES / f"{name}.bin"
    if not path.exists():
        available = [p.stem for p in sorted(VOICES.glob("*.bin"))]
        sys.exit(f"❌ Voice '{name}' not found. Available: {', '.join(available)}")
    return np.fromfile(str(path), dtype=np.float32).reshape(-1, 256)  # (510, 256)


def _infer_chunk(tokenizer, sess, voice_emb, text, speed):
    """Single inference call for one chunk of text."""
    phonemes = tokenizer.phonemize(text, lang="en-us")
    tokens   = tokenizer.tokenize(phonemes)

    if len(tokens) > MAX_TOKENS:
        tokens = tokens[:MAX_TOKENS]

    # style indexed by sequence length — this is the correct Kokoro API
    style  = np.clip(voice_emb[len(tokens)], -4.0, 4.0)
    padded = np.array([[0, *tokens, 0]], dtype=np.int64)

    audio = sess.run(None, {
        "input_ids": padded,
        "style":     np.array([style], dtype=np.float32),   # (1, 256)
        "speed":     np.array([speed], dtype=np.float32),   # (1,)
    })[0]

    if audio.ndim == 2:
        audio = audio[0]

    return np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def speak(text: str, voice: str = "af_heart", speed: float = 1.0,
          chunk_words: int = 90) -> np.ndarray:
    """
    Convert text to audio. Handles any length by splitting at sentence boundaries.

    text        : Natural language. Punctuation encodes emotion (see module docstring).
    voice       : Voice name, e.g. 'af_heart', 'am_adam', 'bf_emma'. Default: af_heart.
    speed       : 0.5 (slow) to 2.0 (fast). Default: 1.0.
    chunk_words : Max words per inference call. 60–100 sounds most natural. Default: 90.

    Returns float32 audio array at 24 000 Hz.

    Script-length note:
      One inference call = one continuous prosody arc. Multi-sentence scripts within
      chunk_words sound naturally connected — the model holds pitch and rhythm across
      sentences. Splitting at sentence boundaries (not mid-sentence) preserves that
      natural flow between chunks.
    """
    tokenizer, sess = _load_resources()
    voice_emb       = _load_voice(voice)

    # Split at sentence boundaries if text is long
    sentences = re.split(r'(?<=[.!?…])\s+', text.strip())
    chunks, cur, cur_words = [], [], 0

    for s in sentences:
        w = len(s.split())
        if cur and cur_words + w > chunk_words:
            chunks.append(" ".join(cur))
            cur, cur_words = [s], w
        else:
            cur.append(s)
            cur_words += w

    if cur:
        chunks.append(" ".join(cur))

    parts = []
    for i, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            print(f"  chunk {i}/{len(chunks)}: {chunk[:60]}{'...' if len(chunk)>60 else ''}")
        audio = _infer_chunk(tokenizer, sess, voice_emb, chunk, speed)
        parts.append(audio)

    audio = np.concatenate(parts) if len(parts) > 1 else parts[0]

    # Normalise
    pk = np.abs(audio).max()
    if pk > 0:
        audio = audio / pk * 0.9

    return audio


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Kokoro TTS — text to speech, locally.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("text", nargs="?", help="Text to synthesise")
    parser.add_argument("--voice",  default="af_heart", help="Voice name (default: af_heart)")
    parser.add_argument("--speed",  type=float, default=1.0, help="Speed 0.5–2.0 (default: 1.0)")
    parser.add_argument("--out",    default="output.wav", help="Output WAV file (default: output.wav)")
    parser.add_argument("--setup",  action="store_true", help="Download voices and exit")
    parser.add_argument("--list",   action="store_true", help="List available voices and exit")
    parser.add_argument("--demo",   action="store_true", help="Generate 6 emotional demo files")
    args = parser.parse_args()

    if args.setup:
        setup_voices()
        return

    if args.list:
        if not VOICES.exists():
            print("No voices directory. Run: python kokoro_run.py --setup")
        else:
            voices = sorted(p.stem for p in VOICES.glob("*.bin"))
            print(f"{len(voices)} voices available:")
            for v in voices:
                print(f"  {v}")
        return

    if args.demo:
        DEMOS = [
            ("Joy & Excitement",
             "I just can't believe it! This is absolutely amazing! I'm so happy right now!",
             "af_heart", 1.3),
            ("Sadness & Melancholy",
             "I don't know... sometimes I feel so lost. Everything just feels empty.",
             "af_heart", 0.75),
            ("Determination & Anger",
             "No. You need to stop. I will not accept this. Not anymore.",
             "am_adam", 1.05),
            ("Calm & Thoughtful",
             "Let's take a moment to think about this. What really matters here?",
             "am_adam", 0.9),
            ("Confusion & Uncertainty",
             "Wait, what? I'm not sure I understand. Can you explain that again?",
             "af_sarah", 0.85),
            ("Warmth & Affection",
             "You mean everything to me. I care about you so much.",
             "af_nova", 0.9),
        ]
        print("\nGenerating 6 emotional demos...\n")
        for label, text, voice, speed in DEMOS:
            print(f"[{label}]  voice={voice}  speed={speed}x")
            print(f"  {text}")
            audio = speak(text, voice=voice, speed=speed)
            fname = label.lower().replace(" & ", "_").replace(" ", "_") + ".wav"
            sf.write(fname, audio, SR)
            print(f"  → {fname}  ({len(audio)/SR:.2f}s)\n")
        return

    if not args.text:
        parser.print_help()
        return

    print(f"Voice: {args.voice}  Speed: {args.speed}x")
    print(f"Text:  {args.text}")
    audio = speak(args.text, voice=args.voice, speed=args.speed)
    sf.write(args.out, audio, SR)
    print(f"Saved: {args.out}  ({len(audio)/SR:.2f}s  {Path(args.out).stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
