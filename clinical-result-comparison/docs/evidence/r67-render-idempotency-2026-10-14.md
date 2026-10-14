# R67 — `render-facts.py` 幂等 + 空 `unit` 拼写写进契约（2026-10-14）

**触发**：R65 三跑把探针从「`·` 怎么写进 `value`」换成了**渲染器自身语义**。`r65n-4` msg55/59 逐字：

> *"Re-rendering will read the file (which contains the appendix), resolve tokens (already resolved → no tokens left) and append ANOTHER appendix? Hmm! Danger: render appends the appendix; if it already exists, does it replace it?"*
> *"Confirmed: render appends a second appendix (not idempotent)."*

模型把这条**未文档化的语义**用实验测了出来（`body.md` 抄一份正文、渲染、再核对附录有没有多一份），代价记在语义阶段 `自产物回读/返工`：**R62 0.8 s → R65n 79.3 s / 14,392 out tok**（4 esid 组），是 R65 与 R62 之间最大的单点差。

## 1 预登记（在 R67 真跑**之前**写下，见 R65 台账 R65-1 与 `r65-token-contract` §6.3）

| 判据 | 判据来源 |
|---|---|
| `自产物回读/返工` 阶段回到 R62 量级（< 20 s） | R65 台账 R65-1 指名 R67 目标 = 幂等/空单位/附录重建语义 |
| 思考里不再出现 `second appendix` / `another appendix` / `body.md` 绕行 | 同上（R65 三跑分别 3 次 / 4 次） |
| `render-facts` 调用数回落到 1 次/跑（不再靠重渲染试错） | R65 三跑 4 / 3 / 1 |

**诚实记账**：以上三条**是**在真跑前写下的（R65 台账 + 证据 §6.3），但我**没有**预先写下墙钟区间或「预期省多少秒」——R63-0 已证明单跑墙钟噪声 ±30%，这类数字预登记了也不可判。本轮只判上面三条形态判据 + 不劣化。

## 2 改了什么

| 文件 | 改动 | 字节 |
|---|---|---|
| `scripts/render-facts.py` | 新增 `_strip_rendered_appendix()`：若 `APPENDIX_TITLE` 是草稿**最后一节**（其后无别的 `## `），先剥掉再渲染 ⇒ 就地重渲染幂等；`--audit` 增加 `idempotent_rerender` 布尔；docstring 写明幂等与空 `unit` 事实 | 37,696 → 39,266 |
| `references/toolbox.md` §4 | 新增「渲染是幂等的」段：就地重渲染安全、**不需要**抄 `work/body.md`、**不需要**读回产物查附录；列出两条已实测格式事实（空 `unit` ⇒ 值后无空格无占位符；附录列/行全由 ledger 推导，不得手改） | 28,845 → 30,007 |
| `system-prompts/…-v0.16.md` 规则 6 | 一句：重渲染是幂等的（替换而非追加），**禁止**为此抄正文副本 / 读回已渲染报告查附录 | 81,413 → 81,687 |
| `skill/…/SKILL.md` | 渲染门禁那句加同口径半句（可安全重渲染，别抄副本、别读回核对附录） | 45,909 → 46,017 |
| `evals/numeric-integrity/test-render-facts.py` | +3 测：① 把自己的输出再喂进去 ⇒ 输出**逐字节相同**、附录只有 1 个、`idempotent_rerender=True`；② 附录标题出现在正文中段时**不动**（那是作者文本）；③ 空 `unit` ⇒ `8.34{{ref_1}}`（无尾随空格）。29 → **32** 测 | 44,979 → 46,023+ |

**行为侧，不是文档侧**：这是本轮与 R65 的本质区别 —— R65 只加判据文字，模型照旧自己做实验；R67 把「会不会多一个附录」这个不确定性**从代码里删掉了**，所以不需要靠文字禁令去堵。

## 3 本地闸门

