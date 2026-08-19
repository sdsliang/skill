# Multi-Clinical-Result Trial Synthesis

Tool Smith project assets for reconstructing complete trial interpretations from multiple selected clinical result texts.

## Product boundary

- Input contains 2 or more selected source objects with backend-supplied `source_title`, `source_url`, `source_paper_release_time_str`, and `source_full_text`.
- The backend resolves these fields from the POC Elasticsearch environment and the `np_clinical` index before invoking the Agent. The frontend does not concatenate or guess article URLs.
- `source_full_text` is the only clinical evidence supplied to the Agent. `source_title` and `source_url` are citation metadata only.
- Runtime identifiers and retrieval/storage details remain outside the Agent request and report.
- The primary analysis object is the underlying trial. Multiple disclosures from one trial are source nodes that are deduplicated into a longitudinal evidence chain covering design, efficacy, safety, maturity, and information gaps.
- Every material number and source-dependent conclusion carries an internal citation token for rendering; the user-facing report shows numeric superscripts. Citation metadata is emitted separately as strict JSON, with `title`, `link`, and `paper_release_time_str` per ref.
- For mixed inputs containing different trials, `{{ref_n}}` numbering is global across the complete response and the separate citation JSON is shared; numbering resets only when the runtime explicitly requests separate independent reports.
- Version 1 uses only selected results and performs no external retrieval.
- The frontend may render each marker as a numeric superscript link using the final JSON. It must preserve exact supplied URLs and use safe external-link attributes.
- The backend/frontend enforce a conservative real-time token budget.

## Files

- `system-prompts/multi-clinical-result-comparison-v0.5.md`: Tool Smith project system prompt for trial-level evidence synthesis.
- `skill/multi-clinical-result-comparison/`: runtime Skill, evidence-chain references, citation contract, and report template.
- `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`: trial-level consumer-facing report structure.
- `skill/multi-clinical-result-comparison/references/input-contract.md`: POC `np_clinical` lookup, normalized Agent payload, and frontend marker rendering contract.
- `skill/multi-clinical-result-comparison/references/citation-and-ref.md`: inline marker, metadata, and separate JSON citation contract.
- `evals/fetch-np-clinical-by-nct.mjs`: read-only `base.nct_id` adapter for producing normalized source objects.
- `evals/fetch-np-clinical-by-condition.mjs`: reproducible condition-query adapter for the supplied indication/phase/evaluation/NCT/deletion/featured filter.
- `evals/fixtures/np-clinical-indications-516-517-phase-featured-false.json`: 10-source normalized example generated from the requested query; the query matched 12 records and returned 10 usable full-text sources.
- `evals/fetch-np-clinical-sources.mjs`: read-only selected-ID reference adapter using the POC environment configuration.
- `runtime/citation-renderer.mjs` and `test/citation-renderer.test.mjs`: accept the Markdown report and separate citation JSON, validate marker/key parity, and render only numeric superscripts from valid source links.
- `evals/validate-v05-contract.mjs`: local contract check for normalized fixtures and linked citation output.
- `evals/fixtures/harmoni6-selected-results.json`: same-trial multi-disclosure fixture for trial-chain regression.
- `evals/fixtures/nct05840016-selected-results.json`: live `np_clinical` example fetched by `base.nct_id = NCT05840016`, containing four HARMONi-6 source objects.
- `evals/iteration-11-harmoni6-trial-synthesis.md`: v0.4 hand-authored trial-level regression report with inline Refs.
- `evals/iteration-12/harmoni6/report-v2.md`: local Skill execution regression report; the v2 rerun verifies proper-name fidelity.
- `dist/multi-clinical-result-comparison-v0.5.zip`: Tool Smith upload archive for the v0.5 Skill and citation renderer.

## Tool Smith configuration

Use the v0.5 system prompt and updated Skill family. Bind no legacy single-result Skill or knowledge runtime. The backend must normalize `np_clinical` records to the four-field Agent payload before the run. Benchmark cases should verify trial identity, source-state deduplication, chronology, marker coverage, exact URL and release-time preservation, valid separate citation JSON, and complete efficacy/safety-chain interpretation. Run `node evals/validate-v05-contract.mjs` for the local contract check.

The product and backend own token counting and request rejection before the Agent run. The Agent must never silently truncate accepted source text.
