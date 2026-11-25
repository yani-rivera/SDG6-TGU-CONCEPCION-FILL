"""Config, paths and provenance."""
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path="config/config.yaml"):
    with open(ROOT / path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def p(rel):
    return (ROOT / rel).resolve()


def out_dir(cfg):
    d = p(cfg["outputs"]["dir"])
    d.mkdir(parents=True, exist_ok=True)
    return d


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_provenance(cfg, outputs, notes):
    prov = {
        "project": cfg["project"],
        "script_version": cfg["version"],
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "inputs": {k: {"path": v, "sha256": sha256(p(v))}
                   for k, v in {**cfg["inputs"], **cfg.get("catalogs", {})}.items() if p(v).is_file()},
        "outputs": {k: {"path": str(Path(v).relative_to(ROOT)), "sha256": sha256(v)} for k, v in outputs.items()},
        "notes": notes,
    }
    out = out_dir(cfg) / "provenance.json"
    out.write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