`bash /tmp/r63/gates.sh` → **GATES_FAILED=0**（`test-render-facts` 32 / `test-skill-scripts` 63 / `test-tell-scan` 10 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test-merge-ref-facts` 16 / `test_regressions` 35 / `mutations` 12/12 / `test-runner` 48 / `verify-run-chain` PASS / `test_pack_dist` 5 / `test_replay_run` 14 / node / `pack-dist --check`）。`pack-dist.py` 重建 → `--check` **IDENTICAL (183,824 B / 29 entries / sha `c98916b3cc26`)**（旧 `fc438d58f02b`）。

## 4 发布与真跑

**原地发布**：prompt family `91febc286412479a8b6d569fa3b8025e` **v1.8** → 81,687 B sha `999ffe38547a`；skill family `9fe0035bdd324b998436c6cb9c2de212` **v1.0.9**（`skill_id 16aeb0406e12425bad27a2444f17225e`）29/29 `differing=0`；`deps` unchanged；发布后 `status` → **in sync**。

**真跑**：固定三组（4 / 18 / 14），输入逐字节复用 `/tmp/r63/p{4,18,14}.txt`，**串行**，web **off**（与 R63 / R65n 同条件）。

| run | 目录 | esid | wall s | 步 | render 调用 | build_ledger | out tok | reasoning | `自产物回读/返工` | 断言 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `r63-4` | `20261014-110640` | 4 | 525.7 | 25 | 1 | 2 | 97,495 | 78,312 | 0.8 | 22P/1F |
| `r63-18` | `20261014-111536` | 18 | 410.3 | 26 | 1 | 2 | 75,899 | 47,709 | — | 22P/1F |
| `r63-14` | `20261014-112254` | 14 | 679.8 | 23 | 4 | 3 | 123,494 | 89,932 | — | 22P/1F |
| `r65n-4` | `20261014-133853` | 4 | 409.7 | 34 | 4 | 4 | 65,077 | 48,153 | **79.3** | 22P/1F |
| `r65n-18` | `20261014-134600` | 18 | 593.2 | 36 | 3 | 4 | 112,538 | 70,869 | — | 22P/1F |
| `r65n-14` | `20261014-135656` | 14 | 376.1 | 20 | 1 | 2 | 68,430 | 45,413 | — | 22P/1F |
| **`r67-4`** | `20261014-141210` | 4 | **331.7** | 22 | **1** | 2 | 63,120 | 44,720 | **0** | 22P/1F |
| **`r67-18`** | `20261014-141754` | 18 | **392.2** | 27 | **1** | 2 | 77,884 | 43,951 | **19.4** | 22P/1F |
| **`r67-14`** | `20261014-142437` | 14 | **580.2** | 32 | **1** | 2 | 107,002 | 16,054 | **8.8** | 22P/1F |

| 代 | wall 均值 | 步均值 | out tok 均值 | `自产物回读/返工` |
|---|---:|---:|---:|---:|
| R63 | 546.9 | 24.7 | 98,963 | — |
| R65n | 459.7 | 30.0 | 82,015 | 79.3（4 组） |
| **R67** | **434.7** | 27.0 | 82,669 | **0 / 19.4 / 8.8** |

## 5 判定

| 预登记判据 | 结果 | 判定 |
|---|---|---|
| `自产物回读/返工` < 20 s | 0 / 19.4 / 8.8 s（R65n 同组 79.3 s） | ✅ **成立**（−88%） |
| 无 `second/another appendix`、无 `body.md` 绕行 | 三跑 **0 / 0**（R65n 3 / 4） | ✅ **成立** |
| `render-facts` 调用回落到 1 次/跑 | **1 / 1 / 1**（R65n 4/3/1） | ✅ **成立** |
| 不劣化 | 断言九跑恒 22P/1F（唯一 FAIL = 平台 `P-R53-1`）；产物齐全；`build_ledger` 回到基线 2/2/2；步数 30.0 → 27.0 | ✅ |

**裁定：KEEP。** 且这是**本轮迭代里第一次目标指标真的动了**：R63（失败可见性）与 R65（token 契约）都没能移动任何测量值，R67 把 `自产物回读/返工` 从 79 s 打到 0–19 s、把防御性绕行清零。墙钟均值 434.7 s 也是三代最低，但**不据此声称提速**（R63-0：单组噪声 ±30%，R67-14 的 580 s 与 R63-14 的 680 s 之间没有可判差异）。

## 6 三跑暴露的下一批变量（R68 候选，均**未**改动）

1. **包内自相矛盾（与 R65 docstring 同类，优先级最高）**：`r67-14` 用了 **2.5k 字**去仲裁 —— `references/cross-trial-comparison.md` 的模板里有 `对齐等级` 列（Step 4 要求），而 host prompt 与 `check_report.py` **禁止**该列名（`no self-labelling … 对齐等级`）。模型逐字推理：*"the cross-trial template has a column '对齐等级' in the reference … but the host prompt says: no self-labelling … check_report.py fails on `对齐等级` as a table column. So the template's `对齐等级` column must be replaced by the `解读边界` column"*。⇒ **我们自己发的参考模板教了一个会被自己的门禁判 FAIL 的列**，必须修模板（或明确写「模板列名以 host prompt 为准，`对齐等级` 必须落成 `解读边界`」）。
2. **`value` 是「印出来的字符」包括**文字数字**：`r67-14` 为 *"Fifty-one patients were randomized"* 纠结 —— 逐字推理 *"value 'Fifty-one' unit '例'? Ugly. Better: change quote to one with digits"*。契约上 `value: "Fifty-one"` **合法**（就是原文印出的字符），但包内从未说过；模型宁可换 quote。⇒ 在 `toolbox.md` §4 的判定表加一行：源文用文字数字时，`value` 照抄文字（`Fifty-one`），不要为凑数字去换 quote。
3. **抽取字段与原文冲突时的处置已正确但没有成文**：`r67-14` 发现 digest 的 `-97.8% (-98.6, -96.9%)` 掉了 `%`，正确回到摘要原文取 quote。这类「以 `work/sources/ref_n.txt` 为原文权威」已有规则，仅在证据里留痕，不再改。
4. **14 组的长思考步**（`r67-14`：2 步 239.2 s = 墙钟 41%）已全是**内容分析**（14 条披露、11 项研究的跨试验对齐与计划），不再含契约不确定性 ⇒ 说明契约类浪费已被打掉，剩下的是选题规模本身的成本。
