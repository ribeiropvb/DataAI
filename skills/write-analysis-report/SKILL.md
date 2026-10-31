---
name: write-analysis-report
description: Produz o relatório PDF real de uma análise do DataAI, com objetivo, achados, gráficos, interpretação proporcional às evidências, limitações e encadeamento analítico (storytelling), usando somente números já calculados. Use quando a entrega pedida incluir relatório, ou para corrigir um relatório apontado pela revisão.
metadata:
  project: DataAI
  agent: report-writer
  spec: specs.md v1.3 (RF-009, RN-004, RN-008, RN-011, CA-008, CA-013, RF-022, RN-016, CA-018, CA-031)
---

# write-analysis-report

Gera o arquivo `report.pdf`. Markdown, HTML ou texto na conversa **não** satisfazem a entrega (RF-009). A interpretação dos resultados pertence a este relatório.

## Ferramentas

> **Fora do orquestrador do DataAI** (por exemplo, num harness como Claude Code ou Codex), chame cada ferramenta citada nesta skill pelo terminal: `python -m dataai ferramenta <pasta_da_analise> <nome> '<json dos argumentos>'` (ou `@arquivo.json`). A saída é JSON. O passo a passo completo está em `CLAUDE.md`.

## Entrada

- Plano (`plan-analysis`): pergunta ou modo exploratório, suposições, limitações.
- Resultados (`describe-data`) e especificações de gráficos (`design-charts`).
- Avisos acumulados das skills anteriores.
- Na correção: a lista de problemas de `orchestrate-quality-review`.

## Estrutura

1. **Capa:** título da análise, data, arquivos analisados.
2. **Objetivo:** a pergunta do usuário (modo `directed`) ou o objetivo da exploração (modo `exploratory`), em uma ou duas frases.
3. **Resposta curta / principais achados:** de 3 a 5 achados em blocos `finding`, cada um com magnitude, comparação com uma referência, confiabilidade e, quando couber, o ponto a investigar (CA-031). No modo `directed`, o primeiro achado responde diretamente à pergunta. O conjunto cobre mais de uma pergunta de decisão (RN-016).
4. **Dados utilizados:** arquivos, período, unidade de observação, volume e relações usadas, em linguagem simples.
5. **Desenvolvimento:** uma seção por achado, na ordem do raciocínio:
   - o que foi medido (métrica e população);
   - o gráfico ou tabela;
   - o que o resultado mostra;
   - o que isso significa para o objetivo, sem ir além da evidência.
6. **Limitações:** qualidade dos dados, suposições adotadas, grupos pequenos, períodos parciais, o que os dados não permitem afirmar.
7. **Apêndice:** definições das métricas (fórmula, unidade, população) e tratamentos aplicados.

## Storytelling (RN-011)

- Cada seção deve se ligar ao objetivo. Uma estatística que não se conecta a nada sai do relatório ou vai para o apêndice.
- Ordem: do achado mais importante para o de detalhe, ou na sequência que responde à pergunta.
- Transições curtas entre seções explicam por que o próximo achado importa.
- Não basta listar números: explique o que eles significam no contexto do usuário.

## Interpretação proporcional

| Evidência | Linguagem adequada |
|---|---|
| Diferença grande e amostra suficiente | "X é maior que Y (35% contra 12%)" |
| Grupo com `small_sample` | "Com poucos casos (n=18), o resultado de X é instável" |
| Associação descritiva | "X e Y variam juntos (r=0,62)"; **nunca** "X causa Y" |
| Período parcial | "2024 inclui apenas até junho" |

Proibido: inventar números, arredondar de forma que mude o sentido, afirmar causalidade ou significância estatística, recomendar ações que os dados não sustentam. Recomendações, se houver, são apresentadas como pontos a investigar.

## Implementação

- Ferramenta `build_report` (`dataai/tools/report.py`, reportlab). Documento:
  ```json
  { "title": "...", "subtitle": "...",
    "sections": [ { "heading": "Principais achados", "blocks": [
      { "type": "finding", "title": "Receita cresceu no 1º trimestre de 2025",
        "magnitude": "{{res_receita_var:pct_change|percent_1}} ({{res_receita_var:abs_change|currency_brl}})",
        "reference": "contra o mesmo trimestre de 2024",
        "reliability": "n = {{res_receita_var:n|integer}} vendas; sensibilidade baixa",
        "interpretation": "...", "investigate": "..." },
      { "type": "chart", "chart_id": "ch_receita_mes" },
      { "type": "paragraph", "text": "..." } ] } ] }
  ```
  Blocos: `paragraph`, `subheading`, `bullets`, `finding`, `chart`, `table`, `tool_note`, `page_break`. Capa, numeração de páginas e apêndice (definições das métricas, tratamentos e mapa de ligações) são automáticos.
- **Números só por marcador:** `{{result_id:caminho|formato}}`, por exemplo `{{res_receita_loja:rows[group=Online].value|currency_brl}}`. O código substitui pelo valor do resultado e registra cada uso em `number_refs`. Número digitado fora de marcador é defeito na revisão. Limiares de método (20%, 80%, 1,5 × IQR) usam `{{const:20%}}` e só valem se estiverem na lista documentada.
- `tool_note` só pode repetir um aviso registrado pelas ferramentas (por exemplo, Simpson ou fonte divergente).
- Gráficos renderizados como PNG em alta resolução, com as cores de `design-charts`.
- Tamanho A4, margens de 2 cm, corpo 10,5 a 11 pt, numeração de páginas, títulos de seção numerados.
- Nenhum gráfico ou tabela cortado entre páginas.
- Salve em `deliverables/v<N>/report.pdf`.

## Antes de entregar

1. Rode `inspect_report` (com `attach_pages: true` para ver as páginas) e confira legibilidade, cortes, páginas vazias e gráficos.
2. Confira que cada número citado no texto existe em algum `result_id` (guarde o mapa em `number_refs`).

## Resultado

```json
{
  "stage": "artifact",
  "artifact_ref": "deliverables/v1/report.pdf",
  "version": 1,
  "sha256": "...",
  "pages": 7,
  "sections": ["Objetivo", "Principais achados", "Dados utilizados", "Evasão por curso", "Limitações", "Apêndice"],
  "charts_included": ["ch_evasao_curso"],
  "number_refs": [ { "text": "35,2%", "page": 2, "result_id": "res_evasao_por_curso", "field": "taxa", "row": "Engenharia" } ],
  "renderer": "weasyprint 62.3",
  "page_images": ["review/pages/report_p1.png"]
}
```

`stage: "draft"` indica só um rascunho e **não** satisfaz a entrega.

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Existe um arquivo `.pdf` real.
- [ ] O objetivo aparece no início e os achados se ligam a ele.
- [ ] Todo número do texto tem `result_id` de origem.
- [ ] Nenhuma afirmação causal ou de significância.
- [ ] Limitações presentes.
