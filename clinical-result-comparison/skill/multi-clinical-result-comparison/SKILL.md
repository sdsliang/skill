---
name: multi-clinical-result-comparison
description: Use when two or more selected clinical result texts need to be synthesized into a complete trial interpretation, especially multiple disclosures from the same study over time. Reconstructs a source-grounded evidence chain with inline citation-marker traceability, deduplication, endpoint evolution, safety maturity, and bounded interpretation. When the selected texts come from different studies, produces a comparison-first, domain-aligned cross-trial comparison (efficacy, safety, PK/PD, PRO) that helps judge which treatment is better or worse. Chart products are pure JSON files produced by reusing the chart-visualization-json skill.
---

# Multi-Clinical-Result Trial Synthesis

## Purpose

Turn selected clinical result texts into a complete interpretation of each underlying trial. The trial is the primary analysis object; the individual disclosures are evidence sources that contribute observations to a longitudinal chain. When several sources describe the same trial, do not make the visible report a comparison of articles, abstracts, or press disclosures.

Use the final template by routing:

- single trial (one identity with multiple disclosures) → `templates/unified-evidence-report.md`
- multiple independent trials → `templates/cross-trial-report.md` (comparison-first, domain-aligned)

Read these support files before starting work:

**每次必读（所有场景）：**

1. `references/input-and-extraction.md`
2. `references/input-contract.md`
3. `references/mode-detection.md`
4. `references/citation-and-ref.md`
5. `references/conclusion-language.md`

**仅在场景匹配时读（不匹配则跳过，不要默认全部读取）：**

6. `references/same-trial-evolution.md` — **仅当**输入中存在同一试验多次披露（multi-disclosure）时才读
7. `references/timeline-diagram.md` — **仅当**同试验输入具有两个及以上不同证据状态时才读
8. `references/cross-trial-comparison.md` — **仅当**所选文本来自不同试验（cross-trial 模式）时才读
9. `references/file-delivery.md` for the v0.9 file-delivery contract (**fixed deliverable paths** — `/workspace/output/report.md` plus `/workspace/output/citations.json`, hard-coded by the backend and never suffixed with a slug, date, or index; chart products use the fixed `/workspace/visualizations/evidence-timeline.json` and `endpoint-<kind>-<n>.json`; `present_artifact` terminal delivery)
9. `references/toolbox.md` — **the packaged scripts and their exact CLI/IO/exit codes**; read this once per run instead of reverse-engineering them. It also answers the questions whose answers previously cost a run the most tool calls (who writes the appendix, what a column header looks like, which numbers belong to the ledger, what `patch.py` wants) — **if a packaged script does not behave as you expect, re-read the relevant section of `references/toolbox.md` or run it with `--help`; never open the script's source to guess, and never write a replacement helper.** They ship at `/workspace/skills/multi-clinical-result-comparison/scripts/` — call them by that path. `scripts/prep_sources.py` (pull → `work/sources/ref_<n>.txt` + `work/refs.json` + digest), `scripts/merge_ref_facts.py` (per-ref shard files → `work/facts.json`; used when 3+ refs are delegated), `scripts/build_ledger.py` (facts → strict `work/ledger.json`, the only validation pass), `scripts/patch.py` (asserted atomic small edits), `scripts/make_chart.py` (chart product from a content-only spec), `scripts/make_citations.py` (citation JSON), `scripts/check_report.py` (the mechanical pre-delivery pass: must exit 0 before `present_artifact`). **Settle the numeric format before the first `facts` row is written** (decimal separator `.` vs `·`, unit and statistic wording): changing it later through `patch.py` cost 3–5 minutes in a measured run. **These are the pipeline — never write your own replacement helper for them**, and never keep a `work/draft.md`: the body is written once at its final path and rendered in place (see item 9b below). Verify with the scripts' own output — a `patch.py` assertion plus **one** `check_report.py -v` pass — instead of re-reading the `output/report.md` you just wrote (a narrow single-range read is the fallback, not the default).
9b. `skill/multi-clinical-result-comparison/scripts/render-facts.py` for the numeric fact-ledger render gate. Use it when the report contains material numeric tables or repeated results; run it **once**, with `--draft` and `--out` both `/workspace/output/report.md` (same-path rendering is intended and safe — it reads the whole file, resolves the tokens, appends the appendix and replaces it atomically). It fails closed on unbound fact tokens, source-quote/value mismatch, duplicate fact IDs, unknown citations or leaked internal provenance. Its audit explicitly does not replace semantic review.
10. `references/chart-templates.md` before producing any chart — chart products are pure JSON and **reuse the upstream `chart-visualization-json` skill** (its protocol, envelope, templates, Zod schemas and CLI validator are the **render config and single source of truth** — reuse them verbatim) instead of a local implementation. The Skill's JSON contract is the only chart channel: do not render a chart through the platform's built-in chart module, `show_widget`, HTML/SVG, or Mermaid, do not call `read_me` for these JSON chart files, and do not invent fields, palettes, or a parallel JSON shape.

