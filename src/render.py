"""Images for the page: a 16-bit depth PNG (R/G channels) and a hillshaded bed PNG, plus the full outline."""
import base64
import io

import geopandas as gpd
import numpy as np
from PIL import Image
from shapely.ops import unary_union

from common import p


def _b64png(arr, mode):
    buf = io.BytesIO()
    Image.fromarray(arr, mode).save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def depth_png(z):
    """Depth in mm packed into R (high byte) and G (low byte); A = 255 where valid."""
    mm = np.clip(np.round(-z.filled(0) * 1000), 0, 65535).astype(np.uint16)
    rgba = np.zeros(z.shape + (4,), np.uint8)
    rgba[..., 0] = mm >> 8
    rgba[..., 1] = mm & 255
    rgba[..., 3] = np.where(z.mask, 0, 255)
    return _b64png(rgba, "RGBA")


def hillshade(z, res, az, alt, zf):
    zz = z.filled(np.nan)
    zz = np.where(np.isnan(zz), np.nanmax(zz), zz) * zf
    dy, dx = np.gradient(zz, res[1], res[0])
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    a, e = np.radians(360 - az + 90), np.radians(alt)
    hs = np.sin(e) * np.cos(slope) + np.cos(e) * np.sin(slope) * np.cos(a - aspect)
    return np.clip(hs, 0, 1)


def bed_png(z, res, cfg):
    r = cfg["render"]
    hs = hillshade(z, res, r["hillshade_azimuth"], r["hillshade_altitude"], r["z_factor"])
    d = np.clip(-z.filled(0) / 35.0, 0, 1)
    # dry lake-bed colours: pale silt near the rim, darker mud in the old channel
    base = np.stack([200 - 60 * d, 180 - 60 * d, 150 - 55 * d], -1)
    shade = 0.45 + 0.75 * hs[..., None]
    rgb = np.clip(base * shade, 0, 255).astype(np.uint8)
    rgba = np.concatenate([rgb, np.where(z.mask, 0, 255).astype(np.uint8)[..., None]], -1)
    return _b64png(rgba, "RGBA")


def outline_path(cfg, transform):
    """Full-reservoir outline (union of the contour polygons) as an SVG path in raster pixel coordinates."""
    g = gpd.read_file(p(cfg["inputs"]["contour_polygons"]))
    full = unary_union(g.geometry).buffer(0)
    a, b, c, d, e, f = transform
    def px(x, y):
        return round((x - c) / a, 1), round((y - f) / e, 1)
    parts = getattr(full, "geoms", [full])
    out = ""
    for poly in parts:
        for ring in [poly.exterior, *poly.interiors]:
            out += "M" + " L".join(f"{u},{v}" for u, v in (px(*pt) for pt in ring.simplify(3).coords)) + "Z"
    return out
