
"""Analytical Quality Judge（Eval Layer 6）。

6 个分析质量维度（1-5 分）：
counter_evidence / action_vs_outcome / capital_allocation / strategic_consistency /
crisis_handling / uncertainty

LLM 模式下由独立 Judge（不同 prompt、不读取生产评分）逐维打分；
Null 模式下用确定性启发式。得分 = 各维度均分 / 满分。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import CONFIG, ArchiveDocument, EvalCase, EvalError, GraderResult
from .judge import JUDGE_RUBRICS, get_backend

DIMENSIONS = list(JUDGE_RUBRICS.keys())


def grade(doc: ArchiveDocument, case: Optional[EvalCase] = None) -> GraderResult:
    r = GraderResult(name="analysis")
    backend = get_backend()
    r.details["judge_backend"] = backend.name

    scores: Dict[str, int] = {}
    disagreements: List[Dict[str, Any]] = []
    for dim in DIMENSIONS:
        res = backend.judge(dim, doc.text)
        scores[dim] = res.score
        # 关键 judge case 重复运行（config），记录分歧
        repeat = int(CONFIG["judge"].get("repeat_runs", 1))
        if repeat > 1 and backend.name == "llm":
            vals = [res.score]
            for _ in range(repeat - 1):
                vals.append(backend.judge(dim, doc.text).score)
            spread = max(vals) - min(vals)
            if spread > 1:
                disagreements.append({"dimension": dim, "scores": vals})
        r.details[dim] = res.to_dict()

    total_score = sum(scores.values())
    max_score = sum(JUDGE_RUBRICS[d]["max_score"] for d in DIMENSIONS)
    r.score = round(total_score / max_score, 4)
    r.metrics["analysis_judges"] = len(DIMENSIONS)
    r.metrics["analysis_total"] = total_score
    r.metrics["analysis_max"] = max_score
    r.metrics["judge_disagreements"] = len(disagreements)
    r.details["dimension_scores"] = scores

    double_thr = CONFIG["judge"].get("double_judge_threshold", 0.4)
    if disagreements:
        r.metrics["manual_review"] = True
        r.details["manual_review_reason"] = f"{len(disagreements)} 个维度 judge 分歧大于阈值"

    # 低分维度附 P2 提示（不阻塞）
    for dim, s in scores.items():
        mx = JUDGE_RUBRICS[dim]["max_score"]
        if s <= 2:
            cid = case.id if case else "?"
            r.add_error("P2", "ANALYSIS_" + dim.upper(),
                        f"[{cid}] {dim} 分析质量 {s}/{mx} 偏低：{r.details[dim]['reason']}")
    return r