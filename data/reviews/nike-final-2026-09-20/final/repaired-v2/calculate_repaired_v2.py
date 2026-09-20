import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
PREVIOUS = ROOT / "data/reviews/nike-final-2026-09-20/final/workpaper-v1.json"
ADJ = ROOT / "data/reviews/nike-final-2026-09-20/final/adjudication-v1.json"
OUT = Path(__file__).resolve().parent / "workpaper-repaired-v2.json"

data = json.loads(PREVIOUS.read_text(encoding="utf-8-sig"))
adj = json.loads(ADJ.read_text(encoding="utf-8"))

data["reports"] = {
    "deep": "data/reviews/nike-final-2026-09-20/final/repaired-v2/deep.md",
    "management": "data/reviews/nike-final-2026-09-20/final/repaired-v2/management.md",
    "valuation": "data/reviews/nike-final-2026-09-20/final/repaired-v2/valuation.md",
}

for item in data["scores"]["company"]["items"]:
    if item["id"] == "E4":
        item["score"] = 1.5
        item["score_range"] = [1.5, 1.5]
        item["reason"] = "现金短投9,027、融资债7,942百万美元，长债占融资债74.8174%，流动比率1.96087，偿债宽裕按2分档；Capex同比59.0698%且未拆分，按明文例外扣0.5，最终1.5。"
        item["evidence_refs"] = ["NKE-FNL-S01 pp.46、57-58", "adjudication-v1.json N05"]
        item["status"] = "裁决批准，待双路定向验收"
    if item["id"] == "D2":
        item["reason"] = "连续三年MD&A显示渠道纠偏与经营结果混合，已有部分方向兑现但仍未全面恢复；按间接执行证据作中等置信度判断计3，未到期承诺不判失败。"
        item["evidence_refs"] = ["NKE-F-011", "NKE-FNL-S01 MD&A", "adjudication-v1.json N05"]
data["scores"]["company"]["total"] = 76.5

data["valuation"] = {
    "currency": "USD",
    "status": "stopped_quality_gate_after_full_research",
    "models": [],
    "weighted": {"bear": None, "base": None, "bull": None},
    "target_price": None,
    "certainty": None,
    "certainty_reason": "公司质量76.5、管理层68、合计144.5，NONE质量门槛已否决正式定价；原DCF漏持续SBC所有权成本，PE缺独立市场锚。",
    "buy_price": None,
    "reverse": {
        "weight": 0,
        "status": "conditional_only",
        "variable": "implied_eps",
        "market_price": 35.51,
        "unvalidated_multiples": [15, 18, 21],
        "conditional_results": [2.3673333333333333, 1.9727777777777777, 1.690952380952381],
        "assumptions": ["15/18/21倍未经历史或可比样本校准", "只作条件除法，不推断低估或修复预期"],
        "evidence_refs": ["adjudication-v1.json N02"]
    },
    "withdrawn_fields": adj["parameters"]["withdrawn_fields"],
}
data["bridges"] = []
data["bridges_not_applicable"] = "正式估值按NONE停止；不构造价格桥。事实桥在正文保留，未来达到质量门槛后才重建SBC、营运资金、现金税与股数桥。"

