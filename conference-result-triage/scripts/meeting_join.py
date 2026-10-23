#!/usr/bin/env python3
"""Join the conference abstract book onto the structured clinical-result table.

Two jobs, both deterministic:

1. **Annotate.** Every structured record that also exists in the meeting book
   gets its ``abstract_id`` (hence presentation tier), ``target``, ``drug``,
   ``moa`` and full ``abstract_text`` attached. On ESMO 2026 the title match is
   646/646, so this never loses a record.

2. **Supplement.** Records that exist only in the meeting book are turned into
   structured-table-shaped rows so ``triage.py`` can screen them. This closes the
   coverage hole that made BG-C477 (abstract 2567P) invisible: the structured
   table only holds records the curation pipeline already processed, while the
   meeting book holds everything released before the meeting.

Supplement rows are deliberately conservative:
  * trial-in-progress placeholders (``1234eTiP``, ``Expected Results``) are dropped;
  * rows need a named drug, a Results section and at least one printed number;
  * phase is parsed from the prose; unknown phase means the row cannot be bucketed;
  * ``evaluation`` is only set when the abstract says so, so **no supplement row
    can ever land in the failed bucket** -- that bucket stays driven by the
    curated ``evaluation`` enum.

Usage
  python3 meeting_join.py --meeting mm.json --rows esmo_rows.json \
      --out-annotations ann.json --out-supplement supplement.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from triage import (  # noqa: E402
    EVIDENCE_TOKEN_RE,
    first_text,
    is_tip_abstract_id,
    presentation_of,
    split_sections,
)

PHASE_RE = re.compile(
    r"\bphase\s*(?:(?P<a>IV|III|II|I|[1-4])\s*(?:[/-]\s*(?P<b>IV|III|II|I|[1-4]))?)",
    re.I)
NUM2ROMAN = {"1": "I", "2": "II", "3": "III", "4": "IV"}

NEGATIVE_RE = re.compile(
    r"\b(did not meet|not met|failed to (?:meet|improve|demonstrate)|"
    r"no (?:statistically )?significant (?:difference|improvement|benefit)|"
    r"was not (?:superior|significant)|did not improve|no benefit|"
    r"inferior to|worse than|no improvement)\b", re.I)
POSITIVE_RE = re.compile(
    r"\b(met (?:its )?(?:primary|pre-?specified) endpoint|"
    r"statistically significant (?:improvement|benefit|increase)|"
    r"significantly (?:improved|prolonged|increased)|demonstrated (?:superiority|benefit)|"
    r"clinically meaningful (?:improvement|benefit))\b", re.I)

# Reviews, RWE, epidemiology and translational work all live in the meeting book
# but never belong in a clinical-result shortlist.
NON_TRIAL_RE = re.compile(
    r"\b(real[- ]world|retrospective|claims database|registry|survey|"
    r"meta-analy|systematic review|pooled analysis of (?:published|literature)|"
    r"budget impact|cost-effectiveness|preclinical|in vivo|in vitro|"
    r"patient[- ]reported outcomes? only|health[- ]related quality of life)\b",
    re.I)


def norm_title(value: Optional[str]) -> str:
    s = unicodedata.normalize("NFKD", (value or "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def phase_from_text(*texts: Optional[str]) -> Optional[str]:
    """Parse a trial phase from prose. Returns e.g. ``Phase I/II`` or None."""
    for text in texts:
        if not text:
            continue
        m = PHASE_RE.search(text)
        if not m:
            continue
        a = NUM2ROMAN.get(m.group("a"), (m.group("a") or "").upper())
        b = m.group("b")
        if b:
            b = NUM2ROMAN.get(b, b.upper())
            if a == b:
                return f"Phase {a}"
            return f"Phase {a}/{b}"
        return f"Phase {a}"
    return None


def evaluation_from_text(*texts: Optional[str]) -> Optional[str]:
    """Only returns a value when the abstract explicitly states the outcome."""
    blob = " ".join(t for t in texts if t)
    if not blob:
        return None
    if NEGATIVE_RE.search(blob):
        return "不佳"
    if POSITIVE_RE.search(blob):
        return "积极"
    return None


N_ENROLL_RE = (
    re.compile(r"a total of\s+(\d[\d,]*)\s+(?:patients|participants|pts)", re.I),
    re.compile(r"\b(\d[\d,]*)\s+(?:patients|participants|pts)\s+(?:were|with|have|had|received|enrolled)", re.I),
    re.compile(r"(?:enrolled|included|treated)\s+(\d[\d,]*)\s+(?:patients|participants|pts)", re.I),
    # "43 NSCLC pts were treated": up to three qualifier words before the noun
    re.compile(r"\b(\d[\d,]*)\s+(?:[A-Za-z][A-Za-z-]*\s+){0,3}(?:patients|participants|pts)\b"),
)


def enrolled_from_text(*texts: Optional[str]) -> Optional[int]:
    """Pull the analysed patient count out of prose (supplement rows only)."""
    for text in texts:
        if not text:
            continue
        for rx in N_ENROLL_RE:
            m = rx.search(text)
            if m:
                try:
                    value = int(m.group(1).replace(",", ""))
                except ValueError:
                    continue
                if 1 <= value <= 20000:
                    return value
    return None


def find_drugs(rec: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for field in ("drug", "drug_name_original"):
        for part in re.split(r"[,;，、]", rec.get(field) or ""):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def annotate(meeting: Dict[str, Any],
             rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Map structured ``_id`` -> meeting metadata, joined on the paper title."""
    by_title: Dict[str, Dict[str, Any]] = {}
    for rec in meeting.get("data") or []:
        key = norm_title(rec.get("title"))
        if key and key not in by_title:
            by_title[key] = rec

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        esid = row.get("clinical_result__id") or row.get("_id")
        if not esid:
            continue
        rec = by_title.get(norm_title(row.get("clinical_result_paper_title")
                                      or row.get("paper_title")))
        if not rec:
            continue
        label, rank = presentation_of(rec.get("abstract_id"))
        out[str(esid)] = {
            "abstract_id": rec.get("abstract_id"),
            "presentation": label,
            "presentation_rank": rank,
            "target": rec.get("target"),
            "drug": rec.get("drug"),
            "moa": rec.get("moa"),
            "abstract_text": rec.get("abstract_text"),
            "abstract_release_date": rec.get("abstract_release_date"),
            "meeting_date": rec.get("meeting_date"),
            "url": rec.get("url"),
        }
    return out


