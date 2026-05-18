"""
golden_layout.py — Golden-ratio screen geometry for CAD animation compositing.

φ ≈ 1.6180339887... derived from the quadratic x² − x − 1 = 0
Key property: φ = 1 + 1/φ  →  segment cut at 1/φ from one end leaves a
smaller rectangle similar to the original.

Reference: cut-the-knot.org/do_you_know/GoldenRatio.shtml

Usage:
    from golden_layout import GoldenLayout
    layout = GoldenLayout(1280, 720)
    print(layout.phi_x1)            # first vertical φ-line (38.2% from left)
    print(layout.focal_point)       # primary golden intersection (x, y)
    print(layout.label_anchor(0))   # φ-derived label position 0
    print(layout.title_height)      # header bar height from φ
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import NamedTuple

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0   # ≈ 1.618
INV_PHI: float = 1.0 / PHI                   # ≈ 0.618 = φ-1
INV_PHI2: float = INV_PHI ** 2               # ≈ 0.382 = 1 - 1/φ


class Rect(NamedTuple):
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2


@dataclass
class GoldenLayout:
    """Screen layout derived entirely from φ and the frame dimensions.

    All measurements are in pixels, integers unless specified.
    "Content viewport" is the area between the title bar and the subtitle bar.
    """
    width: int
    height: int

    # ── internal ────────────────────────────────────────────────────────────
    _phi: float = field(init=False, default=PHI)

    def __post_init__(self) -> None:
        w, h = self.width, self.height
        # Title bar height: h / φ^5 ≈ h * 0.0854
        # At 720p → 61.5 ≈ 62px; at 1080p → 92px
        self._title_h: int = round(h / (PHI ** 5))
        # Subtitle bar: same height as title for visual balance
        self._sub_h: int = self._title_h
        # Progress bar strip inside subtitle bar, at bottom
        self._prog_h: int = max(3, round(self._title_h / PHI ** 4))

        # Viewport = everything between title and subtitle bars
        self._vp_x: int = 0
        self._vp_y: int = self._title_h
        self._vp_w: int = w
        self._vp_h: int = h - self._title_h - self._sub_h

        # Vertical φ-lines across the full frame
        self._phi_x1: int = round(w * INV_PHI2)   # 38.2% from left  ≈ 489
        self._phi_x2: int = round(w * INV_PHI)    # 61.8% from left  ≈ 791

        # Horizontal φ-lines within the viewport
        self._phi_vy1: int = self._vp_y + round(self._vp_h * INV_PHI2)  # 38.2%
        self._phi_vy2: int = self._vp_y + round(self._vp_h * INV_PHI)   # 61.8%

        # Primary focal point: the viewer's natural eye-rest (upper-right φ intersection)
        # Per golden ratio conventions the strongest focal region is the intersection
        # of the 61.8% vertical and 38.2% horizontal lines.
        self._focal: tuple[int, int] = (self._phi_x2, self._phi_vy1)

        # Label panel: right of φ_x2 line, full viewport height.
        # Width = w * INV_PHI2 ≈ 38.2% of frame
        self._label_panel = Rect(
            x=self._phi_x2,
            y=self._vp_y,
            w=w - self._phi_x2,
            h=self._vp_h,
        )

        # Content area: left of φ_x2, within viewport.
        # (The model renders across the full viewport; the label panel is an
        # *overlay zone*, not a crop.)
        self._content = Rect(
            x=0,
            y=self._vp_y,
            w=self._phi_x2,
            h=self._vp_h,
        )

        # Pre-compute font sizes using φ as the type-scale ladder.
        # Base = 20px; each step ×φ (up) or ÷φ (down).
        base = max(12, round(h / 36.0))          # ≈ 20 at 720p
        self._fs_title: int = round(base * PHI)  # ≈ 32
        self._fs_label: int = base               # ≈ 20
        self._fs_small: int = round(base / PHI)  # ≈ 12
        self._fs_tiny:  int = round(base / PHI ** 2)  # ≈ 8

        # Label anchor rows inside the label panel.
        # Use φ-subdivisions of the label panel height.
        # First label at panel_h * INV_PHI2 = 38.2% down from panel top.
        # Spacing between labels = first_y / φ (self-similar).
        lh = self._label_panel.h
        ly0 = self._label_panel.y
        row0 = ly0 + round(lh * INV_PHI2)
        spacing = round(lh * INV_PHI2 / PHI)
        self._label_rows: list[int] = [
            row0 + i * spacing for i in range(6)
        ]
        # Trim to within the viewport
        self._label_rows = [
            r for r in self._label_rows
            if self._label_panel.y <= r <= self._label_panel.bottom - 20
        ]

        # Label column: left edge of panel + small inset
        self._label_col_x: int = self._phi_x2 + max(8, round(h * 0.011))

    # ── public properties ────────────────────────────────────────────────────

    @property
    def phi(self) -> float:
        return self._phi

    @property
    def title_height(self) -> int:
        """Height of the title bar in pixels."""
        return self._title_h

    @property
    def subtitle_height(self) -> int:
        """Height of the subtitle/narration bar in pixels."""
        return self._sub_h

    @property
    def progress_height(self) -> int:
        """Height of the progress strip inside the subtitle bar."""
        return self._prog_h

    @property
    def viewport(self) -> Rect:
        """Full viewport rect between title bar and subtitle bar."""
        return Rect(self._vp_x, self._vp_y, self._vp_w, self._vp_h)

    @property
    def content_rect(self) -> Rect:
        """Preferred content area (left of first φ vertical line)."""
        return self._content

    @property
    def label_panel(self) -> Rect:
        """Right-side label panel zone."""
        return self._label_panel

    @property
    def phi_x1(self) -> int:
        """38.2% vertical line (x)."""
        return self._phi_x1

    @property
    def phi_x2(self) -> int:
        """61.8% vertical line (x) — divides content from label panel."""
        return self._phi_x2

    @property
    def phi_vy1(self) -> int:
        """38.2% horizontal line within viewport (y)."""
        return self._phi_vy1

    @property
    def phi_vy2(self) -> int:
        """61.8% horizontal line within viewport (y)."""
        return self._phi_vy2

    @property
    def focal_point(self) -> tuple[int, int]:
        """Primary golden intersection — (x, y)."""
        return self._focal

    @property
    def font_title(self) -> int:
        """Font size for main titles."""
        return self._fs_title

    @property
    def font_label(self) -> int:
        """Font size for callout labels."""
        return self._fs_label

    @property
    def font_small(self) -> int:
        """Font size for secondary info text."""
        return self._fs_small

    @property
    def font_tiny(self) -> int:
        """Font size for annotation / fine print."""
        return self._fs_tiny

    # ── helper methods ────────────────────────────────────────────────────────

    def label_anchor(self, index: int) -> tuple[int, int]:
        """Return the (x, y) screen position for the n-th label callout box.

        Labels are stacked in φ-proportional rows inside the right label panel.
        The column x is a fixed inset from phi_x2.
        """
        row_y = self._label_rows[min(index, len(self._label_rows) - 1)]
        return (self._label_col_x, row_y)

    def title_rect(self) -> Rect:
        """Full title bar rect."""
        return Rect(0, 0, self.width, self._title_h)

    def subtitle_rect(self) -> Rect:
        """Full subtitle bar rect."""
        return Rect(0, self.height - self._sub_h, self.width, self._sub_h)

    def progress_rect(self, fraction: float) -> Rect:
        """Progress bar fill rect at current fraction [0..1]."""
        bar_x = round(self.width * INV_PHI2 * 0.5)   # indent by ~φ²/2
        bar_w = round(self.width * INV_PHI)
        bar_y = self.height - self._prog_h - 1
        fill_w = round(bar_w * max(0.0, min(1.0, fraction)))
        return Rect(bar_x, bar_y, fill_w, self._prog_h)

    def debug_overlay(self, draw, alpha: int = 80) -> None:
        """Draw the φ-grid onto a PIL ImageDraw for layout inspection."""
        from PIL import Image, ImageDraw
        phi_col = (255, 215, 0, alpha)
        def line(x0, y0, x1, y1, c=(255, 215, 0)):
            draw.line((x0, y0, x1, y1), fill=c, width=1)
        # Vertical φ-lines
        line(self._phi_x1, 0, self._phi_x1, self.height, (80, 180, 80))
        line(self._phi_x2, 0, self._phi_x2, self.height, (255, 215, 0))
        # Horizontal φ-lines (viewport)
        line(0, self._phi_vy1, self.width, self._phi_vy1, (80, 180, 80))
        line(0, self._phi_vy2, self.width, self._phi_vy2, (80, 180, 80))
        # Focal point
        fx, fy = self._focal
        r = 6
        draw.ellipse((fx - r, fy - r, fx + r, fy + r), outline=(255, 80, 80), width=2)
        # Title / subtitle bar borders
        line(0, self._title_h, self.width, self._title_h, (60, 60, 80))
        line(0, self.height - self._sub_h, self.width, self.height - self._sub_h, (60, 60, 80))
        # Label row ticks
        for i, ry in enumerate(self._label_rows):
            draw.rectangle(
                (self._label_col_x - 4, ry - 2, self._label_col_x + 12, ry + 2),
                fill=(180, 140, 60),
            )

    def summary(self) -> str:
        lines = [
            f"GoldenLayout({self.width}×{self.height})",
            f"  φ = {PHI:.6f}",
            f"  title_height        = {self._title_h}px",
            f"  subtitle_height     = {self._sub_h}px",
            f"  viewport            = {self.viewport}",
            f"  φ_x1 (38.2%)        = {self._phi_x1}",
            f"  φ_x2 (61.8%)        = {self._phi_x2}",
            f"  φ_vy1 (38.2%)       = {self._phi_vy1}",
            f"  φ_vy2 (61.8%)       = {self._phi_vy2}",
            f"  focal_point         = {self._focal}",
            f"  label_rows          = {self._label_rows}",
            f"  fonts (title/lbl/sm/tiny) = {self._fs_title}/{self._fs_label}/{self._fs_small}/{self._fs_tiny}",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    # Print the layout for common resolutions and render a φ-grid PNG for review
    from PIL import Image, ImageDraw
    for res in [(1280, 720), (1920, 1080)]:
        lay = GoldenLayout(*res)
        print(lay.summary())
        print()

    # Generate a layout sketch at 1280×720 for visual review
    lay = GoldenLayout(1280, 720)
    img = Image.new("RGB", (1280, 720), (11, 16, 24))
    draw = ImageDraw.Draw(img)
    lay.debug_overlay(draw)
    img.save("/tmp/golden_layout_720.png")
    print("Layout sketch → /tmp/golden_layout_720.png")
