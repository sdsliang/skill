#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile `work/facts.json` (data only) into the strict `work/ledger.json` the render gate reads.

`scripts/render-facts.py` validates the ledger *and* renders the appendix.  It fails closed on
things a model can only notice when the run is already half-wasted: a missing field, a `value`
that is not inside its `quote`, a `quote` that is not an exact substring of `source_file`.  This
script moves every one of those checks *before* drafting: you write the numbers once, in a
loose file, and this compiler either emits a ledger the gate accepts or lists exactly what to
fix.  It never invents a value, never drops a fact, and never renders anything.

Write `work/facts.json` like this (only the listed keys are read; the rest is your own note):

    {
      "records": [
        {"ref": "ref_1", "trial": "NCT02729025", "identity": "NCT02729025｜…｜…",
         "conclusion": "一句披露级结论。"}
      ],
      "facts": [
        {"id": "ocean-mds-tbr-diff", "ref": "ref_1", "study": "NCT02729025",
         "kind": "有效性", "endpoint": "MDS TBR 较基线变化", "arm": "依洛尤单抗 420 mg 每月一次",
         "value": "-5.3", "unit": "%", "timepoint": "第 16 周",
         "quote": "安慰剂组 MDS TBR 下降 5.3%"}
      ]
    }

Required per record: `ref`, `identity`, `conclusion` (`trial` strongly recommended — it is the
appendix merge key).  Required per fact: `id`, `ref`, `study`, `kind`, `endpoint`, `arm`,
`value`, `unit`, `quote`.  Optional per fact (defaulted): `version`, `population`, `timepoint`,
`assessment`, `statistics`, `source_file`.

`--scaffold` is a separate mode.  It reads the pulled params payload and `refs.json`, then writes
a candidate `work/facts.candidates.json`; it never reads `work/facts.json` or writes a ledger.
Every candidate value is copied from the payload and still needs source verification.

Usage
-----
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/build_ledger.py --facts work/facts.json --out work/ledger.json
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/build_ledger.py --facts work/facts.json --stats
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/build_ledger.py --scaffold --tool-results /workspace/tool_results

Exit codes: 0 ledger/candidate written; 3 findings or missing scaffold refs (nothing written);
2 usage / input or write error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

RECORD_REQUIRED = ("ref", "identity", "conclusion")
RECORD_ORDER = ("ref", "trial", "identity", "conclusion", "title", "design", "arms", "coverage")
FACT_REQUIRED = ("id", "ref", "study", "kind", "endpoint", "arm", "value", "unit", "quote")
FACT_ORDER = (
    "id", "ref", "study", "version", "endpoint", "arm", "population", "timepoint",
    "assessment", "kind", "value", "unit", "statistics", "source_file", "quote",
)
FACT_DEFAULTS = {
    "version": "未报告",
    "population": "未报告",
    "timepoint": "未报告",
    "assessment": "未报告",
    "statistics": "",
}
KINDS = ("试验设计", "试验结论", "有效性", "安全性", "PK/PD", "PRO", "其他")
KIND_RE = re.compile(r"^(试验设计|试验结论|有效性|安全性|PK/PD|PRO|其他)(?:·.+)?$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REF_RE = re.compile(r"^ref_[1-9]\d*$")
MINUS_TRANSLATION = str.maketrans({"\N{MINUS SIGN}": "-"})
ESID_KEYS = (
    "clinical_result_extra_esid", "clinical_result_esid", "pharmcube-extra_esid",
    "pharmcube-esid", "_extra_esid", "_esid", "extra_esid", "esid",
)
PREFIX = "clinical_result_"
UNUSABLE_RESULTS = {"", "NR", "NE", "未报告", "NA", "N/A", "-", "—"}
TIMEPOINT_RE = re.compile(r"(?:周|月|天|年|week|day|month)", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"[。！？；;\n]")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).translate(MINUS_TRANSLATION)).strip()


def _clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _resolve_source(source_file: str, refs: dict, ref: str, ledger_dir: Path, cwd: Path) -> str:
    """Return an absolute source path, or '' when it cannot be located."""
    candidates: list[Path] = []
    if source_file:
        path = Path(source_file)
        candidates = [path] if path.is_absolute() else [cwd / path, ledger_dir / path]
    else:
        hint = (refs.get(ref) or {}).get("source_file")
        if hint:
            candidates.append(Path(hint))
        candidates.append(ledger_dir / "sources" / f"{ref}.txt")
        candidates.append(cwd / "work" / "sources" / f"{ref}.txt")
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate.resolve())
        except OSError:
            continue
    return ""


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _payload_text(record: dict, *names: str) -> str:
    for name in names:
        keys = (PREFIX + name, f"_{name}", f"pharmcube-{name}", name)
        for key in keys:
            value = record.get(key)
            if value is None or value == "":
                continue
            if isinstance(value, list):
                values = [_clean(item) for item in value if _clean(item)]
                if values:
                    return "、".join(values)
            else:
                text = _clean(value)
                if text:
                    return text
    return ""


