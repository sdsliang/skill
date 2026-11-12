# PROJECT_STATE — conference-result-triage

## v0.7（2026-11-12）：15 → 10 的编辑收敛、`why` 变判断、上市公司字段

三处改动都来自「45 张卡交出去之后读者会问什么」，而不是脚本能算出来的东西。

| 改动 | 为什么 | 落成什么 |
|---|---|---|
| **两段收敛**：机器短名单 15/45 → **交付清单 10/30** | 15 条是防止池子变倾倒场的天花板，但它不是阅读上限；一份 15 条的清单读不完，10 条的会 | `check_cards.py` `PER_BUCKET_CAP=10` / `TOTAL_CAP=30`；`work/shortlist.json`（≤15）与 `work/plan.json`（≤10）分开 |
| **联网终选（Step 5B）** | 只从会议库挑，永远不知道会议室里真正被讨论的是哪一条，也不知道研发公司是上市公司、披露当天股价怎么走 | 每桶 ≥6 次 `web_search`，证据落 `work/web/<bucket>.jsonl`；允许 `promoted:"web"` 把池外记录提上来（必须在 `rows.json` 里） |
| **`why` 从标签变判断** | 「报告了主要终点读数」等于没写；读者要的是「这项研究值什么」 | `MIN_WHY_CHARS=60`、2–4 句、禁止与 `summary` 互相包含前 20 字 |
| **`listed_company`** | 这类读数是股价的重定价日；查不到就该空着，而不是让读者猜 | 每张卡必有该键，非 null 时 `name/ticker/exchange/source_url` 齐全且 URL 可解析 |

**实探到的坑**：平台的 `web_search`（模型侧可能显示成 `web.run`）有**双重开关** —— 项目 `capabilities_config.web=true`
**且** 回合 `enable_web=true`。只开前者时模型看到的工具表里根本没有检索工具，它会一路"没有联网工具"地编下去；
`debug-history.json` 里 `web_search` 只出现在 prompt 与回复里、零条工具定义。`settings.WEB_SEARCH_API_KEY` 为空时是
**返回一条 message**（`WEB_SEARCH_NOT_CONFIGURED_MESSAGE`），不是隐藏工具——两种现象要分开报。

**事实层**：19 → **23 条 fail 项 + 1 warn**。新增 `A-P5-why-depth`（短 / 复写 `summary` 两个分支）·
`A-F5-listed-company` · `A-F6-promotion-traceable` · `A-W1-web-evidence`，各配 mutation；NEG 从 2 条加到 4 条
（合法的桶间重排、热点标题、`why` 踩 60 字下限、带交易所来源的港股公司）。`EVALUATOR_REVISION = 2026-11-12-r2`。
基线 `facts 23/23`，`mutations.py` 输出 `coverage: 23/23 fail items have a mutation; 4 negative controls green`。

**端到端（2026-11-12）**：v0.7 原地发布（prompt v1.0 in-place / skill v0.3.0 in-place，`STATUS: in sync`）后跑了两轮。

| 轮次 | 结果 | 暴露的缺陷 |
|---|---|---|
| `cards-e2e5` `20261112-105154` | **零交付**（1097 行取数 + 592 条判读都完成，`output/watchlist.json` 不存在） | `web_fetch` 打开 amgen.com 失败后，模型把「一个 IR 页打不开」读成「检索整体不可用」，写下"暂未交付最终 JSON"并结束回合。**文档只写了"要联网核实"，没写"核实不了怎么办"** → 三处补「降级不中止」条款 |
| `cards-e2e6` `20261112-111250` | **`facts 23/23 -> PASS`**；28 卡（10/10/8）；`work/web/*.jsonl` 26 行 / 18 行带 URL；`listed_company` 26/28；`why` 132–160 字 | `A-W1` 原要求「每条检索记录都带 URL」，把「查了但没结果」的如实记录判成漏证（先假红一次）→ 改为「总行数 ≥6 ∧ 带 URL 行 ≥6 ∧ 无 URL 行必须写 note」，并补 `m_web_no_urls` mutation + NEG「零结果但已注明」 |