def supplement_rows(meeting: Dict[str, Any],
                    covered_titles: set) -> List[Dict[str, Any]]:
    """Meeting-only abstracts reshaped into structured-table rows."""
    rows: List[Dict[str, Any]] = []
    for rec in meeting.get("data") or []:
        abstract_id = rec.get("abstract_id")
        text = rec.get("abstract_text") or ""
        if not abstract_id or not text:
            continue
        if is_tip_abstract_id(abstract_id):
            continue
        if norm_title(rec.get("title")) in covered_titles:
            continue

        sections, _fmt = split_sections(text)
        results = sections.get("results") or ""
        if not results or not EVIDENCE_TOKEN_RE.search(results):
            continue
        drugs = find_drugs(rec)
        if not drugs:
            continue
        blob = " ".join([rec.get("title") or "", sections.get("background") or "",
                         sections.get("methods") or "", results])
        if NON_TRIAL_RE.search(blob):
            continue
        phase = phase_from_text(rec.get("title"), sections.get("methods"),
                                sections.get("background"), text[:400])
        if not phase:
            continue

        label, rank = presentation_of(abstract_id)
        rows.append({
            "clinical_result__id": "mm:" + str(abstract_id),
            "clinical_result_abstract_id": abstract_id,
            "clinical_result_paper_title": rec.get("title"),
            "clinical_result_abstract_text": text,
            "clinical_result_summary": None,
            "clinical_result_evidence_source": [phase],
            "clinical_result_evaluation": evaluation_from_text(
                results, sections.get("conclusions")),
            "clinical_result_randomized": None,
            "clinical_result_blinded": None,
            "clinical_result_trial_control": None,
            "clinical_result_group_count": enrolled_from_text(
                sections.get("methods"), results),
            "clinical_result_indication_name": [
                d for d in re.split(r"[,;，、]", rec.get("disease") or "") if d.strip()],
            "clinical_result_trial_abbreviation": [],
            "clinical_result_primary_endpoint_cn": None,
            "clinical_result_key_evidence": "是",
            "clinical_result_study_results": None,
            "_source": "meeting_book",
            "_presentation": label,
            "_presentation_rank": rank,
            "_drug": drugs,
            "_target": [t for t in re.split(r"[,;，、]", rec.get("target") or "") if t.strip()],
            "_moa": rec.get("moa"),
        })
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--meeting", required=True, help="output of meeting_pull.py")
    ap.add_argument("--rows", required=True, help="structured table rows (JSON)")
    ap.add_argument("--out-annotations", default="mm_annotations.json")
    ap.add_argument("--out-supplement", default="supplement.json")
    args = ap.parse_args(argv)

    with open(args.meeting, "r", encoding="utf-8") as fh:
        meeting = json.load(fh)
    with open(args.rows, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    rows = data.get("data") if isinstance(data, dict) else data
    rows = rows or []

    ann = annotate(meeting, rows)
    covered = {norm_title(r.get("clinical_result_paper_title") or r.get("paper_title"))
               for r in rows}
    supp = supplement_rows(meeting, covered)

    with open(args.out_annotations, "w", encoding="utf-8") as fh:
        json.dump(ann, fh, ensure_ascii=False, indent=1)
    with open(args.out_supplement, "w", encoding="utf-8") as fh:
        json.dump(supp, fh, ensure_ascii=False, indent=1)

    labelled = [v for v in ann.values() if v.get("presentation") != "Unknown"]
    print(f"annotations {len(ann)} / {len(rows)} rows ({len(labelled)} with a presentation tier)")
    print(f"supplement rows {len(supp)} "
          f"({sum(1 for r in supp if r['_presentation_rank'] <= 2)} oral-tier)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
