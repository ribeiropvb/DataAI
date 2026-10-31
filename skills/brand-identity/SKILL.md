---
name: brand-identity
description: Guarda a identidade visual aprovada do DataAI (princípios, cores de interface e de dados, tipografia IBM Plex, espaçamento, símbolo) e diz como aplicá-la no dashboard, no PDF e nos gráficos. Use antes de escolher qualquer cor, fonte ou elemento visual, ao revisar o visual de uma entrega, ou ao mudar a própria identidade.
metadata:
  project: DataAI
  agents: visualization-specialist, interface-designer, report-writer, quality-orchestrator
  spec: specs.md v1.3 (RN-006, RN-012, RNF-002, CA-019, seção 12.10)
  source: dataai/brand/tokens.json
---

# brand-identity

A identidade visual do DataAI foi aprovada pelo usuário em 31/10/2026. Esta skill é a dona dela: as outras skills (`design-charts`, `compose-dashboard`, `write-analysis-report`) usam o que está aqui e não definem cores ou fontes próprias.

## Fonte única

| O quê | Onde |
|---|---|
| Todos os valores (cores nos temas claro e escuro, tipografia, espaços, raios, sombra) | `dataai/brand/tokens.json` |
| Leitura no código | `dataai/theme.py` (`color()`, `data_palette()`, `css_variables()`, `logo_svg()`, `register_pdf_fonts()`, `matplotlib_font()`) |
| Símbolo | `dataai/brand/dataai-marca-claro.svg`, `-escuro.svg`, `-mono.svg` |
| Fontes | `dataai/brand/fonts/` (IBM Plex Sans e Mono, licença OFL em `OFL.txt`) |

Nenhum módulo de `dataai/tools/` escreve cor em hexadecimal: tudo vem de `dataai.theme`. Uma cor nova entra primeiro no `tokens.json`, com nota de uso, e só então no código.

## Princípios (em ordem; o de cima vence)

1. **O dado fala primeiro.** A cor da marca nunca disputa atenção com os dados. Nos gráficos, `marca` aparece só como série única ou primeira categoria. Sem faixas, fundos ou ilustrações coloridas.
2. **Descrever, não julgar.** Nenhuma cor diz que um valor é bom ou ruim (RN-006). `sucesso`, `atencao` e `erro` são só para estados do sistema: revisão, qualidade do arquivo, amostra pequena. Variação positiva e negativa usam os dois lados da escala divergente, não verde e vermelho.
3. **Todo número mostra a origem.** Fonte e `result_id` embaixo de cada gráfico e tabela, em `legenda`; nomes técnicos em mono.
4. **Legível para quem não programa.** Corpo de 16 px no dashboard (10,5 pt no PDF), contraste mínimo de 4,5:1 para texto, rótulo direto quando couber, números tabulares com separadores brasileiros.

## Cores de interface

| Papel | Claro | Escuro | Uso |
|---|---|---|---|
| `fundo` | `#F3F8FA` | `#0E161A` | Fundo da página |
| `superficie` | `#FFFFFF` | `#152025` | Cartões, gráficos, papel do PDF |
| `superficie-elevada` | `#E9EEF0` | `#1C2A30` | Cabeçalho de tabela, quadro de achado no PDF |
| `linha` | `#D7DCDE` | `#2A3A41` | Bordas e divisórias |
| `tinta` | `#141C20` | `#E2E9EC` | Texto principal |
| `tinta-suave` | `#606B70` | `#B7C3C9` | Legendas, unidades, rótulos de eixo |
| `marca` | `#067689` | `#57B0C5` | Aba ativa, link, botão, série única |
| `marca-forte` | `#014B58` | `#8CCDDD` | Títulos de seção do PDF |
| `foco` | `#1093AA` | `#8CCDDD` | Anel de foco de 2 px |
| `sucesso` / `atencao` / `erro` / `info` | ver `tokens.json` | | Estados do sistema, sempre com ícone e palavra |

O tema escuro do dashboard segue `prefers-color-scheme`. O PDF usa só o tema claro.

## Cores de dados

