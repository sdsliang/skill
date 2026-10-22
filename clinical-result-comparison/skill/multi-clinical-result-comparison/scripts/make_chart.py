#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one chart product file (protocol envelope + `config`) from a content-only spec.

The chart contract has three moving parts and only one of them is yours to write:

1. the **config body** — this Skill's `templates/charts/*.json` skeleton (kind, type, field names,
   defaults, axis titles) that you copy and then fill;
2. the **envelope** — `{id, version, iframe_template, config}` from the upstream
   `chart-component-layout-json-validation` skill, where `iframe_template` and `version` are
   refreshed on every chart publish and must never be hardcoded;
3. the **content** — title, subTitle, dataSource, describe and `data[]`, which is the only
   part you author.

The upstream skill retired the old `dataSource` / `describe` config fields: the source and the
reading-aid text now live in a `config.notes` node array (`source-note` → `source-note-row` →
`note-label` + `note-content`). This script renders that node structure for you (labels follow the
report language), so the spec keeps the same two plain text fields.

Write that content as a spec file and let this script do 1 + 2 + the structural checks + the
upstream validation, so no chart JSON is ever assembled by hand:

    // work/charts/endpoint-bar-1.json   (a spec — NOT a deliverable)
    {
      "type": "bar",
      "file": "endpoint-bar-1.json",
      "language": "zh",
      "title": "…", "subTitle": "跨试验并列展示≠头对头比较；…",
      "dataSource": "…", "describe": "…",
      "axisXTitle": "…", "axisYTitle": "…",
      "data": [{"label": "…（NCT…）", "value": 70.5, "description": "…"}]
    }

    python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py work/charts/endpoint-bar-1.json
    python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py work/charts/evidence-timeline.json --out-dir /workspace/visualizations

`language` selects the `note-label` wording (`说明：`/`数据来源：` vs `Note:`/`Data source:`) and is
optional: when it is missing the script infers it from the spec's own text (CJK present → `zh`) and
prints a WARN, so an English report does not silently inherit Chinese note labels.

Checks that fail the run (exit 3, nothing written): `type` not in {bar,line,timeline}, a `file`
name outside the fixed product names, a `file`/`type` mismatch, an empty or non-numeric `data`
row, a missing label/description, a timeline event without `time`, a timeline spec that still
carries `weight`/`weightLegend`/`legend` (the deployed timeline renders a plain vertical list —
every node the same dot, no legend at all — so size/shape/legend cannot encode anything; the
judgement belongs in the report text and the node description), or a spec that writes `option` /
`config` / `notes` by hand.  Checks that only warn (length limits, a digit outside the `time`
anchor in a timeline) print on stderr; `--strict` turns them into failures.  After writing, the
upstream CLI (`node <chart-skill>/scripts/validate-cli.js <product>`) must exit 0 — a bare
`config` object or a stale local copy of the chart skill is not accepted (exit 4 = validator
unavailable, product written but unvalidated: say so instead of citing it as validated).

Exit codes: 0 written (a WARN-only run is still 0); 3 structural finding (nothing written); 4
written but the validator was unavailable; 2 usage / IO.  Completeness gaps (empty
label/description/group, over-length text) print WARN and never change the exit code — do not
pre-check them before writing the spec.
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
CONTENT_FIELDS = ("title", "subTitle", "axisXTitle", "axisYTitle")
NOTE_LABELS = {
    "zh": {"note": "说明：", "source": "数据来源："},
    "en": {"note": "Note:", "source": "Data source:"},
}
DEFAULT_SORT = {"bar": "value-desc", "line": "none", "timeline": "time-asc"}
REGISTRY_RX = re.compile(r"\b(?:NCT|jRCT|JRCT|UMIN|ChiCTR|ISRCTN|EudraCT|EUCTR|CTR|IRCT)[\w-]*\d[\w-]*")
MARKER_RX = re.compile(r"\{\{[^{}]+\}\}")
CJK_RX = re.compile(r"[\u3400-\u9fff]")
MAX_LABEL = 18
MAX_CONTENT = 16
# Envelope values are read from the deployed chart skill at runtime; these names only locate them.
SKILL_NAME = "chart-component-layout-json-validation"


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


