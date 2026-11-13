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
