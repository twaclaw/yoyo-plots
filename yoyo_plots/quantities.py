import math
import os

import plotly.graph_objects as go
from plotly.subplots import make_subplots


from .common import (
    svg_to_data_uri,
    resolve_user_path,
    hidden_axis as _hidden_axis,
    resolve_grid_dims as _resolve_grid_dims,
    merge_subplot,
)


def _draw_magic_cell(
    drawing,
    x,
    y,
    cell_size,
    value,
    *,
    fill,
    font_size,
    font_color,
    font_family,
    line_width,
):
    """Append a single grid cell (rectangle + optional centred text) to *drawing*."""
    import drawsvg as draw

    g = draw.Group(transform=f"translate({x},{y})")
    g.append(
        draw.Rectangle(
            0,
            0,
            cell_size,
            cell_size,
            fill=fill,
            stroke="black",
            stroke_width=line_width,
        )
    )
    if value is not None:
        g.append(
            draw.Text(
                str(value),
                font_size,
                cell_size / 2,
                cell_size / 2,
                fill=font_color,
                font_family=font_family,
                text_anchor="middle",
                dominant_baseline="central",
            )
        )
    drawing.append(g)


def plot_quantity(
    image,
    n,
    nrows=1,
    font_size=50,
    save_path=None,
    image_size=0.9,
    font_color="black",
    cols=None,
    center_content=False,
    quantity: str | None = None,
    grid_color: str | None = "black",
    uniform_marker_size: bool = False,
    pixels_per_unit: int = 100,
):
    """
    Generates a plot with two stacked boxes.
    Top box contains n images/emojis in a grid.
    Bottom box contains the handwritten number.

    Parameters:
    - image (str): path to image
    - n (int): Quantity to plot
    - quantity (str | None): Optional string with the quantity to display (default to n if not present)
    - nrows (int): Number of rows for the grid (target height if valid)
    - font_size (int): Font size for the number
    - save_path (str): Optional path to save output
    - image_size (float): Size of the image relative to grid cell (0-1)
    - font_color (str): Color of the number
    - cols (int): Optional fixed number of columns (overrides auto-calculation)
    - center_content (bool): If True, centers the items grid within the available box width.
    - uniform_marker_size (bool): If True, disables automatic scaling for small counts (n=1, 2) to keep icon size consistent.
    - pixels_per_unit (int): Controls the output figure size; higher values produce a larger figure. Defaults to 100.
    """
    fig = go.Figure()

    grid_cols, grid_rows = _resolve_grid_dims(n, nrows, cols)

    cell_size = 1.0

    bottom_padding = -0.15
    top_padding = 0.5

    top_box_width = grid_cols * cell_size
    top_box_height = grid_rows * cell_size + bottom_padding + top_padding

    # Draw Top Box (Upper part)
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=top_box_width,
        y1=top_box_height,
        line=dict(color=grid_color, width=2),
        fillcolor="white",
        layer="below",
    )

    if isinstance(image, str):
        image = resolve_user_path(image)
        if image.lower().endswith(".svg") and os.path.exists(image):
            image = svg_to_data_uri(image)

    x_shift = 0.0
    if center_content:
        if n >= grid_cols:
            filled_cols = grid_cols
        else:
            filled_cols = max(1, n)

        content_width = filled_cols * cell_size
        x_shift = (top_box_width - content_width) / 2.0

    if n > 0:
        actual_rows_used = (n - 1) // grid_cols + 1
    else:
        actual_rows_used = 0

    content_height = actual_rows_used * cell_size
    y_start = (top_box_height + content_height) / 2.0

    # Scale single images up to fill the space
    effective_image_size = image_size
    if not uniform_marker_size:
        if n == 1:
            effective_image_size = image_size * 2.0
        elif n == 2:
            effective_image_size = image_size * 1.25
    img_dim = cell_size * effective_image_size

    for i in range(n):
        row = i // grid_cols
        col = i % grid_cols

        cx = col * cell_size + cell_size / 2 + x_shift
        cy = y_start - (row * cell_size + cell_size / 2.0)

        fig.add_layout_image(
            source=image,
            x=cx,
            y=cy,
            sizex=img_dim,
            sizey=img_dim,
            xanchor="center",
            yanchor="middle",
            xref="x",
            yref="y",
            layer="above",
        )

    bottom_box_height = 1.5

    fig.add_shape(
        type="rect",
        x0=0,
        y0=-bottom_box_height,
        x1=top_box_width,
        y1=0,
        line=dict(color=grid_color, width=2),
        fillcolor="white",
        layer="below",
    )

    # Add Number
    # Force quantity if provided
    number = n if quantity is None else quantity
    text_content = "" if font_color == "white" else str(number)
    fig.add_annotation(
        x=top_box_width / 2,
        y=-bottom_box_height / 2,
        text=text_content,
        showarrow=False,
        font=dict(family="Chalkboard SE", size=font_size, color=font_color),
        xref="x",
        yref="y",
    )

    y_min = -bottom_box_height
    y_max = top_box_height
    x_max = top_box_width

    view_margin = 0.05
    margin_px = 5

    total_width_px = max(
        100, int((x_max + 2 * view_margin) * pixels_per_unit) + 2 * margin_px
    )
    total_height_px = max(
        100, int((y_max - y_min + 2 * view_margin) * pixels_per_unit) + 2 * margin_px
    )

    fig.update_layout(
        xaxis=_hidden_axis(range=[-view_margin, x_max + view_margin], fixedrange=True),
        yaxis=_hidden_axis(
            range=[y_min - view_margin, y_max + view_margin],
            fixedrange=True,
            scaleanchor="x",
            scaleratio=1,
        ),
        plot_bgcolor="white",
        margin=dict(l=margin_px, r=margin_px, t=margin_px, b=margin_px),
        height=total_height_px,
        width=total_width_px,
        dragmode="pan",
    )

    if save_path:
        fig.write_image(save_path)

    return fig


