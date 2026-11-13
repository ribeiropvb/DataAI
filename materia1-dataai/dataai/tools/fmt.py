"""Formatação de números para apresentação (pt-BR). Precisão total fica nos resultados."""
from __future__ import annotations

import math


def _br(x: float, decimals: int) -> str:
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def format_value(v, fmt: str | None = None) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "—"
    if isinstance(v, bool):
        return "sim" if v else "não"
    if not isinstance(v, (int, float)):
        return str(v)
    fmt = fmt or ("integer" if float(v).is_integer() and abs(v) >= 1 else "decimal_2")
    if fmt == "integer":
        return _br(round(v), 0)
    if fmt == "decimal_1":
        return _br(v, 1)
    if fmt == "decimal_2":
        return _br(v, 2)
    if fmt == "percent_0":
        return _br(v * 100, 0) + "%"
    if fmt == "percent_1":
        return _br(v * 100, 1) + "%"
    if fmt == "percent_2":
        return _br(v * 100, 2) + "%"
    if fmt == "pp_1":
        return _br(v * 100, 1) + " p.p."
    if fmt == "currency_brl":
        return "R$ " + _br(v, 2)
    if fmt == "currency_brl_compact":
        return "R$ " + compact(v)
    if fmt == "compact":
        return compact(v)
    if fmt == "days":
        return _br(v, 1) + " dias"
    if fmt == "index":
        return _br(v, 0)
    if fmt == "coef":
        return _br(v, 2)
    return _br(v, 2)


def compact(v: float) -> str:
    a = abs(v)
    for div, suf in ((1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if a >= div:
            return _br(v / div, 1) + suf
    return _br(v, 0) if float(v).is_integer() else _br(v, 2)


def guess_format(unit: str | None, field: str = "") -> str | None:
    f = field.lower()
    if unit in ("%", "fraction") or any(k in f for k in ("pct", "share", "rate", "retention", "attainment", "conv_")):
        return "percent_1"
    if unit in ("R$", "BRL"):
        return "currency_brl"
    if unit == "dias":
        return "days"
    if "index_100" in f:
        return "index"
    if f in ("coef",):
        return "coef"
    return None
