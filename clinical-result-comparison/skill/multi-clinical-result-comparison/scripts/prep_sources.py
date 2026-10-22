#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn one bulk record pull into per-record source files and a ref inventory.

The pull (the `pharmcube-query-clinical-result-with-params` tool result) is persisted by
the runtime under `tool_results/<tool-name>/call_<id>.jsonl` (i.e. `<workspace>/tool_results/...`;
never quote the absolute prefix with a placeholder component), one JSON record per
line.  This script is the only supported way to turn that payload into the material the
later steps consume:

* `/workspace/work/sources/ref_<n>.txt` — the extracted body of record `ref_<n>`, and the
  file a ledger fact's `source_file` / `quote` must resolve against (the render gate fails
  closed unless `quote` is an exact substring of it);
* `/workspace/work/refs.json` — the ref inventory `make_citations.py` copies byte-for-byte
  `title` / `link` / release date from.

Do not hand-copy record text or write your own extraction script: the citation fields must
stay byte-for-byte, and the quote binding is checked mechanically.

Usage
-----
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py --esids 24_1_36342163,24_1_30561610
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py --esids-file work/selected.txt --full
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py --result tool_results/<tool>/call_x.jsonl \
        --esids 24_1_36342163 --sources-dir work/sources --refs work/refs.json

Bounded external reference (`references/external-context.md`): append the records of an expansion pull AFTER the
selected refs, leaving `ref_1..ref_k` untouched, marking every appended entry `"origin":"external"`, and
refusing to renumber, to re-add an esid already present, or to exceed the budget:

    python3 /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py --external \
        --result tool_results/<tool>/call_y.jsonl --max-external 6

Exit codes: 0 every requested esid was found; 3 some requested esids were not in the pull (with `--external`:
nothing new to append, or the budget would be exceeded); 2 usage / input error.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import tempfile
from pathlib import Path

PREFIX = "clinical_result_"
ESID_KEYS = (PREFIX + "extra_esid", PREFIX + "esid", "extra_esid", "esid")
LIST_CONTAINERS = ("data", "rows", "records", "items", "value", "result", "list")

# field -> candidate keys, in priority order (first non-empty wins)
FIELD_KEYS = {
    "title": (PREFIX + "paper_title", "paper_title", "title"),
    "link": (PREFIX + "full_article_link", "full_article_link", "link"),
    "release": (PREFIX + "paper_release_time", "paper_release_time"),
    "journal": (PREFIX + "journal",),
    "doi": (PREFIX + "doi",),
    "pm_id": (PREFIX + "pm_id",),
    "trial_abbreviation": (PREFIX + "trial_abbreviation",),
    "group_count": (PREFIX + "group_count",),
    "blinded": (PREFIX + "blinded",),
    "randomized": (PREFIX + "randomized",),
    "random_ratio": (PREFIX + "random_ratio",),
    "trial_control": (PREFIX + "trial_control",),
    "positive_placebo_control": (PREFIX + "positive_placebo_control",),
    "evidence_source": (PREFIX + "evidence_source",),
    "clinical_stage_cn": (PREFIX + "clinical_stage_cn",),
    "therapy_line_cn": (PREFIX + "therapy_line_cn",),
    "indication_name": (PREFIX + "indication_name",),
    "primary_endpoint_cn": (PREFIX + "primary_endpoint_cn",),
    "multi_center": (PREFIX + "multi_center",),
    "abstract": (PREFIX + "abstract_text",),
    "summary": (PREFIX + "summary",),
}
BODY_LIMIT = 4000          # characters of abstract/summary printed in the digest by default
EVIDENCE_LIMIT = 12        # rows of arms/study_results summarised in the digest by default
EXTERNAL_LIMIT = 6         # hard cap on origin=external entries (references/external-context.md budget)


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


