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
- **事实清单第二份独立样本**：同一场景 A 的新产物 → `SCORE scenario=a facts 30/30 warn 1/1 -> PASS`（修正打分器句切后；修正前 29/30 是 O12 假 FAIL）。
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

### F1 — 事实清单基线 + 负向对照（2026-09-16，**离线，零新 run**）

- **产物**：`evals/fact-check/`（`records/` 2 份 ground truth、`scenario-a/b.facts.json`、`check.py`、`mutations.py`、`README.md`）。
- **清单基线**（直接打 R8 产物，未重跑）：`SCORE scenario=a facts 30/30 warn 1/1 -> PASS`（exit 0）、
  `SCORE scenario=b facts 12/12 warn 1/1 -> PASS`（exit 0，B 打的是 R6 拒产 run）。
- **负向对照（证明清单有牙）**：`python3 evals/fact-check/mutations.py` → **GATE PASS**：
  arm A **15** 个变异翻天 30/30 条 fail 级条目（M05 改引注、M15 表格单元格跨记录归属）；arm B **11** 个变异翻天 12/12 条；
  每个变异都令退出码变 **3**，且必须命中**预期 item id**（只判 `rc==3` 不够）。基线（未变异）两份清单必须全 PASS。
- **第二份独立样本**：R9（同一场景 A 的新产物）→ `SCORE scenario=a facts 30/30 -> PASS`（修正 O12 的句切后）。
- **意义**：质量层从「布尔门」升级为 `facts_ok/facts_total` 标量（`docs/autoresearch-iteration-plan.md` §9），
  后续 keep/discard 先看事实分不掉。

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

**P7 / P8 在 2026-09-16 已由 `docs/toolsmith-run-v2-polling-plan.md` §8.1.1 的三轮实验定案，两项都降为「不报」**：

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
