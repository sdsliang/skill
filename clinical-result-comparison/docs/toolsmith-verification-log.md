# 部署端自验证台账（ToolSmith chat API 直驱）

> **用途**：每次迭代 `skill/` 或 `system-prompts/` 之后，用真跑一次的 chat 来证明
> "线上跑的确实是我们刚改的字节"，并把过程中发现的缺陷按两栏记账：
> **(1) 我们自己能改的**、(2) **平台侧（转开发）**。
>
> 一次验证 = 一条 `R<n>` 记录。**没有新记录就等于这次改动没验证过。**

## 0. 流程（标准动作）

```bash
cd /home/xupeipeioo1/apps/skill/clinical-result-comparison
toolsmith-publish publish                 # 先发布；deps 门禁会自动挡上游漂移
toolsmith-publish status                  # 必须 in sync
printf '解读这几个结果 <esid…>' > ~/.local/state/toolsmith-runs/ask.txt
toolsmith-publish run --prompt-file ~/.local/state/toolsmith-runs/ask.txt --tag <tag>   # 真跑 + 自动断言
```

> **产物落点（2026-09-14 起）**：`run` 默认写到 `~/.local/state/toolsmith-runs/<时间戳>-<tag>/`，
> 临时工作目录也在 `~/.local/state/toolsmith-publish/`；**不再用 `/tmp`**（`/tmp` 会被系统清空，
> 本文件早期记录里的 `/tmp/...` 路径已不可复核，只保留平台侧 thread id 作为回捞入口）。

`run` 会在该目录下落 `stream.sse`、`debug-history.json`、
`artifacts.zip` + 解包目录、`prompt.txt`、`verification.md`（含逐条断言与工具调用链）。

退出码：**0** 全过 / **3** 跑完了但有断言失败或工具报错 / **4** 根本没跑起来。

### 为什么走 API 而不是看分享链接

| 观测 | 分享快照 | API 直驱 |
|---|---|---|
| 并发/程序化跑批 | 手动点 | `run` 一条命令 |
| 线上跑的 prompt 逐字节比对 | 只有特征串，靠 grep 推断 | `/debug/history` 里 `instructions` **逐字节**比对 |
| 线上 skill 正文 + 支持文件清单 | 不可得 | `load_skill` 的 tool-return 里正文 + 18 个文件大小 |
| 整轮 token / 耗时 | 只有 `latency_ms` | `/usage`、`/timing`、`/info`、`/limits` |
| 产物 | 部分 | `/artifacts/archive` 一次拿整个 workspace 的 zip |

## 1. `run` 自动核对的 13 项

部署字节类（这是"我们改的东西真的上线了吗"的硬证据）：

1. deployed system prompt == 本地 `system-prompts/*-v*.md`（+ 打印平台追加尾部字符数）
2. deployed skill 正文 == 本地 `SKILL.md`（去 frontmatter）
3. deployed 支持文件清单（路径 + KB）与本地逐个一致

产物契约类：

4. `output/report.md`、`output/citations.json` 固定路径存在
5. 图表文件名合法（`endpoint-bar-<n>.json` / `endpoint-line-<n>.json` / `evidence-timeline.json`）
6. envelope keys == `[id, iframe_template, option]`；`id == chart-visualization-json`；文件名里的 `bar/line` 与 `option.type` 一致；`iframe_template` 非空（并打印发布 ID）
7. 正文 `::visualization[...]` 标签数 == 图表文件数
8. 正文无残留 `{{…}}` 占位符（`{{ref_n}}` 除外）
9. 无嵌套实体锚点 `](entity:…](entity:`
10. 每个 `{{ref_n}}` 都有 citations 条目（反向也查未引用）
11. **citations 每个键恰为 `link` / `paper_release_time_str` / `title` 三字符串，且 `paper_release_time_str` 为 `YYYY-MM-DD` 或空串**（2026-09-14 新增：把「日期只取日期部分」变成机器可判定的契约）
12. 最后一个工具调用是 `present_artifact`
13. 无 `tool-output-error`

## 2. 运行记录

### R1 — 2026-09-11，14 个 esid（手工脚本，先于 `run`）

- thread `7aa87b77-62f7-4fff-99d0-dc0f5c5b2ac9`，模型 `DeepSeek Flash`
- 墙钟 **299.2 s**；**50** 次工具调用；`reasoning_tokens` **31,782**（SSE reasoning 文本 92,605 字符）；
  input 4,351,105（cached 4,270,464）/ output 58,808
