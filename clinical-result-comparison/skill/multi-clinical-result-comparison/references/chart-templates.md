# 图表使用规则（依赖 chart-visualization-json skill）

本 skill 的图表部分只定义临床场景选择、证据可比性、数值绑定和交付边界；图表协议、字段、模板、Schema、渲染和校验均由上游 `chart-visualization-json` skill 负责。需要生成图表时读取并遵循上游 skill 的当前规则，不在本 skill 中复制其协议说明或维护平行实现。

`templates/charts/*.json` 是本 skill 提供的临床场景起点；它们的内容应作为上游图表模板的配置输入，不构成另一套图表协议。
## 一、选型规则（与 SKILL.md 工作流一致）

**先判时间维度，再判横截面：** 同一研究、同一队列、同一终点存在 ≥2 个已披露时点（长期应答维持、体重/生物标志物变化、OLE 随访、PFS/OS 按时间点）→ **优先用折线图**呈现随时间变化；单时点单值终点（ORR、EASI-75 等横截面应答率）→ 柱状图并列；证据链/里程碑顺序 → 时间轴。

| 场景 | 图表 type | 图表 skill 模板 | 本 skill 临床起点 |
| --- | --- | --- | --- |
| **同试验**证据链时间轴（≥2 个证据状态） | `timeline`（竖向列表：时间 + 卡片 · 节点等大等形、无图例，不编码成熟度/分类） | `templates/timeline.json` | `templates/charts/evidence-timeline.json` |
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
    3) 两组条件都满足 → **两张都出**，按「时间维度 → 横截面对比」分段呈现；某组不满足可比条件则该组不出图，原因写成**材料/数据的限制**（数值不可比 / 只有单个数值 / 人群不同），放在**正文**或该表**已有的材料属性列**里；**不要**做成 `不绘图原因` / `无法绘图` 这类**自述列名或标签**（`check_report.py` 判 FAIL）。
    即：**「时间维度优先」只是排序与取舍优先级，不是「有折线就不出柱状」，也不是「混合输入总共只能出一张图」**；数据里确实没有多时点时，折线条件不成立，此时只出各组的横截面柱状是正确的，不算漏图。
  - **同试验** = 证据链时间轴（≥2 个证据状态且来源支持先后时必出；否则按 `timeline-diagram.md` 回退为表格）；定量主图为**可选补充**，仅当同时满足下列条件时才出 **至多 1 张**：(a) ≥2 条入选结果给出**同一终点、同一口径**（同人群/同定义/可明确对齐的时点）的纯数值；(b) 该终点是横截面单值（→ `bar`）或**同一队列同一终点的 ≥2 个已披露时点**（→ `line`）；(c) 不跨研究/队列/人群连线。任一条件不满足 → **只出时间轴**，把原因写成**材料/数据的限制**（数值不可比 / 只有单个数值 / 人群不同）放进**正文**或表内已有的材料属性列；**不要**写成 `不绘图原因` 这类自述列名或标签。
  - 因此**同试验输入最多 2 张图**（时间轴 + 至多 1 张定量主图）；**混合输入 = 至多 1 张折线 + 每个临床问题组至多 1 张柱状**（同时成立就是 2 张及以上）。每张图都保留解释文字与精确数值表。
- 证据边界以 `references/input-contract.md` 的 **Evidence source priority** 为唯一权威：数值/披露形式/时间顺序可来自所选记录的临床内容及按该契约取得并核实的同记录原文（含 PMC 全文）。全文独占事实保留时点、分析集、人群与来源映射；题名/链接等元数据本身不支持临床事实。不得扩展检索未选研究或凭记忆补值；折线只连已披露时点，不外推。

## 二、怎么用

1. **只写「内容 spec」，组装与校验交给 `python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py`**（**不要**自己 `cp` 模板、**不要**手拼 envelope、**不要**自己改 `option` 内层、**不要**手写成品 JSON）：spec 顶层写 `type`（`bar`/`line`/`timeline`）、`file`（固定成品名，如 `endpoint-bar-1.json`）、`title`/`subTitle`/`dataSource`/`describe`、`axisXTitle`/`axisYTitle`（bar/line）与 `data[]`，然后