`e2e6` 未出现 `promoted` 卡片：外部讨论没有改变入选集，模型把 CS2009 的外部更新写进 `coverage_notes`（"会议库只有初步小队列，未用外部数字补写卡片"）。
NEG 从 4 条加到 **6 条**（新增「检索零结果但已注明」「联网不可用但已声明」）。

**未做**：`featured` 白名单仍是 dev ticket；`stock` 数据源仍未接通；`make_watchlist.py` 尚未同步 `listed_company` / `promoted`，`plan.json` 的 `editorial_policy.max_cards_per_bucket` 仍是 15。

## v0.6.1（2026-11-12）：原地重跑两次，facts 19/19 全绿

v0.6 发布后原地跑全量（592 候选 / 40 批），**第一次 `facts 16/19`，暴露的三个面全部修掉后第二次 `19/19`**。

| 失败项 | 现象 | 性质 |
|---|---|---|
| `A-D4` | `73 lba rows … 19 dropped` | **审计脚本 bug**：比对键用 `extra_esid`（无 `nr_`），池内键是 `_id`（带 `nr_`）→ 归一后 73/73 |
| `A-D2` | `0 sliced calls` | 分片在 `task` 子代理里跑，父回合只看到 id-only 调用；v0.5 依赖的 `slice_counts.json` 这次没写 |
| `A-H1` | `0 notes` | 模型把边界写进 `coverage.boundary`；而 `coverage_notes` **在 SKILL.md 里从没定义过**（v0.5 是运气通过） |

修法（一律修面，不修阈值）：

1. `pull_results.py` 让 `rows.json` 自带 `sources`（每 dump 名 + 行数）——分片证据随数据走，不再依赖调用方记得写账本。
2. `check.py` 分片项改三级回退：`work/slices/slice_*.json` → `rows.json.sources` → 父回合调用；并要求切片 id 与 `rows.json` id **双向相等**。
3. 两条诚实声明升级成闸门：`check_cards.py` 要求顶层 `coverage_notes`（措辞不查，只查事实），同时把 schema 补进 SKILL.md / 系统提示词 / `Deliverable schema`——先有定义才有闸门。`evals/test_check_cards.py` 加 3 例（缺字段 / 少一条 / 合法改写必须过）。

**交付基线**：prompt `conference-result-triage-v0.6.md`（v1.0 原地更新，sha `4a65bf34c51a`）、skill v0.3.0 / dist 17 项、`status: in sync`。
**run 2 `cards-e2e4`**：1520 s、55 次工具调用、45 卡（15/15/15）、17 个不同分数、`facts 19/19 warn 1/1 -> PASS`、VOLGA / KRASCENDO-1 / CLARITY-Gastric01 全部进榜。
**未做**：45 张卡的人工可读性复核；`featured` 白名单（`manual` 恒 `null`）。

**复核页（2026-11-12）**：把 run 2 的交付物渲染成单文件 HTML 供人工读，
`dist/review/esmo2026-watchlist.html`，生成器 `dist/review/build_review_page.py`（只读 `output/watchlist.json`，
不改判读结果）。**只渲染 45 条 card 记录本身**：桶 / 分数 / `title` / `summary` / `why` / `key_numbers` /
`evidence` 以及卡片自带的 `tag`、`phase`、`presentation`、`drug`-`target`-`indication`、`data_type`。
不做漏斗、不做分布图、不重算覆盖率、不抄 `coverage_notes` 或 `verification_points`——
用户口径：**“我只想要推荐卡片，用输出的那 45 个 JSON 组织就行，不需要额外补充字段”**（第一版把派生统计和图都画上了，被否）。

## v0.6（2026-11-11）：排除规则的静默删除 + 事实层首次落地

