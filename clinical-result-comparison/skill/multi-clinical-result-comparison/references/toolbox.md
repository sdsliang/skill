# Toolbox — the packaged scripts (use these, do not write your own)

Every mechanical step of this Skill already has a script, shipped inside this bundle under
`scripts/` (next to `render-facts.py`). **Run them; do not re-implement them.** Writing your own
`build_ledger.py` / `fix_draft.py` / `digest.py` / `clean_draft.py` helper is the single largest
waste in this pipeline (measured: 25–55 % of one run's output tokens, and the source of every
"I could not find the target string" re-prompt). If a step below does not do what you need,
extend the command with its documented flags, or report the gap — do not write a replacement.

At run time this bundle is mounted at `/workspace/skills/multi-clinical-result-comparison/`, so
invoke each script by its full path — `python3 /workspace/skills/multi-clinical-result-comparison/scripts/<name>.py …`. A bare `scripts/…`
does **not** resolve from cwd `/workspace`. Below, `scripts/<name>.py` is shorthand for that
directory. Defaults are the contract paths; pass an explicit flag only to deviate.

## Two levels of output — and what you never pre-verify

Every script here separates **FAIL** from **WARN**, and the exit code follows that split:

| level | meaning | exit | what you do |
| --- | --- | --- | --- |
| `FAIL` / `FINDINGS (n) — nothing written` | provenance or structure is broken: a value that is not in its quote, a quote that is not in its source, a broken `{{ref_n}}`, a malformed envelope, a non-numeric value | `3` | stop, fix the input, re-run — the file was **not** written |
| `WARN` / `advisory` | completeness or style advice: an empty caption, a chart the report never references, a cell repeating a ref, run-logistics wording | `0` | the artifact is written and deliverable — **do nothing**, it is not a failure |

**Never pre-verify an advisory.** Hand-simulating a completeness or style rule while writing —
before the script has run — costs more output tokens than this whole mechanical layer, and it
cannot come out right: the scripts own those rules. Write the artifact, run the script once, act
on the `FAIL`s. A `WARN` you never act on is a normal, finished run.

**Invoke them so a failure is readable.** Every script prints the reason for a non-zero exit on
**stderr** (and writes the same findings into its JSON where it writes one). Run them as:

```
python3 -B /workspace/skills/multi-clinical-result-comparison/scripts/<name>.py … 2>&1 | tail -30; echo "EXIT=${PIPESTATUS[0]}"
```

* A pipeline reports the **last** command's status, so `… | tail -40; echo "EXIT=$?"` prints
  `tail`'s `0` even when the script failed — never write that form: it hides the failure behind a
  green exit code.
* **One marker, one meaning.** `EXIT=${PIPESTATUS[0]}` is the form for every script.
  `tell-scan.py`'s own idiom `… ; echo "SCAN_EXIT=$?"` (§9) is equally readable — both markers are
  recognised — but never write the bare `… | tail -40; echo "EXIT=$?"` form above, and never mix
  the two in one command chain.
* On a non-zero exit, read the printed message and fix **the input it names** — for
  `render-facts.py` that is a token id the ledger does not define, or a ledger field (`errors[]`
  in `--audit` carries the same list). Do **not** bisect the file with `head -n`, do **not**
  re-derive a traceback with `runpy`, do **not** go fishing with `--help`: the reason is already
  on stderr and each probe costs a full round-trip. Measured: one end-to-end silent failure cost
  **18 tool calls — 28% of that run's steps** (R62-1).

| Step | Script | Writes |
| --- | --- | --- |
| Pull → readable sources + ref inventory | `scripts/prep_sources.py` | `work/sources/ref_<n>.txt`, `work/refs.json` |
| Per-ref shard files → one facts file (**only** if you split the rows) | `scripts/merge_ref_facts.py` | `work/facts.json` |
| Facts → strict ledger (+ the only validation) | `scripts/build_ledger.py` | `work/ledger.json` |
| Body + appendix + `{{ref_n}}` | `scripts/render-facts.py` | `/workspace/output/report.md` (in place) |
| Any small edit to an existing file | `scripts/patch.py` | the file, in place |
| Chart product | `scripts/make_chart.py` | `/workspace/visualizations/<fixed name>.json` |
| Citation JSON | `scripts/make_citations.py` | `/workspace/output/citations.json` |
| Final mechanical check | `scripts/check_report.py` | nothing (exit code only) |
| Prose gate (finished file) | `scripts/tell-scan.py` | nothing (exit code only) |

