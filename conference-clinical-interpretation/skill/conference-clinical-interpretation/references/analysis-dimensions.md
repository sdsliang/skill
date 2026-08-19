# 分析维度参考 (Analysis Dimensions)

本 skill 的会议解读可沿多个维度展开。以下维度参考了 ASCO 2026 的医药媒体/行业分析框架（世易医健、良医汇、丁香通、妇产科在线等），并标注**数据支持度**，避免模型臆造数据不支持的维度。

## 媒体常用分析维度（ASCO 2026 实测检索）

网络调研（Bing/搜狐/良医汇/丁香通/妇产科在线，2026 年 ASCO 年会前后）显示，主流医药媒体分析会议时常用以下框架：

1. **按报告级别**：口头报告（Oral）、快速口头（Rapid Oral）、LBA（Late-Breaking）、壁报（Poster）、临床科学研讨会（Clinical Science Symposium）、继续教育专场——媒体常用"中国学者主导入选 95 项口头/快速口头/研讨会/教育专场"这类口径。
2. **按癌种**：肺癌、乳腺癌、消化道（胃/肠/肝胆胰）、泌尿生殖（膀胱/前列腺/肾）、妇科（卵巢/宫颈/内膜）、血液、头颈等。
3. **按药物技术路线**：ADC、双抗（如 PD-1/VEGF 双抗）、免疫检查点、细胞治疗、小分子靶向等。
4. **按中国企业/中国创新药参与**：中国药企入选数量、代表性创新药（如依沃西单抗首个……）、出海/授权动态。
5. **按联合治疗策略**：免疫±化疗±靶向、围手术期/新辅助前移。
6. **按转化医学/生物标志物**：ctDNA/MRD、HRD、伴随诊断。
7. **按治疗线数前移**：晚期→早期、一线→新辅助。

## 数据支持度

| 维度 | 数据来源 | 支持度 | 备注 |
|---|---|---|---|
| 评价/结果方向 | distributions.evaluation | ✅ | 核心 |
| 阶段/疾病阶段 | distributions.trial_phase / disease_stage | ✅ | 核心 |
| 癌种/适应症 | distributions.indication | ✅ | 核心 |
| 治疗线数 | distributions.therapy_line | ✅ | 核心 |
| 终点类型 | distributions.endpoint | ✅ | 核心 |
| 生物标志物 | distributions.biomarker | ✅ | 核心 |
| 发布节奏 | distributions.release_date | ✅ | 核心 |
| 药物技术路线/机制 | drug-profiles.modality / moa_class | 🟡 | 需药物画像增强；modality 可能为空 → 用 moa_class 兜底 |
| 中国企业/中国创新药参与 | drug-profiles.companies（is_china_origin） | 🟡 | 近似推断，见 drug-enrichment.md |
| 联合治疗策略 | evidence.efficacy_text / drugs | 🟡 | 需模型从药物组合/文本归纳 |
| 报告级别（Oral/LBA/Poster） | — | ❌ | `np_clinical` 无此字段；在「信息缺口」中说明，勿臆造 |
| 申办方/公司（原始） | — | ❌ | 结构化数据无申办方字段；仅能经药物画像近似 |

## 使用原则

- **数据支持的维度**：可直接做确定性统计 + 代表性证据引用。
- **部分支持**（🟡）：先做确定性聚合（如按 modality 聚类记录数），再给代表性证据；模型负责解读，不造数字。
- **不支持**（❌）：不得当作事实输出；在「信息缺口与局限」中说明缺失原因与替代方案（如经药物画像近似）。
- 每个维度的论断都要可溯源到 `evidence_scatter[].id` 或统计文件。
