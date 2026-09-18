# 部署端自验证台账（ToolSmith chat API 直驱）

> **用途**：每次迭代 `skill/` 或 `system-prompts/` 之后，用真跑一次的 chat 来证明
> "线上跑的确实是我们刚改的字节"，并把过程中发现的缺陷按两栏记账：
> **(1) 我们自己能改的**、(2) **平台侧（转开发）**。
>
> 一次验证 = 一条 `R<n>` 记录。**没有新记录就等于这次改动没验证过。**

## 0. 流程（标准动作）

```bash
cd /home/xupeipeioo1/apps/skill/clinical-result-comparison
python3 /home/xupeipeioo1/tmp/pack15b.py   # 重打 dist（幂等：只改文档时 SHA 不变）
toolsmith-publish publish                  # 默认原地更新当前版本；deps 门禁会自动挡上游漂移
toolsmith-publish status                   # 必须 in sync（版本号标签不变）
printf '解读这几个结果 <esid…>' > ~/.local/state/toolsmith-runs/ask.txt
toolsmith-publish run --prompt-file ~/.local/state/toolsmith-runs/ask.txt --tag <tag>   # 真跑 + 自动断言
# 「本应拒绝产出」的场景：
toolsmith-publish run --prompt-file <1 有效 + 1 无效 esid> --tag <tag> --expect refusal
```

> **发布语义（2026-09-14 用户拍板）**：`publish` **默认原地更新当前版本**（prompt `ifadd:false` 改写 `is_current` 行；
> skill `POST /api/skills/update_skill_file` 传全量 bundle zip、保 `skill_id` 与版本号、内部 `commit_id` 递增），
> **不再自动涨版本号**；要追加新版用 `--new-version`。发错后原地重发即可（内容被覆盖）。

> **产物落点（2026-09-14 起）**：`run` 默认写到 `~/.local/state/toolsmith-runs/<时间戳>-<tag>/`，
> 临时工作目录也在 `~/.local/state/toolsmith-publish/`；**不再用 `/tmp`**（`/tmp` 会被系统清空，
> 本文件早期记录里的 `/tmp/...` 路径已不可复核，只保留平台侧 thread id 作为回捞入口）。

`run` 会在该目录下落 `run.json`（thread/turn/repo/model/tag，**POST 之前**就写，供 `--resume` 定位）、`prompt.txt`、
`stream.tap`（有界 tap，仅存档、**不作为任何断言的输入**）、`debug-history.json`、`info.json` / `timing.json` / `usage.json`、
`artifacts.zip` + 解包目录、`verification.md`（含轮询日志与分级断言）、`transcript.md`（人读的对话回放）。

退出码：**0** 全过 / **3** 跑完了但有断言失败（或非 schema 拒参的工具报错）/ **4** `not_started`（turn 从未进库，POST 没落地）/ **5** `inconclusive`（错过平台 300–360 s 的终态窗口）或 `timeout`。

> **2026-09-16 起 `run` 不再消费 SSE**：`POST /api/chat` 只读到 `data-turn-start` 就断连，之后按 ≤60 s 轮询
> `GET /api/threads/{tid}/info` 的 `status` 判终态（平台把 run 当独立任务跑，客户端断连只摘订阅者、**不 cancel**）。
> 证据一律从持久化消息（`/debug/history`、`/messages`）与产物重建；`stream.sse` 不再产生。超时**绝不重发 POST**，只能 `--resume`。

### 为什么走 API 而不是看分享链接

| 观测 | 分享快照 | API 直驱 |
|---|---|---|
| 并发/程序化跑批 | 手动点 | `run` 一条命令 |
| 线上跑的 prompt 逐字节比对 | 只有特征串，靠 grep 推断 | `/debug/history` 里 `instructions` **逐字节**比对 |
| 线上 skill 正文 + 支持文件清单 | 不可得 | `load_skill` 的 tool-return 里正文 + 18 个文件大小 |
| 整轮 token / 耗时 | 只有 `latency_ms` | `/usage`、`/timing`、`/info`、`/limits` |
| 产物 | 部分 | `/artifacts/archive` 一次拿整个 workspace 的 zip |

## 1. `run` 自动核对的断言（分级：PASS / FAIL / WARN）

> **2026-09-16 起分级**：只有 **FAIL** 影响退出码（exit 3）；**WARN** 只打印。另外新增两项：
> ① **终态必须 `completed`**（轮询判定的结局，`inconclusive`/`timeout` 另走 exit 5）；
> ② **每个 tool-call 要么有 tool-return、要么被工具 schema 拒**（后者单列成“schema-rejected”，是 WARN/INFO 而非 tool error）。
>
> **2026-09-17 起再加一项（产出物路径 16 → 17 项 / 拒绝路径 10 → 11 项）**：
> ① **turn 的结局必须是 `succeeded`** —— 平台 `30306cb` 把 `/info.status` 的终态值整个删掉（只剩
> `preparing|running|cancelling|idle`），结局只能从**持久化消息**里读（见 §4 的 2026-09-17 段）。
> 没有这条断言时，一个 **失败/被取消**的 turn 会被旧 runner 报成 `completed`（`/info` 说“没活的 run”，
> 不带任何结局）→ 只有 `completed` 一条断言的话，**空手而归的失败轮次能全过**。
> ② 空产物护栏：一个 turn 若**没有任何持久化消息**，分类结果是 `unknown`（不是 `succeeded`）→ 断言 FAIL。

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
11. **citations 每个键恰为 `link` / `paper_release_time_str` / `title` 三字符串，`paper_release_time_str` 为 `YYYY-MM-DD` 或空串，且每个条目的 `title` 非空**（2026-09-14：先把「日期只取日期部分」变成机器可判定的契约，再把「引用不许是空壳」也变成可判定的——原第 11 项只查键集与日期格式，`{"ref_2":{"title":"","link":"","paper_release_time_str":""}}` 这种**空壳引用能全过**，是 R3 的真缺陷）
12. 最后一个工具调用是 `present_artifact`
13. 无 `tool-output-error`（**仅**指非 schema 拒参者；被 `retry-prompt` 命中的一次尝试另有专项行）

### 附：`run --expect refusal` 模式（2026-09-14 新增，4 项）

用于验证「本应拒绝产出」的场景（选中的结果不足 2 条可检索记录）：

1. deployed system prompt / skill 正文 / 支持文件清单三项同上（部署字节硬证据）
2. `output/report.md` 与 `output/citations.json` **均不存在**（`output/` 下什么都没有）
3. 确实调用过 params 工具（不是没查就拒）
4. 回复非空、不含 `{{ref_`，并说明了取不到的结果

> `--expect refusal` 与默认 `artifacts` 互斥；退出码语义不变（0 全过 / 3 有断言失败 / 4 没跑起来）。

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

### R4/R5/R6/R7 — 2026-09-14，**R3 真缺陷的根因修正 + 原地（in-place）发布**

> 已 commit **`4cea33d`** 并 push 到 `origin/v0.15-remove-html`（11 文件 / +142 / -30）。

> 这条不是「又跑了一遍」，而是 R3 暴露的**真缺陷**的闭环：空壳引用不是平台 bug，**是我们自己的 sys 规则逼出来的**。

**根因（R3 的 `ref_2` 为何全空）**：dump 部署端 `GET /api/agent/info` 可以看到部署 prompt 的尾部，里面有一句我们自己的规则：
`every selected esid has a corresponding pulled record and exactly one citation JSON entry, including duplicate or unusable items`（＝ sys:196 的部署副本）。它与另两条叠加，等于**三条我方规则联合要求给「压根没回来的 esid」也写一条引用**：

1. sys:7 / `SKILL.md:33`：`returned records map one-to-one to the supplied esids in the same order → {{ref_1}}, {{ref_2}}, …`
2. sys:196：每个 selected esid 都必须有 pulled record 与恰好一条 citation entry（含 unusable）
3. `citation-and-ref.md`：keys 从 `ref_1` 起连续、按输入顺序

一个「按输入顺序一一对应」+「每条都必须有条目」的契约，遇到空结果就只能写出空壳——**模型当时的行为是对的，规则是错的**。

**本批落地（仓库 v0.15 原地改，不升版本号）**：

- `references/input-contract.md`：新增 **### Unretrievable selected items** —— 一次批量拉取 + **至多一次**确认（不许换拼写/猜 id/逐 esid 循环）；未返回的 esid **不分配 `{{ref_n}}`、不写 citation key**，keys 在「实际返回的记录」上保持连续；**禁止空 `title` 条目**（空 title = 「写了一条根本没回来的引用」的指纹）；证据范围里点名说明；**可用记录 < 2 条 → 不写 report/citations，改在 chat 说明并请用户复核选择**。同时把 Pull protocol 第 4/5 条第 1 条、`Rationale`、`Citation correctness` 的相关句改为「over the records that returned」。
- `references/citation-and-ref.md`：marker 分配改为「对**实际返回**的记录按选择顺序」；citation 契约加「`title` 非空」；连续性与校验段同步。
- `SKILL.md`：把「一一对应」句改为按 `extra_esid` 映射 + markers 落在「回来的记录」上；「至少两条可用记录」扩为「**< 2 条就拒绝产出**」。
- `references/{input-and-extraction,file-delivery}.md`：marker 分配、citation 文件键位描述同步（只给**取回**的来源编号）。
- `templates/unified-evidence-report.md`：证据范围声明加「如有选中结果未取回，在此点名，且不占引用编号」。
- sys v0.15（4+1 处）：line 7 一一对应 → 「按 `extra_esid` 映射 + markers over the records that came back」；新增两条 bullet（**Unretrievable selection — an empty result is not a source** / **Fewer than two usable records → refuse, do not deliver**）；line 196 那条校验项改为「每条引用都对应真正返回且有非空 title 的记录，且正文每个 `{{ref_n}}` 恰有一个 key」；citation JSON 段加「只有取回的记录才出现，空 `title` 绝不可接受」；子代理 fail-loud 那条加「子代理报的 empty 不算证据，主线程要自己在那一次确认调用里复核」。
- `toolsmith-publish`：`check_run` 第 11 项加 **`title` 非空**断言；新增 **`run --expect refusal`** 模式（4 项断言，见 §1 附）。
- **发布方式改变（用户拍板）**：`publish` **默认原地更新当前版本**（prompt `ifadd:false` 更新 `is_current` 行；skill `POST /api/skills/update_skill_file` 传全量 bundle zip、保 `skill_id`/version、内部 `commit_id` 递增），`--new-version` 才追加新版本；不再有 `--overwrite` 别名。**本轮就是原地发**：prompt 仍 `v1.6`、skill 仍 `v1.0.7`（`skill_id=ad75ec2c44334f389a0394895a47b765`）。

**R4 — 场景 A（2 个有效 esid）**：thread `6ad0dcee-9f53-42a2-b907-48f1b18b418c`（产物 `~/.local/state/toolsmith-runs/20260914-173645-a-2valid/`）

- prompt `解读这几个结果 24_1_30561610 24_1_36342163`，模型 `DeepSeek Flash`
- 墙钟 **175.3 s**；**23** 次调用（params×2）；`in=1,135,953 cached=1,073,408 out=34,847 reasoning=24,839`
- **13/13 断言全过、0 工具报错**；deployed sys sha `b3050f32668e`（43,616 ch + 平台尾 18,543 ch）；产物 `report.md` + `citations.json` + `endpoint-bar-1.json`（envelope 发布 ID `20260914-145519`）；markers=2 keys=2 missing/unused 均空；**params 只调了 2 次**（1 批量 + 1 次「同试验补 study_results 字段」，不是重试）

**R5 — 场景 B（1 有效 + 1 无效，本应拒绝产出）**：thread `49653f36-32d0-4a91-86f4-58fb1a4357f9`

- prompt 与 R3 逐字相同（`解读这几个结果 24_1_30561610 24_1_45608045`）
- 墙钟 **36.8 s**（R3 同输入是 **129 s**）；**8** 次调用；`in=259,225 out=4,004 reasoning=2,295`
- **refusal 4 项全过**：`output/` 下**什么都没有**（不再产出空壳引用，也不再造假报告）
- 回复原文（节选）：`本次无法生成联合解读 … **所选结果中有一条取不到记录** - 24_1_45608045：按该结果 ID 取数两次（先与另一条一起批量取，再单独取），均未返回任何记录。按约定，未取到的记录不进入编号与引用清单，我也不会为它编造任何内容。 - 24_1_30561610：正常返回…`
- **新发现（→ O8）**：params 调用 3 次，第 2、3 次是**参数完全相同的确认调用**（同一个 `24_1_45608045` 再查一遍）——规则写的是「至多一次确认」，实际做了两次

**R6 — 场景 B 复跑（O8 措辞收紧后）**：thread `73b427f3-3d19-4819-8228-4460e65a9d2b`

- 墙钟 **33.5 s**；**8** 次调用；params **恰好 2 次**（1 批量 + 1 确认）——收紧生效
- **refusal 4 项全过、0 工具报错**；deployed sys sha `1998f37da67d`

**R7 — 场景 A 复跑（最终部署字节）**：thread `a0420a2f-c1a4-4443-a749-0547eeb43941`

- 墙钟 **209.5 s**；**40** 次调用（params×2）；`in=2,776,723 out=35,662 reasoning=22,256`
- **13/13 断言全过、0 工具报错**；deployed sys sha **`1998f37da67d`**（43,701 ch + 平台尾 18,543 ch）；markers=2 keys=2 missing/unused 均空（与 R6 同一部署字节）
- 产物硬证据（**这才是「不空」的证明**）：
  ```json
  {"ref_1": {"title": "Persistent arterial wall inflammation in patients with elevated lipoprotein(a) despite strong low-density lipoprotein cholesterol reduction by proprotein convertase subtilisin/kexin type 9 antibody treatment.", "link": "https://pubmed.ncbi.nlm.nih.gov/30561610", "paper_release_time_str": "2018-12-19"},
   "ref_2": {"title": "Small Interfering RNA to Reduce Lipoprotein(a) in Cardiovascular Disease.", "link": "https://pubmed.ncbi.nlm.nih.gov/36342163", "paper_release_time_str": "2022-11-08"}}
  ```
  两张图/报告都存在、两个条目都有真实标题与日期、正文里 `{{ref_1}}{{ref_2}}` 都对得上。

> **R3 的分享链接（`…/chat/share/4a2e4685-…`）无法修**：share 是那一轮 turn 的静态快照，含的就是旧字节的旧输出。修复只能体现为**新跑的 turn**（R6/R7）。

### 验证工具自身升级（run v2 轮询版，2026-09-16）

> 这不是 skill 迭代，而是**量具本身的升级**（`~/.local/bin/toolsmith-publish`，不入仓库）：SSE 消费 → 轮询
> `GET /api/threads/{tid}/info` 的 `status`。设计/源码依据见 `docs/toolsmith-run-v2-polling-plan.md`（§12 = 实施状态）。
> **本批不动 `skill/` 与 `system-prompts/`，因此没有新的 `R<n>`**；验收靠零网络重放 + 只读退出码实测。

- **备份**：`~/.local/state/toolsmith-publish/toolsmith-publish.v1.bak`（65,790 B，改前副本）。
- **S0（`status` 假警报）**：平台返回 snake_case `current_version_id`、工具读 camelCase `currentVersionId`（5 处）→ 新增 helper `fam_current_version_id()`。复测 `status` **EXIT=0**、`prompt deployed == local: True`。
- **零网络重放闸门**（`evals/runner-gate/verify-run-chain.py`，5 个已录制 run 的 `stream.sse` vs `debug-history.json`）：
  `171953-cite-date 21/21`、`173645-a-2valid 23/23`、`173947-b-refusal 8/8`、`174145-b2-refusal 8/8`、`174222-a2-2valid 41=40+1 拒`。
  判据：剔除被拒调用后**逐条等于** v1 链、无未返回调用、`errors` 数与 tap 一致 → **GATE: PASS**。
- **只读退出码实测**（全 GET，无写动作）：`--resume <已结束 thread>` → **当时**判定 `inconclusive` **exit 5**；
  `--turn-id <不存在>` → `not_started` **exit 4**。**两者的正确性后来都被推翻了一半**，见 R10 / O14：
  已结束的 turn 应靠 `completed_at` 直接收尾（exit 0 + 跑完断言）；而当时的 `not_started` 是**空判**（probe 没被调用过）。
- **上游漂移顺手清掉**：`deps` 报 `pharmcube-query-clinical-result-with-params: schema changed`，逐项核对为 `selected_fields` 描述里的**序号笔误修正**（`1./1./2.` → `1./2./3.`），18 参数 / 73 字段名 / 73 字段描述**逐字节相同** → **本仓无需适配** → 重生成 `docs/params-tool-schema.md` 镜像 → `deps --accept` → `deps` exit 0。
- **R8 已完成**（轮询版首次端到端真跑，见下节）：`16/16 PASS`、exit 0；**T2/T3 均已证实**。
  （断言总数是 **16**，先前台账写 17 是数错了 —— 已全仓改正；见 O15 的附注。）

### R8 — 2026-09-16，2 个 esid（**轮询版 `run` 的首次端到端真跑**，输入与 R3/R7 相同）

