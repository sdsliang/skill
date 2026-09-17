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
- 文档 `chat-api.mdx` 写"活动 run 的 `latency_ms` 是实时值，**完成后冻结**" → **与代码不符**（见 §8.2）。
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
  s = GET /api/threads/{tid}/info → status            # 2026-09-16 起只可能是这四个值
    preparing | running | cancelling  → 活的：记住 last_live、打印进度、继续等
    completed | failed | cancelled    → 老部署（30306cb 之前）的终态，兼容保留
    idle（或 status 读不到，如 thread 不存在）
        → 本进程没有活的 run，**但这不是结局**（结局已从 API 里删掉）：
          GET /api/threads/{tid}/timing
            turns[turn_id].completed_at 有值 → DONE(completed, durable)；这也是常规路径
            turns[turn_id].completed=true 无时间戳 → INCONCLUSIVE（已知完成但无法证明）
            都没有：连续两次 idle 才肯认；
              见过活状态 → INCONCLUSIVE（进程重启/回收，再等也等不到）
              从未活过 + 过了 grace → GET /api/thread-turns/validate
                  exist != true → 从未启动 → exit 4；exist == true → 继续等

DONE 之后：
  bundle = timing / usage / info / messages / debug-history / artifacts / artifacts/archive
  outcome = classify_outcome(messages, turn_id)         # error_type / state=interrupted
  kind == completed 而 outcome 是 failed/cancelled → kind 改成对应值（不再报成功）
  断言（§5.5）→ 写 run.json + verification.md + transcript.md → exit
