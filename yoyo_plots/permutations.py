"""
permutations.py – Draw the symmetries of a square (the dihedral group D₄) and
the permutations of ``(1, 2, 3, 4)`` they induce.

Two building blocks are provided:

* :class:`SquareSymmetries` – a labelled square whose four corners carry the
  numbers ``1, 2, 3, 4`` (optionally on four coloured sub-squares).  It can draw
  rotation arcs / flip axes as decorations, or *actually* rotate and flip,
  permuting the corner labels.
* :class:`Permutation` – a two-line permutation diagram.  Each element is a
  coloured circle (matching its sub-square) with its number inside; vertical
  arrows join the top row to the bottom row.

Both render themselves as vector SVG via :class:`yoyo_plots.common.SvgDrawing`,
so they drop straight into Quarto / Jupyter with ``display_vector`` and compose
horizontally with :func:`yoyo_plots.common.combine_svgs`.
"""

from __future__ import annotations

import math
from enum import Enum

import drawsvg as draw

from .common import SvgDrawing, combine_svgs

_FONT = "Comic Sans MS, Comic Sans, cursive"
_SQUARE_COLOR = "#333"
_GRID_COLOR = "#999"
_ARC_COLOR = "#060606"
_FLIP_COLOR = "#555"
_NUMBER_COLOR = "#1A1A1A"
_ARROW_COLOR = "#444"

#: Fill colour of each sub-square, keyed by the corner number it holds.  The
#: same palette colours the circles in :class:`Permutation`.  Slot order around
#: the square is top-left ``1``, top-right ``2``, bottom-right ``3``,
#: bottom-left ``4``.
SUBSQUARE_COLORS: dict[int, str] = {
    1: "#E8736C",  # coral red   (top-left)
    2: "#5B8FF9",  # blue        (top-right)
    3: "#5AD8A6",  # green       (bottom-right)
    4: "#F6C53F",  # amber       (bottom-left)
}


class Rotation(Enum):
    """Clockwise rotations of the square, in degrees."""

    R90 = 90
    R180 = 180
    R270 = 270


