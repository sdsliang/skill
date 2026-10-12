#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end tests for the six packaged scripts under skill/multi-clinical-result-comparison/scripts/.

Run directly (the file name contains a hyphen, so `unittest discover` cannot import it):

    python3 evals/scripts/test-skill-scripts.py           # all tests
    python3 evals/scripts/test-skill-scripts.py -v        # verbose
    python3 evals/scripts/test-skill-scripts.py Ledger    # one class

Each test drives the real script as a subprocess inside a throwaway sandbox, so the contract
being asserted is the CLI contract the model actually uses: exit codes, files written, and the
bytes inside them.  Assertions deliberately check *content*, never just the presence of a file:
a test that a runner could satisfy by emitting an empty artifact is not a test (see the
"anti-empty-artifact" cases below).  No test touches /workspace, the network, or ToolSmith.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
SKILL = REPO / "skill" / "multi-clinical-result-comparison"
SCRIPTS = SKILL / "scripts"
RENDER_FACTS = SCRIPTS / "render-facts.py"

ESID_A = "24_1_30561610"
ESID_B = "24_1_36342163"
ABSTRACT_A = ("129 patients were randomized to evolocumab 420 mg monthly or placebo. "
              "The MDS TBR change with placebo was -5.3% at week 16.")
SUMMARY_B = "281 patients received olpasiran; 225 mg every 12 weeks reduced Lp(a) by 70.5%."


def _record(esid: str, title: str, link: str, release: str, abstract: str = "", summary: str = "") -> dict:
    return {
        "clinical_result_extra_esid": esid,
        "clinical_result_paper_title": title,
        "clinical_result_full_article_link": link,
        "clinical_result_paper_release_time": release,
        "clinical_result_journal": "NEJM",
        "clinical_result_doi": "10.1056/NEJMoa000000",
        "clinical_result_pm_id": esid.split("_")[-1],
        "clinical_result_trial_abbreviation": ["OCEAN(a)-DOSE"],
        "clinical_result_indication_name": ["ASCVD"],
        "clinical_result_primary_endpoint_cn": ["Lp(a) 变化"],
        "clinical_result_abstract_text": abstract,
        "clinical_result_summary": summary,
        "clinical_result_arms": [{"arm_label": "olpasiran 225 mg Q12W", "arm_count": "140"}],
        "clinical_result_study_results": [{"arm_id": "a1", "endpoint_label": "36-week",
                                            "result": "-70.5", "result_unit": "%"}],
    }


RECORDS = [
    _record(ESID_A, "Evolocumab in HoFH", "https://pubmed.ncbi.nlm.nih.gov/30561610",
            "2018-11-20 06:00:00", abstract=ABSTRACT_A),
    _record(ESID_B, "Olpasiran in ASCVD", "https://pubmed.ncbi.nlm.nih.gov/36342163",
            "2022-11-08 06:00:00", summary=SUMMARY_B),
]


