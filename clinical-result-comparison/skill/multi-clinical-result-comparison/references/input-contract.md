# Input Contract (v0.12: esid + params tool)

## Purpose

Each selected clinical result is delivered to the Agent as a **clinical-result esid** (the record ID,
`clinical_result.extra_esid`), not as an attached `.md` file and not as inline JSON in a message. The
frontend sends the selected esid list in the user turn (in user-selection order); the Agent then pulls
the detail records itself through the MCP tool `pharmcube-query-clinical-result-with-params`, filtering
by `extra_esids` and keeping the returned payload small via a strict `selected_fields` allowlist.

Rationale: a user may select many results (for example 20–50). A single params response with many
unselected fields can exceed the context budget (`MCP_TOOL_RESULT_MAX_CHARS`); per-esid `{{ref_n}}`
mapping keeps each result addressable, bounds context by what the Agent actually needs, and keeps the
citation mapping stable (3rd esid in input order → `{{ref_3}}`).

## Source of truth

- MCP tool name: `pharmcube-query-clinical-result-with-params`.
- Data source: 医药魔方 TrialiCube (`clinical_trial_result_structured`).
- `extra_esids` = exact-filter by clinical-result ID (each selected esid = one clinical result / one
  disclosure of a trial).
- `selected_fields` = array of field-name strings, **each copied verbatim** from the
  ALLOWED_FIELD_NAMES list. Field names are case-sensitive and must not be descriptions.
  The authoritative full field list + nested shapes live in `docs/params-tool-schema.md`
  (archived from the running tool schema). **Anchor field for selection: `clinical_result.extra_esid`.**
- The response injects the record `_id`; per-record fields appear under their selected names
  (nested: `arms`, `projects`, `study_results`, …).

## Pull protocol

1. Read the selected esid list from the user turn (input order = `{{ref_n}}` assignment order).
2. Call the tool with:
   - `extra_esids: [ ...selected esids in input order ... ]`;
   - `selected_fields`: the recommended minimal set below (trim further if a run is huge).
3. Keep the returned payload small: never request the whole record, never request fields you do not
   need, never re-pull the same esids speculatively once the needed fields are present.
4. Map records back to esids by `clinical_result.extra_esid` (or the record `_id`) in input order →
   `{{ref_1}}`, `{{ref_2}}`, … . If a record is missing or empty, record it in the source inventory as
   a limitation, never drop it silently and never reorder the markers.

### Recommended `selected_fields` (per disclosure record)

Pick the subset needed for the actual run; these cover trial identity, design/arms, evidence text and
structured results. Field names below are verbatim from ALLOWED_FIELD_NAMES.

- Citation: `clinical_result.paper_title`, `clinical_result.full_article_link`,
  `clinical_result.paper_release_time` (+ `clinical_result.journal`, `clinical_result.doi`,
  `clinical_result.pm_id` when needed).
- Trial identity/company: `clinical_result.trial_abbreviation`, `clinical_result.projects`
  (nested: `projects.group_id`, `projects.associate_ids`, `projects.company_ids`,
  `projects.company_name_cn`/`company_all_name`).
- Design/arms/population: `clinical_result.arms` (nested: arm type / `drugs[].drug_earth_id` +
  names + target/moa as needed), `clinical_result.randomized`, `clinical_result.blinded`,
  `clinical_result.trial_control`, `clinical_result.positive_placebo_control`,
  `clinical_result.group_count`, `clinical_result.random_ratio`, `clinical_result.multi_center`,
  `clinical_result.clinical_stage_cn`, `clinical_result.therapy_line_cn`,
  `clinical_result.indication_name`, `clinical_result.evidence_source`, `clinical_result.evaluation`.
- Evidence text + structured results (core clinical content):
  `clinical_result.abstract_text`, `clinical_result.summary`, `clinical_result.study_results`
  (nested endpoint results: endpoint label/type, `result`/`compare_result`, `result_unit`,
  `p_value`/`outcome_p_value`, `outcome_ci`/`compare_result_ci`, `hazard_ratio`(+CI),
  `odd_ratio`, `relative_risk`, arm_type/arm_id(s)), `clinical_result.key_evidence`.
- Images (pass-through, shown as-is when useful): `clinical_result.participant_flow`,
  `clinical_result.baseline_characteristics`, `clinical_result.inclusion_criteria`.

Do not pull large aggregates of unrelated esids; if a batch is big, split the pull (see
"Large-batch delegation") or tighten `selected_fields` further.

## Consumer-field mapping (v0.11 attachment fields → params fields)

| v0.11 attachment field | v0.12 params field(s) |
| --- | --- |
| `source_title` | `clinical_result.paper_title` |
| `source_url` | `clinical_result.full_article_link` |
| `source_paper_release_time_str` | `clinical_result.paper_release_time` |
| `source_nct_id` | `clinical_result.projects[].associate_ids` (registration no.) |
| `source_trial_abbr` | `clinical_result.trial_abbreviation` |
| `source_drug_entities` (drug_earth ids) | `clinical_result.arms[].drugs[].drug_earth_id` + `drug_earth_name_*` |
| `source_company_entities` (base_company ids) | `clinical_result.projects[].company_ids` + `company_name_*` |
| `source_full_text` | no direct equivalent → `abstract_text` / `summary` / `study_results` combined |

**Entity-ID fields** (`projects.associate_ids`, `trial_abbreviation`, `arms[].drugs[].drug_earth_id`,
`projects.company_ids`) are **display/label metadata, not clinical evidence** — the Agent uses them
solely to attach entity inline references to mentions already present in the report (see
`references/entity-inline-reference.md`), never to derive clinical facts. Missing entity fields mean
that entity type is not referenced for that record (graceful degradation).

