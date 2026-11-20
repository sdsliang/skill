# 评测结果台账（conference-result-triage）

对齐 `clinical-result-comparison/evals/EVALUATION_RESULTS.md` 的习惯：每轮改动记一行「改了什么 → 哪个测量动了 → 结论」，不做无测量的声明。

评分口径：`facts_ok / facts_total`（fail 级事实项），不是布尔「跑完没」。布尔说不出「45 张好卡」和「45 张刚好过 schema 的卡」的区别。

---

## R1 — 把 fact-check 架到本技能上（2026-11-11）

**改了什么**：新建 `evals/fact-check/{check.py,facts.json,mutations.py}`，从 `clinical-result-comparison/evals/fact-check` 移植范式——逐条事实项 + 每个 fail 项配 mutation + 合法变体负对照。

**规模**：`EVALUATOR_REVISION = 2026-11-11-r1`；初始 19 项（17 fail + 2 warn）→ 现 20 项（19 fail + 1 warn）。

**测量**：`mutations.py` 在自造合法 fixture 上基线 PASS，17/17 mutation 全部翻红，2 个负对照仍绿。

**结论**：清单有牙。空 fixture 不能过，坏了会响。

---

## R2 — 对真实跑批打分（首次）：16/19

**对象**：`cards-e2e2`（`20261111-174917-cards-e2e2`，outcome `succeeded`，41 卡 = pivotal 15 / early 15 / failed 11，22 个不同分数）。

**首轮**：`facts 16/17` + 1/2 warn，三项不过：

| 项 | 首轮输出 | 判定 |
|---|---|---|
| `A-D2-sliced-pulls` | `0 sliced calls (max 0 ids), 1 unsliced` | **op 缺陷**：分片取数派给了 `task` 子代理，其 `execute` 里的工具调用不进父 turn 的 `debug-history` |
| `A-F4-numbers-traceable` | 4 个不可追溯数字（`40.0%` / `55.0%` / `47.5%` / `47.6%`） | **op 缺陷**：`40.0%` 与原文 `40.0 (19.1–63.9)` 是格式漂移，不是编造 |
| `A-H1-two-honest-claims` | reply 里 0/4 命中 | **op 面选错**：诚实声明写在 `watchlist.coverage_notes`（11 条），回复里只有摘要 |

**修法**（都是修表面，不是放宽闸门）：

1. `query_slicing` 先读 `work/slice_counts.json`：8 片、8 个互不相同的 dump、每片 `missing_ids=0`、最大片 150 → PASS；没有账本才回落去数 `esids`。
2. `numbers_traceable` 只要求数字出现在该 esid 的原文里，单位不作门（摘要把 `%` 放在表头、写 `12.9 (95% CI 10.4-16.3) months`）。语义问题（`47.5` 是 ORR 还是 TRAE）交给判读，抓不住就明说，不假装抓得住。
3. `A-H1` 改查 `watchlist.coverage_notes`，并从 warn 升为 **fail**（删掉 `coverage_notes` 的 mutation 会翻红）。

**复测**：`facts 18/19` + 1/1 warn，唯一失败是下面 R3 挖出来的真缺陷。

---

## R3 — 事实层挖出真缺陷：16 条 LBA 被当非试验证据静默删除

**现象**：新增 `A-D4-lba-not-dropped` 后对 `cards-e2e2` 跑：

```
73 lba rows in the corpus, 37 in the pool, 50 dropped
(e.g. ['24_37_p_8927e6332848b31a629ee1f38fd6d8e1_1', ...]), phase-as-design exclusions=['前瞻性研究']
```

**根因**：`excluded_reason()` 的 `NON_TRIAL_SOURCES` 含 `前瞻性研究`，理由是"非注册试验"。但平台没有独立分期列，`evidence_source` 就是分期来源，**73 条 ESMO 2026 LBA 里 16 条该字段填的是研究设计**（`前瞻性研究`）。于是 VOLGA（LBA2）、KRASCENDO-1（LBA5）、CLARITY-Gastric01（LBA7）三场 Presidential 整类消失，而交付物仍报 `coverage: 1097/1097`。

**修法**：黑名单只留回顾性 / 真实世界 / 汇总分析 / Not Applicable / 其他；分期缺失的行交 `bucket_of`，`lba` 为真进 pivotal，期别照实标"未声明"。回归断言进 `triage.py --self-test`（2 条），事实项进 `A-D4`（1 个 mutation）。

**测量**（对同一份 `rows.json` 本地重算）：

| | 修前 | 修后 |
|---|---:|---:|
| 候选 | 551 | **592** |
| pivotal | 292 | **306** |
| failed | 59 | **86** |
| excluded 中 `前瞻性研究` | 252 | **0** |

**结论**：覆盖率能自证一致而不能证明完整——分子分母同源。凡是"按值排除"的规则，都要拿会议自己的议程（LBA 名单）反查一遍。完整复盘见 `dist/v06/heat-check-v06.md`。

---

## R4 — 外部热度对照（v0.5 真实跑批）

同一份 X 检索（23 帖 / 112 提及），12 个 Presidential LBA 命中：**v0.2 0/12 → v0.5 7/12 → v0.6 池内 12/12**。

5 个漏项分三层，只有一层是错误：

- 上限：SAFFRON（pivotal 第 64 名，被 `--top 60` 切掉）→ 参数误入正式流程，已降级为试跑专用。
- 分组：HERON-Lung01（keep 86 分，榜尾 87 分）→ 15 条上限生效，不改。
- 分类：VOLGA / KRASCENDO-1 / CLARITY-Gastric01 → R3 的真缺陷。

**结论**：热度只能校验覆盖，不能参与排序（12 个 LBA 里 5 个低于 90 分）。

---

## R5 — v0.6 真实跑批（两次，第一次暴露三个面）

发布 v0.6 后原地重跑全量（592 候选 / 40 批），两次都跑完，第一次 `facts 16/19`，第二次 `19/19`。

**run 1 `cards-e2e3`（`20261112-090453`，1883 s，56 次工具调用，40 卡 15/14/11）**

| 失败项 | 输出现象 | 判定 |
|---|---|---|
| `A-D4-lba-not-dropped` | `73 lba rows … 19 dropped` | **op 的 bug**：比对键取 `extra_esid`（无 `nr_` 前缀），池内键是 `_id`（带前缀）。归一到 73/73 后转绿——这是 pitfalls 里记过的 `nr_` 陷阱在审计脚本里复发 |
| `A-D2-sliced-pulls` | `0 sliced calls` | 分片调用发生在 `task` 子代理内，父回合只看到 1 次 id-only 调用；v0.5 依赖的 `slice_counts.json` 账本这次没写 → 审计无面可读 |
| `A-H1-two-honest-claims` | `0 notes` | 模型把两条边界写进了 `coverage.boundary`，不是 `coverage_notes`；而 `coverage_notes` **在 SKILL.md 里从未被定义过**——v0.5 那次只是模型恰好这么写，`A-H1` 是运气通过 |

**三处修法（都修"面"，不修阈值）**

1. `pull_results.py` 让 `rows.json` 自带出处：`"sources": [{"dump": "slice_01.jsonl", "rows": 150}, …]`。数据文件自己证明自己被分过片，不再依赖调用方记得写账本——分片是唯一会静默丢数据的步骤，证据必须随数据走。
2. `check.py` 的分片项改成三级回退：`work/slices/slice_*.json`（切分本身）→ `rows.json.sources` → 父回合调用记录；并要求切片 id 集合与 `rows.json` 的 id 集合**双向相等**（漏了是丢数据，多了是伪造）。
3. 把两条诚实声明从"建议"升级成闸门：`check_cards.py` 要求顶层 `coverage_notes` 是字符串数组且语义上写到两条边界，措辞不查（`无 p 或 HR` / `未列p或HR` / `没给 p 值或 HR` 都算）。同时补上 SKILL.md 与系统提示词里的 schema——**先有定义，才有闸门**。

**run 2 `cards-e2e4`（`20261112-094222`，1520 s，55 次工具调用，45 卡 15/15/15）**

```
facts 19/19 warn 1/1 -> PASS
A-D2  8 slices (largest 150 ids, 1097 distinct), 10 dumps recorded, 0 missing
A-D4  73 lba rows in the corpus, 73 reach the pool, 0 dropped
A-C1  7/12 heat trials on the list
```

VOLGA / KRASCENDO-1 / CLARITY-Gastric01 三条都在榜上（pivotal 96 / 94 / …），`score_parts` 全部自洽，17 个不同分数。

**结论**：v0.6 的 19 项事实层全绿。两次跑批之间差异只来自"面"的补齐，事实规则一条没松——第一次的 16/19 里有 1 项是真缺陷（诚实声明无定义）、2 项是审计脚本与审计面自己的问题。

---

## 待测

- **v0.6 已发布并验证**；剩余项是人工复核（45 张卡的可读性、分数分布）与 `featured` 白名单（`manual` 恒 `null`）。
- 失败桶 vs 热度：阴性 query 两次 502，数据缺失，不给结论。

---

## R6 — v0.7 本地闸门（2026-11-12，未上平台）

**范围**：v0.7 的三条改动（交付清单 10/30、`why` 深度、`listed_company` + `promoted`）在脚本与事实层的行为。
**不做**：端到端跑批——v0.7 尚未发布，`cards-e2e5` 留到发布后。

| 闸门 | 命令 | 结果 |
|---|---|---|
| 分桶 / 切片 / 归一 | `python3 evals/test_triage.py` | OK（4 rows / 4 assertion groups） |
| 卡片闸门 | `python3 evals/test_check_cards.py` | **15 例全绿**（新增：`why` 太短、`why` 复写 `summary`、`listed_company` 缺键、假 ticker/假 URL、池外未标记、`promoted` 合法入榜 + 4 条 NEG 级合法变体） |
| 事实层 | `python3 evals/fact-check/mutations.py` | baseline `facts 23/23`；`23/23 fail items have a mutation; 4 negative controls green` |
| 打包 | `python3 tools/pack-dist.py` | `v0.7` 17 entries / 104494 B / sha256 `3f80acebc4b5a597` |