Run them one after another in a **single `execute` call** where the steps are independent
(e.g. `mkdir -p`, then `prep_sources`, then `build_ledger` in one shell line) instead of one call
per script.

## 1. `prep_sources.py` — the pulled records into files you can read

```
python3 scripts/prep_sources.py --esids <esid_1,esid_2,…>            # selection order
python3 scripts/prep_sources.py --esids-file work/selected.txt      # one esid per line, # comments
python3 scripts/prep_sources.py --esids … --full --quiet
```

* `--result PATH` — the raw `tool_results/**/*.jsonl` pull; omitted, the newest pull with records
  under `--tool-results` (default `/workspace/tool_results`) is used.
* `--sources-dir` (default `work/sources`), `--refs` (default `work/refs.json`),
  `--body-chars` (digest body cap, default 4000), `--full` (whole bodies in the digest),
  `--quiet` (files only).
* refs are numbered in **selection order**, only over esids that came back; a missing esid is
  reported and consumes **no** number (it is not a row in the report, not a marker, not a
  citation entry). A duplicate esid keeps its first ref and is reported on stderr.
* Each `work/sources/ref_<n>.txt` holds the record's own text (title/link/release metadata, the
  abstract or summary body, arms, study results) — this is the file `build_ledger` verifies
  `quote` against, and it is the surface a fact's evidence depth is measured on.
* `work/refs.json` carries `title`, `link`, `paper_release_time_str` (date part only) plus the
  clinical fields used for identity. `make_citations.py` copies `title`/`link` byte-for-byte.
* Exit `0` all found · `3` at least one selected esid returned no record (files still written for
  the rest) · `2` usage/IO.

**Digest 样式（直接读这份输出；数值已在其中，不要再打开 `work/sources/ref_n.txt` 手动提取数字）：**

```
# 记录清单（2 条；来自 /workspace/tool_results/…/result.jsonl）

## ref_1 · esid=a1b2c3d4 · 正文 1820 字
title: HARMONi-6: ivonescimab plus chemotherapy versus pembrolizumab plus chemotherapy…
link: https://doi.org/10.1016/j.lancet.2024.07.013
release: 2024-09-08
journal/doi/pm_id: The Lancet / 10.1016/j.lancet.2024.07.013 / 39260374
trial_abbreviation: HARMONi-6
indication: 非小细胞肺癌 | primary_endpoint: PFS
source_file: work/sources/ref_1.txt
正文：
median PFS was 11.1 months (95% CI 9.6–12.7) in the ivonescimab plus chemotherapy group
versus 7.1 months (6.3–8.6) in the pembrolizumab plus chemotherapy group (HR 0.44, p<0.0001)
…（正文上限 4000 字；`--full` 不截断；`--quiet` 只写文件不打印）
```

`work/sources/ref_1.txt` 是 `render-facts.py` 验证 `quote` 的来源文件，不是你读数字的入口。

## 2. `build_ledger.py` — validate the fact ledger

```
python3 scripts/build_ledger.py --stats        # fact counts by ref and kind
python3 scripts/build_ledger.py --check        # validate only, write nothing
python3 scripts/build_ledger.py                # write work/ledger.json
```

### 2a. authoring the rows — write only what a script cannot derive

The rows are the clinical judgement, and at these selections they are a **small** generated block —
measured at 10–13 % of a turn's output tokens, next to ~75 % in reasoning. Two rules keep them small
without touching a single fact:

* **Omit `source_file`.** The compiler resolves it from `ref` through `work/refs.json`.
* **Omit `version` / `population` / `timepoint` / `assessment` / `statistics`** when the source reports
  nothing for them: the compiler fills `未报告` / empty. Those keys are *allowed* to be absent — writing
  them out is pure token cost.

What remains is `id`, `ref`, `study`, `kind`, `endpoint`, `arm`, `value`, `unit`, `quote`. `arm` and
`unit` stay present as keys and may be `""`; everything else is a clinical judgement no script can make
(the `quote` is the provenance anchor — never let a script derive it). Settle the numeric format
(decimal separator `.` vs `·`, unit and statistic wording) **before** the first row is written: a later
`patch.py` pass over it cost 3–5 minutes in a measured run.

