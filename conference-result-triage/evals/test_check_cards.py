#!/usr/bin/env python3
"""Fixture regression for check_cards.py. Zero deps, exits non-zero on mismatch.

    python3 evals/test_check_cards.py

The gate gained two rules that exist because a list can be wrong without being
obviously wrong:

  - **per-bucket cap 15** -- a 40-card bucket is not a reading list, and padding
    it with `weak` items is how a shortlist turns into a dump;
  - **score self-consistency** -- the score is the reviewer's judgement, so the
    script cannot check whether 78 is the *right* number. What it can check is
    that the five parts add up to it and none exceeds its ceiling; a total that
    does not add up means the number was invented rather than judged.

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
        "abstract_id": None,
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
        "listed_company": None,
        "score": score,
        "score_parts": parts or {"evidence_strength": 20, "effect_size": 15,
                                 "clinical_impact": 15, "novelty": 5,
                                 "readout_maturity": 5},
        "drug": "", "target": "", "indication": "", "phase": "", "presentation": "",
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
size_only = [f for f in fails if not f.startswith("size:")]
if size_only:
    failures.append(f"clean card should pass: {size_only}")
else:
    print("  ok  clean card passes (only the list-size band complains)")

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

# 11. missing listed_company -- the field is the record that somebody looked
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [{k: v for k, v in base[0].items()
                                         if k != "listed_company"}],
                              "coverage_notes": NOTES}, by_esid)
expect("listed_company missing", fails, "missing listed_company")

# 12. a listed company with no verifiable ticker/source is a rumour, not a fact
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], listed_company={
                                  "name": "某公司", "ticker": "", "exchange": "HKEX",
                                  "source_url": "not-a-url"})],
                              "coverage_notes": NOTES}, by_esid)
expect("listed_company ticker", fails, "listed_company.ticker missing")
expect("listed_company url", fails, "not an http(s) URL")

# 13. NEG: a fully sourced listed company passes
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], listed_company={
                                  "name": "Roche Holding AG", "ticker": "ROG",
                                  "exchange": "SIX",
                                  "source_url": "https://www.roche.com/investors"})],
                              "coverage_notes": NOTES}, by_esid)
if [f for f in fails if "listed_company" in f]:
    failures.append(f"legal listed_company rejected: {fails}")
else:
    print("  ok  sourced listed_company passes")

# 14/15. a card the mechanical screen cut may only enter via a web promotion
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

# 16/17/18. v0.9 deleted the quote layer, so the field's reappearance is the defect:
# a meeting-day move is mostly the sector's own beta, and one company's move is
# shared by every card that names it -- neither says anything about an abstract.
listed = {"name": "Tango Therapeutics", "ticker": "TNGX", "exchange": "NASDAQ",
          "source_url": "https://investors.tangotx.com/"}

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], listed_company=dict(listed))],
                              "coverage_notes": NOTES}, by_esid)
if [f for f in fails if "price" in f]:
    failures.append(f"identity-only company rejected: {fails}")
else:
    print("  ok  identity-only listed_company passes (no price needed)")

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], listed_company=dict(
                                  listed, reaction={"to_date": "2026-10-19",
                                                    "change_pct": 6.76}))],
                              "coverage_notes": NOTES}, by_esid)
expect("reaction field returns", fails, "price field")

fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], stock={"ticker": "TNGX",
                                                             "change_pct": 6.76})],
                              "coverage_notes": NOTES}, by_esid)
expect("stock field returns", fails, "price field")

# 20. `09966.HK` + exchange=HKEX is the same fact twice and breaks quote lookup by bare
# code -- the suffix belongs nowhere near the ticker
fails, _ = check_cards.check({"conference": "T", "count": 1,
                              "cards": [dict(base[0], listed_company=dict(listed, ticker="09966.HK"))],
                              "coverage_notes": NOTES}, by_esid)
expect("ticker carries a market suffix", fails, "market suffix")

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

# 27. The report gate mirrors the platform verifier, so a citation schema error is caught
# before present_artifact instead of after it. ESC/EASL 2026 both shipped
# `{title, link}` entries and only found out from the post-run verifier.
import tempfile  # noqa: E402

def report_case(name, head, body, cites):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "citations.json"), "w", encoding="utf-8").write(json.dumps(cites))
    p = os.path.join(d, "report.md")
    open(p, "w", encoding="utf-8").write("---\n" + head + "\n---\n" + body)
    fails, _ = check_cards.check_report(p)
    return fails

GOOD_HEAD = ("skills: [conference-result-triage]\ntitle: T 2026\ndate: 2026-11-12\n"
             "lang: zh-CN\ncitations: /workspace/output/citations.json")
GOOD_CITE = {"ref_1": {"title": "ESC Hot Lines", "link": "https://www.escardio.org/x",
                       "paper_release_time_str": "2026-08-28"}}

fails = report_case("ok", GOOD_HEAD, "正文 {{ref_1}} 引用。", GOOD_CITE)
if fails:
    failures.append(f"valid report rejected: {fails}")
else:
    print("  ok  valid report + citations pass")

fails = report_case("two-keys", GOOD_HEAD, "正文 {{ref_1}} 引用。",
                    {"ref_1": {"title": "ESC Hot Lines",
                               "link": "https://www.escardio.org/x"}})
expect("citation missing the date key", fails, "paper_release_time_str")

fails = report_case("bad-date", GOOD_HEAD, "正文 {{ref_1}} 引用。",
                    {"ref_1": {"title": "T", "link": "https://a.b/c",
                               "paper_release_time_str": "2026-08-28 10:00"}})
expect("citation date is not date-only", fails, "is not YYYY-MM-DD")

fails = report_case("marker-no-entry", GOOD_HEAD, "正文 {{ref_1}} {{ref_2}} 引用。",
                    GOOD_CITE)
expect("marker without entry", fails, "markers=[1, 2] entries=[1]")

fails = report_case("entry-no-marker", GOOD_HEAD, "正文没有标记。", GOOD_CITE)
expect("entry without marker", fails, "unused=[1]")

fails = report_case("undeclared", "skills: [conference-result-triage]\ntitle: T\n"
                                 "date: 2026-11-12\nlang: zh-CN",
                    "正文 {{ref_1}} 引用。", GOOD_CITE)
expect("marker without citations line", fails, "no `citations:` line")

fails = report_case("no-skill", "title: T\ndate: 2026-11-12\nlang: zh-CN",
                    "没有引用。", {})
expect("skills not listed", fails, "conference-result-triage")

if failures:
    print(f"\nFAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
print("\nfixture OK")