**判据说明**：`A-W1-web-evidence` 是 **fail** 级。理由与分片证据同一条——联网终选的全部产出是「检索到了什么」，
而平台 `/workspace/tool_results/` 回合结束即清空、回复里写"查过"无法复核。没有 `work/web/<bucket>.jsonl`
就等于这一步没有留下可查的痕迹，所以不给 SKIP 通道。

**已知风险**：`A-W1` 会把「做了检索但忘记落盘」判成失败，从而挡住交付。这是有意的：宁可一次跑批失败重跑，
也不要一份无法追溯来源的"热点"清单。

---

## R7 — v0.7 端到端（2026-11-12，`cards-e2e5` 失败 / `cards-e2e6` 通过）

### e2e5：零交付（暴露的是文档缺陷，不是数据缺陷）

`20261112-105154-cards-e2e5`，1097 行取数完成、592 条判读完成，然后 **`output/watchlist.json` 不存在**：
`web_search` 实际返回了 12 条来源（medthority / oncodaily / urotoday / esmo.org），随后
`web_fetch https://www.amgen.com/investors` 失败，模型写下"目前搜索无可用返回，公开网页抓取失败"并结束回合，
理由写着"暂未交付最终 JSON 清单"。

- 三层错误叠在一条链上：**一次 `web_fetch` 失败 = 检索整体不可用**、**可选增强 = 交付前置条件**、**放弃时连已有判读一起作废**。
- 判定：**不是模型的锅**。SKILL.md 只写了"要联网核实"，没写"核实不了怎么办"，最保守的读法就是"不交付"。

**处置**：SKILL.md Step 5B / 系统提示词 rule 9 / `review-protocol.md §7` 三处补「降级不中止」——
换词换源再试 → 仍不行按判读分收敛、`listed_company` 全 `null`、`coverage_notes` 写「联网核实未完成（原因）」→ 照常交付。
事实层 `A-W1` 同步开唯一例外通道（声明可用即通过，但清单必须存在）。

### e2e6：通过

`20261112-111250-cards-e2e6`，`GPT 6.1 Sol`，47 polls / 2932.6 s / 108 次工具调用
（`web_fetch` 29 · `task` 25 · `execute` 22 · `write_file` 4 · `present_artifact` 1）。

| 维度 | 实测 |
|---|---|
| 交付 | `output/watchlist.json`，`count = 28`（pivotal 10 / failed 10 / early 8），`present_artifact` 为最后一次调用 |
| 事实层 | **`facts 23/23 -> PASS`**，warn `A-C1` 亦过 |
| 联网证据 | `work/web/{early,failed,pivotal}.jsonl` 共 26 行，其中 18 行带真实 URL |
| `listed_company` | 26/28 填实（TNGX/NASDAQ 等），2 条 `null`；`stock` 全 `null` 且已在 `coverage_notes` 声明 |
| `why` | 132–160 字，全部为判断（未满足需求 → 定位 → 影响 → 局限），无 `summary` 复写 |
| `promoted` | 0 条——本轮外部讨论未改变入选集，模型改在 `coverage_notes` 里说明"CS2009 外部更新未纳入" |
| 分桶诚实性 | early 只给 8 条，明确写"不以扩样预告或跨试验汇总补齐数量" |

**`A-W1` 同日第二次修**：原实现要求"每条检索记录都带 URL"，把「检索执行了但没结果」这种如实记录判成漏证
（e2e6 的 26 行里 8 行 `url` 为空正是这种情况，导致先假红一次）。改为三条联合约束：
总行数 ≥6、带 URL 的行 ≥6、无 URL 的行必须写 `note`；`m_web_no_urls` + NEG「零结果但已注明」各测一侧。

### 仍为非事实层的 runner 噪声（与本 skill 无关）

`verification.md` 里 `report contains nonempty content` / `present_artifact … output/report.md` /
`prose gate … tell-scan.py` / `tool_results receipts archived` 仍为 FAIL：前三条是仓库通用 profile 期望
`output/report.md`，本 skill 的交付物是 `output/watchlist.json`（同一 profile 在其它 skill 上是 PASS）；
最后一条是 runner 把 `web_fetch` 抓回的 HTML 正文里形如路径的行判成"unsafe receipt path"，属 runner 侧误报。

---

## R8 — v0.8 端到端（2026-11-12，`cards-e2e7` 通过，闸门先抓到一处排序倒挂）

`20261112-135332-cards-e2e7`，`DeepSeek Flash`，56 polls / 1159.6 s / 146 次工具调用，
`web=ON`（`--web`），provider 已切 **deepseek**。

| 维度 | 实测 |
|---|---|
| 交付 | `output/watchlist.json`，`count = 30`（**pivotal 10 / failed 10 / early 10**），`present_artifact` 为最后一次调用 |
| 事实层 | **`facts 24/24 warn 1/1 -> PASS`**（首判 `23/24`，`A-P4-score-order` 红，见下） |
| `reaction` | **25/30 张卡带结构化涨跌幅**（26 张有 `listed_company`），`work/web/quotes.jsonl` 13 行 |
| 口径 | 全部 `2026-10-22 → 2026-10-23`，`basis` 写「会议首日(2026-10-23)收盘 vs 会议前最后收盘」，**未归因** |
| 取数路径 | 东财 kline（`106.MRK` / `116.01093`）+ `web_search` 券商页（stockanalysis / ycharts / moomoo / 恒生 / FT）；两个来源交叉值一致 |
| `promoted` | 0 条；外部讨论到的 MOIO（LBA10）、HARMONY-GI001 因 `rows.json` 里查无对应 esid，改写进 `coverage_notes`（正是 v0.7 定的语义） |
| `why` | 全部 ≥60 字且不复写 `summary` |

**会议首日先查过再算**：模型用 10-23 作窗口首日，与 ESMO 官方口径一致（2026-10-23 至 10-27，IFEMA Madrid，
经 `POST /api/tools/web/debug` 检索 Elsevier / Dana-Farber 两处独立确认）。本地抽查三条行情与东财 kline 逐字相同：
`106.MRK` 147.24 → 145.27（−1.34%）、`105.AMGN` 447.28 → 439.26（−1.79%）、`116.01093` 8.355 → 8.345（−0.12%）。

**闸门抓到的真缺陷（非噪声）**：初判 `A-P4-score-order` 红——failed 桶分数序列 `…72, 71, 63, 66`，
末两条倒挂（`IROCAS` 63 排在 `KEYNOTE-B49` 66 之前）。这是排序错误，不是编辑决定（`why` 里没有覆盖理由）。
人工按判读分纠正为 `…71, 66, 63` 后复判 **24/24 绿**；原文件留档 `/tmp/e2e7-orig.json`，
`transcript.md` 未改动。**注意这一条正是"定榜以判读分为主序"的可观测证据：闸门能抓倒挂，但抓不到"分数本身打偏"**。

**同一轮内已修的两处**

1. **`ticker` 与 `exchange` 语义重叠**：e2e7 出现 `ticker="09966.HK"` + `exchange="HKEX"`、`"600276.SH"` + `"SSE"`、
   `"4568.T"` + `"TSE"`。信息没错，但同一事实印了两遍，且 `fetch_quotes.py` 的 `MARKETS` 只认 `HKEX/LSE/NASDAQ/NYSE/AMEX`，
   这些带后缀的写法无法直接回灌预计算。已钉死：`data-contract §6.5` 写「`ticker` 只写代码本体，市场只在 `exchange`」，`check_cards.py` 新增 `MARKET_SUFFIXES` 直接拒后缀（`test_check_cards.py` 第 20 例），e2e7 的 7 张卡与 6 行证据同步纠正后复判仍 24/24。
2. **`coverage_notes` 没有写行情口径与未覆盖交易所**：本轮 30 张卡里 5 张无 `reaction`（含 SIX 的 Roche/Novartis 与
   两只无公开行情的标的），清单里没有任何一句说明。已在 SKILL.md Step 5B 与系统提示词补「省掉的要在 `coverage_notes` 里记一句哪几只没有行情、为什么」——`A-F7` 只能验"印了就自洽"，验不到"没印的为什么没印"，所以这条靠流程而不是闸门。

**`verification.md` 的 4 条 FAIL 仍为仓库通用 profile 噪声**（期望 `output/report.md` / `tell-scan.py` / receipt 路径），
与 R7 完全同源，本 skill 的交付物是 `output/watchlist.json`。

**结论**：v0.8 的 `reaction` 链路在真实回合里成立——模型自己 `web_fetch` 东财 JSON + `web_search` 券商页，
25/30 张卡拿到带口径的窗口涨跌幅，数值与本地 kline 逐字对得上，且 `--quotes-evidence` 能逐行验账。
闸门在这一轮抓到的是**排序倒挂**（真缺陷），不是行情造假。

---

## R8b — v0.9 拆除复验（2026-11-13，无新端到端，改以 e2e7 产物重放）

v0.9 是**减法版本**，验证目标是"删干净了、且删掉的东西回不来"。本轮没有跑新的平台回合（行情层删除不影响取数、判读、收敛任一步），
复验由三组本地闸门 + 一次产物重放组成。

