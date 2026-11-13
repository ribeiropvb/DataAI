---
name: validate-analysis
description: Audita tecnicamente uma análise do DataAI, reexecutando cálculos, conferindo relações, totais de controle, unidades, contratos das skills e a consistência entre resultados, relatório PDF e dashboard HTML. Use depois que as entregas forem geradas e antes da revisão final de qualidade.
metadata:
  project: DataAI
  agent: technical-reviewer
  spec: specs.md v1.3 (RF-013, RN-009, RN-010, 9.3, 12.3, 12.4, 12.7.5, 12.8)
---

# validate-analysis

Responde à pergunta: **os números estão certos e são os mesmos em todo lugar?** Não avalia storytelling nem estética; isso é de `orchestrate-quality-review`.

## Ferramentas

> **Fora do orquestrador do DataAI** (por exemplo, num harness como Claude Code ou Codex), chame cada ferramenta citada nesta skill pelo terminal: `python -m dataai ferramenta <pasta_da_analise> <nome> '<json dos argumentos>'` (ou `@arquivo.json`). A saída é JSON. O passo a passo completo está em `CLAUDE.md`.

`run_validation` (`dataai/tools/validate.py`), que executa as verificações abaixo de forma determinística e devolve `decision`, `checks` e `issues`. O agente `technical-reviewer` interpreta o resultado e pode conferir pontos com `get_result`, `list_results`, `inspect_report` e `inspect_dashboard`. A ferramenta verifica:

- envelopes das skills e perguntas sem resposta nem suposição;
- hash dos arquivos originais, tratamentos sem autorização, totais de controle das junções e linhas dos empilhamentos;
- **reexecução** de toda métrica pela especificação salva, comparando valores e linhas;
- taxas com numerador maior que o denominador;
- cada `number_ref` do PDF contra o resultado atual (valor formatado e versão) e presença no texto extraído;
- KPIs e dados dos gráficos embutidos no HTML contra os resultados atuais;
- mesmo indicador no PDF e no HTML.

## Entrada

- Pasta da análise: manifesto, `working/`, `results/`, `charts/`, `deliverables/v<N>/`.
- Saídas de todas as skills anteriores.

## Verificações

### 1. Contratos

- Toda saída de skill tem o envelope completo (`skill_name`, `status`, `result`, `warnings`, `questions`, `evidence_refs`).
- Nenhuma skill ficou com `needs_clarification` sem resposta registrada.
- Entregas com `stage: "artifact"`, não `specification` ou `draft`.

### 2. Dados e tratamentos

- Hash dos originais igual ao registrado na ingestão.
- Todo tratamento do manifesto foi de fato executado (o dataset derivado existe) e os que exigiam autorização têm a autorização registrada.
- Nenhuma linha descartada sem contagem.

### 3. Relações

- Totais de controle de `relate-datasets` conferem.
- Medidas da tabela pai em 1:N não foram somadas repetidas: reexecute pelo menos uma agregação com e sem deduplicação e compare.

### 4. Cálculos

- **Reexecute** o código (`code_ref`) de cada resultado e compare com o salvo. Tolerância: 1e-9 relativo.
- Escolha pelo menos três resultados e recalcule por um caminho independente (outra forma de agrupar ou filtrar).
- Taxas: numerador ≤ denominador quando aplicável; denominador correto para a população declarada.
- Sem média ou soma de `identifier`.
- Unidades coerentes entre métrica, resultado e gráfico.
- Divisões por zero tratadas como ausente.

### 5. Consistência entre entregas

- Todo número em `number_refs` do relatório bate com o `result_id` indicado, depois do arredondamento.
- Extraia os dados embutidos no `dashboard.html` e compare com `results/`.
- O mesmo indicador tem o mesmo valor no PDF e no HTML.
- Os gráficos usam os `result_id` declarados.

### 6. Formatos

- `report.pdf` é um PDF válido (abre, tem páginas) e `dashboard.html` é HTML válido (abre no navegador).

## Decisão

| `result.decision` | Quando |
|---|---|
| `pass` | Nenhum problema. |
| `pass_with_warnings` | Só problemas que não alteram números nem conclusões (por exemplo, arredondamento inconsistente na terceira casa). |
| `fail` | Algum número errado, divergente entre entregas, relação mal feita ou tratamento não autorizado. |
| `blocked` | Não foi possível verificar (arquivo ausente, código não reexecutável, ferramenta faltando). |

Concluir a auditoria com `fail` é um resultado válido: `status: "completed"` e `decision: "fail"` não se contradizem.

## Resultado

```json
{
  "decision": "fail",
  "checks": [
    { "check_id": "calc_rerun", "target": "res_evasao_por_curso", "ok": true },
    { "check_id": "pdf_vs_results", "target": "deliverables/v1/report.pdf", "ok": false, "detail": "p.3 cita 35,8%; resultado é 35,2%" }
  ],
  "issues": [
    {
      "issue_id": "iss_001",
      "category": "numeric_mismatch",
      "severity": "defect",
      "artifact_ref": "deliverables/v1/report.pdf",
      "location": "página 3, segundo parágrafo",
      "evidence_refs": ["results/res_evasao_por_curso.json"],
      "problem": "Taxa de Engenharia citada como 35,8%; resultado calculado é 35,2%.",
      "owner_agent": "report-writer",
      "target_skill": "write-analysis-report"
    }
  ]
}
```

Os `issues` usam o mesmo formato de `orchestrate-quality-review`, que os recebe e encaminha.

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Todos os resultados foram reexecutados.
- [ ] PDF e HTML conferidos contra `results/`.
- [ ] Cada problema tem localização, evidência e responsável.
