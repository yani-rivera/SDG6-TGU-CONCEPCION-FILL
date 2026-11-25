"""Build the La Concepción fill-and-empty interactive.

    python src/run.py [--config config/config.yaml]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyproj import Transformer  # noqa: E402

from calibrate import calibrated_curve, fit, load_points  # noqa: E402
from common import load_config, out_dir, p, write_provenance  # noqa: E402
from curve import add_range, level_area_volume, load_depth, zero_offset_needed  # noqa: E402
from render import bed_png, depth_png, outline_path  # noqa: E402


def build_page(cfg, meta, curve, images, outline, center):
    data = {"title": cfg["title"], "subtitle": cfg["subtitle"], "version": cfg["version"],
            "w": meta["width"], "h": meta["height"], "res": meta["res"][0],
            "curve": curve[["level_m_below_full", "area_ha", "volume_mm3"]].values.tolist(),
            "cal": meta["cal"], "pts": meta["pts"],
            "range": {"targets": cfg["range"]["targets_mm3"], "labels": cfg["range"]["labels"],
                      "offset_m": meta.get("offsets_m")},
            "official": cfg["official"], "dataset": cfg["dataset"], "outline": outline,
            "center": center, "depth_png": images["depth"], "bed_png": images["bed"]}
    tpl = p("web/template.html").read_text(encoding="utf-8")
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = out_dir(cfg) / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    cfg = load_config(ap.parse_args().config)

    z, meta = load_depth(cfg)
    cell = abs(meta["res"][0] * meta["res"][1])
    curve = level_area_volume(z, cell, cfg["curve"]["step_m"])
    curve = add_range(curve, cfg["range"]["targets_mm3"])
    pts = load_points(cfg)
    cal = fit(curve, pts, cfg["official"]["capacity_mm3"], cfg["calibration"]["grid"])
    curve = calibrated_curve(curve, cal)
    pts_out = pts.assign(residual_mm3=cal["residuals_mm3"])
    pts_csv = out_dir(cfg) / "calibration_points.csv"
    pts_out.to_csv(pts_csv, index=False, encoding=cfg["outputs"]["encoding"])
    meta["cal"] = cal
    meta["pts"] = pts[["level_m_asl", "volume_mm3", "date"]].values.tolist()
    csv = out_dir(cfg) / "level_area_volume.csv"
    curve.to_csv(csv, index=False, encoding=cfg["outputs"]["encoding"])

    rim_area_ha = z.count() * cell / 1e4                    # all basin cells, including the 0 m rim
    meta["offsets_m"] = [round(zero_offset_needed(float(curve.volume_mm3.iloc[-1]), rim_area_ha, t), 1)
                         for t in cfg["range"]["targets_mm3"]]
    b = meta["bounds"]
    lon, lat = Transformer.from_crs(meta["crs"], "EPSG:4326", always_xy=True).transform((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    images = {"depth": depth_png(z), "bed": bed_png(z, meta["res"], cfg)}
    page = build_page(cfg, meta, curve, images, outline_path(cfg, meta["transform"]), [round(lon, 4), round(lat, 4)])

    full = curve.iloc[-1]
    notes = {"cells": int(z.count()), "cell_m2": round(cell, 3), "max_depth_m": round(float(-z.min()), 2),
             "full_area_ha": float(full.area_ha), "full_volume_mm3": float(full.volume_mm3),
             "official_capacity_mm3": cfg["official"]["capacity_mm3"],
             "ratio_reconstructed_to_official": round(float(full.volume_mm3) / cfg["official"]["capacity_mm3"], 3),
             "range_targets_mm3": cfg["range"]["targets_mm3"],
             "zero_offset_needed_m": meta["offsets_m"], "basin_area_incl_rim_ha": round(rim_area_ha, 2),
             "crs": meta["crs"]}
    notes["calibration"] = {k: v for k, v in meta["cal"].items() if k != "residuals_mm3"}
    prov = write_provenance(cfg, {"curve_csv": csv, "calibration_points_csv": pts_csv, "page": page}, notes)
    print(json.dumps(notes, indent=1), "\n", prov)


if __name__ == "__main__":
    main()
