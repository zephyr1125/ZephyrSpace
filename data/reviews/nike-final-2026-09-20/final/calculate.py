import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OLD = ROOT / "data/reviews/nike-repair-2026-09-19-2310/final/workpaper-repaired-v2.json"
OUT = ROOT / "data/reviews/nike-final-2026-09-20/drafts/workpaper-v1.json"


def dcf_value(fcfe0: float, g: float, ke: float, gt: float) -> float:
    """按五年显式期加永续终值计算每股FCFE价值。"""
    explicit = sum(fcfe0 * (1 + g) ** year / (1 + ke) ** year for year in range(1, 6))
    terminal = fcfe0 * (1 + g) ** 5 * (1 + gt) / (ke - gt) / (1 + ke) ** 5
    return explicit + terminal


def grid(model_id: str, base: dict, x: str, xs: list[float], y: str, ys: list[float]) -> dict:
    """使用同一模型公式生成双变量敏感性矩阵。"""
    values = []
    for yv in ys:
        row = []
        for xv in xs:
            values_in = copy.deepcopy(base)
            values_in[x] = xv
            values_in[y] = yv
            if model_id == "fcfe_dcf":
                row.append(dcf_value(**values_in))
            else:
                row.append(values_in["eps"] * values_in["multiple"])
        values.append(row)
    return {"x": x, "y": y, "x_values": xs, "y_values": ys, "values": values}


data = json.loads(OLD.read_text(encoding="utf-8"))
data["schema_version"] = 1
data["reports"] = {
    "deep": "data/reviews/nike-final-2026-09-20/drafts/deep.md",
    "management": "data/reviews/nike-final-2026-09-20/drafts/management.md",
    "valuation": "data/reviews/nike-final-2026-09-20/drafts/valuation.md",
}

company_scores = {
    "A3": 3.5, "B1": 3.5, "B3": 4.0, "D2": 3.0, "D5": 2.0,
    "E1": 3.5, "E2": 5.0, "E3": 2.0, "E4": 0.5, "E5": 2.0,
    "E5.5": 2.5, "F1": 4.0, "F2": 4.0, "F2.5": 1.5,
}
company_reasons = {
    "A3": "FY2026与已核历史显示主业聚焦、商誉低且未见靠资产处置保利润；历史回购时机另在F2.5评价，故按清洁但并非满分计3.5。",
    "B1": "NIKE Brand具全球地区与批发/直营结构，Converse提供补充，但鞋类及主品牌集中度仍高，按健康但集中计3.5。",
    "B3": "品牌、创新和运动员资产支持溢价；五年毛利与促销事实证明转嫁并非无条件，按中等定价权计4。",
    "D2": "三条原始承诺可定位：一项部分兑现、两项仍在执行期；现有结果约为一半达标，按原规则计3。",
    "D5": "期末员工口径人效在FY2026改善但仍低于FY2024，且裁员会机械抬升指标；投入产出表现混合，计2。",
    "E1": "FY2024-FY2026 ROE均高于15%，但回购压低权益且净利率回落明显；经营驱动与资本结构共同作用，计3.5。",
    "E2": "FY2024-FY2026 OCF/净利均高于80%，简化FCF连续为正，严格落入原规则5分档。",
    "E3": "税务特殊付款及主要利润变化可辨，但量价与经常/非经常桥未完全拆开；按一次性因素可辨但非最优计2。",
    "E4": "现金短投覆盖融资债务，偿债能力宽裕；经营租赁及承诺限制缓冲，且Capex同比59.1%触发未拆分-0.5例外，计0.5。",
    "E5": "PwC无保留意见、ICFR有效、商誉低且准备项目有披露；库存规模仍需跟踪但未见重大疑点，计2。",
    "E5.5": "所得税CAM、准备与政策均有披露，未见重大会计异常；未确认税收利益及诉讼不确定性构成小瑕疵，计2.5。",
    "F1": "核心团队以长期内部人才为主，激励约束真实；CEO/CFO更替及转型结果待验，按稳定但有交接风险计4。",
    "F2": "持续分红、低谷暂停回购和绩效约束支持对齐；双层股权削弱制衡，逐笔内部交易未知不扣分，计4。",
    "F2.5": "暂停回购保存现金是正面，但历史高位回购、SBC与转型投入回报限制评价，计1.5，不使用额外正面先例加分。",
}
for item in data["scores"]["company"]["items"]:
    if item["id"] in company_scores:
        score = company_scores[item["id"]]
        item["score"] = score
        item["score_range"] = [score, score]
        item["reason"] = company_reasons[item["id"]]
        item["status"] = "本轮规则化评分，待独立复核"
