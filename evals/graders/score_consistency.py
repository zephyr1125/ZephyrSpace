
"""Score Calibration Eval（Eval Layer 7）。

- Internal Score Consistency：速览卡分 == 明细表总分 == 文件名分；评级与总分一致；结论类型与分数一致
- Pairwise Calibration：相对排序（A 优于 B => score(A) > score(B)）
- Score Drift：与 baseline 对比，超阈值要求解释
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import (
    CONFIG, ArchiveDocument, EvalCase, EvalError, GraderResult, rating_for_score,
)


def _conclusion_type_check(doc: ArchiveDocument) -> Optional[EvalError]:
    """结论类型定位（托付重仓/中性/跟踪/减分项）与总分一致性。

    只匹配「已勾选」的 checkbox（- [x]）或正文直接表述，忽略模板中未勾选项。
    """
    total = doc.total_score
    if total is None:
        return None
    text = re.sub(r"-\s*\[\s*\]\s*[^\n]*", "", doc.text)  # 移除未勾选 checkbox 行
    loc = "可以托付重仓" in text
    neg = "管理层本身就是减分项" in text
    track = "需要持续跟踪" in text
    if total >= 70 and neg:
        return EvalError("P1", "SCORE_INCONSISTENCY",
                         f"总分 {total}（>=70）但结论定位为'减分项'，自相矛盾")
    if total < 40 and loc:
        return EvalError("P1", "SCORE_INCONSISTENCY",
                         f"总分 {total}（<40）但结论定位为'托付重仓'，自相矛盾")
    if total >= 85 and track and not neg:
        # 85+ 且标为需要持续跟踪 → 弱警告（P2）
        return EvalError("P2", "SCORE_INCONSISTENCY",
                         f"总分 {total}（>=85）但结论定位为'需要持续跟踪'，建议复核")
    return None


def grade(doc: ArchiveDocument, case: EvalCase,
          baseline_scores: Optional[Dict[str, float]] = None) -> GraderResult:
    r = GraderResult(name="calibration")
    total = doc.total_score
    ok_checks: List[Tuple[str, bool, str]] = []

    # 1) 文件名分 == 明细总分
    fn_score = doc.filename_score
    if fn_score is not None and total is not None:
        ok = fn_score == total
        ok_checks.append(("filename_vs_total", ok, f"文件名 {fn_score} vs 总分 {total}"))
    # 2) 速览卡分 == 明细总分
    card = doc.card_score
    if card is not None and total is not None:
        ok = card == total
        ok_checks.append(("card_vs_total", ok, f"速览卡 {card} vs 总分 {total}"))
    # 3) 评级与总分
    if total is not None:
        expected = rating_for_score(total)
        declared = doc.declared_rating
        ok = declared == expected if declared else False
        ok_checks.append(("rating_mapping", ok, f"评级 {declared or '缺失'} vs 应 {expected}"))
    # 4) 结论类型
    concl_err = _conclusion_type_check(doc)
    if concl_err:
        r.errors.append(concl_err)
    ok_checks.append(("conclusion_type", concl_err is None, concl_err.message if concl_err else "ok"))

    passed = sum(1 for _, ok, _ in ok_checks if ok)
    total_checks = len(ok_checks)
    r.score = round(passed / total_checks, 4) if total_checks else None
    r.details["checks"] = {name: {"ok": ok, "detail": d} for name, ok, d in ok_checks}
    for name, ok, d in ok_checks:
        if not ok:
            sev = "P1" if name in ("card_vs_total", "filename_vs_total") else "P2"
            r.add_error(sev, "SCORE_INCONSISTENCY", f"[calibration.{name}] {d}")

    # 5) Score Drift
    cid = case.id if case else ""
    if baseline_scores and cid in baseline_scores:
        base = baseline_scores[cid]
        if total is not None:
            drift = abs(total - base)
            threshold = CONFIG["calibration"]["score_drift_threshold"]
            if drift > threshold:
                r.add_error("P2", "SCORE_DRIFT",
                            f"总分 {total} 与 baseline {base} 偏差 {drift} > {threshold}，"
                            f"需要 Score Drift Explanation（事实更新/新证据/Skill 改进/评分漂移）")
                r.metrics["drift_explanation_required"] = True
            r.metrics["drift_vs_baseline"] = round(drift, 1)
    return r


def pairwise_compare(total_scores: Dict[str, float],
                     pairs: List[Tuple[str, str]]) -> Tuple[int, int, List[str]]:
    """相对排序校验。pairs: [(case_a, case_b)] 表示 A 应优于 B。"""
    ok = 0
    fails: List[str] = []
    for a, b in pairs:
        sa, sb = total_scores.get(a), total_scores.get(b)
        if sa is None or sb is None:
            continue
        if sa > sb:
            ok += 1
        else:
            fails.append(f"{a} ({sa}) 应优于 {b} ({sb})")
    return ok, len(pairs), fails