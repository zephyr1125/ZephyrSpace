# 唯一修复包

由已锁定裁决台账生成；裁决台账是唯一判断来源，本文不构成修复完成。

## NKE-A01 · P0 · valid

候选：C003, C007, C012

裁决理由：冻结底稿26项合计67.5；唯一规则25项且没有独立F4。剔除2.5后机械和65，合法F小计8。正文11.5及自检25项/通过均错误。不得为保留作者得分修改规则。

原件：deep-prebuy-skill/SKILL.md：F评分表；final/author-v1-workpaper.json scores.company；drafts/frozen-author-v1/deep.md：综合评分汇总、维度F

动作：删除F4独立评分，保留生产运营/ESG内容并只在有实质证据时联动F3；所有评分由唯一底稿生成。

联动：三稿原始分、显示分、组合分、门槛与停止定价理由全部受影响。

- NKE-A01-01：公司评分ID与唯一规则25项一一对应；F4不存在于评分项，C3+C4不拆项；六维小计等于逐项和。
- NKE-A01-02：原始分与显示分分别保存；ROUND_HALF_UP仅用于总分展示，组合分先加原始分；不得残留67.5/60/127.5作为已验收本轮结论。
- NKE-A01-03：修订底稿及三份新稿运行正式机械检查（必要时声明停止估值适配范围），保留真实结果；原虚假通过自检不得继续引用为验收依据。

## NKE-A02 · P1 · valid

候选：C002, C006

裁决理由：索引F004起错位，底稿和正文混用。以facts.json现行ID为迁移基准不代表认可其中所有值；税务必须是F007，SBC为F006。

原件：evidence/evidence-index.md 决定性事实表；evidence/facts.json NKE-F-004至009及NKE-R-001；S005印刷p74、75-76

动作：由主任务安排中性增量版本，列旧索引别名→唯一事实ID，保留冻结v1；作者修三稿与底稿引用。

联动：税务、股数、SBC、IEEPA、或有事项及后续模型的完整依赖链。

- NKE-A02-01：增量映射覆盖F004=五季度平均ROIC口径，F005=股数，F006=SBC，F007=税务，F008=IEEPA，F009=资本配置，R001=法律或有事项；旧索引歧义明确废止。
- NKE-A02-02：三稿与底稿中953/1026/990/742的引用均指F007及p74；742为953子集，不相加、不充当现金或独立债务；SBC保留F006。
- NKE-A02-03：增量证据同时纳入NKE-A09/A10的值和来源类型纠正，记录版本和差异，不覆盖冻结包。

## NKE-A03 · P1 · partial

候选：C001, C009, C010

裁决理由：E2须5分、E3须2分，趋势下降不能替代明确档位。E1必须杜邦，但C009的22.30%使用错误平均权益，不能采纳为独立正确计算。E5.5现行内容规则明确无MD为1.5；这仅是规则规定的未执行审计分，不能解释为未披露或会计质量差。正常化桥需要税率假设和关税成本对称处理，不能机械扣收益后冒充唯一持续利润。

原件：deep-prebuy-skill/SKILL.md E1/E2/E3/E5.5；S005印刷p55、57-59、61、74；财报/耐克/耐克FY2026_10-K.pdf；docs/three-report-evidence-contract.md 无MD可用PDF/HTML

动作：E2改5，E3改2；在本轮现有无MD路径E5.5改1.5并保留原件审计事实。补正确三期杜邦与正常化敏感桥后裁定E1，不能因利润下降自动定杠杆驱动。

联动：已确定净调整：E2+2、E3+1、E5.5-1.5；E1未批准点值。跨深度财务、管理层经营归因、估值盈利基准。

- NKE-A03-01：E2列正确三年OCF/净利130.3333%、114.8804%、92.2780%，FCF为6617/3268/2184百万美元并注明现金Capex口径；E2=5、E3=2。
- NKE-A03-02：E1三年以同口径期初期末平均资产/权益计算净利率、周转率、权益乘数及ROE；FY2026校验为6.698565%、1.237461、2.670739、22.138329%，不得使用ROIC五季度平均权益；按驱动归因选规则档位而非因高ROE或利润下降直接给分。
- NKE-A03-03：E5.5在无MD且未完整执行该项审计的现路径计1.5，明确此为程序化中性值；不因无MD指控公司。若本轮主任务定向补可追溯MD并执行完整CAM/政策变化/计提核验，可依原评分表重新提交有据点值，不得仅转换文件即给3。
- NKE-A03-04：正常化桥分报告利润、IEEPA收益确认986、已收302、应收684；披露原件称回收大体抵销当年IEEPA成本，故删除回收而保留全部对应成本只是压力诊断。以实际有效税率792/3900=20.307692%作明确分析假设时税后净利2322.233846百万美元，非公司官方扣非数；另解释税率及关税成本匹配不确定性，现金桥不把684再计现金。

