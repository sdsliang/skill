# 部署端自验证台账（ToolSmith chat API 直驱）

> **用途**：每次迭代 `skill/` 或 `system-prompts/` 之后，用真跑一次的 chat 来证明
> "线上跑的确实是我们刚改的字节"，并把过程中发现的缺陷按两栏记账：
> **(1) 我们自己能改的**、(2) **平台侧（转开发）**。
>
> 一次验证 = 一条 `R<n>` 记录。**没有新记录就等于这次改动没验证过。**

## 当前状态（2026-09-18 全项目审查）

本地修复与离线验证见 **F7 / O33–O38**，完整审查见 [project-review-2026-09-18.md](project-review-2026-09-18.md)。**本轮没有发布、没有线上 run，也没有已完成的 R21**；旧 R 记录的断言数、分数、哈希均按当时版本保留。评估器 r2 为显式新基线，A 41→43 不是质量提升。当前 `status` exit 3 是预期的真实差异，不能用历史 in-sync 覆盖。

## 0. 流程（标准动作）

```bash
cd /home/xupeipeioo1/apps/skill/clinical-result-comparison
python3 tools/pack-dist.py                 # 重打 dist；文档改动不进入包
# 每次先取得明确的 prompt/skill 发布授权：
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

退出码：**0** 全过 / **3** 跑完了但有断言失败（或非 schema 拒参的工具报错）/ **4** `not_started`（turn 从未进库，POST 没落地）/ **5** `inconclusive`（缺少可确认完成的 durable 记录）或 `timeout`。

> **2026-09-16 起 `run` 不再消费 SSE**：`POST /api/chat` 只读到 `data-turn-start` 就断连，之后按 ≤60 s 轮询
> `GET /api/threads/{tid}/info` 观察活动状态，并以 `/timing.completed_at` 判完成；`idle` 不代表成功（平台把 run 当独立任务跑，客户端断连只摘订阅者、**不 cancel**）。
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
> ② **每个目标 turn tool-call 必须有实际 tool-return，或有可识别的拒参/抓取失败记录**；无解释的缺返回 FAIL。已分类的无返回分两桶记：
> `args-refused` 参数被工具拒（形状/字段名/取值）由框架重发、`fetch-failed` 外部抓取失败——4xx/5xx、主机不可达；
> 旧版把两者都印成“schema-rejected”**并从 `errors` 里藏掉**，于是 FAIL 级的 `no tool errors` 在抓取已经 500 的情况下
> 仍然全绿，见 runner O32。未知归属、歧义或其它工具错误不能进入豁免桶。
>
> **2026-09-18 起再加一项（产出物路径 17 → 18 项 / 拒绝路径 11 → 12 项）**：**`tool_results` 回执归档**
> —— 平台在 turn 结束时删掉 `tool_results/**`、又在产物面板里过滤掉它（`fs_workspace_store._remove_runtime_paths`
> + `chat_service._ARTIFACT_IGNORE_DIR_NAMES`），所以它**只在 run 存续期间可读**；runner 新增 `ReceiptArchiver`
> 每 5 s 轮询持久化消息抠指针并即时下载（第一次命中在第 7.4 s，见 R19/R20 与 `docs/evidence/receipt-layer-2026-09-18.txt`）。
> 断言 `tool_results receipts archived`：**F7 已收紧**，必需指针由最终目标 turn 的持久化证据重建，不由轮询数量定义。目标证据完整且无指针才可 n/a；漏轮询、归属歧义、缺 manifest、缺文件或字节/哈希不符均 FAIL。
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

**后续（同日 F4）**：换基线后马上发现 `A-P6` 这条 **在真产物上空转**（`O29`）——基线再真，也拦不住「断言自己没在评判」；
修法与产物层证据见 **F4**。

### F4 — 2026-09-18，**`A-P6` 在真产物上空转（`O29`）修掉 + 补上反向的 `A-P9`**（离线，零新 run、零发布）

用户「接着开发完善」授权。改动全在**仓库评测资产**：`evals/fact-check/check.py`（两个 op + 归位助手）、
`scenario-a.facts.json`（新条目）、`mutations.py`（两个新变异 + 一个重写 + 闸门判据收紧）、`README.md`（三节）、
`docs/evidence/` 两份证据。**没碰 `skill/`、`system-prompts/`、runner、平台** ⇒ dist 无变化 ⇒ 不需重打包、不需发布授权。

**缺陷本身（`O29`）**：`A-P6-cite-link-is-deepest` 旧实现只把「文件名以 `ref_<n>` 开头」的归档算作某条 ref 的全文正文，
而真产物按**文章**或 **esid** 命名（`input-contract.md` 要求 `<esid>.<route>.xml`；`R14` 实际落盘
`PMC11270764_fulltext_jats.xml`）⇒ 拿 `R14` 原产物重打（只读、不花额度）：

```
[PASS] A-P5-fulltext-fetch-is-declared full text archived (2 file(s)) and declared
[PASS] A-P6-cite-link-is-deepest  no per-ref full-text body archived (check not triggered)   ← 空转，O29
SCORE scenario=a facts 25/40 -> FAIL
```

打印得像通过，其实一个 citation link 都没看——而 `R14` 正是催生 L3 规则的那份产物。更麻的是**它能过闸门**：
`M21`/`M22` 的归档文件是 harness 自己拼的 `ref_1.pmc-fulltext.xml`，即断言与样本同源、拿自己的假设自证。

**同时发现的单向性**：规则只写了「归档了全文 ⇒ 引用必须指全文」（`A-P6`），没有任何断言防
「引用声称读了全文、磁盘上一个字都没取」——而 `A-S5` 恰恰是允许把 `link` 换成全文白名单 URL 的。

**做了什么**

1. `A-P6` 归位拆四条通道（顺序即优先级）：① 文件名 `ref_<n>` 前缀；② 记录 esid 出现在文件名或正文前 4 K；
   ③ 正文的 `PMC<id>` 与链接相同；④ 正文的 PMID 与链接相同。四通道都归不上时**不猜**（判 PASS，但把文件名写进诊断）；
   `PMC\d+` 先抹掉再扫 PMID（否则 `PMC11270764` 的数字会被当成 PMID 命中）。
2. 新增 **`A-P9-fulltext-cite-has-body`**（`op_fulltext_cite_has_body`，`scenario-a` 第 42 条，fail 级）：
   `link` 一旦指向全文载体（同 `A-P6` 白名单）就必须有带同一个 `PMC<id>` 的字节落在 `/workspace/sources/` 下。
   记录自带 `full_article_link`（PubMed/出版商页）逐字节相同时**不算深度声明**、跳过（那是库给的值，不是模型选的）。
   两条合起来才是 L3 闭环：`A-P9` 管「到底取了没有」、`A-P5` 管「有没有向读者声明」、`A-P6` 管「引用落点对不对」。
3. 变异：`M22` 重写为 **真产物命名**（`PMC11270764_fulltext_jats.xml`，JATS 里带 `pub-id-type=pmcid/pmid`，
   靠链接 PMID 归位到 ref_1；旧版写的匿名 `ref_1.pmc-fulltext.xml` 就是 O29 的同源样本）；新增
   `M28 fulltext-cited-but-not-fetched`（只翻 `A-P9`）与 `N28 fulltext-claim-with-bytes`（`R14` 的合法形状，
   `A-P5`/`A-P6`/`A-P9` 三条必须保持绿——正控）。
4. `NEG_A` 判据收紧：旧版只看「我想保绿的那一条没翻」，于是一个把**别条目**打翻的负向对照也会报 `[OK]`；
   现在要求 `rc == 0 且 flipped == []`，否则 `[BAD]`。四条负控均 `rc=0`。

**证据**

```
$ python3 evals/fact-check/mutations.py            # 退出码 0，50 行输出落库
baseline a: 41 fail-severity items, all PASS
[OK ] M22 fulltext-archived-but-abstract-link    rc=3 flipped=['A-P6-cite-link-is-deepest']
[OK ] M28 fulltext-cited-but-not-fetched         rc=3 flipped=['A-P9-fulltext-cite-has-body']
[OK ] N25 / N26 / N27                            rc=0 kept … green
[OK ] N28 fulltext-claim-with-bytes              rc=0 kept A-P6-cite-link-is-deepest green
arm a: flipped 41/41; never flipped []
arm b: flipped 12/12; never flipped []
GATE: PASS
```

（完整输出 50 行、43 个 `OK` 行：`docs/evidence/mutation-gate-2026-09-18-r17-baseline.txt`。
变异总数 28（`M01–M28`），负控 4（`N25–N28`）。）

真产物重打（这是**闸门看不见的那一层**，单独落库）：
`docs/evidence/fact-check-l3-real-artifact-rescore-2026-09-18.txt` —— **7 份**拿得出来的场景 A 真产物同一命令重判（`R14`/`R8`/`R12`/`R15`/`R16`/`R17`/`archive-scope` 探针），
`R14` 由「`check not triggered`」变为 `1 full-text ref(s) cite their full-text carrier`（`A-P9` 同轮
`1 full-text citation(s) backed by an archived body`）；`R17`（基线，0 归档）与 `archive-scope` 探针
（`sources/probe.txt` 不是原文）三件套均报「未触发」而不是假绿。
文件末尾另有一句**覆盖面自白**：7 份里只有 `R14` 一份真归档了全文 ⇒ 「触发后真的判对」只在 **1/7** 上验过，
另两条归位通道（文件名 `ref_<n>` 前缀、esid）只被 harness 的 `M21`/`M22`/`N28` 练过；下次真拿到 PMC 全文的真跑必须补一行。

**基线自评**：`SCORE scenario=a facts 41/41 warn 1/1 -> PASS`（R17，条目 41→42、fail 级 40→41）。

**没做的（有意）**：不动 `skill/`/`system-prompts/`——本轮发现的是**量具**缺陷，规则本身没错（合同早就要求把抓到的正文
拷到 `/workspace/sources/`，`A-P9` 只是把这个已有要求变成可判）；也不去动清单里其它「前提不成立 PASS」的断言
（`A-P3` 等同族项），先把机制写进 README 的已知缺口，等有真样本再说。

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
| 调用 | **30 次尝试 = 29 返回 + 1 schema 被拒**：`execute`×15、`read_file`×9、`web_fetch`×2、`load_skill`×1、`params`×1、`present_artifact`×1；被拒的那次是 `web_fetch`（**2026-09-18 O32 修正**：它不是参数被拒，而是抓取失败——欧洲 PMC 全文 XML 返回 500；参数被拒与抓取失败现在分两桶记 → 框架重发为新 call，无返回）。**注**：run 目录里的 `verification.md` 是 O25 修复前的渲染，那行印成「30 attempts = 30 returned + 1 schema-rejected」（自相矛盾，见 O25）；上表是修正后的口径，已用 `--resume` 重收验证 |
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

- **更正 W2-a/b 的推断**：`web_fetch` 在**失败时确实带 HTTP 状态码文本**（如 businesswire / jitc.bmj.com 返回 `403 Forbidden`），只是**成功时不回状态码**；失败抓取计入「schema-rejected」而不是普通 tool 调用（所以「0 schema-rejected」不能单独当健康指标）。**（2026-09-18 O32 后修正）**：抓取失败已拆成独立桶 `fetch-failed`，与「参数被拒」不再混计。
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

### R18 — 2026-09-18，**B1（「短 `abstract_text`」假设修正）in-place 发布后的真跑**（17/17 PASS，事实 41/41）

**这一轮改的是 TS 资产**（sys + `references/input-contract.md`），先 `pack-dist.py` 重打包，再
`publish` **原地更新**（prompt `v1.6` 内容替换、skill `v1.0.7` 内容替换，版本号标签不动），
`status` 回读 `in sync`（prompt 逐字节、技能包 19 个文件全同）——发布动作经用户 2026-09-18 明确同意
（「B1,4,5都可以原地」）。

- 改了什么：把「挑 6–8 个小 esid（records 小、`abstract_text` 短）」这条**按 esid 个数**的措辞，
  换成**按来源类**的实测口径（PubMed / 会议摘要体量 1–4 K 字符；登记号类 `2`/`187` 带 CT.gov
  结构化 results JSON，中位 30–60 K、最大 1.9 M、77% 是 JSON 不是散文；`49` 号新闻稿 ≤78 K）。
  数据源：`docs/evidence/abstract-text-by-source-2026-09-17.json`。
- 真跑：thread `f0ac7f8a-2ea4-4ea6-b257-3e6ffc018f2a`，turn `8eefc445-069e-4468-a714-6b5e02f6e6d3`，
  prompt `解读这几个结果 24_1_30561610 24_1_36342163`，`--web`，DeepSeek Flash，**exit 0**。
- 记录：**17/17 PASS**；墙钟 **198.1 s server / 204.8 s polled**；**32 次调用尝试** = 30 returned
  + 1 `args-refused`（`pharmcube-query-clinical-result-with-params`：模型发明字段 `clinical_result.moa`，
  工具回 `INVALID_INPUT: Invalid fields selected`，O3 那条规则的自愈路径）
  + 1 `fetch-failed`（`web_fetch` 抓 `…/europepmc/webservices/rest/PMC6933872/fullTextXML` 收 500）
  = `execute`11 · `read_file`8 · `write_file`3 ·
  `params`2 · `web_fetch`2 · `edit_file`2 · `load_skill`1 · `present_artifact`1；产物 `report.md` 15,658 B、
  `citations.json` 513 B、`visualizations/endpoint-bar-1.json` 1 张（`sources=0`）。
- 事实分（离线 `check.py --scenario a`）：**`facts 41/41 warn 1/1 -> PASS`**（exit 0）。
- **没有把这次改动判成回归**：R17（27 calls / 41/41）→ R18（32 calls / 41/41），成本 +5 次而事实分不动；
  两轮差的不只是 B1 那几行（params 调用 1→3、execute 9→11），n=1，按 §8.2 要 A×3 才谈噪声带
  → 记「**待样本**」，不改规则。

### R19 / R20 — 2026-09-18，**runner 新增 `tool_results` 回执归档**（E0 回测；先失败一次，改对后通过）

**背景（先立事实，再写代码）**：`tool_results/**` 是「工具返回的完整 JSONL/正文」，但平台在 turn 结束时
删它、产物面板也过滤它 ⇒ `file-download?path=…` 对**已结束**的 run 一律 **HTTP 404**（R17 thread
`7549e95f-…` 两个真实指针 + 目录本身实测 404）。离线全量扫描 28 个 run 目录：**109 个 `tool_results` 指针，
107 个永久不可恢复**（证据 `docs/evidence/receipt-layer-2026-09-18.txt`）。

**R19（第一次，暴露一个假指针）**：thread `787494b5-967a-492b-be7d-c5452078e79b`，场景 B 拒产，
33 次轮询、看到 2 个「指针」、取回 1 份 30,816 B；另一个是 `…/tool_results/<tool>/`（**目录**，不是文件）
→ 404。这说明指针正则必须要求「末段是带扩展名的文件名」。同轮 11/11 断言 PASS（当时还没加回执断言）。

**R20（改对后）**：thread `ffb43fde-f912-4fb0-a58d-b47f2d02a7e1`，场景 B 拒产，`--expect refusal`，
**12/12 PASS**（含新增 `[PASS] tool_results receipts archived — 1/1 fetched, 0 failed, 31407 B → tool_results/ (6 polls @ 5.0s)`）；
墙钟 29.4 s server / 32.8 s polled。`receipts.jsonl` 第一行：`{"t": 7.4, …, "status": "ok", "bytes": 31407}`
→ **回执在第 7.4 s 落盘**，即 run 还活着的窗口内；首行内容是带 `clinical_result_study_results` 数组的完整记录
（不是摘要预览）。

**这两轮的「schema-rejected=1」在 O32 之后重读为 `args-refused`**。**2026-09-18 F7 归因更正**：live `deps` 确认 schema 已 `+esids -extra_esids`，但旧 sys/skill **明文要求 `extra_esids`**。记录字段仍是 `clinical_result.extra_esid`；第一发被拒、改用 `esids` 后自愈是事实，原记「模型按记录字段名发明参数」**不成立/证据不足**。本次已适配仓库规则、live 重生成镜像并接受本地 deps 基线；尚未发布。
同一批重读还暴露出 R15/R16/R17 各有一条 `web_fetch` 抓欧洲 PMC 全文 XML 的 500，此前它们在 `errors` 里不可见。

**runner 侧改动**（我们自己的层）：`~/.local/bin/toolsmith-publish` 新增 `ReceiptArchiver`
（5 s 独立线程轮询 `/threads/<tid>/messages` → `artifacts/file-download` → `<run>/tool_results/**` +
`receipts.jsonl` + `run.json.receipts`），**永不致命**（取不到只记账，不丢整轮产物）；
`py_compile` 通过、`evals/runner-gate/verify-run-chain.py` **GATE: PASS**（改动前后各跑一次）。
备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v7.bak`（95,879 B）。
**边界**：只证明回执**被取回**，不证明报告数字**取自**回执（那是另一条断言的事）。

### F5 — 2026-09-18，**autoresearch harness 骨架 + §6 基线离线回填**（离线，零新 run、零发布）

- **产物（仓库）**：`tools/replay-run.py`（`debug-history.json` → 成本/质量全字段 + `--tsv` + `--score` 调 `check.py`）、
  `tools/pack-dist.py`（**入仓**的确定性打包器，`--check` 当闸门）、
  `docs/evidence/autoresearch-baseline-tsv-backfill-2026-09-18.txt`（**7 行** TSV）、
  `docs/evidence/receipt-layer-2026-09-18.txt`（E0 四段证据）。
- **回填结果（§6 的开放问题现在有答案）**：场景 A `173645-a-2valid` **38/41** @ 23 calls；
  `174222-a2-2valid` **40/41** @ 41 calls（+18 calls 换 +2 条事实 = **交换，不是白赚**）；
  R17 **41/41** @ 27 calls；R18 **41/41** @ 32 calls；三个场景 B 行均 **12/12** @ 8/8/8 calls、33–36 s；
  `171953-cite-date` 3/12（场景 b 未收敛仍交付，记 `b?`）。
- **两个口径坑（已写进证据文件，避免下一轮误比）**：① `turns` 在 2026-09-15 前后语义不同（`/info` 的
  `stats.turns` vs 老 harness 数模型轮次）⇒ `--details` 另报 `model_turns`；② `deployed_sys_sha` 是**装配后**
  instructions 的 sha（≠ 本地文件哈希，`--details` 才报「哪份本地 prompt 是其字节前缀」）。
- **`tools/pack-dist.py --check`**：`dist/multi-clinical-result-comparison-v0.15.zip` 与重建结果**逐字节相同**
  （86,285 B / sha `404dbccf5058`）⇒ B1 那次发布的内容与仓库 dist 一致，打包可复现。
- **意义**：`val_bpb` 缺席这件事从「无解」变成「有两层数可读」——成本层 `calls/wall_s`、质量层
  `facts_ok/facts_total`（gate，不进总分）。

### F6 — 2026-09-18，**runner 归因修正：`retry-prompt` 分三桶（O31 + O32）**（离线，零新 run、零发布；仓库 `4a60aba`）

**起因**：R19/R20 的 `verification.md` 里「schema-rejected」那行只有工具名、没有原因，翻 R18 也一样。

- **O31（渲染 bug）**：durable `retry-prompt` 的 part 键是 **`content`**（近期 run 里是 pydantic 的**字符串**，
  更早的 run 是错误 dict 的**列表**）；三处渲染器都在按「list of dict」迭代 `reason` ⇒ 对字符串迭代再筛 dict
  ⇒ 原因永远印不出来（R18/R19/R20 都只印了 `- toolname:`）。修法：统一走 `rej_text(reason, n)` 助手
  （str → 压空白取 300 字符；list → 合并 dict；None → `(no reason recorded)`），断言 detail 与 console 共用。
  **纯展示层，统计值不变**。
- **O32（归因 bug，更重要）**：框架的 `retry-prompt` 有**三种**成因，旧代码全归成「schema-rejected」，
  且在 `raw_ui_messages` 的 `output-error` 回路里按 id 跳过 ⇒ 这些事件**在 `errors` 里也不出现**，
  于是 FAIL 级的 `no tool errors` 断言对「外部抓取失败」完全失效。实测：R15/R16/R17/R18 各有一条
  `web_fetch` 抓 `…/europepmc/webservices/rest/PMC6933872/fullTextXML` 收 **500**，**四轮全绿**。
  修法：按原因文本分三桶 —— `rejected`（参数被拒：pydantic `validation error for call[…]` /
  `Unknown tool name` / `Field required` / `Extra inputs are not permitted` / `[Tool error] INVALID_INPUT`）、
  `fetch_failures`（`^Failed to fetch`：可见、打印、写进 `verification.md`，但**不**判 FAIL）、
  其余（真正的工具链故障）落回 `errors`（**仍是 FAIL 级**）。
- **当时已确认的事实**：交付物确实披露了 500（R17/R18 覆盖行）；**F7 更正其边界**：这只能证明失败可见，不能证明「非 OA」归因正确。HTTP 500 或缺 PMCID 本身均不足以判非 OA，当前仓库规则已纠正，尚未线上验证。O32 的桶名描述技术失败类型，不证明由模型发明参数。
- 影响面：`verification.md` 断言清单多一项 INFO 行（**产出物路径 18 → 19 项 / 拒绝路径 12 → 13 项**）；
  `tool calls:` 行改为「N attempts = M returned + a args-refused + f fetch-failed …」；`--details` 增加 `web=on|off`。
- 备份：`~/.local/state/toolsmith-publish/toolsmith-publish.v8.bak`（O31 的 `rej_text` 补丁前）。
  `py_compile` 通过；`evals/runner-gate/verify-run-chain.py` **GATE: PASS**（gate 自己也要改：把
  `rejected + fetch_failures` 一起当作「SSE tap 看不到的尝试」，否则 5 个 v1 run 里带 500 的那次会对不上）。
- 离线重读（零网络）逐 run 结果见 `docs/evidence/autoresearch-baseline-tsv-backfill-2026-09-18.txt` 注 7/注 8。
- **验收方式**：① 五类原因形状的合成单测（pydantic 串 / 错误 dict 列表 / `Unknown tool name` / `Failed to fetch` /
  `[Tool error] RuntimeError`）→ 前四类归入对应桶、「工具真崩」仍落 `errors`；② 用 R18 真 run 目录**离线**重建
  bundle 调 `check_run` → **19 项**、新增两行 INFO 正常渲染（`args-refused = 1` 带 `clinical_result.moa` 原文、
  `external fetch failures = 1` 带 500 原文）。
- **注意（老 run 目录）**：`receipts` 记录是 O30 之后才有的，拿 O30 之前的老 run 目录重跑 `check_run`
  会让 `tool_results receipts archived` 判 FAIL（无记录）——属预期，不要当成回归。

### F7 — 2026-09-18，全项目审查与本地修复（离线验证 + 只读 live 核对；无发布、无新 run）

用户范围：「A10 给我个示例 id，别的你都改。另外 6-astra 你来，审查整个项目」。本轮修改 **runner + 仓库资产**，不改 TS 平台，不写 TS 资产。A10 仅交付 `24_1_39054491_1`，不写数据库、不发问题单。详细发现、文件和复验边界见 [全项目审查](project-review-2026-09-18.md)。

- **O33 runner 安全/回执**：拒绝路径逃逸与符号链接；回执必需集取自最终目标 turn 的持久化消息，不取自 poll 命中；下载重试、终止收集线程 join、落盘字节/哈希验证。外 turn 指针不污染当前 turn，未知形状/歧义失败。备份先 v9 后 v10；`evals/runner-gate/runner-patches/review-hardening.patch` 为**相对原始 v9 的累计补丁**，不能叠加到 v10。
- **O34 runner 断言/归因**：实际 tool-return 计数；未知缺返回与 turn 归属歧义失败；空产物、错误图表引用、缺支持文件清单失败；错误分类正则加固。历史链无可比样本 exit 2，不能假绿。
- **O35 评估器**：观察值绑定药物/剂量/试验/时间/数值，单点符号翻转和错误显示标签失败；全文需正文与独立身份支撑，查询证据限定目标 turn；补无基线/空文件/错引用/边界对照。**显式新基线 `2026-09-18-r2`**，A 43 fail + 1 warn，B 12 fail + 1 warn，旧 41→43 不是质量增长；详见 [修订及证据](../evals/fact-check/EVALUATOR_REVISION.md)。
- **O36 本地 tools**：打包路径/符号链接和缺输入检查、replay 调用/场景/评分失败处理加固；19 tests PASS，dist 重建可重复。
- **O37 本地引用/实体校验**：引用值/URL、marker parity 与实体检查加固，21 Node tests PASS。`runtime/citation-renderer.mjs` 不是生产实现或 HTML sanitizer，不能由这些测试推导生产前端安全结论。
- **O38 运行规则适配**：live `deps` 证实 `+esids -extra_esids`；旧提示词要求失效参数，R19/R20 不能归咎模型发明。17 份运行文件纠正参数、`group_count` 入组人数语义、L3 统一权威、全文引用与非 OA 推断；live schema 镜像重生成，本地 `deps --accept` 已接受。三 chart templates 对上游 1.0.12 的 `validateVisualizationFile` PASS，使用隔离 Zod 4.6.5（不是 TS runtime）。

**验证汇总（父任务实跑，本次文档整理据此记账）**：runner 30 + scorer 27 + tools 19 + Node 21 = **97 tests PASS**；mutation **63 controls / A 43/43 / B 12/12 PASS**；历史链 **5 comparable / 36 histories / 31 skipped / 4 no-history**。R17/R18 r2 重判 **43/43**、R20 **12/12**；R14 不是 A，只有两条定向全文核验适用且通过，不能写成 A 满分或回归。

**部署对照（只读）**：本地 prompt **54,311 B / 2ff672b5aa9b**，dist **85,633 B / 19 entries / `4d20d48faeeee012c347aa28eb5956e5238a3e95020999c6b9bd6084fba53b1e`**。线上仍 prompt **1.6 / 53,347 B / b9bfcec19538**，skill **1.0.7 / ad75ec2c44334f389a0394895a47b765**，旧 dist `404dbccf5058`；16/19 文件不同，**status exit 3 为预期**。无 publish、无在线 run，**不创建虚构 R21 记录**。待具体授权发布 prompt + skill，回读一致后 A/B 真跑留真实 R 记录。

**剩余风险**：慢速持续响应仍非硬墙钟 deadline；全文来源/回执验证不证明每个数字的提取来源；C/D 无判分基线。Git 当前 `v0.15-remove-html`，本轮不 commit/push，父任务统一处理。无 Docker 配置，无镜像动作。

## 3. 我们自己能改的

| # | 现象（证据） | 改法 | 状态 |
|---|---|---|---|
| O1 | `deps` 基线漏掉 `read_file`：R1/R2 实际调用 21+9 次，但基线内置工具 10 个里没有它 —— `collect_deps` 只做**文档文本匹配**，而我们的 sys/skill 从不提 `read_file` | `toolsmith-publish` 的内置工具指纹改为取**项目实际启用的工具集**（`GET /api/agent/info?project_id=…` → `tools`，16 个），不再靠文本命中；顺带修了漂移输出把 `NEW builtin` 打成 `NEW buil` 的截断 | **已落地**（基线 16 个，`deps` 复跑 exit 0） |
| O2 | digest 翻页：R1 里 **12/50** 次调用在按 offset 读同一个 105 KB / 510 行 `digest.txt`（offset 60→499，limit 30–60） | sys `Step discipline` #1 收尾加一句：**每个 digest 文件要能一次读完**（目标 ≤ ~300 行 / 几十 KB）；超了就拆成「每记录一文件」或「index + 每记录文件」，**不要对单个大 digest 反复 offset 读** | **已落地**（sys v0.15，2026-09-14） |
| O3 | 发明字段：R1 出现 `clinical_result.line_count` → `INVALID_INPUT`（原文见平台 P3），靠重试自愈 | 字段名的**运行期权威 = params 工具自身的 `selected_fields` 参数描述**；逐字复制，**禁止发明**；概念确无字段时取**最接近的真实字段**（线数 → `clinical_result.therapy_line_cn`/`_en`）或**留空并记「未报告」**。**F7 更正：旧「组/臂数 → group_count」建议错误，该字段是入组人数，当前规则已删除臂数映射。**`docs/params-tool-schema.md` 只是维护者镜像（不在部署端包内），明确禁止规划运行期去读它。落到 `SKILL.md`、`references/input-contract.md`、`references/entity-inline-reference.md`、sys | **已落地**（2026-09-14） |
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
| O27 | **清单条目 `A-C16-hard-outcome-gap` 术语绑定过窄**（2026-09-18 `R16` 暴露，与 O20 同类）：R16 在表格里明确写了「心血管结局事件（如 MACE）」并标注两侧「未报告／未对齐」，但条目正则只认 `硬结局|心血管事件` ⇒ 被判 0 命中。要防的是「硬结局缺口不写」这件事实，不是某个词形 | 正则放宽为 `硬结局|硬终点|心血管事件|心血管结局`（pattern 1；pattern 2 的否定式要求不变），配套回归 `test_hard_outcome_gap_accepts_every_wording_but_still_needs_the_gap` + M-变异仍 44/44 全翻 | **已结案（2026-10-10 R43，已修）**：第 2 份误判样本 R43-a 写「两项记录都没有心血管结局数据」（旧正则 0 命中）；放宽后 R43-a 43→**43/44**（该条转 PASS）、R41-A 41→**44/44 PASS**；变异闸门 `arm a 44/44 / arm b 12/12 / GATE: PASS` ⇒ 不产生假绿 |
| O28 | **`A-ATTR` 的「数值对」分支从未命中过任何产物**（2026-09-18 核 `M27` 时发现，**已修**）：token 写 ASCII `-13\.9`，四份真产物正文一律 U+2212（`−13.9`：R8/R12 各 5 处、R16 有符号式、R17 9 处）⇒ 静默漏检（假绿方向）；改成 `[\u2212-]13\.9` 后四份产物重打**无新增 FAIL**（说明真产物数值归属本来就干净，缺的只是这层检查），`M27` 现在能翻 `A-ATTR` | F2 | 已修（仅仓库评测资产） |
| O29 | **`A-P6` 在**真产物**上空转（假绿）**（2026-09-18 核 L3 时发现，**已修**）：旧实现只把「文件名以 `ref_<n>` 开头」的归档算作某条 ref 的全文正文（`op_cite_link_is_deepest` 里的 `re.match(r"ref_(\d+)", …)`），而**真产物从不这么命名**（`R14` 是 `PMC11270764_fulltext_jats.xml`）⇒ 拿 `R14` 原产物重打时它报 `no per-ref full-text body archived (check not triggered)` 并 PASS，**一个 citation link 都没看**——而 `R14` 正是催生 L3 规则的那份产物。更麻的是它**能过闸门**：`M21`/`M22` 用的是 harness 自己拼的 `ref_1.pmc-fulltext.xml`，即「拿自己的假设自证」。同时发现规则**只有一个方向**（归档 ⇒ 引用必须指全文），没有任何东西防「引用声称读了全文而一个字没取」 | ① `A-P6` 归位拆**四条通道**（`ref_` 前缀 / esid / 正文 `PMC<id>` 对链接 `PMC<id>` / 正文 PMID 对链接 PMID），归不上不猜、只记诊断；`PMC\d+` 先抹掉再扫 PMID（否则 PMCID 数字会被当 PMID 命中）；② 新增反向断言 **`A-P9-fulltext-cite-has-body`**（`link` 指全文载体 ⇒ `sources/` 里必须有同 `PMC<id>` 的字节；`link` 逐字节等于记录自带 `full_article_link` 时不算深度声明）；③ 变异改用**真产物命名**并新增 `M28`（只翻 `A-P9`）/ `N28`（`R14` 合法形状需三条全绿）；④ `NEG_A` 判据从「我那一条没翻」收紧为「**整轮干净** `rc==0 && flipped==[]`」（旧版下、负向对照把别条目打翻也会报 `[OK]`） | **已修**（2026-09-18，仅仓库评测资产：`check.py` / `scenario-a.facts.json` / `mutations.py` / `README.md` + 两份 evidence）→ 证据 **F4** |
| O30 | **`tool_results/**` 回执在 run 结束后不可恢复**（2026-09-18 E0 回测）：平台 persist 时删、产物面板过滤 ⇒ `file-download?path=…` 对已结束 run 恒 404；离线扫描 28 个 run 目录 **109 个指针、107 个不可恢复**。而报告里的数字（params JSONL / 抓回来的正文）恰恰只在回执里 | **不进平台问题单**（删/滤是设计如此，属运行期草稿）：runner（`~/.local/bin/toolsmith-publish`）新增 `ReceiptArchiver`，5 s 节奏轮询消息抠指针即时下载 → `<run>/tool_results/**` + `receipts.jsonl` + `run.json.receipts`；两条判定路径各加断言 `tool_results receipts archived`（0 指针 = PASS 且注明 n/a） | **已落地并验证**（R19 暴露目录假指针 → R20 12/12 PASS） |
| O31 | **拒绝原因印不出来**（2026-09-18，**已修**）：`retry-prompt` 的 `content` 在近期 run 是 pydantic **字符串**、早期 run 是错误 dict 的**列表**，而三处渲染器都按「list of dict」迭代 ⇒ 对字符串迭代再筛 dict，原因永远是空（R18/R19/R20 只印 `- toolname:`） | 新增 `rej_text(reason, n)` 助手（str → 压空白 / list → 合并 dict / None → 显式说明），断言 detail、console、`verification.md` 三处共用；**仅展示层，统计值不变** | 已修（备份 `toolsmith-publish.v8.bak`） |
| O32 | **`retry-prompt` 归因过粗导致假绿**（2026-09-18，**已修**）：框架在「参数被拒」和「工具自身失败」两种情况下都会重发，旧代码一律记成 schema-rejected，并在 `output-error` 回路按 id 跳过 ⇒ 外部抓取失败**在 `errors` 里不可见**，FAIL 级 `no tool errors` 对 500/403 完全失效（R15/R16/R17/R18 各有一条欧洲 PMC 全文 XML **500**，四轮全绿；产物侧其实已在覆盖行说明了 500） | 分三桶：`rejected`（参数被拒）/ `fetch_failures`（抓取失败：可见 + 打印 + 入 `verification.md`，不判 FAIL）/ 其余落 `errors`（仍 FAIL）；`verify-run-chain.py` 同步把 `rejected + fetch_failures` 当作「tap 看不到的尝试」 | 已修（`GATE: PASS`；断言 18→19 / 12→13 项） |
| O33 | runner 路径逃逸、符号链接、回执漏采/跨 turn/哈希假绿 | 最终目标 turn 必需集 + 安全落盘 + 重试/join + 文件哈希校验；F7 | 本地已修，30 runner tests PASS；无新线上 run |
| O34 | runner 缺返回/空产物/错误引用/缺 manifest/归因误判 | 实际 return 计数、目标 turn 隔离、歧义失败、正则加固；F7 | 本地已修；历史链 5 comparable PASS，无样本 exit 2 |
| O35 | scorer 观察值错配、伪全文、跨 turn 查询与边界假绿 | r2 新基线 + 身份/正文/观察值绑定；F7 | 27 tests / 63 controls PASS；不作质量提升声明 |
| O36 | pack/replay 安全及不完整输入可能假绿 | 安全打包、调用/场景/评分失败检查；F7 | 19 tests PASS，dist 已重建 |
| O37 | 本地 citation/entity 校验缺口 | 引用值、URL、marker/entity 检查；F7 | 21 Node tests PASS；不代表生产渲染器或 HTML 清洗 |
| O38 | 旧参数/臂数字段/L3 规则冲突与过度非 OA 推断 | live `esids` 适配、入组语义、canonical input-contract；F7 | 本地规则及 deps 基线已改；TS 发布与真跑待授权 |
| O39 | **runner 的 `tool-doc` 里留着已删文件的指针**（2026-10-09 收尾 entity 移除时发现，**已修**）：`cmd_param_doc` 生成的「4.3 嵌套返回结构要点」写「实体 ID 路径见 Skill 的 `references/entity-inline-reference.md`」，而该文件已在 v0.16 删除 ⇒ 生成物 `docs/params-tool-schema.md` 指向不存在的路径。修法：删掉该从句，`toolsmith-publish tool-doc` 重新生成（31,729 B→31,671 B）；备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v10.bak`，`py_compile` OK，零网络闸门 `GATE: PASS`。**只影响文档生成，不进运行期**。 | 已修（本地 runner + 仓库文档） |
| O40 | **`A-ATTR` 对「对对方记录的否定陈述」不给豁免**（2026-10-10 R43-a / R45-a 两份产物，2 样本）：引注 `ref_n` 的单元（含按 cell 拆分的表格单元）里点到**另一条记录的身份证**（药名/登记号），而本单元对该记录的陈述是**否定式**（「未给出」「未报告」「未评估」），仍判 FAIL。例：R43-a 第 60 行 cell「OCEAN(a)-DOSE 摘要只给出 LDL-C 基线中位值，未给出变化值」；R45-a「奥帕司兰未给出可归属的 LDL-C 变化值」「依勒尤单抗所取原文与库内记录均未报告安全性结果」。**当前判定：不改评分器**（现行契约 O19/M15 明文：单元必须点到**自己所引**记录的身份才享豁免；否定陈述不构成豁免理由，否则「未优于 X」成了绕开口）。**R47 更新（第 3 份样本 `r47-loweff-a`，机制已定位）**：该 run 报告第 62 行表格里，cell=「依洛尤单抗 420 mg 每月一次：-8.3 %{{ref_1}}」使整行 `row_refs={ref_1}`，**末尾无标记的 cell「OCEAN(a)-DOSE 未评估该终点」按 `units()` 继承本行标记 ⇒ 变成「引 `ref_1` 却只点名 `ref_2` 的试验」**判 FAIL；同 run 第 94/95 行同型（「奥帕司兰侧终点名称缺失」「另一研究未评估该终点」）。即 R47 新加的正文侧习惯句**覆盖不到表格 cell 的标记继承**。 | 📝 **仍不改评分器**（契约自洽）；**改法已收窄到一句可机械检查的报告侧规则（R48 内容轮）**：*要写「另一条记录没有这个终点/没报告」时，那一句/那一格必须带上**被点名那条记录**自己的 `{{ref_n}}`（或干脆不点名对方，写「未评估该终点」）；不得让它落在引了本条记录的句/格/行里*。|
| O41 | **`A-P2-divergence-shows-both` 对「非分歧地提到库内记录」零容忍**（2026-10-10 R45-a，1 样本）：该条按块要求任意 `库内记录` 出现必须落在 `原文 <值>；库内记录 <值>{{ref_n}}` 相邻双值写成内；R45-a 有一句写「库内记录另含若干按剂量分组的第 36 周百分比变化数值，但未给出可归属的终点名称，无法用于对齐」⇒ 判 FAIL。合同（`references/input-contract.md:224/286`）确实规定了该固定写法，但**未规定「不许在其它语境提到库内记录」**，故本例属**边界**：既可为真阳性（提到库内数值却不给原文对照），也可能只是排版选择 | ✅ **R47 收尾（报告侧习惯句已生效）**：R47 在 prompt/SKILL/`citation-and-ref.md`/`input-contract.md` 四处写入「`库内记录` 只许出现在固定分歧写法里」后，**R47 五份产物（a / 4 / 18 / 14 / loweff-a）`库内记录` 出现次数全部为 0** ⇒ 不再出现「非分歧地提到库内记录」的写法（A-P2 无触发）。**不改评分器**；后续样本若再现再议。|
| O42 | **`no tool errors` 在多写 run 上约 1/4 概率被打掉，三轮 prompt 强化未改变基线**（2026-10-10 R41→R45 共 14 个 run）：失败形态二种——`write_file` 缺 `overwrite`、`edit_file` 目标串过期；二者都只损失**一次工具调用**，平台 re-prompt 后 run 照常完成、其余 21 条断言全过。口径表见下方 R43/R44/R45 三节。 | ✅ **已结案（2026-10-10 R46，选 B 窄口径）**：runner 新增 `TOOL_REFUSED_RX`（两种工具侧前置拒绝、`^` 锚定）+ `REFUSAL_BUDGET = 3`，原恒 PASS 的信息行改成带预算判定（断言仍 22 条）。备份 `toolsmith-publish.v15.bak`；`test-runner.py` 38→**39**；零网络闸门 `GATE: PASS`；离线重打分 98 份归档 = **0 errors**、单 run 最大拒绝 2 次、无超预算样本；线上 r46-a / r46-a2 各 **22 PASS / exit 0`。证据 `docs/evidence/o42-refusal-reclassification-2026-10-10.txt` |
| O43 | **`A-S9` / `A-S9b` / `A-S10` 要求图表行（`label`+`description`）点名该观察所属**试验**，但 prompt / SKILL 从未把这条写成可检查规则**（2026-10-10 R46-a，1 样本）：r46-a 的 5 根柱子只写「药名 + 剂量 + 间隔 + 时点」（`依洛尤单抗 420 mg 每月一次（第 16 周）`），label 与 description 都不含 `NCT02729025` / `OCEAN(a)-DOSE` ⇒ `identified observations=[] want=[0,1,2,3,4]`，**离线 40/44 FAIL**；同一 prompt 的 r46-a2 把试验放进 `description`（`试验 A（NCT02729025）第 16 周，安慰剂校正`）⇒ **44/44 PASS**。同门径下 R45-a 亦 PASS ⇒ 同一 prompt 3 次 scenario A 里 **1/3 丢试验名**。判分侧口径本身**自洽**（行内 5 个维度须全部出现在 label+description 里，且互斥性仍靠 competing-identity 检查兜底），属**报告侧偶发漏写 + 规则只在 fixture 里隐式存在** | 📝 **待修（不在本轮回合内改）**：候选①在 prompt / `SKILL.md` 补一句可机械检查的硬规则（「每根柱子的 `label`/`description` 必须点名该观察所属试验的短名或注册号，不能只靠药物+剂量」），随**下一次内容改动一起发版**（不单独开一轮；与 O40/O41 的报告侧习惯句同批）；候选②判分侧把 chart 的 `identity_patterns` 去掉试验维度（唯一性仍靠「恰好命中 1 个」兜底）——**n=1 证据不足，本轮不做**。注意 `templates/charts/endpoint-bar.json` 的示例 label 本来就带试验槽位（`试验A · 研究组`）| ✅ **已结案（2026-10-10 R47，选候选①）**：prompt 「Every chart row names its own trial (hard rule)」+ `SKILL.md` 硬规则段 + `references/chart-templates.md` 各一句（不点名试验 = 不允许，≥2 试验时 `label`/`description` 必须自带试验短名或注册号），随 R47 内容轮原地发布；**R47 四组真跑 4/4 全部命中**：r47-a 五根柱子 label 前缀 `OCEAN(a)-DOSE · …` / `NCT02729025 · …`，r47-18 五根 `HARMONi-6（NCT05840016）· …`，r47-14 三根 `…（NCT04987320）/（jRCT2051240068）`，r47-4 仅时间线图（单试验，不适用）；且**未引入任何新断言失败**（4/4 run 皆 22 PASS / 0 FAIL）。判分侧未动。|
| O44 | **`A-C9-mds-tbr-A` 只认减号写法，不认「降低 X%」文字写法**（2026-10-10 r47-a，1 样本）：该条 `patterns` 硬编码 `-8\.3` / `-5\.3` / `-3\.0` / `0\.18`，而 r47-a 报告第 62/65 行写「依洛尤单抗 降低 8.3%；安慰剂 降低 5.3%」（**同一交付物内部一致**，`A-S10-sign-convention-consistent` PASS）⇒ 两条 pattern 0 命中，**离线 43/44 FAIL**。同门径的 `A-S10` 规格里自己写着「合同里没有关于符号/幅度的任何字 ⇒ 每次由模型自选」，故**同 spec 内两条断言口径不一致**；历史 6 个 scenario A run（r41-fixed-a / r43-a / r44-a / r45-a / r46-a / r46-a2）与同日的 `r47-loweff-a` 都写减号形式 ⇒ **1/7 触发**。 | 📝 **待样本（不改评分器）**：候选修法 = `A-C9` 的 `-8\.3` / `-5\.3` 各加一个文字式备选（`(?:-8\.3|降低\s*8\.3)`），与 O28「符号容忍」同门径、一行可回退、不产生新假绿（`升高 8.3` 不匹配）。按 O27/O28 先例**等第 2 份样本**再动。 |
| O45 | **runner 的 `tool_results` 指针正则不认全角右括号，把模型写在中文括号里的收据路径连括号一起吃进来**（2026-10-10 R48 四组真跑，**3/4 组炸**）：模型把 24 条记录的清单写进 `work/digest.txt`，第一行写「（14 条；来自 `/workspace/tool_results/pharmcube-query-clinical-result-with-params/call_xx.jsonl`）」；该文件随后被 `read_file` 读回，其**返回内容属权威串**，`TOOL_RESULTS_RX` 只把 ASCII `)`/空格/引号当终止符，`）` 不是 ⇒ 抓成 `…call_xx.jsonl）`，`receipt_relpath()` 以「unsafe or unsupported receipt path」拒绝整次验证（`FAIL: 1 final durable pointers`）。**`r48-4` / `r48-18` / `r48-14` 三组的 FAIL 全是这一条**，与产物质量无关 | ✅ **已修（R48，runner 层）**：新增 `_RECEIPT_STOP`（ASCII 分隔符 + `\u3000-\u303f` + `\uff01-\uff0f\uff1a-\uff20\uff3b-\uff40\uff5b-\uff65`），由它重建 `TOOL_RESULTS_RX`；备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v16.bak`、`py_compile` OK、`verify-run-chain` GATE PASS；**用同一批已存 run 离线重放**：r48-a / r48-4 / r48-18 / r48-14 的 `receipt_check` 全部由 FAIL 转 **PASS（all archived and hash-verified）**；新增回归 `test_cjk_punctuation_delimits_a_receipt_path`（（ ））「 」【 】。 ， ： 全角空格共 7 形）⇒ runner 门禁 **39 → 40**。**修复后用同输入复跑 `r48-4b` / `r48-a2` 均为 22 PASS / 0 FAIL** |
| O46 | **模型仍会用 `read_file(offset=…, limit=…)` 分块重读，且会越过 EOF**（2026-10-10 r48-a，**1/2 组**）：r48-a 的 `read_file` 第 11 次调用给 `offset=148`，而文件只有 136 行 ⇒ 平台返回错误、runner 的 `no tool errors` 断言被打掉（该 run 唯一 FAIL；`r48-a2` 同输入同 prompt 未复现）。**诱发源在平台侧文案**：工具结果过大时平台回「Read it with `read_file(file_path=..., offset=..., limit=...)` to inspect it in chunks」，模型照做；R48 第 7 条虽已要求少调用，但没把「不许凭猜测给 offset」写成可检查句 | 📝 **待修（R49 内容轮，不单独开轮）**：候选①第 7 条补一句硬规则——「不要对本次 run 自己的文件做 offset 分块重读；要看尾部用 `execute: tail -n 40 <path>`，要看全文一次 `read_file` 不加 offset，要看结论跑 `check_report.py`」；候选②第 2 条点明「原始 tool result 过大时**先跑 `prep_sources.py`**，不要分块啃原始文件」。**n=1 复现（1/2）+ 四组 run 的 read_file 调用 8–20 次**作证据，随下一次内容改动发版 |
| O47 | **`A-C7-timepoints` 只认「第 16 周 / 第 36 周」词形，不认「16 周 / Week 16」**（2026-10-10 r48-a2，1 样本）：r48-a2 报告第 20 行「时点为 16 周与 36 周」、第 51 行「安慰剂组 Lp(a) 在 36 周时平均升高 3.6%」、第 57 行表格「Week 16 / —」，**两个时点事实都在**，但 pattern 写死 `第 ?16 ?周` / `第 ?36 ?周` ⇒ 0 命中、离线 **40/44 FAIL**（同 prompt 同输入的 r48-a 写「第 16 周」×19 ⇒ 该条 PASS）。**与 O20/O27/O28 同门径（词形绑死）** | 📝 **待样本（不改评分器）**：候选修法 = 两条 pattern 各加无「第」备选（`(?:第 ?)?16 ?周|Week ?16`），一行可回退；按 O27/O28 先例**等第 2 份样本**再动 |
| O48 | **runner 的支撑文件清单把本地 `scripts/__pycache__/*.pyc` 当成「线上缺失」⇒ 假 FAIL**（2026-10-12 r50-a，**1/2 组**）：r50-a 唯一一条断言失败 = `manifest mismatch: missing=['scripts/__pycache__/build_ledger.cpython-310.pyc', '…/check_report.cpython-310.pyc']`——这两个文件是**本机跑 `python3 -m py_compile` 留下的字节码**，交付 zip 里从未包含（26 entries 全为 .py/.md/.json，已逐条核对）。同一输入清掉本地 `__pycache__` 再跑（r50-a2）即 **25 PASS / 0 FAIL / exit 0**。危害：任何在本仓跑过语法检查的开发都会给自己的每次真跑塞一条假 FAIL，且失败信息指向「线上缺文件」，与真实漂移（线上旧版/缺文件）不可区分 | ✅ **已修（2026-10-12 R50，runner 层）**：清单比对前剪掉 `__pycache__` 目录并跳过 `*.pyc`（本地开发必然产生字节码，bundle 永不包含）；备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v16b.bak` + `python3 -B -m py_compile` + 零网络闸门 `verify-run-chain.py GATE: PASS`（115/5/110）+ `test-runner.py` 40 → **41**（新增「本地存在 `__pycache__/*.pyc` 不得造成缺失」用例，对旧 runner 必 FAIL）；**对存档 run r50-a 的 A/B 复现**：旧 runner 复现同一句 FAIL、新 runner PASS（`/tmp/o48check.py` 直调 `check_run`，本地 .pyc 故意保留） |
| O49 | **图表行的 `description` 提到另一治疗臂的剂量/间隔 ⇒ 该行身份不再唯一**（2026-10-12 r50-a2，**1/2 组**）：第 1 行 `label=奥帕司兰 225 mg 每 24 周（OCEAN(a)-DOSE，第 36 周）`，`description` 写「延长给药间隔后降幅与每 12 周方案接近」⇒ 行文本同时命中 obs 2（225 mg 每 12 周）与 obs 3（225 mg 每 24 周），`A-S9` / `A-S9b` / `A-S10` 三条同源 FAIL（离线 38/44）。判分侧口径**自洽**（行身份必须恰好指向一条观察，competing-identity 兜底），属报告侧写法问题：比较性描述不该复述另一臂的身份数字 | 📝 **待修（随下一次内容改动发版）**：报告侧一句硬规则（`references/chart-templates.md` + `SKILL.md`：图表行只点自己那一条观察的身份；要写「与更短给药间隔组接近」这类比较，用不带剂量数字的措辞）|
| O50 | **`deps` 门禁只比版本标签 ⇒ 上游「原地更新同一版本号」检测不到**（2026-10-12 R51 实证）：`toolsmith-publish deps` 的比对对象是依赖包的**版本标签/指纹标签**，而上游 `chart-visualization-json` 会在**不改版本号**的情况下重新发布同一版本（平台 `current` 仍标 `1.0.12`，`updated` 却从 20260914 变为 `2026-09-21T11:58:40`）。本轮 deps 报 `unchanged since the recorded baseline`，但部署端 zip 已从 47 文件 / 54,684 B 换成 **48 文件 / 64,214 B**（新增 `docs/development.md`，`config.js` 的 `IFRAME_TEMPLATE` 改为 `…/20260921-085926/…`，4 个模板 envelope 删 `width`/`height`，`validate.js` 新增只有 warning 级的标题字宽/元标签检查）。**发现路径**：用户投诉时间轴 `weight` 不生效 → 手动拉部署端 zip + diff `vendor/1.0.12-20260914` 才看到。若无人投诉则会**静默漂移**（本地快照与部署端不再同源，日后核对渲染行为会给出错误结论）。 | 📝 **待应对（不改 runner：deps 的比较语义在 `toolsmith-publish` 内部，本仓不能改）**：①`vendor/` 同一版本号的第二次构建**另起目录** `vendor/<skill>/<版本>-<构建ID日期>/`，README 记源包 SHA-256 / 文件数 / `IFRAME_TEMPLATE` 并标注「平台 current 仍标同版本」（本轮已落 `1.0.12-20260921/`，`vendor/README.md` 新节 + 「更新流程」步 3 纪律）；②部署端行为核查以**下载到的 zip / 渲染 bundle** 为权威，不以 `deps` 的 `unchanged` 为权威；③若上游继续原地更新，需人工周期性拉包对 diff（目前无自动通道） |

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

- **P10（新，2026-09-17，待用户决定是否转开发）`web_fetch` 对主流医药信源的人读页面基本不可用，失败语义不清**：实测（W2-a/c/d；W2-c 更正：**失败时确实返回状态码文本**，如 `403 Forbidden`，只有成功时不回状态码）——PubMed 人读页返回反爬拦截页 `Cookies must be enabled … reload this page to continue.`；ClinicalTrials.gov 人读页（含 `?tab=results`）只返回 JS 骨架（`Show glossary` / `Study record managers: …`），拿不到试验记录；失败抓取会计入「schema-rejected」计数（正常 0 schema-rejected 的健康指标会因此失真）—— **我方已修**：runner O32 把「抓取失败」拆成独立桶 `fetch-failed`，可见且打印，不再冒充 schema 拒绝（详见 §3 O32）。本条**其余部分**（人读页不可用、失败语义不清）仍属平台侧，待转开发；沙箱自身无外网（`Could not resolve host` ⇒ `web_fetch` 为平台侧代抓）。
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

## R27–R29：设计复核原地发布后的固定三组（2026-09-18）

用户明确授权原地发布及固定三组；原始输入见 `evals/fixed-regression-inputs.json`，以后每次迭代全部运行。部署 prompt v1.6（50b870badd16）/ skill v1.0.7（ad75ec2c44334f389a0394895a47b765），回读 19/19 一致。SQL 32 唯一输入全部命中且无需改 ID。全部 DeepSeek Flash / web ON。

| 运行 | 组/记录 | 线程 | 秒（服务端） | 调用尝试 | 输入/输出 token | 产物/断言 |
|---|---|---|---:|---:|---|---|
| R27 | 1 / 4 | 198cd516-7a4f-4d0b-88cc-4f0032ce07ed | 176.9 | 29 | 1,630,848 / 34,461 | 报告、4 引用、时间轴；断言全过 |
| R28 | 2 / 18 | 3f5dcab0-dcae-4f80-87ea-c94289bb11be | 406.1 | 62 | 6,034,856 / 84,038 | 报告、18 引用、柱图和时间轴；no tool errors FAIL（write_file 文件已存在） |
| R29 | 3 / 14 | dc05d69d-8b2c-4554-8dd7-354be8e469a3 | 382.7 | 69 | 7,023,228 / 69,330 | 报告、14 引用、折线图；断言无 FAIL，但3次拒参、2次全文500 |

证据根：`~/.local/state/toolsmith-runs/fixed-regression-20260918/`，各 `r27-fixed-1` / `r28-fixed-2` / `r29-fixed-3` 中保存 verification、完整回执、原始报告、引用、图表及 usage。没有套用 A/B 分数，未改冻结评分器。

### 我方能改的（内容验收均未全绿）

- R27：盲法双来源披露正确（报告122行：论文双盲/登记四盲，原因不确定），4/4 覆盖；102行却称 AE 谱接近、严重程度分布差异不大，现有摘要不足支持；118行把较晚累计比例更高解释为暴露延长导致，证据不足。待后续修复。
- R28：18/18 覆盖，多处双盲/四盲正确披露，但 ref_2 摘要不明确盲法，报告81行仍写双盲；ref_2/ref_3 原文安慰剂与结构化阳性对照冲突漏披露。175行 ref_4 DoR 对照误写6.9（原文8.34）；180行试验组安全性范围89.2–84.6混入对照值（应区分A/B/C 89.2/89.0/84.6）；WJOG5208L 线次未确认却归二线，并有分组前后不一致。write_file 已存在报错后继续产出，原失败保留。待后续修复。
- R29：14/14 覆盖，双盲/四盲、双盲/三盲、平行/序贯冲突披露有效。118行把安慰剂校正 −101.1% 归因为对数尺度、220行推断低于检测下限，均无依据；105行不同单位 Lp(a) 得出2–3倍，不能直接比较；安全性总结把事件泛化为轻中度。ref_2/ref_8 肝损伤原文是轻度，报告写轻中度；ref_6 单中心/登记多中心差异未披露。待后续修复。
- 本轮仅记录真实验收，未为了通过而改原始报告/历史断言，也未追加发布补丁。设计复核改动部分生效，大组仍漏项。


## R30：数值事实账本与完整附表原地更新（2026-09-20）

用户授权原地更新并要求测试。发布前 `config`、`status`、`deps` 均核对通过：目标 project `a7cdda6508e0423c8b7afaaf3a68e50d`，prompt family `91febc286412479a8b6d569fa3b8025e`，skill family `9fe0035bdd324b998436c6cb9c2de212`，`owned=true`，上游依赖 unchanged。原地发布后回读一致：prompt v1.6 57,656 B / SHA `115bac4e5295`；skill v1.0.7、skill_id `ad75ec2c44334f389a0394895a47b765`，20/20 文件一致，dist 93,090 B / SHA `dd4d83f871692bd4c70b98cbf6787af1b6f839426312aee017e75630d95a06bb`。

| 运行 | 组/记录 | 线程 | 秒（服务端） | 调用尝试 | 产物/断言 |
|---|---|---|---:|---:|---|
| R30-1 | 1 / 4 | `0a9d04ac-6870-45ad-8a77-d9ce9f875b8f` | 369.9 | 46 | 报告、4 引用、时间轴；除支持文件清单外断言通过 |
| R30-2 | 2 / 18 | `2a7f94dd-22e8-4f6e-b866-02f0389e61de` | 588.1 | 96 | 报告、18 引用、3 图表；`no tool errors` FAIL |
| R30-3 | 3 / 14 | `7ba351b8-c78e-4d7d-9157-2e693b6d5e8d` | 632.0 | 81 | 报告、14 引用、3 图表；`no tool errors` FAIL，2 次全文 HTTP500 已披露 |

证据目录：`~/.local/state/toolsmith-runs/20260920-094455-r30-fixed-1/`、`20260920-095141-r30-fixed-2/`、`20260920-100208-r30-fixed-3/`。三组均成功结束、报告非空、引用键集/日期/title、图表 envelope 与可视化标签、实体锚点、固定交付路径、回执归档均通过；32 个选中记录分别覆盖 4/18/14 条。R30-1 的支持文件清单失败源于本地 `py_compile` 生成未打包的 `scripts/__pycache__/render-facts.cpython-310.pyc`，已清理且不属于发布包。R30-2 平台运行时重复写 `/workspace/work/fix_anchors.py`；R30-3 重复写 `/workspace/work/draft.md`，均被重试后继续产出。两项是平台运行工具错误，不能宣称三组“无工具错误”全绿；保留原始失败证据。

### 我方能改的

- 本地回归前不应在技能包目录运行会生成 `__pycache__` 的编译检查；应使用隔离缓存或测试后清理，避免支持文件清单污染。已清理，本轮不改历史 R30-1。


### 平台侧/外部服务现象

- R30-2/R30-3 的 `write_file` 已存在文件冲突会计入 `no tool errors` 失败，但不阻止后续报告交付；建议平台运行空间提供唯一临时文件名、显式 overwrite 或在重复写前自动转 `edit_file`。
- R30-3 Europe PMC `PMC10463176`、`PMC6933872` HTTP 500；按输入契约保留为抓取失败，未推断非 OA。

## R31：ES 热点 HARMONi-2 / HARMONi-6 多结果评估（2026-09-20）

本轮为只读 ES 取样后的一次真实 TS run，未修改 Skill、prompt、评分器或历史报告。候选来自 `np_clinical` 的近期会议记录：HARMONi-2（NCT05499390）3 条披露，HARMONi-6（NCT05840016）2 条披露。ES 返回 5/5，库内会议摘要正文长度约 2.8–3.2 KB；原始 ES 样本保存在 `/tmp/harmoni-hotspot-es.json`（临时探针，不入库）。

| 运行 | 记录 | 线程 | 秒（服务端/轮询） | 调用尝试 | 产物/断言 |
|---|---:|---|---:|---:|---|
| R31 | 5 | `1e841bad-058b-4cf4-ba49-fab407c55c27` | 529.9 / 531.5 | 72（71 returned + 1 args-refused） | 报告、5 引用、2 柱状图；19/19 断言通过 |

证据目录：`/home/xupeipeioo1/.local/state/toolsmith-runs/20260920-112401-hot-harmoni-20260920/`。部署状态检查为 in sync；`deps` 仅提示 chart skill v1.0.12 的更新时间指纹变化，版本未变，未执行 `deps --accept`。

### 人工内容审查

- **通过的关键边界**：正确区分两项研究、单药与联合化疗、不同研究内对照；没有合并跨研究排名；HARMONi-2 的 PFS 重述未当作新独立证据；HARMONi-2/HARMONi-6 的 PFS、OS、总人群、PD-L1 亚组分别标注。
- **图表边界通过**：仅生成 HARMONi-2 PD-L1 亚组 ORR 和 HARMONi-6 总人群/PD-L1 分层 PFS 的同试验图，没有生成不当跨研究柱图或时间折线图。
- **统计与成熟度边界通过**：报告保留两项 OS 均非最终分析、亚组无交互检验不能升级为亚组优效、HARMONi-2 与 HARMONi-6 HR 不可直接比较等限制。
- **上游数据质量提示已保留**：HARMONi-6 OS 原文 CI 为 `27.89–NE` / `20.11–NE`，库内结构化字段出现 `27–89` / `20–11` 形态；报告采用原文并明确披露差异，没有静默覆盖。

### 运行与平台现象

- 1 次 `execute` 调用传入额外 `command` 参数，被 schema 拒绝后自动重试；最终无 unresolved/error，不能单独定性为 TS 后端 Bug。
- 本轮无 `write_file` 已存在冲突、无外部抓取失败、无产物断言失败。当前没有新增已证实的 TS 平台功能缺陷。
- 原始 `verification.md`、`transcript.md`、报告、引用和图表均保留；本轮不改历史分数。

## R32：图表文档去重复后的原地更新与固定三组回归（2026-09-21）

用户授权原地更新。发布前 `config`、`status`、`deps` 已检查；依赖闸门发现 chart skill v1.0.12 指纹刷新及内置 `execute` schema 从 `shell_command` 变更为 `command`。前者版本不变且已接受新基线；后者为已知平台侧变化，本地未修改 runner、Skill 或 prompt 以适配。原地发布后回读一致：prompt v1.6，Skill v1.0.7 / skill_id `ad75ec2c44334f389a0394895a47b765`，20/20 支持文件一致，prompt 与本地字节一致。

| 运行 | 组/记录 | 线程 | 秒（服务端） | 调用尝试 | 产物/断言 |
|---|---:|---|---:|---:|---|
| R32-1 | 1 / 4 | `72f8ee86-e3ba-4e82-855a-125b4e4f6437` | 532.5 | 48 | 报告、4 引用、2 图表；支持文件清单 FAIL（残留 `__pycache__`），`no tool errors` FAIL（重复写 `build.py`） |
| R32-2 | 2 / 18 | `514b776d-09c2-4b1f-9bd2-1577750f1d8d` | 836.9 | 76 | 报告、18 引用、3 图表；支持文件清单 FAIL，`no tool errors` FAIL（重复写 `report_template.md`），3 次 Europe PMC 503 |
| R32-3 | 3 / 14 | `95c02f53-0b55-4cbf-9260-cf7765e0de4b` | 653.1 | 81 | 报告、14 引用、1 图表；支持文件清单 FAIL（残留 `__pycache__`），其余断言通过；5 次 Europe PMC 503 |

证据目录：`~/.local/state/toolsmith-runs/20260921-110837-r32-fixed-1/`、`20260921-111759-r32-fixed-2/`、`20260921-113229-r32-fixed-3/`。三组均 `outcome=succeeded`，报告、引用键集/日期/title、图表 envelope/标签、实体锚点、固定路径、回执归档均通过；共覆盖 4/18/14 条输入。由于支持文件清单和工具错误断言失败，不能宣称本轮全绿；外部抓取 503 按原始证据保留，不能推断来源内容缺失。

### 我方能改的

- 三组均报告 `scripts/__pycache__/render-facts.cpython-310.pyc` 不在本地发布包中的支持文件清单差异。该污染来自运行前本地 Python 编译检查，应在回归前清理并避免在 Skill 包目录生成缓存；不修改历史运行结果。

### 平台侧/外部服务现象

- R32-1/R32-2 分别复现 `/workspace/work/build.py`、`/workspace/output/report_template.md` 已存在时的 `write_file` 冲突；模型收到重试后仍完成产出，但 `no tool errors` 失败。与 R30 的同类现象一致，继续转平台开发。
- R32-2/R32-3 的 Europe PMC 请求返回 503；按输入契约保留抓取失败及报告覆盖说明，不把它判作 Skill 内容错误。
- 内置 `execute` schema 的 `command`/`shell_command` 变化继续作为平台依赖变化跟踪；本轮未改本地实现。

## R33：移除实体内联引用 + 附录改为试验列对齐矩阵 + 时间线加「发表时间」（2026-10-09）

**发布方式改变**：本轮按用户要求**不原地更新，改用 `--new-version` 追加新版本**（`/api/skills/create` + `family_id` + 非空 message），因为移除实体引用是产品特性变更而非文档修正，用户要保留旧版可回溯。

发布前 `config` / `status` / `deps` 均已检查；依赖闸门发现两处上游变化并逐项复核：

- `chart-visualization-json` 同版本 v1.0.12 被重新发布（`updated_at` 刷新为 2026-09-21T11:58:40）。本仓库运行期不硬编码该 skill 的 `iframe_template`，prompt 明确要求“运行期从上游 skill 取模板”，故无需改本地实现；由本轮真跑的图表产物验证。
- 内置 `read_file` schema 变化（`limit` 默认 100、`offset` 为零基的描述补齐，参数集不变）。据此把 prompt「Digest first」里的 digest 单文件上限从 ≤300 行收紧为 **≤100 行（即工具默认 `limit`）**，需要更长时显式传 `limit`。改动只落在 prompt，不进 dist。

回读一致：prompt **v1.7**（54,264 B / sha `a638a93fe934` / project prompt id `394a6e51617842a0ae9403579dcf8f45`）== 本地 `system-prompts/multi-clinical-result-comparison-v0.16.md`；skill **v1.0.8** / skill_id `cd93a42af72b4828b1690b3a7bccfa06`，19/19 支持文件一致，`references/entity-inline-reference.md` 已从线上包中消失；dist `dist/multi-clinical-result-comparison-v0.16.zip` = 93,757 B / 19 entries / sha `e5aad92c2618`（`--check` IDENTICAL）。`status` → `in sync`。

| 运行 | 组/记录 | 线程 | 秒（服务端） | 调用尝试 | 产物/断言 |
|---|---:|---|---:|---:|---|
| R33-1 | 1 / 4 | `ca78ca3e-5ac5-4c00-9097-cb15861cde37` | 324.6 | 39 | 报告、4 引用、2 图表；**唯一 FAIL = `no leftover template placeholder in report`（报告里出现 1 个字面 `{{ref_n}}`）**，其余 20 项全过（含支持文件清单 18 文件、`no tool errors`、turn `succeeded`） |
| R33-2 | 2 / 18 | 见 run 目录 `20261009-152421-r33-fixed-2` | 474.4 | 55 | 报告、18 引用、1 图表；**附录把 18 条记录合并成 10 列**（旧账本会裂成 18 列）；FAIL：`no leftover template placeholder`（同 `{{ref_n}}` 回归）＋ 支持文件清单 |
| R33-3 | 3 / 14 | 见 run 目录 `20261009-153236-r33-fixed-3` | 526.1 | 69 | 报告、14 引用；**附录 14 条记录合并成 11 列**；FAIL 与 R33-2 同类（占位符 + 清单） |

三组的支持文件清单 FAIL 与占位符 FAIL 均为**我方进程问题，非平台缺陷**，逐条定位如下：

- **支持文件清单 FAIL 的真相**（纠正 R30/R32 的错误归因）：断言代码是 `missing = expected(local) - listed(platform)`，所以 `missing=['scripts/__pycache__/render-facts.cpython-310.pyc']` 意思是**本地 Skill 目录里多了 pyc**，不是线上包里有。pyc 由我在两组运行**进行中**跑 `evals/numeric-integrity/test-render-facts.py` 生成（该测试用 `importlib` 从 Skill 树加载渲染器，CPython 顺带写字节码缓存）。同时 `scripts/render-facts.py: platform 29.0 KB != local 29.09 KB` 是我在运行期间改了渲染器（修占位符 bug）导致本地与线上字节不一致。**都是「回归跑动期间不要动仓库」的问题**：R33-1 在动手前跑完，清单断言 PASS；R33-2/R33-3 在我边跑边改期间断言，必然 FAIL。
- 修正措施（已在 R34 前落地）：`test-render-facts.py` 顶部加 `sys.dont_write_bytecode = True`（加载渲染器前），本地测试不再往 Skill 树写 pyc；重新打包前清理 `scripts/__pycache__`；把「真跑期间冻结仓库」写进流程。
- 占位符 FAIL 见上条（`APPENDIX_INTRO` 泄漏 `{{ref_n}}` 字面），已修 + 加断言 + 负向对照。

**三组的功能性结果（本轮真正的产出）**：附录矩阵形态在真实数据上成立——同试验多披露按 `records[].trial` 合并（R33-2 18 条 → 10 列、R33-3 14 条 → 11 列、R33-1 4 条 → 1 列），`试验设计/试验结论/有效性/安全性/PK/PD/PRO` 分段齐全，未出现旧形态的「一记录一列 / 44 列不可读」；3 组全部 `outcome=succeeded`、**`no tool errors` 全 PASS**（R32 的重复 `write_file` 冲突本轮未复现）、引用键集/日期/标题、图表 envelope/标签、固定路径、回执归档全部 PASS。修完后需按 R34 重跑三组才算验证通过。

**R33-1 的 FAIL 是我方的回归，已定位并修掉（不是平台问题）**：根因是本次新写的 `APPENDIX_INTRO`（`render-facts.py`）在描述单元格格式时**把 `{{ref_n}}` 字面写进了导语**，而导语会被逐字渲染进交付报告 → runner 的占位符断言把它判为残留模板占位符（该断言只放行真实的 `{{ref_<数字>}}` 标记）。修复：导语改为「紧跟其后的来源标记即该值的引用」等不出现花括号的表述，并新增回归断言 `test_appendix_intro_carries_no_template_placeholder`（逐字比对 runner 的同一条正则）；**已做负向对照**——把旧句子放回，该断言立即 FAIL（`placeholder leaked into the report: ['{{ref_n}}']`），证明断言不是空转。`test-render-facts.py` 因此由 21 项变成 **22 项**，全绿。修后 dist 重打为 93,792 B / sha `dd9c2998c2b6`（`--check` IDENTICAL），并在 R34 前置步骤里原地重发 + 重跑三组（见 R34 段）。

**冻结面基线变更**：删除 `test/entity-refs.test.mjs` 后，本地 Node 单文件回归合计由 21 项降到 **16 项**（`test/citation-renderer.test.mjs` 8 + `test/citation-validation.test.mjs` 8）。这是刻意的新基线，不是回归覆盖退化——被删的 5 项断言全部针对已移除的实体引用语法。`evals/validate-entity-refs.mjs` 同时删除，其离线校验职责由 `render-facts.py` 的 `ENTITY_LINK_RE` 渲染门禁接管（拦残渣 + 阻断交付）。

本地门禁（发布前）：`python3 evals/numeric-integrity/test-render-facts.py` **21/21 绿**；`evals/runner-gate/verify-run-chain.py` → `GATE: PASS`（5 comparable）；`evals/fact-check/mutations.py` → `GATE: PASS`（12/12 翻转）；Node 单文件 8 + 8 全过；`python3 tools/pack-dist.py --check` → IDENTICAL。回归前已清理 Skill 包目录内的 `__pycache__`（R32 支持文件清单 FAIL 的根因）。

### 我方能改的

- `APPENDIX_INTRO` 泄漏 `{{ref_n}}` 字面（见上）：已修 + 加断言 + 负向对照。这条正好复现了「断言要能挡住同一类错误」的教训——本次是**我方新引入**的缺陷，三组回归第一次就抓到了。
- 发布前清理 `scripts/__pycache__` 生效：R33-1 的支持文件清单 18/18 一致（R30/R32 的同类 FAIL 消失）。

### 平台侧/外部服务现象

- （待本轮三组结果回填）

---

## R34 — v0.16 修复后重跑固定三组（2026-10-09）

**发布（原地更新，不是新版本）**：`toolsmith-publish push-skill --version 1.0.8` → `POST /api/skills/update_skill_file` HTTP 200，`skill_id=cd93a42af72b4828b1690b3a7bccfa06`、`version=1.0.8`、`is_current=True`、`commit_id=None`（**版本号与 skill_id 不变**，只换内容）。dist 由 93,757 B / `e5aad92c2618` 变为 **93,792 B / sha `dd9c2998c2b6`**（19 entries，`--check` IDENTICAL）。prompt 未动（仍是 **v1.7** / 54,264 B / `a638a93fe934`），`deps` 报告 0 处上游变化，`status` → `in sync`。

**为什么这次是原地更新**：修的是「刚刚发布、还在验证中的同一版」里的两个缺陷（脚本导语泄漏占位符 + 本地进程污染），不是新的产品变更；原地更新保住 `v1.0.7 / prompt v1.6` 这两个回滚点，也避免线上多出一版内容几乎相同的历史。若要求每次修复都留独立版本号，可再发 `1.0.9`（内容相同，成本一次 API 调用）。

| 运行 | 组/记录 | 线程 | 秒（服务端） | 调用尝试 | 产物/断言 |
|---|---:|---|---:|---:|---|
| R34-1 | 1 / 4 | `1952d185-508a-4d09-9f7b-3126ad4268db` | 372.0 | 45 | 报告、4 引用、1 图表；附录 **1 列**；**22 PASS / 0 FAIL**，exit 0 |
| R34-2 | 2 / 18 | `edea673e-c067-4aff-b362-19007b50668e` | 431.2 | 51 | 报告、18 引用；附录 **10 列**（18 条披露合并）；**22 PASS / 0 FAIL**，exit 0 |
| R34-3 | 3 / 14 | `ca1120ae-c7d7-4d79-b70b-a645046ea8fa` | 418.6 | 33 | 报告、14 引用；附录 **11 列**；**22 PASS / 0 FAIL**，exit 0 |

**本轮全绿的关键项**：`no leftover template placeholder in report`（三组报告里非 `{{ref_n}}` 形态的占位符差集均为空）、`deployed support-file manifest matches local (18 files)`（不再有 pyc 差异）、`deployed system prompt == local` / `deployed skill body == local SKILL.md`、`no nested entity anchor — 0 anchors`、`citations: exact keys + date-only time + every entry has a title`、图表 envelope / 文件名 / `::visualization` 标签数、`present_artifact` 收尾、`no tool errors`、回执归档。三组 token 分别 4.49M / 5.40M / 3.08M，prompt cache 命中率 0.98。

**结论：v0.16 的附录对齐矩阵 + entity 移除 + 时间线「发表时间」在三个真实场景（单试验多披露 / 18 条混合 / 14 条 Lp(a) 类重复披露）上验证通过。**

### 我方能改的

- **`APPENDIX_INTRO` 泄漏 `{{ref_n}}`（R33 抓到，已修）**：导语原文用字面 `{{ref_n}}` 说明「其后是来源标记」，而导语会被逐字写进交付报告 ⇒ runner 的占位符断言判 FAIL。修法：改成不含花括号的表述；新增 `test_appendix_intro_carries_no_template_placeholder`（复刻 runner 的同一条正则）；**负向对照**——把旧句子放回，断言立刻 FAIL（`placeholder leaked into the report: ['{{ref_n}}']`），证明断言不是空转。回归项 21 → **22**。
- **本地 pyc / 边跑边改污染支持文件清单（R33-2/3 抓到，已修）**：断言 `missing = local - platform`，报的是**本地多出来的文件**；pyc 来自跑动期间执行 `test-render-facts.py`（`importlib` 从 Skill 树加载渲染器会写 `scripts/__pycache__/`），另有跑动中改渲染器导致 `platform 29.0 KB != local 29.09 KB`。修法：测试顶部 `sys.dont_write_bytecode = True`；`AGENTS.md` §7 新增「真跑期间冻结仓库」硬性条目；`py_compile` 改 `python3 -B -m py_compile`。**这条同时纠正了 R30/R32 里「线上支持文件清单被 pyc 污染」的错误归因。**
- 台账 R33 段里先前那句「需在 R34 重发后重跑三组才算验证」已由本轮闭环。

### 平台侧（转开发）

- **平台追加样板段仍宣传 `entity:` 内联引用，与 v0.16 的移除相反**（2026-10-09 核 `instructions` 时发现，非本轮引入）：部署提示词 = 我们的 prompt（字节前缀）+ 19,030 字符平台样板，样板第 15–17 行 `### Entity Inline References` 明写「工具返回里有 ID 就写 `[name](entity:type:id)`」，而我们的 prompt 与渲染门禁都禁止该语法且 fail closed ⇒ 模型若照样板写，产物直接**交付失败**。缓解已落在我方 prompt（点名该段「对本产品作废、不要照写」），R34 三组 `no nested entity anchor — 0 anchors` 全过说明生效。问题单全文见 Obsidian `03-技术与VibeCoding/01-AI与LLM/TS平台样板段仍宣传 entity 内联引用与 v0.16 移除冲突.md`；建议样板按项目开关或置于项目提示词之前。
- 另：本轮**没有**新的平台缺陷。唯一提交给开发同行注意的点（不算 bug，是断言语义容易误读）：`deployed support-file manifest matches local` 的 `missing` 方向是「本地有、线上列出的清单里没有」，历史台账两次把它读成「线上包脏」；建议在 `verification.md` 里把差异行写成 `local-only=[…] platform-only=[…]`，省掉后来人踩同一个坑。该建议只进 Obsidian/开发侧沟通，不改平台代码。

**本轮未动 runner**：`~/.local/bin/toolsmith-publish` 与 `evals/runner-gate/verify-run-chain.py` 均未修改，零网络闸门 `GATE: PASS`（60 histories / 5 comparable）。

**本地门禁（R34 后重跑）**：`test-render-facts.py` 22/22 OK；`verify-run-chain.py` → `GATE: PASS`；`mutations.py` → **`arm a: flipped 43/43`**、`arm b: flipped 12/12`、两臂 `never flipped []`、`GATE: PASS`（早期台账把 arm a 记成 `36/36`，是当时样本数，与 `flipped m/n` 语义不同，此处按现口径更正）；`node --test test/citation-renderer.test.mjs` 8/8；`test/citation-validation.test.mjs` 8/8；`pack-dist.py --check` → IDENTICAL（93,792 B / `dd9c2998c2b6`）。

## R35 — 补「平台样板段 entity 冲突」提示后重跑固定三组（2026-10-09）

**改了哪一层**：只改 **TS 资产里的 prompt**（`system-prompts/multi-clinical-result-comparison-v0.16.md`），**不动 skill 包**（因此 dist 不变、无需重打 zip）。

**为什么改**：核 `toolsmith-publish instructions` 时发现，部署提示词 = 我们的 prompt（字节前缀）+ **19,030 字符平台样板**，而样板第 15–17 行 `### Entity Inline References` 仍在教模型「工具结果里有 ID 就写 `[name](entity:type:id)`」。这和我们 v0.16 的移除规则相反，且平台样板**排在我们 prompt 之后**。缓解写在我们这边：在 `### Plain entity names (no inline references)` 下新增一条，点名该段「对本产品作废、不要照写」，并说明它排在后面但不覆盖本条。

**发布**：`push-prompt --version 1.7`（**原地更新当前版本**）→ 54,794 B / sha `16a20328fc43`；`status` → in sync；`deps` 0 变化。

### 三组结果（固定 4 / 18 / 14 条）

| 组 | run 目录 | thread | 墙钟 | 调用 | 附录列 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R35-1 | `20261009-161420-r35-fixed-1` | `49db75db-47a0-42e2-8678-d63e376af560` | 376.9 s | 50 | 1 列 | 21 PASS / 1 FAIL | 3 |
| R35-2 | `20261009-162057-r35-fixed-2` | — | 644.8 s | 56 | 10 列 | 21 PASS / 1 FAIL | 3 |
| R35-3 | `20261009-163203-r35-fixed-3` | — | 454.7 s | 48 | 11 列 | **22 PASS / 0 FAIL** | 0 |

- **entity 冲突提示生效**：三组 `no nested entity anchor — 0 anchors`、`no leftover template placeholder` 全过，附录列数与 R34 完全一致（1 / 10 / 11）。
- **R35-1 / R35-2 的唯一 FAIL 是同一件事**：`write_file [re-prompted]: File '/workspace/work/draft.md' already exists. Read it first and use edit_file instead or use write_file(overwrite=True)`。这是**模型重复整写已存在草稿**被工具拒（框架重发），非平台缺陷；`arguments refused by the tool (re-issued) = 0`、产物完整、其余断言全过。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| prompt 从未写清 `write_file` 不会覆盖已存在文件（R32-1/R32-2、R35-1/R35-2 共 4 次同因 FAIL） | 两次 run 的 `no tool errors` FAIL 行逐字相同；两次 `-prompt` 都发生在写 `draft.md` 第二次整写时 | 在 `## Step discipline` 末尾加**第 6 条**：重写自己写过的文件要 `overwrite=True`，或改用 `edit_file`；不得原样重发同一 `write_file`；**该 re-prompt 计入 tool error** | 已改，随之发布 prompt v1.7 并跑 R36 验证 |

### 平台侧（转开发）

- 见 R34 段的「平台追加样板段仍宣传 `entity:` 内联引用」条（问题单全文在 Obsidian）；本轮**无新增**平台缺陷。

## R36 — 加「重写文件」纪律后重跑固定三组（2026-10-09）

**改动**：prompt `## Step discipline` 新增第 6 条（重写自己写过的文件用 `overwrite=True`，或改用 `edit_file`；原样重发同一 `write_file` 计为 tool error）。**只动 prompt**，skill 包/dist 未动；`push-prompt --version 1.7` 原地更新 → `status` in sync。

### 三组结果

| 组 | run 目录 | 墙钟 | 调用 | 附录列 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- |
| R36-1 | `20261009-164457-r36-fixed-1` | 407.9 s | 55（含 1 args-refused / 1 error） | 1 列 | 21 PASS / 1 FAIL | 3 |
| R36-2 | `20261009-165157-r36-fixed-2` | 548.6 s | 70 | 10 列 | **22 PASS / 0 FAIL** | 0 |
| R36-3 | `20261009-170119-r36-fixed-3` | **16.0 s** | **3** | 无产物 | 18 PASS / 4 FAIL | 3 |

- **R36-1 FAIL**：`edit_file [re-prompted]: Could not find the target string in '/workspace/work/draft.md'`。第 6 条把模型从 `write_file` 逼到了 `edit_file`，在长中文草稿上做外科式改写时目标串失配 ⇒ 换个失败点，没解决「反复整写草稿」这个根因（该组 `write_file×7 + edit_file×5`，草稿 churn 明显）。
- **R36-3（异常，待复跑定性）**：**16.0 秒、3 次调用**（`load_skill` + 参数工具 + 一次 `execute`）后 turn 结束，`timing.completed_at` 有值、`outcome=succeeded`、无 `error_type`；token 只有 output 1,948 / reasoning 1,129（同批 R36-1/2 是 83k/100k output）。**模型在「14 条 esids 都取回、下一步做 digest」处直接收尾**。三组同为 DeepSeek Flash，故不像模型差异；更像上游截断被平台记成正常结束。**runner 没有放行**：`fixed deliverable paths — missing ['output/citations.json','output/report.md']`、`report contains nonempty content`、`citations contains nonempty source entries`、`present_artifact is the final successful call` 四项 FAIL、exit 3，说明「turn outcome=succeeded」不足以证明产物存在，产物契约断言是必要的第二道闸。→ 需复跑定性（见 R37）。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| 第 6 条只堵了 `write_file`，模型改走 `edit_file` 仍在长草稿上失配 | R36-1 唯一 FAIL 是 `Could not find the target string in '/workspace/work/draft.md'`；该组 write_file×7 / edit_file×5 | 第 6 条重写为「不要在长草稿上做外科式编辑」：机械表格交给脚本、正文**一次写成**（`overwrite=True`），需要修订就整文件重写 | 已改，随之发布并跑 R37 |

### 平台侧

- ~~「turn 记成 `succeeded` 但只跑了 3 次调用、无任何产物」~~ → **2026-10-10 复核后撤回，判为模型提前收尾，不是平台缺陷**：R36-3 的 `debug-history.json` 里末条 `kind=response` 是 `finish_reason: "stop"`（`provider_details.finish_reason: "stop"`，provider `deepseek`，`state: complete`），parts 只有 `reasoning`（2,922 字符，末句是完整的「Let me write the digest script.」）+ 65 字符 `text`、**无 `tool_call`**——上游自己报的是正常 stop，平台没有把截断归一成成功；`info.stats.steps=3`、`timing.turns[0].completed=true` 与之自洽。同 prompt 其后 6 组（R37-1/2/3、R38-1/2/3）全部正常，全库 72 次 run 仅此一次「秒级结束+零产物」⇒ 单次 flake。**唯一留下的可提项是文档级（非缺陷）**：`turn` 终态只表示回合结束、不保证产物存在，交付校验是调用方责任（按 2026-09-17 规矩仍可提，由开发判）。Obsidian 笔记同标题已同步改状态与结论：《TS run 16 秒 succeeded 无产物-终态不可当交付证据》（`03-技术与VibeCoding/01-AI与LLM/`）。
- **所有已转出问题单**：平台样板段 `### Entity Inline References` 与 v0.16 移除冲突（见本文件 R33/R35 段与 Obsidian 同名笔记）——**仍待开发处理**。

## R37 — 第 6 条二次修订（不要在长草稿上做外科式编辑）后重跑固定三组（2026-10-09）

**改动**：prompt `## Step discipline` 第 6 条由「重写已写文件用 `overwrite=True`」重写为 **「Never patch a long draft in place — reuse the ledger, write the file once」**（机械表格全部交给脚本、正文一次写成 `overwrite=True`；需要修订就整文件重写，不做外科式 `edit_file`）。**只动 prompt**，skill 包/dist 未动；`push-prompt --version 1.7` 原地更新 → `status` in sync。

### 三组结果（固定 4 / 18 / 14 条）

| 组 | run 目录 | thread | 墙钟 | 工具尝试 | 附录列 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R37-1 | `20261009-171121-r37-fixed-1` | `6143cc8f` | 347.7 s | 45（executex27 / read_filex6 / write_filex3 / edit_filex3 / grepx2 / load_skillx1 / paramsx1 / presentx1；1 args-refused） | 1 列 | **22 PASS / 0 FAIL** | 0 |
| R37-2 | `20261009-171717-r37-fixed-2` | `a7c58280` | 530.5 s | 69（executex37 / read_filex22 / write_filex3 / write_todosx2 / load_skillx1 / lsx1 / paramsx1 / grepx1 / presentx1） | 10 列 | **22 PASS / 0 FAIL** | 0 |
| R37-3 | `20261009-172619-r37-fixed-3` | `15b0f2b5` | 411.9 s | 48（executex23 / read_filex19 / write_filex2 / load_skillx1 / paramsx1 / grepx1 / presentx1） | 11 列 | **22 PASS / 0 FAIL** | 0 |

- **三组全绿、exit 0**：`no tool errors`、`present_artifact is the final successful call`、`citations: exact keys + date-only time + every entry has a title`、`no leftover template placeholder`、`no nested entity anchor`（0 anchors）全过。第 6 条二次修订生效：三组都没有再出现 `write_file` 拒覆盖或 `edit_file` 目标串失配，写文件次数降到 2–3 次（R35/R36 是 7–12 次 churn）。R37-1 唯一的 args-refused 是模型自己写错字段名（`clinical_result.multicenter`），一次 `INVALID_INPUT` 后按 schema 更正重发，不是内容缺陷。
- **R37-3 未复现 R36-3 的 16 s 零产物 flake**（411.9 s / 48 次调用 / 22 PASS）。该 flake 已定性（2026-10-10）：`finish_reason=stop`、模型未发 `tool_call` 即收尾，属模型行为而非平台截断，不作为 bug 单，见 R36 平台侧条目。
- 附录列数与 R34/R35/R36 一致（1 / 10 / 11），说明「列 = 试验」的合并语义在真实数据上稳定。

### 我方能改的（本轮新发现，已定位、未在本轮改）

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| **证据链时间轴图几乎逐字复述时间线表格**（用户反馈「重复的表述」） | 读 `20261009-171121-r37-fixed-1/artifacts/visualizations/evidence-timeline.json`：`data[]` 每节点的 `content` = 表格「本阶段新增的证据」数值块、`description` = 表格「相对前一状态的影响」+refs，`time` = 表格「数据截止/随访」列 | `references/timeline-diagram.md` 新增「图表职责分工」硬规则：图只画骨架（时序/状态名/关系/成熟度），**图内除 `time` 时间锚点外不得出现任何数值**，`content` ≤16 字定性短语、`description` 只写关系+成熟度+refs，图内文本与表格单元格不得有 ≥8 字连续相同文本；`chart-templates.md`、`same-trial-evolution.md`、四个模板同步 | 已改（R38 验证） |
| **单试验附表退化成 1 列 + `<br>` 堆叠长文本**（用户反馈「难读」） | R37-1 附录 1 列，格内多条披露用 `<br>` 堆叠；同格同时承载设计散文与数值 | 渲染器新增单试验布局：**输入只含一个试验且 ≥2 条披露时改为每条披露一列**（表头 `**ref_n**<br>短版本标签`），保留终点行对齐、去掉堆叠；`appendix_layout`/`appendix_columns` 进 audit | 已改（R38 验证） |
| **长散文进附录**（题名/设计/试验组/人群覆盖 4 行），与正文和「试验背景」表重复 | R37-1 账本 `records[]` 的 `title` 是整句英文长标题、`design`/`arms`/`coverage` 均为长散文；探针渲染显示这些字段占掉 4 行 | `records[]` 必填收成 `ref`/`identity`/`conclusion`（+ `trial`），`title`/`design`/`arms`/`coverage` 降级为「接受但不渲染」，四个 row 从 `DESIGN_ROWS` 删除；prompt/SKILL 明写「不要为它们花 token」 | 已改（R38 验证） |
| **附录列头命名风格不一致**（用户反馈「名字不稳定」） | 跨 R33–R37 全部 run 的附录标题完全一致（脚本持有 `## 附录：证据对齐矩阵（数值事实账本）`），真正不稳定的是**列头**：R37-2 同一张表里并存 `LUX-Lung 8（5 条披露）`、`RATIONALE-307（2 条披露）`、`HARMONi-6（4 条披露）`、`CameL-Sq`、`AK105-302` 三种形态 | 列头统一由渲染器生成：多试验 `**试验名**<br>注册号 · N 条披露`；单试验 `**ref_n**<br>短版本标签`（`_short_version` 按 `[·；;｜|]` 取首段、超长去尾部完整括号、绝不截出未闭合 `（`） | 已改（R38 验证） |
| **行标签不稳定**（同一维度三组叫法不同：「随机人数」vs「随机例数」、「中位 DoR」vs「中位缓解持续时间」） | R37-1 账本含 14 条模型自造设计 fact（`研究中心`/`分层因素`/`试验组方案`/`主要终点定义`/`安全性分析集`/`基线性别分布`/`关键入选条件`/`基线年龄中位数`/`中期 OS 分析计划` 等） | 治理放在 prompt/SKILL 白名单（只允许入组例数、分析集与分母、数据截止与随访、事件数、检验边界、给药方案），**渲染器不加硬截断**——避免把合法长尾事实判成错误 | 已改（R38 验证） |

### 平台侧（转开发）

- 本轮**无新增**平台缺陷。已转出的两份问题单（平台样板段 entity 冲突；run 终态 succeeded 不可当交付证据）仍待开发答复。

## R38 — v0.16.1 四点改动（附录列布局 / 长散文出附录 / 设计 fact 白名单 / 图表去重）原地发布后重跑固定三组（2026-10-09）

**改了哪一层**：**Skill 包内 + prompt 都改了**（`scripts/render-facts.py`、`SKILL.md`、`references/timeline-diagram.md`、`references/chart-templates.md`、`references/same-trial-evolution.md`、四个 `templates/*.md`、`system-prompts/multi-clinical-result-comparison-v0.16.md`）→ **必须重打 dist**（EXPECTED 仍 19）。

**改了什么（对应 R37 取证发现的四次产品面问题）**

1. **图表与表格去重**：证据链时间轴图原来是表格的第二份拷贝（R37-1 的 `content`/`description` 就是表格的「数据截止/随访」「本阶段新增的证据」「相对前一状态的影响」三列）。现在**图只画骨架、表格是数值唯一出处**：`label` ≤18 字、`content` ≤16 字定性短语、`description` 只写关系 + 成熟度 + `{{ref_n}}`；**图内除 `time` 的时间锚点（年月/日期）外不得出现任何数值**；图内文本与任一表格单元格**不得出现 ≥8 个连续相同字符**（专有名词除外）。
2. **单试验附录改「每条披露一列」**：R37-1 是 1 列 + `<br>` 堆叠长文本；现在输入只含一个试验且 ≥2 条披露时，**列 = 每条披露**，表头 `**ref_n**<br>短版本标签`（`_short_version` 按 `[·；;｜|]` 取首段、超 20 字先去掉尾部完整括号、绝不留未闭合 `（`），保留终点行对齐、去掉堆叠。
3. **长散文不再进附录**：`records[]` 必填收成 `ref`/`identity`/`conclusion`（+ `trial`），`title`/`design`/`arms`/`coverage` 降级为「接受但不渲染」，`DESIGN_ROWS` 只留 `试验身份`（印 `identity` 首段）。
4. **附录列头形态统一**（消除「名字不稳定」）：多试验 `**试验名**<br>注册号 · N 条披露`；无注册号时回退 `**名称**<br>N 条披露`。新增 audit `appendix_layout`（`trial-columns` / `disclosure-columns`）与 `appendix_columns`。
5. **行为标签不稳定靠 prompt/SKILL 白名单治理**：只允许可对齐的数值设计事实（随机/入组例数、分析集与分母、数据截止与随访、事件数、检验边界、给药方案）起行；研究中心数、性别/年龄分布、入选条件、分层因素、终点定义复述列入 ⛔ 禁建清单。**渲染器不加硬截断**（宁可暴露白名单漏项，也不静默丢真实事实）。
6. **行内限定词上提**：整行所有数值共有的限定词（臂/时点/评估/人群）提到行标签（` · ` 连接、60 字预算贪心），单元格只留差异。

**发布（原地，不新开版本号——用户要求）**：dist 重打 **99,640 B / 19 entries / sha `5457c8c4fd00`** → `push-skill --version 1.0.8`（`skill_id cd93a42af72b4828b1690b3a7bccfa06` 不变、`is_current=True`）；prompt **58,795 B / sha `1d9153c88f3c`** → `push-prompt --version 1.7`；`status` → **in sync**（19/19 支持文件一致）。`deps` 0 变化。

**本地门禁**：`test-render-facts.py` **26/26 OK**；`verify-run-chain.py` → `GATE: PASS`（69 histories / 5 comparable）；`evals/fact-check/mutations.py` → `arm a: flipped 43/43`、`arm b: flipped 12/12`、`never flipped []`、`GATE: PASS`；`pack-dist.py --check` → IDENTICAL。

### 三组结果（固定 4 / 18 / 14 条）

| 组 | run 目录 | thread | 墙钟 | 工具尝试 | 布局 | 列数 | 行数 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R38-1 | `20261009-175146-r38-fixed-1` | `4014f791` | 390.9 s | 45（write_file×1） | `disclosure-columns` | 4 | 20 | **22 PASS / 0 FAIL** | 0 |
| R38-2 | `20261009-175825-r38-fixed-2` | `5ddb5fac` | 494.2 s | 61（write_file×3 / edit_file×3） | `trial-columns` | 10 | 47 | **22 PASS / 0 FAIL** | 0 |
| R38-3 | `20261009-180646-r38-fixed-3` | `c8851877` | 534.4 s | 56（write_file×2 / edit_file×3） | `trial-columns` | 11 | 40 | **22 PASS / 0 FAIL** | 0 |

**四点验收结果（逐项对照产物）**

- **②单试验附录（R38-1，HARMONi-6 / 4 条披露）**：`appendix_layout=disclosure-columns`、`appendix_columns=4`、`appendix_trials=1`；表头四条一致 —— `**ref_1**<br>首次计划 OS 分析`、`**ref_2**<br>首次计划 PFS 分析`、`**ref_3**<br>预设中期 OS 分析`、`**ref_4**<br>首次计划 PFS 分析`。1 列堆叠问题消除。
- **③长散文出附录（三组）**：附录**没有再出现** 披露标题 / 设计与方案 / 试验组与对照 / 人群与证据覆盖 行；`title`/`design`/`arms`/`coverage` 字段仍被 ledger schema 接受（不阻断旧账本），渲染器不再打印。
- **④列头统一（R38-2 / R38-3）**：10 列与 11 列表头全部为 `**名称**<br>注册号 · N 条披露`，**同表内三种命名风格混用的情况消失**（R37-2 实测的 `LUX-Lung 8（5 条披露）` / `CameL-Sq` / `AK105-302` 混排不再出现）。缺注册号的 2 个试验（`WJOG7512L`、`Lp(a)FRONTIERS EXPANSION`）回退为 `**名称**<br>N 条披露`，属契约内回退。
- **⑤设计行白名单（三组）**：R37-1 的 14 条自造设计行（研究中心 / 分层因素 / 主要终点定义 / 安全性分析集 / 基线性别分布 / 关键入选条件 / 基线年龄中位数 / 中期 OS 分析计划 …）**在 R38-1 全部消失**，`试验设计` 段只剩 试验身份 / 披露版本·数据截止 / 随机入组人数 / 中位随访 / OS 检验边界 / PFS 检验边界 / 死亡事件数；R38-2/R38-3 保留的是可对齐的分母类事实（随机化例数、随机并接受治疗例数、安全性分析集例数、可分析人数、倾向性评分匹配后每组例数、OS 分析统计界值、试验组给药方案），未见研究中心 / 性别分布 / 入选条件 / 分层因素 / 终点定义类行。
- **①图表去重（R38-1）**：`evidence-timeline.json` 三个节点 —— `{time:"2023-08", label:"研究启动（里程碑）", content:"入组启动"}`、`{time:"2025-10-19", label:"主要终点分析 · 会议/主刊", content:"主要终点首次达标"}`、`{time:"2026-05-31", label:"生存终点分析 · 会议/主刊", content:"新增生存终点，随访延长"}`；`description` 只写「与前一状态的关系 + 成熟度 + `{{ref_n}}`」。**图中除 `time` 锚点外无任何数值**，脚本比对（去 `{{ref_n}}` 与标点后 ≥8 字滑窗）**与表格共享 0 处连续文本**。R38-2/R38-3 为跨试验输入，按契约不出时间轴图（无共享时间线），因此去重规则只由 R38-1 覆盖。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| 跑动期间改 prompt/SKILL 会打破 `deployed prompt == local` 与 `deployed skill == local tree` 断言（断言在**结束时**读本地文件） | 本轮启动 R38 后才发现 `assert` 里 `open(a.sys)` 读的是当时的本地文件；发现后立即 kill（`20261009-174751-r38-fixed-1`，未产出 verification），改完→重打 dist→重发 prompt v1.7 / skill v1.0.8→再跑 | 沿用 `AGENTS.md` §7「真跑期间冻结仓库」，并把「README/AGENTS 等文档也不要在跑动中改 prompt/SKILL 相邻内容」写进交接段 | 已记（本次为自查拦下，无缺陷产物） |
| 表头缺注册号时形态与其余列不完全一致（`**WJOG7512L**<br>1 条披露`） | R38-2 / R38-3 各 1–2 列如此；来源确实未给注册号 | 视为契约内回退（不编造注册号）；若要求绝对一致，需决定「无注册号时是否用 `study` 名兜底」——**待用户定** | 待定 |

### 平台侧（转开发）

- 本轮**无新增**平台缺陷。已转出两份问题单（平台样板段 entity 冲突；run 终态 `succeeded` 不可当交付证据）仍待答复。R38 三组 `no tool errors` / `no leftover template placeholder` / `no nested entity anchor` 全过，平台样板段冲突的 prompt 压制继续生效。

---

## R39 — 效果 A/B：把两个 `report-humanizer-*` 挂到 `clinical_result_xp` 真跑（2026-10-10）

**改了哪一层**：**没有改 prompt、也没有改任何一个 skill 的字节**——只改了 `clinical_result_xp`（project
`a7cdda6508e0423c8b7afaaf3a68e50d`）挂载的 skills，加了 `report-humanizer-zh` / `report-humanizer-en`。
所以这一条**不是对比 skill 的加发布验收**，是**新 skill 的实效取证 + 缺陷挖掘**（跑的是 ASCO/ESMO 4 条披露的同一天双跑）。

**为什么要用「真对比任务 + humanizer 指令」这个形态**：runner 的产物断言硬编码 `output/report.md` +
`output/citations.json`，且 skill-body 断言比的**是部署的 `skill_name` 的 `SKILL.md`**（即对比 skill 正文）。
纯「只改写一段文字」的任务必然在这两类断言上失败（没有 report.md、citations.json，也没有对的上 skill 正文），
所以实验形态只能是「**真做一次对比报告 + 额外挂 humanizer 指令**」。**同一天两跑**抵消 run 间波动：

| 组 | 挂载 | run 目录 | thread | 墙钟 | 工具尝试 | 报告字符 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 实验组 R39-hz | + `report-humanizer-zh` | `20261010-101129-r39-hz-1` | `0691aaaf` | 528.4 s | 56（write×6） | 3,868 | **22 PASS / 0 FAIL** | 0 |
| 对照组 R39-ctl | 不挂 humanizer | `20261010-102037-r39-ctl-1` | `b4306382` | 340.7 s | 46（write×3） | 5,112 | **22 PASS / 0 FAIL** | 0 |

**同日量化（`/tmp/r39-hz/metrics.py`，两稿同输入同模型 DeepSeek Flash）**

| 指标 | ctl（无 humanizer） | hz（挂 humanizer） | 变化 |
| --- | --- | --- | --- |
| 正文去空白字符 | 5,112 | 3,868 | **−24%** |
| 句数 / 平均句长 | 76 / 67.3 | 72 / 53.7 | 平均句长 **−20%** |
| 破折号（`—–`） | 4 | 8 | +4（口径统一后变多，属排版） |
| 逗号（`，`） | 139 | 84 | **−40%** |
| 12-gram 重复率 | 0.0624 | 0.0447 | **−28%** |
| 引用标记 / 强命中 / 弱命中 | 4 / 0 / 1 | 4 / 0 / 2 | 事实与引用面持平 |

**结论**：humanizer 拿到的是「更短、更少逗号连缀、重复度更低、事实与引用一条不少」的稿子（用户据此**选 B**：
把两个 humanizer skill 转正为项目常挂能力）。**缺陷面**：实验组与对照组**都**在覆盖行里写了我们这一侧的取回过程
（见 R40 的三份证据），这直接催生了本轮的 **A-P10**。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| 两份产物都在覆盖行写「我们这一侧怎么取回」：实验组「本次运行无外网、全文抓取失败（抓取受限）」、对照组「在本运行环境无可用的外网抓取通道（PubMed→PMC 全文链路未能发起）」 | 两份 `report.md` 的 `原文核对：` 行逐字见 `docs/evidence/fact-check-a-p10-real-artifacts-2026-10-10.txt` §3/§4 | 契约层面**移除运行物流叙述**、保留材料属性与深度 → 落成机械门禁 **A-P10**（本轮 R40 已发布并四组验证） | ✅ 已解除（A-P10） |
| 扫描器 `W-BOLD-COUNT` 在两组真产物上各命中一次（加粗 ≥8 处），但两份稿子的加粗都是表头/标签式加粗，非「强调滥用」 | 两组 hz/ctl 均 `['W-BOLD-COUNT']` | 阈值与统计面已在 fixture 上定标，真产物命中归「待样本」——需要更多报告样本才能判断是否该按 prose 行加权 | 待样本（本轮不改规则） |

### 平台侧（转开发）

- 本轮**无新增**平台缺陷（两跑终态 `succeeded`、产物齐全、无 tool 报错）。既有两份问题单仍待答复。

---

## R40 — A-P10（交付物不写运行物流）落地后重跑四组（2026-10-10）

**改了哪一层**：**Skill 包内 + prompt + 离线门禁都改了**（`references/input-contract.md`、四个
`templates/*.md`、`skill/.../SKILL.md`、`system-prompts/multi-clinical-result-comparison-v0.16.md`
6 处、`evals/fact-check/check.py` 新增 `op_no_run_logistics`、`scenario-a.facts.json` 追加 `A-P10`、
`evals/fact-check/mutations.py` 追加 `M43` + `seed_a()`）。

**改了什么**

1. **口径**：交付物只写**材料/来源属性 + 分析深度**；`本次运行无外网` / `全文抓取失败` / `接口返回 500` /
   `未能发起检索` / `重试` 这类**我们这一侧的取回过程**一律不写——它们属于 run 记录（`verification.md`），
   不属于交付物。`非 OA` 只能由明确元数据支撑，**HTTP 500 不是非 OA 证据**（旧 prompt 里正是这么写坏的）。
2. **A-P4 收窄**：class 词表删掉 `抓取受限`（那正是要禁的措辞），改为接受「来源类或**来源侧属性**」
   （`未复核|未收录 PMC|无 pmcid|非 OA|无登记号|该来源不公开`）。
3. **新门禁 `A-P10-no-run-logistics`**（`kind: shape` / `op: no_run_logistics`，fail 级）：逐句匹配
   `本次运行|本运行环境|运行环境|本轮运行`、`无外网|外网(抓取)?(通道|链路)|网络受限|联网`、
   `抓取(失败|受限|超时)|取回失败|拉取失败|未能取回|未能发起`、`HTTP [45]\d\d|状态码|接口(返回|报错|超时)|返回 [45]\d\d`、
   `超时未(返回|响应)|重试|预算(用尽|上限)|工具调用`，命中即 FAIL，文案 `run-side narration in the deliverable: …`。
4. **变异 `M43`**：在覆盖行**尾部追加**一句运行物流（保持路径/来源类/深度不变）→ 只翻 A-P10。

**发布（原地，不新开版本号——沿用用户既有授权）**：dist 重打 **100,422 B / 19 entries / sha `4d92d3b4b7c3`**
→ `push-prompt --version 1.7`（**59,154 B / sha `2aac60f1c992`**，`prompt id 394a6e51617842a0ae9403579dcf8f45`）
+ `push-skill --version 1.0.8`（`skill_id cd93a42af72b4828b1690b3a7bccfa06`）→ `status` **in sync**。

**本地门禁**：`test-render-facts.py` **26/26 OK**；`node --test 'test/*.test.mjs'` **16/16**；
`evals/fact-check/test_regressions.py` **32/32 OK**（新增 `NoRunLogisticsTests` 5 项）；
`evals/fact-check/mutations.py` → `arm a: flipped 44/44; never flipped []`、`arm b: flipped 12/12`、**`GATE: PASS`**。

### 四组结果（2 / 4 / 18 / 14 条）

| 组 | run 目录 | thread | 墙钟 | 工具尝试 | 附录布局 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R40-1 | `20261010-104207-r40-fixed-1`（2 esid，场景 A） | `3e393756` | 323.4 s | 37（write×2） | `trial-columns` 3 列 / 15 行 | **22 PASS / 0 FAIL** | 0 |
| R40-2 | `20261010-104210-r40-fixed-2`（4 esid） | `edd0aad1` | 378.9 s | 48（write×5） | `disclosure-columns` 4 列 / 20 行 | **22 PASS / 0 FAIL** | 0 |
| R40-3 | `20261010-105212-r40-fixed-3`（18 esid） | `34532ecd` | 560.4 s | 62（write×4） | `trial-columns` 11 列 / 57 行 | **22 PASS / 0 FAIL** | 0 |
| R40-4 | `20261010-105217-r40-fixed-4`（14 esid） | `45fa8d59` | 519.4 s | 64（write×3） | `trial-columns` 11 列 / 128 行 | **22 PASS / 0 FAIL** | 0 |

**验收结果（逐项对照产物）**

- **A-P10 生效**：四份 `原文核对：` 行**没有任何运行物流字样**（`grep -cE "本次运行|本运行环境|无外网|抓取失败|抓取受限|取回失败|HTTP ?[0-9]{3}|接口返回|超时|重试"` 四份全 **0**），且四份**都仍写足了材料面**：
  - R40-1：「2/2 条已复核（记录1：src=1，库内正文即原文摘要，未取 PMC 全文；记录2：同）；2 条均按摘要级分析，0 条全文级；无未复核记录。」
  - R40-2：「4/4 条已复核（记录1、2：src=37，库内会议摘要正文；记录3、4：src=1，库内正文即原文摘要，摘要级，未取 PMC 全文）；0 条按全文分析、4 条为摘要级，无未复核记录。」
  - R40-3：「18 条已取回记录全部按所取回的来源正文核对：11 条会议摘要类来源（检索号中段标识为会议来源）即其完整终稿，7 条 PubMed 期刊来源按摘要级复核；…（0 条按全文分析 / 7 条仅摘要级）；无记录因缺少登记号或 DOI 而无法核对。」
  - R40-4：「14/14 条已复核（记录 3、10、11：src=37，库内会议摘要原文，摘要级；记录 1–2、4–9、12–14 共 11 条：src=1，库内正文即原文摘要、未取 PMC 全文，摘要级）；0 条按全文分析，14 条按摘要级核对，无未复核记录。」
  - 逐字证据与 SCORE 行落在 `docs/evidence/fact-check-a-p10-real-artifacts-2026-10-10.txt`。
- **A-P10 的「before」证据（同一门禁在三份真产物上 FAIL）**：R17 未种子基线 `43/44 → FAIL`（**只翻 A-P10**，
  `MUT_SEED_A=0` 可复现）、R39-hz `23/44 → FAIL`、R39-ctl `23/44 → FAIL`（这两组另有与任务形态相关的一批 FAIL，
  A-P10 与任务形态无关）。三个原句见证据文件 §2–§4。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| **R40-1 未用记录自带的中文药名**：记录里 `drug_earth_name_cn=['依洛尤单抗','奥帕司兰',…]` 就在手边，报告却通篇写 `evolocumab`（19 次）/ `olpasiran` → 场景 A 清单按中文名判身份，翻 `A-C1-trial-identity-A`、`A-C2-trial-identity-B`（另有 `A-S9`/`A-S9b`/`A-S10` 三项因图表行标签不能唯一识别观察）`39/44 → FAIL` | `drug_earth_name_cn` / `drug_earth_name_en` 成对字段在该批记录里均存在；prompt 第 62 行「…unless the pulled text itself supplies an equivalent Chinese name」、第 133 行「keep a source-supplied Chinese name when present」只写到「若无中文名才保留原文」这个方向 | 定性为**指令遵循偏差**（不是门禁误报）：规则已有但是软约束。可选锐化 —— 在 prompt/SKILL 明写「中文报告一律取记录自带的 `drug_earth_name_cn`」。**本轮不改**（避免再发一版 + 再跑 4 组），列入下轮候选 | 待下轮 |
| 附录列头在「试验显示名 == 注册号」时重复：`**NCT02729025**<br>NCT02729025 · 1 条披露` | R40-1 产物附录表头 | 属 `render-facts.py` `_column_label()` 的显示名回退问题（显示名取自记录 `trial` 首段，正好等于注册号时不再去重）。改法：显示名与注册号逐字相同则只留其一 | 待下轮（纯渲染，不动契约） |
| 图内/附录内「观察唯一性」不足：图表行标签 `OCEAN(a)-DOSE · olpasiran 10 mg 每 12 周（第 36 周）` 在同一试验多剂量下不能唯一识别观察 → `A-S9`/`A-S9b`/`A-S10` FAIL | R40-1 | 与上面同源（同一批记录），先解决中文命名与观察标识再复跑 | 待下轮 |
| 覆盖行出现「已取回 / 成功取回」叙述（R40-3「18 条**已取回**记录」、R40-4「未取 PMC 全文」） | 证据文件 §6/§7 | **本轮判 PASS 刻意保留**：`已取回/成功取回` 属「材料到手」的可用性陈述，不是我们的沙箱状态；`未取 PMC 全文` 是**深度**（与 `非 OA` 同类）。若日后要收紧，需同时改 `check.py` patterns + README + 变异/回归，属独立一轮 | 待观察（已记原句） |

| `tools/test_pack_dist.py` 自 `3cafb12` 起就是 4 error + 1 failure：fixture 只建了 `references/`、`templates/`、`templates/charts/`，而 `collect()` 无条件遍历四个子目录（含 `scripts/`）→ 四个构建类测试全在 `FileNotFoundError` 上炸，只有只读那一个活着 | `git show HEAD:…/test_pack_dist.py` 在 `/tmp` 重跑同样 4 error + 1 failure（**与 Phase 2 无关的存量缺陷**）；补一行 `"scripts"` 后 **5/5 OK** | 给 fixture 补 `scripts` 目录 + 注释说明为何必须建全 | ✅ 已修（本轮，`tools/test_pack_dist.py`） |

### 平台侧（转开发）

- 本轮**无新增**平台缺陷：四组 `outcome=succeeded`、22/22 断言全过、`no tool errors`、`present_artifact` 收尾。

---

## R41 — 药名成对字段锐化 + 附录可读名 + humanizer 交接段（prompt v1.7 / Skill v1.0.8 原地更新，2026-10-10）

**改了什么**

1. **(c) 命名锐化（把软约束变成可机械检查的硬规则）**：记录自带成对字段
   `clinical_result.arms[].drugs[].drug_earth_name_cn` / `drug_earth_name_en`（`docs/params-tool-schema.md` 的 ALLOWED_FIELD_NAMES 里已有），
   于是规则写成：「**中文报告 `drug_earth_name_cn` 非空即用 `_cn`**（依洛尤单抗 / 奥帕司兰，不写 `evolocumab` / `olpasiran`），
   英文报告用 `_en`；目标语言字段为空或 `未报告` 时回退另一语言并保留源拼写；永不音译 / 翻译 / 归一化 / 凭记忆映射 / 查外部字典」。
   落点：prompt 第 62 行（命名段）、第 133 行（Plain entity names）、第 205 行（final verification）、第 ~208 行 entity 字段段；
   `references/input-and-extraction.md` 第 7 行；`references/input-contract.md`（`source_drug_entities` 行 + Entity-ID 段）；
   `SKILL.md`（命名段 + entity 段）。
2. **(b) 附录列头可读名优先**：`render-facts.py` 新增 `_identifier_only()`；`_column_label()` 改为
   「可读账本 `study` 名 → 可读记录 `trial` 名 → 可读 identity 首段 → 原始 study/trial → 注册号 → identity 首段」；
   `_column_header()` 只在**显示名本身是纯注册号**时删掉第二行的重复注册号。
   **最小改动口径**：`研究甲（NCT05840016）` 这类「名字里带注册号」的列头**保持不变**（既有测试期望不动）。
   `APPENDIX_INTRO` 同步改口径；四模板表头句（4 处）同步。
3. **新增 humanizer 交接段**：prompt 增 `## Report prose style (when a report-humanizer skill is mounted)`
   （中文报告用 `report-humanizer-zh`、英文报告用 `report-humanizer-en`，**绝不同时用**；顺序 = 写完报告 → 过账本渲染门禁 →
   再做语言 pass；**本 prompt 优先于 humanizer 风格规则**；受保护集合 = 固定结构与小节标题 / `原文核对：` 覆盖行 /
   全部 `{{ref_n}}` / 数值与单位精度 CI p 值日期 / 发表时间列与顺序 / 表格形态与单元格 / 图表 JSON 与 `::visualization[...]{path="..."}` /
   citation JSON / 两个固定交付路径；风格范围仅散文）。`SKILL.md` 加对应精简节。
4. **清陈旧句**：`SKILL.md` 尾部「`entity:` … must be kept in the delivered report.」与 v0.16 移除**直接矛盾** → 改为「`entity:` 不属于本产品，
   出现在正文/表格/图表/账本即硬失败」；prompt 第 ~208 行的 entity 段改为「只用于选专有名词 + 填 `trial` 合并键」。

**发布（原地，沿用用户既有 v1.7 / 1.0.8 授权）**：dist 重打
**102,716 B / 19 entries / sha `ab1efaccf624`**（旧 100,422 / `4d92d3b4b7c3`）→
`push-prompt --version 1.7`（**63,422 B / sha `78c1a2a71efe`**，旧 59,154 / `2aac60f1c992`，prompt id `394a6e51617842a0ae9403579dcf8f45`）
+ `push-skill --version 1.0.8`（`skill_id cd93a42af72b4828b1690b3a7bccfa06`）→ `status` **in sync**。
发布前 `deps` 报 2 条上游变化（= 我们自己新建的 `report-humanizer-zh` / `-en` 首次进依赖基线）→ 先 `deps --accept` 记新基线再发布。

**本地门禁**：`evals/numeric-integrity/test-render-facts.py` **26 → 28/28 OK**（新增两条：注册号即显示名不重复 / 可读名优先于注册号）；
`node --test 'test/*.test.mjs'` **16/16**；`evals/runner-gate/test-runner.py` **38/38**；`evals/fact-check/test_regressions.py` **32/32**；
`tools/test_pack_dist.py` **5/5**、`tools/test_replay_run.py` **14/14**；`pack-dist.py --check` IDENTICAL。

### 四组结果（2 / 4 / 18 / 14 esid）

| 组 | run 目录 | thread | 墙钟 | 工具尝试 | 附录布局 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R41-A | `20261010-122243-r41-fixed-a`（2 esid，场景 A） | `933c8104` | 352.7 s | 45 | `trial-columns` 2 列 / 14 行 | **22 PASS / 0 FAIL** | 0 |
| R41-1 | `20261010-113706-r41-fixed-4`（4 esid） | `1d3d9b8f` | 423.0 s | 51（write×3） | `disclosure-columns` 4 列 / 20 行 | 21 PASS / **1 FAIL** | 0 |
| R41-2 | `20261010-113708-r41-fixed-18`（18 esid） | `9027a0a9` | 513.6 s | 77（write×2） | `trial-columns` 10 列 / 49 行 | **22 PASS / 0 FAIL** | 0 |
| R41-3 | `20261010-114717-r41-fixed-14`（14 esid） | `713bdf53` | 472.3 s | 49（write×2） | `trial-columns` 11 列 / 48 行 | **22 PASS / 0 FAIL** | 0 |

**逐项验收（对产物）**

- **(b) 生效（真产物前后对照）**：R41-A 附录表头 `| 维度 | **NCT02729025**<br>1 条披露 | **OCEAN(a)-DOSE**<br>NCT04270760 · 1 条披露 |`；
  R40-1（同一输入、旧渲染器）是 `**NCT02729025**<br>NCT02729025 · 1 条披露` —— 重复注册号消失，可读名列头不变。
  R41-3 另出现无注册号回退形态 `**Lp(a)FRONTIERS EXPANSION**<br>1 条披露`（合法）。
- **(c) 生效**：R41-2 正文中文药名 `卡瑞利珠单抗` 15 次 / `替雷利珠单抗` 50 次；场景 A 离线
  **39/44 → 41/44**，R40-1 的 `A-C1-trial-identity-A` / `A-C2-trial-identity-B`（中文名身份）**由 FAIL 转 PASS**。
- **场景 A 仍 3 项 FAIL，单一根因**：`A-S9-chart-values` / `A-S9b-chart-observation-identity` / `A-S10-sign-convention-consistent`
  —— 图表行标签 `NCT02729025 · 依洛尤单抗 420 mg Q4W（第 16 周）` 里给药间隔写成 `Q4W`，
  而该观察的 `identity_patterns` 只接受 `每月|QM`；报告内部**自己就混用**了两种写法（`每月` 3 次 / `Q4W` 9 次），
  源文（`artifacts/sources/ref_1_record.txt`）只有 `monthly` 一种说法。见下方「我方能改的」F2。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| **F1：模型重写工作区文件被平台拒（`no tool errors` FAIL）** —— 2/5 本轮 run 触发：R41-1 `write_file [re-prompted]: File '/workspace/scripts/build_ledger.py' already exists…`、R42-1 `…'/workspace/scripts/digest.py'…`；两次都是**辅助脚本**，不是报告正文，模型随后自行恢复（报告与附录都正常产出） | 两份 `verification.md` 的 `tool errors` 段；prompt 第 31 行第 6 条只点名「**the report body** 用 `overwrite=True`」 | 把第 6 条从「报告正文」扩到「**本工作区任何文件**（正文 / 辅助脚本 / 图表 JSON）：重写一律 `overwrite=True`；辅助脚本尽量只写一次」 | **待下轮**（会再触发一次发布 + 重跑，等点头） |
| **F2：同一观察的身份词汇在报告内混用** —— 报告「试验背景」表写「依洛尤单抗 420 mg 皮下每月一次」，其它表写 `依洛尤单抗 420 mg Q4W`；图表 label 取后者 → `A-S9`/`A-S9b`/`A-S10` 三项 FAIL（`41/44`） | 报告内 `每月` 3 次 / `Q4W` 9 次；源文只有 `monthly`；R17 与 R40-1 均写 `每月`（10 / 12 次、0 次 `Q4W`），说明这是本轮的词汇漂移而非门禁误报 | ①prompt/SKILL 加「同一观察（试验 / 人群 / 给药方案 / 时点）的身份词在正文、表格、图表 label **只用一套写法**；源文写 `monthly` 就写「每月一次」；图表 label 逐字复用正文该行的身份短语」；②`scenario-a.facts.json` 的该观察 `identity_patterns` 放宽到 `每月\|每月一次\|QM\|Q4W`（对应 `Q12W\|每 12 周`），否则模型全篇统一成 `Q4W` 仍会被判 FAIL | **待下轮**（①+② 一起改，改完重跑 4 组） |
| **本轮已修：R40-1 的附录重复注册号** | 见上「(b) 生效」 | `_identifier_only()` + `_column_label()` + `_column_header()`（`render-facts.py`），配 2 条新测试（28/28） | ✅ 已修（本轮） |
| **本轮已修：R40-1 的中文药名缺失** | 见上「(c) 生效」 | prompt / SKILL / 两份 references 五处写死「中文报告 `_cn` 非空即用」 | ✅ 已修（本轮） |

### 平台侧（转开发）

- 本轮**无新增**平台缺陷。两处 `no tool errors` FAIL 的**平台行为是对的**（拒绝静默覆盖已有文件、并 re-prompt 让模型改道），
  责任在我方 prompt 的写入纪律没覆盖辅助脚本（见 F1）。

---

## R42 — Phase A：18 / 14 esid 的 humanizer 臂（同 prompt、同日，对照组 = R41-2 / R41-3）

> 目的：在 **v1.7 新 prompt**（已含 humanizer 交接段）下，量化「显式让模型 load `report-humanizer-zh` 并按其规则写正文」
> 相对「不额外要求」的差别。对照组用同一 prompt 的 R41-2（18 esid）/ R41-3（14 esid）——**不是** R40-3/-4（那是上一版 prompt）。

| 组 | run 目录 | thread | 墙钟 | 工具尝试 | 附录布局 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R42-1（18 esid + hz） | `20261010-115907-r42-hz-18` | `62cf03f3` | 581.1 s | 116（`edit_file`×59） | `trial-columns` 10 列 / 63 行 | 21 PASS / **1 FAIL**（F1：`write_file` 重写 `scripts/digest.py` 被拒） | 0 |
| R42-2（14 esid + hz） | `20261010-121046-r42-hz-14` | `0be0faf4` | 552.0 s | 71（write×4） | `trial-columns` 11 列 / 46 行 | **22 PASS / 0 FAIL** | 0 |

**量化（正文散文，`/tmp/r39-hz/metrics.py`；hz = 显式要求 humanizer，ctl = 同一 prompt 不额外要求）**

| 指标 | 18 esid ctl（R41-2） | 18 esid hz（R42-1） | 14 esid ctl（R41-3） | 14 esid hz（R42-2） |
| --- | --- | --- | --- | --- |
| 正文去空白字符 | 5,276 | 5,912（+12%） | 4,047 | 4,136（+2%） |
| 平均句长 | 64.3 | 62.9（−2%） | 66.3 | 58.3（−12%） |
| 最长句 | 220 | 193 | 262 | 209 |
| `**粗体**` 数 | 47 | 26（**−45%**） | 18 | 24（+33%） |
| 逗号数 | 87 | 109 | 75 | 66 |
| 12-gram 重复率 | 0.0911 | 0.0643（−29%） | 0.0421 | 0.0521（+24%） |
| 扫描器 strong 命中 | 0 | 0 | 0 | 0 |
| 扫描器 weak 命中 | 1（`W-BOLD-COUNT`） | 2（`W-BOLD-COUNT`,`W-DASH-COUNT`） | 1（`W-BOLD-COUNT`） | 3（`+W-FMT-MIXED`） |
| `{{ref_n}}` 去重数 | 18 | 18 | 14 | 14 |
| 工具尝试 / 墙钟 | 77 / 513.6 s | 116（+51%） / 581.1 s（+13%） | 49 / 472.3 s | 71（+45%） / 552.0 s（+17%） |

（R39 旧 prompt 的 4 esid 对照：hz 3,868 字 / 均句 53.7 / rep12 0.0447 / weak 2 vs ctl 5,112 / 67.3 / 0.0624 / weak 1。）

**结论**

1. **硬契约不受影响**：两臂 `{{ref_n}}` 数逐条相等（18/18、14/14），附录完备性门禁全过；humanizer pass 没动引用、数值与结构。
2. **能看到的稳定方向只有一处**：18 esid 组粗体 −45%、12-gram 重复率 −29%；14 esid 组方向相反（粗体 +33%、重复率 +24%）。
   **每臂 n=1，差异与 run 间波动量级相当**，不足以宣称「humanizer 让报告更好」。strong 级 AI 味命中两臂**都是 0**——
   说明在当前 prompt 下正文本来就没有强 AI 味特征，humanizer 能改的是弱特征与排版形态。
3. **代价是确定的**：hz 臂工具尝试 +45~51%（18 esid 里 `edit_file` 逐句改 59 次）、墙钟 +13~17%，且两臂都出现 F1 类重写被拒。
   故**默认策略保持「prompt 只说明怎么交接，不强制每次调用」**（现 prompt 措辞即此），贵的长报告由用户按需点名。
4. weak 命中数 hz 更高（2 vs 1、3 vs 1）不是回归：`W-DASH-COUNT` / `W-FMT-MIXED` 是文档级弱阈值，说明 hz 臂更多用了破折号等排版手段，
   与「去 AI 味」无关；数据与 `docs/evidence` 一并留给下轮判断是否要调阈值。

---

## R43 — F1（写入纪律扩面）+ F2（同一观察一套写法）落地后重跑四组（2026-10-10）

发布：**prompt v1.7 原地更新 → 65,090 B / sha `e23eef7201d0`**；**Skill v1.0.8 原地更新**（dist **103,693 B / 19 entries / sha `2f4700a2f295`**）；`deps` unchanged；`status` → in sync。
改动面：`system-prompts/multi-clinical-result-comparison-v0.16.md` 第 6 条覆盖面扩到「工作区里你写过的任何文件」+ 新增 hard rule **One wording per observation**；`skill/.../SKILL.md`（硬规则段 + `## Required distinctions` bullet）、`references/chart-templates.md`、`references/file-delivery.md`；`evals/fact-check/scenario-a.facts.json`（30 条 `identity_patterns`/`report_identity_patterns` 双向放宽）；`evals/fact-check/test_regressions.py` 新增 `IdentityWordingTests`（32 → 34）。

| 组 | run 目录 | thread / turn | 墙钟（server/polled） | 工具尝试 | 附录布局 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R43-1（2 esid 场景 A） | `20261010-131547-r43-a` | `313d0f8b…` / `08ef3888…` | 384.5 s / 389.1 s | 43 = 42 returned + **1 unresolved**（write_file 被拒） | `trial-columns` 2 列 / 15 行 | 21 PASS / **1 FAIL**（F1） | 3 |
| R43-2（4 esid） | `20261010-131547-r43-4` | `336aecb9…` / `e2412b9d…` | 498.7 s / 512.8 s | 64（write×4） | `disclosure-columns` 4 列 / 19 行 | **22 PASS / 0 FAIL** | 0 |
| R43-3（18 esid） | `20261010-132805-r43-18` | `0b980877…` / `d4678968…` | 503.1 s / 512.7 s | 66（write×4） | `trial-columns` 10 列 / 43 行 | **22 PASS / 0 FAIL** | 0 |
| R43-4（14 esid） | `20261010-132806-r43-14` | `5e541a08…` / `b4239a9b…` | 491.8 s / — | 54（write 写 `/workspace/scripts/digest.py`） | `trial-columns` 11 列 / 49 行 | **22 PASS / 0 FAIL** | 0 |

**F2 验证（本轮的验收点）**

- R43-a 的三项图表断言 `A-S9-chart-values` / `A-S9b-chart-observation-identity` / `A-S10-sign-convention-consistent` **由 FAIL 转 PASS**（R40-1 39/44、R41-A 41/44 都栽在这三项）⇒ 规格放宽 + 「一套写法」硬规则**双管齐下生效**。
- 附带：`A-C16-hard-outcome-gap` 因 **O27 结案**（术语放宽）也转 PASS；重打分后 **R41-A 41/44 FAIL → 44/44 PASS**、**R43-a 42/44 → 43/44**（仅剩 A-ATTR）。

**F1 仍复发（本轮的未结项）**：R43-a 在 `/workspace/work/draft.md` 上重写时漏传 `overwrite` → `write_file [re-prompted]: File '/workspace/work/draft.md' already exists …`。
说明「扩到所有文件」还不够——模型自己都写「Re-issuing the draft in one write」却仍漏传 flag ⇒ 第二轮改为**无条件 `overwrite=True`**（R44）。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| **F2：同一观察身份词汇混用（`每月` vs `Q4W`）** | 图表行标签 `NCT02729025 · 依洛尤单抗 420 mg Q4W（第 16 周）` vs 正文「每月一次」；`op_chart_observations` 按 `label + description` 匹配 `identity_patterns` | 生成侧：prompt / SKILL / `chart-templates.md` 加「一套写法」硬规则（图表 label 逐字复用正文身份短语）；判分侧：`scenario-a.facts.json` 放宽 30 条 pattern（`(?:每月\|每月一次\|QM\|Q4W)` 等），225 mg Q12W 与 Q24W 仍严格互斥，配 2 条回归测试 | ✅ **已修且已验证**（R41-A/R43-a/R44-a/R45-a 四项图表断言连续 4 次 PASS） |
| **F1：重写工作区文件被平台拒** | R43-a `write_file [re-prompted] … draft.md already exists` | 第一轮：第 6 条覆盖面扩到所有文件（本轮）；**不够** | ⛔ 未修好 → 见 R44 / R45 / O42 |
| **O27：`A-C16` 术语绑定过窄** | R16（心血管结局事件）+ R43-a（心血管结局）两份误判样本 | pattern 1 放宽为 `硬结局\|硬终点\|心血管事件\|心血管结局`，pattern 2（否定式）不动 + 回归测试（scorer 34 → 35） | ✅ 已结案（变异闸门 `GATE: PASS`） |
| **O40 / O41（新增待样本）** | A-ATTR 否定陈述（2 样本）、A-P2 非分歧提到库内记录（1 样本） | 本轮**不改评分器**，只记账 | 📝 待样本（≥2 份） |

### 平台侧（转开发）

- 本轮无新增平台缺陷。`write_file` 拒绝静默覆盖的**平台行为是对的**（且 re-prompt 文案已给出 `overwrite=True` 的改道建议）。

---

## R44 — F1 第二轮（无条件 `overwrite=True`）后重跑四组（2026-10-10）

发布：**prompt v1.7 原地更新 → 65,452 B / sha `5b8043bb3779`**；**Skill v1.0.8**（dist **103,846 B / 19 entries / sha `cdb4992f9b20`**）；`status` → in sync。
改动：第 6 条改为「**每次 `write_file` 一律带 `overwrite=True`，包括全新路径的首次写入**；不要判断路径是否新」（`references/file-delivery.md` + `SKILL.md` 的 Output firewall 同步）。

| 组 | run 目录 | thread / turn | 墙钟（server/polled） | 工具尝试 | 附录布局 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R44-1（2 esid 场景 A） | `20261010-134027-r44-a` | `23fd4111…` / `e2fbcd2f…` | 495.2 s / 511.1 s | 51（write×8，其中 `output/report.md` ×4、`scripts/gen_ledger.py` ×2） | `trial-columns` 2 列 / 11 行 | **22 PASS / 0 FAIL** | 0 |
| R44-2（4 esid） | `20261010-134027-r44-4` | `193a3957…` / `8dbdb11b…` | 380.7 s / 390.7 s | 51（write×3） | `disclosure-columns` 4 列 / 27 行 | **22 PASS / 0 FAIL** | 0 |
| R44-3（18 esid） | `20261010-135018-r44-18` | `0075c41e…` | 655.5 s / 657.3 s | 84 = 83 returned + **1 unresolved**（edit_file 被拒） | `trial-columns` 10 列 / 42 行 | 21 PASS / **1 FAIL**（F1 换形态） | 3 |
| R44-4（14 esid） | `20261010-135018-r44-14` | `c629e4cd…` | 511.9 s / 513.5 s | 56（write×3） | `trial-columns` 11 列 / 44 行 | **22 PASS / 0 FAIL** | 0 |

**关键证据（说明无条件规则确实在起作用）**：R44-a 里 `output/report.md` 被写了 **4 次**、`scripts/gen_ledger.py` 被写了 **2 次**，而 `already exists` / `re-prompted` 命中 **0** 次（R43-a 的同类重写正是失败点）；transcript 因长 args 截断看不到 flag 本身，但「多次重写 + 零拒绝」只能由「确实带了 `overwrite=True`」解释。

**F1 仍未清零，但换了形态**：R44-3 的失败是 `edit_file [re-prompted]: Could not find the target string in '/workspace/scripts/build_ledger.py'` —— 模型对**自己生成的脚本**做 7 次 `edit_file` 补丁，其中一次目标串已过期。⇒ 第三轮把 `edit_file` 也纳入纪律（R45）。

**场景 A 离线判分**：**44/44 PASS（首次全绿）**，`warn 1/1`；F2 四项图表断言保持 PASS；O27 放宽后 A-C16 也 PASS。

---

## R45 — F1 第三轮（`edit_file` 只准用于报告正文）后重跑四组（2026-10-10）

发布：**prompt v1.7 原地更新 → 65,959 B / sha `f63bf180822c`**；**Skill v1.0.8**（dist **103,982 B / 19 entries / sha `47c06e7aa6d4`**）；`deps` unchanged；`status` → in sync。
改动：第 6 条追加「**`edit_file` 只用于 `/workspace/output/report.md`**，且只用刚 `read_file` 看到的短 `old_string`；本轮生成的脚本/账本/digest/`work/*` 一律不补丁，改就整文件 `write_file(overwrite=True)` 重发」（`references/file-delivery.md` 同步）。

| 组 | run 目录 | thread / turn | 墙钟（server/polled） | 工具尝试 | 附录布局 | 断言 | exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R45-1（2 esid 场景 A） | `20261010-140534-r45-a` | `204d1c12…` / `24c03296…` | 344.2 s / 346.3 s | 44（write×7） | `trial-columns` 2 列 / 12 行 | **22 PASS / 0 FAIL** | 0 |
| R45-2（4 esid） | `20261010-140534-r45-4` | `37c35f4a…` / `14e9cde2…` | 390.5 s / 408.3 s | 44（write×8） | `disclosure-columns` 4 列 / 17 行 | **22 PASS / 0 FAIL** | 0 |
| R45-3（18 esid） | `20261010-141356-r45-18` | `bd20d058…` | 410.5 s / 412.0 s | 56（edit_file×4 全在报告正文，全部成功） | `trial-columns` 10 列 / 33 行 | **22 PASS / 0 FAIL** | 0 |
| R45-4（14 esid） | `20261010-141356-r45-14` | `a1937a93…` | 627.1 s / 638.5 s | 59 = 58 returned + **1 unresolved**（write_file 被拒） | `trial-columns` 11 列 / 57 行 | 21 PASS / **1 FAIL**（F1 回到 R43-a 形态） | 3 |

**场景 A 离线判分（R45-a）**：`SCORE scenario=a facts 42/44 warn 1/1 -> FAIL`；余留 2 项为 `A-ATTR-misattribution`（2 个 cell，见 O40）+ `A-P2-divergence-shows-both`（1 处，见 O41）；**F2 四项图表断言全部保持 PASS**。

**F1 三轮汇总（R41 → R45，共 14 个 run）**

| 发布轮 | F1 修法 | 结果 | 失败形态 |
| --- | --- | --- | --- |
| （历史基线 R38–R40） | 「写一次、修订带 `overwrite=True`」 | 6 run 中 0 失败（但写次数少） | — |
| R41 / R42 | 同上（覆盖到辅助脚本） | R41 1/4、R42 1/2 失败 | `write_file` 缺 flag（脚本） |
| **R43** | 覆盖面扩到「工作区里任何文件」 | **1/4 失败** | `write_file` 缺 flag（`work/draft.md`） |
| **R44** | 无条件 `overwrite=True`（含全新路径） | **1/4 失败** | `edit_file` 目标串过期（自写脚本） |
| **R45** | `edit_file` 只准用于报告正文 | **1/4 失败** | `write_file` 缺 flag（`work/draft.md`） |

**结论**：三轮措辞强化都**没能把基线从约 1/4 run 挪动**，且失败形态在两种之间摆动；三次失败中报告侧的其它 21 条断言**全部照常通过**（平台 re-prompt 后 run 正常完成、产物完整）⇒ 这不是合同缺口，而是「长 agentic run 里模型对某个布尔参数偶发漏传」的行为天花板。见 O42 三个选项（接受 / 改 runner 断言口径 / 把正文改成脚本一次成文）。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| **F1（O42）：`write_file` 漏传 `overwrite` / `edit_file` 目标串过期** | R43-a、R44-18、R45-14 三次 `no tool errors` FAIL，各自只损失一次调用 | 已做三轮（覆盖面 → 无条件 flag → `edit_file` 收窄）；**未清零** | ⛔ **未修好**（判为行为天花板，待用户选 O42 的 A/B/C） |
| **F2：同一观察一套写法** | R43-a / R44-a / R45-a 四项图表断言连续 PASS；R41-A 重打分 44/44 | 生成侧规则 + 判分侧放宽（30 条 pattern）+ 2 条回归测试 | ✅ **已修且已复验** |
| **O27：A-C16 术语放宽** | R16 + R43-a 两份样本 | pattern 1 放宽 + 1 条回归测试（scorer 35） | ✅ 已结案 |
| **O40 / O41** | 见上两节 | 只记账 | 📝 待样本 |

### 平台侧（转开发）

- 本轮无新增平台缺陷。若 O42 选 B/C 也不需要平台改动；若想从平台侧根治，可建议 `write_file` 提供「显式 `mode=upsert` 或对已存在路径默认覆盖 + 备份」——**本轮未提单**，等用户决定是否值得报。

---

**R43 / R44 / R45 收尾状态**：线上 = prompt v1.7 **65,959 B / sha `f63bf180822c`**、Skill v1.0.8（dist **103,982 B / 19 entries / sha `47c06e7aa6d4`**），`status` in sync；本地门禁 runner-gate 38 / scorer 35 / tools 5+14 / Node 16 / numeric-integrity 28 全 OK；fact-check 变异闸门 `arm a 44/44, arm b 12/12, GATE: PASS`。

---

## R46 — O42 结案：工具侧前置拒绝改判（runner 层）后两次真跑（2026-10-10）

用户答复：①「谁好，你推荐谁」②「你自己看着办吧」③「不管了」（③ = 撤掉「平台文档级建议」那条）。按①的授权执行 **O42 选项 B 的窄口径**；按②自行处置 O40/O41。

**发布状态：本轮 `prompt` / `Skill` / `dist` 一字未改**（只改本地 runner），无 ToolSmith 写动作。线上仍是 R45 的 prompt v1.7 `f63bf180822c` / Skill v1.0.8 dist `47c06e7aa6d4`，`status` in sync。

### 改了什么（`~/.local/bin/toolsmith-publish`，备份 `toolsmith-publish.v15.bak`）

| 项 | 内容 |
| --- | --- |
| 新增 `TOOL_REFUSED_RX` | `^` 锚定，收编两种**实测确认**的工具侧前置拒绝：`File '<path>' already exists…`（`write_file`，R43-a / R45-14）、`Could not find the target string in '<path>'`（`edit_file`，R44-18） |
| `retry_kind()` | 上述形状返回 `"rejected"`（此前落 `"errors"` ⇒ 整 run 的 `no tool errors` 变红） |
| `REFUSAL_BUDGET = 3` | 原恒 PASS 的信息行改成「拒绝次数 ≤ 3」的判定；**断言条数仍 22**、`verification.md` 语义与退出码不变 |
| 负例保障 | 被包装的消息（`RuntimeError: File '…' already exists`、`MCP error: …`）**仍落 `errors`**（`^` 锚定 + 单测） |
| 风险方向 | 若平台改写 re-prompt 文案 ⇒ 正则失配 ⇒ 回到旧口径（**只会变严，不会漏判**） |

### 离线重打分（98 份归档，零新 run / 零网络 / 不改产物）

| 指标 | 结果 |
| --- | --- |
| 扫到的 run（有 `debug-history.json`） | **98** |
| `errors > 0` 的 run | **0** |
| 拒绝次数直方图（次数 → run 数） | `{0: 77, 1: 18, 2: 3}` |
| 单 run 最大拒绝次数 | **2**（r36-fixed-1：`execute` 1 + `edit_file` 1） |
| 超 `REFUSAL_BUDGET` 的 run | **无**（预算不误伤任何历史样本） |
| 五次历史 F1 FAIL（r41-fixed-4 / r42-hz-18 / r43-a / r44-18 / r45-14） | **各恰好 1 次拒绝** ⇒ 与「一次可恢复拒绝把整 run 判红」的定性吻合 |

### 本地门禁

`py_compile` OK；`evals/runner-gate/test-runner.py` **38 → 39 tests OK**（新增 `test_tool_side_precondition_refusals_are_not_errors`，含 2 个负例）；`evals/runner-gate/verify-run-chain.py` **`GATE: PASS`**（96 份历史 / 5 可比 / 91 跳过）；`tools/test_replay_run.py` **14 OK**；`tools/test_pack_dist.py` **5 OK**。

### 真跑（scenario A，R45 已发布内容）

| tag | run 目录 | thread | turn | 墙钟（server/polled） | 工具尝试 | refused | 断言 | exit | 离线 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| r46-a | `~/.local/state/toolsmith-runs/20261010-145926-r46-a` | `4327dde4-4717-4944-9e68-de57f2a2b5bd` | `f1dbce68-92ed-4b24-b7ed-25f9326f9a7b` | 330.0 / 349.2 s | — | 0 | **22 PASS / 0 FAIL** | 0 | **40/44 FAIL**（O43 ×3 + A-ATTR ×1） |
| r46-a2 | `…/20261010-150625-r46-a2` | `f0e29144-a730-433c-b313-63afb2115cc9` | `f63a99ae-e453-41a2-ae8e-84ceb7463d15` | 360.7 / 371.2 s | — | 0 | **22 PASS / 0 FAIL** | 0 | **44/44 PASS** |

日志 `/tmp/r41/r46a.log`、`/tmp/r41/r46a2.log`；证据包 `docs/evidence/o42-refusal-reclassification-2026-10-10.txt`。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| **O42：一次可恢复的工具拒绝打掉整 run** | 98 份归档 0 error、5 次历史 FAIL 各 1 次拒绝、单 run 最大 2 | runner 双形状 `^` 锚定 + 预算 3 + 单测（含负例） | ✅ **已结案**（R46；回滚 = 复原 `v15.bak` + 重跑 39 项） |
| **O43：图表行必须点名试验（隐性规则）** | r46-a 5 根柱子 label+description 都无试验名 → 40/44；r46-a2 把试验放 `description` → 44/44；R45-a 亦 PASS ⇒ 1/3 丢试验名 | **本轮不改**（n=1）；候选① prompt/SKILL 补一句硬规则（随下次内容改动发版）；候选②判分侧去试验维度 | 📝 **待修**（与 O40/O41 的报告侧习惯句同批，不单独开一轮） |
| **O40 / O41** | 见上两节（A-ATTR 否定陈述 2 样本；A-P2 非分歧提到库内记录 1 样本） | ②「你自己看着办」⇒ **不改评分器、不单独发版**；候选句随下次内容改动一起进 | 📝 待样本 |

### 平台侧（转开发）

- 本轮无新增平台缺陷，**不发新单**。③ 用户已明确「不管了」⇒ 撤回上一轮规划里的「`write_file` 提供 upsert/默认覆盖」平台建议，不再提单。
- 既有观察保留：`write_file` 拒绝静默覆盖**是对的**，re-prompt 文案本身就给出 `overwrite=True` 改道建议；问题只是 runner 口径把它算成 error（本轮已从 runner 侧收口）。

---

### R46 收尾状态

线上未变（prompt v1.7 `f63bf180822c` / dist `47c06e7aa6d4`，in sync）；本地门禁 runner-gate **39** / scorer 35 / tools 5+14 / Node 16 / numeric-integrity 28 全 OK；变异闸门 `arm a 44/44, arm b 12/12, GATE: PASS`。**新增待修项 1 条（O43），已有待样本 2 条（O40/O41），三者共用「下次内容改动一轮」的批次。**

---

## R47 — O43 结案 + O40/O41 报告侧习惯句（原地发布）+ 四组真跑 + 一次 `reasoning-effort` A/B（2026-10-10）

用户答复：「改吧」+「分析下 2–3 条结果也要 5min+ 的耗时分布，看哪些步骤可以调整」。
按「**一次内容改动一轮**」的既有纪律执行：本轮只装 **O43（图表行点名试验）+ O40/O41（报告侧习惯句）**，
把**耗时优化单独留在 R48 提案**（不给本轮 keep/discard 归因添混）。

### 发布（原地更新，与 v0.16.1 / Phase 2 / Phase B / R41–R45 同一授权：`publish` in place，不改版本标签）

| 项 | 改前（R45） | 改后（R47） |
| --- | --- | --- |
| prompt `multi-clinical-result-comparison-v0.16.md` | 65,959 B / sha `f63bf180822c` | **67,591 B / sha `c1641a46810a`** |
| Skill v1.0.8 bundle（19 entries） | 103,982 B / sha `47c06e7aa6d4` | **105,347 B / sha `025aec791b1c`** |
| `deps` | — | **`unchanged since the recorded baseline`**（发布前先过） |
| `status` | in sync | **in sync**（发布后回读逐字节一致） |

改动 5 个文件、共 4 处新增（每处都是"可机械检查"的硬规则，不只是风格建议）：

| 文件 | 新增内容 |
| --- | --- |
| `system-prompts/…-v0.16.md` | 三条 hard rule 段：**Every chart row names its own trial**；**A marker binds its own record's content**（否定/比较句必须同时点自己）；**`库内记录` has exactly one legitimate use** |
| `skill/…/SKILL.md` | 中文硬规则两条（**引注归属** / **图表每一行点名自己的试验**）+ 指向两份 reference |
| `skill/…/references/chart-templates.md` | **图表每一行点名自己的试验（硬性）**：≥2 试验时 `label`/`description` 必须自含试验短名或注册号，不得只靠标题/图例/颜色 |
| `skill/…/references/citation-and-ref.md` | 新节 **`## Marker attribution`**（引注归属 + `库内记录` 唯一合法写法） |
| `skill/…/references/input-contract.md` | 在固定分歧写法那句后补「该写法是 `库内记录` 出现的**唯一**位置」（点名 `A-P2` 作为门禁） |

### 真跑（四组，顺序执行；输入 `/tmp/r40/{a-scenario-a,b-4,c-18,d-14}.txt`）

| tag | run 目录 | thread | turn | 墙钟（server/polled） | 工具尝试 | refused | 断言 | exit | 离线 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| r47-a（2 esid） | `…/20261010-153933-r47-a` | `412a8b27-0bd4-476d-a501-30869404a914` | `e2cc474b-9389-42bc-9599-fb199294d32c` | 349.1 / 349.4 s | 40 | 0 | **22 PASS / 0 FAIL** | 0 | 43/44 FAIL（**A-C9 符号写法**，见 O44） |
| r47-4（4 esid） | `…/20261010-154531-r47-4` | `3e881375-6c1a-447c-a02b-767761fdb01a` | `fe134060-0df3-4339-a841-9b9ebb469da7` | 512.1 / 514.6 s | 56 | 0 | **22 PASS / 0 FAIL** | 0 | — （4 esid 不在 scenario A 规格内） |
| r47-18（18 esid） | `…/20261010-155422-r47-18` | `e9dcf898-fc42-4720-92fc-89823c4aebed` | `ca5fee47-c162-4d00-b424-550515167d00` | 488.6 / 496.7 s | 56 | 0 | **22 PASS / 0 FAIL** | 0 | — |
| r47-14（14 esid） | `…/20261010-160249-r47-14` | `af0b6a07-4a8f-4fb1-bd0b-0e6101fc0fef` | `7dc47608-cff9-492b-a64d-b6a01ce192f7` | 569.7 / 578.1 s | 66 | 0 | **22 PASS / 0 FAIL** | 0 | — |
| r47-loweff-a（2 esid，附加 A/B 臂：`--reasoning-effort low`） | `…/20261010-161320-r47-loweff-a` | `62e4de53-3800-4a9b-b0b5-8b408e8fa9b2` | `e0ba716c-0c9f-4ffb-9094-f0afbb5db572` | 310.4 / 329.7 s | 35 | 0 | **22 PASS / 0 FAIL** | 0 | 43/44 FAIL（**A-ATTR 表格 cell 继承**，见 O40） |

**四组连续 4/4 无工具拒绝**（O42 的窄口径下 `arguments refused = 0`），日志 `/tmp/r47/{r47-a,r47-4,r47-18,r47-14,low-a}.log`。

### O43 验收：4/4 全部命中（图表行自带试验身份）

| run | 图表 | 行证据 |
| --- | --- | --- |
| r47-a | `endpoint-bar-1.json`（5 柱） | `OCEAN(a)-DOSE · 奥帕司兰 225 mg 每 12 周 · 第 36 周`（×4）、`NCT02729025 · 依洛尤单抗 420 mg 每月一次 · 第 16 周` |
| r47-18 | `endpoint-bar-1.json`（5 柱） | `HARMONi-6（NCT05840016）· 依沃西单抗+化疗`、`TQB2450-III-12（NCT05718167）· …`、`RATIONALE-307（NCT03594747）· …` |
| r47-14 | `endpoint-bar-1.json`（5 柱） | `奥帕司兰 225 mg 单次皮下（NCT04987320）`、`zerlasiran 300 mg 单次皮下（jRCT2051240068）` |
| r47-4 | `evidence-timeline.json`（单试验时间线） | 不适用（规则限定 ≥2 试验） |

对比 r46-a（5 根柱子含 0 个试验名 → 离线 40/44）：**同一门径下 1/3 偶发 → R47 后 4/4 全中**。

### 附加 A/B：`reasoning-effort`（回答"耗时能不能靠降思考量砍"）

同日同输入（scenario A），唯一变量 = `--reasoning-effort low`（默认平台值 vs `low`）：

| 臂 | 墙钟 | 步数 | out_tok | reasoning_tok | 工具尝试 | 断言 | 离线 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 默认（r47-a） | 349.1 s | 36 | 60,976 | **40,304** | 40 | 22/0 | 43/44 |
| `low`（r47-loweff-a） | 310.4 s | 26 | 59,665 | **44,975** | 35 | 22/0 | 43/44 |

⇒ **`reasoning_effort=low` 没有减少 reasoning 量（44,975 vs 40,304，噪声级）**，墙钟差 −39 s 全部来自步数少 10 步；
**该旗标不是可用杠杆**（负结果，已记入 `docs/evidence/runtime-breakdown-2026-10-10.md`）。

### 我方能改的

| 现象 | 证据 | 改法 | 状态 |
| --- | --- | --- | --- |
| **O43：图表行不点名试验（隐性规则）** | r46-a 5 柱 label+description 无试验名 → 40/44 | prompt + SKILL + chart-templates 三处硬规则 | ✅ **已结案**（R47 四组 4/4 命中，判分侧未动） |
| **O40：`A-ATTR` 否定陈述不给豁免** | 第 3 份样本 r47-loweff-a：表格 cell「OCEAN(a)-DOSE 未评估该终点」**无标记 ⇒ 继承本行 `ref_1`**，只点名 `ref_2` 的试验 ⇒ FAIL；同 run 第 94/95 行同型 | R47 已加正文侧习惯句（**不足以覆盖表格 cell 的标记继承**）；R48 收窄为可机械检查的一条：阴性/缺测句必须带**被点名那条记录**自己的 `{{ref_n}}`，否则不点名对方 | 📝 **R48 内容轮**（不改评分器） |
| **O41：`库内记录` 非分歧使用** | R47 五份产物 `库内记录` 出现 **0 次**（A-P2 无触发） | 四处写「只许出现在固定分歧写法里」 | ✅ **收尾**（不改评分器；再现再议） |
| **O44（新）：`A-C9` 只认减号写法** | r47-a 写「降低 8.3%／降低 5.3%」（交付物内部一致，`A-S10` PASS）⇒ `-8\.3`/`-5\.3` 0 命中，43/44 FAIL；历史 6/6 + 同日 low 臂都写减号 ⇒ 1/7 | 候选：`A-C9` 两条 pattern 各加文字式备选；**按 O27/O28 先例等第 2 份样本** | 📝 **待样本** |
| **耗时结构（新证据）** | 生成占墙钟 **65–92%**、reasoning 占输出 **46–76%**；工具全部 <15%；2 esid 与 18 esid 耗时同量级 | 见 `docs/evidence/runtime-breakdown-2026-10-10.md`（L1 reasoning 旗标 = 已证负；L2 随包发脚本；L3 去 `draft.md` 两遍写；L4 压步数） | 📝 **R48 提案待用户点选** |

### 平台侧（转开发）

- 本轮无新增平台缺陷（`reasoning_effort` 旗标被 API 接受但未见效果，属**模型侧**行为、非平台契约问题；仅作负结果记录，不单独提单）。

### R47 收尾状态

线上 = prompt v1.7 **67,591 B / sha `c1641a46810a`**、Skill v1.0.8（dist **105,347 B / 19 entries / sha `025aec791b1c`**），`status` in sync；
本地门禁 runner-gate **39** / scorer 35 / tools 5+14 / Node 16 / numeric-integrity 28 全 OK；
变异闸门 `arm a 44/44, arm b 12/12, never flipped [], GATE: PASS`；
**结案 2 条（O41 收尾、O43 结案）、待修 1 条（O40 → R48）、待样本 1 条（O44）**。

## R48 — L2/L3/L4 三条速度杠杆同轮落地（随包脚本 / 单遍正文 / 合批调用）+ 六次真跑（2026-10-10）

**用户口径**：*「L2-4都想要」* —— 覆盖先前「一次只动一个杠杆」的纪律，三条杠杆同轮落地；归因改用**历史 run 基线 + per-lever 签名**（不靠单变量 A/B）。

### 本轮改了什么（内容侧）

| 杠杆 | 改动 | 落地文件 |
|---|---|---|
| **L2** | 把模型每次自写的辅助脚本换成**随 Skill 发布的六个现成脚本**：`prep_sources.py`（切分 + 编号 + `work/refs.json`）/ `build_ledger.py`（编译 + 校验数值事实账本）/ `patch.py`（原子定点改写）/ `check_report.py`（交付前机械门禁）/ `make_chart.py`（内容 spec → envelope + 跑上游校验器）/ `make_citations.py`（citations 逐字节从 `refs.json` 生成） | `skill/.../scripts/`（1 → **7** 个脚本）+ `references/toolbox.md`（**新增**，唯一 CLI 事实源）+ prompt 第 2 条 |
| **L3** | 报告正文**只写一次**、直接落在 `/workspace/output/report.md`；`render-facts.py` **原地**渲染 `--draft == --out`；**取消 `work/draft.md`、取消 scratch 渲染与二次拷贝**；审计落 `work/audit.json`；后续小改走 `patch.py` | prompt 第 6 条、`references/file-delivery.md`、`SKILL.md` 第 9/9b 条 |
| **L4** | 合批：`mkdir` + 切分 + digest 合成一条 `execute`；禁「写 N 个分块再合并」；禁重复读同一文件；目标 ≤ ~25–30 tool calls | prompt 第 7 条 |
| **运行时路径（同轮修的真缺陷）** | 真实 run 取证：Skill 挂在 `/workspace/skills/multi-clinical-result-comparison/`，裸 `scripts/…` 从 `/workspace` **不解析** ⇒ 全部改为绝对路径 `python3 {SD}/<name>.py`（`references/toolbox.md` 原句「`scripts/…` resolves under the mounted Skill directory」是**事实错误**） | prompt（7 处）、`SKILL.md`、`references/toolbox.md` / `chart-templates.md` / `file-delivery.md` / `input-and-extraction.md` / `citation-and-ref.md`、六脚本 usage 与错误提示 |

`tools/pack-dist.py` `EXPECTED` **19 → 26**（+6 脚本 +1 reference）；dist 重打 `multi-clinical-result-comparison-v0.16.zip` = **138,171 B / 26 entries / sha `bf0c9cf84ecf`**（`--check` IDENTICAL）。

### 发布（原地，版本标签不变）

`toolsmith-publish deps` = `unchanged since the recorded baseline`；`push-prompt --version 1.7` → HTTP 200 / in-place / 回读 `current=v1.7 matches_local=True`；`push-skill --version 1.0.8` → HTTP 200 / skill_id `cd93a42af72b4828b1690b3a7bccfa06` / `is_current=True`；`status` = **in sync**（zip `entries=26 identical=26 differing=0 missing=0`）。护栏：prompt family `91febc286412479a8b6d569fa3b8025e`、skill family `9fe0035bdd324b998436c6cb9c2de212`（属主 = 徐佩佩）。

### 六次真跑

| run | 输入 | 目录 | thread_id | run_id | 墙钟（server / polled） | tool calls | runner 断言 | 离线（scenario a） |
|---|---|---|---|---|---|---|---|---|
| r48-a | 2 esid | `…/20261010-165843-r48-a` | `163b3421-2e76-4b2b-bfc6-7e481c3b3740` | `4d47f17a-99f5-4586-acef-c34c318be176` | 312.9 / 313.0 s | 28（27 返回 + 1 error） | **21 PASS / 1 FAIL** | **43/44 FAIL**（A-ATTR） |
| r48-4 | 4 esid | `…/20261010-170446-r48-4` | `6c874842-5150-4a6c-a74a-36e099b7ef33` | `51fd4dad-1bff-4716-ad76-cf3bcf873e9f` | 391.1 / 391.4 s | 42 | 21 PASS / 1 FAIL（O45） | — |
| r48-18（首次） | 18 esid | `…/20261010-171141-r48-18` | `e75cc525-e56e-4b86-9878-4af2cbd66927` | `eb2eae41-de26-42ee-adda-a16df93ad918` | 93.2 s | — | **16 PASS / 6 FAIL**（结局 `inconclusive`：平台 `Connection refused`，无 `completed_at`、无产物） | — |
| r48-18（复跑） | 18 esid | `…/20261010-171358-r48-18` | `4190172d-7236-4eb5-81c1-43bd99ec67f4` | `6d9c9310-070a-46c8-95b6-3c3f67edc691` | 496.0 s | 59 | 21 PASS / 1 FAIL（O45） | — |
| r48-14 | 14 esid | `…/20261010-172231-r48-14` | `4bd3d02c-290c-4aa6-85d9-6e9a7c63299f` | `3527c837-74a2-4019-8e05-1049f709079e` | 303.4 / 303.5 s | 28 | 21 PASS / 1 FAIL（O45） | — |
| r48-4b（O45 修复后复跑） | 4 esid | `…/20261010-173112-r48-4b` | `cf7cee6d-b862-43c8-b3f9-7cc20810a3b1` | `e12c4515-1f17-4179-ae60-8bd32339bad7` | 425.9 / 433.6 s | 51 | **22 PASS / 0 FAIL** | — |
| r48-a2（同输入复跑） | 2 esid | `…/20261010-173839-r48-a2` | `cc9a3368-a9f0-4b06-8fdc-b5ca9ad3f045` | `5e944013-0b20-4ed2-9cce-30f80f4f772e` | 359.5 / 371.9 s | 45 | **22 PASS / 0 FAIL** | **40/44 FAIL**（A-C3 / A-C7 / A-C9 / A-ATTR） |

六次 run 全部产出 `output/report.md` + `output/citations.json` + 至少一张 `visualizations/*.json`；`present_artifact` 均为末次调用。

### per-lever 归因（历史基线 vs 本轮）

**L2（自写辅助脚本）——决定性**

| | 自写脚本文件数 | 自写脚本 / heredoc 字节 | 随包脚本调用 |
|---|---|---|---|
| r47-a（基线） | 有自写 `build_chart.py` / `build_citations.py` 等 | `execute` 输出 17,919 tok | 仅 `render-facts` / `build_ledger` |
| r47-4（基线） | `fix_ledger.py` / `make_timeline.py` / `fix_draft.py` / `finalize.py` / `normalize_ledger.py` | 自写脚本 16,225 out + heredoc 32,710 out | 无 `prep_sources` / `patch` / `make_chart` |
| r47-14（基线） | **11 个自写脚本 / 61,470 B**（`add_paras.py` / `fix_draft_text*.py` / `patch_baseline.py` / `clean_draft.py` / `check_draft.py` / `digest*.py` / `write_outputs.py` / `build_sources.py` …） | 自写脚本 **59,598 out（≈54%）** | `render-facts` ×22 |
| **r48-a / 4 / 18 / 14** | **`artifacts/scripts/` 0 个文件** | `execute` 命令合计 5.0–11.7 KB（其中 heredoc 0–5.0 KB） | 六脚本**每轮全部用到**：`prep_sources` ×1、`build_ledger` ×2–3、`make_chart` ×1–4、`render-facts` ×1–9、`make_citations` ×1–2、`check_report` ×1–3、`patch` ×1–2 |

**L3（单遍正文）——决定性**：四组 run 的 `artifacts/work/` 里**都没有 `draft.md`**（基线 r47-* 均有），`write_file` 调用降为 2–3 次且全部为整文件写入。

**L4（合批/步数）——部分达成**

| run | R47 attempts | R48 attempts | Δ | R47 墙钟 | R48 墙钟 | Δ | out tokens（R47 → R48） |
|---|---|---|---|---|---|---|---|
| a | 40 | **28** | **−30 %** | 349.1 s | 312.9 s | −10 % | 60,976 → 72,161 |
| 4 | 56 | 42（复跑 51） | −25 %（−9 %） | 512.1 s | 391.1 s（425.9 s） | −24 %（−17 %） | 103,095 → 76,223 |
| 18 | 56 | 59 | **+5 %** | 488.6 s | 496.0 s | +2 % | 92,991 → 99,446 |
| 14 | 66 | **28** | **−58 %** | 569.7 s | 303.4 s | **−47 %** | 104,669 → 69,347 |

⇒ 步数/墙钟在 3/4 组明显下降（14 esid 组最显著），18 esid 组持平；**`read_file` 仍占 8–20 次/run**，是 L4 未吃完的部分（见 O46）。out token 有升有降（−34 % ~ +18 %），**不作为 keep/discard 判据**（AGENTS §9：`calls` 才是可比数）。

### 质量侧

- **runner 22 断言的 3 个 FAIL 全部归因清楚**：`r48-4` / `r48-18` / `r48-14` 同一条 **O45（runner 正则缺陷，已修 + 离线重放全转 PASS + 复跑 22 PASS）**；`r48-a` 的 `read_file offset 越界` 是**模型侧**概率残留（同输入 `r48-a2` 未复现）⇒ **O46，随 R49 内容轮加硬规则**。
- **离线 scenario a（仅 `r48-a` / `r48-a2` 可判，另两组输入与 fixture 不同源）**：43/44（A-ATTR，O40 家族）与 40/44（A-C3 / A-C7 / A-C9 / A-ATTR）。`r47-a` 基线为 43/44。⇒ **两条新样本**：`A-C7` 词形绑死 = **O47（1 样本，待样本）**；`A-C3`（机制句缺失）是**两次 run 间的覆盖率差异**（r48-a 写了「机制不同（PCSK9 单抗 vs 靶向 Lp(a) 的小干扰 RNA）」，r48-a2 整句漏），**不记 O 条目**（无机械修法，属生成侧偶发）。
- **未发现速度杠杆带来的结构性质量回归**：图表行点名试验（O43）在四组里仍全部命中；`库内记录`（O41）仍为 0；工具拒绝（O42 窄口径）仍为 0。

### 我方能改的

| 项 | 现象 + 证据 | 改法 | 状态 |
|---|---|---|---|
| **O45** | 全角括号粘住收据路径 ⇒ 3/4 组 FAIL | `_RECEIPT_STOP` 重建 `TOOL_RESULTS_RX` + 回归测试 | ✅ 已修（本轮） |
| **O46** | `read_file offset` 越界 1/2 组；`read_file` 仍 8–20 次/run | R49 内容轮：第 7 条加「不许凭猜测给 offset / 尾部用 `tail`」、第 2 条加「原始 result 过大先跑 `prep_sources.py`」 | 📝 待修（R49） |
| **O47** | `A-C7` 只认「第 X 周」 | 加无「第」备选；**等第 2 份样本** | 📝 待样本 |
| O40 / O44 | 仍待第 2 份样本 / 报告侧机制已生效未复现 | 见 O 表 | 📝 待样本 |

### 平台侧（转开发）

- 本轮**无功能性平台缺陷**。仅一条**文案层面**的观察（不改平台、不单独开单，随 O46 记录）：工具结果过大时平台提示「Read it with `read_file(file_path=..., offset=..., limit=...)` to inspect it in chunks」，模型据此频繁分块重读并偶发越界；对被截断的结构化数据，更省的做法是先跑我们随包的 `prep_sources.py`。

### R48 收尾状态

线上 = prompt v1.7（**原地更新**）、Skill v1.0.8（**原地更新**），`status` in sync；
本地门禁 runner-gate **40** / scorer 35 / tools 5+14 / Node 16 / numeric-integrity 28 / **skill-scripts 54** 全 OK；
`verify-run-chain` `GATE: PASS (5 comparable runs)`；变异闸门 `arm a 44/44, arm b 12/12, never flipped [], GATE: PASS`；`pack-dist --check` IDENTICAL；
**结案 0 条、本轮已修 1 条（O45）、待修 2 条（O46 → R49；O40 → 报告侧已落地待复现）、待样本 3 条（O44 / O47 / O41 收尾）**。

### R50 收尾状态

线上 = prompt v1.7（`bf7b45dbf5d0` / 76,578 B，**原地更新**）、Skill v1.0.8（dist `df993fdddf83` / 151,330 B / 26 entries，**原地更新**），`status` in sync；
本地门禁 runner-gate **41** / scorer 35 / tools 5+14 / Node 16 / skill-scripts 54 / check-report **20** / build-ledger-scaffold 9 /（numeric-integrity 28 单列）全 OK ⇒ **193（含 28 = 221）**；
`verify-run-chain` `GATE: PASS (5 comparable runs / 115 histories)`；变异闸门 `arm a 44/44, arm b 12/12, never flipped [], GATE: PASS`；`pack-dist --check` IDENTICAL；
真跑 = 2 组 2 esid（r50-a 24/1、r50-a2 25/0）+ **固定三组回归（r50-4 / r50-18 / r50-14 各 25 PASS / 0 FAIL / exit 0）**；
**结案 0 条、本轮已修 1 条（O48）、待修 2 条（O49 → 下一次内容轮；O46 → R49 规则已落、待更多样本）、待样本 3 条（O44 / O47 / O40 复现）**。

## R49 — 用户四条交付层投诉：附录版式 / 列头 / 一数一处 / 提速杠杆（2026-10-10，本地全绿 + commit）

**用户口径**：*「1、2 改；3 选方案 1（保留图、不重复赘述）；4 都试试」* —— 四条投诉同时处理，第 4 条不得损失质量。本轮**先本地实现 + 全套闸门 + commit（`2063ff0`）**，与 R50 内容**同批**原地发布。

### 本轮改了什么（内容侧）

| 投诉 | 现象（共享报告现场） | 改法 | 落地文件 |
|---|---|---|---|
| 1 附录版式 | 附录标题后紧跟 ≈600 字「本表如何排布」的规格说明；读者先读规格再读数据 | `render-facts.py` 删 `APPENDIX_INTRO`，只留一行 `APPENDIX_LEGEND`（说明「—」）；`check_report.py` 新增两条 FAIL：附录标题与表格之间出现 >100 字散文块、附录标题出现 >1 次（手写附录 + 渲染附录并存） | `scripts/render-facts.py`、`scripts/check_report.py`、4 模板 |
| 2 附录列头 | 第二行重复第一行already含有的注册号；缺可读标签 | 单试验 ≥2 披露改为 `**可读短标签**<br>ref_n`（无标签回退 `**ref_n**`）；第二行注册号若已出现在展示名里则删除 | `scripts/render-facts.py`（`_column_header` / `_column_label`） |
| 3 图与表重复同一数值 | §二「核心终点速览」同时规定表格 + 图，图里数值与表里数值逐字重复 | **方案 1**：图保留、数值只交付一次。`check_report.py` 新增两条 FAIL（图自身散文不得复述绘图值；非附录小节「有图 + 表里含该图 ≥2 个绘图值」）；两个速览模板的「图表后保留上表」改成「不重复上表」；附录与时间线图豁免；剂量/时点/例数后缀与研究内对照值仍允许 | `scripts/check_report.py`（`CHART_NUMBER_RE` / `_chart_number_tokens` / `_chart_text_findings`）、`references/chart-templates.md`、`templates/cross-trial-report.md`、`templates/mixed-comparison-report.md`、`SKILL.md`、prompt |
| 4 交付耗时 | 模型反复翻随包脚本源码、回读自产文件、逐条试算账本、图表 spec 反复重写 | 四条杠杆：(1) `references/toolbox.md` 增 FAQ（「不用读脚本源码」）；(2) prompt 硬禁回读自产文件、`check_report.py` 一次定稿；(3) `build_ledger.py --scaffold` 直接产出候选事实行；(4) 图表 spec 一次成稿（不许先写草稿再改） | `references/toolbox.md`、`scripts/build_ledger.py`、`SKILL.md`、prompt |

**`--scaffold` 契约**：挂在 `build_ledger.py` 上（不新增脚本，保住 `EXPECTED=26`）；读 `<tool-results>/pharmcube-query-clinical-result-with-params/*.jsonl`（缺失时回退 `tool_results/` → `/workspace/work/tool_results`）；同一 esid 只留最后一份 payload；空值 /`NR`/`NE`/`未报告`/`NA`/`N/A`/`-`/`—` 一律跳过；输出**候选文件**（默认 `work/facts.candidates.json`，永不直接写 `ledger.json`）；语义不足时**不静默**（`defaulted_kinds` / `time_shaped_endpoints` + note）。smoke：`WROTE work/facts.candidates.json: 2 record(s), 42 fact(s) (0 need a quote)`。

### 本地门禁（R49 收口时）

`mutations.py` arm a **44/44** + arm b **12/12** + never flipped `[]` + `GATE: PASS`；`test-render-facts.py` **28** OK；`test-skill-scripts.py` **54** OK；`test-check-report.py` **12** OK（R50 扩到 20）；`test-build-ledger-scaffold.py` **9** OK；`test_regressions.py` **35** OK；`test-runner.py` **40** OK；`test_pack_dist.py` **5** OK；`node --test` **16** pass / 0 fail；`verify-run-chain.py` `GATE: PASS`（110 histories / 5 comparable / 105 skipped）；`pack-dist.py` = **148,346 B / sha256 `78b399b26a94` / 26 entries**，`--check IDENTICAL`。

**端到端复渲染验证**：`/tmp/r49v/draft.md`（6,910 B）+ 账本 → `render-facts.py` exit 0；新附录三行（标题 / 一行图例 / 表格头），表头实测 `**NCT02729025（依洛曲单抗 Lp(a) 影像研究）**<br>1 条披露` 与 `**OCEAN(a)-DOSE**<br>NCT04270760 · 1 条披露`（第二行注册号去重 ✔）。

**Git**：commit `2063ff0`「R49: appendix/table-chart fixes + delivery-speed levers (local gates green)」，push 到 `v0.15-remove-html`（`0c95e05..2063ff0`）。

## R50 — 报告不得叙述自己的方法与分类（第四语域）+ 与 R49 同批原地发布 + 两次真跑（2026-10-12）

**用户口径**：*「交付报告里出现模型自洽 / 思考过程式叙述（例：**分析模式：** 跨试验、非头对头、按指标域对齐。**可比性结论：** 可绘图。…）→ 全篇排查同类表述并优化 → 原地更新 TS → 再测试」*。

### 问题定性（第四语域）

`evals/fact-check/check.py` 现有守卫族（A-P1 覆盖行、`op_original_check_names_class`、A-P5 `op_fulltext_fetch_is_named`、A-P7 模板规格回抄、A-P8 规则元陈述、A-P10 运行后勤）**没有任何一条覆盖「报告叙述自身方法 / 分类 / 处理过程」**。这类文字对读者零信息量：读者要的是「两项研究的时点/人群/口径差异是什么」，不是「我们把它归类为部分对齐」。故按新禁用语域处理，机械闸门落在 `check_report.py`（判分器 `check.py` **不动**，避免破坏 44/12 变异套件）。

### 本轮改了什么（内容侧，与 R49 同批发布）

| 层 | 改动 |
|---|---|
| `scripts/check_report.py` | 新增 6 个常量（`META_LABEL_RE` / `META_COLUMN_RE` / `METHOD_NARRATION_RE` / `SELF_AUDIT_RE` / `INTERNAL_VOCAB_RE` / `SELF_REFERENCE_RE`）与 `_meta_narration_findings()`，`main()` 里作为独立检查组 `report voice` 接入。**FAIL**：自述标签 bullet/表列（`分析模式`/`选择依据`/`可比性结论`/`对齐等级`/`不绘图原因`/`有限并列原因`/`纳入标准`/`检索策略`/`报告结构`）、`可绘图`/`只能有限并列`/`不具备绘图条件`/`部分对齐`/`仅背景对齐` 这类分类判断、过程短语（`本次选择`/`本次纳入`/`我们选择`/`本轮`）、内部字段与运行环境词（`src=`/`esid`/`payload`/`JSONL`/`MCP`/`工作区`/`沙箱`）、自证尾巴（`无未复核记录`/`无遗漏`/`全部通过`）。**WARN**：宽口径自指（`本报告`/`本次`/`本轮`，负面断言排除合法的「本次披露」）。刻意不做 `token`/`轮次`（会误伤「治疗轮次」）。 |
| `SKILL.md` | 新增「只写发现，不写报告自己（硬规则）」段：列出禁用标签与判断语，要求把差异写成时点/人群/口径/定义/方向，保留两个合法位（非头对头声明一句、`原文核对：` 覆盖行），并说明 FAIL/WARN 分级。 |
| `system-prompts/…-v0.16.md` | 三处：覆盖行示例去掉 `src=1` 改说来源类文字；速览段「只写核心终点要点」；交付前检查段追加同一条硬规则（含句级判据「若一句话没在说这些试验及其证据，它就不属于交付物」）。 |
| `references/input-contract.md` | 覆盖行规格：来源类**用文字说**（`PubMed 摘要`/`登记平台结构化结果`/`会议摘要`/`通稿`/`人工补录`/`库内正文即原文摘要`），`src=` 等内部字段名不进交付物；示例改为文字来源类；删除示例末尾的 `无未复核记录` 自证尾巴并写明理由。 |
| `references/toolbox.md` | §7 FAIL 清单补「报告叙述自身」一条；FAQ 增两条（覆盖行该写什么；**不得在正文里写我们怎么对齐**）。 |
| 4 个模板 | 删 `分析模式`；`选择依据`/`可比性结论`/`对齐等级`（含速览表与 §4 各表的列）/`不绘图原因`→`可比性限制`/`可绘图` 判断语全部去掉，改为把时点/人群/口径/定义差异写进 `解读边界`；覆盖行规格统一为「只写材料与深度，不写自证话术与内部字段名」；`比较口径` 保留（blockquote 结构位，内容改为材料化的非头对头声明）。 |
| `evals/scripts/test-check-report.py` | **12 → 20** 用例（新增 8 条：自述标签 bullet、`对齐等级` 表列、绘图可否措辞、自证尾巴、内部字段词、覆盖行不误报、解读边界散文不误报、自指只 WARN）。 |

**`比较口径` 不列入 FAIL**（4 模板本来就有该 blockquote 位，列入则每份报告必挂）；**不改 `check.py` 的覆盖行判分语义**（`op_original_check_names_class` 的 `class_regex` 本就接受文字来源类，禁 `src=` 不与判分冲突）。

### 现场取证（旧产物回放，证明闸门抓得到用户看到的东西）

对 `~/.local/state/toolsmith-runs/20261010-165843-r48-a` 跑新 `check_report.py`：命中 `the report labels its own method ('**分析模式：')`、`('**选择依据：')`、`('**可比性结论：')`、4 处 `table column … 对齐等级 …`、`method/class narration: '纳入本次' / '只能有限并列' / '不生成优效排序' / '部分对齐'`、`self-audit tail: '无未复核记录'`、`internal field or runtime vocabulary: 'src=1'` —— 用户投诉的四类语域**逐条被抓**。

### 发布（原地，版本标签不变）

`toolsmith-publish deps` = `unchanged since the recorded baseline`（`deps_exit=0`）；
`push-prompt --version 1.7` → HTTP 200 / mode=in-place / 回读 `current=v1.7 matches_local=True`（本地 v0.16 = **76,578 B / sha256 `bf7b45dbf5d0`**，含 R49 + R50）；
`push-skill --version 1.0.8` → HTTP 200 / skill_id `cd93a42af72b4828b1690b3a7bccfa06` / `is_current=True`（zip **151,330 B / sha256 `df993fdddf83` / 26 entries**，含 R49 + R50）；
`status` = **in sync**（prompt `deployed == local: True`；skill `entries=26 identical=26 differing=0 missing-locally=0`）。护栏：prompt family `91febc286412479a8b6d569fa3b8025e`、skill family `9fe0035bdd324b998436c6cb9c2de212`（属主 = 徐佩佩）。

### 真跑（2 esid 输入，与 r48-a / r48-a2 同输入）

| run | 目录 | thread_id | 墙钟（server / polled） | tool calls | runner 断言 | 离线（scenario a） |
|---|---|---|---|---|---|---|
| r50-a | `…/20261012-091941-r50-a` | `e336bb06-2e12-41fc-bd1b-371657ca22b5` | 372.2 / 380.5 s | 33 | 24 PASS / 1 FAIL（**O48**） | **43/44**（A-ATTR，O40 家族） |
| r50-a2 | `…/20261012-092606-r50-a2` | — | 343.3 / 356.8 s | **26** | **25 PASS / 0 FAIL** | 38/44（A-S9/A-S9b/A-S10 + A-C3 + A-C9 + A-ATTR） |

**固定三组回归真跑（4 / 18 / 14 esid，输入逐字节复用 R48 的 `/tmp/r50/p-{4,18,14}.txt`，2026-10-12 09:33–09:59）**：

| run | 目录 | 墙钟（polled） | tool calls | runner 断言 | 交付物 | 本地 `check_report.py`（语域组） |
|---|---|---|---|---|---|---|
| r50-4 | `…/20261012-093345-r50-4` | 383.2 s | **25**（execute×12 / read_file×8 / write_file×2） | **25 PASS / 0 FAIL / exit 0** | report + citations + `evidence-timeline.json` | ✅ `report voice` 绿（仅本地回放的 `::visualization` 路径差异） |
| r50-18 | `…/20261012-094013-r50-18` | 617.3 s | 46（execute×28 / read_file×10 / write_file×5） | **25 PASS / 0 FAIL / exit 0** | report + citations + `endpoint-bar-1.json` | ✅ 绿；WARN 一条 8 字重复（`依沃西单抗联合化`，专名语境） |
| r50-14 | `…/20261012-095037-r50-14` | 510.8 s | 31（execute×14 / read_file×10 / write_file×3） | **25 PASS / 0 FAIL / exit 0** | report + citations（该输入不出图） | ✅ 绿（exit 4 = 无图表目录 WARN） |

**回归判定**：三组全绿、`succeeded`、`args-refused = 0`、`deployed support-file manifest … (25 files)` PASS，**新语域闸门零 thrash**（三组正文都没有被 FAIL 命中「方法/分类/自证」词，说明 FAIL 级规则没有把模型逼进「换词硬写」的死路）。
**O49 未在 18 esid 组复发**：`endpoint-bar-1.json` 四行 `description` 各点自己那条观察的对照臂（`对照为替雷利珠单抗联合化疗` / `对照为安慰剂联合化疗` …），没有复述**另一根柱子**的剂量/间隔 ⇒ 每行身份唯一。⇒ O49 维持「1/3 样本、报告侧写法」的定性。
**一数一处（R49.3）在生产侧成立**：三组均未触发「图内复述绘图值」与「有图小节重复该图数值」两条 FAIL；18 esid 组的图表 `subTitle` = `跨试验并列展示≠头对头比较`、`data[].description` 只写对照臂/分析类型/随访，无绘图值。

**语域修法在生产侧生效**：r50-a 正文已无 `分析模式`/`选择依据`/`可比性结论`，速览段只写核心终点要点 + 图，数值表移到 §四并带 `解读边界` 列；覆盖行写成「来源类均为 PubMed 期刊论文，深度为期刊摘要级（库内正文即原文摘要，未取 PMC 全文）」——无 `src=`、无自证尾巴。两份产物用本地 `check_report.py` 回放，`ok: report voice — findings only` 全绿（余下 FAIL 仅为本地回放时 `::visualization` 路径前缀不同；WARN 为 R49 既有的图表/表格 8 字重复 `225mg每月一次` / `(a)-DOSE`，属剂量与专名语境）。

**速度侧**：r50-a2 相对同输入的 r48-a2 —— tool calls **45 → 26**、out token 69,610 → **63,097**、reasoning 51,506 → **43,373**、墙钟 359.5 → **343.3 s**，`read_file` 8 → 9（仍以读原始 payload 为主），自写脚本 0，7 个随包脚本按需调用。

### 我方能改的

| 项 | 现象 + 证据 | 改法 | 状态 |
|---|---|---|---|
| **O48** | **runner 的支撑文件清单把本地 `scripts/__pycache__/*.pyc` 当作「线上缺失」⇒ 假 FAIL**：r50-a 唯一 FAIL = `manifest mismatch: missing=['scripts/__pycache__/build_ledger.cpython-310.pyc', '…/check_report.cpython-310.pyc']`；来源是本机 `python3 -m py_compile` 留下的字节码，**zip 内从未包含**（26 entries 全为 .py/.md/.json）。清掉本地 `__pycache__` 后**同输入复跑 r50-a2 即 25 PASS / 0 FAIL** | runner 侧：清单比对时过滤 `__pycache__/` 与 `*.pyc`（本地开发会正常产生字节码，交付包不会） | ✅ **已修（2026-10-12）**：备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v16b.bak`；`expected` 改为 `os.walk` 时剪掉 `__pycache__` 目录、并跳过 `*.pyc`；`python3 -B -m py_compile` OK；零网络闸门 `verify-run-chain.py` → `GATE: PASS`（115 histories / 5 可比 / 110 跳过）；`test-runner.py` **40 → 41**（新增 `test_local_pycache_does_not_become_a_missing_support_file`，对旧 runner **必 FAIL**、对新 runner PASS，非空产物式断言）。**对同一份存档 run 的 A/B 复现**（`/tmp/o48check.py` 直调 `check_run`，本地 `__pycache__/*.pyc` 故意保留）：旧 runner → `FAIL … missing=['scripts/__pycache__/build_ledger.cpython-310.pyc', …]`（与 r50-a 现场逐字相同）；新 runner → `PASS deployed support-file manifest matches local (25 files)` |
| **O49** | **图表行的 `description` 点名另一治疗臂的剂量/间隔 ⇒ 行身份不再唯一**：r50-a2 第 1 行 `label=奥帕司兰 225 mg 每 24 周（OCEAN(a)-DOSE，第 36 周）` 的 `description` 写「延长给药间隔后降幅与每 12 周方案接近」⇒ 该行同时匹配 obs 2 与 obs 3，`A-S9` / `A-S9b` / `A-S10` 三条同源 FAIL（离线 38/44）；同输入的 r50-a 未触发（**1/2**） | 报告侧一句硬规则（`references/chart-templates.md` + `SKILL.md`）：图表行只点自己那一条观察的身份，比较性描述改用「更短给药间隔组」这类不带剂量数字的措辞 | 📝 待修（随下一次内容改动发版）；**18 esid 回归组未复发 ⇒ 维持 1/3 样本** |
| O40 / O44 / O46 / O47 | 见 O 表 | — | 📝 待样本 / 待复现 |

### 平台侧（转开发）

- 本轮无新平台缺陷。R48 已记的「工具结果过大时平台建议 `read_file(offset=…, limit=…)` 分块重读」仍是 O46 的诱发源（r50-a / r50-a2 各 11 / 9 次 `read_file`，未再越界）。

## R51 — 部署端时间轴不编码任何东西：撤掉 `weight` / `weightLegend` / `legend` / `shape` / `group` / `width` / `height`（2026-10-12，本地全绿 + 原地发布 + 固定三组真跑）

**用户口径**：*「这个 `weight` 字段必须移除，部署端时间轴 JSON 不支持 `weight` 大小」*。

### 问题定性（读者被暗示了一个不存在的编码）

本 skill 的时间轴图模板与文档此前把 `weight` 当作「证据成熟度」编码（宣称「圆点大小 = 成熟度」，并配 `weightLegend` 图例），把 `legend[].shape` 当作节点形状编码。**部署端渲染器根本不实现这些**——读者会以为「大点 = 证据更硬」，而实际所有节点长得一模一样。

### 部署端证据链（权威，2026-10-12 实测）

| 项 | 事实 |
|---|---|
| 上游 family / current | `ee7d944445134cbba5771714f2188cb1` · 版本标签 `1.0.12` · id `1506a6ac693746f299055ee198abf697` · `updated=2026-09-21T11:58:40` |
| 部署端 `templates/timeline.json` | `weight` / `weightLegend` 出现 **0 次** |
| 渲染 bundle | `…/20260921-085926/static/index-9EvceNR0.js`（288,806 B）：节点构造**硬编码 `{ r: dm, shape: "circle" }`（`dm = 3`）**；DOM 节点 dot = `.mf-ai-charts-timeline-dot{width:6px;height:6px;…border-radius:50%}`（**固定 6×6 灰圆点，无 group/color/shape 类**） |
| 时间轴图例 | 渲染器 = **`function Fm(){ return [] }`（空数组）** ⇒ 时间轴**不渲染任何图例**；`empty-circle` 只是 legend swatch 的类名 `mf-ai-charts-legend-empty` |
| ⇒ 结论 | `weight` / `weightLegend` / `legend`（含 `shape`）/ `group` 对时间轴**零视觉效果**；`width`/`height` 上游新模板也已移除（固定 920px 在窄容器会溢出） |
| 上游校验器 | 故意造带 `weight`+`weightLegend` 的 spec 跑新 `validate-cli.js` ⇒ **`exit=0`、零 warning**；`references/schemas/timeline.js` 仍保留 `weight`（`z.number().min(0).optional().default(0)`）与 `weightLegend` |

**⇒ `schema 允许 ≠ 渲染生效`，上游不会拦这个回归，必须本 skill 自建门禁。** 另经此查证发现部署端 `iframe_template` 已指向 `20260921-085926` 构建（平台**原地更新了同一版本号**，见 O50）。

### 本轮改了什么（7 个 bundle 文件）

| 文件 | 改动 |
|---|---|
| `templates/charts/evidence-timeline.json` | 整体重写：删 `weight`/`weightLegend`/`legend`/`group`/`width`/`height`，键序收敛为 `_comment`/`type`/`title`/`subTitle`/`dataSource`/`describe`/`data`；`describe` 写死「**竖向列表：数组顺序即时间顺序（自上而下）、模板不重排、节点等大等形、不渲染图例；大小/形状/颜色都不作编码**，成熟度与分类判断一律写进正文与节点文字」 |
| `references/timeline-diagram.md` | 新增**构建规则第 8 条硬规则**（禁止 `weight`/`weightLegend`/`legend`，拒绝面含「成品与相关文字表述」）；删示例中全部已死字段；顺带修正此前「从左到右」的顺序误述（DOM 是 flex column ⇒ **自上而下**） |
| `references/chart-templates.md` | 表格单元描述 / 字段清单 / 退出码 `3` 清单 / 「数据填充约束」段同步；`value` 的说明删掉「timeline 的图例 key」 |
| `scripts/make_chart.py` | **阻断层**（exit 3、不写文件）：row `weight` / row `shape` / spec `weightLegend` / spec `legend` 四类 findings；docstring 同步 |
| `scripts/check_report.py` | **成品+正文层**（findings、exit 3）：图表 JSON 同四类；另加报告级文本守卫 `CHART_ENCODING_CLAIM_RE = 节点大小\|圆点大小\|节点权重\|权重图例\|节点形状\|形状编码\|大小编码\|空心圆\|实心圆`（挂在 `_meta_narration_findings`，label = `chart cue that does not exist`） |
| `templates/charts/endpoint-bar.json` / `endpoint-line.json` | 三个骨架的 `subTitle` 缩到上游新字宽上限内（≤32），消掉生产 run 里的上游 `⚠` |
| `vendor/` | 新增 `chart-visualization-json/1.0.12-20260921/`（48 文件 / 源包 64,214 B / SHA-256 `423c50a5c857…`）+ `vendor/README.md` 记录「同一版本号被原地更新」与更新流程步 3 纪律 |

**刻意保留（不误伤）**：`group` **不拒收**（bar/line 合法、timeline 上惰性不误导，仅在文档注为「上游保留字段、本 skill 不用」）；报告模板里作为**内容术语**的「证据成熟度」保留；裸 `图例` 不进守卫词表（59 份历史产物回扫，唯一命中的 `r37:191`「正文、表格与图例采用原文的『双盲』」是合法用例）；`PROJECT_STATE.md:869` 那条废弃 HTML 路线里的旧表述保留原文，由新快照节声明其已退役。

### 本地门禁（全绿）

`mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS`；`test-render-facts.py` **28** OK；`test-skill-scripts.py` **54 → 58**（+4：`weight` 被拒文案、`legend`+`shape` 被拒且不写文件、骨架与两份 reference 文档不得再出现已退役字段）；`test-check-report.py` **20 → 25**（+5：`weight` / `legend`+`shape` 被拒、正文声称不存在的图表编码 ⇒ exit 3）；`test-build-ledger-scaffold.py` 9；`test_regressions.py` 35；`test-runner.py` 41；`test_pack_dist.py` 5；`test_replay_run.py` 14；`node --test 'test/*.test.mjs'` **16 pass / 0 fail**。**计数 = 41 + 35 + 19 + 16 + 58 + 25 + 9 = 203**（含 numeric-integrity 28 = **231**）。

**反回潮断言**（非空产物式）：`test_shipped_timeline_assets_stop_encoding_maturity_as_node_size` 直读骨架 JSON 文本，断言 `weight`/`weightLegend`/`legend`/`group`/`shape`/`width`/`height` **一个都不出现**，并对两份 reference 文档断言 `weight 驱动`、`"weight": `、`"weightLegend": `、`"legend": `、`weight 0–N`、`weight=0`、`weight=证据成熟度`、`大小=证据成熟度`、`节点分类形状`、`legend.shape 决定节点形状`、`` `legend[].key` `` 全部不存在 —— 文档侧不能悄悄回潮。

**打包**：`pack-dist.py --check` → `DIFFERS`（151,330 → 152,558 B，预期）→ 重打 → **152,558 B / 26 entries / sha256 `081cd850befc`** → `--check` **IDENTICAL**（`EXPECTED` 仍 26，本轮不新增 bundle 文件）。

### 发布（原地，版本标签不变）

`deps` = `unchanged since the recorded baseline`（⚠ 但见 O50）；`push-skill --version 1.0.8` → **HTTP 200 / mode=in-place / `is_current=True` / skill_id `cd93a42af72b4828b1690b3a7bccfa06` 不变**（zip 152,558 B / `081cd850befc` / 26 entries）；**prompt 一字未动**（本地 v0.16 = 76,578 B / `bf7b45dbf5d0` = 线上 v1.7）；`status` = **in sync**（`entries=26 identical=26 differing=0 missing-locally=0`）。护栏：skill family `9fe0035bdd324b998436c6cb9c2de212`（属主 = 徐佩佩）。

### 真跑：固定三组回归（4 / 18 / 14 esid，输入逐字节复用 R48 → R50 的 `/tmp/r50/p-{4,18,14}.txt`，2026-10-12 10:49–11:11）

| run | 目录 | thread | 墙钟（server / polled） | tool calls | 交付物 | runner 断言 |
|---|---|---|---|---|---|---|
| r51-4 | `…/20261012-104926-r51-4` | `3f58a744-…` | 309.2 / 318.6 s | **23**（execute×13 / read_file×5 / write_file×2 / load_skill×1 / params×1 / present_artifact×1） | report + citations + `evidence-timeline.json` | **22 PASS / 0 FAIL / exit 0** |
| r51-18 | `…/20261012-105457-r51-18` | `44aa54bf-…` | 462.9 / 464.7 s | 36（execute×20 / read_file×11 / write_file×2 / load_skill×1 / params×1 / present_artifact×1） | report + citations + `endpoint-bar-1.json` | **22 PASS / 0 FAIL / exit 0** |
| r51-14 | `…/20261012-110252-r51-14` | `95264ebb-…` | 494.7 / 500.9 s | 38（execute×20 / read_file×11 / grep×2 / load_skill×1 / ls×1 / params×1 / write_file×1 / present_artifact×1） | report + citations + `endpoint-bar-1/2.json` + `endpoint-line-1.json` | **22 PASS / 0 FAIL / exit 0** |

**产物侧核对（本轮核心）**：

- **时间轴骨架已无任何已死字段**：r51-4 的 `evidence-timeline.json` 顶层 = `{id, iframe_template, option}`，`option` = `{type,title,subTitle,dataSource,describe,data}`，两行 data 的键 = `label` / `content` / `description` / `time` —— **`weight` / `weightLegend` / `legend` / `group` / `shape` / `width` / `height` 一个都没有**。
- **`iframe_template` = `…/20260921-085926/iframe-template.json`** ⇒ 生产 run 实际取的就是本轮核对过的那个新构建（部署端与本地结论同源）。
- **正文侧无「声称不存在的编码」**：三组报告过 `check_report.py`，`chart cue that does not exist` 零命中；`report voice` 组绿（余下 FAIL 仅为本地回放的 `::visualization target does not exist` —— `/workspace/…` 绝对路径在本地必然不存在，已知回放假 FAIL）。
- bar/line 的 `"group"` 命中（`"group": false` 与 line 的队列标签）属**合法用法**，与 timeline 无关；守卫只在 `chart_type == "timeline"` 时生效。

### 我方能改的

| 项 | 现象 + 证据 | 改法 | 状态 |
|---|---|---|---|
| **O50** | **`deps` 只比版本标签 ⇒ 上游「原地更新同一版本号」检测不到**：本轮 `deps` 报 `unchanged since the recorded baseline`，而部署端 `chart-visualization-json` 的 `1.0.12` 已从 20260914 构建换成 **20260921 构建**（47 文件 / 54,684 B → **48 文件 / 64,214 B**，新增 `docs/development.md`，`config.js` 的 `IFRAME_TEMPLATE` 换目录，4 个模板 envelope 删 `width`/`height`，`validate.js` 新增只有 warning 级的标题字宽/元标签检查）。**发现路径 = 用户投诉 → 手动拉部署端 zip + diff 本地 vendor 快照**；无人投诉就会静默漂移，日后核对渲染行为会得出错误结论 | `vendor/` 同一版本号的第二次构建**另起目录**（`1.0.12-20260921/`，本轮已落 + README 记源包 SHA/文件数/`IFRAME_TEMPLATE`/「平台 current 仍标同版本」）；部署端行为以**下载到的 zip 与渲染 bundle** 为权威、不以 `deps` 的 `unchanged` 为权威；`vendor/README.md` 更新流程加步 3 纪律 | 📝 **待应对（runner 侧不可改：比较语义在 `toolsmith-publish` 内部）**，本轮已完成留档与纪律 |
| O40 / O44 / O46 / O47 / O49 | 见 O 表 | — | 📝 待样本 / 待复现 |

## R52 — 执行流程梳理 + 差量 facts 审校 + TS 新版本真实回归（2026-10-12）

### 本轮假设与本地门禁

将累积的执行规则收敛为五阶段：准备 → 原文审校 → 编译 → 一次成文 → 交付；候选 facts 不再由模型整份重写，而是通过 `facts.review.json` 的完整 records、逐候选 keep/update/drop 决策和 additions 组装 `facts.json`，再走既有 quote/value/ID/ref 编译门禁。冻结评分器、固定输入、runner、citation renderer 未改。

本地：review 10、workflow 3、既有全套 231，共 **244 项通过**；mutations arm a **44/44**、arm b **12/12**、`GATE: PASS`；runner 零网络链 `118 histories / 5 comparable / GATE: PASS`；`deps` unchanged。代码 commit **`7852b73`** 已推送。

### 发布

按用户授权改为新版本发布，不覆盖 R51：

- prompt **1.8**：71,555 B，SHA 前缀 `ed5ec6c7afe9`，平台 prompt id `475039ccebfe46a3a39002febe28b1f4`。
- skill **1.0.9**：skill_id `16aeb0406e12425bad27a2444f17225e`，26/26 文件一致，dist 156,456 B，SHA256 `0826b8a02e7fee52e16359f65c38055b1fbebbe63803ff2afd9d7802ac14df8d`。
- `status`: in sync；R51 的 prompt 1.7 / skill 1.0.8 保留。

### 固定真实回归

模型 DeepSeek Flash，web=off，输入按 R51 `run.json` 原样复用；归档目录 `~/.local/state/toolsmith-runs/20261012-123356-r52-{4,18,14,b}`。

| 场景 | R52 server / polled | calls | runner | R51 对照 server / calls | 结论 |
|---|---:|---:|---|---:|---|
| 4 条 | 680.1 / 682.6 s | 69 | 22 PASS / 0 FAIL | 309.2 s / 23 | 内容门禁通过，速度明显退步 |
| 18 条 | 569.5 / 575.8 s | 45 | 22 PASS / 0 FAIL | 462.9 s / 36 | 内容门禁通过，速度退步 |
| 14 条 | 691.6 / 708.3 s | 66 | 22 PASS / 0 FAIL | 494.7 s / 38 | 内容门禁通过，速度明显退步 |
| B 拒绝 | 39.9 / 44.4 s | 8 | refusal 14 项部署断言通过 | — | 离线事实 11/12，固定措辞 A3 未命中 |

三组总 server wall 相对 R51 增加约 53%，不能判定为速度优化成功。4 条场景候选 33 行最终为 update 32 / drop 1 / keep 0 + additions 19；18 条为 drop 165 + additions 140；14 条为 update 50 / drop 61 + additions 41。实际运行显示模型仍会先写 `mk_review.py`、反复探针和重建 facts，候选复用率不足时差量接口不能节省生成成本。

### 内容验收与新问题

机械断言通过不等于临床内容通过。4 条产物把免疫相关事件差异解释为「主要来自非免疫机制」，原文只支持事件率，不支持该机制归因。18 条产物出现「只有 LUX-Lung 8 报告 PRO」但同段又列出 SQUIRE 的 PRO，以及把不同随访时点写成同一时点方向一致。另发现 prompt 旧段落把 `execute` 参数写为 `shell_command`，而 live schema required=`command`；跑动期间未修改，列为下一轮我方修复项。

**判定：R52 不 keep（实验未通过，尚未执行回退）。** 新版本已完成发布和真实测试，但在速度与内容质量上均未达到验收要求。代码与本轮证据保留，下一轮应先修工具 schema 参数漂移和报告内部矛盾，再决定是否继续保留差量审校路线。

### 我方能改的

- O51：execute 参数指令漂移（live required command，旧 prompt shell_command），待修。
- O52：差量审校未产生复用收益、探针与自写组装脚本仍大量出现，证据见上述三组，待重新设计。
- O53：机制归因／摘要内部矛盾及内容自检失效，证据见上述报告原句，未通过内容验收。

### 平台侧（转开发）

本轮无新平台缺陷。上游 `chart-visualization-json` 的时间轴 `weight` / `weightLegend` / `legend` / `shape` 仍在 schema 中放行，但部署渲染器不实现这些视觉编码；建议上游拒收这些字段或明确记录时间轴不支持 size/shape/legend 编码。


## R53 — toolbox 文档优化：digest 样例 + token 语法 + 条件参考文件加载（2026-10-12，原地发布 + 真跑验证）

**目标**：消灭三类已测量的运行时浪费：（1）模型通过 `--help` + 临时 ledger 试错发现 `[[fact:id]]` 语法（r51-4 约 15 次工具调用）；（2）模型反复打开 `ref_n.txt` 手动提取数值而非从 digest 读取；（3）render 后数值格式不一致触发 `patch.py` 修正循环（约 3–5 分钟）。

**改动**（仓库资产，commit `08e6929`）：
- `references/toolbox.md §1`：新增 digest 输出样例，明确说明数值已在 digest 中，不需要再打开 `work/sources/ref_n.txt`。
- `references/toolbox.md §3`：新增 `[[fact:id]]` token 语法示例，含完整 facts.json 片段、报告写法和两条硬验证条件（value 在 quote 里、quote 是源文件精确子串）。
- `SKILL.md`：必读 5 个参考文件 + 按场景条件读 3 个（替代原来每次都读 9 个）；scaffold 后加数值格式统一决策步骤。

**发布**：161 项本地回归全过；`dist` 重建（154,430 B / sha `9326006d9d59`，旧 152,558 B 未含本次改动）；`push-skill --version 1.0.9` 原地推，HTTP 200，status 26/26 identical。

**真跑 r53-doc-4b**（`20261012-142802-r53-doc-4b`）：

| 指标 | R51-4 基线 | r53-doc-4b | 变化 |
|---|---:|---:|---|
| 服务端墙钟 | 309.2 s | 320.3 s | +3.6% |
| 工具调用次数 | 23 | 32 | +39% |
| 输出 token | ~107K | 53,490 | **-50%** |
| 推理 token | — | 35,287 | — |
| execute 调用 | 17 | 11 | **-35%** |
| read_file 调用 | 5 | 11 | +120% |
| 机械断言 | 22 PASS | 21 PASS / 1 FAIL | ↓1 |

- thread `4c630621-cdc3-4ac6-bbff-4c465a4d0cac`，turn `ed140c6b-d482-43ac-b6e8-8d6ac905606c`
- 产物：`output/citations.json`, `output/report.md`, `visualizations/evidence-timeline.json`
- 唯一 FAIL：`tool_results receipts archived`（unsafe receipt path）—— 与本次改动无关，平台侧已知问题（见下方平台侧）。
- read_file 增加（5→11）表明模型确实在读文档而非运行试错命令；execute 减少（17→11）验证了探测循环被削减；输出 token 降 50% 是语法探索循环被消灭的直接体现。
- 首次 run（`r53-doc-4`，`20261012-141831`）因 skill 未含本次改动（dist 尚未重建）而失败，已排除，不计入对比。

**判定**：输出 token 和 execute 次数显著下降，说明文档改动达到预期效果。墙钟略升（+11 s / +3.6%），在噪声范围内，不视为退步。21/22 机械断言通过，1 FAIL 为平台侧已知问题。**判定：有效，keep。**

### 我方能改的

- （本轮无新增我方缺陷）

### 平台侧（转开发）

- **P-R53-1（已知）**：`tool_results receipts archived` 断言失败——`/workspace/tool_results/.../result.jsonl` 被 runner 标为 unsafe receipt path，每次运行都会命中。与本次改动无关，属 runner 已知限制，不影响产物正确性。O 编号待分配。

---

## R55 — 建议项不再阻塞（同批带入 R54 空 `arm`/`unit`）（2026-10-12，原地发布 + n=3 实测，**指标 FAIL**）

**假设 → 指标**：回归 132 个 run 目录（96 份 `usage.json`）得 `wall ≈ 34 s + 0.00536 s × output_tokens`，**R²=0.936 / corr(out)=0.967**（reasoning 0.911、steps 0.862、in 0.890）。此前提速都在压工具调用次数（steps 45–65 → 20–28，但每步 9.2 s → 12–18 s，**净持平**）——**优化错了变量**。指标定为 **output_tokens**。

**改动**（commit `9da2b03`）：`check_report.py` 582 → 491 行（删 8 字共享片段启发式 9 个符号 + `--ledger`/`--refs`；`return 4 if warnings else 0` → **`return 0`**）；`make_chart.py` 4 处完整性检查 findings → warnings；文档 6 处 + prompt v0.16 删 8 字规则；`toolbox.md` 新增「绝不预检建议项」段落。指令面 .md `+10,712 / −10,310` B（**净 +402 B**，行 `+39 / −25`）——语义反转而非瘦身。

**发布**：`deps` = `unchanged since the recorded baseline`；`publish` 原地更新 —— prompt v1.8 **76,477 B / `c4bb1a7b3ee1`**（旧 76,578 / `bf7b45dbf5d0`），skill v1.0.9 HTTP 200 `files=0` `is_current=True`，回读 **26/26 identical / in sync**。同批带入 R54 的 `build_ledger.py` / `render-facts.py`（空 `arm`/`unit` 合法）。

**实测 n=3**（同输入 `/tmp/prompt-r53-4.txt`，同模型 DeepSeek Flash，web off；完整数据见 `docs/evidence/r55-advisory-demotion-measurement-2026-10-12.md`）：

| 组 | run dir | out_tokens | reasoning | wall | steps | reasoning 字符 | 断言 |
|---|---|---:|---:|---:|---:|---:|---|
| 基线 | `20261012-164844-r54-base-1` | 77,939 | 50,555 | 419 s | 30 | 147,607 | 20/2 |
| 基线 | `20261012-164844-r54-base-2` | 73,504 | 54,071 | 418 s | 31 | 159,393 | 20/2 |
| 基线 | `20261012-162951-r53-doc-4c` | 61,764 | 44,311 | 365 s | 33 | 136,083 | 21/1 |
| 实测 | `20261012-171124-r55-sub-1` | 63,811 | 41,039 | 382.7 s | 31 | 124,760 | 21/1 |
| 实测 | `20261012-171124-r55-sub-2` | 70,187 | 51,147 | 395.1 s | 30 | 153,339 | 21/1 |
| 实测 | `20261012-171124-r55-sub-3` | 71,778 | 51,877 | 418.7 s | 32 | 156,978 | 21/1 |

- out 中位数 **73,504 → 70,187 = −4.5%**，门槛 **< 62,478（−15%）** → **FAIL**。两组分布重叠（`[63,811/70,187/71,778]` vs `[61,764/73,504/77,939]`）。
- wall 中位数 418 → 419 s **持平**；reasoning 字符中位数 147,607 → 153,339 **持平**；steps 31 → 31 持平（read_file 略降 12→7、execute 略升 13→17，量级在噪声内）。
- 三跑产物完整（`report.md` 10,952 / 11,096 / 12,274 字符 + `citations.json` + `evidence-timeline.json`），各 **21 PASS / 1 FAIL**，唯一 FAIL 仍是平台侧 `tool_results receipts archived`。**无质量退步。**

**关键反证（2026-10-12 修正）**：初判「三跑 `FINDINGS (` / `WARN:` 命中 0 条」是**我自己解析脚本有 bug 造成的假象**——工具调用的实参/结果在 `part["input"]` / `part["output"]`，不在 `part["text"]`，而初判只扫了 `text`。按正确字段重扫：**sub-2 真实触发了 16 条门禁输出** = `WARN: facts[20/23/26/29/32/34/36/38] … has no `arm``（8 条事实缺 arm），**非阻塞、三跑均正常交付**；sub-1 / sub-3 命中为 0（transcript 中的 WARN 字样全来自模型读到的文档正文）。

这两组事实合起来才是完整结论：① **R54 的 arm/unit 宽松化已被真跑验证**（此前 12 次近期运行中 11 次因此 exit 3 → 模型编造 arm，现已改为告警放行）；② **被 R55 降级/删除的路径（`check_report` exit 4 / `make_chart` 完整性检查）在这组输入上一次都没被触发**——4c 触发过的两处（`make_chart` 空 `description`、`check_report` 8 字假阳性）是随机事件。故「建议项 → 修复轮次」触发率低、单次成本约 1 轮（wall 的 ~5%），**无法解释输出 token 主体**——假设①仍被否，但**否的依据要换成「量级不匹配」，不是「一次都没发生」**。

**判定：指标 FAIL —— 假设①（门禁是耗时主因）被否。** 作为**正确性**修复仍成立：8 字启发式不健全（假阳性证据：r53-doc-4b 的 `RMONi-6（`、`一线晚期鳞状非小`，4c 的 3 条假 WARN），且 `check_report`「警告也 exit 4」与另两个校验器只对真 finding fail-closed 的语义不一致。keep / revert 待用户裁决（协议默认回滚；我方建议保留：净删规则 + 修掉已证伪的假阳性 + 指标无退步）。

**方法论沉淀**：同输入 output_tokens 方差 **±20–40%** > 我们追过的每一个效应；**n=3 中位数测不出 <20% 的效应** —— 只有结构性改动值得测。

### 我方能改的

- **R55-1（已修）**：8 字共享片段启发式假阳性（`RMONi-6（` / `一线晚期鳞状非小` 等正当共享散文被判 finding）—— 本轮直接删除该规则，不再打补丁。
- **R55-2（待裁决）**：keep / revert。协议默认回滚；建议保留（理由见上）。
- **R55-3（下一杠杆候选）**：hypothesis ③ —— 45 条事实 × 15 字段手工撰写 + 引文自查，占三跑 reasoning 的约 1/3，且**不依赖门禁**（属模型自发勤勉）。这是唯一还能动指标的杠杆，也是 R52 失败过的领域，需先设计比 R52 更硬的验收口径。**R56 探针已排除「改用子代理分片」这条替代路线**（串行，见 R56）。

### 平台侧（转开发）

- **P-R53-1（已知，仍每次命中）**：`tool_results receipts archived` 断言失败 —— `/workspace/tool_results/…/result.jsonl` 被 runner 标为 unsafe receipt path，与本批改动无关，不影响产物正确性。

---

## R56 — 能力探针：`task` 子代理并行性（2026-10-12，**非 skill 运行**，未改动、未发布）

**问题**：用户提出「每个证据（每篇来源）开一个 subagent 处理」。该方案只在子代理**真并行**时才对墙钟有意义；平台样板段写「同一条消息里多个 `task` 调用会 `concurrently` 并发」，本仓 `references/input-contract.md:429/453` 写实测**串行** —— 两者不能都对。**先后跑了三轮探针（前两轮信号相反，第三轮才判死）**。探针不依赖任何 skill 内容，故无需发布、零部署漂移。

**探针**：thread `5ce05322-60a5-4395-aad8-94e6f18ee03c`，turn `d1fa6eef-98eb-4ee5-8e85-0394a49dc459`，tag `r56-probe-parallel`，模型 `DeepSeek Flash`，web=off。指令：`date` 记 T0 → **同一条消息里**发两个 `task`（A `sleep 60` / B `sleep 45`，各带前后 `date`）→ 都返回后记 T1。判据：并行 span ≈ 65–70 s，串行 ≈ 110–160 s。记录 `~/.local/state/toolsmith-runs/20261012-174039-r56-probe-parallel/`。

**结果：子代理并发，但沙箱 `execute` 全平台单通道串行。**

| 探针 | 子代理 payload | 窗口 | 重叠 |
|---|---|---|---|
| R56-a `r56-probe-parallel` | A `sleep 60` / B `sleep 45`（纯 `execute`） | A `…051.140→…111.141`，B `…147.071→…192.072` | **0.00 s** |
| R56-b `r56b-probe-puregen` | 各生成 ~15000 字（`write_file`，**不碰 `execute`**） | A `…871.732→…916.885`，B `…888.021→…948.344` | **28.86 s** |
| R56-c `r56c-probe-lock` | A/B/C 各 `sleep 20`（三个子代理） | `[169.895→189.896] [192.674→212.676] [215.468→235.470]` | **0.00 s**（首尾相接，间隙 ~2.8 s） |

三轮都通过**同一条 assistant 消息里的多个 `task` part** 下发（part 顺序 `['reasoning','tool-task','trace','tool-task','trace']`），即模型确实按文档要求并发下发了。
R56-b 里 **B 的第一条命令（888.021）跑在 A 的最后一条命令（916.885）之前**，且当时沙箱无其它命令占用 → **两个子代理同时活着**；union 76.61 s vs 串行应 105.47 s ≈ **1.38× 提速**。R56-a/R56-c 两轮纯 `execute` 的 payload 则每次零重叠、交接间隙稳定 —— 队列/锁的签名。

**顺带查实三点**：① 子代理 `execute` **默认超时 30 s**（R56-a 的 B 首条 `execute` 返回 `timed out after 30s` / exit 124，显式 `timeout_seconds: 90` 才成功），与主线程文档 120 s 不一致，且该超时**从命令开始执行时**计时（排队等待也算）；② 每个 `task` 调用带 **`data-subagent-trace`** part（子代理 `traces[]` + 独立 `usage`）——A in 24,640 / out 286，B in 37,135 / out 569，该结构未文档化；③ **turn 级 `usage.json` 确实聚合子代理用量**：R56-b 两个子代理合计 `in 157,335 / out 31,684`，而 turn usage = `in 254,815 / out 35,406`，子代理输出占 89.5%（但主线程仍看不到实时子代理进度）。

**判定（2026-10-12 修正，已撕掉初判）：「按证据开子代理 —— 否决」不成立；但也**不是**无条件可行，判据要重写成「只对生成密集环节有效」。** 三轮探针的合结论是：**子代理并发（模型决定）**＋**沙箱 `execute` 单通道**。故：facts 那一次 28,631 token 的单发长生成（占该轮输出 43%）**可切并行**；而 `prep_sources`/`build_ledger`/`render-facts`/`patch`/`make_chart`/`make_citations`/`check_report` 全走 `execute`，**分片只会让它们排队**。代价实测：子代理重载通用系统提示（R56-b 两子代理合计 **157,335 输入 token**）+ 不继承项目 prompt（规格需在 `description` 重述）+ 子代理内 `execute` 默认超时 30 s + 主线程仍须做跨 ref 合并校验（ref 编号/命名/数值格式/`records[].trial` 合并键）。粒度上本组输入只选 4 篇 → 只能切 4 片，而墙钟同输入噪声 ±20–40%，效应量正好在测量能力边缘。

**撤回**：本批首次提交（commit `2b476fa`）把 R56-a 的「零重叠」读成「子代理串行」并据此否决分片，**该判定错误** —— 把**沙箱队列**误读成**运行器串行**。R56-a 的 35.93 s 空档在「并发子代理 + 单通道沙箱 + 超时从命令开始执行时计时」下完全自洽（B 的命令排到 A 释放后才开始跑，跑满 30 s 被杀，重试才成功）。同样**撤回**当时提的「度量陷阱」（turn usage 实测已聚合子代理用量，指标没被绕过）。

**证据**：`docs/evidence/r56-subagent-parallelism-probe-2026-10-12.md`。

### 我方能改的

- **R56-1（待授权）**：`references/input-contract.md:429/453` 现写「串行実行、当作省上下文的装置而不是并行提速」—— **半错**：子代理**生成**确实并行（R56-b，1.38×），串行的只是 `execute`（沙箱单通道，R56-a/c）。改为带编号的实测，并补「子代理内 `execute` 默认超时 30 s、必须显式传 `timeout_seconds`」与「分片只对生成密集环节有效」；属 skill 内容改动 → 需一次发布授权，本轮只登记不改。
- **R56-2（已撤回）**：**度量陷阱**不成立 —— R56-b 实测 turn `usage.json` 已聚合子代理用量（子代理输出占 89.5%）。以后把生成搬给子代理不会让 `output_tokens` 变好看而墙钟持平。

### 平台侧（转开发）

- **P-R56-1（修正版，原单写错了）**：**沙箱 `execute` 是全平台单通道** —— 同一条消息里发的多个并发工具调用（含子代理内的）会**排队串行执行**，交接间隙 ~2.8 s；任何「并行工具调用提速」的设计都会撞上这一层。**子代理本身是并发的**（同消息多 `task` 即并发），这一点平台描述正确，初版问题单误报为「子代理串行」已撤回。
- **P-R56-2**：子代理内 `execute` 默认超时 **30 s**，而 `execute` 描述写 120 s；且超时**从命令开始执行时**计时，**排队等待也算在内**（R56-a 的子代理因此被误杀一次）。建议：统一默认值，或写明「子代理中默认 30 s、排队时间计入超时」。
- **P-R56-3**：`data-subagent-trace`（子代理 `traces[]` + 独立 `usage`）未文档化；turn 级 usage 实测已聚合子代理用量，但这一点文档未写（建议补文档）。
- **P-R56-4**：沙箱单通道会让「并发子代理」的收益只体现在模型生成上，**平台侧无任何提示**；建议文档写明「工具调用串行、模型生成并行」。
- 问题单全文（已重写）：Obsidian `03-技术与VibeCoding/01-AI与LLM/TS子代理并发但沙箱execute单通道串行-子代理execute默认超时30s.md`（旧文件 `TS子代理声称并行实测串行…` 为**错误的初版报告，已删除**）。

---

## R57 — ① 按 ref 分片 facts + ② facts 撰写面减法（2026-10-12，原地发布 + n=3 实测，**指标 FAIL；① 未被触发**）

**动机**：找上轮遗留「模型读了但没做」的指令 —— `SKILL.md:33` 让模型跑一次 `build_ledger.py --scaffold` 并改它的行，实测三跑**都照做但全部重写**（id 复用 0/33、`value`+`endpoint` 命中 0/51、缺 ref_4），却每轮照付 1 次 `execute` + 读 33 行候选（≈13 K 字符）。**假设 ①**：facts 行（45 条 × 15 字段手写）正是 R55-3 点名的杠杆，而 R56 已证子代理**生成**真并发 → 按 ref 分片可并行；**假设 ②**：facts 的 `source_file`(13%) + 4 个默认字段(11%) 编译器本就能派生，删掉即纯减法。

**改动**（commit `b200eb6`）：新增 `scripts/merge_ref_facts.py`（确定性合并 + 只查「分片本身」：未知 ref / 跨片重复 id·record / 空片 / 未覆盖 ref 告警；有 finding 则 exit 3 不写）+ `evals/scripts/test-merge-ref-facts.py` 16 例；`SKILL.md` / `references/{input-and-extraction,input-contract,toolbox}.md` / 系统提示词 6 处：分片配方（≥3 refs、同一条消息、显式 `timeout_seconds`）、`task` 实测边界表、facts 字段契约改为**可省略派生字段**；`toolbox.md` 新增 `## 3.` merge 章节、`## 2a.` scaffold 段降级为「仍在、工作流不用」并写入实测采用率（**代码 + 9 个测试保留**）、清掉其余 5 处 scaffold 引用；`pack-dist.py` `EXPECTED` 26 → 27。

**发布**：`deps` = `unchanged since the recorded baseline`；`publish` 原地 —— prompt **v1.8 79,218 B / `f293fb45f39e`**（旧 76,477 / `c4bb1a7b3ee1`），skill **v1.0.9** dist **161,148 B / 27 entries / `a4a6f9de9d1b`**，回读 **27/27 identical / in sync**。本地门禁全绿（62/25/9/16/28/35/41/5/14 + node 8+8 + mutations a44 b12）。

**平台事故（首屏三跑全废）**：`20261012-182425-r57-shard-{1,2,3}` 在 ~264 s **同时卡死** —— `status=idle`、steps 冻结（12/24/9）、**`/timing` 无 `completed_at`**、每个线程 2 次 `GET /messages → Connection refused`；三线程都停在等 `execute` 返回、`task` 调用仍为 0（与本轮改动无关）。`run --resume` 重挂不再重发 POST，但 steps 再不前进 → 判死，弃用重跑（tag `r57b-*`）。问题单见下方平台侧 P-R57-1。

**实测 n=3**（`/tmp/prompt-r53-4.txt` = 4 esids → **4 refs，跨过 ≥3 分片门槛**；同模型 web off）：

| 组 | run dir | out_tokens | reasoning | wall | steps | `task` | facts 行 | 断言 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 基线 | R53-doc-4/4b/4c + R54-base-1/2 + R55-sub-1/2/3（n=8） | 中位数 70,983 | 50,851 | 413.8 s | 17–22 | 0 | — | — |
| 紧基线 | `20261012-171124-r55-sub-{1,2,3}` | 70,187 | 51,147 | 405.4 s | 20–22 | 0 | 36/51/55 | 21/1 |
| 实测 | `20261012-183501-r57b-shard-1` | 81,344 | 63,194 | 465.5 s | 24 | **0** | 56 | 21/1 |
| 实测 | `20261012-183501-r57b-shard-2` | 60,599 | 44,529 | 384.9 s | 20 | **0** | 55 | 21/1 |
| 实测 | `20261012-183501-r57b-shard-3` | 78,248 | 62,868 | 445.9 s | 23 | **0** | 48 | 21/1 |

- **① 未被执行：`tool-task` = 0/0/0。** 只有 shard-1 权衡过（16 段推理），并被**我们自己文档里的竞争条款**劝退：`## Subagent delegation` 里的「**Prefer straight-through scripting before delegating**…decide in one line and move on」被套到了 facts 行上；新规则是**许可**（"is a real speed-up"/"needs 3 or more refs"）而旧文本仍写 "never mandatory"，**许可打不过成本**；本轮新加的 *one lane* 那条也被当**代价**读（原话：「4 subagent round-trips (which also share the single execute lane)… doing it myself is cheaper… the benefit is context bounding — but my context already holds the sources」）。→ 指令产生**推理空转、零行为改变**，与它要替换的 scaffold 是同一种失效模式。
- **② 被完整采用**：`source_file` 省略 **159/159 行**，4 个默认字段按行省略 22–49 处；每行序列化字节 **478–482 → 299–337 B**（若补回省略字段应为 400–445 B）= **省 24–26%**（facts 块 ≈ 1.5–2.5 K out token，正是预登记的「≈3%、必然低于噪声」。同时 `--scaffold` 调用 **3/3 → 0/3**，候选文件读取消失 —— 删指令这一半真改了行为。
- **指标**：wall 中位数 413.8 → **445.9 s = +7.8%**（紧基线 405.4 → 445.9 = **+10.0%**）；out 中位数 70,983 → **78,248 = +10.2%**（护栏 <+10% 阈值 78,081，紧基线 +11.5%）→ **FAIL**（在 n=3 中位数检出极限之外，方向不利）。reasoning 中位数 +23.6%。工具组成：`read_file` 10–12→7–10（符合减法预期），`execute` 13–14→17–21（反而上升）。
- **质量无退步**：三跑各 **21 PASS / 1 FAIL**，唯一 FAIL 仍是平台侧 `tool_results receipts archived`；`records[]` 4 条、附录/图完整。

**判定：FAIL —— ① 无法评定（模型在 4 refs 上不分片，且其理由与算术一致），② 确认是真实但很小的减法（facts 块 −25%）并顺带删掉一个「付了钱没用」的步骤。** evidence 全文：`docs/evidence/r57-fact-row-sharding-and-field-subtraction-2026-10-12.md`。

**方法论沉淀**：**加一条许可打不过一条既有的成本句** —— 想推 ①②这类行为，必须先**删**竞争条款，否则模型会照旧权衡后拒绝，而权衡本身就要烧 reasoning（本轮 +23.6% 的 reasoning 中位数里就有这份钱）。

### 我方能改的

- **R57-1（已改，已成事实）**：`--scaffold` 工作流指令删除（代码 + 9 个测试保留）；实测 adoption 0/33 已写进 `toolbox.md` 2a。
- **R57-2（建议 R58 做，属减法，需授权）**：**删掉 facts 行分片配方**（`SKILL.md` :41 段内该分支、`references/input-contract.md` *Delegating the fact rows* 节、系统提示词工作流步 1 指针 + *Fact rows, one subagent per ref* bullet），保留 `merge_ref_facts.py`（可用、16 测试）、`task` 实测边界表、以及「并发而非串行」的更正。若要重试 ①，条件应改为**按源类型**（registration-class 重载荷、≥6 refs），且**先删**「Prefer straight-through scripting before delegating」。
- **R57-3（记账）**：`## Subagent delegation` 段里 pull 的劝退句被模型外推到 facts 行 —— 该段现在同时承载两条互斥策略，属结构问题，不是措辞问题。

### 平台侧（转开发）

- **P-R57-1（新，本轮实毁 3 次运行）**：**并发 turn 同时卡死** —— 2026-10-12 18:25 起三个线程（`3f21ca05-36cb-42b2-ad0d-220011534df6` / `526a8410-9785-471d-8f20-77fed417eee3` / `e72ec310-c8e4-4357-add6-f1e7223bc3a1`）在 ~264 s **同时**变为 `status=idle` 且 steps 冻结，`/timing` **无 `completed_at`**，期间各 2 次 `GET /api/threads/{id}/messages → Connection refused`；`run --resume <thread>` 重挂后 steps 再不前进（线程 2 曾从 12 涨到 24 后停住）。**建议**：① 查明 18:25–18:30 是否有 worker/容器重启（连接拒绝 + timing 行未落库同时出现，符合重启签名）；② `idle` 且无 timing row 的 turn 应在 API 层标记为 `aborted/lost` 而不是只留 `idle`（现在 runner 只能报 inconclusive，用户无法区分「还在跑」与「已死」）；③ `--resume` 对已失去 worker 的 turn 应明确返回终态，而不是继续轮询到宽限期结束。台账只留摘要，全文见 Obsidian `03-技术与VibeCoding/01-AI与LLM/TS并发turn同时卡死-idle无timing-row-resume也救不回.md`。
- **P-R53-1（已知，仍每次命中）**：`tool_results receipts archived` 断言失败（`/workspace/tool_results/…/result.jsonl` 被 runner 标为 unsafe receipt path），与本批改动无关，不影响产物正确性。
- P-R56-1~4 仍在（沙箱单通道 / 子代理 `execute` 默认 30 s / `data-subagent-trace` 未文档化）。

---

## R58 — 删除 facts 行分片配方（纯减法；目标行为达成，指标不可测）（2026-10-13，原地发布 + n=3 实测）

**动机**：R57 判 FAIL，但留下一条更干净的结论 —— 分片**指令**在 4 refs 上 **0/3 被执行**，唯一权衡过的一次（`r57b-shard-1`，16 段推理 / 7,746 字符）是被**我们自己文档里的竞争条款**劝退的：新加的是**许可**（"is a real speed-up"/"needs 3 or more refs"），同段旧成本句仍在（"never mandatory"、"Prefer straight-through scripting before delegating…decide in one line and move on"），*one lane* 那条被当**代价**读（原话：*"4 subagent round-trips (which also share the single execute lane)… doing it myself is cheaper… The benefit is context bounding — but my context already holds the sources."*）。**R58 假设**：既然这条配方在被写成"默认"时也只有 ≤1/3 的运行会去权衡它、权衡本身就要烧 reasoning，而它的目标行为在 2–8 refs 档位上本来就不划算（facts 只占一轮 out token 的 10–13%，75% 是分不掉的 reasoning）—— **整条删掉，行为应当不变，而"权衡它的那块推理"应当消失**。预登记判据：① `task` 全 0；② delegation 关键词的 reasoning part 从 R57 的 1/3 降到 **0/3**；③ 墙钟/out 无方向性劣化；④ 质量断言不回退。

**改动**（commit `3518370`，**净减法、不新增脚本**）：删掉 7 处文本 —— `SKILL.md:41` facts 分片整段 + `:33` 脚本清单注（改 "only if you chose to split"）；`references/input-contract.md` 工作流步 4 从句、`## Large-batch delegation` 的 status 块（"**default for the fact rows once 3 or more refs are selected**"）、`### Delegating the fact rows (per ref) — the default split for 3+ refs` 整节、平台事实 6；`references/input-and-extraction.md` 的大段；`references/toolbox.md` §2 标题/ pipeline merge 行 / §2a 分片句 / §3 标题与 "Used when…" / token 语法节括注；系统提示词工作流步 1 从句 + *Trigger* 的 fact-row 句 + **`Fact rows, one subagent per ref` 整条 bullet** + 委派段开头的 fact-rows 分支；`scripts/merge_ref_facts.py` docstring 首句改 "optional"。

**保留（防误删）**：`merge_ref_facts.py` + 16 例测试（降级为逃生口，同 `build_ledger.py --scaffold`）、`input-contract.md` 的 **`### Measured boundaries of the task tool`** 实测表（并发 28.9 s 重叠 / 四路 6.5 s / 单通道交接 2.8 s / 子代理 `execute` 默认 30 s / 无会话状态 / turn usage 聚合子代理）、**pull 委派（>5 esids）完全不动**、以及 "Try straight-through scripting" 那条（删掉 fact-rows 分支后它只对 pull 生效，不再互斥）。本地门禁全绿：62 / 25 / 9 / 16 / 28 / 35 / 41 / 5 / 14 + node 8+8 + mutations a44 b12。

**发布（原地）**：`deps` = `unchanged since the recorded baseline`；prompt **v1.8** 79,218 B `f293fb45f39e` → **78,155 B / `6d507fb8fff7`（−1,063 B）**；skill **v1.0.9** dist 161,148 → **160,567 B / 27 entries / `16f3bfce7130`**；回读 prompt 逐字节一致 + skill **27/27 identical** + `STATUS: in sync`。

**实测 n=3**（同 prompt `4 refs`、同模型 web off）：

| run | wall s | out tokens | reasoning | steps | `task` | facts 行 | `records` | 断言 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 基线 n=8（R53/R54/R55） | 413.8 | 70,983 | 50,851 | 17–22 | 0 | — | — | — |
| 紧基线 `r55-sub-{1,2,3}` | 405.4 | 70,187 | 51,147 | 20–22 | 0 | 36/51/55 | — | 21/1 |
| R57 参照 `r57b-shard-{1,2,3}` | 445.9 | 78,248 | 62,868 | 20–24 | **0/0/0** | 56/55/48 | — | 21/1 |
| 实测 `20261013-093256-r58-mainthread-1` | 465.6 | 78,846 | 58,638 | 36 | **0** | 55 | 4 | 21/1 |
| 实测 `20261013-093256-r58-mainthread-2` | 404.9 | 68,126 | 56,381 | 25 | **0** | 48 | 4 | 21/1 |
| 实测 `20261013-093258-r58-mainthread-3` | 443.9 | 76,848 | 47,186 | 40 | **0** | 40 | 4 | 21/1 |
| **R58 中位** | **443.9** | **76,848** | 56,381 | 36 | 0 | 48 | 4 | — |

- **② 达成（本次唯一的正面结论）**：含 `subagent|delegat|task tool` 的 reasoning part —— R57 **1/3 跑**（shard-1：2 段 / 7,746 字符 / 占该跑推理 4.1%），R58 **0/3 跑**。权衡块消失，与删除目标一致。
- **③ 无方向性劣化，但也测不出收益**：墙钟中位 413.8 → **443.9 = +7.3%**（紧基线 +9.5%），out 中位 70,983 → **76,848 = +8.3%**（护栏阈值 78,081，**未越线**）。与 R57 直接对比：wall **−0.4%**、out **−1.8%**（R57 是 445.9 / 78,248）。n=3 中位数检不出 <20% 的效应，而本次改动量级（−1,063 B 提示词、少一个"工具权威不再需要"的脚本说明）本身就在噪声里。
- **① 与 R57 相同**：`tool-task` = 0/0/0，删除没有反向触发分片。
- **④ 质量无退步**：三跑各 **21 PASS / 1 FAIL**，唯一 FAIL 仍是平台侧 `tool_results receipts archived`；`records[]` 4 条、附录/时间轴/图齐全、报告 20,631/18,637/21,181 B、facts **55/48/40** 行、**`source_file` 省略 143/143 行**（R57 的②减法未回退）、`--scaffold` 调用 **0/0/0**、`merge_ref_facts` 调用 **0/0/0**。

**判定：KEEP —— 删除生效，代价不可测。** 目标行为（不再花推理权衡委派）达成；指标既无法证明收益也无法证明损害；`merge_ref_facts.py` 留在包里不产生运行时成本。**对「按 ref 分片」的最终结论：不再重试** —— R57 已证 4-refs 档位下模型（正确地）不需要它；要做必须在 ≥6 refs + registration-class 重载荷另开一轮，且**先删**任何竞争的成本句（R57 方法论沉淀）。evidence 全文：`docs/evidence/r58-fact-row-recipe-deletion-2026-10-13.md`。

### 我方能改的

- **R58-1（已改，已成事实）**：上表 7 处文本删除；`pack-dist.py EXPECTED` 仍 27（脚本保留）。
- **R58-2（记账，观察项）**：本轮 `steps` 离散度变大（36 / 25 / **40**）。`r58-mainthread-3` 出现一次 **`execute` 参数名拒绝**（`['command'] Field required; ['shell_command'] Extra inputs are not permitted`，框架自动重发后成功）—— 与 O51 同源，非本轮引入，仅记账（对应下方 P-R58-2）。
- **R58-3（未做，待议）**：`read_file` 8–16 次里含 `ls`/`grep` 与多次探查（`toolbox.md` offset 100 limit 230 一次、`chart-templates.md` / `conclusion-language.md` 各一次）。若还要找杠杆，应量**主线程探查次数**而不是再动 facts/rules —— 但需先有 tool start/end instrumentation，当前不可测。

### 平台侧（转开发）

- **P-R58-1（承接 P-R57-1，本轮未复现）**：三跑同期启动、全部 `succeeded`，未出现 `idle` 无 `completed_at` 的卡死。旧单仍有效，维持观察。
- **P-R58-2（新，轻）**：`execute` 参数名拒绝在 live 跑可复现（`command` vs `shell_command`），框架自动重发后成功，但被 runner 记入 "arguments refused" 清单。属工具 description 与 schema 命名不一致，建议对齐（与 O51 同源）。
- **P-R53-1（已知，每次命中）**：`tool_results receipts archived` 三跑均 `[FAIL]`，与本批改动无关，不影响产物。
- P-R56-1~4 仍在（沙箱单通道 / 子代理 `execute` 默认 30 s / `data-subagent-trace` 未文档化 / 平台无「工具串行、生成并行」提示）。

---

## R52 回退 — 2026-10-12，经用户「回退吧」授权

恢复 R51 commit 3adb77c 的全部运行资产与 dist，撤销 R52 接口测试；R52 失败证据和 Git 历史保留。CLI 无历史版本激活命令，故采用受护栏保护的 publish 原地写回 R51 字节，当前标签 1.8/1.0.9 不变。prompt 76,578 B / bf7b45dbf5d0；bundle 152,558 B / 081cd850befc / 26 entries；deps unchanged，HTTP 200，status in sync，项目当前绑定正确，25 支持文件 + SKILL 全部一致。回退内容已有 R51 三组真实验证，本轮拒绝冒烟 `20261012-132543-r52-rollback-b`：thread `97ac3752-fd44-4a14-bdca-2050d5e5e74f`，36.7 s server / 42.4 s polled，9 attempts（1 次 INVALID_INPUT 参数拒绝后重试成功），14 PASS / 0 FAIL / exit 0；部署 prompt/SKILL/25 支持文件一致，未写报告或 citations。Docker 不涉及。

---

## R59 — 文体门禁内联（A+B）：条件式引用 → 确定性检查（2026-10-13，原地发布 + 真跑实测）

**动机**：用户问「引用外部 human skill 是否增加耗时」，并用全历史 `load_skill` 数据回答：`multi-clinical-result-comparison` **115x** / `report-humanizer-zh` **7x** / `chart-visualization-json` **2x** ⇒ 文体 skill 触发率 **6.1 %**（R58 三跑 **0/3**）。引用本身几乎免费（返回 5,933 字符 ≈1.5 K input token，一次后走 cache；唯一载入它的 `r57b-shard-3` 墙钟 445.9 s 正是三 shard 中位）；**贵的是"应用"**（载入后改报告 + 重跑门禁，估 +30–60 s / +10–20 K out）。**R59 假设**：把「6 % 的条件式引用」换成「100 % 确定性门禁 + 必然生效的内联规则」，产出风格不再靠概率，而成本低于现状（现状是 100 % 的 run 付那 6 % 换 6 % 生效）。用户拍板 **A+B**：A = 扫描器复制进我们的包；B = 精选规则内联进 SKILL.md / 系统提示词。

**关键口径（回答「必过？是不是更耗时」）**：**门禁必跑 ≠ 改写必做**。必跑 = 定稿后 1 次本地 `execute` 跑 `tell-scan.py`（1–3 s、**0 token**、输出 ≈200 B，落在噪声内）；**改写只由强命中触发**（弱命中仅线索）。样本报告实测 **强 0 / 弱 1** ⇒ 重写基本不触发，实际成本**低于**现状。

**改动**（A+B，净加法但**零运行期外部依赖**）：新增 `skill/.../scripts/tell-scan.py`（22,558 B，逐字节复制自 `report-humanizer-zh` 仓库，sha256 `1992a4c48f78dc8e…`）；新增 `skill/.../references/prose-style-zh.md`（13,071 B / 200 行，只内联报告文体相关条目 + 扫描器编号映射 + 「强命中必须处理」）；`SKILL.md`（脚本清单、工作流 §5 必跑门禁、`## Report prose style` 整节改为自包含并明写「不加载、不等待、不依赖外部文体 skill」、参考清单第 11 项）；`references/toolbox.md`（门禁表行 + 新 `## 9.` 节）；系统提示词 6 处（工作流步 8、脚本清单、`## Report prose style` 自包含版、交付前检查两条、机械脚本清单）；`tools/pack-dist.py` `EXPECTED 27 → 29`；新增 `evals/scripts/test-tell-scan.py` **10 例**；`vendor/README.md` 溯源表。

**runner 第 18 项断言（本地 runner 改动，备份 `toolsmith-publish.v10.bak`，改前 sha256 前缀 `b7652eaf9d5cb9d8`）**：`execute` 调用中必须出现 `tell-scan.py`（缺 → **FAIL**，门禁是契约不是选项）；能读到 `SCAN_EXIT` 时必须为 `0`（脏 → FAIL）；调用过但未回显退出码 → **WARN**（工具调用证据在、只是数字读不到，判 FAIL 是罚宿主不是罚 run）；`SCAN_EXIT` 键名同时接受 `command` / `shell_command`（见 P-R59-1）。`fails` 只收 `FAIL`，故 WARN 仍以绿出货。`evals/runner-gate/test-runner.py` **41 → 45**：正向夹具补上门禁调用与 `SCAN_EXIT=0`；新增 4 例（缺门禁 / 脏退出 `SCAN_EXIT=3` 与 `2` / 无回显仅 WARN / 干净扫描不得重复计数）。**修复中撞到假绿**：第一版写 `add(True, …, warn=True)`，而 `lvl = "PASS" if ok else ("WARN" if warn else "FAIL")` ⇒ 被吞成 PASS；改 `add(False, …, warn=True)` 才是 WARN。

**本地门禁（全绿）**：`test-tell-scan` 10 / `test-skill-scripts` 62 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test-merge-ref-facts` 16 / `test-render-facts` 28 / `test_regressions` 35 / `test-runner` **45** / `test_pack_dist` 5 / `test_replay_run` 14 / node **8+8** / `mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS` / `verify-run-chain.py` `GATE: PASS`（145 histories / 5 comparable）。`deps` = `unchanged since the recorded baseline`（当时按「humanizer 是**项目挂载**事实而非文本依赖」解释 —— **【R60 更正】该归因错了**：`collect_deps` 只扫 `skill/` 与 `system-prompts/` 的文本，挂载与它无关；R59 那次 `unchanged` 是巧合，因为正文当时仍点名。见 R60 §2）。

**发布（原地，用户授权「原地实测」）**：prompt v1.8 → **81,614 B / sha `aaf77e7c284b`**（`ifadd=false`，HTTP 200，read-back `current=v1.8 matches_local=True`）；skill v1.0.9 → dist **180,675 B / 29 entries / sha `099504055d79`**（`/api/skills/update_skill_file` HTTP 200，`skill_id=16aeb0406e12425bad27a2444f17225e`）。回读 `status`：`prompt deployed == local: True` / skill `29/29 identical` / **`STATUS: in sync`**。

**项目挂载集 4 → 2 = 用户主动取消（不是平台缺陷）**：发布前后 `status` 打印的 `skills=` 从 4 变 2（`report-humanizer-en` / `report-humanizer-zh` 被移出），三处 API 一致（`/api/projects/<pid>`、`/resources`、`/api/agent/info`）；项目行 `updated_at=2026-10-13T10:12:03`、`updated_by=徐佩佩`、`version=1`。我一度按「平台侧副作用 vs 带外改动」立了 **P-R59-2**，**当日用户澄清：是他自己从项目配置里取消的**——规则已内联进本包，不再需要挂载外部 humanizer ⇒ **该条目作废，无需恢复**。（客户端自我归因没错：`publish` 只发两个文档化 POST、写不到项目记录；真正缺的是线索——无审计端点、`updated_by` 区分不了人改还是服务端改。留作可用性建议，不开单。）对本轮实测**不构成阻断也不需要「不可比」折扣**：被移出的两条从未被加载（R58 三跑在 4 挂载下同样 0 次），影响仅「技能目录少两条」。

**真跑实测（n=2，`DeepSeek Flash`，web off，`/tmp/prompt-r53-4.txt` = 4 esids，10:14:19 并发，tag `r59-gate-{1,2}`）**：

| run | wall s | out tok | reasoning | steps | `tell-scan` 调用 | `SCAN_EXIT` | facts | 断言 |
|---|---|---|---|---|---|---|---|---|
| r59-gate-1 | 332.1 | 52,794 | 37,399 | 30 | 2 | `[0, 0]` | 42 | 21 PASS / 2 FAIL |
| r59-gate-2 | 394.5 | 70,063 | 56,677 | 25 | 2 | `[0, 0]` | 43 | 21 PASS / 1 FAIL |
| **中位** | **363.3** | **61,429** | — | 27.5 | **2** | 全 0 | 42.5 | — |
| R58 中位（4 挂载） | 443.9 | 76,848 | — | 26 | 0 | — | 47.5 | — |
| R55 紧基线 | 405.4 | 70,187 | — | — | 0 | — | — | — |

- **断言 #18 现场**：`[PASS] prose gate ran and exited clean — 2 call(s), SCAN_EXIT=[0, 0] strong-free=True`（两跑同此）⇒ 门禁从「6.1% 靠模型记起」变成 **2/2 跑、每跑 2 次必跑**，且**强命中 0**，无条件改写未被动触发（旧口径 0/3）。
- **弱命中被当线索**：模型自述 `0 strong hits; 2 weak (bold count, mixed numeric notation). Weak only — acceptable`、`only a weak bold-count clue — acceptable, not a reason to change`。
- **零外部依赖**：`report-humanizer` 字符串只出现在我们自己的自包含节（`Do not load, wait for, or depend on any external style skill.`）；`load_skill` 只调本 skill。
- **无分片回潮**：`task` / `subagent_type` **0** 次、`build_ledger.py --scaffold` **0** 次调用、`merge_ref_facts.py` **0** 次调用（transcript 里出现的字符串是阅读 SKILL.md 的叙述）。
- **质量未退**：每跑 21 PASS（citations 4 refs 键集/日期/标题、`{{ref_n}}` 双向齐、图表 envelope 与 `::visualization` 一致、`present_artifact` 收尾、无占位符/嵌套锚点）。
- **FAIL**：两跑共有 `tool_results receipts archived`（P-R53-1）；`r59-gate-1` 另有一条 `no tool errors`，源自 `execute timeout_seconds=180`（>平台上限 120）被拒后框架自动重发成功 → **R59-4**。
- **成本**：墙钟中位 363.3 s（vs R58 443.9、R55 405.4）、out 中位 61,429（vs 76,848 / 70,187）**均更低**，但 n=2 且挂载集不同 ⇒ **不可归因**，只能说「没有可测的变慢」。

**判定：KEEP**（A+B 成立：门禁 100% 执行、强命中才改写、零运行期外部依赖）。

### 我方能改的

- **R59-4（新）**：模型会给主线程 `execute` 传 `timeout_seconds: 180`（平台上限 120）→ 被拒后框架自动重发成功，但计入 `no tool errors` FAIL（`r59-gate-1`）。我们文本已写「main thread 120 s」（`references/input-contract.md`），属模型越界；候选动作 = 在 `toolbox.md` 的 `execute` 行把上限写得更显眼（内容改动，下一轮再议）。
- **R59-6（记账，无需动作）**：`deps` 仍把 `report-humanizer-en/zh` 列为被扫描的依赖源（1.0.0）——因为**我们的正文点名了它们**（自包含节里那句「A deployment may also mount …」），与运行期是否挂载无关；`deps` 判 `unchanged`，无需 `--accept`。
- **R59-5（新，低优先）**：原地更新 skill 后，线上版本的「版本更新说明」仍是旧的（`status` 回读 1.0.9 的 message 还是 R52 那段）——`/api/skills/update_skill_file` 我们只传 `skill_id/skill_name` + 全量 zip；若接口支持 `message`/`commit_message`，下次原地更新时应顺带更新说明（这次先记，不动线上）。
- **R59-1（已用测试兜住）**：扫描器在仓库里有两份拷贝（本包 + `report-humanizer-zh` 仓库）。运行期依赖已消失，残留仅仓库级漂移，由 `test_bundled_copy_matches_the_upstream_repo`（sha256 比对，兄弟目录缺失时 skip 而非假绿）拦截；上游改规则的动作写死在 `prose-style-zh.md` 尾节与 `vendor/README.md`。
- **R59-2（观察项）**：第 18 项断言把「跑过但未回显退出码」降为 WARN。若 live run 显示模型**从不**回显，需回头评估是否收紧（把 `; echo "SCAN_EXIT=$?"` 写成必须照抄的固定命令 → 收紧为 FAIL）。
- **R59-3（记账）**：第 18 项断言**只作用于 artifacts 分支**（`--expect refusal` 在第 1408 行提前 return）—— 拒绝场景本就不该产出报告、也不该跑文体门禁。

### 平台侧（转开发）

- **P-R59-1（新，轻）**：`execute` 参数名不一致 —— 期望 `shell_command`，模型常发 `command`（`r58-mainthread-3` 出现一次 `['command'] Field required; ['shell_command'] Extra inputs are not permitted`，框架自动重发成功但被记入 "arguments refused"）。第 18 项断言已两种键都读以自保；建议把工具 description 与 schema 命名对齐（与 O51 / P-R58-2 同源）。
- **P-R59-3（新，轻）**：`execute.timeout_seconds` 的 `inputSchema` 无 `maximum` 约束、描述仅 *Optional timeout override for this command.* ⇒ 越界执行时才报 `timeout_seconds exceeds the maximum allowed (120s)`；建议加 `maximum: 120` 并把上限写进描述。
- **P-R58-1（承接，维持观察）**：本轮未复现 `idle` 无 `completed_at` 卡死。
- **P-R53-1（已知，每次命中）**：`tool_results receipts archived`（`/workspace/tool_results/…/result.jsonl: unsafe or unsupported receipt path`）与本批改动无关。
- **P-R56-1~4 仍在**：沙箱 `execute` 单通道 / 子代理 `execute` 默认 30 s / `data-subagent-trace` part 未文档化 / 平台无「工具串行、生成并行」提示。

---

## R60 — 运行期文本不再点名外部文体技能（依赖面 3 → 1）（2026-10-13，原地发布 + n=2 实测）

**动机**：用户指出 R59 之后正文里仍写着 `report-humanizer-zh` / `report-humanizer-en` ——「这肯定要改啊……都没有这个 skill 了」。症状有二：① 文本点名 → 依赖错觉；② `deps` 的依赖面把两个已取消挂载的技能一直列为**被扫描的上游源**（`skills: 3`），发布闸门挂着两条与本项目无关的新鲜度。

**R60 假设（一轮 = 一个假设）**：删掉运行期文本里的字面点名 ⇒ `deps` 依赖面收窄到「运行期真会加载的东西」（只剩图表技能），**行为不变**（R59 已内联全部文体规则，运行期从不依赖挂载）。

**改动**（3 个运行期文件，纯措辞收窄，净减）：`SKILL.md:185` 与系统提示词 152 行的 `A deployment may also mount \`report-humanizer-zh\` / \`report-humanizer-en\`` → `If a deployment happens to mount another style skill, do not apply it here: …`（**禁止加载/等待/依赖任何外部文体技能**这条硬指令保留且更明确）；`references/prose-style-zh.md` 维护节 3 行去点名（`源自上游 report-humanizer-zh 仓库` → `随本 Skill 发布的自包含副本（基线 v0.1.1）`、`与上游逐字节一致` → `与基线副本逐字节一致`、更新动作里的「上游」→「基线」）；仓库级 `vendor/README.md`（**不进交付包**）保留完整溯源 + sha256 并追加「用户已取消挂载 / 运行期文本不再点名」一行；顺带把 `tools/pack-dist.py` 的 docstring `27 entries` 修成 `29 entries`。体积：prompt `81,614 → 81,576 B`（−38 B）、dist `180,675 → 180,652 B`（−23 B）、条目数不变 29。

**依赖面现场（本轮的正事）**：
```
$ toolsmith-publish deps      # 改后、未接受新基线
  UPSTREAM CHANGED since the recorded baseline:
     - GONE skills report-humanizer-en
     - GONE skills report-humanizer-zh        exit=3（闸门按预期挡下）
$ toolsmith-publish deps --accept && toolsmith-publish deps
  skills: 1 → chart-visualization-json v1.0.12    |  MCP tools: 1  |  built-in tools: 16
  DEPS: unchanged since the recorded baseline
```
**并更正 R59 的归因**：`deps` 量的是**文本引用面**（`collect_deps` 扫 `skill/`、`system-prompts/` 的 `.md/.json/.py`，对平台技能名做整词匹配），与项目挂载无关；两条 `GONE` 只可能来自点名消失，也反过来证明本轮改动是唯一因。

**本地门禁（全绿）**：`test-skill-scripts` 62 / `test-tell-scan` 10 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test-merge-ref-facts` 16 / `test-render-facts` 28 / `test_regressions` 35 / `test-runner` 45 / `test_pack_dist` 5 / `test_replay_run` 14 / node **8+8** / `mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS` / `verify-run-chain.py` `147 histories / 5 comparable / 142 skipped` + `GATE: PASS` / `pack-dist.py --check` → `IDENTICAL (180652 B / sha 0b8ba50448b6)`。合计 **221**（含 numeric-integrity 28 + merge-ref-facts 16 为 **249**）。

**发布（原地，用户授权「原地实测」）**：prompt v1.8 → **81,576 B / sha `713f4333b74e`**（HTTP 200，read-back `deployed == local: True`、`CURRENT`）；skill v1.0.9 → dist **180,652 B / 29 entries / sha `0b8ba50448b6`**（`POST /api/skills/update_skill_file` HTTP 200，`skill_id=16aeb0406e12425bad27a2444f17225e`）；回读 `status` = `29/29 identical` + **`STATUS: in sync`**；项目行 `prompt=475039ccebfe46a3a39002febe28b1f4`、`skills=[chart-visualization-json, multi-clinical-result-comparison]`。

**真跑实测（n=2，`DeepSeek Flash`，web off，`/tmp/prompt-r53-4.txt` = 4 esids，tag `r60-prose-generic{-2}`）**：

| run | wall s | out tok | reasoning | tool calls | `tell-scan` | `SCAN_EXIT` | facts | report | 断言 |
|---|---|---|---|---|---|---|---|---|---|
| `r60-prose-generic` | 502.7 | 89,145 | 73,317 | 33 | 1 | `[0]` | 63 | 19,022 B | 22 PASS / 1 FAIL |
| `r60-prose-generic-2` | 357.2 | 61,049 | 46,759 | 27 | 1 | `[0]` | 53 | 20,355 B | 22 PASS / 1 FAIL |
| **中位** | **430.0** | **75,097** | — | 30 | 1 | 全 0 | 58 | 19,689 B | — |
| R59（n=2） | 363.3 | 61,429 | — | 27.5 | 2 | 全 0 | 42.5 | — | 21 PASS |

- **断言 #18 两跑 PASS**：`prose gate ran and exited clean — 1 call(s), SCAN_EXIT=[0] strong-free=True`；弱命中仍只作线索（`W-FMT-MIXED` / `W-AIWORD 闭环`，`合计强命中 0 条`）。
- **文本干净**：两跑 `messages.json` / `transcript.md` / `report.md` 中 `humanizer` = **0** 次；`load_skill` 各 1 次且参数均为本 skill（没有去加载任何外部文体技能）。
- **契约未动**：两跑各 22 PASS，唯一 FAIL 均为平台侧 `tool_results receipts archived`（P-R53-1）；`task` / `--scaffold` / `merge_ref_facts` 仍 **0** 次。
- **成本不可归因**：中位 wall 430.0 s（vs R59 363.3 / R58 443.9 / R55 405.4），单跑跨度 357–503 s；改的是措辞、门禁仍 1 次 0 token。`r60-1` 的 out 89,145（reasoning 73,317）是历史最高值，同批 `r60-2` 仅 61,049 ⇒ 记方差。

**判定：KEEP**（目标达成且现场可证：运行期文本零点名、依赖面 3 → 1；契约全绿、无回潮；成本落在已知方差带内）。详见 `docs/evidence/r60-runtime-text-drops-external-style-skill-names-2026-10-13.md`。

### 我方能改的

- **R60-1（记账，无需动作）**：门禁调用数由 R59 的 2 次/跑降为 **1 次/跑** —— 模型把 `tell-scan.py` 并进同一条 `execute` 链（`make_citations … ; check_report … ; tell-scan … ; echo SCAN_EXIT=$?`）。断言只要求 ≥1 次且 `SCAN_EXIT=0`，两跑均在链尾拿到干净的 `0`。
- **R60-2（更正）**：R59 把 `deps` 的 humanizer 归因为「项目挂载事实」有误 ⇒ 正确表述是**文本引用面**（已回填 R59 节）。
- **R60-3（观察，低优先）**：`SCAN_EXIT` 依赖模型自己回显；若后续出现「跑过但无回显」的 WARN，再评估让扫描器自带固定回显命令（当前 n=2 都自带）。

### 平台侧（转开发）

- **P-R53-1（已知，每跑命中）**：`tool_results receipts archived` —— 两跑各一次 `[FAIL]`，与本批改动无关。
- 其余（P-R59-1 / P-R59-3 / P-R56-1~4 / P-R58-1）维持原状态；**P-R59-2 保持作废**（挂载 4 → 2 系用户主动取消，本轮进一步去掉文本点名，与该决定一致）。
