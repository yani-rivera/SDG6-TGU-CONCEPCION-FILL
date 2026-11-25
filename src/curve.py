"""Level–area–volume curve from the depth raster.

Depth z <= 0 is metres below the maximum operating level. For a water level h (also <= 0):
  area(h)   = cell area x number of cells with z < h
  volume(h) = cell area x sum(max(0, h - z))
"""
import numpy as np
import pandas as pd
import rasterio

from common import p


def load_depth(cfg):
    with rasterio.open(p(cfg["inputs"]["depth_tif"])) as r:
        z = r.read(1, masked=True).astype("float64")
        meta = {"crs": r.crs.to_string(), "transform": list(r.transform)[:6], "res": r.res,
                "width": r.width, "height": r.height, "bounds": list(r.bounds)}
    return z, meta


def level_area_volume(z, cell_m2, step):
    v = z.compressed()
    zmin = float(np.floor(v.min() / step) * step)
    levels = np.round(np.arange(zmin, 0 + step / 2, step), 3)
    vs = np.sort(v)
    cums = np.concatenate([[0.0], np.cumsum(vs)])
    rows = []
    for h in levels:
        n = np.searchsorted(vs, h, side="left")          # cells with z < h
        vol = (h * n - cums[n]) * cell_m2
        rows.append((h, n * cell_m2 / 1e4, vol / 1e6))
    df = pd.DataFrame(rows, columns=["level_m_below_full", "area_ha", "volume_mm3"])
    df["pct_of_reconstructed_full"] = 100 * df.volume_mm3 / df.volume_mm3.iloc[-1]
    df = df.round({"area_ha": 2, "volume_mm3": 4, "pct_of_reconstructed_full": 2})
    df[["volume_mm3", "pct_of_reconstructed_full"]] = df[["volume_mm3", "pct_of_reconstructed_full"]].abs()  # no -0.0
    return df


def add_range(df, targets):
    """Shape-preserving range: volume x (target / reconstructed full). Percent full is unchanged."""
    full = df.volume_mm3.iloc[-1]
    for t in targets:
        df[f"volume_mm3_scaled_to_{t:g}"] = (df.volume_mm3 * t / full).round(4).abs()
    return df


def zero_offset_needed(full_mm3, full_area_ha, target_mm3):
    """Metres the full level would have to rise (walls assumed vertical at the outline) to reach the target."""
    return (target_mm3 - full_mm3) * 1e6 / (full_area_ha * 1e4)