**被外部热度对照逼出来的真缺陷**：`excluded_reason()` 用 `evidence_source` 判断研究类型，
而平台没有独立分期列——`evidence_source` 就是分期来源，**73 条 ESMO 2026 LBA 里有 16 条该字段填的是研究设计「前瞻性研究」**。
把它放进 `NON_TRIAL_SOURCES` 黑名单的后果是 VOLGA（LBA2）/ KRASCENDO-1（LBA5）/ CLARITY-Gastric01（LBA7）
三场 Presidential 整类消失，而交付物仍报 `coverage: 1097/1097`（分子分母都取自同一份已取数据，能自证一致，证明不了完整）。

| | 修前 | 修后 |
|---|---:|---:|
| 候选 | 551 | **592** |
| pivotal / early / failed | 292 / 200 / 59 | **306 / 200 / 86** |
| excluded 中 `前瞻性研究` | 252 | **0** |

修法：黑名单只留 回顾性/真实世界/汇总分析/Not Applicable/其他；分期缺失的行交 `bucket_of`，`lba` 为真进 pivotal，
**期别字段不改不猜**，卡片照实写「未声明」。`--top/--limit-per-bucket` 降级为**试跑专用**（ESMO 2026 设 60 会切掉 pivotal 第 64 名 SAFFRON）。

**质量层从布尔门升级成标量**：新建 `evals/fact-check/{check.py,facts.json,mutations.py}`（移植 `clinical-result-comparison` 的范式）：
`EVALUATOR_REVISION = 2026-11-11-r1`，**20 项 = 19 fail + 1 warn**，**19 个 mutation + 2 个合法变体负对照**全部有牙（`mutations.py` exit 0）。
对真实跑批 `cards-e2e2`（41 卡）实测 **18/19**，唯一失败项 `A-D4-lba-not-dropped` 报的就是上面那个缺陷
（`73 lba rows in the corpus, 37 in the pool, 50 dropped, phase-as-design exclusions=['前瞻性研究']`）。

**外部热度对照**：同一份 X 检索（23 帖 / 112 提及），12 个 Presidential LBA 命中 v0.2 **0/12** → v0.5 **7/12** → v0.6 池内 **12/12**。
5 个漏项分三层：上限（SAFFRON，`--top 60` 切掉）/ 分组（HERON-Lung01，keep 86 分 vs 榜尾 87 分）/ 分类（三场 Presidential，即上述缺陷）。
详见 `dist/v06/heat-check-v06.md`、`evals/EVALUATION_RESULTS.md`。

**未做**：v0.6 尚未发布 TS、尚未重跑 E2E（12/12 是**池内**结论，不是榜单结论；目标 `facts 19/19`）。

## 平台内实跑验证（2026-11-11，v0.4）

**数据层已在 ToolSmith 真跑打通**（标签 `slice-e2e`，模型 `GPT 6.1 Sol`，606 s，31 次工具调用，9 次落盘 18.4 MB）：

```
rows=1097 lba=73 with_abstract_text=1097 -> /workspace/work/rows.json
coverage: 1097/1097 ids present
self-test: OK
candidates 551 / missing abstract 0
```

两条实测硬事实（写进 SKILL.md Step 1、系统提示词 step 2、pitfalls §21）：

| 事实 | 证据 |
|---|---|
| **工作区没有网络** | `172.17.26.74:30080` → `Network is unreachable`；公网 → `gaierror -3`；`env` 无 MCP 端点。脚本不能自己连数据服务 |
| **宽字段一次拉静默截断** | 32 字段 + `meeting_tags` 只回 **458/1097**，`ok: true` 无报错；id-only 回全 1097 |
| `selected_fields` 混入线上白名单外的名字 | `research_design.evaluation.text` / `base.abbreviation_label.text` → 整次调用 `INVALID_INPUT`，**一行都不回** |
| `featured` 取不到 | 不在白名单；`TEST_execute-sql` 不能绑项目（400） → `manual` 恒 `null`（三态，`check_cards` 拒绝改成 true/false） |

