#!/usr/bin/env python3
"""
combine.py — Reassemble kokoro-v1_0_fp16.onnx from its parts.

Usage:
    python combine.py                  # reassemble into the current directory
    python combine.py --out path/      # reassemble into a different directory
    python combine.py --no-verify      # skip SHA256 verification (faster, not recommended)

Cross-platform: works on Windows, macOS, and Linux with stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CHUNK_READ = 8 * 1024 * 1024  # 8 MiB streaming buffer


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK_READ), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Reassemble kokoro-v1_0_fp16.onnx from .partNN chunks.")
    parser.add_argument("--manifest", default="manifest.json", help="Path to manifest.json (default: ./manifest.json)")
    parser.add_argument("--out", default=".", help="Output directory (default: current directory)")
    parser.add_argument("--no-verify", action="store_true", help="Skip SHA256 verification of parts and output")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parts_dir = manifest_path.parent
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / manifest["original_filename"]

    # 1. Sanity-check that every part exists and is the right size
    print(f"Found {manifest['part_count']} parts in: {parts_dir.resolve()}")
    for part in manifest["parts"]:
        p = parts_dir / part["name"]
        if not p.is_file():
            print(f"ERROR: missing part: {p}", file=sys.stderr)
            return 2
        actual = p.stat().st_size
        if actual != part["size_bytes"]:
            print(f"ERROR: size mismatch on {p.name}: expected {part['size_bytes']}, got {actual}", file=sys.stderr)
            return 3

    # 2. Optional: verify each part's SHA256 before concatenating
    if not args.no_verify:
        print("Verifying part checksums...")
        for part in manifest["parts"]:
            p = parts_dir / part["name"]
            actual = sha256_of(p)
            if actual != part["sha256"]:
                print(f"ERROR: SHA256 mismatch on {p.name}", file=sys.stderr)
                print(f"  expected: {part['sha256']}", file=sys.stderr)
                print(f"  actual:   {actual}", file=sys.stderr)
                return 4
            print(f"  ok  {p.name}")

    # 3. Concatenate parts in manifest order using streaming I/O
    print(f"Writing {out_path} ...")
    with out_path.open("wb") as out_f:
        for part in manifest["parts"]:
            p = parts_dir / part["name"]
            with p.open("rb") as in_f:
                for block in iter(lambda: in_f.read(CHUNK_READ), b""):
                    out_f.write(block)

    # 4. Verify final file size and SHA256
    final_size = out_path.stat().st_size
    if final_size != manifest["original_size_bytes"]:
        print(f"ERROR: final size mismatch: expected {manifest['original_size_bytes']}, got {final_size}", file=sys.stderr)
        return 5

    if not args.no_verify:
        print("Verifying reassembled file checksum...")
        actual = sha256_of(out_path)
        if actual != manifest["original_sha256"]:
            print("ERROR: final SHA256 does not match original.", file=sys.stderr)
            print(f"  expected: {manifest['original_sha256']}", file=sys.stderr)
            print(f"  actual:   {actual}", file=sys.stderr)
            return 6
        print(f"  ok  sha256={actual}")

    print(f"\nDone. Reassembled: {out_path} ({final_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
