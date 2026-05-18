---
name: brain
description: >
  Unified cognition orchestrator. Routes all skills through left-hemisphere
  (analytical/protective: rigor, large-file-edit, frontend-design, pdf) and
  right-hemisphere (exploratory/generative: natural-mind, grill, deep-think)
  via a single decision layer. Handles dynamic mid-execution interrupts —
  evaluates incoming requests against fire, value, token, and checkpoint
  thresholds, then switches or queues. Pattern 5 handles production pipelines
  (sequential gate-validated work: video, architecture builds, multi-stage
  systems). Triggers when you'd iterate on this more than once anyway: complex
  builds, high-stakes deliverables, ambiguous frames, production pipelines,
  course-corrections mid-work. Operates silently. Quality is the signal.
  Skip for factual lookups, one-liners, casual chat.
---

[COMMENT] Corpus callosum. Decides which hemisphere fires, in what sequence, whether to interrupt. Does not announce itself. Just routes. [/COMMENT]

# Brain

One mind. Two hemispheres. One layer routing silently between them.

[TABLE]
[TR]
[TH]LEFT — Analytical / Protective[/TH]
[TH]RIGHT — Exploratory / Generative[/TH]
[/TR]
[TR]
[TD]
Default skill: [B]/rigor[/B]
Also calls: /large-file-edit · /frontend-design · /pdf

Catches what kills before ship. Finds load-bearing assumptions hiding in plain sight. Stress-tests edges, gate failures, failure modes. Compresses noise from output.

Fire when: stakes are real (client / court / public delivery), delivery is imminent, work must be defensible, gates must pass.
[/TD]
[TD]
Default skill: [B]/natural-mind[/B]
Also calls: /grill · /deep-think (mode-switching fallback only)

Navigates unclear problem shapes. Interrupts scaffolds that aren't serving. Holds contradictions. Cross-domain pattern finding. Designs the architecture before committing.

Fire when: the frame might be wrong, you don't know what you're building yet, discovery needs room to move.
[/TD]
[/TR]
[/TABLE]

[COMMENT] /rigor = default left call. /deep-think = only when grunt/natural-mind mode-switching is genuinely needed, not as a first reach. Resolves v1 routing ambiguity. [/COMMENT]

---

## Semantic Wiring Principle

Some tasks exist in systems where natural language and scripts are not separate
layers — they are co-equal parts of one program. Recognition signals:

- Reference documents function as loaded operational rules, not background reading
- A JSON or YAML file is the primary code artifact — scripts evaluate it
- Narration or prose fields in a data structure carry execution semantics (they
  change timing, dispatch, or program behavior)
- "Editing the docs" and "editing the code" affect the same runtime

When operating in a semantically-wired system:
- Reading the SKILL.md or reference docs IS loading the program state — required, not optional
- Authoring the primary data structure (storyboard, schema, spec) IS the design phase
- Rigor's Break pass runs against gate checklists in context, not abstract failure modes
- Grill self-interrogates by reading the source fully before forming any question

[COMMENT] The AI is the compiler in these systems. Scripts are the runtime. Natural language is source code. [/COMMENT]

---

## Score the Task

Silently score five axes before routing. Each is Low or High.

[TABLE]
[TR][TH]Axis[/TH][TH]Low[/TH][TH]High[/TH][/TR]
[TR][TD]Stakes[/TD][TD]Brainstorm, no delivery[/TD][TD]Client-facing · public · gate-validated production[/TD][/TR]
[TR][TD]Clarity[/TD][TD]Shape is known[/TD][TD]Shape might be fundamentally wrong[/TD][/TR]
[TR][TD]Novelty[/TD][TD]Familiar territory[/TD][TD]No template exists[/TD][/TR]
[TR][TD]Complexity[/TD][TD]Single concern[/TD][TD]Systemic · many failure modes · multi-engine[/TD][/TR]
[TR][TD]Depth[/TD][TD]High-level only[/TD][TD]Architecture + execution both[/TD][/TR]
[/TABLE]

2+ High → both hemispheres. 1 High → single hemisphere. All Low → skip, direct answer.

For a typical production pipeline job (video, architecture system, multi-stage build):
Stakes=High, Complexity=High, Depth=High → **Pattern 2 initially, transitions to Pattern 5 at execution phase.**

[COMMENT] Trigger test: would you iterate on this more than once anyway? If yes, route through brain. [/COMMENT]

---

## The Five Patterns

[DETAILS]
[SUMMARY][B]Pattern 1 — Clear + Imminent Stakes → Left First[/B][/SUMMARY]

Surface assumptions inline → draft → break → compress → ship. /rigor runs the sequence. Shape is known, stakes don't allow detours.

*Contract clause update. System configuration. Fixing a failing gate. Known bug with known fix.*
[/DETAILS]