- 产物：`report.md` 33,166 B、`citations.json` 3,641 B、`endpoint-bar-1.json` 2,699 B、
  `endpoint-line-1.json` 2,110 B；`evidence-timeline` **正确地未生成**（11 个不同试验）
- 图表 envelope 校验通过（部署端 CLI 自证），`iframe_template` 发布 ID `20260911-134013`
- 契约抽查：实体锚点 160（trial 76 / drug 75 / company 9），嵌套锚点 0，标记 220 个但唯一 14
- 1 处 fail-loud：模型发明 `clinical_result.line_count` → `INVALID_INPUT` → 下一次调用自动改对

### R2 — 2026-09-13，1 个 esid（`run` 子命令首次冒烟）

- thread `eaace30f-0e60-45ab-8384-ae7b10983d27`，模型 `DeepSeek Flash`，prompt 21 字符
- 墙钟 **173 s**（客户端 172.9 / 服务端 173.1）；**21** 次工具调用；`reasoning_tokens` **26,153**；
  input 970,370（cached 931,584）/ output 34,024
- 产物：`report.md` 13,873 B、`citations.json` 333 B、`endpoint-bar-1.json` 1,430 B（同试验两治疗组并列）
- **12/12 断言全过，0 工具报错**；deployed sys 40,308 字符 + 平台尾部 18,543 字符（sha `18e3ee0b85bb`），
  skill 正文 18,042 字符与本地逐字节相同，18 个支持文件 0 处大小不一致
- 调用链：`load_skill` → params 工具 → 6×`execute` → 9×`read_file` → `write_file` + 2×`edit_file` → `present_artifact`

### R3 — 2026-09-14，2 个 esid（引用时间裁成日期 + O2/O3 落地后首次）

- **本批改了什么（仓库 v0.15 原地改）**：
  - `paper_release_time_str` 只取 `YYYY-MM-DD`（不擅自再格式化 / 不换时区 / 不编造；空值保持 `""`，格式不匹配则原样透传）——只影响 `citations.json`，正文与时间轴日期不动；
  - selected_fields 字段名以 params 工具 schema 为准、**禁止发明**（O3）；
  - digest 单文件要能一次读完（O2）；
  - `run` 新增第 11 项断言 + `run` 输出目录改持久化（O6）。
- **发布**：prompt `v1.6`（42,301 B / sha `ee9dbe9d3a20`）、skill `v1.0.7`（`skill_id=ad75ec2c44334f389a0394895a47b765`）；`status` = **in sync**。
  > 发布时被 deps 门禁挡过一次（`chart-visualization-json 1.0.10 → 1.0.12`，**线上零改动**，exit 4）——设计内行为；核对差异（仅新发布 ID `20260914-145519` + `chart-types.md` 加 1 行「堆叠 + 负值」；协议零变更、我们无适配）后 `deps --accept` 再发。
- thread `61e5d232-519f-40ab-826d-6e2ceb1b423f`，模型 `DeepSeek Flash`，prompt 36 字符
- 墙钟 **129.0 s**（客户端 128.1）；**21** 次工具调用；`reasoning_tokens` **16,082**；input 703,871（cached 662,272）/ output 23,003
- **13/13 断言全过，0 工具报错**；deployed sys 41,490 字符 + 平台尾部 18,543 字符（sha `e6d9c5fd4188`），skill 正文 18,755 字符与本地逐字节相同，18 个支持文件 0 处不一致
- 产物：`output/report.md`、`output/citations.json`；0 张图（两条结果分属不同试验、无同试验时间轴，也没到定量主图所需数据）
- **本批核心断言的硬证据**（这才是这条记录存在的理由）：
  ```json
  {"ref_1": {"title": "Persistent arterial wall inflammation in patients with elevated lipoprotein(a) …",
             "link": "https://pubmed.ncbi.nlm.nih.gov/30561610",
             "paper_release_time_str": "2018-12-19"},          // 平台原值是 "2018-12-19 00:00:00"
   "ref_2": {"title": "", "link": "", "paper_release_time_str": ""}}
  ```
  即：`HH:MM:SS` 已被裁掉，且截断是**规则驱动**而非偶然（`ref_2` 无元数据就给空串、不编日期）；断言第 11 项用 `re.fullmatch(r"\d{4}-\d{2}-\d{2}")` 机器校验为 `2 refs`
