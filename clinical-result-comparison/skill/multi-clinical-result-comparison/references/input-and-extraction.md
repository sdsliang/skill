# Input and Evidence Extraction

## Source authority

`source_full_text` is the sole clinical evidence for an item. Each item may also contain backend-supplied `source_title` and `source_url`, which are citation metadata only and must not add clinical facts. The backend should resolve these values from `np_clinical` before invoking the Agent. Never retrieve or guess a missing URL in the Agent.

Preserve drug names, trial names, biomarkers, companies, and other proper nouns exactly as supplied. Use a Chinese equivalent only when a selected source explicitly provides it. Do not translate, transliterate, normalize, or map a proper name from memory; retain the English name in a Chinese report when it is the only source-supported form.

Assign each selected source a stable presentation marker (`{{ref_1}}`, `{{ref_2}}`, etc.) before extraction. The marker is the traceability key used in the report; its number does not indicate chronology, maturity, or evidence strength. Keep runtime correlation keys outside the Agent input and report.

## Source quality flags

Assign any applicable flags internally and expose them when they affect interpretation:

- `complete_for_comparison`: reports enough design and outcome context for at least one comparison.
- `partial`: usable but missing important context.
- `qualitative_only`: gives direction without usable effect estimates.
- `possible_truncation`: appears cut off or lacks an expected continuation.
- `duplicate_text`: materially identical to another selected source.
- `non_result_text`: protocol/background content without an actual clinical result.
- `internally_ambiguous`: terms, populations, or figures cannot be assigned confidently.

## Evidence worksheet

Build the following worksheet independently for every source.

### Identity and timing

- backend-supplied `source_title`, `source_url`, and `source_paper_release_time_str` for citation JSON only;
- internal runtime key, retained outside the Agent input for backend correlation only;
- disclosure/publication date;
- data cutoff;
- median follow-up or assessment duration;
- whether timing refers to the study, the analysis, or publication.

Do not substitute publication date for data cutoff. Do not treat a database order as chronology.

### Clinical question

- disease and subtype;
- stage/severity;
- line or treatment setting;
- biomarker or defining eligibility;
- age/geography/special population;
- prior-treatment requirements;
- baseline comparability fields when reported: age, sex, disease severity, baseline endpoint score, prior treatment, biomarker, and other eligibility features;
- intervention and regimen, preserving source-supplied proper names exactly;
- control or reference condition, preserving source-supplied proper names exactly.

### Study design

- phase;
- randomized or non-randomized;
- blinded or open label;
- controlled or uncontrolled;
- prospective/retrospective and interventional/observational when reported;
- number of centers/geography when relevant;
- enrolled, randomized, treated, and analyzed sample sizes;
- analysis population such as ITT, efficacy-evaluable, safety, per protocol, or subgroup.

### Endpoint record

Create a separate record for each reported result:

| Field | Meaning |
|---|---|
| Source | exact visible `{{ref_n}}` marker supporting the record |
| Domain | efficacy, safety, PK/PD, patient-reported outcome, quality of life, or other |
| Hierarchy | primary, key secondary, secondary, exploratory, post hoc, or not reported |
| Endpoint | full endpoint name and construct |
| Definition | threshold, scale, event definition, adjudication, or assessment method |
| Population | exact analysis population or subgroup |
| Arm | exact experimental regimen or within-study control to which the value belongs |
| Arm role | experimental arm, within-study control, between-arm effect, or unclear |
| Statistic | median, mean change, proportion, hazard ratio, odds ratio, count, qualitative direction, etc. |
| Value | exact reported value or status such as NR/NE |
| Unit | months, %, points, events, etc. |
| Time point | assessment time, cutoff, or follow-up |
| Uncertainty | CI, p-value, boundary, multiplicity status when reported |
| Comparison | within-arm, between-arm, baseline change, historical statement, or unclear |

Do not merge values merely because endpoint names are similar. Keep subgroup and overall-population values separate. For every efficacy endpoint, independently capture (a) the experimental-arm observed result and (b) the within-study comparator result or comparative effect. These are different evidence objects. If a source reports only a hazard ratio, difference, or p-value, do not back-calculate an experimental-arm value.

For every extracted numeral, retain the marker in the same internal record. Before drafting, verify that the report can cite the exact source for sample sizes, doses, cutoffs, follow-up, endpoint values, effect estimates, uncertainty, event counts, percentages, and denominators.

### Safety record

Separate at least these concepts when reported:

- any-grade adverse events;
- grade 3 or higher events;
- serious adverse events;
- treatment-related events;
- discontinuations, dose reductions, interruptions, and deaths;
- adverse events of special interest;
- exposure duration and safety population.

Do not compare percentages with different denominators or event definitions as if equivalent.

### Baseline comparability record

Keep baseline fields separate from eligibility and study-design fields. For each source, record the reported value, denominator, time point, and analysis population for age, sex distribution, disease severity or baseline burden, baseline value of the key endpoint, prior treatment and treatment failure/refractoriness, biomarker or phenotype, and other material eligibility features. A similar baseline is an observation, not proof that studies are exchangeable. If a field is not reported, write `未报告` rather than treating it as balanced.

### Reference behavior record

For each efficacy family, separately capture placebo response, baseline change, historical reference, untreated reference, or no comparator. Preserve the reference arm's denominator, time point, endpoint definition, and value. Do not use a reference response to reconstruct an unreported experimental-arm value.

### Endpoint-family record

When the source supports it, group endpoint records into primary endpoint; threshold, responder, remission, or complete-response endpoint; key symptom or subdomain endpoint; durability or time-course endpoint; and safety/tolerability endpoint. Do not assume every disease has the same endpoint hierarchy. A threshold or cutoff is not a clinical meaningfulness threshold unless the source establishes that status.

## Source rhetoric

Capture the source's interpretation separately from the underlying result. Words such as “breakthrough”, “manageable”, “clinically meaningful”, “favorable”, or “new standard” are claims unless the source also provides evidence that permits the comparison report to adopt them.
