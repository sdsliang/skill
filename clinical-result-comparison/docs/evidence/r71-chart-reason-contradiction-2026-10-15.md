# R71 — 「不画图的原因写在哪」：我们自己两处口径打架（2026-10-15）

**一句话**：`prompt` / `SKILL.md` / 两个 `references` 共 **5 处**教模型「不出图就在**表格**里说明原因」，
而 `scripts/check_report.py` 恰好把 `不绘图原因` 这个形态判 **FAIL**，`cross-trial-comparison.md` 自己又写
「**never** a `不绘图原因` label … as part of the prose」。R71 把这 5 处统一成「原因写成材料/数据的限制，
放在正文或表内**已有的材料属性列**里，不要做成自述列名或标签」。

**判定**：真矛盾修掉了（改前红证据 5/5 可复现，被门禁视角证明），**但预登记的三条判据都没达标**
（主 4>3、辅 13→19 回升、离线 22<23）⇒ **本轮不称任何改善**，是否保留交用户裁定（建议保留，理由见 §6）。

---

## §0 纪律与预登记（**判据在改之前已写入 `AGENTS.md`**）

- 单变量：只改「图表原因写在哪」这一处口径（**不加功能、不动门禁正则、不动断言集**）。
- **主判据**（`docs/evidence/r71-metric.py`：思考通道按句判定，同句同时命中「图表原因词」
  `不绘图原因|无法绘图|不出图|不画|没画|未画|why no … chart|no quantitative chart` 与「疑问标记」）：
  **改前基线（同一脚本量 R70 三跑）= 7 句（4 / 2 / 1）** ⇒ **目标 ≤ 3 句**，且 `r71-4` ≤ 1。
- **辅判据**：R70 的主判据（`docs/evidence/r70-metric.py`）**不得回升**，即 ≤ 13 句。
- **断言**：维持 22P/1F（唯一 FAIL = 平台 `P-R53-1`），断言集不得改写。
- **成本**：按 `AGENTS.md` §8 同时列 `wall` + `out_tok`，不宣称提速。
- **判定**：≤3 → keep；4–7 → 噪声内不称改善；>7 或 R70 判据回升 → discard 候选。
- **回退**：断言集变化 / 新 FAIL 类 / 离线分（`--scenario a`）低于 `r70-4` 的 **23/44** ⇒ 回退。

## §1 改前红证据：这确实是「我们自己教模型写会被判 FAIL 的东西」

`git show HEAD` 逐文件计数（改前 → 改后）：

| 文件 | 改前 | 改后 |
|---|---:|---:|
| `skill/.../SKILL.md` | 1 | **0** |
| `skill/.../references/chart-templates.md` | 2 | **0** |
| `skill/.../references/cross-trial-comparison.md` | 1 | **0** |
| `system-prompts/multi-clinical-result-comparison-v0.16.md` | 1 | **0** |

改前原文（5 处）：

- `chart-templates.md:33`「某组不满足可比条件则该组不出图，**并在表格说明原因**。」
- `chart-templates.md:35`「任一条件不满足 → **只出时间轴**，并**在正文/表格说明不出定量图的原因**（数值不可比 / 只有单个数值 / 人群不同）。」
- `cross-trial-comparison.md:157`「Groups that do not meet the compatibility conditions get no chart, **and the reason is stated in the table**;」
- `SKILL.md:191`「groups that fail the compatibility conditions get no chart (**reason stated in the table**).」
- `system-prompts/…v0.16.md`「otherwise draw the timeline only and **state in the table** why no quantitative chart is drawn (values not comparable / a single value only / different populations).」

**门禁视角证明这是真矛盾**（`importlib` 载入门禁自己的正则，喂「按改前指令会写出来的那一行」）：

```
输入: "| 组 | 不绘图原因 |\n- 不绘图原因：数值不可比\n"
META_COLUMN_RE 命中: True
META_LABEL_RE  命中: True          ← 照改前指令写 = 交付失败
```

**真跑里模型逐字仲裁过这一处**（R70 `r70-4` 思考通道原文）：
*“Wait — 「state in the table why no quantitative chart is drawn」 — that's a self-narration label (`不绘图原因`
is banned as a column name!).”*

