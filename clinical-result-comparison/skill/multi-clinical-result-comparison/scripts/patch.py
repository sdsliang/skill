#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Make one asserted, atomic, whole-file text patch — the supported way to fix a draft.

Use this instead of hand-writing a one-off helper script for every small edit, and instead of
re-issuing a whole file through `write_file` when only a phrase changed.  It is deliberately
strict: the number of matches must be exactly what you declared *before* anything is written,
so a stale or over-broad pattern fails loudly instead of silently editing the wrong place.

    python3 /workspace/skills/multi-clinical-result-comparison/scripts/patch.py work/draft.md --find '每月' --replace '每月一次' --count 4
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/patch.py /workspace/output/report.md --find-file /tmp/old.txt \
        --replace-file /tmp/new.txt
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/patch.py /workspace/output/report.md --find '未评估该终点' --count 0  # assert absent
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/patch.py /workspace/output/report.md --find '## 三' --replace '## 三' \
        --insert-after --replace-file /tmp/section.md
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/patch.py /workspace/output/report.md --find 'Q4W' --replace '每 12 周' --dry-run

`--count 0` asserts the text is **absent** (nothing is written).  `--insert-after` inserts
`--replace` immediately after the match instead of replacing it.  `--unescape` turns `\\n`,
`\\t` and `\\\\` in `--find`/`--replace` into real characters, so multi-line patches stay on one
command line.  Writes go to a temporary file in the same directory and are moved into place
atomically: a failed assertion, or a crash, leaves the original file untouched.

Exit codes: 0 patched; 3 match count differs from `--count` (nothing written); 2 usage / IO.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _unescape(value: str) -> str:
    return value.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def _payload(direct: str | None, from_file: Path | None, unescape: bool, label: str) -> str:
    if direct is not None and from_file is not None:
        raise SystemExit(f"ERROR: give either --{label} or --{label}-file, not both")
    if from_file is not None:
        text = Path(from_file).read_text(encoding="utf-8")
        return _unescape(text) if unescape else text
    if direct is None:
        raise SystemExit(f"ERROR: --{label} or --{label}-file is required")
    return _unescape(direct) if unescape else direct


def _context(text: str, needle: str, limit: int = 3) -> list[str]:
    out: list[str] = []
    start = 0
    while len(out) < limit:
        index = text.find(needle, start)
        if index < 0:
            break
        line = text.count("\n", 0, index) + 1
        snippet = text[max(0, index - 30): index + len(needle) + 30].replace("\n", "⏎")
        out.append(f"line {line}: …{snippet}…")
        start = index + len(needle)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Asserted, atomic, whole-file find/replace (default: exactly one match).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", type=Path, help="file to patch in place")
    parser.add_argument("--find")
    parser.add_argument("--find-file", type=Path)
    parser.add_argument("--replace")
    parser.add_argument("--replace-file", type=Path)
    parser.add_argument("--delete", action="store_true", help="shortcut for --replace ''")
    parser.add_argument("--count", type=int, default=1, help="required number of matches (default 1; 0 = must be absent)")
    parser.add_argument("--insert-after", action="store_true", help="insert --replace after the match")
    parser.add_argument("--unescape", action="store_true", help=r"turn \\n / \\t / \\\\ into real characters")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--encoding", default="utf-8")
    args = parser.parse_args(argv)

    path: Path = args.file
    if not path.is_file():
        print(f"ERROR: {path} is not a file", file=sys.stderr)
        return 2
    try:
        find = _payload(args.find, args.find_file, args.unescape, "find")
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.delete or args.count == 0:
        replace = ""
    else:
        try:
            replace = _payload(args.replace, args.replace_file, args.unescape, "replace")
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if not find:
        print("ERROR: --find must not be empty", file=sys.stderr)
        return 2
    if args.count < 0:
        print("ERROR: --count must be >= 0", file=sys.stderr)
        return 2

    try:
        text = path.read_text(encoding=args.encoding)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 2

    found = text.count(find)
    if found != args.count:
        print(f"ASSERT FAILED: {path} contains {found} occurrence(s) of the pattern, wanted {args.count}",
              file=sys.stderr)
        for line in _context(text, find):
            print(f"  {line}", file=sys.stderr)
        print("  nothing written", file=sys.stderr)
        return 3

    if args.count == 0:
        print(json.dumps({"file": str(path), "matches": 0, "changed": False}, ensure_ascii=False))
        return 0

    if args.insert_after:
        updated = text.replace(find, find + replace)
    else:
        updated = text.replace(find, replace)

    summary = {
        "file": str(path),
        "matches": found,
        "insert_after": bool(args.insert_after),
        "bytes_before": len(text.encode(args.encoding)),
        "bytes_after": len(updated.encode(args.encoding)),
        "dry_run": bool(args.dry_run),
    }
    if args.dry_run or updated == text:
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding=args.encoding, newline="\n") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o7777)
        os.replace(temporary, path)
    except Exception as exc:                                    # noqa: BLE001
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        print(f"ERROR: could not write {path}: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
