# 唯一修复包

由已锁定裁决台账生成；裁决台账是唯一判断来源，本文不构成修复完成。

## G02 · P1 · partial

候选：C005, C012, C016

裁决理由：期末桥被称年度加权分母确属错误；SBC重复惩罚是未能证明消除的风险，不判定9百万股全部对应当期费用。现有公式条件算术正确不能弥补归属缺口。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页59、75-77；PDF63、79-81；旧writer/workpaper-v3.json；最新估值股数桥/经济FCFE桥；本run/evidence/facts.json：NKE-R-005、NKE-R-006、NKE-R-007

动作：统一处理股数、SBC与回购现金归属；不要求逐笔未来交易成为事实。可撤回依赖本项的全部正式价格、买入价、确信度及有效价格区，保留原件事实和明确无效原因；错误公式不以改名诊断继续使用。撤回仅关闭错误使用，不声称模型已验证。

联动：两模型EPS/FCFE、超额现金及综合价格受影响；不直接改变经营评分。

- G02-sbc：用已披露RSU/期权余额与FY2026期权3、员工净发行6百万股说明既存奖励/未来授予的处理；明确采用经济费用或稀释路径，量化证明同一成本不双扣。未来授予可以假设并敏感性；无法分辨可撤回该每股模型。
- G02-equity：若保留回购预测，给价格、现金、发生时点，列现金期初+经营/融资-分红-回购=期末及运营保留/超额分配，回购不既消耗被分配现金又无资金减少分母；允许明确零回购假设。保留已核2bn滚续与租金处理，不重查历史事实。
- G02-recalc：保留的模型须按最终输入重算三情景、敏感性、反向解与三份报告一致性；选择撤回路径则正式参数均null，明确原34.213160/.50/25.659870不批准，删除当前有效价格带。

## G03 · P1 · partial

候选：C001, C006, C007, C009, C010

裁决理由：总经营桥算术已成立；需要收入恢复与地区/渠道历史连接及正确分母。供应商selected不是独立交易锚，23.98预测期未知不能支持牛市20倍。未来预测不要求证成事实，合理假设差异本身不构成错误。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页36、86-87；旧adjudication-v2.json verified_facts_delta/market_source_disagreement；最新估值PE模型；本run/evidence/facts.json：NKE-R-003、NKE-R-007

动作：最小经营桥可选地区或渠道一种维度，不能交叉重复相加。若缺独立市场依据，撤回PE正式权重，不新增模型凑数。可撤回依赖本项的全部正式价格、买入价、确信度及有效价格区，保留原件事实和明确无效原因；错误公式不以改名诊断继续使用。撤回仅关闭错误使用，不声称模型已验证。

联动：正式加权价格须两个有效不同依据模型；单模型诊断允许，但目标价/确信度/买入价null。

- G03-eps：若保留预测，列FY2026已核分部或渠道→FY2027三情景增长假设→合计收入；沿用已核毛利至净利算式，股数使用G02时点加权并单列潜在稀释。每项预测注明经济理由，不要求未来公告验证。或撤回依赖该预测的价格。
- G03-anchor：可用冻结包内日期、样本、实际/预测期、盈利口径可核的独立锚，解释到FY2027三档PE的风险/增长调整；不能以35.51/当期EPS反算现价倍数或供应商selected独自充第二合理价值。无可靠锚即撤回正式PE权重，未知保留。
- G03-completion：仅两模型实质闭合才批准权重、确信度五项理由及target×(0.68+0.14×certainty)机械买入价；否则null，研究状态与决策分开。若可信评分上界已否决全部档位，可停止正式定价，不必强凑第二模型。

## G05 · P1 · partial

候选：C003

裁决理由：原页75确认1270现金税含最终过渡税268及预计解决FY17-19事项支付260。最终过渡税未来不再重复有据，历史事项未来结算金额未知；并非必须把528逐美元转成FY2027加回。现有-150/0/+100缺历史/风险依据，不能被当精确正常化。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页75/PDF79；最新估值FY2027现金桥；本run/evidence/facts.json：NKE-R-008

动作：保留两笔特殊付款事实，将未来现金税明确为假设并界定结算未知；可用税费等现金税作为透明基准及压力测试，不索取未披露确数。可撤回依赖本项的全部正式价格、买入价、确信度及有效价格区，保留原件事实和明确无效原因；错误公式不以改名诊断继续使用。撤回仅关闭错误使用，不声称模型已验证。

