#!/usr/bin/env python3
"""Negative-control harness for the fact-check scorer.

Usage:  python3 mutations.py            # both arms, needs the two recorded run dirs
        MUT_RUN_A=<dir> MUT_RUN_B=<dir> python3 mutations.py
Exit 0 = every mutation flipped its expected item and both arms covered all items.

A checklist whose items cannot flip proves nothing about a run.  Each mutation is
applied to a throwaway copy of a real run dir; the scorer must report FAIL for at
least one item, the mutated run must exit 3, and the union over all mutations must
cover every fail-severity item in the checklist.

Arm A: the report-producing run R17 (2026-09-18, 2 valid esids, sign-convention round).  It is a
real, fully-passing artifact (43/43 under evaluator r2) and it already carries the
`原文核对：` line, so the baseline is scored as recorded — nothing is seeded into the copy.
`NEG_A` gives the same arm four *must stay green* controls: the two O19 mixed-sentence shapes,
the O20 "both subjects named" title, and the legal L3 full-text shape (N28 = archive + full-text
link + declaration, i.e. R14's real form), so an over-eager exemption or a mis-attributed archive
shows up as a BAD line instead of a silent pass.
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
# Arm A = a report-producing run (R17) ; arm B = a run that correctly refused (R6).
SRC_A = os.environ.get("MUT_RUN_A", os.path.join(RUNS, "20260918-095553-r17-sign-convention"))
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
    return (d,
            os.path.join(d, "artifacts", "output", "report.md"),
            os.path.join(d, "artifacts", "output", "citations.json"),
            os.path.join(d, "artifacts", "visualizations"))


# Synthetic nonclinical carrier; never a source fixture or evidence of an actual article.
FT_XML = ('<?xml version="1.0"?>\n<article><front><article-title>Synthetic blocks</article-title></front>'
          '<body><sec><title>Results</title><p>Colored wooden blocks were sorted by shape on a table. '
          'This is a synthetic nonclinical evaluator test.</p></sec></body></article>\n')
# The full-text-depth declaration M22/N28 write into the coverage line (A-P5 stays satisfied there,
# so the only thing under test is where the citation points and whether bytes exist).
FT_LINE = ("> **原文核对：** 2/2 条已复核（src=1 取 PMC 全文 PMC11270764；"
           "src=37 库内正文即会议摘要原文）。\n")


def ft_body(pmid, pmcid="PMC11270764"):
    """Synthetic nonclinical JATS: IDs exercise mapping logic, never establish source facts.

    This is not the paper at the supplied PMID/PMCID. Only test copies receive it.
    Real R14 evidence is independently checked by rescore_revision.py.
    """
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<article xml:lang="en" article-type="research-article"><front><article-meta>'
            f'<article-id pub-id-type="pmcid">{pmcid}</article-id>'
            f'<article-id pub-id-type="pmid">{pmid}</article-id>'
            '</article-meta></front><body><sec><title>Results</title>'
            '<p>SYNTHETIC TEST ONLY: colored wooden blocks were sorted by shape on a table. '
            'The inventory recorded square, round and triangular blocks separately.</p></sec></body></article>\n')


def archive_fulltext(d, c, pmcid="PMC11270764"):
    """Archive a body as **R14 did it** — named by PMCID, not by `ref_<n>` — and return the citations.

    Real runs name these files after the article (`PMC11270764_fulltext_jats.xml`) or after the esid
    (`<esid>.<route>.xml`); the `ref_<n>` prefix is a harness convenience.  Using the real naming here
    is what keeps the harness honest about O29 instead of encoding the bug it was written for.
    """
    j = json.load(open(c, encoding="utf-8"))
    m = re.search(r"(?<!\d)(\d{7,8})(?!\d)", str(j.get("ref_1", {}).get("link") or ""))
    assert m, "baseline ref_1 link carries no PMID — cannot build an attributable body"
    src = os.path.join(d, "artifacts", "sources")
    os.makedirs(src, exist_ok=True)
    open(os.path.join(src, f"{pmcid}_fulltext_jats.xml"), "w", encoding="utf-8").write(ft_body(m.group(1), pmcid))
    return j


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
    proc = subprocess.run([sys.executable, CK, "--run", run_dir, "--scenario", scenario,
                           "--json", os.path.join(run_dir, "score.json")],
                          capture_output=True, text=True)
    if proc.returncode not in (0, 3):
        raise RuntimeError(f"scorer unusable rc={proc.returncode}: {proc.stderr or proc.stdout}")
    res = json.load(open(os.path.join(run_dir, "score.json"), encoding="utf-8"))
    bad = [i["id"] for i in res["items"] if not i["ok"] and i["severity"] == "fail"]
    return proc.returncode, bad, res


# --------------------------------------------------------------- arm A mutations

def M01(d, r, c, v):  # bill the primary endpoint with a value that is not the record's
    # Both renderings must go: R17 writes `−13.9%（95% CI …）` in the tables *and* a bare
    # `13.9%` in the direction paragraph, and A-C4's pattern makes the sign optional —
    # replacing only the signed form left the item green (first draft of this rewrite).
    return sub(r, r"(?<![\d.])13\.9", "19.9")


def M02(d, r, c, v):
    return sub(r, "\\+\\s*3\\.6", "\u22123.6")


def M03(d, r, c, v):  # strip record B's registration identity out of every ref_2 block
    # A-C2 needs *all three* of its patterns inside blocks citing ref_2, so dropping the two
    # identity strings is enough; the drug name alone cannot satisfy it.
    # `count=0` = all 22 occurrences (sub_lit defaults to 1).
    return sub_lit(r, "[OCEAN(a)-DOSE](entity:trial:NCT04270760)",
                   "[该项研究](entity:trial:NCT99999999)", count=0)


def M04(d, r, c, v):
    return sub(r, "36 ?周", "16 周")


def M05(d, r, c, v):
    return sub(r, "\\{\\{ref_1\\}\\}", "{{ref_9}}")


def M06(d, r, c, v):  # an H1 that names exactly one of the two subjects
    # The "写成同一个药" branch of A-T1-title-identifies-scope (O20): a theme title is legal, a
    # title naming *one* drug is not.  M26 exercises the "identifies nothing" branch.
    return sub(r, r"^# [^\n]*", "# 依洛尤单抗 跨试验对比报告", count=1)


def M07(d, r, c, v):  # narrate the duplicated rows as five records
    # Replaces every `2 条` (纳入结果, 原文核对 `2/2 条`, `2 条仅摘要级`) so the forbidden
    # `5 条记录` register appears and A-C12's `2 条/项` disappears in the same stroke.
    return sub(r, r"2 ?条", "5 条记录")


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


def M15(d, r, c, v):  # cross-attribution inside a ref_2-only table row (identity, not a value)
    # R17's row is `| [OCEAN(a)-DOSE](…) | [奥帕司兰](drug:11859) 10 mg Q12W | … | −70.5%…{{ref_2}} |`;
    # swapping the drug cell to the *other* record's drug leaves the cell citing ref_2 alone, so the
    # identity exemption cannot fire (no ref_2 identity is named any more) and A-ATTR must flag it.
    return sub_lit(r, "| [奥帕司兰](entity:drug:11859) 10 mg Q12W |",
                   "| [依洛尤单抗](entity:drug:3128) 10 mg Q12W |")


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


def M21(d, r, c, v):  # full text archived, but the coverage line declares only the abstract route
    # R17's own coverage line already names `PMCID PMC6933872` and 全文 (it records that R7 came back
    # 500 for a non-OA journal), so merely archiving a body cannot flip A-P5 here.  The mutation
    # therefore also rewrites the line into an explicit abstract-only declaration — which is exactly
    # the shape the item exists to catch: a 99 KB PMC body on disk, a reader told it was all abstracts.
    src_dir = os.path.join(d, "artifacts", "sources")
    os.makedirs(src_dir, exist_ok=True)
    open(os.path.join(src_dir, "ref_1.pmc-fulltext.xml"), "w", encoding="utf-8").write(FT_XML)
    return sub(r, r"原文核对：[^\n]*\n",
               "> **原文核对：** 2/2 条已复核（src=1：PMID 30561610 按库内摘要核对，该刊非 OA；"
               "src=1：PMID 36342163 按库内摘要核对，非 OA 不可复核）。\n")


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
    """**False-positive regression (O19, shape 1)** — a mixed sentence must NOT count as misattribution.

    Shape taken from R15's real conclusion: one sentence cites `ref_1`, takes ref_1's own drug as its
    subject, and mentions the other trial's drug in an exclusion clause.  The scorer must leave
    A-ATTR-misattribution green (`arm()` asserts that via NEG_A).  Before the O19 exemption this exact
    shape failed.  Appended as its own sentence so the unit cites `ref_1` alone (in R17 every prose
    sentence carrying a marker already cites both records, which would make the control vacuous).
    """
    return sub(r, r"\Z",
               "\n\n- 该影像学结果与[奥帕司兰](entity:drug:11859) 的 Lp(a) 降幅终点不是同一构念，"
               "[依洛尤单抗](entity:drug:3128) 一栏因此不作优效推断{{ref_1}}。\n")


def N26(d, r, c, v):
    """**False-positive regression (O20)** — the *other* legal H1 shape: both subjects named.

    R17's baseline is already a theme title (`# 脂蛋白(a) 升高人群降脂治疗跨试验对比报告`), so the
    baseline run itself proves that branch; this control proves the first branch (both subjects named)
    still passes after the O20 rewrite, without touching the theme branch.
    """
    return sub(r, r"^# [^\n]*",
               "# Lp(a) 升高人群降脂治疗：[依洛尤单抗](entity:drug:3128) vs "
               "[奥帕司兰](entity:drug:11859) 跨试验对比报告", count=1)


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
    """**False-positive regression (O19, shape 2)** — R12's real sentence: a contrast clause that
    names the *other* record's registration number inside a unit that cites only ref_2.

    The unit names ref_2's own trial first, which is what makes the trailing contrast legal.
    """
    return sub(r, r"\Z",
               "\n\n- 安全性维度只有 [OCEAN(a)-DOSE](entity:trial:NCT04270760) 一方直接报告总体不良事件"
               "发生率组间相似，[NCT02729025](entity:trial:NCT02729025) 未报告安全性数据，"
               "无法判定谁更安全{{ref_2}}。\n")


def M24(d, r, c, v):  # state the rule itself (reworded, not verbatim) instead of a finding
    return sub(r, r"\Z", "\n\n> **补充说明：** 未发现原文与库内记录在同一指标、同一口径上的数值不一致。\n")


def M22(d, r, c, v):  # full text archived AND declared, but the citation still points at the abstract
    # O29: the body must be attributable for this item to fire at all.  Named by PMCID (R14's real
    # convention) and carrying the record's own PMID, it reaches ref_1 through the link's PMID —
    # while the *link* stays the PubMed page, which is precisely the failure.  The pre-2026-09-18
    # version of this mutation wrote an anonymous body called `ref_1.pmc-fulltext.xml`, so it proved
    # the item could bite while the item itself never bit on a real artifact.
    archive_fulltext(d, c)
    return sub(r, r"原文核对：[^\n]*\n", FT_LINE)


def M28(d, r, c, v):  # claim full-text depth without fetching anything (the converse of A-P6)
    # Nothing is archived: the citation alone says "analysed from the full text".  A-S5 accepts the
    # upgrade (both whitelisted full-text forms do), A-P5/A-P6 stay untriggered (no body), so only
    # A-P9 can catch it — which is the entire point of closing the loop.
    j = json.load(open(c, encoding="utf-8"))
    j["ref_1"]["link"] = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11270764/"
    json.dump(j, open(c, "w"), ensure_ascii=False, indent=1)
    return 1


def M29(d, r, c, v):
    """Swap two chart labels while leaving the sorted magnitude bag unchanged."""
    p = os.path.join(v, "endpoint-bar-1.json")
    j = json.load(open(p, encoding="utf-8"))
    j["option"]["data"][0]["label"], j["option"]["data"][1]["label"] = (
        j["option"]["data"][1]["label"], j["option"]["data"][0]["label"])
    json.dump(j, open(p, "w"), ensure_ascii=False, indent=1)
    return 1


def M30(d, r, c, v):
    """Flip one chart observation's sign without changing its magnitude."""
    p = os.path.join(v, "endpoint-bar-1.json")
    j = json.load(open(p, encoding="utf-8"))
    j["option"]["data"][1]["value"] = abs(j["option"]["data"][1]["value"])
    json.dump(j, open(p, "w"), ensure_ascii=False, indent=1)
    return 1


