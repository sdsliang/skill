#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Subprocess tests for build_ledger.py --apply-review."""

from __future__ import annotations

import copy
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


class ReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="build-ledger-review-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "work").mkdir()
        self.source = self.root / "work" / "source.txt"
        self.source.write_text(
            "The kept value is 1 percent. The updated value is 2 percent. "
            "The added value is 3 percent.\n", encoding="utf-8")
        self.candidates_path = self.root / "work" / "facts.candidates.json"
        self.review_path = self.root / "work" / "review.json"
        self.facts_path = self.root / "work" / "facts.json"
        self.ledger_path = self.root / "work" / "ledger.json"
        self.candidates = self.make_candidates()
        self.write(self.candidates_path, self.candidates)

    def write(self, path: Path, value) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def fact(self, fact_id: str, value: str, quote: str) -> dict:
        return {
            "id": fact_id, "ref": "ref_1", "study": "TRIAL-ONE", "version": "",
            "endpoint": "Biomarker change", "arm": "Dose A", "population": "",
            "timepoint": "Week 16", "assessment": "", "kind": "有效性",
            "value": value, "unit": "%", "statistics": "", "source_file": str(self.source),
            "quote": quote,
        }

    def make_candidates(self) -> dict:
        return {
            "records": [{"ref": "ref_1", "trial": "TRIAL-ONE", "identity": "TRIAL-ONE",
                         "conclusion": ""}],
            "facts": [
                self.fact("keep-fact", "1", "The kept value is 1 percent."),
                self.fact("update-fact", "1", "The kept value is 1 percent."),
                self.fact("drop-fact", "1", "The kept value is 1 percent."),
            ],
            "_notes": ["candidate rows require review"],
        }

    def review(self) -> dict:
        return {
            "records": [{"ref": "ref_1", "trial": "TRIAL-ONE", "identity": "TRIAL-ONE",
                         "conclusion": "The reviewed record conclusion."}],
            "decisions": [
                {"id": "keep-fact", "action": "keep"},
                {"id": "update-fact", "action": "update", "changes": {
                    "value": "2", "quote": "The updated value is 2 percent.", "statistics": "95% CI 1-3",
                }},
                {"id": "drop-fact", "action": "drop"},
            ],
            "additions": [self.fact("added-fact", "3", "The added value is 3 percent.")],
        }

    def run_script(self, *args: str, expect: int | None = None) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], cwd=self.root,
                              capture_output=True, text=True, check=False)
        if expect is not None:
            self.assertEqual(proc.returncode, expect,
                             f"exit={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

    def apply(self, review: dict | None = None, *extra: str, expect: int | None = 0):
        self.write(self.review_path, review if review is not None else self.review())
        return self.run_script("--apply-review", self.review_path, *extra, expect=expect)

    def test_full_review_keeps_updates_drops_and_adds_without_mutating_inputs(self):
        candidate_before = self.candidates_path.read_bytes()
        review = self.review()
        self.write(self.review_path, review)
        review_before = self.review_path.read_bytes()
        proc = self.run_script("--apply-review", self.review_path, expect=0)
        self.assertIn("WROTE work/facts.json", proc.stdout)
        self.assertEqual(self.candidates_path.read_bytes(), candidate_before)
        self.assertEqual(self.review_path.read_bytes(), review_before)
        self.assertEqual({item["id"] for item in review["decisions"]},
                         {item["id"] for item in self.candidates["facts"]})
        output = json.loads(self.facts_path.read_text(encoding="utf-8"))
        self.assertEqual(list(output), ["records", "facts"])
        self.assertEqual(output["records"][0]["conclusion"], "The reviewed record conclusion.")
        self.assertEqual([fact["id"] for fact in output["facts"]], ["keep-fact", "update-fact", "added-fact"])
        by_id = {fact["id"]: fact for fact in output["facts"]}
        self.assertEqual(by_id["keep-fact"], self.candidates["facts"][0])
        self.assertEqual(by_id["update-fact"]["value"], "2")
        self.assertEqual(by_id["update-fact"]["statistics"], "95% CI 1-3")
        self.assertEqual(by_id["added-fact"]["quote"], "The added value is 3 percent.")
        self.assertFalse(self.ledger_path.exists(), "review assembly must not write a ledger")

    def test_assembled_facts_are_usable_by_the_existing_compiler(self):
        self.apply()
        proc = self.run_script("--facts", self.facts_path, "--out", self.ledger_path, expect=0)
        self.assertIn("WROTE", proc.stdout)
        ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        self.assertEqual([fact["id"] for fact in ledger["facts"]], ["keep-fact", "update-fact", "added-fact"])
        self.assertTrue(all(fact["quote"] for fact in ledger["facts"]))

    def test_downstream_compiler_rejects_bad_reviewed_value_or_quote_and_preserves_ledger(self):
        self.apply()
        self.ledger_path.write_text("existing ledger\n", encoding="utf-8")
        bad_value = self.review()
        bad_value["decisions"][1]["changes"]["value"] = "9"
        self.apply(bad_value, expect=0)
        proc = self.run_script("--facts", self.facts_path, "--out", self.ledger_path, expect=3)
        self.assertIn("absent from `quote`", proc.stderr)
        self.assertEqual(self.ledger_path.read_text(encoding="utf-8"), "existing ledger\n")

        bad_quote = self.review()
        bad_quote["decisions"][1]["changes"]["quote"] = "This sentence is not in the source."
        self.apply(bad_quote, expect=0)
        proc = self.run_script("--facts", self.facts_path, "--out", self.ledger_path, expect=3)
        self.assertIn("not an exact substring", proc.stderr)
        self.assertEqual(self.ledger_path.read_text(encoding="utf-8"), "existing ledger\n")

    def test_review_contract_failures_write_nothing_and_preserve_existing_output(self):
        cases: list[tuple[str, object, str]] = []

        missing = self.review()
        del missing["decisions"][-1]
        cases.append(("missing decision", missing, "missing candidate fact id"))

        duplicate = self.review()
        duplicate["decisions"].append(copy.deepcopy(duplicate["decisions"][0]))
        cases.append(("duplicate decision", duplicate, "duplicate decision id"))

        unknown_key = self.review()
        unknown_key["decisions"][0]["unexpected"] = True
        cases.append(("unknown decision key", unknown_key, "unknown key"))

        keep_changes = self.review()
        keep_changes["decisions"][0]["changes"] = {"value": "7"}
        cases.append(("changes on keep", keep_changes, "allowed only for update"))

        id_change = self.review()
        id_change["decisions"][1]["changes"] = {"id": "other-id"}
        cases.append(("id change", id_change, "immutable key"))

        no_op_update = self.review()
        del no_op_update["decisions"][1]["changes"]
        cases.append(("no-op update", no_op_update, "requires non-empty changes"))

        invalid_action = self.review()
        invalid_action["decisions"][0]["action"] = "accept"
        cases.append(("invalid action", invalid_action, "must be keep, update, or drop"))

        dropped_collision = self.review()
        dropped_collision["additions"] = [self.fact("drop-fact", "3", "The added value is 3 percent.")]
        cases.append(("collision with dropped id", dropped_collision, "including dropped ids"))

        duplicate_addition = self.review()
        duplicate_addition["additions"].append(copy.deepcopy(duplicate_addition["additions"][0]))
        cases.append(("duplicate addition", duplicate_addition, "duplicate addition id"))

        malformed_addition = self.review()
        malformed_addition["additions"] = [{"id": "new-fact"}]
        cases.append(("incomplete addition", malformed_addition, "missing non-empty `ref`"))

        missing_record = self.review()
        missing_record["records"] = []
        cases.append(("missing reviewed record", missing_record, "missing candidate ref"))

        for name, review, expected in cases:
            with self.subTest(name=name):
                self.write(self.review_path, review)
                self.facts_path.write_text("existing facts\n", encoding="utf-8")
                before = self.facts_path.read_bytes()
                proc = self.run_script("--apply-review", self.review_path, expect=3)
                self.assertIn(expected, proc.stderr)
                self.assertEqual(self.facts_path.read_bytes(), before)

    def test_malformed_review_shapes_and_custom_candidates_path_are_enforced(self):
        malformed_cases = []
        missing_top = self.review()
        del missing_top["additions"]
        malformed_cases.append((missing_top, "missing top-level key"))
        wrong_decisions = self.review()
        wrong_decisions["decisions"] = {"keep-fact": "keep"}
        malformed_cases.append((wrong_decisions, "review.decisions must be an array"))
        wrong_changes = self.review()
        wrong_changes["decisions"][1]["changes"] = []
        malformed_cases.append((wrong_changes, "changes must be an object"))
        bad_record_key = self.review()
        bad_record_key["records"][0]["note"] = "not allowed"
        malformed_cases.append((bad_record_key, "unknown key"))
        for review, expected in malformed_cases:
            with self.subTest(expected=expected):
                proc = self.apply(review, expect=3)
                self.assertIn(expected, proc.stderr)

        custom = self.root / "work" / "custom-candidates.json"
        self.candidates_path.rename(custom)
        proc = self.apply(None, "--candidates", custom, expect=0)
        self.assertIn("WROTE", proc.stdout)

    def test_unknown_decision_id_and_unknown_review_top_level_are_rejected(self):
        unknown_id = self.review()
        unknown_id["decisions"][0]["id"] = "not-a-candidate"
        self.apply(unknown_id, expect=3)
        self.assertIn("not an existing candidate fact", self.run_script("--apply-review", self.review_path).stderr)

        extra = self.review()
        extra["notes"] = "not part of the contract"
        proc = self.apply(extra, expect=3)
        self.assertIn("unknown top-level key", proc.stderr)

    def test_malformed_types_fail_without_traceback(self):
        for collection, key in [("records", "ref"), ("additions", "id"), ("decisions", "id")]:
            review = self.review()
            review[collection][0][key] = []
            proc = self.apply(review, expect=3)
            self.assertNotIn("Traceback", proc.stderr)

    def test_inputs_cannot_be_overwritten(self):
        self.write(self.review_path, self.review())
        for path in [self.candidates_path, self.review_path]:
            before = path.read_bytes()
            self.run_script("--apply-review", self.review_path, "--out", path, expect=3)
            self.assertEqual(path.read_bytes(), before)

    def test_empty_or_unknown_ref_updates_are_rejected(self):
        for changes in [{"ref": "ref_9"}, {"quote": ""}]:
            review = self.review()
            review["decisions"][1]["changes"] = changes
            self.apply(review, expect=3)
        review = self.review()
        review["decisions"] = [{"id": f["id"], "action": "drop"} for f in self.candidates["facts"]]
        review["additions"] = []
        self.apply(review, expect=3)

    def test_missing_inputs_and_unwritable_output_are_io_errors(self):
        missing = self.root / "work" / "missing.json"
        proc = self.run_script("--apply-review", missing, expect=2)
        self.assertIn("ERROR: cannot read", proc.stderr)
        self.write(self.review_path, self.review())
        blocked = self.root / "blocked"
        blocked.write_text("file", encoding="utf-8")
        proc = self.run_script("--apply-review", self.review_path, "--out", blocked / "facts.json", expect=2)
        self.assertIn("ERROR: cannot write", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