class FlipAxis(Enum):
    """Reflection axes of the square.

    * ``A`` – main diagonal (top-left → bottom-right).
    * ``B`` – anti-diagonal (top-right → bottom-left).
    * ``C`` – vertical axis (mirror left ↔ right).
    * ``D`` – horizontal axis (mirror top ↔ bottom).
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"


# Slot order used throughout: 0 = top-left, 1 = top-right, 2 = bottom-right,
# 3 = bottom-left (clockwise from the top-left corner).  Each entry below maps a
# destination slot to the *source* slot whose tile lands there after the
# transformation, i.e. ``new[i] = old[arrangement[i]]``.
_ROTATION_ARRANGEMENT: dict[Rotation, tuple[int, int, int, int]] = {
    Rotation.R90: (3, 0, 1, 2),
    Rotation.R180: (2, 3, 0, 1),
    Rotation.R270: (1, 2, 3, 0),
}

_FLIP_ARRANGEMENT: dict[FlipAxis, tuple[int, int, int, int]] = {
    FlipAxis.A: (0, 3, 2, 1),  # swap TR ↔ BL
    FlipAxis.B: (2, 1, 0, 3),  # swap TL ↔ BR
    FlipAxis.C: (1, 0, 3, 2),  # swap TL ↔ TR, BL ↔ BR
    FlipAxis.D: (3, 2, 1, 0),  # swap TL ↔ BL, TR ↔ BR
}


def _coerce_rotation(angle: Rotation | int) -> Rotation:
    """Accept a :class:`Rotation` or a raw ``90/180/270`` and return a Rotation."""
    if isinstance(angle, Rotation):
        return angle
    try:
        return Rotation(angle)
    except ValueError:
        raise ValueError(
            f"rotation must be one of 90, 180, 270 (or a Rotation), got {angle!r}"
        ) from None


def _coerce_axis(axis: FlipAxis | str) -> FlipAxis:
    """Accept a :class:`FlipAxis` or a raw ``'A'/'B'/'C'/'D'`` string."""
    if isinstance(axis, FlipAxis):
        return axis
    try:
        return FlipAxis(str(axis).upper())
    except ValueError:
        raise ValueError(
            f"flip axis must be one of 'A', 'B', 'C', 'D', got {axis!r}"
        ) from None


def _arrow_head(
    tip_x: float, tip_y: float, dx: float, dy: float, *, color: str, size: float = 11
) -> draw.Path:
    """Filled triangular head with its tip at ``(tip_x, tip_y)``.

    ``(dx, dy)`` is the (not necessarily unit) direction the head points in.
    """
    norm = math.hypot(dx, dy) or 1.0
    nx, ny = dx / norm, dy / norm
    px, py = -ny, nx  # perpendicular
    base_x, base_y = tip_x - size * nx, tip_y - size * ny
    head = draw.Path(fill=color, stroke="none")
    head.M(tip_x, tip_y)
    head.L(base_x + 0.5 * size * px, base_y + 0.5 * size * py)
    head.L(base_x - 0.5 * size * px, base_y - 0.5 * size * py)
    head.Z()
    return head


def _parse_label(name: str) -> list[tuple[str, bool]]:
    """Split a label into ``(text, is_subscript)`` runs.

    Supports LaTeX-style underscores: ``"R_1"`` → ``R`` with subscript ``1`` and
    ``"R_{10}"`` → ``R`` with subscript ``10``.  A bare ``_`` subscripts the next
    single character; ``_{…}`` subscripts the braced run.
    """
    segments: list[tuple[str, bool]] = []
    buf = ""
    i = 0
    while i < len(name):
        ch = name[i]
        if ch == "_":
            if buf:
                segments.append((buf, False))
                buf = ""
            i += 1
            if i < len(name) and name[i] == "{":
                close = name.find("}", i)
                close = close if close != -1 else len(name)
                segments.append((name[i + 1 : close], True))
                i = close + 1
            elif i < len(name):
                segments.append((name[i], True))
                i += 1
        else:
            buf += ch
            i += 1
    if buf:
        segments.append((buf, False))
    return segments


class SquareSymmetries(SvgDrawing):
    """A square whose corners are labelled ``1, 2, 3, 4`` and that knows the
    eight symmetries of the dihedral group D₄.

    The four corners sit, clockwise from the top-left, as ``1`` (top-left),
    ``2`` (top-right), ``3`` (bottom-right) and ``4`` (bottom-left).  With
    ``color=True`` the square is split into four equal sub-squares, each filled
    with the colour of the corner it carries (see :data:`SUBSQUARE_COLORS`); the
    numbers ride along, so rotating or flipping moves both colour and label
    together.

    Decorations versus transformations
    ----------------------------------
    * :meth:`draw_rotation` / :meth:`draw_flip_symmetries` only *annotate* the
      square (a curved arrow, or dotted mirror axes) – the labels stay put.
    * :meth:`rotate` / :meth:`flip_around_axis` *actually* permute the corner
      labels (and colours).

    All of these return ``self`` so they chain fluently::

        sq = SquareSymmetries(color=True).rotate(Rotation.R90)

    Parameters
    ----------
    color : bool
        Fill the four sub-squares with distinct colours.
    size : float
        Side length of the square in user units.
    margin : float
        Padding reserved around the square for rotation arcs / flip labels.
    font_size : float
        Font size of the corner numbers.
    show_numbers : bool
        Draw the corner numbers ``1, 2, 3, 4``.  Set ``False`` for a blank
        square (the sub-square colours, if any, are still shown).
    """

    def __init__(
        self,
        color: bool = True,
        *,
        size: float = 160,
        margin: float = 100,
        font_size: float = 26,
        show_numbers: bool = True,
    ):
        self.color = color
        self.size = size
        self.margin = margin
        self.font_size = font_size
        self.show_numbers = show_numbers
        # Tiles in slot order [TL, TR, BR, BL]; each is (number, fill colour).
        self._tiles: list[tuple[int, str]] = [
            (n, SUBSQUARE_COLORS[n]) for n in (1, 2, 3, 4)
        ]
        self._rotation_arc: Rotation | None = None
        self._show_flips: bool = False

    # ── construction helpers ────────────────────────────────────────────────
    def copy(self) -> "SquareSymmetries":
        """Return an independent copy preserving the current label arrangement."""
        clone = SquareSymmetries(
            self.color,
            size=self.size,
            margin=self.margin,
            font_size=self.font_size,
            show_numbers=self.show_numbers,
        )
        clone._tiles = list(self._tiles)
        clone._rotation_arc = self._rotation_arc
        clone._show_flips = self._show_flips
        return clone

    # ── decorations (do NOT move the labels) ────────────────────────────────
    def draw_rotation(self, angle: Rotation | int) -> "SquareSymmetries":
        """Annotate the square with a clockwise rotation arc of *angle* degrees.

        The square itself is left untouched – use :meth:`rotate` to move the
        labels.
        """
        self._rotation_arc = _coerce_rotation(angle)
        return self

    def draw_flip_symmetries(self) -> "SquareSymmetries":
        """Draw the four mirror axes as dotted lines, labelled ``A``–``D``."""
        self._show_flips = True
        return self

    # ── transformations (DO move the labels) ────────────────────────────────
    def _apply(self, arrangement: tuple[int, int, int, int]) -> "SquareSymmetries":
        self._tiles = [self._tiles[src] for src in arrangement]
        return self

    def rotate(self, angle: Rotation | int) -> "SquareSymmetries":
        """Rotate the square clockwise by 90, 180 or 270 degrees, moving labels."""
        return self._apply(_ROTATION_ARRANGEMENT[_coerce_rotation(angle)])

    def flip_around_axis(self, axis: FlipAxis | str) -> "SquareSymmetries":
        """Reflect the square across axis ``A``, ``B``, ``C`` or ``D``."""
        return self._apply(_FLIP_ARRANGEMENT[_coerce_axis(axis)])

    # Convenience aliases mirroring the requested "rotate 90/180/270" wording.
    def rotate90(self) -> "SquareSymmetries":
        return self.rotate(Rotation.R90)

    def rotate180(self) -> "SquareSymmetries":
        return self.rotate(Rotation.R180)

    def rotate270(self) -> "SquareSymmetries":
        return self.rotate(Rotation.R270)

    # ── bridge to permutation diagrams ──────────────────────────────────────
    @property
    def labels(self) -> tuple[int, int, int, int]:
        """Current corner labels in slot order ``[TL, TR, BR, BL]``."""
        return tuple(num for num, _ in self._tiles)  # type: ignore[return-value]

    def to_permutation(
        self, name: str | None = None, *, blank: bool = False
    ) -> "Permutation":
        """The permutation taking the original square to the current one.

        The top row is the pristine layout ``(1, 2, 3, 4)`` (slot order) and the
        bottom row is the number currently occupying each slot, so composing
        transformations on the square matches :func:`compose` on the diagrams.

        With ``blank=True`` the bottom row is left as white empty circles (a
        fill-in template) – the square's own arrangement is not revealed.
        """
        return Permutation((1, 2, 3, 4), None if blank else self.labels, name=name)

    # ── rendering ───────────────────────────────────────────────────────────
    def get_svg_dimensions(self) -> tuple[float, float]:
        full = self.size + 2 * self.margin
        return full, full

    def _draw_rotation_arc(self, sq: draw.Group) -> None:
        cx = cy = self.size / 2
        # Sit the arc *outside* the square: clear the corners (half-diagonal away
        # from the centre) yet stay inside the reserved margin.
        half_diag = (self.size / 2) * math.sqrt(2)
        max_r = self.size / 2 + self.margin - 16
        r = min(half_diag + 14, max_r)
        angle = self._rotation_arc.value
        a = math.radians(angle)

        def pt(radius: float, theta: float) -> tuple[float, float]:
            # Clockwise from the top (12 o'clock); SVG y points down.
            return cx + radius * math.sin(theta), cy - radius * math.cos(theta)

        x0, y0 = pt(r, 0.0)
        x1, y1 = pt(r, a)
        large = 1 if angle > 180 else 0
        path = draw.Path(fill="none", stroke=_ARC_COLOR, stroke_width=3)
        path.M(x0, y0)
        path.A(r, r, 0, large, 1, x1, y1)  # sweep=1 → clockwise on screen
        sq.append(path)

        # Arrowhead tangent to the arc at its end: d/dθ(sinθ, -cosθ)=(cosθ, sinθ).
        sq.append(_arrow_head(x1, y1, math.cos(a), math.sin(a), color=_ARC_COLOR))

        # Degree label out past the arc's midpoint (clear of the curve), clamped
        # inside the canvas.
        label_gap = 36
        lx, ly = pt(r + label_gap, a / 2)
        lo, hi = -self.margin + 14, self.size + self.margin - 14
        lx = min(max(lx, lo), hi)
        ly = min(max(ly, lo), hi)
        sq.append(
            draw.Text(
                f"{angle}°",
                self.font_size,
                lx,
                ly,
                font_family=_FONT,
                font_weight="bold",
                fill=_ARC_COLOR,
                text_anchor="middle",
                dominant_baseline="central",
            )
        )

    def _draw_flip_axes(self, sq: draw.Group) -> None:
        sz = self.size
        half = sz / 2
        ext = self.margin * 0.62  # how far the dotted axes reach past the edge
        lo, hi = -ext, sz + ext
        # (endpoints, label, label anchor) for each axis.
        axes = [
            (((lo, lo), (hi, hi)), "A", (hi, hi)),  # main diagonal
            (((hi, lo), (lo, hi)), "B", (lo, hi)),  # anti-diagonal
            (((half, lo), (half, hi)), "C", (half, lo)),  # vertical
            (((lo, half), (hi, half)), "D", (hi, half)),  # horizontal
        ]
        for (p0, p1), label, (lx, ly) in axes:
            sq.append(
                draw.Line(
                    p0[0],
                    p0[1],
                    p1[0],
                    p1[1],
                    stroke=_FLIP_COLOR,
                    stroke_width=1.6,
                    stroke_dasharray="5,5",
                )
            )
            # Nudge the label just outside its end of the axis.
            ox = 12 if lx > half else (-12 if lx < half else 0)
            oy = 12 if ly > half else (-12 if ly < half else 0)
            sq.append(
                draw.Text(
                    label,
                    self.font_size * 0.8,
                    lx + ox,
                    ly + oy,
                    font_family=_FONT,
                    font_weight="bold",
                    fill=_FLIP_COLOR,
                    text_anchor="middle",
                    dominant_baseline="central",
                )
            )

    def to_group(self, **_kwargs) -> draw.Group:
        g = draw.Group()
        sz = self.size
        half = sz / 2
        sq = draw.Group(transform=f"translate({self.margin},{self.margin})")

        # Sub-square fills, in slot order [TL, TR, BR, BL].
        slot_xy = [(0.0, 0.0), (half, 0.0), (half, half), (0.0, half)]
        for (sx, sy), (_, fill) in zip(slot_xy, self._tiles):
            sq.append(
                draw.Rectangle(
                    sx,
                    sy,
                    half,
                    half,
                    fill=fill if self.color else "white",
                    stroke=_GRID_COLOR,
                    stroke_width=1,
                )
            )

        # Outer border on top of the sub-square strokes.
        sq.append(
            draw.Rectangle(
                0, 0, sz, sz, fill="none", stroke=_SQUARE_COLOR, stroke_width=3
            )
        )

        # Corner numbers, inset from each corner.
        if self.show_numbers:
            inset = sz * 0.15
            label_xy = [
                (inset, inset),
                (sz - inset, inset),
                (sz - inset, sz - inset),
                (inset, sz - inset),
            ]
            for (lx, ly), (num, _) in zip(label_xy, self._tiles):
                sq.append(
                    draw.Text(
                        str(num),
                        self.font_size,
                        lx,
                        ly,
                        font_family=_FONT,
                        font_weight="bold",
                        fill=_NUMBER_COLOR,
                        text_anchor="middle",
                        dominant_baseline="central",
                    )
                )

        if self._rotation_arc is not None:
            self._draw_rotation_arc(sq)
        if self._show_flips:
            self._draw_flip_axes(sq)

        g.append(sq)
        return g


class Permutation(SvgDrawing):
    """A two-line permutation diagram for a permutation of ``(1, 2, 3, 4)``.

    The *top* and *bottom* rows are each a permutation (tuple) of the numbers
    ``1..4``.  Each element is drawn as a circle filled with its sub-square
    colour (see :data:`SUBSQUARE_COLORS`) with the number inside, and a vertical
    arrow joins the top element of every column to the one below it – so the top
    row maps element-wise onto the bottom row.  A single pair of parentheses
    wraps both rows::

        name = / 1 2 3 4 \\
               | ↓ ↓ ↓ ↓ |
               \\ 2 3 1 4 /

    Diagrams compose horizontally to illustrate ``f ∘ g``; see :func:`compose`
    (to compute the resulting permutation) and :func:`draw_composition` (to lay
    several diagrams out with ``∘`` / ``=``).

    Parameters
    ----------
    top : tuple[int, ...]
        Permutation of ``(1, 2, 3, 4)`` for the top row (the domain order).
    bottom : tuple[int, ...] | None
        Permutation of ``(1, 2, 3, 4)`` for the bottom row, or ``None`` to leave
        the bottom row as white empty circles (a fill-in template); the arrows
        still point to them.
    name : str | None
        Optional label drawn as ``name =`` to the left of the diagram.  LaTeX
        style underscores render as subscripts, so ``"R_1"`` shows as ``R₁`` and
        ``"R_{10}"`` as ``R₁₀``.
    radius : float
        Circle radius.
    h_spacing : float
        Horizontal gap between adjacent circles.
    v_gap : float
        Vertical gap between the two rows.
    font_size : float
        Font size of the numbers inside the circles.
    show_brackets : bool
        Wrap both rows in a single pair of parentheses.
    """

    def __init__(
        self,
        top: tuple[int, ...],
        bottom: tuple[int, ...] | None,
        name: str | None = None,
        *,
        radius: float = 20,
        h_spacing: float = 16,
        v_gap: float = 64,
        font_size: float = 22,
        show_brackets: bool = True,
    ):
        top = tuple(top)
        bottom = tuple(bottom) if bottom is not None else None
        bad_top = sorted(top) != [1, 2, 3, 4]
        bad_bottom = bottom is not None and sorted(bottom) != [1, 2, 3, 4]
        if bad_top or bad_bottom:
            raise ValueError(
                "top and bottom must each be a permutation of (1, 2, 3, 4) "
                f"(bottom may be None), got top={top}, bottom={bottom}"
            )
        self.top = top
        self.bottom = bottom
        self.name = name
        self.radius = radius
        self.h_spacing = h_spacing
        self.v_gap = v_gap
        self.font_size = font_size
        self.show_brackets = show_brackets
        self._pad = 18.0

    # ── geometry ────────────────────────────────────────────────────────────
    _CHAR_W = 0.58  # rough glyph-width factor, as a fraction of font size
    _PAREN_GAP = 12.0  # horizontal gap between a parenthesis and the circles

    @property
    def _col_step(self) -> float:
        return 2 * self.radius + self.h_spacing

    @property
    def _content_height(self) -> float:
        """Vertical extent of the two rows, top circle top to bottom circle base."""
        return 4 * self.radius + self.v_gap

    @property
    def _paren_bulge(self) -> float:
        return self._content_height * 0.11

    @property
    def _bracket_w(self) -> float:
        """Horizontal room each wrapping parenthesis needs."""
        return self._PAREN_GAP + self._paren_bulge + 4 if self.show_brackets else 0.0

    @property
    def _name_segments(self) -> list[tuple[str, bool]]:
        """Parsed label runs, with a trailing `` =`` appended."""
        if not self.name:
            return []
        return _parse_label(self.name) + [(" =", False)]

    @property
    def _name_w(self) -> float:
        return sum(
            len(text) * self.font_size * (0.7 if is_sub else 1.0) * self._CHAR_W
            for text, is_sub in self._name_segments
        )

    def _content_x0(self) -> float:
        """X of the first circle's centre."""
        x = self._pad + self._name_w
        if self.name:
            x += self._pad
        return x + self._bracket_w + self.radius

    def _row_cy(self) -> tuple[float, float]:
        top_cy = self._pad + self.radius
        return top_cy, top_cy + 2 * self.radius + self.v_gap

    def get_svg_dimensions(self) -> tuple[float, float]:
        row_w = 4 * 2 * self.radius + 3 * self.h_spacing
        width = self._content_x0() - self.radius + row_w + self._bracket_w + self._pad
        _, bot_cy = self._row_cy()
        height = bot_cy + self.radius + self._pad
        return width, height

    # ── rendering ───────────────────────────────────────────────────────────
    def _draw_brackets(self, g: draw.Group, top_cy: float, bot_cy: float) -> None:
        """Draw one tall parenthesis on each side, wrapping both rows."""
        if not self.show_brackets:
            return
        x0 = self._content_x0()
        content_left = x0 - self.radius
        content_right = x0 + 3 * self._col_step + self.radius
        y_top = top_cy - self.radius - 6
        y_bot = bot_cy + self.radius + 6
        k = (y_bot - y_top) * 0.12  # control-point inset for a rounded curve
        bulge = self._paren_bulge
        lx = content_left - self._PAREN_GAP
        rx = content_right + self._PAREN_GAP
        for x, sign in ((lx, -1), (rx, 1)):
            paren = draw.Path(fill="none", stroke=_NUMBER_COLOR, stroke_width=3)
            paren.M(x, y_top)
            paren.C(x + sign * bulge, y_top + k, x + sign * bulge, y_bot - k, x, y_bot)
            g.append(paren)

    def _draw_name(self, g: draw.Group, cy_mid: float) -> None:
        """Draw the ``name =`` label, rendering ``_`` runs as subscripts."""
        x = self._pad
        for text, is_sub in self._name_segments:
            fs = self.font_size * (0.7 if is_sub else 1.0)
            dy = self.font_size * 0.22 if is_sub else 0.0
            g.append(
                draw.Text(
                    text,
                    fs,
                    x,
                    cy_mid + dy,
                    font_family=_FONT,
                    font_weight="bold",
                    fill=_NUMBER_COLOR,
                    text_anchor="start",
                    dominant_baseline="central",
                )
            )
            x += len(text) * fs * self._CHAR_W

    def _draw_row(
        self, g: draw.Group, values: tuple[int, ...] | None, cy: float
    ) -> None:
        """Draw one row of circles.  ``values=None`` → white, empty circles."""
        x0 = self._content_x0()
        for i in range(4):
            cx = x0 + i * self._col_step
            num = values[i] if values is not None else None
            g.append(
                draw.Circle(
                    cx,
                    cy,
                    self.radius,
                    fill=SUBSQUARE_COLORS[num] if num is not None else "white",
                    stroke=_SQUARE_COLOR,
                    stroke_width=2,
                )
            )
            if num is not None:
                g.append(
                    draw.Text(
                        str(num),
                        self.font_size,
                        cx,
                        cy,
                        font_family=_FONT,
                        font_weight="bold",
                        fill=_NUMBER_COLOR,
                        text_anchor="middle",
                        dominant_baseline="central",
                    )
                )

    def to_group(self, **_kwargs) -> draw.Group:
        g = draw.Group()
        top_cy, bot_cy = self._row_cy()

        # Name label and wrapping parentheses, centred between the rows.
        if self.name:
            self._draw_name(g, (top_cy + bot_cy) / 2)
        self._draw_brackets(g, top_cy, bot_cy)

        # Vertical arrows top → bottom (drawn under the circles).
        x0 = self._content_x0()
        for i in range(4):
            cx = x0 + i * self._col_step
            y_start = top_cy + self.radius
            y_end = bot_cy - self.radius
            g.append(
                draw.Line(
                    cx, y_start, cx, y_end - 2, stroke=_ARROW_COLOR, stroke_width=2
                )
            )
            g.append(_arrow_head(cx, y_end, 0, 1, color=_ARROW_COLOR, size=9))

        self._draw_row(g, self.top, top_cy)
        self._draw_row(g, self.bottom, bot_cy)
        return g