## Input

Each selected clinical result is identified by its backend esid (the clinical-result ID, `clinical_result.extra_esid`). The frontend/user message supplies the selected esid list in user-selection order (that order defines the `{{ref_n}}` marker assignment). The Skill does **not** receive per-source full-text `.md` attachments; it pulls the detail records itself through the MCP tool `pharmcube-query-clinical-result-with-params` (see `references/input-contract.md`): pass `esids: [...selected esids]` plus a **strict, minimal `selected_fields` allowlist** whose names are copied verbatim from the tool's own `selected_fields` parameter description (the runtime authority: it embeds the full `ALLOWED_FIELD_NAMES` / `ALLOWED_FIELDS` list; the repo keeps an offline mirror at `docs/params-tool-schema.md` for maintainers). Never invent a field name or substitute a merely similar concept: `clinical_result.group_count` is enrollment total, **not arm count or per-arm sample size** (see `references/input-contract.md`, *Source of truth*). The tool argument is `esids`; `clinical_result.extra_esid` is the returned record field. On `INVALID_INPUT` / unknown fields, read the runtime schema, correct or remove invalid fields, and retry the same selection. Keep `selected_fields` small to bound the returned payload (a single large response can exceed the context budget). The returned records map back to the supplied esids by `clinical_result.extra_esid`, and markers are assigned in user-selection order over the records that actually came back → `{{ref_1}}, {{ref_2}}, …`. One esid can come back as **several rows** (with `indication_name` requested the backend fans out on a disease-dimension join; those rows differ only in an injected `disease_id`): de-duplicate by `clinical_result.extra_esid` and treat them as **one** record — one marker, one citation entry, one entry in every count, evidence state and timeline event. An esid that returns no record gets **no** marker and **no** citation entry (never write a citation with an empty `title`): the params tool answers `ok: true` with an empty `data` array for an unknown or invisible esid, so confirm missing esids in **one** further batched call at most and never probe variant spellings or guessed ids. Follow `references/input-contract.md` for the exact field mapping, recommended `selected_fields`, response limits, and the unretrievable-item protocol. Never print, quote, or transmit raw field values, filenames, or tool internals into the report body.

**Delegation is for the fact rows, and it is concurrent**: when 3 or more refs are selected and the `task` tool is visible, write the fact rows **one subagent per ref** and send every `task` call **in the same message** (calls sent in separate messages run one after another), then merge the shard files with `scripts/merge_ref_facts.py`. This is the one place where sharding pays: the fact rows are the largest generated block and per-ref work is independent. It is never mandatory, never skips a ref, and the main thread keeps the report, the charts and the delivery. A subagent does not inherit this Skill's prompt, so its `description` must carry the whole spec itself (skill reference paths, its own `work/sources/ref_<n>.txt`, the fixed `study`/`arm` vocabulary, the output path, and an explicit `timeout_seconds` on every command — a subagent's `execute` defaults to 30 s). Full recipe and measured numbers: `references/input-contract.md` (*Delegating the fact rows*). For **pulls** (more than 5 selected esids) per-chunk delegation stays available as a context-bounding option, not a requirement.

## Evidence boundary

`references/input-contract.md` (*Evidence source priority*) is the single authority for the evidence boundary, retrieval permissions/budgets, analysis depth, source-side depth caps and citation-link substitutions. Use the selected records' clinical-content fields (`abstract_text`, `summary`, `study_results`, design/arms context), with the original source taking priority for material clinical facts. Read `abstract_text` first; for `src=1` attempt the permitted R6 → R7 PMC chain even when an abstract is present. A usable full text retrieved for the selected paper becomes its analysis surface: full-text-only facts may enter prose, tables and charts with their own time point, analysis-set and population labels. Depth alone does not determine comparability. Cite that record with C1 or C2 only after retrieving and archiving its full text; otherwise preserve its supplied link. No PMCID, not in PMC, explicit non-OA metadata and a fetch that came back empty are distinct outcomes; judge non-OA on explicit metadata alone, never on a failed retrieval.

