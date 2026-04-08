"""
Geometric shape drawings: rectangles and right triangles.

Uses **drawsvg** and inherits from :class:`~common.SvgDrawing` so that
objects render natively as SVG in notebooks via ``display_vector()``.

Rectangle
---------
* Optional dimension labels, internal grid, area fill, per-cell
  highlights, corner right-angle marks and a diagonal that splits
  the rectangle into two independently coloured triangles.

RightTriangle
-------------
* Optional dimension labels and Pythagorean squares drawn on each
  side, each independently colourable.
"""

from __future__ import annotations

import math

import drawsvg as draw

from .common import SvgDrawing, strip_svg_header

_CELL = 40  # pixels per data-unit
_MARGIN = 30  # px around the figure
_DIM_OFFSET = 20  # px gap for dimension labels
_LINE_COLOR = "black"
_LINE_WIDTH = 1.5
_GRID_COLOR = "#999"
_GRID_WIDTH = 0.5
_FONT_SIZE = 14
_FONT_FAMILY = "sans-serif"
_RIGHT_ANGLE_SIZE = 0.25  # in data units
_DIAGONAL_WIDTH = 1.5
_AREA_OPACITY = 0.25
_CELL_OPACITY = 0.35
_SQUARE_OPACITY = 0.20
_SQUARE_BORDER_OPACITY = 0.5


