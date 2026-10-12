# R52：执行流程梳理与差量审校

## 假设与边界

用户授权（2026-10-12）：重新梳理累积规则，修改后测试，TS 创建新版本后真实测试。

本轮是一项整体流程重构，不把多条改动的收益分别归因。假设：统一正常执行路径与修复路径，减少候选事实整份抄写、帮助探针、报告和图表重复写入，且不削弱原文核对、数字精度、事实覆盖、引用归属与完整附录。

- 运行资产：prompt v0.16、SKILL、toolbox、file-delivery、既有 build_ledger.py。
- 冻结面：评分器、scenario a/b 事实清单、固定输入、citation renderer、runner 均未改。
- 差量审校不是自动接受候选：records 完整重审，每候选一条 keep/update/drop，additions 补充材料事实；组装 facts.json 后默认编译器仍校验来源绑定。
- 小修走 patch.py，结构性修改才整份重写；临床源文档的必要阅读不算机械重复检查。
- 时间轴只能描述关系与成熟度方向，等大节点没有 weight 编码。修复 R51 未覆盖 prompt/SKILL 的残留。

## 计时口径

R51 的 response→latest tool-return 区间同时包含模型生成和工具执行，不能拆成精确的 85%/15%。request→response 的短间隔不能当完整生成耗时。没有工具 start/end 埋点，故本轮只比较整轮墙钟、调用数、输出／推理 token 与流程签名。不得将未归属余量全部算成组装或落库，也不承诺 150–180 秒。

基线是相同输入、模型 DeepSeek Flash、web=off 的 R51：

| 场景 | server wall | tool calls | output tokens | reasoning tokens |
| --- | ---: | ---: | ---: | ---: |
| 4 条 | 309.2 s | 23 | 55,002 | 34,222 |
| 18 条 | 462.9 s | 36 | 85,671 | 50,178 |
| 14 条 | 494.7 s | 38 | 83,027 | 56,137 |

每场景仅一轮，不把一次波动当稳定提速。

## 本地门禁与发布

- 原 231 项 + review 10 + workflow 3 = 244 项通过。
- fact-check mutations：a 44/44、b 12/12；无未触发项；GATE PASS。
- runner 零网络链：118 histories，5 comparable，GATE PASS。
- `deps` unchanged；已知只按上游版本标签比对的 O50 限制仍在。
- 代码提交 `7852b73`，已推送当前分支；Docker 不涉及。
- 已按授权 `publish --new-version`：prompt **1.8**，71,555 B，SHA256 前缀 `ed5ec6c7afe9`，prompt id `475039ccebfe46a3a39002febe28b1f4`。
- skill **1.0.9**，skill_id `16aeb0406e12425bad27a2444f17225e`，2026-10-12 12:32:50（平台时间）；bundle 156,456 B / 26 entries / SHA256 `0826b8a02e7fee52e16359f65c38055b1fbebbe63803ff2afd9d7802ac14df8d`。
- `status` 回读 prompt 逐字节匹配、skill 26/26 identical，项目当前 prompt/skill 均已切换；上一版 1.7/1.0.8 保留。

## TS 真实回归

固定 4/18/14 输入从 R51 run.json 原样复用，B 使用冻结无效 esid。归档目录 `~/.local/state/toolsmith-runs/20261012-123356-r52-{4,18,14,b}`。运行中冻结运行资产，只编辑文档。

首组 r52-4：thread `e07fb6da-c3a0-4794-8405-be1e651b0cb6`，turn `8b20b322-23d7-402e-a3ff-1446c13d8d1e`；680.1 s server / 682.6 s polled，69 calls，output 112,577 / reasoning 86,503；22 PASS / 0 FAIL。较 R51 同输入 309.2 s / 23 calls 明显退步。review 后半段才采用：33 个候选 = update 32 / drop 1 / keep 0，additions 19，最终 51 facts（R51 52）。33 个候选几乎全部需修改，差量接口本轮未减少抄写成本；模型自行编写 `work/mk_review.py`，经历多次修复；此前多轮 render 探针用未编译的测试 ledger，失败返回无细节后继续探针，随后通过 compiler 才正常渲染。这是流程未按阶段执行的实测，而不是宣称接口自动改善行为。

