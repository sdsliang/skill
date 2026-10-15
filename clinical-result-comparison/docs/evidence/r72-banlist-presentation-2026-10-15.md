# R72：禁令「呈现方式」——枚举清单 → 语义判据 + 三形态 + 指针

日期：2026-10-15 · 分支 `v0.15-remove-html` · 承接 R71（`a63ba51`）
用户授权：*“现试下A吧，救不回来的话就B”* → 本轮 *“原地”*（skill v1.0.9 原地更新）
判定：**KEEP（五条预登记判据全中）**；这是 R67 之后**第二次**主判据真正归零，且**辅判据命中里已无禁令词**。

---

## §0 纪律与预登记

预登记写于改前（`AGENTS.md` §「R72 预登记」），单变量 = **禁令在常读路径的呈现方式**；**禁什么没变**、门禁正则 / 断言集 / `templates/` 一行未动。

| # | 判据 | 预登记目标 | 改前基线 | 实测 | 结论 |
|---|---|---|---|---|---|
| 1 | 主判据（`r71-metric.py`，图表原因仲裁句） | ≤ 2 句 | R71 = 4（0/2/2）；R70 = 7 | **0 句**（0/0/0）；每 10 万 reasoning 字符 **0.0**（R71 0.7、R70 1.4） | ✅ |
| 2 | 辅判据（`r70-metric.py`，BAIT×疑问） | ≤ 10 句 | R71 = 19；R70 = 13 | **5 句**（4/1/0）；每 10 万字符 3.0 / 0.5 / 0.0 | ✅ |
| 3 | 产物零禁词（`r72-artifact-scan.py`，门禁自己的正则） | 0 | 0 | **0 / 0 / 0** | ✅ |
| 4 | 不得拿返工换分：steps 均值 ≤ 33 且 out_tok 均值 ≤ 160k | — | R71 30.7 / 152,628 | **28.3 / 90,324**（21/39/25；61,218/103,098/106,657） | ✅ |
| 5 | 断言 22P/1F（唯一 FAIL = 平台 `P-R53-1`）+ 离线 4 组 ≥ 23/44 | — | R71 22P/1F；22/44 | **22P/1F ×3**；离线 **23 / 25 / 24** | ✅ |

判定规则（改前写下）：主 ≤2 且辅 ≤10 且产物零禁词且成本不超且 5 不劣 ⇒ KEEP；主 ≥4 或产物出现禁词或 steps 均值 > 40 或离线 < 22 ⇒ **B（`git revert` R71+R72）**。⇒ 走 KEEP，不需要 B。

---

## §1 改前红证据：复述源到底是哪一处清单

新脚本 `docs/evidence/r72-recitation-source.py` 把「一行里堆 ≥6 个禁词」判为复述句，再把句中出现的禁词与 **HEAD（改前）两处清单**做集合召回：

```
改前两处清单各自出现的禁词数：
  SKILL.md（硬规则段，改前）: 21/32
  toolbox.md（FAIL 条目，改前）: 30/32

r71-18: 复述句 2 条
  • 28 个禁词，召回 {SKILL.md: 21, toolbox.md: 27}
r71b-4: 复述句 1 条
  • 9 个禁词，召回 {SKILL.md: 5, toolbox.md: 9}
```

⇒ 模型逐字复述的是 **`references/toolbox.md` 的 28 词枚举**（模型按装载契约「`toolbox.md` read it once per run」读它），`SKILL.md` 只是它的子集。**只压 SKILL.md 不管用**——这是本轮最关键的取证。

（`r70-4` 的思考通道里更直白：*"the banned list in the skill is a set of common…"*，随后逐词点名 28 个 token。）

## §2 改动（两处，13 行）

| 文件 | 改前 | 改后 |
|---|---|---|
| `skill/…/SKILL.md:197` | 枚举 ~13 个自述标签 / 自指 / 内部词 / 自证尾巴 | 判据（**语义**：在写「我们怎么做的」而不是「材料说了什么」就拒）+ **3 个典型形态**（`选择依据`／`全部通过`／`部分对齐`／`payload`）+「**不要背清单**」+ 指向 `toolbox.md` 与 `check_report.py` |
| `skill/…/references/toolbox.md`（FAIL 条目 + R70 FAQ） | 28 词枚举 + 5 词枚举 | 同样压成 3 个示例 + **保留** R70 的「永远合法材料属性词」清单（`成熟度`／`证据强度`／`判断强度`／`解读边界`／`组内证据关系`／`归属组`／`归组依据`／`可比性`）+「门禁命中时会点名该词」 |

保留件：`check_report.py` 自身输出未动（命中仍逐条点名）、`templates/` 的合法列名说明（R70）、R71 那句「不画图的原因写成材料限制、不做成自述列名」（示例词 `不绘图原因` 仍在禁令语境里，是 R71 的成果）。

断言不变由 R69 的 4 个测试守住：`PackagedTreeVsGateVocabularyTests` 只要求「门禁词汇只许出现在禁令段落内」，**不要求清单存在** ⇒ 压缩合法（`test-check-report.py` 31 OK）。

## §3 顺带结案：R72-1（`本次` WARN）= **非缺陷，不改**

`r71b-4` 里模型写出正文限制句后被 `check_report.py` 判 `本次` 自指 WARN，随即整句重写。查证：

* `SELF_REFERENCE_RE`（`check_report.py:75`）+ `warnings.append(f"the report refers to itself …")`（`:216`）是**设计内的 WARN（A-P10）**，且 **WARN 从不改变退出码**（`:16` / `:483`：只有 FAIL 才 fail closed）；
* 模型 msg29 原话：*“The WARN is not a failure (exit 0), but let me fix it for quality”* —— 它是**主动按质量改**，不是被误导；
* 改后「本次检验的成熟度」→「该终点当前的事件成熟度」**确实更好**，成本 ~1 步。

