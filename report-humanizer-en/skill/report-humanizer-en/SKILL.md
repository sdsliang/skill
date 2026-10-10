---
name: report-humanizer-en
description: Use when writing, editing or reviewing English or bilingual analytical report prose. Removes template scaffolding, empty inflation, process narration and self-explanation. Keeps terminology, abbreviations and drug names consistent including English to Chinese conversion rules with a drug-dictionary tool fallback. Covers pharma pipeline, clinical result, disease landscape, market and policy reports and any ToolSmith project report. Not for authorship detection or detector evasion.
---

# Report Humanizer (English)

Rewrite English report prose so it reads like a colleague wrote it for a decision maker: conclusion first, facts and evidence only, consistent terminology, no explanation of how you worked.

Three modes:

- **Embedded writing**: follow these rules while generating the report. Deliver only the prose, no rewrite explanation, no pattern checklist, no self-assessment.
- **Rewrite draft**: take an existing draft, output the rewrite. Explanation goes outside the deliverable (in conversation), unless explicitly requested.
- **Review only**: give issue list and suggestions, do not modify files. Write to files only when requested.

Supporting files (read as needed):

1. `references/patterns-en.md`: complete expression-problem inventory (structural → phrasing → English-specific), each with report-domain before/after pairs.
2. `references/naming-bilingual.md`: entity and term naming rules for English/Chinese, including drug-name lookup procedure and fallback when dictionary returns nothing.
3. `references/examples.md`: full paragraph before/after pairs (including counter-examples showing what to preserve).

## 1. Priority order

When conflicts arise, resolve in this order:

1. **Preserve information and degree of certainty.** Do not add numbers, names, dates, quotes, sources, conclusions or causal claims beyond the input and user-supplied material. Do not drop independent information, negations, comparison objects, scope, conditions, timeframes, completion status or attribution. Do not turn correlation into causation, possible into certain, planned into completed, subgroup or post-hoc analysis into primary conclusion.
2. **Respect user's editing scope and register.** Polish does not default to expansion, added arguments, changed conclusion or restructure. Do these only when explicitly requested.
3. **Match the document's existing voice.** When a sample exists (other chapters of the same report, prior similar reports), adopt its sentence length, terminology and narrative habit; do not transplant data or positions from the sample into the text. Without a sample, preserve the input's register.
4. **Fix concrete expression problems.** The pattern list is a checklist, not a word blacklist. Leave sound passages alone.

## 2. Report voice and reader

The report reader is a decision maker: they want evidence for judgment, not a work log, not the writer's self-commentary.

- **Answer first.** Each section leads with the judgment, then supporting facts. Do not use a suspense structure that introduces background then reasons step by step to a conclusion.
- **One idea per paragraph.** Organize paragraphs around one judgment; do not force every section to the same length for neatness.
- **Stop when the point is made.** A sentence without new information is surplus, including closing flourishes, transitional scaffolding and significance paragraphs.
- **Stable terminology.** Same entity, same endpoint, same metric, same form throughout (see Section 4).
- **Allow necessary formality.** Formal reports may use passive voice, nominalizations, qualifiers; do not casualize rigorous expression for the sake of naturalness, and do not delete genuine qualifiers in the name of removing tells.
- **No marketing tone.** Do not hype products, make promises, or dress facts in ecosystem/empower language.

## 3. Hard ban: no process narration or self-explanation in reports

This is the strongest rule for reports, especially ToolSmith project deliverables. If any of the following appear in the deliverable, delete them:

- **Process narration**: "This report is based on N pieces of evidence / searched X data sources", "To improve comparability we standardized...", "I first verified registration numbers then extracted endpoints", "I will now present three aspects", "This section introduces..., the next section...".
- **Tool and workflow accounting**: "After searching with XX tool", "following standardization", "filled per established template" — unless the reader needs to know the definition to trust the claim (see exceptions below).
- **Choice rationales and inner debate**: "The reason for selecting these two trials is...", "I tend to believe", "After weighing considerations we decided", "If we did not make this assumption, it would lead to..." — reasoning stays in your head, the report gets conclusion and evidence.
- **Self-assessment and confidence statements**: "The analysis is reliable", "The conclusion is robust", "High confidence", "This judgment may contain bias" — express uncertainty through data definitions (non-significant, not reported, wide interval), not self-evaluation.
- **Empty uncertainty declarations**: "Available material is limited, cannot provide more information", "Data may be incomplete" — unless you can state which item is missing and which judgment it affects.
- **Rewrite ceremony**: "(Optimized / AI tells removed)", "Below is the revised version", "Let me know if you need further changes".
- **AI meta-labels**: Do not write "Generated by AI", "The model may err, please verify", do not write "If needed I can further..." customer-service tails.

**Permitted exceptions** (write these, and write each once): data cutoff time and source definition, inclusion/exclusion criteria, denominator and population definition, follow-up and analysis timepoints, endpoint definitions and statistical assumptions, genuine limitations and unreported items, any statement that changes whether the reader trusts the conclusion or acts.

