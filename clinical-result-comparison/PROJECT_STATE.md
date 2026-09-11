# Project State

## Repository

- Git repository: `git@github.com:sdsliang/skill.git`
- Project subdirectory: `clinical-result-comparison/`
- Branch: `main`
- Migrated from `/home/xupeipeioo1/apps/clinical-result-comparison` and pushed as root commit `08440ad`.


Build the first Tool Smith Agent for reconstructing complete trial interpretations from multiple user-selected clinical result records, using only their original `source_full_text` and preserving source-level linked citation traceability.

## Housekeeping conventions

- 从 NP Clinical 拉取的示例数据（`evals/**/np-clinical-*/`）不入库：`.gitignore` 已忽略，`fetch-np-clinical-attachments.mjs` 可随时重拉。已提交的历史版本也已从跟踪移除（commit 63c031c）。

## 📌 待办: 报告表格整表复制 / 整表下载 CSV-Excel（2026-09-01，已交产品验证，不改文件）

- **背景**：对比结果 skill 报告（`present_artifact` 交付的 .md）含多张 Markdown 表格（timeline 表、endpoint 表、cross-trial 对比表）。问 ToolSmith 能否支持「表格整表复制」+「整表下载为 CSV/Excel」。
- **结论（只读分析，未改 skill 文件）**：
  - 整表复制：**无按钮级能力**。浏览器原生「选中整表→复制」可用（HTML 表格复制为制表符分隔，贴 Excel 保留列）；要一键按钮 = ToolSmith 前端给 markdown 表格加 action。Skill 侧替代（widget 内 `navigator.clipboard`/`<a download>`）受 `sandbox="allow-scripts"` opaque origin 限制（无 allow-downloads / 无 clipboard-write 权限策略 / 消息桥无 copy 事件），不可靠。
  - 整表下载 CSV/Excel：**Skill 侧现在就能做**——每张关键表同步产一份 `.csv`/`.tsv`（`::visualization` 引用 → 前端通用文本预览 + 下载按钮）或 `.xlsx`（沙箱 openpyxl 生成 → `present_artifact`/ArtifactPanel 下载）。注意 CSV/TSV 预览是纯文本不渲染成表格。
  - 产品级「表格卡片自带复制/下载按钮」属 ToolSmith 平台功能，需前端新增 action（类比：下钻 navigate 事件也是待确认项）。
- **决定**：先不改 skill 文件；已交产品（何林杰）先尝试验证平台能力，等其结论后再决定是否给 skill 交付契约加「每表同步产 CSV/TSV/XLSX 数据文件」规则。
- **飞书任务**：待建 task，负责人=何林杰（open_id `ou_543a818d8dcd7a4ce52a9349b1a000ac` 本地聊天记录已取，无需 contact 搜索权限）。**卡点（2026-09-01）**：应用 `cli_aae61ba424389d06` 已启用 28 个 scope（含全部 task），但用户侧 token 未授予 `task:task:write`；bot 身份也未申请该 scope。→ **精简申请链接（仅 task+日历 17 个 scope，一轮审批）**：https://open.feishu.cn/page/scope-apply?clientID=cli_aae61ba424389d06&scopes=task%3Acomment%3Awrite%2Ctask%3Acustom_field%3Awrite%2Ctask%3Atasklist%3Awrite%2Ctask%3Acustom_field%3Aread%2Ctask%3Asection%3Awrite%2Ctask%3Atask%3Aread%2Ctask%3Atasklist%3Aread%2Ctask%3Aattachment%3Awrite%2Ctask%3Asection%3Aread%2Ctask%3Atask%3Awrite%2Ccalendar%3Acalendar%3Areadonly%2Ccalendar%3Acalendar%3Awrite%2Ccalendar%3Acalendar.event%3Aread%2Ccalendar%3Acalendar.event%3Awrite%2Ccalendar%3Acalendar.acl%3Aread%2Ccalendar%3Acalendar.acl%3Acreate%2Ccalendar%3Acalendar.acl%3Adelete 。审批通过后用户再做一次 `--domain task,calendar` 授权即可建任务。

## ⏸️ Parked: bar 柱下钻（v0.9-test，已由用户验证可行，暂不开发）

- 全部改动（未提交）已 stash：`git stash list` → `stash@{0}: On chart-drilldown-nct: wip: bar drill-down (v0.9-test) + 1L ORR test datasets — verified by user, park for later`。分支 `feat/chart-drilldown-nct` 与 main 同提交 `349eabc`（无独立 commit），后续要继续可直接 `git checkout feat/chart-drilldown-nct && git stash pop`。
- 内容：`endpoint-bar.html` 支持 `bars[].url` → `window.__toolsmithNavigate(url)`（登记号详情页 `https://ct.pharmcube.com/trial/{nct_id}`）；`SKILL.md`/`chart-templates.md` 下钻契约；v0.9-test 系统提示词（优先读 md 元数据 `source_nct_id` 拼 url）；`test/drilldown-bar-sample.html`；两套测试数据集 `test/drilldown-sources/`（仅保证登记号）与 `test/drilldown-sources-1l-orr/`（一线+ORR，必出柱状图，均带 `source_nct_id`）；`dist/multi-clinical-result-comparison-v0.9-test.zip`。
- 验证结论：部署端 `__toolsmithNavigate` 桥 + 宿主 `window.open` 均已就位；不画图的根因是数据异构（跨线/跨终点）触发契约不绘图，`1l-orr` 数据集（indication 135 + III期 + ORR 端点 `4a8abd33ec374a46b758926758ed410a` + `therapy_labels.meta.text∈{一线治疗,一线}`）可稳定出柱状图。恢复时无需动 tool-smith 端。

## ⏸️ Parked: 通用下钻契约（drillDownValue，等前端 MCP+skill 落地后再对照）

- 背景（2026-08-28，前端告知）：前端侧通用 `/chart-visualization` skill 的图表格式里，每个数据点带 `drillDownValue`（**一个 id**，如 `"2024-01_销售额"`）；前端拿到该 id 后调接口取 workspace 里脚本生成的 detail json 渲染，**被取的 json schema 可自定义**（"支持数据格式多样"）。链路：`点.drillDownValue(单 id) → 前端调接口 → workspace detail json → 渲染`。
- 与对比结果 skill 的关系：聚合点（如「II期积极结果 = 5 条」）→ **`drillDownValue` 保持单 id，多条记录放进该 id 对应的 detail json**（数组/多值不进 drillDownValue 字段）。可替代/升级现有 parked 的 `bars[].url` → `__toolsmithNavigate(url)` 方案。
- **✅ 已确认设计（2026-08-28 与段帅帅/何林杰对齐）**：
  - `drillDownValue` = **detail json 的文件名**（id↔文件名一一对应，一 id 一 json）。
  - **命名约束**：id/文件名只用安全字符（字母数字+下划线，不含 `/`、空格、`..` 等）——何林杰示例 `赛道_PD1/VEGF 双特异性抗体_结果id` 含 `/`+空格不安全，需用如 `track_pd1vegf_bispecific` 这类 slug。
  - detail json 内容 = **esid 数组**（`clinical_trial_result_structured._id` = ES 的 `_id`，B7 已确认）；前端拿这批 esid 去「临床结果列表页做检索」。极简 schema：`{"ids": [esid1, esid2, …]}`。
  - 会议解读（WCLC 按赛道统计，如 PD1/VEGF 双特异性抗体=10 个结果）是下钻落地场景；下钻逻辑与可视化逻辑分离，仅用 `drillDownValue` 关联。
- **2026-08-28 决定：本条目交接/挂起，等何林杰结果再动。** 何林杰已主动承诺「下周拿具体案例跟帅帅测试验证对接细节和标准规范，把路径跑通、范式具象化并描述记录下来」，届时我方再照着写 skill（若需）。
  - **本周我方 skill 零待办**：下午 2 点会「一句话确认（detail json 放 /workspace/output/、文件名=drillDownValue、安全字符）」改为可选——该问题下周案例测试自然会暴露并顺带记录，不硬推。
  - **下周待办**：等何林杰的测试结果 + 具象化范式；到时评估对比结果 skill 是否也输出 drillDownValue + detail json（照其记录规范执行，属半小时照抄级小活）。
  - 对比结果 skill 继续 parked；当前不做任何代码改动。

## Current version

