# Same-Trial Evidence Chain Synthesis

## Goal

Reconstruct the complete clinical interpretation of one trial from multiple selected disclosures. The trial is the object of analysis. Disclosures are source nodes that supply design details, analysis states, endpoint results, subgroups, and safety updates.

The visible report must answer “What does the whole trial show now?” rather than “How do these disclosures differ?”

## Step 1: Establish the common trial core

Confirm, from the supplied texts:

- trial name and registry identifier;
- disease, treatment line, stage/severity and eligibility;
- randomization, blinding, phase, geography and site count;
- intervention, control, dose, schedule, combination and maintenance;
- randomized, treated, efficacy and safety populations;
- primary and key secondary endpoints;
- stratification and statistical hierarchy when reported.

Create this core once. Do not repeat it for every disclosure. Keep separate cohorts, extensions, substudies, biomarker groups and post hoc populations outside the common core when the sources distinguish them.

## Step 2: Assign source markers and source roles

Assign one stable `{{ref_n}}` marker to each selected source. Classify each source on two separate axes only when explicitly supported.

### Disclosure form

- top-line disclosure;
- full report or publication;
- conference abstract, poster or oral presentation;
- regulatory or sponsor update;
- unclear form.

### Analysis stage or scope

- primary analysis;
- interim analysis, including its stated number;
- final analysis;
- longer follow-up or updated analysis;
- new endpoint analysis;
- subgroup or sensitivity analysis;
- safety, quality-of-life or other complementary analysis;
- unclear stage.

Do not infer interim/final status, chronology, or form from input order.

## Step 3: Consolidate sources into evidence states

An evidence state is a clinically distinct analysis contribution. Multiple sources can support one state. Consolidate sources when they share the same cohort, endpoint, cutoff/follow-up and estimates.

For every state record:

- analysis milestone and scope;
- cutoff, follow-up and event count;
- population and analysis set;
- endpoints contributed;
- efficacy and safety maturity;
- supporting markers;
- relation to the preceding state.

Use source-supported relationship labels:

- **Duplicate**: same underlying cutoff and analysis repeated in another source.
- **Update**: later cutoff/follow-up or refreshed estimate for an existing endpoint.
- **New endpoint**: first mature or quantitative report of another endpoint.
- **Confirmation**: a distinct later analysis supports the earlier direction; not merely duplicate reporting.
- **Complement**: adds subgroup, safety, quality-of-life, exposure or methodological detail.
- **Supersedes**: a later estimate should replace an earlier estimate for the same endpoint and population.
- **Conflict**: values or definitions cannot be reconciled from the supplied texts.
- **Uncertain**: the relationship cannot be established.

The separate citation JSON records every used source marker. The main evidence chain records each state once.

## Step 4: Build clinical chronology

Order states by:

1. data cutoff;
2. stated follow-up;
3. explicit analysis milestone;
4. disclosure/publication date.

Do not use input order, database order or runtime timestamps. If a source has no usable timing, attach it to a matching state only when matching values and scope support that relationship. Otherwise leave chronology uncertain.

## Step 5: Build the efficacy chain

For each endpoint family, reconstruct the earliest and most mature distinct evidence states.

### Primary endpoint

Show endpoint definition, evaluator, population, arm results, within-trial effect, uncertainty, statistical status, cutoff and maturity. Explain whether later disclosures provide a genuine update or only repeat the same result.

### Key secondary endpoints

Show analysis hierarchy, event trigger, interim/final status and whether the endpoint extends or qualifies the primary result. Do not present a first or interim OS analysis as final.

### Other efficacy domains

When reported, integrate response rate, complete response, response duration, fixed-time outcomes, symptom burden, patient-reported outcomes and quality of life. Missing domains become information gaps, not empty repeated rows.

### Subgroups and sensitivity analyses

Keep overall and subgroup estimates separate. Record prespecified/exploratory status and interaction testing when reported. Similar directions across subgroups do not prove equal benefit; different point estimates do not prove heterogeneity.

## Step 6: Build the safety chain

Align safety by analysis state, denominator, exposure, event definition and follow-up. Track, when reported:

- any-grade and grade 3 or higher events;
- serious and treatment-related events;
- immune-related or other adverse events of special interest;
- discontinuation, dose reduction, interruption and death;
- longer-exposure updates and newly reported signals.

A percentage increase between cutoffs is not automatically a worsening incidence pattern because cumulative exposure, event definition and denominator may differ. “No new safety signal” remains a source statement.

## Step 7: Explain maturity, not publication differences

Determine whether the whole-trial interpretation:

- **Strengthened**: a genuinely new analysis or endpoint materially increases confidence or clinical relevance.
- **Broadly unchanged**: later material mainly repeats or adds detail.
- **Qualified**: benefit persists but new limitations or risks matter.
- **Weakened**: later evidence reduces confidence or contradicts an earlier interpretation.
- **Indeterminate**: gaps or conflicts prevent a defensible direction.

State which evidence states and markers caused the classification. Do not name a “winning disclosure”.

## Step 8: Generate the timeline diagram

For every same-trial input with two or more distinct evidence states, build the evidence-chain timeline diagram per `timeline-diagram.md` and place it directly above the timeline table in the evidence-chain overview section.

- One node per evidence state (not per source); merged sources share a node with their markers listed together.
- Node label: state name + analysis stage/disclosure form, this state's key new content, and inline `{{ref_n}}` markers.
- Chronology on the axis comes only from source-supported data cutoff, follow-up, analysis milestone, then disclosure date; never input order. Missing timing is labeled 时间未明, never guessed.
- Relationship and maturity direction go on the edge between consecutive states (更新/新增终点/确认/补充/取代/冲突/不确定 + 加强/基本不变/限定/削弱/无法确定).
- The diagram is descriptive only: no interpolation, pooling, ranking, or inferred dates. It never replaces the exact-value timeline table.

## Step 9: Required report content

- one common trial description;
- one evidence-state timeline, with supporting markers;
- integrated primary and key secondary endpoint chains;
- other efficacy domains only when reported;
- subgroup and sensitivity boundaries;
- safety evolution with denominators and exposure limits;
- duplicate, conflict and uncertainty handling;
- whole-trial efficacy, safety and maturity interpretation;
- next decision-relevant data needs;
- a strict separate citation JSON containing every used source marker and its metadata.

Every material number must have an adjacent marker. Every marker used in the report must have a matching key in the separate citation JSON; repeated disclosures remain represented when they contribute duplicate or complementary support.
