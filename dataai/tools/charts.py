"""Especificação e renderização de gráficos (skill design-charts).

- ``suggest_chart(result)``: proposta inicial de gráfico para um resultado (o agente pode ajustar).
- ``validate_spec(spec, result)``: confere campos, título sem conclusão e unidades.
- ``render_png(spec, result, path)``: imagem para o PDF (matplotlib).
- ``echarts_option(spec, result)``: configuração para o dashboard HTML (ECharts).

Mesma categoria, mesma cor em todos os gráficos: use ``ColorMap``.
"""
from __future__ import annotations

from pathlib import Path

from .. import theme
from ..theme import CATEGORICAL, DIVERGING, NEUTRAL, PRIMARY, SEQUENTIAL
from .fmt import format_value, guess_format

# Cores da identidade visual (dataai/brand/tokens.json, skill brand-identity). Variação positiva e
# negativa usam os lados da escala divergente: nenhuma cor diz se o valor é bom ou ruim.
POSITIVE, NEGATIVE = theme.INCREASE, theme.DECREASE
SECONDARY = CATEGORICAL[1]
INK, MUTED, GRID = theme.INK, theme.INK_MUTED, theme.GRID
CHART_TYPES = ("kpi", "bar_horizontal", "column", "line", "histogram", "heatmap", "pareto", "waterfall", "table")


class ColorMap:
    def __init__(self, initial: dict | None = None):
        self.map = dict(initial or {})

    def get(self, category: str) -> str:
        if category in ("Outros", "(ausente)"):
            return NEUTRAL
        if category not in self.map:
            used = len([c for c in self.map.values() if c in CATEGORICAL])
            self.map[category] = CATEGORICAL[used % len(CATEGORICAL)]
        return self.map[category]


# =========================================================================== proposta

def _base(result: dict, ctype: str, title: str, x: dict | None = None, y: dict | None = None, **kw) -> dict:
    rid = result["result_id"]
    return {"chart_id": "ch_" + rid.removeprefix("res_"), "result_id": rid, "type": ctype, "title": title,
            "x": x or {}, "y": y or {}, "color": kw.pop("color", {"mode": "single", "value": PRIMARY}),
            "targets": kw.pop("targets", ["report", "dashboard"]), "interactions": ["tooltip"],
            "alt_text": kw.pop("alt_text", ""), **kw}


