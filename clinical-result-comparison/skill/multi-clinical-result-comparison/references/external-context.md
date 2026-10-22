# External Context (bounded, objective expansion)

The selected records answer the question the user asked; they cannot tell the reader whether the observed
effect is large or small **for that class**. That judgement needs a small number of external anchors, and this
file is the only place that permits them. Everything here is deliberately narrow: four admissible question
types, one tool, a hard budget, and a mechanically enforced placement. It is not an open research route.

`references/input-contract.md` (*Evidence source priority*) stays the single authority for the evidence
boundary and owns this channel's permissions and budget. Nothing here relaxes the retrieval rules for the
**selected** records, and nothing here creates a second research surface beside them.

## The four admissible questions (closed set)

**This channel is on by default.** The user message never has to ask for it: nobody types «另外给个参照» into a fixed
product prompt. Unless the user explicitly forbids outside context, run the default lookup below once per
clinical-question cluster, before writing the conclusion. It is a step of the deliverable, not an optional extra.

### Default lookup (and its own smaller budget)

| Step | What | Budget |
|---|---|---|
| D1 | one **C1** call per clinical-question cluster (the class baseline) | 1 call per cluster, ≤2 calls per deliverable |
| D2 | one **C2** call when the selected trials name the standard-of-care comparator on the same endpoint | 1 call per deliverable |

**D1 runs even when the selected set looks like the class.** R78 measured what happens otherwise: given a
"the set already holds ≥2 same-class molecules, so the baseline is internal" escape hatch, **3 of 3 runs took it**
and one of them counted a PD-1/VEGF bispecific plus a PD-1 antibody as "the same class". A set that is the class
is exactly when the class baseline is worth *confirming* — and the confirmation is one call whose normal result is
"no record absent from the inventory". So the escape hatch is gone: run the call, then record the outcome.

**Every run ends in exactly one of three recorded states.** The omission rule below makes a successful lookup
invisible (nothing is written, nothing is said), which by itself cannot be told apart from a step that never ran.
So the step ends with one command, and `check_report.py` refuses a deliverable without it:

| State | Command | Meaning |
|---|---|---|
| `appended` | `prep_sources.py --external --result … [--only-esids …]` | at least one alignable source was pulled **and will be cited** |
| `none_alignable` | `prep_sources.py --external --result … --none-found` | the call ran; nothing in the pull is alignable |
| `not_applicable` | `prep_sources.py --external --not-applicable --reason "<clause>"` | the lookup does not apply at all: no same-class target or modality to ask about, no named comparator outside the set, or the user forbade outside context |

`--not-applicable` is a written claim, not a silent skip: the `--reason` lands in `work/external.json` and is read
back by the gate (and by whoever audits the run). "The set is already the class" is **not** a valid reason.

`C3` / `C4` are **not** part of the default lookup — they are used only when the material itself raises that
question (a dose gap the selected records leave open, an earlier disclosure of the same trial). One call per
question, never a second attempt with looser filters.

The hard ceiling is unchanged (≤3 per cluster, ≤6 per deliverable, ≤6 tool calls, ≤2 web calls) — the default
lookup is the subset that runs without being asked.

**If nothing alignable comes back, omit the section entirely.** Default-on does not mean "always show a block":
a `本组未检索到可对齐的外部参照。` line in every ordinary report is noise, and the search itself is never
reported. Write the `## 外部参照（非所选记录）` section only when at least one C1/C2 value is alignable, and say
nothing anywhere else about what was or was not found.

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
`selected_fields` allowlist, and **no retry with a looser filter**. An oversized response ends the question; it
does not get re-run.

The allowlist is minimal but **citable**: `clinical_result.extra_esid`, `clinical_result.paper_title`,
`clinical_result.paper_release_time`, `clinical_result.full_article_link` (plus arms/endpoint/time-point/design
labels when the block needs them) — **never** `abstract_text`. `citations.json` demands a non-empty title, link
and date per cited ref, so a field set without `full_article_link` is not "minimal", it is unusable: the source
gets pulled and can never be cited, which leaves a dangling ref in the inventory.

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
- **append only what you will cite.** A pull can carry a dozen records when the block needs one: name the
  ones you will use with `--only-esids`. An appended source that the block never cites is a gate failure
  (it also means the reader paid for a pull that produced nothing).
- budget exhausted or nothing alignable → **omit the section** (default lookup) and record
  `--none-found`, then stop. The search is not continued under a different wording, and an oversized payload is
  not re-queried.

## Provenance: the same chain, a separate block