- 工具调用：params×8 / `execute`×8 / `read_file`×3 / `load_skill`×1 / `present_artifact`×1；实体锚点 13 个、嵌套 0
- **负面发现（→ O7）**：prompt 里我混了一个**不存在的 esid**（`24_1_45608045`），模型对同一输入换写法重试 8 次仍无果，最后给了一个**全空 `ref_2`**；空条目能过断言，说明当前断言集不覆盖「引用是否真的有内容」（已记入 O7 候选改法）

## 3. 我们自己能改的

| # | 现象（证据） | 改法 | 状态 |
|---|---|---|---|
| O1 | `deps` 基线漏掉 `read_file`：R1/R2 实际调用 21+9 次，但基线内置工具 10 个里没有它 —— `collect_deps` 只做**文档文本匹配**，而我们的 sys/skill 从不提 `read_file` | `toolsmith-publish` 的内置工具指纹改为取**项目实际启用的工具集**（`GET /api/agent/info?project_id=…` → `tools`，16 个），不再靠文本命中；顺带修了漂移输出把 `NEW builtin` 打成 `NEW buil` 的截断 | **已落地**（基线 16 个，`deps` 复跑 exit 0） |
| O2 | digest 翻页：R1 里 **12/50** 次调用在按 offset 读同一个 105 KB / 510 行 `digest.txt`（offset 60→499，limit 30–60） | sys `Step discipline` #1 收尾加一句：**每个 digest 文件要能一次读完**（目标 ≤ ~300 行 / 几十 KB）；超了就拆成「每记录一文件」或「index + 每记录文件」，**不要对单个大 digest 反复 offset 读** | **已落地**（sys v0.15，2026-09-14） |
| O3 | 发明字段：R1 出现 `clinical_result.line_count` → `INVALID_INPUT`（原文见平台 P3），靠重试自愈 | 字段名的**运行期权威 = params 工具自身的 `selected_fields` 参数描述**；逐字复制，**禁止发明**；概念确无字段时取**最接近的真实字段**（组/臂数 → `clinical_result.group_count`，线数 → `clinical_result.therapy_line_cn`/`_en`）或**留空并记「未报告」**。`docs/params-tool-schema.md` 只是维护者镜像（不在部署端包内），明确禁止规划运行期去读它。落到 `SKILL.md`、`references/input-contract.md`、`references/entity-inline-reference.md`、sys | **已落地**（2026-09-14） |
| O4 | 正文句子级返工：R1 的 19 次 `execute` 里 8 次是 `s.replace()` **就地改写 `build_report.py` 里的模板字面量**，另有 3 次 `edit_file`；都是内容打磨（不是规则返工） | 暂不改规则。若要压：把「正文与渲染分离」（正文放 md/data，脚本只做 token 替换 + 断言）写成硬规则 | **待样本**（再攒 3–5 次运行） |
| O5 | 小样本不便宜：1 个 esid 也要 21 次调用 / 173 s / 26k reasoning tokens（14 个 esid 是 50 次 / 299 s / 32k）；成本由"读 skill + 套模板"主导，不随结果数线性 | 暂不改。若体感贵，可考虑给"单结果解读"一条更轻的模板路径 | **待样本** |
| O6 | 台账里写的本地产物路径（`/tmp/toolsmith-runs/...`）全部失效：`/tmp` 被系统清空，早期的 `R1/R2` 产物离线后无法复核（只剩平台侧 thread id 能回捞） | `toolsmith-publish` 的 `WORK` / `RUNS` 改到 `~/.local/state/toolsmith-publish` 与 `~/.local/state/toolsmith-runs`（不用 `/tmp`）；`run --out` 仍可覆盖 | **已落地**（2026-09-14，R3 起生效） |
| O7 | 无效 esid 导致空转：R3 里我把 `24_1_45608045`（库中无数据）和有效 esid 一起给，模型对**同一个输入换了 8 种写法**（`extra_esids:["24_1_45608045"]` → `["45608045"]` → 改 `trial_id:"NCT02729025"` …）共 **8 次** params 调用，最后仍产出 `ref_2` 为**全空**（`title`/`link`/`paper_release_time_str` 均 `""`），而 13 项断言全过（断言只管「有对应条目」，不管条目是否为空） | 候选改法（**先攒样本再改**）：① 同一 esid 连续查不到就停手，**不许换写法反复重试**；② 元数据全空的结果**不分配 `{{ref_n}}`**，正文写「未找到/无数据」而不是给一个空引用 | **待样本**（目前 1 例；R3 的 prompt 里我故意混了一个不存在的 esid） |

