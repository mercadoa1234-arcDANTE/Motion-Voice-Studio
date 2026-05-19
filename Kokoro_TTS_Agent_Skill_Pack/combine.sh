#!/usr/bin/env bash
# combine.sh — Reassemble kokoro-v1_0_fp16.onnx from its parts.
#
# Usage:
#   ./combine.sh                # reassemble into current directory, verify SHA256
#   ./combine.sh -o /some/dir   # reassemble into a different directory
#   ./combine.sh --no-verify    # skip checksum check
#
# Requires: cat, sha256sum (Linux) or shasum (macOS). No Python needed.

set -euo pipefail

OUT_DIR="."
VERIFY=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--out) OUT_DIR="$2"; shift 2;;
    --no-verify) VERIFY=0; shift;;
    -h|--help)
      sed -n '2,12p' "$0"; exit 0;;
    *) echo "Unknown arg: $1" >&2; exit 64;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIG_NAME="kokoro-v1_0_fp16.onnx"
EXPECTED_SHA="ba4527a874b42b21e35f468c10d326fdff3c7fc8cac1f85e9eb6c0dfc35c334a"
EXPECTED_SIZE=163234740
# Note: original size and SHA are unchanged regardless of chunk size — same source file.

mkdir -p "$OUT_DIR"
OUT_PATH="$OUT_DIR/$ORIG_NAME"

# Pick a sha256 tool: GNU coreutils on Linux, BSD shasum on macOS
if command -v sha256sum >/dev/null 2>&1; then
  sha_cmd() { sha256sum "$1" | awk '{print $1}'; }
elif command -v shasum >/dev/null 2>&1; then
  sha_cmd() { shasum -a 256 "$1" | awk '{print $1}'; }
else
  echo "ERROR: neither sha256sum nor shasum is installed." >&2
  exit 1
fi

# Confirm every part is present before doing any work
parts=( "$SCRIPT_DIR"/${ORIG_NAME}.part?? )
if [[ ! -e "${parts[0]}" ]]; then
  echo "ERROR: no parts found matching ${ORIG_NAME}.part?? in $SCRIPT_DIR" >&2
  exit 2
fi
echo "Found ${#parts[@]} parts in $SCRIPT_DIR"

# Concatenate in sorted order (part00, part01, ...)
echo "Writing $OUT_PATH ..."
cat "${parts[@]}" > "$OUT_PATH"

# Verify size
actual_size=$(stat -c %s "$OUT_PATH" 2>/dev/null || stat -f %z "$OUT_PATH")
if [[ "$actual_size" != "$EXPECTED_SIZE" ]]; then
  echo "ERROR: size mismatch: expected $EXPECTED_SIZE, got $actual_size" >&2
  exit 3
fi

# Verify SHA256 unless skipped
if [[ "$VERIFY" == "1" ]]; then
  echo "Verifying SHA256..."
  actual_sha=$(sha_cmd "$OUT_PATH")
  if [[ "$actual_sha" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: SHA256 mismatch" >&2
    echo "  expected: $EXPECTED_SHA" >&2
    echo "  actual:   $actual_sha" >&2
    exit 4
  fi
  echo "  ok  sha256=$actual_sha"
fi

echo
echo "Done. Reassembled: $OUT_PATH ($actual_size bytes)"