## §2 改动（单变量）

统一口径，措辞一致地落到 5 处：**原因写成材料/数据的限制**（数值不可比 / 只有单个数值 / 人群不同），
**放在正文或表内已有的材料属性列**里；**不要**做成 `不绘图原因` / `无法绘图` 这类**自述列名或标签**
（`check_report.py` 判 FAIL）。prompt 侧为对应英文（含 `` `check_report.py` fails those ``）。

`check_report.py` 正则、断言集、`templates/` 结构**一行未动**。

## §3 控制组

- 被禁词在新旧文本下的行为不变：改后 `不绘图原因` 只出现在**禁令语境**（`不要`/`never`），
  本地 `test-check-report.py`（31 项，含 `PackagedTreeVsGateVocabularyTests` 4 项）**全过**。
- 门禁正则对三个被改文件的命中**全部来自改前既有行**（`SKILL.md:197` 禁令清单、`chart-templates.md:91/95`
  「工作区」、`cross-trial-comparison.md:72` 内部分类段），**没有一条来自 R71 新增句子**（逐条打印核对过）。
- 发布后平台侧读回：`instructions` 里 **0** 处 `state in the table why no quantitative chart`、
  新句 1 处；平台包与本地树 `diff -r` **全等**。

## §4 发布（用户在发布前明确授权「**原地**」）

- `deps` = unchanged since the recorded baseline；`publish` **原地更新**：
  prompt **v1.8** 内容被替换（`bytes=81876 sha=ec562b525b64`，deployed == local: True）、
  skill **v1.0.9** 原地更新（`skill_id 16aeb0406e12425bad27a2444f17225e` 不变，`2026-10-15T13:50:24`）。
- 回读：`zip entries=29 identical=29 differing=0 missing-locally=0`，`STATUS: in sync`；
  平台 `deployed-current.zip` 解包后与本地树 **逐字节相同**；dist **186,041 B / sha `9497a814b125`**。
- 闸门：`py_compile` / `test_regressions` 35 / `test-check-report` 31 / `test-render-facts` /
  `test-build-ledger-scaffold` / `test-merge-ref-facts` / `test-skill-scripts` / `test-tell-scan` /
  `test-runner` / `verify-run-chain` GATE PASS / `test_pack_dist` 5 / `test_replay_run` 14 /
  `mutations` a 44/44 b 12/12 / `node --test` 16 → **`GATES_FAILED=0`**。

## §5 真跑（固定 4/18/14，串行，web off，输入逐字节复用）

输入在 `/tmp` 被系统清空后**从历史 run 目录还原并校验**：`p4/p18/p14` 与历史 12 跑
（R67/R68/R69/R70 各 3 跑）`cmp` **逐字节相同**（md5 `f25cd1fe2fbde3b0b9ac150455a7fceb` / `535475736ece88f9…` / `1dafa93fe09dc28a…`）。

| run | 目录 | wall s | 步 | **out_tok** | reasoning tok | 断言 | 主判据句 | R70 辅判据句 |
|---|---|---:|---:|---:|---:|---|---:|---:|
| `r71b-4` | `20261015-145135` | 1378.0 | 32 | 148,786 | 116,316 | 22P/1F | 2 | 11 |
| `r71-18` | `20261015-135928` | 1486.8 | 27 | 209,910 | 154,712 | 22P/1F | 2 | 8 |
| `r71b-14` | `20261015-151442` | 538.2 | 33 | 99,187 | 72,983 | 22P/1F | **0** | 0 |
| **均值** | | **1134.3** | 30.7 | **152,628** | 114,670 | | **4 句** | **19 句** |

**⚠️ 本批的平台混杂因素（必须先说，否则所有绝对数都读不得）**

1. **首次 `r71-4`（`20261015-135204`）判 `inconclusive`**：turn 行在 `/timing` 里 `completed_at=None`
   （`total_latency_ms=0`），工具按 P7 口径拒绝承认验证；`messages.json` 有 724 KB 内容但不算数 ⇒ 重跑为 `r71b-4`。
   同批 `r71-14`（`20261015-142425`）被我自己的 `timeout 1500` 掐断（当时单跑已 >1500 s），同样重跑为 `r71b-14`。
