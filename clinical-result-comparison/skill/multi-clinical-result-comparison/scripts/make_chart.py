#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one chart product file (protocol envelope + option) from a content-only spec.

The chart contract has three moving parts and only one of them is yours to write:

1. the **option body** — this Skill's `templates/charts/*.json` skeleton (type, field names,
   defaults, axis titles) that you copy and then fill;
2. the **envelope** — `{id, iframe_template, option}` from the upstream
   `chart-visualization-json` skill, where `iframe_template` is refreshed on every chart
   publish and must never be hardcoded;
3. the **content** — title, subTitle, dataSource, describe and `data[]`, which is the only
   part you author.

Write that content as a spec file and let this script do 1 + 2 + the structural checks + the
upstream validation, so no chart JSON is ever assembled by hand:

    // work/charts/endpoint-bar-1.json   (a spec — NOT a deliverable)
    {
      "type": "bar",
      "file": "endpoint-bar-1.json",
      "title": "…", "subTitle": "跨试验并列展示≠头对头比较；…",
      "dataSource": "…", "describe": "…",
      "axisXTitle": "…", "axisYTitle": "…",
      "data": [{"label": "…（NCT…）", "value": 70.5, "description": "…"}]
    }

    python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py work/charts/endpoint-bar-1.json
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py work/charts/evidence-timeline.json --out-dir /workspace/visualizations

Checks that fail the run (exit 3, nothing written): `type` not in {bar,line,timeline}, a `file`
name outside the fixed product names, a `file`/`type` mismatch, an empty or non-numeric `data`
row, a missing label/description, a timeline event without `time`.  Checks that only warn
(length limits, a digit outside the `time` anchor in a timeline) print on stderr; `--strict`
turns them into failures.  After writing, the upstream CLI
(`node <chart-skill>/scripts/validate-cli.js <product>`) must exit 0 — a bare `option` object or
a stale local copy of the chart skill is not accepted (exit 4 = validator unavailable, product
written but unvalidated: say so instead of citing it as validated).

Exit codes: 0 written and validated; 3 structural finding (nothing written); 4 written but the
validator was unavailable; 2 usage / IO.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKELETONS = {"bar": "endpoint-bar.json", "line": "endpoint-line.json", "timeline": "evidence-timeline.json"}
PRODUCT_RE = re.compile(r"^(evidence-timeline|endpoint-bar-[1-9]\d*|endpoint-line-[1-9]\d*)\.json$")
FILE_TYPE = {"bar": r"^endpoint-bar-", "line": r"^endpoint-line-", "timeline": r"^evidence-timeline"}
CONTENT_FIELDS = ("title", "subTitle", "dataSource", "describe", "axisXTitle", "axisYTitle", "data")
DEFAULT_SORT = {"bar": "value-desc", "line": "none", "timeline": "time-asc"}
REGISTRY_RX = re.compile(r"\b(?:NCT|jRCT|JRCT|UMIN|ChiCTR|ISRCTN|EudraCT|EUCTR|CTR|IRCT)[\w-]*\d[\w-]*")
MARKER_RX = re.compile(r"\{\{[^{}]+\}\}")
MAX_LABEL = 18
MAX_CONTENT = 16


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


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _find_envelope(chart_skill: Path, kind: str) -> tuple[dict, Path]:
    templates = chart_skill / "templates"
    candidates = sorted(templates.glob("*.json")) if templates.is_dir() else []
    named = templates / f"{kind}.json"
    ordered = ([named] if named.is_file() else []) + [path for path in candidates if path != named]
    for path in ordered:
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        option = data.get("option")
        if isinstance(option, dict) and str(option.get("type", "")).lower() != kind:
            continue
        if data.get("id") and data.get("iframe_template"):
            return data, path
    raise FileNotFoundError(f"no chart-skill template with an id/iframe_template envelope under {templates}")


def _sort_data(data: list, mode: str) -> list:
    rows = list(data)
    if mode == "value-desc":
        return sorted(rows, key=lambda row: -float(row.get("value") or 0))
    if mode == "value-asc":
        return sorted(rows, key=lambda row: float(row.get("value") or 0))
    if mode == "time-asc":
        return sorted(rows, key=lambda row: str(row.get("time") or ""))
    return rows


