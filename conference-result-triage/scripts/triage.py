#!/usr/bin/env python3
"""Conference clinical-result triage: mechanical shortlisting only.

Deliberately does NOT score or rank records with heuristics. Field testing on
ESMO 2026 showed that rule-based scoring produces false precision: safety rows
outrank efficacy rows, `PR count = 3 subjects` is read as a response rate, and
most `study_results` rows carry no p-value or hazard ratio at all. Judgment is
left to the model, which reads ``abstract_text`` / ``summary``.

What this script does (all deterministic, no domain guessing):
  1. collapse duplicate rows to one record per esid;
  2. exclude non-trial evidence sources (前瞻性研究 / 回顾性研究 /
     真实世界研究 / 汇总分析 / Not Applicable / unknown);
  3. split the remainder into early / pivotal / failed pools;
  4. attach a machine-read evidence digest (best efficacy line, endpoint calls)
     so the model does not have to re-parse study_results by hand;
  5. emit review batches ready for the model to read.

Usage
  python3 triage.py rows.json --out-json pool.json --out-csv pool.csv \
      --batches review.jsonl --batch-size 40
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

BUCKETS = ("early", "pivotal", "failed")
BUCKET_TITLES = {"early": "早期机会", "pivotal": "重磅 II/III 期", "failed": "失败/终止"}

EARLY_PHASES = {"Phase I", "Phase I/II"}
LATE_PHASES = {"Phase II", "Phase II/III", "Phase III", "Phase IV"}
TRIAL_PHASES = EARLY_PHASES | LATE_PHASES
FAIL_EVALUATIONS = {"不佳", "终止"}

NON_TRIAL_SOURCES = {
    "前瞻性研究", "回顾性研究", "真实世界研究", "汇总分析", "Not Applicable", "其他",
}

PREFIXES = ("clinical_result.", "clinical_result_")

RESPONSE_HINTS = (
    "response rate", "objective response", "overall response", "orr", "dcr",
    "disease control", "clinical benefit", "pathological complete", "pcr",
)
COUNT_UNITS = ("subjects", "patients", "events", "count")
SAFETY_HINTS = (
    "toxicity", "adverse", "death", "dlt", "dose-limiting", "dose limiting",
    "discontinuation", "dose reduction", "safety", "tolerability",
    # AE-family wording: the most common way a safety row slips into the
    # efficacy pool (measured: 'Grade >=3 TEAE', 'TRAE', 'grade 3/4' labels)
    "teae", "trae", "treatment-emergent", "treatment emergent", "ae of",
    "any-grade", "any grade", "grade >=3", "grade>=3", "grade \u2265 3", "grade \u22653",
    "\u22653\u7ea7", "\u22653\u7ea7", "3\u7ea7\u4ee5\u4e0a", "serious adverse", "sae",
)

ENDPOINT_PHRASES = (
    (("pathological complete", "pcr"), "病理完全缓解率"),
    (("objective response", "orr", "overall response"), "客观缓解率"),
    (("disease control", "dcr"), "疾病控制率"),
    (("clinical benefit",), "临床获益率"),
    (("duration of response", "dor"), "缓解持续时间"),
    (("event-free survival", "efs"), "无事件生存期"),
    (("progression-free survival", "pfs"), "无进展生存期"),
    (("disease-free survival", "dfs"), "无病生存期"),
    (("overall survival", "os"), "总生存期"),
    (("complete response",), "完全缓解率"),
    (("partial response",), "部分缓解率"),
    (("recurrence",), "复发率"),
    (("hazard ratio", "hr"), "风险比"),
)
# Data-type cues: ESMO/ASCO abstracts are often NOT first reports. A long-term
# follow-up or a post-hoc subgroup is worth far less than a primary readout, so
# we tag it for the reviewer instead of silently ranking it like new data.
DATA_TYPE_RULES = (
    ("亚组/二次分析", re.compile(
        r"\b(post[- ]hoc|ad hoc|subgroup analys|secondary analys|exploratory analys|"
        r"pooled analys|biomarker analys|patient[- ]reported outcome)", re.I)),
    ("更新/长期随访", re.compile(
        r"\b(updated?|update of|long[- ]term|final analys|extended follow[- ]?up|"
        r"additional follow[- ]?up|end[- ]of[- ]trial|now report|previously (reported|presented|"
        r"shown)|with (longer|extended|additional) follow|\d[- ](yr|year)s? (follow|data)|"
        r"sustained (benefit|efficacy|pfs|os))", re.I)),
    ("首次公布", re.compile(
        r"\b(first[- ]in[- ]human|first report|first phase|primary results|primary analysis|"
        r"prespecified .{0,30}analysis|interim analysis|we report (the )?(primary|first)|"
        r"we present (the )?(primary|first|prespecified)|first disclosure)", re.I)),
    ("首次公布", re.compile(
        r"\b(here,? we (report|present|show|provide)|we (report|present) (the )?results)", re.I)),
)
DATA_TYPE_ORDER = ("亚组/二次分析", "更新/长期随访", "首次公布")


NOISY_LABEL = re.compile(
    r"follow-up|cutoff|data cut|population|subgroup|review|assessed|analysis set", re.I
)
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


# --------------------------------------------------------------------------- #
# normalisation
# --------------------------------------------------------------------------- #
def norm_key(key: str) -> str:
    for p in PREFIXES:
        if key.startswith(p):
            return key[len(p):]
    return key


def first(value: Any) -> Any:
    if isinstance(value, list):
        for item in value:
            if item not in (None, "", [], {}):
                return item
        return None
    return value


def first_text(value: Any) -> Optional[str]:
    v = first(value)
    if isinstance(v, dict):
        v = v.get("text") or v.get("name")
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def as_text_list(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    out: List[str] = []
    for item in value:
        t = first_text(item)
        if t:
            out.append(t)
    return out


def flat_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    row = {norm_key(k): v for k, v in raw.items()}
    if "_id" not in row and "id" in row:
        row["_id"] = row["id"]
    return row


def parse_num(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"not reached", "nr", "ne", "n/a", "na", "-", "none", "null"}:
        return None
    m = NUM_RE.search(text.replace(",", ""))
    return float(m.group(0)) if m else None


def parse_p(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    m = re.search(r"([<>]=?|=)?\s*(\d*\.?\d+)", text)
    if not m:
        return None
    num = float(m.group(2))
    if m.group(1) == "<":
        return num / 2 if num else 0.0001
    return num


def parse_n(value: Any) -> Optional[int]:
    t = first_text(value)
    if not t:
        return None
    m = re.search(r"\d[\d,]*", t)
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return None


def phase_of(row: Dict[str, Any]) -> Optional[str]:
    return first_text(row.get("evidence_source"))


def evaluation_of(row: Dict[str, Any]) -> Optional[str]:
    return first_text(row.get("evaluation"))


# --------------------------------------------------------------------------- #
# study_results digest (presentation only -- never used to rank)
# --------------------------------------------------------------------------- #
def study_results(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    sr = row.get("study_results")
    return [x for x in sr if isinstance(x, dict)] if isinstance(sr, list) else []


def effective_results(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for item in study_results(row):
        attr = first_text(item.get("endpoint_attribute"))
        if attr and attr != "有效性":
            continue
        out.append(item)
    return out


def is_safety_label(label: Optional[str]) -> bool:
    low = (label or "").lower()
    return any(h in low for h in SAFETY_HINTS)


def signal_quality(item: Dict[str, Any]) -> Tuple[bool, bool, bool]:
    label = str(item.get("endpoint_label") or "").lower()
    unit = str(item.get("result_unit") or "").lower()
    pct = "%" in unit or "percentage" in label or "rate" in label
    resp = any(h in label for h in RESPONSE_HINTS)
    count = any(u in unit for u in COUNT_UNITS) or "count" in label
    return (resp and pct, pct, not count)


def clean_label(label: Optional[str], row: Dict[str, Any]) -> Optional[str]:
    cn = as_text_list(row.get("primary_endpoint_cn"))
    if label:
        low = label.lower()
        for keys, name in ENDPOINT_PHRASES:
            if any(k in low for k in keys):
                return name
        head = label.split("|")[0].strip(" ;")
        if not (len(head) > 60 or NOISY_LABEL.search(head)):
            return head
    return cn[0] if cn else None


def best_efficacy_line(row: Dict[str, Any]) -> Dict[str, Any]:
    pool = [
        x for x in effective_results(row)
        if not is_safety_label(" ".join(
            str(v) for v in (x.get("endpoint_label"), x.get("name")) if v))
    ]
    if not pool:
        return {}
    pool.sort(key=signal_quality, reverse=True)
    for item in pool:
        if not signal_quality(item)[2]:
            continue
        val = parse_num(item.get("result"))
        compare = first_text(item.get("compare_result"))
        if val is None and not compare:
            continue
        label = clean_label(first_text(item.get("endpoint_label")), row)
        if not label:
            continue
        return {
            "endpoint": label,
            "endpoint_raw": first_text(item.get("endpoint_label")),
            "value": val,
            "unit": first_text(item.get("result_unit")),
            "compare": compare,
            "p": first_text(item.get("p_value")),
            "hr": first_text(item.get("hazard_ratio")),
            "hr_ci": first_text(item.get("hazard_ratio_ci")),
        }
    return {}


def data_type_of(row: Dict[str, Any]) -> str:
    """Tag whether this abstract is new data, an update, or a subgroup.

    Rule-based and deliberately conservative: when nothing matches we say
    "未判定" instead of guessing, and the reviewer confirms against the text.
    """
    text = " ".join(filter(None, [first_text(row.get("abstract_text")),
                                  first_text(row.get("summary"))]))
    if not text:
        return "未判定"
    head = text[:1200]
    for label, pattern in DATA_TYPE_RULES:
        if pattern.search(head):
            return label
    return "未判定"


def endpoint_call(row: Dict[str, Any]) -> Dict[str, Any]:
    """Machine reading of the primary-endpoint verdict. Never authoritative."""
    prim = [x for x in effective_results(row) if str(x.get("endpoint_type")) == "主要终点"]
    rel = [x for x in effective_results(row) if str(x.get("arm_type")) == "relative"]
    p_values = []
    hr_ci_top = None
    for item in prim + rel:
        p = parse_p(item.get("p_value") or item.get("outcome_p_value"))
        if p is not None:
            p_values.append(p)
        ci = first_text(item.get("hazard_ratio_ci"))
        if ci:
            nums = [parse_num(x) for x in re.split(r"[-,–~]", ci)]
            nums = [x for x in nums if x is not None]
            if len(nums) >= 2:
                hr_ci_top = max(nums)
    if p_values:
        return {
            "verdict": "met" if min(p_values) < 0.05 else "missed",
            "basis": f"min p={min(p_values):g}",
        }
    if hr_ci_top is not None:
        return {"verdict": "不完整", "basis": f"HR CI 上限 {hr_ci_top:g}"}
    return {"verdict": "无法判断", "basis": "主要终点无 p/HR"}


# --------------------------------------------------------------------------- #
# pools
# --------------------------------------------------------------------------- #
def excluded_reason(row: Dict[str, Any]) -> Optional[str]:
    phase = phase_of(row)
    if phase in TRIAL_PHASES:
        return None
    if phase in NON_TRIAL_SOURCES:
        return phase
    return "未知证据类型" if phase is None else phase


def bucket_of(row: Dict[str, Any]) -> Optional[str]:
    if excluded_reason(row):
        return None
    ev = evaluation_of(row)
    phase = phase_of(row)
    if ev in FAIL_EVALUATIONS:
        return "failed"
    if phase in LATE_PHASES:
        return "pivotal"
    if phase in EARLY_PHASES:
        return "early"
    return None


def dedupe_key(row: Dict[str, Any]) -> str:
    trial = first_text(row.get("trial_abbreviation"))
    return "trial:" + trial.upper() if trial else "esid:" + str(row.get("_id"))


def load_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            data = data["data"]
        elif isinstance(data.get("result"), dict):
            data = data["result"].get("data") or []
        elif "rows" in data:
            data = data["rows"]
    if not isinstance(data, list):
        raise SystemExit("input must be a JSON array or {data|rows: [...]}")
    return [flat_row(r) for r in data if isinstance(r, dict)]


def build_pools(
    rows: Iterable[Dict[str, Any]], per_bucket: Optional[int] = None
) -> Dict[str, Any]:
    rows = list(rows)
    by_esid: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        esid = str(row.get("_id") or "")
        if not esid:
            continue
        merged = by_esid.setdefault(esid, {})
        for k, v in row.items():
            if v not in (None, "", [], {}):
                merged.setdefault(k, v)

    excluded: Counter = Counter()
    pools: Dict[str, Dict[str, Dict[str, Any]]] = {b: {} for b in BUCKETS}
    for row in by_esid.values():
        reason = excluded_reason(row)
        if reason:
            excluded[reason] += 1
            continue
        bucket = bucket_of(row)
        if bucket is None:
            excluded["无法归类"] += 1
            continue
        entry = {
            "esid": row.get("_id"),
            "trial": first_text(row.get("trial_abbreviation")),
            "indication": as_text_list(row.get("indication_name")),
            "phase": phase_of(row),
            "evaluation": evaluation_of(row),
            "n": parse_n(row.get("group_count")),
            "key_evidence": first_text(row.get("key_evidence")),
            "primary_endpoint": as_text_list(row.get("primary_endpoint_cn")),
            "randomized": first_text(row.get("randomized")),
            "blinded": first_text(row.get("blinded")),
            "trial_control": first_text(row.get("trial_control")),
            "title": first_text(row.get("paper_title")),
            "summary": first_text(row.get("summary")),
            "abstract_text": first_text(row.get("abstract_text")),
            "machine_signal": best_efficacy_line(row),
            "machine_endpoint_call": endpoint_call(row),
            "data_type": data_type_of(row),
            "has_study_results": bool(study_results(row)),
        }
        key = dedupe_key(row)
        prev = pools[bucket].get(key)
        # deterministic tie-break: prefer the record that carries study_results,
        # then the larger sample. No clinical scoring.
        rank = (entry["has_study_results"], entry["n"] or 0)
        if prev is None or rank > (prev["has_study_results"], prev["n"] or 0):
            pools[bucket][key] = entry

    out: Dict[str, Any] = {
        "input_rows": len(rows),
        "distinct_esid": len(by_esid),
        "excluded": dict(excluded),
        "pools": {},
    }
    for bucket in BUCKETS:
        items = list(pools[bucket].values())
        items.sort(key=lambda e: (e["n"] or 0, len(e["indication"])), reverse=True)
        out["pools"][bucket] = {
            "count": len(items),
            "reviewed_cap": per_bucket,
            "items": items[:per_bucket] if per_bucket else items,
        }
    return out


def missing_abstract(pool: Dict[str, Any]) -> int:
    return sum(1 for b in BUCKETS for i in pool["pools"][b]["items"] if not i["abstract_text"])


def to_csv(pool: Dict[str, Any], path: str) -> None:
    cols = [
        "bucket", "esid", "trial", "indication", "phase", "evaluation", "n",
        "key_evidence", "primary_endpoint", "randomized", "blinded", "trial_control",
        "data_type", "machine_signal", "machine_endpoint_call", "has_summary", "has_abstract",
    ]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for bucket in BUCKETS:
            for item in pool["pools"][bucket]["items"]:
                sig = item["machine_signal"]
                sig_txt = ""
                if sig.get("endpoint"):
                    bits = [sig["endpoint"]]
                    if sig.get("value") is not None:
                        bits.append(f"{sig['value']}{sig.get('unit') or ''}")
                    if sig.get("p"):
                        bits.append(f"p{sig['p']}")
                    if sig.get("hr"):
                        bits.append(f"HR{sig['hr']}")
                    sig_txt = " ".join(bits)
                writer.writerow({
                    "bucket": bucket,
                    "esid": item["esid"],
                    "trial": item["trial"] or "",
                    "indication": "; ".join(item["indication"]),
                    "phase": item["phase"] or "",
                    "evaluation": item["evaluation"] or "",
                    "n": item["n"] or "",
                    "key_evidence": item["key_evidence"] or "",
                    "primary_endpoint": "; ".join(item["primary_endpoint"]),
                    "randomized": item["randomized"] or "",
                    "blinded": item["blinded"] or "",
                    "trial_control": item["trial_control"] or "",
                    "data_type": item.get("data_type") or "",
                    "machine_signal": sig_txt,
                    "machine_endpoint_call": json.dumps(
                        item["machine_endpoint_call"], ensure_ascii=False),
                    "has_summary": bool(item["summary"]),
                    "has_abstract": bool(item["abstract_text"]),
                })


def to_markdown(pool: Dict[str, Any]) -> str:
    lines = [
        f"- 输入行 {pool['input_rows']} / 去重 esid {pool['distinct_esid']}",
        "- 排除（非试验证据源）：" + (", ".join(
            f"{k} {v}" for k, v in sorted(pool["excluded"].items())) or
            "（无——输入未含非试验记录；两段式拉取时此计数取自第一段 lite 结果）"),
        "- 池内顺序按 n 降序，仅供阅读，**不是推荐顺序**",
        "",
    ]
    for bucket in BUCKETS:
        data = pool["pools"][bucket]
        lines.append(f"## {BUCKET_TITLES[bucket]}（候选 {data['count']} 条）")
        lines.append("")
        lines.append("| 试验 | 适应症 | 期 | 评价 | n | 数据类型 | 机器信号 | 摘要 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for item in data["items"][:25]:
            sig = item["machine_signal"]
            sig_txt = ""
            if sig.get("endpoint"):
                sig_txt = sig["endpoint"]
                if sig.get("value") is not None:
                    sig_txt += f" {sig['value']}{sig.get('unit') or ''}"
            lines.append(
                "| {t} | {i} | {p} | {e} | {n} | {d} | {s} | {a} |".format(
                    t=item["trial"] or "（无简称）",
                    i="; ".join(item["indication"][:2]),
                    p=(item["phase"] or "").replace("Phase ", "P"),
                    e=item["evaluation"] or "-",
                    n=item["n"] or "-",
                    d=item.get("data_type") or "-",
                    s=sig_txt or "-",
                    a="✓" if item["abstract_text"] else ("summary" if item["summary"] else "×"),
                )
            )
        if data["count"] > 25:
            lines.append(f"| … 另外 {data['count'] - 25} 条见 CSV / JSON | | | | | | | |")
        lines.append("")
    return "\n".join(lines)


def to_batches(pool: Dict[str, Any], size: int, path: str) -> int:
    """Emit review batches (JSONL) so the model reads every candidate once."""
    records = []
    for bucket in BUCKETS:
        for item in pool["pools"][bucket]["items"]:
            records.append({
                "bucket": bucket,
                "esid": item["esid"],
                "trial": item["trial"],
                "indication": item["indication"],
                "phase": item["phase"],
                "evaluation": item["evaluation"],
                "n": item["n"],
                "key_evidence": item["key_evidence"],
                "primary_endpoint": item["primary_endpoint"],
                "title": item["title"],
                "abstract_text": item["abstract_text"] or item["summary"],
            })
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(0, len(records), size):
            chunk = records[i:i + size]
            fh.write(json.dumps({"batch": i // size + 1, "items": chunk},
                                ensure_ascii=False) + "\n")
            count += 1
    return count


# --------------------------------------------------------------------------- #
# self-test
# --------------------------------------------------------------------------- #
def _self_test() -> int:
    def row(**kw):
        return flat_row(kw)

    rows = [
        row(clinical_result__id="a", clinical_result_evidence_source=["Phase III"],
            clinical_result_evaluation="不佳", clinical_result_trial_abbreviation=["TRIO-1"],
            clinical_result_indication_name=["非小细胞肺癌"], clinical_result_group_count=["850"],
            clinical_result_summary="Failed to improve OS.",
            clinical_result_study_results=[
                {"arm_type": "relative", "endpoint_type": "主要终点",
                 "endpoint_attribute": "有效性", "endpoint_label": "Overall survival",
                 "p_value": "=0.62", "hazard_ratio": "1.04", "hazard_ratio_ci": "0.88-1.23"},
                {"arm_type": "single", "endpoint_type": "主要终点",
                 "endpoint_attribute": "安全性", "endpoint_label": "Grade 3 adverse events",
                 "result": "44.6", "result_unit": "%"},
            ]),
        row(clinical_result__id="b", clinical_result_evidence_source=["Phase I"],
            clinical_result_evaluation="积极", clinical_result_trial_abbreviation=["FIRST-1"],
            clinical_result_indication_name=["实体瘤"], clinical_result_group_count=["42"],
            clinical_result_study_results=[
                {"arm_type": "single", "endpoint_type": "主要终点",
                 "endpoint_attribute": "安全性", "endpoint_label": "Grade 3 TEAE",
                 "result": "12", "result_unit": "%"},
                {"arm_type": "single", "endpoint_type": "次要终点",
                 "endpoint_attribute": "有效性",
                 "endpoint_label": "Objective response; RECIST v1.1; percentage",
                 "result": "37.5", "result_unit": "%"},
            ]),
        row(clinical_result__id="c", clinical_result_evidence_source=["Phase II"],
            clinical_result_evaluation="积极", clinical_result_trial_abbreviation=["TRIO-1"],
            clinical_result_indication_name=["非小细胞肺癌"], clinical_result_group_count=["120"]),
        row(clinical_result__id="d", clinical_result_evidence_source=["真实世界研究"],
            clinical_result_evaluation="积极", clinical_result_group_count=["300"]),
        row(clinical_result__id="e", clinical_result_evidence_source=["Phase III"],
            clinical_result_evaluation="-", clinical_result_group_count=["20"]),
    ]
    pool = build_pools(rows)
    fails = 0

    def check(cond, msg):
        nonlocal fails
        if not cond:
            fails += 1
            print("FAIL:", msg)

    check(pool["distinct_esid"] == 5, "distinct esid")
    check(pool["excluded"].get("真实世界研究") == 1, "real-world excluded")
    check(pool["pools"]["failed"]["count"] == 1, "failed pool")
    check(pool["pools"]["early"]["count"] == 1, "early pool")
    check(pool["pools"]["pivotal"]["count"] == 2, "pivotal pool")
    early = pool["pools"]["early"]["items"][0]
    check(early["machine_signal"].get("endpoint") == "客观缓解率",
          "early signal prefers efficacy over safety rows")
    check(early["machine_signal"].get("value") == 37.5, "early signal value")
    failed = pool["pools"]["failed"]["items"][0]
    check(failed["machine_endpoint_call"]["verdict"] == "missed", "failed endpoint call")
    check(parse_num("not reached") is None, "parse_num NR")
    check(parse_num("1,234") == 1234.0, "parse_num comma")
    check(parse_p("<0.001") is not None, "parse_p")
    check(any(i["esid"] == "a" for i in pool["pools"]["failed"]["items"]), "failed esid a")
    print("self-test: OK" if not fails else f"self-test: {fails} checks failed")
    return 1 if fails else 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", help="JSON rows from the query tool")
    ap.add_argument("--input", dest="input_opt", help="alias for the positional input")
    ap.add_argument("--out-dir", help="write pool.json / pool.md / review.jsonl here")
    ap.add_argument("--top", type=int, default=0, help="alias for --limit-per-bucket")
    ap.add_argument("--limit-per-bucket", type=int, default=0,
                    help="cap candidates per bucket (0 = keep all)")
    ap.add_argument("--out-json")
    ap.add_argument("--out-csv")
    ap.add_argument("--out-md")
    ap.add_argument("--batches", help="write review batches (JSONL) to this path")
    ap.add_argument("--batch-size", type=int, default=25)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.input:
        args.input = args.input_opt
    if not args.input:
        ap.error("input JSON required unless --self-test")
    if args.top:
        args.limit_per_bucket = args.top
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        args.out_json = args.out_json or os.path.join(args.out_dir, "pool.json")
        args.out_md = args.out_md or os.path.join(args.out_dir, "pool.md")
        args.batches = args.batches or os.path.join(args.out_dir, "review.jsonl")

    pool = build_pools(
        load_rows(args.input),
        per_bucket=args.limit_per_bucket or None,
    )
    text = json.dumps(pool, ensure_ascii=False, indent=2)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.out_json}")
    else:
        print(text)
    if args.out_csv:
        to_csv(pool, args.out_csv)
        print(f"wrote {args.out_csv}")
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(pool))
        print(f"wrote {args.out_md}")
    if args.batches:
        n = to_batches(pool, args.batch_size, args.batches)
        print(f"wrote {args.batches} ({n} batches)")
    total = sum(pool["pools"][b]["count"] for b in BUCKETS)
    print(f"candidates {total} / missing abstract {missing_abstract(pool)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
