# Input Contract (v0.12: esid + params tool)

## Purpose

Each selected clinical result is delivered to the Agent as a **clinical-result esid** (the record ID,
`clinical_result.extra_esid`), not as an attached `.md` file and not as inline JSON in a message. The
frontend sends the selected esid list in the user turn (in user-selection order); the Agent then pulls
the detail records itself through the MCP tool `pharmcube-query-clinical-result-with-params`, filtering
by `extra_esids` and keeping the returned payload small via a strict `selected_fields` allowlist.

Rationale: a user may select several results (up to about 20). A single params response with many
unselected fields can exceed the context budget (`MCP_TOOL_RESULT_MAX_CHARS`); per-esid `{{ref_n}}`
mapping keeps each result addressable, bounds context by what the Agent actually needs, and keeps the
citation mapping stable (3rd retrieved esid in selection order → `{{ref_3}}`).

## Source of truth

- MCP tool name: `pharmcube-query-clinical-result-with-params`.
- Data source: 医药魔方 TrialiCube (`clinical_trial_result_structured`).
- `extra_esids` = exact-filter by clinical-result ID (each selected esid = one clinical result / one
  disclosure of a trial).
- `selected_fields` = array of field-name strings, **each copied verbatim** from the
  ALLOWED_FIELD_NAMES list that the params tool itself publishes in its `selected_fields`
  parameter description (visible in the tool schema at run time; the repo mirror
  `docs/params-tool-schema.md` is maintainer documentation, not a runtime file). Field names are
  case-sensitive and must not be descriptions.
  **Never invent a field name.** A concept the report needs (`线数`, `中位随访`, `亚组`…) does not
  imply a field exists: pick the closest real field on the list (group/arm counts →
  `clinical_result.group_count`, treatment line → `clinical_result.therapy_line_cn`/`_en`) or leave
  the field out and record the result as not reported. An invented name
  (e.g. `clinical_result.line_count`) is rejected and costs the whole pull.
  **Anchor field for selection: `clinical_result.extra_esid`.**
- The response injects the record `_id`; per-record fields appear under their selected names
  (nested: `arms`, `projects`, `study_results`, …).

## Pull protocol

1. Read the selected esid list from the user turn (input order = `{{ref_n}}` assignment order, over the records that return).
2. Call the tool with:
   - `extra_esids: [ ...selected esids in input order ... ]`;
   - `selected_fields`: the recommended minimal set below (trim further if a run is huge).
3. Keep the returned payload small: never request the whole record, never request fields you do not
   need, never re-pull the same esids speculatively once the needed fields are present.
4. Map records back to esids by `clinical_result.extra_esid` (or the record `_id`).
5. Number only what actually came back. Markers are assigned in user-selection order **over the
   records that returned**: 3rd esid in input order → `{{ref_3}}` holds while that record exists, but
   an esid that yields no record is not numbered at all (see *Unretrievable selected items*).

### Row fan-out: one esid can return several rows

`extra_esids` is an exact filter on the clinical-result ID, but **one esid can come back as more than one row**.
When `selected_fields` contains `clinical_result.indication_name` (or `clinical_result.indication_name_en`),
the backend joins a disease dimension and returns **one row per disease id** attached to the record, while every
requested field keeps the *identical* value on every row (the row carries the record's whole indication-name
list, not one name per row) and an extra **`disease_id` column appears that is not a requestable field**
(`disease_id` in `selected_fields` is rejected with `INVALID_INPUT`, yet it shows up in the response).

- Measured: the two selected esids `24_1_30561610` / `24_1_36342163` return **5 rows** with `indication_name`
  requested (3 + 2), and exactly **1 row each** with `paper_title` / `indication_detail` / `indication_type_cn`.
- **Treat all rows sharing a `clinical_result.extra_esid` (same record `_id`) as one record.** De-duplicate by
  `clinical_result.extra_esid` — keep the first row — **before** numbering `{{ref_n}}`, counting records, merging
  evidence states, emitting timeline events, or writing citation entries. A fan-out row set is neither repeated
  disclosure nor several sources: one esid = one marker = one citation key.
- Never emit the injected `disease_id` (or a row count) in the report, and never let the fan-out drive the
  reader-visible record count: the report covers the **selected records**, not the returned rows.
