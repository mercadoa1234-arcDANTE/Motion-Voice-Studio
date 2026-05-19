"""
Built-in manim Scene classes for the manim_action DSL.

Each `kind` in a `manim_action` maps to a builder function that constructs a
Scene subclass at runtime. The renderer in render_manim.py calls
`build_scene_class(action)` to get the class, then runs it through manim's
normal CLI render path.

Add new kinds by writing a builder function and registering in KIND_BUILDERS.
"""
from __future__ import annotations

# manim is a heavy import; only import when actually used
def _get_manim():
    import manim
    return manim


# ── builders ──────────────────────────────────────────────────────────────

def _build_title(action: dict):
    m = _get_manim()
    primary   = action.get("primary", "")
    secondary = action.get("secondary", "")
    subtitle  = action.get("subtitle", "")

    class TitleScene(m.Scene):
        def construct(self):
            items = []
            if primary:
                t = m.Text(primary, color=m.WHITE, font_size=72, weight=m.BOLD)
                items.append(t)
            if secondary:
                s = m.Text(secondary, color="#7aa9d6", font_size=36).next_to(items[-1], m.DOWN) if items else m.Text(secondary, color="#7aa9d6", font_size=36)
                items.append(s)
            if subtitle:
                u = m.Text(subtitle, color="#9aa3ad", font_size=24).next_to(items[-1], m.DOWN) if items else m.Text(subtitle, color="#9aa3ad", font_size=24)
                items.append(u)
            if not items:
                return
            grp = m.VGroup(*items).move_to(m.ORIGIN)
            self.play(m.FadeIn(grp, run_time=0.8))
            self.wait(1.5)
    return TitleScene


def _build_formula(action: dict):
    m = _get_manim()
    tex_str = action.get("tex", "")
    annotations = action.get("annotations", [])
    use_mathtex = action.get("use_mathtex", True)
    position = action.get("position", "center")  # center | top | bottom | top-right | top-left

    class FormulaScene(m.Scene):
        def construct(self):
            try:
                eq = m.MathTex(tex_str, color=m.WHITE).scale(0.9) if use_mathtex \
                     else m.Tex(tex_str, color=m.WHITE).scale(0.9)
            except Exception:
                # LaTeX not installed — fall back to Text
                eq = m.Text(tex_str.replace("\\", ""), color=m.WHITE, font_size=36)
            # Position
            if position == "top":
                eq.to_edge(m.UP, buff=0.7)
            elif position == "top-right":
                eq.to_corner(m.UR, buff=0.7)
            elif position == "top-left":
                eq.to_corner(m.UL, buff=0.7)
            elif position == "bottom":
                eq.to_edge(m.DOWN, buff=0.7)
            # Animate
            self.play(m.Write(eq, run_time=1.2))
            self.wait(0.5)
            # Annotations: pulse-indicate subexpressions in order
            for ann in annotations:
                try:
                    idx = ann["index"]
                    sub = eq[0][idx:idx + ann.get("length", 1)] if hasattr(eq, "__getitem__") else eq
                    color_name = ann.get("color", "#7aa9d6")
                    self.play(m.Indicate(sub, color=color_name, run_time=0.8))
                    self.wait(0.3)
                except Exception:
                    continue
            self.wait(1.0)
    return FormulaScene


def _build_bullets(action: dict):
    m = _get_manim()
    items_text = action.get("items", [])
    title = action.get("title", "")

    class BulletsScene(m.Scene):
        def construct(self):
            elements = []
            if title:
                t = m.Text(title, color="#7aa9d6", font_size=44, weight=m.BOLD).to_edge(m.UP, buff=0.5)
                self.play(m.FadeIn(t, run_time=0.4))
                elements.append(t)
            previous = elements[-1] if elements else None
            for it in items_text:
                bullet = m.Text(f"•  {it}", color=m.WHITE, font_size=30)
                if previous:
                    bullet.next_to(previous, m.DOWN, buff=0.35, aligned_edge=m.LEFT)
                self.play(m.FadeIn(bullet, run_time=0.4))
                self.wait(0.5)
                previous = bullet
                elements.append(bullet)
            self.wait(1.0)
    return BulletsScene