def _payload_esid(record: dict) -> str:
    for key in ESID_KEYS:
        value = record.get(key)
        text = _clean(value)
        if text:
            return text
    return ""


def _load_payload_records(tool_results: Path) -> tuple[list[dict], list[str]]:
    directory = tool_results / "pharmcube-query-clinical-result-with-params"
    records: list[dict] = []
    notes: list[str] = []
    try:
        paths = sorted(directory.glob("*.jsonl"))
    except OSError as exc:
        raise OSError(f"cannot scan {directory}: {exc}") from exc
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            raise OSError(f"cannot read {path}: {exc}") from exc
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                notes.append(f"跳过无法解析的 payload 行：{path.name}:{line_number}。")
                continue
            if not isinstance(value, dict):
                notes.append(f"跳过非对象 payload：{path.name}:{line_number}。")
                continue
            records.append(value)
    return records, notes


def _normalise_refs(value) -> dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, dict] = {}
    for ref, entry in value.items():
        if isinstance(entry, dict) and _clean(entry.get("esid")):
            output[str(ref)] = entry
    return output


def _payload_list(record: dict, name: str):
    for key in (PREFIX + name, f"_{name}", f"pharmcube-{name}", name):
        value = record.get(key)
        if value is not None:
            return value
    return []


def _trial_from_payload(record: dict, ref_entry: dict, esid: str) -> str:
    trial = _payload_text(record, "trial_abbreviation")
    if trial:
        return trial
    projects = _payload_list(record, "projects")
    if isinstance(projects, dict):
        projects = [projects]
    registration_re = re.compile(
        r"(?:NCT\d+|EudraCT\d{4}-\d{6}-\d{2}|ChiCTR[A-Za-z0-9-]+|ISRCTN\d+|jRCT[A-Za-z0-9-]+)",
        re.IGNORECASE,
    )
    if isinstance(projects, list):
        for project in projects:
            if not isinstance(project, dict):
                continue
            ids = project.get("associate_ids", project.get("associated_ids", []))
            if isinstance(ids, (str, int, float)):
                ids = [ids]
            if not isinstance(ids, list):
                continue
            for item in ids:
                match = registration_re.search(_clean(item))
                if match:
                    return match.group(0)
    return _clean(ref_entry.get("trial_abbreviation")) or esid


def _identity(record: dict, trial: str) -> str:
    parts = [trial] if trial else []
    indication = _payload_text(record, "indication_name")
    if indication:
        parts.append(indication)
    for name in ("randomized", "blinded", "trial_control", "positive_placebo_control"):
        value = _payload_text(record, name)
        if value:
            parts.append(value)
    stage = _payload_text(record, "clinical_stage_cn", "stage", "clinical_stage")
    if stage:
        parts.append(stage)
    return "｜".join(parts)


def _arm_fallback(arm: dict) -> str:
    names = arm.get("therapeutic_schedule_name_cn", [])
    if isinstance(names, (str, int, float)):
        names = [names]
    parts = [_clean(item) for item in names if _clean(item)] if isinstance(names, list) else []
    for key in ("dose", "dosage", "dose_value", "dose_unit", "therapeutic_schedule_text_cn"):
        value = _clean(arm.get(key))
        if value and value not in parts:
            parts.append(value)
    return " ".join(parts)


def _split_endpoint(label: str, seen: set[str]) -> tuple[str, str, str]:
    pieces = [piece.strip() for piece in str(label or "").split("|")]
    endpoint = pieces[0] if pieces else ""
    if endpoint:
        base = re.sub(r"\s*\([^()]*\)\s*$", "", endpoint).strip()
        if base in seen:
            endpoint = base
        seen.add(endpoint)
    qualifiers: list[str] = []
    for piece in pieces[1:]:
        qualifiers.extend(part.strip() for part in re.split(r"[;；]", piece) if part.strip())
    timepoints = [part for part in qualifiers if TIMEPOINT_RE.search(part)]
    assessments = [part for part in qualifiers if not TIMEPOINT_RE.search(part)]
    return endpoint, "；".join(assessments), "；".join(timepoints)


def _source_file(ref: str, entry: dict, sources: Path) -> str:
    candidate = _clean(entry.get("source_file"))
    if candidate:
        try:
            if Path(candidate).is_file():
                return candidate
        except OSError:
            pass
    return str(sources / f"{ref}.txt")