2. **平台产出量整体翻了 ~1.8–2 倍**：本轮 out_tok 均值 **152,628**（R70 85,010）、reasoning 均值 **114,670 tok**
   （R70 58,074）；wall 均值 **1134 s**（R70 425 s，其中 638–782 s 是建线程/落盘/收尾，生成只占 43–96%）。
   同一输入、同一份 skill，**吞吐只有昨天的一半左右**，且有 2 跑需要重跑。
   ⇒ 按 `AGENTS.md` §8，**本批与历史批次的 wall / token / 绝对句数不构成可比口径**。
3. 三跑唯一 FAIL 同形 = 平台 `P-R53-1`（`tool_results receipts archived`），与 R67–R70 十二跑一致 ⇒ 断言集未变、无新 FAIL 类；
   文体门禁 `SCAN_EXIT=[0] strong-free=True`；`outcome=succeeded`（durable `completed_at` + 无 `error_type`）。

**主判据明细（`r71-metric.py`）**

| | 绝对句数 | reasoning 字符 | 每 10 万字符 |
|---|---:|---:|---:|
| R70 基线（4/18/14） | **7** | 506,684 | **1.4** |
| R71（4/18/14） | **4** | 603,723 | **0.7** |

残留 4 句的归类（逐句读过）：**2 句 = 整张禁令清单逐字复述**（`r71-18` 1 句、`r71b-4` 1 句；这类在 R70 也在）、
**2 句 = 仍在问「按新写法写出来的这句话算不算标签」**（`r71-18`：「state why the data can't support a chart
（"两项试验的终点与人群不同，无法平行绘制"）— hmm, that phrasing risks the banned …」；`r71b-4`：「that borders
on self-narration ("不绘图原因" is banned)」）。**目标类别（照旧口径的仲裁）确实少了，但没有清零。**

**辅判据明细（`r70-metric.py`）—— 回升 13 → 19，逐句归类后只有 ~2 句可归因本轮**

| 类别 | R70 | R71 | 说明 |
|---|---:|---:|---|
| 念禁令清单 | 3 | 3 | 既有类别（`r71-18` 1 + `r71b-4` 1，另 1 属部分） |
| 读模板列名被计入（`证据关系`/`解读边界`，MARK=`Hmm`） | 0 | 2 | **度量口径弱点**：读列名 ≠ 仲裁，`Hmm` 作疑问标记太松 |
| `成熟度`/`可比性` 在正文里算不算标签 | 4 | 3 | R70 也有（`成熟度×4/3`），部分既有 |
| 照旧口径的图表原因仲裁 | 7 | 4 | **本轮目标类别**（主判据） |
| **新：`本次` 触发门禁 WARN 后的返工** | 0 | **2** | 见下，**本轮新发现** |

**新发现（R72 候选①）**：`r71b-4` 写出「…意味着该终点当前的**事件成熟度**低于原设计预期」这类**正文材料限制句**后，
`check_report.py` 因 `本次` 触发 **WARN（自指）**，模型随即整句重写（`check_report WARN: the report refers to
itself ('本次')`）。注意：**R70 刚写进 `SKILL.md` 的指引是「FAIL 才改、WARN 不是失败」，模型没照做**——
说明「WARN 不阻塞」这条指引需要更强的表达（或门禁需把自指 WARN 的语义讲清）。

**交付层 / 离线**

- 三跑产物（`artifacts/`）中 `不绘图原因|无法绘图|对齐等级|分析模式|选择依据|可比性结论|有限并列原因|处理模式|判断强度|证据成熟度与限制` 命中 **0**（干净）。
- 本地 `check_report.py` 回放三份产物：仅报已知本地 `::visualization` 前缀差异（R50 起已知）。
- 离线 `evals/fact-check/check.py --run … --scenario a`：`r71-18` **24/44**、`r71b-4` **22/44**、`r71b-14` **29/44**。

