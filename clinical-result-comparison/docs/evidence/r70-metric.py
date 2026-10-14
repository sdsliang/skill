import json, pathlib, re, collections
BAIT = ["判断强度","解读边界","组内证据关系","归属组","归组依据","可比性","成熟度","对齐等级",
        "分析模式","分析口径","选择依据","可比性结论","不绘图原因","有限并列原因","纳入标准",
        "检索策略","报告结构","处理模式","部分对齐","仅背景对齐","直接对齐","未对齐","可绘图",
        "只能有限并列","不具备绘图条件","判断结论","证据强度","证据关系"]
MARK = ["banned","is that","conflict","allowed","合法","不能写","不许","算不算","会不会","门禁",
        "check_report","判为","冲突","矛盾","犹豫","risk","踩雷","禁止","FAIL","bait","trap","tricky"]
SPLIT = re.compile(r"(?<=[。！？；])|(?<=[.!?])\s|\n")
base = pathlib.Path.home()/".local/state/toolsmith-runs"
total = collections.Counter(); per_run = {}
for d in sorted(base.iterdir()):
    if not d.is_dir(): continue
    rj = d/"run.json"
    if not rj.exists(): continue
    tag = json.loads(rj.read_text()).get("tag","")
    if not re.match(r"^r(67|68|69)-(4|18|14)$", tag): continue
    md = d/"messages.json"
    if not md.exists(): continue
    hits = collections.Counter(); n = 0; chars = 0
    for m in json.loads(md.read_text()):
        for p in m.get("parts", []):
            if p.get("type") != "reasoning": continue
            for s in SPLIT.split(p.get("text") or ""):
                if not s: continue
                b = [w for w in BAIT if w in s]; k = [w for w in MARK if w in s]
                if b and k:
                    n += 1; chars += len(s)
                    for w in set(b): hits[w] += 1
    per_run[tag] = (n, chars, hits); total.update(hits)
print(f"{'run':8} {'疑问句数':>8} {'字符':>8}  主要触发词")
for tag,(n,chars,hits) in sorted(per_run.items()):
    print(f"{tag:8} {n:8d} {chars:8,d}  " + ", ".join(f"{w}×{c}" for w,c in hits.most_common(5)))
print("\n按词聚合（9 跑合计，降序）:")
for w,c in total.most_common(30): print(f"  {w:12} {c}")
