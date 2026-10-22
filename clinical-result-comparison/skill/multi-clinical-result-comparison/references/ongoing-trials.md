# 在研同类试验（尚未读出结果）

这一节回答一个结果记录回答不了的问题：**这个类里还有什么正在跑、还没读出。** 它登记的是注册事实，
不是结果，因此既不进对齐表，也不参与排序，也不构成任何证据。它和 `references/external-context.md`
的外部参照**分立**：外部参照要的是「可对齐数值」（因此天然有读出的结果），这一节要的恰恰是「还没有
结果」，两者的准入条件互斥，状态文件也不复用。

## 什么时候跑

**默认步骤，不必等用户开口**：与外部参照一起，在写结论之前做一次。用户明确说不要超出所选记录的
背景时，记 `--not-applicable --reason`。三种情况都合法，但结局必须留痕（见下）：

| 结局 | 命令 | 含义 |
| --- | --- | --- |
| 登记了在研试验 | `trial_watchlist.py … --append` | 写 `work/watchlist.json`（`state: listed`）+ 追加 `origin:watchlist` 条目 |
| 查了，没有符合条件的 | `trial_watchlist.py … --none-found` | `state: none_alignable`，不追加任何条目 |
| 这一问不适用 | `trial_watchlist.py --not-applicable --reason "…"` | `state: not_applicable`，reason ≥8 字 |

没有 `work/watchlist.json`，`check_report.py` 直接判失败；`listed` 却没追加条目、或追加了却不在正文
引用，同样判失败。**「所选集合本身就是在研资产」不是跳过理由**——正是这种情况才要登记同类对手。

## 工具与参数

工具：`pharmcube-query-clinical-trial-with-params-v2`（本项目的第二个 MCP 工具）。它的行为有几处实测
坑，写查询时必须避开：

- **`trial_phase` / `trial_status` 是单值字符串**，传数组会被 schema 拒绝；要多个分期就分别查或本地筛。
- **`trial_has_result`、`trial_therapy_line`、`drug_is_primary` 服务端过滤不可用**：`false` / `true` /
  `"否"` / `"是"` 全返回空或直接报校验错，`trial_therapy_line` 传 `一线` / `一线治疗` 也是空。
  这三项一律**本地筛**。
- **行数不是试验数**：一次按 `nct_ids` 查单个登记号可以回 630 行（药 × 终点 × 登记平台 × 时间线的
  笛卡尔展开）。永远不要写「共 N 项在研试验」，只能写去重后的试验条数。
- **`nct_ids` 里混着开发代号**（`TOPAZ-UC`、`J6E-MC-KWAN`），不能当登记号用；链接只能取
  `registry_url`。同一试验在多个平台登记时，`trial_watchlist.py` 按
  `US-ClinicalTrial → EU-EUCT → CN-CDE → JP-JRCT → IN-CTRI` 的固定优先级选一个链接。
- **日期是 epoch 毫秒**，按北京时间还原（登记日就是当地零点，用 UTC 会整体早一天）。
- 只取**试验级**字段。一旦把 `main_trial_sub_endpoint.*` 或 `main_trial_sub_timeline.*` 加进
  `selected_fields`，返回行数按子实体成倍膨胀，而这些字段这一节根本用不到。

`trial_watchlist.py` 的 `SELECTED_FIELDS` 就是这一节要用的全部字段，照抄即可，不要自己加。

## 预算

- **≤2 次** `trial-v2` 调用：一次按靶点/适应症/分期取候选，一次按需补齐（可以省略）。
- **≤5 条**登记行，超出的不写。
- 一次只加一个过滤维度；某个维度把结果打到 0 就退回上一个维度，不要叠加到「什么都没有」。

## 命令

```bash
# 1) 取候选（工具结果会落成 tool_results/pharmcube-query-clinical-trial-with-params-v2/call_*.jsonl）
python3 /workspace/skills/multi-clinical-result-comparison/scripts/trial_watchlist.py \
    --phase "Phase III" --exclude-nct NCT05611671,<已选集合里的登记号> --append \
    --refs /workspace/work/refs.json --sources-dir /workspace/work/sources
```

`--append` 才把保留的试验追加进 `work/refs.json`（`origin: watchlist`，编号接在已有 `ref_n` 之后，
不重编号），并写 `work/sources/ref_<n>.txt`。随后 `make_citations.py` 像对待任何条目一样把
`title` / `link` / `paper_release_time` 抄进 `citations.json`——**不要手写 citation**。

`--exclude-nct` 用来排除本次比较里的试验本身（它们已经有结果，属于「所选记录」）。大小写不敏感。

## 呈现口径

位置：**外部参照之后、最终结论之前**，独立一节，标题固定 `## 在研同类试验（尚未读出）`（英文
`## Ongoing same-class trials (no results yet)`）。区块首句固定：

> 本段仅登记注册信息，这些试验尚无读出结果，不构成本次比较的证据。

（英文：`Registered design only; no efficacy or safety results have been read out for these trials, so they are not evidence in this comparison.`）

每条一行，一行只讲登记事实：登记号（+ 代号）｜分期｜状态｜首次公示｜在研药物｜目标入组｜`{{ref_n}}`。
用表格承载更紧凑，允许；但**只能用这一个表，且不得包含任何结果数值**。

**禁止：**

- 预测读出时间、预测结果方向、写「有望」「预计获批」「将优于」「潜力」「威胁」——本节的每个字都必须
  是登记平台已经写下的事实（`check_report.py` 对这批词判 FAIL）；
- 把在研试验写进任何对齐表、附录、账本或图表，或让它参与排序/权重/结论；
- 在别处（正文、图、表、附录）引用 `origin:watchlist` 的 `{{ref_n}}`——只在它自己那一节里出现；
- 描述检索过程（调用了几次、用了什么工具、覆盖到什么程度）。没有符合条件的试验时**整节省略**，
  正文一个字都不提，但 `work/watchlist.json` 仍然要记 `none_alignable`。

**可以写**的是为什么这一条值得看：靶点或模态是否与所选集合重叠、分期、状态、目标入组、是否已公布
主要终点设计。这些都能从登记记录直接读到，且不构成对结果的预测。