- The rows of one esid are identical in every requested field; should they ever differ substantively, still keep
  them as one record and use the union of the values rather than reporting the record twice.
- If a fan-out makes one response unwieldy (many esids × large fields), split the pull by esid ranges — **do not
  drop `indication_name` to avoid it**: the disease display names exist only in `indication_name` /
  `indication_name_en` (`indication_detail` is a free-text sentence about the enrolled population and
  `indication_type_cn` is the therapeutic area, both of which are not substitutes).

### Unretrievable selected items

The params tool answers `ok: true` with an **empty `data` array and no error** when an esid does not
exist, is not visible, or was deleted — an empty result is silent, so it is on you to detect it.

- **One batched pull, at most one confirmation.** Pull the whole selection in the single
  `extra_esids` call above. If some esids come back without a record, re-issue **exactly those esids
  together** in at most one further call, then stop. Never probe variant spellings, guessed ids,
  neighbouring ids, or other tools, and never loop call-per-esid: a retry that changes the spelling of
  an id is not a retry, it is a guess, and a series of them burns the run without new information. Do
  not repeat a confirmation whose arguments are unchanged either — if the same esid and the same
  `selected_fields` come back empty twice, that esid is absent and further calls cannot change it.
  (A second call with a **different** purpose — e.g. same trial, extra fields you still need — is not a
  confirmation and stays allowed.)
- **No marker, no citation key for a source that did not return.** Do not allocate `{{ref_n}}` to an
  unretrieved esid, and never emit a citation entry with an empty `title` — an empty-title entry *is*
  the signature of a citation written for a record that never came back. Keys stay contiguous
  (`ref_1`, `ref_2`, …) over the retrieved records, in selection order.
- **Say it in the evidence scope.** Name the selected items that could not be retrieved (esid plus,
  when the selection carried it, the trial/title the user saw) as an evidence limitation, and state
  that the report covers only the retrieved records.
- **Fewer than two usable records → refuse, do not deliver.** Do not write `report.md` and do not write
  `citations.json`; there is nothing to compare and a one-record "comparison" is a fabricated
  deliverable. Reply in chat naming the selected results that could not be retrieved and ask the user
  to re-check the selection.

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
"Large-batch delegation") or tighten `selected_fields` further. Requesting `indication_name` / `_en`
multiplies the returned rows (see *Row fan-out*) — de-duplicate by `clinical_result.extra_esid` instead of
dropping the field, which has no substitute.

### Evidence source priority: the original source comes first (原文优先)

The pulled clinical-content fields are **pipeline-processed extracts**: the backend's own parsing of the
source can drop a field, normalize a unit, or misread a table. The **original source** is therefore the
first priority for material clinical numbers, and the pulled fields are the second — use them to structure
the narrative and to fill what the original does not cover, never as the sole unreviewed basis for a
headline number. **"The original" means the deepest body available for that record**, not the shortest one
that happens to be in the pulled fields: see *The analysis surface is the deepest body you can obtain* below.

**Read `abstract_text` first — it usually *is* the original.** Measured 2026-09-17 by alphanumeric-normalized
comparison (9 records, 4 classes): the pulled `abstract_text` is the original text itself, not a rewritten
extract — journal abstracts match Europe PMC **1.000 / 1.000 / 1.000 / 0.992** (the residue is section-header
case, `BACKGROUND:` vs `Background`), conference abstracts match OpenAlex **0.991 / 0.999** (the one low score
is markdown/web residue wrapped around the same words — 50 of 56 chunks of the original sit verbatim inside
the pulled text), press releases carry the wire dateline verbatim, and for registry records the pulled
structured-results JSON contains **102/102 and 72/72** of the decimal values the ClinicalTrials.gov API
returns. So the default is: **read the pulled body and check the report against it, with no external call** —
except where a class has a documented fuller route, where the fuller body *replaces* the pulled body as the
analysis surface (PubMed → PMC full text below).

**Know the source class.** The middle segment of `clinical_result.extra_esid` (`YY_<src>_…`) is the
**ingestion source id**; it decides what "the original" is and which route is worth spending. Classes not
listed here follow the same principle — pulled body first, then a route key, then the record's own link
once.