⇒ 属于「我方能改、但证据显示不必改」的项，按纪律**不动**（不凭感觉改规则）。

## §4 发布（原地）

* `deps`：`DEPS: unchanged since the recorded baseline`（上游技能 / MCP / 16 内置工具无变化）。
* skill **v1.0.9 原地更新**：`skill_id 16aeb0406e12425bad27a2444f17225e` 不变，`2026-10-15T15:59:46`；dist **29 entries / 185,910 B / sha `4f837df865b4`**（R71 为 186,041 B / `9497a814b125`）。
* 回读：`zip entries=29 identical=29 differing=0 missing-locally=0`、`skill deployed == local tree: True`、`prompt deployed == local: True`（prompt v1.8 `bytes=81876 sha=ec562b525b64` 未动）、`STATUS: in sync`。
* 本地闸门：**`GATES_FAILED=0`**（13 套：`py_compile` / `test_regressions` / `test-check-report` 31 / `test-render-facts` / `test-build-ledger-scaffold` / `test-merge-ref-facts` / `test-skill-scripts` / `test-tell-scan` / `test-runner` / `verify-run-chain` GATE PASS / `test_pack_dist` / `test_replay_run` / `mutations` / `node --test`）。

## §5 真跑（固定协议：4 / 18 / 14，串行，web off，`DeepSeek Flash`，输入与历史 12 跑逐字节相同）

| run | dir | wall s | 步 | out_tok | reasoning tok | 断言 | 主判据句 | 辅判据句 |
|---|---|---:|---:|---:|---:|---|---:|---:|
| `r72-4` | `20261015-155953` | 332.2 | 21 | 61,218 | 46,339 | 22P/1F | 0 | 4 |
| `r72-18` | `20261015-160542` | 558.2 | 39 | 103,098 | 64,210 | 22P/1F | 0 | 1 |
| `r72-14` | `20261015-161527` | 546.9 | 25 | 106,657 | 68,825 | 22P/1F | 0 | 0 |
| **均值** | | **479.1** | **28.3** | **90,324** | 59,791 | | **0**（R71 4、R70 7） | **5**（R71 19、R70 13） |

* 三跑唯一 FAIL 同形 = 平台 `P-R53-1`（`tool_results receipts archived`），与 R67–R71 十五跑一致 ⇒ **断言集未变、无新 FAIL 类**；`outcome=succeeded`（durable `completed_at` + 无 `error_type`）。
* **复述句 = 0 条 ×3**（`r72-recitation-source.py`；R71 有 2 条 28 词 / 9 词）⇒ 机制成立：清单没了，就没有可逐字复述的东西。
* **墙钟口径（§8）**：本批 332–558 s，R71 同口径为 538–1487 s；但 R71 同期 `out_tok` 也高（99k–210k，均值 152,628），**本批的成本回落主要由平台吞吐漂移解释**，R72 自身 `out_tok` 均值 90,324 与 R70（85,010）同级。⇒ **不称提速**；只能说「成本未因本次改动上升」。
* `steps` 均值 28.3 达标，但 `r72-18` 单跑 39 步（高于 R71 最高的 33）——**诚实记下**：均值判据过，单跑离散未消除。

## §6 判定与归因

**KEEP**。归因（有对照，不是推测）：
1. 主判据从 4 → **0**、辅判据 19 → **5**，且辅判据的残余触发词**全是合法材料属性词**（`成熟度`×4、`可比性`×1、`判断强度`×1）——**一个禁令词都没有**（R71 残余里含 `不绘图原因`×2 / `部分对齐`×2 / `可比性结论`×2 / `不具备绘图条件`×2 / `选择依据`×1）。争议对象从「我们的词表」换成了「材料的含义」。
2. 复述句 0/0/0：这是 §1 指出的机制的直接后果（枚举移到「门禁命中才点名」）。
3. 无反向代价：产物门禁词命中 0/0/0（判据 3），离线 23/25/24 不劣（group-4 = 23 ≥ R70 的 23 > R71 的 22），断言集未变。

**边界（不吹）**：n=3 单批；`steps` 单跑离散仍在（39）；本批平台较快，故墙钟不能与 R71 直接相比。

## §7 R73 候选（按价值排序）

1. **`r72-4` 的 4 句辅判据全是 `成熟度`** —— 看是否是「模板里同时出现 `证据成熟度与限制` 列名与 `成熟度` 判据」引起的**同一词**反复自问；若是，属可压的纯噪声（下一轮先只取样本定性，不直接改）。
2. **离线 `A-W1-dose-mapping` 长期 0/1（三跑 + 历史全批）** —— 剂量映射那条 WARN 从未通过；确认是场景 a 的 fact 定义与产物形态不匹配，还是真实缺漏（属评测口径问题，先判定再动）。
3. **`results.tsv` 记账口径**（R72-4 起挂账）：4/18/14 不在冻结 A/B 场景集 ⇒ `tools/replay-run.py --score` 一律 `scenario=unknown`；给三组建场景定义，或改「按组记」口径。
4. **R69 门禁测试只扫 skill 树、不扫 `system-prompts/`**（R71 起挂账）——本轮改的 `SKILL.md`/`toolbox.md` 在扫描面内，prompt 不在；把 prompt 纳入静态扫描面。
5. 保留项：P1/P2（`templates/same-trial-evolution-report.md` 孤儿、`references/input-contract.md` + `toolbox.md` 缺 `## Contents`）。
