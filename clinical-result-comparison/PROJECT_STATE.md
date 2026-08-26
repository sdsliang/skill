# Project State

## Repository

- Git repository: `git@github.com:sdsliang/skill.git`
- Project subdirectory: `clinical-result-comparison/`
- Branch: `main`
- Migrated from `/home/xupeipeioo1/apps/clinical-result-comparison` and pushed as root commit `08440ad`.


Build the first Tool Smith Agent for reconstructing complete trial interpretations from multiple user-selected clinical result records, using only their original `source_full_text` and preserving source-level linked citation traceability.

## Housekeeping conventions

- 从 NP Clinical 拉取的示例数据（`evals/**/np-clinical-*/`）不入库：`.gitignore` 已忽略，`fetch-np-clinical-attachments.mjs` 可随时重拉。已提交的历史版本也已从跟踪移除（commit 63c031c）。

## ⏸️ Parked: bar 柱下钻（v0.9-test，已由用户验证可行，暂不开发）

- 全部改动（未提交）已 stash：`git stash list` → `stash@{0}: On chart-drilldown-nct: wip: bar drill-down (v0.9-test) + 1L ORR test datasets — verified by user, park for later`。分支 `feat/chart-drilldown-nct` 与 main 同提交 `349eabc`（无独立 commit），后续要继续可直接 `git checkout feat/chart-drilldown-nct && git stash pop`。
- 内容：`endpoint-bar.html` 支持 `bars[].url` → `window.__toolsmithNavigate(url)`（登记号详情页 `https://ct.pharmcube.com/trial/{nct_id}`）；`SKILL.md`/`chart-templates.md` 下钻契约；v0.9-test 系统提示词（优先读 md 元数据 `source_nct_id` 拼 url）；`test/drilldown-bar-sample.html`；两套测试数据集 `test/drilldown-sources/`（仅保证登记号）与 `test/drilldown-sources-1l-orr/`（一线+ORR，必出柱状图，均带 `source_nct_id`）；`dist/multi-clinical-result-comparison-v0.9-test.zip`。
- 验证结论：部署端 `__toolsmithNavigate` 桥 + 宿主 `window.open` 均已就位；不画图的根因是数据异构（跨线/跨终点）触发契约不绘图，`1l-orr` 数据集（indication 135 + III期 + ORR 端点 `4a8abd33ec374a46b758926758ed410a` + `therapy_labels.meta.text∈{一线治疗,一线}`）可稳定出柱状图。恢复时无需动 tool-smith 端。

## Current version

- System prompt: `v0.9`
- Skill: `multi-clinical-result-comparison` trial-level synthesis `v0.9` (file-based report delivery via `present_artifact`)

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
- 示例成品（真实数据）：`evals/iteration-16/chart-examples/` 下 3 份 HTML + 渲染 PNG，用注入方式生成（模板代码不动、只换 `CHART` 数据）：
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
- **Subagent 机制（调研结论，batch-2 待问 ⑥）**: Tool Smith 后端**已支持**——`SubAgentCapability` 默认注册，主 Agent 有 `task` 工具（参数仅 `subagent_type`+`description`，自包含、无状态、只返回最终结果）；子代理共享同一文件系统（可直接读 `/workspace/uploads/source-0XX.md`，写出的文件主线程可见）；递归深度 `max_recursive_depth=2`；前端 project-dialog 有 `capabilities_config.subagents` 开关。用户提议的「5 个子代理 × 10 个文件 → 汇总」架构上可行（把主 Agent 从读 50 全文降为收 5 份摘要，缓解 token）。待确认：开关是否默认开、多 `task` 并发是否真实生效（pydantic-ai 默认串行，Tool Smith 代码未见 `allow_concurrent_tool_calls`）。
- **Subagent 策略已预写入 SKILL（标注待验证）**: `references/input-contract.md` 新增「Large-batch delegation via subagents (OPTIONAL, pending verification)」章节（分包 ≤10/块、task 自包含描述、只回紧凑摘要、ref 按文件名全局映射、递归≤1 层、无 task 工具时回退直读）；`SKILL.md` Input 段加了同义指针。等下周确认 4 项验证清单（开关、附件落盘、并发、token）后即可转默认启用。

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
