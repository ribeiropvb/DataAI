import pytest

from dataai.tools import ingest, profile, relations


@pytest.fixture
def mapped(workspace):
    ingest.ingest(workspace)
    stage = relations.relationship_map(workspace)
    profile.profile(workspace, stage["active"])
    env = relations.finalize_relationship_map(workspace, stage)
    return workspace, workspace.read_json("results/relationship_map.json"), env


def test_partitions_are_stacked(mapped):  # CA-027
    ws, rmap, _ = mapped
    g = rmap["partitions"][0]
    assert g["members"] == ["ds_vendas_2024_s1", "ds_vendas_2024_s2", "ds_vendas_2025_t1"]
    assert g["checks"]["ok"] and g["checks"]["rows_stacked"] == g["checks"]["rows_sum_parts"]
    assert ws.dataset_meta("ds_vendas")["kind"] == "stacked"
    assert set(ws.load_dataset("ds_vendas")["_source_file"]) == {"vendas_2024_s1.csv", "vendas_2024_s2.csv", "vendas_2025_t1.csv"}


def _strong(rmap):
    return {(r["child"]["dataset_id"], tuple(r["child"]["key"]), r["parent"]["dataset_id"], tuple(r["parent"]["key"])): r
            for r in rmap["relations"] if r["strength"] == "strong"}


def test_links_found_from_data_even_with_different_names(mapped):  # CA-028
    _, rmap, _ = mapped
    s = _strong(rmap)
    r = s[("ds_vendas", ("produto",), "ds_produtos", ("sku",))]
    assert r["cardinality_observed"] == "N:1" and r["evidence"]["containment"] == 1.0
    cli = s[("ds_vendas", ("cod_cliente",), "ds_cadastro_clientes", ("codigo",))]  # zeros à esquerda x inteiro
    assert 0.03 < cli["integrity"]["orphan_rows_pct"] < 0.1
    assert ("ds_crm_clientes", ("codigo_cliente",), "ds_cadastro_clientes", ("codigo",)) in s


def test_independent_file_not_linked_and_no_spurious_sequence_links(mapped):  # CA-029
    _, rmap, _ = mapped
    roles = {t["dataset_id"]: t["role"] for t in rmap["tables"]}
    assert roles["ds_feriados"] == "isolada"
    assert not any(r["parent"]["key"] == ["id_venda"] for r in rmap["relations"] if r["strength"] == "strong")


def test_roles_and_traps(mapped):
    _, rmap, _ = mapped
    roles = {t["dataset_id"]: t["role"] for t in rmap["tables"]}
    assert roles["ds_vendas"] == "fato" and roles["ds_cadastro_metas"] == "agregada"
    assert any(t["kind"] == "fan_out" for t in rmap["traps"])


def test_safe_join_keeps_rows_and_totals(mapped):
    ws, _, _ = mapped
    rec = relations.safe_join(ws, "ds_vendas", "ds_produtos", ["produto"], ["sku"])
    assert rec["rows"]["left_before"] == rec["rows"]["after"]
    assert all(c["ok"] for c in rec["control_totals"])
    assert "sku" not in ws.load_dataset(rec["derived_dataset_id"]).columns


def test_safe_join_refuses_fan_out(mapped):
    ws, _, _ = mapped
    with pytest.raises(relations.JoinError):
        relations.safe_join(ws, "ds_cadastro_lojas", "ds_cadastro_metas", ["loja_id"], ["loja_id"])
    rec = relations.safe_join(ws, "ds_cadastro_lojas", "ds_cadastro_metas", ["loja_id"], ["loja_id"],
                              aggregate_right={"meta_valor": "sum"})
    assert rec["rows"]["after"] == 6


def test_name_similarity_generic_ids_use_table_names():
    assert relations.name_similarity("id", "id", "clientes", "pedidos") == 0.0
    assert relations.name_similarity("cliente_id", "id", "clientes") >= 0.9