class Rectangle(SvgDrawing):
    """A drawable rectangle on a unit grid.

    Parameters
    ----------
    width, height : int
        Rectangle dimensions in data units.
    show_dimensions : bool
        Draw width / height labels alongside the edges.
    show_grid : bool
        Draw the internal 1 x 1 grid.
    area_color : str | None
        Fill colour for the whole rectangle.
    cell_size : int
        Pixel size of one data unit.

    Decorations are added via fluent ``add_*`` methods::

        svg = (Rectangle(5, 3)
            .add_cell_highlights({(0, 0): "red", (1, 2): "blue"})
            .add_right_angles()
            .add_diagonal("orange", "skyblue")
            .to_svg()
        )
    """

    def __init__(
        self,
        width: int,
        height: int,
        *,
        show_dimensions: bool = True,
        show_grid: bool = True,
        area_color: str | None = None,
        cell_size: int = _CELL,
        dimension_labels: tuple[str, str] | None = None,
    ):
        self.w = width
        self.h = height
        self.show_dimensions = show_dimensions
        self.show_grid = show_grid
        self.area_color = area_color
        self.cell_size = cell_size
        self.dimension_labels = dimension_labels

        self._cell_highlights: dict[tuple[int, int], str] = {}
        self._right_angles = False
        self._diagonal: tuple[str, str] | None = None

    def add_cell_highlights(self, cells: dict[tuple[int, int], str]) -> Rectangle:
        """Colour specific grid cells.  Keys are ``(col, row)`` with
        origin at the **lower-left** corner."""
        self._cell_highlights = cells
        return self

    def add_right_angles(self) -> Rectangle:
        """Draw a small right-angle symbol in every corner."""
        self._right_angles = True
        return self

    def add_diagonal(
        self, color_below: str = "orange", color_above: str = "skyblue"
    ) -> Rectangle:
        """Draw the main diagonal (lower-left → upper-right) and fill each
        triangle half with *color_below* / *color_above*."""
        self._diagonal = (color_below, color_above)
        return self

    def to_svg(self) -> str:
        return strip_svg_header(super().to_svg())

    def get_svg_dimensions(self) -> tuple[float, float]:
        extra_x = _DIM_OFFSET if self.show_dimensions else 0
        extra_y = _DIM_OFFSET if self.show_dimensions else 0
        return (
            self.w * self.cell_size + 2 * _MARGIN + extra_x,
            self.h * self.cell_size + 2 * _MARGIN + extra_y,
        )

    def to_group(self, **kwargs) -> draw.Group:
        g = draw.Group()
        cs = self.cell_size
        # Origin offset so y=0 is at the bottom
        ox = _MARGIN + (_DIM_OFFSET if self.show_dimensions else 0)
        oy = _MARGIN
        pw = self.w * cs  # pixel width
        ph = self.h * cs  # pixel height

        def _sx(x: float) -> float:
            """Data x → SVG x."""
            return ox + x * cs

        def _sy(y: float) -> float:
            """Data y → SVG y  (y increases upward)."""
            return oy + ph - y * cs

        # To fill out the area
        if self.area_color and not self._diagonal:
            g.append(
                draw.Rectangle(
                    _sx(0),
                    _sy(self.h),
                    pw,
                    ph,
                    fill=self.area_color,
                    opacity=_AREA_OPACITY,
                )
            )

        if self._diagonal:
            below, above = self._diagonal
            # Below diagonal (lower-left triangle)
            g.append(
                draw.Lines(
                    _sx(0),
                    _sy(0),
                    _sx(self.w),
                    _sy(0),
                    _sx(self.w),
                    _sy(self.h),
                    close=True,
                    fill=below,
                    opacity=_AREA_OPACITY,
                )
            )
            # Above diagonal (upper-left triangle)
            g.append(
                draw.Lines(
                    _sx(0),
                    _sy(0),
                    _sx(0),
                    _sy(self.h),
                    _sx(self.w),
                    _sy(self.h),
                    close=True,
                    fill=above,
                    opacity=_AREA_OPACITY,
                )
            )

        for (cx, cy), color in self._cell_highlights.items():
            g.append(
                draw.Rectangle(
                    _sx(cx),
                    _sy(cy + 1),
                    cs,
                    cs,
                    fill=color,
                    opacity=_CELL_OPACITY,
                )
            )

        if self.show_grid:
            for ix in range(1, self.w):
                g.append(
                    draw.Line(
                        _sx(ix),
                        _sy(0),
                        _sx(ix),
                        _sy(self.h),
                        stroke=_GRID_COLOR,
                        stroke_width=_GRID_WIDTH,
                    )
                )
            for iy in range(1, self.h):
                g.append(
                    draw.Line(
                        _sx(0),
                        _sy(iy),
                        _sx(self.w),
                        _sy(iy),
                        stroke=_GRID_COLOR,
                        stroke_width=_GRID_WIDTH,
                    )
                )

        g.append(
            draw.Rectangle(
                _sx(0),
                _sy(self.h),
                pw,
                ph,
                fill="none",
                stroke=_LINE_COLOR,
                stroke_width=_LINE_WIDTH,
            )
        )

        if self._diagonal:
            g.append(
                draw.Line(
                    _sx(0),
                    _sy(0),
                    _sx(self.w),
                    _sy(self.h),
                    stroke=_LINE_COLOR,
                    stroke_width=_DIAGONAL_WIDTH,
                )
            )

        if self._right_angles:
            s = _RIGHT_ANGLE_SIZE
            corners = [
                ((0, 0), (s, 0), (s, s), (0, s)),  # lower-left
                ((self.w, 0), (-s, 0), (-s, s), (0, s)),  # lower-right
                ((self.w, self.h), (-s, 0), (-s, -s), (0, -s)),  # upper-right
                ((0, self.h), (s, 0), (s, -s), (0, -s)),  # upper-left
            ]
            for (bx, by), (d1x, d1y), (d2x, d2y), (d3x, d3y) in corners:
                g.append(
                    draw.Lines(
                        _sx(bx + d1x),
                        _sy(by + d1y),
                        _sx(bx + d2x),
                        _sy(by + d2y),
                        _sx(bx + d3x),
                        _sy(by + d3y),
                        close=False,
                        fill="none",
                        stroke=_LINE_COLOR,
                        stroke_width=_LINE_WIDTH,
                    )
                )

        if self.show_dimensions:
            w_label = self.dimension_labels[0] if self.dimension_labels else str(self.w)
            h_label = self.dimension_labels[1] if self.dimension_labels else str(self.h)
            # Width label (below)
            g.append(
                draw.Text(
                    w_label,
                    _FONT_SIZE,
                    _sx(self.w / 2),
                    _sy(0) + _DIM_OFFSET,
                    text_anchor="middle",
                    dominant_baseline="auto",
                    font_family=_FONT_FAMILY,
                    fill=_LINE_COLOR,
                    font_style="italic" if self.dimension_labels else "normal",
                )
            )
            # Height label (left)
            g.append(
                draw.Text(
                    h_label,
                    _FONT_SIZE,
                    _sx(0) - _DIM_OFFSET,
                    _sy(self.h / 2),
                    text_anchor="middle",
                    dominant_baseline="central",
                    font_family=_FONT_FAMILY,
                    fill=_LINE_COLOR,
                    font_style="italic" if self.dimension_labels else "normal",
                )
            )

        return g


