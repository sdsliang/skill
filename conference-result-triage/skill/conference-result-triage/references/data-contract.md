# 数据契约（平台内执行版 v0.3）

## 0. 在 TS 上唯一允许的取数方式

**平台工作区没有网络**（见 `pitfalls.md` §21：in-cluster 端点 `Network is unreachable`、公网 DNS 全灭、`env` 里无 MCP 端点）。所以平台内**不允许**让脚本自己联网，两条命令代替原来的直连：

```bash
# 1) 你先调用工具（结果会被平台强制落盘，模型只看到 5 行预览）
#    pharmcube-query-clinical-result-with-params
#      meeting_tags = "ESMO 2026"
#      selected_fields = pull_results.py --list-fields 的输出，逐字复制
#    → /workspace/tool_results/pharmcube-query-clinical-result-with-params/<call-id>.jsonl

# 2) 脚本解析 dump（跨多次调用去重合并）
python3 /workspace/skills/conference-result-triage/scripts/pull_results.py \
    --from-tool-results /workspace/tool_results \
    --out /workspace/work/rows.json
```

落盘格式：`data` 是 list 时一行一个 row（JSONL），键就是 `clinical_result__id` / `clinical_result_lba` 等返回键，**无需映射**。dump 在 **turn 结束时清除**，必须同 turn 解析。

`featured` / `lba` 旁表同理：一次 `TEST_execute-sql`（`SELECT extra_esid, featured, lba FROM clinical_trial_result_structured WHERE journal='ESMO 2026'`），再 `--flags-from /workspace/tool_results/pharmcube-TEST_execute-sql`。

直连模式（不带 `--from-tool-results`）只在本地/有外网时可用：`--conference "ESMO 2026"`，走 `MCP_PHARMCUBE_ENDPOINT_URL`（默认 `http://172.17.26.74:30080/mcp/`）+ `PHARMCUBE_MCP_APP_KEY`，工具名用 `tools/list` 自动发现（匹配 `query-clinical-result`），固定两阶段：先只取 id、再按 `esids` 切片取全字段。

## 1. 直连调试入口（仅排查，不是 skill 的数据路径）

```
POST {TS_BASE}/api/tools/debug
Authorization: Bearer $TS_TOKEN
{
  "name": "pharmcube-query-clinical-result-with-params",
  "mcp_server_id": "pharmcube",
  "arguments": {"meeting_tags": "ESMO 2026", "selected_fields": [ ...见下... ]}
}
```

- `meeting_tags` **精确匹配**（不是模糊搜索），写错得到空集。
- 同一试验会按 arm / endpoint 拆多行，**必须按 esid 去重**。
- `selected_fields` 用字段白名单的原样字符串（大小写敏感）；写错 `BadRequestException`，但**漏写不会报错**——这就是 `lba` 被漏掉的方式。
- `clinical_result__id` 不能作为 `selected_fields` 传入（`INVALID_INPUT`），但会在返回行里出现，就是 `esid`。

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

## 7. 会议摘要库（`medicalMeeting`）—— **仅限本地/有外网，平台内不可用**

> **平台内（v0.3 主运行时）这条路走不通**：Tool Smith 的 35 个工具里没有会议摘要库，`mcp-openapi.pharmcube.com` 不在容器网络内，23 张可查表里也没有会议表。所以平台内**拿不到摘要号**，`abstract_id` 恒为 `null`，报告形式只剩 `clinical_result.lba`（`featured` 是人工/AI 生产标记，不是头条，见 `screening-rules.md` §3.1b）。下面这节只在本地跑或容器能出网时适用。

结构化结果表不是会议全本。ESMO 2026 实测：

| 指标 | 结构化结果表 | 会议摘要库 |
|---|---|---|
| 记录数 | 646（去重后 esid） | **5810** |
| 可用摘要（有 abstract_id + 全文 + 非 TiP） | 646 | **4103** |
| 覆盖关系 | — | 646 条全部能匹配上（title 归一后 646/646，零损失） |

调用形态（endpoint `https://mcp-openapi.pharmcube.com/mcp`，Bearer appkey）：

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
