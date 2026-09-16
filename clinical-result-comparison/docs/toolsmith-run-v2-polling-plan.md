# `toolsmith-publish run` v2：SSE 消费 → 线程状态轮询（方案，**待执行**）

> **状态：方案，未执行。** 本文只沉淀设计与证据，**没有改任何代码、没有发布、没有 commit**。
> 拟于 2026-09-14。接手者先读第 2 节（修订对照）和第 9 节（执行闸门）。

**触发**：ToolSmith 开发两次反馈 —— ①「你怎么还要消费 SSE 啊，不是应该调一次就直接用 TS 的前端看吗」；
② 被问到非流式怎么做时答「非流式要不就用 webhook，要不就轮训 thread 状态，等 running 结束了再去取」；
③ 最后「你自己看代码吧」。复核 `apps/tool-smith` 源码后：**开发是对的**，现有 `run` 把最脆弱的通道
（长连接 SSE）当成了主通道，而它承载的只有 3 类事件是有用的。

---

## 0. TL;DR

| # | 结论 | 依据 |
|---|---|---|
| 1 | **轮询成立**：run 是独立 asyncio 任务，客户端断开只移除订阅者，不 cancel 任务，事件仍进 buffer | `run_manager.py:229-233`（`create_task`）、`subscribe()` 的 `finally` 只 `subscribers.remove(q)` |
| 2 | **终态只能认 `/info.status`**，值域 `running/cancelling/completed/cancelled/failed/未知`；且终态只保留 **300–360 s** | `chat_routes.py:352-353`；`run_manager.py:470-480` + `536-540` |
| 3 | **`/timing` 不能用来判活**：`active_turn` 不判状态、`latency_ms` 每请求现算 → 跑完的 run 5 分钟内仍显示"进行中、耗时还在涨" | `chat_service.py:859-874` |
| 4 | **幂等**：自己生成 `turn_id`，重复 POST 同一 `turn_id` → `409 Turn already exists`（不会重复执行） | `chat_service.py:1502-1505` |
| 5 | **webhook 是项目级、不能按请求带**，且 url 空/events 非法时**只写 warning 日志、配置整体失效** | `schemas/webhook.py:70-84`；`db/models/agent_project.py:20-22` |

**方案一句话**：`POST /api/chat` 后**只读到 `data-turn-start` 就断开**，然后按 ≤60 s 间隔轮询 `/info.status`
判终态、`/timing` 取永久耗时，证据全部从 `/debug/history` + `/messages` + artifacts 拉；工具调用链与工具报错
改从持久化消息里重建，**SSE 不再是任何断言的输入**；`turn_id` 先落盘以支持 `--resume`。

---

## 1. 五条结论的源码依据（行号按 **prod** 修订，见第 2 节）

### 1.1 轮询可行：run 与客户端连接解耦

- `run_manager.activate_run()` 里 `asyncio.create_task(coro)` 起后台任务（`run_manager.py:229-233`）。
- `subscribe()` 只是把队列挂到 `run.subscribers`，客户端断开走 `finally` 移除队列（`run_manager.py:445-468`）。
- 完成时 `complete()` 只置状态 + `events.clear()`（`run_manager.py:418-441`），**不 cancel、不 pop registry 条目**。
- 文档亦记（我们实测过的那次）：客户端断线不会暂停后台 run。

### 1.2 终态判定与可见窗口（**最关键**）

```python
# api/routes/chat_routes.py:352-353   (GET /api/threads/{id}/info)
active = run_manager.get_active_run(thread_id)
current_status = active.status if active and active.user_id == current_user.id else "未知"
```
- `get_active_run()` = `self._runs.get(thread_id)`（`run_manager.py:281-282`），**无状态过滤**。
- `complete()` 置 `completed|failed|cancelled` + `completed_at`，条目留在 `_runs` 里。
- 清理只在 `cleanup_stale(max_age_seconds=300)`：删除 `status != "running" and completed_at is not None and age > 300s`
  的条目（`run_manager.py:470-480`），由 `periodic_cleanup(interval=60, max_age=300)` 每 60 s 触发
  （`run_manager.py:536-540`；调用点 `server.py:164` 用默认参数）。
- → **结局在内存里只活 300（+ 最多 60）秒**，之后 `/info.status` 永久变 `未知`。
- → **轮询间隔 ≤ 60 s 即可保证不漏终态**（本方案取 15–30 s）。
- `"未知"` 有三种含义，必须区分：① 预检阶段（reservation，**此刻 DB 里还没有 turn**，`/info` 不看 reservation）；
  ② 已跑完且被清理；③ **从未启动**（docs：项目校验/资源准备/附件预检失败时不会启动 Agent run）。