- thread `b1302c80-f1f6-487d-8244-f495a5848490`，turn `5506e105-9396-421f-a559-0d6e85c7962f`，产物 `~/.local/state/toolsmith-runs/20260916-104943-v2-poll/`，`DeepSeek Flash`。
- **16/16 PASS，exit 0**。`POST` 后 **0.1 s 就断流**（`stream.tap` 141 B / 1 个事件），其后 **11 次轮询 / 20 s 间隔**看到 `running` → `completed`（202.0 s，真值；当时打印的 202.4 s 是活计数）→ **T2 证实：客户端断流不取消 run**。
- 22 attempts = 22 returned + 0 schema-rejected（`execute×10 / read_file×6 / write_file×2 / load_skill×1 / params×1 / edit_file×1 / present_artifact×1`）；`in=1,253,918 out=39,699 reasoning=24,979 cached=1,212,032`；context `sys=20,701 mcp=5,919 tools=50,127 skill=17,201 conv=3,502`。
- **产物**：`output/report.md` + `output/citations.json` + `visualizations/endpoint-bar-1.json`。**无 timeline** —— 两个 esid 属不同试验，规则「同试验 + ≥2 个证据状态才画时间轴」被正确执行。`citations.json` 两条均有真实标题与日期（`2018-12-19` / `2022-11-08`，与 R7 **逐字节相同**）。
- **部署字节**：deployed sys = 本地 43,701 ch + 平台尾 18,543 ch（deck sha `1a9ff3d209ec`）、skill 正文 19,580 ch、18 个支持文件全等。
- **T3（`409` 幂等）**：重发同一 `(thread_id, turn_id)` 的 `POST /api/chat` → **HTTP 409 `{"detail":"Turn already exists"}`，0.2 s 返回、零执行**（源码 `chat_service.py:1502` `turn_exists(turn_id, thread_id, user_id)`）→ 「超时后重发会double-execute」的担心可以排除。另：`--resume` 复测只**重采集、完全不 POST**（比方案更保守），0.2 s 内判定 `completed`。
- **P7 现场证据**：同一 turn，`/info.status` 已 `completed`，而 `/timing` 里该 turn 仍 `completed:false`、`latency_ms` 从 204 s 一路涨到 **350 s**（+146 s）→ `/timing` 的 latency 是**现算的活计数**。**连带查出一处我们自己的错标**（记为 O10）。
- **P8 未测（当时）**：本轮没做「有意超时/中断」实验；仅确认终态在关掉的 **5.8 分钟内**都能从 `/info.status` 读到 `completed`（与源码推出的 300–360 s 窗口一致）。→ **已于 2026-09-16 补齐，见 R9 / P8**。
- **后续更正（R9 复读时发现）**：本行里的 “350 s” 是**活计数误读** —— `/timing` 在内存期为**临时行**，
  `latency_ms` 现算且**大幅高估**；R9 完成后回读本 thread，`latency_ms` **冻结在 202,049 ms** = 真实服务端耗时
  **16/16 PASS，exit 0**（与 `completed_at - started_at` 逐毫秒相等）。O10 的量具修复已按这个口径落地。
- **本 run 目录的 `verification.md` 后来被 O15 那段 bug 覆盖过**（早先一次 `--resume` 未带 `--out` 时就地重采集，
  `Checks` 段被抹成空，只留下“1 poll / 0.2 s”）。**权威重建件**：修 O15/O14 后用
  `run --resume b1302c80-… --tag r8-recollect` 重新采集到 `~/.local/state/toolsmith-runs/20260916-115047-resume-r8-recollect/`
  → **16/16 PASS / 0 FAIL**，终态行明写 `recovered from timing.completed_at`。

### R9 / P8 — 2026-09-16，2 个 esid（客户端被 `kill -9` 的一轮；P8 实验的写动作那一半）

- 源码与目标：回答 `docs/toolsmith-run-v2-polling-plan.md` §8 的 P8（错过 300–360 s 终态窗口后还能不能拿回结局与内容）。
  执行方式与设计略有不同：**E-P8-1 与 E-P8-3 合并** —— 用 `kill -9` 客户端（比 `--timeout` 主动放弃更狠）代替提前退出。
- 本轮：`run --prompt-file ask.txt --tag p8-kill`，thread `1d8f2104-5a3f-46d3-b382-d8626eaec39b` /
  turn `d67e8c37-1491-4d24-825c-05af7db66c10`，产物 `~/.local/state/toolsmith-runs/20260916-112352-p8-kill/`。
- **硬杀不取消 run**：客户端在第 3 次轮询（**40.5 s**，`status=running`）被 `kill -9` → 同一 turn 照跑到 `completed`
  （服务端 11:23:53 → 11:26:44，真实 **171.1 s**）。比 R8 的 T2（断 socket）更强。
- **resume 完整自愈**：`run --resume`（只重采集、完全不 POST）在窗口内补齐 → **16/16 PASS / exit 0**；
  27 次工具调用（27 returned + 0 schema-rejected；`read_file`×11 / `execute`×9 / `edit_file`×3 / `load_skill`×1 /
  params×1 / `write_file`×1 / `present_artifact`×1）；turn tokens `in=1,448,663 out=31,718 reasoning=21,648`；
  产物 `report.md` + `citations.json` + `endpoint-bar-1.json`（无 timeline 是正确的：两个 esid 属不同试验）。
- **事实清单第二份独立样本**：同一场景 A 的新产物 → `SCORE scenario=a facts 30/30 warn 1/1 -> PASS`（修正打分器句切后；修正前 29/30 是 O12 假 FAIL）。（**注**：这是 2026-09-16 当时的清单版本与分数；2026-09-17 清单修订后 A 为 31 条，同一产物重打分为 31/31）
- **P7 的描述被实测修正**：活窗口内 `/timing` 是**临时行**（`completed_at=null`、`completed=false`、`latency_ms` 现算递增），
  实测被读到的序列 190,000 → 350,200 → 429,651 → 443,488 ms；窗口过期后换成**持久化行**（三者同时变正确，
  `latency_ms` 冻结在 171,141＝真实耗时）。⇒ 活窗口的 `latency_ms` 不只是滞后，而是**大幅高估**；
  R8 的真实服务端耗时因此更正为 **202.0 s**（此前记的 “350.2 s server” 是活计数误读，O10 已修）。
- **P8 判定**：`>10 min` 后 `completed_at` + `/thread-turns/validate`（`exist: true`）仍可拿回结局与全量内容
  （`/messages` 23 条、`/debug/history` 4.26 MB、`/artifacts/archive` 19 KB）⇒ **体验问题，不报开发**；
  我们侧只需把「窗口过期后靠 `completed_at` 直接收尾」写进 `run`（连同 O13）。

### R10 — 2026-09-16，**runner 修复后的只读复测**（O14 + O15，零 POST）

改动对象只有本机 CLI（`~/.local/bin/toolsmith-publish`），**不涉 TS 平台、不涉仓库的 `skill/` 与 `system-prompts/`**，
因此没有触发 `publish`；但按「改完就要有 `R<n>` 记录」的规矩，仍逐项留证。改前备份
`~/.local/state/toolsmith-publish/toolsmith-publish.v2.bak`（85,409 B）。

| 测例 | 命令 | 期望 | 实测 |
|---|---|---|---|
| **T1** 窗口过期后 resume | `run --resume b1302c80-… --tag o14-recover --out …/o14-t1` | 立刻判定终态 + 跑完断言 | **exit 0，0.2 s 收尾**（旧行为是空转到 `--timeout` 报 exit 5），**16/16 PASS**，`wall clock 202.0s server`（冻结值） |
| **T2** 真 thread + 不存在的 turn | `run --resume b1302c80-… --turn-id 0000…0000 --grace 5` | `not_started` exit 4，且 probe **确实被调用** | **exit 4**；`run.json` 记 `uid_probe: true`（旧代码恒无 probe） |
| **T3** 不存在的 thread | `run --resume 0000…dead --turn-id 0000…0001 --grace 5` | `not_started` exit 4 | **exit 4** |
| **T4** R9 thread 复采集 | `run --resume 1d8f2104-… --tag o14-r9 --out …/o14-t4` | 走恢复路径且断言全过 | **exit 0，16/16 PASS**，0.2 s（服务端 171.1 s） |
| **T5** 零网络回归闸门 | `python3 evals/runner-gate/verify-run-chain.py` | 5 个 v1 run 逐条等于 SSE 链 | **GATE: PASS**（v2 两个 run 因 tap 是桩、两个 `--resume` run 因没有 tap 而 SKIP，均属预期） |
| **T6** `--resume` 不带 `--out` | `run --resume 1d8f2104-… --tag t6` | **不得**动原 run 目录 | 新建 `…/20260916-115033-resume-t6/`；R9 原 `verification.md` **md5 未变**（`9eb363896b87035f`） |
| **T7** R8 记录重建 | `run --resume b1302c80-… --tag r8-recollect` | 补齐被 O15 抹掉的记录 | `…/20260916-115047-resume-r8-recollect/` → 16/16 PASS |

同时把「断言总数 16（不是 17）」在三个文档里改正（先前的 17 是数错；`check_run` 在产出物路径上就是 16 个 `add()`）。
> **后续（2026-09-17）**：`30306cb` 之后新增「turn outcome 必须是 `succeeded`」一项 → 产出物路径 **17 项**、
> 拒绝路径 **11 项**（见本节上方 §1 的 2026-09-17 注）。R10 当时记的 16/16 是当时的事实，不改。

### F1 — 事实清单基线 + 负向对照（2026-09-16，**离线，零新 run**）

- **产物**：`evals/fact-check/`（`records/` 2 份 ground truth、`scenario-a/b.facts.json`、`check.py`、`mutations.py`、`README.md`）。
- **清单基线**（直接打 R8 产物，未重跑）：`SCORE scenario=a facts 31/31 warn 1/1 -> PASS`（exit 0）、
  `SCORE scenario=b facts 12/12 warn 1/1 -> PASS`（exit 0，B 打的是 R6 拒产 run）。
- **负向对照（证明清单有牙）**：`python3 evals/fact-check/mutations.py` → **GATE PASS**：
  arm A **16** 个变异翻天 31/31 条 fail 级条目（M05 改引注、M15 表格单元格跨记录归属、M16 删图不解释）；arm B **11** 个变异翻天 12/12 条；
  每个变异都令退出码变 **3**，且必须命中**预期 item id**（只判 `rc==3` 不够）。基线（未变异）两份清单必须全 PASS。
- **第二份独立样本**：R9（同一场景 A 的新产物）→ `SCORE scenario=a facts 31/31 -> PASS`（修正 O12 的句切后；O17 清单修订后再跑仍是满分）。
- **意义**：质量层从「布尔门」升级为 `facts_ok/facts_total` 标量（`docs/autoresearch-iteration-plan.md` §9），
  后续 keep/discard 先看事实分不掉。

### F3 — 2026-09-18，**arm A 基线从「补过一行的 R8 副本」换成真产物 R17**（离线，零新 run、零发布）

用户 2026-09-18 授权「做呗」。改动只在**仓库评测资产**（`evals/fact-check/mutations.py` + `README.md`），
**没碰 `skill/`、`system-prompts/`、runner、平台** ⇒ dist 无变化 ⇒ 不需要重新打包，也不需要发布授权。
清单条目与 `check.py` **一个字没改**——这次换的是**基线产物**和**变异措辞**，不是判分口径。

**为什么要换**：arm A 的基线一直是 R8（`20260916-104943-v2-poll`，2026-09-16）的**临时副本**，且
`fresh()` 会往副本里注入一行 `原文核对：`（`seed_original_check`）——因为 R8 早于原文优先规则，产物里不可能有这一行，
不补的话基线自己就会因 `A-P1` 而不干净。R17（`20260918-095553-r17-sign-convention`，数值口径定案后 in-place
发布跑出来的那一版）是**逐条全绿**的真产物，且**原生带** `原文核对：` 行 ⇒ 基线可以「原样判分」，
`seed_original_check` 的存在理由随之消失。

**做了什么**

- `SRC_A` 默认值 → `~/.local/state/toolsmith-runs/20260918-095553-r17-sign-convention`（仍可用 `MUT_RUN_A` 覆盖）；
  删除 `seed_original_check()` / `SEED_ORIGINAL_CHECK` 常量、`fresh()` 里的调用、`arm()` 里「baseline is seeded」的注释。
- 6 条变异按 R17 的真实字节重写（README 里有 R8 版 ↔ R17 版对照表）：
  `M01`（`13\.9` 全替）、`M03`（替 `[OCEAN(a)-DOSE](entity:trial:NCT04270760)`，`count=0`）、
  `M06`（H1 只点一个药，走 `A-T1` 的「只点一个 subject」FAIL 分支）、`M07`（`2 ?条` 全替）、
  `M15`（ref_2 行的药名单元格换成 ref_1 的药名）、`M21`（加全文归档**并**把覆盖行改写成只声明摘要路径）、
  `N26`（改用「两个 subject 都点名」的标题——R17 的基线本身就是主题式标题，旧的 N26 在它身上是空转）。
- 新增 `FT_XML` 常量（M21/M22 共用的最小 JATS 正文），避免两处字面量各写一遍。

**证据（负向对照闸门，`python3 evals/fact-check/mutations.py`）**

```
baseline a: 40 fail-severity items, all PASS
[OK ] M01 minus139 / M02 signflip / M03 drop-trial-id / M04 timepoint / M05 wrong-ref / M06 …
[OK ] N25 mixed-sentence-not-misattributed  rc=0 kept A-ATTR-misattribution green
[OK ] N26 theme-title-accepted             rc=0 kept A-T1-title-identifies-scope green
[OK ] N27 trial-id-contrast-sentence        rc=0 kept A-ATTR-misattribution green
arm a: flipped 40/40; never flipped []
baseline b: 12 fail-severity items, all PASS
arm b: flipped 12/12; never flipped []
GATE: PASS
```
（完整输出 48 行、41 个 `OK` 行，**已落库**：`docs/evidence/mutation-gate-2026-09-18-r17-baseline.txt`；
harness 每次跑都把 run 目录重新复制到临时目录，可重复，退出码 0。）

真产物直接判分（口径未变）：`SCORE scenario=a facts 40/40 warn 1/1 -> PASS`。

**两次踩坑（都留了痕，正是「变异必须真能翻出对应 FAIL」的价值）**

1. `M01` 第一版只替带负号的 `−13.9` ⇒ `A-C4` 仍是绿的：R17 散文里有一处「与 [依洛尤单抗] 的 `13.9%` 之差」不带负号，
   而 `A-C4` 的图案本就是 `[\u2212-]?`（符号可选，见 O26）。改成 `(?<![\d.])13\.9` 全替后翻出 `A-C4`。
   ——顺带记一条判分器性质：**符号可选的图案，只替一种写法等于没改**。
2. `M03` 第一版用 `sub_lit(...)` 没给 `count`，默认 `count=1`，22 处只改了 1 处 ⇒ harness 报
   `[BAD] M03 drop-trial-id  rc=0 flipped=[]`，闸门直接 FAIL（`A-C2` 要 3 个图案**全中**，只打掉一处不够）。
   改成 `count=0` 后翻出 `A-C2`。

**与 F2 的关系**：F2 记的是打分器两类假阳性（O19/O20）+ O28 的修复；当时明确写了「`MUT_RUN_A` 仍指向带 seed 的 R8 副本，
换基线是一件独立的事」。本条就是那件独立的事，`O20` 行的状态随之补一句，F2 的「没做的（有意）」段落后加了一条指向本条的备注。

### F2 — 2026-09-18，**打分器两类假阳性修复（O19 / O20）+ 顺手挖出的 O28**（离线，零新 run、零发布）

用户 2026-09-18 授权「O19-20 都可以改」。三处全在**仓库评测资产**（`evals/fact-check/`），
**没碰 `skill/`、`system-prompts/`、runner、平台** ⇒ dist 无变化 ⇒ 不需要重新打包、也不需要发布授权。

**改了什么**

| # | 缺陷 | 旧行为 | 新行为 |
| --- | --- | --- | --- |
| O19 | `A-ATTR-misattribution` 把「比较句/排除句」判成错配 | 只看「unit 里的 token，其 owner 必须∈该 unit 的 refs」⇒ `R15` 的 `…与 [奥帕司兰] 的 Lp(a) 降幅终点不是同一构念{{ref_1}}`、`R12` 的 `安全性维度只有 [OCEAN(a)-DOSE]…{{ref_2}}，[NCT02729025] 未报告…` 全被判 FAIL | `pairs` 引入 `"subject": true`＝**记录的身份证**（药名 + 登记号/试验名）。**身份对**：unit 若同时点了**引注记录自己的身份证** ⇒ 这是比较句，豁免（PASS 信息记 `identity pairing(s) skipped as comparison`）。**数值对：永不豁免**——引注 ref_2 却带 ref_1 的数值照旧 FAIL |
| O20 | `A-T1-title-names-both` 期望过窄 | 只认「H1 同时出现两个药名」⇒ `R16/R17` 的主题式标题 `# 脂蛋白(a) 升高人群降脂治疗跨试验对比报告` 被判 FAIL，而模板第 1 行本来写的就是 `# [比较主题]跨试验对比报告` | 改名 `A-T1-title-identifies-scope`，改 `kind: shape` / `op: title_scope`：① 两个 subject 都点名 ⇒ PASS；② 一个药名都不点但命中 `theme_all`（人群 + 对比标记）⇒ PASS；③ **只点一个** ⇒ FAIL（这才是本条要防的「两条记录读成同一个药」）；④ 两者都不占 ⇒ FAIL |
| O28 | **`A-ATTR` 的数值 token 写错符号，整个数值分支从未命中过任何产物**（核 M27 时发现） | token 是 ASCII `-13\.9`，而四份真产物正文一律 U+2212（`−13.9`，R8/R12 各 5 处、R17 9 处）⇒ 「数值对」这条静默失效（假绿方向） | token 改 `[\u2212-]`（与 O26 的「符号写法自由」同源）；改后重打四份产物**无新增 FAIL** |

