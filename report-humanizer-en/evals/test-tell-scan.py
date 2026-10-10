#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine gate for report-humanizer-en.

Run directly (do not use unittest discover; this filename contains a hyphen):

    python3 -B evals/test-tell-scan.py

Four things are covered:
  1. scanner behaviour (language detection, fenced blocks, --allow, exit codes, JSON shape);
  2. fixture outcome shape (the AI-flavoured draft must be caught, the clean and the keep files must not be);
  3. no fact loss (numbers and fact anchors preserved byte for byte, no invented numbers);
  4. anti empty-artifact: the rewrite must be real prose, not an emptied or copied file.
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
SKILL = ROOT / "skill" / "report-humanizer-en"
SCANNER = SKILL / "scripts" / "tell-scan.py"
FIX = ROOT / "evals" / "fixtures"
SIBLING_SCANNER = ROOT.parent / "report-humanizer-zh" / "skill" / "report-humanizer-zh" / "scripts" / "tell-scan.py"
LANG = "en"

AI = "ai-flavored.en.md"
HUMAN = "humanized.en.md"
KEEP = "keep.en.md"
WEAK = "weak-only.en.md"

# Entries the AI-flavoured draft must trigger as [strong]; a missing one means the rule table was weakened.
EXPECTED_STRONG_IN_AI = {
    "S-PROC-01", "S-PROC-02", "S-PROC-03", "S-PROC-04", "S-PROC-05",
    "S-PROC-06", "S-PROC-07", "S-INFL-01", "S-INFL-02", "S-INFL-03",
    "S-STRUCT-01", "S-STRUCT-02",
}
EXPECTED_WEAK_IN_AI = {"S-INFL-04", "W-AIWORD", "W-HEDGE", "W-ING-RIDER", "W-BOLD-DECOR", "W-CURLY", "W-TITLECASE"}
EXPECTED_WEAK_IN_KEEP = {"W-ING-RIDER", "W-NOMINAL"}

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


# ------------------------------------------------------------- scanner behaviour

def t_lang_detect():
    assert SCAN._detect_lang(text(AI)) == "en", "an English draft was detected as Chinese"
    assert SCAN._detect_lang(text(HUMAN)) == "en"
    assert SCAN._detect_lang("帕博利珠单抗组中位 PFS 为 9.4 个月。") == "zh"


def t_code_fence_skipped():
    body = "```\nWe searched 3 registries, and in conclusion the future looks bright.\n```\n"
    assert SCAN.evaluate(body, "en")["strong"] == 0, "text inside a fenced block was scanned as prose"


def t_allow_suppresses():
    full = report(AI)["strong"]
    filtered = SCAN.evaluate(text(AI), "zh", {"S-PROC-01", "S-PROC-02", "S-INFL-02", "S-INFL-03",
                                             "S-STRUCT-01", "S-STRUCT-02", "S-STRUCT-04", "S-PROC-05",
                                             "S-PROC-06", "S-PROC-07"})["strong"]
    assert full >= 10, f"the AI draft only scored {full} strong hits"
    assert filtered == 0, f"--allow did not take effect, {filtered} strong hits remain"


def t_json_shape():
    code, out, _ = run_cli(FIX / AI, "--json")
    assert code == 3, f"the AI draft must exit 3, got {code}"
    payload = json.loads(out)
    assert isinstance(payload, list) and len(payload) == 1, "the JSON top level must be a single-element array"
    rep = payload[0]
    for key in ("lang", "strong", "weak", "findings", "file"):
        assert key in rep, f"the JSON payload is missing {key}"
    for f in rep["findings"]:
        for key in ("rule", "severity", "line", "match", "hint"):
            assert key in f, f"a finding is missing {key}"
        assert f["severity"] in ("strong", "weak")


