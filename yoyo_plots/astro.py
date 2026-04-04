"""
Constellation charts from Sky & Telescope data.

See ``./data/SnT_constellations.txt`` for the underlying catalogue.
Provides two chart types:

* :class:`SkyChart` – standard Cartesian (RA × Dec) projection
* :class:`ZodiacChart` – circular layout for zodiac-belt constellations
"""

from __future__ import annotations

import io
import math
import os
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Ellipse as MplEllipse
from IPython.display import SVG

from .common import pkg_asset

DATA_FILE = pkg_asset("data/SnT_constellations.txt")

_COL_MAG = slice(0, 5)
_COL_RA = slice(6, 14)
_COL_NPD = slice(15, 23)
_COL_LABEL = slice(24, 28)
_COL_CONNECTIVITY = slice(28, 32)
_COL_CON = slice(29, 32)
_MIN_LINE_LEN = 32

# Visual constants
_MAG_ZERO = 6.0
_MAG_SCALE = 2.5
_MAG_EXP = 1.8
_MIN_STAR_SIZE = 3
_MAX_STAR_SIZE = 400
_STAR_EDGE_COLOR = "#555555"

_LINE_WIDTH = 1.2
_LINE_ALPHA_SKY = 0.4
_LINE_ALPHA_ZODIAC = 0.5

_LABEL_COLOR = "#888"
_LABEL_FONT_SIZE_SKY = 14
_LABEL_FONT_SIZE_ZODIAC = 12
_LABEL_ALPHA = 0.7

_STAR_NAME_COLOR = "#333"
_STAR_NAME_FONT_SIZE = 9

_MARKER_PADDING = 1.5
_MARKER_FILL_ALPHA = 0.12
_MARKER_EDGE_ALPHA = 0.6
_MARKER_EDGE_WIDTH = 1.5
_MARKER_FONT_SIZE = 11
_MARKER_MIN_AXIS = 0.8
_MARKER_LABEL_GAP = 0.5

_ZODIAC_RADIUS = 10.0
_ZODIAC_SCALE = 0.15
_ZODIAC_LABEL_OFFSET = 3.0
_ZODIAC_LIMIT_PAD = 5
_ZODIAC_SEG_THRESHOLD = 2000

_FIGSIZE_SKY = (10, 10)
_FIGSIZE_ZODIAC = (12, 12)

# Per-constellation radius tweaks so overlapping zodiac constellations
# (SCO / OPH, CAP / AQR) separate visually.
# The idea here is to draw the zodiac constellations using a polar coordinate system but without distorting individual constellations.
_ZODIAC_RADIUS_OFFSETS: dict[str, float] = {
    "SCO": -2.0,
    "OPH": 1.5,
    "CAP": -1.5,
    "AQR": 1.5,
}

DEFAULT_ZODIAC_TARGETS = [
    "ARI",
    "TAU",
    "GEM",
    "CNC",
    "LEO",
    "VIR",
    "LIB",
    "SCO",
    "OPH",
    "SGR",
    "CAP",
    "AQR",
    "PSC",
]

CON_NAMES: dict[str, str] = {
    "ORI": "Orion",
    "CMA": "Canis Major",
    "CMI": "Canis Minor",
    "TAU": "Taurus",
    "GEM": "Gemini",
    "LEP": "Lepus",
    "AUR": "Auriga",
    "SCO": "Scorpius",
    "BOO": "Bootes",
    "LYR": "Lyra",
    "AQL": "Aquila",
    "CAS": "Cassiopeia",
    "UMA": "Ursa Major",
    "UMI": "Ursa Minor",
    "AND": "Andromeda",
    "PER": "Perseus",
    "CYG": "Cygnus",
    "PEG": "Pegasus",
    "LEO": "Leo",
    "VIR": "Virgo",
    "LIB": "Libra",
    "SGR": "Sagittarius",
    "CAP": "Capricornus",
    "AQR": "Aquarius",
    "PSC": "Pisces",
    "ARI": "Aries",
    "CNC": "Cancer",
    "OPH": "Ophiuchus",
}

STAR_NAMES: dict[str, str] = {
    "alfOri": "Betelgeuse",
    "betOri": "Rigel",
    "gamOri": "Bellatrix",
    "kapOri": "Saiph",
    "delOri": "Mintaka",
    "epsOri": "Alnilam",
    "zetOri": "Alnitak",
    "alfCMa": "Sirius",
    "epsCMa": "Adhara",
    "alfCMi": "Procyon",
    "alfTau": "Aldebaran",
    "betTau": "Elnath",
    "alfGem": "Castor",
    "betGem": "Pollux",
    "alfAur": "Capella",
    "alfLeo": "Regulus",
    "alfSco": "Antares",
    "alfLyr": "Vega",
    "alfAql": "Altair",
    "alfCyg": "Deneb",
    "alfBoo": "Arcturus",
    "alfVir": "Spica",
}

