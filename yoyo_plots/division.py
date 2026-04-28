import math
import os
import drawsvg as draw

from .common import SvgDrawing, strip_svg_header, resolve_user_path, svg_to_data_uri

def draw_card_back(x: float, y: float, width: float = 40, height: float = 60) -> draw.Group:
    """Draw a basic playing card back."""
    g = draw.Group(transform=f"translate({x}, {y})")
    
    # Main card body (white background)
    g.append(draw.Rectangle(0, 0, width, height, rx=4, ry=4, fill="white", stroke="black", stroke_width=1))
    
    # Inner border
    inner_margin = 4
    iw, ih = width - 2 * inner_margin, height - 2 * inner_margin
    g.append(draw.Rectangle(inner_margin, inner_margin, iw, ih, rx=2, ry=2, fill="#cc0000", stroke="none"))
    
    # A simple pattern inside (e.g. a diamond or cross)
    center_x, center_y = width / 2, height / 2
    g.append(draw.Lines(
        center_x, inner_margin + 5,
        width - inner_margin - 5, center_y,
        center_x, height - inner_margin - 5,
        inner_margin + 5, center_y,
        close=True, fill="#ff6666"
    ))
    
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

    def get_svg_dimensions(self) -> tuple[float, float]:
        if self.number == 0:
            w_cards = 0
            h_cards = 0
        elif self.fold_cards:
            w_cards = self.card_width + (self.number - 1) * self.folded_offset
            h_cards = self.card_height + (self.number - 1) * self.folded_offset
        else:
            w_cards = self.number * self.card_width + max(0, self.number - 1) * self.spacing
            h_cards = self.card_height
        
        w_char = self.char_width if self.character_image else 0
        h_char = self.char_height if self.character_image else 0
        w_num = self.font_size * 1.5 if self.draw_number else 0
        h_num = self.font_size if self.draw_number else 0
        
        w_bottom = w_char + (self.spacing if w_char and w_num else 0) + w_num
        h_bottom = max(h_char, h_num)
        
        total_w = max(w_cards, w_bottom) + self.spacing * 2
        
        spacing_between_rows = self.spacing if h_cards > 0 and h_bottom > 0 else 0
        total_h = h_cards + spacing_between_rows + h_bottom + self.spacing * 2
        
        return total_w, total_h

    def to_group(self, **kwargs) -> draw.Group:
        g = draw.Group()
        total_w, _ = self.get_svg_dimensions()
        
        if self.number == 0:
            w_cards = 0
            h_cards = 0
        elif self.fold_cards:
            w_cards = self.card_width + (self.number - 1) * self.folded_offset
            h_cards = self.card_height + (self.number - 1) * self.folded_offset
        else:
            w_cards = self.number * self.card_width + max(0, self.number - 1) * self.spacing
            h_cards = self.card_height
            
        w_char = self.char_width if self.character_image else 0
        h_char = self.char_height if self.character_image else 0
        w_num = self.font_size * 1.5 if self.draw_number else 0
        h_num = self.font_size if self.draw_number else 0
        
        w_bottom = w_char + (self.spacing if w_char and w_num else 0) + w_num
        h_bottom = max(h_char, h_num)
        
        cards_start_x = (total_w - w_cards) / 2
        cards_start_y = self.spacing
        
        bottom_start_x = (total_w - w_bottom) / 2
        spacing_between_rows = self.spacing if h_cards > 0 and w_bottom > 0 else 0
        bottom_start_y = self.spacing + h_cards + spacing_between_rows
        
        if self.number > 0:
            for i in range(self.number):
                if self.fold_cards:
                    cx = cards_start_x + i * self.folded_offset
                    cy = cards_start_y + i * self.folded_offset
                else:
                    cx = cards_start_x + i * (self.card_width + self.spacing)
                    cy = cards_start_y
                    
                g.append(draw_card_back(cx, cy, width=self.card_width, height=self.card_height))
                
        curr_x = bottom_start_x
        if self.character_image:
            image_src = self.character_image
            if not image_src.lstrip().startswith("<svg"):
                if not image_src.startswith("data:"):
                    resolved = resolve_user_path(image_src)
                    if hasattr(resolved, "lower") and resolved.lower().endswith(".svg"):
                        image_src = svg_to_data_uri(resolved)
                    else:
                        image_src = resolved

            g.append(draw.Image(
                curr_x, bottom_start_y,
                self.char_width, self.char_height,
                image_src
            ))
            curr_x += self.char_width + self.spacing
            
        if self.draw_number:
            text_x = curr_x + w_num / 2
            text_y = bottom_start_y + h_bottom / 2
            
            box_sz = self.font_size * 1.5
            g.append(draw.Rectangle(
                text_x - box_sz / 2, text_y - box_sz / 2,
                box_sz, box_sz,
                fill="none", stroke="black", stroke_width=2
            ))
            
            if self.font_color != "white":
                g.append(draw.Text(
                    str(self.number),
                    self.font_size,
                    text_x, text_y,
                    font_family="Comic Sans MS, Comic Sans, cursive",
                    center=True,
                    dominant_baseline="middle",
                    fill=self.font_color
                ))
            
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
            w_bot = sum(d[0] for d in holder_dims) + self.spacing * (len(self.holders) - 1)
            h_bot = max(d[1] for d in holder_dims)

        total_w = max(w_top, w_bot) + self.spacing * 2
        total_h = h_top + h_bot + (self.row_spacing if w_top and w_bot else 0) + self.spacing * 2
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
                w_top = self.total * self.card_width + max(0, self.total - 1) * self.spacing
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
            g.append(draw_card_back(cx, cy, width=self.card_width, height=self.card_height))

        # 2. Holders
        if self.holders:
            holder_dims = [h.get_svg_dimensions() for h in self.holders]
            w_bot = sum(d[0] for d in holder_dims) + self.spacing * (len(self.holders) - 1)
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
