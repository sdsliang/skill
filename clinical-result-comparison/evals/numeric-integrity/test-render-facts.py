#!/usr/bin/env python3
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


# Loading the renderer from the Skill tree must not leave a `__pycache__` behind: the
# deployment check compares the live Skill directory against the published bundle, so a
# local `.pyc` makes an otherwise clean run report a support-file manifest mismatch.
sys.dont_write_bytecode = True

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
                    "trial": "Alpha trial",
                    "identity": "Alpha trial",
                    "design": "Randomized",
                    "arms": "Drug vs placebo",
                    "coverage": "Primary endpoint",
                    "conclusion": "Alpha trial met its primary endpoint.",
                },
                {
                    "ref": "ref_2",
                    "title": "Study beta",
                    "trial": "Beta trial",
                    "identity": "Beta trial",
                    "design": "Open label",
                    "arms": "Drug",
                    "coverage": "Response endpoint",
                    "conclusion": "Beta trial reported a high response rate.",
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

    def test_appendix_is_trial_column_alignment_matrix(self):
        self.assertTrue(self.run_render("Summary [[result:F001]] and [[result:F002]]."))
        output = self.out.read_text(encoding="utf-8")
        self.assertIn("## 附录：证据对齐矩阵（数值事实账本）", output)
        self.assertIn("列为试验", output)
        self.assertIn("| 维度 | **Study alpha**<br>1 条披露 | **Study beta**<br>1 条披露 |", output)
        self.assertIn("| **试验设计** |", output)
        self.assertIn("| **试验结论** |", output)
        self.assertIn("| **有效性** |", output)
        self.assertIn("| 试验身份 |", output)
        self.assertIn("| 披露级结论 |", output)
        self.assertIn("Alpha trial met its primary endpoint.", output)
        self.assertIn("| Primary endpoint |", output)
        self.assertIn("| Response |", output)
        self.assertIn("8.34 %", output)
        self.assertIn("72 %", output)
        self.assertIn("{{ref_1}}", output)
        self.assertIn("{{ref_2}}", output)
        self.assertNotIn("Outcome domain", output)
        self.assertNotIn("F001", output)
        # Long prose rows are gone from the appendix: the body and the 试验背景 table carry them.
        for dropped in ("披露标题", "设计与方案", "试验组与对照", "人群与证据覆盖"):
            self.assertNotIn(f"| {dropped} |", output)
        self.assertNotIn("Randomized", output)
        self.assertNotIn("Drug vs placebo", output)
        self.assertEqual(self.audit_data()["appendix_layout"], "trial-columns")

    def test_appendix_intro_carries_no_template_placeholder(self):
        """The runner fails any report containing a literal `{{ref_n}}`-style
        placeholder that is not a real `{{ref_<digits>}}` marker. The appendix
        intro is emitted verbatim into the delivered report, so it must
        describe the cell format without ever spelling the placeholder out."""
        self.assertTrue(self.run_render("Summary [[result:F001]]."))
        output = self.out.read_text(encoding="utf-8")
        leftovers = sorted({m for m in re.findall(r"\{\{[^}]*\}\}", output)
                            if not re.fullmatch(r"\{\{ref_\d+\}\}", m)})
        self.assertEqual(leftovers, [], f"placeholder leaked into the report: {leftovers}")
        self.assertNotIn("F002", output)
        self.assertNotIn("evidence.txt", output)
        self.assertEqual(self.audit_data()["appendix_trials"], 2)
        self.assertGreater(self.audit_data()["appendix_cells_filled"], 0)

    def test_ledger_without_prose_record_fields_renders(self):
        """`title` / `design` / `arms` / `coverage` are no longer part of the appendix, so a lean
        ledger of ref / trial / identity / conclusion must render without them."""
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        for record in ledger["records"]:
            for field in ("title", "design", "arms", "coverage"):
                del record[field]
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        self.assertIn("| 试验身份 | Alpha trial{{ref_1}} | Beta trial{{ref_2}} |", output)
        self.assertIn("Alpha trial met its primary endpoint.", output)

    def test_appendix_drops_record_prose_rows(self):
        """A legacy ledger's long prose must not be echoed into the appendix: it duplicates the body
        and the 试验背景 table, and long text is bound by `{{ref_n}}` there."""
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["records"][0]["design"] = "多中心随机双盲安慰剂对照 III 期研究，按 PD-L1 表达分层"
        ledger["records"][0]["arms"] = "试验组接受 X 联合化疗，对照组接受安慰剂联合化疗"
        ledger["records"][0]["coverage"] = "覆盖 532 例随机化人群的主要终点与关键次要终点"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        for prose in ("多中心随机双盲", "接受 X 联合化疗", "覆盖 532 例随机化人群"):
            self.assertNotIn(prose, output)
        self.assertNotIn("| 设计与方案 |", output)

    def test_appendix_headers_follow_one_uniform_shape(self):
        """Column headers must not drift between trial name / registry id / free prose: every header
        is `**名称**` plus a `<br>` detail line of registry id and disclosure count."""
        self.assertTrue(self.run_render("Summary [[result:F001]] and [[result:F002]]."))
        header = next(
            line for line in self.out.read_text(encoding="utf-8").splitlines() if line.startswith("| 维度 |")
        )
        cells = [cell.strip() for cell in header.strip().strip("|").split("|")][1:]
        self.assertEqual(len(cells), 2)
        for cell in cells:
            self.assertRegex(cell, r"^\*\*[^*|<]+\*\*<br>(?:[^|]* · )?\d+ 条披露$")

    def test_appendix_disclosure_headers_use_ref_and_short_version(self):
        """The one-trial layout names each column `ref_n` plus a short version tag, so a long
        version string never bloats the header."""
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        for index, record in enumerate(ledger["records"], start=1):
            record["trial"] = "NCT05840016"
        ledger["facts"][0]["version"] = "预设中期 OS 分析·数据截止 2026-02-27"
        ledger["facts"][1]["version"] = "最终 PFS 分析·数据截止 2025-11-30"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        header = next(
            line for line in self.out.read_text(encoding="utf-8").splitlines() if line.startswith("| 维度 |")
        )
        self.assertIn("**ref_1**<br>预设中期 OS 分析", header)
        self.assertIn("**ref_2**<br>最终 PFS 分析", header)
        self.assertNotIn("数据截止", header)
        self.assertEqual(self.audit_data()["appendix_layout"], "disclosure-columns")

    def test_missing_record_conclusion_blocks(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        del ledger["records"][0]["conclusion"]
        self.write_ledger(ledger)
        self.assertFalse(self.run_render())
        self.assertIn("missing fields: conclusion", self.audit_data()["errors"][0])

    def test_appendix_single_trial_becomes_one_column_per_disclosure(self):
        """One trial whose disclosures used to be stacked inside one cell gets one column per
        disclosure: every evidence item keeps a line of its own instead of an HTML `<br>` pile."""
        ledger = {
            "records": [
                {
                    "ref": "ref_1",
                    "title": "Alpha primary",
                    "trial": "NCT05840016",
                    "identity": "Alpha；2024 年会",
                    "design": "Randomized",
                    "arms": "Drug vs placebo",
                    "coverage": "Primary analysis",
                    "conclusion": "Primary analysis met the endpoint.",
                },
                {
                    "ref": "ref_2",
                    "title": "Alpha update",
                    "trial": "NCT05840016",
                    "identity": "Alpha 2025 更新",
                    "design": "Randomized",
                    "arms": "Drug vs placebo",
                    "coverage": "Updated analysis",
                    "conclusion": "Updated analysis confirmed the benefit.",
                },
            ],
            "facts": [
                {
                    "id": "F001",
                    "ref": "ref_1",
                    "study": "Alpha",
                    "version": "2024 年会",
                    "endpoint": "OS",
                    "arm": "Drug",
                    "population": "Adults",
                    "timepoint": "Week 12",
                    "assessment": "ITT",
                    "kind": "有效性",
                    "value": "8.34",
                    "unit": "%",
                    "statistics": "",
                    "source_file": "evidence.txt",
                    "quote": "Study alpha: primary endpoint was 8.34% at week 12.",
                },
                {
                    "id": "F002",
                    "ref": "ref_2",
                    "study": "Alpha",
                    "version": "2025 年会更新",
                    "endpoint": "OS",
                    "arm": "Drug",
                    "population": "Adults",
                    "timepoint": "Week 24",
                    "assessment": "ITT",
                    "kind": "有效性",
                    "value": "72",
                    "unit": "%",
                    "statistics": "",
                    "source_file": "evidence.txt",
                    "quote": "Study beta: response was 72% at week 24.",
                },
            ],
        }
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        header = next(line for line in output.splitlines() if line.startswith("| 维度 |"))
        self.assertEqual(header.count("|"), 4)
        self.assertIn("**ref_1**<br>2024 年会", header)
        self.assertIn("**ref_2**<br>2025 年会更新", header)
        os_row = next(line for line in output.splitlines() if line.startswith("| OS"))
        self.assertIn("8.34 %{{ref_1}}", os_row)
        self.assertIn("72 %{{ref_2}}", os_row)
        # `arm` / `assessment` / `population` hold for the whole row: hoisted into the label,
        # while the differing timepoint stays in each cell.
        self.assertIn("| OS · Drug；ITT；Adults |", os_row)
        self.assertIn("Week 12：8.34 %", os_row)
        self.assertIn("Week 24：72 %", os_row)
        # Each disclosure owns its cell: no disclosure stacking inside one cell anymore.
        self.assertNotIn("<br>", os_row)
        self.assertEqual(os_row.count(" | "), 2)
        audit = self.audit_data()
        self.assertEqual(audit["appendix_trials"], 1)
        self.assertEqual(audit["appendix_columns"], 2)
        self.assertEqual(audit["appendix_layout"], "disclosure-columns")

    def test_appendix_merges_by_registry_id_not_label(self):
        self.source.write_text(
            self.source.read_text(encoding="utf-8") + "Study gamma: response was 41% at week 36.\n",
            encoding="utf-8",
        )

        def record(ref, title, trial, identity, conclusion):
            return {
                "ref": ref,
                "title": title,
                "trial": trial,
                "identity": identity,
                "design": "Randomized",
                "arms": "Drug vs placebo",
                "coverage": "Primary analysis",
                "conclusion": conclusion,
            }

        def fact(fact_id, ref, endpoint, value, quote):
            return {
                "id": fact_id,
                "ref": ref,
                "study": "研究甲",
                "version": "v1",
                "endpoint": endpoint,
                "arm": "Drug",
                "population": "Adults",
                "timepoint": "Week 12",
                "assessment": "ITT",
                "kind": "有效性",
                "value": value,
                "unit": "%",
                "statistics": "",
                "source_file": "evidence.txt",
                "quote": quote,
            }

        ledger = {
            "records": [
                record("ref_1", "Alpha primary", "NCT05840016", "研究甲；2024 年会", "Met the endpoint."),
                record("ref_2", "Other trial", "NCT09999999", "研究甲；2025 年会", "Missed the endpoint."),
                record("ref_3", "Alpha update", "nct05840016", "研究甲更新；2025 更新", "Confirmed the benefit."),
            ],
            "facts": [
                fact("F001", "ref_1", "OS", "8.34", "Study alpha: primary endpoint was 8.34% at week 12."),
                fact("F002", "ref_2", "OS", "72", "Study beta: response was 72% at week 24."),
                fact("F003", "ref_3", "OS", "41", "Study gamma: response was 41% at week 36."),
            ],
        }
        self.write_ledger(ledger)
        self.assertTrue(self.run_render("Results: [[fact:F001]], [[fact:F002]], [[fact:F003]]."))
        output = self.out.read_text(encoding="utf-8")
        header = next(line for line in output.splitlines() if line.startswith("| 维度 |"))
        # Same trial key merges even when the display name and identity text differ.
        self.assertIn("**研究甲（NCT05840016）**<br>NCT05840016 · 2 条披露", header)
        # The same label on two different trial keys stays two columns and is disambiguated.
        self.assertIn("**研究甲（NCT09999999）**<br>NCT09999999 · 1 条披露", header)
        self.assertEqual(header.count("|"), 4)
        os_row = next(line for line in output.splitlines() if line.startswith("| OS"))
        self.assertIn("| OS · Drug；Week 12；ITT；Adults |", os_row)
        for marker in ("8.34 %{{ref_1}}", "41 %{{ref_3}}", "72 %{{ref_2}}"):
            self.assertIn(marker, os_row)
        self.assertEqual(self.audit_data()["appendix_trials"], 2)

    def test_appendix_merge_fallbacks_for_legacy_ledgers(self):
        """v0.15 ledgers carry no `trial` key: registry id, then the study label, still merge them."""
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        for record in ledger["records"]:
            del record["trial"]
        ledger["records"][0]["identity"] = "Alpha；NCT05840016"
        ledger["records"][1]["identity"] = "Alpha update；NCT05840016"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        header = next(line for line in self.out.read_text(encoding="utf-8").splitlines() if line.startswith("| 维度 |"))
        # Both records carry the same registry id, so they merge into one trial; that trial's two
        # disclosures then get one column each.
        self.assertEqual(header.count("|"), 4)
        self.assertEqual(self.audit_data()["appendix_trials"], 1)
        self.assertEqual(self.audit_data()["appendix_columns"], 2)
        self.assertEqual(self.audit_data()["records_without_trial_key"], 2)

        ledger = json.loads(json.dumps(self.base, ensure_ascii=False))
        for record in ledger["records"]:
            del record["trial"]
        for fact in ledger["facts"]:
            fact["study"] = "Study alpha"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        header = next(line for line in output.splitlines() if line.startswith("| 维度 |"))
        self.assertEqual(header.count("|"), 4)
        self.assertIn("**ref_1**<br>v1", header)
        self.assertEqual(self.audit_data()["appendix_trials"], 1)
        self.assertEqual(self.audit_data()["appendix_layout"], "disclosure-columns")

    def test_appendix_aligns_endpoint_variants_on_one_row(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["facts"][0]["endpoint"] = "16 个月 ORR"
        ledger["facts"][1]["endpoint"] = "ORR（%）"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        # `Drug` / `Adults` hold for the whole row, so they move into the row label; the differing
        # `16 个月` qualifier and each value stay in their own cell.
        rows = [line for line in output.splitlines() if line.startswith("| ORR")]
        self.assertEqual(len(rows), 1)
        self.assertIn("| ORR · Drug；Adults |", rows[0])
        self.assertIn("16 个月：8.34 %", rows[0])
        self.assertIn("72 %{{ref_2}}", rows[0])
        self.assertNotIn("| 16 个月 ORR |", output)
        self.assertNotIn("| ORR（%） |", output)

    def test_appendix_aligns_latin_abbreviation_qualifier_on_one_row(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["facts"][0]["endpoint"] = "中位总生存期（OS）"
        ledger["facts"][1]["endpoint"] = "中位总生存期"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        rows = [line for line in output.splitlines() if line.startswith("| 中位总生存期")]
        self.assertEqual(len(rows), 1)
        self.assertIn("OS：8.34 %", rows[0])
        self.assertIn("72 %{{ref_2}}", rows[0])
        self.assertFalse(
            [line for line in output.splitlines() if line.startswith("| 中位总生存期（OS）")],
            "the qualifier must move into the cell, not create a near-duplicate row",
        )

    def test_appendix_ignores_placeholder_study_labels(self):
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        for fact in ledger["facts"]:
            fact["study"] = "see records"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        header = next(line for line in output.splitlines() if line.startswith("| 维度 |"))
        self.assertNotIn("see records", header)
        self.assertIn("Alpha trial", header)
        self.assertIn("Beta trial", header)

    def test_entity_inline_references_are_stripped_from_ledger_text(self):
        """v0.16 removed entity inline references: an old ledger's anchors degrade to plain names."""
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["records"][0]["identity"] = "[Alpha trial](entity:trial:NCT05840016)；2024 年会"
        ledger["records"][0]["arms"] = "[Drug](entity:drug:12483) vs [placebo](entity:drug:2237)"
        ledger["facts"][0]["arm"] = "[Drug](entity:drug:12483)"
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        self.assertNotIn("entity:", output)
        # Only the trial display name (first identity segment) is printed: the long identity tail
        # and the `arms` prose row are no longer part of the appendix.
        self.assertIn("Alpha trial{{ref_1}}", output)
        self.assertNotIn("2024 年会", output)
        self.assertNotIn("Drug vs placebo", output)
        self.assertIn("Drug·Week 12", output)

    def test_entity_syntax_in_draft_blocks_delivery(self):
        self.assertFalse(self.run_render("Drug: [Drug](entity:drug:12483) [[fact:F001]]."))
        self.assertIn("entity inline references", self.audit_data()["errors"][0])
        self.assertFalse(self.out.exists())

    def test_appendix_keeps_arms_and_glued_names_inside_cells(self):
        self.source.write_text(
            self.source.read_text(encoding="utf-8") + "Study gamma: response was 41% at week 36.\n",
            encoding="utf-8",
        )
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        ledger["facts"][0]["endpoint"] = "基线 Lp(a)（中位）"
        ledger["facts"].append(dict(ledger["facts"][0], id="F003", arm="Placebo"))
        ledger["facts"].append(
            {
                "id": "F004",
                "ref": "ref_1",
                "study": "Study alpha",
                "version": "v1",
                "endpoint": "基线 OxPL（中位）",
                "arm": "Drug",
                "population": "Adults",
                "timepoint": "Week 12",
                "assessment": "ITT",
                "kind": "有效性",
                "value": "41",
                "unit": "%",
                "statistics": "",
                "source_file": "evidence.txt",
                "quote": "Study gamma: response was 41% at week 36.",
            }
        )
        self.write_ledger(ledger)
        self.assertTrue(self.run_render())
        output = self.out.read_text(encoding="utf-8")
        row = next(line for line in output.splitlines() if line.startswith("| 基线 Lp(a)"))
        # `Week 12` / `ITT` / `Adults` are shared by both arms of the row, so the label carries them.
        self.assertIn("| 基线 Lp(a) · Week 12；ITT；Adults |", row)
        self.assertIn("Drug·中位：8.34 %", row)
        self.assertIn("Placebo·中位：8.34 %", row)
        self.assertIn("<br>", row)
        self.assertEqual(row.count("{{ref_1}}"), 1)
        # A Latin token followed by a Chinese qualifier still separates: the name stays, the qualifier moves in.
        oxpl_row = next(line for line in output.splitlines() if line.startswith("| 基线 OxPL"))
        self.assertIn("中位：41 %", oxpl_row)
        self.assertFalse([line for line in output.splitlines() if line.startswith("| 基线 OxPL（中位） |")])
        headers = [line for line in output.splitlines() if line.startswith("| 维度 |")]
        self.assertEqual(len(headers), 1)

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
