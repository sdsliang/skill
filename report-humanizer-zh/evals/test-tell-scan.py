#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report-humanizer-zh 的机械闸门。

直接运行（不要用 unittest discover，本文件含连字符文件名）：

    python3 -B evals/test-tell-scan.py

覆盖四件事：
  1. 扫描器本身的行为（语言判定、代码块跳过、--allow、退出码、JSON 形状）；
  2. 三份 fixture 的命中形态（AI 味稿必须被抓、干净稿与保留稿必须不误报）；
  3. 改写不丢事实（数值与事实锚点逐字保留，且不得凭空造数）；
  4. 反「空产物蒙分」：改写稿必须是有内容的正文，不能靠清空或复制原文过关。
"""

import difflib
import importlib.util
import json
import re
import subprocess
import subprocess as SP
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skill" / "report-humanizer-zh"
SCANNER = SKILL / "scripts" / "tell-scan.py"
FIX = ROOT / "evals" / "fixtures"
SIBLING_SCANNER = ROOT.parent / "report-humanizer-en" / "skill" / "report-humanizer-en" / "scripts" / "tell-scan.py"
LANG = "zh"

AI = "ai-flavored.zh.md"
HUMAN = "humanized.zh.md"
KEEP = "keep.zh.md"
WEAK = "weak-only.zh.md"

# AI 味稿里必须被「强」规则抓到的条目；少一条就说明规则表被削弱了。
EXPECTED_STRONG_IN_AI = {
    "S-PROC-01", "S-PROC-02", "S-PROC-05", "S-PROC-06", "S-PROC-07",
    "S-INFL-02", "S-INFL-03", "S-STRUCT-01", "S-STRUCT-02", "S-STRUCT-04",
}
EXPECTED_WEAK_IN_AI = {"S-INFL-04"}
EXPECTED_WEAK_IN_KEEP = {"W-AS-WITH", "W-PASSIVE", "W-VERBNOUN"}

failures = []
checks = 0


def check(name, fn):
    global checks
    checks += 1
    try:
        fn()
    except AssertionError as exc:
        failures.append(f"{name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{name}: unexpected {type(exc).__name__}: {exc}")


def load_scanner():
    spec = importlib.util.spec_from_file_location("tell_scan_under_test", SCANNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCAN = load_scanner()


def text(name):
    return (FIX / name).read_text(encoding="utf-8")


def report(name, lang=None, allow=()):
    return SCAN.evaluate(text(name), lang or LANG, allow)


def rules(rep, severity=None):
    return {f["rule"] for f in rep["findings"] if severity is None or f["severity"] == severity}


def run_cli(*args):
    proc = subprocess.run(
        [sys.executable, "-B", str(SCANNER), *[str(a) for a in args]],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


# ---------------------------------------------------------------- 扫描器行为

def t_lang_detect():
    assert SCAN._detect_lang(text(AI)) == "zh", "中文稿却被判成英文"
    assert SCAN._detect_lang(text(HUMAN)) == "zh"
    assert SCAN._detect_lang("Pembrolizumab improved PFS versus chemotherapy.") == "en"


def t_code_fence_skipped():
    body = "```\n我们首先检索了数据库，综上所述，期待未来。\n```\n"
    assert SCAN.evaluate(body, "zh")["strong"] == 0, "代码块里的文字被当成正文命中"


def t_allow_suppresses():
    full = report(AI)["strong"]
    filtered = SCAN.evaluate(text(AI), "zh", {"S-PROC-01", "S-PROC-02", "S-INFL-02", "S-INFL-03",
                                             "S-STRUCT-01", "S-STRUCT-02", "S-STRUCT-04", "S-PROC-05",
                                             "S-PROC-06", "S-PROC-07"})["strong"]
    assert full >= 10, f"AI 味稿强命中只有 {full} 条"
    assert filtered == 0, f"--allow 未生效，仍剩 {filtered} 条强命中"


def t_json_shape():
    code, out, _ = run_cli(FIX / AI, "--json")
    assert code == 3, f"AI 味稿退出码应为 3，实际 {code}"
    payload = json.loads(out)
    assert isinstance(payload, list) and len(payload) == 1, "JSON 顶层应为单元素数组"
    rep = payload[0]
    for key in ("lang", "strong", "weak", "findings", "file"):
        assert key in rep, f"JSON 缺字段 {key}"
    for f in rep["findings"]:
        for key in ("rule", "severity", "line", "match", "hint"):
            assert key in f, f"findings 缺字段 {key}"
        assert f["severity"] in ("strong", "weak")


def t_exit_codes():
    code, _, _ = run_cli(FIX / HUMAN)
    assert code == 0, f"干净稿退出码应为 0，实际 {code}"
    code, _, _ = run_cli(FIX / WEAK)
    assert code == 0, f"仅弱命中的稿件严格模式应放过，实际 {code}"
    code, _, _ = run_cli(FIX / WEAK, "--weak")
    assert code == 3, f"--weak 下仅弱命中应返回 3，实际 {code}"
    code, _, err = run_cli(FIX / "does-not-exist.md")
    assert code == 2, f"文件不存在应返回 2，实际 {code}"
    assert "error" in err.lower() or "no such file" in err.lower()


def t_heading_restatement():
    body = "## 三、试验背景\n\n三、试验背景部分说明如下内容。\n"
    assert "S-STRUCT-04" in rules(SCAN.evaluate(body, "zh"), "strong"), "标题复述未被抓到"


def t_zh_not_titlecase_rule():
    assert "W-TITLECASE" not in rules(report(AI)), "中文规则表混入了英文 Title Case 检查"


def t_no_bytecode_residue():
    left = list(SKILL.rglob("__pycache__")) + list(SKILL.rglob("*.pyc"))
    assert not left, f"扫描器留下字节码产物：{left}"


def t_bundle_parity():
    if not SIBLING_SCANNER.exists():
        return
    a = SCANNER.read_bytes()
    b = SIBLING_SCANNER.read_bytes()
    assert a == b, "两个 bundle 里的 tell-scan.py 不一致，必须同步复制"


# ------------------------------------------------------------- fixture 形态

def t_ai_flavored_is_caught():
    rep = report(AI)
    assert rep["strong"] >= 10, f"AI 味稿只抓到 {rep['strong']} 条强命中"
    missing = EXPECTED_STRONG_IN_AI - rules(rep, "strong")
    assert not missing, f"AI 味稿漏抓：{sorted(missing)}"
    missing = EXPECTED_WEAK_IN_AI - rules(rep, "weak")
    assert not missing, f"AI 味稿漏抓弱命中：{sorted(missing)}"


def t_humanized_is_clean():
    rep = report(HUMAN)
    assert rep["strong"] == 0, f"改写稿仍被判为强命中：{sorted(rules(rep, 'strong'))}"
    assert rep["weak"] == 0, f"改写稿仍被判为弱命中：{sorted(rules(rep, 'weak'))}"


def t_keep_fixture_not_flagged():
    rep = report(KEEP)
    assert rep["strong"] == 0, f"合法稿件被误判：{sorted(rules(rep, 'strong'))}"
    missing = EXPECTED_WEAK_IN_KEEP - rules(rep, "weak")
    assert not missing, f"该留的弱命中丢了：{sorted(missing)}"


# --------------------------------------------------------------- 事实不丢

def _numbers(s):
    return set(NUM_RE.findall(s))


def t_rewrite_invents_no_numbers():
    src, tgt = text(AI), text(HUMAN)
    invented = _numbers(tgt) - _numbers(src)
    assert not invented, f"改写稿出现原文没有的数值：{sorted(invented)}"


def t_required_tokens_survive():
    facts = json.loads((FIX / "facts.zh.json").read_text(encoding="utf-8"))
    src, tgt = text(AI), text(HUMAN)
    for tok in facts["required_tokens"]:
        assert tok in src, f"原始稿缺锚点 {tok!r}（fixture 被改坏）"
        assert tok in tgt, f"改写丢事实：{tok!r}"


def t_pair_files_match_facts():
    facts = json.loads((FIX / "facts.zh.json").read_text(encoding="utf-8"))
    for name in facts["pair"]:
        assert (FIX / name).exists(), f"facts 声明的配对文件不存在：{name}"


# ------------------------------------------------------- 反「空产物蒙分」

def t_humanized_is_real_prose():
    body = text(HUMAN)
    assert len(body) >= 200, f"改写稿过短（{len(body)} 字符），疑似空产物"
    sentences = [s for s in re.split(r"[。；\n]", body) if len(s.strip()) > 6]
    assert len(sentences) >= 3, "改写稿句子过少，疑似空产物"
    assert "KRYSTAL-12" in body and "9.4" in body, "改写稿缺关键事实，不能算交付"


def t_humanized_is_not_a_copy():
    src, tgt = text(AI), text(HUMAN)
    ratio = difflib.SequenceMatcher(None, src, tgt).ratio()
    assert ratio < 0.9, f"改写稿几乎是原文复制（相似度 {ratio:.2f}）"


def t_ai_flavored_is_longer():
    assert len(text(AI)) > len(text(HUMAN)), "AI 味稿不比重写稿长，fixture 失去对照意义"


# ------------------------------------- references/examples.md 自带材料检查

def _present(token, blob):
    """锚点允许句首大写的差异，其余必须逐字相同。"""
    return token in blob or (token[:1].upper() + token[1:]) in blob

def _example_sections():
    lines = (SKILL / "references" / "examples.md").read_text(encoding="utf-8").splitlines()
    sections, cur, mode, keep_line = [], None, None, None
    for line in lines:
        if line.startswith("## ") and ("例" in line or line.startswith("## Example")):
            if cur:
                sections.append(cur)
            cur = {"title": line.strip("# ").strip(), "before": [], "after": [], "keep": None}
            mode = None
            continue
        if cur is None:
            continue
        if "改写前" in line or "**BEFORE**" in line:
            mode = "before"; continue
        if "改写后" in line or "**AFTER**" in line:
            mode = "after"; continue
        if "必须逐字保留" in line or "Must survive verbatim" in line:
            cur["keep"] = line; mode = None; continue
        if line.startswith("> ") and mode in ("before", "after"):
            cur[mode].append(line[2:])
    if cur:
        sections.append(cur)
    return [s for s in sections if s["before"] and s["after"]]


def t_examples_are_self_contained():
    sections = _example_sections()
    assert len(sections) >= 3, f"对照示例解析到 {len(sections)} 例，至少应有 3 例"
    for sec in sections:
        before, after = "\n".join(sec["before"]), "\n".join(sec["after"])
        hidden = _numbers(after) - _numbers(before)
        assert not hidden, f"{sec['title']}：改写后出现改写前没有的数值 {sorted(hidden)}"


def t_examples_keep_tokens_present():
    for sec in _example_sections():
        before, after = "\n".join(sec["before"]), "\n".join(sec["after"])
        assert sec["keep"], f"{sec['title']}：缺少「必须逐字保留」行"
        tokens = [t for t in re.findall(r"`([^`]+)`", sec["keep"]) if not re.search(r"[\u4e00-\u9fff]", t)]
        assert tokens, f"{sec['title']}：保留清单里没有可机械校验的锚点"
        for tok in tokens:
            assert _present(tok, before), f"{sec['title']}：保留锚点 {tok!r} 不在改写前"
            assert _present(tok, after), f"{sec['title']}：改写丢了保留锚点 {tok!r}"




# ------------------------------------------- 误报回归（真实报告暴露的两处）

def t_bare_noun_is_not_process():
    """裸「统计/筛选」是报告常用名词，不能单命中；带主语或「了」才是过程叙述。"""
    assert not rules(SCAN.evaluate("统计显著性以 p<0.05 为准，筛选人群为全分析集。", "zh"), "strong")
    assert "S-PROC-01" in rules(SCAN.evaluate("我们检索了 27 条披露。", "zh"), "strong")
    assert "S-PROC-01" in rules(SCAN.evaluate("共筛选了 27 条记录。", "zh"), "strong")
    assert "S-PROC-01" in rules(SCAN.evaluate("本文统计各臂不良事件。", "zh"), "strong")


def t_table_rows_are_not_scanned():
    """表格行不参与行级命中，也不进文档级计数（表内加粗与短句是正常排版）。"""
    body = (
        "| 维度 | 试验 A | 试验 B |\n"
        "| --- | --- | --- |\n"
        "| 统计口径 | **全分析集** | **安全性集** |\n"
        "| 说明 | **唯一来源** | **中位随访** |\n"
    )
    rep = SCAN.evaluate(body, "zh")
    assert rep["strong"] == 0 and rep["weak"] == 0, f"表格行被当成正文命中：{rep['findings']}"


def t_mixed_notation_is_flagged():
    """同一文档内小数点/百分号两种写法并存是命中（弱），这是来源混用带进来的痕迹。"""
    mixed = "中位 PFS 11.1 个月，对照组 6·9 个月，≥3 级出血 2% 对 1 %。"
    rep = SCAN.evaluate(mixed, "zh")
    assert rep["strong"] == 0, f"排版混用不应算强命中：{rep['findings']}"
    assert "W-FMT-MIXED" in rules(rep), f"混用未被抓到：{rep['findings']}"


def t_uniform_notation_is_clean():
    """写法统一时不报——包括统一成中圆点、以及只有一种形态的单一数值。"""
    for ok in ("中位 PFS 11.1 个月，对照组 6.9 个月，≥3 级出血 2% 对 1%。",
               "中位 PFS 11.1 个月，≥3 级出血 2%，HR 0.60（95% CI 0.46–0.78）。",
               "中位随访 10·3 个月与 21·4 个月，事件数 204 例。"):
        rep = SCAN.evaluate(ok, "zh")
        assert "W-FMT-MIXED" not in rules(rep), f"统一写法误报：{ok} -> {rep['findings']}"




# ---------------------------------------------------------- 打包闸门

def t_dist_zip_is_current():
    """dist 里的上传附件必须等于当前工作区重打的包（发布口径以包为准）。"""
    out = SP.run([sys.executable, "-B", str(ROOT / "tools" / "pack-dist.py"), "--check"],
                 capture_output=True, text=True)
    assert out.returncode == 0, (out.stdout + out.stderr).strip()


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("t_") and callable(f)]
    for name, fn in tests:
        check(name, fn)
    print(f"report-humanizer-zh machine gate: {checks - len(failures)}/{checks} OK")
    for f in failures:
        print(f"  FAIL {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