def compose(*perms: Permutation, name: str | None = None) -> Permutation:
    """Compose permutation diagrams in ``∘`` order (rightmost applied first).

    ``compose(R1, R2)`` returns ``R1 ∘ R2`` – the permutation you get by
    applying ``R2`` and then ``R1`` – matching how the equivalent
    :class:`SquareSymmetries` transformations stack.  The result's top row is
    the identity ``(1, 2, 3, 4)``.
    """
    if not perms:
        raise ValueError("compose() needs at least one permutation")
    # Each diagram's bottom row, 0-based, is its slot arrangement a[i].
    arrangements = [tuple(v - 1 for v in p.bottom) for p in perms]
    bottom = []
    for i in range(4):
        x = i
        for a in arrangements:
            x = a[x]
        bottom.append(x + 1)
    return Permutation((1, 2, 3, 4), tuple(bottom), name=name)


# Sentinel segment text rendered as a drawn composition ring rather than the
# tiny, baseline-misaligned ``∘`` glyph.  Sized to the font and centred on the
# label's mid-line so it reads as a proper "compose" operator.
_RING_OP = "∘"


def _seg_advance(text: str, is_sub: bool, font_size: float) -> float:
    """Horizontal space a label segment occupies."""
    if text == _RING_OP:
        return 2 * (font_size * 0.30) + 2 * (font_size * 0.34)  # pads + diameter
    fs = font_size * (0.7 if is_sub else 1.0)
    return len(text) * fs * Permutation._CHAR_W


