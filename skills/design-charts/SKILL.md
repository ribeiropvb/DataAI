---
name: design-charts
description: Escolhe e especifica os gráficos de uma análise do DataAI a partir dos resultados calculados, definindo tipo, eixos, ordenação, cores e destino (relatório, dashboard ou ambos), com títulos descritivos e sem interpretação. Use depois de describe-data e antes de compose-dashboard e write-analysis-report.
metadata:
  project: DataAI
  agent: visualization-specialist
  spec: specs.md v1.3 (RF-011, RF-012, RN-006, RN-012)
---

# design-charts

Define **o que** cada gráfico mostra e **como**, de forma que o relatório e o dashboard usem os mesmos visuais e as mesmas cores. Esta skill não desenha o HTML nem o PDF.

## Ferramentas

`suggest_chart` (proposta de especificação a partir de um resultado), `save_chart` (valida e salva `charts/<chart_id>.json`; devolve os problemas se a especificação não bater com o resultado), `list_charts`, `get_result`, `list_results`. Código: `dataai/tools/charts.py`.

- Tipos suportados: `kpi`, `bar_horizontal`, `column`, `line`, `histogram`, `heatmap`, `pareto`, `waterfall` (pontes de M10) e `table`.
- A mesma especificação gera a imagem do PDF (`render_png`, matplotlib) e o gráfico interativo do dashboard (`echarts_option`, ECharts 5.5.1), com as mesmas cores (`ColorMap`).
- Formatos de número: `integer`, `decimal_1`, `decimal_2`, `percent_0/1/2`, `pp_1`, `currency_brl`, `currency_brl_compact`, `compact`, `days`, `index`, `coef` (pt-BR).

## Entrada

- Resultados de `describe-data` (`results/*.json`).
- Gráficos previstos no plano.

## Escolha do tipo

| O que mostrar | Tipo recomendado | Evite |
|---|---|---|
| Comparar categorias | barras horizontais, ordenadas por valor | pizza com mais de 5 fatias |
| Evolução no tempo | linha (ou colunas se poucos períodos) | linha para categorias sem ordem |
| Distribuição de uma medida | histograma ou boxplot | média isolada |
| Composição de um total | barras empilhadas 100% ou barras simples de participação | pizza 3D, rosca com muitas fatias |
| Relação entre duas medidas | dispersão | linha ligando pontos sem ordem |
| Um número de destaque | indicador (KPI) com unidade | gráfico para um único valor |
| Matriz categoria × categoria | heatmap com escala sequencial | muitas cores categóricas |

Mais de 12 categorias: mostre as principais e agrupe o resto em "Outros", registrando o critério.

## Cores

Paleta neutra padrão do MVP (não há paleta de marca definida):

| Função | Cor |
|---|---|
| Série principal | `#2563EB` |
| Categóricas (em ordem) | `#2563EB`, `#F59E0B`, `#10B981`, `#EF4444`, `#8B5CF6`, `#06B6D4`, `#EC4899`, `#84CC16` |
| Sequencial | de `#DBEAFE` a `#1E3A8A` |
| Divergente | `#DC2626` → `#F3F4F6` → `#2563EB` |
| Neutra (eixos, "Outros") | `#9CA3AF` |

Regras (RN-012):
- **A mesma categoria tem a mesma cor em todos os gráficos** da análise. Registre o mapa em `color_map`.
- Uma única série usa uma única cor. Não multicolorir barras de uma série sem motivo.
- Cor nunca é a única forma de distinguir: use rótulos ou legendas.
- Contraste mínimo de 4,5:1 para textos sobre o fundo.

## Títulos e textos (RN-006)

- Títulos **descrevem** o que o gráfico mostra: "Taxa de evasão no 1º ano por curso".
- Títulos **não concluem**: proibido "Engenharia tem a pior evasão" ou "Evasão preocupante em 2024".
- Rótulos de eixo sempre com unidade (`%`, `R$`, `dias`).
- Tooltips mostram valores, unidades e categoria; nunca frases interpretativas.

## Especificação de cada gráfico

```json
{
  "chart_id": "ch_evasao_curso",
  "version": 1,
  "result_id": "res_evasao_por_curso",
  "type": "bar_horizontal",
  "title": "Taxa de evasão no 1º ano por curso",
  "x": { "field": "taxa", "label": "Evasão (%)", "format": "percent_1" },
  "y": { "field": "curso", "label": "Curso", "sort": "desc_by_x" },
  "color": { "mode": "single", "value": "#2563EB" },
  "annotations": [ { "type": "flag", "field": "small_sample", "label": "amostra < 30" } ],
  "targets": ["report", "dashboard"],
  "interactions": ["tooltip"],
  "alt_text": "Barras horizontais com a taxa de evasão de 12 cursos."
}
```

`alt_text` descreve a forma do gráfico, sem interpretar. Salve cada especificação em `charts/<chart_id>.json`.

## Resultado

```json
{
  "charts": [ { "chart_id": "ch_evasao_curso", "path": "charts/ch_evasao_curso.json", "targets": ["report", "dashboard"] } ],
  "color_map": { "Engenharia": "#2563EB", "Direito": "#F59E0B" }
}
```

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Todo gráfico aponta para um `result_id` existente.
- [ ] Nenhum título ou tooltip contém conclusão.
- [ ] Cores consistentes entre gráficos e `color_map` registrado.
- [ ] Eixos com unidade.
