from dataclasses import dataclass

import drawsvg as draw

from yoyo_plots.common import SvgDrawing

# ── Defaults & constants ──────────────────────────────────────────────────
DEFAULT_FONT = "Comic Sans MS"

DEFAULT_DIGIT_COLORS = [
    "black",
    "red",
    "blue",
    "green",
    "purple",
    "orange",
    "pink",
    "brown",
    "gray",
    "cyan",
]

_LABEL_PADDING = 4
_DOOR_WIDTH_RATIO = 0.5
_DOOR_HEIGHT_RATIO = 0.6
_DOOR_FRAME_THICKNESS = 3
_DOOR_WOOD_COLOR = "#DEB887"
_LABEL_DOOR_GAP = 6
_RAIL_INSET_RATIO = 0.1
_CAP_EXTENT_RATIO = 0.2


# ── Helpers ───────────────────────────────────────────────────────────────
def to_digits(
    value: int,
    nplaceholders: int,
    base: int = 10,
    pad_zeros: bool = True,
    colors: list[str] | None = None,
) -> list["Number | None"]:
    """Convert *value* to a list of ``Number`` objects in the given *base*."""
    colors = colors or DEFAULT_DIGIT_COLORS
    digits: list[int | None] = [0 if pad_zeros else None] * nplaceholders
    idx = nplaceholders - 1

    if value == 0 and idx >= 0:
        digits[idx] = 0

    while value > 0 and idx >= 0:
        digits[idx] = value % base
        value //= base
        idx -= 1

    return [
        Number(
            chr(ord("A") + d - 10) if isinstance(d, int) and d >= 10 else d,
            colors[(nplaceholders - 1 - i) % len(colors)],
        )
        if d is not None
        else None
        for i, d in enumerate(digits)
    ]


@dataclass
class Number:
    value: int | str
    color: str


class Label(SvgDrawing):
    """
    The label of every room: the number and placeholders
    """

    def __init__(
        self,
        values: list[Number | None],
        font: str = DEFAULT_FONT,
        cell_size: int = 40,
        draw_grid: bool = True,
        line_width: int = 1,
    ):
        self.values = values
        self.font = font
        self.cell_size = cell_size
        self.draw_grid = draw_grid
        self.line_width = line_width

    def get_dimensions(self):
        total_width = len(self.values) * self.cell_size + _LABEL_PADDING * 2
        total_height = self.cell_size + _LABEL_PADDING * 2
        return total_width, total_height

    # alias used by SvgDrawing base
    get_svg_dimensions = get_dimensions

    def to_group(self, offset_x: float = 0, offset_y: float = 0):
        """Returns a drawable group that can be embedded in other drawings."""
        font_size = int(self.cell_size * 0.5)
        g = draw.Group()

        for i, number in enumerate(self.values):
            x = offset_x + _LABEL_PADDING + i * self.cell_size

            if self.draw_grid:
                g.append(
                    draw.Rectangle(
                        x,
                        offset_y + _LABEL_PADDING,
                        self.cell_size,
                        self.cell_size,
                        fill="none",
                        stroke="black",
                        stroke_width=self.line_width,
                    )
                )

            text_x = x + self.cell_size / 2
            text_y = offset_y + _LABEL_PADDING + self.cell_size / 2
            g.append(
                draw.Text(
                    str(number.value) if number is not None else " ",
                    font_size,
                    text_x,
                    text_y,
                    fill=number.color if number is not None else "black",
                    font_family=self.font,
                    text_anchor="middle",
                    dominant_baseline="central",
                )
            )

        return g


class Room(SvgDrawing):
    """
    A single room in the hotel, basically a rectangle with an optional door and a label.
    """

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        values: list[Number | None],
        font: str = DEFAULT_FONT,
        cell_size: int = 40,
        draw_grid: bool = True,
        line_width: int = 2,
        draw_door: bool = True,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.values = values
        self.font = font
        self.cell_size = cell_size
        self.draw_grid = draw_grid
        self.line_width = line_width
        self.draw_door = draw_door

    def get_svg_dimensions(self):
        return self.x + self.width + 10, self.y + self.height + 10

    def to_group(self):
        """Returns a drawable group that can be embedded in other drawings."""
        g = draw.Group()

        g.append(
            draw.Rectangle(
                self.x,
                self.y,
                self.width,
                self.height,
                fill="white",
                stroke="#333333",
                stroke_width=self.line_width,
            )
        )

        door_width = self.width * _DOOR_WIDTH_RATIO
        door_height = self.height * _DOOR_HEIGHT_RATIO
        door_x = self.x + (self.width - door_width) / 2
        door_y = self.y + self.height - door_height

        label = Label(
            self.values,
            font=self.font,
            cell_size=self.cell_size,
            draw_grid=self.draw_grid,
            line_width=self.line_width,
        )
        label_width, label_height = label.get_dimensions()
        label_x = self.x + (self.width - label_width) / 2
        if self.draw_door:
            label_y = door_y - label_height - _LABEL_DOOR_GAP
        else:
            label_y = self.y + (self.height - label_height) / 2

        g.append(label.to_group(offset_x=label_x, offset_y=label_y))

        if self.draw_door:
            g.append(
                draw.Rectangle(
                    door_x,
                    door_y,
                    door_width,
                    door_height,
                    fill=_DOOR_WOOD_COLOR,
                    stroke="none",
                )
            )
            g.append(
                draw.Rectangle(
                    door_x + _DOOR_FRAME_THICKNESS,
                    door_y + _DOOR_FRAME_THICKNESS,
                    door_width - _DOOR_FRAME_THICKNESS * 2,
                    door_height - _DOOR_FRAME_THICKNESS * 2,
                    fill="white",
                    stroke="none",
                )
            )

        return g