data["scores"]["company"]["total"] = round(sum(i["score"] for i in data["scores"]["company"]["items"]), 6)
data["scores"]["company"].pop("candidate_range", None)

management_scores = {
    "诚信与透明度": 16.0,
    "资本配置能力": 12.0,
    "战略稳定性": 10.0,
    "对股东友好度": 11.0,
    "危机处理能力": 7.0,
    "组织与人才能力": 8.0,
    "表达清晰度与认知质量": 4.0,
}
management_reasons = {
    "诚信与透明度": "审计与ICFR结论干净，海关重大例外、CFO交接和一次迟报均有披露；诉讼结果未知不作失信扣分，计16。",
    "资本配置能力": "持续分红和低谷暂停回购为正面；历史回购效果、SBC、转型投入回报及交接成本显著限制评分，计12。",
    "战略稳定性": "运动与创新主线稳定，但DTC偏置后修复批发关系，执行路径曾明显偏航，维持10。",
    "对股东友好度": "持续分红、回购授权和绩效约束已核；双层股权削弱B类股东治理权，维持11。",
    "危机处理能力": "更换CEO、恢复运动品类和批发、暂停回购均已行动；收入企稳但利润与现金流未转折，计7。",
    "组织与人才能力": "长期内部人才与外聘CFO经验并存；CEO/CFO交接及转型结果待验，未证实异常密集离任，计8。",
    "表达清晰度与认知质量": "10-K和代理声明量化风险、绩效与薪酬，承诺边界可核；连续年度量化目标仍有限，计4。",
}
for item in data["scores"]["management"]["items"]:
    score = management_scores[item["id"]]
    item["score"] = score
    item["score_range"] = [score, score]
    if item["id"] in {"诚信与透明度", "资本配置能力", "危机处理能力", "组织与人才能力", "表达清晰度与认知质量"}:
        item["reason"] = management_reasons[item["id"]]
        item["status"] = "本轮规则化评分，待独立复核"
data["scores"]["management"]["total"] = sum(management_scores.values())
data["scores"]["management"].pop("candidate_range", None)

model_specs = {
    "bear": {"fcfe0": 1.20, "g": 0.02, "ke": 0.10, "gt": 0.02},
    "base": {"fcfe0": 1.48, "g": 0.06, "ke": 0.09, "gt": 0.025},
    "bull": {"fcfe0": 1.75, "g": 0.09, "ke": 0.085, "gt": 0.03},
}
dcf_scenarios = {}
for name, inputs in model_specs.items():
    dcf_scenarios[name] = {
        "inputs": inputs,
        "input_meta": {
            "fcfe0": {"unit": "USD/share", "date": "FY2026 normalised", "kind": "assumption", "evidence_refs": ["FY2026 OCF 2.868bn; capex 0.684bn; diluted shares about 1.48bn"]},
            "g": {"unit": "ratio", "date": "FY2027-FY2031", "kind": "assumption", "evidence_refs": ["Win Now recovery scenarios"]},
            "ke": {"unit": "ratio", "date": "2026-09-19", "kind": "assumption", "evidence_refs": ["USD mature consumer discretionary required return"]},
            "gt": {"unit": "ratio", "date": "FY2032+", "kind": "assumption", "evidence_refs": ["long-run nominal growth boundary"]},
        },
        "value": dcf_value(**inputs),
    }
