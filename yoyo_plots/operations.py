from plotly.subplots import make_subplots

from soroban import Soroban

from .quantities import plot_quantity
from .common import (
    hidden_axis as _hidden_axis,
    resolve_grid_dims as _resolve_grid_dims,
    merge_subplot,
)


def draw_quantity_operation(
    op1,
    op2,
    result,
    operation,
    font_size=50,
    font_color="black",
    save_path=None,
    show_operation=True,
):
    """
    Draws an arithmetic operation between quantity plots: Box(op1) operation Box(op2) = Box(result).

    Parameters:
    - op1 (dict): Arguments for the first operand plot_quantity.
    - op2 (dict): Arguments for the second operand plot_quantity.
    - result (dict): Arguments for the result plot_quantity.
    - operation (str): operation symbol (e.g. "+", "-", "x")
    - font_size (int): Font size for numbers and operators.
    - font_color (str): Color for numbers and operators.
    - save_path (str): Optional path to save the figure.
    - show_operation (bool): If True, shows the operation symbol. If False, hides it (useful for exercises).
    """
    items = [op1, op2, result]

    is_comparison = operation in [">", "<", "="]
    if is_comparison:
        items = [op1, op2]

    max_grid_rows = max(
        _resolve_grid_dims(item.get("n", 0), item.get("nrows", 1), item.get("cols"))[1]
        for item in items
    )

    for item in items:
        item["nrows"] = max_grid_rows
        item["font_size"] = font_size
        item["uniform_marker_size"] = True
        # item["font_color"] = font_color

    generated_plots = []
    widths = []
    heights = []

    for item in items:
        fig_temp = plot_quantity(**item)
        generated_plots.append(fig_temp)

        rng = fig_temp.layout.xaxis.range
        w_units = rng[1] - rng[0]
        widths.append(w_units)

        rng_y = fig_temp.layout.yaxis.range
        h_units = rng_y[1] - rng_y[0]
        heights.append(h_units)

    op_width_units = 1.0

    if is_comparison:
        # [Box1] [Op] [Box2]
        specs = [widths[0], op_width_units, widths[1]]
        cols = 3
    else:
        # [Box1] [Op] [Box2] [=] [Box3]
        specs = [widths[0], op_width_units, widths[1], op_width_units, widths[2]]
        cols = 5

    total_w_units = sum(specs)

    fig = make_subplots(
        rows=1,
        cols=cols,
        column_widths=[s / total_w_units for s in specs],
        horizontal_spacing=0.02,
    )

    max_h = max(heights) * 100

    merge_subplot(fig, generated_plots[0], row=1, col=1, total_cols=cols)
    merge_subplot(fig, generated_plots[1], row=1, col=3, total_cols=cols)
    if not is_comparison:
        merge_subplot(fig, generated_plots[2], row=1, col=5, total_cols=cols)

    # Operators
    top_y = max_grid_rows * 1.0 + 0.5
    bottom_y = -1.5
    mid_y = (top_y + bottom_y) / 2

    potential_operators = [(2, operation)]
    if not is_comparison:
        potential_operators.append((4, "="))

    for idx, sym in potential_operators:
        should_show = show_operation if idx == 2 else True
        text_content = sym if (should_show and font_color != "white") else ""

        if idx == 2 and not should_show:
            box_size = 0.8
            fig.add_shape(
                type="rect",
                x0=0.5 - box_size / 2,
                y0=mid_y - box_size / 2,
                x1=0.5 + box_size / 2,
                y1=mid_y + box_size / 2,
                line=dict(color="black", width=2),
                fillcolor="white",
                xref=f"x{idx}",
                yref=f"y{idx}",
            )

        fig.add_annotation(
            text=text_content,
            x=0.5,
            y=mid_y,
            xref=f"x{idx}",
            yref=f"y{idx}",
            showarrow=False,
            font=dict(family="Chalkboard SE", size=font_size * 1.5, color=font_color),
        )
        fig.layout[f"xaxis{idx}"].update(_hidden_axis(range=[0, 1]))
        fig.layout[f"yaxis{idx}"].update(_hidden_axis(range=[bottom_y - 0.5, top_y]))

    # Sizing
    pixels_per_unit = 100
    fig.update_layout(
        width=int(total_w_units * pixels_per_unit) + 10,
        height=int(max_h) + 10,
        plot_bgcolor="white",
        dragmode="pan",
        margin=dict(l=5, r=5, t=5, b=5),
    )

    if save_path:
        fig.write_image(save_path)

    return fig


def soroban_column(value: int, font_size: int = 30, font_color: str = "black"):
    """
    Uses the soroban_abacus library to show a single column of the abacus
    """
    import drawsvg as draw

    s = Soroban(ncolumns=1)
    s.from_decimal(value)

    lower = value % 5
    upper = value - lower

    s_svg = s.to_svg()

    try:
        w_soroban = float(str(getattr(s_svg, "width", 150)).replace("px", ""))
        h_soroban = float(str(getattr(s_svg, "height", 300)).replace("px", ""))
    except ValueError:
        w_soroban, h_soroban = 150, 300

    box_size = font_size * 2
    spacing = font_size * 0.5

    total_w = w_soroban + 3 * box_size + 4 * spacing + 2 * font_size
    d = draw.Drawing(total_w, h_soroban, origin=(0, 0))

    if hasattr(s_svg, "elements"):
        for el in s_svg.elements:
            d.append(el)
    else:
        d.append(s_svg)

    x_offset = w_soroban + spacing
    text_y = h_soroban / 2

    def draw_box(x, y, sz, text_val):
        d.append(
            draw.Rectangle(
                x, y - sz / 2, sz, sz, fill="white", stroke="black", stroke_width=2
            )
        )
        if font_color != "white":
            d.append(
                draw.Text(
                    str(text_val),
                    font_size,
                    x + sz / 2,
                    y,
                    center=True,
                    font_family="Chalkboard SE",
                    fill=font_color,
                    text_anchor="middle",
                    dominant_baseline="middle",
                )
            )

    def draw_text(x, y, text_val):
        color = (
            "black"
            if text_val in ["+", "="]
            else font_color
            if font_color != "white"
            else "rgba(0,0,0,0)"
        )
        d.append(
            draw.Text(
                text_val,
                font_size,
                x,
                y,
                center=True,
                font_family="Chalkboard SE",
                fill=color,
                text_anchor="middle",
                dominant_baseline="middle",
            )
        )

    draw_box(x_offset, text_y, box_size, upper)
    x_offset += box_size + spacing

    draw_text(x_offset, text_y, "+")
    x_offset += spacing

    draw_box(x_offset, text_y, box_size, lower)
    x_offset += box_size + spacing

    draw_text(x_offset, text_y, "=")
    x_offset += spacing

    draw_box(x_offset, text_y, box_size, value)

    return d
