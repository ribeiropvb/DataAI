---
name: relate-datasets
description: Verifica e define como combinar datasets de uma análise do DataAI, conferindo chaves, cardinalidade, correspondências e totais antes e depois da junção para evitar perda ou multiplicação de registros. Use quando o plano de análise precisar cruzar informações de mais de um arquivo ou aba.
metadata:
  project: DataAI
  agent: data-specialist
  spec: specs.md v1.2 (RF-007, RN-003, 12.4, P-003, CA-007)
---

# relate-datasets

Garante que juntar tabelas não invente nem perca números. Só relacione o que o plano pede (RN-003).

## Entrada

- `relations_needed` de `plan-analysis`.
- Perfis de `profile-data` (chaves candidatas, unidade de observação).
- Datasets em `working/`.

## Relações suportadas [proposta MVP, P-003]

| Cardinalidade | Suporte no MVP |
|---|---|
| um para um (1:1) | sim |
| um para muitos (1:N) | sim, com cuidado com medidas da tabela pai |
| muitos para muitos (N:N) | não automaticamente: devolva `needs_clarification` explicando o risco de dupla contagem |
| chave ambígua (duas colunas candidatas) | não automaticamente: `needs_clarification` |

## Procedimento

Para cada relação pedida:

1. **Confirme as chaves.** Mesmo tipo físico e formato nos dois lados (texto vs. número, zeros à esquerda, espaços, maiúsculas). Normalizar formato da chave é ajuste automático permitido; registre o que foi feito.
2. **Meça antes de juntar:**
   - valores distintos da chave em cada lado;
   - chaves nulas em cada lado;
   - duplicidade da chave no lado que deveria ser único;
   - correspondência: % das chaves da esquerda encontradas na direita e vice-versa.
3. **Determine a cardinalidade observada** e compare com a esperada pela unidade de observação. Se a tabela que deveria ser "um" tem chaves repetidas, pare e avise.
4. **Escolha o tipo de junção** pela pergunta:
   - `left` quando a tabela principal define a população (padrão);
   - `inner` só quando a análise exige registros presentes nos dois lados, registrando quantos saíram;
   - nunca use `outer` sem motivo explícito.
5. **Junte e confira depois:**
   - número de linhas antes e depois. Em `left` 1:1 ou N:1, o número de linhas da esquerda não pode aumentar;
   - **totais de controle**: a soma de pelo menos uma medida da tabela principal antes e depois deve ser igual;
   - linhas sem correspondência (contagem e exemplos).
6. **Medidas da tabela pai em 1:N:** ao juntar pedidos (pai) com itens (filho), o valor do pedido se repete em cada item. Registre em `aggregation_rules` que essa medida deve ser agregada no nível do pai (ou deduplicada pela chave) antes de somar.
7. Salve o resultado em `working/<dataset_id>.parquet` como novo dataset derivado e registre o tratamento `join` no manifesto.

## Falhas

- Correspondência abaixo de 90% na relação principal: aviso; abaixo de 50%: `needs_clarification`, pois a relação pode estar errada.
- Totais de controle diferentes depois da junção: `failed`. Não entregue o dataset derivado.

## Resultado

```json
{
  "relations": [
    {
      "relation_id": "r1",
      "left": { "dataset_id": "ds_orders", "key": ["order_id"] },
      "right": { "dataset_id": "ds_items", "key": ["order_id"] },
      "cardinality_observed": "1:N",
      "join_type": "left",
      "match_rate": { "left_in_right": 99.2, "right_in_left": 100.0 },
      "null_keys": { "left": 0, "right": 0 },
      "rows": { "left_before": 99441, "after": 112650 },
      "control_totals": [ { "measure": "ds_items.price", "before": 13591643.7, "after": 13591643.7, "ok": true } ],
      "unmatched": { "left": 775, "examples": ["..."] },
      "aggregation_rules": [ "ds_orders.freight_total deve ser somado por order_id distinto" ],
      "derived_dataset_id": "ds_orders_items"
    }
  ]
}
```

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Cardinalidade observada registrada para cada relação.
- [ ] Totais de controle iguais antes e depois.
- [ ] Linhas perdidas ou sem correspondência contadas.
- [ ] Regras de agregação para medidas do pai registradas em 1:N.
