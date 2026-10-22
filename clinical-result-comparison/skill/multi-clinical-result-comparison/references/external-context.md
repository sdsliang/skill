# External Context (bounded, objective expansion)

The selected records answer the question the user asked; they cannot tell the reader whether the observed
effect is large or small **for that class**. That judgement needs a small number of external anchors, and this
file is the only place that permits them. Everything here is deliberately narrow: four admissible question
types, one tool, a hard budget, and a mechanically enforced placement. It is not an open research route.

`references/input-contract.md` (*Evidence source priority*) stays the single authority for the evidence
boundary and owns this channel's permissions and budget. Nothing here relaxes the retrieval rules for the
**selected** records, and nothing here creates a second research surface beside them.

## The four admissible questions (closed set)

Ask an external question only when it falls in one of these four **and** its answer carries an alignable
number (same metric family, stateable time point). Anything else stays out of the report.

| Code | Question | Why it is admissible |
|---|---|---|
| **C1** | What did another molecule in the same class (same target, same modality) report in the same indication and line of therapy? | Supplies the class baseline the selected trial cannot |
| **C2** | What did the approved / standard-of-care therapy report on the same endpoint? | Anchors what "meaningful" means in this setting |
| **C3** | What did the same drug report at another dose, time point or disclosure? | Separates a molecule-level result from a schedule-level one |
| **C4** | What else has the same trial disclosed? | Confirms identity and the earlier/later state of that trial |

**Not admissible**, however much the report seems to want it: disease epidemiology or burden, market size or
competitive landscape, mechanism textbook knowledge, guideline summaries, "what experts think", a general
literature review. Such a gap is written as a gap.

**Head-to-head stays forbidden.** External numbers never become a comparison row, never re-rank the selected
arms, and never license "target X is worse than target Y". Their permitted uses are exactly: class baseline;
"another molecule in this class did / did not meet the endpoint"; placebo or baseline-rate calibration; and
blocking an over-attribution. See `references/conclusion-language.md`.

## Channel 1 — the structured tool (default, and usually the only one)

External retrieval is the **second query mode of the same** `pharmcube-query-clinical-result-with-params` call
used for the selection pull — no additional tool, no additional dependency. Use the narrowest filter that
answers the question and turn the child-expansion switches off:

| Code | Arguments |
|---|---|
| C1 | `{"target_names":["<靶点>"],"disease_names":["<适应症>"],"child_target_included":false,"child_disease_included":false}` |
| C2 | `{"drug_names":["<已获批药物>"],"disease_names":["<适应症>"]}`, optionally plus `"global_highest_phase":"批准上市"` |
| C3 | `{"drug_names":["<所选药物>"],"disease_names":["<适应症>"]}` — the selected drug's other disclosures |
| C4 | `{"trial_id":"<NCT…>"}` |

Trial-level facts (status, phase, planned enrolment, sponsor) are taken from the record's own design /
`projects` fields, never from a second tool: this route adds **no** new upstream tool to the Skill.

**This tool has no pagination parameter.** A wide filter returns an unbounded payload that can consume the
whole context budget. Therefore: one filter dimension at a time, `child_*_included:false` always, a minimal
`selected_fields` allowlist (identity, arms, endpoint, time point, design labels — **never** `abstract_text`),
and **no retry with a looser filter**. An oversized response ends the question; it does not get re-run.

## Channel 2 — the web (last resort)

Only for a C2 anchor the structured library genuinely does not carry. At most **2 calls per deliverable**
(inside the same external budget), and only for a **primary** source: the journal article page, the registry
record, the conference abstract, or the sponsor's own release. Never a review, a news rewrite, an aggregator,
a database summary page or an AI answer — and never to obtain a number the structured tool returns.

## Budget (hard; a question is asked once)

- **≤3** external sources per clinical-question cluster;
- **≤6** external sources per deliverable;
- **≤6** external tool calls in total (channel 2 ≤2 of them);
- a source that yields no alignable number is **not** written into the report;
- budget exhausted or nothing alignable → write `本组未检索到可对齐的外部参照。` and stop. The search is not
  continued under a different wording, and an oversized payload is not re-queried.

## Provenance: the same chain, a separate block

Retrieve first, then append through the packaged script — never hand-edit the inventory, never renumber:

```bash
python3 /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py --external \
    --result <tool_results>/<tool>/call_<id>.jsonl --max-external 6 2>&1 | tail -30; echo "EXIT=${PIPESTATUS[0]}"
```

It appends `ref_{k+1}…` after the selected `ref_1…ref_k`, writes the same `work/sources/ref_<n>.txt` bodies,
marks every appended entry `"origin":"external"` in `work/refs.json`, and exits 3 rather than renumber, re-add
an esid already present, or exceed the budget. `make_citations.py` then emits them under the **unchanged**
citation schema, so each external number is a clickable, byte-for-byte source.

External numbers stay **out of the fact ledger** (`work/facts.json` / `work/ledger.json`): the appendix and
every alignment table belong to the selected records alone. The archived `ref_<n>.txt` body plus the citation
link is the audit trail — do not add these values to the fact rows.

## Placement (mechanically enforced by `check_report.py`)

Exactly one section, placed after the comparison sections and **before the final conclusion section** (so the
conclusion may point at it), and never inside the appendix:

```markdown
## 外部参照（非所选记录）

外部参照仅用于背景校准，不构成头对头比较。

- GEMINI 1·vedolizumab：溃疡性结肠炎诱导期第 6 周临床应答 47.1% vs 安慰剂 25.5%{{ref_4}}｜与本组的差异：终点为第 6 周应答、III 期静脉单抗，与本组第 12 周缓解不同域｜用途：C1类内基线
- SWIFT·emvistegrast：第 12 周临床应答 66% vs 37%{{ref_5}}｜与本组的差异：同靶点口服小分子、n=238，安慰剂率明显更高｜用途：C1类内基线
```

Rules:

- one line per external source, exact shape
  `- <药物/试验>：<可对齐数值与口径>{{ref_n}}｜与本组的差异：<人群/终点/时点/设计>｜用途：<C1类内基线|C2标准治疗锚点|C3剂量-时点锚定|C4同试验前序披露>`;
- the fixed line `外部参照仅用于背景校准，不构成头对头比较。` opens the section, verbatim;
- **an English deliverable** uses the English counterparts and nothing else: heading
  `## External reference (non-selected sources)`, the fixed line
  `External references are for background calibration only; they do not constitute a head-to-head comparison.`,
  and the keys `Difference from this set:` / `Use:` in place of `与本组的差异：` / `用途：`;
- an `origin:external` marker may appear **only at or after this section and never on a table line** (`|`);
  it never enters an alignment cell, a snapshot table, a chart JSON, or the appendix;
- a conclusion sentence may name an external source with its marker to block an over-attribution
  (「因此不能把该结果单独归因于靶点」), but that sentence carries no external **numbers**;
- the section reports the reference, not the search: no call counts, tool names, timeouts or coverage claims.

## Failure forms

| Situation | What the report says |
|---|---|
| nothing alignable found | `本组未检索到可对齐的外部参照。` |
| payload too large / filter too wide | stop; write nothing for that question |
| two external sources disagree | cite the primary one and state the divergence inside that entry line; never resolve it with a claim |
| only non-primary sources available | treat as unavailable |