Retrieve first, then append through the packaged script — never hand-edit the inventory, never renumber:

```bash
# append (the usual path): only the sources the block will cite
python3 /workspace/skills/multi-clinical-result-comparison/scripts/prep_sources.py --external \
    --result <tool_results>/<tool>/call_<id>.jsonl --only-esids <the ones the block will cite> \
    --max-external 6 2>&1 | tail -30; echo "EXIT=${PIPESTATUS[0]}"
# the call ran, nothing alignable (block omitted; the report stays silent)
python3 …/prep_sources.py --external --result <call_<id>.jsonl> --none-found 2>&1 | tail -5
# the lookup does not apply at all (needs a reason; "the set is already the class" is not one)
python3 …/prep_sources.py --external --not-applicable --question C1 \
    --reason "<no same-class target in this indication | no named comparator outside the set | user forbade outside context>"
```

It appends `ref_{k+1}…` after the selected `ref_1…ref_k`, writes the same `work/sources/ref_<n>.txt` bodies,
marks every appended entry `"origin":"external"` in `work/refs.json`, and exits 3 rather than renumber, re-add
an esid already present, or exceed the budget. `make_citations.py` then emits them under the **unchanged**
citation schema, so each external number is a clickable, byte-for-byte source.

External numbers stay **out of the fact ledger** (`work/facts.json` / `work/ledger.json`): the appendix and
every alignment table belong to the selected records alone. The archived `ref_<n>.txt` body plus the citation
link is the audit trail — do not add these values to the fact rows.

## Placement (mechanically enforced by `check_report.py`)

Exactly one section — **written whenever the default lookup produced an alignable value, and whenever the user
asked for a reference** — placed after the comparison sections and **before the final conclusion section** (so the
conclusion may point at it), and never inside the appendix:

```markdown
## 外部参照（非所选记录）

外部参照仅用于背景校准，不构成头对头比较。

- GEMINI 1·vedolizumab：溃疡性结肠炎诱导期第 6 周临床应答 47.1% vs 安慰剂 25.5%{{ref_4}}｜与本组的差异：终点为第 6 周应答、III 期静脉单抗，与本组第 12 周缓解不同域｜用途：同类药物在这一人群的通常水平
- SWIFT·emvistegrast：第 12 周临床应答 66% vs 37%{{ref_5}}｜与本组的差异：同靶点口服小分子、n=238，安慰剂率明显更高｜用途：同类药物在这一人群的通常水平
```

Rules:

- one line per external source, exact shape
  `- <药物/试验>：<可对齐数值与口径>{{ref_n}}｜与本组的差异：<人群/终点/时点/设计>｜用途：<同类药物在这一人群的通常水平|已获批治疗在同一终点的水平|区分药物本身与剂量或时点的差别|核对本试验此前的披露>` — plain reader-facing words, **never** the internal question codes `C1`–`C4`;
- the fixed line `外部参照仅用于背景校准，不构成头对头比较。` opens the section, verbatim;
- **an English deliverable** uses the English counterparts and nothing else: heading
  `## External reference (non-selected sources)`, the fixed line
  `External references are for background calibration only; they do not constitute a head-to-head comparison.`,
  and the keys `Difference from this set:` / `Use:` in place of `与本组的差异：` / `用途：`, with the
  same plain-words `Use:` value (`use: the level other drugs of this class reach in this population`) —
  never the C1–C4 codes;
- an `origin:external` marker may appear **only at or after this section and never on a table line** (`|`);
  it never enters an alignment cell, a snapshot table, a chart JSON, or the appendix;
- a conclusion sentence may name an external source with its marker to block an over-attribution
  (「因此不能把该结果单独归因于靶点」), but that sentence carries no external **numbers**;
- the section reports the reference, not the search: no call counts, tool names, timeouts or coverage claims.

**Next block, different job.** A *still-running* trial has nothing to align, so it never belongs here — it goes
into the separate `## 在研同类试验（尚未读出）` block that follows this one (`references/ongoing-trials.md`).
The two steps share the "always leave a record" rule and nothing else: different tool, different state file
(`work/watchlist.json`), different gate.

## Failure forms

| Situation | What the report says |
|---|---|
| nothing alignable found (default lookup) | **omit the section**; no sentence about the search anywhere |
| nothing alignable found although the user asked for a reference | `本组未检索到可对齐的外部参照。` |
| payload too large / filter too wide | stop; write nothing for that question |
| two external sources disagree | cite the primary one and state the divergence inside that entry line; never resolve it with a claim |
| only non-primary sources available | treat as unavailable |
