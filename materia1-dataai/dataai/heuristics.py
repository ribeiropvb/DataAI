"""Modo sem IA (``--no-llm``): planejamento por regras, gráficos sugeridos e texto em modelo fixo.

Serve para testar ferramentas e entregas antes de escolher o provedor de IA. Não interpreta perguntas
em linguagem natural nem escreve interpretação: os achados trazem só magnitude, referência e confiabilidade.
"""
from __future__ import annotations

import re

from .tools import charts as charts_mod
from .tools import metrics, relations
from .tools.textutil import norm_name, tokens
from .workspace import Workspace

MEASURE_HINTS = ("valor", "total", "receita", "amount", "revenue", "price", "preco", "vendas", "custo", "cost", "quantidade", "qtd")
EVENT_DATE_HINTS = ("data", "date", "dt", "criacao", "abertura", "inicio", "venda", "pedido", "registro")
DEADLINE_HINTS = ("previs", "prazo", "limite", "deadline", "due", "vencimento", "esperad")
END_HINTS = ("entrega", "fim", "conclus", "fecha", "encerr", "end", "deliver", "resolu", "pagamento")
STATUS_HINTS = ("status", "situacao", "estado", "state")


def _score_name(name: str, hints) -> int:
    """Quantas dicas aparecem como início de alguma palavra do nome (``venda`` não casa com ``end``)."""
    toks = tokens(name)
    return sum(1 for h in hints if any(t.startswith(h) for t in toks))


def choose_main_table(ws: Workspace) -> str:
    rmap = ws.read_json("results/relationship_map.json")
    tables = rmap["tables"]
    facts = [t for t in tables if t["role"] == "fato"] or [t for t in tables if t["role"] not in ("isolada",)] or tables
    return max(facts, key=lambda t: t["rows"])["dataset_id"]


def plan_joins(ws: Workspace, main: str) -> list[dict]:
    """Enriquece a tabela principal com cadastros (dimensões/referências) ligados por relação forte N:1 ou 1:1."""
    rmap = ws.read_json("results/relationship_map.json")
    roles = {t["dataset_id"]: t["role"] for t in rmap["tables"]}
    joins, left = [], main
    for r in rmap["relations"]:
        if r["strength"] != "strong" or r["child"]["dataset_id"] != main or r.get("ambiguous_with"):
            continue
        if r["cardinality_observed"] not in ("N:1", "1:1") or roles.get(r["parent"]["dataset_id"]) not in ("dimensão", "referência"):
            continue
        derived = f"{left}__{r['parent']['dataset_id'].replace('ds_', '')}"[:80]
        joins.append({"left_id": left, "right_id": r["parent"]["dataset_id"], "left_on": r["child"]["key"],
                      "right_on": r["parent"]["key"], "how": "left", "derived_id": derived,
                      "reason": f"trazer atributos de {r['parent']['dataset_id']} ({r['relation_id']})"})
        left = derived
    return joins


def _pick(cols: list[str], hints, avoid=()) -> str | None:
    cands = [c for c in cols if not any(a in norm_name(c) for a in avoid)] or cols
    return max(cands, key=lambda c: _score_name(c, hints), default=None) if cands else None


