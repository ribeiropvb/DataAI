"""Auditoria técnica (skill validate-analysis): os números estão certos e são os mesmos em todo lugar?"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..envelope import envelope, is_valid_envelope
from ..workspace import Workspace, load_json, sha256_file
from . import metrics
from .charts import ColorMap, echarts_option
from .fmt import format_value
from .inspect import extract_dashboard_data, inspect_pdf, scan_dashboard_static
from .refs import resolve_path

REL_TOL = 1e-9


def _close(a, b) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    return a == b


def _issue(n: int, category: str, artifact: str, location: str, problem: str, owner: str, skill: str,
           evidence: list[str] | None = None, severity: str = "defect", acceptance: str = "") -> dict:
    return {"issue_id": f"val_{n:03d}", "category": category, "severity": severity, "artifact_ref": artifact,
            "location": location, "evidence_refs": evidence or [], "problem": problem, "impact": "",
            "owner_agent": owner, "target_skill": skill, "acceptance_criteria": acceptance or "Valor igual ao resultado calculado.",
            "status": "open", "verified_by": None}


def validate(ws: Workspace, output_mode: str | None = None) -> dict:
    checks, issues = [], []
    output_mode = output_mode or ws.manifest["request"]["output_mode"]

    def add(check_id, target, ok, detail="", issue=None):
        checks.append({"check_id": check_id, "target": target, "ok": bool(ok), "detail": detail})
        if not ok and issue:
            issues.append(issue)

    # 1. contratos
    for p in sorted(ws.path("skill_outputs").glob("*.json")):
        env = load_json(p)
        add("contract_envelope", ws.rel(p), is_valid_envelope(env), "" if is_valid_envelope(env) else "envelope incompleto",
            _issue(len(issues) + 1, "contract", ws.rel(p), "envelope", "Saída de skill sem o envelope completo.",
                   "technical-reviewer", env.get("skill_name", "?") if isinstance(env, dict) else "?"))
        answered = {c["question_id"] for c in ws.manifest["request"].get("clarifications", [])} | \
                   {a.get("question_id") for a in ws.manifest.get("assumptions", []) if isinstance(a, dict)}
        for q in env.get("questions", []) if isinstance(env, dict) else []:
            ok = q["question_id"] in answered
            add("question_resolved", q["question_id"], ok, "" if ok else "pergunta sem resposta nem suposição registrada",
                _issue(len(issues) + 1, "contract", ws.rel(p), q["question_id"], f"Pergunta sem resposta: {q['question']}",
                       "analysis-planner", "plan-analysis"))
    # 2. dados e tratamentos
    for f in ws.manifest["files"]:
        ok = sha256_file(ws.path(f["file"])) == f["sha256"]
        add("original_hash", f["file"], ok, "" if ok else "arquivo original alterado",
            _issue(len(issues) + 1, "data", f["file"], "hash", "Arquivo original foi alterado.", "data-specialist", "ingest-tabular"))
    for t in ws.manifest["treatments"]:
        if t.get("requires_authorization"):
            ok = bool(t.get("authorized_by"))
            add("treatment_authorized", t["treatment_id"], ok, "" if ok else "tratamento sem autorização",
                _issue(len(issues) + 1, "data", "manifest.json", t["treatment_id"], f"Tratamento sem autorização: {t['description']}",
                       "data-specialist", "profile-data"))
        if t["kind"] == "join":
            for c in t["details"].get("control_totals", []):
                if c.get("ok") is False:
                    add("join_control_total", t["treatment_id"], False, str(c),
                        _issue(len(issues) + 1, "relation", "manifest.json", t["treatment_id"], f"Total de controle diferente: {c}",
                               "data-specialist", "relate-datasets"))
        if t["kind"] == "stack":
            ok = t["details"].get("ok", True)
            add("stack_rows", t["treatment_id"], ok)
    for d in ws.manifest["datasets"]:
        ok = ws.path(d["working_path"]).exists()
        add("dataset_exists", d["dataset_id"], ok)
    # 3/4. cálculos reexecutados
    for rid in ws.list_results():
        res = ws.load_result(rid)
        spec = res.get("spec")
        if not spec:
            continue
        try:
            again = metrics.compute(spec, ws, save=False)
        except Exception as e:
            add("calc_rerun", rid, False, f"falhou: {e}",
                _issue(len(issues) + 1, "numeric_mismatch", f"results/{rid}.json", rid, f"Cálculo não reexecutável: {e}",
                       "data-analyst", "describe-data"))
            continue
        ok = _close(res.get("values"), again.get("values")) and _close(res.get("rows"), again.get("rows"))
        add("calc_rerun", rid, ok, "" if ok else "valores diferentes na reexecução",
            _issue(len(issues) + 1, "numeric_mismatch", f"results/{rid}.json", rid, "Reexecução deu valores diferentes.",
                   "data-analyst", "describe-data", [f"results/{rid}.json"]))
        if res.get("function") == "rate":
            for r in [res.get("values", {})] + (res.get("rows") or []):
                num, den = r.get("numerator"), r.get("denominator")
                if "filter" in spec["params"].get("numerator", {}) and num is not None and den and num > den:
                    add("rate_bounds", rid, False, f"numerador {num} > denominador {den}",
                        _issue(len(issues) + 1, "numeric_mismatch", f"results/{rid}.json", rid, "Numerador maior que denominador.",
                               "data-analyst", "describe-data"))
                    break
    # 5. consistência entre entregas
    rep = ws.latest_deliverable("report")
    if output_mode in ("report", "both"):
        if not rep:
            add("format_pdf", "report", False, "relatório pedido e não gerado",
                _issue(len(issues) + 1, "format", "deliverables", "-", "Relatório PDF pedido e não gerado.", "report-writer", "write-analysis-report"))
        else:
            info = inspect_pdf(ws.path(rep["artifact_ref"]))
            add("format_pdf", rep["artifact_ref"], info.get("is_pdf") and info.get("pages", 0) > 0, info.get("error", ""),
                _issue(len(issues) + 1, "format", rep["artifact_ref"], "-", "Arquivo não é PDF válido.", "report-writer", "write-analysis-report"))
            text = "\n".join(info.get("text_by_page", []))
            norm = lambda s: s.replace(" ", " ").replace("\n", " ")
            for ref in rep.get("number_refs", []):
                if ref["result_id"] == "const":
                    continue
                try:
                    cur = ws.load_result(ref["result_id"])
                    expected = format_value(resolve_path(cur, ref["path"]), ref.get("format"))
                except Exception as e:
                    add("pdf_vs_results", rep["artifact_ref"], False, str(e),
                        _issue(len(issues) + 1, "numeric_mismatch", rep["artifact_ref"], ref.get("location", ""), f"Referência quebrada: {e}",
                               "report-writer", "write-analysis-report"))
                    continue
                ok = expected == ref["text"] and cur.get("version") == ref.get("version")
                add("pdf_vs_results", rep["artifact_ref"], ok, "" if ok else f"{ref['location']}: cita {ref['text']}, atual {expected}",
                    _issue(len(issues) + 1, "numeric_mismatch", rep["artifact_ref"], ref.get("location", ""),
                           f"Cita {ref['text']}; resultado atual é {expected} (versão {cur.get('version')}).", "report-writer",
                           "write-analysis-report", [f"results/{ref['result_id']}.json"]))
                if ok and norm(ref["text"]) not in norm(text) and len(ref["text"]) > 1:
                    add("pdf_text_contains", rep["artifact_ref"], False, f"{ref['text']} não encontrado no texto extraído",
                        _issue(len(issues) + 1, "numeric_mismatch", rep["artifact_ref"], ref.get("location", ""),
                               f"Número {ref['text']} não aparece no PDF renderizado.", "report-writer", "write-analysis-report",
                               severity="suggestion"))
    dash = ws.latest_deliverable("dashboard")
    if output_mode in ("dashboard", "both"):
        if not dash:
            add("format_html", "dashboard", False, "dashboard pedido e não gerado",
                _issue(len(issues) + 1, "format", "deliverables", "-", "Dashboard HTML pedido e não gerado.", "interface-designer", "compose-dashboard"))
        else:
            path = ws.path(dash["artifact_ref"])
            scan = scan_dashboard_static(path)
            add("format_html", dash["artifact_ref"], scan["is_html"])
            data = extract_dashboard_data(path.read_text(encoding="utf-8")) or {}
            for k in data.get("kpis", []):
                cur = resolve_path(ws.load_result(k["result_id"]), k["path"])
                ok = _close(cur, k["value"])
                add("html_kpi_vs_results", dash["artifact_ref"], ok, "" if ok else f"KPI {k['label']}: {k['value']} vs {cur}",
                    _issue(len(issues) + 1, "numeric_mismatch", dash["artifact_ref"], f"KPI {k['label']}",
                           f"KPI mostra {k['value']}; resultado atual é {cur}.", "interface-designer", "compose-dashboard"))
            colors = ColorMap((dash.get("config") or {}).get("color_map"))
            for ch in data.get("charts", []):
                spec = ws.read_json(f"charts/{ch['chart_id']}.json")
                cur = ws.load_result(ch["result_id"])
                expected = json.loads(json.dumps(echarts_option(spec, cur, colors), default=str))
                ok = _close(expected.get("series"), ch["option"].get("series")) and spec["result_id"] == ch["result_id"]
                add("html_chart_vs_results", dash["artifact_ref"], ok, "" if ok else f"gráfico {ch['chart_id']} desatualizado",
                    _issue(len(issues) + 1, "numeric_mismatch", dash["artifact_ref"], f"gráfico {ch['chart_id']}",
                           "Dados do gráfico diferem do resultado atual.", "interface-designer", "compose-dashboard"))
    # mesmo indicador no PDF e no HTML
    if rep and dash:
        data = extract_dashboard_data(ws.path(dash["artifact_ref"]).read_text(encoding="utf-8")) or {}
        for k in data.get("kpis", []):
            for ref in rep.get("number_refs", []):
                if ref["result_id"] == k["result_id"] and ref["path"] == k["path"]:
                    ok = _close(ref["raw"], k["value"])
                    add("pdf_vs_html", f"{k['result_id']}:{k['path']}", ok, "" if ok else "valores diferentes no PDF e no HTML",
                        _issue(len(issues) + 1, "numeric_mismatch", rep["artifact_ref"], ref.get("location", ""),
                               "Mesmo indicador com valores diferentes no PDF e no HTML.", "report-writer", "write-analysis-report"))
    defects = [i for i in issues if i["severity"] == "defect"]
    decision = "fail" if defects else ("pass_with_warnings" if issues else "pass")
    env = envelope("validate-analysis", "completed", {"decision": decision, "checks": checks, "issues": issues,
                                                       "summary": {"checks": len(checks), "failed": sum(not c["ok"] for c in checks)}},
                   evidence_refs=["manifest.json"])
    ws.save_skill_output(env)
    return env