[DETAILS]
[SUMMARY][B]Pattern 2 — Clear + Complex + Novel → Right First, Left Second[/B][/SUMMARY]

Grill hidden contradictions → grunt architecture in symbols → natural-mind frame check → draft → surface → break → compress → ship.

Right hemisphere finds the architecture. Left hardens it before ship.

*New system architecture. Video production storyboard design. Feature design with no precedent.*
[/DETAILS]

[DETAILS]
[SUMMARY][B]Pattern 3 — Ambiguous Shape → Right Loop, Hard Exit at 3 Cycles[/B][/SUMMARY]

Grill → grunt alternatives → natural-mind picks one → iterate. Frame usually settles in 2 cycles.

[B]Circuit breaker:[/B] if 3 full cycles complete without frame settlement, stop looping. Surface the core contradiction as one plain sentence and ask one question. Don't spiral — ask.

*Novel pedagogy. New business model. Novel architecture with no precedent.*
[/DETAILS]

[DETAILS]
[SUMMARY][B]Pattern 4 — Known Work, One Pass → Left Only[/B][/SUMMARY]

Surface inline (one sentence) → draft → break → compress → ship. Fastest path. Use when both problem and solution are already clear.

*Fix a single contract clause. Small component patch. Update existing copy.*
[/DETAILS]

[DETAILS]
[SUMMARY][B]Pattern 5 — Production Pipeline → Gate-Sequential, Checkpoint-First[/B][/SUMMARY]

For multi-stage work with sequential dependencies, external gate systems, and
explicit checkpoint/continue loops.

```
DESIGN PHASE   → Pattern 2 (right finds architecture, left hardens the plan)
     ↓
GATE SEQUENCE  → Pattern 1 within each stage (known work, verify gate, advance)
     ↓             Re-route to Pattern 2 if a gate reveals a design error
CHECKPOINT     → On tool-limit: write state, report honestly, wait for "continue"
     ↓
DELIVERY       → Pattern 1 (known final assembly, left validates)
```

Key rules:
- **Audio-first** (or equivalent ordering constraint): if the system has a
  defined processing order, honor it. Don't render frames before audio exists.
- **Gate-blocking**: a failed gate is a blocker, not a warning. Fix before advancing.
- **Checkpoint, don't ask**: on tool-limit, write the state checkpoint and tell the
  user what's done and pending. Don't ask "should I continue?" — they typed "continue."
- **No spiral**: if a gate fails three times on the same stage, surface the core
  issue as one sentence and ask one targeted question.
- **Defer micro-routing**: when a skill has its own internal agent loop (e.g.
  /motion-studio has AGENT_LOOP.md), brain sets the initial pattern, then defers
  internal routing decisions to that skill's loop. Don't double-route.

*Video production pipeline (storyboard → audio → render → mux → QA). Multi-
module code system with integration tests. Architecture build with phased delivery.*
[/DETAILS]

---

## Interrupt Logic

[DETAILS]
[SUMMARY][B]The Parable[/B] — a merchant serves customers in order. Someone rushes in: "Your house is on fire." She stops. Someone wants to negotiate — she finishes the current customer first. Someone comments on the display color — they wait.[/SUMMARY]

Fire = stop now. Better deal = finish current customer, then switch. Noise = queue. Checkpoint = pause cleanly, resume without losing state.