def _flatten(value):
    """Yield record dicts from a payload that may be nested in a list container."""
    if isinstance(value, dict):
        esid = _esid(value)
        if esid:
            yield value
            return
        for key in LIST_CONTAINERS:
            nested = value.get(key)
            if isinstance(nested, list):
                yield from _flatten(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten(item)


def _esid(record: dict) -> str:
    for key in ESID_KEYS:
        raw = record.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return str(raw)
    return ""


def _field(record: dict, name: str) -> str:
    for key in FIELD_KEYS[name]:
        raw = record.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            if raw.strip():
                return raw.strip()
            continue
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return str(raw)
        if isinstance(raw, list):
            values = [str(item).strip() for item in raw if str(item).strip()]
            if values:
                return "、".join(values)
        if isinstance(raw, dict) and raw:
            return json.dumps(raw, ensure_ascii=False)
    return ""


def _date_only(value: str) -> str:
    match = re.match(r"\s*(\d{4}-\d{2}-\d{2})", value or "")
    return match.group(1) if match else ""


def _candidate_files(tool_results: Path) -> list[Path]:
    return [Path(p) for p in sorted(glob.glob(str(tool_results / "**" / "*.jsonl"), recursive=True))]


def _load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.extend(_flatten(payload))
    return records


def _pick_result_file(tool_results: Path) -> Path | None:
    best: tuple[int, Path] | None = None
    for path in _candidate_files(tool_results):
        try:
            records = _load_records(path)
        except OSError:
            continue
        if not records:
            continue
        score = len(records)
        if best is None or score > best[0]:
            best = (score, path)
    return best[1] if best else None


def _esids_from_args(args) -> list[str]:
    ordered: list[str] = []
    if args.esids:
        ordered.extend(part.strip() for part in args.esids.split(","))
    if args.esids_file:
        text = Path(args.esids_file).read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                ordered.extend(part.strip() for part in line.split(","))
    out: list[str] = []
    for esid in ordered:
        if esid and esid not in out:
            out.append(esid)
    return out


def _compact_rows(title: str, rows, limit: int) -> str:
    if not isinstance(rows, list) or not rows:
        return f"## {title}\n（无）\n"
    lines = [f"## {title}（{len(rows)} 条）"]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            lines.append(f"- [{index}] {row}")
            continue
        pairs = []
        for key, value in row.items():
            if value in (None, "", [], {}):
                continue
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            pairs.append(f"{key}={text}")
        lines.append(f"- [{index}] " + " | ".join(pairs))
    return "\n".join(lines) + "\n"


def _source_body(record: dict, ref: str, esid: str) -> str:
    abstract = _field(record, "abstract")
    summary = _field(record, "summary")
    header = [
        f"# {ref} · esid={esid}",
        f"title: {_field(record, 'title')}",
        f"link: {_field(record, 'link')}",
        f"release_time: {_field(record, 'release')}",
        f"journal: {_field(record, 'journal')}",
        f"doi: {_field(record, 'doi')}",
        f"pm_id: {_field(record, 'pm_id')}",
        f"trial_abbreviation: {_field(record, 'trial_abbreviation')}",
        f"indication: {_field(record, 'indication_name')}",
        f"primary_endpoint: {_field(record, 'primary_endpoint_cn')}",
        f"group_count: {_field(record, 'group_count')}",
        f"randomized: {_field(record, 'randomized')}",
        f"blinded: {_field(record, 'blinded')}",
        f"random_ratio: {_field(record, 'random_ratio')}",
        f"trial_control: {_field(record, 'trial_control')}",
        f"positive_placebo_control: {_field(record, 'positive_placebo_control')}",
        f"evidence_source: {_field(record, 'evidence_source')}",
        f"clinical_stage: {_field(record, 'clinical_stage_cn')}",
        f"therapy_line: {_field(record, 'therapy_line_cn')}",
        f"multi_center: {_field(record, 'multi_center')}",
    ]
    blocks = ["\n".join(header), ""]
    if abstract:
        blocks.append("## 正文（abstract）")
        blocks.append(abstract)
        blocks.append("")
    if summary:
        blocks.append("## 摘要（summary）")
        blocks.append(summary)
        blocks.append("")
    if not abstract and not summary:
        blocks.append("## 正文\n（该记录未返回正文，任何引用都必须说明这一点）\n")
    blocks.append(_compact_rows("arms", record.get(PREFIX + "arms"), EVIDENCE_LIMIT))
    blocks.append(_compact_rows("study_results", record.get(PREFIX + "study_results"), EVIDENCE_LIMIT))
    projects = record.get(PREFIX + "projects")
    if isinstance(projects, list) and projects:
        blocks.append(_compact_rows("projects", projects, EVIDENCE_LIMIT))
    return "\n".join(blocks).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract the pulled records into work/sources/ref_<n>.txt + work/refs.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run once per selection, then read work/refs.json and the printed digest.",
    )
    parser.add_argument("--result", type=Path, help="raw .jsonl from tool_results/ (default: newest with records)")
    parser.add_argument("--tool-results", type=Path, default=Path("/workspace/tool_results"),
                        help="directory scanned for the raw pull when --result is omitted")
    parser.add_argument("--esids", help="comma-separated esids in selection order")
    parser.add_argument("--esids-file", type=Path, help="file with esids (one per line, '#' comments allowed)")
    parser.add_argument("--sources-dir", type=Path, default=Path("/workspace/work/sources"))
    parser.add_argument("--refs", type=Path, default=Path("/workspace/work/refs.json"))
    parser.add_argument("--body-chars", type=int, default=BODY_LIMIT, help="digest body characters per record")
    parser.add_argument("--full", action="store_true", help="print whole bodies and every arm/result row")
    parser.add_argument("--quiet", action="store_true", help="write files only, print one summary line")
    parser.add_argument("--external", action="store_true",
                        help="append the pull's new records after the existing refs as origin=external")
    parser.add_argument("--only-esids", help="with --external: append only these esids from the pull "
                                            "(the ones the block will actually cite)")
    parser.add_argument("--max-external", type=int, default=EXTERNAL_LIMIT,
                        help=f"hard cap on origin=external entries in the inventory (default {EXTERNAL_LIMIT})")
    args = parser.parse_args(argv)

    esids = [] if args.external else _esids_from_args(args)
    if not esids and not args.external:
        parser.error("give --esids or --esids-file")
    if args.external and args.result is None:
        parser.error("--external requires --result (name the expansion pull; never guess the newest payload)")

    result_file = args.result
    if result_file is None:
        searched = [args.tool_results]
        if args.tool_results == Path("/workspace/tool_results"):
            searched += [Path("tool_results"), Path("/workspace/work/tool_results")]
        for directory in searched:
            if directory.is_dir():
                result_file = _pick_result_file(directory)
                if result_file is not None:
                    break
        if result_file is None:
            print("ERROR: no record pull found under "
                  + ", ".join(str(item) for item in searched) + "; pass --result", file=sys.stderr)
            return 2
    if not result_file.is_file():
        print(f"ERROR: {result_file} is not a file", file=sys.stderr)
        return 2

    records = _load_records(result_file)
    if not records:
        print(f"ERROR: no records parsed from {result_file}", file=sys.stderr)
        return 2

    by_esid: dict[str, dict] = {}
    duplicates: list[str] = []
    for record in records:
        esid = _esid(record)
        if not esid:
            continue
        if esid in by_esid:
            duplicates.append(esid)
            continue
        by_esid[esid] = record

    origin = "external" if args.external else "selected"
    refs: dict[str, dict] = {}
    start_index = 1
    found: list[tuple[str, dict]] = []
    missing: list[str] = []
    skipped: list[str] = []

    if args.external:
        if not args.refs.is_file():
            print(f"ERROR: --external appends to an existing inventory, but {args.refs} does not exist "
                  "(run the selection pull through prep_sources.py first)", file=sys.stderr)
            return 2
        try:
            existing = json.loads(args.refs.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: cannot read {args.refs}: {exc}", file=sys.stderr)
            return 2
        if not isinstance(existing, dict) or not existing:
            print(f"ERROR: {args.refs} is not a ref inventory object", file=sys.stderr)
            return 2
        refs = existing
        indices = [int(key.split("_", 1)[1]) for key in refs if re.fullmatch(r"ref_[1-9]\d*", str(key))]
        start_index = (max(indices) + 1) if indices else 1
        already = {str(entry.get("esid", "")).strip() for entry in refs.values() if isinstance(entry, dict)}
        external_used = sum(1 for entry in refs.values()
                            if isinstance(entry, dict) and str(entry.get("origin", "")).strip() == "external")
        only = {item.strip() for item in (args.only_esids or "").split(",") if item.strip()}
        seen: set[str] = set()
        for record in records:
            esid = _esid(record)
            if only and esid not in only:
                continue
            if not esid:
                skipped.append("(no esid)")
                continue
            if esid in already or esid in seen:
                skipped.append(esid)
                continue
            seen.add(esid)
            found.append((esid, record))
        if not found:
            scope = f"for --only-esids {sorted(only)}" if only else "at all"
            print(f"ERROR: the expansion pull carries no record absent from {args.refs} {scope}; "
                  "nothing to append", file=sys.stderr)
            return 3
        appended = {esid for esid, _ in found}
        if only - appended:
            missing.extend(sorted(only - appended))
        remaining = args.max_external - external_used
        if len(found) > remaining:
            print(f"ERROR: external-reference budget exceeded: {external_used} already recorded, this pull adds "
                  f"{len(found)}, cap is {args.max_external} (keep at most {max(remaining, 0)})", file=sys.stderr)
            return 3
    else:
        for esid in esids:
            record = by_esid.get(esid)
            if record is None:
                missing.append(esid)
                continue
            found.append((esid, record))

    digest: list[str] = [f"# 记录清单（{len(found)} 条；来自 {result_file}；origin={origin}）", ""]
    for offset, (esid, record) in enumerate(found):
        ref = f"ref_{start_index + offset}"
        path = args.sources_dir / f"{ref}.txt"
        try:
            _atomic_write(path, _source_body(record, ref, esid))
        except OSError as exc:
            print(f"ERROR: cannot write {path}: {exc}", file=sys.stderr)
            return 2
        entry = {
            "esid": esid,
            "origin": origin,
            "title": _field(record, "title"),
            "link": _field(record, "link"),
            "paper_release_time": _field(record, "release"),
            "paper_release_time_str": _date_only(_field(record, "release")),
            "journal": _field(record, "journal"),
            "doi": _field(record, "doi"),
            "pm_id": _field(record, "pm_id"),
            "trial_abbreviation": _field(record, "trial_abbreviation"),
            "indication": _field(record, "indication_name"),
            "primary_endpoint": _field(record, "primary_endpoint_cn"),
            "source_file": str(path),
        }
        refs[ref] = entry
        body = _field(record, "abstract") or _field(record, "summary")
        shown = body if args.full else body[: args.body_chars]
        tail = "" if args.full or len(body) <= args.body_chars else f"\n…（正文共 {len(body)} 字，完整内容见 {path}）"
        digest.append(f"## {ref} · esid={esid} · 正文 {len(body)} 字")
        digest.append(f"title: {entry['title']}")
        digest.append(f"link: {entry['link']}")
        digest.append(f"release: {entry['paper_release_time'] or '（未返回）'}")
        digest.append(f"journal/doi/pm_id: {entry['journal']} / {entry['doi']} / {entry['pm_id']}")
        digest.append(f"trial_abbreviation: {entry['trial_abbreviation']}")
        digest.append(f"indication: {entry['indication']} | primary_endpoint: {entry['primary_endpoint']}")
        digest.append(f"source_file: {path}")
        digest.append("正文：")
        digest.append(shown + tail)
        digest.append("")

    try:
        _atomic_write(args.refs, json.dumps(refs, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"ERROR: cannot write {args.refs}: {exc}", file=sys.stderr)
        return 2

    if args.quiet:
        print(f"{len(found)} record(s) written to {args.sources_dir}; refs -> {args.refs}; missing={missing}")
    else:
        print("\n".join(digest).rstrip())
        print("")
        print(f"WROTE {len(found)} record(s) ({origin}) to {args.sources_dir}")
        print(f"WROTE ref inventory to {args.refs} (keys: {', '.join(refs) or 'none'})")
    if skipped:
        print(f"NOTE: {len(skipped)} record(s) in the expansion pull were already in the inventory "
              f"(not re-added): {', '.join(skipped[:5])}", file=sys.stderr)
    if duplicates:
        print(f"NOTE: the pull repeated {len(duplicates)} record row(s) (deduplicated): "
              f"{', '.join(sorted(set(duplicates))[:5])}", file=sys.stderr)
    if missing:
        print("MISSING (requested but absent from the pull): " + ", ".join(missing), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