### 1.3 `/timing` 的两个坑（我们上次就栽在这里）

```python
# services/chat_service.py:859-874   (get_thread_timing)
runtime = self.run_manager.get_active_run(thread_id) or self.run_manager.get_reservation(thread_id)
if runtime is not None:
    latency = max(0, (perf_counter_ns() - runtime.monotonic_started_ns) // 1_000_000)
    active = TurnTimingRecord(..., completed_at=None, latency_ms=latency, completed=False)
    timings[runtime.turn_id] = active        # 覆盖 DB 里的真实记录
```
- **坑 A**：跑完但还没被清理的 run，`active_turn` 仍报 `completed=False` + `completed_at=None`。
- **坑 B**：`latency_ms` 是现算的 → **"耗时还在涨"不是存活的证据**（推翻了早期"latency 不涨=stall"的想法）。
- **坑 C**：`timings[runtime.turn_id] = active` **覆盖**了 DB 值 → 在 300–360 s 窗口内
  **`turns[<turn_id>].completed` 恒为 `false`**，"用 completed 判终态"这个写法在窗口内读不到。
- `turns[]` 本身来自 DB 的 user 消息行（`_build_turn_timing_map`，`chat_service.py:3115-3132`，`completed = timing_completed_at is not None`），
  永久可读，但**只有耗时、没有结局**（成功/失败/取消不落库）。
- 文档 `chat-api.mdx` 写"活动 run 的 `latency_ms` 是实时值，**完成后冻结**" → **与代码不符**（见 §8.1）。
- 实测：一个 run 的服务端 `completed_at` 已落库，53 s 后拉 `/timing` 仍返回 `completed:false` 且 latency 更大。

### 1.4 幂等：自己生成 `turn_id`，撞车吃 409

```python
# services/chat_service.py:1502-1505
if await self.thread_repository.turn_exists(turn_id=turn_id, thread_id=thread_id, user_id=user_id):
    raise Conflict("Turn already exists")
```
→ 重试用**同一个** `turn_id` 永远不会重复执行。这是 `--resume` 该依赖的机制，而不是"重连 SSE"。

### 1.5 webhook：项目级、不能按请求带、失效静默

- 配置只存在项目上（`db/models/agent_project.py:20-22` 的 `webhook_config_json`）；请求体字段只有
  `thread_id/model_id/project_id/enable_web/reasoning_effort/turn_id`（`schemas/chat.py`），**无 per-request 回调**。
- `url` 空/缺失 → `return None`；`events` 非法 → `logger.warning("webhook.config.parse_failed")` + `return None`
  （`schemas/webhook.py:70-84`）→ **API 侧看不出配置已失效**。
- 投递：10 s 超时、3 次重试、无签名、只有 `X-Toolsmith-Event` 头（`webhook_dispatcher.py:26,43,50-78`）。
- 唯一比轮询强的地方：**推送里有结局 + `termination_reason` + usage + artifacts**。
- **决策**：主线轮询；webhook 留作"以后无人值守批量"的备选。
  **不要为了验证去改项目 webhook 配置**（会污染线上项目配置，且属于写动作）。

### 1.6 force-kill 的形状

10 分钟无新事件 → `cancelling` → `failed` + `termination_reason="timeout"`（`run_manager.py:482-514`、`522-532`）。
→ 轮询只能看到 `failed`，**分辨不出是不是超时**；`termination_reason` 只在 webhook 里出口。

---

## 2. 证据地图与修订对照（接手必读）

| 位置 | 修订 | 备注 |
|---|---|---|
| 本地 `/home/xupeipeioo1/apps/tool-smith` | **`50f048b`**（master，工作区干净） | 本次读的代码 |
| `origin/master` | **`34215c3`**（`fix tool schema and docs`） | 比本地多 1 个 commit |
| **prod**（`prod/deployments/788-789`）= `$TS_BASE`（内网地址见 `~/.secrets`） | **`5a44c19`** = `release-2026-09-10` | **线上真正在跑的** |
| test（`test/deployments/798-799`） | `34215c3`；上一跳 797 = `50f048b` | test 已在跑 master |

- 上述 5 个证据文件（`chat_service.py` / `run_manager.py` / `chat_routes.py` / `webhook_dispatcher.py` / `schemas/webhook.py`）
  在 **`50f048b` 与 `34215c3` 逐字节相同**；`5a44c19 → 50f048b` 只差 `chat_service.py` 的 48/20 行
  （`usage_limits` 配置化、token 统计修正、metadata chunk），**不涉及 timing/info/status/webhook**。
