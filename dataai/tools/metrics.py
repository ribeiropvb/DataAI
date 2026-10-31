"""Catálogo de métricas do DataAI (specs.md 12.7, skill describe-data).

Cada função recebe um DataFrame (e parâmetros) e devolve um dicionário com:

- ``values``: escalares nomeados (o que relatório e dashboard citam);
- ``rows``: tabela de resultado (lista de registros), quando houver;
- ``n`` e ``excluded``: base efetiva e linhas excluídas por ausência/filtro;
- ``flags`` e ``warnings``: amostra pequena, período parcial, sensibilidade etc.

``compute(spec, ws)`` executa uma especificação de métrica sobre um dataset da análise,
anexa fórmula, população, linhagem e o próprio ``spec`` (que é o código reexecutável) e salva
o resultado versionado em ``results/``.
"""
from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
import pandas as pd

from .textutil import strip_accents

SMALL_SAMPLE = 30
SENSITIVE_THRESHOLD = 0.10
MAX_ROWS = 500
PERCENTILES = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
FREQ_ALIASES = {"D": "D", "W": "W", "M": "M", "Q": "Q", "Y": "Y", "dia": "D", "semana": "W", "mes": "M",
                "mês": "M", "trimestre": "Q", "ano": "Y"}


# =========================================================================== helpers

def _num(s: pd.Series) -> pd.Series:
    if s.dtype == "boolean" or s.dtype == bool:
        return s.astype("Float64").astype(float)
    return pd.to_numeric(s, errors="coerce").astype(float)


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(x) or math.isinf(x)) else x


def _safe_div(a, b) -> float | None:
    a, b = _f(a), _f(b)
    if a is None or b is None or b == 0:
        return None
    return a / b


def _records(df: pd.DataFrame, limit: int = MAX_ROWS) -> list[dict]:
    out = []
    for rec in df.head(limit).to_dict(orient="records"):
        clean = {}
        for k, v in rec.items():
            if isinstance(v, (pd.Timestamp,)):
                v = v.isoformat()
            elif isinstance(v, pd.Period):
                v = str(v)
            elif isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating, float)):
                v = _f(v)
            elif v is pd.NA or v is pd.NaT:
                v = None
            elif isinstance(v, (np.bool_,)):
                v = bool(v)
            clean[str(k)] = v
        out.append(clean)
    return out


def _result(values: dict | None = None, rows: list | None = None, n: int | None = None,
            excluded: int = 0, flags: dict | None = None, warnings: list | None = None,
            truncated: bool = False) -> dict:
    return {"values": {k: (_f(v) if isinstance(v, (float, np.floating)) else v) for k, v in (values or {}).items()},
            "rows": rows or [], "n": n, "excluded": int(excluded), "flags": flags or {},
            "warnings": warnings or [], "rows_truncated": truncated}


def _freq(freq: str) -> str:
    return FREQ_ALIASES.get(freq, freq)


def _period(s: pd.Series, freq: str) -> pd.Series:
    f = _freq(freq)
    return pd.to_datetime(s, errors="coerce").dt.to_period(f)


def _agg(series: pd.Series, agg: str) -> float:
    if agg == "count":
        return float(series.count())
    x = _num(series).dropna()
    if agg == "sum":
        return float(x.sum())
    if agg == "mean":
        return float(x.mean()) if len(x) else float("nan")
    if agg == "median":
        return float(x.median()) if len(x) else float("nan")
    if agg == "nunique":
        return float(series.nunique())
    raise ValueError(f"agregação desconhecida: {agg}")


def _grouped_agg(df: pd.DataFrame, keys: list[str] | str, measure: str | None, agg: str) -> pd.DataFrame:
    keys = [keys] if isinstance(keys, str) else list(keys)
    if measure is None or agg == "count" and measure is None:
        g = df.groupby(keys, dropna=False, observed=True).size().rename("value").reset_index()
        g["n"] = g["value"]
        return g
    tmp = df[keys].copy()
    tmp["_m"] = _num(df[measure]) if agg not in ("count", "nunique") else df[measure]
    gb = tmp.groupby(keys, dropna=False, observed=True)["_m"]
    if agg == "nunique":
        val = gb.nunique()
    elif agg == "count":
        val = gb.count()
    else:
        val = getattr(gb, agg)()
    out = val.rename("value").reset_index()
    out["n"] = gb.count().values
    return out


