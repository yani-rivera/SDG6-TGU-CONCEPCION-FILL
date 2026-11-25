"""Calibrate the reconstructed curve against UMAPS level–volume readings.

Model (depth stretch): the reconstruction has the right plan shape but too-shallow depths.
  real depth below full  = s x reconstructed depth
  real volume(level)     = s x V_rec((level - E_full) / s)
  real surface(level)    = A_rec((level - E_full) / s)          (area is unchanged by a vertical stretch)
Two fits are reported:
  constrained: s fixed so that full volume = official capacity; E_full fitted
  free:        s and E_full both fitted (capacity becomes a result)
"""
import numpy as np
import pandas as pd

from common import p


def load_points(cfg):
    pts = pd.read_csv(p(cfg["catalogs"]["umaps_points"]), dtype={"date": str})
    # the UMAPS volumes come from a fixed rating curve: the same level must give the same volume
    dup = pts.groupby("level_m_asl").volume_mm3.nunique()
    bad = dup[dup > 1]
    if len(bad):
        raise ValueError(f"Same level with different volumes (check transcription): {list(bad.index)}")
    return pts


def _model(E, h, V, Efull, s):
    return s * np.interp((E - Efull) / s, h, V, left=0.0)


def _rmse(E, Vo, h, V, Efull, s):
    return float(np.sqrt(np.mean((_model(E, h, V, Efull, s) - Vo) ** 2)))


def fit(curve, pts, capacity, grid):
    h = curve.level_m_below_full.values
    V = curve.volume_mm3.values
    E, Vo = pts.level_m_asl.values, pts.volume_mm3.values
    Es = np.arange(grid["full_min"], grid["full_max"], grid["full_step"])
    s_c = capacity / V[-1]
    e_c, Ef_c = min((_rmse(E, Vo, h, V, Ef, s_c), Ef) for Ef in Es)
    best = None
    for s in np.arange(grid["s_min"], grid["s_max"], grid["s_step"]):
        for Ef in Es:
            e = _rmse(E, Vo, h, V, Ef, s)
            if best is None or e < best[0]:
                best = (e, s, Ef)
    e_f, s_f, Ef_f = best
    resid = _model(E, h, V, Ef_c, s_c) - Vo
    return {
        "constrained": {"s": round(s_c, 4), "full_level_m_asl": round(float(Ef_c), 2), "rmse_mm3": round(e_c, 3),
                        "capacity_mm3": capacity, "max_depth_m": round(float(-h[0] * s_c), 1)},
        "free": {"s": round(float(s_f), 3), "full_level_m_asl": round(float(Ef_f), 2), "rmse_mm3": round(e_f, 3),
                 "capacity_mm3": round(float(s_f * V[-1]), 2), "max_depth_m": round(float(-h[0] * s_f), 1)},
        "residuals_mm3": [round(float(r), 3) for r in resid],
        "n_points": int(len(pts)),
    }


def calibrated_curve(curve, cal):
    c = cal["constrained"]
    out = curve.copy()
    out["level_m_asl_calibrated"] = (c["full_level_m_asl"] + out.level_m_below_full * c["s"]).round(2)
    out["volume_mm3_calibrated"] = (out.volume_mm3 * c["s"]).round(4).abs()
    return out
