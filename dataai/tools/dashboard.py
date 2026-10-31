"""Gera o dashboard HTML (skill compose-dashboard). Um arquivo autossuficiente, dados embutidos,
sem narrativa interpretativa (RN-006). Números só de ``results/``."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .. import theme
from ..workspace import Workspace, now_iso, sha256_file
from .charts import ColorMap, echarts_option
from .fmt import format_value
from .inspect import find_narrative
from .refs import resolve_path

ECHARTS_VERSION = "5.5.1"
ECHARTS_CDN = f"https://cdn.jsdelivr.net/npm/echarts@{ECHARTS_VERSION}/dist/echarts.min.js"

_CSS = theme.css_variables() + """
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 """ + theme.FONT_STACK_SANS + """}
body{-webkit-font-smoothing:antialiased}
header{padding:24px 24px 8px;max-width:1360px;margin:0 auto;display:flex;gap:12px;align-items:flex-start}
header .mark{width:40px;height:40px;flex:none;margin-top:2px}header .mark svg{width:100%;height:100%;display:block}
header .mark .dark{display:none}
@media (prefers-color-scheme:dark){header .mark .light{display:none}header .mark .dark{display:block}}
h1{font-size:30px;line-height:36px;font-weight:600;letter-spacing:-.01em;margin:0 0 4px;text-wrap:balance}.meta{color:var(--muted);font-size:14px}
main{max-width:1360px;margin:0 auto;padding:8px 24px 32px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:16px 0 24px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:var(--shadow)}
.kpi .label{color:var(--muted);font-size:12px;line-height:16px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}
.kpi .value{font-size:32px;line-height:36px;font-weight:600;margin-top:6px;letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.kpi .sub{color:var(--muted);font-size:12px;margin-top:4px}
nav.tabs{display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin-bottom:16px}
nav.tabs button{font:inherit;font-size:14px;background:none;border:0;border-bottom:3px solid transparent;padding:10px 12px;color:var(--muted);cursor:pointer;border-radius:8px 8px 0 0}
nav.tabs button[aria-selected=true]{color:var(--ink);border-color:var(--accent);font-weight:600}
nav.tabs button:focus-visible,th:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.view{display:none}.view.active{display:block}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;grid-auto-flow:dense}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;min-width:0;box-shadow:var(--shadow)}
.card.wide{grid-column:span 2}.card.full{grid-column:1/-1}
.card h3{font-size:16px;line-height:22px;font-weight:500;margin:0 0 8px;text-wrap:balance}
.chart{width:100%;height:320px}
.src{margin-top:8px;color:var(--muted);font-size:12px;line-height:16px}
.src code,footer code{font-family:""" + theme.FONT_STACK_MONO + """;font-size:12px;background:var(--raised);border:1px solid var(--line);border-radius:4px;padding:1px 6px;color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
th{cursor:pointer;color:var(--muted);font-weight:600;position:sticky;top:0;background:var(--raised)}td.num{text-align:right;font-variant-numeric:tabular-nums}
.tablewrap{max-height:420px;overflow:auto}
footer{max-width:1360px;margin:0 auto;padding:0 24px 24px;color:var(--muted);font-size:12px}
@media (max-width:1100px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.card.wide{grid-column:1/-1}}
@media (max-width:700px){.grid{grid-template-columns:1fr}.card.wide,.card.full{grid-column:auto}header,main,footer{padding-left:16px;padding-right:16px}h1{font-size:24px;line-height:30px}.kpi .value{font-size:26px}.chart{height:280px}}
"""

_JS = r"""
(function(){
const D = JSON.parse(document.getElementById('dataai-data').textContent);
const nf = (d) => new Intl.NumberFormat('pt-BR', {minimumFractionDigits:d, maximumFractionDigits:d});
function compact(v){const a=Math.abs(v);if(a>=1e9)return nf(1).format(v/1e9)+' bi';if(a>=1e6)return nf(1).format(v/1e6)+' mi';if(a>=1e3)return nf(1).format(v/1e3)+' mil';return nf(Number.isInteger(v)?0:2).format(v);}
function F(v,f){ if(v===null||v===undefined||Number.isNaN(v))return '—'; if(typeof v!=='number')return String(v);
  switch(f){case 'integer':return nf(0).format(Math.round(v));case 'decimal_1':return nf(1).format(v);case 'percent_0':return nf(0).format(v*100)+'%';
  case 'percent_1':return nf(1).format(v*100)+'%';case 'percent_2':return nf(2).format(v*100)+'%';case 'currency_brl':return 'R$ '+nf(2).format(v);
  case 'currency_brl_compact':return 'R$ '+compact(v);case 'compact':return compact(v);case 'days':return nf(1).format(v)+' dias';case 'index':return nf(0).format(v);
  default:return nf(Number.isInteger(v)?0:2).format(v);} }
window.__dataaiFormat = F;
const DARK = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function themed(opt){
  if(!DARK) return opt;
  let s = JSON.stringify(opt);
  for(const [a,b] of Object.entries(D.palette_dark||{})) s = s.split('"'+a+'"').join('"'+b+'"');
  return JSON.parse(s);
}
function prep(opt){
  opt = themed(opt);
  const f = opt._fmt; delete opt._fmt;
  const ink=css('--ink'), muted=css('--muted'), grid=css('--grid-line');
  opt.textStyle = {fontFamily: getComputedStyle(document.body).fontFamily, color: muted};
  const axisStyle = (ax) => { if(!ax) return; (Array.isArray(ax)?ax:[ax]).forEach(a => {
    a.axisLine = Object.assign({lineStyle:{color:grid}}, a.axisLine); a.axisTick = Object.assign({show:false}, a.axisTick);
    a.splitLine = Object.assign({lineStyle:{color:grid}}, a.splitLine); a.axisLabel = Object.assign({color:muted}, a.axisLabel);
    a.nameTextStyle = Object.assign({color:muted}, a.nameTextStyle); }); };
  axisStyle(opt.xAxis); axisStyle(opt.yAxis);
  (opt.series||[]).forEach(s => { if(s.label && s.label.show) s.label.color = s.type==='heatmap' ? undefined : ink;
    if(s.type==='bar' && !s.stack) s.itemStyle = Object.assign({borderRadius: s.data && opt.yAxis && opt.yAxis.type==='category' ? [0,4,4,0] : [4,4,0,0]}, s.itemStyle); });
  if(opt.tooltip) opt.tooltip = Object.assign({backgroundColor: css('--card'), borderColor: css('--line'), textStyle:{color:ink}}, opt.tooltip);
  const C = (x) => x==='currency_brl' ? 'currency_brl_compact' : x;
  const axisFmt = (ax) => { if(!ax) return; (Array.isArray(ax)?ax:[ax]).forEach(a => { a.axisLabel=Object.assign({hideOverlap:true},a.axisLabel); if(a.type==='value'){ const af=a._fmt||f; delete a._fmt; a.axisLabel.formatter=(v)=>F(v, C(af)); } }); };
  axisFmt(opt.xAxis); axisFmt(opt.yAxis);
  if(opt.visualMap){ const vf=opt.visualMap._fmt; delete opt.visualMap._fmt; opt.visualMap.formatter=(v)=>F(v,vf); }
  (opt.series||[]).forEach(s => { const sf=s._fmt||f; delete s._fmt;
    s.tooltip = Object.assign({}, s.tooltip, {valueFormatter:(v)=>F(v,sf)});
    if(s.label && s.label.show){ s.label.formatter = (p)=>F(p.value && p.value.length===3 ? p.value[2] : (typeof p.value==='object'&&p.value!==null?p.value.value:p.value), C(sf)); }
    if(s.data){ s.data = s.data.map(d => { if(d && typeof d==='object' && !Array.isArray(d) && '_signed' in d){ const sv=d._signed; delete d._signed; d.tooltip={valueFormatter:()=>F(sv,sf)}; } return d; }); }
  });
  if(opt.tooltip && opt.tooltip.trigger==='item' && opt.series && opt.series[0] && opt.series[0].type==='heatmap'){
    const vf=f; opt.tooltip.formatter=(p)=>{const x=opt.xAxis.data[p.value[0]], y=opt.yAxis.data[p.value[1]]; return y+' · '+x+': '+F(p.value[2],vf);};
  }
  return opt;
}
const charts = {};
function draw(scope){
  scope.querySelectorAll('[data-chart-id]').forEach(el => {
    if(el.offsetParent===null) return;
    const id = el.dataset.chartId; const c = D.charts.find(x => x.chart_id===id); if(!c) return;
    if(!charts[id]){ charts[id] = echarts.init(el, null, {renderer:'canvas'}); charts[id].setOption(prep(JSON.parse(JSON.stringify(c.option)))); }
    else charts[id].resize();
  });
}
document.querySelectorAll('[data-view-tab]').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('[data-view-tab]').forEach(b => b.setAttribute('aria-selected', b===btn));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id==='view-'+btn.dataset.viewTab));
  draw(document.getElementById('view-'+btn.dataset.viewTab));
}));
document.querySelectorAll('table[data-sortable] th').forEach((th, i) => th.addEventListener('click', () => {
  const tb = th.closest('table').tBodies[0]; const rows=[...tb.rows]; const asc = th.dataset.asc!=='1'; th.dataset.asc = asc?'1':'0';
  rows.sort((a,b)=>{const x=a.cells[i].dataset.v, y=b.cells[i].dataset.v; const nx=parseFloat(x), ny=parseFloat(y);
    const r = (!isNaN(nx)&&!isNaN(ny)) ? nx-ny : String(x).localeCompare(String(y),'pt-BR'); return asc?r:-r;});
  rows.forEach(r=>tb.appendChild(r));
}));
window.addEventListener('resize', () => Object.values(charts).forEach(c => c.resize()));
draw(document);
})();
"""


def _b64(text: str) -> str:
    import base64
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _inline_svg(variant: str) -> str:
    svg = theme.logo_svg(variant)
    return svg.replace('role="img" aria-label="DataAI"', 'aria-hidden="true" focusable="false"')


class DashboardError(ValueError):
    pass


def _slug_view(name: str) -> str:
    from .textutil import slug
    return slug(name, 30)


def build_dashboard(ws: Workspace, config: dict, version: int, inline_library: str | Path | None = None) -> dict:
    """``config``::

        {"title": "...", "subtitle": "...",
         "kpis": [{"label": "Receita", "result_id": "res_x", "path": "total", "format": "currency_brl_compact"}],
         "views": [{"name": "Vendas", "charts": [{"chart_id": "ch_x", "size": "wide"}]}],
         "detail_table": {"result_id": "res_y", "columns": ["group", "value"], "labels": {...}, "formats": {...}}}
    """
    problems = []
    for txt in [config.get("title", ""), config.get("subtitle", "")] + [k.get("label", "") for k in config.get("kpis", [])] \
            + [v.get("name", "") for v in config.get("views", [])]:
        for h in find_narrative(txt):
            problems.append(f"texto interpretativo '{h}' em '{txt}'")
    if problems:
        raise DashboardError("; ".join(problems))
    colors = ColorMap(config.get("color_map"))
    kpis = []
    for k in config.get("kpis", []):
        res = ws.load_result(k["result_id"])
        v = resolve_path(res, k.get("path", "value"))
        kpis.append({"label": k["label"], "value": v, "format": k.get("format"), "text": format_value(v, k.get("format")),
                     "sub": k.get("sub", ""), "result_id": k["result_id"], "path": k.get("path"), "version": res.get("version")})
    charts_data, views_html, used = [], [], []
    for vi, view in enumerate(config.get("views", [])):
        cards = []
        for item in view.get("charts", []):
            item = {"chart_id": item} if isinstance(item, str) else item
            spec = ws.read_json(f"charts/{item['chart_id']}.json")
            res = ws.load_result(spec["result_id"])
            size = item.get("size") or ("full" if spec["type"] in ("heatmap",) else "wide" if spec["type"] in ("line", "pareto", "waterfall") else "")
            if spec["type"] == "table":
                cards.append(_table_card(spec, res, size or "full"))
            elif spec["type"] == "kpi":
                continue
            else:
                opt = echarts_option(spec, res, colors)
                charts_data.append({"chart_id": spec["chart_id"], "title": spec["title"], "result_id": spec["result_id"],
                                    "result_version": res.get("version"), "alt_text": spec.get("alt_text", ""), "option": opt})
                h = 260 + 22 * max(0, min(14, len(res.get("rows") or [])) - 8) if spec["type"] == "bar_horizontal" else 320
                cards.append(f'<section class="card {size}"><h3>{html.escape(spec["title"])}</h3>'
                             f'<div class="chart" style="height:{h}px" data-chart-id="{spec["chart_id"]}" role="img" '
                             f'aria-label="{html.escape(spec.get("alt_text") or spec["title"])}"></div>'
                             f'<div class="src">Calculado em <code>{html.escape(spec["result_id"])}</code></div></section>')
            used.append(spec["chart_id"])
        vid = _slug_view(view["name"])
        views_html.append(f'<div class="view{" active" if vi == 0 else ""}" id="view-{vid}"><div class="grid">{"".join(cards)}</div></div>')
    if config.get("detail_table"):
        dt = config["detail_table"]
        res = ws.load_result(dt["result_id"])
        views_html[-1] = views_html[-1].replace("</div></div>", _table_card({"title": dt.get("title", res.get("label")), "columns": dt["columns"],
                                                                              "labels": dt.get("labels", {}), "formats": dt.get("formats", {})}, res, "full") + "</div></div>", 1)
    tabs = ""
    if len(config.get("views", [])) > 1:
        tabs = '<nav class="tabs" role="tablist">' + "".join(
            f'<button role="tab" data-view-tab="{_slug_view(v["name"])}" aria-selected="{"true" if i == 0 else "false"}">{html.escape(v["name"])}</button>'
            for i, v in enumerate(config["views"])) + "</nav>"
    light, dark = theme.data_palette("claro"), theme.data_palette("escuro")
    palette_dark = {a: b for key in ("categorical", "sequential", "diverging") for a, b in zip(light[key], dark[key])}
    palette_dark[light["neutral"]] = dark["neutral"]
    data = {"generated_at": now_iso(), "analysis_id": ws.manifest["analysis_id"], "kpis": kpis, "charts": charts_data,
            "library": f"echarts@{ECHARTS_VERSION}", "palette_dark": palette_dark}
    import os
    inline_library = inline_library or os.environ.get("DATAAI_ECHARTS_JS")  # modo offline: biblioteca embutida
    lib = (f"<script>{Path(inline_library).read_text(encoding='utf-8')}</script>" if inline_library
           else f'<script src="{ECHARTS_CDN}"></script>')
    kpi_html = "".join(f'<div class="kpi"><div class="label">{html.escape(k["label"])}</div><div class="value">{html.escape(k["text"])}</div>'
                       + (f'<div class="sub">{html.escape(k["sub"])}</div>' if k["sub"] else "") + "</div>" for k in kpis)
    sources = ", ".join(sorted({f["original_name"] for f in ws.manifest["files"]}))
    doc = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(config["title"])}</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,{_b64(theme.logo_svg("claro"))}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="{theme.GOOGLE_FONTS_URL}">
<style>{_CSS}</style></head>
<body><header><div class="mark" aria-hidden="true"><span class="light">{_inline_svg("claro")}</span><span class="dark">{_inline_svg("escuro")}</span></div>
<div><h1>{html.escape(config["title"])}</h1><div class="meta">{html.escape(config.get("subtitle", ""))}</div></div></header>
<main><div class="kpis">{kpi_html}</div>{tabs}{"".join(views_html)}</main>
<footer>Gerado pelo DataAI em {html.escape(data["generated_at"][:10])} · Fonte: {html.escape(sources)}</footer>
<script type="application/json" id="dataai-data">{json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")}</script>
{lib}<script>{_JS}</script></body></html>"""
    path = ws.deliverable_dir(version) / "dashboard.html"
    path.write_text(doc, encoding="utf-8")
    rec = ws.add_deliverable("dashboard", path, version, {"charts_included": used, "views": [v["name"] for v in config.get("views", [])],
                                                          "library": f"echarts@{ECHARTS_VERSION}", "config": config})
    return {"stage": "artifact", "artifact_ref": rec["artifact_ref"], "version": version, "sha256": sha256_file(path),
            "views": rec["views"], "charts_included": used, "library": rec["library"]}


def _table_card(spec: dict, res: dict, size: str) -> str:
    cols = spec.get("columns") or list((res.get("rows") or [{}])[0].keys())[:6]
    labels = spec.get("labels", {})
    formats = spec.get("formats", {})
    head = "".join(f"<th>{html.escape(labels.get(c, c))}</th>" for c in cols)
    body = []
    for r in (res.get("rows") or [])[: spec.get("max_rows", 200)]:
        tds = []
        for c in cols:
            v = r.get(c)
            num = isinstance(v, (int, float)) and not isinstance(v, bool)
            tds.append(f'<td class="{"num" if num else ""}" data-v="{html.escape(str(v))}">{html.escape(format_value(v, formats.get(c)))}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    return (f'<section class="card {size}"><h3>{html.escape(spec["title"])}</h3><div class="tablewrap"><table data-sortable>'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div></section>")