```

**不变量**
- 超时/异常**绝不重新 POST**（会重复执行 + 烧 token）；只能 `--resume <thread_id>`。
- 终态判据 = `/info.status` 离开活词表（`idle`）**加上** `/timing` 行的 `completed_at`；两者缺一不可——
  `idle` 单独**不构成结局**，`/timing` 行的 `latency_ms` 也**绝不能**当作“还在跑”（P7）。
- `active_turn` 不参与任何判定。
- 结局（succeeded / failed / cancelled）**只从持久化消息读**（`/info` 没有 outcome，`thread_messages` 也没有 outcome 列）。
- 轮询间隔 ≤ 60 s。
- 客户端没有任何“必须保持的连接”。

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

## 8. 平台侧缺口（P7 / P8，**已写草稿、暂缓上报**，仓库只留摘要）

> **口径（用户 2026-09-14 定）：以代码为准。后续发现的平台文档/文档缺口一律不上报**，只留内部存档。
> 只报会直接影响"我们能算/能跑"的功能性缺陷 —— P7、P8 属此类；原拟报的 P9（纯文档不一致）**已撑回**，移到 §8.2 存档防踩坑。
> **但上报时机也由用户定：P7/P8 先不报**（用户 2026-09-14：「p7-8 我先不报告，我们待会转接用新流程跑的时候再排查一下吧」）。

| # | 现象（有源码/实测依据） | 影响 | 建议 |
|---|---|---|---|
| P7 | `/timing.active_turn` **不判状态**：跑完但未清理的 run 仍报 `completed=false`、`completed_at=null`、`latency_ms` 现算递增（`chat_service.py:859-874`） | 任何客户端都会把已结束的 run 判成"仍在跑"；我们实测到 53 s 滞后 | `status != running` 时 `active_turn` 归 null，或另给 `last_turn_status` |
| P8 | **run 结局（成功/失败/取消）不落库**，只在内存活 300–360 s；轮询间隔 >5 min 就无法区分成功/失败/force-kill | 慢轮询客户端只能翻 message 里的 `error_type` 反推；同样地 `webhook_config` 解析失败只写 `logger.warning`（`schemas/webhook.py:76-84`），配置静默失效且读接口看不出 | 把终态（含 `termination_reason`）落到 turn 并暴露在 `/timing` 或 `/info`；项目读接口回显一个 `webhook_config_effective` 之类的字段 |

**动作（2026-09-14，⏸ 暂缓上报）**：P7/P8 已作为"第二批"写进 Obsidian
`03-技术与VibeCoding/01-AI与LLM/ToolSmith-平台问题单-ChatAPI与SSE文档缺口.md` 的**草稿区**，
但**没提交给开发**；待 v2 轮询版落地后真跑一次（§9 第 5 步的 `R8`）时顺带排查这两条到底挡不挡我们的路，
确认后再由用户定报不报。仓库台账只留摘要 + 指向。

**排查口径（v2 真跑时顺手看）**
- P7：`/timing.active_turn` 在轮询过程中是否出现"`/info.status` 已终态、而它还在报 `completed=false` + latency 继续涨"——§4 状态机已用 `/info.status` 作唯一终态判据绕过它，这里只是确认绕过是否足够。
- P8：一次有意超时/中断的运行，看轮询能否在 300 s 窗口内捕获终态；错过窗口时能否靠持久化消息里的 `error_type` 把结局反推出来（§5.6）。若都能，P8 就只是"体验问题"，可以不报。

### 8.1 P8 实验设计（E-P8-1/2/3，**2026-09-16 已执行完成 → 见 §12.2 结果**）

**要回答的唯一问题**：错过那 300–360 s 的终态窗口后，我们还能不能把这一次 run 的结局与内容完整拿回来？
能 → P8 降为「体验问题」，不报；不能 → 升级为功能性缺陷上报开发。
**只读 vs 写动作**：E-P8-1 会创建新 thread/turn（写）；E-P8-2/3 纯 GET（读）。

| 实验 | 做法 | 看什么 | 判定 |
|---|---|---|---|
| **E-P8-1** | `run --prompt-file <场景A话术> --timeout 60 --tag p8-cutoff` → 预期出口 **exit 5 `inconclusive`**（客户端主动放弃，run 仍在跑） | `run.json` 是否落下 `turn_id`；接着 `run --resume <thread> --tag p8-resume` 能否在窗口内把终态与产物补齐 | resume 能补齐 = 客户端放弃可恢复；resume 报 `inconclusive` = 只能等下一次窗口 |
| **E-P8-2** | E-P8-1 结束 **>10 min** 后再读同一 thread：`/info`、`/timing`、`/debug/history`、`/messages`、`/artifacts/archive` | `/info.status` 是否已回落到 `未知`；终态能否从持久化消息（`error_type` / 最后一条 assistant 消息 / 产物是否存在）反推 | 能反推 = P8 非阻断；全为空 = 必须上报 |
| **E-P8-3** | 起一个 `run`，在其 `running` 期间 `kill -9` 客户端进程（不是 Ctrl-C），再重新查询 | run 是否继续到 `completed`；产物是否齐全 | 与 T2 同构，但确认 **硬杀** 也不取消（T2 只证明了断 socket） |

**判定表**

| E-P8-1/2 结果 | 结论 | 动作 |
|---|---|---|
| 两臂都能补齐 | 客户端侧可自愈 | P8 留在 §8 表格「已缓解」，**不报** |
| 能补齐但要手工拼 | 体验问题 | 在 `toolsmith-publish run` 里加「终态缺失时从持久化消息反推」的 fallback，**不报** |
| 丢结果 / 完全无法反推 | 功能缺陷 | 按 §8 表格的建议上报开发（终态 + `termination_reason` 落库） |

**成本**：E-P8-1 一轮 ≈ 3.5 min 墙钟（比 R8 的 202 s 略长，因为有意提前放弃后会继续跑完）；E-P8-2 0 成本；
E-P8-3 复用 E-P8-1 的 run ⇒ **合计 1 次新 run**。执行前需确认：该轮会真实消耗 token（约 1.2 M in / 40 k out，
与 R8 同量级）。

### 8.1.1 执行结果（2026-09-16，一轮真跑 + 两次只读复读）

**执行方式与设计不同点**：E-P8-1 与 E-P8-3 合并为同一轮 —— 用 `kill -9` 客户端（比「主动放弃」更狠）代替
`--timeout 60` 提前退出，因此同时回答「客户端消失后 run 是否继续」与「放弃后能否 resume 补齐」。

| 实验 | 实测 | 结论 |
|---|---|---|
| **E-P8-3**（硬杀） | `run --tag p8-kill` 起跑，第 3 次轮询（`40.5 s`，`status=running`）时 `kill -9` 客户端 → 同一 turn 随后正常跑到 `completed`（服务端 11:23:53 → 11:26:44） | **`kill -9` 也不取消 run**（比 R8 的 T2「断 socket」更强）；`run` 作为独立 asyncio 任务成立 |
| **E-P8-1**（resume 补齐） | 杀掉后立即 `run --resume <thread> --tag p8-resume`（只重采集、完全不 POST）→ 在窗口内拿到终态，**16/16 PASS / exit 0**，产物 `report.md` + `citations.json` + `endpoint-bar-1.json` 齐全 | 客户端放弃**可完整自愈** |
| **E-P8-2**（>10 min 后复读，t+11 min） | `/info.status` 回落到 **`未知`**（窗口到期）；但 `/timing` 的**持久化行**出现：`completed_at=2026-09-16T11:26:44.370178`、`completed=true`、`latency_ms=171141`（**冻结**）；`/thread-turns/validate` → `{"exist": true}`；`/messages` 23 条、`/debug/history` **4.26 MB**、`/artifacts/archive` 19 KB 全部可读；R8 的旧 thread 同样如此 | **终态与全量内容都能拿回来** —— 不靠 `/info.status`，靠 `completed_at` + `validate`（两者都落库）。→ 判定表第二行：**体验问题，不报** |

**顺带纠正两件事**

1. **P7 的准确描述**（原描述只说「不判状态」）：“内存中（`cleanup_stale` 之前）`/timing` 返回**临时行**： `completed_at=null`、
   `completed=false`、`latency_ms` 现算递增；窗口过期后换成**持久化行**：三者同时变正确。”
   实测 R9：`latency_ms` 在被读到时依次为 190,000 → 350,200 → 429,651 → 443,488 ms（全程 `completed:false`），
   窗口过期后冻结为 **171,141 ms**（= 真实服务端墙钟，与 `completed_at - started_at` 逐毫秒相等）。
   ⇒ **活窗口内的 `latency_ms` 不止滞后，而且大幅高估**（350 s vs 真实 171 s）；它不是“不判状态”这么轻。
   我们的量具已按 O10 改成「优先 `completed_at - started_at`，无则回退并标注 provisional」，此处结论与 O10 一致。
2. **R8 的真实服务端耗时** = **202.0 s**（持久化行 `latency_ms=202049`），当时记的 “202.4 s polled” 是对的，
   “350.2 s server” 是活计数误读（O10 已修）。

### 8.2 内部的文档坑（**不对外报**，实现时别信文档）

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
4. ⏸（2026-09-14）P7/P8 已写入 Obsidian **草稿区**，**按用户决定暂缓上报**（合到第 5 步 `R8` 真跑时一起排查，见 §8 排查口径）；文档缺口不再上报（P9 降级为 §8.2 内部存档）。
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

---

## 12. 实施状态（2026-09-16，方案 B 落地：S0 修键名 + run v2 一次改完）

> 授权：用户 2026-09-16 明确选 **B**（"你选啥，B？"），并终止了原持有本方案的另一个 session。
> 改动范围**只有** `~/.local/bin/toolsmith-publish`（不入任何仓库）；备份
> `~/.local/state/toolsmith-publish/toolsmith-publish.v1.bak`（65,790 B，改前副本）。

**已落地**

| 项 | 内容 |
|---|---|
| S0 | `status` 假警报根因 = 平台返回 snake_case `current_version_id`、工具读 camelCase `currentVersionId`（5 处）。新增 helper `fam_current_version_id(fam)`（读两种拼法），替换 5 个调用点。复测 `status` **EXIT=0**、`prompt deployed == local: True` |
| 主通道 | `cmd_run` 不再消费 SSE：`POST /api/chat` 只读到 `data-turn-start`（≤ `TAP_MAX_SECONDS` 20 s）即断连，改为轮询 `GET /api/threads/{tid}/info` 的 `status` 判终态（间隔 ≤ `POLL_MAX_INTERVAL` 60 s，默认 20 s） |
| 状态机 | 见 §4；**2026-09-17 按平台 `30306cb` 重建**：活词表 = `preparing/running/cancelling`，`idle` = 无活 run（不是结局）→ 看 `/timing` 行 `completed_at`（**durable，常规路径**）→ `completed`；行存在但无时间戳 → `inconclusive`；从没活过 + 过 grace + validate `exist!=true` → `not_started`（exit 4）。新增 `classify_outcome()` 从持久化消息定结局（`error_type` / `state=interrupted`），`completed` 但失败/取消的 turn **不再谎报成功**。**超时绝不重发 POST**，只允许 `--resume`（见 §12.2 / §12.3） |
| 旧词表 | `completed/failed/cancelled/未知` 已从平台 API 删除（`?status=completed` → **422**）；runner 仍兼容这些值，但只对旧部署有意义 |
| 证据源 | 调用链改由 `tool_chain_from_history()` 从 `/debug/history` 的持久化消息重建；`parse_stream()` **降级为 legacy 离线对账用的 oracle**，运行期不读 SSE |
| 幂等 | `turn_id = uuid4()` **在 POST 之前**写进 `run.json`；body 同时带 `id`/`threadId`/`thread_id`/`turnId`/`turn_id`；重复 POST 收到 **409** 视为幂等提示而非失败 |
| 新断言 | ① 终态必须 `completed`；② 每个 tool-call 要么有 tool-return 要么被 schema 拒（WARN 级，只有 FAIL 计入 exit 3）；③ `retry-prompt`（参数被工具 schema 拒绝）单独记账，不再混入 tool error；④ **2026-09-17 新增：turn outcome 必须 `succeeded`**（产出物路径 **17 项** / 拒绝路径 **11 项**） | 
| 产物 | 每次运行落 `run.json`（thread/turn/repo/model/tag/prompt 长度，**POST 前**）、`prompt.txt`、`stream.tap`（有界 tap）、`info.json`/`timing.json`/`usage.json`、`debug-history.json`、`artifacts.zip` + 解包、`verification.md`（含轮询日志 + 分级断言）、**新增 `transcript.md`** |
| CLI | 新增 `--resume THREAD_ID`、`--turn-id`、`--poll-interval`、`--grace`、`--no-tap`；`--timeout` 语义改为"停止轮询"（默认 2400 s） |
| 退出码 | 0 全过 / 3 断言失败或工具报错 / **4 `not_started`（turn 从未进库）** / **5 `inconclusive`（活着时看不到终态、且 DB 行也没有 `completed_at`）或 `timeout`** |
| 恢复 | 窗口过期后的 `--resume` **不再算 `inconclusive`**：`completed_at` 在就按已结束收尾、跑完全套断言 → **exit 0**（实测 0.2 s vs 旧行为空转到 2400 s）。另：`--resume` 默认写**新目录**，不再就地覆盖原 run 记录（台账 O15） |

**零网络回归闸门（§9 第 3 步）** —— `python3 evals/runner-gate/verify-run-chain.py`
（落仓前的临时副本是 `/tmp/verify_v2.py`；`/tmp` 会被清，以仓库里这份为准），对已录制的 run：

```
20260914-171953-cite-date  attempts=21 returned=21 rejected=0 errors=0 -> OK
20260914-173645-a-2valid   attempts=23 returned=23 rejected=0 errors=0 -> OK
20260914-173947-b-refusal  attempts=8  returned=8  rejected=0 errors=0 -> OK
20260914-174145-b2-refusal attempts=8  returned=8  rejected=0 errors=0 -> OK
20260914-174222-a2-2valid  attempts=41 returned=40 rejected=1 errors=0 -> OK
20260916-104943-v2-poll    SKIP (v2 run: tap 是桩，无 tool 事件可比)  history_attempts=22
20260916-112352-p8-kill    SKIP (同上)                              history_attempts=27
GATE: PASS — v2 history extraction == v1 SSE chain + schema-rejected attempts
```

（v2 的 run 必须 SKIP：它的 `stream.tap` 只有 141 B / 1 个 `data-turn-start`，没有链可比 —— 持久化消息本身就是链。
早先这个闸门因为没处理 `stream.tap` 而报 `FileNotFoundError` / `MISMATCH`，已补上。）

判据（比 §9 第 3 步更严）：把 v2 链里被拒的那次调用剔掉，必须**逐条等于** v1 链；
`extra ids == rejected`；`attempts == 旧调用数 + 拒绝数`；无未返回调用；`errors` 数与 tap 的 `tool-output-error` 一致。

**顺带查出的旧工具缺陷（→ 台账 O9）**：a2 那次真跑里模型**实际发了 41 次工具调用**，其中 1 次把 `execute` 的
`shell_command` 写成 `command`，被工具 schema 拒绝后由框架重新提示、以新 id 重发。SSE 里这次尝试是
`tool-input-error`（`tool-input-start`=41 / `tool-input-available`=40 / `tool-input-error`=1），而 v1 的
`parse_stream()` **不认这个事件类型** → R7 记的是"40 次调用、0 工具报错"，断言"无工具报错"是**假 PASS**。
v2 从持久化消息重建，天然看得到（`raw_ui_messages` 里同 id 的 `state=="output-error"` part）。

**已做的只读退出码实测（§9 第 1 步的只读部分）**

- **当时**：`run --resume <已结束 thread>` → `status=未知` 1 次轮询后由 `/timing` 判 `completed` → **inconclusive / EXIT=5**
  （16 PASS + 1 FAIL，FAIL 就是“没有活着观察到的终态”）。
- **现在（R10 后）**：同一命令 → **`completed` / exit 0**，16/16 PASS，0.2 s 收尾 —— `completed_at` 足以证明终态，
  没必要因为“没活着看到”而扣分（§12.2 / O14）。
- `run --resume <thread> --turn-id 0000…` → `/thread-turns/validate` 返回 `exist=false` → **not_started / EXIT=4**
- 三条都是 GET，**没有产生任何平台写动作**，也没有创建新 turn。

**执行状态 / 剩余项**

1. **R8**（§9 第 5 步）——**已于 2026-09-16 执行完毕**，见 §12.1；
2. P7/P8 顺手排查（§8 排查口径）：**P7 已取得现场证据并修正描述**（见 §12.1、§8.1.1）；**P8 已于 2026-09-16 执行完毕**（§8.1.1，三轮臂全答）→ 判定表第二行：**体验问题，**不报****。剩下要做的只是把「窗口过期后靠 `completed_at` 直接收尾」写进 `run`（见 §12.2 待办 2）；
3. **上游依赖漂移已顺手清掉**：`deps` 报 `pharmcube-query-clinical-result-with-params: schema changed`。
   逐项核对后确认唯一差异是 `selected_fields` 描述里的**序号笔误修正**（`1./1./2.` → `1./2./3.`）；
   18 个参数、73 个 `ALLOWED_FIELD_NAMES`、73 条字段描述**逐字节相同** → **本仓库无需适配**；
   已按流程重生成 `docs/params-tool-schema.md` 镜像 → `deps --accept` → `deps` exit 0。
4. 本次**不改 `skill/` 或 `system-prompts/`** → 不触发 Toolsmith 发布；`status` 复测 in sync（EXIT=0）。

### 12.1 R8：轮询版首次端到端真跑（2026-09-16，已执行）

- 输入与 R3/R7 相同（`解读这几个结果 24_1_30561610 24_1_36342163`，`DeepSeek Flash`），
  thread `b1302c80-f1f6-487d-8244-f495a5848490` / turn `5506e105-9396-421f-a559-0d6e85c7962f`，
  产物 `~/.local/state/toolsmith-runs/20260916-104943-v2-poll/` → **16/16 PASS，exit 0**。
- **§9 T2「断流不取消 run」证实**：`POST` 后 **0.1 s** 就读到 `data-turn-start` 并断开（`stream.tap` 141 B / 1 事件），
  然后 11 次轮询（20 s 间隔）看到 `running` → `completed`（202.4 s）→ **主通道成立，不需要 SSE**。
- **§9 T3「`409` 幂等」证实**：对同一 `(thread_id, turn_id)` 重发 `POST /api/chat` →
  **HTTP 409 `{"detail":"Turn already exists"}`，0.2 s 返回、零执行**（`chat_service.py:1502` `turn_exists(turn_id, thread_id, user_id)`）。
  另：`--resume` 只重采集、**完全不 POST**（比本文档原方案更保守）。
- **§8 P7 现场证据**：`/info.status` 已 `completed`，而 `/timing` 中该 turn 仍 `completed:false`、
  `latency_ms` 从 204,066 ms 涨到 **350,200 ms**（+146 s）→ 「`/timing` 不能判活」从源码推论变成实测。
- **§8 P8 当时未测**：本轮没做「有意超时/中断」实验；仅确认终态在完成的 **5.8 分钟内**仍能从 `/info.status` 读到
  （与源码 300–360 s 窗口一致）——**P8 已于 2026-09-16 补齐，见 §8.1.1**。
- **量具自身又发现两处错（已修，仓库台账记作 O10）**：① `verification` 里 `no tool errors` 打印两遍（遗留的重复 `add()`）；
  ② `wall clock … server (permanent)` 把 `latency_ms` 当永久值 —— 实际上账时它是**现算活计数**（P7），
  会记下一个偏小的服务端耗时。已改为**优先 `completed_at - started_at`**，无 `completed_at` 时回退并明写
  「live `/timing` counter — keeps rising」。

### 12.2 R9 / P8：客户端被 `kill -9` 的那一轮（2026-09-16，已执行）

- thread `1d8f2104-5a3f-46d3-b382-d8626eaec39b` / turn `d67e8c37-1491-4d24-825c-05af7db66c10`，
  输入与 R8 相同（同场景 A），`kill -9` 后 `--resume` 补齐 → **16/16 PASS / exit 0**；
  服务端真实耗时 **171.1 s**、27 次工具调用（27 returned + 0 schema-rejected）、
  turn tokens `in=1,448,663 out=31,718 reasoning=21,648`。
- 事实清单打分（新 run 作为第二份独立样本）：**A 30/30 PASS**（修正打分器句切后）。
- **P8 三个臂全部回答完**（§8.1.1）：硬杀不取消、resume 能补齐、>10 min 后 `completed_at` + `validate` 仍可拿回结局与全部产物。
- **本轮又摸到三个我们自己侧的问题（仓库台账 O12/O13/O15）**：
  1. **O12**：打分器把括号内的 `；` 当句边界，硬生生把 `（…{{ref_2}}；对应 …{{ref_1}}）` 切成两半，
     于是 R9 那份**正确的**报告被成 `A-ATTR-misattribution` 假 FAIL（29/30）。改为「只在括号/方括号深度 0 处切句」；
     同时发现了 harness 自己的一颗雷：变异用的字符串被当**正则**（`| 试验 B {{ref_2}} |` 里的 `|` 变成空分支交替，
     一次替换 **7923** 处、把报告改烂）→ 加 `sub_lit()`（`re.escape`）与「替换次数上限」断言。
  2. **O14**（**更严重**）：`run` 在「`/info.status` 认不出来」时靠 `/thread-turns/validate` 判 `not_started`，
     但代码取的是 `me(c)['id']` —— 而 `/api/auth/me` 返回的是 **`user_id`**，`id` 恒为 `None` ⇒ `uid` 为假 ⇒
     **validate 根本不会被调用** ⇒ `in_db` 永远 `None` ⇒ **任何「状态未知」的 turn 都被无条件报成 `not_started`（exit 4）**。
     实测（只读）：真实的已完成 turn 带正确 `user_id` 查 validate → `{"exist": true}`，缺参 → **HTTP 422**，
     传字串 `None` → **`{"exist": false}`**（假阴性）。修法 = 取 `me(c).get("user_id") or .get("id")`，
     并（建议）在 validate 说 `exist=true` 时先看 `/timing` 的 `completed_at`：有值 → 直接按已结束收尾（走断言），
     不必捛到 `--timeout`（默认 2400 s）才报 `timeout`。
     **2026-09-16 已落地**（用户先点头、改前备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v2.bak`）：
     取 `user_id`，并且**在窗口过期后靠 `completed_at` 直接收尾**（不再空转到 `--timeout`）。
  3. **O15**：`--resume` 不带 `--out` 时会**就地覆盖原 run 目录**（`verification.md` 的 `Checks` 段被抹空）——
     R8 那份记录就是这么丢的。现改为默认写新目录（`<stamp>-resume-<tag>`，并打印原目录位置），
     只有显式 `--out` 才写指定目录（已存在记录时先 warning）；resume 目录也补写自描述的 `run.json` + `prompt.txt`。