| 面 | 命令 | 结果 |
|---|---|---|
| 卡片闸门 | `python3 evals/test_check_cards.py` | **20 case 全绿**：identity-only `listed_company` 通过；`listed_company.reaction` 回潮 → `listed_company.reaction is a price field …`；卡片 `stock` 回潮 → `stock is a price field …`；`ticker="09966.HK"` 仍被 `MARKET_SUFFIXES` 拒 |
| 事实层 | `python3 evals/fact-check/mutations.py` | **coverage 25/25 fail items have a mutation; 7 negative controls green**。新 `A-N1-no-price-claims` / `A-C2-report-frontmatter` 各有 mutation，NEG「声明引文且双向对得上」保持绿 |
| 打包 | `python3 tools/pack-dist.py --check` | `OK 16 entries, sha256=dc88978b67b2d6c9`（`fetch_quotes.py` 与 `make_watchlist.py` 均不入包） |
| 产物重放 | `build_review_page.py dist/review/esmo2026-watchlist-v09.json` | e2e7 原始产物剥掉 55 个价格键后重建复核页，**30 卡 10/10/10**，页面无任何涨跌幅 chip，身份 chip（`GSK · NYSE` / `600276.SH · SSE`）仍在 |

**`cards-e2e7` 的 4 条 `verification.md` FAIL 定性**（上一轮遗留，现明确）：`report contains nonempty content` /
`present_artifact is the final successful call for output/report.md` / `prose gate ran` / `no tool errors`
—— 前三项是**仓库通用 profile 的预期不适用**（e2e7 在 v0.8 契约下交付 `watchlist.json`，那时还没有 `report.md`）；
`no tool errors` 对应 `[unmatched-retry] pyd_ai_172e08d3336c4550a3` 一次平台侧重试，无工具报错回传。
**v0.9 起这三项不再"预期不适用"**：交付物就是 `output/report.md`，下一次端到端必须让它们真绿。

**留档**：`/tmp/e2e7-orig.json` 是 e2e7 的**原始未改**产物（含被闸门抓到的 failed 桶排序倒挂，以及 25 张卡的价格字段）；
`dist/review/esmo2026-watchlist-v09.json/.html` 是它的**剥价格重建版**，用于说明"删掉行情后页面长什么样"。两者都不代表 v0.9 的端到端结果——
v0.9 的端到端（E2E #8）尚未跑。

## R9 — E2E #8（2026-11-13，共享 SP 原地更新后首次全链路）

**回合**：`cards-e2e8`，thread `c60b14c7-1ebc-4cd6-8c1e-1df330ac60c1`，turn `98388943-1189-4fa2-b594-c85b0bcc046a`，
DeepSeek Flash，`web=true`。831.5 s / 74 steps / 111 attempts（108 返回 + 3 `write_file` 参数被拒）/ `outcome: succeeded`。
交付 `output/report.md` + `output/watchlist.json`。**首个在"项目不再有自己的系统提示词、只装配共享 SP"下跑通的回合。**

> 一次被中止的尝试（`20261112-173950`，thread `e2bf6508`）不计入：`run` 的 `--web` 默认 off，
> 联网类 skill 必须显式传 `--web`，否则检索层整段消失。已 `POST /api/chat/stop` 停掉并以 `--web` 重跑。

| 面 | 结果 |
|---|---|
| `verification.md`（`--resume` 重建） | **24 PASS / 0 FAIL / 0 WARN**；头部 `web tools: enabled`；`receipts` 10 个持久 pointer 全部存档并 hash 校验 |
| 事实层 `check.py` | `facts 24/25 warn 1/1 -> FAIL`，唯一失败 `A-F4-numbers-traceable`（见下） |
| 交付规模 | 30 卡 `10/10/10`；`coverage: 1097/1097`；8 个切片 / 1097 distinct；`lba 73/73`；`abstract_id` 与 `manual` 全 `null`；20 个不同 `score`；每桶降序 |
| 报告 | `report.md` frontmatter `skills: [conference-result-triage]` / 正文口径 `1097 条登记 → 592 候选 → 30 条` |

### 本轮的三个验证器缺陷（都已修）

1. **`prose gate ran`** 永久 FAIL：本仓库契约里没有 `scripts/tell-scan.py`，而 `toolsmith-publish` 默认
   `prose_gate=True`。→ 在 `projects.json` 显式声明 `prose_gate: false`，输出改为
   `prose gate not part of this repo's contract — skipped`（"不适用"，不是"静默禁用"）。
2. **`deployed support-file manifest matches local`** 永久 FAIL：校验器按 `os.walk(worktree)` 算期望文件集，
   而 `pack-dist.py` 刻意 `EXCLUDE=("make_watchlist.py",)` → 每次运行都把该文件报成"平台缺文件"。
   → 期望集改以 **shipped zip 的 `namelist()`** 为准（`from conference-result-triage-v0.9.zip`）。
3. **`tool_results receipts archived`** FAIL：`/workspace/tool_results/` 是**回合运行期**目录，resume 时窗口已关；
   且原 run 的 `run.json` 因为报告阶段崩溃根本没写 `receipts` 键。→ `--resume` 时把上一个 run 的
   `tool_results/` **copy**（不是 move）到新目录，并**从 `receipts.jsonl` 的 fetch log 重建 manifest**
   （size 来自 log、sha256 来自冻结副本，不一致才 warn），`inherited_from` 写进 `run.json`。
   顺带修 `web tools: disabled` 误报（`--resume` 不传 `--web`，改从 `run.json.enable_web` 兜底）。

### `A-F4-numbers-traceable` —— 交付前闸门比事后校验宽（已修）

失败明细：`44%` / `24%`（esid `24_37_p_60b6645907f2bcd7747db53774088cbb_1`，Krascendo 1）。
原文只有 `44.7` / `24.5`，模型自己四舍五入成 `44%` / `24%`。**同一次运行里 `check_cards.py` 是 exit 0**：
它当时用子串判断（`"44" in "44.7"` 为真），而离线事实层用数值相等。两个闸门口径不一致 → 交付前放行、事后判死，
而 `present_artifact` 是终端动作，读者先看到、评估后打分。

**修法（两侧同源）**：

- `check_cards.py`：数字溯源改成**数值比对**（与 `A-F4` 同语义），新增 3 条 case（prefix 陷阱 `44%` vs `44.7%`、
  逐字 `44.7%` 仍通过、中文 `16 个月` 会被扫到）⇒ 卡片闸门 **23 case 全绿**；对 e2e8 原产物重跑得
  `FAIL (4): figure '16 个月' / '44%' / '24%' / '43 个月' not found` ⇒ **fail-closed 恢复**（现在它会挡住那次交付）。
- `check.py`：`NUM_RE` 的单位枚举补 `个?月`。原来只认 `月`，于是「随访约 16 个月」「随访逾 43 个月」**整个数字被跳过**
  （`月` 前面有 `个`），而同样的错误写成英文（`16.1 mo`）就会被抓。修后 `A-F4` 从 2 条升到 4 条。
- `mutations.py`：新增 `m_number_round`（`ORR 3%` 而原文 `30.0%` / 标题 `DeLLphi-305`，数字出现过、数值没有）
  与 NEG `ngen_decimal_places`（`30.00%` 与 `30.0%` 同值，必须仍绿）⇒ **25/25 fail items 有 mutation，8 个负控全绿**。

**`EVALUATOR_REVISION` → `2026-11-13-r5`。** e2e8 的产物**不修**（它是这一轮的证据）；下一次端到端（R10）以
`facts 26/26` 为通过条件。

## R10（2026-11-13）：跨疾病领域三场并行（ADA / ESC / EASL 2026），v0.9 代码

用户要求把这份 skill 从「ESMO 一场」推广到全疾病领域，判定标准是拿 TS 的推荐与本地联网查到的
「大会热议」比对，不合就改。选三场不同领域、规模差两个数量级的会议并行跑同一份 skill（只换
`meeting_tags`）：ADA 2026（代谢）/ ESC 2026（心血管）/ EASL 2026（肝病）。
run dirs `20261112-181722-cards-{ADA,ESC,EASL}26`，全部 `--web`，同一份已发布的 v0.9 包。

| 会议 | 行数 | 交付 | 卡片分布 | 平台 verification | 事实层（r5） |
|---|---|---|---|---|---|
| ADA 2026 | 191 | 18 卡 | 10 / 5 / 3 | 24 PASS | 22/25 **FAIL** |
| ESC 2026 | 242 | 26 卡 | 8 / 9 / 9 | 23 PASS 1 FAIL（引文） | 19/24 **FAIL** |
| EASL 2026 | 214 | 20 卡 | 10 / 7 / 3 | 23 PASS 1 FAIL（引文） | 22/24 **FAIL** |

**三场同时红，但根因只有三类**（详细复盘见 `references/pitfalls.md` §29–§33）：

1. **期别缺失被当成「非试验证据」丢掉**（`bucket_of()` 返回 `None` → `excluded["无法归类"]`）。
   ESC 242 条里丢 123 条（**51%**），含 `ACACIA-HCM` / `ENRICH-AF` / `SAL003`；ADA 丢 40、EASL 丢 55
   （含 `bepirovirsen` / `pemvidutide`）。ESMO 没暴露这个缺陷，因为肿瘤数据源几乎都填了 `Phase`。
2. **成员资格闸门可被手拼 pool 文件绕过**：ESC 现场有 `work/pool/build_pool_ext.py`，把 110 条塞进
   `pool_ext.json` 当 `--pool` 传进去，卡片闸门全绿，事实层报 9 个未知 esid + 61 个不可溯源数字。
3. **引文两场全红**：`markers=3 keys=0`。一半是 runner 读错了对象（配置 `deliverables` 里没有
   `citations.json` → `cites={}`），一半是文档漏写平台要的 `paper_release_time_str` 键。

**v0.10 修后重算（同一批 `rows.json`，不重跑 TS）**：

| 会议 | 候选池 | 无法归类 | 卡片有池子背书 | `phase_inferred` |
|---|---|---|---|---|
| ADA 2026 | 98 → **138** | 40 → **0** | 18/18 | 18 / 22 / 1 |
| ESC 2026 | 54 → **164** | 123 → **0** | 25/26 → **26/26** | 44 / 69 / 17 |
| EASL 2026 | 80 → **135** | 55 → **0** | 20/20 | 28 / 27 / 5 |