def _digits_without_anchor(row: dict) -> str:
    """Return leftover digit-bearing text outside markers/registry ids (timeline no-number rule)."""
    leftovers = []
    for field in ("label", "content", "description", "group"):
        text = str(row.get(field) or "")
        text = MARKER_RX.sub("", text)
        text = REGISTRY_RX.sub("", text)
        if re.search(r"\d", text):
            leftovers.append(f"{field}={row.get(field)!r}")
    return "; ".join(leftovers)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Assemble one chart product from a content-only spec (envelope from the chart skill).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("/workspace/visualizations"))
    parser.add_argument("--chart-skill", type=Path, default=Path("/workspace/skills/chart-visualization-json"))
    parser.add_argument("--skeleton-dir", type=Path, default=here.parent / "templates" / "charts")
    parser.add_argument("--sort", choices=("auto", "none", "value-desc", "value-asc", "time-asc"), default="auto")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--no-validate", action="store_true", help="skip the upstream validate-cli run")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="machine-readable summary only")
    args = parser.parse_args(argv)

    if not args.spec.is_file():
        print(f"ERROR: spec not found: {args.spec}", file=sys.stderr)
        return 2
    try:
        spec = _load_json(args.spec)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read spec: {exc}", file=sys.stderr)
        return 2
    if not isinstance(spec, dict):
        print("ERROR: spec must be a JSON object", file=sys.stderr)
        return 2

    findings: list[str] = []
    warnings: list[str] = []

    kind = str(spec.get("type") or "").strip().lower()
    if kind not in SKELETONS:
        print(f"ERROR: spec.type must be one of {sorted(SKELETONS)} (got {kind!r})", file=sys.stderr)
        return 2
    file_name = str(spec.get("file") or "").strip()
    if not file_name:
        print("ERROR: spec.file is required (evidence-timeline.json / endpoint-bar-<n>.json / endpoint-line-<n>.json)",
              file=sys.stderr)
        return 2
    if not PRODUCT_RE.match(file_name):
        print(f"ERROR: {file_name!r} is not a fixed product name; the delivery path never takes a slug or index",
              file=sys.stderr)
        return 2
    if not re.match(FILE_TYPE[kind], file_name):
        print(f"ERROR: chart type {kind!r} cannot be written to {file_name!r}", file=sys.stderr)
        return 2

    skeleton_path = args.skeleton_dir / SKELETONS[kind]
    if not skeleton_path.is_file():
        print(f"ERROR: skeleton missing: {skeleton_path}", file=sys.stderr)
        return 2
    skeleton = _load_json(skeleton_path)
    option = {key: value for key, value in skeleton.items() if key != "_comment"}

    data = spec.get("data")
    if not isinstance(data, list) or not data:
        findings.append("spec.data must be a non-empty array")
        data = []
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            findings.append(f"data[{index}] is not an object")
            continue
        if not str(row.get("label") or "").strip():
            findings.append(f"data[{index}].label is empty")
        if kind == "timeline":
            if not str(row.get("time") or "").strip():
                findings.append(f"data[{index}].time is empty (a timeline event needs its date anchor)")
            if not str(row.get("description") or "").strip():
                findings.append(f"data[{index}].description is empty (relationship + maturity + {{ref_n}})")
            if len(str(row.get("label") or "")) > MAX_LABEL:
                warnings.append(f"data[{index}].label is {len(str(row['label']))} chars (limit {MAX_LABEL})")
            if len(str(row.get("content") or "")) > MAX_CONTENT:
                warnings.append(f"data[{index}].content is {len(str(row['content']))} chars (limit {MAX_CONTENT})")
            tricky = _digits_without_anchor(row)
            if tricky:
                warnings.append(f"data[{index}] carries a number outside the time anchor: {tricky}")
        else:
            value = row.get("value")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                findings.append(f"data[{index}].value must be a number (got {value!r})")
            if not str(row.get("description") or "").strip():
                findings.append(f"data[{index}].description is empty")
            if kind == "line" and not str(row.get("group") or "").strip():
                findings.append(f"data[{index}].group is empty (a line needs its cohort/treatment group)")

    for field in ("title", "subTitle", "dataSource", "describe"):
        if not str(spec.get(field) or "").strip():
            warnings.append(f"spec.{field} is empty")
    for field in CONTENT_FIELDS:
        if field in spec:
            option[field] = spec[field]

    mode = DEFAULT_SORT[kind] if args.sort == "auto" else args.sort
    if mode != "none":
        option["data"] = _sort_data(data, mode)
    else:
        option["data"] = list(data)

    try:
        envelope, envelope_path = _find_envelope(args.chart_skill, kind)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    product = {"id": envelope["id"], "iframe_template": envelope["iframe_template"], "option": option}

    if findings:
        print(f"FINDINGS ({len(findings)}) — nothing written:", file=sys.stderr)
        for item in findings:
            print(f"  - {item}", file=sys.stderr)
        return 3
    strict_fail = args.strict and warnings
    for item in warnings:
        print(f"WARN: {item}", file=sys.stderr)
    if strict_fail:
        print("STRICT: warnings treated as failures — nothing written", file=sys.stderr)
        return 3

    target = args.out_dir / file_name
    if args.dry_run:
        print(json.dumps({"file": str(target), "rows": len(option["data"]), "envelope": envelope_path.name,
                          "iframe_template": product["iframe_template"], "warnings": warnings,
                          "dry_run": True}, ensure_ascii=False))
        return 0

    try:
        _atomic_write(target, json.dumps(product, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"ERROR: cannot write {target}: {exc}", file=sys.stderr)
        return 2

    validator = args.chart_skill / "scripts" / "validate-cli.js"
    if args.no_validate:
        status, note = "skipped", "--no-validate"
    elif not validator.is_file() or shutil.which("node") is None:
        status, note = "unavailable", f"node or {validator} missing"
    else:
        completed = subprocess.run(["node", str(validator), str(target)], capture_output=True, text=True)
        if completed.returncode == 0:
            status, note = "pass", (completed.stdout or "").strip()[:200]
        else:
            status, note = "fail", ((completed.stderr or completed.stdout or "").strip()[:600])

    summary = {"file": str(target), "type": kind, "rows": len(option["data"]),
               "sort": mode, "envelope": envelope_path.name, "validation": status, "note": note,
               "warnings": warnings}
    print(json.dumps(summary, ensure_ascii=False))
    if status == "fail":
        print("VALIDATION FAILED — the chart is not deliverable as written; fix the spec and rerun",
              file=sys.stderr)
        return 3
    if status == "unavailable":
        print("NOTE: chart validation is unavailable in this runtime; report that state instead of claiming "
              "a validated chart", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