def M31(d, r, c, v):
    """Replace the expected bar chart with a wrong line chart."""
    p = os.path.join(v, "endpoint-bar-1.json")
    j = json.load(open(p, encoding="utf-8"))
    j["option"]["type"] = "line"
    os.rename(p, os.path.join(v, "endpoint-line-1.json"))
    json.dump(j, open(os.path.join(v, "endpoint-line-1.json"), "w"), ensure_ascii=False, indent=1)
    return 1


def M32(d, r, c, v):
    """Attach an unsigned B value to ref_1, the reviewer-found ownership hole."""
    return sub(r, r"\Z", "\n\n依洛尤单抗降低 70.5%{{ref_1}}。\n")


def M33(d, r, c, v):
    """Use an empty PMC filename and matching citation URL: filename equality is not evidence."""
    j = json.load(open(c, encoding="utf-8"))
    j["ref_1"]["link"] = "https://pmc.ncbi.nlm.nih.gov/articles/PMC99999999/"
    json.dump(j, open(c, "w"), ensure_ascii=False, indent=1)
    src = os.path.join(d, "artifacts", "sources")
    os.makedirs(src, exist_ok=True)
    open(os.path.join(src, "PMC99999999_fulltext_jats.xml"), "w", encoding="utf-8").write("")
    return 1


