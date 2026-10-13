# 按「语义阶段」拆时间：一次 HARMONi-6 四证据跑分到底花在哪（2026-10-13，n=3）

用户问题：**「别按 agent 的工具调用流看，我要知道各语义阶段各花了多久，比如写引用花了多久。」**

本文给的就是这个口径：**按业务产出物拆时间**（取数 / 读源文取证 / 建事实账本 / 写报告 / 画图 / 编引用 / 跑门禁 / 交付），
不是 `execute → execute → write_file` 的调用序列。

数据源：`~/.local/state/toolsmith-runs/20261013-*` 的 `debug-history.json`（`raw_model_messages`，带每步 `usage` + `timestamp`）
＋ `timing.json` / `usage.json` / `run.json` / `verification.md`。复算脚本：**`tools/semantic-timing.py`**（只读、离线）。

样本：同一输入（`/tmp/prompt-r53-4.txt`，4 个 esid，web off，DeepSeek Flash）三次真跑，其中两次是本轮新跑的
（`r61-sem-1` / `r61-sem-2`，串行执行以避免并发抢吞吐），第三次用 2026-10-13 的 R60 实测（`r60-prose-generic-2`）做对照。

---

## 1. 三次跑的原始指标

| run | wall s | 步数 | out tok | reasoning | 工具耗时 s | 工具调用 | 账本字节 | 断言 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `r60-prose-generic-2`（R60 对照） | 344.1 | 23 | 61,049 | 46,759 | 5.4 | 27 | 13,992 | 22 PASS / 1 FAIL |
| `r61-sem-1` | **354.5** | 29 | 58,363 | 41,627 | 6.7 | 32 | 15,053 | 22 PASS / 1 FAIL |
| `r61-sem-2` | **251.7** | 19 | 52,551 | 38,420 | 5.0 | 23 | 17,124 | 21 PASS / 2 FAIL |
| 中位 | 344.1 | 23 | 58,363 | 41,627 | 5.4 | 27 | 15,053 | — |

同输入三次跑 wall 251.7 – 354.5 s（跨度 41%），步数 19 – 29 —— **这是本任务当前的方差带**，讨论任何秒级差异都必须先落在这条带里。
两次 FAIL 有 1 条是本轮新发现的**我们自己的假 FAIL**（见 §6），两次都能跑完、交付物齐全（`output/report.md` + `output/citations.json` + `visualizations/evidence-timeline.json`）。

---

## 2. 语义阶段分布（生成时间按产出物归因）

口径：每步生成时间 = `t(下一步首个工具返回) − t(本步开始生成) − 工具跨度`；再按该步**参数写向哪个产出物**（`write_file` 的
`file_path`、`execute` 的重定向目标/脚本名、`read_file` 的路径）按字节权重摊到各阶段。`execute` 里的 `cmd1 && cmd2` 会按子命令拆开，
不整段算一个阶段。

| 语义阶段（生成 s） | r60-2 | r61-sem-1 | r61-sem-2 | 三次区间 | 备注 |
|---|---:|---:|---:|---|---|
| 装载契约 load contract | 67.6 | 64.8 | 22.5 | 22–68 | **几乎全是长思考步**（见 §4），名义动作只是读模板 |
| 取数 fetch records | 3.3 | 10.7 | 6.1 | 3–11 | MCP 参数工具 1 次/跑 |
| 源文阅读/取证 sources | 47.3 | 18.9 | 22.9 | 19–47 | 读 `work/sources/ref_*.txt`、探引文串 |
| 事实与账本 facts/ledger | 47.4 | 75.1 | 43.9 | 44–75 | 写 `work/facts.json`/`ledger.json` + `build_ledger`/`merge_ref_facts` |
| 自产物回读/返工 self-read | 29.0 | 32.2 | 7.5 | 8–32 | 回读自己的草稿/中间产物再改 |
| 报告正文 report | 54.8 | 70.1 | 68.6 | 55–70 | 写 `output/report.md`（+ 回改） |
| 图表 charts | 22.8 | 11.9 | 20.4 | 12–23 | 写图表 JSON + `make_chart.py` |
| 引用编撰 citations | **1.8** | **1.8** | **1.4** | **1.4–1.8** | 已脚本化，**基本不花时间**（0 字节手写） |
| 门禁自检 gates | 5.3 | 5.6 | 5.6 | 5.3–5.6 | 极稳定 |
| 交付 present_artifact | 2.2 | 0.0 | 1.1 | 0–2 | |
| 其他 other | 37.6 | 31.9 | 29.6 | 30–38 | 无产出物路径的 shell/python 管道行（`echo`/`wc`/`tail`/解析片段） |
| **生成合计** | **319.2** | **323.5** | **229.7** | — | 占 server 的 91–93% |
| 工具本身（全部调用） | 5.4 | 6.7 | 5.0 | 5.0–6.7 | **仅 1.5–2.0%** |
| 其余（建线程/落盘/收尾/断言） | 19.5 | 24.3 | 17.1 | 17–24 | 5–7% |

