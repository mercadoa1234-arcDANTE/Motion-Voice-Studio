# Architecture

The design philosophy of the brain package. Read this once to understand why
the skills are shaped this way. The skills themselves are operational — they
encode rules. This document explains the choices behind those rules.

---

## The Core Idea

Cognition for a working AI agent has two failure modes:

1. **Under-thinking.** The model produces fluent output that doesn't survive
   contact with reality. Confident, fast, wrong.
2. **Over-thinking.** The model loops on the same problem, narrates its
   process, performs rigor instead of deploying it, and burns tokens on
   ceremony.

Both failures stem from the same root cause: no routing layer between *what is
being asked* and *how cognition should be applied to it.* The brain package
adds that routing layer.

---

## Why Two Hemispheres

There are two distinct kinds of cognitive work, and conflating them produces
predictable failures.

**Analytical work** has known shape. The deliverable is to make sure nothing
breaks. Surface assumptions, stress-test edges, compress for signal density.
The failure mode is hidden assumptions and overlooked failure modes. The
correct disposition is protective.

**Exploratory work** has unknown shape. The deliverable is to find the right
frame before committing. Interrupt false scaffolds, hold contradictions, find
patterns across domains. The failure mode is premature commitment to the wrong
architecture. The correct disposition is generative.

Treating these as one mode produces output that's neither rigorous (because it
keeps exploring) nor exploratory (because it keeps locking down). Treating them
as two — and routing between them based on what the task actually needs — gives
each its full power.

The hemisphere metaphor is borrowed from neuroanatomy as a mnemonic. The model
is not a claim about biology.

---

## Why Five Patterns

The patterns are not arbitrary. They cover the shape-space of work
exhaustively, with each pattern matching a distinct combination of certainty
and complexity.

[TABLE]
[TR][TH]Pattern[/TH][TH]Shape[/TH][TH]Routing[/TH][/TR]
[TR][TD]1[/TD][TD]Known shape, real stakes, single pass[/TD][TD]Left only[/TD][/TR]
[TR][TD]2[/TD][TD]Known stakes, novel architecture, deep work[/TD][TD]Right → Left[/TD][/TR]
[TR][TD]3[/TD][TD]Frame might be wrong, ambiguous shape[/TD][TD]Right loop, hard exit at 3 cycles[/TD][/TR]
[TR][TD]4[/TD][TD]Known problem, known solution, one pass[/TD][TD]Left only, minimal[/TD][/TR]
[TR][TD]5[/TD][TD]Multi-stage, gate-validated, manifest-driven[/TD][TD]Right designs, Left validates, iteration is surgical[/TD][/TR]
[/TABLE]

Patterns 1–4 handle single-output work. Pattern 5 handles pipeline work, which
behaves fundamentally differently — output is composed from discrete stages,
each with its own verification, and iteration touches individual stages rather
than the whole.

Without Pattern 5, pipeline work would route as either "code" (left, Pattern
1) or "architecture" (right, Pattern 2), and both routings would miss what
makes pipelines hard: the ordering constraints, the manifest, the gate
sequence, the surgical iteration loop.

---

## The Two Principles

Two cross-cutting principles inform multiple patterns:

### Semantic Wiring

In some systems, the line between "documentation" and "code" is false. A
storyboard JSON is not configuration — it's a program that the runtime
evaluates. Reference documents are not background reading — they're loaded
operational rules. Natural language fields inside a data structure carry
execution semantics (narration drives audio timing, which drives all
downstream frame counts).

When operating in such a system, "reading the docs" and "loading program
state" are the same act. "Editing the spec" and "modifying behavior" are
the same act. Brain encodes this recognition so that rigor's Surface pass
treats unread reference docs as missing program state, and grill's
self-interrogation treats source documents as the first pass of inquiry.

### Surgical Re-execution

When work has discrete units assembled by a manifest, iteration should be
surgical. Re-rendering an entire video to fix one scene is waste. Re-running
a full test suite to verify one module is waste. Re-deriving an entire
deliverable to update one section is waste.

The manifest is separable from the artifacts. Edit the units that changed,
re-execute only the stages that consume them, re-assemble using the unchanged
manifest. This principle is operationalized in Pattern 5's iterate sub-phase
but applies anywhere work has the manifest + units structure.