class Sandbox(unittest.TestCase):
    """Shared fixture: a throwaway workspace with a fake tool_results pull and chart skill."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="skill-scripts-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for name in ("work/sources", "output", "visualizations", "chartskill/templates"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        pull = self.root / "tool_results" / "pharmcube-query-clinical-result-with-params"
        pull.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(row, ensure_ascii=False) for row in RECORDS]
        lines += [lines[0], "{not json", ""]                      # duplicate row + junk + blank
        (pull / "call_1.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        for kind in ("bar", "line", "timeline"):
            (self.root / "chartskill" / "templates" / f"{kind}.json").write_text(
                json.dumps({"id": "chart-visualization-json",
                            "iframe_template": "https://vcdn.example/iframe-template.json",
                            "option": {"type": kind}}, ensure_ascii=False), encoding="utf-8")
        self.refs = self.root / "work" / "refs.json"
        self.sources = self.root / "work" / "sources"
        self.ledger = self.root / "work" / "ledger.json"

    # -- helpers -------------------------------------------------------------------------
    def sh(self, script: str, *args, expect: int | None = 0) -> subprocess.CompletedProcess:
        proc = subprocess.run([sys.executable, "-B", str(SCRIPTS / script), *[str(a) for a in args]],
                              cwd=str(self.root), capture_output=True, text=True)
        if expect is not None:
            self.assertEqual(proc.returncode, expect,
                             f"{script} exit {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        return proc

    def prep(self, esids: str = f"{ESID_A},{ESID_B}", *extra, expect: int | None = 0):
        return self.sh("prep_sources.py", "--result", self.root / "tool_results/pharmcube-query-clinical-result-with-params/call_1.jsonl",
                        "--esids", esids, "--sources-dir", self.sources, "--refs", self.refs, *extra, expect=expect)

    def write_json(self, relpath: str, payload) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def facts_payload(self) -> dict:
        return {
            "records": [{"ref": "ref_1", "trial": "NCT02729025",
                         "identity": "NCT02729025｜依洛尤单抗 420 mg 每月一次｜第 16 周",
                         "conclusion": "该披露的结论。"}],
            "facts": [
                {"id": "ocean-tbr", "ref": "ref_1", "study": "NCT02729025", "kind": "有效性",
                 "endpoint": "MDS TBR 较基线变化", "arm": "安慰剂 每月一次", "value": "-5.3",
                 "unit": "%", "timepoint": "第 16 周", "quote": "MDS TBR change with placebo was -5.3%"},
                {"id": "ocean-n", "ref": "ref_1", "study": "NCT02729025", "kind": "试验设计",
                 "endpoint": "入组例数", "arm": "未报告", "value": "129", "unit": "例",
                 "quote": "129 patients were randomized"},
            ],
        }

    def build_ledger(self, payload=None, *extra, expect: int | None = 0):
        facts = self.write_json("work/facts.json", payload if payload is not None else self.facts_payload())
        return self.sh("build_ledger.py", "--facts", facts, "--out", self.ledger,
                        "--refs", self.refs, *extra, expect=expect)

    def chart(self, spec: dict, *extra, expect: int | None = 0):
        path = self.write_json("work/chart-spec.json", spec)
        return self.sh("make_chart.py", path, "--out-dir", self.root / "visualizations",
                        "--chart-skill", self.root / "chartskill", "--no-validate", *extra, expect=expect)

    def bar_spec(self, **overrides) -> dict:
        spec = {"type": "bar", "file": "endpoint-bar-1.json", "title": "MDS TBR 变化（跨试验并列展示）",
                "subTitle": "跨试验并列展示≠头对头比较", "dataSource": "数值事实账本",
                "describe": "两组的 MDS TBR 较基线变化", "axisXTitle": "试验", "axisYTitle": "较基线变化 (%)",
                "data": [{"label": "NCT02729025 · 依洛尤单抗 420 mg 每月一次", "value": -8.3,
                          "description": "依洛尤单抗组 MDS TBR 较基线变化{{ref_1}}"},
                         {"label": "NCT04270760 · 安慰剂 每月一次", "value": -5.3,
                          "description": "安慰剂组 MDS TBR 较基线变化{{ref_2}}"}]}
        spec.update(overrides)
        return spec

    @staticmethod
    def chart_envelope(option: dict) -> dict:
        return {"id": "chart-visualization-json",
                "iframe_template": "https://vcdn.example/iframe-template.json", "option": option}

    def delivery_fixture(self, report_body: str | None = None, citations: dict | None = None,
                         chart: dict | None = None) -> dict:
        """A minimal but *complete* green delivery: report + citations + one chart product."""
        self.prep()
        self.build_ledger()
        vis = self.root / "visualizations"
        if chart is None:
            chart = {"id": "chart-visualization-json",
                     "iframe_template": "https://vcdn.example/iframe-template.json",
                     "option": {"type": "bar", "title": "两组变化并列展示", "subTitle": "并列展示不等于头对头比较",
                                "dataSource": "本地数值事实账本", "describe": "按组展示",
                                "axisXTitle": "试验", "axisYTitle": "较基线变化 (%)",
                                "data": [{"label": "依洛尤单抗组", "value": -8.3, "description": "较基线变化{{ref_1}}"}]}}
        (vis / "endpoint-bar-1.json").write_text(json.dumps(chart, ensure_ascii=False, indent=2), encoding="utf-8")
        body = report_body if report_body is not None else (
            "# 跨试验结果对比\n\n## 速览\n\n依洛尤单抗组的较基线变化为 -5.3 %{{ref_1}}，"
            "入组 129 例{{ref_1}}。\n\n"
            f"::visualization[endpoint-bar]{{path=\"{vis}/endpoint-bar-1.json\"}}\n\n"
            "## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>NCT02729025 · 2 条披露 |\n| --- | --- |\n"
            "| 入组例数 | 129 例{{ref_1}} |\n")
        report_path = self.root / "output" / "report.md"
        report_path.write_text(body, encoding="utf-8")
        citation_path = self.root / "output" / "citations.json"
        if citations is None:
            citations = {"ref_1": {"title": "Evolocumab in HoFH",
                                   "link": "https://pubmed.ncbi.nlm.nih.gov/30561610",
                                   "paper_release_time_str": "2018-11-20"}}
        citation_path.write_text(json.dumps(citations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"report": report_path, "citations": citation_path, "charts": vis}

    def check(self, paths: dict, *extra, expect: int | None = 0):
        return self.sh("check_report.py", "--report", paths["report"], "--citations", paths["citations"],
                        "--charts-dir", paths["charts"], "--vis-prefix", str(paths["charts"]) + "/",
                        *extra, expect=expect)

    # -- prep_sources.py ----------------------------------------------------------------
    def test_prep_writes_sources_and_refs_in_selection_order(self):
        proc = self.prep(expect=0)
        self.assertIn("WROTE 2 record(s)", proc.stdout)
        refs = json.loads(self.refs.read_text(encoding="utf-8"))
        self.assertEqual(list(refs), ["ref_1", "ref_2"])
        self.assertEqual(refs["ref_1"]["esid"], ESID_A)
        self.assertEqual(refs["ref_2"]["esid"], ESID_B)
        self.assertEqual(refs["ref_1"]["title"], "Evolocumab in HoFH")
        self.assertEqual(refs["ref_1"]["link"], "https://pubmed.ncbi.nlm.nih.gov/30561610")
        self.assertEqual(refs["ref_1"]["paper_release_time_str"], "2018-11-20")
        self.assertEqual(refs["ref_1"]["trial_abbreviation"], "OCEAN(a)-DOSE")

    def test_prep_source_body_is_the_record_text_verbatim(self):
        self.prep()
        body = (self.sources / "ref_1.txt").read_text(encoding="utf-8")
        self.assertIn(ABSTRACT_A, body)
        self.assertIn("## arms", body)
        self.assertIn("result=-70.5", body)
        self.assertIn(ESID_A, body.splitlines()[0])

    def test_prep_second_record_without_abstract_uses_summary(self):
        self.prep()
        body = (self.sources / "ref_2.txt").read_text(encoding="utf-8")
        self.assertIn(SUMMARY_B, body)
        self.assertIn("## 摘要（summary）", body)

    def test_prep_duplicate_rows_do_not_create_a_second_ref(self):
        proc = self.prep()
        refs = json.loads(self.refs.read_text(encoding="utf-8"))
        self.assertEqual(len(refs), 2)
        self.assertIn("deduplicated", proc.stderr)

    def test_prep_missing_esid_exits_3_and_consumes_no_ref_number(self):
        proc = self.prep(esids=f"{ESID_A},no_such_esid,{ESID_B}", expect=3)
        self.assertIn("no_such_esid", proc.stderr)
        refs = json.loads(self.refs.read_text(encoding="utf-8"))
        self.assertEqual({key: item["esid"] for key, item in refs.items()},
                         {"ref_1": ESID_A, "ref_2": ESID_B})

    def test_prep_esids_file_ignores_comments_and_blank_lines(self):
        listing = self.root / "work" / "selected.txt"
        listing.write_text(f"# selection\n{ESID_B}\n\n{ESID_A}  # second\n", encoding="utf-8")
        self.sh("prep_sources.py", "--result",
                 self.root / "tool_results/pharmcube-query-clinical-result-with-params/call_1.jsonl",
                 "--esids-file", listing, "--sources-dir", self.sources, "--refs", self.refs)
        refs = json.loads(self.refs.read_text(encoding="utf-8"))
        self.assertEqual([refs["ref_1"]["esid"], refs["ref_2"]["esid"]], [ESID_B, ESID_A])

    def test_prep_discovers_the_pull_without_result_flag(self):
        self.sh("prep_sources.py", "--tool-results", self.root / "tool_results", "--esids", ESID_A,
                 "--sources-dir", self.sources, "--refs", self.refs, expect=0)
        self.assertEqual(len(json.loads(self.refs.read_text(encoding="utf-8"))), 1)

    def test_prep_without_esids_is_a_usage_error(self):
        self.sh("prep_sources.py", "--result",
                 self.root / "tool_results/pharmcube-query-clinical-result-with-params/call_1.jsonl",
                 expect=2)

    # -- build_ledger.py ----------------------------------------------------------------
    def test_ledger_shape_is_exactly_what_the_render_gate_accepts(self):
        self.prep()
        self.build_ledger()
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(set(ledger), {"records", "facts"})
        record = ledger["records"][0]
        self.assertEqual(set(record), {"ref", "trial", "identity", "conclusion"})
        fact = ledger["facts"][0]
        self.assertEqual(list(fact), ["id", "ref", "study", "version", "endpoint", "arm", "population",
                                      "timepoint", "assessment", "kind", "value", "unit", "statistics",
                                      "source_file", "quote"])

    def test_ledger_fills_defaults_without_inventing_values(self):
        self.prep()
        self.build_ledger()
        facts = json.loads(self.ledger.read_text(encoding="utf-8"))["facts"]
        self.assertEqual(len(facts), 2)
        by_id = {fact["id"]: fact for fact in facts}
        self.assertEqual(by_id["ocean-tbr"]["version"], "未报告")
        self.assertEqual(by_id["ocean-tbr"]["population"], "未报告")
        self.assertEqual(by_id["ocean-n"]["statistics"], "")
        self.assertEqual(by_id["ocean-n"]["assessment"], "未报告")
        for fact in facts:                                   # anti-empty-artifact: real payload, not blanks
            for field in ("endpoint", "arm", "kind", "value", "unit", "quote", "study", "ref"):
                self.assertTrue(fact[field].strip(), f"{field} empty in {fact['id']}")

    def test_ledger_source_file_is_absolute_and_exists(self):
        self.prep()
        self.build_ledger()
        for fact in json.loads(self.ledger.read_text(encoding="utf-8"))["facts"]:
            path = Path(fact["source_file"])
            self.assertTrue(path.is_absolute() and path.is_file(), fact["source_file"])
            self.assertIn(fact["quote"].split()[0], path.read_text(encoding="utf-8"))

    def test_ledger_fails_closed_when_quote_is_not_in_the_source(self):
        self.prep()
        payload = self.facts_payload()
        payload["facts"][0]["quote"] = "安慰剂组 MDS TBR 下降 5.3%（原文没有这句话）"
        proc = self.build_ledger(payload, expect=3)
        self.assertIn("not an exact substring", proc.stderr)
        self.assertFalse(self.ledger.exists(), "a failing compile must not write a ledger")

    def test_ledger_fails_closed_when_value_is_absent_from_the_quote(self):
        self.prep()
        payload = self.facts_payload()
        payload["facts"][0]["value"] = "-8.3"                # quote says 5.3
        proc = self.build_ledger(payload, expect=3)
        self.assertIn("absent from `quote`", proc.stderr)

    def test_ledger_reports_every_structural_problem_at_once(self):
        self.prep()
        payload = self.facts_payload()
        payload["facts"][1]["kind"] = "有效性（手工写下划线）"
        payload["facts"][1]["id"] = payload["facts"][0]["id"]
        payload["facts"][1]["ref"] = "ref_9"
        proc = self.build_ledger(payload, expect=3)
        self.assertIn("duplicate fact id", proc.stderr)
        self.assertIn("kind must be one of", proc.stderr)
        self.assertIn("not in records[]", proc.stderr)

    def test_ledger_fills_trial_from_the_ref_inventory(self):
        self.prep()
        payload = self.facts_payload()
        del payload["records"][0]["trial"]
        self.build_ledger(payload)
        self.assertEqual(json.loads(self.ledger.read_text(encoding="utf-8"))["records"][0]["trial"],
                         "OCEAN(a)-DOSE")

    def test_ledger_refuses_to_overwrite_a_good_file_with_a_bad_run(self):
        self.prep()
        self.build_ledger()
        before = self.ledger.read_bytes()
        payload = self.facts_payload()
        del payload["facts"][0]["unit"]
        proc = self.build_ledger(payload, expect=3)
        self.assertIn("missing the `unit` key", proc.stderr)
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_ledger_accepts_an_empty_unit_for_a_dimensionless_value(self):
        self.prep()
        payload = self.facts_payload()
        payload["facts"][0]["unit"] = ""
        self.build_ledger(payload, expect=0)
        ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(ledger["facts"][0]["unit"], "")

    def test_render_drops_the_trailing_space_of_an_empty_unit(self):
        self.prep()
        payload = self.facts_payload()
        payload["facts"][0]["unit"] = ""
        self.build_ledger(payload, expect=0)
        draft = self.root / "work" / "draft.md"
        draft.write_text("## 速览\n\n变化 [[fact:ocean-tbr]]。\n", encoding="utf-8")
        out = self.root / "output" / "report.md"
        self.sh("render-facts.py", "--ledger", self.ledger, "--draft", draft, "--out", out,
                "--audit", self.root / "work" / "audit.json", expect=0)
        rendered = out.read_text(encoding="utf-8")
        self.assertIn("变化 -5.3{{ref_1}}。", rendered)

    def test_ledger_check_only_writes_nothing(self):
        self.prep()
        proc = self.build_ledger(None, "--check", expect=0)
        self.assertIn("OK (check only)", proc.stdout)
        self.assertFalse(self.ledger.exists())

    # -- patch.py -----------------------------------------------------------------------
    def _draft(self, text: str = "依洛尤单抗 420 mg 每月一次\n安慰剂 每月一次\n") -> Path:
        path = self.root / "work" / "draft.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_patch_replaces_exactly_the_declared_count(self):
        path = self._draft()
        proc = self.sh("patch.py", path, "--find", "每月一次", "--replace", "每 12 周给药", "--count", "2")
        self.assertEqual(json.loads(proc.stdout)["matches"], 2)
        self.assertEqual(path.read_text(encoding="utf-8"),
                         "依洛尤单抗 420 mg 每 12 周给药\n安慰剂 每 12 周给药\n")

    def test_patch_assertion_failure_leaves_the_file_untouched(self):
        path = self._draft()
        proc = self.sh("patch.py", path, "--find", "每月一次", "--replace", "x", "--count", "3", expect=3)
        self.assertIn("ASSERT FAILED", proc.stderr)
        self.assertIn("line 1", proc.stderr)
        self.assertIn("每月一次", path.read_text(encoding="utf-8"))

    def test_patch_count_zero_asserts_absence(self):
        path = self._draft()
        self.sh("patch.py", path, "--find", "{{ref_9}}", "--count", "0")
        self.sh("patch.py", path, "--find", "每月一次", "--count", "0", expect=3)

    def test_patch_insert_after_keeps_the_anchor(self):
        path = self._draft("标题\n")
        self.sh("patch.py", path, "--find", "标题", "--insert-after", "--replace", "\n正文")
        self.assertEqual(path.read_text(encoding="utf-8"), "标题\n正文\n")

    def test_patch_unescape_handles_multiline_find_and_replace(self):
        path = self._draft("a\nb\nc\n")
        self.sh("patch.py", path, "--find", r"a\nb", "--replace", r"a\nB", "--unescape")
        self.assertEqual(path.read_text(encoding="utf-8"), "a\nB\nc\n")

    def test_patch_delete_removes_the_match(self):
        path = self._draft("保留\n删除这一行\n")
        self.sh("patch.py", path, "--find", "删除这一行\n", "--delete")
        self.assertEqual(path.read_text(encoding="utf-8"), "保留\n")

    def test_patch_dry_run_changes_nothing(self):
        path = self._draft()
        before = path.read_text(encoding="utf-8")
        proc = self.sh("patch.py", path, "--find", "每月一次", "--replace", "y", "--count", "2", "--dry-run")
        self.assertTrue(json.loads(proc.stdout)["dry_run"])
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    # -- make_chart.py ------------------------------------------------------------------
    def test_make_chart_wraps_the_skeleton_in_the_upstream_envelope(self):
        self.chart(self.bar_spec())
        product = json.loads((self.root / "visualizations" / "endpoint-bar-1.json").read_text(encoding="utf-8"))
        self.assertEqual(set(product), {"id", "iframe_template", "option"})
        self.assertEqual(product["id"], "chart-visualization-json")
        self.assertEqual(product["iframe_template"], "https://vcdn.example/iframe-template.json")
        option = product["option"]
        self.assertEqual(option["type"], "bar")
        self.assertEqual(option["axisYTitle"], "较基线变化 (%)")
        for skeleton_default in ("direction", "group", "stack"):       # skeleton defaults survive
            self.assertIn(skeleton_default, option)
        self.assertNotIn("_comment", option)
        self.assertEqual([row["value"] for row in option["data"]], [-5.3, -8.3])   # value-desc
        for row in option["data"]:                                     # anti-empty-artifact
            self.assertTrue(row["label"].strip() and row["description"].strip())
            self.assertIn("{{ref_", row["description"])

    def test_make_chart_rejects_a_type_file_mismatch(self):
        proc = self.chart(self.bar_spec(file="evidence-timeline.json"), expect=2)
        self.assertIn("cannot be written", proc.stderr)
        self.assertFalse((self.root / "visualizations" / "evidence-timeline.json").exists())

    def test_make_chart_rejects_a_slug_file_name(self):
        proc = self.chart(self.bar_spec(file="mds-tbr-2026-10-10.json"), expect=2)
        self.assertIn("fixed product name", proc.stderr)

    def test_make_chart_fails_when_a_timeline_event_lacks_its_anchor(self):
        spec = {"type": "timeline", "file": "evidence-timeline.json", "title": "t", "subTitle": "s",
                "dataSource": "d", "describe": "x",
                "data": [{"label": "首次披露", "content": "主要分析", "description": "设计变更{{ref_1}}",
                          "time": "2022-11"},
                         {"label": "随访更新", "content": "最终分析", "description": "结论更新{{ref_1}}"}]}
        proc = self.chart(spec, expect=3)
        self.assertIn("time is empty", proc.stderr)
        self.assertFalse((self.root / "visualizations" / "evidence-timeline.json").exists())

    def test_make_chart_warns_on_over_length_timeline_text_and_strict_fails(self):
        spec = {"type": "timeline", "file": "evidence-timeline.json", "title": "t", "subTitle": "s",
                "dataSource": "d", "describe": "x",
                "data": [{"label": "首次披露与主要终点最终分析完整读出更新版", "content": "主要终点最终分析已完整读出的第二次更新",
                          "description": "结论更新{{ref_1}}", "time": "2022-11"}]}
        proc = self.chart(spec, expect=0)
        self.assertIn("limit 18", proc.stderr)
        self.assertTrue((self.root / "visualizations" / "evidence-timeline.json").is_file())
        self.chart(spec, "--strict", expect=3)

    def test_make_chart_flags_a_number_outside_the_time_anchor_but_allows_a_registry_id(self):
        spec = {"type": "timeline", "file": "evidence-timeline.json", "title": "t", "subTitle": "s",
                "dataSource": "d", "describe": "x",
                "data": [{"label": "NCT04270760 首次披露", "content": "主要分析",
                          "description": "第 36 周读出{{ref_1}}", "time": "2022-11"}]}
        proc = self.chart(spec, expect=0)
        self.assertIn("number outside the time anchor", proc.stderr)
        self.assertNotIn("label=", proc.stderr.split("number outside the time anchor")[1][:120])

    def test_make_chart_reports_an_unavailable_validator_instead_of_claiming_success(self):
        path = self.write_json("work/chart-spec.json", self.bar_spec())
        proc = self.sh("make_chart.py", path, "--out-dir", self.root / "visualizations",
                        "--chart-skill", self.root / "chartskill", expect=4)
        self.assertIn('"validation": "unavailable"', proc.stdout)
        self.assertTrue((self.root / "visualizations" / "endpoint-bar-1.json").is_file())

    def test_make_chart_requires_a_group_on_a_line_row(self):
        spec = {"type": "line", "file": "endpoint-line-1.json", "title": "t", "subTitle": "s",
                "dataSource": "d", "describe": "x", "data": [{"label": "第 36 周", "value": -70.5,
                                                              "description": "Lp(a) 变化{{ref_2}}"}]}
        proc = self.chart(spec, expect=3)
        self.assertIn("group is empty", proc.stderr)

    def test_make_chart_rejects_a_timeline_weight_encoding(self):
        spec = {"type": "timeline", "file": "evidence-timeline.json", "title": "t", "subTitle": "s",
                "dataSource": "d", "describe": "x",
                "data": [{"label": "首次披露", "content": "主要分析", "time": "2022-11",
                          "description": "设计变更{{ref_1}}", "weight": 2}]}
        proc = self.chart(spec, expect=3)
        self.assertIn("weight is not supported", proc.stderr)
        self.assertIn("renders every node the same", proc.stderr)
        self.assertFalse((self.root / "visualizations" / "evidence-timeline.json").exists())

    def test_make_chart_rejects_a_timeline_weight_legend(self):
        spec = {"type": "timeline", "file": "evidence-timeline.json", "title": "t", "subTitle": "s",
                "dataSource": "d", "describe": "x",
                "weightLegend": {"show": True, "label": "证据成熟度"},
                "data": [{"label": "首次披露", "content": "主要分析", "time": "2022-11",
                          "description": "设计变更{{ref_1}}"}]}
        proc = self.chart(spec, expect=3)
        self.assertIn("weightLegend is not supported", proc.stderr)
        self.assertFalse((self.root / "visualizations" / "evidence-timeline.json").exists())

    def test_make_chart_rejects_a_timeline_legend_and_a_node_shape(self):
        base = {"type": "timeline", "file": "evidence-timeline.json", "title": "t", "subTitle": "s",
                "dataSource": "d", "describe": "x",
                "data": [{"label": "首次披露", "content": "主要分析", "time": "2022-11",
                          "description": "设计变更{{ref_1}}"}]}
        legend = dict(base, legend=[{"key": "milestone", "label": "研究里程碑", "shape": "empty-circle"}])
        proc = self.chart(legend, expect=3)
        self.assertIn("spec.legend is not supported", proc.stderr)
        shaped = {**base, "data": [{**base["data"][0], "shape": "empty-circle"}]}
        proc = self.chart(shaped, expect=3)
        self.assertIn("shape is not supported", proc.stderr)
        self.assertFalse((self.root / "visualizations" / "evidence-timeline.json").exists())

    def test_shipped_timeline_assets_stop_encoding_maturity_as_node_size(self):
        skeleton_text = (SKILL / "templates" / "charts" / "evidence-timeline.json").read_text(encoding="utf-8")
        skeleton = json.loads(skeleton_text)
        for dead in ('"weight"', '"weightLegend"', '"legend"', '"group"', '"shape"', '"width"', '"height"'):
            self.assertNotIn(dead, skeleton_text, f"the timeline skeleton still ships {dead}")
        self.assertTrue(skeleton["data"], "the skeleton must keep real sample rows")
        for rel in ("references/timeline-diagram.md", "references/chart-templates.md"):
            text = (SKILL / rel).read_text(encoding="utf-8")
            for stale in ("weight 驱动", '"weight": ', '"weightLegend": ', '"legend": ', "weight 0–N",
                          "weight=0", "weight=证据成熟度", "大小=证据成熟度", "节点分类形状",
                          "legend.shape 决定节点形状", "`legend[].key`"):
                self.assertNotIn(stale, text, f"{rel} still advertises {stale!r}")

    # -- make_citations.py --------------------------------------------------------------
    def _citations(self, report_markers: str = '{{ref_1}}', *extra, expect: int | None = 0):
        report = self.root / "output" / "report.md"
        report.write_text(f"正文 {report_markers}\n", encoding="utf-8")
        return self.sh("make_citations.py", "--refs", self.refs, "--out", self.root / "output/citations.json",
                        "--report", report, *extra, expect=expect)

    def test_citations_copy_the_record_fields_byte_for_byte(self):
        self.prep()
        self._citations("{{ref_1}}{{ref_2}}")
        payload = json.loads((self.root / "output" / "citations.json").read_text(encoding="utf-8"))
        refs = json.loads(self.refs.read_text(encoding="utf-8"))
        self.assertEqual(list(payload), ["ref_1", "ref_2"])
        for ref, entry in payload.items():
            self.assertEqual(list(entry), ["title", "link", "paper_release_time_str"])
            self.assertEqual(entry["title"], refs[ref]["title"])
            self.assertEqual(entry["link"], refs[ref]["link"])
            self.assertTrue(entry["title"].strip() and entry["link"].startswith("http"))

    def test_citations_drop_unused_keys_with_a_note(self):
        self.prep()
        proc = self._citations("{{ref_1}}")
        self.assertIn("dropped unused key(s)", proc.stderr)
        self.assertEqual(list(json.loads((self.root / "output" / "citations.json").read_text(encoding="utf-8"))),
                         ["ref_1"])

    def test_citations_keep_unused_keys_on_request(self):
        self.prep()
        self._citations("{{ref_1}}", "--keep-unused")
        self.assertEqual(len(json.loads((self.root / "output" / "citations.json").read_text(encoding="utf-8"))), 2)

    def test_citations_fail_when_the_report_cites_an_unknown_ref(self):
        self.prep()
        proc = self._citations("{{ref_7}}", expect=3)
        self.assertIn("absent from", proc.stderr)

    def test_citations_fail_when_the_report_cites_nothing(self):
        self.prep()
        self._citations("没有任何标记", expect=3)

    def test_citations_fail_on_a_recording_without_a_title(self):
        self.prep()
        refs = json.loads(self.refs.read_text(encoding="utf-8"))
        refs["ref_1"]["title"] = ""
        self.refs.write_text(json.dumps(refs, ensure_ascii=False), encoding="utf-8")
        proc = self._citations("{{ref_1}}", expect=3)
        self.assertIn("never cite a record that did not come back", proc.stderr)

    def test_citations_full_text_substitution_uses_the_retrieved_url(self):
        self.prep()
        self._citations("{{ref_2}}", "--full-text", "ref_2=https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/")
        payload = json.loads((self.root / "output" / "citations.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["ref_2"]["link"], "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/")
        self.assertEqual(payload["ref_2"]["title"], "Olpasiran in ASCVD")

    # -- check_report.py ----------------------------------------------------------------
    def test_check_report_passes_a_complete_delivery(self):
        paths = self.delivery_fixture()
        proc = self.check(paths, "-v")
        self.assertIn("PASS", proc.stdout)
        self.assertIn("chart products — 1 file(s), 1 reference(s)", proc.stdout)

    def test_check_report_catches_unresolved_tokens(self):
        paths = self.delivery_fixture(report_body=(
            "# 报告\n\n[[fact:ocean-tbr]] 未渲染\n\n## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n| 入组例数 | 129 例{{ref_1}} |\n"))
        proc = self.check(paths, expect=3)
        self.assertIn("unresolved fact/result token", proc.stdout)

    def test_check_report_catches_placeholder_braces(self):
        paths = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_n}}\n\n## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n| 入组例数 | 129 例 |\n"))
        proc = self.check(paths, expect=3)
        self.assertIn("placeholder braces", proc.stdout)

    def test_check_report_catches_entity_syntax(self):
        paths = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_1}}(entity:drug)\n\n## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n| 入组例数 | 129 例{{ref_1}} |\n"))
        proc = self.check(paths, expect=3)
        self.assertIn("entity:", proc.stdout)

    def test_check_report_requires_an_appendix_with_data_rows(self):
        paths = self.delivery_fixture(report_body="# 报告\n\n依洛尤单抗{{ref_1}}\n")
        self.assertIn("appendix title", self.check(paths, expect=3).stdout)
        header_only = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_1}}\n\n## 附录：证据对齐矩阵（数值事实账本）\n\n| 维度 | 试验 |\n| --- | --- |\n"))
        self.assertIn("no data row", self.check(header_only, expect=3).stdout)

    def test_check_report_enforces_marker_key_parity_both_ways(self):
        unused = self.delivery_fixture(citations={
            "ref_1": {"title": "Evolocumab in HoFH", "link": "https://pubmed.ncbi.nlm.nih.gov/30561610",
                      "paper_release_time_str": "2018-11-20"},
            "ref_2": {"title": "Olpasiran in ASCVD", "link": "https://pubmed.ncbi.nlm.nih.gov/36342163",
                      "paper_release_time_str": "2022-11-08"}})
        self.assertIn("never used in the report", self.check(unused, expect=3).stdout)
        missing = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_1}} 与 奥帕司兰{{ref_2}}\n\n## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n| 入组例数 | 129 例{{ref_1}} |\n"))
        self.assertIn("markers without a citation key", self.check(missing, expect=3).stdout)

    def test_check_report_catches_an_empty_or_fenced_or_fat_citation_entry(self):
        empty_title = self.delivery_fixture(citations={
            "ref_1": {"title": "", "link": "https://pubmed.ncbi.nlm.nih.gov/30561610",
                      "paper_release_time_str": "2018-11-20"}})
        self.assertIn("empty title", self.check(empty_title, expect=3).stdout)
        fat = self.delivery_fixture(citations={
            "ref_1": {"title": "t", "link": "https://x", "paper_release_time_str": "2018-11-20",
                      "note": "extra"}})
        self.assertIn("extra fields", self.check(fat, expect=3).stdout)
        paths = self.delivery_fixture()
        paths["citations"].write_text("```json\n{}\n```\n", encoding="utf-8")
        self.assertIn("fenced", self.check(paths, expect=3).stdout)

    def test_check_report_rejects_a_bare_option_instead_of_an_envelope(self):
        paths = self.delivery_fixture(chart={"type": "bar", "title": "t", "data": [
            {"label": "a", "value": 1, "description": "d{{ref_1}}"}]})
        self.assertIn("envelope keys must be exactly", self.check(paths, expect=3).stdout)

    def test_check_report_rejects_an_empty_or_mistyped_chart(self):
        empty = self.delivery_fixture(chart={"id": "chart-visualization-json", "iframe_template": "https://x",
                                            "option": {"type": "bar", "data": []}})
        self.assertIn("option.data is empty", self.check(empty, expect=3).stdout)
        mistyped = self.delivery_fixture(chart={"id": "chart-visualization-json", "iframe_template": "https://x",
                                                "option": {"type": "line", "data": [
                                                    {"label": "a", "value": 1, "description": "d{{ref_1}}"}]}})
        self.assertIn("option.type is", self.check(mistyped, expect=3).stdout)

    def test_check_report_rejects_a_dangling_visualization_reference(self):
        paths = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_1}}\n\n"
            f"::visualization[endpoint-bar]{{path=\"{self.root}/visualizations/endpoint-bar-9.json\"}}\n\n"
            "## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n| 入组例数 | 129 例{{ref_1}} |\n"))
        self.assertIn("does not exist", self.check(paths, expect=3).stdout)

    def test_check_report_catches_internal_leaks_and_warns_on_run_logistics(self):
        leaked = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_1}}（source_file: work/sources/ref_1.txt）\n\n"
            "## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n| 入组例数 | 129 例{{ref_1}} |\n"))
        self.assertIn("source_file leaked", self.check(leaked, expect=3).stdout)
        logistic = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_1}}（本次运行环境无外网）\n\n"
            "## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n| 入组例数 | 129 例{{ref_1}} |\n"))
        self.assertEqual(self.check(logistic, expect=4).returncode, 4)

    def test_check_report_exempts_registry_ids_from_the_shared_run_rule(self):
        paths = self.delivery_fixture(chart=self.chart_envelope({
            "type": "bar", "title": "两组变化并列展示", "subTitle": "并列展示不等于头对头比较",
            "dataSource": "本地数值事实账本", "describe": "按组展示",
            "data": [{"label": "NCT02729025 · 依洛尤单抗组", "value": -8.3,
                      "description": "NCT02729025 组较基线变化{{ref_1}}"}]}))
        proc = self.check(paths, expect=0)
        self.assertNotIn("shares an 8-character run", proc.stdout)

    def test_check_report_still_warns_about_a_duplicated_prose_run(self):
        paths = self.delivery_fixture(
            chart=self.chart_envelope({
                "type": "bar", "title": "两组变化并列展示", "subTitle": "并列展示不等于头对头比较",
                "dataSource": "本地数值事实账本", "describe": "按组展示",
                "data": [{"label": "依洛尤单抗组", "value": -8.3,
                          "description": "该终点尚未在对照组评估{{ref_1}}"}]}),
            report_body=(
                "# 报告\n\n依洛尤单抗{{ref_1}}\n\n"
                "## 附录：证据对齐矩阵（数值事实账本）\n\n"
                "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n"
                "| 终点覆盖 | 该终点尚未在对照组评估{{ref_1}} |\n"))
        proc = self.check(paths, expect=4)
        self.assertIn("shares an 8-character run", proc.stdout)

    def test_check_report_exempts_ledger_declared_names_from_the_shared_run_rule(self):
        # Arm / identity names from the run's own ledger are names, not duplicated prose.
        paths = self.delivery_fixture(
            chart=self.chart_envelope({
                "type": "bar", "title": "两组变化并列展示", "subTitle": "并列展示不等于头对头比较",
                "dataSource": "本地数值事实账本", "describe": "按组展示",
                "data": [{"label": "安慰剂每月一次组", "value": -5.3,
                          "description": "安慰剂每月一次组变化{{ref_1}}"}]}),
            report_body=(
                "# 报告\n\n依洛尤单抗{{ref_1}}\n\n"
                "## 附录：证据对齐矩阵（数值事实账本）\n\n"
                "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n"
                "| 安慰剂每月一次组 | -5.3 %{{ref_1}} |\n"))
        proc = self.check(paths, expect=None)
        self.assertNotIn("shares an 8-character run", proc.stdout)

    def test_check_report_warns_about_a_duplicated_ref_inside_one_cell(self):
        paths = self.delivery_fixture(report_body=(
            "# 报告\n\n依洛尤单抗{{ref_1}}\n\n## 附录：证据对齐矩阵（数值事实账本）\n\n"
            "| 维度 | **NCT02729025**<br>2 条披露 |\n| --- | --- |\n"
            "| 入组例数 | 129 例{{ref_1}}；101 例{{ref_1}} |\n"))
        proc = self.check(paths, expect=4)
        self.assertIn("cites the same ref more than once", proc.stdout)

    # -- the chain the model actually runs ------------------------------------------------
    def test_end_to_end_chain_produces_a_delivery_the_real_gate_accepts(self):
        self.prep()
        self.build_ledger()
        draft = self.root / "work" / "draft.md"
        draft.write_text("## 速览\n\nMDS TBR 变化为 [[fact:ocean-tbr]]，入组 [[fact:ocean-n]]。\n\n"
                         f"::visualization[endpoint-bar]{{path=\"{self.root}/visualizations/endpoint-bar-1.json\"}}\n",
                         encoding="utf-8")
        report = self.root / "output" / "report.md"
        self.sh("render-facts.py", "--ledger", self.ledger, "--draft", draft, "--out", report,
                 "--audit", self.root / "work" / "audit.json", expect=0)
        rendered = report.read_text(encoding="utf-8")
        self.assertIn("-5.3 %{{ref_1}}", rendered)
        self.assertIn("## 附录：证据对齐矩阵", rendered)
        appendix_rows = [line for line in rendered.splitlines()
                         if line.startswith("|") and "---" not in line and "维度" not in line]
        self.assertTrue(appendix_rows, "the render gate appended an appendix without data rows")

        self.chart(self.bar_spec(**{
            "title": "两组变化并列展示", "subTitle": "并列展示不等于头对头比较",
            "dataSource": "本地数值事实账本", "describe": "按组展示",
            "data": [{"label": "依洛尤单抗组", "value": -8.3, "description": "较基线变化{{ref_1}}"},
                     {"label": "安慰剂组", "value": -5.3, "description": "较基线变化{{ref_2}}"}]}))
        self.sh("make_citations.py", "--refs", self.refs, "--out", self.root / "output" / "citations.json",
                 "--report", report, expect=0)
        paths = {"report": report, "citations": self.root / "output" / "citations.json",
                 "charts": self.root / "visualizations"}
        proc = self.check(paths, "-v")
        self.assertIn("PASS", proc.stdout)
        self.assertIn("1 reference(s)", proc.stdout)
        payload = json.loads(paths["citations"].read_text(encoding="utf-8"))
        refs = json.loads(self.refs.read_text(encoding="utf-8"))
        self.assertEqual(payload["ref_1"]["title"], refs["ref_1"]["title"])


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    unittest.main(verbosity=2)
