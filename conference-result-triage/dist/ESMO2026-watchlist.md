# ESMO 2026 会议临床结果推荐榜（三桶）

> 生成：conference-result-triage / 数据源 np_clinical `meeting_tags = "ESMO 2026"`
> 数据截止：ESMO 2026 摘要库当前快照（945 篇会议文献）
> 说明：本榜是**机器机械筛 + 逐条摘要复核**的产物，不含任何"模型自算数字"。每条的关键数字均摘自摘要原文；标「待核实」的条目表示摘要内不足以确认。

---

## 0. 口径与筛选漏斗

| 步骤 | 数量 | 说明 |
|---|---|---|
| 会议文献（np_clinical） | 945 | `base.journal.text = ESMO 2026` |
| MCP structured 拉取原始行 | 1338 | 同一 esid 多行（按 arms/endpoint 拆行） |
| 去重后 esid | 988 | |
| 排除非试验证据源 | -494 | 前瞻性研究 235、真实世界研究 210、回顾性研究 49、Not Applicable 4、汇总分析 1、未知 19 |
| 进入三桶候选 | 467 | 早期 180 / 重磅 238 / 失败 49 |
| 模型逐条复核（keep） | 206 | 其余 181 weak / 80 drop |
| 定榜 | 30 | 每桶 10 条 |

**硬规则**（写进 `scripts/triage.py`，不可协商）：

1. 真实世界 / 回顾性 / 汇总分析**不进任何桶**，单独计为 excluded。
2. **n（样本量）不作入榜门槛**，只做展示与并列时的次级排序。
3. 试验分期取自 `evidence_source`（Phase I/II/III），**不是** `clinical_stage_new`（那是疾病分期）。
4. "失败"首先由 `research_design.evaluation ∈ {不佳, 终止}` 驱动，p 值 / HR 只作佐证。
5. 模型只写"为什么上榜"的归因，**不自算** ORR/HR/PFS。

**数据类型标注**（`data_type`，规则自动打，摘要无信号则「未判定」= 待人工）：
`首次公布` / `更新-长期随访` / `亚组-二次分析` / `未判定`。
本批 467 条的分布：首次 90、更新 77、亚组 53、未判定 247。**未判定比例偏高是预期的**——ESMO 很多摘要不写明，需人工翻原文；这也是本 skill 让模型读摘要而不是只看机器分数的原因。

---

## 一、早期机会（Phase I / I-II，新机制 + 数字超预期）

| # | 试验 / 药物 | 靶点机制 | 适应症 | 期 | n | 类型 | 关键数字 |
|---|---|---|---|---|---|---|---|
| 1 | **ABBV-706** | SEZ6 ADC（Top1i payload） | R/R SCLC | I | 124 | 首次（剂量优化） | 2L+ RP3D 1.8 mg/kg（n=41）**ORR 56%、mOS 12.4 mo**；2L 亚组（n=17）**ORR 82%、mOS 14.3 mo** |
| 2 | **ZL-1310** + 阿替利珠 | DLL3 ADC | 1L ES-SCLC | I | 58 | 更新 | 双联（1.6 mg/kg + atezo，n=15）**确认 ORR 80%**；三联（+卡铂，n=13）**ORR 91%**；全剂量双联 65.9% |
| 3 | **IBI363 / TAK-928** | PD-1/IL-2α-bias 双抗融合蛋白 | 1L NSCLC；胃癌 | I | 80 / 46 | 更新 | NSCLC 三剂量组 **ORR 47.4% / 61.9% / 86.4%**；胃癌（n=35 可评估）**ORR 80%、cORR 60%**，中位随访 9.6 mo |
| 4 | **givastomig / ABL111** + nivo + mFOLFOX | CLDN18.2 × 4-1BB 双抗 | 1L 胃食管腺癌 | I | 64 | 首次 | ORR **77%**（8 mg/kg）/ **75%**（12 mg/kg）；DCR 96% / 100%；**mPFS 16.9 / 14.5 mo**（1L 胃癌 PFS 罕见地长） |
| 5 | **SHR-4849 / IDE849** | DLL3 ADC | R/R SCLC + 其他 NEC | I | 122 | 更新 | SCLC ≥1.8 mg/kg **ORR 68.3%**（确认 55.4%）、DCR 94.1%、mPFS 6.8 mo；2L **ORR 72.5%**；脑转移（n=26）**ORR 76.9%**、DCR 100% |
| 6 | **ZG005 / nilvanstomig** + 化疗±贝伐 | PD-1 × TIGIT 双抗 | 1L 宫颈癌 | I/II | 96 | 更新 | 20 mg/kg 组（n=70）**uORR 81.4%**，中位随访 9.0 mo，86.5% 鳞癌 |
| 7 | **SHR-A1811 / trastuzumab rezetecan** | HER2 ADC | HER2+ 晚期乳腺癌 | I/II | 75 | 更新 | Ph2 **ORR 83.1%**（4.8 mg/kg 组 86.4%）；**24 / 36 mo PFS 率 73.4% / 61.1%**；无 ILD、无治疗相关死亡 |
| 8 | **obrixtamig / BI 764532** | DLL3 × CD3 T 细胞衔接器 | NEC（epNEC 为主） | I | 44 | 亚组分析 | **确认 ORR 77%**（DLL3 高表达 88%）、**mPFS 7.7 mo**；CRS G1/2 59%/14%，无 G≥3 ICANS |
| 9 | **FMC-376** | 口服 KRAS G12C（ON/OFF 双态，抗前代耐药） | NSCLC 为主 | I | 62 | 首次 | NSCLC n=42，**ORR 52%**；65% 已用过 1–2 种前代 G12Ci；GI 毒性无 G≥3 |
| 10 | **SYS6043** | B7-H3 ADC | 乳腺癌（三队列） | I/II | 137 | 首次 | HR+/HER2- **ORR 45.7%**、**TNBC 70.6%**、HER2+ **71.4%**；G≥3 TRAE 仅 24.1% |

