# Phrase Pacing — Kokoro Discipline for v3

The single most important production lesson from v2:

> **Let Kokoro do the rhythm work. Don't synthesize sentences in isolation if they belong together as a phrase.**

## The v2 mistake

v2 synthesized one sentence at a time and inserted 320–420ms silence between every sentence. For long shots this added breath. For short rapid phrases it was catastrophic:

```
Source: "No three. No six. No nine."

v2 audio: [No three.] [SILENCE 320ms] [No six.] [SILENCE 320ms] [No nine.]
          = stilted, plodding, no emotion, painful
```

Even though each sentence is short, Kokoro produced THREE separate utterances, each with its own intonation arc, separated by long silences.

## The v3 fix

The phrase chunker (`scripts/phrase_chunker.py`) groups related sentences into ONE Kokoro call. Kokoro's prosody handles the commas and periods naturally inside the call:

```
v3 audio (same source): [No three. No six. No nine.] = one call, natural cadence
```

Or, even better — author rewrites with commas to signal phrase rhythm:

```
"Never three, never six, never nine."
v3 audio: one call, comma micro-pauses, smooth phrase delivery
```

## Authoring rules

### 1. Default: write natural prose with proper punctuation

- Comma → micro-pause inside Kokoro's prosody.
- Period → sentence-end intonation.
- Question mark → rising intonation.
- Em-dash (`—`) → slight pause inside a sentence.
- Blank line → paragraph break (the chunker WILL split here for breath).

### 2. Phrase rhythms: ONE sentence with commas, not multiple sentences

```
✓ "Eleven becomes two, seventeen becomes eight, twenty-three becomes five."
✗ "Eleven becomes two. Seventeen becomes eight. Twenty-three becomes five."
```

The first delivers as a connected phrase. The second is three separate utterances.

(The chunker now combines the second form into one chunk too — but the comma-form gives Kokoro better prosody cues.)

### 3. Dramatic pauses: use `<beat>` (650ms) or `<pause 400>` (custom ms)

```
"The cross is the doubling circuit. <beat> Drawn in geometry."
"Watch this <pause 250> nine"
```

A `<beat>` produces a 650ms silence in the audio AND a chunk split (so the second half delivers with fresh intonation).

### 4. Paragraph-level breath: blank line in the narration

```
"Take any prime greater than three. Add its digits. Reduce to one digit.

You will land on one of only six numbers."
```

The chunker splits at the blank line and inserts a 450ms breath. The viewer feels the pivot.

### 5. Long paragraphs: chunker auto-splits at sentence boundaries

If a paragraph exceeds 6 sentences OR 600 characters, the chunker splits at the nearest sentence boundary and gives the split a smaller breath (~225ms). This keeps Kokoro from rushing through a 10-sentence run.

## Quick reference

| Author wants… | Author writes… | Audio result |
|---|---|---|
| Phrase rhythm (3 short bits) | "A, B, C." (one sentence) | One call, smooth commas |
| Short sentences flowing | "A. B. C." | One call (chunker combines), natural sentence pacing |
| Slight dramatic pause | "A. <beat> B." | Two calls, 650ms silence |
| Custom pause | "A. <pause 300> B." | Two calls, 300ms silence |
| Paragraph break (breath) | `"A.\n\nB."` (blank line) | Two calls, 450ms silence |
| Pivot or new section | Two paragraphs with blank line | Two calls, breath between |

## What the chunker WILL NOT do

- Split mid-sentence (it always splits on `.!?` boundaries).
- Insert silence inside a Kokoro call.
- Change the author's wording.

If a section sounds wrong, the fix is in the source narration (punctuation, paragraph breaks, beat markers) — not in the chunker. Kokoro is doing what it's told.

## When to override (audio post-edit)

If Kokoro mispronounces a word ("phi" as "f-eye") or rushes a comma, the fix order is:

1. **Rewrite the source.** Spell out abbreviations ("phi" → "fie" or "the golden ratio"). Add comma to slow.
2. **Add a `<beat>` after the trouble word** to force Kokoro to land on it.
3. **Last resort: REAPER post-edit** with `scripts/audio_master.py` for loudness + denoise, then manual splice in REAPER.

Do not break the phrase rule to fix a single mispronunciation. You'll trade one problem for ten.

## Validation

Before rendering, dry-run the chunker on your narration:

```bash
echo "No three. No six. No nine." | python scripts/phrase_chunker.py -
```

Expected output: ONE chunk, no splits. If you see multiple chunks for a short phrase rhythm, something in the source string is forcing a split (likely a blank line or a `<beat>` marker you didn't notice).