```bash
python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py work/charts/endpoint-bar-1.json
```

   脚本会从本 skill `templates/charts/` 取 `option` 骨架、从**运行期** chart skill 取 envelope（`id` / `iframe_template` / `option` 三键；`iframe_template` 每次发布都会变，本 skill 文档里没有、也不该有这个值）、写入 `/workspace/visualizations/<固定成品名>` 并跑上游 CLI 校验。`--sort auto|none|value-desc|value-asc|time-asc`（默认 bar `value-desc`、line `none`、timeline `time-asc`）由脚本负责排序，不必自己排。完整 CLI / 退出码见 `references/toolbox.md`。
2. **只改内容字段**：`title`/`subTitle`/`dataSource`/`describe`/`axisXTitle`/`axisYTitle` 与 `data[]`（及 timeline 的 `time`/`content`）。JSON 无注释；不要加 HTML/注释/尾逗号（脚本会校验结构、`data` 非空与数值形态）。**timeline 不要写 `weight`/`weightLegend`/`legend`**（见下条硬规则）。
3. **`make_chart.py` 退出码 `0`（已写，WARN 也算 `0`）后才在正文引用**；`3` = 结构/数值问题（`data` 为空或非数值、timeline 缺 `time`、`data[].value` 非数值、timeline 带 `weight`/`weightLegend`/`legend`、`file` 与 `type` 不符）**且不写文件**，按提示修 spec 重跑；`4` = 成品已写但校验器不可用，**必须如实说明「未校验」，不得当已校验**。空 `label`/`description`/`group` 只打印 `WARN:`（成品照写、exit `0`），**不要在写 spec 之前为它们预检**。详见下方「自检」。
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

- timeline `data[]` 一条 = **一个证据状态**（同状态多篇披露合并为一节点），按来源支持的 数据截止→随访→分析里程碑→披露日期 排布（数组顺序即时间顺序，渲染端自上而下逐条渲染、不重排）。
- **图只画骨架，表是数值唯一出处（硬性）**：timeline 的 `label` ≤18 字、`content` ≤16 字定性短语、`description` 只写关系 + 成熟度方向 + `{{ref_n}}`；**图内除 `time` 的时间锚点（年月/日期）外不得出现任何数值**（样本量、pCR/ORR/HR/CI/p、发生率、随访时长一律留在时间线表格）。
- **一个数值只交付一次（硬性，bar/line 同样适用）**：图所在的小节内**不得再放复述该图数值的表格**（数值表放独立小节或附录）；速览段若已有图，只写散文不列表。**图的 `subTitle`/`describe`/`data[].description` 不得复述自己的绘图值**——只写口径、时点差异、方向、可比性判断与 `{{ref_n}}`（timeline 的相应要求见上一条）。剂量/间隔/时点/例数后缀里的数字（`225 mg`、`每 12 周`、`129 例`）是上下文不是复述；研究内对照值/边界值（安慰剂组、95%CI、p）仍可留在 `description`，它们不是绘图值。同一小节出现 ≥2 个该图绘图值即 FAIL，由 `scripts/check_report.py` 机械检查（附录与 timeline 图豁免）。**这不是取消图**：图必须保留，只是不再重复同一批数字。
- **排序规则**：柱状图如需降序由生成方按 `value` 从高到低排好 `data[]`；折线图/时间轴按**时间顺序**（`label`/`time` 数组顺序即时间顺序）。
- **图表每一行点名自己的试验（硬性）**：身份维度一共五个——试验·治疗臂·剂量·间隔·时点。**一张图里出现 ≥2 个试验时，每根柱子/每条线自己的 `label` 或 `description` 里必须写明它属于哪个试验**（有注册号写注册号，没有写试验短名）；**不得只靠标题、图例或颜色区分试验**——读者单看一根柱子也要知道它来自哪个试验。只画一个试验的图可以把试验写在标题里。
- **同一观察一套写法（硬性）**：同一观察（试验·治疗臂·剂量·间隔·时点）只用**一套**身份短语，并在正文、精确值表与图表 `label`/`description` 中**逐字复用**；写法取原文本来的措辞（`monthly` → `每月一次`，`every 12 weeks` → `每 12 周`）——原文说 monthly 就写每月，不因 `Q4W` 更常见而改字。**不得一份报告里同物两名**（正文 `每月`、图表 `Q4W`/`QM`），**图表 label 不得引入正文没有的臂/剂量/间隔/时点写法**：label 就是正文该行身份短语的原样引用。确需缩写时只固定一种，正文同时给出全称，全篇统一用该缩写。
- `value` 只填纯数字（**timeline 不用 `value`**）；line/bar 的 `description` 放可追溯的补充说明（95%CI、人群口径、`{{ref_n}}` 对应信息等），直接写说明内容，不加「数据说明：」或「数据说明」前缀；timeline 的 `description` 按上一条的骨架规则（无数值）。`group` 用于多系列（line 的队列/治疗组、bar 的系列）。
- **timeline 不使用 `weight`/`weightLegend`/`legend`（硬性）**：现行时间轴渲染为**竖向列表**（每个节点 = 时间 + 卡片），所有节点**等大等形**、**不渲染图例**，且 `group`/`shape` 在画布上没有任何视觉效果 ⇒ `weight`（大小）、`weightLegend`（图例）、`legend`（分类图例/形状）写了只会制造“成熟度或分类已被编码”的错觉。证据成熟度写在正文与节点 `description` 的文字里，分类写在 `label`/`content` 的文字里（详见 `references/timeline-diagram.md` 构建规则第 8 条）。
- 引用保留：`dataSource` 行写清数据来源，正文相应位置保留 `{{ref_n}}` 标记；**图表 JSON 内不写 `entity:` 文本**（v0.16 已移除该内联引用语法，任何地方都不再承载它）。

