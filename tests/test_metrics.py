import math

import numpy as np
import pandas as pd
import pytest

from dataai.tools import metrics as M


def test_position_dispersion_conventions():
    df = pd.DataFrame({"v": [1, 2, 3, 4, 100]})
    pos = M.position_stats(df, "v")["values"]
    assert pos["median"] == 3 and pos["p25"] == 2  # quantil linear
    d = M.dispersion_shape(df, "v")["values"]
    assert math.isclose(d["std"], pd.Series([1, 2, 3, 4, 100]).std(ddof=1))
    assert d["outliers_iqr"] == 1


def test_concentration_gini_hhi():
    df = pd.DataFrame({"item": list("abcd"), "v": [25, 25, 25, 25]})
    v = M.concentration(df, "item", "v")["values"]
    assert v["gini"] == pytest.approx(0, abs=1e-12) and v["hhi"] == pytest.approx(2500)
    df2 = pd.DataFrame({"item": list("abcd"), "v": [100, 0, 0, 0]})
    v2 = M.concentration(df2, "item", "v")["values"]
    assert v2["top1_share"] == 1 and v2["hhi"] == pytest.approx(10000) and v2["gini"] == pytest.approx(0.75)


def _two_months():
    return pd.DataFrame({
        "d": pd.to_datetime(["2024-01-01", "2024-01-31", "2024-02-01", "2024-02-29", "2024-03-01", "2024-03-31"] * 2),
        "g": ["A"] * 6 + ["B"] * 6, "v": [10, 10, 12, 12, 15, 15, 5, 5, 4, 4, 9, 9]})


def test_contribution_sums_to_one_and_mix_rate_is_exact():
    df = _two_months()
    c = M.contribution_to_change(df, "d", "g", "v", period_a="2024-01", period_b="2024-03")
    assert sum(r["contribution"] for r in c["rows"]) == pytest.approx(1.0)
    m = M.mix_rate_decomposition(df, "d", "g", value="v", period_a="2024-01", period_b="2024-03")["values"]
    assert m["check_residual"] == pytest.approx(0, abs=1e-12)


def test_rate_keeps_numerator_denominator_and_zero_division():
    df = pd.DataFrame({"g": ["a", "a", "b"], "ok": [True, False, True]})
    r = M.rate(df, {"column": "ok"}, group_by="g")
    assert r["values"]["numerator"] == 2 and r["values"]["denominator"] == 3
    z = M.rate(df.iloc[:0], {"column": "ok"})
    assert z["values"]["rate"] is None and z["warnings"]


def test_simpson_reversal_detected():
    rows = []
    # clássico: A melhor em cada estrato, pior no total
    for g, s, n, k in [("A", "leve", 87, 81), ("A", "grave", 263, 192), ("B", "leve", 270, 234), ("B", "grave", 80, 55)]:
        rows += [{"g": g, "s": s, "ok": 1}] * k + [{"g": g, "s": s, "ok": 0}] * (n - k)
    out = M.simpson_check(pd.DataFrame(rows), "g", "s", {"column": "ok"}, groups=["A", "B"])
    assert out["values"]["simpson_reversal"] is True


def test_time_series_partial_periods_and_trend():
    d = pd.date_range("2024-01-01", "2024-06-15", freq="D")
    df = pd.DataFrame({"d": d, "v": 1.0})
    ts = M.time_series(df, "d", "v")
    assert ts["flags"]["partial_periods"] == ["2024-06"]
    tr = M.trend_summary(df, "d", "v")
    assert tr["values"]["complete_periods"] == 5


def test_cohort_rfm_deadline():
    df = pd.DataFrame({"e": ["x", "x", "y", "z", "z"],
                       "d": pd.to_datetime(["2024-01-05", "2024-02-05", "2024-01-10", "2024-02-01", "2024-03-01"]),
                       "v": [10, 20, 5, 7, 8]})
    co = M.cohort_retention(df, "e", "d")
    assert co["values"]["cohorts"] == 2 and co["values"]["retention_age_1"] == pytest.approx(2 / 3)
    rfm = M.entity_rfm(df, "e", "d", "v")
    assert rfm["values"]["entities"] == 3
    dl = pd.DataFrame({"fim": pd.to_datetime(["2024-01-02", "2024-01-10", None]),
                       "prazo": pd.to_datetime(["2024-01-05", "2024-01-05", "2024-01-01"])})
    out = M.deadline_compliance(dl, "fim", "prazo")["values"]
    assert out["on_time"] == 1 and out["late"] == 1 and out["open_items"] == 1 and out["open_overdue"] == 1


def test_association_and_sources():
    df = pd.DataFrame({"a": range(50), "b": [x * 2 for x in range(50)], "c": ["p", "q"] * 25, "k": ["s", "t"] * 25})
    rows = M.association(df, ["a", "b", "c", "k"])["rows"]
    pear = next(r for r in rows if r["method"] == "pearson")
    assert pear["coef"] == pytest.approx(1.0)
    assert next(r for r in rows if r["method"] == "cramers_v")["coef"] == pytest.approx(1.0, abs=0.05)
    A = pd.DataFrame({"k": ["001", "2", "3"], "v": [10, 20, 30]})
    B = pd.DataFrame({"id": [1, 2, 4], "v": [10, 25, 1]})
    cov = M.source_coverage(A, "k", B, "id")["values"]
    assert cov["in_both"] == 2
    rec = M.reconcile_measure(A, "k", "v", B, "id", "v")["values"]
    assert rec["common_keys"] == 2 and rec["divergent_keys"] == 1


def test_sensitivity_flags():
    df = pd.DataFrame({"v": [1, 1, 1, 1, 1, 1, 1, 100]})
    s = M.sensitivity(df, "v")
    assert s["values"]["sensitive"] is True


def test_catalog_covers_all_families():
    fams = {m["family"] for m in M.catalog_summary()}
    assert fams == {f"M{i}" for i in range(1, 16)}


def test_compute_blocks_identifier_aggregation(workspace):
    from dataai.tools import ingest, profile
    ingest.ingest(workspace)
    profile.profile(workspace)
    with pytest.raises(M.MetricError):
        M.compute({"metric_id": "x", "function": "position_stats", "dataset_id": "ds_produtos", "params": {"column": "sku"}}, workspace)
