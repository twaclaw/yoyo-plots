import os

import numpy as np
import plotly.graph_objects as go
from .common import svg_to_data_uri, resolve_user_path


class BasePlot:
    """
    Holds the underlying ``plotly.graph_objects.Figure`` and exposes
    convenience proxies so that instances can be used almost everywhere
    a bare Plotly figure is expected (``display()``, ``write_html()``, …).
    """

    def __init__(self):
        self.fig = go.Figure()

    # ── Plotly figure proxies ───────────────────────────────────────
    def show(self, *args, **kwargs):
        return self.fig.show(*args, **kwargs)

    def write_html(self, *args, **kwargs):
        return self.fig.write_html(*args, **kwargs)

    def write_image(self, *args, **kwargs):
        return self.fig.write_image(*args, **kwargs)

    def to_html(self, *args, **kwargs):
        return self.fig.to_html(*args, **kwargs)

    def to_image(self, *args, **kwargs):
        return self.fig.to_image(*args, **kwargs)

    def _repr_html_(self):
        return self.fig._repr_html_()

    @staticmethod
    def _get_image_source(image_path: str) -> str:
        path = resolve_user_path(image_path)
        if os.path.exists(path) and path.lower().endswith(".svg"):
            return svg_to_data_uri(path)
        return path

    def _add_arrow(self, x, y, ax, ay, line_width, color="black", arrow_size=1.5):
        self.fig.add_annotation(
            x=x, y=y, ax=ax, ay=ay,
            xref="x", yref="y", axref="x", ayref="y",
            text="", showarrow=True, arrowhead=2, arrowsize=arrow_size,
            arrowwidth=line_width, arrowcolor=color,
            standoff=0, startstandoff=0,
        )

    def _add_segment_arrow_tip(self, x, y, dx, dy, seg_width, color):
        """Draw a proportionally-sized arrowhead at the end of a segment."""
        dist = (dx**2 + dy**2) ** 0.5 or 1e-9
        tail_offset = 0.5
        ax = x - (dx / dist) * tail_offset
        ay = y - (dy / dist) * tail_offset

        base_width = 3.0
        prop_size = max(1.0, 1.5 * (seg_width / base_width))

        self.fig.add_annotation(
            x=x, y=y, ax=ax, ay=ay,
            xref="x", yref="y", axref="x", ayref="y",
            text="", showarrow=True, arrowhead=2, arrowsize=prop_size,
            arrowwidth=seg_width, arrowcolor=color,
            standoff=0, startstandoff=0,
        )


