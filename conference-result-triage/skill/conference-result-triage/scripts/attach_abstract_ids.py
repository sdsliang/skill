#!/usr/bin/env python3
"""Attach conference abstract numbers to pool items.

The TS result table exposes ``lba`` as a boolean flag but **no abstract number**
(``abstract_id`` lives only in the meeting book). Without the number a card can
say "late-breaking" but not "LBA3", and ``presentation_of`` cannot decode the
slot at all.

So: pull the meeting book once (``scripts/meeting_pull.py``), then join it onto
the pool by normalized title. This script only *labels* rows -- it never adds,
removes or re-ranks a candidate, and the meeting book is not a data source for
results.

    python3 scripts/attach_abstract_ids.py \
        --pool pool.json --meeting mm.json --out pool_labeled.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from triage import BUCKETS, presentation_of  # noqa: E402


def norm_title(text: Any) -> str:
    """NFKD + lowercase + non-alnum -> space. Same key the join step uses."""
    s = unicodedata.normalize("NFKD", str(text or "")).lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def load_book(path: str) -> Dict[str, str]:
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("data") or data.get("rows") or []
    book: Dict[str, str] = {}
    for row in data:
        aid = (row.get("abstract_id") or "").strip()
        title = row.get("title")
        if aid and title:
            book.setdefault(norm_title(title), aid)
    return book


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--meeting", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    book = load_book(args.meeting)
    pool = json.load(open(args.pool, encoding="utf-8"))
    attached = already = missing = 0
    misses: List[str] = []
    for bucket in BUCKETS:
        for item in pool["pools"][bucket]["items"]:
            if item.get("abstract_id"):
                already += 1
            else:
                aid = book.get(norm_title(item.get("title")))
                if aid:
                    item["abstract_id"] = aid
                    attached += 1
                else:
                    missing += 1
                    misses.append((item.get("trial") or "")[:40] or str(item.get("esid")))
            label, rank = presentation_of(item.get("abstract_id"), bool(item.get("lba")))
            item["presentation"], item["presentation_rank"] = label, rank

    total = sum(pool["pools"][b]["count"] for b in BUCKETS)
    lba_ids = sum(1 for b in BUCKETS for i in pool["pools"][b]["items"]
                  if str(i.get("abstract_id") or "").upper().startswith("LBA"))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(pool, fh, ensure_ascii=False, indent=1)
    print(f"items {total}: attached {attached}, already {already}, missing {missing}")
    print(f"lba rows carrying an LBA number: {lba_ids}")
    if misses:
        print("unmatched (first 10): " + " | ".join(misses[:10]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
