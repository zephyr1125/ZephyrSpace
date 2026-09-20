import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from scripts.triplet_workpaper import report_sections


BASE = Path(__file__).resolve().parent
wp = json.loads((BASE / "workpaper-repaired-v2.json").read_text(encoding="utf-8"))
deep = (BASE / "deep.md").read_text(encoding="utf-8")
management = (BASE / "management.md").read_text(encoding="utf-8")
valuation = (BASE / "valuation.md").read_text(encoding="utf-8")
errors = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


company_sum = sum(row["score"] for row in wp["scores"]["company"]["items"])
management_sum = sum(row["score"] for row in wp["scores"]["management"]["items"])
require(abs(company_sum - 76.5) < 1e-9 and wp["scores"]["company"]["total"] == 76.5, "公司评分不闭合")
require(abs(management_sum - 68) < 1e-9 and wp["scores"]["management"]["total"] == 68, "管理层评分不闭合")
e4 = next(row for row in wp["scores"]["company"]["items"] if row["id"] == "E4")
require(e4["score"] == 1.5 and "2分档" in e4["reason"] and "扣0.5" in e4["reason"], "E4评分桥不完整")
valuation_wp = wp["valuation"]
require(valuation_wp["models"] == [], "有效估值模型未清空")
require(all(valuation_wp[key] is None for key in ("target_price", "certainty", "buy_price")), "价格字段未全部null")
require(all(value is None for value in valuation_wp["weighted"].values()), "加权价格情景未全部null")
require(valuation_wp["reverse"]["weight"] == 0, "反向条件表权重不为0")

for name, text, minimum in (("deep", deep, 150), ("management", management, 150), ("valuation", valuation, 100)):
    require(len(text.splitlines()) >= minimum, f"{name}行数不足")
    require("<!-- triplet:cScore -->76.500000<!-- /triplet:cScore -->" in text, f"{name}公司分快照错误")
    require("<!-- triplet:mScore -->68.000000<!-- /triplet:mScore -->" in text, f"{name}管理层分快照错误")
    require("正式目标价 | null" in text or "合理价值: null" in text, f"{name}缺价格null状态")

for forbidden in ("33.905817", "25.666703", "21.480000", "49.383939", "<!-- triplet:certainty -->0.550000"):
    require(forbidden not in deep + management + valuation, f"有效报告残留撤回价格：{forbidden}")

require("D2点值撤回为null" not in deep + management, "残留D2旧null状态")
require("资本配置能力12分未获批准" not in management, "残留资本配置12未批准状态")
require("建议`defer" not in deep + management + valuation, "残留defer结论")
require("约一半达标" not in deep + management + valuation, "残留D2伪达成率")

for token in ("986", "965", "302", "684", "绝大部分"):
    require(token in deep and token in management and token in valuation, f"三报告退款桥缺字段：{token}")
for token in ("715", "1,481.0", "1.2百万股", "81.8"):
    require(token in valuation, f"SBC边界缺字段：{token}")
for token in ("15.5", "1.7", "4.9", "4.7", "2.4", "1.6", "1.1", "2031", "254"):
    require(token in valuation, f"承诺或税惠边界缺字段：{token}")

adjudicated = json.loads((BASE.parent / "adjudication-v1.json").read_text(encoding="utf-8"))
expected = {a["id"] for issue in adjudicated["issues"] for a in issue.get("acceptance", [])}
actual = {check["id"] for closure in wp["repair"]["closures"] for check in closure["checks"]}
require(expected == actual, "验收ID未完整覆盖")
require(all(check["passed"] and check["evidence"] for closure in wp["repair"]["closures"] for check in closure["checks"]), "关闭表缺证据")

# 按上一冻结底稿执行修复差异核对；估值停止路径由本脚本替代通用双模型检查。
previous = json.loads((BASE.parent / "workpaper-v1.json").read_text(encoding="utf-8-sig"))
declared_scores = {row["key"] for row in wp["repair"]["score_changes"]}
actual_scores = set()
for group in ("company", "management"):
    old_rows = {row["id"]: row for row in previous["scores"][group]["items"]}
    new_rows = {row["id"]: row for row in wp["scores"][group]["items"]}
    require(old_rows.keys() == new_rows.keys(), f"{group}评分项发生增删")
    actual_scores |= {f"{group}/{key}" for key in old_rows if old_rows[key] != new_rows[key]}
require(declared_scores == actual_scores, "评分差异与repair声明不一致")

declared_sections = {(row["report"], row["section"]): row for row in wp["repair"]["report_changes"]}
actual_sections = set()
for report in ("deep", "management", "valuation"):
    old_sections = report_sections((ROOT := BASE.parents[4] / previous["reports"][report]).read_text(encoding="utf-8-sig"))
    new_sections = report_sections((BASE / f"{report}.md").read_text(encoding="utf-8"))
    for section in old_sections.keys() | new_sections.keys():
        if old_sections.get(section) != new_sections.get(section):
            actual_sections.add((report, section))
require(set(declared_sections) == actual_sections, "正文差异与repair声明不一致")

result = {
    "status": "mechanical_checks_passed" if not errors else "failed",
    "errors": errors,
    "scope": {
        "scores": True,
        "valuation_stop": True,
        "withdrawn_price_scan": True,
        "acceptance_ids": sorted(expected),
        "report_lines": {"deep": len(deep.splitlines()), "management": len(management.splitlines()), "valuation": len(valuation.splitlines())},
    },
    "limitations": "复杂停止估值路径适配检查；不验证原件真实性、分析判断合理性或替代双路定向验收。",
}
(BASE / "selfcheck-repaired-v2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(1 if errors else 0)
