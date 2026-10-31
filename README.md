# DataAI

Análise de dados com agentes de IA para quem não programa.

Você envia um ou mais arquivos CSV ou Excel, faz uma pergunta sobre eles (ou pede uma exploração geral) e recebe um **relatório PDF** com a interpretação dos resultados, um **dashboard HTML** com as visualizações, ou os dois. Os números são calculados por ferramentas de verdade, nunca estimados pelo modelo, e toda entrega passa por uma revisão de qualidade antes de ser liberada.

> **Situação:** em especificação. Ainda não há código implementado. A especificação completa está em [`specs.md`](specs.md) (versão 1.2).

## Para quem é

- **Primeiro público:** pessoas que conhecem seu negócio ou seus dados, mas não programam.
- **Público futuro:** analistas que querem acelerar o próprio trabalho.

O produto é multidomínio: funciona com dados de qualquer tema (vendas, educação, operações etc.), sem métricas fixas de um setor.

## Como funciona

1. **Entrada:** um ou mais arquivos CSV ou `.xlsx`, que podem estar relacionados entre si.
2. **Intenção:** uma pergunta em linguagem natural ou um pedido de exploração geral, sem precisar de pergunta.
3. **Entrega escolhida:** relatório, dashboard ou ambos.
4. **Processamento por agentes:** leitura e perfil dos dados, planejamento, relações entre tabelas, cálculos descritivos, gráficos e geração dos arquivos.
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
- Ferramentas usadas pelos agentes: cálculo (pandas), geração de PDF e HTML, e navegador headless para a revisão visual.
- No MVP: execução local, um usuário, uma análise por vez, histórico em uma pasta por análise com manifesto JSON.

### Skills previstas

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

## Escopo do MVP

**Dentro:** CSV e `.xlsx` (uma tabela por aba), até 10 arquivos e 50 MB por análise, relações um para um e um para muitos, análise descritiva, PDF e HTML, revisão de qualidade e histórico local.

**Fora:** login e controle de acesso, modelos preditivos, testes de hipóteses, inferência causal, conexão direta a bancos e sistemas externos, atualização recorrente, upload de arquivos compactados e modo avançado para analistas.

## Pendências

- Escolha do provedor e do modelo de IA.
- Confirmação dos limites de entrada propostos (10 arquivos e 50 MB).
- Demais decisões listadas na seção 16 do [`specs.md`](specs.md).

## Documentação

- [`specs.md`](specs.md): especificação consolidada, com requisitos (RF), regras de negócio (RN), critérios de aceite (CA) e pendências (P).
