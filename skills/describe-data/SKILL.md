---
name: describe-data
description: Calcula com código as métricas, estatísticas descritivas, agregações e séries temporais definidas no plano de uma análise do DataAI, registrando fórmula, população e origem de cada número. Use depois de plan-analysis (e de relate-datasets, quando houver junções) e antes de gráficos e entregas.
metadata:
  project: DataAI
  agent: data-analyst
  spec: specs.md v1.2 (RF-006, RF-018, RF-019, 12.4, P-016)
---

# describe-data

Produz todos os números da análise. Gráficos, relatório e dashboard só podem usar números que saem daqui.

## Entrada

- Plano de `plan-analysis` (métricas e análises).
- Datasets em `working/` e regras de agregação de `relate-datasets`.

## Convenções estatísticas [proposta MVP, P-016]

| Item | Convenção |
|---|---|
| Desvio-padrão | amostral, `ddof=1` |
| Quantis | método linear (`numpy`/`pandas` padrão `linear`) |
| Intervalo interquartil | Q3 − Q1 |
| Valores extremos | sinalizados fora de Q1 − 1,5·IQR e Q3 + 1,5·IQR; nunca removidos automaticamente |
| Ausentes | excluídos do cálculo da métrica, com a contagem de excluídos registrada |
| Precisão | precisão total no armazenamento; arredondamento só na apresentação |
| Percentuais | guardados como fração (0,153); a apresentação converte para 15,3% |

## Procedimento

1. **Calcule com pandas**, nunca de cabeça. Para cada análise do plano:
   - aplique população e filtros da métrica;
   - agrupe conforme `group_by`;
   - calcule o que for pertinente ao tipo: contagens, distintos, soma, média, mediana, mínimo, máximo, quartis, IQR, desvio-padrão, frequências absolutas e relativas, participação no total, variação entre períodos.
2. **Respeite os tipos semânticos:** `identifier` só em contagens; `category` em frequências; `measure` em estatísticas numéricas.
3. **Respeite as regras de agregação** de `relate-datasets` (por exemplo, somar medida do pai por chave distinta).
4. **Taxas:** registre numerador e denominador separados. Divisão por zero resulta em ausente com aviso `division_by_zero`, nunca em zero.
5. **Séries temporais:** declare a granularidade (dia, semana, mês). Períodos incompletos no início ou fim da série são marcados com `partial_period: true`.
6. **Grupos pequenos:** médias e taxas de grupos com menos de 30 observações recebem `small_sample: true`, para o relatório não tirar conclusão forte delas.
7. **Totais de controle:** para cada resultado agrupado, confira que a soma dos grupos bate com o total geral (quando a métrica é aditiva).
8. Salve cada resultado em `results/<result_id>.json` com os dados e os metadados abaixo. Se um resultado for recalculado em correção, salve uma nova versão do mesmo `result_id`.

## Regras

- Não atribua causa, não calcule p-valor, não faça previsão (MVP descritivo).
- Associação descritiva (por exemplo, correlação de Pearson ou Spearman) pode ser calculada quando o plano pedir, sempre com o tamanho da amostra e sem linguagem causal.
- Se um cálculo não puder ser feito como planejado (coluna com muitos ausentes, população vazia), devolva o motivo; não troque a métrica em silêncio.

## Resultado

```json
{
  "results": [
    {
      "result_id": "res_evasao_por_curso",
      "version": 1,
      "metric_id": "m_evasao_1ano",
      "analysis_item_id": "a1",
      "path": "results/res_evasao_por_curso.json",
      "group_by": ["curso"],
      "rows": 12,
      "population_rows": 4830,
      "excluded_missing": 17,
      "flags": { "small_sample_groups": ["Música"], "partial_periods": [] },
      "control_total": { "expected": 4830, "obtained": 4830, "ok": true },
      "code_ref": "review/code/res_evasao_por_curso.py"
    }
  ]
}
```

Guarde o código usado em cada cálculo (`code_ref`) para a auditoria de `validate-analysis`.

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Todo número veio de código salvo e reexecutável.
- [ ] Toda taxa tem numerador e denominador.
- [ ] Totais de controle conferidos.
- [ ] Grupos pequenos e períodos parciais sinalizados.
