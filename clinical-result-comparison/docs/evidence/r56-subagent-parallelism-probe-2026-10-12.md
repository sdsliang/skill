# R56 — 子代理并行性三探针（2026-10-12）

**目的**：用户提出「每个证据（每篇来源）开一个 subagent 处理 facts，能不能压缩墙钟」。
该方案成立与否只取决于一件事：**同一轮里多个 `task` 到底是不是并发跑的**。
平台样板段写「Launch multiple subagents **concurrently** … in a single message」，
本仓 `references/input-contract.md:429/453` 却写实测**串行**。两句不能都对 → 用探针判死。

**探针不加载任何 skill、不读参考文件 → 不依赖部署内容，无需发布，零部署漂移。**
三轮都是同一个模型（`DeepSeek Flash`，web=off），时间戳由沙箱内 `date +%s.%N` 自报，
主线程与全部子代理**共用同一条 epoch 时间轴**，因此可以精确判重叠。

---

## 1. 三轮探针与结果

| # | 记录目录 | 子代理 payload | A 窗口 | B 窗口 | 重叠 |
|---|---|---|---|---|---|
| R56-a | `20261012-174039-r56-probe-parallel` | A `sleep 60` / B `sleep 45`（纯 `execute`） | `1791798051.140 → 1791798111.141` | `1791798147.071 → 1791798192.072` | **0.00 s** |
| R56-b | `20261012-175403-r56b-probe-puregen` | 各生成 ~15000 字，**只用 `write_file`，不碰 `execute`** | `1791798871.732 → 1791798916.885` | `1791798888.021 → 1791798948.344` | **28.86 s** |
| R56-c | `20261012-175923-r56c-probe-lock`（resume 记录 `20261012-180330-resume-r56c-probe-lock`） | A/B/C 各 `sleep 20`（三个子代理） | `1791799169.895 → 1791799189.896` | B `1791799192.674 → 1791799212.676`；C `1791799215.468 → 1791799235.470` | **0.00 s**（三段首尾相接） |

三轮都通过**同一条 assistant 消息里的多个 `task` part** 下发（已核对 `messages.json`）：
`msg[1]` 的 part 顺序为 `['reasoning','tool-task','data-subagent-trace','tool-task','data-subagent-trace']`
（R56-c 为三段 `tool-task` + 三段 trace）。即：**模型确实按文档要求并发下发了**。

### R56-a：纯 `execute` payload → 零重叠

`T0 = 1791798046.086` → `T1 = 1791798198.371`，**span 152.285 s**；整轮 `total_latency_ms = 162,272`。
A 窗口 60.00 s，B 窗口 45.00 s，A 结束到 B 开始空档 **35.93 s**。
该空档 = B 首次 `execute`（未传 `timeout_seconds`）被默认 **30 s** 超时杀掉后的重试代价：
B 首条命令返回 `Error: execution timed out after 30s` / exit 124，显式 `timeout_seconds: 90` 才成功。

### R56-b：纯生成 payload（不碰 `execute`）→ **重叠 28.86 s**

- A：`T_start 1791798871.732` → `T_end 1791798916.885`（45.15 s），随后 `write_file /workspace/probe_A.txt`（10 000 字）。
- B：`T_start 1791798888.021` → `T_end 1791798948.344`（60.32 s），`write_file /workspace/probe_B.txt`（8 459 字）。
- **B 的第一条命令跑在 A 的最后一条命令之前**（888.021 < 916.885），且当时沙箱无其它命令占用
  （B 的这条 `date` 是瞬时命令、返回 `exit 0`）→ **A、B 两个子代理同时活着**。
- 并行效率：union 窗口 `8888.021→8948.344` 实为 `8871.732→8948.344 = 76.61 s`；
  若串行应为 `45.15 + 60.32 = 105.47 s` → **实测 76.61 s ≈ 1.38× 加速**。
- `T_all_done = 1791798972.830`，整轮 `total_latency_ms = 131,690`。

### R56-c：三个子代理、各 `sleep 20` → 零重叠，30 s 的活花 70.2 s

```
A  BEG 1791799169.894785539 → END 1791799189.896388346   (20.00 s)
B  BEG 1791799192.674033689 → END 1791799212.675514113   (20.00 s)   交接间隙 2.78 s
C  BEG 1791799215.468239622 → END 1791799235.469726111   (20.00 s)   交接间隙 2.79 s
T_all_done 1791799240.110     整轮 total_latency_ms = 80,734
```
三段严格首尾相接、交接间隙稳定在 ~2.8 s —— 这是**队列/锁**的签名，不是"每个子代理等前一个整轮结束"
（后者间隙会包含整轮调度开销，且 R56-b 已证伪串行）。

---

## 2. 结论（含对前一轮错误结论的撤回）

### ① 子代理**是**并发的 —— 机制由模型决定，TS 开发者说法正确

