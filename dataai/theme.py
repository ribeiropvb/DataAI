"""Identidade visual do DataAI (skill brand-identity).

Fonte única dos valores: ``dataai/brand/tokens.json``. Dashboard, PDF e gráficos leem as cores, as
fontes e o símbolo daqui; nenhum outro módulo deve ter cor escrita à mão.

- ``color(nome, tema)``: valor de um token de cor (resolve apelidos como ``{petroleo-600}``).
- ``CATEGORICAL``, ``SEQUENTIAL``, ``DIVERGING``, ``PRIMARY``, ``NEUTRAL``: cores de dados do tema claro
  (o PDF e o padrão do dashboard). ``data_palette("escuro")`` dá as do tema escuro.
- ``css_variables()``: variáveis CSS dos dois temas para o dashboard.
- ``logo_svg(variante)``: o símbolo (``claro``, ``escuro`` ou ``mono``).
- ``register_pdf_fonts()`` e ``matplotlib_font()``: IBM Plex embutida, com DejaVu Sans como reserva.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

BRAND_DIR = Path(__file__).resolve().parent / "brand"
FONT_DIR = BRAND_DIR / "fonts"
THEMES = ("claro", "escuro")


@lru_cache(maxsize=1)
def tokens() -> dict:
    return json.loads((BRAND_DIR / "tokens.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _colors() -> dict[str, dict | str]:
    return {t["name"]: t["value"] for t in tokens()["color"]["tokens"]}


def color(name: str, theme: str = "claro") -> str:
    """Valor hexadecimal do token ``name`` no tema dado; o tema ausente herda o claro."""
    seen = set()
    while True:
        if name in seen:
            raise ValueError(f"apelido circular em {name}")
        seen.add(name)
        val = _colors()[name]
        if isinstance(val, dict):
            val = val.get(theme, val[THEMES[0]])
        m = re.fullmatch(r"\{(.+)\}", val)
        if not m:
            return val
        name = m.group(1)


def data_palette(theme: str = "claro") -> dict:
    return {
        "categorical": [color(f"dados-{i}", theme) for i in range(1, 9)],
        "sequential": [color(f"dados-seq-{i}", theme) for i in range(1, 6)],
        "diverging": [color(f"dados-div-{i}", theme) for i in range(1, 6)],
        "neutral": color("dados-outros", theme),
        "grid": color("dados-grade", theme),
    }


_P = data_palette("claro")
PRIMARY: str = _P["categorical"][0]
CATEGORICAL: list[str] = _P["categorical"]
SEQUENTIAL: list[str] = _P["sequential"]
DIVERGING: list[str] = _P["diverging"]
NEUTRAL: str = _P["neutral"]
GRID: str = _P["grid"]
# variação positiva/negativa (cascata): lados da escala divergente, sem julgamento de bom/ruim
INCREASE: str = DIVERGING[-1]
DECREASE: str = DIVERGING[0]
INK = color("tinta")
INK_MUTED = color("tinta-suave")
BRAND = color("marca")
BRAND_STRONG = color("marca-forte")
LINE = color("linha")
SURFACE_RAISED = color("superficie-elevada")
WARNING = color("atencao")

FONT_STACK_SANS = tokens()["type"]["families"]["sans"]
FONT_STACK_MONO = tokens()["type"]["families"]["mono"]
GOOGLE_FONTS_URL = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500"
                    "&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap")

# nomes de token de cor -> variável CSS curta usada no dashboard
_CSS_ROLES = {
    "bg": "fundo", "card": "superficie", "raised": "superficie-elevada", "line": "linha", "ink": "tinta",
    "muted": "tinta-suave", "accent": "marca", "accent-strong": "marca-forte", "on-accent": "sobre-marca",
    "focus": "foco", "warn": "atencao", "warn-bg": "atencao-fundo", "grid-line": "dados-grade",
}


def css_variables() -> str:
    """Blocos ``:root`` (claro) e ``prefers-color-scheme: dark`` (escuro) com as variáveis do dashboard."""
    def block(theme: str) -> str:
        return ";".join(f"--{k}:{color(v, theme)}" for k, v in _CSS_ROLES.items())
    light = block("claro") + ";--shadow:" + _shadow("claro")
    dark = block("escuro") + ";--shadow:" + _shadow("escuro")
    return (f":root{{{light};color-scheme:light}}"
            f"@media (prefers-color-scheme:dark){{:root{{{dark};color-scheme:dark}}}}")


def _shadow(theme: str) -> str:
    for t in tokens().get("shadow", {}).get("tokens", []):
        if t["name"] == "sombra-cartao":
            v = t["value"]
            return v.get(theme, v["claro"]) if isinstance(v, dict) else v
    return "none"


def logo_svg(variant: str = "claro") -> str:
    return (BRAND_DIR / f"dataai-marca-{variant}.svg").read_text(encoding="utf-8")


def logo_path(variant: str = "claro") -> Path:
    return BRAND_DIR / f"dataai-marca-{variant}.svg"


_PLEX = {"regular": "IBMPlexSans-Regular.ttf", "italic": "IBMPlexSans-Italic.ttf", "medium": "IBMPlexSans-Medium.ttf",
         "bold": "IBMPlexSans-SemiBold.ttf", "bolditalic": "IBMPlexSans-SemiBoldItalic.ttf",
         "mono": "IBMPlexMono-Regular.ttf"}


def plex_available() -> bool:
    return all((FONT_DIR / f).exists() for f in _PLEX.values())


def register_pdf_fonts() -> dict:
    """Registra as fontes no ReportLab. Devolve ``{"regular", "bold", "medium", "mono"}`` com os nomes registrados."""
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    registered = pdfmetrics.getRegisteredFontNames()
    if plex_available():
        names = {"regular": "Plex", "italic": "Plex-Italic", "bold": "Plex-SemiBold", "bolditalic": "Plex-SemiBoldItalic",
                 "medium": "Plex-Medium", "mono": "PlexMono"}
        if "Plex" not in registered:
            for key, fname in names.items():
                pdfmetrics.registerFont(TTFont(fname, str(FONT_DIR / _PLEX[key])))
            addMapping("Plex", 0, 0, "Plex")
            addMapping("Plex", 1, 0, "Plex-SemiBold")
            addMapping("Plex", 0, 1, "Plex-Italic")
            addMapping("Plex", 1, 1, "Plex-SemiBoldItalic")
        return {"regular": "Plex", "bold": "Plex-SemiBold", "medium": "Plex-Medium", "mono": "PlexMono"}
    try:  # reserva: DejaVu do matplotlib
        import matplotlib
        base = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        if "DejaVu" not in registered:
            pdfmetrics.registerFont(TTFont("DejaVu", str(base / "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(base / "DejaVuSans-Bold.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(base / "DejaVuSans-Oblique.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVuMono", str(base / "DejaVuSansMono.ttf")))
            addMapping("DejaVu", 0, 0, "DejaVu")
            addMapping("DejaVu", 1, 0, "DejaVu-Bold")
            addMapping("DejaVu", 0, 1, "DejaVu-Oblique")
            addMapping("DejaVu", 1, 1, "DejaVu-Bold")
        return {"regular": "DejaVu", "bold": "DejaVu-Bold", "medium": "DejaVu-Bold", "mono": "DejaVuMono"}
    except Exception:  # pragma: no cover
        return {"regular": "Helvetica", "bold": "Helvetica-Bold", "medium": "Helvetica-Bold", "mono": "Courier"}


def matplotlib_font() -> str:
    """Registra a IBM Plex Sans no matplotlib (se presente) e devolve o nome da família a usar."""
    if not plex_available():
        return "DejaVu Sans"
    from matplotlib import font_manager
    known = {f.name for f in font_manager.fontManager.ttflist}
    if "IBM Plex Sans" not in known:
        for key in ("regular", "italic", "medium", "bold", "bolditalic"):
            font_manager.fontManager.addfont(str(FONT_DIR / _PLEX[key]))
    return "IBM Plex Sans"
