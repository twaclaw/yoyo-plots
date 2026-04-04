import base64
import math
import os
import inspect

MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))


def pkg_asset(path: str) -> str:
    return os.path.join(MODULE_ROOT, path.lstrip("/"))


def resolve_user_path(path: str) -> str:
    """
    Resolves path in different folders of the quarto document
    """

    if os.path.exists(path):
        return path

    curr_search = os.getcwd()
    for _ in range(5):
        resolved_up = os.path.join(curr_search, path.lstrip("/\\"))
        if os.path.exists(resolved_up):
            return resolved_up
        parent = os.path.dirname(curr_search)
        if parent == curr_search:
            break
        curr_search = parent

    try:
        for frame_info in inspect.stack():
            frame_filename = frame_info.filename
            if (
                frame_filename.startswith(MODULE_ROOT)
                or frame_filename.startswith("<")
                or "importlib" in frame_filename
            ):
                continue
            if os.path.exists(frame_filename):
                caller_dir = os.path.dirname(os.path.abspath(frame_filename))
                resolved = os.path.join(caller_dir, path.lstrip("/\\"))
                if os.path.exists(resolved):
                    return resolved
                curr_search = caller_dir
                for _ in range(3):
                    curr_search = os.path.dirname(curr_search)
                    resolved_up = os.path.join(curr_search, path.lstrip("/\\"))
                    if os.path.exists(resolved_up):
                        return resolved_up
    except Exception:
        pass
    return path


def svg_to_data_uri(svg_path):
    with open(svg_path, "rb") as f:
        svg_data = f.read()
    svg_b64 = base64.b64encode(svg_data).decode()
    return f"data:image/svg+xml;base64,{svg_b64}"


def hidden_axis(**kw) -> dict:
    """Return a Plotly axis config dict with visibility disabled."""
    cfg = dict(visible=False, showgrid=False, zeroline=False)
    cfg.update(kw)
    return cfg


def resolve_grid_dims(
    n: int, nrows: int = 1, cols: int | None = None
) -> tuple[int, int]:
    """Return ``(grid_cols, grid_rows)`` for laying out *n* items."""
    if cols is not None:
        grid_cols = cols
    elif nrows > 0:
        grid_cols = math.ceil(n / nrows)
    else:
        grid_cols = n
    grid_cols = max(1, grid_cols)

    grid_rows = nrows
    if n > grid_rows * grid_cols:
        grid_rows = math.ceil(n / grid_cols)
    grid_rows = max(1, grid_rows)

    return grid_cols, grid_rows


def merge_subplot(fig, sub_fig, *, row: int, col: int, total_cols: int):
    """Copy shapes, annotations and images from *sub_fig* into a subplot of *fig*.

    Also configures the corresponding axes as hidden with matched ranges.
    """
    if sub_fig.layout.shapes:
        for shape in sub_fig.layout.shapes:
            fig.add_shape(shape, row=row, col=col)

    if sub_fig.layout.annotations:
        for note in sub_fig.layout.annotations:
            fig.add_annotation(note, row=row, col=col)

    plot_idx = (row - 1) * total_cols + col
    xref = f"x{plot_idx}" if plot_idx > 1 else "x"
    yref = f"y{plot_idx}" if plot_idx > 1 else "y"

    if sub_fig.layout.images:
        for img in sub_fig.layout.images:
            img.xref = xref
            img.yref = yref
            fig.add_layout_image(img)

    xaxis_key = "xaxis" if plot_idx == 1 else f"xaxis{plot_idx}"
    yaxis_key = "yaxis" if plot_idx == 1 else f"yaxis{plot_idx}"
    fig.layout[xaxis_key].update(hidden_axis(range=sub_fig.layout.xaxis.range))
    fig.layout[yaxis_key].update(
        hidden_axis(range=sub_fig.layout.yaxis.range, scaleanchor=xref, scaleratio=1)
    )


