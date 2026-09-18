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
    tools/replay-run.py --pointers <run>                         # tool_results pointers (E0)
    tools/replay-run.py --deployed <run>                         # deployed sys/skill vs local

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
    edit_file    calls of `edit_file` / `write_file` / `read_file` (return work)
    thinking_chars  total characters of `thinking` parts (reasoning volume)
    gate_pass    run.json exit == 0 and no assertion FAIL in verification.md
    artifacts    report.md / citations.json / chart count actually present
    sources      files under artifacts/sources/ (full-text bodies archived)
    tool_results pointers seen in tool returns (0 today — see the ledger O-item)
    facts        left to `evals/fact-check/check.py`; this script does not score facts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

DEFAULT_ROOT = os.path.expanduser("~/.local/state/toolsmith-runs")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS_DIR = os.path.join(REPO, "system-prompts")
LOCAL_SYS = os.path.join(SYS_DIR, "multi-clinical-result-comparison-v0.15.md")


def local_prompts() -> list[tuple[str, str]]:
    """(label, text) for every local system prompt, newest version label first.

    The deployed prompt is our prompt **plus** platform boilerplate (`toolsmith-publish
    instructions`), so identity is tested as a *byte prefix* — hashing the assembled
    instructions can never equal a local file, which is why the two are reported separately:
    `deployed_sys_sha` (assembled, comparable across runs and with the §6 table) and
    `deployed_sys_version` (which local file is a prefix of it).
    """
    out = []
    for name in sorted(os.listdir(SYS_DIR), reverse=True):
        if name.endswith(".md"):
            with open(os.path.join(SYS_DIR, name), encoding="utf-8") as fh:
                out.append((name, fh.read()))
    return out