- **R10 = runner 修复后的只读复测**（T1–T7，零 POST）：窗口过期 resume → **exit 0 / 16/16 PASS / 0.2 s**；
  真 thread + 不存在 turn → `not_started` exit 4 且 `uid_probe: true`；不存在 thread → exit 4；
  零网络闸门 PASS；`--resume` 不带 `--out` 不动原目录（md5 未变）；
  R8 记录重建件 `~/.local/state/toolsmith-runs/20260916-115047-resume-r8-recollect/` → 16/16 PASS。
  **附带改正**：断言总数是 **16**（此前台账写 17 是数错）。

### 12.3 R11：平台 `30306cb` 之后的状态机重建（2026-09-17，已执行）

上游 `30306cb remove unknown status, add idle`（含 `34215c3` / `af4f601` / `8d10fa0`）对我们是**契约级变更**：

- **P7 从根修掉**：`cleanup_stale(300)` 删除，`run_manager.complete()` / cancel / force-kill 三处立即 `_discard_run()`，
  `active_run_count` 简化为 `len(self._runs)`，并新增 `RunManager.live_status(thread_id)`。
  ⇒ 「活窗口内 `latency_ms` 现算递增且大幅高估」不存在了（run 一结束就换持久化行）。
- **但 `ThreadStatusFilter` / `ThreadInfoResponse.status` 改成了 `Literal["preparing","running","cancelling","idle"]`** ⇒
  `completed/failed/cancelled/未知` **从 API 删除**（prod 实测：`?status=idle`→200、`?status=未知`→400、
  `?status=completed`→**422**），而 `/info` 里**没有任何 outcome 字段**、`thread_messages` 也没有 outcome 列。
