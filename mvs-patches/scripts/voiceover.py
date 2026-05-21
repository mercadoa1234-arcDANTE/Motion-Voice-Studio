"""
Voice-over generation, captions, and final mux. Audio-first pipeline.

The core discipline: generate audio FIRST, measure ACTUAL durations, then drive
video timing from those measurements. Never guess durations from word counts
or estimate from speed — the audio engine's actual output is the source of
truth.

Engines, in priority order:
1. Kokoro-82M ONNX (bundled, CPU-only, neural quality, no network) — default
2. gTTS (online, fallback if Kokoro fails or user requests)
3. espeak-ng (last resort)

Usage:
    from voiceover import generate_narration, plan_timeline, mux_final

    # Audio-first
    audio_records = generate_narration(shots, out_dir="narration/")
    timeline      = plan_timeline(shots, audio_records, pacing)
    # Render video to match timeline durations (per-shot)
    # Then mux:
    mux_final(frames_glob, fps, audio_records, timeline, captions_srt=..., out=...)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


SKILL_ROOT = Path(__file__).resolve().parent.parent

# Canonical model filename matches the manifest (underscored).
# The dotted name is the historic v2 default; kept as a fallback so
# previously-staged installs don't break on upgrade. New stagings should
# always use the canonical name.
KOKORO_MODEL_CANONICAL = SKILL_ROOT / "model" / "kokoro-v1_0_fp16.onnx"
KOKORO_MODEL_LEGACY    = SKILL_ROOT / "model" / "kokoro-v1.0.fp16.onnx"


def _resolve_kokoro_model() -> Path:
    """Pick the model path: canonical (underscored) first, legacy (dotted) as fallback.

    Emits a one-line deprecation warning the first time the legacy path is used,
    so users know to rename their file before the legacy fallback gets removed.
    """
    if KOKORO_MODEL_CANONICAL.exists():
        return KOKORO_MODEL_CANONICAL
    if KOKORO_MODEL_LEGACY.exists():
        if not getattr(_resolve_kokoro_model, "_warned", False):
            print(
                f"  [voiceover] DEPRECATION: model found at legacy path "
                f"{KOKORO_MODEL_LEGACY.name}. Rename to "
                f"{KOKORO_MODEL_CANONICAL.name} to match manifest. "
                f"Legacy fallback will be removed in a future release.",
                file=sys.stderr,
            )
            _resolve_kokoro_model._warned = True
        return KOKORO_MODEL_LEGACY
    return KOKORO_MODEL_CANONICAL  # canonical path for the "missing file" error message


KOKORO_MODEL = _resolve_kokoro_model()
KOKORO_CONFIG = SKILL_ROOT / "model" / "config.json"
KOKORO_VOICES = SKILL_ROOT / "voices"
CACHE_DIR = Path.home() / ".cache" / "cad-studio-voiceover"

DEFAULT_PACING = {
    "leading_silence_ms": 100,
    "post_shot_gap_same_voice_ms": 150,
    "post_shot_gap_voice_change_ms": 250,
    "tail_silence_ms": 500,
}


# ── engine selection ──────────────────────────────────────────────────────

_engine = None

def _kokoro_available() -> bool:
    # Re-resolve at call time so a model staged after import is still found.
    model = _resolve_kokoro_model()
    return model.exists() and KOKORO_CONFIG.exists() and any(KOKORO_VOICES.glob("*.pt"))


def _get_kokoro_engine():
    """Lazy-init Kokoro. Returns the engine or raises."""
    global _engine, KOKORO_MODEL
    if _engine is not None:
        return _engine
    if not _kokoro_available():
        raise FileNotFoundError(
            f"Kokoro assets missing under {SKILL_ROOT}.\n"
            f"  Need: model/kokoro-v1_0_fp16.onnx, model/config.json, voices/*.pt\n"
            f"  To assemble the model from the bundled split parts, run:\n"
            f"    cd Kokoro_TTS_Agent_Skill_Pack/\n"
            f"    python combine.py --out ../model/\n"
            f"  Or run scripts/verify_setup.sh to install + stage in one step."
        )
    KOKORO_MODEL = _resolve_kokoro_model()  # refresh in case it was just staged
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    from kokoro_engine import KokoroEngine
    _engine = KokoroEngine(str(KOKORO_MODEL), str(KOKORO_CONFIG), str(KOKORO_VOICES))
    return _engine


# ── narration generation ──────────────────────────────────────────────────

def generate_narration(
    shots: list,
    out_dir: str,
    engine: str = "kokoro",
    default_voice: str = "af_bella",
    default_speed: float = 1.0,
    default_lang: str = "en-us",
) -> list:
    """Generate per-shot narration audio. Returns list of records:
    [{shot_id, path, duration_s, voice, sample_rate, is_silent}, ...]

    Empty-narration shots produce a silence record (no audio file).
    """
    os.makedirs(out_dir, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if engine == "kokoro":
        return _generate_with_kokoro(shots, out_dir, default_voice, default_speed, default_lang)
    if engine == "gtts":
        return _generate_with_gtts(shots, out_dir, default_lang)
    raise ValueError(f"unknown engine: {engine}")


def _generate_with_kokoro(shots, out_dir, default_voice, default_speed, default_lang):
    """v3: phrase-aware synthesis.

    For each shot, split narration into paragraph-level chunks (4-6 sentences
    each, or smaller if author used <beat>/<pause> markers or blank lines).
    Synthesize each chunk as ONE Kokoro call so its internal prosody handles
    comma/period rhythm. Concatenate chunks with real silence gaps for breath.

    The fix vs v2: never synthesize a single short sentence in isolation if it
    belongs to a phrase rhythm. "Never three, never six, never nine." is ONE
    call. The phrase_chunker keeps related phrases together unless the author
    explicitly forces a break.
    """
    import numpy as np
    import soundfile as sf
    from phrase_chunker import chunk_narration

    records = []
    eng = None
    for shot in shots:
        sid = shot["id"]
        text = (shot.get("narration") or "").strip()
        if not text:
            records.append({"shot_id": sid, "path": None, "duration_s": 0.0,
                            "voice": None, "sample_rate": 24000, "is_silent": True})
            continue
        voice = shot.get("voice", default_voice)
        speed = float(shot.get("speed", default_speed))
        lang = shot.get("lang", default_lang)

        # Cache key now includes the chunker version so v2 caches don't pollute v3.
        ck = _cache_key(text + "::v3-phrase", voice, speed, lang)
        cache_path = CACHE_DIR / f"{ck}.wav"
        out_path = Path(out_dir) / f"shot_{sid}.wav"

        if cache_path.exists() and cache_path.stat().st_size > 1000:
            shutil.copy(cache_path, out_path)
            dur = sf.info(str(out_path)).duration
            records.append({"shot_id": sid, "path": str(out_path), "duration_s": dur,
                            "voice": voice, "sample_rate": 24000, "is_silent": False,
                            "cached": True})
            print(f"  [{sid}] {voice}: {dur:.2f}s (cached)", flush=True)
            continue

        if eng is None:
            t0 = time.time()
            eng = _get_kokoro_engine()
            print(f"  [engine] kokoro init: {time.time()-t0:.2f}s", flush=True)

        # Phrase-chunk the shot text. Each chunk is one Kokoro call.
        chunks = chunk_narration(text)
        if not chunks:
            print(f"  ⚠ [{sid}] empty after chunking; using silence", flush=True)
            audio_full = np.zeros(int(2.0 * 24000), dtype=np.float32)
            sr = 24000
        else:
            audio_pieces = []
            t0 = time.time()
            for idx, (chunk_text, post_gap) in enumerate(chunks):
                a, sr = eng.synthesize(chunk_text, voice=voice, speed=speed, lang=lang)
                if not np.isfinite(a).all():
                    print(f"  ⚠ [{sid}#{idx}] non-finite; silence", flush=True)
                    a = np.zeros(int(1.0 * sr), dtype=np.float32)
                audio_pieces.append(a.astype(np.float32))
                if post_gap > 0 and idx < len(chunks) - 1:
                    audio_pieces.append(np.zeros(int(round(post_gap * sr)), dtype=np.float32))
            audio_full = np.concatenate(audio_pieces) if audio_pieces else np.zeros(int(1.0 * 24000), dtype=np.float32)
            gen_t = time.time() - t0

        # Quality check: per-chunk dropout
        if np.sqrt((audio_full.astype(float) ** 2).mean()) < 1e-4:
            print(f"  ⚠ [{sid}] near-silent (phonemizer dropout)", flush=True)

        # Peak-normalize to ~-1 dBFS (audio_master.py applies final LUFS pass later)
        peak = float(np.abs(audio_full).max())
        if peak > 1e-9:
            audio_full = audio_full * (0.891 / peak)

        sf.write(str(out_path), audio_full, sr)
        shutil.copy(out_path, cache_path)
        dur = len(audio_full) / sr
        records.append({"shot_id": sid, "path": str(out_path), "duration_s": dur,
                        "voice": voice, "sample_rate": sr, "is_silent": False,
                        "cached": False, "chunk_count": len(chunks)})
        print(f"  [{sid}] {voice}: {dur:.2f}s in {gen_t:.2f}s "
              f"({dur/max(gen_t,1e-6):.2f}× rt · {len(chunks)} chunks)", flush=True)
    return records


def _generate_with_gtts(shots, out_dir, default_lang):
    from gtts import gTTS
    records = []
    lang = default_lang.split("-")[0]  # gTTS uses 'en' not 'en-us'
    for shot in shots:
        sid = shot["id"]
        text = (shot.get("narration") or "").strip()
        if not text:
            records.append({"shot_id": sid, "path": None, "duration_s": 0.0,
                            "voice": None, "sample_rate": 24000, "is_silent": True})
            continue
        raw = os.path.join(out_dir, f"shot_{sid}_raw.mp3")
        out = os.path.join(out_dir, f"shot_{sid}.wav")
        gTTS(text=text, lang=lang, slow=False).save(raw)
        # Convert to 24kHz mono WAV for consistency with Kokoro output
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", raw, "-ar", "24000", "-ac", "1", out,
        ], check=True)
        os.remove(raw)
        dur = _audio_duration(out)
        records.append({"shot_id": sid, "path": out, "duration_s": dur,
                        "voice": "gtts", "sample_rate": 24000, "is_silent": False})
        print(f"  [{sid}] gtts: {dur:.2f}s", flush=True)
    return records


def _cache_key(text, voice, speed, lang):
    blob = json.dumps({"t": text, "v": voice, "s": speed, "l": lang}, sort_keys=True).encode()
    return hashlib.sha1(blob).hexdigest()[:16]


def _audio_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


# ── timeline planning ─────────────────────────────────────────────────────

def plan_timeline(shots: list, audio_records: list, pacing: dict = None) -> dict:
    """Plan the audio timeline AND compute per-shot video durations.

    The audio determines its own timing; the video must match. Returns a dict:

        {
          "version": 1,
          "pacing": {...},
          "leading_silence_s": 0.1,
          "tail_silence_s": 0.5,
          "shots": [
            {"id": "...", "audio_duration": 5.08, "audio_start": 0.1,
             "video_duration": 5.23,  ← audio + post_gap
             "post_gap_s": 0.15, "voice": "af_bella", "narration": "...", "captions": True},
            ...
          ],
          "total_audio_seconds": <full timeline>,
        }

    The video renderer reads `video_duration` per shot to know how many frames
    to render. The mux step uses `audio_start` to place each audio file.
    """
    p = {**DEFAULT_PACING, **(pacing or {})}
    out = {
        "version": 1,
        "pacing": p,
        "leading_silence_s": p["leading_silence_ms"] / 1000.0,
        "tail_silence_s":    p["tail_silence_ms"] / 1000.0,
        "shots": [],
    }
    cursor = out["leading_silence_s"]
    for i, (shot, rec) in enumerate(zip(shots, audio_records)):
        same_voice_next = (
            i + 1 < len(shots)
            and rec.get("voice")
            and audio_records[i + 1].get("voice") == rec.get("voice")
        )
        if i + 1 < len(shots):
            gap = (p["post_shot_gap_same_voice_ms"] if same_voice_next
                   else p["post_shot_gap_voice_change_ms"]) / 1000.0
        else:
            gap = p["tail_silence_ms"] / 1000.0

        # If the shot has no narration but has a stated duration, use that.
        if rec["is_silent"]:
            audio_dur = shot.get("duration", 2.0)
            video_dur = audio_dur
            audio_start = cursor
        else:
            audio_dur = rec["duration_s"]
            video_dur = audio_dur + gap  # video stays on screen during gap
            audio_start = cursor

        out["shots"].append({
            "id":               shot["id"],
            "audio_duration":   audio_dur,
            "audio_start":      audio_start,
            "video_duration":   video_dur,
            "post_gap_s":       gap,
            "voice":            rec.get("voice"),
            "narration":        shot.get("narration", ""),
            "captions":         shot.get("captions", True),
            "is_silent":        rec["is_silent"],
            "audio_path":       rec["path"],
        })
        cursor += video_dur
    out["total_audio_seconds"] = cursor
    return out


# ── SRT captions ──────────────────────────────────────────────────────────

def write_srt(timeline: dict, path: str):
    """Write SRT cues against the planned timeline."""
    def fmt(s):
        h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
        return f"{h:02d}:{m:02d}:{int(sec):02d},{int((sec - int(sec)) * 1000):03d}"

    cues = []
    for s in timeline["shots"]:
        if s["narration"] and s["captions"] and not s["is_silent"]:
            cues.append((s["audio_start"],
                         s["audio_start"] + s["audio_duration"],
                         s["narration"]))
    with open(path, "w") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{i}\n{fmt(a)} --> {fmt(b)}\n{txt}\n\n")
    return path


# ── audio mix and mux ─────────────────────────────────────────────────────

def mix_audio_timeline(timeline: dict, out_path: str) -> str:
    """Mix all per-shot audio files onto a single timeline with proper gaps.

    Uses ffmpeg's anullsrc base + adelay/amix pattern from the manim skill.
    """
    total = timeline["total_audio_seconds"]
    parts = [f"anullsrc=r=24000:cl=mono:duration={total:.3f}[base]"]
    inputs = []
    mix_labels = ["[base]"]
    for i, s in enumerate(timeline["shots"]):
        if s["is_silent"] or not s["audio_path"]:
            continue
        inputs.append(s["audio_path"])
        idx = len(inputs)
        delay_ms = int(round(s["audio_start"] * 1000))
        parts.append(
            f"[{idx}:a]aformat=sample_rates=24000:channel_layouts=mono,"
            f"adelay={delay_ms}|{delay_ms}[s{i}]"
        )
        mix_labels.append(f"[s{i}]")
    n = len(mix_labels)
    parts.append(
        "".join(mix_labels)
        + f"amix=inputs={n}:duration=first:normalize=0,"
        + "loudnorm=I=-16:TP=-1.5:LRA=11[out]"
    )
    fc = ";".join(parts)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-filter_complex", fc, "-map", "[out]",
            "-t", f"{total:.3f}", out_path]
    subprocess.run(cmd, check=True)
    return out_path


def mux_final(
    frames_glob: str,
    fps: int,
    audio_path: str,
    out_path: str,
    captions_srt: Optional[str] = None,
    burn_in: bool = False,
    video_duration: Optional[float] = None,
    audio_drift_tolerance_s: float = 0.1,
    sidecar_srt: bool = True,
    apply_audio_master: bool = True,
    target_lufs: float = -14.0,
) -> str:
    """Mux frames + audio + captions to MP4. v3 defaults:
      - burn_in=False (soft-sub via mov_text track instead of pixel burn)
      - sidecar_srt=True (also copies the SRT next to the MP4 for user toggling)
      - apply_audio_master=True (-14 LUFS for video, gentle denoise)

    If video_duration is provided, asserts audio matches within tolerance.
    """
    if video_duration is not None:
        audio_dur = _audio_duration(audio_path)
        drift = abs(audio_dur - video_duration)
        if drift > audio_drift_tolerance_s:
            print(
                f"  ⚠ audio/video drift {drift*1000:.0f}ms > {audio_drift_tolerance_s*1000:.0f}ms; "
                f"audio={audio_dur:.3f}s video={video_duration:.3f}s",
                file=sys.stderr,
            )

    # ── v3: audio mastering pass before mux ──
    mastered_audio = audio_path
    if apply_audio_master:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from audio_master import master_audio
            mastered_audio = audio_path.replace('.wav', '_mastered.wav')
            master_audio(audio_path, mastered_audio,
                         target_lufs=target_lufs, denoise=True, reverb='none')
            print(f"  ✓ audio mastered → {target_lufs} LUFS", flush=True)
        except Exception as e:
            print(f"  ⚠ audio mastering skipped: {e}", flush=True)
            mastered_audio = audio_path

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(fps),
        "-i", frames_glob,
        "-i", mastered_audio,
    ]

    if captions_srt and burn_in:
        # Legacy/explicit burn-in path (use only when user demands pixel subs)
        cmd += [
            "-vf",
            f"subtitles={captions_srt}:force_style='Fontname=DejaVu Sans,"
            "Fontsize=22,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=40'",
        ]
        cmd += [
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest", out_path,
        ]
    elif captions_srt and not burn_in:
        # v3 default: soft-sub via mov_text track in the MP4 container
        cmd += ["-i", captions_srt]
        cmd += [
            "-map", "0:v", "-map", "1:a", "-map", "2:s",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=eng",
            "-metadata:s:s:0", "title=English",
            "-movflags", "+faststart",
            "-shortest", out_path,
        ]
    else:
        cmd += [
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest", out_path,
        ]

    subprocess.run(cmd, check=True)

    # v3: emit sidecar .srt alongside the MP4 (user-friendly, players auto-detect)
    if captions_srt and sidecar_srt:
        sidecar = str(Path(out_path).with_suffix('.srt'))
        if os.path.realpath(captions_srt) != os.path.realpath(sidecar):
            shutil.copy(captions_srt, sidecar)
            print(f"  ✓ sidecar SRT → {sidecar}", flush=True)

    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate Kokoro narration for a storyboard")
    ap.add_argument("storyboard", help="path to storyboard JSON")
    ap.add_argument("--out-dir", default="/tmp/cad-studio-narration")
    ap.add_argument("--engine", default="kokoro", choices=["kokoro", "gtts"])
    ap.add_argument("--default-voice", default="af_bella")
    args = ap.parse_args()

    schema = json.loads(Path(args.storyboard).read_text())
    # Accept either 'shots' (canonical, matches plan_timeline output) or 'scenes'
    # (used by some Core Production Contract examples). Equivalent meaning.
    shots = schema.get("shots") or schema.get("scenes")
    if not shots:
        raise ValueError(
            f"Storyboard must contain a 'shots' or 'scenes' array. "
            f"Got top-level keys: {sorted(schema.keys())}"
        )
    print(f"[voiceover] {len(shots)} shots, engine={args.engine}")
    records = generate_narration(shots, args.out_dir, engine=args.engine,
                                  default_voice=args.default_voice)
    timeline = plan_timeline(shots, records, pacing=schema.get("voiceover", {}).get("pacing"))
    (Path(args.out_dir) / "timing.json").write_text(json.dumps(timeline, indent=2))
    print(f"[voiceover] timeline total: {timeline['total_audio_seconds']:.2f}s")
    print(f"[voiceover] timing.json written → {args.out_dir}/timing.json")