结论：**同一份 skill 换会议能跑，但 v0.9 的候选池在非肿瘤领域会系统性缩水一半**，缩的是会议主线。
这不是调参问题，是「分期缺失 = 排除」这条隐含假设在肿瘤数据里碰巧成立。

**待办**：publish v0.10 → 三场用新代码重跑 → 逐条列「热议但漏推 / 推荐但无人提」的比对表（当前只做了三态计数：
ADA `5/5/5`、ESC `7/1/6`、EASL `6/4/1` = 上榜 / 库内有未上榜 / 库里没有）。

## R11（2026-11-13）：同场评分 + GT 比对 + 选择缺陷归因（v0.10 代码，三场重跑）

R10 之后的三场用 **v0.10 代码**重跑（pool 已修好，`无法归类` 归零），本轮要回答的是**同场评分下
推荐质量到底差在哪**：不跨会议比分数，只看「这场会议自己的判读 → 这场会议自己的榜单」是否自洽、
以及和本地联网查到的「热议」差多少。

运行：`20261113-092008-cards-{ADA,ESC,EASL}-26-v10`（并行，DeepSeek Flash，`--web`）。

| 会议 | 行数 | 候选池 (early/pivotal/failed) | 交付卡 | 平台断言 | 事实层 |
|---|---|---|---|---|---|
| ADA 2026 | 191 | **138** (47/87/4) | 14 (10/2/2) | 24 PASS / 0 FAIL | **25/25 PASS** |
| EASL 2026 | 214 | **136** (56/70/10) | 24 (10/10/4) | 24 PASS / 0 FAIL | **24/24 PASS** |
| ESC 2026 | 242 | **164** (56/85/23) | 24 (10/9/5) | 22 PASS / **2 FAIL** | 24/25 FAIL |

ESC 那 2 条 FAIL 都是「deployed skill ≠ 本地 SKILL.md / 支持文件清单」，原因是**我在它跑的过程中
改本地文件**（v0.11 的 `check_cards.py`/文档），归档里比对的是当时的线上版 —— 属于评测方法噪声，
不是产物缺陷；ESC 的事实层唯一 FAIL 是新增的 `A-P6-selection-order`，**FAIL 的原因正是它的判读文件
没有 `esid`**（见下），闸门按要求拒了。

### 1. 判读分与榜单分：62/62 相等，问题不在「分被改写」

| 会议 | 卡片 `score` == 该 `esid` 的判读 `score` |
|---|---|
| ADA | 14/14 |
| EASL | 24/24 |
| ESC | 24/24 |

`make_cards.py` 只渲染不排序的判断成立。**所以缺陷只能出在「选了谁」。**

### 2. 选择缺陷：三场共 16 条「被判 keep 且分数高于本桶最低入选卡」的条目被舍弃

逐桶取 `floor = min(入选卡 score)`，再看同桶 `keep` 里被舍弃且分数 > floor 的条目：

| 会议 | 桶 | 入选卡 | floor | 被舍弃的更高分 keep |
|---|---|---|---|---|
| ADA 2026 | pivotal | 10 | 71 | **4**：77 `HR17031-301`、74 `HRS9531-T-201`、73 `ACCESS II`、73 `ACCESS` |
| ADA 2026 | failed | 2 | 52 | **1**：72 |
| EASL 2026 | pivotal | 10 | 74 | **3**：85 `PEMA-PBC`、79、76 `TRUTH` |
| ESC 2026 | pivotal | 10 | 54 | **8**：73 `SYH2053-002`、66 `Early tirzepatide after kidney…`、65 `FINO-HF`、65 `VICTORION-Difference`、63 `BETAMI-DANBLOCK`、62 `DIALY-MRA`… |
| ESC/EASL | early / failed | — | — | 0 |

三种会议都中，说明不是某场会议的特例。EASL 的 pivotal 缺口从 R10 的「7 条全高于 35 分卡」缩到
「3 条高于 74 分卡」，是 v0.10 池子修好后**有更多高分卡填满 10 个位子**的结果 —— 但 85 分那条
（`PEMA-PBC`）仍然输给了 74 分的卡，没有任何文字解释。

### 3. GT 比对（同源 web provider）：漏推的多半是「判读正确地判低了」

GT 由平台自己的 web provider 取（`POST /api/tools/web/debug`, provider=deepseek），匹配按 esid 而非
字符串，分三态：上榜 / 库内有但没上榜（真漏）/ 库里根本没有（覆盖缺口，不是排序问题）。

| 会议 | GT 热议 | 库内有 | 上榜 | 真漏 | 库里没有 |
|---|---|---|---|---|---|
| ADA 2026 | 40 | 9 | 4 | 5 | 83 |
| ESC 2026 | 40 | 7 | 5 | 2 | 116 |
| EASL 2026 | 40 | 11 | 4 | 7 | 152 |

逐条看那 14 条「真漏」的判读结论（这是本轮最有价值的一段）：

| 热议条目 | 判读 | 分 | 判读对不对 |
|---|---|---|---|
| `ACHIEVE-2`（orforglipron vs 达格列净） | keep | 70 | **对**，pivotal floor 71，差 1 分落榜 |
| `SOLSTICE` / `RESPONSE` | keep | 74 / 54 | **对**，两条都已上榜（GT 按旧试验名记的，属于匹配噪声） |
| `ASSURE`（seladelpar 开放标签延展，只看血脂/肌痛） | drop | 32 | **对**：已获批药的长期安全性，无新疗效 |
| `NAVIGATE`（belapectin，主要终点未达） | weak | 35 | **对**：终点没打成 |
| `AT HOME-HF`（皮下呋塞米） | drop | 28 | 对，次要读数 |
| `DAN-RSV` / `MILOS` | drop 25 / weak 34 | | 对，亚组/早期 |
| `DREAMS-3`（mazdutide vs 司美，头对头） | weak | 64 | **可争议**：头对头优效但 me-too，novelty 扣分可以理解 |
| `SELECT`（司美哮喘相关不良事件） | weak | 53 | 对，不是那个 CVOT，是二次分析 |
| **`ENSURE`（elebsiran+PEG-IFN，随机，功能治愈 17% vs 6%，n=55）** | **weak** | **65** | **错**，见下 |

`ENSURE` 的 `reason` 是「NA 经治CHB，随机48周加停药24周，功能治愈17%对6%，**每组仅18例**」，
`score_parts = evidence 14 / effect 16 / impact 20 / novelty 8 / maturity 7`。同一个会议里：

| 记录 | 设计 | 效应 | 判读 |
|---|---|---|---|
| `ENSURE` n=55 | **随机对照** | FC 17% vs 6%（3 倍、+11 pt） | **weak** 65，effect 16 |
| 单臂 n=22 长期延展 | 单臂 | 45.5% 清除 | **keep** 68 |
| 开放小队列 n=56 | 开放 | 清除率最高 80% | **keep** 62 |
| `B-Sure` n=44 停药随访 | 应答者随访 | 80% 维持 FC，各时点分母 1–10 | weak 60（**这个 weak 是对的**） |

**同一个「小样本」量出了三种结论** —— 判读在用 `n` 当判决器，而 skill 明写「`n` 不是纳入闸门」。
扫描三场判读理由，把样本量写进 `weak`/`drop` 理由的占 31/138、43/136、42/164（约 1/4），多数是合理
的证据强度描述，但 `ENSURE` 这种「随机 + 主终点达成 + 效应 3 倍」被 n 打成 weak 属于自伤。

### 4. 不能只事后记，必须交付前就挡

`A-P4-score-order` 只查「卡内排序是否降序」（榜单里 10 张卡自己是降序的），`A-P6` 是本轮新增的
「被舍弃者高于入选者」检查，两者都是**事后**复核。真正能挡住的是交付前的
`check_cards.py --judged`：`selection_order()` 逐桶算 floor，任何 `keep` 分数 > floor 却没上榜、
也没写进 `editorial_overrides` 的，直接失败；写了但 `reason` < 10 字的不算豁免。

三场 run 的判读产物（`judged_A..G.json` / `judged_01..23.json`）**都没有 `esid`**，`i` 又是批次内
序号（ADA 每批从 1 重数，ESC 却是全局 1..164），所以「85 分那条去哪了」只能靠猜批次对齐 ——
这就是判读契约从八键加到九键的原因。**这三场不能当 v0.11 的证据**，要重跑。

### 5. 本轮结论与改动

1. `check_cards.py`：判读必须带 `esid`；`--judged` 必传；`selection_order()` 逐桶比 floor；
   `editorial_overrides` 逐条校 `reason` ≥10 字；CLI 侧拿不到可用判读 → **fail-closed**。
2. 事实层加 `A-P6-selection-order`（28 项）+ `m_selection_order` mutation（抬**被跳过者**的分，
   抬已入选卡会先被 `A-P4` 抓，验不到新项）。
3. `make_cards.py` 从 `plan.json` 顶层搬 `coverage_notes` / `editorial_overrides`。
4. `review-protocol.md §2.5` + `SKILL.md` Step 4：**样本量只进 `evidence_strength`**，不进
   `verdict`、不压 `effect_size`；`weak`/`drop` 的 `reason` 里只有「仅 N 例」不算理由。
5. `pitfalls.md §34`：所有闸门全绿，榜单仍然可能是「次优的那一版」。

**未修**：`ENSURE` 这类判读偏差只能靠规则 + 重跑观测，没有机器闸门（判定「这个 weak 合不合理」需要
读摘要，不给脚本做 NLP 判官）。下一轮重跑时检查 HBV/功能治愈这一类是否还出现 n 驱动的降档。

## R12（2026-11-13）：v0.11 原地发布后重跑 EASL / ESC 2026 —— 闸门在真 run 上确实生效