Keep the source-class permissions, blocked hosts, one-attempt limit (two calls for the PMC chain), whole-run cap and no-search/no-retry rules in the input contract. Record paths and the depth actually reached in `原文核对：` (the material and its depth — never fetch failures, HTTP statuses, tooling or environment narration); write same-metric, same-label divergences as `原文 …；库内记录 …{{ref_n}}`, and distinguish version differences. Citation and entity metadata are not clinical evidence; the selected evidence alone supports every clinical claim, and drug/company/trial names are written as **plain text** — the v0.10/v0.11 `[名字](entity:type:id)` inline-reference syntax was removed in v0.16 and must never appear in the report, its tables, its charts or the fact ledger. Do not fill gaps from memory or introduce unselected studies. Require at least two usable records: **if fewer come back, do not write a report or citation file**; name the missing/unusable selections in chat and ask the user to re-check them. With at least two usable records, name any remaining gaps in the evidence scope and never invent a citation for an unretrieved record.

Preserve the exact source spelling of drug names, trial names, biomarkers, companies, and other proper nouns unless a selected record explicitly provides the equivalent Chinese name. **For drugs that equivalent is a paired field the same record already returns**: `clinical_result.arms[].drugs[].drug_earth_name_cn` / `drug_earth_name_en` — no extra call, no judgement call. In a Chinese report write `drug_earth_name_cn` whenever it is non-empty (`依洛尤单抗`, not `evolocumab`), in an English report write `drug_earth_name_en`, and fall back to the other language's value only when the target-language field is empty or a `未报告` placeholder. Do not transliterate, translate, normalize, or map proper names from memory, and never look a name up in another tool or dictionary. A Chinese report retains an English drug name only when the record carries no Chinese name.

## Source references

At the beginning of processing, assign stable inline markers in selection (esid) order over the records that returned: `{{ref_1}}`, `{{ref_2}}`, and so on. This numbering is only a citation label and does not establish chronology. Keep a source ledger internally with:

- citation fields from the pulled records (`paper_title`, `full_article_link`, `paper_release_time` — date part only for the release time — and when returned `journal`/`doi`/`pm_id`) for the separate final citation JSON;
- source-supported trial/study name, registry identifier, disclosure title, endpoint, analysis scope, cutoff, and follow-up;
- usability and material limitations;
- evidence states and numeric claims supported by the source.

In the finished report, every material number and source-dependent conclusion must be followed by its marker. Do not append JSON or a source table to the report body; output one separate strict citation JSON object. Never expose runtime correlation IDs, database/index names, storage fields, retrieval traces, or file paths.

## Workflow

### 1. Extract each source independently

Build an internal worksheet for each source. Capture only explicitly supported:

- trial identity, disease, stage, treatment setting and eligibility;
- design, phase, randomization, blinding, sites and comparator; explicitly re-check registry-based blinding, randomization, control design and active/placebo control against the selected paper's Methods in the deepest available permitted original. Follow `references/input-contract.md` (*Study-design verification*): the paper's design governs the report; disclose actual differences as `原文：…；登记平台记录：…{{ref_n}}`, distinguish role/period/version differences, and mark unconfirmed aspects rather than assuming agreement or an extraction error;
- intervention dose, schedule, combination and maintenance;
- enrolled, randomized, treated and analyzed populations;
- endpoint hierarchy, definition, assessment method and analysis set;
- experimental-arm observations and within-trial comparative effects as separate objects;
- response, durability, symptom, quality-of-life, subgroup and sensitivity results;
- safety events, severity, seriousness, treatment relatedness, denominator, exposure, discontinuation, dose modification and death;
- data cutoff, follow-up, analysis milestone and disclosure date;
- source interpretation, omissions, ambiguities and possible truncation.

A numeric result is never a free-floating value. Preserve the tuple:

```text
records: ref + trial + identity + conclusion (one entry per returned disclosure; `conclusion` is required, `trial` is the appendix column key, `identity` is printed only through its first segment; the long-prose `title` / `design` / `arms` / `coverage` fields are legacy-accepted and never printed)
facts:   fact_id + marker + record/disclosure version + study identity + population/subgroup + arm + endpoint/definition + statistic/value + unit + time/cutoff + denominator + analysis status + source quote
```

