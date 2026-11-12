#!/usr/bin/env python3
"""Fail-closed validator for the delivered card list.

Run this **before** ``present_artifact``. It checks the things a human reviewer would
otherwise have to eyeball, and it checks them against the pool rather than against the
plan, so a card cannot be self-consistent and still fabricated.

Exit codes: 0 = clean, 3 = at least one FAIL (details on stdout).

Checks
  1. envelope shape, ``count`` == len(cards), **at most 10 cards per bucket** (30 total)
  2. every card has a non-empty ``title`` / ``summary`` / ``why``, and ``why`` earns its
     place: it must reach ``MIN_WHY_CHARS`` and not be a re-wrap of ``summary``
     -- the field is supposed to say what the result *means*, not repeat what was printed
  3. ``esid`` exists in the pool (no invented records)
  4. ``bucket`` is one of early|pivotal|failed
  5. ``lba`` is a real boolean and ``manual`` is true/false/null -- both must match
     the pool row (``manual`` is null on the platform, where ``featured`` cannot be
     selected; a card may not upgrade that to a claim)
  6. no placeholder text leaked (TODO/XXX/None/nan/{}/$VAR)
  7. ``summary`` carries at least one unit-bearing number
  8. every ``%`` / ``mo`` / ``HR`` / ``ORR`` figure in summary+why appears in that
     record's own text -- the anti-fabrication gate
  9. list size is within a sane band for a reading list
 10. ``score`` is a real 0-100 integer and ``score_parts`` sums to it -- the score
     is the reviewer's judgement, so this gate checks self-consistency, not merit
 11. ``coverage_notes`` states the two honest limits (``data_type`` undetermined,
     abstracts without p/HR) -- the JSON is what gets read next month, so a limit
     that lives only in the chat reply is a limit nobody will see
 12. ``listed_company`` is present on every card (``null`` when the sponsor is not
     listed or could not be verified) and, when present, carries name+ticker+
     exchange+a resolvable source URL -- identity, no price: v0.9 removed the quote
     fields because a meeting abstract's readout is not separable from the ticker's
     sector beta, so a per-card percentage was beta dressed as signal
 13. no price claim survives anywhere -- ``stock``, ``reaction``, ``change_pct``,
     ``excess_pct`` on the card or under ``listed_company`` all fail. v0.9 deleted the
     quote layer deliberately; this is the gate that keeps it deleted
 14. a card whose esid is *not* in the machine pools is only legal when it was
     promoted by the web-curation step (``promoted == "web"``); it is then verified
     against ``work/rows.json`` instead, since promotion exists precisely to reach
     records the mechanical screen cut
"""

from __future__ import annotations

from collections import Counter

# The rubric from references/review-protocol.md §2.5. These are *ceilings*, not
# weights: the reviewer decides how much of each to award, and the only thing
# checked mechanically is that the parts add up to the total they claimed.
# v0.7: the machine pools feed a 15-per-bucket shortlist, then the web-curation step
# cuts to 10. The cap lives here because an uncapped list stops being a reading list.
PER_BUCKET_CAP = 10
TOTAL_CAP = 30
# A "why" that is shorter than this is a label, not a judgement. 60 Chinese chars is
# roughly two sentences -- enough for "unmet need -> what this readout changes".
MIN_WHY_CHARS = 60
LISTED_FIELDS = ("name", "ticker", "exchange", "source_url")
# v0.8: `09966.HK` + `exchange=HKEX` prints one fact twice; the ticker is the bare code,
# the exchange field is the market, and a tool keyed on (market, code) can only match that.
MARKET_SUFFIXES = (".HK", ".SH", ".SS", ".SZ", ".T", ".L", ".DE", ".PA", ".AS", ".SW")
PROMOTE_REASONS = ("web",)
# What a regression would look like. Kept as a literal list rather than a schema check
# because the point is to catch the *field coming back*, whatever shape it has.
PRICE_KEYS = ("stock", "reaction", "change_pct", "excess_pct", "bench_change_pct",
              "price_source")
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
from typing import Any, Dict, List, Optional, Tuple

try:  # same directory; the CLI runs from scripts/
    import triage
except ImportError:  # pragma: no cover - packaged imports
    triage = None  # type: ignore[assignment]

