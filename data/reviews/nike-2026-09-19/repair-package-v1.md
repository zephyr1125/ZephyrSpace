# 唯一修复包

由已锁定裁决台账生成；裁决台账是唯一判断来源，本文不构成修复完成。

## G01 · P1 · valid

候选：C002, C006, C009

裁决理由：期末权益误用五季度平均值成立；杜邦、税务CAM与计提检查缺失成立。无保留审计不等于无需分析CAM，也不表示CAM本身构成会计异常。FY2026简化平均权益ROE为22.138329%，权益乘数2.670739，不能仅以回购史认定杠杆主导。原权益增加9.21亿美元不机械带来评分上调。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页31、54、57（PDF35、58、61）、47-48；NKE-F-012与原件冲突；deep-prebuy-skill/SKILL.md E1/E4/E5/E5.5

动作：局部覆盖错误事实并给原值→更正值桥；补三年杜邦、应收/库存及准备检查、所得税CAM和政策估计变化。冻结中性包不覆盖，在修订底稿显式引用更正。

联动：E1/E4/E5/E5.5待定；E2/E3联动G05。净资产、BVPS、PB、杠杆与所有评分引用同步；不凭审计意见直接维持13/20。

- G01-equity：期末权益14.865bn、FY2025 13.213bn；13.944bn仅标五季度平均；查清所有引用且区分2026-07-08股数与2026-05-31余额。
- G01-dupont：FY2024-FY2026逐年列净利率×平均资产周转×平均权益乘数=ROE，附期初期末原件；FY2026应复算6.698565%×1.237461×2.670739=22.138329%，解释经营与资本结构贡献。
- G01-accounting：所得税CAM、未确认税收利益953m及742m潜在税率影响、估计方法无重大改变、销售/库存准备及坏账/商誉检查有原文和金额或明确未披露限制；不能把税务不确定余额全额当新增损失。
- G01-score：逐项给E1/E4/E5/E5.5前后分数与规则依据；Capex增长59.07%触发E4拆分规则，无法拆分则显式按原规则减0.5并列扣前基分，不能把未披露虚写成已存在非运营支出；最终总分待所有相关验收闭合。

## G02 · P1 · partial

候选：C005, C007, C014

裁决理由：现金正常化桥和SBC处理缺失成立。报表FCF2.184bn不自动等于可持续FCFE；原基准3.412047bn高56.229259%。候选条件敏感性算术成立但不得作为修正目标价。FCFE加全现金减全债的现式口径未闭合；不能断言所有FCFE均不得加现金，关键是分配范围、利息与净借款不重复。租赁现金已在OCF，不能再无条件扣租赁负债。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页45、57-58、70、75-77、88-89；SBC费用表实际原页76/PDF80，候选写75不精确；skills/valuation/SKILL.md 方法矩阵、标准化FCF、综合加权；docs/three-report-workpaper.md bridges

动作：保留适用的FCFE/Ke现金模型，重建三情景经营现金→资本开支→净借款→股东现金桥，选择SBC经济扣费或逐年稀释一种；说明可分配现金与利息剔除、债务滚续或偿还，不沿用未闭合的净现金附加项。

联动：三个fcf0、现金调整和DCF价值均待定；原DCF38.192731及综合42.915639仅为旧假设试算。G05/G09调整进入同一桥，不能重复。

- G02-cashflow：三情景逐项从2.868bn CFO、0.684bn现金Capex开始或从经营预测复建并对账，区分实际/预测/假设；解释增量及增长再投资；reported_fcfe_bridge改名简化报表FCF或补齐净借款定义。
- G02-sbc：SBC0.715bn已在CFO加回；明确经济扣费或未来股数桥，现有81.8m反稀释奖励不机械全额新增股数；扣SBC时不得再重复扣相同稀释成本，PE EPS保留其已费用化属性。
- G02-equity：逐年融资/还本与20亿美元FY2027到期债处理明确；现金只加可分配且未在经营现金价值内的部分，利息收入不重复；若使用FCFE不再机械减全部债务。维持租赁租金后现金与负债一致性。
- G02-recalc：用最终输入独立重算两模型三情景、同权重综合值、DCF和PE双变量矩阵、机械价及三报告快照/正文/价格分区；原0.731是舍入值，1.085/1.483498703=0.731379136仅为报表净现金尺度，非已批准估值加项。

