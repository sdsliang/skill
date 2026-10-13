#!/usr/bin/env python3
"""Semantic wall-clock breakdown of one ToolSmith run (read-only, offline).

Not the agent flow (tool calls per step) but the *semantic* pipeline: how long the run
spent loading its contract, pulling records, reading the delivered evidence, extracting
facts, composing citations, writing the report, drawing charts, running the gates,
delivering.

Data source: `<run>/debug-history.json` -> `raw_model_messages`.
Every assistant message carries `usage` (output_tokens + reasoning_tokens) and a
`timestamp` that is the *start of generation*; the next message carries the `tool-return`
parts with their own timestamps. Hence, for step i:

    generation+exec(i) = t(first tool-return of i+1) - t(assistant i)
    tool span(i)       = t(last return) - t(first return)
    generation(i)      = (generation+exec) - tool span

`generation(i)` is split into thinking vs writing by the token mix (`reasoning_tokens` vs
`output_tokens - reasoning_tokens`) and across semantic phases by the byte volume of the
arguments typed in that step. Classification is call-aware: a call is attributed by the
target it acts on (the file a `write_file` touches, the script an `execute` runs, the path
a `read_file` opens); an `execute` command is split into sub-commands (heredoc payloads
included) so a step that both reads sources and rebuilds the ledger splits honestly.

Caveat that no classifier can remove: reasoning tokens are billed to the step that happens
to carry them, and the model decides where to think. A step whose *target* is "read the
report template" can carry 60 s of report-planning thinking. The `--artifacts` view is the
step-independent companion: it converts authored bytes into estimated typing time using a
decode rate regressed from the same run.

Usage:
  python3 -B tools/semantic-timing.py <run-dir> [...] [--rows] [--artifacts] [--json OUT]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

# ---------------------------------------------------------------- semantic phases
PHASES = [
    "装载契约 load contract",
    "取数 fetch records",
    "源文阅读/取证 sources",
    "事实与账本 facts/ledger",
    "自产物回读/返工 self-read",
    "报告正文 report",
    "图表 charts",
    "引用编撰 citations",
    "门禁自检 gates",
    "交付 present_artifact",
    "其他 other",
]
(LOAD, FETCH, SOURCES, FACTS, SELF, REPORT, CHARTS, CITE, GATES, DELIVER,
 OTHER) = PHASES
PHASE_NAMES = DISPLAY_ORDER = PHASES

# A step whose generation is almost all reasoning and which touches no artifact is a "long
# thinking step": its nominal tool call (read a template, probe a source) is only the excuse.
# The doc's derived "planning" number is the sum of these; the excerpt table shows why.
THINK_DOMINANT = 0.80   # reasoning_tokens / output_tokens
THINK_LONG_S = 40.0     # generation seconds

SKILL_DIR_RX = re.compile(
    r"multi-clinical-result-comparison/(?:SKILL\.md|references/|templates/|scripts/|assets/)"
    r"|toolbox\.md|input-contract\.md|mode-detection\.md|timeline-diagram\.md"
    r"|citation-and-ref\.md|prose-style-zh\.md|chart-templates\.md|load_skill")
SOURCES_RX = re.compile(r"work/sources|sources/ref[-_\w]*\.(?:txt|md|json)|ref_\d"
                        r"|curl\s|fullTextXML|europepmc|clinicaltrials\.gov")
REPORT_RX = re.compile(r"(?<![\w-])report\.md|draft\.md|patch\.py")
CITE_RX = re.compile(r"make_citations\.py|citations\.json")
GATE_RX = re.compile(r"check_report\.py|tell-scan\.py|validate-cli|make_citations\.py[^\n]*--check")
FACTS_RX = re.compile(r"build_ledger\.py|merge_ref_facts|render-facts\.py|ledger\.json"
                      r"|facts\.json|audit\.json")
CHARTS_RX = re.compile(r"make_chart\.py|visualizations?/|charts?/|chart-templates")
FETCH_RX = re.compile(r"pharmcube-query-clinical-result|prep_sources\.py|extra_esids"
                      r"|selected_fields")
SELF_DIR = re.compile(r"(?:^|[\s\"'(])(?:/workspace/)?(?:work|output|visualizations)/")

SCRIPT_RX = ((GATE_RX, GATES), (CITE_RX, CITE), (FACTS_RX, FACTS), (CHARTS_RX, CHARTS),
             (REPORT_RX, REPORT), (SOURCES_RX, SOURCES), (FETCH_RX, FETCH))
HEREDOC_RX = re.compile(r"<<\s*-?'?(\w+)'?\n(.*?)(?:\n\1\b)", re.S)
REDIRECT_RX = re.compile(r"(?:>>?|cat\s*>+)\s*([\w./-]+\.(?:md|json|txt|csv|py|js))")
PATH_RX = re.compile(r"[\w./-]+\.(?:md|json|txt|csv|py|js)")


def _by_path(path: str) -> str | None:
    if not path:
        return None
    if SKILL_DIR_RX.search(path):
        return LOAD
    if SOURCES_RX.search(path):
        return SOURCES
    if CITE_RX.search(path):
        return CITE
    if GATE_RX.search(path):
        return GATES
    if REPORT_RX.search(path):
        return REPORT
    if FACTS_RX.search(path):
        return FACTS
    if CHARTS_RX.search(path):
        return CHARTS
    if SELF_DIR.search(path):
        return SELF
    return None


def _script_phase(text: str) -> str | None:
    for rx, ph in SCRIPT_RX:
        if rx.search(text):
            return ph
    return None


def _segment_phase(text: str) -> str | None:
    """Phase of one shell sub-command: redirect target, then scripts, then paths."""
    for m in re.finditer(r"(?:>>?|cat\s*>+)\s*([\w./-]+\.(?:md|json|txt|csv))", text):
        ph = _by_path(m.group(1))
        if ph:
            return ph
    ph = _script_phase(text)
    if ph:
        return ph
    for m in PATH_RX.finditer(text):
        ph = _by_path(m.group(0))
        if ph:
            return ph
    return None


def segments(args: str) -> list[tuple[str, int]]:
    """Split one shell command into (phase, weight) parts so mixed steps split honestly."""
    out: list[tuple[str, int]] = []
    spans: list[tuple[int, int]] = []
    for m in HEREDOC_RX.finditer(args):
        spans.append((m.start(), m.end()))
        head = args[max(0, m.start() - 400):m.start()]
        rm = None
        for rm in REDIRECT_RX.finditer(head):
            pass
        ph = _by_path(rm.group(1)) if rm else None
        payload = m.group(2)
        if not ph:  # heredoc fed to a program: classify the payload lines themselves
            head_ph = _segment_phase(head)
            w: dict[str, int] = {}
            for line in payload.splitlines():
                phl = _segment_phase(line) or head_ph or OTHER
                w[phl] = w.get(phl, 0) + max(len(line), 8)
            for phl, n in w.items():
                out.append((phl, n))
            continue
        out.append((ph, max(len(payload), 40)))
    rest, prev = [], 0
    for a, b in spans:
        rest.append(args[prev:a])
        prev = b
    rest.append(args[prev:])
    for chunk in re.split(r"&&|\|\||;|\n|\|", "\n".join(rest)):
        chunk = chunk.strip()
        if len(chunk) < 4:
            continue
        out.append((_segment_phase(chunk) or OTHER, max(len(chunk), 20)))
    return out or [(OTHER, max(len(args), 40))]


def _arg_path(args: str, key: str) -> str:
    """Path value of an argument in either JSON form or the readable `key: value` form."""
    m = re.search(r'"%s"\s*:\s*"([^"]+)"' % key, args) or \
        re.search(r"^%s:\s*(\S+)" % key, args, re.M)
    return m.group(1).strip('"') if m else ""


def classify_call(name: str, args: str) -> str:
    """Attribute one tool call to a semantic phase by the target it acts on."""
    if name == "present_artifact":
        return DELIVER
    if name == "load_skill":
        return LOAD
    if name.startswith("pharmcube-"):
        return FETCH
    if name == "write_file":
        return _by_path(_arg_path(args, "file_path")) or OTHER
    if name in ("read_file", "read_media", "ls", "grep", "glob"):
        return _by_path(_arg_path(args, r"(?:file_path|path|pattern)")) or LOAD
    if name == "execute":
        weight: dict[str, int] = {}
        for ph, n in segments(args):
            weight[ph] = weight.get(ph, 0) + n
        return max(weight, key=weight.get) if weight else OTHER
    return _segment_phase(args) or OTHER


# ---------------------------------------------------------------- run parsing
def ts(part) -> float | None:
    s = part.get("timestamp")
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s).timestamp()


def args_text(name: str, raw: str) -> str:
    """Readable argument text: JSON escapes resolved so shell splits/heredocs work."""
    try:
        d = json.loads(raw)
    except Exception:
        return raw
    if isinstance(d, dict):
        return "\n".join(f"{k}: {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}"
                         for k, v in d.items())
    return raw


def steps_of(run_dir: str) -> list[dict]:
    hist = json.load(open(os.path.join(run_dir, "debug-history.json")))
    msgs = hist["raw_model_messages"]
    steps = []
    for i, msg in enumerate(msgs):
        if msg.get("usage") is None:
            continue
        nxt = msgs[i + 1] if i + 1 < len(msgs) else None
        parts = (nxt or {}).get("parts", [])
        rets = [ts(p) for p in parts if p.get("part_kind") == "tool-return" and ts(p)]
        t0 = ts(msg)
        calls = [(c.get("tool_name"), str(c.get("args", ""))) for c in msg.get("parts", [])
                 if c.get("part_kind") == "tool-call"]
        calls = [(n, raw, args_text(n, raw)) for n, raw in calls]
        think_text = "".join(str(p.get("content", "")) for p in msg.get("parts", [])
                             if "think" in str(p.get("part_kind", "")) or "reason" in str(p.get("part_kind", "")))
        u = msg["usage"]
        out = u.get("output_tokens", 0)
        rea = (u.get("details") or {}).get("reasoning_tokens", 0)
        gen_exec = (min(rets) - t0) if rets and t0 else 0.0
        tool_span = (max(rets) - min(rets)) if len(rets) > 1 else 0.0
        steps.append({
            "idx": i, "t0": t0, "gen_exec": gen_exec, "tool_span": tool_span,
            "gen": max(gen_exec - tool_span, 0.0), "out": out, "reason": rea,
            "think": think_text,
            "calls": calls,
        })
    return steps


def phase_weights(step: dict) -> dict[str, float]:
    w: dict[str, float] = {}
    for name, _raw, text in step["calls"]:
        parts = segments(text) if name == "execute" else [(classify_call(name, text), max(len(text), 40))]
        for ph, n in parts:
            w[ph] = w.get(ph, 0.0) + n
    if not w:
        w[OTHER] = 1.0
    return w


def authored_bytes(step: dict) -> dict[str, int]:
    """Bytes the model typed into each artifact (write_file body / `cat > path << EOF`)."""
    out: dict[str, int] = {}
    for name, _raw, text in step["calls"]:
        targets: list[tuple[str, int]] = []
        if name == "write_file":
            path = _arg_path(text, "file_path")
            c, p = text.find("content: "), text.find("\nfile_path: ")
            body = len(text[c + 9:(p if c >= 0 and p > c else len(text))]) if c >= 0 else 0
            if path:
                targets.append((path, body))
        for m in HEREDOC_RX.finditer(text):
            head = text[max(0, m.start() - 400):m.start()]
            rm = None
            for rm in REDIRECT_RX.finditer(head):
                pass
            if rm:
                targets.append((rm.group(1), len(m.group(2))))
        for path, n in targets:
            out[_by_path(path) or OTHER] = out.get(_by_path(path) or OTHER, 0) + n
    return out


# ---------------------------------------------------------------- analysis
def calibrate(steps: list[dict]) -> dict:
    """Least squares gen_s ~ a*reason_tok + b*content_tok + c (ms/token + fixed)."""
    rows = [(s["reason"], max(s["out"] - s["reason"], 0), 1.0, s["gen"]) for s in steps]
    rows = [r for r in rows if r[0] + r[1] > 0]
    if len(rows) < 6:
        return {}
    import itertools
    n = 3
    A = [[sum(r[i] * r[j] for r in rows) for j in range(n)] + [sum(r[i] * r[3] for r in rows)]
         for i in range(n)]
    # gaussian elimination
    for i in range(n):
        piv = max(range(i, n), key=lambda k: abs(A[k][i]))
        A[i], A[piv] = A[piv], A[i]
        if abs(A[i][i]) < 1e-9:
            return {}
        for k in range(n):
            if k != i:
                f = A[k][i] / A[i][i]
                for j in range(i, n + 1):
                    A[k][j] -= f * A[i][j]
    coef = [A[i][n] / A[i][i] for i in range(n)]
    pred = [coef[0] * r[0] + coef[1] * r[1] + coef[2] for r in rows]
    obs = [r[3] for r in rows]
    mean = sum(obs) / len(obs)
    ss_tot = sum((o - mean) ** 2 for o in obs)
    ss_res = sum((o - p) ** 2 for o, p in zip(obs, pred))
    return dict(a_ms_per_reason=coef[0] * 1000, b_ms_per_content=coef[1] * 1000,
                fixed_s=coef[2], r2=1 - ss_res / ss_tot if ss_tot else 0.0, n=len(rows))


def analyse(run_dir: str) -> dict:
    steps = steps_of(run_dir)
    agg = {p: dict(gen=0.0, think=0.0, write=0.0, tool=0.0, out=0, reason=0, bytes=0)
           for p in PHASES}
    for s in steps:
        w = phase_weights(s)
        tot = sum(w.values())
        frac_reason = (s["reason"] / s["out"]) if s["out"] else 0.0
        think, write = s["gen"] * frac_reason, s["gen"] * (1 - frac_reason)
        for ph, weight in w.items():
            share = weight / tot
            a = agg[ph]
            a["gen"] += s["gen"] * share
            a["think"] += think * share
            a["write"] += write * share
            a["tool"] += s["tool_span"] * share
            a["out"] += round(s["out"] * share)
            a["reason"] += round(s["reason"] * share)
        for ph, nb in authored_bytes(s).items():
            agg[ph]["bytes"] += nb

    def load(name):
        p = os.path.join(run_dir, name)
        return json.load(open(p)) if os.path.exists(p) else {}

    timing, usage, run_json = load("timing.json"), load("usage.json"), load("run.json")
    server_s = (timing.get("total_latency_ms") or 0) / 1000
    gen = sum(s["gen"] for s in steps)
    tool = sum(s["tool_span"] for s in steps)
    cal = calibrate(steps)
    content_tok = sum(max(s["out"] - s["reason"], 0) for s in steps)
    typed_bytes = sum(len(t) for s in steps for _n, _r, t in s["calls"])
    bpt = (typed_bytes / content_tok) if content_tok else 0.0
    artifacts = {}
    if cal and bpt:
        for ph, a in agg.items():
            if a["bytes"]:
                artifacts[ph] = a["bytes"] / bpt * cal["b_ms_per_content"] / 1000
    return dict(dir=run_dir, tag=run_json.get("tag") or os.path.basename(run_dir.rstrip("/")),
                model=run_json.get("model"), steps=len(steps), server_s=server_s,
                gen_s=gen, tool_s=tool, overhead_s=max(server_s - gen - tool, 0.0),
                out=(usage.get("usage") or {}).get("output_tokens"),
                reason=(usage.get("usage") or {}).get("reasoning_tokens"),
                cal=cal, bytes_per_token=bpt, typed_bytes=typed_bytes,
                long_think=[s for s in steps
                            if s["out"] and s["reason"] / s["out"] >= THINK_DOMINANT
                            and s["gen"] >= THINK_LONG_S],
                decomp=dict(
                    reasoning_s=sum(x["reason"] for x in steps) * cal["a_ms_per_reason"] / 1000 if cal else 0,
                    content_s=sum(max(x["out"] - x["reason"], 0) for x in steps) * cal["b_ms_per_content"] / 1000 if cal else 0,
                    fixed_s=len(steps) * cal["fixed_s"] if cal else 0),
                artifact_write_s=artifacts, phases=agg, raw_steps=steps)


def fmt_table(res: dict | list[dict], rows: bool = False, artifacts: bool = False) -> str:
    lines = []
    for r in ([res] if isinstance(res, dict) else res):
        cal = r["cal"]
        lines.append(f"\n## {r['tag']}  ({r['model']})")
        lines.append(f"server {r['server_s']:.1f} s | 生成 {r['gen_s']:.1f} s "
                     f"({100*r['gen_s']/max(r['server_s'],1e-9):.0f}%) | 工具 {r['tool_s']:.1f} s "
                     f"| 其余(建线程/落盘/收尾) {r['overhead_s']:.1f} s | 步数 {r['steps']} "
                     f"| out {r['out']} / reasoning {r['reason']}")
        if cal:
            lines.append(f"标定（本次 run 回归，n={cal['n']}, R²={cal['r2']:.3f}）: "
                         f"reasoning {cal['a_ms_per_reason']:.2f} ms/tok, "
                         f"落笔 {cal['b_ms_per_content']:.2f} ms/tok, "
                         f"每步固定 {cal['fixed_s']:.2f} s；"
                         f"实测 {r['bytes_per_token']:.2f} 字节/tok")
        lt = r.get("long_think") or []
        if lt:
            lines.append(f"长思考步（reasoning ≥ {THINK_DOMINANT:.0%}out 且 ≥ {THINK_LONG_S:.0f} s）"
                         f"{len(lt)} 步，合计 {sum(x['gen'] for x in lt):.1f} s "
                         f"({100*sum(x['gen'] for x in lt)/max(r['server_s'],1e-9):.0f}%)")
        d = r.get("decomp") or {}
        if d:
            lines.append(f"全 run 分解: 思考 {d['reasoning_s']:.1f} s "
                         f"({100*d['reasoning_s']/max(r['server_s'],1e-9):.0f}%) + "
                         f"落笔(打字) {d['content_s']:.1f} s "
                         f"({100*d['content_s']/max(r['server_s'],1e-9):.0f}%) + "
                         f"每步固定开销 {d['fixed_s']:.1f} s "
                         f"({100*d['fixed_s']/max(r['server_s'],1e-9):.0f}%)，"
                         f"工具本身 {r['tool_s']:.1f} s "
                         f"({100*r['tool_s']/max(r['server_s'],1e-9):.1f}%)")
        lines.append("")
        lines.append("| 语义阶段 | 生成 s | 其中思考 | 其中落笔 | 工具 s | out tok | 写出的字节 | 占比 |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        tot = r["server_s"] or 1.0
        for ph in DISPLAY_ORDER:
            a = r["phases"][ph]
            if a["gen"] < 0.5 and a["tool"] < 0.5 and a["bytes"] == 0:
                continue
            lines.append(f"| {ph} | {a['gen']:.1f} | {a['think']:.1f} | {a['write']:.1f} | "
                         f"{a['tool']:.1f} | {a['out']} | {a['bytes']:,} | {100*a['gen']/tot:.0f}% |")
        lines.append(f"| **合计** | **{r['gen_s']:.1f}** | | | **{r['tool_s']:.1f}** | "
                     f"**{r['out']}** | "
                     f"**{sum(r['phases'][p]['bytes'] for p in PHASE_NAMES):,}** | "
                     f"**{100*r['gen_s']/tot:.0f}%** |")
        if artifacts and r["artifact_write_s"]:
            lines.append("")
            lines.append("| 产物（按字节标定的纯落笔时间） | 字节 | 估算落笔 s |")
            lines.append("|---|---:|---:|")
            for ph, sec in sorted(r["artifact_write_s"].items(), key=lambda kv: -kv[1]):
                lines.append(f"| {ph} | {r['phases'][ph]['bytes']:,} | {sec:.1f} |")
        if rows:
            lines.append("")
            lines.append("| step | gen s | think | write | tool s | out | reason | 阶段(权重) | calls |")
            lines.append("|---:|---:|---:|---:|---:|---:|---:|---|---|")
            for s in r["raw_steps"]:
                fr = (s["reason"] / s["out"]) if s["out"] else 0
                w = phase_weights(s)
                phs = " + ".join(f"{k.split()[0]}:{int(v)}" for k, v in
                                 sorted(w.items(), key=lambda kv: -kv[1]))
                calls = " ; ".join(f"{n}({len(t)}B)" for n, _rw, t in s["calls"]) or "-"
                lines.append(f"| {s['idx']} | {s['gen']:.1f} | {s['gen']*fr:.1f} | "
                             f"{s['gen']*(1-fr):.1f} | {s['tool_span']:.1f} | {s['out']} | "
                             f"{s['reason']} | {phs} | {calls} |")
    return "\n".join(lines)


def fmt_thinking(r: dict) -> str:
    out = [f"\n### 长思考步 —— {r['tag']}", "",
           "| step | gen s | reasoning 占比 | 名义动作 | thinking 开头 |", "|---:|---:|---:|---|---|"]
    for s in r.get("long_think", []):
        w = phase_weights(s)
        ph = max(w, key=w.get) if w else OTHER
        head = " ".join(s["think"].split())[:220].replace("|", "\\|")
        args = " ; ".join(n for n, _r, _t in s["calls"]) or "-"
        out.append(f"| {s['idx']} | {s['gen']:.1f} | {100*s['reason']/max(s['out'],1):.0f}% | "
                   f"{args} → {ph.split()[0]} | {head}… |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--rows", action="store_true", help="dump per-step rows")
    ap.add_argument("--artifacts", action="store_true", help="also show the byte-based view")
    ap.add_argument("--thinking", action="store_true",
                    help="show the long-thinking steps with a thinking excerpt")
    args = ap.parse_args()
    results = []
    for d in args.runs:
        res = analyse(d)
        results.append(res)
        print(fmt_table(res, rows=args.rows, artifacts=args.artifacts))
        if args.thinking:
            print(fmt_thinking(res))
    if args.json_out:
        keep = [{k: v for k, v in r.items() if k != "raw_steps"} for r in results]
        json.dump(keep, open(args.json_out, "w"), ensure_ascii=False, indent=1)
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
