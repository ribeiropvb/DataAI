---
name: relate-datasets
description: Trata análises com vários arquivos no DataAI. Identifica partições (uma tabela dividida em vários arquivos ou abas) e as empilha, descobre a partir dos dados as ligações entre tabelas de arquivos diferentes (chaves, contenção, cardinalidade, integridade referencial, papéis das tabelas, armadilhas de junção) e executa as junções pedidas pelo plano com verificação antes e depois. Use sempre que houver mais de um arquivo ou aba, e quando o plano precisar cruzar tabelas.
metadata:
  project: DataAI
  agent: data-specialist
  spec: specs.md v1.3 (RF-007, RF-023, RF-024, RF-025, RN-003, RN-017, RN-018, RN-019, 12.8, P-003, CA-007, CA-027 a CA-030)
---

# relate-datasets

Um arquivo não é uma tabela (RN-017). Esta skill descobre como os arquivos se organizam e se ligam, e garante que juntar tabelas não invente nem perca números. Descobrir uma ligação não autoriza usá-la: só se junta o que o plano pede (RN-003).

## Ferramentas

> **Fora do orquestrador do DataAI** (por exemplo, num harness como Claude Code ou Codex), chame cada ferramenta citada nesta skill pelo terminal: `python -m dataai ferramenta <pasta_da_analise> <nome> '<json dos argumentos>'` (ou `@arquivo.json`). A saída é JSON. O passo a passo completo está em `CLAUDE.md`.

| Etapa | Função (`dataai/tools/relations.py`) |
|---|---|
| Partições e empilhamento | `relationship_map(ws)` → usa `detect_partitions` e `stack_partitions` |
| Descoberta, papéis, grafo, armadilhas | `finalize_relationship_map(ws, stage)` (depois de `profile-data`) |
| Caminhos de junção | `build_graph(relations)`, `join_paths(graph, a, b)` |
| Junção verificada | `safe_join(ws, left_id, right_id, left_on, right_on, how, derived_id, aggregate_right)` |

Saída principal: `results/relationship_map.json`.

## 1. Partições: uma tabela em vários arquivos [proposta MVP, P-003]

1. Compare os esquemas normalizados (nomes sem acento, minúsculos) de todos os pares de tabelas.
2. **Esquema idêntico** e tipos compatíveis: grupo de partições. Empilhe automaticamente (ajuste de leitura registrado), com `_source_file` e `_source_sheet` em cada linha.
3. **Esquema quase idêntico** (Jaccard dos nomes ≥ 0,8): pergunta ao usuário com o mapeamento proposto. Não empilhe sem resposta.
4. Depois de empilhar, confira: total de linhas = soma das partições; chaves repetidas entre partições; períodos sobrepostos. Registre o discriminador (token do nome do arquivo ou aba).
5. A partir daqui, use o dataset empilhado (`kind: stacked`); as partições ficam com `kind: partition`.

## 2. Descoberta de ligações (12.8.3)

Rode depois de `profile-data`, que define tipos semânticos e chaves candidatas (inclusive compostas, até 3 colunas).

| Evidência | Como é medida |
|---|---|
| Contenção | \|distintos de A ∩ distintos de B\| ÷ \|distintos de A\|, depois de normalizar formato (texto aparado, maiúsculas, inteiros sem zeros à esquerda e sem `.0`) |
| Unicidade do alvo | o lado referenciado precisa ser chave candidata |
| Nome | semelhança dos nomes; nomes genéricos (`id`, `codigo`) comparam os nomes das tabelas. **Indício, nunca prova** (RN-018) |
| Formato | tipos físicos compatíveis |

