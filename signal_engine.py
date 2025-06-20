"""YAML'deki sinyal bloklarını değerlendirir.

NOT: Gerçek piyasa verisi gerektirdiği için burada yalnızca iskelet sağlanır.
Kullanıcı kendi indikatör hesaplamalarını ekleyebilir.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Mapping

from .utils import load_yaml_spec, load_config
from .formula_parser import compile_formula

SPEC = load_yaml_spec()
SIGNALS_SPEC: Mapping[str, Mapping[str, str]] = SPEC["signals"]

# Eşik konfigürasyonu – thresholds
CFG_THRESHOLDS = load_config().get("thresholds", {})

# Her sinyal için primary/confirm formüllerini derle ve sakla
_COMPILED: Dict[str, Dict[str, object]] = {}
for name, block in SIGNALS_SPEC.items():
    compiled = {}
    if "primary" in block and block["primary"]:
        try:
            compiled["primary"] = compile_formula(block["primary"])
        except Exception as exc:
            logging.error("Compile error for primary formula of %s: %s", name, exc)
            compiled["primary"] = None
    if "confirm" in block and block["confirm"]:
        try:
            compiled["confirm"] = compile_formula(block["confirm"])
        except Exception as exc:
            logging.error("Compile error for confirm formula of %s: %s", name, exc)
            compiled["confirm"] = None
    _COMPILED[name] = compiled


def evaluate_signals(asset: Dict) -> List[Dict]:
    """Bir varlık için YAML tanımlı sinyalleri değerlendir.

    Parameters
    ----------
    asset : dict
        `data_fetcher` sonucu Coin bilgisi ya da OHLC/indicator verilerini
        içeren sözlük. İleri aşamada OHLCV & indikatör değerleri eklenecek.
    """
    results: List[Dict] = []

    # data sözlüğü: şimdilik asset dict + ADM hoc prepared indicators eklenmeli
    data = asset.copy()

    for name, compiled in _COMPILED.items():
        primary_fn = compiled.get("primary")
        confirm_fn = compiled.get("confirm")
        try:
            primary_ok = bool(primary_fn(data, CFG_THRESHOLDS)) if primary_fn else True
            confirm_ok = bool(confirm_fn(data, CFG_THRESHOLDS)) if confirm_fn else True
        except Exception as exc:
            logging.error("Formula eval error for %s: %s", name, exc)
            primary_ok = confirm_ok = False

        is_true = primary_ok and confirm_ok

        # Basit conviction: confirm varsa +1 puan, primary 2 puan
        score = 0
        if primary_ok:
            score += 2
        if confirm_ok:
            score += 1
        conviction = "High" if score >= 3 else "Medium" if score == 2 else "Low"

        results.append({
            "name": name,
            "true": is_true,
            "conviction": conviction,
        })

    logging.debug("Signals for %s: %s", asset.get("symbol"), results)
    return results
