#!/usr/bin/env python3
"""Render fact-bound clinical results from a validated evidence ledger.

The renderer deliberately treats the ledger as a provenance contract: it checks
that every value is present in its cited source quote, but it does not infer or
validate clinical meaning.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


RECORD_FIELDS = ("ref", "title", "identity", "design", "arms", "coverage")
FACT_FIELDS = (
    "id",
    "ref",
    "study",
    "version",
    "endpoint",
    "arm",
    "population",
    "timepoint",
    "assessment",
    "kind",
    "value",
    "unit",
    "statistics",
    "source_file",
    "quote",
)
FACT_TOKEN_RE = re.compile(r"\[\[(fact|result):([^\]]+)\]\]")
CITATION_RE = re.compile(r"\{\{([^{}]+)\}\}")
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+−]?\d+(?:[.,]\d+)?%?")

# U+2212 is the common mathematical minus used by extracted clinical text.
MINUS_TRANSLATION = str.maketrans({"\N{MINUS SIGN}": "-"})


class ValidationError(Exception):
    """A user-facing ledger or draft validation error."""


def _is_string(value: Any, *, allow_empty: bool = False) -> bool:
    return isinstance(value, str) and (allow_empty or bool(value.strip()))


def _normalise_text(value: str) -> str:
    """Make source/quote whitespace comparable without changing other text."""
    return re.sub(r"\s+", " ", value.translate(MINUS_TRANSLATION)).strip()


def _normalise_markdown(value: str) -> str:
    """Keep ledger content in a single Markdown table cell."""
    return value.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"missing JSON file: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read UTF-8 JSON {path}: {exc}") from exc


def _validate_string_fields(item: Any, fields: tuple[str, ...], label: str, *, allow_empty: tuple[str, ...] = ()) -> None:
    if not isinstance(item, dict):
        raise ValidationError(f"{label} must be an object")
    missing = [field for field in fields if field not in item]
    extra = sorted(set(item) - set(fields))
    if missing:
        raise ValidationError(f"{label} missing fields: {', '.join(missing)}")
    if extra:
        raise ValidationError(f"{label} has unknown fields: {', '.join(extra)}")
    for field in fields:
        if not _is_string(item[field], allow_empty=field in allow_empty):
            state = "a string" if field not in allow_empty else "a string (possibly empty)"
            raise ValidationError(f"{label}.{field} must be {state}")


def _resolve_source(source_file: str, ledger_path: Path) -> Path:
    path = Path(source_file)
    return path if path.is_absolute() else ledger_path.parent / path


def validate_ledger(data: Any, ledger_path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not isinstance(data, dict) or set(data) != {"records", "facts"}:
        raise ValidationError("ledger must contain exactly records and facts")
    records = data["records"]
    facts = data["facts"]
    if not isinstance(records, list) or not records:
        raise ValidationError("ledger.records must be a non-empty array")
    if not isinstance(facts, list) or not facts:
        raise ValidationError("ledger.facts must be a non-empty array")

    record_values: list[dict[str, str]] = []
    refs: set[str] = set()
    for index, record in enumerate(records):
        _validate_string_fields(record, RECORD_FIELDS, f"records[{index}]")
        ref = record["ref"]
        if not re.fullmatch(r"ref_[1-9]\d*", ref):
            raise ValidationError(f"records[{index}].ref must look like ref_1")
        if ref in refs:
            raise ValidationError(f"duplicate record ref: {ref}")
        refs.add(ref)
        record_values.append(record)

    fact_values: list[dict[str, str]] = []
    ids: set[str] = set()
    source_cache: dict[Path, str] = {}
    for index, fact in enumerate(facts):
        _validate_string_fields(fact, FACT_FIELDS, f"facts[{index}]", allow_empty=("statistics",))
        fact_id = fact["id"]
        if fact_id in ids:
            raise ValidationError(f"duplicate fact id: {fact_id}")
        ids.add(fact_id)
        ref = fact["ref"]
        if ref not in refs:
            raise ValidationError(f"facts[{index}].ref is unknown: {ref}")

        source_path = _resolve_source(fact["source_file"], ledger_path)
        if not source_path.is_file():
            raise ValidationError(f"facts[{index}].source_file does not exist: {fact['source_file']}")
        if source_path not in source_cache:
            try:
                source_cache[source_path] = source_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ValidationError(f"cannot read UTF-8 source {fact['source_file']}: {exc}") from exc
        source_text = _normalise_text(source_cache[source_path])
        quote = _normalise_text(fact["quote"])
        if quote not in source_text:
            raise ValidationError(f"facts[{index}].quote is not an exact source substring: {fact_id}")
        value = _normalise_text(fact["value"])
        if value not in quote:
            raise ValidationError(f"facts[{index}].value is absent from quote: {fact_id}")
        fact_values.append(fact)

    return record_values, fact_values


def _replace_tokens(draft: str, facts_by_id: dict[str, dict[str, str]]) -> str:
    def replace(match: re.Match[str]) -> str:
        kind, fact_id = match.groups()
        fact = facts_by_id.get(fact_id)
        if fact is None:
            raise ValidationError(f"unknown fact token: {fact_id}")
        marker = "{{" + fact["ref"] + "}}"
        value_unit = f"{fact['value']} {fact['unit']}"
        if kind == "fact":
            return value_unit + marker
        statistics = f"；{fact['statistics']}" if fact["statistics"] else ""
        return f"{fact['endpoint']}：{value_unit}{statistics}{marker}"

    rendered = FACT_TOKEN_RE.sub(replace, draft)
    if re.search(r"\[\[(?:fact|result):", rendered):
        raise ValidationError("unresolved fact/result token remains in draft")
    return rendered


def _validate_citations(text: str, refs: set[str]) -> None:
    for citation in CITATION_RE.findall(text):
        if citation.startswith("ref_") and citation not in refs:
            raise ValidationError(f"draft contains unknown citation: {{{{{citation}}}}}")


def _dedupe_table_cell_citations(text: str) -> str:
    """Keep each source marker once per Markdown table cell."""
    seen: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        ref = match.group(1)
        if ref in seen:
            return ""
        seen.add(ref)
        return match.group(0)

    return CITATION_RE.sub(replace, text)


def _dedupe_table_citations(text: str) -> str:
    """Avoid repeating one ref after every fact in the same table cell."""
    lines = []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("|"):
            parts = re.split(r"(?<!\\)\|", line)
            line = "|".join(_dedupe_table_cell_citations(part) for part in parts)
        lines.append(line)
    return "".join(lines)


def _appendix(records: list[dict[str, str]], facts: list[dict[str, str]]) -> str:
    records_by_ref = {record["ref"]: record for record in records}
    record_order = {record["ref"]: index for index, record in enumerate(records)}
    ordered_facts = sorted(
        enumerate(facts),
        key=lambda item: (
            item[1]["kind"],
            item[1]["endpoint"],
            record_order[item[1]["ref"]],
            item[0],
        ),
    )

    parts = [
        "## Fact Ledger Appendix",
        "",
        "This appendix is a consolidated alignment matrix, not a separate report for each trial. Rows are ordered by outcome domain and endpoint; each row retains one disclosure version, endpoint, comparison, population, timepoint, and source marker.",
        "",
        "| Outcome domain | Trial / disclosure | Version / cutoff | Design and treatment groups | Endpoint / definition | Arm | Population / analysis set | Timepoint / assessment | Result / unit | Statistics | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, fact in ordered_facts:
        record = records_by_ref[fact["ref"]]
        context = f"{record['title']}<br>{record['identity']}"
        design = f"{record['design']}<br>{record['arms']}"
        result = f"{fact['value']} {fact['unit']}"
        parts.append(
            "| "
            + " | ".join(
                (
                    _normalise_markdown(fact["kind"]),
                    _normalise_markdown(context),
                    _normalise_markdown(fact["version"]),
                    _normalise_markdown(design),
                    _normalise_markdown(fact["endpoint"]),
                    _normalise_markdown(fact["arm"]),
                    _normalise_markdown(fact["population"]),
                    _normalise_markdown(f"{fact['timepoint']} / {fact['assessment']}"),
                    _normalise_markdown(result),
                    _normalise_markdown(fact["statistics"]),
                    "{{" + fact["ref"] + "}}",
                )
            )
            + " |"
        )
    if not facts:
        parts.append("| No ledger facts |  |  |  |  |  |  |  |  |  |  |")
    return "\n".join(parts) + "\n"


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


def render(ledger_path: Path, draft_path: Path, out_path: Path, audit_path: Path) -> bool:
    audit: dict[str, Any] = {
        "success": False,
        "output_written": False,
        "errors": [],
        "review_required": [
            "Token rendering does not validate clinical semantics.",
            "Statistics are provenance-checked but not clinically validated.",
            "Unbound handwritten prose numbers require human review; this renderer does not claim complete semantic safety.",
        ],
    }
    try:
        if out_path.resolve() == audit_path.resolve():
            raise ValidationError("--out and --audit must be different paths")
        ledger_data = _load_json(ledger_path)
        records, facts = validate_ledger(ledger_data, ledger_path)
        try:
            draft = draft_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValidationError(f"cannot read UTF-8 draft {draft_path}: {exc}") from exc

        refs = {record["ref"] for record in records}
        facts_by_id = {fact["id"]: fact for fact in facts}
        rendered_draft = _replace_tokens(draft, facts_by_id)
        _validate_citations(rendered_draft, refs)
        appendix = _appendix(records, facts)
        output = _dedupe_table_citations(rendered_draft.rstrip() + "\n\n" + appendix)

        # These are internal ledger identifiers and evidence paths, never report content.
        leaked = [fact["id"] for fact in facts if fact["id"] in output]
        leaked.extend(fact["source_file"] for fact in facts if fact["source_file"] in output)
        if leaked:
            raise ValidationError("final report exposes internal fact/source identifiers")
        if not output.strip():
            raise ValidationError("refusing to write an empty output")

        audit.update(
            {
                "records": len(records),
                "facts": len(facts),
                "fact_tokens_rendered": len(FACT_TOKEN_RE.findall(draft)),
                "handwritten_number_literals_for_review": len(NUMBER_RE.findall(draft)),
                "semantic_safety_claim": "none",
            }
        )
        _atomic_write(out_path, output)
        audit["success"] = True
        audit["output_written"] = True
    except (ValidationError, OSError) as exc:
        audit["errors"] = [str(exc)]
    except Exception as exc:  # Keep audit JSON available for unexpected failures.
        audit["errors"] = [f"unexpected error: {type(exc).__name__}: {exc}"]

    try:
        _atomic_write(audit_path, json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"cannot write audit {audit_path}: {exc}", file=sys.stderr)
        return False
    return bool(audit["success"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return 0 if render(args.ledger, args.draft, args.out, args.audit) else 1


if __name__ == "__main__":
    raise SystemExit(main())