def strip_svg_header(svg_str: str) -> str:
    """Strip XML declaration / DOCTYPE, returning just the ``<svg …`` element."""
    start = svg_str.find("<svg")
    return svg_str[start:] if start > 0 else svg_str


class SvgDrawing:
    """Base class for objects that render themselves as SVG via drawsvg.

    Subclasses must implement:
    * ``to_group()``  – return a ``drawsvg.Group``
    * ``get_svg_dimensions()`` – return ``(width, height)``
    """

    def to_group(self, **kwargs):
        raise NotImplementedError

    def get_svg_dimensions(self) -> tuple[float, float]:
        raise NotImplementedError

    def to_svg(self) -> str:
        import drawsvg as draw

        w, h = self.get_svg_dimensions()
        d = draw.Drawing(w, h)
        d.append(self.to_group())
        return d.as_svg()


class VectorDisplay:
    def __init__(self, fig):
        self.fig = fig

    def _repr_pdf_(self):
        if isinstance(self.fig, str) or not hasattr(self.fig, "to_image"):
            return None
        import plotly.io as pio

        if pio.kaleido.scope:
            pio.kaleido.scope.mathjax = None
        return self.fig.to_image(format="pdf")

    def _repr_html_(self):
        if hasattr(self.fig, "to_html"):
            return self.fig.to_html(include_plotlyjs="cdn", full_html=False)
        return None

    def _repr_svg_(self):
        # For drawsvg / pure-SVG objects -> return the SVG string directly (vector).
        if isinstance(self.fig, str) and self.fig.strip().startswith("<svg"):
            return self.fig
        elif hasattr(self.fig, "as_svg"):
            return self.fig.as_svg()
        elif hasattr(self.fig, "to_svg"):
            return self.fig.to_svg()
        return None

def display_vector(fig):
    """
    This is inntended mainly for Quarto, that internally uses a Jupyter-like notebook.
    """
    from IPython.display import display

    display(VectorDisplay(fig))


