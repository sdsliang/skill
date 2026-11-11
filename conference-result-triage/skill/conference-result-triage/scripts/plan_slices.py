#!/usr/bin/env python3
"""Cut the conference's id list into slices an agent can hand back to the tool.

Why this exists: the query tool caps a response at roughly 6 MB and ~500 rows, and it
answers a truncated call with ``ok: true`` -- so a single wide ``meeting_tags`` pull
returns a silently partial conference (observed: 458 of 1097 rows). The only exact way
in is the tool's ``esids`` filter, in slices small enough that 200 rows fit. An
id-only pull is ~50 KB for the whole conference, so stage 1 is always complete.

The output is deliberately dumb: one JSON array per file plus the array printed on
stdout, because the caller has to paste it into a tool argument by hand. Nothing here
sorts, filters or renames ids.

Usage
  python3 plan_slices.py --ids-from /workspace/tool_results --size 150 \\
      --out-dir /workspace/work/slices
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull_results import load_tool_result_rows  # noqa: E402


def ids_of(rows: List[Dict[str, Any]]) -> List[str]:
    """Take the row key, in the order returned; de-duplicate without re-sorting."""
    out: List[str] = []
    for row in rows:
        key = (row.get("clinical_result__id") or row.get("clinical_result_extra_esid")
               or row.get("_id") or row.get("extra_esid"))
        if key:
            out.append(str(key))
    return list(dict.fromkeys(out))


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids-from", nargs="+", required=True, metavar="PATH")
    ap.add_argument("--size", type=int, default=150)
    ap.add_argument("--out-dir", default="/workspace/work/slices")
    ap.add_argument("--quiet", action="store_true", help="write files, print only the plan")
    args = ap.parse_args(argv)

    ids = ids_of(load_tool_result_rows(args.ids_from))
    if not ids:
        print(f"no ids found under {args.ids_from} -- did the id-only pull run first?",
              file=sys.stderr)
        return 2

    os.makedirs(args.out_dir, exist_ok=True)
    all_path = os.path.join(args.out_dir, "_all_ids.txt")
    with open(all_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(ids) + "\n")

    slices = [ids[i:i + args.size] for i in range(0, len(ids), args.size)]
    print(f"ids={len(ids)} slices={len(slices)} size={args.size} -> {args.out_dir}")
    print(f"coverage file: {all_path}")
    for n, chunk in enumerate(slices, 1):
        path = os.path.join(args.out_dir, f"slice_{n:02d}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(chunk, fh)
        print(f"\n--- slice_{n:02d}.json ({len(chunk)} ids) ---")
        if not args.quiet:
            print(json.dumps(chunk))
    print("\nFor each slice call the tool with these two arguments:")
    print('  esids          = the array printed above')
    print('  selected_fields = `pull_results.py --list-fields`')
    print("Every call writes its own /workspace/tool_results/…jsonl; collect them all,")
    print("then run pull_results.py --from-tool-results … --expect-ids " + all_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
