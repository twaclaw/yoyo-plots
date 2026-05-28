"""
functions.py – Plot a mathematical function with optional Riemann / Lebesgue rectangles.
"""

from __future__ import annotations

import io
import math

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

            segments_list: list[tuple[float, float]] = []
            for s_idx, e_idx in zip(starts, ends):
                x_left = float(self._x[s_idx])
                x_right = float(self._x[min(e_idx, len(self._x) - 1)])
                if self.only_integers:
                    # snap to integer boundaries (shrink inward)
                    x_left = float(math.ceil(x_left))
                    x_right = float(math.floor(x_right))
                seg_w = x_right - x_left
                if seg_w <= 0:
                    continue
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

            # Label each segment individually
            if rect.get("show_label", False) and segments_list:
                for seg_x, seg_w in segments_list:
                    seg_measure = float(round(seg_w)) if self.only_integers else seg_w
                    m_str, h_str = self._fmt_dims(seg_measure, strip_h)
                    self._ax.text(
                        seg_x + seg_w / 2,
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
                x_val,
                y_val,
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


import drawsvg as draw

from .common import SvgDrawing, embed_svg_image

_FONT = "Comic Sans MS, Comic Sans, cursive"
_ARROW_COLOR = "#444"
_ARROW_HEAD_LEN = 12
_ARROW_HEAD_WIDTH = 5


def _is_svg(source: str) -> bool:
    """Return ``True`` if *source* is an inline SVG, an ``svg+xml`` data URI,
    or a path ending in ``.svg``.  Everything else is treated as a plain
    text label.
    """
    s = source.strip()
    return (
        s.startswith("<svg")
        or s.startswith("data:image/svg+xml")
        or s.lower().endswith(".svg")
    )


class _MemberRef:
    """A reference to one element inside a :class:`Set`.

    Returned by ``Set[index]`` or ``Set["label"]``.  Pass these directly
    as the endpoints of :class:`CayleyDiagram` mappings — no global
    variables needed.
    """

    __slots__ = ("_set", "index")

    def __init__(self, set_: "Set", index: int) -> None:
        self._set = set_
        self.index = index

    @property
    def content(self) -> str:
        """The raw string stored for this member."""
        return self._set._members[self.index]

    def __repr__(self) -> str:
        return f"<MemberRef [{self.index}] {self.content!r}>"


class Set(SvgDrawing):
    """A mathematical set rendered as a labelled oval.

    Each element is a plain **string** — either a text label *or* an SVG
    source (path ending in ``.svg``, inline ``<svg>…</svg>`` string, or
    ``data:image/svg+xml`` URI).  The two roles are mutually exclusive per
    element; raster image formats are not supported.

    Access elements via subscript to build :class:`CayleyDiagram` mappings::

        A = Set(["a₁", "a₂", "a₃"], label="A")
        B = Set(["b₁", "b₂"],        label="B")

        diagram = CayleyDiagram(
            sets=[A, B],
            mappings=[(A["a₁"], B["b₁"]), (A["a₂"], B["b₁"]), (A["a₃"], B["b₂"])],
        )

    Parameters
    ----------
    members : list[str]
        Elements of the set, displayed top-to-bottom.
    label : str | None
        Optional set name shown at the top of the oval.
    padding : float
        Extra space between the content and the oval edge.
    item_spacing : float
        Vertical gap between consecutive members.
    img_size : float
        Width = height for image thumbnails.
    font_size : int
        Font size for all text.
    """

    def __init__(
        self,
        members: list[str],
        label: str | None = None,
        *,
        padding: float = 28,
        item_spacing: float = 14,
        img_size: float = 60,
        font_size: int = 16,
    ):
        self._members = list(members)
        self.label = label
        self.padding = padding
        self.item_spacing = item_spacing
        self.img_size = img_size
        self.font_size = font_size

    def __getitem__(self, key: int | str) -> _MemberRef:
        """Return a :class:`_MemberRef` for *key*.

        Parameters
        ----------
        key : int
            Zero-based position.
        key : str
            Member string value (first match wins).
        """
        if isinstance(key, int):
            if not 0 <= key < len(self._members):
                raise IndexError(key)
            return _MemberRef(self, key)
        try:
            return _MemberRef(self, self._members.index(key))
        except ValueError:
            raise KeyError(key) from None

    def __len__(self) -> int:
        return len(self._members)

    def _member_size(self, content: str) -> tuple[float, float]:
        """``(content_width, content_height)`` for one member string."""
        if _is_svg(content):
            return self.img_size, self.img_size
        return len(content) * self.font_size * 0.6, self.font_size * 1.2

    def get_layout(self) -> tuple[float, float, list[tuple[float, float, float]]]:
        """Compute the oval dimensions and each member's centre.

        Returns
        -------
        set_w, set_h : float
            Bounding box of the oval.
        member_data : list of ``(cx, cy, mw)``
            One tuple per member in the same order as *members*.
            *cx* is always ``set_w / 2`` (members are centred horizontally).
        """
        sizes = [self._member_size(m) for m in self._members]

        max_content_w = max((mw for mw, _ in sizes), default=0.0)
        label_w = len(self.label) * self.font_size * 0.6 if self.label else 0.0
        set_w = max(max_content_w, label_w) + self.padding * 4

        curr_y = self.padding
        if self.label:
            curr_y += self.font_size * 1.5 + self.item_spacing * 0.5

        member_data: list[tuple[float, float, float]] = []
        for mw, mh in sizes:
            cy = curr_y + mh / 2
            member_data.append((set_w / 2, cy, mw))
            curr_y = cy + mh / 2 + self.item_spacing

        set_h = curr_y - self.item_spacing + self.padding
        return set_w, set_h, member_data

    def get_svg_dimensions(self) -> tuple[float, float]:
        w, h, _ = self.get_layout()
        return w, h

    def to_group(self, **kwargs) -> draw.Group:
        set_w, set_h, member_data = self.get_layout()
        g = draw.Group()

        # Background oval
        g.append(
            draw.Ellipse(
                set_w / 2,
                set_h / 2,
                rx=set_w / 2,
                ry=set_h / 2,
                fill="white",
                stroke="#333",
                stroke_width=2,
            )
        )

        # Optional set label
        if self.label:
            g.append(
                draw.Text(
                    self.label,
                    self.font_size,
                    set_w / 2,
                    self.padding * 0.65 + self.font_size / 2,
                    font_family=_FONT,
                    font_weight="bold",
                    text_anchor="middle",
                    dominant_baseline="middle",
                    fill="#333",
                )
            )

        # Each member is either an image or a text label — never both.
        for content, (cx, cy, _) in zip(self._members, member_data):
            if _is_svg(content):
                g.append(
                    embed_svg_image(
                        content,
                        cx - self.img_size / 2,
                        cy - self.img_size / 2,
                        self.img_size,
                        self.img_size,
                    )
                )
            else:
                g.append(
                    draw.Text(
                        content,
                        self.font_size,
                        cx,
                        cy,
                        font_family=_FONT,
                        text_anchor="middle",
                        dominant_baseline="middle",
                        fill="#333",
                    )
                )

        return g


class CayleyDiagram(SvgDrawing):
    """Function mapping diagram between two or more :class:`Set` s.

    Sets are laid out left-to-right.  Arrows connect mapped members across
    sets, departing from and arriving at the member content (drawn on top of
    the ovals so they remain visible where they cross the oval stroke).

    Obtain member references via ``set_obj[index]`` or ``set_obj["label"]``::

        Fruits = Set(["apple", "banana", "cherry"], label="Fruits")
        Vars   = Set(["x", "y"],                   label="Variables")

        diagram = CayleyDiagram(
            sets=[Fruits, Vars],
            mappings=[
                (Fruits["apple"],  Vars["x"]),
                (Fruits["banana"], Vars["y"]),
                (Fruits["cherry"], Vars["x"]),
            ],
        )

    For a bijection, a comprehension keeps things concise::

        G = Set(["α", "β", "γ", "δ"], label="Greek")
        L = Set(["a", "b", "c", "d"], label="Latin")
        diagram = CayleyDiagram(sets=[G, L], mappings=[(G[i], L[i]) for i in range(4)])

    Parameters
    ----------
    sets : list[Set]
        Two or more sets in order (domain → … → codomain).
    mappings : list of ``(_MemberRef, _MemberRef)`` pairs
        Each pair connects one element of a source set to one element of a
        target set.
    spacing_x : float
        Horizontal gap between consecutive ovals.
    arrow_image : str | None
        Optional image (file path, inline ``<svg>`` string, or ``data:`` URI)
        drawn on top of every mapping arrow.  When ``None`` (default) the
        arrows are rendered as plain curves.  SVG sources are inlined via
        :func:`yoyo_plots.common.embed_svg_image` so they remain vector and
        render correctly inside Quarto documents.
    arrow_image_size : float
        Width = height of the per-arrow image when *arrow_image* is provided.
    arrow_image_offset_y : float
        Vertical displacement of the image relative to the arrow's midpoint.
        Negative values lift the image *above* the line; ``0`` (default)
        centres it on the line.
    """

    def __init__(
        self,
        sets: list[Set],
        mappings: list[tuple[_MemberRef, _MemberRef]],
        *,
        spacing_x: float = 140,
        arrow_image: str | None = None,
        arrow_image_size: float = 24,
        arrow_image_offset_y: float = 0,
    ):
        self.sets = sets
        self.mappings = mappings
        self.spacing_x = spacing_x
        self.arrow_image = arrow_image
        self.arrow_image_size = arrow_image_size
        self.arrow_image_offset_y = arrow_image_offset_y

    def get_svg_dimensions(self) -> tuple[float, float]:
        total_w = sum(s.get_svg_dimensions()[0] for s in self.sets)
        total_w += self.spacing_x * max(len(self.sets) - 1, 0)
        total_h = max((s.get_svg_dimensions()[1] for s in self.sets), default=0.0)
        return total_w, total_h

    def to_group(self, **_kwargs) -> draw.Group:
        g = draw.Group()
        _, total_h = self.get_svg_dimensions()

        # Key: (id(set_instance), member_index)
        # Value: (global_cy, set_x_offset, set_w, content_w)
        member_info: dict[tuple[int, int], tuple[float, float, float, float]] = {}
        curr_x = 0.0

        for s in self.sets:
            sw, sh, member_data = s.get_layout()
            off_y = (total_h - sh) / 2

            sg = draw.Group(transform=f"translate({curr_x},{off_y})")
            sg.append(s.to_group())
            g.append(sg)

            for i, (_, local_cy, mw) in enumerate(member_data):
                member_info[(id(s), i)] = (off_y + local_cy, curr_x, sw, mw)

            curr_x += sw + self.spacing_x

        # Arrow tail = right edge of source content  (set_cx + mw/2)
        # Arrow head = left  edge of target content  (set_cx - mw/2)
        for from_ref, to_ref in self.mappings:
            key_f = (id(from_ref._set), from_ref.index)
            key_t = (id(to_ref._set), to_ref.index)
            if key_f not in member_info or key_t not in member_info:
                continue

            gfy, off_x_f, sw_f, mw_f = member_info[key_f]
            gty, off_x_t, sw_t, mw_t = member_info[key_t]

            fx, fy = off_x_f + sw_f / 2 + mw_f / 2, gfy
            tx, ty = off_x_t + sw_t / 2 - mw_t / 2, gty

            cp = (tx - fx) * 0.45
            path = draw.Path(fill="none", stroke=_ARROW_COLOR, stroke_width=2)
            path.M(fx, fy)
            path.C(fx + cp, fy, tx - cp, ty, tx - _ARROW_HEAD_LEN + 2, ty)
            g.append(path)

            head = draw.Path(fill=_ARROW_COLOR, stroke="none")
            head.M(tx, ty)
            head.L(tx - _ARROW_HEAD_LEN, ty - _ARROW_HEAD_WIDTH)
            head.L(tx - _ARROW_HEAD_LEN, ty + _ARROW_HEAD_WIDTH)
            head.Z()
            g.append(head)

            if self.arrow_image:
                # Midpoint of a cubic Bézier with horizontal control handles
                # equals the average of the endpoints.
                mx = (fx + tx) / 2
                my = (fy + ty) / 2 + self.arrow_image_offset_y
                s = self.arrow_image_size
                g.append(
                    embed_svg_image(self.arrow_image, mx - s / 2, my - s / 2, s, s)
                )

        return g