后端确实按「**同一条 assistant 消息里出现多个 `task` 调用**」并发启动子代理（R56-b 直接证据）。
反过来，若模型分成多条消息逐个发 `task`，那就是串行 —— **并行与否取决于模型的调用形状**，
这正是 TS 开发者的说法。R56-b 已排除"运行器串行"假说。

### ② 真正串行的是沙箱 `execute` —— 全局单通道

R56-a 与 R56-c 的 payload 全是长 `execute`（`sleep`），两轮都是**零重叠 + 稳定交接间隙**。
因此：

- **模型生成会并行**（占本项目输出 token 的 75%）；
- **工具执行不会并行**：主线程与所有子代理的 `execute` 排同一条队。

**撤回**：本批第一次提交（commit `2b476fa`）把 R56-a 的"零重叠"读成"子代理串行"，据此否决
「按证据开子代理」。**该判定错误** —— 把**沙箱队列**误读成**运行器串行**。
R56-a 的 36 s 空档在"并发子代理 + 单通道沙箱 + 超时从命令开始执行时计时"的模型下完全自洽：
B 的命令排队到 A 释放（111 s）后才开始跑，跑满 30 s 默认超时被杀，重试才成功。

### ③ turn 级 `usage.json` **聚合**子代理用量 —— 指标没被绕过

R56-b：两个子代理自报合计 `in 157,335 / out 31,684`（A `in 71,489 / out 14,046 / reasoning 9,300`；
B `in 85,846 / out 17,638 / reasoning 7,436`），而 turn `usage.json` = `in 254,815 / out 35,406 /
reasoning 19,934`，子代理输出占 turn 输出的 **89.5%**。
→ **撤回**前一轮提出的「度量陷阱」：把生成搬给子代理**不会**让 `output_tokens` 指标变好看，
指标仍然诚实。

---

## 3. 对「按证据（按 ref）分片 facts」的重新判定

**不是死路，但收益面比我先前以为的窄，且判据必须重写：**

| | 能否受益于子代理并行 |
|---|---|
| facts 单发长生成（实测一次 `write_file facts.json` = 28,631 token，占该轮输出 43%） | **能** —— 纯生成，可切片并行 |
| `prep_sources` / `build_ledger` / `render-facts` / `patch` / `make_chart` / `make_citations` / `check_report` | **不能** —— 全走 `execute`，排同一条队，分片只会让它们排队 |

代价（都实测过）：

- 每个子代理重新载入**通用**系统提示：R56-b 两个子代理合计 **157,335 输入 token**，
  其中相当部分是每次重载的通用提示（R56-a 里只回一行输出的子代理也要 `in 24,640` / `37,135`）。
- 子代理**不继承本项目 system prompt** → 抽取规格必须在 `description` 里重述。
- 子代理里 `execute` **默认超时 30 s**（主线程文档写 120 s）→ 任何命令必须显式传 `timeout_seconds`。
- 主线程仍必须做跨 ref 合并校验（ref 编号 / 命名 / 数值格式 / `records[].trial` 合并键全局一致）。
- 粒度：本组输入只选 4 篇 → 只能切成 4 片；而墙钟同输入噪声是 **±20–40%**，这个效应量正好在测量能力边缘。

---

## 4. 平台侧发现（供转开发）

1. **沙箱 `execute` 全局单通道**：同一条消息里的多个并发工具调用（含子代理内的）会排队串行执行，
   交接间隙 ~2.8 s。任何"并行工具调用提速"的设计都会撞上这一层。（R56-a / R56-c）
2. **子代理内 `execute` 默认超时 30 s**，与 `execute` 描述里的 120 s 不一致；且该超时**从命令开始执行时**计时
   （排队等待也算在内，R56-a 的 B 因此被误杀）。（R56-a）
3. **`data-subagent-trace`**：每个 `task` 调用附带子代理 `traces[]`（`started`/`tool_call`/`tool_result`/`finished`
   + `input_summary`/`output_summary`/`tool_call_id`）与**子代理独立 `usage`**；该结构未文档化，
   但 turn 级 `usage` 已聚合子代理用量（实测，见 §2③）。

问题单全文写在 Obsidian：`03-技术与VibeCoding/01-AI与LLM/TS子代理并发但沙箱execute单通道串行-子代理execute默认超时30s.md`。

---

## 5. 复现方式

```bash
# 参考 /tmp/probe-puregen.txt（生成型）与 /tmp/probe-lock.txt（工具型）的写法：
#   同一条消息里发多个 task；每个子代理内部用 `date +%s.%N` 自报窗口；
#   主线程前后各取一次 date，最后输出一行 JSON。
cd ~/apps/skill
toolsmith-publish run --prompt-file /tmp/probe-lock.txt --tag r56c-probe-lock
# 掉线后重挂（不重发 POST）：
toolsmith-publish run --resume <thread_id> --tag r56c-probe-lock
```

探针是**非交付型**运行，runner 的产物类断言（`present_artifact` 等）按预期 FAIL，与结论无关。
