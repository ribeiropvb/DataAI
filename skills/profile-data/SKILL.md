---
name: profile-data
description: Examina os datasets já lidos de uma análise do DataAI para identificar a unidade de observação, os tipos semânticos das colunas, ausências, duplicidades, valores suspeitos e chaves candidatas. Use logo após ingest-tabular e antes de planejar a análise ou relacionar tabelas.
metadata:
  project: DataAI
  agent: data-specialist
  spec: specs.md v1.2 (RF-003, RF-006, RN-001, RN-014, 12.4, P-004)
---

# profile-data

Descobre **o que os dados são** antes que alguém calcule algo com eles. Esta skill observa e registra; ela não exclui, não imputa e não corrige.

## Entrada

- Saída de `ingest-tabular` (datasets e caminhos em `working/`).
- O pedido do usuário, apenas como contexto para nomear coisas. Não restrinja o perfil ao pedido.

## Procedimento

Para cada dataset, calcule com código (pandas) e registre:

1. **Volume:** linhas, colunas, tamanho em memória.
2. **Unidade de observação:** o que uma linha representa (pessoa, pedido, item de pedido, evento, agregado mensal...). Baseie-se em colunas únicas, nomes e granularidade de datas. Se houver duas leituras plausíveis com consequências diferentes para somas, registre uma `question`.
3. **Tipo semântico de cada coluna**, além do tipo físico:

   | Tipo semântico | Exemplos | Consequência |
   |---|---|---|
   | `identifier` | ids, códigos, CEP, matrícula | contar distintos; **nunca** somar ou tirar média |
   | `measure` | valor, quantidade, nota, duração | pode somar ou tirar média, conforme a unidade |
   | `category` | status, região, curso | frequências e agrupamentos |
   | `datetime` | datas e horários | séries temporais e períodos |
   | `text` | comentários, descrições | contar e amostrar; sem estatística numérica |
   | `boolean` | sim/não | proporções |

   Uma coluna armazenada como número pode ser `identifier`. Na dúvida entre `identifier` e `measure`, prefira `identifier` e avise.
4. **Ausências:** contagem e percentual por coluna. Diferencie vazio, marcador de ausência e zero. Nunca trate ausência como zero.
5. **Duplicidades:**
   - Linhas totalmente duplicadas (contagem e exemplos).
   - Duplicidade nas chaves candidatas.
   - **Não remova.** Remover ou consolidar exige autorização (P-004); apenas descreva.
6. **Chaves candidatas:** colunas ou combinações com valores únicos e sem ausentes. Indique as que parecem chave estrangeira para outro dataset (mesmo nome, mesmo formato, sobreposição de valores). A confirmação fica com `relate-datasets`.
7. **Valores suspeitos:** negativos em medidas que não deveriam ser negativas, datas no futuro ou muito antigas, categorias quase iguais (`SP`, `sp`, `São Paulo`), valores extremos (fora de 1,5 × IQR, apenas como sinal). Registre como aviso, sem corrigir.
8. **Resumo rápido por coluna:** para `measure`, mínimo, máximo, média e mediana; para `category`, número de categorias e as 10 mais frequentes; para `datetime`, intervalo coberto.

## Regras

- Não use conhecimento de outro domínio para "completar" o significado de uma coluna. Se o nome não esclarece (`v1`, `cod2`), registre como desconhecido.
- Não reutilize perfis de análises anteriores (RN-014).
- Amostras de valores no resultado devem ser curtas (até 5 por coluna) e nunca expor colunas inteiras de dados pessoais.

## Resultado

```json
{
  "profiles": [
    {
      "dataset_id": "ds_orders",
      "rows": 99441,
      "observation_unit": { "description": "um pedido", "confidence": "high", "basis": "order_id único em todas as linhas" },
      "columns": [
        {
          "name": "order_id",
          "semantic_type": "identifier",
          "missing": { "count": 0, "pct": 0.0 },
          "distinct": 99441,
          "summary": {},
          "notes": []
        }
      ],
      "duplicates": { "full_rows": 0, "by_candidate_key": {} },
      "candidate_keys": [ ["order_id"] ],
      "possible_foreign_keys": [ { "column": "customer_id", "target_dataset": "ds_customers", "overlap_pct": 99.8 } ],
      "suspicious": [ { "column": "price", "issue": "valores negativos", "count": 3, "examples": [-10.0] } ]
    }
  ]
}
```

O envelope comum está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Cada dataset tem unidade de observação registrada (ou uma pergunta sobre ela).
- [ ] Nenhum identificador foi marcado como `measure`.
- [ ] Ausência e zero estão separados.
- [ ] Nada foi alterado nos dados de trabalho.
