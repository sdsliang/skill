# R58 — 删除 facts 行分片配方（减法），原地发布 + n=3 实测

日期：2026-10-13 ｜ branch `v0.15-remove-html` ｜ commit `3518370`（实现+dist）→ 本文档 + 台账
前置：R57（`docs/evidence/r57-fact-row-sharding-and-field-subtraction-2026-10-12.md`）

## 1. 假设

R57 测出「按 ref 分片写 facts 行」这条**指令**在 4 refs 上 **0/3 被执行**，且唯一权衡过的一次（`r57b-shard-1`，16 段推理 / 7,746 字符）是**被我们自己文档里的竞争条款劝退**的，不是模型偷懒：

- 新加的是**许可**（"that is where sharding is a real speed-up"、"needs 3 or more refs"）；
- 同段里旧成本句仍在（"**never mandatory**"、"**Prefer straight-through scripting before delegating**…decide in one line and move on"），且 *one lane* 那条被当**代价**读 —— 原话：*"4 subagent round-trips (which also share the single execute lane)… doing it myself is cheaper and more accurate. The benefit is context bounding — but my context already holds the sources."*

**R58 假设（可证伪、可测的那个）**：既然这条配方（a）在被写成"默认"时也只有 ≤1/3 的运行会去权衡它，（b）权衡本身就要烧 reasoning，而（c）它的目标行为在 2–8 refs 这个真实档位上本来就不划算（facts 只占一轮 out token 的 10–13%，而 75% 是分不掉的 reasoning）—— **把它整条删掉，行为应当不变，而"权衡它的那一块推理"应当消失。**

预登记判据：① `tool-task` 全 0（行为不因删除而变，与 R57 同）；② **含 subagent/delegation 关键词的 reasoning part 数从 R57 的 1/3 降到 0/3**；③ 墙钟/out token 无超噪声的方向性劣化；④ 质量断言不回退（21 PASS / 1 FAIL 平台侧那条）。

## 2. 改动（净减法，不新增任何脚本）

删掉的文本：

| 位置 | 删掉的内容 |
|---|---|
| `SKILL.md:41` | facts 行分片整段（"one subagent per ref"/"send every task call in the same message"/"merge the shard files"），改为一句「facts 行在主线程写」 |
| `SKILL.md:33` | 脚本清单里 `merge_ref_facts.py` 的"used when 3+ refs are delegated" → "only if you chose to split" |
| `references/input-contract.md` | 工作流步 4 的分片从句；`## Large-batch delegation` 的 status 块（"**default for the fact rows once 3 or more refs are selected**"）；`### Delegating the fact rows (per ref) — the default split for 3+ refs` 整节（三步配方 + "Below 3 refs…"）；平台事实 6 的"fact-row split is measured and is the default" |
| `references/input-and-extraction.md` | "Writing the fact rows is the biggest block… so it is worth splitting" 整段 |
| `references/toolbox.md` | §2 标题的"(and merge the shards first)"、pipeline 里的 merge 行、§2a 的分片句、§3 标题与"Used when the fact rows were delegated"、token 语法节的"按 ref 分片时由 merge_ref_facts.py 合出来" |
| `system-prompts/…-v0.16.md` | 工作流步 1 的分片从句（"when 3 or more records are selected you should delegate the fact rows"）；委派段开头"Two different things are worth delegating"里的 fact-rows 分支；*Trigger* 的"Fact-row delegation needs 3 or more selected refs"；`Fact rows, one subagent per ref` bullet（整条） |
| `scripts/merge_ref_facts.py` | 模块 docstring 首句（改为"optional"，与 2a 的 `--scaffold` 同级） |

**保留（表里说清，避免以后误删）**：

- `scripts/merge_ref_facts.py` + `evals/scripts/test-merge-ref-facts.py` 16 例 —— 降级为**逃生口**（"a run that split the rows can merge with it; nothing in the workflow requires it"），与 `build_ledger.py --scaffold` 同一处理方式；
- `references/input-contract.md` 的 **`### Measured boundaries of the task tool`** 实测表（并发 28.9 s 重叠、四路 6.5 s 内起、单通道 `execute` 交接 2.8 s、子代理 `execute` 默认 30 s、无会话状态、turn usage 聚合子代理）—— 这是**事实**，防止未来重踩；
- **pull 委派（>5 esids）完全不动**：`task` 现在只有这一个用途，仍是可选、只做上下文控制、永不缩小来源集；
- `## Subagent delegation` 里的 "Try straight-through scripting before delegating" 保留 —— 删掉 facts 行分支后它只对 pull 生效，不再与任何东西互斥。