**读法（三点，都反直觉）**

1. **`写引用` 已经不是成本**：1.4–1.8 s、0 字节手写 —— `make_citations.py` 把它变成了纯脚本调用。用户问的"写引用多久"答案是 **≈1.6 s（0.5%）**。
2. **真正的两个大头是「账本」和「报告正文」**：合计 102–145 s（占 30–44%）。它们不是"打字慢"，而是**边想边写**（见 §3 的落笔列：账本/报告的落笔只占其生成时间的 1/3）。
3. **工具不慢**：整跑所有工具调用只花 5–7 s。优化平台沙箱吞吐（P-R56-1）对本任务几乎无收益，**要优化的是步数与思考**。

---

## 3. 全 run 成本分解：思考 ≫ 落笔

每跑的生成时间用该跑自身做线性回归标定（`生成 s ≈ a·reasoning_tok + b·content_tok + c·步数`，R² = 0.985–0.991），
再把同一系数作用于全跑，得到与总时长自洽的分解：

| run | 思考 | 落笔（真在打字） | 每步固定开销 | 工具本身 | 标定（ms/tok） |
|---|---:|---:|---:|---:|---|
| r60-2 | 242.9 s (**71%**) | 39.6 s (12%) | 36.7 s (11%) | 5.4 s (1.6%) | reason 5.19 / 落笔 2.77 / 每步 1.60 s |
| r61-sem-1 | 232.1 s (**65%**) | 34.9 s (10%) | 56.5 s (16%) | 6.7 s (1.9%) | reason 5.57 / 落笔 2.08 / 每步 1.95 s |
| r61-sem-2 | 166.2 s (**66%**) | 24.4 s (10%) | 39.0 s (16%) | 5.0 s (2.0%) | reason 4.33 / 落笔 1.73 / 每步 2.05 s |

- **思考占 65–71%**，落笔只占 10–12%（三次跑一致得离谱，偏差 ≤2 pt）。
- **每步固定开销 1.6–2.1 s**（系统提示 + 工具 schema 重放的 prefill 成本），乘以 19–29 步 = **37–57 s（11–16%）**。
  含义：**砍步数**（合并脚本调用、少一次回读）比省 token 更省时间，一次 `execute` 大约值 2 s。
- 与 2026-10-10 基线（`docs/evidence/runtime-breakdown-2026-10-10.md`：生成占 65–91%、3.3–4.1 ms/token、1.4–2.6 s/步、reasoning 占 out 的 46–76%）**完全同构**；
  本轮的增量信息是**语义归属**与"长思考步"结构。

---

## 4. 长思考步：每跑恰好一次 58–64 s 的「取证归拢 + 账本设计 + 报告规划」

规则（纯客观、无人工挑选）：`reasoning_tokens / output_tokens ≥ 80%` 且 `生成 ≥ 40 s` 的步。

| run | 步 | 生成 s | reasoning 占比 | 名义动作（工具目标） | 该步 thinking 开头（原文） |
|---|---:|---:|---:|---|---|
| r60-2 | 19 | 63.5 | 96% | `execute` → 源文阅读/取证 | *"Now I have full data. Let me carefully assemble the evidence. Trial: HARMONi-6 … one trial, 4 disclosures, 2 distinct evidence states."* |
| r60-2 | 21 | 60.2 | 99% | `read_file`（读报告模板） → 装载契约 | *"No normalization: value must literally appear… the ledger requires "·" values for ref_3/ref_4 quotes."* |
| r61-sem-1 | 25 | 63.2 | 99% | `read_file`（读报告模板） → 装载契约 | *"Consistent. Now build the facts ledger. Let me plan the ledger facts. Note: quote must be an exact substring of the source file for that ref…"* |
| r61-sem-2 | 13 | 57.8 | 99% | `read_file` + `execute` → 装载契约 | *"Now I have a complete picture. Single trial HARMONi-6, 4 disclosures, 2 evidence states. Key facts and the design verification issue: registry `blinded` = 四盲…"* |
| **合计/跑** | | **57.8 – 123.7** | | | 占该跑 wall 的 **18% / 23% / 36%** |

**这条才是真实的最大单项成本**：模型在拿到全部证据后，集中用一步把「四条披露 → 两个证据状态 → 账本条目 → 报告结构」一次想清楚
（r60-2 拆成两步：先归拢证据、再设计账本）。它记账时挂在"读模板/探源文"名下，但那一步 **99% 的时间是思考**，
工具只是它思考前的最后一次取证 —— 所以主表里「装载契约 18–20%」**不应读成"读契约文件很慢"**，应读成"**规划/设计 ≈ 60 s**"。

派生量（本文档口径，不写进脚本的固定阶段表）：**规划/设计 = 18–36%，中位 23%**。

---

## 5. 对迭代方向的直接含义

