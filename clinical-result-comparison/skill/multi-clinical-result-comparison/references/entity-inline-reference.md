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
- `id`：实体 ID，**只能来自附件文件的实体元数据行**。

示例：

```markdown
[依沃西单抗](entity:drug:12483){{ref_1}}
[NCT05840016](entity:trial:NCT05840016){{ref_1}}
[Bristol-Myers Squibb](entity:company:319){{ref_1}}
```

## ID 来源（硬规则）

实体 ID 由**后端在每源附件文件的元数据区透传**，Agent 只能使用这三行：

```markdown
source_nct_id: NCT05840016
source_drug_entities: 依沃西单抗|drug_earth|12483; 卡铂|drug_earth|1618; 紫杉醇|drug_earth|1738
source_company_entities: Bristol-Myers Squibb|base_company|319
```

- `source_drug_entities` / `source_company_entities` 的元组格式为 `名称|实体索引|ID`，多个元组用 `;` 分隔。
- **只引用这三行里明确给出的 ID**。不得从 `source_full_text` 推断 ID，不得为拿 ID 调用任何外部查询/链接工具，不得编造或补全 ID，不得引用元数据行里不存在的实体。
- 某行缺失或为空 → 该类型不引用任何实体（自然降级为纯文本名称）。
- 注册号以 `source_nct_id` 为准（元数据行优先）：该行存在才把注册号渲染为 `entity:trial:`；行缺失时，即使全文出现 NCT/CTR/ChiCTR 也不引用（v0.10 不做文本抽取兜底）。

## 适用范围与命名规则

- **类型映射**：注册号 → `entity:trial:<source_nct_id>`；药品 → `entity:drug:<药品 ID>`；公司 → `entity:company:<公司 ID>`。
- **展示名 = 报告本来要用的名称**：中文报告沿用来源支持的中文名（如 `依沃西单抗`），英文来源仅保留英文时沿用英文名（如 `ivonescimab`）。展示名不必等于元数据行的名称，但必须是同一实体的来源支持写法；不得为凑引用而给实体起新名或翻译。
- **注册号展示名用注册号本身**：`[NCT05840016](entity:trial:NCT05840016)`。
- **每次提及都引用**，不只是首次：报告中同一药品/公司/注册号的每一处出现，只要有可用 ID 就包成实体引用。
- 实体引用可与 `{{ref_n}}` 共存：`[依沃西单抗](entity:drug:12483){{ref_1}}`；两者互不影响。
- **表格与正文均可使用**；同一单元格内的实体引用和 `{{ref_n}}` 相邻书写。
- **图表内不引用**：`::visualization` HTML/SVG 在隔离 iframe 中渲染，没有实体渲染器。图表中的药品/公司/注册号保留纯文本，不写 `entity:` 链接（图表登记号下钻另走 `__toolsmithNavigate`，见 `chart-templates.md`，与实体引用无关）。

## 与证据边界的关系

实体元数据行（`source_nct_id` / `source_drug_entities` / `source_company_entities`）与 `source_title`/`source_url` 同级，是**展示/标签元数据，不是临床证据**。用途仅限：

- 把报告中**本来就会出现**的实体名称绑定到 ID 标签；
- 不得用这些 ID 推断、补充或拼接任何临床事实、阶段、人群、数值或结论；
- 不得仅仅因为元数据行有某个实体，就把该实体强塞进报告正文。

## 校验

交付前自查：

- 每个 `entity:` 引用都能在对应附件元数据行中找到它的类型与 ID（ID 一致）；
- 没有引用任何元数据行未提供的 ID；
- 没有为凑 ID 而调用外部工具或编造；
- 报告正文中所有可用 ID 的实体提及均已引用（无遗漏）；
- 图表文件中不包含 `entity:` 文本。

## 当前范围

v0.10 只启用三类：**药品（drug）、公司（company）、临床试验注册号（trial）**。适应症、靶点等类型在元数据行提供前不引用。