- 结论已在 **prod 修订上逐条复核**（`git show 5a44c19:...`）。**本文行号按 prod 给**；本地对应位置差几行
  （如 409 在本地是 `:1505`，prod 是 `:1502`；`periodic_cleanup` 调用点本地 `server.py:197`、prod `:164`）。
- `34215c3` 改了 `frontend/content/docs/integrate/{chat-api,streaming,attachments}.mdx` → **线上文档是旧版**，
  新文档有一条直接影响实现（见 §3.3）。

---

## 3. 我们自己的运行数据（`~/.local/state/toolsmith-runs/`）

（下表已按 `verification.md` 的 `thread:` 行逐一核对过，勿再凭记忆填）

| run dir（`~/.local/state/toolsmith-runs/`） | thread | 事件数 | `reasoning-delta` | `tool-input-delta` | `tool-input-available` | `tool-output-error` | 持久化 `tool-call` | `retry-prompt` | `stream.sse` | `debug-history.json` | 墙钟(客户端) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `20260914-171953-cite-date` | `61e5d232-519f-40ab-826d-6e2ceb1b423f` | 22 430 | 16 081 | 6 152 | 21 | 0 | 21 | 0 | 2.19 MB | 2.67 MB | 128.1 s |
| `20260914-173645-a-2valid` | `6ad0dcee-9f53-42a2-b907-48f1b18b418c` | 34 302 | 24 839 | 9 217 | 23 | 0 | 23 | 0 | 3.41 MB | 3.61 MB | 173.7 s |
| `20260914-173947-b-refusal` | `49653f36-32d0-4a91-86f4-58fb1a4357f9` | 3 785 | 2 295 | 1 118 | 8 | 0 | 8 | 0 | 0.42 MB | 1.33 MB | 36.8 s |
| `20260914-174145-b2-refusal` | `73b427f3-3d19-4819-8228-4460e65a9d2b` | 3 977 | 2 189 | 1 375 | 8 | 0 | 8 | 0 | 0.45 MB | 1.24 MB | 33.9 s |
| `20260914-174222-a2-2valid` | `a0420a2f-c1a4-4443-a749-0547eeb43941` | 34 626 | 22 256 | 12 075 | 40 | 0 | **41** | **1** | 3.53 MB | 5.80 MB | 208.4 s |

- **结论：98–99% 的事件是 `reasoning-delta` + `tool-input-delta`，我们一条都不用。**
  `parse_stream()` 真正取用的只有 `tool-input-available` / `tool-output-available` / `tool-output-error`（每轮 8–41 条）。
- **5 次运行累计 0 个 `tool-output-error`** → "无工具报错"这条断言**没有失败样本**（见 §7 T1）。
- 注意 `a2-2valid` 那行：**41 次 tool-call 只有 40 次 tool-return，而流里只有 40 个 `tool-input-available`** —— 见 §3.2。
- `stream.sse` 0.4–3.6 MB/次，而 `debug-history.json` 是同一批数据的结构化版本（1.3–5.9 MB），
  本来就要拉。**所以换轮询主要收益是"健壮性 + 单一事实来源"，不是省磁盘。**

### 3.1 持久化里有什么（已实测，供断言重建用）

`debug-history.json` 的 `raw_model_messages`（32 条）part_kind 分布：
`user-prompt 1 / thinking 15 / text 3 / tool-call 21 / tool-return 21`。

```json
// tool-call part
{"part_kind":"tool-call","tool_name":"load_skill","args":"{\"skill_name\": \"...(JSON 字符串)\"}",
 "tool_call_id":"call_00_ijECi…","tool_kind":null,"id":null,"provider_name":null,"provider_details":null}
// tool-return part
{"part_kind":"tool-return","tool_name":"execute","content":"rows: 3\n---\n…",
 "outcome":"success","metadata":{…},"timestamp":…,"tool_call_id":"call_00_…","tool_kind":null}
```
`raw_ui_messages`（17 条）part types：`text 4 / reasoning 15 / tool-<name> 21 / data-sql 8 / data-table 3`，
tool part 形如 `{"type":"tool-load_skill","toolCallId":"call_…","state":"output-available",…}`。