## G03 · P1 · insufficient

候选：C003, C017

裁决理由：两公式算术不同不证明第二独立估值依据。EPS2/2.5/3和PE17/20/24只有主观区间，不能核实FY2027经营实现路径及市场锚；FY2027-FY2028与正文FY2027期限也不一致。可采用自主预测，不强制卖方一致预期。

原件：writer/workpaper-v1.json valuation.models[pe_recovery]；估值分析/耐克 估值分析 2026-09-19.md 六至七章；skills/valuation/SKILL.md 第0步预测、第1步单模型试算、第2步

动作：补FY2027三情景盈利桥和至少一种同口径历史/可比市场锚；只需局部定向补证，无需重写全文。

联动：PE EPS/倍数/价值待定；60/40暂不批准为最终权重；目标价、确信度、买入价null，缺模型不能用低确信度替代。

- G03-eps：从地区/渠道收入至毛利、费用、利息、税率、稀释股数形成三情景EPS，标FY2027预测或统一另一期；与现金模型共享经营假设相互对账，正常化时点较远则明确折现。
- G03-anchor：给可核日期、样本、TTM/前瞻口径、非经常项目及风险成长调整，解释三档PE；历史分位与前瞻EPS不混用。
- G03-completion：两个有效且不同依据模型方可给最终权重与价格；补证失败明确估值未完成/单模型试算并保留null，不强造第二模型。

## G04 · P1 · valid

候选：C013, C018

裁决理由：静态PE除法及代回正确，但只是行情比率，不符合项目要求的市价隐含经营假设验证。反推必须复用修正后的主模型。

原件：估值分析/耐克 估值分析 2026-09-19.md 八章；skills/valuation/SKILL.md 反向验证参数

动作：将静态PE移回快照；用最终现金模型反求可持续现金或增长，或有证据PE下反求EPS/利润率。

联动：反向权重固定0；不改变主模型独立性要求。

- G04-solve：给市价35.51、日期、最终模型固定参数及隐含经济变量，代回误差可复核；在旧未批准参数下反推fcf0约2.135291仅可作条件示例。
- G04-sensitivity：至少一项关键固定变量敏感性、与实际/三情景对照及解的边界；权重为0，不把市价再次加权。

## G05 · P1 · valid

候选：C010

裁决理由：IEEPA退款收益986m与FY2026关税成本大体抵销、已收302m、应收684m且年后基本收回均属决定性遗漏。重组费用385m、付现142m、应付243m应分期。不能单剔退款收益、不剔对应成本；不能把回收永久化。另原页75现金税1270m含最后一期过渡税268m和FY2017-2019税务解决预付款260m，须解释正常化而非全额任意加回。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页30、45、58、75、89；deep-prebuy-skill/SKILL.md E2/E3；skills/valuation/SKILL.md 标准化现金桥

动作：利润桥与现金桥成对列示；与G02同一经济ID连接，按税务原文区分重复性与结算时点。

联动：E2/E3、B2的毛利解释、管理层危机/兑现归因及两个模型联动；不能以现金下降单独认定转型承诺失败。

- G05-paired：展示986m收益及相关成本、302m已收/684m应收、385m费用/142m支付/243m后续支付，说明历史2024重组443m提示重复发生可能；未来节约须单列假设。
- G05-tax：列现金税1270m及268m/260m特殊付款原文，明确可正常化金额与税率、未来支付关系；不可把税务余额或所有现金税当一次性加回。
- G05-once：684m年后收回只进入一次现金时点桥，不同时加估值现金、显式期流入并提高永续基数；三报告经营归因及G02/G03预测一致。

## G06 · P1 · partial

候选：C004

裁决理由：比利时海关索赔遗漏成立；公司Note16明确该例外可能重大不利且无法估计损失范围。13亿美元是全部银行担保和信用证，不能全部归该索赔或直接当损失/冻结现金。事项已披露，报告遗漏不能转化为管理层隐瞒；未有败诉结论不能判违规已成立。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页88 Note16（PDF92）；Item3原页25；deep-prebuy-skill/SKILL.md F3/F4；management-archive/SKILL.md 八/九

动作：三报告补事实、范围未知、上诉/担保和反证；检查估值现金缓冲与尾部风险，不编损失概率或金额。