联动：仅影响现金流模型现金税/价值；历史E2不因预测税额未知自动扣分。

- G05-tax：若保留模型，列三情景税前利润×22%=税费、税费与现金税差及其假设依据；268不重复、260结算未知不永久加回，敏感性覆盖可论证的时点差。不能声称已精确预测IRS结算；或撤回依赖价格并保留未知。

## G07 · P1 · valid

候选：C008

裁决理由：A3定义是融资用途与资本运作清洁度，回购纪律在F2.5/管理层资本配置；A3=3.5仍用回购纪律不足不给满分属错误归因。但删错理由不自动证明4分。

原件：deep-prebuy-skill/SKILL.md A3/F2.5；财报/耐克/耐克FY2026_10-K.pdf 原页45-46、59；旧adjudication-v2.json G07；最新深度最终评分桥；本run/evidence/facts.json：NKE-R-007

动作：恢复A3对应原件范围的融资用途、并购/商誉、非主营出售判断；仅按清洁度给分或明确待定。F2.5和资本配置已核问题保留原边界，不重复扣分。

联动：A3点值待定，规则上限4；公司总分不能以72.5作已批准。

- G07-score：A3用事实→规则→分数或待定原因；若仅作资格上界可用满分4作为数学上限，不把资料未知当0分或瑕疵。其余G07已核分项恢复各自理由，不能复活外聘/亲属/未知自动负面归因。

## G08 · P1 · partial

候选：C002, C004, C013

裁决理由：员工数、人效、D2/D5修复无本轮实质反证，保留；人事表以任命代替离任模式、F1与组织分数据此受影响成立。要求每名离任真实动机全部可知不成立。已核CEO/CFO更替不能扩大为已证实异常集中离职。

原件：management-archive/SKILL.md 六/九及references/pitfalls.md M8；旧adjudication-v2.json G08/员工事实；最新管理层五年核心人事/七维评分桥；本run/evidence/facts.json：NKE-R-009、NKE-R-010

动作：就既有人事表区分任命、调岗、新设职责和离任；明确对应离任者/日期未核与公开原因未知；撤回依赖未知的集中异常离任或继任失败判断。无需无限补齐公开未披露原因。

联动：F1与组织人才待定；D2=3、D5=2候选修正分可保留但G13须恢复对应执行/效率理由，不以人事未知连带失效。

- G08-people：既有表每行给事件类别、已核日期/身份/接任来源，原件未确认离任者或原因明确未知；对12个月离任模式只据核实离任判断，任命数不能充离任数。Donahoe/Hill与Friend/Denton保留；未知可界定，不要求无公开资料的动机。
- G08-score：F1按核心稳定/激励证据重评，管理层组织按稳定性、人才保留、激励三部分说明，不把未知原因当扣分。可不给点值并用原规则满分上限5/10作资格上界；D2/D5与战略/危机/表达未受影响依据保留，复查不得自动把任命未知扩大扣分。

## G09A · P2 · suggestion

候选：C015

裁决理由：三年绝对额正确、合计可复算，未单列同比不改变北美改善/中国及Converse承压方向，不构成本轮P1。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页36、86-87；旧adjudication-v2.json verified_facts_delta/segments；本run/evidence/facts.json：NKE-R-003

动作：可用正确绝对额机械补同比；负基数与跨零注明不可简单解释。

联动：无新增评分影响，不阻塞。

- G09-segments：保留已核三年分部/合计与Note15定位，建议补同比；未补百分比本身不判P1，若发现方向或实际金额错误按实质另列。

## G09B · P1 · partial

候选：C011

裁决理由：15.5/1.7、4.9/4.7、2.4/1.6bn事实已核；仅原则映射不足证明8.027bn缓冲合理。但公司未披露每份合同与预测科目逐项勾稽，不能要求不可知精确分配。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页46、62/PDF50、66；最新估值现金归属与预测桥；本run/evidence/facts.json：原件p46与p62直接核验

动作：给三类未来12月承诺的数值覆盖假设或上下界及现金压力；未来合同支付可作假设，不把全部承诺当债。可撤回依赖本项的全部正式价格、买入价、确信度及有效价格区，保留原件事实和明确无效原因；错误公式不以改名诊断继续使用。撤回仅关闭错误使用，不声称模型已验证。

联动：与G02现金缓冲统一一张桥，不额外重复现金扣减；不自动改变B1/E4评分。

