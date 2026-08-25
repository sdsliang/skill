# 图表模板（charts/）使用说明

> 多临床结果对比 Skill 的三张图表模板，基于 **lieflat-charts violet 紫罗兰预设**
> （象牙纸 + 单色相紫阶，明度 = 数值；柱形为横档柱、1 格 = 1 单位；一律实心无渐变阴影），
> 纯 SVG/CSS/原生 JS 单文件 HTML，无外部依赖（离线可用、Tool Smith 沙箱内可运行）。
> 与 `templates/charts/` 下的 HTML 文件配套使用。

## 一、选型规则（与 SKILL.md 工作流一致）

**先判时间维度，再判横截面：** 同一研究、同一队列、同一终点存在 ≥2 个已披露时点（长期应答维持、体重/生物标志物变化、OLE 随访、PFS/OS 按时间点）→ **优先用折线图**呈现随时间变化；单时点单值终点（ORR、EASI-75 等横截面应答率）→ 柱状图并列；证据链/里程碑顺序 → 时间轴。

| 场景 | 图表 | 模板文件 |
| --- | --- | --- |
| **同试验**证据链时间轴（≥2 个证据状态） | 时间轴（圆点坐基线 · 大小=证据成熟度） | `charts/evidence-timeline.html` |
| **同试验** OLE/长随访，同一队列多时点终点 | 折线图（同队列时点连线，无对照即单臂曲线） | `charts/endpoint-line.html` |
| **混合/不同试验**，终点无时间维（ORR 等单值） | 柱状图（横向） | `charts/endpoint-bar.html` |
| **混合/不同试验**，终点有时间维（体重、PFS/OS 按时间点） | 折线图；仅一个时间点→自动单点模式 | `charts/endpoint-line.html` |

### 时间维度优先判定（新增，硬规则）

- **当数据集以长期随访/多时点披露为主（OLE 开放标签延展、同一队列 ≥2 个时点、停药后复发时间等）时，图表主线用折线图（`endpoint-line.html`）**，横截面单值柱状图仅作组间对照补充，不作为第一呈现。
- 折线图 `series[]` = 队列/治疗组（`color` 用 `--viz-series-*` token），`points[]` = 已披露时点 `{t,v}`。**只连线同一研究、同一队列、同一终点的时点**；不同研究/不同人群/不同队列的时点**不连线**（避免把跨研究差异误画成趋势）；不插值、不补点、不外推。
- 单时点披露（如某 OLE 只报第 68 周）用**单点模式**（模板自动：只标点 + 数值，不强行连线），多个单点系列可同图并列。
- 无对照的开放标签单臂（婴幼儿外用药等）也按时间维度画折线，但标题/说明必须注明「单臂、无对照，仅描述随时间变化，不解读为对照获益」。
- 图内 `note` 标注时点口径（如 W16 为 OLE 基线沿用原研究基线）、分母/人群（应答者/部分应答者、n）、以及 `{{ref_n}}` 可追溯标记。

- 一个报告图数量按需组织：同试验 = 时间轴（+ OLE 多时点折线）；混合 = 时间维度优先折线 + 横截面单值柱状（每组各一图）；图多时按「时间维度 → 横截面对比」分段呈现，每张图保留解释文字与精确数值表。
- 证据边界不变：数值/披露形式/时间顺序**只能来自 `source_full_text`**，不得从输入顺序推断；折线只连已披露时点，不外推。

## 二、模板怎么用

1. **复制**对应 HTML 文件为成品（不要直接改模板文件）。
2. **只改 `<script>` 里的 `CHART` 数据对象**（title/subtitle/source/events/bars/series…），渲染区代码一律不动。
3. 保存为 `xxx.html`，正文中用 `::visualization[标题]{path="/workspace/visualizations/xxx.html"}` **绝对路径**引用（workspace 文件 + 引用 通道），独占一行；图前后保留解释文字。
   - Tool Smith 交付：文件**先写入** `/workspace/visualizations/`，再引用；引用路径必须从 `/workspace/visualizations/` 开头。
   - 降级：接入方不支持时，正文保留文字结论 + 可下载链接。

### 交付路径契约（所有图表统一遵守）

