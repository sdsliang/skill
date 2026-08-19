# 药物机制增强（drug_earth 字典）

## 目标

会议临床解读不只展示「有哪些药」，还应回答「这些药是什么、作用在哪」。本 skill 为代表药物与重点清单中的药物补充**靶点（target）、作用机制（MOA）、药物类型（modality）、研发阶段、别名、研发机构、获批信息**，来源为药物字典（drug_earth，医药魔方 DrugBank 同源数据），经 Linking API `/linking/drug` 批量查询。

## 数据来源与接口

- 字典：`drug_earth`（ES 索引，含 `drugbank_id` 字段，可与 DrugBank 关联）
- 接口：Linking API `POST /linking/drug`
  - 入参：`input_text`（药物名，支持别名）、`top_k`（取 1 命中即可）、`use_gpt_recommender:false`（确定性匹配优先）
  - 出参：`raw_candidates[0].metadata[0]` 含完整画像字段
- 命中原则：`name_short` / `title` 与查询名高度一致；明显误匹配（试验名、噪声片段）丢弃

## 提取字段（写入 drug-profiles.json）

| 字段 | 来源 | 说明 |
| --- | --- | --- |
| `name` | `name_short` / `title` | 标准中文/英文名 |
| `aliases` | `all_name_for_show_en` | 别名（含商品名、代号） |
| `targets` | `target_all_name` | 靶点全名列表（如 PD-1 / nectin-4 / TROP2） |
| `moa_cn` / `moa_en` | `moa_track_name_cn/en` | 作用机制轨道名（可用） |
| `moa_class` | `moa_all_name` | 机制类别（如 单克隆抗体 / ADC / 抑制剂） |
| `drug_type_1/2` | `drug_type_1/2` | 创新类型、药品类别 |
| `modality` | `drug_type_3` / `modality_manual` | 分子形态（如 双特异性抗体、抗体偶联药物） |
| `latest_phase` | `latest_phase` | 全球最高研发阶段 |
| `first_appr_date` | `first_appr_date` | 首次获批时间 |
| `drugbank_id` | `drugbank_id` | DrugBank 关联 ID |
| `dar_value` | `dar_value` | ADC 的 DAR 值 |
| `companies` | `company_all_name` | 研发机构 |
| `originator_regions` | `regn_of_originator_right_full` | 原研权利区域 |
| `status` | `status` | 研发状态 |

## 画像文件格式

`drug-profiles.json`：

```json
{
  "schema_version": "2.0.0",
  "conference": "ASCO 2026",
  "drug_count": 59,
  "profiles": {
    "维恩妥尤单抗": {
      "query": "维恩妥尤单抗",
      "name": "维恩妥尤单抗",
      "aliases": ["Padcev", "enfortumab vedotin-ejfv", "备思复", ...],
      "targets": ["nectin4", "nectin-4", ...],
      "moa_class": ["抗体偶联药物"],
      "modality": ["抗体偶联药物"],
      "latest_phase": "批准上市",
      ...
    }
  },
  "lookup": { "<标准名小写>": { ... }, "<别名小写>": { ... } }
}
```

- `lookup` 索引由「标准名 + 别名 + 查询名」小写化构建，供渲染层 O(1) 命中。
- 文件同时落到 `evals/iteration-01/<conference>/drug-profiles.json` 与 `evals/fixtures/<conference>-drug-profiles.json`（后者供复用/测试）。

## 渲染层用法

- **靶点/机制标签**：每条证据、每个重点清单条目按 `drugs` 列表反查画像，用 `targets[0]`（短代码化）与 `moa_class[0]` 生成标签；靶点=青绿标签、MOA=紫标签，避免别名重复。
- **药物画像下钻**：点击证据/清单「查看证据」弹出抽屉，逐药物展示完整画像（靶点、MOA、modality、阶段、别名、DrugBank ID、研发机构、获批时间）。
- **搜索增强**：证据搜索同时匹配药物别名、靶点、MOA（如搜「PD1」可命中所有 PD-1 相关证据）。
- **网络悬停**：关系网络中药物的 tooltip 展示其靶点/机制。

## 短代码化规则

`target_all_name` 常含冗余别名与拼接串（如 `tumorassociatedcalciumsignaltransducer2TACSTD2`、`programmed cell death 1 (PD1)`）。渲染时：
- 优先取括号内的缩写（`(PD1)` → `PD1`）
- 过长拼接串用已知靶点正则收窄（`TACSTD2`/`HER2`/`PD1`/`CTLA4`/`VEGFR2` 等）
- 每药每类只保留首个标签，全表去重，最多 5 个标签

## 覆盖率与噪声

- 化疗辅药（奥沙利铂/卡铂/氟尿嘧啶等）同样可命中，其靶点（如 DNA、TYMS）与机制类别（铂类抗癌药、抗代谢）一并展示，**热度≠记录数** 原则不变。
- 试验名、期刊缩写等非药物实体不进入查询集合；查询时用长度 + 噪声正则（`phase|study|trial|癌|症|vs |[0-9]` 等）过滤。
- 单次查询失败自动重试（≤3 次），并发 5；约 60 个药物全量可在 1 分钟内完成。

## 中国企业/中国创新药判定（近似）

用于报告「中国企业/中国创新药参与」维度的数据依据。**属近似推断**，不是申办方字段。

- 依据：`companies`（研发机构/原研机构列表）中出现中国药企名称/拼音/股票代码。
- 中国药企特征词：`hengr|恒瑞|beiGene|百济|君实|junshi|信达|innovent|康方|kangfang|科伦|kelun|正大天晴|石药|先声|simcere|荣昌|remegen|三生|sanyou|基石|cstone|和黄|hutchmed|再鼎|zailab|复宏汉霖|迪哲|泽璟|歌礼|亚盛|迈威|普米斯|乐普|绿叶|远大|豪森|hansoh|艾力斯|海和|加科思|德琪|盟科|宜明昂科|百奥赛图|传奇|legendbiotech|驯鹿|亘喜|斯丹赛|诺诚健华|贝达|贝伐?…` 等（名单随数据扩充）。
- 注意：
  - 有些中国药企产品已 license-out（如替雷利珠单抗→诺华、呋喹替尼→武田），`companies` 会显示外企——**需以原研/中国研发机构为准**，必要时参考 `name_short`/历史记录，标注为近似。
  - `originator_regions` 字段过于宽泛（多数药物都含"中国(内地)"），**不可单独**用作中国企业判定；仅作辅助参考。
- 输出：`drug-profiles.json` 中每药附 `is_china_origin`（true/false，基于 companies 判定）与 `china_company`（匹配到的公司名）。
- 报告中使用时必须在「信息缺口与局限」说明该判定的近似性。
