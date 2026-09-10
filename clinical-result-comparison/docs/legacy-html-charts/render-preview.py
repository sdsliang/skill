#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEMP preview generator (v0.12 debug): chart JSON (chart-visualization-json
protocol) -> self-contained HTML preview fragment for the Tool Smith chat page.

WHY (temporary): the deployed Tool Smith front-end has no chart-visualization-json
renderer yet, so a .json visualization is not drawn in the chat. The chat page
renders an .html fragment natively. Until the real renderer lands, the report
body should therefore reference <name>.preview.html (generated below) instead of
<name>.json; the .json stays the formal contract and is delivered alongside.
This file is a TEMP debug asset: it is removed (and the report references revert
to .json) once the renderer is live. It is not part of the final contract.

Single source of truth: this script reads ONE validated chart JSON and embeds
the exact same JSON text into a data script block (no hand-copying of numbers
into a second structure), so JSON and preview HTML can never drift.

Usage:
    python3 render-preview.py <chart.json>                # writes stdout
    python3 render-preview.py <chart.json> -o out.html    # writes out.html

Output is a Tool Smith HTML fragment: it carries no document wrappers
(no doctype/html/head/body tags), and neither the text nor any string/comment
literal contains those wrapper substrings (the Tool Smith front-end rejects any
fragment whose whole text matches such a substring anywhere).
Embedding escapes the "</" sequence inside the JSON text so it cannot close the
data script block prematurely.
"""
import json, os, sys

def _bad_wrapper_substrs(text):
    """Return any forbidden document-wrapper substring found (fragment rule)."""
    bad = []
    for s in ("doctype html", "<html", "<head", "<body", "html>",
              "</html", "</head", "</body"):
        if s in text:
            bad.append(s)
    return bad

def main():
    args = sys.argv[1:]
    out = None
    if "-o" in args:
        i = args.index("-o")
        try:
            out = args[i + 1]
        except IndexError:
            sys.stderr.write("error: -o requires a filename\n")
            return 2
        del args[i:i + 2]
    if not args:
        sys.stderr.write(
            "usage: python3 render-preview.py <chart.json> [-o out.html]\n")
        return 2
    path = args[0]
    try:
        with open(path, encoding="utf-8") as fh:
            chart = json.load(fh)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("error reading JSON: %s\n" % e)
        return 2
    ctype = chart.get("type")
    if ctype not in ("line", "bar", "timeline"):
        sys.stderr.write(f"unsupported chart type: {ctype!r}\n")
        return 2
    # Embed the JSON text verbatim; escape the sequence "</" so it cannot close
    # the data script block prematurely.
    data_text = json.dumps(chart, ensure_ascii=False, separators=(",", ":"))
    data_text = data_text.replace("</", "<\\/")
    html = TEMPLATE.replace("__CHART_JSON__", data_text)
    # Fragment-safety self-check before emitting.
    bad = _bad_wrapper_substrs(html)
    if bad:
        sys.stderr.write("fragment check FAILED, forbidden substrings: %s\n" % bad)
        return 2
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(html)
        sys.stderr.write("wrote %s (%d bytes)\n" % (out, len(html)))
    else:
        sys.stdout.write(html)
    return 0

# ---------------------------------------------------------------------------
# Template (fragment-safe: no document-wrapper tags nor any string/comment
# literal containing those wrapper substrings).
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!-- Tool Smith HTML fragment preview (TEMP debug renderer for chart JSON protocol v1.0.7)
     Data = embedded chart JSON (<script type="application/json"> below). Not the final renderer. -->
<style>
:root{--brand-bg:#F4F5F2;--brand-surface:#FFFFFF;--brand-text:#172321;--brand-muted:rgba(23,35,33,.64);--brand-faint:rgba(23,35,33,.38);--brand-border:rgba(23,35,33,.14);--brand-s1:#087F76;--brand-s2:#D65A45;--brand-s3:#4C6F91;--brand-s4:#D49A3A;--brand-s5:#9BB8B0}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--viz-background,var(--brand-bg))}
body{font-family:var(--font-sans,"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif);color:var(--viz-text,var(--brand-text));-webkit-font-smoothing:antialiased;padding:18px 16px}
.chart{background:var(--viz-surface,var(--viz-background,var(--brand-surface)));border:1px solid var(--viz-border,var(--brand-border));border-radius:14px;padding:24px 26px 16px;max-width:980px;margin:0 auto;position:relative;box-shadow:0 8px 26px rgba(23,35,33,.06)}
.badge{display:inline-flex;align-items:center;font-size:9px;font-weight:800;letter-spacing:.12em;padding:5px 9px;border-radius:5px;margin-bottom:12px;border:1px solid rgba(8,127,118,.24);color:var(--viz-series-1,var(--brand-s1));background:rgba(8,127,118,.08)}
h1{font-size:19px;font-weight:750;letter-spacing:0;line-height:1.35;color:var(--viz-text,var(--brand-text))}
.sub{font-size:12px;color:var(--viz-text-muted,var(--brand-muted));margin-top:5px;line-height:1.65}
.desc{font-size:11px;color:var(--viz-text-muted,var(--brand-muted));margin-top:12px;line-height:1.65;border-left:3px solid var(--viz-series-1,var(--brand-s1));padding:2px 0 2px 11px;max-width:760px}
.stage{position:relative;width:100%;margin:18px 0 2px;overflow:hidden}
.stage svg{display:block;width:100%;height:auto;overflow:visible}
svg text{font-family:inherit}
.legend{display:flex;flex-wrap:wrap;align-items:center;gap:7px 18px;margin:10px 0 2px;font-size:11px;color:var(--viz-text-muted,var(--brand-muted))}
.legend .lg{display:inline-flex;align-items:center;gap:7px}
.legend .dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--viz-series-1,var(--brand-s1));box-shadow:0 0 0 3px rgba(8,127,118,.12)}
.legend .hint{margin-left:auto;font-size:10px;opacity:.8}
.src{margin-top:12px;padding-top:10px;border-top:1px solid var(--viz-border,var(--brand-border));font-size:10px;color:var(--viz-text-faint,var(--brand-faint));line-height:1.5;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.src b{font-weight:700;color:var(--viz-text-muted,var(--brand-muted))}
.tip{position:fixed;z-index:9;max-width:320px;background:var(--viz-text,var(--brand-text));color:var(--viz-background,var(--brand-bg));border:1px solid rgba(255,255,255,.14);border-radius:8px;padding:9px 11px;font-size:11px;line-height:1.55;box-shadow:0 8px 24px rgba(23,35,33,.18);opacity:0;pointer-events:none;transition:opacity .12s}
.tip.on{opacity:1}
.tip .tt{font-weight:750;margin-bottom:3px;color:#8ED6CA}
@media (max-width:620px){body{padding:10px 8px}.chart{padding:18px 14px 13px;border-radius:11px}h1{font-size:17px}.stage{margin-top:13px}.legend .hint{width:100%;margin-left:0}}


<div class="chart">
  <span class="badge" id="badge">CHART PREVIEW</span>
  <h1 id="title"></h1>
  <div class="sub" id="subtitle"></div>
  <div class="desc" id="describe"></div>
  <div class="stage" id="stage"></div>
  <div class="legend" id="legend"></div>
  <div class="src"><span id="datasrc"></span><span id="note"></span></div>
</div>
<div class="tip" id="tip"></div>

<script type="application/json" id="chartjson">__CHART_JSON__</script>
<script>
(function(){
  var CFG = JSON.parse(document.getElementById("chartjson").textContent);
  var esc = function(s){ return String(s==null?"":s).replace(/[<>&]/g,function(c){return{"<":"&lt;",">":"&gt;","&":"&amp;"}[c];}); };
  function viz(name, fb){ var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); return v || fb; }
  function pick(c, fb){ return (c && c.indexOf("--viz")===0) ? viz(c, fb) : (c || fb); }
  var INK = viz("--viz-text","#172321");
  var PAPER = viz("--viz-background","#F4F5F2");
  var MUTED = viz("--viz-text-muted","rgba(23,35,33,.64)");
  var FAINT = viz("--viz-text-faint","rgba(23,35,33,.38)");
  var GRID = viz("--viz-border","rgba(23,35,33,.14)");
  var SER = [viz("--viz-series-1","#087F76"), viz("--viz-series-2","#D65A45"), viz("--viz-series-3","#4C6F91"), viz("--viz-series-4","#D49A3A"), viz("--viz-series-5","#9BB8B0")];
  var SHADES = ["#174E4B","#12635D","#087F76","#269288","#4C6F91","#6586A1","#D49A3A","#C17F2C","#D65A45","#DF765F","#9BB8B0","#C7DAD4"];
  var TYPE = CFG.type || "";
  var BADGE = {line:"ENDPOINT TREND", bar:"ENDPOINT BAR", timeline:"EVIDENCE TIMELINE"}[TYPE] || "CHART";
  document.getElementById("badge").textContent = BADGE;
  document.getElementById("title").textContent = CFG.title || "";
  document.getElementById("subtitle").textContent = CFG.subTitle || "";
  var dd = document.getElementById("describe");
  if (CFG.describe){ dd.innerHTML = "<b>说明：</b>" + esc(CFG.describe); } else { dd.style.display="none"; }
  var ds = document.getElementById("datasrc");
  if (CFG.dataSource){ ds.innerHTML = "<b>数据来源：</b>" + esc(CFG.dataSource); } else { ds.style.display="none"; }
  var note = document.getElementById("note");
  note.textContent = "HTML 预览为临时调试件（近似渲染，非最终 renderer）· 数据与 chart JSON 完全一致";
  var stage = document.getElementById("stage");
  var legendBox = document.getElementById("legend");
  function wrap(s, per, cap){ s=String(s==null?"":s); if(s.length<=per) return [s]; var a=[],i=0; while(i<s.length){ a.push(s.slice(i,i+per)); i+=per; if(a.length>=(cap||3)) break;} return a; }
  function wrapLines(s, per){ s=String(s==null?"":s); if(!s) return []; var out=[],segs=s.split("\n"),i,seg; for(i=0;i<segs.length;i++){seg=segs[i];if(!seg)continue; out=out.concat(wrap(seg,per,3)); if(out.length>=3)break;} return out.slice(0,3); }
  var NS="http://www.w3.org/2000/svg";
  function el(n){ return document.createElementNS(NS,n); }
  function tipShow(html){ var t=document.getElementById("tip"); t.innerHTML=html; t.classList.add("on"); }
  function tipHide(){ document.getElementById("tip").classList.remove("on"); }
  function tipMove(evt){ var t=document.getElementById("tip"),rr=t.getBoundingClientRect(); var x2=evt.clientX+14,y2=evt.clientY-10; if(x2+rr.width>window.innerWidth-8)x2=evt.clientX-rr.width-14; t.style.left=x2+"px"; t.style.top=y2+"px"; }
  function bindTip(node, html){ node.style.cursor="pointer"; node.addEventListener("mouseenter",function(){tipShow(html);}); node.addEventListener("mousemove",tipMove); node.addEventListener("mouseleave",tipHide); }
  function scaleColor(v){ var idx=Math.max(0,Math.min(11,Math.round(v))); return SHADES[idx]; }

  if (TYPE === "line") { renderLine(); }
  else if (TYPE === "bar") { renderBar(); }
  else if (TYPE === "timeline") { renderTimeline(); }

  /* ---------------- LINE ---------------- */
  function renderLine(){
    var rows = CFG.data || [];
    if (!rows.length) return;
    // group rows into series by `group` (or single series when absent), keep first-seen order
    var order=[], map={};
    rows.forEach(function(r){ var g=(r.group==null)?"":String(r.group); if(!(g in map)){ map[g]=[]; order.push(g);} map[g].push(r); });
    var series = order.map(function(g){ return { name: g || "值", rows: map[g] }; });
    // x categories: union of labels, keep first-seen order
    var xcat=[], seen={};
    rows.forEach(function(r){ var l=String(r.label==null?"":r.label); if(!(l in seen)){seen[l]=1;xcat.push(l);} });
    var single = series.every(function(s){ return s.rows.length<=1; });
    var W=900,H=320,padL=64,padR=30,padT=34,padB=46;
    var plotW=W-padL-padR, plotH=H-padT-padB;
    // value domain
    var vals=rows.map(function(r){return r.value;});
    var vmin=Math.min.apply(null,vals), vmax=Math.max.apply(null,vals);
    var span=(vmax-vmin)||1; vmin-=(vmax-vmin)*.08; vmax+=(vmax-vmin)*.08+0.0001; if(span===0){vmin-=1;vmax+=1;}
    var X=function(i){ return padL+plotW*(xcat.length<=1?0.5:i/(xcat.length-1)); };
    var Y=function(v){ return padT+plotH*(1-(v-vmin)/(vmax-vmin)); };
    var svg=el("svg"); svg.setAttribute("viewBox","0 0 "+W+" "+H); svg.setAttribute("role","img");
    // gridlines + y labels
    var g0=el("g");
    for(var t=0;t<=4;t++){ var gv=vmin+(vmax-vmin)*t/4; var y=Y(gv); g0.innerHTML+='<line x1="'+padL+'" y1="'+y+'" x2="'+(W-padR)+'" y2="'+y+'" stroke="'+GRID+'" stroke-width="1" opacity=".55"/>'+'<text x="'+(padL-8)+'" y="'+(y+3)+'" text-anchor="end" font-size="10" fill="'+MUTED+'">'+esc((Math.round(gv*100)/100)+"")+'</text>'; }
    svg.appendChild(g0);
    // x category ticks
    xcat.forEach(function(l,i){ var x=X(i); var t2=el("g"); t2.innerHTML='<text x="'+x+'" y="'+(H-padB+16)+'" text-anchor="middle" font-size="10.5" font-weight="600" fill="'+MUTED+'">'+esc(wrap(l,9,2).join("\n"))+'</text>'; svg.appendChild(t2); });
    if (CFG.axisXTitle){ var ax=el("text"); ax.setAttribute("x",padL+plotW/2); ax.setAttribute("y",H-8); ax.setAttribute("text-anchor","middle"); ax.setAttribute("font-size","10"); ax.setAttribute("fill",FAINT); ax.textContent=CFG.axisXTitle; svg.appendChild(ax); }
    if (CFG.axisYTitle){ var ay=el("text"); ay.setAttribute("transform","rotate(-90 14 "+(padT+plotH/2)+")"); ay.setAttribute("x",14); ay.setAttribute("y",padT+plotH/2); ay.setAttribute("text-anchor","middle"); ay.setAttribute("font-size","10"); ay.setAttribute("fill",FAINT); ay.textContent=CFG.axisYTitle; svg.appendChild(ay); }
    // per-series polyline
    series.forEach(function(s,si){
      var col=pick(s.color,SER[si%SER.length]);
      var pts=s.rows.map(function(r){ var xi=xcat.indexOf(String(r.label==null?"":r.label)); return [X(xi),Y(r.value)]; });
      // legend
      var lg=document.createElement("span"); lg.className="lg"; lg.innerHTML='<span class="dot" style="background:'+col+'"></span>'+esc(s.name); legendBox.appendChild(lg);
      if(!single && pts.length>1){
        var pl=el("polyline"); pl.setAttribute("points",pts.map(function(p){return p[0]+","+p[1];}).join(" ")); pl.setAttribute("fill","none"); pl.setAttribute("stroke",col); pl.setAttribute("stroke-width","2"); pl.setAttribute("stroke-linejoin","round"); pl.setAttribute("stroke-linecap","round"); svg.appendChild(pl);
      }
      // points + labels + hover
      s.rows.forEach(function(r,pi){
        var px=pts[pi][0], py=pts[pi][1];
        var grp=el("g"); var hollow=single;
        grp.innerHTML=(hollow?'<circle cx="'+px+'" cy="'+py+'" r="5.5" fill="'+PAPER+'" stroke="'+col+'" stroke-width="2.4"/>':'<circle cx="'+px+'" cy="'+py+'" r="4.2" fill="'+col+'"/>')+'<text x="'+px+'" y="'+(py-10)+'" text-anchor="middle" font-size="10.5" font-weight="800" fill="'+col+'" paint-order="stroke" stroke="'+PAPER+'" stroke-width="3px">'+esc(String(r.value))+'</text>';
        svg.appendChild(grp);
        var tip='<div class="tt">'+esc(s.name)+'</div><div style="opacity:.85">'+esc(String(r.label==null?"":r.label))+' · '+esc(String(r.value))+'</div>'+(r.description?'<div style="opacity:.85">'+esc(r.description)+'</div>':"");
        bindTip(grp, tip);
      });
    });
    stage.appendChild(svg);
  }

  /* ---------------- BAR ---------------- */
  function renderBar(){
    var rows=(CFG.data||[]).slice(); if(!rows.length)return;
    var horizontal=(CFG.direction||"horizontal")!=="vertical";
    var maxV=0; rows.forEach(function(b){ if(Math.abs(b.value)>maxV)maxV=Math.abs(b.value); });
    var W=900,H=Math.max(200,46+rows.length*54+20),padL=horizontal?Math.max(150,0):64,padR=44,padT=30,padB=52;
    var plotW=W-padL-padR;
    var plotH=H-padT-padB;
    var svg=el("svg"); svg.setAttribute("viewBox","0 0 "+W+" "+H); svg.setAttribute("role","img");
    function barColor(b){ if(b.color)return pick(b.color,viz("--viz-series-1","#087F76")); var r=maxV?Math.abs(b.value)/maxV:0; return scaleColor(1+r*10); }
    if (horizontal){
      var inner=plotW/(maxV||1);
      rows.forEach(function(b,i){
        var y=padT+i*(plotH/rows.length);
        var bw=Math.max(6,plotH/rows.length-12);
        var len=b.value*inner;
        var g=el("g");
        var col=barColor(b);
        var rect=el("rect"); rect.setAttribute("x",padL+(b.value>=0?0:len)); rect.setAttribute("y",y); rect.setAttribute("width",Math.abs(len)); rect.setAttribute("height",bw); rect.setAttribute("rx","4"); rect.setAttribute("fill",col);
        g.appendChild(rect);
        g.innerHTML+='<text x="'+(b.value>=0?padL+Math.abs(len)+8:padL-8)+'" y="'+(y+bw/2+4)+'" text-anchor="'+(b.value>=0?"start":"end")+'" font-size="11.5" font-weight="800" fill="'+col+'">'+esc(String(b.value))+'</text>';
        g.innerHTML+='<text x="'+(padL-10)+'" y="'+(y+bw/2+4)+'" text-anchor="end" font-size="11" font-weight="600" fill="'+INK+'">'+esc(wrap(b.label,26,2).join("\n"))+'</text>';
        svg.appendChild(g);
        var tip='<div class="tt">'+esc(b.label)+'</div><div style="font-weight:800;white-space:pre-line">'+esc(String(b.value))+'</div>'+(b.description?'<div style="opacity:.85">'+esc(b.description)+'</div>':"");
        bindTip(g, tip);
      });
      if(CFG.axisXTitle){ var t1=el("text"); t1.setAttribute("x",padL+plotW/2); t1.setAttribute("y",H-14); t1.setAttribute("text-anchor","middle"); t1.setAttribute("font-size","10"); t1.setAttribute("fill",FAINT); t1.textContent=CFG.axisXTitle; svg.appendChild(t1); }
    } else {
      var inner=plotH/(maxV||1);
      rows.forEach(function(b,i){
        var x=padL+i*(plotW/rows.length);
        var bw=Math.max(6,plotW/rows.length-14);
        var bh=b.value*inner;
        var col=barColor(b);
        var g=el("g");
        var rect=el("rect"); rect.setAttribute("x",x); rect.setAttribute("y",padT+plotH-bh); rect.setAttribute("width",bw); rect.setAttribute("height",bh); rect.setAttribute("rx","3"); rect.setAttribute("fill",col);
        g.appendChild(rect);
        g.innerHTML+='<text x="'+(x+bw/2)+'" y="'+(padT+plotH-bh-6)+'" text-anchor="middle" font-size="11" font-weight="800" fill="'+col+'">'+esc(String(b.value))+'</text>';
        svg.appendChild(g);
        var tip='<div class="tt">'+esc(b.label)+'</div><div style="font-weight:800">'+esc(String(b.value))+'</div>'+(b.description?'<div style="opacity:.85">'+esc(b.description)+'</div>':"");
        bindTip(g, tip);
        // x label under bar
        var xl=el("g"); var sp="";
        wrap(b.label,8,2).forEach(function(ln,k){ sp+='<tspan x="'+(x+bw/2)+'" y="'+(H-padB+16+k*12)+'">'+esc(ln)+'</tspan>'; });
        xl.innerHTML='<text text-anchor="middle" font-size="10" fill="'+MUTED+'">'+sp+'</text>'; svg.appendChild(xl);
      });
      if(CFG.axisYTitle){ var t2=el("text"); t2.setAttribute("x",W-10); t2.setAttribute("y",padT-8); t2.setAttribute("text-anchor","end"); t2.setAttribute("font-size","10"); t2.setAttribute("fill",FAINT); t2.textContent=CFG.axisYTitle; svg.appendChild(t2); }
      if(CFG.axisXTitle){ var t3=el("text"); t3.setAttribute("x",padL+plotW/2); t3.setAttribute("y",H-8); t3.setAttribute("text-anchor","middle"); t3.setAttribute("font-size","10"); t3.setAttribute("fill",FAINT); t3.textContent=CFG.axisXTitle; svg.appendChild(t3); }
    }
    stage.appendChild(svg);
  }

  /* ---------------- TIMELINE ---------------- */
  function renderTimeline(){
    var ev=(CFG.data||[]); if(!ev.length)return;
    var legend=(CFG.legend||[]);
    var W=CFG.width||920, H=CFG.height||300;
    var padL=40,padR=40; var baseY=Math.round(H*0.68);
    var plotW=W-padL-padR;
    function x(i){ return padL+plotW*(ev.length===1?0.5:i/(ev.length-1)); }
    function kindMeta(k){
      var m=null; legend.forEach(function(l){ if(l.key===k)m=l; });
      if(!m) return {label:k,shape:"circle",color:viz("--viz-series-1","#087F76")};
      return {label:m.label,shape:m.shape||"circle",color:pick(m.color,SER[legend.indexOf(m)%SER.length])};
    }
    function rad(e){ var w=(e.weight==null?0:e.weight); return 6+Math.min(Math.max(w,0),5)*1.5; }
    function anchorFor(i){ return i===0?"start":(i===ev.length-1?"end":"middle"); }
    function axFor(i){ return i===0?padL+2:(i===ev.length-1?W-padR-2:x(i)); }
    var spacing=plotW/Math.max(1,ev.length-1);
    var labelPer=Math.max(6,Math.min(12,Math.round(spacing/14)));
    var svg=el("svg"); svg.setAttribute("viewBox","0 0 "+W+" "+H); svg.setAttribute("role","img");
    var g=el("g");
    g.innerHTML='<line x1="'+padL+'" y1="'+baseY+'" x2="'+(W-padR)+'" y2="'+baseY+'" stroke="'+GRID+'" stroke-width="1.4"/>'+
      '<circle cx="'+padL+'" cy="'+baseY+'" r="2.6" fill="'+GRID+'"/>'+
      '<circle cx="'+(W-padR)+'" cy="'+baseY+'" r="2.6" fill="'+GRID+'"/>';
    svg.appendChild(g);
    // legend + weightLegend hint
    legend.forEach(function(l){
      var lg=document.createElement("span"); lg.className="lg";
      var col=pick(l.color,SER[legend.indexOf(l)%SER.length]);
      var hollow=(l.shape==="empty-circle");
      lg.innerHTML=(hollow?'<span class="dot" style="background:'+PAPER+';border:1.5px solid '+col+'"></span>':'<span class="dot" style="background:'+col+'"></span>')+esc(l.label);
      legendBox.appendChild(lg);
    });
    if(CFG.weightLegend && CFG.weightLegend.show){ var hint=document.createElement("span"); hint.className="hint"; hint.textContent=(CFG.weightLegend.label||"weight")+" · 圆点越大表示越成熟"; legendBox.appendChild(hint); }
    var LBL_TOP=30, LBL_LH=14;
    var CONTENT_TOP=54, CONTENT_LH=15;
    var TIME_TOP=baseY+20, TIME_LH=14;
    var MAXCONT=4;
    ev.forEach(function(e,i){
      var cx=x(i), r=rad(e), meta=kindMeta(e.group);
      var hollow=(meta.shape==="empty-circle");
      var anchor=anchorFor(i), ax=axFor(i);
      var lbl=wrap(e.label,labelPer,2);
      var content=wrapLines(e.content, Math.max(8,Math.min(16,Math.round(spacing/11))));
      content=content.slice(0,MAXCONT);
      var times=wrap(e.time,16,2);
      var lspans="",cspans="",tspans="",k;
      for(k=0;k<lbl.length;k++) lspans+='<tspan x="'+ax+'" y="'+(LBL_TOP+k*LBL_LH)+'">'+esc(lbl[k])+'</tspan>';
      for(k=0;k<content.length;k++) cspans+='<tspan x="'+ax+'" y="'+(CONTENT_TOP+k*CONTENT_LH)+'">'+esc(content[k])+'</tspan>';
      for(k=0;k<times.length;k++) tspans+='<tspan x="'+ax+'" y="'+(TIME_TOP+k*TIME_LH)+'">'+esc(times[k])+'</tspan>';
      var node=el("g");
      var seg=el("g");
      seg.innerHTML=
        '<text x="'+ax+'" y="'+LBL_TOP+'" text-anchor="'+anchor+'" font-size="11.5" font-weight="600" fill="'+INK+'" paint-order="stroke" stroke="'+PAPER+'" stroke-width="3px">'+lspans+'</text>'+
        (content.length?'<text x="'+ax+'" y="'+CONTENT_TOP+'" text-anchor="'+anchor+'" font-size="10.5" font-weight="700" fill="'+meta.color+'" paint-order="stroke" stroke="'+PAPER+'" stroke-width="3px">'+cspans+'</text>':"")+
        (hollow?'<circle cx="'+cx+'" cy="'+baseY+'" r="'+r+'" fill="'+PAPER+'" stroke="'+meta.color+'" stroke-width="2"/>':'<circle cx="'+cx+'" cy="'+baseY+'" r="'+r+'" fill="'+meta.color+'"/>')+
        '<text x="'+ax+'" y="'+(TIME_TOP+times.length*TIME_LH)+'" text-anchor="'+anchor+'" font-size="10" font-weight="600" fill="'+MUTED+'" paint-order="stroke" stroke="'+PAPER+'" stroke-width="3px">'+tspans+'</text>';
      node.appendChild(seg);
      svg.appendChild(node);
      var tip='<div class="tt">'+esc(e.label)+'</div>'+(e.time?'<div style="opacity:.85">'+esc(e.time)+'</div>':"")+
        (e.content?'<div style="font-weight:800;white-space:pre-line">'+esc(e.content)+'</div>':"")+
        (e.description?'<div style="opacity:.85">'+esc(e.description)+'</div>':"")+
        '<div style="opacity:.6">'+esc(meta.label)+'</div>';
      bindTip(node, tip);
    });
    stage.appendChild(svg);
  }
})();
</script>
"""

if __name__ == "__main__":
    sys.exit(main())
