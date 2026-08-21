# Project State

## Repository

- Git repository: `git@github.com:sdsliang/skill.git`
- Project subdirectory: `clinical-result-comparison/`
- Branch: `main`
- Migrated from `/home/xupeipeioo1/apps/clinical-result-comparison` and pushed as root commit `08440ad`.


Build the first Tool Smith Agent for reconstructing complete trial interpretations from multiple user-selected clinical result records, using only their original `source_full_text` and preserving source-level linked citation traceability.

## Housekeeping conventions

- 从 NP Clinical 拉取的示例数据（`evals/**/np-clinical-*/`）不入库：`.gitignore` 已忽略，`fetch-np-clinical-attachments.mjs` 可随时重拉。已提交的历史版本也已从跟踪移除（commit 63c031c）。

## Current version

- System prompt: `v0.7`
- Skill: `multi-clinical-result-comparison` trial-level synthesis `v0.7`

## v0.7 change: attachment-based input（每条结果一个附件文件）

- 背景：原设计把选中的结果以内联 JSON 放进单条 message，用户勾选 20–50 条时容易超上下文。改为：每条结果写成单独 `.md` 附件（`source-001.md`…），随用户消息一起作为附件送达；Agent 按文件名顺序读 `/workspace/uploads/` 下每个附件，`{{ref_n}}` 按文件顺序分配。
- 单文件格式：`# 临床结果来源 {n}` + 三行元数据（`source_title:`/`source_url:`/`source_paper_release_time_str:`）+ `## source_full_text` 标题 + 全文正文。文件名顺序=输入顺序=ref 顺序（仅展示标签，非临床时序）。
- 附件限制（Tool Smith）：每消息 ≤10 文件、每线程 ≤100、单文件 ≤20 MiB；超出时拆分消息/线程，Agent 不假定固定数量。
- 改动文件：`references/input-contract.md`（重写：单文件布局/附件限制/Agent 读取协议/后端 manifest）；`references/input-and-extraction.md`（开头改附件读取）；`SKILL.md`（新增 Input 章节+证据边界措辞）；新增 `system-prompts/multi-clinical-result-comparison-v0.7.md`；README 同步；重建 `dist/multi-clinical-result-comparison-v0.7.zip`（18 文件，含 charts 模板）。
- 新增 `evals/fetch-np-clinical-attachments.mjs`：按条件从 `np_clinical` 拉取并写每源一个附件文件 + `manifest.json`（后端日志用），内置往返校验。默认条件=非小细胞肺癌（indications 135/5718/5719）+ 三期 + 积极。
- 真实测试：拉取 `evals/iteration-16/np-clinical-nsclc-50/`（50 条，条件命中 890 条）；50 个 `.md` + manifest；元数据完整度 title 50/50、url 49/50、time 50/50、空正文 0；Agent 视角对账（读文件→建 ref 台账→比对 manifest）50/50 一致。
- ⚠️ 数据事实修正：此前 NASH 示例用的 indications 516/517 其实是「非酒精性脂肪肝/非酒精性脂肪性肝炎」，不是非小细胞肺癌；ORR 属实体瘤终点，NASH 数据里不存在。本次已查实真实 ID：非小细胞肺癌=135、鳞状非小=5718、非鳞状非小=5719。
- ORR 柱状图实测：50 条中 30 条含 ORR/缓解率；取 3 个一线晚期 NSCLC 随机 III 期研究（CATAPULT I：27.5% vs 13.7%；E4599：35% vs 15%；nab-紫杉醇+卡铂 vs 溶剂型：33% vs 25%）注入 `templates/charts/endpoint-bar.html` 生成 `evals/iteration-16/chart-examples/orr-bar.html/.png`（真实数据，含跨试验可比性提示）。
- ⚠️ 柱状图模板修复（用户反馈）：① 数值刻度原本画在左侧与组别标签重叠 → 改为底部横轴（标准横向柱状图）；② 行高自适应（≤62px，行多时压到 ≥30px）；③ 行密时（rowH<42）组别字号缩到 11、左栏加宽到 224，杜绝长标签越出画布；④ 行密时（rowH<46）隐藏柱端 CI 副行避免串行。实测 51 行全量 ORR（24 个试验）：程序化 getBBox 测量 非同行重叠 0、越出画布 0。

