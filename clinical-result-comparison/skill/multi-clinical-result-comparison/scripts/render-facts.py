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


RECORD_FIELDS = ("ref", "title", "identity", "design", "arms", "coverage", "conclusion")
# `trial` is the appendix merge key. Contract (prompt v0.16) says every record carries it;
# the renderer tolerates its absence and falls back to registry id / `study` label, because a
# presentation hint must not block an otherwise sound delivery.
RECORD_OPTIONAL_FIELDS = ("trial",)
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

APPENDIX_TITLE = "## 附录：证据对齐矩阵（数值事实账本）"
APPENDIX_INTRO = (
    "按「试验设计 → 试验结论 → 有效性 → 安全性 → PK/PD → PRO」分段排列：列为试验，同一试验的多条披露合并为一列；"
    "行为维度与终点（同一终点的不同时点/口径统一到同一行，细分标签写进单元格）；`—` 表示该披露在该终点上未报告数值。"
    "单元格格式为「治疗臂·时点·评估·人群：结果 单位（统计量）」，紧跟其后的来源标记即该值的引用；"
    "同一披露的多个数值用 `<br>` 分行，未报告处写 `—`。"
)
SEGMENT_ORDER = ("试验设计", "试验结论", "有效性", "安全性", "PK/PD", "PRO", "其他")

# Record-level rows of the 试验设计 / 试验结论 blocks, in the fixed reading order.
DESIGN_ROWS = (
    ("试验身份", "identity"),
    ("披露标题", "title"),
    ("设计与方案", "design"),
    ("试验组与对照", "arms"),
    ("人群与证据覆盖", "coverage"),
)
# Entity inline references were removed in v0.16: the report carries plain names only.
# `_strip_entity_links` removes the syntax from ledger display text; this regex is the
# post-strip safety net that keeps any leftover `entity:` form out of the deliverable.
ENTITY_LINK_RE = re.compile(r"\(entity:[^)]*\)|entity:\s*[a-z]+", re.IGNORECASE)
# Trial registry identifiers are the primary appendix column key.
REGISTRATION_RE = re.compile(
    r"\b(?:NCT\d{6,9}|ChiCTR[0-9A-Za-z\-]{4,}|ISRCTN\d{6,}|UMIN\d{9}|JapicCTI[\-\w]{4,}"
    r"|JPRN[\-\w]{4,}|EudraCT[\-\w]{4,}|CTR\d{4,}|KCT\d{4,}|IRCT[\-\w]{4,})\b"
)
TRAILING_QUALIFIER_RE = re.compile(r"[（(]([^（）()]*)[)）]\s*$")
LEADING_TIMEPOINT_RE = re.compile(
    r"^(?:第\s*)?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)*\s*"
    r"(?:个月|月|周|年|天|小时|-?months?|-?weeks?|-?years?|-?days?|-?hours?)"
    r"(?![-A-Za-z0-9_])\s*[-—·、,，:：]?\s*",
    re.IGNORECASE,
)
TRIVIAL_QUALIFIER_RE = re.compile(r"^[\s%％、,，;；:：nN=+＋\-−~～≈]*$")
# `study` values that carry no trial identity (seen in early ledgers): never use as a column header.
PLACEHOLDER_STUDY_LABELS = {
    "see records",
    "see record",
    "see the records",
    "n/a",
    "na",
    "unknown",
    "none",
    "未报告",
    "-",
    "—",
}
MAX_QUALIFIER_LEN = 40
EMPTY_CELL = "—"

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


def _facts_by_ref(records: list[dict[str, str]], facts: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {record["ref"]: [] for record in records}
    for fact in facts:
        grouped[fact["ref"]].append(fact)
    return grouped


def _column_keys(
    records: list[dict[str, str]], facts_by_ref: dict[str, list[dict[str, str]]]
) -> tuple[list[str], dict[str, str]]:
    """Ordered appendix column keys plus the ref → key map that builds them."""
    keys: list[str] = []
    ref_to_key: dict[str, str] = {}
    for record in records:
        key = _column_key(record, _study_labels([record], facts_by_ref))
        ref_to_key[record["ref"]] = key
        if key not in keys:
            keys.append(key)
    return keys, ref_to_key


def _appendix_columns(records: list[dict[str, str]], facts: list[dict[str, str]]) -> list[str]:
    """Column keys of the appendix: one column per trial (same-trial disclosures merged)."""
    return _column_keys(records, _facts_by_ref(records, facts))[0]


def _appendix_body_rows(appendix: str) -> list[str]:
    """Markdown table rows of the appendix, excluding the header and separator rows."""
    rows = [
        line
        for line in appendix.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    ]
    return rows[1:]


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"missing JSON file: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read UTF-8 JSON {path}: {exc}") from exc


