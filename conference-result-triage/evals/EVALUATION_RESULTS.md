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

## 待测

- **R5 — v0.6 真实跑批**：本文的 12/12 是池内结论，不是榜单结论。发布 v0.6 后需重跑一次 E2E，目标 `facts 19/19`。
- 失败桶 vs 热度：阴性 query 两次 502，数据缺失，不给结论。
