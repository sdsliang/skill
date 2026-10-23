#!/usr/bin/env python3
"""Pull the conference abstract book (medicalMeeting) into a local JSON file.

Why this exists
---------------
``CLINICAL_TRIAL_RESULT_STRUCTURED`` only contains records that already passed
the curation pipeline. Anything brand new -- a first-in-human readout released
days before the meeting -- may not be there yet. On ESMO 2026 that gap was
demonstrated by BG-C477 (abstract 2567P, 43 NSCLC pts, ORR 34.9%): present in
the meeting book, absent from the structured result table.

This script talks to the Pharmcube MCP endpoint directly (streamable HTTP,
Bearer appkey) and pages through ``medicalMeeting`` for one conference.

Two things the meeting book adds that the structured table does not have:
  * ``abstract_id`` -- whose suffix (``O`` / ``RO`` / ``P``) is the presentation
    tier, the strongest single prior available for "is this a headline?";
  * ``target`` / ``drug`` / ``moa`` -- standardised, so target scarcity can be
    counted instead of guessed.

Usage
  python3 meeting_pull.py --conference "ESMO 2026" --out mm.json
  python3 meeting_pull.py --conference "ESMO 2026" --out mm.json --max-pages 5
  python3 meeting_pull.py --abstract-id 2567P --conference "ESMO 2026"

Env
  PHARMCUBE_MCP_APP_KEY   overrides ~/.pi/agent/pharmcube-mcp-appkey
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

MCP_URL = "https://mcp-openapi.pharmcube.com/mcp"
SECRET_FILE = os.path.expanduser("~/.pi/agent/pharmcube-mcp-appkey")
TOOL = "pharmcube-mcp-medicalMeeting"
PAGE_SIZE = 20

FIELDS_KEPT = (
    "abstract_id", "title", "conference", "research_theme", "abstract_text",
    "abstract_release_date", "meeting_date", "url",
    "drug", "drug_type_1", "drug_type_2", "drug_tag", "drug_name_original",
    "target", "target_name_original", "moa", "moa_en", "moa_name_original",
    "disease", "disease_en", "disease_area", "disease_name_original",
    "source_id", "job_update_time",
)


def app_key() -> str:
    key = (os.environ.get("PHARMCUBE_MCP_APP_KEY") or "").strip()
    if key:
        return key
    try:
        with open(SECRET_FILE, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


class Mcp:
    """Minimal MCP streamable-HTTP client: initialize once, then tools/call."""

    def __init__(self, key: Optional[str] = None, timeout: int = 90):
        self.key = key or app_key()
        if not self.key:
            raise SystemExit(
                "no MCP appkey: set PHARMCUBE_MCP_APP_KEY or write "
                + SECRET_FILE)
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self._id = 0

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(MCP_URL, data=body, method="POST")
        req.add_header("Authorization", "Bearer " + self.key)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.session_id:
            req.add_header("mcp-session-id", self.session_id)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            self.session_id = resp.headers.get("mcp-session-id") or self.session_id
            raw = resp.read().decode("utf-8", "replace")
        return _parse_body(raw)

    def init(self) -> None:
        if self.session_id:
            return
        self._id += 1
        self._post({
            "jsonrpc": "2.0", "id": self._id, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "conference-result-triage", "version": "0.2"},
            },
        })

    def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.init()
        self._id += 1
        out = self._post({
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        if "error" in out:
            raise RuntimeError(f"MCP error: {out['error']}")
        content = (out.get("result") or {}).get("content") or []
        for part in content:
            if part.get("type") == "text":
                return json.loads(part["text"])
        return {}


def _parse_body(raw: str) -> Dict[str, Any]:
    """MCP may answer with plain JSON or an SSE stream; accept both."""
    text = raw.strip()
    if not text:
        return {}
    if text.startswith("{"):
        return json.loads(text)
    data_lines = [ln[5:].strip() for ln in text.splitlines() if ln.startswith("data:")]
    for chunk in reversed(data_lines):
        if chunk and chunk.startswith("{"):
            return json.loads(chunk)
    raise RuntimeError("unparseable MCP response: " + text[:200])


def keep(rec: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: rec.get(k) for k in FIELDS_KEPT if rec.get(k) not in (None, "", [])}
    if not out.get("abstract_id"):
        out["abstract_id"] = None
    return out


def pull_page(args_tuple) -> Dict[str, Any]:
    key, conference, page_no, extra = args_tuple
    cli = Mcp(key)
    arguments: Dict[str, Any] = {"pageNo": page_no}
    if conference:
        arguments["conference"] = conference
    arguments.update(extra)
    last: Optional[Exception] = None
    for attempt in range(3):
        try:
            return cli.call(TOOL, arguments)
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"page {page_no} failed: {last}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conference", default="ESMO 2026",
                    help='"" or "-" searches every conference (use with --drug '
                         'to build an asset history)')
    ap.add_argument("--abstract-id")
    ap.add_argument("--drug")
    ap.add_argument("--target")
    ap.add_argument("--disease")
    ap.add_argument("--out", default="meeting.json")
    ap.add_argument("--max-pages", type=int, default=0, help="0 = all pages")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args(argv)

    key = app_key()
    if args.conference in ("", "-"):
        args.conference = ""
    extra: Dict[str, Any] = {}
    if args.abstract_id:
        extra["abstractId"] = args.abstract_id
    if args.drug:
        extra["drugName"] = args.drug
    if args.target:
        extra["target"] = args.target
    if args.disease:
        extra["disease"] = args.disease

    first = pull_page((key, args.conference, 0, extra))
    total = int(first.get("total") or 0)
    page_size = int(first.get("pageSize") or PAGE_SIZE)

    records: List[Dict[str, Any]] = [keep(r) for r in first.get("data") or []]
    pages = (total + page_size - 1) // page_size
    if args.max_pages:
        pages = min(pages, args.max_pages)

    scope = args.conference or "all conferences"
    print(f"{scope}: total {total}, {page_size}/page -> {pages} pages", flush=True)
    seen = {(r.get("source_id") or "") + "|" + (r.get("abstract_id") or "") for r in records}

    if pages > 1:
        jobs = [(key, args.conference, p, extra) for p in range(1, pages)]
        done = 0
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            for page in pool.map(pull_page, jobs):
                done += 1
                for rec in page.get("data") or []:
                    k = keep(rec)
                    sig = (k.get("source_id") or "") + "|" + (k.get("abstract_id") or "")
                    if sig not in seen:
                        seen.add(sig)
                        records.append(k)
                if done % 20 == 0:
                    print(f"  {done}/{len(jobs)} pages, {len(records)} records", flush=True)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"conference": args.conference, "total": total,
                   "fetched": len(records), "data": records},
                  fh, ensure_ascii=False, indent=1)

    with_id = sum(1 for r in records if r.get("abstract_id"))
    with_text = sum(1 for r in records if r.get("abstract_text"))
    print(f"wrote {args.out}: {len(records)} records "
          f"({with_id} with abstract_id, {with_text} with abstract_text)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
