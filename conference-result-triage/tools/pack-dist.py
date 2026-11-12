#!/usr/bin/env python3
"""Deterministic dist packer for the conference-result-triage skill.

Byte-stable for an unchanged worktree, so ``toolsmith-publish status`` can compare the
deployed zip against this output by member and by bytes.

Contract
  - entries: SKILL.md + references/*.md + templates/*.md + scripts/*.py
  - arcname prefix ``conference-result-triage/`` (what the platform unpacks under
    /workspace/skills/, so every path in SKILL.md starts with that name)
  - fixed date_time stamp, 0644, deflate level 6
  - hard checks: no __pycache__, no .pyc, no dotfiles, at least one script and one
    reference present (a package that ships without either is broken by construction)

Usage
  tools/pack-dist.py           # build dist/conference-result-triage-v0.4.zip
  tools/pack-dist.py --check   # rebuild in memory, compare with the dist file
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "skill", "conference-result-triage")
VERSION = "v0.7"
NAME = "conference-result-triage"
OUT = os.path.join(REPO, "dist", f"{NAME}-{VERSION}.zip")
PREFIX = NAME + "/"
STAMP = (2026, 11, 11, 0, 0, 0)
COMPRESS_LEVEL = 6
FORBIDDEN = ("__pycache__", ".pyc", ".DS_Store", ".git")


def collect() -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    fixed = ["SKILL.md"]
    trees = [("references", ".md"), ("templates", ".md"), ("scripts", ".py")]
    rels = list(fixed)
    for sub, ext in trees:
        d = os.path.join(SRC, sub)
        if not os.path.isdir(d):
            raise SystemExit(f"missing directory: {d}")
        for fn in sorted(os.listdir(d)):
            if fn.endswith(ext):
                rels.append(f"{sub}/{fn}")
    for rel in rels:
        path = os.path.join(SRC, rel)
        if not os.path.isfile(path):
            raise SystemExit(f"missing file: {path}")
        if any(bad in rel for bad in FORBIDDEN):
            raise SystemExit(f"forbidden artifact in package: {rel}")
        with open(path, "rb") as fh:
            entries.append((PREFIX + rel, fh.read()))
    names = [n for n, _ in entries]
    if not any(n.startswith(PREFIX + "references/") for n in names):
        raise SystemExit("package has no references/ — the SKILL reads them at runtime")
    if not any(n.startswith(PREFIX + "scripts/") for n in names):
        raise SystemExit("package has no scripts/ — the SKILL calls them at runtime")
    return entries


def build(entries: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=COMPRESS_LEVEL) as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=STAMP)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="compare the rebuild with the dist file instead of writing")
    args = ap.parse_args(argv)

    entries = collect()
    blob = build(entries)
    digest = hashlib.sha256(blob).hexdigest()
    if args.check:
        if not os.path.exists(OUT):
            print(f"MISSING {OUT}")
            return 3
        current = open(OUT, "rb").read()
        if current == blob:
            print(f"OK {len(entries)} entries, sha256={digest[:16]}")
            return 0
        print(f"DRIFT {OUT} sha256={hashlib.sha256(current).hexdigest()[:16]} "
              f"!= rebuild {digest[:16]}")
        return 3

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as fh:
        fh.write(blob)
    print(f"wrote {OUT} ({len(blob)} B, {len(entries)} entries, sha256={digest[:16]})")
    for name, data in entries:
        print(f"  {len(data):>7}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