def suggest_chart(result: dict) -> dict | None:
    fn, label, unit = result["function"], result.get("label") or result["result_id"], result.get("unit")
    rows = result.get("rows") or []
    vfmt = guess_format(unit) or None
    if fn == "time_series" and rows and "group" not in rows[0]:
        return _base(result, "line", label, {"field": "period", "label": "Período"},
                     {"field": "value", "label": _axis(label, unit), "format": vfmt},
                     annotations=[{"type": "flag", "field": "partial_period", "label": "período parcial"}],
                     alt_text=f"Linha com {len(rows)} períodos.")
    if fn == "frequency_table" and rows:
        return _base(result, "bar_horizontal", label, {"field": "count", "label": "Quantidade", "format": "integer"},
                     {"field": "category", "label": "", "sort": "desc_by_x"}, alt_text=f"Barras com {len(rows)} categorias.")
    if fn == "share_of_total" and rows:
        pct = vfmt and vfmt.startswith("percent")
        return _base(result, "bar_horizontal", label, {"field": "share" if pct else "total", "label": _axis(label, unit), "format": vfmt},
                     {"field": "category", "label": "", "sort": "desc_by_x"},
                     color={"mode": "by_category", "field": "category"}, alt_text=f"Barras com {len(rows)} categorias.")
    if fn in ("concentration", "pareto_abc") and rows and "cum_share" in rows[0] and "item" in rows[0]:
        return _base(result, "pareto", label, {"field": "item", "label": ""},
                     {"field": "total", "label": _axis(label, unit), "format": vfmt, "line_field": "cum_share"},
                     alt_text="Barras ordenadas com linha de participação acumulada.")
    if fn == "group_comparison" and rows:
        return _base(result, "bar_horizontal", label, {"field": "value", "label": _axis(label, unit), "format": vfmt},
                     {"field": "group", "label": "", "sort": "desc_by_x"},
                     annotations=[{"type": "flag", "field": "small_sample", "label": "amostra < 30"}],
                     alt_text=f"Barras horizontais com {len(rows)} grupos.")
    if fn in ("rate", "deadline_compliance", "compare_to_reference") and rows:
        field = {"rate": "rate", "deadline_compliance": "on_time_pct", "compare_to_reference": "attainment"}[fn]
        return _base(result, "bar_horizontal", label, {"field": field, "label": label, "format": "percent_1"},
                     {"field": "group", "label": "", "sort": "desc_by_x"},
                     reference_line=1.0 if fn == "compare_to_reference" else None,
                     annotations=[{"type": "flag", "field": "small_sample", "label": "amostra < 30"}],
                     alt_text=f"Barras horizontais com {len(rows)} grupos.")
    if fn in ("dispersion_shape",) and rows:
        return _base(result, "histogram", label, {"field": "bin_start", "label": _axis(label, unit), "format": vfmt},
                     {"field": "count", "label": "Quantidade", "format": "integer"}, alt_text="Histograma.")
    if fn == "contribution_to_change" and rows:
        return _base(result, "waterfall", label, {"field": "group", "label": ""},
                     {"field": "delta", "label": _axis("Variação", unit), "format": vfmt},
                     alt_text="Ponte da variação por grupo.")
    if fn == "seasonal_profile" and rows:
        return _base(result, "column", label, {"field": "label", "label": ""},
                     {"field": "value", "label": _axis("Média", unit), "format": vfmt}, alt_text="Colunas por período do ciclo.")
    if fn == "crosstab" and rows:
        return _base(result, "heatmap", label, {"field": "col", "label": ""}, {"field": "row", "label": ""},
                     value={"field": "pct_row", "format": "percent_1"}, color={"mode": "sequential"}, alt_text="Mapa de calor.")
    if fn == "cohort_retention" and rows:
        return _base(result, "heatmap", label, {"field": "age", "label": "Períodos desde a entrada"},
                     {"field": "cohort", "label": "Coorte"}, value={"field": "retention", "format": "percent_0"},
                     color={"mode": "sequential"}, alt_text="Matriz de retenção por coorte.")
    if fn == "funnel" and rows:
        return _base(result, "bar_horizontal", label, {"field": "count", "label": "Quantidade", "format": "integer"},
                     {"field": "step", "label": "", "sort": "none"}, alt_text="Etapas do funil.")
    if fn == "association" and rows:
        return _base(result, "table", label, columns=["x", "y", "method", "coef", "n", "strength"],
                     targets=["report"], alt_text="Tabela de associações.")
    return None


def _axis(label: str, unit: str | None) -> str:
    return f"{label} ({unit})" if unit and unit not in ("fraction",) else label


def _rows_for(spec: dict, result: dict) -> list[dict]:
    rows = list(result.get("rows") or [])
    for cond in spec.get("row_filter", []) or []:
        rows = [r for r in rows if str(r.get(cond["field"])) == str(cond["value"])]
    if spec.get("max_items") and len(rows) > spec["max_items"]:
        rows = rows[: spec["max_items"]]
    sort = (spec.get("y") or {}).get("sort")
    xf = (spec.get("x") or {}).get("field")
    if spec["type"] == "bar_horizontal" and sort == "desc_by_x" and xf:
        rows = sorted(rows, key=lambda r: (r.get(xf) is None, -(r.get(xf) or 0)))
    return rows


def validate_spec(spec: dict, result: dict) -> list[str]:
    from .inspect import find_narrative
    problems = []
    if spec.get("type") not in CHART_TYPES:
        problems.append(f"tipo inválido: {spec.get('type')}")
    if spec.get("result_id") != result.get("result_id"):
        problems.append("result_id do gráfico não corresponde ao resultado")
    rows = result.get("rows") or []
    for axis in ("x", "y"):
        f = (spec.get(axis) or {}).get("field")
        if f and rows and f not in rows[0]:
            problems.append(f"campo '{f}' não existe nas linhas de {result['result_id']}")
    for hit in find_narrative(spec.get("title", "")) + find_narrative(spec.get("alt_text", "")):
        problems.append(f"título/alt com linguagem interpretativa: '{hit}'")
    return problems


# =========================================================================== PNG (PDF)

