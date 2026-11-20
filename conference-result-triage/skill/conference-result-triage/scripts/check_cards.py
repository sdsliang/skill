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
  9. every bucket with candidates carries at least one card, and a list under the
     10-card floor has to declare the shortfall in ``coverage_notes`` (v0.18). A
     thin bucket is fine; a silently empty one is a claim that the conference
     produced nothing there, which is not ours to make by omission
 10. ``score`` is a real 0-100 integer and ``score_parts`` sums to it -- the score
     is the reviewer's judgement, so this gate checks self-consistency, not merit
 11. ``coverage_notes`` states the two honest limits (``data_type`` undetermined,
     abstracts without p/HR) -- the JSON is what gets read next month, so a limit
     that lives only in the chat reply is a limit nobody will see
 12. ``tag`` is a slot label, not a badge: only "" or "LBA". v0.13 stopped rendering
     ``is_recommand`` as a chip -- the flag still decides *placement* (it leads its
     bucket, see rule 16), but a "推荐" chip on a judged list reads as our own
     endorsement of a row the data owner flagged
 13. no market data survives anywhere -- no price (``stock`` / ``reaction`` /
     ``change_pct`` / ``excess_pct``) and no company code (``listed_company`` /
     ``ticker`` / ``exchange``). v0.9 deleted the quote layer, v0.13 deleted the
     ticker: on a conference card the code is read as "how did this trade", the same
     misreading the quote layer caused, so the field is gone and this gate keeps it
     gone -- either shape coming back fails
 14. a card whose esid is *not* in the machine pools is only legal when it was
     promoted by the web-curation step (``promoted == "web"``); it is then verified
     against ``work/rows.json`` instead, since promotion exists precisely to reach
     records the mechanical screen cut
 15. **selection is the top-k of the judgements** (v0.11): inside one bucket you may
     not drop a ``keep`` that scores higher than the lowest card you kept. Every such
     skip has to be declared in ``editorial_overrides`` with a reason, because "why is
     the better-scored trial missing" is the question a reader asks first. Same-score
     ties are free to break either way.
 16. **the data owner's flag is forced** (v0.12): every row with
     ``clinical_result.is_recommand == 是`` must be on the list, and inside one bucket the
     flagged cards must come before the unflagged ones whatever the scores say. This is
     the one rule that outranks the judgement ranking, because it is not our judgement:
     dropping a flagged readout is the failure the flag exists to prevent. ``abstract_id``
     must be printed on every card whose row carries one -- the reader searches the
     abstract book by that number, so an invented or missing one sends them nowhere.
 17. **inside a bucket and flag class, scores never go up** (v0.14). Rule 17 puts the
     flagged cards first; this one says the rest is a descending list. The sort key is
     ``(is_recommand, -score)``, so the grouping is on *both* -- grouping on ``bucket``
     alone would call a flagged 60 above an unflagged 80 "out of order", which is
     exactly the placement rule 16 mandates.
 18. **one trial, at most two cards** (v0.14). A trial that publishes its primary
     result, a subgroup and a safety cut takes three seats without ever changing
     mechanism, so the prose rule "same mechanism, at most two" does not bind it. A
     third seat is legal only when ``editorial_overrides`` declares a reason (>=10
     chars) -- the same ledger as rule 15, not a new back door. Where the rows carry
     no ``trial_abbreviation`` this check reports "nothing to group by" rather than
     passing: an empty surface is not a green light.
 19. **every card names its drug and its target** (v0.16). The result tool has no
     drug/target column: the only structured source is the nested
     ``clinical_result.arms[].drugs[]``, and at 5.9 KB per record it is not pulled at
     conference scale. So ``drug`` / ``target`` are extracted by the reviewer from the
     title/summary/abstract while it writes ``why`` -- and until v0.16 nothing checked
     them: the ADA 2026 run shipped 27/27 cards with both empty, the card face rendered
     ``—``, and the sidebar collapsed to truncated titles while every other gate stayed
     green. A record with no molecular target at all (BCG, metformin) may leave
     ``target`` empty only by declaring it in ``editorial_overrides`` with
     ``field: "target"`` and a reason (>=10 chars): the same ledger, but keyed per
     field, so a selection-skip reason cannot silently cover a blank card face.
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
# v0.18: the floor is a claim about how much reading a conference can sustain, so it
# may only be asked of a corpus that can pay it. ENA 2026 holds 17 records -> 9
# candidates in total; "10 cards" was arithmetically unreachable, and the run that
# told the truth (8 cards, both gaps declared) was failed by the gate, not by the data.
MIN_TOTAL = 10
# A "why" that is shorter than this is a label, not a judgement. 60 Chinese chars is
# roughly two sentences -- enough for "unmet need -> what this readout changes".
MIN_WHY_CHARS = 60
PROMOTE_REASONS = ("web",)
# What a regression would look like. Kept as a literal list rather than a schema check
# because the point is to catch the *field coming back*, whatever shape it has.
PRICE_KEYS = ("stock", "reaction", "change_pct", "excess_pct", "bench_change_pct",
              "price_source")
