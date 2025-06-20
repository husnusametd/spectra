"""Utility to auto-generate `thresholds` section in config.yaml
based on parameter references found in YAML signal/spec files.

Method
------
1. Open `spectra/spec.yaml` (or given path) and look for occurrences of
   the pattern ``cfg.<param_name>`` inside formula strings.
2. Collect unique parameter names.
3. For each name, assign a starting default value:
   * If name hints *overbought* / *oversold* use 70 / 30 respectively.
   * else 1.0 as generic placeholder.
4. Merge into existing config under `thresholds:` (create if missing).
5. Write updated config back (and backup previous as `config.yaml.bak`).

This keeps the config in sync with actual parameters referenced by the
signal engine, avoiding manual drift.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict

from spectra.utils import load_config, save_config, load_yaml_spec

SPEC_PATH = Path(__file__).resolve().parent / "spec.yaml"
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

CFG_PATTERN = re.compile(r"cfg\.([a-zA-Z0-9_]+)")

def _default_value(name: str) -> float:
    if "overbought" in name:
        return 70.0
    if "oversold" in name:
        return 30.0
    if "zscore" in name:
        return 1.5
    if "bb_width" in name:
        return 0.04
    return 1.0


def generate_thresholds() -> Dict[str, float]:
    # 1. collect param names from spec formulas
    spec = load_yaml_spec()
    param_names: set[str] = set()

    def _walk(node):
        if isinstance(node, dict):
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)
        elif isinstance(node, str):
            for m in CFG_PATTERN.findall(node):
                param_names.add(m)

    _walk(spec)

    defaults = {name: _default_value(name) for name in sorted(param_names)}
    cfg = load_config()
    cfg.setdefault("thresholds", {}).update({k: v for k, v in defaults.items() if k not in cfg["thresholds"]})

    # backup then save
    if CONFIG_PATH.exists():
        shutil.copy(CONFIG_PATH, CONFIG_PATH.with_suffix(".yaml.bak"))
    save_config(cfg, CONFIG_PATH)
    return defaults


if __name__ == "__main__":  # pragma: no cover
    new_thr = generate_thresholds()
    print("Generated/merged thresholds:")
    for k, v in new_thr.items():
        print(f"  {k}: {v}")
