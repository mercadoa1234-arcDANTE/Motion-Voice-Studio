---
name: brain
description: >
  Optional cognitive orchestration layer. Routes between analytical (rigor)
  and exploratory (natural-mind/grill) modes. Summon with /brain when the
  problem shape is unclear, stakes are real, or you've been looping >300 tokens.
  Silent. Quality is the only visible signal. NOT required for Motion-Voice-Studio
  standard production runs — README-FIRST.md covers the full pipeline without it.
---

# Brain — Optional Cognitive Orchestrator

Not required. Summon when the task would benefit from more than one cognitive pass:
novel architectures, high-stakes deliverables, or stuck loops.

---

## Score the task first (5 axes, silent)

| Axis | Low | High |
|---|---|---|
| Stakes | Brainstorm, no delivery | Client-facing, high revision cost |
| Clarity | Shape is known | Frame might be fundamentally wrong |
| Novelty | Familiar territory | No template exists |
| Complexity | Single concern | Many failure modes |
| Depth | High-level only | Architecture + execution both needed |

2+ High → both hemispheres. 1 High → one hemisphere. All Low → skip brain, answer directly.

---

## Four patterns

**Pattern 1 — Clear + imminent stakes → Left first (Rigor)**  
Surface assumptions inline → draft → break → compress → ship.  
*Use for: contract edits, tight spec implementation, known-shape problems.*

**Pattern 2 — Clear + complex + novel → Right first, Left second**  
Natural-Mind finds the architecture → Grill tests it → Rigor hardens → ship.  
*Use for: new pipeline design, novel lesson structure, feature architecture.*

**Pattern 3 — Ambiguous shape → Right loop, hard exit at 3 cycles**  
Grill → Natural-Mind → Grill → settle. If frame doesn't settle in 3 cycles:
surface one plain-sentence contradiction and ask one question. Don't spiral.

**Pattern 4 — Known work, one pass → Left only**  
Surface one inline assumption → draft → compress → ship.  
*Use for: small component patch, copy update, targeted fix.*

---

## Rigor (Left hemisphere default)

Silent. No announced passes. Three internal passes before surfacing:

1. **Surface**: What load-bearing assumptions could be wrong?
2. **Break**: What would cause this to fail under real conditions?
3. **Compress**: Remove everything that doesn't change the outcome.

Trigger: stakes are real, delivery is imminent, work must be defensible.  
Gate-adaptive when a checklist exists: Break pass runs against the checklist.

---

## Natural-Mind (Right hemisphere default)

No frameworks. No scaffolding. Raw honest reasoning.

Trigger: "what do you actually think", "real talk", "think naturally", "no templates".  
Interrupt false frames. Hold contradictions. Cross-domain pattern finding.

---

## Grill (Self-interrogation)

Before surfacing questions to the user, grill self first:

1. Read the full source/prompt
2. Form questions
3. Answer each one yourself from available context
4. Only surface what genuinely can't be answered

Max 3 questions per surface. If you can answer it from context, don't ask.

---

## Interrupt thresholds

| Type | Rule |
|---|---|
| **Fire** | Current work blocked. Data loss risk. Switch immediately. |
| **Better path** | Same output, different approach, >15% token savings. Switch if savings exceed ~50-token re-anchor cost. |
| **Higher value** | New task unlocks more; deadline < 4 hrs. Promote if value delta justifies context loss. |
| **Override** | "Hold on that." "Pause this." "Do X instead." Always honor immediately. |

Checkpoint before any switch: save code state, note position, tag in git. ~50 tokens upfront saves 200+ on cold restart.

---

## Brain's cognition extras (sub-skills it routes between)

Detailed catalog: `brain/extras/EXTRAS_MANIFEST.md`

| Sub-skill | File | Role |
|---|---|---|
| Rigor        | `brain/extras/rigor.skill.md`        | Left default. 3 silent passes: surface · break · compress. |
| Natural-Mind | `brain/extras/natural-mind.skill.md` | Right default. Raw unfiltered reasoning, no frameworks. |
| Grill        | `brain/extras/grill.skill.md`        | Self-interrogation before surfacing questions (3-question cap). |
| Grunt-Brain  | `brain/extras/grunt-brain.skill.md`  | Compressed symbolic notation when symbols beat prose. |

Each is **standalone-callable** — users can invoke "use rigor on this" or "grill me"
directly without summoning brain. Brain coordinates them when multiple modes are
needed for one task; otherwise it stays out of the way.

## Skills brain can coordinate (Motion-Voice-Studio)

When summoned in an MVS context, brain is aware of and can route work through:

| Module | Path | Brain uses it for |
|---|---|---|
| Production pipeline | `docs/PIPELINE.md` | Agent loop, audio-first contract, mux discipline |
| Audio + Kokoro | `docs/AUDIO.md` | Voice choice, phrase pacing, NaN recovery |
| Render engines | `docs/RENDER.md` | Engine selection (manim · pyvista · composite · image · bom · title) |
| Text display | `scripts/text_display.py` | Kerning, overlap detection/avoidance/fixing, subtitles |
| Troubleshooting | `docs/TROUBLESHOOT.md` | Fast lookup when a render or audio pass breaks |
| CAD (optional) | `docs/CAD.md` | build123d, pyvista, assembly schema, recon handoffs |
| Browser (optional) | `docs/BROWSER.md` | WebGPU, Hunyuan3D, GPU offload |

**Coordination patterns by task:**

- **New lesson from a topic** → Pattern 2 (right designs storyboard → left hardens JSON → pipeline executes)
- **Adapt a paper into a video** → Pattern 2, source-doc pass first, then standard pipeline
- **Fix a render bug** → Pattern 4 (one-pass left), use `docs/TROUBLESHOOT.md` directly
- **Design a new engine** → Pattern 3 (right loop, ambiguous shape), 3-cycle circuit breaker

## Motion-Voice-Studio integration

When routing to the MVS pipeline:

1. **Right** designs the storyboard architecture (engine choices, narration arc, composite layout).
2. **Left (Rigor)** gate-checks the JSON (schema, timing arithmetic, engine choices vs. table).
3. **Execution** → Pattern 4 (known pipeline). Brain does not re-score per shot — the pipeline's own loop handles micro-routing.
4. **Tool-limit** → Checkpoint interrupt. Write `state.json`, report, wait for "continue."

Brain scores once at the start and sets the pattern. The pipeline executes.  
Do not re-invoke brain inside the render loop — that's double-routing overhead.

---

## Token conservation

- Manual chaining (`/rigor` → `/grill` → `/natural-mind`) = 3× overhead for the same result.
- Call `/brain` once. Internal orchestration runs the sequence.
- Any loop reading as ceremony after 300 tokens: exit. Re-enter at Pattern 1 with Rigor.
