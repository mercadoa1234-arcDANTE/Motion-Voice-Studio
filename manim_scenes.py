"""
Pure-Python Kokoro ONNX TTS engine — no PyTorch, no spacy/misaki.

Loads voice tensors from .pt files by parsing the zip+pickle structure directly,
phonemizes via espeak-ng (through phonemizer-fork), and runs the fp16 ONNX model.

Usage:
    from kokoro_engine import KokoroEngine
    eng = KokoroEngine(model_path="model/kokoro-v1.0.fp16.onnx",
                       config_path="model/config.json",
                       voices_dir="voices")
    audio, sr = eng.synthesize("Hello world.", voice="af_bella", speed=1.0, lang="en-us")
"""
from __future__ import annotations

import json
import os
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

# Hard-import deps — installed by setup_env.sh
from onnxruntime import InferenceSession, SessionOptions
from phonemizer.backend import EspeakBackend


# Cache of espeak backends keyed by language so we don't rebuild repeatedly.
_BACKEND_CACHE: dict[str, EspeakBackend] = {}


def _get_backend(lang: str) -> EspeakBackend:
    """Map plan languages to espeak-ng codes; cache backends."""
    espeak_lang_map = {
        "en-us": "en-us",
        "en-gb": "en-gb",
        "es":    "es",
        "fr":    "fr-fr",
        "it":    "it",
        "pt-br": "pt-br",
        "hi":    "hi",
        "ja":    "ja",
        "zh":    "cmn",
    }
    code = espeak_lang_map.get(lang, lang)
    if code not in _BACKEND_CACHE:
        _BACKEND_CACHE[code] = EspeakBackend(
            language=code,
            preserve_punctuation=True,
            with_stress=True,
        )
    return _BACKEND_CACHE[code]


