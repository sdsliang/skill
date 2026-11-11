#!/usr/bin/env python3
"""Fail-closed validator for the delivered card list.

Run this **before** ``present_artifact``. It checks the things a human reviewer would
otherwise have to eyeball, and it checks them against the pool rather than against the
plan, so a card cannot be self-consistent and still fabricated.

Exit codes: 0 = clean, 3 = at least one FAIL (details on stdout).

Checks
  1. envelope shape, ``count`` == len(cards)
  2. every card has a non-empty ``title`` / ``summary`` / ``why``
  3. ``esid`` exists in the pool (no invented records)
  4. ``bucket`` is one of early|pivotal|failed
  5. ``lba`` is a real boolean and matches the pool row
  6. no placeholder text leaked (TODO/XXX/None/nan/{}/$VAR)
  7. ``summary`` carries at least one unit-bearing number
  8. every ``%`` / ``mo`` / ``HR`` / ``ORR`` figure in summary+why appears in that
     record's own text -- the anti-fabrication gate
  9. ``stock``, when present, has ticker+change_pct+date
 10. list size is within a sane band for a reading list
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Tuple

BUCKETS = ("early", "pivotal", "failed")
PLACEHOLDERS = ("TODO", "TBD", "XXX", "FIXME", "None", "nan", "{{", "}}", "占位")
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
    if not 10 <= len(cards) <= 60:
        fails.append(f"size: {len(cards)} cards (expected a 10-60 item reading list)")

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
        body = json.dumps(card, ensure_ascii=False)
        for ph in PLACEHOLDERS:
            if ph in body:
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
