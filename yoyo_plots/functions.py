"""
functions.py – Plot a mathematical function with optional Riemann / Lebesgue rectangles.
"""

from __future__ import annotations

import io

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from typing import Sequence

from .common import strip_svg_header


class FunctionPlot:
    """A matplotlib-based function plot drawn in *xkcd* style.

    The constructor draws the curve and sets up the axes.

    svg = (FunctionPlot(x, y, xlabel="x", ylabel="f(x)")
            .add_vertical_rectangles(rects)
            .to_svg())
    """

    def __init__(
        self,
        x: Sequence[float],
        y: Sequence[float],
        *,
        xlabel: str = "x",
        ylabel: str = "y",
        title: str | None = None,
        font_size: int = 14,
        label_font_size: int | None = None,
        title_font_size: int | None = None,
        tick_font_size: int | None = None,
        line_color: str = "black",
        line_width: float = 2.5,
        figsize: tuple[float, float] = (8, 5),
        show_grid: bool = False,
        only_integers: bool = True,
        # rectangle styling defaults
        rect_alpha: float = 0.45,
        rect_edge_color: str = "black",
        rect_edge_width: float = 1.0,
    ):
        self._x = np.asarray(x, dtype=float)
        self._y = np.asarray(y, dtype=float)

        # Font sizes
        self._lbl_fs = label_font_size if label_font_size is not None else font_size
        self._ttl_fs = title_font_size if title_font_size is not None else font_size + 2
        self._tck_fs = (
            tick_font_size if tick_font_size is not None else max(8, font_size - 2)
        )

        # rectangle defaults
        self.only_integers = only_integers
        self.rect_alpha = rect_alpha
        self.rect_edge_color = rect_edge_color
        self.rect_edge_width = rect_edge_width

        with plt.xkcd():
            self._fig, self._ax = plt.subplots(figsize=figsize)
            self._ax.plot(
                self._x,
                self._y,
                color=line_color,
                linewidth=line_width,
                zorder=2,
            )
            self._ax.set_xlabel(xlabel, fontsize=self._lbl_fs)
            self._ax.set_ylabel(ylabel, fontsize=self._lbl_fs)
            if title:
                self._ax.set_title(title, fontsize=self._ttl_fs)
            self._ax.tick_params(labelsize=self._tck_fs)
            if show_grid:
                self._ax.grid(True, linestyle="--", alpha=0.5)
            # Flush x-axis to data range
            self._ax.set_xlim(self._x.min(), self._x.max())
            # Y-axis: start at 0 (or below if data goes negative), headroom on top
            y_data_lo = float(self._y.min())
            y_data_hi = float(self._y.max())
            y_lo = min(0, y_data_lo)
            self._ax.set_ylim(y_lo, y_data_hi + (y_data_hi - y_lo) * 0.05)

            # Integer ticks on both axes
            self._ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
            self._ax.yaxis.set_major_locator(mticker.MultipleLocator(1))

        plt.close(self._fig)

    # methods to add stuff

    def add_vertical_rectangles(self, rectangles: list[dict]) -> "FunctionPlot":
        """Add Riemann-style vertical rectangles.

        Each dict must have keys:
          - ``"start"``      : x coordinate of the left edge
          - ``"end"``        : x coordinate of the right edge
          - ``"color"``      : fill color
          - ``"show_label"`` : (optional, bool) draw a "width×height" label
        """
        for rect in rectangles:
            r_start = float(rect["start"])
            r_end = float(rect["end"])
            r_color = rect["color"]
            mid = 0.5 * (r_start + r_end)
            r_height = float(np.interp(mid, self._x, self._y))
            r_width = r_end - r_start
            if self.only_integers:
                r_height = float(round(r_height))
                r_width = float(round(r_width))

            if r_height >= 0:
                self._ax.add_patch(
                    mpatches.Rectangle(
                        (r_start, 0),
                        r_width,
                        r_height,
                        facecolor=r_color,
                        alpha=self.rect_alpha,
                        edgecolor=self.rect_edge_color,
                        linewidth=self.rect_edge_width,
                        zorder=1,
                    )
                )
                if rect.get("show_label", False) and r_height > 0:
                    w_str, h_str = self._fmt_dims(r_width, r_height)
                    self._ax.text(
                        mid,
                        r_height / 2,
                        f"{w_str}\u00d7{h_str}",
                        ha="center",
                        va="center",
                        fontsize=max(7, self._tck_fs - 1),
                        zorder=3,
                    )
            else:
                self._ax.add_patch(
                    mpatches.Rectangle(
                        (r_start, r_height),
                        r_width,
                        -r_height,
                        facecolor=r_color,
                        alpha=self.rect_alpha,
                        edgecolor=self.rect_edge_color,
                        linewidth=self.rect_edge_width,
                        zorder=1,
                    )
                )
        return self

    def add_horizontal_rectangles(self, rectangles: list[dict]) -> "FunctionPlot":
        """Add Lebesgue-style horizontal rectangles.

        Each dict must have keys:
          - ``"start"``      : y coordinate of the bottom edge
          - ``"end"``        : y coordinate of the top edge
          - ``"color"``      : fill color
          - ``"show_label"`` : (optional, bool) draw a "measure×height" label
        """
        for rect in rectangles:
            y_lo = float(rect["start"])
            y_hi = float(rect["end"])
            r_color = rect["color"]
            strip_h = y_hi - y_lo
            if self.only_integers:
                strip_h = float(round(strip_h))

            above = self._y >= y_lo

            # Find contiguous runs
            diff = np.diff(above.astype(int))
            starts = np.where(diff == 1)[0] + 1
            ends = np.where(diff == -1)[0] + 1
            if above[0]:
                starts = np.concatenate(([0], starts))
            if above[-1]:
                ends = np.concatenate((ends, [len(above)]))

            total_measure = 0.0
            segments_list: list[tuple[float, float]] = []
            for s_idx, e_idx in zip(starts, ends):
                x_left = float(self._x[s_idx])
                x_right = float(self._x[min(e_idx, len(self._x) - 1)])
                seg_w = x_right - x_left
                if seg_w <= 0:
                    continue
                total_measure += seg_w
                segments_list.append((x_left, seg_w))
                self._ax.add_patch(
                    mpatches.Rectangle(
                        (x_left, y_lo),
                        seg_w,
                        strip_h,
                        facecolor=r_color,
                        alpha=self.rect_alpha,
                        edgecolor=self.rect_edge_color,
                        linewidth=self.rect_edge_width,
                        zorder=1,
                    )
                )

            if self.only_integers:
                total_measure = float(round(total_measure))

            # Place a single label in the widest segment
            if rect.get("show_label", False) and segments_list:
                m_str, h_str = self._fmt_dims(total_measure, strip_h)
                best_x, best_w = max(segments_list, key=lambda t: t[1])
                self._ax.text(
                    best_x + best_w / 2,
                    y_lo + strip_h / 2,
                    f"{m_str}\u00d7{h_str}",
                    ha="center",
                    va="center",
                    fontsize=max(7, self._tck_fs - 1),
                    zorder=3,
                )
        return self

    def add_markers(self, markers: dict[float, dict]) -> "FunctionPlot":
        """Place labelled markers on the curve.

        Parameters
        ----------
        markers : dict
            ``{x_value: opts}`` where *opts* is a dict with keys:

            * ``"color"``      marker colour (required)
            * ``"label"``      annotation text (default ``None``)
            * ``"help_line"``  draw a dotted line to the y-axis
              (default ``False``)

        Example::

            plot.add_markers({
                2: {"color": "red", "label": "peak", "help_line": True},
                5: {"color": "blue"},
            })
        """
        for x_val, opts in markers.items():
            y_val = float(np.interp(x_val, self._x, self._y))
            color = opts["color"]
            label = opts.get("label")
            help_line = opts.get("help_line", False)

            # marker dot
            self._ax.plot(
                x_val, y_val,
                "o",
                color=color,
                markersize=8,
                zorder=4,
            )

            # dotted help lines to the axis spines
            if help_line:
                x_spine = self._ax.get_xlim()[0]
                y_spine = self._ax.get_ylim()[0]
                self._ax.plot(
                    [x_spine, x_val],
                    [y_val, y_val],
                    color=color,
                    linestyle=":",
                    linewidth=1.2,
                    alpha=0.6,
                    zorder=1,
                    clip_on=False,
                )
                self._ax.plot(
                    [x_val, x_val],
                    [y_spine, y_val],
                    color=color,
                    linestyle=":",
                    linewidth=1.2,
                    alpha=0.6,
                    zorder=1,
                    clip_on=False,
                )

            # annotated label with arrow
            if label:
                self._ax.annotate(
                    label,
                    xy=(x_val, y_val),
                    xytext=(15, 15),
                    textcoords="offset points",
                    fontsize=self._lbl_fs,
                    color=color,
                    arrowprops=dict(
                        arrowstyle="->",
                        color=color,
                        lw=1.5,
                    ),
                    zorder=5,
                )
        return self

    def color_area(
        self, color: str = "skyblue", *, alpha: float = 0.4
    ) -> "FunctionPlot":
        """Fill the area between the curve and the x-axis.

        Parameters
        ----------
        color : str
            Fill color (any matplotlib color specification).
        alpha : float
            Opacity of the fill (0 = transparent, 1 = opaque).
        """
        self._ax.fill_between(
            self._x,
            self._y,
            0,
            color=color,
            alpha=alpha,
            zorder=1,
        )
        return self

    # Output methods

    def to_svg(self) -> str:
        """Export the plot as an SVG string.

        Suitable for passing to ``display_vector`` or ``combine_svgs``.
        """
        self._fig.tight_layout()
        buf = io.StringIO()
        self._fig.savefig(buf, format="svg", bbox_inches="tight")
        svg_str = buf.getvalue()
        buf.close()
        return strip_svg_header(svg_str)

    def show(self):
        """Display the plot in a matplotlib window."""
        self._fig.tight_layout()
        self._fig.show()

    def _repr_svg_(self) -> str:
        """Jupyter / IPython rich display hook (vector output)."""
        return self.to_svg()

    def _fmt_dims(self, w: float, h: float) -> tuple:
        """Format width and height for rectangle labels."""
        if self.only_integers:
            return int(w), int(h)
        w_s = int(w) if w == int(w) else round(w, 2)
        h_s = int(h) if h == int(h) else round(h, 2)
        return w_s, h_s
