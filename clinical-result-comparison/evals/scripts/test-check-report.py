#!/usr/bin/env python3
"""Standalone subprocess tests for check_report.py's chart duplication rules."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CHECKER = REPO / "skill" / "multi-clinical-result-comparison" / "scripts" / "check_report.py"


class CheckReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="check-report-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.report = self.root / "report.md"
        self.citations = self.root / "citations.json"
        self.charts = self.root / "visualizations"
        self.charts.mkdir()
        self.chart_path = self.charts / "endpoint-bar-1.json"
        self.citations.write_text(json.dumps({
            "ref_1": {"title": "A realistic trial report", "link": "https://example.test/a",
                      "paper_release_time_str": "2024-01-02"}
        }), encoding="utf-8")

    def chart(self, option: dict | None = None, name: str = "endpoint-bar-1.json") -> None:
        if option is None:
            option = {"type": "bar", "subTitle": "独立描述", "describe": "终点变化",
                      "data": [{"label": "A", "value": -13.9, "description": "治疗结果{{ref_1}}"},
                                {"label": "B", "value": -70.5, "description": "治疗结果{{ref_1}}"}]}
        path = self.charts / name
        path.write_text(json.dumps({"id": "chart-visualization-json", "iframe_template": "https://example.test/i",
                                    "option": option}, ensure_ascii=False), encoding="utf-8")

    def report_text(self, body: str, appendix: str = "| 事实 | 值 |\n| --- | --- |\n| 样本量 | 12 例{{ref_1}} |\n") -> None:
        self.report.write_text(body + "\n\n## 附录：证据对齐矩阵\n\n" + appendix, encoding="utf-8")

    def run_check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(CHECKER), "--report", str(self.report),
                               "--citations", str(self.citations), "--charts-dir", str(self.charts),
                               "--vis-prefix", str(self.charts) + "/", "--json"],
                              capture_output=True, text=True, check=False)

    def base_body(self, section: str = "## 结果\n\n结果如表所示{{ref_1}}。\n") -> str:
        return section + f'\n::visualization[endpoint]{{path="{self.chart_path}"}}\n'

    def test_clean_report_passes_and_parses_real_content(self):
        self.chart()
        self.report_text(self.base_body(), "| 事实 | 值 |\n| --- | --- |\n| 样本量 | 12 例{{ref_1}} |\n")
        self.assertTrue(self.report.read_text(encoding="utf-8").strip())
        rows = [line for line in self.report.read_text(encoding="utf-8").splitlines() if line.startswith("|") and "---" not in line]
        self.assertTrue(rows, "fixture must contain a real parsed table row")
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"findings": []', proc.stdout)
        self.assertIn('"checks"', proc.stdout)

    def test_chart_description_repeating_value_fails(self):
        self.chart({"type": "bar", "subTitle": "独立", "describe": "终点 -13.9%", "data": [
            {"label": "A", "value": -13.9, "description": "结果{{ref_1}}"}]})
        self.report_text(self.base_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("option.describe restates plotted value -13.9", proc.stdout)
        self.assertIn("remove the value from the chart text", proc.stdout)

    def test_dose_numbers_are_not_flagged(self):
        self.chart({"type": "bar", "subTitle": "每 12 周，225 mg", "describe": "给药方案",
                    "data": [{"label": "A", "value": 12.0, "description": "225 mg 每 12 周{{ref_1}}"}]})
        self.report_text(self.base_body())
        self.assertEqual(self.run_check().returncode, 0)

    def test_two_table_values_in_chart_section_fail(self):
        self.chart()
        table = "| 终点 | 结果 |\n| --- | --- |\n| A | -13.9%{{ref_1}} |\n| B | -70.5%{{ref_1}} |\n"
        self.report_text(self.base_body() + table)
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("section table repeats plotted values", proc.stdout)
        self.assertIn("move the chart to a section without the table", proc.stdout)

    def test_appendix_values_do_not_fail(self):
        self.chart()
        appendix = "| 终点 | 结果 |\n| --- | --- |\n| A | -13.9%{{ref_1}} |\n| B | -70.5%{{ref_1}} |\n"
        self.report_text("## 结果\n\n结果{{ref_1}}\n" + f'\n::visualization[endpoint]{{path="{self.chart_path}"}}\n', appendix)
        self.assertEqual(self.run_check().returncode, 0)

    def test_chart_before_the_first_heading_cannot_reach_the_appendix(self):
        """A chart placed above every heading has no enclosing section; the appendix table
        below it carries the same values and must not be mistaken for a repeat."""
        self.chart()
        appendix = "| 终点 | 结果 |\n| --- | --- |\n| A | -13.9%{{ref_1}} |\n| B | -70.5%{{ref_1}} |\n"
        self.report_text(f'结果{{{{ref_1}}}}\n\n::visualization[endpoint]{{path="{self.chart_path}"}}\n', appendix)
        self.assertEqual(self.run_check().returncode, 0)

    def test_single_coincidental_table_value_is_allowed(self):
        self.chart()
        table = "| 终点 | 结果 |\n| --- | --- |\n| A | -13.9%{{ref_1}} |\n"
        self.report_text(self.base_body(), table)
        self.assertEqual(self.run_check().returncode, 0)

    def test_timeline_has_no_numeric_duplication_rule(self):
        self.chart({"type": "timeline", "subTitle": "数值 -13.9", "describe": "数值 -70.5",
                    "data": [{"time": "2024-01", "description": "-13.9 -70.5{{ref_1}}"}]}, "evidence-timeline.json")
        self.chart_path = self.charts / "evidence-timeline.json"
        self.report_text(self.base_body().replace("endpoint-bar-1", "evidence-timeline"))
        self.assertEqual(self.run_check().returncode, 0)

    def test_integer_without_decimal_point_is_not_flagged(self):
        self.chart({"type": "bar", "subTitle": "共 12 例", "describe": "整数描述",
                    "data": [{"label": "A", "value": 12, "description": "结果{{ref_1}}"}]})
        self.report_text(self.base_body())
        self.assertEqual(self.run_check().returncode, 0)

    def test_hand_written_appendix_spec_paragraph_fails(self):
        """Complaint 1: the appendix must open with the renderer's one-line legend, never with a
        specification paragraph describing the columns."""
        self.chart()
        spec = ("按「试验设计 → 试验结论 → 有效性 → 安全性 → PK/PD → PRO」分段排列。**列为试验**：同一试验的多条披露合并为一列，"
                "列头为该试验的显示名 + 注册号与披露条数；行为维度与终点父级，单元格只留差异部分。")
        self.report_text(self.base_body(), spec + "\n\n| 事实 | 值 |\n| --- | --- |\n| 样本量 | 12 例{{ref_1}} |\n")
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("prose block instead of the", proc.stdout)
        self.assertIn("write no appendix specification paragraph", proc.stdout)

    def test_single_line_legend_after_the_title_passes(self):
        self.chart()
        self.report_text(self.base_body(),
                         "表中「—」表示该披露在该终点上未报告该数值。\n\n| 事实 | 值 |\n| --- | --- |\n| 样本量 | 12 例{{ref_1}} |\n")
        self.assertEqual(self.run_check().returncode, 0)

    def test_two_appendix_headings_fail(self):
        self.chart()
        body = self.base_body() + "\n## 附录：证据对齐矩阵\n\n手写的附录说明。\n"
        self.report_text(body)
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("appendix title appears 2 times", proc.stdout)

    # ---- report voice: findings only, never the report's own method -------------------

    def test_method_label_bullets_fail(self):
        """Complaint 5: `**分析模式：** 跨试验、非头对头` is the model describing its own method."""
        self.chart()
        self.report_text("## 一、比较范围\n\n- **分析模式：** 跨试验、非头对头、按指标域对齐\n" + self.base_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("labels its own method", proc.stdout)
        self.assertIn("分析模式", proc.stdout)

    def test_alignment_level_column_fails(self):
        self.chart()
        table = ("| 终点（定义） | 试验 A | 时间点 | 对齐等级 | 解读边界 |\n|---|---|---|---|---|\n"
                 "| Lp(a) 变化 | -13.9%{{ref_1}} | 16 周 | 部分对齐 | 时点不同 |\n")
        self.report_text(self.base_body() + table)
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("is the report classifying its own work", proc.stdout)

    def test_chart_decidability_wording_fails(self):
        self.chart()
        self.report_text("- **可比性结论：** 只能有限并列\n" + self.base_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("method/class narration", proc.stdout)
        self.assertIn("只能有限并列", proc.stdout)

    def test_self_audit_tail_fails(self):
        self.chart()
        self.report_text("## 一、范围\n\n核对完成，无未复核记录。\n" + self.base_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("self-audit tail", proc.stdout)

    def test_internal_field_vocabulary_fails(self):
        self.chart()
        self.report_text("> **原文核对：** 2/2 条已复核（2 条均为 src=1，库内正文即原文摘要）\n" + self.base_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3)
        self.assertIn("internal field or runtime vocabulary", proc.stdout)

    def test_material_coverage_line_passes(self):
        """The two kept slots — the coverage line and a comparability caveat — stay writable."""
        self.chart()
        self.report_text(
            "> **证据范围：** 只整合所选结果材料。**原文核对：** 2/2 条已复核（PMID 23841780；登记平台结构化结果；摘要级，未收录 PMC）。\n"
            "\n核对路径与来源类如上；两条记录均无可用的全文正文。\n" + self.base_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"findings": []', proc.stdout)

    def test_interpretation_boundary_prose_passes(self):
        self.chart()
        self.report_text("按终点逐行对齐；最后一列写解读边界：时点 16 周与 36 周不同，人群与分析集也不同。\n"
                         + self.base_body())
        self.assertEqual(self.run_check().returncode, 0)

    def test_self_reference_is_a_warning_not_a_failure(self):
        self.chart()
        self.report_text("## 一、范围\n\n本报告不把两组拼成头对头比较。\n" + self.base_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"findings": []', proc.stdout)
        self.assertIn("refers to itself", proc.stdout)

    def _timeline_body(self) -> str:
        return self.base_body().replace("endpoint-bar-1.json", "evidence-timeline.json")

    def _timeline_chart(self, **extra) -> None:
        row = {"time": "2022-11", "label": "首次披露", "content": "主要分析",
               "description": "设计变更，成熟度尚低{{ref_1}}"}
        row.update(extra.pop("row", {}))
        option = {"type": "timeline", "subTitle": "同一试验披露演进，不等同于头对头比较",
                  "describe": "证据状态按时间顺序排列", "data": [row]}
        option.update(extra)
        self.chart(option, name="evidence-timeline.json")

    def test_timeline_node_weight_fails(self):
        self._timeline_chart(row={"weight": 2})
        self.report_text(self._timeline_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("`weight` is dead", proc.stdout)
        self.assertIn("renders every node the same", proc.stdout)

    def test_timeline_weight_legend_fails(self):
        self._timeline_chart(weightLegend={"show": True, "label": "证据成熟度"})
        self.report_text(self._timeline_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("`weightLegend` is no longer rendered", proc.stdout)

    def test_timeline_legend_and_node_shape_fail(self):
        self._timeline_chart(legend=[{"key": "milestone", "label": "研究里程碑", "shape": "empty-circle"}])
        self.report_text(self._timeline_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("renders no legend", proc.stdout)
        self._timeline_chart(row={"shape": "empty-circle"})
        self.report_text(self._timeline_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("node `shape` is dead", proc.stdout)

    def test_report_text_must_not_explain_a_chart_cue_that_does_not_exist(self):
        """Complaint: a reader cannot decode dots the renderer draws identically (R51)."""
        self._timeline_chart()
        self.report_text(self._timeline_body() + "\n节点大小对应证据成熟度。\n")
        proc = self.run_check()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("chart cue that does not exist", proc.stdout)

    def test_timeline_without_a_weight_encoding_stays_clean(self):
        self._timeline_chart()
        self.report_text(self._timeline_body())
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"findings": []', proc.stdout)


class ReferenceSetVsGateTests(unittest.TestCase):
    """The packaged references must not prescribe anything this gate rejects (R68).

    r67-14 spent 2.5k chars arbitrating a contradiction we shipped ourselves:
    ``references/cross-trial-comparison.md`` asked for "a dedicated last column for
    alignment level", while the host prompt - and META_COLUMN_RE above - fail a
    ``对齐等级`` column.  These tests pin both sides to the same vocabulary.
    """

    SKILL = REPO / "skill" / "multi-clinical-result-comparison"

    def texts(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for path in sorted((self.SKILL / "references").glob("*.md")):
            out[str(path.relative_to(self.SKILL))] = path.read_text(encoding="utf-8")
        for name in ("SKILL.md", "scripts/check_report.py"):
            out[name] = (self.SKILL / name).read_text(encoding="utf-8")
        return out

    def test_no_reference_prescribes_a_gate_rejected_column_or_label(self):
        banned = {
            "alignment-level column": (r"column for alignment level",
                                       r"^\s*[-*]\s*alignment level\s*;",
                                       r"^\s*[-*]\s*interpretation boundary\."),
            "chart-decidability label": (r"no-chart reason",),
        }
        for name, text in self.texts().items():
            for what, patterns in banned.items():
                for pattern in patterns:
                    hit = re.search(pattern, text, re.MULTILINE)
                    if not hit:
                        continue
                    # The prohibition lists name the labels on purpose (they sit right next to
                    # `check_report.py`); an instruction to *build* one is the defect.
                    para = text[: hit.start()].rsplit("\n\n", 1)[-1] + hit.group()
                    if "check_report" not in para:
                        self.fail(f"{name} prescribes a {what}: {hit.group()!r}")

    def test_cross_trial_template_names_the_printable_boundary_column(self):
        text = (self.SKILL / "references" / "cross-trial-comparison.md").read_text(encoding="utf-8")
        self.assertIn("解读边界", text)
        self.assertIn("never printed", text)
        self.assertRegex(text, r"check_report\.py` rejects it")


if __name__ == "__main__":
    unittest.main(verbosity=2)