本地门禁：`test-skill-scripts` 62 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test-merge-ref-facts` 16 / `test-render-facts` 28 / `test_regressions` 35 / `test-runner` 41 / `test_pack_dist` 5 / `test_replay_run` 14 / node 8+8 / mutations **arm a 44/44 + arm b 12/12** = 全绿。

## 3. 发布（原地）

- `deps`：**unchanged since the recorded baseline**（3 skills / 18-param MCP / 16 built-in tools）。
- prompt：**v1.8 原地** —— 79,218 B `f293fb45f39e` → **78,155 B `6d507fb8fff7`**（**−1,063 B**，本地提示词文件 78,155 B）。
- skill：**v1.0.9 原地** —— dist 161,148 B → **160,567 B / 27 entries / sha256 `16f3bfce7130`**。
- 回读：`prompt deployed == local: True`（逐字节）、skill **27/27 identical**、`STATUS: in sync`。

## 4. 实测 n=3

输入 `/tmp/prompt-r53-4.txt`（4 esids → 4 refs），模型 `DeepSeek Flash`，web off，tag `r58-mainthread-{1,2,3}`，目录 `~/.local/state/toolsmith-runs/20261013-0932{56,56,58}-r58-mainthread-{1,2,3}`。

| run | wall s | out tokens | reasoning | steps | `task` | facts 行 | `records` | 断言 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| r58-mainthread-1 | 465.6 | 78,846 | 58,638 | 36 | **0** | 55 | 4 | 21/1 |
| r58-mainthread-2 | 404.9 | 68,126 | 56,381 | 25 | **0** | 48 | 4 | 21/1 |
| r58-mainthread-3 | 443.9 | 76,848 | 47,186 | 40 | **0** | 40 | 4 | 21/1 |
| **中位 / 均** | **443.9** / 438.1 | **76,848** / 74,607 | 56,381 | 36 | 0 | 48 | 4 | — |

基线（同 prompt、同模型）：n=8（R53-doc-4/4b/4c + R54-base-1/2 + R55-sub-1/2/3）wall 中位 **413.8**、out 中位 **70,983**、reasoning 中位 50,851；紧基线 `r55-sub-{1,2,3}` wall **405.4** / out **70,187**。
参照组 R57（配方在位、写成"默认"）：wall 中位 445.9、out 中位 78,248、reasoning 中位 62,868、`task` 0/0/0。

### 4.1 预登记判据逐条

| 判据 | 结果 |
|---|---|
| ① `task` 全 0 | **0/0/0 —— 与 R57 相同**（删除没有反向触发分片） |
| ② delegation 关键词 reasoning part | **R57：1/3 跑（`r57b-shard-1`，2 段 / 7,746 字符 / 占该跑推理 4.1%）；R58：0/3 跑（0 段）** —— 权重块消失，正是删除的目标 |
| ③ 墙钟 / out 无方向性劣化 | 墙钟中位 413.8 → **443.9 = +7.3%**（紧基线 +9.5%）；out 中位 70,983 → **76,848 = +8.3%**（护栏阈值 78,081，**未越线**；紧基线 +9.5%）。均在 ±20–40% 的同输入波动带内，且 R58（443.9 / 76,848）**低于 R57**（445.9 / 78,248）→ 无证据支持删除有害 |
| ④ 质量不回退 | 三跑各 **21 PASS / 1 FAIL**，唯一 FAIL 仍是平台侧 `tool_results receipts archived`；`records[]` 4 条、附录/图/时间轴齐全、报告 20,631 / 18,637 / 21,181 B、facts 55/48/40 行、**`source_file` 省略 143/143 行**（②减法未回退）、`--scaffold` 调用 0/0/0、`merge_ref_facts` 调用 0/0/0 |

## 5. 判定：**KEEP（删除生效，代价不可测）**

- **目标行为达成**：那条"付了推理却没产出行为"的指令连同权衡它的推理块一起消失（②判据 1/3 → 0/3）。
- **指标上无法证明任何收益**，也**无法证明任何损害**：n=3 中位数检不出 <20% 的效应，而本次改动的量级（−1,063 B 提示词、少一个工具权威**不再需要**的脚本说明）本来就落在噪声里。与 R57 相比 wall −0.4%、out −1.8%。
- **保留的账**：`merge_ref_facts.py` 与其 16 例测试留在包里（不产生运行时成本：模型不会调用它、也不会读它的源码），`task` 实测边界表留作事实基线。
- **对 ①（分片）的最终结论**：不再重试。R57 已证 4-refs 档位下模型（正确地）不需要它；要做也必须在 ≥6 refs 且 registration-class 重载荷的档位上另开一轮，且**先删**任何与之竞争的成本句（R57 方法论沉淀）。

### 我方能改的

- **R58-1（已改，已成事实）**：上表 7 处文本删除，`EXPECTED` 仍 27（脚本保留）。
- **R58-2（记账，观察项）**：三跑的 `steps` 离散度变大（36 / 25 / **40**）、`execute` 12–16、`read_file` 8–16。`r58-mainthread-3` 出现一次 **`execute` 参数名拒绝**（`['command'] Field required; ['shell_command'] Extra inputs are not permitted`，框架已自动重发成功）—— 与 O51 同源，属平台工具 description 与实际参数名不一致，非本轮改动引入，**仅记账**。
- **R58-3（未做，待议）**：`read_file` 16 次里含 `ls`、`grep` 与多次 `sed/grep` 式探查（`toolbox.md` offset 100 limit 230 一次、`chart-templates.md`、`conclusion-language.md` 各一次）。若下一步还要找杠杆，应量**主线程探查次数**而不是再动 facts/rules —— 但这需要先有 tool start/end instrumentation，当前不可测。

### 平台侧（转开发）

- **P-R58-1（承接 P-R57-1，本轮未复现）**：本轮三跑同期启动、全部 `succeeded`，未出现 `idle` 无 `completed_at` 的卡死。旧单仍有效（同一时段/负载下会发生），维持观察。
- **P-R53-1（已知，每次命中）**：`tool_results receipts archived` —— `/workspace/tool_results/…/result.jsonl: unsafe or unsupported receipt path`，三跑均 `[FAIL]`，与本批改动无关，不影响产物。
- **P-R58-2（新，轻）**：`execute` 的参数名拒绝在 live 跑里可复现（R58-3 那次），框架自动重发后成功、但被 runner 记入"arguments refused"清单。属工具 description 与 schema 命名不一致，建议对齐（同 O51 记录）。
- P-R56-1~4 仍在（沙箱单通道 / 子代理 `execute` 默认 30 s / `data-subagent-trace` 未文档化 / 平台无「工具串行、生成并行」提示）。
