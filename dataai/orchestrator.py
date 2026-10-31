"""Orquestração de uma análise completa (specs 8.1, 8.2, 8.3, 12.2, 12.9).

    ingestão → partições → perfil → mapa de ligações → [especialista de dados]
      → plano → junções → métricas → gráficos → dashboard e/ou relatório
      → validação técnica → revisão de qualidade ↺ correções (até 3 ciclos) → resumo da execução

Com ``provider`` (um ``LLMProvider``), as decisões são dos agentes. Sem provedor (``--no-llm``),
o fluxo usa ``heuristics`` para planejar e redigir, sem interpretação.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from . import heuristics, review
from .agents.profiles import load_profiles
from .agents.runner import AgentRunner
from .agents.toolbox import Toolbox
from .envelope import envelope
from .llm.base import LLMProvider
from .tools import charts as charts_mod
from .tools import ingest, metrics, profile, relations, validate
from .tools.fmt import format_value
from .workspace import Workspace, now_iso

MAX_CYCLES = 3  # [proposta MVP] P-012

AskFn = Callable[[list[dict]], dict[str, str]]


class Orchestrator:
    def __init__(self, ws: Workspace, provider: LLMProvider | None = None, ask: AskFn | None = None,
                 inline_library: str | None = None, max_cycles: int = MAX_CYCLES, log: Callable[[str], None] = print):
        self.ws = ws
        self.provider = provider
        self.ask = ask
        self.inline_library = inline_library
        self.max_cycles = max_cycles
        self.log = log
        self.profiles = load_profiles() if provider else {}
        self.plan: dict = {}
        self.report_build: dict | None = None
        self.roles: dict = {}

    # ------------------------------------------------------------------ utilidades
    def _agent(self, agent_id: str, task: str, context: dict | None = None, version: int = 1) -> dict:
        tb = Toolbox(self.ws, version, self.inline_library)
        runner = AgentRunner(self.profiles[agent_id], self.provider, tb)
        self.log(f"  agente {agent_id}…")
        env = runner.run(task, context)
        self.ws.save_skill_output(env, agent_id)
        return env

    def _questions(self, env: dict) -> bool:
        """Resolve perguntas: pergunta ao usuário (se houver ``ask``) ou aplica o padrão como suposição.
        Devolve False se alguma pergunta sem padrão ficar sem resposta (análise pausa, P-005)."""
        qs = env.get("questions") or []
        if not qs:
            return True
        answers = self.ask(qs) if self.ask else {}
        for q in qs:
            if q["question_id"] in answers:
                self.ws.manifest["request"]["clarifications"].append(
                    {"question_id": q["question_id"], "question": q["question"], "answer": answers[q["question_id"]], "at": now_iso()})
            elif q.get("default_if_unanswered") is not None:
                self.ws.manifest["assumptions"].append(
                    {"question_id": q["question_id"], "assumption": f"{q['question']} → adotado: {q['default_if_unanswered']}",
                     "why": q.get("why_it_matters")})
            else:
                self.ws.manifest["pending_questions"] = self.ws.manifest.get("pending_questions", []) + [q]
                self.ws.save()
                return False
        self.ws.save()
        return True

    # ------------------------------------------------------------------ etapas
    def stage_data(self) -> bool:
        ws = self.ws
        self.log("1. Lendo arquivos…")
        env = ingest.ingest(ws)
        if env["status"] == "blocked":
            ws.manifest["status"] = "blocked"
            ws.save()
            return False
        if not self._questions(env):
            return False
        self.log("2. Procurando partições (uma tabela em vários arquivos)…")
        stage = relations.relationship_map(ws)
        self.log("3. Perfil dos dados…")
        penv = profile.profile(ws, stage["active"])
        if not self._questions(penv):
            return False
        self.log("4. Descobrindo ligações entre arquivos…")
        renv = relations.finalize_relationship_map(ws, stage)
        if self.provider:
            self._agent("data-specialist", "Revise os perfis e o mapa de ligações desta análise. Corrija tipos semânticos mal inferidos e "
                        "confirme ou rejeite as ligações prováveis. Não junte tabelas.",
                        {"relationship_summary": renv["result"]["summary"], "warnings": renv["warnings"]})
        return self._questions(renv)

    def stage_plan(self) -> None:
        ws = self.ws
        req = ws.manifest["request"]
        self.log("5. Planejando a análise…")
        if self.provider:
            env = self._agent("analysis-planner",
                              "Monte o plano executável desta análise. Junções: colunas da direita mantêm o nome; em conflito recebem o sufixo "
                              "__<right_id>; a chave da direita é descartada.",
                              {"question": req["question"], "analysis_mode": req["analysis_mode"], "output_mode": req["output_mode"],
                               "assumptions_so_far": ws.manifest["assumptions"]})
            self._questions(env)
            self.plan = env.get("result") or {}
        else:
            main = heuristics.choose_main_table(ws)
            joins = heuristics.plan_joins(ws, main)
            self.plan = {"analysis_mode": req["analysis_mode"], "question": req["question"], "output_mode": req["output_mode"],
                         "main_table": main, "joins": joins, "metrics": [],
                         "assumptions": ["Modo sem IA: nenhum filtro de população foi aplicado (todas as linhas entram, inclusive "
                                         "registros que um analista poderia excluir, como cancelados)."],
                         "limitations": []}
            if req["question"]:
                self.plan["limitations"].append("Sem provedor de IA, a pergunta não foi interpretada; foi feita exploração geral.")
        ws.write_json("results/plan.json", self.plan)
        for a in self.plan.get("assumptions", []):
            ws.manifest["assumptions"].append({"assumption": a, "source": "plan"})
        ws.save()

    def stage_relate(self) -> None:
        self.log("6. Juntando tabelas conforme o plano…")
        done = []
        for j in self.plan.get("joins", []):
            try:
                rec = relations.safe_join(self.ws, j["left_id"], j["right_id"], j["left_on"], j["right_on"], j.get("how", "left"),
                                          j.get("derived_id"), j.get("aggregate_right"))
                done.append(rec)
            except Exception as e:
                self.ws.manifest["warnings"].append({"code": "join_failed", "message": f"Junção {j['left_id']} + {j['right_id']} não feita: {e}",
                                                     "evidence_refs": [], "skill": "relate-datasets"})
        self.ws.save_skill_output(envelope("relate-datasets", "completed", {"relations": done}), "joins")
        if not self.provider:
            ds = done[-1]["derived_dataset_id"] if done else self.plan["main_table"]
            specs, self.roles = heuristics.plan_metrics(self.ws, self.plan["main_table"], ds)
            self.plan["metrics"] = specs
            self.plan["roles"] = self.roles
            self.ws.write_json("results/plan.json", self.plan)

    def stage_compute(self) -> list[str]:
        self.log("7. Calculando métricas…")
        ok, failed = [], []
        for spec in self.plan.get("metrics", []):
            try:
                res = metrics.compute(spec, self.ws)
                ok.append(res["result_id"])
                self.ws.manifest["metrics"].append({k: spec.get(k) for k in ("metric_id", "label", "function", "dataset_id", "formula",
                                                                              "population", "unit", "decision_question", "filters")})
            except Exception as e:
                failed.append({"metric_id": spec.get("metric_id"), "spec": spec, "reason": f"{type(e).__name__}: {e}"})
        self.ws.save()
        if failed and self.provider:
            env = self._agent("data-analyst", "Algumas métricas do plano falharam. Corrija as specs e calcule com compute_metric, "
                              "sem trocar o significado da métrica sem registrar.", {"failed": failed})
            ok += [r for r in (env.get("result") or {}).get("results", []) if isinstance(r, str)]
        elif failed:
            for f in failed:
                self.ws.manifest["warnings"].append({"code": "metric_failed", "message": f"Métrica {f['metric_id']} não calculada: {f['reason']}",
                                                     "evidence_refs": [], "skill": "describe-data"})
        self.ws.save_skill_output(envelope("describe-data", "completed", {"results": ok, "failed": failed}))
        return ok

    def stage_charts(self, result_ids: list[str]) -> None:
        self.log("8. Especificando gráficos…")
        if self.provider:
            self._agent("visualization-specialist", "Especifique e salve os gráficos dos resultados desta análise.",
                        {"planned_charts": self.plan.get("charts", []), "results": result_ids})
        else:
            heuristics.suggest_all_charts(self.ws, result_ids)

    def stage_deliverables(self, version: int, repair: dict[str, list[dict]] | None = None) -> None:
        ws = self.ws
        mode = ws.manifest["request"]["output_mode"]
        repair = repair or {}
        results = {rid: ws.load_result(rid) for rid in ws.list_results()}
        title = self.plan.get("title") or ("Análise: " + ws.manifest["request"]["question"] if ws.manifest["request"]["question"]
                                           else "Exploração dos dados")
        prev_dash, prev_rep = ws.latest_deliverable("dashboard"), ws.latest_deliverable("report")
        if mode in ("dashboard", "both") and (version == 1 or "compose-dashboard" in repair):
            self.log(f"9. Gerando dashboard (v{version})…")
            if self.provider:
                self._agent("interface-designer", "Gere o dashboard HTML desta análise e confira com inspect_dashboard."
                            + (" Corrija os problemas listados em issues." if repair.get("compose-dashboard") else ""),
                            {"plan_views": self.plan.get("dashboard_views"), "issues": repair.get("compose-dashboard", []),
                             "previous_config": (prev_dash or {}).get("config")}, version)
            else:
                from .tools.dashboard import build_dashboard
                build_dashboard(ws, heuristics.dashboard_config(ws, results, self.roles, title), version, self.inline_library)
        elif mode in ("dashboard", "both") and prev_dash and version > 1:
            self._carry(prev_dash, version)
        if mode in ("report", "both") and (version == 1 or "write-analysis-report" in repair):
            self.log(f"10. Gerando relatório PDF (v{version})…")
            if self.provider:
                env = self._agent("report-writer", "Escreva e gere o relatório PDF desta análise e confira com inspect_report."
                                  + (" Corrija os problemas listados em issues." if repair.get("write-analysis-report") else ""),
                                  {"question": ws.manifest["request"]["question"], "decision_questions": self.plan.get("decision_questions"),
                                   "assumptions": ws.manifest["assumptions"], "limitations": self.plan.get("limitations"),
                                   "warnings": [w["message"] for w in ws.manifest["warnings"]][:30],
                                   "issues": repair.get("write-analysis-report", []),
                                   "previous_document": (prev_rep or {}).get("document")}, version)
                latest = ws.latest_deliverable("report")
                self.report_build = None
                if latest and latest["version"] == version:
                    from .tools.report import build_report
                    self.report_build = build_report(ws, latest["document"], version)  # reconstrução determinística para auditoria
            else:
                from .tools.report import build_report
                doc = heuristics.report_document(ws, results, self.roles, title, ws.manifest["request"]["question"])
                self.report_build = build_report(ws, doc, version)
        elif mode in ("report", "both") and prev_rep and version > 1:
            self._carry(prev_rep, version)

    def _carry(self, prev: dict, version: int) -> None:
        """Entrega sem correção neste ciclo: copia para a nova versão (mesmo conteúdo, mesmo hash)."""
        import shutil
        src = self.ws.path(prev["artifact_ref"])
        dst = self.ws.deliverable_dir(version) / src.name
        shutil.copy2(src, dst)
        extra = {k: v for k, v in prev.items() if k not in ("kind", "artifact_ref", "version", "sha256", "created_at")}
        self.ws.add_deliverable(prev["kind"], dst, version, {**extra, "carried_from": prev["version"]})

    def stage_review(self, version: int, cycle: int) -> dict:
        ws = self.ws
        self.log(f"11. Validação técnica e revisão de qualidade (ciclo {cycle})…")
        val = validate.validate(ws)["result"]
        det = review.deterministic_review(ws, val, self.report_build)
        issues = det["issues"]
        if self.provider:
            tenv = self._agent("technical-reviewer", "Audite os números desta análise além da auditoria automática.",
                               {"validation_summary": val["summary"], "validation_issues": val["issues"]})
            issues += [i for i in (tenv.get("result") or {}).get("issues", []) if isinstance(i, dict)]
            qenv = self._agent("quality-orchestrator", "Revise as entregas finais e decida a liberação. Problemas já encontrados "
                               "pelas verificações automáticas estão em known_issues; não os repita.",
                               {"cycle": cycle, "max_cycles": self.max_cycles, "output_mode": ws.manifest["request"]["output_mode"],
                                "question": ws.manifest["request"]["question"], "known_issues": issues}, version)
            issues += [i for i in (qenv.get("result") or {}).get("issues", []) if isinstance(i, dict)]
        for n, i in enumerate(issues, start=1):
            i["issue_id"] = f"c{cycle}_{n:03d}"
            i.setdefault("severity", "defect")
            i.setdefault("status", "open")
        defects = [i for i in issues if i.get("severity") == "defect"]
        decision = "approve" if not defects else ("revise" if cycle < self.max_cycles else "blocked")
        tasks: dict[str, list[dict]] = {}
        for i in defects:
            tasks.setdefault(i.get("target_skill", "unknown"), []).append(i)
        rec = {"cycle": cycle, "version": version, "decision": decision, "checks_performed": det["checks_performed"],
               "validation_decision": val["decision"], "issues": issues,
               "repair_tasks": [{"target_skill": k, "owner_agent": v[0].get("owner_agent"), "issue_ids": [i["issue_id"] for i in v],
                                 "acceptance_criteria": [i.get("acceptance_criteria") for i in v]} for k, v in tasks.items()]}
        ws.manifest["reviews"].append(rec)
        ws.save()
        ws.save_skill_output(envelope("orchestrate-quality-review", "completed", rec), f"cycle{cycle}")
        return rec

    def repair_upstream(self, tasks: dict[str, list[dict]]) -> None:
        """Correções que exigem refazer etapas anteriores às entregas (plano, cálculo, gráficos)."""
        if not self.provider:
            return
        if "plan-analysis" in tasks:
            env = self._agent("analysis-planner", "A revisão apontou problemas no plano. Acrescente as métricas que faltam e devolva o plano "
                              "completo atualizado.", {"issues": tasks["plan-analysis"], "previous_plan": self.plan})
            self.plan = env.get("result") or self.plan
            self.ws.write_json("results/plan.json", self.plan)
            self.stage_compute()
        if "describe-data" in tasks or "validate-analysis" in tasks:
            self._agent("data-analyst", "Corrija os cálculos apontados pela revisão.", {"issues": tasks.get("describe-data", []) + tasks.get("validate-analysis", [])})
        if "design-charts" in tasks or "plan-analysis" in tasks:
            self.stage_charts(self.ws.list_results())

    # ------------------------------------------------------------------ fluxo
    def run(self) -> dict:
        ws = self.ws
        ws.manifest["status"] = "running"
        ws.manifest["mode"] = "agents" if self.provider else "no_llm"
        ws.manifest["provider"] = {"name": getattr(self.provider, "name", None), "model": getattr(self.provider, "model", None)} if self.provider else None
        ws.save()
        if not self.stage_data():
            return self._finish("needs_clarification" if ws.manifest.get("pending_questions") else "blocked")
        self.stage_plan()
        self.stage_relate()
        results = self.stage_compute()
        self.stage_charts(results)
        version, cycle, repair = 1, 1, None
        while True:
            self.stage_deliverables(version, repair)
            rec = self.stage_review(version, cycle)
            if rec["decision"] in ("approve", "blocked"):
                break
            if not self.provider:
                rec["decision"] = "blocked"
                rec["note"] = "Sem provedor de IA, as correções não podem ser feitas automaticamente."
                ws.save()
                break
            repair = {}
            for i in rec["issues"]:
                if i.get("severity") == "defect":
                    repair.setdefault(i.get("target_skill", "unknown"), []).append(i)
            self.repair_upstream(repair)
            if any(k in repair for k in ("plan-analysis", "describe-data", "design-charts", "validate-analysis")):
                repair.setdefault("compose-dashboard", [])
                repair.setdefault("write-analysis-report", [])
            version += 1
            cycle += 1
        final = ws.manifest["reviews"][-1]
        status = "approved" if final["decision"] == "approve" else "not_approved"
        if status == "approved":
            ws.manifest["approved_artifacts"] = [{"artifact_ref": d["artifact_ref"], "sha256": d["sha256"]}
                                                 for d in ws.manifest["deliverables"] if d["version"] == final["version"]]
        return self._finish(status)

    def _finish(self, status: str) -> dict:
        ws = self.ws
        ws.manifest["status"] = status
        ws.manifest["finished_at"] = now_iso()
        ws.save()
        summary = write_execution_summary(ws)
        return {"analysis_id": ws.manifest["analysis_id"], "status": status, "folder": str(ws.root),
                "deliverables": [d for d in ws.manifest["deliverables"] if d["version"] == max((x["version"] for x in ws.manifest["deliverables"]), default=0)],
                "execution_summary": summary, "pending_questions": ws.manifest.get("pending_questions", [])}


def write_execution_summary(ws: Workspace) -> str:
    """Resumo da execução (RN-015): pedido, entregas, suposições, tratamentos, limitações e revisão. Sem interpretação."""
    m = ws.manifest
    req = m["request"]
    lines = [f"# Resumo da execução — {m['analysis_id']}", "",
             f"- **Pedido:** {req['question'] or 'exploração geral dos dados'}",
             f"- **Entregas pedidas:** {req['output_mode']}",
             f"- **Modo:** {'agentes com IA (' + str((m.get('provider') or {}).get('name')) + ' / ' + str((m.get('provider') or {}).get('model')) + ')' if m.get('mode') == 'agents' else 'sem IA (planejamento por regras)'}",
             f"- **Situação:** {({'approved': 'aprovada', 'not_approved': 'NÃO APROVADA', 'needs_clarification': 'aguardando esclarecimento', 'blocked': 'bloqueada'}).get(m['status'], m['status'])}",
             "", "## Arquivos recebidos", ""]
    lines += [f"- {f['original_name']} (origem: {f.get('source_label')}; sha256 {f['sha256'][:12]}…)" for f in m["files"]]
    latest = max((d["version"] for d in m["deliverables"]), default=None)
    lines += ["", "## Entregas", ""]
    lines += [f"- {d['artifact_ref']} (versão {d['version']}, sha256 {d['sha256'][:12]}…)" for d in m["deliverables"] if d["version"] == latest] or ["- nenhuma"]
    lines += ["", "## Esclarecimentos e suposições", ""]
    lines += [f"- Esclarecimento: {c['question']} → {c['answer']}" for c in req.get("clarifications", [])]
    lines += [f"- Suposição: {a.get('assumption') if isinstance(a, dict) else a}" for a in m.get("assumptions", [])]
    if m.get("pending_questions"):
        lines += [f"- **Pergunta pendente:** {q['question']} ({q.get('why_it_matters')})" for q in m["pending_questions"]]
    if not (req.get("clarifications") or m.get("assumptions") or m.get("pending_questions")):
        lines.append("- nenhuma")
    lines += ["", "## Tratamentos aplicados aos dados", ""]
    lines += [f"- {t['description']} ({t['kind']})" for t in m["treatments"]] or ["- nenhum"]
    lines += ["", "## Tabelas e ligações entre arquivos", ""]
    try:
        rmap = ws.read_json("results/relationship_map.json")
        for t in rmap["tables"]:
            lines.append(f"- {t['dataset_id']}: {t['role']} — {t.get('observation_unit') or ''} ({t['rows']} linhas)")
        for g in rmap.get("partitions", []):
            lines.append(f"- Partições empilhadas em {g.get('stacked_dataset_id')}: {', '.join(g['members'])}")
        for r in rmap["relations"]:
            if r["strength"] == "strong":
                lines.append(f"- Ligação {r['child']['dataset_id']}.{'+'.join(r['child']['key'])} → {r['parent']['dataset_id']}.{'+'.join(r['parent']['key'])}: "
                             f"{r['cardinality_label']}, correspondência {format_value(r['evidence']['containment'], 'percent_1')}, "
                             f"órfãos {format_value(r['integrity']['orphan_rows_pct'] or 0, 'percent_1')}")
    except FileNotFoundError:
        lines.append("- mapa não gerado")
    lines += ["", "## Limitações e avisos dos dados", ""]
    seen = set()
    for w in m.get("warnings", []):
        if w["message"] not in seen:
            seen.add(w["message"])
            lines.append(f"- {w['message']}")
    if not seen:
        lines.append("- nenhum")
    lines += ["", "## Revisão de qualidade", ""]
    for r in m.get("reviews", []):
        defects = [i for i in r["issues"] if i.get("severity") == "defect"]
        lines.append(f"- Ciclo {r['cycle']} (versão {r['version']}): decisão **{r['decision']}**, validação técnica {r['validation_decision']}, "
                     f"{len(defects)} defeito(s), {len(r['issues']) - len(defects)} sugestão(ões). Verificações: {', '.join(r['checks_performed'])}.")
    if m["status"] == "not_approved" and m.get("reviews"):
        lines += ["", "**Defeitos restantes (a entrega não foi aprovada):**", ""]
        lines += [f"- [{i['category']}] {i['artifact_ref']} — {i['location']}: {i['problem']}" for i in m["reviews"][-1]["issues"] if i.get("severity") == "defect"]
    usage = m.get("llm_usage", [])
    if usage:
        tin = sum(u.get("input_tokens", 0) for u in usage)
        tout = sum(u.get("output_tokens", 0) for u in usage)
        lines += ["", "## Custo de IA", "", f"- Tokens de entrada: {tin}; tokens de saída: {tout}; chamadas de agente: {len(usage)}."]
    text = "\n".join(lines) + "\n"
    ws.path("execution_summary.md").write_text(text, encoding="utf-8")
    return "execution_summary.md"


def run_analysis(files: list[str | Path], question: str | None = None, output_mode: str = "both", base_dir: str | Path = "analyses",
                 provider: LLMProvider | None = None, ask: AskFn | None = None, source_labels: dict[str, str] | None = None,
                 inline_library: str | None = None, analysis_id: str | None = None, log: Callable[[str], None] = print) -> dict:
    if output_mode not in ("report", "dashboard", "both"):
        raise ValueError("output_mode deve ser report, dashboard ou both")
    ws = Workspace.create(base_dir, files, question, output_mode, analysis_id, source_labels)
    return Orchestrator(ws, provider, ask, inline_library, log=log).run()
