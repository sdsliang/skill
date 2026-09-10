# 图表模板与校验（复用 chart-visualization-json skill）

> 多临床结果对比 Skill 自 v0.14 起，图表产物**统一为 JSON 文件**，并**直接复用上游
> `chart-visualization-json` skill**（下称「图表 skill」）的协议、模板与校验能力，不再自研一套平行实现。
>
> | 能力            | 来源（图表 skill，唯一权威）                                                       |
> | --------------- | ---------------------------------------------------------------------------------- |
> | 协议与工作流    | `chart-visualization-json/SKILL.md`                                                |
> | 类型 / 字段细则 | `chart-visualization-json/references/chart-types.md`                               |
> | 可渲染模板      | `chart-visualization-json/templates/line.json`、`bar.json`、`timeline.json`        |
> | Schema 实现     | `chart-visualization-json/references/schemas/`（Zod，小驼峰字段）                  |
> | 校验命令        | `node /workspace/skills/chart-visualization-json/scripts/validate-cli.js <file.json>` |
>
> 本 skill 不再产出 HTML/SVG fragment，也**不再维护自研校验脚本**：旧 HTML 图表模板与
> `validate-chart.py` / `render-preview.py` 自 **v0.15 起已从本仓库彻底移除**（回溯可见 git 历史
> `e4f3bb7`，本 skill 不再默认它们存在）。`templates/charts/*.json` 只是**按该协议预填的
> 临床场景起点**，产物是否合法一律以图表 skill 的 schema 与 CLI 校验结果为准；渲染由前端
> chart-visualization-json 渲染层完成。
>
> 运行时路径以工作区实际情况为准（图表 skill 通常位于 `/workspace/skills/chart-visualization-json/`，
> 与本 skill 同级）；校验脚本依赖项目根的 `zod`。

## 零、协议要点（以图表 skill 为准，勿自造字段）

- 可渲染类型 `RENDERABLE = line | bar | timeline`（图表 skill 的 `RENDERABLE_CHART_TYPES`）；本 skill 只产出这三种。
- 合并 JSON 无额外 envelope：顶层公共字段（小驼峰）+ `type` + 类型专属 payload。
  - 公共字段：`title`、`subTitle`、`dataSource`、`describe`、`width`、`height`、`theme`，带坐标轴的图再加
    `axisXTitle`、`axisYTitle`（`timeline` 不适用坐标轴标题）。
  - `dataSource` / `describe` 是元数据，**不参与前端组件绘制**（只在协议层保留来源与读图说明）。
- 数据行（line/bar 的 `data[]`）：`label`（维度标签）、`value`（**纯 number**）、`group`（多系列分组，string）、
  `description`（可选短说明，不参与绘制）、`drill`（可选下钻传参）。
- timeline 的 `data[]`：`label`（必填）+ `time`（**必填**，时间锚点文案；未知写「时间未明」）、`group`、
  `weight`（number ≥ 0，驱动圆点大小，默认 0）、`content`（支持 `\n` 多行）、`description`、`drill`；
  顶层可选 `legend`（`key`/`label`/`shape: circle | empty-circle`）与 `weightLegend`（`{ show, label }`）。
  `data[].group` 必须与 `legend[].key` 对应。
- bar 的类型专属字段：`group`（boolean，默认 false）、`stack`（boolean，默认 **true**）、`direction`
  （`horizontal` | `vertical`，不填时 bar 按 horizontal）。**并排柱状须显式写 `group: false, stack: false`**，
  否则默认 `stack: true` 会按堆叠语义解读。`theme` ∈ `default` / `academy` / `dark`。
- line 可选的 `style.startAtZero` / `style.lineWidth` 等属图表 skill 能力；本 skill 默认只用最小字段集。
- **数值纪律（硬规则）**：`value` 只放纯数字，不得把「未报告 / NR / NE / 空 / 区间 / 95%CI / 带 `%` 字符串」
  放入 `value`——这类放该项 `description` 或正文精确数值表。
- 不写 Mermaid、不产出 `.html`、不在 JSON 内混入自定义色板或 CSS/HTML token（视觉与主题统一由渲染层处理，`theme` 字段按图表 skill 协议填写）。

## 一、选型规则（与 SKILL.md 工作流一致）

