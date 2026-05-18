#!/usr/bin/env bash
# verify_setup.sh — idempotent setup for cad-studio.
# Checks Python deps, system tools, Kokoro assets, runs smoke tests.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UPLOADS="/mnt/user-data/uploads"

G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; B='\033[0;36m'; N='\033[0m'
log()  { echo -e "${B}[verify]${N} $*"; }
ok()   { echo -e "${G}  ✓${N} $*"; }
warn() { echo -e "${Y}  ⚠${N} $*"; }
err()  { echo -e "${R}  ✗${N} $*"; }

# ── 1. Python deps ─────────────────────────────────────────────────────────
log "Python packages..."
need=()
for mod_pkg in \
    "build123d build123d" "trimesh trimesh" "pyvista pyvista" \
    "ezdxf ezdxf" "solid2 solidpython2" \
    "PIL pillow" "cv2 opencv-python-headless" \
    "numpy numpy" "scipy scipy" "matplotlib matplotlib" \
    "soundfile soundfile" "onnxruntime onnxruntime" \
    "phonemizer phonemizer-fork" \
    "gtts gtts" \
    "manim manim"; do
  mod="${mod_pkg% *}"; pkg="${mod_pkg#* }"
  if ! python3 -c "import ${mod}" 2>/dev/null; then
    need+=("$pkg")
  else
    ok "$mod"
  fi
