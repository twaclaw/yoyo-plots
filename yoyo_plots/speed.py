import drawsvg as draw
from .common import resolve_user_path


def speed_limit(
    n: int,
    text: str | None = None,
    n_fontsize: int = 50,
    text_font_size: int = 20,
    image_path: str | None = None,
) -> draw.Drawing:
    """
    Creates a speed limit sign SVG using drawsvg.
    """
    width = 120
    height = 120
    img_size = 80

    if image_path:
        height += img_size + 10

    d = draw.Drawing(width, height, origin=(-width / 2, -60))

    # Red circle with white background
    d.append(draw.Circle(0, 0, 50, fill="white", stroke="red", stroke_width=10))

    y_n = 0
    if text:
        y_n = -10
        # Text string (e.g. km/h)
        d.append(
            draw.Text(
                text,
                text_font_size,
                0,
                25,
                fill="black",
                text_anchor="middle",
                dominant_baseline="middle",
                font_family="sans-serif",
            )
        )

    # Speed limit number
    d.append(
        draw.Text(
            str(n),
            n_fontsize,
            0,
            y_n,
            fill="black",
            text_anchor="middle",
            dominant_baseline="middle",
            font_family="sans-serif",
            font_weight="bold",
        )
    )

    if image_path:
        resolved_path = resolve_user_path(image_path)
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            import re

            svg_clean = re.sub(r"<\?xml[^>]*\?>", "", svg_content)
            svg_clean = re.sub(r"<!DOCTYPE[^>]*>", "", svg_clean)

            nested_svg = svg_clean
            # Replace the outermost <svg width="X" height="Y" ...> with our own x, y, width, height, but KEEP viewBox
            viewbox_match = re.search(
                r"<svg[^>]*\sviewBox=[\"\']([^\"\']+)[\"\']", nested_svg
            )
            viewbox_attr = (
                f' viewBox="{viewbox_match.group(1)}"' if viewbox_match else ""
            )

            xmlns_matches = re.findall(
                r"(xmlns(?::\w+)?=[\"\'][^\"\']+[\"\'])", nested_svg.split(">", 1)[0]
            )
            xmlns_str = " ".join(xmlns_matches)

            # Remove the root <svg ...> and </svg> tags
            inner = re.sub(r"^\s*<svg[^>]*>", "", nested_svg.strip())
            inner = re.sub(r"</svg>\s*$", "", inner)

            wrapped = f'<svg x="{-img_size / 2}" y="{60 + 5}" width="{img_size}" height="{img_size}"{viewbox_attr} {xmlns_str}>{inner}</svg>'
            d.append(draw.Raw(wrapped))
        except Exception as e:
            print(f"Warning: could not load image {image_path}: {e}")

    return d
