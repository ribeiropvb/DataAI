"""Leitura de CSV e .xlsx (skill ingest-tabular).

Princípios: originais intocados, nenhuma linha descartada em silêncio, identificadores
preservados como texto, conversão de tipo só quando todos os valores convertem.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
from pathlib import Path

import pandas as pd

from ..envelope import envelope, question, warning
from ..workspace import Workspace
from .textutil import norm_name, slug, tokens

SUPPORTED = {".csv", ".txt", ".tsv", ".xlsx"}
MAX_FILES = 10  # [proposta MVP] P-002
MAX_TOTAL_BYTES = 50 * 1024 * 1024  # [proposta MVP] P-002
MALFORMED_CLARIFY_RATIO = 0.05

NA_MARKERS = {"", "na", "n/a", "null", "none", "-", "nan", "#n/a", "#null!", "--"}
ID_HINTS = {"id", "cod", "codigo", "code", "cpf", "cnpj", "cep", "zip", "matricula", "sku", "ean",
            "telefone", "phone", "celular", "rg", "chave", "key", "uuid", "protocolo", "placa"}
BOOL_TRUE = {"sim", "s", "true", "verdadeiro", "yes", "y", "t"}
BOOL_FALSE = {"nao", "não", "n", "false", "falso", "no", "f"}

_RE_EN = re.compile(r"^[-+]?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")
_RE_BR = re.compile(r"^[-+]?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?$")
_RE_PLAIN_INT = re.compile(r"^[-+]?\d+$")
_RE_LEADING_ZERO = re.compile(r"^0\d+$")
_CURRENCY = re.compile(r"^(R\$|US\$|\$|€|£)\s*|\s*(R\$|€)$")

DATE_FORMATS_DAYFIRST = ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"]
DATE_FORMATS_MONTHFIRST = ["%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S"]
DATE_FORMATS_ISO = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d",
                    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m"]


# --------------------------------------------------------------------------- CSV

def detect_encoding(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8"):
        try:
            raw.decode(enc)
            return "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
        except UnicodeDecodeError:
            continue
    try:
        raw.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        return "latin-1"


def detect_delimiter(text: str) -> str:
    """Escolhe o delimitador cujo número de campos é mais consistente nas primeiras linhas."""
    lines = [ln for ln in text.splitlines()[:50] if ln.strip()]
    best, best_score = ",", -1.0
    for d in (",", ";", "\t", "|"):
        try:
            counts = [len(r) for r in csv.reader(lines, delimiter=d)]
        except csv.Error:
            continue
        if not counts or max(counts) < 2:
            continue
        mode = max(set(counts), key=counts.count)
        score = counts.count(mode) / len(counts) + (0.001 * mode)
        if mode >= 2 and score > best_score:
            best, best_score = d, score
    return best


def _read_csv_rows(path: Path) -> tuple[list[str], list[list[str]], dict, list[dict], int, int]:
    raw = path.read_bytes()
    enc = detect_encoding(raw)
    text = raw.decode(enc)
    delim = detect_delimiter(text)
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    while rows and not any(c.strip() for c in rows[0]):
        rows.pop(0)
    if not rows:
        return [], [], {"encoding": enc, "delimiter": delim}, [], 0, 0
    header = rows[0]
    body, malformed, repeated = [], [], 0
    for i, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue
        if [c.strip() for c in r] == [c.strip() for c in header]:
            repeated += 1
            continue
        if len(r) != len(header):
            malformed.append({"line": i, "fields": len(r), "expected": len(header), "sample": delim.join(r)[:200]})
            continue
        body.append(r)
    return header, body, {"encoding": enc, "delimiter": delim}, malformed, repeated, len(rows) - 1


# --------------------------------------------------------------------------- Excel

def _cell_to_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dt.datetime,)):
        return v.isoformat(sep=" ") if (v.hour or v.minute or v.second) else v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float):
        return repr(int(v)) if v.is_integer() else repr(v)
    return str(v)


def _read_xlsx(path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Devolve (tabelas, abas_ignoradas, avisos). Cada tabela: sheet, header, body."""
    import openpyxl

    wb_val = openpyxl.load_workbook(path, data_only=True, read_only=False)
    try:
        wb_f = openpyxl.load_workbook(path, data_only=False, read_only=False)
    except Exception:  # pragma: no cover
        wb_f = None
    tables, ignored, warns = [], [], []
    for ws in wb_val.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        # remove linhas e colunas vazias nas pontas
        while rows and all(v is None or str(v).strip() == "" for v in rows[-1]):
            rows.pop()
        while rows and all(v is None or str(v).strip() == "" for v in rows[0]):
            rows.pop(0)
        if not rows:
            ignored.append({"sheet": ws.title, "reason": "aba vazia", "hidden": ws.sheet_state != "visible"})
            continue
        width = max(i + 1 for r in rows for i, v in enumerate(r) if v is not None and str(v).strip() != "")
        rows = [r[:width] + [None] * (width - len(r[:width])) for r in rows]
        reasons = []
        header_row = ws.min_row
        for rng in ws.merged_cells.ranges:
            if rng.min_row <= header_row <= rng.max_row:
                reasons.append("cabeçalho com células mescladas")
                break
        blank_inside = [i for i, r in enumerate(rows) if all(v is None or str(v).strip() == "" for v in r)]
        if blank_inside:
            reasons.append("linha vazia separando blocos (possíveis várias tabelas na aba)")
        sub = [i for i, r in enumerate(rows[1:], start=2)
               if any(isinstance(v, str) and re.match(r"^\s*(sub)?total\b", v, re.I) for v in r[:2])]
        if sub:
            reasons.append(f"linhas de total/subtotal (linhas {sub[:5]})")
        if reasons:
            ignored.append({"sheet": ws.title, "reason": "estrutura fora do suporte do MVP: " + "; ".join(reasons),
                            "hidden": ws.sheet_state != "visible"})
            continue
        missing_cache = 0
        if wb_f is not None:
            wsf = wb_f[ws.title]
            for row_f, row_v in zip(wsf.iter_rows(), ws.iter_rows()):
                for cf, cv in zip(row_f, row_v):
                    if isinstance(cf.value, str) and cf.value.startswith("=") and cv.value is None:
                        missing_cache += 1
        if missing_cache:
            warns.append(warning("excel_formula_without_value",
                                 f"Aba '{ws.title}': {missing_cache} fórmulas sem valor calculado salvo (ficaram ausentes)."))
        header = [_cell_to_text(v) for v in rows[0]]
        body = [[_cell_to_text(v) for v in r] for r in rows[1:]]
        tables.append({"sheet": ws.title, "header": header, "body": body,
                       "hidden": ws.sheet_state != "visible"})
    return tables, ignored, warns


