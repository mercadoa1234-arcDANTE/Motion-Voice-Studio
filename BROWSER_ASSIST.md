# Audio Mastering — v3 Recipe

Why Kokoro-only output is not finished audio. What v3 does to fix it.

## The problem

Kokoro produces clean speech but at variable loudness (typically -23 to -18 LUFS). Different shots end up with different perceived volumes. Viewers hit play, immediately adjust their volume, hit a louder section, adjust again — fatigue.

There's also a faint computational hiss around -55 dB that sits below the speech but rises through the mix when stacking shots. And without any reverb, the voice sits "in front of" any background music; it doesn't blend.

## The v3 fix (scripts/audio_master.py)

Applied automatically during the mux step. Three filters in order:

1. **Noise floor reduction** (`afftdn` — FFT denoise, 12 dB nominal reduction)
2. **Two-pass loudness normalization** (`loudnorm`)
   - First pass measures integrated LUFS, LRA, true peak.
   - Second pass renormalizes to the target with the measured values.
   - Target: **-14 LUFS for video**, **-16 LUFS for podcast** (per spec, May 2026).
3. **Optional reverb** (`aecho`) — three presets:
   - `none` (default for explainer videos)
   - `subtle` (slap-back, blends voice with background music)
   - `room` (small-room IR)
   - `hall` (large-hall, dramatic)

## Default targets

| Use | LUFS | LRA | True Peak | Reverb |
|---|---|---|---|---|
| Video / YouTube | -14 | 11 | -1.5 dBTP | none or subtle |
| Podcast / Spotify | -16 | 11 | -1.5 dBTP | none |
| Cinema / dramatic | -23 | 18 | -2.0 dBTP | hall (sparingly) |

## CLI usage

```bash
python scripts/audio_master.py in.wav out.wav --lufs -14 --reverb subtle -v
```

Output (JSON):
```json
{
  "input_lufs": "-23.36",
  "output_lufs": "-13.72",
  "true_peak": "-1.50",
  "target_lufs": -14.0,
  "denoise": true,
  "reverb": "subtle"
}
```

## Library usage

```python
from audio_master import master_audio
result = master_audio('shot.wav', 'shot_mastered.wav',
                      target_lufs=-14, denoise=True, reverb='none')
```

## When mastering is skipped

`mux_final(... apply_audio_master=False ...)` bypasses the pass. Use only when:
- You're testing the raw Kokoro output.
- You're handing the audio to an external DAW (REAPER, Audition) for manual mastering and want the unprocessed track.

## REAPER pipeline (advanced)

For broadcast-grade results, the user's source workflow:

1. Skip in-pipeline mastering (`apply_audio_master=False`).
2. Open `narration_mixed.wav` in REAPER.
3. Apply ReaFIR (subtract noise profile from a silent region — captures the actual sound floor of THIS session, not a general assumption).
4. Apply ReaEQ for tone shaping (high-pass at 80Hz; gentle presence boost around 4–5kHz).
5. Apply ReaXComp for multi-band compression (3:1 ratio, slow attack).
6. Render to -14 LUFS / -1.5 dBTP using ReaJS loudness measurement.
7. Replace `narration_mixed.wav` and re-run mux with `apply_audio_master=False`.

This is the "if it really matters" path. The in-pipeline filter chain is "good enough for 95% of explainer videos."

## Validation

After a render, verify the mastered audio:

```bash
ffmpeg -hide_banner -i final.mp4 -af "loudnorm=I=-14:LRA=11:TP=-1.5:print_format=json" -f null - 2>&1 | tail -30
```

You should see `output_i` within ±1 LUFS of -14.0 and `output_tp` below -1.0.
