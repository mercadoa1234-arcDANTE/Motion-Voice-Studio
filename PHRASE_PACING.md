# Manim Action DSL — Visual Primitive Recipes

`manim_action` is a structured description of what animates during a scene. The renderer translates each `kind` into Manim primitives and emits the scene code. This DSL covers ~80% of educational videos. For the other 20%, use `kind: "custom"` with raw Manim code.

## Common fields (every kind)

- `kind`: required. One of the recipes below.
- `transition_in`: optional, default `"fade"`. One of `"fade"`, `"write"`, `"create"`, `"none"`.
- `transition_out`: optional, default `"none"`. The next scene's transition_in handles handover.
- `palette`: optional override of default palette per scene.

## The kinds

### `kind: "title"`

Opening or section break. Pure text on screen.

```json
{
  "kind": "title",
  "primary": "The Fourier Transform",
  "secondary": "What frequencies live inside a signal?",
  "subtitle": null
}
```

`primary` is the big text. `secondary` is the colored tagline below. `subtitle` is optional small dim text.

### `kind: "formula"`

A mathematical statement, optionally annotated.

```json
{
  "kind": "formula",
  "tex": "\\hat{f}(x) = \\int_{-\\infty}^{\\infty} f(t)\\, e^{-2\\pi i x t}\\, dt",
  "annotations": [
    {"index": 0, "label": "spectrum", "color": "green"},
    {"index": 3, "label": "signal",   "color": "blue"},
    {"index": 5, "label": "winding",  "color": "pink"}
  ]
}
```

`index` refers to the index of a sub-expression in the MathTex split. The renderer adds arrows from labels to the indexed term, in sequence.

### `kind: "axes_plot"`

A function or parametric curve on coordinate axes.

```json
{
  "kind": "axes_plot",
  "x_range": [-1.5, 1.5],
  "y_range": [-1.5, 1.5],
  "curves": [
    {"parametric": "[cos(2*PI*t), sin(2*PI*t)]", "t_range": [0, 1], "color": "blue"},
    {"function": "sin(x) * exp(-0.3*x)", "x_range": [0, 6], "color": "purple"}
  ],
  "labels": {"x": "Re", "y": "Im"},
  "trace_dot": true
}
```

`trace_dot: true` adds a glowing dot that animates along the first curve during the scene's audio duration.

### `kind: "side_by_side"`

Two `axes_plot`s, animated in sync. Useful for time-domain ↔ frequency-domain, before/after, etc.

```json
{
  "kind": "side_by_side",
  "left":  {"axes_plot": {...}, "label": "time domain"},
  "right": {"axes_plot": {...}, "label": "wound signal"},
  "linked_value_tracker": {
    "name": "x",
    "from": 1.0,
    "to": 3.5
  }
}
```

The `linked_value_tracker` drives BOTH plots — useful for "as we change x, watch what happens on both panels".

### `kind: "transform_chain"`

A sequence of object transformations. Replaces a static idea with a moving one.

```json
{
  "kind": "transform_chain",
  "stages": [
    {"object": "Circle(radius=1)", "label": "circle"},
    {"object": "ParametricFunction(...)", "label": "spiral", "morph": "transform"},
    {"object": "ParametricFunction(...)", "label": "wider spiral", "morph": "transform"}
  ]
}
```

`morph: "transform"` does a `Transform` (smooth shape morph). `morph: "replace"` does `ReplacementTransform` (clean swap).

### `kind: "bullets"`

A growing bulleted list. Each bullet appears as a separate sub-step within the scene's audio duration.

```json
{
  "kind": "bullets",
  "header": "What we just saw",
  "items": [
    {"text": "Circles encode pure frequencies", "color": "blue"},
    {"text": "Spirals encode decaying signals", "color": "purple"},
    {"text": "The center of mass IS the spectrum", "color": "gold"}
  ]
}
```

The renderer auto-distributes the items across the scene's duration: if the audio is 12s and there are 3 bullets, each appears at ~4s intervals.

### `kind: "diagram"`

Boxes-and-arrows. For systems, flows, anything non-quantitative.

```json
{
  "kind": "diagram",
  "nodes": [
    {"id": "input",   "text": "Signal f(t)",    "position": [-4, 0]},
    {"id": "winding", "text": "Wind around\\ncircle at rate x", "position": [0, 0]},
    {"id": "output",  "text": "F̂(x)",            "position": [4, 0]}
  ],
  "edges": [
    {"from": "input", "to": "winding", "label": "input"},
    {"from": "winding", "to": "output", "label": "centroid"}
  ]
}
```

### `kind: "highlight"`

Don't change the scene; emphasize part of what's already there. Used in scenes that follow a previous `axes_plot` or `formula`.

```json
{
  "kind": "highlight",
  "target": "previous_scene_object_id",
  "effect": "circle"
}
```

`effect`: `circle`, `flash`, `wiggle`, `pulse`.

### `kind: "custom"`

Raw Manim code for cases the recipes don't cover. The renderer wraps your code in a scene method; you have access to `self`, all of Manim, and any colors/fonts the skill defines.

```json
{
  "kind": "custom",
  "code": "ax = Axes(); self.play(Create(ax)); dot = Dot(ax.c2p(0,0)); self.play(FadeIn(dot))"
}
```

**Use sparingly.** Custom code bypasses the styling and timing safety nets. Prefer composing recipes if at all possible.

## How timing works

Every recipe is rendered to fit exactly the scene's audio duration. The renderer:

1. Reads `scene_<id>.wav` length from `audio/timing.json`.
2. Distributes the action's animation calls across that duration with `run_time` proportional to the action's complexity (titles get 1s of write time; complex curves get more; the rest is `wait`).
3. Appends `self.wait(post_gap)` according to `pacing` rules.

**You never write `wait()` or `run_time` values.** The renderer owns timing.

## Color palette (used unless overridden)

```
background  #0d0d1a     dark indigo
narrator/Text #EAEAEA   off-white
gold        #FFD700     accent / centroid
blue        #58C4DD     primary curves
pink        #FF6B9D     formula / winding
green       #A8FF78     positive emphasis
orange      #FF9A3C     decay / second curve
purple      #C77DFF     transformation
dim         #666688     axes / grids
```

These match the 3Blue1Brown feel without copying the exact hex values. If the user asks for a different palette, override `palette` in the action or in the top-level `video.background`.

## Choosing the right kind

| If the scene is about... | Use |
|---|---|
| "Here's what we're learning" | `title` |
| "Here's the formula" | `formula` |
| "Watch this function" | `axes_plot` |
| "These two things are related" | `side_by_side` |
| "Watch this become that" | `transform_chain` |
| "Now we know..." | `bullets` |
| "How the system works" | `diagram` |
| "Look here on what's already on screen" | `highlight` |
| "I need something the recipes can't do" | `custom` |