- System prompt: `v0.15`
- Skill: `multi-clinical-result-comparison` trial-level synthesis `v0.15` (esid + `pharmcube-query-clinical-result-with-params` input, chart products as pure JSON **produced by reusing the upstream `chart-visualization-json` skill** and validated by that skill's CLI, file-based report delivery via `present_artifact`, entity inline references with trial short-name display, **no HTML chart asset anywhere in the repo**) 
- 仓库内 HTML 资产：**v0.15 已全部移除**（`docs/legacy-html-charts/` 整目录删除：3 个 HTML 模板 + `chart-tokens.css` + `validate-chart.py` + `render-preview.py`，见 git `e4f3bb7`）；保留的只是「禁止再产出 HTML/Mermaid、禁止混入 CSS/HTML token」类**防回退护栏**。
- Chart validation entry: `node /workspace/skills/chart-visualization-json/scripts/validate-cli.js <product.json>`（前端仓库别名 `pnpm validate:chart -- <path>`）；自研 `validate-chart.py` 已退役。
- **`dist/multi-clinical-result-comparison-v0.12-temp-preview.zip` 已删除（v0.15，用户要求）**：v0.12 调试期双写包（含 `render-preview.py`，写 `.preview.html` 孪生页）；双写已在 v0.14 撤销、HTML 已在 v0.15 全销，该包随之下线。它从未入库，删除后不可恢复。
- v0.13 轻量版：**弃用但未删除**（源码 `docs/legacy-v0.13/`，归档 `dist/multi-clinical-result-comparison-v0.13.zip`）。
- 当前 dist：`dist/multi-clinical-result-comparison-v0.15.zip`（19 文件，系统提示词不入包），SHA-256 `0deda5d3b6fa94a279ed62b89e5b107c01bf84516054d852f25a2a71cfe91408`（HTML 清理版 + 子代理委派规则（触发 >5 / 每块 ≤5）+ 图表 envelope 契约 + 空目录兜底 + 上游 v1.0.9 对齐 / 渲染配置归图表 skill + `::visualization` 标签不进实体锚点覆盖；67897 B）。**2026-09-11 复盘上游 chart skill v1.0.10 后再跑 `/tmp/pack15b.py`：SHA 不变**（dist 只装运行文件，本轮未改任何运行文件）。`dist/…-v0.14.zip`（`c0a7d4c0…`，含「输出文件固定命名」契约）及更早自动降为历史归档。
- Git：分支 `v0.15-remove-html`（从 `main` 的 `16cbb96` 切出）；`main` 已含 v0.14 提交 `e4f3bb7` 与记账提交 `16cbb96`，且已 push（`origin/main` = `16cbb96`）。v0.15 提交链 **`da5b157`（HTML 全销）→ `aa05104`（子代理委派边界，含阈值二次校准）→ `d65abdf`（记账）→ `4040ff3`（上游 v1.0.9 对齐 + 渲染配置归 Skill + 重打 dist）→ `87a2afb`（记账）→ **`49f00d9`（`::visualization` 标签不进实体锚点覆盖 + 重打 dist）→ 本轮 v1.0.10 记账提交**）** 全部按用户授权 push 到 `origin/v0.15-remove-html`；**按要求不合回 `main`、不开 PR**（不合并分支）。
- 未提交：无 tracked 改动（`49f00d9` 与本轮 v1.0.10 记账提交均已 push）。未跟踪保留 `vendor/`（上游 chart skill **v1.0.9 + v1.0.10** 两份源码副本 + `vendor/README.md`）；`.gitignore` 已忽略 `vendor/**/node_modules/` 与 `vendor/chart-visualization-json/*/`，而 `vendor/README.md` **尚未被忽略**——要不要入库待用户拍板（内含上游内部 CDN 地址与源包 SHA）。无 `Dockerfile`/compose，不涉及镜像。

## v0.15 change: 仓库内 HTML 资产彻底移除（2026-09-10）

- **触发**：用户拍板「新建一个分支，把 html 完全移除，搞一个 v0.15」。承接上下文：`docs/legacy-html-charts/` 里的 6 个 v0.8–v0.12 遗留 HTML/CSS/py 资产已无运行时用途（v0.14 起图表走纯 JSON + 上游 `chart-visualization-json` skill）。
- **分支**：`v0.15-remove-html`（不直接在 `main` 上改）。
- **删除**：`git rm -r docs/legacy-html-charts` —— `endpoint-bar.html` / `endpoint-line.html` / `evidence-timeline.html` / `chart-tokens.css` / `validate-chart.py` / `render-preview.py` 全销。仓库现在没有任何 `.html` / `.css` / 图表相关 `.py`；回溯看 git `e4f3bb7`。
- **运行时不变量**：这 6 个文件**从未进过发布包**（v0.14 dist 不含 HTML/CSS/py，已有打包断言护栏），所以对 Tool Smith 的运行时契约零影响——本次只是仓库卫生。
- **保留（故意，防回退护栏）**：`references/chart-templates.md` 仍写明「不写 Mermaid、不产出 `.html`、不混入自定义色板/CSS/HTML token」；sys 仍禁止 HTML/SVG fragment 与非 `.json` 图表文件；Final verification 仍断言 `::visualization` 目标是 `/workspace/visualizations/*.json`。只把两处 **v0.12 调试期遗留** 的 `.preview.html` 提法泛化为「非 `.json` 图表文件」。
- **eval 目录一并清空 HTML**：`evals/iteration-16/chart-examples/*.html` 7 个已跟踪文件 `git rm`；`evals/iteration-16/np-clinical-*/`（gitignore 内的本地示例数据）里 14 个 HTML 图表先移到仓库外暂存（`/tmp/html-attic/`），**经用户确认后已彻底删除**（这 14 个从未入库，不可恢复）。PNG 预览保留，`chart-examples/README.md` 已改写为「HTML 时代留存预览」并指向 JSON 契约。工作区内 `.html` / `.css` 残留 = 0。
- **历史段落说明**：本文档 v0.8–v0.11 各段里的 `*.html` 文件名、`CHART` 结构、坐标数值、`chart-tokens.css` 配色都是 HTML 时代的历史记录，**对应文件已不存在**（回溯看 git `e4f3bb7`）；原文保留仅为决策追溯，不代表当前能力。
- **同步**：新建 `system-prompts/multi-clinical-result-comparison-v0.15.md`（后扩充至 **213 行**：HTML 清理版 + `## Subagent delegation` 段）；`references/chart-templates.md` 头部不再指向已删目录；`README.md` 新增 v0.15 段并把历史段里指向该目录的句子标注「deleted in v0.15」；重打 `dist/multi-clinical-result-comparison-v0.15.zip`（打包断言新增「拒绝 `.html`/`.css`/`.py` 入包」）。

## v0.15 change: 图表 envelope 契约 + 空目录兜底（2026-09-10，分享会话复盘后）

- **触发**：用户分享 Tool Smith 会话 `fa0c0317-6c35-4b3e-8a57-6490fa9eb1b4`（thread `55906375`，标题 “Snapshot of 折线图”，同一批 14 个 Lp(a) esid），问「子代理用上了吗？好像也没有变快」。复盘结论：
  - **sys v0.15 生效，但模型主动否决了委派**：msg#1 reasoning 原文「We have 14 esids. More than 5, and the task tool is available. So delegation is possible.」；msg#3 权衡 5+5+4 后否决，理由：(a) citation 元数据要逐字节，(b) **params MCP 结果会自动落盘**到 `/workspace/tool_results/pharmcube-query-clinical-result-with-params/call_*.jsonl`，用 `execute`+python 脚本 digest 更省，(c) 委派要多管一条线。→ **在本平台「结果落盘 + execute」形态下委派无收益**，脚本化 digest 才是真省钱项（本次 23 次 `execute`）。
  - **其实更快**：本次总时长 **5.5 分钟**（`latency_ms 329871`）、42 步、48 次工具调用、reasoning 10.3 万字符；同批 14 esid 历史基线 9.9 / 10.9 分钟。但该 thread 复用了旧上下文，不算干净 A/B。
  - **返工点两处**：图表 envelope（约 4 步）+ `/workspace/output` 空目录（3 步）；契约面（固定命名、绝对路径引用、`present_artifact`、144 个实体锚点）全部遵守。
- **根因 1（我们的文档 bug）**：部署端 `chart-visualization-json` 已是 **2026-09-10 新版**，协议要求成品为 envelope `{"id":"chart-visualization-json","iframe_template":"<与 config.js 全等>","option":{…}}`，并**显式拒绝**旧的 option 层平铺格式（`未包 envelope：…；旧格式（option 层配置）已不再兼容。`）；`iframe_template` 由 `apps/ai-charts-html` 每次发布 CDN 后刷新、**必须与运行期 `config.js` 的 `IFRAME_TEMPLATE` 全等**。而本 skill `references/chart-templates.md` 旧版写的是「**合并 JSON 无额外 envelope**」——**写反了**；`templates/charts/*.json` 三个模板也都平铺。模型因此写入 → 校验失败 → 读 `validate.js`(6.3KB) → 读 `config.js` → 重写 → 才 PASS。
- **根因 2（平台 bug，已交后端）**：`/workspace/output` 空目录不跨 `execute` 调用持久——早期 `mkdir -p` 过、后续 `ls /workspace/` 里已无该目录（`scripts`/`visualizations` 在），单独 mkdir 后仍报 `FileNotFoundError`，最后把 `mkdir -p` 与写入放**同一次调用**才过。
- **改动（全部在 v0.15 上原地改）**：
  1. `references/chart-templates.md`：能力来源表加「成品包裹层」行；§零 把「无额外 envelope」整条替换为 **envelope 硬规则 + 三键来源（禁止硬编码）**（首选复制图表 skill 自己的 `templates/{bar,line,timeline}.json`，退路 `cat config.js`，两者都不可读则 fail-loud）；§一 表下补「两者交付角色不同」；§二 步骤 1/2 改为「先复制图表 skill 模板拿 envelope → 再只替换 `option` 内层」；自检段加 envelope 前置确认、校验覆盖加三键，并新增「**权威只有部署端那一份**」避坑条（旧副本会给出错误的 PASS）。
  2. `templates/charts/{endpoint-bar,endpoint-line,evidence-timeline}.json`：三个文件头部加 `_comment`，标明它们是 **`option` 内层起点**、不是可交付成品。（`_comment` 被 Zod schema 的默认 strip 语义忽略，`option` 内层仍校验通过。）
  3. 同步改写交付措辞：`SKILL.md`、`references/{timeline-diagram,cross-trial-comparison,file-delivery}.md`、`templates/unified-evidence-report.md`。
  4. `references/file-delivery.md` 新增 **empty-dir fallback** 条目（`mkdir -p` 必须与首次写入同一次调用；报目录缺失就重做后继续）。
  5. sys v0.15 六处：File delivery 段加同一条 mkdir 规则；Chart contract 段补 envelope 硬规则（`templates/charts/*.json` 只是 `option` 内层）；timeline 段改为「先拷图表 skill `templates/timeline.json` 拿 envelope」；Final verification 的图表项加 envelope 与「旧副本 PASS 不算权威」、交付文件项加「与父目录同一次调用创建」；**子代理段新增「先试脚本化 digest 再考虑委派」**（避免下次再花一段 reasoning 权衡）。sys **213 → 214 行**（段落内改写，行数几乎不变）。
- **重打 dist**：`67c17a026d21bcd437c1940214f628c7f59068b70ba3f0178abc6f2969d3c5ae`（19 entries / 66440 B；上一版 `1a6b5274…` / 63387 B 作废）。
- **验证**：包内 envelope 措辞就位（`chart-templates.md` 11 处命中）、旧措辞「无额外 envelope」与硬编码 CDN 地址残留 0、包内三个 `option` 内层经图表 skill CLI 仍 `校验通过: bar/line/timeline`。**未验证项**：envelope 层校验本地做不到（手头只有前端给的**旧副本**图表 skill，本地无部署端 `validate.js`/`config.js`），须由用户在 Tool Smith 运行期确认。
- **教训**：上一轮「三模板全 PASS」是**无效验证**——验的是前端给的旧副本；上游协议升级后本地副本不再是权威。凡「上游能力」类结论，一律以**部署端实际安装的文件**为准。

## v0.15 change: 子代理委派规则上移入 sys（2026-09-10）

- **触发**：用户问「sys 是不是该强调下（子代理规则）」，并回复「我开了呀」——即本项目 Tool Smith 部署的 `capabilities_config.subagents` 开关**已开**，于是子代理变成真实可用能力；若 sys 继续零提及，会出现「工具可见但无约束」的裸奔（模型自行委派，而 `{{ref_n}}` 全局顺序、来源 marker 回显、不得跳过来源这些护栏只在 Skill 正文里）。
- **决定：在 v0.15 上原地改**（不新开 v0.16）——因为 v0.15 尚未投递 Tool Smith，属未发布版本，改版号无意义。
- **sys 变更**：v0.15 新增 `## Subagent delegation (when the `task` tool is visible and there are more than 5 esids)`（位于 Step discipline 之后、Evidence boundary 之前，L33-45）；Required workflow 第 1 步加同义指针。sys **200 → 213 行**。
- **Skill 变更**：`references/input-contract.md` 该节标题去掉 `pending verification`、状态改为「platform-supported, and enabled on our deployment — still opt-in」；Constraints 补「子代理不继承项目 sys/Skill，description 必须自带规格」「多 call 串行」；原「Verification checklist（4 项待问）」替换为「**Platform facts**（已对 Tool Smith 后端源码核实，2026-09-10）」六条。`SKILL.md` Input 段指针同步改写。
- **设计取舍**：即便开关已开，规则仍保持 **opt-in + 条件式**（>5 esid 才用），且**只写「不变量」不写「提速承诺」**——委派治的是上下文膨胀，而实测并发不存在（串行），端到端 token/耗时收益仍未量化。护栏优先于收益：`task` 不可用/失败一律 fail-loud 回退直读，绝不静默缩源。
- **阈值二次校准（同日，用户反馈）**：初版写「~20+ esid 才委派、每块 ≤10」，用户指出**产品侧选中上限就只有 20 个**，等于阈值卡在理论上限 → 改为 **触发 >5 个 esid、每块 ≤5**（6 → 3+3；20 → 5+5+5+5），并加「不得切细于 5（每块要花一个串行子代理回合）、能均衡就不留 1 个的零头」。附带修正旧例「20–50 esid」为「最多约 20」。
- **重打 dist**：`1a6b52744ac71605611721e8afd165ed9ee7f65120f6cf22368d32d926954403`（19 entries / 63387 B；旧 `b89024c8…` / 62896 B、`1a7db902…` / 63328 B 均作废；**该包随后被下一节的 envelope 修复版 `67c17a02…` / 66440 B 取代**）。本节的 sys/Skill/dist 改动落在提交 **`aa05104`**（分支 `v0.15-remove-html`，已 push，不合 `main`）。SKILL.md 与 input-contract.md 是在包内的，所以本次**运行时有变化**（与上一节「HTML 清理对运行时零影响」不同）。

## v0.15 change: 对齐上游 chart skill v1.0.9 + 渲染配置归 Skill + vendor 留档（2026-09-11）

- **触发**：① 用户要求执行上一轮挂起的 4 处文档微调，且**保持 v0.15 版本号不变**（不下发新版本）；② 用户转达 TS 前端建议：在 sys 的**可视化渲染**部分加一条「渲染配置优先取自 Skill」，避免图表被内置渲染路径绕开、skill 不被触发。
- **上游版本核实**：解包前端交付的 `chart-visualization-json-v1.0.9.zip`（2026-09-10 build，源包 SHA-256 `572fbe553978696e3f915b6a13ea9a7ebe31f4be6d00987c057c8daf75e20438`），逐条比对我们已编码的规则——envelope 三键、`iframe_template` 需与 `config.js` 的 `IFRAME_TEMPLATE` 全等且每次发布 CDN 后刷新、`RENDERABLE_CHART_TYPES = line|bar|timeline`、bar `group` 默认 false / `stack` 默认 true、`theme ∈ default|academy|dark`（默认 default）、`width` 600 / `height` 400、行格式 `{label, value:number, group?, description?, drill?}`、timeline `time` 必填 / `weight` min 0 默认 0 / `legend[].shape ∈ circle|empty-circle` / 数组顺序即时间序不重排 / `weightLegend.show` 默认 true、`dataSource`+`describe` 不参与绘制——**全部一致，无规则变更**。
- **本地校验空缺补齐**：用留档的 v1.0.9 副本跑 `validate-cli.js`（exit 0 通过 / 1 失败）。正例：我们三个 `templates/charts/*.json` 的 `option` 内层套上游 envelope（含 `_comment`）→ 全 PASS；负例：平铺 `option` → `未包 envelope：…旧格式（option 层配置）已不再兼容。`、陈旧 `iframe_template` → `必须与 config.js 的 IFRAME_TEMPLATE 全等，期望 …20260910-153117…`、相对路径 template / 错 `id` 均报错，而**多出一个未知顶层键**与**极简 `option`** 都 PASS（前者被 strip、后者用 bar 默认值）——即上游对未知字段是「静默忽略」。
- **文档微调（4 处，全在 v0.15 原地改）**：
  1. 「协议 v2」措辞废除（上游只有 zip 版本号，没有 v2 概念）→ 改为「图表 skill v1.0.9 / 2026-09-10 build」（`references/chart-templates.md` 两处：能力来源表 + §零 硬规则标题）。
  2. 能力来源表「可渲染模板」行补上游最小骨架 `templates/visualization.json`。
  3. §零 新增「上游对未知字段静默忽略（Zod strip）」一条：`_comment` 之类说明键不会校验失败，但渲染层不保证使用 → 面向读者的说明写 `describe`/`description`。
  4. §零 记录 v1.0.9 新增可选字段（`bar.minCategoryGap`、`bar.style.barWidth`、各类型 `style.palette`/`texture`/`backgroundColor`）**本 skill 不用**，保持最小字段集。
  5. 「权威只有部署端那一份」条补「离线核对可用带版本号副本，但**前提是版本与部署端一致**，且副本内嵌的 `iframe_template` 只是留档时点的值」。
- **渲染配置归 Skill（前端要求，落三处）**：
  - `references/chart-templates.md` §零 新增「**渲染配置一律取自图表 skill（硬规则）**」：类型/字段名/默认值/`theme` 以图表 skill 的 `templates/*.json` 与 `references/schemas/` 为准，**原样复用、不重述、不扩展、不自造**；交付通道只有「图表 skill 定义的 JSON 数据文件 + `::visualization`」，**不要为本 skill 的 JSON 图调 `read_me`**（平台 Visualizer 段声明 Skill-defined data file 无需 `read_me`）、不用 `show_widget`、不退到内置 chart 模块（Chart.js/HTML/SVG）、不另造字段与配色。
  - `SKILL.md`：必读文件第 11 项把上游图表 skill 标为「**render config and single source of truth**，原样复用」，并补「唯一图表通道 + 不使用内置 chart 模块/`show_widget`/HTML/SVG/Mermaid + 不为这些 JSON 图调 `read_me`」；第 6 步 mixed-inputs 图表段补同义约束。
  - sys v0.15 Chart contract 新增独立段 **"The Skill owns the chart rendering config — never bypass it (hard rule)."**（类型/字段名/默认值/`theme`/envelope 一律 verbatim 取自图表 skill 模板与 schema；唯一通道是 Skill 定义的 JSON + `::visualization`；不得用平台内置 chart 模块 / `show_widget` / 手写 HTML-SVG-Chart.js 替代；不为这些图调 `read_me`；不得因「有个图会更好」而绕开 Skill）。Final verification 的图表项同步加「每张图都出自 Skill JSON 契约、渲染配置来自图表 skill 模板/schema，无内置模块/`show_widget`/`read_me`/自造字段与配色」断言。sys **214 → 216 行**。
- **`vendor/` 留档落地（新约定）**：`vendor/<上游 skill 名>/<版本>/` 逐字节复制上游包（本次 `vendor/chart-visualization-json/1.0.9/`，47 文件 + `node_modules`），并写 `vendor/README.md`（来源 zip、SHA-256、接收日期、该 build 内嵌的 `iframe_template`、跑法、协议要点、更新流程）。**默认不入 git**（`.gitignore` 加 `vendor/**/node_modules/` 与 `vendor/chart-visualization-json/*/`）——上游源码含内部 CDN 地址，是否入库待用户决定。留档副本自证可用：`node scripts/validate-cli.js templates/{bar,line,timeline,visualization}.json` 全 PASS。**skill/sys 文档内零 `vendor/` 引用**（部署端无此目录，已 grep 确认）；`dist` 内零 `vendor`。
- **顺带修正**：`templates/unified-evidence-report.md` 的旧措辞（「无额外 envelope」类）已改；全 skill 残留旧措辞 = 0，硬编码 CDN 地址 = 0。
- **重打 dist**：`495647bf3e1daf6ba1adfa6693c7d2441fbb90ec901d529201f98323b2b92cf3`（19 entries / 67496 B；上一版 `67c17a02…` / 66440 B 作废）。**已提交并 push**：本节的 14 个 tracked 文件改动落提交 **`4040ff3`**（分支 `v0.15-remove-html`，不合 `main`）；未跟踪的 `vendor/` 未入库。
- **待用户决定**：① `vendor/`（含 `vendor/README.md`）是否入库；② 「6–8 条且单条 payload 不大时直接直读」的下限豁免是否写进 sys。

## v0.15 change: 上游 chart skill v1.0.10 支持 line/bar 负值（2026-09-11）

- **来源与留档**：前端交付 `C:\Users\YYMF\Downloads\chart-visualization-json-v1.0.10.zip`（明文 zip，头 `PK\x03\x04`，无需走 Windows Python 解密）；源包 SHA-256 `57c36b0f4c9a409b483eb245c807afd87a1fbce4692ed9d13156e84d9323a4b7`，54,525 B，47 条目。留档 `vendor/chart-visualization-json/1.0.10/`（逐字节复制，与裸解包目录 `diff -r` 空差异，47 文件全 SHA 校验通过），`vendor/README.md` 补该版本 provenance、与 1.0.9 的差异表与负值协议要点。
- **差异面极小（6 个文件）**：`config.js` 与 4 个 `templates/*.json` 的 `iframe_template` 全部指向新发布 `…/ai-charts-html/test/20260911-134013/iframe-template.json`；`references/chart-types.md` **仅 +1 行**（负值语义）；`SKILL.md`、`schemas/*`、`scripts/validate.js` 逐字节未变 → **协议零变更**，`schemas/data.js` 仍是 `value: z.number()`（没加 `.nonnegative()`），即上游选「支持负值」而非「fail-loud」。
- **修的是渲染器（源码级 + 实测双证）**：新 bundle `…/20260911-134013/static/index-DocPC1fd.js`（旧 `index-DXN82l-u.js`）——bar 值域 `Si({min:0, max:maxValue||0})` → `vi({min: Math.min(0, n.minValue||0), max: Math.max(0, n.maxValue||0)})`（数据提取开始返 `minValue`）；柱长 `max(plotW*(v/domainMax), 3)` + 固定起点 `padL` → 零轴 `k(0)` + `max(|k(v)−k(0)|, 3)`；横向刻度/网格 `padL + plotW*tick/(domainMax||1)`（负域算出负像素）→ 按 `[domainMin, domainMax]` 归一化；新增单系列负值柱紫色判定；line 侧 `max: i<0 ? Math.max(s,0) : s`（负值数据补 0）。
- **实测（同一份全负 bar 数据，两版 bundle 各渲一次，量 DOM 真实盒）**：旧 5 根柱 `3/3/3/3/3 px` 起点同一点（静默炸）；新 `566.8 / 818.8 / 852.8 / 865 / 881.6 px`、右端全部 `x+w = 1320`（即 0 轴）、`881.6/101.1 = 865/99.2 = 852.8/97.8 = 818.8/93.9 = 566.8/65.0 = 8.72 px/单位`、fill 全 `#814487` 紫 → 双向生长正确。对照图 `/tmp/nb_fix_compare.png`（上旧下新，红/绿框）。**回归**：正值分组柱逐像素一致（`275.3/233.8/109.5/68.1`，x/y/fill 全同）、负值折线正常（仅因「补入 0」整体上移压缩）。
- **本 skill 零改动（结论成立的理由）**：仓库内 `grep vcdn.pharmcube.com|2026091*`（排除 `vendor/`）零命中 → 从不硬编码 `iframe_template`，运行期从部署端 chart skill 模板取 envelope，发布 ID 变更自动跟随（本次更新正好验证该硬规则）；skill/sys 内 `负值` 相关文字本来就是 0 处，无绕行约定需撤；先前记的「若上游选 B（fail-loud）则回 skill 落非负值约定」**不触发**。重打 dist 得同一 SHA（`0deda5d3…`，dist 只装运行文件）。
- **部署端未升级**：用户 2026-09-11 决定暂不把 v1.0.10 传到 Tool Smith，故部署端仍是 1.0.9 / `20260910-153117`（`vendor/README.md` 已如实标注）；日后升级后若出现 `iframe_template` 不匹配报错属预期（模板值随 CDN 发布刷新）。
- **记账**：本节改动随记账提交 push 到 `v0.15-remove-html`（提交信息 `v0.15: record upstream chart skill v1.0.10 negative-value support`）；`vendor/1.0.10` 仍按既有约定不入库。

## v0.15 change: `::visualization` 标签与实体锚点边界 + 图表内 `{{ref_n}}` 外观问题放行（2026-09-11，两个新分享会话复盘后）

- **触发**：复盘两个并发的新分享会话（同一 Tool Smith 项目 `a7cdda65…`）：`d83e5527…`（标题「条形图」，18 esid / 11 试验，混合跨试验）与 `087abf28…`（标题「时间轴」，4 esid，全部同一试验 HARMONi-6）。
- **v0.15 生效确认（两个 run 都验到）**：envelope 一次过（A 用 `json.load` 读图表 skill `templates/bar.json`、B 直接 `cp` `templates/{timeline,bar}.json`，只换 `option` 内层；`校验通过: chart-visualization-json（option.type=bar）` exit 0，零返工）；固定命名契约全对（`/workspace/output/report.md`、`citations.json`、`/workspace/visualizations/evidence-timeline.json`、`endpoint-bar-1.json`）；`/workspace/output` 空目录 bug 未复现（建目录与首次写入同一次调用）；渲染配置归图表 skill 的硬规则被遵守（读了图表 skill `SKILL.md` + `templates/*.json`，**没调 `read_me`、没用 `show_widget`、没走内置 chart 模块**）；只 `present_artifact` 报告。
- **耗时/委派**：A 5.0 min / 39 步 / reasoning 83.2k 字符（18 esid，**未委派**——reasoning 明写「多于 5 个，但指引说先试文件化 digest」，符合 opt-in 设计）；B 2.8 min / 27 步 / 46.8k 字符。对照 v0.12 时代同批 14 esid 的 10.9 min / 178k 字符 → 约 2× 提速、reasoning 减半（两 run 并行）。**图表策略也对**：A（跨试验）不出 timeline；B（单试验 4 披露）合并同分析同披露为 1 个证据状态，timeline 3 节点。
- **新增规则（本轮落地的唯一改动）**：`::visualization[...]` 的方括号是**图表标题、不是正文实体提及** → 不进实体锚点覆盖、不算「有 ID 的提及必须已引用」；标签内不得出现裸试验名/药品名，用描述性标题，要点名的实体放到图前后说明里再锚定。落点 3 文件：`references/entity-inline-reference.md`（适用范围 1 条 + 校验 1 条，76 → 78 行）、`SKILL.md`（与「图表文件不写 entity」同处 1 句）、sys v0.15（anti-patch 硬规则后 1 句，防止「每个提及都要锚定」被读成覆盖图表标签）。sys 仍 216 行、`SKILL.md` 仍 151 行。触发原因：B 的模型把 `::visualization[HARMONi-6 证据链时间轴]` 的标签当成未锚定裸试验名，自己改名并重跑校验（约 3 步返工）。
- **图表内 `{{ref_n}}` 问题：查实后按用户决定放行**。事实：图表 iframe **不做**标记替换（部署端 bundle `…/20260910-153117/static/index-DXN82l-u.js` 内 `{{` 命中 0）；时间轴节点说明 `div.mf-ai-charts-timeline-desc` 与 bar hover tooltip `div.mf-ai-charts-tip-desc` 都是逐字渲染 `description`。用 B 会话真实 option + 部署端 bundle 在本地（`google-chrome --headless=new`，按平台 iframe 模板把 `option` 灌进 `window.chartOptions`）渲染后做 DOM/布局探针：标记子串占真实盒子 ~89×17 px、`visibility:visible / opacity:1`、颜色与说明文字同色 → 是**被画出来的可见字符**；去掉标记后同坐标区域墨迹从 916 px 降到 51 px、说明块高度 198 → 158 px。影响面：**仅外观**（读者看到字面量标记，点不了、不提供真正的可追溯性），数值/标签/结论/`citations.json` 全不受影响。**用户拍板：图先允许标引 ref，等开发/前端有人提出或前端做了替换再改**；`chart-templates.md:114` 与 `timeline-diagram.md:20` 的口径不一致（bar 无要求 / timeline 要求）也暂留。
- **bar 负值已由上游修复（v1.0.10，见下节）——本条闭环**。原状：值域硬编码 `[0, maxValue]`（`Ls()` bar 分支 + `Ts()` 只算 `maxValue`），全负 → `domainMax=0` → 柱长 `Math.max(w*(v/0), 3)` 卡 3px、轴刻度飞出画布；用户拍板**不在本 skill 绕**，驱动上游修（A 支持负值 / B `value.nonnegative()` fail-loud），本 skill 暂不动；负值数据优先选 line（line 值域取数据 min/max，天然支持负值）。**2026-09-11 上游落地 A 方案**：bar 恒以 0 为基准双向生长（单系列负值柱紫 `#814487`）、line 轴含负刻度并补入 0；实测旧 bundle 5 根负值柱全 3px、新 bundle 长度 ∝ 降幅（8.72 px/单位）。**本 skill 仍零改动**（B 分支未触发）。
- **重打 dist**：`0deda5d3b6fa94a279ed62b89e5b107c01bf84516054d852f25a2a71cfe91408`（19 entries / 67897 B；上一版 `495647bf…` / 67496 B 作废）。脚本 `/tmp/pack15b.py` 幂等（固定 stamp、19 文件断言、fail-loud 守卫），本次仅 SKILL.md 与 `entity-inline-reference.md` 内容变化。
- **验证工具经验**：本地可用 `/usr/bin/google-chrome --headless=new` + 部署端 bundle 复现 envelope 渲染，并用 `--dump-dom` 做 DOM 级验证（比截图 OCR 可靠）；本环境**视觉子代理通道不可用**（deepseek-v4-flash-vision-exp 403 billing / glm-5.3-flash 收到空图像）→ 需要目检时把 PNG 存 `/tmp` 交用户自己看。
- **待用户决定**：① 本批（3 个 doc 文件 + README/PROJECT_STATE + 新 dist）是否提交/push；② `vendor/` 是否入库。

## v0.14 change: 复用上游 chart-visualization-json skill；撤销 TEMP 双写（2026-09-08）

- **触发**：前端发来两份说明书（`chart-templates.md` + `chart-visualization-json-prompt-examples.md`；两份均为 Windows DLP 透明加密文件，WSL 直读只得密文，经 Windows Python 提取明文后阅读）。**结论：说明书有用**——上游 `chart-visualization-json` skill 已是图表协议 / 模板 / Zod schema / CLI 校验的权威实现；我方 v0.12 的平行实现（自研 `validate-chart.py` + 本地重述协议）属重复维护，且存在「本地宽松校验 PASS 但真实 Zod 渲染失败」的风险。
- **决策（用户拍板）**：v0.13 弃用但不删除；**以 v0.12 为基线**做 **v0.14**；图表能力**复用上游 skill**（协议/模板/schema/校验）；**撤销 TEMP 双写**，`::visualization` 引用回切 `.json`（开发即将联调，renderer 即将落地）。版本号取 v0.14 而非原地改 v0.12，避免与已部署的 v0.12（TEMP 版）及 `dist/v0.12.zip` 混淆（可应要求改名）。
- **`SKILL.md`**：frontmatter `description` 增「图表产物为纯 JSON，由复用 chart-visualization-json skill 产出」；每次运行必读清单增 `references/chart-templates.md` 并声明复用关系；中英文两处校验命令改图表 skill CLI；**整段删除 TEMP section**。
- **`references/chart-templates.md` 整篇重写**：新增「能力来源表」（上游 `SKILL.md` / `chart-types.md` / `templates/{line,bar,timeline}.json` / `schemas/` / `validate-cli.js`）；协议要点以图表 skill 为准（`RENDERABLE = line|bar|timeline`；`dataSource`/`describe` 为不参与绘制的元数据；bar 默认 `stack: true`，并排柱状须显式 `group:false, stack:false`；timeline `time` 必填、`weight` 驱动圆点、`legend` 用 `circle`/`empty-circle` 且与 `data[].group` 对应）；`templates/charts/*.json` 降级为「临床场景预填起点」；新增**校验环境不可用时的降级规则**（不静默跳过、不退回自研脚本；先 `ls` 定位真实路径重试一次，仍不可用则在报告中声明「图表校验环境不可用」、省略该图 `::visualization` 引用、以精确数值表为主交付）。
- **其余引用/模板**：`references/timeline-diagram.md` 去 TEMP 两行 + CLI 命令替换；`references/file-delivery.md`、`references/cross-trial-comparison.md`、`templates/{unified-evidence-report,mixed-comparison-report,cross-trial-report}.md` 的校验命令与终检项全部改为图表 skill CLI。
- **`templates/charts/`**：删除 `validate-chart.py`；`render-preview.py` 移入 `docs/legacy-html-charts/`（该归档目录已在 v0.15 整目录删除）；`endpoint-bar.json` 补 `group:false, stack:false`；v0.13 残留的 `templates/quick-comparison-report.md` 移出发布集（副本在 `docs/legacy-v0.13/`）。
- **新 `system-prompts/multi-clinical-result-comparison-v0.14.md`**：基于 v0.12，删除 TEMP override 段与 Final verification 的 TEMP 项；`### Chart contract` 改为 v0.14 并新增声明段（协议/模板/Zod schema/CLI 为唯一真源，不自研校验、不产 HTML/SVG fragment、不写 `.preview.html`）；两处校验命令改 CLI 并补 bar `group/stack` 提醒；Final verification 新增「每个 `::visualization` 引用必须指向 `/workspace/visualizations/` 下的 `.json`」与「校验环境不可用时禁止输出未校验引用」两项。
- **验证**：三个临床模板经上游 CLI 全部 `校验通过`（bar / line / timeline，exit=0）；解包后包内三模板同样全 PASS；发布集内 TEMP / `preview.html` / `render-preview` 残留清零，仅 `chart-templates.md` 保留两处**历史说明**（「`validate-chart.py` 已归档」/「v0.12 调试期双写方案已随 v0.14 移除」）。
- **阻塞项（待上游确认）**：(a) 校验命令与技能的权威路径到底是前端说明书写的 `.agents/skills/chart-visualization-json/scripts/validate-cli.js` + `pnpm validate:chart`，还是上游 `SKILL.md` 写的 `/workspace/skills/chart-visualization-json/scripts/validate-cli.js` + `node`；(b) Tool Smith 工作区是否已装 `zod`/`node_modules`——上游 `package.json` **未声明依赖**，缺依赖时 CLI 以 `Cannot find module 'zod'` 崩溃（本地测试时用 `npm install zod --no-save` 绕过）。
- **DLP 排除记录**：两份前端文档 `head -c 8` 为 `88 7d 1c .. 3f 02 4c 00`（DLP 包装头，非 PDF/Office 魔数），WSL 直读高熵密文；改用 `C:\Users\YYMF\AppData\Local\Programs\Python\Python311\python.exe` 读 `D:\Users\feishu_download\` 抽明文到 `\\wsl.localhost\Ubuntu-22.04\home\xupeipeioo1\tmp\frontend-chart-docs` 后正常解析。
- **输出文件命名契约收紧（2026-09-09，用户提「后端好传输」）**：原契约只有「后缀固定 + slug 需小写连字符」的弱约束，slug 由模型自由发挥，后端只能 glob 或猜。**先查后端实际消费方式**，结论三点：(a) 报告路径**无需预知**——`present_artifact` 把真实 `path` 记入 run-local `ArtifactPresentationCollector`（manifest 存 `{"path","filename"}`），前端卡片直接用；(b) 图表路径**无需推导**——每张图在报告里以 `::visualization{path="/workspace/visualizations/..."}` 绝对路径逐条携带；(c) **唯一需要推导的是引文 JSON**（报告正文刻意不含引文清单）。且 `backend/src` + `frontend/src` 里 `citations` / `-report.md` **零命中**——后端/前端尚未实现消费，**现在定契约零成本、不构成 breaking change**。
  - **最终采纳（方案 C，后端开发者明确要求「加个约束文件名，我直接写死好了，就不从 tool 里取了」）**：**四个产物路径全部固定**，移除 `<slug>` 概念——报告 `/workspace/output/report.md`、引文 `/workspace/output/citations.json`、时间轴图 `/workspace/visualizations/evidence-timeline.json`、定量图按**图表类型 + 序号**命名：柱状 `/workspace/visualizations/endpoint-bar-<n>.json`、折线 `/workspace/visualizations/endpoint-line-<n>.json`（`<n>` 为该类型图在正文中的出现顺序，从 1 开始；单张柱状图恒为 `endpoint-bar-1.json`，单张折线图恒为 `endpoint-line-1.json`）。需编号是因为混合/跨试验输入允许**每组各一图**（`mixed-comparison-report.md`、`cross-trial-comparison.md`），同类型也可能多张，定量图数量不限于 1。重跑**覆盖**同名文件（一个 workspace 一份当前报告），与平台 `present_artifact` 的 “current version of this path” 语义一致；已写进契约“不得用加后缀的方式规避”。
  - **类型区分方式（2026-09-09 追问后定稿）**：用户追问「line 和 bar 在哪里区分」。上游 `chart-visualization-json` 的真实区分点在 **JSON 内部的 `type` 字段**——`scripts/validate.js` 的 `TopLevelSchema` 把 `type` 定为 `z.enum(CHART_TYPES)`（**必填**，非 optional），`RENDERABLE_CHART_TYPES = ["line", "bar", "timeline"]`，渲染器即按 `type` 派发。最初定稿的 `endpoint-chart-<n>.json`（数量词命名）经追问后判定不够：混合模式下折线/柱状混编序号，`endpoint-chart-1.json` 不保证是哪种图，后端无法对某一种图写死。故把**类型提到文件名**（`endpoint-bar-*` / `endpoint-line-*`），并在 `references/chart-templates.md`、`references/file-delivery.md`、sys v0.14 File delivery + Final verification 写入**双向一致约束**：文件名类型必须与 JSON 内 `type` 一致（fail-loud 校验项）。文件名供人与后端做稳定索引，渲染仍以 `type` 为准。
  - **落地文件**：`references/file-delivery.md`（`## Naming contract` 改为固定路径表 + 重写 Deliverables / Delivery sequence / 验证项 / `present_artifact` 调用）、`references/citation-and-ref.md`、`references/chart-templates.md`（复制示例、引用示例、交付路径契约、CLI 自检命令均换成固定成品名）、`references/timeline-diagram.md`（2 处）、`references/cross-trial-comparison.md`（1 处）、`templates/{unified-evidence-report,mixed-comparison-report,cross-trial-report}.md`（共 4 处 `::visualization` 路径）、`SKILL.md`（必读清单第 9 条、同试验流程、Output firewall）、sys v0.14（Step 9、File delivery 硬规则、citation 段、两处 `::visualization` 示例、Final verification 3 项）。机械替换全部经 Python 断言脚本（`assert n == count`）；第一轮在 `templates/mixed-comparison-report.md` 因实际 2 处而被断言拦下（脚本中止未写入），修正计数后继续——断言机制有效。全库 `grep` 残留扫描：`<slug>` / `xxx-` / `/workspace/visualizations/<` 全部为 0。dist 重打，19 entries / 63015 B，SHA-256 `816b3174580c350876285d0748937f54fb6e43961632353773e3937376e8f67a`。
  - **已知代价（已告知用户）**：卡片与下载名会变成 `report.md`（`present_artifact` 的显示名只能从路径派生，无 `display_name` 参数），报告主题靠文件内 H1 承载；同一 workspace 多次运行会覆盖旧报告（历史需后端/平台侧快照）。若后续要改善下载名，平台侧给 `present_artifact` 加 `display_name` 参数是干净做法。
  - **上一轮曾按方案 A 落地（已被本轮覆盖）**：保留描述性 `<slug>` + 强制两文件同 slug + 正则 `^[a-z0-9]+(-[a-z0-9]+)*$` + ≤40 字符 + 幂等复用，引文路径 = 报告路径单次后缀替换；因后端明确不要推导而废弃。

## v0.12 change: 输入切 esid + params 拉取；图表切外部 JSON 协议（纯 JSON 产物）

- 背景（用户批准，2026-09-01 起三批次执行）：因上游/前端协作需要，输入契约从「每源一个 .md 附件」改为「**选中 esid 列表** + Skill 经 MCP `pharmcube-query-clinical-result-with-params`（`extra_esids` + 严格 `selected_fields`）自拉详情」；图表从「自研 HTML fragment」改为「**外部 chart-visualization-json skill 的纯 JSON 协议**」（仅 `line`/`bar`/`timeline` 可渲染），本地只保留自研 JSON 结构校验脚本。**schema 权威真源 = `docs/params-tool-schema.md`**（用户粘贴存档；远端 data schema 服务 172.17.16.224:31234 经飞连不可达，无法自动 dump 运行时 ALLOWED_FIELD_NAMES，以此存档为准）。  - **删减重复小节（2026-09-10，前端开发反馈「这一段和 chart skill 重复了，可以删掉」）**：`references/chart-templates.md` 删除末尾三节——「三、配色与渲染」（theme/色板/HTML token 均属渲染层职责）、「四、与 chart-visualization-json skill 的关系」（与文件头「能力来源表」重复）、「五、当前版本边界」（v0.11 HTML / v0.12 双写 / validate-chart.py 属内部历史，非运行时契约），共 964 字符；文件从 136 行降至 114 行，小节收归为「零、协议要点 / 一、选型规则 / 二、怎么用」。**保留性核验**：三条守卫项未随删除流失——① 「不写 Mermaid、不产出 `.html`」在「零」末条（并在 `SKILL.md` ×1、sys ×4）；② 「不混入自定义色板/CSS/HTML token」已并入「零」末条（sys 另有 "do not restyle or swap palettes"）；③ 「证据边界只能来自 params 字段」在「一」末条。删除前逐项 grep 比对，确认无其它文件引用被删小节标题。

- **图表富文本取舍（用户拍板）**：协议能承载的说明文字（data point `description` + 顶层 `describe`/`subTitle`/`dataSource`）保留；协议外富文本（行内 `{{ref_n}}`、CI/误差线、交互 tab）丢弃；数值/边界由正文表格承载。**校验脚本（用户拍板）**：保留自研——`validate-chart.py` 重写为纯 Python JSON 结构校验器（不依赖 node/zod）。
- **图表契约**：`templates/charts/` 下 `endpoint-bar.json` / `endpoint-line.json` / `evidence-timeline.json` 三个 JSON 骨架（字段完全对齐外部协议）；旧 HTML 五件（chart-tokens.css + 三 .html + 旧 validate-chart.py）归档到 `docs/legacy-html-charts/`（该目录已在 v0.15 整目录删除，回溯看 git `e4f3bb7`）；bar 用 `direction:"horizontal"`、line 用 `group` 分系列、timeline 用 legend/weightLegend/data{time,label,group,weight,content,description}；**data[] 排序责任改为生成方**（前端不重排：bar 降序、line/timeline 时间序由 Agent 排好）。`references/chart-templates.md`、`references/timeline-diagram.md` 整篇重写为 JSON 协议；`references/cross-trial-comparison.md`、`references/same-trial-evolution.md`、`SKILL.md` 与三份报告模板的图表段 .json 化。
- **输入契约**：`references/input-contract.md` 整篇重写（保留 subagent 预写章节为可选、pending 验证）；`references/citation-and-ref.md` / `input-and-extraction.md` / `file-delivery.md` / `entity-inline-reference.md` / `SKILL.md` Input+Evidence boundary+Workflow、三份报告模板 source_* 单元格全部改为 params 字段。字段映射：`source_title`→`paper_title`、`source_url`→`full_article_link`、`source_paper_release_time_str`→`paper_release_time`、`source_nct_id`→`projects[].associate_ids`、`source_trial_abbr`→`trial_abbreviation`、`source_drug_entities`→`arms[].drugs[].drug_earth_id`+名称、`source_company_entities`→`projects[].company_ids`+名称、`source_full_text`→`abstract_text`/`summary`/`study_results` 组合（无直接等价）。引文 JSON 的 `title`/`link`/`paper_release_time_str` 三个 key 不变，值来自 params 返回字段 byte-for-byte。
- 新系统提示词 `system-prompts/multi-clinical-result-comparison-v0.12.md`（基于 v0.11：输入 esid + params、证据边界改 params 临床内容字段、实体表改 params 实体字段来源、图表段改纯 JSON + validate PASS + 排序责任、Final verification 全改）；重建 `dist/multi-clinical-result-comparison-v0.12.zip`（20 文件 = v0.11 集去掉 css+3 html、加 3 json，系统提示词不入 zip）；README v0.12 段 + 文件清单 + 配置。
- 验证：三份 JSON 骨架 `validate-chart.py` 全 PASS；skill 本体（SKILL.md+references+templates）旧术语（source_*/attached/.html 图名/CHART 数据）清零（仅保留 input-contract 映射对照列与 chart-templates「不再产出 .html」历史说明等有意保留）；v0.12 系统提示词旧措辞清零。
- 后补小修（2026-09-07）：`templates/charts/endpoint-bar.json` 的 `describe` 残留 v0.11 旧 HTML 语义「本模板按 value 从高到低自动降序，无需人工排序」——v0.12 协议为渲染端不重排、`data[]` 降序排序由生成方负责。已改为「`data[]` 由生成方按 value 从高到低排好序后交付（渲染端不重排）」；dist v0.12.zip 仅替换该条目后重建，20 文件逐文件 SHA-256 对比 BAD=0。
- **TEMP 双写调试资产（2026-09-07 用户批准「双写安排」）**：Tool Smith 对话页目前**不渲染 chart-visualization-json 的 `.json` 图**（只对 `.html` fragment 原生绘图），所以 v0.12 纯 JSON 产物在对话端不可见图。调试期方案 B 落地 = skill 运行期**双写**：每个 `.json` 成品（`validate-chart.py` PASS）后用随附 `templates/charts/render-preview.py` 从**同一份 JSON** 机械生成同名 `<name>.preview.html`（单一数据源，HTML 内嵌同一 JSON，禁手工另填），报告正文 `::visualization` **引用 `.preview.html`**（对话端可见），`.json` 作为正式契约随行交付。改动：`SKILL.md` 新增「TEMP (debug only — remove when the chart renderer is deployed)」权威覆盖段（override 全文档含模板的 `.json` 引用示例）；`references/timeline-diagram.md` / `references/chart-templates.md` 各加 TEMP 提示行；新增 `templates/charts/render-preview.py`（自原型 `/tmp/chartpreview/render-preview.py` 收编，fragment-safe 子串自检 + `-o` 输出）。**dist v0.12.zip 正式快照未动**，另打 `dist/multi-clinical-result-comparison-v0.12-temp-preview.zip`（21 文件，逐文件 SHA-256 BAD=0）。**回切**：renderer 落地后删除 SKILL.md TEMP 段 + 两个 references 的 TEMP 行 + `render-preview.py`，报告引用回切 `.json`，删除本 zip。
- **（后补 2026-09-07 会话诊断）TEMP 双写进系统提示词（方案 A）**：用户共享会话 share4（Lp(a) 跨试验）/share5（sqNSCLC）/share6（HARMONi-6）出现「一会 json 一会 html」不稳定——同一部署端 skill 资产一致（SKILL.md 含 TEMP 段），但**系统提示词 v0.12 仍是纯 JSON 契约（无 preview 字样）**，两契约互斥，Agent 裁决摇摆：share5/6 跟 skill TEMP 引用 `.preview.html`，share4 判「sys 更高权威」引用 `.json` 并跳过 render-preview（reasoning 有明确权衡原文）。根因 = TEMP 双写只进了 skill、没进 sys；skill（load_skill 注入）对 Agent 是次级指令。修复（用户拍板方案 A）：`system-prompts/multi-clinical-result-comparison-v0.12.md` 图表段（`### Chart contract` 标题下、所有 `.json` 引用示例之前）新增「TEMP override (debug only — remove when the chart renderer is deployed)」四步双写段，显式声明覆盖本 prompt + skill 内全部 `.json` 引用示例；`Final verification` 图表检查项后补同义 TEMP 双写检查项。sys 与 skill 对齐后 Agent 无论读哪层都指向 `.preview.html`。**该 sys 改动需 Tool Smith 侧重新装载/重传系统提示词**（此前结论「sys 不用重传」作废，仅限本轮 TEMP 期间）。
- **（2026-09-08 v0.14 撤销 TEMP）** 用户拍板：renderer 即将联调，**撤销双写**。已删除 sys v0.14 的 TEMP override 段与 Final verification TEMP 项、`SKILL.md` 的 TEMP section、`references/timeline-diagram.md` 与 `references/chart-templates.md` 的 TEMP 提示行；`render-preview.py` 移入 `docs/legacy-html-charts/`（该目录已在 v0.15 删除）；报告引用回切 `.json`。`dist/multi-clinical-result-comparison-v0.12-temp-preview.zip` 降级为历史快照（勿用）。详见「v0.14 change」段。
- **契约未定待办（挂起/交上游）**：表格整表复制/下载 CSV-Excel（产品验证中，见文首待办段）；bar 柱下钻（parked，等何林杰 drillDownValue 案例）；subagent 四项验证（next week 上游协作方）。

## v0.11 change: 试验简称内联（trial short name as entity display label）

- 用户需求：「试验简称能内联」——报告里试验展示名优先用简称（如 HARMONi-6、TRAIN-2），而不是只显示注册号。
- 数据源核实（只读）：`np_clinical.base.trial_abbreviation` 是现成字段，形态为对象 `{text}` 或数组 `[{text}]`（多别名）；覆盖度：nsclc 三期积极 88/100、ind579 三期 70/100、TRAIN-2 5/5。试验简称 ID 不新增——`entity:trial:` 的 ID 仍是注册号（`source_nct_id`），简称仅作展示名。
- 契约：附件新增可选元数据行 `source_trial_abbr`（试验简称，多个别名 `;` 分隔，去重、丢弃含 `|`/`;` 的值；无简称不写行）。展示名优先级 = `source_trial_abbr` → 注册号；行缺失/为空 → 回退注册号（自然降级）。注册号仍只作 `entity:trial:` 的 ID。
- 改动文件：`evals/fetch-np-clinical-attachments.mjs`（`_source` 加 `base.trial_abbreviation` + `extractTrialAbbr` + render/parse/roundtrip 加 `source_trial_abbr`）；`references/input-contract.md`（ES lookup + JSON 形状 + 文件布局 + 实体元数据行 + 读取协议 + 可复现检查）；`references/entity-inline-reference.md`（trial 规则：简称优先展示、ID 仍注册号、图表内仍禁）；三份报告模板（研究名称/注册号、试验/注册号单元格改简称优先示例）；`SKILL.md`（阅读清单 #10 + Input + 证据边界 + 工作流第 8 步）；新增 `system-prompts/multi-clinical-result-comparison-v0.11.md`（基于 v0.10，Entity 表加「试验（展示名优先用简称）」行 + 展示名规则 + Final verification）；README（v0.11 段 + 文件清单 + 配置）；重建 `dist/multi-clinical-result-comparison-v0.11.zip`（21 文件，系统提示词不入 zip）。`validate-entity-refs.mjs` 无需改（trial ID 仍是注册号）。
- 重拉 `evals/iteration-16` 三个数据目录（均 gitignored）：nsclc-50 50 条（34/50 带简称，顺序与旧一致）、ind579-phase3-50 59 条（40/59 带简称）、nct01996267 5 条（5/5 带 TRAIN-2，`NP_CLINICAL_ATTACH_ORDER` 保持旧顺序）。roundtrip 全过。

## v0.10 change: 实体内联引用（药品 / 公司 / 临床试验注册号）

- 背景（用户拍板）：整合 Tool Smith 的 `[name](entity:type:id)` 实体内联引用能力，让报告里的药品、公司、注册号渲染成可交互实体胶囊（前端 `EntityAnchor` 已支持，artifact 阅读器走 `ChatMarkdown` → `EntityAnchor`，**前端 0 改动**）。范围限定三类：药品 + 公司 + 注册号；适应症/靶点不做（无元数据行）。
- **ID 来源 = 后端附件元数据行透传**（用户确认），nct_id 也是元数据行优先：新增三行可选元数据 `source_nct_id` / `source_drug_entities` / `source_company_entities`（`名称|实体索引|ID`，`;` 分隔）。行缺失/为空 → 该类型不引用（自然降级）。不编造 ID、不为拿 ID 调工具；注册号仅在 `source_nct_id` 存在时引用（v0.10 不做 CTR/ChiCTR 文本抽取兑底）。
- **数据源核实**（只读）：`base.nct_id.text`（多值时取首个干净 token，NCT 优先）→ `entity:trial:`；`base.trial_drug[].meta[]`（drug_earth，中文药名+ID，如依沃西单抗=12483）→ `entity:drug:`；`trial_details` 内 `company_ids`（仅 ID 数组）→ 用 `base_company` 索引 `terms{id}` 解析显示名（`name_show_cn`→`short_name`→`name`，319=BMS/169=Pfizer/355=Eli Lilly/55=Bayer）→ `entity:company:`。HARMONi-6 记录无 company_ids（自然省略公司行）。
- 证据边界：三行实体元数据是**展示/标签元数据，非临床证据**；只给报告里本来出现的实体名绑 ID，不推临床事实。与 `{{ref_n}}` 共存（`[依沃西单抗](entity:drug:12483){{ref_1}}`）；`::visualization` 图表内不写 `entity:`（隔离 iframe 无实体渲染器，登记号下钻仍走 `__toolsmithNavigate`）。
- 改动文件：新增 `skill/.../references/entity-inline-reference.md`（语法/ID 来源硬规则/适用范围/与证据边界关系/校验）；`references/input-contract.md`（JSON 形状加三字段 + 文件布局加三行 + 读取协议第 4 步实体台账）；`references/citation-and-ref.md`（首段交叉引用）；`SKILL.md`（阅读清单 #10 + Input 段 + 证据边界 + 工作流第 8 步 + Output firewall 允许 `entity:` 受控格式）；三份报告模板（研究名称/注册号、试验组/试验组方案单元格加 `entity:` 示例）；新增 `system-prompts/multi-clinical-result-comparison-v0.10.md`（基于 v0.9，加「Entity inline references」规则表 + 工作流第 8 步 + Final verification 实体校验条款）；`evals/fetch-np-clinical-attachments.mjs`（`_source` 加三字段、`enrichEntityMetadata` 生成三行、renderSourceFile/parseSourceFile/roundtrip 扩展）；新增 `evals/validate-entity-refs.mjs`（报告实体引用 ↔ 附件元数据行一致性校验：类型白名单、ID 必须在元数据、图表内禁 `entity:`）；README（v0.10 段 + 文件清单 + 配置）；重建 `dist/multi-clinical-result-comparison-v0.10.zip`（21 文件 = v0.9 的 20 + entity-inline-reference.md，系统提示词不入 zip）。
- 验证：fetch 脚本 `node --check` OK + 小批量（3 条）实拉——无 ID 旧来源自然省略三行、有 drug_earth 的来源正确输出 `source_drug_entities`；HARMONi-6（NCT05840016）nct_id 提取=可 `NCT05840016`、drugs=卡铂1618/依沃西单抗12483/紫杉醇1738、公司为空（数据本身无）；带 company_ids 的样本（319,169,355,31284,55）经 `base_company` 全部解析出名称；roundtrip 校验全过。`validate-entity-refs.mjs`：编造 ID（NCT99999999 不在元数据）正确 FAIL，真实 ID 正确 PASS；zip 解包 = v0.9 集 + 新参考文档。
- 遗留：前端实体胶囊实际渲染仍待真实部署验证（延续 `{{ref_n}}`/`::visualization` 同款待办）；公司显示名取 `name_show_cn→short_name→name`，可能含非目标拼写，Agent 以来源拼写为展示名（元数据名仅作匹配提示）。

## v0.10 follow-up: iteration-16 数据重拉 + fetch 脚本增强

- 背景（用户）：把 `evals/iteration-16` 里所有 np-clinical 数据目录按 v0.10 新规则（实体元数据行）重新拉取。
- `evals/fetch-np-clinical-attachments.mjs` 增强（同一脚本三种场景）：`NP_CLINICAL_ATTACH_NO_EVALUATION=1`（去掉 evaluation 过滤，供 ind579 这类无 evaluation 批次）；`NP_CLINICAL_ATTACH_NCT="NCT..."`（按注册号拉单试验）；`NP_CLINICAL_ATTACH_ORDER="<doc_id>,..."`（按文档 `_id` 指定输出顺序，复现历史手工选择顺序，保持旧报告 ref 对齐）。`normalizeSource` 携带 `_docId` 用于排序，写入 manifest/文件前删除（`_id` 不泄漏）。`references/input-contract.md` Reproducible local check 段补三种 env 覆盖说明。
- 重拉结果（均为 gitignored 生成物，不入库）：
  - `np-clinical-nsclc-50`：50 条，顺序与旧一致（旧 report.md/refs.json 仍对齐）；实体行 44/50 至少一行（nct 36 / drug 31 / company 21）。
  - `np-clinical-ind579-phase3-50`：59 条（原 50 条前序一致 + 数据源新增 9 条 usable）；实体行 58/59（nct 56 / drug 43 / company 0——AD 试验 np_clinical 无 company_ids）。旧 report.md 对应前 50 条仍对齐；多出的 9 条无报告覆盖。
  - `np-clinical-nct01996267`（TRAIN-2）：5 条，按旧顺序（`NP_CLINICAL_ATTACH_ORDER`）重拉，与旧 report.md 完全对齐；全部带 `source_nct_id: NCT01996267` + drug_earth 药名，company 行 0（记录无 company_ids）。
- roundtrip 校验全部通过；备份旧数据在 `/tmp/iter16-backup/`。

## v0.9 change: 报告文件化交付（present_artifact 终局）

- 背景（用户确认）：利用 Tool Smith 新增 `present_artifact` capability，把最终报告从「聊天正文流式输出」改为「写盘 + 卡片交付」；开发要点：后端不用解析模型输出、可杜绝开场白/尾随 tool、可为交付写文件模板。用户定案：**方案 B**（正文留空/至多一句用途说明，只有卡片）+ **`{{ref_n}}` 与独立引文 JSON 暂不改**（保留标记与 schema，只是 JSON 也变成文件）；气泡/悬停字段说明本轮不做。
- 交付契约（新增 `skill/.../references/file-delivery.md`，权威）：
  - 报告 → `/workspace/output/<slug>-report.md`（路由模板内容 + `{{ref_n}}` + `::visualization` 引用，首行即标题无开场白）；引文 JSON → `/workspace/output/<slug>-citations.json`（raw strict JSON，一源一键，字段 byte-for-byte）。
  - `present_artifact('/workspace/output/<slug>-report.md')` 作为**最后一个 tool call**，成功后立即结束；正文留空或至多一句「完整报告已生成，见下方文件卡片」；调用后不得再输出/再调 tool。
  - 只 present 报告文件；内嵌 `::visualization` 图不再单独 present（除非本身就是独立交付物）。
  - 引文 JSON 文件不 present 也可见：`/workspace/output/` 下的文件都是 workspace artifact（已核实 tool-smith `list_artifacts` 只过滤忽略目录），后端/前端走 artifacts API 直接取两个文件。
  - 若部署未开 `artifact_presentation`（工具不可见），回退 v0.8 契约（正文全量报告 + 独立 JSON）。
- 依赖开关：目标项目须开 `artifact_presentation`（默认 OFF）+ `visualization`（报告文件里的 `::visualization` 渲染依赖）。
- 改动文件：新增 `references/file-delivery.md`；`SKILL.md`（阅读清单 #9 + 工作流第5步写盘 + Output firewall 文件化交付/回退）；新系统提示词 `system-prompts/multi-clinical-result-comparison-v0.9.md`；`references/citation-and-ref.md` 与 `references/input-contract.md` 的 JSON 交付改为文件；`runtime/citation-renderer.mjs` 新增 `validateCitationPair`（不渲染的配对校验）+ `test/citation-renderer.test.mjs` 两条新测试；README v0.9 段落/文件清单/配置；重建 `dist/multi-clinical-result-comparison-v0.9.zip`（20 文件，含 file-delivery.md）。
- 报告模板（unified/cross-trial/mixed）未改动——它们就是报告文件的内容骨架；v0.9 只改了「交付方式」这一层，不改内容结构与图表契约。
- 验证：`node --test test/citation-renderer.test.mjs` 8/8；`node evals/validate-v05-contract.mjs` → `v0.5_contract_ok`；zip 解包结构/前缀/20 文件校验通过。
- 遗留：`{{ref_n}}` 在 artifact 文件阅读器里仍显示为字面 token（前端上标渲染未做，属已知限制，`{{ref_n}}` 不改是用户定案）；正文 `::visualization` 真实环境渲染仍待验证（延续 v0.8 待办）。

## v0.8.1 change: 三张图表模板视觉升级（lieflat violet 紫罗兰设计语言）

- 背景（用户）：现有时间轴/柱状/折线模板不好看，希望按已认可的 ORR 图（violet 横档柱）重做；并确认用了 lieflat skill。
- 三张模板（`templates/charts/`）重写，设计语言 = lieflat-charts **violet 预设**（象牙纸 `#F7F2EB`、墨 `#2B1450`、紫阶 `#2B1450→#55339A→#8A63D2→#C6B3EE`），单色相明度阶、一律实心无渐变阴影、发丝网格、数值标签纸色描边光晕、虚线徽章、全大写来源行、fade/draw 动画 + reduced-motion、确定性 rnd（无 Math.random）。
  - `endpoint-bar.html`：改为**横档柱**（1 格 = 1 单位，档距 ~2.6px，1-2-5 自动步进），**柱深浅 = 数值高低**（明度即数据，12 档紫阶）；`series` 保留为可选显式紫档覆盖（缺省=数值取色）；加 TRACK 打底、nice 网格刻度、悬停 tip（墨紫底）。
  - `endpoint-line.html`：系列默认 = 紫系 SER（研究组最深 `#2B1450`），线宽 ×1.8 实心圆头、纸色光晕数据点 + 800 数值标签、发丝网格 + 虚线动画，保留单点模式。
  - `evidence-timeline.html`：旗帜改**实心**（去掉渐变），图例默认按证据类型取紫系深浅（里程碑 `#C6B3EE`/披露 `#55339A`/更新 `#8A63D2`）；成熟带改实心 TRACK 底 + 纸色圆点描边（去渐变）。
  - 排序规则：柱状图按 value 从高到低自动降序（模板内 sort，无需人工排）；折线/时间轴按时间顺序（数组顺序即时间顺序，模板不重排）。注释与 `chart-templates.md` 数据填充约束同步。
- 契约不变：仍是 Tool Smith HTML fragment（无 `<!doctype`/`<html`/`<head`/`<body` 子串，含注释/脚本）；颜色一律 `var(--viz-*, violet_fallback)` + 模板 JS `viz(name,fb)` 读注入值；`CHART` 数据对象结构不变（`endpoint-bar` 的 `series` 语义改为“可选紫档覆盖”）。
- 系统提示词 `multi-clinical-result-comparison-v0.8.md`：定量图段落补“排序与外观固定”条款（柱形自动降序、折线/时间轴保持时间顺序、内置 violet 编辑设计只填 CHART 不改样式）。
- `references/cross-trial-comparison.md`：Chart rules 补同款排序与外观条款。
- 重建 `dist/multi-clinical-result-comparison-v0.8.zip`（18 文件，前缀正确，含新版 violet 模板 + 排序规则，66KB）。
- 文档同步：`chart-templates.md`（导语/第三节配色/第四节与 lieflat 关系）、`chart-tokens.css`（fallback 改 violet + 明度即数据规则）、模板内注释。`SKILL.md` 契约层描述未改（仍是“只改 CHART”）。

## v0.8.1 follow-up: 脚本填充防复发纪律 + 生成自检

- 背景（用户）：某 Tool Smith 分享页图表渲染失败，错误 `渲染失败：Unexpected token '{'`，怀疑是 violet 模板改动引起。
- 排查结论（与本轮模板无关）：从分享快照拉取 Agent 实际生成的三份 `endpoint-bar` 产物（`nsclc-egfr-3g-tki-pfs` / `nsclc-egfr-tki-combo-pfs` / `nsclc-io-chemo-pfs`），`node --check` 全部报 `Unexpected token '{'`——Agent 临时写的 `gen_charts.py` 用 `tpl[:i] + start_marker + payload` 拼接时，模板自带的 `const CHART = {` 与 `json.dumps` 输出（以 `{` 开头）叠成双 `{`；同时用 json 的 `}` 替换模板 `};` 丢失分号，ASI 把对象与下一行 IIFE 连读成“调用对象”→ 修完语法错误后还会报 `TypeError: … is not a function`。用同一脚本逻辑拼旧模板（349eabc）复现同样双 `{` + 丢 `;`，证明与 violet 重写无关。修复后三图在 Tool Smith 同款沙箱（`--viz-*` 注入 + 隔离 iframe）零错误渲染；修复产物见 `charts/share-fix-preview/`（fragment + 包裹预览 + PNG）。
- 防复发改动：新增可执行校验脚本 `templates/charts/validate-chart.py`（纯 Python，node 可用时额外做真 JS 语法校验）——检测 Tool Smith 禁用子串/结构、双 `{`、缺 `;`、花括号配对、CHART 字段、文件大小，FAIL 时输出行号 + 修复提示，供 Agent 修复后重跑；`references/chart-templates.md` 数据填充约束「5. ⚠️ 脚本批量填充与自检」改为指向该脚本（必跑，FAIL→修复→重跑直到 PASS）；系统提示词 `multi-clinical-result-comparison-v0.8.md` 定量图段落 + Final verification 均改为要求运行 `validate-chart.py`。`SKILL.md` 契约层未改。
- 脚本自测：修复产物 3 份全 PASS；未修复坏文件准确报双 `{`（第 17 行）+ node SyntaxError（第 18 行）；缺分号场景由启发式报“未以 `};` 结尾”（node 不报因语法合法）；`<body` 禁用子串报第 1 行；三模板本体 PASS。
- 重建 `dist/multi-clinical-result-comparison-v0.8.zip`（含更新后的 `chart-templates.md` + `validate-chart.py`，系统提示词不入 zip）。

## v0.8.1 follow-up 2: 时间轴重设计（lieflat L11 语法延伸，去掉旗帜/成熟带矩形）

- 背景（用户）：分享页（share `22a71675…`）时间轴「不知道三角形和长方形都是啥意味」——旧模板的竖矩形（旗面）+ 三角（旗杆）+ 底部横矩形（成熟度带）几何符号语义不明，且长标签/长日期两端溢出被裁（真实产物 TRAIN-2：首标签从 x=46 向左截断、末日期从 x=854 向右截断）。用户询问是否用了 lieflat skill。
- 结论：lieflat 决策树有「事件序列生命史 → L11 Trend Lineage」，为最接近组件；上轮未去 gallery 找对口实现而是沿用旗帜造型，属疏漏。按 lieflat 规则第 3 条（无现成单试验时间轴 → 从 L11 现有语法延伸）重做。
- 新版 `evidence-timeline.html`（仅改渲染区，CHART 结构/契约不变）：
  - 语义：圆点=事件节点（**实心=披露/更新、空心=里程碑锚点**），圆点**直接坐基线**（时间轴即证据链），**圆点大小=证据成熟度**（phase 0..4 → r 6.5..11.3）；数值**横排在圆点右侧**（末节点放左侧防溢出）；无矩形/三角/刻线。
  - 动画：基线 draw（链式展开）、圆点 pop、文本 fade，reduced-motion 全关。
  - 健壮性：标签/日期**自动折行**（按间距算每行字数）+ **端部锚定**（首节点左对齐、末节点右对齐）——彻底解决两端溢出与重叠。
  - 契约不变：fragment（无 `<!doctype`/`<html`/`<head`/`<body` 子串）、`--viz-*` + violet fallback、确定性（无随机）。
- 验证：validate-chart.py PASS；渲染 DOM dump 全坐标在 viewBox 内无溢出无重叠（圆点 y=200 坐线，r 递增，标签 2 行折行正常）；真实 TRAIN-2 数据产物校验 PASS。预览：`charts/timeline-v2-preview/`（产物 + wrapped + PNG）。
- 文档同步：`chart-templates.md`（模板选型表、与 lieflat 关系改为 L11 语法延伸）、`timeline-diagram.md`（phase → 圆点大小递增）。系统提示词无视觉描述，未改。

### v0.8.1 follow-up 2 修订（用户复看："数值不要放在轴上，多整几行，注意对齐"）
- 改 3 点：①数值不再横排在轴线（原 y=204 贴基线 200），改为**纵排多行**在圆点下方（`value` 支持 `\n` 手动分行 + 自动折行，每节点 ≤3 行）；②圆点从"坐基线"改为**悬浮于基线上方**（信息块与轴线分层，数值离开轴线、基线下方为日期）；③对齐：数值首行固定 `dotY+25` 各节点**顶对齐**（修复初版随 r 变化的 160/162/163 错位）、标签**底对齐**贴节点（2 行时 54/69）、日期首行固定 235。
- 坐标（H=270）：标签 54/69 → 圆点 140 → 数值 165/181/197 → 基线 215 → 日期 235/249。校验 PASS；真实 TRAIN-2 产物 v3 + 截图：`charts/timeline-v2-preview/train2-evidence-timeline-v3(.html/-wrapped.html/.png)`。文档两处视觉描述同步（chart-templates.md、timeline-diagram.md）。

### v0.8.1 follow-up 2 修订 2（用户："轴和点之间没有关联性"）→ v4 定稿
- 问题：v3 圆点悬浮于基线上方 75px，与基线上的日期刻度无视觉连接，读起来“飘”。
- v4 定稿：**圆点直接坐回基线**（dotY=baseY=200，点轴一体，关联最强），**数值纵排多行移到圆点上方**（离开轴线，`\n` 分行 ≤3 行），基线下为日期。三块固定槽位顶部对齐：标签 52/67 → 数值 96/112/128 → 圆点 200（坐基线）→ 日期 222/236；H=272。
- 对齐=固定槽位（各节点同一 y），行数不足留白但不歪；端部锚定保留。校验 PASS；真实产物 v4 + 截图：`charts/timeline-v2-preview/train2-evidence-timeline-v4(.html/-wrapped.html/.png)`。文档两处同步。

### v0.8.1 follow-up 2 修订 3（用户："整点丝线连接，现在偏离太远没关联"）→ v5 定稿
- v4 数值悬在圆点上方 47px+ 仅靠脑补归属，加**丝线**：1px muted、opacity .5 细线，从数值块底部（VAL_TOP+(rows-1)*VAL_LH，如 128）连到圆点顶部（dotY-r，189–192 随 r 变，长 61–64px），draw 动画自圆点向上生长；先画（数值文字与圆点盖住线头）；**里程碑无数值不连**，保持空心圆纯净。
- 布局坐标不变（v4 定稿：标签 52/67 → 数值 96/112/128 → 圆点 200 坐线 → 日期 222/236）。校验 PASS；真实产物 v5 + 截图：`charts/timeline-v2-preview/train2-evidence-timeline-v5(.html/-wrapped.html/.png)`。文档两处同步。
- 验证：`node --check` 三个脚本通过；禁用子串 grep 干净；headless Chrome 渲染 violet 色值/横档/旗/线均出；预览包在 `/home/xupeipeioo1/charts/skill-violet-redesign/`（wrapper + PNG）。
- ⚠️ 待办：`::visualization` 正文渲染支持仍未在真实环境验证（延续 v0.8 待办，与开发者对齐时确认）。

## v0.8 change: 图表统一走 HTML 可视化（全面移除 Mermaid）

- 决策（用户明确）：时间轴与跨试验图都不再输出 Mermaid，统一用 `templates/charts/` 的 HTML 模板 + 正文 `::visualization[标题]{path="..."}` 引用（workspace 文件 + 引用通道）。
- `references/timeline-diagram.md` 重写：交付方式改为复制 `evidence-timeline.html` → 只改 `CHART` 数据 → `::visualization` 独占一行引用；**节点语义明确为 events[] 一条=一个证据状态**（同状态多篇披露合并为一节点，`note` 并列 `{{ref_n}}`，不构成独立验证）；保留原规则（数据截止→随访→分析里程碑→披露日期排序、时间未明不猜测、成熟度边界、回退规则=仅 1 个状态或先后不确定时不生成图）。删除 Mermaid 结构模板/示例，改为 TRAIN-2 数据填写示例。
- `references/chart-templates.md`：events[] 语义同步为“一条=一个证据状态”；版本边界改“全部图表随 v0.8 生效、不再输出 Mermaid”。
- `references/cross-trial-comparison.md`：Chart contract 从 Mermaid `xychart-beta` 改为 HTML 模板（单值→`endpoint-bar.html`，时间序列→`endpoint-line.html`）+ `::visualization` 引用。
- 模板 `unified-evidence-report.md` / `mixed-comparison-report.md` / `cross-trial-report.md`、`SKILL.md`、`templates/charts/evidence-timeline.html`（注释）同步更新。
- 新增 `system-prompts/multi-clinical-result-comparison-v0.8.md`（基于 v0.7，时间轴/定量图段改为 HTML；3 处 mermaid 均为禁止性表述“不输出 Mermaid”）。历史 v0.3–v0.7 提示词保留为快照。
- README：v0.8 段 + 文件描述（timeline-diagram 改 HTML、zip 改 v0.8）+ Tool Smith configuration 改 v0.8。
- 重建 `dist/multi-clinical-result-comparison-v0.8.zip`（18 文件，同 v0.7 结构）。
- 示例：TRAIN-2（`evals/iteration-16/np-clinical-nct01996267/`）`report.md` 的 Mermaid 块替换为 `::visualization` 引用；`train2-evidence-timeline.html/.png` 重生成（3 状态+里程碑，每条=一个证据状态）。report 校验：标记双向一致、连续、无 Mermaid 残留。
- 验证：`node evals/validate-v05-contract.mjs` → `v0.5_contract_ok` 保持绿。
- ⚠️ 待办：`::visualization` 在 Tool Smith 正文中的渲染支持尚未在真实环境验证（此前 Mermaid 走渲染器原生渲染）；若正文不支持，需降级为“文字+表格+下载链接”。下次与开发者对齐时确认。
- 修订（路径规范）：Tool Smith 可视化契约要求**绝对路径** `::visualization[标题]{path="/workspace/visualizations/xxx.html"}`，路径必须位于 `/workspace/visualizations/` 下、不能目录穿越或反斜杠、引用前先写入文件、文件名 ASCII。已把 `chart-templates.md`/`timeline-diagram.md`/三个报告模板/`SKILL.md`/`cross-trial-comparison.md`/v0.8 提示词/README 里所有 `path="..."` 相对写法改为绝对路径，`chart-templates.md` 新增“交付路径契约”小节作为统一条款（含 fallback 要求）；TRAIN-2 示例 `report.md` 引用同步改绝对路径。开发端将加相对路径兜底逻辑——与绝对路径契约不冲突，兜底应同时校验 `..`/反斜杠/前缀外路径。
- 修订（fragment 格式）：Tool Smith 对 HTML 可视化用与内联 widget 相同的隔离 fragment 渲染器，**成品必须是 HTML fragment**，不含 `<!doctype html>`/`<html>`/`<head>`/`<body>`/`<meta>`/`<title>` 文档包裹。三个模板（`evidence-timeline.html`/`endpoint-bar.html`/`endpoint-line.html`）与 TRAIN-2 示例已去掉文档包裹改为 fragment；`chart-templates.md` 交付契约新增 fragment 条款，`timeline-diagram.md`/`SKILL.md`/v0.8 提示词/README 同步。本地验证：用 wrapper 包成完整文档经 headless Chrome 渲染，12 个 text 元素正确、PNG 重新生成。
- 修订（分组建图固化）：跨试验/混合报告**按临床问题分组 → 每组各出一张 `endpoint-bar.html` 柱状图**（各组独立 CHART 文件，图内并列该组各试验的试验组结果值，研究内对照数值与证据边界放悬停 note，标题注明「跨试验并列展示≠头对头比较」，不满足可比条件的组不出图）。契约同步：`mixed-comparison-report.md`（第一章「按组绘图」+ 图插入说明 + ORR 说明）、`cross-trial-comparison.md`（Chart contract 补分组建图）、v0.8 系统提示词（120 行定量图规则补每组一图）、`endpoint-bar.html`（数据区注释补多实例分组）、`SKILL.md`（§6 Mixed inputs）、README。示例：NSCLC 10 试验分三组 → nsc-group1/2/3 固化到 `evals/iteration-16/chart-examples/`（含 README）。
- 修订（品牌配色 token 化，前端确认）：图表主色一律引用宿主注入的 `--viz-*` 语义 token（背景/surface/text/text-muted/border/series-1..5/info 等），品牌 hex 仅作为 `var(--viz-*, #hex)` fallback。品牌色：背景 `#f4f5f7`、主文字 `#020A1A`、次文字 `#4e5969`、说明 `#8993a4`、边框 `#DADEE6`。三张模板 + TRAIN-2 示例已删除 `:root` 整套 `--c-*` hex 色板，改用 `var(--viz-*)` + `--brand-*` fallback；模板 JS 加 `viz(name,fb)` 运行时读注入值；`legend`/`series` 的 `color` 可填 token 名或 hex。`chart-tokens.css` 改为 token 唯一来源 + 映射表 + 速查。验证：headless Chrome 注入 `--viz-series-1:#2563eb` 等，渲染后 SVG 全部用注入色（无 fallback 漏出），未注入时 fallback 生效。契约同步：`chart-templates.md` 配色章节、`toolsmith-visualization` skill（reference §4 + SKILL.md 要点 4）、Obsidian 笔记。
- 给开发的兜底建议（已同步到 Obsidian 笔记 `ToolSmith可视化能力与4种画图方式.md`）：① 完整文档剥离（DOMParser 取 body + 前置 head 的 style/script，不改内容）；② 剥离后校验（无嵌套 iframe/无文档标签残留/≤1MiB，超限降级下载）；③ 相对路径兜底 `path="xxx.html"`→`/workspace/visualizations/xxx.html`（同时拒绝 `..`/反斜杠/前缀外）；④ 文件缺失显示占位+保留正文 fallback。边界：不做内容级修复、不绕过路径穿越校验、不执行外部导航。定位：兜底仅兼容 Agent 偶发不规范输出，核心正确性仍由 Agent 按契约负责，不应成为依赖。

## v0.7 change: attachment-based input（每条结果一个附件文件）

- 背景：原设计把选中的结果以内联 JSON 放进单条 message，用户勾选 20–50 条时容易超上下文。改为：每条结果写成单独 `.md` 附件（`source-001.md`…），随用户消息一起作为附件送达；Agent 按文件名顺序读 `/workspace/uploads/` 下每个附件，`{{ref_n}}` 按文件顺序分配。
- 单文件格式：`# 临床结果来源 {n}` + 三行元数据（`source_title:`/`source_url:`/`source_paper_release_time_str:`）+ `## source_full_text` 标题 + 全文正文。文件名顺序=输入顺序=ref 顺序（仅展示标签，非临床时序）。
- 附件限制（Tool Smith）：每消息 ≤10 文件、每线程 ≤100、单文件 ≤20 MiB；超出时拆分消息/线程，Agent 不假定固定数量。
- 改动文件：`references/input-contract.md`（重写：单文件布局/附件限制/Agent 读取协议/后端 manifest）；`references/input-and-extraction.md`（开头改附件读取）；`SKILL.md`（新增 Input 章节+证据边界措辞）；新增 `system-prompts/multi-clinical-result-comparison-v0.7.md`；README 同步；重建 `dist/multi-clinical-result-comparison-v0.7.zip`（18 文件，含 charts 模板）。
- 新增 `evals/fetch-np-clinical-attachments.mjs`：按条件从 `np_clinical` 拉取并写每源一个附件文件 + `manifest.json`（后端日志用），内置往返校验。默认条件=非小细胞肺癌（indications 135/5718/5719）+ 三期 + 积极。
- 真实测试：拉取 `evals/iteration-16/np-clinical-nsclc-50/`（50 条，条件命中 890 条）；50 个 `.md` + manifest；元数据完整度 title 50/50、url 49/50、time 50/50、空正文 0；Agent 视角对账（读文件→建 ref 台账→比对 manifest）50/50 一致。
- ⚠️ 数据事实修正：此前 NASH 示例用的 indications 516/517 其实是「非酒精性脂肪肝/非酒精性脂肪性肝炎」，不是非小细胞肺癌；ORR 属实体瘤终点，NASH 数据里不存在。本次已查实真实 ID：非小细胞肺癌=135、鳞状非小=5718、非鳞状非小=5719。
- ORR 柱状图实测：50 条中 30 条含 ORR/缓解率；取 3 个一线晚期 NSCLC 随机 III 期研究（CATAPULT I：27.5% vs 13.7%；E4599：35% vs 15%；nab-紫杉醇+卡铂 vs 溶剂型：33% vs 25%）注入 `templates/charts/endpoint-bar.html` 生成 `evals/iteration-16/chart-examples/orr-bar.html/.png`（真实数据，含跨试验可比性提示）。
- ⚠️ 柱状图模板修复（用户反馈）：① 数值刻度原本画在左侧与组别标签重叠 → 改为底部横轴（标准横向柱状图）；② 行高自适应（≤62px，行多时压到 ≥30px）；③ 行密时（rowH<42）组别字号缩到 11、左栏加宽到 224，杜绝长标签越出画布；④ 行密时（rowH<46）隐藏柱端 CI 副行避免串行。实测 51 行全量 ORR（24 个试验）：程序化 getBBox 测量 非同行重叠 0、越出画布 0。

## v0.6 change: evidence-chain timeline diagram

- Added `skill/multi-clinical-result-comparison/references/timeline-diagram.md`: construction rules for a descriptive Mermaid evidence-chain timeline.
- Scope: same-trial inputs only, when consolidation leaves ≥2 genuinely distinct evidence states. Cross-trial/mixed inputs do not get a shared timeline.
- Delivery: a Mermaid fenced code block placed directly above the timeline table in the 证据链总览与时间线 section. Mermaid is rendered natively by the Tool Smith Markdown renderer; it does not use `read_me`/`show_widget`/workspace files and does not require the inline-visualization capability.
- Diagram carries: source-supported chronology (data cutoff → follow-up → analysis milestone → disclosure date; never input order), one node per evidence state (analysis stage/disclosure form + this state's key new content + `{{ref_n}}` markers), a time axis (时间未明 when missing, never guessed), dotted time-to-state links, and a labeled relationship + maturity-direction arrow between consecutive states (更新/新增终点/确认/补充/取代/冲突/不确定 + 加强/基本不变/限定/削弱/无法确定).
- It is descriptive/chronological, not a quantitative series, so it does not require numeric compatibility. It never replaces the exact-value timeline table.
- Fallback: only 1 distinct state or undeterminable order → omit the diagram and state the order uncertainty in the table.
- Updated `SKILL.md` (read list + workflow step 5 + chart rule), `references/same-trial-evolution.md` (new Step 8), `templates/unified-evidence-report.md` (section 三 timeline insertion), `system-prompts/multi-clinical-result-comparison-v0.6.md` (new v0.6 prompt with the timeline rule), and `README.md`.
- Rebuilt `dist/multi-clinical-result-comparison-v0.6.zip` (13 files incl. `references/timeline-diagram.md`).
- Example: `evals/iteration-15/harmoni6-timeline/report.md` + `report.refs.json` — HARMONi-6 4-source/2-state report with the Mermaid timeline inserted. Verified: marker/key parity 4/4, citation keys == fixture count, fixture title/link/release-time parity, no forbidden implementation terms, no unresolved placeholders, Mermaid block bracket/quote balance OK. Mermaid v11.15.0 (bundled via `@streamdown/mermaid`) fully supports the used syntax (`flowchart`, quoted subgraph titles, `direction`, `-.-`, `<br/>`, quoted edge labels).
- Validation note: this workspace cannot run the Tool Smith cloud Benchmark or the actual frontend Mermaid render; validation is local static contract + syntax review.

## Chart templates (v0.7 direction): 蓝紫色系 HTML 图表

- Created `skill/multi-clinical-result-comparison/templates/charts/` with 3 single-file HTML chart templates (pure SVG/CSS/vanilla JS, no external deps → offline + Tool Smith sandbox ready):
  - `evidence-timeline.html` — same-trial 证据链时间轴（旗帜 + 时间轴基线 + 证据链成熟度渐变带，hover 提示；events 按证据披露时间先后排列）。
  - `endpoint-bar.html` — 混合/不同试验、无时间维终点（ORR 类）横向柱状图（轨道+主柱+高光、值+CI、hover）。
  - `endpoint-line.html` — 混合/不同试验、时间维终点（体重类）折线图；全部系列仅 1 个点 → 自动单点模式（只画点+值，不强行连线）。
- `chart-tokens.css`：蓝紫色系基准（靛蓝 #4f46e5 → 紫罗兰 #7c3aed → 紫 #a855f7；系列色 --c-s1..s6；语义用明度区分，不用红绿）。全部抽成 CSS 变量，模板内联；底部附 `--viz-*` 注入映射表，接宿主主题时整体替换 :root 即可，图代码不改。
- `references/chart-templates.md`：选型规则（同试验→时间轴；无时间维→柱状；有时间维→折线）、填数约束（仅 source_full_text、不推断阶段/顺序）、交付方式（workspace 文件 + `::visualization` 引用，图前后保留文字）、与 lieflat-charts 的关系。
- 验证：三模板 JS 语法 `node --check` 全过；headless Chrome 渲染出 PNG（36/32/30KB）；DOM 校验 svg/rect/circle/text 数量与代码预期一致、标题均注入成功。
- 版本边界：同试验时间轴随 v0.6；柱状/折线（定量图）供混合场景，计划随 v0.7 放开；`dist/` 未重建（待用户定夺是否并入 v0.7 后重建）。
- 相关安装：从 GitHub 拉了 `lieflat-charts`（64 图型，`~/.agents/skills/lieflat-charts`）供 fancy 图扩展；新建参考型 SKILL `toolsmith-visualization`（`~/.agents/skills/toolsmith-visualization`，沉淀 4 方式/2 通道/主题 token/下钻结论，均已在 Obsidian 笔记 `ToolSmith可视化能力与4种画图方式.md` 记录）。
- 示例成品（真实数据）：`evals/iteration-16/chart-examples/` 下 3 份 HTML + 渲染 PNG，用注入方式生成（模板代码不动、只换 `CHART` 数据）；**v0.15 已删除 HTML，仅存 PNG**：
  - `harmoni6-evidence-timeline.html/.png` —— HARMONi-6 4 来源→2 状态（PFS 核心分析 2025-10 披露、OS 核心分析 2026-05 披露）+ 研究启动里程碑；PFS 11.1 vs 6.9 月（HR 0.60）、OS 27.9 vs 23.7 月（HR 0.66），披露时间取自 refs.json。
  - `harmoni6-pfs-bar.html/.png` —— HARMONi-6 中位 PFS 按治疗组（11.1 vs 6.9 月 + 95%CI）。注明 HARMONi-6 未报告 ORR，以中位 PFS 单值演示柱状模板。
  - `mazdutide-weight-line.html/.png` —— 折线模板演示：HARMONi-6 无时间维重复测量终点，改用真实 obesity fixture 的马扎度肽 2b 期数据（4mg/6mg/安慰剂，W32/W48 体重变化 %：-10.09/-12.55/+0.45 → -11.00/-14.01/+0.30），已在副标题注明。
  - 校验：JS 语法 OK；headless Chrome 渲染 PNG（38/29/29KB）；DOM 校验关键数值（11.1/6.9、27.9/23.7、-10.09/-12.55/-14.01/+0.45/+0.30）全部注入成功。

## Confirmed decisions

- Users include medical intelligence, clinical development, and BD/investment teams; all receive the same report granularity.
- Version 1 compares only selected records and performs no external retrieval.
- The backend resolves selected records from the POC Elasticsearch environment and `np_clinical`, then sends `source_title`, `source_url`, `source_paper_release_time_str`, and `source_full_text` to the Agent. Runtime correlation IDs remain outside the Agent request and report.
- The frontend/backend enforce a conservative real-time token budget.
- The primary analysis object is the underlying trial. Multiple disclosures from one trial are source nodes that form a longitudinal evidence chain; repeated cutoffs and analyses are deduplicated.
- Different trials receive a comparison-first, domain-aligned cross-trial report: efficacy, safety, PK/PD, and PRO are aligned across trials so the user can judge which treatment is better or worse, with explicit comparability/evidence-strength labels and compact per-trial context; no pooling or fabricated head-to-head proof. Trial narratives are supporting context, not the primary structure. Synced into `system-prompts/multi-clinical-result-comparison-v0.5.md` (opening, required workflow step 8, and “Mixed or different-trial inputs”).
- Every material number and source-dependent conclusion in the report carries an internal citation token for frontend rendering; user-facing output shows numeric superscripts. Citation metadata is a separate strict JSON artifact, not part of the report body, and each ref includes `title`, `link`, and `paper_release_time_str`.
- Trial-level reports integrate design, population, regimen, primary and key secondary endpoints, response/durability when reported, subgroups, safety, evidence maturity, and information gaps.
- The finished report must not expose technical correlation keys, database/index names, retrieval traces, internal field names, or implementation terms such as `result_id`, `doc_id`, ES/Elasticsearch, `np_result`, or `source_full_text`.
- Visible labels use a source-supported study short name or name for different studies. Multiple disclosures from one study add a data cutoff/disclosure date or, when unavailable, follow-up plus endpoint/analysis scope. Generic labels such as “材料 1” are last-resort fallbacks; “证据 A/B/C” are not used when a readable source-supported label exists.
- Every cross-trial or mixed report includes a research-key-information alignment table and an experimental-arm endpoint table.
- The frontend/backend enforce a conservative real-time token budget.
- Within-trial controls and comparative effects remain tied to their original randomized comparison and are never converted into cross-trial claims.
- Same-trial reports begin with an evidence relationship overview that separately classifies disclosure form and analysis stage/scope, then explains duplicate/update/subgroup/final/interim relationships before endpoint evolution.
- Cross-trial reports begin with a core-endpoint snapshot per clinical-question cluster. The snapshot always includes an exact-value table; compatible ORR-like endpoints may additionally use a valid Mermaid bar chart, while weight-change line charts require the same explicit time-point grid across plotted series. Missing values, incompatible definitions, or unexpressible time structures trigger a table fallback. Charts are descriptive only: no interpolation, pooling, ranking, or head-to-head inference.
- Cross-trial reports use one global marker namespace in input order and one shared separate citation JSON artifact for the complete response. Markers do not restart at each trial boundary. Separate independently requested reports may use separate local namespaces.
- The citation renderer supports multiple trial sections, accepts a separate citation JSON object, validates marker/key parity, and makes only the numeric superscript clickable. Generic Markdown autolinking must not receive the citation JSON.

## 50 试验跨试验跑批（2026-08-24）
- 输入：`evals/iteration-16/np-clinical-nsclc-50/`（50 个 NSCLC 随机试验 source，2000–2013，gitignored 示例）。
- 用当前 v0.8 skill 契约跑：按临床问题分 7 组（组A 一线化疗 ORR / 组B 一线抗血管 ORR / 组C 一线 EGFR TKI 中位PFS / 组D 二线 ORR / 组E 维持 PFS / 组F 辅助 5年OS / 组G 放疗不可比不出图），每组一图（endpoint-bar）。
- 产出：`np-clinical-nsclc-50/report.md`（跨试验报告，每组表格+`::visualization`+可比性说明，{{ref_n}} 追踪）、`report.refs.json`（ref_1..50）、`charts/nsclc50-group-*.html/.png`（6 张图，fragment 校验全 OK）。
- 关键结论：EGFR 突变一线 TKI 较化疗 PFS 方向一致且显著；含铂双药方向普遍优于单药/非铂；二线无综合胜者（TKI 人群富集 ORR 高不可跨类别解读）；维持各研究内均 PFS 获益。
- 子代理并行提取（5×10 文件，JSON 到 /tmp/nsclc50-extract/），抽查关键原文核对无偏差。

## 特应性皮炎 50 条跑批（2026-08-24）
- 用户给定新 query（indications.id=579 + trial_phase.id=9567bdf8567c48c3b5368659e63b12f7 + 排除删除）拉 np_clinical：total=100，拉 50 条 usable。
- id 579 = 特应性皮炎（非肿瘤），2013–2024，生物/JAK 时代；与 NSCLC 批次不同，重复披露多（OLE/亚组/PRO/特殊人群），主结果仅 7 条。
- 输出：`evals/iteration-16/np-clinical-ind579-phase3-50/`（manifest + source-001..050 + report.md + report.refs.json + charts/ 3 张 EASI-75 柱状图）。
- 分组按靶点通路：组A dupilumab/IL-4R、组B IL-13 单抗、组C 口服 JAK、组D 外用（不出图）、组E nemolizumab（瘙痒终点不出图）、组G 传统/基础（不出图）。同主试验多披露合并（PRESCHOOL/PED-OLE/JP01/AD3/AD7/EXTEND）为一个证据状态。
- 拉取脚本：`/tmp/fetch-np-user-query.mjs`（可复用，接 query 拉任意条件）；子代理 5×10 提取到 /tmp/ind579-extract/。

## 时间维度优先折线图契约（2026-08-24 用户确认，v0.8 修订）
- **触发**：AD 批次首版交付全用柱状图（横截面 16 周 EASI-75），用户指出时间维度（OLE 长期随访/多时点）才是这批核心，应优先用折线图。
- **硬规则（固化进 skill）**：先判时间维度再判横截面——同一研究+同一队列+同一终点 ≥2 个已披露时点（OLE 延展、多时点、停药复发）→ 优先 `endpoint-line.html` 折线图（series=队列、points=已披露时点）；只连线同研究/同队列/同终点，**不跨研究/不跨队列/不跨人群连线**；不插值/补点/外推；单时点披露用单点模式；无对照单臂（婴幼儿外用药等）也可画折线但注明「单臂无对照，仅描述随时间变化」。横截面单值终点（ORR/EASI-75 单时点应答率）才用 `endpoint-bar.html` 柱状图，作组间对照补充。
- **同步文件**：`SKILL.md`（§6 时间维度优先 + Required distinction「同队列时间过程 vs 跨试验横截面快照」）、`references/chart-templates.md`（选型表 + 新增「时间维度优先判定」小节）、`references/cross-trial-comparison.md`（Chart contract time-dimension-first 条款）、`references/same-trial-evolution.md`（区分定量时点折线图 vs 证据链时间轴）、`templates/mixed-comparison-report.md`、`templates/cross-trial-report.md`、`system-prompts/multi-clinical-result-comparison-v0.8.md`（120 行补时间维度优先条款）。dist zip 重建（18 文件字节一致）、`validate-v05-contract.mjs` green。
- **AD 交付重写**：`np-clinical-ind579-phase3-50/` 新增 4 张时间维度折线图——`ad-line-baricitinib-breeze-ad3-ole`（4mg/2mg EASI-75 W16→W68）、`ad-line-delgocitinib-infant-measi`（mEASI 变化 W4/28/52 单臂）、`ad-line-difamilast-infant`（EASI-75/IGA W1→W4→中期单臂）、`ad-line-nemolizumab-ole`（W68 单点模式）；report.md 重写为「时间维度折线（主线）→ 横截面 EASI-75 柱状（组间对照补充）」结构，共 7 图；全部 DOM 验证 + fragment 校验 OK。

## Pending verification (next week, with Tool Smith developer)

- **Input delivery (batch-2 待问 ④⑤)**: 20–50 附件跨消息投递——前端是否自动拆成 10/条？跨消息附件是否全部进 `/workspace/uploads/` 且主 Agent 一次 run 都能读到？50 个全文真实读取的 token 实测（读全是否顶爆上下文；缓解：按需读 / 只读元数据 / 子代理分包）。
- **Subagent 机制（已核查代码，2026-09-10）**: Tool Smith 后端支持且**本项目部署已开启开关**——`schemas/capabilities.py` `subagents: bool = False`（项目级默认关，用户已手动打开）；主 Agent 有 `task` 工具（参数仅 `subagent_type`+`description`，仅有 `general-purpose` 一种，自包含、无状态、只回最终结果）；子代理由同一 `create_chat_agent()` 工厂构造，因此继承默认能力集（**含 params MCP 工具**、`load_skill`、文件系统、代码执行）并共享同一文件系统/凭证/额度；递归深度 `max_recursive_depth=2`（主→子→孙，本 Skill 自身收紧为 1 层）。**已确认**：多 `task` 并发**不生效**——全仓无 `allow_concurrent_tool_calls`，pydantic-ai 默认串行（平台工具描述写「concurrently」与实际不符，可报给后端）；且 `agent.py:65-75` 在 `recursive_depth > 0` 时把系统提示词换成通用子代理提示词，**子代理看不到项目 sys / Skill 正文**（它仍能 `load_skill`，但委派 `description` 必须自带完整抽取规格）。
- **Subagent 策略已写入 sys + SKILL（v0.15，已去待验证标注）**: `references/input-contract.md` 的「Large-batch delegation via subagents (OPTIONAL)」章节 + `SKILL.md` Input 段指针 + sys v0.15 新增 `## Subagent delegation` 段。规则：>5 esid 且 `task` 可见才用、≤5/块按输入顺序均衡切分、一块一 `task`、`description` 完全自包含、只回带 source marker 的紧凑摘要、`{{ref_n}}` 仍按输入 esid 全局分配、串行执行预期、只许一层嵌套、`task` 缺失或 chunk 失败则回退直读且**绝不因此跳过任何来源**。仍未实测：6–20 esid 下的端到端 token/耗时收益，所以仍为 opt-in（不作为提速手段）。

## Validation completed

- Tool Smith `validate_skill_md` accepted the Skill name and description.
- Ran the Skill locally against the condition-based fixture `np-clinical-indications-516-517-phase-featured-false.json`: generated `evals/iteration-14/condition-example/report.md` (4-trial mixed input: ESSENCE, MAESTRO-NASH, MAESTRO-NAFLD-1/OLE, SYNCHRONIZE-MASLD) and `report.refs.json`. Per user feedback the report was restructured to be comparison-first and domain-aligned (efficacy, safety, PK/PD, PRO) rather than trial-by-trial narratives; the Skill routing, `cross-trial-comparison.md`, `cross-trial-report.md`, and SKILL step 6 were updated accordingly. Marker/key parity 10/10, renderer tests 6/6, contract validation `v0.5_contract_ok`.
- The upload archive contains the expected root directory and nine Skill files.
- PWS heterogeneous cross-trial/mixed case: passed after removing cross-cluster rankings.
- HARMONi-6 same-trial evolution case: passed chronology and duplicate-disclosure checks.
- Adversarial/incomplete case: passed prompt-injection, missing-data, and no-soft-ranking checks.

## Iteration 13 HARMONi-6 v0.5 regression report

- Generated `evals/iteration-13/harmoni6/report.md` from the four selected HARMONi-6 source objects using the v0.5 prompt, Skill, required references, and unified evidence template.
- Consolidated the disclosures into one trial narrative with one PFS core state and one 2026-02-27 OS core state; repeated PFS and OS analyses are treated as duplicate or complementary reporting rather than independent validation.
- Preserved source-supplied proper names, retained OS as a first planned/interim analysis, and traced material numbers and source-dependent conclusions with `{{ref_1}}` through `{{ref_4}}`.
- Verification covers inline-marker/JSON key parity, strict separate JSON parsing, exact fixture title/link/release-time parity, unresolved placeholders, prohibited internal fields, and absence of citation metadata from the report body.
- The project root has no Git metadata or Docker configuration, so commit, push, image build, and registry push are not applicable.

## Current revision

- Reviewer feedback identified that the prior example lacked a clear endpoint alignment surface.
- v0.2 replaces default pairwise comparability matrices with a row-oriented experimental-arm endpoint table.
- Experimental-arm observations and within-study control/effect estimates are now separate fields; neither may be inferred from the other.

## v0.3 revision

- A reviewed therapeutic-area landscape article showed that users need more than study-by-study extraction: they need baseline comparability, endpoint-family scanning, complete-response or threshold outcomes, placebo/reference behavior, and a bounded development interpretation.
- v0.3 adds these as reusable output structures without importing the article's CSU facts or conclusions.

## v0.3 to C revision

- Changed the output boundary for the to C report: technical identifiers, ES/database retrieval details, internal field names, runtime terms, and implementation traces are prohibited in final Markdown.
- Removed technical identifier columns and references from all three report templates while retaining readable evidence labels for user-facing comparison.
- Added the to C evidence relationship overview and core-endpoint chart modules to the v0.3 prompt, Skill references, and report templates.
- The final report is now a single consumer-facing evidence synthesis. Internal relationship classification still distinguishes evidence evolution from endpoint alignment, but the report no longer exposes separate same-trial, cross-trial, or mixed report paths.
- The unified runtime template is `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`. It organizes the visible output by core findings, evidence relationships, time course, endpoints, comparability, maturity, and information gaps.
- The chart contract was tightened for Tool Smith Markdown rendering: Mermaid is conditional, uses quoted labels and numeric-only arrays, and is omitted entirely when any value is missing or the time-point structure cannot be represented without interpolation. Every chart is accompanied by an exact-value table and a comparability note.
- The upload archive was regenerated after the updated Skill, reference rules, templates, and system prompt passed validation.

## v0.4 direction reset: trial-level synthesis

- Reframed the primary analysis object from disclosure-to-disclosure comparison to the underlying clinical trial.
- Multiple disclosures from one trial are now source nodes. The runtime must consolidate repeated cutoffs and analyses into one evidence state, preserve genuinely new endpoint/follow-up states, and explain the whole trial across design, efficacy, safety, maturity, and information gaps.
- Added `references/citation-and-ref.md`: stable presentation labels `[Ref n]` are assigned per selected source, every material number and source-dependent conclusion requires an adjacent Ref, and the final `来源索引` maps all selected sources to their contributions.
- Replaced the unified report template with a trial-level structure: clinical question, design, evidence-state timeline, integrated efficacy chain, safety chain, maturity/contradictions/gaps, whole-trial interpretation, and source index.
- Retained limited different-trial alignment only after each trial receives a complete synthesis; no global ranking replaces the trial narrative.
- Updated the same-trial reference to treat disclosures as evidence nodes and states, and updated mode routing so same-trial synthesis is the default visible behavior.
- Added v0.4 system prompt and revised benchmark expectations for trial identity, state deduplication, chronology, inline Ref coverage, and complete-trial interpretation.

## v0.5 linked-source input revision

- Added `references/input-contract.md` documenting the POC configuration, `np_clinical` lookup, normalized Agent payload, absolute URL policy, and frontend superscript rendering.
- Added `evals/fetch-np-clinical-sources.mjs`, a read-only reference adapter that imports the POC config and requests `base.title`, `base.full_article_link`, `source_full_text`, plus `base.paper_title` for the observed title-shape fallback.
- Added `evals/fetch-np-clinical-by-condition.mjs`, which reproduces the requested indication/phase/evaluation/NCT/deletion/featured filter and writes a normalized 10-source example to `evals/fixtures/np-clinical-indications-516-517-phase-featured-false.json`. The query matched 12 records and returned 10 usable full-text sources.
- Pulled `NCT05840016` successfully: 4 HARMONi-6 disclosures with source text lengths 3294, 3587, 2936, and 3067 characters. The fixture preserves exact backend URLs and contains no internal record IDs.
- Updated the v0.5 prompt, Skill, extraction rules, template, README, fixtures, and renderer to use `source_title/source_url/source_paper_release_time_str/source_full_text`, internal `{{ref_n}}` rendering tokens, and a separate strict citation JSON artifact.
- The v0.5 HARMONi-6 fixture preserves four backend-supplied titles and exact URLs, including the ESMO query string. It contains no runtime result IDs.
- Updated the PWS fixture with five read-only `np_clinical` title/URL/release-time pairs. Updated the synthetic adversarial fixture to the same four-field shape with intentionally empty links and release times rather than invented metadata.
- Added `runtime/citation-renderer.mjs` and `test/citation-renderer.test.mjs`: parse the separate citation JSON, enforce marker/key parity, preserve release-time metadata, and safely render valid HTTP(S) links as numeric superscripts with escaped attributes.
- Added explicit cross-trial rules: marker numbering is global for one mixed response and the separate citation JSON is shared; numbering resets only for separately requested reports. A cross-trial comparison claim must cite the source markers for both trials.
- Added the standalone example citation artifact `evals/iteration-13/harmoni6/report.refs.json`; the Markdown report no longer contains a citation section.
- Updated the HARMONi-6 example evidence scope to state `2 份期刊摘要、2 份会议摘要`; the report no longer explains `{{ref_n}}` in visible prose.
- Citation output uses no JSON. The final section is a strict two-line-per-source numbered list: `n. exact title` followed by three spaces and the exact URL.
- Runtime test suite passes 6/6; `node evals/validate-v05-contract.mjs` returns `v0.5_contract_ok`.
- Rebuilt and extracted `dist/multi-clinical-result-comparison-v0.5.zip` with the correct Skill `references/` and `templates/` directory structure; archive contains 13 files.
- Tool Smith cloud Benchmark and actual frontend superscript rendering remain unavailable in this workspace and were not run.
- No Git metadata or Docker configuration is present at the project root; commit, push, image build, and registry push are inapplicable. The POC repository remains dirty with unrelated pre-existing work and was not modified.

## v0.4 verification status

- Static contract review completed for prompt, Skill, support references, template, README, and eval definitions.
- Local v0.4 execution completed against `evals/fixtures/harmoni6-selected-results.json` using the Skill and system prompt: [first run](evals/iteration-12/harmoni6/report.md) and [corrected rerun](evals/iteration-12/harmoni6/report-v2.md).
- The first run exposed a provenance bug: the model invented an unsupported Chinese translation for the source-only drug name `ivonescimab`. Added an explicit proper-name fidelity rule to the system prompt, Skill, and extraction reference: preserve source spelling unless the source itself supplies a Chinese equivalent.
- Corrected rerun passed the trial-level checks: one HARMONi-6 narrative, one PFS state, one OS state, duplicate-source handling, chronology, all four Refs in the source index, inline numeric citations, no internal identifiers, and no unresolved placeholders. It retained `ivonescimab`, `tislelizumab`, `paclitaxel`, and `carboplatin` exactly as supplied.
- `evals/evals.json` now includes the proper-name fidelity assertion. Rebuilt `dist/multi-clinical-result-comparison-v0.4.zip` after the Skill change.
- No Git metadata or Docker configuration is present at the project root; commit, push, image build, and registry push remain inapplicable.

- Regenerated `evals/iteration-10/harmoni6/unified/report.md` from the current v0.3 Skill, system prompt, unified template, and required reference rules using only the four selected HARMONi-6 result texts.
- Replaced generic letter labels with stable source-supported disclosure labels based on HARMONi-6, explicit data cutoff where available, and PFS/OS/safety or analysis scope.
- Deduplicated the four disclosures into one PFS core analysis state and one 2026-02-27 OS core analysis state while preserving disclosure-specific PD-L1 subgroup, baseline anatomy, testing procedure, event-count, and safety details.
- Preserved uncertainty around the undated first planned PFS disclosure: its repeated overall PFS values were deduplicated, but no chronology or shared data cutoff was inferred.
- Kept OS as a prespecified interim/first planned analysis rather than a final analysis, including the 204-event trigger versus the approximately 225-event plan and the non-estimable upper confidence limits.
- No chart was emitted because PFS and OS are incompatible endpoint/time structures and plotting repeated disclosures would double-count the same analyses.
- Manual fidelity review confirmed all four selected disclosures are represented and key PFS, OS, subgroup, event-count, denominator, and safety values match the supplied texts.
- The report contains no generic “证据 A/B/C” labels, internal correlation keys, implementation/storage terminology, template placeholders, or Mermaid blocks.
- Current project state indicates no Git metadata or Docker configuration at the project root, so no commit, push, image build, or registry push was applicable.

## Iteration 10 PWS unified report

- Regenerated `evals/iteration-10/pws/unified/report.md` from the current v0.3 Skill, system prompt, unified template, and required reference rules using only the five selected PWS result texts.
- Replaced generic letter labels with stable source-supported labels: C601/C602 disclosures are distinguished by follow-up and analysis scope; independent studies use registry identifiers or a source-supported descriptive study name.
- Kept body composition, infant growth/development, eating/behavior, and long-term glycemic safety as separate clinical questions within one report. C601/C602 body-composition and glycemic disclosures are treated as complementary analyses, not independent confirmation.
- No chart was emitted because no clinical-question cluster had compatible complete numeric series. Exact-value snapshot tables, study alignment, baseline comparability, endpoint alignment, endpoint-family maturity, safety interpretation, and information gaps were retained.
- Manual fidelity review confirmed all five selected items are represented; key values match the supplied texts; the source's week-64 versus 3-year discrepancy, week-156 HbA1c wording discrepancy, adult LMI formatting anomaly, and unresolved percentage denominators remain explicitly bounded.
- The output contains no generic “证据 A/B/C” labels, internal correlation keys, implementation/storage terminology, or Mermaid blocks.
- No Git metadata or Docker configuration was present at the project root, so no commit, push, image build, or registry push was applicable.

## Iteration 9 unified report

- Replaced visible mode-specific report routing with one runtime template: `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`.
- Internal relationship detection remains available for deduplication, chronology, endpoint alignment, and comparability, but the final report is organized as one evidence synthesis around core findings, evidence relationships, time course, endpoints, comparability, maturity, and information gaps.
- Regenerated unified PWS and HARMONi-6 examples under `evals/iteration-9/`; both passed scans for internal identifiers, implementation terminology, forbidden path labels, and invalid Mermaid output.

## Iteration 8 examples

- Regenerated `evals/iteration-8/pws/with-skill/report.md` from the current v0.3 assets. It separates body composition, development, hyperphagia/behavior, and long-term glycemic safety; all chart candidates correctly fell back to exact-value tables because the supplied evidence was incomplete or incompatible.
- Regenerated `evals/iteration-8/harmoni6/with-skill/report.md` from the current v0.3 assets. It groups duplicate PFS and OS disclosures into two analysis states, orders them by cutoff/follow-up, and preserves the interim-not-final OS boundary.
- Both reports passed scans for internal identifiers, retrieval/storage terminology, and invalid Mermaid output. These are independent local generations from the fixtures, not production Tool Smith Benchmark runs.

- Queried `np_result_3` directly with the selected 16 `doc_id` values and preserved `deleted`/`is_delete` exclusions.
- Retrieved 17 non-empty `source_full_text` values; `38912654` contains Trial 1 and Trial 2, so 16 documents yield 17 result items.
- Added `evals/fixtures/obesity-results-es-source-full-text.json` and the reproducible fetcher `evals/fetch-obesity-es-fixture.mjs`.
- Added `evals/iteration-7/obesity-results-es-source-full-text-report.md`, which separates adult weight management, T2D/prediabetes, pediatric obesity, and OSA questions before limited vertical alignment.
- Marked `35658024`/`39536238` as the same SURMOUNT-1 trial and `38912654` Study 1/Study 2 as two trials in one disclosure.

## v0.13 quick-comparison rebuild (2026-09-07) — ABANDONED in v0.14, kept for reference only

- Reframed the default product from full trial synthesis to a fast comparison brief: one MCP pull, one digest, one compact alignment table, one main chart at most, short interpretation and gaps.
- Added `skill/multi-clinical-result-comparison/templates/quick-comparison-report.md`.
- Added `system-prompts/multi-clinical-result-comparison-v0.13.md`; v0.12 remains the historical deep-synthesis prompt.
- Retained strict selected-fields input, citation parity, duplicate handling, no inference/pooling, safety boundaries, entity provenance, chart validation, TEMP preview dual-write, and `present_artifact` delivery.
- Verification: Python syntax checks pass; all three JSON chart skeletons pass `validate-chart.py`; v0.13 archive contains 22 runtime Skill files, including the quick-comparison template and the same-trial evidence timeline assets.

## Preview renderer visual refresh (2026-09-08) — renderer archived in v0.14 then deleted in v0.15 (was `docs/legacy-html-charts/render-preview.py`)

- Refined `templates/charts/render-preview.py` without changing the JSON protocol or Tool Smith fragment contract.
- Replaced the monochrome violet debug styling with a neutral paper/white surface, ink typography, teal/coral/blue/gold series palette, restrained border/shadow treatment, clearer source footer, and responsive mobile spacing.
- Improved badge, legend, tooltip and chart-stage hierarchy; preserved hover tooltips and host `--viz-*` token overrides.
- Chrome desktop/mobile screenshots were generated for bar, line, and timeline previews; all three renderers emitted non-empty PNGs without wrapper-fragment validation errors.
- Rebuilt `dist/multi-clinical-result-comparison-v0.13.zip` after the renderer update.

## v0.13 timeline condition correction — applies to the abandoned v0.13 line only

- The evidence-chain timeline is generated only when **all usable selected records belong to one trial** and there are at least two distinct evidence states.
- Mixed-trial inputs do not receive the default timeline, even when some records are repeated disclosures from the same trial.
- Rebuilt `dist/multi-clinical-result-comparison-v0.13.zip`; current SHA-256: `445d7335f0d503c60fd3da6950015915fbb36f0d883360d03e971ec25462e7f3`.
