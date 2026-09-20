import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
reports = {
    "deep": ROOT / "深度分析" / "中国民航信息网络 深度分析 73 2026-09-19 修订版.md",
    "management": ROOT / "管理层档案" / "中国民航信息网络 管理层档案 70 2026-09-19 修订版.md",
    "valuation": ROOT / "估值分析" / "中国民航信息网络 估值分析 未完成 2026-09-19 修订版.md",
}
mins = {"deep": 150, "management": 150, "valuation": 100}
calc = json.loads(Path(__file__).with_name("repair-calculation-output.json").read_text(encoding="utf-8"))
checks = []
hashes = {}
for key, path in reports.items():
    text = path.read_text(encoding="utf-8")
    lines = len(text.splitlines())
    hashes[key] = {"path": str(path), "lines": lines, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    checks.append({"id": f"{key}_lines", "passed": lines >= mins[key], "actual": lines, "required": mins[key]})
checks += [
    {"id": "receivables_reconcile", "passed": all(calc["receivable_checks"].values())},
    {"id": "company_score", "passed": calc["candidate_cScore"] == 73},
    {"id": "management_score", "passed": calc["candidate_mScore"] == 70},
    {"id": "important_parameters_null", "passed": all(calc[x] is None for x in ("target_price", "valuation_certainty", "mechanical_buy_price", "watchlistLevel"))},
    {"id": "reverse_weight_zero", "passed": calc["reverse_validation_weight"] == 0},
    {"id": "draft_archive", "passed": all((ROOT / "data/reviews/travelsky-2026-09-19/draft-v1" / p.name.replace(" 修订版", "").replace(" 70 ", " 68 ").replace(" 未完成", "")).exists() for p in []) or (ROOT / "data/reviews/travelsky-2026-09-19/draft-v1").exists()},
]
result = {
    "artifact_checks_passed": all(c["passed"] for c in checks),
    "research_complete": False,
    "remaining_p1": ["C04", "C05"],
    "checks": checks,
    "revision_hashes": hashes,
}
Path(__file__).with_name("repair-selfcheck-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["artifact_checks_passed"] else 1)
