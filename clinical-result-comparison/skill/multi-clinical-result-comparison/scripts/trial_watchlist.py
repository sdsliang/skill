#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn one `pharmcube-query-clinical-trial-with-params-v2` pull into a bounded watchlist.

The module answers a question the result records cannot: **what is still running in the same class and
has not read out yet.** Its output is registry facts only — it is never evidence in the comparison.

Everything mechanical happens here, for three reasons the probes made concrete (2026-10-22):

* a single registry id came back as **630 rows**, because the payload expands one row per
  drug x endpoint x registry x timeline combination. Row counts therefore say nothing about how many
  trials matched, and a report must never claim "N trials in the class";
* the filters that should have bounded the pull are unusable: `trial_has_result` rejects booleans
  (`Input should be a valid boolean`) and returns nothing for `false` / `true` / `"否"` / `"是"`, and
  `trial_therapy_line` returns nothing for `一线` / `一线治疗`. Both are applied **locally** instead;
* `drug_is_primary: true` also returns nothing, so it is not used at all.

Usage
-----
    # select (writes work/watchlist.json, appends the refs the report will cite)
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/trial_watchlist.py \
        --result tool_results/pharmcube-query-clinical-trial-with-params-v2/call_x.jsonl \
        --phase "Phase III" --exclude-nct NCT05611671 --append

    # the lookup ran but nothing qualified
    python3 .../trial_watchlist.py --none-found --result <pull>

    # the lookup does not apply here
    python3 .../trial_watchlist.py --not-applicable --reason "所选集合本身即为唯一在研资产"

Exit codes: 0 wrote a selection or recorded a state; 3 nothing qualified while `--append` was asked
(nothing to cite); 2 usage / input error.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prep_sources as ps  # noqa: E402  (same package: it owns the refs.json invariants)

ONGOING_STATUSES = ("招募中", "尚未招募", "完成招募")
RESULT_YES = "是"
STATES = ("listed", "none_alignable", "not_applicable")
DEFAULT_LIMIT = 5
# One trial arrives once per registry x drug x endpoint combination, so a single NCT id can come back
# as several hundred rows. The link the report cites must therefore be chosen deterministically:
# clinicaltrials.gov first, then the other public registries.
REGISTRY_PREFERENCE = ("US-ClinicalTrial", "EU-EUCT", "CN-CDE", "JP-JRCT", "IN-CTRI")
# `nct_ids` mixes real registry ids with development aliases (`TOPAZ-UC`, `J6E-MC-KWAN`).
REGISTRY_ID_RE = re.compile(
    r"^(?:NCT\d{6,}|CTR\d{4,}|EUCT[\d-]+|jRCT[\w-]+|CTRI/[\d/]+|U1111-[\w-]+|ChiCTR[\w-]+|"
    r"ISRCTN\d+|DRKS\d+|ACTRN[\w.]+)$", re.IGNORECASE)

# The fields the watchlist needs, and the whole of what it asks the tool for. Keep this list flat and
# trial-level where possible: every sub-entity field adds a cross-product dimension to the payload.
SELECTED_FIELDS = (
    "main_trial.nct_ids",
    "main_trial.trial_id",
    "main_trial.trial_title_zh",
    "main_trial.trial_phase",
    "main_trial.trial_status",
    "main_trial.trial_has_result",
    "main_trial.trial_indication_names_zh",
    "main_trial.trial_enrollment_estimated_global",
    "main_trial.trial_first_post_date",
    "main_trial_sub_drug.drug_name_zh",
    "main_trial_sub_drug.drug_company_names_zh",
    "main_trial_sub_registry.registry_id",
    "main_trial_sub_registry.registry_url",
)


def state_path(args) -> Path:
    return args.watchlist_state or (args.refs.parent / "watchlist.json")


def _records(path: Path) -> list[dict]:
    """Read one tool-result .jsonl; every line is a record (or a container holding them)."""
    out: list[dict] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                nested = None
                for key in ps.LIST_CONTAINERS:
                    if isinstance(payload.get(key), list):
                        nested = payload[key]
                        break
                if nested is not None:
                    out.extend(item for item in nested if isinstance(item, dict))
                else:
                    out.append(payload)
            elif isinstance(payload, list):
                out.extend(item for item in payload if isinstance(item, dict))
    return out


def _values(record: dict, *keys: str) -> list[str]:
    for key in keys:
        raw = record.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            if raw.strip():
                return [raw.strip()]
            continue
        if isinstance(raw, list):
            found = [str(item).strip() for item in raw if str(item).strip()]
            if found:
                return found
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return [str(raw)]
    return []


def _text(record: dict, *keys: str) -> str:
    values = _values(record, *keys)
    return values[0] if values else ""


