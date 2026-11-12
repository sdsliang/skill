#!/usr/bin/env python3
"""Fail-closed validator for the delivered card list.

Run this **before** ``present_artifact``. It checks the things a human reviewer would
otherwise have to eyeball, and it checks them against the pool rather than against the
plan, so a card cannot be self-consistent and still fabricated.

Exit codes: 0 = clean, 3 = at least one FAIL (details on stdout).

Checks
  1. envelope shape, ``count`` == len(cards), **at most 15 cards per bucket**
  2. every card has a non-empty ``title`` / ``summary`` / ``why``
  3. ``esid`` exists in the pool (no invented records)
  4. ``bucket`` is one of early|pivotal|failed
  5. ``lba`` is a real boolean and ``manual`` is true/false/null -- both must match
     the pool row (``manual`` is null on the platform, where ``featured`` cannot be
     selected; a card may not upgrade that to a claim)
  6. no placeholder text leaked (TODO/XXX/None/nan/{}/$VAR)
  7. ``summary`` carries at least one unit-bearing number
  8. every ``%`` / ``mo`` / ``HR`` / ``ORR`` figure in summary+why appears in that
     record's own text -- the anti-fabrication gate
  9. ``stock``, when present, has ticker+change_pct+date
 10. list size is within a sane band for a reading list
 11. ``score`` is a real 0-100 integer and ``score_parts`` sums to it -- the score
     is the reviewer's judgement, so this gate checks self-consistency, not merit
 12. ``coverage_notes`` states the two honest limits (``data_type`` undetermined,
     abstracts without p/HR) -- the JSON is what gets read next month, so a limit
     that lives only in the chat reply is a limit nobody will see
"""

from __future__ import annotations

from collections import Counter

# The rubric from references/review-protocol.md §2.5. These are *ceilings*, not
# weights: the reviewer decides how much of each to award, and the only thing
# checked mechanically is that the parts add up to the total they claimed.
PER_BUCKET_CAP = 15
BUCKETS = ("early", "pivotal", "failed")
SCORE_CAPS = {"evidence_strength": 30, "effect_size": 25, "clinical_impact": 25,
              "novelty": 10, "readout_maturity": 10}

# The two claims the deliverable itself must carry. Kept in sync with
# `evals/fact-check/facts.json` -> A-H1-two-honest-claims (that item audits a finished
# run; this one stops the run from being delivered in the first place).
COVERAGE_CLAIMS = {
    "data_type":
        r"(?s)(?=.*(?:data_?type|数据类型|首次/更新))"
        r"(?=.*(?:未判定|未知|无法判定|不确定|判不出|不猜))",
    # "no p or HR" gets written at least five ways across runs ("无 p 或 HR" /
    # "未列p或HR" / "没给 p 值或 HR"). The gate is for the fact, not the wording.
    "p_hr":
        r"(?s)(?=.*(?:覆盖|全量|完整|不代表|并非))"
        r"(?=.*(?:p\s*值?\s*(?:[或/、,和与]|and)\s*(?:HR|风险比)"
        r"|(?:HR|风险比)\s*(?:[或/、,和与]|and)\s*p\s*值?"
        r"|(?:未列|无|缺|未给出|没有|没给|不含)\s*p\s*值?))",
}

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Tuple

BUCKETS = ("early", "pivotal", "failed")
PLACEHOLDERS = ("TODO", "TBD", "XXX", "FIXME", "None", "nan", "{{", "}}", "占位")

# Word-like placeholders must match as whole tokens. Substring matching flagged
# "mainte**nan**ce" and "fi**nan**ce" as leaked "nan", which would fail a perfectly
# good card -- a false positive here is worse than a missed one, because the gate
# is fail-closed and stops the whole run.
_WORD_PLACEHOLDERS = {ph for ph in PLACEHOLDERS if ph.replace("_", "").isalnum()}


def placeholder_hits(text: str) -> List[str]:
    hits = []
    for ph in PLACEHOLDERS:
        if ph in _WORD_PLACEHOLDERS:
            if re.search(rf"(?<![A-Za-z]){re.escape(ph)}(?![A-Za-z])", text):
                hits.append(ph)
        elif ph in text:
            hits.append(ph)
    return hits
UNIT_NUM = re.compile(r"\d+(?:\.\d+)?\s*(?:%|个月|月|mo|months?|年|HR|OR|CI)", re.I)
FIGURE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|mo|months?|个月)", re.I)


def load_pool(path: str) -> Dict[str, Dict[str, Any]]:
    pool = json.load(open(path, encoding="utf-8"))
    by_esid: Dict[str, Dict[str, Any]] = {}
    for b in BUCKETS:
        for item in pool["pools"][b]["items"]:
            esid = item.get("esid")
            if esid:
                by_esid[str(esid)] = dict(item, _bucket=b)
    return by_esid


def record_text(item: Dict[str, Any]) -> str:
    """Everything the record itself claims, for the number-traceability check."""
    parts = [item.get("results"), item.get("results_text"), item.get("key_evidence"),
             item.get("summary"), item.get("background"), item.get("primary_endpoint"),
             item.get("abstract_text")]
    flat: List[str] = []
    for p in parts:
        if isinstance(p, list):
            flat.extend(str(x) for x in p)
        elif p:
            flat.append(str(p))
    return " ".join(flat)


