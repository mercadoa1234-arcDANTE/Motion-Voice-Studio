"""
phrase_chunker.py — v3 narration chunking discipline.

The lesson from v2 production (Anthony's feedback, May 2026):
- Per-sentence synthesis with silence-gaps-between produced choppy delivery for
  short rapid phrases ("No three. No six. No nine." → three Kokoro calls with
  320ms gaps between = painful).
- Per-shot synthesis (entire 50-second shot in one call) made Kokoro rush; no
  natural breath between paragraphs.

v3 rule: synthesize PARAGRAPH-LEVEL chunks, 4–6 sentences each. Within a
paragraph, let commas and periods do their job — Kokoro's prosody handles
phrase rhythm naturally inside one call. Between paragraphs, insert real
silence (a breath).

Authoring discipline:
- Write narration as natural prose with proper punctuation. Commas for
  micro-pauses, periods for sentence ends, blank lines for paragraph breaks.
- For dramatic short-phrase rhythms, use ONE sentence with commas:
  "Never three, never six, never nine." (not three separate sentences)
- For genuine dramatic pause, write `<beat>` inline — the chunker treats it as
  a forced split with extra silence.
- Paragraph breaks (`\\n\\n` in source) become breath gaps in the audio.

Output: list of (text, trailing_gap_seconds) pairs where text is one Kokoro
synthesis call. Concatenating with silences yields the shot's audio.
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Sentence boundary pattern: period/exclaim/question followed by whitespace + capital/digit.
_SENT_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\u201c])')

# Inline beat marker for explicit dramatic split with longer silence.
_BEAT_MARKER = re.compile(r'\s*<beat(?:\s+(\d+))?>\s*', re.IGNORECASE)
# Inline pause marker for medium silence (e.g., <pause 500> for 500ms).
_PAUSE_MARKER = re.compile(r'\s*<pause(?:\s+(\d+))?>\s*', re.IGNORECASE)

# Default silence durations (seconds) for natural breath.
DEFAULT_PARAGRAPH_GAP = 0.45    # between paragraph chunks
DEFAULT_BEAT_GAP = 0.65         # explicit <beat>
DEFAULT_SHORT_PAUSE_GAP = 0.30  # explicit <pause>
PARAGRAPH_THRESHOLD = 4          # min sentences in a chunk before considering paragraph break
PARAGRAPH_MAX_SENTENCES = 6     # max sentences per Kokoro call (above this, force a split)
PARAGRAPH_MAX_CHARS = 600        # safety: Kokoro is happiest under this length per call


def chunk_narration(text: str) -> List[Tuple[str, float]]:
    """Split a narration string into (kokoro_input_text, trailing_silence_sec) pairs.

    Strategy:
    1. Split on explicit `<beat>` and `<pause>` markers first (these force splits).
    2. Within each segment, split on paragraph breaks (blank lines).
    3. Within each paragraph, IF it exceeds PARAGRAPH_MAX_SENTENCES or
       PARAGRAPH_MAX_CHARS, split at the nearest sentence boundary. Otherwise
       keep as one Kokoro call so prosody is preserved.
    4. Trailing gaps: <beat>=0.65s, <pause>=0.30s, paragraph break=0.45s,
       last chunk=0.0s.

    The output is what the synthesizer should hand to Kokoro one chunk at a
    time. The synthesizer concatenates the resulting waveforms with the
    specified silences.
    """
    text = text.strip()
    if not text:
        return []

    # Phase 1: Walk the source string, extracting segments split by explicit markers.
    raw_segments: List[Tuple[str, float]] = []
    cursor = 0
    while cursor < len(text):
        m_beat = _BEAT_MARKER.search(text, cursor)
        m_pause = _PAUSE_MARKER.search(text, cursor)
        # Pick whichever marker comes first.
        m = None
        gap = 0.0
        if m_beat and m_pause:
            m = m_beat if m_beat.start() < m_pause.start() else m_pause
        elif m_beat:
            m = m_beat
        elif m_pause:
            m = m_pause
        if m is None:
            # No more markers — rest of string is final segment
            seg = text[cursor:].strip()
            if seg:
                raw_segments.append((seg, 0.0))
            break
        seg = text[cursor:m.start()].strip()
        if m is m_beat:
            ms = m.group(1)
            gap = (int(ms) / 1000.0) if ms else DEFAULT_BEAT_GAP
        else:
            ms = m.group(1)
            gap = (int(ms) / 1000.0) if ms else DEFAULT_SHORT_PAUSE_GAP
        if seg:
            raw_segments.append((seg, gap))
        else:
            # marker at the very start — attach gap to following segment's leading silence
            # by merging with next; for now we drop a leading-only marker.
            pass
        cursor = m.end()

    # Phase 2: For each marker-bounded segment, split on paragraph breaks.
    paragraph_segments: List[Tuple[str, float]] = []
    for seg, post_gap in raw_segments:
        # Paragraph break = 2+ newlines
        paras = re.split(r'\n\s*\n', seg)
        paras = [p.strip() for p in paras if p.strip()]
        if not paras:
            continue
        for i, p in enumerate(paras):
            # The last paragraph in this segment carries the post_gap from the marker.
            # Intermediate paragraphs use DEFAULT_PARAGRAPH_GAP.
            is_last = (i == len(paras) - 1)
            gap = post_gap if is_last else DEFAULT_PARAGRAPH_GAP
            paragraph_segments.append((p, gap))

    # Phase 3: Within each paragraph, ensure no single Kokoro call exceeds
    # PARAGRAPH_MAX_SENTENCES or PARAGRAPH_MAX_CHARS. If it does, split at the
    # nearest sentence boundary.
    final: List[Tuple[str, float]] = []
    for para, gap in paragraph_segments:
        chunks = _split_paragraph(para)
        for j, chunk in enumerate(chunks):
            is_last = (j == len(chunks) - 1)
            # Intermediate chunks inside a paragraph get a small breath
            chunk_gap = gap if is_last else DEFAULT_PARAGRAPH_GAP * 0.5
            final.append((chunk, chunk_gap))

    # The very last chunk has no trailing silence (the shot mixer adds shot-end gaps).
    if final:
        last_text, _ = final[-1]
        final[-1] = (last_text, 0.0)

    return final


def _split_paragraph(para: str) -> List[str]:
    """Split a paragraph into chunks of at most PARAGRAPH_MAX_SENTENCES (and
    PARAGRAPH_MAX_CHARS) while respecting sentence boundaries. Try to keep
    chunks at least PARAGRAPH_THRESHOLD sentences if possible — but if the
    paragraph is shorter, return it as a single chunk."""
    sentences = _SENT_BOUNDARY.split(para)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return []

    if len(sentences) <= PARAGRAPH_MAX_SENTENCES and len(para) <= PARAGRAPH_MAX_CHARS:
        return [para]

    chunks: List[str] = []
    current_sentences: List[str] = []
    current_chars = 0
    for s in sentences:
        # Force a flush if adding this sentence would exceed limits.
        proposed_chars = current_chars + len(s) + (1 if current_sentences else 0)
        if current_sentences and (
            len(current_sentences) >= PARAGRAPH_MAX_SENTENCES
            or proposed_chars > PARAGRAPH_MAX_CHARS
        ):
            chunks.append(' '.join(current_sentences))
            current_sentences = []
            current_chars = 0
        current_sentences.append(s)
        current_chars += len(s) + (1 if len(current_sentences) > 1 else 0)
    if current_sentences:
        chunks.append(' '.join(current_sentences))
    return chunks


def cli():
    """Manual test: read a file path or stdin string, print chunks."""
    import sys
    if len(sys.argv) > 1 and sys.argv[1] != '-':
        text = open(sys.argv[1]).read()
    else:
        text = sys.stdin.read()
    chunks = chunk_narration(text)
    print(f"{len(chunks)} chunks:")
    for i, (chunk, gap) in enumerate(chunks):
        print(f"--- chunk {i} (gap_after={gap:.2f}s, {len(chunk)} chars) ---")
        print(chunk)
        print()


if __name__ == '__main__':
    cli()
