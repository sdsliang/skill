# 图表使用规则（依赖 chart-visualization-json skill）

本 skill 的图表部分只定义临床场景选择、证据可比性、数值绑定和交付边界；图表协议、字段、模板、Schema、渲染和校验均由上游 `chart-visualization-json` skill 负责。需要生成图表时读取并遵循上游 skill 的当前规则，不在本 skill 中复制其协议说明或维护平行实现。

`templates/charts/*.json` 是本 skill 提供的临床场景起点；它们的内容应作为上游图表模板的配置输入，不构成另一套图表协议。
## 一、选型规则（与 SKILL.md 工作流一致）

**先判时间维度，再判横截面：** 同一研究、同一队列、同一终点存在 ≥2 个已披露时点（长期应答维持、体重/生物标志物变化、OLE 随访、PFS/OS 按时间点）→ **优先用折线图**呈现随时间变化；单时点单值终点（ORR、EASI-75 等横截面应答率）→ 柱状图并列；证据链/里程碑顺序 → 时间轴。

| 场景 | 图表 type | 图表 skill 模板 | 本 skill 临床起点 |
| --- | --- | --- | --- |
| **同试验**证据链时间轴（≥2 个证据状态） | `timeline`（圆点坐基线 · 大小=证据成熟度） | `templates/timeline.json` | `templates/charts/evidence-timeline.json` |
| **同试验** OLE/长随访，同一队列多时点终点 | `line`（同队列时点连线，无对照即单臂曲线） | `templates/line.json` | `templates/charts/endpoint-line.json` |
| **混合/不同试验**，终点无时间维（ORR 等单值） | `bar`（横向） | `templates/bar.json` | `templates/charts/endpoint-bar.json` |
| **混合/不同试验**，终点有时间维（体重、PFS/OS 按时间点） | `line`；仅一个时间点→自动单点模式 | `templates/line.json` | `templates/charts/endpoint-line.json` |

> 「图表 skill 模板」列的路径相对图表 skill 根目录；「本 skill 临床起点」列的路径相对本 skill 根目录。二者同为图表 skill 协议结构，临床起点只是把 `title`/`describe`/`axisTitle`/示例数据预填成临床口径，**仍以图表 skill 的 schema 为准**。
>
> **两者的交付角色不同**：图表 skill 的 `templates/*.json` 是**带 envelope 的完整成品骨架**（复制它拿到 `id`/`iframe_template`）；本 skill 的临床起点是 **`option` 内层**（嵌进 envelope 的 `option` 里）。直接拿临床起点当成品交付会在校验时被拒（`未包 envelope`）。

### 时间维度优先判定（硬规则）

- **当数据集以长期随访/多时点披露为主（OLE 开放标签延展、同一队列 ≥2 个时点、停药后复发时间等）时，图表主线用折线图**，横截面单值柱状图仅作组间对照补充，不作为第一呈现。
- 折线图 `data[]` 用 `group` = 队列/治疗组、`label` = 已披露时点（W4/W12/…）。**只连线同一研究、同一队列、同一终点的时点**；不同研究/不同人群/不同队列的时点**不连线**（避免把跨研究差异误画成趋势）；不插值、不补点、不外推。
- 单时点披露（如某 OLE 只报第 68 周）用**单点模式**（前端只标点 + 数值，不强行连线），多个单点系列可同图并列。
- 无对照的开放标签单臂（婴幼儿外用药等）也按时间维度画折线，但 `subTitle`/`describe` 必须注明「单臂、无对照，仅描述随时间变化，不解读为对照获益」。
- `description` 标注时点口径（如 W16 为 OLE 基线沿用原研究基线）、分母/人群（应答者/部分应答者、n）、以及可追溯信息；直接写说明内容，不添加「数据说明：」或「数据说明」前缀。`title` 只提供语义标题字段，不在本 skill 中加入前端展示控制语句。

- **图数量与组合（同一输入不应因运行而变）**：
  - **混合/不同试验**：时间维度与横截面**是两件独立的事，不是二选一**，按下面顺序各自判断：
    1) 存在**同一研究、同一队列、同一终点**的 ≥2 个已披露时点 → 出 **1 张折线**（时间维度优先，先出、先呈现）；
    2) 每个临床问题组，只要组内有 ≥2 条**可比**（同人群/同定义/可对齐时点）的横截面单值 → 该组出 **1 张横截面柱状**；
    3) 两组条件都满足 → **两张都出**，按「时间维度 → 横截面对比」分段呈现；某组不满足可比条件则该组不出图，并在表格说明原因。
    即：**「时间维度优先」只是排序与取舍优先级，不是「有折线就不出柱状」，也不是「混合输入总共只能出一张图」**；数据里确实没有多时点时，折线条件不成立，此时只出各组的横截面柱状是正确的，不算漏图。
  - **同试验** = 证据链时间轴（≥2 个证据状态且来源支持先后时必出；否则按 `timeline-diagram.md` 回退为表格）；定量主图为**可选补充**，仅当同时满足下列条件时才出 **至多 1 张**：(a) ≥2 条入选结果给出**同一终点、同一口径**（同人群/同定义/可明确对齐的时点）的纯数值；(b) 该终点是横截面单值（→ `bar`）或**同一队列同一终点的 ≥2 个已披露时点**（→ `line`）；(c) 不跨研究/队列/人群连线。任一条件不满足 → **只出时间轴**，并在正文/表格说明不出定量图的原因（数值不可比 / 只有单个数值 / 人群不同）。
  - 因此**同试验输入最多 2 张图**（时间轴 + 至多 1 张定量主图）；**混合输入 = 至多 1 张折线 + 每个临床问题组至多 1 张柱状**（同时成立就是 2 张及以上）。每张图都保留解释文字与精确数值表。
