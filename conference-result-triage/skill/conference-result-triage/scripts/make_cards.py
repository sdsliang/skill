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
      "score":        78,                 # the reviewer's own 0-100 judgement (Step 4), not computed here
      "score_parts":  {"evidence_strength": 26, "effect_size": 22,
                       "clinical_impact": 20, "novelty": 4, "readout_maturity": 6},
      "bucket":       "pivotal",          # early | pivotal | failed
      "title":        "...",              # abstract title, verbatim
      "summary":      "...",              # what was reported, numbers included
      "why":          "...",              # what the result means (>=60 chars, v0.7)
      "listed_company": {"name": "...", "ticker": "...", "exchange": "...",
                         "source_url": "https://..."},  # or null
      "promoted":     "web",              # only for cards the web step pulled in
      "drug": "...", "target": "...", "indication": "...", "phase": "Phase III"
    }

Zero third-party dependencies.

The script never invents content: ``title`` comes from the record, ``summary`` /
``why`` come from the plan file written by the reviewer. Anything missing is
reported, not filled.

v0.9 dropped the quote fields (``stock`` / ``listed_company.reaction``) entirely:
a card is about the readout, and a per-abstract price move on a conference day is
mostly the sector's own beta -- 18 of 20 quotes landed inside +/-0.6% of their
benchmark, i.e. the number said nothing about the abstract.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
import sys
from typing import Any, Dict, List, Optional, Tuple

BUCKETS = ("early", "pivotal", "failed")
PROMOTE_REASONS = ("web",)

try:  # same directory; the CLI runs from scripts/
    import triage
except ImportError:  # pragma: no cover
    triage = None  # type: ignore[assignment]


def load_pool(path: str) -> Dict[str, Dict[str, Any]]:
    """Index pool items by esid, tagging each with the bucket it came from."""
    pool = json.load(open(path, encoding="utf-8"))
    by_esid: Dict[str, Dict[str, Any]] = {}
    for b in BUCKETS:
        for item in pool["pools"][b]["items"]:
            if item.get("esid"):
                by_esid[str(item["esid"])] = dict(item, _bucket=b)
    return by_esid


def load_rows(path: str) -> Dict[str, Dict[str, Any]]:
    """``work/rows.json`` flattened like ``triage.py`` does.

    Only needed for web-promoted cards: they exist in the workspace but were cut out
    of the pools by the mechanical screen, and the numbers on the card still have to
    come from that row's own text.
    """
    payload = json.load(open(path, encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    out: Dict[str, Dict[str, Any]] = {}
    for raw in rows or []:
        item = (triage.flat_row(raw)
                if triage and any(str(k).startswith(triage.PREFIXES) for k in raw)
                else dict(raw))
        esid = item.get("esid") or item.get("_id")
        if esid:
            out[str(esid)] = item
    return out


def build_cards(plan: Dict[str, Any], by_esid: Dict[str, Dict[str, Any]],
                by_rows: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    problems: List[str] = []
    for spec in plan.get("cards") or []:
        esid = str(spec.get("esid") or "")
        item = by_esid.get(esid)
        if item is None and by_rows is not None:
            # A promoted card may live outside the pools -- but only with the marker,
            # otherwise "not in pool" is the honest answer.
            if spec.get("promoted") not in PROMOTE_REASONS:
                problems.append(f"{esid or '<empty esid>'}: not in pool "
                                f"(set promoted='web' if the web step pulled it in)")
                continue
            item = by_rows.get(esid)
            if item is None:
                problems.append(f"{esid}: promoted but not found in --rows")
                continue
        if item is None:
            problems.append(f"{esid or '<empty esid>'}: not in pool")
            continue
        for key in ("title", "summary", "why"):
            if not (spec.get(key) or "").strip():
                problems.append(f"{esid}: missing {key}")
        # The score belongs to whoever read the abstract; this script only carries
        # it through. A plan without one is a plan that never judged the record,
        # so it fails here rather than shipping an unranked list.
        judged = spec.get("score", item.get("score"))
        if not isinstance(judged, int) or not 0 <= judged <= 100:
            problems.append(f"{esid}: score must be an integer 0-100 from the review")
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
            "score": judged,
            "score_parts": spec.get("score_parts") or item.get("score_parts") or {},
            "drug": spec.get("drug") or item.get("drug") or "",
            "target": spec.get("target") or item.get("target") or "",
            "indication": spec.get("indication")
            or ", ".join((item.get("indication") or [])[:2]),
            "phase": item.get("phase") or "",
            # v0.10: non-oncology records rarely carry a phase; triage places
            # them by study design and records the basis here, so the card can
            # print "期别未标注（按设计判定：随机化对照）" instead of a blank.
            "phase_inferred": item.get("phase_inferred") or None,
            "presentation": item.get("presentation") or "",
        }
        # Both keys are carried only when the plan supplies them: an absent
        # `listed_company` must reach `check_cards.py` as "missing" rather than
        # silently defaulting to null, which is the value that means "checked".
        if "listed_company" in spec:
            card["listed_company"] = spec["listed_company"]
        if spec.get("promoted"):
            card["promoted"] = spec["promoted"]
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
    ap.add_argument("--rows", help="work/rows.json -- needed only for promoted cards")
    ap.add_argument("--pretty", action="store_true", help="indent the output")
    args = ap.parse_args(argv)

    plan = json.load(open(args.plan, encoding="utf-8"))
    by_esid = load_pool(args.pool)
    cards = build_cards(plan, by_esid, load_rows(args.rows) if args.rows else None)

    payload = {
        "conference": plan.get("conference"),
        "count": len(cards),
        "cards": cards,
    }
    # v0.11: the envelope carries two statements that belong to the deliverable, not to
    # the chat reply -- the honest limits, and the ledger of every skip that overrode the
    # judgement ranking. Passing them through means the model states them once, in the
    # plan, instead of hand-editing the rendered JSON afterwards (which is how v0.5/v0.6
    # shipped `coverage.boundary` and failed A-H1 twice).
    if plan.get("coverage_notes"):
        payload["coverage_notes"] = plan["coverage_notes"]
    if plan.get("editorial_overrides"):
        payload["editorial_overrides"] = plan["editorial_overrides"]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False,
                  indent=2 if args.pretty else None)
        fh.write("\n")
    lba = sum(1 for c in cards if c["lba"])
    manual = sum(1 for c in cards if c.get("manual") is True)
    unknown = sum(1 for c in cards if c.get("manual") is None)
    buckets = Counter(c["bucket"] for c in cards)
    spread = " ".join(f"{b}={buckets.get(b, 0)}" for b in ("early", "pivotal", "failed"))
    print(f"cards {len(cards)} ({spread}; lba {lba} manual {manual} unknown {unknown}) -> {args.out}")
    for b in BUCKETS:
        print(f"  {b}: {sum(1 for c in cards if c['bucket'] == b)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