| src | Source class | What the pulled `abstract_text` is | Fuller external original | What to do |
|---|---|---|---|---|
| `1` | PubMed / journal paper | the journal abstract, verbatim (median ~1.8 K chars) | **yes — PMC full text**; 56 of 100 sampled rows carry a `pmcid` | **always try R6 → R7**, even when `abstract_text` is non-empty, and **analyse the full text** when it comes back |
| `2`, `187` | ClinicalTrials.gov registration results | the registry's **structured-results JSON**, not prose (src `187` measured 100% empty) | the same data, possibly a newer posted version | no fetch; R2 only to confirm the registry version/date |
| `37` | conference abstract (ASCO/ESMO/ASH/…) | the conference abstract, verbatim (median ~2.8 K chars) | none reachable (meeting sites answer 403 / JS-shell) | no fetch; R3 only if the pulled body is empty or truncated |
| `49`, uuid-only legacy rows | news / company press release | **the release body, copied verbatim** at ingestion (wire dateline `(GLOBE NEWSWIRE) --`, `/PRNewswire/`, `(BUSINESS WIRE)--` present) | wire pages mostly unreachable | no fetch — check the report against the pulled body |
| numeric-only legacy rows | mostly ClinicalTrials.gov / conference material | registry JSON or abstract text | as the matching class above | same as `2` / `37` |
| `120` | manual entry (人工补录) | measured 100% empty | company-owned pages reachable, wire hosts not | **R3** if a `doi` exists, else the record's own link (once) |
| `245`, `398`, other unlisted ids | unclassified ingestion source / SEC filing | measured empty or no usable sample | unknown / EDGAR answers `403`, `data.sec.gov/…json` carries filing **indexes only** | no fetch → record the reason class |

**Retrieval routes.** Only these templates, and only with values that already came back in the pulled
record. Never invent a URL, never change a host or path, never add, drop or reorder query parameters,
never use a search engine, and never re-try the same content through a different route.

| # | Template | Build from | Returns | Measured (2026-09-17) |
|---|---|---|---|---|
| R2 | `https://clinicaltrials.gov/api/v2/studies/{NCT}` | the registration id inside `clinical_result.full_article_link` or `paper_title` | the registry's own protocol **and posted results** JSON (endpoint values, CIs, p-values, arms) | works: 2/2, ~323 KB |
| R3 | `https://api.openalex.org/works/doi:{doi}` | `clinical_result.doi` | publisher-deposited **abstract** + OA locations; works for journal papers *and* conference abstracts | works: 5/6, 25–49 KB (one returned `abstract_inverted_index: null` — reachable but no abstract) |
| R4 | `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{pm_id}&resultType=core&format=json` | `clinical_result.pm_id` | abstract (`abstractText`), `pmcid`, `isOpenAccess` | works: 1/1 |
| R5 | `https://api.crossref.org/works/{doi}` | `clinical_result.doi` | **bibliographic metadata only** — never clinical evidence | works: 1/1 |
| R6 | `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{pm_id}&resultType=core&format=json` | `clinical_result.pm_id` | abstract + **`pmcid`** + `inPMC` — the key that unlocks full text | works: 1/1 |
| R7 | `https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML` | the `pmcid` that **R6** just returned | the **PMC full text** as JATS XML: sections, tables, endpoint numbers | works: 4/5, 63–99 KB — the single failure is per record (`500` when that paper is not in PMC/OA), not a dead route |

**The analysis surface is the deepest body you can obtain — depth is not comparability.** A scientific fact
does not become a different fact because it was disclosed in an abstract rather than in a full text, so
"the full text is longer" must never be used to call two records incomparable. What depth changes is *how
much of the record is available to you*: it decides whether a report can speak about PFS, a hazard ratio, a
subgroup or grade-3 safety at all. So:

- **`src=1` (PubMed) is the documenting case.** Even when `abstract_text` is present, spend the two calls —
  **R6** to read `pmcid` / `inPMC`, then **R7** for the full text — and when R7 returns, the **full text is
the analysis surface**, not a cross-check on the abstract. Measured 2026-09-17 over three `src=1` rows: the
  abstract (2.6 K chars) carries 30 / 41 / 2 of the numerals the full text (49–99 K chars) carries, i.e.
  **88–99 % of the full text's numbers appear nowhere in the abstract** (absent dimensions included PFS,
  HR / ORR / DoR, TTR, p = / n =, subgroup and grade-3 safety; see
  `docs/evidence/source-link-accessibility-2026-09-17.json`, `pmc_fulltext_information_gain`).
