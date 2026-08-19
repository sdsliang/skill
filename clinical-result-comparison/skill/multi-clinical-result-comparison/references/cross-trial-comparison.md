# Cross-Trial Comparison (comparison-first, domain-aligned)

## Goal

When the selected sources contain multiple independent trials, the primary deliverable is a **cross-trial comparison aligned by outcome domain** (efficacy, safety, PK/PD, PRO, and the design/baseline context that qualifies them). The purpose is to help the user judge which treatment is better or worse on each decision-relevant dimension, with an explicit evidence-strength label for every judgment.

Trial narratives are supporting context, not the main structure. Provide one compact trial-context block per trial (design, population, endpoints, maturity) so every aligned value can be interpreted in its own trial, but do not make the report a sequence of full trial interpretations with a small comparison appendix.

## Citation scope across trials

Assign `{{ref_n}}` markers globally in the original input order for the entire Agent response, before grouping sources into trials or clinical-question clusters. Do not restart numbering at each trial boundary. A mixed report uses one shared separate citation JSON artifact; markers in each row resolve to the source metadata for that trial.

For example, Trial A may use `{{ref_1}}` and `{{ref_3}}`, while Trial B uses `{{ref_2}}` and `{{ref_4}}`. If the product requests separate independent reports, each report gets its own local numbering scope and its own citation JSON artifact.

Attach markers to every cross-trial table value and every source-dependent comparison claim. A comparison sentence must cite the sources for the trials it compares; the marker link identifies the source, while the prose must retain each trial's population, endpoint, time point, comparator, and design boundary.

## Step 1: Cluster by clinical question, not disease name

Group records using the clinical question. Consider:

- intended condition or symptom;
- population and treatment setting;
- therapeutic objective;
- intervention role;
- outcome domain.

One disease may contain several clusters (e.g., histology, survival, liver-fat/weight, symptom/PRO, long-term metabolic safety). Never merge clusters into one efficacy ranking. A cluster is the scope inside which a comparative direction may be discussed.

## Step 2: Build the outcome-domain alignment skeleton

For each clinical-question cluster, organize the report by outcome domain. The domain set is driven by what the selected sources actually report; PK/PD and PRO become explicit information gaps when no source reports them:

- **有效性 (efficacy)**: primary endpoint, key secondary endpoints, response/threshold, durability/time-course, subgroups;
- **安全性 (safety)**: event type, grade, seriousness, relatedness, discontinuation, death, exposure;
- **PK/PD**: exposure, pharmacokinetics, exposure–response (only when reported);
- **PRO / 症状 / 生活质量**: patient-reported and symptom endpoints (only when reported);
- **设计/人群可比性**: used as a qualifier for every aligned value, not as a domain with a winner.

Each domain gets its own alignment table (see Step 4). This is the main body of the report.

## Step 3: Trial-context block (compact, not narrative-first)

Before the domain tables (or immediately after the snapshot), provide one row per trial so every aligned value can be interpreted:

- trial and registration identity;
- population and treatment setting;
- phase/design, control, blinding;
- experimental regimen (dose, schedule);
- experimental-arm sample and analysis set;
- endpoint hierarchy and primary endpoint;
- time point/follow-up;
- evidence maturity and reporting completeness.

Keep this compact. Do not build a full evidence-chain narrative here; the domain tables are the primary output.

## Step 4: Domain alignment tables

For every domain, create one table with one row per **outcome/metric** and one column per **trial (experimental arm)**. Each cell holds the trial's reported value plus its marker. Use a dedicated last column for alignment level and a comparability note per row.

Use these distinct columns or equivalent:

- outcome/metric and definition;
- experimental regimen;
- reported value for each trial;
- time point/follow-up;
- alignment level;
- interpretation boundary.

Do not collapse the experimental-arm observed value with the within-study control effect. If the experimental-arm observed value is not given, write `未报告（仅报告研究内比较效应）`. Keep each study's control visible in the trial-context block or a control column, but never treat controls from different studies as a common comparator.

### Classify endpoint/metric alignment

Assign one level for each attempted comparison:

- **Directly aligned**: same clinical construct, materially compatible definition, population, statistic, and time frame.
- **Partially aligned**: same construct but one or more meaningful differences require caution.
- **Context only**: related domain but different endpoint definition, statistic, population, or timing prevents numeric comparison.
- **Not aligned**: different clinical question or no counterpart.

- **Directly aligned** and **Partially aligned** rows may support a bounded comparative direction after considering design and uncertainty.
- **Context only** and **Not aligned** rows must not produce a leader, directional winner, or raw-number ranking. Report the values only inside their own source contexts.