class RightTriangle(SvgDrawing):
    """A right triangle with legs *base* and *height*.

    The right angle sits at the **lower-left** corner.

    Parameters
    ----------
    base, height : int
        Leg lengths in data units.
    show_dimensions : bool
        Label each side with its numeric length.
    cell_size : int
        Pixel size of one data unit.

    Example::

        svg = (RightTriangle(3, 4)
            .add_pythagorean_squares(
                base_color="skyblue",
                height_color="orange",
                hypotenuse_color="mediumpurple",
            )
            .to_svg()
        )
    """

    def __init__(
        self,
        base: int,
        height: int,
        *,
        show_dimensions: bool = True,
        show_hypotenuse_dimension: bool = False,
        cell_size: int = _CELL,
        dimension_labels: tuple[str, str] | tuple[str, str, str] | None = None,
    ):
        self.base = base
        self.height = height
        self.show_dimensions = show_dimensions
        self.show_hypotenuse_dimension = show_hypotenuse_dimension
        self.cell_size = cell_size
        self.dimension_labels = dimension_labels

        self._squares: dict[str, str | None] | None = None

    def add_pythagorean_squares(
        self,
        *,
        base_color: str | None = "skyblue",
        height_color: str | None = "orange",
        hypotenuse_color: str | None = "mediumpurple",
    ) -> RightTriangle:
        """Draw a square on each side to illustrate the Pythagorean theorem.

        Pass ``None`` for any colour to leave that square undrawn.
        """
        self._squares = dict(
            base=base_color, height=height_color, hypotenuse=hypotenuse_color
        )
        return self

    def to_svg(self) -> str:
        return strip_svg_header(super().to_svg())

    def get_svg_dimensions(self) -> tuple[float, float]:
        cs = self.cell_size
        hyp = math.hypot(self.base, self.height)

        # compute extra space in graph
        extra_left = 0.0
        extra_top = 0.0
        extra_right = 0.0
        extra_bottom = 0.0

        if self._squares:
            # base square extends below
            if self._squares.get("base"):
                extra_bottom = max(extra_bottom, self.base)
            # height square extends to the left
            if self._squares.get("height"):
                extra_left = max(extra_left, self.height)
            # hypotenuse square extends top-right
            if self._squares.get("hypotenuse"):
                # Normal unit vector pointing outward (same as _draw_hyp_square)
                nx = self.height / hyp
                ny = self.base / hyp
                p1 = (self.base, 0)
                p2 = (0, self.height)
                p3 = (p2[0] + hyp * nx, p2[1] + hyp * ny)
                p4 = (p1[0] + hyp * nx, p1[1] + hyp * ny)
                xs = [p1[0], p2[0], p3[0], p4[0]]
                ys = [p1[1], p2[1], p3[1], p4[1]]
                extra_right = max(extra_right, max(xs) - self.base)
                extra_top = max(extra_top, max(ys) - self.height)
                extra_left = max(extra_left, -min(xs)) if min(xs) < 0 else extra_left

        total_w = (
            (extra_left + self.base + extra_right) * cs + 2 * _MARGIN + _DIM_OFFSET
        )
        total_h = (
            (extra_bottom + self.height + extra_top) * cs + 2 * _MARGIN + _DIM_OFFSET
        )
        return total_w, total_h

    def to_group(self, **kwargs) -> draw.Group:
        g = draw.Group()
        cs = self.cell_size
        hyp = math.hypot(self.base, self.height)

        # Work out extra offsets so everything fits
        extra_left = 0.0
        extra_bottom = 0.0
        extra_top = 0.0

        if self._squares:
            if self._squares.get("base"):
                extra_bottom = self.base
            if self._squares.get("height"):
                extra_left = self.height
            if self._squares.get("hypotenuse"):
                nx = self.height / hyp
                ny = self.base / hyp
                p2 = (0, self.height)
                p3 = (p2[0] + hyp * nx, p2[1] + hyp * ny)
                p4 = (self.base + hyp * nx, hyp * ny)
                xs = [self.base, 0, p3[0], p4[0]]
                ys = [0, self.height, p3[1], p4[1]]
                if min(xs) < 0:
                    extra_left = max(extra_left, -min(xs))
                if max(ys) > self.height:
                    extra_top = max(extra_top, max(ys) - self.height)

        ox = _MARGIN + _DIM_OFFSET + extra_left * cs
        oy_base = _MARGIN + extra_top * cs

        def _sx(x: float) -> float:
            return ox + x * cs

        def _sy(y: float) -> float:
            return oy_base + (self.height - y) * cs

        # Resolve dimension label text
        if self.dimension_labels:
            b_label = self.dimension_labels[0]
            h_label = self.dimension_labels[1]
            hyp_label = self.dimension_labels[2] if len(self.dimension_labels) > 2 else "c"
        else:
            b_label = str(self.base)
            h_label = str(self.height)
            hyp_val = math.hypot(self.base, self.height)
            hyp_label = (
                f"{hyp_val:.2f}" if hyp_val != int(hyp_val) else str(int(hyp_val))
            )

        if self._squares:
            # Base square (below the base)
            if self._squares.get("base"):
                self._draw_square_on_segment(
                    g,
                    (0, 0),
                    (self.base, 0),
                    self.base,
                    self._squares["base"],
                    _sx,
                    _sy,
                    cs,
                    side="below",
                    label=b_label,
                )

            # Height square (left of the height)
            if self._squares.get("height"):
                self._draw_square_on_segment(
                    g,
                    (0, 0),
                    (0, self.height),
                    self.height,
                    self._squares["height"],
                    _sx,
                    _sy,
                    cs,
                    side="left",
                    label=h_label,
                )

            # Hypotenuse square (outward from the hypotenuse)
            if self._squares.get("hypotenuse"):
                self._draw_hyp_square(
                    g, _sx, _sy, cs, hyp, self._squares["hypotenuse"],
                    label=hyp_label,
                )

        g.append(
            draw.Lines(
                _sx(0),
                _sy(0),
                _sx(self.base),
                _sy(0),
                _sx(0),
                _sy(self.height),
                close=True,
                fill="none",
                stroke=_LINE_COLOR,
                stroke_width=_LINE_WIDTH * 1.2,
            )
        )

        s = _RIGHT_ANGLE_SIZE
        g.append(
            draw.Lines(
                _sx(s),
                _sy(0),
                _sx(s),
                _sy(s),
                _sx(0),
                _sy(s),
                close=False,
                fill="none",
                stroke=_LINE_COLOR,
                stroke_width=_LINE_WIDTH,
            )
        )

        if self.show_dimensions:
            is_custom = self.dimension_labels is not None
            font_style = "italic" if is_custom else "normal"
            # Base
            g.append(
                draw.Text(
                    b_label,
                    _FONT_SIZE,
                    _sx(self.base / 2),
                    _sy(0) + _DIM_OFFSET,
                    text_anchor="middle",
                    dominant_baseline="auto",
                    font_family=_FONT_FAMILY,
                    fill=_LINE_COLOR,
                    font_style=font_style,
                )
            )
            # Height
            g.append(
                draw.Text(
                    h_label,
                    _FONT_SIZE,
                    _sx(0) - _DIM_OFFSET,
                    _sy(self.height / 2),
                    text_anchor="middle",
                    dominant_baseline="central",
                    font_family=_FONT_FAMILY,
                    fill=_LINE_COLOR,
                    font_style=font_style,
                )
            )
            # Hypotenuse (rotated along the diagonal)
            if self.show_hypotenuse_dimension:
                mid_x = _sx(self.base / 2)
                mid_y = _sy(self.height / 2)
                angle = -math.degrees(math.atan2(self.height * cs, self.base * cs))
                g.append(
                    draw.Text(
                        hyp_label,
                        _FONT_SIZE,
                        mid_x + _DIM_OFFSET * 0.7 * math.sin(math.radians(-angle)),
                        mid_y + _DIM_OFFSET * 0.7 * math.cos(math.radians(-angle)),
                        text_anchor="middle",
                        dominant_baseline="central",
                        font_family=_FONT_FAMILY,
                        fill=_LINE_COLOR,
                        font_style=font_style,
                        transform=f"rotate({angle},{mid_x},{mid_y})",
                    )
                )

        return g

    def _draw_square_on_segment(
        self,
        g: draw.Group,
        p0: tuple[float, float],
        p1: tuple[float, float],
        side_len: float,
        color: str,
        sx,
        sy,
        cs,
        side: str,
        label: str | None = None,
    ):
        """Draw a filled square with grid on one side of a segment."""
        lbl = label if label is not None else str(int(side_len))
        if side == "below":
            # Square extends downward from the base
            x0, y0 = sx(p0[0]), sy(p0[1])
            g.append(
                draw.Rectangle(
                    x0,
                    y0,
                    side_len * cs,
                    side_len * cs,
                    fill=color,
                    opacity=_SQUARE_OPACITY,
                    stroke=color,
                    stroke_opacity=_SQUARE_BORDER_OPACITY,
                    stroke_width=_LINE_WIDTH,
                )
            )
            # Grid
            for i in range(1, int(side_len)):
                g.append(
                    draw.Line(
                        x0 + i * cs,
                        y0,
                        x0 + i * cs,
                        y0 + side_len * cs,
                        stroke=_GRID_COLOR,
                        stroke_width=_GRID_WIDTH,
                    )
                )
                g.append(
                    draw.Line(
                        x0,
                        y0 + i * cs,
                        x0 + side_len * cs,
                        y0 + i * cs,
                        stroke=_GRID_COLOR,
                        stroke_width=_GRID_WIDTH,
                    )
                )
            # Area label
            g.append(
                draw.Text(
                    f"{lbl}² = {int(side_len**2)}",
                    _FONT_SIZE,
                    x0 + side_len * cs / 2,
                    y0 + side_len * cs / 2,
                    text_anchor="middle",
                    dominant_baseline="central",
                    font_family=_FONT_FAMILY,
                    fill=color,
                    font_weight="bold",
                )
            )

        elif side == "left":
            # Square extends to the left of the height segment
            x0, y0 = sx(p0[0]) - side_len * cs, sy(p1[1])
            g.append(
                draw.Rectangle(
                    x0,
                    y0,
                    side_len * cs,
                    side_len * cs,
                    fill=color,
                    opacity=_SQUARE_OPACITY,
                    stroke=color,
                    stroke_opacity=_SQUARE_BORDER_OPACITY,
                    stroke_width=_LINE_WIDTH,
                )
            )
            # Grid
            for i in range(1, int(side_len)):
                g.append(
                    draw.Line(
                        x0 + i * cs,
                        y0,
                        x0 + i * cs,
                        y0 + side_len * cs,
                        stroke=_GRID_COLOR,
                        stroke_width=_GRID_WIDTH,
                    )
                )
                g.append(
                    draw.Line(
                        x0,
                        y0 + i * cs,
                        x0 + side_len * cs,
                        y0 + i * cs,
                        stroke=_GRID_COLOR,
                        stroke_width=_GRID_WIDTH,
                    )
                )
            # Area label
            g.append(
                draw.Text(
                    f"{lbl}² = {int(side_len**2)}",
                    _FONT_SIZE,
                    x0 + side_len * cs / 2,
                    y0 + side_len * cs / 2,
                    text_anchor="middle",
                    dominant_baseline="central",
                    font_family=_FONT_FAMILY,
                    fill=color,
                    font_weight="bold",
                )
            )

    def _draw_hyp_square(self, g, sx, sy, cs, hyp, color, *, label: str = "c"):
        """Draw the tilted square on the hypotenuse."""
        # Unit normal pointing outward (away from the right angle at origin)
        nx = self.height / hyp
        ny = self.base / hyp

        # The hypotenuse goes from (base, 0) to (0, height).
        # The outward square has corners:
        p1 = (self.base, 0)
        p2 = (0, self.height)
        p3 = (p2[0] + hyp * nx, p2[1] + hyp * ny)
        p4 = (p1[0] + hyp * nx, p1[1] + hyp * ny)

        g.append(
            draw.Lines(
                sx(p1[0]),
                sy(p1[1]),
                sx(p2[0]),
                sy(p2[1]),
                sx(p3[0]),
                sy(p3[1]),
                sx(p4[0]),
                sy(p4[1]),
                close=True,
                fill=color,
                opacity=_SQUARE_OPACITY,
                stroke=color,
                stroke_opacity=_SQUARE_BORDER_OPACITY,
                stroke_width=_LINE_WIDTH,
            )
        )

        # Grid lines along hypotenuse direction
        dx_h = (p2[0] - p1[0]) / hyp  # unit vector along hypotenuse
        dy_h = (p2[1] - p1[1]) / hyp
        n_lines = int(round(hyp))
        for i in range(1, n_lines):
            frac = i / hyp
            # Lines parallel to hypotenuse
            a = (p1[0] + frac * (p4[0] - p1[0]), p1[1] + frac * (p4[1] - p1[1]))
            b = (p2[0] + frac * (p3[0] - p2[0]), p2[1] + frac * (p3[1] - p2[1]))
            g.append(
                draw.Line(
                    sx(a[0]),
                    sy(a[1]),
                    sx(b[0]),
                    sy(b[1]),
                    stroke=_GRID_COLOR,
                    stroke_width=_GRID_WIDTH,
                )
            )
            # Lines perpendicular to hypotenuse
            c = (p1[0] + frac * (p2[0] - p1[0]), p1[1] + frac * (p2[1] - p1[1]))
            d = (p4[0] + frac * (p3[0] - p4[0]), p4[1] + frac * (p3[1] - p4[1]))
            g.append(
                draw.Line(
                    sx(c[0]),
                    sy(c[1]),
                    sx(d[0]),
                    sy(d[1]),
                    stroke=_GRID_COLOR,
                    stroke_width=_GRID_WIDTH,
                )
            )

        # Area label in the centre of the tilted square
        cx = (p1[0] + p2[0] + p3[0] + p4[0]) / 4
        cy = (p1[1] + p2[1] + p3[1] + p4[1]) / 4
        hyp_sq = hyp**2
        sq_label = (
            f"{label}² = {hyp_sq:.0f}"
            if abs(hyp_sq - round(hyp_sq)) < 0.01
            else f"{label}² ≈ {hyp_sq:.1f}"
        )
        g.append(
            draw.Text(
                sq_label,
                _FONT_SIZE,
                sx(cx),
                sy(cy),
                text_anchor="middle",
                dominant_baseline="central",
                font_family=_FONT_FAMILY,
                fill=color,
                font_weight="bold",
            )
        )


