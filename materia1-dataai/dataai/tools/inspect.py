"""Inspeção das entregas geradas (usada por compose-dashboard, write-analysis-report,
validate-analysis e orchestrate-quality-review). Examina o arquivo real, não a descrição dele."""
from __future__ import annotations

import glob
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path

from .textutil import strip_accents

# Linguagem interpretativa proibida no dashboard (RN-006). Comparação sem acento e sem caixa.
NARRATIVE_PATTERNS = [
    r"\bdemonstr\w*", r"\bmostra(m)? que\b", r"\bindica(m)? que\b", r"\bsugere\w*", r"\bevidencia\w*",
    r"\brevela\w*", r"\bcomprova\w*", r"\bconclu\w*", r"\bportanto\b", r"\bisso significa\b", r"\bo que significa\b",
    r"\bdevido a\b", r"\bpor causa\b", r"\bcausou\b", r"\bresultou em\b", r"\bimpulsionad\w*", r"\bgracas a\b",
    r"\bpreocupante\w*", r"\bexcelente\w*", r"\botim[oa]s?\b", r"\bpessim[oa]s?\b", r"\balarmante\w*",
    r"\bsurpreendente\w*", r"\bdestaca(-se)?\b", r"\bdestaques?\b", r"\blidera\w*", r"\bmelhor desempenho\b",
    r"\bpior desempenho\b", r"\bsucesso\b", r"\bfracasso\b", r"\brecomend\w*", r"\bdeve-se\b", r"\bdevemos\b",
    r"\bsugerimos\b", r"\be necessario\b", r"\bconvem\b", r"\binsights?\b", r"\bresumo executivo\b",
    r"\bprincipais achados\b", r"\bachados?\b", r"\bpreocupa\w*", r"\bvale notar\b", r"\bveja que\b",
    r"\bshows? that\b", r"\bindicates?\b", r"\bsuggests?\b", r"\bkey findings?\b", r"\brecommend\w*", r"\bdue to\b",
]
_NARR = [re.compile(p) for p in NARRATIVE_PATTERNS]


def find_narrative(text: str) -> list[str]:
    t = strip_accents(text or "").lower()
    hits = []
    for rx in _NARR:
        m = rx.search(t)
        if m:
            hits.append(m.group(0))
    return hits


# =========================================================================== HTML estático