# --------------------------------------------------------------------------- tipos

def _is_na(v: str) -> bool:
    return v.strip().lower() in NA_MARKERS


def _looks_identifier_name(name: str) -> bool:
    toks = set(tokens(name))
    return bool(toks & ID_HINTS) or norm_name(name).endswith("_id") or norm_name(name).startswith("id_")


def _parse_number(v: str, decimal: str) -> float | None:
    s = _CURRENCY.sub("", v.strip()).replace(" ", "").replace(" ", "")
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    if decimal == ",":
        if not _RE_BR.match(s):
            return None
        s = s.replace(".", "").replace(",", ".")
    else:
        if not _RE_EN.match(s):
            return None
        s = s.replace(",", "")
    try:
        x = float(s)
    except ValueError:
        return None
    return x / 100.0 if pct else x


def _number_convention(values: list[str]) -> str | None:
    """Decide o separador decimal de uma coluna: '.', ',' ou None (não numérica)."""
    en_ok = br_ok = True
    en_only = br_only = False
    for v in values:
        s = _CURRENCY.sub("", v.strip()).replace(" ", "").rstrip("%")
        e, b = bool(_RE_EN.match(s)), bool(_RE_BR.match(s))
        en_ok &= e
        br_ok &= b
        if e and not b:
            en_only = True
        if b and not e:
            br_only = True
        if not (en_ok or br_ok):
            return None
    if en_ok and (en_only or not br_ok):
        return "."
    if br_ok and (br_only or not en_ok):
        return ","
    return "ambiguous" if en_ok and br_ok else None