**证据（负向对照 harness 升级）**：除 27 条正向变异（M1–M27，翻天 40/40 条 fail 级条目）外，
新增 **假阳性回归对照 `NEG_A`/`NEG_B`**——`arm()` 现在会断言指定条目**保持绿**（只 `rc==3` 的旧判法抓不到「改大了」的过头修复）：

- `N25`：`R15` 形状的混合句（引注 ref_1 + 句内点两条记录的药名）→ `A-ATTR` 必须保持绿；
- `N26`：主题式标题（无药名）→ `A-T1-title-identifies-scope` 必须保持绿；
- `N27`：`R12` 形状的登记号对照句（引注 ref_1 + 提对方试验）→ `A-ATTR` 必须保持绿；
- `M27`：在点了对方登记号的句子里塞进**另一条记录的数值** → `A-ATTR` **必须翻 FAIL**（证明豁免只对身份对生效，不是全免）；
- `M06`（标题药名换成另一个）与 `M15`（表格单元格内跨记录错配）**照旧必须翻**，保证豁免没有把 `A-ATTR` 的牙拔掉。

```
baseline a: 40 fail-severity items, all PASS          baseline b: 12 fail-severity items, all PASS
[OK] M06 cross-attribution  flipped=['A-T1-title-identifies-scope']
[OK] M15 cross-attribution  flipped=['A-ATTR-misattribution']
[OK] M26 generic-title      flipped=['A-T1-title-identifies-scope']
[OK] M27 value-misattribution-under-exemption flipped=['A-ATTR-misattribution']
[OK] N25/N26/N27            rc=0, 目标条目保持绿
arm a: flipped 40/40; never flipped []      arm b: flipped 12/12; never flipped []
GATE: PASS
```

**真产物重打分（同一打分器，四份历史产物 + R17）**

| 产物 | 旧分 | 新分 | 说明 |
| --- | --- | --- | --- |
| R17 `20260918-095553-r17-sign-convention` | 39/40（唯一 FAIL＝O20） | **40/40 PASS** | 第一个满分真产物 |
| R8 `20260916-104943-v2-poll` | 31/31（当时清单） | 39/40 | 唯一 FAIL＝`A-P1` 原文核对行（R8 早于原文优先规则）⇒ arm A 仍需 `seed_original_check` |
| R12 `20260917-191502-r12-fanout-dedup` | 29/31 → 旧打分器 37/40 | 39/40 | `A-ATTR` 假阳性消失；剩 `A-P1` 同上 |
| R15 `20260918-092157-r15-l3-scenario-a` | 36/40 | 37/40 | `A-ATTR` 假阳性消失；剩 3 条是**真**模板泄漏（`A-P2/A-P7/A-P8`） |
| R16 `20260918-094333-resume-r16-resume` | 36/40 | 37/40 | `A-T1` 转 PASS；剩 `A-C16`（待样本）+ `A-P2/A-P8`（真缺陷） |

**没做的（有意）**：`MUT_RUN_A` 仍指向「补过一行」的 R8 副本。R17 是现成的干净基线，但实测指过去会打掉 4 条**绑定 R8 字节**的变异
（`M01 minus139` / `M06` 首个药名 / `M07`「2 条」/ `M15`「试验 B {{ref_2}}」表格行在 R17 产物里匹配不到或改不动），
且 `M21` 依赖「基线不提全文」这个前提，而 R17 的覆盖行本来就写了「R7 全文接口返回 500（该刊非 OA）」。
换基线＝按 R17 真实字节重写这几条变异，是一件独立的事，记在 `O20` 条目里等下一步做。
（**后续**：2026-09-18 用户授权后已做——见 `### F3`：基线重指 R17、`seed_original_check` 删除、6 条变异重写。）

### R11 — 2026-09-17，**platform `30306cb` 契约变更后的 runner 适配**（只读复测 N1–N4 + 1 次真跑 + 拒绝路径复核）

背景：上游 `30306cb remove unknown status, add idle` 把 `/info.status` 收敛为 `Literal["preparing","running","cancelling","idle"]`
并删掉 `cleanup_stale(300)`（run 一结束即 `_discard_run`），**P7 从根修掉**，同时**任何结局都不再出现在 `/info` 里**。
改的对象只有 runner（本机 CLI；备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v3.bak`，88,308 B），
**未动 TS 平台、未动 `skill/` 与 `system-prompts/`**，所以没有触发 `publish`。

改动：① `wait_for_run()` 学新词表（`preparing/running/cancelling` 继续轮询、`idle` 转 durable 分支、老值 `completed/failed/cancelled` 兼容）；
② `idle` 但**没见过活状态**且 `/timing` 行无 `completed_at` + `/thread-turns/validate` 说 `exist!=true` → `not_started`（exit 4，不再空转）；
③ **见过活状态却突然消失**且无 `completed_at`（进程重启）→ 立刻 `inconclusive`（exit 5），不再空转到 `--timeout`（连续两次 `idle` 才算，避免误读）；
④ 新增 `classify_outcome()`：读**已抓下来的** `messages.json`（零新增网络请求），`error_type` 非空 → failed、`state == "interrupted"` 或 error_type 含 Cancel → cancelled、无消息 → `unknown`、否则 succeeded；
⑤ 终态/结局写进 `run.json`、`verification.md` 与 stdout；⑥ 新增第 17 项断言。

| 测例 | 命令 | 期望 | 实测 |
|---|---|---|---|
| **N1** 已完成 thread（R8） | `run --resume b1302c80-… --tag idle-r8` | 新词表下仍判 `completed` + durable 耗时 | **exit 0，0.2 s**，`status=idle` → `timing.completed_at`，**17/17 PASS**，`202.0s server` |
| **N2** 已完成 thread（R9） | `run --resume 1d8f2104-… --tag idle-r9` | 同上 | **exit 0**，**17/17 PASS**，`171.1s server` |
| **N3** 真 thread + 不存在的 turn | `run --resume b1302c80-… --turn-id 0000…0000 --grace 5` | `not_started` exit 4 且 probe 真被调用 | **exit 4**（2 次轮询 / 5.6 s），`run.json` `uid_probe: true` |
| **N4** 不存在的 thread | `run --resume 1111…5555 --turn-id 0000…0000 --grace 5` | `not_started` exit 4 | **exit 4**（`/info` 非 2xx 也走同一分支） |
| **R11** 真跑（新契约下的活路径） | `run --prompt-file ~/.local/state/toolsmith-runs/ask.txt --tag r11-idle-vocab` | 看到活词表 → idle → durable 收尾 | thread `ea0b6213-…` / turn `ee2ff701-…`；轮询 10 次：`running`×9 → `idle`；**exit 0，17/17 PASS**；`177.6s server / 188.9s polled`；`last_live=running durable=timing.completed_at`，`outcome=succeeded` |
| **拒绝路径复核** | `run --resume 73b427f3-… --expect refusal` | 拒绝契约仍全过 | **exit 0，11/11 PASS**（含新增的 outcome 项） |
| **零网络回归闸门** | `python3 evals/runner-gate/verify-run-chain.py` | 5 个 v1 run 逐条等于 SSE 链 | **`GATE_RC=0` / GATE: PASS**（2 个 v2 + 2 个 resume 按预期 SKIP） |
| **离线单测 `classify_outcome()`** | 直接吃 `messages.json`（零网络） | 成功/失败/取消/超时/空/跨 turn 六种 | R8 与 R9 真记录 → `succeeded`；合成 `stream_error` → `failed`；`interrupted`+`RunCancelled` → `cancelled`；`TimeoutError` → `failed`；空列表 → `unknown`；错误只出现在别的 turn → `succeeded` |

- **顺带证实**：`run` 在 R11 上是「客户端 0.1 s 断流、run 与客户端断开无关」的又一次复现（与 R8 的 T2 同结论）。
- **事实分（离线清单，非本 runner 职责）**：R11 产物打 `scenario=a` → **`facts 25/30`（FAIL）**，
  与 R8 同输入的 `30/30` 不同。逐条分诊见下方 §3 的 O16（图表断言缺口）与 **O17**（清单期望本身与规则文本冲突）—— 5 个 FAIL 里 **3 个是清单自身的期望与规则文本冲突**、
  1 个是模式过窄（字面 `2 条` vs 产物写的 `2 项`）、1 个（A-C6：未报安慰剂组 +3.6%）**像真的内容缺口**。
  ⇒ **当时不改清单迁就产物**，三项挂「待用户判定」。
- **（2026-09-17 后续，已判）** 用户批准修清单（O17）后已落地：`A-S2b-chart-or-reason` 新增（无定量图必须在正文说明白）+
  `A-S8/A-S9` 改条件式 `optional_when_absent` + `A-C12` pattern 放宽为 `2 ?(条|项)` +
  变异 `M16 drop-chart-silent` → **R11 重打分为 `30/31`（只剩 `A-C6`）**、R8/R9 基线 **31/31**（新增一条条目）、
  B 仍 12/12、`mutations.py` 覆盖 31/31 GATE PASS；正向对照（删图+写明原因）仍 31/31 PASS。

### R12 — 2026-09-17，**一个 esid 多行扇出的兼容措辞**（本地先行，发布未授权；部署一致性 3 项 FAIL 属预期）

背景：产品侧确认「一个 esid 扇出多行」是**疾病 join 引入的**（不是可依赖的语义），要求 Skill 侧兼容。
只读实测（`POST /api/tools/debug`）：`extra_esids=[24_1_30561610, 24_1_36342163]` + `selected_fields=[clinical_result.indication_name]`
→ **5 行**（3+2），每行被请求字段的取值**完全相同**，只有注入列 `disease_id` 不同（该列**不可请求**：写进 `selected_fields` 直接 `INVALID_INPUT`）；
同样两个 esid 改请求 `paper_title` / `indication_detail` / `indication_type_cn` → **各 1 行**。
⇒ 病名只存在于 `indication_name` / `_en`（`indication_detail` 是描述入组人群的**句子**、`indication_type_cn` 是**领域**），**没有替代字段**，只能接受扇出 + 去重。

改动（4 个仓库资产文件；**未动 runner、未动 TS 平台**）：
① `references/input-contract.md` 新增 `### Row fan-out: one esid can return several rows`（触发条件 / 实测行数 / **去重时机在编号与计数之前** / 注入列不得进正文 / 不可用 `indication_detail` 替代）+
Recommended `selected_fields` 收尾一句；② `SKILL.md` 输入契约段加「按 `extra_esid` 去重 = 一词一 marker」；
③ `references/citation-and-ref.md` 加同义规则；④ sys `-v0.15.md` 第 7 行加同义子句；
⑤ 顺带修 `evals/fact-check/README.md` 的条目计数笔误（场景 A 实为 **31 fail + 1 warn**，文中写作 30）。

| 项 | 值 |
|---|---|
| 命令 | `toolsmith-publish run --prompt "解读这几个结果 24_1_30561610 24_1_36342163" --tag r12-fanout-dedup` |
| thread / turn | `89c055da-3c8b-4a6e-90ee-7f779510c3f3` / `c100df33-c1d0-4f28-91d0-149d44219f29` |
| 终态 / 结局 | `completed`（durable `timing.completed_at`）/ `succeeded` |
| 墙钟 | 201.8 s server / 207.9 s polled（11 次轮询：`running`×10 → `idle`） |
| 调用 | **36 次**：`execute`×16、`read_file`×15、`load_skill`×1、`params`×1、`write_file`×1、`edit_file`×1、`present_artifact`×1；schema 被拒 0 |
| token | thread in 110,371；turn in 2,210,912 / out 36,713 / reasoning 24,864；cache 97.6% |
| 产物 | `output/report.md`、`output/citations.json`、`visualizations/endpoint-bar-1.json` |
| 断言 | **14 PASS / 3 FAIL（exit 3）** —— 3 个 FAIL 全是「部署端 == 本地」一致性项（prompt `d58b0638ce34`、SKILL 19,580 vs 19,933、`citation-and-ref.md` 7.9 vs 8.33 KB、`input-contract.md` 16.4 vs 18.74 KB）：**本地已改而未发布**，属预期信号而非缺陷 |
| 事实分（离线清单） | `scenario=a facts 29/31 warn 1/1 -> FAIL` |

**基线行为（旧版部署内容 + 扇出输入）**：旧版**照样去重成功** —— 正文写「2 项独立试验、各 1 条结果来源」，
`citations.json` 恰为 `ref_1`/`ref_2` 且标题非空 ⇒ 再次印证扇出是**潜风险而非在线缺陷**。
但代价可见：模型为了弄清「5 行 → 2 条记录」用了 **16 次 `execute` + 15 次 `read_file`**（枚举 jsonl、逐行比对），
36 次调用 / 201.8 s 里相当一部分就是这个探索 —— 这正是新增措辞要省掉的部分。

**事实分 2 个 FAIL 的分诊（都不像内容缺口）**：
- `A-ATTR-misattribution`（**打分器假阳性，见 O19**）：合法的一句多 marker 被判错配。
- `A-T1-title-names-both`（**清单期望过窄，见 O20**；已修：现名 `A-T1-title-identifies-scope`，`R17` 回填 **40/40**）：主题式 H1 不含药名即 FAIL，但药名都在正文锚点里。

**下一步**：发布授权 → `publish`（原地更新 prompt v1.6 + skill 1.0.7）→ 同输入重跑 → 新记录（预期 17/17 PASS，并把事实分与调用数与本次基线对比）。

### R14 — 2026-09-18，**L3 发布后的真跑**：全文即分析面 + 引用落点跟随深度（**17/17 PASS**）

背景：用户 2026-09-18 授权「原地更新，不要新版本」⇒ `publish`（prompt v1.6 / skill v1.0.7 同版本号替换内容），
回读一致（prompt 逐字节 == 本地、skill `19 identical / 0 differing`、`STATUS: in sync`）。随后真跑验证 L3。

| 项 | 值 |
|---|---|
| 命令 | `toolsmith-publish run --web --prompt "解读这几个结果 24_1_39054491_1 24_1_42477684_1" --tag r14-l3` |
| thread / turn | `273e52b4-ab76-4dbf-b0d6-ad324835c34f` / `b096510f-63bd-41ec-8f31-d3ce3dee4cb9` |
| 终态 / 结局 | `completed`（durable `timing.completed_at`）/ `succeeded` |
| 墙钟 | 148.0 s server |
| 调用 | **26 次**：`execute`×8、`read_file`×8、`grep`×3、`web_fetch`×3、`load_skill`×1、`params`×1、`write_file`×1、`present_artifact`×1；schema 被拒 **0** |
| token | thread in 96,478；turn in 1,188,741 / out 26,793 / reasoning 15,653；cache 93.0% |
| 产物 | `output/report.md`（22,031 B）、`output/citations.json`、`sources/PMC11270764_fulltext_jats.xml`（100,030 B）、`sources/PMC11270764_plain.txt`（49,169 B） |
| 断言 | **17 PASS / 0 FAIL（exit 0）** —— 含「部署端 == 本地」（sys `837ef4cc16c9`、SKILL 22,706 ch、支持文件 18 个）与「citations 键集/日期/`title` 非空」 |
| 记录 | `~/.local/state/toolsmith-runs/20260918-092000-resume-r14-l3-recollect/`（原目录 `…091057-r14-l3` 因下述 O23 事故只留 `run.json`/`timing.json`，按 O15 约定冻结不覆盖） |

**输入为什么选这两条**（直接压 L3 的两个分支）：`24_1_39054491_1` = `src=1` 且 `R6` 能拿到 `PMC11270764`（走全文分支）；
`24_1_42477684_1` = `src=1` 但 `inPMC=N`、无 pmcid（走「无 PMCID / 非 OA，保持摘要级」分支）。

**L3 的四条行为逐条核实（不是「断言过了」，是逐项对照产物）**

1. **引用落点跟随深度**：`output/citations.json` 里 `ref_1.link = https://pmc.ncbi.nlm.nih.gov/articles/PMC11270764/`（C1），
   而该记录库内的 `full_article_link` 是 `https://pubmed.ncbi.nlm.nih.gov/39054491` ⇒ **发生了唯一一次、且只对该记录发生的替换**；
   `ref_2.link` 仍**逐字节**等于库内 `full_article_link`（`…/42477684`），两条 `title`/`paper_release_time_str` 未被动过。
2. **全文确实被归档**：`artifacts/sources/` 下有 JATS 原文 + 纯文本（100 K / 49 K），覆盖行也点名了 `PMC11270764` **全文**（`A-P5`/`A-P6` 双双满足）。
3. **逐记录声明分析深度**：覆盖行原文 —— 「2 条均属 PubMed 来源类（src=1），均按 R6→R7 链路核对：1 条取回并归档 PMC11270764 **全文**（PMID 39054491，按全文分析），1 条无 PMCID（PMID 42477684，inPMC=N、非 OA，仅摘要级）→ 按全文分析 1 条 / 仅摘要级 1 条」，并补一句「该记录基于全文分析，其引用指向全文页面而非摘要页」。这正是 L3 要的**透明性**：读者能分辨「原文没写」与「我们没查」。
4. **真拿到了摘要里没有的事实**（L3 的实质收益，用库内 `abstract_text` 逐字对照，2,590 字符）：
   `36.0`（PD-L1 CPS≥10 ORR）、`18.5`、`26.3`、`90.7`、`87.8`（任何 AE）、中位暴露「86 天」、`CPS` 自身 —— **全部不在摘要里**（仅 `31.8`/`24.5` 主要 ORR 在摘要中）；
   报告把这些放在 `### 4.3 亚组与一致性` 并带标签（「安全性分析集 43 / 49」「亚组事件数小，原文未报告交互检验」），没有裸用。

