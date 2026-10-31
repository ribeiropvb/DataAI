"""Modo harness: um agente externo (Claude Code, Codex, outro) faz o papel dos agentes do DataAI.

As etapas determinísticas e as ferramentas das skills ficam disponíveis como comandos:

    python -m dataai preparar arquivos... [--pergunta "..."] [--entrega both] [--resposta q_id=valor]
    python -m dataai ferramenta <pasta> --listar
    python -m dataai ferramenta <pasta> <nome> '<json com os argumentos>'   (ou @arquivo.json)
    python -m dataai revisar <pasta>

O harness segue as skills (``skills/<nome>/SKILL.md``) e chama as ferramentas por estes comandos.
Os números continuam saindo só das ferramentas; a revisão determinística continua obrigatória.
"""
from __future__ import annotations

import json
from pathlib import Path

from .agents.toolbox import Toolbox
from .orchestrator import Orchestrator, write_execution_summary
from .review import deterministic_review
from .tools import validate
from .workspace import Workspace, now_iso




def _quiet(_msg: str) -> None:
    pass


def prepare(files: list[str | Path], question: str | None, output_mode: str, base_dir: str | Path,
            answers: dict[str, str] | None = None, source_labels: dict[str, str] | None = None) -> dict:
    """Leitura, partições, perfil e mapa de ligações (etapas 1–4). Sem IA."""
    ws = Workspace.create(base_dir, files, question, output_mode, None, source_labels)
    answers = answers or {}
    asked: list[dict] = []

    def ask(qs):
        asked.extend(qs)
        return {q["question_id"]: answers[q["question_id"]] for q in qs if q["question_id"] in answers}

    orch = Orchestrator(ws, None, ask, log=_quiet)
    ws.manifest["mode"] = "harness"
    ws.manifest["status"] = "running"
    ws.save()
    ok = orch.stage_data()
    ws.manifest["status"] = "prepared" if ok else ("needs_clarification" if ws.manifest.get("pending_questions") else "blocked")
    ws.save()
    tb = Toolbox(ws)
    try:
        rmap = ws.read_json("results/relationship_map.json")
    except FileNotFoundError:
        rmap = {}
    return {
        "folder": str(ws.root),
        "status": ws.manifest["status"],
        "question": question,
        "analysis_mode": ws.manifest["request"]["analysis_mode"],
        "output_mode": output_mode,
        "datasets": tb.list_datasets() if ok else [],
        "relationship_summary": rmap.get("summary"),
        "questions_answered": ws.manifest["request"]["clarifications"],
        "assumptions_adopted": ws.manifest["assumptions"],
        "pending_questions": ws.manifest.get("pending_questions", []),
        "questions_seen": [{k: q.get(k) for k in ("question_id", "question", "options", "default_if_unanswered")} for q in asked],
        "next": ("Siga skills/README.md a partir de profile-data/relate-datasets, chamando as ferramentas com "
                 f"'python -m dataai ferramenta {ws.root} <nome> <json>'." if ok else
                 "Pergunte ao usuário as pending_questions e rode 'preparar' de novo com --resposta id=valor."),
    }


def _version(ws: Workspace) -> int:
    """Versão das entregas: 1 até a primeira revisão; depois de uma revisão que pediu correção, a seguinte."""
    revs = ws.manifest.get("reviews", [])
    if not revs:
        return 1
    last = revs[-1]
    return last["version"] + 1 if last["decision"] == "revise" else last["version"]


def list_tools(folder: str | Path) -> list[dict]:
    tb = Toolbox(Workspace(folder))
    return [{"name": n, "description": s.description, "parameters": s.parameters.get("properties", {}),
             "required": s.parameters.get("required", [])} for n, (s, _) in tb._tools.items()]


