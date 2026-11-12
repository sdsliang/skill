#!/usr/bin/env python3
"""Render the cards-e2e4 watchlist into a single-file HTML review page.

Structure follows the lieflat chart card contract (结论式标题 + 副标题 + 图 + 来源行),
Mono colour system (high-density reading, no stable colour semantics for buckets).
Charts are adaptations of gallery templates, noted in the source lines:
  图A  L13 Hourglass Stream · lupi-gallery.html
  图B  F15 Tick Box        · basics-gallery.html
Everything else is typography, not a chart, so it does not consume the chart budget.
"""
import json
import statistics
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/wl/watchlist.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/wl/esmo2026-watchlist.html"

W = json.load(open(SRC, encoding="utf-8"))
cards = W["cards"]

BUCKETS = [
    ("early", "早期机会提示", "I 期 / I–II 期，剂量、队列或新机制的首个信号"),
    ("pivotal", "重磅 II/III 期", "随机对照或注册级证据，能直接改变临床判断"),
    ("failed", "失败的研究", "终点未达、终止，或关键亚组/OS 明确的阴性结论"),
]

rc = W.get("review_coverage", {})
stages = [
    ["检出结果", rc.get("source_rows", 1097), "会议库 ESMO 2026 登记结果"],
    ["进入判读", rc.get("candidate_count", 592), "剔除真实世界 / 回顾性 / 汇总分析等非试验证据"],
    ["判读保留", rc.get("review_verdicts", {}).get("keep", 272), "keep；另 weak / drop 见下"],
    ["最终上榜", len(cards), "同机制最多两条 + 每桶 15 条上限"],
]

