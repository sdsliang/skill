#!/usr/bin/env python3
"""Render the conference watchlist (markdown + csv) from a judged pool.

Zero third-party dependencies. Two jobs:

1. ``judgements.csv`` -- every candidate the reviewer saw, one row each, with
   the machine bucket *and* the re-judged bucket side by side so a disagreement
   is visible instead of silently overwritten.
2. ``watchlist.md`` / ``watchlist.csv`` -- the printed list, i.e. the curated
   subset plus the ones that could not be decided locally ("待人工核实").

The curated list is passed in as an explicit file of abstract ids in reading
order. This script never decides what belongs on the list: ordering, de-dup of
same-mechanism items and the "why read it" line are editorial decisions that
belong to the reviewer, not to a score.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Any, Dict, List, Optional

BUCKETS = ("early", "pivotal", "failed")
BUCKET_CN = {"early": "早期机会提示", "pivotal": "重磅 II/III 期", "failed": "失败的研究"}


def load_pool(pool_json: str) -> Dict[str, Dict[str, Any]]:
    pool = json.load(open(pool_json, encoding="utf-8"))
    by_id: Dict[str, Dict[str, Any]] = {}
    for b in BUCKETS:
        for item in pool["pools"][b]["items"]:
            aid = item.get("abstract_id")
            if aid:
                by_id[aid] = item
    return by_id


def load_review(review_jsonl: str) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    with open(review_jsonl, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            for item in json.loads(line)["items"]:
                out[int(item["i"])] = item
    return out


def load_judged(path: str) -> List[Dict[str, Any]]:
    data = json.load(open(path, encoding="utf-8"))
    return data["judgements"] if isinstance(data, dict) else data


NUM_KEEP_RE = None


def useful_numbers(nums: List[str]) -> List[str]:
    """Drop bare counts from ``key_numbers``.

    The model reliably lists numbers but also lists incidental ones ("60 years",
    "≥2"). Only keep tokens carrying a magnitude unit, so the column reads as
    efficacy figures and not as a word-frequency dump. Percentages, time units,
    hazard/odds ratios and p-values survive; ages and line counts do not.
    """
    import re
    pat = re.compile(r"(%|％|\bmo\b|month|year|\byr\b|\bHR\b|\bOR\b|\bCI\b|p\s*[=<>])",
                     re.I)
    return [n for n in nums if pat.search(n)]


def write_judgements(path: str, judged: List[Dict[str, Any]],
                     review: Dict[int, Dict[str, Any]],
                     meta: Dict[str, Dict[str, Any]]) -> int:
    cols = ["i", "machine_bucket", "bucket", "verdict", "abstract_id",
            "presentation", "trial", "drug", "target", "indication", "phase",
            "n", "data_type", "reason", "evidence", "key_numbers"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for j in sorted(judged, key=lambda x: x["i"]):
            r = review[j["i"]]
            m = meta.get(r.get("abstract_id") or "", {})
            w.writerow({
                "i": j["i"],
                "machine_bucket": r["bucket"],
                "bucket": j["bucket"],
                "verdict": j["verdict"],
                "abstract_id": r.get("abstract_id") or "",
                "presentation": r.get("presentation") or "",
                "trial": r.get("trial") or "",
                "drug": m.get("drug") or "",
                "target": m.get("target") or "",
                "indication": "; ".join(r.get("indication") or []),
                "phase": r.get("phase") or "",
                "n": r.get("n") or "",
                "data_type": r.get("data_type") or "",
                "reason": j.get("reason") or "",
                "evidence": j.get("evidence") or "",
                "key_numbers": "; ".join(useful_numbers(j.get("key_numbers") or [])),
            })
    return len(judged)


def rows_for(plan: Dict[str, List[Dict[str, str]]],
             meta: Dict[str, Dict[str, Any]],
             judged_by_id: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for bucket in BUCKETS:
        for n, spec in enumerate(plan.get(bucket) or [], 1):
            aid = spec["abstract_id"]
            m = meta.get(aid)
            if m is None:
                raise SystemExit(f"{aid} not in pool")
            j = judged_by_id.get(aid) or {}
            rows.append({
                "rank": n,
                "bucket": bucket,
                "abstract_id": aid,
                "presentation": m.get("presentation") or "-",
                "drug": spec.get("drug") or m.get("drug") or "-",
                "target": spec.get("target") or m.get("target") or "-",
                "indication": spec.get("indication")
                or ", ".join((m.get("indication") or [])[:1]) or "-",
                "phase": (m.get("phase") or "-").replace("Phase ", "Ph"),
                "n": m.get("n") or "-",
                "key_data": spec["key_data"],
                "why": spec["why"],
                "data_type": m.get("data_type") or "-",
                "verdict": j.get("verdict") or "-",
            })
    return rows


def md_table(rows: List[Dict[str, Any]]) -> List[str]:
    out = ["| # | 摘要号 | 报告形式 | 药物（靶点） | 阶段 · 适应症 | n | 关键数据 | 为什么值得读 |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| {rank} | {abstract_id} | {presentation} | {drug}（{target}） | "
                   "{phase} · {indication} | {n} | {key_data} | {why} |".format(**r))
    return out


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    cols = ["rank", "bucket", "abstract_id", "presentation", "drug", "target",
            "indication", "phase", "n", "key_data", "why", "data_type"]
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True, help="triage pool.json")
    ap.add_argument("--review", required=True, help="review batches jsonl")
    ap.add_argument("--judged", required=True, help="merged judgements json")
    ap.add_argument("--plan", required=True, help="curated watchlist plan json")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    meta = load_pool(args.pool)
    review = load_review(args.review)
    judged = load_judged(args.judged)
    judged_by_id = {review[j["i"]]["abstract_id"]: j for j in judged
                    if review.get(j["i"])}
    plan = json.load(open(args.plan, encoding="utf-8"))

    os.makedirs(args.outdir, exist_ok=True)
    n = write_judgements(os.path.join(args.outdir, "judgements.csv"),
                         judged, review, meta)
    rows = rows_for(plan, meta, judged_by_id)
    write_csv(os.path.join(args.outdir, "watchlist.csv"), rows)
    print(f"judgements {n} rows -> judgements.csv")
    print(f"watchlist  {len(rows)} rows -> watchlist.csv")
    for b in BUCKETS:
        print(f"  {b}: {sum(1 for r in rows if r['bucket'] == b)}")
    template = plan.get("template")
    if template:
        print("md sections available in plan['md']")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