Draft fast, polish late. Low fidelity first to verify structure; high fidelity
later only on the parts that survived review.

---

## Why These Four Skills

The orchestrated set — what brain routes between — is four skills. Each occupies a unique slot.

[TABLE]
[TR][TH]Skill[/TH][TH]Role[/TH][TH]What it isn't[/TH][/TR]
[TR][TD]brain[/TD][TD]Router. Sets pattern, manages interrupts.[/TD][TD]Not a thinking skill itself.[/TD][/TR]
[TR][TD]rigor[/TD][TD]Left default. Three passes for analytical work.[/TD][TD]Not for casual replies. Not a content generator.[/TD][/TR]
[TR][TD]natural-mind[/TD][TD]Right default. Honest reasoning, no scaffolds.[/TD][TD]Not for high-stakes code. Not for novel architecture.[/TD][/TR]
[TR][TD]grill[/TD][TD]Self-interrogation before user questions.[/TD][TD]Not for asking the user three things at once.[/TD][/TR]
[/TABLE]

The package does not include thinking modes that duplicate what other skills
do. There is no separate "deep thinking" skill because brain already routes
to rigor or natural-mind based on need. There is no separate "analysis" skill
because rigor is analysis. There is no separate "planning" skill because
Pattern 5's design sub-phase is planning.

If a skill could be removed without functional loss, it was removed.

## The Fifth Skill: grunt-brain

One skill ships alongside the orchestrated set but sits outside it:
`grunt-brain` — a standalone compressed-notation mode for fast sketches,
dependency maps, and architecture shapes where symbols carry more meaning
per token than prose.

It is not invoked by brain. Brain routes between work shapes; grunt-brain is
an output mode the user requests directly. Brain's internal cognition uses
similar notation for routing decisions (the Internal Thinking Tools section
in brain/SKILL.md), but that is invisible to the user. grunt-brain is the
visible, on-demand version — triggered by phrases like "sketch it" or
"give me the shape" — and it produces output in symbols rather than prose.

The two could be collapsed but shouldn't be. Brain's internal notation is a
private tool for routing math. grunt-brain is a public response style. The
trigger surfaces are different, the use cases are different, and conflating
them would force brain to expose its internal cognition as output (bad) or
force grunt-brain to depend on brain's full orchestration (bloat). They are
disjoint by design.

---

## How the Skills Compose

A typical complex task moves through skills like this:

```
Request
  │
  ▼
brain (routes — picks pattern, hemisphere sequence)
  │
  ├── grill (self) — what is genuinely unknown after reading source?
  │
  ├── natural-mind — find the frame, drop scaffolds
  │   or
  │   rigor — surface assumptions, draft, break, compress
  │
  ├── domain skill — specialty execution (production pipeline, UI, edit)
  │
  └── rigor (compress pass) — final density check before delivery
```

Brain doesn't visibly appear in the output. Neither does rigor's pass
structure. Neither does grill's self-interrogation. The user sees the
deliverable. The skills are infrastructure.

---

## What the Package Optimizes For

The package optimizes for **quality per token** in real production work.

It is not optimized for:

- Conversational chat (skip brain entirely — direct answer is correct)
- One-shot factual lookups (skip — search or answer)
- Demonstrations of reasoning (the substrate is anti-performative)
- Maximum capability surface (capability the user doesn't need is bloat)

It is optimized for:

- Multi-stage builds where errors compound
- Deliverables that go in front of clients, regulators, or the public
- Iteration loops where re-doing the wrong work is the failure mode
- Long-running production pipelines that need checkpoint/continue discipline

The package costs ~5,000 tokens loaded into context. The breakeven point is
about three tasks where rigor or pattern 5 saves a rework cycle.

---

## What Lives Outside This Package

Brain orchestrates. It does not implement domain knowledge. Production
pipelines (video, CAD, manim, audio, build systems) live in their own skill
packages with their own reference documents, scripts, and agent loops.

The contract: when a domain skill has its own internal agent loop documented,
brain sets the initial pattern and defers internal micro-routing to that
skill. Brain does not re-score every shot in a video, every test in a suite,
every step in a build. It sets the shape; the domain skill runs the steps.

This is why the package is small. Cognition is universal; execution is local.
