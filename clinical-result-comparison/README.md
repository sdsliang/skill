# Multi-Clinical-Result Trial Synthesis

Tool Smith project assets for reconstructing complete trial interpretations from multiple selected clinical result texts.

## Product boundary

- Input is delivered as **attachments**: each selected clinical result is one `.md` file (`source-001.md`, `source-002.md`, …), sent together in the user turn. Each file carries backend-supplied `source_title`, `source_url`, and `source_paper_release_time_str` metadata lines, optional entity-ID metadata lines (`source_nct_id`, `source_drug_entities`, `source_company_entities`) for inline entity references, plus the full text under `## source_full_text`. The full text is the only clinical evidence supplied to the Agent; the entity-ID lines are display/label metadata only.
- The backend resolves these fields from the POC Elasticsearch environment and the `np_clinical` index, writes one file per selected result, and the frontend attaches the files. The frontend does not concatenate or guess article URLs.
- Per-source files keep large selections (20–50 results) addressable without blowing the per-message context budget; the Agent reads each attached file and assigns `{{ref_n}}` in file order. File order is a presentation label, not clinical chronology.
- Runtime identifiers and retrieval/storage details remain outside the Agent request and report.
- The primary analysis object is the underlying trial. Multiple disclosures from one trial are source nodes that are deduplicated into a longitudinal evidence chain covering design, efficacy, safety, maturity, and information gaps.
- Every material number and source-dependent conclusion carries an internal citation token for rendering; the user-facing report shows numeric superscripts. Citation metadata is emitted separately as strict JSON, with `title`, `link`, and `paper_release_time_str` per ref.
- For mixed inputs containing different trials, the deliverable is comparison-first and domain-aligned: efficacy, safety, PK/PD, and PRO are aligned across trials so the user can judge which treatment is better or worse, with explicit comparability/evidence-strength labels and compact per-trial context. The report does not pool results or fabricate head-to-head proof. `{{ref_n}}` numbering is global across the complete response and the separate citation JSON is shared; numbering resets only when the runtime explicitly requests separate independent reports.
- Version 1 uses only selected results and performs no external retrieval.
- The frontend may render each marker as a numeric superscript link using the final JSON. It must preserve exact supplied URLs and use safe external-link attributes.
- The backend/frontend enforce a conservative real-time token budget.

## Files

- `system-prompts/multi-clinical-result-comparison-v0.10.md`: Tool Smith project system prompt for trial-level evidence synthesis (current; attachment-based input, HTML visualizations, file-based report delivery via `present_artifact`, entity inline references).
- `skill/multi-clinical-result-comparison/`: runtime Skill, evidence-chain references, citation contract, and report template.
- `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`: single-trial consumer-facing report structure.
- `skill/multi-clinical-result-comparison/references/timeline-diagram.md`: construction rules for the evidence-chain timeline as an HTML visualization (same-trial, ≥2 distinct evidence states) built on `templates/charts/evidence-timeline.html` with `::visualization` references; no Mermaid.
- `skill/multi-clinical-result-comparison/templates/cross-trial-report.md`: comparison-first, domain-aligned report structure for multiple independent trials (efficacy, safety, PK/PD, PRO).
- `skill/multi-clinical-result-comparison/references/file-delivery.md`: v0.9 file-delivery contract — final report written to `/workspace/output/<slug>-report.md`, citation JSON to `/workspace/output/<slug>-citations.json`, delivered with `present_artifact` as the terminal tool call, empty/minimal chat body.
- `skill/multi-clinical-result-comparison/references/citation-and-ref.md`: inline marker, metadata, and separate JSON citation contract.
- `skill/multi-clinical-result-comparison/references/entity-inline-reference.md`: v0.10 entity inline reference contract — `[name](entity:type:id)` links for 药品/公司/临床试验注册号, with IDs only from the attachment metadata lines (`source_nct_id`, `source_drug_entities`, `source_company_entities`), no fabricated IDs, no entity refs inside chart files.
- `skill/multi-clinical-result-comparison/references/chart-templates.md` + `templates/charts/`: blue-purple HTML chart templates (evidence timeline / bar / line) with `--viz-*` injection mapping; the bar template renders ORR-type single-value comparisons.
- `evals/fetch-np-clinical-attachments.mjs`: reproducible condition-query adapter that writes one `.md` attachment file per source plus a backend `manifest.json`, with a built-in round-trip check. v0.10 also pulls `base.nct_id`/`base.trial_drug`/`trial_details` and enriches each file with optional `source_nct_id`, `source_drug_entities` (drug_earth), and `source_company_entities` (resolved to `base_company` display names) metadata lines.
- `evals/fetch-np-clinical-by-nct.mjs`: read-only `base.nct_id` adapter for producing normalized source objects.
- `evals/fetch-np-clinical-by-condition.mjs`: original condition-query adapter for the supplied indication/phase/evaluation/NCT/deletion/featured filter.
- `evals/fixtures/np-clinical-indications-516-517-phase-featured-false.json`: 10-source normalized example generated from the requested query; the query matched 12 records and returned 10 usable full-text sources.
- `evals/fetch-np-clinical-sources.mjs`: read-only selected-ID reference adapter using the POC environment configuration.
- `runtime/citation-renderer.mjs` and `test/citation-renderer.test.mjs`: accept the Markdown report and separate citation JSON, validate marker/key parity, and render only numeric superscripts from valid source links.
- `evals/validate-v05-contract.mjs`: local contract check for normalized fixtures and linked citation output.
- `evals/fixtures/harmoni6-selected-results.json`: same-trial multi-disclosure fixture for trial-chain regression.
- `evals/fixtures/nct05840016-selected-results.json`: live `np_clinical` example fetched by `base.nct_id = NCT05840016`, containing four HARMONi-6 source objects.
- `evals/iteration-11-harmoni6-trial-synthesis.md`: v0.4 hand-authored trial-level regression report with inline Refs.
- `evals/iteration-12/harmoni6/report-v2.md`: local Skill execution regression report; the v2 rerun verifies proper-name fidelity.
- `dist/multi-clinical-result-comparison-v0.10.zip`: Tool Smith upload archive for the v0.10 Skill (attachment-based input, HTML visualization path, file-based report delivery, entity inline references), citation renderer, file-delivery reference, entity-inline-reference reference, timeline diagram reference, and chart templates.

