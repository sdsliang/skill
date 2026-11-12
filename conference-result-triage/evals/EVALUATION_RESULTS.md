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
