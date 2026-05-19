# brain

A cognitive orchestration package for AI agents working on multi-stage,
high-stakes, or production-pipeline tasks. Four skills, one router, one
design philosophy.

For the design philosophy, see `ARCHITECTURE.md`.

---

## Contents

```
brain/
├── README.md           This file. Logistics.
├── ARCHITECTURE.md     Design philosophy. Why the skills are shaped this way.
├── brain/
│   └── SKILL.md        Orchestrator. Routes work between left/right hemispheres
│                       through five patterns. Includes interrupt logic and
│                       internal thinking notation.
├── rigor/
│   └── SKILL.md        Left-hemisphere default. Three silent passes: surface
│                       load-bearing assumptions, break against gates or failure
│                       modes, compress for signal density.
├── natural-mind/
│   └── SKILL.md        Right-hemisphere default. Honest reasoning without
│                       scaffolds. Plain language.
├── grill/
│   └── SKILL.md        Self-interrogation discipline. Read source fully before
│                       forming user-facing questions. 3-question cap, ordered
│                       by impact.
└── grunt-brain/
    └── SKILL.md        Compressed symbolic thinking notation. Standalone mode
                        for fast sketches and flow shapes where symbols beat
                        prose. Not invoked by brain — used independently.
```

---

## Install

Copy each skill folder into the skills directory of the environment:

```
your-skills/
├── brain/
├── rigor/
├── natural-mind/
├── grill/
└── grunt-brain/
```

`README.md` and `ARCHITECTURE.md` are package documentation — they live
alongside the folders or in their own location, not inside a skill directory.

No configuration. No dependencies on each other beyond the contract that brain
routes to the others when a task is scored above the threshold.

---

## When to Use

[TABLE]
[TR][TH]Situation[/TH][TH]Load this package[/TH][/TR]
[TR][TD]Multi-stage build with sequential dependencies[/TD][TD]Yes[/TD][/TR]
[TR][TD]Production pipeline (video, build, deploy, multi-engine)[/TD][TD]Yes[/TD][/TR]
[TR][TD]High-stakes deliverable (client, public, regulatory)[/TD][TD]Yes[/TD][/TR]
[TR][TD]Ambiguous problem shape requiring architecture work[/TD][TD]Yes[/TD][/TR]
[TR][TD]Long-running task likely to hit tool-call limits[/TD][TD]Yes[/TD][/TR]
[TR][TD]Single factual lookup[/TD][TD]No[/TD][/TR]
[TR][TD]Conversational chat[/TD][TD]No[/TD][/TR]
[TR][TD]Quick one-pass edit[/TD][TD]No[/TD][/TR]
[/TABLE]

---

## Quick Start

The skills are operational documents. Loading them into context loads their
rules. Brain reads the task, scores it, and routes through the appropriate
pattern. Routing is silent — the output speaks.

To use the package with a domain-specific skill (production pipeline, UI
framework, etc.), load both. Brain sets the initial pattern. When the domain
skill has its own agent loop documented, brain defers internal routing to that
skill. No double-routing.

For the operational rules each skill enforces, read the individual `SKILL.md`
files. For the design philosophy that connects them, read `ARCHITECTURE.md`.
