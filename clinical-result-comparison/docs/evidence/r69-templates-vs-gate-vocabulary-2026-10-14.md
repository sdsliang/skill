# R69 — 清扫 `templates/` 里被门禁拒收的词汇 + 静态测试扩到整棵打包树（2026-10-14）

**触发**：R68 §5 的第 1、2 条（R68 自己就是漏扫 `templates/` 才留下这一半）。R68 的 `r68-18` 逐字：
*"The mixed template's section 4.3 column header 「解读边界」 with values 直接对齐/部分对齐/仅背景相关/未对齐 — those clash with the host prompt's ban on 「部分对齐」"*、
*"`处理模式` with values 跨试验/同试验演进 — that's a self-classification. Risky!"* —— 那一跑为此烧掉 41 次合法性推理。

---

## 0 预登记（真跑之前写下，2026-10-14）

**主判据（继承 R68-3 的度量，口径本轮固定）**：`r69-18`（R68 里最重的一跑）的**模板词汇合法性推理**必须显著低于 `r68-18`。
度量口径（脚本 `/tmp/r69/metric.py`，对三类 run 目录的 `messages.json` 中 `type=reasoning` 的 part 做：
`template-vocab = 处理模式|直接对齐|部分对齐|仅背景|未对齐|对齐等级`，`gate-check = check_report.py|FAIL list|banned|self-label|class label`；
「次」= 命中总数，「字符」= 含命中的整块思考字符数）。**基线按同一口径重算**（R68 文档里的 `24.9k 字符` 用的是更窄的字符口径，不可比，故本轮一律用本口径）：

| 代 | run | template-vocab | gate-check | 合计 | 字符 |
|---|---|---:|---:|---:|---:|
| R67 | `r67-4` / `r67-18` / `r67-14` | 2 / 14 / 14（均 10.0） | 26 / 22 / 24（均 24.0） | 28 / 36 / 38 | 121.8k / 91.4k / 153.8k |
| R68 | `r68-4` / `r68-18` / `r68-14` | 0 / **23** / 14（均 12.3） | 4 / 28 / 10（均 14.0） | 4 / 51 / 24 | 77.0k / 169.2k / 55.9k |

- **预登记目标**：`template-vocab` 三组全部降到 **0**（模板不再教那些词，模型没有可仲裁的对象）；`r69-18` 该项必须 **≤ 2**（对照 `r68-18` 的 23）。
- **不得劣化**：三跑断言恒 **22P/1F**（唯一 FAIL 仍应是平台 `P-R53-1`）；产物齐全；`自产物回读/返工` 不高于 R68（0 / 14.3 / 0.9 s）；`check.py` 离线判分不低于同组 R68 基线。
- **撤的条件（kill criterion）**：任一组断言集变化（不再是 22P/1F）、出现新的 FAIL 类别、或离线判分下降 ⇒ 回退本轮模板改动。
- **不可宣称**：墙钟 / out tok / 步数。单跑离散 ±30%（R63-0），R67 434.7 s → R68 473.7 s 这种 1σ 级差异一律记为「噪声内」。

---

## 1 改了什么

| 文件 | 改动 | 依据 |
|---|---|---|
| `templates/mixed-comparison-report.md` | ① 表头 `处理模式` → **`组内证据关系`**，并在表下加一段说明：该列写**材料之间的关系本身**（时点/人群/定义/评估口径/方向），**不要**写成对本次分析做法的归类；② 第 70 行示例单元格 `直接对齐/部分对齐/仅背景相关/未对齐` → `评估时点与人群定义不同，只作方向性并列`；③ 边界句 `只解释直接或部分对齐的终点` → `只对同一终点定义、同一评估口径的观察作并列解读`；④ 修表格分隔行与表头列数不符（`:31` 分隔 5 列 vs 表头 4 列；`:71/:73` 行 9 列 vs 表头 8 列） | `check_report.py:55 META_LABEL_RE`（`处理流程`/`分析模式`…）、`:59 META_COLUMN_RE`、`:62 METHOD_NARRATION_RE`（`(?:部分\|直接\|仅背景\|未)对齐`），以及 host prompt v0.16 第 39 行同款禁令 —— 三条都是 FAIL |
| `templates/cross-trial-report.md` | 示例 `直接对齐数据等` → `同一终点与人群下可直接比较的数据等`；修 `:67` 分隔行列数（5 vs 6） | 同上 |
| `evals/scripts/test-check-report.py` | **扫描范围从 `references/` 扩到整棵打包树**（`SKILL.md` + `references/*.md` + `templates/*.md` + `templates/charts/*.json`，`packaged_texts()`）；**直接用 `importlib` 加载 `check_report.py` 取它的正则对象**（`REPORT_VOICE_REGEXES` / `FULL_GATE_REGEXES`），断言不再与门禁漂移；新增 `TEMPLATE_COLUMN_BAN`（含 `处理模式`）；新增 `PackagedTreeVsGateVocabularyTests` 4 项：`test_report_voice_lexicon_appears_only_inside_prohibitions`、`test_templates_name_the_full_gate_lexicon_only_inside_prohibitions`、`test_templates_have_no_self_classification_column_or_cell`、`test_the_scanners_themselves_fail_on_the_r68_template_text` | R68-2（纪律）：扫描范围必须覆盖整棵打包树 |
| 同上（方法论） | 「禁令豁免」判定从 ±N 字符窗口改为**段落作用域**（`_paragraph_span()`：以空行分块）。窗口法会把第 73 行的 `不得` 漏给第 70 行的表格行 —— 那正是 R68 的漏网形态 | 本轮先行验证：窗口版对新测试**放过了**那一行 |

