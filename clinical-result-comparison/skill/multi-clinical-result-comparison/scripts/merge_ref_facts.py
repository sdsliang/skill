#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge per-ref subagent shards into one `work/facts.json`.

Delegation splits the ledger across one subagent per ref; each shard writes
`work/facts.ref_<n>.json` in the `facts.json` shape (`{"records":[…],"facts":[…]}` or a bare list of
facts).  The main thread must **not** re-type those rows: this script concatenates the shard files in
ref order and is the only place the merged file is produced.

It is deliberately dumb about clinical content — `build_ledger.py` stays the validation gate — but it
does the checks that are about the *split* itself, so a bad shard is caught next to its filename
instead of surfacing much later as a `build_ledger` finding:

* a fact/record whose `ref` is not in `work/refs.json`;
* the same fact `id` or record `ref` produced by two shards;
* a known ref that no shard covered (WARN — a shard may legitimately return nothing for a source
  with no usable numbers, but it must never be silently missing).

Usage:
    python3 scripts/merge_ref_facts.py --shards work --refs work/refs.json --out work/facts.json
    python3 scripts/merge_ref_facts.py --check          # merge in memory, write nothing

Exit codes: 0 merged (or `--check` clean); 3 findings (nothing written); 2 unreadable input or
unwritable output.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import tempfile
from pathlib import Path

REF_NUM_RE = re.compile(r"ref_(\d+)")
DEFAULT_PATTERN = "facts.ref_*.json"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False)
    try:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


def _load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _known_refs(path: Path) -> dict:
    data = _load(path)
    if not isinstance(data, dict):
        raise ValueError("refs.json must be an object")
    return {str(key): value for key, value in data.items()}


def _ref_number(name: str) -> tuple[int, str]:
    match = REF_NUM_RE.search(name)
    return (int(match.group(1)) if match else 10 ** 6, name)


def _rows(data, key: str) -> list:
    if data is None:
        return []
    if isinstance(data, list):
        return data if key == "facts" else []
    if isinstance(data, dict):
        value = data.get(key)
        return value if isinstance(value, list) else []
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge per-ref facts shards into work/facts.json.")
    parser.add_argument("--shards", default="work", help="directory holding the shard files (default: work)")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help=f"shard file name pattern (default: {DEFAULT_PATTERN})")
    parser.add_argument("--refs", default="work/refs.json", help="ref inventory written by prep_sources.py")
    parser.add_argument("--out", default="work/facts.json", help="merged output (default: work/facts.json)")
    parser.add_argument("--check", action="store_true", help="merge in memory; write nothing")
    args = parser.parse_args(argv)

    shard_dir = Path(args.shards)
    refs_path = Path(args.refs)
    if not refs_path.is_file():
        print(f"ERROR: {refs_path} is missing or empty; run prep_sources.py first", file=sys.stderr)
        return 3
    try:
        refs = _known_refs(refs_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: cannot read {refs_path}: {exc}; run prep_sources.py first", file=sys.stderr)
        return 3
    if not refs:
        print(f"ERROR: {refs_path} lists no refs; run prep_sources.py first", file=sys.stderr)
        return 3

    names = sorted(glob.glob(str(shard_dir / args.pattern)), key=lambda item: _ref_number(Path(item).name))
    if not names:
        print(f"ERROR: no shard file matching {args.pattern} under {shard_dir} — "
              f"the delegated subagents must write one file per ref", file=sys.stderr)
        return 3

    findings: list[str] = []
    warnings: list[str] = []
    records: list[dict] = []
    facts: list[dict] = []
    seen_record_refs: dict[str, str] = {}
    seen_fact_ids: dict[str, str] = {}
    covered: dict[str, int] = {}
    per_shard: list[tuple[str, int, int]] = []

    for name in names:
        path = Path(name)
        try:
            data = _load(path)
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(f"{path.name}: cannot read as JSON ({exc}) — the shard must write valid JSON")
            continue
        shard_records = _rows(data, "records")
        shard_facts = _rows(data, "facts")
        if not shard_records and not shard_facts:
            findings.append(f"{path.name}: no `records` and no `facts` — write the facts.json shape, "
                            f"or a bare list of facts")
            continue
        for record in shard_records:
            if not isinstance(record, dict):
                findings.append(f"{path.name}: a `records` entry is not an object")
                continue
            ref = str(record.get("ref", ""))
            if ref not in refs:
                findings.append(f"{path.name}: record `ref` {ref!r} is not in {refs_path.name}")
            elif ref in seen_record_refs:
                findings.append(f"{path.name}: record {ref} is already produced by {seen_record_refs[ref]}")
            else:
                seen_record_refs[ref] = path.name
            records.append(record)
        for fact in shard_facts:
            if not isinstance(fact, dict):
                findings.append(f"{path.name}: a `facts` entry is not an object")
                continue
            ref = str(fact.get("ref", ""))
            if ref not in refs:
                findings.append(f"{path.name}: fact `ref` {ref!r} is not in {refs_path.name} "
                                f"(shards must keep the ref their source file belongs to)")
            fact_id = str(fact.get("id", ""))
            if not fact_id:
                findings.append(f"{path.name}: a fact has no `id`")
            elif fact_id in seen_fact_ids:
                findings.append(f"{path.name}: fact id {fact_id!r} is already used by {seen_fact_ids[fact_id]} "
                                f"— ids must be unique across shards (prefix them with the ref)")
            else:
                seen_fact_ids[fact_id] = path.name
            covered[ref] = covered.get(ref, 0) + 1
            facts.append(fact)
        per_shard.append((path.name, len(shard_records), len(shard_facts)))

    for ref in sorted(refs, key=lambda item: _ref_number(item)):
        if not covered.get(ref):
            warnings.append(f"{ref} has no fact from any shard — every selected ref must be extracted "
                            f"(a source with no usable number still needs its record)")

    print(f"shards merged: {len(names)}")
    for name, record_count, fact_count in per_shard:
        print(f"  {name}: {record_count} record(s), {fact_count} fact(s)")
    if facts:
        for ref in sorted(covered, key=lambda item: _ref_number(item)):
            print(f"  {ref}: {covered[ref]} fact(s)")

    if findings:
        print(f"FINDINGS ({len(findings)}) — nothing written:", file=sys.stderr)
        for item in findings:
            print(f"  - {item}", file=sys.stderr)
        return 3
    for item in warnings:
        print(f"WARN: {item}", file=sys.stderr)

    records.sort(key=lambda item: _ref_number(str(item.get("ref", ""))))
    facts.sort(key=lambda item: _ref_number(str(item.get("ref", ""))))
    ledger = {
        "records": records,
        "facts": facts,
    }
    if args.check:
        print(f"OK (check only): {len(records)} record(s), {len(facts)} fact(s) — run without --check to write")
        return 0
    try:
        _atomic_write(Path(args.out), json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"ERROR: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    print(f"WROTE {args.out}: {len(records)} record(s), {len(facts)} fact(s) "
          f"— now run build_ledger.py on it (the validation gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
