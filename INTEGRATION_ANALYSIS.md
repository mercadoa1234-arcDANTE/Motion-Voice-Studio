# Brain v4 × Motion Studio v3 — Integration Analysis

## Overview

This document covers the full MECE analysis of current vs desired state across
all brain skills, then the architecture of the v4 refactor. Read this before
deploying the skill package into a Motion Studio v3 production context.

The central premise: **scripts and natural language together are the code.**
The storyboard JSON is not a config file — it's the program. The SKILL.md and
references/*.md are not documentation — they're operational rules the AI reads
as executable instructions. The Python scripts are runtime engines that evaluate
the JSON program. Natural language narration embedded in the storyboard is a
first-class code element that drives audio-first timing, controls engine
dispatch, and determines the entire production timeline. This is semantic
wiring: the boundary between "documentation" and "code" dissolves by design.

Brain v4 is built to understand this.

---

## Part I — Motion Studio v3 Pattern Analysis

### What it is

A multi-engine video production pipeline run in a 4 GB / 1 CPU sandbox.
Six render engines (pyvista, manim, composite, image, bom, title), one
bundled TTS (Kokoro-82M, 7 voices, CPU-only), one assembler (ffmpeg), one
orchestrator (storyboard.py), one QA harness (self_check_v2.py).

### The semantic wiring architecture

```
SKILL.md + references/*.md
  ↓ read as operational rules by AI
AI writes storyboard.json
  ↓ declarative DSL — the primary code artifact
storyboard.py parses + dispatches per shot
  ↓
[pyvista | manim | composite | image | bom | title]
  ↓
ffmpeg: concat + audio mix + soft-sub mux
  ↓
final.mp4 (mov_text track + sidecar .srt)
```

The storyboard is not configuration. It IS the program. Writing a storyboard
IS writing the video. Every field has execution semantics: `engine` routes
dispatch, `narration` drives audio-first timing, `ken_burns` specifies pixel-
level animation, `voice` selects the synthesis model.

### Redundancy scoring (hard-hitting vs over-redundant)

| Redundancy | Score | Assessment |
|---|---|---|
| Hard gate system (A-F) + QA script | **Hard-hitting** | Six independent checkpoints, each verifiable by the script. No ceremony — each gate has a bash command. |
| SKILL.md tool table + TOOL_CHOICE.md full tree | **Productive** | Short version speeds common choices; long version needed for edge cases. Both earn their tokens. |
| AGENT_LOOP.md re-documents `/brain` scoring | **Over-redundant** | AGENT_LOOP.md re-states brain's 5-axis scoring verbatim. One of these should reference the other, not duplicate it. |
| PIPELINES.md + examples/ runnable code | **Hard-hitting** | Different registers: PIPELINES = copy-paste skeleton; examples = verified working code. Both serve. |
| VOICEOVER.md + PHRASE_PACING.md + VOICES.md | **Borderline** | Three docs for one subsystem. VOICES.md is a clean catalog. PHRASE_PACING.md fixes a specific v2 bug. VOICEOVER.md is the synthesis. Could collapse VOICEOVER + PHRASE_PACING. |
| CAV reference dir (legacy v2) still present | **Dead weight** | Legacy references under /cav are not referenced in SKILL.md workflows. Clear dead weight unless user is migrating from v2. |

### Rigidity / flexibility issues

**Too rigid:**
- Engine categories are fixed. There is no `hybrid` engine type for cases where
  a shot needs, say, a 2D diagram (matplotlib) composited with narration but no
  3D CAD. The composite engine assumes a pyvista base. A shot that is just
  "matplotlib diagram + math overlay" has no clean engine path.
- The golden-ratio layout grid is hardcoded to 1280×720. Scaling to 1920×1080
  works numerically but the pixel comments throughout the docs become misleading.
- Kokoro speed range (0.5–2.0 multiplier) is documented but not enforced at the
  storyboard schema level. A speed=3.0 entry silently breaks intelligibility.

**Too flexible:**
- The storyboard JSON has no strict schema validator upstream of storyboard.py.
  Brain authors the JSON; if it has typos in engine names or missing required keys,
  the error surfaces at render time (minutes of compute later), not at plan time.
- The `/grill` cap of "≤3 questions" is appropriate as a ceiling but the loop has
  no enforcement mechanism. Without brain explicitly tracking the count, this
  becomes a suggestion.
- The `continue` loop has no maximum defined. A project can technically checkpoint
  infinitely. In practice users stop when they get tired, not when the loop breaks.

### Where brain fundamentally doesn't fit Motion Studio — the real gaps

**Gap 1: Hemisphere model assumes one routing decision per task.**
Brain routes once: "this is a right-first / left-first / both task." But Motion
Studio production needs continuous hemisphere switching within a single task.
Storyboard authoring is right-hemisphere (creative, exploratory). Gate checking
is left-hemisphere (validation, arithmetic). Audio synthesis is neither — it's
execution. Composite layout planning is both simultaneously. Brain's four static
patterns don't model this sub-task switching.

**Gap 2: Brain doesn't know the storyboard JSON is the primary deliverable.**
When brain thinks "build this," it thinks Python scripts or React components.
When Motion Studio says "build this," the first deliverable is the storyboard
JSON — everything else is derived from it. Brain would route a storyboard authoring
task as "code generation" (left hemisphere), when it should route it as "program
design" (right hemisphere finds the architecture, left hardens the schema).

**Gap 3: Double-routing overhead.**
Motion Studio's AGENT_LOOP.md already has a built-in agent loop that re-states
brain's 5-axis scoring. When brain routes to `/motion-studio`, and then
motion-studio reads AGENT_LOOP.md and re-scores on 5 axes, the user pays twice
for the same cognitive work. One of these should defer to the other.

**Gap 4: Checkpoint/continue is not a first-class interrupt.**
Brain's interrupt logic covers: fire, better-path, higher-value, override. It
does not cover "tool-call limit reached, checkpoint state, wait for continue."
This is the most common interrupt in Motion Studio production — it should be in
brain's interrupt table as a first-class pattern, not a footnote.

**Gap 5: Rigor's domain language is wrong for production.**
Rigor's triggers reference "investor packaging," "lender," "regulator," "court."
These are correct for the original context but misroute in Motion Studio. A video
production job with Gates A-F is exactly the kind of high-stakes deliverable rigor
should fire on — but the trigger language doesn't match, so rigor may not fire at
all, or the AI reads the mismatch as "this isn't a rigor situation."

---

## Part II — MECE: Current State vs Desired State

Five exhaustive, non-overlapping dimensions.

### Dimension 1: Orchestration Model

**Current:** Brain routes once per task using a static 4-pattern system. Patterns
map to lender/regulator/court contexts. Mid-task switching is interrupt-based but
only four interrupt types exist. Production pipeline work (sequential gates, sub-
task hemisphere switching) has no dedicated pattern.

**Desired:** Brain v4 adds Pattern 5 (Production Pipeline): linear, gate-
validated, checkpoint-first. Sub-task hemisphere switching is explicit — brain
can re-route mid-production without treating it as an "interrupt." The storyboard
JSON is recognized as a primary deliverable type, not just code.

**Gap:** No gate-sequence routing pattern. Checkpoint/continue not interrupt-
listed. Storyboard authoring has no dedicated routing label.

### Dimension 2: Execution Awareness

**Current:** Brain knows Python scripts exist and routes large-file-edit to handle
them. It doesn't know about:
- The render engine dispatch model (shot → engine → frames)
- Gate system (A-F sequential verification)
- Audio-first ordering constraint
- Checkpoint/continue loop as a production norm

**Desired:** Brain v4 understands that in a production pipeline:
(a) audio generation precedes frame render always
(b) gates must pass in sequence — a failed Gate B blocks Gate C–F
(c) `state.json` checkpointing is the correct interrupt response when hitting
tool-call limits, not asking the user what to do next
(d) the storyboard JSON is the architecture artifact — authoring it IS the design phase

**Gap:** Brain treats all pipeline work as "code." Production has ordering
constraints (audio-first), gate dependencies (A→B→C→D→E→F), and artifact
types (storyboard, state.json) that don't appear in brain's current vocabulary.

### Dimension 3: Code / Language Unity

**Current:** Brain treats scripts (Python) and natural language (narration,
documentation) as separate things. Skills are either "code skills" (large-file-
edit, frontend-design) or "thinking skills" (natural-mind, grill). There is no
model for work where NL and scripts are unified — where narration IS a code
field, where reference docs ARE operational rules.

**Desired:** Brain v4 encodes the semantic wiring principle: in a system where
docs are rules and narration is code, editing a storyboard's `narration` field
has execution consequences (it changes audio duration, which changes timing, which
changes all downstream frame counts). Reading SKILL.md is not optional background
reading — it is loading the operational program. The distinction between "reading
docs" and "executing code" is false in this architecture.

**Gap:** No skill in the current set addresses this. It must be encoded in brain's
integration section and in rigor's pass structure.

### Dimension 4: Quality Gates

**Current:** Rigor runs three passes (surface/break/compress) with domain triggers
that reference legal/regulatory/financial work. Gates are internal to rigor. No
correspondence to external gate systems (Gate A–F). Rigor's "break" pass asks
"what breaks this in the real world" — useful but not mapped to the specific gate
checks Motion Studio defines.

**Desired:** Rigor v2 maps its Break pass to any external gate system present in
the current skill context. In Motion Studio production, "break" means: did Gate A
pass (geometry exists)? Did Gate B pass (still render viewed)? Is audio duration
within ±5% of video duration (Gate D)? The three-pass structure should recognize
gate systems and run against them rather than generating abstract "what could break."

**Gap:** Rigor's Pass 2 is domain-generic. It should be domain-adaptive: when a
gate checklist is present in the task context, Break runs against the gates, not
against abstract failure modes.

### Dimension 5: Identity Layer

**Current:** Brain, rigor, and deep-think contain personal name references,
personal project references (specific real estate deals, specific apps, specific
legal contexts), and substrate comments that reference specific belief systems.
These make the skills non-portable — they are persona-locked to one user's context.

**Desired:** All skills in the v4 package are anonymous. Personal names removed.
Personal project references replaced with generic domain equivalents. Substrate
values (honesty, corrigibility, quality) are retained as universal operating
principles — they're not persona-specific. The skills are deployable in any
professional context without modification.

**Gap:** Rigor contains "Anthony" by name in Pass 1 and Pass 2. Brain's examples
reference specific personal projects. Deep-think's comments reference specific
personal relationships. All of these need excision.

---

## Part III — The Optimal Plan

Execute in order. Each step unlocks the next.

### Step 1: Refactor brain → brain v4
- Strip all personal name/project references
- Add Pattern 5 (Production Pipeline)
- Add checkpoint/continue as a first-class interrupt type
- Add storyboard-as-code to the Integration section
- Remove double-routing: brain notes explicitly that when a skill has its own
  agent loop (like motion-studio), brain sets the initial pattern and then
  defers internal micro-routing to the skill
- Update skill registry examples to remove personal project names

### Step 2: Refactor rigor → rigor v2
- Strip "Anthony" references throughout
- Replace legal/regulatory trigger language with production-aware triggers:
  "multi-stage pipelines, gate-validated workflows, public-facing deliverables"
- Make Pass 2 (Break) gate-adaptive: "If the task context includes an explicit
  gate or checklist, run Break against those gates specifically"
- Add production examples (video, pipeline, architecture builds)

### Step 3: Minor update grill
- Add source-doc self-grill rule: "When a source document is present (PDF,
  paper, codebase), read it fully before forming any question. A question
  answered in the source is never asked."
- Already mostly correct — minimal change needed

### Step 4: Retain natural-mind as-is
- Already clean and generic
- No personal references
- No changes needed

### Step 5: Anonymize deep-think, retain as fallback
- Strip the personal relationship comments from [COMMENT] blocks
- Retain the four modes (grunt, natural-mind, grill, large-file-edit) — these
  are still valid cognitive modes
- Mark clearly as "fallback for complex mode-switching" — brain should not
  reach for deep-think first

### Step 6: Write motion-studio brain integration note
- A short addendum in brain v4's skill registry that explains the Motion Studio
  integration pattern specifically
- This closes the double-routing gap by making the handoff protocol explicit

---

## Part IV — Semantic Wiring Principle (for v4 skills)

This principle must be encoded in brain v4 and referenced in rigor v2:

> In a semantically-wired system, natural language and scripts are not separate
> layers — they are co-equal parts of one program. Reference documents are
> operational rules. JSON storyboards are executable programs. Natural language
> narration fields carry timing semantics. Reading the docs IS loading the program.
> Editing narration IS editing code. The AI is the compiler.

Practical consequences:
1. When authoring a storyboard, treat it as programming — not content writing.
   Every field has downstream execution effects.
2. When reading SKILL.md or references/*.md, treat them as loaded program state —
   not background reading. Rules there are active constraints.
3. When rigor runs Pass 2 (break) on a storyboard, it is running a logic check
   on a program, not a review on a document.
4. When grill self-interrogates before surfacing questions, it is doing static
   analysis on the program-to-be-built, not casual planning.

---

## Part V — Scoring Summary for Brain Fitness to Motion Studio

| Dimension | Score (1-5) | Note |
|---|---|---|
| Orchestration model fit | 3/5 | Hemisphere logic is valid; 4 patterns don't cover Production Pipeline |
| Execution awareness | 2/5 | Audio-first, gates, checkpoint/continue all missing from brain's vocabulary |
| Code/language unity | 2/5 | Brain treats docs and scripts as separate; semantic wiring not encoded |
| Quality gate alignment | 2/5 | Rigor fires on wrong domain triggers; gates not mapped to Break pass |
| Portability (anonymity) | 1/5 | Personal names and projects throughout three skills |
| **Overall** | **2/5** | Structurally sound but fundamentally under-fitted for production pipeline work |

After v4 refactor, projected scores:
| Dimension | Score (1-5) |
|---|---|
| Orchestration model fit | 4/5 |
| Execution awareness | 4/5 |
| Code/language unity | 4/5 |
| Quality gate alignment | 4/5 |
| Portability (anonymity) | 5/5 |
| **Overall** | **4/5** |

The remaining 1-point gap in most dimensions reflects Motion Studio's inherent
complexity — no general orchestrator can perfectly model every domain-specific
pipeline. The gap is closed at the skill level (motion-studio's AGENT_LOOP.md)
not at the brain level.