def _envelope_from_config_js(chart_skill: Path) -> dict | None:
    """Fallback: read SKILL_NAME / IFRAME_TEMPLATE / VERSION out of the chart skill's config.js."""
    config_js = chart_skill / "config.js"
    try:
        source = config_js.read_text(encoding="utf-8")
    except OSError:
        return None

    def literal(name: str) -> str | None:
        match = re.search(rf"""^\s*const\s+{name}\s*=\s*'([^']*)'""", source, re.MULTILINE)
        return match.group(1) if match else None

    envelope = {
        "id": literal("SKILL_NAME"),
        "version": literal("VERSION"),
        "iframe_template": literal("IFRAME_TEMPLATE"),
    }
    if all(envelope.values()):
        return envelope
    return None


def _find_envelope(chart_skill: Path, kind: str) -> tuple[dict, Path]:
    """Return the deployed `{id, version, iframe_template}` plus the file it came from.

    The chart skill ships full envelope templates under `templates/charts/<type>.json`; the single
    chart templates and the node templates are not chart products, so only `charts/` is scanned.
    """
    templates = chart_skill / "templates" / "charts"
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
        config = data.get("config")
        if isinstance(config, dict) and str(config.get("type", "")).lower() not in ("", kind):
            continue
        envelope = {key: data.get(key) for key in ("id", "version", "iframe_template")}
        if all(isinstance(value, str) and value.strip() for value in envelope.values()):
            return envelope, path
    fallback = _envelope_from_config_js(chart_skill)
    if fallback is None:
        raise FileNotFoundError(
            f"no chart-skill template with an id/version/iframe_template envelope under {templates}"
        )
    return fallback, chart_skill / "config.js"


def _language(spec: dict) -> tuple[str, bool]:
    """Return (language, declared). `language` is declared by the spec or inferred from its text."""
    declared = str(spec.get("language") or "").strip().lower()
    if declared in NOTE_LABELS:
        return declared, True
    probe = " ".join(str(spec.get(field) or "") for field in ("title", "subTitle", "describe", "dataSource"))
    return ("zh" if CJK_RX.search(probe) else "en"), False