**先判时间维度，再判横截面：** 同一研究、同一队列、同一终点存在 ≥2 个已披露时点（长期应答维持、体重/生物标志物变化、OLE 随访、PFS/OS 按时间点）→ **优先用折线图**呈现随时间变化；单时点单值终点（ORR、EASI-75 等横截面应答率）→ 柱状图并列；证据链/里程碑顺序 → 时间轴。

| 场景 | 图表 type | 图表 skill 模板 | 本 skill 临床起点 |
| --- | --- | --- | --- |
| **同试验**证据链时间轴（≥2 个证据状态） | `timeline`（圆点坐基线 · 大小=证据成熟度） | `templates/timeline.json` | `templates/charts/evidence-timeline.json` |
| **同试验** OLE/长随访，同一队列多时点终点 | `line`（同队列时点连线，无对照即单臂曲线） | `templates/line.json` | `templates/charts/endpoint-line.json` |
| **混合/不同试验**，终点无时间维（ORR 等单值） | `bar`（横向） | `templates/bar.json` | `templates/charts/endpoint-bar.json` |
| **混合/不同试验**，终点有时间维（体重、PFS/OS 按时间点） | `line`；仅一个时间点→自动单点模式 | `templates/line.json` | `templates/charts/endpoint-line.json` |

> 「图表 skill 模板」列的路径相对图表 skill 根目录；「本 skill 临床起点」列的路径相对本 skill 根目录。二者同为图表 skill 协议结构，临床起点只是把 `title`/`describe`/`axisTitle`/示例数据预填成临床口径，**仍以图表 skill 的 schema 为准**。

### 时间维度优先判定（硬规则）

- **当数据集以长期随访/多时点披露为主（OLE 开放标签延展、同一队列 ≥2 个时点、停药后复发时间等）时，图表主线用折线图**，横截面单值柱状图仅作组间对照补充，不作为第一呈现。
- 折线图 `data[]` 用 `group` = 队列/治疗组、`label` = 已披露时点（W4/W12/…）。**只连线同一研究、同一队列、同一终点的时点**；不同研究/不同人群/不同队列的时点**不连线**（避免把跨研究差异误画成趋势）；不插值、不补点、不外推。
- 单时点披露（如某 OLE 只报第 68 周）用**单点模式**（前端只标点 + 数值，不强行连线），多个单点系列可同图并列。
- 无对照的开放标签单臂（婴幼儿外用药等）也按时间维度画折线，但 `subTitle`/`describe` 必须注明「单臂、无对照，仅描述随时间变化，不解读为对照获益」。
- `description` 标注时点口径（如 W16 为 OLE 基线沿用原研究基线）、分母/人群（应答者/部分应答者、n）、以及可追溯信息。

- 一个报告图数量按需组织：同试验 = 时间轴（+ OLE 多时点折线）；混合 = 时间维度优先折线 + 横截面单值柱状（每组各一图）；图多时按「时间维度 → 横截面对比」分段呈现，每张图保留解释文字与精确数值表。
- 证据边界不变：数值/披露形式/时间顺序**只能来自所选临床结果的 params 返回字段**，不得凭空编造或从记忆补；折线只连已披露时点，不外推。

## 二、怎么用

1. **复制**对应模板为成品（不要直接改模板文件）：优先从图表 skill 模板或本 skill 临床起点复制，例如
   `cp /workspace/skills/chart-visualization-json/templates/bar.json /workspace/visualizations/endpoint-bar-1.json`，
   或 `cp templates/charts/endpoint-bar.json /workspace/visualizations/endpoint-bar-1.json`。
2. **只改数据与文案字段**：`title`/`subTitle`/`dataSource`/`describe`/`axisXTitle`/`axisYTitle` 与 `data[]`
   （及 timeline 的 `legend`/`weightLegend`/`time`/`weight`/`content`）。JSON 无注释；不要加 HTML/注释/尾逗号。
3. **用图表 skill 的 CLI 校验**（见下「自检」），全部 PASS 后再在正文引用；FAIL 则按输出的 JSON path 修正后重跑，直到 PASS。
4. 正文中用 `::visualization[标题]{path="/workspace/visualizations/endpoint-bar-1.json"}` **绝对路径**引用（workspace 文件 + 引用通道），独占一行；图前后保留解释文字与 `{{ref_n}}` 标记。
   - 交付：文件**先写入** `/workspace/visualizations/`，再引用；引用路径必须从 `/workspace/visualizations/` 开头。
   - 降级：接入方不支持渲染时，正文保留文字结论 + 精确数值表 + 下载链接。