def _try_dates(values: list[str], formats: list[str]) -> str | None:
    for fmt in formats:
        try:
            for v in values:
                dt.datetime.strptime(v.strip(), fmt)
            return fmt
        except ValueError:
            continue
    return None


def infer_column(name: str, raw: list[str], default_decimal: str) -> tuple[pd.Series, dict]:
    """Converte uma coluna de texto. Devolve série e metadados (tipo, falhas, avisos)."""
    meta: dict = {"name": name, "dtype": "string", "conversion_failures": 0, "notes": []}
    vals = [None if _is_na(v) else v.strip() for v in raw]
    present = [v for v in vals if v is not None]
    meta["missing"] = len(vals) - len(present)
    series_text = pd.Series(vals, dtype="string")
    if not present:
        meta["notes"].append("coluna inteiramente ausente")
        return series_text, meta

    # identificadores: zeros à esquerda ou nome sugestivo com valores inteiros
    leading = sum(1 for v in present if _RE_LEADING_ZERO.match(v))
    if leading:
        meta["dtype"] = "string"
        meta["identifier_hint"] = True
        meta["notes"].append(f"{leading} valores com zeros à esquerda; mantida como texto")
        return series_text, meta
    if _looks_identifier_name(name) and all(_RE_PLAIN_INT.match(v) for v in present):
        meta["identifier_hint"] = True
        meta["notes"].append("nome sugere identificador; mantida como texto")
        return series_text, meta

    # booleanos
    low = {v.lower() for v in present}
    if len(low) <= 2 and low <= (BOOL_TRUE | BOOL_FALSE):
        meta["dtype"] = "boolean"
        return pd.Series([None if v is None else v.lower() in BOOL_TRUE for v in vals], dtype="boolean"), meta

    # números
    conv = _number_convention(present)
    if conv:
        dec = default_decimal if conv == "ambiguous" else conv
        if conv == "ambiguous":
            meta["notes"].append(f"separador decimal ambíguo; usado '{dec}' (convenção do arquivo)")
        nums = [None if v is None else _parse_number(v, dec) for v in vals]
        fails = sum(1 for v, x in zip(vals, nums) if v is not None and x is None)
        if fails == 0:
            meta["decimal"] = dec
            if any(v.strip().endswith("%") for v in present):
                meta["notes"].append("percentuais convertidos para fração (15% -> 0,15)")
                meta["unit"] = "fraction"
            if all(x is None or float(x).is_integer() for x in nums) and not any(dec in v for v in present):
                meta["dtype"] = "integer"
                return pd.Series(nums, dtype="Float64").astype("Int64"), meta
            meta["dtype"] = "float"
            return pd.Series(nums, dtype="Float64"), meta

    # datas
    fmt_iso = _try_dates(present, DATE_FORMATS_ISO)
    fmt_d = None if fmt_iso else _try_dates(present, DATE_FORMATS_DAYFIRST)
    fmt_m = None if fmt_iso else _try_dates(present, DATE_FORMATS_MONTHFIRST)
    fmt = fmt_iso or fmt_d or fmt_m
    if fmt:
        if fmt_d and fmt_m:
            meta["ambiguous_date_order"] = True
            meta["notes"].append("ordem dia/mês ambígua; usado dia/mês (padrão pt-BR) até confirmação")
            fmt = fmt_d
        parsed = pd.to_datetime(pd.Series(vals, dtype="object"), format=fmt, errors="coerce")
        meta["dtype"] = "datetime"
        meta["date_format"] = fmt
        return parsed, meta

    # texto: registra quantos falhariam como número, para o aviso
    numeric_like = sum(1 for v in present if _parse_number(v, default_decimal) is not None)
    if 0 < numeric_like < len(present) and numeric_like / len(present) > 0.8:
        meta["conversion_failures"] = len(present) - numeric_like
        meta["notes"].append(f"{meta['conversion_failures']} valores não numéricos impediram a conversão para número")
    return series_text, meta


