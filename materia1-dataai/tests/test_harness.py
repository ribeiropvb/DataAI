"""Modo harness: um agente externo conduz a análise só pelos comandos da linha de comando."""
import json

import pytest

from conftest import ECHARTS, browser_available
from dataai.cli import main


def run(capsys, *args) -> tuple[int, dict | list | str]:
    rc = main([str(a) for a in args])
    out = capsys.readouterr().out
    try:
        return rc, json.loads(out)
    except json.JSONDecodeError:
        return rc, out


def test_harness_flow(tmp_path, demo_dir, capsys, monkeypatch):
    if ECHARTS:
        monkeypatch.setenv("DATAAI_ECHARTS_JS", ECHARTS)
    rc, prep = run(capsys, "preparar", *sorted(demo_dir.iterdir()), "--pergunta", "Quais lojas explicam a variação da receita?",
                   "--pasta", tmp_path)
    assert rc == 0 and prep["status"] == "prepared"
    folder = prep["folder"]
    roles = {d["dataset_id"]: d["role"] for d in prep["datasets"]}
    assert roles["ds_vendas"] == "fato"

    rc, tools = run(capsys, "ferramenta", folder, "--listar")
    assert {"compute_metric", "build_report", "inspect_dashboard"} <= {t["name"] for t in tools}

    rc, j = run(capsys, "ferramenta", folder, "join_datasets", json.dumps(
        {"left_id": "ds_vendas", "right_id": "ds_cadastro_lojas", "left_on": ["loja_id"], "right_on": ["loja_id"],
         "derived_id": "ds_vl"}))
    assert rc == 0 and all(c["ok"] for c in j["control_totals"])

    def metric(spec):
        rc, r = run(capsys, "ferramenta", folder, "compute_metric", json.dumps({"spec": spec}))
        assert rc == 0, r
        return r

    base = {"dataset_id": "ds_vl", "unit": "R$", "population": "todas as vendas"}
    r = metric({**base, "metric_id": "res_total", "label": "Receita", "function": "position_stats", "params": {"column": "valor_total"},
                "formula": "valor_total"})
    assert r["result_id"] == "res_total"  # sem prefixo duplicado
    metric({**base, "metric_id": "contrib", "label": "Contribuição das lojas", "function": "contribution_to_change",
            "params": {"date_col": "data_venda", "group": "nome_loja", "measure": "valor_total", "agg": "sum", "freq": "Q",
                       "period_a": "2024Q1", "period_b": "2025Q1"}, "formula": "Δ loja / Δ total"})
    metric({**base, "metric_id": "share", "label": "Participação das lojas", "function": "share_of_total", "unit": "%",
            "params": {"category": "nome_loja", "measure": "valor_total"}, "formula": "loja / total"})

    rc, err = run(capsys, "ferramenta", folder, "compute_metric", json.dumps({"spec": {**base, "metric_id": "x", "label": "x",
                  "function": "position_stats", "params": {"column": "nao_existe"}, "formula": "-"}}))
    assert rc == 1 and "error" in err

    for rid in ("res_contrib", "res_share"):
        rc, spec = run(capsys, "ferramenta", folder, "suggest_chart", json.dumps({"result_id": rid}))
        rc, saved = run(capsys, "ferramenta", folder, "save_chart", json.dumps({"spec": spec}))
        assert saved["ok"], saved
    rc, dash = run(capsys, "ferramenta", folder, "build_dashboard", json.dumps({"config": {
        "title": "Receita por loja", "kpis": [{"label": "Receita", "result_id": "res_total", "path": "sum", "format": "currency_brl"}],
        "views": [{"name": "Lojas", "charts": ["ch_share", "ch_contrib"]}]}}))
    assert rc == 0 and dash["version"] == 1

    doc = {"title": "Quais lojas explicam a variação da receita?", "sections": [
        {"heading": "Principais achados", "blocks": [
            {"type": "finding", "title": "Variação concentrada em poucas lojas",
             "magnitude": "{{res_contrib:top_contribution|percent_0}} da variação vem de {{res_contrib:top_contributor}}",
             "reference": "variação total de {{res_contrib:total_delta|currency_brl}} entre 2024 e 2025 (1º trimestre)",
             "reliability": "n = {{res_total:n|integer}} vendas em 12 lojas"},  # "12" é número digitado: defeito esperado
            {"type": "chart", "chart_id": "ch_contrib"}]},
        {"heading": "Limitações", "blocks": [{"type": "paragraph", "text": "Análise descritiva."}]}]}
    path = tmp_path / "doc.json"
    path.write_text(json.dumps({"document": doc}), encoding="utf-8")
    rc, rep = run(capsys, "ferramenta", folder, "build_report", f"@{path}")
    assert rc == 0 and rep["version"] == 1

    if not browser_available():
        pytest.skip("navegador headless indisponível")
    rc, rev = run(capsys, "revisar", folder)
    assert rev["decision"] == "revise"
    assert any("sem marcador" in i["problem"] for i in rev["issues"])

    doc["sections"][0]["blocks"][0]["reliability"] = "n = {{res_total:n|integer}} vendas"
    path.write_text(json.dumps({"document": doc}), encoding="utf-8")
    rc, rep = run(capsys, "ferramenta", folder, "build_report", f"@{path}")
    assert rep["version"] == 2  # versão sobe depois de uma revisão que pediu correção
    rc, rev = run(capsys, "revisar", folder)
    assert rev["decision"] == "approve", rev["issues"]
    assert rev["deliverables"]["dashboard"].endswith("v1/dashboard.html")
    assert rev["deliverables"]["report"].endswith("v2/report.pdf")
    manifest = json.loads((tmp_path / prep["folder"].split("/")[-1] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "approved" and len(manifest["approved_artifacts"]) == 2
    assert sum(d["kind"] == "report" and d["version"] == 2 for d in manifest["deliverables"]) == 1
