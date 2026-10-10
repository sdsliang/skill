#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tell-scan.py — 报告去 AI 味的机械自查（中英双语，零依赖）。

它是**助手**，不是判分器：命中不等于必须改，没命中不等于没问题。
把命中当线索，回到上下文问「这句是空泛、重复、歧义，还是与报告文体不符」。

用法：
    python3 tell-scan.py report.md                  # 自动判语言（按中日韩字符占比）
    python3 tell-scan.py report.md --lang en        # 强制英文规则
    python3 tell-scan.py report.md --json           # JSON 输出（给宿主/断言用）
    python3 tell-scan.py a.md b.md|--json
    python3 tell-scan.py report.md --weak           # 弱命中也让退出码为 3
    python3 tell-scan.py report.md --allow S-INFL-02,W-AIWORD

退出码：0 = 无「强」命中；3 = 有「强」命中（可当闸门）；2 = 用法/文件错误。

规则两档：
    强（strong）— 见到一次就足以改；
    弱（weak）  — 单独出现不是理由，需要同段/同文内有其它命中一起判断。

报告特有的硬规则：交付物里出现过程叙述、工具与流程交代、自我评价、改写仪式、
AI 元信息时，无论强弱都应删除。
"""

import argparse
import json
import re
import sys

sys.dont_write_bytecode = True

# ------------------------------------------------------------------ 中文规则

ZH_RULES = [
    # ---- 过程叙述与自我解释（报告最重的一类） ----
    ("S-PROC-01", "strong",
     r"(我们|本人|本文|本报告)(首先|先|已|共)?\s*(检索|筛选|剔除|抽取|整理|比对|统计|查阅)了?"
     r"|(首先|先|已|共)\s*(检索|筛选|剔除|抽取|整理|比对|统计|查阅)了?"
     r"|(检索|筛选|剔除|抽取|整理|比对|统计|查阅)了",
     "工作过程叙述：报告只给结论与依据，检索/筛选/抽取的过程不写"),
    ("S-PROC-02", "strong", r"(本报告|本文|本分析)基于",
     "过程叙述：说明「基于什么做的」属于工作汇报，不是结论"),
    ("S-PROC-03", "strong", r"(为了(更(好|全面|清晰)|便于|提高)(理解|对比|阅读|呈现|说明)|为提高(可比性|可读性|严谨性))",
     "自述写作动机：口径说明可以留，写作动机删除"),
    ("S-PROC-04", "strong", r"(下面|接下来|以下)(我们)?(将|将先|先|会|来)(介绍|讨论|说明|展开|看|梳理|分析)",
     "预告下文：直接给内容，不预告"),
    ("S-PROC-05", "strong", r"(本节|本部分|本小节)(将|会|主要)(介绍|讨论|说明|展开|梳理)",
     "组织说明：不介绍自己怎么组织内容"),
    ("S-PROC-06", "strong", r"(之所以|综合考虑|权衡(再三|之后|后)|我(们)?(倾向于|更倾向)|(最终|因此)决定(采用|选取|选择|保留))",
     "选择理由/内心戏：推理过程留在思考里，报告给结论"),
    ("S-PROC-07", "strong", r"(结论|判断|结果)(较为|比较|相对)?(可靠|稳健|可信|扎实)|把握(较|比)大|数据(质量|可靠性)(较高|良好)|置信度(为|是|：)",
     "自我评价/置信度：不确定性用数据口径表达，不用自评"),
    ("S-PROC-08", "strong", r"(已(优化|去\s?AI\s?味|改写|润色)|以下是(修改后|改写后|优化后)的?(版本|内容)|如需(调整|进一步|更多)[，,]?(我可以|可|请)|希望(这|对您)(有|能))",
     "改写仪式/客服尾：交付物里不写"),
    ("S-PROC-09", "strong", r"(由\s?AI\s?(生成|撰写)|模型(可能)?(出错|幻觉)|请(人工)?复核|本段由|生成时间[：:])",
     "AI 元信息：报告里不写工具与免责声明"),
    ("S-PROC-10", "weak", r"(现有(材料|信息|数据)(有限|较少|不足)|(信息|资料)(确实)?(较为|比较)?有限|无法给出更多)",
     "免责空转：要么指出缺哪一项、影响什么判断，要么删"),
    # ---- 抬价与空泛 ----
    ("S-INFL-01", "strong", r"(不仅(仅)?是[^，。；]{0,24}(更是|而且是|也是)|不只是[^，。；]{0,24}而是|与其说是[^，。；]{0,20}不如说是)",
     "假对比抬价：两部分都有信息时才保留"),
    ("S-INFL-02", "strong", r"(标志着|里程碑(式|意义)|新(的)?(篇章|纪元|时代|格局)|迎来[^，。；]{0,12}(新|突破|变革|曙光)|为患者带来(新|更多)?(的)?(希望|选择)|填补了?(空白)|开创了?|引领(行业|新|未来))",
     "意义拔高：追加的评价句没有新信息就删"),
    ("S-INFL-03", "strong", r"(业内(普遍)?(认为|公认)|业界(普遍)?(认为|公认)|专家(们)?(一致)?认为|有(观点|人)认为|据(报道|悉)(?![：:]))",
     "借权威：无具体来源的背书，改成有出处的表述或保持模糊程度"),
    ("S-INFL-04", "weak", r"(值得(关注|期待|注意)|表现(亮眼|抢眼|不俗)|可圈可点|令人(瞩目|期待)|颇具(亮点|潜力)|仍需(持续|长期)?关注)",
     "空泛评价：给依据，给不出就删"),
    ("S-INFL-05", "weak", r"(具有(重要|重大|深远)的?(临床|现实|实际|战略|历史)?意义|意义重大|发挥(着)?(重要|关键)作用|起到(了)?(至关)?(重要|关键)作用)",
     "空泛意义：替换为具体贡献"),
    # ---- 结构与排版 ----
    ("S-STRUCT-01", "strong", r"(如下表所示|如上表所示|见下表|下表(展示|列出|给出|汇总)|如图\s?\d?\s?所示|下图(展示|给出|列出)|从上图可以看出|图中(展示|给出|列出)|表格(展示|列出)了)",
     "复述图表：图表能表达的，正文不重复"),
    ("S-STRUCT-02", "strong", r"(综上所述[，,]?\s*(让)?(我们)?(拭目以待|期待)|未来可期|拭目以待|相信在不久的将来|让我们(共同)?期待|期待(更多|后续)(的)?(可能|数据|好消息))",
     "套话收尾：删；有真实下一步就写下一步"),
    ("S-STRUCT-03", "weak", r"(^|\n)\s*(总而言之|总之|总的来说|整体来看|综合来看)[，,、]",
     "总起/收束空转：信息已在正文，重述即多余"),
    ("W-DASH", "weak", r"——[^—\n]{0,30}——",
     "破折号连用制造悬念：承担解释功能的单个破折号可保留"),
    # ---- 措辞 ----
    ("W-AIWORD", "weak", r"(赋能|深度赋能|至关重要的?|无缝(衔接|对接)?|闭环|生态位|全方位|多维度|深层次|全面赋能|蓝图|版图|新范式|护城河)",
     "AI 高频词/包装词：有具体工程含义时不算命中"),
    ("W-HEDGE", "weak", r"(或许可能|可能或许|或许|也许).{0,10}(或许|也许|可能|一定程度上)|(在一定程度上|在某种程度上|从某种意义上)",
     "限定词堆叠：压缩为原文真实的不确定程度"),
    ("W-VAGUE", "weak", r"(有着(密切|紧密|重要)的?(关系|联系|作用)|密切(相关|关联)|占据(重要|核心)地位|在[^，。；]{0,10}方面(表现)?(突出|优异|良好))",
     "模糊关联：原文未写明角色就保持概括，写明了就直接说"),
    ("W-VERBNOUN", "weak", r"进行(了|着)?[一-龥]{2}",
     "「进行＋动词」：换成直接动词，保留时态与次数"),
    ("W-PASSIVE", "weak", r"被[一-龥]{0,8}(认为|报告|发现|指出|认作|视为)",
     "被字句：改主动时保持归因强度（可能/据报 != 导致）"),
    ("W-AS-WITH", "weak", r"随着[^，。；]{0,14}(的)?(发展|到来|推进|变化|演进|延长|增加|累积)",
     "「随着…的发展」式开头：背景没有独立信息时压缩"),
    ("W-4CHAR", "weak", r"(稳步推进|持续发力|不断完善|全面提升|扎实推进|有序推进|持续优化|深度挖掘)",
     "四字排比空转：承载真实程度词时保留"),
    ("W-BOLD-DECOR", "weak", r"(\*\*[^*\n]{1,12}\*\*)[^，。；\n]{0,4}(\*\*[^*\n]{1,12}\*\*)",
     "粗体当装饰：加粗只留给需要定位的关键项"),
]

ZH_DOC_RULES = [
    ("W-DASH-COUNT", "weak", 3, lambda t: len(re.findall(r"——", t)),
     "破折号使用频繁：检查是否有替代分句关系的用法"),
    ("W-BOLD-COUNT", "weak", 8, lambda t: len(re.findall(r"\*\*[^*\n]+\*\*", t)),
     "粗体过多：加粗密度高时读者跳过全部加粗"),
]

# ------------------------------------------------------------------ 英文规则

EN_RULES = [
    # ---- process narration and self-explanation (heaviest report tells) ----
    ("S-PROC-01", "strong", r"\bwe (?:first |then |also |next |subsequently )?(searched|screened|reviewed|queried|compiled|extracted|cross-?checked|reconciled|collected|standardized)\b",
     "Process narration: the report states conclusions and evidence, not the search or extraction steps"),
    ("S-PROC-02", "strong", r"((this|the) report is based on|based on (our|my) (review|search|analysis|survey)|to (improve|ensure) (comparability|readability|consistency)|for completeness, we|values were (extracted|pulled|compiled) from)",
     "Method accounting: how the material was assembled belongs outside the deliverable"),
    ("S-PROC-03", "strong", r"\b(I (tend to|would|lean toward|lean towards|prefer)|after weighing|we decided to|the reason (we|I) (chose|selected|kept)|why (we|I) (chose|selected))\b",
     "Choice rationale or inner debate: keep the conclusion, cut the reasoning about your own choices"),
    ("S-PROC-04", "strong", r"(let'?s (dive|take a look|explore|unpack)|in this (report|section|document) (we|I) (will|'ll)|(this|the following) sections? (will|describes? how the report))",
     "Preview of the document: state the content instead of announcing it"),
    ("S-PROC-05", "strong", r"(the analysis is (reliable|robust|sound)|(our|my) confidence|little confidence|this judgment (may|might) (contain|reflect) bias|on balance, the evidence)",
     "Self-assessment: express uncertainty through data definitions, not self-evaluation"),
    ("S-PROC-06", "strong", r"(let me know if you('d)? (like|need|want)|below is the (revised|updated|rewritten) version|I('ve| have) (optimized|revised|rewritten|polished)|hope this helps)",
     "Rewrite ceremony or sign-off: not part of the deliverable"),
    ("S-PROC-07", "strong", r"(generated by (an )?AI|AI-generated|please (verify|double-check|confirm)|the model may (err|make mistakes)|this content (was|is) (produced|written) using)",
     "AI meta-label: no tooling or disclaimer text inside the report"),
    # ---- inflation and borrowed authority ----
    ("S-INFL-01", "strong", r"(not (just|only|merely) [^.!?]{0,40}\bbut\b|it'?s not about [^.!?]{0,30}it'?s about|more than (just )?a [^.!?]{0,30}, it)",
     "Contrast inflation: keep it only when both halves carry information"),
    ("S-INFL-02", "strong", r"(a testament to|speaks volumes|underscores? the (importance|value|significance)|marks? a (new|major|significant) (era|milestone|step)|paves? the way|a major step forward|nothing short of|game[- ]chang(er|ing)|ushers? in)",
     "Inflated significance: delete the appended evaluation when it adds no fact"),
    ("S-INFL-03", "strong", r"(industry analysts (have|say)|leading experts|experts (say|believe|agree|note)|studies (show|suggest|have shown)|research (shows|suggests)|it is widely (believed|accepted|recognized)|commentators have)",
     "Borrowed authority with no named source: keep the hedging or give a traceable source"),
    ("S-INFL-04", "weak", r"\b(remarkable|impressive|compelling|highly (manageable|promising|effective)|differentiated value|best-in-class|world-class|state-of-the-art|exciting)\b",
     "Empty evaluation: give the evidence or delete"),
    ("S-STRUCT-01", "strong", r"(as shown in (the )?(table|figure|chart)|the (table|figure|chart) (below|above) (shows|lists|summarizes)|see (the )?(table|figure) (below|above|for))",
     "Reciting a table or figure: the chart or table already shows it"),
    ("S-STRUCT-02", "strong", r"(in conclusion,? (the )?(future|outlook|path)|only time will tell|remains to be seen|exciting times ahead|watch this space)",
     "Empty closer: end on evidence or a real next step"),
    ("S-STRUCT-03", "weak", r"(^|\n)\s*(in (summary|conclusion)|overall|all in all|taken together)[,:]",
     "Restating the summary: the information already appeared above"),
    # ---- phrasing ----
    ("W-AIWORD", "weak", r"\b(delve|leverage|leveraging|seamless(ly)?|robust(ly)?|underscore[sd]?|showcase[sd]?|pivotal|landscape|realm|tapestry|holistic|synerg(y|ies|istic)|paradigm shift|cutting[- ]edge|robustness)\b",
     "Overused AI word: a real technical meaning (e.g. robust statistics) is not a hit"),
    ("W-HEDGE", "weak", r"(it is (important|worth) (to note|noting) that|it should be noted that|needless to say|to some extent|in some sense|more or less|arguably)",
     "Hedge padding: state the finding or the caveat, not the throat-clearing"),
    ("W-ING-RIDER", "weak", r",\s+(highlighting|underscoring|showcasing|demonstrating|reflecting|emphasizing|reinforcing|marking|solidifying|paving|enabling|cementing)\b",
     "Shallow -ing rider: the clause repeats or inflates the point"),
    ("W-VAGUE", "weak", r"(has a (strong|close|deep) (relationship|connection|tie)|closely (related|linked|associated)|plays? a (key|critical|vital|important) role|occupies a (central|key) position)",
     "Vague association: name the role, or keep the source's vagueness"),
    ("W-BORED", "weak", r"(in today'?s (fast[- ]paced|rapidly (evolving|changing)|competitive)|in an era of|as the (landscape|market) evolves)",
     "Opening filler about the era: skip to the subject"),
    ("W-NOMINAL", "weak", r"\b(utilization|implementation|optimization|facilitation|methodology of|in terms of)\b",
     "Nominalization or padding: use the verb unless the register requires the noun"),
    ("W-DASH", "weak", r"—[^—\n]{0,30}—",
     "Em dashes used for suspense: a dash carrying an explanation can stay"),
    ("W-BOLD-DECOR", "weak", r"(\*\*[^*\n]{1,14}\*\*)[^,.;\n]{0,4}(\*\*[^*\n]{1,14}\*\*)",
     "Bold as decoration: reserve bold for what the reader must locate"),
    ("W-CHATBOT", "weak", r"(great question|hope (this|that) helps|feel free to (ask|reach out)|happy to (help|clarify)|please don'?t hesitate)",
     "Chatbot residue: keep greetings only in letters and emails"),
    ("W-EMOJI", "weak", r"[\U0001F300-\U0001FAFF\u2600-\u27BF]",
     "Emoji: not in report prose"),
    ("W-CURLY", "weak", r"[\u201C\u201D\u2018\u2019]",
     "Curly quotes: follow the document convention; straight quotes in code and data stay as-is"),
]

EN_DOC_RULES = [
    ("W-DASH-COUNT", "weak", 4, lambda t: len(re.findall(r"—", t)),
     "Em dashes frequent: check whether any replace a real clause relation"),
    ("W-BOLD-COUNT", "weak", 8, lambda t: len(re.findall(r"\*\*[^*\n]+\*\*", t)),
     "Heavy bold: when everything is bold, nothing is"),
]

LANG_RULES = {"zh": (ZH_RULES, ZH_DOC_RULES), "en": (EN_RULES, EN_DOC_RULES)}

# --------------------------------------------------------------- 结构检查

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SENT_SPLIT_RE = re.compile(r"[。！？；\n]|[.!?;]\s")
TITLE_CASE_SKIP = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in",
                   "into", "of", "on", "or", "the", "to", "via", "with", "vs"}


def _norm(text):
    """去标点与空白，用于标题复述检测。"""
    return re.sub(r"[\s，。、：；（）()「」“”\"'·\-—…！？,.!?/|]", "", text)


def _detect_lang(text):
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "zh" if cjk * 6 >= latin else "en"


def _title_case_heading(text):
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", text)]
    if len(words) < 4:
        return False
    major = [w for w in words if w.lower() not in TITLE_CASE_SKIP]
    if not major:
        return False
    capped = sum(1 for w in major if w[0].isupper())
    return capped >= len(major) - 1


def _scan(text, lang):
    rules, doc_rules = LANG_RULES[lang]
    findings = []
    lines = text.splitlines()
    in_code = False
    prose_lines = []
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith("|"):
            # 表格行不参与行级命中：表格是数值与依据的载体，表内短句与加粗属正常排版
            continue
        prose_lines.append(line)
        for rule_id, severity, pattern, hint in rules:
            for m in re.finditer(pattern, line, re.IGNORECASE if lang == "en" else 0):
                findings.append({
                    "rule": rule_id,
                    "severity": severity,
                    "line": idx,
                    "match": m.group(0).strip(),
                    "hint": hint,
                })
        hm = HEADING_RE.match(line)
        if hm:
            head = _norm(hm.group(2))
            if lang == "en" and _title_case_heading(hm.group(2)):
                findings.append({
                    "rule": "W-TITLECASE",
                    "severity": "weak",
                    "line": idx,
                    "match": hm.group(2)[:40],
                    "hint": "Title Case heading: sentence case is the default for report headings",
                })
            # 标题后紧跟复述标题的句子
            if len(head) >= 3:
                for probe in lines[idx:idx + 3]:
                    probe = probe.strip()
                    if not probe or HEADING_RE.match(probe) or probe.startswith("|"):
                        continue
                    first = _norm(SENT_SPLIT_RE.split(probe)[0])
                    if first and (first.startswith(head) or head in first):
                        findings.append({
                            "rule": "S-STRUCT-04",
                            "severity": "strong",
                            "line": idx + 1,
                            "match": probe[:40],
                            "hint": "The heading is restated: delete the sentence if it adds nothing"
                            if lang == "en" else "标题后复述标题：这句没有独立信息就删",
                        })
                    break
    prose = "\n".join(prose_lines)
    for rule_id, severity, threshold, counter, hint in doc_rules:
        n = counter(prose)
        if n >= threshold:
            findings.append({
                "rule": rule_id,
                "severity": severity,
                "line": 0,
                "match": f"{n} 处" if lang == "zh" else f"{n} occurrences",
                "hint": hint,
            })
    findings.sort(key=lambda f: (f["line"] or 0, f["rule"]))
    return findings


def evaluate(text, lang=None, allow=()):
    if lang in (None, "auto"):
        lang = _detect_lang(text)
    if lang not in LANG_RULES:
        raise ValueError(f"unknown lang: {lang}")
    findings = [f for f in _scan(text, lang) if f["rule"] not in allow]
    strong = sum(1 for f in findings if f["severity"] == "strong")
    return {
        "lang": lang,
        "strong": strong,
        "weak": len(findings) - strong,
        "findings": findings,
    }


def scan_file(path, lang=None, allow=()):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    rep = evaluate(text, lang, allow)
    rep["file"] = path
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description="报告去 AI 味机械自查（助手，非判分器，中英双语）")
    ap.add_argument("files", nargs="+", help="待检查的 Markdown/文本文件")
    ap.add_argument("--lang", choices=["auto", "zh", "en"], default="auto", help="规则语言，默认按内容自动判断")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--weak", action="store_true", help="弱命中也让退出码为 3")
    ap.add_argument("--allow", default="", help="逗号分隔的规则 ID 白名单")
    args = ap.parse_args(argv)

    allow = {r.strip() for r in args.allow.split(",") if r.strip()}
    reports, failed = [], False
    for path in args.files:
        try:
            rep = scan_file(path, args.lang, allow)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        reports.append(rep)
        if rep["strong"] or (args.weak and rep["weak"]):
            failed = True

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        for rep in reports:
            print(f"== {rep['file']}  [{rep['lang']}]  强 {rep['strong']} / 弱 {rep['weak']}")
            for f in rep["findings"]:
                where = f"L{f['line']}" if f["line"] else ("全文" if rep["lang"] == "zh" else "doc")
                tag = "强" if f["severity"] == "strong" else "弱"
                print(f"  {where:>8} [{tag}] {f['rule']}  «{f['match']}»")
                print(f"{'':>12}→ {f['hint']}")
            if not rep["findings"]:
                print("  无命中" if rep["lang"] == "zh" else "  no hits")
        total = sum(r["strong"] for r in reports)
        print(f"\n合计强命中 {total} 条 / total strong hits {total}."
              " 命中是线索不是判决：回到上下文判断是否真的空泛、重复或与文体不符。")
    return 3 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
