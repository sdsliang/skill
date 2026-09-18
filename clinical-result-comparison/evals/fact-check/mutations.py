#!/usr/bin/env python3
"""Negative-control harness for the fact-check scorer.

Usage:  python3 mutations.py            # both arms, needs the two recorded run dirs
        MUT_RUN_A=<dir> MUT_RUN_B=<dir> python3 mutations.py
Exit 0 = every mutation flipped its expected item and both arms covered all items.

A checklist whose items cannot flip proves nothing about a run.  Each mutation is
applied to a throwaway copy of a real run dir; the scorer must report FAIL for at
least one item, the mutated run must exit 3, and the union over all mutations must
cover every fail-severity item in the checklist.

Arm A: the report-producing run R8 (2026-09-16, 2 valid esids).
`NEG_A` gives the same arm two *must stay green* controls: the O19 mixed-sentence shape and the
O20 theme-title shape, so an over-eager exemption shows up as a BAD line instead of a silent pass.
Arm B: the correctly refusing v1 run R6 (1 valid + 1 unusable esid).
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CK = os.path.join(HERE, "check.py")
RUNS = os.path.expanduser("~/.local/state/toolsmith-runs")
WORK = os.environ.get("MUT_WORK", "/tmp/fact-check-mutations")
# Arm A = a report-producing run (R8) ; arm B = a run that correctly refused (R6).
SRC_A = os.environ.get("MUT_RUN_A", os.path.join(RUNS, "20260916-104943-v2-poll"))
SRC_B = os.environ.get("MUT_RUN_B", os.path.join(RUNS, "20260914-174145-b2-refusal"))
COPY_A = ["messages.json", "transcript.md"]
COPY_B = ["debug-history.json"]
MAX_MATCHES = 200   # floor; the real bound is size-relative (see `sub`): M05 legitimately
                    # rewrites every `{{ref_1}}` (~50 in a 15 KB report) and arm B mutates a
                    # ~1 MB debug-history.json where a drug name occurs hundreds of times.


def fresh(name, src, files, with_artifacts):
    d = os.path.join(WORK, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for f in files:
        p = os.path.join(src, f)
        if os.path.isfile(p):
            shutil.copy2(p, d)
    if with_artifacts and os.path.isdir(os.path.join(src, "artifacts")):
        shutil.copytree(os.path.join(src, "artifacts"), os.path.join(d, "artifacts"))
    else:
        os.makedirs(os.path.join(d, "artifacts", "visualizations"), exist_ok=True)
    r = os.path.join(d, "artifacts", "output", "report.md")
    if with_artifacts and os.path.isfile(r):
        seed_original_check(r)
    return (d, r,
            os.path.join(d, "artifacts", "output", "citations.json"),
            os.path.join(d, "artifacts", "visualizations"))


# The recorded baseline run (R8, 2026-09-16) predates the original-source contract, so it
# cannot already contain the `原文核对：` line that contract now requires.  Seed that one line
# into the throwaway baseline copy: every content item still sees the real run's bytes, and the
# four original-source items each keep their own mutation (M17-M20) proving they can flip.
# The seed line deliberately avoids the literal `库内记录`, which would arm the conditional
# divergence item A-P2 on a line that is not a divergence, and it names both a route and a
# source class so that A-P4 (route + class) is satisfied by the seed rather than by accident.
# It deliberately contains neither `PMC<digits>` nor 全文, so M21 can flip A-P5 off the baseline.
SEED_ORIGINAL_CHECK = ("> **原文核对：** 1/2 条已按原文复核（src=1 库内正文即摘要原文，未取更多：无 PMCID）；"
                       "1 条未能复核（src=49 新闻稿：库内正文即通稿原文，未做外部抓取）。\n")


def seed_original_check(report_path):
    t = open(report_path, encoding="utf-8").read()
    lines = t.splitlines(keepends=True)
    lines.insert(1, "\n" + SEED_ORIGINAL_CHECK)
    open(report_path, "w", encoding="utf-8").write("".join(lines))
    return 1


def sub(path, pat, rep, count=0):
    t = open(path, encoding="utf-8").read()
    new, n = re.subn(pat, rep, t, count=count)
    assert n > 0, f"mutation pattern {pat!r} matched nothing in {path}"
    # A replace-all mutation that fires hundreds of times means the pattern was read as a
    # regex by accident (e.g. a literal `| a | b |` becomes an alternation with empty
    # branches and matches at every position) — that corrupts the whole file and silently
    # turns a targeted mutation into "delete everything".
    assert n <= max(MAX_MATCHES, len(t) // 200), \
        f"mutation pattern {pat!r} matched {n} times in {path}"
    open(path, "w", encoding="utf-8").write(new)
    return n


def sub_lit(path, literal, rep, count=1):
    """Replace a literal string (metacharacters escaped) — use for text containing `|` or `{}`."""
    return sub(path, re.escape(literal), rep, count=count)


def score(run_dir, scenario):
    subprocess.run([sys.executable, CK, "--run", run_dir, "--scenario", scenario,
                    "--json", os.path.join(run_dir, "score.json")],
                   capture_output=True, text=True)
    res = json.load(open(os.path.join(run_dir, "score.json"), encoding="utf-8"))
    bad = [i["id"] for i in res["items"] if not i["ok"] and i["severity"] == "fail"]
    return subprocess.run([sys.executable, CK, "--run", run_dir, "--scenario", scenario],
                          capture_output=True, text=True).returncode, bad, res


# --------------------------------------------------------------- arm A mutations

def M01(d, r, c, v):
    return sub(r, "[\u2212-]13\\.9", "\u221219.9")


def M02(d, r, c, v):
    return sub(r, "\\+\\s*3\\.6", "\u22123.6")


def M03(d, r, c, v):
    return sub(r, "NCT04270760", "NCT00000000")


def M04(d, r, c, v):
    return sub(r, "36 ?周", "16 周")


def M05(d, r, c, v):
    return sub(r, "\\{\\{ref_1\\}\\}", "{{ref_9}}")


def M06(d, r, c, v):
    return sub(r, "奥帕司兰", "依洛尤单抗", count=1)


def M07(d, r, c, v):
    return sub(r, "2 ?条", "5 条")


def M08(d, r, c, v):
    j = json.load(open(c, encoding="utf-8"))
    j["ref_1"]["title"] = "Some other paper."
    json.dump(j, open(c, "w"), ensure_ascii=False, indent=1)
    return 1


def M09(d, r, c, v):
    j = json.load(open(c, encoding="utf-8"))
    j["ref_2"]["link"] = j["ref_1"]["link"]
    json.dump(j, open(c, "w"), ensure_ascii=False, indent=1)
    return 1


def M10(d, r, c, v):
    p = os.path.join(v, "endpoint-bar-1.json")
    j = json.load(open(p, encoding="utf-8"))
    j["option"]["data"][0]["value"] = -19.9
    json.dump(j, open(p, "w"), ensure_ascii=False, indent=1)
    return 1


def M11(d, r, c, v):
    json.dump({"id": "chart-visualization-json", "iframe_template": "https://x/y.json",
               "option": {"type": "timeline", "data": []}},
              open(os.path.join(v, "evidence-timeline.json"), "w"))
    return 1


def M12(d, r, c, v):
    os.remove(r)
    return 1


def M13(d, r, c, v):
    p = os.path.join(v, "endpoint-bar-1.json")
    j = json.load(open(p, encoding="utf-8"))
    j.pop("iframe_template", None)
    j["option"]["stack"] = True
    json.dump(j, open(p, "w"), ensure_ascii=False, indent=1)
    return 1


def M14(d, r, c, v):
    j = json.load(open(c, encoding="utf-8"))
    j.pop("ref_2", None)
    json.dump(j, open(c, "w"), ensure_ascii=False, indent=1)
    return 1


def M15(d, r, c, v):  # cross-attribution inside a ref_2-only table row
    return sub_lit(os.path.join(d, "artifacts/output/report.md"),
                   "| 试验 B {{ref_2}} |",
                   "| 试验 B（优于依洛尤单抗）{{ref_2}} |")


def M16(d, r, c, v):  # drop the quantitative chart and say nothing about charts
    os.unlink(os.path.join(v, "endpoint-bar-1.json"))
    return 1


def M17(d, r, c, v):  # answer without any original-source coverage line
    return sub(r, r"原文核对：[^\n]*\n", "")


def M18(d, r, c, v):  # paste a long verbatim run from a fetched original into the report
    src_dir = os.path.join(d, "artifacts", "sources")
    os.makedirs(src_dir, exist_ok=True)
    t = re.sub(r"\s+", "", open(r, encoding="utf-8").read())
    frag = t[200:320]
    assert len(frag) >= 60, "baseline report too short to build a verbatim-copy mutation"
    open(os.path.join(src_dir, "ref_1.abstract.json"), "w", encoding="utf-8").write(frag)
    open(r, "a", encoding="utf-8").write("\n\n" + frag[:100] + "\n")
    return 1


def M19(d, r, c, v):  # quote only the pulled value where the original disagrees (silent one-sided divergence)
    return sub(r, r"\Z", "\n\n库内记录显示主要终点降幅为 −13.9%。\n")


def M20(d, r, c, v):  # keep a hollow coverage line: right shape, no route/class content
    return sub(r, r"原文核对：[^\n]*\n", "> **原文核对：** 2/2 条已复核。\n")


def M21(d, r, c, v):  # archive a PMC full text but declare only the abstract route
    src_dir = os.path.join(d, "artifacts", "sources")
    os.makedirs(src_dir, exist_ok=True)
    open(os.path.join(src_dir, "ref_1.pmc-fulltext.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0"?>\n<article><front><article-title>t</article-title></front>'
        '<body><sec><title>Results</title><p>ORR was 35.0% (95% CI, 23.1-48.4).</p></sec></body></article>\n')
    assert "全文" not in open(r, encoding="utf-8").read(), (
        "baseline already mentions 全文 — M21 could pass by accident")
    return 1


def M23(d, r, c, v):  # echo the template's own spec wording into the delivered report
    return sub(r, r"\Z", "\n\n> **补充说明：** 原文优先于库内加工字段，不一致处同时写出原文值与库内记录值。\n")

def M25(d, r, c, v):
    """Force the chart into the convention the report does *not* use.

    Convention must be read off the baseline, not assumed: arm A's baseline renders
    `-13.9` while an R16-style artifact renders `13.9` + 降幅.  Whichever it is, flipping
    the chart away from it is the mutation; digits are untouched so A-S9 stays green
    (which is what isolates A-S10).
    """
    rep = open(r, encoding="utf-8").read()
    report_signed = bool(re.search(r"[\u2212-]13\.9", rep))
    p = os.path.join(v, "endpoint-bar-1.json")
    j = json.load(open(p, encoding="utf-8"))
    for row in j["option"]["data"]:
        row["value"] = abs(row["value"]) if report_signed else -abs(row["value"])
    json.dump(j, open(p, "w"), ensure_ascii=False, indent=1)
    return 1


def M26(d, r, c, v):  # an H1 that identifies nothing
    return sub(r, r"^# [^\n]*", "# 结果对比报告", count=1)


def N25(d, r, c, v):
    """**False-positive regression (O19)** — a mixed sentence must NOT count as misattribution.

    Shape taken from R15's real conclusion paragraph: one sentence cites `ref_1`, takes ref_1's own
    drug as its subject, and mentions the other trial's drug in an exclusion clause.  The scorer
    must leave A-ATTR-misattribution green (`arm()` asserts that via NEG_A).  Before the O19
    exemption this exact shape failed.
    """
    return sub(r, r"\{\{ref_1\}\}",
               "{{ref_1}}（该构念与奥帕司兰的 Lp(a) 降幅终点不是同一构念，"
               "与依洛尤单抗记录的可比性也不成立）", count=1)


def N26(d, r, c, v):
    """**False-positive regression (O20)** — a theme title with *no* drug name must pass A-T1.

    R16/R17 render `# 脂蛋白(a) 升高人群降脂治疗跨试验对比报告`; the old item failed it.
    """
    return sub(r, r"^# [^\n]*", "# 脂蛋白(a) 升高人群降脂治疗跨试验对比报告", count=1)


def M27(d, r, c, v):
    """The O19 exemption must not become a blanket: a *value* pair stays strict.

    Ref_2's own trial is named in the sentence, so an identity pairing would be exempt — but the
    sentence carries ref_1's number, which is exactly the misattribution the item exists for.
    """
    # A trailing sentence (not a cell) so the unit cites ref_2 alone; ref_2's own trial is named,
    # which would exempt an *identity* pairing — the number is ref_1's and must still be caught.
    return sub(r, r"\Z",
               "\n\n- 试验 2（[OCEAN(a)-DOSE](entity:trial:NCT04270760)）的安慰剂校正 Lp(a) 降幅为"
               " −13.9%，与 [依洛尤单抗](entity:drug:3128) 记录一致{{ref_2}}。\n")


def N27(d, r, c, v):
    """**False-positive regression (O19, second shape)** — R12's real sentence: a contrast clause
    that names the *other* record's trial id in a cited unit (`安全性维度只有 …{{ref_2}}，NCT02729025 未报告…`).
    """
    return sub(r, r"\{\{ref_1\}\}",
               "{{ref_1}}（另一试验 NCT04270760 未报告该指标，无法判定）", count=1)


def M24(d, r, c, v):  # state the rule itself (reworded, not verbatim) instead of a finding
    return sub(r, r"\Z", "\n\n> **补充说明：** 未发现原文与库内记录在同一指标、同一口径上的数值不一致。\n")


def M22(d, r, c, v):  # full text archived AND declared, but the citation still points at the abstract
    src_dir = os.path.join(d, "artifacts", "sources")
    os.makedirs(src_dir, exist_ok=True)
    open(os.path.join(src_dir, "ref_1.pmc-fulltext.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0"?>\n<article><front><article-title>t</article-title></front>'
        '<body><sec><title>Results</title><p>ORR was 35.0% (95% CI, 23.1-48.4).</p></sec></body></article>\n')
    # declare the full-text depth so A-P5 stays satisfied: only the citation link is wrong here
    return sub(r, r"原文核对：[^\n]*\n",
               "> **原文核对：** 2/2 条已复核（src=1 取 PMC 全文 PMC11270764；src=37 库内正文即会议摘要原文）。\n")


MUTS_A = [
    ("M01 minus139", M01, "A-C4-primary-A"),
    ("M02 signflip", M02, "A-N2-no-sign-flip"),
    ("M03 drop-trial-id", M03, "A-C2-trial-identity-B"),
    ("M04 timepoint", M04, "A-C7-timepoints"),
    ("M05 wrong-ref", M05, "A-ATTR-misattribution"),
    ("M06 cross-attribution", M06, "A-T1-title-identifies-scope"),
    ("M07 count-5", M07, "A-N1-no-five-records"),
    ("M08 cite-title", M08, "A-S5-cite-ref1-record"),
    ("M09 cite-dup", M09, "A-S7-cite-distinct"),
    ("M10 chart-value", M10, "A-S9-chart-values"),
    ("M11 chart-timeline", M11, "A-S2-chart-set"),
    ("M12 no-report", M12, "A-S1-artifacts"),
    ("M13 chart-envelope", M13, "A-S8-chart-envelope"),
    ("M14 cite-drop-ref", M14, "A-S3-cite-keys"),
    ("M15 cross-attribution", M15, "A-ATTR-misattribution"),
    ("M16 drop-chart-silent", M16, "A-S2b-chart-or-reason"),
    ("M17 drop-original-check", M17, "A-P1-original-check-line"),
    ("M18 verbatim-copy", M18, "A-P3-no-long-verbatim"),
    ("M19 one-sided-divergence", M19, "A-P2-divergence-shows-both"),
    ("M20 hollow-original-check", M20, "A-P4-original-check-names-route-and-class"),
    ("M21 fulltext-archived-but-undeclared", M21, "A-P5-fulltext-fetch-is-declared"),
    ("M22 fulltext-archived-but-abstract-link", M22, "A-P6-cite-link-is-deepest"),
    ("M23 template-spec-echo", M23, "A-P7-no-template-spec-in-report"),
    ("M24 rule-metastatement", M24, "A-P8-no-rule-metastatement"),
    ("M25 split-convention", M25, "A-S10-sign-convention-consistent"),
    ("M26 generic-title", M26, "A-T1-title-identifies-scope"),
    ("M27 value-misattribution-under-exemption", M27, "A-ATTR-misattribution"),
]

# --------------------------------------------------------------- arm B mutations

def MB01(d, r, c, v):
    os.makedirs(os.path.dirname(r), exist_ok=True)
    open(r, "w").write("# report\n\n| a |\n|---|\n")
    json.dump({"ref_1": {"title": "t", "link": "l", "paper_release_time_str": "2018-12-19"}},
              open(c, "w"))
    return 1


def MB02(d, r, c, v):
    json.dump({"id": "chart-visualization-json"},
              open(os.path.join(v, "endpoint-bar-1.json"), "w"))
    return 1


def MB03(d, r, c, v):
    return sub(os.path.join(d, "debug-history.json"), "我没有生成报告文件", "我已生成报告文件")


def MB04(d, r, c, v):
    return sub(os.path.join(d, "debug-history.json"), "24_1_45608045", "24_1_99999999")


def MB05(d, r, c, v):
    return sub(os.path.join(d, "debug-history.json"), "24_1_30561610", "24_1_88888888")


def MB06(d, r, c, v):
    p = os.path.join(d, "debug-history.json")
    sub(p, "两次检索均未返回任何记录", "两次检索均已返回记录")
    return sub(p, "该记录不存在、当前不可见或已删除", "该记录存在且可见")


def MB07(d, r, c, v):
    p = os.path.join(d, "debug-history.json")
    sub(p, "无法构成两两解读", "能够构成两两解读")
    return sub(p, "不足以构成跨试验对比", "足以构成跨试验对比")


def MB08(d, r, c, v):
    p = os.path.join(d, "debug-history.json")
    sub(p, "确认 `24_1_45608045`", "核实 `24_1_45608045`")
    sub(p, "请重新勾选后再发起一次解读", "可再次发起一次解读")
    return sub(p, "请按上面第 1", "后续任选第 1")


def MB09(d, r, c, v):  # fabricate a finding for the unusable record
    return sub(os.path.join(d, "debug-history.json"),
               "本次只成功取回一个结果记录",
               "24_1_45608045 显示 Lp(a) 显著降低。本次只成功取回一个结果记录")


def MB10(d, r, c, v):
    p = os.path.join(d, "debug-history.json")
    sub(p, "我没有生成报告文件", "本次没有可用产出")
    return sub(p, "因此我没有写入 `/workspace/output/report.md` 与 `/workspace/output/citations.json`，也未做任何文件交付。",
               "这两个路径本次均为空：`/workspace/output/report.md`、`/workspace/output/citations.json`。")


def MB11(d, r, c, v):
    p = os.path.join(d, "debug-history.json")
    sub(p, "依洛尤单抗", "某降脂单抗")
    return sub(p, "evolocumab", "某降脂单抗")


MUTS_B = [
    ("MB01 writes-report", MB01, "B-S1-no-report"),
    ("MB02 writes-chart", MB02, "B-S2-no-charts"),
    ("MB03 claims-produced", MB03, "B-A7-no-production-claim"),
    ("MB04 renames-dead-esid", MB04, "B-A1-name-dead-esid"),
    ("MB05 renames-live-esid", MB05, "B-A4-name-live-esid"),
    ("MB06 drops-no-record", MB06, "B-A2-say-no-record"),
    ("MB07 drops-cannot-produce", MB07, "B-A3-say-cannot-produce"),
    ("MB08 drops-ask-user", MB08, "B-A5-ask-user"),
    ("MB09 fabricates-finding", MB09, "B-A6-no-fabricated-facts"),
    ("MB10 denies-nothing-written", MB10, "B-A8-state-nothing-written"),
    ("MB11 drops-live-drug-name", MB11, "B-C1-live-record-facts-sane"),
]


# --------------------------------------------------------------------- negative controls
# `arm()` proves every item *can* fail.  These prove two items do *not* fail on the shapes that
# wrongly tripped them once (O19 = mixed sentence, O20 = theme title) — a regression guard for the
# exemptions themselves, which the positive list cannot express.
NEG_A = [
    ("N25 mixed-sentence-not-misattributed", N25, "A-ATTR-misattribution"),
    ("N26 theme-title-accepted", N26, "A-T1-title-identifies-scope"),
    ("N27 trial-id-contrast-sentence", N27, "A-ATTR-misattribution"),
]
NEG_B = []
NEG = {"a": NEG_A, "b": NEG_B}


def arm(scenario, src, files, with_artifacts, muts):
    if not os.path.isdir(src):
        print(f"arm {scenario}: SKIP (run dir not found: {src})")
        return True, [], []
    # Score a seeded *copy* as the baseline: the recorded run predates the original-source
    # contract, so its own bytes cannot satisfy A-P1 (see seed_original_check).
    bd, _, _, _ = fresh("baseline", src, files, with_artifacts)
    rc0, bad0, base = score(bd, scenario)
    shutil.rmtree(bd, ignore_errors=True)
    assert rc0 == 0 and not bad0, f"baseline {scenario} not clean: rc={rc0} bad={bad0}"
    total = {i["id"] for i in base["items"] if i["severity"] == "fail"}
    print(f"baseline {scenario}: {len(total)} fail-severity items, all PASS")
    covered, mismatch, ok = set(), [], True
    for name, fn, expect in muts:
        d, r, c, v = fresh(name, src, files, with_artifacts)
        fn(d, r, c, v)
        rc, bad, _ = score(d, scenario)
        hit = "OK "
        if rc != 3 or not bad:
            hit, ok = "BAD", False
        if expect not in bad:
            hit, ok = "BAD", False
            mismatch.append((name, expect, bad))
        covered |= set(bad)
        print(f"[{hit}] {name:22} rc={rc} flipped={bad}")
        shutil.rmtree(d, ignore_errors=True)
    for name, fn, keep_green in NEG.get(scenario, []):
        d, r, c, v = fresh(name, src, files, with_artifacts)
        fn(d, r, c, v)
        rc, bad, _ = score(d, scenario)
        if keep_green in bad:
            hit, ok = "BAD", False
            mismatch.append((name, f"NOT {keep_green}", bad))
            print(f"[{hit}] {name:22} rc={rc} wrongly flipped {keep_green}")
        else:
            print(f"[OK ] {name:22} rc={rc} kept {keep_green} green")
        shutil.rmtree(d, ignore_errors=True)
    missing = sorted(total - covered)
    print(f"arm {scenario}: flipped {len(covered)}/{len(total)}; never flipped {missing}\n")
    return ok and not missing, missing, mismatch


def main():
    os.makedirs(WORK, exist_ok=True)
    okA, missA, badA = arm("a", SRC_A, COPY_A, True, MUTS_A)
    okB, missB, badB = arm("b", SRC_B, COPY_B, False, MUTS_B)
    for name, expect, got in badA + badB:
        print(f"  expected-vs-actual mismatch: {name}: expected {expect}, got {got}")
    for tag, miss in (("a", missA), ("b", missB)):
        if miss:
            print(f"  arm {tag} never flipped: {miss}")
    ok = okA and okB
    print("GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