def _file_default_decimal(delimiter: str) -> str:
    return "," if delimiter == ";" else "."


def _unique_names(header: list[str]) -> tuple[list[str], list[str]]:
    seen: dict[str, int] = {}
    out, notes = [], []
    for i, h in enumerate(header, start=1):
        name = h.strip() or f"coluna_{i}"
        if not h.strip():
            notes.append(f"coluna {i} sem nome recebeu '{name}'")
        if name in seen:
            seen[name] += 1
            new = f"{name}_{seen[name]}"
            notes.append(f"nome duplicado '{name}' renomeado para '{new}'")
            name = new
        else:
            seen[name] = 1
        out.append(name)
    return out, notes


def _build_dataset(ws: Workspace, dataset_id: str, header: list[str], body: list[list[str]],
                   default_decimal: str, file_rec: dict, sheet: str | None, read_options: dict,
                   malformed: list[dict], repeated: int) -> tuple[dict, list, list]:
    warns, questions = [], []
    names, name_notes = _unique_names(header)
    for n in name_notes:
        warns.append(warning("header_renamed", f"{dataset_id}: {n}"))
    cols, metas = {}, []
    for j, name in enumerate(names):
        raw = [r[j] if j < len(r) else "" for r in body]
        s, meta = infer_column(name, raw, default_decimal)
        meta["original_name"] = header[j]
        cols[name] = s
        metas.append(meta)
        if meta.get("ambiguous_date_order"):
            questions.append(question(
                f"q_date_{dataset_id}_{slug(name)}",
                f"Na coluna '{name}' de {file_rec['original_name']}, as datas estão no formato dia/mês ou mês/dia?",
                "Trocar dia e mês muda períodos, séries e prazos.",
                ["dia/mês", "mês/dia"], "dia/mês"))
        if meta.get("conversion_failures"):
            warns.append(warning("type_conversion_failed",
                                 f"{dataset_id}.{name}: {meta['conversion_failures']} valores impediram a conversão; coluna mantida como texto."))
    df = pd.DataFrame(cols)
    df["_source_file"] = file_rec["original_name"]
    df["_source_sheet"] = sheet or ""
    working = f"working/{dataset_id}.parquet"
    df.to_parquet(ws.path(working), index=False)
    if malformed:
        warns.append(warning("malformed_rows",
                             f"{dataset_id}: {len(malformed)} linhas com número de campos diferente do cabeçalho foram separadas (exemplos no resultado)."))
    if repeated:
        warns.append(warning("repeated_header", f"{dataset_id}: {repeated} repetições do cabeçalho no meio do arquivo foram removidas."))
    meta = {
        "dataset_id": dataset_id,
        "kind": "source",
        "source_file": file_rec["file"],
        "source_name": file_rec["original_name"],
        "source_sheet": sheet,
        "source_label": file_rec.get("source_label"),
        "sha256": file_rec["sha256"],
        "working_path": working,
        "read_options": read_options,
        "rows": int(len(df)),
        "columns": metas,
        "malformed_rows": {"count": len(malformed), "examples": malformed[:20]},
        "repeated_headers_removed": repeated,
        "parents": [],
    }
    ws.register_dataset(meta)
    ws.add_treatment("read_adjustment", f"Leitura de {file_rec['original_name']}" + (f" / aba {sheet}" if sheet else ""),
                     [dataset_id], {"read_options": read_options,
                                    "type_conversions": {m["name"]: m["dtype"] for m in metas},
                                    "malformed_rows_set_aside": len(malformed),
                                    "repeated_headers_removed": repeated})
    total = len(body) + len(malformed)
    if total and len(malformed) / total > MALFORMED_CLARIFY_RATIO:
        questions.append(question(
            f"q_malformed_{dataset_id}",
            f"{len(malformed)} de {total} linhas de {file_rec['original_name']} estão malformadas. Seguir sem elas?",
            "Mais de 5% das linhas ficaram de fora e podem mudar os resultados.",
            ["seguir sem elas", "parar e corrigir o arquivo"], None))
    return meta, warns, questions