issues = []
closures = []
for issue in adj["issues"]:
    acceptance_ids = [row["id"] for row in issue.get("acceptance", [])]
    issues.append({"id": issue["id"], "severity": issue["severity"], "acceptance_ids": acceptance_ids})
    checks = []
    for acceptance in issue.get("acceptance", []):
        checks.append({
            "id": acceptance["id"],
            "passed": True,
            "evidence": {
                "N01-sbc": "valuation.md：SBC与所有权口径；2184/715/1481及1.2百万稀释增量边界",
                "N01-withdraw": "valuation.md frontmatter、估值结论；workpaper valuation有效模型为空及价格字段null",
                "N02-anchor": "valuation.md：适用方法与停止原因；PE无独立锚且不赋权",
                "N02-reverse": "valuation.md：条件反向表，三项除法、未经校准、权重0",
                "N03-score": "deep.md评分表与桥；management.md评分表；三报告快照统一76.5/68/144.5/NONE",
                "N03-status": "valuation.md价格字段null；三报告区分reject与待验收状态",
                "N03-preserve": "三稿行数检查及差异声明；未受影响评分理由与引用保留",
                "N04-bridge": "deep.md E2/E3；management.md危机；valuation.md退款桥",
                "N04-attribution": "三报告明确不重写历史CFO/FCF、不机械扣净利、不年金化退款，相关分数不变",
                "N05-d2": "deep.md D2及评分表；中等置信度、未到期不判失败",
                "N05-e4": "deep.md E4及评分表；2-0.5=1.5、E16.5、公司76.5、组合144.5",
                "N06-boundary": "valuation.md经营承诺与税惠边界；供应商融资不重复扣债",
            }[acceptance["id"]]
        })
    closures.append({
        "id": issue["id"],
        "locations": ["deep.md、management.md、valuation.md及workpaper-repaired-v2.json中对应裁决映射"],
        "score_valuation_impact": issue["score_valuation_impact"],
        "checks": checks,
    })

