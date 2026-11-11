#!/usr/bin/env python3
"""Render the deliverable: a JSON list of recommended-reading cards.

This is the skill's primary output. One card per recommendation, deliberately
small -- a reader should be able to decide from ``title`` + ``summary`` + ``why``
whether to open the abstract, without a table.

Card shape::

    {
      "esid":         "24_37_p_...",      # the clinical-result record id
      "abstract_id":  null,               # conference abstract number (null on TS)
      "lba":          true,               # late-breaking tag
      "manual":       true,               # human-curated? null = unknown (platform can't fetch featured)
      "bucket":       "pivotal",          # early | pivotal | failed
      "title":        "...",              # abstract title, verbatim
      "summary":      "...",              # what was reported, numbers included
      "why":          "...",              # why it is worth reading
      "drug": "...", "target": "...", "indication": "...", "phase": "Phase III",
      "stock": null                       # optional {ticker, change_pct, date, ...}
    }

Zero third-party dependencies.

The script never invents content: ``title`` comes from the record, ``summary`` /
``why`` come from the plan file written by the reviewer, and ``stock`` only from
``--quotes``. Anything missing is reported, not filled.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

BUCKETS = ("early", "pivotal", "failed")


def load_pool(path: str) -> Dict[str, Dict[str, Any]]:
    """Index pool items by esid, tagging each with the bucket it came from."""
    pool = json.load(open(path, encoding="utf-8"))
    by_esid: Dict[str, Dict[str, Any]] = {}
    for b in BUCKETS:
        for item in pool["pools"][b]["items"]:
            if item.get("esid"):
                by_esid[str(item["esid"])] = dict(item, _bucket=b)
    return by_esid


def load_quotes(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """``{"<esid>": {ticker, change_pct, date, ...}}`` -- optional sidecar."""
    if not path:
        return {}
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict) and "quotes" in data:
        data = data["quotes"]
    if not isinstance(data, dict):
        raise SystemExit("--quotes must be {esid: {...}} or {\"quotes\": {...}}")
    return {str(k): v for k, v in data.items()}


def build_cards(plan: Dict[str, Any], by_esid: Dict[str, Dict[str, Any]],
                quotes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    problems: List[str] = []
    for spec in plan.get("cards") or []:
        esid = str(spec.get("esid") or "")
        item = by_esid.get(esid)
        if item is None:
            problems.append(f"{esid or '<empty esid>'}: not in pool")
            continue
        for key in ("title", "summary", "why"):
            if not (spec.get(key) or "").strip():
                problems.append(f"{esid}: missing {key}")
        card = {
            "esid": esid,
            "abstract_id": spec.get("abstract_id") or item.get("abstract_id"),
            "lba": bool(item.get("lba") or spec.get("lba")),
            # Tri-state on purpose: `featured` is not selectable on the platform, so
            # "unknown" is the honest value and `false` would be a fabrication.
            "manual": (item["manual"] if "manual" in item else spec.get("manual")),
            "bucket": spec.get("bucket") or item.get("_bucket"),
            "tag": spec.get("tag") or _auto_tag(item),
            "title": spec.get("title") or item.get("title") or "",
            "summary": spec.get("summary") or "",
            "why": spec.get("why") or "",
            "drug": spec.get("drug") or item.get("drug") or "",
            "target": spec.get("target") or item.get("target") or "",
            "indication": spec.get("indication")
            or ", ".join((item.get("indication") or [])[:2]),
            "phase": item.get("phase") or "",
            "presentation": item.get("presentation") or "",
            "stock": quotes.get(esid),
        }
        cards.append(card)
    if problems:
        for p in problems:
            sys.stderr.write(f"  ! {p}\n")
        raise SystemExit(f"{len(problems)} card problem(s); fix the plan")
    return cards


def _auto_tag(item: Dict[str, Any]) -> str:
    """Short read-slot label. Never invents one for an unmarked record.

    Only ``lba`` feeds the slot label. ``featured`` is deliberately excluded: it
    marks human- vs machine-produced rows, so "精选" would be a fabricated claim
    about editorial importance.
    """
    return "LBA" if item.get("lba") else ""


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True, help="triage pool.json")
    ap.add_argument("--plan", required=True, help="cards plan JSON {conference, cards:[...]}")
    ap.add_argument("--out", required=True, help="output JSON path")
    ap.add_argument("--quotes", help="optional {esid: {ticker, change_pct, ...}}")
    ap.add_argument("--pretty", action="store_true", help="indent the output")
    args = ap.parse_args(argv)

    plan = json.load(open(args.plan, encoding="utf-8"))
    by_esid = load_pool(args.pool)
    quotes = load_quotes(args.quotes)
    cards = build_cards(plan, by_esid, quotes)

    missing_quotes = [c["esid"] for c in cards if not c["stock"]]
    payload = {
        "conference": plan.get("conference"),
        "count": len(cards),
        "cards": cards,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False,
                  indent=2 if args.pretty else None)
        fh.write("\n")
    lba = sum(1 for c in cards if c["lba"])
    manual = sum(1 for c in cards if c.get("manual") is True)
    unknown = sum(1 for c in cards if c.get("manual") is None)
    print(f"cards {len(cards)} (lba {lba} manual {manual} unknown {unknown}) -> {args.out}")
    for b in BUCKETS:
        print(f"  {b}: {sum(1 for c in cards if c['bucket'] == b)}")
    if quotes:
        print(f"  stock attached: {len(cards) - len(missing_quotes)}/{len(cards)}")
    else:
        print("  stock: no --quotes given (field is null)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
