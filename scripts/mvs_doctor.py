#!/usr/bin/env python3
"""
mvs_doctor.py — read-only health check for Motion-Voice-Studio.

Unlike verify_setup.sh, this script NEVER installs or modifies anything.
It runs every required check, prints PASS or FAIL with a one-line remediation
hint, and exits 0 if everything passes, 1 if any check failed.

Usage:
    python3 scripts/mvs_doctor.py            # human-readable output
    python3 scripts/mvs_doctor.py --json     # machine-readable JSON
    python3 scripts/mvs_doctor.py --strict   # treat warnings as failures

Cross-platform: works on Linux, macOS, Windows. Pure stdlib + repo imports.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CheckResult:
    name: str
    status: str           # "pass" | "warn" | "fail"
    detail: str = ""
    fix: str = ""         # remediation hint
    category: str = ""


# ── individual checks ─────────────────────────────────────────────────────

def check_python_version() -> CheckResult:
    v = sys.version_info
    if v >= (3, 10):
        return CheckResult("python", "pass",
            detail=f"Python {v.major}.{v.minor}.{v.micro}", category="runtime")
    return CheckResult("python", "fail",
        detail=f"Python {v.major}.{v.minor} too old; need 3.10+",
        fix="Install Python 3.10 or newer", category="runtime")


def check_system_tool(cmd: str, install_hint: str, category: str = "system") -> CheckResult:
    path = shutil.which(cmd)
    if path:
        return CheckResult(cmd, "pass", detail=path, category=category)
    return CheckResult(cmd, "fail", detail="not on PATH",
        fix=install_hint, category=category)


def check_python_module(mod: str, pip_name: str, optional: bool = False,
                        category: str = "python") -> CheckResult:
    try:
        m = importlib.import_module(mod)
        version = getattr(m, "__version__", "?")
        return CheckResult(mod, "pass", detail=f"version={version}", category=category)
    except ImportError:
        status = "warn" if optional else "fail"
        return CheckResult(mod, status,
            detail="import failed",
            fix=f"pip install {pip_name}",
            category=category)


def check_phonemizer_backend() -> CheckResult:
    try:
        from phonemizer.backend import EspeakBackend
        b = EspeakBackend("en-us")
        out = b.phonemize(["hello"])
        if out and out[0].strip():
            return CheckResult("phonemizer+espeak", "pass",
                detail=f"en-us → {out[0].strip()!r}", category="tts")
        return CheckResult("phonemizer+espeak", "fail",
            detail="returned empty phonemes",
            fix="Reinstall espeak-ng: apt install espeak-ng", category="tts")
    except Exception as e:
        return CheckResult("phonemizer+espeak", "fail",
            detail=f"{type(e).__name__}: {e}",
            fix="Ensure espeak-ng is on PATH and phonemizer-fork is installed",
            category="tts")


def check_kokoro_model() -> tuple[CheckResult, Optional[Path]]:
    canonical = REPO_ROOT / "model" / "kokoro-v1_0_fp16.onnx"
    legacy    = REPO_ROOT / "model" / "kokoro-v1.0.fp16.onnx"

    if canonical.exists():
        sz = canonical.stat().st_size
        return CheckResult("kokoro.model", "pass",
            detail=f"{canonical.name} ({sz/1024/1024:.0f} MB)",
            category="kokoro"), canonical
    if legacy.exists():
        return CheckResult("kokoro.model", "warn",
            detail=f"found at legacy path {legacy.name}",
            fix=f"Rename to {canonical.name} to match manifest",
            category="kokoro"), legacy
    return CheckResult("kokoro.model", "fail",
        detail="model file not found",
        fix="Run: python Kokoro_TTS_Agent_Skill_Pack/combine.py --out model/",
        category="kokoro"), None


def check_kokoro_model_sha(model_path: Optional[Path]) -> CheckResult:
    if model_path is None or not model_path.exists():
        return CheckResult("kokoro.model.sha256", "warn",
            detail="skipped (no model file)", category="kokoro")
    manifest_path = REPO_ROOT / "Kokoro_TTS_Agent_Skill_Pack" / "manifest.json"
    if not manifest_path.exists():
        return CheckResult("kokoro.model.sha256", "warn",
            detail="skipped (no manifest)", category="kokoro")
    expected = json.loads(manifest_path.read_text())["original_sha256"]
    h = hashlib.sha256()
    with model_path.open("rb") as f:
        for blk in iter(lambda: f.read(8 << 20), b""):
            h.update(blk)
    actual = h.hexdigest()
    if actual == expected:
        return CheckResult("kokoro.model.sha256", "pass",
            detail=f"matches manifest ({actual[:16]}…)", category="kokoro")
    return CheckResult("kokoro.model.sha256", "fail",
        detail=f"sha256 mismatch (got {actual[:16]}…, want {expected[:16]}…)",
        fix="Re-run combine.py to rebuild from parts",
        category="kokoro")


def check_kokoro_config() -> CheckResult:
    p = REPO_ROOT / "model" / "config.json"
    if p.exists():
        try:
            json.loads(p.read_text())
            return CheckResult("kokoro.config", "pass",
                detail=str(p.relative_to(REPO_ROOT)), category="kokoro")
        except Exception as e:
            return CheckResult("kokoro.config", "fail",
                detail=f"unparseable: {e}",
                fix="Copy Kokoro_TTS_Agent_Skill_Pack/config.json to model/",
                category="kokoro")
    return CheckResult("kokoro.config", "fail",
        detail="model/config.json missing",
        fix="cp Kokoro_TTS_Agent_Skill_Pack/config.json model/",
        category="kokoro")


def check_kokoro_voices() -> CheckResult:
    voices_dir = REPO_ROOT / "voices"
    if not voices_dir.is_dir():
        return CheckResult("kokoro.voices", "fail",
            detail="voices/ directory missing",
            fix="cp kokoro-voices/*.pt voices/", category="kokoro")
    voices = list(voices_dir.glob("*.pt"))
    if not voices:
        return CheckResult("kokoro.voices", "fail",
            detail="no .pt files in voices/",
            fix="cp kokoro-voices/*.pt voices/", category="kokoro")
    names = sorted(p.stem for p in voices)
    must_have = {"af_bella"}  # the NaN-safe fallback default
    missing = must_have - set(names)
    if missing:
        return CheckResult("kokoro.voices", "warn",
            detail=f"{len(voices)} voice(s); missing fallback: {sorted(missing)}",
            fix="cp kokoro-voices/af_bella.pt voices/", category="kokoro")
    return CheckResult("kokoro.voices", "pass",
        detail=f"{len(voices)} voice(s): {', '.join(names[:6])}{'...' if len(names)>6 else ''}",
        category="kokoro")


def check_kokoro_smoke(model_path: Optional[Path]) -> CheckResult:
    """End-to-end synthesis smoke test. Takes 2-5 seconds on CPU."""
    if model_path is None or not model_path.exists():
        return CheckResult("kokoro.smoke", "warn",
            detail="skipped (no model)", category="kokoro")
    cfg = REPO_ROOT / "model" / "config.json"
    voices = REPO_ROOT / "voices"
    if not cfg.exists() or not any(voices.glob("*.pt")):
        return CheckResult("kokoro.smoke", "warn",
            detail="skipped (config or voices missing)", category="kokoro")
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from kokoro_engine import KokoroEngine  # type: ignore
        eng = KokoroEngine(str(model_path), str(cfg), str(voices))
        avail = eng.list_voices()
        v = "af_bella" if "af_bella" in avail else avail[0]
        audio, sr = eng.synthesize("Doctor check.", voice=v)
        import numpy as np  # safe: onnxruntime already pulled numpy
        if np.isnan(audio).any():
            return CheckResult("kokoro.smoke", "fail",
                detail=f"voice={v} produced NaN audio",
                fix="Try voice='af_bella' (NaN-safe fallback)", category="kokoro")
        dur = len(audio) / sr
        return CheckResult("kokoro.smoke", "pass",
            detail=f"voice={v}, {dur:.2f}s audio at {sr} Hz", category="kokoro")
    except Exception as e:
        return CheckResult("kokoro.smoke", "fail",
            detail=f"{type(e).__name__}: {e}",
            fix="Check kokoro.model, config, and voices checks above",
            category="kokoro")


def check_manim_smoke() -> CheckResult:
    """Run a 2-line manim Scene. Catches missing pangocairo, dvisvgm, etc."""
    if shutil.which("manim") is None:
        return CheckResult("manim.smoke", "fail",
            detail="manim CLI not on PATH",
            fix="pip install manim==0.20.1", category="manim")
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="mvs-doctor-"))
    scene = tmp / "_smoke.py"
    scene.write_text(
        "from manim import *\n"
        "class S(Scene):\n"
        "    def construct(self):\n"
        "        self.play(FadeIn(Text('ok', color=WHITE), run_time=0.2))\n"
        "        self.wait(0.1)\n"
    )
    res = subprocess.run(
        ["manim", "render", "-ql", "--disable_caching",
         "--media_dir", str(tmp), str(scene), "S"],
        capture_output=True, text=True,
    )
    videos = list(tmp.rglob("*.mp4")) + list(tmp.rglob("*.mov"))
    shutil.rmtree(tmp, ignore_errors=True)
    if videos:
        return CheckResult("manim.smoke", "pass",
            detail="2-frame test scene rendered", category="manim")
    return CheckResult("manim.smoke", "fail",
        detail=f"manim render failed (rc={res.returncode})",
        fix="Check pangocairo: pkg-config --modversion pangocairo",
        category="manim")


def check_engines_text_display() -> CheckResult:
    """Core Production Contract imports `from engines.text_display import ...`."""
    canonical = REPO_ROOT / "engines" / "text_display.py"
    legacy = (REPO_ROOT / "MVS-README-DOCS-FOR-AGENTS-START-HERE"
                       / "text_display.py")
    if canonical.exists():
        return CheckResult("engines.text_display", "pass",
            detail="engines/text_display.py present", category="layout")
    if legacy.exists():
        return CheckResult("engines.text_display", "warn",
            detail="found at legacy docs path",
            fix=f"git mv {legacy.relative_to(REPO_ROOT)} engines/text_display.py",
            category="layout")
    return CheckResult("engines.text_display", "fail",
        detail="text_display.py not found at canonical or legacy path",
        fix="Repo appears incomplete; re-clone or restore from backup",
        category="layout")


# ── runner ────────────────────────────────────────────────────────────────

CATEGORY_ORDER = ["runtime", "system", "python", "tts", "kokoro", "manim", "layout"]

PRETTY = {
    "pass": ("✓", "\033[0;32m"),
    "warn": ("⚠", "\033[0;33m"),
    "fail": ("✗", "\033[0;31m"),
}
RESET = "\033[0m"


def all_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    results.append(check_python_version())

    results.append(check_system_tool("ffmpeg",
        "apt install ffmpeg  |  brew install ffmpeg"))
    results.append(check_system_tool("ffprobe",
        "(ships with ffmpeg)"))
    results.append(check_system_tool("espeak-ng",
        "apt install espeak-ng  |  brew install espeak-ng"))
    results.append(check_system_tool("dvisvgm",
        "apt install dvisvgm  |  (part of TeX Live on macOS)",
        category="system"))
    results.append(check_system_tool("latex",
        "apt install texlive-latex-extra  |  brew install --cask mactex-no-gui",
        category="system"))

    for mod, pip_name in [
        ("manim", "manim==0.20.1"),
        ("numpy", "numpy<2.0"),
        ("onnxruntime", "onnxruntime>=1.20"),
        ("phonemizer", "phonemizer-fork"),
        ("soundfile", "soundfile"),
    ]:
        results.append(check_python_module(mod, pip_name))

    results.append(check_phonemizer_backend())

    model_check, model_path = check_kokoro_model()
    results.append(model_check)
    results.append(check_kokoro_model_sha(model_path))
    results.append(check_kokoro_config())
    results.append(check_kokoro_voices())
    results.append(check_kokoro_smoke(model_path))

    results.append(check_manim_smoke())

    results.append(check_engines_text_display())

    return results


def print_human(results: list[CheckResult]) -> None:
    print(f"\nMotion-Voice-Studio doctor — {platform.system()} {platform.machine()}\n")
    last_cat = None
    for r in sorted(results, key=lambda x: (CATEGORY_ORDER.index(x.category) if x.category in CATEGORY_ORDER else 99, x.name)):
        if r.category != last_cat:
            print(f"  [{r.category}]")
            last_cat = r.category
        glyph, color = PRETTY[r.status]
        line = f"    {color}{glyph}{RESET} {r.name:30s} {r.detail}"
        print(line)
        if r.status != "pass" and r.fix:
            print(f"        fix: {r.fix}")

    n_pass = sum(1 for r in results if r.status == "pass")
    n_warn = sum(1 for r in results if r.status == "warn")
    n_fail = sum(1 for r in results if r.status == "fail")
    print(f"\n  Summary: {n_pass} pass · {n_warn} warn · {n_fail} fail\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON instead of human output")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as failures for exit code")
    args = ap.parse_args()

    results = all_checks()

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print_human(results)

    fail_states = {"fail"} | ({"warn"} if args.strict else set())
    return 1 if any(r.status in fail_states for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
