#!/usr/bin/env python3
"""R69 metric: vocabulary-legality reasoning volume in thinking parts.

Convention (fixed BEFORE the R69 runs; baselines recomputed with it):
  groups: template-vocab = 处理模式|直接对齐|部分对齐|仅背景|未对齐|对齐等级
          gate-check    = check_report.py|FAIL list|banned|self-label|class label
  次 = total matches over reasoning parts; 字符 = chars of reasoning parts holding >=1 match.
"""
import json, pathlib, re, sys

G = {
    "template-vocab": re.compile(r"处理模式|直接对齐|部分对齐|仅背景|未对齐|对齐等级"),
    "gate-check": re.compile(r"check_report\.py|FAIL list|banned|self-label|class label"),
}
ALL = re.compile("|".join(g.pattern for g in G.values()))

def metric(rd: pathlib.Path):
    per = {k: 0 for k in G}
    chars = 0
    for msg in json.loads((rd / "messages.json").read_text()):
        for p in msg.get("parts", []):
            if p.get("type") != "reasoning":
                continue
            t = p.get("text") or ""
            for k, rx in G.items():
                per[k] += len(rx.findall(t))
            if ALL.search(t):
                chars += len(t)
    return per, chars

if __name__ == "__main__":
    base = pathlib.Path.home() / ".local/state/toolsmith-runs"
    for name in sys.argv[1:]:
        per, c = metric(base / name)
        tv, gc = per["template-vocab"], per["gate-check"]
        print(f"{name:26s} template-vocab={tv:3d}  gate-check={gc:3d}  合计={tv+gc:3d}  ({c/1000:6.1f}k chars)")
