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

Usage
-----
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/build_ledger.py --facts work/facts.json --out work/ledger.json
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/build_ledger.py --facts work/facts.json --stats

Exit codes: 0 ledger written; 3 findings (nothing written); 2 usage / input error.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate work/facts.json and write the strict work/ledger.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--facts", type=Path, default=Path("work/facts.json"))
    parser.add_argument("--out", type=Path, default=Path("work/ledger.json"))
    parser.add_argument("--refs", type=Path, default=Path("work/refs.json"),
                        help="ref inventory written by prep_sources.py (for trial/source_file defaults)")
    parser.add_argument("--stats", action="store_true", help="print fact counts by ref and kind")
    parser.add_argument("--check", action="store_true", help="validate only; write nothing")
    args = parser.parse_args(argv)

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