**取数四阶段**（平台版）：id-only 调用 → `plan_slices.py --size 150` → 每片 `esids` 调用 → `pull_results.py --from-tool-results --expect-ids` 合并校验。落盘路径 `/workspace/tool_results/<tool>/<call-id>.jsonl`，**turn 结束时清除**。

TS 侧：project `d1c193d7809d4c04ba5423942523f91c`，prompt family `3fa0f27ef41648c0a968bb7b9a76adfb`，skill family `69db628c867b4bf2acf8477789562c96` / skill_id `230463cbc03d4fe5ba0e2e8964fe91dd`（v0.3.0，17 entries），`toolsmith-publish status` → **in sync**。

## 现状（2026-11-11，v0.3 改为平台内执行）

**状态**：v0.3 完成，**目标形态是 ToolSmith 平台内运行**（不是本地脚本跑批）：用户在 TS 会话里给一个会议名，agent 拉全量结果 → 机械筛 → 逐批判读 → 输出 `/workspace/output/watchlist.json` 卡片清单 → `present_artifact`。仍未发布 TS（用户要求发布前须单独确认）。

**目录已对齐 `clinical-result-comparison` 的形态**：

```
skill/conference-result-triage/{SKILL.md, references/, templates/, scripts/}
system-prompts/conference-result-triage-v0.4.md
tools/pack-dist.py     -> dist/conference-result-triage-v0.4.zip (17 entries)
```

平台把 zip 解到 `/workspace/skills/conference-result-triage/`，所以 SKILL.md 里的脚本一律按 `/workspace/skills/conference-result-triage/scripts/...` 调用。

## v0.3 改了什么（相对 v0.2）

| 项 | v0.2 | v0.3 |
|---|---|---|
| 取数 | 本地直连 `/api/tools/debug`，缺 `lba` | `scripts/pull_results.py` 走 MCP，`lba` 在 `DEFAULT_FIELDS` |
| 大响应 | 一次取全字段，静默只回 ~500 行 | 两阶段：先 id 全量，再 `esids` 切片 120/次（1097/1097） |
| LBA 排序 | 纯 `LBA<n>` rank 3，被压到普通口头下 | `Late-breaking Oral: 0`，高于 `Oral: 1` |
| LBA 分桶 | 「只在会议库 ⇒ 只进 early」把 LBA 一并误伤 | LBA 行豁免，可进 pivotal/failed |
| 摘要号 | 平台内**拿不到**（无 `abstract_id` 列、无会议库工具） | `abstract_id` 恒 `null`；报告形式只有 `lba`（51/551 有层级） |
| 报告形式 | 只有 `lba`（进池 51/551） | `featured` 是**人工/AI 生产**标记（`是` 100/100 = `source=np_result_conf`），**不是头条**，只做卡片生产方式标注 |
| 交付物 | `watchlist.md` + 两个 csv | `/workspace/output/watchlist.json` 卡片清单（固定路径） |
| 闸门 | 无 | `check_cards.py` fail-closed（exit 3） |
| 候选池 | 532 | **551**（early 200 / pivotal 292 / failed 59），37 批 |

NATALEE / NSABP B-42 / INTerpath-001 / DASL-HiCaP / LOMAC / CAPItello-281 / DUO-E / CheckMate 8HW / DeLLphi-305 等 LBA 已全部进 pivotal 桶。

## 交付 schema

```json
{"conference":"ESMO 2026","count":30,"cards":[
 {"esid":"...","abstract_id":"LBA3","lba":true,"bucket":"pivotal","tag":"LBA",
  "title":"...","summary":"...","why":"...","drug":"","target":"","indication":"",
  "phase":"Phase III","presentation":"Late-breaking Oral","stock":null}]}
```

`esid` = 结果记录 id；`stock` 只在给了 `--quotes` 同日行情时非空，否则 `null`（不用其它日期顶替）。

## 是什么