def _date(value) -> str:
    """The payload mixes epoch millis and `YYYY-MM-DD HH:MM:SS`; return `YYYY-MM-DD` only.

    Timestamps are rendered in Beijing time: the registries record dates as local midnights, and a UTC
    rendering would date every Chinese registration one day early.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return _dt.datetime.fromtimestamp(value / 1000.0, _dt.timezone(_dt.timedelta(hours=8))).strftime("%Y-%m-%d")
        except (OverflowError, OSError, ValueError):
            return ""
    return ps._date_only(str(value or ""))


def _split_ids(values: list[str]) -> tuple[list[str], list[str]]:
    """Separate real registry ids from development aliases (`TOPAZ-UC`, `J6E-MC-KWAN`)."""
    real = [item for item in values if REGISTRY_ID_RE.match(item)]
    aliases = [item for item in values if not REGISTRY_ID_RE.match(item)]
    return real, aliases


def _registry_rank(platform: str) -> int:
    try:
        return REGISTRY_PREFERENCE.index(platform)
    except ValueError:
        return len(REGISTRY_PREFERENCE)


def _collect(records: list[dict], *, phases: set[str], exclude: set[str]) -> tuple[list[dict], dict]:
    """Deduplicate to one row per trial, applying the filters the tool cannot apply server-side.

    Row counts are never reported: 630 rows here were one trial, so the only honest count is the number
    of distinct trials that survive.
    """
    by_trial: dict[str, dict] = {}
    stats = {"rows": len(records), "no_trial_id": 0, "status": 0, "has_result": 0, "phase": 0, "excluded": 0}
    for record in records:
        trial_id = _text(record, "trial_id", "main_trial.trial_id")
        if not trial_id:
            stats["no_trial_id"] += 1
            continue
        status = _text(record, "trial_status", "main_trial.trial_status")
        if status and status not in ONGOING_STATUSES:
            stats["status"] += 1
            continue
        if _text(record, "trial_has_result", "main_trial.trial_has_result") == RESULT_YES:
            stats["has_result"] += 1
            continue
        phase = _text(record, "trial_phase", "main_trial.trial_phase")
        if phases and phase not in phases:
            stats["phase"] += 1
            continue
        all_ids = _values(record, "nct_ids", "main_trial.nct_ids")
        registry_ids, aliases = _split_ids(all_ids)
        if exclude & {item.upper() for item in all_ids}:
            stats["excluded"] += 1
            continue
        platform = _text(record, "registry_platform", "main_trial_sub_registry.registry_platform")
        registry = _text(record, "registry_id", "main_trial_sub_registry.registry_id")
        url = _text(record, "registry_url", "main_trial_sub_registry.registry_url")
        row = by_trial.get(trial_id)
        if row is None:
            row = by_trial[trial_id] = {
                "trial_id": trial_id,
                "registry_id": "",
                "registry_url": "",
                "registry_platform": "",
                "title": _text(record, "trial_title_zh", "main_trial.trial_title_zh"),
                "phase": phase,
                "status": status,
                "first_post_date": _date(record.get("trial_first_post_date")
                                         if record.get("trial_first_post_date") is not None
                                         else record.get("main_trial.trial_first_post_date")),
                "enrollment": _text(record, "trial_enrollment_estimated_global",
                                    "main_trial.trial_enrollment_estimated_global"),
                "indications": _values(record, "trial_indication_names_zh",
                                       "main_trial.trial_indication_names_zh"),
                "drugs": [],
                "secondary_drugs": [],
                "companies": [],
                "registry_ids": [],
                "aliases": [],
                "_rank": len(REGISTRY_PREFERENCE) + 1,
            }
        if url and _registry_rank(platform) < row["_rank"]:
            row.update({"registry_id": registry, "registry_url": url, "registry_platform": platform,
                        "_rank": _registry_rank(platform)})
        primary = _text(record, "drug_is_primary", "main_trial_sub_drug.drug_is_primary") == "是"
        for drug in _values(record, "drug_name_zh", "main_trial_sub_drug.drug_name_zh"):
            bucket = row["drugs"] if primary else row["secondary_drugs"]
            if drug not in bucket:
                bucket.append(drug)
        for company in _values(record, "drug_company_names_zh",
                               "main_trial_sub_drug.drug_company_names_zh"):
            if company not in row["companies"]:
                row["companies"].append(company)
        for item in registry_ids:
            if item not in row["registry_ids"]:
                row["registry_ids"].append(item)
        for item in aliases:
            if item not in row["aliases"]:
                row["aliases"].append(item)
    rows: list[dict] = []
    for row in by_trial.values():
        row.pop("_rank", None)
        if not row["drugs"]:                      # no row was flagged primary: keep what was returned
            row["drugs"] = row.pop("secondary_drugs")
        else:
            row.pop("secondary_drugs", None)
        if not row["registry_id"]:
            row["registry_id"] = next(iter(row["registry_ids"]), "")
        rows.append(row)
    # Most recently posted first: a reader watching the class wants the newest registration first.
    # A missing date sorts last (the empty string is below every `YYYY-MM-DD`).
    rows.sort(key=lambda item: item["first_post_date"], reverse=True)
    return rows, stats


def _write_state(path: Path, payload: dict) -> None:
    ps._atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _print_rows(rows: list[dict]) -> None:
    for index, row in enumerate(rows, start=1):
        print(f"{index}. {row['registry_id'] or row['trial_id']} · {row['phase'] or '（未返回）'} · "
              f"{row['status'] or '（未返回）'} · 首次公示 {row['first_post_date'] or '（未返回）'}")
        print(f"   药物：{'、'.join(row['drugs']) or '（未返回）'}｜公司：{'、'.join(row['companies']) or '（未返回）'}"
              f"｜目标入组：{row['enrollment'] or '（未返回）'}")
        print(f"   适应症：{'、'.join(row['indications']) or '（未返回）'}")
        print(f"   题目：{row['title'] or '（未返回）'}")
        print(f"   link：{row['registry_url'] or '（未返回）'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select the bounded ongoing-same-class watchlist from a trial pull and record its outcome.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--result", type=Path, help="raw .jsonl from the trial-v2 tool result")
    parser.add_argument("--tool-results", type=Path, default=Path("/workspace/tool_results"),
                        help="directory scanned when --result is omitted")
    parser.add_argument("--phase", action="append", default=[],
                        help="keep only these phases (repeatable; default: keep every phase present)")
    parser.add_argument("--exclude-nct", default="",
                        help="comma-separated registry ids already in the selected set")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"rows to keep (default {DEFAULT_LIMIT})")
    parser.add_argument("--refs", type=Path, default=Path("/workspace/work/refs.json"))
    parser.add_argument("--sources-dir", type=Path, default=Path("/workspace/work/sources"))
    parser.add_argument("--watchlist-state", type=Path,
                        help="where to record the outcome (default: <refs dir>/watchlist.json)")
    parser.add_argument("--append", action="store_true",
                        help="append the kept trials to work/refs.json as origin=watchlist")
    parser.add_argument("--none-found", action="store_true",
                        help="the pull came back and nothing ongoing/same-class survived the filters")
    parser.add_argument("--not-applicable", action="store_true",
                        help="the lookup does not apply here (needs --reason)")
    parser.add_argument("--reason", help="why --not-applicable (one clause, reader-free)")
    parser.add_argument("--json", action="store_true", help="print the selection as JSON")
    args = parser.parse_args(argv)

    path = state_path(args)
    reason = (args.reason or "").strip()

    if args.not_applicable:
        if len(reason) < 8:
            print("ERROR: --not-applicable needs --reason with at least 8 characters", file=sys.stderr)
            return 2
        _write_state(path, {"version": 1, "state": "not_applicable", "reason": reason,
                            "trials": [], "refs_added": []})
        print(f"RECORDED watchlist step as not_applicable: {reason}")
        return 0

    result = args.result
    if result is None:
        candidates = sorted(args.tool_results.glob("**/pharmcube-query-clinical-trial-with-params*/call_*.jsonl"))
        if not candidates:
            print(f"ERROR: no trial pull under {args.tool_results}", file=sys.stderr)
            return 2
        result = candidates[-1]
    if not result.is_file():
        print(f"ERROR: no such pull: {result}", file=sys.stderr)
        return 2

    records = _records(result)
    exclude = {item.strip().upper() for item in args.exclude_nct.split(",") if item.strip()}
    rows, stats = _collect(records, phases={p.strip() for p in args.phase if p.strip()}, exclude=exclude)
    kept = rows[: max(args.limit, 0)]

    payload = {
        "version": 1,
        "pull": str(result),
        "params": {"phase": args.phase, "exclude_nct": sorted(exclude), "limit": args.limit},
        "selected_fields": list(SELECTED_FIELDS),
        "stats": stats,
        "trials": kept,
        "refs_added": [],
    }

    if args.none_found or not kept:
        payload.update({"state": "none_alignable", "trials": []})
        if reason:
            payload["reason"] = reason
        _write_state(path, payload)
        if args.none_found:
            print(f"RECORDED watchlist step as none_alignable: {len(rows)} qualifying trial(s) after local "
                  "filters — nothing listed")
            return 0
        print(f"ERROR: the pull yielded no ongoing same-class trial once filtered "
              f"(rows={stats['rows']}, off-status={stats['status']}, with-results={stats['has_result']}, "
              f"off-phase={stats['phase']}, already-selected={stats['excluded']}); record the outcome with "
              "--none-found", file=sys.stderr)
        return 3

    if not args.append:
        payload["state"] = "listed"
        _write_state(path, payload)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print_rows(kept)
        print(f"WROTE {len(kept)} trial(s) to {path} (refs not appended; add --append when the report "
              "will cite them)")
        return 0

    try:
        added = ps.append_watchlist_refs(refs_path=args.refs, sources_dir=args.sources_dir, trials=kept)
    except ps.WatchlistAppendError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    for row, ref in zip(kept, added):
        row["ref"] = ref
    payload.update({"state": "listed", "refs_added": added})
    _write_state(path, payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_rows(kept)
        print(f"WROTE {len(kept)} trial(s) to {path}; appended {', '.join(added)} to {args.refs} "
              f"(origin=watchlist)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