**顺带发现（库内字段与原文矛盾，同指标同标签 ⇒ 按规则写双值）**：该记录 `clinical_result.blinded = ['开放']`，
而原文（摘要 1 次 + 全文 3 次）均为 **double-blind**（ECHO-307/KEYNOTE-672 是双盲安慰剂对照 III 期）。
报告写成 `原文 double-blinded；库内记录 开放{{ref_1}}`（符合 `A-P2` 格式）。⇒ 这是**可转开发的库内数据问题**，
记入 A10 待发清单（暂不单独发；等 A5/A6/A7 一起走）。

**行为对比基线（R12）**：调用 36 → **26**（扇出去重措辞生效：R12 为弄清 5 行→2 条花了 16×`execute`+15×`read_file`，
本次 `grep`×3 定位、`web_fetch`×3 = 恰好 R6→R7 取全文 + 1 次补取），墙钟 201.8 → **148.0 s**，产出多出 `sources/` 全文归档。

**结论**：L3 在平台上**已验证生效**（不是「规则写了」）。仍开着的两条：① 只压到 1 条全文记录 + 1 条无 PMCID 记录，样本窄；
② `A-P6` 只覆盖「已归档全文」方向，反向（引用指全文却无归档）仍无断言 —— 等更多样本再决定是否加。

### R17 — 2026-09-18，**数值口径定案后 in-place 发布 · 同输入第四次跑**（`39/40`，唯一 FAIL 是已知的 O20）

**用户决策（2026-09-18）**：对台账 ③ 两问的回答是 ——
> 「**三没关系，只要自洽就行。in place**」

即：① 数值符号写法**两种都可以**（`−13.9` 与「降低 13.9%」等价），合同不写死，**但同一份交付物必须自洽**；② O27（`A-C16` 术语绑定）不专门处理；③ 授权**原地更新**（prompt 仍 `v1.6`、skill 仍 `v1.0.7`）。

**发布（in-place，回读为准）**

| 对象 | 命令 | 结果 |
|---|---|---|
| prompt | `push-prompt --version 1.6` | `POST /api/prompts/…/versions -> HTTP 200`；回读 `current=v1.6 matches_local=True`；`52,919 B / sha 06e07ca11a91` |
| skill | `push-skill --version 1.0.7` | `POST /api/skills/update_skill_file -> HTTP 200`；`skill_id=ad75ec2c… version=1.0.7 is_current=True`（HTTP 200 字段照旧无信息量，判定看 `status` 回读） |
| 回读 | `status` | `prompt deployed == local: True`；`zip entries=19 identical=19 differing=0`；**`STATUS: in sync`** |
| 上游 | `deps` | `DEPS: unchanged since the recorded baseline`（发布前 `publish` 也跑过一遍） |

**规则改动（按用户口径）**

| 文件 | 改动 |
|---|---|
| `references/input-contract.md` | 新增 *Number rendering: one convention per deliverable*：两种写法等价、**禁止在同一份交付物里混用**（报告与图表必须同口径）；作用域只限**被画进图的那几个量**（点估计无符号 + CI 带符号是正常渲染） |
| `system-prompts/...-v0.15.md` | 同步一句（sign convention is free, but one deliverable uses exactly one） |
| `evals/fact-check/scenario-a.facts.json` | `A-C4` / `A-C5` 模式改 `[\u2212-]?`（符号可选，数值仍逐位精确）；`A-S9` 比绝对值；新增 **`A-S10-sign-convention-consistent`**（`values` 里被画的量在报告与图表必须同口径）→ **41 条（40 fail + 1 warn）** |
| `evals/fact-check/check.py` | `op_chart_values` 改符号无关（`|got|` vs `|want|`）；新算子 `op_sign_convention_consistent` + `_form_of` |
| `evals/fact-check/mutations.py` | 新变异 **`M25`**：先读基线报告用哪种口径，再把**图表**改成另一种 ⇒ 只翻 `A-S10`（数值不动，`A-S9` 保持绿，正是隔离性证据） |
| `evals/fact-check/README.md` | 计数 40 → 41、arm a 40/40、`A-S10` 行、M25 明细 |

**为什么这样改不算「为迁就产物放宽清单」**：放宽的是**写法**、不是**数值**（`M01` 把 13.9 改成 19.9 仍翻 `A-C4`，`M10` 改图表数值仍翻 `A-S9`），并且**同轮加了一条更严的 `A-S10`** 换回来（口径混用以前根本没人管）。另外注明一点等价的覆盖面：方向**措辞**在两种口径下都没被断言（带符号写法里「升高 −13.9%」本来也能过），所以放宽不产生新的盲区。

| 项 | 值 |
|---|---|
| 命令 | `toolsmith-publish run --web --tag r17-sign-convention --prompt "解读这几个结果 24_1_30561610 24_1_36342163"` |
| 终态 | `completed` / `succeeded`（10 次轮询 / 186.2 s polled） |
| 调用 | **27 次尝试**，1 次 schema 被拒（`web_fetch`，框架重发后成功；O25 新口径单列） |
| 断言 | **18/18 PASS**：部署端 prompt sha `ac0b7e71c2db`（本地前缀 51,860 ch + 平台尾部 19,197 ch）、部署端 `SKILL.md` 22,706 == 本地、18 个支持文件清单一致 |
| 产物 | `output/report.md`、`output/citations.json`、`visualizations/endpoint-bar-1.json`（图表值 `[-13.9, -70.5, -97.4, -100.5, -101.1]`，全带符号） |
| 事实分 | **`SCORE scenario=a facts 39/40 warn 1/1 -> FAIL`** —— 唯一 FAIL 是 **`A-T1-title-names-both`（已知 O20：主题式 H1 被判）**（**O20 修复后回填 `40/40 -> PASS`**，见 `### F2`）；`A-C4/A-C5/A-S9/A-S10/A-P2/A-P7/A-P8/A-ATTR` 全 PASS |
| 记录 | `~/.local/state/toolsmith-runs/20260918-095553-r17-sign-convention/`（`verification.md` / `transcript.md` / `artifacts.zip`） |

**本轮四个确认**

1. **O24 彻底闭环**：覆盖行 `2/2 条已复核（src=1 PubMed 类：PMID 30561610 经 R6 取回 PMCID PMC6933872，但 R7 全文接口返回 500（该刊非 OA），按库内摘要核对；PMID 36342163 经 R6 无 PMCID 且 inPMC=N，属非 OA，按库内摘要核对）；本批次 0 条按全文分析、2 条仅摘要级` —— **无任何规则句**（`A-P7`/`A-P8`/`A-P2` 全 PASS），路径、原因类、分析深度齐备（`A-P4` PASS）。
2. **口径规则落地生效**：该跑自觉选了带符号口径、图表与正文一致（`A-S10` PASS）；同一份清单打 R16（幅度口径）也 PASS ⇒ 两种写法都能过，而混用会被 `M25` 抓住。
3. **`A-C16` 本轮 PASS**（报告用了「心血管事件」词面）⇒ O27 目前是 **1 失败 / 1 通过**，维持「待样本」，不凭 1 份产物改规则。
4. **`A-ATTR` 本轮 PASS**（R15 那次是 O19 的假阳性）⇒ O19 的判定口径仍未定，但不再妨碍「找一份干净基线」。

**观察到的细节（刻意不判 FAIL）**：报告里 `13.9` 出现 9 次带符号、1 次不带符号，那一处是散文比较句「…与 [依洛尤单抗] 的 `13.9%` 之差远超…」。
`A-S10` 是**口径级**而不是**逐处级**断言：逐处强制会把这种自然表述判错。这一条写进理由里了。

**`MUT_RUN_A` 的状态更新**：R17 是**第一份除 O20 外全绿的场景 A 真产物**（且原生带 `原文核对：` 行 ⇒ `seed_original_check` 的存在理由消失）。
但直接指过去前必须先确认 `M21`/`M22` 的自足性 —— R17 没归档任何全文（非 OA），`A-P5`/`A-P6` 在它身上不触发，
两个变异必须自己 plant 全文归档才能保持「arm a 40/40 全翻」（`M21`/`M22` 本来就是这样写的）。**已于 2026-09-18 完成 → `### F3`**。

### R16 — 2026-09-18，**模板修复上线后的场景 A 收口复跑**（同输入第三跑：`A-P7` 复验通过；又挖出一类「换措辞」泄漏 + 一类「数值写法口径」缺口）

**跑法（含一次 shell 中断的处置）**：先 `toolsmith-publish push-skill --version 1.0.7`（in-place，回读 `19 identical / 0 differing`，`STATUS: in sync`）把 `A-P7` 修复上线；
随后用**与 R12/R15 完全相同的输入**跑 `run` —— POST 已发出（thread `b31bdfb7…`）后我的 shell 被中断，`20260918-094215-r16-templates-fixed/` 只留下
`prompt.txt`/`run.json`/`stream.tap`（O15 同类冻结残档，**不重跑**）；按 O23 的做法用 `run --resume b31bdfb7-a457-4f7d-8a09-23b0e91e373c --tag r16-resume` **重新收集**成完整记录。

| 项 | 值 |
|---|---|
| 命令 | `toolsmith-publish run --resume b31bdfb7-a457-4f7d-8a09-23b0e91e373c --tag r16-resume --web` |
| thread / turn | `b31bdfb7-a457-4f7d-8a09-23b0e91e373c` / `11072d2c-9eb3-4180-8100-fb9e56377923` |
| 终态 / 结局 | `completed` / `succeeded`（8 次轮询；tap: skipped (--resume)） |
| 墙钟 | 206.4 s server / 144.8 s polled |
| 调用 | **30 次尝试 = 28 返回 + 2 schema 被拒**：`execute`×12、`read_file`×10、`web_fetch`×2、`load_skill`×1、`params`×1、`write_file`×1、`present_artifact`×1；被拒 2 次 = `bash`×1、`web_fetch`×1（O25 新口径渲染，计数自洽） |
| token | thread in 110,828；turn in 1,772,089 / out 39,986 / reasoning 24,031；cache 96.6%；上下文 total 110,828（sys 22,835 / mcp 5,919 / tools 56,761 / skill 22,610 / conv 2,703） |
| 产物 | `output/report.md`、`output/citations.json`、`visualizations/endpoint-bar-1.json` |
| 断言 | **18/18 PASS（exit 0）**，含「部署端 prompt 逐字节 == 本地」「部署端 skill 正文 + 18 个支持文件逐字节 == 本地」 |
| 事实分 | `SCORE scenario=a facts 32/39 warn 1/1 -> FAIL`（同期清单 38 → 39 条 fail 级，见下）；**O20 修复后回填 `37/40`**（`A-T1` 转 PASS；剩 `A-C16` 待样本 + `A-P2/A-P8` 真缺陷），见 `### F2`） |
| 记录 | `~/.local/state/toolsmith-runs/20260918-094333-resume-r16-resume/`（冻结残档：`~/.local/state/toolsmith-runs/20260918-094215-r16-templates-fixed/`） |

**①`O24` 的修复在真跑里得到确认（本轮主要目的）**

- 三个 `A-P7` 字面（`原文优先于库内加工字段` / `不静默取一侧` / `库内记录值`）在 `report.md` 里 **0 次命中**；
- 覆盖行不再是规格句，而是实质内容：`原文核对：2/2 条检索记录均已按原文复核，两条同属 PubMed 来源类（src=1），复核路径为 Europe PMC 题录核对后尝试 PMC 全文：1 条（PMID 30561610）返回 PMCID PMC6933872，但全文取回失败（该记录非 OA，全文接口返回 500），未归档全文；1 条（PMID 36342163）…`（`A-P4` PASS）；
- 部署端断言「skill 正文 + 18 支持文件逐字节 == 本地」PASS ⇒ 线上确实换成了修好的模板。

**②`A-C16` 说明：本节第二条 L3 反向证据（非 OA）在这一跑里再次成立**：`24_1_30561610` 依旧命中 `PMC6933872`、依旧非 OA、依旧没有构造链接（`citations.json` 两条 `link` 与 R15 逐字节相同）。

**③ 新缺陷（我们自己的资产，与 O24 同类但换了写法）：规则句被「换措辞」照写进交付物**

覆盖行末尾出现：`未发现原文与库内记录在同一指标、同一口径上的数值不一致；` —— 没有数值、没有 `{{ref_n}}`，读者拿不到任何信息；
它是模型把我们的规则**改写**了一遍（R15 逐字照抄、R16 换措辞，说明只靠字面表抓不住）。修法（仓库资产，三处）：

| 文件 | 改动 |
|---|---|
| `templates/*.md`（4 个） | `原文核对：` 规格括号内补一句：本行只写复核路径/分析深度/未能复核的原因类，**不复述本规则措辞、不写「未发现不一致」这类规则性表述**（没有实际分歧就不写任何谈分歧的句子） |
| `references/input-contract.md` | *Say it in the evidence scope* 段补同义规则（英文）：该行只报 path/depth/reason class，规则本身绝不进交付物；没分歧就没有分歧句 |
| `system-prompts/...-v0.15.md` | original-check 那条 bullet 同步补一句 |
| `evals/fact-check/check.py` | 新算子 `no_rule_metastatement`：句子同时点名库内一侧（`库内记录`/`库内抽取`/`库内字段`/`库内值`）与「一致/不一致」、且**通篇无数字** ⇒ FAIL（真实分歧必带双值 + ref，「无数字」正好切开元话语与结论） |
| `evals/fact-check/scenario-a.facts.json` | 新条目 `A-P8-no-rule-metastatement` → **40 条（39 fail + 1 warn）** |
| `evals/fact-check/mutations.py` | 新变异 **M24**（把改写版规则句写进报告）→ 实测 `flipped=['A-P2', 'A-P8']`；M23 现在带动 `['A-P2', 'A-P7', 'A-P8']` |

**这一条在**真产物**上也有效**：`check.py --run …r16-resume --scenario a` 直接报 `[FAIL] A-P8-no-rule-metastatement report states the rule instead of a finding: '未发现原文与库内记录在同一指标、同一口径上的数值不一致；'` ⇒ 不是只对着变异有牙。

**④ 新缺口（不是缺陷，是**合同没定死的口径**）：数值「符号 vs 幅度」写法随 run 漂移**

同一输入三次跑，数值写法不一致，而清单 `A-C4` / `A-C5` / `A-S9` 绑定的是**带符号**写法：

| run | 报告写法 | 图表数值 |
|---|---|---|
| R8（2026-09-16） | `−13.9` | `-13.9` / `-70.5` |
| R12 / R15 | `−13.9`（5 处，U+2212 减号） | `-13.9`（带符号） |
| **R16** | `下降 13.9%` / `降幅 13.9%`（全篇无符号，内部自洽） | `13.9`、`70.5`、`97.4`、`100.5`、`101.1`（全为正幅度） |

- 合同里**根本没有**关于符号/幅度的任何字（`grep -rn "同号\|负号\|降幅\|符号\|正值" skill/ system-prompts/` → 无命中），所以这是**模型每次自己选**的口径；
- 两种写法都自洽、都能读懂（`降幅 + 幅度` 与 `带符号值` 语义等价），但**同一输入不同 run 输出不同符号**这件事本身是交付一致性问题；
- 按「**不得为了迁就产物放宽清单**」的规矩，本轮**没有**去放宽 `A-C4/A-C5/A-S9`，也没有擅自把口径写死；记 **O26** 等口径拍板。
- `A-C16-hard-outcome-gap` 的 FAIL 同源：R16 写「**心血管结局**事件（如 MACE）」（表格里明确标注两侧「未报告」「未对齐」），而条目的正则只认 `硬结局|心血管事件` ⇒ 术语变体漏判，记 **O27**（与 O20 同类：清单绑定了某一次 run 的写法）。

**离线闸门（全部绿）**

```
python3 -m py_compile evals/fact-check/{check,mutations}.py            → PYC_OK
python3 evals/fact-check/mutations.py                                  → baseline a: 39 fail-severity items, all PASS
                                                                         arm a: flipped 39/39; never flipped []
                                                                         arm b: flipped 12/12; never flipped []
                                                                         GATE: PASS
python3 evals/runner-gate/verify-run-chain.py                          → GATE: PASS
python3 evals/fact-check/check.py --run …r16-resume --scenario a        → facts 32/39 warn 1/1（A-P8 在真产物上命中；A-C4/A-C5/A-S9/A-C16/A-T1 为写法口径问题，见 ④）
python3 tmp/pack15b.py + 逐文件 sha256 比对                             → dist 19 entries / 85,544 B
                                                                         sha256 a1b65809eb8b98c4e2a2cc223dc3f9c99e4e8c6fcef85b951c64e13e0f010938
                                                                         mismatch vs worktree: []
```

**发布状态（诚实标注）**：R16 跑的时候线上是 `prompt v1.6`（sha `0ae72c9302b3`）+ `skill v1.0.7`（dist `c55321ad4619`，即已含 `A-P7` 修复的模板）；
本轮又改了 4 个模板 + `input-contract.md` + **sys v0.15**（本地已重打成 `a1b65809eb8b` / 85,544 B；**第十一轮已再次重打并 in-place 发布为 `50477adfe102` / 86,084 B**）⇒ **prompt 与 skill 都需再次授权**才能发布（prompt 原地更新 v1.6、skill 原地更新 v1.0.7）。

**`MUT_RUN_A` 仍然不能换**：本跑带着 ③ 的规则句（`A-P8` FAIL）与 ④ 的写法口径问题（`A-C4/A-C5/A-S9` FAIL），整份清单下不干净；
`A-ATTR`（O19 假阳性）也还在。

### R15 — 2026-09-18，**L3 发布后 · 场景 A 同输入复跑**（与 R12 对照；发现并修掉一个我们自己的资产缺陷）

