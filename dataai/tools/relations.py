"""Vários arquivos, partições e ligações entre tabelas (skill relate-datasets, specs 12.8).

- ``detect_partitions`` / ``stack_partitions``: uma tabela dividida em vários arquivos ou abas.
- ``discover_relationships``: chaves e ligações candidatas entre arquivos, com evidência.
- ``relationship_map``: inventário completo (papéis, partições, ligações, armadilhas, caminhos).
- ``safe_join``: junção com verificação antes e depois (linhas, totais de controle, órfãos).
"""
from __future__ import annotations

import itertools
import re
from collections import deque
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

from ..envelope import envelope, question, warning
from ..workspace import Workspace
from .textutil import key_tokens, norm_name, singular, slug, tokens

# [proposta MVP] P-003 — pesos e limiares da seção 12.8.3
W_CONTAINMENT, W_UNIQUE, W_NAME, W_FORMAT = 0.50, 0.25, 0.15, 0.10
STRONG_SCORE, STRONG_CONTAINMENT = 0.70, 0.90
PROBABLE_SCORE, PROBABLE_CONTAINMENT = 0.50, 0.50
MIN_DISTINCT_WITHOUT_NAME = 10
NEAR_SCHEMA_JACCARD = 0.80

_INT_LIKE = re.compile(r"^-?\d+(\.0+)?$")


# =========================================================================== chaves

