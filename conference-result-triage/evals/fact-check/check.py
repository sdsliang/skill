#!/usr/bin/env python3
"""Offline fact-checklist scorer for conference-result-triage.

Reads a ``toolsmith-publish run`` directory and scores the *deliverable* against a
hand-written checklist, producing one scalar: ``facts_ok/facts_total``.

Why this exists
---------------
The old gates were boolean: did the run finish, did ``check_cards.py`` exit 0. A
boolean cannot tell "45 good cards" from "45 cards that pass the schema". Adopting
the pattern from ``clinical-result-comparison/evals/fact-check/``: write down what
the run *must be able to say*, then judge it mechanically, so a change to the skill
can be scored as better or worse instead of pass/fail.

Surfaces (all read from the run dir, nothing is fetched)
--------------------------------------------------------
watchlist  artifacts/output/watchlist.json      the deliverable
pool       artifacts/work/pool/pool.json        candidate records (optional)
calls      debug-history.json raw_model_messages tool-call parts (args as JSON)
reply      last assistant text part of messages.json
transcript transcript.md

Usage
-----
    python3 check.py --run ~/.local/state/toolsmith-runs/20261111-174917-cards-e2e2
    python3 check.py --run <dir> -v            # print every item
    python3 check.py --run <dir> --json /tmp/score.json

Exit codes: 0 = every fail-severity item PASS, 3 = at least one FAIL,
4 = the run directory or its deliverable cannot be read.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List

EVALUATOR_REVISION = "2026-11-13-r5"

# Presidential / late-breaking trials the X discussion concentrated on. Used by the
# heat-coverage item, which is `warn`: the list must never be bent toward what was
# talked about, but a total miss is worth printing.
HEAT_TRIALS = ["DeLLphi-305", "SAFFRON", "INTerpath-001", "VOLGA", "KRASCENDO-1",
               "CheckMate 8HW", "CLARITY-Gastric01", "OptiTROP-Lung06", "PANKU-Lung01",
               "HERON-Lung01", "TroFuse-005", "NEOTORCH"]

BUCKETS = ("early", "pivotal", "failed")
SCORE_CAPS = {"evidence_strength": 30, "effect_size": 25, "clinical_impact": 25,
              "novelty": 10, "readout_maturity": 10}
PER_BUCKET_CAP = 10
TOTAL_CAP = 30
MIN_WHY_CHARS = 60
LISTED_FIELDS = ("name", "ticker", "exchange", "source_url")
# v0.9: the quote layer is gone. These keys are what a regression would look like.
PRICE_KEYS = ("stock", "reaction", "change_pct", "excess_pct", "bench_change_pct",
              "price_source")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
# `个?月` and not just `月`: Chinese abstracts write "16 个月", and a unit alternation that
# only knew "月" skipped every one of those figures -- "随访约 16 个月" (the record says 16.1)
# went unchecked while the same mistake in English was caught.
NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(%|mo|months?|个?月|HR|hazard|OR\b|p\s*[=<>]|P\s*[=<>])")


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def _load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_run(run_dir: str) -> dict:
    """Collect the surfaces. Any missing optional surface becomes None/[]."""
    art = os.path.join(run_dir, "artifacts")
    index = _load_json(os.path.join(run_dir, "artifacts.json"), []) or []
    paths = [x.get("path", "") for x in index if isinstance(x, dict)]

    def pick(*suffixes):
        for want in suffixes:
            for p in paths:
                if p.endswith(want):
                    local = os.path.join(art, p[len("/workspace/"):])
                    if os.path.exists(local):
                        return local
        return None

    watchlist_path = pick("output/watchlist.json")
    pool_path = pick("work/pool/pool.json")
    # v0.9: the delivered result is the Markdown report (frontmatter carries `skills`),
    # so the report itself is a surface -- not just the JSON behind it.
    report_path = pick("output/report.md")

    watchlist = _load_json(watchlist_path) if watchlist_path else None
    pool = _load_json(pool_path) if pool_path else None

    calls = []
    hist = _load_json(os.path.join(run_dir, "debug-history.json"), {}) or {}
    for msg in hist.get("raw_model_messages") or []:
        for part in msg.get("parts") or []:
            if part.get("part_kind") != "tool-call":
                continue
            args = part.get("args")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            calls.append({"name": part.get("tool_name"), "args": args or {}})

    reply = ""
    msgs = _load_json(os.path.join(run_dir, "messages.json"), []) or []
    for msg in reversed(msgs if isinstance(msgs, list) else []):
        for part in reversed(msg.get("parts") or []):
            body = part.get("text") or part.get("content")
            if body and part.get("part_kind") in (None, "text"):
                reply = body
                break
        if reply:
            break

    transcript = ""
    tpath = os.path.join(run_dir, "transcript.md")
    if os.path.exists(tpath):
        with open(tpath, encoding="utf-8", errors="replace") as f:
            transcript = f.read()

    rows_path = pick("work/rows.json")
    ledger_path = pick("work/slice_counts.json")
    ledger = _load_json(ledger_path) if ledger_path else None

    # `plan_slices.py` writes one `slice_NN.json` per slice into work/slices/. It is the
    # only surface that proves the corpus was actually split: subagent tool calls never
    # reach the parent transcript, and `tool_results/` is wiped at turn end.
    slices: List[List[str]] = []
    sdir = os.path.join(os.path.dirname(rows_path), "slices") if rows_path else ""
    if sdir and os.path.isdir(sdir):
        for name in sorted(os.listdir(sdir)):
            if name.startswith("slice_") and name.endswith(".json"):
                doc = _load_json(os.path.join(sdir, name))
                if isinstance(doc, list):
                    slices.append([str(x) for x in doc])

    rows_doc = _load_json(rows_path) if rows_path else None
    rows = rows_doc
    if isinstance(rows_doc, dict):
        rows = rows_doc.get("rows")

    # `work/web/<bucket>.jsonl` -- one line per live search, the only durable proof
    # that step 5B happened (the reply can claim anything; tool_results is wiped).
    web_evidence: Dict[str, List[dict]] = {}
    wdir = os.path.join(os.path.dirname(rows_path), "web") if rows_path else ""
    if wdir and os.path.isdir(wdir):
        for name in sorted(os.listdir(wdir)):
            if not name.endswith(".jsonl"):
                continue
            recs = []
            with open(os.path.join(wdir, name), encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        recs.append(json.loads(line))
                    except Exception:
                        recs.append({})
            web_evidence[name] = recs

    report = ""
    if report_path and os.path.exists(report_path):
        with open(report_path, encoding="utf-8", errors="replace") as f:
            report = f.read()

    # Any `citations*.json` that actually landed under output/ -- the frontmatter path
    # is checked separately, because a declared path that does not exist is the bug.
    citations: Dict[str, dict] = {}
    out_dir = os.path.join(art, "output")
    if os.path.isdir(out_dir):
        for name in sorted(os.listdir(out_dir)):
            if name.startswith("citations") and name.endswith(".json"):
                doc = _load_json(os.path.join(out_dir, name), {}) or {}
                if isinstance(doc, dict):
                    citations[name] = doc

    return {"watchlist": watchlist, "pool": pool, "calls": calls, "reply": reply,
            "report": report, "citations": citations,
            "web_evidence": web_evidence,
            "slice_counts": ledger if isinstance(ledger, list) else None,
            "rows": rows if isinstance(rows, list) else None,
            "rows_doc": rows_doc if isinstance(rows_doc, dict) else None,
            "slices": slices,
            "transcript": transcript,
            "paths": {"watchlist": watchlist_path, "pool": pool_path,
                      "report": report_path}}


def pool_text_by_esid(pool) -> dict:
    """Everything the abstract itself said, concatenated per esid."""
    out = {}
    if not pool:
        return out
    for bucket in (pool.get("pools") or {}).values():
        for item in bucket.get("items") or []:
            key = str(item.get("esid") or "")
            if not key:
                continue
            out[key] = " ".join(str(item.get(f) or "") for f in
                                ("title", "results_text", "abstract_text",
                                 "key_evidence", "summary", "machine_signal"))
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def numbers_of(text: str) -> list:
    return [m.group(0) for m in NUM_RE.finditer(text or "")]


def value_traceable(value: float, unit: str, src: str) -> bool:
    """The figure itself must occur in the record's own text.

    Units are deliberately not a gate: abstracts put `%` in a table header and write
    `12.9 (95% CI 10.4-16.3) months`. So the check is "does this number appear at
    all" -- which is what "traceable" can honestly mean offline. Whether `47.5` there
    was an ORR or a TRAE rate is a semantic judgement, and the reply has to say so.
    """
    for m in re.finditer(r"(\d+(?:\.\d+)?)", src):
        if abs(float(m.group(1)) - value) <= 1e-9:
            return True
    return False


# --------------------------------------------------------------------------- #
# ops
# --------------------------------------------------------------------------- #
def op_query_slicing(sv, spec):
    """Every data pull must slice by `esids`; a wide pull truncates at ~458/1097 rows.

    Three surfaces, best first, because none of them is always there:

    1. `work/slices/slice_NN.json` -- the split itself, durable, and independent of
       who performed the pull (the pulls are usually delegated to a `task`
       subagent, whose calls never reach this turn's debug-history);
    2. `rows.json.sources` -- one entry per dump with the rows it contributed;
    3. the parent turn's own tool calls -- only when nobody delegated.
    """
    min_calls = spec.get("min_calls", 7)
    max_slice = spec.get("max_slice", 300)

    slices = sv.get("slices") or []
    if slices:
        biggest = max((len(x) for x in slices), default=0)
        union = {i for x in slices for i in x}
        rows = sv.get("rows") or []
        have = {str(r.get("clinical_result__id") or r.get("clinical_result_extra_esid") or "")
                .removeprefix("nr_") for r in rows}
        uncovered = sorted(i for i in union if i.removeprefix("nr_") not in have)
        # Both directions matter: a slice set that misses rows hides a lost pull, and
        # one that invents ids means rows.json was not the output of these slices.
        unsliced = sorted(i for i in have if i and i not in {u.removeprefix("nr_") for u in union})
        sources = (sv.get("rows_doc") or {}).get("sources") or []
        ok = (len(slices) >= min_calls and 0 < biggest <= max_slice
              and not uncovered and not unsliced)
        return ok, (f"{len(slices)} slices (largest {biggest} ids, {len(union)} distinct), "
                    f"{len(sources)} dumps recorded in rows.json, "
                    f"{len(uncovered)} slice ids missing from rows, "
                    f"{len(unsliced)} rows ids not in any slice")

    sources = (sv.get("rows_doc") or {}).get("sources")
    if isinstance(sources, list) and sources:
        dumps = [x for x in sources if int(x.get("rows") or 0) > 0]
        ok = len(dumps) >= min_calls
        return ok, (f"{len(sources)} dumps in rows.json, {len(dumps)} non-empty "
                    f"(slices dir absent, so the split cannot be checked)")

    ledger = sv.get("slice_counts")
    if ledger:
        n = len(ledger)
        dumps = {x.get("dump") for x in ledger if x.get("dump")}
        complete = all(int(x.get("missing_ids") or 0) == 0 for x in ledger)
        biggest = max((int(x.get("requested_ids") or 0) for x in ledger), default=0)
        ok = (n >= min_calls and len(dumps) == n and complete
              and 0 < biggest <= max_slice)
        return ok, (f"{n} slices, {len(dumps)} distinct dumps, missing_ids all zero={complete}, "
                    f"largest slice {biggest} ids")

    q = [c for c in sv["calls"] if "clinical-result-with-params" in str(c["name"])]
    if not q:
        return False, "no query tool call at all"
    sliced = [c for c in q if c["args"].get("esids")]
    wide = [c for c in q if not c["args"].get("esids")]
    biggest = max((len(c["args"].get("esids") or []) for c in sliced), default=0)
    ok = len(sliced) >= min_calls and biggest <= max_slice
    return ok, (f"{len(sliced)} sliced calls (max {biggest} ids), {len(wide)} unsliced; "
                f"need >={min_calls} sliced, max id count <={max_slice}")


def op_transcript_has(sv, spec):
    pat = spec["pattern"]
    hit = re.search(pat, sv["transcript"])
    return bool(hit), (f"found {hit.group(0)!r}" if hit else f"missing pattern {pat!r}")


def op_transcript_absent(sv, spec):
    pat = spec["pattern"]
    hit = re.search(pat, sv["transcript"])
    return not hit, (f"forbidden {hit.group(0)!r} present" if hit else "absent, as required")


def op_present_artifact(sv, spec):
    calls = [c for c in sv["calls"] if c["name"] == "present_artifact"]
    if not calls:
        return False, "present_artifact was never called"
    paths = [str(c["args"].get("path") or "") for c in calls]
    ok = any(p.endswith(spec["suffix"]) for p in paths)
    return ok, f"presented {paths}"


def op_cards_cap(sv, spec):
    cards = ((sv["watchlist"] or {}).get("cards") or [])
    per = {}
    for c in cards:
        per[c.get("bucket")] = per.get(c.get("bucket"), 0) + 1
    bad = {k: v for k, v in per.items() if v > spec.get("cap", PER_BUCKET_CAP)}
    over_total = len(cards) > spec.get("total", TOTAL_CAP)
    ok = not bad and not over_total
    return ok, f"per-bucket {per}, total {len(cards)}"


def op_why_depth(sv, spec):
    """`why` must be a judgement: long enough to hold one, and not `summary` re-wrapped.

    A 20-character `why` is a label ("数据好"), and a `why` that opens with the same
    20 characters as `summary` is the number restated. Both were the actual failure
    of v0.6's cards.
    """
    bad = []
    for i, c in enumerate((sv["watchlist"] or {}).get("cards") or [], 1):
        why = str(c.get("why") or "")
        summary = str(c.get("summary") or "")
        if len(why) < spec.get("min_chars", MIN_WHY_CHARS):
            bad.append(f"card{i} why {len(why)} chars")
        elif summary and (summary[:20] in why or why[:20] in summary):
            bad.append(f"card{i} why repeats summary")
    return not bad, "; ".join(bad[:4]) if bad else "every why is a judgement, not a label"


def op_listed_company_shape(sv, spec):
    """`listed_company` is mandatory; a non-null one must carry ticker + source URL."""
    bad = []
    for i, c in enumerate((sv["watchlist"] or {}).get("cards") or [], 1):
        if "listed_company" not in c:
            bad.append(f"card{i} key missing")
            continue
        co = c["listed_company"]
        if co is None:
            continue
        if not isinstance(co, dict):
            bad.append(f"card{i} not an object")
            continue
        for key in LISTED_FIELDS:
            if not str(co.get(key) or "").strip():
                bad.append(f"card{i} .{key} empty")
        if not re.match(r"^https?://\S+$", str(co.get("source_url") or "")):
            bad.append(f"card{i} source_url not http(s)")
    return not bad, "; ".join(bad[:4]) if bad else "listed_company present and sourced"


def op_promotion_traceable(sv, spec):
    """A card outside the machine pools may only enter as a `promoted: "web"` record,
    and the esid must exist in `rows.json` -- otherwise the numbers have no source."""
    pool_ids, row_ids = set(), set()
    for bucket in ((sv["pool"] or {}).get("pools") or {}).values():
        for item in bucket.get("items") or []:
            if item.get("esid"):
                pool_ids.add(str(item["esid"]).removeprefix("nr_"))
    for row in sv["rows"] or []:
        if isinstance(row, dict):
            for key in ("esid", "_id", "clinical_result.extra_esid",
                        "clinical_result._extra_esid"):
                if row.get(key):
                    row_ids.add(str(row[key]).removeprefix("nr_"))
                    break
    bad, seen = [], 0
    for i, c in enumerate((sv["watchlist"] or {}).get("cards") or [], 1):
        esid = str(c.get("esid") or "").removeprefix("nr_")
        if esid in pool_ids:
            if c.get("promoted"):
                bad.append(f"card{i} promoted but already in pool")
            continue
        seen += 1
        if c.get("promoted") != "web":
            bad.append(f"card{i} outside pool without promoted='web'")
        elif row_ids and esid not in row_ids:
            bad.append(f"card{i} promoted esid not in rows.json")
    return not bad, ("; ".join(bad[:4]) if bad
                     else f"all {seen} out-of-pool card(s) traceable to rows.json")


def op_web_evidence(sv, spec):
    """The web step must leave re-checkable evidence, not just a claim in the reply.

    A dead provider is not a licence to ship silently, but it is also not a reason to
    ship nothing: the degrade path is to say so in `coverage_notes` and keep the list.
    Which is why the declared-unavailable branch exists -- otherwise a 403 on one
    investor-relations page turns into "no deliverable at all" (observed in cards-e2e5).
    """
    files = sv.get("web_evidence") or {}
    if not files:
        notes = " ".join(str(n) for n in ((sv["watchlist"] or {}).get("coverage_notes") or []))
        if re.search(spec.get("unavailable_pattern", r"联网"), notes) and \
                re.search(spec.get("unavailable_why", r"不可用|失败|未完成|未启用|无返回|超时"), notes):
            return True, "web step declared unavailable in coverage_notes"
        return False, "no work/web/*.jsonl -- the web curation step left no trace"
    lines = sum(len(v) for v in files.values())
    if lines < spec.get("min_lines", 6):
        return False, f"only {lines} search record(s) across {len(files)} file(s)"
    # A search that returned nothing usable has no URL -- that is an honest record, not
    # a fabricated one. What it may not be is silent: a URL-less row must say why, and
    # the evidence as a whole still has to carry real sources (min_urls).
    # Rows that carry a price (close + change_pct) are market calls, not searches: they
    # could satisfy the search-evidence floor without a single query having run. v0.9
    # removed the quote layer, so this filter is now purely defensive -- it stays
    # because the floor is the only thing standing between "curated with the web" and
    # "wrote a plausible list".
    def _is_quote(row):
        return "close" in row and "change_pct" in row

    rows = [(k, i, r) for k, v in files.items() for i, r in enumerate(v, 1)
            if not _is_quote(r)]
    url_rows = [x for x in rows if str(x[2].get("url") or "").startswith("http")]
    silent = [f"{k}:{i}" for k, i, r in rows
              if not str(r.get("url") or "").startswith("http")
              and not str(r.get("note") or "").strip()]
    if silent:
        return False, f"{len(silent)} record(s) with neither URL nor note"
    min_urls = spec.get("min_urls", 6)
    if len(url_rows) < min_urls:
        return False, (f"{len(url_rows)} record(s) with a URL < min_urls={min_urls} "
                       f"({lines} record(s) total)")
    return True, (f"{len(files)} file(s)/{lines} record(s), {len(url_rows)} with a URL")


def _frontmatter(text: str):
    """The YAML block at the top of the report, parsed just enough to be checked.

    Not a YAML parser on purpose: the contract is three scalars and one list, and a
    dependency-free reader that also *rejects* what the contract forbids (a bare
    ``type`` standing in for ``skills``) is more useful here than a tolerant one.
    """
    m = FRONTMATTER_RE.match(text or "")
    if not m:
        return None
    meta: dict = {}
    key = None
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line.lstrip()[2:].strip().strip('"\''))
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not val:
            meta[key] = []
        elif val.startswith("[") and val.endswith("]"):
            meta[key] = [x.strip().strip('"\'') for x in val[1:-1].split(",") if x.strip()]
        else:
            meta[key] = val.strip('"\'')
    return meta


def op_no_price_claims(sv, spec):
    """v0.9 removed the quote layer; this item is what keeps it removed.

    The reason is not taste. Re-measured on the 30-card e2e run, anchoring each card on
    its *own* abstract release date and printing the excess over that market's sector
    benchmark left 18 of 24 quotes inside +/-0.6% -- i.e. the number was the sector's
    beta, not a view on the abstract. Eight Merck cards all received the same -3.83%,
    because the move belongs to the company, not to any one readout.
    """
    cards = (sv["watchlist"] or {}).get("cards") or []
    hits = []
    for i, c in enumerate(cards, 1):
        for k in PRICE_KEYS:
            if k in c and c.get(k) not in (None, "", {}):
                hits.append(f"card{i}.{k}")
        co = c.get("listed_company")
        if isinstance(co, dict):
            for k in PRICE_KEYS:
                if k in co and co.get(k) not in (None, "", {}):
                    hits.append(f"card{i}.listed_company.{k}")
    if hits:
        return False, f"price fields came back: {', '.join(hits[:5])}"
    return True, f"no price claim on {len(cards)} card(s)"


def op_report_meta(sv, spec):
    """The result must be identifiable as *this* skill's output by `skills`, not `type`.

    Host-side contract (产品经理使用 Skill 的通用约束 §2): a non-empty `skills` array,
    `title`, `date`, `lang`; `citations` only when the result cites sources, and then
    the path must live under /workspace/output and match the body markers one-to-one.
    """
    text = sv.get("report") or ""
    if not text.strip():
        return False, "no artifacts/output/report.md -- the result was not delivered"
    meta = _frontmatter(text)
    if meta is None:
        return False, "report.md has no YAML frontmatter"
    bad = []
    skills = meta.get("skills")
    if not isinstance(skills, list) or not skills:
        bad.append("skills is not a non-empty array")
    want = spec.get("skill", "conference-result-triage")
    if isinstance(skills, list) and skills and want not in skills:
        bad.append(f"skills={skills} does not contain {want}")
    if not str(meta.get("title") or "").strip():
        bad.append("title missing")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(meta.get("date") or "")):
        bad.append("date is not YYYY-MM-DD")
    if not str(meta.get("lang") or "").strip():
        bad.append("lang missing")
    if "type" in meta and "skills" not in meta:
        bad.append("a bare `type` is not a result identifier")
    cites = str(meta.get("citations") or "").strip()
    if cites:
        if not cites.startswith("/workspace/output"):
            bad.append(f"citations path {cites!r} is outside /workspace/output")
        body = text[len(FRONTMATTER_RE.match(text).group(0)):]
        refs = re.findall(r"\{\{(ref_\d+)\}\}", body)
        declared = [v for v in (sv.get("citations") or {}).values()]
        keys = set()
        for doc in declared:
            keys |= set(doc.keys())
        if not declared:
            bad.append("citations declared but no citations json landed under output/")
        elif set(refs) != {k for k in keys if k.startswith("ref_")}:
            missing = sorted({k for k in keys if k.startswith("ref_")} - set(refs))
            dangling = sorted(set(refs) - keys)
            bad.append(f"body/citation mismatch missing={missing} dangling={dangling}")
        else:
            for key, item in (declared[0] or {}).items():
                if not isinstance(item, dict):
                    bad.append(f"{key} is not an object")
                    continue
                if not str(item.get("title") or "").strip():
                    bad.append(f"{key} has an empty title")
                if not re.match(r"^https?://\S+$", str(item.get("link") or "")):
                    bad.append(f"{key} link is not http(s)")
    if bad:
        return False, "; ".join(bad[:4])
    return True, (f"skills={skills} lang={meta.get('lang')} "
                  f"citations={'yes' if cites else 'no'}")


def op_count_matches(sv, spec):
    w = sv["watchlist"] or {}
    cards = w.get("cards") or []
    return w.get("count") == len(cards), f"count={w.get('count')} vs cards={len(cards)}"


def op_buckets_valid(sv, spec):
    bad = sorted({str(c.get("bucket")) for c in (sv["watchlist"] or {}).get("cards") or []
                  if c.get("bucket") not in BUCKETS})
    return not bad, f"unexpected buckets {bad}" if bad else "all buckets legal"


def op_unique_esid(sv, spec):
    esids = [str(c.get("esid")) for c in (sv["watchlist"] or {}).get("cards") or []]
    dup = sorted({e for e in esids if esids.count(e) > 1})
    return not dup, f"duplicates {dup}" if dup else f"{len(esids)} unique esids"


def op_score_shape(sv, spec):
    bad = []
    for i, c in enumerate((sv["watchlist"] or {}).get("cards") or [], 1):
        s = c.get("score")
        if not isinstance(s, int) or isinstance(s, bool) or not 0 <= s <= 100:
            bad.append(f"card{i} score={s!r}")
    return not bad, "; ".join(bad[:4]) if bad else "every card carries an integer 0-100 score"


def op_score_parts(sv, spec):
    bad = []
    for i, c in enumerate((sv["watchlist"] or {}).get("cards") or [], 1):
        parts = c.get("score_parts") or {}
        if set(parts) != set(SCORE_CAPS):
            bad.append(f"card{i} keys={sorted(parts)}")
            continue
        for k, cap in SCORE_CAPS.items():
            v = parts[k]
            if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= cap:
                bad.append(f"card{i} {k}={v!r} cap {cap}")
        if sum(parts.values()) != c.get("score"):
            bad.append(f"card{i} sum {sum(parts.values())} != {c.get('score')}")
    return not bad, "; ".join(bad[:4]) if bad else "five parts each within cap and summing to score"


def op_score_varied(sv, spec):
    """A constant score means nobody judged anything."""
    scores = [c.get("score") for c in (sv["watchlist"] or {}).get("cards") or []]
    distinct = len({s for s in scores if isinstance(s, int)})
    return distinct >= spec.get("min_distinct", 5), f"{distinct} distinct scores across {len(scores)} cards"


def op_score_order(sv, spec):
    """Within a bucket the list must descend by score."""
    by = {}
    for c in (sv["watchlist"] or {}).get("cards") or []:
        by.setdefault(c.get("bucket"), []).append(c.get("score") or 0)
    breaks = [b for b, xs in by.items() if any(xs[i] < xs[i + 1] for i in range(len(xs) - 1))]
    return not breaks, f"ascending inside {breaks}" if breaks else "each bucket descends by score"


def op_null_field(sv, spec):
    field = spec["field"]
    bad = [str(c.get("esid")) for c in (sv["watchlist"] or {}).get("cards") or []
           if c.get(field) not in (None, "")]
    return not bad, (f"{field} filled on {len(bad)} cards (e.g. {bad[:2]}) -- platform cannot supply it"
                     if bad else f"{field} null everywhere, as the platform requires")


def op_esids_in_pool(sv, spec):
    if not sv["pool"]:
        return None, "no pool snapshot in the run dir"
    known = set(pool_text_by_esid(sv["pool"]))
    unknown = [str(c.get("esid")) for c in (sv["watchlist"] or {}).get("cards") or []
               if str(c.get("esid")) not in known]
    return not unknown, (f"{len(unknown)} esids absent from the pool: {unknown[:3]}"
                         if unknown else f"all cards trace to pool records ({len(known)} indexed)")


def op_numbers_traceable(sv, spec):
    """Every unit-bearing figure in summary/why must occur in that record's own text."""
    if not sv["pool"]:
        return None, "no pool snapshot in the run dir"
    texts = pool_text_by_esid(sv["pool"])
    bad = []
    for c in (sv["watchlist"] or {}).get("cards") or []:
        body = f"{c.get('summary') or ''} {c.get('why') or ''}"
        src = norm(texts.get(str(c.get("esid")), ""))
        for m in NUM_RE.finditer(body):
            if not value_traceable(float(m.group(1)), m.group(2), src):
                bad.append(f"{c.get('esid')}: {m.group(0)!r}")
    return not bad, (f"{len(bad)} untraceable figures: {bad[:4]}" if bad
                     else "every figure in summary/why occurs in that record")


def op_no_json_paste(sv, spec):
    blocks = re.findall(r"```json\s*(.*?)```", sv["reply"] or "", re.S)
    big = [b for b in blocks if len(b) > spec.get("max_chars", 1500)]
    return not big, (f"{len(big)} pasted JSON block(s) over {spec.get('max_chars', 1500)} chars"
                     if big else "deliverable not pasted into the reply")


def op_reply_mentions(sv, spec):
    pats = spec["patterns"]
    hits = [p for p in pats if re.search(p, sv["reply"] or "")]
    need = spec.get("min_hits", 1)
    return len(hits) >= need, f"{len(hits)}/{len(pats)} of {pats} found"


def op_lba_not_dropped(sv, spec):
    """A late-breaking abstract must never be dropped for having a blank phase.

    The platform's only phase signal is `evidence_source`, and 16 of the 73 ESMO
    2026 LBAs fill it with the study design ("前瞻性研究"). Reading that as
    non-trial evidence deleted VOLGA, KRASCENDO-1 and CLARITY-Gastric01 -- the
    Presidential session -- while the pool still reported full coverage, because
    coverage is measured against the rows actually fetched.

    Ids are normalised by stripping the `nr_` prefix: the result table keys the
    human-curated slice `nr_<esid>` while the same record is `<esid>` elsewhere.
    """
    if not sv.get("rows") or not sv["pool"]:
        return None, "no rows.json / pool.json in the run dir"

    def norm(value):
        return str(value or "").strip().removeprefix("nr_")

    lba_rows = [r for r in sv["rows"]
                if str(r.get("clinical_result_lba") or r.get("lba") or "").strip().upper() == "LBA"]
    if not lba_rows:
        return None, "no lba rows in this corpus"
    pooled = {norm(item.get("esid"))
              for bucket in (sv["pool"].get("pools") or {}).values()
              for item in bucket.get("items") or []}
    dropped = [norm(r.get("clinical_result__id") or r.get("_id")
                    or r.get("clinical_result_extra_esid"))
               for r in lba_rows
               if norm(r.get("clinical_result__id") or r.get("_id")
                       or r.get("clinical_result_extra_esid")) not in pooled]
    excluded = sv["pool"].get("excluded") or {}
    bad_exc = [k for k in excluded if "前瞻性" in str(k)]
    ok = not bad_exc and len(dropped) <= spec.get("allow_dropped", 0)
    return ok, (f"{len(lba_rows)} lba rows in the corpus, "
                f"{len(lba_rows) - len(dropped)} reach the pool, "
                f"{len(dropped)} dropped (e.g. {dropped[:2]}), "
                f"phase-as-design exclusions={bad_exc}")


def op_coverage_claims(sv, spec):
    """The deliverable itself must admit what it could not determine.

    Two claims are part of the contract, not decoration: the data_type was often not
    determinable, and only part of the corpus carries p / HR. If those live only in a
    chat reply, the JSON -- which is what gets read next month -- reads as if the
    corpus were complete.
    """
    notes = (sv["watchlist"] or {}).get("coverage_notes") or []
    text = " ".join(str(n) for n in notes)
    missing = [g for g in spec["groups"] if not re.search(g, text)]
    return not missing, (f"{len(notes)} notes; missing {missing}" if missing
                         else f"{len(notes)} notes state both limits")


def op_heat_coverage(sv, spec):
    cards = (sv["watchlist"] or {}).get("cards") or []
    body = " ".join(norm(c.get(f) or "") for c in cards
                    for f in ("title", "summary", "why", "drug", "indication"))
    hit = [t for t in spec.get("trials", HEAT_TRIALS) if norm(t) in body]
    return len(hit) >= spec.get("min_hits", 3), f"{len(hit)}/{len(spec.get('trials', HEAT_TRIALS))} heat trials on the list: {hit}"


OPS = {
    "query_slicing": op_query_slicing,
    "transcript_has": op_transcript_has,
    "transcript_absent": op_transcript_absent,
    "present_artifact": op_present_artifact,
    "cards_cap": op_cards_cap,
    "count_matches": op_count_matches,
    "buckets_valid": op_buckets_valid,
    "unique_esid": op_unique_esid,
    "score_shape": op_score_shape,
    "score_parts": op_score_parts,
    "score_varied": op_score_varied,
    "score_order": op_score_order,
    "null_field": op_null_field,
    "esids_in_pool": op_esids_in_pool,
    "numbers_traceable": op_numbers_traceable,
    "no_json_paste": op_no_json_paste,
    "reply_mentions": op_reply_mentions,
    "lba_not_dropped": op_lba_not_dropped,
    "coverage_claims": op_coverage_claims,
    "why_depth": op_why_depth,
    "listed_company_shape": op_listed_company_shape,
    "promotion_traceable": op_promotion_traceable,
    "web_evidence": op_web_evidence,
    "report_meta": op_report_meta,
    "no_price_claims": op_no_price_claims,
    "heat_coverage": op_heat_coverage,
}


def score(sv: dict, facts: dict, verbose: bool = False) -> dict:
    rows, fails = [], []
    for item in facts["items"]:
        fn = OPS.get(item["op"])
        if fn is None:
            rows.append({"id": item["id"], "state": "ERROR", "detail": f"unknown op {item['op']}"})
            fails.append(item["id"])
            continue
        try:
            ok, detail = fn(sv, item)
        except Exception as exc:  # a crashing op is a failing op, never a passing one
            ok, detail = False, f"op raised {type(exc).__name__}: {exc}"
        if ok is None:
            state = "SKIP"
        else:
            state = "PASS" if ok else "FAIL"
        if state == "FAIL" and item.get("severity", "fail") == "fail":
            fails.append(item["id"])
        rows.append({"id": item["id"], "state": state, "severity": item.get("severity", "fail"),
                     "detail": detail, "rationale": item.get("rationale", "")})
        if verbose:
            print(f"  [{state:4}] {item['id']:28} {detail}")
    graded = [r for r in rows if r["severity"] == "fail" and r["state"] != "SKIP"]
    ok_n = sum(1 for r in graded if r["state"] == "PASS")
    warn = [r for r in rows if r["severity"] == "warn"]
    return {"rows": rows, "fails": fails, "ok": ok_n, "total": len(graded),
            "warn_ok": sum(1 for r in warn if r["state"] == "PASS"), "warn_total": len(warn)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Offline fact checklist scorer")
    ap.add_argument("--run", required=True, help="a toolsmith-publish run directory")
    ap.add_argument("--facts", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    "facts.json"))
    ap.add_argument("--json", help="write the full result here")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.run):
        print(f"run dir not found: {args.run}")
        return 4
    facts = _load_json(args.facts)
    if not facts or "items" not in facts:
        print(f"facts file unusable: {args.facts}")
        return 4
    sv = load_run(args.run)
    if not sv["watchlist"]:
        print(f"no watchlist.json artifact in {args.run} — the run never produced a deliverable")
        return 4

    print(f"evaluator {EVALUATOR_REVISION} · scenario={facts.get('scenario')} · run={os.path.basename(args.run.rstrip('/'))}")
    print(f"  watchlist: {sv['paths']['watchlist']}")
    print(f"  pool     : {sv['paths']['pool'] or '(absent)'}")
    res = score(sv, facts, verbose=args.verbose)
    print(f"SCORE scenario={facts.get('scenario')} facts {res['ok']}/{res['total']} "
          f"warn {res['warn_ok']}/{res['warn_total']} -> "
          f"{'PASS' if not res['fails'] else 'FAIL'}")
    if res["fails"]:
        print("  failed:", ", ".join(res["fails"]))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"revision": EVALUATOR_REVISION, "run": args.run,
                       "watchlist": sv["paths"]["watchlist"], **res}, f,
                      ensure_ascii=False, indent=1)
    return 0 if not res["fails"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
