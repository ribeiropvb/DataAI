"""Referências a números calculados.

O texto do relatório nunca traz números digitados pelo modelo. Ele usa marcadores que o código
substitui pelo valor do resultado::

    {{res_receita_mes:last_complete_value|currency_brl}}
    {{res_receita_loja:rows[group=Online].value|currency_brl}}
    {{res_conc_clientes:top20pct_items_share|percent_1}}

Constantes de definição de método (não são resultados) usam ``{{const:20%}}`` e só são aceitas se
estiverem em ``ALLOWED_CONSTANTS`` (limiares documentados em specs 12.7).

Caminho: nome em ``values`` (padrão), ``values.x``, ``n``, ``excluded`` ou ``rows[campo=valor].campo`` /
``rows[0].campo``. Formato: ver ``fmt.format_value``.
"""
from __future__ import annotations

import re

from .fmt import format_value

MARKER = re.compile(r"\{\{\s*([A-Za-z0-9_\-]+)\s*:\s*([^|}]+?)\s*(?:\|\s*([a-z0-9_]+)\s*)?\}\}")
_ROW = re.compile(r"^rows\[(.+?)\](?:\.(.+))?$")


ALLOWED_CONSTANTS = {"20%", "80%", "95%", "1,5", "1,5 × IQR", "30", "n < 30", "3,5", "10%", "0,3", "0,5", "100",
                     "0", "1", "50%", "90%", "5%"}


class RefError(KeyError):
    pass


def resolve_path(result: dict, path: str):
    path = path.strip()
    m = _ROW.match(path)
    if m:
        sel, field = m.group(1), m.group(2)
        rows = result.get("rows") or []
        if sel.isdigit() or (sel.startswith("-") and sel[1:].isdigit()):
            idx = int(sel)
            if not rows or idx >= len(rows) or -idx > len(rows):
                raise RefError(f"linha {sel} inexistente em {result.get('result_id')}")
            row = rows[idx]
        else:
            k, _, v = sel.partition("=")
            matches = [r for r in rows if str(r.get(k.strip())) == v.strip()]
            if not matches:
                raise RefError(f"linha com {k}={v} inexistente em {result.get('result_id')}")
            row = matches[0]
        if field is None:
            return row
        if field not in row:
            raise RefError(f"campo {field} inexistente na linha de {result.get('result_id')}")
        return row[field]
    if path in ("n", "excluded", "rows_filtered_out"):
        return result.get(path)
    key = path.removeprefix("values.")
    vals = result.get("values") or {}
    if key not in vals:
        raise RefError(f"valor '{key}' inexistente em {result.get('result_id')} (disponíveis: {sorted(vals)[:30]})")
    return vals[key]


def render_markers(text: str, load_result, refs: list | None = None, location: str = "") -> str:
    """Substitui marcadores pelos valores formatados. ``load_result(result_id) -> dict``.
    Registra cada substituição em ``refs`` (para ``number_refs`` e a auditoria)."""
    def sub(m):
        rid, path, fmt = m.group(1), m.group(2), m.group(3)
        if rid == "const":
            if path.strip() not in ALLOWED_CONSTANTS:
                raise RefError(f"constante não documentada: {path!r} (permitidas: {sorted(ALLOWED_CONSTANTS)})")
            if refs is not None:
                refs.append({"text": path.strip(), "result_id": "const", "path": path.strip(), "format": None, "raw": path.strip(),
                             "version": None, "location": location})
            return path.strip()
        try:
            res = load_result(rid)
        except FileNotFoundError as e:
            raise RefError(f"resultado inexistente: {rid}") from e
        value = resolve_path(res, path)
        txt = format_value(value, fmt)
        if refs is not None:
            refs.append({"text": txt, "result_id": rid, "path": path, "format": fmt, "raw": value,
                         "version": res.get("version"), "location": location})
        return txt
    return MARKER.sub(sub, text)


def unresolved_numbers(text: str) -> list[str]:
    """Números escritos diretamente (fora de marcadores), exceto anos, numeração de seção e n pequenos."""
    stripped = MARKER.sub("", text)
    out = []
    for m in re.finditer(r"(?<![\w{])\d[\d.,]*%?", stripped):
        tok = m.group(0).rstrip(".,")
        if re.fullmatch(r"(19|20)\d{2}", tok) or re.fullmatch(r"\d", tok):
            continue
        out.append(tok)
    return out