R14 用的是尿路上皮癌那对输入（L3 需要 `src=1` + PMC 全文），因此事实清单（场景 A 绑定 `24_1_30561610` + `24_1_36342163`）在 R14 上是 N/A。
本轮用**与 R12 完全相同的输入**再跑一次，才能做发布前后对照。

| 项 | 值 |
|---|---|
| 命令 | `toolsmith-publish run --web --tag r15-l3-scenario-a --prompt "解读这几个结果 24_1_30561610 24_1_36342163"` |
| thread / turn | `e0d198b3-22c8-43fd-82ef-cd1199644f20` / `bcc4e1ae-696a-4c37-b7fa-1b84648a6b70` |
| 终态 / 结局 | `completed`（durable `timing.completed_at`）/ `succeeded` |
| 墙钟 | 191.7 s server / 202.4 s polled（11 次轮询：`running`×10 → `idle`） |
| 调用 | **30 次尝试 = 29 返回 + 1 schema 被拒**：`execute`×15、`read_file`×9、`web_fetch`×2、`load_skill`×1、`params`×1、`present_artifact`×1；被拒的那次是 `web_fetch`（参数被 schema 拒 → 框架重发为新 call，无返回）。**注**：run 目录里的 `verification.md` 是 O25 修复前的渲染，那行印成「30 attempts = 30 returned + 1 schema-rejected」（自相矛盾，见 O25）；上表是修正后的口径，已用 `--resume` 重收验证 |
| token | thread in 113,908；turn in 1,881,535 / out 34,851 / reasoning 22,817；cache 96.7%；上下文 total 113,908（sys 22,835 / mcp 5,919 / tools 55,195 / skill 28,767） |
| 产物 | `output/report.md`、`output/citations.json`、`visualizations/endpoint-bar-1.json` |
| 断言 | **17/17 PASS（exit 0）**，含「部署端 == 本地」与「citations 键集/日期/`title`」 |
| 事实分 | `SCORE scenario=a facts 35/38 warn 1/1 -> FAIL`（R12 基线：`29/31`；**O19 修复后按 41 条清单回填 `37/40`**，剩 3 条是**真**模板泄漏，见 `### F2`）—— 清单同期由 31 → 38 条 fail 级，**两个 FAIL 都不是内容缺口**：`A-ATTR-misattribution`（已知打分器假阳性，O19）、`A-P7`（本轮新发现的**我们自己的缺陷**，见下） |
| 记录 | `~/.local/state/toolsmith-runs/20260918-092157-r15-l3-scenario-a/` |

**L3 的两条反向证据（比 PASS 更有信息量）**

1. **R6 命中但全文拿不到时，引用正确保持不变**：`24_1_30561610` 经 Europe PMC 取到 `PMC6933872`，**但该文非 OA、全文不可得** ——
   覆盖行写成「1 条经 Europe PMC 检索取得 PMC 记录号 PMC6933872，但该文非 OA、全文不可得，按库内摘要——即期刊摘要原文——核对」，
   `citations.json` 里两条 `link` 都**逐字节**等于库内 `full_article_link`（`…/30561610`、`…/36342163`），**没有出现任何构造链接**。
   ⇒ 白名单替换只在真取到全文时发生（R14 正例 / R15 反例，一对对照）。
2. **平台侧探针里那次 `PMC6933872 → 500`，在真 run 里得到解释**：不是 PMC 路由坏了，是**该记录非 OA** ⇒ 再次印证 O22/W2-d 的更正（「per record，不是全文路由不可用」）。

**本轮发现的缺陷（我们自己的资产）：模板规格句被照抄进交付报告**

`output/report.md` 的覆盖行渲染成了：

> …无因抓取受限而完全无法复核的记录。**原文优先于库内加工字段，不一致处同时写出原文值与库内记录值；不同披露版本（数据截止、人群或分析集不同）不作为库内错误。**

这**不是研究结论、也不是路径说明，而是模板写给模型的规格句**。成因：四个报告模板的第 5 行把原文优先规则写在 `**原文核对：** [...]`
括号**之外**，于是被当成正文照抄。离线清单 `A-P2` 忠实报 FAIL（该句含「库内记录」却没有 `{{ref_n}}`），但它的诊断信息（缺引用）指不到真正原因。

**修法（仓库资产，三处一起）**

1. **四个模板**（`cross-trial-report.md` / `mixed-comparison-report.md` / `same-trial-evolution-report.md` / `unified-evidence-report.md`）：
   把 `]` 之后的三句规格说明（原文优先 / 版本差异 / 全文引用落点）**移进 `[...]` 规格括号内**，与其余规格一致 —— 交付正文不再出现指令口吻。
2. **清单新增 `A-P7-no-template-spec-in-report`**（`shape` / `op_report_excludes_literals`）：报告正文不得逐字出现
   `原文优先于库内加工字段` / `不静默取一侧` / `库内记录值`（三条均为指令口吻，正常报告不会出现）。清单 38 → **39 条（38 fail + 1 warn）**。
   只加进场景 A：四个模板为两侧共用，但场景 B 的 arm 需要一个 B 形态样本才能给该条配对变异，样本到了再加。
3. **专属变异 `M23`**（把规格句写进报告）→ 实测 `flipped=['A-P2-divergence-shows-both', 'A-P7-no-template-spec-in-report']`：
   **隔离性符合预期**（M23 同时带动 A-P2，正因为 A-P2 的触发词是「库内记录」；两条各自仍有独立变异 M19 / M23）。

**离线闸门（全部绿）**

```
python3 -m py_compile evals/fact-check/{check,mutations}.py            → PYC_OK
python3 evals/fact-check/mutations.py                                  → arm a: flipped 38/38; never flipped []
                                                                         arm b: flipped 12/12; never flipped []
                                                                         GATE: PASS
python3 evals/runner-gate/verify-run-chain.py                          → GATE: PASS
python3 evals/fact-check/check.py --run …/20260918-092157-r15-… --scenario a
                                                                       → facts 35/38 warn 1/1（A-P7 如实指出泄漏）
python3 tmp/pack15b.py + 逐文件 sha256 比对                             → dist 19 entries / 84,991 B
                                                                         sha256 c55321ad46191f97d13ce52434535e3bc6f7ba64cf6dda00f0b029bad429934e
                                                                         mismatch vs worktree: []
```

**发布状态（诚实标注）**：`A-P7` 与模板修好的字节**尚未上线** —— 已发布的 skill `v1.0.7` 里仍是括号外的旧模板（即线上会复现这个泄漏）；
prompt `v1.6` 未受影响（sys 文件本轮没动）。两者都需要**再次授权**才能 `push-skill`（in-place）。

**顺带记录（库内数据问题）**：`24_1_39054491_1` 的 `clinical_result.blinded=['开放']` 而原文为 double-blind（见 `R14`），已并入 A10 待发清单。

**`MUT_RUN_A` 为什么不换成 R14/R15**：arm A 要求基线**在整份清单下全 PASS**。R15 的报告带着本轮泄漏（`A-P7` 判 FAIL），
R14 的输入不是场景 A（内容条目对不上）；且 R15 还带 `A-ATTR` 假阳性（O19，未修）。⇒ `seed_original_check` 这一步
**要等「模板修复上线后的场景 A 真 run」且 O19 定案**才能去掉。

### W6 — 2026-09-17，L3：分析面 = 可得最深载体 + 引用落点跟随分析深度（仓库先行，未发布）

**用户决策（2026-09-17，L1/L2/L3 定级）**：**先试 L3**，并当场驳掉了本台账先前的论证 ——
> 不应仅因「长短」判定不可比，因为科学事实不会因披露载体（PubMed 摘要 vs 全文）而改变。可改为在 **ref** 处
> 处理：若已获取全文并基于全文分析，则将引用指向**真正的全文链接**，而不是原来的 PubMed 摘要链接。

**收回一句错话。** 先前用「会议摘要类（本切片 55.6%）外部永久只有摘要级 ⇒ 深度不对等 ⇒ 不可比」论证 L2，
该论证**撤回**：深度决定「这条记录有多少内容可用」，不决定两个事实是否可比。深度不对等的正确处置是**逐条声明
分析深度**，而不是把记录判为不可比。O22 的 L1/L2/L3 建议表据此作废重写。

**规则改动（仓库资产，未发布会话）**

| 文件 | 改动 |
|---|---|
| `references/input-contract.md` | 新增 *The analysis surface is the deepest body you can obtain*（深度≠可比性；`src=1` 全文即分析面；其它类保持已测最深载体）；新增 *Facts that exist only in the full text are allowed — but they must carry their own label*（时点/分析集/人群 + 亚组/事后点名 + 版本差异不判库内错）；新增 *Citation link follows the analysis depth* 及 **C1/C2 引用 URL 白名单**；覆盖行须按**记录**说明分析深度 |
| `references/citation-and-ref.md` | `link` 逐字节规则的**唯一例外**：基于全文分析的记录 `link` 指向全文（C1 默认 / C2 备选），`title` 与 `paper_release_time_str` 不变；前置校验同步改写 |
| `SKILL.md` | 证据边界段：`src=1` 全文即分析面、全文独占事实须带标签、该记录引用指全文 |
| `system-prompts/...-v0.15.md` | 第 14/15/46/51/187/209 行同步（引用 JSON 例外、分析面、覆盖率深度、版本差异、前置清单） |
| `templates/*.md`（4 个报告模板） | `原文核对：` 槽位补「按记录的分析深度」+ 全文链接规则 + 版本差异不算库内错 |
| `evals/fact-check/check.py` | ① `citations_matches_record` 放宽：`link` ≠ 记录值时必须命中白名单全文 URL（否则仍判 FAIL）；② 新算子 `cite_link_is_deepest` |
| `evals/fact-check/scenario-a.facts.json` | 新条目 `A-P6-cite-link-is-deepest` → 共 **38 条（37 fail + 1 warn）** |
| `evals/fact-check/mutations.py` | 新变异 **M22**（归档全文 + 覆盖行已声明全文 + 引用仍指摘要页 → 只翻 `A-P6`，证明与 `A-P5` 隔离） |
| `evals/fact-check/README.md` | 条目数 38 / 变异 22 / 新算子表格行 / arm-a 明细 |

**引用该指哪个 URL——实测（run `R13` = `20260917-211711-pmclink`，3 URL 各一次 literal、无重试、不产报告）**

| 候选 | ok | 结果 |
|---|---|---|
| `https://pmc.ncbi.nlm.nih.gov/articles/PMC11270764/` | ❌ | reCAPTCHA 挑战页（115 字符）；**机房出口被拦，浏览器正常可通过** |
| `https://europepmc.org/article/MED/39054491` | ❌ | `403 Forbidden` |
| `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11270764/fullTextXML` | ✅ | 99,433 字符（本次真正读取的字节源） |

⇒ 定成 **C1 只写不取**（写进 `citations.json` 供读者点击；不作为抓取目标），**C2 = 本次实际读取的字节源**备选，
用 C2 时覆盖行要说明。取回链本身不变（R6→R7）。

**离线门禁（本次全绿）**

```
py_compile                          -> PYC_OK
evals/fact-check/mutations.py        -> arm a: flipped 37/37; never flipped []
                                       arm b: flipped 12/12; never flipped []
                                       GATE: PASS
evals/runner-gate/verify-run-chain.py-> GATE: PASS
check.py --run ...r12-fanout-dedup --scenario a -> 34/37 warn 1/1 FAIL
   （3 条 FAIL 均为既有挂账：A-P1 用的是未发布字节；A-T1/A-ATTR = O20/O19）
dist d5afb1f00320（84,994 B / 19 entries / mismatch vs worktree: []）
```

**验证状态**：本条目写就时 L3 还是**仓库先行**（用户当时明确「还不用发布ts」），无法用 `run` 证明平台装配后的行为。
**该缺口已由 `R14`（2026-09-18，发布后真跑）关闭**：17/17 断言 PASS，且逐项核实了引用落点替换、全文归档、
逐记录深度声明、以及「摘要里没有的数值确实进了报告」。
**仍未覆盖**：只压到 1 条全文记录 + 1 条无 PMCID 记录（样本窄）。

**我方仍可改的**：`A-P6` 只覆盖「归档了全文」的情形；若某记录全文取回后被丢弃未归档、而引用又改指全文，属
`A-P5`/`A-P6` 都管不到的盲区——等真 run 样本再决定是否加「引用指全文 ⇒ 必须有对应归档」的反向断言（不凭感觉加）。

### W5 — 2026-09-17，抓取预算收窄为「只有当库内没有原文时才抓」+ `src=1` 例外（PMC 全文）

**用户定调（2026-09-17）**：① 认可「默认优先库内 `abstract_text`，其余内容再努力」；② `src` 其实还有**其他类型**，
不要只对已知几类特化，一般规则是「**先 `abstract_text`，再为剩下的努力**」；③ **PubMed（`src=1`）即使有
`abstract_text`，也要尝试取 PMC 全文。**

**先证伪旧结论。** 先前把单条 `500/502` 读成「Europe PMC `fullTextXML` 不可用」（W2-d），据此把「原文」定成
摘要级。重新测：

| 探针 | 结果 |
|---|---|
| 本地（`/tmp/pmc_probe.py`，12 条 `src=1`） | 有 PMCID **4/12**；`{PMCID}/fullTextXML` **http=200**，63–100 KB JATS |
| 平台侧 `run --web`（`20260917-204927-webprobe-pmc`，7 URL） | R7 **4/5 成功**（PMC11270764 99,433 / PMC8449961 87,164 / PMC12265996 63,413 / PMC11736335 99,094 字符，均含 Results 分节与数值）；`PMC6933872` → `500` |
| 同 run 的 R6 | `EXT_ID:39054491` → `"pmcid": "PMC11270764"`；`EXT_ID:42477684` → `"inPMC": "N"`（无 pmcid） |
| 覆盖度（100 条 `src=1`） | 有 PMCID **56/100 = 56%**，且这些 100% `isOpenAccess=Y`/`inEPMC=Y` |

⇒ `500` 是**记录级**（该文未进 PMC/OA），不是路由失效；**结论更正并写进规则**。

**再证「库内 `abstract_text` 是否就是原文」**（`/tmp/verbatim_check.py`、`/tmp/vc2.py`，字符集归一后比较）：

| 类 | 样本 | 结果 |
|---|---|---|
| `src=1` PubMed vs Europe PMC | 4 条 | alnum 归一 **1.000 / 0.992 / 1.000 / 1.000**（残差只是分节标题大小写 `BACKGROUND:` vs `Background`） |
| `src=37` 会议 vs OpenAlex | 3 条 | 0.976 / 0.991（SITC 那条 alnum 0.45 已解释：库内尾部含 markdown 加粗与网页残留 `Back to top`，扣掉后 60 字符块命中 **50/56**，库内 ⊇ 原文） |
| `src=2` 登记结果 vs CT.gov v2 | 2 条 | 小数逐位命中 **102/102** 与 **72/72**（库内容量≈46 K vs API 65 K） |
| `src=49` 通稿 | 已知 | 线报日期首行 `(GLOBE NEWSWIRE) --` / `/PRNewswire/` 逐字在库内 |

⇒ 库内 `abstract_text` **不是「另一份加工产物」**；真正被加工的是 `study_results`/`summary` 这类结构化抽取。
所以「有 `abstract_text` 就不必抓」在多数类**成立**。

**其他来源类实测**（回答用户第 ② 点，不特化）：切片 4,106 行的 esid 中段分布 =
`37` 2281 / `1` 1478 / `49` 156 / uuid 遗留 84 / numeric 遗留 68 / `120` 21 / `187` 8 / `2` 7 / `245` 2 / `398` 1；
抽测未列出形态：uuid 遗留行（`ad0c754e…`）库内 = **PRNewswire 通稿原文** 8,542 字符；numeric 遗留行（`31628`）库内 =
**ESMO 2021 会议摘要原文** 14,111 字符（带 DOI）；`src=245` 库内空、无 `doi`/`pm_id`/link ⇒ 不可复核。

**改后的规则（写进仓库的版本）**

- 默认：**先读库内正文并据此核对报告，不花额度**；只有库内空/疑似截断，或该类有已知更全路由时才抓。
- **`src=1` 例外**：即使摘要已在手，也走 **R6**（Europe PMC search → `pmcid`）→ **R7**（`{PMCID}/fullTextXML`）；
  无 `pmcid` 或 `inPMC=N` 记原因类「无 PMCID / 非 OA」，**不计作抓取失败**。
- 预算：**每条 ≤1 次、`src=1` 允许 2 次（R6→R7 同一条链）**，整批上限 **40** 次 `web_fetch`。
- 覆盖行（`原文核对：`）：非抓取路径也算点名（`库内正文即原文摘要（src=1，未取 PMC 全文）`）；
  `src=1` 组必须写明 PMC 结果（`PMC11270764` / 无 PMCID / 非 OA）；归档了全文就**必须**出现 `PMC<号>` 或「全文」。
- 未列出类沿用同一原理：库内正文 → 路由键 → 自身 link 一次 → 记原因类。