- G09-commitments：分别映射1.7/4.7/1.6bn支付到费用、成本/存货/应付、Capex；给预测覆盖量或有据边界并解释未覆盖现金需求如何影响现金留存。不得全额在成本后再减承诺；若未知不可界定则撤回超额现金加项和依赖价格，不要求逐份合同不可得信息。

## G13 · P1 · valid

候选：C014

裁决理由：v3将25个公司评分理由及7个管理层理由替换为循环引用，最新正文删除多年度历史、控制选举权、激励/关联金额等原有可复核内容；上次33项泛指关闭不真实。v1有已裁定错误，不能整篇回退。

原件：旧writer/workpaper-v1/v2/v3.json；旧writer/frozen-deep-v1.md、frozen-management-v1.md、frozen-valuation-v1.md；最新三报告全文；docs/three-report-closeout.md；本run/evidence/facts.json：NKE-R-002、NKE-R-004、NKE-R-010、NKE-R-011

动作：以v1可追溯结构与理由为恢复基线，叠加v2裁决精确事实和已通过修正；最新稿仅提供修正片段。只恢复删除内容并改本轮13ID，不整篇模板再生成。

联动：评分上界只有每个固定项原件/规则/理由恢复并双路认可后才可作reject依据；不得从72.5/68总数倒推固定项成立。

- G13-single-source：逐项恢复25+7理由和具体来源：旧裁决已批准项原理由保留，受纠错项替换错误事实/归因并注明旧→新分。恢复七年经营表、原控制权选举8/3及78.8%、激励兑现和关联交易具体金额等已核内容；源材料不支持则标未知而非编造。对本轮13验收ID分别列实际段落/表格/计算/撤回位置；其余原33关闭项做防回退映射而非重新研究。评分点值或上下界、三份快照与价格状态唯一一致。恢复全文150/150/100及内容要求，程序通过不等于实质通过。

## 最终参数或待定原因

