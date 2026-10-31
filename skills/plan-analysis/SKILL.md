---
name: plan-analysis
description: Interpreta o pedido do usuário no DataAI (pergunta específica ou exploração geral), confronta com o perfil dos dados e produz o plano de análise com métricas, recortes, relações necessárias, gráficos previstos e entregas (PDF, HTML ou ambos). Use depois de profile-data e antes de qualquer cálculo.
metadata:
  project: DataAI
  agent: analysis-planner
  spec: specs.md v1.2 (RF-004, RF-005, RF-008, RN-001, RN-002, RN-007, RN-014, P-005, P-010)
---

# plan-analysis

Transforma a intenção do usuário em um plano verificável. Nenhum número é calculado aqui.

## Entrada

- Pedido do usuário em linguagem natural e esclarecimentos já recebidos.
- Entregas pedidas: `report`, `dashboard` ou `both`.
- Saídas de `ingest-tabular` e `profile-data`.

## Procedimento

1. **Classifique o modo de análise:**
   - `directed`: há uma pergunta específica. O plano deve responder a ela (CA-004).
   - `exploratory`: o usuário pediu varredura ou insights sem pergunta. **Aceite o pedido**; ausência de pergunta não é motivo para recusar (RN-002).
2. **Defina a entrega.** Se o usuário não disse, use `both` e registre a suposição. No MVP: no máximo um PDF e um HTML por solicitação; o HTML pode ter mais de uma visão [proposta MVP, P-010].
3. **Liste as métricas.** Para cada uma, registre:
   - `metric_id`, nome em linguagem do usuário, fórmula, unidade, população (quais linhas entram), filtros, denominador (para taxas) e datasets/colunas de origem.
   - Use só colunas que existem e com o tipo semântico adequado (nunca média de `identifier`).
   - Escolha métricas do **domínio dos dados** (RN-001). Ticket médio não é obrigatório em dados educacionais.
4. **Modo `directed`:** derive as métricas e recortes que respondem à pergunta. Se a pergunta não puder ser respondida com os dados (falta coluna, falta período), diga isso no plano e proponha o que é possível.
5. **Modo `exploratory`:** monte uma varredura proporcional aos dados, cobrindo o que fizer sentido entre:
   - distribuição das principais medidas;
   - composição por categorias relevantes;
   - evolução no tempo, se houver datas;
   - diferenças entre grupos;
   - concentração (poucos itens respondem por muito do total);
   - extremos, ausências e inconsistências relevantes;
   - associações descritivas entre variáveis compatíveis.

   Não execute uma lista fixa para todo arquivo. Priorize de 5 a 12 análises com maior chance de achado relevante.
6. **Relações:** indique quando a análise precisa combinar datasets e quais chaves parecem envolvidas. A verificação fica com `relate-datasets`. Arquivos enviados juntos não precisam ser combinados se a análise não pede (RN-003).
7. **Gráficos previstos:** para cada análise, sugira o tipo de visual e se vai para o relatório, o dashboard ou ambos. O detalhamento é de `design-charts`.
8. **Perguntas ao usuário:** só quando a ambiguidade puder mudar materialmente a resposta (P-005). Exemplos: qual coluna é "a receita" quando há duas candidatas; qual período considerar quando há dados de anos incompletos. Para o resto, adote uma suposição razoável e registre em `assumptions`, que vai para o resumo da execução.

## Regras

- Não reutilize métricas, filtros, moeda ou período de análises anteriores (RN-014).
- Não planeje previsão, teste de hipótese ou inferência causal; estão fora do MVP (P-014).
- Planejar um tratamento não é executá-lo. Tratamentos que excluem, imputam ou consolidam dados entram como `requires_authorization: true`.

## Resultado

```json
{
  "analysis_mode": "directed",
  "question": "Quais cursos têm maior evasão no primeiro ano?",
  "output_mode": "both",
  "metrics": [
    {
      "metric_id": "m_evasao_1ano",
      "label": "Taxa de evasão no 1º ano",
      "formula": "alunos com situação 'evadido' e ano_curso = 1 / alunos com ano_curso = 1",
      "unit": "%",
      "population": "matrículas com ano_curso = 1",
      "filters": [],
      "denominator": "alunos com ano_curso = 1",
      "sources": [ { "dataset_id": "ds_matriculas", "columns": ["situacao", "ano_curso"] } ]
    }
  ],
  "analyses": [
    { "analysis_item_id": "a1", "description": "evasão por curso", "metrics": ["m_evasao_1ano"], "group_by": ["curso"], "charts": [ { "type": "bar_horizontal", "targets": ["report", "dashboard"] } ] }
  ],
  "relations_needed": [ { "from": "ds_matriculas.curso_id", "to": "ds_cursos.curso_id", "reason": "nome do curso" } ],
  "treatments": [ { "description": "excluir matrículas de teste", "requires_authorization": true } ],
  "assumptions": [ "Considerado todo o período disponível (2021 a 2024)." ],
  "limitations": [ "Não há data de evasão, só a situação final." ]
}
```

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] O modo de análise está classificado e, se `directed`, cada análise contribui para a pergunta.
- [ ] Toda métrica tem fórmula, unidade, população e origem.
- [ ] Nenhuma métrica depende de colunas inexistentes ou de identificadores somados.
- [ ] Suposições e limitações estão registradas.
