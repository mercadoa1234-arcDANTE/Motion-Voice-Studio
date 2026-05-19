"""
audio_master.py — v3 audio mastering pass.

Applies post-Kokoro mastering to a WAV file:
  1. Noise floor reduction (afftdn) — gentle de-noise of ambient sound floor
  2. Two-pass loudness normalization (loudnorm) — to -14 LUFS for video,
     -16 LUFS for podcast (per Anthony's spec, May 2026 review)
  3. Optional subtle reverb (aecho) — blends voice into other audio tracks

This mirrors what a REAPER session with ReFir + loudnorm would do, but
runs entirely in ffmpeg so it ships with the skill (no DAW dependency).

Usage as library:
    from audio_master import master_audio
    master_audio('in.wav', 'out.wav', target_lufs=-14, denoise=True, reverb='subtle')

CLI:
    python audio_master.py in.wav out.wav --lufs -14 --denoise --reverb subtle
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


# Reverb presets — aecho parameters (in_gain : out_gain : delays_ms : decays)
REVERB_PRESETS = {
    'none':    None,
    'subtle':  '0.8:0.88:60:0.4',     # short slap-back, very low wet
    'room':    '0.7:0.85:60|120:0.3|0.2',
    'hall':    '0.6:0.8:100|200|350:0.5|0.3|0.2',
}

DEFAULT_LUFS_VIDEO = -14.0
DEFAULT_LUFS_PODCAST = -16.0
DEFAULT_LRA = 11.0       # loudness range target
DEFAULT_TP = -1.5         # true peak target (dBTP)


def master_audio(
    in_path: str,
    out_path: str,
    target_lufs: float = DEFAULT_LUFS_VIDEO,
    denoise: bool = True,
    denoise_nr: float = 12.0,   # noise reduction (dB), 8-20 reasonable
    denoise_nt: str = 'w',       # noise type: w=white, v=vinyl, s=shellac
    reverb: str = 'none',        # 'none' | 'subtle' | 'room' | 'hall'
    lra: float = DEFAULT_LRA,
    tp: float = DEFAULT_TP,
    verbose: bool = False,
) -> dict:
    """Apply mastering filters to a WAV and write the result.

    Returns a dict with measured loudness stats:
        {'input_lufs': float, 'output_lufs': float, 'true_peak': float}
    """
    in_path = str(in_path); out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Build filter chain.
    filters = []
    if denoise:
        # afftdn: FFT denoiser. nr=noise reduction in dB; nt=noise type guess.
        filters.append(f'afftdn=nr={denoise_nr}:nf=-25:tn=1')
    rv = REVERB_PRESETS.get(reverb, None)
    if rv:
        filters.append(f'aecho={rv}')

    # Pass 1: analyze loudness (loudnorm in print_format=json mode)
    pre_filter = ','.join(filters) if filters else None
    analyze_cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'info', '-i', in_path]
    if pre_filter:
        analyze_cmd += ['-af', f'{pre_filter},loudnorm=I={target_lufs}:LRA={lra}:TP={tp}:print_format=json']
    else:
        analyze_cmd += ['-af', f'loudnorm=I={target_lufs}:LRA={lra}:TP={tp}:print_format=json']
    analyze_cmd += ['-f', 'null', '-']

    if verbose:
        print(f'  [audio_master] analyze: {" ".join(analyze_cmd)}', flush=True)
    res = subprocess.run(analyze_cmd, capture_output=True, text=True)
    stderr = res.stderr or ''
    stats = _parse_loudnorm_json(stderr)

    # Pass 2: actual mastering with measured loudness inputs
    measured_args = ''
    if stats:
        measured_args = (
            f':measured_I={stats["input_i"]}'
            f':measured_LRA={stats["input_lra"]}'
            f':measured_TP={stats["input_tp"]}'
            f':measured_thresh={stats["input_thresh"]}'
            f':offset={stats["target_offset"]}:linear=true'
        )
    if pre_filter:
        chain = f'{pre_filter},loudnorm=I={target_lufs}:LRA={lra}:TP={tp}{measured_args}'
    else:
        chain = f'loudnorm=I={target_lufs}:LRA={lra}:TP={tp}{measured_args}'

    apply_cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-i', in_path,
        '-af', chain,
        '-ar', '24000', '-ac', '1',
        out_path,
    ]
    if verbose:
        print(f'  [audio_master] apply: {" ".join(apply_cmd)}', flush=True)
    subprocess.run(apply_cmd, check=True)

    # Verify
    final_stats = _measure_loudness(out_path)
    result = {
        'input_lufs': stats.get('input_i') if stats else None,
        'output_lufs': final_stats.get('output_i'),
        'true_peak': final_stats.get('output_tp'),
        'target_lufs': target_lufs,
        'denoise': denoise,
        'reverb': reverb,
    }
    if verbose:
        print(f'  [audio_master] {in_path} → {out_path}')
        print(f'    input  LUFS: {result["input_lufs"]}')
        print(f'    output LUFS: {result["output_lufs"]}')
        print(f'    true peak  : {result["true_peak"]} dBTP')
    return result


def _parse_loudnorm_json(stderr: str) -> dict:
    """Extract the JSON block from loudnorm's stderr output."""
    # loudnorm prints a JSON object at the end of stderr. Find the last { ... }
    s = stderr.strip()
    if not s:
        return {}
    # Find the position of the last "{" preceded by whitespace/newline
    idx = s.rfind('{')
    while idx > 0:
        # find the matching close brace
        try:
            blob = s[idx:]
            # find first '}' that closes the object — count braces
            depth = 0
            end = -1
            for i, ch in enumerate(blob):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end < 0:
                return {}
            data = json.loads(blob[:end + 1])
            return data
        except (json.JSONDecodeError, ValueError):
            idx = s.rfind('{', 0, idx)
    return {}


def _measure_loudness(path: str) -> dict:
    """Measure the loudness of a WAV file via loudnorm analysis."""
    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'info', '-i', path,
        '-af', 'loudnorm=I=-14:LRA=11:TP=-1.5:print_format=json',
        '-f', 'null', '-',
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return _parse_loudnorm_json(res.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--lufs', type=float, default=DEFAULT_LUFS_VIDEO,
                    help='target integrated loudness (LUFS). -14 video, -16 podcast.')
    ap.add_argument('--no-denoise', action='store_true')
    ap.add_argument('--reverb', choices=list(REVERB_PRESETS.keys()), default='none')
    ap.add_argument('--lra', type=float, default=DEFAULT_LRA)
    ap.add_argument('--tp', type=float, default=DEFAULT_TP)
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()
    result = master_audio(
        args.input, args.output,
        target_lufs=args.lufs,
        denoise=not args.no_denoise,
        reverb=args.reverb,
        lra=args.lra, tp=args.tp,
        verbose=args.verbose,
    )
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