def plan_metrics(ws: Workspace, main: str, dataset: str) -> tuple[list[dict], dict]:
    meta, main_meta = ws.dataset_meta(dataset), ws.dataset_meta(main)
    sem = meta.get("semantic_types", {})
    df = ws.load_dataset(dataset)
    main_cols = set(main_meta.get("semantic_types", {}))
    measures = [c for c, t in sem.items() if t == "measure"]
    main_measures = [c for c in measures if c in main_cols] or measures
    dates = [c for c, t in sem.items() if t == "datetime" and c in main_cols] or [c for c, t in sem.items() if t == "datetime"]
    cats = [c for c, t in sem.items() if t == "category" and 2 <= df[c].nunique() <= 15 and df[c].isna().mean() < 0.3]
    rmap = ws.read_json("results/relationship_map.json")
    fks = [r["child"]["key"][0] for r in rmap["relations"] if r["strength"] == "strong" and r["child"]["dataset_id"] == main
           and len(r["child"]["key"]) == 1]
    entities = sorted([c for c in fks if c in df.columns and df[c].nunique() >= 20], key=lambda c: -df[c].nunique())
    measure = None
    if main_measures:
        measure = max(main_measures, key=lambda c: (_score_name(c, MEASURE_HINTS[:8]), _score_name(c, MEASURE_HINTS), float(df[c].abs().sum() or 0)))
    date = None
    if dates:
        date = max(dates, key=lambda c: (_score_name(c, EVENT_DATE_HINTS) - 2 * _score_name(c, DEADLINE_HINTS + END_HINTS), df[c].notna().sum()))
    status = [c for c in cats if _score_name(c, STATUS_HINTS)]
    groups = [c for c in cats if c not in status]
    groups.sort(key=lambda c: (c in main_cols, abs(df[c].nunique() - 6)))
    cat1 = groups[0] if groups else (cats[0] if cats else None)
    entity = entities[0] if entities else None
    roles = {"measure": measure, "date": date, "category": cat1, "categories": groups[:3], "status": status[:1], "entity": entity}

    specs: list[dict] = []
    lab = lambda c: c.replace("_", " ")

    def add(mid, label, fn, params, dq, ds=dataset, **kw):
        specs.append({"metric_id": mid, "label": label, "function": fn, "dataset_id": ds, "params": params,
                      "decision_question": dq, **kw})

    add("volume", "Volume de registros", "volume_counts", {"entity": entity, "date_col": date}, "Quanto e quão típico?")
    if measure:
        add("dist_medida", f"Distribuição de {lab(measure)}", "dispersion_shape", {"column": measure}, "Quanto e quão típico?",
            formula=f"estatísticas de {measure} por registro")
        add("pos_medida", f"Posição de {lab(measure)}", "position_stats", {"column": measure, **({"group_by": cat1} if cat1 else {})},
            "Quanto e quão típico?")
        add("sens_medida", f"Sensibilidade da média de {lab(measure)} a extremos", "sensitivity",
            {"column": measure, "agg": "mean", **({"group_by": cat1} if cat1 else {})}, "Posso confiar nestes dados?")
    if date:
        add("serie", f"{lab(measure).capitalize() if measure else 'Registros'} por mês", "time_series",
            {"date_col": date, "measure": measure, "agg": "sum" if measure else "count", "freq": "M"}, "Para onde está indo?",
            formula=f"soma de {measure} por mês" if measure else "contagem de registros por mês")
        add("tendencia", f"Tendência mensal de {lab(measure) if measure else 'registros'}", "trend_summary",
            {"date_col": date, "measure": measure, "agg": "sum" if measure else "count", "freq": "M"}, "Para onde está indo?")
        months = df[date].dt.to_period("M").nunique() if date in df else 0
        add("sazonal", f"{lab(measure).capitalize() if measure else 'Registros'} médio por {'mês do ano' if months >= 13 else 'dia da semana'}",
            "seasonal_profile", {"date_col": date, "measure": measure, "agg": "sum" if measure else "count",
                                 "by": "month" if months >= 13 else "weekday"}, "Para onde está indo?")
    if cat1:
        if measure:
            add("part_cat", f"{lab(measure).capitalize()} por {lab(cat1)}", "share_of_total", {"category": cat1, "measure": measure},
                "Onde está o volume ou o problema?")
            add("comp_cat", f"{lab(measure).capitalize()} médio por registro, por {lab(cat1)}", "group_comparison",
                {"group": cat1, "measure": measure, "agg": "mean"}, "Em relação a quê?")
        else:
            add("freq_cat", f"Registros por {lab(cat1)}", "frequency_table", {"column": cat1}, "Onde está o volume ou o problema?")
        if date and measure:
            add("contrib_cat", f"Contribuição de cada {lab(cat1)} para a variação entre os dois últimos meses completos",
                "contribution_to_change", {"date_col": date, "group": cat1, "measure": measure, "agg": "sum", "freq": "M"},
                "O que explica a variação?")
    for st in status:
        add(f"freq_{norm_name(st)[:20]}", f"Registros por {lab(st)}", "frequency_table", {"column": st}, "Onde está o volume ou o problema?")
    if entity and measure:
        add("conc_ent", f"Concentração de {lab(measure)} por {lab(entity)}", "concentration", {"item": entity, "measure": measure},
            "Onde está o volume ou o problema?")
    if entity and date:
        add("rfm_ent", f"Recência, frequência e valor por {lab(entity)}", "entity_rfm",
            {"entity": entity, "date_col": date, **({"measure": measure} if measure else {})}, "Quem são as entidades e como se comportam?")
    # prazos
    all_dates = [c for c, t in sem.items() if t == "datetime"]
    deadline = next((c for c in all_dates if _score_name(c, DEADLINE_HINTS)), None)
    end = next((c for c in all_dates if _score_name(c, END_HINTS) and c != deadline), None)
    if deadline and end:
        add("prazo", f"Cumprimento do prazo ({lab(end)} até {lab(deadline)})", "deadline_compliance",
            {"end": end, "deadline": deadline, **({"group_by": cat1} if cat1 else {})}, "Os prazos estão sendo cumpridos?")
    if date and end and end != date:
        add("duracao", f"Tempo entre {lab(date)} e {lab(end)}", "durations", {"start": date, "end": end}, "Os prazos estão sendo cumpridos?",
            unit="dias")
    assoc_cols = (main_measures[:3] + groups[:3])[:6]
    if len(assoc_cols) >= 2:
        add("assoc", "Associação descritiva entre variáveis", "association", {"columns": assoc_cols}, "O que varia junto?")
    # fontes: cobertura das ligações da tabela principal e divergência entre cadastros 1:1
    for r in rmap["relations"]:
        if r["strength"] != "strong" or len(r["child"]["key"]) != 1:
            continue
        a, b = r["child"]["dataset_id"], r["parent"]["dataset_id"]
        if a == main and (r["integrity"]["orphan_rows"] or 0) > 0:
            add(f"cob_{norm_name(b)[:24]}", f"Cobertura de {lab(r['child']['key'][0])} entre {a} e {b}", "source_coverage",
                {"key": r["child"]["key"][0], "key_b": r["parent"]["key"][0]}, "As fontes concordam entre si?", ds=a, dataset_id_b=b)
        if r["cardinality_observed"] == "1:1" and a != main and b != main:
            sa, sb = ws.dataset_meta(a).get("semantic_types", {}), ws.dataset_meta(b).get("semantic_types", {})
            common = [c for c in sa if c in sb and sa[c] == "category" and c not in r["child"]["key"] + r["parent"]["key"]]
            for c in common[:2]:
                add(f"div_{norm_name(c)[:16]}_{norm_name(a)[:12]}", f"Divergência de {lab(c)} entre {a} e {b}", "attribute_divergence",
                    {"key": r["child"]["key"][0], "attribute": c, "key_b": r["parent"]["key"][0], "attribute_b": c},
                    "As fontes concordam entre si?", ds=a, dataset_id_b=b)
    return specs, roles


