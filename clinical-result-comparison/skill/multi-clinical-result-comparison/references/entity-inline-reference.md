# 实体内联引用（entity inline reference）

## Purpose

把报告中出现的药品、公司、临床试验注册号等名称渲染成 ToolSmith 前端可识别的**实体标签**：点击可继续追问、复制实体 ID、降低同名/别名/中英文混用歧义。平台在 Markdown 正文和 artifact 文件阅读器里都把这类引用渲染为可交互实体胶囊。

## Syntax

ToolSmith 前端（`EntityAnchor`）识别的格式是 Markdown 内联链接：

```markdown
[name](entity:type:id)
```

- `name`：报告中展示的实体名称（保留来源支持的拼写，见下）；
- `type`：`drug`（药品）、`company`（公司）、`trial`（临床试验/注册号）；
- `id`：实体 ID，**只能来自 params 返回记录的实体字段**（见下）。

示例：

```markdown
[依沃西单抗](entity:drug:12483){{ref_1}}
[NCT05840016](entity:trial:NCT05840016){{ref_1}}
[Bristol-Myers Squibb](entity:company:319){{ref_1}}
```

## ID 来源（硬规则）

实体 ID 来自 MCP `pharmcube-query-clinical-result-with-params` 返回记录中经 `selected_fields`
拉取的嵌套字段（见 `references/input-contract.md` 与 `docs/params-tool-schema.md`）：

| 实体 | 类型 | ID 字段 | 展示名来源 |
| --- | --- | --- | --- |
| 药品 | `drug` | `clinical_result.arms[].drugs[].drug_earth_id` | 同记录的 `drug_earth_name_cn`（优先）/ `drug_earth_all_name` / `drug_earth_name_en` |
| 公司/申办方 | `company` | `clinical_result.projects[].company_ids[]` | 同记录的 `company_name_cn`（优先）/ `company_all_name` / `company_name_en` |
| 临床试验注册号 | `trial` | `clinical_result.projects[].associate_ids[]`（NCT/ChiCTR 等） | `clinical_result.trial_abbreviation`（试验简称）存在时用简称作展示名；否则用注册号本身 |

- **只使用 params 返回记录里明确给出的 ID**，且 ID 与名称要取自同一记录。
- 不得从 `abstract_text`/`summary` 文本推断 ID，不得为拿 ID 调用任何其它外部查询/链接工具，不得编造或补全 ID，不得引用返回记录里不存在的实体。
- 某条记录缺少实体字段 → 该类型不引用任何实体（自然降级为纯文本名称），并在内部记录为标签信息缺口（不影响临床证据边界）。
- 一个记录存在多个 arms / 多个 drugs / 多个 company_ids / 多个 associate_ids 时，只引用报告中**实际出现**的实体；同名实体跨记录去重后仍各自引用其所属记录的 ID。

## 适用范围与命名规则

- **类型映射**：注册号 → `entity:trial:<associate_ids 中该注册号>`；药品 → `entity:drug:<drug_earth_id>`；公司 → `entity:company:<company_ids>`。
- **展示名 = 报告本来要用的名称**：中文报告沿用返回记录支持的中文名（如 `依沃西单抗`），英文记录仅含英文时沿用英文名（如 `ivonescimab`）。展示名不必等于实体字段的名称，但必须是同一实体的来源支持写法；不得为凑引用而给实体起新名或翻译。
- **试验展示名优先用试验简称（v0.11）**：当记录有 `trial_abbreviation` 时，试验展示名用简称（如 `[HARMONi-6](entity:trial:NCT05840016)`、`[TRAIN-2](entity:trial:NCT01996267)`）；无简称时才回退用注册号本身（`[NCT05840016](entity:trial:NCT05840016)`）。注册号永远只作 `entity:trial:` 的 ID，不作为展示名被强行优先。
- **每次提及都引用**，不只是首次：报告中同一药品/公司/注册号的每一处出现，只要有可用 ID 就包成实体引用（含正文/表格/图注里的试验简称）。
- 实体引用可与 `{{ref_n}}` 共存：`[依沃西单抗](entity:drug:12483){{ref_1}}`；两者互不影响。
- **表格与正文均可使用**；同一单元格内的实体引用和 `{{ref_n}}` 相邻书写。
- **图表内不引用**：`::visualization` JSON 图表（chart-visualization-json 协议）不承载 `entity:` 内联链接渲染。图表中的药品/公司/注册号保留纯文本，不写 `entity:` 链接。
- **图表引用标签不是正文实体提及**：`::visualization[...]` 的方括号内容是图表标题，不参与实体锚点覆盖（不要求包 `entity:` 链接），也不算作「有可用 ID 的提及必须已引用」。反过来，标签内不要单独出现裸试验名/药品名，用描述性标题即可（如 `本试验证据链时间轴`、`晚期 sq-NSCLC 一线各试验组中位 PFS`）；需要点名的实体放在图前后的说明文字里，并在那里正常锚定。

