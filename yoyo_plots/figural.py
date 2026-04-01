import plotly.graph_objects as go

from .common import hidden_axis


def plot_figural(
    ntype, n, save_path=None, font_size=50, font_color: str = "black", box_size=None
):
    """
    Plots the n-th figural number of a given type by extracting coordinates
    from the 'figural' library and rendering them with Plotly.

    Parameters:
    - ntype (str): 'triangular' or 'pentagonal'
    - n (int): The index of the  number (1-based usually).
    - save_path (str): Optional.
    - font_size (int): Font size for the number.
    - box_size (float | None): When set, forces the top box to this size (in data
      units) so that multiple figures can be combined at a uniform scale.
      Defaults to None (auto-sized from content).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if ntype == "triangular":
        import figural.triangular as mod
    elif ntype == "pentagonal":
        import figural.pentagonal as mod
    else:
        raise ValueError(
            f"Unknown ntype '{ntype}'. Supported: 'triangular', 'pentagonal'."
        )

    val = mod.ith(n)

    fig_mpl, ax = plt.subplots()

    try:
        mod.draw_ith(n, ax=ax, show=False, with_label=False)
    except Exception as e:
        plt.close(fig_mpl)
        raise RuntimeError(f"Error calling {ntype}.draw_ith: {e}")

    dots_x = []
    dots_y = []
    lines_x = []
    lines_y = []

    for line in ax.get_lines():
        lx, ly = line.get_data()
        marker = line.get_marker()
        ls = line.get_linestyle()

        if marker not in [None, "", "None", " "]:
            dots_x.extend(lx)
            dots_y.extend(ly)

        if ls not in [None, "", "None", " "]:
            lines_x.append(lx)
            lines_y.append(ly)

    for collection in ax.collections:
        offsets = collection.get_offsets()
        if len(offsets) > 0:
            dots_x.extend(offsets[:, 0])
            dots_y.extend(offsets[:, 1])

    plt.close(fig_mpl)

    if not dots_x and not lines_x:
        min_x, max_x = 0, 0
        min_y, max_y = 0, 0
    else:
        all_x = list(dots_x)
        all_y = list(dots_y)
        for lx in lines_x:
            all_x.extend(lx)
        for ly in lines_y:
            all_y.extend(ly)

        if not all_x:
            min_x, max_x = 0, 0
            min_y, max_y = 0, 0
        else:
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

    shape_w = max_x - min_x
    shape_h = max_y - min_y

    # Define Box Layout
    padding = 1.0
    top_box_width = max(shape_w + padding, 2.0)
    top_box_height = max(shape_h + padding, 2.0)

    if box_size is not None:
        top_box_width = max(float(box_size), top_box_width)
        top_box_height = max(float(box_size), top_box_height)

    tc_x = top_box_width / 2
    tc_y = top_box_height / 2
    sc_x = (min_x + max_x) / 2
    sc_y = (min_y + max_y) / 2
    dx = tc_x - sc_x
    dy = tc_y - sc_y

    def shift_x(arr):
        return [v + dx for v in arr]

    def shift_y(arr):
        return [v + dy for v in arr]

    fig = go.Figure()

    # Draw Top Box Frame
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=top_box_width,
        y1=top_box_height,
        line=dict(color="black", width=2),
        fillcolor="white",
        layer="below",
    )

    # Add Lines
    for lx, ly in zip(lines_x, lines_y):
        fig.add_trace(
            go.Scatter(
                x=shift_x(lx),
                y=shift_y(ly),
                mode="lines",
                line=dict(color="black", width=1),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Add Dots
    if dots_x:
        fig.add_trace(
            go.Scatter(
                x=shift_x(dots_x),
                y=shift_y(dots_y),
                mode="markers",
                marker=dict(size=12, color="black"),
                showlegend=False,
            )
        )

    # Bottom Box
    bottom_box_height = 1.5
    fig.add_shape(
        type="rect",
        x0=0,
        y0=-bottom_box_height,
        x1=top_box_width,
        y1=0,
        line=dict(color="black", width=2),
        fillcolor="white",
        layer="below",
    )

    # Label
    text_content = "" if font_color == "white" else str(val)
    fig.add_annotation(
        x=top_box_width / 2,
        y=-bottom_box_height / 2,
        text=text_content,
        showarrow=False,
        font=dict(size=font_size, color=font_color),
    )

    # Layout
    y_min = -bottom_box_height
    y_max = top_box_height
    view_margin = 0.05
    margin_px = 5

    pixels_per_unit = 80
    total_width_px = max(
        100, int((top_box_width + 2 * view_margin) * pixels_per_unit) + 2 * margin_px
    )
    total_height_px = max(
        100, int((y_max - y_min + 2 * view_margin) * pixels_per_unit) + 2 * margin_px
    )

    fig.update_layout(
        xaxis=hidden_axis(
            range=[-view_margin, top_box_width + view_margin],
            scaleanchor="y",
            scaleratio=1,
            fixedrange=True,
        ),
        yaxis=hidden_axis(
            range=[y_min - view_margin, y_max + view_margin], fixedrange=True
        ),
        width=total_width_px,
        height=total_height_px,
        plot_bgcolor="white",
        margin=dict(l=margin_px, r=margin_px, t=margin_px, b=margin_px),
    )

    return fig
