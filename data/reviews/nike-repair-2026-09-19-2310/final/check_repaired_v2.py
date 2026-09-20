import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "data/reviews/nike-repair-2026-09-19-2310"


def load(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


wp = load(RUN / "final/workpaper-repaired-v2.json")
sr = load(RUN / "final/score-review-v2.json")
errors = []
if len(sr["items"]) != 32:
    errors.append("评分项不是32项")
for x in sr["items"]:
    if not x.get("definition") or not x.get("facts_and_reason") or not x.get("evidence_refs"):
        errors.append(f"{x['group']}/{x['id']}缺定义、理由或证据")
    if x.get("score") is None and x.get("rule_maximum") is None:
        errors.append(f"{x['group']}/{x['id']}既无已批准分也无规则数学上限")

company_known = sum(x["score"] for x in sr["items"] if x["group"] == "company" and x.get("score") is not None)
management_known = sum(x["score"] for x in sr["items"] if x["group"] == "management" and x.get("score") is not None)
if abs(company_known - 39.5) > 1e-9 or abs(management_known - 21) > 1e-9:
    errors.append(f"已固定分小计错误：{company_known}/{management_known}")
e2 = next(x for x in sr["items"] if x["group"] == "company" and x["id"] == "E2")
if e2.get("score") != 5:
    errors.append("E2未按裁决固定为5")
if sr.get("withdrawn_ranges", {}).get("combined") != [140.5, 144.5]:
    errors.append("未明确记录撤回的144.5区间")

for key in ("target_price", "certainty", "buy_price"):
    if wp["valuation"].get(key) is not None:
        errors.append(f"{key}必须为null")
if wp["valuation"].get("models"):
    errors.append("正式模型数组必须为空")
if wp.get("historical_issue_ids") != [f"G{i:02d}" for i in range(1, 14)]:
    errors.append("原G01-G13问题ID未完整保留")

required = {
    "deep.md": ["FY2024–FY2026分部经营", "三年杜邦复核", "会计估计与准备", "20亿美元节约机会", "比利时海关进口争议", "Philip Knight 221"],
    "management.md": ["FY2023–FY2026人效", "2023-12-21", "ROIC为18.7%/20.2%", "比利时海关进口争议"],
    "valuation.md": ["代言承诺1.7", "产品采购承诺4.7", "其他采购承诺1.6", "流动债务2,000", "比利时海关进口争议"],
}
for name, needles in required.items():
    text = (RUN / "drafts/repaired-v2" / name).read_text(encoding="utf-8-sig")
    minimum = 100 if name == "valuation.md" else 150
    if len(text.splitlines()) < minimum:
        errors.append(f"{name}行数不足")
    for needle in needles:
        if needle not in text:
            errors.append(f"{name}缺恢复项：{needle}")

result = {
    "status": "pass" if not errors else "fail",
    "errors": errors,
    "known_point_subtotals": {"company": company_known, "management": management_known},
    "limitations": ["不验证事实真实性", "不批准争议评分", "不等同独立复查"],
}
(RUN / "final/selfcheck-repaired-v2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
