# Citation and Linked-Source Traceability

## Goal

Make every material number and source-dependent conclusion in a trial synthesis traceable to one supplied source. Inline markers are presentation-stable tokens that the frontend converts to numeric superscript links; they do not represent independent trials, evidence grades, or chronology.

## Input metadata

Each selected source arrives as:

```json
{
  "source_title": "backend-supplied title",
  "source_url": "https://backend-supplied.example/source",
  "source_paper_release_time_str": "backend-supplied release time string",
  "source_full_text": "clinical evidence text"
}
```

Only `source_full_text` supports clinical claims. `source_title`, `source_url`, and `source_paper_release_time_str` are citation metadata. Do not derive clinical facts from them. Preserve the release-time string exactly and do not retrieve, complete, transform, or guess metadata.

Assign markers in input inventory order: `{{ref_1}}`, `{{ref_2}}`, and so on. This ordering is stable but does not establish clinical chronology.

## Inline syntax

Markers are internal presentation tokens. The visible report should not explain or spell out `{{ref_n}}` in its evidence-scope paragraph; the frontend replaces them with numeric superscripts.

Use markers immediately after the supported number, clause, or table value:

```text
中位 PFS 为 11.1 个月（95% CI 9.9-NE），对照组为 6.9 个月（95% CI 5.8-8.6），HR 0.60（95% CI 0.46-0.78；单侧 p<0.0001）。{{ref_1}}

11.1 个月（95% CI 9.9-NE）{{ref_1}}
```

For a claim fully supported by more than one source, concatenate markers without punctuation: `{{ref_1}}{{ref_3}}`. Do not place a single marker after a long paragraph containing independently sourced values; split the statement or cite each clause locally.

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

The Markdown report contains inline markers only. Output a separate, raw JSON object with one key per marker. Each value must contain exactly the supplied `title`, `link`, and `paper_release_time_str` strings. Do not append this object to the report body.

```json
{"ref_1":{"title":"Source title","link":"https://example.com/source","paper_release_time_str":"2025-01-01"}}
```

The code fence is documentation only. The delivered JSON artifact must be unfenced, strict JSON. Every marker used in the report has exactly one matching key, no unused key is present, and keys are contiguous from `ref_1` in input order. Links must be preserved byte-for-byte; empty values remain empty when supplied.

## Verification

Before delivery, scan every clinical numeral and ensure it has a nearby marker. Parse the separate citation JSON. Compare the set of inline marker keys against the JSON keys in both directions. Verify every cited source contains the claimed value and every JSON title, link, and release-time string exactly matches the supplied metadata.
