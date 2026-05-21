#!/usr/bin/env bash
# apply-mvs-patches.sh — apply the MVS setup patch set in one go.
#
# Usage (from anywhere — auto-locates the repo root):
#     bash mvs-patches/apply-mvs-patches.sh
#
# What this does:
#   1. Confirms it's running inside (or alongside) the MVS repo
#   2. Backs up every file it replaces to .mvs-patch-backup-<timestamp>/
#   3. DELETE MVS-README-DOCS-FOR-AGENTS-START-HERE/text_display.py
#   4. MOVE  text_display.py to engines/  (content unchanged)
#   5. REPLACE 4 modified files (voiceover.py, combine.py, verify_setup.sh, README-FIRST.md)
#   6. ADD 7 new files (setup.sh, setup.ps1, requirements.txt, Dockerfile,
#                       mvs_doctor.py, smoke.storyboard.json, .gitignore)
#   7. chmod +x on the bash scripts and Python entry points
#   8. Runs mvs_doctor.py to verify the patched repo
#
# Safe to re-run. Backups are timestamped so re-runs never overwrite each other.
# If anything fails midway, your originals are in the backup dir — nothing lost.

set -euo pipefail

# ── colors ────────────────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; B='\033[0;36m'; N='\033[0m'
log()  { echo -e "${B}[apply]${N} $*"; }
ok()   { echo -e "${G}  ✓${N} $*"; }
warn() { echo -e "${Y}  ⚠${N} $*"; }
err()  { echo -e "${R}  ✗${N} $*"; }

# ── locate patch source and repo root ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="$SCRIPT_DIR"

# The patch dir is expected to be INSIDE the repo (e.g. Motion-Voice-Studio-main/mvs-patches/).
# If the user dropped it one level up, fall back to that.
candidate_roots=("$PATCH_DIR/.." "$PWD" "$PATCH_DIR/../..")

REPO_ROOT=""
for c in "${candidate_roots[@]}"; do
  c_abs="$(cd "$c" && pwd)"
  if [ -d "$c_abs/Kokoro_TTS_Agent_Skill_Pack" ] && [ -d "$c_abs/scripts" ]; then
    REPO_ROOT="$c_abs"
    break
  fi
done

if [ -z "$REPO_ROOT" ]; then
  err "Cannot find the MVS repo root."
  err "  Looked in: ${candidate_roots[*]}"
  err "  Expected to find Kokoro_TTS_Agent_Skill_Pack/ and scripts/ subdirectories."
  err
  err "  Standard layout:"
  err "    Motion-Voice-Studio-main/"
  err "    ├── Kokoro_TTS_Agent_Skill_Pack/"
  err "    ├── scripts/"
  err "    └── mvs-patches/             ← extract zip here, then bash apply-mvs-patches.sh"
  exit 1
fi

log "Repo root: $REPO_ROOT"
log "Patch source: $PATCH_DIR"

cd "$REPO_ROOT"

# ── refuse to run if patch source IS the repo root (sanity) ───────────────
if [ "$PATCH_DIR" = "$REPO_ROOT" ]; then
  err "Patch directory is the repo root — that means the zip wasn't extracted into a subfolder."
  err "  Move the patch files into a subdirectory (e.g. ./mvs-patches/) and re-run."
  exit 2
fi

# ── verify every expected patch file exists before touching anything ──────
log "Verifying patch bundle is complete..."
required=(
  "AGENT-GUIDE.md"
  "scripts/voiceover.py"
  "scripts/verify_setup.sh"
  "scripts/mvs_doctor.py"
  "Kokoro_TTS_Agent_Skill_Pack/combine.py"
  "MVS-README-DOCS-FOR-AGENTS-START-HERE/README-FIRST.md"
  "MVS-README-DOCS-FOR-AGENTS-START-HERE/Core Production Contract - Readme Second.md"
  "engines/text_display.py"
  "examples/smoke.storyboard.json"
  "setup.sh"
  "setup.ps1"
  "requirements.txt"
  "Dockerfile"
  ".gitignore"
)
missing=()
for f in "${required[@]}"; do
  if [ ! -f "$PATCH_DIR/$f" ]; then
    missing+=("$f")
  fi