- **顺序不变量**（`chat_service.py`）：`pending_turn.finish_timing_now(completed_at=db_now())` 与持久化发生在
  `run_manager.complete()`（line 2019）**之前** ⇒ **`idle` ⇒ DB 行必已有 `completed_at`** ⇒ 终态永远可判。
- **结局的唯一外部通道**：`_normalize_error_text_part()`（`chat_service.py:2988-3022`）把
  `providerMetadata.pydantic_ai.provider_details.error_type` 归一化成 text part 顶层的 `error_type`
  （`stream_error` / `TimeoutError` / 异常类名），取消则 `state="interrupted"`
  （`_persist_partial_run(error_type=type(reported_cancellation).__name__)`，line 1803）。
  官方 durable 结局通道是**项目级 webhook** `run.completed` + `event_status` —— 外部接入方**无法按请求携带**。

runner 因此改了三处（改前备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v3.bak`，88,308 B）：

1. `wait_for_run()`：活词表 `preparing/running/cancelling` 继续轮询；`idle` → durable 分支
   （`/timing` 行 `completed_at` → `completed` + `recovered=timing.completed_at`；行 `completed` 无时间戳 → `inconclusive`）；
   老值 `completed/failed/cancelled` 仍兼容（旧部署）；**从没活过 + 过 grace + validate `exist!=true` → `not_started`**；
   **见过活状态却消失且无 `completed_at`（进程重启）→ 立刻 `inconclusive`**（不再空转到 `--timeout`）；
   `idle` 必须**连续两次**才肯认，避免把一次瞬时读数当真。
2. 新增 `classify_outcome(bundle, turn_id)`：零新增网络请求（吃已抓下来的 `messages.json`）；
   `error_type` 非空 → `failed`；`state=="interrupted"` 或 error_type 含 Cancel → `cancelled`；
   **没有任何持久化消息 → `unknown`（不是 `succeeded`，空产物糊不过去）**；否则 `succeeded`。
   `kind == completed` 而 outcome 是 failed/cancelled 时**把 kind 改掉**，不再谎报成功。
3. 新增断言「turn outcome is succeeded」→ **产出物路径 16 → 17 项、拒绝路径 10 → 11 项**；
   `verification.md` 的终态行改为“read from `timing.completed_at`（durable DB row…）”，并附 outcome 行。

R11 实测（同一 2-esid 场景，新契约下的活路径）：thread `ea0b6213-…` / turn `ee2ff701-…`，
轮询 10 次 `running`×9 → `idle`，**exit 0 / 17/17 PASS**，`177.6 s server / 188.9 s polled`，
`last_live=running durable=timing.completed_at outcome=succeeded`；只读复测 N1–N4（R8/R9 两 thread 复采集 17/17、
两个不存在 turn/thread 的 `not_started` exit 4）、拒绝路径 11/11、零网络闸门 `GATE_RC=0` 均过。

**同时暴露一个清单侧问题（台账 O16/O17，未自行修改）**：R11 产物打场景 A 只有 **25/30**，
5 个 FAIL 里 3 个是「没出定量主图」——而 `references/chart-templates.md:91` 的规则是**定量主图可选**、
要求「同一终点、同一口径（**可明确对齐的时点**）」的纯数值，场景 A 的两条记录是**第 16 周 vs 第 36 周**，
R11 明确写了「不具备绘图条件——本报告不输出图表」并给了理由（R8 同一输入反而画了图）。
⇒ `A-S2/S8/S9` 的期望更像**从 R8 那一份产物倒推**出来的（正是「清单条目必须先于产物撰写」要防的坑），
但改它会重算标量，**所以挂「待用户判定」**，不自行改。
