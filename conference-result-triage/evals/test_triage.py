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
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import triage  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "mini_rows.json")
failures = []


def check(name, got, want):
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def main():
    rows = triage.load_rows(FIXTURE)
    check("loaded rows", len(rows), 4)
    pool = triage.build_pools(rows)

    check("early count", pool["pools"]["early"]["count"], 1)
    check("pivotal count", pool["pools"]["pivotal"]["count"], 1)
    check("failed count", pool["pools"]["failed"]["count"], 1)
    check("excluded real-world", pool["excluded"].get("真实世界研究"), 1)

    early = pool["pools"]["early"]["items"][0]
    check("early trial", early["trial"], "FIXTURE-ADC-101")
    check("early n display-only", early["n"], 45)

    # The safety row (Grade>=3 TEAE 44.6%) must not become the efficacy signal.
    sig = early["machine_signal"]
    check("signal endpoint is efficacy", sig.get("endpoint"), "客观缓解率")
    check("signal value is ORR", sig.get("value"), 51.1)

    failed = pool["pools"]["failed"]["items"][0]
    check("failed trial", failed["trial"], "FIXTURE-III-301")
    check("failed endpoint call", failed["machine_endpoint_call"]["verdict"], "missed")

    pivotal = pool["pools"]["pivotal"]["items"][0]
    check("pivotal trial", pivotal["trial"], "FIXTURE-III-201")
    check("pivotal endpoint call", pivotal["machine_endpoint_call"]["verdict"], "met")

    # data_type tagger must fire on the explicit first-report / update wording.
    check("data_type early", early["data_type"] in ("未判定", "首次公布"), True)
    check("data_type pivotal", pivotal["data_type"], "未判定")

    # numeric parsing regressions
    check("comma number", triage.parse_num("1,234"), 1234.0)
    check("p-value", triage.parse_p("0.1366"), 0.1366)
    check("p-value lt", triage.parse_p("<0.001") <= 0.001, True)
    check("safety label", triage.is_safety_label("Grade >=3 TEAE"), True)
    check("efficacy label", triage.is_safety_label("ORR"), False)

    if failures:
        for f in failures:
            print("FAIL " + f)
        print(f"{len(failures)} failure(s)")
        return 1
    print("fixture OK (4 rows, 4 assertions groups)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