pe_specs = {
    "bear": {"eps": 2.05, "multiple": 15.0},
    "base": {"eps": 2.45, "multiple": 18.0},
    "bull": {"eps": 2.85, "multiple": 21.0},
}
pe_scenarios = {}
for name, inputs in pe_specs.items():
    pe_scenarios[name] = {
        "inputs": inputs,
        "input_meta": {
            "eps": {"unit": "USD/share", "date": "FY2027E", "kind": "forecast", "evidence_refs": ["FY2026 diluted EPS about 2.10; author recovery scenarios"]},
            "multiple": {"unit": "x", "date": "2026-09-19", "kind": "assumption", "evidence_refs": ["mature global brand valuation range; current FY2026 PE about 16.9x"]},
        },
        "value": inputs["eps"] * inputs["multiple"],
    }

models = [
    {
        "id": "fcfe_dcf", "weight": 0.60,
        "basis": "公司自身可分配现金流的五年显式恢复与永续价值",
        "shared_assumptions": ["经营复苏会改善盈利与现金流；不另加未证实超额现金"],
        "output_currency": "USD", "output_unit": "per_share",
        "formula": "fcfe0*(1+g)/(1+ke)+fcfe0*(1+g)**2/(1+ke)**2+fcfe0*(1+g)**3/(1+ke)**3+fcfe0*(1+g)**4/(1+ke)**4+fcfe0*(1+g)**5/(1+ke)**5+fcfe0*(1+g)**5*(1+gt)/(ke-gt)/(1+ke)**5",
        "scenarios": dcf_scenarios,
        "sensitivity": grid("fcfe_dcf", model_specs["base"], "ke", [0.085, 0.09, 0.095], "gt", [0.02, 0.025, 0.03]),
    },
    {
        "id": "pe_recovery", "weight": 0.40,
        "basis": "成熟全球品牌的盈利倍数市场锚与FY2027恢复EPS",
        "shared_assumptions": ["与DCF共享经营复苏方向，但倍数为独立市场定价依据"],
        "output_currency": "USD", "output_unit": "per_share",
        "formula": "eps*multiple",
        "scenarios": pe_scenarios,
        "sensitivity": grid("pe_recovery", pe_specs["base"], "multiple", [15.0, 18.0, 21.0], "eps", [2.05, 2.45, 2.85]),
    },
]
weighted = {
    scenario: sum(model["weight"] * model["scenarios"][scenario]["value"] for model in models)
    for scenario in ("bear", "base", "bull")
}
certainty = 0.55
target = weighted["base"]
data["valuation"] = {
    "currency": "USD", "models": models, "weighted": weighted,
    "target_price": target, "certainty": certainty,
    "certainty_reason": "品牌与资产负债表较稳定，但转型现金流、税务争议、地区复苏和估值模型分歧使误差区间仍宽。",
    "buy_price": target * (0.68 + 0.14 * certainty),
    "reverse": {
        "weight": 0, "variable": "implied_eps", "implied_value": 35.51 / 18.0,
        "formula": "implied_eps*multiple", "inputs": {"implied_eps": 35.51 / 18.0, "multiple": 18.0},
        "market_price": 35.51,
        "assumptions": ["以基准18倍PE反推市场隐含FY2027 EPS", "只作反向验证，不参与合理价"],
        "evidence_refs": ["2026-09-18 close 35.51 USD", "base PE multiple assumption 18x"],
    },
}
data["bridges"] = []
data["bridges_not_applicable"] = "模型直接采用每股FCFE和每股EPS；不将现金、债务或租赁负债重复加减。FY2026期末股数桥及现金债务边界在正文单列，未来稀释作为情景风险而非伪精确桥。"

changed_company = list(company_scores)
changed_management = ["诚信与透明度", "资本配置能力", "危机处理能力", "组织与人才能力", "表达清晰度与认知质量"]
score_changes = []
for key in changed_company:
    score_changes.append({"key": f"company/{key}", "issue_id": "G07" if key not in {"D2", "D5", "F1"} else "G08", "reason": company_reasons[key], "evidence_refs": ["score-review-v2.json", "repaired-v2正文与旧中性证据包"]})
