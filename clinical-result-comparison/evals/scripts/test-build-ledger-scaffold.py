#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone subprocess tests for build_ledger.py --scaffold."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
SCRIPT = REPO / "skill" / "multi-clinical-result-comparison" / "scripts" / "build_ledger.py"


class ScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="build-ledger-scaffold-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.sources = self.root / "work" / "sources"
        self.pull = self.root / "tool_results" / "pharmcube-query-clinical-result-with-params"
        self.sources.mkdir(parents=True)
        self.pull.mkdir(parents=True)
        self.refs = self.root / "work" / "refs.json"
        self.out = self.root / "work" / "facts.candidates.json"
        self.source_text = (
            "A realistic report states −8.3% at Week 16。"
            "The placebo result was -5.3% at Week 16。"
        )
        (self.sources / "ref_1.txt").write_text(self.source_text, encoding="utf-8")
        (self.sources / "ref_2.txt").write_text("A second source contains no matching result。\n", encoding="utf-8")
        self.refs.write_text(json.dumps({
            "ref_1": {"esid": "esid-1", "trial_abbreviation": "TRIAL-ONE",
                      "source_file": str(self.sources / "ref_1.txt")},
            "ref_2": {"esid": "esid-2", "trial_abbreviation": "TRIAL-TWO",
                      "source_file": str(self.sources / "ref_2.txt")},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        self.payload = {
            "clinical_result_extra_esid": "esid-1",
            "clinical_result_trial_abbreviation": [],
            "clinical_result_indication_name": ["示例疾病"],
            "clinical_result_randomized": ["随机化"],
            "clinical_result_blinded": ["双盲"],
            "clinical_result_trial_control": ["平行分组"],
            "clinical_result_positive_placebo_control": "安慰剂对照",
            "clinical_result_clinical_stage_cn": "III期",
            "clinical_result_projects": [{"associate_ids": ["NCT12345678", "EudraCT2024-000001-11"]}],
            "clinical_result_arms": [
                {"arm_id": "arm-abcdef12", "regimen_label": "Regimen A 100 mg"},
                {"arm_id": "arm-placebo", "regimen_label": "Placebo"},
            ],
            "clinical_result_study_results": [
                {"result": "−8.3", "result_unit": "%", "arm_id": "arm-abcdef12",
                 "endpoint_id": "endpoint-12345678", "endpoint_attribute": "有效性",
                 "endpoint_label": "Arterial Wall Inflammation – MDS TBR | percentage change; Most-diseased-segment target-to-background ratio (MDS TBR); Week 16",
                 "outcome_ci": "-10.0 to -6.6", "outcome_p_value": "0.01"},
                {"result": "-5.3", "result_unit": "%", "arm_id": "arm-placebo",
                 "endpoint_id": "endpoint-12345678", "endpoint_attribute": "安全性",
                 "endpoint_label": "Arterial Wall Inflammation – MDS TBR | percentage change; Most-diseased-segment target-to-background ratio (MDS TBR); Week 16",
                 "outcome_ci": "", "outcome_p_value": ""},
                {"result": "70.5", "result_unit": "%", "arm_id": "arm-abcdef12",
                 "endpoint_id": "endpoint-missing", "endpoint_attribute": "unknown-kind",
                 "endpoint_label": "Lipoprotein(a) | percentage change; Week 36",
                 "outcome_ci": "", "outcome_p_value": ""},
                {"result": "NR", "result_unit": "%", "arm_id": "arm-abcdef12",
                 "endpoint_id": "endpoint-nr", "endpoint_attribute": "有效性", "endpoint_label": "NR"},
                {"result": "", "result_unit": "%", "arm_id": "arm-abcdef12",
                 "endpoint_id": "endpoint-empty", "endpoint_attribute": "有效性", "endpoint_label": "Empty"},
            ],
        }
        self.write_payload([self.payload])

    def write_payload(self, records: list[dict]) -> None:
        (self.pull / "call_1.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n", encoding="utf-8")

    def run_script(self, *args: str, expect: int | None = None) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], cwd=self.root,
                              capture_output=True, text=True, check=False)
        if expect is not None:
            self.assertEqual(proc.returncode, expect,
                             f"exit={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

    def scaffold(self, *extra: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        return self.run_script("--scaffold", "--tool-results", self.root / "tool_results",
                               "--refs", self.refs, "--sources", self.sources, "--out", self.out,
                               *extra, expect=expect)

    def candidate(self) -> dict:
        return json.loads(self.out.read_text(encoding="utf-8"))

    def test_happy_path_is_usable_by_default_ledger_mode(self):
        proc = self.scaffold()
        candidate = self.candidate()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("WROTE", proc.stdout)
        self.assertIn("1 record(s), 3 fact(s)", proc.stdout)
        self.assertEqual(set(candidate), {"records", "facts", "_notes"})
        self.assertEqual(len(candidate["records"]), 1)
        self.assertEqual(len(candidate["facts"]), 3)
        for record in candidate["records"]:
            record["conclusion"] = "模型补写的披露结论。"
        for fact in candidate["facts"]:
            if not fact["quote"]:
                fact["quote"] = "模型核对：70.5% 出现在后续比较。"
                (self.sources / "ref_1.txt").write_text(
                    self.source_text + "模型核对：70.5% 出现在后续比较。", encoding="utf-8")
        facts = self.root / "work" / "facts.json"
        facts.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
        ledger = self.root / "work" / "ledger.json"
        compiled = self.run_script("--facts", facts, "--out", ledger, "--refs", self.refs, expect=0)
        self.assertIn("WROTE", compiled.stdout)
        self.assertTrue(ledger.is_file())
        self.assertEqual(set(json.loads(ledger.read_text(encoding="utf-8"))), {"records", "facts"})

    def test_values_are_verbatim_and_unusable_results_are_reported(self):
        proc = self.scaffold()
        candidate = self.candidate()
        self.assertEqual([fact["value"] for fact in candidate["facts"]], ["−8.3", "-5.3", "70.5"])
        self.assertNotIn("NR", [fact["value"] for fact in candidate["facts"]])
        self.assertIn("跳过 2 条结果", proc.stdout)
        self.assertIn("所有 value 均逐字复制", proc.stdout)

    def test_endpoint_timepoint_and_assessment_split(self):
        self.scaffold()
        fact = self.candidate()["facts"][0]
        self.assertEqual(fact["endpoint"], "Arterial Wall Inflammation – MDS TBR")
        self.assertEqual(fact["assessment"], "percentage change；Most-diseased-segment target-to-background ratio (MDS TBR)")
        self.assertEqual(fact["timepoint"], "Week 16")
        self.assertEqual(fact["statistics"], "95% CI -10.0 to -6.6；p=0.01")

    def test_quote_found_and_missing_quote_is_explicit(self):
        (self.sources / "ref_1.txt").write_text(
            "A realistic report states −8.3% at Week 16。The placebo result was -5.3% at Week 16。",
            encoding="utf-8")
        proc = self.scaffold()
        facts = {fact["value"]: fact for fact in self.candidate()["facts"]}
        self.assertEqual(facts["−8.3"]["quote"], "A realistic report states -8.3% at Week 16")
        self.assertEqual(facts["-5.3"]["quote"], "The placebo result was -5.3% at Week 16")
        self.assertEqual(facts["70.5"]["quote"], "")
        self.assertIn("缺少 quote 的 fact id", proc.stdout)

    def test_unmapped_esid_is_skipped_and_missing_refs_is_exit_3(self):
        self.write_payload([self.payload, {"clinical_result_extra_esid": "not-in-refs",
                                           "clinical_result_study_results": []}])
        proc = self.scaffold()
        self.assertIn("esid 未映射到 refs.json", proc.stdout)
        self.assertIn("not-in-refs", proc.stdout)
        self.out.unlink()
        missing = self.root / "work" / "missing-refs.json"
        proc = self.run_script("--scaffold", "--tool-results", self.root / "tool_results",
                               "--refs", missing, "--sources", self.sources, "--out", self.out, expect=3)
        self.assertIn("run prep_sources.py first", proc.stderr)
        self.assertFalse(self.out.exists())

    def test_unwritable_out_returns_exit_2(self):
        blocked = self.root / "blocked"
        blocked.write_text("not a directory", encoding="utf-8")
        proc = self.run_script("--scaffold", "--tool-results", self.root / "tool_results",
                               "--refs", self.refs, "--sources", self.sources,
                               "--out", blocked / "candidate.json", expect=2)
        self.assertIn("ERROR: cannot write", proc.stderr)

    def test_scaffold_does_not_read_facts_or_write_ledger(self):
        facts = self.root / "work" / "facts.json"
        facts.write_text("this is deliberately not JSON", encoding="utf-8")
        self.scaffold()
        self.assertTrue(self.out.exists())
        self.assertFalse((self.root / "work" / "ledger.json").exists())

    def test_anti_empty_artifact(self):
        self.scaffold()
        candidate = self.candidate()
        self.assertEqual(len(candidate["records"]), 1)
        self.assertGreaterEqual(len(candidate["facts"]), 3)
        self.assertTrue(candidate["_notes"])
        ids = [fact["id"] for fact in candidate["facts"]]
        self.assertEqual(len(ids), len(set(ids)))
        for fact in candidate["facts"]:
            for key in ("id", "endpoint", "value", "unit"):
                self.assertTrue(fact[key], f"empty {key}: {fact}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
