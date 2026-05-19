#!/usr/bin/env python3
"""
split.py — Re-chunk a single binary file into <25 MB parts plus a manifest.

Useful if you update kokoro-v1_0_fp16.onnx (or any binary) and want to refresh
the .partNN files + manifest.json before committing to GitHub.

Usage:
    python split.py kokoro-v1_0_fp16.onnx
    python split.py path/to/file.bin --out-dir ./chunks --chunk-mib 24
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

READ_BUF = 8 * 1024 * 1024


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(READ_BUF), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Split a binary file into <25 MB chunks for GitHub.")
    ap.add_argument("source", help="Path to the file to split")
    ap.add_argument("--out-dir", default=".", help="Where to write parts + manifest (default: current dir)")
    ap.add_argument(
        "--chunk-mb",
        type=int,
        default=24,
        help="Chunk size in MB (decimal, default 24). Must be < 25 to stay under GitHub's upload cap.",
    )
    args = ap.parse_args()

    if args.chunk_mb >= 25:
        print("ERROR: --chunk-mb must be < 25 to stay under GitHub's 25 MB upload limit.", file=sys.stderr)
        return 1

    src = Path(args.source)
    if not src.is_file():
        print(f"ERROR: not a file: {src}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chunk_bytes = args.chunk_mb * 1_000_000  # decimal MB to stay strictly under 25 MB cap
    total_size = src.stat().st_size
    print(f"Splitting {src.name} ({total_size:,} bytes) into {args.chunk_mb} MB (decimal) chunks...")

    parts: list[dict] = []
    idx = 0
    with src.open("rb") as f:
        while True:
            blob = f.read(chunk_bytes)
            if not blob:
                break
            name = f"{src.name}.part{idx:02d}"
            part_path = out_dir / name
            part_path.write_bytes(blob)
            parts.append({
                "name": name,
                "size_bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            })
            print(f"  wrote {name} ({len(blob):,} bytes)")
            idx += 1

    manifest = {
        "schema": "split-file/v1",
        "original_filename": src.name,
        "original_size_bytes": total_size,
        "original_sha256": sha256_of(src),
        "split_method": "raw byte concatenation (binary append, no compression, no encoding)",
        "chunk_size_bytes": chunk_bytes,
        "chunk_size_human": f"{args.chunk_mb} MB (decimal)",
        "reason": "GitHub blocks single-file uploads above 25 MB through the web UI.",
        "part_count": len(parts),
        "parts": parts,
        "reassembly": {
            "order": "lexicographic by filename (part00, part01, ...)",
            "operation": f"cat parts in order > {src.name}",
            "verify": "sha256(reassembled) must equal original_sha256",
        },
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")
    print(f"Done. {len(parts)} parts in {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
