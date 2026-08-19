# Cross-Trial Comparison

## Goal

Answer which selected result is stronger, weaker, or simply different without turning heterogeneous studies into a false league table.

## Citation scope across trials

Assign `{{ref_n}}` markers globally in the original input order for the entire Agent response, before grouping sources into trials or clinical-question clusters. Do not restart numbering when a new trial narrative begins. A mixed report therefore uses one shared separate citation JSON artifact; markers in each trial section resolve to the source metadata for that section's trial.

For example, sources for Trial A may use `{{ref_1}}` and `{{ref_3}}`, while Trial B uses `{{ref_2}}` and `{{ref_4}}`. The frontend can render all of them with the same marker renderer. If the product requests separate independent reports instead of one mixed report, each report gets a fresh local numbering scope and its own citation JSON artifact.

Attach markers to every cross-trial table value and source-dependent comparison claim. A comparison sentence must cite the sources for both trials; the marker link identifies the source, while the prose must retain each trial's population, endpoint, time point, comparator, and design boundary.


Cluster records using the clinical question, not disease name alone. Consider:

- intended condition or symptom;
- population and treatment setting;
- therapeutic objective;
- intervention role;
- outcome domain.

Examples within one disease may still require separate clusters for survival, symptom control, physical development, body composition, and long-term metabolic safety.

If two results answer different clinical questions, compare their evidence scope and relevance but do not declare one treatment clinically superior. Do not create a shared “efficacy winner” across clusters based on positivity, p-values, endpoint hierarchy, or narrative strength; those quantities answer different questions.

## Step 2: Add a core-endpoint snapshot and chart

Before the full alignment tables and prose interpretation, identify the most decision-relevant endpoint for each clinical-question cluster represented in the selected set. Choose it from the supplied texts using the stated primary endpoint or the endpoint that best represents the shared therapeutic objective. Do not import an endpoint hierarchy from outside the supplied texts. If the selected set contains multiple distinct indications or clinical questions, create a separate snapshot per cluster rather than one overall chart.

The snapshot is mandatory; a chart is not. Use this decision sequence:

1. Select the endpoint and define its unit, direction, population, analysis set, and time frame.
2. Build the exact-value evidence table.
3. Test whether every intended plotted value is explicit, numeric, and materially compatible.
4. Add a Mermaid chart only if it passes the chart contract below.
5. Place the exact-value table and a one- or two-sentence comparability note immediately after the chart. If no chart is valid, show the table in the same location and state the specific reason.

### ORR-like bar chart

Use a descriptive `xychart-beta` bar chart only when the response endpoint definition, population, analysis set, assessment method when material, and assessment time are sufficiently aligned. One bar represents one experimental arm in its own study. Quote every x-axis category label. Supply bare numeric values in the `bar` array; do not include `%` inside the array. Put the percentage unit on the y-axis and retain exact values in the adjacent table.

### Weight-change line chart

Use a time-versus-weight-change `xychart-beta` line chart only when all of the following hold:

- each plotted experimental arm reports at least two explicit numeric time points;
- all series use the same metric, unit, direction, population scope, and analysis set;
- the compared series share the same plotted time-point grid;
- every point on that shared grid is explicitly reported for every plotted series;
- the line identity can be explained next to the chart and in the exact-value table.

Do not use zero as an assumed baseline unless the source explicitly reports that plotted baseline value. Do not insert `null`, blank entries, carried-forward values, modeled values, or interpolated points. If time-point grids differ, use the table fallback or separate per-study views; do not force them into one combined line chart.

### Mermaid output contract

- Use only valid Mermaid `xychart-beta` syntax supported by Tool Smith Markdown rendering.
- Quote category labels, especially Chinese labels or labels containing spaces or punctuation.
- Mermaid data arrays must contain numbers only. Never place `未报告`, `NR`, `NE`, ranges, confidence intervals, percentages with `%`, or prose in an array.
- Use one unit and one endpoint direction per chart.
- Set the y-axis range to include all plotted values without clipping and without visually exaggerating a narrow difference. For percentage response rates, normally use 0 to 100. For percentage weight change, use a range that includes zero and all reported values.
- Do not rely on line color alone. State series order/identity in adjacent text and show every point in the exact-value table.
- Never emit a Mermaid fence containing template placeholders. If any chart requirement fails, remove the entire fence.

Charts are descriptive evidence views, not head-to-head proof, rankings, or pooled analyses. They never replace the exact-value table or the complete alignment layer. Never put technical identifiers in chart labels, captions, or fallback tables.

## Step 3: Build the research-key-information alignment

For every cluster, create one vertically stacked row per selected result and align:

- trial and registration identity;
- population and treatment setting;
- experimental intervention and regimen;
- within-study control or reference;
- design;
- experimental-arm sample and analysis set;
- endpoint hierarchy;
- time point/follow-up;
- efficacy and safety completeness.