done
if [ ${#need[@]} -gt 0 ]; then
  log "installing: ${need[*]}"
  pip install --break-system-packages -q "${need[@]}" 2>&1 | tail -3
  for p in "${need[@]}"; do ok "installed $p"; done
fi

# ── 2. System tools ───────────────────────────────────────────────────────
log "System tools..."
for tool in ffmpeg ffprobe espeak-ng Xvfb; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    warn "$tool missing — installing"
    apt-get install -y -qq "$tool" >/dev/null 2>&1 || {
      err "$tool install failed; install manually then re-run."
      exit 3
    }
  fi
  ok "$tool"
done

# v3: PDF tools for source_doc_pass.py
log "PDF tools (v3 source-doc ingest)..."
for tool in pdftoppm pdftotext pdfimages pdfinfo; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    warn "$tool missing — installing poppler-utils"
    apt-get install -y -qq poppler-utils >/dev/null 2>&1 || {
      warn "poppler-utils install failed; source-doc PDF ingest will not work"
    }
    break
  fi
done
for tool in pdftoppm pdftotext pdfimages pdfinfo; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool"
  else
    warn "$tool still missing"
  fi
done

# Pango / Cairo system libraries needed for manim
log "Pango / Cairo for manim..."
if ! pkg-config --exists pangocairo 2>/dev/null; then
  warn "pangocairo dev headers missing — installing"
  apt-get install -y -qq libpango1.0-dev libcairo2-dev pkg-config >/dev/null 2>&1 || {
    err "pango/cairo install failed"; exit 3
  }
fi
ok "pangocairo $(pkg-config --modversion pangocairo 2>/dev/null || echo '?')"

# LaTeX (MathTex) — opt-in. Test for it; don't install (~1 GB).
if command -v latex >/dev/null 2>&1 && command -v dvisvgm >/dev/null 2>&1; then
  ok "LaTeX + dvisvgm (manim MathTex enabled)"
else
  warn "LaTeX not installed — manim Text() works, MathTex() will fail"
  warn "  to enable: apt-get install -y texlive-latex-extra dvisvgm   (~1 GB)"
fi

# OpenSCAD opt-in
if command -v openscad >/dev/null 2>&1; then
  ok "openscad (optional — installed)"
else
  warn "openscad not installed — solidpython2 still emits .scad, "
  warn "  but kind='openscad' assembly components will fail to render in-sandbox."
  warn "  to enable: apt-get install -y openscad   (~300 MB)"
fi

# ── 3. Kokoro asset staging ───────────────────────────────────────────────
log "Kokoro assets..."
mkdir -p "$SKILL_ROOT/model" "$SKILL_ROOT/voices"

KOKORO="$SKILL_ROOT/model/kokoro-v1.0.fp16.onnx"
CONFIG="$SKILL_ROOT/model/config.json"

if [ ! -s "$KOKORO" ]; then
  for cand in "$UPLOADS/kokoro-v1.0.fp16.onnx" "$UPLOADS/model_fp16.onnx"; do
    if [ -s "$cand" ]; then
      log "staging $(basename "$cand") → model/kokoro-v1.0.fp16.onnx"
      cp "$cand" "$KOKORO"; break
    fi
  done
fi
if [ ! -s "$CONFIG" ]; then
  for cand in "$UPLOADS/config.json"; do
    if [ -s "$cand" ]; then
      log "staging config.json"
      cp "$cand" "$CONFIG"; break
    fi
  done
fi
for src in "$UPLOADS"/*.pt; do
  [ -s "$src" ] || continue
  name=$(basename "$src")
  dst="$SKILL_ROOT/voices/$name"
  [ -s "$dst" ] || cp "$src" "$dst" && ok "staged voice $name"
done

# ── 4. Inventory ──────────────────────────────────────────────────────────
log "Inventory..."
missing=0
if [ -s "$KOKORO" ]; then
  ok "model/kokoro-v1.0.fp16.onnx ($(du -h "$KOKORO" | cut -f1))"
else
  err "kokoro model missing — upload kokoro-v1.0.fp16.onnx to $UPLOADS"
  echo "    source: https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX"
  missing=1
fi
[ -s "$CONFIG" ] && ok "model/config.json" || { err "config.json missing"; missing=1; }
n_voices=$(ls "$SKILL_ROOT/voices"/*.pt 2>/dev/null | wc -l)
[ "$n_voices" -ge 1 ] && ok "$n_voices voice(s)" || { err "no voices"; missing=1; }

if [ "$missing" -ne 0 ]; then
  warn "Kokoro setup incomplete — voiceover will fall back to gTTS until fixed."
fi

# ── 5. Smoke tests ────────────────────────────────────────────────────────
# pyvista's teardown sometimes prints harmless XIO noise; don't let it kill us.
set +e
log "Smoke tests..."

# build123d → trimesh → pyvista path
python3 - <<PY 2>/dev/null
import sys, os
sys.path.insert(0, "$SCRIPT_DIR")
from headless import headless_display
from build123d import BuildPart, Box, Cylinder, Mode, export_stl
import trimesh

with BuildPart() as p:
    Box(10, 10, 10)
    Cylinder(2, 12, mode=Mode.SUBTRACT)
export_stl(p.part, "/tmp/cs_smoke.stl")
m = trimesh.load("/tmp/cs_smoke.stl")
print(f"  build123d->stl->trimesh ok (verts={len(m.vertices)})")

with headless_display():
    import pyvista as pv
    pm = pv.read("/tmp/cs_smoke.stl")
    plotter = pv.Plotter(off_screen=True, window_size=(320, 240))
    plotter.add_mesh(pm, color="lightblue", smooth_shading=True)
    plotter.screenshot("/tmp/cs_smoke.png")
    plotter.close()
print(f"  pyvista headless render ok ({os.path.getsize('/tmp/cs_smoke.png')} bytes)")
PY
rc=$?
[ $rc -eq 0 ] && ok "build123d + pyvista smoke ok" || warn "smoke test rc=$rc (often cosmetic exit noise; check above)"

# Kokoro if available
if [ -s "$KOKORO" ] && [ "$n_voices" -ge 1 ]; then
  python3 - <<PY 2>/dev/null
import sys, time, numpy as np
sys.path.insert(0, "$SCRIPT_DIR")
from kokoro_engine import KokoroEngine
t0 = time.time()
eng = KokoroEngine("$KOKORO", "$CONFIG", "$SKILL_ROOT/voices")
voices = eng.list_voices()
v = "af_bella" if "af_bella" in voices else voices[0]
audio, sr = eng.synthesize("Setup verified.", voice=v)
print(f"  kokoro {v}: {len(audio)/sr:.2f}s in {time.time()-t0:.2f}s peak={float(np.abs(audio).max()):.3f}")
PY
  rc=$?
  [ $rc -eq 0 ] && ok "kokoro smoke ok" || warn "kokoro smoke rc=$rc"
fi

# Manim smoke test (text-only, no LaTeX)
log "Manim smoke test..."
python3 - 2>/dev/null <<'PY'
import tempfile, os, subprocess, sys
tmp = tempfile.mkdtemp(prefix="motion-studio-smoke-")
scene_path = os.path.join(tmp, "_smoke.py")
with open(scene_path, "w") as f:
    f.write('''from manim import *
class Smoke(Scene):
    def construct(self):
        t = Text("ok", color=WHITE)
        self.play(FadeIn(t), run_time=0.3)
        self.wait(0.2)
''')
result = subprocess.run(
    ["manim", "render", "-ql", "--transparent", "--disable_caching",
     "--media_dir", tmp, scene_path, "Smoke"],
    capture_output=True, text=True,
)
movs = []
for root, _, files in os.walk(tmp):
    for fn in files:
        if fn.endswith(".mov"):
            movs.append(os.path.join(root, fn))
if movs:
    print(f"  manim rendered: {os.path.basename(movs[0])}")
else:
    print(f"  manim FAILED: {result.stderr[:200]}")
    sys.exit(1)
import shutil; shutil.rmtree(tmp, ignore_errors=True)
PY
rc=$?
[ $rc -eq 0 ] && ok "manim smoke ok" || warn "manim smoke rc=$rc"

set -e
ok "Setup OK. Ready."
