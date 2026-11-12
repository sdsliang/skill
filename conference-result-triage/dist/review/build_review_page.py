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


def entry(idx, c):
    chips = []
    if c.get("tag"):
        chips.append(f'<span class="chip solid">{esc(c["tag"])}</span>')
    if c.get("phase"):
        chips.append(f'<span class="chip">{esc(c["phase"])}</span>')
    # "LBA" and "Late-breaking Oral" are the same fact in two fields — print it once
    if c.get("presentation") and c["presentation"] != "Unknown" and not c.get("tag"):
        chips.append(f'<span class="chip">{esc(c["presentation"])}</span>')
    who = " · ".join(x for x in [c.get("drug"), c.get("target"), c.get("indication")] if x)
    if who:
        chips.append(f'<span class="chip who">{esc(who)}</span>')
    # "未判定" is the honest default, not information — it stays in the JSON only
    if c.get("data_type") and c["data_type"] != "未判定":
        chips.append(f'<span class="chip ghost">{esc(c["data_type"])}</span>')
    return f"""
    <article class="item">
      <div class="idx"><div class="sc">{c['score']}</div><div class="no">#{idx:02d}</div></div>
      <div class="body">
        <h3>{esc(c['title'])}</h3>
        <div class="chips">{''.join(chips)}</div>
        <p class="sum">{esc(c['summary'])}</p>
        <p class="why">{esc(c['why'])}</p>
        <div class="ev">{esc(c.get('evidence') or '')}</div>
      </div>
    </article>"""


sections = []
for key, label in BUCKETS:
    items = [c for c in cards if c["bucket"] == key]
    if not items:
        continue
    rows = "\n".join(entry(i + 1, c) for i, c in enumerate(items))
    sections.append(f"""
  <section class="bucket">
    <div class="bh"><span class="ladder l-{key}"></span><h2>{label}<span class="cnt">{len(items)}</span></h2></div>
    {rows}
  </section>""")

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
  .sheet{{width:1080px;max-width:1080px;margin:0 auto}}

  .kick{{font-size:9.5px;font-weight:700;letter-spacing:.16em;color:var(--muted)}}
  h1{{font-size:44px;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin:14px 0 0}}

  .bucket{{margin-top:52px}}
  .bh{{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--ink);padding-bottom:10px}}
  .ladder{{width:13px;height:13px;border-radius:4px}}
  .l-early{{background:var(--l3)}} .l-pivotal{{background:var(--ink)}} .l-failed{{background:var(--l5)}}
  .bh h2{{font-size:18px;font-weight:800;letter-spacing:-.02em}}
  .bh .cnt{{font-size:11px;font-weight:600;color:var(--muted);margin-left:10px;letter-spacing:.06em}}

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
  .why:before{{content:'推荐理由 · ';font-weight:700;color:var(--muted);letter-spacing:.02em}}
  .ev{{font-size:10.5px;line-height:1.6;color:var(--muted);margin-top:10px;max-width:900px;
    border-left:2px solid var(--grid);padding-left:10px}}
</style>
</head>
<body>
<div class="sheet">
  <div class="kick">{esc(W.get('conference', ''))} · 临床结果推荐</div>
  <h1>{len(cards)} 张推荐卡片</h1>
  {''.join(sections)}
</div>
</body>
</html>
"""

open(OUT, "w", encoding="utf-8").write(HTML)
print(f"{OUT} · {len(cards)} cards · " + " ".join(
    f"{k}={sum(1 for c in cards if c['bucket'] == k)}" for k, _ in BUCKETS))