会议临床结果推荐榜 skill：输入一个会议标识（`meeting_tags`，如 `ESMO 2026`），输出三桶榜单
（早期机会 / 重磅 II/III / 失败）+ 排除档 + 待人工核实清单。

与两个既有 skill 的边界：

| skill | 分析对象 | 输出 |
|---|---|---|
| `conference-clinical-interpretation` | 一个会议的**统计概览** | 会议整体解读报告 + 图表 |
| `clinical-result-comparison` | 2 个以上**已选定**的结果 | 药物间疗效/安全性对比 |
| **本 skill** | 一个会议的**全部候选** | 值得看的 30 条 + 为什么 |

## 关键设计决策（含理由，勿回退）

1. **机器评分被显式废弃**。实测规则打分产生假精度：安全性行会压过疗效行（`Grade≥3 TEAE 44.6%` 被当疗效）、`PR = 3 subjects` 被读成 3% 缓解率、约一半 `study_results` 没有 p/HR。现 `triage.py` 只做机械操作 + 附**非权威**提示。
2. **n 不作入榜门槛**（用户 2026-10-23 决定）。只做展示与并列次级排序。
3. **真实世界/回顾性/前瞻性非注册研究不进桶**（用户决定）。单独计入 `excluded`，在交付物里明示条数。
4. **失败桶由 `evaluation ∈ {不佳, 终止}` 或复核阶段证实的「主要终点未达/未显著/提前终止」驱动**，p/HR 只作佐证。
5. **试验期别取 `evidence_source`**，不是 `clinical_stage_new`（后者是疾病分期）。
6. **`data_type` 四分类**（首次 / 更新 / 亚组 / 未判定）为强制列。理由：会议摘要大量是长期随访与 post-hoc 分析，不标会把 7 年 OS 更新写成新药突破。未命中一律 `未判定`，不猜。
7. **批次 15 条/片**（v0.1 为 25）。硬约束来自工具单文件读取上限（~50 KB）与"Results 全文不截断"的叠加要求：36 片实测 max 40,804 B / avg 35,964 B。
8. **索引用显式顺序 `i`**，不用 esid 下标。此前一次 6 路并行复核因为 esid 与顺序错位，合并结果不可用。
9. **两条数据源是并联关系，不是主备**（v0.2 新增）。`drugClinicalResult`（结构化结果表）只有 646 条 ESMO 2026 记录；`medicalMeeting`（会议库）有 5810 条、可用 4103 条。只走前者会漏掉 3638 篇没进结果库的摘要，其中 141 篇是口头档、358 篇带药名+数字+期别。
10. **会议库独有记录硬性只进 early 桶**（v0.2 新增，在 `build_pools` 层强制）。因为它们的期别是从正文正则出来的，撑不起"重磅"或"失败"两种断言。ESMO 2026：补录 305 条 → 68 条进 early，235 条被这条闸门挡在桶外。
11. **平台内报告形式只剩 `lba`**（v0.3）。没有摘要号，`featured` 是人工/AI 生产标记（用户确认 + SQL 100/100 验证），只做生产方式标注。551 候选里 51 条有 `lba`，其余 `Unknown` 是诚实结果。用法：排序权重 + 每条必须标注，**绝不当准入门槛**。详见 `references/pitfalls.md` §20。
12. **ORR 门槛按人群难度分档**（v0.2 新增）：一线/非耐药 ≥40%，后线≥2 线/明确耐药 ≥25%，**降档必须在理由里写明人群**。用例：9MW2821 在 TOP1i-ADC 耐药 TNBC 里 30.0%。
13. **机器排序 ≠ 推荐排序**。池子按 `(presentation_rank, -n)` 排只为决定"读的顺序"；定榜顺序由读完 keep 的人给。实证：7 条专家选择在机器序里排 2/19/27/72/101，两条壁报被 n 大的平庸研究压到 72、101 名。`make_watchlist.py` 只按给定顺序渲染，不做排序。

## 已完成

