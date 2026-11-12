#!/usr/bin/env python3
"""Negative-control harness for the fact-check scorer.

    python3 mutations.py                # builds its own fixture run, no network
    MUT_WORK=/tmp/x python3 mutations.py

A checklist that cannot fail proves nothing about a run, so this file builds one
**legal** synthetic run (which must score PASS), then applies one mutation per
fail-severity item and requires that exact item to flip to FAIL. The union of the
mutations must cover every fail item in ``facts.json`` -- a new item without a
mutation is a gate nobody has ever fired.

Two kinds of control per mutation:
  * MUT -- the item must FAIL;
  * NEG -- a legal variation (same fact, different wording/format) must stay PASS,
    so the scorer cannot be satisfied by crippling it instead of testing it.

Exit 0 = every mutation flipped, every negative control stayed green, full coverage.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CK = os.path.join(HERE, "check.py")
FACTS = os.path.join(HERE, "facts.json")
WORK = os.environ.get("MUT_WORK", "/tmp/fact-check-mutations-tri")

CAPS = {"evidence_strength": 30, "effect_size": 25, "clinical_impact": 25,
        "novelty": 10, "readout_maturity": 10}
BASE_PARTS = {"evidence_strength": 24, "effect_size": 20, "clinical_impact": 16,
              "novelty": 6, "readout_maturity": 4}          # sums to 70


def parts_for(total):
    """Distribute `total` over the five caps without exceeding any of them."""
    out, left = {}, total
    for k in ("evidence_strength", "effect_size", "clinical_impact", "novelty",
              "readout_maturity"):
        take = min(CAPS[k], left)
        out[k] = take
        left -= take
    return out if left == 0 else None


def make_pool(cards):
    pools = {"early": {"items": []}, "pivotal": {"items": []}, "failed": {"items": []}}
    for c in cards:
        pools[c["bucket"]]["items"].append({
            "esid": c["esid"], "title": c["title"], "phase": "Phase III",
            "n": 500, "presentation": "Oral", "results_text": c["_source"],
            "abstract_text": c["_source"], "summary": "", "key_evidence": "是",
        })
    return {"conference": "ESMO 2026", "pools": pools}


def build_fixture(root):
    """A legal run: 12 cards, descending scores, traceable numbers, artifact presented."""
    os.makedirs(os.path.join(root, "artifacts", "output"), exist_ok=True)
    os.makedirs(os.path.join(root, "artifacts", "work", "pool"), exist_ok=True)
    os.makedirs(os.path.join(root, "artifacts", "work", "slices"), exist_ok=True)

    os.makedirs(os.path.join(root, "artifacts", "work", "web"), exist_ok=True)
    raw = []
    for i, (bucket, scores, name) in enumerate((
            ("pivotal", [88, 84, 79, 75, 71], "DeLLphi-305"),
            ("early", [70, 66, 61, 57], "SYS6043"),
            ("failed", [74, 68, 62], "LITESPARK-012"))):
        for j, sc in enumerate(scores):
            title = f"{name} (cohort {j})" if name == "DeLLphi-305" else f"{name} {j}"
            esid = f"nr_24_37_p_{i}{j}abcdef0123456789"
            source = f"{title} met its endpoint with ORR {float(30 + i + j)}% and HR {0.5 + j / 100:.2f}"
            raw.append({"esid": esid, "bucket": bucket, "score": sc,
                        "score_parts": parts_for(sc), "title": title,
                        "summary": f"ORR {float(30 + i + j)}% with HR {0.5 + j / 100:.2f}",
                        # A judgement, not a label: >=60 chars, and not a re-wrap of
                        # `summary` (that pair of rules is what A-P5 audits).
                        "why": ("该人群至今没有确立的二线标准，随机对照把主要终点打成阳性，"
                                "效应量足以改写这一线的治疗选择；局限是随访仍短，"
                                "总生存尚未成熟，且入组排除了经过免疫治疗进展的患者。"),
                        "_source": source})
    cards = []
    for n, c in enumerate(raw):
        card = {k: v for k, v in c.items() if not k.startswith("_")}
        # `listed_company` is mandatory on every card; one card carries a fully
        # sourced company so the shape check has something legal to accept.
        card["listed_company"] = (
            {"name": "Tango Therapeutics", "ticker": "TNGX", "exchange": "NASDAQ",
             # A window move, not an attribution: the `basis` string travels with the
             # number so a reader cannot mistake it for "rose because of the abstract".
             "reaction": {"from_date": "2026-10-16", "to_date": "2026-10-19",
                          "prev_close": 22.04, "close": 23.53, "change_pct": 6.76,
                          "basis": "meeting-window first session vs prior close (not attributed)",
                          "source_url": "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=105.TNGX"},
             "source_url": "https://investors.tangotx.com/"} if n == 0 else None)
        cards.append(card)

    watchlist = {"conference": "ESMO 2026", "count": len(cards), "cards": cards,
                 "coverage_notes": ["数据类型无明确首次/更新依据则未判定。",
                                    "部分摘要无 p 或 HR；本榜不代表会议全量覆盖。"]}
    pool = make_pool(raw)

    # One pivotal card stands in for an LBA row: the shape that used to vanish
    # when `evidence_source` carried "前瞻性研究" instead of a phase.
    pool["pools"]["pivotal"]["items"][0]["lba"] = True
    rows = [{"clinical_result__id": pool["pools"]["pivotal"]["items"][0]["esid"],
             "clinical_result_lba": "LBA"}]
    rows += [{"clinical_result__id": c["esid"], "clinical_result_lba": None}
             for c in cards[1:]]

    for rel, obj in (("artifacts/output/watchlist.json", watchlist),
                     ("artifacts/work/pool/pool.json", pool),
                     ("artifacts/work/rows.json", {"rows": rows,
                                                   "sources": [{"dump": f"slice_{n:02d}.jsonl", "rows": 1}
                                                               for n in range(1, 9)]})):
        with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    # The split itself is the primary slicing evidence: 8 slice files, each far below
    # the truncation threshold, whose union is every id in rows.json.
    ids = [r["clinical_result__id"] for r in rows]
    per = max(1, len(ids) // 8)
    for n in range(8):
        chunk = ids[n * per:(n + 1) * per] if n < 7 else ids[7 * per:]
        with open(os.path.join(root, "artifacts", "work", "slices", f"slice_{n + 1:02d}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(chunk, f)

    # The web-curation step has to leave re-checkable evidence: one JSON line per
    # query, per bucket. Without it the step is unverifiable after the turn ends.
    for bucket in ("pivotal", "early", "failed"):
        recs = [{"query": f"ESMO 2026 {bucket} trial results {n}",
                 "title": f"ESMO 2026 {bucket} round-up {n}",
                 "url": f"https://example.org/esmo-2026/{bucket}-{n}",
                 "published_at": "2026-10-20", "note": "media coverage"}
                for n in (1, 2, 3, 4)]
        with open(os.path.join(root, "artifacts", "work", "web", f"{bucket}.jsonl"),
                  "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Quote evidence shares the web surface but records market calls, not searches.
    with open(os.path.join(root, "artifacts", "work", "web", "quotes.jsonl"),
              "w", encoding="utf-8") as f:
        f.write(json.dumps({"ticker": "TNGX", "exchange": "NASDAQ", "secid": "105.TNGX",
                            "from_date": "2026-10-16", "to_date": "2026-10-19",
                            "prev_close": 22.04, "close": 23.53, "change_pct": 6.76,
                            "url": "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=105.TNGX"},
                           ensure_ascii=False) + "\n")

    with open(os.path.join(root, "artifacts.json"), "w", encoding="utf-8") as f:
        json.dump([{"path": "/workspace/output/watchlist.json"},
                   {"path": "/workspace/work/pool/pool.json"},
                   {"path": "/workspace/work/rows.json"}], f)

    calls = []
    for n in range(8):
        calls.append({"tool_name": "pharmcube-query-clinical-result-with-params",
                      "args": {"esids": [f"id{i}" for i in range(150)], "meeting_tags": "ESMO 2026"},
                      "part_kind": "tool-call"})
    calls.append({"tool_name": "present_artifact",
                  "args": {"path": "/workspace/output/watchlist.json"},
                  "part_kind": "tool-call"})
    hist = {"raw_model_messages": [{"parts": calls, "usage": {}}]}
    with open(os.path.join(root, "debug-history.json"), "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False)

    reply = ("每桶 pivotal 5 / early 4 / failed 3。check_cards.py: OK cards=12。"
             "两条边界：data_type 大量为未判定；只有约一半记录带 p 值或 HR，"
             "判不出来的不参与排序。")
    with open(os.path.join(root, "messages.json"), "w", encoding="utf-8") as f:
        json.dump([{"parts": [{"part_kind": "text", "content": reply}]}], f, ensure_ascii=False)

    with open(os.path.join(root, "transcript.md"), "w", encoding="utf-8") as f:
        f.write("# fixture run\n\nrows=1097 lba=73 with_abstract_text=1097\n"
                "coverage: 1097/1097 ids present\ncandidates 179 / missing abstract 0\n"
                "OK cards=12\n")
    return root


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return json.load(f)


def write(root, rel, obj):
    with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def run_check(root):
    r = subprocess.run([sys.executable, CK, "--run", root, "--json",
                        os.path.join(root, "score.json")],
                       capture_output=True, text=True)
    sc = {}
    try:
        sc = json.load(open(os.path.join(root, "score.json"), encoding="utf-8"))
    except Exception:
        pass
    return r.returncode, sc, (r.stdout + r.stderr)


# --------------------------------------------------------------------------- #
# mutations: one per fail-severity item
# --------------------------------------------------------------------------- #
def m_bucket_cap(root):
    w = read(root, "artifacts/output/watchlist.json")
    extra = copy.deepcopy(w["cards"][0])
    while sum(1 for c in w["cards"] if c["bucket"] == "pivotal") <= 10:
        e = copy.deepcopy(extra)
        e["esid"] = e["esid"] + f"_x{len(w['cards'])}"
        w["cards"].append(e)
    w["count"] = len(w["cards"])
    write(root, "artifacts/output/watchlist.json", w)


def m_count(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["count"] = len(w["cards"]) + 7
    write(root, "artifacts/output/watchlist.json", w)


def m_bucket(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["bucket"] = "keep"
    write(root, "artifacts/output/watchlist.json", w)


def m_dup(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"].append(copy.deepcopy(w["cards"][1]))
    w["count"] = len(w["cards"])
    write(root, "artifacts/output/watchlist.json", w)


def m_score_range(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["score"] = 140
    write(root, "artifacts/output/watchlist.json", w)


def m_score_parts(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["score_parts"]["novelty"] = 40
    write(root, "artifacts/output/watchlist.json", w)


def m_score_flat(root):
    w = read(root, "artifacts/output/watchlist.json")
    for c in w["cards"]:
        c["score"] = 60
        c["score_parts"] = parts_for(60)
    write(root, "artifacts/output/watchlist.json", w)


def m_score_order(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"].reverse()
    write(root, "artifacts/output/watchlist.json", w)


def m_abstract_id(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["abstract_id"] = "5RO"
    write(root, "artifacts/output/watchlist.json", w)


def m_manual(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][1]["manual"] = False
    write(root, "artifacts/output/watchlist.json", w)


def m_esid(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["esid"] = "nr_made_up_id"
    write(root, "artifacts/output/watchlist.json", w)


def m_number(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["summary"] = "ORR 97% with HR 0.11"
    write(root, "artifacts/output/watchlist.json", w)


def m_no_present(root):
    h = read(root, "debug-history.json")
    parts = [p for p in h["raw_model_messages"][0]["parts"] if p["tool_name"] != "present_artifact"]
    h["raw_model_messages"][0]["parts"] = parts
    write(root, "debug-history.json", h)


def m_json_paste(root):
    msgs = read(root, "messages.json")
    msgs[0]["parts"][0]["content"] += "\n```json\n" + json.dumps({"cards": [{"x": "y" * 200}] * 40}) + "\n```\n"
    write(root, "messages.json", msgs)


def m_lba_dropped(root):
    """Dropping the LBA flag is what "前瞻性研究" used to do silently."""
    p = read(root, "artifacts/work/pool/pool.json")
    p["pools"]["pivotal"]["items"][0]["lba"] = False
    p["excluded"] = dict(p.get("excluded") or {}, **{"前瞻性研究": 16})
    write(root, "artifacts/work/pool/pool.json", p)


def m_notes(root):
    """Dropping the honest limits turns the JSON into a claim of full coverage."""
    w = read(root, "artifacts/output/watchlist.json")
    w.pop("coverage_notes", None)
    write(root, "artifacts/output/watchlist.json", w)


def m_coverage(root):
    p = os.path.join(root, "transcript.md")
    txt = open(p, encoding="utf-8").read().replace("coverage: 1097/1097 ids present", "")
    open(p, "w", encoding="utf-8").write(txt)


def m_wide_pull(root):
    """The defect: skip `plan_slices.py` and ask for the whole conference at once.

    One giant slice (all 1097 ids in slice_01.json) is exactly what a `--size 5000`
    run looks like, and it is the call shape that silently truncates.
    """
    sdir = os.path.join(root, "artifacts", "work", "slices")
    ids = []
    for name in sorted(os.listdir(sdir)):
        if name.startswith("slice_"):
            ids.extend(json.load(open(os.path.join(sdir, name), encoding="utf-8")))
            os.remove(os.path.join(sdir, name))
    with open(os.path.join(sdir, "slice_01.json"), "w", encoding="utf-8") as f:
        json.dump(ids, f)


def m_direct_es(root):
    p = os.path.join(root, "transcript.md")
    open(p, "a", encoding="utf-8").write("\ncurl -s $ES_HOST/np_clinical/_search?size=10\n")


def m_why_depth(root):
    """Both branches of A-P5 in one mutation: a label, and a number restated."""
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["why"] = "数据好，值得关注"
    c = w["cards"][1]
    c["why"] = c["summary"] + "，此外这项研究的人群与对照设置都值得注意，" \
               "随访成熟后可能改变一线选择，但目前的入组经过高度筛选。"
    write(root, "artifacts/output/watchlist.json", w)


def m_listed_missing(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0].pop("listed_company", None)
    write(root, "artifacts/output/watchlist.json", w)


def m_listed_bare(root):
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["listed_company"] = {"name": "某公司", "ticker": "",
                                       "exchange": "HKEX", "source_url": "n/a"}
    write(root, "artifacts/output/watchlist.json", w)


def m_promoted_missing(root):
    w = read(root, "artifacts/output/watchlist.json")
    c = copy.deepcopy(w["cards"][0])
    c["esid"] = "nr_24_37_p_notinpool"
    c.pop("promoted", None)
    w["cards"].append(c)
    w["count"] = len(w["cards"])
    write(root, "artifacts/output/watchlist.json", w)


def m_web_missing(root):
    shutil.rmtree(os.path.join(root, "artifacts", "work", "web"), ignore_errors=True)


def m_web_no_urls(root):
    """Recording searches without their sources is not evidence of searching."""
    wdir = os.path.join(root, "artifacts", "work", "web")
    for name in os.listdir(wdir):
        if not name.endswith(".jsonl"):
            continue
        p = os.path.join(wdir, name)
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        for r in rows:
            r["url"] = ""
        with open(p, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def m_reaction_skewed(root):
    """A percentage that does not follow from its own two closes."""
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["listed_company"]["reaction"]["change_pct"] = 12.4
    write(root, "artifacts/output/watchlist.json", w)


def m_reaction_untraced(root):
    """A price move with nothing durable behind it: the file it should point at is gone."""
    os.remove(os.path.join(root, "artifacts", "work", "web", "quotes.jsonl"))


def ngen_web_declared(root):
    """A dead provider may degrade the deliverable -- but only by saying so in it."""
    shutil.rmtree(os.path.join(root, "artifacts", "work", "web"), ignore_errors=True)
    w = read(root, "artifacts/output/watchlist.json")
    # If the web layer never ran, no quote was fetched either: printing a move would
    # be claiming a number whose evidence this same variation just deleted.
    for card in w["cards"]:
        if isinstance(card.get("listed_company"), dict):
            card["listed_company"].pop("reaction", None)
    w.setdefault("coverage_notes", []).append(
        "联网检索不可用（provider 无返回），本次未做外部热度校正与上市公司核实，"
        "listed_company 一律留空。")
    write(root, "artifacts/output/watchlist.json", w)


MUTATIONS = [
    ("A-D1-full-coverage", m_coverage),
    ("A-D2-sliced-pulls", m_wide_pull),
    ("A-D3-no-direct-es", m_direct_es),
    ("A-S1-bucket-cap", m_bucket_cap),
    ("A-S2-count-field", m_count),
    ("A-S3-buckets-legal", m_bucket),
    ("A-S4-unique-esid", m_dup),
    ("A-P1-score-integer", m_score_range),
    ("A-P2-score-parts", m_score_parts),
    ("A-P3-score-varied", m_score_flat),
    ("A-P4-score-order", m_score_order),
    ("A-F1-abstract-id-null", m_abstract_id),
    ("A-F2-manual-null", m_manual),
    ("A-F3-esid-in-pool", m_esid),
    ("A-F4-numbers-traceable", m_number),
    ("A-T1-present-artifact", m_no_present),
    ("A-T2-no-json-paste", m_json_paste),
    ("A-H1-two-honest-claims", m_notes),
    ("A-D4-lba-not-dropped", m_lba_dropped),
    ("A-P5-why-depth", m_why_depth),
    ("A-F5-listed-company", m_listed_missing),
    ("A-F6-promotion-traceable", m_promoted_missing),
    ("A-W1-web-evidence", m_web_missing),
    ("A-W1-web-evidence", m_web_no_urls),
    ("A-F7-reaction-traceable", m_reaction_skewed),
    ("A-F7-reaction-traceable", m_reaction_untraced),
]

# Legal variations that must stay green: the scorer should test facts, not formatting.
def ngen_legal_reorder(root):
    """Reverse the order *between* buckets -- order is only meaningful inside one."""
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"].sort(key=lambda c: c["bucket"])
    write(root, "artifacts/output/watchlist.json", w)


def ngen_why_varied(root):
    """A `why` at the 60-char floor with different wording must stay green."""
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["why"] = ("该适应症长期缺少随机对照证据，这次把主要终点做成阳性，"
                            "效应量足够支撑一个二线新选择；但总生存尚未成熟，"
                            "且入组排除了免疫经治者，外推要谨慎。")
    write(root, "artifacts/output/watchlist.json", w)


def ngen_listed_legal(root):
    """A different but fully sourced company shape must stay green."""
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][1]["listed_company"] = {"name": "四川科伦博泰生物医药股份有限公司",
                                       "ticker": "06990", "exchange": "HKEX",
                                       "source_url": "https://www.hkexnews.hk/"}
    write(root, "artifacts/output/watchlist.json", w)


def ngen_web_empty_url_noted(root):
    """A search that returned nothing usable still counts -- if it says so."""
    wdir = os.path.join(root, "artifacts", "work", "web")
    p = os.path.join(wdir, "pivotal.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    rows[0]["url"] = ""
    rows[0]["note"] = "检索已执行；无可用外部读数"
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def ngen_reaction_absent(root):
    """Omitting the move entirely is legal -- it is an enhancement, not a requirement."""
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["listed_company"].pop("reaction", None)
    write(root, "artifacts/output/watchlist.json", w)


def ngen_heat_hit(root):
    """Putting a heat trial on the list must satisfy the warn item, not break a fail one."""
    w = read(root, "artifacts/output/watchlist.json")
    w["cards"][0]["title"] = "DeLLphi-305 (ES-SCLC)"
    write(root, "artifacts/output/watchlist.json", w)


NEGATIVES = [("legal bucket reorder", ngen_legal_reorder),
             ("heat trial titled", ngen_heat_hit),
             ("why at the length floor", ngen_why_varied),
             ("fully sourced HK company", ngen_listed_legal),
             ("web down but declared in coverage_notes", ngen_web_declared),
             ("search with no usable result, noted", ngen_web_empty_url_noted),
             ("reaction omitted entirely", ngen_reaction_absent)]


def main() -> int:
    facts = json.load(open(FACTS, encoding="utf-8"))
    fail_ids = [i["id"] for i in facts["items"] if i.get("severity", "fail") == "fail"]
    base_dir = os.path.join(WORK, "base")
    shutil.rmtree(WORK, ignore_errors=True)
    build_fixture(base_dir)

    code, sc, out = run_check(base_dir)
    if code != 0:
        print("BASELINE fixture does not pass — the harness is broken, not the skill:")
        print(out)
        return 1
    print(f"baseline: PASS facts {sc.get('ok')}/{sc.get('total')}")

    covered, bad = set(), []
    for n, (item_id, mutate) in enumerate(MUTATIONS):
        # Two mutations may target the same fact (one per branch); the dir has to differ.
        root = os.path.join(WORK, f"{n:02d}-{item_id}")
        shutil.copytree(base_dir, root)
        mutate(root)
        code, sc, out = run_check(root)
        fails = set(sc.get("fails") or [])
        if item_id in fails:
            covered.add(item_id)
            print(f"  ok  {item_id:26} -> FAIL (as required)")
        else:
            bad.append(f"{item_id}: mutation did not flip it (exit {code}, fails={sorted(fails)})")
            print(f"  BAD {item_id:26} -> still passing")

    for label, mutate in NEGATIVES:
        root = os.path.join(WORK, "neg-" + label.replace(" ", "-"))
        shutil.copytree(base_dir, root)
        mutate(root)
        code, sc, _ = run_check(root)
        if code == 0:
            print(f"  ok  NEG {label:26} -> still PASS")
        else:
            bad.append(f"NEG {label}: legal variation failed {sorted(sc.get('fails') or [])}")
            print(f"  BAD NEG {label} -> FAIL {sorted(sc.get('fails') or [])}")

    missing = [i for i in fail_ids if i not in covered]
    if missing:
        bad.append(f"items with no mutation: {missing}")

    if bad:
        print(f"\nFAIL ({len(bad)}):")
        for b in bad:
            print("  -", b)
        return 1
    print(f"\ncoverage: {len(covered)}/{len(fail_ids)} fail items have a mutation; "
          f"{len(NEGATIVES)} negative controls green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
