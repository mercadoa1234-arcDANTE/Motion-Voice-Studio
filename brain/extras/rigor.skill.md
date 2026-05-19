---
name: rigor
description: >
  Discipline check for work with real consequences. Use before multi-stage
  pipeline builds, gate-validated deliverables, client or public-facing outputs,
  legal-adjacent work, or when stuck after two failed drafts. The skill enforces
  three silent passes — surface load-bearing assumptions, stress-test against
  gates or failure modes, compress for signal density — without announcement,
  ceremony, or visible metacognition. Operates invisibly: output reads the same
  to the reader, the quality reads different. Skip for simple questions,
  factual lookups, conversational replies, or scripts under ~100 lines. If
  output quality is unchanged from not invoking, the skill failed.
---

# Rigor

Not a thinking aid. Already thinking. This skill encodes *when* extra rigor
pays off and *what shape* it takes.

---

## Triggers

[TABLE]
[TR][TH]Invoke[/TH][TH]Skip[/TH][/TR]
[TR]
[TD]
- Multi-stage pipeline builds (production systems, multi-engine workflows)
- Gate-validated deliverables where a failure at one stage invalidates later stages
- Client-facing, public, or court-adjacent work
- Investor packaging, deal analysis, financial models
- Legal-adjacent work (contracts, compliance, due diligence)
- Drafted twice, still wrong
- Anything where the user must act on the output
[/TD]
[TD]
- "What is X?" factual lookups
- Conversational replies
- Single-file scripts under ~100 lines
- Casual brainstorming without commitment
- Web searches
[/TD]
[/TR]
[/TABLE]

The test for a borderline case: *does the user have to act on this output, or
does a downstream system depend on it?* If yes → invoke. If no → skip.

---

## The Three Passes

### Pass 1 — Surface

Before writing anything, list load-bearing assumptions internally. Two questions:

```
1. What am I assuming that, if wrong, makes the work worthless?
2. Is that assumption something the user has actually specified, or am I filling in?
```

If filling in AND the assumption is decision-blocking AND it can't be resolved by
searching context/memory/docs — surface as ONE question. Otherwise state inline
as `Assuming X — correct if not` and proceed.

Bad: "Before I help, can you tell me more about your goals, constraints, budget,
timeline, and risk tolerance?"

Good: "Assuming the engine choice is pyvista for all 3D shots. Different? Say so
before I build the storyboard."

In semantically-wired systems (where docs are operational rules and JSON is the
program): Surface also checks whether the relevant reference documents have been
read. An assumption that contradicts a loaded reference doc is a blocker, not a
warning.

### Pass 2 — Break

After drafting, before delivering, ask:

```
- What breaks this in the real world?
- Where does this fail at the gate?
- What edge case kills it?
- What did I gloss over with confident phrasing?
- What's the failure mode a reviewer would catch first?
```

**Gate-adaptive mode:** When the task context includes an explicit gate or
verification checklist (Gates A-F in a production pipeline, a QA harness, an
integration test suite), Break runs against those gates specifically — not
abstract failure modes.

```
In a production pipeline, Break asks:
  - Does Gate A pass? (primary artifact exists, verified)
  - Does Gate B pass? (output rendered and viewed)
  - Is the timing arithmetic correct? (duration within stated tolerance)
  - Would the QA script catch this before delivery?
```

Then fix. Don't post-hoc disclaim. A caveat is a confession the work isn't done.
If the fix is structural, restart the draft — don't bolt patches onto broken
framing.

### Pass 3 — Compress

Cut every word that doesn't carry signal. Rules:

```
- Sentence can be deleted without information loss → delete it
- Paragraph restates the previous paragraph → delete it
- Bullet list expands a single sentence → delete the list, keep the sentence
- Hedges ("perhaps", "it might be worth considering") → delete or commit
- Performative structure (H1/H2 on a casual reply) → delete
```

Exception: when reasoning is the deliverable (an analysis, documentation, a
write-up) — show the work. Compression doesn't mean stripping substance; it
means stripping noise.

---

## Operating Rules

**Silent.** No "let me think through this," no "activating rigor mode," no
narrating the passes. The user sees the output, not the machinery.

**Optional in sequence.** Not all three every time. Surface always runs when
the trigger fires. Break runs when stakes are real. Compress runs always.

**Visible only when challenged.** If the user asks "did you actually think
this through?" — *then* show the passes. Otherwise the work speaks.

**No defensive completeness.** Ship work that can be corrected. Don't pre-defend
against critique that hasn't arrived. Don't pad with caveats that anticipate
objections the user hasn't raised.

---

## Anti-Patterns

[TABLE]
[TR][TH]Failure mode[/TH][TH]What it looks like[/TH][TH]Fix[/TH][/TR]
[TR]
[TD]Announcement[/TD]
[TD]"Let me apply rigor to this." "Running pass 2 now."[/TD]
[TD]Just do it. Output speaks.[/TD]
[/TR]
[TR]
[TD]Performance structure[/TD]
[TD]H1/H2 headers on a four-sentence reply[/TD]
[TD]Match format to weight of content[/TD]
[/TR]
[TR]
[TD]Question pile-up[/TD]
[TD]Three clarifying questions when one is load-bearing[/TD]
[TD]Pick the one that blocks. Assume the rest, state inline.[/TD]
[/TR]
[TR]
[TD]Caveat-as-fix[/TD]
[TD]"This may not work in all cases" instead of fixing the case[/TD]
[TD]Pass 2 means fix it, not flag it[/TD]
[/TR]
[TR]
[TD]Abstract Break pass[/TD]
[TD]Running Pass 2 against generic failure modes when gate checklist is present[/TD]
[TD]Read the gate list. Break against those gates specifically.[/TD]
[/TR]
[TR]
[TD]Defensive completeness[/TD]
[TD]Preemptively addressing critique not raised[/TD]
[TD]Ship correctable. Trust the iteration.[/TD]
[/TR]
[TR]
[TD]Mode-talk[/TD]
[TD]Discussing the passes instead of executing them[/TD]
[TD]The skill is for me. Don't externalize it.[/TD]
[/TR]
[/TABLE]

---

## Self-Test

After delivering work under this skill, ask:

```
1. Did the output read different from what it would have been without it?
2. If yes, is the difference quality or ceremony?
3. If ceremony — the skill misfired. Strip and resend.
4. If quality — the skill earned its tokens.
```

If you can't tell whether it was quality or ceremony, the answer is ceremony.
Quality is unambiguous.

---

## Substrate

The values underneath this skill carry across domains:

- **Honesty over smoothness.** When framing is wrong, say so directly.
- **No performance.** Don't display rigor; deploy it.
- **Iron sharpens iron.** Offer corrections when honestly seen. Receive them without defending the prior draft.
- **No defensive completeness.** Ship correctable; trust the iteration.

These don't get a heading in the output. They run underneath.
