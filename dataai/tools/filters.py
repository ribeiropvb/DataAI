"""Condições de filtro declarativas (população das métricas).

Cada condição: {"column": "status", "op": "==", "value": "pago"}.
Operadores: ==, !=, >, >=, <, <=, in, not_in, is_null, not_null, contains, between.
Comparações de texto ignoram caixa e espaços nas pontas.
"""
from __future__ import annotations

import pandas as pd

OPS = ("==", "!=", ">", ">=", "<", "<=", "in", "not_in", "is_null", "not_null", "contains", "between")


def _coerce(series: pd.Series, value):
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(value)
    return value


def _txt(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.lower()


def condition_mask(df: pd.DataFrame, cond: dict) -> pd.Series:
    col, op, val = cond["column"], cond.get("op", "=="), cond.get("value")
    if col not in df.columns:
        raise KeyError(f"coluna inexistente no filtro: {col}")
    s = df[col]
    is_text = not (pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s) or s.dtype == "boolean")
    if op == "is_null":
        return s.isna()
    if op == "not_null":
        return s.notna()
    if op in ("in", "not_in"):
        vals = list(val or [])
        m = _txt(s).isin([str(v).strip().lower() for v in vals]) if is_text else s.isin(vals)
        m = m.fillna(False).astype(bool)
        return m if op == "in" else ~m & s.notna()
    if op == "contains":
        return _txt(s).str.contains(str(val).lower(), regex=False).fillna(False).astype(bool)
    if op == "between":
        lo, hi = (_coerce(s, v) for v in val)
        return s.between(lo, hi).fillna(False).astype(bool)
    v = _coerce(s, val)
    if is_text and op in ("==", "!="):
        m = _txt(s) == str(v).strip().lower()
        m = m.fillna(False).astype(bool)
        return m if op == "==" else ~m & s.notna()
    m = {"==": s == v, "!=": s != v, ">": s > v, ">=": s >= v, "<": s < v, "<=": s <= v}[op]
    return m.fillna(False).astype(bool)


def apply_conditions(df: pd.DataFrame, conds: list[dict]) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for c in conds or []:
        if c.get("op", "==") not in OPS:
            raise ValueError(f"operador inválido: {c.get('op')}")
        mask &= condition_mask(df, c)
    return mask
