# core/AUDIO.md — Audio Configuration

Phrase pacing, voice config, loudnorm targets, and Kokoro quirks.

---

## Phrase pacing (the #1 production lesson)

**Never synthesize sentence-by-sentence.** Group rhythmically related phrases into one Kokoro call.

```
BAD:  kokoro("No three.")  +320ms+  kokoro("No six.")  +320ms+  kokoro("No nine.")
      → stilted, broken prosody, three flat arcs

GOOD: kokoro("No three, no six, no nine. The pattern holds.")
      → one natural arc, Kokoro handles the internal rhythm
```

**Chunking rules:**
- 60–100 words per call for paragraphs
- Comma-grouped short phrases → always one call
- Over 120 words: split at sentence boundaries (full stop / `<beat>` marker), concatenate WAVs
- Blank lines in narration → 320–420ms silence gap (add explicitly)
- `<beat>` → 200ms silence, `<pause 0.5>` → 500ms silence

---

## Voice config

**12 bundled voices in `kokoro-voices/`** (offline. no network required). Includes multilingual support.

| File | Prefix meaning | Notes |
|---|---|---|
| `af_bella.pt`   | American female | NaN-safe fallback for any English voice issue |
| `af_heart.pt`   | American female | Warm, default for English narration |
| `af_nicole.pt`  | American female | Clear |
| `am_fenrir.pt`  | American male   | Deeper |
| `am_michael.pt` | American male   | Speed ≥ 1.0 only — NaN below |
| `am_puck.pt`    | American male   | Lighter |
| `bf_emma.pt`    | British female  | Formal |
| `bm_daniel.pt`  | British male    | Neutral |
| `bm_george.pt`  | British male    | Authoritative |
| `jf_alpha.pt`   | Japanese female | Japanese-language narration |
| `pf_dora.pt`    | Brazilian Portuguese female | Portuguese-language narration |
| `zf_xiaoyi.pt`  | Mandarin Chinese female | Mandarin-language narration |

**Multilingual note:** non-English voices have thinner training data — best on 100–200 token utterances. Long Japanese/Portuguese/Mandarin passages may need shorter chunking than English (~80 words per call vs 100).

**NaN recovery protocol (any voice):**
1. Detect as zero RMS or `np.any(np.isnan(audio))`
2. Switch voice to `af_bella` (English) — most stable known voice
3. Split narration into ≤ 60-word chunks
4. Synthesise chunks separately, concatenate WAVs

**Additional voices via npm:** `python Kokoro_TTS_Agent_Skill_Pack/kokoro_run.py --setup` downloads 54 voices total (~26 MB one-time). Bundled 12 work offline.

---

## Kokoro inference config

```python
# Correct tokenizer API (kokoro-onnx 1.x):
normed   = tok.normalize_text(text)
phonemes = tok.phonemize(normed, lang="en-us")
tokens   = tok.tokenize(phonemes)

input_ids = np.array([[0] + tokens + [0]], dtype=np.int64)
style_idx = min(input_ids.shape[1] - 1, voice_arr.shape[1] - 1)
style     = voice_arr[0, style_idx]

audio = sess.run(None, {
    "input_ids": input_ids,
    "style":     np.array([style], dtype=np.float32),
    "speed":     np.array([speed], dtype=np.float32),
})[0].squeeze()
```

MAX_TOKENS = 460 (leave headroom below the 500 model limit).

---

## Audio mastering targets

| Destination | LUFS target | True peak |
|---|---|---|
| Video (YouTube, Vimeo) | -14 LUFS | -1.5 dBTP |
| Podcast / podcast export | -16 LUFS | -1.5 dBTP |
| Broadcast | -23 LUFS | -1.0 dBTP |

**Pipeline (applied by mux.py automatically):**

```
raw Kokoro WAV
   → afftdn  (FFT denoise, 12 dB reduction, eliminates computation hiss)
   → loudnorm first pass  (measure integrated LUFS, LRA, true peak)
   → loudnorm second pass (renormalize to target with measured values)
   → [optional] aecho reverb preset
   → AAC 192k
```

**Reverb presets (`audio_master.py`):**

```python
"none"   → default for explainers
"subtle" → slap-back; blends voice with background music
"room"   → small room IR
"hall"   → large hall, dramatic
```