→ **工具调用链可从 `raw_model_messages` 的 `tool-call`（`tool_name` 顺序）重建**；
**工具报错的两个候选信号**：① `tool-return.outcome != "success"`；② `raw_ui_messages` 的 `tool-*.state == "output-error"`。
现有代码已经在读同一个 dump（`check_run` 用 `part_kind == "tool-return" and tool_name == "load_skill"`），
所以形状是已验证的。

### 3.2 `retry-prompt`：持久化消息能看到 SSE **根本看不见**的东西（新增证据）

`a2-2valid` 那个不配对的调用（`call_00_gdum0r7eAWad9Uimjmto4976`）在持久化里长这样：

```
msg[55] tool-call   read_file  …  outcome=None
msg[56] tool-return read_file  …  outcome=success
msg[57] tool-call   execute    call_…to4976  args={"command": "cd /workspace && grep -n …"}
msg[58] retry-prompt         call_…to4976  content=[{"type":"missing","loc":["shell_command"],"msg":"Field required"},
                                             {"type":"extra_forbidden","loc":["command"],…}]
msg[59] tool-call   execute    call_…n79878  args={"shell_command": "cd /workspace && grep -n …"}   ← 自愈重试
msg[60] tool-return execute    call_…n79878  outcome=success
```

- **成因**：模型把 `shell_command` 写成了 `command` → 参数 schema 校验失败 → 框架回 `retry-prompt` → 模型换正确参数重发成功。
  这正是 R1 记过的 `INVALID_INPUT`（模型自创字段名）那一类。
- **关键点**：整条链在 SSE 里**只留下 1 个 `tool-input-start`，既没有 `tool-output-available` 也没有 `tool-output-error`**
  （该轮 `tool-output-error = 0`）→ **旧的三条 SSE 断言完全看不到这次参数返工**，而持久化消息一眼可见。
- 5 次运行里 `retry-prompt` 恰好 1 次，都在 `a2-2valid`。
- → **证据源换成持久化消息不仅等价，还严格更强**；顺手把 `retry-prompt` 次数记进 `verification.md`（模型返工的可观测指标，对应台账 O4/O8 类问题）。

### 3.3 现有 `run` 的哪几项断言真的依赖 SSE

`check_run()` 里只有 **2/13** 项（+ `--expect refusal` 里 **2/4** 项）吃 `parse_stream()` 的产物 `st`：

| 依赖 | 断言 |
|---|---|
| `st["calls"]` | 「末尾工具 == `present_artifact`」；refusal 里的「确实查过（`a.tool` 出现过）」 |
| `st["errors"]` | 「无工具报错」；refusal 里的「无工具报错」 |
| 其它 11 项 | 全部来自 `b["history"]` 或 `b["zip"]`（artifacts / report / citations），**与 SSE 无关** |

`cmd_run()` 打印的"tool calls"直方图和 `verification.md` 的"工具调用链"也来自 `st["calls"]`。

### 3.4 master 新文档带来的两条实现注意

- ToolSmith 字段命名**统一 snake_case**（`turn_id` / `thread_id` / `project_id`）；Chat 体里 camelCase 仍兼容。
  现工具只发 `threadId` + 查询串。**改法：body 里同时发 `turn_id` 与 `turnId`（同值 UUID v4）**，
  无论 prod 读哪个，落库的 `turn_id` 都是我们那个（见 §7 T2）。
- `messages` **只需带本轮最后一条、且 `role` 必须是 `user`**，历史由线程维护。

---

## 4. 新判定状态机

```text
turn_id = uuid4()                                   # 落盘后再发（§5.7）
POST /api/chat  (body 带 thread_id/turn_id + query 保留以兼容 prod)
  ├─ 2xx  → 只读到第一个 data-turn-start 事件（有界 20 s）后关闭连接
  │         读不到/断开 → 静默降级，直接进轮询（不是错误）
  └─ 409 Turn already exists → 不是错误，直接进轮询（幂等保护生效）
    其他 4xx/5xx → exit 4（预检失败，run 未启动）

loop 每 15–30 s，墙钟上限 = --timeout（默认 2400 s）:
  s = GET /api/threads/{tid}/info → status
    running | cancelling              → 打印进度（status + steps + 已耗时），继续
    completed                         → DONE(ok)
    failed | cancelled                → DONE(bad)；再扫持久化消息取 error_type 写进 verification.md
    "未知" → GET /api/threads/{tid}/timing
        active_turn.turn_id == turn_id       → 预检/准备阶段，继续等
        turns[turn_id] 存在且 completed      → 跑完了但结局已被清理 → INCONCLUSIVE
        turn 记录不存在 → 若已过 grace(默认 120 s) 且从未见到 running → 从未启动 → exit 4
                        → 否则（刚 POST 完）继续等

DONE 之后：
  bundle = timing / usage / info / messages / debug-history / artifacts / artifacts/archive
  断言（§5.5）→ 写 verification.md + transcript.md → exit
```