def t_exit_codes():
    code, _, _ = run_cli(FIX / HUMAN)
    assert code == 0, f"the clean draft must exit 0, got {code}"
    code, _, _ = run_cli(FIX / WEAK)
    assert code == 0, f"a weak-only draft must pass the strict gate, got {code}"
    code, _, _ = run_cli(FIX / WEAK, "--weak")
    assert code == 3, f"with --weak a weak-only draft must return 3, got {code}"
    code, _, err = run_cli(FIX / "does-not-exist.md")
    assert code == 2, f"a missing file must return 2, got {code}"
    assert "error" in err.lower() or "no such file" in err.lower()


def t_heading_restatement():
    body = "## Trial background\n\nTrial background is described below.\n"
    assert "S-STRUCT-04" in rules(SCAN.evaluate(body, "en"), "strong"), "the heading restatement was not caught"


def t_en_has_titlecase_rule():
    assert "W-TITLECASE" in rules(report(AI), "weak"), "the English rule table is missing the Title Case heading check"


def t_no_bytecode_residue():
    left = list(SKILL.rglob("__pycache__")) + list(SKILL.rglob("*.pyc"))
    assert not left, f"the scanner left bytecode behind: {left}"


def t_bundle_parity():
    if not SIBLING_SCANNER.exists():
        return
    a = SCANNER.read_bytes()
    b = SIBLING_SCANNER.read_bytes()
    assert a == b, "the two bundles ship different tell-scan.py files; they must be copied in sync"


# --------------------------------------------------------------- fixture shape

def t_ai_flavored_is_caught():
    rep = report(AI)
    assert rep["strong"] >= 10, f"the AI draft only scored {rep['strong']} strong hits"
    missing = EXPECTED_STRONG_IN_AI - rules(rep, "strong")
    assert not missing, f"the AI draft did not trigger: {sorted(missing)}"
    missing = EXPECTED_WEAK_IN_AI - rules(rep, "weak")
    assert not missing, f"the AI draft did not trigger as weak: {sorted(missing)}"


def t_humanized_is_clean():
    rep = report(HUMAN)
    assert rep["strong"] == 0, f"the rewrite is still flagged as strong: {sorted(rules(rep, 'strong'))}"
    assert rep["weak"] == 0, f"the rewrite is still flagged as weak: {sorted(rules(rep, 'weak'))}"


def t_keep_fixture_not_flagged():
    rep = report(KEEP)
    assert rep["strong"] == 0, f"the keep fixture was flagged as strong: {sorted(rules(rep, 'strong'))}"
    missing = EXPECTED_WEAK_IN_KEEP - rules(rep, "weak")
    assert not missing, f"expected weak hits are missing: {sorted(missing)}"


# ------------------------------------------------------------- no fact loss

def _numbers(s):
    return set(NUM_RE.findall(s))


def t_rewrite_invents_no_numbers():
    src, tgt = text(AI), text(HUMAN)
    invented = _numbers(tgt) - _numbers(src)
    assert not invented, f"the rewrite invents numbers absent from the source: {sorted(invented)}"


def t_required_tokens_survive():
    facts = json.loads((FIX / "facts.en.json").read_text(encoding="utf-8"))
    src, tgt = text(AI), text(HUMAN)
    for tok in facts["required_tokens"]:
        assert tok in src, f"the source fixture lost anchor {tok!r}"
        assert tok in tgt, f"the rewrite dropped the fact {tok!r}"


def t_pair_files_match_facts():
    facts = json.loads((FIX / "facts.en.json").read_text(encoding="utf-8"))
    for name in facts["pair"]:
        assert (FIX / name).exists(), f"a file declared by facts does not exist: {name}"


# ------------------------------------------- anti empty-artifact scoring

def t_humanized_is_real_prose():
    body = text(HUMAN)
    assert len(body) >= 200, f"the rewrite is too short ({len(body)} chars), likely an empty artifact"
    sentences = [s for s in re.split(r"[.;\n]", body) if len(s.strip()) > 6]
    assert len(sentences) >= 3, "the rewrite has too few sentences, likely an empty artifact"
    assert "KRYSTAL-12" in body and "9.4" in body, "the rewrite lacks key facts and does not count as a delivery"


