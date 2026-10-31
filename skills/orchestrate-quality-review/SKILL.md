---
name: orchestrate-quality-review
description: Revisa criticamente as entregas finais de uma análise do DataAI (PDF e/ou HTML) quanto a conteúdo, formato, storytelling e apresentação visual, localiza cada defeito, encaminha a correção ao agente responsável, confere a nova versão e decide a liberação. Use depois de validate-analysis e a cada versão corrigida, até aprovar ou esgotar os ciclos.
metadata:
  project: DataAI
  agent: quality-orchestrator
  spec: specs.md v1.2 (RF-013 a RF-015, RN-006, RN-009 a RN-012, RN-015, 8.3, 12.3, P-012, CA-014 a CA-019)
---

# orchestrate-quality-review

É a última barreira antes do usuário. Examina **os arquivos gerados e renderizados**, nunca apenas a descrição que o agente produtor deu deles.

## Entrada

- Entregas em `deliverables/v<N>/`, capturas de tela e imagens de página.
- Decisão e `issues` de `validate-analysis`.
- Plano, pedido do usuário e entregas pedidas (`output_mode`).
- Em ciclos seguintes: problemas abertos e as novas versões.

## O que revisar

### Formato (RN-009, sempre)

- [ ] Se foi pedido relatório: existe `report.pdf` real.
- [ ] Se foi pedido dashboard: existe `dashboard.html` real.
- [ ] Se foram pedidos os dois: existem os dois, e não um terceiro formato no lugar (RN-007).

### Dashboard sem narrativa (RN-006)

Abra o HTML em navegador headless e extraia **todo** o texto: visível, tooltips (passe o mouse sobre os pontos), atributos `title`, `alt` e `aria-label`. Aponte qualquer frase que conclua, avalie ou recomende. Títulos descritivos, valores, unidades, eixos, legendas e rótulos de controles são permitidos.

### Relatório: conteúdo e storytelling (RN-011)

- [ ] O objetivo ou a pergunta aparece no início.
- [ ] No modo `directed`, a pergunta é respondida explicitamente.
- [ ] Os achados seguem uma ordem lógica e se ligam ao objetivo.
- [ ] A interpretação é proporcional à evidência; sem causalidade, sem significância inventada.
- [ ] Grupos pequenos e períodos parciais são tratados com cautela.
- [ ] Há seção de limitações.
- [ ] Todas as páginas legíveis, sem gráficos ou tabelas cortados.

### Dashboard: apresentação (RN-012)

- [ ] Hierarquia clara (indicadores em destaque, depois gráficos, depois detalhe).
- [ ] Não monótono: tipos de gráfico adequados e variados conforme os dados; paleta categórica onde há categorias.
- [ ] Cores consistentes para a mesma categoria; uma série única sem multicoloração.
- [ ] Valores e rótulos legíveis; nada sobreposto.
- [ ] Filtros e abas funcionam (teste cada um).
- [ ] Layout correto em larguras ampla, média e de celular.

### Números

Incorpore os `issues` de `validate-analysis`. Se a decisão dela for `fail` ou `blocked`, a entrega não pode ser aprovada.

## Registro de problemas

Cada problema precisa ser localizável e verificável. "Melhorar o dashboard" não serve (RF-014).

```json
{
  "issue_id": "iss_004",
  "category": "dashboard_narrative",
  "severity": "defect",
  "artifact_ref": "deliverables/v1/dashboard.html",
  "location": "aba Evasão, título do gráfico ch_evasao_curso",
  "evidence_refs": ["review/screens/dashboard_wide.png"],
  "problem": "O título 'Engenharia lidera a evasão' contém conclusão.",
  "impact": "Viola RN-006: interpretação no dashboard.",
  "owner_agent": "interface-designer",
  "target_skill": "compose-dashboard",
  "acceptance_criteria": "Título descritivo, por exemplo 'Taxa de evasão no 1º ano por curso'.",
  "status": "open",
  "verified_by": null
}
```

Categorias: `format`, `dashboard_narrative`, `numeric_mismatch`, `storytelling`, `interpretation`, `visual`, `interaction`, `responsiveness`, `legibility`, `missing_content`.

**Severidade [proposta MVP, P-012]:**
- `defect`: impede a aprovação. Inclui todo problema de formato, narrativa no HTML, número errado, causalidade sem suporte, conteúdo ilegível ou pergunta não respondida.
- `suggestion`: melhoria opcional que não afeta correção nem regras. Pode ser encaminhada, mas não bloqueia.

## Ciclo de correção

1. Agrupe os problemas por `target_skill` e gere `repair_tasks`, uma por skill, com a lista de `issue_id` e os critérios de aceite.
2. Encaminhe cada tarefa ao agente responsável. Se a correção envolve números, inclua `describe-data` e rode `validate-analysis` de novo depois.
3. Ao receber a nova versão, **examine o arquivo novo** e verifique cada problema contra o seu `acceptance_criteria`. Só marque `resolved` com evidência (nova captura, página, trecho). A declaração do produtor não basta (RF-015).
4. Verifique também se a correção não quebrou outra coisa (regressão).
5. Repita até não haver `defect` aberto ou até o limite de **3 ciclos** [proposta MVP, P-012].

## Decisão

| `result.decision` | Quando |
|---|---|
| `approve` | Nenhum `defect` aberto e todas as verificações obrigatórias feitas. Registre o SHA-256 das versões aprovadas. |
| `revise` | Há `defect` aberto e ainda há ciclos disponíveis. |
| `blocked` | Não é possível revisar (arquivo ausente, renderização impossível) ou os ciclos acabaram com defeito aberto. |

Se os 3 ciclos acabarem com defeito aberto, **nunca aprove**. Entregue a última versão marcada como "não aprovada" e liste os defeitos restantes no resumo da execução.

Qualquer alteração em um arquivo depois de aprovado invalida a aprovação daquele arquivo (o hash muda).

## Resumo da execução (RN-015)

Ao final, escreva `execution_summary.md` com:
- o que foi pedido e as entregas geradas;
- suposições adotadas e esclarecimentos recebidos;
- tratamentos aplicados aos dados;
- limitações dos dados;
- resultado da revisão: aprovado ou não, ciclos usados, defeitos restantes (se houver).

Esse resumo não contém interpretação dos achados (isso é do PDF) e é o canal das limitações quando só o dashboard foi pedido.

## Resultado

```json
{
  "decision": "approve",
  "cycle": 2,
  "max_cycles": 3,
  "checks_performed": ["format", "dashboard_narrative", "storytelling", "visual", "interaction", "responsiveness", "numbers"],
  "issues": [],
  "repair_tasks": [],
  "approved_artifacts": [
    { "artifact_ref": "deliverables/v2/report.pdf", "sha256": "..." },
    { "artifact_ref": "deliverables/v2/dashboard.html", "sha256": "..." }
  ],
  "execution_summary": "execution_summary.md"
}
```

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Revisei os arquivos renderizados, não descrições.
- [ ] Formato e ausência de narrativa conferidos explicitamente.
- [ ] Cada problema tem localização, evidência, responsável e critério de aceite.
- [ ] Cada correção foi verificada no arquivo novo.
- [ ] Nada com defeito aberto foi aprovado.
- [ ] Resumo da execução escrito.
