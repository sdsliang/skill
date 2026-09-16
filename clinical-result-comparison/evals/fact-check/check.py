#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline fact checklist scorer for the multi-clinical-result-comparison Skill.

Reads a ToolSmith run directory (as produced by `toolsmith-publish run`) and scores it
against a human-authored fact checklist derived from the frozen tool records in
`records/`.  Gives the autoresearch-style keep/discard loop the scalar it otherwise
lacks (`facts_ok/facts_total`), while keeping every item traceable to a record field.

Usage:
    python3 check.py --run ~/.local/state/toolsmith-runs/<ts>-<tag> --scenario a
    python3 check.py --run ... --scenario b --json /tmp/score-b.json -v

Exit codes: 0 = all fail-severity items PASS, 3 = at least one FAIL, 4 = input unusable.

Surfaces
--------
report     artifacts/output/report.md
citations  artifacts/output/citations.json
charts     artifacts/visualizations/*.json
answer     assistant text parts of messages.json  (the chat reply shown to the user)
transcript transcript.md (whole run, incl. tool calls)
any        report + answer

Anchors
-------
`{{ref_n}}` markers partition the report into blocks (one markdown line / table row each).
`present` patterns must land in a block citing the anchor; `absent` patterns must not.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

MINUS = "\u2212"          # −
EN_DASH = "\u2013"        # –
FW_LT = "\uff1c"          # ＜
FW_PCT = "\uff05"         # ％
NBSP = "\u00a0"


def norm(s: str) -> str:
    return (s.replace(MINUS, "-").replace(EN_DASH, "-").replace(FW_LT, "<")
             .replace(FW_PCT, "%").replace(NBSP, " "))


# --------------------------------------------------------------------------- surfaces

def load_surfaces(run_dir: str) -> dict:
    art = os.path.join(run_dir, "artifacts")
    if not os.path.isdir(art):
        art = os.path.join(run_dir, "artifacts-unpacked")
    out = {"run_dir": run_dir, "artifacts_dir": art if os.path.isdir(art) else None,
           "report": "", "citations": None, "charts": {}, "answer": "", "transcript": "",
           "errors": []}
    rp = os.path.join(art, "output", "report.md")
    if os.path.isfile(rp):
        out["report"] = norm(open(rp, encoding="utf-8", errors="replace").read())
    cp = os.path.join(art, "output", "citations.json")
    if os.path.isfile(cp):
        try:
            out["citations"] = json.load(open(cp, encoding="utf-8"))
        except Exception as e:                                    # noqa: BLE001
            out["errors"].append(f"citations.json unparsable: {e}")
    for p in sorted(glob.glob(os.path.join(art, "visualizations", "*.json"))):
        try:
            out["charts"][os.path.basename(p)] = json.load(open(p, encoding="utf-8"))
        except Exception as e:                                    # noqa: BLE001
            out["errors"].append(f"{os.path.basename(p)} unparsable: {e}")
    mp = os.path.join(run_dir, "messages.json")
    if os.path.isfile(mp):
        try:
            msgs = json.load(open(mp, encoding="utf-8"))
            texts = []
            for m in msgs if isinstance(msgs, list) else []:
                if not isinstance(m, dict) or m.get("role") != "assistant":
                    continue
                for part in m.get("parts") or []:
                    if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                        texts.append(part["text"])
            out["answer"] = norm("\n\n".join(texts))
        except Exception as e:                                    # noqa: BLE001
            out["errors"].append(f"messages.json unparsable: {e}")
    else:
        # v1 (SSE) runs have no messages.json — rebuild both surfaces from debug history
        dp = os.path.join(run_dir, "debug-history.json")
        if os.path.isfile(dp):
            texts, calls = [], []

            def walk(o):
                if isinstance(o, dict):
                    k = o.get("part_kind")
                    if k == "text":
                        c = o.get("content")
                        if isinstance(c, dict):
                            c = c.get("text") or c.get("content")
                        if c and str(c).strip():
                            texts.append(str(c))
                    elif k in ("tool-call", "user-prompt"):
                        bits = [str(o.get("tool_name") or ""), str(o.get("content") or ""),
                                str(o.get("args") or "")]
                        line = " ".join(b for b in bits if b)
                        if line.strip():
                            calls.append(line)
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)

            try:
                walk(json.load(open(dp, encoding="utf-8")))
                out["answer"] = norm("\n\n".join(dict.fromkeys(texts)))
                out["transcript"] = norm("\n".join(dict.fromkeys(calls)))
                out["errors"].append("surfaces rebuilt from debug-history.json (v1 run)")
            except Exception as e:                                # noqa: BLE001
                out["errors"].append(f"debug-history.json unparsable: {e}")
    tp = os.path.join(run_dir, "transcript.md")
    if os.path.isfile(tp):
        out["transcript"] = norm(open(tp, encoding="utf-8", errors="replace").read())
    return out


def surface_text(sv: dict, name: str) -> str:
    if name == "report":
        return sv["report"]
    if name == "answer":
        return sv["answer"]
    if name == "transcript":
        return sv["transcript"]
    if name == "any":
        return sv["report"] + "\n\n" + sv["answer"]
    if name == "citations":
        return json.dumps(sv["citations"], ensure_ascii=False) if sv["citations"] else ""
    if name == "charts":
        return json.dumps(sv["charts"], ensure_ascii=False)
    return ""


# --------------------------------------------------------------------------- blocks

def blocks(text: str) -> list:
    """Split into blocks: one line each, table rows individually, blank lines dropped."""
    out, pending = [], []
    for line in text.splitlines():
        if not line.strip():
            if pending:
                out.append("\n".join(pending))
                pending = []
            continue
        if line.lstrip().startswith("|") or re.match(r"^\s*(#{1,6} |[-*+] |> |\d+\. )", line):
            if pending:
                out.append("\n".join(pending))
                pending = []
            out.append(line)
        else:
            pending.append(line)
    if pending:
        out.append("\n".join(pending))
    return out


def refs_in(block: str) -> set:
    return {"ref_" + n for n in re.findall(r"\{\{ref_(\d+)\}\}", block)}


def sentences(block: str) -> list:
    """Sentence-ish units inside a block: a mixed-mode line must still attribute per claim.

    Split points are terminators **at bracket depth 0** only.  A `；` that separates clauses
    inside a parenthetical (e.g. `（-70.5% 至 -101.1%，第 36 周{{ref_2}}；对应 -13.9%，第 16 周{{ref_1}}）`)
    must not cut the unit in two: each half would then lose the other record's marker and every
    number in it would look misattributed (false FAIL on a correct report — seen on the P8 run).
    """
    out, buf, depth = [], [], 0
    for ch in block:
        if ch in "（(［[【":
            depth += 1
        elif ch in "）)］]】":
            depth = max(0, depth - 1)
        buf.append(ch)
        if depth == 0 and ch in "。；;":
            out.append("".join(buf))
            buf = []
    if "".join(buf).strip():
        out.append("".join(buf))
    return [s for s in out if s.strip()]


def units(block: str) -> list:
    """Attribution units = (text, refs) inside a block.

    Prose splits per sentence (a scope line naming both trials must still attribute
    each claim).  A markdown table row splits per cell, because citations there are
    per cell; a cell without a marker inherits the row's markers (tables in this
    skill carry the record's marker in the row's first cell).
    """
    if block.lstrip().startswith("|"):
        row_refs = refs_in(block)
        return [(c, refs_in(c) or row_refs) for c in block.split("|") if c.strip()]
    return [(s, refs_in(s)) for s in sentences(block)]


# --------------------------------------------------------------------------- record lookup

def record_of(fixture: dict, esid: str) -> dict:
    for rec in fixture["response"]["result"]["data"]:
        if rec.get("clinical_result_extra_esid") == esid:
            return rec
    raise KeyError(f"esid {esid} not present in fixture")


# --------------------------------------------------------------------------- ops

def op_artifact_present(files: dict, spec: dict) -> tuple:
    missing = [p for p, ok in files.items() if not ok]
    return (not missing, f"missing={missing}" if missing else "all present")


def op_artifact_absent(files: dict, spec: dict) -> tuple:
    scope = spec.get("files") or list(files)
    present = [p for p in scope if files.get(p)]
    return (not present, f"unexpected files={present}" if present else f"nothing written out of {scope}")


def op_glob_count(sv: dict, spec: dict) -> tuple:
    art = sv["artifacts_dir"] or ""
    pat = os.path.join(art, spec["pattern"])
    got = sorted(os.path.basename(p) for p in glob.glob(pat))
    want = sorted(spec["expect"])
    return (got == want, f"got={got} want={want}")


def op_citations_keys_exact(sv: dict, spec: dict) -> tuple:
    c = sv["citations"]
    if not isinstance(c, dict):
        return False, "citations.json missing or not an object"
    got = sorted(c.keys())
    want = sorted(spec["keys"])
    return (got == want, f"got={got} want={want}")


def op_citations_entry_key_set(sv: dict, spec: dict) -> tuple:
    c = sv["citations"] or {}
    bad = []
    for ref in spec["refs"]:
        e = c.get(ref)
        if not isinstance(e, dict):
            bad.append(f"{ref}: missing")
            continue
        got = sorted(e.keys())
        if got != sorted(spec["keys"]):
            bad.append(f"{ref}: {got}")
        elif any(not str(e[k]).strip() for k in spec["keys"]):
            bad.append(f"{ref}: empty value")
    return (not bad, "; ".join(bad) if bad else f"{len(spec['refs'])} entries OK")


def op_citations_matches_record(sv: dict, spec: dict, ctx: dict) -> tuple:
    rec = record_of(ctx["fixture"], spec["esid"])
    e = (sv["citations"] or {}).get(spec["ref"])
    if not isinstance(e, dict):
        return False, f"{spec['ref']} missing"
    bad = []
    t = rec.get(spec["map"]["title"])
    if e.get("title") != t:
        bad.append(f"title != record ({str(e.get('title'))[:60]!r} vs {str(t)[:60]!r})")
    link = rec.get(spec["map"]["link"])
    if e.get("link") != link:
        bad.append(f"link != record ({e.get('link')!r} vs {link!r})")
    raw = rec.get(spec["map"]["date"]) or ""
    want_date = str(raw)[:10]
    if e.get("paper_release_time_str") != want_date:
        bad.append(f"date != {want_date!r} (record={raw!r})")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("paper_release_time_str") or "")):
        bad.append("date not YYYY-MM-DD")
    return (not bad, "; ".join(bad) if bad else f"{spec['ref']} == record {spec['esid']}")


def op_citations_distinct(sv: dict, spec: dict) -> tuple:
    c = sv["citations"] or {}
    vals = [str((c.get(r) or {}).get(spec["field"], "")) for r in spec["refs"]]
    ok = len(vals) == len(set(vals)) and all(vals)
    return (ok, f"{spec['field']}s distinct={ok}")


def op_chart_envelope(sv: dict, spec: dict) -> tuple:
    ch = sv["charts"].get(spec["file"])
    if not isinstance(ch, dict):
        return False, f"{spec['file']} missing"
    bad = []
    exp = spec["expect"]
    if ch.get("id") != exp["id"]:
        bad.append(f"id={ch.get('id')!r}")
    tpl = str(ch.get("iframe_template") or "")
    if not re.match(exp["iframe_template_regex"], tpl):
        bad.append(f"iframe_template={tpl[:60]!r} does not match {exp['iframe_template_regex']}")
    opt = ch.get("option")
    if not isinstance(opt, dict):
        bad.append("option missing")
    else:
        for k, v in exp["option"].items():
            if opt.get(k) != v:
                bad.append(f"option.{k}={opt.get(k)!r} want {v!r}")
        data = opt.get("data") or []
        if len(data) != exp["data_len"]:
            bad.append(f"option.data len={len(data)} want {exp['data_len']}")
        for row in data:
            if not str(row.get("label") or "").strip():
                bad.append(f"empty label in data row {row}")
        for k in ("title",):
            if not str(opt.get(k) or "").strip():
                bad.append(f"option.{k} empty")
    return (not bad, "; ".join(bad) if bad else "envelope + option OK")


def op_chart_values(sv: dict, spec: dict) -> tuple:
    ch = sv["charts"].get(spec["file"])
    if not isinstance(ch, dict):
        return False, f"{spec['file']} missing"
    got = sorted(round(float(r["value"]), 3) for r in (ch.get("option") or {}).get("data") or [])
    want = sorted(round(float(v), 3) for v in spec["values"])
    return (got == want, f"got={got} want={want}")


SHAPE_OPS = {
    "artifact_present": op_artifact_present,
    "artifact_absent": op_artifact_absent,
    "glob_count": op_glob_count,
    "citations_keys_exact": op_citations_keys_exact,
    "citations_entry_key_set": op_citations_entry_key_set,
    "citations_matches_record": op_citations_matches_record,
    "citations_distinct": op_citations_distinct,
    "chart_envelope": op_chart_envelope,
    "chart_values": op_chart_values,
}
NO_CTX_OPS = {k: v for k, v in SHAPE_OPS.items()
               if k not in ("citations_matches_record",)}
FILES_OPS = {"artifact_present", "artifact_absent"}


# --------------------------------------------------------------------------- text items

def eval_present(item: dict, sv: dict) -> tuple:
    text = surface_text(sv, item.get("surface", "report"))
    if not text:
        return False, f"surface {item.get('surface', 'report')} is empty"
    anchors = item.get("anchors") or []
    min_count = item.get("min_count", 1)
    bad = []
    for pat in item["patterns"]:
        rx = re.compile(pat)
        if anchors:
            hits = sum(1 for b in blocks(text)
                       if refs_in(b) & set(anchors) and rx.search(b))
        else:
            hits = len(rx.findall(text))
        if hits < min_count:
            where = f" within blocks citing {anchors}" if anchors else ""
            bad.append(f"{pat!r}: {hits} hit(s), need >= {min_count}{where}")
    return (not bad, "; ".join(bad) if bad else f"{len(item['patterns'])} pattern(s) matched")


def eval_absent(item: dict, sv: dict) -> tuple:
    text = surface_text(sv, item.get("surface", "report"))
    anchors = item.get("anchors") or []
    bad = []
    for pat in item["patterns"]:
        rx = re.compile(pat)
        if anchors:
            hit = [b for b in blocks(text) if refs_in(b) & set(anchors) and rx.search(b)]
            if hit:
                bad.append(f"{pat!r} found in anchored block: {hit[0][:80]!r}")
        else:
            m = rx.search(text)
            if m:
                bad.append(f"{pat!r} found: {text[max(0, m.start() - 40):m.end() + 40]!r}")
    return (not bad, "; ".join(bad) if bad else f"{len(item['patterns'])} pattern(s) absent")


def eval_line(item: dict, sv: dict) -> tuple:
    """All patterns must co-occur on one line matching line_regex (e.g. the H1 title)."""
    text = surface_text(sv, item.get("surface", "report"))
    if not text:
        return False, f"surface {item.get('surface', 'report')} is empty"
    sel = [l for l in text.splitlines() if re.search(item["line_regex"], l)]
    if not sel:
        return False, f"no line matches {item['line_regex']!r}"
    for l in sel:
        miss = [p for p in item["patterns"] if not re.search(p, l)]
        if not miss:
            return True, f"{item['line_regex']!r} line carries all {len(item['patterns'])} pattern(s)"
    return False, (f"none of {len(sel)} matching line(s) carries all patterns; "
                   f"first line missing {[p for p in item['patterns'] if not re.search(p, sel[0])]}"
                   f" -- {sel[0][:90]!r}")


def eval_attribution(item: dict, sv: dict) -> tuple:
    """Every claim that cites anything must cite the owner of each token it names.

    Granularity is the sentence, not the line: a scope line that lists both trials
    legitimately names both drugs, so a line-level rule cannot see a drug name that
    got attached to the wrong record.
    """
    text = sv["report"]
    if not text:
        return False, "report surface is empty"
    bad, checked = [], 0
    for b in blocks(text):
        for sent, rs in units(b):
            if not rs:
                continue
            for pair in item["pairs"]:
                if re.search(pair["token"], sent):
                    checked += 1
                    if pair["owner"] not in rs:
                        bad.append(f"{pair['token']!r} in unit citing {sorted(rs)} "
                                   f"(owner {pair['owner']}): {sent.strip()[:70]!r}")
    return (not bad, "; ".join(bad) if bad else f"{checked} token/unit pairings correctly attributed")


# --------------------------------------------------------------------------- driver

def run_check(args) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    cfile = os.path.join(here, f"scenario-{args.scenario}.facts.json")
    rfile = os.path.join(here, "records", f"scenario-{args.scenario}.records.json")
    for p in (cfile, rfile):
        if not os.path.isfile(p):
            print(f"FATAL: missing {p}", file=sys.stderr)
            return 4
    check = json.load(open(cfile, encoding="utf-8"))
    fixture = json.load(open(rfile, encoding="utf-8"))
    sv = load_surfaces(os.path.expanduser(args.run))
    if not sv["artifacts_dir"] and not sv["answer"]:
        print(f"FATAL: {args.run} has neither artifacts/ nor messages.json", file=sys.stderr)
        return 4

    files = {
        "output/report.md": bool(sv["report"]),
        "output/citations.json": isinstance(sv["citations"], dict),
    }
    ctx = {"fixture": fixture, "check": check}
    results, n_fail, n_warn = [], 0, 0
    for item in check["items"]:
        sev = item.get("severity", "fail")
        kind = item["kind"]
        if kind == "shape":
            op = SHAPE_OPS.get(item["op"])
            if op is None:
                ok, detail = False, f"unknown op {item['op']}"
            elif item["op"] in NO_CTX_OPS:
                ok, detail = op(files if item["op"] in FILES_OPS else sv, item)
            else:
                ok, detail = op(sv, item, ctx)
        elif kind == "present":
            ok, detail = eval_present(item, sv)
        elif kind == "absent":
            ok, detail = eval_absent(item, sv)
        elif kind == "attribution":
            ok, detail = eval_attribution(item, sv)
        elif kind == "line":
            ok, detail = eval_line(item, sv)
        else:
            ok, detail = False, f"unknown kind {kind}"
        if not ok:
            if sev == "warn":
                n_warn += 1
            else:
                n_fail += 1
        results.append({"id": item["id"], "kind": kind, "severity": sev, "ok": ok,
                        "detail": detail, "why": item.get("rationale", ""),
                        "evidence": item.get("evidence", "")})
        if args.verbose or not ok:
            tag = "PASS" if ok else ("WARN" if sev == "warn" else "FAIL")
            print(f"[{tag:4}] {item['id']:26} {detail}")
    total = sum(1 for r in results if r["severity"] == "fail")
    warn_total = sum(1 for r in results if r["severity"] == "warn")
    ok_total = sum(1 for r in results if r["severity"] == "fail" and r["ok"])
    ok_warn = sum(1 for r in results if r["severity"] == "warn" and r["ok"])
    verdict = "PASS" if n_fail == 0 else "FAIL"
    print(f"SCORE scenario={check['scenario']} facts {ok_total}/{total} "
          f"warn {ok_warn}/{warn_total} -> {verdict}")
    for e in sv["errors"]:
        print(f"[WARN] surface: {e}")
    if args.json:
        json.dump({"scenario": check["scenario"], "run": os.path.expanduser(args.run),
                   "facts_ok": ok_total, "facts_total": total,
                   "warn_ok": ok_warn, "warn_total": warn_total,
                   "verdict": verdict, "items": results},
                  open(os.path.expanduser(args.json), "w"), ensure_ascii=False, indent=1)
        print(f"json  -> {args.json}")
    return 0 if n_fail == 0 else 3


def main() -> int:
    ap = argparse.ArgumentParser(description="offline fact-checklist scorer")
    ap.add_argument("--run", required=True, help="run dir, e.g. ~/.local/state/toolsmith-runs/<ts>-<tag>")
    ap.add_argument("--scenario", required=True, choices=["a", "b"])
    ap.add_argument("--json", help="write machine-readable score to this path")
    ap.add_argument("-v", "--verbose", action="store_true", help="print PASS lines too")
    return run_check(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