class _Collector(HTMLParser):
    """Coleta texto autoral (títulos, rótulos, cabeçalhos, atributos), separado de células de dados."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.authored: list[dict] = []
        self.data_cells = 0
        self.scripts: list[str] = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        a = dict(attrs)
        for k in ("title", "alt", "aria-label", "placeholder", "data-tooltip"):
            if a.get(k):
                self.authored.append({"where": f"<{tag} {k}>", "text": a[k]})
        if tag == "script":
            self._script = [] if a.get("type") in (None, "application/json", "text/javascript", "module") else None

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None
        while self.stack:
            if self.stack.pop() == tag:
                break

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)
            return
        text = data.strip()
        if not text or "style" in self.stack:
            return
        if "td" in self.stack:
            self.data_cells += 1
            return
        self.authored.append({"where": "/".join(self.stack[-3:]), "text": text})


def extract_dashboard_data(html: str) -> dict | None:
    m = re.search(r'<script[^>]+id="dataai-data"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def scan_dashboard_static(html_path: str | Path) -> dict:
    html = Path(html_path).read_text(encoding="utf-8")
    c = _Collector()
    c.feed(html)
    data = extract_dashboard_data(html)
    hits = []
    for item in c.authored:
        for h in find_narrative(item["text"]):
            hits.append({**item, "match": h})
    # títulos e rótulos dentro das opções dos gráficos (tooltips, nomes de eixo)
    if data:
        for ch in data.get("charts", []):
            for key in ("title", "alt_text"):
                for h in find_narrative(ch.get(key, "")):
                    hits.append({"where": f"chart {ch.get('chart_id')} {key}", "text": ch.get(key), "match": h})
            opt = json.dumps(ch.get("option", {}), ensure_ascii=False)
            for name in re.findall(r'"name":\s*"([^"]+)"', opt):
                for h in find_narrative(name):
                    hits.append({"where": f"chart {ch.get('chart_id')} eixo", "text": name, "match": h})
    return {"is_html": bool(re.search(r"<html", html, re.I)), "bytes": len(html.encode()),
            "authored_text_items": len(c.authored), "narrative_hits": hits, "embedded_data": data is not None,
            "has_paragraphs": len(re.findall(r"<p[\s>]", html)), "data_cells": c.data_cells}


# =========================================================================== navegador

def _chromium_path() -> str | None:
    env = os.environ.get("DATAAI_CHROMIUM")
    if env:
        return env
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux*/chrome",):
        found = sorted(glob.glob(pat))
        if found:
            return found[-1]
    return None


def launch_browser(p):
    try:
        return p.chromium.launch()
    except Exception:
        path = _chromium_path()
        if not path:
            raise
        return p.chromium.launch(executable_path=path, args=["--no-sandbox"])


def render_dashboard(html_path: str | Path, out_dir: str | Path, widths=(1440, 900, 390)) -> dict:
    """Abre o HTML em navegador headless, tira capturas, confere erros, rolagem horizontal,
    gráficos renderizados e abas. Sem Playwright: ``available: False`` (a revisão fica bloqueada)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"available": False, "reason": "playwright não instalado"}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"available": True, "screens": [], "console_errors": [], "horizontal_scroll": {},
                    "charts_rendered": {}, "tabs_tested": [], "tooltip_texts": []}
    url = Path(html_path).resolve().as_uri()
    with sync_playwright() as p:
        browser = launch_browser(p)
        for w in widths:
            page = browser.new_page(viewport={"width": w, "height": 900})
            page.on("console", lambda m: report["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: report["console_errors"].append(str(e)))
            page.goto(url)
            page.wait_for_timeout(1200)
            report["horizontal_scroll"][w] = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            tabs = page.query_selector_all("[data-view-tab]")
            views = [t.get_attribute("data-view-tab") for t in tabs] or [None]
            for v in views:
                if v is not None:
                    page.click(f'[data-view-tab="{v}"]')
                    page.wait_for_timeout(400)
                    if w == widths[0]:
                        report["tabs_tested"].append(v)
                stats = page.evaluate("""() => {
                    const boxes = [...document.querySelectorAll('[data-chart-id]')].filter(e => e.offsetParent !== null);
                    const painted = (c) => { try { const g=c.getContext('2d'); const d=g.getImageData(0,0,c.width,c.height).data; let n=0; for(let i=3;i<d.length;i+=64){ if(d[i]>0) n++; } return n>50; } catch(e){ return true; } };
                    return boxes.map(b => { const c=b.querySelector('canvas'); return {id: b.dataset.chartId, ok: !!c && b.clientHeight > 50 && painted(c)}; });
                }""")
                for s in stats:
                    report["charts_rendered"][s["id"]] = report["charts_rendered"].get(s["id"], False) or s["ok"]
                name = f"dashboard_{w}{'_' + v if v else ''}.png"
                page.screenshot(path=str(out_dir / name), full_page=True)
                report["screens"].append(str(out_dir / name))
                if w == widths[0]:
                    report["tooltip_texts"] += _hover_tooltips(page)
            page.close()
        browser.close()
    report["narrative_in_tooltips"] = [{"text": t, "match": h} for t in report["tooltip_texts"] for h in find_narrative(t)]
    return report


def _hover_tooltips(page) -> list[str]:
    texts = []
    for box in page.query_selector_all("[data-chart-id]"):
        if not box.is_visible():
            continue
        bb = box.bounding_box()
        if not bb:
            continue
        for fx in (0.35, 0.6):
            page.mouse.move(bb["x"] + bb["width"] * fx, bb["y"] + bb["height"] * 0.5)
            page.wait_for_timeout(120)
            tip = page.evaluate("""() => { const t=[...document.querySelectorAll('div')].find(d => d.style && d.style.zIndex==='9999999' && d.style.display!=='none' && d.innerText); return t ? t.innerText : null; }""")
            if tip:
                texts.append(tip)
    return list(dict.fromkeys(texts))


# =========================================================================== PDF

A4 = (595.28, 841.89)


def inspect_pdf(pdf_path: str | Path, out_dir: str | Path | None = None, scale: float = 1.4) -> dict:
    from pypdf import PdfReader
    rep: dict = {"is_pdf": False}
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        return {**rep, "error": f"{type(e).__name__}: {e}"}
    pages = []
    for i, pg in enumerate(reader.pages, start=1):
        w, h = float(pg.mediabox.width), float(pg.mediabox.height)
        text = pg.extract_text() or ""
        pages.append({"page": i, "width": w, "height": h, "is_a4": abs(w - A4[0]) < 2 and abs(h - A4[1]) < 2,
                      "chars": len(text), "text": text})
    rep.update({"is_pdf": True, "pages": len(pages), "page_info": [{k: v for k, v in p.items() if k != "text"} for p in pages],
                "text_by_page": [p["text"] for p in pages],
                "empty_pages": [p["page"] for p in pages if p["chars"] < 20]})
    if out_dir:
        try:
            import pypdfium2 as pdfium
            out = Path(out_dir)
            out.mkdir(parents=True, exist_ok=True)
            doc = pdfium.PdfDocument(str(pdf_path))
            imgs = []
            for i in range(len(doc)):
                img = doc[i].render(scale=scale).to_pil()
                pth = out / f"report_p{i + 1}.png"
                img.save(pth)
                imgs.append(str(pth))
            rep["page_images"] = imgs
        except Exception as e:  # pragma: no cover
            rep["page_images_error"] = str(e)
    return rep


_NUM = re.compile(r"(?<![\w/])[-−]?(?:R\$\s?)?\d{1,3}(?:\.\d{3})*(?:,\d+)?%?|(?<![\w/])[-−]?\d+(?:,\d+)?%?")


def numbers_in_text(text: str) -> list[str]:
    return [m.group(0).strip() for m in _NUM.finditer(text or "")]