| 改动文件 | 内容 |
|---|---|
| `skill/.../references/input-contract.md` | 新增「先读 `abstract_text`」实测段；来源类表加 `245`/uuid/numeric 行与「不抓」列；路由表加 **R6/R7**；封锁清单段更正 fullTextXML 误判；预算段改 1/2/40；覆盖行要求补 PMC 结果与非抓取路径示例 |
| `skill/.../SKILL.md` | Evidence boundary 段落写入「库内正文即原文」实测与 `src=1` PMC 例外 |
| `system-prompts/...-v0.15.md` | 步骤 3、`原文核对` 可见性条、Evidence boundary 段、链接白名单条（1→2 次 PMC 链 + 40 次上限） |
| `templates/*.md`（4 个） | `原文核对：` 槽位改成「默认库内即原文 + `src=1` 必写 PMC 结果」并加原因类「无 PMCID / 非 OA」 |
| `evals/fact-check/check.py` | `A-P4` 路由正则放宽（`PMC\d`/全文/库内正文）；**新增 `op_fulltext_fetch_is_named`** |
| `evals/fact-check/scenario-a.facts.json` | 新增 **`A-P5-fulltext-fetch-is-declared`** ⇒ 37 条（36 fail + 1 warn） |
| `evals/fact-check/mutations.py` | 新增 **M21**（归档 PMC 全文但覆盖行只写摘要路径）；基线补行改成「库内正文即摘要原文 / 无 PMCID」且回避 `PMC<号>`、全文 |
| `docs/evidence/source-link-accessibility-2026-09-17.json` | 新增 `pmc_fulltext_route`（路由 + 平台 7 URL 明细 + 56% 覆盖）、`library_text_is_the_original`（12 条逐条比对）、`slice_src_distribution`；`verdicts` 加更正条；`routes` 加 R6/R7 |

**离线闸门（本轮终态）**：`py_compile` → `PYC_OK`；`mutations.py` → **`arm a: flipped 36/36`**、
`arm b: flipped 12/12`、**`GATE: PASS`**；`check.py --run …r12-fanout-dedup --scenario a` →
`SCORE scenario=a facts 32/36 warn 1/1 -> FAIL`（`A-P1`/`A-P4`/`A-P5` 在未发布的旧产物上按预期 FAIL 或缺行）。

**相对 W3/W4 的关系**：W3 立「原文第一优先」，W4 把路由按来源类分化；**W5 收窄抓取触发条件**（从「每条 ≤1 次」
收到「只有库内没有原文时才抓」）并给 `src=1` 唯一例外。前两轮的禁止项与封锁清单**未被推翻**，只是不再是默认动作。

### W2 — 2026-09-17，`run --web` 的 **egress 探针**：路线 C（抓原文）可行性实测 → 变成技能规则

背景：A2 追问「字段是不是 agent 自己选」「想让它优先读 `abstract_text`（预存全文）、再访问 `full_article_link` 取全文，怎么约束」。
先用 `run --web`（W1 新增的能力）探清「到底能不能抓、能抓到什么」，再把结论写成规则（本次已落仓库，见 `### W3`）。

**W2-a/W2-b（前两个探针，只挑代表性 URL）**

| # | 探针 | URL | `web_fetch` 实测返回 | 结论 |
|---|---|---|---|---|
| W2-a | 人读页面 | `https://pubmed.ncbi.nlm.nih.gov/30561610` | `Cookies must be enabled … reload this page to continue.`（反爬拦截页，零内容） | 论文类**不可用** |
| W2-a | 人读页面 | `https://clinicaltrials.gov/study/NCT06618118?tab=results` | 站点骨架（`Show glossary` / `Study record managers: …`），零试验内容（正文靠 JS 渲染） | 登记平台类**不可用** |
| W2-b | 登记平台 API | `https://clinicaltrials.gov/api/v2/studies/NCT06618118` | **完整协议 JSON**（`protocolSection.identificationModule.nctId=NCT06618118`、`orgStudyIdInfo.id=M24-840`、`statusModule.overallStatus=TERMINATED`、申办方 AbbVie…，共 ~7.4 k 字符） | **可用** |
| W2-b | 文献 API | `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:30561610&resultType=core&format=json` | **Europe PMC JSON**：`pmcid=PMC6933872`、`abstractText`（带 `<h4>` 小标题的摘要全文）、`isOpenAccess="N"`、`hasPDF="Y"`、`citedByCount=110` | **可用** |
| W2-b | 题录 API | `https://api.crossref.org/works/10.1056/NEJMoa2211023` | 抓取成功，但返回体被平台落盘（`too large to keep inline`），对话里**未展开内容** | 可达（后续 W2-d 复核≈题录） |

- 两个探针共 2 次 run（`20260917-193854-webprobe-egress`、`20260917-194022-webprobe-api`），均 `enable_web=true`、断言全绿、`web_fetch` 分别 2 次 / 3 次。
- **附带事实**：沙箱自身无外网（模型试 `curl` → `Could not resolve host: pubmed.ncbi.nlm.nih.gov`、`HTTP_STATUS:000`），`web_fetch` 是**平台侧代抓**。

**W2-c（覆盖探针，11 个真实 URL，来自 1 个药名的 4,106 条结果里各域的代表链接）**

run `20260917-200934-webprobe-coverage`：**10/11 FAIL**，只有题录类成功。

- **更正 W2-a/b 的推断**：`web_fetch` 在**失败时确实带 HTTP 状态码文本**（如 businesswire / jitc.bmj.com 返回 `403 Forbidden`），只是**成功时不回状态码**；失败抓取计入「schema-rejected」而不是普通 tool 调用（所以「0 schema-rejected」不能单独当健康指标）。
- 逐域结果：`ascopubs / sciencedirect / annalsofoncology / jitc.bmj / businesswire` → `403`；`clinicaltrials.gov` 人读页 / `cslide / abstractsonline` → JS 骨架；`pubmed` → cookie 墙；`doi.org` 重定向类 → 抓取错误。
- 另一发现：写到 `output/` 的探针文件**会随 run 归档**（`output/fetch-probe.json` 在 `artifacts.zip` 里），而 `tool_results/` **不归档** → 证据落盘必须主动搬到 `output/` 或 `sources/`（后来专门验证，见 W2-e）。

**W2-d（端点覆盖探针，4 个 URL）** run `20260917-201202-webprobe-api2`：

| URL 类 | 结果 |
|---|---|
| `…/europepmc/webservices/rest/PMC6933872/fullTextXML` | ❌ `Server error '500 '`（两次尝试均失败）→ 当时的结论「全文 XML 路不通」**后被证明是记录级误判**（该 PMC 未进 PMC/OA），见 `### W5` |
| `https://api.openalex.org/works/doi:10.1093/eurheartj/ehy862` | ✅ `has_abstract=true`、`has_endpoint_numbers=true`，49,195 字符 |
| `https://api.openalex.org/works/doi:10.1200/JCO.2023.41.4_suppl.345`（会议摘要） | ✅ `has_abstract=true`、`has_endpoint_numbers=true`，31,147 字符 → **会议摘要有 DOI 也能拿到原文摘要** |
| `https://clinicaltrials.gov/api/v2/studies/NCT05419908` | ✅ 真原文（`protocolSection`）+ **结果数值**，322,763 字符 |

**W2-e（落盘归档探针）** run `20260917-201416-archive-scope`：写 `/workspace/{sources,notes,output}/probe.txt` 三个路径 → `artifacts.json` 三个都在，`artifacts.zip` 内 `['notes/probe.txt','output/probe.txt','sources/probe.txt']` ⇒ **工作区任意路径都随 run 归档**，`sources/` 可作为「抓到的原文」的审计落点。

**覆盖度测量**（药名切片 4,106 行，字段：`doi` / `pm_id` / `full_article_link` 内登记号）

- 有 `doi` 81.8%；有 `pm_id` 36.2%；链接/标题里有 NCT 0.6%；**至少有一条白名单路由的 83.0%**。
- 按 esid 中段（源 id）：`src=1`（论文）100% 可路由，`src=37` 82.2%，`src=49`（公司/微信）**0%**，裸 id 26.3%，`src=120` 4.8%。

**最终结论（W2 当时的版本）**：人读页面统一不可用，**API 端点可用且适用面 ~83%**；`fullTextXML` 曾被判不可用 ⇒
「原文」当时被当作**摘要级 / 登记平台级**。**该最后一点已在 `### W5` 更正：PMC 全文路由实测可用，且 `src=1` 已改为「即使有摘要也要尝试取全文」。**

### W3 — 2026-09-17，规则改为「原文第一优先级」（仓库已改，**等发布授权 + 真 run 才是 R14**）

**背景**：用户指出「esid 字段值是**加工过**的，可能出错，应以**原文**为第一优先级，库内字段次之」，并要求把
skill 里「禁止外部内容」的条款改掉。实测数据支持这个判断：`abstract_text` 中位数 33 KB、最大 1.9 MB，
且 77.4% 的 CT.gov 行里它是**结构化结果 JSON 而不是文字摘要**（见 `docs/evidence/*.json`）。

**改了哪些行（全部为仓库资产，尚未发布）**

| 文件 | 改动 |
|---|---|
| `skill/.../references/input-contract.md` | 新增 `### Evidence source priority: the original source comes first`：白名单路由表 R2/R3/R4/R5、预算（每记录 1 次 / 整批 1 轮 / 上限 20 次）、失败处理、分歧固定写法 `原文 …；库内记录 …{{ref_n}}`、「原文缺失 ≠ 库内错」、`原文核对：` 覆盖行、版权闸门 |
| `skill/.../SKILL.md` | 证据段：把「clinical evidence」改为「processed extracts」，删掉「Do not retrieve external facts or URLs」的全面禁止，改为「只走白名单模板、原文优先、冲突写双值」 |
| `skill/.../references/input-and-extraction.md` | 同上口径（去「never retrieve … a missing URL」的绝对禁止） |
| `skill/.../references/citation-and-ref.md` | 说明 `doi`/`pm_id`/登记号仅作路由键，题录字段本身仍不得产生临床事实 |
| `system-prompts/…-v0.15.md` | ①line 50 证据定义改为「加工抽取 + 原文复核」；②line 53 澄清「复核**已选**记录不算引入未选内容」；③line 209 `no URL was retrieved` 改为「只允许白名单模板」；④新增「原文核对必须可见」条：`原文核对：` 行 + 分歧双值 + 未复核点名 |
| `templates/*.md`（unified / cross-trial / mixed / same-trial） | 证据范围（or 比较口径）块加 `原文核对：` 槽位；unified §6.3 差异段加双值写法 |
| `evals/fact-check/` | 新增 `A-P1/P2/P3`（覆盖率行 / 分歧双值 / 禁长段照抄）与 `sent_if` kind、`no_verbatim_copy` op；`mutations.py` 加 M17–M19（含「基线补一行」的说明与实现） |

**离线闸门（已跑）**：`py_compile` OK；`mutations.py` → `arm a: flipped 34/34`、`arm b: 12/12`、`GATE: PASS`；
`check.py --scenario a` 对 R12（旧部署字节）→ `31/34`（新三项按预期 FAIL，属契约新增）。

**待办**：发布授权 → `publish` → `run --web --prompt "解读这几个结果 24_1_30561610 24_1_36342163"` → `R13`
（预期 17/17 断言 + `facts 34/34`；若抓取命中原文，`sources/` 应有落盘、正文应有 `原文核对：` 行）。

### W4 — 2026-09-17，原文优先规则**按来源类细化**（用户质疑「你不考虑所有源的 link 可访问性吗？」）

**背景**：W3 把「原文第一优先级」写成一条**扁平**规则——一张路由表 + 一条「不许抓 link 页」的禁令。
用户质疑：不同来源的 link 可访问性并不一样，一刀切既会浪费调用（对本来就不可达的站点反复抓），
也会漏掉本来可复核的记录。本轮按 **esid 中段 = 摄取来源 id** 把规则改成**按来源类分化**。

**新增实测（只读，零线上改动；产物 `docs/evidence/source-link-accessibility-2026-09-17.json`）**

| 来源类（src） | 库内 `abstract_text` 是什么 | 外部原文可达性（实测） | 首选路由 |
|---|---|---|---|
| `1` PubMed | 期刊摘要正文（中位 1,812 字符） | 可达（PMID 路由 1/1） | R4 → R3 |
| `2` / `187` CT.gov | 登记平台**结构化结果 JSON**（`187` 实测 602/602 空） | 可达（CT.gov JSON API 323 K 字符，含端点数值） | R2 |
| `37` 会议摘要 | 会议摘要正文（中位 2,786） | 82.2% 有 DOI ⇒ 可达；**会议站点本身全封**（asco / cslide / abstractsonline / annalsofoncology） | R3 |
| `49` 新闻稿 | **通稿正文逐字**（`(GLOBE NEWSWIRE) --` / `/PRNewswire/` dateline 在文内） | 分裂：prnewswire ✅ / businesswire ❌403 / globenewswire ❌ / 微信公众号 ❌壳 | **不需外部抓取** |
| `120` 人工补录 | 实测 100% 空 | 仅 4.8% 有 DOI；公司域页 ✅、IR 静态文件 ❌ | R3（有 DOI）或 link 1 次 |
| `398` SEC | 未取到有效样本 | EDGAR `403`；`data.sec.gov/*.json` 只有题录**无临床数值** | 不可复核 ⇒ 记原因类 |
| 无中段 | CT.gov 结构化结果 JSON（38.1% 空） | 26.3% 有路由键 | R2 / R3 |

- 32 条实测 URL：**11 可达 / 21 不可达**（含 4 条路由 API）。同主机可能「人类页不可达、API 可达」：
  `clinicaltrials.gov/study/…` JS 壳 vs `clinicaltrials.gov/api/v2/…` 正常；`pubmed.ncbi.nlm.nih.gov` cookie 墙 vs
  Europe PMC REST 正常；`www.sec.gov` 403 vs `data.sec.gov` JSON 可达（仅题录）⇒ **封锁清单是 host+页面类，不是主机名**。
- 结论：**可达性按来源类判断**；把「link 页一律禁抓」换成「封锁清单 + 每记录最多 1 次、仅在无路由键或主机可用/未知时」。

**改了哪些行（仓库资产，仍未发布）**

| 文件 | 改动 |
|---|---|
| `references/input-contract.md` | 原文优先章新增「先认来源类」表（src → 库内 `abstract_text` 性质 / 可达性 / 首选路由）与「按主机分化的抓取策略」（封锁清单 16 个主机 + 可用类 + 每记录 1 次 + `src=49` 免抓）；路由表补足 R3 实测 5/6、R2 2/2；覆盖行要求**逐组点名路由与来源类**并给示例 |
| `SKILL.md` | 证据段写明按 esid 中段选路（`49` 库内即原文、`398` 不可复核），把「绝不抓 link 页」换成「白名单路由 + 每记录最多 1 次自身 link（仅无路由键或主机可用/未知）」 |
| `system-prompts/…-v0.15.md` | ①line 15 步骤 3 按来源类选路；②line 46 覆盖行要求点名路由 + 来源类、结构性不可达要按类说明；③line 51 证据段写来源类分流与封锁清单；④line 209 可见性检查改为「路由模板 + 每记录最多 1 次自身 link」 |
| `templates/*.md`（4 个） | `原文核对：` 槽位说明改为**逐条按来源类标注路径**（含 `src=49` 库内即原文、`src=398` 不可复核） |
| `evals/fact-check/` | 新增 `A-P4-original-check-names-route-and-class`（op `original_check_names_class`）与 `M20`；`SEED_ORIGINAL_CHECK` 改为同时点名路径与来源类（仍避开 `库内记录`）；README 计数与变异清单同步 |
| `docs/evidence/source-link-accessibility-2026-09-17.json` | 新增：按来源类的路由键占比 / 库内文本性质 / 32 条 URL 实测 / 主机封锁与可用清单 / 注意事项 |

**离线闸门（已跑，本机）**：`py_compile check.py mutations.py` OK；`mutations.py` →
`arm a: flipped 35/35`（20 个变异，含 M20「覆盖行空壳」）、`arm b: flipped 12/12`、**`GATE: PASS`**；
`check.py --run …/20260917-191502-r12-fanout-dedup --scenario a` → `facts 32/35`（`A-P1` 按预期 FAIL 于旧部署字节；
`A-P4` 在缺行时自动让位给 `A-P1`，不重复计分）。

**为什么加 `A-P4`**：`A-P1` 只查「有一行 + 有数字」，`原文核对：2/2 条已复核。` 这种空壳能全过；
而本轮实测恰恰说明「是新闻稿（库内即原文、无需抓）」与「是 SEC 备案（不可复核）」必须被写出来，
否则下游分不清「没复核」和「不需要复核」。`M20` 专门构造这个空壳，证明这条规则有牙。

**待办**：发布授权 → `publish` → `run --web --prompt "解读这几个结果 24_1_30561610 24_1_36342163"` → `R13`
（预期 17/17 断言 + `facts 35/35`；正文应带 `原文核对：` 行，若命中原文则 `/workspace/sources/` 有落盘）。W3 的计数
（34/34、`facts 34/34`）以本节为最新。

### W1 — 2026-09-17，runner 新增 `run --web`（只改 runner，零线上改动；台账 O18）

**背景**：平台把 Web 工具挂在**「项目能力 + 请求级 `enable_web`」两道开关**上（`capabilities/web.py:140`
`should_activate_web_tool`）。本项目能力已开（`GET /api/agent/info?…&enable_web=true` 注入 `## Web Tools`），
但 `run` 的 `post_turn` **硬编码 `enable_web: False`** ⇒ 无论如何都跑不到「联网状态」，也就无法验证
「联网时 skill 会怎样」（CT.gov 路线 C 的前置条件）。

**改动**（`~/.local/bin/toolsmith-publish`，1805 → 1822 行；改前备份
`~/.local/state/toolsmith-publish/toolsmith-publish.v4.bak`，92,618 B，`f7fc69be…`）：新增全局 `--web`
（`GLOBALS` + `add_global_args`）→ `post_turn` body 改成 `enable_web: bool(a.web)`；`run.json` 记 `enable_web`；
`verification.md` 头部记 `web tools: enabled/disabled`；`--resume` 时明说该开关对已 POST 的 turn 无效。