The Agent must never print, quote, or transmit raw field values, record `_id`s, index/table names,
storage paths, or tool diagnostics into the report body; and must not fabricate or guess a missing
title, URL, or release time — a missing value stays empty in the citation JSON.

## Response limits

- A params response is a single tool result. If a pull would be very large (many esids × many fields),
  split into multiple tool calls by esid ranges or tighten `selected_fields`; never let one response
  blow the context budget.
- Prefer re-requesting only missing fields over pulling everything again.

## Agent consumption protocol

1. Read the selected esid list (input order = marker order).
2. Pull records with the recommended `selected_fields`; map each returned record to its esid.
3. For each record, keep an internal ledger:
   - citation fields (`paper_title`, `full_article_link`, `paper_release_time`, and when returned
     `journal`/`doi`/`pm_id`) for the separate final citation JSON;
   - trial identity: registration no. (`projects.associate_ids`), trial short name
     (`trial_abbreviation`), sponsor (`company_ids`/`company_name_*`), drug IDs/names
     (`arms[].drugs[].drug_earth_id` + names);
   - clinical content fields: `abstract_text`, `summary`, `study_results` (endpoint records),
     design/arms context.
4. Build the internal worksheet exactly as described in `references/input-and-extraction.md`, using
   these pulled fields as the per-record source.

## Large-batch delegation via subagents (OPTIONAL, pending verification)

> ⚠️ Status: **not yet validated in a real Tool Smith deployment.** Keep this as an opt-in strategy;
> the default path remains "Agent pulls every selected esid directly" per the protocol above.

When the deployment exposes the `task` tool (backend `SubAgentCapability` registered and
`capabilities_config.subagents` enabled) and the number of selected esids is large
(recommendation: ≥ 20), the Agent MAY delegate extraction to subagents to keep the main-thread context
bounded. This is a performance strategy, **not a change to the evidence boundary**: only the pulled
fields (`abstract_text`/`summary`/`study_results`/design context) are evidence, and every extracted
value must still carry its source esid / marker number.

- **Chunking**: split the esid list by input order into chunks of at most 10 esids each (e.g. 50 esids
  → 5 chunks). Chunk boundaries must never reorder markers.
- **One `task` call per chunk**: `subagent_type: "general-purpose"`, with a fully self-contained
  `description` stating exactly which esids to pull (or the tool call parameters), the exact
  `selected_fields` to use, the exact per-trial fields to extract (same as the evidence worksheet in
  `references/input-and-extraction.md`), and the exact compact output format including the source esid
  / marker number on every extracted value.
- **Output discipline**: the subagent returns only a compact structured summary (short trial name,
  arm/label, endpoint values, p-values/CIs, source marker). Keep the returned text small (a few hundred
  characters per trial) so 5–10 summaries do not re-bloat the main thread.
- **Citation correctness**: `{{ref_n}}` assignment stays global by input esid order regardless of
  which chunk processed it. Subagents must echo the source marker; the main Agent maps those to ref
  markers and deduplicates.
- **Constraints**: subagents are stateless (single `description`, no follow-ups — put everything needed
  in it); recursive depth is limited (do not nest delegation deeper than one level); multiple `task`
  calls in one message are allowed but concurrency is not guaranteed — treat serial execution as
  acceptable.
- **Fallback**: if the `task` tool is not visible/available, ignore this section and pull every
  selected esid directly (default protocol). Never skip a source because delegation is unavailable.

**Verification checklist before enabling as default** (see pending questions with the Tool Smith
developer):
1. `capabilities_config.subagents` is enabled on the deployment and `task` is visible to the Agent.
2. Subagents can reach the params MCP tool with the same credentials/quota, and 20–50 esids are pulled
   reliably in one run.
3. Concurrent `task` calls are either truly concurrent or acceptably fast serially.
4. Measured token cost: 5–10 compact summaries + aggregation stay well under the run budget.

## Citation rendering

The Agent emits machine-readable `{{ref_n}}` tokens in the Markdown report. Both the report and the
citation metadata are delivered as workspace files under `/workspace/output/` (see
`references/file-delivery.md`): the report is presented with `present_artifact` as the final tool call,
and the citation file is a supporting machine-readable artifact (listed by the artifacts API without
needing a card). The citation metadata must not be appended to the report or passed through a generic
Markdown autolinker. The frontend/consumer fetches the report file and the citation file from the
artifact endpoints, validates marker/key parity, then renders only the report body.

```html
<sup class="source-citation"><a href="SUPPLIED_LINK" title="SUPPLIED_TITLE" target="_blank" rel="noopener noreferrer">n</a></sup>
```

Render only validated `http`/`https` links. Escape the title and URL for HTML attributes, prevent
arbitrary HTML interpolation, and leave the marker as plain text or an unavailable citation state when
the link is empty. Only the numeric superscript is clickable; never wrap the surrounding sentence,
paragraph, table cell, or punctuation in the citation anchor. Do not expose the citation JSON in the
visible report body.

## Local verification note

The v0.11 reproducible adapter (`evals/fetch-np-clinical-attachments.mjs`, writing `source-*.md`) is
superseded by the params tool path. Field-name grounding for pulls now comes from the archived tool
schema in `docs/params-tool-schema.md`; if a live schema dump is ever available at a routable data
service, re-verify the archived ALLOWED_FIELD_NAMES against it before changing `selected_fields`.
Production request orchestration remains owned by the backend; the params tool is the delivery path.