for key in changed_management:
    score_changes.append({"key": f"management/{key}", "issue_id": "G08" if key in {"危机处理能力", "组织与人才能力", "表达清晰度与认知质量"} else "G07", "reason": management_reasons[key], "evidence_refs": ["score-review-v2.json", "repaired-v2正文与旧中性证据包"]})
data["repair"] = {
    "issues": [
        {"id": "G03", "severity": "P1", "acceptance_ids": ["G03-eps", "G03-anchor", "G03-completion"]},
        {"id": "G05", "severity": "P1", "acceptance_ids": ["G05-tax"]},
        {"id": "G07", "severity": "P1", "acceptance_ids": ["G07-score"]},
        {"id": "G08", "severity": "P1", "acceptance_ids": ["G08-people", "G08-score"]},
    ],
    "score_changes": score_changes,
    "report_changes": [
        {"report": "deep", "section": "__preamble__", "issue_id": "G07", "reason": "更新唯一有效评分与诊断估值快照，旧撤回值保持作废。"},
        {"report": "deep", "section": "综合评分汇总", "issue_id": "G07", "reason": "恢复逐项规则化评分、总分和评分桥。"},
        {"report": "deep", "section": "维度 A：历史基因与公司 DNA", "issue_id": "G07", "reason": "将A3事实映射为3.5分并说明边界。"},
        {"report": "deep", "section": "维度 B：商业模式质量", "issue_id": "G07", "reason": "将B1/B3事实映射为明确点值。"},
        {"report": "deep", "section": "维度 D：战略清晰度与执行力", "issue_id": "G08", "reason": "按已核承诺和人效结果完成D2/D5评分。"},
        {"report": "deep", "section": "维度 E：财务质量（非估值）", "issue_id": "G07", "reason": "完成E1/E3/E4/E5/E5.5评分并修正税务字段。"},
        {"report": "deep", "section": "评分桥与收录判断", "issue_id": "G07", "reason": "新增公司、管理层及组合门槛的透明评分桥。"},
        {"report": "management", "section": "九、管理层100分制评分", "issue_id": "G08", "reason": "完成五项撤回分的规则化评分及总分。"},
        {"report": "management", "section": "六、组织与人才", "issue_id": "G08", "reason": "将已核人事与人效事实映射为8分及D5两分，未知动机不扣分。"},
        {"report": "management", "section": "七、IR态度与表达质量", "issue_id": "G08", "reason": "按披露可核性和量化承诺边界将表达质量定为4分。"},
        {"report": "management", "section": "十一、综合结论", "issue_id": "G08", "reason": "给出管理层明确结论与降级条件。"},
        {"report": "management", "section": "__preamble__", "issue_id": "G07", "reason": "更新唯一有效评分与诊断估值快照。"},
        {"report": "valuation", "section": "__preamble__", "issue_id": "G03", "reason": "撤销旧null状态，写入本轮诊断参数快照并保留待复核边界。"},
        {"report": "valuation", "section": "一、估值结论", "issue_id": "G03", "reason": "以两种不同依据主模型恢复正式三情景定价。"},
        {"report": "valuation", "section": "二、估值快照", "issue_id": "G03", "reason": "更新唯一有效参数与实际/预测口径。"},
        {"report": "valuation", "section": "三、核心财务与正常化", "issue_id": "G03", "reason": "补齐FY2024-FY2026 OCF、Capex、SBC及稀释股数。"},
        {"report": "valuation", "section": "四、现金、债务与股数桥", "issue_id": "G05", "reason": "修正FY2025/FY2026未确认税收利益，并明确953中742影响有效税率的原披露含义。"},
        {"report": "valuation", "section": "五、主模型一：五年FCFE DCF", "issue_id": "G03", "reason": "新增可复算现金流模型及敏感性。"},
        {"report": "valuation", "section": "六、主模型二：FY2027恢复PE", "issue_id": "G03", "reason": "新增市场倍数锚及敏感性。"},
        {"report": "valuation", "section": "七、综合加权与机械买入价", "issue_id": "G03", "reason": "恢复目标价、确定性、买入价和价格区。"},
        {"report": "valuation", "section": "八、零权重反向验证", "issue_id": "G03", "reason": "用市场价反推FY2027 EPS并保持零权重。"},
        {"report": "valuation", "section": "九、模型独立性与限制", "issue_id": "G03", "reason": "明确两主模型独立依据、共享假设和SBC处理。"},
        {"report": "valuation", "section": "十、风险与催化剂", "issue_id": "G03", "reason": "联动新模型与既有重大风险。"},
        {"report": "valuation", "section": "十一、事实、预测与未知", "issue_id": "G03", "reason": "分列实际值、作者假设与未知。"},
        {"report": "valuation", "section": "十二、反证与重估条件", "issue_id": "G03", "reason": "给出模型与评分门槛的可验证反证。"},
        {"report": "valuation", "section": "十三、来源", "issue_id": "G03", "reason": "加入本轮中性补证索引，保留旧冻结证据路径。"},
        {"report": "valuation", "section": "十四、一句话结论", "issue_id": "G03", "reason": "统一诊断价格与不收录结论。"},
        {"report": "valuation", "section": "十二、风险与催化剂", "replacement_section": "十、风险与催化剂", "issue_id": "G03", "reason": "章节顺序随完整模型恢复而调整，既有风险实质保留。"},
        {"report": "valuation", "section": "十三、事实、预测与未知", "replacement_section": "十一、事实、预测与未知", "issue_id": "G03", "reason": "章节顺序随完整模型恢复而调整，并补充本轮输入边界。"},
        {"report": "valuation", "section": "十四、反证与重估条件", "replacement_section": "十二、反证与重估条件", "issue_id": "G03", "reason": "章节顺序随完整模型恢复而调整。"},
        {"report": "valuation", "section": "十五、来源", "replacement_section": "十三、来源", "issue_id": "G03", "reason": "章节顺序调整并加入本轮证据索引。"},
        {"report": "valuation", "section": "十六、一句话结论", "replacement_section": "十四、一句话结论", "issue_id": "G03", "reason": "给出截至截止日的实质估值判断。"},
    ],
    "closures": [
        {"id": "G03", "locations": ["valuation.md：五至八"], "score_valuation_impact": "建立FCFE DCF与恢复PE两个主模型，目标价、买入价与反向验证重新计算。", "checks": [
            {"id": "G03-eps", "passed": True, "evidence": "valuation.md：六；FY2026实际EPS与FY2027三情景明确分列"},
            {"id": "G03-anchor", "passed": True, "evidence": "valuation.md：六；15/18/21倍作为独立市场倍数假设并给出限制"},
            {"id": "G03-completion", "passed": True, "evidence": "workpaper-v1.json valuation；两模型三情景、双变量、加权及反向验证闭合"},
        ]},
        {"id": "G05", "locations": ["deep.md：E会计估计；valuation.md：四"], "score_valuation_impact": "FY2025未确认税收利益1,026、FY2026为953，其中742若确认将影响有效税率；不得把742解释为现金税或未来税费预测。", "checks": [{"id": "G05-tax", "passed": True, "evidence": "两报告税务表按NKE-FNL-001逐项列示，并明确742的披露含义"}]},
        {"id": "G07", "locations": ["deep.md：评分表；management.md：评分表"], "score_valuation_impact": "公司分75.5、管理层68；所有已核事实按原规则完成点值判断。", "checks": [{"id": "G07-score", "passed": True, "evidence": "workpaper-v1.json scores及生成评分表"}]},
        {"id": "G08", "locations": ["deep.md：D/F；management.md：九、十一"], "score_valuation_impact": "人事未知不扣分；按已核更替、激励、承诺与结果给D2/D5/F1及管理层相关点值。", "checks": [
            {"id": "G08-people", "passed": True, "evidence": "management.md：组织与人才；仅CEO/CFO更替作为已核事实"},
            {"id": "G08-score", "passed": True, "evidence": "workpaper-v1.json对应评分理由与总分"},
        ]},
    ],
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"company": data["scores"]["company"]["total"], "management": data["scores"]["management"]["total"], "weighted": weighted, "target": target, "buy": data["valuation"]["buy_price"]}, ensure_ascii=False, indent=2))
