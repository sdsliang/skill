# pharmcube-query-clinical-result-with-params — Tool Schema 存档

> 用途：v0.12 输入契约（附件 → esid + params tool）的**权威真源**。
> 本文件由用户粘贴的运行时 tool schema 建立；`selected_fields` 必须精确匹配此处列出的字段名。

## 1. 工具元信息

- MCP 工具名：`pharmcube-query-clinical-result-with-params`
- 数据来源：医药魔方 TrialiCube（`clinical_trial_result_structured`）
- 过滤：给定参数值精确过滤；`extra_esids` = 按临床结果 ID 精确过滤
- （用户粘贴 schema 全文，如下 ↓）

---

/tools/pharmcube-query-clinical-result-with-params

Request Body
trial_id
string
临床试验注册/登记号，如：'ChiCTR2100043573'


extra_esids
array
临床结果的ID列表，用于精确过滤

extra_esids[]
string

drug_names
array
药品名称列表，如：['阿司匹林']

drug_names[]
string

disease_names
array
疾病名称列表，如：['非小细胞肺癌']

disease_names[]
string

target_names
array
靶点名称列表，如：['EGFR']

target_names[]
string

company_names
array
公司/申办方机构名称列表，如：["恒瑞医药"]

company_names[]
string
modality
string
治疗方式/手段（MOA），如：'单抗'

global_highest_phase
string
最高研发阶段(全球), 可选值：临床前, 申报临床, I期临床, I/II期临床, II期临床, II/III期临床, III期临床, 申请上市, 批准上市

global_highest_phase_excluded
string
最高研发阶段(全球)排除值, 可选值：临床前, 申报临床, I期临床, I/II期临床, II期临床, II/III期临床, III期临床, 申请上市, 批准上市

therapy_line
string
治疗线程，如：'一线治疗'

evidence_type
string
证据类型，可选值：["BE","Phase III","系统评价","Ⅱ期临床试验","前瞻性研究","Other","Phase II/III","IIb/III期临床试验","队列研究","Ⅰ期临床试验","Phase I","汇总分析","Phase I/II","荟萃分析","Not Applicable","探索性试验","回顾性研究","真实世界研究","Phase IV","Phase II"]

initiation_type
string
申办类型，可选值：["IIT", "IST"]

meeting_tags
string
期刊/会议名称，如：'ASCO'

child_disease_included
boolean
检索的疾病是否要涵盖其所有子疾病，默认为是

child_target_included
boolean
检索的靶点是否要涵盖其所有子靶点，默认为是

child_company_included
boolean
检索的公司/申办方机构是否要涵盖其所有子公司，默认为是

child_modality_included
boolean
检索的modality是否要涵盖其所有子modality，默认为是


selected_fields
array

`selected_fields` 必须是字段名字符串数组，例如：["clinical_trial_project.nct_id", "company.company_name_cn"]。
严格遵守以下规则：
1. 阅读 ALLOWED_FIELDS，通过字段描述得知其含义并选择你所需要的字段。
1. 字段名只能从 ALLOWED_FIELD_NAMES 中逐字复制，大小写必须完全一致。
2. `selected_fields` 不能为空且每项都必须是 ALLOWED_FIELD_NAMES 中的完整字符串，不能填描述文本。

