#!/usr/bin/env bash
# setup.sh — one-shot Motion-Voice-Studio installer.
#
# What this does:
#   1. apt: ffmpeg, espeak-ng, dvisvgm, libpangocairo-dev, texlive-latex-extra
#   2. pip: install requirements.txt (pinned)
#   3. Assemble the Kokoro fp16 ONNX model from bundled split parts
#   4. Stage voices into ./voices/
#   5. Run verify_setup.sh to confirm everything works
#
# Idempotent: running twice is safe and skips already-installed items.
# Cross-platform: detects apt-get / brew / dnf where possible.
# Does NOT require sudo if you're already root (e.g. Docker, claude.ai sandbox).
# If sudo is needed and unavailable, prints what to install manually.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; B='\033[0;36m'; N='\033[0m'
log()  { echo -e "${B}[setup]${N} $*"; }
ok()   { echo -e "${G}  ✓${N} $*"; }
warn() { echo -e "${Y}  ⚠${N} $*"; }
err()  { echo -e "${R}  ✗${N} $*"; }

# ── 0. Privilege detection ────────────────────────────────────────────────

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
elif command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
  warn "Not root and no sudo found. apt/brew calls may fail — install manually if so."
fi

# ── 1. System packages ────────────────────────────────────────────────────

SYS_DEB=(ffmpeg espeak-ng dvisvgm libpangocairo-1.0-0 libpango1.0-dev libcairo2-dev pkg-config poppler-utils)
SYS_DEB_OPT=(texlive-latex-extra texlive-fonts-recommended)  # ~1 GB, needed for MathTex

log "System packages..."
if command -v apt-get >/dev/null 2>&1; then
  # apt-get update can fail on unrelated third-party repos (nodesource, etc.).
  # Don't let someone else's broken repo kill our install — keep going as long
  # as the packages we actually need install successfully.
  $SUDO apt-get update -qq || warn "apt-get update reported errors (likely unrelated 3rd-party repos); continuing"
  $SUDO apt-get install -y -qq "${SYS_DEB[@]}" && ok "core system tools"
  if [ "${INSTALL_LATEX:-1}" = "1" ]; then
    log "Installing TeX Live (~1 GB; set INSTALL_LATEX=0 to skip)..."
    $SUDO apt-get install -y -qq "${SYS_DEB_OPT[@]}" && ok "TeX Live (MathTex enabled)"
  else
    warn "Skipping TeX Live. manim Text() works, MathTex() will fall back to plain text."
  fi
elif command -v brew >/dev/null 2>&1; then
  brew install ffmpeg espeak-ng dvisvgm pango cairo pkg-config poppler && ok "core system tools (brew)"
  if [ "${INSTALL_LATEX:-1}" = "1" ]; then
    brew install --cask mactex-no-gui 2>/dev/null && ok "MacTeX" || warn "MacTeX install skipped — install manually if you need MathTex"
  fi
elif command -v dnf >/dev/null 2>&1; then
  $SUDO dnf install -y ffmpeg espeak-ng dvisvgm pango-devel cairo-devel pkgconf-pkg-config poppler-utils && ok "core system tools (dnf)"
else
  err "No supported package manager found (apt-get / brew / dnf)."
  err "Install these manually then re-run:"
  err "  ${SYS_DEB[*]}"
  exit 1
fi

# ── 2. Python packages ────────────────────────────────────────────────────

log "Python packages from requirements.txt..."
PIP_FLAGS=()
# --break-system-packages needed on Debian/Ubuntu 23+ outside a venv.
if pip install --help 2>/dev/null | grep -q -- --break-system-packages; then
  PIP_FLAGS+=(--break-system-packages)
fi

if [ -f "$REPO_ROOT/requirements.txt" ]; then
  pip install "${PIP_FLAGS[@]}" -q -r "$REPO_ROOT/requirements.txt" && ok "pip install -r requirements.txt"
else
  err "requirements.txt not found at $REPO_ROOT/requirements.txt"
  exit 2
fi

# ── 3. Assemble the Kokoro model ──────────────────────────────────────────

log "Assembling Kokoro fp16 ONNX model from bundled split parts..."

KOKORO_MANIFEST="$REPO_ROOT/Kokoro_TTS_Agent_Skill_Pack/manifest.json"
MODEL_DIR="$REPO_ROOT/model"
MODEL_OUT="$MODEL_DIR/kokoro-v1_0_fp16.onnx"

if [ ! -f "$KOKORO_MANIFEST" ]; then
  err "Kokoro manifest not found at $KOKORO_MANIFEST"
  err "Cannot assemble model. Verify the repo is intact."
  exit 3
fi

mkdir -p "$MODEL_DIR"

if [ -s "$MODEL_OUT" ]; then
  ok "model already assembled ($(du -h "$MODEL_OUT" | cut -f1)) — skipping"
else
  python3 "$REPO_ROOT/Kokoro_TTS_Agent_Skill_Pack/combine.py" \
    --manifest "$KOKORO_MANIFEST" \
    --out "$MODEL_DIR" \
    && ok "model assembled → model/kokoro-v1_0_fp16.onnx"
fi

# Stage config.json next to the model
if [ ! -f "$MODEL_DIR/config.json" ]; then
  if [ -f "$REPO_ROOT/Kokoro_TTS_Agent_Skill_Pack/config.json" ]; then
    cp "$REPO_ROOT/Kokoro_TTS_Agent_Skill_Pack/config.json" "$MODEL_DIR/"
    ok "staged model/config.json"
  else
    err "config.json not found in Kokoro_TTS_Agent_Skill_Pack/"
    exit 4
  fi
fi

# ── 4. Stage voices ───────────────────────────────────────────────────────

log "Staging voices..."
VOICES_DST="$REPO_ROOT/voices"
mkdir -p "$VOICES_DST"

if [ -d "$REPO_ROOT/kokoro-voices" ]; then
  n_copied=0
  for voice in "$REPO_ROOT/kokoro-voices"/*.pt; do
    [ -e "$voice" ] || continue
    name=$(basename "$voice")
    if [ ! -s "$VOICES_DST/$name" ]; then
      cp "$voice" "$VOICES_DST/$name"
      n_copied=$((n_copied + 1))
    fi
  done
  n_total=$(ls "$VOICES_DST"/*.pt 2>/dev/null | wc -l)
  ok "$n_total voice(s) in voices/ (newly staged: $n_copied)"
else
  warn "kokoro-voices/ directory not found — checking voices/ alone"
fi

# ── 5. Verify ─────────────────────────────────────────────────────────────

log "Running verify_setup.sh for end-to-end smoke test..."
if [ -x "$REPO_ROOT/scripts/verify_setup.sh" ]; then
  "$REPO_ROOT/scripts/verify_setup.sh" || warn "verify_setup.sh reported issues (see above)"
elif [ -f "$REPO_ROOT/scripts/verify_setup.sh" ]; then
  bash "$REPO_ROOT/scripts/verify_setup.sh" || warn "verify_setup.sh reported issues (see above)"
else
  warn "verify_setup.sh not found — skipping end-to-end smoke test"
  warn "  to verify manually: python3 -m mvs_doctor  (after the doctor script lands)"
fi

ok "Setup complete. Try the smoke storyboard:"
echo "  python3 scripts/voiceover.py examples/smoke.storyboard.json --out-dir /tmp/mvs-smoke"