- **Every other class keeps its measured deepest body** and needs no extra call: `37` / `49` / uuid rows —
  the pulled `abstract_text` *is* the deepest carrier that exists; `2` / `187` — the pulled body already *is*
  the registry JSON, so the registry holds no deeper layer for you.
- A paper where R6 returns no `pmcid`, or `inPMC: N`, stays at abstract depth and is reported as its own
  reason class (无 PMCID / **非 OA**) instead of being counted as a failed fetch.

**Facts that exist only in the full text are allowed — but they must carry their own label.** When a number
comes from a deeper body than the pulled fields, write its 时点 / 分析集 / 人群 next to it, and name a
subgroup, post-hoc or updated-cutoff analysis as exactly that. Never let a full-text-only number read as the
primary analysis merely because it is more precise, and never merge two depths into one unlabelled figure.
For the same reason a divergence between the full text and the pulled fields is not automatically a library
error: when the two are different disclosure versions (different cutoff, cohort or analysis set), record it
as a version difference and name it — only a same-metric, same-label conflict is written
`原文 <值>；库内记录 <值>{{ref_n}}`.

**Citation link follows the analysis depth.** When a record's facts rest on a retrieved full text, its
`citations.json` entry must point at that full text instead of the abstract/publisher page — otherwise the
reader who clicks the superscript lands on a page that does not contain the numbers the report used. Exactly
one substitution per record, built only from the `PMCID` that R6 returned:

| # | Template | When |
|---|---|---|
| C1 | `https://pmc.ncbi.nlm.nih.gov/articles/{PMCID}/` | **default** — the canonical human full-text page, what a reader can actually open |
| C2 | `https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML` | allowed alternative — the exact byte source the run read (say so in the coverage line) |

Measured 2026-09-17: **C1 answers a reCAPTCHA challenge to our datacenter egress and C2 is the URL we can
and did fetch.** C1 is therefore only ever *written* as a citation, never fetched as evidence; a browser
passes the challenge that our egress does not. Every other citation entry keeps `link` byte-for-byte from
`full_article_link` — this is the *only* exception to the byte-for-byte rule, it never applies to `title` or
`paper_release_time_str`, and no other URL may be written.

**The record's own `full_article_link` page is a last resort, and accessibility is per host** (measured
2026-09-17 over 30 representative links: 22 fail, 3 succeed, plus the route calls). Do not treat "the link
page" as one thing:

- **Do not fetch these hosts at all** — they answer `403` / anti-bot / JS-shell, so the attempt only burns
  budget and inflates the failed-call count: `businesswire.com`, `globenewswire.com`, `mp.weixin.qq.com`,
  `www.sec.gov`, `cslide.ctimeetingtech.com`, `www.abstractsonline.com`, `ascopubs.org`,
  `meetings.asco.org`, `www.sciencedirect.com`, `jitc.bmj.com`, `www.annalsofoncology.org`,
  `pubmed.ncbi.nlm.nih.gov` (cookie wall), `www.chinadrugtrials.org.cn`, `library.ehaweb.org`,
  `sabcs.org`, `oncologypro.esmo.org`. Record the reason class instead. (This is the *human-facing* host
  class; the API endpoints above, including R7's full text, are unaffected. An earlier note that PMC
  `fullTextXML` was "unusable (500/502)" was wrong — that `500` is per record, see R7.)
- **These work**: `prnewswire.com` ✅ (a 55.8 K-char release carrying the trial numbers) and **company-owned
  news pages** ✅ (`bioinvent.com`, `hanchorbio.com` both returned the release body with analysis numbers).
- So fetch the record's own link **at most once per record**, and only when (i) the record carries no usable
  route key (`doi` / `pm_id` / registration id), or (ii) its host is in the working class above or is
  unknown. One attempt, no retry, no substitute URL. Full article text is normally out of reach — retrieve
  the abstract- or registry-level original (or the press-release body) and say so.
- **`src=49` needs no external fetch at all**: the pulled `abstract_text` *is* the press-release text, so
  "checking it against the original" means checking that the report stays faithful to that body — fetching
  the wire page adds nothing and usually fails.