def q(vals):
    v = sorted(vals)
    n = len(v)
    med = statistics.median(v)
    q1 = statistics.median(v[: n // 2]) if n % 2 == 0 else statistics.median(v[: n // 2 + 1])
    q3 = statistics.median(v[(n + 1) // 2:]) if n % 2 == 0 else statistics.median(v[n // 2:])
    # Tukey fences on the same sample -> what the hollow dots mean
    iqr = q3 - q1
    lo_f, hi_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outs = [x for x in v if x < lo_f or x > hi_f]
    inner = [x for x in v if lo_f <= x <= hi_f] or v
    return {"min": min(inner), "q1": q1, "med": med, "q3": q3, "max": max(inner),
            "out": outs, "all": v}

groups = []
for key, label, dek in BUCKETS:
    ks = [c for c in cards if c["bucket"] == key]
    st = q([c["score"] for c in ks])
    st.update({"key": key, "label": label, "dek": dek, "n": len(ks)})
    groups.append(st)

KPI = [
    (f"{rc.get('source_rows', 1097):,}", "检出结果记录"),
    (f"{rc.get('candidate_count', 592):,}", "进入判读的候选"),
    (f"{rc.get('review_verdicts', {}).get('keep', 272):,}", "判读保留 keep"),
    (f"{len(cards)}", "最终上榜"),
]

notes = W.get("coverage_notes", [])
verification = W.get("verification_points") or {}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def chip(txt, kind="plain"):
    return f'<span class="chip {kind}">{esc(txt)}</span>'


def entry(idx, c):
    chips = []
    if c.get("tag"):
        chips.append(chip(c["tag"], "solid"))
    if c.get("phase"):
        chips.append(chip(c["phase"]))
    if c.get("presentation") and c["presentation"] != "Unknown":
        chips.append(chip(c["presentation"]))
    who = " · ".join(x for x in [c.get("drug"), c.get("target"), c.get("indication")] if x)
    if who:
        chips.append(chip(who, "who"))
    dt = c.get("data_type")
    if dt:
        chips.append(chip(dt, "ghost"))
    nums = "".join(f'<span class="num">{esc(x)}</span>' for x in (c.get("key_numbers") or []))
    parts = c.get("score_parts") or {}
    part_txt = " · ".join(
        f"{k.replace('_', ' ')} {parts[k]}" for k in
        ("evidence_strength", "effect_size", "clinical_impact", "novelty", "readout_maturity")
        if k in parts)
    return f"""
    <article class="item">
      <div class="idx"><div class="sc">{c['score']}</div><div class="no">#{idx:02d}</div></div>
      <div class="body">
        <h3>{esc(c['title'])}</h3>
        <div class="chips">{''.join(chips)}</div>
        <p class="sum">{esc(c['summary'])}</p>
        <p class="why">{esc(c['why'])}</p>
        <div class="nums">{nums}</div>
        <div class="ev">{esc(c.get('evidence') or '')}</div>
        <div class="parts" title="score_parts">判读分 {c['score']} = {esc(part_txt)}</div>
      </div>
    </article>"""


sections = []
for g in groups:
    items = [c for c in cards if c["bucket"] == g["key"]]
    rows = "\n".join(entry(i + 1, c) for i, c in enumerate(items))
    sections.append(f"""
  <section class="bucket" id="{g['key']}">
    <div class="bh">
      <span class="ladder l-{g['key']}"></span>
      <h2>{g['label']}<span class="cnt">{g['n']} 条</span></h2>
      <div class="bdek">{g['dek']} · 分数 {min(c['score'] for c in items)}–{max(c['score'] for c in items)}，中位 {g['med']:.0f}</div>
    </div>
    {rows}
  </section>""")

def _norm(v):
    return str(v or "").strip().removeprefix("nr_")

on_list = {_norm(c.get("esid")) for c in cards}
vh = ""
if verification:
    for _k, _v in verification.items():
        _v["selected"] = _norm(_v.get("esid")) in on_list
    rows = "".join(
        f'<tr><td>{esc(k)}</td><td>{"在池" if v.get("present_in_pool") else "不在池"}</td>'
        f'<td>{"已上榜" if v.get("selected") else "未上榜"}</td>'
        f'<td class="esid">{esc(v.get("esid") or "")}</td></tr>'
        for k, v in verification.items())
    vh = f"""
  <div class="verify">
    <div class="kick">SELF-CHECK · 三条最热 LBA 的去向</div>
    <table>{rows}</table>
  </div>"""

notes_html = "".join(f"<li>{esc(n)}</li>" for n in notes)
data = json.dumps({"stages": stages, "groups": [{k: g[k] for k in ("key", "label", "n", "min", "q1", "med", "q3", "max", "out")} for g in groups]},
                  ensure_ascii=False)

HTML = f"""<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>ESMO 2026 · 会议临床结果推荐 — 45 条清单复核</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root{{--bg:#F0EFEB;--ink:#1C1C1A;--muted:#8F8E88;--faint:#C6C5BF;--grid:#DEDDD6;
        --l2:#4A4944;--l3:#6A6963;--l5:#B0AFA9;--paper:#F0EFEB}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--bg);color:var(--ink);font-family:'Inter','Noto Sans SC',sans-serif;
    -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums lining-nums;padding:56px 28px 80px}}
  .sheet{{width:1080px;max-width:1080px;margin:0 auto}}
  .pop{{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,.7,.3,1.3) both}}
  @keyframes pop{{from{{transform:scale(0)}}to{{transform:none}}}}
  .fade{{animation:fade .9s ease both}}
  @keyframes fade{{from{{opacity:0}}}}
  .draw{{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1s cubic-bezier(.4,0,.2,1) both}}
  @keyframes draw{{to{{stroke-dashoffset:0}}}}
  @media (prefers-reduced-motion:reduce){{.pop,.fade,.draw{{animation:none}}.draw{{stroke-dasharray:none;stroke-dashoffset:0}}}}

  .kick{{font-size:9.5px;font-weight:700;letter-spacing:.16em;color:var(--muted)}}
  h1{{font-size:46px;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin:14px 0 10px}}
  h1 b{{font-weight:800}}
  .dek{{font-size:15px;line-height:1.7;color:var(--l2);max-width:740px}}
  .meta{{margin-top:18px;font-size:10px;font-weight:600;letter-spacing:.1em;color:var(--faint)}}

  .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin:40px 0 8px;
    border-top:1px solid var(--ink);padding-top:22px}}
  .kpi .big{{font-size:34px;font-weight:800;letter-spacing:-.03em}}
  .kpi .lb{{font-size:10.5px;font-weight:600;color:var(--muted);margin-top:6px;letter-spacing:.04em}}
  .nav{{margin-top:22px;font-size:10.5px;font-weight:600;letter-spacing:.06em;color:var(--muted);display:flex;gap:22px}}
  .nav a{{color:var(--l2);text-decoration:none;border-bottom:1px solid var(--l5);padding-bottom:2px}}
  .nav a:hover{{color:var(--ink);border-color:var(--ink)}}

  .card{{padding:34px 0 6px}}
  .card+.card{{border-top:1px solid var(--grid)}}
  .card h2{{font-size:16.5px;font-weight:700;letter-spacing:-.02em}}
  .card .sub{{font-size:11.5px;color:var(--muted);margin:4px 0 12px}}
  .src{{font-size:9.5px;font-weight:500;letter-spacing:.08em;color:var(--faint);margin-top:8px}}
  svg text{{font-family:'Inter','Noto Sans SC',sans-serif}}

  .bucket{{margin-top:54px}}
  .bh{{display:flex;align-items:baseline;gap:12px;border-bottom:1px solid var(--ink);padding-bottom:10px}}
  .ladder{{width:13px;height:13px;border-radius:4px;transform:translateY(1px)}}
  .l-early{{background:var(--l3)}} .l-pivotal{{background:var(--ink)}} .l-failed{{background:var(--l5)}}
  .bh h2{{font-size:18px;font-weight:800;letter-spacing:-.02em}}
  .bh .cnt{{font-size:11px;font-weight:600;color:var(--muted);margin-left:10px;letter-spacing:.06em}}
  .bdek{{margin-left:auto;font-size:10.5px;color:var(--muted);letter-spacing:.02em}}

  .item{{display:grid;grid-template-columns:78px 1fr;gap:18px;padding:26px 0 20px;
    border-bottom:1px solid var(--grid)}}
  .idx{{text-align:right}}
  .idx .sc{{font-size:26px;font-weight:800;letter-spacing:-.03em;line-height:1}}
  .idx .no{{font-size:9.5px;font-weight:600;color:var(--faint);margin-top:6px;letter-spacing:.1em}}
  .item h3{{font-size:14.5px;font-weight:700;line-height:1.45;letter-spacing:-.01em;max-width:900px}}
  .chips{{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0 11px}}
  .chip{{font-size:9.5px;font-weight:600;letter-spacing:.04em;padding:3px 8px;border-radius:99px;
    border:1px solid var(--grid);color:var(--l2)}}
  .chip.solid{{background:var(--ink);color:var(--paper);border-color:var(--ink)}}
  .chip.who{{border-color:var(--l5);color:var(--l2)}}
  .chip.ghost{{border-style:dashed;color:var(--muted)}}
  .sum{{font-size:13px;line-height:1.7;color:var(--ink);max-width:900px}}
  .why{{font-size:12.5px;line-height:1.7;color:var(--l2);margin-top:7px;max-width:900px}}
  .why:before{{content:'为什么在榜上 · ';font-weight:700;color:var(--muted);letter-spacing:.02em}}
  .nums{{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px}}
  .num{{font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:6px;background:#E7E6E0}}
  .ev{{font-size:10.5px;line-height:1.6;color:var(--muted);margin-top:10px;max-width:900px;
    border-left:2px solid var(--grid);padding-left:10px}}
  .parts{{font-size:9px;font-weight:600;letter-spacing:.06em;color:var(--faint);margin-top:10px}}

  .verify{{margin-top:56px;border-top:1px solid var(--ink);padding-top:22px}}
  .verify table{{width:100%;border-collapse:collapse;margin-top:14px;font-size:11px}}
  .verify td{{padding:7px 0;border-bottom:1px solid var(--grid)}}
  .verify td:first-child{{font-weight:700;width:200px}}
  .verify .esid{{color:var(--faint);font-size:9.5px;letter-spacing:.02em}}

  .honest{{margin-top:56px;border-top:1px solid var(--ink);padding-top:22px}}
  .honest h2{{font-size:18px;font-weight:800;letter-spacing:-.02em;margin-bottom:4px}}
  .honest .sub{{font-size:11.5px;color:var(--muted);margin-bottom:16px}}
  .honest ol{{list-style:none;counter-reset:n}}
  .honest li{{counter-increment:n;position:relative;padding-left:30px;font-size:12px;line-height:1.75;
    color:var(--l2);margin-bottom:11px;max-width:920px}}
  .honest li:before{{content:counter(n,decimal-leading-zero);position:absolute;left:0;top:1px;
    font-size:9.5px;font-weight:700;color:var(--faint);letter-spacing:.08em}}
  .foot{{margin-top:44px;font-size:9.5px;font-weight:500;letter-spacing:.08em;color:var(--faint)}}
</style>
</head>
<body>
<div class="sheet">

  <div class="kick">ESMO 2026 · 会议临床结果推荐 · 清单复核稿</div>
  <h1>45 条值得先读的<b>临床结果</b></h1>
  <div class="dek">从会议库 1,097 条结果记录里筛出 592 条试验类候选，逐条判读后留 272 条，再按“同机制最多两条、每桶 15 条”压到 45 条。三个桶各 15 条：早期机会、重磅 II/III 期、失败的研究。分数是判读结果，不是公式。</div>
  <div class="meta">数据 ESMO 2026 · 平台 MCP CLINICAL_TRIAL_RESULT_STRUCTURED · 生成 2026-11-12 · v0.6 全量实跑 1,520 S · 40 批判读</div>

  <div class="kpis">
    {''.join(f'<div class="kpi"><div class="big">{v}</div><div class="lb">{esc(k)}</div></div>' for v, k in KPI)}
  </div>

  <div class="nav">
    <a href="#early">早期机会提示 15</a><a href="#pivotal">重磅 II/III 期 15</a><a href="#failed">失败的研究 15</a><a href="#honest">覆盖与边界</a>
  </div>

  <div class="card wide">
    <h2>三步筛掉 96%，每一步删的都是同一类东西</h2>
    <div class="sub">一条 = 一条记录 · 宽度与条数成正比 · 左侧为留存率</div>
    <svg id="funnel" viewBox="0 0 760 330" preserveAspectRatio="xMidYMid meet"></svg>
    <div class="src">L13 HOURGLASS STREAM · LUPI-GALLERY · 漏斗 1,097 → 592 → 272 → 45</div>
  </div>

  <div class="card wide">
    <h2>三个桶的分数重心不同，失败桶并不低</h2>
    <div class="sub">横档 = 该桶 15 条的中位数 · 箱体 = 中间一半 · 空心点 = 落在 1.5 IQR 外的记录 · 纵轴为判读分</div>
    <svg id="box" viewBox="0 0 760 350" preserveAspectRatio="xMidYMid meet"></svg>
    <div class="src">F15 TICK BOX · BASICS-GALLERY · 判读分分布 · 45 条</div>
  </div>

  {''.join(sections)}
  {vh}

  <div class="honest" id="honest">
    <h2>覆盖与边界</h2>
    <div class="sub">这七条写在交付 JSON 里，不是写在聊天回复里——下个月读这份清单的人同样应该看到。</div>
    <ol>{notes_html}</ol>
  </div>

  <div class="foot">判读分 = evidence strength ≤30 + effect size ≤25 + clinical impact ≤25 + novelty ≤10 + readout maturity ≤10 · 分数不进卡片正文，只用于定榜 · 清单顺序为编辑定榜，不由脚本排序</div>
</div>

<script>
const D = {data};

(function funnel(){{
  const s = document.getElementById('funnel');
  const CX = 300, top = 44, gap = 72, MAXW = 300;
  const maxV = D.stages[0][1];
  const w = v => v / maxV * MAXW;
  const mk = (tag, at) => {{ const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const k in at) e.setAttribute(k, at[k]); s.appendChild(e); return e; }};
  const txt = (x, y, t, at) => {{ const e = mk('text', Object.assign({{x, y}}, at));
    e.textContent = t; return e; }};

  D.stages.forEach(([name, v, note], k) => {{
    const y = top + k * gap, hw = w(v) / 2;
    // one tick per record, thinned only as far as the strip can physically hold
    const n = Math.max(4, Math.min(v, Math.floor(hw * 2 / 1.5)));
    for (let t = 0; t < n; t++) {{
      const x = CX - hw + (t + .5) / n * hw * 2;
      mk('line', {{x1: x, y1: y - 9, x2: x, y2: y + 9, stroke: '#1C1C1A', 'stroke-width': .7,
        opacity: .45 + ((t * 37) % 100) / 200, class: 'fade',
        style: `animation-delay:${{k * .12 + t * .004}}s`}});
    }}
    // threads trickling into the next, narrower strip
    if (k < D.stages.length - 1) {{
      const hw1 = w(D.stages[k + 1][1]) / 2;
      for (let t = 0; t < 26; t++) {{
        const xt = CX + ((((t * 61) % 100) / 100 - .5) * 2 * hw * .92);
        const xb = CX + ((((t * 47 + 13) % 100) / 100 - .5) * 2 * hw1 * .92);
        mk('path', {{d: `M${{xt}} ${{y + 11}} C${{xt}} ${{y + 34}} ${{xb}} ${{y + gap - 34}} ${{xb}} ${{y + gap - 11}}`,
          fill: 'none', stroke: '#B0AFA9', 'stroke-width': .5, opacity: .3, pathLength: 1,
          class: 'draw', style: `animation-delay:${{.2 + k * .15 + t * .008}}s;animation-duration:.8s`}});
      }}
      const pct = Math.round(D.stages[k + 1][1] / v * 100);
      txt(48, y + gap / 2 + 4, pct + '%', {{'font-size': 12, 'font-weight': 800, fill: '#8F8E88'}});
      txt(48, y + gap / 2 + 18, '留存', {{'font-size': 7.5, 'font-weight': 600, fill: '#C6C5BF', 'letter-spacing': '.1em'}});
    }}
    mk('line', {{x1: CX + hw + 8, y1: y, x2: CX + MAXW / 2 + 26, y2: y, stroke: '#DEDDD6', 'stroke-width': .8, class: 'fade'}});
    txt(CX + MAXW / 2 + 32, y - 1, name, {{'font-size': 11, 'font-weight': 700, fill: '#4A4944', 'letter-spacing': '.04em'}});
    txt(CX + MAXW / 2 + 32, y + 16, v.toLocaleString(), {{'font-size': 15, 'font-weight': 800, fill: '#1C1C1A'}});
    txt(CX + MAXW / 2 + 32, y + 30, note, {{'font-size': 8, 'font-weight': 500, fill: '#8F8E88'}});
  }});
  txt(48, 300, '每节 = 一条记录，仅按条宽抽稀 · 条宽与条数严格成正比', {{'font-size': 8, 'font-weight': 600, fill: '#B0AFA9', 'letter-spacing': '.08em'}});
}})();

(function boxplot(){{
  const s = document.getElementById('box');
  const TOP = 30, BASE = 270, LO = 75, HI = 100;
  const mapY = v => BASE - (v - LO) / (HI - LO) * (BASE - TOP);
  const mk = (tag, at) => {{ const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const k in at) e.setAttribute(k, at[k]); s.appendChild(e); return e; }};
  const txt = (x, y, t, at) => {{ const e = mk('text', Object.assign({{x, y}}, at));
    e.textContent = t; return e; }};
  const SHADE = {{early: '#6A6963', pivotal: '#1C1C1A', failed: '#B0AFA9'}};
  for (let v = 75; v <= 100; v += 5) {{
    mk('line', {{x1: 60, y1: mapY(v), x2: 700, y2: mapY(v), stroke: '#E3E2DB', 'stroke-width': .8, class: 'fade'}});
    txt(52, mapY(v) + 3, v, {{'font-size': 8.5, 'font-weight': 600, fill: '#8F8E88', 'text-anchor': 'end'}});
  }}
  const colX = g => 150 + g * 205, BW = 40;
  D.groups.forEach((g, i) => {{
    const x = colX(i);
    mk('line', {{x1: x, y1: mapY(g.min), x2: x, y2: mapY(g.max), stroke: '#8F8E88', 'stroke-width': .9,
      pathLength: 1, class: 'draw', style: `animation-delay:${{i * .12}}s;animation-duration:.6s`}});
    [g.min, g.max].forEach(v => mk('line', {{x1: x - 13, y1: mapY(v), x2: x + 13, y2: mapY(v),
      stroke: '#8F8E88', 'stroke-width': 1, class: 'fade'}}));
    mk('rect', {{x: x - BW / 2, y: mapY(g.q3), width: BW, height: Math.max(2, mapY(g.q1) - mapY(g.q3)),
      rx: 14, fill: SHADE[g.key], class: 'pop', style: `animation-delay:${{.15 + i * .12}}s`}});
    mk('line', {{x1: x - BW / 2 + 6, y1: mapY(g.med), x2: x + BW / 2 - 6, y2: mapY(g.med),
      stroke: '#F0EFEB', 'stroke-width': 2.4, class: 'fade', style: `animation-delay:${{.5 + i * .12}}s`}});
    txt(x + BW / 2 + 8, mapY(g.med) + 4, '中位 ' + g.med, {{'font-size': 10.5, 'font-weight': 800, fill: '#1C1C1A'}});
    g.out.forEach((o, k) => mk('circle', {{cx: x + (k % 2 ? 7 : -7), cy: mapY(o), r: 3, fill: '#F0EFEB',
      stroke: '#6A6963', 'stroke-width': 1.1, class: 'pop', style: `animation-delay:${{.7 + i * .12 + k * .06}}s`}}));
    txt(x, BASE + 26, g.label, {{'font-size': 10.5, 'font-weight': 700, fill: '#4A4944', 'text-anchor': 'middle'}});
    txt(x, BASE + 43, g.n + ' 条 · ' + g.min + '–' + g.max, {{'font-size': 9, 'font-weight': 600, fill: '#8F8E88', 'text-anchor': 'middle'}});
  }});
  txt(52, 338, '箱体 = 中间一半 · 纸色横档 = 中位数 · 空心点 = 1.5 IQR 外', {{'font-size': 8, 'font-weight': 600, fill: '#B0AFA9', 'letter-spacing': '.08em'}});
}})();
</script>
</body>
</html>
"""

open(OUT, "w", encoding="utf-8").write(HTML)
print(f"{OUT} {len(HTML)} bytes · {len(cards)} cards · " +
      " ".join(f"{g['key']}={g['n']}({g['med']:.0f})" for g in groups))
