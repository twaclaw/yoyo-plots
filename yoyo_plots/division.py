import math
import random

import drawsvg as draw

from .common import SvgDrawing, embed_svg_image

_FONT = "Comic Sans MS, Comic Sans, Chalkboard SE, Chalkboard, Marker Felt, sans-serif"


def draw_card_back(
    x: float, y: float, width: float = 40, height: float = 60
) -> draw.Group:
    """Draw a basic playing card back."""
    g = draw.Group(transform=f"translate({x}, {y})")

    # Main card body (white background)
    g.append(
        draw.Rectangle(
            0,
            0,
            width,
            height,
            rx=4,
            ry=4,
            fill="white",
            stroke="black",
            stroke_width=1,
        )
    )

    # Inner border
    inner_margin = 4
    iw, ih = width - 2 * inner_margin, height - 2 * inner_margin
    g.append(
        draw.Rectangle(
            inner_margin,
            inner_margin,
            iw,
            ih,
            rx=2,
            ry=2,
            fill="#cc0000",
            stroke="none",
        )
    )

    # A simple pattern inside (e.g. a diamond or cross)
    center_x, center_y = width / 2, height / 2
    g.append(
        draw.Lines(
            center_x,
            inner_margin + 5,
            width - inner_margin - 5,
            center_y,
            center_x,
            height - inner_margin - 5,
            inner_margin + 5,
            center_y,
            close=True,
            fill="#ff6666",
        )
    )

    return g


class CardHolder(SvgDrawing):
    """Draws a character holding a specified number of cards."""

    def __init__(
        self,
        number: int,
        character_image: str | None = None,
        draw_number: bool = False,
        font_size: int = 24,
        font_color: str = "black",
        fold_cards: bool = False,
        card_width: float = 40,
        card_height: float = 60,
        char_width: float = 80,
        char_height: float = 80,
    ):
        self.number = number
        self.character_image = character_image
        self.draw_number = draw_number
        self.font_size = font_size
        self.font_color = font_color
        self.fold_cards = fold_cards
        self.card_width = card_width
        self.card_height = card_height
        self.char_width = char_width
        self.char_height = char_height

        self.spacing = 10
        self.folded_offset = 15

    def _layout(self) -> tuple[float, float, float, float, float, float]:
        """Compute card-stack and bottom-section dimensions.

        Returns ``(w_cards, h_cards, w_bottom, h_bottom, total_w, total_h)``.
        Called by both :meth:`get_svg_dimensions` and :meth:`to_group` so the
        calculation is never duplicated.
        """
        if self.number == 0:
            w_cards, h_cards = 0.0, 0.0
        elif self.fold_cards:
            w_cards = self.card_width + (self.number - 1) * self.folded_offset
            h_cards = self.card_height + (self.number - 1) * self.folded_offset
        else:
            w_cards = self.number * self.card_width + max(0, self.number - 1) * self.spacing
            h_cards = self.card_height

        w_char = self.char_width if self.character_image else 0.0
        h_char = self.char_height if self.character_image else 0.0
        w_num = self.font_size * 1.5 if self.draw_number else 0.0
        h_num = float(self.font_size) if self.draw_number else 0.0

        w_bottom = w_char + (self.spacing if w_char and w_num else 0) + w_num
        h_bottom = max(h_char, h_num)

        total_w = max(w_cards, w_bottom) + self.spacing * 2
        gap = self.spacing if h_cards > 0 and h_bottom > 0 else 0
        total_h = h_cards + gap + h_bottom + self.spacing * 2

        return w_cards, h_cards, w_bottom, h_bottom, total_w, total_h

    def get_svg_dimensions(self) -> tuple[float, float]:
        _, _, _, _, total_w, total_h = self._layout()
        return total_w, total_h

    def to_group(self, **kwargs) -> draw.Group:
        g = draw.Group()
        w_cards, h_cards, w_bottom, h_bottom, total_w, _ = self._layout()

        cards_start_x = (total_w - w_cards) / 2
        cards_start_y = self.spacing

        bottom_start_x = (total_w - w_bottom) / 2
        gap = self.spacing if h_cards > 0 and h_bottom > 0 else 0
        bottom_start_y = self.spacing + h_cards + gap

        if self.number > 0:
            for i in range(self.number):
                if self.fold_cards:
                    cx = cards_start_x + i * self.folded_offset
                    cy = cards_start_y + i * self.folded_offset
                else:
                    cx = cards_start_x + i * (self.card_width + self.spacing)
                    cy = cards_start_y

                g.append(
                    draw_card_back(
                        cx, cy, width=self.card_width, height=self.card_height
                    )
                )

        curr_x = bottom_start_x
        if self.character_image:
            g.append(
                embed_svg_image(
                    self.character_image,
                    curr_x,
                    bottom_start_y,
                    self.char_width,
                    self.char_height,
                )
            )
            curr_x += self.char_width + self.spacing

        if self.draw_number:
            box_sz = self.font_size * 1.5
            text_x = curr_x + box_sz / 2
            text_y = bottom_start_y + h_bottom / 2
            g.append(
                draw.Rectangle(
                    text_x - box_sz / 2,
                    text_y - box_sz / 2,
                    box_sz,
                    box_sz,
                    fill="none",
                    stroke="black",
                    stroke_width=2,
                )
            )

            if self.font_color != "white":
                g.append(
                    draw.Text(
                        str(self.number),
                        self.font_size,
                        text_x,
                        text_y,
                        font_family=_FONT,
                        center=True,
                        dominant_baseline="middle",
                        fill=self.font_color,
                    )
                )

        return g


