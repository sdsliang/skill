#!/usr/bin/env python3
"""R71 metric: legality-litigation volume about "why no chart" wording, per sentence.

Convention (fixed BEFORE the R71 runs; R70 runs reused as the pre-edit baseline):
  topic = 不绘图原因 / 无法绘图 / 不出图 / 不画 / 没画 / 未画 / why no ... chart / no quantitative chart
  question = banned|is that|conflict|合法|算不算|会不会|门禁|check_report|FAIL|forbidden|self-label
  A sentence counts only when it hits BOTH (same sentence, thinking channel).

usage: r71-metric.py [tag-regex]     (default: ^r(70|71)-(4|18|14)$)
"""
import json, pathlib, re, sys, collections

TOPIC = re.compile(r"不绘图原因|无法绘图|不出图|不画|没画|未画|why no[^\n]{0,30}chart|no quantitative chart")
Q = re.compile(r"banned|is that|conflict|合法|算不算|会不会|门禁|check_report|FAIL|forbidden|self-label|被判|拒收")
SPLIT = re.compile(r"(?<=[。！？；])|(?<=[.!?])\s|\n")
BASE = pathlib.Path.home() / ".local/state/toolsmith-runs"


def reason_chars(rundir):
    tot = 0
    for m in json.loads((rundir / "messages.json").read_text()):
        for p in m.get("parts", []):
            if p.get("type") == "reasoning":
                tot += len(p.get("text") or "")
    return tot


def scan(rundir):
    hits = []
    for m in json.loads((rundir / "messages.json").read_text()):
        for p in m.get("parts", []):
            if p.get("type") != "reasoning":
                continue
            for s in SPLIT.split(p.get("text") or ""):
                s = s.strip()
                if s and TOPIC.search(s) and Q.search(s):
                    hits.append(s.replace("\n", " "))
    return hits


if __name__ == "__main__":
    pat = re.compile(sys.argv[1] if len(sys.argv) > 1 else r"^r(70|71)-(4|18|14)$")
    tot = 0
    grand = [0]
    words = collections.Counter()
    for d in sorted(BASE.iterdir()):
        if not d.is_dir():
            continue
        f = d / "run.json"
        if not f.is_file():
            continue
        tag = json.loads(f.read_text()).get("tag", "")
        if not pat.match(tag):
            continue
        if not (d / "messages.json").is_file():
            print(f"{tag:12s} 跳过（无 messages.json，未完成/未验证）")
            continue
        hits = scan(d)
        tot += len(hits)
        for h in hits:
            for w in TOPIC.findall(h):
                words[w] += 1
        rc = reason_chars(d)
        grand[0] += rc
        print(f"{tag:12s} 句={len(hits):3d}  reasoning字符={rc:,}  (每10万字符 {100000*len(hits)/rc if rc else 0:.1f})")
        for h in hits:
            print("     •", h[:200])
    print(f"\n合计 {tot} 句 / reasoning {grand[0]:,} 字符 "
          f"⇒ 每 10 万字符 {100000*tot/grand[0] if grand[0] else 0:.1f} 句；触发词 {dict(words)}")