**Write the rows in the main thread.** A measured round made the per-ref split the default for 3+ refs
and a model declined it in 3/3 runs, on the arithmetic — the rows are small next to the reasoning, and
reasoning does not split. If you do split them, `merge_ref_facts.py` (§3) merges the shards. The
payload-checklist mode `build_ledger.py --scaffold` still exists and still writes
`work/facts.candidates.json`, but **the workflow does not use it**: measured over three live runs its
rows were almost entirely rewritten (0 of 33 ids reused, `value`+`endpoint` matched 0 of 51 final rows,
and the last ref was missing altogether) while still costing a call and a full read of the file.

### 2b. default mode — the only validation gate

* Input `--facts` (default `work/facts.json`), output `--out` (default `work/ledger.json`),
  `--refs` for trial/`source_file` defaults.
* You author `facts.json` (the clinical judgment); the script does every mechanical check and
  writes the strict shape `render-facts.py` accepts: `{"records":[…],"facts":[…]}`. Each record
  = `ref` + `identity` + `conclusion` (optionally `trial`, `title`, `design`, `arms`, `coverage`);
  each fact = the fields `id, ref, study, kind, endpoint, arm, value, unit, quote` —
  `version` / `population` / `timepoint` / `assessment` / `statistics` / `source_file` **may be omitted entirely**
  and are filled in for you (`未报告` / empty / resolved from `ref`); writing them out is pure token cost.
  `arm` 与 `unit` 必须作为键存在，但值可以为 `""`：设计类事实（随机与样本量、数据截止、检验界值、
  中位随访等）本身就没有 arm；p 界值、HR、NE/NR 等无量纲值本身就没有 unit。**不要编造分组名或单位
  凑过校验**——空值本身就是合法的，编译器必须接受它。空 `unit` 渲染为
  `0.0049{{ref_n}}`（不带尾随空格），空 `arm` 在单元格里整段省略、不留分隔符；若 `kind` 不是
  `试验设计` 而 `arm` 为空，编译通过但打一条 `WARN` 提醒补分组。
  `kind` ∈ `试验设计｜试验结论｜有效性｜安全性｜PK/PD｜PRO｜其他` (a `·家族` suffix is allowed).
* Checks that fail the whole compile (exit 3, **nothing written**, existing ledger untouched) and
  are printed together: `quote` is not an exact substring of that ref's source file, `value` is
  absent from `quote`, `kind` outside the vocabulary, duplicate `id`, unknown `ref`, more than one
  `study` per ref. A failing compile never leaves a half-written ledger.
* Exit `0` written (or clean under `--check`) · `3` findings · `2` usage/IO.

## 3. `merge_ref_facts.py` — merge per-ref shard files (optional escape hatch)

```
python3 scripts/merge_ref_facts.py --shards work --refs work/refs.json --out work/facts.json
python3 scripts/merge_ref_facts.py --check        # merge in memory, write nothing
```

Exists for a run that split the fact rows across subagents, one shard file per ref — the workflow does
not ask for that (the rows are normally written in the main thread; see §2a and
`references/input-contract.md`, *Fact rows*), so in the default pipeline nothing produces shard files. It concatenates `work/facts.ref_<n>.json`
in ref order, accepts either the `facts.json` shape (`{"records":[…],"facts":[…]}`) or a bare list of
facts, and is the only place the merged file is produced: **never re-type a shard's rows.**

It does not validate clinical content — `build_ledger.py` (below) remains the only validation gate —
but it checks the things that are about the **split**, so a bad shard is reported next to its own
filename:

* a fact or record whose `ref` is not in `work/refs.json`;
* the same fact `id` or record `ref` delivered by two shards (ids must be unique across shards);
* a shard file that is unreadable JSON, or carries neither `records` nor `facts`;
* `WARN` for a ref no shard covered (writing no rows for a thin source is legal; silently dropping a
  ref is not).

Exit `0` merged (or clean under `--check`) · `3` findings / no shard files / unreadable `work/refs.json`
(nothing written) · `2` unwritable `--out`.

## 4. `render-facts.py` — body + appendix, in one write

```
python3 scripts/render-facts.py --ledger work/ledger.json --draft /workspace/output/report.md \
        --out /workspace/output/report.md --audit work/audit.json
```

