---
name: plan-analysis
description: Interpreta o pedido do usuário no DataAI (pergunta específica ou exploração geral), confronta com o perfil dos dados e produz o plano de análise com métricas, recortes, relações necessárias, gráficos previstos e entregas (PDF, HTML ou ambos). Use depois de profile-data e antes de qualquer cálculo.
metadata:
  project: DataAI
  agent: analysis-planner
  spec: specs.md v1.3 (RF-004, RF-005, RF-008, RF-022, RN-001, RN-002, RN-007, RN-014, RN-016, 12.7, 12.8.4, P-005, P-010)
---

# plan-analysis

Transforma a intenção do usuário em um plano verificável. Nenhum número é calculado aqui.

## Entrada

- Pedido do usuário em linguagem natural e esclarecimentos já recebidos.
- Entregas pedidas: `report`, `dashboard` ou `both`.
- Saídas de `ingest-tabular` e `profile-data`.

## Ferramentas

`list_datasets`, `get_profile` (inclui `applicable_families`), `get_relationship_map`, `preview_rows`, `list_metric_functions`. Você não calcula nada: suas métricas são especificações que `describe-data` executa com `compute_metric`.

## Procedimento

1. **Classifique o modo de análise:**
   - `directed`: há uma pergunta específica. O plano deve responder a ela (CA-004).
   - `exploratory`: o usuário pediu varredura ou insights sem pergunta. **Aceite o pedido**; ausência de pergunta não é motivo para recusar (RN-002).
2. **Defina a entrega.** Se o usuário não disse, use `both` e registre a suposição. No MVP: no máximo um PDF e um HTML por solicitação; o HTML pode ter mais de uma visão [proposta MVP, P-010].
3. **Liste as métricas.** Para cada uma, registre:
   - `metric_id`, nome em linguagem do usuário, fórmula, unidade, população (quais linhas entram), filtros, denominador (para taxas) e datasets/colunas de origem.
   - Use só colunas que existem e com o tipo semântico adequado (nunca média de `identifier`).
   - Escolha métricas do **domínio dos dados** (RN-001). Ticket médio não é obrigatório em dados educacionais.
   - Escreva cada métrica já como especificação executável (`function`, `dataset_id`, `params`, `filters`), no formato de `describe-data`, usando só funções de `list_metric_functions` e famílias marcadas como aplicáveis no perfil.
   - **Abrangência (RN-016):** não se limite a posição e dispersão. Cubra as perguntas de decisão de specs 12.7.2 que os dados permitem: onde está o volume (M5, M6), para onde vai (M7), em relação a quê (M8, M9), o que explica a variação (M10), quem são as entidades (M11), prazos (M12), o que varia junto (M13) e se as fontes concordam (M14). Qualidade (M1) sempre entra, e a métrica principal recebe sensibilidade (M15).
   - **Referência:** todo achado principal precisa de uma comparação (período anterior, média geral, outro grupo ou meta). Planeje a métrica de referência junto com a principal. Meta só vale se existir nos dados ou for informada (P-019).
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
6. **Relações:** leia `get_relationship_map`. Partições já vêm empilhadas. Escolha só as ligações fortes (ou prováveis confirmadas) que a análise exige e indique-as em `relations_needed` com `left_id`, `right_id`, `left_on`, `right_on` e `derived_id`. Respeite as armadilhas do mapa: em *fan-out* e grão diferente, peça `aggregate_right`. Nas especificações de métrica sobre o dataset juntado, as colunas da direita mantêm o nome original; em conflito recebem o sufixo `__<right_id>`; a chave da direita é descartada. Arquivos enviados juntos não precisam ser combinados se a análise não pede (RN-003). Duas fontes com a mesma medida pedem reconciliação (M14), não escolha de fonte (P-020).
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
      "sources": [ { "dataset_id": "ds_matriculas", "columns": ["situacao", "ano_curso"] } ],
      "decision_question": "Em relação a quê?",
      "spec": {
        "metric_id": "m_evasao_1ano", "label": "Taxa de evasão no 1º ano", "function": "rate", "dataset_id": "ds_matriculas_cursos",
        "params": { "numerator": { "filter": [ { "column": "situacao", "op": "==", "value": "evadido" } ] }, "denominator": { "filter": [] }, "group_by": ["nome_curso"] },
        "filters": [ { "column": "ano_curso", "op": "==", "value": 1 } ], "unit": "%", "formula": "evadidos / matriculados no 1º ano",
        "population": "matrículas com ano_curso = 1"
      }
    }
  ],
  "analyses": [
    { "analysis_item_id": "a1", "description": "evasão por curso", "metrics": ["m_evasao_1ano"], "group_by": ["curso"], "charts": [ { "type": "bar_horizontal", "targets": ["report", "dashboard"] } ] }
  ],
  "relations_needed": [ { "left_id": "ds_matriculas", "right_id": "ds_cursos", "left_on": ["curso_id"], "right_on": ["curso_id"], "how": "left", "derived_id": "ds_matriculas_cursos", "reason": "nome do curso" } ],
  "treatments": [ { "description": "excluir matrículas de teste", "requires_authorization": true } ],
  "assumptions": [ "Considerado todo o período disponível (2021 a 2024)." ],
  "limitations": [ "Não há data de evasão, só a situação final." ]
}
```

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] O modo de análise está classificado e, se `directed`, cada análise contribui para a pergunta.
- [ ] Toda métrica tem fórmula, unidade, população, origem e especificação executável.
- [ ] O plano cobre pelo menos duas perguntas de decisão além de "quanto" quando os dados permitem (RN-016), e cada achado esperado tem referência.
- [ ] Nenhuma métrica depende de colunas inexistentes ou de identificadores somados.
- [ ] Suposições e limitações estão registradas.
