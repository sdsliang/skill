#!/usr/bin/env python3
"""Offline replay of one or more ToolSmith runs — the cost/metrics layer of the loop.

Zero network, zero new runs: everything is read from a run directory produced by
`toolsmith-publish run` (default root `~/.local/state/toolsmith-runs/`).

Why it exists
-------------
`docs/autoresearch-iteration-plan.md` §8.3 defines the campaign table (`results.tsv`)
and §9 makes `calls` the only comparable number. Both need a *reproducible* extraction
from `debug-history.json` + `run.json` + `info.json`, not a hand-read of the log. This
script is that extractor, so a keep/discard call cannot be rationalised after the fact.

Usage
-----
    tools/replay-run.py 20260918-110804-r18-abstract-size        # one-line metrics
    tools/replay-run.py --details <run>                          # + tool distribution
    tools/replay-run.py --tsv <run> [<run> …]                    # campaign TSV rows
    tools/replay-run.py --pointer-only <run>                    # tool_results pointers (E0)

Column semantics (must stay stable — results.tsv is append-only history):
    r            run directory name (timestamp-tag)
    deployed_sys sha256[:12] of the `instructions` actually sent on the last model request
    scenario     a|b|unknown, inferred from the user prompt (scenario-a/b fixtures)
    turns        info.json stats.turns
    steps        info.json stats.steps
    calls        number of `tool-call` parts (the comparable cost number)
    wall_s       run.json wall_clock_s
    params_calls calls of the pharmcube params tool
    execute      calls of the `execute` tool (shell scripts)
    edit_file    calls of `edit_file` / `write_file` (return work)
    thinking_chars  total characters of `thinking` parts (reasoning volume)
    gate_pass    recorded run.json exit == 0 and nonempty verification assertions without FAIL
                 (unknown when evidence is missing; never replaced by today's fact checker)
    artifacts    report.md / citations.json / chart count actually present
    sources      files under artifacts/sources/ (full-text bodies archived)
    tool_results pointers seen in tool returns, checked against contained receipt files
    facts        --score runs today's checker; otherwise only recorded score text is read

Exit codes: 0 = complete replay, 3 = recorded gate/current score failed,
4 = incomplete or invalid evidence/checker failure, 2 = invalid CLI/run path.
TSV retains its frozen columns; missing metrics/gate are `unknown`, unscored facts blank.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

DEFAULT_ROOT = os.path.expanduser("~/.local/state/toolsmith-runs")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS_DIR = os.path.join(REPO, "system-prompts")
LOCAL_SYS = os.path.join(SYS_DIR, "multi-clinical-result-comparison-v0.15.md")


def local_prompts() -> list[tuple[str, bytes]]:
    """Nonempty worktree bytes, longest first; labels are not historical provenance."""
    out = []
    for path in sorted(Path(SYS_DIR).glob("*.md")):
        data = path.read_bytes()
        if data:
            out.append((path.name, data))
    return sorted(out, key=lambda item: -len(item[1]))


def prompt_candidates() -> list[tuple[str, bytes]]:
    """Only inspect local files. Never silently consult a different Git tree."""
    return local_prompts()

#: esids that define the frozen scenario set (`docs/autoresearch-iteration-plan.md` §8.1)
SCENARIO_ESIDS = {
    "a": {"24_1_30561610", "24_1_36342163"},
    "b": {"24_1_30561610", "24_1_45608045"},
}

SHELL_TOOLS = ("execute",)
RETURN_WORK_TOOLS = ("edit_file", "write_file")
POINTER_RX = re.compile(r"/workspace/tool_results/[^\s\"'`\\)\],;]+")
#: prose appends punctuation to a path ("…call_ab4a.jsonl." / "…).md)") — strip it, or the
#: archive check would look for a filename that never existed
POINTER_CLEAN = ".,;)"


def load_json(path: str, issues: list[str] | None = None):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        return data
    except (OSError, ValueError) as exc:
        if issues is not None:
            issues.append(f"{os.path.basename(path)}: {exc}")
        return None


def read_text(path: str, issues: list[str]) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        issues.append(f"{os.path.basename(path)}: {exc}")
        return ""


def history_messages(hist: dict, issues: list[str]) -> list | None:
    raw = hist.get("raw_model_messages")
    if not isinstance(raw, list) or not raw:
        issues.append("debug-history.json: missing/empty raw_model_messages")
        return None
    for msg in raw:
        if (not isinstance(msg, dict) or msg.get("kind") not in ("request", "response")
                or not isinstance(msg.get("parts"), list)
                or (msg.get("instructions") is not None and not isinstance(msg["instructions"], str))):
            issues.append("debug-history.json: invalid message")
            return None
        for part in msg["parts"]:
            if not isinstance(part, dict) or not isinstance(part.get("part_kind"), str):
                issues.append("debug-history.json: invalid part")
                return None
            if part["part_kind"] in ("thinking", "text") and not isinstance(part.get("content"), str):
                issues.append("debug-history.json: invalid text content")
                return None
            if part["part_kind"] == "tool-call" and not isinstance(part.get("tool_name"), str):
                issues.append("debug-history.json: invalid tool name")
                return None
    return raw


def numeric(value, label: str, issues: list[str], integer: bool = False):
    valid = type(value) is int if integer else type(value) in (int, float)
    if valid and value >= 0 and (type(value) is int or math.isfinite(value)):
        return value
    if value is not None:
        issues.append(f"{label}: invalid numeric value")
    return None


def sha12(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def resolve(run: str) -> str:
    if os.path.isdir(run):
        return os.path.abspath(run)
    cand = os.path.join(DEFAULT_ROOT, run)
    if os.path.isdir(cand):
        return cand
    die(f"no such run directory: {run}")


def die(msg: str, code: int = 2):
    print(f"replay-run: {msg}", file=sys.stderr)
    raise SystemExit(code)


def metrics(run_dir: str) -> dict:
    name = os.path.basename(run_dir.rstrip("/"))
    issues: list[str] = []
    hist = load_json(os.path.join(run_dir, "debug-history.json"), issues) or {}
    run = load_json(os.path.join(run_dir, "run.json"), issues) or {}
    info = load_json(os.path.join(run_dir, "info.json"), issues) or {}
    raw = history_messages(hist, issues)
    stats = info.get("stats")
    if not isinstance(stats, dict):
        stats = {}
        issues.append("info.json: missing/invalid stats")
    usage = info.get("turn_usage")
    if not isinstance(usage, dict):
        usage = {}

    calls: dict[str, int] = {}
    thinking_chars = 0
    text_chars = 0
    pointers: list[str] = []
    retry_prompts = 0
    model_turns = 0
    last_instructions = None
    for msg in raw or []:
        if msg.get("kind") == "response":
            model_turns += 1
        if msg.get("kind") == "request":
            last_instructions = msg.get("instructions")
        for part in msg.get("parts") or []:
            kind = part.get("part_kind")
            if kind == "tool-call":
                calls[part.get("tool_name") or "?"] = calls.get(part.get("tool_name") or "?", 0) + 1
            elif kind == "thinking":
                thinking_chars += len(part.get("content") or "")
            elif kind == "text":
                text_chars += len(part.get("content") or "")
            elif kind == "retry-prompt":
                # Includes argument refusals and external fetch failures; both are attempts.
                retry_prompts += 1
            elif kind == "tool-return":
                content = part.get("content")
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False)
                pointers.extend(p.rstrip(POINTER_CLEAN) for p in POINTER_RX.findall(content)
                                if not any(token in p for token in ("\u2026", "...", "*", "?", "<", ">"))
                                and not p.endswith("/"))

    prompt = run.get("prompt") or ""
    if not isinstance(prompt, str):
        issues.append("run.json: invalid prompt")
        prompt = ""
    if not prompt:
        ppath = os.path.join(run_dir, "prompt.txt")
        if os.path.isfile(ppath):
            prompt = read_text(ppath, issues).strip()
    scenario = "unknown"
    ids = set(re.findall(r"\b\d+_[0-9A-Za-z]+_[0-9A-Za-z]+_?\d*\b", prompt))
    for key, want in SCENARIO_ESIDS.items():
        if want == ids:
            scenario = key
    delivered = os.path.getsize(os.path.join(run_dir, "artifacts", "output", "report.md")) if os.path.isfile(
        os.path.join(run_dir, "artifacts", "output", "report.md")) else 0
    if scenario == "b" and delivered:
        scenario = "b?"
    if scenario == "a" and not delivered:
        scenario = "a?"

    art = os.path.join(run_dir, "artifacts")
    report = os.path.join(art, "output", "report.md")
    cites = os.path.join(art, "output", "citations.json")
    vis_dir = os.path.join(art, "visualizations")
    charts = sorted(os.listdir(vis_dir)) if os.path.isdir(vis_dir) else []
    src_dir = os.path.join(art, "sources")
    sources = sorted(os.listdir(src_dir)) if os.path.isdir(src_dir) else []

    verification = read_text(os.path.join(run_dir, "verification.md"), issues)
    checks = re.search(r"^## Checks\s*\n(.*?)(?=^## |\Z)", verification, re.M | re.S)
    check_text = checks.group(1) if checks else verification
    assertions = re.findall(r"^[ \t]*-[ \t]+\[(PASS|FAIL|WARN)\][ \t]+\S[^\n]*$", check_text, re.M)
    assert_fail = assertions.count("FAIL")
    assert_pass = assertions.count("PASS")
    assert_warn = assertions.count("WARN")
    invalid_checks = re.findall(r"^[ \t]*-[ \t]+\[([^\]]*)\]", check_text, re.M)
    checks_valid = bool(assertions) and len(assertions) == len(invalid_checks)
    if not checks_valid:
        issues.append("verification.md: missing/invalid assertions")

    wall_s = numeric(run.get("wall_clock_s"), "wall_clock_s", issues)
    if wall_s is None:
        m = re.search(r"wall clock: (\d+(?:\.\d+)?)s server", verification)
        if m:
            wall_s = numeric(float(m.group(1)), "server wall clock", issues)
    turns = numeric(stats.get("turns"), "stats.turns", issues, integer=True)
    if turns is None and raw is not None:
        turns = model_turns
    exit_code = run.get("exit")
    if type(exit_code) is not int or exit_code < 0:
        issues.append("run.json: missing/invalid exit")
        exit_code = None
    gate_pass = None
    if (assert_fail or (exit_code is not None and exit_code != 0) or run.get("fails")
            or run.get("outcome") in ("failed", "cancelled", "interrupted")
            or run.get("kind") in ("failed", "cancelled", "not_started", "inconclusive", "timeout")):
        gate_pass = False
    elif exit_code == 0 and checks_valid and assert_pass:
        gate_pass = True

    enable_web = run.get("enable_web")
    if type(enable_web) is not bool:
        enable_web = None
        if "enable_web" in run:
            issues.append("run.json: invalid enable_web")
    web_markers = set(re.findall(r"enable_web=(true|false)\b", verification))
    if len(web_markers) == 1:
        recorded_web = web_markers == {"true"}
        if enable_web is not None and enable_web != recorded_web:
            issues.append("enable_web: run.json/verification.md conflict")
            enable_web = None
        elif "enable_web" not in run:
            enable_web = recorded_web
    elif len(web_markers) > 1:
        issues.append("verification.md: conflicting enable_web markers")
        enable_web = None

    deployed_sys_sha = sha12(last_instructions.encode("utf-8")) if last_instructions else None
    deployed_sys_version = None
    prefix_matches = []
    if last_instructions:
        prefix_matches = [fname for fname, data in prompt_candidates()
                          if last_instructions.encode("utf-8").startswith(data)]
        if prefix_matches:
            deployed_sys_version = prefix_matches[0]
    if deployed_sys_sha is None:
        # This is a recorded hash, not proof of a match to today's worktree.
        m = re.search(r"deployed sha=([0-9a-f]{12,64})\b", verification)
        if m:
            deployed_sys_sha = m.group(1)[:12]
    local_bytes = Path(LOCAL_SYS).read_bytes() if os.path.isfile(LOCAL_SYS) else None
    local_sys_sha = sha12(local_bytes) if local_bytes is not None else None
    local_match = (last_instructions.encode("utf-8").startswith(local_bytes)
                   if last_instructions and local_bytes else None)
    recorded_version = re.search(r"deployed system prompt == local[^\n]*?([\w.-]+\.md)", verification)

    return {
        "run": name,
        "dir": run_dir,
        "scenario": scenario,
        "turns": turns,
        "model_turns": model_turns if raw is not None else None,
        "steps": numeric(stats.get("steps"), "stats.steps", issues, integer=True),
        "calls": sum(calls.values()) if raw is not None else None,
        "calls_by_tool": dict(sorted(calls.items(), key=lambda kv: -kv[1])),
        "wall_s": wall_s,
        "exit": exit_code,
        "kind": run.get("kind"),
        "model": run.get("model"),
        "params_calls": calls.get("pharmcube-query-clinical-result-with-params", 0) if raw is not None else None,
        "execute": calls.get("execute", 0) if raw is not None else None,
        "edit_file": sum(calls.get(t, 0) for t in RETURN_WORK_TOOLS) if raw is not None else None,
        "web_fetch": calls.get("web_fetch", 0) if raw is not None else None,
        "task_calls": calls.get("task", 0) if raw is not None else None,
        "thinking_chars": thinking_chars if raw is not None else None,
        "text_chars": text_chars if raw is not None else None,
        "retry_prompts": retry_prompts if raw is not None else None,
        "assert_pass": assert_pass,
        "assert_fail": assert_fail,
        "assert_warn": assert_warn,
        "gate_pass": gate_pass,
        "report_bytes": os.path.getsize(report) if os.path.isfile(report) else 0,
        "citations_bytes": os.path.getsize(cites) if os.path.isfile(cites) else 0,
        "charts": charts,
        "sources": sources,
        "tool_result_pointers": sorted(set(pointers)),
        "tool_results_archived": sum(1 for p in set(pointers) if _archived(run_dir, p)),
        "deployed_sys_sha": deployed_sys_sha,
        # (O32 corollary) the assembled blob carries the platform's `## Web Tools` block when
        # enable_web is on (654 B), so `deployed_sys_sha` is only comparable between runs with
        # the same web setting — the marker travels with the metric.
        "enable_web": enable_web,
        "deployed_sys_version": deployed_sys_version,
        "deployed_sys_version_source": "worktree-byte-prefix" if prefix_matches else "unknown",
        "deployed_sys_prefix_matches": prefix_matches,
        "recorded_sys_version": recorded_version.group(1) if recorded_version else None,
        "local_sys_sha": local_sys_sha,
        "deployed_sys_matches_local": local_match,
        "usage": numeric(usage.get("total_tokens"), "turn_usage.total_tokens", issues, integer=True),
        "data_issues": issues,
    }


def _archived(run_dir: str, pointer: str) -> bool:
    """Receipt already on disk? Two locations, because there are two eras:
    * `<run>/tool_results/…` — pulled mid-run by the runner's ReceiptArchiver (2026-09-18+);
    * `<run>/artifacts/tool_results/…` — would only exist if the platform ever archived it
      (it does not: `tool_results` is stripped at persist and filtered from the archive).
    """
    prefix = "/workspace/tool_results/"
    if not pointer.startswith(prefix):
        return False
    rel = PurePosixPath(pointer[len(prefix):])
    if rel.is_absolute() or not rel.parts or ".." in rel.parts or "\\" in str(rel):
        return False
    run_root = Path(run_dir).resolve()
    for base in (run_root / "tool_results", run_root / "artifacts" / "tool_results"):
        try:
            if base.resolve() != base:
                continue
            target = (base / str(rel)).resolve()
            if (base.is_relative_to(run_root) and target.is_relative_to(base)
                    and target.is_file()):
                return True
        except (OSError, RuntimeError):
            continue
    return False


def show(m: dict, details: bool) -> None:
    print(f"{m['run']}  scenario={m['scenario']}  model={m['model']}  "
          f"exit={m['exit']} kind={m['kind']}  recorded_gate={ {True: 'PASS', False: 'FAIL', None: 'UNKNOWN'}[m['gate_pass']]}")
    print(f"  turns={m['turns']} (model_turns={m['model_turns']}) steps={m['steps']} calls={m['calls']} "
          f"wall_s={m['wall_s']} thinking_chars={m['thinking_chars']} tokens={m['usage']}")
    print(f"  params={m['params_calls']} execute={m['execute']} edit/write={m['edit_file']} "
          f"web_fetch={m['web_fetch']} task={m['task_calls']} retry_prompts={m['retry_prompts']}")
    print(f"  report={m['report_bytes']}B citations={m['citations_bytes']}B "
          f"charts={len(m['charts'])} sources={len(m['sources'])}"
          + (f" {m['sources']}" if m["sources"] else ""))
    print(f"  tool_results: pointers={len(m['tool_result_pointers'])} "
          f"archived_in_run_dir={m['tool_results_archived']}")
    print(f"  deployed_sys={m['deployed_sys_sha']} ({m['deployed_sys_version']}) "
          f"web={ {True: 'on', False: 'off', None: 'unknown'}[m['enable_web']]} "
          f"local_sys={m['local_sys_sha']} match={m['deployed_sys_matches_local']}")
    if details:
        print(f"  assertions: {m['assert_pass']} PASS / {m['assert_fail']} FAIL / {m['assert_warn']} WARN")
        print(f"  prefix provenance: {m['deployed_sys_version_source']}; "
              f"historical label: {m['recorded_sys_version']}")
        print("  calls by tool:")
        for tool, n in m["calls_by_tool"].items():
            print(f"    {n:3d}  {tool}")
        if m["tool_result_pointers"]:
            print("  tool_results pointers (receipts truth — E0):")
            for p in m["tool_result_pointers"]:
                print(f"    {'ARCHIVED' if _archived(m['dir'], p) else 'MISSING ':>8}  {p}")


TSV_COLUMNS = (
    "r commit deployed_sys_sha scenario turns calls wall_s params_calls execute edit_file "
    "thinking_chars gate_pass facts_ok facts_total status description"
).split()


def tsv_row(m: dict, extra: dict) -> str:
    row = {
        "r": m["run"],
        "commit": extra.get("commit", ""),
        "deployed_sys_sha": m["deployed_sys_sha"] or "",
        "scenario": m["scenario"],
        "turns": m["turns"],
        "calls": m["calls"],
        "wall_s": m["wall_s"],
        "params_calls": m["params_calls"],
        "execute": m["execute"],
        "edit_file": m["edit_file"],
        "thinking_chars": m["thinking_chars"],
        "gate_pass": {True: "1", False: "0", None: "unknown"}[m["gate_pass"]],
        "facts_ok": extra.get("facts_ok", ""),
        "facts_total": extra.get("facts_total", ""),
        "status": extra.get("status", ""),
        "description": extra.get("description", ""),
    }
    buf = io.StringIO(newline="")
    csv.writer(buf, delimiter="\t", lineterminator="\r\n").writerow(
        "unknown" if row[c] is None else row[c] for c in TSV_COLUMNS)
    return buf.getvalue()[:-2]


SCORE_RX = re.compile(
    r"^SCORE scenario=([ab]) facts (\d+)/(\d+) warn (\d+)/(\d+) -> (PASS|FAIL)\s*$", re.M)


def parse_score(text: str, scenario: str | None = None) -> dict:
    matches = list(SCORE_RX.finditer(text))
    if len(matches) != 1:
        return {"score_error": "expected exactly one complete SCORE line"}
    m = matches[0]
    got, ok, total, warn_ok, warn_total, verdict = m.groups()
    ok, total, warn_ok, warn_total = map(int, (ok, total, warn_ok, warn_total))
    if (scenario is not None and got != scenario) or not (0 <= ok <= total and total > 0):
        return {"score_error": "SCORE scenario/count mismatch"}
    if not 0 <= warn_ok <= warn_total or (verdict == "PASS") != (ok == total):
        return {"score_error": "inconsistent SCORE verdict/counts"}
    return {"facts_ok": ok, "facts_total": total, "score_verdict": verdict,
            "score_scenario": got, "warn_ok": warn_ok, "warn_total": warn_total}


def facts_from_dir(run_dir: str, scenario: str | None = None) -> dict:
    """Historical score only; --score never uses this cache."""
    for name in ("facts.txt", "score.txt", "verification.md"):
        path = Path(run_dir) / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return {"score_error": f"{name}: {exc}"}
        if "SCORE scenario=" in text:
            score = parse_score(text, scenario)
            score["score_source"] = f"recorded:{name}"
            return score
    return {}


def facts_from_score(run_dir: str, scenario: str | None = None) -> dict:
    """Run today's checker, without changing the recorded historical gate."""
    if scenario not in ("a", "b"):
        return {"score_error": "cannot score an unknown scenario"}
    try:
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "evals", "fact-check", "check.py"),
             "--run", run_dir, "--scenario", scenario],
            capture_output=True, text=True, timeout=120, cwd=REPO,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        return {"score_error": f"checker could not complete: {exc}"}
    if proc.returncode not in (0, 3):
        return {"check_exit": proc.returncode,
                "score_error": f"checker exit {proc.returncode}: {proc.stderr.strip()[:500]}"}
    score = parse_score(proc.stdout, scenario)
    if "score_error" not in score:
        expected_exit = 0 if score["score_verdict"] == "PASS" else 3
        if proc.returncode != expected_exit:
            score = {"score_error": "checker exit contradicts SCORE verdict"}
    score.update(check_exit=proc.returncode, score_source="current-checker")
    return score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="run directory or its name under ~/.local/state/toolsmith-runs")
    ap.add_argument("--details", action="store_true", help="tool distribution + per-pointer archive state")
    ap.add_argument("--tsv", action="store_true", help="emit campaign TSV rows (results.tsv columns)")
    ap.add_argument("--pointer-only", dest="pointer_only", action="store_true",
                    help="print only the tool_results pointers (E0 receipts backtest)")
    ap.add_argument("--description", default="", help="TSV description column")
    ap.add_argument("--status", default="", help="TSV status column (keep/discard/…)")
    ap.add_argument("--commit", default="", help="TSV commit column")
    ap.add_argument("--score", action="store_true",
                    help="fill facts_ok/facts_total by running evals/fact-check/check.py (offline)")
    ap.add_argument("--no-header", dest="no_header", action="store_true", help="suppress the TSV header")
    args = ap.parse_args()

    if args.tsv and not args.no_header:
        print("\t".join(TSV_COLUMNS))
    result = 0
    for run in args.runs:
        run_dir = resolve(run)
        m = metrics(run_dir)
        for issue in m["data_issues"]:
            print(f"replay-run: {m['run']}: {issue}", file=sys.stderr)
        if m["data_issues"] or m["gate_pass"] is None:
            result = 4
        elif m["gate_pass"] is False and result != 4:
            result = 3
        if args.pointer_only:
            for p in m["tool_result_pointers"]:
                print(f"{m['run']}\t{'ARCHIVED' if _archived(run_dir, p) else 'MISSING'}\t{p}")
            continue
        scenario = m["scenario"].rstrip("?")
        extra = (facts_from_score(run_dir, scenario) if args.score
                 else facts_from_dir(run_dir, scenario if scenario in ("a", "b") else None))
        if "score_error" in extra:
            print(f"replay-run: {m['run']}: {extra['score_error']}", file=sys.stderr)
            result = 4
        elif args.score and extra.get("check_exit") == 3 and result != 4:
            result = 3
        if args.tsv:
            extra.update({"description": args.description, "status": args.status, "commit": args.commit})
            print(tsv_row(m, extra))
        else:
            show(m, args.details)
            if extra:
                print(f"  facts ({extra.get('score_source', 'unknown')}): "
                      f"{extra.get('facts_ok', 'unknown')}/{extra.get('facts_total', 'unknown')} "
                      f"{extra.get('score_verdict', 'INCONCLUSIVE')}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