## Step 5: Judge comparison confidence

Assess the comparison of a row (or of the domain as a whole) using observable properties rather than a fixed score:

- similarity of patient populations;
- compatibility of interventions and controls;
- study-design differences;
- endpoint/metric alignment;
- timing/follow-up alignment;
- analysis maturity and statistical completeness;
- safety exposure and reporting completeness.

Use one label:

- **High comparability**: rare outside a head-to-head or closely matched design; supports a strong comparative statement.
- **Moderate comparability**: supports a cautious directional comparison.
- **Low comparability**: supports context-level observations only.
- **Not meaningfully comparable**: do not rank outcomes.

Cross-trial comparisons usually cannot establish treatment superiority even when comparability is moderate or high. State that distinction clearly: a directional judgment on evidence is not a head-to-head superiority proof.

## Step 6: Make dimension-specific judgments

For each sufficiently aligned dimension **within the same clinical-question cluster**, use one of the labels below. “Favored” and “directionally favored” are available only when endpoint alignment is Directly aligned or Partially aligned:

- **Result A is favored on this dimension**: the evidence supports a clear within-scope advantage.
- **Result A is directionally favored**: the observed signal points toward A, but indirectness or uncertainty prevents a firm claim.
- **No material difference demonstrated**: the supplied evidence does not establish a meaningful difference.
- **Cannot determine**: missing or incompatible evidence blocks judgment.

Always attach the reason and evidence strength. Do not rank a raw percentage or median without verifying endpoint direction and context. Default to a plain-language interpretation after each domain table rather than an exhaustive pairwise matrix. Create pairwise `A vs B` rows only for a true head-to-head comparison reported by a selected source.

## Step 7: Give the overall who-is-better judgment per cluster

For each clinical-question cluster, state explicitly which experimental regimen is best supported by the supplied evidence, using the dimension-specific judgments. Provide:

- the leading regimen (or `无法确定` when evidence is insufficient);
- the dimensions that drive the leading position;
- the evidence strength (high/moderate/low comparability);
- the boundary (not a head-to-head superiority proof; missing safety/PK-PD/PRO may reverse the decision).

An overall leader within a cluster requires:

- the compared results address substantially the same clinical question;
- key populations and regimens are sufficiently compatible;
- at least one decision-relevant efficacy endpoint is directly or partially aligned;
- safety evidence is not missing in a way that could reverse the decision;
- findings are directionally coherent across the most important dimensions.

If any condition fails, report `无法确定` for that cluster and give the most decision-relevant dimension-specific conclusion instead. Do not report a cross-cluster winner when the input contains multiple distinct clinical-question clusters.

## Required visible output

The report must contain, in comparison-first order:

1. a one-sentence overall verdict (who is favored on what, with strength and boundary);
2. the scope and clinical-question clusters;
3. a core-endpoint snapshot table per cluster (with a Mermaid chart only when the chart contract below passes, otherwise a concise no-chart reason);
4. a compact trial-context table (one row per trial);
5. outcome-domain alignment tables (efficacy, safety, PK/PD, PRO — one per reported domain, with explicit information gaps);
6. dimension-specific judgments (who is favored on each dimension, with strength);
7. per-cluster overall who-is-better judgment with boundaries;
8. information gaps and next most decision-relevant data.

## Chart contract (descriptive only)

The snapshot may include a Mermaid `xychart-beta` chart only when all plotted values are explicitly reported numbers with a single unit, direction, population, analysis set, and time frame, and the Mermaid syntax is valid. Chart rules:

- quote category labels; data arrays contain numbers only (never `未报告`, NR, NE, ranges, CIs, or `%` strings);
- one unit and one endpoint direction per chart;
- y-axis range includes all plotted values without clipping or exaggerating a narrow difference;
- state series identity in adjacent text and show every point in the exact-value table;
- do not assume zero as a baseline unless reported;
- never emit a Mermaid fence with template placeholders; if any requirement fails, remove the entire fence and state the reason.

Charts are descriptive evidence views, not head-to-head proof, rankings, or pooled analyses. They never replace the exact-value table or the domain alignment.

## Required deep-analysis topics

- what can be compared and why;
- what cannot be compared and why;
- efficacy signal per domain and its maturity;
- safety signal and reporting completeness;
- PK/PD and PRO coverage (or their absence as a gap);
- study-design impact on confidence;
- source rhetoric versus supported conclusion;
- dimension-specific leader, if any;
- per-cluster overall who-is-better judgment and its boundary.