**验证**：

| 闸门 | 命令 | 结果 |
|---|---|---|
| 语法 | `python3 -m py_compile` | `PYC_OK` |
| 零网络回归 | `python3 evals/runner-gate/verify-run-chain.py` | **`GATE: PASS` / RC=0**（11 个录制 run：5 个 v1 逐条相等，其余按预期 SKIP，含 4 个 web 探针 run） |
| 正向真跑（开） | `run --no-assert --tag webflag-on --web --prompt "用 web_fetch 打开 https://example.com …"` | thread `f11aeb37-…` / turn `48b7797f-…`；打印 `web=ON`；**`web_fetch`×1** 取回正文并逐字回报；`outcome=succeeded`，server 5.7 s |
| 负向对照（关） | 同一 prompt，不带 `--web` | thread `da5fc11c-…` / turn `bf38ed63-…`；**0 次工具调用**、`tools=0` tokens，模型答「我没有 web_fetch 工具」 |

run 目录：`~/.local/state/toolsmith-runs/20260917-141451-webflag-on`、`20260917-141634-webflag-off`
（两份 `run.json` 的 `"enable_web"` 分别为 `true` / `false`，可复核）。

**边界（避免误用）**：`--web` 只影响 **`run` 新建 turn 的请求体**；`--resume` 只重采集、不 POST ⇒ 开关无效（会打印提示）；
`deps` / `status` / `tools` / `instructions` 的 `enable_web` 语义未动（它们只查目录）。它**不改任何已发布资产**，
只是让本机验证器能复现「联网状态」。

**对本项目的影响**：CT.gov 路线 C（运行期用 `web_fetch` 拉官方全量 JSON）**现在本机可验证了** —— 政策/引用口径
一旦拍板，就能用 `run --web` 测「skill 在联网下是否照规矩引用」；当前仍 parked 等产品。

## 3. 我们自己能改的

| # | 现象（证据） | 改法 | 状态 |
|---|---|---|---|
| O1 | `deps` 基线漏掉 `read_file`：R1/R2 实际调用 21+9 次，但基线内置工具 10 个里没有它 —— `collect_deps` 只做**文档文本匹配**，而我们的 sys/skill 从不提 `read_file` | `toolsmith-publish` 的内置工具指纹改为取**项目实际启用的工具集**（`GET /api/agent/info?project_id=…` → `tools`，16 个），不再靠文本命中；顺带修了漂移输出把 `NEW builtin` 打成 `NEW buil` 的截断 | **已落地**（基线 16 个，`deps` 复跑 exit 0） |
| O2 | digest 翻页：R1 里 **12/50** 次调用在按 offset 读同一个 105 KB / 510 行 `digest.txt`（offset 60→499，limit 30–60） | sys `Step discipline` #1 收尾加一句：**每个 digest 文件要能一次读完**（目标 ≤ ~300 行 / 几十 KB）；超了就拆成「每记录一文件」或「index + 每记录文件」，**不要对单个大 digest 反复 offset 读** | **已落地**（sys v0.15，2026-09-14） |
| O3 | 发明字段：R1 出现 `clinical_result.line_count` → `INVALID_INPUT`（原文见平台 P3），靠重试自愈 | 字段名的**运行期权威 = params 工具自身的 `selected_fields` 参数描述**；逐字复制，**禁止发明**；概念确无字段时取**最接近的真实字段**（组/臂数 → `clinical_result.group_count`，线数 → `clinical_result.therapy_line_cn`/`_en`）或**留空并记「未报告」**。`docs/params-tool-schema.md` 只是维护者镜像（不在部署端包内），明确禁止规划运行期去读它。落到 `SKILL.md`、`references/input-contract.md`、`references/entity-inline-reference.md`、sys | **已落地**（2026-09-14） |
| O4 | 正文句子级返工：R1 的 19 次 `execute` 里 8 次是 `s.replace()` **就地改写 `build_report.py` 里的模板字面量**，另有 3 次 `edit_file`；都是内容打磨（不是规则返工） | 暂不改规则。若要压：把「正文与渲染分离」（正文放 md/data，脚本只做 token 替换 + 断言）写成硬规则 | **待样本**（再攒 3–5 次运行） |
| O5 | 小样本不便宜：1 个 esid 也要 21 次调用 / 173 s / 26k reasoning tokens（14 个 esid 是 50 次 / 299 s / 32k）；成本由"读 skill + 套模板"主导，不随结果数线性 | 暂不改。若体感贵，可考虑给"单结果解读"一条更轻的模板路径 | **待样本** |
| O6 | 台账里写的本地产物路径（`/tmp/toolsmith-runs/...`）全部失效：`/tmp` 被系统清空，早期的 `R1/R2` 产物离线后无法复核（只剩平台侧 thread id 能回捞） | `toolsmith-publish` 的 `WORK` / `RUNS` 改到 `~/.local/state/toolsmith-publish` 与 `~/.local/state/toolsmith-runs`（不用 `/tmp`）；`run --out` 仍可覆盖 | **已落地**（2026-09-14，R3 起生效） |
| O7 | 无效 esid 导致空转：R3 里我把 `24_1_45608045`（库中无数据）和有效 esid 一起给，模型对**同一个输入换了 8 种写法**（`extra_esids:["24_1_45608045"]` → `["45608045"]` → 改 `trial_id:"NCT02729025"` …）共 **8 次** params 调用，最后仍产出 `ref_2` 为**全空**（`title`/`link`/`paper_release_time_str` 均 `""`），而 13 项断言全过（断言只管「有对应条目」，不管条目是否为空） | 改法：① 一次批量拉取 + **至多一次**确认，同一 esid 连续空即停手，**不许换写法反复重试**（已写入 sys / `input-contract.md` / `citation-and-ref.md` / `SKILL.md`）；② 未返回的 esid **不分配 `{{ref_n}}`、不写 citation key**，**禁止空 `title` 条目**，keys 在「实际返回的记录」上连续；③ 可用记录 < 2 → **拒绝产出**并回 chat 说明（新增 `run --expect refusal` 断言框）；④ 断言第 11 项加「`title` 非空」 | **已落地**（2026-09-14；证据：R3 旧行为 8 次重试 + 空壳引用 vs **R5/R6 同输入 2 次调用、零产物、回复点名说明**；R7 两个条目均有真实标题/日期） |
| O9 | **旧 `parse_stream()` 漏事件类型 → 假 PASS**：R7（a2 真跑）里模型实际发 **41** 次调用，其中 1 次把 `execute` 的 `shell_command` 写成 `command` 被 schema 拒、框架重新提示后重发；SSE 计数 `tool-input-start=41 / tool-input-available=40 / tool-input-error=1`，而 v1 只认后两者 → 台账记成「40 次调用、0 工具报错」，第 10 项断言「无工具报错」是**假绿**（同类问题也会让真报错漏判） | 工具侧：调用链改从 `/debug/history` 的持久化消息重建（`tool_chain_from_history()`），被拒调用（有匹配 `retry-prompt` 的 `tool_call_id`）单列 `rejected` 并给 WARN/INFO、不计入 `errors`；新增「每个 tool-call 要么有 return 要么被 schema 拒」断言。`parse_stream()` 降级为 legacy 对账 oracle | **已落地**（2026-09-16；证据：5 run 重放门禁 PASS，其中 a2 的 41=40+1 被正确拆出） |
| O8 | 同输入重复确认：R5 里规则已写「至多一次确认」，实际 params 调了 3 次——第 2、3 次**参数完全相同**（同一个 `24_1_45608045` 再查一遍） | `input-contract.md` + sys 加一句：**参数不变的确认不得重复**（同一 esid + 同一 `selected_fields` 空两次就是真的不在）；同时明确「不同用途的第二次调用（如补字段）不是确认、仍允许」，以免误伤 R4 那种合理的补字段调用 | **已落地**（2026-09-14；证据：R6 同输入 params **恰好 2 次**） |
| O10 | **量具自己的两处错**（R8 真跑时暴露）：① `verification` 里 `[PASS] no tool errors` **打印两遍**（一处遗留的重复 `add()`）；② `wall clock: … server (permanent)` 把 `/timing.turns[].latency_ms` 当永久值，而它其实是**现算活计数**（同一 turn 204 s → 350 s 还在涨，见 P7） → 台账里可能记下一个偏小的服务端耗时 | ① 删掉重复断言；② `turn_completed_ms()` 改为**优先 `completed_at - started_at`**，无 `completed_at` 时回退 `latency_ms` 并在输出里明写「live `/timing` counter … keeps rising」 | **已落地**（2026-09-16，`py_compile` + `--resume` 复测：新文案与 16 项断言均正常） |
| O11 | **事实清单打分器自身的三处缺陷**（全部由负向对照暴露，否则会带着假绿上路）：① 用 `edit` 插入 `op_artifact_absent` 时**误删了 `def op_glob_count` 的头行** → `NameError`；② 归因规则原本按**整行**判（report 行内同时出现 A/B 两条记录的元素），把 B 的药名写成 A 的药**逃过检查**（变异 M06）；③ 改成句粒度后又误伤**表格行**——表格行的引注按单元格分布，按 `；` 切句会把「引注在最后一格」的数值单元格判成无人认领（R8 报告里一行对比表即触发假 FAIL） | ① 补回 def 并立规矩：插入后立即 `py_compile`；② 归因单元改为「散文按 `。；` 切句 / 表格行按 `|` 切单元格，无引注的单元格继承该行引注」；③ 另加 `line` 类条目 `A-T1-title-names-both` 补上「标题无引注、不受归因规则保护」这个缺口 | **已落地**（2026-09-16；判据：`mutations.py` 双盲 GATE PASS，A 30/30 / B 12/12） |
| O12 | **打分器把括号内的 `；` 当句边界**：`（-70.5% 至 -101.1%，第 36 周{{ref_2}}；对应 -13.9%，第 16 周{{ref_1}}）` 被切成两半，每半只剩一条记录的引注 → **R9 那份正确的报告被判 `A-ATTR-misattribution` 假 FAIL（29/30）** | `sentences()` 改为**只在括号/方括号深度 0 处切句**（`（(［[【` / `）)］]】` 计数）；并在 `evals/fact-check/README.md` 写明该规则 | **已落地**（2026-09-16；判据：R8 仍 30/30、R9 由 29/30 → 30/30、`mutations.py` GATE 仍 PASS） |
| O13 | **变异 harness 把字符串当正则**：`sub()` 用 `re.subn`，而 `| 试验 B {{ref_2}} |` 里的 `|` 是**空分支交替** → 一次替换 **7923 处**，把整份报告改烂，却仍报“变异成功”（翻转 19 条 item，掩盖了真正的定位） | 新增 `sub_lit()`（`re.escape` + `count=1`）用于含 `|`/`{}` 的字面量；`sub()` 加**替换次数上限**断言 `n <= max(200, len(text)//200)` —— 这类“匹配到到处都是”的静默灾难直接 fail-loud | **已落地**（2026-09-16；判据：M15 从“翻转 19 条”收敛为“只翻 `A-ATTR`”，GATE PASS） |
| O14 | **`run` 的 `not_started` 判定实际从未生效**：取的是 `me(c)['id']`，而 `/api/auth/me` 返回的是 **`user_id`** ⇒ `uid` 恒为 `None` ⇒ `/thread-turns/validate` **根本没被调用** ⇒ `in_db` 永为 `None` ⇒ **任何“状态未知”的 turn 都被无条件报成 `not_started`（exit 4，“the POST never landed”）**。只读实测：真实已完成 turn + 正确 `user_id` → `{"exist": true}`；缺参 → **HTTP 422**；传字串 `None` → `{"exist": false}`（假阴性） | 改 `me(c).get("user_id") or .get("id")`；并在 validate 说 `exist=true` 时先看 `/timing` 的 `completed_at`：有值就直接按已结束收尾（走完断言），不捛到 `--timeout`（默认 2400 s）才报 `timeout` | **已落地**（2026-09-16，用户先点头后才改；改前备份 `toolsmith-publish.v2.bak`，85,409 B）→ R10 |
| O15 | **`--resume` 不带 `--out` 就地重采集，把原 run 目录的 `verification.md` / `run.json` 覆盖掉**（`Checks` 段被抹空）—— R8 那份记录就是这么丢的；而原 run 目录常是那次验证**唯一**的证据副本 | `--resume` 默认写**新目录**（`<stamp>-resume-<tag>`，并打印原目录位置）；只有显式 `--out` 才写指定目录（已存在记录时先 warning）；同时给 resume 目录补写自描述的 `run.json` + `prompt.txt` | **已落地**（2026-09-16）→ R10 的 T6/T7 |
| O16 | **runner 的图表类断言在「0 图」时全部平凡通过**（R11 产物只有 `report.md` + `citations.json`，3 条图表断言照旧 PASS：「0 tags / 0 files」「no chart」）——断言本身没错（有没有图取决于输入，不能无条件要求），但意味着**“该出的图没出”这件事 runner 看不见**；R11 的事实分里 3 个 FAIL 正是这一类 | **定案：不改 runner**。`run` 是**通用**入口，不知道场景，无条件要求出图会把合法场景判死；这类“该不该出一张定量主图”的判定交给**离线事实清单**（`evals/fact-check/` 的 `A-S2/S8/S9`），清单知道场景、也知道规则文本 | **定案保留**（2026-09-17；由 R11 暴露，非缺陷） |
| O17 | **清单条目 `A-S2-chart-set` 是「基线污染」**（期望从 R8 产物倒推，而不是从规则文本推）·**已按用户批准修正**：它期望场景 A 必出 `endpoint-bar-1.json`，但 `chart-templates.md:91` 的规则是「定量主图**可选**，需 ≥2 条入选结果给出**同一终点、同一口径（可明确对齐的时点）**的纯数值」，而场景 A 的两条记录是**第 16 周 vs 第 36 周**——R11 据此明确写了「不具备绘图条件——本报告不输出图表」并给了理由；R8（同一输入）反而画了图。**这就是「清单必须先于产物撰写」要防的那个坑** | **已落地**（2026-09-17）：① `A-S2` 改为 `chart_set_allowed`（文件名合法 + 禁 timeline（跨试验前置条件不成立）+ 定量图 ≤1 张；**空集合不算违规**）；② 新增 **`A-S2b-chart-or-reason`**：没有定量图时正文必须**明确写出不出图**（`required_groups`）且给 ≥1 条实质理由（`supporting_groups`）——只查支持理由不够（跨试验报告天然写「跨试验」「时点不同」，删图不说话也能过）；③ `A-S8/A-S9` 加 `"optional_when_absent": true`（文件在则硬断言封套/数值，不在则 PASS 并指向 A-S2b）；④ `A-C12` pattern `2 ?条` → **`2 ?(条\|项)`**；⑤ 新增变异 **`M16 drop-chart-silent`** | **已落地**（2026-09-17；判据：R8/R9 新基线 **31/31**、R11 由 25/30 → **30/31**（只剩 `A-C6`）、B 仍 12/12、`mutations.py` arm A **16** 个变异覆盖 31/31 + arm B 11 个覆盖 12/12 → **GATE PASS**；正向对照「删图 + 写明原因」手动跑 → 31/31 PASS） |
| O18 | **`run` 无法进入「联网状态」**：`post_turn` 把请求级 `enable_web` 硬编码为 `False`，而平台只在「项目能力 + 请求级开关」双开时才注入 `web_search`/`web_fetch`（`capabilities/web.py:140`）—— 项目能力本项目已开（`/api/agent/info?…&enable_web=true` 注入 `## Web Tools`），所以唯一的闸门正好是本机验证器碰不到的那一个；后果是无法用 `run` 验证「联网时 skill 行为」（路线 C 的前置条件），之前只能靠临时探针脚本 `/tmp/webtest.py` | `run` 新增全局 `--web`（写进请求体 `enable_web`，`run.json` 与 `verification.md` 均留痕；`--resume` 打印无效提示），CLI docstring 与 plan doc 同步 | **已落地**（2026-09-17，用户先点头后才改；改前备份 `.v4.bak`，92,618 B）→ 证据见 **W1** |
| O19 | **打分器在「一句多 marker」上假阳性**：R12 报告里 `… NCT02729025 的机制终点未达显著{{ref_1}}，其结论不能外推至 OCEAN(a)-DOSE{{ref_2}}` 被判 `A-ATTR-misattribution` FAIL（`'NCT02729025' in unit citing ['ref_2']`）——而 sys 明文允许「一句确实混用多来源时可挂多个 marker」（`system-prompts/…-v0.15.md:203`）。判分器只看「token 的 owner 是否等于该 unit 的**唯一** ref」，与契约文本冲突 | 方案改过：**不是**按「refs 集合大小」放松（实测 R12/R15 的假阳性 unit 都只挂**一个** marker），而是按「**这条 unit 在讲哪条记录**」放松 —— `pairs` 标 `"subject": true` 的 token＝记录身份证（药名 + 登记号）；**身份对**在「unit 同时点了引注记录自己的身份证」时豁免（比较句/排除句），**数值对永不豁免**（M27 证明），`M06`/`M15` 照旧翻（豁免没把牙拔掉）。另加假阳性回归对照 `N25`/`N27` + `arm()` 的「必须保持绿」断言 | **已修**（2026-09-18 用户「O19-20 都可以改」）→ 证据 **F2**；R12 由 `37/40` 升到 `39/40`、R15 `36→37/40`、R17 `39→40/40` |
| O20 | **清单条目 `A-T1-title-names-both` 期望过窄**：R12 的 H1 是主题式标题「Lp(a) 升高人群降 Lp(a) 治疗：跨试验对比报告」→ FAIL；但两个药名都在正文锚点里（`A-C1/C2` PASS）。该条的理由是「标题无引注、不受归因保护」，真正要防的是**两药混成一个**；而「H1 必须点名两个药」是从 R8 那份标题倒推的写法偏好（与 O17 同类基线污染） | 落地为 `kind: shape` / `op: title_scope`，条目改名 `A-T1-title-identifies-scope`：两个 subject 都点 ⇒ PASS；一个都不点但命中 `theme_all`（人群 + 对比标记）⇒ PASS；**只点一个 ⇒ FAIL**；两者都不占 ⇒ FAIL。专属变异 `M26`（`# 结果对比报告`）与 `M06`（药名换另一个）双双证明有牙，假阳性回归对照 `N26`（主题式标题）保持绿 | **已修**（2026-09-18 用户授权；R12/R15/R16/R17 四份产物证据齐）→ 证据 **F2**。**后续**：arm A 基线已重指 R17、`seed_original_check` 删除（清单/打分器未动）→ 证据 **F3** |
| O21 | **A2 追问的实现路径（分诊完成：政策已放开，规则已改仓库，等发布）**：① **`source_full_link` 字段不存在** —— 那是 v0.11 附件契约的名字（`source_url`/`source_full_text`），现行 params 工具里只有 `clinical_result.full_article_link`（描述「临床结果论文的URL」）；写错名字的后果是整次取数 `INVALID_INPUT`。② 原计划「优先 `abstract_text` → 再访问 `full_article_link`」与**旧** sys:50「citation metadata only」冲突，且对人类可读页面实测不可用（W2-a/W2-c：pubmed cookie 墙、CT.gov JS 骨架、5 个出版域 403）。③ 只有 **API 端点**可用（W2-b/d：CT.gov v2 真原文含结果数值、OpenAlex 按 DOI 拿到原文摘要含会议摘要、Europe PMC 按 pmid 拿摘要；`fullTextXML` 当时误判为 500/不可用，已在 `### W5` 更正为「记录级、路由可用」），而 API 端点必须由 `pm_id`/`doi`/登记号**拼 URL**，与「URL 只逐字用、不得构造」冲突 ⇒ 必须开白名单模板。三个开关已定：**(a) 政策 = 放开**（用户 2026-09-17：字段值是加工的、可能出错，原文第一优先级）；**(b) 可追溯性承载 = 报告正文**（`citations.json` 保持严格 3 键、不加键，因此不破 `A-S4`）；**(c) 冲突/降级语义 = 原文为准 + 分歧必须双值写明 + 抓不到必须点名原因类**。 | 规则已写入仓库（清单见 `### W3`），开白名单模板 R2/R3/R4/R5；**并按来源类细化**（`### W4`：`1` PubMed / `2`/`187` CT.gov / `37` 会议 / `49` 新闻稿=库内即原文 / `120` 补录 / `398` SEC 不可复核），把「link 页一律禁抓」改成「16 主机封锁清单 + 每记录最多 1 次自身 link（仅无路由键或主机可用/未知）」。**第四轮（`### W5`）再收窄**：默认改为「**先读库内 `abstract_text`——实测多数类它就是原文**（期刊摘要 alnum 1.000/0.992、会议摘要 0.991/0.976、登记结果小数 102/102、通稿带线报日期），所以默认不抓」；唯一例外 **`src=1` PubMed 即使有摘要也走 `R6`→`R7` 取 PMC 全文**（100 条抽样 56% 有 PMCID；平台侧 R7 4/5 成功、63–99 K JATS 全文；无 PMCID/非 OA 记原因类不计失败）；预算改「每条 ≤1、`src=1` ≤2、整批 ≤40」；覆盖行必须写 PMC 结果，归档全文就必须点名 `PMC<号>`/「全文」（新断言 `A-P5` + M21 证明有牙） | **已定案 → 待发布授权 + 真 run（R13）**（2026-09-17；证据 W2、W3、W4、W5 + 字段实测） |