**候补（差一位）**：SKB500（B7-H3 ADC，SCLC ORR 67.2%、mPFS 7.2 mo）；JSKN033（皮下双 payload HER2 ADC，宫颈癌 ORR 52.9%）；WX390 + 特瑞普利单抗（PI3K-mTOR，宫颈癌确认 ORR 41.8%）；R2810-ONC-1901（CSCC 54 mo EFS 76.2%）。

**看点**：SCLC 的 DLL3/SEZ6/B7-H3 三条 ADC 路线同时出强数据（#1、#2、#5），是本届最密集的信号；中国资产的 PD-1/IL-2、CLDN18.2×4-1BB、PD-1×TIGIT 三个双抗在 1L 大瘤种上都给出了单臂 75%+ ORR。

---

## 二、重磅 II/III 期（随机对照，主要终点达成且有临床意义）

| # | 试验 / 药物 | 适应症 | 期 | n | 类型 | 关键数字 |
|---|---|---|---|---|---|---|
| 1 | **PERSEE**（pembro ± 铂类化疗） | PD-L1 ≥50% 晚期 NSCLC 1L | III | 321 | 首次 | **PFS 16.1 vs 6.9 mo，HR 0.56**；**OS 50.2 vs 29.9 mo**；28 家法国中心 |
| 2 | **UNION**（卡瑞利珠 + 短程放疗 + CAPOX） | 局部晚期直肠癌新辅助（pMMR/MSS 为主） | III | 231 | 首次 | **3 年 EFS 91.3% vs 77.4%，HR 0.33（95%CI 0.15–0.71），p=0.0029**；首个 LARC 新辅助免疫 III 期 |
| 3 | **OptiTROP-Breast01**（sac-TMT / SKB264） | 晚期 TNBC ≥2L | III | 263 | 更新（最终 OS） | **OS 14.7 vs 9.9 mo，HR 0.60**；24 mo OS 33.8% vs 21.4%；校正后续 ADC 后 HR 0.55 |
| 4 | **RC48-C012**（维迪西妥单抗 / DV） | HER2 低表达乳腺癌（含肝转移 BCLM） | III | 377 | 首次 | 总体 **PFS 4.67 vs 2.86 mo，HR 0.718（p=0.0061）**；**BCLM 亚组 PFS 5.62 vs 2.60，HR 0.430，ORR 44.4% vs 18.3%，OS 20.47 vs 15.84（HR 0.744）** |
| 5 | **DeLLphi-304**（tarlatamab） | 2L SCLC | III | 509 | 更新（长期随访） | **OS 13.6 vs 8.4 mo，HR 0.62**；18 mo OS 42% vs 24%；12 mo PFS 21% vs 6%；铂耐药与脑转移亚组一致获益 |
| 6 | **LIBRETTO-531**（selpercatinib） | 1L RET 突变甲状腺髓样癌 | III | 291 | 更新（最终 OS） | **3 年 PFS 75% vs 25%，HR 0.21**；**3 年 OS 92% vs 75%，HR 0.34**；PFS2 HR 0.23 |
| 7 | **FLAMES**（senaparib 维持） | 1L 卵巢癌维持 | III | 403 | 更新（48.5 mo） | **mPFS 38.7 vs 13.6 mo，HR 0.47**；BRCA 野生型 33.3 mo，HR 0.49；各预设亚组一致 |
| 8 | **COMPANION-002**（tovecimig，DLL4 × VEGF-A 双抗）+ 紫杉醇 | 2L 胆道癌 | II/III | 168 | 首次 | **ORR 17.1% vs 5.3%**；**PFS 4.7 vs 2.6 mo，HR 0.44** |
| 9 | **RINGSIDE**（γ-secretase 抑制剂） | 硬纤维瘤 | III | 156 | 更新（安全性报告） | 此前 **ORR 56% vs 9%**；本次 G≥3 AE **57% vs 17%**、80% 需减量、20% 因 AE 停药（疗效数据非本摘要新增） |
| 10 | **MANEUVER**（pimicotinib） | 腱鞘巨细胞瘤 | III | 63 | 更新（2 年） | **RECIST ORR 76.2%、TVS ORR 77.8%**，中位 DOR 未达；关节活动度/僵硬/疼痛持续改善至 2 年 |

