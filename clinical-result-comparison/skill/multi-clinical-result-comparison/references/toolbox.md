# Toolbox — the six packaged scripts (use these, do not write your own)

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

| Step | Script | Writes |
| --- | --- | --- |
| Pull → readable sources + ref inventory | `scripts/prep_sources.py` | `work/sources/ref_<n>.txt`, `work/refs.json` |
| Payload → candidate facts (never transcribe by hand) | `scripts/build_ledger.py --scaffold` | `work/facts.candidates.json` |
| Facts → strict ledger (+ the only validation) | `scripts/build_ledger.py` | `work/ledger.json` |
| Body + appendix + `{{ref_n}}` | `scripts/render-facts.py` | `/workspace/output/report.md` (in place) |
| Any small edit to an existing file | `scripts/patch.py` | the file, in place |
| Chart product | `scripts/make_chart.py` | `/workspace/visualizations/<fixed name>.json` |
| Citation JSON | `scripts/make_citations.py` | `/workspace/output/citations.json` |
| Final mechanical check | `scripts/check_report.py` | nothing (exit code only) |

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

**Digest 样式（直接读这份输出；数值已在其中，不要再打开 `work/sources/ref_n.txt` 手动提取数字 — `build_ledger.py --scaffold` 会从 payload 自动提取）：**

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

## 2. `build_ledger.py` — scaffold candidate facts, then validate the fact ledger

```
python3 scripts/build_ledger.py --scaffold        # payload → work/facts.candidates.json (run first)
python3 scripts/build_ledger.py --stats          # fact counts by ref and kind
python3 scripts/build_ledger.py --check           # validate only, write nothing
python3 scripts/build_ledger.py                   # write work/ledger.json
```

### 2a. `--scaffold` — the pulled payload written out as candidate rows

Mechanical transcription is the one part of the ledger you should never do by hand: it is where
values get mistyped and where the largest output-token block goes. Run this **once, after
`prep_sources.py`** (it needs `work/refs.json` and `work/sources/ref_<n>.txt`) and edit the file it
writes instead of typing the numbers yourself.

```
python3 scripts/build_ledger.py --scaffold --tool-results /workspace/tool_results \
    --refs work/refs.json --sources work/sources --out work/facts.candidates.json
```

* Output `--out` defaults to `work/facts.candidates.json` and has exactly the `facts.json` shape
  (`records` / `facts`), plus a `_notes` array the compiler ignores. Fill in the blanks and feed it
  back with the default mode — you do not hand-write this file from scratch.
* One `records[]` entry per pulled esid (`conclusion` is always empty — you write it), one `facts[]`
  entry per `clinical_result_study_results[]` row that carries a usable `result`.
* `value` / `unit` / `statistics` / `timepoint` / `assessment` are copied **verbatim** from the
  payload, `arm` is the payload's regimen label, and `quote` is the first source sentence in
  `work/sources/ref_<n>.txt` that contains that value (`""` plus a note when there is none — then
  copy the sentence from the original yourself).
* One esid pulled several times collapses to one record, as in `prep_sources.py`.
* **The candidate file is a checklist, not the ledger.** Every row still has to be verified against
  the original, and `_notes` names the ones that need work (no quote, no endpoint name, `kind`
  defaulted because the payload attributes nothing). Delete every row that is not a material,
  cross-disclosure-comparable value, and write from the original text the material values the
  payload never carried — a thin payload (endpoint labels that are only a time point, empty
  `endpoint_attribute`, several placebo arms per dose) yields mostly unusable rows, and the notes
  say so; do not pad the ledger to keep them.
* It never reads `work/facts.json`, never writes `work/ledger.json` and never validates anything:
  that stays the default mode's job. Exit `0` written · `3` `work/refs.json` missing/empty (run
  `prep_sources.py` first) · `2` unreadable payload or unwritable `--out`.

### 2b. default mode — the only validation gate

* Input `--facts` (default `work/facts.json`), output `--out` (default `work/ledger.json`),
  `--refs` for trial/`source_file` defaults.