def prompt_candidates() -> list[tuple[str, str]]:
    """Local prompt files plus the committed (HEAD) copy of the current one.

    Runs made before the worktree changed can only be identified against the committed
    bytes, so `git show HEAD:<prompt>` is offered as an extra candidate. Offline and
    best-effort: no git here is not an error.
    """
    cands = local_prompts()
    try:
        import subprocess

        rel = os.path.relpath(LOCAL_SYS, REPO)
        text = subprocess.run(
            ["git", "-C", REPO, "show", f"HEAD:{rel}"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
        cands.append((os.path.basename(LOCAL_SYS) + "@HEAD", text))
    except Exception:
        pass
    return cands

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


def load_json(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
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
    hist = load_json(os.path.join(run_dir, "debug-history.json")) or {}
    run = load_json(os.path.join(run_dir, "run.json")) or {}
    info = load_json(os.path.join(run_dir, "info.json")) or {}
    raw = hist.get("raw_model_messages") or []

    calls: dict[str, int] = {}
    thinking_chars = 0
    text_chars = 0
    pointers: list[str] = []
    retry_prompts = 0
    model_turns = 0
    last_instructions = None
    for msg in raw:
        if msg.get("kind") == "response":
            model_turns += 1
        if msg.get("kind") == "request" and msg.get("instructions"):
            last_instructions = msg["instructions"]
        for part in msg.get("parts") or []:
            kind = part.get("part_kind")
            if kind == "tool-call":
                calls[part.get("tool_name") or "?"] = calls.get(part.get("tool_name") or "?", 0) + 1
            elif kind == "thinking":
                thinking_chars += len(part.get("content") or "")
            elif kind == "text":
                thinking_chars += 0
                text_chars += len(part.get("content") or "")
            elif kind == "retry-prompt":
                # schema-rejected call: the model re-issued it, both are billed calls
                retry_prompts += 1
            elif kind == "tool-return":
                pointers.extend(p.rstrip(POINTER_CLEAN)
                                for p in POINTER_RX.findall(part.get("content") or ""))

    prompt = run.get("prompt") or ""
    if not prompt:
        ppath = os.path.join(run_dir, "prompt.txt")
        if os.path.isfile(ppath):
            with open(ppath, encoding="utf-8", errors="ignore") as fh:
                prompt = fh.read().strip()
    scenario = "unknown"
    ids = set(re.findall(r"\b\d+_[0-9A-Za-z]+_[0-9A-Za-z]+_?\d*\b", prompt))
    for key, want in SCENARIO_ESIDS.items():
        if want.issubset(ids):
            scenario = key
    if scenario == "unknown" and re.search(r"refus|拒", prompt, re.I):
        scenario = "b"
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

    verification = ""
    vpath = os.path.join(run_dir, "verification.md")
    if os.path.isfile(vpath):
        with open(vpath, encoding="utf-8", errors="ignore") as fh:
            verification = fh.read()
    assert_fail = len(re.findall(r"\[FAIL\]", verification))
    assert_pass = len(re.findall(r"\[PASS\]", verification))

    wall_s = run.get("wall_clock_s")
    if wall_s is None:
        m = re.search(r"wall clock: ([\d.]+)s server", verification)
        if m:
            wall_s = float(m.group(1))
    turns = (info.get("stats") or {}).get("turns")
    if turns is None:
        # pre-2026-09-15 run dirs: no info.json → report client-side model turns
        turns = model_turns
    exit_code = run.get("exit")
    if exit_code is None:
        exit_code = 0 if assert_fail == 0 else 3

    deployed_sys_sha = sha12(last_instructions.encode()) if last_instructions else None
    deployed_sys_version = "(no instructions captured)" if not last_instructions else None
    if last_instructions:
        for fname, text in prompt_candidates():
            if last_instructions.startswith(text):
                deployed_sys_version = fname
                break
        if deployed_sys_version is None:
            deployed_sys_version = "(assembled; no local/HEAD prompt is a prefix)"
    if deployed_sys_sha is None:
        # pre-2026-09-15 dirs: only the assembled sha survives, recorded by the old harness
        m = re.search(r"deployed sha=([0-9a-f]{8,64})", verification)
        if m:
            deployed_sys_sha = m.group(1)[:12]
    local_sys_sha = sha12(open(LOCAL_SYS, "rb").read()) if os.path.isfile(LOCAL_SYS) else None
    local_sys_name = os.path.basename(LOCAL_SYS)

    return {
        "run": name,
        "dir": run_dir,
        "scenario": scenario,
        "turns": turns,
        "model_turns": model_turns,
        "steps": (info.get("stats") or {}).get("steps"),
        "calls": sum(calls.values()),
        "calls_by_tool": dict(sorted(calls.items(), key=lambda kv: -kv[1])),
        "wall_s": wall_s,
        "exit": exit_code,
        "kind": run.get("kind"),
        "model": run.get("model"),
        "params_calls": calls.get("pharmcube-query-clinical-result-with-params", 0),
        "execute": calls.get("execute", 0),
        "edit_file": sum(calls.get(t, 0) for t in RETURN_WORK_TOOLS),
        "web_fetch": calls.get("web_fetch", 0),
        "task_calls": calls.get("task", 0),
        "thinking_chars": thinking_chars,
        "text_chars": text_chars,
        "retry_prompts": retry_prompts,
        "assert_pass": assert_pass,
        "assert_fail": assert_fail,
        "gate_pass": exit_code == 0 and assert_fail == 0,
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
        "enable_web": bool(run.get("enable_web")),
        "deployed_sys_version": deployed_sys_version,
        "local_sys_sha": local_sys_sha,
        "deployed_sys_matches_local": deployed_sys_version == local_sys_name,
        "usage": ((info.get("turn_usage") or {}).get("total_tokens")),
    }


def _archived(run_dir: str, pointer: str) -> bool:
    """Receipt already on disk? Two locations, because there are two eras:
    * `<run>/tool_results/…` — pulled mid-run by the runner's ReceiptArchiver (2026-09-18+);
    * `<run>/artifacts/tool_results/…` — would only exist if the platform ever archived it
      (it does not: `tool_results` is stripped at persist and filtered from the archive).
    """
    rel = pointer.replace("/workspace/", "")
    return (os.path.isfile(os.path.join(run_dir, rel))
            or os.path.isfile(os.path.join(run_dir, "artifacts", rel)))


def show(m: dict, details: bool) -> None:
    print(f"{m['run']}  scenario={m['scenario']}  model={m['model']}  "
          f"exit={m['exit']} kind={m['kind']}  gate={'PASS' if m['gate_pass'] else 'FAIL'}")
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
          f"web={'on' if m['enable_web'] else 'off'} "
          f"local_sys={m['local_sys_sha']} match={m['deployed_sys_matches_local']}")
    if details:
        print(f"  assertions: {m['assert_pass']} PASS / {m['assert_fail']} FAIL")
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
        "gate_pass": "1" if m["gate_pass"] else "0",
        "facts_ok": extra.get("facts_ok", ""),
        "facts_total": extra.get("facts_total", ""),
        "status": extra.get("status", ""),
        "description": extra.get("description", ""),
    }
    return "\t".join(str(row[c]) for c in TSV_COLUMNS)


def facts_from_dir(run_dir: str) -> dict:
    """Read a `SCORE scenario=… facts <ok>/<total>` line if the scoring output was kept."""
    return facts_from_score(run_dir)


def facts_from_score(run_dir: str, scenario: str | None = None) -> dict:
    """Offline fact score via `evals/fact-check/check.py` (no network, no new run).

    Kept in-process (subprocess) so a TSV row carries the quality layer too: `facts_ok`
    missing from a row is what made the §6 table unable to answer "cost down, quality up?"
    """
    for name in ("verification.md", "facts.txt", "score.txt"):
        path = os.path.join(run_dir, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="ignore") as fh:
            m = re.search(r"SCORE scenario=(\w+) facts (\d+)/(\d+)", fh.read())
        if m:
            return {"facts_ok": m.group(2), "facts_total": m.group(3)}
    if not scenario or scenario not in ("a", "b"):
        return {}
    import subprocess

    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "evals", "fact-check", "check.py"),
         "--run", run_dir, "--scenario", scenario],
        capture_output=True, text=True, timeout=600, cwd=REPO,
    )
    m = re.search(r"SCORE scenario=\w+ facts (\d+)/(\d+)", proc.stdout)
    if not m:
        return {}
    return {"facts_ok": m.group(1), "facts_total": m.group(2), "check_exit": proc.returncode}


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
    for run in args.runs:
        run_dir = resolve(run)
        m = metrics(run_dir)
        if args.pointer_only:
            for p in m["tool_result_pointers"]:
                print(f"{m['run']}\t{'ARCHIVED' if _archived(run_dir, p) else 'MISSING'}\t{p}")
            continue
        if args.tsv:
            extra = facts_from_score(run_dir, m["scenario"].rstrip("?")) if args.score else facts_from_dir(run_dir)
            extra.update({"description": args.description, "status": args.status, "commit": args.commit})
            print(tsv_row(m, extra))
        else:
            show(m, args.details)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