class CardGame(SvgDrawing):
    """Draws total cards at the top, and a list of CardHolders below, centered side-by-side."""

    def __init__(
        self,
        total: int,
        holders: list[CardHolder] | None = None,
        fold_total: bool = False,
        card_width: float = 40,
        card_height: float = 60,
    ):
        self.total = total
        self.holders = holders or []
        self.fold_total = fold_total
        self.card_width = card_width
        self.card_height = card_height

        self.spacing = 10
        self.folded_offset = 15
        self.row_spacing = 30

    def get_svg_dimensions(self) -> tuple[float, float]:
        if self.total == 0:
            w_top, h_top = 0, 0
        elif self.fold_total:
            w_top = self.card_width + (self.total - 1) * self.folded_offset
            h_top = self.card_height + (self.total - 1) * self.folded_offset
        else:
            w_top = self.total * self.card_width + max(0, self.total - 1) * self.spacing
            h_top = self.card_height

        if not self.holders:
            w_bot, h_bot = 0, 0
        else:
            holder_dims = [h.get_svg_dimensions() for h in self.holders]
            w_bot = sum(d[0] for d in holder_dims) + self.spacing * (
                len(self.holders) - 1
            )
            h_bot = max(d[1] for d in holder_dims)

        total_w = max(w_top, w_bot) + self.spacing * 2
        total_h = (
            h_top
            + h_bot
            + (self.row_spacing if w_top and w_bot else 0)
            + self.spacing * 2
        )
        return total_w, total_h

    def to_group(self, **kwargs) -> draw.Group:
        g = draw.Group()
        total_w, total_h = self.get_svg_dimensions()

        # 1. Total Cards
        if self.total > 0:
            if self.fold_total:
                w_top = self.card_width + (self.total - 1) * self.folded_offset
                h_top = self.card_height + (self.total - 1) * self.folded_offset
            else:
                w_top = (
                    self.total * self.card_width + max(0, self.total - 1) * self.spacing
                )
                h_top = self.card_height
        else:
            w_top = h_top = 0

        top_start_x = (total_w - w_top) / 2
        top_start_y = self.spacing

        for i in range(self.total):
            if self.fold_total:
                cx = top_start_x + i * self.folded_offset
                cy = top_start_y + i * self.folded_offset
            else:
                cx = top_start_x + i * (self.card_width + self.spacing)
                cy = top_start_y
            g.append(
                draw_card_back(cx, cy, width=self.card_width, height=self.card_height)
            )

        # 2. Holders
        if self.holders:
            holder_dims = [h.get_svg_dimensions() for h in self.holders]
            w_bot = sum(d[0] for d in holder_dims) + self.spacing * (
                len(self.holders) - 1
            )
            h_bot = max(d[1] for d in holder_dims)

            bot_start_x = (total_w - w_bot) / 2
            bot_start_y = top_start_y + h_top + (self.row_spacing if h_top else 0)

            curr_x = bot_start_x
            for h, (hw, hh) in zip(self.holders, holder_dims):
                hg = draw.Group(transform=f"translate({curr_x}, {bot_start_y})")
                hg.append(h.to_group())
                g.append(hg)
                curr_x += hw + self.spacing

        return g