```json
{
  "currency": "USD",
  "company_score": null,
  "management_score": null,
  "target_price": null,
  "certainty": null,
  "buy_price": null,
  "pending_reason": "原点值尚未实质验收；估值归属/锚缺口仍在，原34.213160/.50/25.659870不批准。",
  "score_bridges": {
    "company": [
      {
        "id": "A1",
        "original_score": 3,
        "prior_adjudicated_score": 3,
        "latest_author_proposal": 3,
        "approved_score": 3,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "创始人运动员背景与产品创新、品牌营销结合，形成全球先发品牌基因。",
        "original_evidence_refs": [
          "NKE-G-002；S001 FY2026 10-K Item 1 pp.3-5"
        ],
        "adjudication_reason": "运动产品创新及品牌先发基因未被本轮新证据推翻。"
      },
      {
        "id": "A2",
        "original_score": 3,
        "prior_adjudicated_score": 3,
        "latest_author_proposal": 3,
        "approved_score": 3,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "控制权长期稳定；双层股权保持Knight家族影响力，但降低B类股东董事选举权。",
        "original_evidence_refs": [
          "NKE-G-009；NKE-G-017"
        ],
        "adjudication_reason": "控制权长期稳定；公众制衡问题归治理，不改变稳定性事实。"
      },
      {
        "id": "A3",
        "original_score": 3.5,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 3.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "主业集中、无跨界并购主导迹象；历史回购规模大，但高价回购与当前股价下跌削弱资本运作质量。",
        "original_evidence_refs": [
          "NKE-F-015；S001 Item 5 HTML L809-812"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "B0",
        "original_score": 2,
        "prior_adjudicated_score": 2,
        "latest_author_proposal": 2,
        "approved_score": 2,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "从跑鞋创新与专业运动员连接起步，演化为轻资产合同制造、品牌和渠道驱动模式。",
        "original_evidence_refs": [
          "NKE-G-002；S001 Item 1 HTML L217-260"
        ],
        "adjudication_reason": "设计/品牌/合同制造商业模式可核。"
      },
      {
        "id": "B1",
        "original_score": 3,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 3.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "鞋类、服装、装备及Converse形成产品组合，地域全球化；鞋类与NIKE品牌集中度仍高。",
        "original_evidence_refs": [
          "S001 FY2026 10-K Note 19 segment disclosure；HTML L979-1040"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "B2",
        "original_score": 2,
        "prior_adjudicated_score": 2,
        "latest_author_proposal": 2,
        "approved_score": 2,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "品牌复购和规模效应较强，但运动鞋服属于可选消费，批发与直营流量均受需求波动。",
        "original_evidence_refs": [
          "NKE-G-002；S001 MD&A HTML L843-856"
        ],
        "adjudication_reason": "可选消费且低转换成本的经济属性未变；关税桥改变盈利归因不改变该项基本模式判断。"
      },
      {
        "id": "B3",
        "original_score": 5,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 4,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "全球品牌、运动员资产和产品创新构成强定价基础；FY2024-FY2026利润与库存压力显示定价权并非无条件。",
        "original_evidence_refs": [
          "NKE-F-011；NKE-F-012；S001 Risk Factors"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "B4",
        "original_score": 2.5,
        "prior_adjudicated_score": 2.5,
        "latest_author_proposal": 2.5,
        "approved_score": 2.5,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "行业长期需求存在但成熟、竞争激烈；FY2024-FY2026收入由51.362降至46.398十亿美元，复苏仍需验证。",
        "original_evidence_refs": [
          "NKE-F-011"
        ],
        "adjudication_reason": "成熟市场与近两年收入疲弱仍支持原谨慎判断。"
      },
      {
        "id": "C1",
        "original_score": 6,
        "prior_adjudicated_score": 6,
        "latest_author_proposal": 6,
        "approved_score": 6,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "公司在10-K中称其为全球最大运动鞋服销售商，仍属绝对第一梯队。",
        "original_evidence_refs": [
          "S001 MD&A HTML L843-847"
        ],
        "adjudication_reason": "全球规模第一梯队判断无决定性反证。"
      },
      {
        "id": "C2",
        "original_score": 3,
        "prior_adjudicated_score": 3,
        "latest_author_proposal": 3,
        "approved_score": 3,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "合同制造与全球采购提供弹性，品牌对消费者有议价力；供应链集中、关税与批发渠道仍制约利润率。",
        "original_evidence_refs": [
          "NKE-G-002；S001 Risk Factors HTML L702-710"
        ],
        "adjudication_reason": "合同制造优势与供应地域集中、关税制约并存。"
      },
      {
        "id": "C3+C4",
        "original_score": 7,
        "prior_adjudicated_score": 7,
        "latest_author_proposal": 7,
        "approved_score": 7,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "品牌、规模、运动员网络、研发与渠道构成四星级护城河；低切换成本与Adidas、On、Hoka等竞争限制满分。",
        "original_evidence_refs": [
          "NKE-G-002；S001 Competition and Products sections"
        ],
        "adjudication_reason": "品牌、研发、运动员和渠道壁垒同时有低切换成本限制；本轮没有支持机械改变7分的新事实。"
      },
      {
        "id": "D1",
        "original_score": 3,
        "prior_adjudicated_score": 3,
        "latest_author_proposal": 3,
        "approved_score": 3,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "长期围绕运动、创新和消费者连接，FY2026重新强调Win Now；DTC偏置后又修复批发，属可解释的渠道调整。",
        "original_evidence_refs": [
          "S001 MD&A HTML L843-847；NKE-F-011"
        ],
        "adjudication_reason": "运动创新主线与可解释渠道修正并存；D2履约不可混作D1战略漂移。"
      },
      {
        "id": "D2",
        "original_score": 2.5,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 3,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "FY2024高位后FY2025利润显著下降，FY2026收入仅持平且净利继续下降；转型目标兑现不完整。",
        "original_evidence_refs": [
          "NKE-F-011；V3-003"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "D3",
        "original_score": 1,
        "prior_adjudicated_score": 1,
        "latest_author_proposal": 1,
        "approved_score": 1,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "可选消费疲弱、关税、汇率、中国市场和新品牌竞争构成明显外部逆风。",
        "original_evidence_refs": [
          "S001 Risk Factors；S001 MD&A"
        ],
        "adjudication_reason": "外部需求、贸易及竞争逆风仍在。"
      },
      {
        "id": "D5",
        "original_score": 1.5,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 2,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "CEO回归与COO、CFO重组带来修复能力，也反映组织尚在重置；连续执行证据不足。",
        "original_evidence_refs": [
          "NKE-G-008；V3-002"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "E1",
        "original_score": 3,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 3.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "品牌轻资产属性支持较高回报，但回购缩减权益及利润波动使ROE质量不能按纯经营驱动满分。",
        "original_evidence_refs": [
          "NKE-F-011；NKE-F-012；NKE-F-015"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "E2",
        "original_score": 3,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 3,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "FY2020-FY2026累计现金转化总体健康，但FY2026 CFO降至2.868十亿美元、低于净利3.108十亿美元，FCF仅2.184十亿美元。",
        "original_evidence_refs": [
          "NKE-F-010；NKE-F-011；NKE-F-020"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "E3",
        "original_score": 1.5,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 1.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "七年收入CAGR为低个位数且近两年利润明显回落，增长质量处于修复期。",
        "original_evidence_refs": [
          "NKE-F-010；NKE-F-011；V3-001"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "E4",
        "original_score": 1,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 0.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "现金短投9.027十亿美元覆盖7.942十亿美元有息债务，但另有3.091十亿美元租赁负债。",
        "original_evidence_refs": [
          "NKE-F-012；NKE-F-021"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "E5",
        "original_score": 2,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 2,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "PwC对报表与ICFR均出具无保留意见；库存7.501十亿美元仍需持续观察。",
        "original_evidence_refs": [
          "NKE-G-005；NKE-F-012"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "E5.5",
        "original_score": 2.5,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 2.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "审计与内控结论干净，关键估计有披露；证券诉讼和估计敏感性保留但未见重大会计异常。",
        "original_evidence_refs": [
          "NKE-G-005；NKE-L-023；S005 pp.52-54"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "F1",
        "original_score": 4,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 3.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "内部晋升CEO与长期任职团队有连续性；CFO交接成本较高但8-K明确无经营政策分歧。",
        "original_evidence_refs": [
          "V3-002；S001 executive officers"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "F2",
        "original_score": 4,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 4,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "持续分红、回购和高比例绩效薪酬对齐股东；双层股权与未逐笔核完内部交易限制满分。",
        "original_evidence_refs": [
          "NKE-F-015；NKE-G-022；V3-003；V3-004"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "F2.5",
        "original_score": 1,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 1.5,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "FY2026暂停回购并保留现金应对转型具有审慎性，但历史高价回购、SBC和高额CFO交接补偿降低效率。",
        "original_evidence_refs": [
          "NKE-F-014；NKE-F-015；V3-002"
        ],
        "adjudication_reason": "沿用v1待定；本次具体闭合要求见关联根因及G13。"
      },
      {
        "id": "F3",
        "original_score": 2,
        "prior_adjudicated_score": 2,
        "latest_author_proposal": 2,
        "approved_score": 2,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "独立委员会审查关联交易且金额较小；家族控制、亲属雇佣及一次Section16迟报构成治理瑕疵。",
        "original_evidence_refs": [
          "NKE-G-017；NKE-G-018；V3-004"
        ],
        "adjudication_reason": "维持2/3：独立审查及披露是正面，一次已核迟报属小瑕疵；海关争议保留风险而非既成处罚；不以亲属身份或作者漏项认定不公允/隐瞒。"
      }
    ],
    "management": [
      {
        "id": "诚信与透明度",
        "original_score": 15,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 16,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "官方披露完整且审计干净，CFO交接明确否认分歧；诉讼与内部交易仍有原件缺口。",
        "original_evidence_refs": [
          "NKE-G-005；NKE-G-006；V3-002；V3-004"
        ],
        "adjudication_reason": "删研究缺口与作者遗漏的诚信扣分，核实言行与已披露风险后重评；无原件证明其隐瞒。"
      },
      {
        "id": "资本配置能力",
        "original_score": 13,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 12,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "分红连续且暂停回购保护现金，但历史回购成本高、SBC显著、转型回报尚未兑现。",
        "original_evidence_refs": [
          "NKE-F-014；NKE-F-015；NKE-F-020"
        ],
        "adjudication_reason": "ROIC/WACC、回购及Capex效率桥未闭合。"
      },
      {
        "id": "战略稳定性",
        "original_score": 10,
        "prior_adjudicated_score": 10,
        "latest_author_proposal": 10,
        "approved_score": 10,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "运动与创新主线稳定，但DTC偏置后重新修复批发关系，执行路径发生较大调整。",
        "original_evidence_refs": [
          "S001 MD&A HTML L843-856；NKE-F-011"
        ],
        "adjudication_reason": "长期运动创新主线稳定而渠道路线调整确实存在；保留10分只评价战略稳定性，不能引用未核FY2025承诺落空；如目标原文改变这一事实则按实质新证据处理。"
      },
      {
        "id": "对股东友好度",
        "original_score": 11,
        "prior_adjudicated_score": 11,
        "latest_author_proposal": 11,
        "approved_score": 11,
        "status": "保留旧裁决分项，恢复原理由",
        "original_reason": "FY2026分红2.407十亿美元且有长期回购计划；双层股权削弱B类股东治理权。",
        "original_evidence_refs": [
          "NKE-F-015；NKE-G-017"
        ],
        "adjudication_reason": "分红与绩效约束已核、B类投票制衡弱；维持11分，不用未逐笔核交易作扣分或无减持保证。"
      },
      {
        "id": "危机处理能力",
        "original_score": 6,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 7,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "面对品牌和渠道修复已更换CEO并调整团队，但FY2026财务结果尚未证明转折。",
        "original_evidence_refs": [
          "NKE-F-011；V3-002"
        ],
        "adjudication_reason": "行动到结果桥、目标期限与关税现金效应待厘清。"
      },
      {
        "id": "组织与人才能力",
        "original_score": 7,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 8,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "核心高管多为长期内部人才，继任CFO具大型公司经验；高额补偿与多次岗位调整显示稳定性成本。",
        "original_evidence_refs": [
          "S001 executive officers；V3-002；V3-003"
        ],
        "adjudication_reason": "五年人事模式及人才效率缺口，外聘/补偿不是自动负面。"
      },
      {
        "id": "表达清晰度与认知质量",
        "original_score": 3,
        "prior_adjudicated_score": null,
        "latest_author_proposal": 4,
        "approved_score": null,
        "status": "作者修正候选，须逐项恢复理由并定向验收，不视为旧裁决批准",
        "original_reason": "10-K与代理声明能量化风险及绩效，但连续三年可直接核验的定量经营承诺有限。",
        "original_evidence_refs": [
          "S001 MD&A；NKE-G-022；V3-003"
        ],
        "adjudication_reason": "研究未找到原话不能直接等于公司表达差；需原始上下文。"
      }
    ]
  },
  "qualification_upper_bound_candidate": {
    "company": 74.5,
    "management": 70,
    "total": 144.5,
    "formula": "72.5-3.5(A3)-3.5(F1)+4+5=74.5；68-8(组织)+10=70",
    "approved": false,
    "condition": "仅当其余候选分项逐项由原件和评分理由证成、两路验收认可才生效；非从最新总分直接批准。A3/F1/组织使用满分是数学上限，不把未知作负面，也不默认为该分。",
    "rule": "B_GROWTH双分>=150且各>=70；A_CORE>=160且各>=76；S_STRATEGIC>=170且各>=82及其余硬门槛",
    "if_verified": "最高合计144.5<150，reject；即便组织满分管理层70也不能使合计达门槛。若任何固定项证据不成立，重列有据上界；跨门槛则defer。"
  },
  "industry_model": "非金融品牌公司可用FCFE/Ke与独立正常化PE；未闭合时仅保留正确诊断，不强凑正式双模型",
  "reverse_weight": 0,
  "decision": "defer",
  "research_status": "execution_incomplete",
  "decision_reason": "当前仍待一次修复和独立验收；资格上界尚未批准。",
  "closeout_rule": "已知错误未撤回=execution_incomplete；正确性隔离后仅不可知可closed_with_uncertainty，均不冒充完成定价三件套；verified_complete需全部实质验收。",
  "independent_checks": {
    "units": "USD millions；股数millions；每股USD",
    "historical_shares": "1476+3+6-2=1483，只证明期末股数；不能证明FY2027加权1487/1485/1480",
    "sbc": "278+58+379=715；期权行权现金155与员工净发行权益110不能直接当成9百万股全部现金筹资",
    "cash_tax": "1270-268-260=742仅历史剔除尺度，不是FY2027现金税预测",
    "eps_conditional": [
      1.2694014794889037,
      2.2438787878787876,
      3.0356756756756758
    ],
    "fcfe_conditional": [
      1117.6,
      2962.16,
      4422.8
    ],
    "buy_price_conditional": 25.65987,
    "approved": false
  },
  "score_bridge_warning": "prior_adjudicated_score仅表示旧裁决保留的分项，不表示整套审核通过。所有original_reason为历史文本定位，含已知错误者必须按本次和旧裁决纠正；尤其B1 Note19、E1杠杆归因、A3回购归因、F2未知内部交易、F3亲属身份、D2事后财务代替承诺等不得恢复为有效理由。"
}
```
