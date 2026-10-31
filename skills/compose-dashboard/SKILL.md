---
name: compose-dashboard
description: Produz o dashboard HTML real de uma análise do DataAI a partir dos resultados e das especificações de gráficos, com hierarquia visual, cores consistentes, interações e layout responsivo, sem nenhuma narrativa interpretativa. Use quando a entrega pedida incluir dashboard, ou para corrigir um dashboard apontado pela revisão.
metadata:
  project: DataAI
  agent: interface-designer
  spec: specs.md v1.3 (RF-010, RF-012, RN-005, RN-006, RN-008, RN-012, RN-015, CA-009 a CA-011, CA-019)
---

# compose-dashboard

Gera o arquivo `dashboard.html`. Uma especificação, imagem ou PDF **não** substitui o HTML (RF-010).

## Ferramentas

> **Fora do orquestrador do DataAI** (por exemplo, num harness como Claude Code ou Codex), chame cada ferramenta citada nesta skill pelo terminal: `python -m dataai ferramenta <pasta_da_analise> <nome> '<json dos argumentos>'` (ou `@arquivo.json`). A saída é JSON. O passo a passo completo está em `CLAUDE.md`.

## Entrada

- Especificações de `design-charts` (`charts/*.json`) e `color_map`.
- Resultados de `describe-data` (`results/*.json`).
- Plano (para nomear visões e filtros).
- Na correção: a lista de problemas de `orchestrate-quality-review`.

## O que o dashboard pode e não pode ter (RN-006)

| Pode | Não pode |
|---|---|
| Títulos descritivos de gráficos e seções | Parágrafos analíticos |
| Valores, unidades, eixos, legendas | Resumo executivo |
| Cabeçalhos de tabela | Conclusões ou recomendações |
| Rótulos de filtros e controles | Cards de "insights" ou "destaques" |
| Indicadores (KPI) com nome e unidade | Frases interpretativas em títulos, tooltips, rodapés ou atributos `title`/`alt` |
| Data de geração e fonte dos dados | "Veja que...", "Isso mostra...", "Preocupante", "Excelente" |

Exemplo permitido: "Ocorrências por mês". Proibido: "O aumento de ocorrências demonstra falha da estratégia".

Limitações e suposições **não** entram no HTML; elas vão para o resumo da execução (RN-015).

## Estrutura

1. **Cabeçalho:** nome da análise, período coberto, data de geração.
2. **Faixa de indicadores:** de 3 a 6 KPIs principais.
3. **Filtros** somente quando fizerem sentido para os dados desta análise (período, categoria principal). Não copie filtros de outras análises.
4. **Visões:** quando houver muitos gráficos, organize em abas ou seções por tema (por exemplo, "Matrículas" e "Evasão"). No MVP, um único arquivo HTML [proposta MVP, P-010].
5. **Grade de gráficos:** do mais importante para o de detalhe; gráficos relacionados lado a lado.
6. **Tabela detalhada** opcional no final, com ordenação.

## Implementação

- Ferramenta `build_dashboard` (`dataai/tools/dashboard.py`) com a configuração:
  ```json
  { "title": "Vendas 2024–2025", "subtitle": "Período: jan/2024 a mar/2025",
    "kpis": [ { "label": "Receita", "result_id": "res_receita_total", "path": "sum", "format": "currency_brl_compact" } ],
    "views": [ { "name": "Visão geral", "charts": ["ch_receita_mes", "ch_receita_loja"] } ],
    "detail_table": "ch_tabela_lojas" }
  ```
  `path` usa a mesma sintaxe dos marcadores do relatório (`valor`, `rows[group=Online].value`). A ferramenta recusa texto narrativo na configuração.
- Um único arquivo `deliverables/v<N>/dashboard.html`, autossuficiente: dados embutidos em `<script id="dataai-data">` (lido pela validação).
- ECharts 5.5.1 por CDN com versão fixa, ou embutido quando `DATAAI_ECHARTS_JS` aponta para uma cópia local (uso sem internet).
- Os números vêm **somente** de `results/*.json`. Não recalcule, não digite valores à mão.
- Use as cores de `design-charts` e o `color_map`. Mesma categoria, mesma cor em todos os gráficos e filtros.
- Formate números no padrão do usuário (pt-BR: `1.234,56`; percentuais com uma casa).
- Filtros atualizam todos os gráficos afetados e mostram o filtro ativo.

## Visual (RN-012)

- Fundo claro e neutro, cartões com borda ou sombra leve, espaçamento consistente (múltiplos de 8 px).
- Hierarquia por tamanho: KPIs em destaque, títulos de gráfico menores que o título da página.
- Tipografia legível: corpo ≥ 14 px, rótulos ≥ 12 px.
- Evite monotonia: variar tipos de gráfico conforme o dado e usar a paleta categórica quando houver categorias. Não colorir uma série única com várias cores.
- **Responsivo:** a grade passa de 3 para 2 e para 1 coluna em telas menores. Nada de rolagem horizontal na página.

## Antes de entregar

1. Rode `inspect_dashboard` (com `attach_screens: true` para ver as capturas). Ela abre o HTML em navegador headless em 1440, 900 e 390 px, salva capturas em `review/screens_v<N>/`, confere se cada gráfico pintou o canvas, erros no console, rolagem horizontal, abas e o texto dos tooltips.
2. Confira que todos os gráficos renderizaram e que não há erros no console.
3. Varra todo o texto visível, tooltips e atributos `title`/`alt` procurando linguagem interpretativa.
4. Teste cada filtro e cada aba.

## Resultado

```json
{
  "stage": "artifact",
  "artifact_ref": "deliverables/v1/dashboard.html",
  "version": 1,
  "sha256": "...",
  "views": ["Matrículas", "Evasão"],
  "charts_included": ["ch_evasao_curso"],
  "filters": ["periodo", "campus"],
  "library": "echarts@5.5.1",
  "screenshots": ["review/screens/dashboard_wide.png", "review/screens/dashboard_mobile.png"],
  "self_check": { "console_errors": 0, "narrative_found": [] }
}
```

`stage: "specification"` indica só um rascunho e **não** satisfaz a entrega.

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Existe um arquivo `.html` real.
- [ ] Nenhuma frase interpretativa em lugar nenhum do HTML.
- [ ] Todos os números vêm de `results/`.
- [ ] Renderiza sem erros nas três larguras.