class Pizza(SvgDrawing):
    """Draws a pizza divided into equal fractional slices.
    Only `numerator` slices are drawn out of `denominator`."""

    def __init__(
        self,
        numerator: int,
        denominator: int,
        radius: float = 100,
        flavour: str = "margherita",
        division_color: str = "white",
        draw_fraction: bool = False,
        fraction_num: int | None = None,
        fraction_den: int | None = None,
        font_size: int = 36,
        font_color: str = "black",
    ):
        self.numerator = numerator
        self.denominator = denominator
        self.radius = radius
        self.flavour = flavour
        self.division_color = division_color

        self.draw_fraction = draw_fraction
        self.fraction_num = fraction_num
        self.fraction_den = fraction_den
        self.font_size = font_size
        self.font_color = font_color

        # Colors for the flavours
        self.flavours = {
            "margherita": "#F5C754",  # Golden cheese base
            "pepperoni": "#F5C754",  # Golden cheese base
            "marinara": "#DD2A00",  # Tomato red base
            "bianca": "#FEF7E3",  # Creamy beige base
        }

    def get_svg_dimensions(self) -> tuple[float, float]:
        pizza_size = self.radius * 2 + 10  # 5px padding on each side
        if not self.draw_fraction:
            return pizza_size, pizza_size

        box_sz = self.font_size * 1.5
        fraction_h = box_sz * 2 + 20  # 10px spacing around the central line

        total_w = pizza_size + 20 + box_sz  # 20px spacing between pizza and fraction
        total_h = max(pizza_size, fraction_h)
        return total_w, total_h

    def to_group(self, **kwargs) -> draw.Group:
        total_w, total_h = self.get_svg_dimensions()
        g = draw.Group()

        pizza_size = self.radius * 2 + 10
        # Center of the drawing for the pizza
        cx = pizza_size / 2
        cy = total_h / 2

        flavour_color = self.flavours.get(
            self.flavour.lower(), self.flavours["margherita"]
        )

        if self.denominator <= 0:
            return g

        def polar_to_cartesian(cx, cy, r, angle_deg):
            angle_rad = math.radians(angle_deg)
            return cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad)

        angle_per_piece = 360.0 / self.denominator
        start_angle = -90

        def add_texture(group, path_shape, texture_type):
            clip_id = f"clip-{id(self)}-{id(path_shape)}"
            clip = draw.ClipPath(id=clip_id)
            clip.append(path_shape)
            g.append(clip)

            texture_g = draw.Group(clip_path=f"url(#{clip_id})")
            rng = random.Random(hash(self.flavour) + self.numerator + self.denominator)

            texture_g.append(
                draw.Circle(
                    cx,
                    cy,
                    r=self.radius - 8,
                    stroke="#DAA05D",
                    stroke_width=16,
                    fill="none",
                )
            )
            texture_g.append(
                draw.Circle(
                    cx,
                    cy,
                    r=self.radius - 2,
                    stroke="#C37B32",
                    stroke_width=5,
                    fill="none",
                )
            )

            # Universal: Cheese mottling, baked spots, and blisters
            for _ in range(self.numerator * 15):
                r_dist = math.sqrt(rng.uniform(0, 1)) * (
                    self.radius - 15
                )  # keep away from outer crust edge
                theta = rng.uniform(0, 2 * math.pi)
                tx, ty = cx + r_dist * math.cos(theta), cy + r_dist * math.sin(theta)
                r_spot = rng.uniform(2, 6)

                spot_color = rng.choice(["#FFFFFF", "#FFDE75", "#D2691E", "#8B4513"])
                spot_op = rng.uniform(0.2, 0.6)
                if texture_type == "marinara" and spot_color in ["#FFFFFF", "#FFDE75"]:
                    spot_color = (
                        "#8B0000"  # darker tomato sauce spots instead of cheese
                    )

                texture_g.append(
                    draw.Circle(tx, ty, r=r_spot, fill=spot_color, fill_opacity=spot_op)
                )

            # Specific toppings
            if texture_type == "margherita":
                # Molten mozzarella patches (smaller, fewer, blended organically)
                for _ in range(self.numerator * 3):
                    r_dist = math.sqrt(rng.uniform(0, 1)) * (self.radius - 18)
                    theta = rng.uniform(0, 2 * math.pi)
                    tx, ty = (
                        cx + r_dist * math.cos(theta),
                        cy + r_dist * math.sin(theta),
                    )
                    # Soft melted edge
                    texture_g.append(
                        draw.Ellipse(
                            tx,
                            ty,
                            rx=rng.uniform(5, 10),
                            ry=rng.uniform(4, 9),
                            fill="#FFFDF0",
                            fill_opacity=0.6,
                        )
                    )
                    # Brighter cheese core
                    texture_g.append(
                        draw.Ellipse(
                            tx + rng.uniform(-1, 1),
                            ty + rng.uniform(-1, 1),
                            rx=rng.uniform(2, 5),
                            ry=rng.uniform(2, 4),
                            fill="#FFFFFF",
                            fill_opacity=0.85,
                        )
                    )

            elif texture_type == "pepperoni":
                for _ in range(self.numerator * 4):
                    r_dist = math.sqrt(rng.uniform(0, 1)) * (
                        self.radius - 22
                    )  # stay well within crust
                    theta = rng.uniform(0, 2 * math.pi)
                    tx, ty = (
                        cx + r_dist * math.cos(theta),
                        cy + r_dist * math.sin(theta),
                    )
                    texture_g.append(
                        draw.Circle(
                            tx,
                            ty,
                            r=rng.uniform(9, 12),
                            fill="#C92A2A",
                            stroke="#800000",
                            stroke_width=1,
                        )
                    )
                    # Little fat bubbles / reflections in the pepperoni
                    for __ in range(rng.randint(3, 7)):
                        ox, oy = tx + rng.uniform(-6, 6), ty + rng.uniform(-6, 6)
                        texture_g.append(
                            draw.Circle(
                                ox,
                                oy,
                                r=rng.uniform(0.5, 1.5),
                                fill="#FFA07A",
                                fill_opacity=0.7,
                            )
                        )

            elif texture_type == "marinara":
                for _ in range(self.numerator * 8):
                    r_dist = math.sqrt(rng.uniform(0, 1)) * (self.radius - 15)
                    theta = rng.uniform(0, 2 * math.pi)
                    tx, ty = (
                        cx + r_dist * math.cos(theta),
                        cy + r_dist * math.sin(theta),
                    )
                    if rng.random() > 0.3:
                        # Oregano specks
                        texture_g.append(
                            draw.Circle(
                                tx,
                                ty,
                                r=rng.uniform(0.5, 1.5),
                                fill="#4B5320",
                                fill_opacity=0.9,
                            )
                        )
                    else:
                        # Garlic slices
                        texture_g.append(
                            draw.Circle(
                                tx,
                                ty,
                                r=rng.uniform(2, 4),
                                fill="#FFFDE7",
                                fill_opacity=0.8,
                                stroke="#E0E0E0",
                                stroke_width=0.5,
                            )
                        )

            elif texture_type == "bianca":
                for _ in range(self.numerator * 6):
                    r_dist = math.sqrt(rng.uniform(0, 1)) * (self.radius - 20)
                    theta = rng.uniform(0, 2 * math.pi)
                    tx, ty = (
                        cx + r_dist * math.cos(theta),
                        cy + r_dist * math.sin(theta),
                    )
                    # Glob of ricotta/soft cheese
                    texture_g.append(
                        draw.Circle(
                            tx,
                            ty,
                            r=rng.uniform(5, 12),
                            fill="#FFFFFF",
                            fill_opacity=0.95,
                            stroke="#FAF0E6",
                            stroke_width=1.5,
                        )
                    )

            group.append(texture_g)

        # To avoid overlaps and drawing a full circle with lines when numerator == denominator
        if self.numerator >= self.denominator:
            base_circle = draw.Circle(cx, cy, self.radius, fill=flavour_color)
            g.append(base_circle)
            add_texture(
                g, draw.Circle(cx, cy, self.radius, fill="none"), self.flavour.lower()
            )

            # Draw division lines
            for i in range(self.denominator):
                angle = start_angle + i * angle_per_piece
                px, py = polar_to_cartesian(cx, cy, self.radius, angle)
                g.append(
                    draw.Line(
                        cx, cy, px, py, stroke=self.division_color, stroke_width=2
                    )
                )

            # Outer crust/border
            g.append(
                draw.Circle(
                    cx,
                    cy,
                    self.radius,
                    fill="none",
                    stroke=self.division_color,
                    stroke_width=2,
                )
            )

        else:
            # First, draw the outlines for ALL slices (even the empty ones)
            for i in range(self.denominator):
                angle = start_angle + i * angle_per_piece
                px, py = polar_to_cartesian(cx, cy, self.radius, angle)
                # Outer crust/border line segment
                angle_next = start_angle + (i + 1) * angle_per_piece
                x1, y1 = polar_to_cartesian(cx, cy, self.radius, angle)
                x2, y2 = polar_to_cartesian(cx, cy, self.radius, angle_next)

                # Draw the empty slice outline to make the grid visible
                empty_path = draw.Path(
                    fill="none", stroke=self.division_color, stroke_width=2
                )
                empty_path.M(cx, cy)
                empty_path.L(x1, y1)
                empty_path.A(
                    self.radius,
                    self.radius,
                    0,
                    1 if angle_per_piece > 180 else 0,
                    1,
                    x2,
                    y2,
                )
                empty_path.Z()
                g.append(empty_path)

            # Then, draw and fill the actual numerator slices
            for i in range(self.numerator):
                current_start = start_angle + i * angle_per_piece
                current_end = current_start + angle_per_piece

                x1, y1 = polar_to_cartesian(cx, cy, self.radius, current_start)
                x2, y2 = polar_to_cartesian(cx, cy, self.radius, current_end)

                large_arc = 1 if angle_per_piece > 180 else 0

                path = draw.Path(
                    fill=flavour_color, stroke=self.division_color, stroke_width=2
                )
                path.M(cx, cy)
                path.L(x1, y1)
                path.A(self.radius, self.radius, 0, large_arc, 1, x2, y2)
                path.Z()

                g.append(path)

                # Add texture independently for each slice for clipping simplification
                # Create a pure path without stroke for clipping
                clip_path = draw.Path(fill="none")
                clip_path.M(cx, cy)
                clip_path.L(x1, y1)
                clip_path.A(self.radius, self.radius, 0, large_arc, 1, x2, y2)
                clip_path.Z()

                add_texture(g, clip_path, self.flavour.lower())

        if self.draw_fraction:
            box_sz = self.font_size * 1.5
            frac_x = pizza_size + 20 + box_sz / 2

            # top box
            g.append(
                draw.Rectangle(
                    frac_x - box_sz / 2,
                    cy - 10 - box_sz,
                    box_sz,
                    box_sz,
                    fill="none",
                    stroke="black",
                    stroke_width=2,
                )
            )

            # bottom box
            g.append(
                draw.Rectangle(
                    frac_x - box_sz / 2,
                    cy + 10,
                    box_sz,
                    box_sz,
                    fill="none",
                    stroke="black",
                    stroke_width=2,
                )
            )

            # Line
            g.append(
                draw.Line(
                    frac_x - box_sz / 2 - 5,
                    cy,
                    frac_x + box_sz / 2 + 5,
                    cy,
                    stroke="black",
                    stroke_width=2,
                )
            )

            if self.font_color != "white":
                num_v = (
                    self.numerator if self.fraction_num is None else self.fraction_num
                )
                den_v = (
                    self.denominator if self.fraction_den is None else self.fraction_den
                )

                g.append(
                    draw.Text(
                        str(num_v),
                        self.font_size,
                        frac_x,
                        cy - 10 - box_sz / 2,
                        font_family=_FONT,
                        center=True,
                        dominant_baseline="middle",
                        fill=self.font_color,
                    )
                )
                g.append(
                    draw.Text(
                        str(den_v),
                        self.font_size,
                        frac_x,
                        cy + 10 + box_sz / 2,
                        font_family=_FONT,
                        center=True,
                        dominant_baseline="middle",
                        fill=self.font_color,
                    )
                )

        return g