def _quote_for_value(path_text: str, value: str, cwd: Path) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        path = cwd / path
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for sentence in SENTENCE_SPLIT_RE.split(source):
        normalised = _normalise_text(sentence)
        if value in normalised:
            return normalised
    return ""


def _id_token(value: str, fallback: str) -> str:
    token = "".join(char for char in _clean(value) if ord(char) < 128 and (char.isalnum() or char in "._-"))
    return token[:8] or fallback


def _scaffold_tool_results_path(path: Path) -> Path:
    if path != Path("/workspace/tool_results") or path.is_dir():
        return path
    for fallback in (Path("tool_results"), Path("/workspace/work/tool_results")):
        if fallback.is_dir():
            return fallback
    return path


def _scaffold(args) -> int:
    refs_path: Path = args.refs
    if not refs_path.is_file():
        print(f"ERROR: {refs_path} is missing or empty; run prep_sources.py first", file=sys.stderr)
        return 3
    try:
        refs = _normalise_refs(_load(refs_path))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {refs_path}: {exc}; run prep_sources.py first", file=sys.stderr)
        return 3
    if not refs:
        print(f"ERROR: {refs_path} is missing or empty; run prep_sources.py first", file=sys.stderr)
        return 3
    by_esid = {_clean(entry.get("esid")): (ref, entry) for ref, entry in refs.items()}
    tool_results = _scaffold_tool_results_path(args.tool_results)
    try:
        payloads, load_notes = _load_payload_records(tool_results)
    except OSError as exc:
        print(f"ERROR: cannot read tool results: {exc}", file=sys.stderr)
        return 2
    if not payloads:
        print(f"ERROR: no payload records found under {tool_results / 'pharmcube-query-clinical-result-with-params'}", file=sys.stderr)
        return 2

    records: list[dict] = []
    facts: list[dict] = []
    notes = list(load_notes)
    skipped_esids: list[str] = []
    missing_values = 0
    unresolved_arms = 0
    missing_quotes: list[str] = []
    used_ids: set[str] = set()
    endpoint_seen: dict[str, set[str]] = {}
    cwd = Path.cwd()

    for payload_index, payload in enumerate(payloads):
        esid = _payload_esid(payload)
        mapped = by_esid.get(esid)
        if mapped is None:
            skipped_esids.append(esid or "（无 esid）")
            continue
        ref, ref_entry = mapped
        trial = _trial_from_payload(payload, ref_entry, esid)
        records.append({"ref": ref, "trial": trial, "identity": _identity(payload, trial), "conclusion": ""})
        arms = _payload_list(payload, "arms")
        arm_by_id = {str(item.get("arm_id")): item for item in arms if isinstance(item, dict) and _clean(item.get("arm_id"))} if isinstance(arms, list) else {}
        results = _payload_list(payload, "study_results")
        if not isinstance(results, list):
            continue
        seen = endpoint_seen.setdefault(ref, set())
        for item_index, item in enumerate(results):
            if not isinstance(item, dict):
                continue
            raw_result = item.get("result")
            value = _clean(raw_result).strip()
            if not value or value in UNUSABLE_RESULTS or value.upper() in {"NR", "NE", "NA", "N/A"}:
                missing_values += 1
                continue
            endpoint, assessment, timepoint = _split_endpoint(_clean(item.get("endpoint_label")), seen)
            arm_id = _clean(item.get("arm_id"))
            arm = arm_by_id.get(arm_id)
            arm_text = _clean(arm.get("regimen_label")) if isinstance(arm, dict) else ""
            if not arm_text and isinstance(arm, dict):
                arm_text = _arm_fallback(arm)
            if not arm_text:
                unresolved_arms += 1
            kind_raw = _clean(item.get("endpoint_attribute"))
            kind = kind_raw if KIND_RE.match(kind_raw) else "有效性"
            statistics: list[str] = []
            ci = _clean(item.get("outcome_ci"))
            p_value = _clean(item.get("outcome_p_value"))
            if ci:
                statistics.append(f"95% CI {ci}")
            if p_value:
                statistics.append(f"p={p_value}")
            base_id = f"{_id_token(ref, 'ref')}-{_id_token(arm_id, 'noarm')}-{_id_token(_clean(item.get('endpoint_id')), 'noendpoint')}"
            fact_id = base_id
            suffix = 2
            while fact_id in used_ids:
                fact_id = f"{base_id}-{suffix}"
                suffix += 1
            used_ids.add(fact_id)
            source_file = _source_file(ref, ref_entry, args.sources)
            quote = _quote_for_value(source_file, value.translate(MINUS_TRANSLATION), cwd)
            fact = {
                "id": fact_id, "ref": ref, "study": trial, "version": "", "endpoint": endpoint,
                "arm": arm_text, "population": "", "timepoint": timepoint, "assessment": assessment,
                "kind": kind, "value": value, "unit": _clean(item.get("result_unit")),
                "statistics": "；".join(statistics), "source_file": source_file, "quote": quote,
            }
            facts.append(fact)
            if not quote:
                missing_quotes.append(fact_id)

    records.sort(key=lambda item: item["ref"])
    facts.sort(key=lambda item: item["ref"])
    notes.insert(0, f"已 scaffold {len(records)} 条记录、{len(facts)} 条事实。")
    notes.append("所有 value 均逐字复制 payload 的 result（仅去除首尾空白）；使用前必须对照原文核验。")
    notes.append("conclusion 始终留空，必须由模型补写。")
    notes.append("identity 只是预填，必须结合原文最终定稿。")
    notes.append("arm 必须在报告中改写一次为自己的中文身份短语，之后逐字复用。")
    notes.append(f"因 result 为空或为 NR/NE/未报告/NA/N/A/-/—，跳过 {missing_values} 条结果。")
    notes.append(f"有 {len(missing_quotes)} 条事实缺少 quote，必须由模型从原文手工补齐。")
    for fact_id in missing_quotes:
        notes.append(f"缺少 quote 的 fact id：{fact_id}。")
    if unresolved_arms:
        notes.append(f"有 {unresolved_arms} 条事实无法按 arm_id 找到可用 arm，arm 留空，必须人工核对。")
    if skipped_esids:
        notes.append("因 esid 未映射到 refs.json 而跳过 payload 记录：" + "、".join(skipped_esids) + "。")
    output = {"records": records, "facts": facts, "_notes": notes}
    try:
        _atomic_write(args.out, json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"ERROR: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    print(f"WROTE {args.out}: {len(records)} record(s), {len(facts)} fact(s) ({len(missing_quotes)} need a quote)")
    for note in notes:
        print(f"  {note}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate work/facts.json or scaffold a candidate from the pulled payload.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scaffold", action="store_true",
                        help="build candidate records/facts from the pulled params payload")
    parser.add_argument("--facts", type=Path, default=Path("work/facts.json"),
                        help="facts input for the default ledger mode")
    parser.add_argument("--out", type=Path,
                        help="output path (scaffold default: work/facts.candidates.json; ledger default: work/ledger.json)")
    parser.add_argument("--tool-results", type=Path, default=Path("/workspace/tool_results"),
                        help="payload directory for --scaffold; falls back like prep_sources.py")
    parser.add_argument("--sources", type=Path, default=Path("work/sources"),
                        help="source directory for --scaffold facts")
    parser.add_argument("--refs", type=Path, default=Path("work/refs.json"),
                        help="ref inventory written by prep_sources.py (for trial/source_file defaults)")
    parser.add_argument("--stats", action="store_true", help="print fact counts by ref and kind")
    parser.add_argument("--check", action="store_true", help="validate only; write nothing")
    args = parser.parse_args(argv)
    if args.out is None:
        args.out = Path("work/facts.candidates.json" if args.scaffold else "work/ledger.json")
    if args.scaffold:
        return _scaffold(args)

    facts_path: Path = args.facts
    if not facts_path.is_file():
        print(f"ERROR: {facts_path} not found; write work/facts.json first", file=sys.stderr)
        return 2
    try:
        data = _load(facts_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {facts_path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict) or not isinstance(data.get("records"), list) or not isinstance(data.get("facts"), list):
        print("ERROR: work/facts.json must be an object with `records` and `facts` arrays", file=sys.stderr)
        return 2

    refs: dict = {}
    if args.refs.is_file():
        try:
            refs = _load(args.refs) or {}
        except (OSError, json.JSONDecodeError):
            refs = {}
    ledger_dir = args.out.parent if str(args.out.parent) else Path(".")
    cwd = Path.cwd()

    findings: list[str] = []
    warnings: list[str] = []

    records: list[dict] = []
    known_refs: set[str] = set()
    for index, raw in enumerate(data["records"]):
        if not isinstance(raw, dict):
            findings.append(f"records[{index}] is not an object")
            continue
        record = {key: _clean(raw.get(key)) for key in RECORD_ORDER if key in raw}
        for key in RECORD_REQUIRED:
            if not record.get(key):
                findings.append(f"records[{index}] ({record.get('ref') or 'no ref'}) is missing `{key}`")
        ref = record.get("ref", "")
        if ref and not REF_RE.match(ref):
            findings.append(f"records[{index}].ref must look like ref_1 (got {ref!r})")
        if ref in known_refs:
            findings.append(f"duplicate record ref: {ref}")
        known_refs.add(ref)
        if not record.get("trial"):
            hint = (refs.get(ref) or {}).get("trial_abbreviation") or ""
            if hint:
                record["trial"] = hint
            else:
                warnings.append(f"records[{index}] ({ref}) has no `trial`: the appendix merges columns by it")
        records.append(record)

    facts: list[dict] = []
    seen_ids: set[str] = set()
    studies_by_ref: dict[str, set[str]] = {}
    quotes: dict[str, str] = {}
    for index, raw in enumerate(data["facts"]):
        if not isinstance(raw, dict):
            findings.append(f"facts[{index}] is not an object")
            continue
        fact = {key: _clean(raw.get(key)) for key in FACT_ORDER if key in raw}
        for key, value in FACT_DEFAULTS.items():
            if not fact.get(key):
                fact[key] = value
        label = f"facts[{index}] ({fact.get('id') or 'no id'})"
        for key in FACT_REQUIRED:
            if not fact.get(key):
                findings.append(f"{label} is missing `{key}`")
        fact_id = fact.get("id", "")
        if fact_id and not ID_RE.match(fact_id):
            findings.append(f"{label}.id must be ASCII letters/digits/._- (no spaces or CJK)")
        if fact_id in seen_ids:
            findings.append(f"duplicate fact id: {fact_id}")
        seen_ids.add(fact_id)
        ref = fact.get("ref", "")
        if ref and ref not in known_refs:
            findings.append(f"{label}.ref is not in records[]: {ref}")
        kind = fact.get("kind", "")
        if kind and not KIND_RE.match(kind):
            findings.append(f"{label}.kind must be one of {', '.join(KINDS)} (may add `·家族`, e.g. 有效性·OS): {kind!r}")
        if ref and fact.get("study"):
            studies_by_ref.setdefault(ref, set()).add(fact["study"])

        source_file = _resolve_source(_clean(raw.get("source_file")), refs, ref, ledger_dir, cwd)
        if not source_file:
            findings.append(f"{label}: no reachable source file — run /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py (looked for "
                            f"work/sources/{ref}.txt and refs.json entries)")
        else:
            fact["source_file"] = source_file
            if source_file not in quotes:
                try:
                    quotes[source_file] = _normalise_text(Path(source_file).read_text(encoding="utf-8", errors="replace"))
                except OSError as exc:
                    findings.append(f"{label}: cannot read {source_file}: {exc}")
                    quotes[source_file] = ""
            source_text = quotes[source_file]
            quote = _normalise_text(fact.get("quote", ""))
            value = _normalise_text(fact.get("value", ""))
            if source_text and quote and quote not in source_text:
                findings.append(f"{label}: `quote` is not an exact substring of {Path(source_file).name} "
                                f"— copy it from the record body: {quote[:70]!r}")
            if quote and value and value not in quote:
                findings.append(f"{label}: `value` {value!r} is absent from `quote` ({quote[:70]!r})")
        facts.append(fact)

    for ref, studies in sorted(studies_by_ref.items()):
        if len(studies) > 1:
            warnings.append(f"{ref} uses {len(studies)} different `study` labels ({sorted(studies)}); "
                            f"one trial must use one string or the appendix splits its rows")

    if args.stats:
        print(f"records: {len(records)}  facts: {len(facts)}")
        for ref in sorted(known_refs):
            mine = [fact for fact in facts if fact.get("ref") == ref]
            kinds = Counter(fact.get("kind", "?") for fact in mine)
            print(f"  {ref}: {len(mine)} fact(s) " + ", ".join(f"{k}×{v}" for k, v in kinds.most_common()))

    if findings:
        print(f"FINDINGS ({len(findings)}) — nothing written:", file=sys.stderr)
        for item in findings:
            print(f"  - {item}", file=sys.stderr)
        return 3
    for item in warnings:
        print(f"WARN: {item}", file=sys.stderr)

    ledger = {
        "records": [{key: record[key] for key in RECORD_ORDER if key in record} for record in records],
        "facts": [{key: fact[key] for key in FACT_ORDER if key in fact} for fact in facts],
    }
    if args.check:
        print(f"OK (check only): {len(records)} record(s), {len(facts)} fact(s)")
        return 0
    try:
        _atomic_write(args.out, json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"ERROR: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    print(f"WROTE {args.out}: {len(records)} record(s), {len(facts)} fact(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