def M34(d, r, c, v):
    """Archive nonempty full-text-shaped content with no independent PMID/PMCID."""
    src = os.path.join(d, "artifacts", "sources")
    os.makedirs(src, exist_ok=True)
    open(os.path.join(src, "PMC99999999_fulltext_jats.xml"), "w", encoding="utf-8").write(
        "<article><body><p>nonempty body without independent article mapping</p></body></article>")
    return 1


def M35(d, r, c, v):
    """A different allowed bar filename must not bypass observation validation."""
    M29(d, r, c, v)
    os.rename(os.path.join(v, "endpoint-bar-1.json"), os.path.join(v, "endpoint-bar-7.json"))
    return 1


def M36(d, r, c, v):
    """Matching PMCID but a different article PMID cannot back the selected source."""
    j = archive_fulltext(d, c, "PMC99999999")
    path = os.path.join(d, "artifacts", "sources", "PMC99999999_fulltext_jats.xml")
    open(path, "w", encoding="utf-8").write(ft_body("87654321", "PMC99999999"))
    j["ref_1"]["link"] = "https://pmc.ncbi.nlm.nih.gov/articles/PMC99999999/"
    json.dump(j, open(c, "w"), ensure_ascii=False)
    return 1


def M37(d, r, c, v):
    open(os.path.join(v, "endpoint-bar-1.json"), "w").write("{broken")
    return 1


