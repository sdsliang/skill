#!/usr/bin/env python3
"""Fixture regression for check_cards.py. Zero deps, exits non-zero on mismatch.

    python3 evals/test_check_cards.py

The gate gained two rules that exist because a list can be wrong without being
obviously wrong:

  - **per-bucket cap 15** -- a 40-card bucket is not a reading list, and padding
    it with `weak` items is how a shortlist turns into a dump;
  - **score self-consistency** -- the score is the reviewer's judgement, so the
    script cannot check whether 78 is the *right* number. What it can check is
    that the five parts add up to it and none exceeds its ceiling; a total that
    does not add up means the number was invented rather than judged.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skill", "conference-result-triage", "scripts"))

import check_cards  # noqa: E402
import triage  # noqa: E402

failures = []


def expect(name, fails, needle):
    hits = [f for f in fails if needle in f]
    if not hits:
        failures.append(f"{name}: nothing matched {needle!r} in {len(fails)} fails")
        return
    print(f"  ok  {name}: {hits[0][:90]}")


def build_pool():
    rows = json.load(open(os.path.join(HERE, "fixtures", "mini_rows.json"), encoding="utf-8"))
    pool = triage.build_pools([triage.flat_row(r) for r in rows])
    by_esid = {}
    for bucket in triage.BUCKETS:
        for item in pool["pools"][bucket]["items"]:
            item["_bucket"] = bucket
            by_esid[str(item["esid"])] = item
    return pool, by_esid


def card(item, score=60, parts=None):
    """A card the gate should accept, apart from whatever the caller breaks."""
    text = str(item.get("results_text") or "")
    summary = next((s for s in text.replace("\n", " ").split(". ") if "%" in s), "")
    return {
        "esid": item["esid"],
        "abstract_id": None,
        "lba": bool(item.get("lba")),
        "manual": item.get("manual"),
        "bucket": item["_bucket"],
        "tag": "LBA" if item.get("lba") else "",
        "title": str(item.get("title") or item.get("trial") or "untitled"),
        "summary": summary or "ORR 40%",
        "why": "报告了主要终点读数，人群见摘要",
        "score": score,
        "score_parts": parts or {"evidence_strength": 20, "effect_size": 15,
                                 "clinical_impact": 15, "novelty": 5,
                                 "readout_maturity": 5},
        "drug": "", "target": "", "indication": "", "phase": "", "presentation": "",
        "stock": None,
    }


pool, by_esid = build_pool()
items = list(by_esid.values())
if len(items) < 2:
    raise SystemExit("fixture too small: need at least 2 pool items")

print("check_cards fixture:")

# 1. a hand-made card passes (proves the rest of the gate is not the thing failing)
base = [card(items[0], score=60)]
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": base}, by_esid)
size_only = [f for f in fails if not f.startswith("size:")]
if size_only:
    failures.append(f"clean card should pass: {size_only}")
else:
    print("  ok  clean card passes (only the list-size band complains)")

# 2. score_parts that do not sum to score
broken = dict(base[0], score=90)
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [broken]}, by_esid)
expect("parts sum != score", fails, "score_parts sum")

# 3. a part above its ceiling -- this is what a reviewer does when award-happy
over = card(items[0], score=60,
            parts={"evidence_strength": 40, "effect_size": 10, "clinical_impact": 5,
                   "novelty": 3, "readout_maturity": 2})
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [over]}, by_esid)
expect("part over ceiling", fails, "must be an integer 0-30")

# 4. score outside 0-100
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], score=140)]}, by_esid)
expect("score out of range", fails, "must be an integer 0-100")

# 5. per-bucket cap 15: sixteen cards in one bucket must be refused
many = [card(items[i % len(items)]) for i in range(check_cards.PER_BUCKET_CAP + 1)]
same_bucket = many[0]["bucket"]
for c in many:
    c["bucket"] = same_bucket
fails, _ = check_cards.check({"conference": "T", "count": len(many), "cards": many}, by_esid)
expect(f"{same_bucket} over 15", fails, "> cap 15")

if failures:
    print(f"\nFAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
print("\nfixture OK")
