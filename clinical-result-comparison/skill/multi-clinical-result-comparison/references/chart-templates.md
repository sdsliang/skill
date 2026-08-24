# 图表模板（charts/）使用说明

> 多临床结果对比 Skill 的三张图表模板，基于蓝紫色系自定义色板（靛蓝→紫），
> 纯 SVG/CSS/原生 JS 单文件 HTML，无外部依赖（离线可用、Tool Smith 沙箱内可运行）。
> 与 `templates/charts/` 下的 HTML 文件配套使用。

## 一、选型规则（与 SKILL.md 工作流一致）

| 场景 | 图表 | 模板文件 |
| --- | --- | --- |
| **同试验**证据链时间轴（≥2 个证据状态） | 时间轴（旗帜 + 证据链成熟度带） | `charts/evidence-timeline.html` |
| **混合/不同试验**，终点无时间维（ORR 等单值） | 柱状图（横向） | `charts/endpoint-bar.html` |
| **混合/不同试验**，终点有时间维（体重、PFS/OS 按时间点） | 折线图；仅一个时间点→自动单点模式 | `charts/endpoint-line.html` |

- 一个报告最多 1–2 张图：同试验 = 1 张时间轴；混合 = 1 张柱状或折线。
- 证据边界不变：数值/披露形式/时间顺序**只能来自 `source_full_text`**，不得从输入顺序推断。

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
   - `value` 只填原文数值；`ci` 填原文给出的置信区间；`note` 为可追溯的补充说明。
   - 引用保留：图下方 source 行写清数据来源，正文相应位置保留 `{{ref_n}}` 标记。

## 三、配色（Tool Smith 品牌 token）

基准见 `charts/chart-tokens.css`（每个模板内联同一套规则），**硬规则**：

- **主色一律引用宿主注入的 `--viz-*` 语义 token**，不得把整套独立 hex 色板写进图表代码（那属第二套配置，会覆盖宿主主题）。
- 品牌 hex 只允许作为 `var(--viz-*, #hex)` 的 **fallback 参数**（本地独立预览 / 宿主未注入时兜底），接入后被 `--viz-*` 自动覆盖；模板 JS 用 `viz(name, fb)` 运行时读取注入值。
- 映射（前端给定）：背景 `--viz-background`、卡片 `--viz-surface`、主文字 `--viz-text`、次要/说明 `--viz-text-muted`、边框/坐标轴 `--viz-border`、分类系列 `--viz-series-1..5`；状态 `--viz-info/success/warning/danger`。
- 品牌 hex fallback 值：背景 `#f4f5f7`、卡片 `#ffffff`、主文字 `#020A1A`、次要 `#4e5969`、说明 `#8993a4`、边框 `#DADEE6`、系列 `#3d7eff/#7c3aed/#0ea5e9/#14b8a6/#f59e0b`（见 `chart-tokens.css`）。
- 模板内 `legend`/`series` 的 `color` 可填 token 名（如 `"--viz-series-1"`，推荐）或 hex；未填用默认系列色。
- 不用红绿色表语义好坏（宿主注入的系列色为准）。

## 四、与 lieflat-charts 的关系

- 当前三张模板为自建（走 Tool Smith 品牌 token，先保证“好看 + 品牌一致”）。
- 需要更花哨的图型（分布、矩阵、网络、报告页）时，可基于
  `~/.agents/skills/lieflat-charts`（64 图型）的 gallery 模板扩展；
  颜色仍建议收敛到 `--viz-*` token 注入，避免混用色系。
- 同试验时间轴无 lieflat 完全对口图型，以本模板为准。

## 五、当前版本边界

- 全部图表（同试验时间轴、混合/不同试验柱状与折线）统一走 HTML 模板 + `::visualization` 引用，随 v0.8 生效；不再输出 Mermaid。
- 证据边界不变：数值/披露形式/时间顺序只能来自 `source_full_text`。
