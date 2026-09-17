# Citation and Linked-Source Traceability

## Goal

Make every material number and source-dependent conclusion in a trial synthesis traceable to one supplied source. Inline markers are presentation-stable tokens that the frontend converts to numeric superscript links; they do not represent independent trials, evidence grades, or chronology. Entity inline references (`[name](entity:type:id)`, v0.10) are a separate display feature that coexists with markers — see `references/entity-inline-reference.md`; they never replace or alter marker placement.

## Input metadata

Each selected clinical result is pulled by esid through the MCP tool `pharmcube-query-clinical-result-with-params` (`extra_esids` + strict `selected_fields`, see `references/input-contract.md`). The consumer-facing citation fields map from the returned record as:

```json
{
  "title": "paper_title",
  "link": "full_article_link",
  "paper_release_time_str": "paper_release_time → date part only (YYYY-MM-DD)"
}
```

Only the fields that carry clinical content (`abstract_text`, `summary`, `study_results`, design/arms context) support clinical claims, and they are pipeline-processed extracts: the original source is the first-priority check for material numbers (see `references/input-contract.md`, *Evidence source priority*) and wins on divergence. `paper_title`, `full_article_link`, `paper_release_time`, `journal`, `doi`, and `pm_id` are citation metadata. Do not derive clinical facts from them; `doi` / `pm_id` / a registration id serve only as the route keys of the whitelisted fetch templates. `title` and `link` are preserved byte-for-byte and are never completed, transformed, or guessed — with **one** exception below (*link follows the analysis depth*).

`paper_release_time` comes back as a **datetime string** (`YYYY-MM-DD HH:MM:SS`, e.g. `2018-12-19 00:00:00`); the citation value is its **date part only**: keep `YYYY-MM-DD` (the first 10 characters, after checking they match `\d{4}-\d{2}-\d{2}`) and drop the time component. Never reformat beyond that, never convert to another format or timezone, and never invent or complete a missing date: an empty value stays `""`, and a value that does not begin with a date is passed through unchanged.

Assign markers in selection (esid) order over the records that actually came back: `{{ref_1}}`, `{{ref_2}}`, and so on. This ordering is stable but does not establish clinical chronology.

**One esid can return several rows.** With `clinical_result.indication_name` (`_en`) requested, the backend joins a disease dimension and returns one row per disease id for the same record, the rows differing only in an injected `disease_id`. Fan-out rows are **one** source: de-duplicate by `clinical_result.extra_esid` before numbering, keep the first row, and never emit one marker or one citation key per row (see `references/input-contract.md`, *Row fan-out*).

**A selected record that did not come back is not a source.** The params tool returns `ok: true` with an empty `data` array — no error — for an esid that does not exist or is not visible, so retrieve the whole selection in one batched call and confirm the gaps in at most one further call for exactly those esids; never probe variant spellings or guessed ids and never loop per esid (see `references/input-contract.md`, *Unretrievable selected items*). Such an esid gets **no** marker and **no** citation key: never emit an entry with an empty `title` — an empty-title entry is the signature of a citation written for a record that never returned. Name the unretrieved items in the evidence-scope paragraph as a limitation instead. If fewer than two usable records come back, write neither the report nor the citation file and tell the user in chat which selections could not be retrieved.

## Inline syntax

Markers are internal presentation tokens. The visible report should not explain or spell out `{{ref_n}}` in its evidence-scope paragraph; the frontend replaces them with numeric superscripts.

Use markers at the end of the supported sentence, bullet, or table cell:

```text
中位 PFS 为 11.1 个月（95% CI 9.9-NE），对照组为 6.9 个月（95% CI 5.8-8.6），HR 0.60（95% CI 0.46-0.78；单侧 p<0.0001）。{{ref_1}}

11.1 个月（95% CI 9.9-NE）{{ref_1}}
```

For a claim fully supported by more than one source, concatenate markers without punctuation: `{{ref_1}}{{ref_3}}`.

Granularity is the **sentence / bullet / table cell, not the individual number**. When one sentence (or one cell) as a whole rests on one source, a single marker at its end is enough — three numbers in that sentence still need only one marker. Attach several markers to one sentence **only when the sentence genuinely mixes facts from different sources**, and then place each marker at the end of the clause it supports (a separated `{{ref_1}} … {{ref_3}}` inside one sentence is fine; a concatenated `{{ref_1}}{{ref_3}}` means both sources support the whole claim).