class NumberLine(BasePlot):
    """A straight (horizontal or vertical) number line.

    The constructor draws the bare axis with ticks and labels.

    nl = (NumberLine(-5, 5)
            .add_markers({0: "red"})
            .add_segments({-2: {"color": "blue", "arrow": True}}))
    """

    def __init__(
        self,
        xmin: int,
        xmax: int,
        font_size: int = 14,
        line_width: int = 2,
        tick_frequency: int = 1,
        rotate: bool = False,
        save_path: str | None = None,
    ):
        super().__init__()

        if tick_frequency <= 0:
            raise ValueError("tick_frequency must be a positive integer.")

        self.xmin = xmin
        self.xmax = xmax
        self.font_size = font_size
        self.line_width = line_width
        self.tick_frequency = tick_frequency
        self.rotate = rotate

        first_tick = int(np.ceil(xmin / tick_frequency) * tick_frequency)
        last_tick = int(np.floor(xmax / tick_frequency) * tick_frequency)
        self._tick_vals = list(range(first_tick, last_tick + 1, tick_frequency))
        n_ticks = len(self._tick_vals)
        if n_ticks == 0:
            self._tick_vals = [first_tick]
            n_ticks = 1

        self._first_tick = first_tick
        self._norm_max = float(n_ticks - 1)
        self._line_start = -1.0
        self._line_end = self._norm_max + 1.0
        delta = self._norm_max if self._norm_max > 0 else 1.0
        self._delta = delta
        self._arrow_len = delta * 0.05

        # ── Draw the base line + arrows + ticks + labels
        self._draw_base_line()
        self._draw_tick_marks_and_labels()
        self._apply_layout()

        if save_path:
            self.write_image(save_path)

    def _to_norm(self, v):
        return (v - self._first_tick) / self.tick_frequency

    def _draw_base_line(self):
        ls, le, al = self._line_start, self._line_end, self._arrow_len
        lw = self.line_width

        if not self.rotate:
            self.fig.add_shape(
                type="line", x0=ls, y0=0, x1=le, y1=0,
                line=dict(color="black", width=lw), layer="below",
            )
            overlap = 0.1 if self._delta <= 15 else self._delta * 0.02
            self._add_arrow(x=le + al, y=0, ax=le - overlap, ay=0, line_width=lw)
            self._add_arrow(x=ls - al, y=0, ax=ls + overlap, ay=0, line_width=lw)
        else:
            self.fig.add_shape(
                type="line", x0=0, y0=ls, x1=0, y1=le,
                line=dict(color="black", width=lw), layer="below",
            )
            overlap = 0.5 if self._delta <= 15 else self._delta * 0.05
            self._add_arrow(x=0, y=le + al, ax=0, ay=le - overlap, line_width=lw)
            self._add_arrow(x=0, y=ls - al, ax=0, ay=ls + overlap, line_width=lw)

    def _draw_tick_marks_and_labels(self):
        lw = self.line_width

        if not self.rotate:
            tick_cross = 0.15
            for val in self._tick_vals:
                nv = self._to_norm(val)
                self.fig.add_shape(
                    type="line", x0=nv, y0=-tick_cross, x1=nv, y1=tick_cross,
                    line=dict(color="black", width=lw), layer="below",
                )
                self.fig.add_annotation(
                    x=nv, y=-0.25, text=str(val), showarrow=False,
                    font=dict(size=self.font_size, color="black"),
                    xref="x", yref="y", yanchor="top",
                )

    def _apply_layout(self):
        al = self._arrow_len

        if not self.rotate:
            y_max, y_min = 1, -1
            y_range_span = y_max - y_min
            ppu = 50
            calc_h = max(250, int(y_range_span * ppu))
            calc_w = int(self._delta * ppu) if self._delta > 15 else None
            self.fig.update_layout(
                xaxis=dict(
                    range=[self._line_start - al * 2, self._line_end + al * 2],
                    visible=False, showgrid=False, zeroline=False,
                    showline=False, tickmode="array", tickvals=[],
                ),
                yaxis=dict(
                    visible=False, range=[y_min, y_max],
                    fixedrange=True, scaleanchor="x", scaleratio=1,
                ),
                height=calc_h, width=calc_w,
                plot_bgcolor="white",
                margin=dict(l=5, r=5, t=5, b=5),
                dragmode="pan", template="plotly_white",
            )
        else:
            x_min, x_max = -1.5, 1
            x_range_span = x_max - x_min
            yaxis_pos = (0 - x_min) / x_range_span
            y_range_min = self._line_start - al * 2
            y_range_max = self._line_end + al * 2
            y_range_span = y_range_max - y_range_min
            ppu = 50
            calc_w = max(250, int(x_range_span * ppu))
            calc_h = int(y_range_span * ppu)
            norm_tick_vals = [self._to_norm(v) for v in self._tick_vals]
            tick_text = [str(v) for v in self._tick_vals]
            self.fig.update_layout(
                yaxis=dict(
                    range=[y_range_min, y_range_max],
                    visible=True, showgrid=False, zeroline=False, showline=False,
                    tickmode="array", tickvals=norm_tick_vals, ticktext=tick_text,
                    ticks="outside", ticklen=10, tickwidth=self.line_width,
                    tickcolor="black",
                    tickfont=dict(size=self.font_size, color="black"),
                    anchor="free", position=yaxis_pos,
                ),
                xaxis=dict(visible=False, range=[x_min, x_max], fixedrange=True),
                width=calc_w, height=calc_h,
                plot_bgcolor="white",
                margin=dict(l=5, r=5, t=5, b=5),
                dragmode="pan", template="plotly_white",
            )

    # Methods to add additional attributes, like coloring, images,  segments, etc.
    def add_tick_icons(self, tick_icon, tick_icon_size: float = 0.8):
        """Add SVG icons at tick positions.

        *tick_icon* is either a single path applied to every tick, or a
        ``{position: path}`` dict.
        """
        for pos_val in self._tick_vals:
            if isinstance(tick_icon, dict):
                if pos_val not in tick_icon:
                    continue
                svg_path = tick_icon[pos_val]
            else:
                svg_path = tick_icon

            image_source = self._get_image_source(svg_path)

            if not self.rotate:
                x, y = self._to_norm(pos_val), 0.1
                x_anch, y_anch = "center", "bottom"
            else:
                x, y = 0.2, self._to_norm(pos_val)
                x_anch, y_anch = "left", "middle"

            self.fig.add_layout_image(
                source=image_source, x=x, y=y,
                sizex=tick_icon_size, sizey=tick_icon_size,
                xanchor=x_anch, yanchor=y_anch,
                xref="x", yref="y", layer="above", sizing="contain",
            )
        return self

    def add_markers(self, markers: dict, marker_size: float = 0.15):
        """Add circular markers on the line.

        *markers* maps tick positions to fill colours.  Use the special
        key ``"all"`` to set a base colour for every tick.
        """
        final_markers = {}
        if "all" in markers:
            for t in self._tick_vals:
                final_markers[t] = markers["all"]
        for k, v in markers.items():
            if k == "all":
                continue
            final_markers[k] = v

        for pos, color in final_markers.items():
            np_ = self._to_norm(pos)
            if not self.rotate:
                self.fig.add_shape(
                    type="circle",
                    x0=np_ - marker_size, y0=-marker_size,
                    x1=np_ + marker_size, y1=marker_size,
                    line=dict(color="black", width=2),
                    fillcolor=color, layer="above",
                )
            else:
                self.fig.add_shape(
                    type="circle",
                    x0=-marker_size, y0=np_ - marker_size,
                    x1=marker_size, y1=np_ + marker_size,
                    line=dict(color="black", width=2),
                    fillcolor=color, layer="above",
                )
        return self

    def add_segments(self, segments: dict, segment_width: float = 3):
        """Add coloured segments between ticks.

        Each entry maps a start position to either a colour string or a
        config dict ``{"color": …, "thickness": …, "arrow": bool}``.
        """
        default_seg_width = self.line_width * segment_width
        for start, config in segments.items():
            if isinstance(config, dict):
                color = config.get("color", "black")
                seg_width = config.get("thickness", default_seg_width)
                arrow = config.get("arrow", False)
            else:
                color = config
                seg_width = default_seg_width
                arrow = False

            ns = self._to_norm(start)
            if not self.rotate:
                self.fig.add_shape(
                    type="line", x0=ns, y0=0, x1=ns + 1, y1=0,
                    line=dict(color=color, width=seg_width), layer="above",
                )
                if arrow:
                    self._add_segment_arrow_tip(
                        x=ns + 1, y=0, dx=1, dy=0,
                        seg_width=seg_width, color=color,
                    )
            else:
                self.fig.add_shape(
                    type="line", x0=0, y0=ns, x1=0, y1=ns + 1,
                    line=dict(color=color, width=seg_width), layer="above",
                )
                if arrow:
                    self._add_segment_arrow_tip(
                        x=0, y=ns + 1, dx=0, dy=1,
                        seg_width=seg_width, color=color,
                    )
        return self

    def add_arcs(self, arcs: dict, arc_font_size: int | None = None):
        """Add jump arcs between ticks.

        *arcs* maps a start tick to ``{"len": int, "color": str, "text": str}``.
        The special key ``"all"`` broadcasts the same config to every tick.
        """
        if arc_font_size is None:
            arc_font_size = max(8, self.font_size - 2)

        final_arcs: dict = {}
        if "all" in arcs and isinstance(arcs["all"], dict):
            for t in self._tick_vals:
                final_arcs[t] = arcs["all"]
        for k, v in arcs.items():
            if k == "all":
                continue
            final_arcs[k] = v

        for start, cfg in final_arcs.items():
            if not isinstance(cfg, dict):
                continue
            jump_len = int(cfg.get("len", 1))
            if jump_len == 0:
                continue
            end = start + jump_len
            if start not in self._tick_vals or end not in self._tick_vals:
                continue

            arc_color = cfg.get("color", "black")
            arc_text = cfg.get("text", None)

            if not self.rotate:
                x0, y0 = self._to_norm(start), 0
                x1, y1 = self._to_norm(end), 0
                mid_x = (x0 + x1) / 2
                normalized_jump = abs(jump_len) / self.tick_frequency
                arc_h = 0.42 + 0.25 * max(0, normalized_jump - 1)
                path = f"M {x0},{y0} Q {mid_x},{arc_h} {x1},{y1}"
                self.fig.add_shape(
                    type="path", path=path,
                    line=dict(color=arc_color, width=self.line_width),
                    layer="above",
                )
                tdx, tdy = x1 - mid_x, y1 - arc_h
                tn = (tdx**2 + tdy**2) ** 0.5 or 1e-9
                tail_offset = 0.12
                ax_arrow = x1 - tail_offset * tdx / tn
                ay_arrow = y1 - tail_offset * tdy / tn
                self.fig.add_annotation(
                    x=x1, y=y1, ax=ax_arrow, ay=ay_arrow,
                    xref="x", yref="y", axref="x", ayref="y",
                    text="", showarrow=True, arrowhead=2, arrowsize=1.2,
                    arrowwidth=self.line_width, arrowcolor=arc_color, standoff=0,
                )
                if arc_text is not None:
                    self.fig.add_annotation(
                        x=mid_x, y=0.5 * arc_h + 0.02,
                        text=str(arc_text), showarrow=False,
                        font=dict(size=arc_font_size, color=arc_color),
                        xanchor="center", yanchor="bottom",
                        xref="x", yref="y",
                    )
            else:
                x0, y0 = 0, self._to_norm(start)
                x1, y1 = 0, self._to_norm(end)
                mid_y = (y0 + y1) / 2
                normalized_jump = abs(jump_len) / self.tick_frequency
                arc_w = 0.42 + 0.25 * max(0, normalized_jump - 1)
                path = f"M {x0},{y0} Q {arc_w},{mid_y} {x1},{y1}"
                self.fig.add_shape(
                    type="path", path=path,
                    line=dict(color=arc_color, width=self.line_width),
                    layer="above",
                )
                tdx, tdy = x1 - arc_w, y1 - mid_y
                tn = (tdx**2 + tdy**2) ** 0.5 or 1e-9
                tail_offset = 0.12
                ax_arrow = x1 - tail_offset * tdx / tn
                ay_arrow = y1 - tail_offset * tdy / tn
                self.fig.add_annotation(
                    x=x1, y=y1, ax=ax_arrow, ay=ay_arrow,
                    xref="x", yref="y", axref="x", ayref="y",
                    text="", showarrow=True, arrowhead=2, arrowsize=1.2,
                    arrowwidth=self.line_width, arrowcolor=arc_color, standoff=0,
                )
                if arc_text is not None:
                    self.fig.add_annotation(
                        x=0.5 * arc_w + 0.02, y=mid_y,
                        text=str(arc_text), showarrow=False,
                        font=dict(size=arc_font_size, color=arc_color),
                        xanchor="left", yanchor="middle",
                        xref="x", yref="y",
                    )
        return self

    def add_boxes(self, box_size: float = 1.0, box_labels: dict | None = None):
        """Draw the arithmetic boxes below the line.

        ``box_labels`` maps ``"box1"`` … ``"box4"`` to display values.
        """
        gap = box_size * 0.2
        eq_gap = box_size * 0.4
        total_content_width = (4 * box_size) + (2 * gap) + (2 * eq_gap)

        if not self.rotate:
            start_x = self._norm_max / 2 - total_content_width / 2
            dist_from_line = 1.0 + (box_size * 0.5)
            box_y_center = -(dist_from_line + box_size / 2)
        else:
            start_x = 1.5
            box_y_center = self._norm_max / 2

        def _add_box(x_left, label_key=None):
            self.fig.add_shape(
                type="rect",
                x0=x_left, y0=box_y_center - box_size / 2,
                x1=x_left + box_size, y1=box_y_center + box_size / 2,
                line=dict(color="black", width=2),
                fillcolor="white", layer="below",
            )
            if box_labels and label_key and label_key in box_labels:
                self.fig.add_annotation(
                    x=x_left + box_size / 2, y=box_y_center,
                    text=str(box_labels[label_key]), showarrow=False,
                    font=dict(size=self.font_size * 1.5, color="black"),
                    xref="x", yref="y",
                )
            return x_left + box_size

        cur_x = start_x
        cur_x = _add_box(cur_x, "box1")
        cur_x += gap
        cur_x = _add_box(cur_x, "box2")
        cur_x += gap
        cur_x = _add_box(cur_x, "box3")
        cur_x += eq_gap
        self.fig.add_annotation(
            x=cur_x, y=box_y_center, text="=", showarrow=False,
            font=dict(size=self.font_size * 1.5, color="black"),
            xref="x", yref="y",
        )
        cur_x += eq_gap
        _add_box(cur_x, "box4")

        # Adjust vertical range to accommodate boxes
        if not self.rotate:
            box_bottom = box_y_center - box_size / 2
            y_min = min(-1, box_bottom - 0.5)
            y_range_span = 1 - y_min
            ppu = 50
            calc_h = max(250, int(y_range_span * ppu))
            self.fig.update_layout(
                yaxis=dict(range=[y_min, 1]),
                height=calc_h,
            )

        return self


