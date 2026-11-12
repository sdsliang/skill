#!/usr/bin/env python3
"""Render the 45 recommendation cards from output/watchlist.json into one HTML page.

Only the card records are shown — no derived aggregates, no coverage block, no extra
fields. Everything printed on the page is a field of a card object, verbatim.

    python3 build_review_page.py <watchlist.json> <out.html>
"""
import json
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "watchlist.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "esmo2026-watchlist.html"

W = json.load(open(SRC, encoding="utf-8"))
cards = W["cards"]

BUCKETS = [
    ("early", "早期机会提示"),
    ("pivotal", "重磅 II/III 期"),
    ("failed", "失败的研究"),
]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def entry(idx, c, bucket):
    chips = []
    if c.get("tag"):
        chips.append(f'<span class="chip solid">{esc(c["tag"])}</span>')
    if c.get("phase"):
        chips.append(f'<span class="chip">{esc(c["phase"])}</span>')
    # "LBA" and "Late-breaking Oral" are the same fact in two fields — print it once
    if c.get("presentation") and c["presentation"] != "Unknown" and not c.get("tag"):
        chips.append(f'<span class="chip">{esc(c["presentation"])}</span>')
    # the drug name moved up to the head of the card, so the chip keeps only target · indication
    who = " · ".join(x for x in [c.get("target"), c.get("indication")] if x)
    if who:
        chips.append(f'<span class="chip who">{esc(who)}</span>')
    # "未判定" is the honest default, not information — it stays in the JSON only
    if c.get("data_type") and c["data_type"] != "未判定":
        chips.append(f'<span class="chip ghost">{esc(c["data_type"])}</span>')
    # v0.7: only render a ticker we could actually source — a listed-looking chip with
    # no exchange behind it is worse than nothing next to a share-price claim.
    co = c.get("listed_company") or {}
    if co.get("ticker"):
        label = f'{co.get("ticker")} · {co.get("exchange")}' if co.get("exchange") \
            else str(co["ticker"])
        chips.append(f'<span class="chip stock" title="{esc(co.get("name") or "")}">'
                     f'{esc(label)}</span>')
    if c.get("promoted"):
        chips.append('<span class="chip ghost">网页补录</span>')
    return f"""
    <article class="item" id="c-{bucket}-{idx}">
      <div class="body">
        <div class="head"><span class="no">#{idx:02d}</span><span class="drug">{esc(c.get('drug') or '—')}</span></div>
        <h3>{esc(c['title'])}</h3>
        <div class="chips">{''.join(chips)}</div>
        <p class="sum">{esc(c['summary'])}</p>
        <p class="why">{esc(c['why'])}</p>
        <div class="ev">{esc(c.get('evidence') or '')}</div>
      </div>
    </article>"""


nav_groups = []
sections = []
for key, label in BUCKETS:
    items = [c for c in cards if c["bucket"] == key]
    if not items:
        continue
    rows = "\n".join(entry(i + 1, c, key) for i, c in enumerate(items))
    sections.append(f"""
  <section class="bucket" id="b-{key}">
    <div class="bh"><span class="ladder l-{key}"></span><h2>{label}<span class="cnt">{len(items)}</span></h2></div>
    {rows}
  </section>""")
    links = "".join(
        f'<a href="#c-{key}-{i + 1}" title="{esc(c["title"])}">'
        f'<span class="nd">{esc(c.get("drug") or c["title"])}</span></a>'
        for i, c in enumerate(items))
    nav_groups.append(f'<div class="ng"><a class="ng-t" href="#b-{key}">'
                      f'<span class="ladder l-{key}"></span>{label}</a>{links}</div>')