# wrappers


def draw_rectangle(
    width: int,
    height: int,
    *,
    show_dimensions: bool = True,
    show_grid: bool = True,
    area_color: str | None = None,
    cell_highlights: dict[tuple[int, int], str] | None = None,
    right_angles: bool = False,
    diagonal: tuple[str, str] | None = None,
    cell_size: int = _CELL,
    dimension_labels: tuple[str, str] | None = None,
) -> str:
    """Draw a rectangle and return an SVG string.

    Parameters
    ----------
    width, height : int
        Rectangle dimensions.
    show_dimensions : bool
        Label the sides.
    show_grid : bool
        Draw the 1×1 grid.
    area_color : str | None
        Background fill colour.
    cell_highlights : dict | None
        ``{(col, row): colour}`` to colour specific cells.
    right_angles : bool
        Draw right-angle marks in every corner.
    diagonal : tuple[str, str] | None
        ``(colour_below, colour_above)`` to draw a diagonal.
    cell_size : int
        Pixels per data unit.
    """
    rect = Rectangle(
        width,
        height,
        show_dimensions=show_dimensions,
        show_grid=show_grid,
        area_color=area_color,
        cell_size=cell_size,
        dimension_labels=dimension_labels,
    )
    if cell_highlights:
        rect.add_cell_highlights(cell_highlights)
    if right_angles:
        rect.add_right_angles()
    if diagonal:
        rect.add_diagonal(*diagonal)
    return rect.to_svg()


