# 联合研究接口（过渡版A）

## 精简送审的输入完整性

估值局部验证或恢复时，使用 `python -X utf8 scripts/triplet_review_packet.py <workpaper.json> <evidence-paths.json> <新packet.json>` 生成审核包。它保留整段估值、桥接与缺口，递归携带显式引用的事实及来源，并附与机械检查共用的买入价公式。缺引用、三情景或参数元数据、买入价算术不符时拒绝生成；不能手工裁剪后仅凭文件短就送审。完整联合首审仍须提供全32项底稿，本包不替代完整研究审核。

审核逐项回应包内经济问题，尤其是折现率、终值及再投资依据；不适用须说明理由。区分输入包漏带（packet_missing）、核实后原件未披露（source_missing）与假设依据不足（unsupported_assumption）。来源路径允许按需读取原件及索引外资料，引用闭合不证明原件真实或假设合理。模型相关性、结果价差本身不是禁止加权的充分理由；不得因未提供规则而自行要求买入价等于悲观估值。

2026-09-27起新完整请求使用 `research_profile: "joint_research_v1"`。旧底稿、局部评分与历史回放保持旧命令兼容。阶段、双全审及额度只在[调度SOP](three-report-economy-routing.md)维护。本接口不改变32项原规则、模型配置或估值公式，不自动批准研究。

## 首次送审

保存与批准分开：`python -X utf8 scripts/triplet_research.py save-draft <草稿.json> <新目录>` 可正常保留null分数、`evidence_gaps`中的`not_obtained`（未取得）/`not_derivable`（无法推导），以及模型的`not_applicable`（不适用）/`withdrawn`（撤回）状态。它保留原字段，输出`draft_saved_not_reviewed`和哈希回执，不要求捏造数值或增加例外审批。`check`、冻结与发布仍分别判断是否达到其验收条件；保存成功不代表可估值、评分获批或研究完成。已批准历史文件不原地修改。

现有workpaper同时保存scores、valuation、bridges，不另建估值台账。主模型增加 `economic_basis` 和注册的 `evidence_refs`，说明参数经济来源；PE/Ke/远期现金流与终值的最低依据见SOP。程序只能检查存在，独立审核必须判断是否充分。完整首审不接受deferred占位；确实未齐则保留未就绪状态和恢复点。质量停止仍用既有stopped_quality_gate_after_full_research，不能由缺证推导。

```powershell
python -X utf8 scripts/triplet_research.py check <workpaper.json> <evidence-files.json> <check.json>
```

两路审核沿用现有JSON，另加 `workpaper_sha256`、`input_sha256: {有效证据或规则路径: SHA256}` 和 `coverage: {"score": true, "valuation": true}`；true表示实际完成首次覆盖，不表示通过。input_sha256覆盖全部有效证据及公司/管理层/估值核心模块、管理层review-checks。未覆盖不能填true。匿名裁决保留这两份记录路径；覆盖自述由主任务抽核内容，不能用路径数量证明独立性。

## 关键数值

在原证据JSON的事实记录添加字段，不复制数值到第二份台账。底稿的 `numeric_fact_ids` 列全部决定性数值ID（非空），审核核是否遗漏。每条要求：

`fact_id/entity/metric/value/unit/currency/period_start/period_end/as_of/consolidation/actual_or_plan/source_ref/locator`。

日期用ISO日期；时点值start=end；无币种写none。actual_or_plan取actual/plan/forecast/assumption；source_ref引用同一有效证据清单中的来源ID。分红metric用dividend，另加整数profit_attribution_year、declaration_date、payment_status（paid/unpaid/unknown）；paid必须有payment_date。

派生值放底稿 `numeric_calculations`，每项 `{id, formula, input_fact_ids: {变量: 事实ID}, result, unit, basis, same_basis: [同口径字段]}`。same_basis允许unit/currency/consolidation/period_start/period_end/actual_or_plan。分红累计再给dividend_basis（profit_attribution_year/payment_year）和years数组；输入必须归属对应年份。跨期比较不要声明期别相同；跨单位转换须在公式与basis中显式表示。模型及桥接的evidence_refs可直接引用已复算的派生记录ID，不必把结果重复抄入事实表；ID不得与现有证据重名。公式重算不验证抄录真实、漏项或经济归因。

估值 `input_meta` 中kind=actual的输入必须加numeric_fact_id，与该事实value、unit和实际属性核对。换算后的值不能冒充同一原始事实，应保留派生计算与来源。预测仍按模型经济依据审核，不把预测登记成实际值。

作者填好原始输入、绑定关系和公式后，可运行 `python -X utf8 scripts/triplet_research.py recompute <草稿.json> <证据路径数组.json> <新输出目录>`，生成workpaper.json与receipt.json。工具按依赖排序并重算派生值、三情景、二维敏感性、加权价和机械买入价；不改分项、参数、公式、权重、反向求解、文字理由或修复计数。输入绑定冲突、缺依赖、成环或同口径约束失败直接拒绝；其他联合检查错误写入receipt并以非零退出。不得把生成计算稿当作研究批准。修复时只把获授权字段的计算结果带回delta，仍由apply-delta检查范围；冻结稿与历史报告不得原地修改。证据路径参数是JSON数组，不是含files字段的清单对象。