## NKE-A04 · P1 · partial

候选：C004

裁决理由：A3的3分既非明示档位亦无融资用途/资本史支持；B0只部分覆盖应1分，完成必填分析后才可2分；D5不能以CFO交接替代人效/研发；E1/E5.5并入A03。不是所有缺口都应扣零，也不需要无上限的历史调查。

原件：deep-prebuy-skill/SKILL.md A3、B0、D5；drafts/frozen-author-v1/deep.md A/B/D；S005现金流、附注及人力资本章节

动作：定向补最低分析并给有据分档；B0当前认定1分，可在完整补齐后按2分条件验收。

联动：A3、B0、D5及公司总分；资本史与管理层资本配置联动。

- NKE-A04-01：A3核可得近五年融资/并购/处置记录、用途和利润依赖，判4/2/0并逐项论证；3分撤回，缺证不得作为轻微瑕疵事实。
- NKE-A04-02：B0补创立与当下九要素对照、三个关键判断及四选一分类；建设期不适用须解释。当前部分覆盖1分；完整事实与判断闭合可2分，不准为总分倒填。
- NKE-A04-03：D5补三期人均创收与员工口径、研发披露方式和可得组织信号；未单列研发费用标未知，不把营销费当研发；有实质混合信号才2分，满足人效上升及研发健康才3分，不能凭缺失值给0。

## NKE-A05 · P1 · partial

候选：C013

裁决理由：七维算术60无误，但公开Proxy/人事/资本效果漏查使部分分值未验收。不能把七项全部视为无法判断：战略稳定性8、危机处理5及表达4可由已有经营事实维持；后者只评价书面披露质量，不声称核过电话会。诚信/配置/股东/组织须补证归因。

原件：management-archive/SKILL.md 第九节；management-archive/references/review-checks.md；S005印刷p30、55、58-59；S008 CFO transition p27、Compensation Discussion and Analysis、Transactions with Related Persons p72

动作：一次定向补公开材料，保留已成立判断；主任务交证据角色或作者收集，裁决不另开研究。

联动：管理层总分暂null；公司D2、F1/F2/F2.5/F3作对应联动而不重复惩罚。

- NKE-A05-01：管理层七维分别写事实→分析→分值；保留战略8/危机5/表达4的原始分，明确渠道转向有解释但尚未兑现、回收披露不等于危机解决、书面清晰不代表即兴问答已核；重大新证据才改变已保留项。
- NKE-A05-02：Proxy定向核激励指标/调整权/支付结果及关联交易审查，不能只引用薪酬委员会无关联关系。区分grant-date、realizable、实际现金支付；对诚信、股东友好、组织分别给分值依据。
- NKE-A05-03：资本配置核近五年并购/融资及近三年回购价格、股数净变化、SBC抵消和现金支出；p59回购权益变动不是p58现金回购，不用当期低价倒推全部历史回购必然失败；配置13不得仅凭回购减少维持。
- NKE-A05-04：补近五年主要高管离任/继任时间线，明确截止日12个月是否存在集中离任证据；个别人事动机和未披露保留率允许未知。CFO已公开继任人不得仍写未知；组织7须据稳定性/人才/激励三个子域论证。
- NKE-A05-05：至少三期可得战略目标与执行结果对应，不能把D2上限3当自动得分；如仍仅有一年，应撤回已验证三年执行的措辞并据事实重新判D2，缺原话加漂移上限仍3。

## NKE-A06 · P1 · valid

候选：C008

裁决理由：质量停止定价规则适用，但当前评分错误且未闭合，不能批准reject。没有正式模型本身不是企业质量差。

原件：docs/three-report-closeout.md 质量不达标与停止定价；data/WATCHLIST_RULES.md S/A/B现行门槛

动作：当前defer/execution_incomplete，null仅为未批准。按可信修复评分决定是否进入停止路径或正式双模型。

联动：decision/research_status/watchlistLevel/所有价格字段及三稿结论。

