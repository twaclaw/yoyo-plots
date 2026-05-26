import drawsvg as draw
from .common import embed_svg_image


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
        try:
            d.append(
                embed_svg_image(image_path, -img_size / 2, 60 + 5, img_size, img_size)
            )
        except Exception as e:
            print(f"Warning: could not load image {image_path}: {e}")

    return d
