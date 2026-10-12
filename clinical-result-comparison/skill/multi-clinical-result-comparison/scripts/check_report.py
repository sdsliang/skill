#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical pre-delivery self-check for the two deliverables and the chart products.

Run this after the render gate and before `present_artifact`.  It only checks things a machine
can settle — text that must not appear, marker/citation parity, chart envelope shape, fixed
paths — so it never replaces clinical review; it stops the run from shipping an unresolved
`[[fact:…]]` token, a chart JSON that is a bare `option` object, a citation key no marker uses,
or a `::visualization` reference pointing at nothing.

    python3 /workspace/skills/multi-clinical-result-comparison/scripts/check_report.py
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/check_report.py --report /workspace/output/report.md \
        --citations /workspace/output/citations.json --charts-dir /workspace/visualizations -v

Fixed defaults are the delivery contract paths, so a bare run is the normal case.  Exit codes:
0 all checks pass; 3 at least one finding (fix before delivering); 4 warnings only; 2 usage/IO.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

APPENDIX_TITLE = "## 附录：证据对齐矩阵"
MARKER_RE = re.compile(r"\{\{(ref_[1-9]\d*)\}\}")
ANY_BRACE_RE = re.compile(r"\{\{[^{}]*\}\}")
TOKEN_RE = re.compile(r"\[\[\s*(?:fact|result)\s*:")
ENTITY_RE = re.compile(r"\(entity:[^)]*\)|entity:\s*[a-z]+", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VIS_REF_RE = re.compile(r"::visualization\[[^\]]*\]\{([^}]*)\}")
PATH_ATTR_RE = re.compile(r'path\s*=\s*"([^"]+)"')
FENCE_RE = re.compile(r"```")
CHART_TYPE_BY_PREFIX = (("evidence-timeline", "timeline"), ("endpoint-bar-", "bar"), ("endpoint-line-", "line"))
CITATION_FIELDS = ("title", "link", "paper_release_time_str")
LEAK_PATTERNS = (
    ("source_file", r"source_file"),
    ("tool_results path", r"tool_results"),
    ("internal esid field", r"\besid\b"),
    ("work/ scratch path", r"/workspace/work/"),
    ("ledger file name", r"\b(?:ledger|facts)\.json\b"),
)
# The run-logistics vocabulary is a product rule owned by the evaluator (A-P10); here it is only a
# warning, so a stray word never blocks an otherwise sound delivery mid-run.
RUN_LOGISTICS = (r"本次运行", r"本运行环境", r"运行环境", r"本轮运行", r"无外网", r"网络受限",
                 r"抓取(?:失败|受限|超时)")
# The report states clinical findings; it never narrates its own method, classification or
# bookkeeping.  Labels and chart-decidability wording are the authoring layer's own vocabulary
# (`分析模式`/`选择依据`/`可比性结论`/`对齐等级`/`可绘图`) and they leak the reasoning process into a
# deliverable the reader only wants findings from.  Two slots stay: the fixed non-head-to-head
# caveat and the `原文核对：` coverage line — both written as material statements.
META_LABEL_RE = re.compile(
    r"(?:\*\*|^\s*[-*]\s*)(?:分析模式|分析口径|选择依据|可比性结论|对齐等级|不绘图原因|"
    r"有限并列原因|处理流程|撰写方式|报告结构|检索策略|纳入标准)\s*[:：*]",
    re.MULTILINE)
META_COLUMN_RE = re.compile(
    r"^\s*\|[^\n|]*(?:\|[^\n|]*)*\|\s*(?:对齐等级|分析模式|选择依据|可比性结论|"
    r"不绘图原因|有限并列原因)\s*\|", re.MULTILINE)
METHOD_NARRATION_RE = re.compile(
    r"可绘图|不具备绘图条件|只能有限并列|未生成图表|不生成图表|不生成优效排序|"
    r"本次选择|本次纳入|纳入本次|我们选择|我们纳入|我们取用|本轮|"
    r"(?:部分|直接|仅背景|未)对齐|为便于阅读|便于读者理解")
SELF_AUDIT_RE = re.compile(
    r"无未复核记录|无遗漏记录|无缺失项|无未取回记录|全部通过(?:自检|校验)|"
    r"未发现(?:不一致|问题|异常)|不存在未复核")
INTERNAL_VOCAB_RE = re.compile(r"\bsrc\s*=\s*\d|\bpayload\b|\bJSONL\b|\bMCP\b|沙箱|工作区")
SELF_REFERENCE_RE = re.compile(r"本报告|本文档|本工具|本流程|本管线|本交付物|本次(?!披露)")
SHINGLE = 8
CHART_NUMBER_RE = re.compile(r"[-+−]?\d+(?:\.\d+)?")
CHART_UNIT_SUFFIX_RE = re.compile(r"\s*(?:mg/?|周|天|月|年|例|名|岁|nmol/L|mmol/L|每)(?![A-Za-z])", re.IGNORECASE)
# Chart prose must not repeat plotted values; dose/time/count units are allowed context.
# 表格重复只在图表所属正文 section 生效，附录是事实账本，不参与判断。

# A registry id (or any code-like token) is a proper name: two rows that both name the same trial
# are supposed to look alike, so ids are masked out before shingles are compared.
REGISTRY_RX = re.compile(r"[A-Za-z]{2,}[-\s]?\d{4,}[A-Za-z-]*")
MASK = "\x00"


def _atomic_note(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _shingles(text: str) -> set[str]:
    compact = REGISTRY_RX.sub(lambda match: MASK * len(match.group()), _atomic_note(text))
    return {compact[i:i + SHINGLE] for i in range(max(0, len(compact) - SHINGLE + 1))
            if MASK not in compact[i:i + SHINGLE]}


def _chart_number_tokens(text: str) -> list[tuple[str, float, int]]:
    tokens: list[tuple[str, float, int]] = []
    for match in CHART_NUMBER_RE.finditer(text.replace("−", "-")):
        try:
            tokens.append((match.group(), float(match.group()), match.end()))
        except ValueError:
            continue
    return tokens


def _chart_text_findings(name: str, option: dict) -> list[str]:
    """Return hard findings for plotted values repeated in chart prose."""
    if str(option.get("type") or "").lower() == "timeline":
        return []
    values = [row.get("value") for row in option.get("data", [])
              if isinstance(row, dict) and isinstance(row.get("value"), (int, float))
              and not isinstance(row.get("value"), bool)]
    fields: list[tuple[str, str]] = []
    for key in ("subTitle", "describe"):
        if isinstance(option.get(key), str):
            fields.append((f"option.{key}", option[key]))
    for index, row in enumerate(option.get("data", [])):
        if isinstance(row, dict) and isinstance(row.get("description"), str):
            fields.append((f"option.data[{index}].description", row["description"]))
    for field, text in fields:
        for token, number, end in _chart_number_tokens(text):
            if "." not in token:
                continue
            if CHART_UNIT_SUFFIX_RE.match(text[end:]):
                continue
            if any(abs(number - value) <= 0.05 for value in values):
                value = next(value for value in values if abs(number - value) <= 0.05)
                return [f"chart {name} {field} restates plotted value {value}; remove the value from the chart text or keep it only in the plot data"]
    return []


def _chart_table_findings(report: str, name: str, option: dict, references: list[re.Match[str]]) -> list[str]:
    """Return hard findings for two plotted values repeated in a non-appendix section table."""
    if str(option.get("type") or "").lower() == "timeline":
        return []
    values = [float(row["value"]) for row in option.get("data", [])
              if isinstance(row, dict) and isinstance(row.get("value"), (int, float))
              and not isinstance(row.get("value"), bool)]
    lines = report.splitlines()
    heading_re = re.compile(r"^(#{1,6})\s+")
    for reference in references:
        line_no = report.count("\n", 0, reference.start())
        heading_index = 0
        heading_level = 0
        heading_text = ""
        for index in range(line_no, -1, -1):
            heading = heading_re.match(lines[index])
            if heading:
                heading_index = index
                heading_level = len(heading.group(1))
                heading_text = lines[index][heading.end():]
                break
        if "附录" in heading_text:
            continue
        end = len(lines)
        for index in range(heading_index + 1, len(lines)):
            heading = heading_re.match(lines[index])
            if heading and (heading_level == 0 or len(heading.group(1)) <= heading_level):
                # heading_level == 0 means the chart sits before the first heading: treat the
                # document head as the section so the appendix can never be counted as a repeat.
                end = index
                break
        matched: set[float] = set()
        for line in lines[heading_index:end]:
            if not line.strip().startswith("|"):
                continue
            for token, number, token_end in _chart_number_tokens(line):
                if CHART_UNIT_SUFFIX_RE.match(line[token_end:]):
                    continue
                for value in values:
                    if abs(number - value) <= 0.05:
                        matched.add(value)
        if len(matched) >= 2:
            displayed = ", ".join(str(value) for value in sorted(matched))
            return [f"chart {name} section table repeats plotted values {displayed}; move the chart to a section without the table or drop the duplicated values"]
    return []


def _appendix_preamble_findings(report: str, max_preamble: int = 100) -> list[str]:
    """The appendix is renderer output: title, one-line `—` legend, then the table.

    A long prose block between the title and the table means the report is carrying a hand-written
    specification of the appendix (or an older renderer's spec paragraph) — the defect that made
    readers scroll past ~600 characters of layout instructions before any data.
    """
    lines = report.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith(APPENDIX_TITLE)), None)
    if start is None:
        return []
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            return []
        if len(stripped) > max_preamble:
            return [f"the appendix opens with a {len(stripped)}-character prose block instead of the "
                    f"renderer's one-line legend; write no appendix specification paragraph (rows and "
                    f"columns come from the ledger, the title and legend from render-facts.py)"]
        return []
    return []