def dashboard_config(ws: Workspace, results: dict[str, dict], roles: dict, title: str) -> dict:
    def has(mid):
        return f"res_{mid}" in results

    kpis = []
    if has("serie") and results["res_serie"]["values"].get("total") is not None:
        kpis.append({"label": f"Total de {roles['measure'].replace('_', ' ')}" if roles.get("measure") else "Registros no período",
                     "result_id": "res_serie", "path": "total", "format": "compact"})
    kpis.append({"label": "Registros", "result_id": "res_volume", "path": "rows", "format": "integer"})
    if has("volume") and results["res_volume"]["values"].get("entities"):
        kpis.append({"label": f"{roles['entity'].replace('_', ' ').capitalize()} distintos", "result_id": "res_volume",
                     "path": "entities", "format": "integer"})
    if has("tendencia") and results["res_tendencia"]["values"].get("total_change_pct") is not None:
        kpis.append({"label": "Variação do primeiro ao último mês completo", "result_id": "res_tendencia",
                     "path": "total_change_pct", "format": "percent_1"})
    if has("prazo"):
        kpis.append({"label": "No prazo", "result_id": "res_prazo", "path": "on_time_pct", "format": "percent_1"})
    charts_by_mid = {}
    for cid in ws.manifest.get("charts", {}):
        spec = ws.read_json(f"charts/{cid}.json")
        charts_by_mid[spec["result_id"].removeprefix("res_")] = cid
    views_def = [("Visão geral", ["serie", "part_cat", "comp_cat", "sazonal"]),
                 ("Concentração e variação", ["conc_ent", "contrib_cat", "dist_medida"]),
                 ("Prazos e registros", ["prazo", "freq_cat"] + [m for m in charts_by_mid if m.startswith("freq_")])]
    views = []
    for name, mids in views_def:
        cs = [charts_by_mid[m] for m in dict.fromkeys(mids) if m in charts_by_mid]
        if cs:
            views.append({"name": name, "charts": cs})
    period = results.get("res_serie", {}).get("values", {})
    sub = f"Período: {period.get('first_period')} a {period.get('last_period')}" if period.get("first_period") else ""
    return {"title": title, "subtitle": sub, "kpis": kpis[:6], "views": views}


