---
name: multi-clinical-result-comparison
description: Use when two or more selected clinical result records need a fast, source-grounded comparison. Produces a compact alignment brief with one primary chart when compatible, rather than a full evidence-synthesis report.
---

# Clinical Result Quick Comparison

## Purpose

Answer the user's comparison question quickly. The default output is a compact decision-support brief, not a monograph:

1. one-sentence takeaway;
2. one compact alignment table;
3. an evidence-chain timeline only when all usable selected records belong to one trial and contain multiple distinct disclosures from that trial;
4. one primary quantitative chart for a compatible comparison endpoint, when useful;
5. short interpretation, caveats, and missing information.

Do not expand into a full trial history, publication-by-publication review, endpoint-family survey, or detailed subgroup report unless the user explicitly asks for a deep review. The evidence-chain timeline is the deliberate exception for an all-records-single-trial input: it is a compact visual of disclosure progression, not a full narrative reconstruction. Mixed-trial inputs never receive this timeline by default.

## Read these references

Always read:

1. `references/input-contract.md`
2. `references/citation-and-ref.md`
3. `references/conclusion-language.md`
4. `references/file-delivery.md`
5. `references/chart-templates.md`

Same-trial disclosures are handled as rows in one alignment table by default. Only when **all usable selected records belong to one trial** and there are two or more distinct evidence states should you also generate the compact evidence-chain timeline; read `references/same-trial-evolution.md` and `references/timeline-diagram.md` for that case. Mixed-trial inputs do not get a timeline by default. Read `references/cross-trial-comparison.md` only when the user asks for detailed cross-trial comparability.

## Input

The user provides selected clinical-result `esid` values in selection order. Pull them with MCP `pharmcube-query-clinical-result-with-params`, passing `extra_esids` and a strict, minimal `selected_fields` allowlist copied from `docs/params-tool-schema.md`. The returned records map to `{{ref_1}}`, `{{ref_2}}`, etc. in input order.

Require at least two usable records for comparison. Keep every selected record in the source inventory and citation JSON, including duplicates and unusable records. Never request whole records, unrelated esids, or external facts.

## Fast workflow

### 1. Pull once and make one digest

Make one MCP request, then one compact digest containing only:

- trial/study identity and whether records appear same-trial or different-trial;
- disease, line/setting, phase and design;
- treatment and comparator;
- sample or analysis population;
- the strongest directly reported common endpoint(s), value, unit, time point and denominator;
- key safety signal or limitation;
- source marker and available entity IDs.

Do not reread or paste full records unless a specific ambiguity blocks the comparison.

### 2. Choose the comparison spine

Choose one primary question and one main endpoint. Prefer, in order:

1. the endpoint explicitly shared by the selected records;
2. the primary endpoint shared by the largest compatible subset;
3. the clearest directly reported efficacy endpoint.

Do not manufacture a common endpoint by converting, averaging, pooling, or deriving values from HR, p-value, difference, percentage change, or qualitative language. If no endpoint is compatible, produce the table and state why no chart is shown.

Use the study's reported experimental-arm observation as the comparison value when available. Keep within-study comparator effects beside it as context, never as a cross-trial head-to-head value.

### 3. Make the evidence-chain timeline only for a single-trial input

First establish that every usable selected record belongs to the same trial. If any usable record belongs to another trial, or trial identity cannot be established consistently, do not generate a timeline in the default quick-comparison mode. If all usable records are from one trial and support two or more distinct evidence states, generate the descriptive evidence-chain timeline from `templates/charts/evidence-timeline.json`. Merge duplicate disclosures into one state, preserve source-supported chronology, and show only the state label, cutoff/follow-up, key update and source markers. This timeline is required for the all-records-single-trial multi-disclosure case.

Do not generate the timeline for mixed-trial inputs, a single distinct state, or unsupported chronology. State the limitation briefly when relevant.

### 4. Make one primary quantitative chart

Generate at most **one quantitative** chart by default. The chart should answer the primary comparison question at a glance:

- cross-sectional compatible single values → `endpoint-bar.json`;
- same study/cohort/endpoint with at least two reported time points → `endpoint-line.json`;
- do not generate multiple quantitative endpoint charts unless the user asks for them.

Only plot values with matching endpoint definition, population/analysis set, unit, direction and time point or clearly comparable follow-up. Use plain chart text without `{{ref_n}}` or `entity:` links; keep exact values and citations in the Markdown table. For the current debug deployment, create the `.preview.html` twin for each produced chart from the validated JSON and reference the preview in the report, as specified in the TEMP rule below.

