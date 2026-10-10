#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write the strict citation JSON from the ref inventory, and assert it matches the report.

`/workspace/output/citations.json` has to carry `title` / `link` **byte-for-byte** from the
pulled record and `paper_release_time_str` as the `YYYY-MM-DD` part of `paper_release_time`,
with exactly one entry per `{{ref_n}}` marker used in the report — no unused key (an unused key
means the report cites a source it never uses) and no missing key.  Copying those fields by
hand is both slow and the one place where a single character breaks the traceability contract,
so build the file from `work/refs.json` (written by `prep_sources.py`, which read the raw pull).

    python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_citations.py --refs work/refs.json --report /workspace/output/report.md
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_citations.py --refs work/refs.json --report output/report.md \
        --full-text ref_2=https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/

`--full-text ref_n=<url>` performs the C1/C2 full-text link substitution required by
`references/input-contract.md` for a record analysed from a retrieved PMC full text (title
unchanged).  When `--report` is given the file is restricted to the refs the report actually
cites; unused refs are dropped and listed.  Without `--report` every ref is emitted.

Exit codes: 0 written; 3 marker parity / field problem (nothing written); 2 usage / IO.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MARKER_RE = re.compile(r"\{\{(ref_[1-9]\d*)\}\}")
FIELDS = ("title", "link", "paper_release_time_str")


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


def _date_only(value: str) -> str:
    match = re.match(r"\s*(\d{4}-\d{2}-\d{2})", value or "")
    return match.group(1) if match else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build /workspace/output/citations.json from work/refs.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--refs", type=Path, default=Path("work/refs.json"))
    parser.add_argument("--out", type=Path, default=Path("/workspace/output/citations.json"))
    parser.add_argument("--report", type=Path, help="report file; its {{ref_n}} markers must equal the keys")
    parser.add_argument("--full-text", action="append", default=[], metavar="ref_n=URL",
                        help="C1/C2 full-text link substitution for a record read from PMC full text (repeatable)")
    parser.add_argument("--keep-unused", action="store_true", help="keep refs the report does not cite")
    parser.add_argument("--check", action="store_true", help="validate only; write nothing")
    parser.add_argument("--print", action="store_true", dest="print_body", help="also print the JSON body")
    args = parser.parse_args(argv)

    if not args.refs.is_file():
        print(f"ERROR: {args.refs} not found; run /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py first", file=sys.stderr)
        return 2
    try:
        refs = json.loads(Path(args.refs).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {args.refs}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(refs, dict) or not refs:
        print(f"ERROR: {args.refs} must be a non-empty object keyed by ref_n", file=sys.stderr)
        return 2

    overrides: dict[str, str] = {}
    for item in args.full_text:
        if "=" not in item:
            print(f"ERROR: --full-text expects ref_n=URL (got {item!r})", file=sys.stderr)
            return 2
        ref, url = item.split("=", 1)
        ref, url = ref.strip(), url.strip()
        if ref not in refs:
            print(f"ERROR: --full-text names an unknown ref: {ref}", file=sys.stderr)
            return 2
        if not url.startswith(("http://", "https://")):
            print(f"ERROR: --full-text needs an absolute URL: {url!r}", file=sys.stderr)
            return 2
        overrides[ref] = url

    cited: set[str] | None = None
    if args.report is not None:
        if not args.report.is_file():
            print(f"ERROR: report not found: {args.report}", file=sys.stderr)
            return 2
        try:
            report = args.report.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"ERROR: cannot read {args.report}: {exc}", file=sys.stderr)
            return 2
        cited = set(MARKER_RE.findall(report))
        if not cited:
            print(f"ERROR: no {{{{ref_n}}}} marker found in {args.report}; the report cites nothing",
                  file=sys.stderr)
            return 3

    keys = sorted(refs, key=lambda key: int(key.split("_")[1])) if all(
        re.fullmatch(r"ref_\d+", key) for key in refs) else sorted(refs)
    selected = keys if cited is None or args.keep_unused else [key for key in keys if key in cited]

    findings: list[str] = []
    payload: dict[str, dict[str, str]] = {}
    for ref in selected:
        entry = refs[ref] or {}
        title = str(entry.get("title") or "")
        link = overrides.get(ref) or str(entry.get("link") or "")
        release = str(entry.get("paper_release_time") or "")
        stamp = str(entry.get("paper_release_time_str") or "") or _date_only(release)
        if ref in overrides:
            note = entry.get("link") or ""
            print(f"NOTE: {ref} link substituted with the retrieved full text "
                  f"({overrides[ref]}; record link was {note})", file=sys.stderr)
        if not title.strip():
            findings.append(f"{ref}: the record returned no title — never cite a record that did not come back")
        if not link.strip():
            findings.append(f"{ref}: empty link")
        if stamp and not DATE_RE.match(stamp):
            findings.append(f"{ref}: paper_release_time_str must be YYYY-MM-DD or empty (got {stamp!r})")
        payload[ref] = {"title": title, "link": link, "paper_release_time_str": stamp}

    if cited is not None:
        unknown = sorted(cited - set(refs))
        if unknown:
            findings.append(f"the report cites refs absent from {args.refs}: {', '.join(unknown)}")
        unused = [ref for ref in keys if ref not in cited]
        if unused and args.keep_unused:
            print(f"WARN: keys never used by the report: {', '.join(unused)}", file=sys.stderr)
        elif unused:
            print(f"NOTE: dropped unused key(s) not cited by the report: {', '.join(unused)}", file=sys.stderr)

    if findings:
        print(f"FINDINGS ({len(findings)}) — nothing written:", file=sys.stderr)
        for item in findings:
            print(f"  - {item}", file=sys.stderr)
        return 3

    body = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.print_body:
        print(body)
    if args.check:
        print(f"OK (check only): {len(payload)} citation(s): {', '.join(payload)}")
        return 0
    try:
        _atomic_write(args.out, body + "\n")
    except OSError as exc:
        print(f"ERROR: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    print(f"WROTE {args.out}: {len(payload)} citation(s) [{', '.join(payload)}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
