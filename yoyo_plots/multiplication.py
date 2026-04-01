"""
Operation / group tables.

Given a group ⟨G, *⟩ this module can display its Cayley table, or more
generally any operation table (addition, multiplication, …).
"""

from __future__ import annotations

from collections.abc import Callable

import plotly.graph_objects as go

from .common import hidden_axis, strip_svg_header

# ── Defaults & constants ──────────────────────────────────────────────────
DEFAULT_FONT_FAMILY = "Comic Sans MS"
DEFAULT_FONT_SIZE = 22
DEFAULT_FONT_COLOR = "black"
DEFAULT_HEADER_COLOR = "#d5d8dc"
DEFAULT_GRID_COLOR = "#808080"
DEFAULT_LINE_WIDTH = 1.5
DEFAULT_CELL_SIZE = 1.0
DEFAULT_PIXELS_PER_UNIT = 55

_VIEW_MARGIN = 0.05
_MARGIN_PX = 5


class OperationTable:
    """A Plotly-based operation table (multiplication, addition, group, …).

    Parameters
    ----------
    nrows, ncols : int
        Number of data rows / columns.
    operation : Callable[[int, int], int | str]
        Binary operation applied to ``(row, col)`` to produce the cell value.
    operation_name : str
        Symbol shown in the top-left header cell.
    show_upper : bool
        If *True*, only upper-triangular cells (``col >= row``) show values.
    rows, cols : dict[int, str] | None
        Row / column index → highlight fill color.
    elements : dict[tuple[int, int], str] | None
        ``(row, col)`` → highlight fill color.  Takes precedence over
        *rows* / *cols*.
    only_rows : list[int] | None
        If set, only these rows display values; others are blank & white.
    font_color, font_size, font_family, cell_size, header_color,
    grid_color, line_width, pixels_per_unit :
        Visual tweaks – see defaults above.
    """

    def __init__(
        self,
        nrows: int = 10,
        ncols: int = 10,
        operation: Callable[[int, int], int | str] = lambda r, c: r * c,
        operation_name: str = "×",
        show_upper: bool = True,
        rows: dict[int, str] | None = None,
        cols: dict[int, str] | None = None,
        elements: dict[tuple[int, int], str] | None = None,
        font_color: str = DEFAULT_FONT_COLOR,
        font_size: int = DEFAULT_FONT_SIZE,
        font_family: str = DEFAULT_FONT_FAMILY,
        cell_size: float = DEFAULT_CELL_SIZE,
        header_color: str = DEFAULT_HEADER_COLOR,
        grid_color: str = DEFAULT_GRID_COLOR,
        line_width: float = DEFAULT_LINE_WIDTH,
        pixels_per_unit: int = DEFAULT_PIXELS_PER_UNIT,
        only_rows: list[int] | None = None,
    ):
        self.nrows = nrows
        self.ncols = ncols
        self.operation = operation
        self.operation_name = operation_name
        self.show_upper = show_upper
        self.rows = rows or {}
        self.cols = cols or {}
        self.elements = elements or {}
        self.font_color = font_color
        self.font_size = font_size
        self.font_family = font_family
        self.cell_size = cell_size
        self.header_color = header_color
        self.grid_color = grid_color
        self.line_width = line_width
        self.pixels_per_unit = pixels_per_unit
        self.only_rows = only_rows

    # ── geometry helpers ──────────────────────────────────────────────────

    def _cell_rect(self, gc: int, gr: int):
        """Return ``(x0, y0, x1, y1)`` for grid cell at column *gc*, row *gr*."""
        s = self.cell_size
        x0 = gc * s
        x1 = x0 + s
        y1 = -gr * s
        y0 = y1 - s
        return x0, y0, x1, y1

    # ── figure building ───────────────────────────────────────────────────

    def _add_cell(self, fig: go.Figure, gc: int, gr: int, fill: str, text: str,
                  text_color: str | None = None):
        x0, y0, x1, y1 = self._cell_rect(gc, gr)
        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            fillcolor=fill,
            line=dict(color=self.grid_color, width=self.line_width),
            layer="below",
        )
        if text:
            fig.add_annotation(
                x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                text=text, showarrow=False,
                font=dict(
                    family=self.font_family,
                    size=self.font_size,
                    color=text_color or self.font_color,
                ),
                xanchor="center", yanchor="middle",
                xref="x", yref="y",
            )

    def _cell_bg(self, r: int, c: int) -> str:
        """Resolve highlight colour for a data cell (element > row > col > white)."""
        return self.elements.get((r, c)) or self.rows.get(r) or self.cols.get(c) or "white"

    def to_figure(self) -> go.Figure:
        """Build and return the Plotly ``Figure`` (no side-effects)."""
        fig = go.Figure()

        total_cols = self.ncols + 1
        total_rows = self.nrows + 1

        # Header cells
        self._add_cell(fig, 0, 0, self.header_color, self.operation_name)
        for c in range(self.ncols):
            self._add_cell(fig, c + 1, 0, self.header_color, str(c))
        for r in range(self.nrows):
            self._add_cell(fig, 0, r + 1, self.header_color, str(r))

        # Data cells
        for r in range(self.nrows):
            for c in range(self.ncols):
                if self.only_rows and r not in self.only_rows:
                    self._add_cell(fig, c + 1, r + 1, "white", "")
                    continue

                bg = self._cell_bg(r, c)
                show_value = (not self.show_upper) or (c >= r)
                text = str(self.operation(r, c)) if show_value else ""
                self._add_cell(fig, c + 1, r + 1, bg, text)

        # Layout
        s = self.cell_size
        fig_width = int(total_cols * s * self.pixels_per_unit) + 2 * _MARGIN_PX
        fig_height = int(total_rows * s * self.pixels_per_unit) + 2 * _MARGIN_PX

        fig.update_layout(
            xaxis=hidden_axis(
                range=[-_VIEW_MARGIN, total_cols * s + _VIEW_MARGIN],
                fixedrange=True,
            ),
            yaxis=hidden_axis(
                range=[-total_rows * s - _VIEW_MARGIN, _VIEW_MARGIN],
                fixedrange=True,
                scaleanchor="x",
                scaleratio=1,
            ),
            plot_bgcolor="white",
            margin=dict(l=_MARGIN_PX, r=_MARGIN_PX, t=_MARGIN_PX, b=_MARGIN_PX),
            width=fig_width,
            height=fig_height,
            dragmode="pan",
        )
        return fig

    def to_svg(self) -> str:
        """Render the table to an SVG string."""
        fig = self.to_figure()
        return strip_svg_header(fig.to_image(format="svg").decode("utf-8"))