**不变量**
- 超时/异常**绝不重新 POST**（会重复执行 + 烧 token）；只能 `--resume <thread_id>`。
- 终态判据**只认 `/info.status`**；`/timing` 只用于"永久耗时 / 是否已落库 / 是否在准备阶段"。
- 轮询间隔 ≤ 60 s（终态窗口下限 300 s）。
- 客户端没有任何"必须保持的连接"。

---

## 5. 改动清单（目标文件 `~/.local/bin/toolsmith-publish`，1324 行；**不进任何仓库**）

### 5.1 `run_chat()`（现 `450-499`）→ 拆成 `start_turn()` + `wait_for_run()`

- 保留：建线程（`POST /api/threads`）、body 构造、`assert_owned_project` 前置护栏。
- body 增加 `"turn_id": tid_uuid`（与 `turnId` 同值，§3.3）；`POST /api/chat` 的 HTTP 错误处理保留（非 2xx → exit 4）。
- SSE 读循环（现 `while True: resp.readline()`）→ 改成 **有界读**：最多读 N 行 / 20 s，命中 `data-turn-start` 即 `resp.close()`。
  读到的内容（若有）写到 `stream.tap`（可选，**不再是断言输入**）；默认保留这个 tap 以便排障，`--no-tap` 关闭。
- **删掉**"流断=失败"的隐含语义：任何流异常都只打印一行 warning。

### 5.2 新增 `wait_for_run(c, tid, turn_id, timeout, grace, interval)` 

- 实现 §4 的状态机，返回 `{"kind": "completed|failed|cancelled|inconclusive|not_started", "wall_clock_s":…, "polls":[…], "terminal_seen": bool}`。
- 进度行示例：`[ 45s] status=running steps=8`（`steps` 取 `/info.stats.steps`；best-effort，失败则省略）。
- 轮询失败（网络抖动）→ 重试该次，不改变状态机判定；连续 N 次失败才报错。

### 5.3 新增 `tool_chain_from_history(history)` —— 取代 `parse_stream()`

- 返回与旧 `st` 同构的 `{"calls": [(call_id, name, args_dict), …], "outputs": {…}, "errors": [str, …]}`，
  数据源 = `raw_model_messages` 的 `tool-call` / `tool-return`（§3.1）。
- `args` 是 JSON 字符串 → 解析失败时保留原串（不要抛）。
- `errors`：`tool-return.outcome` 非 `success` 的条目 + （可选）`raw_ui_messages` 里 `state == "output-error"` 的 tool part。
  **首次遇到非 success 时把原始 part JSON 打到 `verification.md` 的 findings 区**，人工确认形状后再收紧断言（§7 T1）。
- 额外返回 `{"retries": [...], "unmatched": [...]}`：
  - `retries` = `part_kind == "retry-prompt"` 的条目（模型工具参数非法被框架打回、随后自愈）→ **只记数、不判失败**，
    但大于 0 时在 `verification.md` 里列出 `tool_name` + `content[].loc`（哪几个字段写错了）。
  - `unmatched` = 有 `tool-call` 无 `tool-return` 的调用。**判为 WARN 而不是 FAIL**：`a2-2valid` 证明正常通过的运行
    也会出现这种条目（成因就是上面那个 `retry-prompt`）。可按是否紧跟 `retry-prompt` 分成
    「参数返工（可接受）」与「真中断（要报）」两类。

### 5.4 `thread_bundle()`（现 `523-542`）增补

- 新增拉取：`/api/threads/{tid}/messages`（**前端渲染的那一份**，前端 `ChatPage` 读它 → AI 与你复核同一份数据），
  落 `messages.json`。
- 用 `/info.usage`、`/info.turn_usage`、`/usage` **三种口径**分别记录（master 文档明确三者范围不同：最后一步 /
  最近一轮含子 Agent / 全线程含子 Agent），**断言里不得互相比较**。
- `/info.estimate`（`system_capability_tokens` / `mcp_tokens` / `tools_tokens` / `skill_tokens` / `conversation_tokens` / `cache_rate`）
  记入 verification.md 头部（成本可观测，不做硬断言）。
- `/info.status` 的终态值也要落盘（它是"结局"的唯一来源）。
- `limits` 保留。