## 4. 平台侧（转开发）

完整、可直接转发的版本见 Obsidian：
`03-技术与VibeCoding/01-AI与LLM/ToolSmith-平台问题单-ChatAPI与SSE文档缺口.md`

摘要（均为文档/可观测性问题，非阻断性 bug）：

- **P1** Chat API 缺最小可用示例，字段命名不一致（`threadId` 驼峰 vs `project_id` 下划线；顶层 `id` 必填；
  `messages` 只发最后一条；query 要重复 `thread_id` + `model`）；`/api/projects` 用 `projects` 键、
  其他列表端点用 `items`。
- **P2** SSE 事件字典缺失：`data-turn-start`、`data-sql`、`data-table` 未文档化（一次 turn 共 16 种事件）。
- **P3** `INVALID_INPUT` 回吐 `ALLOWED_FIELD_NAMES` 被**硬截断**（180 字符，末尾停在 `"clinical_r`），
  既无省略号也无"怎么拿全量"的指引 → 模型只能重试猜。
- **P4** `/api/threads/{id}/info` 的 `usage` 只统计**最后一步**（output 35），整轮要看 `turn_usage`（output 34,024）。
- **P5** `/artifacts/archive`（一次拿整 zip）只出现在 openapi，没进文档；
  `/artifacts/content` 的 `content` 外层包装也易踩空。
- **P6** `POST /api/tools/debug` 的必填字段与 schema 不一致：源码里 `ToolDebugRequest.mcp_server_id: str | None = None`（OpenAPI 呈现为 `anyOf[string,null]`、不在 `required`），但 `origin == "MCP"` 时不传就被 `model_validator` 拦下，422 原文
  `"mcp_server_id is required for MCP tool debug"` —— 调用方只能从报错反推。

### 2026-09-14 对照 TS `master` @ `50f048b`（拉最新代码后再核）

拉下上游仓库最新代码（33 个新提交）逐条对照，这几项**平台已自行解决或部分解决**，不再算问题：

- **P1 大部分已解**：`chat_routes.py` + `schemas/chat.py` 现在**顶层字段同时接受 snake_case 与 camelCase**（`projectId`/`project_id`、`turn_id`/`turnId`），且 `chat-api.mdx` 已写明“文档示例用前端约定”。剩下的只是会话层小不一致（`/api/projects` 用 `projects` 键、其他列表端点用 `items`）。
- **P5 部分已解**：新增 `frontend/content/docs/integrate/token-api.mdx`（146 行），把 chat / 提示词 / 技能 / 项目的令牌接口全列了；`chat-api.mdx` 也补上了 `/artifacts`、`/artifacts/content`、`/artifacts/file-download` 与 share 侧对应端点。**`/artifacts/archive` 仍只在 openapi**。
- **P2 仍存在**：`streaming.mdx` 只写了“文本增量 / 工具状态 / data-turn-start / 完成或错误”，`data-sql` / `data-table` 仍无字典。
- **P3 / P4 / P6 仍在**（P6 已在上方补源码级证据：`tool_routes.py:41/47`）。
- 顺带记下与本项目相关的新事实：① DeepSeek 系新增 `low` 档（`supported_efforts = [low, high, max]`，`838ba7f`）；② 新增前端 spec `spec/chart-json-ai-renderer.md`，正式描述了我们的 envelope（按 `id == "chart-visualization-json"` + `iframe_template` + `option` 判定渲染）且明确**旧构建的模板 URL 会被删除**→ “`iframe_template` 只能运行期现读、禁止硬编码”这条规则再次被印证；③ PAT 与细粒度权限（`7ad5782` / `023704d`）已进正式文档 `authentication.mdx`，其中“写接口无幂等键、先查再写”与我们 `toolsmith-publish` 的行为一致。

- **更正（非平台问题，仍成立）**：此前记的“`/api/threads`、`/api/chat/shares` 返回 Unauthorized”是**我漏带 token**。
  实测无 token / 坏 token 均 401，带自己 PAT 返回 200 且只含自己的数据；单条 `GET /api/chat/share/{id}` 匿名可读，
  符合 share 语义。
