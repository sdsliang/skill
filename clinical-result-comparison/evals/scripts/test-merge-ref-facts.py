#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone subprocess tests for scripts/merge_ref_facts.py.

    python3 evals/scripts/test-merge-ref-facts.py
    python3 evals/scripts/test-merge-ref-facts.py -v
"""

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
SCRIPT = REPO / "skill" / "multi-clinical-result-comparison" / "scripts" / "merge_ref_facts.py"


def fact(fact_id: str, ref: str) -> dict:
    return {
        "id": fact_id, "ref": ref, "study": "HARMONi-6", "kind": "有效性", "endpoint": "OS",
        "arm": "AK112 组", "value": "0.60", "unit": "", "quote": "中位 OS 为 0.60",
    }


class MergeRefFactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="merge-ref-facts-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.work = self.root / "work"
        self.work.mkdir(parents=True)
        self.refs = self.work / "refs.json"
        self.refs.write_text(json.dumps({
            "ref_1": {"esid": "24_37_1", "source_file": "work/sources/ref_1.txt", "trial_abbreviation": "HARMONi-6"},
            "ref_2": {"esid": "24_37_2", "source_file": "work/sources/ref_2.txt", "trial_abbreviation": "HARMONi-6"},
            "ref_3": {"esid": "24_37_3", "source_file": "work/sources/ref_3.txt", "trial_abbreviation": "HARMONi-6"},
        }), encoding="utf-8")

    def shard(self, name: str, payload) -> Path:
        path = self.work / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--shards", str(self.work), "--refs", str(self.refs),
             "--out", str(self.work / "facts.json"), *args],
            capture_output=True, text=True, cwd=str(self.root),
        )

    def merged(self) -> dict:
        return json.loads((self.work / "facts.json").read_text(encoding="utf-8"))

    # ── happy path ───────────────────────────────────────────────────────────────
    def test_merges_shards_in_ref_order(self) -> None:
        self.shard("facts.ref_3.json", {"records": [{"ref": "ref_3", "identity": "c", "conclusion": "k"}],
                                        "facts": [fact("r3-a", "ref_3")]})
        self.shard("facts.ref_1.json", {"records": [{"ref": "ref_1", "identity": "a", "conclusion": "k"}],
                                        "facts": [fact("r1-a", "ref_1"), fact("r1-b", "ref_1")]})
        self.shard("facts.ref_2.json", {"records": [{"ref": "ref_2", "identity": "b", "conclusion": "k"}],
                                        "facts": [fact("r2-a", "ref_2")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.merged()
        self.assertEqual([f["id"] for f in data["facts"]], ["r1-a", "r1-b", "r2-a", "r3-a"])
        self.assertEqual([r["ref"] for r in data["records"]], ["ref_1", "ref_2", "ref_3"])
        self.assertIn("WROTE", proc.stdout)

    def test_accepts_a_bare_list_of_facts(self) -> None:
        self.shard("facts.ref_1.json", [fact("r1-a", "ref_1")])
        self.shard("facts.ref_2.json", {"facts": [fact("r2-a", "ref_2")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.merged()["facts"]), 2)

    def test_output_keeps_the_facts_json_shape(self) -> None:
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_1")]})
        self.run_script()
        data = self.merged()
        self.assertEqual(sorted(data), ["facts", "records"])

    def test_omitted_source_file_survives_the_merge(self) -> None:
        # The shard contract drops `source_file` (build_ledger.py derives it from the ref); the merge
        # must not invent one, or the derived default would be shadowed by a wrong path.
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_1")]})
        self.run_script()
        self.assertNotIn("source_file", self.merged()["facts"][0])

    def test_missing_ref_is_a_warning_not_a_failure(self) -> None:
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_1")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("WARN: ref_2 has no fact", proc.stderr)
        self.assertIn("WARN: ref_3 has no fact", proc.stderr)

    # ── the split itself is checked ──────────────────────────────────────────────
    def test_duplicate_fact_id_across_shards_fails_the_merge(self) -> None:
        self.shard("facts.ref_1.json", {"facts": [fact("shared", "ref_1")]})
        self.shard("facts.ref_2.json", {"facts": [fact("shared", "ref_2")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("already used by", proc.stderr)
        self.assertFalse((self.work / "facts.json").exists(), "a failing merge must write nothing")

    def test_duplicate_record_ref_across_shards_fails_the_merge(self) -> None:
        record = {"ref": "ref_1", "identity": "a", "conclusion": "k"}
        self.shard("facts.ref_1.json", {"records": [record], "facts": [fact("r1-a", "ref_1")]})
        self.shard("facts.ref_2.json", {"records": [record]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("is already produced by", proc.stderr)

    def test_unknown_ref_fails_the_merge(self) -> None:
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_9")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("is not in refs.json", proc.stderr)

    def test_fact_without_id_fails_the_merge(self) -> None:
        broken = fact("r1-a", "ref_1")
        del broken["id"]
        self.shard("facts.ref_1.json", {"facts": [broken]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("has no `id`", proc.stderr)

    def test_empty_shard_fails_the_merge(self) -> None:
        self.shard("facts.ref_1.json", {"records": [], "facts": []})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("no `records` and no `facts`", proc.stderr)

    def test_unreadable_shard_fails_the_merge(self) -> None:
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_1")]})
        (self.work / "facts.ref_2.json").write_text("{not json", encoding="utf-8")
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("cannot read as JSON", proc.stderr)

    # ── guards about the inputs ──────────────────────────────────────────────────
    def test_no_shard_files_is_an_error(self) -> None:
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("no shard file matching", proc.stderr)

    def test_missing_refs_is_an_error(self) -> None:
        self.refs.unlink()
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_1")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("run prep_sources.py first", proc.stderr)

    def test_check_writes_nothing(self) -> None:
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_1")]})
        proc = self.run_script("--check")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("check only", proc.stdout)
        self.assertFalse((self.work / "facts.json").exists())

    def test_existing_output_is_untouched_when_the_merge_fails(self) -> None:
        (self.work / "facts.json").write_text('{"records": [], "facts": []}\n', encoding="utf-8")
        self.shard("facts.ref_1.json", {"facts": [fact("r1-a", "ref_9")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertEqual(json.loads((self.work / "facts.json").read_text(encoding="utf-8"))["facts"], [])

    def test_merged_output_compiles_with_build_ledger(self) -> None:
        ledger_script = REPO / "skill" / "multi-clinical-result-comparison" / "scripts" / "build_ledger.py"
        sources = self.work / "sources"
        sources.mkdir()
        (sources / "ref_1.txt").write_text("中位 OS 为 0.60。\n", encoding="utf-8")
        self.shard("facts.ref_1.json", {"records": [{"ref": "ref_1", "identity": "HARMONi-6", "conclusion": "k"}],
                                        "facts": [fact("r1-a", "ref_1")]})
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        compile_proc = subprocess.run(
            [sys.executable, "-B", str(ledger_script), "--facts", str(self.work / "facts.json"),
             "--refs", str(self.refs), "--sources", str(sources),
             "--out", str(self.work / "ledger.json")],
            capture_output=True, text=True, cwd=str(self.root),
        )
        self.assertEqual(compile_proc.returncode, 0, compile_proc.stderr)
        ledger = json.loads((self.work / "ledger.json").read_text(encoding="utf-8"))
        # derived source_file survives the round trip through both scripts
        self.assertTrue(ledger["facts"][0]["source_file"].endswith("ref_1.txt"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
