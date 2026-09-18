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

Optional artefacts
------------------
The quantitative main chart is **optional** per `chart-templates.md:91`: a legal run may
emit `visualizations/evidence-timeline.json` only, or no chart at all.  Items that inspect
one specific chart therefore carry `"optional_when_absent": true` (they police the chart
*when it exists* instead of demanding it), and the no-chart branch is policed separately
by `op=chart_or_reason` — so "emit nothing and explain nothing" cannot pass for free.

Anchors
-------
`{{ref_n}}` markers partition the report into blocks (one markdown line / table row each).
`present` patterns must land in a block citing the anchor; `absent` patterns must not.
"""

from __future__ import annotations

import argparse
import fnmatch
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


# A citation link may carry the full-text body instead of the record's own link, but only in the two
# whitelisted forms from `references/input-contract.md` (*Citation link follows the analysis depth*).
FT_CITE = (re.compile(r"^https://pmc\.ncbi\.nlm\.nih\.gov/articles/PMC\d+/?$"),
           re.compile(r"^https://www\.ebi\.ac\.uk/europepmc/webservices/rest/PMC\d+/fullTextXML$"))


def is_fulltext_citation_link(link: str) -> bool:
    return any(p.match(str(link or "")) for p in FT_CITE)


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
    upgraded = (e.get("link") != link)
    if upgraded and not is_fulltext_citation_link(e.get("link")):
        bad.append(f"link != record and not a whitelisted full-text link ({e.get('link')!r} vs {link!r})")
    raw = rec.get(spec["map"]["date"]) or ""
    want_date = str(raw)[:10]
    if e.get("paper_release_time_str") != want_date:
        bad.append(f"date != {want_date!r} (record={raw!r})")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("paper_release_time_str") or "")):
        bad.append("date not YYYY-MM-DD")
    if bad:
        return False, "; ".join(bad)
    if upgraded:
        return True, f"{spec['ref']} == record {spec['esid']} (link carries the full text)"
    return True, f"{spec['ref']} == record {spec['esid']}"


def op_citations_distinct(sv: dict, spec: dict) -> tuple:
    c = sv["citations"] or {}
    vals = [str((c.get(r) or {}).get(spec["field"], "")) for r in spec["refs"]]
    ok = len(vals) == len(set(vals)) and all(vals)
    return (ok, f"{spec['field']}s distinct={ok}")


def op_chart_envelope(sv: dict, spec: dict) -> tuple:
    ch = sv["charts"].get(spec["file"])
    if not isinstance(ch, dict):
        if spec.get("optional_when_absent"):
            return True, (f"{spec['file']} absent — allowed (quantitative main chart is "
                          f"optional per chart-templates.md:91); the reason is asserted by "
                          f"A-S2b-chart-or-reason")
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


def _chart_floats(sv: dict, name: str) -> list | None:
    ch = sv["charts"].get(name)
    if not isinstance(ch, dict):
        return None
    return [round(float(r["value"]), 3) for r in (ch.get("option") or {}).get("data") or []]


def op_chart_values(sv: dict, spec: dict) -> tuple:
    """Charted magnitudes must equal the record's, sign aside.

    2026-09-18 (user ruling): `-70.5` and `降幅 70.5%` are equally acceptable renderings —
    the convention is free, so the comparison here is sign-agnostic and the **consistency**
    requirement lives in A-S10-sign-convention-consistent.  Digits are still compared exactly:
    a wrong magnitude fails here under either convention (M10).
    """
    got = _chart_floats(sv, spec["file"])
    if got is None:
        if spec.get("optional_when_absent"):
            return True, (f"{spec['file']} absent — allowed (see A-S2b-chart-or-reason)")
        return False, f"{spec['file']} missing"
    g, w = sorted(abs(x) for x in got), sorted(abs(round(float(v), 3)) for v in spec["values"])
    return (g == w, f"|got|={g} |want|={w} (raw got={sorted(got)})")


def _form_of(text: str, value: float) -> str:
    """How `value` is rendered in `text`: 'signed', 'unsigned' or 'absent'."""
    t = norm(text)
    lit = f"{abs(round(float(value), 3)):g}".replace(".", r"\.")
    if re.search(rf"(?<![\d.])-\s*{lit}(?![\d])", t):
        return "signed"
    if re.search(rf"(?<![\d.\-]){lit}(?![\d])", t):
        return "unsigned"
    return "absent"


def op_sign_convention_consistent(sv: dict, spec: dict) -> tuple:
    """One deliverable, one sign convention — the report and its chart must agree.

    The user ruled (2026-09-18) that `−13.9` and `降幅 13.9%` are both fine, "只要自洽".
    So the convention is not pinned; what must not happen is the report dropping the sign
    while its chart keeps it (or the reverse): a reader then cannot tell whether the chart's
    `-70.5` is the same quantity as the prose's `70.5`.  Only the charted magnitudes are
    inspected — a signed confidence interval (`95% CI -19.3～-8.5`) next to an unsigned
    point estimate (`降低 13.9%`) is the normal, self-consistent rendering, not a mix.
    Direction *wording* is asserted under neither convention (a signed report saying
    `升高 −13.9%` also passes today), so allowing magnitudes costs no coverage.
    """
    vals = [float(v) for v in spec["values"]]
    got = _chart_floats(sv, spec.get("file", ""))
    if got is None:
        return True, f"{spec.get('file')} absent — convention not displayed (see A-S2b)"
    ch = sv["charts"].get(spec["file"]) or {}
    c_forms = set()
    for row, v in zip((ch.get("option") or {}).get("data") or [], vals):
        c_forms.add(_form_of(json.dumps(row.get("value")), v))
    r_forms = {_form_of(sv["report"], v) for v in vals}
    c_signed, r_signed = "signed" in c_forms, "signed" in r_forms
    if c_signed != r_signed:
        return False, (f"report renders the endpoints "
                       f"{'signed' if r_signed else 'unsigned'} but the chart "
                       f"{'signed' if c_signed else 'unsigned'} "
                       f"(report forms={sorted(r_forms)}, chart forms={sorted(c_forms)}) "
                       f"— one deliverable, one convention")
    if "absent" in r_forms or "absent" in c_forms:
        return True, (f"convention consistent ({'signed' if r_signed else 'unsigned'}); "
                      f"some value absent from a surface — coverage is A-C4/A-C5's job")
    return True, f"one convention throughout: {'signed' if r_signed else 'unsigned'} magnitudes / chart"


def _chart_names(sv: dict, pattern: str) -> list:
    """Chart files (basenames) matching `pattern`, which may be bare (`endpoint-bar-*.json`)
    or already scoped (`visualizations/*.json`).  All charts live under artifacts/visualizations."""
    art = sv["artifacts_dir"] or ""
    pat = pattern if "/" in pattern else os.path.join("visualizations", pattern)
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(art, pat)))


def op_chart_set_allowed(sv: dict, spec: dict) -> tuple:
    """Every emitted chart must be a legal file name; forbidden kinds must not appear;
    the number of quantitative charts must not exceed the rule's cap.

    Deliberately NOT an exact expected set: the quantitative main chart is optional
    (chart-templates.md:91), so "no chart at all" is legal here and is policed by
    A-S2b-chart-or-reason instead.
    """
    got = _chart_names(sv, spec.get("pattern", "visualizations/*.json"))
    bad = []
    for name in got:
        if not any(fnmatch.fnmatch(name, g) for g in spec["allowed"]):
            bad.append(f"illegal chart file {name!r} (allowed: {spec['allowed']})")
    for name in spec.get("forbidden", []):
        if name in got:
            bad.append(f"forbidden chart {name!r} present ({spec.get('forbidden_why', 'rule')})")
    quants = [n for n in got if any(fnmatch.fnmatch(n, g) for g in spec.get("quant_globs", []))]
    cap = spec.get("max_quant", 1)
    if len(quants) > cap:
        bad.append(f"{len(quants)} quantitative charts {quants} > cap {cap}")
    return (not bad, "; ".join(bad) if bad else f"charts={got} quants={quants} (cap {cap}) OK")


def op_chart_or_reason(sv: dict, spec: dict) -> tuple:
    """If no quantitative chart was emitted, the report must SAY SO and give a reason.

    This is the counterpart to the optional chart: without it, "emit nothing and
    explain nothing" would pass for free.  The explicit no-chart statement is
    *required* (a cross-trial report mentions `跨试验` / `时点不同` all the time, so a
    supporting-reasons-only check leaks), and at least one substantive reason must
    accompany it.
    """
    quants = []
    for g in spec["quant_globs"]:
        quants += _chart_names(sv, g)
    if quants:
        return True, f"quantitative chart present: {sorted(quants)}"
    text = surface_text(sv, spec.get("surface", "report"))
    if not text:
        return False, "no quantitative chart AND no report text to state the reason"
    req = [g for g in spec["required_groups"] if re.search(g, text)]
    sup = [g for g in spec["supporting_groups"] if re.search(g, text)]
    need_sup = spec.get("min_supporting", 1)
    ok = len(req) == len(spec["required_groups"]) and len(sup) >= need_sup
    return (ok,
            f"no quantitative chart; explicit no-chart statement {len(req)}/"
            f"{len(spec['required_groups'])}; supporting reason groups {len(sup)}/"
            f"{len(spec['supporting_groups'])} (need {need_sup}): {sup}")


def op_no_verbatim_copy(sv: dict, spec: dict) -> tuple:
    """No long verbatim run from a fetched original source may appear in the report.

    The original-source rule lets the Skill read publisher/registry text, so the
    copyright-and-style guard has to be mechanical: whatever text was fetched into
    `/workspace/sources/` (archived with the run) must not reappear in the report as
    a run of `min_run` consecutive characters.  Whitespace is stripped on both sides
    because the report re-flows text.  When nothing was fetched the check is not
    triggered and passes with a note, so a record set without a reachable original
    is never punished twice.
    """
    art = sv.get("artifacts_dir") or ""
    n = int(spec.get("min_run", 60))
    step = max(10, n // 3)
    srcs = [p for p in sorted(glob.glob(os.path.join(art, "sources", "**", "*"), recursive=True))
            if os.path.isfile(p) and os.path.getsize(p) < 5_000_000]
    if not srcs:
        return True, "no fetched original archived under sources/ (check not triggered)"
    rep = re.sub(r"\s+", "", sv["report"] or "")
    if not rep:
        return False, "report surface is empty"
    hits = []
    for p in srcs:
        try:
            # norm() is what the report surface was put through, so the archived source has to
            # be aligned the same way (Unicode minus, full-width percent, NBSP) before comparing.
            t = re.sub(r"\s+", "", norm(open(p, encoding="utf-8", errors="replace").read()))
        except Exception:                                          # noqa: BLE001
            continue
        for i in range(0, max(0, len(t) - n), step):
            frag = t[i:i + n]
            if frag and frag in rep:
                hits.append(f"{os.path.basename(p)}: {frag[:60]!r}")
                break
    if hits:
        return False, f"verbatim run >= {n} chars copied into the report: {hits[:3]}"
    return True, f"{len(srcs)} archived source file(s), no verbatim run >= {n} chars in the report"


def op_original_check_names_class(sv: dict, spec: dict) -> tuple:
    """The `原文核对：` line must say *how* each record was re-checked and name its source class.

    `A-P1` only proves the line exists and carries a count — an empty shell such as
    `原文核对：2/2 条已复核` would sail through while hiding that nothing was actually
    re-checked and that one of the records is a press release whose original is the pulled
    body itself.  So the line has to name a retrieval route (PMID / DOI / registration id /
    registry API) *and* classify the records (esid source class or an explicit reason class).
    """
    route = spec.get("route_regex") or (r"PMID|DOI|doi|注册号|登记号|NCT|api|API|PMC\d|PMC|全文|库内正文|库内即原文|未取")
    cls = spec.get("class_regex") or (
        r"src\s*=\s*\d|来源\s*类|来源[:：]\s*\d|新闻稿|通稿|会议|登记平台|SEC|补录|库内正文|库内即原文"
        r"|未复核|不可复核|抓取受限|无登记号|该来源不公开|无 \`?pmcid\`?|非 OA")
    lines = [ln for ln in (sv["report"] or "").splitlines() if "原文核对" in ln]
    if not lines:
        return True, "no 原文核对 line (A-P1 owns that failure; not reported twice)"
    line = lines[0]
    miss = []
    if not re.search(route, line):
        miss.append("route(PMID/DOI/登记号/registry API/PMC 全文/库内正文即原文)")
    if not re.search(cls, line):
        miss.append("source class or reason class")
    if miss:
        return False, f"原文核对 line misses {' + '.join(miss)}: {line[:150]!r}"
    return True, f"原文核对 line names route and source class: {line[:110]!r}"


def op_fulltext_fetch_is_named(sv: dict, spec: dict) -> tuple:
    """A full text that was actually retrieved must be declared in the coverage line.

    `A-P4` can still be satisfied by a line that names only the *abstract* route, so a run
    could pull 99 KB of PMC full text into `sources/` and never tell the reader that the
    check went beyond the abstract — or, worse, claim a full-text check it did not do. This
    op looks at what is archived under `sources/` and requires the `原文核对：` line to carry
    the matching token: `PMC<digits>` (or the word 全文) when a full-text body was archived.
    Nothing archived ⇒ not triggered, passes with a note (a run that legitimately fetched
    no full text must not be punished).
    """
    art = sv.get("artifacts_dir") or ""
    srcs = [p for p in sorted(glob.glob(os.path.join(art, "sources", "**", "*"), recursive=True))
            if os.path.isfile(p) and os.path.getsize(p) < 20_000_000]
    ft = []
    for p in srcs:
        name = os.path.basename(p).lower()
        if "fulltext" in name or "full-text" in name or re.search(r"pmc\d", name):
            ft.append(p); continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                head = fh.read(4000)
        except OSError:
            continue
        if re.search(r"<article|<sec\b|<body\b", head):
            ft.append(p)
    if not ft:
        return True, "no full-text body archived under sources/ (check not triggered)"
    lines = [ln for ln in (sv["report"] or "").splitlines() if "原文核对" in ln]
    blob = "\n".join(lines) if lines else ""
    if not blob:
        return True, "full text archived but no 原文核对 line (A-P1 owns that failure)"
    if re.search(r"PMC\s*\d|全文", blob):
        return True, f"full text archived ({len(ft)} file(s)) and declared"
    return False, (f"{len(ft)} full-text file(s) archived under sources/ but the 原文核对 line "
                   f"names neither PMC<id> nor 全文 — the reader cannot tell a full-text check "
                   f"from an abstract-only check")


def archived_fulltexts(art: str) -> list:
    """Full-text bodies archived under `sources/` (same detection as `op_fulltext_fetch_is_named`)."""
    srcs = [p for p in sorted(glob.glob(os.path.join(art or "", "sources", "**", "*"), recursive=True))
            if os.path.isfile(p) and os.path.getsize(p) < 20_000_000]
    ft = []
    for p in srcs:
        name = os.path.basename(p).lower()
        if "fulltext" in name or "full-text" in name or re.search(r"pmc\d", name):
            ft.append(p); continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                head = fh.read(4000)
        except OSError:
            continue
        if re.search(r"<article|<sec\b|<body\b", head):
            ft.append(p)
    return ft


PMCID_RX = re.compile(r"PMC\d+", re.I)
PMID_RX = re.compile(r"(?<!\d)(\d{7,8})(?!\d)")


def link_identity(link: str) -> dict:
    """`PMC<id>` / PMID tokens carried by a citation link."""
    s = str(link or "")
    return {"pmcid": {m.upper() for m in PMCID_RX.findall(s)},
            "pmid": set(PMID_RX.findall(re.sub(r"PMC\d+", " ", s, flags=re.I)))}


def body_identity(path: str) -> dict:
    """Identity tokens carried by an archived body: file name plus the first 4 KB of content.

    PMIDs are scanned after blanking `PMC<id>` tokens, because a PMCID's digits are themselves
    7–8 digits long (`PMC11270764` would otherwise read as PMID 11270764).
    """
    name = os.path.basename(path)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            head = fh.read(4000)
    except OSError:
        head = ""
    stripped = re.sub(r"PMC\d+", " ", name + " " + head, flags=re.I)
    m = re.match(r"ref_(\d+)", name.lower())
    return {"name": name, "head": head, "ref": m.group(1) if m else "",
            "pmcid": {i.upper() for i in PMCID_RX.findall(name + " " + head)},
            "pmid": set(PMID_RX.findall(stripped))}


def attribute_fulltexts(sv: dict, ctx: dict) -> tuple:
    """Map each archived full-text body to the `ref_n` it backs; list the bodies that stay unmapped.

    Four channels, tried in order — a run names its archives the way it likes (`R14` wrote
    `PMC11270764_fulltext_jats.xml`, `input-contract.md` suggests `<esid>.<route>.xml`), and the
    channel set *is* the fix for O29: while this op read the `ref_<n>` prefix only, it passed
    vacuously on the very artifact that motivated it (R14 archived by PMCID, so the item reported
    "check not triggered" and never looked at a single citation link).

      1. `ref_<n>` prefix in the file name;
      2. the record's esid in the name or the head (`check.esids` order gives esid → ref);
      3. the same `PMC<id>` as that ref's citation link;
      4. the same PMID as that ref's citation link.

    A body none of whose tokens match anything is reported as unmapped instead of guessed at.
    """
    cites = sv.get("citations") or {}
    esids = ctx.get("check", {}).get("esids") or []
    by_ref, unmapped = {}, []
    for p in archived_fulltexts(sv.get("artifacts_dir") or ""):
        ident = body_identity(p)
        refs = [f"ref_{ident['ref']}"] if ident["ref"] else []
        blob = ident["name"] + " " + ident["head"]
        if not refs:
            refs = [f"ref_{i + 1}" for i, e in enumerate(esids) if e and e in blob]
        if not refs and isinstance(cites, dict):
            for ref, e in cites.items():
                if not isinstance(e, dict):
                    continue
                li = link_identity(e.get("link"))
                if (li["pmcid"] & ident["pmcid"]) or (li["pmid"] & ident["pmid"]):
                    refs.append(ref)
        if refs:
            for r in refs:
                by_ref.setdefault(r, []).append(p)
        else:
            unmapped.append(ident["name"])
    return by_ref, unmapped


def op_cite_link_is_deepest(sv: dict, spec: dict, ctx: dict) -> tuple:
    """A record analysed from the full text must cite the full text, not the abstract page.

    `A-P5` makes the *declaration* of a full-text check mandatory; the citation `link` is the other
    half of that promise. If a full-text body for a ref sits in `sources/` while `citations.json`
    still points that ref at the abstract/publisher URL, whoever clicks the superscript lands on a
    page that does not contain the numbers the report used. Attribution goes through the channels in
    `attribute_fulltexts`; a link carrying the same `PMC<id>` as the archive is accepted too.
    Nothing archived (or nothing attributable) ⇒ not triggered.
    """
    by_ref, unmapped = attribute_fulltexts(sv, ctx)
    note = (f"{len(unmapped)} full-text body(ies) archived but not attributable to a ref "
            f"({unmapped})" if unmapped else "")
    if not by_ref:
        return True, note or "no full-text body archived (check not triggered)"
    cites = sv.get("citations") or {}
    bad = []
    for ref in sorted(by_ref):
        bodies = by_ref[ref]
        base = os.path.basename(bodies[0])
        e = cites.get(ref)
        if not isinstance(e, dict):
            bad.append(f"{ref} missing from citations.json (full text archived as {base})")
            continue
        link = str(e.get("link") or "")
        ids = set().union(*[body_identity(p)["pmcid"] for p in bodies])
        if not (is_fulltext_citation_link(link) or any(i in link.upper() for i in ids)):
            bad.append(f"{ref} cites {link!r} but its full text is archived as {base}")
    if bad:
        return False, ("full-text body archived without pointing the citation at it: " + "; ".join(bad)
                       + " — a record analysed from the full text must cite the full text"
                       + (f" [{note}]" if note else ""))
    return True, (f"{len(by_ref)} full-text ref(s) cite their full-text carrier"
                  + (f"; {note}" if note else ""))


def op_fulltext_cite_has_body(sv: dict, spec: dict, ctx: dict) -> tuple:
    """A citation that *claims* full-text depth must be backed by the fetched body (the converse of A-P6).

    `A-P6` reads the archive and asks whether the link followed the analysis; this op reads the link
    and asks whether the archive exists at all.  Without it the L3 rule is one-sided: nothing stops a
    run from pointing `link` at a PMC article page — or fabricating one — and never fetching anything,
    so the citation claims "we read the full text" with no bytes on disk to contradict it.  The
    contract requires every fetched body to be copied under `/workspace/sources/` ("that path is
    archived with the run, so the evidence stays auditable"), so the archived bytes are exactly the
    audit trail the depth claim has to match.

    A link byte-equal to the record's own `full_article_link` is **not** a depth claim — the run did
    not choose it — and stays out of scope.  Needs the fixture (`spec['link_field']`, the record's own
    link column) plus `check.esids` for the ref → esid order.
    """
    cites = sv.get("citations") or {}
    if not isinstance(cites, dict) or not cites:
        return True, "no citations.json (A-S3 owns that failure)"
    body_ids = [body_identity(p)["pmcid"] for p in archived_fulltexts(sv.get("artifacts_dir") or "")]
    esids = (ctx.get("check") or {}).get("esids") or []
    bad, claimed, skipped = [], 0, 0
    for ref, e in sorted(cites.items()):
        if not isinstance(e, dict):
            continue
        link = str(e.get("link") or "")
        if not is_fulltext_citation_link(link):
            continue
        m = re.fullmatch(r"ref_(\d+)", ref)
        if m and 1 <= int(m.group(1)) <= len(esids):
            try:
                own = str(record_of(ctx["fixture"], esids[int(m.group(1)) - 1]).get(spec["link_field"]) or "")
            except KeyError:
                own = ""
            if own == link:
                skipped += 1
                continue
        claimed += 1
        want = link_identity(link)["pmcid"]
        if not any(want & ids for ids in body_ids):
            bad.append(f"{ref} cites the full-text carrier {link!r} but no body under sources/ carries "
                       f"{sorted(want) or 'that article'}")
    if bad:
        return False, ("full-text citation without the fetched body: " + "; ".join(bad)
                       + " — the depth claim has no bytes behind it")
    if not claimed:
        return True, ("no citation points at a full-text carrier (check not triggered)"
                      + (f"; {skipped} link(s) byte-equal to the record's own link" if skipped else ""))
    return True, (f"{claimed} full-text citation(s) backed by an archived body"
                  + (f"; {skipped} link(s) were the record's own" if skipped else ""))


def op_report_excludes_literals(sv: dict, spec: dict) -> tuple:
    """Template *spec* wording must never be echoed into the delivered report.

    The report templates carry the original-source rules as bracketed spec sitting next to
    the `原文核对：` slot.  A run that copies that spec register into the report ships
    instruction text to the reader instead of findings: R15 (2026-09-18, published v1.6 /
    1.0.7) rendered 「原文优先于库内加工字段，不一致处同时写出原文值与库内记录值；」 inside
    its coverage line.  The template has since moved those sentences inside the spec
    brackets; this item is the mechanical guard against a future edit putting them back.
    """
    rep = sv.get("report") or ""
    hits = [t for t in spec["literals"] if t in rep]
    if hits:
        return False, ("report carries template spec wording verbatim: "
                       + ", ".join(repr(h) for h in hits))
    return True, f"no template spec wording in report ({len(spec['literals'])} phrases checked)"


def op_no_rule_metastatement(sv: dict, spec: dict) -> tuple:
    """A deliverable must not carry a sentence about the rule itself.

    R16 (2026-09-18, deployed v1.6 / v1.0.7 with the templates already fixed for the *verbatim* echo)
    rendered 「未发现原文与库内记录在同一指标、同一口径上的数值不一致；」 inside its coverage line: this is
    meta text about our contract, not a finding — no values, no ref, nothing a reader can act on.  A real
    divergence always carries both values plus a `{{ref_n}}`, so "names the library side AND talks about
    一致/不一致 BUT holds no digit" is exactly the meta register.  `A-P7` catches the verbatim echo; this
    catches the paraphrase, because in one run the model copied our sentence and in the next it rewrote it.
    """
    rep = sv.get("report") or ""
    side = re.compile(spec.get("side_regex", r"库内记录|库内抽取|库内字段|库内值"))
    word = re.compile(spec.get("word_regex", r"不一致|一致"))
    bad = [t for blk in blocks(rep) for t in sentences(blk)
           if side.search(t) and word.search(t) and not re.search(r"\d", t)]
    if bad:
        return False, ("report states the rule instead of a finding: "
                       + "; ".join(repr(b[:80]) for b in bad[:3]))
    return True, "no rule-shaped statement about the library side (库内… + 一致…, digits-free)"


def op_title_scope(sv: dict, item: dict) -> tuple:
    """The H1 must identify what is being compared — and never collapse the two into one.

    Three legal shapes (O20, 2026-09-18 — a theme title is legitimate and used to be
    wrongly failed):

    1. both record subjects named (the original expectation);
    2. a theme title naming the shared population/indication plus a comparison marker,
       with no drug name at all (R16/R17 render `# 脂蛋白(a) 升高人群降脂治疗跨试验对比报告`);
    3. *fail* whenever the title names exactly one of the two subjects — that is the
       "写成同一个药" error the item exists for (mutation M06), and it stays a failure
       no matter how good the rest of the theme is.
    """
    text = sv[item.get("surface", "report")] or ""
    rx = item.get("line_regex", r"^#\s")
    lines = [l for l in text.splitlines() if re.search(rx, l)]
    if not lines:
        return False, f"no line matching {rx!r}"
    line = lines[0]
    hits = [g for g in item["subjects"] if any(re.search(p, line) for p in g)]
    if len(hits) == len(item["subjects"]):
        return True, f"H1 names both subjects: {line.strip()[:80]!r}"
    if hits:
        missing = [g for g in item["subjects"] if g not in hits]
        return False, (f"H1 names {len(hits)}/{len(item['subjects'])} subjects "
                       f"(missing {missing}): {line.strip()[:80]!r} — the two compared "
                       f"records read as one drug")
    theme = item.get("theme_all", [])
    if theme and all(re.search(p, line) for p in theme):
        return True, f"theme H1 (no drug name, population + comparison marker): {line.strip()[:80]!r}"
    return False, (f"H1 names neither both subjects nor a theme "
                   f"(missing {[p for p in theme if not re.search(p, line)]}): {line.strip()[:80]!r}")


# --------------------------------------------------------------------------- driver


SHAPE_OPS = {
    "artifact_present": op_artifact_present,
    "artifact_absent": op_artifact_absent,
    "no_verbatim_copy": op_no_verbatim_copy,
    "original_check_names_class": op_original_check_names_class,
    "fulltext_fetch_is_named": op_fulltext_fetch_is_named,
    "cite_link_is_deepest": op_cite_link_is_deepest,
    "fulltext_cite_has_body": op_fulltext_cite_has_body,
    "report_excludes_literals": op_report_excludes_literals,
    "no_rule_metastatement": op_no_rule_metastatement,
    "glob_count": op_glob_count,
    "citations_keys_exact": op_citations_keys_exact,
    "citations_entry_key_set": op_citations_entry_key_set,
    "citations_matches_record": op_citations_matches_record,
    "citations_distinct": op_citations_distinct,
    "chart_envelope": op_chart_envelope,
    "title_scope": op_title_scope,
    "chart_values": op_chart_values,
    "sign_convention_consistent": op_sign_convention_consistent,
    "chart_set_allowed": op_chart_set_allowed,
    "chart_or_reason": op_chart_or_reason,
}
NO_CTX_OPS = {k: v for k, v in SHAPE_OPS.items()
               if k not in ("citations_matches_record", "cite_link_is_deepest",
                            "fulltext_cite_has_body")}
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


def eval_sent_if(item: dict, sv: dict) -> tuple:
    """Conditional sentence rule: *if* a sentence matches `if_regex`, it must carry all patterns.

    Needed for the original-source rules, which only bind when the occasion arises:
    a divergence between original and pulled extract must show both values in one
    sentence, but a run where nothing diverged has no such sentence and must not fail.
    """
    text = sv["report"]
    if not text:
        return False, "report surface is empty"
    rx = re.compile(item["if_regex"])
    hits = [sent for b in blocks(text) for sent, _ in units(b) if rx.search(sent)]
    if not hits:
        return True, f"no sentence matches {item['if_regex']!r} (check not triggered)"
    bad = [s for s in hits if any(not re.search(p, s) for p in item["patterns"])]
    if bad:
        return False, (f"{len(bad)}/{len(hits)} triggered sentence(s) missing patterns "
                       f"{[p for p in item['patterns'] if not re.search(p, bad[0])]}: "
                       f"{bad[0].strip()[:80]!r}")
    return True, f"{len(hits)} triggered sentence(s) carry all {len(item['patterns'])} pattern(s)"


def eval_attribution(item: dict, sv: dict) -> tuple:
    """Every claim that cites anything must cite the owner of each token it names.

    Granularity is the sentence, not the line: a scope line that lists both trials
    legitimately names both drugs, so a line-level rule cannot see a drug name that
    got attached to the wrong record.

    **Exemption (O19, 2026-09-18):** an *identity* pair (`subject: true` — a drug name or a
    trial registration number, i.e. a token that names the record) does not count as
    misattribution when the unit also names an identity of a record it *does* cite: such a
    sentence is comparing two records, and which side carries the trailing marker is a
    writing choice, not a factual error.  R12 ("安全性维度只有 OCEAN(a)-DOSE …{{ref_2}}，
    NCT02729025 未报告安全性数据") and R15 ("…与奥帕司兰的 Lp(a) 降幅终点不是同一构念{{ref_1}}")
    are exactly that shape and were false positives.  **Value pairs are never exempt**: a
    unit citing A that carries B's number still fails (M27), and so does a unit that names
    B without naming any identity of the record it cites (M06 / M15).
    """
    text = sv["report"]
    if not text:
        return False, "report surface is empty"
    subjects = {p["owner"] for p in item["pairs"] if p.get("subject")}
    subj_rx = {}
    for p in item["pairs"]:
        if p.get("subject"):
            subj_rx.setdefault(p["owner"], []).append(p["token"])
    bad, checked, exempt = [], 0, 0
    for b in blocks(text):
        for sent, rs in units(b):
            if not rs:
                continue
            named_subject = {o for o in rs if o in subj_rx
                             and any(re.search(t, sent) for t in subj_rx[o])} if subjects else set()
            for pair in item["pairs"]:
                if not re.search(pair["token"], sent):
                    continue
                checked += 1
                if pair["owner"] in rs:
                    continue
                if pair.get("subject") and named_subject:
                    exempt += 1
                    continue
                bad.append(f"{pair['token']!r} in unit citing {sorted(rs)} "
                           f"(owner {pair['owner']}): {sent.strip()[:70]!r}")
    if bad:
        return False, "; ".join(bad)
    return True, (f"{checked} token/unit pairings correctly attributed"
                  + (f"; {exempt} identity pairing(s) skipped as comparison (cited record named)" if exempt else ""))



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
        elif kind == "sent_if":
            ok, detail = eval_sent_if(item, sv)
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
