---
name: describe-data
description: Calcula com as ferramentas do DataAI as métricas do plano (catálogo M1–M15: qualidade, volume, posição, dispersão, composição, concentração, tempo, referência, taxas, decomposição, entidades, prazos, associação, reconciliação entre fontes e sensibilidade), registrando fórmula, população e origem de cada número. Use depois de plan-analysis (e de relate-datasets, quando houver junções) e antes de gráficos e entregas.
metadata:
  project: DataAI
  agent: data-analyst
  spec: specs.md v1.3 (RF-006, RF-018, RF-019, RF-022, RN-016, 12.7, P-016)
---

# describe-data

Produz todos os números da análise. Gráficos, relatório e dashboard só podem usar números que saem daqui. Você nunca calcula de cabeça: toda métrica é uma chamada a `compute_metric`, que executa pandas, salva o resultado e guarda a especificação para ser reexecutada na auditoria.

## Ferramentas

| Ferramenta | Uso |
|---|---|
| `list_metric_functions` | Catálogo de funções com família e parâmetros. |
| `list_datasets`, `get_profile` | Colunas, tipos semânticos, chaves e famílias aplicáveis. |
| `compute_metric` | Calcula e salva uma métrica (`results/<result_id>.json`, com versão). |
| `get_result`, `list_results` | Lê resultados já salvos. |

Código: `dataai/tools/metrics.py` (`compute`, `CATALOG`).

## Especificação de uma métrica

```json
{
  "metric_id": "res_receita_mes",
  "label": "Receita mensal",
  "function": "time_series",
  "dataset_id": "ds_vendas",
  "params": { "date_col": "data_venda", "measure": "valor_total", "agg": "sum", "freq": "M" },
  "filters": [ { "column": "status", "op": "!=", "value": "cancelada" } ],
  "unit": "R$",
  "formula": "soma de valor_total por mês",
  "population": "vendas não canceladas"
}
```

- `metric_id` vira o `result_id` e é usado nos marcadores do relatório.
- Funções de reconciliação (M14) recebem também `dataset_id_b`.
- Operadores de filtro: `== != > >= < <= in not_in is_null not_null contains between` (texto sem diferenciar maiúsculas).
- A ferramenta recusa colunas inexistentes e agregação numérica de `identifier`. O erro volta para você corrigir a especificação, nunca para trocar a métrica em silêncio.

## Catálogo (specs 12.7)

| Família | Pergunta de decisão | Funções |
|---|---|---|
| M1 Qualidade | Posso confiar? | `quality_completeness`, `quality_uniqueness`, `quality_validity`, `quality_consistency`, `quality_temporal_coverage` |
| M2 Volume | Quanto? | `volume_counts` |
| M3 Posição | Quão típico? | `position_stats` |
| M4 Dispersão e forma | Quão variável? Há extremos? | `dispersion_shape` |
| M5 Composição | Onde está o volume? | `frequency_table`, `share_of_total`, `crosstab` |
| M6 Concentração | Poucos respondem por muito? | `concentration` (top N, Gini, HHI), `pareto_abc` |
| M7 Tempo | Para onde está indo? | `time_series`, `period_change`, `trend_summary`, `seasonal_profile` |
| M8 Referência | Em relação a quê? | `group_comparison`, `compare_to_reference` (meta, P-019) |
| M9 Taxas e funis | Qual a proporção? | `rate`, `funnel`, `simpson_check` |
| M10 Decomposição | O que explica a variação? | `contribution_to_change`, `mix_rate_decomposition` |
| M11 Entidades | Quem são e como se comportam? | `entity_rfm`, `cohort_retention`, `new_vs_returning` |
| M12 Prazos | Os prazos são cumpridos? | `durations`, `deadline_compliance` |
| M13 Associação | O que varia junto? | `association` (Pearson, Spearman, V de Cramér, eta) |
| M14 Fontes | As fontes concordam? | `source_coverage`, `reconcile_measure`, `attribute_divergence` |
| M15 Sensibilidade | O resultado é robusto? | `sensitivity` |

## Procedimento

1. Leia o plano e confira, em `get_profile`, que cada métrica é aplicável (`applicable_families`).
2. Calcule cada métrica do plano com `compute_metric`. Use a granularidade, filtros e população do plano.
3. Para a métrica principal, calcule também `sensitivity` (M15). Se `sensitive: true`, isso vai para o relatório.
4. Taxas: use `rate`, que guarda numerador e denominador. Quando houver estratos, rode `simpson_check`; um aviso de Simpson é obrigatório no relatório.
5. Variação entre períodos: complemente `period_change` com `contribution_to_change` ou `mix_rate_decomposition` para dizer de onde vem a mudança.
6. Mesma medida em duas fontes: rode `reconcile_measure` ou `attribute_divergence`; não escolha uma fonte como oficial (P-020).
7. Leia `flags` e `warnings` de cada resultado (`small_sample`, `partial_period`, `division_by_zero`, `sensitive`, `simpson`) e repasse no resultado da skill.
8. Se um cálculo falhar, corrija a especificação. Se for impossível como planejado, devolva o motivo.

## Convenções (specs 12.7.5)

- Desvio-padrão amostral (`ddof=1`); quantis lineares; percentuais guardados como fração; precisão total, arredondamento só na apresentação.
- Ausentes são excluídos e contados; divisão por zero gera ausente com aviso, nunca zero.
- Grupos com n < 30 recebem `small_sample`; períodos incompletos, `partial_period`.
- Extremos são sinalizados (1,5·IQR e z robusto > 3,5), nunca removidos.
- Sem p-valor, previsão ou causa (P-014). Associação usa linguagem descritiva: |r| < 0,3 fraca, 0,3 a 0,5 moderada, ≥ 0,5 forte.

## Resultado

```json
{
  "results": [
    { "result_id": "res_receita_mes", "family": "M7", "function": "time_series", "n": 3373, "excluded": 0,
      "flags": { "partial_period": ["2025-03"] }, "warnings": [] }
  ],
  "decision_questions_covered": ["Para onde está indo?", "Onde está o volume?", "Posso confiar?"],
  "failed": []
}
```

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Todo número veio de `compute_metric` (reexecutável).
- [ ] Toda taxa tem numerador e denominador.
- [ ] A métrica principal tem sensibilidade calculada.
- [ ] O conjunto cobre pelo menos duas perguntas de decisão além de "quanto" (RN-016), quando os dados permitem.
- [ ] Avisos e sinais de cada resultado foram repassados.