def draw_operation_table(
    nrows: int = 10,
    ncols: int = 10,
    operation: Callable[[int, int], int | str] = lambda r, c: r * c,
    operation_name: str = "×",
    show_upper: bool = True,
    rows: dict[int, str] | None = None,
    cols: dict[int, str] | None = None,
    elements: dict[tuple[int, int], str] | None = None,
    font_color: str = DEFAULT_FONT_COLOR,
    font_size: int = DEFAULT_FONT_SIZE,
    font_family: str = DEFAULT_FONT_FAMILY,
    cell_size: float = DEFAULT_CELL_SIZE,
    header_color: str = DEFAULT_HEADER_COLOR,
    grid_color: str = DEFAULT_GRID_COLOR,
    line_width: float = DEFAULT_LINE_WIDTH,
    pixels_per_unit: int = DEFAULT_PIXELS_PER_UNIT,
    only_rows: list[int] | None = None,
) -> str:
    """Convenience wrapper around :class:`OperationTable`.

    """
    return OperationTable(
        nrows=nrows, ncols=ncols, operation=operation,
        operation_name=operation_name, show_upper=show_upper,
        rows=rows, cols=cols, elements=elements,
        font_color=font_color, font_size=font_size,
        font_family=font_family, cell_size=cell_size,
        header_color=header_color, grid_color=grid_color,
        line_width=line_width, pixels_per_unit=pixels_per_unit,
        only_rows=only_rows,
    ).to_svg()
