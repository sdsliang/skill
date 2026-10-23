#!/usr/bin/env python3
"""Build an asset history table: how the same drug read out at earlier meetings.

The single most common expert remark on a conference shortlist is not "this ORR
is high" but "this is 45.7% versus 56.8% at ASCO six months ago". A single
conference snapshot cannot answer that, so this script pulls every meeting
record for the drugs already shortlisted and prints the readout over time.

Note this is a *lookup*, not a judgement: it lists what the drug's earlier
abstracts printed. Deciding whether the delta is dilution from a broader
population, a weaker dose, or genuine loss of activity stays with the reviewer.

Usage
  python3 history_for.py --drugs SYS6043,HS-20122 --out history.md
  python3 history_for.py --pool pool.json --top 10 --out history.md
  python3 history_for.py --csv watchlist.csv --out history.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import meeting_pull  # noqa: E402
from triage import split_sections  # noqa: E402

ORR_RE = re.compile(
    r"(?:objective response rate|overall response rate|\bORR\b|客观缓解率|总缓解率)"
    r"[^.%\n]{0,60}?(\d{1,3}(?:\.\d+)?)\s*%", re.I)
PFS_RE = re.compile(r"(?:median\s+)?(?:progression-free survival|\bPFS\b|无进展生存)"
                    r"[^.\n]{0,60}?(\d{1,2}(?:\.\d+)?)\s*(?:months|个月)", re.I)
OS_RE = re.compile(r"(?:median\s+)?(?:overall survival|\bOS\b|总生存)"
                   r"[^.\n]{0,60}?(\d{1,2}(?:\.\d+)?)\s*(?:months|个月)", re.I)
N_RE = re.compile(r"\b(\d{1,4})\s+(?:patients|pts|participants)\b", re.I)


def extract(text: str) -> Dict[str, Any]:
    sections, _ = split_sections(text or "")
    results = sections.get("results") or ""
    blob = results or (text or "")
    out: Dict[str, Any] = {}
    for key, rx in (("orr", ORR_RE), ("pfs", PFS_RE), ("os", OS_RE)):
        m = rx.search(blob)
        if m:
            out[key] = m.group(1)
    m = N_RE.search(blob) or N_RE.search(text or "")
    if m:
        out["n"] = m.group(1)
    return out


def fetch(drug: str, key: str) -> List[Dict[str, Any]]:
    try:
        first = meeting_pull.pull_page((key, "", 0, {"drugName": drug}))
    except Exception as exc:  # noqa: BLE001 - a miss must not kill the batch
        print(f"  ! {drug}: {exc}", file=sys.stderr)
        return []
    total = int(first.get("total") or 0)
    page_size = int(first.get("pageSize") or meeting_pull.PAGE_SIZE)
    recs = list(first.get("data") or [])
    pages = (total + page_size - 1) // page_size
    for page_no in range(1, min(pages, 3)):
        try:
            recs += list(meeting_pull.pull_page((key, "", page_no, {"drugName": drug}))
                         .get("data") or [])
        except Exception:  # noqa: BLE001
            break
    out = []
    for rec in recs:
        if not rec.get("abstract_text"):
            continue
        nums = extract(rec["abstract_text"])
        out.append({
            "drug": drug,
            "conference": rec.get("conference") or "-",
            "abstract_id": rec.get("abstract_id") or "-",
            "date": (rec.get("meeting_date") or rec.get("abstract_release_date") or "")[:10],
            "title": (rec.get("title") or "").strip(),
            **nums,
        })
    out.sort(key=lambda r: r["date"])
    return out


def drugs_from_pool(path: str, top: int) -> List[str]:
    with open(path, "r", encoding="utf-8") as fh:
        pool = json.load(fh)
    seen: List[str] = []
    for bucket in ("early", "pivotal", "failed"):
        for item in pool["pools"][bucket]["items"][:top]:
            raw = item.get("drug") or ""
            for part in re.split(r"[,;，、]", raw):
                part = part.strip()
                if part and part not in seen and len(part) > 2:
                    seen.append(part)
    return seen


def drugs_from_csv(path: str) -> List[str]:
    seen: List[str] = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            for part in re.split(r"[,;，、/]", row.get("drug") or ""):
                part = part.strip()
                if part and part not in seen and len(part) > 2:
                    seen.append(part)
    return seen


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drugs", help="comma separated drug names")
    ap.add_argument("--pool", help="pool.json from triage.py (uses the drug column)")
    ap.add_argument("--csv", help="watchlist CSV (uses the drug column)")
    ap.add_argument("--top", type=int, default=10, help="per bucket when --pool is used")
    ap.add_argument("--out", default="history.md")
    args = ap.parse_args(argv)

    if args.drugs:
        drugs = [d.strip() for d in args.drugs.split(",") if d.strip()]
    elif args.pool:
        drugs = drugs_from_pool(args.pool, args.top)
    elif args.csv:
        drugs = drugs_from_csv(args.csv)
    else:
        ap.error("give --drugs, --pool or --csv")
    drugs = drugs[:40]

    key = meeting_pull.app_key()
    rows: List[Dict[str, Any]] = []
    for drug in drugs:
        got = fetch(drug, key)
        print(f"{drug}: {len(got)} meeting records", file=sys.stderr)
        rows += got

    rows.sort(key=lambda r: (r["drug"], r["date"]))
    lines = ["# 同资产历次会议数据对照", "",
             "> 由 `history_for.py` 自动生成；只列摘要里印出来的数字，不做判断。",
             "> 样本量变小、剂量不同、人群放宽都会改变对比结论，**必须结合正文阅读**。",
             "> n 与 ORR 取的是 Results 段里**最先出现**的那一组数字，通常是总样本或首个亚组，"
             "不等于全文唯一口径；引用前必须回正文核对。", "",
             "| 药物 | 会议 | 摘要号 | 日期 | n | ORR | mPFS | mOS | 标题 |",
             "|---|---|---|---|---|---|---|---|---|"]
    if not rows:
        lines.append("| （无记录） | | | | | | | | |")
    for r in rows:
        lines.append("| {drug} | {conference} | {abstract_id} | {date} | {n} | {orr} | {pfs} | {os} | {title} |".format(
            drug=r["drug"], conference=r["conference"], abstract_id=r["abstract_id"],
            date=r["date"] or "-", n=r.get("n") or "-",
            orr=(r["orr"] + "%") if r.get("orr") else "-",
            pfs=(r["pfs"] + " mo") if r.get("pfs") else "-",
            os=(r["os"] + " mo") if r.get("os") else "-",
            title=r["title"][:70].replace("|", "/")))

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {args.out}: {len(rows)} records for {len(drugs)} drugs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