## v0.10 changes

- **Entity inline references** (药品 / 公司 / 临床试验注册号). When an attachment file carries the new entity-ID metadata lines, the Agent renders every mention of those drugs, companies, and the registration number as Tool Smith entity links `[name](entity:drug:id)` / `[name](entity:company:id)` / `[name](entity:trial:NCT…)` so the frontend `EntityAnchor` shows clickable entity tags. The artifact reader (`ArtifactMarkdownViewer` → `ChatMarkdown` → `EntityAnchor`) already renders these, so the frontend needs no changes.
- **ID source = backend metadata passthrough**: new `references/entity-inline-reference.md`; `references/input-contract.md` adds the `source_nct_id` / `source_drug_entities` / `source_company_entities` lines (metadata-line priority for nct_id; no text-extraction fallback). The Agent never fabricates IDs and never queries tools for IDs.
- `evals/fetch-np-clinical-attachments.mjs` enriches each attachment with the entity lines: `base.nct_id` → `source_nct_id` (first clean token, NCT preferred), `base.trial_drug` meta → `source_drug_entities` (`名称|drug_earth|ID`), and `trial_details` `company_ids` → `source_company_entities` via a `base_company` `terms`-on-`id` resolution (`name_show_cn` → `short_name` → `name`). Graceful degradation: a source with no IDs simply omits the line.
- Entity metadata lines are **display/label metadata, not clinical evidence**; entity refs coexist with `{{ref_n}}` and never appear inside `::visualization` chart files.
- Scope is limited to drug + company + trial registration number; indication/target remain disabled (no metadata lines).
- New system prompt `system-prompts/multi-clinical-result-comparison-v0.10.md`; historical v0.3–v0.9 prompts remain as snapshots.

## v0.9 changes

- **File-based report delivery via `present_artifact`** (方案 B). The finished report is no longer streamed as chat text. It is written to `/workspace/output/<slug>-report.md` (report template content with inline `{{ref_n}}` markers and `::visualization` references) and the strict citation JSON to `/workspace/output/<slug>-citations.json`, then the report file is delivered with `present_artifact` as the **final tool call**. The chat body stays empty or holds at most one short purpose line — no intro text, no report content, and no tool call after `present_artifact`.
- Backend no longer parses model output: it serves the report and citation files directly from the artifacts API; the citation file is a visible workspace artifact even without a card.
- `{{ref_n}}` markers and the separate citation JSON schema are unchanged; downstream consumers render markers using the citation file. New `references/file-delivery.md` is the authoritative delivery contract.
- New system prompt `system-prompts/multi-clinical-result-comparison-v0.9.md`; historical v0.3–v0.8 prompts remain as snapshots.
- `runtime/citation-renderer.mjs` adds `validateCitationPair(report, citationJson)` (parity check without rendering) with tests.