The experimental regimen is the focal object. Keep the study's control visible because it affects internal validity, but do not treat controls from different studies as if they were a common comparator. Use `未报告` when absent. Do not replace a missing value with an inference.

## Step 4: Build the experimental-arm endpoint alignment

Create the report's primary outcome table with one row per `result + endpoint + population/time point`. Vertically stack the experimental arms across studies. Use these distinct columns:

- result label and clinical-question cluster;
- experimental regimen;
- endpoint, hierarchy, and definition;
- analysis population;
- experimental-arm observed result;
- within-study control and/or treatment-versus-control effect;
- time point/follow-up;
- endpoint alignment level;
- interpretation boundary.

Do not collapse the two result columns. An experimental-arm rate, median, or change is not the same object as a hazard ratio, least-squares difference, p-value, or qualitative statement versus control. If the experimental-arm observed value is not given, write `未报告（仅报告研究内比较效应）`. If no comparator exists or is reported, write `无/未报告` in the within-study context column.

This table is a non-head-to-head longitudinal view: it permits scanning of how selected experimental arms performed in their own studies, but does not by itself support a winner.

## Step 5: Classify endpoint alignment

Assign one level for each attempted endpoint comparison:

- **Directly aligned**: same clinical construct, materially compatible definition, population, statistic, and time frame.
- **Partially aligned**: same construct but one or more meaningful differences require caution.
- **Context only**: related domain but different endpoint definition, statistic, population, or timing prevents numeric comparison.
- **Not aligned**: different clinical question or no counterpart.

- **Directly aligned** and **Partially aligned** endpoints may support a bounded comparative direction after considering design and uncertainty.
- **Context only** and **Not aligned** endpoints must not produce a leader, directional winner, or raw-number ranking. Report the values only inside their own source contexts.

## Step 6: Judge comparison confidence

Assess the comparison as a whole using observable properties rather than a fixed score:

- similarity of patient populations;
- compatibility of interventions and controls;
- study-design differences;
- endpoint alignment;
- timing/follow-up alignment;
- analysis maturity and statistical completeness;
- safety exposure and reporting completeness.

Use one label:

- **High comparability**: rare outside a head-to-head or closely matched design; supports a strong comparative statement.
- **Moderate comparability**: supports a cautious directional comparison.
- **Low comparability**: supports context-level observations only.
- **Not meaningfully comparable**: do not rank outcomes.

Cross-trial comparisons usually cannot establish treatment superiority even when comparability is moderate or high. State that distinction clearly.

## Step 7: Make dimension-specific judgments

For each sufficiently aligned dimension **within the same clinical-question cluster**, use one of the labels below. “Favored” and “directionally favored” are available only when endpoint alignment is Directly aligned or Partially aligned:

- **Result A is favored on this dimension**: the evidence supports a clear within-scope advantage.
- **Result A is directionally favored**: the observed signal points toward A, but indirectness or uncertainty prevents a firm claim.
- **No material difference demonstrated**: the supplied evidence does not establish a meaningful difference.
- **Cannot determine**: missing or incompatible evidence blocks judgment.

Always attach the reason and confidence. Do not rank a raw percentage or median without verifying endpoint direction and context. Default to a plain-language interpretation after the vertical table rather than an exhaustive pairwise matrix. Create pairwise `A vs B` rows only for a true head-to-head comparison reported by a selected source.

## Step 8: Decide whether an overall winner exists

An overall winner requires all of the following:

- the compared results address substantially the same clinical question;
- key populations and regimens are sufficiently compatible;
- at least one decision-relevant efficacy endpoint is directly or partially aligned;
- safety evidence is not missing in a way that could reverse the decision;
- findings are directionally coherent across the most important dimensions;
- the wording does not imply head-to-head proof when none exists.

If any condition fails, report no overall winner and provide the most decision-relevant dimension-specific conclusion instead. When the input contains multiple clinical-question clusters, report leaders only inside each cluster and use `不适用` for any cross-cluster efficacy winner.

## Required visible output

Every cross-trial cluster must contain, before prose interpretation:

1. a core-endpoint snapshot selected after clinical-question grouping;
2. an exact-value snapshot table, whether or not a chart is used;
3. a descriptive Mermaid chart only when the chart contract passes, otherwise a concise no-chart reason;
4. a research-key-information alignment table with one row per result;
5. an experimental-arm endpoint alignment table with one row per result-endpoint.

The user-visible snapshot appears first, but it is produced only after the internal grouping, endpoint selection, and chartability checks. The chart never replaces the evidence tables and must never be interpreted as pooled or head-to-head evidence.



## Required deep-analysis topics

- what can be compared and why;
- what cannot be compared and why;
- efficacy signal and its maturity;
- safety signal and reporting completeness;
- study-design impact on confidence;
- source rhetoric versus supported conclusion;
- dimension-specific leader, if any;
- whether an overall winner is justified.