- **Categóricas, nesta ordem:** `dados-1` petróleo, `dados-2` ocre, `dados-3` vinho, `dados-4` azul, `dados-5` ameixa, `dados-6` laranja, `dados-7` violeta, `dados-8` verde. A ordem maximiza a separação também para daltonismo (deuteranopia, protanopia, tritanopia).
- Até 6 categorias: cor + legenda. 7ª e 8ª: só com rótulo direto. Acima de 8: principais e "Outros" (`dados-outros`, sempre por último).
- **A mesma categoria tem a mesma cor em toda a análise** (`color_map`). A cor é atribuída na ordem de leitura: o primeiro item exibido recebe `dados-1`.
- **Série única:** só `dados-1`.
- **Sequencial** `dados-seq-1` a `-5` (petróleo): valores ordenados, mapas de calor, coortes.
- **Divergente** `dados-div-1` a `-5` (laranja, neutro, petróleo): variação em torno de uma referência e cascata de variação. O centro é a referência.
- **Grade e eixos:** `dados-grade`; texto do gráfico em `tinta` e `tinta-suave`, nunca na cor da série.
- Marcações de confiabilidade (período parcial, amostra pequena): `atencao`, com símbolo e texto ("○ período parcial", "△ amostra < 30").
- Cada tema tem sua versão das cores de dados; o dashboard troca para a versão escura sozinho. Cor de dados nunca é cor de texto.

## Tipografia

- **IBM Plex Sans** em tudo; **IBM Plex Mono** para `result_id`, colunas e arquivos. Reserva: DejaVu Sans (PDF/matplotlib) e `Segoe UI`/`system-ui` (dashboard).
- Escala (dashboard): `titulo-1` 38, `titulo-2` 30, `titulo-3` 24, `subtitulo` 20, `corpo` 16, `corpo-p` 14, `legenda`/`rotulo` 12 px. No máximo quatro tamanhos por tela. `rotulo` em caixa alta com espaçamento de 0,06em (rótulo de indicador).
- PDF (A4): título da capa 26 pt, seção 15 pt em `marca-forte`, subseção 12 pt, corpo 10,5/15 pt, legenda 8,5 pt.
- Números: `numero-destaque` (32 px, 600) nos indicadores, tabulares sempre.

## Espaço e forma

- Grade de 4 px: 4, 8, 12, 16, 24, 32, 48. Cartões com padding 16 e vão 16; blocos separados por 24.
- Raios: 12 em cartões, 8 em botões, campos e abas, pílula em selos, 4 só na ponta das barras.
- Borda de 1 px em `linha`. Sombra só `sombra-cartao`, só no claro. Sem degradê, sem borda lateral colorida em cartões.

## Símbolo

A **barra-fonte**: duas barras e um traço com ponto no topo, que também lê como o "i" de AI. O ponto é a origem do número.

- Dashboard: símbolo de 40 px à esquerda do título (versão clara ou escura conforme o tema) e como favicon.
- PDF: símbolo de 1,6 cm na capa, acima do título; rodapé "DataAI · título" e número da página.
- Mínimo de 16 px. Não girar, não recolorir, sem sombra.

## Revisão visual (o que reprovar)

Ao inspecionar um dashboard ou PDF (`inspect_dashboard` com `attach_screens`, `inspect_report` com `attach_pages`), aponte como defeito para a skill responsável:

- cor fora dos tokens, ou cores de dados diferentes para a mesma categoria entre gráficos;
- verde/vermelho (ou qualquer cor) julgando valor de negócio;
- série única multicolorida; mais de 8 categorias sem "Outros";
- texto com contraste abaixo de 4,5:1 em algum dos temas;
- gráfico ou tabela sem a linha de origem;
- título de seção sozinho no fim da página do PDF.

## Mudar a identidade

Só com pedido do usuário. Altere `dataai/brand/tokens.json` (e os SVGs, se for o símbolo), confira contraste nos dois temas e separação para daltonismo, atualize esta skill e rode `python -m pytest -q tests`. O guia visual publicado do projeto é a referência para o usuário e deve receber a mesma mudança.

## Checklist antes de concluir

- [ ] Nenhuma cor ou fonte escrita fora de `dataai/brand/tokens.json` / `dataai.theme`.
- [ ] Cores de dados na ordem, `color_map` consistente, "Outros" em `dados-outros`.
- [ ] Nenhuma cor julgando valores.
- [ ] Contraste conferido no tema claro e no escuro.
- [ ] Origem visível em cada gráfico e tabela.