def draw_right_triangle(
    base: int,
    height: int,
    *,
    show_dimensions: bool = True,
    show_hypotenuse_dimension: bool = False,
    pythagorean_squares: bool = False,
    base_color: str | None = "skyblue",
    height_color: str | None = "orange",
    hypotenuse_color: str | None = "mediumpurple",
    cell_size: int = _CELL,
    dimension_labels: tuple[str, str] | tuple[str, str, str] | None = None,
) -> str:
    """Draw a right triangle and return an SVG string.

    Parameters
    ----------
    base, height : int
        Leg lengths.
    show_dimensions : bool
        Label the two legs.
    show_hypotenuse_dimension : bool
        Label the hypotenuse as well.
    pythagorean_squares : bool
        Draw a square on each side.
    base_color, height_color, hypotenuse_color : str | None
        Colours for the Pythagorean squares.
    cell_size : int
        Pixels per data unit.
    """
    tri = RightTriangle(
        base,
        height,
        show_dimensions=show_dimensions,
        show_hypotenuse_dimension=show_hypotenuse_dimension,
        cell_size=cell_size,
        dimension_labels=dimension_labels,
    )
    if pythagorean_squares:
        tri.add_pythagorean_squares(
            base_color=base_color,
            height_color=height_color,
            hypotenuse_color=hypotenuse_color,
        )
    return tri.to_svg()