| 成本项 | 实测 | 可否动 | 怎么动 |
|---|---|---|---|
| 思考（65–71%） | 166–243 s | 部分 | 与模型/提示词强相关；**压 token 的收益线性 5.2–5.6 ms/tok**，比压字节（2 左右 ms/tok）更值 |
| 规划/设计（18–36%） | 58–124 s | 难 | 是任务固有的一次性推理；能做的只有"一次想对"（减少事后返工） |
| 账本 + 报告正文（30–44%） | 102–145 s | 部分 | 账本已脚本化但模型仍手写 `facts.json`（13.7–18.2 s 纯打字）；报告正文 4–11 s 纯打字，其余是边想边写 |
| 自产物回读/返工（3–9%） | 8–32 s | **可动** | 回读自己的草稿再改：可由更严格的"写前契约校验"消掉 |
| 每步固定开销（11–16%） | 37–57 s | **可动** | **减步数**：run1 用了 29 步、run2 只用 19 步而 wall 短 29% —— 步数是最显著的自变量 |
| 工具/沙箱（1.5–2%） | 5–7 s | 不值得 | 平台 P-R56-1（单通道）**不是瓶颈** |
| 引用编撰（0.5%） | 1.4–1.8 s | 已完成 | 已脚本化，无需再优化 |

---

## 6. 本轮顺带发现的测试侧问题（我们自己的假 FAIL）

`r61-sem-2` 的断言里有一条 `[FAIL] prose gate exited clean`（`SCAN_EXIT=[0, 3, 0]`）。
**核实结论：这是假 FAIL，报告本体并无文体回潮。** 归因链（来自该步的 `tool-call` 与 `tool-return` 原文）：

1. 第 25 步模型链：`patch.py --find '…' && patch.py --find '…' && … check_report.py … && tell-scan.py report.md; echo "SCAN_EXIT=$?"`；
2. **第一个 `patch.py` 断言失败**（`ASSERT FAILED: … contains 0 occurrence(s) of the pattern, wanted 1`，`patch.py` 失败即 `exit 3`）
   → `&&` 短路，后面的 `check_report.py` / `tell-scan.py` **根本没跑**；
3. `; echo "SCAN_EXIT=$?"` 打印的 `3` 是 **`patch.py` 的退出码**，不是扫描器的；
4. 该跑的收尾（第 34 步）扫描器**真跑过**：`强 0 / 弱 1（W-FMT-MIXED，弱）`，`SCAN_EXIT=0` —— 门禁是干净的。

⇒ 断言把"模型自己 echo 的 SCAN_EXIT"当作扫描器结论，遇到 `&&` 短路就会被别的命令的退出码污染。
（这是 R60-3「`SCAN_EXIT` 依赖模型自回显」的第一次真实踩坑，已记入台账 `R61-3`，本轮**未修**，留作下一轮的单一假设。）

---

## 7. 口径与诚实性边界

1. **时间片公式**：`生成+执行(i) = t(下一步首个工具返回) − t(本步开始生成)`，`工具跨度(i) = t(最后返回) − t(首个返回)`，
   `生成(i) = 生成+执行 − 工具跨度`。前提是每步助理消息带 `usage` 且 `timestamp` = 开始生成（本批数据成立，逐条校验过）。
2. **归因靠"目标"，不靠关键字**：`write_file` 看 `file_path`；`execute` 看重定向目标与脚本名（`make_chart.py`→图表、
   `build_ledger.py`/`ledger.json`→账本、`check_report.py`/`tell-scan.py`→门禁…），并按 `&&`/`;`/`|`/heredoc 拆子命令。
   早期版本按关键字匹配曾把报告正文里**提到** `visualizations/` 的文字算成图表时间，已废弃。
3. **不可消除的归因限制**：reasoning token 记在"承载它的那一步"上，而**思考放哪由模型决定**。
   一个名义目标为"读模板"的步可以扛 60 s 的报告规划思考 —— 这既是本方法的已知偏差，也正是 §4 单列"长思考步"的原因。
   因此本文所有阶段数字应读作**"该产出物所吸收的模型时间"**，而非"处理该文件本身的开销"。
4. **落笔字节标定**：`真在打字的时间 ≈ 手写字节 ÷ (手写字节/内容 token) × 落笔 ms/tok`；三次跑实测比 2.13–2.16 字节/token，跨跑稳定。

**复算**：

```bash
cd /home/xupeipeioo1/apps/skill/clinical-result-comparison
python3 -B tools/semantic-timing.py \
  ~/.local/state/toolsmith-runs/20261013-132120-r60-prose-generic-2 \
  ~/.local/state/toolsmith-runs/20261013-133535-r61-sem-1 \
  ~/.local/state/toolsmith-runs/20261013-134217-r61-sem-2 \
  --artifacts --thinking --json /tmp/semtiming/three-runs.json
```

产出物：`/tmp/semtiming/three-runs.json`（纯 JSON 指标，不含逐步明细）＋ 本文件。