def draw_magic_square(
    grid: list[list[int]],
    highlight: list[tuple[int, int]] | None = None,
    highlight_color: str = "pink",
    font_size: int = 28,
    font_color: str = "black",
    font_family: str = "Comic Sans MS",
    cell_size: int = 48,
    line_width: int = 2,
    save_path=None,
):
    """
    Draws a magic square grid using drawsvg.

    Parameters:
    - grid: 2D list of integers representing the magic square.
    - highlight: List of (row, col) tuples whose cells get a colored background.
    - highlight_color: Background color for highlighted cells.
    - font_size: Font size for the numbers.
    - font_color: Color of the numbers.
    - font_family: Font family for the numbers.
    - cell_size: Size of each cell in pixels.
    - line_width: Width of the grid lines.
    - save_path: Optional path to save the figure as an SVG file.
    """
    import drawsvg as draw

    rows = len(grid)
    cols = max(len(r) for r in grid)
    highlight_set = set(highlight) if highlight else set()

    total_w = cols * cell_size
    total_h = rows * cell_size
    d = draw.Drawing(total_w, total_h)

    for r in range(rows):
        for c in range(cols):
            value = grid[r][c] if c < len(grid[r]) else None
            _draw_magic_cell(
                d,
                c * cell_size,
                r * cell_size,
                cell_size,
                value,
                fill=highlight_color if (r, c) in highlight_set else "white",
                font_size=font_size,
                font_color=font_color,
                font_family=font_family,
                line_width=line_width,
            )

    if save_path:
        d.save_svg(save_path)

    return d


def draw_magic_squares_grid(
    grids: list[list[list[int]]],
    highlights: list[list[tuple[int, int]] | None] | None = None,
    highlight_color: str = "pink",
    font_size: int = 28,
    font_color: str = "black",
    font_family: str = "Comic Sans MS",
    cell_size: int = 48,
    line_width: int = 2,
    cols: int = 2,
    spacing: int = 20,
    save_path=None,
):
    """
    Draws a grid of multiple magic squares inside a single unified SVG.
    This avoids complex SVG recombination rules needed by external renderers like VS Code/Quarto.
    """
    import drawsvg as draw

    if not grids:
        return draw.Drawing(1, 1)

    max_rows = max(len(g) for g in grids)
    max_cols = max(max((len(r) for r in g), default=0) for g in grids)

    sq_w = max_cols * cell_size
    sq_h = max_rows * cell_size

    n = len(grids)
    grid_cols = min(n, cols)
    grid_cols = max(1, grid_cols)
    grid_rows = math.ceil(n / grid_cols)

    total_w = grid_cols * sq_w + (grid_cols - 1) * spacing
    total_h = grid_rows * sq_h + (grid_rows - 1) * spacing

    d = draw.Drawing(total_w, total_h)

    if highlights is None:
        highlights = [None] * n
    else:
        # pad if missing
        while len(highlights) < n:
            highlights.append(None)

    for i, grid in enumerate(grids):
        r = i // grid_cols
        c = i % grid_cols
        x_offset = c * (sq_w + spacing)
        y_offset = r * (sq_h + spacing)

        highlight_set = set(highlights[i]) if highlights[i] else set()

        for gr in range(len(grid)):
            for gc in range(len(grid[gr])):
                _draw_magic_cell(
                    d,
                    x_offset + gc * cell_size,
                    y_offset + gr * cell_size,
                    cell_size,
                    grid[gr][gc],
                    fill=highlight_color if (gr, gc) in highlight_set else "white",
                    font_size=font_size,
                    font_color=font_color,
                    font_family=font_family,
                    line_width=line_width,
                )

    if save_path:
        d.save_svg(save_path)

    return d


