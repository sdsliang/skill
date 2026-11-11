# ESMO 2026：网络议论热度 vs v0.2 推荐榜（对照检查）

> 目的：回答「网上讨论的热点，与 watchlist v0.2 的 30 条是否匹配」。
> 结论先说：**不匹配，而且根因是结构性的——候选池里一条 LBA 都没有。** 热度中心恰好就是 LBA。

## 1. 方法与口径

| 项 | 说明 |
|---|---|
| 数据源 | X（Twitter）实时检索，经 grok `/responses` + `tools:[{"type":"x_search"}]`（本机唯一可用的开放检索通道：Google/Bing/DDG/Reddit/Bluesky/Mojeek 与 esmo.org 均被墙或 Cloudflare 拦截） |
| 检索窗口 | 2026-10-15 ～ 2026-11-15（会前一周至会后三周） |
| 检索批次 | 4 个主题 query：Presidential/LBA、ADC、消化道、肺癌+其他；每次要求模型输出 **严格 JSON 数组**，逐条带 `post_url` + 原文摘录 + `trials_named` |
| 解析结果 | **23 条帖子、112 次试验/药名提及、75 个不同实体**（含药名噪音，去噪后约 40 个试验级实体） |
| 局限 | 样本量小（23 帖），不是「全网热度排名」，只能当作**方向性**证据；但 12 个 Presidential LBA 在不同批次里被反复点名，方向可信 |
| 未取到 | 阴性/失败结果专项 query（两次 502 上游错误）→ **failed 桶的热度证据缺失，本文不给结论** |

热度是「帖子数」，同一试验的多种写法（`KRASCENDO-1` / `KRAScend-1` / `KRAScendo 1`）已按试验名归并。

## 2. 热度榜（出现 ≥2 次）与推荐榜对照

| 热度 | 试验 | 会议编号 | v0.2 中的位置 |
|---:|---|---|---|
| 5 | DeLLphi-305（tarlatamab+度伐利尤单抗，ES-SCLC 一线维持） | **LBA3** | 不在池 |
| 5 | SAFFRON（奥希替尼+赛沃替尼，EGFRm MET 过表达） | **LBA6** | 不在池 |
| 4 | INTerpath-001（mRNA 新抗原 + 帕博利珠单抗，黑色素瘤辅助） | **LBA1** | 不在池 |
| 4 | VOLGA（度伐利尤单抗±曲美木单抗 + EV，MIBC 围手术期） | **LBA2** | 不在池 |
| 2 | KRASCENDO-1（divarasib vs 标准治疗，KRAS G12C NSCLC） | **LBA5** | 不在池 |
| 2 | CheckMate 8HW（纳武利尤单抗+伊匹木单抗，MSI-H/dMMR mCRC） | **LBA32** | 不在池 |
| 2 | CLARITY-Gastric01（CLDN18.2 ADC，胃癌） | **LBA7** | 不在池 |
| 2 | OptiTROP-Lung06（sac-TMT + 帕博利珠单抗，NSCLC） | **LBA66** | 不在池 |
| 2 | PANKU-Lung01 | **LBA71** | 不在池 |
| 2 | HERON-Lung01 | **LBA72** | 不在池 |
| 2 | TroFuse-005（TROP2 ADC，乳腺癌/妇科） | **LBA11** | 不在池 |
| 2 | NEOTORCH（围手术期免疫，NSCLC） | **LBA64** | 不在池 |
| 2 | BEHOLD-1（B7-H4 ADC，卵巢癌） | 1248RO（+LBA41） | 池内 `early / weak`，未入榜 |
| 2 | NATALEE（辅助 ribociclib） | 581P（+LBA25） | 池内 `pivotal / weak`，未入榜 |
| 2 | NeoCOAST-2 | 4244RO | 不在池 |
| 2 | **PERSEE**（帕博利珠单抗+化疗，PD-L1≥50% 一线 NSCLC） | 2614O | ✅ **watchlist pivotal #4** |
| 2 | **DeLLphi-304**（塔拉妥单抗，经治 SCLC） | 3808O | ✅ **watchlist pivotal #2** |
| 2 | **OptiTROP-Breast01**（芦康沙妥珠单抗，TNBC） | 4639RO | ✅ **watchlist pivotal #10** |