def render_png(spec: dict, result: dict, path: str | Path, colors: ColorMap | None = None, dpi: int = 200) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    colors = colors or ColorMap()
    rows = _rows_for(spec, result)
    t = spec["type"]
    x, y = spec.get("x") or {}, spec.get("y") or {}
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                         "ytick.color": MUTED, "font.family": [theme.matplotlib_font(), "DejaVu Sans"], "text.color": INK,
                         "axes.titlecolor": INK})
    fig_h = 3.2
    if t == "bar_horizontal":
        fig_h = max(2.4, min(7.5, 0.32 * len(rows) + 1.0))
    if t == "heatmap":
        fig_h = max(3.0, min(8.0, 0.35 * len({r[y['field']] for r in rows}) + 1.2))
    fig, ax = plt.subplots(figsize=(7.0, fig_h))
    fmt_axis = lambda f: FuncFormatter(lambda v, _: format_value(v, "currency_brl_compact" if f == "currency_brl" else f))
    if t in ("bar_horizontal",):
        labels = [str(r[y["field"]]) for r in rows][::-1]
        vals = [r.get(x["field"]) or 0 for r in rows][::-1]
        if spec.get("color", {}).get("mode") == "by_category":
            for l in labels[::-1]:  # atribui na ordem de leitura (maior primeiro): dados-1 vai para o primeiro item
                colors.get(l)
            cs = [colors.get(l) for l in labels]
        else:
            cs = [NEUTRAL if l == "Outros" else spec.get("color", {}).get("value", PRIMARY) for l in labels]
        bars = ax.barh(labels, vals, color=cs)
        ax.xaxis.set_major_formatter(fmt_axis(x.get("format")))
        for b, v in zip(bars, vals):
            ax.text(b.get_width(), b.get_y() + b.get_height() / 2, " " + format_value(v, x.get("format")),
                    va="center", fontsize=7.5, color=INK)
        if spec.get("reference_line") is not None:
            ax.axvline(spec["reference_line"], color=MUTED, lw=1, ls="--")
        ax.set_xlabel(x.get("label", ""))
        ax.margins(x=0.15)
    elif t == "column":
        labels = [str(r[x["field"]]) for r in rows]
        vals = [r.get(y["field"]) or 0 for r in rows]
        ax.bar(labels, vals, color=PRIMARY)
        ax.yaxis.set_major_formatter(fmt_axis(y.get("format")))
        ax.set_ylabel(y.get("label", ""))
    elif t == "line":
        labels = [str(r[x["field"]]) for r in rows]
        vals = [r.get(y["field"]) for r in rows]
        ax.plot(labels, vals, color=PRIMARY, lw=2, marker="o", ms=3)
        partial = [i for i, r in enumerate(rows) if r.get("partial_period")]
        for i in partial:
            ax.plot([labels[i]], [vals[i]], marker="o", ms=6, mfc="white", mec=theme.WARNING, mew=1.5)
        ax.yaxis.set_major_formatter(fmt_axis(y.get("format")))
        ax.set_ylabel(y.get("label", ""))
        step = max(1, len(labels) // 12)
        ax.set_xticks(range(0, len(labels), step))
        ax.set_xticklabels(labels[::step], rotation=45, ha="right")
        if partial:
            ax.text(0.99, 0.02, "○ período parcial", transform=ax.transAxes, ha="right", fontsize=7, color=theme.WARNING)
    elif t == "histogram":
        starts = [r["bin_start"] for r in rows]
        widths = [r["bin_end"] - r["bin_start"] for r in rows]
        ax.bar(starts, [r["count"] for r in rows], width=widths, align="edge", color=PRIMARY, edgecolor="white")
        ax.xaxis.set_major_formatter(fmt_axis(x.get("format")))
        ax.set_xlabel(x.get("label", ""))
        ax.set_ylabel(y.get("label", "Quantidade"))
    elif t == "pareto":
        labels = [str(r[x["field"]]) for r in rows][:20]
        vals = [r.get(y["field"]) or 0 for r in rows][:20]
        ax.bar(labels, vals, color=PRIMARY)
        ax.yaxis.set_major_formatter(fmt_axis(y.get("format")))
        ax2 = ax.twinx()
        ax2.plot(labels, [r.get(y.get("line_field", "cum_share")) for r in rows][:20], color=SECONDARY, marker="o", ms=3)
        ax2.yaxis.set_major_formatter(fmt_axis("percent_0"))
        ax2.set_ylim(0, 1.05)
        ax2.spines["top"].set_visible(False)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
    elif t == "waterfall":
        labels = [str(r[x["field"]]) for r in rows][:12]
        vals = [r.get(y["field"]) or 0 for r in rows][:12]
        cum, bottoms = 0.0, []
        for v in vals:
            bottoms.append(cum if v >= 0 else cum + v)
            cum += v
        ax.bar(labels, [abs(v) for v in vals], bottom=bottoms, color=[POSITIVE if v >= 0 else NEGATIVE for v in vals])
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.yaxis.set_major_formatter(fmt_axis(y.get("format")))
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
    elif t == "heatmap":
        import numpy as np
        vf = spec["value"]["field"]
        xs = list(dict.fromkeys(str(r[x["field"]]) for r in rows))
        ys = list(dict.fromkeys(str(r[y["field"]]) for r in rows))
        m = np.full((len(ys), len(xs)), np.nan)
        for r in rows:
            m[ys.index(str(r[y["field"]])), xs.index(str(r[x["field"]]))] = r.get(vf) if r.get(vf) is not None else np.nan
        from matplotlib.colors import LinearSegmentedColormap
        im = ax.imshow(m, cmap=LinearSegmentedColormap.from_list("seq", SEQUENTIAL), aspect="auto")
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels(xs, rotation=45, ha="right")
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels(ys)
        if len(xs) * len(ys) <= 120:
            for i in range(len(ys)):
                for j in range(len(xs)):
                    if not np.isnan(m[i, j]):
                        ax.text(j, i, format_value(m[i, j], spec["value"].get("format")), ha="center", va="center",
                                fontsize=6.5, color="white" if m[i, j] > np.nanmean(m) else INK)
        fig.colorbar(im, ax=ax, fraction=0.03)
        ax.spines[:].set_visible(False)
    elif t == "table":
        cols = spec.get("columns") or list(rows[0].keys())[:6]
        ax.axis("off")
        cell = [[format_value(r.get(c)) for c in cols] for r in rows[:15]]
        tb = ax.table(cellText=cell, colLabels=cols, loc="center")
        tb.auto_set_font_size(False)
        tb.set_fontsize(7.5)
    else:
        plt.close(fig)
        raise ValueError(f"tipo sem renderização PNG: {t}")
    ax.set_title(spec["title"], loc="left", fontsize=10.5, color=INK, fontweight=600, pad=10)
    if t not in ("heatmap", "table"):
        ax.grid(axis="x" if t == "bar_horizontal" else "y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return str(path)


# =========================================================================== ECharts (HTML)

def echarts_option(spec: dict, result: dict, colors: ColorMap | None = None) -> dict:
    """Opção ECharts com os valores do resultado (sem recalcular). Formatação é feita no navegador
    pelo código de formato (``_fmt``), que o dashboard traduz para pt-BR."""
    colors = colors or ColorMap()
    rows = _rows_for(spec, result)
    t = spec["type"]
    x, y = spec.get("x") or {}, spec.get("y") or {}
    base = {"_fmt": None, "animation": False, "grid": {"left": 8, "right": 24, "top": 16, "bottom": 8, "containLabel": True},
            "tooltip": {"trigger": "axis", "confine": True}}
    if t == "bar_horizontal":
        rows_r = rows[::-1]
        cats = [str(r[y["field"]]) for r in rows_r]
        if spec.get("color", {}).get("mode") == "by_category":
            for c in cats[::-1]:  # atribui na ordem de leitura (maior primeiro)
                colors.get(c)
        data = []
        for r, c in zip(rows_r, cats):
            col = colors.get(c) if spec.get("color", {}).get("mode") == "by_category" else (NEUTRAL if c == "Outros" else PRIMARY)
            data.append({"value": r.get(x["field"]), "itemStyle": {"color": col}})
        opt = {**base, "_fmt": x.get("format"), "grid": {**base["grid"], "right": 72}, "xAxis": {"type": "value", "splitNumber": 4},
               "yAxis": {"type": "category", "data": cats}, "series": [{"type": "bar", "data": data, "label": {"show": True, "position": "right"}}]}
        if spec.get("reference_line") is not None:
            opt["series"][0]["markLine"] = {"symbol": "none", "data": [{"xAxis": spec["reference_line"]}], "lineStyle": {"color": MUTED}}
        return opt
    if t in ("column", "line"):
        cats = [str(r[x["field"]]) for r in rows]
        vals = [r.get(y["field"]) for r in rows]
        series = {"type": "bar" if t == "column" else "line", "data": vals, "itemStyle": {"color": PRIMARY},
                  "smooth": False, "showSymbol": True}
        if t == "line":
            series["data"] = [{"value": v, "symbol": "emptyCircle" if r.get("partial_period") else "circle",
                               "symbolSize": 9 if r.get("partial_period") else 5} for v, r in zip(vals, rows)]
        return {**base, "_fmt": y.get("format"), "xAxis": {"type": "category", "data": cats},
                "yAxis": {"type": "value"}, "series": [series]}
    if t == "histogram":
        cats = [f"{format_value(r['bin_start'], x.get('format'))} – {format_value(r['bin_end'], x.get('format'))}" for r in rows]
        return {**base, "_fmt": "integer", "xAxis": {"type": "category", "data": cats},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "barCategoryGap": "2%", "data": [r["count"] for r in rows], "itemStyle": {"color": PRIMARY}}]}
    if t == "pareto":
        rows20 = rows[:20]
        return {**base, "_fmt": y.get("format"), "xAxis": {"type": "category", "data": [str(r[x["field"]]) for r in rows20]},
                "yAxis": [{"type": "value"}, {"type": "value", "max": 1, "_fmt": "percent_0"}],
                "series": [{"type": "bar", "data": [r.get(y["field"]) for r in rows20], "itemStyle": {"color": PRIMARY}},
                           {"type": "line", "yAxisIndex": 1, "_fmt": "percent_1",
                            "data": [r.get(y.get("line_field", "cum_share")) for r in rows20], "itemStyle": {"color": SECONDARY}}]}
    if t == "waterfall":
        rows12 = rows[:12]
        cum, base_vals, vals = 0.0, [], []
        for r in rows12:
            v = r.get(y["field"]) or 0
            base_vals.append(cum if v >= 0 else cum + v)
            vals.append({"value": abs(v), "itemStyle": {"color": POSITIVE if v >= 0 else NEGATIVE}, "_signed": v})
            cum += v
        return {**base, "_fmt": y.get("format"), "tooltip": {"trigger": "item", "confine": True},
                "xAxis": {"type": "category", "data": [str(r[x["field"]]) for r in rows12]}, "yAxis": {"type": "value"},
                "series": [{"type": "bar", "stack": "w", "stackStrategy": "all", "data": base_vals, "itemStyle": {"color": "transparent"},
                            "silent": True, "tooltip": {"show": False}},
                           {"type": "bar", "stack": "w", "stackStrategy": "all", "data": vals}]}
    if t == "heatmap":
        vf = spec["value"]["field"]
        xs = list(dict.fromkeys(str(r[x["field"]]) for r in rows))
        ys = list(dict.fromkeys(str(r[y["field"]]) for r in rows))
        data = [[xs.index(str(r[x["field"]])), ys.index(str(r[y["field"]])), r.get(vf)] for r in rows]
        vals = [d[2] for d in data if d[2] is not None]
        return {**base, "_fmt": spec["value"].get("format"), "tooltip": {"trigger": "item", "confine": True},
                "xAxis": {"type": "category", "data": xs, "name": x.get("label", ""), "nameLocation": "middle", "nameGap": 26},
                "yAxis": {"type": "category", "data": ys},
                "visualMap": {"min": min(vals) if vals else 0, "max": max(vals) if vals else 1, "calculable": True,
                              "orient": "horizontal", "left": "center", "bottom": 0, "inRange": {"color": SEQUENTIAL}, "_fmt": spec["value"].get("format")},
                "grid": {**base["grid"], "bottom": 56},
                "series": [{"type": "heatmap", "data": data, "label": {"show": len(data) <= 120}}]}
    raise ValueError(f"tipo sem ECharts: {t}")