class CircularNumberLine(BasePlot):
    """A circular number line from *xmin* to *xmax*.

    Builder methods: ``.add_markers``, ``.add_segments``,
    ``.add_tick_icons``, ``.add_center_image``, ``.add_boxes``.

    Call ``.build()`` after all builder methods to finalise layout.
    """

    def __init__(
        self,
        xmin: float,
        xmax: float,
        font_size: int = 14,
        line_width: int = 2,
        tick_distance: float | None = None,
        radius: float = 5.0,
        save_path: str | None = None,
    ):
        super().__init__()

        self.xmin = xmin
        self.xmax = xmax
        self.font_size = font_size
        self.line_width = line_width
        self.marker_size = 0.4

        delta = (xmax - xmin) + 1
        if delta <= 0:
            delta = 1
        self._delta = delta

        if tick_distance is not None:
            radius = (delta * tick_distance) / (2 * np.pi)
        self.radius = radius

        self._tick_vals = list(range(int(np.ceil(xmin)), int(np.floor(xmax)) + 1))
        if len(self._tick_vals) == 0:
            self._tick_vals = [int(xmin)]

        self._tick_length = radius * 0.05
        self._r_in = radius - self._tick_length
        self._r_out = radius + self._tick_length
        self._r_text = radius + self._tick_length + (font_size / 15.0)

        self._tick_icon_size = 0.0
        self._box_distance = 1.0
        self._y_min_bound = -radius - self._box_distance

        self._draw_circle_and_ticks()

        if save_path:
            self.write_image(save_path)

    def _angle(self, val):
        return np.pi / 2 - (val - self.xmin) / self._delta * 2 * np.pi

    def _draw_circle_and_ticks(self):
        r = self.radius
        lw = self.line_width

        self.fig.add_shape(
            type="circle", x0=-r, y0=-r, x1=r, y1=r,
            line=dict(color="black", width=lw), layer="below",
        )

        for val in self._tick_vals:
            angle = self._angle(val)
            self.fig.add_shape(
                type="line",
                x0=self._r_in * np.cos(angle), y0=self._r_in * np.sin(angle),
                x1=self._r_out * np.cos(angle), y1=self._r_out * np.sin(angle),
                line=dict(color="black", width=lw), layer="below",
            )
            self.fig.add_annotation(
                x=self._r_text * np.cos(angle),
                y=self._r_text * np.sin(angle),
                text=str(val), showarrow=False,
                font=dict(size=self.font_size, color="black"),
                xanchor="center", yanchor="middle",
            )

    def _apply_layout(self):
        """(Re)compute and apply the final layout bounds."""
        val_max = (
            self.radius + self._tick_length + (self.font_size / 15.0)
            + max(1.0, max(self._tick_icon_size, self.marker_size))
        )
        pad = val_max * 0.05
        val_max += pad
        y_min_bound = self._y_min_bound

        self.fig.update_layout(
            xaxis=dict(range=[-val_max, val_max], visible=False,
                       fixedrange=True, zeroline=False),
            yaxis=dict(range=[y_min_bound - pad, val_max], visible=False,
                       scaleanchor="x", scaleratio=1,
                       fixedrange=True, zeroline=False),
            width=500,
            height=int(500 * (val_max - y_min_bound + pad) / (2 * val_max)),
            plot_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20),
            dragmode="pan", template="plotly_white",
        )

    # Methods to add images, segments, etc.
    def add_tick_icons(self, tick_icon, tick_icon_size: float = 2.0):
        """Add SVG icons inside the circle at tick positions."""
        self._tick_icon_size = tick_icon_size
        r_img = self.radius - self._tick_length - tick_icon_size / 2.0 - 0.5
        for pos_val in self._tick_vals:
            if isinstance(tick_icon, dict):
                if pos_val not in tick_icon:
                    continue
                svg_path = tick_icon[pos_val]
            else:
                svg_path = tick_icon

            image_source = self._get_image_source(svg_path)
            angle = self._angle(pos_val)
            self.fig.add_layout_image(
                source=image_source,
                x=r_img * np.cos(angle), y=r_img * np.sin(angle),
                sizex=tick_icon_size, sizey=tick_icon_size,
                xanchor="center", yanchor="middle",
                xref="x", yref="y", layer="above", sizing="contain",
            )
        return self

    def add_markers(self, markers: dict, marker_size: float = 0.4):
        """Add circular markers on the circle at tick positions."""
        self.marker_size = marker_size
        final_markers = {}
        if "all" in markers:
            for t in self._tick_vals:
                final_markers[t] = markers["all"]
        for k, v in markers.items():
            if k == "all":
                continue
            final_markers[k] = v

        for pos, color in final_markers.items():
            angle = self._angle(pos)
            x_c = self.radius * np.cos(angle)
            y_c = self.radius * np.sin(angle)
            self.fig.add_shape(
                type="circle",
                x0=x_c - marker_size, y0=y_c - marker_size,
                x1=x_c + marker_size, y1=y_c + marker_size,
                line=dict(color="black", width=2),
                fillcolor=color, layer="above",
            )
        return self

    def add_center_image(self, image_path: str, size: float = 4.0):
        """Place an image at the centre of the circle."""
        image_source = self._get_image_source(image_path)
        self.fig.add_layout_image(
            source=image_source, x=0, y=0,
            sizex=size, sizey=size,
            xanchor="center", yanchor="middle",
            xref="x", yref="y", layer="below", sizing="contain",
        )
        return self

    def add_segments(self, segments: dict, segment_width: float = 3):
        """Add coloured arc segments between adjacent ticks."""
        default_seg_width = self.line_width * segment_width
        for start, config in segments.items():
            if isinstance(config, dict):
                color = config.get("color", "black")
                seg_width = config.get("thickness", default_seg_width)
                arrow = config.get("arrow", False)
            else:
                color = config
                seg_width = default_seg_width
                arrow = False

            end = start + 1
            start_angle = self._angle(start)
            end_angle = self._angle(end)

            t = np.linspace(start_angle, end_angle, 50)
            x_arc = self.radius * np.cos(t)
            y_arc = self.radius * np.sin(t)
            path = f"M {x_arc[0]},{y_arc[0]}"
            for i in range(1, len(t)):
                path += f" L {x_arc[i]},{y_arc[i]}"

            self.fig.add_shape(
                type="path", path=path,
                line=dict(color=color, width=seg_width), layer="above",
            )

            if arrow:
                dx = x_arc[-1] - x_arc[-2]
                dy = y_arc[-1] - y_arc[-2]
                self._add_segment_arrow_tip(
                    x=x_arc[-1], y=y_arc[-1], dx=dx, dy=dy,
                    seg_width=seg_width, color=color,
                )
        return self

    def add_boxes(self, box_size: float = 3, box_labels: dict | None = None,
                  box_distance: float = 1.0):
        """Draw arithmetic boxes below the circle."""
        self._box_distance = box_distance
        gap = box_size * 0.2
        eq_gap = box_size * 0.4
        total_content_width = (4 * box_size) + (2 * gap) + (2 * eq_gap)
        y_min_bound = -self.radius - box_distance
        box_y_center = y_min_bound - box_size / 2 - box_distance
        start_x = -total_content_width / 2

        def _add_box(x_left, label_key=None):
            self.fig.add_shape(
                type="rect",
                x0=x_left, y0=box_y_center - box_size / 2,
                x1=x_left + box_size, y1=box_y_center + box_size / 2,
                line=dict(color="black", width=2),
                fillcolor="white", layer="below",
            )
            if box_labels and label_key and label_key in box_labels:
                self.fig.add_annotation(
                    x=x_left + box_size / 2, y=box_y_center,
                    text=str(box_labels[label_key]), showarrow=False,
                    font=dict(size=self.font_size * 1.5, color="black"),
                    xref="x", yref="y",
                )
            return x_left + box_size

        cur_x = start_x
        cur_x = _add_box(cur_x, "box1")
        cur_x += gap
        cur_x = _add_box(cur_x, "box2")
        cur_x += gap
        cur_x = _add_box(cur_x, "box3")
        cur_x += eq_gap
        self.fig.add_annotation(
            x=cur_x, y=box_y_center, text="=", showarrow=False,
            font=dict(size=self.font_size * 1.5, color="black"),
            xref="x", yref="y",
        )
        cur_x += eq_gap
        _add_box(cur_x, "box4")

        self._y_min_bound = box_y_center - box_size / 2 - box_distance
        return self

    def build(self):
        """Finalise layout after all builder methods have been called."""
        self._apply_layout()
        return self