- Pontuação = 0,50·contenção + 0,25·unicidade + 0,15·nome + 0,10·formato.
- **Forte:** pontuação ≥ 0,7 e contenção ≥ 0,9. **Provável:** ≥ 0,5 e contenção ≥ 0,5; só é usada depois de confirmada pelo especialista ou pelo usuário.
- Ficam fora, para evitar coincidências: medidas contínuas, datas, booleanos e texto livre. Colunas com menos de 10 valores distintos, inteiros classificados como medida e alvos que são sequências 1..N só entram com apoio do nome (semelhança ≥ 0,5).
- Para cada ligação registre: cardinalidade observada (1:1, N:1, N:N), integridade referencial (órfãos em linhas e %, exemplos, chaves nulas, pais sem filhos) e se há ambiguidade (mesma coluna apontando para dois alvos fortes).

## 3. Papéis, grafo e armadilhas

- **Papel de cada tabela:** fato, dimensão, ponte, agregada (grão mensal/anual), referência ou isolada.
- **Grafo:** tabelas são nós, ligações fortes são arestas. Caminhos de junção pelo menor caminho; vários caminhos mínimos = ambiguidade (pergunta).
- **Armadilhas detectadas:** *fan-out* (duas tabelas fato ligadas ao mesmo cadastro), grão diferente (diário × mensal) e muitos para muitos. Todas viram aviso e orientam o plano: agregar ao grão comum antes de juntar.

## 4. Relações suportadas [proposta MVP, P-003]

| Caso | Suporte no MVP |
|---|---|
| 1:1, N:1 (chave simples ou composta) | sim |
| N:N | só por tabela ponte detectada; direto, `needs_clarification` |
| chave ambígua ou caminhos alternativos | `needs_clarification` |
| ligação "provável" | só depois de confirmada |

## 5. Junção verificada (`safe_join`)

1. Normalize as chaves dos dois lados (ajuste automático registrado).
2. Se a direita repete a chave, **pare** (multiplicaria a esquerda) ou agregue antes com `aggregate_right`.
3. `left` por padrão (a tabela principal define a população); `inner` só com motivo, registrando quantas linhas saíram; nunca `outer` automático.
4. Depois: linhas da esquerda iguais em `left`; **totais de controle** das medidas da esquerda iguais; órfãos contados com exemplos.
5. Nomes: colunas da direita mantêm o nome; em conflito recebem `__<right_id>`; a chave da direita é descartada.
6. O dataset derivado guarda `parents` e tipos semânticos (linhagem, RN-019); o tratamento `join` vai para o manifesto.

## 6. Origens diferentes (RF-025)

- A origem de cada arquivo (`source_label`, informada pelo usuário ou o nome do arquivo) acompanha datasets e resultados.
- Códigos diferentes para a mesma coisa exigem tabela de correspondência nos dados ou informada; sem ela, não ligue.
- Mesma medida ou atributo em duas fontes: reconcilie com `source_coverage`, `reconcile_measure` e `attribute_divergence` (família M14 de `describe-data`). Escolher uma fonte como oficial é decisão do usuário (P-020).

## Resultado

```json
{
  "relationship_map": "results/relationship_map.json",
  "summary": {
    "tables": { "ds_vendas": "fato", "ds_produtos": "dimensão", "ds_feriados": "isolada" },
    "partitions": [ { "stacked": "ds_vendas", "members": ["ds_vendas_2024_s1", "ds_vendas_2024_s2", "ds_vendas_2025_t1"] } ],
    "strong_relations": [ "ds_vendas.produto -> ds_produtos.sku (N:1, órfãos 0.0%)" ],
    "probable_relations": [],
    "isolated": ["ds_feriados"],
    "traps": ["fan_out"]
  }
}
```

Cada junção executada devolve `rows`, `control_totals`, `unmatched`, `renamed_right_columns` e `derived_dataset_id`.

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Partições identificadas e empilhadas com origem por linha; esquemas parecidos viraram pergunta.
- [ ] Toda ligação usada tem contenção, cardinalidade e órfãos registrados (RN-018).
- [ ] Arquivos sem evidência de ligação ficaram isolados (CA-029).
- [ ] Armadilhas de fan-out e grão tratadas por agregação antes da junção.
- [ ] Totais de controle iguais antes e depois de cada junção.
