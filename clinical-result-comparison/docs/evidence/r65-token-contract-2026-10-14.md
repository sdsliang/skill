# R65 — token 契约唯一化 + 提交前可自查（**本地就绪，待发布授权**）

日期 2026-10-14 · 目标变量 = **输出 token 量**（R63-0：n=39 下 `r(wall, out tok)=+0.924`，是唯一主导项）
本轮**只改运行期文本 + 一个脚本 docstring**，不删任何规则；发布属 TS 写动作，**等用户一句话**。

## 1 预登记（改前写死，防止事后编故事）

- **假设**：`value` / `quote` 的验收契约在运行期文本里**只有一句结论、没有可判定的边界**，且交付包内**有一份自相矛盾的范例**；模型因此无法静态判定，只能「先瞎猜 → 等校验失败 → 再改」。
  ⇒ 把契约写成**可静态自查的四条判定 + 具名自检命令**、并修掉矛盾范例，应减少「试错型思考」与**探针草稿渲染**。
- **不劣化判据**：R65 三跑（固定 4/18/14 组，复用 R48/R50 逐字节输入、串行）相对 R63 三跑带
  （wall 526.5 / 425.5 / 688.6 s，out 97,495 / 75,899 / 123,494，步 25/26/23，调用 35/29/31）**不得出现新的形态指标**：
  `probe draft` 渲染次数 0、`render-facts: FAILED` 0、`P-R53-1` 仍是唯一 FAIL、产物齐全。
- **可观察的省时点（预登记）**：`r63-14` 有 **2 次自造探针草稿渲染**（`work/probe.md` 最小样张试渲染，R63-2 观察）；`r63-4` 第 23 条 thinking 明确写下「先瞎猜、等校验失败再改」的策略。假设成立 ⇒ 这两处应消失。

## 2 证据（改前实测，只读）

**触发原文（`r63-4` msg[23] thinking，逐字）**：

> The toy example shows `"value": "11.1"` with quote containing "11.1" — no guidance on ·. … Now let me define
> the facts. I'll try "." values; where the quote uses ·, the validation will fail and I'll then switch that fact's quote/value …

**思考 token 分布**（`/tmp/r64/why.py` 按信号切 thinking；单位字符数）：

| 信号 | r63-4 | r63-18 | r63-14 |
|---|---|---|---|
| 结构化字段解读 | 8 步 / 208,527 | 7 步 / 108,163 | 8 步 / 203,962 |
| `facts.json` 形状/写法 | 7 步 / 206,394 | 4 步 / 87,815 | 6 步 / 159,338 |
| `build_ledger` 语义 | 7 步 / 186,031 | 3 步 / 83,641 | 7 步 / 183,810 |
| `render-facts` 验收 | 5 步 / 139,195 | 3 步 / 86,433 | 4 步 / 79,644 |
| 分隔符/字段歧义 | 4 步 / 88,725 | 1 步 / 53,192 | 7 步 / 198,296 |
| 试错/二分 | 1 步 / 5,811 | 1 步 / 13,763 | 1 步 / 13,980 |

⇒ 契约不确定性是**最大单一思考簇**（三跑都排前列），而不是内容判断。

**契约源码**（判定权威，逐行核对过）：

- `scripts/render-facts.py` l.253–258：`quote` 必须 `in` 源文，`value` 必须 `in quote`；l.111–113 `_normalise_text` = 空白压缩 + `MINUS_TRANSLATION`（减号归一）。
- `scripts/build_ledger.py` l.609–615：**同一套检查**在编译期就跑（`facts[..]: quote is not an exact substring of …` / `value '…' is absent from quote`），`--check` 只校验不写文件 —— **这条现成能力此前从未在任何运行期文本里被点名**。

**实测判定表**（`build_ledger.py --facts … --check`，源文印 `中位 PFS 为 11.1 · 9.8 个月`）：

| `value` | EXIT | 原因 |
|---|---|---|
| `11.1 · 9.8` | 0 | 连分隔符照抄 = 子串 |
| `11.1` | 0 | 子串允许只截一段 |
| `11.1 vs 9.8` | 3 | 改写分隔符后不再是子串 |
| `-5.3`（源文只印 `5.3`） | 3 | 派生值不属于 `value` |
| `-0.44` / `−0.44`（源文 U+2212） | 0 / 0 | 减号两侧都归一 |