## 局部修复与额度

裁决加入research_cycle：mode=joint、first_review_refs（两份联合初审路径）、first_workpaper_sha256、repairs_used（首次修复前为0，例外前为1）；例外还需exception_reason。首次两路必须覆盖同一底稿的评分和估值。程序拒绝评分单审消耗联合额度，拒绝第三次修复；新底稿记录递增后的repairs_used。裁决复查必须继承新底稿计数及前版谱系，不允许重置；主任务核日志，计数不是可任意自填的授权。

沿用 `triplet_score_flow.py apply-delta`；旧changes和metadata_changes兼容。联合模式新增：

- 裁决 `valuation_repair_scope: [{field, acceptance_ids, model_ids}]`。field只能是valuation已有接口：models、weighted、target_price、certainty、certainty_reason、buy_price、reverse、currency、status、reason、additional_model_reason。models必须明确model_ids，只允许修改所列已有模型，其他模型原样保留。
- 作者 `valuation_changes: [{field, acceptance_ids, set}]`，同裁决原验收ID；相关计算结果变化也须在范围内列出，不能靠自动重算掩盖未经批准的输入变化。
- metadata_repair_scope另允许bridges、numeric_fact_ids、numeric_calculations，均以完整数组提交并记录前后差异；evidence_gaps仍兼容。修复事实用新证据文件版本，禁止覆盖旧原件。

需要增删模型或改变超出接口的经济结构时，由原裁决明确范围后保存全新底稿并人工核完整差异，不用通用JSON patch绕过限制。额度仍计入原研究循环。receipt证明机械变更，不证明问题关闭。

### 修复送审前的计算依赖

裁决要求特定经营驱动进入预测时，在原裁决加入 `mechanical_requirements`，不另建审批表。例如 `{id:"A2-growth", acceptance_id:"A2", model_id:"fcfe_owner_cash_dcf", scenarios:["bear","base","bull"], input:"fcfe1", required_metrics:["same_store_growth","net_openings"]}`。这些是本次裁决要求，不是所有行业统一必填指标；后续年份有相同要求时逐输入绑定。不得由作者删除或减轻裁决条件。

作者复用底稿 `numeric_calculations` 和证据中的 `metric/value/unit`，将模型 `input_meta` 的 `calculation_id` 绑定对应派生计算。计算的 `input_fact_ids` 可引用数值事实或其他派生计算；必须按依赖先后排列（被引用计算在前）、无环、可复算、单位与模型输入一致。外部脚本路径字典不等于计算记录数组，须在新底稿中提取为可验证记录；程序不自动执行外部脚本，也不将旧格式默认为空数组。只有实际连到受影响模型输入的依赖才计入，单独写一段未被使用的驱动说明不算闭合。

送定向复核前运行 `python -X utf8 scripts/triplet_research.py check-acceptance <workpaper.json> <ruling.json> <evidence-files.json> <新check.json>`。冻结有此声明的裁决也再次检查。缺输入绑定、必需驱动、合法公式、单位或计算结果一致性则不能送审；通过只说明映射及运算成立，不能证明来源真实、驱动充分或经济合理。原件摘录、预测边界与独立复核保留。历史裁决不追溯补写条件。

## 不可变研究版本与批准依赖

准备冻结描述 `{workpaper, decision, evidence: [有效JSON路径], previous_decision: 上一冻结裁决路径}`；第一版可省previous_decision。输入decision由裁决维护，作者不能自批；score_state/valuation_state独立记录，完整research_state=approved要求两者approved（质量停止的valuation_state表示获批停止，并非获批价格）。

```powershell
python -X utf8 scripts/triplet_research.py freeze <freeze-config.json> data/reviews/<run>/versions/v1
```

生成新目录的workpaper.json、decision.json，并更新同级current.json。已有版本拒绝覆盖；后续用v2。current只存路径与哈希，不进入构建输入。bundle的workpaper/decision直接指向versions/vN内文件；发布批准在构建生成、独立验收后引用其manifest，沿用check-release/archive-release，不回写旧decision。

裁决冻结全部有效证据、原规则、审核记录哈希和底稿字节哈希；评分/估值批准分别保存approval_projections。评分投影包含评分和共用上下文，不包含估值状态；估值投影另包含评分与估值。第一版保守绑定全部有效证据和规则，任何证据变化均可能触发重审，不假装已有精确依赖图。估值参数单独变化不撤销匹配投影的已批准评分，共享事实变化则失效。批准有效不等于允许发布。

freeze只生成批准绑定，不代替人工授权；旧裁决的冻结输入和批准投影必须先通过校验，不能自动重签给变化后的证据。新批准要求两份审核的input_sha256绑定当前证据和规则，并绑定当前底稿哈希，或由审核者明确给出仍有效的approval_projections对应范围哈希。局部修复仅能保留原裁决已有且投影仍匹配的评分批准。构建校验冻结依赖及底稿版本；手改冻结文件、替换规则、变更证据会失败。旧版本仍按旧接口复现，不能追改其状态。
