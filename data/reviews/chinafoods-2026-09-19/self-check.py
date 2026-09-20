import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "data/reviews/chinafoods-2026-09-19"
reports = {
    "deep": ROOT / "深度分析/中国食品 深度分析 69 2026-09-19.md",
    "management": ROOT / "管理层档案/中国食品 管理层档案 70 2026-09-19.md",
    "valuation": ROOT / "估值分析/中国食品 估值分析 2026-09-19.md",
}
minimum = {"deep": 150, "management": 150, "valuation": 100}
required = {
    "deep": ["## A ", "## B ", "## C ", "## D ", "## E ", "## F ", "## 综合风险地图", "## 反证条件", "## 最终结论"],
    "management": ["## 一、", "## 二、", "## 三、", "## 四、", "## 五、", "## 六、", "## 七、", "## 八、", "## 九、", "## 十、", "## 十一、"],
    "valuation": ["## 主模型一", "## 主模型二", "## 综合三情景", "## 反向验证", "## PE敏感性", "## DDM支付时点敏感性", "## 机械买入价"]
}
calc = json.loads((RUN / "calculation-results.json").read_text(encoding="utf-8"))
result = {"reports": {}, "cross_report": {}}
for key, path in reports.items():
    text = path.read_text(encoding="utf-8")
    lines = len(text.splitlines())
    missing = [x for x in required[key] if x not in text]
    result["reports"][key] = {
        "path": str(path),
        "lines": lines,
        "minimum": minimum[key],
        "line_pass": lines >= minimum[key],
        "missing_sections": missing,
        "section_pass": not missing,
        "reviewing_mark_present": "审核中" in text,
    }

deep_text = reports["deep"].read_text(encoding="utf-8")
management_text = reports["management"].read_text(encoding="utf-8")
valuation_text = reports["valuation"].read_text(encoding="utf-8")
result["cross_report"] = {
    "cscore_69": calc["cscore"] == 69 and "69/100" in deep_text,
    "mscore_70": calc["mscore"] == 70 and "70/100" in management_text,
    "target_2_72": abs(calc["target_price_hkd"] - 2.720600357723633) < 1e-12 and "HKD2.72" in valuation_text,
    "certainty_0_60": calc["valuation_certainty"] == 0.60 and "0.60" in valuation_text,
    "buy_2_08": abs(calc["mechanical_buy_price_hkd"] - 2.0785386733008555) < 1e-12 and "HKD2.08" in valuation_text,
    "fx_present": "0.86062" in valuation_text and "1.161953" in valuation_text,
    "shares_present": "2,797,223,396" in valuation_text,
    "cashflow_scope_warning": all("非归母" in t or "不能直接归母" in t or "不能称为“归母FCF”" in t for t in [deep_text, valuation_text]),
    "three_scenarios": all(x in valuation_text for x in ["保守", "基准", "乐观"]),
    "weights_50_50": "50%/50%" in valuation_text,
    "none_level": "NONE" in deep_text and "NONE" in valuation_text,
    "zero_weight_reverse": "权重为0" in valuation_text,
}
expected_grid = {
    "0.01": {"0.1": 2.0081130141, "0.11": 1.8073017127, "0.12": 1.6430015570},
    "0.025": {"0.1": 2.4455237697, "0.11": 2.1578150909, "0.12": 1.9306766603},
    "0.04": {"0.1": 3.1016399030, "0.11": 2.6585484883, "0.12": 2.3262299273},
}
grid = calc.get("ddm_ke_g_sensitivity_hkd", {})
result["cross_report"]["ddm_grid_3x3"] = all(abs(grid[g][ke] - value) <= 1e-9 for g, row in expected_grid.items() for ke, value in row.items())
result["cross_report"]["ddm_grid_in_report"] = "## DDM敏感性：Ke×g" in valuation_text and "2.157815" in valuation_text and "3.101640" in valuation_text
result["cross_report"]["management_threshold_16"] = management_text.count("资本配置16>10") == 2 and "资本配置18>10" not in management_text
result["pass"] = all(v["line_pass"] and v["section_pass"] and v["reviewing_mark_present"] for v in result["reports"].values()) and all(result["cross_report"].values())
(RUN / "self-check-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
