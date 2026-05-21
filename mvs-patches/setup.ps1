# setup.ps1 — one-shot Motion-Voice-Studio installer for Windows.
#
# What this does:
#   1. winget or choco: ffmpeg, espeak-ng, miktex (optional)
#   2. pip: install requirements.txt (pinned)
#   3. Assemble the Kokoro fp16 ONNX model from bundled split parts
#   4. Stage voices into .\voices\
#   5. Run verify_setup.ps1 if present, or basic Python smoke tests
#
# Run from the repo root in an admin PowerShell:
#   .\setup.ps1
#
# To skip MiKTeX install (saves ~1 GB), set: $env:INSTALL_LATEX = "0"

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Log($msg)  { Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  ✓ $msg"     -ForegroundColor Green }
function Warn($msg) { Write-Host "  ⚠ $msg"     -ForegroundColor Yellow }
function ErrMsg($msg) { Write-Host "  ✗ $msg"   -ForegroundColor Red }

# ── 1. System packages ────────────────────────────────────────────────────

Log "System packages..."

function Test-Installed($cmd) {
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

$useWinget = Test-Installed "winget"
$useChoco  = Test-Installed "choco"

if (-not $useWinget -and -not $useChoco) {
    ErrMsg "Neither winget nor chocolatey found."
    ErrMsg "Install one of them first, or install these tools manually:"
    ErrMsg "  ffmpeg, espeak-ng, miktex (optional)"
    exit 1
}

function Install-If-Missing($cmd, $wingetId, $chocoId) {
    if (Test-Installed $cmd) {
        Ok "$cmd already installed"
        return
    }
    if ($useWinget) {
        winget install --silent --accept-source-agreements --accept-package-agreements --id $wingetId | Out-Null
    } elseif ($useChoco) {
        choco install -y $chocoId | Out-Null
    }
    if (Test-Installed $cmd) { Ok "$cmd installed" } else { Warn "$cmd install reported no error but command still not found — restart PowerShell and re-run" }
}

Install-If-Missing "ffmpeg"   "Gyan.FFmpeg"        "ffmpeg"
Install-If-Missing "espeak-ng" "eSpeak-NG.eSpeak-NG" "espeak-ng"

if ($env:INSTALL_LATEX -ne "0") {
    Log "Installing MiKTeX (set `$env:INSTALL_LATEX = '0' to skip)..."
    Install-If-Missing "miktex-console" "MiKTeX.MiKTeX" "miktex"
} else {
    Warn "Skipping MiKTeX. manim Text() works, MathTex() will fall back to plain text."
}

# ── 2. Python packages ────────────────────────────────────────────────────

Log "Python packages from requirements.txt..."

if (-not (Test-Path "$RepoRoot\requirements.txt")) {
    ErrMsg "requirements.txt not found at $RepoRoot\requirements.txt"
    exit 2
}

python -m pip install -q -r "$RepoRoot\requirements.txt"
Ok "pip install -r requirements.txt"

# ── 3. Assemble the Kokoro model ──────────────────────────────────────────

Log "Assembling Kokoro fp16 ONNX model from bundled split parts..."

$Manifest = Join-Path $RepoRoot "Kokoro_TTS_Agent_Skill_Pack\manifest.json"
$ModelDir = Join-Path $RepoRoot "model"
$ModelOut = Join-Path $ModelDir "kokoro-v1_0_fp16.onnx"

if (-not (Test-Path $Manifest)) {
    ErrMsg "Kokoro manifest not found at $Manifest"
    exit 3
}

New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

if ((Test-Path $ModelOut) -and ((Get-Item $ModelOut).Length -gt 0)) {
    $sizeMB = [math]::Round((Get-Item $ModelOut).Length / 1MB, 1)
    Ok "model already assembled (${sizeMB} MB) — skipping"
} else {
    python "$RepoRoot\Kokoro_TTS_Agent_Skill_Pack\combine.py" `
        --manifest $Manifest `
        --out $ModelDir
    if ($LASTEXITCODE -ne 0) { ErrMsg "combine.py failed (rc=$LASTEXITCODE)"; exit 4 }
    Ok "model assembled → model\kokoro-v1_0_fp16.onnx"
}

# Stage config.json
$ConfigSrc = Join-Path $RepoRoot "Kokoro_TTS_Agent_Skill_Pack\config.json"
$ConfigDst = Join-Path $ModelDir "config.json"
if (-not (Test-Path $ConfigDst)) {
    if (Test-Path $ConfigSrc) {
        Copy-Item $ConfigSrc $ConfigDst
        Ok "staged model\config.json"
    } else {
        ErrMsg "config.json not found in Kokoro_TTS_Agent_Skill_Pack\"
        exit 5
    }
}

# ── 4. Stage voices ───────────────────────────────────────────────────────

Log "Staging voices..."
$VoicesSrc = Join-Path $RepoRoot "kokoro-voices"
$VoicesDst = Join-Path $RepoRoot "voices"
New-Item -ItemType Directory -Force -Path $VoicesDst | Out-Null

if (Test-Path $VoicesSrc) {
    $copied = 0
    Get-ChildItem -Path $VoicesSrc -Filter "*.pt" | ForEach-Object {
        $dst = Join-Path $VoicesDst $_.Name
        if (-not (Test-Path $dst)) {
            Copy-Item $_.FullName $dst
            $copied++
        }
    }
    $total = (Get-ChildItem -Path $VoicesDst -Filter "*.pt").Count
    Ok "$total voice(s) in voices\ (newly staged: $copied)"
} else {
    Warn "kokoro-voices\ directory not found — checking voices\ alone"
}

# ── 5. Smoke test ─────────────────────────────────────────────────────────

Log "Running Kokoro smoke test..."

$smokeCode = @"
import sys, time
sys.path.insert(0, r"$RepoRoot\scripts")
from kokoro_engine import KokoroEngine
t0 = time.time()
eng = KokoroEngine(r"$ModelOut", r"$ConfigDst", r"$VoicesDst")
voices = eng.list_voices()
v = "af_bella" if "af_bella" in voices else voices[0]
audio, sr = eng.synthesize("Setup verified.", voice=v)
print(f"  kokoro {v}: {len(audio)/sr:.2f}s in {time.time()-t0:.2f}s")
"@

$smokeCode | python -
if ($LASTEXITCODE -eq 0) { Ok "Kokoro smoke ok" } else { Warn "Kokoro smoke failed (rc=$LASTEXITCODE)" }

# Manim smoke
Log "Running Manim smoke test..."
$manimCode = @"
import tempfile, os, subprocess, sys
tmp = tempfile.mkdtemp(prefix='mvs-smoke-')
scene_path = os.path.join(tmp, '_smoke.py')
with open(scene_path, 'w') as f:
    f.write('from manim import *\nclass Smoke(Scene):\n    def construct(self):\n        t = Text(\"ok\", color=WHITE)\n        self.play(FadeIn(t), run_time=0.3)\n        self.wait(0.2)\n')
result = subprocess.run(['manim','render','-ql','--disable_caching','--media_dir',tmp,scene_path,'Smoke'], capture_output=True, text=True)
movs = []
for root, _, files in os.walk(tmp):
    for fn in files:
        if fn.endswith('.mp4') or fn.endswith('.mov'):
            movs.append(os.path.join(root, fn))
if movs:
    print(f'  manim rendered: {os.path.basename(movs[0])}')
else:
    print(f'  manim FAILED: {result.stderr[:200]}')
    sys.exit(1)
"@

$manimCode | python -
if ($LASTEXITCODE -eq 0) { Ok "Manim smoke ok" } else { Warn "Manim smoke failed (rc=$LASTEXITCODE)" }

Ok "Setup complete. Try the smoke storyboard:"
Write-Host "  python scripts\voiceover.py examples\smoke.storyboard.json --out-dir `$env:TEMP\mvs-smoke"
