#!/usr/bin/env python3
"""Pull every clinical-result row of one conference -> ``work/rows.json``.

This is the **only** data path the Skill is allowed to use. It calls the Tool Smith
data server through MCP (``query-clinical-result-with-params``) and never touches
Elasticsearch: the result table is not readable from the platform workspace and the
ES mirror (``np_clinical``) has no ``lba`` column, so an ES detour silently loses the
whole late-breaking tier -- that mistake cost v0.2 twelve missing headline readouts.

Two defects are hard-coded as defences because both fail *silently*:

1. ``clinical_result.lba`` must be in ``selected_fields``. It is a boolean marker
   (``"LBA"`` or null), carries no number, and is the only way to tell a late-breaking
   abstract from a poster once the row enters the pool. Omit it and 57 ESMO 2026
   headline rows come back looking like ordinary records.
2. The tool truncates the response body at roughly 6 MB. A 35-field, 1097-row call
   therefore returns ~500 rows with ``ok: true`` -- no error, no flag. Wide pulls must
   be sliced, so this script always does: ids first, then ``esids`` in batches.

Stage 1 asks for ``clinical_result__id`` only, which fits the whole conference in one
response; stage 2 re-queries those ids with the full field set in slices.

Usage (inside the platform workspace)
  python3 /workspace/skills/conference-result-triage/scripts/pull_results.py \
      --conference "ESMO 2026" --out /workspace/work/rows.json

Env
  MCP_PHARMCUBE_ENDPOINT_URL   in-cluster data server (has query-clinical-result-with-params)
  PHARMCUBE_MCP_APP_KEY        bearer token, when the server needs one
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import Mcp  # noqa: E402

TOOL_NEEDLE = "query-clinical-result"
SQL_TOOL_NEEDLE = "execute-sql"
DEFAULT_SLICE = 120

# Copy these names verbatim from the tool's own ``selected_fields`` description
# (ALLOWED_FIELD_NAMES runtime authority). A name that is merely similar is rejected
# with INVALID_INPUT, and a *missing* name is not rejected -- it is just absent, which
# is how ``lba`` went unnoticed in v0.2.
DEFAULT_FIELDS: List[str] = [
    "clinical_result.extra_esid",
    "clinical_result.lba",
    "clinical_result.paper_title",
    "clinical_result.journal",
    "clinical_result.paper_release_time",
    "clinical_result.abbreviation_label",
    "clinical_result.abstract_text",
    "clinical_result.summary",
    "clinical_result.key_evidence",
    "clinical_result.study_results",
    "clinical_result.evaluation",
    "clinical_result.evidence_source",
    "clinical_result.trial_abbreviation",
    "clinical_result.primary_endpoint_all_name",
    "clinical_result.primary_endpoint_en",
    "clinical_result.group_count",
    "clinical_result.projects",
    "clinical_result.indication_name",
    "clinical_result.indication_name_en",
    "clinical_result.therapy_line_en",
    "clinical_result.therapy_line_cn",
    "clinical_result.randomized",
    "clinical_result.random_ratio",
    "clinical_result.trial_control",
    "clinical_result.blinded",
    "clinical_result.multi_center",
    "clinical_result.clinical_stage_en",
    "clinical_result.clinical_stage_cn",
    "clinical_result.layer_factor",
    "clinical_result.full_article_link",
    "clinical_result.doi",
    "clinical_result.pm_id",
    "research_design.evaluation.text",
    "base.abbreviation_label.text",
]


def _rows_of(resp: Any) -> List[Dict[str, Any]]:
    """Unwrap the MCP envelope: ``{"ok":..,"data":[..]}`` or ``{"result":{...}}``."""
    if isinstance(resp, list):
        return resp
    if not isinstance(resp, dict):
        return []
    inner = resp.get("result") if isinstance(resp.get("result"), dict) else resp
    if inner.get("ok") is False:
        err = inner.get("error") or {}
        raise RuntimeError(f"tool error {err.get('code')}: {err.get('message')}")
    for key in ("data", "rows", "items", "list"):
        if isinstance(inner.get(key), list):
            return inner[key]
    return []


def pull(client: Mcp, tool: str, conference: str, fields: List[str],
         slice_size: int, timeout: int) -> Dict[str, Any]:
    # Stage 1: identifiers only. One field keeps the body small enough that the whole
    # conference arrives in a single response, so the id list is complete by
    # construction and the slice count is exact.
    id_resp = client.call(tool, {"meeting_tags": conference,
                                "selected_fields": ["clinical_result.extra_esid"]})
    ids: List[str] = []
    for row in _rows_of(id_resp):
        esid = (row.get("clinical_result__id") or row.get("clinical_result_extra_esid")
                or row.get("extra_esid"))
        if esid:
            ids.append(str(esid))
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise SystemExit(f"no rows for conference '{conference}' -- check the exact "
                         "meeting label (it maps to the tool's meeting_tags/journal filter)")

    # Stage 2: full fields, sliced. Never raise the slice to "just finish in one call":
    # above ~6 MB the tool returns a truncated page with ok: true.
    rows: List[Dict[str, Any]] = []
    seen = set()
    for start in range(0, len(ids), slice_size):
        chunk = ids[start:start + slice_size]
        resp = client.call(tool, {"esids": chunk, "selected_fields": fields})
        for row in _rows_of(resp):
            key = row.get("clinical_result__id") or json.dumps(row, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        print(f"  slice {start // slice_size + 1}: "
              f"{len(rows)}/{len(ids)} rows", file=sys.stderr)

    missing = [i for i in ids if i not in seen]
    return {"conference": conference, "requested": len(ids), "rows": rows,
            "missing": missing}


def pull_flags(client: Mcp, conference: str) -> Dict[str, Any]:
    """Fetch the curation flags that ``query-clinical-result-with-params`` cannot expose.

    ``clinical_result.featured`` (是/否) is **not** in the tool's selectable field
    whitelist, so a with-params pull silently returns rows without the key -- the
    same failure mode that lost ``lba`` in v0.2. It is the closest in-platform
    substitute for the abstract-number tier: on ESMO 2026 it marks 100 of 1100
    rows, and that slice is dominated by Presidential late-breaking readouts.

    ``TEST_execute-sql`` is used only for this narrow three-column sidecar. It is
    the platform's own SQL tool, not a direct Elasticsearch connection, and the
    payload is ~100 KB for a whole conference, so no truncation risk. The primary
    row data still comes through ``query-clinical-result-with-params``.
    """
    safe = conference.replace("'", "''")
    sql = ("SELECT extra_esid, featured, lba FROM clinical_trial_result_structured "
           f"WHERE journal = '{safe}'")
    resp = client.call(client.find_tool(SQL_TOOL_NEEDLE), {"sql": sql})
    rows = _rows_of(resp)
    flags = {}
    for row in rows:
        esid = row.get("extra_esid")
        if esid:
            flags[str(esid)] = {"featured": row.get("featured"), "lba": row.get("lba")}
    return flags


def _norm_esid(value: Any) -> str:
    """Strip the ``nr_`` prefix that the result table adds to ``np_result_conf`` rows.

    The same record is keyed ``24_37_p_<hash>_1`` in ``clinical_trial_result_structured``
    but ``nr_24_37_p_<hash>_1`` in the ``with-params`` payload (~100 of ESMO 2026's
    1100 rows, exactly the ``source='np_result_conf'`` slice). Without normalising,
    those 97 rows silently get ``featured=null`` and drop out of the headline tier --
    a full 100% of the sidecar matches only after the prefix is stripped.
    """
    s = str(value or "")
    return s[3:] if s.startswith("nr_") else s


def merge_flags(rows: List[Dict[str, Any]], flags: Dict[str, Any]) -> int:
    """Attach ``clinical_result_featured`` to each row; return how many matched."""
    index = {_norm_esid(k): v for k, v in flags.items()}
    hit = 0
    for row in rows:
        esid = row.get("clinical_result__id") or row.get("clinical_result_extra_esid") or ""
        f = index.get(_norm_esid(esid))
        if not f:
            continue
        hit += 1
        row["clinical_result_featured"] = f.get("featured")
        # The sidecar carries `lba` too; use it as a cross-check, never to overwrite
        # the value from the primary pull (with-params is authoritative for fields
        # it *does* expose).
        if f.get("lba") and not row.get("clinical_result_lba"):
            row["clinical_result_lba"] = f.get("lba")
    return hit


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conference", required=True, help='e.g. "ESMO 2026"')
    ap.add_argument("--out", default="/workspace/work/rows.json")
    ap.add_argument("--endpoint", default=None, help="override MCP_PHARMCUBE_ENDPOINT_URL")
    ap.add_argument("--tool", default=None, help="override the discovered tool name")
    ap.add_argument("--fields", nargs="*", default=None, help="replace the field list")
    ap.add_argument("--extra", nargs="*", default=[], help="append fields")
    ap.add_argument("--slice-size", type=int, default=DEFAULT_SLICE)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--list-fields", action="store_true")
    ap.add_argument("--no-flags", action="store_true",
                    help="skip the featured/lba SQL sidecar")
    args = ap.parse_args(argv)

    fields = (args.fields or DEFAULT_FIELDS) + list(args.extra or [])
    if args.list_fields:
        for name in fields:
            print(name)
        return 0

    client = Mcp(url=args.endpoint, timeout=args.timeout)
    tool = args.tool or client.find_tool(TOOL_NEEDLE)
    print(f"tool={tool} endpoint={client.url}", file=sys.stderr)
    payload = pull(client, tool, args.conference, fields, args.slice_size, args.timeout)

    featured = 0
    if not args.no_flags:
        try:
            flags = pull_flags(client, args.conference)
            matched = merge_flags(payload["rows"], flags)
            featured = sum(1 for r in payload["rows"]
                           if str(r.get("clinical_result_featured") or "").strip() == "是")
            print(f"flags: sidecar={len(flags)} matched={matched} featured={featured}",
                  file=sys.stderr)
            if matched == 0:
                print("WARNING: featured sidecar matched 0 rows -- the esid keys differ "
                      "between SQL and with-params; cards will render featured=false",
                      file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - sidecar is an enhancement, not a gate
            print(f"WARNING: featured sidecar unavailable ({exc}); continuing without it",
                  file=sys.stderr)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)

    lba = sum(1 for r in payload["rows"] if r.get("clinical_result_lba"))
    with_abs = sum(1 for r in payload["rows"] if r.get("clinical_result_abstract_text"))
    print(f"rows={len(payload['rows'])} requested={payload['requested']} "
          f"missing={len(payload['missing'])} lba={lba} featured={featured} "
          f"with_abstract_text={with_abs} -> {args.out}")
    if payload["missing"]:
        print(f"WARNING: {len(payload['missing'])} ids returned no row; "
              "re-run those ids in one further call before building the pool",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
