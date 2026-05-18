# Brain v4 — Cognitive Orchestration Package

Drop-in skill package for use alongside Motion Studio v3 (or any complex
production pipeline). Five skills, one orchestrator.

---

## What's in the package

```
brain-v4/
├── README.md                     This file
├── INTEGRATION_ANALYSIS.md       Full MECE analysis: current vs desired state,
│                                 Motion Studio pattern scoring, gap analysis
├── brain/
│   └── SKILL.md                  Unified orchestrator. Routes all skills.
│                                 v4: adds Pattern 5 (Production Pipeline),
│                                 Checkpoint interrupt, Semantic Wiring
│                                 principle, Motion Studio integration note.
├── rigor/
│   └── SKILL.md                  Analytical discipline. v2: gate-adaptive
│                                 Break pass, production triggers, anonymous.
├── natural-mind/
│   └── SKILL.md                  Raw honest reasoning. No frameworks. Unchanged.
├── grill/
│   └── SKILL.md                  Self-interrogation before user questions. v2:
│                                 adds source-doc self-grill rule. 3-question cap.
└── deep-think/
    └── SKILL.md                  Fallback mode orchestration. Four modes (grunt,
                                  natural-mind, grill, large-file-edit). Anonymous.
```

---

## How to install

Drop the skill folders alongside your other skills. If using with Motion Studio v3:

```
your-skills/
├── brain/              ← from this package
├── rigor/              ← from this package
├── natural-mind/       ← from this package
├── grill/              ← from this package
├── deep-think/         ← from this package
└── motion-studio/      ← your existing motion-studio-v3 folder
```

No configuration required. Brain reads all skill SKILL.md files at routing time.

---

## What changed from the previous brain

| Skill | Change |
|---|---|
| brain | + Pattern 5 (Production Pipeline: gate-sequential, checkpoint-first) |
| brain | + Checkpoint interrupt type (tool-limit: write state, report, wait) |
| brain | + Semantic Wiring section (NL + scripts = unified code) |
| brain | + Motion Studio integration note (defer micro-routing to skill's own loop) |
| brain | − Personal name and project references throughout |
| rigor | + Gate-adaptive Break pass (runs against gate checklists when present) |
| rigor | + Production pipeline triggers (video, architecture, multi-stage builds) |
| rigor | − "Anthony" references in Pass 1 and Pass 2 |
| rigor | − Legal/regulatory domain language from triggers |
| grill | + Source-doc self-grill rule (read source fully before forming questions) |
| grill | + Explicit 3-question cap with self-grill-first ordering |
| natural-mind | No changes — already clean and generic |
| deep-think | − Personal relationship comments from [COMMENT] blocks |
| deep-think | + Note: brain routes here as fallback only, not first reach |

---

## The Semantic Wiring Principle (why this matters for Motion Studio)

Motion Studio v3 is a semantically-wired system. The storyboard JSON is the
program — not a config file, not a content document, a program. The SKILL.md
and references/*.md are operational rules, not background reading. Natural
language narration fields carry execution semantics (they change audio timing,
which changes all downstream frame counts). The Python scripts are runtime
engines that evaluate the program.

Brain v4 encodes this understanding. When routing to motion-studio:

1. Right hemisphere designs the storyboard architecture (engine choices per shot,
   narration arc, source-doc weaving, composite layout plan).
2. Left hemisphere (rigor) hardens the JSON (gate-checks schema, validates engine
   choices against tool table, verifies timing arithmetic).
3. Execution phase → Pattern 5. Motion Studio's AGENT_LOOP.md owns micro-routing.
   Brain does not re-score per shot (eliminates double-routing overhead).
4. Tool-call limit → Checkpoint interrupt. Write state.json, report honestly,
   wait for "continue." Not a question — a report.

---

## How the double-routing problem was solved

Motion Studio v3's AGENT_LOOP.md already re-states brain's 5-axis scoring
verbatim. In the previous brain, routing to /motion-studio caused two full
scoring passes (brain's + AGENT_LOOP's) for the same task — overhead without
benefit.

Brain v4 resolves this by making the handoff explicit: brain scores and sets
the pattern, then notes in its Motion Studio integration section that internal
micro-routing is delegated to the skill's own loop. AGENT_LOOP.md's scoring
becomes the authoritative execution-phase router. No duplication.

For any skill with its own agent loop: same principle. Brain sets the initial
pattern. The skill's loop handles sub-task routing internally.

---

## Anonymous deployment

All personal names, project references, and domain-specific persona elements
have been removed. The substrate values (honesty, corrigibility, quality,
iron-sharpens-iron) are universal operating principles — they remain. The
skills are deployable in any professional context without modification.