R11 的结论要求「判读带 `esid` + 定榜按判读分取前 k」。发布 v0.11（in-place）后用**同一份 skill**重跑两场：

| 会议 | run | 墙钟 | 工具调用 | 平台断言 | 事实层 | 交付卡 |
|---|---|---|---|---|---|---|
| EASL 2026 | `20261113-094709-cards-EASL-26-v11` | ~19 min | — | **23 PASS / 1 FAIL** | **25/25 PASS**（含 `A-P6`） | 25 (10/10/5) |
| ESC 2026 | `20261113-094710-cards-ESC-26-v11` | ~20 min | — | **24 PASS / 0 FAIL** | **25/25 PASS**（含 `A-P6`） | 22 (10/6/6) |

对照 R11（v0.10 代码跑同样两场）：

| 指标 | EASL v10 | EASL v11 | ESC v10 | ESC v11 |
|---|---|---|---|---|
| 判读条目带 `esid` | 0/136 | **136/136** | 0/164 | **164/164** |
| pivotal 入选最低分（floor） | 74 | **81** | 54 | **62** |
| 舍弃的更高分 `keep`（违规） | 3 | **0** | 8 | **1（已声明）** |
| `editorial_overrides` 条数 | 0 | 0 | 0 | **1** |
| 事实层 `A-P6-selection-order` | FAIL（无 `esid`） | **PASS** | FAIL（无 `esid`） | **PASS** |

ESC 那唯一一条「舍弃更高分」被写进了交付 JSON 顶层：

```json
{"esid": "24_37_d0c8a8812ed1d2f31ea96153ae1f483b_1",
 "reason": "VICTORION-Difference 为探索性二次分析，与已入选的 VICTORION-Challenge 同属 inclisiran 策略、
            同适应症，压同质只留一条 PCSK9 siRNA 头对头；改选同为 62 分的 LIRA-HF（HFrEF 合并肥胖的事件终点）
            以覆盖心衰方向。"}
```

这正是 v0.11 想要的形态：**要么按分数取前 k，要么把「为什么不」写成账**。`check_cards.py --judged <work 目录>`
在 ESC 上 exit 0（同一次调用换成旧 run 的 `judged_all.json` → exit 3 `holds no usable judgement record`，
fail-closed 双向都验到）。

EASL 那条 FAIL 不是产物问题：模型在 `present_artifact` 之后又调了一次 `write_todos`，平台断言
「`present_artifact` 必须是最后一个成功调用」判红。已写进 `pitfalls.md §35` + `SKILL.md` Step 7 行为约束。

**EASL v11 的 pivotal 榜**（floor 81，含之前被错标的 85 分 AHB-137 现在标题也对了）：95 牛初乳重症酒精肝 /
88 贺普拉肽丁肝 / 87 HSK31679 MASH / 86 saroglitazar EPICS-III / 86 APACHE / 85 AHB-137 —— R11 里被舍弃的
85 `PEMA-PBC`、79、76 `TRUTH` 一类不再有「比它们低的卡占位」。

**尚未验证**：`ENSURE` 那类「用 n 当判决器」的判读偏差，这两轮没有同名记录可对照；HF/HBV 领域要等下一轮
GT 比对才看得出规则文字是否真的改了判读行为。

## R13（2026-11-16）：v0.12 原地发布后跑 ESMO 2026 —— 标星强制位在真 run 上生效

v0.12 把 `clinical_result.abstract_id` / `clinical_result.is_recommand` 加进 `selected_fields`（此前从未请求过，是两个版本以上的静默缺列），
并把 `is_recommand=是` 定义成**强制位**：必上榜、桶内置顶、压过判读分、不吃 `editorial_overrides`。发布（in-place，`v0.3.0`，16 entries，133599 → 142389 B）
后立刻用同一份 skill 跑 **ESMO 2026**（1097 条记录，是迄今最大的一场，EASL 214 / ESC 242 的 4~5 倍）。

| 项 | 值 |
|---|---|
| run | `20261116-162537-cards-ESMO-26-v12` |
| 墙钟 | 1681.9 s 服务端 / 1700.3 s 轮询（~28 min） |
| 工具调用 | 107 次（`execute` 49 / `web_search` 22 / `task` 19 / `params 工具` 9 / `present_artifact` 1） |
| token | in 31.06 M / out 0.72 M / reasoning 0.44 M，缓存命中 0.967 |
| 平台断言 | **24 PASS / 0 FAIL / 0 WARN** |
| 事实层 | **28/28 fail + 1/1 warn → PASS**（`evaluator 2026-11-13-r6`，含 `A-F1-abstract-id-traceable` 与 `A-P7-recommand-forced`） |
| 交付卡 | **30（10/10/10）**，全场 817 条判读（keep 352 / weak 309 / drop 156），1634 条判读记录全部带 `esid`（19 个 `judged_G*.json` + `judged_all.json`） |
| `check_cards.py --judged <work>` | **EXIT=0**，`OK cards=30` |

### 强制位的实际表现

全场 1097 条里只有 **1 条**标星：`LBA7` / `CLARITY-Gastric 01`（Sone-Ve，CLDN18.2 ADC，2L+ 胃食管腺癌）。

```
pivotal 桶顺序：LBA7 81(推荐) → LBA3 95 → LBA1 90 → 2071O 88 → LBA69 88 → …
```

判读只给了它 **81 分**（同桶第 10 名附近），但它排在 95 分的 DeLLphi-305 之前 —— 这正是 v0.12 要的行为：
**强制位决定"读不读"，判读分回答"有多强"，两者不混**。`tag` 印「推荐」（优先于 `LBA`），报告正文第 48 行即为其卡片。

`coverage_notes` 第三条把三态说全了：

> `is_recommand 列已拉取，1097 行中仅 1 行被数据方标星（LBA7 CLARITY-Gastric 01），已按强制位置顶于重磅 II/III 期桶首位；其余行未标星不等于无价值。`

### `abstract_id`

30 张卡 **全部非空**（`LBA87` / `2575P` / `1768RO` / `LBA7` / `LBA3` / `2492P` …），且逐条与 `work/rows.json` 相等
—— `check_cards.py` 的三态校验（缺失 / 与 rows 不符 / 凭空发明）一条未触发，`A-F1-abstract-id-traceable` PASS。
对照 R11/R12：EASL/ESC 两场的卡片在这一列上全是 `null`，不是那些会议没有摘要号，是我们从来没要过。

### 选择闸门

| 桶 | 判读 keep | 入卡 | floor（入选最低分） | 舍弃的更高分 keep | overrides |
|---|---|---|---|---|---|
| 早期机会 | 219 | 10 | 69 | 1（70 分，`nr_24_37_p_289483b`，胰腺癌十余人 / NSCLC 3 例，82% 缓解率） | 1 |
| 重磅 II/III | 82 | 10 | 81 | 11（85 / 84 / 84 / …） | 11 |
| 失败的研究 | 51 | 10 | 73 | **0** | 0 |

`card score == judged score`：**30/30 逐条相等**，无一条在渲染阶段被改写。
12 条 `editorial_overrides` 全部 ≥39 字（最短 39，最长 81），逐条对应一个被舍弃的更高分 `keep`；
其中一条直接写了强制位的代价：*「标星强制位占去一个名额后，更新读数让位于首次公布的研究」*。

### 这一轮暴露的新问题（进 TODO，不是本轮修的）

- **卡片「期别未标注」丢了推断依据**：`LBA7` 的 `phase_inferred = 随机化对照（按设计判定）`，但报告正文该栏只印「期别未标注」，
  没按 `data-contract.md §6.5.0` 印出括号里的判定依据。数据层没错，是渲染措辞没照抄 —— 下一轮把模板里的三种取值写死在 Step 5 的渲染说明里。
- **判读文件命名仍在漂**：ESMO 产 `judged_G01..G19` + `judged_all.json`，EASL 产 `judged_01..14` 无 `_all`，ESC 产 `judged_a..f`。
  `check_cards.py --judged <目录>` 三种都能读，但「同一种布局」才谈得上跨场自动化，待统一。

# 评测结果台账（conference-result-triage）

对齐 `clinical-result-comparison/evals/EVALUATION_RESULTS.md` 的习惯：每轮改动记一行「改了什么 → 哪个测量动了 → 结论」，不做无测量的声明。

评分口径：`facts_ok / facts_total`（fail 级事实项），不是布尔「跑完没」。布尔说不出「45 张好卡」和「45 张刚好过 schema 的卡」的区别。

---

## R14（2026-11-17）：v0.13 原地发布后跑 ADA 2026 —— 代码层确实没了，顺序与三态露出来

**改了什么**：v0.13 删掉 `listed_company` / `ticker` / `exchange` 整层，`is_recommand` 不再渲染徽章（`TAGS = ("", "LBA")`）。发布前用 v0.12 的 ESMO 产物验过 fail-closed（`EXIT=3`：30 条代码 + 1 条 tag），同批内容去掉身份层后 `EXIT=0`。**这一轮是发布后的第一次真跑。**

**对象**：`20261117-090551-cards-ADA-26-v13`（ADA 2026，DeepSeek Flash，`--web`）。191 行 → **138 候选**（early 47 / pivotal 87 / failed 4）→ 判读 138 条（5 批）→ 交付 **30 卡（10/10/10）**。墙钟 **1321.6 s**（22 min），101 次工具调用（`web_search` 17 / `with-params` 3 / `task` 5 / `execute` 49）。

**三个验证点全部成立**：

| 验证点 | 实测 |
|---|---|
| 卡面没有公司代码 | `with code keys: 0` —— 30/30 卡无 `listed_company`/`ticker`/`exchange`，连 `null` 都没有 |
| `tag` 不是徽章 | 取值集合 **`{'', 'LBA'}`**，无「推荐」；LBA 卡 7 张 |
| 标星仍决定位置 | 本场 `is_recommand` 整列空（191 条 0 标星）→ 强制位不适用，`coverage_notes` 按「列已拉取、无标星」写 |
| 顺带 | `abstract_id` **30/30** 非空；`check_cards.py` **EXIT=0 `OK cards=30`**；平台断言 **24 PASS / 0 FAIL / 0 WARN** |

