#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the packaged prose gate (`scripts/tell-scan.py`).

Run:
    python3 evals/scripts/test-tell-scan.py           # all tests
    python3 evals/scripts/test-tell-scan.py -v        # verbose

Run it as a script with `python3` (the repo pattern) — not through unittest
discovery of the directory.

Two things are covered here: the scanner's *contract* (exit 0/3/2, strong vs
weak, `--allow`, `--json`, read-only) and the *wiring* that would otherwise rot
silently — the bundled copy must stay byte-identical with the upstream
`report-humanizer-zh` repo it came from, and both the checklist and the Skill's
own text must keep naming it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
SKILL = REPO / "skill" / "multi-clinical-result-comparison"
SCANNER = SKILL / "scripts" / "tell-scan.py"
CHECKLIST = SKILL / "references" / "prose-style-zh.md"
SKILL_MD = SKILL / "SKILL.md"
UPSTREAM = (REPO.parent / "report-humanizer-zh" / "skill" / "report-humanizer-zh"
            / "scripts" / "tell-scan.py")

CLEAN = "# 试验结果\n\n该方案在主要终点上优于对照组（HR 0.62，95% CI 0.48–0.80，p<0.001）。\n"
STRONG = ("# 试验结果\n\n我们共检索到 27 条披露，去掉 9 条无终点数据者后，对剩余记录逐条抽取终点，"
          "得到如下结论：该方案优于对照组。相信在不久的将来会有更多数据。\n")
WEAK = "# 试验结果\n\n该数据值得关注。\n"
NUMERIC = "# 试验结果\n\n中位 PFS 11.1 个月（95% CI 9.9–NE），≥3 级出血 12%。\n"


class TellScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="tell-scan-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, ignore_errors=True))

    def write(self, name: str, body: str) -> Path:
        path = self.root / name
        path.write_text(body, encoding="utf-8")
        return path

    def scan(self, *args: object) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(SCANNER), *[str(a) for a in args]],
                              capture_output=True, text=True)

    # ── the contract ────────────────────────────────────────────────────────

    def test_clean_report_passes(self) -> None:
        proc = self.scan(self.write("clean.md", CLEAN))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("强 0", proc.stdout)

    def test_strong_hit_fails_closed_and_names_the_rule(self) -> None:
        proc = self.scan(self.write("strong.md", STRONG))
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("S-PROC-01", proc.stdout)
        self.assertIn("[强]", proc.stdout)

    def test_weak_hit_alone_does_not_fail_unless_asked(self) -> None:
        path = self.write("weak.md", WEAK)
        self.assertEqual(self.scan(path).returncode, 0)
        self.assertEqual(self.scan(path, "--weak").returncode, 3)

    def test_allow_silences_only_the_judged_rule(self) -> None:
        path = self.write("strong.md", STRONG)
        self.assertEqual(self.scan(path, "--allow", "S-PROC-01,S-STRUCT-02").returncode, 0)
        self.assertEqual(self.scan(path, "--allow", "S-PROC-01").returncode, 3)

    def test_json_output_is_machine_readable(self) -> None:
        proc = self.scan(self.write("strong.md", STRONG), "--json")
        self.assertEqual(proc.returncode, 3)
        payload = json.loads(proc.stdout)
        self.assertEqual(len(payload), 1)
        entry = payload[0]
        self.assertEqual(entry["lang"], "zh")
        self.assertEqual(entry["strong"], len([f for f in entry["findings"]
                                               if f["severity"] == "strong"]))
        self.assertTrue(entry["findings"])
        for finding in entry["findings"]:
            self.assertTrue(finding["rule"] and finding["hint"])
            self.assertIn(finding["severity"], ("strong", "weak"))

    def test_missing_file_is_a_usage_error_not_a_verdict(self) -> None:
        proc = self.scan(self.root / "nope.md")
        self.assertEqual(proc.returncode, 2)

    def test_scanner_is_read_only(self) -> None:
        path = self.write("numeric.md", NUMERIC)
        before = path.read_bytes()
        self.assertEqual(self.scan(path, "--json").returncode, 0)
        self.assertEqual(path.read_bytes(), before, "tell-scan must never rewrite the report")

    # ── the wiring ──────────────────────────────────────────────────────────

    def test_bundled_copy_matches_the_upstream_repo(self) -> None:
        """The scan runs on a copy that ships with this bundle; it must not drift."""
        if not UPSTREAM.exists():
            self.skipTest(f"upstream repo not checked out: {UPSTREAM}")
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
        self.assertEqual(digest(SCANNER), digest(UPSTREAM),
                         "scripts/tell-scan.py drifted from report-humanizer-zh; "
                         "re-copy it and re-run this suite")

    def test_skill_still_points_at_the_scanner_and_the_checklist(self) -> None:
        body = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("scripts/tell-scan.py", body)
        self.assertIn("references/prose-style-zh.md", body)
        self.assertIn("SCAN_EXIT", body)

    def test_checklist_names_every_rule_family(self) -> None:
        body = CHECKLIST.read_text(encoding="utf-8")
        for family in ("S-PROC-", "S-INFL-", "S-STRUCT-", "W-"):
            self.assertIn(family, body, f"checklist no longer explains {family}*")
        self.assertIn("tell-scan.py", body)
        self.assertIn("强命中必须处理", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
