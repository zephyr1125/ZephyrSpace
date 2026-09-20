import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "data/reviews/nike-repair-2026-09-19-2310"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def visible(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


wp = load(RUN / "final/workpaper-repaired-v1.json")
score_review = load(RUN / "final/score-review-v1.json")
errors = []

items = score_review["items"]
if len(items) != 32:
    errors.append(f"评分项应为32，实际{len(items)}")
for item in items:
    if not item.get("definition") or not item.get("facts_and_reason") or not item.get("evidence_refs"):
        errors.append(f"{item['group']}/{item['id']}缺定义、事实理由或证据")
    lo, hi = item["score_range"]
    if lo > hi:
        errors.append(f"{item['group']}/{item['id']}区间倒置")

for group, expected in (("company", [72.5, 74.5]), ("management", [68, 70])):
    group_items = [x for x in items if x["group"] == group]
    actual = [sum(x["score_range"][k] for x in group_items) for k in (0, 1)]
    if any(abs(a - b) > 1e-9 for a, b in zip(actual, expected)):
        errors.append(f"{group}区间加总{actual}不等于{expected}")

valuation = wp["valuation"]
for key in ("target_price", "certainty", "buy_price"):
    if valuation.get(key) is not None:
        errors.append(f"正式{key}必须为null")
if valuation.get("models"):
    errors.append("正式主模型数组必须为空，避免继续使用已撤回模型")

expected_ids = {"G02", "G03", "G05", "G07", "G08", "G09A", "G09B", "G13"}
issue_ids = {x["id"] for x in wp["repair"]["issues"]}
closure_ids = {x["id"] for x in wp["repair"]["closures"]}
if issue_ids != expected_ids or closure_ids != expected_ids:
    errors.append(f"问题或关闭ID不完整：issues={issue_ids}, closures={closure_ids}")
for closure in wp["repair"]["closures"]:
    expected = next(x for x in wp["repair"]["issues"] if x["id"] == closure["id"])["acceptance_ids"]
    actual = [x["id"] for x in closure["checks"]]
    if actual != expected or not all(x["passed"] and x["evidence"] for x in closure["checks"]):
        errors.append(f"{closure['id']}验收条件或作者声明不完整")

for name, minimum in (("deep", 150), ("management", 150), ("valuation", 100)):
    path = RUN / f"drafts/repaired-v1/{name}.md"
    text = path.read_text(encoding="utf-8-sig")
    lines = len(text.splitlines())
    if lines < minimum:
        errors.append(f"{name}仅{lines}行，低于{minimum}")
    shown = visible(text)
    if name == "valuation":
        for stale in ("42.915639", "34.213160", "32.487138"):
            if stale in shown and "撤回" not in shown[max(0, shown.index(stale)-80):shown.index(stale)+80]:
                errors.append(f"估值可见正文仍把旧数{stale}作为有效值")

result = {
    "status": "pass" if not errors else "fail",
    "errors": errors,
    "coverage": {
        "score_items": 32,
        "score_range_sums": True,
        "formal_price_null": True,
        "repair_ids": sorted(expected_ids),
        "line_count": True,
        "active_stale_price_scan": True,
        "fact_or_model_correctness": False,
        "independent_review": False,
    },
}
(RUN / "final/selfcheck-repaired-v1.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
