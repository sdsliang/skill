#!/usr/bin/env python3
"""Deterministic dist packer for the multi-clinical-result-comparison skill.

Moved into the repo on 2026-09-18 (it used to live in `/tmp` as `pack15b.py`, and got
wiped once — a packaging step that decides what reaches the platform cannot live in
scratch space).

Contract (byte-stable for an unchanged worktree — `toolsmith-publish status` compares the
deployed zip against this output by member and by bytes):
  - 20 entries: SKILL.md + references/*.md + templates/*.md + templates/charts/*.json + scripts/*.py
  - arcname prefix `multi-clinical-result-comparison/`
  - fixed date_time stamp, Unix creator, 0644 external_attr, deflate level 6
  - hard checks (also under python -O): exact entry count, no cache/metadata leakage

Level 6 preserves the existing archives: passing a ZipInfo to writestr previously
ignored the archive's level=9 setting and used zlib's default (6). Byte identity is
expected within the same Python/zlib implementation; cross-zlib identity is not promised.

Usage
-----
    tools/pack-dist.py                # build dist/multi-clinical-result-comparison-v0.15.zip
    tools/pack-dist.py --check        # rebuild in memory and compare with the dist file (no write)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
from pathlib import Path
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "skill", "multi-clinical-result-comparison")
VERSION = "v0.15"
OUT = os.path.join(REPO, "dist", f"multi-clinical-result-comparison-{VERSION}.zip")
PREFIX = "multi-clinical-result-comparison/"
STAMP = (2026, 9, 10, 0, 0, 0)
EXPECTED = 20
COMPRESS_LEVEL = 6


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def source_file(path: str) -> None:
    root = Path(SRC).resolve()
    target = Path(path).resolve()
    require(target.is_relative_to(root) and target.is_file(),
            f"missing or outside source tree: {path}")


def collect() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    skill_md = os.path.join(SRC, "SKILL.md")
    source_file(skill_md)
    entries.append(("SKILL.md", skill_md))
    for sub, exts in (("references", (".md",)), ("templates/charts", (".json",)), ("templates", (".md",)), ("scripts", (".py",))):
        base = os.path.join(SRC, sub)
        rels = sorted(f"{sub}/{n}" for n in os.listdir(base) if n.endswith(exts))
        for rel in rels:
            path = os.path.join(SRC, rel)
            source_file(path)
            entries.append((rel, path))
    return entries


def build() -> bytes:
    entries = collect()
    require(len(entries) == EXPECTED,
            f"expected {EXPECTED} entries, got {len(entries)}: {[e[0] for e in entries]}")
    rels = [r for r, _ in entries]
    for bad in ("__pycache__", ".pyc", "system-prompts", "docs/", "vendor/", "README.md", "PROJECT_STATE"):
        hit = [r for r in rels if bad in r]
        require(not hit, f"forbidden member {bad!r}: {hit}")
    require(len(set(rels)) == len(rels), "duplicate members")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=COMPRESS_LEVEL) as z:
        for rel, path in entries:
            info = zipfile.ZipInfo(PREFIX + rel, date_time=STAMP)
            info.create_system = 3
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as fh:
                z.writestr(info, fh.read(), compresslevel=COMPRESS_LEVEL)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="compare a fresh build against the dist file, write nothing")
    args = ap.parse_args()

    try:
        data = build()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"pack-dist: {exc}", file=sys.stderr)
        return 2
    sha = hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = len(archive.namelist())

    if args.check:
        if not os.path.isfile(OUT):
            print(f"MISSING {OUT}")
            return 3
        with open(OUT, "rb") as fh:
            cur = fh.read()
        same = cur == data
        print(f"{os.path.basename(OUT)}: {'IDENTICAL' if same else 'DIFFERS'} "
              f"({len(cur)} B / sha {hashlib.sha256(cur).hexdigest()[:12]} vs rebuilt {len(data)} B / sha {sha[:12]})")
        return 0 if same else 3

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as fh:
        fh.write(data)
    print(f"{OUT}\n  {len(data)} B / {entries} entries\n  sha256 {sha}")
    for rel, _ in collect():
        print(f"    {PREFIX}{rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