- 引用一律用**绝对路径**：`::visualization[标题]{path="/workspace/visualizations/<文件名>.html"}`。不写相对路径（如 `path="xxx.html"` 或 `path="visualizations/xxx.html"`）。
- 路径必须位于 `/workspace/visualizations/` 下；禁止目录穿越（`..`）、反斜杠 `\`、以及 `/workspace/visualizations/` 前缀之外的任何路径。
- 文件名用 ASCII 小写字母、数字、连字符（如 `train2-evidence-timeline.html`、`orr-comparison-endpoint-bar.html`），不使用子目录。
- 引用必须出现在文件写入**之后**；HTML 文件上限 1 MiB。
- 文件必须是 **HTML fragment**（Tool Smith 用隔离 iframe 的 fragment 渲染器注入，规则与内联 widget 相同）：**不含** `<!doctype html>`、`<html>`、`<head>`、`<body>`、`<meta>`、`<title>` 等文档级包裹；只保留 `<style>` + 内容 + `<script>`。模板已按此格式提供，成品不得再加回文档包裹标签。
- ⚠️ Tool Smith 前端用**子串匹配**校验：`lower.includes('<!doctype') / '<html' / '<head' / '<body'`，对**全文**（含注释、CSS、script 字符串）任何位置命中即报“不是有效的 HTML/SVG fragment”。因此**不要使用 `<header>` 等含 `<head` 前缀的标签**（模板已用 `<div class="header">`）；CSS 选择器、注释、脚本字符串里也不要出现这些子串。
- 正文始终保留 fallback（文字结论 + 精确数值表 + 下载链接），接入方不支持可视化时仍能完整理解结论。
4. 数据填充约束：
   - `events[]`（时间轴模板）一条 = **一个证据状态**（同状态多篇披露合并为一节点，`note` 并列 `{{ref_n}}`），按来源支持的 数据截止→随访→分析里程碑→披露日期 排布（模板按数组顺序排布，不推断阶段/形式）。
   - **排序规则**：柱状图（`endpoint-bar.html`）按 `value` 从高到低**自动降序**（模板内完成，无需人工排）；折线图/时间轴按**时间顺序**（`points[]`/`events[]` 数组顺序即时间顺序，模板不重排）。
   - `value` 只填原文数值；`ci` 填原文给出的置信区间；`note` 为可追溯的补充说明。
   - 引用保留：图下方 source 行写清数据来源，正文相应位置保留 `{{ref_n}}` 标记。
5. ⚠️ **脚本批量填充与自检（防 JS 语法错误）**：多图批量时可用脚本（如 Python）复制模板后替换 `CHART` 数据对象，但替换结果**必须是合法 JS**——否则 Tool Smith 隔离 iframe 直接报「渲染失败」：
   - `const CHART = {` 的左花括号**只能有一个**（模板已带）。数据对象是 `{…}` 时不要再拼一个 `{`：直接用 `json.dumps` 拼接会在其后多出一个 `{`（`const CHART = {` 下一行出现 `{`）→ `Unexpected token '{'`。
   - 数据对象必须以 `};` 结尾，**保留模板分号**。丢了分号会被 ASI 与下一行 `(function(){…})()` 连读成“调用对象”→ 运行时 `TypeError: … is not a function`。
   - 只替换 `CHART`；不改渲染区、不换配色。
   - **生成后自检（硬步骤，必跑）**：每个成品写入 `/workspace/visualizations/` 前，运行 `python3 templates/charts/validate-chart.py <成品文件>`（与模板同目录带校验脚本），全部 **PASS** 才算完成；**FAIL 时按输出的行号与修复提示修正后重跑校验，直到 PASS**，不要让语法错误的文件进入分享页。校验项：Tool Smith 禁用子串/结构、双 `{`、缺 `;`、花括号配对、CHART 字段、文件大小；node 可用时额外做真 JS 语法校验。

## 三、配色（lieflat violet 预设 + Tool Smith token 契约）

基准见 `charts/chart-tokens.css`（每个模板内联同一套规则）。默认设计语言 = **lieflat-charts violet 紫罗兰预设**：
象牙纸 `#F7F2EB`、墨 `#2B1450`、紫阶 `#2B1450 → #55339A → #8A63D2 → #C6B3EE`，单色相明度阶、
一律实心无渐变阴影、发丝网格、数值标签纸色描边光晕、全大写来源行。**硬规则**：

- **每个模板只使用一种色彩系统（violet 紫系）**，禁止在图表里混入第二套色系。
- **柱形深浅 = 数值高低**（明度即数据，柱越高越深紫）；折线/图例/时间轴默认取紫系多档色（SER）；
  研究组/对照组等语义由标签与标题区分，不用第二色相。
- 仍保留 `--viz-*` 契约：颜色一律以 `var(--viz-*, #violet-fallback)` 引用宿主注入值，
  未注入时 fallback = violet 预设；宿主注入主题时自动覆盖（几何/排版不变）。
- 模板 JS 用 `viz(name, fb)` 运行时读取注入值；`legend`/`series` 的 `color` 可填 token 名
  （如 `"--viz-series-1"`）或 hex；未填用紫系默认档位。
- fallback 值见 `chart-tokens.css`：背景 `#F7F2EB`、卡片 `#F7F2EB`、主文字 `#2B1450`、
  次要 `rgba(43,20,80,.60)`、说明 `rgba(43,20,80,.32)`、边框 `rgba(43,20,80,.16)`、
  紫阶系列 `#55339A/#2B1450/#8A63D2/#C6B3EE/#E4DAF8`。
- 不用红绿色表语义好坏；深浅只表数值/证据强度，好坏判断留在文字。

## 四、与 lieflat-charts 的关系

- 三张模板的设计语言已接入 **lieflat-charts violet 预设**（`~/.agents/skills/lieflat-charts`，
  `color-presets.js` 四套内置之一）：象牙纸 + 单色相紫阶 + 横档柱 + 发丝网格 + 编辑排版，
  几何与排版继承 lieflat 的 Mono 视觉语法；violet 由用户定制的紫色家族固化而来。
- 需要更花哨的图型（分布、矩阵、网络、报告页）时，可基于 lieflat-charts gallery 模板扩展；
  颜色仍收敛到同一套 violet 预设或 `--viz-*` 注入，禁止混用色系。
- 同试验时间轴无 lieflat 现成组件，按 lieflat **L11 Trend Lineage（事件序列生命史）** 语法延伸为本模板：圆点=事件节点（实心=披露/更新，空心=里程碑锚点）、圆点大小=证据成熟度（phase）、圆点**直接坐基线上**（点轴一体）、数值**纵排多行**在圆点上方（value 支持 `\n` 手动分行 + 自动折行，离开轴线）、基线下为日期；每条**丝线**（1px muted）连接数值块底部与圆点顶部（归属连接，里程碑无数值不连）；标签/数值/日期三块**固定槽位顶部对齐**（LBL 52/67 → VAL 96/112/128 → 圆点 200 → 日期 222/236）、端部锚定（首左/末右）防溢出；无矩形/三角/刻线。

## 五、当前版本边界

- 全部图表（同试验时间轴、混合/不同试验柱状与折线）统一走 HTML 模板 + `::visualization` 引用，随 v0.8 生效；不再输出 Mermaid。
- 证据边界不变：数值/披露形式/时间顺序只能来自 `source_full_text`。