Build a compact internal numeric fact ledger before drafting any table, chart or repeated summary. **Author the facts, then let `python3 /workspace/skills/multi-clinical-result-comparison/scripts/build_ledger.py` compile and validate them** (see `references/toolbox.md`): it fills the `未报告` defaults, checks that every `quote` is an exact substring of that ref's `work/sources/ref_<n>.txt` and that every `value` occurs inside its `quote`, rejects unknown refs / duplicate ids / kinds outside the vocabulary, and fails the whole compile — writing nothing — when any check fails. Do not hand-write the ledger JSON and do not write your own validator. The ledger is one JSON object with exactly `records` and `facts`. `records[]` entries carry `ref`, `identity`, `conclusion` plus the expected `trial` key (`title` / `design` / `arms` / `coverage` are accepted for backward compatibility but **no longer printed**: the design and population prose lives in the body and the 试验背景 table, bound by `{{ref_n}}`). `identity` is the one-line trial identity; the appendix prints only its first segment (`HARMONi-6（AK112-306 / NCT05840016）` before the `｜` separators). `conclusion` is a one-sentence, source-supported disclosure-level conclusion and is **required** (the render gate fails without it). `trial` is the trial this disclosure belongs to — the registry number when the source states one, otherwise the trial name; every disclosure of one trial must carry the **same** `trial` string, because it is the only key that merges a trial's disclosures into one appendix column (a missing key falls back to a registry identifier then to the `study` label, which splits a trial whose disclosures are named differently). Use the same `study` string for every fact of one trial. `facts[]` entries carry the clinical judgement — `id`, `ref`, `study`, `kind`, `endpoint`, `arm`, `value`, `unit`, `quote` — and **nothing a script can derive**: omit `source_file` (the compiler resolves it from `ref`) and omit `version` / `population` / `timepoint` / `assessment` / `statistics` when the source reports nothing for them (the compiler fills `未报告` / empty), so those keys may simply be absent rather than blank; `kind` is one of `试验设计` / `试验结论` / `有效性` / `安全性` / `PK/PD` / `PRO` / `其他` (endpoint family may follow after `·`, e.g. `有效性·OS`), design facts such as enrollment or analysis sets are `试验设计` rather than `有效性`, and `endpoint` is the smallest comparable parent label (`OS`, `中位 PFS`, `ORR`) so timepoint/definition variants align on one appendix row. **Only alignable numeric design facts belong in the ledger** — randomization/enrollment counts, analysis set and denominator, data cutoff and follow-up duration, event counts, statistical boundaries, dose and interval. 研究中心数、性别/年龄分布、入选/排除条件条目、分层因素、终点定义复述与分析计划细节 are **not** ledger facts: they are not comparable numbers and only manufacture one-off rows (R37 produced 14 such self-invented design rows in one appendix). Each material value gets one stable fact ID and one source quote; bind HR, CI, p value, numerator/denominator and arm to the same endpoint comparison rather than treating them as interchangeable fragments. Reuse the same fact IDs everywhere. Do not hand-copy a value into a second table from memory. When the report contains material numeric results or repeated result tables, run the bundled `scripts/render-facts.py` gate **once**, in place, with `--ledger work/ledger.json --draft /workspace/output/report.md --out /workspace/output/report.md --audit work/audit.json`: it validates source-quote/value binding, renders fact tokens and appends the complete disclosure appendix. A failed gate blocks delivery and must not be bypassed by deleting the appendix, thinning the ledger or replacing values with prose. The gate is provenance-only: it does not validate clinical semantics, endpoint definitions, statistical interpretation or handwritten numbers that were not fact-token bound; these remain mandatory human/agent review items.

The final report has two layers:

