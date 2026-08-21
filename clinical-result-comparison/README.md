# Multi-Clinical-Result Trial Synthesis

Tool Smith project assets for reconstructing complete trial interpretations from multiple selected clinical result texts.

## Product boundary

- Input is delivered as **attachments**: each selected clinical result is one `.md` file (`source-001.md`, `source-002.md`, …), sent together in the user turn. Each file carries backend-supplied `source_title`, `source_url`, and `source_paper_release_time_str` metadata lines plus the full text under `## source_full_text`. The full text is the only clinical evidence supplied to the Agent.
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

- `system-prompts/multi-clinical-result-comparison-v0.7.md`: Tool Smith project system prompt for trial-level evidence synthesis (current; attachment-based input).
- `skill/multi-clinical-result-comparison/`: runtime Skill, evidence-chain references, citation contract, and report template.
- `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`: single-trial consumer-facing report structure.
- `skill/multi-clinical-result-comparison/references/timeline-diagram.md`: construction rules for the evidence-chain Mermaid timeline diagram (same-trial, ≥2 distinct evidence states).
- `skill/multi-clinical-result-comparison/templates/cross-trial-report.md`: comparison-first, domain-aligned report structure for multiple independent trials (efficacy, safety, PK/PD, PRO).
- `skill/multi-clinical-result-comparison/references/input-contract.md`: `np_clinical` lookup, per-source attachment file layout, delivery limits, Agent reading protocol, and frontend marker rendering contract.
- `skill/multi-clinical-result-comparison/references/citation-and-ref.md`: inline marker, metadata, and separate JSON citation contract.
- `skill/multi-clinical-result-comparison/references/chart-templates.md` + `templates/charts/`: blue-purple HTML chart templates (evidence timeline / bar / line) with `--viz-*` injection mapping; the bar template renders ORR-type single-value comparisons.
- `evals/fetch-np-clinical-attachments.mjs`: reproducible condition-query adapter that writes one `.md` attachment file per source plus a backend `manifest.json`, with a built-in round-trip check.
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
- `dist/multi-clinical-result-comparison-v0.7.zip`: Tool Smith upload archive for the v0.7 Skill (attachment-based input), citation renderer, timeline diagram reference, and chart templates.

## v0.7 changes

- Input switched from inline JSON in a single message to **one attached `.md` file per selected result** (attachment-based delivery). Each file carries the four consumer fields (metadata lines + full text under `## source_full_text`); the Agent reads every attached file in filename order and assigns `{{ref_n}}` markers in that order. This keeps large selections (20–50 results) within the context budget.
- `references/input-contract.md` rewritten: per-source file layout, attachment limits (10 per message / 100 per thread / 20 MiB per file), Agent reading protocol, and backend manifest. `SKILL.md` and `system-prompts/multi-clinical-result-comparison-v0.7.md` updated accordingly.
- `evals/fetch-np-clinical-attachments.mjs`: pulls `np_clinical` by condition (default: non-small-cell lung cancer 135/5718/5719 + phase 3 + positive evaluation, ~890 matched) and writes one attachment file per source plus `manifest.json`, with a built-in round-trip check.

## v0.6 changes

- Same-trial inputs with two or more distinct evidence states now output a descriptive Mermaid evidence-chain timeline diagram directly above the timeline table in the 证据链总览与时间线 section, per `references/timeline-diagram.md`: one node per evidence state with key labels and `{{ref_n}}` markers, a source-supported time axis (时间未明 when missing), dotted time-to-state links, and a labeled relationship + maturity-direction arrow between consecutive states.
- The diagram is descriptive/chronological and does not require numeric compatibility; it never replaces the exact-value timeline table. Quantitative charts remain restricted. If only one distinct state remains or order cannot be determined, no diagram is generated and the order uncertainty is stated in the table.

## Tool Smith configuration

Use the v0.7 system prompt and updated Skill family. Bind no legacy single-result Skill or knowledge runtime. The backend must normalize `np_clinical` records to the four-field consumer shape and write one `.md` attachment file per selected source before the run; the frontend attaches the files. Benchmark cases should verify trial identity, source-state deduplication, chronology, marker coverage (markers match attached-file order), exact URL and release-time preservation, valid separate citation JSON, the evidence-chain timeline diagram (when applicable), and complete efficacy/safety-chain interpretation. Run `node evals/validate-v05-contract.mjs` for the local contract check and `node evals/fetch-np-clinical-attachments.mjs <dir> <size>` to produce a reproducible attachment batch.

The product and backend own token counting and request rejection before the Agent run. The Agent must never silently truncate accepted source text.