def M38(d, r, c, v):
    return sub(r, r"\Z", "\n原文 36.0；库内记录 18.5{{ref_1}}。库内记录 90{{ref_1}}。\n")


def chart_tooltip_conflict(v, label):
    path = os.path.join(v, "endpoint-bar-1.json")
    chart = json.load(open(path, encoding="utf-8"))
    row = chart["option"]["data"][0]
    row["description"] = row["label"] + " " + row["description"]
    row["label"] = label
    json.dump(chart, open(path, "w"), ensure_ascii=False)
    return 1


def M39(d, r, c, v):
    return chart_tooltip_conflict(v, "奥帕司兰")


def M40(d, r, c, v):
    return chart_tooltip_conflict(v, "依洛尤单抗 75 mg")


def M41(d, r, c, v):
    return chart_tooltip_conflict(v, "依洛尤单抗 第 36 周")


def M42(d, r, c, v):
    j = json.load(open(c, encoding="utf-8"))
    pmid = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", j["ref_1"]["link"])[1]
    j["ref_1"]["link"] = "https://pmc.ncbi.nlm.nih.gov/articles/PMC99999999/"
    json.dump(j, open(c, "w"), ensure_ascii=False)
    src = os.path.join(d, "artifacts", "sources")
    os.makedirs(src, exist_ok=True)
    open(os.path.join(src, "PMC99999999_plain.txt"), "w").write(
        f"PMC99999999 PMID:{pmid}\nMethods\n" + "x" * 200)
    return 1