**检索成本下降兑现**：同场（ADA 2026）三次运行的 `web_search` 调用数 **29（v0.9）→ 25（v0.10）→ 17（v0.13）**，降 32%。删掉「上市公司」那一类查询模板的预期收益成立。

**事实层 25/27 FAIL，两项都不是 v0.13 引入的**：

| 项 | 输出 | 归因 |
|---|---|---|
| `A-D1-full-coverage` | `missing pattern 'coverage:\s*1097/1097'` | **评测器缺陷（我方）**：pattern 把 ESMO 的行数写死成 `1097`，ADA 是 `191/191`。同一句断言换个会议就假红 |
| `A-P4-score-order` | `ascending inside ['pivotal/recommand=False']` | **交付缺陷（真）**：pivotal 第 8–10 张为 `71, 73, 71`，73 分排在 71 之后 |

**A-P4 的两个次生问题**（同一处暴露）：

1. **plan 顺序没有交付前闸门**。`make_cards.py` 只渲染不排序，桶内降序靠模型写 plan 时自觉；`check_cards.py` 的 selection gate 只查「有没有跳过高分」，不查「已经入选的是不是降序」。所以顺序错了能过闸门，只能靠事后 `A-P4` 抓 —— 与 v0.11 修选择缺陷时的处境同形。
2. **同一条试验的三个亚组占掉 pivotal 三席**（`HR17031 vs iGlar` 71 / 73 / 71）。「同机制 ≤2」是按机制限的，管不住同一试验拆成主结果 + 亚组 + 安全性三篇。

**另一个只有实跑才看得见的缺陷**：卡片上 `is_recommand` 印成 **`False`**，而它在库里是 `None`（本场 191 条全空）。`make_cards.py:130` 与 `check_cards.py:622` 都用 `bool(...)` 把三态压成二值 —— 「数据方没标星」被写成了「数据方标了否」。平台这轮同步更新了该字段的工具文档：`是`=推荐、**`否`=不推荐须排除**、空=模型自判。按新语义，卡面一个 `false` 就是一条可执行的排除指令，这不再是表述问题。

**结论**：v0.13 的目标达成（代码层消失、徽章消失、检索省 1/3）。**缺陷从「卡面多一个字段」转移到「顺序与三态」** —— 两者都是 v0.12 就埋下、这轮同场对比才照出来的。

## R15（2026-11-19）：v0.14 发布后跑 ASH 2026 —— 三态不再坍缩、桶内降序成立，`A-D1` 的写死行数被真跑打红

**改了什么**：①`is_recommand` 三态一路直传（`_recommand_value` / `_recommand_of` / `_recommand_state` 各一份，`None` 不写 `False`）；②新增交付前闸门 `bucket_order_gate`（分组键 `(bucket, is_recommand)`）与 `trial_seats_gate`（同试验 ≤2 席，超席须 `editorial_overrides` 且 `reason ≥10`）；③`phase_label()` 让设计词（「前瞻性研究」等）不印进 `phase` 槽；④事实层补 `A-P8-recommand-tristate` / `A-P9-trial-seats`，共 **29 fail + 1 warn**；⑤`A-D1-full-coverage` 从写死 pattern 改为 `self_coverage`（从 transcript 读 `coverage: n/n`，要求自洽且等于 `rows.json` 行数）。

**对象**：`20261119-120850-resume-cards-ASH-26-v14b`（thread `b10c7f03`，接在 `20261119-111741-cards-ASH-26-v14` 之后 `--resume`）。ASH 2026（68th，2026-12-12 至 12-15，New Orleans，官网核过）**1524 行** → 排除 577（回顾性 463 / TiP 57 / 真实世界 50 / 汇总分析 2 / Not Applicable 5）→ **893 候选**（early 493 / pivotal 356 / failed 44）→ 全量判读 → 交付 **30 卡（10/10/10）**。墙钟 **3753 s**（62.6 min，首轮 3002 s 超时后续跑 694 s），64 次工具调用（`task` 21 批判读 / `execute` 14 / `read_file` 13 / `web_fetch` 4 / `with-params` 1）。

| 验证点 | 实测 |
|---|---|
| 三态不坍缩 | 30/30 卡 `is_recommand = null`（本场 `column_present=False`），**没有一张被写成 `false`** —— R14 的 191 条全 `false` 未复现 |
| 桶内降序 | early `86,86,85,84,83,83,82,82,80,80` · pivotal `96,94,94,93,91,91,91,90,90,90` · failed `94,94,93,91,91,90,88,88,87,86`，`bucket_order_gate` 无告警 |
| 同试验席位 | `A-P9` 无超席；ASH 的 `trial_abbreviation` 有值率高，闸门这次**有数据可算**（对比 ADA 只有 1/191） |
| 设计词不进 `phase` | 交付卡 `phase` 槽全部是期别或空，无「前瞻性研究」类设计词 |
| 闸门与事实层一致 | `check_cards.py` **EXIT=0 `OK cards=30`**；`check.py` **facts 28/28 warn 0/1 → PASS** |

**`A-D1` 是这轮唯一被真跑改掉的闸门**。R14 里它把 `1097/1097` 写死，ADA（191）假红，当时只加了一句告警；ASH（1524）同样假红且没有 scenario 可切。改成 `self_coverage` 后同一 run 由 `FAIL` 变 `PASS`（`coverage 1524/1524 matches 1524 rows`），mutation `m_coverage` 仍能翻红（删掉该行 → `no coverage line matched`），fixture 的 transcript 也改成按实际行数写（12/12）。**教训：写死语料规模的断言，等于把「评测器缺陷」长期伪装成「交付缺陷」。**

**这轮暴露的数据缺口（不是 skill 缺陷）**：ASH 2026 的 `clinical_result.lba` **1524 条全为 null**（`A-D4-lba-not-dropped` 报 `no lba rows in this corpus` → SKIP），`is_recommand` 列**不存在**（`column_present=False`）。两条都写进了 `coverage_notes`：LBA 按官方「晚期突破性摘要 2026-12-07 才公开」解释，推荐列按「已拉取但全空 ≠ 没有重点研究」解释。v0.14 的 LBA 加分项在这种会场上**无处可加**，闸门输出 SKIP 而非 PASS，符合「缺面 → SKIP」的规矩。

**共享 SP 在发布前被 owner 原地改了**：pin 记的是 `a2b1581ef7cd`（29169 B），live 变成 `6db755d1f080`（29311 B，v1.0 未升号），publish 硬拦一次。按工具指示重读 deployed instructions（580 行 / 23363 chars，`## File Artifact Presentation` 契约未变、无 `report.md` / `citations` 路径硬要求），更新本地 `shared_prompt_pin` 后 `status` 转 `pin matches`。**没有写 SP 本体。**

**run 期两条断言 FAIL 属发布态不同步，不是内容缺陷**：`deployed skill body == local SKILL.md` 与支持文件清单两条红，因为我在 run 进行中改了 `check_cards.py` 的 docstring（补规则 18/19）与 `SKILL.md` 的 case 计数。12:23 重新 `publish` 后 `identical=16 differing=0`、`STATUS: in sync`，两条断言的对象已一致。**代价是这一轮没有「发布态下的全绿断言」快照**，如实记在此处，不假装重跑过。

**另一个 runner 侧发现（`--resume` 丢模型参数）**：首轮用 `--model "GPT 6.1 Sol"` 起跑，`--resume` 时未重传，平台回落到项目默认模型，`verification.md` 记的是 **DeepSeek Flash**。产物质量仍达标（30 卡、facts 全绿），说明该 skill 对模型不敏感；但**续跑必须重传 `--model`**，否则「同一 run 换模型」会静默发生。

**结论**：v0.14 的三个目标（三态、顺序/席位闸门、设计词不进期别槽）在 893 条全量判读的大会上全部成立。这轮真正被拧动的旋钮是评测器本身（`A-D1` 动态化），以及两条只有跨会议真跑才照得出来的数据缺口（`lba` 全空、`is_recommand` 列缺失）。

> **更正（v0.15 复核）**：上面那条「`--resume` 平台回落到 DeepSeek Flash」**是记录错，不是平台行为**。续跑的首轮与 `--resume` 两轮 `turn_id` 完全相同（`a896be10-21e5-4ef2-ab97-ad39b07e5f91`），`--resume` 根本不 `POST /api/chat`，模型不可能变；出错的是 runner 把 `a.model`（CLI/配置默认值）写进了 `run.json` 与 `verification.md`。修法见 O56（续跑继承原 `run.json` 的 `model` / `reasoning_effort`，显式 `--model` 与原记录冲突时告警而不篡改）。

## R16（2026-11-19）：v0.15 发布后跑 ADA 2026 —— 交付物只剩一份 JSON，28/28 全绿

**改了什么**：把 `report.md` 及其整条链删掉（frontmatter / `skills` / `{{ref_N}}` / `citations.json` / `check_cards.py --report` / 事实项 `A-C2` / 3 条 citation mutation），`watchlist.json` 成为唯一交付物；rule 19 → 18、facts 30 → 29（28 fail + 1 warn）；`projects.json` 的 `deliverables` 只剩 JSON；runner 侧修掉两处（O57 md 可选、O56 续跑模型记录）。

**对象**：`20261119-144018-cards-ADA-26-v15`（thread `ba885826`，`--model "DeepSeek Flash"`、`--web`，`enable_web=true`）。ADA 2026 191 行 → 交付 **27 卡（early 10 / pivotal 10 / failed 7）**。墙钟 **635.8 s**，86 次工具调用（`execute` 41 / `web_search` 21 / `read_file` 7 / `task` 5 / `write_file` 5 / `with-params` 3 / `present_artifact` 1）。

