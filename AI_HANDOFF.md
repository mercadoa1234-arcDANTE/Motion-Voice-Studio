# Agent Loop — Motion Studio v3

The discipline for any production run.

## The loop

```
SOURCE PAPER + USER PROMPT
        │
        ▼
   /brain  ──── score 5 axes, pick a pattern
        │
        ▼
   PLAN (storyboard JSON · scene-by-scene)
        │
        ▼
   /grill ──── only what the plan / source / prompt cannot answer
        │       (≤ 3 sharp questions, NEVER more)
        ▼
   EXECUTE
        │
        ├── audio first (Kokoro phrase chunks)
        ├── render frames per shot (manim · pyvista · composite · image · title)
        ├── audio master (-14 LUFS, denoise, optional reverb)
        ├── soft-sub mux (mov_text track + sidecar .srt — NEVER pixel burn-in)
        └── deliver
        │
        ▼
   ON TOOL-LIMIT REACHED → emit a checkpoint with state → user types "continue"
   ON FAILURE → /brain re-routes, doesn't re-prompt the user unless stuck
```

## /brain scoring (silent)

Score each axis Low / High before deciding which skills to involve.

| Axis | Low | High |
|---|---|---|
| Stakes | brainstorm | investor / regulator / public |
| Clarity | shape known | shape might be wrong |
| Novelty | familiar | no template exists |
| Complexity | single concern | systemic |
| Depth | high-level only | architecture + execution |

- **2+ High** → both hemispheres (right finds the frame; left hardens it). Pattern 2 or 3.
- **1 High** → single hemisphere. Pattern 1 (left only) or 4 (left only, fast).
- **All Low** → skip /brain, direct answer.

For a typical source-paper-to-video build: Stakes=High, Clarity=High (the paper's intent might be misread), Novelty=Medium-to-High → **Pattern 2 (right first, left second)**.

## /grill discipline

Ask only what the source, plan, or prompt does NOT answer. Self-grill first:

1. Read the source paper end-to-end (or its abstract + headings + figures).
2. Map the user prompt to scenes the storyboard already plans for.
3. Whatever remains genuinely unknown — that's the grill question.

Cap: **3 sharp questions max**, one at a time, **ordered by highest impact**. When the user's answer reveals something inferable, state what you now understand rather than asking about it.

## Adaptive but on-source

The plan can deepen mid-execution, but it should never drift off-source unless:

- **The user explicitly asks** to add to or diverge from the source.
- **A synthesis of two source points** yields a deeply enriched main-line connection. Only then is a "rabbit-trail" beat permitted; it must reconnect to the main thesis at the next scene.
- A claim in the source is mathematically wrong or theory-specific — flag it inline with epistemic-honesty markers, do not silently propagate.

If you find yourself adding a scene that doesn't trace to a source claim or a user request, STOP. Reconnect or cut it.

## The "continue" contract

When tool-call limits force a cutoff:

1. **Checkpoint the state** — write `/home/claude/production/<project>/state.json` with what's done, what's pending, and what the next action would be.
2. **Tell the user honestly** what's done and what's pending. No spin.
3. **Wait for "continue"** — when the user types it, resume from the checkpoint without re-asking.
4. **If something is genuinely blocked** (missing file, unanswerable design question), use /grill (one question) BEFORE asking for "continue".

This is the Ralph loop: user types "continue" until the work is done. Claude doesn't re-prompt unless the only path forward needs a human answer.

## When NOT to ask the user

- The answer is in the source paper (read it).
- The answer is in the SKILL.md or one of the `references/*.md` files (read them first).
- A reasonable default exists (use it and proceed; note the assumption inline).
- `/brain` or `/natural-mind` can resolve the ambiguity by re-reading prior context.

## When TO ask the user

- Source contradicts itself and the user's intent decides which version stands.
- The user's prompt includes mutually exclusive requirements.
- A planned scene depends on a fact (a date, a name, a file path) that doesn't exist anywhere in context and a default would be visibly wrong.

In these cases the question is one sentence, kindly framed (per `/grill` discipline), and offered with a default the user can accept by saying "use your default."

## Default workflow (the happy path)

```bash
# 0. Setup
cd /home/claude/motion-studio-v3
bash scripts/verify_setup.sh

# 1. Ingest the source paper
python scripts/source_doc_pass.py /mnt/user-data/uploads/paper.pdf \
    --out /home/claude/production/<project>/assets/source_docs/<doc_id>/

# 2. Plan the storyboard (use /brain, write the JSON)
#    Storyboard includes: image shots for source pages, manim for mechanism
#    scenes, composite for CAD-with-overlay where relevant.

# 3. Render
python scripts/storyboard.py /home/claude/production/<project>/storyboard.json \
    --out /home/claude/production/<project>/output

# 4. Verify (Gates A-F)
python scripts/self_check_v2.py /home/claude/production/<project>/output/final.mp4 ...

# 5. Deliver
cp /home/claude/production/<project>/output/final.mp4 /mnt/user-data/outputs/
present_files /mnt/user-data/outputs/final.mp4
```

When this loop hits a tool limit, the user types "continue" — and the loop resumes from the checkpoint without ceremony.
