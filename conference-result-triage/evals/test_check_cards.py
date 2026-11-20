#!/usr/bin/env python3
"""Fixture regression for check_cards.py. Zero deps, exits non-zero on mismatch.

    python3 evals/test_check_cards.py

The gate gained two rules that exist because a list can be wrong without being
obviously wrong:

  - **per-bucket cap 10 / 30 overall** -- a 40-card bucket is not a reading list, and
    padding it with `weak` items is how a shortlist turns into a dump;
  - **score self-consistency** -- the score is the reviewer's judgement, so the
    script cannot check whether 78 is the *right* number. What it can check is
    that the five parts add up to it and none exceeds its ceiling; a total that
    does not add up means the number was invented rather than judged.

v0.11 adds **selection monotonicity**: inside a bucket the delivered cards must be the
top of the judgements' own ranking, and a skip of a higher-scored keep is only legal when
the deliverable declares it in `editorial_overrides`.

It also checks `coverage_notes`: the run that shipped 40 cards with the limits
stated only in its chat reply is why that became a gate. The shape must be
strict, the prose must not be -- case 8 pins a legal paraphrase as passing, so
the rule is testing a fact rather than a wording.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skill", "conference-result-triage", "scripts"))

import check_cards  # noqa: E402
import triage  # noqa: E402

failures = []


def expect(name, fails, needle):
    hits = [f for f in fails if needle in f]
    if not hits:
        failures.append(f"{name}: nothing matched {needle!r} in {len(fails)} fails")
        return
    print(f"  ok  {name}: {hits[0][:90]}")


def build_pool():
    rows = json.load(open(os.path.join(HERE, "fixtures", "mini_rows.json"), encoding="utf-8"))
    pool = triage.build_pools([triage.flat_row(r) for r in rows])
    by_esid = {}
    for bucket in triage.BUCKETS:
        for item in pool["pools"][bucket]["items"]:
            item["_bucket"] = bucket
            by_esid[str(item["esid"])] = item
    return pool, by_esid


def card(item, score=60, parts=None):
    """A card the gate should accept, apart from whatever the caller breaks."""
    text = str(item.get("results_text") or "")
    summary = next((s for s in text.replace("\n", " ").split(". ") if "%" in s), "")
    return {
        "esid": item["esid"],
        # v0.12: the number the reader searches the abstract book by, plus the data
        # owner's forced-slot flag. Both are copied from the row, never invented.
        "abstract_id": item.get("abstract_id"),
        # v0.14: tri-state, no coercion -- an empty column is `None`, not `False`.
        "is_recommand": (item["is_recommand"]
                         if isinstance(item.get("is_recommand"), bool) else None),
        "lba": bool(item.get("lba")),
        "manual": item.get("manual"),
        "bucket": item["_bucket"],
        "tag": "LBA" if item.get("lba") else "",
        "title": str(item.get("title") or item.get("trial") or "untitled"),
        "summary": summary or "ORR 40%",
        # `why` has to carry a judgement, not a label: >=60 chars, and it may not be a
        # re-wrap of `summary`. Both rules exist because the field kept collapsing
        # back into "报告了主要终点读数".
        "why": ("该读数首次在随机对照中验证这一机制，缓解深度与既往同类药物相比"
                "有明显提升；若总生存获益在后继随访中成立，会直接改变这一线的标准治疗，"
                "但入组人群经过高度筛选，外推需谨慎。"),
        "score": score,
        "score_parts": parts or {"evidence_strength": 20, "effect_size": 15,
                                 "clinical_impact": 15, "novelty": 5,
                                 "readout_maturity": 5},
        # v0.16: the card face. There is no data column behind either field, so the
        # legal shim states them; a blank drug is a rendered dash, not a soft default.
        "drug": "Tarlatamab", "target": "DLL3",
        "indication": "", "phase": "", "presentation": "",
        "stock": None,
    }


pool, by_esid = build_pool()
items = list(by_esid.values())
if len(items) < 2:
    raise SystemExit("fixture too small: need at least 2 pool items")

print("check_cards fixture:")

# 1. a hand-made card passes (proves the rest of the gate is not the thing failing)
NOTES = ["data_type 无明确首次/更新依据则未判定。",
         "部分摘要未列p或HR；本榜并非会议书全覆盖。"]

base = [card(items[0], score=60)]
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": base,
                              "coverage_notes": NOTES}, by_esid)
# v0.18: a one-card fixture is deliberately short, so both floor-shaped complaints
# (undeclared shortfall, unrepresented bucket) are expected here and checked on their
# own below; everything else must stay silent.
size_only = [f for f in fails if not f.startswith(("size:", "buckets:"))]
if size_only:
    failures.append(f"clean card should pass: {size_only}")
else:
    print("  ok  clean card passes (only the size / bucket floors complain)")

# 2. score_parts that do not sum to score
broken = dict(base[0], score=90)
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [broken],
                             "coverage_notes": NOTES}, by_esid)
expect("parts sum != score", fails, "score_parts sum")

# 3. a part above its ceiling -- this is what a reviewer does when award-happy
over = card(items[0], score=60,
            parts={"evidence_strength": 40, "effect_size": 10, "clinical_impact": 5,
                   "novelty": 3, "readout_maturity": 2})
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [over],
                             "coverage_notes": NOTES}, by_esid)
expect("part over ceiling", fails, "must be an integer 0-30")

# 4. score outside 0-100
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], score=140)],
                              "coverage_notes": NOTES}, by_esid)
expect("score out of range", fails, "must be an integer 0-100")

# 5. per-bucket cap 15: sixteen cards in one bucket must be refused
many = [card(items[i % len(items)]) for i in range(check_cards.PER_BUCKET_CAP + 1)]
same_bucket = many[0]["bucket"]
for c in many:
    c["bucket"] = same_bucket
fails, _ = check_cards.check({"conference": "T", "count": len(many), "cards": many,
                             "coverage_notes": NOTES}, by_esid)
expect(f"{same_bucket} over cap", fails, f"> cap {check_cards.PER_BUCKET_CAP}")

# 6. no coverage_notes at all -- the exact defect of the 40-card ESMO 2026 run
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": base}, by_esid)
expect("no coverage_notes", fails, "coverage_notes` missing")

# 7. notes that never state the data_type limit
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": base,
                              "coverage_notes": [NOTES[1]]}, by_esid)
expect("data_type limit unstated", fails, "does not state the data_type limit")

# 8. NEG: a different wording for the same two facts must still pass
legal = ["多数记录的 data_type 无法判定，按未判定处理，不猜首次或更新。",
         "摘要普遍没给 p 值或 HR，且本榜不代表会议全量。"]
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": base,
                              "coverage_notes": legal}, by_esid)
paraphrase = [f for f in fails if "coverage_notes" in f]
if paraphrase:
    failures.append(f"legal paraphrase rejected: {paraphrase}")
else:
    print("  ok  legal paraphrase of the notes passes")

# 9. `why` too short -- "数据好" is not a reason
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], why="数据很好，值得关注")],
                              "coverage_notes": NOTES}, by_esid)
expect("why too short", fails, f"why is ")

# 10. `why` that just repeats `summary`
dup = dict(base[0], why=str(base[0]["summary"]) + "该结果值得关注，因为这项研究改变了这一线的治疗格局，"
           "且入组人群的缓解持续时间明显优于历史对照，后续随访会验证总生存。")
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [dup],
                              "coverage_notes": NOTES}, by_esid)
expect("why repeats summary", fails, "repeats summary")

# 11/12/13. v0.13 removed the identity layer: the ticker went with the quote. Presence
# is a regression, and so is the quieter `null` form -- "checked and not listed" is the
# same market claim as a filled ticker.
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], listed_company=None)],
                              "coverage_notes": NOTES}, by_esid)
expect("listed_company returns (null form)", fails, "company-code field")
expect("listed_company returns (null form)", fails, "v0.13 removed it")

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], ticker="TNGX")],
                              "coverage_notes": NOTES}, by_esid)
expect("bare ticker returns", fails, "company-code field")

# 14. NEG: the legal card carries no company code at all
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [base[0]],
                              "coverage_notes": NOTES}, by_esid)
if [f for f in fails if "company-code" in f]:
    failures.append(f"legal card rejected for a missing company code: {fails}")
else:
    print("  ok  card without any company code passes")

# 15. a card the mechanical screen cut may only enter via a web promotion
promoted_row = {"esid": "nr_post_hoc_1", "lba": False, "manual": None,
                "summary": "ORR 40%", "study_results": ["ORR 40%"]}
promo_card = dict(base[0], esid="nr_post_hoc_1", lba=False, bucket="pivotal")
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [promo_card],
                              "coverage_notes": NOTES}, by_esid,
                             {"nr_post_hoc_1": promoted_row})
expect("unpromoted out-of-pool card", fails, "was not promoted")
fails, notes = check_cards.check({"conference": "T", "count": 1,
                                  "cards": [dict(promo_card, promoted="web")],
                                  "coverage_notes": NOTES}, by_esid,
                                 {"nr_post_hoc_1": promoted_row})
# the fixture row deliberately carries only "ORR 40%", so the summary's other
# figures are untraceable here -- that is the number gate, not the promotion gate
left = [f for f in fails if f.startswith("card ") and "figure" not in f]
if left:
    failures.append(f"promoted card rejected: {left}")
else:
    print("  ok  web-promoted card resolves against rows.json")

# 16/17. v0.9 deleted the quote layer; v0.13 deleted what it left behind. A
# meeting-day move is mostly the sector's own beta, and a ticker invites exactly that
# reading -- so both shapes are defects, not decoration.
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], reaction={"to_date": "2026-10-19",
                                                               "change_pct": 6.76})],
                              "coverage_notes": NOTES}, by_esid)
expect("reaction field returns", fails, "price field")

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], stock={"ticker": "TNGX",
                                                             "change_pct": 6.76})],
                              "coverage_notes": NOTES}, by_esid)
expect("stock field returns", fails, "price field")

# 20. v0.13 keeps the flag out of the label: `is_recommand` still decides placement
# (it leads its bucket), but a chip on a judged list reads as our endorsement of a row
# the data owner flagged.
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], tag="推荐")],
                              "coverage_notes": NOTES}, by_esid)
expect("is_recommand rendered as a badge", fails, "keeps the flag out of the label")

legit = dict(base[0], tag="LBA", lba=True)
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [legit], "coverage_notes": NOTES},
                             {**by_esid, legit["esid"]: {**by_esid[legit["esid"]], "lba": True}})
if [f for f in fails if "label" in f]:
    failures.append(f"legal LBA label rejected: {fails}")
else:
    print("  ok  LBA slot label still legal")

# 21/22/23. Number traceability compares values, not digit strings. e2e8 shipped
# "12 个月 PFS 率 44% vs 24%" (the abstract printed 44.7 / 24.5 only) and "随访约 16 个月"
# (the abstract said 16.1 mo); a substring test answered yes to both, so the delivered
# JSON passed its own gate while the offline fact layer said no.
import copy  # noqa: E402

trap = copy.deepcopy(items[0])
trap["results_text"] = ("Kras trap met its endpoint with confirmed ORR 44.7% versus "
                        "24.5% for the comparator; median follow-up 16.1 mo.")
trap_by = {str(trap["esid"]): trap}

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], summary="确认 ORR 44% 对比 25%。")],
                              "coverage_notes": NOTES}, trap_by)
expect("rounded figure is not traceable", fails, "figure '44%' not found")

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], summary="确认 ORR 44.7% 对比 24.5%。")],
                              "coverage_notes": NOTES}, trap_by)
if [f for f in fails if "figure" in f]:
    failures.append(f"verbatim figures rejected: {fails}")
else:
    print("  ok  verbatim figures pass (44.7 / 24.5)")

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], summary="ORR 44.7%，随访约 16 个月。")],
                              "coverage_notes": NOTES}, trap_by)
expect("chinese month unit is scanned", fails, "figure '16 个月' not found")

# 24. v0.10: lab units are numbers too. Cardiology / diabetes / hepatology abstracts
# report mmol/L, mg/dL, mL/min, IU/mL, mL -- none of which the old %/mo figure regex
# could see, so a fabricated lab value was invisible to the gate. ESC 2026 writes in
# exactly these units.
lab = copy.deepcopy(items[0])
lab["results_text"] = ("HbA1c fell 1.8% with LDL-C 52.3 mg/dL and eGFR change "
                       "+4.1 mL/min/1.73m2 over 24 weeks.")
lab_by = {str(lab["esid"]): lab}
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], summary="LDL-C 下降 55.0 mg/dL。")],
                              "coverage_notes": NOTES}, lab_by)
expect("lab unit is scanned", fails, "figure '55.0 mg/dL' not found")

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], summary="LDL-C 52.3 mg/dL，eGFR +4.1 mL/min/1.73m2。")],
                              "coverage_notes": NOTES}, lab_by)
if [f for f in fails if "figure" in f]:
    failures.append(f"verbatim lab figures rejected: {fails}")
else:
    print("  ok  verbatim lab figures pass (52.3 mg/dL / 4.1 mL/min)")

# 25. The pool file is metadata; membership is rebuilt from rows.json. e2e #10 shipped
# 9 ESC 2026 cards that triage had cut, by pointing --pool at a hand-made pool_ext.json;
# the delivered JSON passed its own gate while the fact layer failed on unknown esids.
hand_pool_row = {"esid": "nr_hand_pool_1", "lba": False, "manual": None,
                 "summary": "ORR 40%", "study_results": ["ORR 40%"],
                 "_bucket": "pivotal"}
hand_by_esid = dict(by_esid)
hand_by_esid["nr_hand_pool_1"] = hand_pool_row
hand_card = dict(base[0], esid="nr_hand_pool_1")
fails, notes = check_cards.check({"conference": "T", "count": 1, "cards": [hand_card],
                                  "coverage_notes": NOTES}, hand_by_esid,
                                 {"nr_hand_pool_1": hand_pool_row}, {})
expect("hand-made pool is overruled", fails, "was not promoted")

# 26. and the rebuild must agree with the pools a clean run produces
rows_by_esid = json.load(open(os.path.join(HERE, "fixtures", "mini_rows.json"), encoding="utf-8"))
rebuilt = check_cards.recompute_pool({str(r["_id"]): triage.flat_row(r) for r in rows_by_esid})
if set(rebuilt) != set(by_esid):
    failures.append(f"recompute_pool disagrees: {len(rebuilt)} vs {len(by_esid)}")
else:
    print(f"  ok  recompute_pool agrees with build_pools ({len(rebuilt)} records)")

# --- selection monotonicity (v0.11) -------------------------------------- #
# The defect these pin: EASL 2026 delivered a 35-score pivotal card while a judged-85
# PBC phase III sat unused in the same bucket, and every other rule was green because
# they all ask "is what you listed legal", never "is it the better one".
def sel_case(cards, judged, overrides=None):
    payload = {"conference": "T", "count": len(cards), "cards": cards}
    if overrides is not None:
        payload["editorial_overrides"] = overrides
    return check_cards.selection_order(cards, judged, payload.get("editorial_overrides"))[0]


sel_cards = [{"esid": "a", "bucket": "pivotal", "score": 70},
             {"esid": "b", "bucket": "pivotal", "score": 55}]
sel_judged = {"a": {"esid": "a", "bucket": "pivotal", "verdict": "keep", "score": 70},
              "b": {"esid": "b", "bucket": "pivotal", "verdict": "keep", "score": 55},
              "c": {"esid": "c", "bucket": "pivotal", "verdict": "keep", "score": 50},
              "d": {"esid": "d", "bucket": "pivotal", "verdict": "weak", "score": 90}}
fails = sel_case(sel_cards, sel_judged)
if fails:
    failures.append(f"a skip below the floor is legal: {fails}")
else:
    print("  ok  selection: keeps below the bucket floor may be skipped")

fails = sel_case(sel_cards, dict(sel_judged,
                                 e={"esid": "e", "bucket": "pivotal",
                                    "verdict": "keep", "score": 95}))
expect("selection: higher-scored keep skipped", fails, "judged-keep e scores 95")

fails = sel_case(sel_cards, dict(sel_judged,
                                 e={"esid": "e", "bucket": "pivotal",
                                    "verdict": "keep", "score": 95}),
                 [{"esid": "e", "reason": "与已入选的 a 同机制同适应症，压同质只留一条"}])
if fails:
    failures.append(f"a reason-bearing override should clear it: {fails}")
else:
    print("  ok  selection: declared override with a reason clears the skip")

fails = sel_case(sel_cards, dict(sel_judged,
                                 e={"esid": "e", "bucket": "pivotal",
                                    "verdict": "keep", "score": 95}),
                 [{"esid": "e", "reason": "同机制"}])
expect("selection: override reason too short", fails, "reason is 3 chars")
expect("selection: short override does not waive", fails, "judged-keep e scores 95")

fails = sel_case(sel_cards, {})
expect("selection: no usable judgements", fails, "not one judged record landed")

# A plan/selected file in the same directory carries `esid` but no verdict -- if the
# loader kept it, `judged` would look non-empty and both checks above would pass on an
# empty set (the "empty vs empty" trap).
tmpdir = os.path.join(HERE, ".tmp-judged")
os.makedirs(tmpdir, exist_ok=True)
with open(os.path.join(tmpdir, "judged_01.json"), "w", encoding="utf-8") as f:
    json.dump([{"i": 1, "esid": "a", "bucket": "pivotal", "verdict": "keep", "score": 70}], f)
with open(os.path.join(tmpdir, "selected.json"), "w", encoding="utf-8") as f:
    json.dump({"items": [{"esid": "b", "bucket": "pivotal"}, {"esid": "c", "bucket": "pivotal"}]}, f)
loaded = check_cards.load_judged(tmpdir)
if list(loaded) != ["a"]:
    failures.append(f"load_judged kept non-judgement records: {sorted(loaded)}")
else:
    print("  ok  selection: only verdict-carrying records are loaded")
for name in os.listdir(tmpdir):
    os.unlink(os.path.join(tmpdir, name))
os.rmdir(tmpdir)

# 18. v0.12: the data owner's `is_recommand` is a forced slot, not a ranking hint.
# Two independent failures, because they fail for different reasons: dropping the
# flagged row (coverage) and burying it under unflagged cards (order). Neither is
# waivable by `editorial_overrides` -- a flag we can override is a flag we can ignore.
rec_pool = {
    "nr_rec_1": {"esid": "nr_rec_1", "is_recommand": True, "abstract_id": "LBA7",
                 "trial": "CLARITY-Gastric01"},
    "nr_plain_1": {"esid": "nr_plain_1", "is_recommand": False, "abstract_id": "1234P"},
}
plain_card = {"esid": "nr_plain_1", "bucket": "pivotal", "score": 72, "is_recommand": False}
rec_card = {"esid": "nr_rec_1", "bucket": "pivotal", "score": 41, "is_recommand": True}
fails, notes = check_cards.recommand_gate([plain_card], rec_pool)
expect("recommand: flagged row dropped", fails, "is_recommand=是 upstream but is not on the list")
fails, _ = check_cards.recommand_gate([plain_card, rec_card], rec_pool)
expect("recommand: flagged card buried", fails, "below an unflagged card")
fails, notes = check_cards.recommand_gate([rec_card, plain_card], rec_pool)
if fails:
    failures.append(f"a flagged-first bucket should pass: {fails}")
else:
    print("  ok  recommand: flagged-first bucket passes even at a lower score")

# An all-null column is a *different statement* from a missing one: it says nobody
# flagged anything, and the delivery has to say that out loud instead of scoring as
# if the flag had been absent. `None` is not `False`.
fails, notes = check_cards.recommand_gate([plain_card],
                                          {"nr_plain_1": {"esid": "nr_plain_1",
                                                          "is_recommand": None}})
if fails or not any("no row in this conference carries is_recommand" in n for n in notes):
    failures.append(f"empty is_recommand column should only be a note: {fails} {notes}")
else:
    print("  ok  recommand: an empty flag column is a note, not a pass by silence")

# 19. `abstract_id` is now reachable from the tool, so it is a checkable claim: the
# number is what a reader types into the abstract book.
ABS_ESID = str(base[0]["esid"])
abs_item = dict(by_esid[ABS_ESID], abstract_id="LBA7")
abs_card = {k: v for k, v in base[0].items() if k != "abstract_id"}
fails, _ = check_cards.check({"conference": "T", "count": 1, "cards": [abs_card],
                              "coverage_notes": NOTES}, {ABS_ESID: abs_item})
expect("abstract_id: missing on the card", fails, "missing abstract_id")
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(abs_card, abstract_id="9999P")],
                              "coverage_notes": NOTES}, {ABS_ESID: abs_item})
expect("abstract_id: disagrees with the row", fails, "!= rows.json")
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(abs_card, abstract_id="LBA7")],
                              "coverage_notes": NOTES}, {ABS_ESID: abs_item})
fails = [f for f in fails if not f.startswith("size:")]
if fails:
    failures.append(f"a matching abstract_id should pass: {fails}")
else:
    print("  ok  abstract_id: the row's own number passes")

# 20. `is_recommand` on a card is a claim about the row, so it cannot be self-declared.
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(abs_card, abstract_id="LBA7",
                                             is_recommand=True)],
                              "coverage_notes": NOTES}, {ABS_ESID: abs_item})
expect("is_recommand: card invents the flag", fails, "but rows.json says None")

# 20b. v0.14: the three states are three different statements. `None` (empty column)
# must not be rewritten as `False` ("the owner said exclude") in either direction.
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(abs_card, abstract_id="LBA7",
                                             is_recommand=False)],
                              "coverage_notes": NOTES}, {ABS_ESID: abs_item})
expect("is_recommand: null row printed as false", fails,
       "is_recommand=False but rows.json says None")

# 20c. A row the owner explicitly marked 否 must read back as false, and an empty
# column as null -- the mapping is what the card gate compares against.
if check_cards._recommand_of({"is_recommand": False}) is not False:
    failures.append("an explicit 否 row must map to False")
elif check_cards._recommand_of({"is_recommand": None}) is not None:
    failures.append("an empty is_recommand column must map to None, not False")
elif check_cards._recommand_of({"forced": True}) is not True:
    failures.append("a forced row must map to True")
else:
    print("  ok  is_recommand: text three states map to True / False / None")

# 21. v0.16: a card must name the drug and the target. Neither comes from a column,
# so this is the only thing standing between the run and 27/27 blank card faces.
clean, _ = check_cards.card_identity_gate([base[0]])
if clean:
    failures.append(f"a card naming drug+target should pass identity: {clean}")
else:
    print("  ok  identity: drug+target named passes")

blank, _ = check_cards.card_identity_gate([dict(base[0], drug="")])
expect("identity: blank drug", blank, "drug is empty")

gone, _ = check_cards.card_identity_gate([{k: v for k, v in base[0].items()
                                           if k != "target"}])
expect("identity: missing target key", gone, "target missing or not a string")

# 21b. `target` may be empty for a record with no molecular target, but the excuse has
# to be keyed to the field -- a selection-skip reason must not double as a licence.
excused, notes = check_cards.card_identity_gate(
    [dict(base[0], target="")],
    [{"esid": base[0]["esid"], "field": "target",
      "reason": "卡介苗是免疫调节疫苗，没有分子靶点可比。"}])
if excused:
    failures.append(f"a field-keyed override should excuse an empty target: {excused}")
elif not any("declared in editorial_overrides" in n for n in notes):
    failures.append("an excused empty target must be reported as a note, not silence")
else:
    print("  ok  identity: empty target excused only via field-keyed override")

unkeyed, _ = check_cards.card_identity_gate(
    [dict(base[0], target="")],
    [{"esid": base[0]["esid"], "reason": "同机制已有两张卡，这一席让给更弱的读数。"}])
expect("identity: selection reason must not excuse a blank target", unkeyed,
       "target is empty")

# v0.18 -- a bucket with candidates and no card is a claim, not an omission
empty_failed = [c for c in base if c.get("bucket") != "failed"] or base
pres, _ = check_cards.check({"conference": "T", "count": len(empty_failed),
                             "cards": empty_failed,
                             "coverage_notes": NOTES + [
                                 "条数不足 10 条下限：本会议失败桶无可读记录。"]}, by_esid)
expect("bucket presence: candidate-bearing bucket left empty", pres,
       "has 1 candidate(s) but no card")

# v0.18 -- a short list must name the floor it cannot meet
undeclared, _ = check_cards.check({"conference": "T", "count": 1, "cards": base,
                                   "coverage_notes": NOTES}, by_esid)
expect("floor: short list without a declared shortfall", undeclared,
       "no coverage_note declares the shortfall")

declared, decl_notes = check_cards.check({"conference": "T", "count": 1, "cards": base,
                                          "coverage_notes": NOTES + [
                                              "条数不足 10 条下限：本会议结果库可读记录有限。"],
                                          }, by_esid)
if any("no coverage_note declares the shortfall" in f for f in declared):
    failures.append("a declared shortfall should satisfy the floor rule")
else:
    print("  ok  floor: declared shortfall accepted")

if failures:
    print(f"\nFAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
print("\nfixture OK")