**候补**：AGITG MASTERPLAN（胰腺癌 II 期，**OS 22 vs 14 mo**，PFS 11.9 vs 6.3）；FRUSICA-2（肾癌**老年亚组** n=75，PFS 24.87 vs 8.31，HR 0.32）；DESTINY-Gastric04（2L HER2+ 胃癌 **Q-TWiST +3.21 mo**，OS 相对获益 23.4%，为生活质量二次分析）。

**看点**：真正的"首次 III 期阳性"只有 #1 #2 #4 #8；#3 #5 #6 #7 #9 #10 都是既有试验的最终/长期分析——进榜理由是"数据成熟后结论更硬"，不是"新药"。**做投资/立项判断时，#1 #2 #4 的信息增量最大。**

---

## 三、失败的研究（III 期 / 大型随机，主要终点未达）

| # | 试验 / 药物 | 适应症 | 期 | n | 结论 |
|---|---|---|---|---|---|
| 1 | **LITESPARK-012**（pembro + lenvatinib ± belzutifan） | 1L 晚期 ccRCC | III | 1688 | 三联/双联**均未改善疗效**；因 AE 停药 **51.6% / 51.4% vs 36.2%**；G≥3 AE 87.2% / 88.7% vs 84.8% |
| 2 | **KEYNOTE-866**（围手术期 pembro + 化疗） | 肌层浸润性膀胱癌 | III | 907 | **EFS HR 0.88（p=0.1366）未达**；pCR 44.4% vs 35.8%；**OS HR 1.00**；G3-5 AE 80.2% vs 75.1% |
| 3 | **CA017-078**（新辅助 nivo + GC → 辅助 nivo） | 肌层浸润性膀胱癌 | III | 653 | **EFS HR 0.94（p=0.67）**；pCR 39.1% vs 29.6%；OS HR 0.88，均未显著 |
| 4 | **KEYNOTE-630**（辅助 pembro） | 高危皮肤鳞癌 | III | 450 | **RFS HR 0.81（95%CI 0.58–1.12）未达**；**OS HR 1.70（1.11–2.60）反向不利** |
| 5 | **LEAP-012**（lenva + pembro + TACE） | 不可切除 HCC | III | 480 | PFS 阳性但 **OS 40.4 vs 40.8 mo，HR 0.98**；G≥3 TRAE 72.2% vs 32.0% |
| 6 | **LEAP-009**（lenva + pembro） | R/M 头颈鳞癌 | II | 404 | **OS HR 1.48（1.11–1.97），研究提前停止**；本次为停药后 >16 mo 的安全性收尾 |
| 7 | **postMONARCH**（abemaciclib + 氟维司群） | HR+ HER2- 乳腺癌（CDK4/6i 后） | III | 368 | **OS 32.1 vs 24.6 mo，HR 0.80，p=0.1145 未达显著**；PFS HR 0.78（名义 p=0.039） |
| 8 | **NRG-GY020**（放疗 ± pembro） | 高中危子宫内膜癌 | III | 168 | **3 年 RFS 73% vs 70%，p=0.68 未达**；**G3/4 毒性 43% vs 15%**（获益未现、毒性翻倍） |
| 9 | **ASPIK-PRODIGE 50**（阿司匹林辅助） | PIK3CA 突变结肠癌 | III | 134 | **3 年 DFS 67.1% vs 75.1%，HR 1.28**；5 年 OS 78.9% vs 89.7%，方向不利 |
| 10 | **MITO 32** | 复发卵巢癌 | III | 68 | **提前终止**；12 mo OS 41.8% vs 52.2%（p=0.378）；G3-4 AE 14.3% vs 56.8% |