- NKE-A06-01：可信原始评分或有据上下界确定否决所有档位时，decision可reject、level NONE，目标价/确定性/买入价均null；完整估值报告保留适用方法、三种经营情景、停止理由和重评条件，明确未完成正式定价。
- NKE-A06-02：若仍可能达到任一档位，则估值仍未完成：补两个不同依据的适用主模型、三情景、同公式双变量敏感性、统一币种每股权益桥、零权重反向验证及买入公式；不能用低确定性或缺模型直接reject。
- NKE-A06-03：所有P0/P1双路定向验收前research_status保持execution_incomplete；完整研究通过才verified_complete；仅错误已修正或全部依赖结论已撤回、剩余未知有界时才可closed_with_uncertainty，轮次耗尽不等于通过。

## NKE-A07 · P2 · suggestion

候选：C005

裁决理由：现有方向性风险分析成立；观察期更明确有用，但任意具体阈值不是规则强制的新门槛。

原件：S005 MD&A；三稿反证及重评条件

动作：建议以连续两期已披露财报比较同口径全价销售/毛利、库存及现金，阈值作为监测而非入池硬门槛。

联动：仅重评可执行性，不直接改分或产生价格。

- NKE-A07-01：P2建议项：记录是否采纳明确观察期的重评建议；采纳则标明新稿位置，不采纳则保留现有方向性反证并说明理由。此项不阻塞P0/P1验收，不新增入池门槛，也不触发额外修复或复裁轮次。

## NKE-A08 · P2 · partial

候选：C011

裁决理由：供应链页码与来源表是展示定位问题；税务ID和公开Proxy漏核已升级归入A02/A05，不能重复计重大问题。

原件：S005 Item 1 Manufacturing印刷p5-6；三稿来源引用

动作：统一印刷页/PDF物理页口径并补集中来源表；有误页号逐个回看，不统一机械加页。

联动：来源可复核性，不另行扣分。

- NKE-A08-01：P2来源定位项：记录供应链页码与集中来源表的修正位置，统一印刷页/PDF物理页口径；税务ID和Proxy实质问题仍仅按A02/A05验收。此项不阻塞P0/P1验收，不重复计重大问题，也不触发额外修复或复裁轮次。

## NKE-A09 · P1 · valid

候选：裁决原件新增

裁决理由：裁决直接核原件发现中性包/候选共同遗漏：13944/13926为ROIC表五季度平均权益，非期末权益；FY2026/25期末权益14865/13213。前两年简化FCF也扣错Capex。候选C009杜邦数字不能照用。

原件：S005印刷p31、55、57、58、59；S001 https://www.sec.gov/Archives/edgar/data/320187/000032018726000088/nke-20260531.htm ROIC与合并资产负债表

动作：增量纠正事实、回算受影响桥，允许扩大至同类平均数/期末数和现金流/权益变动混用检查，非全量重写。

联动：E1/E2/E4/E5、资本配置、资产负债表和未来估值桥；不影响已核收入/净利/OCF本身。

- NKE-A09-01：证据增量列FY2026/25期末权益14865/13213、FY2024/23权益14430/14004；13944/13926仅保留为各年度五季度平均权益。三稿及底稿不得残留误标。
- NKE-A09-02：FY2024/25/26现金Capex812/430/684，OCF-Capex6617/3268/2184百万美元；深度稿6804/3400撤回，管理层原Capex表812/430/684保留。
- NKE-A09-03：触发E4 Capex同比超过30%规则：补运营/非运营拆分或明确无法拆分并按原规则扣0.5，若基础E4=2则净1.5；不得用缺拆分证明实际资本消耗恶化。
- NKE-A09-04：复查所有期末/平均、现金回购/权益变动口径，给事实→分项→三稿影响表及未变依据。

## NKE-A10 · P1 · valid

候选：裁决原件新增

裁决理由：S010链接正文为EX-10.2 Executive Severance Pay Plan，非CFO任命主文。S008 p27已明确David Denton于2026-08-17任CFO，故未知继任者是公开事实遗漏，不可用作稳定性扣分。

原件：S010 https://www.sec.gov/Archives/edgar/data/320187/000032018726000070/nike-2026nikeincexecutives.htm 顶部EX-10.2；S008 https://www.sec.gov/Archives/edgar/data/320187/000032018726000089/nke-20260715.htm CFO transition p27

动作：纠正S010来源类型；在同accession定位8-K主文及相关附件，定向核个人安排，不把通用遣散资格当已支付个人金额。

联动：NKE-G004、公司F1和管理层组织/诚信/友好，估值治理边界。

- NKE-A10-01：中性增量准确标S010为通用计划附件，补真正8-K主文ID和截至截止日任命/离任生效日期；三稿写明David Denton继任及Friend顾问/离职时间。
- NKE-A10-02：分清计划适用条件、潜在支付、个人约定与已付金额；非竞业/遣散抵扣不重复相加；撤回因未读主文造成的组织负面推断，未知动机仍未知。