### 5.5 `check_run()`（现 `543-658`）断言重映射

13 项中 11 项完全不动（来源是 history / zip）。改 2 项 + 新增 2 项：

| 断言 | 旧来源 | 新来源 |
|---|---|---|
| 末尾工具 == `present_artifact` | `st["calls"][-1]`（SSE） | `tool_chain_from_history` 的 calls 末项 |
| 无工具报错 | `st["errors"]`（SSE `tool-output-error`） | `tool-return.outcome != "success"`（+ UI `state=="output-error"`） |
| **新**：每个 tool-call 都有 tool-return | — | 持久化消息配对（**WARN**，见 §5.3） |
| **新**：`/info.status` 终态 == completed | — | `/info.status`（失败/取消不再只表现为"流断了"） |
| **新**：`retry-prompt` 计数入册 | — | 持久化消息（SSE 完全看不到，§3.2） |

`--expect refusal` 4 项同理（"确实查过" 与 "无工具报错" 两项换源）。

### 5.6 `cmd_run()`（现 `659-731`）输出 / 退出码 / 产物

- 打印：`status`（终态）+ 服务端耗时 + 客户端墙钟 + 轮询次数 + token 三口径 + 工具直方图。
- **退出码**：`0` 全过 / `3` 跑完但有断言失败、工具报错、或终态 != completed / `4` 未启动（POST 失败或 grace 内无 turn 记录）/ `5`（新增）结局不可判（`inconclusive`：跑完但终态窗口已过）。
- `verification.md` 头部增加：`status`、`turn_id`、`polls`、estimate、三口径 token。
- 失败时把持久化里带 `error_type` 的 text part 原文抄进 findings（`chat_service.py:2989-3029` + `2248-2257` 会归一化 `error_type`）。

### 5.7 新增 `run.json`（落 out_dir）+ `--resume`

```json
{"thread_id":"…","turn_id":"…","model":"…","project_id":"…","tag":"…",
 "prompt_sha256":"…","started_at":"2026-09-14T…Z","status":"running|completed|…"}
```
- `POST` 之前先写（`turn_id` 必须在网络调用前落盘）。
- `run --resume <thread_id>`：跳过建线程与 POST，直接 `wait_for_run` + bundle + 断言。
- 进程被杀/断网/流断后，用 `--resume` 从平台侧捞回，**不重复执行**。

### 5.8 新增 `transcript.md`（给人看的那一份）

- 由 `/messages`（或 `raw_ui_messages`）渲染：按 part 顺序输出 `text` / `reasoning`（可折叠/摘要）/ 每个工具调用的
  `name` + 入参摘要 + 输出摘要 / `data-sql`、`data-table` 摘要。
- 目的：**"AI 先看（程序化证据），人再看（同一份数据的人读版）"**，替代现在那个 2–3 MB 没人会读的 `stream.sse`。
- 不再默认保留 `stream.tap`（`--no-tap` 变默认；需要排障时显式开）。

### 5.9 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--poll-interval` | 20 s | ≤60 s 硬上限（超过直接拒绝并提示终态窗口） |
| `--grace` | 120 s | `未知` + 无 turn 记录 判定"从未启动"的宽限 |
| `--timeout` | 2400 s | 轮询墙钟上限（服务端 10 min 无事件会自己 force-kill） |
| `--no-tap` | 关（v2 后默认 tap 关闭） | 不读那一行 SSE 确认事件 |
| `--resume` | — | 从 thread_id 续（需 `run.json` 或显式给 `--turn-id`） |
| `--turn-id` | 随机 UUID4 | 便于人工指定重放边界 |

---

## 6. 产物与退出码对照

| | v1（现在） | v2（方案） |
|---|---|---|
| 主等待机制 | 消费 SSE 直到流结束 | 轮询 `/info.status`（≤60 s） |
| 断线后果 | 断言/证据可能不全（流是断言输入） | 无影响（流非断言输入） |
| 并发/后台 | 长连接常驻 | 纯短 GET |
| 产物 | `stream.sse`（0.4–3.6 MB）+ debug-history + artifacts + verification.md | `messages.json` + `debug-history.json` + artifacts + **`transcript.md`** + `run.json` +（可选 `stream.tap`）+ verification.md |
| 幂等 | 靠流不重复 | 靠 `turn_id` + 409 |
| 断点续跑 | 无 | `--resume` |
| 退出码 | 0 / 3 / 4 | 0 / 3 / 4 / **5（结局不可判）** |

---