联动：F3无需仅因报告漏项自动减分；诚信透明度不可据此当失信。确信度须重评，但null仍由模型未闭合决定。

- G06-risk：写清自FY2018进口、公司争议并上诉、银行担保、损失范围不可估计、若败诉可能重大影响；Item3与Note16例外并列。
- G06-limits：13亿美元保函/信用证为总体，具体索赔担保、保证金和限制现金未披露则未知；不等同13亿美元损失；估值尾部风险、现金缓冲和触发重估条件可执行。
- G06-score：逐项说明F3与诚信分数影响或不变依据，区分潜在合规风险、已核处罚和公司披露质量。

## G07 · P1 · partial

候选：C008, C019

裁决理由：资本配置量化不足、研究缺口当治理扣分及省略补偿背景成立。97.57对35.51的事后跌幅可揭示回购风险，不能等同当时已可知的价值毁损或资本运作不清洁。8-K说明新聘款弥补前职放弃薪酬并附条件，单次外聘不证明内部继任链失效；亲属身份不证明不公允。不同维度可使用同一事实评价不同后果，但不能重复无解释扣分。C019反对缺资料扣分的原则不覆盖E4明文Capex未拆分减0.5的项目例外。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页31、45、58、75-77；https://www.sec.gov/Archives/edgar/data/320187/000032018726000070/nke-20260616.htm Item5.02 L74-101；https://www.sec.gov/Archives/edgar/data/320187/000032018726000089/nke-20260715.htm L2196-2217；deep-prebuy-skill/SKILL.md A3、F2/F2.5/F3；management-archive/SKILL.md 三、六、九

动作：回购质量归资本配置，补时点/价值约束、净股数与融资/Capex效率；重建相关扣分桥，不按候选预定总分。

联动：A3原扣分理由不成立、最终数值待融资用途/资本运作证据小结；F2/F2.5及管理层资本配置/人才/诚信/表达待重评；F3可维持2但理由只用已核披露瑕疵及中等治理风险，不用亲属身份自动扣分。

- G07-allocation：ROIC18.7%/20.2%与口径匹配WACC比较，不能拿Ke直接当WACC；回购124.4m股/约12.1bn/97.57均价，FY2026计划执行122.4m/67.63与现金流146m分列并解释差异/未知；股数净变动及SBC抵消、融资和Capex效率有桥。
- G07-attribution：CFO补偿写make-whole、服务/绩效/返还约束；删仅外聘推断继任不足、仅未核交易推断治理缺陷、仅亲属身份推断不公允。正常研究未知单列；E4明确规则例外照执行。
- G07-score：列A3/F2/F2.5/F3及管理层相关七维的旧分→最终分→证据→规则；保留分数也重新说明，不因删错理由直接满分，不用事后股价差直接认定重大资本配置失败；正面先例加0.5须最终成功证据。

## G08 · P1 · valid

候选：C016, C021

裁决理由：连续三年原始目标—期限—实际结果桥缺失，薪酬支付并非事前经营目标。FY2026年报预计动作2026年12月完成且中国/Converse负面影响贯穿FY2027，不可在截止日把尚未到期动作判失败。当前D2 original_statement_found=true无对应证据；缺目标不等于失信。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页30；writer/workpaper-v1.json D2；deep-prebuy-skill/SKILL.md D2/D5上限条款；management-archive/SKILL.md 二、六；references/pitfalls.md M3/M7/M8

动作：定向补连续三年年度原始目标及兑现和近五年人事时间线；区分前后CEO责任、行动与结果、未到期与落空。

联动：D2/D5及管理层战略/危机/人才/表达分项待定；D1战略漂移不因渠道调整自动置true；总分不可维持72/65作最终。

- G08-promises：连续三年每项保留当时原文上下文、发布日、目标期限、责任人、实际对照、已达/未达/进行中/未知；只对可核目标算达成率，不能用事后方向标签替代。
- G08-cap：D2原话标记与证据一致；若无第1/2优先级而有年报间接执行表，应用4/5上限并标中等置信度；仅同时证实战略漂移才3/5。上限不是自动得分，执行表仍缺则null。
- G08-people：近五年核心任离职表、原因/接任来源与集中离任模式；D5至少近三年人均收入等适用效率指标，研发未单列则写限制；不凭单次外聘断继任链失败。
- G08-score：原始目标与现金归因G05连通，D2/D5/F1及管理层相关分项有评分桥；依项目≤40%维度警戒重算，不新增门槛。