def _strip_entity_links(value: str) -> str:
    """Drop the removed entity-anchor syntax, keeping the display name it wrapped.

    Entity inline references were removed in v0.16. A ledger written by an older run may still
    carry `[依沃西单抗](entity:drug:12483)`; the appendix must show the plain name, and the report
    must not deliver `entity:` syntax at all.
    """
    return re.sub(r"\[([^\[\]]*)\]\(entity:[^)\s]*\)", r"\1", value)


def _validate_string_fields(
    item: Any,
    fields: tuple[str, ...],
    label: str,
    *,
    allow_empty: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
) -> None:
    if not isinstance(item, dict):
        raise ValidationError(f"{label} must be an object")
    missing = [field for field in fields if field not in item and field not in optional]
    extra = sorted(set(item) - set(fields))
    if missing:
        raise ValidationError(f"{label} missing fields: {', '.join(missing)}")
    if extra:
        raise ValidationError(f"{label} has unknown fields: {', '.join(extra)}")
    for field in fields:
        if field not in item:
            continue
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
        _validate_string_fields(
            record, (*RECORD_FIELDS, *RECORD_OPTIONAL_FIELDS), f"records[{index}]", optional=RECORD_OPTIONAL_FIELDS
        )
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

    # Display text must never carry the removed entity-anchor syntax; `quote`/`source_file` stay
    # byte-exact because they are matched against the source evidence.
    for item in (*record_values, *fact_values):
        for field, value in item.items():
            if isinstance(value, str) and field not in ("quote", "source_file"):
                item[field] = _strip_entity_links(value)

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


def _segment(kind: str) -> str:
    """Map a fact kind onto one of the fixed appendix segments."""
    value = _normalise_text(kind)
    upper = value.upper()
    if value.startswith(("设计", "试验设计")) or upper.startswith("DESIGN"):
        return "试验设计"
    if value.startswith("结论") or upper.startswith("CONCLUSION"):
        return "试验结论"
    if value.startswith(("安全", "耐受")) or upper.startswith(("SAFETY", "TOLERAB")):
        return "安全性"
    if upper.startswith("PRO") or value.startswith(("生活质量", "症状", "患者报告")):
        return "PRO"
    if upper.startswith(("PK", "PD", "TK")) or value.startswith(("暴露", "药代", "药动")):
        return "PK/PD"
    if value.startswith(("有效性", "疗效", "缓解", "生存", "生物标志物", "亚组", "应答")) or upper.startswith(
        ("EFFICACY", "EFFECTIVENESS", "RESPONSE", "ENDPOINT")
    ):
        return "有效性"
    return "其他"


def _endpoint_row(endpoint: str) -> tuple[str, list[str]]:
    """Split an endpoint label into its aligned row label plus fine-grained qualifiers.

    ``16 个月 ORR`` becomes row ``ORR`` with qualifier ``16 个月`` and ``中位 PFS（IRRC）``
    becomes row ``中位 PFS`` with qualifier ``IRRC``, so comparable endpoints align on one
    row while their timepoint/definition detail stays inside the cell.
    """
    label = _normalise_text(endpoint)
    qualifiers: list[str] = []
    while True:
        match = TRAILING_QUALIFIER_RE.search(label)
        if not match:
            break
        inner = match.group(1).strip()
        prefix = label[: match.start()]
        if TRIVIAL_QUALIFIER_RE.fullmatch(inner):
            label = prefix.strip()
            continue
        # Only peel a trailing parenthetical that is a qualifier, not part of a name:
        # `Lp(a)` stays glued in the label, while `（IRRC）` / `（OS）` / `（中位）` move into the cell.
        # Glue means a short Latin fragment completing a Latin token (`Lp(a)`), not any
        # parenthetical that happens to follow one (`基线 OxPL（中位）` is a qualifier).
        glued_to_word = (
            bool(prefix)
            and prefix[-1].isascii()
            and prefix[-1].isalnum()
            and re.fullmatch(r"[A-Za-z0-9]{1,2}", inner) is not None
        )
        if glued_to_word or len(inner) > MAX_QUALIFIER_LEN or not prefix.strip():
            break
        qualifiers.insert(0, inner)
        label = prefix.strip()
    match = LEADING_TIMEPOINT_RE.match(label)
    if match and len(match.group(0).strip()) < len(label):
        qualifiers.insert(0, match.group(0).strip().rstrip("-—·、,，:："))
        label = label[match.end() :].strip()
    return (label or _normalise_text(endpoint), qualifiers)


def _registration_ids(record: dict[str, str]) -> list[str]:
    """Registry identifiers (NCT/ChiCTR/…) stated in the disclosure's trial key, identity or title."""
    text = " ".join((record.get("trial", ""), record.get("identity", ""), record.get("title", "")))
    return sorted({match.group(0).upper() for match in REGISTRATION_RE.finditer(text)})