def _build_highlight(action: dict):
    """Just a piece of plain text or label, optionally with an arrow.
    Useful for callouts that don't need true 3D anchoring."""
    m = _get_manim()
    text = action.get("text", "")
    subtitle = action.get("subtitle", "")
    position = action.get("position", "top-right")  # placement on screen
    box = action.get("box", True)

    class HighlightScene(m.Scene):
        def construct(self):
            txt = m.Text(text, color=m.WHITE, font_size=36, weight=m.BOLD)
            if subtitle:
                sub = m.Text(subtitle, color="#9aa3ad", font_size=22).next_to(txt, m.DOWN, aligned_edge=m.LEFT)
                grp = m.VGroup(txt, sub)
            else:
                grp = m.VGroup(txt)
            if position == "top-right":
                grp.to_corner(m.UR, buff=0.5)
            elif position == "top-left":
                grp.to_corner(m.UL, buff=0.5)
            elif position == "bottom-left":
                grp.to_corner(m.DL, buff=0.5)
            elif position == "bottom-right":
                grp.to_corner(m.DR, buff=0.5)
            if box:
                rect = m.SurroundingRectangle(grp, color="#7aa9d6", buff=0.25, corner_radius=0.1, stroke_width=2)
                bg = m.BackgroundRectangle(grp, color="#0e1116", fill_opacity=0.7, buff=0.25, corner_radius=0.1)
                self.play(m.FadeIn(bg, run_time=0.3), m.Create(rect, run_time=0.5))
            self.play(m.Write(grp, run_time=1.0))
            self.wait(1.5)
    return HighlightScene


def _build_lower_third(action: dict):
    """A teaching lower-third panel — title + subtitle in a strip near the bottom."""
    m = _get_manim()
    title = action.get("title", "")
    subtitle = action.get("subtitle", "")

    class LowerThirdScene(m.Scene):
        def construct(self):
            t = m.Text(title, color=m.WHITE, font_size=40, weight=m.BOLD)
            s = m.Text(subtitle, color="#7aa9d6", font_size=24).next_to(t, m.DOWN, aligned_edge=m.LEFT)
            grp = m.VGroup(t, s).to_corner(m.DL, buff=0.5)
            strip = m.SurroundingRectangle(grp, color="#7aa9d6", buff=0.4, corner_radius=0.1, stroke_width=2)
            bg = m.BackgroundRectangle(grp, color="#0e1116", fill_opacity=0.78, buff=0.4, corner_radius=0.1)
            self.play(m.FadeIn(bg, run_time=0.3), m.Create(strip, run_time=0.4))
            self.play(m.Write(grp, run_time=1.0))
            self.wait(1.5)
            self.play(m.FadeOut(m.VGroup(grp, strip, bg), run_time=0.5))
    return LowerThirdScene


def _build_custom(action: dict):
    """Execute raw user-provided manim code. The action must include `code`
    (string) defining a Scene subclass and `scene_name` (string)."""
    m = _get_manim()
    code = action["code"]
    scene_name = action["scene_name"]
    namespace = {"manim": m}
    exec(f"from manim import *\n{code}", namespace)
    return namespace[scene_name]


# ── registry ──────────────────────────────────────────────────────────────

KIND_BUILDERS = {
    "title":       _build_title,
    "formula":     _build_formula,
    "bullets":     _build_bullets,
    "highlight":   _build_highlight,
    "lower_third": _build_lower_third,
    "custom":      _build_custom,
}


def build_scene_class(action: dict):
    """Dispatch a manim_action description to its Scene class."""
    kind = action.get("kind")
    if kind not in KIND_BUILDERS:
        raise ValueError(f"Unknown manim_action kind: {kind!r}. "
                         f"Known: {list(KIND_BUILDERS)}")
    return KIND_BUILDERS[kind](action)


def scene_from_action(action: dict):
    """Convenience wrapper."""
    return build_scene_class(action)