def _meta_narration_findings(report: str) -> tuple[list[str], list[str]]:
    """Report-about-itself findings: the authoring layer's labels, class and process wording."""
    findings: list[str] = []
    warnings: list[str] = []
    for match in META_LABEL_RE.finditer(report):
        findings.append(f"the report labels its own method ({match.group().strip()!r}); state the finding, "
                        f"not how the report was built")
    for match in META_COLUMN_RE.finditer(report):
        findings.append(f"table column {match.group().strip()!r} is the report classifying its own work; "
                        f"replace the label with the material difference it stands for")
    for label, pattern in (("method/class narration", METHOD_NARRATION_RE),
                           ("self-audit tail", SELF_AUDIT_RE),
                           ("internal field or runtime vocabulary", INTERNAL_VOCAB_RE)):
        seen: set[str] = set()
        for match in pattern.finditer(report):
            token = match.group()
            if token in seen:
                continue
            seen.add(token)
            findings.append(f"{label} in the deliverable: {token!r}")
    seen = set()
    for match in SELF_REFERENCE_RE.finditer(report):
        token = match.group()
        if token in seen:
            continue
        seen.add(token)
        warnings.append(f"the report refers to itself ({token!r}); write the finding directly")
    return findings, warnings


def _table_cells(report: str) -> list[str]:
    cells: list[str] = []
    for line in report.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        for cell in stripped.strip("|").split("|"):
            cell = cell.strip()
            if cell and set(cell) - set("-: "):
                cells.append(cell)
    return cells