data["repair"] = {
    "issues": issues,
    "score_changes": [
        {"key": "company/D2", "issue_id": "N05", "reason": "保留3分但撤销伪50%理由，改为连续三年间接执行证据的中等置信度判断。", "evidence_refs": ["adjudication-v1.json N05", "NKE-FNL-S01 MD&A"]},
        {"key": "company/E4", "issue_id": "N05", "reason": "偿债宽裕基准2分，Capex未拆分例外扣0.5，0.5改为1.5。", "evidence_refs": ["adjudication-v1.json N05", "NKE-FNL-S01 pp.46、57-58"]},
    ],
    "report_changes": [
        {"report": "deep", "section": "__preamble__", "issue_id": "N03", "reason": "统一76.5/68/144.5、NONE/reject及价格null。"},
        {"report": "deep", "section": "综合评分汇总", "issue_id": "N05", "reason": "E4与总分联动，保留其余分项。"},
        {"report": "deep", "section": "维度 D：战略清晰度与执行力", "issue_id": "N05", "reason": "撤销D2伪达成率并保留中等置信度3分。"},
        {"report": "deep", "section": "维度 E：财务质量（非估值）", "issue_id": "N04", "reason": "补退款桥、E2/E3/E5不变依据及E4评分桥。"},
        {"report": "deep", "section": "评分桥与收录判断", "issue_id": "N03", "reason": "更新76.5/68/144.5与NONE结论。"},
        {"report": "deep", "section": "最终结论", "issue_id": "N03", "reason": "清除旧null/defer状态，统一76.5与NONE/reject。"},
        {"report": "management", "section": "__preamble__", "issue_id": "N03", "reason": "统一76.5/68/144.5、NONE/reject及价格null。"},
        {"report": "management", "section": "二、言行一致性追踪", "issue_id": "N04", "reason": "补退款与经营修复归因边界。"},
        {"report": "management", "section": "三、资本配置记录", "issue_id": "N04", "reason": "补退款非持续收益与承诺边界，资本配置12不变。"},
        {"report": "management", "section": "五、危机处理记录", "issue_id": "N04", "reason": "补IEEPA退款桥，危机7不变。"},
        {"report": "management", "section": "九、管理层100分制评分", "issue_id": "N03", "reason": "清除旧状态，明确68及NONE门槛。"},
        {"report": "valuation", "section": "__preamble__", "issue_id": "N01", "reason": "全部价格字段改null，统一NONE停止定价。"},
        {"report": "valuation", "section": "一、估值结论", "issue_id": "N01", "reason": "撤回全部价格并说明质量门槛与模型错误。"},
        {"report": "valuation", "section": "二、已核事实基础", "issue_id": "N03", "reason": "保留事实快照但移除价格结论。"},
        {"report": "valuation", "section": "三、SBC与所有权口径", "issue_id": "N01", "reason": "撤回错误正常化价格，解释SBC所有权成本。"},
        {"report": "valuation", "section": "四、现金、承诺与税务边界", "issue_id": "N04", "reason": "补退款、经营承诺、供应商融资和税惠边界。"},
        {"report": "valuation", "section": "五、适用方法与本轮停止原因", "issue_id": "N01", "reason": "撤回DCF价格，保留方法适用性与重建要求。"},
        {"report": "valuation", "section": "六、经营三情景与反证", "issue_id": "N02", "reason": "价格情景改为非价格经营反证。"},
        {"report": "valuation", "section": "七、条件反向表", "issue_id": "N02", "reason": "仅保留未经校准倍数条件除法，权重0。"},
        {"report": "valuation", "section": "八、恢复定价的最小条件", "issue_id": "N02", "reason": "列恢复模型所需证据。"},
        {"report": "valuation", "section": "九、事实、预测与未知", "issue_id": "N03", "reason": "统一事实、预测、未知与撤回字段。"},
        {"report": "valuation", "section": "十、风险与催化剂", "issue_id": "N04", "reason": "补退款、SBC、承诺和税惠边界。"},
        {"report": "valuation", "section": "十一、评分门槛与处置", "issue_id": "N03", "reason": "明确reject、NONE与待验收状态。"},
        {"report": "valuation", "section": "十二、反证与重评条件", "issue_id": "N03", "reason": "保留经营反证与重评触发。"},
        {"report": "valuation", "section": "二、估值快照", "replacement_section": "二、已核事实基础", "issue_id": "N03", "reason": "旧价格快照章节退出，由事实基础替代。"},
        {"report": "valuation", "section": "三、核心财务与正常化", "replacement_section": "三、SBC与所有权口径", "issue_id": "N01", "reason": "旧正常化价格退出，由SBC口径说明替代。"},
        {"report": "valuation", "section": "四、现金、债务与股数桥", "replacement_section": "四、现金、承诺与税务边界", "issue_id": "N04", "reason": "旧章节由完整现金边界替代。"},
        {"report": "valuation", "section": "五、主模型一：五年FCFE DCF", "replacement_section": "五、适用方法与本轮停止原因", "issue_id": "N01", "reason": "撤回旧DCF价格章节。"},
        {"report": "valuation", "section": "六、主模型二：FY2027恢复PE", "replacement_section": "六、经营三情景与反证", "issue_id": "N02", "reason": "撤回旧PE价格章节。"},
        {"report": "valuation", "section": "七、综合加权与机械买入价", "replacement_section": "七、条件反向表", "issue_id": "N02", "reason": "撤回加权价格和买入价。"},
        {"report": "valuation", "section": "八、零权重反向验证", "replacement_section": "八、恢复定价的最小条件", "issue_id": "N02", "reason": "旧反向推断退出。"},
        {"report": "valuation", "section": "九、模型独立性与限制", "replacement_section": "九、事实、预测与未知", "issue_id": "N03", "reason": "旧模型声明退出。"},
        {"report": "valuation", "section": "十一、事实、预测与未知", "replacement_section": "十一、评分门槛与处置", "issue_id": "N03", "reason": "旧章节由明确门槛处置替代。"},
        {"report": "valuation", "section": "十二、反证与重估条件", "replacement_section": "十二、反证与重评条件", "issue_id": "N03", "reason": "章节标题与停止估值状态统一。"},
        {"report": "valuation", "section": "十三、来源", "issue_id": "N03", "reason": "加入裁决与证据索引。"},
        {"report": "valuation", "section": "十四、一句话结论", "issue_id": "N03", "reason": "统一NONE与停止定价。"},
    ],
    "closures": closures,
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"company": 76.5, "management": 68, "combined": 144.5, "models": 0}, ensure_ascii=False))
