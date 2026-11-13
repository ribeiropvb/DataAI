"""Normalização de nomes e textos usada por várias ferramentas."""
from __future__ import annotations

import re
import unicodedata

_STOP_KEY_TOKENS = {"id", "cod", "codigo", "code", "key", "chave", "fk", "pk", "nr", "num", "numero", "no", "n"}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def norm_name(text: str) -> str:
    """Nome normalizado: sem acento, minúsculo, separadores viram ``_``."""
    t = strip_accents(str(text)).lower().strip()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return t.strip("_")


def slug(text: str, maxlen: int = 40) -> str:
    return norm_name(text)[:maxlen] or "x"


def tokens(text: str) -> list[str]:
    return [t for t in norm_name(text).split("_") if t]


def singular(token: str) -> str:
    """Singular aproximado (pt/en) para comparar nomes de tabelas e colunas."""
    for suf, rep in (("oes", "ao"), ("aes", "ao"), ("ies", "y"), ("res", "r"), ("is", "l"), ("s", "")):
        if len(token) > 3 and token.endswith(suf):
            return token[: -len(suf)] + rep
    return token


def key_tokens(text: str) -> set[str]:
    return {singular(t) for t in tokens(text) if t not in _STOP_KEY_TOKENS}