# v0.13 removed the identity layer for the same reason the quote layer went in v0.9:
# a ticker on a conference card gets read as "how did this trade". Names stay in prose.
COMPANY_CODE_KEYS = ("listed_company", "ticker", "exchange")
# v0.13: the only legal slot labels. `is_recommand` is not one of them -- it orders.
TAGS = ("", "LBA")
# v0.16: the two fields that answer "which drug is this, hitting what". There is no
# column behind them, so the only way to keep them populated is to check them.
IDENTITY_FIELDS = ("drug", "target")
MIN_OVERRIDE_CHARS = 10
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
import os
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
# v0.10: the unit list is what decides whether a number is checked at all, so a
# missing unit is a silent hole -- exactly how `16.1 mo` slipped through as
# 「16 个月」 in v0.9.1. Oncology wrote in %/months; cardiology, diabetes,
# hepatology and neurology write in mmol/L, mg/dL, mL/min, U/L, IU/mL, mL,
# points, mmHg, events per 100 patient-years. Every unit listed here is checked;
# anything absent is not.
UNIT_PATTERN = (
    r"(?:%|个百分点|个月|月|周|天|小时|年|"
    r"mo|months?|weeks?|days?|hours?|years?|"
    r"mmol/L|μmol/L|umol/L|mg/dL|mg/L|g/L|g/dL|ng/mL|pg/mL|μg/mL|ug/mL|"
    r"IU/mL|U/L|copies/mL|log10|mL/min(?:/1\.73m2)?|mL/kg/min|mL|L|"
    r"kg|cm|mmHg|bpm|points?|分|次/年|events?/100)"
)
UNIT_NUM = re.compile(r"\d+(?:\.\d+)?\s*" + UNIT_PATTERN, re.I)
FIGURE = re.compile(r"\d+(?:\.\d+)?\s*" + UNIT_PATTERN, re.I)


def load_pool(path: str) -> Dict[str, Dict[str, Any]]:
    pool = json.load(open(path, encoding="utf-8"))
    by_esid: Dict[str, Dict[str, Any]] = {}
    for b in BUCKETS:
        for item in pool["pools"][b]["items"]:
            esid = item.get("esid")
            if esid:
                by_esid[str(esid)] = dict(item, _bucket=b)
    return by_esid