MUTS_A = [
    ("M39 tooltip-hides-wrong-drug", M39, "A-S9b-chart-observation-identity"),
    ("M40 tooltip-hides-wrong-dose", M40, "A-S9b-chart-observation-identity"),
    ("M41 tooltip-hides-wrong-time", M41, "A-S9b-chart-observation-identity"),
    ("M42 plaintext-self-claimed-PMID", M42, "A-P9-fulltext-cite-has-body"),
    ("M35 renamed-label-swap", M35, "A-S9b-chart-observation-identity"),
    ("M36 wrong-source-fulltext", M36, "A-P9-fulltext-cite-has-body"),
    ("M37 malformed-chart", M37, "A-S2a-chart-structure"),
    ("M38 paired-claim-no-blanket-exemption", M38, "A-P2-divergence-shows-both"),
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
    ("M28 fulltext-cited-but-not-fetched", M28, "A-P9-fulltext-cite-has-body"),
    ("M23 template-spec-echo", M23, "A-P7-no-template-spec-in-report"),
    ("M24 rule-metastatement", M24, "A-P8-no-rule-metastatement"),
    ("M25 split-convention", M25, "A-S10-sign-convention-consistent"),
    ("M26 generic-title", M26, "A-T1-title-identifies-scope"),
    ("M27 value-misattribution-under-exemption", M27, "A-ATTR-misattribution"),
    ("M29 chart-label-swap", M29, "A-S9b-chart-observation-identity"),
    ("M30 chart-sign-flip", M30, "A-S9b-chart-observation-identity"),
    ("M31 wrong-line-chart", M31, "A-S2-chart-set"),
    ("M32 unsigned-wrong-owner", M32, "A-ATTR-misattribution"),
    ("M33 empty-fulltext-filename", M33, "A-P9-fulltext-cite-has-body"),
    ("M34 unmapped-fulltext-body", M34, "A-P6-cite-link-is-deepest"),
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


def mutate_b_calls(d, mode):
    path = os.path.join(d, "debug-history.json")
    history = json.load(open(path, encoding="utf-8"))
    calls = []
    for message in history["raw_model_messages"]:
        parts = message["parts"]
        matching = [p for p in parts if p.get("part_kind") == "tool-call" and
                    p.get("tool_name") == "pharmcube-query-clinical-result-with-params"]
        if mode == "current":
            for part in matching:
                args = part["args"]
                args = json.loads(args) if isinstance(args, str) else args
                args["esids"] = args.pop("extra_esids")
                part["args"] = args
        else:
            calls.extend(matching)
            message["parts"] = [p for p in parts if p not in matching]
    if mode == "nested":
        history["raw_model_messages"].append({'kind': 'request', 'parts': [
            {'part_kind': 'tool-return', 'tool_name': 'execute', 'content': calls}]})
    elif mode == "foreign":
        target = history['raw_ui_messages'][0]['turn_id']
        json.dump({'turn_id': target}, open(os.path.join(d, 'run.json'), 'w'))
        history['raw_model_messages'].append({'kind': 'response', 'turn_id': 'foreign', 'parts': calls})
    elif mode == "ambiguous":
        history['raw_ui_messages'].append({'role': 'user', 'turn_id': 'foreign', 'parts': []})
        history['raw_model_messages'].append({'kind': 'response', 'parts': calls})
    json.dump(history, open(path, 'w'), ensure_ascii=False)
    return 1


def MB12(d, r, c, v):
    return mutate_b_calls(d, 'foreign')


def MB13(d, r, c, v):
    return mutate_b_calls(d, 'nested')


def MB14(d, r, c, v):
    return mutate_b_calls(d, 'ambiguous')


def NB01(d, r, c, v):
    return mutate_b_calls(d, 'current')


MUTS_B = [
    ("MB12 foreign-turn-calls", MB12, "B-T1-queried-then-refused"),
    ("MB13 nested-counterfeit-calls", MB13, "B-T1-queried-then-refused"),
    ("MB14 ambiguous-target-turn", MB14, "B-T1-queried-then-refused"),
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
# `arm()` proves every item *can* fail.  These prove items do *not* fail on shapes that wrongly
# tripped them once (O19 = mixed sentence, O20 = theme title) or that must stay green by design
# (N28 = the legal L3 full-text shape) — regression guards for exemptions and for attribution, which
# the positive list cannot express.
def N28(d, r, c, v):
    """Synthetic positive control for archive + source identity + full-text link + declaration.

    It borrows R14's archive naming layout only. Its wooden-block body is synthetic;
    the separately archived R14 originals are tested by rescore_revision.py.
    """
    j = archive_fulltext(d, c)
    j["ref_1"]["link"] = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11270764/"
    json.dump(j, open(c, "w"), ensure_ascii=False, indent=1)
    return sub(r, r"原文核对：[^\n]*\n", FT_LINE)


def N29(d, r, c, v):
    """Legal paired divergence split at Chinese semicolon remains green."""
    return sub(r, r"\Z", "\n\n原文 36.0；库内记录 18.5{{ref_1}}。\n")


def N30(d, r, c, v):
    path = os.path.join(v, "endpoint-bar-1.json")
    chart = json.load(open(path))
    chart["option"]["data"].reverse()
    os.unlink(path)
    json.dump(chart, open(os.path.join(v, "endpoint-bar-7.json"), "w"), ensure_ascii=False)
    return 1


NEG_A = [
    ("N30 renamed-reordered-chart", N30, "A-S9b-chart-observation-identity"),
    ("N25 mixed-sentence-not-misattributed", N25, "A-ATTR-misattribution"),
    ("N26 theme-title-accepted", N26, "A-T1-title-identifies-scope"),
    ("N27 trial-id-contrast-sentence", N27, "A-ATTR-misattribution"),
    ("N28 fulltext-claim-with-bytes", N28, "A-P6-cite-link-is-deepest"),
    ("N29 paired-divergence", N29, "A-P2-divergence-shows-both"),
]
NEG_B = [("NB01 current-esids-schema", NB01, "B-T1-queried-then-refused")]
NEG = {"a": NEG_A, "b": NEG_B}


def arm(scenario, src, files, with_artifacts, muts):
    if not os.path.isdir(src):
        print(f"arm {scenario}: FAIL (required baseline run dir not found: {src})")
        return False, ["<baseline-missing>"], [("baseline", "recorded run directory", [])]
    # Score the recorded run copy *as recorded*: arm A's baseline (R17) postdates the
    # original-source contract and already carries the `原文核对：` line, so no seeding is needed
    # (before 2026-09-18 arm A was R8 and one line had to be injected — see the README history).
    bd, _, _, _ = fresh("baseline", src, files, with_artifacts)
    rc0, bad0, base = score(bd, scenario)
    shutil.rmtree(bd, ignore_errors=True)
    if rc0 != 0 or bad0:
        print(f"arm {scenario}: FAIL (baseline not clean: rc={rc0} bad={bad0})")
        return False, ["<baseline-not-clean>"], [("baseline", "clean recorded run", bad0)]
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
        # A negative control must leave the run *fully clean*, not just keep its one item green:
        # `rc != 0` means the control shape broke something else, which is exactly the regression
        # this list exists to catch (asserting `keep_green` alone would print an OK line for it).
        if rc != 0 or bad:
            hit, ok = "BAD", False
            mismatch.append((name, f"a clean run keeping {keep_green} green", bad))
            print(f"[{hit}] {name:22} rc={rc} expected a clean run, flipped={bad}")
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
