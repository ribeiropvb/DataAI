"""Perfil dos datasets (skill profile-data): unidade de observação, tipos semânticos,
qualidade (família M1), chaves candidatas e valores suspeitos. Observa; não altera dados."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from ..envelope import envelope, question, warning
from ..workspace import Workspace
from . import metrics
from .textutil import slug, tokens

TIME_PART_TOKENS = {"ano", "year", "mes", "month", "dia", "day", "trimestre", "quarter", "semana", "week", "hora", "hour"}
MEASURE_HINTS = {"valor", "value", "preco", "price", "qtd", "quantidade", "quantity", "total", "custo", "cost",
                 "receita", "revenue", "nota", "score", "peso", "weight", "idade", "age", "duracao", "tempo",
                 "frete", "desconto", "saldo", "amount", "meta", "target", "volume"}
ID_TOKENS = {"id", "cod", "codigo", "code", "key", "chave", "cpf", "cnpj", "cep", "matricula", "sku", "uuid"}
MAX_COMPOSITE = 3


def semantic_type(s: pd.Series, name: str, col_meta: dict | None = None) -> tuple[str, str]:
    """Devolve (tipo semântico, justificativa)."""
    col_meta = col_meta or {}
    toks = set(tokens(name))
    nn = s.dropna()
    if nn.empty:
        return "text", "coluna vazia"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime", "datas convertidas na leitura"
    if s.dtype == "boolean" or s.dtype == bool:
        return "boolean", "valores verdadeiro/falso"
    distinct = nn.nunique()
    ratio = distinct / len(nn)
    if pd.api.types.is_numeric_dtype(s):
        if set(pd.unique(nn)) <= {0, 1} and distinct == 2:
            return "boolean", "apenas 0 e 1"
        integral = bool((nn.astype(float) % 1 == 0).all())
        if toks & ID_TOKENS and integral:
            return "identifier", "nome sugere identificador"
        if toks & TIME_PART_TOKENS and integral and not toks & MEASURE_HINTS:
            return "category", "parte de data (ano/mês/dia)"
        if integral and ratio > 0.98 and distinct > 50 and not toks & MEASURE_HINTS and _is_sequence(nn):
            return "identifier", "inteiros únicos em sequência"
        return "measure", "numérica"
    # texto
    if col_meta.get("identifier_hint") or toks & ID_TOKENS:
        return "identifier", "nome ou formato de identificador"
    lens = nn.astype(str).str.len()
    spaces = nn.astype(str).str.contains(" ").mean()
    if lens.mean() > 40 or (spaces > 0.5 and ratio > 0.8 and lens.mean() > 20):
        return "text", "texto livre"
    if ratio > 0.95 and len(nn) > 20 and spaces < 0.2:
        return "identifier", "valores quase todos únicos"
    return "category", "texto com valores repetidos"


def _is_sequence(nn: pd.Series) -> bool:
    v = np.sort(nn.astype(float).unique())
    if len(v) < 3:
        return False
    d = np.diff(v)
    return bool((d == 1).mean() > 0.9)


def candidate_keys(df: pd.DataFrame, sem: dict[str, str], max_cols: int = MAX_COMPOSITE) -> list[list[str]]:
    cols = [c for c in df.columns if not c.startswith("_") and sem.get(c) not in ("measure", "text")
            and df[c].notna().all()]
    single = [[c] for c in cols if df[c].is_unique]
    if single:
        # identificadores primeiro
        return sorted(single, key=lambda k: (sem.get(k[0]) != "identifier", k[0]))
    pool = sorted(cols, key=lambda c: -df[c].nunique())[:10]
    found: list[list[str]] = []
    for r in range(2, max_cols + 1):
        for combo in itertools.combinations(pool, r):
            if any(set(f) <= set(combo) for f in found):
                continue
            if not df.duplicated(subset=list(combo)).any():
                found.append(list(combo))
        if found:
            break
    return found


def observation_unit(df: pd.DataFrame, keys: list[list[str]], sem: dict) -> dict:
    if keys:
        k = keys[0]
        if len(k) == 1:
            return {"description": f"uma linha por {k[0]}", "key": k, "confidence": "high",
                    "basis": f"{k[0]} é único e sem ausentes"}
        return {"description": f"uma linha por combinação de {' + '.join(k)}", "key": k, "confidence": "medium",
                "basis": "combinação única de colunas"}
    return {"description": "sem chave única: cada linha é um registro/evento", "key": [], "confidence": "low",
            "basis": "nenhuma coluna ou combinação de até 3 colunas é única"}


def _summary(s: pd.Series, st: str) -> dict:
    nn = s.dropna()
    if nn.empty:
        return {}
    if st == "measure":
        x = pd.to_numeric(nn, errors="coerce").astype(float)
        return {"min": float(x.min()), "max": float(x.max()), "mean": float(x.mean()), "median": float(x.median())}
    if st in ("category", "boolean"):
        vc = nn.astype(str).value_counts()
        return {"categories": int(vc.size), "top": [{"value": k[:60], "count": int(v)} for k, v in vc.head(10).items()]}
    if st == "datetime":
        return {"min": nn.min().isoformat(), "max": nn.max().isoformat()}
    return {}


def profile_dataset(ws: Workspace, dataset_id: str) -> tuple[dict, list, list]:
    meta = ws.dataset_meta(dataset_id)
    df = ws.load_dataset(dataset_id)
    col_meta = {c["name"]: c for c in meta.get("columns", [])}
    warns, questions = [], []
    cols = [c for c in df.columns if not c.startswith("_")]
    sem, basis = {}, {}
    for c in cols:
        sem[c], basis[c] = semantic_type(df[c], c, col_meta.get(c))
    keys = candidate_keys(df, sem)
    unit = observation_unit(df, keys, sem)
    meta["semantic_types"] = sem
    meta["candidate_keys"] = keys
    meta["observation_unit"] = unit
    ws.register_dataset(meta)

    measures = [c for c in cols if sem[c] == "measure"]
    dates = [c for c in cols if sem[c] == "datetime"]
    cats = [c for c in cols if sem[c] == "category"]
    non_neg = [c for c in measures if (pd.to_numeric(df[c], errors="coerce") >= 0).mean() >= 0.95]
    q_specs = [
        {"metric_id": f"q_completeness_{dataset_id}", "function": "quality_completeness", "params": {}},
        {"metric_id": f"q_uniqueness_{dataset_id}", "function": "quality_uniqueness", "params": {"keys": keys[:3]}},
        {"metric_id": f"q_validity_{dataset_id}", "function": "quality_validity",
         "params": {"dates": dates, "non_negative": non_neg}},
        {"metric_id": f"q_consistency_{dataset_id}", "function": "quality_consistency",
         "params": {"categories": cats, "date_pairs": metrics.infer_date_pairs(df, dates)}},
    ]
    if dates:
        main_date = max(dates, key=lambda c: df[c].notna().sum())
        q_specs.append({"metric_id": f"q_temporal_{dataset_id}", "function": "quality_temporal_coverage",
                        "params": {"date_col": main_date, "freq": "M"}})
    quality = {}
    for sp in q_specs:
        sp.update({"dataset_id": dataset_id, "label": f"Qualidade: {sp['function'].replace('quality_', '')} ({dataset_id})"})
        res = metrics.compute(sp, ws)
        quality[sp["function"]] = {"result_id": res["result_id"], "values": res["values"]}
        for r in res["rows"]:
            if r.get("violations"):
                warns.append(warning("data_quality", f"{dataset_id}.{r['column']}: {r['check']} ({r['violations']})",
                                     [res["path"]]))

    columns = []
    suspicious = []
    for c in cols:
        miss = int(df[c].isna().sum())
        info = {"name": c, "physical_type": col_meta.get(c, {}).get("dtype", str(df[c].dtype)),
                "semantic_type": sem[c], "semantic_basis": basis[c],
                "missing": {"count": miss, "pct": miss / len(df) if len(df) else None},
                "distinct": int(df[c].nunique()), "summary": _summary(df[c], sem[c]), "notes": col_meta.get(c, {}).get("notes", [])}
        if sem[c] == "measure":
            x = pd.to_numeric(df[c], errors="coerce").astype(float).dropna()
            if len(x) > 3:
                q1, q3 = np.quantile(x, [0.25, 0.75])
                iqr = q3 - q1
                out = int(((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)).sum())
                if out:
                    suspicious.append({"column": c, "issue": "valores extremos (fora de 1,5×IQR, só sinal)", "count": out})
                neg = int((x < 0).sum())
                if neg and c in non_neg:
                    suspicious.append({"column": c, "issue": "valores negativos em medida quase sempre positiva", "count": neg,
                                       "examples": x[x < 0].head(5).tolist()})
        if basis[c] == "valores quase todos únicos" or (sem[c] == "identifier" and col_meta.get(c, {}).get("dtype") in ("integer", "float")):
            info["notes"] = info["notes"] + ["tipo semântico inferido; confirmar se for medida"]
        columns.append(info)
        if miss / max(len(df), 1) > 0.3:
            warns.append(warning("high_missing", f"{dataset_id}.{c}: {miss / len(df):.0%} ausentes"))
    if unit["confidence"] == "low" and measures:
        warns.append(warning("no_unique_key", f"{dataset_id}: sem chave única; somas são por registro"))
    dup = quality["quality_uniqueness"]["values"]["duplicate_rows"]
    if dup:
        warns.append(warning("duplicate_rows", f"{dataset_id}: {dup} linhas totalmente duplicadas (não removidas; remover exige autorização)"))
        questions.append(question(f"q_dups_{slug(dataset_id)}",
                                  f"{dataset_id} tem {dup} linhas repetidas. Elas são registros legítimos ou duplicidade a remover?",
                                  "Remover duplicidades muda contagens e somas (P-004).",
                                  ["manter", "remover duplicadas"], "manter"))
    profile = {
        "dataset_id": dataset_id, "rows": int(len(df)), "columns_count": len(cols),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
        "observation_unit": unit, "columns": columns, "candidate_keys": keys,
        "quality": quality, "suspicious": suspicious,
        "role_hints": {"measures": measures, "dates": dates, "categories": cats,
                       "identifiers": [c for c in cols if sem[c] == "identifier"]},
    }
    ws.write_json(f"results/profile_{dataset_id}.json", profile)
    return profile, warns, questions


def applicable_families(profile: dict) -> dict[str, bool]:
    """Matriz de aplicabilidade das famílias M1–M15 (specs 12.7.4) para um dataset."""
    h = profile["role_hints"]
    m, d, c, i = bool(h["measures"]), bool(h["dates"]), bool(h["categories"]), bool(h["identifiers"])
    return {"M1": True, "M2": True, "M3": m, "M4": m, "M5": c, "M6": (c or i) and m, "M7": d,
            "M8": c and (m or True), "M9": True, "M10": d and c and m, "M11": i and d, "M12": len(h["dates"]) >= 2,
            "M13": (len(h["measures"]) + len(h["categories"])) >= 2, "M14": False, "M15": m}


def profile(ws: Workspace, dataset_ids: list[str] | None = None) -> dict:
    ids = dataset_ids or [d["dataset_id"] for d in ws.manifest["datasets"] if d.get("kind") in ("source", "stacked")]
    profiles, warns, questions = [], [], []
    for did in ids:
        p, w, q = profile_dataset(ws, did)
        p["applicable_families"] = applicable_families(p)
        ws.write_json(f"results/profile_{did}.json", p)
        profiles.append(p)
        warns += w
        questions += q
    env = envelope("profile-data", "completed", {"profiles": profiles}, warns, questions,
                   [f"results/profile_{d}.json" for d in ids])
    ws.save_skill_output(env)
    return env