# Colour overrides for well-known bright stars.
_STAR_COLORS: dict[str, str] = {
    "alfOri": "#FFBB99",  # Betelgeuse  (red supergiant)
    "betOri": "#AAAACC",  # Rigel       (blue-white)
    "alfCMa": "#CCCCFF",  # Sirius      (white / blue)
    "alfCMi": "#F8F8FF",  # Procyon     (yellow-white)
    "alfTau": "#FFBB44",  # Aldebaran   (orange)
    "alfSco": "#FFBB99",  # Antares     (red)
    "alfBoo": "#FFCC66",  # Arcturus    (orange)
    "alfLyr": "#CCCCFF",  # Vega        (blue-white)
    "alfAql": "#F8F8FF",  # Altair      (white)
    "betGem": "#FFCC66",  # Pollux      (orange)
    "alfGem": "#CCCCFF",  # Castor      (white)
}


def _star_key(label: str, con: str) -> str:
    """Canonical key for a star: e.g. ``'alfOri'``."""
    return f"{label}{con[0]}{con[1:].lower()}".replace(" ", "")


def _star_color(label: str, con: str) -> str:
    """Look up a star's display colour; falls back to black."""
    return _STAR_COLORS.get(_star_key(label, con), "black")


def _mag_to_size(mag: float) -> float:
    """Convert a visual magnitude to a matplotlib scatter size."""
    val = max(0, _MAG_ZERO - mag)
    return max(_MIN_STAR_SIZE, min((val * _MAG_SCALE) ** _MAG_EXP, _MAX_STAR_SIZE))


def _star_scatter_kw(color: str) -> dict:
    """Return ``edgecolors`` / ``linewidth`` kwargs for a star marker."""
    if color == "black":
        return dict(edgecolors="none", linewidth=0.0)
    return dict(edgecolors=_STAR_EDGE_COLOR, linewidth=0.5)


def _delta_ra(a: float, b: float) -> float:
    """Signed shortest-path difference *a − b* on [0, 360)."""
    d = a - b
    if d > 180:
        d -= 360
    elif d < -180:
        d += 360
    return d


def _mean_ra(ras: list[float]) -> float:
    """Circular mean of a list of RA values (in degrees)."""
    if max(ras) - min(ras) > 180:
        adjusted = [r if r > 180 else r + 360 for r in ras]
        avg = sum(adjusted) / len(adjusted)
        return avg % 360
    return sum(ras) / len(ras)


def _fit_ellipse(
    points: list[tuple[float, float]],
    padding: float = _MARKER_PADDING,
) -> tuple[float, float, float, float, float]:
    """Fit a bounding ellipse around *points* → *(cx, cy, w, h, angle_deg)*.

    Uses PCA to find the natural axes of the point cloud, then sizes
    the ellipse to contain every point plus *padding* degrees on each
    side.  Returned *w* and *h* are full diameters suitable for
    ``matplotlib.patches.Ellipse``.
    """
    n = len(points)
    ras = [p[0] for p in points]
    decs = [p[1] for p in points]

    cx = _mean_ra(ras)
    cy = sum(decs) / n

    if n == 1:
        return cx, cy, padding * 2, padding * 2, 0.0

    # Centre the coordinates
    dx = [_delta_ra(r, cx) for r in ras]
    dy = [d - cy for d in decs]
    coords = np.array([dx, dy])  # shape (2, n)

    cov = np.cov(coords)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # Sort by descending eigenvalue (major axis first)
    order = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, order]

    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))

    # Project points onto principal axes to find extent
    proj = eigenvectors.T @ coords  # (2, n)
    semi_a = max(float(np.max(np.abs(proj[0, :]))), _MARKER_MIN_AXIS) + padding
    semi_b = max(float(np.max(np.abs(proj[1, :]))), _MARKER_MIN_AXIS) + padding

    return cx, cy, semi_a * 2, semi_b * 2, float(angle)


