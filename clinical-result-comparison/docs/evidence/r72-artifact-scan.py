#!/usr/bin/env python3
"""R72 判据 3：交付物里「门禁词汇」命中数必须为 0（用 check_report.py 自己的正则，不用手写词表）。

用法：python3 -B docs/evidence/r72-artifact-scan.py <run-dir> [<run-dir> ...]
"""
from __future__ import annotations
import importlib.util, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parents[2]
CHECKER = REPO / "skill/multi-clinical-result-comparison/scripts/check_report.py"
NAMES = ["META_LABEL_RE", "META_COLUMN_RE", "METHOD_NARRATION_RE", "SELF_AUDIT_RE",
         "INTERNAL_VOCAB_RE", "CHART_ENCODING_CLAIM_RE", "SELF_REFERENCE_RE", "RUN_LOGISTICS"]

def gate():
    spec = importlib.util.spec_from_file_location("_gate", CHECKER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def regexes(g, name):
    v = getattr(g, name)
    if isinstance(v, (tuple, list)): return [re.compile(x) for x in v]
    if isinstance(v, str): return [re.compile(v)]
    return [v]

def main(dirs: list[str]) -> int:
    g, bad = gate(), 0
    for d in dirs:
        root = pathlib.Path(d).expanduser() / "artifacts"
        hits = []
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".md", ".json", ".jsonl"):
                text = f.read_text(errors="replace")
                for n in NAMES:
                    for r in regexes(g, n):
                        for h in r.finditer(text):
                            hits.append(f"{f.relative_to(root)} : {n} : {h.group()!r}")
        print(f"{pathlib.Path(d).name}: 命中 {len(hits)}")
        for h in hits: print("   ", h)
        bad += len(hits)
    print(f"TOTAL HITS = {bad}  ⇒ 判据 3 {'PASS' if bad == 0 else 'FAIL'}")
    return 0 if bad == 0 else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