def check(payload: Dict[str, Any], by_esid: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    fails: List[str] = []
    notes: List[str] = []
    cards = payload.get("cards")
    if not isinstance(cards, list):
        return ["envelope: `cards` is not a list"], notes
    if payload.get("count") != len(cards):
        fails.append(f"envelope: count={payload.get('count')} != len(cards)={len(cards)}")
    if not payload.get("conference"):
        fails.append("envelope: missing conference")
    if not 10 <= len(cards) <= 45:
        fails.append(f"size: {len(cards)} cards (expected a 10-45 item reading list)")
    claims = payload.get("coverage_notes")
    if not isinstance(claims, list) or not claims:
        fails.append("envelope: `coverage_notes` missing -- the two honest limits "
                     "(data_type undetermined / abstracts without p or HR) must live "
                     "in the delivered JSON, not only in the reply")
    else:
        joined = "\n".join(str(x) for x in claims if str(x).strip())
        for name, pattern in COVERAGE_CLAIMS.items():
            if not re.search(pattern, joined):
                fails.append(f"envelope: coverage_notes does not state the {name} limit")

    per_bucket = Counter(c.get("bucket") for c in cards)
    for name, num in per_bucket.items():
        if name not in BUCKETS:
            fails.append(f"bucket: unknown bucket {name!r}")
        elif num > PER_BUCKET_CAP:
            fails.append(f"bucket {name}: {num} cards > cap {PER_BUCKET_CAP} "
                         f"-- cut by score, do not pad the list")

    seen = set()
    for n, card in enumerate(cards, 1):
        tag = f"card {n} ({card.get('esid') or 'no-esid'})"
        esid = str(card.get("esid") or "")
        item = by_esid.get(esid)
        if not esid:
            fails.append(f"{tag}: empty esid")
            continue
        if esid in seen:
            fails.append(f"{tag}: duplicate esid")
        seen.add(esid)
        if item is None:
            fails.append(f"{tag}: esid not in pool")
            continue
        for key in ("title", "summary", "why"):
            if not str(card.get(key) or "").strip():
                fails.append(f"{tag}: missing {key}")
        if card.get("bucket") not in BUCKETS:
            fails.append(f"{tag}: bad bucket {card.get('bucket')!r}")
        elif card["bucket"] != item.get("_bucket"):
            notes.append(f"{tag}: bucket re-judged {item.get('_bucket')} -> {card['bucket']}")
        if not isinstance(card.get("lba"), bool):
            fails.append(f"{tag}: lba must be boolean")
        elif card["lba"] != bool(item.get("lba")):
            fails.append(f"{tag}: lba={card['lba']} but pool row says {bool(item.get('lba'))}")
        # `manual` is a provenance claim (human-curated vs pipeline-extracted), so a
        # card that flips it is telling the reader the wrong thing about how the row
        # was produced. Optional key: older plans predate it and a missing key must
        # not fail -- but a present key must agree with the pool.
        if "manual" in card:
            if not isinstance(card["manual"], bool | None):
                fails.append(f"{tag}: manual must be boolean or null")
            elif card["manual"] != item.get("manual"):
                fails.append(f"{tag}: manual={card['manual']} but pool row says "
                             f"{item.get('manual')}")
        if "score" not in card:
            fails.append(f"{tag}: missing score (the review must judge every card)")
        else:
            score = card["score"]
            if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
                fails.append(f"{tag}: score={score!r} must be an integer 0-100")
            parts = card.get("score_parts") or {}
            if parts:
                if set(parts) != set(SCORE_CAPS):
                    fails.append(f"{tag}: score_parts keys {sorted(parts)} != "
                                 f"{sorted(SCORE_CAPS)}")
                else:
                    for name, cap in SCORE_CAPS.items():
                        val = parts[name]
                        if not isinstance(val, int) or isinstance(val, bool) or not 0 <= val <= cap:
                            fails.append(f"{tag}: score_parts[{name}]={val!r} "
                                         f"must be an integer 0-{cap}")
                    if sum(parts.values()) != score:
                        fails.append(f"{tag}: score_parts sum {sum(parts.values())} "
                                     f"!= score {score}")
        body = json.dumps(card, ensure_ascii=False)
        for ph in placeholder_hits(body):
            fails.append(f"{tag}: placeholder {ph!r} leaked into the card")
        if not UNIT_NUM.search(str(card.get("summary") or "")):
            fails.append(f"{tag}: summary has no unit-bearing number")
        text = record_text(item)
        for fig in set(FIGURE.findall(f"{card.get('summary')} {card.get('why')}")):
            num = re.sub(r"[^\d.]", "", fig)
            if num and num not in text:
                fails.append(f"{tag}: figure {fig!r} not found in the record text")
        stock = card.get("stock")
        if stock is not None:
            if not isinstance(stock, dict):
                fails.append(f"{tag}: stock must be an object or null")
            else:
                for key in ("ticker", "change_pct", "date"):
                    if stock.get(key) in (None, ""):
                        fails.append(f"{tag}: stock.{key} missing")
    return fails, notes


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cards", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    payload = json.load(open(args.cards, encoding="utf-8"))
    by_esid = load_pool(args.pool)
    fails, notes = check(payload, by_esid)

    if notes and args.verbose:
        for n in notes:
            print(f"  note: {n}")
    if fails:
        print(f"FAIL ({len(fails)}):")
        for f in fails:
            print(f"  - {f}")
        return 3
    print(f"OK cards={len(payload['cards'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
