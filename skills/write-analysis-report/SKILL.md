---
name: write-analysis-report
description: Produz o relatório PDF real de uma análise do DataAI, com objetivo, achados, gráficos, interpretação proporcional às evidências, limitações e encadeamento analítico (storytelling), usando somente números já calculados. Use quando a entrega pedida incluir relatório, ou para corrigir um relatório apontado pela revisão.
metadata:
  project: DataAI
  agent: report-writer
  spec: specs.md v1.2 (RF-009, RN-004, RN-008, RN-011, CA-008, CA-013, CA-018)
---

# write-analysis-report

Gera o arquivo `report.pdf`. Markdown, HTML ou texto na conversa **não** satisfazem a entrega (RF-009). A interpretação dos resultados pertence a este relatório.

## Entrada

- Plano (`plan-analysis`): pergunta ou modo exploratório, suposições, limitações.
- Resultados (`describe-data`) e especificações de gráficos (`design-charts`).
- Avisos acumulados das skills anteriores.
- Na correção: a lista de problemas de `orchestrate-quality-review`.

## Estrutura

1. **Capa:** título da análise, data, arquivos analisados.
2. **Objetivo:** a pergunta do usuário (modo `directed`) ou o objetivo da exploração (modo `exploratory`), em uma ou duas frases.
3. **Resposta curta / principais achados:** de 3 a 5 achados, cada um em uma frase com o número que o sustenta. No modo `directed`, o primeiro achado responde diretamente à pergunta.
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

- Gere o PDF a partir de HTML com CSS de impressão (por exemplo, WeasyPrint ou Playwright `page.pdf`). Registre a ferramenta.
- Gráficos renderizados como imagem vetorial (SVG) ou PNG em alta resolução, com as cores de `design-charts`.
- Números **somente** de `results/*.json`, formatados em pt-BR.
- Tamanho A4, margens de 2 cm, corpo 10,5 a 11 pt, numeração de páginas, títulos de seção numerados.
- Nenhum gráfico ou tabela cortado entre páginas.
- Salve em `deliverables/v<N>/report.pdf`.

## Antes de entregar

1. Converta cada página do PDF em imagem e confira legibilidade, cortes e gráficos.
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