class Floor(SvgDrawing):
    """
    A collection of contiguous rooms forming a floor in the hotel.
    """

    def __init__(
        self,
        x: float,
        y: float,
        nplaceholders: int,
        room_width: float = 100,
        room_height: float = 200,
        offset: int = 0,
        base: int = 10,
        pad_zeros: bool = True,
        draw_label_grid: bool = True,
        line_width: int = 1,
        draw_door: bool = True,
        cell_size: int = 40,
        colors: list[str] | None = None,
    ):
        self.x = x
        self.y = y
        self.room_width = room_width
        self.room_height = room_height
        self.base = base
        self.nplaceholders = nplaceholders
        self.pad_zeros = pad_zeros
        self.draw_label_grid = draw_label_grid
        self.line_width = line_width
        self.draw_door = draw_door
        self.cell_size = cell_size
        self.offset = offset
        self.colors = colors or DEFAULT_DIGIT_COLORS

    def get_svg_dimensions(self):
        return (
            self.x + self.base * self.room_width + 10,
            self.y + self.room_height + 10,
        )

    def to_group(self):
        """Returns a drawable group of contiguous rooms."""
        g = draw.Group()

        for i in range(self.base):
            room_x = self.x + i * self.room_width
            values = to_digits(
                i + self.offset,
                self.nplaceholders,
                base=self.base,
                pad_zeros=self.pad_zeros,
                colors=self.colors,
            )

            room = Room(
                x=room_x,
                y=self.y,
                width=self.room_width,
                height=self.room_height,
                values=values,
                cell_size=self.cell_size,
                draw_grid=self.draw_label_grid,
                line_width=self.line_width,
                draw_door=self.draw_door,
            )
            g.append(room.to_group())

        return g


class Building(SvgDrawing):
    """
    A collection of stacked floors forming the hotel building.
    """

    def __init__(
        self,
        x: float,
        y: float,
        nplaceholders: int,
        nfloors: int,
        cell_size: int = 40,
        room_width: float = None,
        room_height: float = 200,
        base: int = 10,
        pad_zeros: bool = True,
        line_width: int = 1,
        ladder_line_width: int = 3,
        draw_door: bool = True,
        draw_grid_line: bool = True,
        without_offset: bool = False,
    ):
        self.x = x
        self.y = y
        self.nfloors = nfloors
        self.room_width = (
            room_width
            if room_width is not None
            else max(80, nplaceholders * cell_size + 24)
        )
        self.room_height = room_height
        self.base = base
        self.nplaceholders = nplaceholders
        self.pad_zeros = pad_zeros
        self.line_width = line_width
        self.draw_door = draw_door
        self.cell_size = cell_size
        self.draw_grid_line = draw_grid_line
        self.ladders: list[Ladder] = []
        self.ladder_line_width = ladder_line_width
        self.without_offset = without_offset

    def get_svg_dimensions(self):
        return (
            self.x + self.base * self.room_width + 10,
            self.y + self.nfloors * self.room_height + 10,
        )

    def to_group(self):
        """Returns a drawable group of stacked floors."""
        g = draw.Group()

        for floor_num in range(self.nfloors):
            floor_y = self.y + (self.nfloors - 1 - floor_num) * self.room_height
            floor_offset = 0 if self.without_offset else floor_num * self.base

            floor = Floor(
                x=self.x,
                y=floor_y,
                room_width=self.room_width,
                room_height=self.room_height,
                base=self.base,
                offset=floor_offset,
                nplaceholders=self.nplaceholders,
                pad_zeros=self.pad_zeros,
                draw_label_grid=self.draw_grid_line,
                line_width=self.line_width,
                draw_door=self.draw_door,
                cell_size=self.cell_size,
            )
            g.append(floor.to_group())

        for ladder in self.ladders:
            g.append(ladder.to_group())

        return g

    def add_ladder(
        self,
        floor_num: int,
        room_num: int,
        color: str = "red",
        width: float = 0.3,
        height: int = 1,
        rung_spacing: float = 40,
    ) -> "Building":
        """Add a ladder at the specified floor and room position."""
        ladder_width = self.room_width * width
        ladder_x = (
            self.x + room_num * self.room_width + self.room_width - ladder_width / 2
        )
        ladder_y = self.y + (self.nfloors - floor_num - height) * self.room_height

        self.ladders.append(
            Ladder(
                x=ladder_x,
                y=ladder_y,
                width=ladder_width,
                height=self.room_height * height,
                line_width=self.ladder_line_width,
                color=color,
                rung_spacing=rung_spacing,
            )
        )
        return self