def report_document(ws: Workspace, results: dict[str, dict], roles: dict, title: str, question: str | None) -> dict:
    def has(mid):
        return f"res_{mid}" in results

    m = roles.get("measure")
    ml = m.replace("_", " ") if m else "registros"
    findings = []
    if has("part_cat"):
        r = results["res_part_cat"]
        second = "{{res_part_cat:rows[1].category}} vem em seguida, com {{res_part_cat:rows[1].share|percent_1}}." if len(r["rows"]) > 1 else ""
        findings.append({"type": "finding", "title": f"{{{{res_part_cat:top_category}}}} responde por {{{{res_part_cat:top_share|percent_1}}}} do total de {ml}",
                         "magnitude": f"{{{{res_part_cat:rows[0].total|compact}}}} de {{{{res_part_cat:total|compact}}}} no total.",
                         "reference": second or "Há uma única categoria.",
                         "reliability": "Base de {{res_part_cat:n|integer}} registros; {{res_part_cat:excluded|integer}} excluídos por ausência."})
    if has("tendencia") and results["res_tendencia"]["values"].get("direction"):
        findings.append({"type": "finding", "title": f"{ml.capitalize()} por mês: tendência de {{{{res_tendencia:direction}}}}",
                         "magnitude": "De {{res_tendencia:first_value|compact}} em {{res_tendencia:first_period}} para {{res_tendencia:last_value|compact}} em {{res_tendencia:last_period}} ({{res_tendencia:total_change_pct|percent_1}}).",
                         "reference": "Pico em {{res_tendencia:peak_period}} ({{res_tendencia:peak_value|compact}}) e mínimo em {{res_tendencia:trough_period}} ({{res_tendencia:trough_value|compact}}).",
                         "reliability": "{{res_tendencia:complete_periods|integer}} meses completos; meses parciais ficam fora da tendência."})
    if has("conc_ent"):
        findings.append({"type": "finding", "title": f"Os {{{{const:20%}}}} maiores {roles['entity'].replace('_', ' ')} concentram {{{{res_conc_ent:top20pct_items_share|percent_1}}}} do total",
                         "magnitude": "{{res_conc_ent:items_for_80pct|integer}} de {{res_conc_ent:items|integer}} itens somam {{const:80%}} do total.",
                         "reference": "Índice de Gini {{res_conc_ent:gini|coef}} (0 = igualdade, 1 = concentração total).",
                         "reliability": "Base de {{res_conc_ent:n|integer}} itens; {{res_conc_ent:excluded|integer}} registros sem valor."})
    if has("contrib_cat") and results["res_contrib_cat"]["values"].get("top_contributor"):
        findings.append({"type": "finding", "title": "{{res_contrib_cat:top_contributor}} é o grupo que mais contribui para a variação entre {{res_contrib_cat:period_a}} e {{res_contrib_cat:period_b}}",
                         "magnitude": "Variação total de {{res_contrib_cat:total_delta|compact}} ({{res_contrib_cat:total_delta_pct|percent_1}}).",
                         "reference": "Esse grupo responde por {{res_contrib_cat:top_contribution|percent_1}} da variação.",
                         "reliability": "Compara apenas os dois últimos meses completos."})
    if has("prazo"):
        findings.append({"type": "finding", "title": "{{res_prazo:on_time_pct|percent_1}} dos itens concluídos ficaram dentro do prazo",
                         "magnitude": "{{res_prazo:late|integer}} itens atrasados, com atraso mediano de {{res_prazo:median_delay_late|decimal_1}} dias.",
                         "reference": "{{res_prazo:on_time|integer}} itens no prazo de {{res_prazo:closed|integer}} concluídos.",
                         "reliability": "{{res_prazo:open_items|integer}} itens ainda sem conclusão ficaram fora da taxa."})
    if has("sens_medida"):
        findings.append({"type": "finding", "title": f"Média de {ml} e valores extremos",
                         "magnitude": "Média de {{res_sens_medida:base|compact}}; sem extremos, {{res_sens_medida:without_outliers|compact}} ({{res_sens_medida:change_pct|percent_1}}).",
                         "reference": "A média fica {{res_sens_medida:mean_median_gap_pct|percent_1}} acima ou abaixo da mediana.",
                         "reliability": "{{res_sens_medida:removed|integer}} valores fora das cercas de {{const:1,5 × IQR}}."})
    objective = (f"Responder à pergunta: \"{question}\". Sem um provedor de IA configurado, a pergunta não foi interpretada; "
                 "o relatório apresenta uma exploração geral dos dados.") if question else \
        "Explorar os dados enviados e identificar onde está o volume, como ele evolui, o que explica as variações e quanto se pode confiar nos números."
    data_par = "Foram analisados {{res_volume:rows|integer}} registros da tabela principal"
    if has("volume") and results["res_volume"]["values"].get("periods"):
        data_par += ", distribuídos em {{res_volume:periods|integer}} meses"
    data_par += ". As tabelas, as partições empilhadas e as ligações encontradas entre os arquivos estão no apêndice."
    dev = []
    for cid in ws.manifest.get("charts", {}):
        spec = ws.read_json(f"charts/{cid}.json")
        if "report" in spec.get("targets", []):
            dev.append({"type": "chart", "chart_id": cid})
    warns = [w["message"] for w in ws.manifest.get("warnings", []) if w.get("code") not in ("partitions_stacked",)]
    lim = [{"type": "tool_note", "text": w} for w in list(dict.fromkeys(warns))[:12]]
    lim.append({"type": "paragraph", "text": "A análise é descritiva: não estabelece causas nem significância estatística."})
    return {"title": title, "subtitle": "Exploração dos dados enviados" if not question else question,
            "sections": [{"heading": "Objetivo", "blocks": [{"type": "paragraph", "text": objective}]},
                         {"heading": "Principais achados", "blocks": findings or [{"type": "paragraph", "text": "Sem achados calculáveis."}]},
                         {"heading": "Dados utilizados", "blocks": [{"type": "paragraph", "text": data_par}]},
                         {"heading": "Desenvolvimento", "blocks": dev},
                         {"heading": "Limitações", "blocks": lim}]}


def suggest_all_charts(ws: Workspace, result_ids: list[str]) -> list[str]:
    made = []
    for rid in result_ids:
        res = ws.load_result(rid)
        spec = charts_mod.suggest_chart(res)
        if spec and not charts_mod.validate_spec(spec, res):
            if rid.removeprefix("res_") in ("pos_medida", "assoc"):
                spec["targets"] = ["report"]
            ws.save_chart(spec)
            made.append(spec["chart_id"])
    return made