**命中率：3 / 18（17%）**；另有 2 个进了候选池但判 `weak` 落榜；**13 个完全不在池**，其中 **12 个是 LBA**。

## 3. 反向检查：我推荐的 30 条，网上有人聊吗

把 30 条的药物名 / 试验名 / 摘要号逐个去这 23 条帖子里找：

- **被提及：2 / 30**（tarlatamab `3808O`、sac-TMT `4639RO`）
- **零讨论：28 / 30**，其中 **early 桶 10 条全部为 0**
- 原因不是「数据不好」，而是受众：early 桶是国产一期资产（SYS6043、HS-20122、CTS3497、BG-C477…），英文肿瘤 KOL 圈基本不转一期 poster；X 的讨论量集中在 Presidential / LBA 的 III 期 OS 数据。

## 4. 根因：两个结构性缺陷

### B1（主因）候选池系统性缺失 LBA 整类

- 会议库（`medicalMeeting`）ESMO 2026 共 **91 条 LBA**，其中 **57 条**能通过 `supplement_rows()` 的全部门槛（有 Results 段、有可识别药物、能判分期）。
- 但 **532 条候选里 0 条、30 条榜单里 0 条带 LBA 编号**。
- 机制：候选池以结构化结果表为起点；LBA 在结果表侧是延迟收录的，只能走「会议库独有（`mm:` 前缀）→ 硬性只准进 early」这条补位通道，而 LBA 绝大多数是 II/III 期，被该规则挡在门外（实测放开前缀后仅 3 条落地，其余仍在 `dedupe` / 分桶环节丢失）。
- 后果：全场最重磅的 12 个 Presidential LBA **一个都不在体系内**，热度榜 12/18 落在池外。

### B2 表现层级排序把 LBA 排在普通 Oral 之后

`PRESENTATION_RANK` 给纯 `LBA<数字>`（无 O/RO 后缀）判为 `Late-breaking` = rank 3，即**低于任意普通 Oral（rank 1）与 Rapid Oral（rank 2）**：

```
presentation_of("LBA3")  -> ("Late-breaking", 3)   # DeLLphi-305，Presidential
presentation_of("2041O") -> ("Oral", 1)
```

ESMO 的编号约定里，不带后缀的 `LBA1..LBA95` 本身就是 late-breaking 主榜（Presidential / 专场口头），实际档位不低于甚至高于普通 oral。当前实现会把最重磅的一批排到阅读顺序末尾。

## 5. 建议修法（尚未实施）

1. **给 LBA 开独立通道**：`mm:` 行若 `abstract_id` 以 `LBA` 开头、且摘要含完整 Results 段与可判分期，允许进入 `pivotal` / `failed`；其余 `mm:` 行维持「只进 early」不变（原规则的用意——防止会议手册的计划性数据污染晚期桶——对非 LBA 仍然成立）。
2. **修 `PRESENTATION_RANK`**：纯 `LBA<n>` 视为 `Late-breaking Oral`（rank 1）或单列一档 rank 0，并保留 `LBA<n>P` 之类的后缀细分。
3. **supplement 输入改为会议库全量**（5810 条），`covered_titles` 从结构化表全量标题生成，避免只对已被结构化覆盖的标题做补位。

预期效果：候选池从 532 增至约 590（+57 LBA），榜单需要重新定榜——Presidential LBA 至少占走 pivotal 桶的多数席位，现有 10 条 pivotal 里约 4～5 条会被挤到候补。

## 6. 证据样例（可点开核对）

- DeLLphi-305：<https://x.com/Alfdoc2/status/2113906373633228813>、<https://x.com/youngkwangchae/status/2116495141376606578>
- INTerpath-001：<https://x.com/ProfGLongMIA/status/2114173758839890093>、<https://x.com/rodrigo_arruda/status/2120352642769813874>
- TAISHAN-301：<https://x.com/ChandrakanthMv/status/2119014349796958347>
- VOLGA：<https://x.com/SuyogCancer/status/2113767973295104023>
- 12 个 Presidential LBA 的会前盘点：<https://x.com/KolPulseAI/status/2102753873014235308>
