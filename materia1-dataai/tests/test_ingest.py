from pathlib import Path

import pandas as pd

from dataai.tools import ingest
from dataai.workspace import Workspace


def _ws(tmp_path, files):
    return Workspace.create(tmp_path / "an", files, None, "both", "x")


def test_csv_br_encoding_delimiter_decimal_and_leading_zeros(tmp_path):
    f = tmp_path / "vendas.csv"
    f.write_bytes("código;valor;data;cep\n001;1.234,56;31/12/2024;01001000\n002;10,5;01/01/2025;02002000\n".encode("cp1252"))
    ws = _ws(tmp_path, [f])
    env = ingest.ingest(ws)
    ds = env["result"]["datasets"][0]
    assert ds["read_options"]["delimiter"] == ";" and ds["read_options"]["encoding"] == "cp1252"
    types = {c["name"]: c["dtype"] for c in ds["columns"]}
    assert types == {"código": "string", "valor": "float", "data": "datetime", "cep": "string"}
    df = ws.load_dataset(ds["dataset_id"])
    assert df["valor"].tolist() == [1234.56, 10.5]
    assert df["código"].tolist() == ["001", "002"]


def test_malformed_rows_counted_not_silently_dropped(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("a,b\n1,2\n3,4,5\n6,7\na,b\n8,9\n", encoding="utf-8")
    ws = _ws(tmp_path, [f])
    env = ingest.ingest(ws)
    ds = env["result"]["datasets"][0]
    assert ds["rows"] == 3 and ds["malformed_rows"]["count"] == 1
    codes = {w["code"] for w in env["warnings"]}
    assert {"malformed_rows", "repeated_header"} <= codes
    assert env["status"] == "needs_clarification"  # 1 de 4 linhas (> 5%)


def test_ambiguous_dates_generate_question(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("dia,v\n01/02/2024,1\n03/04/2024,2\n05/06/2024,3\n", encoding="utf-8")
    env = ingest.ingest(_ws(tmp_path, [f]))
    assert any(q["question_id"].startswith("q_date_") for q in env["questions"])


def test_xlsx_each_sheet_is_a_dataset_and_unsupported_structures_blocked(tmp_path):
    f = tmp_path / "plan.xlsx"
    with pd.ExcelWriter(f, engine="openpyxl") as xw:
        pd.DataFrame({"id": [1, 2], "nome": ["a", "b"]}).to_excel(xw, sheet_name="Cad", index=False)
        pd.DataFrame({"x": ["A", "Total"], "v": [1, 1]}).to_excel(xw, sheet_name="Resumo", index=False)
        pd.DataFrame().to_excel(xw, sheet_name="Vazia", index=False)
    env = ingest.ingest(_ws(tmp_path, [f]))
    assert [d["source_sheet"] for d in env["result"]["datasets"]] == ["Cad"]
    reasons = {i["sheet"]: i["reason"] for i in env["result"]["ignored_sheets"]}
    assert "total" in reasons["Resumo"] and reasons["Vazia"] == "aba vazia"


def test_unsupported_format_rejected(tmp_path):
    good = tmp_path / "a.csv"
    good.write_text("a,b\n1,2\n", encoding="utf-8")
    bad = tmp_path / "b.xls"
    bad.write_bytes(b"nada")
    env = ingest.ingest(_ws(tmp_path, [good, bad]))
    assert env["status"] == "completed"
    assert env["result"]["rejected_files"][0]["file"].endswith("b.xls")