## 最终参数或待定原因

```json
{
  "company_score": null,
  "management_score": null,
  "combined_score": null,
  "display_scores": null,
  "watchlistLevel": null,
  "target_price": null,
  "certainty": null,
  "buy_price": null,
  "currency": "USD",
  "valuation_status": "not_approved_pending_quality_scores",
  "pending_reason": "评分结构、权益口径、分项依据及公开治理材料遗漏尚需按逐ID修复；目前没有可信边界足以否决所有档位。",
  "company_score_bridge": [
    {
      "id": "A1",
      "frozen_score": 3,
      "adjudicated_score": 3,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "A2",
      "frozen_score": 3,
      "adjudicated_score": 3,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "A3",
      "frozen_score": 3,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "B0",
      "frozen_score": 2,
      "adjudicated_score": 1,
      "status": "approved_on_current_evidence"
    },
    {
      "id": "B1",
      "frozen_score": 3,
      "adjudicated_score": 3,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "B2",
      "frozen_score": 3,
      "adjudicated_score": 3,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "B3",
      "frozen_score": 4,
      "adjudicated_score": 4,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "B4",
      "frozen_score": 1,
      "adjudicated_score": 1,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "C1",
      "frozen_score": 6,
      "adjudicated_score": 6,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "C2",
      "frozen_score": 3,
      "adjudicated_score": 3,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "C3",
      "frozen_score": 5,
      "adjudicated_score": 5,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "D1",
      "frozen_score": 2,
      "adjudicated_score": 2,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "D2",
      "frozen_score": 3,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "D3",
      "frozen_score": 1,
      "adjudicated_score": 1,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "D5",
      "frozen_score": 2,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "E1",
      "frozen_score": 2,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "E2",
      "frozen_score": 3,
      "adjudicated_score": 5,
      "status": "approved_on_current_evidence"
    },
    {
      "id": "E3",
      "frozen_score": 1,
      "adjudicated_score": 2,
      "status": "approved_on_current_evidence"
    },
    {
      "id": "E4",
      "frozen_score": 2,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "E5",
      "frozen_score": 2,
      "adjudicated_score": 2,
      "status": "retain_unaffected_judgment_subject_to_linkage"
    },
    {
      "id": "E5.5",
      "frozen_score": 3,
      "adjudicated_score": 1.5,
      "status": "approved_on_current_evidence"
    },
    {
      "id": "F1",
      "frozen_score": 2,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "F2",
      "frozen_score": 3,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "F2.5",
      "frozen_score": 1,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "F3",
      "frozen_score": 2,
      "adjudicated_score": null,
      "status": "pending_targeted_evidence_or_recalculation"
    },
    {
      "id": "F4",
      "frozen_score": 2.5,
      "adjudicated_score": null,
      "status": "delete_invalid_item"
    }
  ],
  "mechanical_bridge": {
    "frozen_unapproved_total": 67.5,
    "remove_F4": -2.5,
    "legal_25_item_sum_before_regrading": 65.0,
    "E2_delta": 2,
    "E3_delta": 1,
    "E5_5_delta": -1.5,
    "B0_current_partial_coverage_delta": -1,
    "subtotal_before_pending_items_rejudged": 65.5,
    "subtotal_is_final_score": false,
    "note": "65.5仍包含待定项目的冻结旧值，只是差异核算占位，不是分数下限/上限或资格输入。E4未拆分时另扣0.5；B0完整补齐可回2，其他按规则补证。"
  },
  "management_score_bridge": {
    "frozen_unapproved_total": 60,
    "retained_items": {
      "战略稳定性": 8,
      "危机处理能力": 5,
      "表达清晰度与认知质量": 4
    },
    "pending_items": [
      "诚信与透明度",
      "资本配置能力",
      "对股东友好度",
      "组织与人才能力"
    ],
    "reason": "不得用完整原件未阅读作缺证扣分；七维总分在补证后重算，不先定目标总分。"
  },
  "thresholds": {
    "B_GROWTH": "原始公司>=70且管理层>=70且合计>=150",
    "A_CORE": "原始两项均>=76且合计>=160",
    "S_STRATEGIC": "原始两项均>=82且合计>=170，并满足确定性>=0.80及其余现行硬条件"
  },
  "decision_conditions": "按NKE-A06验收；原始分可信否决全部档位则reject/NONE及停止正式定价，否则可能合格须正式双模型。历史76.5/68/NONE不参与本轮基线。"
}
```