## §6 判定：**预登记三条判据全部未达标 ⇒ 不称任何改善**（是否保留交用户裁定，建议保留）

| 预登记判据 | 目标 | 实测 | 结论 |
|---|---|---|---|
| 主判据（图表原因仲裁句） | ≤ 3 句 | **4 句**（2/2/0；归一化 1.4 → **0.7** 每 10 万字符） | ❌ **未达标**（落在「4–7 噪声带 ⇒ 不称改善」） |
| 辅判据（R70 主判据） | ≤ 13 句 | **19 句**（2.6 → 3.1 每 10 万字符） | ❌ **回升** ⇒ 预登记的 discard 触发条件命中 |
| 回退（离线分） | ≥ 23/44 | `r71b-4` **22/44**（`r71-18` 24、`r71b-14` 29） | ⚠️ **低于基线 1 分** ⇒ 回退条件字面命中 |
| 断言 | 22P/1F、无新 FAIL 类 | 22P/1F ×3，唯一 FAIL = `P-R53-1` | ✅ 维持 |

**为什么仍建议保留（不撤）**：本轮修的是**我们自己文本里的真矛盾**——改前 5 处教模型写出的形态，
被门禁正则**当场判 FAIL**（§1 可复现），撤回去等于把这个矛盾重新装回去；而三条未达标的量级都极小
（主判据差 1 句、离线差 1 分、辅判据在平台产出翻倍下按字符归一化只升 19%，且逐句归类只有 ~2 句可归因本轮）。
这与 R69 的先例一致：**真错修掉、被测试钉住，但不声称减负/提速**。

**必须先说清的度量教训（写进 R72 前提）**：

1. **绝对句数在平台吞吐波动下不可比。** 本轮 out_tok 1.8×、reasoning 1.8–2×、wall 2.7×。
   以后拿句数做判据，**必须同时给「每 10 万 reasoning 字符」**，或**带一次对照重跑**（用上一轮同一份代码）。
2. **`r70-metric` 的 BAIT×MARK 口径太松**：`Hmm`/`Wait` 作疑问标记会把「读模板列名」也算作仲裁（本轮 2 句）。
   改法：疑问标记限定为「判定性提问」（`banned|is that|合法|算不算|门禁|check_report|FAIL|risks|borders on`），
   并把 BAIT 里的模板列名单独一类报告。
3. **`r71-4` 的 `inconclusive` 是本轮新见的失败模式**（turn 行无 `completed_at`、`total_latency_ms=0`，
   但有 724 KB `messages.json`）：按 P7 口径不能算验证，**重跑成本 20 分钟起** ⇒ 长跑批次要预留重跑预算。

## §7 下一轮（R72）候选

- **R72-1（首选）**：`check_report.py` 的 `本次` 自指 **WARN** 触发正文重写（`r71b-4` 实证）。
  要么把「WARN 不阻塞」写得更硬（给一个具体反例：本次这种句子是合规的、不必改写），
  要么在 `toolbox.md` 里直接给「正文里写材料限制」的合规模板句（避开 `本次`/`本报告`）。
- **R72-2**：禁令清单的**逐字复述**仍占主判据残留的一半（R70 4 次 / R71 2 次）⇒ 试着把清单从「列举」压成
  「判据 + 一个脚本入口」，或把清单挪出常读路径（`toolbox.md`）而在硬规则段只留判据。
- **R72-3（度量）**：按 §6 的 3 条教训改口径：句数必须以「每 10 万 reasoning 字符」并列；疑问标记收紧；
  BAIT 分两类（模板列名 vs 禁令词）；**并在平台吞吐明显漂移时强制跑一次对照**。
- **R72-4（记账）**：`results.tsv` 自 R52 起未追加（4/18/14 不在冻结 A/B 场景集 ⇒ `--score` 记 `unknown`），
  需用户定口径；本轮三跑的 commit / `deployed_sys_sha` / 输入 md5 已齐，随时可补。

**证据脚本**：`docs/evidence/r71-metric.py`（主判据，含归一化列）、`docs/evidence/r70-metric.py`（辅判据，含归一化列）。