class CartesianPlane(BasePlot):
    """A Cartesian coordinate plane with axes, grid, and optional overlays.

    Builder methods: ``.add_markers``, ``.add_icons``,
    ``.add_manhattan_lines``, ``.add_areas``.
    """

    def __init__(
        self,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        font_size: int = 14,
        line_width: int = 2,
        draw_ticks: bool = True,
        save_path: str | None = None,
    ):
        super().__init__()

        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.font_size = font_size
        self.line_width = line_width
        self.marker_size = 0.15

        self._aw = (xmax - xmin) * 0.05
        self._ah = (ymax - ymin) * 0.05

        self._draw_grid(draw_ticks)
        self._draw_axes()
        self._apply_layout()

        if save_path:
            self.write_image(save_path)

    def _draw_grid(self, draw_ticks: bool):
        tick_cross_size = 0.15
        lw = self.line_width

        for x_val in range(int(np.ceil(self.xmin)), int(np.floor(self.xmax)) + 1):
            self.fig.add_shape(
                type="line", x0=x_val, y0=self.ymin, x1=x_val, y1=self.ymax,
                line=dict(color="lightgray", width=1), layer="below",
            )
            if draw_ticks:
                self.fig.add_shape(
                    type="line",
                    x0=x_val, y0=-tick_cross_size, x1=x_val, y1=tick_cross_size,
                    line=dict(color="black", width=lw), layer="below",
                )
            if x_val != 0:
                self.fig.add_annotation(
                    x=x_val, y=-0.2, text=str(x_val), showarrow=False,
                    font=dict(size=self.font_size),
                    xanchor="center", yanchor="top",
                )

        for y_val in range(int(np.ceil(self.ymin)), int(np.floor(self.ymax)) + 1):
            self.fig.add_shape(
                type="line", x0=self.xmin, y0=y_val, x1=self.xmax, y1=y_val,
                line=dict(color="lightgray", width=1), layer="below",
            )
            if draw_ticks:
                self.fig.add_shape(
                    type="line",
                    x0=-tick_cross_size, y0=y_val, x1=tick_cross_size, y1=y_val,
                    line=dict(color="black", width=lw), layer="below",
                )
            if y_val != 0:
                self.fig.add_annotation(
                    x=-0.2, y=y_val, text=str(y_val), showarrow=False,
                    font=dict(size=self.font_size),
                    xanchor="right", yanchor="middle",
                )

        # Origin label
        self.fig.add_annotation(
            x=-0.2, y=-0.2, text="0", showarrow=False,
            font=dict(size=self.font_size),
            xanchor="right", yanchor="top",
        )

    def _draw_axes(self):
        lw = self.line_width
        aw, ah = self._aw, self._ah

        # x axis
        self.fig.add_shape(
            type="line", x0=self.xmin, y0=0, x1=self.xmax, y1=0,
            line=dict(color="black", width=lw), layer="below",
        )
        overlap_x = 0.1 if (self.xmax - self.xmin) <= 15 else (self.xmax - self.xmin) * 0.02
        self._add_arrow(x=self.xmax + aw, y=0, ax=self.xmax - overlap_x, ay=0,
                        line_width=lw)
        self._add_arrow(x=self.xmin - aw, y=0, ax=self.xmin + overlap_x, ay=0,
                        line_width=lw)

        # y axis
        self.fig.add_shape(
            type="line", x0=0, y0=self.ymin, x1=0, y1=self.ymax,
            line=dict(color="black", width=lw), layer="below",
        )
        overlap_y = 0.5 if (self.ymax - self.ymin) <= 15 else (self.ymax - self.ymin) * 0.05
        self._add_arrow(x=0, y=self.ymax + ah, ax=0, ay=self.ymax - overlap_y,
                        line_width=lw)
        self._add_arrow(x=0, y=self.ymin - ah, ax=0, ay=self.ymin + overlap_y,
                        line_width=lw)

    def _apply_layout(self):
        aw, ah = self._aw, self._ah
        ppu = 50
        w = max(400, int((self.xmax - self.xmin + 2 * aw) * ppu))
        h = max(400, int((self.ymax - self.ymin + 2 * ah) * ppu))
        pad_x = (self.xmax - self.xmin) * 0.1
        pad_y = (self.ymax - self.ymin) * 0.1

        self.fig.update_layout(
            xaxis=dict(range=[self.xmin - pad_x, self.xmax + pad_x],
                       visible=False, fixedrange=True, zeroline=False),
            yaxis=dict(range=[self.ymin - pad_y, self.ymax + pad_y],
                       visible=False, scaleanchor="x", scaleratio=1,
                       fixedrange=True, zeroline=False),
            plot_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20),
            dragmode="pan", template="plotly_white",
            width=w, height=h,
        )

    # Modifier methods
    def add_areas(self, areas: list[dict]):
        """Add rectangular shaded regions.

        Each dict: ``{"x0", "y0", "x1", "y1", "color", "alpha",
        "edge_color", "show_label", "font_size", "font_color"}``.
        """
        for area in areas:
            ax0 = float(area["x0"])
            ay0 = float(area["y0"])
            ax1 = float(area["x1"])
            ay1 = float(area["y1"])
            a_color = area.get("color", "steelblue")
            a_alpha = area.get("alpha", 0.35)
            a_edge = area.get("edge_color", a_color)
            self.fig.add_shape(
                type="rect", x0=ax0, y0=ay0, x1=ax1, y1=ay1,
                fillcolor=a_color, opacity=a_alpha,
                line=dict(color=a_edge, width=self.line_width),
                layer="below",
            )
            if area.get("show_label", False):
                w = abs(ax1 - ax0)
                h = abs(ay1 - ay0)
                w_str = int(w) if w == int(w) else round(w, 2)
                h_str = int(h) if h == int(h) else round(h, 2)
                label_font_size = area.get("font_size", self.font_size)
                label_font_color = area.get("font_color", "black")
                self.fig.add_annotation(
                    x=(ax0 + ax1) / 2, y=(ay0 + ay1) / 2,
                    text=f"{w_str}\u00d7{h_str}", showarrow=False,
                    font=dict(size=label_font_size, color=label_font_color),
                    xanchor="center", yanchor="middle",
                    xref="x", yref="y",
                )
        return self

    def add_markers(self, markers: dict, marker_size: float = 0.15):
        """Add point markers on the plane.

        *markers* maps ``(x, y)`` tuples to property dicts:
        ``{"color", "draw_lines", "dash", "show_coords"}``.
        """
        self.marker_size = marker_size
        lw = self.line_width
        for (cx, cy), props in markers.items():
            color = props.get("color", "red")
            if props.get("draw_lines"):
                m_dash = props.get("dash", "dot")
                self.fig.add_shape(
                    type="line", x0=cx, y0=0, x1=cx, y1=cy,
                    line=dict(color=color, width=lw, dash=m_dash), layer="below",
                )
                self.fig.add_shape(
                    type="line", x0=0, y0=cy, x1=cx, y1=cy,
                    line=dict(color=color, width=lw, dash=m_dash), layer="below",
                )
            self.fig.add_shape(
                type="circle",
                x0=cx - marker_size, y0=cy - marker_size,
                x1=cx + marker_size, y1=cy + marker_size,
                line=dict(color="black", width=lw),
                fillcolor=color, layer="above",
            )
            if props.get("show_coords"):
                x_off = 10 if cx >= 0 else -10
                y_off = 10 if cy >= 0 else -10
                a_xanch = "left" if cx >= 0 else "right"
                a_yanch = "bottom" if cy >= 0 else "top"
                self.fig.add_annotation(
                    x=cx, y=cy, text=f"({cx}, {cy})",
                    font=dict(color=color, size=self.font_size),
                    showarrow=False, xshift=x_off, yshift=y_off,
                    xanchor=a_xanch, yanchor=a_yanch,
                )
        return self

    def add_icons(self, icons: dict, icon_size: float = 1.0):
        """Add SVG icons on the plane.

        *icons* maps ``(x, y)`` to ``{"image", "color", "draw_lines",
        "dash", "show_coords"}``.
        """
        lw = self.line_width
        for (cx, cy), props in icons.items():
            svg_path = props.get("image")
            if not svg_path:
                continue
            img_src = self._get_image_source(svg_path)

            if props.get("draw_lines"):
                line_color = props.get("color", "gray")
                i_dash = props.get("dash", "dot")
                self.fig.add_shape(
                    type="line", x0=cx, y0=0, x1=cx, y1=cy,
                    line=dict(color=line_color, width=lw, dash=i_dash),
                    layer="below",
                )
                self.fig.add_shape(
                    type="line", x0=0, y0=cy, x1=cx, y1=cy,
                    line=dict(color=line_color, width=lw, dash=i_dash),
                    layer="below",
                )

            self.fig.add_layout_image(
                source=img_src, x=cx, y=cy,
                sizex=icon_size, sizey=icon_size,
                xanchor="center", yanchor="middle",
                xref="x", yref="y", layer="above", sizing="contain",
            )

            if props.get("show_coords"):
                x_off = 20 if cx >= 0 else -20
                y_off = 20 if cy >= 0 else -20
                a_xanch = "left" if cx >= 0 else "right"
                a_yanch = "bottom" if cy >= 0 else "top"
                text_color = props.get("color", "black")
                self.fig.add_annotation(
                    x=cx, y=cy, text=f"({cx}, {cy})",
                    font=dict(color=text_color, size=self.font_size),
                    showarrow=False, xshift=x_off, yshift=y_off,
                    xanchor=a_xanch, yanchor=a_yanch,
                )
        return self

    def add_manhattan_lines(self, manhattan_lines: dict):
        """Add Manhattan-distance path lines between point pairs.

        *manhattan_lines* maps ``((x1,y1),(x2,y2))`` to
        ``{"color", "path", "dash", "width"}``.
        """
        lw = self.line_width
        for ((x1, y1), (x2, y2)), props in manhattan_lines.items():
            color = props.get("color", "green")
            path_type = props.get("path", "x_first")
            dash = props.get("dash", "dot")
            width = props.get("width", lw)

            if path_type in ("x_first", "both"):
                self.fig.add_shape(
                    type="line", x0=x1, y0=y1, x1=x2, y1=y1,
                    line=dict(color=color, width=width, dash=dash), layer="below",
                )
                self.fig.add_shape(
                    type="line", x0=x2, y0=y1, x1=x2, y1=y2,
                    line=dict(color=color, width=width, dash=dash), layer="below",
                )
            if path_type in ("y_first", "both"):
                self.fig.add_shape(
                    type="line", x0=x1, y0=y1, x1=x1, y1=y2,
                    line=dict(color=color, width=width, dash=dash), layer="below",
                )
                self.fig.add_shape(
                    type="line", x0=x1, y0=y2, x1=x2, y1=y2,
                    line=dict(color=color, width=width, dash=dash), layer="below",
                )
        return self