| 验证点 | 实测 |
|---|---|
| 交付物只有一份 | `artifacts/output/` 下**只有 `watchlist.json`**，没有 `report.md`、没有 `citations.json` |
| `present_artifact` 目标 | `args={'path': '/workspace/output/watchlist.json'}`，且是**最后一个成功调用**（断言 24 PASS） |
| runner 不再假红 | `[PASS] no markdown deliverable declared - report-body assertions skipped · deliverables=output/watchlist.json`（旧 runner 在这一行恒 FAIL） |
| 交付前闸门 | `check_cards.py` **EXIT=0 `OK cards=27`** |
| 事实层 | `check.py --scenario ada2026` **facts 28/28 warn 0/1 → PASS** |
| 三态 | 27/27 `is_recommand = null`（本场列存在但全空），无一张写成 `false` |
| 桶内降序 | early `57…36` · pivotal `88…74` · failed `75,65,56,54,52,36,36`，无回升 |
| 徽章 | `tag` 只有 `""`(17) 与 `LBA`(10)；卡面无 `listed_company` / `ticker` / `exchange` / 行情字段 |
| 卡面键集 | 18 键，无 `phase`/`phase_inferred` 混用（设计词未进期别槽） |

**失败桶只有 7 张，不是少交付**：ADA 2026 的 pivotal/failed 候选本身就少（v13 同场也是 failed 桶凑不满），`check_cards.py` 的 `PER_BUCKET_CAP=10` 是上限不是配额，未用 `weak` 凑数。这与 v0.14 的「每桶 10 条」不矛盾——那一轮 ASH 1524 行候选充足。

**这轮验证的重点不是榜单质量，而是「删掉一层之后契约是否还成立」**：`present_artifact` 的路径、事实项的 suffix、runner 的回落、`projects.json` 的 deliverables、`check_cards.py` 的参数面，五处全部换到 JSON 上，真跑一次全绿。反证也留了：拿 v0.14 的 ASH 产物跑新事实层 → **只红 `A-T1-present-artifact`**（它指向 `report.md`），其余 26 项照旧绿，说明闸门不是被删空而是被改指。

**发布**：`POST /api/skills/update_skill_file` HTTP 200，`entries=15 identical=15 differing=0`、`STATUS: in sync`（label 仍 `v0.3.0`，部署时间 `2026-11-19T14:40:10`）。共享 SP 未动（`pin matches`；deployed instructions 从 23363 → 23408 chars 的差值只是末尾一行 `Today's date is 2026-11-19.`）。

## R17（2026-11-20）：v0.16 本地闸门复验 —— `drug`/`target` 从「模型自觉填」变成第四条四件套

**改了什么**：`check_cards.py` 新增第 19 条 `card_identity_gate()`（每卡 `drug`/`target` 非空；`target` 空只认
`editorial_overrides` 里 `field: "target"` 的声明）；事实项 `A-P10-card-identity` + `op_card_identity`（facts 29 → **30**，
`EVALUATOR_REVISION` → `2026-11-20-r7`）；mutation `m_drug_blank`；`test_check_cards` 51 → **56**；文档四改
（`review-protocol §7A` 删掉「会议库已给出 drug/target」这句假话、`data-contract` 表 + 规则数、`SKILL.md` 契约与版本块、
`pitfalls §44`）。

**为什么值得单列一条记录**：这不是加一条 nice-to-have，而是补一个**已经真实丢失过**的可读层。ADA 2026（R16）
交付的 27 张卡 `drug`/`target` **27/27 全空**，而当时 `OK cards=27`、`facts 28/28 PASS` —— 18 条规则里没有一条问过
这两个字段，因为它们的值不从任何列来，只从判读者的阅读里来。

| 验证点 | 实测 |
|---|---|
| 单测（干净卡有值） | `test_check_cards.py` → `fixture OK`，新增 5 case 全绿（含「选择跳过理由不许豁免空靶点」反向 case） |
| 事实层全覆盖 | `mutations.py` → **`coverage: 29/29 fail items have a mutation; 7 negative controls green`** |
| **反例：真实产物** | `20261119-144018-cards-ADA-26-v15/artifacts/output/watchlist.json` → 新事实层 `facts 28/29 -> FAIL`，**唯一红项 `A-P10-card-identity`**；`check_cards.py` **EXIT=3**、54 处空位（27 卡 × 2 字段） |
| **正例：已补齐的同一份榜单** | `dist/review/ada2026-watchlist-v15.json`（`attach_arms.py` 从 `clinical_result.arms` 填 22 张 + 5 张手补）→ 只剩 **3 处 `target` 空**（BCG × 2、二甲双胍），正是「确实没有分子靶点」的那三条，须走 `field: "target"` 声明 |
| 打包 | `dist/conference-result-triage-v0.16.zip` — **151730 B / 15 entries** / sha256 `bd2197a2cbaa3248…` |

**没做的**：未发布（写平台需授权）、未跑 E2E。要在真跑里证明两件事：①模型**在拿不到 `arms` 通道**时会自己从
标题/摘要里读出药名与靶点；②无靶点的记录会正确写成 `editorial_overrides` 的 `field: "target"` 声明，而不是留空。
在此之前 v0.16 只能算「闸门就位」，不算「已验收」。

**数据侧的既有结论（供下一轮参考）**：`clinical_result` 无 `drug`/`target`/`moa` 列；唯一结构化来源
`clinical_result.arms[].drugs[]` 单条 ≈5.9 KB（27 卡 159.9 KB、全场 1097 卡 ≈6.4 MB 撞 6 MB 截断）；
`is_primary_drug` 实测不可信（ACHIEVE-5 把甘精胰岛素标成 primary）；药名选择必须「标题 `vs` 前段 + cn/en 双名匹配」，
靶点只取选中药那一条。

## R18（2026-11-20）：v0.16 原地发布后跑 ENA 2026 —— 模型在拿不到 `arms` 通道时自己把药名与靶点写上了

**改了什么**：v0.16 原地发布（第 19 条 `card_identity_gate()` / `A-P10-card-identity` / `m_drug_blank`）。这轮是 v0.16 的**验收跑**，不是评分质量评测：重点只有一个 —— 没有任何数据列兜底时，判读者会不会真的把 `drug` / `target` 写进卡。

**对象**：`20261119-154031-cards-ENA-26-v16`（thread `7d3f9320`，turn `2ab455af`，`--model "DeepSeek Flash"`、`--web`）。**ENA 2026**（EORTC-NCI-AACR 分子靶点与癌症治疗研讨会）结果库仅 **17 条**记录 → 交付 **10 卡（early 8 / pivotal 1 / failed 1）**，墙钟 **413.3 s**，78 次工具调用（`execute`×29 / `read_file`×19 / `web_search`×11 / `with-params`×10 / `write_file`×3 / `write_todos`×2 / `load_skill`×1 / `edit_file`×1 / `present_artifact`×1）。

| 验证点 | 实测 |
|---|---|
| **`drug` / `target`（本轮主题）** | **10/10 两张都非空**，全部由标题+摘要抽出（本轮**没有**调 `clinical_result.arms`，也没有手补）：`OMO-103（Omomyc）/ MYC`、`[212Pb]VMT-α-NET / SSTR2`、`AVZO-1418（DB-1418）/ EGFR·HER3`、`lifileucel / 肿瘤浸润淋巴细胞（TIL，非分子靶点）`、`ACE1831 / CD20`、`BAL0891 / TTK·PLK1`、`INCB123667 / CDK2`、`CRB-701（SYS6002）/ Nectin-4`、`RSO-021 / PRX3`、`LY4066434 / KRAS` |
| 交付前闸门 | `check_cards.py` **EXIT=0 `OK cards=10`**（含第 19 条） |
| 事实层 | `check.py` → **facts 28/28 warn 0/1 → PASS**，`A-P10-card-identity` → `drug+target named on 10 card(s)`；恰好 `A-D4` SKIP（本场 `lba` 全空） |
| runner 断言 | **24 PASS / 0 FAIL / 0 WARN**（唯一瑕疵：`write_file` 一次 `plan.json` 已存在被拒、随后重发成功） |
| 覆盖与自洽 | `A-D1` `coverage 17/17`（与 `rows.json` 比，未写死语料规模）；`A-D5` 17 = 17 pooled；`A-F3` 全部溯源到池；`A-F4` 每个数字可回溯 |
| 三态 / 席位 / 顺序 | `is_recommand` 全 null（列存在但整列空）且写进 `coverage_notes`；`A-P9` 每试验 1 席；`A-P4` 桶内降序 |
| 诚实声明 | 6 条 `coverage_notes`：明写本场只有 17 条、三桶无法各 10 条、**未用无读数记录凑数**；明写库里没有的 LBA（ADCE-D01 / REM-422 / AN4035）**未纳入** |
| 复核页 | `dist/review/ena2026-watchlist-v16.html`（19818 B / 10 卡）——卡头药物胶囊与左导全部印模型写的药名，`lifileucel` 那条显示 `TIL，非分子靶点` |

### 这轮抓到的**评测器缺陷**（不是交付缺陷）：`A-D2-sliced-pulls` 把语料规模写死成 ESMO 的量级

ENA 只有 17 条，`plan_slices.py` 正确地没有切分（`work/slices/` 下只有 `_all_ids.txt`），一次拉完 17 行 —— 这本身是对的。但 `op_query_slicing` 的 `sources` 分支用常数 `min_calls=7` 判「至少 7 次 dump」，于是**一个正确的 17 行会议被判失败**（`1 dump < 7`）。这与 v0.12 那个「断言里写死 1097」是同一类错误，只是换了个位置。