ALLOWED_FIELD_NAMES:
[
"clinical_result.abbreviation_label",
"clinical_result.abstract_text",
"clinical_result.arms",
"clinical_result.baseline_characteristics",
"clinical_result.biomarker_cn",
"clinical_result.biomarker_en",
"clinical_result.blinded",
"clinical_result.clinical_stage_cn",
"clinical_result.clinical_stage_en",
"clinical_result.doi",
"clinical_result.evaluation",
"clinical_result.evidence_source",
"clinical_result.extra_esid",
"clinical_result.full_article_link",
"clinical_result.group_count",
"clinical_result.inclusion_criteria",
"clinical_result.indication_detail",
"clinical_result.indication_name",
"clinical_result.indication_name_en",
"clinical_result.indication_type_cn",
"clinical_result.journal",
"clinical_result.key_evidence",
"clinical_result.layer_factor",
"clinical_result.lba",
"clinical_result.multi_center",
"clinical_result.paper_release_time",
"clinical_result.paper_title",
"clinical_result.participant_flow",
"clinical_result.pathology_cn",
"clinical_result.pathology_en",
"clinical_result.patient_baseline_cn",
"clinical_result.patient_baseline_en",
"clinical_result.pm_id",
"clinical_result.positive_placebo_control",
"clinical_result.precision_medicine_cn",
"clinical_result.precision_medicine_en",
"clinical_result.primary_endpoint_all_name",
"clinical_result.primary_endpoint_cn",
"clinical_result.primary_endpoint_en",
"clinical_result.projects",
"clinical_result.randomized",
"clinical_result.random_ratio",
"clinical_result.study_results",
"clinical_result.summary",
"clinical_result.therapy_line_cn",
"clinical_result.therapy_line_en",
"clinical_result.trial_abbreviation",
"clinical_result.trial_control",
"company.company_category",
"company.company_type",
"company.is_ct",
"company.is_important_corp",
"company.official_website",
"company.short_name",
"company.short_name_en",
"target.name_short",
"target.parent_target",
"indication.name",
"indication.name_en",
"indication.parent_indication",
"biomarker.biomarker",
"biomarker.name",
"clinical_stage.stage",
"clinical_stage.stage_en",
"therapy_label.name",
"therapy_label.name_en",
"clinical_endpoint.endpoint",
"clinical_endpoint.endpoint_attr",
"clinical_endpoint.endpoint_en",
"clinical_endpoint.endpoint_short",
"modality.name",
"modality.name_en",
"modality.parent_moa"
]