**改前（HEAD）红证据**（新测试对改前文本的运行结果，证明是回归测试不是橡皮章）：

| 扫描对象 | `REPORT_VOICE_REGEXES` | `FULL_GATE_REGEXES` | `TEMPLATE_COLUMN_BAN` |
|---|---:|---:|---:|
| HEAD 的整棵打包树 | **5** 处 | **5** 处 | **1** 处（`处理模式`） |

命中详情：`templates/cross-trial-report.md:107 直接对齐`；`templates/mixed-comparison-report.md:70 直接对齐 / 部分对齐 / 未对齐`、`:87 部分对齐`。

**没碰**：prompt（host prompt 本来就说对了）、任何 `scripts/*.py` 逻辑、断言集本身、`templates/unified-evidence-report.md` / `same-trial-evolution-report.md`（扫描下来本就干净）。

---

## 2 本地闸门

`GATES_FAILED=0`：

```
py_compile OK
evals/fact-check/test_regressions.py          35 OK
evals/numeric-integrity/test-render-facts.py  32 OK
evals/scripts/test-check-report.py            31 OK   (R68 的 27 → 31，新增 4 项整树扫描)
evals/scripts/test-build-ledger-scaffold.py    9 OK
evals/scripts/test-merge-ref-facts.py         16 OK
evals/scripts/test-skill-scripts.py           63 OK
evals/scripts/test-tell-scan.py               10 OK
evals/runner-gate/test-runner.py              48 OK
evals/runner-gate/verify-run-chain.py         GATE: PASS (169 histories; 5 comparable; 164 skipped)
tools/test_pack_dist.py                        5 OK
tools/test_replay_run.py                      14 OK
evals/fact-check/mutations.py                 arm a 44/44, arm b 12/12, never flipped [], GATE: PASS
node --test 'test/*.test.mjs'                 16/16
tools/pack-dist.py --check                    DIFFERS 184,391 B af36ade72593 → rebuilt 184,637 B 64151671d952 (改动所致，重建后 IDENTICAL)
```

真跑前已清掉 `skill/multi-clinical-result-comparison/scripts/__pycache__`（R33 教训：本地多出来的文件会被「支持文件清单」断言报成 `missing`）。

---

## 3 发布（原地，用户授权「原地发布」）

- prompt v1.8 未变（sha `999ffe38547a`，本轮改动全在 skill 包内）；`deps` = `unchanged since the recorded baseline`。
- skill **v1.0.9 原地更新**（`skill_id=16aeb0406e12425bad27a2444f17225e` 不变）：`publish` 回读 **29 entries / identical=29 / differing=0 / missing-locally=0**，`status` → **in sync — deployed matches the worktree**。
- **平台侧逐字节回读**（`~/.local/state/toolsmith-publish/deployed-current.zip` vs 本地 `dist/multi-clinical-result-comparison-v0.16.zip`）：29/29 同名、**byte-differing = []**；平台包内 `组内证据关系` = 2、`处理模式` = 0。
- dist：184,391 B `af36ade72593` → **184,637 B `64151671d952`**（+246 B）。
- 包内残留的 `部分对齐` 5 处**全部在禁令上下文内**（`templates/cross-trial-report.md:46`「不要用「部分对齐」这类分类标签」、`references/toolbox.md:352/424`、`references/cross-trial-comparison.md:72`、`SKILL.md:197` 禁用清单）—— 这正是段落作用域豁免要保留的合法形态。

## 4 真跑（固定三组 4/18/14，输入逐字节复用 `/tmp/r63/p{4,18,14}.txt`，串行，web off）

| run | 目录 | server wall s | 步 | out tok | reasoning | `自产物回读/返工` s | 断言 | `template-vocab` | `gate-check` |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| `r69-4` | `20261014-154955` | 414.4 | 31 | 73,911 | 47,938 | 0.6 | 22P/1F | **0** | 13 |
| `r69-18` | `20261014-155716` | 461.8 | 29 | 85,532 | 56,976 | 8.8 | 22P/1F | **4** | 13 |
| `r69-14` | `20261014-160520` | 514.6 | 30 | 90,419 | 64,512 | 7.9 | 22P/1F | **1** | 20 |
| **均值** | | **463.6** | 30.0 | **83,287** | 56,475 | **5.8** | | **1.7** | 15.3 |