`--draft` **and** `--out` may be the same path: the script reads the whole draft, resolves every
`[[fact:id]]` / `[[result:id]]` token, appends the evidence-alignment appendix and replaces the
file atomically. So the body is written **once**, in the canonical form, and rendered in place —
there is no separate `work/draft.md` stage and no second copy. Exit `3` on a schema/validation
failure (unknown token id, missing field, a `value` absent from its `quote`, a `{{ref_n}}` that
resolves to nothing) with nothing written: the file is left exactly as it was, and **every
finding is printed on stderr** (the same list is in `--audit`'s `errors[]`).

**渲染是幂等的：就地重渲染安全，同一个输入恒得同一个输出、只保留一个附录。**
附录是这个渲染器自己输出在文末的那一节，重渲染会**替换**它而不是再追加一份（audit 里
`idempotent_rerender: true` 就是这条路径）。因此**不需要**为了重渲染把正文抄到
`work/body.md` / 别的副本、**不需要**读回已渲染的产物去核对附录有没有多一份 ——
要对齐格式改完 `work/facts.json` 后直接重跑上面那条命令即可。两条已实测的格式事实：

- `unit` 为空时值后面**不留空格、不留占位符**：`"5.3" + ""` 渲染成 `5.3`，不要自己补 `—` 或不换行空格
- 附录列/行的排列完全由 ledger 推导（`appendix_layout`、`appendix_columns`、`appendix_rows`、`appendix_cells_filled` 都在 `--audit` 里），不要手工编辑附录

**Token 语法（直接照抄；不要用 `--help` 或构造临时 ledger 试错探索语法）：**

`work/facts.json` 就是上面那个形状（`records` / `facts` 两个数组），通过 `build_ledger.py` 编译生成 `work/ledger.json`，再用以下 token 语法引用：

```json
{"id": "f1", "ref": "ref_1", "study": "HARMONi-6", "version": "",
 "endpoint": "PFS", "arm": "依沃西单抗+化疗", "population": "",
 "timepoint": "中位", "assessment": "", "kind": "有效性",
 "value": "11.1", "unit": "月", "statistics": "HR 0.44, p<0.0001",
 "source_file": "work/sources/ref_1.txt",
 "quote": "median PFS was 11.1 months (95% CI 9.6\u201312.7) in the ivonescimab plus chemotherapy group"}
```

在报告草稿正文里（`[[fact:id]]` 与 `[[result:id]]` 等价）：

```markdown
依沃西单抗联合化疗组中位 PFS [[fact:f1]]（对比组 [[fact:f2]]）
```

渲染器把 token 替换为带 `{{ref_n}}` 标记的文本，并在文末追加完整附录。**正文里凡是来自 ledger 的数值，一律写 token，不要硬编码同一数值两次** — token 绑定后格式由渲染器统一，消灭事后 `patch.py` 修正数值格式不一致的循环（这个循环在已测 run 里耗时 3–5 分钟）。

两个强制条件（任一不满足，编译与渲染都拒绝写出，文件不变）：
- `value` 必须**逐字**是 `quote` 的子串（只归一两种东西：连续空白压成一个空格、各种减号统一为 `-`）
- `quote` 必须是对应 `work/sources/ref_1.txt` 的、同样归一后的精确子串

**照抄原文印出来的那串字符**：不要重排、不要改写分隔符、不要把算出来的数写进 `value`。实测判定（源文印 `中位 PFS 为 11.1 · 9.8 个月`）：

| `value` 写法 | 判定 | 原因 |
| --- | --- | --- |
| `11.1 · 9.8` | ✅ | 连分隔符一起照抄，就是子串 |
| `11.1` | ✅ | 子串允许只截取其中一段 |
| `11.1 vs 9.8` | ❌ | 把 `·` 改写成 `vs`，就不再是子串 |
| `-5.3`（源文只印 `5.3`） | ❌ | **派生值不属于 `value`**：两臂差值、算出来的变化量写进正文，`value` 只放原文数字 |
| `Fifty-one`（源文印的是文字数字） | ✅ | `value` 是**源文印出来的那串字符**，不要求是阿拉伯数字：文字数字照抄文字，不要为了凑数字去换一条 quote（`unit` 照样可以写 `例`） |

**提交前自检就是编译本身**，不需要渲染、也不需要临时 ledger 试错：
`python3 scripts/build_ledger.py --facts work/facts.json --check` 只校验不写文件，逐条报出上面两类问题（exit 3）；默认编译模式跑的是同一套检查。

## 5. `patch.py` — asserted, atomic, whole-file find/replace

```
python3 scripts/patch.py <file> --find '<text>' --replace '<text>' [--count N]
python3 scripts/patch.py <file> --find '<text>' --count 0        # assert absent, change nothing
python3 scripts/patch.py <file> --find '<anchor>' --replace $'\n<new paragraph>' --insert-after --unescape
```

* Default `--count 1`: the number of matches **must** equal it, otherwise exit 3 and the file is
  left untouched (the match context is printed so you can see what differed). `--count 0` asserts
  the text is absent.
* `--replace ''` / `--delete` removes; `--find-file` / `--replace-file` read the payload from a
  file (use them for multi-line CJK text instead of shell-quoting); `--unescape` turns `\n`/`\t`
  into real characters; `--dry-run` reports without writing.
* **A `--find` value that starts with `-` needs the equals form**: `--find=-5.3` (argparse reads
  `--find -5.3` as a flag). Same for `--replace`.
* Use this instead of authoring a one-off fix script, and instead of `edit_file` on anything that
  is not the report body.
* Exit `0` applied · `3` assertion failed (nothing written) · `2` usage/IO.

## 6. `make_chart.py` — one chart product from a content-only spec

```
python3 scripts/make_chart.py work/charts/endpoint-bar-1.json
```

* You write **only the content**: `type` (`bar`|`line`|`timeline`), `file` (the fixed product
  name), `language` (`zh`|`en`, same as the report), `title`, `subTitle`, `dataSource`, `describe`,
  `axisXTitle`/`axisYTitle` (bar/line), `data[]`. The script pulls the `config` skeleton from this
  Skill's `templates/charts/`, the envelope (`id` + `version` + `iframe_template`) from the mounted
  `chart-component-layout-json-validation` skill, renders `describe`/`dataSource` into `config.notes`,
  then validates with the upstream CLI. Never hand-write the envelope, never hardcode
  `iframe_template`/`version`, and never put `option`/`config`/`notes` in the spec (exits `3`).
* `data` rows: bar/line = `{label, value, description}` (line also needs `group`); timeline =
  `{label, content, description, time}` where `time` is the anchor (`YYYY-MM`). `description`
  carries the `{{ref_n}}` markers; the figure is the skeleton, the numbers live in the tables.
* Fixed product names: `endpoint-bar-<n>.json`, `endpoint-line-<n>.json` (n = order of that type
  in the report), `evidence-timeline.json`. A `file`/`type` mismatch or a slug name exits 2.
* `--sort auto|none|value-desc|value-asc|time-asc` (defaults: bar `value-desc`, line `none`,
  timeline `time-asc`), `--strict` (warnings become failures), `--dry-run`, `--json`.
* Exit `0` written (that includes a run that only warned) · `3` structural finding, nothing written
  (empty or non-numeric `data`, a timeline event without `time`, a `file`/`type` mismatch) · `4`
  written but the validator is unavailable — say so, never call it validated · `2` usage/IO.
* Warnings only (on stderr, exit stays `0`): an empty `label` / `description` / `group`, label >
  18 / content > 16 characters, and a digit outside the `time` anchor in a timeline row (registry
  ids such as `NCT02729025` are exempt). Never pre-check these while writing the spec; `--strict`
  is the opt-in switch that turns them into failures.

## 7. `make_citations.py` — the citation JSON

```
python3 scripts/make_citations.py --report /workspace/output/report.md
python3 scripts/make_citations.py --report … --full-text ref_2=https://pmc.ncbi.nlm.nih.gov/articles/PMC…
```

* Built from `work/refs.json`; each entry is exactly `{title, link, paper_release_time_str}` with
  `title`/`link` copied byte-for-byte from the pulled record and the release time reduced to
  `YYYY-MM-DD`.
* With `--report`, only refs the report actually cites are written (unused keys are dropped with
  a NOTE — this is what keeps citations ⇄ markers in parity); a report marker with no refs entry,
  an entry with an empty title, or a record that never came back exits 3 with nothing written.
  `--keep-unused` keeps everything (only for debugging), `--check` validates without writing,
  `--print` echoes the body.
* `--full-text ref_n=URL` is the C1/C2 substitution for a record whose facts rest on a retrieved
  PMC full text (repeatable, `http(s)://` only). Exit `0` · `3` parity/format finding · `2` IO.

## 8. `check_report.py` — the mechanical pre-delivery pass

```
python3 scripts/check_report.py -v            # then fix what FAILED and re-run
# WARN 不阻塞（exit 仍是 0），也不要在写之前预检它们：先写、再跑、只修 FAIL。
# 只有 --help 里写明会 fail-closed 的开关（如 make_chart.py --strict）才把建议当致命。
```

Checks the report text (unresolved `[[fact:…]]` tokens, `{{…}}` braces that are not `ref_n`
markers, `entity:` syntax, the appendix title **and** that it has data rows, that the appendix
starts with the renderer's one-line legend rather than a hand-written specification paragraph, and
that the title appears exactly once so a hand-written appendix can never stand beside the rendered
one), marker ⇄ citation parity in both directions, citation entry shape (empty title, extra fields,
a fenced code block),
chart products (envelope keys exactly `{id, version, iframe_template, config}` with `config.kind == "chart"`,
version/template equal to the deployed `config.js`, non-empty data, no retired `describe`/`dataSource` in `config`, type vs
file name, and that every `::visualization` target exists under the fixed prefix), plus internal
leaks in the delivered text (`source_file`, `tool_results`, `esid`, `/workspace/work/`, a
`ledger|facts.json` path, a Mermaid block). Warnings only: run-logistics wording, a chart product
never referenced by the report, and a table cell citing the same ref twice.

**FAIL** rules that keep one number in one place and the appendix renderer-owned:

* a chart that restates its own plotted value in `subTitle` / `describe` /
  `data[].description` — chart prose states the basis, the time-point difference, the direction,
  the comparability and the `{{ref_n}}`, never the plotted number (dose/time/count suffixes such as
  `225 mg`, `每 12 周`, `129 例` are context and pass, and study-internal control/boundary values
  stay allowed);
* a **non-appendix** section that shows a chart *and* a table carrying two or more of that chart's
  plotted values — move the chart, or drop the repeated values from the table. The appendix is the
  fact ledger and values there are expected; the aligned-detail section is where the table belongs;
* an appendix that opens with a prose block instead of the renderer's legend — the appendix is
  renderer output (title, `—` legend, columns), never a place for a layout specification;
* the report narrating itself: through the lens of **meaning, not spelling** — any wording that presents
  our own method, grading or bookkeeping instead of what the material says (the gate names the exact
  token when it fires: e.g. a self-label column heading like `选择依据`, our own verdict turned into a
  class like `部分对齐`, an internal field like `payload`). The two kept slots are the non-head-to-head
  caveat and the `原文核对：` line, both written as material statements. Broad self-reference
  (`本报告` / `本次`) is a warning, not a failure.

Exit `0` — nothing fatal (warnings are printed and do **not** change the exit code) · `3` at least
one FAIL, the product is broken · `2` usage/IO. Run it **before** `present_artifact`; the run is
not finished while it reports a FAIL. Fix FAILs only.

## 9. `tell-scan.py` — the prose gate (deterministic, no model)

```bash
python3 -B /workspace/skills/multi-clinical-result-comparison/scripts/tell-scan.py /workspace/output/report.md; echo "SCAN_EXIT=$?"
```

It mechanically scans the **finished** report for AI-flavoured prose and report-specific wording
problems — process narration, self-explanation, hype, borrowed authority, section-filler, leftover
draft/work talk, mixed numeric notation — and prints one line per hit with a rule id
(`S-PROC-*` / `S-INFL-*` / `S-STRUCT-*` / `W-*`), the matched text and what the rule wants.

| Exit | Meaning | What you do |
| --- | --- | --- |
| `0` | no strong hit | nothing — deliver (still run `check_report.py` if it has not run yet, and re-run it once if this pass changed wording) |
| `3` | ≥1 **strong** hit | handle each one: rewrite it, or pass `--allow <ID,…>` for the ids you judged inapplicable |
| `2` | usage / missing file | fix the command, not the report |

Flags: `--lang {auto,zh,en}` (default auto, by CJK ratio — a Chinese report needs no flag),
`--json` (per-hit detail, for reading a long hit list), `--weak` (weak hits also count as 3 — not
the default), `--allow ID,ID,…`.

* Strong vs weak is the whole point: a **strong** hit is enough to fix; a **weak** hit (`W-*`, e.g.
  one AI-flavoured word, one decorative dash, 11 bold spans) is a clue to re-read the sentence, not
  an order. Never rewrite to zero out weak hits.
* It is an assister, **not a judge**: a clean scan proves nothing about the writing, and a hit may be
  legitimate (a quoted original, a formal term with a real technical meaning).
* When a hit needs judgement — which rule, how to rewrite — read `references/prose-style-zh.md`
  (the full checklist with 改写前/改写后 examples). Do not read the script's source.
* **It never changes a number** and never authorises dropping a 局限 / 缺口 / 未报告 statement or a
  comparability caveat. Rewriting whole sentences is expected; swapping only the flagged words is
  not a fix. Re-run this gate after a rewrite.

## Questions this file answers so you never read the scripts

Reading a packaged script's source to guess its behaviour is the most expensive habit in this
pipeline (it cost a measured 9 tool calls in one run). The answer is here or in `--help`.

* **Who writes the appendix?** `render-facts.py` — title, legend line and columns are generated
  from `work/ledger.json`. Never hand-write the appendix, a placeholder for it, its legend, or a
  paragraph describing its layout; its rows come from the facts you declared.
* **What does an appendix column header look like?** Renderer decision, not yours: several
disclosures in one trial → `**试验名**<br>注册号 · N 条披露`; one disclosure →
`**可读短标签**<br>ref_n`; a missing tag → `**ref_n**`. Do not transcribe the layout anywhere in
  the body.
* **Which numbers go in the ledger?** Only material, cross-disclosure-comparable values (one row
  per comparable reading, quoted from `work/sources/ref_<n>.txt`). `--stats` tells you the counts and
  which refs/kinds they came from — compare it against the sources you actually read.
* **How do I cite?** `{{ref_n}}` in the body, one `citations.json` entry per ref
  (`make_citations.py` writes the shape). The same ref is cited once per table cell; the appendix
  row already carries its own ref, so the body does not need to repeat it there.
* **`patch.py` says the target is not found.** The string must match the file byte for byte; for a
  find value starting with `-` use `--find=<text>`. Do not fall back to rewriting the whole file,
  and do not re-read your own draft to locate strings — re-render or pass the exact source line.
* **What does the coverage line say?** The material and the depth reached: count, source class in
  words (`PubMed 摘要` / `登记平台结构化结果` / `会议摘要` / `通稿` / `人工补录` / `库内正文即原文摘要`), where
  the check landed, and any record that stayed shallower with the source-side property that capped
  it (`未收录 PMC` / `非 OA 元数据` / `无登记号或 DOI`). Route tokens (`src=1`), internal field names and
  a closing `无未复核记录` are not written into the deliverable.
* **May I write in prose how I aligned the two trials?** No. The deliverable carries findings,
  material properties and the resulting limits — not our method, our categories or our bookkeeping.
  Write the difference itself (timepoint, population, definition, direction) in the reading-boundary
  column, not the class we assigned to it (`部分对齐`, `可绘图`). `check_report.py` fails those.
* **The template's own column names look like the banned ones — are they safe?** Yes, and you do not
  need to re-litigate them per run. The test is **meaning, not spelling**: a word that names a
  *material property* is always legal — `成熟度`, `证据强度`, `判断强度`, `解读边界`, `组内证据关系`,
  `归属组`, `归组依据`, `可比性` as a limit. Only one thing is banned: phrasing that presents **our own
  analysis, grading or process** as a deliverable (`选择依据`-style headings, `部分对齐`-style class
  words). The gate's own message names the token it hit, and settle uncertainty by running
  `check_report.py` once, not by re-deriving each word in your head.
* **Is my aligned-detail column header allowed to end with `（高/中/低可比性）`?** Yes — it states how
  firm the material comparison is. It is not `可比性结论`; do not rewrite it as a class label.
* **Did my body survive?** One `check_report.py -v` pass, and the assertions inside `patch.py`. A
  confirmation re-read of your own `output/report.md` is a fallback, not the default; if you need
  it, read one narrow range once.

## What is still yours

`facts.json` (which numbers and conclusions are worth stating, and their quotes), the report
prose and structure, the chart content (which skeleton, which rows), and every clinical judgment
about comparability. Everything else above is mechanical and already written.