def ingest(ws: Workspace) -> dict:
    """Lê todos os arquivos da análise e grava as cópias de trabalho em Parquet."""
    warns, questions, rejected, ignored, datasets = [], [], [], [], []
    files = ws.manifest["files"]
    if len(files) > MAX_FILES:
        warns.append(warning("too_many_files", f"{len(files)} arquivos; o limite proposto do MVP é {MAX_FILES}."))
    total = sum(f["bytes"] for f in files)
    if total > MAX_TOTAL_BYTES:
        warns.append(warning("too_large", f"{total / 1e6:.1f} MB somados; o limite proposto do MVP é 50 MB."))
    used_ids: set[str] = set()

    def new_id(base: str) -> str:
        i, cand = 1, base
        while cand in used_ids:
            i += 1
            cand = f"{base}_{i}"
        used_ids.add(cand)
        return cand

    for f in files:
        path = ws.path(f["file"])
        ext = path.suffix.lower()
        if ext not in SUPPORTED:
            rejected.append({"file": f["file"], "reason": f"formato {ext or '(sem extensão)'} fora do suporte do MVP"})
            continue
        try:
            if ext == ".xlsx":
                tables, ign, w = _read_xlsx(path)
                warns.extend(w)
                for item in ign:
                    ignored.append({"file": f["file"], **item})
                for t in tables:
                    did = new_id(f"ds_{slug(path.stem, 24)}_{slug(t['sheet'], 16)}" if len(tables) > 1 else f"ds_{slug(path.stem)}")
                    meta, w2, q2 = _build_dataset(ws, did, t["header"], t["body"], ".", f, t["sheet"],
                                                  {"format": "xlsx", "values": "valores calculados (data_only)",
                                                   "hidden_sheet": t["hidden"]}, [], 0)
                    datasets.append(meta)
                    warns += w2
                    questions += q2
            else:
                header, body, opts, malformed, repeated, _ = _read_csv_rows(path)
                if not header:
                    rejected.append({"file": f["file"], "reason": "arquivo vazio"})
                    continue
                dec = _file_default_decimal(opts["delimiter"])
                opts = {"format": "csv", **opts, "decimal_default": dec}
                did = new_id(f"ds_{slug(path.stem)}")
                meta, w2, q2 = _build_dataset(ws, did, header, body, dec, f, None, opts, malformed, repeated)
                datasets.append(meta)
                warns += w2
                questions += q2
        except ImportError as e:
            return envelope("ingest-tabular", "blocked", {"missing_dependency": str(e)})
        except Exception as e:  # leitura falhou: registra e segue com os demais (P-013)
            rejected.append({"file": f["file"], "reason": f"falha na leitura: {type(e).__name__}: {e}"})
    for r in rejected:
        warns.append(warning("file_rejected", f"{r['file']}: {r['reason']}", [r["file"]]))
    status = "completed" if datasets else "blocked"
    result = {
        "datasets": [{k: d[k] for k in ("dataset_id", "source_file", "source_sheet", "sha256", "working_path",
                                         "read_options", "rows", "columns", "malformed_rows")} for d in datasets],
        "rejected_files": rejected,
        "ignored_sheets": ignored,
    }
    env = envelope("ingest-tabular", status, result, warns, questions,
                   [d["working_path"] for d in datasets])
    ws.save_skill_output(env)
    return env