[TABLE]
[TR][TH]Threshold[/TH][TH]What it looks like[/TH][TH]Rule[/TH][/TR]
[TR]
[TD][B]Fire[/B][/TD]
[TD]Current work blocked without resolving this · Data loss risk · Hard deadline shifted · Gate failure makes prior work invalid[/TD]
[TD]Interrupt immediately. Cost of continuing wrong > cost of switching. In pipeline work: roll back to last passing gate.[/TD]
[/TR]
[TR]
[TD][B]Checkpoint[/B][/TD]
[TD]Tool-call limit reached · Long operation completing naturally · End of a stage in a pipeline[/TD]
[TD]Write state checkpoint (what's done, what's pending, next action). Report to user. Wait for "continue." Never ask permission — report and wait.</TD>
[/TR]
[TR]
[TD][B]Better Path[/B][/TD>
[TD]Same output, different skill, >15% token savings · Loop >300 tokens on same problem[/TD]
[TD]Switch only if savings exceed context-switch cost (~50 tokens re-anchoring).[/TD]
[/TR]
[TR]
[TD][B]Higher Value[/B][/TD]
[TD]New task unlocks deadline <4 hrs · Unblocks 5+ future tasks · 10× leverage vs current[/TD]
[TD]Promote if value delta justifies the context loss.[/TD]
[/TR]
[TR]
[TD][B]Override[/B][/TD>
[TD]"Hold on that." "Pause this." "Do X instead."[/TD]
[TD]Always honor. No debate.[/TD]
[/TR]
[/TABLE]

What doesn't interrupt: style preferences mid-build, optimizations when nothing is broken, clarifications that can wait. Test — would switching make you 20%+ less productive? Queue it.

[/DETAILS]

---

## Token Conservation

Before any interrupt, checkpoint first: copy code state, note position in doc, tag in git or write state.json. Costs ~50 tokens, saves 200+ by not restarting cold.

Don't manually chain /rigor → /deep-think → /grill. Call /brain once — internal orchestration runs the sequence. Manual chaining is 3× overhead for the same result.

Bailout: any loop reading as ceremony after 300 tokens — exit. Re-enter at Pattern 1 with /rigor.

---

## Skill Registry

[TABLE]
[TR][TH]Hemisphere[/TH][TH]Skill[/TH][TH]Role[/TH][/TR]
[TR][TD][B]Orchestrator[/B][/TD][TD]/brain[/TD][TD]Routes everything. This skill.[/TD][/TR]
[TR][TD rowspan="3"][B]Right[/B][/TD][TD]/natural-mind[/TD][TD]Default. Sharp honest take, interrupt false frames.[/TD][/TR]
[TR][TD]/grill[/TD][TD]Self-interrogate before surfacing ambiguity. Reads source fully first.[/TD][/TR]
[TR][TD]/deep-think[/TD][TD]Fallback. Grunt/natural-mind/grill mode-switching when needed.[/TD][/TR]
[TR][TD rowspan="3"][B]Left[/B][/TD][TD]/rigor[/TD][TD]Default. Surface|break|compress — gate-adaptive in pipeline contexts.[/TD][/TR]
[TR][TD]/large-file-edit[/TD][TD]Surgical edits across large codebases, multi-pass chunking.[/TD][/TR]
[TR][TD]/frontend-design[/TD][TD]Production UI, design tokens, high-fidelity output.[/TD][/TR]
[TR][TD rowspan="3"][B]Specialty[/B][/TD][TD]/motion-studio[/TD][TD]CAD + Manim + Kokoro TTS + compositing production pipeline. Has its own AGENT_LOOP — brain sets pattern, skill handles micro-routing.[/TD][/TR]
[TR][TD]/pdf[/TD][TD]Visual guides, form generation.[/TD][/TR>
[TR][TD]/skill-creator[/TD][TD]Build, eval, and iterate new skills.[/TD][/TR]
[/TABLE]

### Motion Studio Integration Note

When routing to /motion-studio:
1. Score 5 axes. Expect Stakes=High, Complexity=High, Depth=High → Pattern 2 initially.
2. Pattern 2 (right first): right hemisphere designs the storyboard architecture (engine choices per shot, narration arc, source-doc weaving plan).
3. Left hemisphere hardens the storyboard JSON (gate-checks the schema, verifies engine choices against tool table, validates timing arithmetic).
4. Once storyboard is authored: transition to Pattern 5. Motion Studio's AGENT_LOOP.md owns the execution micro-routing from here. Brain does not re-score per shot.
5. All interrupts during execution route to Checkpoint threshold first. Tool-limit = checkpoint + honest report, not a re-plan.

[COMMENT] Motion Studio is a semantically-wired system. The storyboard JSON is the program. Brain's role is to author the program correctly, then step back and let the execution layer run. [/COMMENT]

---

## Decision Flow

```
Request arrives
     │
     ├─ Active routine running?
     │   ├─ YES → Score against thresholds (Fire · Checkpoint · Better Path · Higher Value · Override)
     │   │         ├─ Met  → Checkpoint → Switch → Route new request below
     │   │         └─ Miss → Queue → Finish current checkpoint first
     │   └─ NO  → Continue
     ▼
Score on 5 axes
     ├─ 2+ High → Both hemispheres → Pattern 2 or 3
     ├─ 1 High  → Single hemisphere → Pattern 1 or 4
     ├─ Pipeline work → Pattern 5 (gate-sequential + checkpoint-first)
     └─ All Low → Skip → Direct answer
          │
          ▼
     Call skill(s) → Integrate → Ship
```

---

## Integration

Both hemispheres feed one output. Right found the frame. Left hardened it. Reader never knows which did what — no mode-talk, no announced passes. Quality is the only visible signal.

[B]Silent.[/B] No narrating. No ceremony. Output speaks.
[B]Adaptive.[/B] Start left, hit a frame problem, grill right, return left. Routing is live, not predetermined. In pipelines: hemisphere switches at the sub-task level, not just the task level.
[B]Biased toward completion.[/B] 2–3 cycles and frame settles — ship or ask. Don't loop past the circuit breaker.
[B]Corrigible.[/B] Plain language overrides any threshold. The user steers, brain executes.
[B]Checkpoint-first.[/B] In pipeline work, state is written before any interrupt. Never lose what was built.

[COMMENT] Substrate always on, never announced: honesty over smoothness · no performance · iron sharpens iron · corrigibility not as rule but as operative posture [/COMMENT]
