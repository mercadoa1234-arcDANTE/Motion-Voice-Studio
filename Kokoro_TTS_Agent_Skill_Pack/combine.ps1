# combine.ps1 — Reassemble kokoro-v1_0_fp16.onnx from its parts on Windows.
#
# Usage:
#   .\combine.ps1                       # reassemble into current dir, verify
#   .\combine.ps1 -OutDir C:\models     # reassemble elsewhere
#   .\combine.ps1 -NoVerify             # skip checksum check
#
# Requires: PowerShell 5.1+ (built into Windows 10/11). No extra installs.

[CmdletBinding()]
param(
    [string]$OutDir = ".",
    [switch]$NoVerify
)

$ErrorActionPreference = "Stop"

$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$OrigName      = "kokoro-v1_0_fp16.onnx"
$ExpectedSha   = "ba4527a874b42b21e35f468c10d326fdff3c7fc8cac1f85e9eb6c0dfc35c334a"
$ExpectedSize  = 163234740

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$OutPath = Join-Path $OutDir $OrigName

# Find and sort parts
$Parts = Get-ChildItem -Path $ScriptDir -Filter "$OrigName.part*" | Sort-Object Name
if ($Parts.Count -eq 0) {
    Write-Error "No parts found matching $OrigName.part* in $ScriptDir"
    exit 2
}
Write-Host "Found $($Parts.Count) parts in $ScriptDir"

# Concatenate using a FileStream so we never load the whole thing into memory
Write-Host "Writing $OutPath ..."
$Out = [System.IO.File]::Create($OutPath)
try {
    foreach ($p in $Parts) {
        $In = [System.IO.File]::OpenRead($p.FullName)
        try {
            $In.CopyTo($Out, 8MB)
        } finally {
            $In.Dispose()
        }
    }
} finally {
    $Out.Dispose()
}

# Verify size
$ActualSize = (Get-Item $OutPath).Length
if ($ActualSize -ne $ExpectedSize) {
    Write-Error "Size mismatch: expected $ExpectedSize, got $ActualSize"
    exit 3
}

# Verify SHA256
if (-not $NoVerify) {
    Write-Host "Verifying SHA256..."
    $Hash = (Get-FileHash -Path $OutPath -Algorithm SHA256).Hash.ToLower()
    if ($Hash -ne $ExpectedSha) {
        Write-Error "SHA256 mismatch:`n  expected: $ExpectedSha`n  actual:   $Hash"
        exit 4
    }
    Write-Host "  ok  sha256=$Hash"
}

Write-Host ""
Write-Host "Done. Reassembled: $OutPath ($ActualSize bytes)"
