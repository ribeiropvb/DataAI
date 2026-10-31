"""Fluxo completo: modo sem IA e modo com agentes (provedor roteirizado, sem rede)."""
import json

import pytest

from conftest import ECHARTS, browser_available
from dataai.llm.base import LLMResponse, ToolCall

needs_render = pytest.mark.skipif(not (browser_available() and ECHARTS),
                                  reason="exige navegador headless e DATAAI_ECHARTS_JS (ECharts local)")


@needs_render
def test_no_llm_end_to_end(tmp_path, demo_dir):
    from dataai.orchestrator import run_analysis
    out = run_analysis(sorted(demo_dir.iterdir()), None, "both", tmp_path, None, inline_library=ECHARTS, log=lambda *_: None)
    assert out["status"] == "approved", (tmp_path / out["analysis_id"] / "execution_summary.md").read_text()
    kinds = {d["kind"] for d in out["deliverables"]}
    assert kinds == {"report", "dashboard"}
    m = json.loads((tmp_path / out["analysis_id"] / "manifest.json").read_text())
    fams = {json.loads((tmp_path / out["analysis_id"] / "results" / f"{r}.json").read_text())["family"] for r in m["results"]}
    assert len(fams) >= 10  # RN-016: muito além de posição e dispersão
    summary = (tmp_path / out["analysis_id"] / "execution_summary.md").read_text()
    assert "Partições empilhadas" in summary and "órfãos" in summary


def _fake_agents():
    """Responde como cada agente, chamando ferramentas reais (exercita o ciclo de agentes)."""
    from dataai import heuristics
    state = {}

    def respond(system, messages, tools):
        agent = system.split("(`", 1)[1].split("`", 1)[0]
        last = messages[-1]
        tool_round = last["role"] == "tool"
        env = lambda result: LLMResponse(text=json.dumps({"skill_name": agent, "status": "completed", "result": result,
                                                          "warnings": [], "questions": [], "evidence_refs": []}))
        ws = state["ws"]
        if agent == "analysis-planner":
            main = heuristics.choose_main_table(ws)
            joins = heuristics.plan_joins(ws, main)
            return env({"analysis_mode": "exploratory", "output_mode": "both", "joins": joins, "metrics": [], "_main": main,
                        "decision_questions": ["Onde está o volume?"]})
        if agent == "data-analyst" and not tool_round:
            return env({"results": [], "failed": []})
        if agent == "visualization-specialist":
            if not tool_round:
                return LLMResponse(tool_calls=[ToolCall("t1", "list_results", {})])
            heuristics.suggest_all_charts(ws, ws.list_results())
            return env({"charts": sorted(ws.manifest["charts"])})
        if agent == "interface-designer":
            if not tool_round:
                cfg = heuristics.dashboard_config(ws, {r: ws.load_result(r) for r in ws.list_results()}, state["roles"], "Teste")
                return LLMResponse(tool_calls=[ToolCall("t1", "build_dashboard", {"config": cfg})])
            return env({"stage": "artifact"})
        if agent == "report-writer":
            if not tool_round:
                doc = heuristics.report_document(ws, {r: ws.load_result(r) for r in ws.list_results()}, state["roles"], "Teste", None)
                return LLMResponse(tool_calls=[ToolCall("t1", "build_report", {"document": doc})])
            return env({"stage": "artifact"})
        if agent == "quality-orchestrator":
            return env({"decision": "approve", "issues": []})
        return env({})
    return respond, state


@needs_render
def test_agents_pipeline_with_scripted_provider(tmp_path, demo_dir, monkeypatch):
    from dataai import heuristics
    from dataai.llm.scripted import ScriptedProvider
    from dataai.orchestrator import Orchestrator
    from dataai.workspace import Workspace

    respond, state = _fake_agents()
    ws = Workspace.create(tmp_path, sorted(demo_dir.iterdir()), None, "both", "agents")
    state["ws"] = ws
    orch = Orchestrator(ws, ScriptedProvider(respond), inline_library=ECHARTS, log=lambda *_: None)
    real_relate = orch.stage_relate

    def relate_then_metrics():
        real_relate()  # executa as junções do plano
        main = orch.plan["_main"]
        ds = orch.plan["joins"][-1]["derived_id"] if orch.plan["joins"] else main
        orch.plan["metrics"], state["roles"] = heuristics.plan_metrics(ws, main, ds)
    monkeypatch.setattr(orch, "stage_relate", relate_then_metrics)
    out = orch.run()
    assert out["status"] == "approved", (ws.root / "execution_summary.md").read_text()
    agents = {u["agent"] for u in ws.manifest["llm_usage"]}
    assert {"data-specialist", "analysis-planner", "visualization-specialist", "interface-designer", "report-writer",
            "technical-reviewer", "quality-orchestrator"} <= agents


def test_runner_rejects_tool_not_in_profile(tmp_path, demo_dir):
    from dataai.agents.profiles import load_profiles
    from dataai.agents.runner import AgentRunner
    from dataai.agents.toolbox import Toolbox
    from dataai.llm.scripted import ScriptedProvider
    from dataai.workspace import Workspace
    ws = Workspace.create(tmp_path, [sorted(demo_dir.iterdir())[0]], None, "both", "r")
    prof = load_profiles()["visualization-specialist"]
    final = json.dumps({"skill_name": "design-charts", "status": "completed", "result": {}, "warnings": [], "questions": [], "evidence_refs": []})
    prov = ScriptedProvider([LLMResponse(tool_calls=[ToolCall("1", "build_report", {"document": {}})]), LLMResponse(text=final)])
    env = AgentRunner(prof, prov, Toolbox(ws)).run("teste")
    assert env["status"] == "completed"
    tool_msg = [m for m in prov.calls[-1]["messages"] if m["role"] == "tool"][0]
    assert "não permitida" in tool_msg["content"]


def test_profiles_reference_existing_skills_and_tools(tmp_path):
    from dataai.agents.profiles import SKILLS_DIR, load_profiles
    from dataai.agents.toolbox import Toolbox
    from dataai.workspace import Workspace
    profs = load_profiles()
    assert len(profs) == 8
    tb = Toolbox(Workspace(tmp_path))
    for p in profs.values():
        for s in p.skills:
            assert (SKILLS_DIR / s / "SKILL.md").exists(), s
        tb.specs(p.tools)
        assert "Formato da resposta final" in p.system_prompt()
