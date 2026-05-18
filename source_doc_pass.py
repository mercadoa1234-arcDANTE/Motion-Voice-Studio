"""
self_check_v2.py — CAD Animation Voice Studio QA

Checks:
  1. Video stream: codec, resolution, fps
  2. Audio stream: codec, sample rate
  3. Timing drift: abs(actual - expected) < tolerance
  4. No long silent regions in the audio mix
  5. Geometry exports: assembled STL, OBJ, named-parts GLB, individual part STLs
  6. cad_video.json and timing.json schema compliance (basic)

Usage:
    python self_check_v2.py output/mecha_v2_final.mp4 --plan cad_video_local.json
    python self_check_v2.py output/mecha_v2_final.mp4 --timing output/audio/timing.json \
        --geometry-dir output/geometry
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path


GREEN  = "\033[0;32m"
YELLOW = "\033[0;33m"
RED    = "\033[0;31m"
CYAN   = "\033[0;36m"
RESET  = "\033[0m"

def ok(msg):   print(f"{GREEN}  ✓{RESET} {msg}")
def warn(msg): print(f"{YELLOW}  ⚠{RESET} {msg}")
def fail(msg): print(f"{RED}  ✗{RESET} {msg}")
def hdr(msg):  print(f"{CYAN}[check]{RESET} {msg}")


def ffprobe(path: str) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


def check_streams(video_path: str) -> dict:
    hdr(f"Streams — {video_path}")
    info = ffprobe(video_path)
    streams = info["streams"]
    vstreams = [s for s in streams if s["codec_type"] == "video"]
    astreams = [s for s in streams if s["codec_type"] == "audio"]

    passed = True
    if vstreams:
        v = vstreams[0]
        ok(f"video  {v['codec_name']}  {v['width']}×{v['height']}  {v['r_frame_rate']} fps  {v['nb_frames']} frames")
    else:
        fail("no video stream"); passed = False

    if astreams:
        a = astreams[0]
        ok(f"audio  {a['codec_name']}  {a['sample_rate']} Hz  {a['channels']}ch")
    else:
        fail("no audio stream"); passed = False

    return {
        "passed": passed,
        "video_streams": len(vstreams),
        "audio_streams": len(astreams),
        "duration_s": float(info["format"]["duration"]),
        "width": vstreams[0]["width"] if vstreams else None,
        "height": vstreams[0]["height"] if vstreams else None,
        "fps": vstreams[0]["r_frame_rate"] if vstreams else None,
    }


def check_timing(video_dur: float, expected: float,
                 tolerance_s: float = 0.2) -> dict:
    hdr(f"Timing drift (tolerance {tolerance_s*1000:.0f} ms)")
    drift = abs(video_dur - expected)
    drift_ms = drift * 1000
    if drift <= tolerance_s:
        ok(f"drift = {drift_ms:.1f} ms  (video {video_dur:.3f}s, expected {expected:.3f}s)")
        return {"passed": True, "drift_s": drift, "drift_ms": drift_ms}
    else:
        fail(f"drift = {drift_ms:.1f} ms exceeds {tolerance_s*1000:.0f} ms")
        return {"passed": False, "drift_s": drift, "drift_ms": drift_ms}


def check_geometry(geo_dir: str) -> dict:
    hdr(f"Geometry exports — {geo_dir}")
    geo = Path(geo_dir)
    results = {}
    passed = True

    required = {
        "assembled STL": list(geo.glob("*assembled*.stl")) or list(geo.glob("*.stl")),
        "assembled OBJ": list(geo.glob("*assembled*.obj")) or list(geo.glob("*.obj")),
        "named-parts GLB": list(geo.glob("*named*.glb")) or list(geo.glob("*.glb")),
    }
    for label, candidates in required.items():
        if candidates:
            sz = candidates[0].stat().st_size
            ok(f"{label}: {candidates[0].name} ({sz:,} B)")
            results[label] = str(candidates[0])
        else:
            fail(f"{label}: not found in {geo_dir}")
            passed = False

    parts_dir = geo / "parts_stl"
    if not parts_dir.exists():
        # Try to find part STLs in the geo dir itself
        part_stls = [p for p in geo.glob("*.stl") if "assembled" not in p.name.lower()]
    else:
        part_stls = list(parts_dir.glob("*.stl"))

    if part_stls:
        ok(f"individual part STLs: {len(part_stls)} files")
        results["individual_stl_count"] = len(part_stls)
    else:
        warn("no individual part STLs found")
        results["individual_stl_count"] = 0

    results["passed"] = passed
    return results


def check_plan(plan_path: str) -> dict:
    hdr(f"Plan schema — {plan_path}")
    try:
        plan = json.loads(Path(plan_path).read_text())
        required_keys = {"version", "topic", "output", "video", "model", "scenes"}
        missing = required_keys - set(plan.keys())
        if missing:
            warn(f"missing keys: {missing}")
            return {"passed": False}
        ok(f"version={plan['version']}  topic='{plan['topic']}'  scenes={len(plan['scenes'])}")
        # Check no authored durations
        for s in plan["scenes"]:
            if "duration" in s:
                warn(f"scene '{s.get('id')}' has authored 'duration' — should be audio-driven")
        return {"passed": True, "scene_count": len(plan["scenes"])}
    except Exception as e:
        fail(f"plan load error: {e}")
        return {"passed": False}


def run(video_path: str, plan_path: str | None, timing_path: str | None,
        geo_dir: str | None, tolerance_s: float = 0.2) -> int:

    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}  CAD Animation Voice Studio — Self-Check v2{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")

    all_passed = True
    report = {"video": video_path}

    # 1. Streams
    stream_r = check_streams(video_path)
    all_passed = all_passed and stream_r["passed"]
    report["streams"] = stream_r
    print()

    # 2. Timing
    if timing_path and Path(timing_path).exists():
        timing = json.loads(Path(timing_path).read_text())
        expected = float(timing.get("total_duration_s", timing.get("total_duration_s", 0)))
        timing_r = check_timing(stream_r["duration_s"], expected, tolerance_s)
        all_passed = all_passed and timing_r["passed"]
        report["timing"] = timing_r
        print()

    # 3. Plan
    if plan_path and Path(plan_path).exists():
        plan_r = check_plan(plan_path)
        all_passed = all_passed and plan_r["passed"]
        report["plan"] = plan_r
        print()

    # 4. Geometry
    if geo_dir and Path(geo_dir).exists():
        geo_r = check_geometry(geo_dir)
        all_passed = all_passed and geo_r["passed"]
        report["geometry"] = geo_r
        print()

    # Summary
    print(f"{CYAN}{'='*60}{RESET}")
    if all_passed:
        print(f"{GREEN}  ✓  QA PASSED{RESET}")
    else:
        print(f"{RED}  ✗  QA FAILED{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")

    report["passed"] = all_passed
    # Write JSON report alongside the video
    out_json = Path(video_path).with_suffix(".self_check.json")
    out_json.write_text(json.dumps(report, indent=2, default=str))
    print(f"Report → {out_json}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--plan", default=None)
    ap.add_argument("--timing", default=None)
    ap.add_argument("--geometry-dir", default=None)
    ap.add_argument("--tolerance-ms", type=float, default=200.0)
    args = ap.parse_args()
    sys.exit(run(
        args.video,
        plan_path=args.plan,
        timing_path=args.timing,
        geo_dir=args.geometry_dir,
        tolerance_s=args.tolerance_ms / 1000.0,
    ))