def draw_quantity_grid(plot_items, cols=2, save_path=None):
    """
    Creates a grid of quantity plots.

    Parameters:
    - plot_items (list[dict]): List of dictionaries, each containing arguments for plot_quantity.
    - cols (int): Number of columns in the grid.
    - save_path (str): Optional path to save the grid figure.
    """
    if not plot_items:
        return go.Figure()

    for item in plot_items:
        if "image" not in item:
            item["image"] = "❓"

        if isinstance(item["image"], str) and not item["image"].startswith("❓"):
            item["image"] = resolve_user_path(item["image"])

    max_grid_cols = 0
    max_grid_rows = 0

    for item in plot_items:
        c, r = _resolve_grid_dims(
            item.get("n", 0), item.get("nrows", 1), item.get("cols")
        )
        max_grid_cols = max(max_grid_cols, c)
        max_grid_rows = max(max_grid_rows, r)

    count = len(plot_items)
    rows = math.ceil(count / cols)

    fig = make_subplots(
        rows=rows, cols=cols, horizontal_spacing=0.010, vertical_spacing=0.010
    )

    max_w = 0
    max_h = 0

    for idx, item_args in enumerate(plot_items):
        r = (idx // cols) + 1
        c = (idx % cols) + 1

        call_args = item_args.copy()
        call_args["cols"] = max_grid_cols
        call_args["nrows"] = max_grid_rows
        # When forcing widths in a grid, we usually want centered content for aesthetics
        call_args["center_content"] = True

        sub_fig = plot_quantity(**call_args)

        max_w = max(max_w, sub_fig.layout.width or 0)
        max_h = max(max_h, sub_fig.layout.height or 0)

        merge_subplot(fig, sub_fig, row=r, col=c, total_cols=cols)

    fig.update_layout(
        width=max_w * cols + 10,
        height=max_h * rows + 10,
        plot_bgcolor="white",
        dragmode="pan",
        margin=dict(l=5, r=5, t=5, b=5),
    )

    if save_path:
        fig.write_image(save_path)

    return fig


def draw_handwritten_range(
    numbers: list[int],
    font_size=50,
    rows=1,
    font_color="black",
    first_element_color=None,
    append_comma: bool = False,
    add_ellipsis: bool = False,
    save_path=None,
):
    """
    Draws a list of numbers (or items) in a handwritten style.

    Parameters:
    - numbers (list): List of numbers/items to draw
    - font_size (int): Size of the font
    - rows (int): Number of rows to distribute the numbers
    - font_color (str): Default color for the numbers
    - first_element_color (str): Color for the first element. Defaults to font_color.
    - save_path (str): Optional path to save the figure as SVG.

    Returns a plotly.graph_objects.Figure
    """
    fig = go.Figure()

    if not numbers:
        return fig

    if first_element_color is None:
        first_element_color = font_color

    count = len(numbers)
    effective_count = count + (1 if add_ellipsis else 0)
    cols = (effective_count + rows - 1) // rows

    font_family = "Chalkboard SE"

    # Grid Logic
    row_height = 1.0

    # Scale col_width so the widest item (e.g. "10," vs "1,") always has the same
    # relative padding as a 1-digit item, keeping spacing visually consistent.
    max_item_chars = max(len(str(n)) + (1 if append_comma else 0) for n in numbers)
    if add_ellipsis:
        max_item_chars = max(max_item_chars, 3)  # "..." counts as 3 chars
    # 0.55 data-units per char gives comfortable spacing; floor at 1.0 for short items
    col_width = max(1.0, max_item_chars * 0.55)

    for idx, num in enumerate(numbers):
        row = idx // cols
        col = idx % cols

        x_center = col * col_width
        y_center = -row * row_height

        if idx == 0:
            color = first_element_color
        else:
            color = font_color

        # Add comma if: not the last real element, OR there's an ellipsis following the last element
        needs_comma = append_comma and (idx < count - 1 or add_ellipsis)
        text_content = (
            "" if color == "white" else str(num) + ("," if needs_comma else "")
        )
        fig.add_annotation(
            x=x_center,
            y=y_center,
            text=text_content,
            showarrow=False,
            font=dict(family=font_family, size=font_size, color=color),
            xref="x",
            yref="y",
        )

    if add_ellipsis:
        ellipsis_idx = count
        row = ellipsis_idx // cols
        col = ellipsis_idx % cols
        fig.add_annotation(
            x=col * col_width,
            y=-row * row_height,
            text="...",
            showarrow=False,
            font=dict(family=font_family, size=font_size, color=font_color),
            xref="x",
            yref="y",
        )

    actual_rows = (effective_count + cols - 1) // cols
    actual_cols = min(effective_count, cols)

    x_min = -0.5 * col_width
    x_max = (actual_cols - 0.5) * col_width

    y_max = 0.5 * row_height
    # Extra room for comma/punctuation descenders so they aren't clipped in Quarto
    descender_extra = 0.2 if append_comma or add_ellipsis else 0.0
    y_min = -(actual_rows - 1 + 0.5 + descender_extra) * row_height
    bottom_margin_px = 15 if append_comma or add_ellipsis else 5

    # Update Layout
    fig.update_layout(
        xaxis=_hidden_axis(range=[x_min, x_max], fixedrange=True),
        yaxis=_hidden_axis(
            range=[y_min, y_max], fixedrange=True, scaleanchor="x", scaleratio=1
        ),
        plot_bgcolor="white",
        margin=dict(l=5, r=5, t=5, b=bottom_margin_px),
        height=max(50, int((y_max - y_min) * font_size * 1.6)) + 10,
        width=int(actual_cols * col_width * font_size * 1.5) + 20,
        dragmode="pan",
    )

    if save_path:
        fig.write_image(save_path)

    return fig
