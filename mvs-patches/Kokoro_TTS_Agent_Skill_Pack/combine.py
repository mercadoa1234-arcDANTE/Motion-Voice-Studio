#!/usr/bin/env python3
"""
combine.py — Reassemble kokoro-v1_0_fp16.onnx from its parts.

Usage:
    python combine.py                          # auto-discover parts, reassemble next to manifest
    python combine.py --out path/              # reassemble into a different directory
    python combine.py --parts-dir path/        # parts live somewhere other than next to manifest
    python combine.py --no-verify              # skip SHA256 verification (faster, not recommended)

Auto-discovery: if the manifest's directory has no .partNN files, this script
looks in common sibling locations (../Kokoro_Model_Split_Files/, ./parts/,
./split/) before failing. This handles the common case where the manifest and
the parts ship in separate folders of the same repo.

Cross-platform: works on Windows, macOS, and Linux with stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CHUNK_READ = 8 * 1024 * 1024  # 8 MiB streaming buffer

# Where to look for parts if they're not next to the manifest.
# Order matters: first hit wins.
AUTO_DISCOVERY_DIRS = [
    "../Kokoro_Model_Split_Files",
    "../kokoro-model-split-files",
    "./parts",
    "./split",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK_READ), b""):
            h.update(block)
    return h.hexdigest()


def find_parts_dir(manifest_path: Path, manifest: dict, override: Path | None) -> Path:
    """Locate the directory containing the .partNN files.

    Resolution order:
      1. --parts-dir override (if given)
      2. The manifest's own directory
      3. Each entry in AUTO_DISCOVERY_DIRS, relative to the manifest
    """
    if override is not None:
        if not override.is_dir():
            raise FileNotFoundError(f"--parts-dir not a directory: {override}")
        return override.resolve()

    candidates = [manifest_path.parent]
    for rel in AUTO_DISCOVERY_DIRS:
        candidates.append((manifest_path.parent / rel).resolve())

    first_part_name = manifest["parts"][0]["name"]
    for d in candidates:
        if (d / first_part_name).is_file():
            return d.resolve()

    raise FileNotFoundError(
        f"No directory containing {first_part_name} found.\n"
        f"  Searched: {[str(c) for c in candidates]}\n"
        f"  Hint: pass --parts-dir <path> if your .partNN files live elsewhere."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reassemble kokoro-v1_0_fp16.onnx from .partNN chunks."
    )
    parser.add_argument("--manifest", default="manifest.json",
                        help="Path to manifest.json (default: ./manifest.json)")
    parser.add_argument("--out", default=".",
                        help="Output directory (default: current directory)")
    parser.add_argument("--parts-dir", default=None,
                        help="Directory containing .partNN files "
                             "(default: auto-discover near manifest)")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip SHA256 verification of parts and output")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.is_file():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    override = Path(args.parts_dir).resolve() if args.parts_dir else None
    try:
        parts_dir = find_parts_dir(manifest_path, manifest, override)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / manifest["original_filename"]

    # 1. Sanity-check that every part exists and is the right size
    print(f"Found {manifest['part_count']} parts in: {parts_dir}")
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