HTML = f"""<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{esc(W.get('conference', ''))} · 推荐清单</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root{{--bg:#F0EFEB;--ink:#1C1C1A;--muted:#8F8E88;--faint:#C6C5BF;--grid:#DEDDD6;
        --l2:#4A4944;--l3:#6A6963;--l5:#B0AFA9;--paper:#F0EFEB}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--bg);color:var(--ink);font-family:'Inter','Noto Sans SC',sans-serif;
    -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums lining-nums;padding:56px 28px 80px}}
  html{{scroll-behavior:smooth}}
  .sheet{{width:1280px;max-width:1280px;margin:0 auto;display:grid;
    grid-template-columns:206px minmax(0,1fr);gap:44px}}
  .main{{min-width:0}}

  .nav{{position:sticky;top:26px;align-self:start;max-height:calc(100vh - 52px);
    overflow:auto;padding-right:6px}}
  .nav::-webkit-scrollbar{{width:4px}}
  .nav::-webkit-scrollbar-thumb{{background:var(--grid);border-radius:9px}}
  .nt{{font-size:9.5px;font-weight:700;letter-spacing:.14em;color:var(--muted);
    line-height:1.7;padding-bottom:12px;border-bottom:1px solid var(--ink)}}
  .nt b{{font-size:11px;letter-spacing:.02em;color:var(--ink)}}
  .ng{{margin-top:16px}}
  .ng-t{{display:flex;align-items:center;gap:7px;font-size:10.5px;font-weight:800;
    color:var(--ink);text-decoration:none;letter-spacing:-.01em;margin-bottom:8px}}
  .ng-t .ladder{{width:9px;height:9px;border-radius:3px;flex:none}}
  .nav a{{text-decoration:none}}
  .ng a:not(.ng-t){{display:flex;gap:7px;align-items:baseline;padding:3px 0;max-width:100%;
    font-size:10px;color:var(--l2);border-bottom:1px solid transparent}}
  .ng a:not(.ng-t):hover{{color:var(--ink)}}
  .ng a:not(.ng-t):hover .nd{{text-decoration:underline;text-underline-offset:2px}}
  .nd{{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;letter-spacing:-.01em}}
  .l-early{{background:var(--l3)}} .l-pivotal{{background:var(--ink)}} .l-failed{{background:var(--l5)}}
  @media (max-width:1320px){{
    body{{padding:34px 20px 60px}}
    .sheet{{width:auto;max-width:1080px;grid-template-columns:1fr;gap:26px}}
    .nav{{position:static;max-height:none;overflow:visible;border-bottom:1px solid var(--grid);padding-bottom:16px}}
    .nav .ng{{display:inline-block;vertical-align:top;margin:14px 26px 0 0;
      width:calc((100% - 60px) / 3);max-width:300px}}
    .nt{{display:none}}
  }}

  .kick{{font-size:9.5px;font-weight:700;letter-spacing:.16em;color:var(--muted)}}
  h1{{font-size:44px;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin:14px 0 0}}

  .bucket{{margin-top:52px}}
  .bh{{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--ink);padding-bottom:10px}}
  .ladder{{width:13px;height:13px;border-radius:4px;flex:none}}
  .bh h2{{font-size:18px;font-weight:800;letter-spacing:-.02em}}
  .bh .cnt{{font-size:11px;font-weight:600;color:var(--muted);margin-left:10px;letter-spacing:.06em}}

  .item{{padding:24px 0 20px;border-bottom:1px solid var(--grid)}}
  .head{{display:flex;align-items:baseline;gap:9px;margin-bottom:7px}}
  .head .no{{font-size:9.5px;font-weight:700;color:var(--faint);letter-spacing:.1em}}
  .head .drug{{font-size:12.5px;font-weight:800;letter-spacing:-.01em;color:var(--ink)}}
  .item h3{{font-size:14.5px;font-weight:700;line-height:1.45;letter-spacing:-.01em;max-width:900px}}
  .chips{{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0 11px}}
  .chip{{font-size:9.5px;font-weight:600;letter-spacing:.04em;padding:3px 8px;border-radius:99px;
    border:1px solid var(--grid);color:var(--l2)}}
  .chip.solid{{background:var(--ink);color:var(--paper);border-color:var(--ink)}}
  .chip.who{{border-color:var(--l5);color:var(--l2)}}
  .chip.ghost{{border-style:dashed;color:var(--muted)}}
  .chip.stock{{border-color:var(--ink);color:var(--ink);font-variant-numeric:tabular-nums}}
  .sum{{font-size:13px;line-height:1.7;color:var(--ink);max-width:900px}}
  .why{{font-size:12.5px;line-height:1.7;color:var(--l2);margin-top:7px;max-width:900px}}
  .why:before{{content:'推荐理由 · ';font-weight:700;color:var(--muted);letter-spacing:.02em}}
  .ev{{font-size:10.5px;line-height:1.6;color:var(--muted);margin-top:10px;max-width:900px;
    border-left:2px solid var(--grid);padding-left:10px}}
</style>
</head>
<body>
<div class="sheet">
  <nav class="nav">
    <div class="nt">{esc(W.get('conference', ''))}<br><b>{len(cards)} 张推荐卡片</b></div>
    {''.join(nav_groups)}
  </nav>
  <main class="main">
    <div class="kick">{esc(W.get('conference', ''))} · 临床结果推荐</div>
    <h1>{len(cards)} 张推荐卡片</h1>
    {''.join(sections)}
  </main>
</div>
</body>
</html>
"""

open(OUT, "w", encoding="utf-8").write(HTML)
print(f"{OUT} · {len(cards)} cards · " + " ".join(
    f"{k}={sum(1 for c in cards if c['bucket'] == k)}" for k, _ in BUCKETS))