class Ladder(SvgDrawing):
    """
    A simple ladder.
    """

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        line_width: int = 3,
        color: str = "red",
        rung_spacing: float = 20,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.line_width = line_width
        self.color = color
        self.rung_spacing = rung_spacing

    def get_svg_dimensions(self):
        return self.x + self.width + 10, self.y + self.height + 10

    def to_group(self):
        """Returns a drawable group representing a ladder."""
        g = draw.Group()

        rail_inset = self.width * _RAIL_INSET_RATIO
        left_rail_x = self.x + rail_inset
        right_rail_x = self.x + self.width - rail_inset
        cap_extent = self.width * _CAP_EXTENT_RATIO
        rail_width = self.line_width + 1

        for rail_x in (left_rail_x, right_rail_x):
            # Vertical rail
            g.append(
                draw.Line(
                    rail_x,
                    self.y,
                    rail_x,
                    self.y + self.height,
                    stroke=self.color,
                    stroke_width=rail_width,
                )
            )
            # Top and bottom caps
            for cap_y in (self.y, self.y + self.height):
                g.append(
                    draw.Line(
                        rail_x - cap_extent,
                        cap_y,
                        rail_x + cap_extent,
                        cap_y,
                        stroke=self.color,
                        stroke_width=rail_width,
                    )
                )

        # Horizontal rungs
        num_rungs = max(3, int(self.height / self.rung_spacing))
        spacing = self.height / (num_rungs + 1)

        for i in range(1, num_rungs + 1):
            rung_y = self.y + i * spacing
            g.append(
                draw.Line(
                    left_rail_x,
                    rung_y,
                    right_rail_x,
                    rung_y,
                    stroke=self.color,
                    stroke_width=self.line_width,
                )
            )
        return g

    def to_svg(
        self,
        top_label: "Label | None" = None,
        bottom_label: "Label | None" = None,
        annotation: str | None = None,
        font_size: int = 20,
        font: str = DEFAULT_FONT,
        annotation_gap: float = 16,
    ) -> draw.Drawing:
        return draw_ladders(
            [(self, annotation)],
            top_label=top_label,
            bottom_label=bottom_label,
            font_size=font_size,
            font=font,
            annotation_gap=annotation_gap,
        )


def draw_ladders(
    entries: list[tuple["Ladder", str | None]],
    top_label: "Label | None" = None,
    bottom_label: "Label | None" = None,
    font_size: int = 20,
    font: str = DEFAULT_FONT,
    annotation_gap: float = 16,
) -> draw.Drawing:
    """
    Draw one or more stacked ladders with optional top/bottom Labels and
    per-ladder side annotations.

    entries  – list of (Ladder, annotation_text) pairs, bottom ladder first.
    """
    margin = 10
    label_gap = 8

    max_w = max(ladder.width for ladder, _ in entries)
    total_ladder_h = sum(ladder.height for ladder, _ in entries)

    top_h = 0
    if top_label is not None:
        _, top_h = top_label.get_dimensions()
        top_h += label_gap

    bot_h = 0
    if bottom_label is not None:
        _, bot_h = bottom_label.get_dimensions()
        bot_h += label_gap

    ann_w = max((len(ann) * font_size * 0.6 if ann else 0) for _, ann in entries)
    ann_total = annotation_gap + ann_w if ann_w > 0 else 0

    total_w = margin * 2 + max_w + ann_total
    total_h = margin * 2 + top_h + total_ladder_h + bot_h

    d = draw.Drawing(total_w, total_h)

    current_y = margin

    if top_label is not None:
        lw, lh = top_label.get_dimensions()
        lx = margin + (max_w - lw) / 2
        d.append(top_label.to_group(offset_x=lx, offset_y=current_y))
        current_y += lh + label_gap

    for ladder, annotation in reversed(entries):
        dx = margin + (max_w - ladder.width) / 2 - ladder.x
        dy = current_y - ladder.y
        g = draw.Group(transform=f"translate({dx},{dy})")
        g.append(ladder.to_group())
        d.append(g)

        if annotation:
            ann_x = margin + max_w + annotation_gap
            ann_y = current_y + ladder.height / 2
            d.append(
                draw.Text(
                    annotation,
                    font_size,
                    ann_x,
                    ann_y,
                    font_family=font,
                    fill=ladder.color,
                    text_anchor="start",
                    dominant_baseline="central",
                )
            )

        current_y += ladder.height

    if bottom_label is not None:
        current_y += label_gap
        lw, lh = bottom_label.get_dimensions()
        lx = margin + (max_w - lw) / 2
        d.append(bottom_label.to_group(offset_x=lx, offset_y=current_y))

    return d
