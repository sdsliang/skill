"""Offline regression tests; no runner, Git, network, or real run mutations."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


replay = load_tool("replay-run")
PASS_SCORE = "SCORE scenario=a facts 2/2 warn 0/1 -> PASS\n"
FAIL_SCORE = "SCORE scenario=a facts 1/2 warn 1/1 -> FAIL\n"


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        self.run.mkdir()
        self.prompts = self.root / "prompts"
        self.prompts.mkdir()
        self.local = self.prompts / "v0.15.md"
        self.local.write_bytes(b"system\r\n")
        for key, value in (("SYS_DIR", str(self.prompts)), ("LOCAL_SYS", str(self.local))):
            mocker = patch.object(replay, key, value)
            mocker.start()
            self.addCleanup(mocker.stop)

    def put(self, name, value):
        (self.run / name).write_text(json.dumps(value), encoding="utf-8")

    def seed(self):
        self.put("run.json", {"exit": 0, "enable_web": False, "wall_clock_s": 1.2,
                              "prompt": "24_1_30561610 24_1_36342163"})
        self.put("info.json", {"stats": {"turns": 1, "steps": 2}})
        self.put("debug-history.json", {"raw_model_messages": [
            {"kind": "request", "instructions": "system\r\nplatform", "parts": []},
            {"kind": "response", "parts": [
                {"part_kind": "tool-call", "tool_name": "execute"},
                {"part_kind": "thinking", "content": "abc"}]}]})
        (self.run / "verification.md").write_text("## Checks\n- [PASS] check\n")

    def metrics(self):
        return replay.metrics(str(self.run))

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["replay-run", *args, str(self.run)]), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = replay.main()
        return rc, stdout.getvalue(), stderr.getvalue()

    def test_empty_directory_is_unknown_not_pass_or_web_off(self):
        m = self.metrics()
        for key in ("gate_pass", "enable_web", "calls", "turns", "thinking_chars", "exit"):
            self.assertIsNone(m[key], key)
        rc, out, err = self.cli("--tsv")
        self.assertEqual(rc, 4)
        row = list(csv.DictReader(io.StringIO(out), delimiter="\t"))[0]
        self.assertEqual(row["gate_pass"], "unknown")
        self.assertEqual(row["calls"], "unknown")
        self.assertIn("debug-history.json", err)
        rc, out, _ = self.cli()
        self.assertIn("web=unknown", out)
        self.assertIn("recorded_gate=UNKNOWN", out)

    def test_corrupt_and_wrong_shape_history_never_zero(self):
        self.seed()
        for value in ("{", "[]", '{"raw_model_messages": {}}',
                      '{"raw_model_messages": [null]}',
                      '{"raw_model_messages": [{"kind":"response","parts":[null]}]}'):
            with self.subTest(value=value):
                (self.run / "debug-history.json").write_text(value)
                m = self.metrics()
                self.assertIsNone(m["calls"])
                # The archive's historical gate remains separate from replay completeness.
                self.assertIs(m["gate_pass"], True)
                self.assertEqual(self.cli()[0], 4)

    def test_assertions_missing_fail_warn_and_quoted_tags(self):
        self.seed()
        for text, expected in (("", None), ("prose [PASS]", None),
                               ("## Checks\n- [WARN] note\n", None),
                               ("## Checks\n- [PASS] ok\n- [WARN] note\n", True),
                               ("## Checks\n- [PASS] ok\n- [FAIL] bad\n", False),
                               ("## Checks\n- [PASS] ok\n- [MISSING] bad\n", None),
                               ("## Checks\n- [PASS] ok\n- [PASS]\n", None),
                               ("## Checks\n- [PASS] ok\n## Transcript\n- [FAIL] quoted\n", True)):
            with self.subTest(text=text):
                (self.run / "verification.md").write_text(text)
                self.assertIs(self.metrics()["gate_pass"], expected)
        (self.run / "run.json").unlink()
        self.assertIsNone(self.metrics()["gate_pass"])

    def test_web_requires_boolean_or_explicit_historical_evidence(self):
        self.seed()
        for value in (None, "false", 0, [], {}):
            self.put("run.json", {"exit": 0, "enable_web": value})
            self.assertIsNone(self.metrics()["enable_web"])
        self.put("run.json", {"exit": 0})
        (self.run / "verification.md").write_text("enable_web=false\n- [PASS] ok\n")
        self.assertIs(self.metrics()["enable_web"], False)
        self.put("run.json", {"exit": 0, "enable_web": True})
        self.assertIsNone(self.metrics()["enable_web"])

    def test_non_object_nested_stats_and_invalid_numbers(self):
        self.seed()
        self.put("info.json", {"stats": [1], "turn_usage": "bad"})
        self.put("run.json", {"exit": False, "wall_clock_s": float("nan")})
        m = self.metrics()
        self.assertIsNone(m["exit"])
        self.assertIsNone(m["wall_s"])
        self.assertIsNone(m["usage"])
        self.assertTrue(m["data_issues"])

    def test_scenario_requires_exact_input_ids(self):
        self.seed()
        for prompt in ("refusal", "24_1_30561610 24_1_36342163 24_1_45608045",
                       "24_1_30561610 24_1_36342163_1"):
            self.put("run.json", {"exit": 0, "prompt": prompt})
            self.assertEqual(self.metrics()["scenario"], "unknown")

    def test_prompt_prefix_is_byte_exact_nonempty_longest_and_no_git(self):
        self.seed()
        (self.prompts / "zz-empty.md").write_bytes(b"")
        (self.prompts / "zz-short.md").write_bytes(b"system")
        with patch.object(replay.subprocess, "run", side_effect=AssertionError("no subprocess")):
            m = self.metrics()
        self.assertEqual(m["deployed_sys_version"], "v0.15.md")
        self.assertTrue(m["deployed_sys_matches_local"])
        self.assertEqual(m["deployed_sys_version_source"], "worktree-byte-prefix")
        self.local.write_bytes(b"system\n")
        self.assertFalse(self.metrics()["deployed_sys_matches_local"])
        self.put("debug-history.json", {"raw_model_messages": [
            {"kind": "request", "instructions": "system\nold", "parts": []},
            {"kind": "request", "parts": []}]})
        self.assertIsNone(self.metrics()["deployed_sys_version"])

    def test_tsv_escaping_round_trips_all_frozen_columns(self):
        self.seed()
        m = self.metrics()
        m["run"] = 'run\twith"quotes\r\nline'
        extra = {"commit": "sha\tvalue", "status": "keep\rvalue",
                 "description": 'text\t"quoted"\r\nnext'}
        row = replay.tsv_row(m, extra)
        values = list(csv.reader(io.StringIO(row, newline=""), delimiter="\t"))
        self.assertEqual(len(values), 1)
        self.assertEqual(len(values[0]), 16)
        decoded = dict(zip(replay.TSV_COLUMNS, values[0]))
        self.assertEqual(decoded["r"], m["run"])
        for key, value in extra.items():
            self.assertEqual(decoded[key], value)

    def test_receipts_must_be_real_contained_files(self):
        base = self.run / "tool_results"
        base.mkdir()
        (base / "ok.json").write_text("{}")
        (base / "directory").mkdir()
        (self.root / "outside.json").write_text("{}")
        (base / "escape.json").symlink_to(self.root / "outside.json")
        prefix = "/workspace/tool_results/"
        self.assertTrue(replay._archived(str(self.run), prefix + "ok.json"))
        for rel in ("directory", "missing.json", "../../outside.json", "escape.json", "/etc/passwd"):
            self.assertFalse(replay._archived(str(self.run), prefix + rel), rel)
        self.assertFalse(replay._archived(str(self.run), str(self.root / "outside.json")))
        (self.run / "artifacts").mkdir()
        (self.run / "artifacts" / "tool_results").symlink_to(self.root)
        self.assertFalse(replay._archived(str(self.run), prefix + "outside.json"))

    def test_structured_return_content(self):
        self.seed()
        self.put("debug-history.json", {"raw_model_messages": [{"kind": "request", "parts": [
            {"part_kind": "tool-return", "content": {"path": "/workspace/tool_results/a.json"}}]}]})
        self.assertEqual(self.metrics()["tool_result_pointers"], ["/workspace/tool_results/a.json"])

    def test_pointer_placeholders_are_not_receipts(self):
        self.seed()
        self.put("debug-history.json", {"raw_model_messages": [{"kind": "request", "parts": [
            {"part_kind": "tool-return", "content": "/workspace/tool_results/web_fetch/\u2026 "
             "/workspace/tool_results/web_fetch/... /workspace/tool_results/web_fetch/ "
             "/workspace/tool_results/web_fetch/*.md /workspace/tool_results/web_fetch/real.md."}]}]})
        self.assertEqual(self.metrics()["tool_result_pointers"],
                         ["/workspace/tool_results/web_fetch/real.md"])

    def test_current_score_never_reuses_recorded_score(self):
        self.seed()
        (self.run / "score.txt").write_text(PASS_SCORE)
        with patch.object(replay.subprocess, "run", return_value=subprocess.CompletedProcess([], 3, FAIL_SCORE, "")) as proc:
            score = replay.facts_from_score(str(self.run), "a")
            self.assertEqual(score["facts_ok"], 1)
            proc.assert_called_once()
            rc, out, _ = self.cli("--tsv", "--score")
        self.assertEqual(rc, 3)
        row = list(csv.DictReader(io.StringIO(out), delimiter="\t"))[0]
        self.assertEqual(row["gate_pass"], "1")
        self.assertEqual(row["facts_ok"], "1")
        self.assertEqual(replay.facts_from_dir(str(self.run), "a")["facts_ok"], 2)

    def test_score_failure_and_invalid_output_are_inconclusive(self):
        self.seed()
        cases = [(1, PASS_SCORE), (4, PASS_SCORE), (0, FAIL_SCORE), (3, PASS_SCORE),
                 (0, ""), (0, PASS_SCORE * 2), (0, PASS_SCORE.replace("scenario=a", "scenario=b")),
                 (0, PASS_SCORE.replace("2/2", "3/2")), (0, PASS_SCORE.replace("2/2", "0/0")),
                 (0, "SCORE scenario=a facts 2/2")]
        for rc, output in cases:
            with self.subTest(rc=rc, output=output), patch.object(
                    replay.subprocess, "run", return_value=subprocess.CompletedProcess([], rc, output, "problem")):
                score = replay.facts_from_score(str(self.run), "a")
                self.assertIn("score_error", score)
                self.assertNotIn("facts_ok", score)
        for exc in (OSError("missing"), subprocess.TimeoutExpired("check", 120)):
            with patch.object(replay.subprocess, "run", side_effect=exc):
                self.assertIn("score_error", replay.facts_from_score(str(self.run), "a"))
                self.assertEqual(self.cli("--score")[0], 4)

    def test_score_runs_without_tsv(self):
        self.seed()
        with patch.object(replay.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, PASS_SCORE, "")) as proc:
            rc, out, _ = self.cli("--score")
        proc.assert_called_once()
        self.assertEqual(rc, 0)
        self.assertIn("facts (current-checker): 2/2 PASS", out)


if __name__ == "__main__":
    unittest.main()
