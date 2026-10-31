---
name: ingest-tabular
description: Lê arquivos CSV e Excel (.xlsx) enviados para uma análise do DataAI, preserva os originais, detecta encoding, delimitador e tipos, e registra origem, abas e erros de leitura. Use no início de toda análise, antes de qualquer perfil ou cálculo, sempre que houver arquivos tabulares novos.
metadata:
  project: DataAI
  agent: data-specialist
  spec: specs.md v1.3 (RF-001, RF-002, RF-016, RN-003, P-001, P-002, RF-023, RN-019, 12.8.1, P-013)
---

# ingest-tabular

Transforma os arquivos recebidos em datasets de trabalho confiáveis, sem perder nada em silêncio. Esta skill não interpreta o significado dos dados; isso é papel de `profile-data`.

## Ferramentas

Executada pelo código antes dos agentes: `dataai/tools/ingest.py` (`ingest(ws)`), chamado por `python -m dataai analisar`. O agente `data-specialist` lê o resultado com `list_datasets` e `preview_rows`.

- Vários arquivos por análise (até 10, 50 MB no total). Cada CSV é uma tabela; cada aba `.xlsx` com dados é uma tabela (P-001).
- Cada tabela guarda arquivo, aba, hash e a **origem** informada pelo usuário (`--origem arquivo=rótulo`); sem ela, a origem é o nome do arquivo (12.8.1).
- Cada linha do Parquet em `working/` recebe `_source_file` e `_source_sheet` (RN-019), usados depois para empilhar partições e rastrear a linhagem.
- Detecção automática de codificação (utf-8, cp1252, latin-1), delimitador, separador decimal (pt-BR ou en), percentuais, datas (ordem ambígua vira pergunta) e códigos com zeros à esquerda (mantidos como texto).

## Entrada

- `analysis_id` e a pasta da análise.
- Lista de arquivos enviados pelo usuário (caminhos em `originals/`).

## Limites aceitos [proposta MVP]

| Item | Aceito | Fora do suporte |
|---|---|---|
| Formatos | `.csv`, `.txt` delimitado, `.xlsx` | `.xls`, `.xlsm`, `.ods`, compactados (`.zip`, `.rar`) |
| Quantidade | até 10 arquivos por análise | acima disso |
| Tamanho | até 50 MB somados | acima disso |
| Excel | uma tabela por aba, cabeçalho na primeira linha, fórmulas lidas pelo valor calculado | várias tabelas na mesma aba, cabeçalho com células mescladas, linhas de subtotal, arquivo protegido por senha |

Fora do suporte: não tente adivinhar a estrutura. Registre o motivo e siga a regra de falhas abaixo.

## Procedimento

1. **Preserve os originais.** Calcule o SHA-256 de cada arquivo em `originals/` e registre no manifesto. Nunca altere esses arquivos.
2. **CSV:**
   - Detecte o encoding (tente UTF-8, depois UTF-8 com BOM, depois Latin-1) e registre qual funcionou.
   - Detecte o delimitador entre `,`, `;`, tabulação e `|` pela consistência do número de campos nas primeiras linhas.
   - Detecte o separador decimal e de milhar olhando colunas numéricas (`1.234,56` vs `1,234.56`).
   - Leia **todas as colunas como texto** primeiro; a conversão de tipos vem depois.
3. **Excel (`.xlsx`):**
   - Liste todas as abas, inclusive ocultas. Cada aba com dados vira um dataset; abas vazias são registradas e ignoradas.
   - Leia os valores calculados (por exemplo, `openpyxl` com `data_only=True`). Se uma fórmula não tiver valor em cache, registre aviso `excel_formula_without_value`.
   - Sinais de estrutura fora do suporte: células mescladas no cabeçalho, linhas totalmente vazias separando blocos, linhas com "Total"/"Subtotal" na primeira coluna. Registre e trate como fora do suporte para aquela aba.
4. **Linhas malformadas:** nunca descarte em silêncio. Conte linhas com número de campos diferente do cabeçalho, guarde até 20 exemplos com o número da linha e registre o aviso `malformed_rows`. Se passarem de 5% das linhas, devolva `needs_clarification`.
5. **Cabeçalhos:** normalize espaços nas pontas, mas guarde o nome original. Colunas sem nome recebem `coluna_<n>`. Nomes duplicados recebem sufixo e aviso. Cabeçalho repetido no meio do arquivo é aviso `repeated_header`.
6. **Conversão de tipos (ajuste de leitura automático):**
   - Números, datas e booleanos só são convertidos quando **todos** os valores não vazios convertem; senão a coluna fica como texto e o aviso informa quantos falharam.
   - **Preserve identificadores:** colunas com zeros à esquerda, códigos (CEP, CPF, matrícula, SKU) ou cujo nome sugira id ficam como texto, mesmo que pareçam números.
   - Datas ambíguas (`03/04/2025` pode ser dia/mês ou mês/dia): se nenhum valor tiver dia acima de 12, gere uma `question`; não escolha em silêncio.
   - Vazio, `NA`, `N/A`, `null`, `-` viram ausente. **Zero nunca é ausente** e ausente nunca vira zero.
7. **Salve a cópia de trabalho** em `working/<dataset_id>.parquet` e registre o tratamento como `read_adjustment` no manifesto.

## Falhas e bloqueios

- Arquivo ilegível ou fora do suporte: registre em `result.rejected_files`. Se o pedido não depender dele, continue com os demais e gere aviso; se depender, devolva `blocked` (P-013).
- Biblioteca de leitura ausente: `blocked` com a dependência faltante.
- Erro inesperado durante a leitura: `failed` com a causa útil.

## Resultado

```json
{
  "datasets": [
    {
      "dataset_id": "ds_orders",
      "source_file": "originals/orders.csv",
      "source_sheet": null,
      "sha256": "...",
      "working_path": "working/ds_orders.parquet",
      "read_options": { "encoding": "utf-8", "delimiter": ";", "decimal": ",", "thousands": "." },
      "rows": 99441,
      "columns": [
        { "name": "order_id", "original_name": "order_id", "dtype": "string", "conversion_failures": 0 }
      ],
      "malformed_rows": { "count": 0, "examples": [] }
    }
  ],
  "rejected_files": [ { "file": "originals/x.xls", "reason": "formato .xls fora do suporte do MVP" } ],
  "ignored_sheets": [ { "file": "originals/y.xlsx", "sheet": "Plan3", "reason": "aba vazia" } ]
}
```

O envelope comum (`skill_name`, `status`, `result`, `warnings`, `questions`, `evidence_refs`) está descrito em `skills/README.md`.

## Checklist antes de concluir

- [ ] Todo arquivo recebido aparece em `datasets`, `rejected_files` ou `ignored_sheets`.
- [ ] Nenhuma linha foi descartada sem contagem e aviso.
- [ ] Identificadores continuam como texto.
- [ ] Originais com hash registrado e intocados.