- 证据边界以 `references/input-contract.md` 的 **Evidence source priority** 为唯一权威：数值/披露形式/时间顺序可来自所选记录的临床内容及按该契约取得并核实的同记录原文（含 PMC 全文）。全文独占事实保留时点、分析集、人群与来源映射；题名/链接等元数据本身不支持临床事实。不得扩展检索未选研究或凭记忆补值；折线只连已披露时点，不外推。

## 二、怎么用

1. **先复制图表 skill 的模板拿到 envelope**（不要直接改模板文件，也不要把本 skill 的临床起点当成品）：
  `mkdir -p /workspace/visualizations && cp /workspace/skills/chart-visualization-json/templates/bar.json /workspace/visualizations/endpoint-bar-1.json`
   ——复制来的 `id` / `iframe_template` / `option` 三键**原样保留**，`iframe_template` 每次发布都会变，本 skill 文档里没有、也不该有这个值。
2. **只替换 `option` 内层**：把 `option` 内的 `data[]` 与文案换成该次运行的临床内容；内容可从本 skill 临床起点
   `templates/charts/endpoint-bar.json` 拷进去（它是 **`option` 内层，直接当成品校验会报「未包 envelope」**）。
   只改数据与文案字段：`title`/`subTitle`/`dataSource`/`describe`/`axisXTitle`/`axisYTitle` 与 `data[]`
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
- `value` 只填纯数字；`description` 放可追溯的补充说明（95%CI、人群口径、`{{ref_n}}` 对应信息等），直接写说明内容，不加「数据说明：」或「数据说明」前缀。`group` 用于多系列（line 的队列/治疗组、bar 的系列、timeline 的图例 key）。
- timeline 的 `group` 必须与 `legend[].key` 一致；`weight` 0–N 表示证据成熟度/强调度。
- 引用保留：`dataSource` 行写清数据来源，正文相应位置保留 `{{ref_n}}` 标记；**图表 JSON 内不写 `entity:` 链接**（图表是隔离的渲染件，正文才承载实体引用）。

### 自检（硬步骤，必跑）

**生成后自检（硬步骤，必跑）**：先确认成品顶层是 envelope 三键（`id` / `iframe_template` / `option`），不是平铺的 `option`；
再对每个成品运行图表 skill 的校验命令：

```bash
node /workspace/skills/chart-visualization-json/scripts/validate-cli.js /workspace/visualizations/endpoint-bar-1.json
# 前端仓库内的等价别名：
pnpm validate:chart -- /workspace/visualizations/endpoint-bar-1.json
```

（把示例中的 `endpoint-bar-1.json` 换成该次运行实际产出的固定成品名，如 `endpoint-bar-2.json`、`endpoint-line-1.json`、`evidence-timeline.json`，对每个成品各跑一次。）

全部 **PASS（退出码 0）** 才算完成；**FAIL 时按输出的 JSON path 与提示修正后重跑校验，直到 PASS**，不要让非法 JSON 进入交付。
校验覆盖：envelope 三键（`id` 为字面量；`iframe_template` 与运行期图表 skill `config.js` 的 `IFRAME_TEMPLATE` **全等**）、
`type` 属于图表 skill 收录的类型、`data` 非空、字段名/类型符合 Zod schema、timeline 的
`time`/`weight`/`legend` 关联、JSON 可解析等。产物是**纯 JSON**，不校验 HTML 片段（本 skill 不产出 HTML）。

**权威只有部署端那一份（避坑）**：校验结果以工作区里实际安装的图表 skill（`/workspace/skills/chart-visualization-json/`）为准。离线核对可以拿**带版本号的上游副本**（如 v1.0.9）跑同一个 `validate-cli.js`，但**前提是该副本版本与部署端一致**，且副本里内嵌的 `iframe_template` 只是**留档时点的值**，永远不能当本次运行的取值。
不要拿手头保存的旧副本或旧文档里的模板当基准——图表 skill 升级协议（例如新增 envelope 要求）后，旧副本会给出错误的「PASS」结论。
若部署端报出本文件未覆盖的新规则，以部署端报错为准修正，并把差异反馈给维护者（不要自研平行校验器）。

**校验环境不可用时的降级（不得静默跳过）**：若脚本不存在（图表 skill 未安装在工作区）或运行时报依赖缺失
（如 `Cannot find module 'zod'`），**不要**跳过校验、也**不要**输出未经校验的图表引用。此时按以下顺序处理：
先用 `ls /workspace/skills/` 定位图表 skill 的真实路径重试一次；仍不可用则在报告中明确说明「图表校验环境不可用」，
把该图的正文精确数值表与文字结论作为主交付，并省略对应 `::visualization` 引用。不要退回自研校验脚本。