The test is one sentence: **Does this statement change what the reader believes or does?** Yes → write it clearly, write it once; No → delete.

A second direct test: **Is this sentence about my work, or about the facts?** About my work → delete.

**Wording inside the exception.** A disclosure the host contract mandates (for example "full text not retrieved, checked against the abstract level", "one record was excluded") must be written, but write it as a **property of the material**, not as your runtime environment, tooling or link chain: write "all four records in this batch are abstract-level, none full-text", not "this run had no external network, the PubMed→PMC chain could not be started". The first is the definition the reader needs; the second is working conditions you do not owe anyone.

## 4. Data and provenance discipline

- Every number, comparison, timepoint in the report must trace back to input or source; **do not produce new numbers**, **do not write "not reported" as "absent"**, **do not directly compare numbers across trials** (unless the input itself provided a comparable control).
- Dose, stage, sample size, HR/OR/RR, 95% CI, p-value, units, percentage precision: **preserve verbatim**, do not round, convert or merge.
- Distinguish pre-specified analysis from post-hoc analysis, planned endpoint from achieved endpoint, primary endpoint from exploratory endpoint.
- Tables and figures each serve their role: a figure does not repeat numbers already in a table, a table does not rely on prose repetition. The prose does not recite table contents cell by cell.
- **Byte-frozen protected content**: citation markers and anchors, table data, list order, code blocks and inline code, commands, paths, URLs, IDs, YAML front matter, structured data (JSON, etc.). These are not touched during polish.

## 5. Terminology and naming (English/Chinese)

Abbreviations: give full form and abbreviation at first appearance (`pembrolizumab, an anti-PD-1 monoclonal antibody`), then use one form consistently; use only one form throughout, do not mix aliases in the same document.

**Drug names (hard procedure)**

1. **Common sense first.** Common-drug English/Chinese pairs are settled knowledge, use them directly: `pembrolizumab = 帕博利珠单抗`, `bevacizumab = 贝伐珠单抗`, `osimertinib = 奥希替尼`. When certain, do not look up.
2. **Uncertain → look up dictionary.** Choose one method in availability order, **look up once or twice maximum, no chaining attempts**:
   - When the host project has already returned paired fields, use them directly without translating yourself: such as `drug_earth_name_cn` / `drug_earth_name_en` in parameterized search results.
   - Drug dictionary tool: `report-query-drug` for ToolSmith report projects (pass name in `drug_names`, toggle Chinese/English output with `is_en`); or `pharmcube-mcp-drugBaseLiteCN` for Pharmcube MCP; or Linking API `drug` entity (to retrieve standard name and aliases).
   - When multiple candidates are returned, take the one consistent with the report context (R&D institution, target, indication), not the one with highest popularity.
3. **Not found → fall back by direction, never invent a translation:**
   - **English → Chinese: do not force a translation, keep the English name** (if `zongertinib` has no verified Chinese correspondence, keep writing English, do not transliterate or create an unverified name like 宗格替尼).
   - **Chinese → English: use pinyin** (if the input gives a Chinese colloquial name with no English correspondence, write pinyin and optionally bracket the Chinese original on first appearance).
   - At no time abbreviate to a speculated Chinese short name or English acronym; do not treat a brand name as a generic name, and do not substitute a generic name on your own (if the original uses the brand name, keep the brand name, optionally bracket the generic).