## 7. 待验证项（**不要凭感觉写死**）

| # | 不确定 | 验证方法 | 兜底 |
|---|---|---|---|
| T1 | 工具报错在持久化消息里的确切形状（我们 5 次运行 0 个 `tool-output-error`，**无失败样本**） | 造成一次真实工具失败（例如让 MCP 参数非法 / 断网），然后 dump `tool-return.outcome` 与 `tool-*.state` | 断言先写成"配对齐全 + 打印非 success 原文"，样本确认后再收紧 |
| T2 | **prod（`5a44c19`）是否认 body 里的 `turn_id`**（新文档说 snake_case 为准，线上文档是 camelCase） | 一次真跑后拉 `/timing`，看 `turns[].turn_id` 是否 == 我们发的那两个同值 UUID | 两个键同值发送 → 无论读哪个结果一致 |
| T3 | "客户端断线不停"的一次可复现实测（代码已确认，运行期只做过半次记录：`a0420a2f` 那次日志实际是正常跑完 208 s，"流中途断"是我另一次人工实验，**证据不完整**） | `curl` 发起后 30 s 掐断 → 等 3 min → `/timing` 看服务端是否到 `completed_at` | 已由源码确认，实测只作台账补证 |
| T4 | `/info.status` 在 force-kill 时是先 `cancelling` 后 `failed`（代码如此），轮询是否可能恰好只看到中间态 | 轮询间隔 20 s 下持续观察；或人为超时 | 把 `cancelling` 当作"继续等"，不判终态 |

---

## 8. 平台侧缺口（→ 问题单 P7 / P8，全文写 Obsidian，仓库只留摘要）

> **口径（用户 2026-09-14 定）：以代码为准。后续发现的平台文档/文档缺口一律不上报**，只留内部存档。
> 只报会直接影响"我们能算/能跑"的功能性缺陷 —— P7、P8 属此类；原拟报的 P9（纯文档不一致）**已撑回**，移到 §8.1 存档防踩坑。

| # | 现象（有源码/实测依据） | 影响 | 建议 |
|---|---|---|---|
| P7 | `/timing.active_turn` **不判状态**：跑完但未清理的 run 仍报 `completed=false`、`completed_at=null`、`latency_ms` 现算递增（`chat_service.py:859-874`） | 任何客户端都会把已结束的 run 判成"仍在跑"；我们实测到 53 s 滞后 | `status != running` 时 `active_turn` 归 null，或另给 `last_turn_status` |
| P8 | **run 结局（成功/失败/取消）不落库**，只在内存活 300–360 s；轮询间隔 >5 min 就无法区分成功/失败/force-kill | 慢轮询客户端只能翻 message 里的 `error_type` 反推；同样地 `webhook_config` 解析失败只写 `logger.warning`（`schemas/webhook.py:76-84`），配置静默失效且读接口看不出 | 把终态（含 `termination_reason`）落到 turn 并暴露在 `/timing` 或 `/info`；项目读接口回显一个 `webhook_config_effective` 之类的字段 |

**动作（✅ 2026-09-14 已做）**：P7/P8 已追加到 Obsidian `03-技术与VibeCoding/01-AI与LLM/ToolSmith-平台问题单-ChatAPI与SSE文档缺口.md`（作为该问题单的"第二批"），
仓库台账只留摘要 + 指向。

### 8.1 内部的文档坑（**不对外报**，实现时别信文档）

- `chat-api.mdx` 说"活动 run 的 `latency_ms` 完成后冻结"→ 实际要等 `cleanup_stale`（约 300 s）才冻结（§1.3 坑 B）。
- `streaming.mdx` 没写重连接口（实为 `GET /api/chat/{thread_id}/stream`），且**只在 `running` 有效、其余一律 204**（`chat_routes.py:895-905`）；
  非流式（轮询 / webhook）也没有推荐做法 —— 本文 §4 就是我们的做法。
- 这些**只归档、不转开发**；结论以 prod 源码为准（§10 有一键复核命令）。

---

## 9. 执行顺序与闸门（**下一步该做什么，以及哪里必须停下问人**）

1. **先确认 §7 T2/T3**（一次真跑即可同时回答 T2 与补 T3 证据；真跑是写动作，**需用户同意**）。
2. 改 `~/.local/bin/toolsmith-publish`（§5）。**动手前先向用户说明要改哪些函数**，并先备份
   （`cp ~/.local/bin/toolsmith-publish ~/.local/state/toolsmith-publish/toolsmith-publish.v1.bak`）。
