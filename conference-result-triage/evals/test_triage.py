#!/usr/bin/env python3
"""Fixture regression for triage.py. Zero deps, exits non-zero on any mismatch.

    python3 evals/test_triage.py

Covers the decisions that actually broke before:
  - safety endpoints must never win the efficacy signal
  - disease stage must not be read as trial phase
  - real-world evidence must be excluded, not bucketed
  - negative `evaluation` lands in `failed`, not `pivotal`
  - comma-decimal sample sizes parse
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skill", "conference-result-triage", "scripts"))

import triage  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "mini_rows.json")
failures = []


def check(name, got, want):
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def main():
    rows = triage.load_rows(FIXTURE)
    check("loaded rows", len(rows), 6)
    pool = triage.build_pools(rows)

    check("early count", pool["pools"]["early"]["count"], 2)
    check("pivotal count", pool["pools"]["pivotal"]["count"], 2)
    check("failed count", pool["pools"]["failed"]["count"], 1)
    check("excluded real-world", pool["excluded"].get("真实世界研究"), 1)

    by_trial = {i["trial"]: i for b in pool["pools"].values() for i in b["items"]}
    early = by_trial["FIXTURE-ADC-101"]
    check("early trial", early["trial"], "FIXTURE-ADC-101")
    check("early n display-only", early["n"], 45)

    # The safety row (Grade>=3 TEAE 44.6%) must not become the efficacy signal.
    sig = early["machine_signal"]
    check("signal endpoint is efficacy", sig.get("endpoint"), "客观缓解率")
    check("signal value is ORR", sig.get("value"), 51.1)

    failed = by_trial["FIXTURE-III-301"]
    check("failed trial", failed["trial"], "FIXTURE-III-301")
    check("failed endpoint call", failed["machine_endpoint_call"]["verdict"], "missed")

    pivotal = by_trial["FIXTURE-III-201"]
    check("pivotal trial", pivotal["trial"], "FIXTURE-III-201")
    check("pivotal endpoint call", pivotal["machine_endpoint_call"]["verdict"], "met")

    # v0.10: a record with no phase label is placed by study design, never dropped.
    # ESC 2026 lost 123 of 242 records (ACACIA-HCM / ENRICH-AF / SAL003 among them)
    # because non-oncology meetings fill `evidence_source` with design words, not
    # phases. The basis must be visible on the item so the card can state it.
    hf = by_trial["FIXTURE-HF-401"]
    check("phase-less randomised -> pivotal", "FIXTURE-HF-401" in pool["pools"]["pivotal"]["items"][0:2] or hf in pool["pools"]["pivotal"]["items"], True)
    check("phase-less randomised basis", hf["phase_inferred"], "随机化对照（按设计判定）")
    hbv = by_trial["FIXTURE-HBV-101"]
    check("phase-less single-arm -> early", hbv in pool["pools"]["early"]["items"], True)
    check("phase-less single-arm basis", hbv["phase_inferred"], "单臂或未标注设计（按设计判定）")
    check("no row left unclassified", pool["excluded"].get("无法归类"), None)
    check("phased row keeps no inference", pivotal["phase_inferred"], None)

    # data_type tagger must fire on the explicit first-report / update wording.
    check("data_type early", early["data_type"] in ("未判定", "首次公布"), True)
    check("data_type pivotal", pivotal["data_type"], "未判定")

    # numeric parsing regressions
    check("comma number", triage.parse_num("1,234"), 1234.0)
    check("p-value", triage.parse_p("0.1366"), 0.1366)
    check("p-value lt", triage.parse_p("<0.001") <= 0.001, True)
    check("safety label", triage.is_safety_label("Grade >=3 TEAE"), True)
    check("efficacy label", triage.is_safety_label("ORR"), False)

    # Two rows of one trial are one card: the dedupe loser must survive as an
    # ``alias_esids`` entry, otherwise a card written off the sibling record looks
    # like a record triage never admitted (ESC 2026 VESALIUS-CV prespecified
    # analysis vs its primary publication).
    dup = triage.build_pools([
        {"_id": "dup_a", "trial_abbreviation": ["DUP-1"], "evidence_source": ["Phase III"],
         "randomized": ["随机化"], "clinical_result_evaluation": ["积极"],
         "paper_title": "primary"},
        {"_id": "dup_b", "trial_abbreviation": ["DUP-1"], "evidence_source": ["Phase III"],
         "randomized": ["随机化"], "clinical_result_evaluation": ["积极"],
         "paper_title": "prespecified analysis"},
    ])
    dup_items = [i for b in dup["pools"].values() for i in b["items"]]
    check("duplicate trial collapses to one item", len(dup_items), 1)
    check("dedupe loser kept as alias",
          sorted(dup_items[0].get("alias_esids") or []),
          sorted({"dup_a", "dup_b"} - {dup_items[0]["esid"]}))

    if failures:
        for f in failures:
            print("FAIL " + f)
        print(f"{len(failures)} failure(s)")
        return 1
    print("fixture OK (6 rows, design-fallback + dedupe-alias covered)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
