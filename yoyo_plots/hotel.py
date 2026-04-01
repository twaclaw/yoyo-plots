from dataclasses import dataclass

import drawsvg as draw


@dataclass
class Number:
    value: int | str
    color: str


class Label:
    """
    The label of every room: the number and placeholders
    """

    def __init__(
        self,
        values: list[Number | None],
        font: str = "Comic Sans MS",
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
        padding = 4
        total_width = len(self.values) * self.cell_size + padding * 2
        total_height = self.cell_size + padding * 2
        return total_width, total_height

    def to_group(self, offset_x: float = 0, offset_y: float = 0):
        """Returns a drawable group that can be embedded in other drawings."""
        padding = 4
        font_size = int(self.cell_size * 0.5)

        g = draw.Group()

        for i, number in enumerate(self.values):
            x = offset_x + padding + i * self.cell_size

            if self.draw_grid:
                g.append(
                    draw.Rectangle(
                        x,
                        offset_y + padding,
                        self.cell_size,
                        self.cell_size,
                        fill="none",
                        stroke="black",
                        stroke_width=self.line_width,
                    )
                )

            text_x = x + self.cell_size / 2
            text_y = offset_y + padding + self.cell_size / 2
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

    def to_svg(self):
        total_width, total_height = self.get_dimensions()
        d = draw.Drawing(total_width, total_height)
        d.append(self.to_group())
        return d.as_svg()


class Room:
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
        font: str = "Comic Sans MS",
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

        door_width = self.width * 0.5
        door_height = self.height * 0.6
        door_x = self.x + (self.width - door_width) / 2
        door_y = self.y + self.height - door_height

        label_door_gap = 6

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
            label_y = door_y - label_height - label_door_gap
        else:
            label_y = self.y + (self.height - label_height) / 2

        g.append(label.to_group(offset_x=label_x, offset_y=label_y))

        if self.draw_door:
            frame_thickness = 3
            wood_color = "#DEB887"  # hardcoded wood color

            g.append(
                draw.Rectangle(
                    door_x,
                    door_y,
                    door_width,
                    door_height,
                    fill=wood_color,
                    stroke="none",
                )
            )

            interior_width = door_width - frame_thickness * 2
            interior_height = door_height - frame_thickness * 2
            g.append(
                draw.Rectangle(
                    door_x + frame_thickness,
                    door_y + frame_thickness,
                    interior_width,
                    interior_height,
                    fill="white",
                    stroke="none",
                )
            )

        return g

    def to_svg(self):
        d = draw.Drawing(self.x + self.width + 10, self.y + self.height + 10)
        d.append(self.to_group())
        return d.as_svg()


class Floor:
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

    def to_digits(self, value: int, colors: list[str]) -> list[Number]:
        """Converts in the given base"""
        digits = [0 if self.pad_zeros else None] * self.nplaceholders
        idx = self.nplaceholders - 1

        if value == 0 and idx >= 0:
            digits[idx] = 0

        while value > 0 and idx >= 0:
            digits[idx] = value % self.base
            value //= self.base
            idx -= 1
        return [
            Number(
                chr(ord('A') + d - 10) if isinstance(d, int) and d >= 10 else d,
                colors[(self.nplaceholders - 1 - i) % len(colors)],
            )
            if d is not None
            else None
            for i, d in enumerate(digits)
        ]

    def to_group(self):
        """Returns a drawable group of contiguous rooms."""
        g = draw.Group()

        colors = [
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

        for i in range(self.base):
            room_x = self.x + i * self.room_width
            values = self.to_digits(i + self.offset, colors)

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

    def to_svg(self):
        total_width = self.x + self.base * self.room_width + 10
        total_height = self.y + self.room_height + 10
        d = draw.Drawing(total_width, total_height)
        d.append(self.to_group())
        return d.as_svg()


class Building:
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
        self.ladders = []
        self.ladder_line_width = ladder_line_width
        self.without_offset = without_offset

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

        # Draw all ladders
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
    ):
        """Add a ladder at the specified floor and room position."""
        ladder_width = self.room_width * width
        ladder_x = (
            self.x + room_num * self.room_width + self.room_width - ladder_width / 2
        )
        ladder_y = self.y + (self.nfloors - floor_num - height) * self.room_height

        ladder = Ladder(
            x=ladder_x,
            y=ladder_y,
            width=ladder_width,
            height=self.room_height * height,
            line_width=self.ladder_line_width,
            color=color,
            rung_spacing=rung_spacing,
        )
        self.ladders.append(ladder)

    def to_svg(self):
        total_width = self.x + self.base * self.room_width + 10
        total_height = self.y + self.nfloors * self.room_height + 10
        d = draw.Drawing(total_width, total_height)
        d.append(self.to_group())
        return d.as_svg()


class Ladder:
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

    def to_group(self):
        """Returns a drawable group representing a ladder."""
        g = draw.Group()

        # Two vertical rails
        rail_inset = self.width * 0.1
        left_rail_x = self.x + rail_inset
        right_rail_x = self.x + self.width - rail_inset
        cap_extent = self.width * 0.2

        for rail_x in (left_rail_x, right_rail_x):
            g.append(
                draw.Line(
                    rail_x,
                    self.y,
                    rail_x,
                    self.y + self.height,
                    stroke=self.color,
                    stroke_width=self.line_width + 1,
                )
            )
            # Top cap (T shape)
            g.append(
                draw.Line(
                    rail_x - cap_extent,
                    self.y,
                    rail_x + cap_extent,
                    self.y,
                    stroke=self.color,
                    stroke_width=self.line_width + 1,
                )
            )
            # Bottom cap (inverted T shape)
            g.append(
                draw.Line(
                    rail_x - cap_extent,
                    self.y + self.height,
                    rail_x + cap_extent,
                    self.y + self.height,
                    stroke=self.color,
                    stroke_width=self.line_width + 1,
                )
            )

        # Horizontal rungs
        num_rungs = max(3, int(self.height / self.rung_spacing))
        rung_spacing = self.height / (num_rungs + 1)

        for i in range(1, num_rungs + 1):
            rung_y = self.y + i * rung_spacing
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
        font: str = "Comic Sans MS",
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
    font: str = "Comic Sans MS",
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