**Budget and failure handling.** **One** pass over the selection; at most **one** fetch per record, except
`src=1`, which may spend **two** (R6 → R7 — a single retrieval chain, still one record, one pass) and where
the two calls are the **primary** retrieval, not a fallback for a missing body.
Whole-run cap: **40** `web_fetch` calls. If the selection is larger than the budget, fetch for the records
that carry the key conclusions first and state the coverage. A failed fetch is dropped — no retry, no alternative route,
no substitute URL — and its reason class is recorded. `web_fetch` writes each response under
`/workspace/tool_results/web_fetch/…`: copy what you need to `/workspace/sources/<esid>.<route>.json|md`
(that path is archived with the run, so the evidence stays auditable) and **digest it with a script** —
never paste a response body into the context.

**Divergence.** Compare like with like: a divergence is a *material clinical number* that the original
states differently from the pulled fields (endpoint value, unit, p-value, CI, HR/OR/RR, n, population,
analysis time point). Then the **original wins** and the report writes both values in the fixed form
`原文 <值>；库内记录 <值>{{ref_n}}` — never silently pick one. Absence in the original is **not** evidence
that the pulled value is wrong (abstract-level originals are the norm and omit detail): keep the pulled
value and add no marker. Original text never enters the report body — at most a short phrase, never a
paragraph (a mechanical ≥60-character verbatim guard runs in `evals/fact-check`).

