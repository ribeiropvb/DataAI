"""Linha de comando do DataAI.

    python -m dataai analisar dados/*.csv dados/cadastro.xlsx --pergunta "..." --entrega both
    python -m dataai analisar dados/* --no-llm            # sem IA, para testar ferramentas e entregas
    python -m dataai catalogo                             # lista as métricas disponíveis (M1–M15)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ask_terminal(questions: list[dict]) -> dict[str, str]:
    answers = {}
    for q in questions:
        print(f"\nPergunta: {q['question']}\n  Por que importa: {q.get('why_it_matters')}")
        for i, o in enumerate(q.get("options") or [], start=1):
            print(f"  {i}. {o}")
        default = q.get("default_if_unanswered")
        raw = input(f"Resposta{f' [{default}]' if default else ''}: ").strip()
        if raw.isdigit() and q.get("options") and 1 <= int(raw) <= len(q["options"]):
            raw = q["options"][int(raw) - 1]
        if raw:
            answers[q["question_id"]] = raw
    return answers


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dataai", description="DataAI: análise de dados com agentes de IA.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analisar", help="executa uma análise completa")
    a.add_argument("arquivos", nargs="+", help="arquivos CSV ou .xlsx")
    a.add_argument("--pergunta", default=None, help="pergunta em linguagem natural (omitir = exploração geral)")
    a.add_argument("--entrega", default="both", choices=["report", "dashboard", "both"])
    a.add_argument("--pasta", default="analyses", help="pasta onde as análises são guardadas")
    a.add_argument("--origem", action="append", default=[], metavar="ARQUIVO=ROTULO",
                   help="origem de um arquivo (sistema ou fonte), ex.: vendas.csv=ERP")
    a.add_argument("--no-llm", action="store_true", help="executa sem IA (planejamento por regras)")
    a.add_argument("--interativo", action="store_true", help="faz as perguntas de esclarecimento no terminal")
    a.add_argument("--echarts-local", default=None, help="caminho de echarts.min.js para embutir no HTML (uso offline)")
    sub.add_parser("catalogo", help="lista as funções de métrica")
    args = ap.parse_args(argv)

    if args.cmd == "catalogo":
        from .tools.metrics import catalog_summary
        for m in catalog_summary():
            print(f"{m['family']:>4}  {m['function']:<26} {m['label']}  ({', '.join(m['params'])})")
        return 0

    provider = None
    if not args.no_llm:
        from .llm.base import ProviderConfigError, get_provider
        try:
            provider = get_provider()
        except ProviderConfigError as e:
            print(f"Erro: {e}", file=sys.stderr)
            return 2
    labels = dict(o.split("=", 1) for o in args.origem if "=" in o)
    from .orchestrator import run_analysis
    out = run_analysis([Path(f) for f in args.arquivos], args.pergunta, args.entrega, args.pasta, provider,
                       _ask_terminal if args.interativo else None, labels, args.echarts_local)
    print(json.dumps({k: out[k] for k in ("analysis_id", "status", "folder", "execution_summary")}, ensure_ascii=False, indent=2))
    for d in out["deliverables"]:
        print(f"  entrega: {Path(out['folder']) / d['artifact_ref']}")
    return 0 if out["status"] in ("approved", "not_approved") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
