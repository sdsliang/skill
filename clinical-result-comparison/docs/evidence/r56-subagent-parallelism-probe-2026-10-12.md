# R56 能力探针 — `task` 子代理到底是并行还是串行（2026-10-12）

**问题**：用户提出「每个证据（每篇来源）开一个 subagent 处理 facts」。该方案只有在子代理**真并行**时才对指标（墙钟）有意义；平台样板段写着
「Launch multiple subagents concurrently by emitting multiple `task` tool calls in a single message」，
而本仓 `references/input-contract.md:429/453` 写着实测**串行**。两句不能都对 → 用一次探针判死。

探针**不依赖任何 skill 内容**，因此无需发布、不产生部署漂移。

## 1. 探针设计

- 线程 `5ce05322-60a5-4395-aad8-94e6f18ee03c`，turn `d1fa6eef-98eb-4ee5-8e85-0394a49dc459`，tag `r56-probe-parallel`
- 记录目录 `~/.local/state/toolsmith-runs/20261012-174039-r56-probe-parallel/`
- 模型 `DeepSeek Flash`，web=off（与既有基线一致）
- 指令：主线程先 `date +%s.%N` 记 T0 → **在同一条消息里**发两个 `task`（A=`sleep 60`，B=`sleep 45`，各带前后 `date +%s.%N`）
  → 两个都返回后再 `date +%s.%N` 记 T1 → 只回一个 JSON
- 判据：真并行 → span ≈ 65–70 s；串行 → span ≈ 110–160 s

## 2. 结果：串行，零重叠

| 量 | 值 |
|---|---|
| T0（主线程开始） | `1791798046.086` |
| T1（两个 task 都返回后） | `1791798198.371` |
| **主线程 span** | **152.285 s** |
| A 窗口 | `1791798051.140` → `1791798111.141` = **60.00 s**（sleep 60，一次成功，显式 `timeout_seconds: 90`） |
| B 窗口 | `1791798147.071` → `1791798192.072` = **45.00 s** |
| A 结束 → B 开始 的间隙 | **35.93 s** |
| **A / B 时间重叠** | **0 s** |
| 整轮 wall（`timing.json.total_latency_ms`） | 162,272 ms |

两个 `task` 写在同一条消息里，平台仍然**先跑完 A 再跑 B**：span = 60 + 45 + 35.9(间隙) + ~11(生成/调度) ≈ 152 s。

**结论：`references/input-contract.md` 的「串行」是对的，平台样板段的「concurrently」是不成立的描述。**

## 3. 顺带查实的三件事

### 3.1 子代理 `execute` 默认超时 = 30 s（文档说 120 s）

B 的 trace 第一条 `execute` 结果：`[stderr] Error: execution timed out after 30s` / `exit code 124`，随后它自己加了
`timeout_seconds: 90` 才成功。而主线程工具描述写的是「Execution is time-limited to 120 seconds」。
→ **任何 `task` 的 description 必须显式要求「沙箱命令一律带 `timeout_seconds`」**，否则子代理里超过 30 s 的命令必然中断并重试（本例重试就白烧了 36 s）。

### 3.2 子代理的轨迹与用量是**可见**的（`data-subagent-trace`）

`messages.json` 里每个 `task` 调用带一个 `data-subagent-trace` part，含该子代理的
`traces[]`（`started` / `tool_call` / `tool_result` / `finished`，带 `input_summary` / `output_summary` / `tool_call_id`）与**独立 `usage`**：

| 子代理 | input | cached | output | reasoning |
|---|---:|---:|---:|---:|
| A | 24,640 | 22,016 | 286 | 186 |
| B | 37,135 | 34,304 | 569 | 399 |
| **合计** | **61,775** | 56,320 | **855** | 585 |

固定开销巨大：一个**只回一行命令输出**的子代理就要 ~25–37 K 输入 token（通用子代理系统提示 + 工具 schema）。
本轮 turn 级 `usage.json` = input 185,072 / output 2,130 / reasoning 1,524 —— 与子代理各自的 61,775 / 855 **看不出被合并**（待定，见 4.2）。

### 3.3 `task` 的入参形状（写进契约时别再猜）

只用两个参数：`subagent_type`（本项目仅 `general-purpose`）+ `description`；**无状态、不可追问**；只回最终消息；
子代理**不继承本项目 system prompt**（本仓 `input-contract.md:450` 已知）；与主线程**共享 `/workspace` 文件系统**。

## 4. 对「按证据开 subagent」这个方案的判定

### 4.1 串行 ⇒ 它**不可能**压缩墙钟（一阶论证，不依赖实测）

一轮的墙钟 = Σ(该轮内**所有**模型生成耗时，主线程 + 所有子代理) + 工具耗时。本轮已证明子代理耗时**计入**整轮 wall（162.3 s 含 60 + 45）。

- 把 facts 撰写从主线程搬给子代理，只是**把生成量换了个地方**，Σ 不变；
- 且**变贵**：每个子代理要重新载入通用系统提示（实测 25–37 K 输入 token/个）+ 重述完整抽取规格（子代理不继承 prompt）+ 重读源文件；
- 还要**在主线程加一轮合并/校验**（跨 ref 的 ref 编号、命名、数值格式、`records[].trial` 合并键仍必须全局一致）。

**所以：串行前提下，按 ref 分片对墙钟是「持平或更差」，不存在变快的路径。** 第 2 步（写分片验收口径）的**前提不成立，不再编写**。

### 4.2 附带发现的**度量陷阱**（若以后仍要引入子代理，先解决这个）

子代理用量记在 `data-subagent-trace.usage`，而 `usage.json` 疑似**只统计主线程**。
若真如此，任何「把活搬给子代理」的改动都会让 `output_tokens`（我们的指标）**很好看**，而墙钟持平或变差 —— 指标会被绕过。
需要一次 90 秒的对照实验才能定：同一指令跑两次（一次带一个「产出 5 K token 长文」的子代理、一次不带），比较 turn `usage.json` 是否随之上涨。

## 5. 沉淀

- 「子代理 = 省上下文的装置，不是并行提速」现在有**直接实测**（此前只有断言）：`input-contract.md` 的表述可升级为「实测（R56 探针，2026-10-12，60+45 s 睡眠零重叠）」，但那是 skill 内容改动 → **需一次发布授权**，本轮只登记不改。
- 平台侧（转开发）：① 工具描述承诺并发、后端从不开启并发；② 子代理 `execute` 默认超时 30 s 与文档 120 s 不一致；③ `data-subagent-trace` 未文档化（含子代理独立 usage）。
  → 问题单全文见 Obsidian `03-技术与VibeCoding/01-AI与LLM/TS子代理声称并行实测串行且子代理execute默认超时30s.md`（本仓只留摘要）。