**Say it in the evidence scope.** The evidence-scope block (unified template's `证据范围`, cross-trial /
mixed templates' `比较口径`) carries one line beginning `原文核对：` that gives how many retrieved records
were re-checked against the original, **naming the route or the source class per group**, and which records
could not be, grouped by reason class (抓取受限 / 无登记号或 DOI / 该来源不公开 / 无 PMCID / 非 OA). A
non-fetch path is still a named path: `库内正文即原文摘要（src=1，未取 PMC 全文）` is a valid entry. For every
`src=1` group the line must also state the PMC outcome — full text taken (`PMC11270764`), no `pmcid`, or not
OA — and if a full text was archived under `/workspace/sources/`, both the PMID/PMCID and the word 全文 must
appear, so a reader can tell "checked against the actual full text" from "checked against the abstract".
**State the depth per record, not just per group**: say how many records were analysed at full-text depth
("2 条按全文分析 / 1 条仅摘要级"), so that a fact missing from the report can be attributed to the source
("the full text does not state it") rather than to the run ("we never looked") — the two must stay
distinguishable in the deliverable, and a record whose citation `link` was pointed at the full text (C1/C2)
is exactly such a full-text-depth record.
Example: `原文核对：3/3 条已复核（src=1 取 PMC 全文 PMC11270764、PMC8449961；1 条无 PMCID 仅核库内摘要；
src=37 库内正文即会议摘要原文）；1 条未复核（src=49 新闻稿：库内正文即通稿原文，未做外部抓取）`. A run that
re-checked none must say so, and a run that fetched nothing because a source class is structurally
unreachable must name that class instead of reporting a generic failure.

## Consumer-field mapping (v0.11 attachment fields → params fields)

| v0.11 attachment field | v0.12 params field(s) |
| --- | --- |
| `source_title` | `clinical_result.paper_title` |
| `source_url` | `clinical_result.full_article_link` |
| `source_paper_release_time_str` | `clinical_result.paper_release_time` (datetime string `YYYY-MM-DD HH:MM:SS`; only its `YYYY-MM-DD` date part goes into the citation JSON) |
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
   - citation fields (`paper_title`, `full_article_link`, `paper_release_time` — date part only, and when returned
     `journal`/`doi`/`pm_id`) for the separate final citation JSON;
   - trial identity: registration no. (`projects.associate_ids`), trial short name
     (`trial_abbreviation`), sponsor (`company_ids`/`company_name_*`), drug IDs/names
     (`arms[].drugs[].drug_earth_id` + names);
   - clinical content fields: `abstract_text`, `summary`, `study_results` (endpoint records),
     design/arms context.
4. Build the internal worksheet exactly as described in `references/input-and-extraction.md`, using
   these pulled fields as the per-record source.

## Large-batch delegation via subagents (OPTIONAL)

> Status: **platform-supported, and enabled on our deployment — still opt-in.** The default path remains
> "Agent pulls every selected esid directly" per the protocol above; delegation is a context-bounding
> strategy for large selections, not a required step and not a speed-up.

When the deployment exposes the `task` tool (backend `SubAgentCapability` registered and
`capabilities_config.subagents` enabled) and the number of selected esids is more than 5, the Agent
MAY delegate extraction to subagents to keep the main-thread context
bounded. This is a performance strategy, **not a change to the evidence boundary**: only the pulled
fields (`abstract_text`/`summary`/`study_results`/design context) are evidence, and every extracted
value must still carry its source esid / marker number.

- **Chunking**: split the esid list by input order into **balanced chunks of at most 5 esids**
  (6 esids → 3+3; 20 esids → 5+5+5+5). Never split finer than 5 — each chunk costs one serial subagent
  turn — and avoid a one-esid remainder when the split can be balanced. Chunk boundaries must never
  reorder markers.
- **One `task` call per chunk**: `subagent_type: "general-purpose"`, with a fully self-contained
  `description` stating exactly which esids to pull (or the tool call parameters), the exact
  `selected_fields` to use, the exact per-trial fields to extract (same as the evidence worksheet in
  `references/input-and-extraction.md`), and the exact compact output format including the source esid
  / marker number on every extracted value.
- **Output discipline**: the subagent returns only a compact structured summary (short trial name,
  arm/label, endpoint values, p-values/CIs, source marker). Keep the returned text small (a few hundred
  characters per trial) so the 2–4 per-chunk summaries do not re-bloat the main thread.
- **Citation correctness**: `{{ref_n}}` assignment stays global by input esid order regardless of
  which chunk processed it, and covers only the records that actually returned (see *Unretrievable
  selected items*). Subagents must echo the source marker; the main Agent maps those to ref
  markers and deduplicates.
- **Constraints**: `task` accepts only two parameters, `subagent_type` and `description`, and every call
  is stateless (no follow-ups — put everything needed in the description); a subagent does **not**
  inherit this Skill's prompt or the project system prompt, so the description must repeat the
  `selected_fields`, the fields to extract, and the output format in full; recursive depth is limited
  (do not nest delegation deeper than one level); multiple `task` calls in one message execute
  **serially**, so treat delegation as a context-saving device rather than a parallel speed-up.
- **Small selections favor direct pulls**: with 6–8 selected esids whose records are small (a few
  endpoints each, short `abstract_text`/`study_results`), pulling them directly in one or two
  `selected_fields`-bounded calls is usually faster and at least as accurate as delegating. Delegation is a
  context-bounding device for genuinely heavy payloads (or for a persisted file a script cannot digest),
  not a default for every selection above 5.
- **Fallback**: if the `task` tool is not visible/available, ignore this section and pull every
  selected esid directly (default protocol). Never skip a source because delegation is unavailable.

**Platform facts** (verified against the Tool Smith backend source, 2026-09-10):

1. `capabilities_config.subagents` defaults to `False` (`schemas/capabilities.py`) and is switched on per
   project; once on, the main Agent sees the `task` tool. It is **enabled on our deployment**.
2. The child agent comes from the same `create_chat_agent()` factory, so it inherits the default
   capabilities — the params MCP tool, `load_skill`, the filesystem and code execution — and shares the
   main Agent's filesystem, credentials and quota.
3. A subagent does **not** inherit the project system prompt: the backend swaps in generic subagent
   instructions whenever `recursive_depth > 0`. It still sees the skill list and may call `load_skill`,
   but never depend on that — the `description` must carry the extraction spec itself.
4. Several `task` calls in one message run **serially** (the backend never enables pydantic-ai
   `allow_concurrent_tool_calls`), despite the tool description promising concurrency.
5. Platform recursion allows main → child → grandchild (`max_recursive_depth = 2`); this Skill stays
   stricter and uses a single level.
6. Still unmeasured: the end-to-end token/latency benefit at 6–20 esids. Keep delegation opt-in until a
   real large-batch run confirms it.

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
superseded by the params tool path. Field-name grounding for pulls now comes from the params tool's own
`selected_fields` description (`ALLOWED_FIELD_NAMES` / `ALLOWED_FIELDS`), which is what the model sees at
run time; the repo mirror `docs/params-tool-schema.md` is regenerated from that live schema with
`toolsmith-publish tool-doc` and is for maintainers — it is **not** part of the deployed skill package,
so never plan a run around reading it. Re-verify the mirror whenever the tool schema changes before
changing `selected_fields`.
Production request orchestration remains owned by the backend; the params tool is the delivery path.
