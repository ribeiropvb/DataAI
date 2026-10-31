"""Gera o conjunto de demonstração (fictício) usado nos testes e no README.

Cenário: rede varejista fictícia com dados vindos de fontes diferentes.
- ERP: vendas em 3 arquivos (partições por período), CSV com ';' e decimal ','.
- Planilha de cadastro (.xlsx): abas Clientes, Lojas e Metas (metas mensais por loja).
- Catálogo: produtos.csv com chave de nome diferente (sku x produto).
- CRM: crm_clientes.csv, outra fonte com o segmento do cliente (para reconciliação).
- feriados.csv: arquivo independente, sem ligação com os demais.

Uso: python examples/generate_demo.py [pasta_destino]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "demo_varejo")
out.mkdir(parents=True, exist_ok=True)

lojas = pd.DataFrame({"loja_id": [1, 2, 3, 4, 5, 6],
                      "nome_loja": ["Centro", "Shopping Norte", "Bairro Sul", "Aeroporto", "Online", "Outlet"],
                      "regiao": ["Centro-Oeste", "Norte", "Sul", "Centro-Oeste", "Nacional", "Sudeste"]})
n_cli = 400
segmentos = rng.choice(["Varejo", "Atacado", "Corporativo"], n_cli, p=[0.7, 0.2, 0.1])
ufs = rng.choice(["GO", "DF", "SP", "MG", "PR", "AM"], n_cli, p=[0.35, 0.2, 0.2, 0.1, 0.1, 0.05])
clientes = pd.DataFrame({"codigo": np.arange(1, n_cli + 1), "nome": [f"Cliente {i:03d}" for i in range(1, n_cli + 1)],
                         "segmento": segmentos, "uf": ufs})
cats = {"Eletrônicos": (1200, 0.15), "Casa": (180, 0.30), "Moda": (120, 0.30), "Esporte": (250, 0.15), "Livros": (60, 0.10)}
prod_rows = []
k = 1
for cat, (preco, _) in cats.items():
    for _ in range(12):
        prod_rows.append({"sku": f"P{k:03d}", "categoria": cat, "preco_lista": round(float(rng.normal(preco, preco * 0.2)), 2)})
        k += 1
produtos = pd.DataFrame(prod_rows)

dates = pd.date_range("2024-01-01", "2025-03-20", freq="D")
rows = []
vid = 1
for d in dates:
    season = 1.0 + 0.35 * (d.month in (11, 12)) + 0.1 * (d.weekday() >= 5)
    growth = 1.0 + 0.02 * ((d - dates[0]).days / 30)
    for _ in range(rng.poisson(6 * season * growth)):
        loja = int(rng.choice(lojas["loja_id"], p=[0.2, 0.15, 0.1, 0.1, 0.35, 0.1]))
        cli = int(rng.integers(1, n_cli + 25))  # alguns clientes não existem no cadastro (órfãos)
        p = produtos.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
        qtd = int(rng.integers(1, 5))
        valor = round(qtd * p["preco_lista"] * float(rng.uniform(0.85, 1.05)), 2)
        status = rng.choice(["pago", "cancelado", "Pago", "PAGO "], p=[0.85, 0.08, 0.05, 0.02])
        prazo = d + pd.Timedelta(days=int(rng.integers(3, 10)))
        atraso = int(rng.choice([0, 0, 0, 1, 2, 5])) + (2 if loja == 5 and d.month in (11, 12) else 0)
        entrega = prazo + pd.Timedelta(days=atraso - int(rng.integers(0, 3))) if status.strip().lower() != "cancelado" else pd.NaT
        rows.append({"id_venda": vid, "data_venda": d, "cod_cliente": f"{cli:06d}", "produto": p["sku"], "loja_id": loja,
                     "quantidade": qtd, "valor_total": valor, "status": status, "data_prevista": prazo, "data_entrega": entrega})
        vid += 1
vendas = pd.DataFrame(rows)


def br_csv(df: pd.DataFrame, path: Path) -> None:
    d = df.copy()
    for c in ("data_venda", "data_prevista", "data_entrega"):
        d[c] = d[c].dt.strftime("%d/%m/%Y")
    d["valor_total"] = d["valor_total"].map(lambda x: f"{x:.2f}".replace(".", ","))
    d.to_csv(path, sep=";", index=False, encoding="cp1252")


br_csv(vendas[vendas["data_venda"] < "2024-07-01"], out / "vendas_2024_s1.csv")
br_csv(vendas[(vendas["data_venda"] >= "2024-07-01") & (vendas["data_venda"] < "2025-01-01")], out / "vendas_2024_s2.csv")
br_csv(vendas[vendas["data_venda"] >= "2025-01-01"], out / "vendas_2025_t1.csv")
produtos.to_csv(out / "produtos.csv", index=False)

meses = pd.date_range("2024-01-01", "2025-03-01", freq="MS")
metas = []
real = vendas.assign(m=vendas["data_venda"].dt.to_period("M").dt.to_timestamp()).groupby(["loja_id", "m"])["valor_total"].sum()
for lj in lojas["loja_id"]:
    for m in meses:
        base = real.get((lj, m), 10000.0)
        metas.append({"loja_id": lj, "mes": m.to_pydatetime(), "meta_valor": round(float(base * rng.uniform(0.9, 1.15)), 2)})
with pd.ExcelWriter(out / "cadastro.xlsx", engine="openpyxl") as xw:
    clientes.to_excel(xw, sheet_name="Clientes", index=False)
    lojas.to_excel(xw, sheet_name="Lojas", index=False)
    pd.DataFrame(metas).to_excel(xw, sheet_name="Metas", index=False)

crm = clientes.sample(frac=0.9, random_state=1)[["codigo", "segmento"]].rename(columns={"codigo": "codigo_cliente"})
flip = crm.sample(frac=0.06, random_state=2).index
crm.loc[flip, "segmento"] = "Corporativo"
crm["origem_cadastro"] = "CRM"
crm.to_csv(out / "crm_clientes.csv", index=False)

pd.DataFrame({"data": ["2024-01-01", "2024-04-21", "2024-05-01", "2024-09-07", "2024-10-12", "2024-11-02",
                       "2024-11-15", "2024-12-25", "2025-01-01", "2025-03-04"],
              "feriado": ["Confraternização", "Tiradentes", "Trabalho", "Independência", "Aparecida", "Finados",
                          "República", "Natal", "Confraternização", "Carnaval"]}).to_csv(out / "feriados.csv", index=False)
print(f"demo gerada em {out} ({len(vendas)} vendas)")