3. **干跑校验**：用一个已知完成的 thread 验证 `tool_chain_from_history()` 能重建出与旧 `parse_stream()` **完全相同**的
   调用链（用 `~/.local/state/toolsmith-runs/20260914-171953-cite-date/` 做对照：
   期望 `load_skill×1, pharmcube-query-…×8, execute×8, read_file×3, present_artifact×1`，共 21 次）。
   这一步**不需要任何网络**，是最便宜的回归闸门。
4. ✅（2026-09-14 已完成）§8 的 P7/P8 已追加进 Obsidian 问题单；**文档缺口不再上报**（P9 降级为 §8.1 内部存档）。
5. 一次真跑验证 v2（写动作，**需用户同意**）：`toolsmith-publish run --prompt-file … --tag v2-poll`，
   期望 `transcript.md` / `run.json` / 无 `stream.sse` / 轮询次数在 10–15 次 / 13 项断言与 v1 结论一致。
6. 更新 `docs/toolsmith-verification-log.md`（新增 `R8` 记录 + 两栏台账）与 `PROJECT_STATE.md`。
7. **发布/commit 都不是本方案的一部分**：`run` 工具不入仓库；skill/sys 本次不改 → **无需 Toolsmith 发布**。
   若后续动了 `skill/` 或 `system-prompts/`，仍按老规矩：先问"要不要推 ToolSmith"→ 发布 → `status` 回读绿 → 再问 commit。

**红线（写进实现注释）**
- 超时**绝不重新 POST** `/api/chat`；只允许 `--resume`。
- 不改项目 webhook 配置。
- 不把 `stream.sse` 重新变成任何断言的输入。
- 轮询间隔 > 60 s 直接拒绝（会丢终态）。

---

## 10. 复现命令附录（只读，随时可跑）

```bash
cd /home/xupeipeioo1/apps/tool-smith

# 修订对照
git log -1 --format='%H %s' 5a44c19c 50f048bc 34215c30
git ls-remote origin refs/heads/master 'refs/environments/prod/deployments/*' | tail

# 证据文件在三个修订上是否一致（空=一致）
git diff --stat 5a44c19c 50f048bc -- backend/src/toolsmith/services/{chat_service,run_manager}.py \
  backend/src/toolsmith/api/routes/chat_routes.py backend/src/toolsmith/services/webhook_dispatcher.py \
  backend/src/toolsmith/schemas/webhook.py

# 逐条复核结论（prod 修订）
git show 5a44c19c:backend/src/toolsmith/api/routes/chat_routes.py | sed -n '352,353p;895,913p'
git show 5a44c19c:backend/src/toolsmith/services/chat_service.py  | sed -n '859,875p;1502,1505p'
git show 5a44c19c:backend/src/toolsmith/services/run_manager.py   | sed -n '418,441p;470,480p;536,540p'
git show 5a44c19c:backend/src/toolsmith/schemas/webhook.py        | sed -n '70,84p'

# 运行期只读探测（PAT 在 ~/.secrets 的 TS_BASE / TS_TOKEN）
. ~/.secrets
curl -s -H "Authorization: Bearer $TS_TOKEN" "$TS_BASE/api/threads/<tid>/info"   | python3 -m json.tool | head -20
curl -s -H "Authorization: Bearer $TS_TOKEN" "$TS_BASE/api/threads/<tid>/timing" | python3 -m json.tool | head -40

# 本地回归对照（不需要网络）
cd ~/.local/state/toolsmith-runs/20260914-171953-cite-date && python3 - <<'EOF'
import json, collections
h = json.load(open("debug-history.json"))
c = collections.Counter(p["tool_name"] for m in h["raw_model_messages"] for p in (m.get("parts") or [])
                        if p.get("part_kind") == "tool-call")
print(c, "total", sum(c.values()))          # 期望 21 次
EOF
```

---

## 11. 交接清单（给下一个 session）

- 要读的代码：`~/.local/bin/toolsmith-publish` 的 `run_chat()` `parse_stream()` `thread_bundle()` `check_run()` `cmd_run()`。
- 要读的上游：`apps/tool-smith` 的 `services/run_manager.py`、`services/chat_service.py`（timing 段 + 409 段）、
  `api/routes/chat_routes.py`（info / resume）、`schemas/webhook.py`。
- 不要做的事：重新 POST；改 webhook 配置；把 SSE 当断言输入；未经同意真跑或 commit。
- 本方案不涉及 `skill/` / `system-prompts/` → 不触发 Toolsmith 发布流程。
