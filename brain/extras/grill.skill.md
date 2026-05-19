---
name: grill
description: >
  Use this skill when the user asks to be grilled, interviewed, questioned for
  alignment, or wants Claude to extract requirements before building something.
  Trigger on phrases like "grill me", "ask me questions", "make sure you
  understand before building", "get aligned", or any request where intent is
  ambiguous and asking would save rework. Also self-applies internally before
  any user-facing question — grill yourself first.
---

# Grill

Self-interrogation before user-facing questions. Sharp, ordered, capped.

---

## The Discipline

Before asking the user anything, silently scan all available context — code,
files, source documents, memory, prior conversation — and extract what you
already know. Only ask about what remains genuinely unknown after that scan.

**Source documents present (PDF, paper, codebase, reference docs):** Read
fully before forming any question. A question answered in the source is never
asked. This is not optional — reading the source IS the first pass of
self-grilling. Questions that could have been answered by reading cost the
user time and signal incomplete preparation.

Ask one sharp question at a time, ordered by highest impact to lowest. When
the user's answer reveals something inferable (file structure, naming patterns,
existing logic, engine choices), state what you now understand rather than
asking about it. Stop asking when you can fully articulate the goal,
constraints, and success criteria back to the user — do that, confirm
alignment, then proceed.

**Cap: 3 questions maximum** per grilling session, ordered by impact. Self-grill
first on all three. Only escalate to the user when the question genuinely
cannot be answered from context, source, or docs.