- 修法：该分支改为按已拉到的行数反推 `need = ceil(rows / max_slice)`（与 `slices` 分支同一原则），截断型宽拉仍会被抓（一次 dump 的自身行数超过 `max_slice`，单 dump 覆盖不了 2× 上限）。
- 反例：新增负控 **`ngen_small_corpus_single_dump`**（17 行、单 dump、无切片）必须绿 → `coverage: 29/29 fail items have a mutation; **8** negative controls green`。
- 修完同一份产物 → `facts 28/28 PASS`。

### 留作下轮的三条观察（未改）

1. **`lifileucel` 的 `target` 写成了散文**（`肿瘤浸润淋巴细胞（TIL，非分子靶点）`）。它诚实地表达了「细胞治疗没有分子靶点」，但走 `editorial_overrides` 的 `field: "target"` 声明才是本版设计路径。闸门目前只查非空，若要连这种写法一起管，需要一条「`target` 不得是解释性长句」的规则 —— 有误伤风险，留证据不动。
2. **`A-C1-heat-coverage` 0/12**（warn）：那张「热议试验」名单是 ESMO 2026 攒的，跨会议天然 0/12。warn 不阻断，但按「事实项按会议能力 gating」的原则，它应该改成按会议取名单或在该会议无名单时 SKIP。
3. **ENA 2026 结果库严重不全**：17 条，同期 ENA 2025 有 43 条，模型检索到的三条 late-breaking 口头报告库里都没有。**这类小会议不适合当「榜单质量」评测对象，只适合当「契约是否成立」的验收对象** —— 本轮正是后者。

## R19（2026-11-20）：v0.16 在大会语料上复跑 ESMO 2026 —— 30/30 卡面标识靠判读写出，一个 override 用在正当位上

**改了什么**：无（本轮是 v0.16 发布后的第二场验收跑）。R18 在 17 行的 ENA 上证明了「没有 `arms` 通道也能填满卡面」，但小会议无法证明**选择与排序**是否还站得住；这轮回到 **ESMO 2026（1097 条）**，与 R13（v0.12 同场）可比。

**对象**：`20261119-173236-cards-ESMO-26-v16`（thread `1ae47309`，turn `262d5ef6`，DeepSeek Flash + `--web`）。**墙钟 1376.5 s**，103 次工具调用（`execute`×30 / `read_file`×20 / `web_search`×17 / `task`×16 / `with-params`×9 / `write_file`×5 / `write_todos`×3 / `load_skill`×1 / `edit_file`×1 / `present_artifact`×1），reasoning 382302 tok。

| 验证点 | 实测 |
|---|---|
| 交付 | **30 卡，early/pivotal/failed = 10/10/10**，`output/watchlist.json` 唯一产物 |
| **`drug` / `target`** | **30/30 两张都非空**，全部由判读者从标题/摘要读出（本轮同样**没调** `clinical_result.arms`、**零手补**）：如 `sonesitatug vedotin (Sone-Ve) / CLDN18.2`、`intismeran autogene (V940) / 个体化肿瘤新抗原（mRNA）`、`izalontamab brengitecan (Iza-bren) / EGFR × HER3` |
| 交付前闸门 | `check_cards.py` **EXIT=0 `OK cards=30`** |
| 事实层 | **facts 29/29 · warn 1/1 → PASS**（`A-C1-heat-coverage` 4/12 命中，warn 级仍绿）、`A-P10` → `drug+target named on 30 card(s)`、`A-D2` → 8 切片 / 最大 150 ids / 双向零缺失 |
| runner 断言 | **24 PASS / 0 FAIL / 0 WARN**，`write_file` 零拒绝（R18 那次唯一的瑕疵消失） |
| `abstract_id` | **30/30 有号**（`LBA41` / `2680RO` / `791RO` / `2575P`），`A-F1` → `matches rows.json on 30 card(s)` —— **与 R18 的 ENA 空列对照，坐实那是数据侧缺口而非取数或渲染缺陷** |
| 三态 / 席位 / 顺序 | `is_recommand` 30 张中 1 张 `是`（LBA7 CLARITY-Gastric01）→ 强制位顶到 pivotal 首位（87 < 95 也照样第一，这是设计）；`A-P6` 377 条判读记录 + **1 条声明式 override**；`A-P9` 每试验 1 席 |
| override 是否正当 | 唯一一条：**放弃 LBA11（TroFuse-005，sac-TMT 治经治子宫内膜癌，88 分）**，理由写明「同适应症 + 已被 LBA71 的 TROP2 ADC 机制代表，按压同质只留一条，席位让给机制互补的 HER2 阳性一线方案」→ 属**选择理由**，不是数据缺失后门 |
| 诚实声明 | 4 条 `coverage_notes`：`is_recommand` 全场仅 1 条标星**已按强制位置顶**且「其余为空 ≠ 无人推荐」；`data_type` 判不出写「未判定」；`manual` 取不到记 null；非全量覆盖 |
| 复核页 | `dist/review/esmo2026-watchlist-v16.html`（30 卡 / 10/10/10）——药名 chip 与 phase / target 同排，左导按药名索引 |

### 与 R13（v0.12 同场）的可比变化

同为 30 卡 10/10/10，但这轮多了三件 v0.12 没有的东西：①**卡面标识（`drug`/`target`）全部有值**；②`abstract_id` 从「可能为空」变成逐卡可核；③override 从「隐式让席」变成**带理由的账本条目**（`A-P6` 已把 floors 与 override 一起判）。

### 留作下轮的两条观察（与 R18 同源，未改）

1. **「无分子靶点」类记录仍在用散文填 `target`**：本轮 failed 桶出现 `mFOLFIRINOX vs mFOLFOX6 / 无分子靶点（细胞毒化疗方案）`、`二十碳五烯酸 (EPA) / 无分子靶点（omega-3 脂肪酸）`，R18 的 `lifileucel / 肿瘤浸润淋巴细胞（TIL，非分子靶点）` 同理。三场累计 4 例 → 这已经**不是偶发写法而是稳定模式**：细胞毒方案、细胞治疗、omega-3 这类确实没有分子靶点。要么承认「`target` 允许一句类型说明」并写进契约，要么规定走 `field: "target"` 豁免 —— 两条都行，但现在契约里两种都没写，等于默许模型自选。
2. **`A-P4` 的桶内顺序在「强制位」存在时对读者是反直觉的**（pivotal 首条 87 分压在 95 分前面）。这是既定设计（`is_recommand` 是首位排序键），复核页上不印 `is_recommand` 也不印分数，所以读者看不出原因 —— 若以后要给读者看顺序理由，需另开一栏，不要在页面上复活徽章。

## R20（2026-11-20）：v0.17 首跑 ENA 2026 —— 回执闸门成立，条数闸门翻车

**改了什么**：v0.17（回执上限 `A-T3-reply-terse`）原地发布后，用同一句 prompt 重跑 ENA 2026，目的是确认**模型真只回三句**。

**对象**：`20261120-095523-ENA-26-v17`（thread `7d3f...` 系列新线程，DeepSeek Flash + `--web`）。**墙钟 299.1 s**，52 steps。

| 验证点 | 实测 |
|---|---|
| 发布态 | `entries=15 identical=15 differing=0` / `STATUS: in sync`（skill_id `230463cbc03d4fe5ba0e2e8964fe91dd`，共享 SP pin 未动） |
| **回执（本轮目标）** | **486 字 / 0 行表格 / 2 列表项**（v0.16 同场是 **3461 字 / 10 行表格**）→ `A-T3-reply-terse` **PASS** |
| 回执内容 | 条数（8 张，6/1/1）+ 两处真实缺口（凑不足 10 条的原因 / 本届多数 LBA 库内没有）+ 两条口径（`is_recommand` 整列为空、`abstract_id` 全空） |
| runner 断言 | **24 PASS / 0 FAIL** |
| 事实层 | **31/31 · warn 0/1 → PASS**（`A-D4` SKIP：全场无 `lba`） |
| `drug` / `target` | 8/8 两张都非空（`[212Pb]VMT-α-NET / SSTR2`、`LY4066434 / KRAS（多突变型）` …），仍全部由判读者从标题+摘要抽出 |
| **交付前闸门** | **FAIL：`size: 8 cards (expected a 10-30 item reading list)`** ← 本轮的真发现 |

### 归因：闸门缺陷，不是判读缺陷

`--rows` 重算出的候选池是 **early 14 / pivotal 2 / failed 1 = 17 条**（全库 17 条记录）。模型交 8 张、并已在
`coverage_notes` 第 5 条写明「三桶各 10 条无法凑足……故条数低于 10 条下限」。**闸门要求 10 张，而诚实交付是 8 张**：
同一份产物里，把 9 条弱记录硬凑成 10 张会让闸门变绿 —— 这正是「绝对下限」形状的缺陷（与 v0.11 的 `A-D2`
写死 ESMO 语料规模同源）。

### 修法（v0.18，用户拍板「每类 min 1 条」）

1. **桶是下限**：池里有候选的桶必须 ≥1 张卡 → `A-S5-bucket-presence`（ENA：`failed` 只有 1 条候选，仍出 1 张）。
2. **总数是上限 + 可声名的下限**：≤30 照旧；<10 张时 `coverage_notes` 必须点名「10」并说明语料填不满 → `A-S6-size-floor-declared`。

修后用**同一份 ENA 产物**复评：`check_cards.py` → **`OK cards=8`（EXIT=0）**，`facts 31/31 → PASS`。
不回归：ESMO 2026（池 357·86·374）/ ADA 2026 在两条新事实项上均 PASS。

### 留作下轮

- v0.18 待发布；发布后建议**再跑一场 ENA**（小语料，验「短清单合法」）与**一场大会**（验「不许少给」）。
- ENA 2026 的 `abstract_id` 仍全 null（数据侧缺口），`lba` 列全空 → `A-D4` 长期 SKIP，属会议能力 gating 的正常行为。