## v0.8 changes

- All charts (same-trial evidence timeline and cross-trial bar/line) moved from Mermaid to **HTML templates + `::visualization` references**. `references/timeline-diagram.md` rewritten to build the timeline from `templates/charts/evidence-timeline.html` (one event per evidence state, merging duplicate disclosures); `references/cross-trial-comparison.md` chart contract now uses `endpoint-bar.html`/`endpoint-line.html`; templates `unified-evidence-report.md`, `mixed-comparison-report.md`, `cross-trial-report.md`, `SKILL.md`, and `system-prompts/multi-clinical-result-comparison-v0.8.md` updated. Cross-trial/mixed reports grouped by clinical question produce **one bar chart per group** (each group its own `endpoint-bar.html` product file; experimental-arm values side by side; comparators and boundaries in hover notes; 跨试验并列展示≠头对头比较 stated). No Mermaid output anywhere.
- References use **absolute paths** per the Tool Smith visualization contract: files are written to `/workspace/visualizations/` first, then `::visualization[标题]{path="/workspace/visualizations/xxx.html"}` on its own line (no relative path, no `..`/backslash/out-of-prefix, ASCII filename, no subdirectory, ≤1 MiB for HTML). Charts are **HTML fragments** (no `<!doctype html>`/`<html>`/`<head>`/`<body>` document wrapper — Tool Smith injects them with the widget fragment renderer; it validates by substring match over the whole file, so `<head`-prefixed tags like `<header>` must be avoided, templates use `<div class="header">`). The full delivery-path contract lives in `references/chart-templates.md`.
- New system prompt `system-prompts/multi-clinical-result-comparison-v0.8.md`; historical v0.3–v0.7 prompts remain as snapshots.

## v0.7 changes

- Input switched from inline JSON in a single message to **one attached `.md` file per selected result** (attachment-based delivery). Each file carries the four consumer fields (metadata lines + full text under `## source_full_text`); the Agent reads every attached file in filename order and assigns `{{ref_n}}` markers in that order. This keeps large selections (20–50 results) within the context budget.
- `references/input-contract.md` rewritten: per-source file layout, attachment limits (10 per message / 100 per thread / 20 MiB per file), Agent reading protocol, and backend manifest. `SKILL.md` and `system-prompts/multi-clinical-result-comparison-v0.7.md` updated accordingly.
- `evals/fetch-np-clinical-attachments.mjs`: pulls `np_clinical` by condition (default: non-small-cell lung cancer 135/5718/5719 + phase 3 + positive evaluation, ~890 matched) and writes one attachment file per source plus `manifest.json`, with a built-in round-trip check.

## v0.6 changes

- Same-trial inputs with two or more distinct evidence states now output a descriptive Mermaid evidence-chain timeline diagram directly above the timeline table in the 证据链总览与时间线 section, per `references/timeline-diagram.md`: one node per evidence state with key labels and `{{ref_n}}` markers, a source-supported time axis (时间未明 when missing), dotted time-to-state links, and a labeled relationship + maturity-direction arrow between consecutive states.
- The diagram is descriptive/chronological and does not require numeric compatibility; it never replaces the exact-value timeline table. Quantitative charts remain restricted. If only one distinct state remains or order cannot be determined, no diagram is generated and the order uncertainty is stated in the table.

## Tool Smith configuration

Use the v0.10 system prompt and updated Skill family. The project must enable the **`artifact_presentation`** capability (per-project switch, default OFF) and keep the **`visualization`** capability on (report files embed `::visualization` references). Bind no legacy single-result Skill or knowledge runtime. The backend must normalize `np_clinical` records to the consumer shape (four citation fields + optional entity-ID lines: `source_nct_id`, `source_drug_entities`, `source_company_entities`) and write one `.md` attachment file per selected source before the run; the frontend attaches the files and renders `entity:` links as entity tags via the existing `EntityAnchor`. Benchmark cases should verify trial identity, source-state deduplication, chronology, marker coverage (markers match attached-file order), exact URL and release-time preservation, valid citation JSON file, the evidence-chain timeline diagram (when applicable), complete efficacy/safety-chain interpretation, entity references using only metadata-supplied IDs (no fabrication, every available mention referenced), and that the report is delivered as a presented artifact file with an empty/minimal chat body.

The product and backend own token counting and request rejection before the Agent run. The Agent must never silently truncate accepted source text.
