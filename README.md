# DataAI

Análise de dados com agentes de IA para quem não programa.

Você envia um ou mais arquivos CSV ou Excel, faz uma pergunta sobre eles (ou pede uma exploração geral) e recebe um **relatório PDF** com a interpretação dos resultados, um **dashboard HTML** com as visualizações, ou os dois. Os números são calculados por ferramentas de verdade, nunca estimados pelo modelo, e toda entrega passa por uma revisão de qualidade antes de ser liberada.

> **Situação:** especificação na versão 1.3 ([`specs.md`](specs.md)), skills escritas e implementação de referência em Python funcionando ponta a ponta (com IA ou no modo sem IA). Falta escolher o provedor e o modelo de IA.

## Para quem é

- **Primeiro público:** pessoas que conhecem seu negócio ou seus dados, mas não programam.
- **Público futuro:** analistas que querem acelerar o próprio trabalho.

O produto é multidomínio: funciona com dados de qualquer tema (vendas, educação, operações etc.), sem métricas fixas de um setor.

## Como funciona

1. **Entrada:** um ou mais arquivos CSV ou `.xlsx`, que podem estar relacionados entre si. Uma tabela dividida em vários arquivos (por mês, por filial) é empilhada automaticamente, e as ligações entre arquivos são descobertas pela evidência dos dados, não só pelo nome das colunas.
2. **Intenção:** uma pergunta em linguagem natural ou um pedido de exploração geral, sem precisar de pergunta.
3. **Entrega escolhida:** relatório, dashboard ou ambos.
4. **Processamento por agentes:** leitura e perfil dos dados, planejamento, relações entre tabelas, métricas para decisão (qualidade, composição, concentração, tendência, comparação com referência, decomposição da variação, entidades e coortes, prazos, associação, reconciliação entre fontes e sensibilidade), gráficos e geração dos arquivos.
5. **Revisão de qualidade:** um agente orquestrador inspeciona os arquivos gerados, aponta cada defeito, envia a correção ao agente responsável e confere de novo (até 3 ciclos no MVP).
6. **Resultado:** os arquivos pedidos e um **resumo da execução**, com suposições, tratamentos aplicados, limitações e o resultado da revisão.

## Regras principais

- **Relatório é sempre PDF** e contém a interpretação, com encadeamento analítico (storytelling).
- **Dashboard é sempre HTML** e **não contém narrativa interpretativa**: nada de conclusões, recomendações ou cards de insights, nem em títulos e tooltips.
- **Números vêm de cálculo real**, com referência à origem. Sem causalidade ou significância estatística sem suporte.
- **Os arquivos originais são preservados.** Ajustes de leitura são automáticos e registrados; excluir registros, imputar ausências ou resolver duplicidades ambíguas exige autorização.
- **Cada análise guarda seu histórico:** arquivos usados, pedido, esclarecimentos, definições de métricas, tratamentos e versões dos resultados e entregas.

## Arquitetura