## G09 · P1 · partial

候选：C020, C011

裁决理由：分部量化与经营承诺缺失成立，Note19误引成立（分部实际Note15）。供应商融资余额1.1bn已在应付账款且公司不提供担保，不能自动另加有息债务；余额FY2026对FY2025约持平，不说明当年现金下降由此导致。承诺是经营现金需求，不可把总额全数资本化扣债。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页46、85-89（分部Note15；供应商融资Note19）；deep-prebuy-skill/SKILL.md B1/E4

动作：补紧凑地区/品牌分部及渠道/产品结构、经营现金承诺期限和现金覆盖；供应商融资附注并入现金质量，不单独制造P1。

联动：B1/E4及G02现金缓冲联动；采购/代言若已在预测成本或营运资金内不得重复扣减。

- G09-segments：FY2024-FY2026分部收入与EBIT、增速并核合计；至少北美/EMEA/中国/APLA/Converse与Global Brand/Corporate桥，地区、品牌、渠道、产品不混加；Note15引用修正。
- G09-commitments：代言15.5bn/12个月1.7、产品采购4.9/4.7、其他采购2.4/1.6列时点及限定词；逐项说明经营预测覆盖与未覆盖现金缓冲，禁止全额扣债。
- G09-supplier：供应商融资1.1/1.1/0.8bn（FY2026/25/24），已在应付账款，无担保；评估变动对营运资金，无重复融资债务或臆定当年融资增量。

## G10 · P2 · valid

候选：C001

裁决理由：FY2024 3.76为基本EPS、稀释EPS3.73，比较口径应更正；不直接改变当前算术。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页77 Note10

动作：将历史峰值比较统一为FY2024稀释EPS3.73。

联动：当前PE预测桥仍由G03决定，不因0.03差异单独调整倍数或目标。

- G10-eps：正文与底稿历史比较均用稀释3.73、实际FY2024标签；当前FY2026约2.10与FY2027预测分开。

## G11 · P2 · partial

候选：C012

裁决理由：缺PB/PS/FCF Yield及历史背景成立；可得历史分位需同口径，无法可靠获取允许标缺，不因此虚构。市场工具市值52.611616bn与价格×7月股数52.679039bn略异，应标来源分母，不能当同时点精确股本。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页57、58；封面PDF2股数日期2026-07-08；skills/valuation/SKILL.md 输出模板

动作：补当前倍数快照与清楚日期分母；PE市场锚的必要补证已归G03。

联动：以跨日7月股数作近似，BVPS10.020231、PB3.543830、PS1.135373、报表FCF Yield4.145862%；非新目标价。

- G11-snapshot：明确35.51与2026-07-08 A+B股数推算市值52.679039bn是跨日近似；PB/PS/报表及正常化FCF Yield各日期、单位、性质齐全；缺历史分位标未覆盖，不能宣称已经验证低分位。

## G12 · P1 · insufficient

候选：C015

裁决理由：B3强定价权5/6缺五年毛利、提价与同行验证属实。44.6/42.7/42.9三年毛利本身既不能证明强定价权也不足证明消失；退税/成本、产品折扣和渠道结构需分开。候选标P2，但其直接影响最终公司评分且原规则列必查，提升为P1局部闭合，不自动减分。

原件：财报/耐克/耐克FY2026_10-K.pdf 原页30、86-87；deep-prebuy-skill/SKILL.md B3

动作：补五年毛利、可核ASP/提价/折扣原文、至少可得同行可比口径；不能获得精确行业均值则清楚限制并用可核证据完成分档判断。

联动：B3最终分待定，与PE净利率及现金盈利修复假设相互约束；不把所有品牌强度证据等同定价权。

- G12-pricing：五年毛利趋势、主动提价/折扣/ASP证据和同行可比性说明；IEEPA成对影响剔除/保留一致；对5/6重新给规则和证据，不足则留待定而非仅调置信度后保留分数。

## 最终参数或待定原因