def _trial_key(value: str) -> str:
    """Normalise a record's `trial` merge key: `HARMONi-6`, `HARMONi-6（NCT05840016）` and
    `harmoni-6 ` all collapse to one key, so a trial's disclosures share one appendix column."""
    key = _normalise_text(value).strip().casefold()
    while True:
        match = TRAILING_QUALIFIER_RE.search(key)
        if not match:
            break
        key = key[: match.start()].strip()
    return re.sub(r"[\s　·、,，:：;；/\\|（）()\[\]【】]+", "", key)


def _study_key(study: str) -> str:
    """Normalise a ledger `study` label so one trial's disclosures merge into one column."""
    return _trial_key(study)


def _column_key(record: dict[str, str], studies: list[str]) -> str:
    """Merge one trial's disclosures into one column.

    Key order: the record's explicit `trial` key, else a registry identifier stated in the
    identity/title, else the normalised `study` label its facts carry, else the record itself.
    
    Names alone never merge two records: a shared generic name (“Study 301”) would otherwise
    invent a trial identity, so the fallbacks stay identifier-based.
    """
    key = _trial_key(record.get("trial", ""))
    if key:
        return "trial:" + key
    registration_ids = _registration_ids(record)
    if registration_ids:
        return "trial:" + "|".join(registration_ids)
    for study in studies:
        key = _study_key(study)
        if key:
            return "study:" + key
    return "ref:" + record["ref"]


def _most_common(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts, key=lambda value: (counts[value], -len(value))) if counts else ""


def _study_labels(column_records: list[dict[str, str]], facts_by_ref: dict[str, list[dict[str, str]]]) -> list[str]:
    """Non-placeholder `study` labels carried by the column's facts, in encounter order."""
    labels: list[str] = []
    for record in column_records:
        for fact in facts_by_ref.get(record["ref"], []):
            study = _normalise_text(fact["study"]).strip()
            if study and study.casefold() not in PLACEHOLDER_STUDY_LABELS:
                labels.append(study)
    return labels


def _column_label(column_records: list[dict[str, str]], facts_by_ref: dict[str, list[dict[str, str]]]) -> str:
    """Prefer the study label its facts carry, then the trial key, then the registry id,
    then the first segment of the identity text."""
    label = _most_common(_study_labels(column_records, facts_by_ref))
    if label:
        return label
    trials = [_normalise_text(record.get("trial", "")).strip() for record in column_records]
    label = _most_common([value for value in trials if value])
    if label:
        return label
    registration_ids = [rid for record in column_records for rid in _registration_ids(record)]
    label = _most_common(registration_ids)
    if label:
        return label
    return _identity_name(column_records[0]["identity"])


def _identity_name(identity: str) -> str:
    """Trial name is the first segment of an identity line (`LUX-Lung 8｜二线鳞状 NSCLC｜…`)."""
    value = _normalise_text(identity).strip()
    for separator in ("｜", "|", "；", ";", "、", "，"):
        if separator in value:
            value = value.split(separator, 1)[0].strip()
            break
    return value[:40]


def _fact_line(fact: dict[str, str], endpoint_qualifiers: list[str]) -> str:
    parts: list[str] = []
    for field in ("arm", "timepoint", "assessment", "population"):
        value = _normalise_text(fact[field])
        if value and value not in {"-", "—", "未报告", "不适用"} and value not in parts:
            parts.append(value)
    for value in endpoint_qualifiers:
        if value and value not in parts:
            parts.append(value)
    line = f"{'·'.join(parts)}：" if parts else ""
    line += f"{fact['value']} {fact['unit']}".strip()
    if fact["statistics"]:
        line += f"（{fact['statistics']}）"
    return line + "{{" + fact["ref"] + "}}"


def _record_cell(column_records: list[dict[str, str]], field: str) -> str:
    """One line per disclosure, keeping each line bound to its own source marker."""
    lines: list[str] = []
    seen: set[str] = set()
    for record in column_records:
        value = _normalise_text(record[field])
        if value and value not in seen:
            seen.add(value)
            lines.append(f"{value}{{{{{record['ref']}}}}}")
    return "<br>".join(lines)


