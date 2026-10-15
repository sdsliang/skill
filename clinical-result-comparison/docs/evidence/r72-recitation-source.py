#!/usr/bin/env python3
"""R72 红证据：模型逐字复述的那串禁词，来自哪一处常数清单？

对 r71-18 / r71b-4 的思考通道取「复述句」，把句中出现过的禁词与**改前（HEAD）**两处清单做集合对照：
`SKILL.md` 的硬规则段 vs `references/toolbox.md` 的 FAIL 条目。谁召回得多，谁就是复述源。
"""
from __future__ import annotations
import json, pathlib, re, subprocess, sys

BASE = pathlib.Path.home() / ".local/state/toolsmith-runs"
REPO = pathlib.Path(__file__).resolve().parents[2]

# 门禁词汇（check_report.py 的 META_LABEL_RE / META_COLUMN_RE / METHOD_NARRATION_RE / SELF_AUDIT_RE
# / SELF_REFERENCE_RE / INTERNAL_VOCAB_RE 里出现的形态，人工并集，用于「复述源」比对）
VOCAB = ["分析模式", "分析口径", "选择依据", "可比性结论", "对齐等级", "不绘图原因", "有限并列原因",
         "纳入标准", "检索策略", "报告结构", "可绘图", "只能有限并列", "不具备绘图条件", "部分对齐",
         "仅背景对齐", "本报告", "本文档", "本次", "本轮", "src=", "esid", "payload", "JSONL", "MCP",
         "工作区", "沙箱", "无未复核记录", "无遗漏", "全部通过", "我们选择", "本次选择", "本次纳入"]

def head(path: str) -> str:
    return subprocess.run(["git", "show", f"HEAD:./{path}"], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout

def recitations(rundir: pathlib.Path) -> list[str]:
    out = []
    for m in json.loads((rundir / "messages.json").read_text()):
        for p in m.get("parts", []):
            if p.get("type") != "reasoning":
                continue
            for line in re.split(r"[\n。；;]", p.get("text") or ""):
                hits = [w for w in VOCAB if w in line]
                if len(hits) >= 6:                      # 复述 = 一行里堆了 ≥6 个禁词
                    out.append((line.strip(), hits))
    return out

def main() -> int:
    lists = {
        "SKILL.md（硬规则段，改前）": head("skill/multi-clinical-result-comparison/SKILL.md"),
        "toolbox.md（FAIL 条目，改前）": head("skill/multi-clinical-result-comparison/references/toolbox.md"),
    }
    print("改前两处清单各自出现的禁词数：")
    for name, text in lists.items():
        print(f"  {name}: {sum(1 for w in VOCAB if w in text)}/{len(VOCAB)}")
    pat = re.compile(sys.argv[1] if len(sys.argv) > 1 else r"^r71-18$|^r71b-4$")
    for d in sorted(BASE.iterdir()):
        if not d.is_dir() or not (d / "run.json").is_file():
            continue
        tag = json.loads((d / "run.json").read_text()).get("tag", "")
        if not pat.match(tag) or not (d / "messages.json").is_file():
            continue
        reps = recitations(d)
        print(f"\n{tag}: 复述句 {len(reps)} 条")
        for line, hits in reps:
            recall = {n: sum(1 for w in hits if w in t) for n, t in lists.items()}
            print(f"  • {len(hits)} 个禁词，召回 {recall}")
            print(f"    {line[:150]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