## v0.6 change: evidence-chain timeline diagram

- Added `skill/multi-clinical-result-comparison/references/timeline-diagram.md`: construction rules for a descriptive Mermaid evidence-chain timeline.
- Scope: same-trial inputs only, when consolidation leaves ≥2 genuinely distinct evidence states. Cross-trial/mixed inputs do not get a shared timeline.
- Delivery: a Mermaid fenced code block placed directly above the timeline table in the 证据链总览与时间线 section. Mermaid is rendered natively by the Tool Smith Markdown renderer; it does not use `read_me`/`show_widget`/workspace files and does not require the inline-visualization capability.
- Diagram carries: source-supported chronology (data cutoff → follow-up → analysis milestone → disclosure date; never input order), one node per evidence state (analysis stage/disclosure form + this state's key new content + `{{ref_n}}` markers), a time axis (时间未明 when missing, never guessed), dotted time-to-state links, and a labeled relationship + maturity-direction arrow between consecutive states (更新/新增终点/确认/补充/取代/冲突/不确定 + 加强/基本不变/限定/削弱/无法确定).
- It is descriptive/chronological, not a quantitative series, so it does not require numeric compatibility. It never replaces the exact-value timeline table.
- Fallback: only 1 distinct state or undeterminable order → omit the diagram and state the order uncertainty in the table.
- Updated `SKILL.md` (read list + workflow step 5 + chart rule), `references/same-trial-evolution.md` (new Step 8), `templates/unified-evidence-report.md` (section 三 timeline insertion), `system-prompts/multi-clinical-result-comparison-v0.6.md` (new v0.6 prompt with the timeline rule), and `README.md`.
- Rebuilt `dist/multi-clinical-result-comparison-v0.6.zip` (13 files incl. `references/timeline-diagram.md`).
- Example: `evals/iteration-15/harmoni6-timeline/report.md` + `report.refs.json` — HARMONi-6 4-source/2-state report with the Mermaid timeline inserted. Verified: marker/key parity 4/4, citation keys == fixture count, fixture title/link/release-time parity, no forbidden implementation terms, no unresolved placeholders, Mermaid block bracket/quote balance OK. Mermaid v11.15.0 (bundled via `@streamdown/mermaid`) fully supports the used syntax (`flowchart`, quoted subgraph titles, `direction`, `-.-`, `<br/>`, quoted edge labels).
- Validation note: this workspace cannot run the Tool Smith cloud Benchmark or the actual frontend Mermaid render; validation is local static contract + syntax review.

## Chart templates (v0.7 direction): 蓝紫色系 HTML 图表

- Created `skill/multi-clinical-result-comparison/templates/charts/` with 3 single-file HTML chart templates (pure SVG/CSS/vanilla JS, no external deps → offline + Tool Smith sandbox ready):
  - `evidence-timeline.html` — same-trial 证据链时间轴（旗帜 + 时间轴基线 + 证据链成熟度渐变带，hover 提示；events 按证据披露时间先后排列）。
  - `endpoint-bar.html` — 混合/不同试验、无时间维终点（ORR 类）横向柱状图（轨道+主柱+高光、值+CI、hover）。
  - `endpoint-line.html` — 混合/不同试验、时间维终点（体重类）折线图；全部系列仅 1 个点 → 自动单点模式（只画点+值，不强行连线）。
- `chart-tokens.css`：蓝紫色系基准（靛蓝 #4f46e5 → 紫罗兰 #7c3aed → 紫 #a855f7；系列色 --c-s1..s6；语义用明度区分，不用红绿）。全部抽成 CSS 变量，模板内联；底部附 `--viz-*` 注入映射表，接宿主主题时整体替换 :root 即可，图代码不改。
- `references/chart-templates.md`：选型规则（同试验→时间轴；无时间维→柱状；有时间维→折线）、填数约束（仅 source_full_text、不推断阶段/顺序）、交付方式（workspace 文件 + `::visualization` 引用，图前后保留文字）、与 lieflat-charts 的关系。
- 验证：三模板 JS 语法 `node --check` 全过；headless Chrome 渲染出 PNG（36/32/30KB）；DOM 校验 svg/rect/circle/text 数量与代码预期一致、标题均注入成功。
- 版本边界：同试验时间轴随 v0.6；柱状/折线（定量图）供混合场景，计划随 v0.7 放开；`dist/` 未重建（待用户定夺是否并入 v0.7 后重建）。
- 相关安装：从 GitHub 拉了 `lieflat-charts`（64 图型，`~/.agents/skills/lieflat-charts`）供 fancy 图扩展；新建参考型 SKILL `toolsmith-visualization`（`~/.agents/skills/toolsmith-visualization`，沉淀 4 方式/2 通道/主题 token/下钻结论，均已在 Obsidian 笔记 `ToolSmith可视化能力与4种画图方式.md` 记录）。
- 示例成品（真实数据）：`evals/iteration-16/chart-examples/` 下 3 份 HTML + 渲染 PNG，用注入方式生成（模板代码不动、只换 `CHART` 数据）：
  - `harmoni6-evidence-timeline.html/.png` —— HARMONi-6 4 来源→2 状态（PFS 核心分析 2025-10 披露、OS 核心分析 2026-05 披露）+ 研究启动里程碑；PFS 11.1 vs 6.9 月（HR 0.60）、OS 27.9 vs 23.7 月（HR 0.66），披露时间取自 refs.json。
  - `harmoni6-pfs-bar.html/.png` —— HARMONi-6 中位 PFS 按治疗组（11.1 vs 6.9 月 + 95%CI）。注明 HARMONi-6 未报告 ORR，以中位 PFS 单值演示柱状模板。
  - `mazdutide-weight-line.html/.png` —— 折线模板演示：HARMONi-6 无时间维重复测量终点，改用真实 obesity fixture 的马扎度肽 2b 期数据（4mg/6mg/安慰剂，W32/W48 体重变化 %：-10.09/-12.55/+0.45 → -11.00/-14.01/+0.30），已在副标题注明。
  - 校验：JS 语法 OK；headless Chrome 渲染 PNG（38/29/29KB）；DOM 校验关键数值（11.1/6.9、27.9/23.7、-10.09/-12.55/-14.01/+0.45/+0.30）全部注入成功。

## Confirmed decisions

- Users include medical intelligence, clinical development, and BD/investment teams; all receive the same report granularity.
- Version 1 compares only selected records and performs no external retrieval.
- The backend resolves selected records from the POC Elasticsearch environment and `np_clinical`, then sends `source_title`, `source_url`, `source_paper_release_time_str`, and `source_full_text` to the Agent. Runtime correlation IDs remain outside the Agent request and report.
- The frontend/backend enforce a conservative real-time token budget.
- The primary analysis object is the underlying trial. Multiple disclosures from one trial are source nodes that form a longitudinal evidence chain; repeated cutoffs and analyses are deduplicated.
- Different trials receive a comparison-first, domain-aligned cross-trial report: efficacy, safety, PK/PD, and PRO are aligned across trials so the user can judge which treatment is better or worse, with explicit comparability/evidence-strength labels and compact per-trial context; no pooling or fabricated head-to-head proof. Trial narratives are supporting context, not the primary structure. Synced into `system-prompts/multi-clinical-result-comparison-v0.5.md` (opening, required workflow step 8, and “Mixed or different-trial inputs”).
- Every material number and source-dependent conclusion in the report carries an internal citation token for frontend rendering; user-facing output shows numeric superscripts. Citation metadata is a separate strict JSON artifact, not part of the report body, and each ref includes `title`, `link`, and `paper_release_time_str`.
- Trial-level reports integrate design, population, regimen, primary and key secondary endpoints, response/durability when reported, subgroups, safety, evidence maturity, and information gaps.
- The finished report must not expose technical correlation keys, database/index names, retrieval traces, internal field names, or implementation terms such as `result_id`, `doc_id`, ES/Elasticsearch, `np_result`, or `source_full_text`.
- Visible labels use a source-supported study short name or name for different studies. Multiple disclosures from one study add a data cutoff/disclosure date or, when unavailable, follow-up plus endpoint/analysis scope. Generic labels such as “材料 1” are last-resort fallbacks; “证据 A/B/C” are not used when a readable source-supported label exists.
- Every cross-trial or mixed report includes a research-key-information alignment table and an experimental-arm endpoint table.
- The frontend/backend enforce a conservative real-time token budget.
- Within-trial controls and comparative effects remain tied to their original randomized comparison and are never converted into cross-trial claims.
- Same-trial reports begin with an evidence relationship overview that separately classifies disclosure form and analysis stage/scope, then explains duplicate/update/subgroup/final/interim relationships before endpoint evolution.
- Cross-trial reports begin with a core-endpoint snapshot per clinical-question cluster. The snapshot always includes an exact-value table; compatible ORR-like endpoints may additionally use a valid Mermaid bar chart, while weight-change line charts require the same explicit time-point grid across plotted series. Missing values, incompatible definitions, or unexpressible time structures trigger a table fallback. Charts are descriptive only: no interpolation, pooling, ranking, or head-to-head inference.
- Cross-trial reports use one global marker namespace in input order and one shared separate citation JSON artifact for the complete response. Markers do not restart at each trial boundary. Separate independently requested reports may use separate local namespaces.
- The citation renderer supports multiple trial sections, accepts a separate citation JSON object, validates marker/key parity, and makes only the numeric superscript clickable. Generic Markdown autolinking must not receive the citation JSON.

## Validation completed

- Tool Smith `validate_skill_md` accepted the Skill name and description.
- Ran the Skill locally against the condition-based fixture `np-clinical-indications-516-517-phase-featured-false.json`: generated `evals/iteration-14/condition-example/report.md` (4-trial mixed input: ESSENCE, MAESTRO-NASH, MAESTRO-NAFLD-1/OLE, SYNCHRONIZE-MASLD) and `report.refs.json`. Per user feedback the report was restructured to be comparison-first and domain-aligned (efficacy, safety, PK/PD, PRO) rather than trial-by-trial narratives; the Skill routing, `cross-trial-comparison.md`, `cross-trial-report.md`, and SKILL step 6 were updated accordingly. Marker/key parity 10/10, renderer tests 6/6, contract validation `v0.5_contract_ok`.
- The upload archive contains the expected root directory and nine Skill files.
- PWS heterogeneous cross-trial/mixed case: passed after removing cross-cluster rankings.
- HARMONi-6 same-trial evolution case: passed chronology and duplicate-disclosure checks.
- Adversarial/incomplete case: passed prompt-injection, missing-data, and no-soft-ranking checks.

## Iteration 13 HARMONi-6 v0.5 regression report

- Generated `evals/iteration-13/harmoni6/report.md` from the four selected HARMONi-6 source objects using the v0.5 prompt, Skill, required references, and unified evidence template.
- Consolidated the disclosures into one trial narrative with one PFS core state and one 2026-02-27 OS core state; repeated PFS and OS analyses are treated as duplicate or complementary reporting rather than independent validation.
- Preserved source-supplied proper names, retained OS as a first planned/interim analysis, and traced material numbers and source-dependent conclusions with `{{ref_1}}` through `{{ref_4}}`.
- Verification covers inline-marker/JSON key parity, strict separate JSON parsing, exact fixture title/link/release-time parity, unresolved placeholders, prohibited internal fields, and absence of citation metadata from the report body.
- The project root has no Git metadata or Docker configuration, so commit, push, image build, and registry push are not applicable.

## Current revision

- Reviewer feedback identified that the prior example lacked a clear endpoint alignment surface.
- v0.2 replaces default pairwise comparability matrices with a row-oriented experimental-arm endpoint table.
- Experimental-arm observations and within-study control/effect estimates are now separate fields; neither may be inferred from the other.

## v0.3 revision

- A reviewed therapeutic-area landscape article showed that users need more than study-by-study extraction: they need baseline comparability, endpoint-family scanning, complete-response or threshold outcomes, placebo/reference behavior, and a bounded development interpretation.
- v0.3 adds these as reusable output structures without importing the article's CSU facts or conclusions.

## v0.3 to C revision

- Changed the output boundary for the to C report: technical identifiers, ES/database retrieval details, internal field names, runtime terms, and implementation traces are prohibited in final Markdown.
- Removed technical identifier columns and references from all three report templates while retaining readable evidence labels for user-facing comparison.
- Added the to C evidence relationship overview and core-endpoint chart modules to the v0.3 prompt, Skill references, and report templates.
- The final report is now a single consumer-facing evidence synthesis. Internal relationship classification still distinguishes evidence evolution from endpoint alignment, but the report no longer exposes separate same-trial, cross-trial, or mixed report paths.
- The unified runtime template is `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`. It organizes the visible output by core findings, evidence relationships, time course, endpoints, comparability, maturity, and information gaps.
- The chart contract was tightened for Tool Smith Markdown rendering: Mermaid is conditional, uses quoted labels and numeric-only arrays, and is omitted entirely when any value is missing or the time-point structure cannot be represented without interpolation. Every chart is accompanied by an exact-value table and a comparability note.
- The upload archive was regenerated after the updated Skill, reference rules, templates, and system prompt passed validation.

## v0.4 direction reset: trial-level synthesis

- Reframed the primary analysis object from disclosure-to-disclosure comparison to the underlying clinical trial.
- Multiple disclosures from one trial are now source nodes. The runtime must consolidate repeated cutoffs and analyses into one evidence state, preserve genuinely new endpoint/follow-up states, and explain the whole trial across design, efficacy, safety, maturity, and information gaps.
- Added `references/citation-and-ref.md`: stable presentation labels `[Ref n]` are assigned per selected source, every material number and source-dependent conclusion requires an adjacent Ref, and the final `来源索引` maps all selected sources to their contributions.
- Replaced the unified report template with a trial-level structure: clinical question, design, evidence-state timeline, integrated efficacy chain, safety chain, maturity/contradictions/gaps, whole-trial interpretation, and source index.
- Retained limited different-trial alignment only after each trial receives a complete synthesis; no global ranking replaces the trial narrative.
- Updated the same-trial reference to treat disclosures as evidence nodes and states, and updated mode routing so same-trial synthesis is the default visible behavior.
- Added v0.4 system prompt and revised benchmark expectations for trial identity, state deduplication, chronology, inline Ref coverage, and complete-trial interpretation.

## v0.5 linked-source input revision

- Added `references/input-contract.md` documenting the POC configuration, `np_clinical` lookup, normalized Agent payload, absolute URL policy, and frontend superscript rendering.
- Added `evals/fetch-np-clinical-sources.mjs`, a read-only reference adapter that imports the POC config and requests `base.title`, `base.full_article_link`, `source_full_text`, plus `base.paper_title` for the observed title-shape fallback.
- Added `evals/fetch-np-clinical-by-condition.mjs`, which reproduces the requested indication/phase/evaluation/NCT/deletion/featured filter and writes a normalized 10-source example to `evals/fixtures/np-clinical-indications-516-517-phase-featured-false.json`. The query matched 12 records and returned 10 usable full-text sources.
- Pulled `NCT05840016` successfully: 4 HARMONi-6 disclosures with source text lengths 3294, 3587, 2936, and 3067 characters. The fixture preserves exact backend URLs and contains no internal record IDs.
- Updated the v0.5 prompt, Skill, extraction rules, template, README, fixtures, and renderer to use `source_title/source_url/source_paper_release_time_str/source_full_text`, internal `{{ref_n}}` rendering tokens, and a separate strict citation JSON artifact.
- The v0.5 HARMONi-6 fixture preserves four backend-supplied titles and exact URLs, including the ESMO query string. It contains no runtime result IDs.
- Updated the PWS fixture with five read-only `np_clinical` title/URL/release-time pairs. Updated the synthetic adversarial fixture to the same four-field shape with intentionally empty links and release times rather than invented metadata.
- Added `runtime/citation-renderer.mjs` and `test/citation-renderer.test.mjs`: parse the separate citation JSON, enforce marker/key parity, preserve release-time metadata, and safely render valid HTTP(S) links as numeric superscripts with escaped attributes.
- Added explicit cross-trial rules: marker numbering is global for one mixed response and the separate citation JSON is shared; numbering resets only for separately requested reports. A cross-trial comparison claim must cite the source markers for both trials.
- Added the standalone example citation artifact `evals/iteration-13/harmoni6/report.refs.json`; the Markdown report no longer contains a citation section.
- Updated the HARMONi-6 example evidence scope to state `2 份期刊摘要、2 份会议摘要`; the report no longer explains `{{ref_n}}` in visible prose.
- Citation output uses no JSON. The final section is a strict two-line-per-source numbered list: `n. exact title` followed by three spaces and the exact URL.
- Runtime test suite passes 6/6; `node evals/validate-v05-contract.mjs` returns `v0.5_contract_ok`.
- Rebuilt and extracted `dist/multi-clinical-result-comparison-v0.5.zip` with the correct Skill `references/` and `templates/` directory structure; archive contains 13 files.
- Tool Smith cloud Benchmark and actual frontend superscript rendering remain unavailable in this workspace and were not run.
- No Git metadata or Docker configuration is present at the project root; commit, push, image build, and registry push are inapplicable. The POC repository remains dirty with unrelated pre-existing work and was not modified.

## v0.4 verification status

- Static contract review completed for prompt, Skill, support references, template, README, and eval definitions.
- Local v0.4 execution completed against `evals/fixtures/harmoni6-selected-results.json` using the Skill and system prompt: [first run](evals/iteration-12/harmoni6/report.md) and [corrected rerun](evals/iteration-12/harmoni6/report-v2.md).
- The first run exposed a provenance bug: the model invented an unsupported Chinese translation for the source-only drug name `ivonescimab`. Added an explicit proper-name fidelity rule to the system prompt, Skill, and extraction reference: preserve source spelling unless the source itself supplies a Chinese equivalent.
- Corrected rerun passed the trial-level checks: one HARMONi-6 narrative, one PFS state, one OS state, duplicate-source handling, chronology, all four Refs in the source index, inline numeric citations, no internal identifiers, and no unresolved placeholders. It retained `ivonescimab`, `tislelizumab`, `paclitaxel`, and `carboplatin` exactly as supplied.
- `evals/evals.json` now includes the proper-name fidelity assertion. Rebuilt `dist/multi-clinical-result-comparison-v0.4.zip` after the Skill change.
- No Git metadata or Docker configuration is present at the project root; commit, push, image build, and registry push remain inapplicable.

- Regenerated `evals/iteration-10/harmoni6/unified/report.md` from the current v0.3 Skill, system prompt, unified template, and required reference rules using only the four selected HARMONi-6 result texts.
- Replaced generic letter labels with stable source-supported disclosure labels based on HARMONi-6, explicit data cutoff where available, and PFS/OS/safety or analysis scope.
- Deduplicated the four disclosures into one PFS core analysis state and one 2026-02-27 OS core analysis state while preserving disclosure-specific PD-L1 subgroup, baseline anatomy, testing procedure, event-count, and safety details.
- Preserved uncertainty around the undated first planned PFS disclosure: its repeated overall PFS values were deduplicated, but no chronology or shared data cutoff was inferred.
- Kept OS as a prespecified interim/first planned analysis rather than a final analysis, including the 204-event trigger versus the approximately 225-event plan and the non-estimable upper confidence limits.
- No chart was emitted because PFS and OS are incompatible endpoint/time structures and plotting repeated disclosures would double-count the same analyses.
- Manual fidelity review confirmed all four selected disclosures are represented and key PFS, OS, subgroup, event-count, denominator, and safety values match the supplied texts.
- The report contains no generic “证据 A/B/C” labels, internal correlation keys, implementation/storage terminology, template placeholders, or Mermaid blocks.
- Current project state indicates no Git metadata or Docker configuration at the project root, so no commit, push, image build, or registry push was applicable.

## Iteration 10 PWS unified report

- Regenerated `evals/iteration-10/pws/unified/report.md` from the current v0.3 Skill, system prompt, unified template, and required reference rules using only the five selected PWS result texts.
- Replaced generic letter labels with stable source-supported labels: C601/C602 disclosures are distinguished by follow-up and analysis scope; independent studies use registry identifiers or a source-supported descriptive study name.
- Kept body composition, infant growth/development, eating/behavior, and long-term glycemic safety as separate clinical questions within one report. C601/C602 body-composition and glycemic disclosures are treated as complementary analyses, not independent confirmation.
- No chart was emitted because no clinical-question cluster had compatible complete numeric series. Exact-value snapshot tables, study alignment, baseline comparability, endpoint alignment, endpoint-family maturity, safety interpretation, and information gaps were retained.
- Manual fidelity review confirmed all five selected items are represented; key values match the supplied texts; the source's week-64 versus 3-year discrepancy, week-156 HbA1c wording discrepancy, adult LMI formatting anomaly, and unresolved percentage denominators remain explicitly bounded.
- The output contains no generic “证据 A/B/C” labels, internal correlation keys, implementation/storage terminology, or Mermaid blocks.
- No Git metadata or Docker configuration was present at the project root, so no commit, push, image build, or registry push was applicable.

## Iteration 9 unified report

- Replaced visible mode-specific report routing with one runtime template: `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`.
- Internal relationship detection remains available for deduplication, chronology, endpoint alignment, and comparability, but the final report is organized as one evidence synthesis around core findings, evidence relationships, time course, endpoints, comparability, maturity, and information gaps.
- Regenerated unified PWS and HARMONi-6 examples under `evals/iteration-9/`; both passed scans for internal identifiers, implementation terminology, forbidden path labels, and invalid Mermaid output.

## Iteration 8 examples

- Regenerated `evals/iteration-8/pws/with-skill/report.md` from the current v0.3 assets. It separates body composition, development, hyperphagia/behavior, and long-term glycemic safety; all chart candidates correctly fell back to exact-value tables because the supplied evidence was incomplete or incompatible.
- Regenerated `evals/iteration-8/harmoni6/with-skill/report.md` from the current v0.3 assets. It groups duplicate PFS and OS disclosures into two analysis states, orders them by cutoff/follow-up, and preserves the interim-not-final OS boundary.
- Both reports passed scans for internal identifiers, retrieval/storage terminology, and invalid Mermaid output. These are independent local generations from the fixtures, not production Tool Smith Benchmark runs.

- Queried `np_result_3` directly with the selected 16 `doc_id` values and preserved `deleted`/`is_delete` exclusions.
- Retrieved 17 non-empty `source_full_text` values; `38912654` contains Trial 1 and Trial 2, so 16 documents yield 17 result items.
- Added `evals/fixtures/obesity-results-es-source-full-text.json` and the reproducible fetcher `evals/fetch-obesity-es-fixture.mjs`.
- Added `evals/iteration-7/obesity-results-es-source-full-text-report.md`, which separates adult weight management, T2D/prediabetes, pediatric obesity, and OSA questions before limited vertical alignment.
- Marked `35658024`/`39536238` as the same SURMOUNT-1 trial and `38912654` Study 1/Study 2 as two trials in one disclosure.