The report may contain two visual products only in this specific combined case: one same-trial evidence-chain timeline plus one compatible quantitative chart. If quantitative compatibility is partial, omit the quantitative chart rather than forcing a visual ranking. Say `不绘图：...` with the concrete mismatch.

### 4. Write once

Prepare the report and citation map before writing. Write the complete report once to `/workspace/output/<slug>-report.md`; write the strict citation object once to `/workspace/output/<slug>-citations.json`. Run one final read-only check. Do not use repeated grep/edit passes to add citations, entities, or chart references.

## Default report shape

Use Chinese unless requested otherwise. Keep the report short and use this structure:

```markdown
# [主题]快速对比

**一句话结论：** [直接回答比较问题；注明不是头对头时不得写成优胜结论]

## 核心对齐

| 结果/试验 | 治疗方案 | 人群/分析集 | 核心终点与定义 | 结果 | 时间点/随访 | 研究内对照 | 证据限制 |
|---|---|---|---|---|---|---|---|

[最多一张 ::visualization]

## 证据演进（仅全部来自同一试验且存在多披露时）

[one evidence-chain timeline visualization]

| 证据状态 | 数据截止/随访 | 主要新增信息 | 与前序关系 |
|---|---|---|---|
| | | | |

## 怎么读

- [一至三条最重要的比较观察]
- [可比性与不能推断的边界]
- [安全性关键信号或未报告项]

## 仍需确认

[最多三条真正影响判断的信息缺口]
```

The table must retain source markers immediately beside every material number or claim. Same-trial repeated disclosures may occupy separate rows, but mark duplicate/update status briefly and do not count duplicates as independent evidence. When there are two or more distinct states from one trial, include the compact evidence-chain timeline; do not expand into a full narrative timeline unless requested.

## Evidence and interpretation boundaries

- Clinical evidence comes only from selected `abstract_text`, `summary`, `study_results`, and returned design/arms fields.
- Citation metadata is only for the separate citation JSON.
- Entity metadata is label metadata, not clinical evidence.
- Preserve source spelling and reported units, definitions, denominators, time points and analysis sets.
- Never infer an experimental-arm value from a treatment effect, HR, p-value, CI, or qualitative statement.
- Never pool results or imply head-to-head superiority across unrelated trials.
- A directional cross-trial observation must state the comparability level: `直接可比`, `有限可比`, or `不可直接比较`.
- Safety is a compact boundary check: retain event definition, grade, denominator and exposure when reported; `未报告` is not `无风险`.
- Do not add external competitors, standards of care, regulatory claims, market claims, or remembered facts.

## Entity references

When entity IDs are explicitly returned, use `[name](entity:type:id)` for drug, company and trial mentions in the report. Do not put entity links in chart JSON or preview HTML. Build the name-to-ID map before the one report write. Apply available anchors while writing; do one coverage check afterward and do not run multi-pass patch loops.

## Chart protocol

Use `evidence-timeline.json` for the required same-trial multi-disclosure timeline and use at most one `endpoint-bar.json` or `endpoint-line.json` for the optional quantitative chart. Fill only data/text fields, write products under `/workspace/visualizations/`, and run:

```bash
python3 templates/charts/validate-chart.py /workspace/visualizations/<name>.json
```

Bars are sorted high-to-low; line points remain chronological. Chart values are numbers only. No HTML wrapper, comments, Mermaid, inline citations or entity links in JSON.

## TEMP debug dual-write

Until the real chart renderer is deployed, apply the dual-write rule to every produced chart (the timeline and, if applicable, the one quantitative chart):

1. validate the formal `.json` chart;
2. generate its twin from the same JSON:
   `python3 templates/charts/render-preview.py <chart>.json -o <chart>.preview.html`;
3. reference only the `.preview.html` in the report, while shipping both files.

This rule overrides `.json` examples elsewhere. When the renderer is deployed, remove the preview twin and reference the validated `.json` directly.

## Delivery

Write the report and citation JSON under `/workspace/output/`. The citation JSON is raw strict JSON with exactly `title`, `link`, and `paper_release_time_str` per `ref_n`, copied byte-for-byte from the selected records. Call `present_artifact('/workspace/output/<slug>-report.md')` as the final tool call. The chat body is empty or one short delivery sentence. If `present_artifact` is unavailable, return the files' intended contents under the existing fallback contract.
