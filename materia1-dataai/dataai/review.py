"""Verificações determinísticas da revisão final (skill orchestrate-quality-review).

Rodam sempre, com ou sem IA. O agente orquestrador de qualidade acrescenta o julgamento (storytelling,
estética), mas nunca pode aprovar algo que estas verificações reprovam.
"""
from __future__ import annotations

from .tools import inspect as inspect_mod
from .tools.textutil import strip_accents, tokens
from .workspace import Workspace

DESCRIPTIVE_ONLY = {"M1", "M2", "M3", "M4"}


def _issue(issues: list, category: str, artifact: str, location: str, problem: str, owner: str, skill: str,
           acceptance: str, evidence: list[str] | None = None, severity: str = "defect", impact: str = "") -> None:
    issues.append({"issue_id": f"rev_{len(issues) + 1:03d}", "category": category, "severity": severity,
                   "artifact_ref": artifact, "location": location, "evidence_refs": evidence or [], "problem": problem,
                   "impact": impact, "owner_agent": owner, "target_skill": skill, "acceptance_criteria": acceptance,
                   "status": "open", "verified_by": None})


def deterministic_review(ws: Workspace, validation: dict, report_build: dict | None = None) -> dict:
    issues: list[dict] = []
    checks: list[str] = []
    mode = ws.manifest["request"]["output_mode"]
    rep, dash = ws.latest_deliverable("report"), ws.latest_deliverable("dashboard")
    # formato (RN-009)
    checks.append("format")
    if mode in ("report", "both") and not rep:
        _issue(issues, "format", "deliverables", "-", "Relatório PDF pedido e não gerado.", "report-writer", "write-analysis-report",
               "Existe report.pdf válido.", impact="Viola RN-004.")
    if mode in ("dashboard", "both") and not dash:
        _issue(issues, "format", "deliverables", "-", "Dashboard HTML pedido e não gerado.", "interface-designer", "compose-dashboard",
               "Existe dashboard.html válido.", impact="Viola RN-005.")
    render = None
    if dash:
        p = ws.path(dash["artifact_ref"])
        static = inspect_mod.scan_dashboard_static(p)
        checks += ["dashboard_narrative", "visual", "interaction", "responsiveness"]
        for h in static["narrative_hits"]:
            _issue(issues, "dashboard_narrative", dash["artifact_ref"], h["where"], f"Texto interpretativo no dashboard: '{h['text']}' ({h['match']}).",
                   "interface-designer", "compose-dashboard", "Texto apenas descritivo, sem conclusão.", impact="Viola RN-006.")
        if static["has_paragraphs"]:
            _issue(issues, "dashboard_narrative", dash["artifact_ref"], "<p>", "Dashboard contém parágrafos de texto.",
                   "interface-designer", "compose-dashboard", "Sem parágrafos analíticos.", impact="Viola RN-006.")
        render = inspect_mod.render_dashboard(p, ws.path(f"review/screens_v{dash['version']}"))
        if not render.get("available"):
            _issue(issues, "visual", dash["artifact_ref"], "-", "Não foi possível renderizar o dashboard (navegador headless ausente).",
                   "interface-designer", "compose-dashboard", "Renderização verificada.", impact="Revisão visual obrigatória não realizada (P-013).")
        else:
            if render["console_errors"]:
                _issue(issues, "interaction", dash["artifact_ref"], "console", f"Erros no navegador: {render['console_errors'][:3]}",
                       "interface-designer", "compose-dashboard", "Nenhum erro no console.", render["screens"][:1])
            for cid, ok in render["charts_rendered"].items():
                if not ok:
                    _issue(issues, "visual", dash["artifact_ref"], f"gráfico {cid}", "Gráfico não renderizou.", "interface-designer",
                           "compose-dashboard", "Gráfico visível com dados.", render["screens"][:1])
            for w, scroll in render["horizontal_scroll"].items():
                if scroll:
                    _issue(issues, "responsiveness", dash["artifact_ref"], f"largura {w}px", "Rolagem horizontal na página.",
                           "interface-designer", "compose-dashboard", "Sem rolagem horizontal.", [s for s in render["screens"] if f"_{w}" in s][:1])
            for h in render.get("narrative_in_tooltips", []):
                _issue(issues, "dashboard_narrative", dash["artifact_ref"], "tooltip", f"Tooltip interpretativo: {h['text']}",
                       "interface-designer", "compose-dashboard", "Tooltip só com valores, unidades e categoria.")
    if rep:
        info = inspect_mod.inspect_pdf(ws.path(rep["artifact_ref"]), ws.path(f"review/pages_v{rep['version']}"))
        checks += ["legibility", "storytelling", "interpretation"]
        if info.get("empty_pages"):
            _issue(issues, "legibility", rep["artifact_ref"], f"páginas {info['empty_pages']}", "Páginas vazias no PDF.",
                   "report-writer", "write-analysis-report", "Nenhuma página vazia.")
        doc = rep.get("document") or {}
        build = report_build or {}
        for e in build.get("errors", []):
            _issue(issues, "numeric_mismatch", rep["artifact_ref"], e.split(":")[0], f"Marcador ou bloco inválido: {e}",
                   "report-writer", "write-analysis-report", "Todos os marcadores resolvidos para resultados existentes.")
        for rn in build.get("raw_numbers", []):
            _issue(issues, "numeric_mismatch", rep["artifact_ref"], rn["location"],
                   f"Número '{rn['number']}' escrito diretamente, sem marcador de resultado: \"{rn['text']}\"",
                   "report-writer", "write-analysis-report", "Todo número do texto vem de um marcador {{result_id:campo}}.",
                   impact="Números precisam vir de ferramentas (regra 2).")
        headings = [strip_accents(s.get("heading", "")).lower() for s in doc.get("sections", [])]
        if not any("limita" in h for h in headings):
            _issue(issues, "missing_content", rep["artifact_ref"], "estrutura", "Relatório sem seção de limitações.",
                   "report-writer", "write-analysis-report", "Seção 'Limitações' presente.", impact="RN-011 / skill write-analysis-report.")
        findings = [b for s in doc.get("sections", []) for b in s.get("blocks", []) if b.get("type") == "finding"]
        if not findings:
            _issue(issues, "storytelling", rep["artifact_ref"], "achados", "Relatório sem achados principais estruturados.",
                   "report-writer", "write-analysis-report", "Achados principais com magnitude, referência e confiabilidade.", impact="CA-031.")
        for i, f in enumerate(findings, start=1):
            miss = [k for k in ("magnitude", "reference", "reliability") if not f.get(k)]
            if miss:
                _issue(issues, "storytelling", rep["artifact_ref"], f"achado {i} ({f.get('title', '')[:50]})",
                       f"Achado sem {', '.join(miss)}.", "report-writer", "write-analysis-report",
                       "Cada achado traz magnitude, comparação com referência e confiabilidade.", impact="CA-031 / RN-016.")
        q = ws.manifest["request"].get("question")
        if q:
            text = strip_accents(" ".join(info.get("text_by_page", [])[:3])).lower()
            qt = [t for t in tokens(q) if len(t) > 3]
            if qt and sum(t in text for t in qt) / len(qt) < 0.6:
                _issue(issues, "storytelling", rep["artifact_ref"], "início do relatório", "A pergunta do usuário não aparece no início.",
                       "report-writer", "write-analysis-report", "Pergunta citada no objetivo e respondida no primeiro achado.", impact="CA-004.")
    # abrangência (RN-016)
    checks.append("metric_breadth")
    used = set()
    for d in (rep, dash):
        if not d:
            continue
        for cid in d.get("charts_included", []):
            try:
                used.add(ws.read_json(f"charts/{cid}.json")["result_id"])
            except FileNotFoundError:
                pass
        for r in d.get("number_refs", []) or []:
            if r["result_id"] != "const":
                used.add(r["result_id"])
        for k in (d.get("config") or {}).get("kpis", []):
            used.add(k["result_id"])
    fams = set()
    for rid in used:
        try:
            fams.add(ws.load_result(rid).get("family"))
        except FileNotFoundError:
            pass
    applicable = set()
    for ds in ws.manifest["datasets"]:
        try:
            prof = ws.read_json(f"results/profile_{ds['dataset_id']}.json")
            applicable |= {f for f, ok in (prof.get("applicable_families") or {}).items() if ok}
        except FileNotFoundError:
            continue
    decision_fams = (applicable - DESCRIPTIVE_ONLY) & {"M5", "M6", "M7", "M8", "M10", "M11", "M12", "M14"}
    if used and len(decision_fams) >= 2 and len(fams - DESCRIPTIVE_ONLY - {None}) < 2:
        _issue(issues, "missing_content", (rep or dash)["artifact_ref"], "conjunto das entregas",
               f"Entregas usam só métricas de posição/dispersão/volume ({sorted(fams)}), embora os dados permitam {sorted(decision_fams)}.",
               "analysis-planner", "plan-analysis", "Pelo menos duas famílias orientadas à decisão (composição, concentração, tendência, referência, decomposição...).",
               impact="Viola RN-016.")
    # números
    checks.append("numbers")
    for i in validation.get("issues", []):
        issues.append({**i, "issue_id": f"rev_{len(issues) + 1:03d}"})
    if validation.get("decision") in ("fail", "blocked") and not validation.get("issues"):
        _issue(issues, "numeric_mismatch", "-", "-", f"Validação técnica com decisão {validation.get('decision')}.",
               "technical-reviewer", "validate-analysis", "Validação aprovada.")
    return {"issues": issues, "checks_performed": sorted(set(checks)), "render": render}