def combine_svgs(
    svgs: list, direction: str = "horizontal", spacing: float = 15.0,
    separators: list | str | None = None, separator_font_size: float = 24.0,
) -> str:
    """
    Combines multiple SVG strings or draw.Drawing objects into a single SVG layout.
    direction: "horizontal" or "vertical". This is so far used for speed drawings mainly.
    """
    import re

    parsed_svgs = []
    total_width = 0.0
    total_height = 0.0
    max_width = 0.0
    max_height = 0.0

    for svg in svgs:
        if hasattr(svg, "as_svg"):
            svg_str = svg.as_svg()
        elif hasattr(svg, "to_svg"):
            svg_str = svg.to_svg()
        elif hasattr(svg, "to_image"):
            svg_str = svg.to_image(format="svg").decode("utf-8")
        else:
            svg_str = str(svg)

        # remove XML declaration
        svg_clean = re.sub(r"<\?xml[^>]*\?>", "", svg_str)
        svg_clean = re.sub(r"<!DOCTYPE[^>]*>", "", svg_clean)

        root_svg_match = re.search(r"^\s*<svg([^>]*)>", svg_clean, re.IGNORECASE)
        root_svg_attrs = root_svg_match.group(1) if root_svg_match else ""

        w_match = re.search(r"\bwidth=[\"\']([\d\.]+)[\"\']", root_svg_attrs)
        h_match = re.search(r"\bheight=[\"\']([\d\.]+)[\"\']", root_svg_attrs)

        w = float(w_match.group(1)) if w_match else 100.0
        h = float(h_match.group(1)) if h_match else 100.0

        viewbox_match = re.search(r"\bviewBox=[\"\']([^\"\']+)[\"\']", root_svg_attrs)
        viewbox_attr = f' viewBox="{viewbox_match.group(1)}"' if viewbox_match else ""

        xmlns_matches = re.findall(
            r"(xmlns(?::\w+)?=[\"\'][^\"\']+[\"\'])", root_svg_attrs
        )
        xmlns_str = " ".join(xmlns_matches)

        inner = re.sub(r"^\s*<svg[^>]*>", "", svg_clean.strip())
        inner = re.sub(r"</svg>\s*$", "", inner)

        parsed_svgs.append(
            {
                "inner": inner,
                "viewbox": viewbox_attr,
                "xmlns": xmlns_str,
                "width": w,
                "height": h,
            }
        )

        if direction == "horizontal":
            total_width += w + spacing
            max_height = max(max_height, h)
        else:
            total_height += h + spacing
            max_width = max(max_width, w)

    if not parsed_svgs:
        return "<svg></svg>"

    # Normalise separators to a list of (n-1) items (dict or None)
    n = len(parsed_svgs)
    sep_items: list[dict | None] = [None] * (n - 1)
    if separators is not None:
        if isinstance(separators, str):
            raw = [separators] * (n - 1)
        else:
            raw = list(separators)
        for i, s in enumerate(raw[: n - 1]):
            if isinstance(s, str):
                sep_items[i] = {"text": s, "font_size": separator_font_size}
            elif isinstance(s, dict):
                sep_items[i] = {
                    "text": s["text"],
                    "font_size": s.get("font_size", separator_font_size),
                }

    # Estimate separator text widths (≈ 0.6 × font_size per character)
    sep_widths: list[float] = []
    for sep in sep_items:
        if sep:
            sep_widths.append(len(sep["text"]) * sep["font_size"] * 0.6)
        else:
            sep_widths.append(0.0)

    # Compute total dimensions
    if direction == "horizontal":
        total_height = max(item["height"] for item in parsed_svgs)
        total_width = sum(item["width"] for item in parsed_svgs)
        for i in range(n - 1):
            if sep_items[i]:
                total_width += spacing + sep_widths[i] + spacing
            else:
                total_width += spacing
    else:
        total_width = max(item["width"] for item in parsed_svgs)
        total_height = sum(item["height"] for item in parsed_svgs)
        for i in range(n - 1):
            if sep_items[i]:
                total_height += spacing + sep_items[i]["font_size"] * 1.2 + spacing
            else:
                total_height += spacing

    combined = [
        f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
    ]

    current_x = 0.0
    current_y = 0.0

    for idx, item in enumerate(parsed_svgs):
        if direction == "horizontal":
            y_offset = current_y + (total_height - item["height"]) / 2.0
            x_offset = current_x
        else:
            x_offset = current_x + (total_width - item["width"]) / 2.0
            y_offset = current_y

        combined.append(
            f'<svg x="{x_offset}" y="{y_offset}" width="{item["width"]}" height="{item["height"]}"{item["viewbox"]} {item["xmlns"]}>{item["inner"]}</svg>'
        )

        # Add gap + optional separator before the next image
        if idx < n - 1:
            sep = sep_items[idx]
            if direction == "horizontal":
                current_x += item["width"] + spacing
                if sep:
                    text_x = current_x + sep_widths[idx] / 2.0
                    text_y = total_height / 2.0
                    combined.append(
                        f'<text x="{text_x}" y="{text_y}" '
                        f'font-size="{sep["font_size"]}" '
                        f'text-anchor="middle" dominant-baseline="central" '
                        f'font-family="sans-serif">{sep["text"]}</text>'
                    )
                    current_x += sep_widths[idx] + spacing
            else:
                current_y += item["height"] + spacing
                if sep:
                    sep_h = sep["font_size"] * 1.2
                    text_x = total_width / 2.0
                    text_y = current_y + sep_h / 2.0
                    combined.append(
                        f'<text x="{text_x}" y="{text_y}" '
                        f'font-size="{sep["font_size"]}" '
                        f'text-anchor="middle" dominant-baseline="central" '
                        f'font-family="sans-serif">{sep["text"]}</text>'
                    )
                    current_y += sep_h + spacing

    combined.append("</svg>")

    return "\n".join(combined)