## 与证据边界的关系

实体字段（`projects.associate_ids` / `projects.company_ids` / `arms.drugs.drug_earth_id` /
`trial_abbreviation`）与 `paper_title` / `full_article_link` 同级，是**展示/标签元数据，不是临床证据**。用途仅限：

- 把报告中**本来就会出现**的实体名称绑定到 ID 标签；
- 不得用这些 ID 推断、补充或拼接任何临床事实、阶段、人群、数值或结论；
- 不得仅仅因为实体字段有某个实体，就把该实体强塞进报告正文。

## 校验

交付前自查：

- 每个 `entity:` 引用都能在对应 params 返回记录中找到它的类型与 ID（ID 一致）；
- 没有引用任何返回记录未提供的 ID；
- 没有为凑 ID 而调用外部工具或编造；
- 报告正文中所有可用 ID 的实体提及均已引用（无遗漏）；
- 图表 JSON 文件中不包含 `entity:` 文本；
- 锚点覆盖检查只统计正文与表格：`::visualization[...]` 标签不计入，也不要为凑锚点把裸试验名/药品名写进标签；
- **检查前先剥离 `](entity:type:id)` 里的 ID 部分**（只保留方括号展示名），再匹配裸实体名/注册号：`[NCT05840016](entity:trial:NCT05840016)` 已经是锚定提及，不得再被当成裸注册号计为「漏锚点」（否则会触发无谓的返工式编辑）。

### 建议做法：锚点模板 + 构建脚本（一次写对）

锚点应在**第一次写入报告之前**就定下来，靠机械手段保证，而不是写完再 grep 补：

1. **锚点模板**：把报告模板复制成工作文件后，把每个**有可用 ID** 的实体提及写成占位符，例如
   `[{T_IVO}](entity:drug:12483)`、`[{T_TRIAL}](entity:trial:NCT05840016)`，另维护一张 `占位符 → 展示名` 的映射表；
2. **构建脚本带断言**：用脚本渲染模板做替换，并断言
   (a) 输出里没有残留 `{T_…}` 占位符，(b) 每个占位符的实际替换次数等于映射表声明值（`assert n == count`），
   (c) 所有「有可用 ID 的实体名」都出现在锚点位置；任一断言失败即报错重跑，不得静默输出。

这条路比「先写正文、再 grep + `edit_file` 逐个补锚点」少 1–2 个工具步，也避免漏锚点；`{{ref_n}}` 标记可由同一套脚本一并校验。

## 当前范围

v0.10 只启用三类：**药品（drug）、公司（company）、临床试验注册号（trial）**。适应症、靶点等类型在实体字段提供前不引用。

v0.11 在 trial 类型上增加**试验简称展示名**：`entity:trial:` 的 ID 仍是注册号（`projects.associate_ids`），但当 `trial_abbreviation` 存在时展示名用简称；无简称则回退注册号。试验简称同样只在报告正文/表格中使用，不写进图表 JSON。