- `scripts/triage.py`（零依赖）：去重 / 排除 / 三桶 / `data_type` / 机器信号 / 批次输出 / `--self-test` / `--require-detail` 两段式。
- `scripts/meeting_pull.py`：最小 MCP streamable-HTTP 客户端，拉 `medicalMeeting` 全量（290 页 / 4m04s / 5810 条），支持 `--conference -` 跨会议检索（用于同资产历史）。
- `scripts/meeting_join.py`：归一化标题归并（646/646 零漏配）+ 会议库独有记录保守补录（305 条，49 oral 档）+ `enrolled_from_text` 补 n（257/305）。
- `scripts/history_for.py`：同资产历次会议读数对照（只列摘要印出的数字，不做判断）。
- `scripts/make_watchlist.py`：渲染 `judgements.csv` / `watchlist.csv`，机器桶与复核桶并排。
- `references/` 四份（data-contract 含 §7 会议库契约 / screening-rules / review-protocol / pitfalls 17 条）。
- `templates/watchlist-report.md`、`system-prompts/conference-result-triage-v0.1.md` + `v0.2.md`、`SKILL.md`、`README.md`。
- `evals/test_triage.py` + `evals/fixtures/mini_rows.json`（4 条固定样例）。
- **ESMO 2026 v0.2 实跑**：5810 会议记录 → 4103 可用 → 结构化 646 + 补录 305 = 951 → 候选 532 → 逐条判定 532 → keep 232 → 定榜 30。产物在 `dist/v02/`（判 532 / 榜 30 / 历史 185 条）。

## 验证记录

| 项 | v0.1 | v0.2 |
|---|---|---|
| `triage.py --self-test` | OK | OK |
| `evals/test_triage.py` | OK（4 组断言） | OK |
| 全部脚本 `ast.parse` | — | 5/5 OK |
| 候选池 | 467 | **532**（early 248 / pivotal 235 / failed 49） |
| 复核覆盖 | 467/467 | **532/532**，`i` 无缺口无重复 |
| evidence 逐字命中 | 400/467（86%） | **532/532（100%）** |
| `reason` 超 40 字 | — | 0 条 |
| 专家 7 条：在候选池 | 7/7 | 7/7 |
| 专家 7 条：判 keep | 3/7 | **5/7** |
| 专家 7 条：进定榜 30 | 1/30 | **5/30** |

**v0.2 首轮踩的坑（已修，记在 pitfalls §16）**：直接用 `pool.json` 切片导致 36 片 `condensed` 全为空，6 个子任务 4 个拒绝、2 个改用 `summary`，keep 率从 24% 掉到 2%。改成从 `review.jsonl` 的 batch item 拼 `Background + 完整 Results + DB summary`，并加落盘断言。

## 已知问题 / 待办

- [ ] **口径不一致 1 处**：`1015P` CM518D1 按"后线 25%"应 keep，模型判 weak 且理由未写人群。已列候补，未强行改判（规则与判定冲突时以原文为准，由人定夺）。
- [ ] `judgements.csv` 的 `key_numbers` 已做单位过滤（只留 % / 时间 / HR / p），但仍会混入 `60 years` 这类；`evidence` 才是权威字段。
- [ ] `data_type` 未判定 279/532，规则命中率仍是主要短板。
- [ ] `clean_label()` 残留噪声：`...; percentage`、`Patients who completed N cycles`。
- [ ] 机器重判后的桶分布明显偏移：机器 pivotal 235 条里 146 条被复核降到 early（单臂 II 期的"分期 = 确证级证据"误解）。若下游要按桶出数，需固定用的是机器桶还是复核桶。
- [ ] ToolSmith 发布（用户暂缓）：`system-prompts/conference-result-triage-v0.2.md` + `SKILL.md` 已备好；发布前须在 `~/.config/toolsmith/projects.json` 注册 family 并标 `owned: true`。

## Git

仓库根 `/home/xupeipeioo1/apps/skill`，分支 `feature/interactive-html-track`。
v0.1 提交 `ea90305`；v0.2 提交见 `git log`。