- **Interpretation layer:** concise trial-level reasoning, evidence maturity, comparability, design conflicts and only the numbers needed to support the conclusion. Do not repeat a full result table in every section. Put PFS/OS/ORR/DoR and safety metrics in their own endpoint families; do not mix values merely because they share a unit.
- **Complete evidence appendix:** the renderer's single alignment matrix (`## 附录：证据对齐矩阵（数值事实账本）`), produced from the ledger rather than written by hand. Its column layout is fixed by the renderer: **one column per trial** (disclosures sharing the record's `trial` key merge into one column, header `**试验名**<br>注册号 · N 条披露`; `**试验名**` is the readable name the renderer resolves — the fact `study` label first, then the record's `trial` name, then the identity line's first segment — so never fill `study`/`trial` with a registry number while the record carries a readable name; a trial without a registry number shows its `study`/`trial` name, and a display name that *is* a registry number is printed once as `**注册号**<br>N 条披露`), and for a **single trial with ≥2 disclosures one column per disclosure** (`**短版本标签**<br>ref_n`, or `**ref_n**` alone when there is no readable tag) so a trial's disclosures never pile into one cell. The appendix is **renderer output**: its title, its one-line legend for `—` and its columns all come from `work/ledger.json` — never hand-write an appendix, a placeholder for it, its legend, or a paragraph describing its layout; rows enter only through declared facts. Rows are dimensions and parent endpoints, grouped in the fixed segments 试验设计 → 试验结论 → 有效性 → 安全性 → PK/PD → PRO: the design block is the trial identity (`identity` first segment) plus the reported versions/cutoffs, the conclusion row is each record's `conclusion`, and endpoint rows align the same parent endpoint across disclosures with treatment arm, timepoint, assessment, population and definition qualifiers kept inside the cell as `治疗臂·时点·评估·人群：结果 单位（统计量）{{ref_n}}` (`—` when a disclosure reports no value); a qualifier every value of a row shares moves up into the row label. The record prose rows (披露标题 / 设计与方案 / 试验组与对照 / 人群与证据覆盖) were **removed in v0.16.1** — title, design and population text belongs in the body and the 试验背景 table, bound by `{{ref_n}}`. Every ledger fact must appear in the appendix: the gate fails closed on a dropped fact, and keep PFS, OS, ORR, DoR and safety metrics on separate rows; never merge unlike endpoints or arms into slash-separated cells. This is the product-side field-alignment view: it preserves disclosure-level facts while making comparable fields readable across trials. The interpretation layer explains only supported relationships.

Repeated numbers in narrative, tables and charts must resolve to the same fact ID. Before delivery, check exact duplicate consistency, study/endpoint/arm/timepoint/analysis-set binding, units and effect types, and absence of unsupported causal/statistical explanations. An apparent conflict between original text and registry fields is a source divergence to disclose, not a license to merge values.

### 2. Resolve trial identity and boundaries

Use converging source signals: exact registry ID, trial acronym, explicit previous-report wording, matching interventions and comparator, sample/arm structure, eligibility, geography and matching endpoint values. A shared identifier is strong evidence but still check for separate cohorts, extensions, substudies and post hoc groups.

If identity is probable but unconfirmed, retain the uncertainty in every later reference to the cluster. Never merge different cohorts merely because they share a program name.

### 3. Build evidence states, not a disclosure comparison

Group sources into evidence states. A state represents a distinct analysis/cutoff/population/endpoint contribution, for example:

- early or first result;
- prespecified primary analysis;
- interim analysis;
- final analysis;
- longer follow-up/update;
- new endpoint;
- subgroup or complementary analysis;
- safety or quality-of-life update.

Classify source relationships only when supported: duplicate, update, new endpoint, confirmation, complement, supersedes, conflict, uncertain. A repeated source using the same cutoff and analysis is a duplicate. It may retain its marker in the final citation list and appear alongside the state, but it is never counted as independent confirmation.

Order states by data cutoff, follow-up, analysis milestone, then disclosure date. If timing is missing or contradictory, show the uncertainty rather than guessing.

### 4. Reconstruct the complete trial chain

Analyze the trial as one coherent clinical question:

1. What population and treatment decision did the trial study?
2. What was the design and how credible is the comparison?
3. What did the primary endpoint show at each genuinely distinct state?
4. Did key secondary endpoints, especially OS or other time-to-event outcomes, extend or qualify the primary result?
5. What is known about response depth, durability, symptoms and quality of life?
6. Are subgroup observations prespecified and consistent, and are interactions reported?
7. How did safety evolve with exposure and follow-up?
8. What changed, what stayed stable, and what remains unknown?

The main narrative should explain the incremental information in each state. Do not create a “who won” or “which disclosure was better” conclusion for sources from the same trial.

### 5. Draft the report