内容人工复核：报告 §7.2 写「免疫相关事件并未同步升高，提示升高主要来自非免疫机制」。ref_4 原文给出 ≥3 级 TRAE 64%/54%、≥3 级免疫相关 AE 9%/10%，没有直接给出机制归因；当前数字／引用门禁不会拦这种推断。记为内容验收未通过，不用 22 PASS 自证质量。

额外只读 schema 核对：`toolsmith-publish tools --internal --schema execute`（落在 CLI state）实测 required=`command`、另有 stdin/timeout_seconds，而 prompt 的旧工具参数说明仍要求 shell_command。属于我方旧文本漂移，跑动期间没有修改。

r52-18：thread `0bf5a665-db76-441b-a577-349f3fbcc0be`，turn `13317995-2366-4b11-b959-80d3d55b6238`；569.5 s server / 575.8 s polled，45 calls，output 118,905 / reasoning 67,218；22 PASS / 0 FAIL。165 个候选全部 drop，再 additions 140，实际整份重建；模型额外写 `mk_review.py` 19,250 B、`facts_additions.json` 78,985 B，没有保留或更新候选行。相同输入 R51 是 462.9 s / 36 calls，本轮仍退步。

内容人工复核（r52-18）：§4.4 起句「只有 LUX-Lung 8 报告了患者报告结局」，同段又写 SQUIRE 有 EQ-5D / LCSS；§4.1 长期生存率边界声称 CameL-Sq 与 AK105-302「在同一时点方向一致」，同行列出的时点却是 5 年与 24 个月；§五声称 HARMONi-6 与 RATIONALE-307 的 OS 成熟度最高，又在同句列出 CameL-Sq 有更长 65.6 个月随访。前两项为明确的报告内部矛盾，成熟度项缺少额外依据。不能把机械通过当临床验收通过。

检查两层：部署／产物机械断言；临床源文档对照与事实覆盖。三组没有完整冻结事实清单，不能把 22 PASS 解释成临床内容完全正确。

r52-14：thread `82f8c653-8054-4dd6-8e0e-a877153a730f`、turn `21267dcd-b553-4a4a-849a-43c77458926e`；691.6 s server / 708.3 s polled，66 calls，output 113,368 / reasoning 78,309；22 PASS。111 candidates = update 50 / drop 61 + additions 41，final 91 facts，review assembly 重跑 7 次。报告首段正确给出 GLP-1RA 队列全因死亡 HR 0.66，后面证据深度段却称「全部 14 条披露都没有心血管结局终点」，明显内部矛盾；单一 bar 混合异口径、多时点的最高剂量值，相比 R51 的 2 bar + 1 line，不能把图少当提速证据。

r52-b：thread `7a668e04-92f7-42f2-b141-cf5e49005642`、turn `86c3bcce-1d40-482f-9942-447cc1385c56`；39.9 / 44.4 s，8 calls，14 PASS，未写 report/citations。offline scenario b 11/12，唯一 B-A3 固定拒产措辞未命中；实际回复说「一次综合解读至少需要两条可用记录，因此我没有生成报告文件」「只有单条记录…这次先不输出」，属措辞评分未全绿，不改冻结评分器。params 共 3 调用，记录原始行为。

判定：本轮实验不 keep，成本三组全部上升且内容验收有明确问题。TS 当前仍绑定 1.8/1.0.9，尚未回退。不得把一次实验失败解释为接口永远无用，但已有证据不支持其当前设计；不再追加昂贵 A×3 证明收益。回退属于另一 TS 资产写动作，需要用户明确授权。

