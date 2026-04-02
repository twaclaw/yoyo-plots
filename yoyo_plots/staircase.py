"""
Staircase diagrams.

Draws a side-view staircase profile where each step has width = height = 1
data unit.  Supports optional labels, icons, coloured segments and arcs.
"""

from __future__ import annotations

import os

import plotly.graph_objects as go

from .common import hidden_axis, svg_to_data_uri, resolve_user_path

DEFAULT_LINE_WIDTH = 2.0
DEFAULT_LINE_COLOR = "black"
DEFAULT_FONT_SIZE = 14
DEFAULT_FONT_COLOR = "black"
DEFAULT_ICON_SIZE = 0.6
DEFAULT_SEGMENT_WIDTH_MULT = 3.0
DEFAULT_PIXELS_PER_UNIT = 80
DEFAULT_MIN_PX = 200

_PAD_X = 1.2
_PAD_Y_BOTTOM = 0.8
_PAD_Y_TOP = 1.0
_LABEL_Y_OFFSET = 0.12
_ARC_HEIGHT_FACTOR = 1.2
_ARC_PEAK_Y_FACTOR = 0.75
_ARROW_TAIL_OFFSET = 0.15
_MARGIN_PX = 5


def _expand_all_key(mapping: dict, valid_keys: range) -> dict:
    """Expand the special ``"all"`` key across *valid_keys*, then overlay specifics."""
    result = {}
    if "all" in mapping:
        base = mapping["all"]
        for k in valid_keys:
            result[k] = base
    for k, v in mapping.items():
        if k != "all":
            result[k] = v
    return result


def _resolve_icon_source(path: str) -> str:
    resolved = resolve_user_path(path)
    if os.path.exists(resolved) and resolved.lower().endswith(".svg"):
        return svg_to_data_uri(resolved)
    return resolved