def normalize_key(s: pd.Series) -> pd.Series:
    """Formato comparável de chave: texto aparado, maiúsculo, inteiros sem zeros à esquerda e sem '.0'."""
    def norm(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
            return None
        t = str(v).strip().upper()
        if not t:
            return None
        if _INT_LIKE.match(t):
            t = str(int(float(t))) if len(t) < 16 else t.split(".")[0].lstrip("0") or "0"
        return t
    return s.map(norm).astype("object")


def name_similarity(col_a: str, col_b: str, table_b: str = "", table_a: str = "") -> float:
    """Semelhança de nomes (indício, nunca prova). Nomes genéricos (``id``, ``codigo``) comparam as tabelas."""
    na, nb = norm_name(col_a), norm_name(col_b)
    ta, tb = key_tokens(col_a), key_tokens(col_b)
    table_toks_b = {singular(t) for t in tokens(table_b) if t != "ds"}
    table_toks_a = {singular(t) for t in tokens(table_a) if t != "ds"}
    if not ta and not tb:  # dois nomes genéricos: só vale se as tabelas forem a mesma entidade
        if not (table_toks_a or table_toks_b):
            return 1.0 if na == nb else 0.0
        inter = table_toks_a & table_toks_b
        return len(inter) / len(table_toks_a | table_toks_b) if (table_toks_a | table_toks_b) else 0.0
    if na == nb:
        return 1.0
    if not tb:
        tb = table_toks_b
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    if ta and ta <= (tb | table_toks_b):
        jac = max(jac, 0.9)
    seq = SequenceMatcher(None, na, nb).ratio() * 0.8
    return float(max(jac, seq))


def _sequential(values: set) -> bool:
    """Inteiros quase contíguos (1..N): coincidem com qualquer outra sequência, não provam ligação."""
    try:
        ints = sorted(int(v) for v in values)
    except (TypeError, ValueError):
        return False
    return len(ints) >= 3 and (ints[-1] - ints[0] + 1) <= 1.1 * len(ints)


def _format_compat(a: pd.Series, b: pd.Series) -> float:
    na, nb = pd.api.types.is_numeric_dtype(a), pd.api.types.is_numeric_dtype(b)
    if na == nb:
        return 1.0
    return 0.7


def _key_eligible(series: pd.Series, sem: str) -> str | None:
    """'yes', 'name_required' (inteiro classificado como medida) ou None."""
    if sem in ("identifier", "category"):
        return "yes"
    if sem == "measure" and pd.api.types.is_integer_dtype(series):
        return "name_required"
    return None


# =========================================================================== partições

def _schema(meta: dict) -> dict[str, str]:
    return {norm_name(c["name"]): c.get("dtype", "string") for c in meta.get("columns", [])}


def _types_compatible(t1: str, t2: str) -> bool:
    num = {"integer", "float"}
    return t1 == t2 or (t1 in num and t2 in num)


def detect_partitions(ws: Workspace, dataset_ids: list[str]) -> tuple[list[dict], list[dict]]:
    """Grupos de partições (esquema idêntico) e pares quase idênticos (pedem confirmação)."""
    metas = {d: ws.dataset_meta(d) for d in dataset_ids}
    schemas = {d: _schema(m) for d, m in metas.items()}
    parent = {d: d for d in dataset_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    near = []
    for a, b in itertools.combinations(dataset_ids, 2):
        sa, sb = schemas[a], schemas[b]
        if not sa or not sb:
            continue
        if set(sa) == set(sb) and all(_types_compatible(sa[c], sb[c]) for c in sa):
            parent[find(a)] = find(b)
        else:
            jac = len(set(sa) & set(sb)) / len(set(sa) | set(sb))
            if jac >= NEAR_SCHEMA_JACCARD:
                near.append({"datasets": [a, b], "jaccard": round(jac, 3),
                             "only_in_a": sorted(set(sa) - set(sb)), "only_in_b": sorted(set(sb) - set(sa))})
    groups: dict[str, list[str]] = {}
    for d in dataset_ids:
        groups.setdefault(find(d), []).append(d)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members = sorted(members)
        out.append({"members": members, "discriminator": _discriminator(ws, members, metas)})
    return out, near


def _discriminator(ws: Workspace, members: list[str], metas: dict) -> dict:
    names = [metas[m].get("source_name") or m for m in members]
    sheets = [metas[m].get("source_sheet") for m in members]
    toks = [set(tokens(re.sub(r"\.[a-z0-9]+$", "", n, flags=re.I))) for n in names]
    common = set.intersection(*toks) if toks else set()
    varying = [sorted(t - common) for t in toks]
    if all(varying) and len({tuple(v) for v in varying}) == len(members):
        return {"kind": "nome do arquivo", "values": {m: "_".join(v) for m, v in zip(members, varying)}}
    if all(sheets) and len(set(sheets)) == len(members):
        return {"kind": "aba", "values": dict(zip(members, sheets))}
    return {"kind": "desconhecido", "values": {}}


def stack_partitions(ws: Workspace, members: list[str], dataset_id: str | None = None) -> dict:
    metas = [ws.dataset_meta(m) for m in members]
    frames = []
    for m in members:
        df = ws.load_dataset(m)
        df = df.rename(columns={c: norm_name(c) if not c.startswith("_") else c for c in df.columns})
        frames.append(df)
    # nomes originais da primeira partição
    original = {norm_name(c["name"]): c["name"] for c in metas[0]["columns"]}
    cols = list(frames[0].columns)
    for c in cols:
        if c.startswith("_"):
            continue
        dtypes = {str(f[c].dtype) for f in frames}
        if len(dtypes) > 1:
            if all(pd.api.types.is_numeric_dtype(f[c]) for f in frames):
                for f in frames:
                    f[c] = f[c].astype("Float64")
            else:
                for f in frames:
                    f[c] = f[c].astype("string")
    stacked = pd.concat([f[cols] for f in frames], ignore_index=True)
    stacked = stacked.rename(columns={k: v for k, v in original.items()})
    did = dataset_id or _stack_id(members)
    working = f"working/{did}.parquet"
    stacked.to_parquet(ws.path(working), index=False)
    rows_parts = [len(f) for f in frames]
    checks = {"rows_sum_parts": int(sum(rows_parts)), "rows_stacked": int(len(stacked)),
              "ok": int(sum(rows_parts)) == int(len(stacked))}
    # duplicidade de chave entre partições e sobreposição de períodos
    overlap_keys, period_overlap = [], []
    for c in cols:
        if c.startswith("_"):
            continue
        oc = original.get(c, c)
        if all(f[c].notna().all() and f[c].is_unique for f in frames) and frames[0][c].dtype != "Float64":
            seen: dict = {}
            dups = 0
            for i, f in enumerate(frames):
                for v in f[c]:
                    if v in seen and seen[v] != i:
                        dups += 1
                    seen.setdefault(v, i)
            overlap_keys.append({"column": oc, "keys_in_more_than_one_partition": dups})
        if pd.api.types.is_datetime64_any_dtype(frames[0][c]):
            ranges = [(f[c].min(), f[c].max()) for f in frames]
            ov = sum(1 for (a1, b1), (a2, b2) in itertools.combinations(ranges, 2)
                     if pd.notna(a1) and pd.notna(a2) and a1 <= b2 and a2 <= b1)
            period_overlap.append({"column": oc, "overlapping_pairs": ov})
    columns = [{**c} for c in metas[0]["columns"]]
    for c in columns:
        c["dtype"] = {"Float64": "float", "Int64": "integer", "string": "string"}.get(str(stacked[c["name"]].dtype), c["dtype"]) \
            if c["name"] in stacked.columns else c["dtype"]
    meta = {
        "dataset_id": did, "kind": "stacked", "source_file": [m["source_file"] for m in metas],
        "source_name": ", ".join(m["source_name"] for m in metas), "source_sheet": None,
        "source_label": ", ".join(sorted({str(m.get("source_label")) for m in metas})),
        "working_path": working, "rows": int(len(stacked)), "columns": columns, "parents": members,
        "partition_checks": {**checks, "key_overlap": overlap_keys, "period_overlap": period_overlap},
    }
    ws.register_dataset(meta)
    for m in metas:
        m["kind"] = "partition"
        m["stacked_into"] = did
        ws.register_dataset(m)
    ws.add_treatment("stack", f"Empilhamento de {len(members)} partições com o mesmo esquema em {did}",
                     [did] + members, {"rows_per_partition": dict(zip(members, rows_parts)), **meta["partition_checks"]})
    return meta


def _stack_id(members: list[str]) -> str:
    parts = [m.split("_") for m in members]
    prefix = []
    for toks in zip(*parts):
        if len(set(toks)) == 1:
            prefix.append(toks[0])
        else:
            break
    base = "_".join(prefix).rstrip("_") or "ds_stacked"
    return base if base != "ds" else "ds_stacked"


# =========================================================================== descoberta

def cardinality(child_keys: pd.Series, parent_keys: pd.Series) -> str:
    c = child_keys.dropna()
    p = parent_keys.dropna()
    cm = "N" if c.duplicated().any() else "1"
    pm = "N" if p.duplicated().any() else "1"
    return f"{cm}:{pm}"


def referential_integrity(child_keys: pd.Series, parent_keys: pd.Series, examples: int = 10) -> dict:
    c = child_keys
    pset = set(parent_keys.dropna())
    nn = c.dropna()
    orphan_mask = ~nn.isin(pset)
    cset = set(nn)
    return {
        "child_rows": int(len(c)), "child_null_keys": int(c.isna().sum()),
        "orphan_rows": int(orphan_mask.sum()), "orphan_rows_pct": float(orphan_mask.mean()) if len(nn) else None,
        "orphan_distinct": int(nn[orphan_mask].nunique()),
        "orphan_examples": sorted(map(str, nn[orphan_mask].unique()))[:examples],
        "parent_distinct": len(pset), "parent_without_children": len(pset - cset),
        "parent_without_children_pct": (len(pset - cset) / len(pset)) if pset else None,
    }


def _composite_candidates(ws, a_id, b_id, dfa, dfb, keys_b):
    """Chaves compostas do alvo cujas partes existem na origem com o mesmo nome normalizado."""
    out = []
    na = {norm_name(c): c for c in dfa.columns if not c.startswith("_")}
    for key in keys_b:
        if len(key) < 2:
            continue
        cols_a = [na.get(norm_name(k)) for k in key]
        if any(c is None for c in cols_a):
            continue
        ta = pd.Series(list(zip(*[normalize_key(dfa[c]) for c in cols_a])))
        tb = pd.Series(list(zip(*[normalize_key(dfb[c]) for c in key])))
        sa, sb = set(ta), set(tb)
        if not sa:
            continue
        cont = len(sa & sb) / len(sa)
        out.append((cols_a, key, cont, ta, tb))
    return out


def discover_relationships(ws: Workspace, dataset_ids: list[str]) -> list[dict]:
    frames = {d: ws.load_dataset(d) for d in dataset_ids}
    metas = {d: ws.dataset_meta(d) for d in dataset_ids}
    norm_cache: dict[tuple[str, str], pd.Series] = {}

    def nk(d, c):
        if (d, c) not in norm_cache:
            norm_cache[(d, c)] = normalize_key(frames[d][c])
        return norm_cache[(d, c)]

    found = []
    for a_id, b_id in itertools.permutations(dataset_ids, 2):
        dfa, dfb = frames[a_id], frames[b_id]
        sem_a, sem_b = metas[a_id].get("semantic_types", {}), metas[b_id].get("semantic_types", {})
        keys_b = metas[b_id].get("candidate_keys") or []
        single_keys_b = [k[0] for k in keys_b if len(k) == 1]
        table_b_name = _table_name(metas[b_id], b_id)
        table_a_name = _table_name(metas[a_id], a_id)
        for cb in single_keys_b:
            if not _key_eligible(dfb[cb], sem_b.get(cb, "category")):
                continue
            set_b = set(nk(b_id, cb).dropna())
            seq_b = _sequential(set_b)
            for ca in [c for c in dfa.columns if not c.startswith("_")]:
                elig = _key_eligible(dfa[ca], sem_a.get(ca, "category"))
                if not elig:
                    continue
                name = name_similarity(ca, cb, table_b_name, table_a_name)
                va = nk(a_id, ca).dropna()
                set_a = set(va)
                if not set_a:
                    continue
                if (elig == "name_required" or len(set_a) < MIN_DISTINCT_WITHOUT_NAME) and name < 0.5:
                    continue
                if seq_b and name < 0.5:  # PK 1..N contém qualquer inteiro pequeno: exige apoio do nome
                    continue
                inter = len(set_a & set_b)
                if inter == 0:
                    continue
                cont = inter / len(set_a)
                uniq = 1.0
                fmt = _format_compat(dfa[ca], dfb[cb])
                score = W_CONTAINMENT * cont + W_UNIQUE * uniq + W_NAME * name + W_FORMAT * fmt
                strength = ("strong" if score >= STRONG_SCORE and cont >= STRONG_CONTAINMENT else
                            "probable" if score >= PROBABLE_SCORE and cont >= PROBABLE_CONTAINMENT else None)
                if strength is None:
                    continue
                found.append(_relation(a_id, b_id, [ca], [cb], cont, uniq, name, fmt, score, strength,
                                       nk(a_id, ca), nk(b_id, cb)))
        for cols_a, key, cont, ta, tb in _composite_candidates(ws, a_id, b_id, dfa, dfb, keys_b):
            if cont < PROBABLE_CONTAINMENT:
                continue
            score = W_CONTAINMENT * cont + W_UNIQUE + W_NAME + W_FORMAT
            strength = "strong" if cont >= STRONG_CONTAINMENT else "probable"
            found.append(_relation(a_id, b_id, cols_a, list(key), cont, 1.0, 1.0, 1.0, score, strength, ta, tb))
    return _dedupe(found)


def _table_name(meta: dict, did: str) -> str:
    if meta.get("kind") == "stacked":
        return did.replace("ds_", "")
    return meta.get("source_sheet") or re.sub(r"\.[^.]+$", "", meta.get("source_name") or did)


def _relation(a_id, b_id, cols_a, cols_b, cont, uniq, name, fmt, score, strength, ka, kb) -> dict:
    card = cardinality(ka, kb)
    integ = referential_integrity(ka, kb)
    return {
        "relation_id": f"r_{slug(a_id, 20)}__{slug(b_id, 20)}__{slug('_'.join(cols_a), 20)}",
        "child": {"dataset_id": a_id, "key": cols_a},
        "parent": {"dataset_id": b_id, "key": cols_b},
        "evidence": {"containment": round(cont, 4), "target_uniqueness": uniq, "name_similarity": round(name, 3),
                     "format_compat": fmt, "score": round(score, 4)},
        "strength": strength,
        "needs_confirmation": strength != "strong",
        "cardinality_observed": card,
        "cardinality_label": {"N:1": "muitos para um", "1:1": "um para um", "1:N": "um para muitos",
                              "N:N": "muitos para muitos"}[card],
        "integrity": integ,
    }


def _dedupe(rels: list[dict]) -> list[dict]:
    """Remove o par espelhado de relações 1:1 e mantém a de maior pontuação por par de colunas."""
    best: dict = {}
    for r in rels:
        a, b = r["child"], r["parent"]
        k = tuple(sorted([(a["dataset_id"], tuple(a["key"])), (b["dataset_id"], tuple(b["key"]))]))
        if k not in best or r["evidence"]["score"] > best[k]["evidence"]["score"]:
            best[k] = r
    out = sorted(best.values(), key=lambda r: (r["strength"] != "strong", -r["evidence"]["score"]))
    # se uma coluna da origem aponta para dois alvos, marque ambiguidade
    by_child: dict = {}
    for r in out:
        by_child.setdefault((r["child"]["dataset_id"], tuple(r["child"]["key"])), []).append(r)
    for group in by_child.values():
        strong = [r for r in group if r["strength"] == "strong"]
        if len(strong) > 1:
            for r in strong:
                r["ambiguous_with"] = [x["relation_id"] for x in strong if x is not r]
                r["needs_confirmation"] = True
    return out


# =========================================================================== papéis, grafo, armadilhas

def _date_grain(df: pd.DataFrame, dates: list[str]) -> str | None:
    if not dates:
        return None
    d = pd.to_datetime(df[dates[0]], errors="coerce").dropna()
    if d.empty:
        return None
    if (d.dt.day == 1).all() and (d.dt.month == 1).all():
        return "anual"
    if (d.dt.day == 1).all():
        return "mensal"
    return "diário ou mais fino"


def classify_roles(ws: Workspace, dataset_ids: list[str], rels: list[dict]) -> dict[str, dict]:
    strong = [r for r in rels if r["strength"] == "strong"]
    roles = {}
    for d in dataset_ids:
        m = ws.dataset_meta(d)
        sem = m.get("semantic_types", {})
        measures = [c for c, t in sem.items() if t == "measure"]
        dates = [c for c, t in sem.items() if t == "datetime"]
        out_rels = [r for r in strong if r["child"]["dataset_id"] == d and r["cardinality_observed"] in ("N:1", "1:1")]
        in_rels = [r for r in strong if r["parent"]["dataset_id"] == d]
        keys = m.get("candidate_keys") or []
        fk_cols = {c for r in out_rels for c in r["child"]["key"]}
        df = ws.load_dataset(d)
        grain = _date_grain(df, dates)
        if not out_rels and not in_rels:
            role, why = "isolada", "sem ligação forte com outras tabelas"
        elif len({r["parent"]["dataset_id"] for r in out_rels}) >= 2 and any(set(k) <= fk_cols for k in keys if len(k) >= 2) and len(measures) <= 1:
            role, why = "ponte", "chave composta formada por chaves de outras tabelas"
        elif grain in ("mensal", "anual") and measures:
            role, why = "agregada", f"datas no grão {grain} com medidas"
        elif in_rels and not measures and m["rows"] <= 50:
            role, why = "referência", "tabela pequena referenciada por outras"
        elif in_rels and (len(measures) <= 1 or not out_rels) and not dates:
            role, why = "dimensão", "referenciada por outras tabelas (cadastro)"
        elif measures or dates:
            role, why = "fato", "registros com medidas ou datas que apontam para cadastros"
        else:
            role, why = "dimensão", "referenciada por outras tabelas"
        roles[d] = {"role": role, "basis": why, "rows": m["rows"], "grain": grain,
                    "observation_unit": (m.get("observation_unit") or {}).get("description")}
    return roles


def build_graph(rels: list[dict]) -> dict[str, set[str]]:
    g: dict[str, set[str]] = {}
    for r in rels:
        if r["strength"] != "strong":
            continue
        a, b = r["child"]["dataset_id"], r["parent"]["dataset_id"]
        g.setdefault(a, set()).add(b)
        g.setdefault(b, set()).add(a)
    return g


def join_paths(graph: dict[str, set[str]], start: str, goal: str, max_paths: int = 5) -> list[list[str]]:
    """Todos os caminhos mais curtos entre duas tabelas (vários = ambiguidade)."""
    if start == goal:
        return [[start]]
    best, paths = None, []
    q = deque([[start]])
    while q:
        path = q.popleft()
        if best is not None and len(path) > best:
            break
        for nxt in sorted(graph.get(path[-1], ())):
            if nxt in path:
                continue
            np_ = path + [nxt]
            if nxt == goal:
                best = len(np_)
                paths.append(np_)
                if len(paths) >= max_paths:
                    return paths
            else:
                q.append(np_)
    return paths


def detect_traps(rels: list[dict], roles: dict[str, dict]) -> list[dict]:
    traps = []
    strong = [r for r in rels if r["strength"] == "strong"]
    children_of: dict[str, list[str]] = {}
    for r in strong:
        if r["cardinality_observed"] == "N:1":
            children_of.setdefault(r["parent"]["dataset_id"], []).append(r["child"]["dataset_id"])
    for parent, kids in children_of.items():
        kids = sorted(set(kids))
        facts = [k for k in kids if roles.get(k, {}).get("role") in ("fato", "agregada", "ponte")]
        if len(facts) >= 2:
            traps.append({"kind": "fan_out", "tables": [parent] + facts,
                          "message": f"Juntar {', '.join(facts)} pela tabela {parent} na mesma consulta multiplica medidas. "
                                     f"Agregue cada uma ao grão de {parent} antes de combinar."})
    for r in strong:
        a, b = r["child"]["dataset_id"], r["parent"]["dataset_id"]
        ga, gb = roles.get(a, {}).get("grain"), roles.get(b, {}).get("grain")
        if ga and gb and ga != gb:
            traps.append({"kind": "grain_mismatch", "tables": [a, b],
                          "message": f"{a} está no grão {ga} e {b} no grão {gb}; agregue ao grão comum antes de juntar."})
        if r["cardinality_observed"] == "N:N":
            traps.append({"kind": "many_to_many", "tables": [a, b],
                          "message": f"Ligação {a} ↔ {b} é muitos para muitos; não juntar sem tabela ponte ou agregação (P-003)."})
    return traps


# =========================================================================== mapa completo

def relationship_map(ws: Workspace, stack: bool = True) -> dict:
    """Etapa completa de vários arquivos: partições, ligações, papéis, grafo e armadilhas."""
    warns, questions = [], []
    src = [d["dataset_id"] for d in ws.manifest["datasets"] if d.get("kind") == "source"]
    groups, near = detect_partitions(ws, src)
    stacked = []
    if stack:
        for g in groups:
            meta = stack_partitions(ws, g["members"])
            g["stacked_dataset_id"] = meta["dataset_id"]
            g["checks"] = meta["partition_checks"]
            stacked.append(meta["dataset_id"])
            warns.append(warning("partitions_stacked",
                                 f"{len(g['members'])} arquivos/abas com o mesmo esquema foram empilhados em {meta['dataset_id']} "
                                 f"({meta['rows']} linhas).", [meta["working_path"]]))
            for k in meta["partition_checks"]["key_overlap"]:
                if k["keys_in_more_than_one_partition"]:
                    warns.append(warning("partition_key_overlap",
                                         f"{meta['dataset_id']}.{k['column']}: {k['keys_in_more_than_one_partition']} chaves aparecem em mais de uma partição."))
    for n in near:
        questions.append(question(
            f"q_near_schema_{slug('_'.join(n['datasets']), 30)}",
            f"{n['datasets'][0]} e {n['datasets'][1]} têm colunas quase iguais. São partes da mesma tabela?",
            "Se forem, devem ser empilhadas; se não, são tabelas diferentes.",
            ["sim, empilhar (mapeando as colunas diferentes)", "não, são tabelas diferentes"],
            "não, são tabelas diferentes"))
    active = [d["dataset_id"] for d in ws.manifest["datasets"] if d.get("kind") in ("source", "stacked")]
    return {"active": active, "groups": groups, "near": near, "warnings": warns, "questions": questions}


def finalize_relationship_map(ws: Workspace, stage: dict) -> dict:
    """Depois do perfil (que define tipos e chaves), descobre ligações e grava o mapa."""
    active = stage["active"]
    warns, questions = list(stage["warnings"]), list(stage["questions"])
    rels = discover_relationships(ws, active) if len(active) > 1 else []
    roles = classify_roles(ws, active, rels)
    graph = build_graph(rels)
    traps = detect_traps(rels, roles)
    for r in rels:
        integ = r["integrity"]
        if r["strength"] == "strong" and (integ["orphan_rows_pct"] or 0) > 0.0:
            warns.append(warning("orphan_keys",
                                 f"{r['child']['dataset_id']}.{'+'.join(r['child']['key'])}: "
                                 f"{integ['orphan_rows']} linhas ({integ['orphan_rows_pct']:.1%}) sem correspondência em {r['parent']['dataset_id']}."))
        if r.get("ambiguous_with"):
            warns.append(warning("ambiguous_key", f"{r['relation_id']} concorre com {r['ambiguous_with']}; escolha exige confirmação."))
    for t in traps:
        warns.append(warning(t["kind"], t["message"]))
    components = _components(active, graph)
    rmap = {
        "tables": [{"dataset_id": d, **roles[d], "source": ws.dataset_meta(d).get("source_name"),
                    "source_label": ws.dataset_meta(d).get("source_label"),
                    "candidate_keys": ws.dataset_meta(d).get("candidate_keys")} for d in active],
        "partitions": stage["groups"], "near_identical_schemas": stage["near"],
        "relations": rels, "graph": {k: sorted(v) for k, v in graph.items()}, "components": components,
        "traps": traps,
        "thresholds": {"strong": {"score": STRONG_SCORE, "containment": STRONG_CONTAINMENT},
                       "probable": {"score": PROBABLE_SCORE, "containment": PROBABLE_CONTAINMENT},
                       "weights": {"containment": W_CONTAINMENT, "target_uniqueness": W_UNIQUE,
                                   "name": W_NAME, "format": W_FORMAT}},
    }
    ws.write_json("results/relationship_map.json", rmap)
    env = envelope("relate-datasets", "completed", {"relationship_map": "results/relationship_map.json",
                                                     "summary": summarize_map(rmap)},
                   warns, questions, ["results/relationship_map.json"])
    ws.save_skill_output(env, "discovery")
    return env


def _components(nodes: list[str], graph: dict[str, set[str]]) -> list[list[str]]:
    seen, comps = set(), []
    for n in nodes:
        if n in seen:
            continue
        comp, stack = [], [n]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(graph.get(x, ()))
        comps.append(sorted(comp))
    return comps


def summarize_map(rmap: dict) -> dict:
    return {
        "tables": {t["dataset_id"]: t["role"] for t in rmap["tables"]},
        "partitions": [{"stacked": g.get("stacked_dataset_id"), "members": g["members"]} for g in rmap["partitions"]],
        "strong_relations": [f"{r['child']['dataset_id']}.{'+'.join(r['child']['key'])} -> "
                             f"{r['parent']['dataset_id']}.{'+'.join(r['parent']['key'])} ({r['cardinality_observed']}, "
                             f"órfãos {r['integrity']['orphan_rows_pct'] or 0:.1%})"
                             for r in rmap["relations"] if r["strength"] == "strong"],
        "probable_relations": [r["relation_id"] for r in rmap["relations"] if r["strength"] == "probable"],
        "isolated": [t["dataset_id"] for t in rmap["tables"] if t["role"] == "isolada"],
        "traps": [t["kind"] for t in rmap["traps"]],
    }


# =========================================================================== junção verificada

class JoinError(RuntimeError):
    pass


def safe_join(ws: Workspace, left_id: str, right_id: str, left_on: list[str], right_on: list[str],
              how: str = "left", derived_id: str | None = None, aggregate_right: dict[str, str] | None = None,
              control_measures: list[str] | None = None, relation_id: str | None = None) -> dict:
    """Junção com verificação. ``aggregate_right`` ({coluna: agg}) agrega a direita ao grão da chave antes."""
    if how not in ("left", "inner"):
        raise JoinError("use 'left' (padrão) ou 'inner'; 'outer' exige motivo explícito e não é automático")
    L, R = ws.load_dataset(left_id), ws.load_dataset(right_id)
    lm, rm = ws.dataset_meta(left_id), ws.dataset_meta(right_id)
    lk = [f"__k{i}" for i in range(len(left_on))]
    for i, (a, b) in enumerate(zip(left_on, right_on)):
        L[lk[i]] = normalize_key(L[a])
        R[lk[i]] = normalize_key(R[b])
    if aggregate_right:
        R = R.groupby(lk, dropna=False).agg({c: a for c, a in aggregate_right.items()}).reset_index()
    R = R.drop(columns=[c for c in right_on if c in R.columns])  # a chave da direita é igual à da esquerda
    dup_right = int(R.duplicated(subset=lk).sum())
    if dup_right:
        raise JoinError(f"{right_id} repete a chave {right_on} em {dup_right} linhas: a junção multiplicaria "
                        f"linhas de {left_id} (fan-out). Agregue a direita (aggregate_right) ou inverta a junção.")
    sem_l = lm.get("semantic_types", {})
    controls = control_measures or [c for c, t in sem_l.items() if t == "measure"][:3]
    before = {c: float(pd.to_numeric(L[c], errors="coerce").sum()) for c in controls if c in L.columns}
    rows_before = len(L)
    rename = {}
    for c in R.columns:
        if c in lk:
            continue
        if c in L.columns or c.startswith("_"):
            rename[c] = f"{c}__{right_id}"
    R = R.rename(columns=rename)
    drop_right_keys = list(right_on)
    out = L.merge(R, on=lk, how=how, indicator=True)
    unmatched = int((out["_merge"] == "left_only").sum())
    unmatched_examples = sorted(map(str, out.loc[out["_merge"] == "left_only", lk[0]].dropna().unique()))[:10]
    out = out.drop(columns=lk + ["_merge"])
    after = {c: float(pd.to_numeric(out[c], errors="coerce").sum()) for c in before}
    control = [{"measure": f"{left_id}.{c}", "before": before[c], "after": after[c],
                "ok": bool(np.isclose(before[c], after[c], rtol=1e-12, atol=1e-9)) if how == "left" else None}
               for c in before]
    if how == "left" and len(out) != rows_before:
        raise JoinError(f"linhas mudaram de {rows_before} para {len(out)} numa junção left N:1")
    if how == "left" and any(c["ok"] is False for c in control):
        raise JoinError(f"totais de controle diferentes depois da junção: {control}")
    did = derived_id or f"{left_id}__{slug(right_id.replace('ds_', ''), 20)}"
    working = f"working/{did}.parquet"
    out.to_parquet(ws.path(working), index=False)
    sem = dict(sem_l)
    for c, t in rm.get("semantic_types", {}).items():
        sem[rename.get(c, c)] = t
    cols_meta = [*lm.get("columns", []), *[{**c, "name": rename.get(c["name"], c["name"])} for c in rm.get("columns", [])
                                           if c["name"] not in drop_right_keys]]
    meta = {"dataset_id": did, "kind": "derived", "source_file": None,
            "source_name": f"{lm.get('source_name')} + {rm.get('source_name')}", "source_sheet": None,
            "source_label": f"{lm.get('source_label')} + {rm.get('source_label')}",
            "working_path": working, "rows": int(len(out)), "columns": cols_meta, "parents": [left_id, right_id],
            "semantic_types": sem, "candidate_keys": lm.get("candidate_keys"),
            "observation_unit": lm.get("observation_unit")}
    ws.register_dataset(meta)
    rec = {
        "relation_id": relation_id or f"j_{did}",
        "left": {"dataset_id": left_id, "key": left_on}, "right": {"dataset_id": right_id, "key": right_on},
        "join_type": how, "right_aggregated": aggregate_right,
        "rows": {"left_before": rows_before, "after": int(len(out))},
        "control_totals": control,
        "unmatched": {"left": unmatched, "examples": unmatched_examples},
        "renamed_right_columns": rename,
        "derived_dataset_id": did,
    }
    ws.add_treatment("join", f"Junção {how} de {left_id} com {right_id} por {left_on}={right_on}", [did, left_id, right_id], rec)
    return rec
