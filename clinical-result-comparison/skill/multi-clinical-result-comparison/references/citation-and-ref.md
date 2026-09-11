# Citation and Linked-Source Traceability

## Goal

Make every material number and source-dependent conclusion in a trial synthesis traceable to one supplied source. Inline markers are presentation-stable tokens that the frontend converts to numeric superscript links; they do not represent independent trials, evidence grades, or chronology. Entity inline references (`[name](entity:type:id)`, v0.10) are a separate display feature that coexists with markers — see `references/entity-inline-reference.md`; they never replace or alter marker placement.

## Input metadata

Each selected clinical result is pulled by esid through the MCP tool `pharmcube-query-clinical-result-with-params` (`extra_esids` + strict `selected_fields`, see `references/input-contract.md`). The consumer-facing citation fields map from the returned record as:

```json
{
  "title": "paper_title",
  "link": "full_article_link",
  "paper_release_time_str": "paper_release_time"
}
```

Only the fields that carry clinical content (`abstract_text`, `summary`, `study_results`, design/arms context) support clinical claims. `paper_title`, `full_article_link`, `paper_release_time`, `journal`, `doi`, and `pm_id` are citation metadata. Do not derive clinical facts from them. Preserve the returned strings exactly and do not retrieve, complete, transform, or guess metadata.

Assign markers in input (esid) order: `{{ref_1}}`, `{{ref_2}}`, and so on. This ordering is stable but does not establish clinical chronology.

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

The Markdown report contains inline markers only. The citation metadata is emitted as a **raw JSON file** at the fixed path `/workspace/output/citations.json` (see `references/file-delivery.md`), one key per marker. The path is hard-coded by the backend and never derived from the report name, so write it exactly there — a renamed or relocated citation file is orphaned and downstream marker rendering silently fails. Each value must contain exactly the `title`, `link`, and `paper_release_time_str` strings from the pulled record (fields copied byte-for-byte from the returned `paper_title` / `full_article_link` / `paper_release_time`). Do not append this object to the report body.

```json
{"ref_1":{"title":"Source title","link":"https://example.com/source","paper_release_time_str":"2025-01-01"}}
```

The code fence is documentation only. The delivered citation file must be raw, unfenced strict JSON. Every marker used in the report has exactly one matching key, no unused key is present, and keys are contiguous from `ref_1` in input order. Links must be preserved byte-for-byte; empty values remain empty when supplied.

## Verification

Before delivery, scan every clinical numeral and ensure it has a nearby marker. Read the citation file back and parse it. Compare the set of inline marker keys against the JSON keys in both directions. Verify every cited source contains the claimed value and every JSON title, link, and release-time string exactly matches the supplied metadata. Then call `present_artifact` on the report file as the final tool call (see `references/file-delivery.md`).
