# 数据契约（np_clinical via MCP）

## 1. 入口

唯一数据路径：ToolSmith 的 MCP 工具 `pharmcube-query-clinical-result-with-params`
（底层表 `TableName.CLINICAL_TRIAL_RESULT_STRUCTURED`）。

调用方式（本地脚本 / 排查用）：

```
POST {TS_BASE}/api/tools/debug
Authorization: Bearer $TS_TOKEN
{
  "name": "pharmcube-query-clinical-result-with-params",
  "mcp_server_id": "pharmcube",
  "arguments": {
    "meeting_tags": "ESMO 2026",
    "selected_fields": [ ...见下... ]
  }
}
```

- `meeting_tags` **精确匹配**（不是模糊搜索）。ESMO 2026 → 1338 原始行，1.1 s 量级。
- 同一试验会返回多行（按 arm / endpoint 拆行）。**必须按 esid 去重**：1338 → 988。
- `selected_fields` 必须是字段白名单里的**原样字符串**（大小写敏感）。写错直接 `BadRequestException`，不会静默忽略。

> 不走 ES 直连的原因：ES 里 `np_clinical` 与 `np_result` 的口径不同（ESMO 2026：945 vs 332），且 `np_clinical_conference` 索引对本账号 403。结构化表是唯一能拿到 `study_results`（含 p / HR / CI）的路径。

## 2. 字段清单（15 个，实跑可用）

```
_id
trial_abbreviation
paper_title
abstract_text
summary
key_evidence
evaluation
evidence_source
group_count
randomized
blinded
trial_control
indication_name
primary_endpoint_cn
study_results
```

说明：

| 字段 | 含义 | 坑 |
|---|---|---|
| `_id` | esid | 去重键 |
| `trial_abbreviation` | 试验简称 | **可能为空**，且同试验不同摘要可能写法不同；为空时去重退化为 esid |
| `abstract_text` | 完整结构化摘要（Background/Methods/Results/Conclusion，~2500 字符） | 复核的**主输入** |
| `summary` | ~300–400 字符英文摘要（无中文） | 缺失率极低（467/467 命中），作降级输入 |
| `key_evidence` | 「是/否」类枚举 | 不是 LBA 标记，别误用 |
| `evaluation` | `积极` / `-` / `不佳` / `终止` | **记录级**，同试验不同摘要可能不同 |
| `evidence_source` | `Phase I` / `Phase I/II` / `Phase II` / `Phase II/III` / `Phase III` / `Phase IV` / `前瞻性研究` / `回顾性研究` / `真实世界研究` / `Not Applicable` / `汇总分析` | **这是试验期别的正确来源** |
| `group_count` | 样本量 | 展示用，不作门槛 |
| `randomized` / `blinded` / `trial_control` | 设计属性 | 缺失较多，只能作佐证 |
| `indication_name` | 适应症列表 | 列表，不是字符串 |
| `primary_endpoint_cn` | 主要终点（中文） | 列表 |
| `study_results` | 臂级终点行（见下） | 只在"详情拉取"里返回；lite 拉取常为空 |

## 3. `study_results` 行结构

```
arm_type, endpoint_type, endpoint_label, endpoint_attribute,
result, compare_result, result_unit,
p_value, outcome_p_value, hazard_ratio, hazard_ratio_ci, odd_ratio, relative_risk
```

实测分布（ESMO 2026，3445 行）：

- `endpoint_attribute`：有效性 1717 / 安全性 1475 / QOL 130 / PK-PD 120 / 空 3。
  → **取疗效信号前必须过滤掉安全性行**，否则 `Grade≥3 TEAE 44.6%` 会被当成疗效。
- 只有约 5–6/10 行带 `p_value` 或 `hazard_ratio`；多数结论只能来自 `abstract_text`。

## 4. 两段式拉取（省额度）

1. **lite 拉取**：只拉元数据（不含 `study_results`），用于分桶。ESMO 2026 → 988 esid。
2. **详情拉取**：只对进入复核的 esid 拉 `study_results` + 全文，每批 25 个 esid。

`scripts/triage.py --require-detail` 对应这个两段式：先在 lite 池里排名，再只对带 `study_results` 的记录重排。

## 5. 额度与时间

- 单次 `meeting_tags` 全量拉取 ≈ 1 s、~1300 行。
- 详情拉取：149 esid → 212 行 → ~3.7 MB。批量 25 个 esid 一轮，别一次塞几百个。
- 不要为了"确认一个数字"重复全量拉取；把结果落 JSON 再复用。

## 6. 本仓库已有的实跑产物

| 文件 | 内容 |
|---|---|
| `dist/esmo2026-judgements.csv` | 467 条逐条判定（含 data_type / key_numbers / reason） |
| `dist/ESMO2026-watchlist.csv` | 30 条定榜 |
| `dist/ESMO2026-watchlist.md` | 三桶报告 |

## 7. 会议摘要库（`medicalMeeting`）—— 并列第二入口

结构化结果表不是会议全本。ESMO 2026 实测：

| 指标 | 结构化结果表 | 会议摘要库 |
|---|---|---|
| 记录数 | 646（去重后 esid） | **5810** |
| 可用摘要（有 abstract_id + 全文 + 非 TiP） | 646 | **4103** |
| 覆盖关系 | — | 646 条全部能匹配上（title 归一后 646/646，零损失） |

调用形态：

```json
{"name":"pharmcube-mcp-medicalMeeting",
 "arguments":{"conference":"ESMO 2026","pageNo":1}}
```

可选过滤：`abstractId` / `drugName` / `target` / `disease`。20 条/页，ESMO 2026 共 290 页，8 并发约 4 分钟。

**`conference` 留空 = 跨全部会议检索**，`scripts/meeting_pull.py --conference -` 即用于拉某药的历史读出一览。

返回字段（对 triage 有用的）：

| 字段 | 用途 |
|---|---|
| `abstract_id` | **报告形式来源**（后缀 `O`/`RO`/`P`/`eP`/`eTiP`）+ 唯一标识 |
| `abstract_text` | 全文（B 型裸标题格式：`Background` / `Methods` / `Results` / `Conclusions` 各占一行） |
| `title` | join 键（`NFKD` + 小写 + 非字母数字转空格） |
| `drug` / `target` / `moa` | 结构化表常缺；ESMO 2026 分别 1954 / 1797 条有值 |
| `abstract_release_date` / `meeting_date` / `url` | 时间线与引用 |
| `session_type` | 报告形式（也可从 `abstract_id` 后缀直接得，更稳） |

**注意**：会议摘要库没有 `study_results`、没有 `evidence_source`、没有 `evaluation`。所以它只能**补充**，不能**替代**结构化表的分桶依据。

> 这些是**样例产物**，不是随 skill 发布的固定答案；换会议必须重跑。