def _label_to_svg(segments: list[tuple[str, bool]], font_size: float) -> str:
    """Render label *segments* as a standalone SVG.

    Subscript runs (``is_sub``) render smaller and lowered; the ``∘`` operator
    renders as a drawn ring sized to *font_size* and vertically centred.
    """
    width = max(sum(_seg_advance(t, s, font_size) for t, s in segments), 1.0)
    height = font_size * 1.8
    d = draw.Drawing(width, height)
    cy = height / 2
    x = 0.0
    for text, is_sub in segments:
        if text == _RING_OP:
            pad = font_size * 0.30
            ring_r = font_size * 0.24
            d.append(
                draw.Circle(
                    x + pad + ring_r,
                    cy,
                    ring_r,
                    fill="none",
                    stroke=_NUMBER_COLOR,
                    stroke_width=max(2.2, font_size * 0.1),
                )
            )
            x += _seg_advance(text, is_sub, font_size)
            continue
        fs = font_size * (0.7 if is_sub else 1.0)
        dy = font_size * 0.22 if is_sub else 0.0
        d.append(
            draw.Text(
                text,
                fs,
                x,
                cy + dy,
                font_family=_FONT,
                font_weight="bold",
                fill=_NUMBER_COLOR,
                text_anchor="start",
                dominant_baseline="central",
            )
        )
        x += len(text) * fs * Permutation._CHAR_W
    return d.as_svg()


