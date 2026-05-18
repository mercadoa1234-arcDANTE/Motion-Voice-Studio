# Teaching — Structure That Lands

When a prompt is vague ("make a video about X"), most of the work is figuring out *what to teach*, not *how to render it*. This file collects the patterns that make educational videos actually educational, modeled on what makes 3Blue1Brown videos work.

## The single-question principle

Every good lesson can be stated as one question the video answers. Before you write a single scene, write the question.

Examples:
- ❌ "Make a video about the Fourier transform" — too broad to plan.
- ✅ "What does the Fourier transform actually *do*, geometrically?" — answerable in 2 minutes.

- ❌ "Make a video about machine learning" — fifty videos couldn't cover it.
- ✅ "Why does gradient descent work?" — single video, clean.

If your topic doesn't reduce to a single question, you're trying to make several videos. Pick one.

## Structure — the seven-beat lesson

3Blue1Brown videos follow (loosely) the same structural skeleton. Use it.

1. **Hook.** A puzzle, a paradox, a weird fact. ~10s. The viewer needs a reason to keep watching.
2. **Restate the question.** Concretely, with the variables named. ~5s.
3. **Naive approach.** Show the obvious thing first, then show why it's not enough. ~15-20s.
4. **The pivot.** "What if instead..." — introduce the actual idea. ~15s.
5. **The mechanism.** The visual heart of the lesson. ~30-60s. This is where animation earns its keep.
6. **Generalization.** "Notice this works for any..." — extend the pattern. ~15s.
7. **Closing thought.** The takeaway in one sentence. The viewer should be able to repeat this back. ~10s.

Total: ~2-3 minutes for a tight lesson. Longer is OK if the mechanism step has multiple sub-mechanisms.

## Pacing rules of thumb

- A scene of 8s feels brisk. A scene of 25s feels like a lecture. Stay in 10-20 unless you're showing a complex animation that needs time to read.
- The first 10 seconds set the contract: "this video will be about X". Don't bury the topic.
- The last 10 seconds plant the takeaway. Don't trail off into "and there's lots more to say...".
- Silence is allowed and welcome — the inter-scene gap (250ms voice change, 150ms same voice) is your friend. Don't fight it by cramming filler.

## Choosing the visual story

Concepts have natural visual representations. Match them.

| Concept type | Visual representation |
|---|---|
| Function of one variable | Curve on `axes_plot` |
| Two-variable relationship | Surface, contour plot, or heatmap |
| Time evolution | `transform_chain` or animated curve |
| System / process | `diagram` (boxes + arrows) |
| Statistical distribution | Histogram on `axes_plot` or scatter |
| Algorithm / sequence | `bullets` showing steps appearing one at a time |
| Geometric transformation | `transform_chain` with the object visibly morphing |
| Field / vector field | Quiver of arrows or `custom` |
| Probability event tree | `diagram` with nodes |

When the concept is abstract (a definition, a rule), find a *concrete instance* to animate, not the abstract version. "What does an integral do?" → animate accumulating area, not the integral notation.

## The narrator's voice

The narration text is half the lesson. Some patterns that work:

**Specificity beats generality.** "Pick the number 3" lands better than "Pick any number".

**Verbs first.** "We multiply" beats "Multiplication is performed".

**Address the listener.** "Notice the dot" beats "It can be observed that".

**Pause before the punchline.** End the scene before delivering the key insight. The inter-scene gap gives it weight.

**Concede the difficulty.** "This part is genuinely tricky" earns trust. Pretending nothing is hard alienates the viewer.

**Avoid hedge words.** "Sort of", "kind of", "basically" — strip them unless they're load-bearing.

## When the user's prompt is vague

Vague prompts are common. Don't grill the user. Instead:

1. Pick the **most generous, useful** interpretation in your head.
2. State that interpretation in **one sentence** at the top of your response.
3. Build it.

Example: User says "make a video about entropy". Decide: thermodynamic entropy (mixing, irreversibility) or information entropy (Shannon, surprise). Both are great topics; pick one.

A reasonable interpretation, stated up front:
> "I'm going to make a 2-minute lesson on thermodynamic entropy — specifically, why mixing is irreversible. Tell me if you wanted information theory instead."

Then proceed. The user can redirect cheaply if you guessed wrong; making them write a spec is worse for everyone.

## When the user's prompt is specific

If they say "explain why eigenvalues of a 2×2 matrix are the roots of det(A − λI) = 0", that's the topic. Don't rewrite it. Reason about how to teach exactly that.

## Test the lesson against this checklist

Before generating, read your draft aloud (in your head, fast). Check:

- [ ] Could a friend who doesn't know the topic follow this?
- [ ] Is there a moment where the "aha" is supposed to land? Is it well-positioned?
- [ ] Could you cut a scene without losing the lesson? If yes, cut it.
- [ ] Does the closing line restate the answer to the opening question?
- [ ] Is the math notation introduced with the words for it (don't show `∫` and assume the viewer knows it's an integral)?

If any of these is "no", revise before generating audio. Audio generation is the slow step — fix the script first.

## Counter-example: what a bad lesson looks like

A failed prompt: "Make a 2-minute video covering the entire history of artificial intelligence."

Why it fails:
- Topic is too broad — no single question.
- 2 minutes / 70 years = 1.7 seconds per year. Useless.
- No visual mechanism — history is dates and names, not geometry.

A better take on the same intent: "Why was the 2012 ImageNet result a turning point?" — one question, one mechanism (depth + GPU + dataset), specific date, visual: a bar chart of error rates dropping.

When a user gives you a too-broad prompt, narrow it on their behalf and proceed.