- Agentes baseados em LLM, coordenados pelo código da própria aplicação, em Python.
- **Sem CrewAI e sem n8n.**
- Competências organizadas em skills com `SKILL.md`, no padrão [Agent Skills](https://agentskills.io/home).
- Ferramentas usadas pelos agentes: cálculo (pandas), gráficos (matplotlib no PDF, ECharts no HTML), PDF (reportlab), navegador headless (Playwright) para a revisão visual.
- No MVP: execução local, um usuário, uma análise por vez, histórico em uma pasta por análise com manifesto JSON.

### Skills

| Skill | Responsabilidade |
|---|---|
| `plan-analysis` | Interpretar a intenção e planejar a análise e as entregas. |
| `ingest-tabular` | Ler CSV e Excel e registrar origem, abas e erros de leitura. |
| `profile-data` | Examinar tipos, ausências, duplicidades e qualidade. |
| `relate-datasets` | Planejar e verificar relações entre tabelas. |
| `describe-data` | Calcular estatísticas e agregações descritivas. |
| `design-charts` | Definir as visualizações. |
| `compose-dashboard` | Produzir o dashboard HTML. |
| `write-analysis-report` | Produzir o relatório PDF. |
| `validate-analysis` | Auditar números, relações e consistência. |
| `orchestrate-quality-review` | Revisar as entregas, direcionar correções e decidir a liberação. |

## Como executar

Requer Python 3.11 ou mais recente.

```bash
pip install -e ".[dev]"            # dependências e pytest
python -m playwright install chromium   # navegador para a revisão visual do dashboard
```

**Sem IA** (planejamento por regras; útil para testar ferramentas e entregas):

```bash
python examples/generate_demo.py
python -m dataai analisar examples/demo_varejo/* --no-llm --entrega both
```

**Com IA:** o código não depende de um provedor específico. Configure por variáveis de ambiente:

| Variável | Valores |
|---|---|
| `DATAAI_PROVIDER` | `anthropic`, `openai` ou `openai_compatible` (qualquer serviço com a API de chat da OpenAI, inclusive modelos locais) |
| `DATAAI_MODEL` | nome do modelo |
| `DATAAI_API_KEY` | chave da API (ou a variável padrão do provedor) |
| `DATAAI_BASE_URL` | endereço do serviço, para `openai_compatible` |

Instale o adaptador com `pip install -e ".[anthropic]"` ou `".[openai]"` e rode:

```bash
python -m dataai analisar examples/demo_varejo/* --pergunta "Quais lojas e categorias explicam a variação da receita?" --entrega both --interativo
```

Outras opções: `--origem arquivo.csv=ERP` informa a origem de um arquivo; `--echarts-local caminho/echarts.min.js` (ou `DATAAI_ECHARTS_JS`) embute o ECharts no HTML para uso sem internet; `python -m dataai catalogo` lista as métricas.

Cada análise fica em `analyses/<id>/` com os originais, os dados de trabalho, os resultados versionados, os gráficos, as entregas (`deliverables/v<N>/`), a revisão e o `execution_summary.md`.

**Testes:** `python -m pytest -q tests`.

### Estrutura do código

| Pasta | Papel |
|---|---|
| `dataai/tools/` | Ferramentas determinísticas: leitura, perfil, ligações, métricas (M1–M15), gráficos, dashboard, PDF, inspeção e validação. Todo número sai daqui. |
| `dataai/agents/` | Monta cada agente (perfil + `SKILL.md`), expõe as ferramentas permitidas e executa o ciclo de chamadas. |
| `dataai/llm/` | Interface única de provedor de IA, com adaptadores. |
| `dataai/orchestrator.py` | Encadeia as etapas e os ciclos de revisão. |
| `agents/` | Perfis dos oito agentes. |
| `skills/` | Instruções dos agentes. |
| `examples/` | Gerador de dados de demonstração com sete arquivos ligados entre si. |

## Escopo do MVP

**Dentro:** CSV e `.xlsx` (uma tabela por aba), até 10 arquivos e 50 MB por análise, relações um para um e um para muitos, análise descritiva, PDF e HTML, revisão de qualidade e histórico local.

**Fora:** login e controle de acesso, modelos preditivos, testes de hipóteses, inferência causal, conexão direta a bancos e sistemas externos, atualização recorrente, upload de arquivos compactados e modo avançado para analistas.

## Pendências

- Escolha do provedor e do modelo de IA (o código já aceita qualquer um dos adaptadores).
- Metas como referência (P-019) e fonte oficial quando duas fontes divergem (P-020).
- Confirmação dos limites de entrada propostos (10 arquivos e 50 MB).
- Demais decisões listadas na seção 16 do [`specs.md`](specs.md).

## Documentação

- [`specs.md`](specs.md): especificação consolidada, com requisitos (RF), regras de negócio (RN), critérios de aceite (CA) e pendências (P).
- [`skills/`](skills/README.md): as 10 skills dos agentes, com o contrato de saída comum e o fluxo entre elas.