def _op_to_svg(symbol: str, font_size: float) -> str:
    """Standalone SVG for a single operator (``∘`` ring or ``=``)."""
    return _label_to_svg([(symbol, False)], font_size)


def _nameless(p: Permutation) -> Permutation:
    """A copy of *p* without its name label, preserving every style setting."""
    return Permutation(
        p.top,
        p.bottom,
        name=None,
        radius=p.radius,
        h_spacing=p.h_spacing,
        v_gap=p.v_gap,
        font_size=p.font_size,
        show_brackets=p.show_brackets,
    )


def _names_segments(names: list[str], *, with_equals: bool) -> list[tuple[str, bool]]:
    """Segments for ``name₁ ∘ name₂ ∘ … [=]`` with per-name subscripts."""
    segs: list[tuple[str, bool]] = []
    for i, nm in enumerate(names):
        if i:
            segs.append((_RING_OP, False))
        segs.extend(_parse_label(nm))
    if with_equals:
        segs.append((" =", False))
    return segs


def draw_composition(
    perms: list[Permutation],
    *,
    show_result: bool = True,
    result_name: str | None = None,
    spacing: float = 12.0,
) -> str:
    """Lay diagrams out as a composition equation and return a standalone SVG.

    When every diagram is named the names are factored out, so the layout reads
    like the maths it illustrates::

        R_1 ∘ R_2 = (plot) ∘ (plot) = (plot) = R_3

    i.e. a ``name₁ ∘ name₂ =`` prefix, the bare permutation plots joined with
    ``∘``, an ``=``, the composed plot (via :func:`compose`), and a ``= result``
    suffix.  Names use the same ``_`` subscript syntax as :class:`Permutation`,
    and every ``∘`` is drawn as a ring sized to the label font.  If any diagram
    is unnamed, each plot keeps its own label instead.

    With ``show_result=False`` the composed plot and trailing ``=`` are omitted.
    The result is ready for :func:`yoyo_plots.common.display_vector`.
    """
    if not perms:
        raise ValueError("draw_composition() needs at least one permutation")
    fs = perms[0].font_size

    # Bare plots joined by ring / equals operators, all sized to the font.  Items
    # are glued with plain spacing; combine_svgs centres each one vertically.
    items: list = []
    if all(p.name for p in perms):
        # Named: factor names into a prefix (and a "= result" suffix).
        items.append(
            _label_to_svg(
                _names_segments([p.name for p in perms], with_equals=show_result), fs
            )
        )
        plots = [_nameless(p).to_svg() for p in perms]
        result = _nameless(compose(*perms, name=result_name)) if show_result else None
        suffix_name = result_name
    else:
        # Unnamed: each plot keeps its own label.
        plots = [p.to_svg() for p in perms]
        result = compose(*perms, name=result_name) if show_result else None
        suffix_name = None

    for i, plot_svg in enumerate(plots):
        if i:
            items.append(_op_to_svg(_RING_OP, fs))
        items.append(plot_svg)

    if result is not None:
        items.append(_op_to_svg("=", fs))
        items.append(result.to_svg())
        if suffix_name:
            items.append(_label_to_svg([("= ", False)] + _parse_label(suffix_name), fs))

    return combine_svgs(items, direction="horizontal", spacing=spacing)