Other entities follow the same rule: trial names and registration numbers (NCT/ChiCTR/..., copy verbatim, do not change case or reorder), company names (standard short form preferred, optionally give full form on first appearance), targets (follow the input's standard form), endpoints (give full form on first abbreviation, e.g. `OS, overall survival`), disease names (standard Chinese name, optionally bracket English), stage and line of therapy (`Phase III trial`, `second-line`, consistent throughout).

English/Chinese mixed text: Chinese prose uses Chinese punctuation, English proper names and abbreviations keep original case and hyphens; do not add spaces between Chinese and English unless the document's existing style does so; numbers use Arabic numerals.

**Notation must be consistent across the whole document (typography only, never the value).** Source material mixes decimal points and percent spacing all the time; copying that through gives one value two forms, which is one of the most visible outsourcing/machine tells:

- **One decimal point only**: if the source writes a middle dot (`10·3 months`) while the rest of the prose uses a full stop, normalize to `10.3 months`; never change the number of decimals or the value.
- **Percent sign tight against the number**: `64%`, not `64 %`.
- **One range symbol only**: do not mix `0.46–0.78` with `0.46-0.78`; follow the document's existing convention if it has one.
- **Add nothing**: no thousands separators, no units, no uniform two-decimal rounding invented on your own.
- **Scope**: prose and lists. Tables, citation markers, code, paths, URLs and IDs follow the host contract; when the host declares tables protected, leave them as they are and at least unify the prose and lists. Only the symbol form and spacing may change — the **value and digit count** of every number must match the draft.

For details and more examples see `references/naming-bilingual.md`.

## 6. Workflow

1. **Read through and mark.** Determine the document type and target reader, mark conclusions, numbers, definitions, qualifiers and sources; at the same time mark expression problems per `references/patterns-en.md` (for structural problems, look at paragraph shape, not just sentences).
2. **Rewrite, do not patch.** Changing flagged phrases one by one leaves the same tone; rewrite the whole paragraph around its main point. Preserve every sourced claim.
3. **Self-check.** Go through the Section 7 checklist item by item: any new facts added, qualifiers dropped, possible written as certain, process written into prose? Run `scripts/tell-scan.py` (Section 8) when a mechanical pass helps.
4. **Deliver.** Hand over only the prose; explanation goes outside the prose. Leave sound passages alone.

## 7. Pre-delivery checklist

- Any sentence that talks about "my work" rather than "the facts"? (Section 3) — this is the first check item.
- Can every new piece of concrete information be found in the input or user material? If not, retract it.
- Are independent information, negations, comparison objects, scope, time, completion status, attribution complete? Are meanings carried by "possibly/reportedly/over/only/planned/not yet" preserved?
- Any correlation written as causation, not-reported written as absent, subgroup written as primary conclusion?
- Do numbers, units, confidence intervals, citation markers, table data, IDs match the original verbatim?
- Is notation consistent throughout (decimal point / percent sign / range symbol)? Does one value appear in two forms? Did unifying it change any value?
- Is the same entity/abbreviation/drug name written consistently throughout? Do abbreviations have a first-appearance definition? For drug names not found in the dictionary, does the fallback follow direction (English→Chinese keep English, Chinese→English use pinyin) without inventing names?
- Do closings only repeat praise or best wishes? Any unsupported "significance" sentences left behind?
- Are originally sound passages forced into change? Are quotes, titles, proper nouns, the terms themselves kept intact?

Do not substitute "word count fell" or "pattern count fell" or a self-assessment score for fact and semantic verification.

## 8. Mechanical self-check (optional assistant)

The skill bundle ships a dependency-free scanner: `scripts/tell-scan.py` (published with the bundle, relative path unchanged).

```bash
python3 -B scripts/tell-scan.py report.md            # language auto-detected
python3 -B scripts/tell-scan.py report.md --json     # JSON for host-side assertions
python3 -B scripts/tell-scan.py report.md --weak     # strict: weak hits fail too
python3 -B scripts/tell-scan.py report.md --allow S-INFL-02,W-AIWORD
```

Rule families:

| Family | What it catches |
|---|---|
| `S-PROC-01..07` | Process narration, tooling and method accounting, choice rationale, self-assessment and confidence talk, rewrite ceremony, AI meta-labels |
| `S-INFL-01..04` | Contrast inflation, inflated significance, borrowed authority with no named source, empty evaluation |
| `S-STRUCT-01..04` | Reciting tables and figures, empty closers, summary restatement, heading restatement |
| `W-*` | Phrasing level: em dash pairs, overused AI words, hedge stacks, vague association, nominalization, shallow -ing riders, decorative bold, plus document-level counts (dash and bold density, **mixed notation**) |

Boundaries (important):

- It is an **assistant, not a judge**: a hit is not an order to edit, and no hit is not proof of quality. Only `[strong]` hits justify a change; `[weak]` hits need company in the same passage and a look at context.
- When process narration or self-explanation appears in a deliverable, delete it by Section 3 without consulting the scan at all.
- Exit codes: `0` no strong hits / `3` strong hits present (usable as a gate) / `2` usage or file error.
- **Never let a fall in hit count stand in for fact and semantic verification** (end of Section 7).

## 9. When not to act

Quoted text, titles, proper nouns, the terms themselves, table data, structured data, and styles the user explicitly asked to preserve are not touched. Deliberate authorial use of contrast, parallelism, em dashes, first person and emotion: preserve when allowed by report voice and when they carry information. This skill handles expression problems only, not authorship detection, and does not guarantee text will pass any detector.

---

## 10. Worked example

**Before (trial readout draft with AI tells):**
> It's worth noting that the Phase III trial (NCT04839458) enrolled 847 patients with advanced non-small cell lung cancer. Not just any patients, but those who had progressed on prior platinum-based chemotherapy. The primary endpoint was overall survival (OS) — a pivotal measure in oncology trials — and the results were nothing short of remarkable. The median OS in the experimental arm was 18.3 months (95% CI: 16.1–21.2) versus 13.9 months (95% CI: 12.4–15.8) in the control arm (HR 0.72, p=0.0043). This improvement underscores the clinical benefit of adding pembrolizumab. Adverse events were consistent with the known safety profile, and the study showcases the drug's potential in this setting.

**After:**
> The Phase III trial (NCT04839458) enrolled 847 patients with advanced non-small cell lung cancer who had progressed on prior platinum-based chemotherapy. The primary endpoint was overall survival (OS). Median OS was 18.3 months (95% CI: 16.1–21.2) in the experimental arm versus 13.9 months (95% CI: 12.4–15.8) in the control arm (HR 0.72, p=0.0043). Adverse events were consistent with the known safety profile.