Never fragment citations to satisfy the marker rule: do not split a sentence, bullet, or table row into several lines just to hang a marker on each part, do not bolt a marker onto every number, and do not run repeated `edit_file` passes to redistribute markers — decide the marker placement together with the text in the single report write (or in the generator script that renders it).

## Claims requiring markers

Always mark:

- phase, randomization, blinding, center count, and geography;
- sample size, arm size, analysis population, and denominator;
- baseline characteristics, dose, schedule, cycles, treatment duration, and maintenance;
- data cutoff, follow-up, event count, endpoint value, confidence interval, p-value, and effect estimate;
- subgroup values and analysis status;
- safety event counts, percentages, grade, seriousness, relatedness, and discontinuation;
- source-supported labels such as interim, final, prespecified, post hoc, or no new safety signal;
- conclusions that rely on one or more supplied sources.

Methodological cautions with no source-specific factual assertion do not require a marker.

## Duplicates and multiple sources

For repeated reporting of one analysis, cite the clearest source for the value. Optionally add a duplicate source marker when it contributes material context. Multiple markers must never be presented as independent patient-level confirmation.

When a sentence combines distinct source-supported facts, attach the relevant marker to each clause. A combined marker is valid only when every listed source supports the complete claim.

## Separate citation JSON

The Markdown report contains inline markers only. The citation metadata is emitted as a **raw JSON file** at the fixed path `/workspace/output/citations.json` (see `references/file-delivery.md`), one key per marker. The path is hard-coded by the backend and never derived from the report name, so write it exactly there — a renamed or relocated citation file is orphaned and downstream marker rendering silently fails. Each value must contain exactly the `title`, `link`, and `paper_release_time_str` strings of the pulled record: `title` / `link` copied byte-for-byte from `paper_title` / `full_article_link`, and `paper_release_time_str` = the date part (`YYYY-MM-DD`) of `paper_release_time`. `title` and `link` may be empty only when the record that **did** come back carried them empty; an entry whose `title` is empty because the source never returned must not exist at all. Do not append this object to the report body.

**Link follows the analysis depth (the one exception to byte-for-byte `link`).** When a record's facts rest on a retrieved PMC full text (`R6` → `R7`, see `references/input-contract.md`), that record's `link` must point at the full text, not at the abstract/publisher page the record came with — a reader clicking the superscript must land on the page that actually contains the numbers the report used. Build it only from the `PMCID` that `R6` returned, exactly one substitution per record, and only in one of the two whitelisted forms: `https://pmc.ncbi.nlm.nih.gov/articles/{PMCID}/` (default) or `https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML`. No other URL is ever written; `title` and `paper_release_time_str` are untouched, and every record analysed at abstract depth keeps the pulled `full_article_link` byte-for-byte.

```json
{"ref_1":{"title":"Source title","link":"https://example.com/source","paper_release_time_str":"2025-01-01"}}
```

The code fence is documentation only. The delivered citation file must be raw, unfenced strict JSON. Every marker used in the report has exactly one matching key, no unused key is present, and keys are contiguous from `ref_1` in selection order over the records that returned. Links must be preserved byte-for-byte; empty values remain empty when the returned record supplied nothing.

## Verification

Before delivery, scan every clinical numeral and ensure it has a nearby marker. Read the citation file back and parse it. Compare the set of inline marker keys against the JSON keys in both directions. Verify that **every entry has a non-empty `title`** (an empty title means a record that never came back was cited) and that the number of numbered sources equals the number of records the pull actually returned. Verify every cited source contains the claimed value; every JSON `title` matches the supplied metadata byte-for-byte, every `link` matches it byte-for-byte **or** is the whitelisted full-text URL of a record whose facts rest on that full text (see *link follows the analysis depth* above); and every `paper_release_time_str` is exactly the `YYYY-MM-DD` date part of the supplied `paper_release_time` — no `HH:MM:SS` and no time component, and `""` where the record supplied none. Then call `present_artifact` on the report file as the final tool call (see `references/file-delivery.md`).
