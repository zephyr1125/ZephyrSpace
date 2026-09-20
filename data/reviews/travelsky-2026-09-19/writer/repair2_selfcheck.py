import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
files = {
    "deep": root / "深度分析/中国民航信息网络 深度分析 未完成 2026-09-19 最终修订.md",
    "management": root / "管理层档案/中国民航信息网络 管理层档案 未完成 2026-09-19 最终修订.md",
    "valuation": root / "估值分析/中国民航信息网络 估值分析 未完成 2026-09-19 最终修订.md",
}
minimums = {"deep": 150, "management": 150, "valuation": 100}
forbidden_current = ["候选有效", "公司质量评分为 **73", "保守净现金约64.28", "标准化FCFF约21.37"]
checks = []
hashes = {}
for name, path in files.items():
    text = path.read_text(encoding="utf-8")
    lines = len(text.splitlines())
    checks.append({"id": f"{name}_lines", "passed": lines >= minimums[name], "actual": lines, "required": minimums[name]})
    checks.append({"id": f"{name}_status", "passed": "研究未完成" in text})
    checks.append({"id": f"{name}_no_forbidden_current", "passed": not any(x in text for x in forbidden_current)})
    hashes[name] = {"path": str(path), "lines": lines, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

calc = json.loads((Path(__file__).parent / "repair2-calculation-output.json").read_text(encoding="utf-8"))
checks.extend([
    {"id": "formal_parameters_null", "passed": all(v is None for v in calc["formal_parameters"].values())},
    {"id": "reverse_weight_zero", "passed": calc["reverse_validation_weight"] == 0},
    {"id": "remaining_p1", "passed": calc["remaining_p1_author_view"] == ["C04", "C05"]},
    {"id": "dupont_identity", "passed": all(abs(x["roe_identity"] - x["roe_direct"]) < 1e-12 for x in calc["dupont"].values())},
    {"id": "candidate_company_arithmetic", "passed": abs(sum(calc["dimension_totals"].values()) - 71.5) < 1e-12},
    {"id": "candidate_management_arithmetic", "passed": calc["candidate_management_score"] == 70},
    {"id": "repair_v1_snapshot", "passed": len(list((Path(__file__).parents[1] / "repair-v1-snapshot").glob("*.md"))) == 3},
])
result = {
    "artifact_checks_passed": all(x["passed"] for x in checks),
    "research_complete": False,
    "repair_round": 2,
    "exception_round": 1,
    "remaining_p1": ["C04", "C05"],
    "checks": checks,
    "hashes": hashes,
}
(Path(__file__).parent / "repair2-selfcheck-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