* You author `facts.json` (the clinical judgment); the script does every mechanical check and
  writes the strict shape `render-facts.py` accepts: `{"records":[…],"facts":[…]}`. Each record
  = `ref` + `identity` + `conclusion` (optionally `trial`, `title`, `design`, `arms`, `coverage`);
  each fact = the 15 fields `id, ref, study, version, endpoint, arm, population, timepoint,
  assessment, kind, value, unit, statistics, source_file, quote` — absent
  `version`/`population`/`timepoint`/`assessment` are filled with `未报告`, `statistics` with `""`.
  `kind` ∈ `试验设计｜试验结论｜有效性｜安全性｜PK/PD｜PRO｜其他` (a `·家族` suffix is allowed).
* Checks that fail the whole compile (exit 3, **nothing written**, existing ledger untouched) and
  are printed together: `quote` is not an exact substring of that ref's source file, `value` is
  absent from `quote`, `kind` outside the vocabulary, duplicate `id`, unknown `ref`, more than one
  `study` per ref. A failing compile never leaves a half-written ledger.
* Exit `0` written (or clean under `--check`) · `3` findings · `2` usage/IO.

## 3. `render-facts.py` — body + appendix, in one write

```
python3 scripts/render-facts.py --ledger work/ledger.json --draft /workspace/output/report.md \
        --out /workspace/output/report.md --audit work/audit.json
```

`--draft` **and** `--out` may be the same path: the script reads the whole draft, resolves every
`[[fact:id]]` / `[[result:id]]` token, appends the evidence-alignment appendix and replaces the
file atomically. So the body is written **once**, in the canonical form, and rendered in place —
there is no separate `work/draft.md` stage and no second copy. Exit `3` on a schema/validation
failure (unknown token id, missing field) with nothing written.

**Token 语法（直接照抄；不要用 `--help` 或构造临时 ledger 试错探索语法）：**

`build_ledger.py --scaffold` 输出的 `work/facts.candidates.json` 骨架已有正确字段形状，填入 `endpoint` / `arm` / `kind` / `quote` 空项后通过 `build_ledger.py` 编译生成 `work/ledger.json`，再用以下 token 语法引用：

```json
{"id": "f1", "ref": "ref_1", "study": "HARMONi-6", "version": "",
 "endpoint": "PFS", "arm": "依沃西单抗+化疗", "population": "",
 "timepoint": "中位", "assessment": "", "kind": "有效性",
 "value": "11.1", "unit": "月", "statistics": "HR 0.44, p<0.0001",
 "source_file": "work/sources/ref_1.txt",
 "quote": "median PFS was 11.1 months (95% CI 9.6\u20139.6) in the ivonescimab plus chemotherapy group"}
```

在报告草稿正文里（`[[fact:id]]` 与 `[[result:id]]` 等价）：

```markdown
依沃西单抗联合化疗组中位 PFS [[fact:f1]]（对比组 [[fact:f2]]）
```

渲染器把 token 替换为带 `{{ref_n}}` 标记的文本，并在文末追加完整附录。**正文里凡是来自 ledger 的数值，一律写 token，不要硬编码同一数值两次** — token 绑定后格式由渲染器统一，消灭事后 `patch.py` 修正数值格式不一致的循环（这个循环在已测 run 里耗时 3–5 分钟）。

两个强制条件（任一不满足，渲染拒绝写出，文件不变）：
- `value`（`11.1`）必须逐字出现在 `quote` 里
- `quote` 必须是对应 `work/sources/ref_1.txt` 的精确子串

## 4. `patch.py` — asserted, atomic, whole-file find/replace

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

## 5. `make_chart.py` — one chart product from a content-only spec

```
python3 scripts/make_chart.py work/charts/endpoint-bar-1.json
```

* You write **only the content**: `type` (`bar`|`line`|`timeline`), `file` (the fixed product
  name), `title`, `subTitle`, `dataSource`, `describe`, `axisXTitle`/`axisYTitle` (bar/line),
  `data[]`. The script pulls the skeleton from this Skill's `templates/charts/` and the envelope
  (`id` + `iframe_template`) from the mounted `chart-visualization-json` skill, then validates
  with the upstream CLI. Never hand-write the envelope and never hardcode `iframe_template`.