```json
{
  "currency": "USD",
  "company_score": null,
  "management_score": null,
  "target_price": null,
  "certainty": null,
  "buy_price": null,
  "pending_reason": "公司与管理层若干分项的事实→规则桥未闭合，不能确认72/65；FCFE正常化、权益现金及第二模型市场锚尚不充分，不能确认42.915639/0.55/32.487138。正常化并非不允许，而是不得无桥设值。",
  "company_score_bridge": {
    "previous_total": 72,
    "final_total": null,
    "items": [
      {
        "id": "A1",
        "previous": 3,
        "final": 3,
        "delta": 0,
        "reason": "运动产品创新及品牌先发基因未被本轮新证据推翻。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "A2",
        "previous": 3,
        "final": 3,
        "delta": 0,
        "reason": "控制权长期稳定；公众制衡问题归治理，不改变稳定性事实。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "A3",
        "previous": 3.5,
        "final": null,
        "delta": null,
        "reason": "应删事后价格跌幅对资本清洁度的扣分，仍需对融资用途及资本运作清洁度给正面证据后定分，不能直接加满。",
        "issue_ids": [
          "G07"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "B0",
        "previous": 2,
        "final": 2,
        "delta": 0,
        "reason": "设计/品牌/合同制造商业模式可核。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "B1",
        "previous": 3,
        "final": null,
        "delta": null,
        "reason": "原件分部可以补齐，但现分项依据误引且缺结构量化，局部桥完成后定分。",
        "issue_ids": [
          "G09"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "B2",
        "previous": 2,
        "final": 2,
        "delta": 0,
        "reason": "可选消费且低转换成本的经济属性未变；关税桥改变盈利归因不改变该项基本模式判断。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "B3",
        "previous": 5,
        "final": null,
        "delta": null,
        "reason": "定价权强度与周期/同行证据待闭合。",
        "issue_ids": [
          "G12"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "B4",
        "previous": 2.5,
        "final": 2.5,
        "delta": 0,
        "reason": "成熟市场与近两年收入疲弱仍支持原谨慎判断。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "C1",
        "previous": 6,
        "final": 6,
        "delta": 0,
        "reason": "全球规模第一梯队判断无决定性反证。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "C2",
        "previous": 3,
        "final": 3,
        "delta": 0,
        "reason": "合同制造优势与供应地域集中、关税制约并存。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "C3+C4",
        "previous": 7,
        "final": 7,
        "delta": 0,
        "reason": "品牌、研发、运动员和渠道壁垒同时有低切换成本限制；本轮没有支持机械改变7分的新事实。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "D1",
        "previous": 3,
        "final": 3,
        "delta": 0,
        "reason": "运动创新主线与可解释渠道修正并存；D2履约不可混作D1战略漂移。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "D2",
        "previous": 2.5,
        "final": null,
        "delta": null,
        "reason": "无可核三年原始目标兑现表；上限不能替代评分。",
        "issue_ids": [
          "G08"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "D3",
        "previous": 1,
        "final": 1,
        "delta": 0,
        "reason": "外部需求、贸易及竞争逆风仍在。",
        "issue_ids": [],
        "status": "retained_for_this_adjudication"
      },
      {
        "id": "D5",
        "previous": 1.5,
        "final": null,
        "delta": null,
        "reason": "组织效率及人事时间线待闭合。",
        "issue_ids": [
          "G08"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "E1",
        "previous": 3,
        "final": null,
        "delta": null,
        "reason": "三年杜邦与回购/经营驱动分解待补。",
        "issue_ids": [
          "G01"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "E2",
        "previous": 3,
        "final": null,
        "delta": null,
        "reason": "现金转化全周期总体良好，但应收退款、税款、SBC及现金归因影响原评分。",
        "issue_ids": [
          "G05"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "E3",
        "previous": 1.5,
        "final": null,
        "delta": null,
        "reason": "一次性关税与重组须成对正常化，不能只用净利下降定增长质量。",
        "issue_ids": [
          "G05"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "E4",
        "previous": 1,
        "final": null,
        "delta": null,
        "reason": "资本结构量化与Capex强制减0.5前基分待核；关联G09现金承诺。",
        "issue_ids": [
          "G01"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "E5",
        "previous": 2,
        "final": null,
        "delta": null,
        "reason": "资产质量和准备检查未完成。",
        "issue_ids": [
          "G01"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "E5.5",
        "previous": 2.5,
        "final": null,
        "delta": null,
        "reason": "税务CAM与政策/计提量化检查未完成，不因没有MD而直接中性给分（原PDF已可用）。",
        "issue_ids": [
          "G01"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "F1",
        "previous": 4,
        "final": null,
        "delta": null,
        "reason": "时间线/稳定性需补，不能以单次外聘或薪酬金额直接扣。",
        "issue_ids": [
          "G08"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "F2",
        "previous": 4,
        "final": null,
        "delta": null,
        "reason": "把未核内部交易移到未知，按已核分红/激励/融资及双层治理作用重评。",
        "issue_ids": [
          "G07"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "F2.5",
        "previous": 1,
        "final": null,
        "delta": null,
        "reason": "回购价值、ROIC/WACC和Capex产出待闭合。",
        "issue_ids": [
          "G07"
        ],
        "status": "pending_evidence"
      },
      {
        "id": "F3",
        "previous": 2,
        "final": 2,
        "delta": 0,
        "reason": "维持2/3：独立审查及披露是正面，一次已核迟报属小瑕疵；海关争议保留风险而非既成处罚；不以亲属身份或作者漏项认定不公允/隐瞒。",
        "issue_ids": [
          "G06",
          "G07"
        ],
        "status": "retained_for_this_adjudication"
      }
    ],
    "aggregation": "25项全部闭合后按原权重求和；C3+C4一个合并项；不得用已定部分求暂定总分或倒填未定分项。"
  },
  "management_score_bridge": {
    "previous_total": 65,
    "final_total": null,
    "items": [
      {
        "id": "诚信与透明度",
        "previous": 15,
        "final": null,
        "delta": null,
        "issue_ids": [
          "G06",
          "G07",
          "G08"
        ],
        "reason": "删研究缺口与作者遗漏的诚信扣分，核实言行与已披露风险后重评；无原件证明其隐瞒。"
      },
      {
        "id": "资本配置能力",
        "previous": 13,
        "final": null,
        "delta": null,
        "issue_ids": [
          "G07"
        ],
        "reason": "ROIC/WACC、回购及Capex效率桥未闭合。"
      },
      {
        "id": "战略稳定性",
        "previous": 10,
        "final": 10,
        "delta": 0,
        "issue_ids": [
          "G08"
        ],
        "reason": "长期运动创新主线稳定而渠道路线调整确实存在；保留10分只评价战略稳定性，不能引用未核FY2025承诺落空；如目标原文改变这一事实则按实质新证据处理。"
      },
      {
        "id": "对股东友好度",
        "previous": 11,
        "final": 11,
        "delta": 0,
        "issue_ids": [
          "G07"
        ],
        "reason": "分红与绩效约束已核、B类投票制衡弱；维持11分，不用未逐笔核交易作扣分或无减持保证。"
      },
      {
        "id": "危机处理能力",
        "previous": 6,
        "final": null,
        "delta": null,
        "issue_ids": [
          "G05",
          "G08"
        ],
        "reason": "行动到结果桥、目标期限与关税现金效应待厘清。"
      },
      {
        "id": "组织与人才能力",
        "previous": 7,
        "final": null,
        "delta": null,
        "issue_ids": [
          "G07",
          "G08"
        ],
        "reason": "五年人事模式及人才效率缺口，外聘/补偿不是自动负面。"
      },
      {
        "id": "表达清晰度与认知质量",
        "previous": 3,
        "final": null,
        "delta": null,
        "issue_ids": [
          "G07",
          "G08"
        ],
        "reason": "研究未找到原话不能直接等于公司表达差；需原始上下文。"
      }
    ],
    "aggregation": "七项依原满分20/25/15/15/10/10/5求和；诚信≤8或资本配置≤10触发原红旗。"
  },
  "valuation": {
    "economic_model": "非金融品牌消费企业，适用可持续现金流估值与有独立市场证据的正常化PE；无需套用金融模型，也不因FCFE难建而把EPS当FCF。",
    "primary_models": [
      {
        "id": "fcfe_dcf",
        "status": "applicable_inputs_pending",
        "weight": null,
        "fcf0": {
          "bear": null,
          "base": null,
          "bull": null
        },
        "g": null,
        "ke": null,
        "tg": null,
        "cash_equity_adjustment": null,
        "reason": "保留FCFE配Ke，按G02/G05/G09重建。现有增长与折现率可作为待论证假设，但不得视作已核实际，给定经济依据及期限，再由修复结果检验。"
      },
      {
        "id": "pe_recovery",
        "status": "independent_anchor_pending",
        "weight": null,
        "eps": {
          "bear": null,
          "base": null,
          "bull": null
        },
        "pe": {
          "bear": null,
          "base": null,
          "bull": null
        },
        "reason": "EPS经营桥与同期市场锚待G03，先统一预测期。"
      }
    ],
    "reverse": {
      "weight": 0,
      "variable": "最终现金模型的隐含可持续FCFE或增长（或有证据PE下的EPS/利润率）",
      "implied_value": null
    },
    "weighted": {
      "bear": null,
      "base": null,
      "bull": null
    },
    "target_price": null,
    "certainty": null,
    "buy_price": null,
    "buy_price_formula": "target_price * (0.68 + 0.14 * certainty)",
    "certainty_rule": "待两有效模型、五项确定性依据及尾部风险闭合后判定；不能因公司质量、研究缺口或目标价想贴近市价而任定。",
    "price_zones": null
  },
  "verified_numeric_inputs": {
    "period_end_equity_usd_bn": 14.865,
    "previous_equity_usd_bn": 13.213,
    "five_quarter_average_equity_usd_bn": 13.944,
    "cash_and_st_investments_usd_bn": 9.027,
    "interest_bearing_debt_book_usd_bn": 7.942,
    "operating_lease_liability_usd_bn": 3.091,
    "debt_due_fy2027_usd_bn": 2,
    "total_shares": 1483498703,
    "shares_date": "2026-07-08（并非2026-05-31期末精确股数）",
    "fy2026_cfo_usd_bn": 2.868,
    "fy2026_cash_capex_usd_bn": 0.684,
    "fy2026_simplified_fcf_usd_bn": 2.184,
    "fy2026_sbc_usd_bn": 0.715,
    "fy2024_diluted_eps": 3.73,
    "ieepa_benefit_usd_bn": 0.986,
    "ieepa_collected_by_year_end_usd_bn": 0.302,
    "ieepa_receivable_usd_bn": 0.684,
    "severance_expense_usd_bn": 0.385,
    "severance_paid_usd_bn": 0.142,
    "severance_accrued_usd_bn": 0.243,
    "reference_market_price": 35.51,
    "reference_market_date": "2026-09-18",
    "market_limit": "复用V3-005第三方历史行情核验，非交易所原件；盘后时间戳不能证明收盘。"
  },
  "independent_calculations": {
    "fy2026_margin": 0.06698564593301436,
    "fy2026_asset_turnover": 1.237461494352505,
    "fy2026_equity_multiplier": 2.670738656599473,
    "fy2026_roe_simple_average": 0.2213832894080775,
    "reference_market_cap_usd_bn": 52.67903894353,
    "reference_bvps": 10.020231207441777,
    "reference_pb": 3.5438304031974432,
    "reference_ps": 1.1353730536559763,
    "reported_fcf_yield": 0.041458615111433,
    "reported_fcf_per_share": 1.4721954226069858,
    "sbc_per_reference_share": 0.4819687395439536,
    "old_base_fcfe_uplift_usd_bn": 1.2280470169,
    "old_base_fcfe_uplift_percent": 56.22925901556775,
    "conditional_reported_fcf_dcf": 24.70969086680943,
    "conditional_sbc_subtracted_dcf": 30.342564410025474,
    "conditional_market_implied_fcf0": 2.135291075198767,
    "method": "直接独立标量计算，未以作者脚本代替。条件DCF均仅沿用旧g5%、Ke9.5%、tg2.5%、net_cash0.731以检验量级；这些不是修正价格。跨日股数倍数均为近似。"
  },
  "gate_and_level": {
    "redline_conclusion": "未见已证实新增一票否决或任意两条不入出口；OCF/净利92.28%未触发20%线，海关索赔不能当已判违规；未完成不等于不入。",
    "watchlist_level": null,
    "max_position": null,
    "reason": "最终评分与完整三件套验收待定，不能给档位或具体仓位；沿用当前S≥170且双方≥82并满足S附加条件，A≥160且双方≥76，B≥150且双方≥70。A/B不添加确定性硬门槛。",
    "completion_condition": "所有P0/P1逐验收ID实质关闭、双路定向复查后由主Agent按现有规则处理；本裁决不修改公司页/索引/Watchlist。"
  }
}
```