def recompute_pool(by_rows: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Rebuild the candidate pools from rows.json with the shipped triage code.

    The membership question ("is this record allowed on the list?") is answered by
    code, not by whichever pool file was passed in. E2E #10 on ESC 2026 found the
    cheap bypass: the model appended 110 records it thought triage had wrongly cut
    to a hand-made ``pool_ext.json`` and passed *that* as ``--pool``; every check
    went green while the fact layer, which rebuilds from ``work/pool/pool.json``,
    failed on 9 unknown esids and 61 untraceable figures. A pool file is display
    metadata now; this function is the gate.
    """
    rows = []
    for esid, item in by_rows.items():
        row = dict(item)
        row["_id"] = esid
        rows.append(row)
    pool = triage.build_pools(rows)
    out: Dict[str, Dict[str, Any]] = {}
    for b in BUCKETS:
        for item in pool["pools"][b]["items"]:
            if item.get("esid"):
                entry = dict(item, _bucket=b)
                out[str(item["esid"])] = entry
                # Dedupe merged these esids into the entry above; a card written
                # off the sibling record is the same card (see triage.build_pools).
                for alias in item.get("alias_esids") or []:
                    out[str(alias)] = dict(entry, _alias_of=str(item["esid"]))
    return out


def load_judged(path: str) -> Dict[str, Dict[str, Any]]:
    """Per-item judgement records, keyed by esid.

    v0.11 requires ``esid`` on every judged entry. Before that the records carried
    only a batch-local ``i``, so "which record did the reviewer score 85" could only be
    answered by re-reading the batch file -- and a hand-made batch could answer it
    differently. An identity the *judgement* states is an identity the gate can hold
    it to, and ``selection_order`` is exactly that gate.
    """
    files: List[str] = []
    if os.path.isdir(path):
        files = [os.path.join(path, f) for f in sorted(os.listdir(path))
                 if f.startswith("judged") and f.endswith(".json")]
    elif os.path.exists(path):
        files = [path]
    out: Dict[str, Dict[str, Any]] = {}
    for f in files:
        payload = json.load(open(f, encoding="utf-8"))
        items = payload.get("items") if isinstance(payload, dict) else payload
        for item in items or []:
            if not isinstance(item, dict):
                continue
            # Only real judgement records: a `selected.json` or a plan file in the
            # same directory must not be mistaken for one (it carries esid but no
            # verdict), or the gate would read "nobody was judged keep" as "nothing
            # to compare" and pass on an empty set -- the classic empty-vs-empty trap.
            if item.get("verdict") is None or item.get("score") is None:
                continue
            esid = str(item.get("esid") or "").strip()
            if esid:
                out[esid] = item
    return out


def selection_order(cards: List[Dict[str, Any]], judged: Dict[str, Dict[str, Any]],
                    overrides: Any) -> Tuple[List[str], List[str]]:
    """A bucket list must be the top of its own ranking.

    E2E #11 (EASL 2026) shipped a 35-score pivotal card while a judged-85 PBC trial sat
    unused in the same bucket: every other gate was green, because they all ask "is what
    you listed legal", never "is what you listed better". The judgement layer already
    answered that -- this compares its answers against the delivered set.

    Overrides are a ledger, not a loophole: an entry without a readable reason does not
    count, so the only way past a higher-scored skip is to say why in the deliverable.
    """
    fails: List[str] = []
    notes: List[str] = []
    waived: Dict[str, str] = {}
    if overrides is not None:
        if not isinstance(overrides, list):
            fails.append("envelope: editorial_overrides must be a list")
        else:
            for entry in overrides:
                if not isinstance(entry, dict):
                    fails.append("envelope: editorial_overrides entries must be objects")
                    continue
                esid = str(entry.get("esid") or "").strip()
                reason = " ".join(str(entry.get("reason") or "").split())
                if not esid:
                    fails.append("envelope: editorial_overrides entry without esid")
                    continue
                if len(reason) < 10:
                    fails.append(f"envelope: editorial_overrides[{esid}] reason is "
                                 f"{len(reason)} chars -- say what made you skip it")
                    continue
                waived[esid] = reason
    kept = {str(c.get("esid") or ""): c for c in cards}
    by_bucket: Dict[str, List[Dict[str, Any]]] = {}
    for esid, item in judged.items():
        if str(item.get("verdict") or "").lower() != "keep":
            continue
        score = item.get("score")
        if not isinstance(score, int) or isinstance(score, bool):
            continue
        bucket = str(item.get("bucket") or "")
        by_bucket.setdefault(bucket, []).append(
            {"esid": esid, "score": score, "title": str(item.get("reason") or "")})
    if not by_bucket:
        fails.append("selection: not one judged record landed in a bucket -- the "
                     "judgement records need `esid` + `bucket` + `verdict` + `score` "
                     "(v0.11), otherwise the editorial step cannot be checked at all")
        return fails, notes
    for bucket, items in by_bucket.items():
        chosen = [c for e, c in kept.items() if str(c.get("bucket") or "") == bucket]
        if not chosen:
            notes.append(f"selection: bucket {bucket} kept nothing; nothing to compare")
            continue
        floor = min(int(c.get("score") or 0) for c in chosen)
        for item in sorted(items, key=lambda x: -x["score"]):
            if item["esid"] in kept or item["score"] <= floor:
                continue
            if item["esid"] in waived:
                notes.append(f"selection: {bucket} skipped {item['esid']} "
                             f"({item['score']} > floor {floor}) under a declared "
                             f"override")
                continue
            fails.append(
                f"selection: {bucket} kept a {floor}-score card while judged-keep "
                f"{item['esid']} scores {item['score']} -- take the higher one, or "
                f"declare it in editorial_overrides with a reason ({item['title'][:40]})")
    return fails, notes


def _recommand_of(item: Dict[str, Any]) -> Optional[bool]:
    """Pool row -> the same three states the card must print."""
    value = item.get("is_recommand")
    if isinstance(value, bool):
        return value
    if item.get("forced"):
        return True
    return None


def bucket_order_gate(cards: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Inside one bucket, scores must not go up.

    R14 (ADA 2026) delivered pivotal as `83, 80, 80, 78, 78, 76, 76, 71, 73, 71`:
    every other gate was green, because `selection_order()` only asks "did you skip
    a higher-scored record", never "is what you did list still in order". The list
    is a ranking, so an out-of-order pair is a defect a reader can see with their
    eyes -- and it is checkable here, before delivery, instead of only in the
    offline fact layer (`A-P4-score-order`).

    Two levels per bucket: flagged cards lead (that is `recommand_gate`'s job), and
    *within* each flag class the score is non-increasing. That is why the grouping
    key is `(bucket, is_recommand)` and not `bucket` alone -- a flagged 60 legally
    sits above an unflagged 80, and a plain `bucket` check would call that a
    reversal.
    """
    fails: List[str] = []
    notes: List[str] = []
    groups: Dict[Tuple[str, Any], List[Dict[str, Any]]] = {}
    for card in cards:
        key = (str(card.get("bucket") or ""), card.get("is_recommand"))
        groups.setdefault(key, []).append(card)
    for (bucket, flag), items in groups.items():
        prev = None
        for card in items:
            score = card.get("score")
            if not isinstance(score, int) or isinstance(score, bool):
                continue
            if prev is not None and score > prev[0]:
                fails.append(
                    f"order: {bucket} puts {card.get('esid')} ({score}) after "
                    f"{prev[1]} ({prev[0]}) -- inside one bucket and one flag class "
                    f"scores must not go up; sort the plan by (is_recommand, -score)")
            prev = (score, card.get("esid"))
    if not notes:
        notes.append("order: in-bucket monotonicity checked per (bucket, flag) group")
    return fails, notes


def trial_seats_gate(cards: List[Dict[str, Any]],
                     pool: Dict[str, Dict[str, Any]],
                     overrides: Any = None,
                     max_seats: int = 2) -> Tuple[List[str], List[str]]:
    """One trial gets two seats, not three.

    R14: `HR17031 vs iGlar` took three of ten pivotal slots with the primary
    result, a subgroup and a safety readout (71 / 73 / 71). The "same mechanism,
    at most two" rule is editorial prose and does not bind a trial split into
    three publications. A third seat is only legal when it is declared in
    `editorial_overrides` with a reason -- same ledger, same rule as elsewhere.
    """
    fails: List[str] = []
    notes: List[str] = []
    waived = set()
    for entry in (overrides if isinstance(overrides, list) else []):
        if not isinstance(entry, dict):
            continue
        esid = str(entry.get("esid") or "").strip()
        reason = " ".join(str(entry.get("reason") or "").split())
        if esid and len(reason) >= 10:
            waived.add(esid)
    seats: Dict[str, List[str]] = {}
    for card in cards:
        esid = str(card.get("esid") or "")
        item = pool.get(esid) or {}
        trial = str(item.get("trial") or "").strip().upper()
        if not trial:
            continue
        seats.setdefault(trial, []).append(esid)
    for trial, esids in sorted(seats.items()):
        extra = esids[max_seats:]
        if not extra:
            continue
        undeclared = [e for e in extra if e not in waived]
        if not undeclared:
            notes.append(f"seats: trial {trial} keeps {len(esids)} seats under a "
                         f"declared override ({', '.join(extra)})")
            continue
        fails.append(
            f"seats: trial {trial} holds {len(esids)} cards ({', '.join(esids)}) -- "
            f"cap is {max_seats}; merge the sub-analyses into the primary card, or "
            f"declare the extra seat in editorial_overrides with a reason "
            f"({', '.join(undeclared)} undeclared)")
    if seats:
        notes.append(f"seats: {len(seats)} distinct trials across "
                     f"{sum(len(v) for v in seats.values())} cards (cap {max_seats})")
    return fails, notes


def card_identity_gate(cards: List[Dict[str, Any]],
                       overrides: Any = None) -> Tuple[List[str], List[str]]:
    """Every card must say which drug it is about, and what that drug hits.

    v0.16. Nothing in the deliverable used to check this, and the fields do not come
    from the data: `clinical_result` has no drug/target column (the only structured
    source is `clinical_result.arms[].drugs[]`, 5.9 KB per record), so `make_cards.py`
    copies whatever the plan says and an empty plan field is simply an empty card face.
    The ADA 2026 run proved the failure mode: 27/27 cards shipped blank, `OK cards=27`,
    and the review page rendered `—` for every drug.

    `target` may be empty for a record that has no molecular target (BCG, metformin),
    but only by declaring `field: "target"` in `editorial_overrides` with a reason. The
    field key matters: a reason written to excuse a *selection* skip must not double as
    a licence for a blank card.
    """
    fails: List[str] = []
    notes: List[str] = []
    cards = cards or []
    excused: Dict[str, set] = {}
    for entry in (overrides if isinstance(overrides, list) else []):
        if not isinstance(entry, dict):
            continue
        esid = str(entry.get("esid") or "").strip()
        reason = " ".join(str(entry.get("reason") or "").split())
        raw_field = entry.get("fields") or entry.get("field")
        fields = {raw_field} if isinstance(raw_field, str) else set(raw_field or [])
        if not esid or len(reason) < MIN_OVERRIDE_CHARS:
            continue
        for name in fields & set(IDENTITY_FIELDS):
            excused.setdefault(esid, set()).add(name)
    filled = 0
    for card in cards:
        tag = f"card[{card.get('esid') or '?'}]"
        for name in IDENTITY_FIELDS:
            value = card.get(name)
            if not isinstance(value, str):
                fails.append(f"{tag}: {name} missing or not a string -- every card must "
                             f"name the drug and the target it hits")
                continue
            if value.strip():
                filled += 1
                continue
            if name in excused.get(str(card.get("esid") or "").strip(), set()):
                notes.append(f"identity: {card.get('esid')} has no {name} "
                             f"(declared in editorial_overrides)")
                continue
            fails.append(f"{tag}: {name} is empty -- extract it from the title/summary/"
                         f"abstract while writing `why` (the result tool has no "
                         f"{name} column), or declare editorial_overrides with "
                         f"field={name!r} and a reason")
    if cards:
        notes.append(f"identity: {filled}/{2 * len(cards)} drug/target slots filled on "
                     f"{len(cards)} card(s)")
    else:
        notes.append("identity: no cards -- nothing to check")
    return fails, notes


def recommand_gate(cards: List[Dict[str, Any]],
                   pool: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """The data owner's ``is_recommand`` is a forced slot, not a ranking hint.

    Two things are checked and neither can be waived by ``editorial_overrides``:

    1. **coverage** -- a flagged row has to be on the list. Our screening exists to
       cut a 1097-row conference down to a reading list; a human at the data end
       already said "read this one", and silently dropping it is the single failure
       the flag was added to prevent.
    2. **order** -- inside a bucket, flagged cards come before unflagged ones. Note
       that this deliberately contradicts the score ordering gate above; the two are
       reconciled by reading them together: *within one flag class* scores must be
       non-increasing, and the flag class dominates the score across classes. A
       flagged-but-low-scoring card is therefore legal, and it must still be judged
       honestly (`score` is the reviewer's number, not a copy of the flag).

    EASL/ESC 2026 have no flagged rows at all, so the note says "the column was empty"
    rather than staying silent -- an empty flag is a different statement from a
    missing one, and only the former means nobody recommended anything.
    """
    fails: List[str] = []
    notes: List[str] = []
    flagged: Dict[str, Dict[str, Any]] = {}
    for esid, item in pool.items():
        if item.get("is_recommand") is True:
            flagged.setdefault(str(item.get("esid") or esid), item)
    by_card = {str(c.get("esid") or ""): c for c in cards}
    covered = set(by_card)
    for esid, item in pool.items():
        if item.get("_alias_of"):
            covered.add(str(item["_alias_of"]))
    if not flagged:
        notes.append("recommand: no row in this conference carries is_recommand=是 -- "
                     "there is no forced slot to honour (say so in coverage_notes; an "
                     "empty flag is not a statement that nothing was recommended)")
        return fails, notes
    for esid, item in sorted(flagged.items()):
        if esid in covered:
            continue
        fails.append(
            f"recommand: {esid} ({item.get('abstract_id') or 'no abstract id'}, "
            f"{item.get('trial') or 'no trial'}) is flagged is_recommand=是 upstream but "
            f"is not on the list -- a flagged readout is forced; put it in its bucket "
            f"whether or not the judgement scored it low")
    by_bucket: Dict[str, List[Dict[str, Any]]] = {}
    for card in cards:
        by_bucket.setdefault(str(card.get("bucket") or ""), []).append(card)
    for bucket, items in by_bucket.items():
        seen_plain = False
        for card in items:
            if card.get("is_recommand") is True:
                if seen_plain:
                    fails.append(
                        f"recommand: {bucket} puts flagged {card.get('esid')} below an "
                        f"unflagged card -- flagged cards come first inside their bucket")
            else:
                seen_plain = True
    if flagged:
        hits = [e for e in flagged if e in covered]
        notes.append(f"recommand: {len(hits)}/{len(flagged)} flagged row(s) on the list")
    return fails, notes


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
          by_calc: Optional[Dict[str, Dict[str, Any]]] = None,
          judged: Optional[Dict[str, Dict[str, Any]]] = None,
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
    if len(cards) > TOTAL_CAP:
        fails.append(f"size: {len(cards)} cards (cap is {TOTAL_CAP})")
    # v0.18: a short list is a claim about the corpus, so it has to be declared. ENA
    # 2026 holds 17 records (14 / 2 / 1 candidates); 8 cards was the honest output and
    # the run said so in coverage_notes -- but an undeclared short list is exactly the
    # shape of a lazy run, and the two used to be indistinguishable here.
    present = {str(c.get("bucket") or "") for c in cards if isinstance(c, dict)}
    short = [] if len(cards) >= MIN_TOTAL else [
        str(x) for x in (payload.get("coverage_notes") or [])
        if re.search(r"(不足|低于|未达|凑不满|凑不齐|无法凑)",
                     str(x)) and str(MIN_TOTAL) in str(x)]
    if len(cards) < MIN_TOTAL and not short:
        fails.append(f"size: {len(cards)} cards < {MIN_TOTAL} and no coverage_note declares "
                     f"the shortfall (name the {MIN_TOTAL}-card floor and why the corpus "
                     f"cannot fill it)")
    elif len(cards) < MIN_TOTAL:
        notes.append(f"size: {len(cards)} cards, shortfall declared in coverage_notes")
    # v0.18: this replaces the old blanket total floor as the floor's real job. A bucket
    # that has candidates and no card is a silent hole in the reading list -- the reader
    # concludes the conference produced no failures, which is a claim, not an omission.
    for b in BUCKETS:
        n = sum(1 for it in by_esid.values()
                if it.get("_bucket") == b and not it.get("_alias_of"))
        if n and b not in present:
            fails.append(f"buckets: `{b}` has {n} candidate(s) but no card -- a bucket "
                         f"may be thin, never silently empty")
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

    if judged:
        sfails, snotes = selection_order(cards, judged,
                                        payload.get("editorial_overrides"))
        fails += sfails
        notes += snotes
        rfails, rnotes = recommand_gate(cards, by_calc if by_calc is not None else by_esid)
        fails += rfails
        notes += rnotes
    else:
        notes.append("selection: no judged records passed in -- the editorial hop "
                     "from judgement to list is unchecked (the CLI always passes "
                     "`--judged`, so this only happens in-process)")

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
        # Membership comes from the recomputed pools when rows.json was supplied;
        # the pool file only fills in display fields for records it happens to hold.
        item = (by_calc if by_calc is not None else by_esid).get(esid)
        origin = "pool"
        if item is None and by_rows:
            item = by_rows.get(esid)
            origin = "rows"
        if item is not None and origin == "pool":
            item = dict(item)
            item.setdefault("_bucket", (by_esid.get(esid) or {}).get("_bucket"))
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
        if card.get("tag") not in TAGS:
            fails.append(f"{tag}: tag={card.get('tag')!r} -- v0.13 keeps the flag out of the "
                         f"label; a flagged row leads its bucket silently instead of wearing "
                         f"a badge (legal: {list(TAGS)})")
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
        # v0.12: `abstract_id` is reachable from the tool again (it had simply never
        # been in `selected_fields`, not been missing from the table), so a card that
        # prints one is making a checkable claim. The number is what a reader types
        # into the abstract book; a wrong one is worse than no number.
        row_abs = str(item.get("abstract_id") or "").strip()
        card_abs = str(card.get("abstract_id") or "").strip()
        if row_abs and not card_abs:
            fails.append(f"{tag}: missing abstract_id (rows.json has {row_abs!r})")
        elif card_abs and row_abs and card_abs != row_abs:
            fails.append(f"{tag}: abstract_id={card_abs!r} != rows.json {row_abs!r}")
        elif card_abs and not row_abs:
            fails.append(f"{tag}: abstract_id={card_abs!r} invented -- rows.json has none")
        # `is_recommand` decides whether this card was allowed to outrank a higher
        # score, so it cannot be a label the card invents about itself. It is also
        # tri-state (v0.14): True = flagged, False = owner said "exclude", None =
        # the column was empty. Collapsing None to False is exactly the bug that
        # shipped 191 unflagged ADA 2026 rows as `false` -- an exclusion nobody issued.
        if card.get("is_recommand") is not None and not isinstance(card["is_recommand"], bool):
            fails.append(f"{tag}: is_recommand must be boolean or null")
        elif card.get("is_recommand") != _recommand_of(item):
            fails.append(f"{tag}: is_recommand={card.get('is_recommand')!r} but rows.json says "
                         f"{_recommand_of(item)!r}")
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
        # v0.13: the ticker is gone, not merely quiet. A card that still carries it
        # (or the exchange) is a regression, so it fails instead of being ignored --
        # and `null` fails too, because "we checked and it is not listed" is the same
        # claim in a quieter voice.
        for key in COMPANY_CODE_KEYS:
            if key in card:
                fails.append(f"{tag}: {key} is a company-code field -- v0.13 removed it; "
                             f"the card answers what was reported, not who trades where")
    return fails, notes


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cards", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--rows", required=True,
                    help="work/rows.json -- always required: the pool membership "
                         "gate is rebuilt from it, so a hand-edited pool file cannot "
                         "widen the candidate set")
    ap.add_argument("--judged", required=True,
                    help="work/judged_*.json (or their directory) -- every judged entry "
                         "needs an `esid` so the selection can be compared against the "
                         "scores the reviewer actually gave")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    payload = json.load(open(args.cards, encoding="utf-8"))
    by_esid = load_pool(args.pool)
    by_rows = load_rows(args.rows)
    by_calc = recompute_pool(by_rows)
    judged = load_judged(args.judged)
    if not judged:
        # Fail closed: the path exists but nothing in it is usable. Passing here would
        # mean "nobody was judged keep", which is indistinguishable from "the check
        # never ran" -- and an unchecked editorial step is precisely what shipped the
        # EASL 2026 list with a 35-score card above an unused 85-score one.
        judged = None
        sel_fail = (f"selection: {args.judged} holds no usable judgement record "
                    f"(needs esid + bucket + verdict + score per entry)")
    (fails, notes) = check(payload, by_esid, by_rows, by_calc, judged)
    if judged is None:
        fails.append(sel_fail)
    if set(by_calc) != set(by_esid):
        notes.append(
            f"pool file holds {len(by_esid)} records, a fresh triage build over "
            f"rows.json gives {len(by_calc)} -- membership is judged on the rebuild, "
            f"so re-run triage.py instead of editing the pool by hand")
    ofails, onotes = bucket_order_gate(payload.get("cards") or [])
    fails += ofails
    notes += onotes
    tfails, tnotes = trial_seats_gate(payload.get("cards") or [], by_calc or by_esid,
                                     payload.get("editorial_overrides"))
    fails += tfails
    notes += tnotes
    ifails, inotes = card_identity_gate(payload.get("cards") or [],
                                        payload.get("editorial_overrides"))
    fails += ifails
    notes += inotes
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