For one trial, use `templates/unified-evidence-report.md`; for multiple trials use `templates/cross-trial-report.md` (or `templates/mixed-comparison-report.md` for a mixed set), per the routing above. A one-trial report must read as one trial-level evidence synthesis. Use a timeline table with one row per evidence state and a **发表时间** first column (the date part of that disclosure's `paper_release_time`, `未报告` when the record returns none): it labels when the disclosure appeared and is only the last-resort ordering key — order still follows source-supported data cutoff, follow-up and analysis milestone, never input order. Use endpoint tables that show the earliest and latest distinct values, analysis status, maturity, and inline markers. The separate citation JSON is the only source listing. Draft the complete report, then write it to `/workspace/output/report.md` and the citation JSON to `/workspace/output/citations.json` per `references/file-delivery.md` (do not stream the report into the chat body).

Name drugs, companies and trials as **plain text** in the report; the v0.10/v0.11 `[名字](entity:type:id)` inline-reference syntax was removed in v0.16 and any occurrence is blocked by the render gate. Entity-ID and paired-name metadata (`projects.associate_ids`, `trial_abbreviation`, `arms.drugs.drug_earth_id`, `arms.drugs.drug_earth_name_cn` / `drug_earth_name_en`, `projects.company_ids`) now only informs which proper name to use (prefer the source-supported trial abbreviation; for a drug, `drug_earth_name_cn` in a Chinese report and `drug_earth_name_en` in an English one) and the trial's `trial`/`study` key: never query another tool for IDs and never render one into prose, a table, a chart or the fact ledger.

For a same-trial input with two or more distinct evidence states, also generate the evidence-chain timeline diagram per `references/timeline-diagram.md` and place it directly above the timeline table in the evidence-chain overview section. **Assemble it with `python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py`** (see `references/toolbox.md`): you write only a content-only spec — `type: "timeline"`, `file: "evidence-timeline.json"`, the text fields and one `data[]` row per evidence state (merging duplicate disclosures) — and the script takes the `option` skeleton from `templates/charts/`, takes the envelope `{id, iframe_template, option}` from the live chart skill, writes it to `/workspace/visualizations/` and runs the validator. Never hand-copy the envelope (its `iframe_template` is refreshed on every chart publish), never hand-write the product JSON, and never construct it by copying `templates/timeline.json` yourself. Then reference it in the body with an absolute path: `::visualization[标题]{path="/workspace/visualizations/evidence-timeline.json"}` on its own line (no relative path, no `..`/backslash/out-of-prefix). The file must be **pure JSON** (chart-visualization-json envelope protocol, camelCase inside `option`; no HTML wrapper, no comments, no trailing commas — see `references/chart-templates.md`). The diagram is a descriptive timeline (chronology, per-state key labels, relationship notes, maturity via weight) and never replaces the exact-value timeline table; it is a **skeleton, not a second results table** — label ≤18 characters, `content` a ≤16-character qualitative phrase, `description` only the relationship plus maturity and its markers, and **the only number allowed in the chart is the `time` anchor itself (a year-month or date)** — every other value (cutoff, follow-up, sample size, rate, HR/CI/p, unit) belongs in exactly one place: the table. The table's 与前序关系 / 相对前一状态的影响 column states the relationship only, never the values again. Do not output Mermaid.

For numeric tables, put the marker in the same cell as the number or in a dedicated source-marker column immediately adjacent to the numeric result. For prose, put the marker immediately after the number or claim. Do not cite an entire paragraph only at its end when it contains multiple independently sourced numbers.

Write the body **once**, at its final path, and render it in place; a long draft that is later patched in pieces is the most expensive shape this pipeline has. Small corrections after rendering go through `scripts/patch.py` (asserted, atomic), not through a rewrite and not through re-reading the file to find the target.

### 6. Mixed inputs

For multiple unrelated trials, the primary deliverable is a **cross-trial comparison aligned by outcome domain** (efficacy, safety, PK/PD, PRO) that helps the user judge which treatment is better or worse. Build the comparison first: cluster by clinical question, then align each outcome domain across trials with one compact trial-context block per trial as support. Never fabricate a head-to-head proof or pool results; every per-cluster who-is-better judgment carries an explicit comparability/evidence-strength label. A comparison claim must cite the sources for the trials it compares. See `references/cross-trial-comparison.md`.

**引注归属（硬规则）：** 带 `{{ref_n}}` 的句子、条目或单元格里出现的**数值、臂、剂量、间隔、时点**必须是该 `ref_n` 记录自己的；一句话可以提到**另一条记录**的药名或登记号（比较句、排除句、否定句，如「未优于 X」「与 A 的终点不是同一构念」），但**必须同时点名本条记录自己的药名或登记号**——只点对方不点自己，这句就无法判定归属。`库内记录` 只出现在固定分歧写法 `原文 <值>；库内记录 <值>{{ref_n}}` 里（两半 + 标记齐全），不得在其它语境里指代库内值（如「库内记录为 70.5%」），两边一致时一个字都不提。同规则见 `references/citation-and-ref.md` 与 `references/input-contract.md`。

**图表每一行点名自己的试验（硬规则）：** 一张图里出现 ≥2 个试验时，**每根柱子/每条线自己的 `label` 或 `description` 里必须写明它属于哪个试验**（有注册号写注册号，否则写试验短名）——不得只靠标题、图例或颜色区分试验；只画一个试验的图可以把试验写在标题里。同规则见 `references/chart-templates.md`。

**同一观察一套写法（硬规则）：** 每个观察（试验·治疗臂·剂量·间隔·时点）只有**一套**身份短语，并在正文、精确值表与图表 `label`/`description` 中逐字复用；写法取原文本来的措辞（`monthly` → `每月一次`，`every 12 weeks` → `每 12 周`）。不得一份报告里同物两名（正文 `每月`、图表 `Q4W`/`QM`），**图表 label 不得引入正文没有的臂/剂量/间隔/时点写法**——label 是正文该行身份短语的原样引用。确需缩写时只固定一种并在正文给出全称。同规则见 `references/chart-templates.md`。

**时间维度优先（硬规则，先判时间维再判横截面）：** 当数据以长期随访/多时点披露为主（OLE 开放标签延展、同一研究同一队列 ≥2 个已披露时点、停药后复发等）时，图表主线用**折线图 `endpoint-line.json`**（`group`=队列/治疗组，`label`=已披露时点），只连线同一研究、同一队列、同一终点的时点，不跨研究/不跨队列/不跨人群连线，不插值、不补点、不外推；单时点披露用单点模式；无对照单臂（如婴幼儿外用药）也按时间维度画折线，但标题/说明注明「单臂无对照，仅描述随时间变化」。横截面单值终点（ORR、EASI-75 等单时点应答率）才用柱状图：按临床问题分组时，产生 **one `endpoint-bar.json` chart per group** (each group its own product file; plot that group's experimental-arm values side by side; study-internal comparators and boundaries go into per-item `description` or the exact-value table; title/subtitle state 跨试验并列展示≠头对头比较); never merge different groups into one chart, and groups that fail the compatibility conditions get no chart (reason stated in the table). 同一证据状态内既有单值对比又有时间维度的，时间维度折线优先呈现，单值柱状作为组间对照补充。所有图表成品为**纯 JSON**（见 `references/chart-templates.md`；协议、模板与校验一律复用上游 `chart-visualization-json` skill，不自研平行实现，**渲染配置（类型、字段名、默认值、`theme` 取值）也一律取自它的模板与 schema，不重述、不扩展、不自造**；图的交付通道只有 Skill 定义的 JSON + `::visualization`，不要用内置 chart 模块 / `show_widget` / HTML / SVG / Mermaid 绕开它，也不为这些 JSON 图调用 `read_me`），先跑 `node /workspace/skills/chart-visualization-json/scripts/validate-cli.js <成品>` PASS 再引用。

**一个数值只交付一次（硬规则）：** 数值的唯一出处是**指标域对齐表**（如「有效性对齐」）与附录；图是骨架，不承担抄数字的职责。所以：(1) **图所在的小节内不得再有复述该图数值的表格**（把数值表放到独立小节或附录，或把图移到没有该数值表的小节）；速览段若给了图，就只写散文，不再列一张同样的数字表；(2) **图自身的文字（`title`/`subTitle`/`describe`/`data[].label`/`data[].description`）不得复述它自己的绘图值**——只写口径、时点差异、方向、可比性判断与 `{{ref_n}}`；剂量/间隔/时点/例数里的数字（`225 mg`、`每 12 周`、`129 例`）是上下文，不算复述，研究内对照值与边界值仍可留在 `description`；(3) 同一张图的同一小节里出现 ≥2 个该图的绘图值即判 FAIL（由 `scripts/check_report.py` 机械检查，附录与时间轴图豁免）。这不是「不要图」——图必须保留，只是不再重复同一批数字。同规则见 `references/chart-templates.md`。

**只写发现，不写报告自己（硬规则）：** 交付物写给读报告的人：临床发现、证据材料属性，以及由此产生的可比性与成熟度限制。**不得出现报告自身的做法、分类或处理过程**——具体包括：`分析模式`／`选择依据`／`可比性结论`／`对齐等级`／`不绘图原因` 这类自述标签（含同名列的表格列）；「可绘图／只能有限并列／不具备绘图条件／部分对齐」这类由我们做的判断（判断的**内容**——时点、人群、口径、定义差异——直接写进解读边界）；`本报告`／`本次`／`本轮` 这类自指；`src=`／`esid`／`payload`／`JSONL`／`MCP`／工作区 这类内部字段与运行词汇；「无未复核记录／无遗漏／全部通过」这类自证尾巴。两个保留位照旧：固定的非头对头声明（一句），以及 `原文核对：` 覆盖行（按材料与深度写，用文字写来源类，不加自证尾巴）。`scripts/check_report.py` 把上述各项判 **FAIL**，宽泛的自指（`本报告`／`本次`）判 **WARN**。

## Required distinctions

- Trial identity versus disclosure identity.
- Evidence state versus duplicate source.
- Data cutoff versus publication/disclosure date.
- Experimental-arm observation versus within-trial comparison effect.
- Statistical significance versus clinical meaning.
- Subgroup consistency versus proof of treatment interaction.
- More mature evidence versus independently replicated evidence.
- A within-cohort time course (same study/cohort/endpoint multi-time-point, connectable as a line) versus cross-trial or cross-cohort snapshots (never connected into a trend).
- Unreported safety versus absence of safety risk.
- Source interpretation versus agent synthesis.
- Source-supplied proper name versus invented translation or normalization.
- One wording per observation: the same arm/dose/interval/timepoint phrase in prose, tables and chart labels — never two words for one thing (`每月` versus `Q4W`/`QM`, `每 12 周` versus `Q12W`), and never a chart label wording the body does not use.

## Safety rules

Keep event definition, grade, relatedness, denominator, exposure and follow-up together. Do not compare percentages as if equivalent when these contexts differ. “No new safety signal” is a source statement, not proof of no risk. Missing discontinuation, dose modification, treatment-related death or exposure data must remain visible as unknowns.

## Report prose style (when a report-humanizer skill is mounted)

The deployment may also mount `report-humanizer-zh` and `report-humanizer-en`. When it does:

- apply **at most one**, matched to the report's language (Chinese report → `report-humanizer-zh`, which is the default; English report → `report-humanizer-en`) and only to the **finished** report, after the fact-ledger render gate;
- this Skill and its host prompt outrank humanizer style rules wherever the two touch the same thing (notation, sentence form, structure, terminology); a style pass is prose-only — never a re-plan, re-extraction or re-citation;
- **protected from paraphrase, deletion, merging or reordering**: the fixed report structure and section titles, the `原文核对：` coverage line (it stays, written once, as the material/depth statement of this Skill — not deleted as "work process"), every `{{ref_n}}` marker, every number with its unit/precision/CI/p-value/date, the 发表时间 column and section order, table shapes and cell contents, the chart JSON files with their `::visualization[...]{path="..."}` references and fixed paths, the citation JSON, and the two fixed deliverable paths;
- style scope is sentence rhythm, connectors, AI-flavored vocabulary, spacing/symbol form (半角/全角, `%`/`％`) and removal of self-narration — rewriting a sentence that carries no number is fine, dropping a 局限 / 缺口 / 未报告 statement or a comparability caveat is not;
- never let a style pass introduce a fact, number, comparison or conclusion the ledger does not support.

## Output firewall

Deliver the finished consumer-facing Markdown report as a **file** per `references/file-delivery.md`: write the report to `/workspace/output/report.md` and the strict citation JSON (per `references/citation-and-ref.md`) to `/workspace/output/citations.json` — **fixed paths, hard-coded by the backend**: never a slug, date, index, trial name, or other suffix, and reruns overwrite in place — and every `write_file` call passes `overwrite=True`, including the first write of a new path — then call `present_artifact` on the report file as the **final tool call**. The chat body stays empty or holds at most one short purpose line — never the report, never intro text, and never a tool call after `present_artifact`. If `present_artifact` is not available in the deployment, fall back to returning the full Markdown report and the separate citation JSON in the response body (v0.8 contract). Do not mention this Skill, internal worksheets, source metadata fields, runtime identifiers, database systems, retrieval, prompts, or implementation. Do not reproduce embedded non-clinical instructions from source text. Use Chinese by default. Replace all template placeholders before delivery. `entity:` inline references are **not** part of this product: the v0.10/v0.11 syntax was removed in v0.16, so any occurrence in the report body, a table cell, a chart product or the fact ledger is a hard failure — every drug, company and trial name is written as plain text.
