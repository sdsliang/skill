#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
RENDERER_PATH = HERE.parents[2] / "skill/multi-clinical-result-comparison/scripts/render-facts.py"
SPEC = importlib.util.spec_from_file_location("render_facts", RENDERER_PATH)
render_facts = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(render_facts)


class RenderFactsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "evidence.txt"
        self.source.write_text(
            "Study alpha: primary endpoint was 8.34% at week 12.\n"
            "Study beta: response was 72% at week 24.\n",
            encoding="utf-8",
        )
        self.ledger = self.root / "ledger.json"
        self.draft = self.root / "draft.md"
        self.out = self.root / "report.md"
        self.audit = self.root / "audit.json"
        self.base = {
            "records": [
                {
                    "ref": "ref_1",
                    "title": "Study alpha",
                    "identity": "Alpha trial",
                    "design": "Randomized",
                    "arms": "Drug vs placebo",
                    "coverage": "Primary endpoint",
                },
                {
                    "ref": "ref_2",
                    "title": "Study beta",
                    "identity": "Beta trial",
                    "design": "Open label",
                    "arms": "Drug",
                    "coverage": "Response endpoint",
                },
            ],
            "facts": [
                {
                    "id": "F001",
                    "ref": "ref_1",
                    "study": "Study alpha",
                    "version": "v1",
                    "endpoint": "Primary endpoint",
                    "arm": "Drug",
                    "population": "Adults",
                    "timepoint": "Week 12",
                    "assessment": "ITT",
                    "kind": "efficacy",
                    "value": "8.34",
                    "unit": "%",
                    "statistics": "95% CI",
                    "source_file": "evidence.txt",
                    "quote": "Study alpha: primary endpoint was 8.34% at week 12.",
                },
                {
                    "id": "F002",
                    "ref": "ref_2",
                    "study": "Study beta",
                    "version": "v1",
                    "endpoint": "Response",
                    "arm": "Drug",
                    "population": "Adults",
                    "timepoint": "Week 24",
                    "assessment": "Investigator",
                    "kind": "efficacy",
                    "value": "72",
                    "unit": "%",
                    "statistics": "",
                    "source_file": "evidence.txt",
                    "quote": "Study beta: response was 72% at week 24.",
                },
            ],
        }
        self.write_ledger(self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def write_ledger(self, ledger):
        self.ledger.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    def run_render(self, draft="Results: [[fact:F001]]; detail: [[result:F001]]."):
        self.draft.write_text(draft, encoding="utf-8")
        return render_facts.render(self.ledger, self.draft, self.out, self.audit)

    def audit_data(self):
        return json.loads(self.audit.read_text(encoding="utf-8"))

    def test_cli_contract_writes_output_and_audit(self):
        self.draft.write_text("CLI [[result:F001]].", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(RENDERER_PATH),
                "--ledger",
                str(self.ledger),
                "--draft",
                str(self.draft),
                "--out",
                str(self.out),
                "--audit",
                str(self.audit),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Primary endpoint：8.34 %；95% CI{{ref_1}}", self.out.read_text(encoding="utf-8"))
        self.assertTrue(self.audit_data()["success"])

    def test_correct_reused_fact_is_consistent(self):
        self.assertTrue(self.run_render("Repeated [[fact:F001]] and [[fact:F001]]."))
        output = self.out.read_text(encoding="utf-8")
        self.assertEqual(output.count("8.34 %{{ref_1}}"), 2)
        self.assertNotIn("F001", output)
        self.assertNotIn("evidence.txt", output)

        self.assertTrue(self.run_render("Repeated [[fact:F001]] and [[fact:F001]]."))
        output = self.out.read_text(encoding="utf-8")
        self.assertEqual(output.count("8.34 %{{ref_1}}"), 2)
        self.assertNotIn("F001", output)
        self.assertNotIn("evidence.txt", output)

    def test_table_cell_deduplicates_same_ref_but_keeps_separate_cells(self):
        draft = "| Result | Source |\n|---|---|\n| [[fact:F001]] / [[fact:F001]] | [[fact:F001]] |"
        self.assertTrue(self.run_render(draft))
        output = self.out.read_text(encoding="utf-8")
        table_line = next(line for line in output.splitlines() if line.startswith("| 8.34 %"))
        self.assertEqual(table_line.count("{{ref_1}}"), 2)
        self.assertEqual(table_line.split("|")[1].count("{{ref_1}}"), 1)

    def test_unknown_token_blocks_and_audit_records_failure(self):
        self.out.write_text("old report", encoding="utf-8")
        self.assertFalse(self.run_render("Unknown [[fact:F999]]."))
        self.assertEqual(self.out.read_text(encoding="utf-8"), "old report")
        self.assertFalse(self.audit_data()["success"])
        self.assertIn("unknown fact token", self.audit_data()["errors"][0])

    def test_unknown_draft_citation_blocks(self):
        self.assertFalse(self.run_render("Citation {{ref_99}}."))
        self.assertIn("unknown citation", self.audit_data()["errors"][0])

    def test_cross_record_duplicate_id_blocks(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        duplicate = dict(ledger["facts"][1])
        duplicate["id"] = "F001"
        ledger["facts"].append(duplicate)
        self.write_ledger(ledger)
        self.assertFalse(self.run_render())
        self.assertIn("duplicate fact id", self.audit_data()["errors"][0])

    def test_value_absent_from_quote_blocks(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["facts"][0]["value"] = "6.9"
        self.write_ledger(ledger)
        self.assertFalse(self.run_render())
        self.assertIn("value is absent from quote", self.audit_data()["errors"][0])

    def test_unknown_source_and_ref_block(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["facts"][0]["source_file"] = "missing.txt"
        self.write_ledger(ledger)
        self.assertFalse(self.run_render())
        self.assertIn("does not exist", self.audit_data()["errors"][0])

        ledger["facts"][0]["source_file"] = "evidence.txt"
        ledger["facts"][0]["ref"] = "ref_99"
        self.write_ledger(ledger)
        self.assertFalse(self.run_render())
        self.assertIn("unknown", self.audit_data()["errors"][0])

    def test_appendix_is_consolidated_alignment_matrix(self):
        self.assertTrue(self.run_render("Summary [[result:F001]] and [[result:F002]]."))
        output = self.out.read_text(encoding="utf-8")
        self.assertIn("## Fact Ledger Appendix", output)
        self.assertIn("This appendix is a consolidated alignment matrix", output)
        self.assertIn("| Outcome domain | Trial / disclosure |", output)
        self.assertNotIn("### Study alpha", output)
        self.assertNotIn("### Study beta", output)
        self.assertIn("Primary endpoint", output)
        self.assertIn("Response", output)
        self.assertIn("8.34 %", output)
        self.assertIn("72 %", output)
        self.assertIn("{{ref_1}}", output)
        self.assertIn("{{ref_2}}", output)
        self.assertNotIn("F001", output)
        self.assertNotIn("F002", output)
        self.assertNotIn("evidence.txt", output)

    def test_unicode_minus_and_mutated_value_are_checked(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["facts"][0]["quote"] = "Study alpha: primary endpoint was −8.34% at week 12."
        self.source.write_text(
            "Study alpha: primary endpoint was −8.34% at week 12.\n"
            "Study beta: response was 72% at week 24.\n",
            encoding="utf-8",
        )
        self.write_ledger(ledger)
        self.assertTrue(self.run_render("Value [[fact:F001]]."))

        ledger["facts"][0]["value"] = "6.9"
        self.write_ledger(ledger)
        self.assertFalse(self.run_render("Value [[fact:F001]]."))
        self.assertIn("value is absent from quote", self.audit_data()["errors"][0])

    def test_quote_source_mismatch_rejects(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["facts"][0]["quote"] = "A quote copied from another source: 8.34%."
        self.write_ledger(ledger)
        self.assertFalse(self.run_render())
        self.assertIn("quote is not an exact source substring", self.audit_data()["errors"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