def call_tool(folder: str | Path, name: str, arguments: dict | None, version: int | None = None) -> str:
    ws = Workspace(folder)
    if not ws.manifest:
        raise FileNotFoundError(f"pasta de análise inválida: {folder} (rode 'preparar' antes)")
    tb = Toolbox(ws, version or _version(ws))
    if name not in tb._tools:
        return json.dumps({"error": f"ferramenta inexistente: {name}", "disponiveis": sorted(tb._tools)}, ensure_ascii=False)
    out = tb.call(name, arguments or {}, list(tb._tools))
    if tb.attachments:  # capturas de tela: o harness pode abrir as imagens
        data = json.loads(out) if out.startswith("{") and not out.endswith('[truncado]"}') else None
        if isinstance(data, dict):
            data["images"] = [str(Path(p)) for p in tb.attachments]
            out = json.dumps(data, ensure_ascii=False, default=str)
        else:
            out += "\nimagens: " + ", ".join(str(p) for p in tb.attachments)
    if name == "compute_metric" and arguments and not out.startswith('{"error"'):
        spec = arguments.get("spec") or {}
        ws = Workspace(folder)
        ws.manifest["metrics"] = [m for m in ws.manifest["metrics"] if m.get("metric_id") != spec.get("metric_id")]
        ws.manifest["metrics"].append({k: spec.get(k) for k in ("metric_id", "label", "function", "dataset_id", "formula",
                                                                 "population", "unit", "decision_question", "filters")})
        ws.save()
    return out


def review(folder: str | Path, max_cycles: int = 3) -> dict:
    """Validação técnica e revisão determinística (o harness acrescenta o próprio julgamento)."""
    ws = Workspace(folder)
    versions = [d["version"] for d in ws.manifest["deliverables"]]
    version = max(versions, default=0)
    cycle = len(ws.manifest.get("reviews", [])) + 1
    val = validate.validate(ws)["result"]
    rep = ws.latest_deliverable("report")
    build = None
    if rep and rep.get("document"):
        from .tools.report import build_report
        build = build_report(ws, rep["document"], rep["version"])  # reconstrução determinística para auditoria
        ws = Workspace(folder)
    det = deterministic_review(ws, val, build)
    issues = det["issues"]
    for n, i in enumerate(issues, start=1):
        i["issue_id"] = f"c{cycle}_{n:03d}"
    defects = [i for i in issues if i.get("severity") == "defect"]
    decision = "approve" if not defects else ("revise" if cycle < max_cycles else "blocked")
    rec = {"cycle": cycle, "version": version, "decision": decision, "checks_performed": det["checks_performed"],
           "validation_decision": val["decision"], "issues": issues, "by": "harness"}
    ws.manifest["reviews"].append(rec)
    if decision in ("approve", "blocked"):
        ws.manifest["status"] = "approved" if decision == "approve" else "not_approved"
        ws.manifest["finished_at"] = now_iso()
        if decision == "approve":
            latest_by_kind = {d["kind"]: d for d in ws.manifest["deliverables"]}  # a mais recente de cada tipo
            ws.manifest["approved_artifacts"] = [{"artifact_ref": d["artifact_ref"], "sha256": d["sha256"]} for d in latest_by_kind.values()]
    ws.save()
    summary = write_execution_summary(ws)
    latest = {}
    for d in ws.manifest["deliverables"]:
        latest[d["kind"]] = str(ws.path(d["artifact_ref"]))
    return {"decision": decision, "cycle": cycle, "max_cycles": max_cycles, "validation": val["decision"],
            "issues": [{k: i.get(k) for k in ("issue_id", "severity", "category", "location", "problem", "target_skill",
                                               "acceptance_criteria")} for i in issues],
            "deliverables": latest, "execution_summary": summary,
            "next": {"approve": "Entregue os arquivos ao usuário com o resumo da execução.",
                     "revise": f"Corrija os defeitos (cada um indica a skill), gere as entregas de novo (versão {version + 1}) e rode 'revisar' outra vez.",
                     "blocked": "Limite de ciclos atingido: entregue avisando que não foi aprovado e quais defeitos restam."}[decision]}