### 交付路径契约（所有图表统一遵守）

- 引用一律用**绝对路径**，并写上下方契约定义的固定成品名：`::visualization[标题]{path="/workspace/visualizations/endpoint-bar-1.json"}`。不写相对路径。
- 路径必须位于 `/workspace/visualizations/` 下；禁止目录穿越（`..`）、反斜杠 `\`、以及 `/workspace/visualizations/` 前缀之外的任何路径。
- **文件名固定，后端可写死**（无需从报告或工具结果反推）：证据链时间轴恒为 `evidence-timeline.json`；柱状图 `endpoint-bar-<n>.json`、折线图 `endpoint-line-<n>.json`，`<n>` 为**该类型图在正文中的出现顺序**，从 1 开始（单张柱状图恒为 `endpoint-bar-1.json`，单张折线图恒为 `endpoint-line-1.json`）。**图表类型进文件名**（`bar` / `line`），并且必须与 JSON 内的 `type` 字段一致（`"type": "bar"` / `"type": "line"`）——渲染器就是按 `type` 派发的（`RENDERABLE_CHART_TYPES = ["line","bar","timeline"]`），文件名只是给人和后端看的稳定索引。只用 ASCII 小写字母、数字、连字符，不使用子目录，不加 slug / 日期 / 试验名后缀。
- 引用必须出现在文件写入**之后**；JSON 文件上限 1 MiB。
- 正文始终保留 fallback（文字结论 + 精确数值表），接入方不支持渲染时仍能完整理解结论。

### 数据填充约束

- timeline `data[]` 一条 = **一个证据状态**（同状态多篇披露合并为一节点），按来源支持的 数据截止→随访→分析里程碑→披露日期 排布（数组顺序即时间顺序，图表 skill 不重排）。
- **排序规则**：柱状图如需降序由生成方按 `value` 从高到低排好 `data[]`；折线图/时间轴按**时间顺序**（`label`/`time` 数组顺序即时间顺序）。
- `value` 只填纯数字；`description` 放可追溯的补充说明（95%CI、人群口径、`{{ref_n}}` 对应信息等）。`group` 用于多系列（line 的队列/治疗组、bar 的系列、timeline 的图例 key）。
- timeline 的 `group` 必须与 `legend[].key` 一致；`weight` 0–N 表示证据成熟度/强调度。
- 引用保留：`dataSource` 行写清数据来源，正文相应位置保留 `{{ref_n}}` 标记；**图表 JSON 内不写 `entity:` 链接**（图表是隔离的渲染件，正文才承载实体引用）。

### 自检（硬步骤，必跑）

**生成后自检（硬步骤，必跑）**：每个成品写入 `/workspace/visualizations/` 前，运行图表 skill 的校验命令：

```bash
node /workspace/skills/chart-visualization-json/scripts/validate-cli.js /workspace/visualizations/endpoint-bar-1.json
# 前端仓库内的等价别名：
pnpm validate:chart -- /workspace/visualizations/endpoint-bar-1.json
```

（把示例中的 `endpoint-bar-1.json` 换成该次运行实际产出的固定成品名，如 `endpoint-bar-2.json`、`endpoint-line-1.json`、`evidence-timeline.json`，对每个成品各跑一次。）

全部 **PASS（退出码 0）** 才算完成；**FAIL 时按输出的 JSON path 与提示修正后重跑校验，直到 PASS**，不要让非法 JSON 进入交付。
校验覆盖：`type` 属于图表 skill 收录的类型、`data` 非空、字段名/类型符合 Zod schema、timeline 的
`time`/`weight`/`legend` 关联、JSON 可解析等。产物是**纯 JSON**，不校验 HTML 片段（本 skill 不产出 HTML）。

**校验环境不可用时的降级（不得静默跳过）**：若脚本不存在（图表 skill 未安装在工作区）或运行时报依赖缺失
（如 `Cannot find module 'zod'`），**不要**跳过校验、也**不要**输出未经校验的图表引用。此时按以下顺序处理：
先用 `ls /workspace/skills/` 定位图表 skill 的真实路径重试一次；仍不可用则在报告中明确说明「图表校验环境不可用」，
把该图的正文精确数值表与文字结论作为主交付，并省略对应 `::visualization` 引用。不要退回自研校验脚本。