对照（同口径重算）：R68 = wall 473.7 / 步 29.7 / out 86,384 / self-read 5.1 / `template-vocab` **12.3**；R67 = 434.7 / 27.0 / 82,669 / 9.4 / **10.0**。

**产物与门禁**：三跑 `outcome=succeeded`、`fails=['tool_results receipts archived']`（= 平台 `P-R53-1`，与 R67/R68 六跑同形）；`report.md` / `citations.json` / `visualizations/*.json` 齐全；平台断言 **22 PASS / 1 FAIL**；平台「prose gate ran and exited clean」`SCAN_EXIT=[0] strong-free=True`。

**本地回放**：`check_report.py` 对三份产物 —— 语域（report voice）**全绿**，唯一 FAIL 是本地回放的 `::visualization` 路径前缀差异（R50 起已知，非产物缺陷）。三份产物内 `处理模式` / `对齐等级` / `部分对齐` 命中 **0 / 0 / 0**，`解读边界` 命中 1 / 7 / 8。

**离线判分**（同 `--scenario a`，4 组）：`r69-4` **22/44** vs `r68-4` **23/44** —— 无劣化信号，也**不称改善**（该判分历史区间 38–44，单条级波动大）。

## 5 判定：KEEP（真错修掉、被测试钉住），但**预登记的主判据只完成了一半**

**成立的**：

1. `template-vocab` 均值 **12.3 → 1.7**（−86%），R68 那一跑 **23 → 4**；三跑不再出现「模板教我怎么做 ↔ 门禁拒收」的**仲裁**，4 处残留 + 1 处全是**复述 host prompt 禁令清单**（逐字：*"Banned: 分析模式/选择依据/可比性结论/对齐等级/…"*）——这类命中是合法的自检，不是冲突。
2. 静态测试对改前文本命中 **5 处语域 / 5 处全词表 / 1 处列名**，改动后 **31/31 OK** ⇒ 真回归测试；扫描范围已覆盖整棵打包树，且正则**直接取自 `check_report.py`**，不会再漂移。
3. 三跑断言仍恒 **22P/1F**，唯一 FAIL 是既有平台项；`自产物回读/返工` 5.1 → 5.8（噪声内）；离线判分同量级。

**没做满的（诚实记账）**：

- **预登记写的是「三组 `template-vocab` 全 0、`r69-18` ≤ 2」，实测 0 / 4 / 1 ⇒ 硬指标未达**（`r69-18` = 4 > 2）。残留 4 处经逐条取证全部是禁令复述，但按预登记口径**不能算达标**。
- **同类缺陷换到第三处**：`templates/cross-trial-report.md` 的 `判断强度（高/中/低可比性）` 列。`r69-18` 逐字：*"Hmm — 判断强度（高/中/低可比性）is a template column; is that a banned self-label (可比性结论/对齐等级)? … Conflict."*、`r69-14` 也自问一次（*"The cross-trial template's column 判断强度（高/中/低可比性）is fine."*）。它**不**被 `check_report.py` 拒（该列名不在 `META_COLUMN_RE`），是**语义像**被判词 —— 但模型为此还是花了推理，且 `r69-18` 最终**放弃了该列**（产物里 `判断强度` = 0，只有 `r69-14` 用 1 次）。
- **不称减负/提速**：wall 473.7 → 463.6（−2%）、out tok 86,384 → 83,287（−3.6%）、步 29.7 → 30.0，三项全在单跑 ±30% 噪声内（R63-0）。

**与 R68 的差别**：R68 是「改对了列名层、却把词层留给下一轮」；R69 是「列名层 + 模板词层都清了、残留降到纯复述」，但**暴露出第三处同类**（`判断强度` 列语义）。这轮的价值主要在**测试覆盖**（整树 + 直取门禁正则 + 段落作用域）而不是指标数字。

## 6 下一轮（R70 候选，未改）

1. **R70-1（首选，同类第三处）**：`templates/cross-trial-report.md` 给 `判断强度` 列加一句「该列名合法、`check_report.py` 不拒；取值是定性标签（高/中/低），**不是** `可比性结论` 那类分类词；列名与取值都不得写成被禁词」——照 R68 修 `解读边界` 的同一手法（给设定、不给判词）。
2. **R70-2**：`gate-check` 复述本身（均值 R67 24.0 / R68 14.0 / R69 15.3）是否可压低：在 SKILL.md 里把「禁令清单」与「怎么自检」合成一条更短的指令，减少模型逐条背禁令的必要（**先取证再改**，别凭感觉）。
3. **R70-3（P2 遗留）**：description 反向边界已在本轮加入（`checking whether a new result is already covered by the library` 等 5 条）；`references/input-contract.md`（523 行）与 `toolbox.md`（433 行）补 `## Contents`；`make_chart.py:149 --no-validate` 标注 debug-only；`references/toolbox.md:226` 示例引文 `95% CI 9.6–9.6` 的 CI typo。
- 不再追 darwin 第 4 维（检查点设计）分数 —— 那是职能边界分歧，不是缺陷。