* `data` rows: bar/line = `{label, value, description}` (line also needs `group`); timeline =
  `{label, content, description, time}` where `time` is the anchor (`YYYY-MM`). `description`
  carries the `{{ref_n}}` markers; the figure is the skeleton, the numbers live in the tables.
* Fixed product names: `endpoint-bar-<n>.json`, `endpoint-line-<n>.json` (n = order of that type
  in the report), `evidence-timeline.json`. A `file`/`type` mismatch or a slug name exits 2.
* `--sort auto|none|value-desc|value-asc|time-asc` (defaults: bar `value-desc`, line `none`,
  timeline `time-asc`), `--strict` (warnings become failures), `--dry-run`, `--json`.
* Exit `0` written and validated · `3` structural finding, nothing written (missing label/
  description, empty or non-numeric `data`, a timeline event without `time`, a line row without
  `group`) · `4` written but the validator is unavailable — say so, never call it validated · `2`
  usage/IO.
* Warnings only (on stderr): label > 18 / content > 16 characters, and a digit outside the `time`
  anchor in a timeline row (registry ids such as `NCT02729025` are exempt). `--strict` fails them.

## 6. `make_citations.py` — the citation JSON

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

## 7. `check_report.py` — the mechanical pre-delivery pass

```
python3 scripts/check_report.py -v            # then fix what it printed and re-run
```

Checks the report text (unresolved `[[fact:…]]` tokens, `{{…}}` braces that are not `ref_n`
markers, `entity:` syntax, the appendix title **and** that it has data rows, that the appendix
starts with the renderer's one-line legend rather than a hand-written specification paragraph, and
that the title appears exactly once so a hand-written appendix can never stand beside the rendered
one), marker ⇄ citation parity in both directions, citation entry shape (empty title, extra fields,
a fenced code block),
chart products (envelope keys exactly `{id, iframe_template, option}`, non-empty data, type vs
file name, and that every `::visualization` target exists under the fixed prefix), plus internal
leaks in the delivered text (`source_file`, `tool_results`, `esid`, `/workspace/work/`, a
`ledger|facts.json` path, a Mermaid block). Warnings only: run-logistics wording, a chart product
never referenced by the report, a table cell citing the same ref twice, and chart text sharing an
8-character run with a table cell (registry ids and citation-title text are exempt).

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
* the report narrating itself: a self-label bullet or table column (`分析模式` / `选择依据` /
  `可比性结论` / `对齐等级` / `不绘图原因` / `有限并列原因` / `纳入标准` / `检索策略` / `报告结构`), our own
  work presented as a class (`可绘图` / `只能有限并列` / `不具备绘图条件` / `部分对齐` / `仅背景对齐`), a
  process phrase (`本次选择` / `本次纳入` / `我们选择` / `本轮`), an internal field or runtime word
  (`src=` / `esid` / `payload` / `JSONL` / `MCP` / 工作区 / 沙箱), or a self-audit tail (`无未复核记录` /
  `无遗漏` / `全部通过`). The two kept slots are the non-head-to-head caveat and the `原文核对：`
  line, both written as material statements. Broad self-reference (`本报告` / `本次`) is a warning,
  not a failure.

Exit `0` all green · `3` at least one FAIL · `4` warnings only · `2` usage/IO. Run it **before**
`present_artifact`; the run is not finished while it reports a FAIL.

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
  per comparable reading, quoted from `work/sources/ref_<n>.txt`). `--stats` tells you the counts;
  the `--scaffold` notes tell you which candidate rows still need work.
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
* **Did my body survive?** One `check_report.py -v` pass, and the assertions inside `patch.py`. A
  confirmation re-read of your own `output/report.md` is a fallback, not the default; if you need
  it, read one narrow range once.

## What is still yours

`facts.json` (which numbers and conclusions are worth stating, and their quotes), the report
prose and structure, the chart content (which skeleton, which rows), and every clinical judgment
about comparability. Everything else above is mechanical and already written.