BUCKETS = ("early", "pivotal", "failed")
PLACEHOLDERS = ("TODO", "TBD", "XXX", "FIXME", "None", "nan", "{{", "}}", "占位")

# Word-like placeholders must match as whole tokens. Substring matching flagged
# "mainte**nan**ce" and "fi**nan**ce" as leaked "nan", which would fail a perfectly
# good card -- a false positive here is worse than a missed one, because the gate
# is fail-closed and stops the whole run.
_WORD_PLACEHOLDERS = {ph for ph in PLACEHOLDERS if ph.replace("_", "").isalnum()}


def leaf_text(value: Any) -> str:
    """All scalar strings inside a card, never the JSON punctuation around them.

    Scanning ``json.dumps(card)`` for ``}}`` flags every card whose last key is a
    nested object -- i.e. the well-formed case. Placeholders live in leaves.
    """
    if isinstance(value, dict):
        return "\n".join(leaf_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return "\n".join(leaf_text(v) for v in value)
    if value is None or isinstance(value, bool):
        return ""
    return str(value)


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
FIGURE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|mo|months?|个?月)", re.I)


def load_pool(path: str) -> Dict[str, Dict[str, Any]]:
    pool = json.load(open(path, encoding="utf-8"))
    by_esid: Dict[str, Dict[str, Any]] = {}
    for b in BUCKETS:
        for item in pool["pools"][b]["items"]:
            esid = item.get("esid")
            if esid:
                by_esid[str(esid)] = dict(item, _bucket=b)
    return by_esid