def t_humanized_is_not_a_copy():
    src, tgt = text(AI), text(HUMAN)
    ratio = difflib.SequenceMatcher(None, src, tgt).ratio()
    assert ratio < 0.9, f"the rewrite is almost a copy of the source (similarity {ratio:.2f})"


def t_ai_flavored_is_longer():
    assert len(text(AI)) > len(text(HUMAN)), "the AI draft is not longer than the rewrite, so the fixture pair is pointless"


# --------------------------------- references/examples.md self-containment

def _present(token, blob):
    """Anchor matching tolerates sentence-initial capitalisation only."""
    return token in blob or (token[:1].upper() + token[1:]) in blob

def _example_sections():
    lines = (SKILL / "references" / "examples.md").read_text(encoding="utf-8").splitlines()
    sections, cur, mode = [], None, None
    for line in lines:
        if line.startswith("## Example"):
            if cur:
                sections.append(cur)
            cur = {"title": line.strip("# ").strip(), "before": [], "after": [], "keep": None}
            mode = None
            continue
        if cur is None:
            continue
        if "**BEFORE**" in line:
            mode = "before"; continue
        if "**AFTER**" in line:
            mode = "after"; continue
        if "Must survive verbatim" in line:
            cur["keep"] = line; mode = None; continue
        if line.startswith("> ") and mode in ("before", "after"):
            cur[mode].append(line[2:])
    if cur:
        sections.append(cur)
    return [s for s in sections if s["before"] and s["after"]]


def t_examples_are_self_contained():
    sections = _example_sections()
    assert len(sections) >= 3, f"only {len(sections)} examples parsed, at least 3 expected"
    for sec in sections:
        before, after = "\n".join(sec["before"]), "\n".join(sec["after"])
        hidden = _numbers(after) - _numbers(before)
        assert not hidden, f"{sec['title']}: the AFTER paragraph has numbers absent from BEFORE: {sorted(hidden)}"


def t_examples_keep_tokens_present():
    for sec in _example_sections():
        before, after = "\n".join(sec["before"]), "\n".join(sec["after"])
        assert sec["keep"], f"{sec['title']}: missing the 'must survive verbatim' line"
        tokens = re.findall(r"`([^`]+)`", sec["keep"])
        assert tokens, f"{sec['title']}: no mechanically checkable anchor in the keep list"
        for tok in tokens:
            assert _present(tok, before), f"{sec['title']}: anchor {tok!r} is absent from BEFORE"
            assert _present(tok, after), f"{sec['title']}: the rewrite dropped the anchor {tok!r}"




# ---------------------------- false-positive regressions (from a real report)

def t_table_rows_are_not_scanned():
    """Table rows are neither scanned line by line nor counted at document level."""
    body = (
        "| Dimension | Trial A | Trial B |\n"
        "| --- | --- | --- |\n"
        "| Analysis set | **Full analysis set** | **Safety set** |\n"
        "| Note | **Single source** | **Median follow-up** |\n"
    )
    rep = SCAN.evaluate(body, "en")
    assert rep["strong"] == 0 and rep["weak"] == 0, f"table rows were scanned as prose: {rep['findings']}"


def t_dictionary_lookup_verbs_need_an_actor():
    """Method verbs only count as process narration with an actor or a completed form."""
    assert rules(SCAN.evaluate("We searched 27 disclosures and extracted endpoints.", "en"), "strong")
    assert SCAN.evaluate("The search covered 27 disclosures; endpoints came from 18 of them.", "en")["strong"] == 0




# ------------------------------------------------------------ packaging gate

def t_dist_zip_is_current():
    """The upload attachment in dist/ must equal a fresh build of the worktree."""
    out = SP.run([sys.executable, "-B", str(ROOT / "tools" / "pack-dist.py"), "--check"],
                 capture_output=True, text=True)
    assert out.returncode == 0, (out.stdout + out.stderr).strip()


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("t_") and callable(f)]
    for name, fn in tests:
        check(name, fn)
    print(f"report-humanizer-en machine gate: {checks - len(failures)}/{checks} OK")
    for f in failures:
        print(f"  FAIL {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
