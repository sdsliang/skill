#!/usr/bin/env python3
"""Standalone subprocess tests for check_report.py's chart duplication rules."""

from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