**交付包内自相矛盾的范例（本轮修掉的实体缺陷）**：`scripts/build_ledger.py` docstring 的 `Write work/facts.json like this` 范例是
`"value": "-5.3"` + `"quote": "安慰剂组 MDS TBR 下降 5.3%"` —— **拿它原样喂给脚本，EXIT=3**：

```
FINDINGS (1) — nothing written:
  - facts[0] (ocean-mds-tbr-diff): `value` '-5.3' is absent from `quote` ('安慰剂组 MDS TBR 下降 5.3%')
```

即：**模型读到的唯一一份完整范例，本身就是校验器拒绝的形状**（`-5.3` 是两臂差值，源文只有 `5.3`）。

## 3 改了什么（四文件 + 一条测试，全部可回读）

| 文件 | 字节 | 内容 |
|---|---|---|
| `references/toolbox.md` §4 | 27,540 → **28,845** | 两条强制条件写成**可静态判定**的措辞（只归一空白与减号；`value` 只能是印出来的字符）＋ §2 那张**实测判定表**（4 行，✅✅❌❌）＋ **点名 `build_ledger.py --facts work/facts.json --check` 就是提交前自检**（不写文件、报同类问题、exit 3），并**明令不要写探针草稿去试语法** |
| `scripts/build_ledger.py` docstring | 29,515 → **30,198** | ② 范例 `value` `-5.3` → `5.3`（arm 改为「安慰剂组」，与 quote 自洽）；③ 新增一段：两条检查就在本脚本内、只归一空白与减号、**派生数字不得进 `value`**、`--check` 即自检、**不要写探针草稿试渲染** |
| `system-prompts/…-v0.16.md` | 80,960 → **81,413** | ledger 段一句收紧：`value` 是源文**印出来的**子串、`quote` 是源文精确子串（不改分隔符 / 不放派生数字），`build_ledger.py --check` 是提交前自检 |
| `SKILL.md` | 45,485 → **45,909** | 同一个 contract 段落同口径收紧 + 指向 toolbox §4 |
| `evals/scripts/test-skill-scripts.py` | 44,979 → **46,023** | 新增 `test_value_must_be_a_verbatim_substring_of_its_quote`：把 §2 表格的 ✅✅❌❌ 四例做成断言（62 → **63**），**文档声明由测试钉住** |

**顺手收掉 R64 留下的文本冲突（R63 埋的雷）**：`toolbox.md` 调用形态段新增一条 **One marker, one meaning** ——
`EXIT=${PIPESTATUS[0]}` 是通用形态，`tell-scan.py` 自己的 `SCAN_EXIT=$?` 同样可读（两者 runner 都认），**但禁止混写 / 禁止裸 `… | tail -40; echo "EXIT=$?"`**。
（四处 tell-scan 专属写法**故意不改**：那是该工具自己的 idiom，改它只是白改字节；冲突由这一句一次说清。）

## 4 本地闸门（改后）

`py_compile` 0 · test-render-facts **29** · test-skill-scripts **63** · test-tell-scan 10 · test-check-report 25 ·
test-build-ledger-scaffold 9 · test-merge-ref-facts 16 · test_regressions 35 · mutations b 12/12 · test-runner **48** ·
`verify-run-chain GATE: PASS`（5 可比）· test_pack_dist 5 · test_replay_run 14 · node 16 ·
`pack-dist --check` **IDENTICAL 182,666 B / sha `fc438d58f02b`** ⇒ `GATES_FAILED=0`。
dist 181,638 → **182,666 B**（`39640fd6e679` → `fc438d58f02b`）。

## 5 待办（发布之后才有 R 记录）

1. **`toolsmith-publish publish`（原地，需用户授权）** → `status` 回读必须 in sync（prompt v1.8 新 SHA / skill v1.0.9 新 SHA）。
2. 固定三组回归（4/18/14，串行、输入复用 R48/R50）→ 按 §1 判据比对 R63 三跑带，落 `R65` 台账记录。
3. 若探针草稿渲染仍出现 ⇒ 假设立不住，回退口径写进台账（**不许拿「已加禁令」当结论**）。