def load_constellation(
    target_abbrs: list[str],
    filename: str = DATA_FILE,
) -> tuple[list[list[tuple[float, float]]], list[dict]]:
    """Parse S&T data for *target_abbrs* (e.g. ``['ORI', 'CMA']``).

    Returns ``(segments, stars)`` where each segment is a list of
    ``(ra_deg, dec_deg)`` points and each star is a dict with keys
    ``ra, dec, mag, label, con, color``.
    """
    targets = {t.strip().upper() for t in target_abbrs}

    if not os.path.exists(filename):
        raise FileNotFoundError(filename)

    segments: list[list[tuple[float, float]]] = []
    current_segment: list[tuple[float, float]] = []
    stars: dict[tuple[float, float], dict] = {}
    last_key: str | None = None

    with open(filename, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or len(line) < _MIN_LINE_LEN:
                continue
            try:
                con = line[_COL_CON].strip().upper()
                if con not in targets:
                    if len(current_segment) > 1:
                        segments.append(current_segment)
                    current_segment = []
                    last_key = None
                    continue

                key = line[_COL_CONNECTIVITY]
                ra = float(line[_COL_RA]) * 15.0  # Hours to degrees
                dec = 90.0 - float(line[_COL_NPD])
                mag_str = line[_COL_MAG].strip()
                mag = float(mag_str) if mag_str else _MAG_ZERO
                label = line[_COL_LABEL].strip()

                point = (ra, dec)
                s_key = (round(ra, 3), round(dec, 3))
                if s_key not in stars:
                    stars[s_key] = dict(
                        ra=ra,
                        dec=dec,
                        mag=mag,
                        label=label,
                        con=con,
                        color=_star_color(label, con),
                    )

                if key == last_key:
                    current_segment.append(point)
                else:
                    if len(current_segment) > 1:
                        segments.append(current_segment)
                    current_segment = [point]
                last_key = key

            except ValueError:
                continue

    if len(current_segment) > 1:
        segments.append(current_segment)

    return segments, list(stars.values())


def _compute_centroids(
    stars: list[dict],
) -> tuple[dict[str, tuple[float, float]], dict[str, list[dict]]]:
    """Group *stars* by constellation, returning centroids and per-con star lists."""
    con_points: dict[str, list[tuple[float, float]]] = defaultdict(list)
    con_stars: dict[str, list[dict]] = defaultdict(list)

    for s in stars:
        c = s["con"]
        con_points[c].append((s["ra"], s["dec"]))
        con_stars[c].append(s)

    centroids: dict[str, tuple[float, float]] = {}
    for c, pts in con_points.items():
        ras, decs = zip(*pts)
        centroids[c] = (_mean_ra(list(ras)), sum(decs) / len(decs))

    return centroids, dict(con_stars)


class SkyChart:
    """Cartesian (RA x Dec) sky chart.

    Parameters
    ----------
    target_list : list[str]
        Constellation abbreviations (e.g. ``["ORI", "CMA"]``).
    figsize : tuple[int, int]
        Matplotlib figure size.

    Decorations are added via fluent ``add_*`` methods::

        chart = (SkyChart(["ORI", "CMA", "CMI"])
            .add_constellation_labels()
            .add_star_names()
        )
        fig = chart.to_figure()
    """

    def __init__(
        self,
        target_list: list[str],
        *,
        figsize: tuple[int, int] = _FIGSIZE_SKY,
    ):
        self.target_list = [t.strip().upper() for t in target_list]
        self.figsize = figsize
        self._show_constellation_labels = False
        self._show_star_names = False
        self._markers: dict[tuple[str, ...], dict] = {}

    def add_constellation_labels(self) -> SkyChart:
        """Show constellation names at their centroids."""
        self._show_constellation_labels = True
        return self

    def add_star_names(self) -> SkyChart:
        """Label well-known stars by name."""
        self._show_star_names = True
        return self

    def add_markers(
        self,
        markers: dict[tuple[str, ...], dict],
    ) -> SkyChart:
        """Highlight groups of stars with labelled ellipses.

        Parameters
        ----------
        markers : dict
            ``{(star_key, ...): {"color": str, "text": str}}``
            where each *star_key* uses the internal Bayer-style
            notation, e.g. ``"delOri"`` for δ Orionis.
        """
        self._markers = markers
        return self

    def to_figure(self) -> plt.Figure:
        """Build and return a matplotlib ``Figure``."""
        segments, stars = load_constellation(self.target_list)
        if not segments and not stars:
            fig = plt.figure(figsize=self.figsize)
            return fig

        centroids, _ = _compute_centroids(stars)

        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()

        # Segments
        for seg in segments:
            xs, ys = zip(*seg)
            ax.plot(
                xs, ys, color="black", lw=_LINE_WIDTH, alpha=_LINE_ALPHA_SKY, zorder=1
            )

        # Stars (draw faint first so bright stars are on top)
        stars.sort(key=lambda s: -s["mag"])
        for s in stars:
            size = _mag_to_size(s["mag"])
            kw = _star_scatter_kw(s["color"])
            ax.scatter(s["ra"], s["dec"], s=size, c=s["color"], zorder=2, **kw)

            if self._show_star_names:
                name = STAR_NAMES.get(_star_key(s["label"], s["con"]))
                if name:
                    ax.text(
                        s["ra"],
                        s["dec"],
                        f"  {name}",
                        color=_STAR_NAME_COLOR,
                        fontsize=_STAR_NAME_FONT_SIZE,
                        fontweight="bold",
                        ha="left",
                        va="center",
                        zorder=3,
                    )

        # Constellation labels
        if self._show_constellation_labels:
            for c, (cra, cdec) in centroids.items():
                ax.text(
                    cra,
                    cdec,
                    CON_NAMES.get(c, c).upper(),
                    color=_LABEL_COLOR,
                    fontsize=_LABEL_FONT_SIZE_SKY,
                    alpha=_LABEL_ALPHA,
                    ha="center",
                    va="center",
                    zorder=0,
                )

        # Markers
        if self._markers:
            star_lookup: dict[str, tuple[float, float]] = {}
            for s in stars:
                star_lookup[_star_key(s["label"], s["con"])] = (s["ra"], s["dec"])

            for star_keys, opts in self._markers.items():
                pts = [star_lookup[k] for k in star_keys if k in star_lookup]
                if not pts:
                    continue
                color = opts.get("color", "#FF6644")
                text = opts.get("text", "")
                cx, cy, w, h, angle = _fit_ellipse(pts)
                rgb = to_rgb(color)
                patch = MplEllipse(
                    (cx, cy),
                    w,
                    h,
                    angle=angle,
                    facecolor=(*rgb, _MARKER_FILL_ALPHA),
                    edgecolor=(*rgb, _MARKER_EDGE_ALPHA),
                    linewidth=_MARKER_EDGE_WIDTH,
                    linestyle="--",
                    zorder=4,
                )
                ax.add_patch(patch)
                if text:
                    angle_rad = np.radians(angle)
                    half_bbox_h = (
                        (w / 2) * abs(np.sin(angle_rad))
                        + (h / 2) * abs(np.cos(angle_rad))
                    )
                    ax.text(
                        cx,
                        cy + half_bbox_h + _MARKER_LABEL_GAP,
                        text,
                        color=color,
                        fontsize=_MARKER_FONT_SIZE,
                        fontweight="bold",
                        ha="center",
                        va="bottom",
                        zorder=5,
                    )

        ax.invert_xaxis()  # Sky-map convention
        ax.set_aspect("equal", "datalim")
        return fig


class ZodiacChart:
    """Circular zodiac-belt chart.

    Parameters
    ----------
    target_list : list[str] | None
        Constellation abbreviations.  Defaults to the 13 zodiac
        constellations (including Ophiuchus).
    figsize : tuple[int, int]
        Matplotlib figure size.
    """

    def __init__(
        self,
        target_list: list[str] | None = None,
        *,
        figsize: tuple[int, int] = _FIGSIZE_ZODIAC,
    ):
        self.target_list = (
            [t.strip().upper() for t in target_list]
            if target_list is not None
            else list(DEFAULT_ZODIAC_TARGETS)
        )
        self.figsize = figsize

    @staticmethod
    def _assign_segments_to_constellations(
        segments: list,
        centroids: dict[str, tuple[float, float]],
    ) -> dict[str, list]:
        """Map each segment to its nearest constellation centroid."""
        con_segs: dict[str, list] = {c: [] for c in centroids}
        for seg in segments:
            sx, sy = zip(*seg)
            s_ra = _mean_ra(list(sx))
            s_dec = sum(sy) / len(sy)

            best_c, min_d = None, float("inf")
            for c, (cra, cdec) in centroids.items():
                d = _delta_ra(s_ra, cra) ** 2 + (s_dec - cdec) ** 2
                if d < min_d:
                    min_d, best_c = d, c

            if best_c is not None and min_d < _ZODIAC_SEG_THRESHOLD:
                con_segs[best_c].append(seg)
        return con_segs

    def _project_point(
        self,
        ra: float,
        dec: float,
        cra: float,
        cdec: float,
        cx: float,
        cy: float,
        cos_rot: float,
        sin_rot: float,
    ) -> tuple[float, float]:
        """Project a sky point onto the zodiac patch centred at *(cx, cy)*."""
        dra = _delta_ra(ra, cra)
        ddec = dec - cdec
        x_local = -(dra * math.cos(math.radians(cdec)))
        y_local = ddec
        x_final = x_local * cos_rot - y_local * sin_rot
        y_final = x_local * sin_rot + y_local * cos_rot
        return cx + x_final * _ZODIAC_SCALE, cy + y_final * _ZODIAC_SCALE

    def to_figure(self) -> plt.Figure:
        """Build and return a matplotlib ``Figure``."""
        segments, stars = load_constellation(self.target_list)
        if not segments and not stars:
            fig = plt.figure(figsize=self.figsize)
            return fig

        centroids, con_star_groups = _compute_centroids(stars)
        con_segments = self._assign_segments_to_constellations(segments, centroids)

        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.set_aspect("equal")

        for c_code, (cra, cdec) in centroids.items():
            radius = _ZODIAC_RADIUS + _ZODIAC_RADIUS_OFFSETS.get(c_code, 0.0)
            theta = math.radians(cra)
            cx = radius * math.cos(theta)
            cy = radius * math.sin(theta)

            patch_rot = theta - math.pi / 2.0
            cos_rot = math.cos(patch_rot)
            sin_rot = math.sin(patch_rot)

            # Label
            l_dist = radius + _ZODIAC_LABEL_OFFSET
            lx, ly = l_dist * math.cos(theta), l_dist * math.sin(theta)
            text_rot = math.degrees(patch_rot) + 90
            if 90 < text_rot % 360 < 270:
                text_rot += 180
            ax.text(
                lx,
                ly,
                CON_NAMES.get(c_code, c_code).upper(),
                color=_LABEL_COLOR,
                fontsize=_LABEL_FONT_SIZE_ZODIAC,
                ha="center",
                va="center",
                rotation=text_rot,
            )

            # Segments
            for seg in con_segments.get(c_code, []):
                pts = [
                    self._project_point(pra, pdec, cra, cdec, cx, cy, cos_rot, sin_rot)
                    for pra, pdec in seg
                ]
                ax.plot(
                    [p[0] for p in pts],
                    [p[1] for p in pts],
                    color="black",
                    lw=_LINE_WIDTH,
                    alpha=_LINE_ALPHA_ZODIAC,
                )

            # Stars
            c_stars = sorted(con_star_groups.get(c_code, []), key=lambda s: -s["mag"])
            for s in c_stars:
                fx, fy = self._project_point(
                    s["ra"],
                    s["dec"],
                    cra,
                    cdec,
                    cx,
                    cy,
                    cos_rot,
                    sin_rot,
                )
                size = _mag_to_size(s["mag"])
                kw = _star_scatter_kw(s["color"])
                ax.scatter(fx, fy, s=size, c=s["color"], zorder=2, **kw)

        limit = _ZODIAC_RADIUS + _ZODIAC_LIMIT_PAD
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        return fig


def _fig_to_svg(fig: plt.Figure) -> SVG:
    """Render a matplotlib *fig* as an IPython SVG display object."""
    buf = io.BytesIO()
    fig.savefig(
        buf, format="svg", transparent=True, bbox_inches="tight", pad_inches=0.1
    )
    plt.close(fig)
    buf.seek(0)
    return SVG(data=buf.getvalue())


# conviencnce and backward compatible wrappers


def plot_zodiac(
    target_list: list[str] | None = None,
    output_file: str | None = None,
) -> SVG:
    fig = ZodiacChart(target_list).to_figure()
    if output_file:
        fig.savefig(output_file, transparent=True, bbox_inches="tight", pad_inches=0.1)
    return _fig_to_svg(fig)


def plot_sky(
    target_list: list[str],
    output_file: str | None = None,
    show_constellations: bool = False,
    show_stars: bool = False,
    markers: dict[tuple[str, ...], dict] | None = None,
) -> SVG:
    chart = SkyChart(target_list)
    if show_constellations:
        chart.add_constellation_labels()
    if show_stars:
        chart.add_star_names()
    if markers:
        chart.add_markers(markers)
    fig = chart.to_figure()
    if output_file:
        fig.savefig(output_file, transparent=True, bbox_inches="tight", pad_inches=0.1)
    return _fig_to_svg(fig)