def _label(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA:
        return "(ausente)"
    return str(v)


# =========================================================================== M1 Qualidade

def quality_completeness(df: pd.DataFrame, columns: list[str] | None = None) -> dict:
    cols = columns or [c for c in df.columns if not c.startswith("_")]
    rows = []
    for c in cols:
        miss = int(df[c].isna().sum())
        rows.append({"column": c, "missing": miss, "missing_pct": miss / len(df) if len(df) else None,
                     "completeness": 1 - miss / len(df) if len(df) else None})
    complete_rows = int(df[cols].notna().all(axis=1).sum()) if len(df) else 0
    cells = len(df) * len(cols)
    return _result({"rows": len(df), "complete_rows": complete_rows,
                    "complete_rows_pct": _safe_div(complete_rows, len(df)),
                    "cell_completeness": 1 - _safe_div(sum(r["missing"] for r in rows), cells) if cells else None,
                    "worst_column": max(rows, key=lambda r: r["missing"])["column"] if rows else None},
                   sorted(rows, key=lambda r: -r["missing"]), n=len(df))


def quality_uniqueness(df: pd.DataFrame, keys: list[list[str]] | None = None) -> dict:
    cols = [c for c in df.columns if not c.startswith("_")]
    dup = int(df.duplicated(subset=cols).sum())
    rows = []
    for k in keys or []:
        k = [k] if isinstance(k, str) else k
        d = int(df.duplicated(subset=k).sum())
        rows.append({"key": "+".join(k), "duplicated_rows": d, "duplicated_pct": _safe_div(d, len(df)),
                     "null_keys": int(df[k].isna().any(axis=1).sum())})
    return _result({"duplicate_rows": dup, "duplicate_rows_pct": _safe_div(dup, len(df))}, rows, n=len(df))


def quality_validity(df: pd.DataFrame, measures: list[str] | None = None, dates: list[str] | None = None,
                     non_negative: list[str] | None = None, today: str | None = None) -> dict:
    today_ts = pd.Timestamp(today) if today else pd.Timestamp.now().normalize()
    rows = []
    for c in non_negative or []:
        x = _num(df[c])
        neg = int((x < 0).sum())
        rows.append({"column": c, "check": "negativos inesperados", "violations": neg, "pct": _safe_div(neg, x.notna().sum())})
    for c in dates or []:
        d = pd.to_datetime(df[c], errors="coerce")
        fut = int((d > today_ts).sum())
        old = int((d < pd.Timestamp("1900-01-01")).sum())
        rows.append({"column": c, "check": "datas futuras", "violations": fut, "pct": _safe_div(fut, d.notna().sum())})
        rows.append({"column": c, "check": "datas anteriores a 1900", "violations": old, "pct": _safe_div(old, d.notna().sum())})
    for c in measures or []:
        x = _num(df[c])
        bad = int(df[c].notna().sum() - x.notna().sum())
        rows.append({"column": c, "check": "valores não numéricos", "violations": bad, "pct": _safe_div(bad, df[c].notna().sum())})
    total_v = sum(r["violations"] for r in rows)
    return _result({"total_violations": total_v, "checks": len(rows)}, rows, n=len(df))


def _canon(v: str) -> str:
    return "".join(ch for ch in strip_accents(str(v)).lower() if ch.isalnum())


def quality_consistency(df: pd.DataFrame, categories: list[str] | None = None,
                        date_pairs: list[list[str]] | None = None) -> dict:
    rows = []
    for c in categories or []:
        s = df[c].dropna().astype(str)
        groups = s.groupby(s.map(_canon)).agg(lambda x: sorted(set(x)))
        for canon, variants in groups.items():
            if len(variants) > 1:
                rows.append({"column": c, "check": "grafias variantes", "detail": " | ".join(variants[:6]),
                             "violations": int(s.map(_canon).eq(canon).sum())})
    for a, b in date_pairs or []:
        da, db = pd.to_datetime(df[a], errors="coerce"), pd.to_datetime(df[b], errors="coerce")
        both = da.notna() & db.notna()
        v = int((db[both] < da[both]).sum())
        rows.append({"column": f"{a} -> {b}", "check": f"{b} anterior a {a}", "detail": "",
                     "violations": v, "pct": _safe_div(v, both.sum())})
    return _result({"issues": sum(1 for r in rows if r["violations"])}, rows, n=len(df))


def infer_date_pairs(df: pd.DataFrame, date_cols: list[str], min_order: float = 0.95) -> list[list[str]]:
    """Pares de datas em que b >= a em pelo menos 95% das linhas (ex.: abertura -> fechamento)."""
    pairs = []
    for i, a in enumerate(date_cols):
        for b in date_cols[i + 1:]:
            da, db = pd.to_datetime(df[a], errors="coerce"), pd.to_datetime(df[b], errors="coerce")
            both = da.notna() & db.notna()
            if both.sum() < 10:
                continue
            ge = (db[both] >= da[both]).mean()
            le = (db[both] <= da[both]).mean()
            if ge >= min_order and ge > le:
                pairs.append([a, b])
            elif le >= min_order and le > ge:
                pairs.append([b, a])
    return pairs


def quality_temporal_coverage(df: pd.DataFrame, date_col: str, freq: str = "M") -> dict:
    d = pd.to_datetime(df[date_col], errors="coerce")
    excl = int(d.isna().sum())
    d = d.dropna()
    if d.empty:
        return _result({"periods": 0}, n=0, excluded=excl, warnings=["sem datas válidas"])
    p = d.dt.to_period(_freq(freq))
    full = pd.period_range(p.min(), p.max(), freq=_freq(freq))
    present = set(p.unique())
    gaps = [str(x) for x in full if x not in present]
    first_partial = d.min() > p.min().start_time
    last_partial = d.max() < p.max().end_time.normalize()
    counts = p.value_counts().sort_index()
    rows = _records(pd.DataFrame({"period": [str(x) for x in counts.index], "rows": counts.values}))
    return _result({"min_date": d.min().isoformat(), "max_date": d.max().isoformat(), "periods": len(full),
                    "periods_without_records": len(gaps), "first_period_partial": bool(first_partial),
                    "last_period_partial": bool(last_partial)},
                   rows, n=len(d), excluded=excl, flags={"gaps": gaps[:50]})


# =========================================================================== M2 Volume

def volume_counts(df: pd.DataFrame, entity: str | None = None, date_col: str | None = None, freq: str = "M") -> dict:
    cols = [c for c in df.columns if not c.startswith("_")]
    rows = [{"column": c, "distinct": int(df[c].nunique()), "non_missing": int(df[c].notna().sum())} for c in cols]
    vals: dict[str, Any] = {"rows": len(df), "columns": len(cols)}
    if entity:
        per = df.groupby(entity, observed=True).size()
        vals.update({"entities": int(per.size), "events_per_entity_mean": float(per.mean()),
                     "events_per_entity_median": float(per.median()), "events_per_entity_max": int(per.max())})
    if date_col:
        p = _period(df[date_col], freq).dropna()
        if len(p):
            per_p = p.value_counts()
            vals.update({"periods": int(per_p.size), "rows_per_period_mean": float(per_p.mean())})
    return _result(vals, rows, n=len(df))


# =========================================================================== M3/M4 posição, dispersão

def _position(x: pd.Series, w: pd.Series | None = None) -> dict:
    x = x.dropna()
    if x.empty:
        return {"n": 0}
    out = {"n": int(len(x)), "mean": float(x.mean()), "median": float(x.median()),
           "min": float(x.min()), "max": float(x.max()), "sum": float(x.sum())}
    mode = x.mode()
    out["mode"] = float(mode.iloc[0]) if len(mode) and len(mode) < len(x) else None
    k = int(len(x) * 0.05)
    xs = np.sort(x.values)
    out["trimmed_mean_5"] = float(xs[k:len(xs) - k].mean()) if len(xs) - 2 * k > 0 else out["mean"]
    for q in PERCENTILES:
        out[f"p{int(round(q * 100))}"] = float(np.quantile(xs, q, method="linear"))
    if w is not None:
        ww = w.loc[x.index]
        ok = ww.notna()
        out["weighted_mean"] = _safe_div((x[ok] * ww[ok]).sum(), ww[ok].sum())
    return out


def position_stats(df: pd.DataFrame, column: str, weight: str | None = None, group_by: str | None = None) -> dict:
    x = _num(df[column])
    w = _num(df[weight]) if weight else None
    excl = int(x.isna().sum())
    vals = _position(x, w)
    rows = []
    flags = {}
    if group_by:
        small = []
        for g, idx in df.groupby(group_by, dropna=False, observed=True).groups.items():
            p = _position(x.loc[idx], w.loc[idx] if w is not None else None)
            p = {"group": _label(g), **{k: p.get(k) for k in ("n", "mean", "median", "p25", "p75", "min", "max", "sum")}}
            p["small_sample"] = (p["n"] or 0) < SMALL_SAMPLE
            if p["small_sample"]:
                small.append(p["group"])
            rows.append(p)
        rows.sort(key=lambda r: -(r["median"] if r["median"] is not None else -1e300))
        flags["small_sample_groups"] = small
    return _result(vals, rows, n=vals.get("n", 0), excluded=excl, flags=flags)


def _fd_bins(x: np.ndarray) -> int:
    if len(x) < 2:
        return 1
    q75, q25 = np.quantile(x, [0.75, 0.25])
    iqr = q75 - q25
    if iqr == 0:
        return min(10, max(1, len(np.unique(x))))
    h = 2 * iqr / (len(x) ** (1 / 3))
    return int(min(60, max(5, math.ceil((x.max() - x.min()) / h))))


def dispersion_shape(df: pd.DataFrame, column: str, histogram: bool = True) -> dict:
    x = _num(df[column])
    excl = int(x.isna().sum())
    x = x.dropna()
    if len(x) < 2:
        return _result({"n": int(len(x))}, n=int(len(x)), excluded=excl, warnings=["menos de 2 valores"])
    q1, q3 = np.quantile(x, [0.25, 0.75], method="linear")
    iqr = q3 - q1
    med = float(x.median())
    mad = float((x - med).abs().median())
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    out_iqr = int(((x < lo) | (x > hi)).sum())
    out_rz = int(((0.6745 * (x - med) / mad).abs() > 3.5).sum()) if mad > 0 else 0
    vals = {"n": int(len(x)), "std": float(x.std(ddof=1)), "var": float(x.var(ddof=1)),
            "range": float(x.max() - x.min()), "iqr": float(iqr), "q1": float(q1), "q3": float(q3),
            "mad": mad, "cv": float(x.std(ddof=1) / x.mean()) if (x > 0).all() and x.mean() != 0 else None,
            "skewness": float(x.skew()) if len(x) > 2 else None,
            "excess_kurtosis": float(x.kurt()) if len(x) > 3 else None,
            "outliers_iqr": out_iqr, "outliers_iqr_pct": out_iqr / len(x),
            "outliers_robust_z": out_rz, "fence_low": float(lo), "fence_high": float(hi)}
    rows = []
    if histogram:
        counts, edges = np.histogram(x.values, bins=_fd_bins(x.values))
        rows = [{"bin_start": float(edges[i]), "bin_end": float(edges[i + 1]), "count": int(c)} for i, c in enumerate(counts)]
    return _result(vals, rows, n=int(len(x)), excluded=excl)


# =========================================================================== M5 composição

def frequency_table(df: pd.DataFrame, column: str, top: int | None = 12, other_label: str = "Outros") -> dict:
    s = df[column]
    excl = int(s.isna().sum())
    vc = s.dropna().astype(str).value_counts()
    n = int(vc.sum())
    p = vc / n if n else vc
    entropy = float(-(p * np.log(p)).sum()) if n else 0.0
    k = len(vc)
    ent_norm = entropy / math.log(k) if k > 1 else 0.0
    t = pd.DataFrame({"category": vc.index, "count": vc.values})
    truncated = False
    if top and len(t) > top:
        rest = t.iloc[top - 1:]
        t = pd.concat([t.iloc[:top - 1], pd.DataFrame({"category": [other_label], "count": [rest["count"].sum()]})])
        truncated = True
    t["pct"] = t["count"] / n if n else None
    t["cum_pct"] = t["pct"].cumsum()
    vals = {"n": n, "categories": k, "mode": vc.index[0] if k else None,
            "mode_pct": float(p.iloc[0]) if k else None, "entropy_norm": ent_norm}
    return _result(vals, _records(t), n=n, excluded=excl,
                   flags={"grouped_other": truncated, "other_rule": f"top {top - 1} + Outros" if truncated else None})


def share_of_total(df: pd.DataFrame, category: str, measure: str, top: int | None = 12, other_label: str = "Outros") -> dict:
    x = _num(df[measure])
    excl = int(x.isna().sum())
    tmp = pd.DataFrame({"category": df[category].map(_label), "value": x}).dropna(subset=["value"])
    g = tmp.groupby("category")["value"].agg(["sum", "count"]).sort_values("sum", ascending=False)
    total = float(g["sum"].sum())
    t = pd.DataFrame({"category": g.index, "total": g["sum"].values, "n": g["count"].values})
    truncated = False
    if top and len(t) > top:
        rest = t.iloc[top - 1:]
        t = pd.concat([t.iloc[:top - 1], pd.DataFrame({"category": [other_label], "total": [rest["total"].sum()], "n": [rest["n"].sum()]})])
        truncated = True
    t["share"] = t["total"] / total if total else None
    t["cum_share"] = t["share"].cumsum()
    return _result({"total": total, "categories": int(len(g)), "top_category": t.iloc[0]["category"] if len(t) else None,
                    "top_share": float(t.iloc[0]["share"]) if len(t) and total else None},
                   _records(t), n=int(len(tmp)), excluded=excl, flags={"grouped_other": truncated},
                   warnings=["há valores negativos; participação pode exceder 100%"] if (tmp["value"] < 0).any() else [])


def crosstab(df: pd.DataFrame, row: str, col: str, measure: str | None = None, agg: str = "count", top: int = 12) -> dict:
    r, c = df[row].map(_label), df[col].map(_label)
    keep_r = r.value_counts().index[:top]
    keep_c = c.value_counts().index[:top]
    r = r.where(r.isin(keep_r), "Outros")
    c = c.where(c.isin(keep_c), "Outros")
    if measure:
        ct = pd.crosstab(r, c, values=_num(df[measure]), aggfunc=agg).fillna(0)
    else:
        ct = pd.crosstab(r, c)
    total = ct.values.sum()
    long = ct.stack().rename("value").reset_index()
    long.columns = ["row", "col", "value"]
    long["pct_row"] = long["value"] / long.groupby("row")["value"].transform("sum")
    long["pct_col"] = long["value"] / long.groupby("col")["value"].transform("sum")
    long["pct_total"] = long["value"] / total if total else None
    return _result({"total": float(total), "rows": int(ct.shape[0]), "cols": int(ct.shape[1])}, _records(long, 2000),
                   n=int(len(df)))


# =========================================================================== M6 concentração

def _gini(v: np.ndarray) -> float | None:
    v = np.sort(v[v >= 0])
    n = len(v)
    if n == 0 or v.sum() == 0:
        return None
    cum = np.cumsum(v)
    return float((n + 1 - 2 * (cum / cum[-1]).sum()) / n)


def concentration(df: pd.DataFrame, item: str, measure: str | None = None) -> dict:
    if measure:
        x = _num(df[measure])
        excl = int(x.isna().sum())
        agg = pd.DataFrame({"item": df[item], "v": x}).dropna().groupby("item")["v"].sum()
    else:
        excl = int(df[item].isna().sum())
        agg = df[item].dropna().value_counts()
    agg = agg.sort_values(ascending=False)
    warns = []
    if (agg < 0).any():
        warns.append("medida com totais negativos por item; concentração calculada só com itens não negativos")
        agg = agg[agg >= 0]
    total = float(agg.sum())
    n_items = len(agg)
    share = agg / total if total else agg * 0
    cum = share.cumsum()

    def top_share(k):
        return float(share.iloc[:k].sum()) if n_items else None

    k20 = max(1, int(math.ceil(n_items * 0.2)))
    vals = {"items": n_items, "total": total, "top1_share": top_share(1), "top5_share": top_share(5),
            "top10_share": top_share(10), "top20pct_items_share": top_share(k20),
            "items_for_80pct": int((cum < 0.8).sum() + 1) if n_items else None,
            "items_for_80pct_share_of_items": _safe_div(int((cum < 0.8).sum() + 1), n_items) if n_items else None,
            "gini": _gini(agg.values.astype(float)), "hhi": float(((share * 100) ** 2).sum()) if total else None}
    rows = _records(pd.DataFrame({"item": agg.index.astype(str), "total": agg.values, "share": share.values,
                                  "cum_share": cum.values}), 50)
    return _result(vals, rows, n=int(agg.size), excluded=excl, warnings=warns, truncated=n_items > 50)


def pareto_abc(df: pd.DataFrame, item: str, measure: str, a: float = 0.8, b: float = 0.95) -> dict:
    base = concentration(df, item, measure)
    x = _num(df[measure])
    agg = pd.DataFrame({"item": df[item], "v": x}).dropna().groupby("item")["v"].sum().sort_values(ascending=False)
    agg = agg[agg >= 0]
    total = agg.sum()
    cum = agg.cumsum() / total if total else agg * 0
    prev = cum.shift(fill_value=0)
    cls = np.where(prev < a, "A", np.where(prev < b, "B", "C"))
    t = pd.DataFrame({"item": agg.index.astype(str), "total": agg.values, "cum_share": cum.values, "class": cls})
    summary = t.groupby("class").agg(items=("item", "count"), total=("total", "sum")).reset_index()
    summary["share_items"] = summary["items"] / len(t) if len(t) else None
    summary["share_total"] = summary["total"] / total if total else None
    vals = {**base["values"], **{f"class_{r['class']}_items": int(r["items"]) for _, r in summary.iterrows()},
            **{f"class_{r['class']}_share_total": float(r["share_total"]) for _, r in summary.iterrows()}}
    return _result(vals, _records(summary), n=base["n"], excluded=base["excluded"],
                   flags={"thresholds": {"A": a, "B": b}})


# =========================================================================== M7 tempo

def _series(df, date_col, measure, agg, freq, group_by=None):
    p = _period(df[date_col], freq)
    excl = int(p.isna().sum())
    tmp = df.assign(_period=p).dropna(subset=["_period"])
    keys = ["_period"] + ([group_by] if group_by else [])
    g = _grouped_agg(tmp, keys, measure, agg if measure else "count")
    d = pd.to_datetime(tmp[date_col])
    return g, excl, d.min(), d.max()


def _partial_flags(periods: pd.Series, dmin, dmax) -> pd.Series:
    first, last = periods.min(), periods.max()
    flags = pd.Series(False, index=periods.index)
    if dmin is not None and dmin > first.start_time:
        flags |= periods == first
    if dmax is not None and dmax.normalize() < last.end_time.normalize():
        flags |= periods == last
    return flags


def time_series(df: pd.DataFrame, date_col: str, measure: str | None = None, agg: str = "sum", freq: str = "M",
                group_by: str | None = None, moving_average: int | None = 3, fill_gaps: bool = True) -> dict:
    g, excl, dmin, dmax = _series(df, date_col, measure, agg, freq, group_by)
    if g.empty:
        return _result({"periods": 0}, n=0, excluded=excl)
    if group_by:
        g["partial_period"] = _partial_flags(g["_period"], dmin, dmax)
        g["period"] = g["_period"].astype(str)
        g = g.rename(columns={group_by: "group"}).sort_values(["group", "_period"])
        g["change_pct"] = g.groupby("group")["value"].pct_change(fill_method=None)
        rows = _records(g.drop(columns=["_period"]), 2000)
        return _result({"periods": int(g["_period"].nunique()), "groups": int(g["group"].nunique())}, rows,
                       n=int(g["n"].sum()), excluded=excl)
    g = g.set_index("_period").sort_index()
    if fill_gaps:
        full = pd.period_range(g.index.min(), g.index.max(), freq=g.index.freq)
        fill_value = 0 if (agg in ("sum", "count") or measure is None) else np.nan
        g = g.reindex(full)
        g["value"] = g["value"].fillna(fill_value) if fill_value == 0 else g["value"]
        g["n"] = g["n"].fillna(0)
    g.index.name = "_period"
    g = g.reset_index()
    g["partial_period"] = _partial_flags(g["_period"], dmin, dmax)
    g["change_abs"] = g["value"].diff()
    g["change_pct"] = g["value"].pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    if moving_average and moving_average > 1:
        g[f"moving_avg_{moving_average}"] = g["value"].rolling(moving_average).mean()
    if _freq(freq) == "M" and len(g) >= 13:
        g["yoy_pct"] = g["value"].pct_change(12, fill_method=None).replace([np.inf, -np.inf], np.nan)
    if _freq(freq) in ("M", "Q", "W", "D") and agg in ("sum", "count"):
        years = g["_period"].map(lambda p: p.start_time.year)
        g["ytd"] = g.groupby(years)["value"].cumsum()
    g["period"] = g["_period"].astype(str)
    complete = g[~g["partial_period"]]
    vals = {"periods": int(len(g)), "partial_periods": int(g["partial_period"].sum()),
            "first_period": g["period"].iloc[0], "last_period": g["period"].iloc[-1],
            "last_complete_period": complete["period"].iloc[-1] if len(complete) else None,
            "last_complete_value": float(complete["value"].iloc[-1]) if len(complete) else None,
            "total": float(g["value"].sum()) if agg in ("sum", "count") else None}
    return _result(vals, _records(g.drop(columns=["_period"]), 2000), n=int(g["n"].sum()), excluded=excl,
                   flags={"partial_periods": g.loc[g["partial_period"], "period"].tolist()})


def period_change(df: pd.DataFrame, date_col: str, measure: str | None = None, agg: str = "sum", freq: str = "M",
                  current: str | None = None, previous: str | None = None) -> dict:
    ts = time_series(df, date_col, measure, agg, freq, moving_average=None)
    rows = ts["rows"]
    complete = [r for r in rows if not r["partial_period"]]
    if current is None:
        if len(complete) < 2:
            return _result({}, n=ts["n"], warnings=["menos de dois períodos completos"])
        cur, prev = complete[-1], complete[-2]
    else:
        by = {r["period"]: r for r in rows}
        cur, prev = by.get(current), by.get(previous)
        if not cur or not prev:
            return _result({}, warnings=[f"período {current} ou {previous} inexistente"])
    vals = {"current_period": cur["period"], "previous_period": prev["period"], "current": cur["value"],
            "previous": prev["value"], "change_abs": (cur["value"] or 0) - (prev["value"] or 0),
            "change_pct": _safe_div((cur["value"] or 0) - (prev["value"] or 0), prev["value"])}
    return _result(vals, [prev, cur], n=ts["n"])


def trend_summary(df: pd.DataFrame, date_col: str, measure: str | None = None, agg: str = "sum", freq: str = "M") -> dict:
    ts = time_series(df, date_col, measure, agg, freq, moving_average=None)
    rows = [r for r in ts["rows"] if not r["partial_period"] and r["value"] is not None]
    if len(rows) < 3:
        return _result({"complete_periods": len(rows)}, n=ts["n"], warnings=["menos de 3 períodos completos"])
    y = np.array([r["value"] for r in rows], dtype=float)
    t = np.arange(len(y))
    slope, intercept = np.polyfit(t, y, 1)
    changes = pd.Series(y).pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
    vals = {"complete_periods": len(rows), "first_period": rows[0]["period"], "last_period": rows[-1]["period"],
            "first_value": float(y[0]), "last_value": float(y[-1]), "total_change_abs": float(y[-1] - y[0]),
            "total_change_pct": _safe_div(y[-1] - y[0], y[0]), "slope_per_period": float(slope),
            "slope_pct_of_mean": _safe_div(slope, y.mean()),
            "direction": "alta" if slope > 0 and abs(_safe_div(slope, y.mean()) or 0) > 0.005 else
                         "queda" if slope < 0 and abs(_safe_div(slope, y.mean()) or 0) > 0.005 else "estável",
            "volatility": float(changes.std(ddof=1)) if len(changes) > 1 else None,
            "peak_period": rows[int(y.argmax())]["period"], "peak_value": float(y.max()),
            "trough_period": rows[int(y.argmin())]["period"], "trough_value": float(y.min())}
    # CAGR com anos completos
    d = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if not d.empty and agg in ("sum", "count"):
        yearly = time_series(df, date_col, measure, agg, "Y", moving_average=None)["rows"]
        full = [r for r in yearly if not r["partial_period"]]
        if len(full) >= 2 and full[0]["value"] and full[0]["value"] > 0 and full[-1]["value"] > 0:
            yrs = len(full) - 1
            vals["cagr"] = (full[-1]["value"] / full[0]["value"]) ** (1 / yrs) - 1
            vals["cagr_years"] = f"{full[0]['period']}-{full[-1]['period']}"
    return _result(vals, rows, n=ts["n"], flags={"method": "mínimos quadrados sobre períodos completos; descritivo"})


def seasonal_profile(df: pd.DataFrame, date_col: str, measure: str | None = None, agg: str = "sum", by: str = "month") -> dict:
    d = pd.to_datetime(df[date_col], errors="coerce")
    excl = int(d.isna().sum())
    tmp = df.assign(_d=d).dropna(subset=["_d"])
    if by == "month":
        tmp["_unit"] = tmp["_d"].dt.to_period("M")
        bucket = lambda u: u.month
        names = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    elif by == "weekday":
        tmp["_unit"] = tmp["_d"].dt.normalize()
        bucket = lambda u: u.weekday() + 1
        names = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    elif by == "hour":
        tmp["_unit"] = tmp["_d"].dt.floor("h")
        bucket = lambda u: u.hour + 1
        names = [f"{h:02d}h" for h in range(24)]
    else:
        raise ValueError("by deve ser month, weekday ou hour")
    g = _grouped_agg(tmp, ["_unit"], measure, agg if measure else "count")
    g["bucket"] = g["_unit"].map(bucket)
    prof = g.groupby("bucket")["value"].agg(["mean", "count"]).reset_index()
    prof["label"] = prof["bucket"].map(lambda b: names[b - 1])
    overall = prof["mean"].mean()
    prof["index_100"] = prof["mean"] / overall * 100 if overall else None
    vals = {"peak": prof.loc[prof["mean"].idxmax(), "label"] if len(prof) else None,
            "trough": prof.loc[prof["mean"].idxmin(), "label"] if len(prof) else None,
            "peak_to_trough_ratio": _safe_div(prof["mean"].max(), prof["mean"].min()) if len(prof) else None,
            "units_observed": int(len(g))}
    return _result(vals, _records(prof.rename(columns={"mean": "value", "count": "units"})[["label", "bucket", "value", "units", "index_100"]]),
                   n=int(len(tmp)), excluded=excl, flags={"by": by})


# =========================================================================== M8 comparação

def group_comparison(df: pd.DataFrame, group: str, measure: str | None = None, agg: str = "mean", top: int | None = 30) -> dict:
    g = _grouped_agg(df, [group], measure, agg if measure else "count")
    g = g.rename(columns={group: "group"})
    g["group"] = g["group"].map(_label)
    overall = _agg(df[measure], agg) if measure else float(len(df)) / max(len(g), 1)
    excl = int(df[measure].isna().sum()) if measure else 0
    g["diff_vs_overall"] = g["value"] - overall
    g["rel_diff_vs_overall"] = g["value"] / overall - 1 if overall else None
    g["index_100"] = g["value"] / overall * 100 if overall else None
    g["rank"] = g["value"].rank(ascending=False, method="min").astype(int)
    g["small_sample"] = g["n"] < SMALL_SAMPLE
    g = g.sort_values("value", ascending=False)
    hi, lo = g.iloc[0], g.iloc[-1]
    vals = {"overall": overall, "groups": int(len(g)), "max_group": hi["group"], "max_value": float(hi["value"]),
            "min_group": lo["group"], "min_value": float(lo["value"]), "max_min_diff": float(hi["value"] - lo["value"]),
            "max_min_ratio": _safe_div(hi["value"], lo["value"]),
            "overall_basis": "mesma agregação sobre todas as linhas" if measure else "média de linhas por grupo"}
    return _result(vals, _records(g, top or MAX_ROWS), n=int(g["n"].sum()), excluded=excl,
                   flags={"small_sample_groups": g.loc[g["small_sample"], "group"].tolist()},
                   truncated=bool(top and len(g) > top))


def compare_to_reference(df: pd.DataFrame, actual: str, reference: str | None = None, reference_value: float | None = None,
                         group_by: str | None = None, agg: str = "sum", reference_label: str = "meta") -> dict:
    if reference is None and reference_value is None:
        return _result({}, warnings=["sem referência (coluna ou valor informado); não calculado (P-019)"])

    def one(sub):
        a = _agg(sub[actual], agg)
        r = _agg(sub[reference], agg) if reference else float(reference_value)
        return {"actual": a, "reference": r, "attainment": _safe_div(a, r), "gap": a - r if r is not None else None}

    vals = one(df)
    vals["reference_label"] = reference_label
    rows = []
    if group_by:
        for g, sub in df.groupby(group_by, dropna=False, observed=True):
            rows.append({"group": _label(g), **one(sub), "n": int(len(sub))})
        rows.sort(key=lambda r: (r["attainment"] is None, -(r["attainment"] or 0)))
        vals["groups_below_reference"] = sum(1 for r in rows if r["attainment"] is not None and r["attainment"] < 1)
    return _result(vals, rows, n=int(len(df)))


# =========================================================================== M9 taxas

def _mask(df: pd.DataFrame, conds: list[dict]) -> pd.Series:
    from .filters import apply_conditions
    return apply_conditions(df, conds)


def _num_den(df: pd.DataFrame, numerator: dict, denominator: dict | None) -> tuple[pd.Series, pd.Series]:
    if "filter" in numerator:
        num = _mask(df, numerator["filter"]).astype(float)
    else:
        num = _num(df[numerator["column"]])
    if denominator is None or denominator == {}:
        den = pd.Series(1.0, index=df.index)
    elif "filter" in denominator:
        den = _mask(df, denominator["filter"]).astype(float)
    else:
        den = _num(df[denominator["column"]])
    return num, den


def rate(df: pd.DataFrame, numerator: dict, denominator: dict | None = None, group_by: str | None = None) -> dict:
    """Taxa = Σnumerador / Σdenominador. ``numerator``/``denominator``: {"column": c} ou {"filter": [condições]}."""
    num, den = _num_den(df, numerator, denominator)
    ok = num.notna() & den.notna()
    excl = int((~ok).sum())
    vals = {"numerator": float(num[ok].sum()), "denominator": float(den[ok].sum())}
    vals["rate"] = _safe_div(vals["numerator"], vals["denominator"])
    warns = [] if vals["denominator"] else ["denominador zero: taxa ausente (division_by_zero)"]
    rows, flags = [], {}
    if group_by:
        t = pd.DataFrame({"g": df[group_by].map(_label), "num": num, "den": den})[ok]
        gg = t.groupby("g").agg(numerator=("num", "sum"), denominator=("den", "sum"), n=("num", "size")).reset_index()
        gg["rate"] = [_safe_div(a, b) for a, b in zip(gg["numerator"], gg["denominator"])]
        gg["small_sample"] = gg["n"] < SMALL_SAMPLE
        gg = gg.rename(columns={"g": "group"}).sort_values("rate", ascending=False, na_position="last")
        rows = _records(gg)
        rates = [r for r in gg["rate"] if r is not None]
        vals["mean_of_group_rates"] = float(np.mean(rates)) if rates else None
        vals["aggregate_minus_mean_of_rates"] = (vals["rate"] - vals["mean_of_group_rates"]) if rates and vals["rate"] is not None else None
        flags["small_sample_groups"] = gg.loc[gg["small_sample"], "group"].tolist()
    return _result(vals, rows, n=int(ok.sum()), excluded=excl, flags=flags, warnings=warns)


def funnel(df: pd.DataFrame, steps: list[dict], entity: str | None = None) -> dict:
    """Etapas sequenciais. Cada etapa: {"label", "filter": [...] } ou {"label", "column"} (não ausente/verdadeiro)."""
    alive = pd.Series(True, index=df.index)
    rows, first = [], None
    for st in steps:
        if "filter" in st:
            m = _mask(df, st["filter"])
        else:
            col = df[st["column"]]
            m = col.fillna(False).astype(bool) if col.dtype == "boolean" or col.dtype == bool else col.notna()
        alive &= m
        cnt = int(df.loc[alive, entity].nunique()) if entity else int(alive.sum())
        first = cnt if first is None else first
        prev = rows[-1]["count"] if rows else None
        rows.append({"step": st["label"], "count": cnt, "conv_from_prev": _safe_div(cnt, prev) if prev is not None else 1.0,
                     "conv_from_start": _safe_div(cnt, first)})
    worst = min(rows[1:], key=lambda r: r["conv_from_prev"] if r["conv_from_prev"] is not None else 2) if len(rows) > 1 else None
    return _result({"start": rows[0]["count"] if rows else 0, "end": rows[-1]["count"] if rows else 0,
                    "overall_conversion": rows[-1]["conv_from_start"] if rows else None,
                    "largest_drop_step": worst["step"] if worst else None}, rows, n=int(len(df)))


def simpson_check(df: pd.DataFrame, group: str, stratum: str, numerator: dict, denominator: dict | None = None,
                  groups: list[str] | None = None) -> dict:
    num, den = _num_den(df, numerator, denominator)
    t = pd.DataFrame({"g": df[group].map(_label), "s": df[stratum].map(_label), "num": num, "den": den}).dropna()
    if groups is None:
        groups = t["g"].value_counts().index[:2].tolist()
    if len(groups) < 2:
        return _result({}, warnings=["menos de dois grupos"])
    a, b = groups[:2]
    t = t[t["g"].isin([a, b])]

    def r(sub):
        return _safe_div(sub["num"].sum(), sub["den"].sum())

    ra, rb = r(t[t["g"] == a]), r(t[t["g"] == b])
    overall_sign = np.sign((ra or 0) - (rb or 0))
    rows, signs = [], []
    for s, sub in t.groupby("s"):
        sa, sb = r(sub[sub["g"] == a]), r(sub[sub["g"] == b])
        if sa is None or sb is None:
            continue
        sg = np.sign(sa - sb)
        signs.append(sg)
        rows.append({"stratum": s, f"rate_{a}": sa, f"rate_{b}": sb, "diff": sa - sb,
                     "n": int(len(sub))})
    reversed_ = bool(signs) and overall_sign != 0 and all(sg == -overall_sign for sg in signs if sg != 0) and any(signs)
    vals = {"group_a": a, "group_b": b, "overall_rate_a": ra, "overall_rate_b": rb,
            "overall_diff": (ra or 0) - (rb or 0), "strata": len(rows), "simpson_reversal": reversed_}
    warns = [f"paradoxo de Simpson: a diferença entre {a} e {b} no total se inverte dentro de {stratum}"] if reversed_ else []
    return _result(vals, rows, n=int(len(t)), flags={"simpson_reversal": reversed_}, warnings=warns)


# =========================================================================== M10 decomposição

def _two_periods(p: pd.Series, period_a, period_b, dmin, dmax):
    periods = sorted(p.dropna().unique())
    if period_a and period_b:
        return pd.Period(period_a), pd.Period(period_b)
    flags = _partial_flags(pd.Series(periods), dmin, dmax)
    complete = [x for x, f in zip(periods, flags) if not f]
    if len(complete) < 2:
        return None, None
    return complete[-2], complete[-1]


def contribution_to_change(df: pd.DataFrame, date_col: str, group: str, measure: str | None = None, agg: str = "sum",
                           freq: str = "M", period_a: str | None = None, period_b: str | None = None, top: int = 15) -> dict:
    if agg not in ("sum", "count"):
        return _result({}, warnings=["contribuição exige métrica aditiva (sum ou count)"])
    p = _period(df[date_col], freq)
    d = pd.to_datetime(df[date_col], errors="coerce")
    a, b = _two_periods(p, period_a and pd.Period(period_a, freq=_freq(freq)), period_b and pd.Period(period_b, freq=_freq(freq)), d.min(), d.max())
    if a is None:
        return _result({}, warnings=["menos de dois períodos completos"])
    tmp = df.assign(_p=p)
    tmp = tmp[tmp["_p"].isin([a, b])]
    g = _grouped_agg(tmp, ["_p", group], measure, agg if measure else "count")
    pv = g.pivot_table(index=group, columns="_p", values="value", aggfunc="sum", observed=True).reindex(columns=[a, b]).fillna(0)
    pv.columns = ["value_a", "value_b"]
    pv["delta"] = pv["value_b"] - pv["value_a"]
    total_a, total_b = float(pv["value_a"].sum()), float(pv["value_b"].sum())
    dt_ = total_b - total_a
    pv["contribution"] = pv["delta"] / dt_ if dt_ else None
    pv = pv.reset_index().rename(columns={group: "group"})
    pv["group"] = pv["group"].map(_label)
    pv = pv.reindex(pv["delta"].abs().sort_values(ascending=False).index)
    vals = {"period_a": str(a), "period_b": str(b), "total_a": total_a, "total_b": total_b, "total_delta": dt_,
            "total_delta_pct": _safe_div(dt_, total_a), "top_contributor": pv.iloc[0]["group"] if len(pv) else None,
            "top_contribution": _f(pv.iloc[0]["contribution"]) if len(pv) and dt_ else None}
    return _result(vals, _records(pv, top), n=int(len(tmp)), truncated=len(pv) > top)


def mix_rate_decomposition(df: pd.DataFrame, date_col: str, group: str, value: str | None = None,
                           numerator: dict | None = None, denominator: dict | None = None, freq: str = "M",
                           period_a: str | None = None, period_b: str | None = None) -> dict:
    """Decompõe a variação de uma média (``value``) ou taxa (``numerator``/``denominator``) em efeito
    composição (mix) e efeito desempenho (rate), por shift-share com pesos médios (exato)."""
    p = _period(df[date_col], freq)
    d = pd.to_datetime(df[date_col], errors="coerce")
    a, b = _two_periods(p, period_a and pd.Period(period_a, freq=_freq(freq)), period_b and pd.Period(period_b, freq=_freq(freq)), d.min(), d.max())
    if a is None:
        return _result({}, warnings=["menos de dois períodos completos"])
    if value is not None:
        num, den = _num(df[value]), pd.Series(1.0, index=df.index)
    else:
        num, den = _num_den(df, numerator, denominator)
    t = pd.DataFrame({"p": p, "g": df[group].map(_label), "num": num, "den": den}).dropna()
    t = t[t["p"].isin([a, b])]
    agg = t.groupby(["p", "g"]).agg(num=("num", "sum"), den=("den", "sum")).reset_index()
    out = {}
    for per in (a, b):
        sub = agg[agg["p"] == per].set_index("g")
        out[per] = sub
    groups = sorted(set(out[a].index) | set(out[b].index))
    rows = []
    tot_mix = tot_rate = 0.0
    den_a, den_b = out[a]["den"].sum(), out[b]["den"].sum()
    for g in groups:
        wa = out[a]["den"].get(g, 0) / den_a if den_a else 0
        wb = out[b]["den"].get(g, 0) / den_b if den_b else 0
        ra = _safe_div(out[a]["num"].get(g, np.nan), out[a]["den"].get(g, np.nan))
        rb = _safe_div(out[b]["num"].get(g, np.nan), out[b]["den"].get(g, np.nan))
        ra = rb if ra is None else ra
        rb = ra if rb is None else rb
        ra = ra or 0.0
        rb = rb or 0.0
        mix = (wb - wa) * (ra + rb) / 2
        rte = (rb - ra) * (wa + wb) / 2
        tot_mix += mix
        tot_rate += rte
        rows.append({"group": g, "weight_a": wa, "weight_b": wb, "rate_a": ra, "rate_b": rb,
                     "mix_effect": mix, "rate_effect": rte, "total_effect": mix + rte})
    overall_a = _safe_div(out[a]["num"].sum(), den_a)
    overall_b = _safe_div(out[b]["num"].sum(), den_b)
    rows.sort(key=lambda r: -abs(r["total_effect"]))
    vals = {"period_a": str(a), "period_b": str(b), "overall_a": overall_a, "overall_b": overall_b,
            "overall_change": (overall_b or 0) - (overall_a or 0), "mix_effect": tot_mix, "rate_effect": tot_rate,
            "check_residual": ((overall_b or 0) - (overall_a or 0)) - (tot_mix + tot_rate)}
    return _result(vals, rows, n=int(len(t)), flags={"method": "shift-share com pesos médios"})


# =========================================================================== M11 entidades

def entity_rfm(df: pd.DataFrame, entity: str, date_col: str, measure: str | None = None, ref_date: str | None = None) -> dict:
    d = pd.to_datetime(df[date_col], errors="coerce")
    t = pd.DataFrame({"e": df[entity], "d": d})
    if measure:
        t["v"] = _num(df[measure])
    excl = int(t[["e", "d"]].isna().any(axis=1).sum())
    t = t.dropna(subset=["e", "d"])
    ref = pd.Timestamp(ref_date) if ref_date else t["d"].max()
    agg = t.groupby("e").agg(last=("d", "max"), first=("d", "min"), frequency=("d", "size"),
                             **({"monetary": ("v", "sum")} if measure else {}))
    agg["recency_days"] = (ref - agg["last"]).dt.days
    agg["r_score"] = 6 - _quintile(agg["recency_days"])
    agg["f_score"] = _quintile(agg["frequency"])
    if measure:
        agg["m_score"] = _quintile(agg["monetary"])
    seg = agg.groupby("r_score").agg(entities=("frequency", "size"), frequency_mean=("frequency", "mean"),
                                     recency_median=("recency_days", "median"),
                                     **({"monetary_total": ("monetary", "sum")} if measure else {})).reset_index()
    if measure:
        tot = seg["monetary_total"].sum()
        seg["monetary_share"] = seg["monetary_total"] / tot if tot else None
    gaps = t.sort_values("d").groupby("e")["d"].diff().dt.days.dropna()
    vals = {"entities": int(len(agg)), "reference_date": ref.isoformat(), "recency_median_days": float(agg["recency_days"].median()),
            "frequency_mean": float(agg["frequency"].mean()), "frequency_median": float(agg["frequency"].median()),
            "single_event_entities_pct": float((agg["frequency"] == 1).mean()),
            "interevent_median_days": float(gaps.median()) if len(gaps) else None}
    if measure:
        m = agg["monetary"].sort_values(ascending=False)
        k = max(1, int(math.ceil(len(m) * 0.2)))
        vals.update({"monetary_mean": float(m.mean()), "monetary_median": float(m.median()),
                     "top20pct_entities_value_share": _safe_div(m.iloc[:k].sum(), m.sum())})
    return _result(vals, _records(seg), n=int(len(t)), excluded=excl, flags={"score_method": "quintis (5 = melhor)"})


def _quintile(s: pd.Series) -> pd.Series:
    r = s.rank(method="first", pct=True)
    return np.ceil(r * 5).clip(1, 5).astype(int)


def cohort_retention(df: pd.DataFrame, entity: str, date_col: str, freq: str = "M", max_age: int = 12) -> dict:
    p = _period(df[date_col], freq)
    t = pd.DataFrame({"e": df[entity], "p": p}).dropna().drop_duplicates()
    first = t.groupby("e")["p"].min().rename("cohort")
    t = t.join(first, on="e")
    t["age"] = (t["p"] - t["cohort"]).map(lambda x: x.n)
    t = t[t["age"] <= max_age]
    m = t.groupby(["cohort", "age"])["e"].nunique().rename("active").reset_index()
    size = m[m["age"] == 0].set_index("cohort")["active"]
    m["cohort_size"] = m["cohort"].map(size)
    m["retention"] = m["active"] / m["cohort_size"]
    m["cohort"] = m["cohort"].astype(str)
    by_age = m.groupby("age").apply(lambda g: _safe_div(g["active"].sum(), g["cohort_size"].sum()), include_groups=False)
    vals = {"cohorts": int(size.size), "entities": int(first.size),
            "retention_age_1": _f(by_age.get(1)), "retention_age_3": _f(by_age.get(3)),
            "retention_age_6": _f(by_age.get(6))}
    return _result(vals, _records(m, 2000), n=int(len(t)), flags={"freq": freq, "note": "coortes recentes têm menos idades observadas"})


def new_vs_returning(df: pd.DataFrame, entity: str, date_col: str, freq: str = "M") -> dict:
    p = _period(df[date_col], freq)
    t = pd.DataFrame({"e": df[entity], "p": p}).dropna().drop_duplicates()
    first = t.groupby("e")["p"].min()
    t["new"] = t["p"] == t["e"].map(first)
    g = t.groupby("p").agg(active=("e", "nunique"), new=("new", "sum")).reset_index()
    g["returning"] = g["active"] - g["new"]
    g["new_share"] = g["new"] / g["active"]
    g["period"] = g["p"].astype(str)
    return _result({"periods": int(len(g)), "new_share_mean": float(g["new_share"].iloc[1:].mean()) if len(g) > 1 else None},
                   _records(g.drop(columns=["p"])), n=int(len(t)))


# =========================================================================== M12 prazos

def _duration(df, start, end, unit):
    a, b = pd.to_datetime(df[start], errors="coerce"), pd.to_datetime(df[end], errors="coerce")
    div = {"days": 86400, "hours": 3600, "minutes": 60}[unit]
    return (b - a).dt.total_seconds() / div


def durations(df: pd.DataFrame, start: str, end: str, unit: str = "days", group_by: str | None = None) -> dict:
    dur = _duration(df, start, end, unit)
    neg = int((dur < 0).sum())
    tmp = df.assign(_dur=dur.where(dur >= 0))
    res = position_stats(tmp, "_dur", group_by=group_by)
    res["values"]["negative_durations"] = neg
    res["values"]["unit"] = unit
    res["values"]["open_items"] = int(pd.to_datetime(df[end], errors="coerce").isna().sum())
    if neg:
        res["warnings"].append(f"{neg} durações negativas (fim antes do início) ficaram fora do cálculo")
    return res


def deadline_compliance(df: pd.DataFrame, end: str, deadline: str | None = None, start: str | None = None,
                        limit: float | None = None, unit: str = "days", ref_date: str | None = None,
                        group_by: str | None = None) -> dict:
    e = pd.to_datetime(df[end], errors="coerce")
    if deadline:
        dl = pd.to_datetime(df[deadline], errors="coerce")
        delay = (e - dl).dt.total_seconds() / {"days": 86400, "hours": 3600, "minutes": 60}[unit]
    elif start and limit is not None:
        delay = _duration(df, start, end, unit) - float(limit)
        dl = pd.to_datetime(df[start], errors="coerce") + pd.to_timedelta(float(limit), unit={"days": "D", "hours": "h", "minutes": "min"}[unit])
    else:
        return _result({}, warnings=["informe deadline (coluna) ou start + limit"])
    closed = e.notna() & delay.notna()
    on_time = closed & (delay <= 0)
    late = closed & (delay > 0)
    ref = pd.Timestamp(ref_date) if ref_date else max(e.max(), pd.to_datetime(df[start], errors="coerce").max() if start else e.max())
    open_ = e.isna()
    overdue_open = open_ & (dl < ref)
    vals = {"closed": int(closed.sum()), "on_time": int(on_time.sum()), "late": int(late.sum()),
            "on_time_pct": _safe_div(on_time.sum(), closed.sum()),
            "mean_delay_late": float(delay[late].mean()) if late.any() else None,
            "median_delay_late": float(delay[late].median()) if late.any() else None,
            "open_items": int(open_.sum()), "open_overdue": int(overdue_open.sum()), "unit": unit,
            "reference_date": ref.isoformat() if pd.notna(ref) else None}
    rows = []
    if group_by:
        t = pd.DataFrame({"g": df[group_by].map(_label), "closed": closed, "on_time": on_time})
        gg = t.groupby("g").agg(closed=("closed", "sum"), on_time=("on_time", "sum"), n=("closed", "size")).reset_index()
        gg["on_time_pct"] = [_safe_div(a, b) for a, b in zip(gg["on_time"], gg["closed"])]
        gg["small_sample"] = gg["closed"] < SMALL_SAMPLE
        rows = _records(gg.rename(columns={"g": "group"}).sort_values("on_time_pct"))
    return _result(vals, rows, n=int(len(df)), excluded=int((~closed & ~open_).sum()))


# =========================================================================== M13 associação

def _cramers_v(x: pd.Series, y: pd.Series) -> float | None:
    ct = pd.crosstab(x, y)
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return None
    n = ct.values.sum()
    exp = np.outer(ct.sum(axis=1), ct.sum(axis=0)) / n
    chi2 = ((ct.values - exp) ** 2 / exp).sum()
    phi2 = chi2 / n
    r, k = ct.shape
    phi2c = max(0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
    den = min(kc - 1, rc - 1)
    return float(math.sqrt(phi2c / den)) if den > 0 else None


def _eta(cat: pd.Series, num: pd.Series) -> float | None:
    t = pd.DataFrame({"c": cat, "x": num}).dropna()
    if t["c"].nunique() < 2:
        return None
    grand = t["x"].mean()
    ss_b = t.groupby("c")["x"].apply(lambda g: len(g) * (g.mean() - grand) ** 2).sum()
    ss_t = ((t["x"] - grand) ** 2).sum()
    return float(math.sqrt(ss_b / ss_t)) if ss_t else None


def _strength(v: float | None) -> str | None:
    if v is None:
        return None
    a = abs(v)
    return "forte" if a >= 0.5 else "moderada" if a >= 0.3 else "fraca"


def association(df: pd.DataFrame, columns: list[str], kinds: dict[str, str] | None = None, min_n: int = 10) -> dict:
    """Associação par a par. ``kinds`` mapeia coluna -> 'measure' | 'category' (padrão: pelo dtype)."""
    kinds = kinds or {}

    def kind(c):
        if c in kinds:
            return kinds[c]
        return "measure" if pd.api.types.is_numeric_dtype(df[c]) and df[c].dtype != "boolean" else "category"

    rows = []
    cols = columns[:12]
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            ka, kb = kind(a), kind(b)
            sub = df[[a, b]].dropna()
            n = len(sub)
            if n < min_n:
                continue
            if ka == kb == "measure":
                xa, xb = _num(sub[a]), _num(sub[b])
                pear = _f(xa.corr(xb, method="pearson"))
                spear = _f(xa.rank().corr(xb.rank(), method="pearson"))  # Spearman sem scipy
                rows.append({"x": a, "y": b, "method": "pearson", "coef": pear, "n": n, "strength": _strength(pear)})
                rows.append({"x": a, "y": b, "method": "spearman", "coef": spear, "n": n, "strength": _strength(spear)})
            elif ka == kb == "category":
                v = _cramers_v(sub[a].astype(str), sub[b].astype(str))
                rows.append({"x": a, "y": b, "method": "cramers_v", "coef": v, "n": n, "strength": _strength(v)})
            else:
                c, m = (a, b) if ka == "category" else (b, a)
                v = _eta(sub[c].astype(str), _num(sub[m]))
                rows.append({"x": c, "y": m, "method": "eta", "coef": v, "n": n, "strength": _strength(v)})
    rows.sort(key=lambda r: -abs(r["coef"] or 0))
    top = rows[0] if rows else None
    return _result({"pairs": len(rows), "strongest": f"{top['x']} × {top['y']} ({top['method']})" if top else None,
                    "strongest_coef": top["coef"] if top else None},
                   rows, n=int(len(df)), flags={"note": "associação descritiva, sem p-valor e sem causalidade"})


# =========================================================================== M14 fontes

def _norm_key(s: pd.Series) -> pd.Series:
    from .relations import normalize_key
    return normalize_key(s)


def source_coverage(df: pd.DataFrame, key: str, df_b: pd.DataFrame, key_b: str) -> dict:
    a, b = set(_norm_key(df[key]).dropna()), set(_norm_key(df_b[key_b]).dropna())
    both = a & b
    return _result({"distinct_a": len(a), "distinct_b": len(b), "in_both": len(both),
                    "a_in_b_pct": _safe_div(len(both), len(a)), "b_in_a_pct": _safe_div(len(both), len(b)),
                    "only_a": len(a - b), "only_b": len(b - a)},
                   [{"side": "somente A", "examples": sorted(map(str, a - b))[:10]},
                    {"side": "somente B", "examples": sorted(map(str, b - a))[:10]}], n=len(a | b))


def reconcile_measure(df: pd.DataFrame, key: str, measure: str, df_b: pd.DataFrame, key_b: str, measure_b: str,
                      tolerance: float = 0.005) -> dict:
    a = pd.DataFrame({"k": _norm_key(df[key]), "v": _num(df[measure])}).groupby("k")["v"].sum()
    b = pd.DataFrame({"k": _norm_key(df_b[key_b]), "v": _num(df_b[measure_b])}).groupby("k")["v"].sum()
    common = a.index.intersection(b.index)
    diff = (a[common] - b[common])
    rel = diff / b[common].replace(0, np.nan)
    divergent = rel.abs() > tolerance
    t = pd.DataFrame({"key": common.astype(str), "value_a": a[common].values, "value_b": b[common].values,
                      "diff": diff.values, "diff_pct": rel.values})
    t = t.reindex(t["diff"].abs().sort_values(ascending=False).index)
    vals = {"total_a": float(a.sum()), "total_b": float(b.sum()), "total_diff": float(a.sum() - b.sum()),
            "total_diff_pct": _safe_div(a.sum() - b.sum(), b.sum()), "common_keys": int(len(common)),
            "common_total_a": float(a[common].sum()), "common_total_b": float(b[common].sum()),
            "divergent_keys": int(divergent.sum()), "divergent_keys_pct": _safe_div(divergent.sum(), len(common)),
            "tolerance": tolerance}
    return _result(vals, _records(t, 20), n=int(len(common)), truncated=len(t) > 20)


def attribute_divergence(df: pd.DataFrame, key: str, attribute: str, df_b: pd.DataFrame, key_b: str, attribute_b: str) -> dict:
    a = pd.DataFrame({"k": _norm_key(df[key]), "v": df[attribute].map(lambda v: _canon(v) if pd.notna(v) else None)}).dropna().drop_duplicates("k").set_index("k")["v"]
    b = pd.DataFrame({"k": _norm_key(df_b[key_b]), "v": df_b[attribute_b].map(lambda v: _canon(v) if pd.notna(v) else None)}).dropna().drop_duplicates("k").set_index("k")["v"]
    common = a.index.intersection(b.index)
    differ = a[common] != b[common]
    ex = [{"key": str(k), "value_a": str(df.loc[_norm_key(df[key]) == k, attribute].iloc[0]),
           "value_b": str(df_b.loc[_norm_key(df_b[key_b]) == k, attribute_b].iloc[0])} for k in common[differ.values][:10]]
    return _result({"common_keys": int(len(common)), "divergent": int(differ.sum()),
                    "divergent_pct": _safe_div(differ.sum(), len(common))}, ex, n=int(len(common)))


# =========================================================================== M15 sensibilidade

def sensitivity(df: pd.DataFrame, column: str, agg: str = "mean", group_by: str | None = None) -> dict:
    x = _num(df[column])
    xs = x.dropna()
    if len(xs) < 4:
        return _result({}, n=int(len(xs)), warnings=["poucos valores para sensibilidade"])
    q1, q3 = np.quantile(xs, [0.25, 0.75])
    iqr = q3 - q1
    keep = (x >= q1 - 1.5 * iqr) & (x <= q3 + 1.5 * iqr)
    base = _agg(x, agg)
    trimmed = _agg(x[keep], agg)
    change = _safe_div(trimmed - base, base)
    vals = {"base": base, "without_outliers": trimmed, "change_pct": change,
            "removed": int((~keep & x.notna()).sum()),
            "mean_median_gap_pct": _safe_div(xs.mean() - xs.median(), xs.median()),
            "sensitive": bool(change is not None and abs(change) > SENSITIVE_THRESHOLD)}
    rows = []
    if group_by:
        g0 = df.assign(_x=x).groupby(group_by, observed=True)["_x"].agg(agg).rank(ascending=False, method="min")
        g1 = df.assign(_x=x)[keep].groupby(group_by, observed=True)["_x"].agg(agg).rank(ascending=False, method="min")
        joined = pd.DataFrame({"rank_base": g0, "rank_without_outliers": g1}).dropna()
        joined["moved"] = joined["rank_base"] != joined["rank_without_outliers"]
        vals["groups_changing_rank"] = int(joined["moved"].sum())
        rows = _records(joined.reset_index().rename(columns={group_by: "group"}))
    return _result(vals, rows, n=int(len(xs)), flags={"sensitive": vals["sensitive"]},
                   warnings=["resultado sensível a extremos (variação > 10%)"] if vals["sensitive"] else [])


# =========================================================================== registro

CATALOG: dict[str, dict] = {
    "quality_completeness": {"family": "M1", "func": quality_completeness, "label": "Completude"},
    "quality_uniqueness": {"family": "M1", "func": quality_uniqueness, "label": "Unicidade"},
    "quality_validity": {"family": "M1", "func": quality_validity, "label": "Validade"},
    "quality_consistency": {"family": "M1", "func": quality_consistency, "label": "Consistência"},
    "quality_temporal_coverage": {"family": "M1", "func": quality_temporal_coverage, "label": "Cobertura temporal"},
    "volume_counts": {"family": "M2", "func": volume_counts, "label": "Volume e contagem"},
    "position_stats": {"family": "M3", "func": position_stats, "label": "Posição"},
    "dispersion_shape": {"family": "M4", "func": dispersion_shape, "label": "Dispersão e forma"},
    "frequency_table": {"family": "M5", "func": frequency_table, "label": "Frequência"},
    "share_of_total": {"family": "M5", "func": share_of_total, "label": "Participação no total"},
    "crosstab": {"family": "M5", "func": crosstab, "label": "Tabela cruzada"},
    "concentration": {"family": "M6", "func": concentration, "label": "Concentração"},
    "pareto_abc": {"family": "M6", "func": pareto_abc, "label": "Pareto / ABC"},
    "time_series": {"family": "M7", "func": time_series, "label": "Série temporal"},
    "period_change": {"family": "M7", "func": period_change, "label": "Variação entre períodos"},
    "trend_summary": {"family": "M7", "func": trend_summary, "label": "Tendência"},
    "seasonal_profile": {"family": "M7", "func": seasonal_profile, "label": "Perfil sazonal"},
    "group_comparison": {"family": "M8", "func": group_comparison, "label": "Comparação entre grupos"},
    "compare_to_reference": {"family": "M8", "func": compare_to_reference, "label": "Comparação com referência"},
    "rate": {"family": "M9", "func": rate, "label": "Taxa"},
    "funnel": {"family": "M9", "func": funnel, "label": "Funil"},
    "simpson_check": {"family": "M9", "func": simpson_check, "label": "Verificação de Simpson"},
    "contribution_to_change": {"family": "M10", "func": contribution_to_change, "label": "Contribuição para a variação"},
    "mix_rate_decomposition": {"family": "M10", "func": mix_rate_decomposition, "label": "Decomposição composição × desempenho"},
    "entity_rfm": {"family": "M11", "func": entity_rfm, "label": "Recência, frequência e valor"},
    "cohort_retention": {"family": "M11", "func": cohort_retention, "label": "Coortes e retenção"},
    "new_vs_returning": {"family": "M11", "func": new_vs_returning, "label": "Novos e recorrentes"},
    "durations": {"family": "M12", "func": durations, "label": "Durações"},
    "deadline_compliance": {"family": "M12", "func": deadline_compliance, "label": "Cumprimento de prazo"},
    "association": {"family": "M13", "func": association, "label": "Associação descritiva"},
    "source_coverage": {"family": "M14", "func": source_coverage, "label": "Cobertura entre fontes", "two_datasets": True},
    "reconcile_measure": {"family": "M14", "func": reconcile_measure, "label": "Reconciliação de medida", "two_datasets": True},
    "attribute_divergence": {"family": "M14", "func": attribute_divergence, "label": "Divergência de atributo", "two_datasets": True},
    "sensitivity": {"family": "M15", "func": sensitivity, "label": "Sensibilidade"},
}

# parâmetros que nomeiam colunas: usados para linhagem e para checar tipos semânticos
COLUMN_PARAMS = {"column", "columns", "measure", "measure_b", "category", "item", "group", "group_by", "date_col",
                 "entity", "start", "end", "deadline", "actual", "reference", "weight", "row", "col", "value",
                 "key", "key_b", "attribute", "attribute_b", "stratum", "categories", "measures", "dates", "non_negative"}
AGGREGATING_PARAMS = {"column", "measure", "measure_b", "actual", "reference", "value", "weight"}


def catalog_summary() -> list[dict]:
    import inspect
    out = []
    for name, meta in CATALOG.items():
        sig = inspect.signature(meta["func"])
        params = [p for p in sig.parameters if p not in ("df", "df_b")]
        out.append({"function": name, "family": meta["family"], "label": meta["label"], "params": params,
                    "two_datasets": meta.get("two_datasets", False),
                    "doc": (meta["func"].__doc__ or "").strip().split("\n")[0]})
    return out


def _columns_in(params: dict) -> list[str]:
    cols = []
    for k, v in params.items():
        if k in COLUMN_PARAMS:
            if isinstance(v, str):
                cols.append(v)
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, str):
                        cols.append(x)
                    elif isinstance(x, list):
                        cols += [y for y in x if isinstance(y, str)]
        elif k in ("numerator", "denominator") and isinstance(v, dict):
            if "column" in v:
                cols.append(v["column"])
            for c in v.get("filter", []):
                cols.append(c["column"])
        elif k == "steps":
            for st in v:
                if "column" in st:
                    cols.append(st["column"])
                for c in st.get("filter", []):
                    cols.append(c["column"])
    return list(dict.fromkeys(cols))


class MetricError(ValueError):
    pass


def compute(spec: dict, ws, save: bool = True) -> dict:
    """Executa uma especificação de métrica e salva o resultado.

    ``spec``::

        {"metric_id": "m_receita_mes", "label": "Receita por mês", "function": "time_series",
         "dataset_id": "ds_vendas", "params": {"date_col": "data", "measure": "valor", "agg": "sum"},
         "filters": [{"column": "status", "op": "!=", "value": "cancelado"}],
         "unit": "R$", "formula": "soma de valor por mês", "population": "vendas não canceladas"}
    """
    from .filters import apply_conditions

    fn = spec["function"]
    if fn not in CATALOG:
        raise MetricError(f"função desconhecida: {fn}. Use uma de: {', '.join(CATALOG)}")
    meta = CATALOG[fn]
    params = dict(spec.get("params") or {})
    ds_meta = ws.dataset_meta(spec["dataset_id"])
    df = ws.load_dataset(spec["dataset_id"])
    cols = _columns_in(params)
    missing = [c for c in cols if c not in df.columns]
    df_b = None
    if meta.get("two_datasets"):
        df_b = ws.load_dataset(spec["dataset_id_b"])
        b_cols = [params.get(k) for k in ("key_b", "measure_b", "attribute_b") if params.get(k)]
        missing = [c for c in cols if c not in df.columns and c not in b_cols] + [c for c in b_cols if c not in df_b.columns]
    if missing:
        raise MetricError(f"colunas inexistentes em {spec['dataset_id']}: {missing}")
    sem = ds_meta.get("semantic_types", {})
    for k in AGGREGATING_PARAMS:
        c = params.get(k)
        if isinstance(c, str) and sem.get(c) == "identifier" and params.get("agg", "sum") not in ("count", "nunique"):
            raise MetricError(f"'{c}' é identificador: não pode ser somado nem ter média (use contagem)")
    n_before = len(df)
    if spec.get("filters"):
        df = df[apply_conditions(df, spec["filters"])]
    filtered_out = n_before - len(df)
    out = meta["func"](df, df_b=df_b, **params) if df_b is not None else meta["func"](df, **params)
    lineage_ds = [spec["dataset_id"]] + ([spec["dataset_id_b"]] if df_b is not None else [])
    lineage = []
    for did in lineage_ds:
        m = ws.dataset_meta(did)
        lineage.append({"dataset_id": did, "source_file": m.get("source_file"), "source_sheet": m.get("source_sheet"),
                        "source_label": m.get("source_label"), "parents": m.get("parents", []),
                        "columns": cols})
    result = {
        "result_id": spec.get("result_id") or f"res_{spec['metric_id']}",
        "metric_id": spec["metric_id"],
        "label": spec.get("label", meta["label"]),
        "family": meta["family"],
        "function": fn,
        "unit": spec.get("unit"),
        "formula": spec.get("formula"),
        "population": spec.get("population"),
        "filters": spec.get("filters", []),
        "rows_filtered_out": int(filtered_out),
        "lineage": lineage,
        "spec": spec,
        "conventions": {"std_ddof": 1, "quantile_method": "linear", "small_sample": SMALL_SAMPLE},
        **out,
    }
    if save:
        result["path"] = ws.save_result(result)
    return result