ALLOWED_FIELDS (格式：[{"name":"字段名", "description":"字段描述"}, ...]):(json)
[
{
"name": "clinical_result.abbreviation_label",
"description": "可枚举字段。临床结果的评价类型"
},
{
"name": "clinical_result.abstract_text",
"description": "临床结果来源的源文本信息"
},
{
"name": "clinical_result.arms",
"description": "临床试验的队列信息，嵌套字段，其中包含如下子层级：\n【name】arms.type_revised，【description】可枚举字段。队列类型（试验组/对照组）；\n【name】arms.therapeutic_schedule_id，【description】队列的治疗方案ID；\n【name】arms.therapeutic_schedule_name_cn，【description】队列的治疗方案中文描述；\n【name】arms.therapeutic_schedule_name_en，【description】队列的治疗方案英文描述；\n【name】arms.therapeutic_schedule_text_cn，【description】队列的治疗方案中文描述文本，therapeutic_schedule_name_cn为空时补充使用；\n【name】arms.therapeutic_schedule_text_en，【description】队列的治疗方案英文描述文本，therapeutic_schedule_name_en为空时补充使用；\n【name】arms.drug_earth_ids，【description】队列治疗方案中的药品ID，为arms.drugs.drug_earth_id的集合；\n【name】arms.drug_count，【description】队列治疗方案中的药品数量，即drug_earth_ids的个数；\n【name】arms.mono_or_combo，【description】可枚举字段。临床试验为联用治疗还是单药治疗；\n【name】arms.drugs，【description】队列中药品及药品特征的详细信息，嵌套字段，其中包含如下子层级：\n【name】arms.drugs.drug_earth_id，【description】药品ID；\n【name】arms.drugs.is_primary_drug，【description】该药品是否为主试验药；\n【name】arms.drugs.drug_earth_name_cn，【description】药品中文名称；\n【name】arms.drugs.drug_earth_name_en，【description】药品英文名称；\n【name】arms.drugs.drug_earth_all_name，【description】药品名称集合，在药品实体标准化时通常使用这个字段；\n【name】arms.drugs.target_ids，【description】药品的靶点ID；\n【name】arms.drugs.target_count，【description】药品的靶点数量；\n【name】arms.drugs.target_name，【description】药品的靶点名称；\n【name】arms.drugs.target_all_name，【description】药品的靶点名称集合，在靶点实体标准化时通常使用这个字段；\n【name】arms.drugs.drug_type_1，【description】可枚举字段。药品的创新类型；\n【name】arms.drugs.drug_type_2，【description】可枚举字段。药品的药品类别；\n【name】arms.drugs.moa_ids，【description】Modality ID；\n【name】arms.drugs.moa_name_cn，【description】Modality 中文名称；\n【name】arms.drugs.moa_name_en，【description】Modality 英文名称；\n【name】arms.drugs.latest_phase，【description】可枚举字段。药品的全球最高研发阶段；\n【name】arms.drugs.latest_phase_cn，【description】可枚举字段。药品的中国最高研发阶段；\n【name】arms.drugs.research_institute_ids，【description】药品研发机构ID；\n【name】arms.drugs.research_institute_names_cn，【description】药品研发机构中文名称；\n【name】arms.drugs.research_institute_names_en，【description】药品研发机构英文名称；\n【name】arms.drugs.research_institute_all_names，【description】药品研发机构名称集合，在药品研发机构实体标准化时通常使用这个字段；\n【name】arms.drugs.research_institute_area，【description】药品研发机构国家/地区。"
},
{
"name": "clinical_result.baseline_characteristics",
"description": "临床结果的baseline characteristics，以图片的形式存在；可以直接展示"
},
{
"name": "clinical_result.biomarker_cn",
"description": "临床试验的生物标记物中文名称"
},
{
"name": "clinical_result.biomarker_en",
"description": "临床试验的生物标记物英文名称"
},
{
"name": "clinical_result.blinded",
"description": "可枚举字段。临床试验的盲法类型"
},
{
"name": "clinical_result.clinical_stage_cn",
"description": "临床试验的临床分期中文名称"
},
{
"name": "clinical_result.clinical_stage_en",
"description": "临床试验的临床分期英文名称"
},
{
"name": "clinical_result.doi",
"description": "通用ID字段。这篇临床结果论文的doi"
},
{
"name": "clinical_result.evaluation",
"description": "可枚举字段。临床结果的总体评价，可枚举，便于检索"
},
{
"name": "clinical_result.evidence_source",
"description": "可枚举字段。临床结果的证据类型"
},
{
"name": "clinical_result.extra_esid",
"description": "临床结果的id"
},
{
"name": "clinical_result.full_article_link",
"description": "临床结果论文的URL"
},
{
"name": "clinical_result.group_count",
"description": "临床试验的受试者入组人数"
},
{
"name": "clinical_result.inclusion_criteria",
"description": "临床试验的试验设计，以图片的形式存在；可以直接展示"
},
{
"name": "clinical_result.indication_detail",
"description": "临床试验的适应症原文描述"
},
{
"name": "clinical_result.indication_name",
"description": "标准疾病中文名称"
},
{
"name": "clinical_result.indication_name_en",
"description": "标准疾病英文名称"
},
{
"name": "clinical_result.indication_type_cn",
"description": "可枚举字段。标准疾病所在的疾病领域"
},
{
"name": "clinical_result.journal",
"description": "可枚举字段。临床结果论文发表的期刊/会议名称"
},
{
"name": "clinical_result.key_evidence",
"description": "可枚举字段。由于一个临床试验可能发表多次结果信息，故选取出了一条结果作为关键结果。若该试验已支持获批，则选取其第一次发表主要终点结果的证据；若该试验未支持获批，则选取其最新一次发表的重要结果（排除亚组分析、事后分析等）"
},
{
"name": "clinical_result.layer_factor",
"description": "临床试验的分层因素"
},
{
"name": "clinical_result.lba",
"description": "可枚举字段。临床结果是否是最新突破性摘要（Late-Breaking Abstract）"
},
{
"name": "clinical_result.multi_center",
"description": "可枚举字段。临床试验的研究中心范围"
},
{
"name": "clinical_result.paper_release_time",
"description": "时间戳。临床结果论文的发表日期"
},
{
"name": "clinical_result.paper_title",
"description": "临床结果论文的标题"
},
{
"name": "clinical_result.participant_flow",
"description": "临床试验的participant flow，以图片的形式存在；可以直接展示"
},
{
"name": "clinical_result.pathology_cn",
"description": "临床试验的病理中文名称"
},
{
"name": "clinical_result.pathology_en",
"description": "临床试验的病理英文名称"
},
{
"name": "clinical_result.patient_baseline_cn",
"description": "临床试验的基线特征中文名称"
},
{
"name": "clinical_result.patient_baseline_en",
"description": "临床试验的基线特征英文名称"
},
{
"name": "clinical_result.pm_id",
"description": "通用ID字段。以这个临床结果发表的论文在PubMed中的编码ID"
},
{
"name": "clinical_result.positive_placebo_control",
"description": "可枚举字段。临床结果中的对照是阳性对照还是安慰剂对照"
},
{
"name": "clinical_result.precision_medicine_cn",
"description": "临床试验的人群疾病特征中文名称"
},
{
"name": "clinical_result.precision_medicine_en",
"description": "临床试验的人群疾病特征英文名称"
},
{
"name": "clinical_result.primary_endpoint_all_name",
"description": "临床结果的主要终点各种名称集合，多用于检索"
},
{
"name": "clinical_result.primary_endpoint_cn",
"description": "临床结果的主要终点中文名称"
},
{
"name": "clinical_result.primary_endpoint_en",
"description": "临床结果的主要终点英文名称"
},
{
"name": "clinical_result.projects",
"description": "临床试验信息，嵌套字段，其中包含如下子层级：\n【name】projects.group_id，【description】临床试验ID；\n【name】projects.associate_ids，【description】临床试验编号/登记号；\n【name】projects.company_ids，【description】临床试验的申办方ID；\n【name】projects.company_name_cn，【description】临床试验的申办方中文名称；\n【name】projects.company_name_en，【description】临床试验的申办方英文名称；\n【name】projects.company_all_name，【description】临床试验的申办方名称集合，多用于检索；\n【name】projects.co_ids，【description】临床试验的合作方ID；\n【name】projects.co_name_cn，【description】临床试验的合作方中文名称；\n【name】projects.co_name_en，【description】临床试验的合作方英文名称；\n【name】projects.co_all_name，【description】临床试验的合作方名称集合，多用于检索；\n【name】projects.company_area，【description】临床试验的申办方所在的国家或地区；\n【name】projects.initiation_type，【description】可枚举字段。临床试验是IST(企业发起)还是IIT(研究者发起)的；\n【name】projects.country_names，【description】临床试验的开展国家或地区；\n【name】projects.pivotal_ids，【description】可枚举字段。临床试验是否是注册性临床；\n【name】projects.ma_indication，【description】可枚举字段。临床试验是否是支持获批临床，支持药物进行获批（包括首次上市申请和补充申请）的关键临床试验所对应的所有临床结果均会被打上【获批】标签。；\n【name】projects.guideline_support，【description】可枚举字段。临床试验是否是指南推荐临床。"
},
{
"name": "clinical_result.randomized",
"description": "可枚举字段。临床研究的随机化方式"
},
{
"name": "clinical_result.random_ratio",
"description": "临床试验的随机比例"
},
{
"name": "clinical_result.study_results",
"description": "临床结果的详细信息，嵌套字段，其中包含如下子层级：\n【name】study_results.arm_type，【description】标注结果值的类型，single指结果值仅当前队列arm_id有效（这种情况下arm_id不为空，arm_ids为空），relative指对多个队列arm_ids的对比值有效（这种情况下arm_id为空，arm_ids不为空），all指对所有arm_id都有效（这种情况下没有特定的arm_id）；\n【name】study_results.arm_ids，【description】对比结果中参与对比的队列ID；\n【name】study_results.arm_id，【description】单一队列结果中的队列ID；\n【name】study_results.endpoint_id，【description】终点指标ID；\n【name】study_results.endpoint_label，【description】终点指标描述，与endpoint_id对应的名称共同构成终点指标；\n【name】study_results.endpoint_type，【description】可枚举字段。终点指标类型，分为主要终点、次要终点、不区分类型终点（值为空时）；\n【name】study_results.result，【description】当前队列在当前终点指标下的结果值；\n【name】study_results.compare_result，【description】对比队列在当前终点指标下的对比结果值；\n【name】study_results.result_unit，【description】结果值的计数单位，即result或compare_result的单位；\n【name】study_results.outcome_p_value，【description】当前队列在当前终点指标下的P值；\n【name】study_results.p_value，【description】对比队列在当前终点指标下的P值；\n【name】study_results.outcome_ci，【description】当前队列在当前终点指标下的结果置信区间；\n【name】study_results.compare_result_ci，【description】对比队列在当前终点指标下的对比结果的置信区间；\n【name】study_results.hazard_ratio，【description】对比队列在当前终点指标下的hazard ratio；\n【name】study_results.hazard_ratio_ci，【description】对比队列在当前终点指标下的hazard ratio置信区间；\n【name】study_results.odd_ratio，【description】对比队列在当前终点指标下的odd ratio；\n【name】study_results.odd_ratio_ci，【description】对比队列在当前终点指标下的odd ratio置信区间；\n【name】study_results.relative_risk，【description】对比队列在当前终点指标下的relative_risk；\n【name】study_results.relative_risk_ci，【description】对比队列在当前终点指标下的relative_risk置信区间。"
},
{
"name": "clinical_result.summary",
"description": "临床结果的summary，文本总结"
},
{
"name": "clinical_result.therapy_line_cn",
"description": "临床试验的治疗线数中文名称"
},
{
"name": "clinical_result.therapy_line_en",
"description": "临床试验的治疗线数英文名称"
},
{
"name": "clinical_result.trial_abbreviation",
"description": "可枚举字段。临床试验简称，可以具体的指代一个临床试验"
},
{
"name": "clinical_result.trial_control",
"description": "临床试验的对照标签"
},
{
"name": "company.company_category",
"description": "公司类型"
},
{
"name": "company.company_type",
"description": "数据类型，集团 or 企业"
},
{
"name": "company.is_ct",
"description": "是否为临床试验使用的公司词条"
},
{
"name": "company.is_important_corp",
"description": "是否为创新药管线drug_earth使用的公司词条"
},
{
"name": "company.official_website",
"description": "公司官网地址"
},
{
"name": "company.short_name",
"description": "企业标准中文简称，用于展示"
},
{
"name": "company.short_name_en",
"description": "企业标准英文简称，用于展示"
},
{
"name": "target.name_short",
"description": "靶点简称，用于展示"
},
{
"name": "target.parent_target",
"description": "上级靶点ID"
},
{
"name": "indication.name",
"description": "疾病中文名称"
},
{
"name": "indication.name_en",
"description": "疾病英文名称"
},
{
"name": "indication.parent_indication",
"description": "上级疾病ID"
},
{
"name": "biomarker.biomarker",
"description": "生物标记物英文标准名称"
},
{
"name": "biomarker.name",
"description": "生物标记物中文标准名称"
},
{
"name": "clinical_stage.stage",
"description": "临床分期中文标准名称"
},
{
"name": "clinical_stage.stage_en",
"description": "临床分期英文标准名称"
},
{
"name": "therapy_label.name",
"description": "治疗线程中文标准名称"
},
{
"name": "therapy_label.name_en",
"description": "治疗线程英文标准名称"
},
{
"name": "clinical_endpoint.endpoint",
"description": "终点中文描述"
},
{
"name": "clinical_endpoint.endpoint_attr",
"description": "终点属性"
},
{
"name": "clinical_endpoint.endpoint_en",
"description": "终点英文描述"
},
{
"name": "clinical_endpoint.endpoint_short",
"description": "终点简称，在中英文环境下都优先展示"
},
{
"name": "modality.name",
"description": "modality中文名称"
},
{
"name": "modality.name_en",
"description": "modality英文名称"
},
{
"name": "modality.parent_moa",
"description": "modality 的父级 ID"
}
]

selected_fields[]
string

Response

content
array
The result content of the tool call

content[]
object
Text or image content

isError
boolean
Whether the tool call failed
