"""统计口径修复测试：
- judge_total 必须 = grounding claims + analytical 维度（26 次），且写回 case metrics
- regressions.md 必须反映 regression 层状态（不是 case 整体 status）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import evals.runners.run_eval as re_mod
from evals.graders.common import CONFIG, GraderResult, load_cases
from evals.graders import analytical_quality as aq
from evals.graders import grounding as gr
from evals.runners.run_skill import ReplayRunner


def test_judge_total_merges_all_layers(monkeypatch):
    """grounding(20) + analytical(6) = 26 次 judge，且 error 求和、写回 metrics。"""

    def fake_analysis(doc, case=None):
        r = GraderResult(name="analysis")
        r.score = 1.0
        r.metrics["judge_total"] = 6
        r.metrics["judge_error_count"] = 0
        r.gates["grounded_claim_rate"] = True
        return r

    def fake_grounding(doc, case=None):
        r = GraderResult(name="grounding")
        r.score = 1.0
        r.metrics["judge_total"] = 20
        r.metrics["judge_error_count"] = 1
        r.gates["grounded_claim_rate"] = True
        return r

    monkeypatch.setattr(aq, "grade", fake_analysis)
    monkeypatch.setattr(gr, "grade", fake_grounding)
    monkeypatch.setitem(CONFIG["judge"], "backend", "llm")
    try:
        case = load_cases()["management_archive_001"]
        runner = ReplayRunner()
        skill = Path(__file__).resolve().parents[2] / "management-archive" / "SKILL.md"
        r, _ = re_mod._run_single(case, "skill", "v", runner, skill, {}, 1.0)
        assert r["metrics"]["judge_total"] == 26, "judge_total 应为 20+6=26"
        assert r["metrics"]["judge_error_count"] == 1
        assert r["metrics"]["judge_success_rate"] == pytest.approx(round(25 / 26, 4))
        assert r["status"] == "INCOMPLETE"  # llm 模式 + 1 个 judge 失败
    finally:
        pass


def test_regressions_md_uses_regression_layer_status():
    results = [
        {"case_id": "a", "status": "PASS",
         "gates": {"regression_stability": False},
         "metrics": {"regression_pass": 6, "regression_total": 8},
         "errors": [{"severity": "P1", "category": "FACT_CAPITAL_ACTION", "message": "[M4] ..."}]},
        {"case_id": "b", "status": "PASS",
         "gates": {"regression_stability": True},
         "metrics": {"regression_pass": 8, "regression_total": 8},
         "errors": []},
    ]
    md = re_mod._regressions_md(results)
    assert "a: FAIL (M-pass 6/8)" in md, md
    assert "b: PASS (M-pass 8/8)" in md, md
    assert "a: PASS" not in md  # 不再沿用 case 整体 PASS
