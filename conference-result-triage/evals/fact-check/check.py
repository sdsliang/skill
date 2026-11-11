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

EVALUATOR_REVISION = "2026-11-11-r1"

# Presidential / late-breaking trials the X discussion concentrated on. Used by the
# heat-coverage item, which is `warn`: the list must never be bent toward what was
# talked about, but a total miss is worth printing.
HEAT_TRIALS = ["DeLLphi-305", "SAFFRON", "INTerpath-001", "VOLGA", "KRASCENDO-1",
               "CheckMate 8HW", "CLARITY-Gastric01", "OptiTROP-Lung06", "PANKU-Lung01",
               "HERON-Lung01", "TroFuse-005", "NEOTORCH"]

BUCKETS = ("early", "pivotal", "failed")
SCORE_CAPS = {"evidence_strength": 30, "effect_size": 25, "clinical_impact": 25,
              "novelty": 10, "readout_maturity": 10}
PER_BUCKET_CAP = 15
NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(%|mo|months?|月|HR|hazard|OR\b|p\s*[=<>]|P\s*[=<>])")


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

    ledger_path = pick("work/slice_counts.json")
    ledger = _load_json(ledger_path) if ledger_path else None

    rows_path = pick("work/rows.json")
    rows = _load_json(rows_path) if rows_path else None
    if isinstance(rows, dict):
        rows = rows.get("rows")

    return {"watchlist": watchlist, "pool": pool, "calls": calls, "reply": reply,
            "slice_counts": ledger if isinstance(ledger, list) else None,
            "rows": rows if isinstance(rows, list) else None,
            "transcript": transcript,
            "paths": {"watchlist": watchlist_path, "pool": pool_path}}


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
    """Every data pull must slice by `esids`; a wide pull truncates silently.

    The pulls are often delegated to a `task` subagent, whose tool calls never reach
    this turn's debug-history. In that case the per-slice ledger `slice_counts.json`
    is the evidence: one dump per slice, every requested id returned.
    """
    ledger = sv.get("slice_counts")
    if ledger:
        n = len(ledger)
        dumps = {x.get("dump") for x in ledger if x.get("dump")}
        complete = all(int(x.get("missing_ids") or 0) == 0 for x in ledger)
        biggest = max((int(x.get("requested_ids") or 0) for x in ledger), default=0)
        ok = (n >= spec.get("min_calls", 7) and len(dumps) == n and complete
              and 0 < biggest <= spec.get("max_slice", 300))
        return ok, (f"{n} slices, {len(dumps)} distinct dumps, missing_ids all zero={complete}, "
                    f"largest slice {biggest} ids")

    q = [c for c in sv["calls"] if "clinical-result-with-params" in str(c["name"])]
    if not q:
        return False, "no query tool call at all"
    sliced = [c for c in q if c["args"].get("esids")]
    wide = [c for c in q if not c["args"].get("esids")]
    biggest = max((len(c["args"].get("esids") or []) for c in sliced), default=0)
    ok = len(sliced) >= spec.get("min_calls", 7) and biggest <= spec.get("max_slice", 300)
    return ok, (f"{len(sliced)} sliced calls (max {biggest} ids), {len(wide)} unsliced; "
                f"need >={spec.get('min_calls', 7)} sliced, max id count <={spec.get('max_slice', 300)}")


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
    over_total = len(cards) > spec.get("total", 45)
    ok = not bad and not over_total
    return ok, f"per-bucket {per}, total {len(cards)}"


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
    """
    if not sv["rows"] or not sv["pool"]:
        return None, "no rows.json / pool.json in the run dir"
    lba_rows = [r for r in sv["rows"]
                if str(r.get("clinical_result_lba") or r.get("lba") or "").strip().upper() == "LBA"]
    if not lba_rows:
        return None, "no lba rows in this corpus"
    pooled = set()
    for bucket in (sv["pool"].get("pools") or {}).values():
        for item in bucket.get("items") or []:
            if item.get("lba"):
                pooled.add(str(item.get("esid")))
    excluded = sv["pool"].get("excluded") or {}
    bad_exc = [k for k in excluded if "前瞻性" in str(k)]
    dropped = [str(r.get("clinical_result_extra_esid") or r.get("_id"))
               for r in lba_rows
               if str(r.get("clinical_result_extra_esid") or r.get("_id")) not in pooled]
    ok = not bad_exc and len(dropped) <= spec.get("allow_dropped", 0)
    return ok, (f"{len(lba_rows)} lba rows in the corpus, {len(pooled)} in the pool, "
                f"{len(dropped)} dropped (e.g. {dropped[:2]}), phase-as-design exclusions={bad_exc}")


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
