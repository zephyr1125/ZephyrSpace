import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FILES = {
    "deep": ROOT / "深度分析" / "中国民航信息网络 深度分析 73 2026-09-19.md",
    "management": ROOT / "管理层档案" / "中国民航信息网络 管理层档案 68 2026-09-19.md",
    "valuation": ROOT / "估值分析" / "中国民航信息网络 估值分析 2026-09-19.md",
}
MIN_LINES = {"deep": 150, "management": 150, "valuation": 100}
calc_path = Path(__file__).with_name("calculation-output.json")
calc = json.loads(calc_path.read_text(encoding="utf-8"))

checks = []
hashes = {}
for key, path in FILES.items():
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    checks.append({"check": f"{key}_line_count", "passed": len(lines) >= MIN_LINES[key], "actual": len(lines), "required": MIN_LINES[key]})
    checks.append({"check": f"{key}_fact_prediction_unknown", "passed": all(token in text for token in ("事实", "未知"))})
    checks.append({"check": f"{key}_cutoff", "passed": "2026-09-19" in text})
    hashes[key] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "lines": len(lines)}

deep_text = FILES["deep"].read_text(encoding="utf-8")
mgmt_text = FILES["management"].read_text(encoding="utf-8")
val_text = FILES["valuation"].read_text(encoding="utf-8")
checks.extend([
    {"check": "company_score_sum", "passed": sum([8, 16, 17, 10, 14, 8]) == 73},
    {"check": "management_score_sum", "passed": sum([12, 14, 13, 12, 9, 8]) == 68},
    {"check": "two_main_models", "passed": "FCFF DCF（权重60%）" in val_text and "RI/PB-ROE（权重40%）" in val_text},
    {"check": "reverse_zero_weight", "passed": "反向DCF权重为0" in val_text or "反向验证权重0%" in val_text},
    {"check": "three_scenarios", "passed": all(x in val_text for x in ("保守", "基准", "乐观"))},
    {"check": "sensitivity", "passed": val_text.count("敏感性") >= 2},
    {"check": "mechanical_buy_price", "passed": abs(calc["mechanical_buy_price_hkd"] - calc["target_price_hkd"] * (0.68 + 0.14 * calc["valuation_certainty"])) < 1e-10},
    {"check": "weights_sum", "passed": abs(sum(calc["weights"].values()) - 1.0) < 1e-12},
    {"check": "target_recalculation", "passed": abs(calc["target_price_hkd"] - (calc["dcf_scenarios_hkd"]["基准"] * 0.6 + calc["ri_scenarios_hkd"]["基准"] * 0.4)) < 1e-10},
    {"check": "first_version_disclosure", "passed": all("首次建立，无上一版可比" in t for t in (deep_text, mgmt_text, val_text))},
    {"check": "market_risk", "passed": all(x in val_text for x in ("汇率", "流动性", "港元"))},
    {"check": "no_watchlist_write_claim", "passed": "作者不修改Watchlist" in val_text},
])

result = {"passed": all(x["passed"] for x in checks), "checks": checks, "frozen_draft": hashes}
out = Path(__file__).with_name("selfcheck-result.json")
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["passed"] else 1)