class KokoroEngine:
    """Kokoro-82M TTS via ONNX Runtime + bundled voice embeddings."""

    SAMPLE_RATE = 24000
    MAX_TOKENS  = 510            # 512 minus two pad tokens

    def __init__(
        self,
        model_path: str | os.PathLike,
        config_path: str | os.PathLike,
        voices_dir: str | os.PathLike,
        providers: Optional[list[str]] = None,
    ) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Kokoro ONNX model not found: {model_path}")
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Kokoro config.json not found: {config_path}")
        self.voices_dir = Path(voices_dir)
        if not self.voices_dir.is_dir():
            raise FileNotFoundError(f"voices dir not found: {self.voices_dir}")

        with open(config_path) as f:
            self.config = json.load(f)
        self.vocab: dict[str, int] = self.config["vocab"]

        opts = SessionOptions()
        opts.intra_op_num_threads = max(1, (os.cpu_count() or 1) - 0)
        self.sess = InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=providers or ["CPUExecutionProvider"],
        )
        # Inspect model i/o once
        names = {i.name for i in self.sess.get_inputs()}
        required = {"input_ids", "style", "speed"}
        missing = required - names
        if missing:
            raise RuntimeError(f"ONNX model missing expected inputs: {missing}")

    # ── voice loading ─────────────────────────────────────────────────────
    @lru_cache(maxsize=64)
    def _load_voice_tensor(self, name: str) -> np.ndarray:
        """Load voice .pt → (510, 1, 256) float32 array. Cached.

        Reads the torch.save zip without requiring torch itself: the .pt is a
        zip with a `data/0` blob holding raw float32 bytes.
        """
        path = self.voices_dir / f"{name}.pt"
        if not path.exists():
            available = sorted(p.stem for p in self.voices_dir.glob("*.pt"))
            raise ValueError(
                f"voice {name!r} not found. Available: {available}"
            )
        with zipfile.ZipFile(path) as z:
            # The internal layout is `<voicename>/data/0`. Find it dynamically.
            data_member = next(n for n in z.namelist() if n.endswith("/data/0"))
            raw = z.read(data_member)
        arr = np.frombuffer(raw, dtype=np.float32)
        if arr.size != 510 * 1 * 256:
            raise ValueError(
                f"voice {name} has unexpected size {arr.size}, expected {510*256}"
            )
        return arr.reshape(510, 1, 256).copy()  # copy: detach from buffer

    def list_voices(self) -> list[str]:
        return sorted(p.stem for p in self.voices_dir.glob("*.pt"))

    # ── phonemization & tokenization ──────────────────────────────────────
    def _phonemize(self, text: str, lang: str) -> str:
        backend = _get_backend(lang)
        result = backend.phonemize([text])[0]
        return result

    def _tokenize(self, phonemes: str) -> list[int]:
        # Drop chars not in vocab silently — espeak-ng occasionally emits
        # rare diacritics not present in Kokoro's vocab.
        out: list[int] = []
        for c in phonemes:
            tid = self.vocab.get(c)
            if tid is not None:
                out.append(tid)
        return out

    # ── synthesis ─────────────────────────────────────────────────────────
    def synthesize(
        self,
        text: str,
        voice: str = "af_bella",
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> tuple[np.ndarray, int]:
        """Generate one chunk of audio. Returns (audio_float32_mono, sample_rate)."""
        if not (0.5 <= speed <= 2.0):
            raise ValueError(f"speed must be in [0.5, 2.0], got {speed}")

        phonemes = self._phonemize(text, lang)
        tokens   = self._tokenize(phonemes)

        if not tokens:
            return np.zeros(0, dtype=np.float32), self.SAMPLE_RATE

        # fp16 ONNX can produce NaN on long sequences, especially at speed < 1.0.
        # Chunk when: over hard limit OR (over 160 tokens AND speed < 1.0).
        fp16_safe_limit = 160 if speed < 1.0 else self.MAX_TOKENS
        if len(tokens) > fp16_safe_limit:
            return self._synthesize_chunked(text, voice, speed, lang)

        voices_tensor = self._load_voice_tensor(voice)
        ref_s         = voices_tensor[len(tokens)].astype(np.float32)  # (1, 256)
        input_ids     = np.array([[0, *tokens, 0]], dtype=np.int64)

        out = self.sess.run(
            None,
            {
                "input_ids": input_ids,
                "style":     ref_s,
                "speed":     np.array([float(speed)], dtype=np.float32),
            },
        )[0]
        audio = out.squeeze().astype(np.float32)
        if not np.isfinite(audio).all():
            # fp16 overflow — fall back to chunked synthesis
            return self._synthesize_chunked(text, voice, speed, lang)
        return audio, self.SAMPLE_RATE

    def _synthesize_chunked(
        self,
        text: str,
        voice: str,
        speed: float,
        lang: str,
    ) -> tuple[np.ndarray, int]:
        """Split overly-long or NaN-prone text on sentence boundaries, concatenate audio."""
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentences) <= 1:
            sentences = re.split(r"(?<=[,;:])\s+", text.strip())
        if len(sentences) <= 1:
            # Last resort: split on word count
            words = text.split()
            mid = len(words) // 2
            sentences = [" ".join(words[:mid]), " ".join(words[mid:])]
        chunks: list[np.ndarray] = []
        for s in sentences:
            if not s.strip():
                continue
            phon = self._phonemize(s, lang)
            tokens = self._tokenize(phon)
            if not tokens:
                continue
            # Direct inference — no recursion
            voices_tensor = self._load_voice_tensor(voice)
            idx = min(len(tokens), 509)
            ref_s = voices_tensor[idx].astype(np.float32)
            input_ids = np.array([[0, *tokens, 0]], dtype=np.int64)
            out = self.sess.run(None, {
                "input_ids": input_ids,
                "style":     ref_s,
                "speed":     np.array([float(speed)], dtype=np.float32),
            })[0]
            a = out.squeeze().astype(np.float32)
            if not np.isfinite(a).all():
                # Replace NaN chunk with silence of proportional length
                est_dur = max(0.5, len(tokens) / 10.0)
                a = np.zeros(int(est_dur * self.SAMPLE_RATE), dtype=np.float32)
            chunks.append(a)
            chunks.append(np.zeros(int(0.15 * self.SAMPLE_RATE), dtype=np.float32))
        audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
        return audio, self.SAMPLE_RATE