def _chart_strings(value, out: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("id", "iframe_template"):
                continue
            _chart_strings(item, out)
    elif isinstance(value, list):
        for item in value:
            _chart_strings(item, out)
    elif isinstance(value, str):
        out.append(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical pre-delivery checks for report.md, citations.json and /workspace/visualizations/*.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--report", type=Path, default=Path("/workspace/output/report.md"))
    parser.add_argument("--citations", type=Path, default=Path("/workspace/output/citations.json"))
    parser.add_argument("--charts-dir", type=Path, default=Path("/workspace/visualizations"))
    parser.add_argument("--vis-prefix", default="/workspace/visualizations/",
                        help="required prefix of a ::visualization target (fixed at /workspace/visualizations/ "
                             "in the runtime; overridable only for a mirrored/test layout)")
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    findings: list[str] = []
    warnings: list[str] = []
    checks: list[tuple[str, str]] = []

    if not args.report.is_file():
        print(f"FAIL: report missing: {args.report}", file=sys.stderr)
        return 3
    report = args.report.read_text(encoding="utf-8", errors="replace")
    if not report.strip():
        print(f"FAIL: report is empty: {args.report}", file=sys.stderr)
        return 3

    # ---- report text invariants -------------------------------------------------------
    tokens = TOKEN_RE.findall(report)
    if tokens:
        sample = re.findall(r"\[\[\s*(?:fact|result)\s*:[^\]]*\]\]", report)[:3]
        findings.append(f"unresolved fact/result token(s) in the report: {sample}")
    braces = set(ANY_BRACE_RE.findall(report)) - {f"{{{{{ref}}}}}" for ref in MARKER_RE.findall(report)}
    braces = {item for item in braces if item not in {"{{APPENDIX}}", "{{appendix}}"}}
    if braces:
        findings.append(f"placeholder braces that are not {{ref_n}} markers: {sorted(braces)[:5]}")
    if ENTITY_RE.search(report):
        findings.append("`entity:` inline-reference syntax present (removed in v0.16, fails closed)")
    appendix_lines = [line for line in report.splitlines() if line.startswith(APPENDIX_TITLE)]
    if not appendix_lines:
        findings.append(f"appendix title `{APPENDIX_TITLE}` not found (the render gate appends it)")
    else:
        if len(appendix_lines) > 1:
            findings.append(f"appendix title appears {len(appendix_lines)} times — the appendix is renderer output; "
                            "write no appendix of your own and never render the same file twice")
        findings.extend(_appendix_preamble_findings(report))
    appendix_rows = 0
    if appendix_lines:
        start = report.index(appendix_lines[0])
        for line in report[start:].splitlines():
            if line.strip().startswith("|") and "---" not in line:
                appendix_rows += 1
        if appendix_rows <= 1:
            findings.append("appendix carries no data row (header only)")
    for label, pattern in LEAK_PATTERNS:
        hit = re.search(pattern, report)
        if hit:
            line_no = report.count("\n", 0, hit.start()) + 1
            findings.append(f"{label} leaked into the report at line {line_no}: {hit.group()!r}")
    for pattern in RUN_LOGISTICS:
        hit = re.search(pattern, report)
        if hit:
            warnings.append(f"run-logistics wording in the deliverable (A-P10): {hit.group()!r}")
    meta_findings, meta_warnings = _meta_narration_findings(report)
    findings.extend(meta_findings)
    warnings.extend(meta_warnings)
    checks.append(("report voice", "findings only — no method/class/self-audit narration"))
    if re.search(r"```\s*mermaid", report, re.IGNORECASE):
        findings.append("Mermaid block emitted; the delivery channel is chart JSON + ::visualization only")
    checks.append(("report text", "tokens/markers/entity/appendix"))

    # ---- markers vs citations --------------------------------------------------------
    markers = set(MARKER_RE.findall(report))
    citations: dict = {}
    if not args.citations.is_file():
        findings.append(f"citation file missing: {args.citations}")
    else:
        raw = args.citations.read_text(encoding="utf-8", errors="replace")
        text = raw.strip()
        if text.startswith("```") or not text.startswith("{"):
            findings.append("citation file is fenced or not raw JSON; it must be one unfenced JSON object")
        else:
            try:
                citations = json.loads(text)
            except json.JSONDecodeError as exc:
                findings.append(f"citation file is not valid JSON: {exc}")
        if not isinstance(citations, dict):
            findings.append("citation JSON must be an object keyed by ref_n")
            citations = {}
        for key, entry in sorted(citations.items()):
            if not re.fullmatch(r"ref_[1-9]\d*", str(key)):
                findings.append(f"citation key {key!r} is not a ref_n marker")
                continue
            if not isinstance(entry, dict):
                findings.append(f"{key}: citation entry is not an object")
                continue
            extra = sorted(set(entry) - set(CITATION_FIELDS))
            missing = [field for field in CITATION_FIELDS if field not in entry]
            if missing:
                findings.append(f"{key}: citation entry missing {missing}")
            if extra:
                findings.append(f"{key}: citation entry has extra fields {extra}")
            title = entry.get("title")
            link = entry.get("link")
            stamp = entry.get("paper_release_time_str")
            if not isinstance(title, str) or not title.strip():
                findings.append(f"{key}: empty title — a record that never came back must not be cited")
            if not isinstance(link, str) or not link.strip():
                findings.append(f"{key}: empty link")
            if not isinstance(stamp, str):
                findings.append(f"{key}: paper_release_time_str must be a string")
            elif stamp and not DATE_RE.match(stamp):
                findings.append(f"{key}: paper_release_time_str must be YYYY-MM-DD or empty (got {stamp!r})")
        keys = set(citations)
        if markers - keys:
            findings.append(f"markers without a citation key: {sorted(markers - keys)}")
        if keys - markers:
            findings.append(f"citation keys never used in the report: {sorted(keys - markers)}")
        if ENTITY_RE.search(json.dumps(citations, ensure_ascii=False)):
            findings.append("`entity:` syntax present in the citation JSON")
        checks.append(("markers vs citations", f"{len(markers)} marker(s) / {len(keys)} key(s)"))

    # ---- chart products --------------------------------------------------------------
    charts: dict[str, dict] = {}
    referenced: list[str] = []
    for match in VIS_REF_RE.finditer(report):
        path_match = PATH_ATTR_RE.search(match.group(1))
        if not path_match:
            findings.append(f"::visualization reference without a path attribute: {match.group(0)[:80]}")
            continue
        target = path_match.group(1)
        referenced.append(target)
        if not target.endswith(".json"):
            findings.append(f"::visualization target is not a .json file: {target}")
        if not target.startswith(args.vis_prefix):
            findings.append(f"::visualization target is outside the固定 prefix: {target}")
        if not Path(target).is_file():
            findings.append(f"::visualization target does not exist: {target}")
    if args.charts_dir.is_dir():
        for path in sorted(args.charts_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                findings.append(f"{path.name}: not valid JSON ({exc})")
                continue
            if not isinstance(payload, dict):
                findings.append(f"{path.name}: chart product is not an object")
                continue
            charts[path.name] = payload
            if set(payload) != {"id", "iframe_template", "option"}:
                findings.append(f"{path.name}: envelope keys must be exactly id/iframe_template/option "
                                f"(got {sorted(payload)}) — a bare option object is invalid")
                continue
            if payload.get("id") != "chart-visualization-json":
                findings.append(f"{path.name}: envelope id must be 'chart-visualization-json'")
            if not str(payload.get("iframe_template") or "").strip():
                findings.append(f"{path.name}: empty iframe_template (it is refreshed on every chart publish)")
            option = payload.get("option")
            if not isinstance(option, dict):
                findings.append(f"{path.name}: option must be an object")
                continue
            chart_type = str(option.get("type") or "").lower()
            expected_type = next((kind for prefix, kind in CHART_TYPE_BY_PREFIX if path.name.startswith(prefix)), None)
            if expected_type is None:
                warnings.append(f"{path.name}: file name is outside the fixed product names")
            elif chart_type != expected_type:
                findings.append(f"{path.name}: option.type is {chart_type!r}, expected {expected_type!r}")
            data = option.get("data")
            if not isinstance(data, list) or not data:
                findings.append(f"{path.name}: option.data is empty — an empty chart is not a deliverable")
                continue
            for index, row in enumerate(data):
                if not isinstance(row, dict):
                    findings.append(f"{path.name}.data[{index}]: not an object")
                    continue
                if chart_type == "timeline":
                    if not str(row.get("time") or "").strip():
                        findings.append(f"{path.name}.data[{index}]: missing time anchor")
                    if not str(row.get("description") or "").strip():
                        findings.append(f"{path.name}.data[{index}]: empty description")
                else:
                    if not str(row.get("label") or "").strip():
                        findings.append(f"{path.name}.data[{index}]: empty label")
                    if not isinstance(row.get("value"), (int, float)) or isinstance(row.get("value"), bool):
                        findings.append(f"{path.name}.data[{index}]: value is not numeric")
                    if not str(row.get("description") or "").strip():
                        findings.append(f"{path.name}.data[{index}]: empty description")
            if ENTITY_RE.search(json.dumps(payload, ensure_ascii=False)):
                findings.append(f"{path.name}: `entity:` syntax present in the chart JSON")
            if re.search(r"<html|<svg|<div", json.dumps(payload), re.IGNORECASE):
                findings.append(f"{path.name}: contains markup; chart products are pure JSON")
        unused_charts = sorted(set(charts) - {Path(item).name for item in referenced})
        if unused_charts:
            warnings.append(f"chart product(s) never referenced by the report: {unused_charts}")
    else:
        warnings.append(f"no chart directory at {args.charts_dir}")
    checks.append(("chart products", f"{len(charts)} file(s), {len(referenced)} reference(s)"))

    # Hard chart-duplication rules run only for referenced chart products.
    for name, payload in charts.items():
        option = payload.get("option")
        if not isinstance(option, dict) or name not in {Path(item).name for item in referenced}:
            continue
        findings.extend(_chart_text_findings(name, option))
        chart_refs = []
        for match in VIS_REF_RE.finditer(report):
            path_match = PATH_ATTR_RE.search(match.group(1))
            if path_match and Path(path_match.group(1)).name == name:
                chart_refs.append(match)
        findings.extend(_chart_table_findings(report, name, option, chart_refs))

    # ---- soft content checks ---------------------------------------------------------
    for cell in _table_cells(report):
        refs = MARKER_RE.findall(cell)
        if len(refs) != len(set(refs)):
            warnings.append(f"table cell cites the same ref more than once: {cell[:60]!r}")
    citation_shingles: set[str] = set()
    for entry in citations.values():
        if isinstance(entry, dict):
            citation_shingles |= _shingles(str(entry.get("title") or "")) | _shingles(str(entry.get("link") or ""))
    cell_shingles: set[str] = set()
    for cell in _table_cells(report):
        cell_shingles |= _shingles(MARKER_RE.sub("", cell))
    shared: list[str] = []
    for name, payload in charts.items():
        strings: list[str] = []
        _chart_strings(payload.get("option"), strings)
        for text in strings:
            run = (_shingles(MARKER_RE.sub("", text)) & cell_shingles) - citation_shingles
            if run:
                shared.append(f"{name}: {sorted(run)[0]!r}")
                break
    if shared:
        warnings.append("chart text shares an 8-character run with a table cell (proper names excepted): "
                        + "; ".join(shared[:3]))

    if args.json:
        print(json.dumps({"findings": findings, "warnings": warnings, "checks": checks}, ensure_ascii=False))
    else:
        if args.verbose:
            for name, note in checks:
                print(f"  ok: {name} — {note}")
        for item in findings:
            print(f"FAIL: {item}")
        for item in warnings:
            print(f"WARN: {item}")
        if not findings:
            print(f"PASS: {len(checks)} check group(s) green"
                  + (f", {len(warnings)} warning(s)" if warnings else "")
                  + f" — report {len(report.encode('utf-8'))} B, {len(markers)} marker(s), "
                    f"{len(charts)} chart file(s)")
    if findings:
        return 3
    return 4 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