def _appendix(records: list[dict[str, str]], facts: list[dict[str, str]]) -> str:
    """Render the trial-as-columns alignment matrix and prove every fact entered it."""
    record_order = {record["ref"]: index for index, record in enumerate(records)}
    facts_by_ref = _facts_by_ref(records, facts)

    keys, ref_to_key = _column_keys(records, facts_by_ref)
    column_index = {key: index for index, key in enumerate(keys)}
    columns: list[list[dict[str, str]]] = [[] for _ in keys]
    for record in records:
        columns[column_index[ref_to_key[record["ref"]]]].append(record)
    labels = [_column_label(column, facts_by_ref) for column in columns]
    # Two different trials may share a display name: disambiguate those headers by registry id.
    duplicate_labels = {label for label in labels if labels.count(label) > 1}
    for index, (label, column) in enumerate(zip(labels, columns)):
        if label not in duplicate_labels:
            continue
        identifiers = sorted({rid for record in column for rid in _registration_ids(record)})
        if identifiers:
            labels[index] = f"{label}（{'/'.join(identifiers)}）"

    column_of_ref = {record["ref"]: column_index[ref_to_key[record["ref"]]] for record in records}
    blocks: dict[str, list[tuple[str, list[str]]]] = {segment: [] for segment in SEGMENT_ORDER}
    placed: set[str] = set()

    def add_row(segment: str, label: str, cells: list[list[str] | str]) -> None:
        blocks[segment].append(
            (
                label,
                ["<br>".join(dict.fromkeys(cell if isinstance(cell, list) else [cell])) for cell in cells],
            )
        )

    # 试验设计 / 试验结论 blocks come from the record objects, one line per disclosure.
    for label, field in DESIGN_ROWS:
        add_row("试验设计", label, [_record_cell(column, field) for column in columns])
    version_cells: list[list[str]] = []
    for column in columns:
        cell: list[str] = []
        seen_versions: set[str] = set()
        for record in column:
            for fact in facts_by_ref[record["ref"]]:
                version = _normalise_text(fact["version"])
                if version and version not in seen_versions:
                    seen_versions.add(version)
                    cell.append(f"{version}{{{{{fact['ref']}}}}}")
        version_cells.append(cell)
    add_row("试验设计", "披露版本 / 数据截止", version_cells)
    add_row("试验结论", "披露级结论", [_record_cell(column, "conclusion") for column in columns])

    # Endpoint rows: aligned by (segment, parent endpoint) across trials.
    grouped: dict[tuple[str, str], list[tuple[int, int, dict[str, str], list[str]]]] = {}
    for index, fact in enumerate(facts):
        label, qualifiers = _endpoint_row(fact["endpoint"])
        grouped.setdefault((_segment(fact["kind"]), label), []).append(
            (record_order[fact["ref"]], index, fact, qualifiers)
        )

    for segment in SEGMENT_ORDER:
        rows = sorted(
            (key for key in grouped if key[0] == segment),
            key=lambda key: (
                -len({item[2]["ref"] for item in grouped[key]}),
                min(item[0] for item in grouped[key]),
                min(item[1] for item in grouped[key]),
                key[1],
            ),
        )
        for key in rows:
            cells: list[list[str]] = [[] for _ in columns]
            for _, _, fact, qualifiers in grouped[key]:
                cells[column_of_ref[fact["ref"]]].append(_fact_line(fact, qualifiers))
                placed.add(fact["id"])
            add_row(segment, key[1], cells)

    missing = [fact["id"] for fact in facts if fact["id"] not in placed]
    if missing:
        raise ValidationError("appendix dropped ledger facts: " + ", ".join(sorted(missing)))

    if not facts:
        raise ValidationError("ledger has no facts to render")

    header = "| 维度 | " + " | ".join(
        label + (f"（{len(column)} 条披露）" if len(column) > 1 else "") for label, column in zip(labels, columns)
    ) + " |"
    parts = [
        APPENDIX_TITLE,
        "",
        APPENDIX_INTRO,
        "",
        header,
        "| --- |" + " --- |" * len(columns),
    ]
    for segment in SEGMENT_ORDER:
        if not blocks[segment]:
            continue
        parts.append("| **" + segment + "** |" + "  |" * len(columns))
        for label, cells in blocks[segment]:
            parts.append(
                "| "
                + _normalise_markdown(label)
                + " | "
                + " | ".join(_normalise_markdown(cell) if cell else EMPTY_CELL for cell in cells)
                + " |"
            )
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
        if ENTITY_LINK_RE.search(output):
            raise ValidationError(
                "entity inline references are no longer part of the report format (removed in v0.16): "
                "write the plain source-supported name instead"
            )
        if not output.strip():
            raise ValidationError("refusing to write an empty output")

        audit.update(
            {
                "records": len(records),
                "facts": len(facts),
                "appendix_trials": len(_appendix_columns(records, facts)),
                "records_without_trial_key": sum(1 for record in records if not record.get("trial", "").strip()),
                "appendix_rows": len(_appendix_body_rows(appendix)),
                "appendix_cells_filled": sum(
                    1
                    for row in _appendix_body_rows(appendix)
                    for cell in row.strip("| ").split(" | ")
                    if cell.strip() not in ("", EMPTY_CELL)
                ),
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
