"""Basit sinyal formülü ayrıştırıcısı.

Formül sözdizimi TradingView / YAML benzeri basit mantıksal ifadelerden oluşur:
    Price_4H > EMA21_4H & Price_4H < EMA50_4H
    Vol_Z_1H > cfg.vol_z_breakout_1h | RSI < 30

Özellikler
----------
* Mantıksal **&**, **|** operatörlerini Python `and` / `or`'a dönüştürür.
* Karşılaştırma operatörleri (>, <, >=, <=, ==, !=) korunur.
* `cfg.<param>` referanslarını `cfg["<param>"]` biçimine dönüştürür.
* Diğer sembolleri (`Price_4H`, `BB_Width_4H` vb.) `data["..."]` olarak değerlendirir.
* Güvenlik için `eval` yalnızca boş builtins ile çalışır.

Bu sade yaklaşım karmaşık parantez iç içe geçme durumlarını ve matematiksel
operasyonları da destekler; ancak fonksiyon çağırılarını (EMA(...)) **dışarıda
bırakır**. İleri seviye gereksinimlerde `ast` modülüyle tam parser yazılabilir.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Mapping

__all__ = [
    "compile_formula",
    "evaluate_formula",
]

# regex kalıpları
_CFG_RE = re.compile(r"cfg\.([A-Za-z0-9_]+)")
# Değişken (EMA21_4H, OI_%1H vs.) – cfg hariç tüm kelimeler & sayı içeren
_VAR_RE = re.compile(r"\b(?!cfg\.)[A-Za-z0-9_%]+\b")

# Mantıksal operatörler
_OP_REPLACEMENTS = {
    "&": " and ",
    "|": " or ",
}


def _translate(expr: str) -> str:
    """YAML formülünü güvenli Python ifadesine dönüştürür."""
    # Mantıksal operatörler
    for k, v in _OP_REPLACEMENTS.items():
        expr = expr.replace(k, v)

    # cfg.<param> → cfg["param"]
    expr = _CFG_RE.sub(r'cfg["\1"]', expr)

    # Diğer semboller → data["symbol"]  
    def _var_sub(match: re.Match) -> str:
        token = match.group(0)
        # sayısal lit mi?
        if token.isdigit():
            return token
        # python boolean literalleri vs. es geç
        if token in {"and", "or", "not", "True", "False"}:
            return token
        return f'data.get("{token}")'

    expr = _VAR_RE.sub(_var_sub, expr)
    return expr


def compile_formula(expr: str):
    """Formülü derler ve geriye çağrılabilir fonksiyon döndürür."""
    py_expr = _translate(expr)
    code = compile(py_expr, "<formula>", "eval")

    def _fn(data: Mapping[str, Any], cfg: Mapping[str, Any]) -> Any:
        return eval(code, {"__builtins__": {}}, {"data": data, "cfg": cfg})

    return _fn


def evaluate_formula(expr: str, data: Dict[str, Any], cfg: Dict[str, Any]):
    """Tek seferlik değerlendirme yardımcı fonksiyonu."""
    return compile_formula(expr)(data, cfg)