### 自检（硬步骤，必跑）

**生成后自检（硬步骤，必跑）**：`make_chart.py` 已把成品写成 envelope 三键（`id` / `iframe_template` / `option`）并跑过一次上游 CLI；交稿前再用 `python3 /workspace/skills/multi-clinical-result-comparison/scripts/check_report.py`（它会检查每个 `::visualization` 目标是否存在、envelope 键是否恰为三键、`data` 是否非空、`type` 与文件名是否一致）确认引用面，并在需要时手动复跑上游校验命令：

```bash
node /workspace/skills/chart-visualization-json/scripts/validate-cli.js /workspace/visualizations/endpoint-bar-1.json
# 前端仓库内的等价别名：
pnpm validate:chart -- /workspace/visualizations/endpoint-bar-1.json
```

（把示例中的 `endpoint-bar-1.json` 换成该次运行实际产出的固定成品名，如 `endpoint-bar-2.json`、`endpoint-line-1.json`、`evidence-timeline.json`，对每个成品各跑一次。）

全部 **PASS（退出码 0）** 才算完成；**FAIL 时按输出的 JSON path 与提示修正后重跑校验，直到 PASS**，不要让非法 JSON 进入交付。
校验覆盖：envelope 三键（`id` 为字面量；`iframe_template` 与运行期图表 skill `config.js` 的 `IFRAME_TEMPLATE` **全等**）、
`type` 属于图表 skill 收录的类型、`data` 非空、字段名/类型符合 Zod schema、timeline 的
`time` 与 `data[]` 顺序、JSON 可解析等。产物是**纯 JSON**，不校验 HTML 片段（本 skill 不产出 HTML）。

**权威只有部署端那一份（避坑）**：校验结果以工作区里实际安装的图表 skill（`/workspace/skills/chart-visualization-json/`）为准。离线核对可以拿**带版本号的上游副本**（如 v1.0.9）跑同一个 `validate-cli.js`，但**前提是该副本版本与部署端一致**，且副本里内嵌的 `iframe_template` 只是**留档时点的值**，永远不能当本次运行的取值。
不要拿手头保存的旧副本或旧文档里的模板当基准——图表 skill 升级协议（例如新增 envelope 要求）后，旧副本会给出错误的「PASS」结论。
若部署端报出本文件未覆盖的新规则，以部署端报错为准修正，并把差异反馈给维护者（不要自研平行校验器）。

**校验环境不可用时的降级（不得静默跳过）**：若脚本不存在（图表 skill 未安装在工作区）或运行时报依赖缺失
（如 `Cannot find module 'zod'`），**不要**跳过校验、也**不要**输出未经校验的图表引用。此时按以下顺序处理：
先用 `ls /workspace/skills/` 定位图表 skill 的真实路径重试一次；仍不可用则在报告中明确说明「图表校验环境不可用」，
把该图的正文精确数值表与文字结论作为主交付，并省略对应 `::visualization` 引用。不要退回自研校验脚本。