def _notes(spec: dict, language: str) -> list[dict]:
    """Render `config.notes`: 说明 / 数据来源 rows, labels in the report's language."""
    labels = NOTE_LABELS[language]
    rows = []
    for key, label_key in (("describe", "note"), ("dataSource", "source")):
        text = str(spec.get(key) or "").strip()
        if not text:
            continue
        rows.append({
            "kind": "layout",
            "role": "source-note-row",
            "cols": [
                {"kind": "string", "role": "note-label", "markdown": labels[label_key]},
                {"kind": "string", "role": "note-content", "markdown": text},
            ],
        })
    if not rows:
        return []
    return [{"kind": "layout", "role": "source-note", "rows": rows}]


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
    parser.add_argument("--chart-skill", type=Path, default=Path(f"/workspace/skills/{SKILL_NAME}"))
    parser.add_argument("--skeleton-dir", type=Path, default=here.parent / "templates" / "charts")
    parser.add_argument("--sort", choices=("auto", "none", "value-desc", "value-asc", "time-asc"), default="auto")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--no-validate", action="store_true", help="DEBUG ONLY — skips the upstream validate-cli run; charts produced this way can still be rejected downstream by the report gate")
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
    for hand_written in ("option", "config", "notes"):
        if hand_written in spec:
            findings.append(
                f"spec.{hand_written} is not accepted: the envelope and the notes node tree are assembled "
                "from the deployed chart skill — write title/subTitle/describe/dataSource/data only")

    language, language_declared = _language(spec)
    if not language_declared:
        warnings.append(
            f"spec.language is missing (inferred {language!r} from the spec text); declare "
            "\"language\": \"zh\" or \"en\" so the chart notes match the report language")

    skeleton_path = args.skeleton_dir / SKELETONS[kind]
    if not skeleton_path.is_file():
        print(f"ERROR: skeleton missing: {skeleton_path}", file=sys.stderr)
        return 2
    skeleton = _load_json(skeleton_path)
    config = {key: value for key, value in skeleton.items() if key != "_comment"}
    config["kind"] = "chart"
    config["type"] = kind

    data = spec.get("data")
    if not isinstance(data, list) or not data:
        findings.append("spec.data must be a non-empty array")
        data = []
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            findings.append(f"data[{index}] is not an object")
            continue
        if not str(row.get("label") or "").strip():
            warnings.append(f"data[{index}].label is empty (advisory: the chart still renders)")
        if kind == "timeline":
            if not str(row.get("time") or "").strip():
                findings.append(f"data[{index}].time is empty (a timeline event needs its date anchor)")
            if not str(row.get("description") or "").strip():
                warnings.append(f"data[{index}].description is empty (relationship + maturity + {{ref_n}}) "
                                f"— advisory: the node still renders on its time anchor")
            if len(str(row.get("label") or "")) > MAX_LABEL:
                warnings.append(f"data[{index}].label is {len(str(row['label']))} chars (limit {MAX_LABEL})")
            if len(str(row.get("content") or "")) > MAX_CONTENT:
                warnings.append(f"data[{index}].content is {len(str(row['content']))} chars (limit {MAX_CONTENT})")
            tricky = _digits_without_anchor(row)
            if tricky:
                warnings.append(f"data[{index}] carries a number outside the time anchor: {tricky}")
            if row.get("weight") is not None:
                findings.append(
                    f"data[{index}].weight is not supported: the deployed timeline renders every node the "
                    "same, so weight encodes nothing — write the maturity judgement in the node description "
                    "and the report text instead")
            if row.get("shape") is not None:
                findings.append(
                    f"data[{index}].shape is not supported: timeline nodes are not shape-coded (the legend "
                    "renderer is empty for this type) — state the category in the node label/content text")
        else:
            value = row.get("value")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                findings.append(f"data[{index}].value must be a number (got {value!r})")
            if not str(row.get("description") or "").strip():
                warnings.append(f"data[{index}].description is empty (advisory: the value still plots)")
            if kind == "line" and not str(row.get("group") or "").strip():
                warnings.append(f"data[{index}].group is empty (a line names its cohort/treatment group) "
                                f"— advisory: the series still plots")

    if kind == "timeline" and spec.get("weightLegend") is not None:
        findings.append(
            "spec.weightLegend is not supported: the deployed timeline renders no weight legend, so it "
            "would only imply a size encoding that does not exist — drop it and state the maturity "
            "judgement in text")
    if kind == "timeline" and spec.get("legend") is not None:
        findings.append(
            "spec.legend is not supported: the deployed timeline renders no legend and every node looks "
            "the same, so a legend would only imply a category/shape encoding that does not exist — drop "
            "it and name each state's category in its label/content text")
    for field in ("title", "subTitle", "dataSource", "describe"):
        if not str(spec.get(field) or "").strip():
            warnings.append(f"spec.{field} is empty")
    for field in CONTENT_FIELDS:
        if field in spec:
            config[field] = spec[field]
    config["notes"] = _notes(spec, language)

    mode = DEFAULT_SORT[kind] if args.sort == "auto" else args.sort
    if mode != "none":
        config["data"] = _sort_data(data, mode)
    else:
        config["data"] = list(data)

    try:
        envelope, envelope_path = _find_envelope(args.chart_skill, kind)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if envelope.get("id") != SKILL_NAME:
        warnings.append(
            f"chart skill envelope id is {envelope.get('id')!r}, expected {SKILL_NAME!r} — the deployed skill "
            "may be a different one; verify before referencing the product")
    product = {
        "id": envelope["id"],
        "version": envelope["version"],
        "iframe_template": envelope["iframe_template"],
        "config": config,
    }

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
        print(json.dumps({"file": str(target), "rows": len(config["data"]), "envelope": envelope_path.name,
                          "iframe_template": product["iframe_template"], "language": language,
                          "warnings": warnings, "dry_run": True}, ensure_ascii=False))
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

    summary = {"file": str(target), "type": kind, "rows": len(config["data"]), "language": language,
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
