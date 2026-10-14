# R68 — 把「我们自己的模板教出来的 FAIL 词汇」清掉（2026-10-14，原地发布 + web-off 三组）

**触发**：R67 证据 §6 ①（真跑前写下）—— `r67-14` 花 **2.5k 字**仲裁我们自己造成的矛盾：`references/cross-trial-comparison.md` Step 4 要求 *"Use a dedicated last column for alignment level and a comparability note per row"*，而 host prompt 与 `check_report.py`（`META_COLUMN_RE` / `META_LABEL_RE` / `METHOD_NARRATION_RE`，三条都是 **FAIL**）禁止 `对齐等级` 列与 `部分对齐` 这类词。

## 1 改了什么

| 文件 | 改动 | 字节 |
|---|---|---|
| `references/cross-trial-comparison.md` | Step 4 的列不再叫 `对齐等级`，末列一律是 **`解读边界`**（写时点/人群/定义/评估/方向这些**材料差异**本身），并明写「列名 `对齐等级` 是交付失败，`check_report.py` 会拒」；「Classify endpoint/metric alignment」改为**显式内部判定**（`**never printed**`：不是列、不是标签、也不写那几个词）；Step 5 的 comparability label 同样标注为内部、正文写成句子；Required output 第 3 条不再要求 "no-chart reason"，改为「用一句发现说出未满足的要求，不许 `不绘图原因` 标签」 | 12,067 → 13,831 |
| `references/toolbox.md` §4 | 判定表加一行：**文字数字**（源文印 `Fifty-one patients`）时 `value` 照抄文字是合法的，不要为凑数字换 quote | 30,007 → 30,219 |
| `evals/scripts/test-check-report.py` | 新增 `ReferenceSetVsGateTests`（25 → **27** 测）：① 扫描打包文本（`references/*.md` + `SKILL.md` + `check_report.py`），**不得出现「叫你去建一个会被本门禁拒掉的列/标签」的措辞**（`column for alignment level` / `- alignment level;` / `- interpretation boundary.` / `no-chart reason`），出现即 FAIL（禁令清单旁引 `check_report.py` 的情形不误伤）；② `cross-trial-comparison.md` 必须点名 `解读边界` 与 `never printed`。**该测试对改前文本命中 4 处 → 是真正的回归测试，不是橡皮章** | 25 测 → 27 测 |

**没碰**：prompt（host prompt 本来就说对了，这次错的是我们的参考文件）、任何脚本逻辑、断言集。`deps` unchanged。

## 2 本地闸门

`bash /tmp/r63/gates.sh` 首轮 `GATES_FAILED=1`（`pack-dist --check` rc=3，dist 未重建）→ 重建 → 二轮 **GATES_FAILED=0**（`test-check-report` **27** / `test-render-facts` 32 / `test-skill-scripts` 63 / 其余同 R67 / `pack-dist --check` **IDENTICAL 184,391 B sha `af36ade72593`**，R67 为 183,824 B）。

## 3 发布与真跑

**原地发布**（用户授权「原地」）：prompt v1.8 未变（sha `999ffe38547a`，本轮的改动全在 skill 包内）；skill v1.0.9 内容替换，29/29 `differing=0`；发布后 `status` → **in sync**；回读确认 dist 内已含 R68 文本（`never printed` = 1、`解读边界` = 3、旧措辞 `column for alignment level` = 0）。

**真跑**：固定三组 4/18/14，输入逐字节复用 `/tmp/r63/p{4,18,14}.txt`，串行，web off。

| run | 目录 | wall s | 步 | 每步固定开销 s | render 调用 | build_ledger | `--check` | out tok | reasoning | `自产物回读/返工` | 断言 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `r67-4` | `20261014-141210` | 331.7 | 22 | 2.4 | 1 | 2 | 1 | 63,120 | 44,720 | 0 | 22P/1F |
| `r67-18` | `20261014-141754` | 392.2 | 27 | 2.4 | 1 | 2 | 1 | 77,884 | 43,951 | 19.4 | 22P/1F |
| `r67-14` | `20261014-142437` | 580.2 | 32 | 0.0 | 1 | 4 | 2 | 107,002 | 16,054 | 8.8 | 22P/1F |
| **`r68-4`** | `20261014-144841` | **306.3** | 20 | 9.1 | 1 | 3 | 1 | **53,438** | 23,352 | **0** | 22P/1F |
| **`r68-18`** | `20261014-145353` | **609.4** | 41 | 0.2 | 2 | 3 | 1 | 108,848 | 54,415 | **14.3** | 22P/1F |
| **`r68-14`** | `20261014-150409` | **505.5** | 28 | 2.6 | 1 | 2 | 1 | 96,866 | 65,444 | **0.9** | 22P/1F |