| O22 | **全文深度分层 → 已定级 L3（2026-09-17）**：用户提问「字段值基于摘要生成，PMC 能取到的能不能直接读全文」⇒ 实测成立：3 篇 R6 返回 pmcid 的记录，全文独立数值 **334 / 334 / 249**，其中 **92% / 88% / 99%** 不在摘要里，且 `PFS`/`DoR`/`HR`/`TTR`/亚组/`Grade 3` 等维度摘要根本不出现。**用户选 L3 并驳掉「长短即不可比」**：科学事实不因披露载体改变 ⇒ 规则改为「分析面 = 可得最深载体」，且**基于全文分析的记录其引用 `link` 指向全文**（C1 `pmc.ncbi.nlm.nih.gov/articles/{PMCID}/` 只写不取 / C2 ebi REST fullTextXML 为实际读取源），覆盖行须按记录声明深度。新断言 `A-P6-cite-link-is-deepest`（M22 证明可翻）。证据：`docs/evidence/source-link-accessibility-2026-09-17.json` 的 `l3_decision` / `pmc_fulltext_information_gain`。 | W6 | 仓库已改，**未发布** | **待用户发布授权**（发布后跑 R14 才算已验证） |
| O23 | **runner 韧性缺口：次要端点抖一下就把整次验证毁掉**（2026-09-18 实测发现）：`run` 收集阶段顺序 GET `/timing`、`/usage`、`/info`、`/artifacts`、`/limits`、`/messages`，其中 `/usage` 一次 `urlopen` 超时（`Errno 110`）触发 `die()` ⇒ 进程直接退出，**后面的产物归档、17 项断言、`verification.md` 全部丢失**（`20260918-091057-r14-l3` 只剩 `run.json`/`timing.json`，而 turn 本身已成功完成）。改法（只动 runner）：① `_req` 对 **GET 重试 3 次**（退避 3/6 s）后仍失败才 `die`；**POST 保持单次**，保证抖动不可能变成重复写入；② `usage`/`limits` 这两个**纯装饰**端点标 `soft=True`，失败返回 HTTP 0 并在记录里落 `{"_error": …}`，`verification.md` 新增一行 `collection gaps (decorative endpoints unreachable, evidence intact)`；③ 承载证据的 `/timing`、`/info`、`/messages`、`/artifacts`、`debug/history`、`artifacts/archive` **仍保持硬失败**（宁可红也不假绿）。备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v5.bak` | W6/R14 | 已修 | 已修并回填：不改 runner 的条件下用 `run --resume <thread>` 把这线程重新收集成 `…092000-resume-r14-l3-recollect/`（17/17 PASS） |
| O24 | **模板规格句被照抄进交付报告**（2026-09-18 `R15` 发现，**已修**）：报告覆盖行出现「原文优先于库内加工字段，不一致处同时写出原文值与库内记录值；」—— 模板第 5 行把规则写在 `**原文核对：** [...]` 括号外，模型当正文照抄。四个模板已移进规格括号；新增清单项 `A-P7-no-template-spec-in-report`（`op_report_excludes_literals`）+ 专属变异 `M23`（实测同时带动 `A-P2`）。备份/闸门：`arm a 38/38`、`arm b 12/12`、`GATE: PASS`、`verify-run-chain GATE: PASS`、dist `c55321ad4619` / 84,991 B 逐字节校验。**线上仍是旧模板** ⇒ 需再次授权 `push-skill`（in-place） | R15 / R16 | 已修（仓库 + 已上线一版） | **R16 已复验：三个字面在真产物里 0 命中**；但 R16 又暴露**同类换措辞**写法（`未发现原文与库内记录…不一致`）⇒ 已按 `A-P8` + `M24` + 合同/模板/sys 三处补规则，**R17（发布后同输入真跑）已复验：`A-P2/A-P7/A-P8` 全 PASS、覆盖行无规则句** |
| O25 | **runner 工具调用计数口径自相矛盾**（2026-09-18 核 R15 数字时发现，**已修**）：schema 被拒的 call 会被框架重发成**新 call**，它既在 durable `calls` 里（无返回）、又不是「已返回」的一次；旧代码两处都印成 `attempts = len(calls) returned + len(rejected)` ⇒ R15 印出「30 attempts = 30 returned + 1 schema-rejected」，且被拒的那次被算进 returned 直方图（`web_fetch`×3，实为 2 次返回 + 1 次被拒）。修法：`ret_n = len(calls) - len(rej_ids)`，直方图剔除被拒项，另加 `[rejected: web_fetch×1]` 单列。备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v6.bak`（95,169 B，**O23 之后 / O25 之前**的状态，由 O25 三处 hunk 反向重建并 `py_compile` 通过）；`verify-run-chain.py` 仍 `GATE: PASS`；`run --resume`（R15 线程）实测新口径输出「29 returned + 1 schema-rejected (…web_fetch×2…) + rejected web_fetch×1」 | R15 | 已修（仅 runner 本地） |
| O26 | **数值「符号 vs 幅度」写法**（2026-09-18 `R16` 对比 R8/R12/R15 发现）→ **已定案并落地**：用户口径「两种写法没关系，只要自洽就行」⇒ (a) 放弃原先「写死带符号」方案，改成**写法自由 + 同份交付物自洽**：`A-C4`/`A-C5` 模式 `[\u2212-]?` 符号可选（数值仍逐位精确，M01 仍翻）、`A-S9` 比绝对值（M10 仍翻）、**新增 `A-S10-sign-convention-consistent`**（被画进图的量在报告与图表必须同口径；`M25` 先读基线口径再把图表翻成另一种，只翻 A-S10）；合同（`input-contract.md`）+ sys v0.15 同步写清「作用域 = 被画的量，点估计无符号 + CI 带符号是正常渲染」 | R8/R12/R15/R16/R17 | 已改（仓库 + 已 in-place 发布） | **R17 复验通过**（`39/40`，本轮唯一 FAIL 是 O20；R16 幅度口径现在也全 PASS） |
| O27 | **清单条目 `A-C16-hard-outcome-gap` 术语绑定过窄**（2026-09-18 `R16` 暴露，与 O20 同类）：R16 在表格里明确写了「心血管结局事件（如 MACE）」并标注两侧「未报告／未对齐」，但条目正则只认 `硬结局|心血管事件` ⇒ 被判 0 命中。要防的是「硬结局缺口不写」这件事实，不是某个词形 | 正则放宽为 `硬结局|心血管事件|心血管结局`（仍要求出现在正文），配套检查 M-变异仍能翻 | **待批**（证据：R16 报告第 4.3 节 + 表格行；1 份产物） |（**R17 用「心血管事件」词面 ⇒ 该条 PASS**，故现为 1 失败 / 1 通过，仍按「待样本」不动） |
| O28 | **`A-ATTR` 的「数值对」分支从未命中过任何产物**（2026-09-18 核 `M27` 时发现，**已修**）：token 写 ASCII `-13\.9`，四份真产物正文一律 U+2212（`−13.9`：R8/R12 各 5 处、R16 有符号式、R17 9 处）⇒ 静默漏检（假绿方向）；改成 `[\u2212-]13\.9` 后四份产物重打**无新增 FAIL**（说明真产物数值归属本来就干净，缺的只是这层检查），`M27` 现在能翻 `A-ATTR` | F2 | 已修（仅仓库评测资产） |
## 4. 平台侧（转开发）

完整、可直接转发的版本见 Obsidian：
`03-技术与VibeCoding/01-AI与LLM/ToolSmith-平台问题单-ChatAPI与SSE文档缺口.md`

摘要（均为文档/可观测性问题，非阻断性 bug；**2026-09-17 起文档缺口也一并上报**，旧「不报文档缺口」规矩已作废）：

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

- **P10（新，2026-09-17，待用户决定是否转开发）`web_fetch` 对主流医药信源的人读页面基本不可用，失败语义不清**：实测（W2-a/c/d；W2-c 更正：**失败时确实返回状态码文本**，如 `403 Forbidden`，只有成功时不回状态码）——PubMed 人读页返回反爬拦截页 `Cookies must be enabled … reload this page to continue.`；ClinicalTrials.gov 人读页（含 `?tab=results`）只返回 JS 骨架（`Show glossary` / `Study record managers: …`），拿不到试验记录；失败抓取会计入「schema-rejected」计数（正常 0 schema-rejected 的健康指标会因此失真）；沙箱自身无外网（`Could not resolve host` ⇒ `web_fetch` 为平台侧代抓）。
  - **可用替代（我们实测能通）**：CT.gov v2 API `https://clinicaltrials.gov/api/v2/studies/<NCT>`（返回完整协议 JSON）、Europe PMC REST `…/rest/search?query=EXT_ID:<pmid>&resultType=core&format=json`（返回 `abstractText`/`pmcid`/`isOpenAccess`）。
  - **建议**（开发定）：`web_fetch` 至少回传状态码/失败原因；若能力允许，对已知医药域名提供「API 端点优先 / 简单渲染」路径。

### 2026-09-17 对照 TS @ `30306cb`（**P7/P8 的定性要改：P7 已由平台从根修掉**）

上游 `30306cb remove unknown status, add idle`（含前三个提交 `8d10fa0` / `af4f601` / `34215c3`）逐条核对：

- **P7 = 已修（从根，不是绕过）**：`30306cb` 里 `cleanup_stale(300)` 被删、`run_manager.complete()` / cancel / force-kill
  三处立即 `_discard_run()`、`active_run_count` 简化为 `len(self._runs)`。**「活窗口内 `/timing` 大幅高估」不再存在**
  （run 一结束就换成持久化行）。prod 只读实测（2026-09-17）：R8/R9 两个 thread 的 `/timing` 已是冻结行
  （`latency_ms` 202049 / 171141，与记录逐位相等）。
- **但同一提交把「结局」从 API 里删掉了**：`/info.status` 现在是 `Literal["preparing","running","cancelling","idle"]`
  （`?status=idle`→200、`?status=未知`→400、**`?status=completed`→422**），而 `/info` 没有任何 outcome 字段、
  `thread_messages` 也没有 outcome 列。源码里的顺序不变量是「**先**持久化（含 `finish_timing_now(completed_at=…)`）、
  **后** `run_manager.complete()`」⇒ `idle` 必然意味着 DB 行已有 `completed_at`（终态可判），但
  **成功/失败/取消只能从持久化消息里读**：`chat_service._normalize_error_text_part()` 把
  `providerMetadata.pydantic_ai.provider_details.error_type` 归一化成 text part 顶层的 `error_type`
  （`stream_error` / `TimeoutError` / 异常类名），取消则写 `state="interrupted"`（`_persist_partial_run(error_type=…)`）。
- **→ 2026-09-17 改为上报（P9，用户已撤销「不报文档缺口」）**：上面这条当时按「不报文档缺口」的旧规矩内部存档，**该规矩已作废**（用户原话：「这个不报是不对的，得报，让他自己决定」）。已写成完整问题单 **P9**（Obsidian 同文件「第三批」，含端点逐条清单 + DB 列清单 + webhook 为唯一通道的源码位置 + 文档自相矛盾那段 + 三条建议）。仓库侧只留摘要：
  - **现象**：run 结局（`succeeded`/`failed`/`partial`/`cancelled` + `termination_reason`）**只能从项目级 webhook 拿到**；HTTP 侧 `chat_routes.py` 全部端点无 outcome 字段、`thread_messages` 表无 outcome 列、`/timing` 只说明「结束了」、`/thread-turns/validate` 只回 `{exist}`（且未文档化）、`GET /chat/{tid}/stream` 在 run 结束后回 **204 且不重放**。
  - **影响**：`chat-api.mdx` 要求「外部客户端需要在 run 成功完成后重新确认产物」，却没给判断「成功完成」的 HTTP 方法；失败/取消的 run 也可能已写出部分产物。我们只能靠未文档化的 `messages` text part `error_type` / `state=interrupted` 自建 `classify_outcome()`（R11 已在生产路径跑通）。
  - **建议**（开发定）：① `/timing` 的 turn 行加 `outcome`/`status`；② 或新增 `GET /threads/{id}/turns/{turn_id}`（与 webhook 同口径）；③ 或至少把「webhook 是唯一权威通道 / 无 webhook 时怎么判」写进文档。
- **P8（原：错过窗口就无法区分成功/失败）→ 定性修正**：窗口问题由平台从根解决；剩下的是**结局不在 API 里**，
  由 runner 侧 `classify_outcome()` 补齐。
- 与我们的依赖无关：`8d10fa0 add province and city params` 只改 `params_drug_deal_tool_v2.py` / `params_pipeline_tool_v2.py`，
  **`params_clinical_result_tool.py` 未动**；`deps` 复跑 **RC=0**。

**（2026-09-16 的旧结论，保留作历史）P7 / P8 当时按 §8.1.1 的三轮实验定为「不报」**：

- **P8（原：终态不落库、错过 300–360 s 窗口就无法区分成功/失败）→ 撤销上报**。实测：窗口过期后 `/info.status` 确实回落
  `未知`，但 `/timing` 的**持久化行**（`completed_at` / `completed=true` / 冻结的 `latency_ms`）与
  `/thread-turns/validate`（`exist: true`）都长期可读，`/messages` / `/debug/history` / `/artifacts/archive` 一样在。
  ⇒ 终态与全量内容可重建，属客户端体验问题，我们自己加 fallback 即可。
- **P7（原：`/timing.active_turn` 不判状态）→ 描述修正、仍降为不报**。准确描述是：run 仍在内存时 `/timing` 给的是
  **临时行**（`completed_at=null`、`completed=false`、`latency_ms` **现算递增且大幅高估**，实测 190 s → 350 s → 429 s →
  443 s，真实只跑了 171 s）；`cleanup_stale` 之后换成**持久化行**（三个字段同时变正确）。
  结论不变（`/info.status` 为唯一终态判据已足够），但“滞后”这个说法要改成“**临时行不可信**”。

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