done
if [ ${#missing[@]} -gt 0 ]; then
  err "Patch bundle incomplete. Missing:"
  for f in "${missing[@]}"; do err "    $f"; done
  err "  Did the zip extract fully?"
  exit 3
fi
ok "All 14 patch files present in $PATCH_DIR"

# ── create timestamped backup directory ───────────────────────────────────
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$REPO_ROOT/.mvs-patch-backup-$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
log "Backups will go to: $BACKUP_DIR"

backup_if_exists() {
  local rel="$1"
  if [ -f "$REPO_ROOT/$rel" ]; then
    local dst="$BACKUP_DIR/$rel"
    mkdir -p "$(dirname "$dst")"
    cp "$REPO_ROOT/$rel" "$dst"
    ok "backed up: $rel"
  fi
}

apply_replace() {
  local rel="$1"
  backup_if_exists "$rel"
  local target_dir
  target_dir="$(dirname "$REPO_ROOT/$rel")"
  mkdir -p "$target_dir"
  cp "$PATCH_DIR/$rel" "$REPO_ROOT/$rel"
  ok "replaced: $rel"
}

apply_add() {
  local rel="$1"
  local target_dir
  target_dir="$(dirname "$REPO_ROOT/$rel")"
  mkdir -p "$target_dir"
  if [ -f "$REPO_ROOT/$rel" ]; then
    # If the file exists, treat as replace
    backup_if_exists "$rel"
  fi
  cp "$PATCH_DIR/$rel" "$REPO_ROOT/$rel"
  ok "added:    $rel"
}

# ── 1. DELETE legacy text_display.py ──────────────────────────────────────
log "Step 1 — DELETE legacy file"
legacy_td="MVS-README-DOCS-FOR-AGENTS-START-HERE/text_display.py"
if [ -f "$REPO_ROOT/$legacy_td" ]; then
  backup_if_exists "$legacy_td"
  rm "$REPO_ROOT/$legacy_td"
  ok "deleted: $legacy_td"
else
  warn "$legacy_td not present — nothing to delete (probably already migrated)"
fi

# ── 2. MOVE text_display.py to engines/ ───────────────────────────────────
log "Step 2 — MOVE text_display.py to canonical engines/ path"
mkdir -p "$REPO_ROOT/engines"
cp "$PATCH_DIR/engines/text_display.py" "$REPO_ROOT/engines/text_display.py"
ok "engines/text_display.py present"

# ── 3. REPLACE 5 modified files ───────────────────────────────────────────
log "Step 3 — REPLACE 5 modified files"
apply_replace "scripts/voiceover.py"
apply_replace "Kokoro_TTS_Agent_Skill_Pack/combine.py"
apply_replace "scripts/verify_setup.sh"
apply_replace "MVS-README-DOCS-FOR-AGENTS-START-HERE/README-FIRST.md"
apply_replace "MVS-README-DOCS-FOR-AGENTS-START-HERE/Core Production Contract - Readme Second.md"

# ── 4. ADD 8 new files ────────────────────────────────────────────────────
log "Step 4 — ADD 8 new files"
apply_add "AGENT-GUIDE.md"
apply_add "setup.sh"
apply_add "setup.ps1"
apply_add "requirements.txt"
apply_add "Dockerfile"
apply_add "scripts/mvs_doctor.py"
apply_add "examples/smoke.storyboard.json"
apply_add ".gitignore"

# ── 5. Set executable bits ────────────────────────────────────────────────
log "Step 5 — chmod +x on scripts"
chmod +x "$REPO_ROOT/setup.sh"
chmod +x "$REPO_ROOT/scripts/verify_setup.sh"
chmod +x "$REPO_ROOT/scripts/mvs_doctor.py" 2>/dev/null || true
chmod +x "$REPO_ROOT/Kokoro_TTS_Agent_Skill_Pack/combine.py" 2>/dev/null || true
ok "executable bits set"

# ── 6. Verify with the doctor (read-only) ─────────────────────────────────
log "Step 6 — Verifying patched repo with mvs_doctor.py..."
echo
if command -v python3 >/dev/null 2>&1; then
  python3 "$REPO_ROOT/scripts/mvs_doctor.py" || {
    echo
    warn "Doctor reported issues. This is OK if you haven't run setup.sh yet —"
    warn "  the doctor expects the model assembled and deps installed."
    warn "  Next: bash setup.sh   (then re-run the doctor)"
  }
else
  warn "python3 not found — cannot run doctor automatically. Run manually:"
  warn "  python3 scripts/mvs_doctor.py"
fi

# ── 7. Summary ────────────────────────────────────────────────────────────
echo
log "Patch set applied."
echo
echo "  Backups at: $BACKUP_DIR"
echo "  To revert:  cp -r '$BACKUP_DIR'/* '$REPO_ROOT'/"
echo
echo "  Next steps:"
echo "    1. bash setup.sh                                          # install everything"
echo "    2. python3 scripts/mvs_doctor.py                          # verify health"
echo "    3. python3 scripts/voiceover.py examples/smoke.storyboard.json --out-dir /tmp/mvs-smoke"
echo "    4. git add -A && git commit -m \"setup-easy patch set\""
echo
echo "  The .gitignore now keeps the assembled model and voices out of commits."
echo "  Source-of-truth artifacts (split parts, kokoro-voices/) stay tracked."
echo