def load_rows(path: str) -> Dict[str, Dict[str, Any]]:
    """Raw workspace rows, flattened exactly like ``triage.py`` does.

    Needed only for promoted cards: ``bucket_of``/``excluded_reason`` deliberately cut
    ~500 rows out of the pools, and the web step is allowed to bring one back.
    """
    payload = json.load(open(path, encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    out: Dict[str, Dict[str, Any]] = {}
    for raw in rows or []:
        item = triage.flat_row(raw) if any(str(k).startswith(triage.PREFIXES) for k in raw) else dict(raw)
        esid = item.get("esid") or item.get("_id")
        if esid:
            out[str(esid)] = item
    return out


def record_text(item: Dict[str, Any]) -> str:
    """Everything the record itself claims, for the number-traceability check."""
    parts = [item.get("results"), item.get("results_text"), item.get("study_results"),
             item.get("key_evidence"), item.get("summary"), item.get("background"),
             item.get("primary_endpoint"), item.get("abstract_text")]
    flat: List[str] = []
    for p in parts:
        if isinstance(p, list):
            flat.extend(str(x) for x in p)
        elif p:
            flat.append(str(p))
    return " ".join(flat)


def check(payload: Dict[str, Any], by_esid: Dict[str, Dict[str, Any]],
          by_rows: Optional[Dict[str, Dict[str, Any]]] = None,
          ) -> Tuple[List[str], List[str]]:
    fails: List[str] = []
    notes: List[str] = []
    cards = payload.get("cards")
    if not isinstance(cards, list):
        return ["envelope: `cards` is not a list"], notes
    if payload.get("count") != len(cards):
        fails.append(f"envelope: count={payload.get('count')} != len(cards)={len(cards)}")
    if not payload.get("conference"):
        fails.append("envelope: missing conference")
    if not 10 <= len(cards) <= TOTAL_CAP:
        fails.append(f"size: {len(cards)} cards (expected a 10-{TOTAL_CAP} item reading list)")
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
        if not esid:
            fails.append(f"{tag}: empty esid")
            continue
        if esid in seen:
            fails.append(f"{tag}: duplicate esid")
        seen.add(esid)
        item = by_esid.get(esid)
        origin = "pool"
        if item is None and by_rows:
            item = by_rows.get(esid)
            origin = "rows"
        if item is None:
            fails.append(f"{tag}: esid not in pool")
            continue
        promoted = card.get("promoted")
        if promoted is not None and promoted not in PROMOTE_REASONS:
            fails.append(f"{tag}: promoted={promoted!r} not in {list(PROMOTE_REASONS)}")
        if origin == "rows":
            if promoted not in PROMOTE_REASONS:
                fails.append(f"{tag}: esid is outside the machine pools and was not "
                             f"promoted -- set promoted='web' and say why in `why`")
                continue
            notes.append(f"{tag}: promoted from rows.json (outside the candidate pools)")
        for key in ("title", "summary", "why"):
            if not str(card.get(key) or "").strip():
                fails.append(f"{tag}: missing {key}")
        if card.get("bucket") not in BUCKETS:
            fails.append(f"{tag}: bad bucket {card.get('bucket')!r}")
        elif item.get("_bucket") and card["bucket"] != item.get("_bucket"):
            notes.append(f"{tag}: bucket re-judged {item.get('_bucket')} -> {card['bucket']}")
        why = " ".join(str(card.get("why") or "").split())
        summary = " ".join(str(card.get("summary") or "").split())
        if why and len(why) < MIN_WHY_CHARS:
            fails.append(f"{tag}: why is {len(why)} chars (< {MIN_WHY_CHARS}) -- it must "
                         f"say what the result means, not label it")
        if why and summary and (summary[:20] in why or why[:20] in summary):
            fails.append(f"{tag}: why repeats summary -- state the value, not the numbers")
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
        body = leaf_text(card)
        for ph in placeholder_hits(body):
            fails.append(f"{tag}: placeholder {ph!r} leaked into the card")
        if not UNIT_NUM.search(str(card.get("summary") or "")):
            fails.append(f"{tag}: summary has no unit-bearing number")
        text = record_text(item)
        # Compare values, not substrings. `"44" in text` was true whenever the abstract
        # said 44.7% or n=144, so "12 个月 PFS 率 44% vs 24%" (a press-release figure the
        # abstract never printed) sailed through this gate while the offline fact layer
        # caught it. The two must agree, and this is the weaker side by design: the
        # delivered JSON has to fail before it is presented, not after.
        src_nums = {float(m.group(0)) for m in re.finditer(r"\d+(?:\.\d+)?", text)}
        for fig in sorted(set(FIGURE.findall(f"{card.get('summary')} {card.get('why')}"))):
            try:
                num = float(re.sub(r"[^\d.]", "", fig))
            except ValueError:
                continue
            if num not in src_nums:
                fails.append(f"{tag}: figure {fig!r} not found in the record text")
        for key in PRICE_KEYS:
            if key in card and card.get(key) not in (None, "", {}):
                fails.append(f"{tag}: {key} is a price field -- v0.9 removed the quote "
                             f"layer; the card is about the readout")
        # Presence of the key is the contract, not presence of a value: `null` means
        # "checked and not listed / not verifiable". A missing key silently means the
        # same thing without anybody having looked, which is the failure mode this
        # field exists to prevent.
        if "listed_company" not in card:
            fails.append(f"{tag}: missing listed_company (null when the sponsor is not "
                         f"listed or cannot be verified)")
            continue
        company = card["listed_company"]
        if company is None:
            continue
        if not isinstance(company, dict):
            fails.append(f"{tag}: listed_company must be an object or null")
            continue
        for key in LISTED_FIELDS:
            if not str(company.get(key) or "").strip():
                fails.append(f"{tag}: listed_company.{key} missing")
        url = str(company.get("source_url") or "")
        if url and not re.match(r"^https?://\S+$", url):
            fails.append(f"{tag}: listed_company.source_url is not an http(s) URL: {url!r}")
        ticker = str(company.get("ticker") or "")
        if ticker and not re.search(r"[0-9A-Za-z]", ticker):
            fails.append(f"{tag}: listed_company.ticker={ticker!r} has no alphanumerics")
        for key in PRICE_KEYS:
            if key in company and company.get(key) not in (None, "", {}):
                fails.append(f"{tag}: listed_company.{key} is a price field -- v0.9 keeps "
                             f"identity only; a meeting-day move is sector beta")
        hit = next((sfx for sfx in MARKET_SUFFIXES if ticker.upper().endswith(sfx)), None)
        if hit:
            fails.append(f"{tag}: listed_company.ticker={ticker!r} carries the market suffix "
                         f"{hit} while exchange={company.get('exchange')!r} -- the ticker holds "
                         f"the bare code, the exchange field holds the market")
    return fails, notes


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cards", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--rows", help="work/rows.json -- required only when a card was "
                                   "promoted from outside the machine pools")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    payload = json.load(open(args.cards, encoding="utf-8"))
    by_esid = load_pool(args.pool)
    by_rows = load_rows(args.rows) if args.rows else None
    fails, notes = check(payload, by_esid, by_rows)

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
