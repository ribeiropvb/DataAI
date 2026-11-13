"""Gera o relatório PDF (skill write-analysis-report) com reportlab.

O agente redator entrega um documento estruturado (JSON) cujo texto usa marcadores
``{{result_id:caminho|formato}}``; este módulo substitui os marcadores pelos valores calculados,
renderiza os gráficos, numera seções e páginas e acrescenta o apêndice de definições e tratamentos.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from .. import theme
from ..workspace import Workspace, now_iso, sha256_file
from .charts import ColorMap, render_png
from .fmt import format_value
from .refs import RefError, render_markers, unresolved_numbers

ACCENT = theme.BRAND_STRONG


def _fonts():
    f = theme.register_pdf_fonts()
    return f["regular"], f["bold"]


def _styles():
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    reg, bold = _fonts()
    ss = getSampleStyleSheet()
    ink = HexColor(theme.INK)
    muted = HexColor(theme.INK_MUTED)
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName=bold, fontSize=26, leading=31, textColor=ink, alignment=0, spaceAfter=10),
        "subtitle": ParagraphStyle("st", parent=ss["Normal"], fontName=reg, fontSize=12.5, leading=17, textColor=muted),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName=bold, fontSize=15, leading=19, textColor=HexColor(ACCENT), spaceBefore=12, spaceAfter=6, keepWithNext=1),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=bold, fontSize=12, leading=15, textColor=ink, spaceBefore=8, spaceAfter=4, keepWithNext=1),
        "body": ParagraphStyle("b", parent=ss["Normal"], fontName=reg, fontSize=10.5, leading=15, textColor=ink, spaceAfter=6),
        "small": ParagraphStyle("s", parent=ss["Normal"], fontName=reg, fontSize=8.5, leading=11, textColor=muted),
        "caption": ParagraphStyle("c", parent=ss["Normal"], fontName=reg, fontSize=8.5, leading=11, textColor=muted, spaceAfter=8),
        "cell": ParagraphStyle("cell", parent=ss["Normal"], fontName=reg, fontSize=8.5, leading=10.5, textColor=ink),
        "cellb": ParagraphStyle("cellb", parent=ss["Normal"], fontName=bold, fontSize=8.5, leading=10.5, textColor=ink),
        "finding_title": ParagraphStyle("ft", parent=ss["Normal"], fontName=bold, fontSize=10.5, leading=14, textColor=HexColor(ACCENT)),
        "_fonts": (reg, bold),
    }


def _md(text: str) -> str:
    """Escapa HTML e aceita **negrito** e *itálico*."""
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    return t


def build_report(ws: Workspace, doc: dict, version: int, include_appendix: bool = True) -> dict:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)

    st = _styles()
    reg, bold = st["_fonts"]
    out_dir = ws.deliverable_dir(version)
    img_dir = ws.path(f"review/report_v{version}_charts")
    refs: list[dict] = []
    raw_numbers: list[dict] = []
    errors: list[str] = []
    used_results: list[str] = []
    charts_included: list[str] = []
    colors = ColorMap(doc.get("color_map"))

    def text(t: str, where: str) -> str:
        for tok in unresolved_numbers(t):
            raw_numbers.append({"location": where, "number": tok, "text": t[:120]})
        try:
            return render_markers(t, ws.load_result, refs, where)
        except (RefError, KeyError) as e:
            errors.append(f"{where}: {e}")
            return t

    story = []
    # capa
    story += [Spacer(1, 3.6 * cm), _logo_flowable(1.6 * cm), Spacer(1, 0.9 * cm), Paragraph(_md(doc["title"]), st["title"])]
    if doc.get("subtitle"):
        story.append(Paragraph(_md(text(doc["subtitle"], "capa")), st["subtitle"]))
    files = ", ".join(f["original_name"] for f in ws.manifest["files"])
    story += [Spacer(1, 1.2 * cm), Paragraph(f"Gerado em {now_iso()[:10]}", st["small"]),
              Paragraph(f"Arquivos analisados: {html.escape(files)}", st["small"]), PageBreak()]

    for si, sec in enumerate(doc.get("sections", []), start=1):
        where_sec = f"seção {si} ({sec.get('heading', '')})"
        story.append(Paragraph(f"{si}. {_md(sec['heading'])}", st["h1"]))
        for bi, b in enumerate(sec.get("blocks", []), start=1):
            where = f"{where_sec}, bloco {bi}"
            t = b.get("type", "paragraph")
            if t == "paragraph":
                story.append(Paragraph(_md(text(b["text"], where)), st["body"]))
            elif t == "subheading":
                story.append(Paragraph(_md(b["text"]), st["h2"]))
            elif t == "bullets":
                items = [ListItem(Paragraph(_md(text(it, where)), st["body"]), leftIndent=12) for it in b["items"]]
                story.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=12, bulletFontName=reg))
            elif t == "finding":
                rows = [[Paragraph(_md(text(b["title"], where)), st["finding_title"])]]
                for key, lab in (("magnitude", "Magnitude"), ("reference", "Comparação"), ("reliability", "Confiabilidade"),
                                 ("interpretation", "O que significa"), ("investigate", "Ponto a investigar")):
                    if b.get(key):
                        rows.append([Paragraph(f"<b>{lab}:</b> " + _md(text(b[key], where)), st["body"])])
                tb = Table(rows, colWidths=[16.5 * cm])
                tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor(theme.SURFACE_RAISED)),
                                        ("LINEABOVE", (0, 0), (-1, 0), 1.2, HexColor(theme.BRAND)),
                                        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                                        ("TOPPADDING", (0, 0), (0, 0), 7), ("TOPPADDING", (0, 1), (-1, -1), 3),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, -1), (-1, -1), 7)]))
                story += [KeepTogether([tb]), Spacer(1, 8)]
            elif t == "chart":
                try:
                    spec = ws.read_json(f"charts/{b['chart_id']}.json")
                    res = ws.load_result(spec["result_id"])
                except FileNotFoundError:
                    errors.append(f"{where}: gráfico {b['chart_id']} inexistente")
                    continue
                png = render_png(spec, res, img_dir / f"{spec['chart_id']}.png", colors)
                from PIL import Image as PILImage
                w_px, h_px = PILImage.open(png).size
                width = 16 * cm
                img = Image(png, width=width, height=width * h_px / w_px)
                parts = [img]
                cap = b.get("caption") or f"Fonte: {res.get('label')} ({spec['result_id']}), n = {{{{{spec['result_id']}:n|integer}}}}."
                parts.append(Paragraph(_md(text(cap, where)), st["caption"]))
                story.append(KeepTogether(parts))
                charts_included.append(spec["chart_id"])
                used_results.append(spec["result_id"])
            elif t == "table":
                res = ws.load_result(b["result_id"])
                used_results.append(b["result_id"])
                cols = b.get("columns") or list((res.get("rows") or [{}])[0].keys())[:6]
                labels, fmts = b.get("labels", {}), b.get("formats", {})
                data = [[Paragraph(html.escape(labels.get(c, c)), st["cellb"]) for c in cols]]
                for r in (res.get("rows") or [])[: b.get("max_rows", 15)]:
                    data.append([Paragraph(html.escape(format_value(r.get(c), fmts.get(c))), st["cell"]) for c in cols])
                tb = Table(data, repeatRows=1, colWidths=[16.5 * cm / len(cols)] * len(cols))
                tb.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.8, HexColor(theme.INK_MUTED)),
                                        ("LINEBELOW", (0, 1), (-1, -1), 0.3, HexColor(theme.LINE)),
                                        ("VALIGN", (0, 0), (-1, -1), "TOP")]))
                story += [tb, Paragraph(_md(b.get("caption") or f"Fonte: {res.get('label')} ({b['result_id']})."), st["caption"])]
            elif t == "tool_note":
                # aviso produzido por uma ferramenta: o texto (e seus números) precisa existir no manifesto
                known = {w.get("message") for w in ws.manifest.get("warnings", [])}
                if b["text"] not in known:
                    errors.append(f"{where}: tool_note não corresponde a nenhum aviso registrado pelas ferramentas")
                    continue
                story.append(Paragraph("• " + html.escape(b["text"]), st["body"]))
            elif t == "page_break":
                story.append(PageBreak())
            else:
                errors.append(f"{where}: tipo de bloco desconhecido '{t}'")
    for r in refs:
        if r["result_id"] != "const":
            used_results.append(r["result_id"])
    if include_appendix:
        story += _appendix(ws, sorted(set(used_results)), st, len(doc.get("sections", [])) + 1)

    def on_page(canvas, d):
        canvas.saveState()
        canvas.setFont(reg, 8)
        canvas.setFillColor(HexColor(theme.INK_MUTED))
        if d.page > 1:
            canvas.setStrokeColor(HexColor(theme.LINE))
            canvas.setLineWidth(0.5)
            canvas.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
            canvas.drawString(2 * cm, 1.2 * cm, ("DataAI · " + doc["title"])[:96])
            canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {d.page}")
        canvas.restoreState()

    path = out_dir / "report.pdf"
    pdf = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm, title=doc["title"], author="DataAI")
    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    from pypdf import PdfReader
    pages = len(PdfReader(str(path)).pages)
    rec = ws.add_deliverable("report", path, version, {"pages": pages, "charts_included": charts_included,
                                                       "number_refs": refs, "document": doc})
    ws.write_json(f"review/report_v{version}_document.json", doc)
    return {"stage": "artifact", "artifact_ref": rec["artifact_ref"], "version": version, "sha256": sha256_file(path),
            "pages": pages, "sections": [s["heading"] for s in doc.get("sections", [])], "charts_included": charts_included,
            "number_refs": refs, "renderer": "reportlab", "errors": errors, "raw_numbers": raw_numbers}


def _logo_flowable(size: float):
    """Símbolo do DataAI desenhado em vetor (mesma geometria de dataai/brand/dataai-marca-claro.svg)."""
    from reportlab.graphics.shapes import Circle, Drawing, Rect
    from reportlab.lib.colors import HexColor
    k = size / 64.0
    d = Drawing(size, size)
    y = lambda top, h: (64 - top - h) * k  # SVG tem origem no topo
    d.add(Rect(0, 0, 64 * k, 64 * k, rx=14 * k, ry=14 * k, fillColor=HexColor(theme.color("petroleo-600")), strokeColor=None))
    for x, top, w, h in ((13, 24, 10, 26), (27, 35, 10, 15), (42.5, 29, 5, 21)):
        d.add(Rect(x * k, y(top, h), w * k, h * k, rx=2.5 * k, ry=2.5 * k, fillColor=HexColor("#FFFFFF"), strokeColor=None))
    d.add(Circle(45 * k, (64 - 22) * k, 6.5 * k, fillColor=HexColor(theme.color("ocre-claro")), strokeColor=None))
    d.hAlign = "LEFT"
    return d


def _appendix(ws: Workspace, result_ids: list[str], st: dict, n: int) -> list:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, Table, TableStyle
    out = [PageBreak(), Paragraph(f"{n}. Apêndice: definições, tratamentos e ligações", st["h1"]),
           Paragraph("Definições das métricas citadas", st["h2"])]
    rows = [[Paragraph(h, st["cellb"]) for h in ("Métrica", "Fórmula e população", "Base", "Origem")]]
    for rid in result_ids:
        try:
            r = ws.load_result(rid)
        except FileNotFoundError:
            continue
        origin = "; ".join(f"{l.get('source_label') or l['dataset_id']} ({', '.join(l.get('columns', [])[:4])})" for l in r.get("lineage", []))
        formula = r.get("formula") or f"{r.get('function')} {r.get('spec', {}).get('params', {})}"
        pop = r.get("population") or ("filtros: " + str(r.get("filters")) if r.get("filters") else "todas as linhas")
        rows.append([Paragraph(html.escape(f"{r.get('label')} [{r.get('family')}]"), st["cell"]),
                     Paragraph(html.escape(f"{formula}. População: {pop}."), st["cell"]),
                     Paragraph(html.escape(f"n = {format_value(r.get('n'), 'integer')}; excluídos = {format_value(r.get('excluded'), 'integer')}"), st["cell"]),
                     Paragraph(html.escape(origin), st["cell"])])
    tb = Table(rows, colWidths=[3.6 * cm, 6.4 * cm, 2.8 * cm, 4.2 * cm], repeatRows=1)
    tb.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor(theme.LINE)), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    out.append(tb)
    out.append(Paragraph("Tratamentos aplicados aos dados", st["h2"]))
    for t in ws.manifest.get("treatments", []):
        out.append(Paragraph(html.escape(f"• {t['description']} ({t['kind']})"), st["small"]))
    try:
        rmap = ws.read_json("results/relationship_map.json")
        out.append(Paragraph("Tabelas e ligações encontradas entre os arquivos", st["h2"]))
        for tbl in rmap.get("tables", []):
            out.append(Paragraph(html.escape(f"• {tbl['dataset_id']}: {tbl['role']} ({tbl['rows']} linhas; {tbl.get('observation_unit') or ''}) — fonte {tbl.get('source')}"), st["small"]))
        for r in rmap.get("relations", []):
            if r["strength"] == "strong":
                i = r["integrity"]
                out.append(Paragraph(html.escape(
                    f"• {r['child']['dataset_id']}.{'+'.join(r['child']['key'])} → {r['parent']['dataset_id']}.{'+'.join(r['parent']['key'])}: "
                    f"{r['cardinality_label']}, correspondência {format_value(r['evidence']['containment'], 'percent_1')}, "
                    f"órfãos {format_value(i['orphan_rows_pct'] or 0, 'percent_1')}"), st["small"]))
    except FileNotFoundError:
        pass
    return out
