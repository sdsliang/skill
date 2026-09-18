# pharmcube-query-clinical-result-with-params — Tool Schema 存档

> **自动生成，不要手改。** 由 `toolsmith-publish tool-doc` 从平台 `GET /api/tools` 的 live inputSchema 渲染；
> 上游 schema 变更后重新生成即可（`toolsmith-publish deps` 会先提醒）。
> `selected_fields` 的字段名只能逐字复制自下方 ALLOWED_FIELD_NAMES。

## 1. 工具元信息

- MCP 工具名：`pharmcube-query-clinical-result-with-params`
- MCP server：`Pharmcube`（enabled=True）
- 数据来源：用于查询临床试验结果相关数据，通过给定具体的参数值进行精确过滤。数据来源为"医药魔方 TrialiCube"
- 必填参数：无
- 参数数：18

## 2. 参数表

| 参数 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `trial_id` | string |  | `` | 临床试验注册/登记号，如：'ChiCTR2100043573' |
| `esids` | array[string] |  | `None` | 临床结果的ID列表，用于精确过滤 |
| `drug_names` | array[string] |  | `None` | 药品名称列表，如：['阿司匹林'] |
| `disease_names` | array[string] |  | `None` | 疾病名称列表，如：['非小细胞肺癌'] |
| `target_names` | array[string] |  | `None` | 靶点名称列表，如：['EGFR'] |
| `company_names` | array[string] |  | `None` | 公司/申办方机构名称列表，如：["恒瑞医药"] |
| `modality` | string |  | `` | 治疗方式/手段（MOA），如：'单抗' |
| `global_highest_phase` | string |  | `` | 最高研发阶段(全球), 可选值：临床前, 申报临床, I期临床, I/II期临床, II期临床, II/III期临床, III期临床, 申请上市, 批准上市 |
| `global_highest_phase_excluded` | string |  | `` | 最高研发阶段(全球)排除值, 可选值：临床前, 申报临床, I期临床, I/II期临床, II期临床, II/III期临床, III期临床, 申请上市, 批准上市 |
| `therapy_line` | string |  | `` | 治疗线程，如：'一线治疗' |
| `evidence_type` | string |  | `` | 证据类型，可选值：["BE","Phase III","系统评价","Ⅱ期临床试验","前瞻性研究","Other","Phase II/III","IIb/III期临床试验","队列研究","Ⅰ期临床试验","Phase I","汇总分析","Phase I/II","荟萃分析","Not Applicable","探索性试验","回顾性研究","真实世界研究","Phase IV","Phase II"] |
| `initiation_type` | string |  | `` | 申办类型，可选值：["IIT", "IST"] |
| `meeting_tags` | string |  | `` | 期刊/会议名称，如：'ASCO' |
| `child_disease_included` | boolean |  | `True` | 检索的疾病是否要涵盖其所有子疾病，默认为是 |
| `child_target_included` | boolean |  | `True` | 检索的靶点是否要涵盖其所有子靶点，默认为是 |
| `child_company_included` | boolean |  | `True` | 检索的公司/申办方机构是否要涵盖其所有子公司，默认为是 |
| `child_modality_included` | boolean |  | `True` | 检索的modality是否要涵盖其所有子modality，默认为是 |
| `selected_fields` | array[string] |  | `None` | `selected_fields` 必须是字段名字符串数组，例如：["clinical_trial_project.nct_id", "company.company_name_cn"]。 严格遵守以下规则： 1. 阅读 ALLOWED_FIELDS，通过字段描述得知其含义并选择你所需要的字段。 2. 字段名只能从 ALLOWED_FIELD_NAMES 中逐字复制，大小写必须完全一致。 3. `selected_fields` 不能为空且每项都必须是 ALLOWED_FIELD_NAMES 中的完整字符串，不能填描述文本。 ALLOWED_FIELD_NAMES: [ "clinical_r …（全文见下） |

## 3. 参数完整 schema（逐字节来自平台）

```json
{
  "additionalProperties": false,
  "properties": {
    "trial_id": {
      "default": "",
      "description": "临床试验注册/登记号，如：'ChiCTR2100043573'",
      "type": "string"
    },
    "esids": {
      "default": null,
      "description": "临床结果的ID列表，用于精确过滤",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "drug_names": {
      "default": null,
      "description": "药品名称列表，如：['阿司匹林']",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "disease_names": {
      "default": null,
      "description": "疾病名称列表，如：['非小细胞肺癌']",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "target_names": {
      "default": null,
      "description": "靶点名称列表，如：['EGFR']",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "company_names": {
      "default": null,
      "description": "公司/申办方机构名称列表，如：[\"恒瑞医药\"]",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "modality": {
      "default": "",
      "description": "治疗方式/手段（MOA），如：'单抗'",
      "type": "string"
    },
    "global_highest_phase": {
      "default": "",
      "description": "最高研发阶段(全球), 可选值：临床前, 申报临床, I期临床, I/II期临床, II期临床, II/III期临床, III期临床, 申请上市, 批准上市",
      "type": "string"
    },
    "global_highest_phase_excluded": {
      "default": "",
      "description": "最高研发阶段(全球)排除值, 可选值：临床前, 申报临床, I期临床, I/II期临床, II期临床, II/III期临床, III期临床, 申请上市, 批准上市",
      "type": "string"
    },
    "therapy_line": {
      "default": "",
      "description": "治疗线程，如：'一线治疗'",
      "type": "string"
    },
    "evidence_type": {
      "default": "",
      "description": "证据类型，可选值：[\"BE\",\"Phase III\",\"系统评价\",\"Ⅱ期临床试验\",\"前瞻性研究\",\"Other\",\"Phase II/III\",\"IIb/III期临床试验\",\"队列研究\",\"Ⅰ期临床试验\",\"Phase I\",\"汇总分析\",\"Phase I/II\",\"荟萃分析\",\"Not Applicable\",\"探索性试验\",\"回顾性研究\",\"真实世界研究\",\"Phase IV\",\"Phase II\"]",
      "type": "string"
    },
    "initiation_type": {
      "default": "",
      "description": "申办类型，可选值：[\"IIT\", \"IST\"]",
      "type": "string"
    },
    "meeting_tags": {
      "default": "",
      "description": "期刊/会议名称，如：'ASCO'",
      "type": "string"
    },
    "child_disease_included": {
      "default": true,
      "description": "检索的疾病是否要涵盖其所有子疾病，默认为是",
      "type": "boolean"
    },
    "child_target_included": {
      "default": true,
      "description": "检索的靶点是否要涵盖其所有子靶点，默认为是",
      "type": "boolean"
    },
    "child_company_included": {
      "default": true,
      "description": "检索的公司/申办方机构是否要涵盖其所有子公司，默认为是",
      "type": "boolean"
    },
    "child_modality_included": {
      "default": true,
      "description": "检索的modality是否要涵盖其所有子modality，默认为是",
      "type": "boolean"
    },
    "selected_fields": {
      "default": null,
      "description": "\n            `selected_fields` 必须是字段名字符串数组，例如：[\"clinical_trial_project.nct_id\", \"company.company_name_cn\"]。\n            严格遵守以下规则：\n            1. 阅读 ALLOWED_FIELDS，通过字段描述得知其含义并选择你所需要的字段。\n            2. 字段名只能从 ALLOWED_FIELD_NAMES 中逐字复制，大小写必须完全一致。\n            3. `selected_fields` 不能为空且每项都必须是 ALLOWED_FIELD_NAMES 中的完整字符串，不能填描述文本。\n\n            ALLOWED_FIELD_NAMES:\n            [\n  \"clinical_result.abbreviation_label\",\n  \"clinical_result.abstract_text\",\n  \"clinical_result.arms\",\n  \"clinical_result.baseline_characteristics\",\n  \"clinical_result.biomarker_cn\",\n  \"clinical_result.biomarker_en\",\n  \"clinical_result.blinded\",\n  \"clinical_result.clinical_stage_cn\",\n  \"clinical_result.clinical_stage_en\",\n  \"clinical_result.doi\",\n  \"clinical_result.evaluation\",\n  \"clinical_result.evidence_source\",\n  \"clinical_result.extra_esid\",\n  \"clinical_result.full_article_link\",\n  \"clinical_result.group_count\",\n  \"clinical_result.inclusion_criteria\",\n  \"clinical_result.indication_detail\",\n  \"clinical_result.indication_name\",\n  \"clinical_result.indication_name_en\",\n  \"clinical_result.indication_type_cn\",\n  \"clinical_result.journal\",\n  \"clinical_result.key_evidence\",\n  \"clinical_result.layer_factor\",\n  \"clinical_result.lba\",\n  \"clinical_result.multi_center\",\n  \"clinical_result.paper_release_time\",\n  \"clinical_result.paper_title\",\n  \"clinical_result.participant_flow\",\n  \"clinical_result.pathology_cn\",\n  \"clinical_result.pathology_en\",\n  \"clinical_result.patient_baseline_cn\",\n  \"clinical_result.patient_baseline_en\",\n  \"clinical_result.pm_id\",\n  \"clinical_result.positive_placebo_control\",\n  \"clinical_result.precision_medicine_cn\",\n  \"clinical_result.precision_medicine_en\",\n  \"clinical_result.primary_endpoint_all_name\",\n  \"clinical_result.primary_endpoint_cn\",\n  \"clinical_result.primary_endpoint_en\",\n  \"clinical_result.projects\",\n  \"clinical_result.randomized\",\n  \"clinical_result.random_ratio\",\n  \"clinical_result.study_results\",\n  \"clinical_result.summary\",\n  \"clinical_result.therapy_line_cn\",\n  \"clinical_result.therapy_line_en\",\n  \"clinical_result.trial_abbreviation\",\n  \"clinical_result.trial_control\",\n  \"company.company_category\",\n  \"company.company_type\",\n  \"company.is_ct\",\n  \"company.is_important_corp\",\n  \"company.official_website\",\n  \"company.short_name\",\n  \"company.short_name_en\",\n  \"target.name_short\",\n  \"target.parent_target\",\n  \"indication.name\",\n  \"indication.name_en\",\n  \"indication.parent_indication\",\n  \"biomarker.biomarker\",\n  \"biomarker.name\",\n  \"clinical_stage.stage\",\n  \"clinical_stage.stage_en\",\n  \"therapy_label.name\",\n  \"therapy_label.name_en\",\n  \"clinical_endpoint.endpoint\",\n  \"clinical_endpoint.endpoint_attr\",\n  \"clinical_endpoint.endpoint_en\",\n  \"clinical_endpoint.endpoint_short\",\n  \"modality.name\",\n  \"modality.name_en\",\n  \"modality.parent_moa\"\n]\n\n            ALLOWED_FIELDS (格式：[{\"name\":\"字段名\", \"description\":\"字段描述\"}, ...]):(json)\n            [\n  {\n    \"name\": \"clinical_result.abbreviation_label\",\n    \"description\": \"可枚举字段。临床结果的评价类型\"\n  },\n  {\n    \"name\": \"clinical_result.abstract_text\",\n    \"description\": \"临床结果来源的源文本信息\"\n  },\n  {\n    \"name\": \"clinical_result.arms\",\n    \"description\": \"临床试验的队列信息，嵌套字段，其中包含如下子层级：\\n【name】arms.type_revised，【description】可枚举字段。队列类型（试验组/对照组）；\\n【name】arms.therapeutic_schedule_id，【description】队列的治疗方案ID；\\n【name】arms.therapeutic_schedule_name_cn，【description】队列的治疗方案中文描述；\\n【name】arms.therapeutic_schedule_name_en，【description】队列的治疗方案英文描述；\\n【name】arms.therapeutic_schedule_text_cn，【description】队列的治疗方案中文描述文本，therapeutic_schedule_name_cn为空时补充使用；\\n【name】arms.therapeutic_schedule_text_en，【description】队列的治疗方案英文描述文本，therapeutic_schedule_name_en为空时补充使用；\\n【name】arms.drug_earth_ids，【description】队列治疗方案中的药品ID，为arms.drugs.drug_earth_id的集合；\\n【name】arms.drug_count，【description】队列治疗方案中的药品数量，即drug_earth_ids的个数；\\n【name】arms.mono_or_combo，【description】可枚举字段。临床试验为联用治疗还是单药治疗；\\n【name】arms.drugs，【description】队列中药品及药品特征的详细信息，嵌套字段，其中包含如下子层级：\\n【name】arms.drugs.drug_earth_id，【description】药品ID；\\n【name】arms.drugs.is_primary_drug，【description】该药品是否为主试验药；\\n【name】arms.drugs.drug_earth_name_cn，【description】药品中文名称；\\n【name】arms.drugs.drug_earth_name_en，【description】药品英文名称；\\n【name】arms.drugs.drug_earth_all_name，【description】药品名称集合，在药品实体标准化时通常使用这个字段；\\n【name】arms.drugs.target_ids，【description】药品的靶点ID；\\n【name】arms.drugs.target_count，【description】药品的靶点数量；\\n【name】arms.drugs.target_name，【description】药品的靶点名称；\\n【name】arms.drugs.target_all_name，【description】药品的靶点名称集合，在靶点实体标准化时通常使用这个字段；\\n【name】arms.drugs.drug_type_1，【description】可枚举字段。药品的创新类型；\\n【name】arms.drugs.drug_type_2，【description】可枚举字段。药品的药品类别；\\n【name】arms.drugs.moa_ids，【description】Modality ID；\\n【name】arms.drugs.moa_name_cn，【description】Modality 中文名称；\\n【name】arms.drugs.moa_name_en，【description】Modality 英文名称；\\n【name】arms.drugs.latest_phase，【description】可枚举字段。药品的全球最高研发阶段；\\n【name】arms.drugs.latest_phase_cn，【description】可枚举字段。药品的中国最高研发阶段；\\n【name】arms.drugs.research_institute_ids，【description】药品研发机构ID；\\n【name】arms.drugs.research_institute_names_cn，【description】药品研发机构中文名称；\\n【name】arms.drugs.research_institute_names_en，【description】药品研发机构英文名称；\\n【name】arms.drugs.research_institute_all_names，【description】药品研发机构名称集合，在药品研发机构实体标准化时通常使用这个字段；\\n【name】arms.drugs.research_institute_area，【description】药品研发机构国家/地区。\"\n  },\n  {\n    \"name\": \"clinical_result.baseline_characteristics\",\n    \"description\": \"临床结果的baseline characteristics，以图片的形式存在；可以直接展示\"\n  },\n  {\n    \"name\": \"clinical_result.biomarker_cn\",\n    \"description\": \"临床试验的生物标记物中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.biomarker_en\",\n    \"description\": \"临床试验的生物标记物英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.blinded\",\n    \"description\": \"可枚举字段。临床试验的盲法类型\"\n  },\n  {\n    \"name\": \"clinical_result.clinical_stage_cn\",\n    \"description\": \"临床试验的临床分期中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.clinical_stage_en\",\n    \"description\": \"临床试验的临床分期英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.doi\",\n    \"description\": \"通用ID字段。这篇临床结果论文的doi\"\n  },\n  {\n    \"name\": \"clinical_result.evaluation\",\n    \"description\": \"可枚举字段。临床结果的总体评价，可枚举，便于检索\"\n  },\n  {\n    \"name\": \"clinical_result.evidence_source\",\n    \"description\": \"可枚举字段。临床结果的证据类型\"\n  },\n  {\n    \"name\": \"clinical_result.extra_esid\",\n    \"description\": \"临床结果的来源 ID\"\n  },\n  {\n    \"name\": \"clinical_result.full_article_link\",\n    \"description\": \"临床结果论文的URL\"\n  },\n  {\n    \"name\": \"clinical_result.group_count\",\n    \"description\": \"临床试验的受试者入组人数\"\n  },\n  {\n    \"name\": \"clinical_result.inclusion_criteria\",\n    \"description\": \"临床试验的试验设计，以图片的形式存在；可以直接展示\"\n  },\n  {\n    \"name\": \"clinical_result.indication_detail\",\n    \"description\": \"临床试验的适应症原文描述\"\n  },\n  {\n    \"name\": \"clinical_result.indication_name\",\n    \"description\": \"标准疾病中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.indication_name_en\",\n    \"description\": \"标准疾病英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.indication_type_cn\",\n    \"description\": \"可枚举字段。标准疾病所在的疾病领域\"\n  },\n  {\n    \"name\": \"clinical_result.journal\",\n    \"description\": \"可枚举字段。临床结果论文发表的期刊/会议名称\"\n  },\n  {\n    \"name\": \"clinical_result.key_evidence\",\n    \"description\": \"可枚举字段。由于一个临床试验可能发表多次结果信息，故选取出了一条结果作为关键结果。若该试验已支持获批，则选取其第一次发表主要终点结果的证据；若该试验未支持获批，则选取其最新一次发表的重要结果（排除亚组分析、事后分析等）\"\n  },\n  {\n    \"name\": \"clinical_result.layer_factor\",\n    \"description\": \"临床试验的分层因素\"\n  },\n  {\n    \"name\": \"clinical_result.lba\",\n    \"description\": \"可枚举字段。临床结果是否是最新突破性摘要（Late-Breaking Abstract）\"\n  },\n  {\n    \"name\": \"clinical_result.multi_center\",\n    \"description\": \"可枚举字段。临床试验的研究中心范围\"\n  },\n  {\n    \"name\": \"clinical_result.paper_release_time\",\n    \"description\": \"时间戳。临床结果论文的发表日期\"\n  },\n  {\n    \"name\": \"clinical_result.paper_title\",\n    \"description\": \"临床结果论文的标题\"\n  },\n  {\n    \"name\": \"clinical_result.participant_flow\",\n    \"description\": \"临床试验的participant flow，以图片的形式存在；可以直接展示\"\n  },\n  {\n    \"name\": \"clinical_result.pathology_cn\",\n    \"description\": \"临床试验的病理中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.pathology_en\",\n    \"description\": \"临床试验的病理英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.patient_baseline_cn\",\n    \"description\": \"临床试验的基线特征中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.patient_baseline_en\",\n    \"description\": \"临床试验的基线特征英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.pm_id\",\n    \"description\": \"通用ID字段。以这个临床结果发表的论文在PubMed中的编码ID\"\n  },\n  {\n    \"name\": \"clinical_result.positive_placebo_control\",\n    \"description\": \"可枚举字段。临床结果中的对照是阳性对照还是安慰剂对照\"\n  },\n  {\n    \"name\": \"clinical_result.precision_medicine_cn\",\n    \"description\": \"临床试验的人群疾病特征中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.precision_medicine_en\",\n    \"description\": \"临床试验的人群疾病特征英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.primary_endpoint_all_name\",\n    \"description\": \"临床结果的主要终点各种名称集合，多用于检索\"\n  },\n  {\n    \"name\": \"clinical_result.primary_endpoint_cn\",\n    \"description\": \"临床结果的主要终点中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.primary_endpoint_en\",\n    \"description\": \"临床结果的主要终点英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.projects\",\n    \"description\": \"临床试验信息，嵌套字段，其中包含如下子层级：\\n【name】projects.group_id，【description】临床试验ID；\\n【name】projects.associate_ids，【description】临床试验编号/登记号；\\n【name】projects.company_ids，【description】临床试验的申办方ID；\\n【name】projects.company_name_cn，【description】临床试验的申办方中文名称；\\n【name】projects.company_name_en，【description】临床试验的申办方英文名称；\\n【name】projects.company_all_name，【description】临床试验的申办方名称集合，多用于检索；\\n【name】projects.co_ids，【description】临床试验的合作方ID；\\n【name】projects.co_name_cn，【description】临床试验的合作方中文名称；\\n【name】projects.co_name_en，【description】临床试验的合作方英文名称；\\n【name】projects.co_all_name，【description】临床试验的合作方名称集合，多用于检索；\\n【name】projects.company_area，【description】临床试验的申办方所在的国家或地区；\\n【name】projects.initiation_type，【description】可枚举字段。临床试验是IST(企业发起)还是IIT(研究者发起)的；\\n【name】projects.country_names，【description】临床试验的开展国家或地区；\\n【name】projects.pivotal_ids，【description】可枚举字段。临床试验是否是注册性临床；\\n【name】projects.ma_indication，【description】可枚举字段。临床试验是否是支持获批临床，支持药物进行获批（包括首次上市申请和补充申请）的关键临床试验所对应的所有临床结果均会被打上【获批】标签。；\\n【name】projects.guideline_support，【description】可枚举字段。临床试验是否是指南推荐临床。\"\n  },\n  {\n    \"name\": \"clinical_result.randomized\",\n    \"description\": \"可枚举字段。临床研究的随机化方式\"\n  },\n  {\n    \"name\": \"clinical_result.random_ratio\",\n    \"description\": \"临床试验的随机比例\"\n  },\n  {\n    \"name\": \"clinical_result.study_results\",\n    \"description\": \"临床结果的详细信息，嵌套字段，其中包含如下子层级：\\n【name】study_results.arm_type，【description】标注结果值的类型，single指结果值仅当前队列arm_id有效（这种情况下arm_id不为空，arm_ids为空），relative指对多个队列arm_ids的对比值有效（这种情况下arm_id为空，arm_ids不为空），all指对所有arm_id都有效（这种情况下没有特定的arm_id）；\\n【name】study_results.arm_ids，【description】对比结果中参与对比的队列ID；\\n【name】study_results.arm_id，【description】单一队列结果中的队列ID；\\n【name】study_results.endpoint_id，【description】终点指标ID；\\n【name】study_results.endpoint_label，【description】终点指标描述，与endpoint_id对应的名称共同构成终点指标；\\n【name】study_results.endpoint_type，【description】可枚举字段。终点指标类型，分为主要终点、次要终点、不区分类型终点（值为空时）；\\n【name】study_results.result，【description】当前队列在当前终点指标下的结果值；\\n【name】study_results.compare_result，【description】对比队列在当前终点指标下的对比结果值；\\n【name】study_results.result_unit，【description】结果值的计数单位，即result或compare_result的单位；\\n【name】study_results.outcome_p_value，【description】当前队列在当前终点指标下的P值；\\n【name】study_results.p_value，【description】对比队列在当前终点指标下的P值；\\n【name】study_results.outcome_ci，【description】当前队列在当前终点指标下的结果置信区间；\\n【name】study_results.compare_result_ci，【description】对比队列在当前终点指标下的对比结果的置信区间；\\n【name】study_results.hazard_ratio，【description】对比队列在当前终点指标下的hazard ratio；\\n【name】study_results.hazard_ratio_ci，【description】对比队列在当前终点指标下的hazard ratio置信区间；\\n【name】study_results.odd_ratio，【description】对比队列在当前终点指标下的odd ratio；\\n【name】study_results.odd_ratio_ci，【description】对比队列在当前终点指标下的odd ratio置信区间；\\n【name】study_results.relative_risk，【description】对比队列在当前终点指标下的relative_risk；\\n【name】study_results.relative_risk_ci，【description】对比队列在当前终点指标下的relative_risk置信区间。\"\n  },\n  {\n    \"name\": \"clinical_result.summary\",\n    \"description\": \"临床结果的summary，文本总结\"\n  },\n  {\n    \"name\": \"clinical_result.therapy_line_cn\",\n    \"description\": \"临床试验的治疗线数中文名称\"\n  },\n  {\n    \"name\": \"clinical_result.therapy_line_en\",\n    \"description\": \"临床试验的治疗线数英文名称\"\n  },\n  {\n    \"name\": \"clinical_result.trial_abbreviation\",\n    \"description\": \"可枚举字段。临床试验简称，可以具体的指代一个临床试验\"\n  },\n  {\n    \"name\": \"clinical_result.trial_control\",\n    \"description\": \"临床试验的对照标签\"\n  },\n  {\n    \"name\": \"company.company_category\",\n    \"description\": \"公司类型\"\n  },\n  {\n    \"name\": \"company.company_type\",\n    \"description\": \"数据类型，集团 or 企业\"\n  },\n  {\n    \"name\": \"company.is_ct\",\n    \"description\": \"是否为临床试验使用的公司词条\"\n  },\n  {\n    \"name\": \"company.is_important_corp\",\n    \"description\": \"是否为创新药管线drug_earth使用的公司词条\"\n  },\n  {\n    \"name\": \"company.official_website\",\n    \"description\": \"公司官网地址\"\n  },\n  {\n    \"name\": \"company.short_name\",\n    \"description\": \"企业标准中文简称，用于展示\"\n  },\n  {\n    \"name\": \"company.short_name_en\",\n    \"description\": \"企业标准英文简称，用于展示\"\n  },\n  {\n    \"name\": \"target.name_short\",\n    \"description\": \"靶点简称，用于展示\"\n  },\n  {\n    \"name\": \"target.parent_target\",\n    \"description\": \"上级靶点ID\"\n  },\n  {\n    \"name\": \"indication.name\",\n    \"description\": \"疾病中文名称\"\n  },\n  {\n    \"name\": \"indication.name_en\",\n    \"description\": \"疾病英文名称\"\n  },\n  {\n    \"name\": \"indication.parent_indication\",\n    \"description\": \"上级疾病ID\"\n  },\n  {\n    \"name\": \"biomarker.biomarker\",\n    \"description\": \"生物标记物英文标准名称\"\n  },\n  {\n    \"name\": \"biomarker.name\",\n    \"description\": \"生物标记物中文标准名称\"\n  },\n  {\n    \"name\": \"clinical_stage.stage\",\n    \"description\": \"临床分期中文标准名称\"\n  },\n  {\n    \"name\": \"clinical_stage.stage_en\",\n    \"description\": \"临床分期英文标准名称\"\n  },\n  {\n    \"name\": \"therapy_label.name\",\n    \"description\": \"治疗线程中文标准名称\"\n  },\n  {\n    \"name\": \"therapy_label.name_en\",\n    \"description\": \"治疗线程英文标准名称\"\n  },\n  {\n    \"name\": \"clinical_endpoint.endpoint\",\n    \"description\": \"终点中文描述\"\n  },\n  {\n    \"name\": \"clinical_endpoint.endpoint_attr\",\n    \"description\": \"终点属性\"\n  },\n  {\n    \"name\": \"clinical_endpoint.endpoint_en\",\n    \"description\": \"终点英文描述\"\n  },\n  {\n    \"name\": \"clinical_endpoint.endpoint_short\",\n    \"description\": \"终点简称，在中英文环境下都优先展示\"\n  },\n  {\n    \"name\": \"modality.name\",\n    \"description\": \"modality中文名称\"\n  },\n  {\n    \"name\": \"modality.name_en\",\n    \"description\": \"modality英文名称\"\n  },\n  {\n    \"name\": \"modality.parent_moa\",\n    \"description\": \"modality 的父级 ID\"\n  }\n]\n            ",
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "type": "object"
}
```

## 4. `selected_fields` 字段白名单（权威真源）

以下 4.1 / 4.2 由平台 `selected_fields` 的完整描述机械展开；原始描述可用 `toolsmith-publish tools --schema <tool>` 导出。

### 4.1 ALLOWED_FIELD_NAMES（73 个，逐字复制）

- `clinical_result.abbreviation_label`
- `clinical_result.abstract_text`
- `clinical_result.arms`
- `clinical_result.baseline_characteristics`
- `clinical_result.biomarker_cn`
- `clinical_result.biomarker_en`
- `clinical_result.blinded`
- `clinical_result.clinical_stage_cn`
- `clinical_result.clinical_stage_en`
- `clinical_result.doi`
- `clinical_result.evaluation`
- `clinical_result.evidence_source`
- `clinical_result.extra_esid`
- `clinical_result.full_article_link`
- `clinical_result.group_count`
- `clinical_result.inclusion_criteria`
- `clinical_result.indication_detail`
- `clinical_result.indication_name`
- `clinical_result.indication_name_en`
- `clinical_result.indication_type_cn`
- `clinical_result.journal`
- `clinical_result.key_evidence`
- `clinical_result.layer_factor`
- `clinical_result.lba`
- `clinical_result.multi_center`
- `clinical_result.paper_release_time`
- `clinical_result.paper_title`
- `clinical_result.participant_flow`
- `clinical_result.pathology_cn`
- `clinical_result.pathology_en`
- `clinical_result.patient_baseline_cn`
- `clinical_result.patient_baseline_en`
- `clinical_result.pm_id`
- `clinical_result.positive_placebo_control`
- `clinical_result.precision_medicine_cn`
- `clinical_result.precision_medicine_en`
- `clinical_result.primary_endpoint_all_name`
- `clinical_result.primary_endpoint_cn`
- `clinical_result.primary_endpoint_en`
- `clinical_result.projects`
- `clinical_result.randomized`
- `clinical_result.random_ratio`
- `clinical_result.study_results`
- `clinical_result.summary`
- `clinical_result.therapy_line_cn`
- `clinical_result.therapy_line_en`
- `clinical_result.trial_abbreviation`
- `clinical_result.trial_control`
- `company.company_category`
- `company.company_type`
- `company.is_ct`
- `company.is_important_corp`
- `company.official_website`
- `company.short_name`
- `company.short_name_en`
- `target.name_short`
- `target.parent_target`
- `indication.name`
- `indication.name_en`
- `indication.parent_indication`
- `biomarker.biomarker`
- `biomarker.name`
- `clinical_stage.stage`
- `clinical_stage.stage_en`
- `therapy_label.name`
- `therapy_label.name_en`
- `clinical_endpoint.endpoint`
- `clinical_endpoint.endpoint_attr`
- `clinical_endpoint.endpoint_en`
- `clinical_endpoint.endpoint_short`
- `modality.name`
- `modality.name_en`
- `modality.parent_moa`

### 4.2 ALLOWED_FIELDS 字段含义（73 条）

| 字段 | 含义 |
| --- | --- |
| `clinical_result.abbreviation_label` | 可枚举字段。临床结果的评价类型 |
| `clinical_result.abstract_text` | 临床结果来源的源文本信息 |
| `clinical_result.arms` | 临床试验的队列信息，嵌套字段，其中包含如下子层级： 【name】arms.type_revised，【description】可枚举字段。队列类型（试验组/对照组）； 【name】arms.therapeutic_schedule_id，【description】队列的治疗方案ID； 【name】arms.therapeutic_schedule_name_cn，【description】队列的治疗方案中文描述； 【name】arms.therapeutic_schedule_name_en，【description】队列的治疗方案英文描述； 【name】arms.therapeutic_schedule_text_cn，【description】队列的治疗方案中文描述文本，therapeutic_schedule_name_cn为空时补充使用； 【name】arms.therapeutic_schedule_text_en，【description】队列的治疗方案英文描述文本，therapeutic_schedule_name_en为空时补充使用； 【name】arms.drug_earth_ids，【description】队列治疗方案中的药品ID，为arms.drugs.drug_earth_id的集合； 【name】arms.drug_count，【description】队列治疗方案中的药品数量，即drug_earth_ids的个数； 【name】arms.mono_or_combo，【description】可枚举字段。临床试验为联用治疗还是单药治疗； 【name】arms.drugs，【description】队列中药品及药品特征的详细信息，嵌套字段，其中包含如下子层级： 【name】arms.drugs.drug_earth_id，【description】药品ID； 【name】arms.drugs.is_primary_drug，【description】该药品是否为主试验药； 【name】arms.drugs.drug_earth_name_cn，【description】药品中文名称； 【name】arms.drugs.drug_earth_name_en，【description】药品英文名称； 【name】arms.drugs.drug_earth_all_name，【description】药品名称集合，在药品实体标准化时通常使用这个字段； 【name】arms.drugs.target_ids，【description】药品的靶点ID； 【name】arms.drugs.target_count，【description】药品的靶点数量； 【name】arms.drugs.target_name，【description】药品的靶点名称； 【name】arms.drugs.target_all_name，【description】药品的靶点名称集合，在靶点实体标准化时通常使用这个字段； 【name】arms.drugs.drug_type_1，【description】可枚举字段。药品的创新类型； 【name】arms.drugs.drug_type_2，【description】可枚举字段。药品的药品类别； 【name】arms.drugs.moa_ids，【description】Modality ID； 【name】arms.drugs.moa_name_cn，【description】Modality 中文名称； 【name】arms.drugs.moa_name_en，【description】Modality 英文名称； 【name】arms.drugs.latest_phase，【description】可枚举字段。药品的全球最高研发阶段； 【name】arms.drugs.latest_phase_cn，【description】可枚举字段。药品的中国最高研发阶段； 【name】arms.drugs.research_institute_ids，【description】药品研发机构ID； 【name】arms.drugs.research_institute_names_cn，【description】药品研发机构中文名称； 【name】arms.drugs.research_institute_names_en，【description】药品研发机构英文名称； 【name】arms.drugs.research_institute_all_names，【description】药品研发机构名称集合，在药品研发机构实体标准化时通常使用这个字段； 【name】arms.drugs.research_institute_area，【description】药品研发机构国家/地区。 |
| `clinical_result.baseline_characteristics` | 临床结果的baseline characteristics，以图片的形式存在；可以直接展示 |
| `clinical_result.biomarker_cn` | 临床试验的生物标记物中文名称 |
| `clinical_result.biomarker_en` | 临床试验的生物标记物英文名称 |
| `clinical_result.blinded` | 可枚举字段。临床试验的盲法类型 |
| `clinical_result.clinical_stage_cn` | 临床试验的临床分期中文名称 |
| `clinical_result.clinical_stage_en` | 临床试验的临床分期英文名称 |
| `clinical_result.doi` | 通用ID字段。这篇临床结果论文的doi |
| `clinical_result.evaluation` | 可枚举字段。临床结果的总体评价，可枚举，便于检索 |
| `clinical_result.evidence_source` | 可枚举字段。临床结果的证据类型 |
| `clinical_result.extra_esid` | 临床结果的来源 ID |
| `clinical_result.full_article_link` | 临床结果论文的URL |
| `clinical_result.group_count` | 临床试验的受试者入组人数 |
| `clinical_result.inclusion_criteria` | 临床试验的试验设计，以图片的形式存在；可以直接展示 |
| `clinical_result.indication_detail` | 临床试验的适应症原文描述 |
| `clinical_result.indication_name` | 标准疾病中文名称 |
| `clinical_result.indication_name_en` | 标准疾病英文名称 |
| `clinical_result.indication_type_cn` | 可枚举字段。标准疾病所在的疾病领域 |
| `clinical_result.journal` | 可枚举字段。临床结果论文发表的期刊/会议名称 |
| `clinical_result.key_evidence` | 可枚举字段。由于一个临床试验可能发表多次结果信息，故选取出了一条结果作为关键结果。若该试验已支持获批，则选取其第一次发表主要终点结果的证据；若该试验未支持获批，则选取其最新一次发表的重要结果（排除亚组分析、事后分析等） |
| `clinical_result.layer_factor` | 临床试验的分层因素 |
| `clinical_result.lba` | 可枚举字段。临床结果是否是最新突破性摘要（Late-Breaking Abstract） |
| `clinical_result.multi_center` | 可枚举字段。临床试验的研究中心范围 |
| `clinical_result.paper_release_time` | 时间戳。临床结果论文的发表日期 |
| `clinical_result.paper_title` | 临床结果论文的标题 |
| `clinical_result.participant_flow` | 临床试验的participant flow，以图片的形式存在；可以直接展示 |
| `clinical_result.pathology_cn` | 临床试验的病理中文名称 |
| `clinical_result.pathology_en` | 临床试验的病理英文名称 |
| `clinical_result.patient_baseline_cn` | 临床试验的基线特征中文名称 |
| `clinical_result.patient_baseline_en` | 临床试验的基线特征英文名称 |
| `clinical_result.pm_id` | 通用ID字段。以这个临床结果发表的论文在PubMed中的编码ID |
| `clinical_result.positive_placebo_control` | 可枚举字段。临床结果中的对照是阳性对照还是安慰剂对照 |
| `clinical_result.precision_medicine_cn` | 临床试验的人群疾病特征中文名称 |
| `clinical_result.precision_medicine_en` | 临床试验的人群疾病特征英文名称 |
| `clinical_result.primary_endpoint_all_name` | 临床结果的主要终点各种名称集合，多用于检索 |
| `clinical_result.primary_endpoint_cn` | 临床结果的主要终点中文名称 |
| `clinical_result.primary_endpoint_en` | 临床结果的主要终点英文名称 |
| `clinical_result.projects` | 临床试验信息，嵌套字段，其中包含如下子层级： 【name】projects.group_id，【description】临床试验ID； 【name】projects.associate_ids，【description】临床试验编号/登记号； 【name】projects.company_ids，【description】临床试验的申办方ID； 【name】projects.company_name_cn，【description】临床试验的申办方中文名称； 【name】projects.company_name_en，【description】临床试验的申办方英文名称； 【name】projects.company_all_name，【description】临床试验的申办方名称集合，多用于检索； 【name】projects.co_ids，【description】临床试验的合作方ID； 【name】projects.co_name_cn，【description】临床试验的合作方中文名称； 【name】projects.co_name_en，【description】临床试验的合作方英文名称； 【name】projects.co_all_name，【description】临床试验的合作方名称集合，多用于检索； 【name】projects.company_area，【description】临床试验的申办方所在的国家或地区； 【name】projects.initiation_type，【description】可枚举字段。临床试验是IST(企业发起)还是IIT(研究者发起)的； 【name】projects.country_names，【description】临床试验的开展国家或地区； 【name】projects.pivotal_ids，【description】可枚举字段。临床试验是否是注册性临床； 【name】projects.ma_indication，【description】可枚举字段。临床试验是否是支持获批临床，支持药物进行获批（包括首次上市申请和补充申请）的关键临床试验所对应的所有临床结果均会被打上【获批】标签。； 【name】projects.guideline_support，【description】可枚举字段。临床试验是否是指南推荐临床。 |
| `clinical_result.randomized` | 可枚举字段。临床研究的随机化方式 |
| `clinical_result.random_ratio` | 临床试验的随机比例 |
| `clinical_result.study_results` | 临床结果的详细信息，嵌套字段，其中包含如下子层级： 【name】study_results.arm_type，【description】标注结果值的类型，single指结果值仅当前队列arm_id有效（这种情况下arm_id不为空，arm_ids为空），relative指对多个队列arm_ids的对比值有效（这种情况下arm_id为空，arm_ids不为空），all指对所有arm_id都有效（这种情况下没有特定的arm_id）； 【name】study_results.arm_ids，【description】对比结果中参与对比的队列ID； 【name】study_results.arm_id，【description】单一队列结果中的队列ID； 【name】study_results.endpoint_id，【description】终点指标ID； 【name】study_results.endpoint_label，【description】终点指标描述，与endpoint_id对应的名称共同构成终点指标； 【name】study_results.endpoint_type，【description】可枚举字段。终点指标类型，分为主要终点、次要终点、不区分类型终点（值为空时）； 【name】study_results.result，【description】当前队列在当前终点指标下的结果值； 【name】study_results.compare_result，【description】对比队列在当前终点指标下的对比结果值； 【name】study_results.result_unit，【description】结果值的计数单位，即result或compare_result的单位； 【name】study_results.outcome_p_value，【description】当前队列在当前终点指标下的P值； 【name】study_results.p_value，【description】对比队列在当前终点指标下的P值； 【name】study_results.outcome_ci，【description】当前队列在当前终点指标下的结果置信区间； 【name】study_results.compare_result_ci，【description】对比队列在当前终点指标下的对比结果的置信区间； 【name】study_results.hazard_ratio，【description】对比队列在当前终点指标下的hazard ratio； 【name】study_results.hazard_ratio_ci，【description】对比队列在当前终点指标下的hazard ratio置信区间； 【name】study_results.odd_ratio，【description】对比队列在当前终点指标下的odd ratio； 【name】study_results.odd_ratio_ci，【description】对比队列在当前终点指标下的odd ratio置信区间； 【name】study_results.relative_risk，【description】对比队列在当前终点指标下的relative_risk； 【name】study_results.relative_risk_ci，【description】对比队列在当前终点指标下的relative_risk置信区间。 |
| `clinical_result.summary` | 临床结果的summary，文本总结 |
| `clinical_result.therapy_line_cn` | 临床试验的治疗线数中文名称 |
| `clinical_result.therapy_line_en` | 临床试验的治疗线数英文名称 |
| `clinical_result.trial_abbreviation` | 可枚举字段。临床试验简称，可以具体的指代一个临床试验 |
| `clinical_result.trial_control` | 临床试验的对照标签 |
| `company.company_category` | 公司类型 |
| `company.company_type` | 数据类型，集团 or 企业 |
| `company.is_ct` | 是否为临床试验使用的公司词条 |
| `company.is_important_corp` | 是否为创新药管线drug_earth使用的公司词条 |
| `company.official_website` | 公司官网地址 |
| `company.short_name` | 企业标准中文简称，用于展示 |
| `company.short_name_en` | 企业标准英文简称，用于展示 |
| `target.name_short` | 靶点简称，用于展示 |
| `target.parent_target` | 上级靶点ID |
| `indication.name` | 疾病中文名称 |
| `indication.name_en` | 疾病英文名称 |
| `indication.parent_indication` | 上级疾病ID |
| `biomarker.biomarker` | 生物标记物英文标准名称 |
| `biomarker.name` | 生物标记物中文标准名称 |
| `clinical_stage.stage` | 临床分期中文标准名称 |
| `clinical_stage.stage_en` | 临床分期英文标准名称 |
| `therapy_label.name` | 治疗线程中文标准名称 |
| `therapy_label.name_en` | 治疗线程英文标准名称 |
| `clinical_endpoint.endpoint` | 终点中文描述 |
| `clinical_endpoint.endpoint_attr` | 终点属性 |
| `clinical_endpoint.endpoint_en` | 终点英文描述 |
| `clinical_endpoint.endpoint_short` | 终点简称，在中英文环境下都优先展示 |
| `modality.name` | modality中文名称 |
| `modality.name_en` | modality英文名称 |
| `modality.parent_moa` | modality 的父级 ID |

### 4.3 嵌套返回结构要点

`arms[]` / `projects` / `company` / `indication` / `target` 等嵌套字段的取值路径以 4.2 的描述为准；实体 ID 路径见 Skill 的 `references/entity-inline-reference.md`。

## 5. MCP 调用返回封装（平台通用）

```text
content      array     The result content of the tool call
content[]    object    Text or image content
isError      boolean   Whether the tool call failed
```