**候补**：ENGOT-en9/LEAP-001（子宫内膜癌，PFS/OS 与化疗相当，无可用预测标志物）；IDH 相关胶质母细胞瘤 II 期（n=184，12 mo PFS 22.2% vs 38.9%，实验组更差）；ARION PRODIGE 67（食管癌 II 期，PFS HR 0.92，p=0.351）。

**看点**：围手术期免疫在 MIBC 上出现**分歧**——NIAGARA（度伐利尤 + 化疗）EFS HR 0.52 阳性，而 KEYNOTE-866（pembro + 化疗）EFS HR 0.88 阴性、CA017-078（nivo + GC）EFS HR 0.94 阴性。同一治疗范式、同类人群、结论相反，这是本届最值得追问的机制/设计问题（给药时序、对照选择、pCR 与 EFS 脱节）。KEYNOTE-630 的 **OS HR 1.70** 与 LEAP-009 的 **OS HR 1.48** 是本批最强的"反向信号"，应作为安全性/超进展假说的线索而不是噪声。

---

## 四、明确排除（不进榜，单独留档）

| 类别 | 条数 | 例子 |
|---|---|---|
| 前瞻性研究（非注册试验） | 235 | 单中心前瞻队列、剂量探索非试验注册 |
| 真实世界研究 | 210 | 真实世界疗效/安全性对比 |
| 回顾性研究 | 49 | 单中心回顾、倾向评分匹配 |
| Not Applicable / 汇总分析 / 未知 | 24 | 荟萃分析、方法学摘要 |

排除原因：这些证据的**入组与终点不可比**，放进"重磅/早期"会造成与注册试验同一把尺子量不同东西。若需要，可另开一档"真实世界信号"，规则需单独定义。

---

## 五、待人工核实清单（不隐藏不确定性）

1. **数据类型**：467 条中 247 条摘要未写明"首次/更新/亚组"，本榜 30 条已人工回原文确认，其余需在正式交付前抽查。
2. **`lba` 字段全为 None**，无法用"LBA 标记"判断重磅程度——本榜未使用 LBA 作为信号，勿在其它场景假设该字段可用。
3. **统计量稀疏**：`study_results` 中仅约 5–6/10 行带 p 或 HR，多数疗效结论依赖 `abstract_text` 而非结构化字段；因此所有 p/HR 均从摘要原文抄录，**未经二次计算**。
4. **同试验多摘要**：本届同一试验常拆成"主结果 + 亚组 + 安全性"多篇（如 RINGSIDE、NIAGARA、MIRASOL），本榜按 esid 去重后保留信息量最大的一篇，**主结果篇可能落在别条**，做尽调时需回查同试验其它摘要。
5. **中国资产占比高**（早期桶 10 条中 6 条为中国原研），跨会议比较时注意样本与随访时长差异。

---

## 六、复现

```bash
# 1. 拉取（MCP structured，meeting_tags 精确匹配）
#    POST {TS_BASE}/api/tools/debug  name=pharmcube-query-clinical-result-with-params
#    arguments={"meeting_tags":"ESMO 2026","selected_fields":[...15 个字段...]}
# 2. 机械筛（去重 / 排除非试验 / 分桶 / 附非权威机器信号）
python3 scripts/triage.py --input rows.json --out-dir out --top 0
# 3. 模型逐条复核（每批 25 条摘要，只判 keep|weak|drop + 理由 + 原文证据）
#    产出 dist/esmo2026-judgements.csv（467 条全量判定）
# 4. 定榜（人工/模型合并，每桶 10 条）
```

产物：
- `dist/esmo2026-judgements.csv` — 467 条逐条判定（含 data_type、关键数字、理由）
- `dist/ESMO2026-watchlist.csv` — 本榜 30 条的机器可读版
- `dist/ESMO2026-watchlist.md` — 本文件