| 代 | wall 均值 | 步均值 | out tok 均值 | `自产物回读/返工` | 词汇合法性推理（次数 / k 字符） |
|---|---:|---:|---:|---:|---|
| R65n | 459.7 | 30.0 | 82,015 | 79.3 | — |
| R67 | 434.7 | 27.0 | 82,669 | 9.4 | 32.3 / 19.7 |
| **R68** | 473.7 | 29.7 | 86,384 | **5.1** | **23.3 / 14.1** |

（`r68-4` 306.3 s 是这三代里单跑最快的一次，前纪录 309.2 s；`r68-18` 609.4 s / 41 步是六跑里最慢最重的一次 —— 单跑离散仍是 ±30% 量级。）

## 4 判定：KEEP，但**只说对了一半**

**成立的部分**：R68 的目标矛盾**消失**。同一个 14 组（`r67-14` 就是仲裁那一跑）在 R68 里 `对齐等级` 提到 **0** 次、`check_report.py fails on 对齐等级` **0** 次，模型直接按 `解读边界` 写；`r68-18` 出现的 3 次只是把 host prompt 的禁令清单复述一遍（没有仲裁）。新增静态测试对改前文本命中 4 处 ⇒ 这类矛盾以后不会再悄悄回来。

**没解决的部分（诚实记账）**：同一类缺陷**仍在**，只是换了位置 —— 模型这次纠结的是**单元格里的词**而不是**列名**。`r68-18` 逐字：

> *"The mixed template's section 4.3 column header 「解读边界」 with values 直接对齐/部分对齐/仅背景相关/未对齐 — those clash with the host prompt's ban on 「部分对齐」."*

> *"`处理模式` with values 跨试验/同试验演进 — that's a self-classification. Risky!"*

真凶是 **`templates/mixed-comparison-report.md`**：第 70 行的示例单元格就写着 `直接对齐/部分对齐/仅背景对齐…`，第 30 行还有一个 `处理模式` 列。`r68-14` 也在 `判断强度` 单元格上反复自问（*"I'll label 判断强度 as 低—中可比性… Careful: 是「部分对齐」banned class label"*），最后把 `中（部分对齐）` 删掉。⇒ 我 R68 的**扫描范围只写了 `references/`，漏了 `templates/`**，这是本轮的纪律教训。

**为什么仍然 KEEP 不撤**：① 改的是真的错（我们自己发的参考文件教了一个会被自己门禁判 FAIL 的列）；② 九跑（R63 / R65n / R67 / R68）断言恒 22P/1F、唯一 FAIL 是平台 `P-R53-1`，无新增缺陷；③ `自产物回读/返工` 保持 R67 的低位（0 / 14.3 / 0.9）；④ 静态测试把这一半永久钉住。**但不得声称 R68 减了负**：墙钟均值 434.7 → 473.7、out tok 82,669 → 86,384、步数 27.0 → 29.7，全在噪声内且方向偏坏；词汇合法性推理总量（32.3 → 23.3 次）下降主要来自 `r68-4` 的 5 次，而最重的 `r68-18`（41 次 / 24.9k 字符）恰好就是踩到 templates 那一跑的。

## 5 下一轮（R69，未改）

1. **`templates/*.md` 全面清扫**（首选）：把示例单元格里的对齐等级词（`直接对齐` / `部分对齐` / `仅背景对齐` / `未对齐`）换成**材料差异**示例（`时点不同（16 周 vs 52 周）`），`处理模式` 列按同一原则处理或删掉；`templates/mixed-comparison-report.md` 第 30、70 行是已定位的两处。
2. **静态测试扩到整棵打包树**（`skill/**/*.md` + `*.json`，不只 `references/`），并用「模板不得示范被门禁拒的写法」这条不变式守住（比如：对每个模板文件跑一遍 `check_report.py` 的正则族，命中即 FAIL）。
3. 之后才轮得到 R66 候选 B（惰性段条件化）与 D（`same-trial-evolution.md` 0 读取）。

**证据**：本文件；静态测试 `evals/scripts/test-check-report.py::ReferenceSetVsGateTests`。