class Staircase:
    """A Plotly-based staircase profile (side view).

    Parameters
    ----------
    nsteps : int
        Number of steps (0 = floor, 1 … *nsteps* = stairs).
    label_steps : bool
        If *True*, draw the step number under each tread.
    line_width, line_color, font_size, font_color, pixels_per_unit :
        Visual tweaks — see module-level defaults.

    Decorations are added via fluent ``add_*`` methods::

        fig = (Staircase(5)
            .add_icons("./alien.svg", icon_size=0.6)
            .add_segments({0: "red", 2: "blue"})
            .add_arcs({"all": {"len": 1, "color": "green", "text": "+1"}})
            .to_figure()
        )
    """

    def __init__(
        self,
        nsteps: int = 5,
        *,
        line_width: float = DEFAULT_LINE_WIDTH,
        line_color: str = DEFAULT_LINE_COLOR,
        font_size: int = DEFAULT_FONT_SIZE,
        font_color: str = DEFAULT_FONT_COLOR,
        label_steps: bool = True,
        pixels_per_unit: int = DEFAULT_PIXELS_PER_UNIT,
    ):
        self.nsteps = nsteps
        self.line_width = line_width
        self.line_color = line_color
        self.font_size = font_size
        self.font_color = font_color
        self.label_steps = label_steps
        self.pixels_per_unit = pixels_per_unit

        self._icons: str | dict[int, str] | None = None
        self._icon_size: float = DEFAULT_ICON_SIZE
        self._segments: dict[int | str, str] | None = None
        self._segment_width: float = DEFAULT_SEGMENT_WIDTH_MULT
        self._arcs: dict[int | str, dict] | None = None

    def add_icons(
        self,
        icons: str | dict[int, str],
        icon_size: float = DEFAULT_ICON_SIZE,
    ) -> Staircase:
        """Add icons on top of step treads.

        Parameters
        ----------
        icons : str | dict[int, str]
            A single SVG path applied to every step, or a dict mapping
            step index → SVG path.
        icon_size : float
            Size of each icon in data units.
        """
        self._icons = icons
        self._icon_size = icon_size
        return self

    def add_segments(
        self,
        segments: dict[int | str, str],
        segment_width: float = DEFAULT_SEGMENT_WIDTH_MULT,
    ) -> Staircase:
        """Colour the staircase path between consecutive step midpoints.

        Parameters
        ----------
        segments : dict[int | str, str]
            Maps step index (or ``"all"``) → colour.  Colours the path
            from the midpoint of step *s* to the midpoint of step *s + 1*.
        segment_width : float
            Line-width multiplier relative to ``self.line_width``.
        """
        self._segments = segments
        self._segment_width = segment_width
        return self

    def add_arcs(
        self,
        arcs: dict[int | str, dict],
    ) -> Staircase:
        """Draw Bézier arcs between step midpoints.

        Parameters
        ----------
        arcs : dict[int | str, dict]
            Maps step index (or ``"all"``) → ``{"len": int, "color": str,
            "text": str | None}``.
        """
        self._arcs = arcs
        return self

    @property
    def _step_range(self) -> range:
        return range(self.nsteps + 1)

    @staticmethod
    def _step_mid(i: int) -> tuple[float, float]:
        """Midpoint of the tread at step *i*."""
        return (i + 0.5, float(i))

    def _draw_outline(self, fig: go.Figure) -> None:
        line = dict(color=self.line_color, width=self.line_width)
        # Treads
        for i in self._step_range:
            fig.add_shape(
                type="line", x0=i, y0=i, x1=i + 1, y1=i, line=line, layer="above"
            )
        # Risers
        for i in range(1, self.nsteps + 1):
            fig.add_shape(
                type="line", x0=i, y0=i - 1, x1=i, y1=i, line=line, layer="above"
            )

    def _draw_labels(self, fig: go.Figure) -> None:
        for i in self._step_range:
            mx, my = self._step_mid(i)
            fig.add_annotation(
                x=mx,
                y=my - _LABEL_Y_OFFSET,
                text=str(i),
                showarrow=False,
                font=dict(size=self.font_size, color=self.font_color),
                xanchor="center",
                yanchor="top",
                xref="x",
                yref="y",
            )

    def _draw_icons(self, fig: go.Figure) -> None:
        if self._icons is None:
            return
        for i in self._step_range:
            if isinstance(self._icons, dict):
                if i not in self._icons:
                    continue
                path = self._icons[i]
            else:
                path = self._icons

            mx, my = self._step_mid(i)
            fig.add_layout_image(
                source=_resolve_icon_source(path),
                x=mx,
                y=my,
                sizex=self._icon_size,
                sizey=self._icon_size,
                xanchor="center",
                yanchor="bottom",
                xref="x",
                yref="y",
                layer="above",
                sizing="contain",
            )

    def _draw_segments(self, fig: go.Figure) -> None:
        if not self._segments:
            return
        sw = self.line_width * self._segment_width
        valid = range(self.nsteps)  # segment from step s to s+1
        for s, color in _expand_all_key(self._segments, valid).items():
            if s not in self._step_range or (s + 1) not in self._step_range:
                continue
            mx0, _ = self._step_mid(s)
            mx1, _ = self._step_mid(s + 1)
            seg_line = dict(color=color, width=sw)
            # Right half of tread s → riser s+1 → left half of tread s+1
            fig.add_shape(
                type="line", x0=mx0, y0=s, x1=s + 1, y1=s, line=seg_line, layer="above"
            )
            fig.add_shape(
                type="line",
                x0=s + 1,
                y0=s,
                x1=s + 1,
                y1=s + 1,
                line=seg_line,
                layer="above",
            )
            fig.add_shape(
                type="line",
                x0=s + 1,
                y0=s + 1,
                x1=mx1,
                y1=s + 1,
                line=seg_line,
                layer="above",
            )

    def _draw_arcs(self, fig: go.Figure) -> None:
        if not self._arcs:
            return
        valid = range(self.nsteps)
        for start, cfg in _expand_all_key(self._arcs, valid).items():
            if not isinstance(cfg, dict):
                continue
            jump_len = int(cfg.get("len", 1))
            if jump_len == 0:
                continue
            end = start + jump_len
            if start not in self._step_range or end not in self._step_range:
                continue

            arc_color = cfg.get("color", "black")
            x0, y0 = self._step_mid(start)
            x1, y1 = self._step_mid(end)

            # Cubic Bézier with vertical control points
            h = jump_len * _ARC_HEIGHT_FACTOR
            path = f"M {x0},{y0} C {x0},{y0 + h} {x1},{y1 + h} {x1},{y1}"
            fig.add_shape(
                type="path",
                path=path,
                line=dict(color=arc_color, width=self.line_width),
                layer="above",
            )

            # Arrowhead (tangent at t=1 points straight down)
            fig.add_annotation(
                x=x1,
                y=y1,
                ax=x1,
                ay=y1 + _ARROW_TAIL_OFFSET,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                text="",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.2,
                arrowwidth=self.line_width,
                arrowcolor=arc_color,
                standoff=0,
            )

            arc_text = cfg.get("text")
            if arc_text is not None:
                peak_x = 0.5 * (x0 + x1)
                peak_y = 0.5 * (y0 + y1) + _ARC_PEAK_Y_FACTOR * h
                fig.add_annotation(
                    x=peak_x,
                    y=peak_y,
                    text=str(arc_text),
                    showarrow=False,
                    font=dict(size=self.font_size, color=arc_color),
                    xanchor="center",
                    yanchor="bottom",
                    xref="x",
                    yref="y",
                )

    def to_figure(self) -> go.Figure:
        """Build and return the Plotly ``Figure`` (no side-effects)."""
        fig = go.Figure()

        self._draw_outline(fig)
        if self.label_steps:
            self._draw_labels(fig)
        self._draw_icons(fig)
        self._draw_segments(fig)
        self._draw_arcs(fig)

        n = self.nsteps
        ppu = self.pixels_per_unit
        fig.update_layout(
            xaxis=hidden_axis(
                range=[-_PAD_X, n + 1 + _PAD_X],
                fixedrange=True,
                scaleanchor="y",
                scaleratio=1,
            ),
            yaxis=hidden_axis(
                range=[-_PAD_Y_BOTTOM, n + _PAD_Y_TOP],
                fixedrange=True,
            ),
            plot_bgcolor="white",
            margin=dict(l=_MARGIN_PX, r=_MARGIN_PX, t=_MARGIN_PX, b=_MARGIN_PX),
            width=max(DEFAULT_MIN_PX, int((n + 1 + 2 * _PAD_X) * ppu)),
            height=max(DEFAULT_MIN_PX, int((n + _PAD_Y_BOTTOM + _PAD_Y_TOP) * ppu)),
            dragmode="pan",
        )
        return fig


def draw_staircase(
    nsteps: int = 5,
    line_width: float = DEFAULT_LINE_WIDTH,
    line_color: str = DEFAULT_LINE_COLOR,
    font_size: int = DEFAULT_FONT_SIZE,
    font_color: str = DEFAULT_FONT_COLOR,
    arcs: dict | None = None,
    label_steps: bool = True,
    icons: str | dict[int, str] | None = None,
    icon_size: float = DEFAULT_ICON_SIZE,
    segments: dict | None = None,
    segment_width: float = DEFAULT_SEGMENT_WIDTH_MULT,
    save_path: str | None = None,
) -> go.Figure:
    """Convenience wrapper around :class:`Staircase`."""
    s = Staircase(
        nsteps=nsteps,
        line_width=line_width,
        line_color=line_color,
        font_size=font_size,
        font_color=font_color,
        label_steps=label_steps,
    )
    if icons is not None:
        s.add_icons(icons, icon_size=icon_size)
    if segments is not None:
        s.add_segments(segments, segment_width=segment_width)
    if arcs is not None:
        s.add_arcs(arcs)

    fig = s.to_figure()
    if save_path:
        fig.write_image(save_path)

    return fig
