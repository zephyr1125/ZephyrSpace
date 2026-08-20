"""Score Calibration Eval 测试（Layer 7）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import score_consistency
from evals.tests.conftest import GOOD_DOC, make_doc


def test_good_doc_consistent(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = score_consistency.grade(d, None)
    assert r.score == 1.0, r.errors


def test_card_vs_total_mismatch(tmp_path):
    text = GOOD_DOC.replace("| **管理层评分** | **80 / 100** |", "| **管理层评分** | **81 / 100** |")
    d = make_doc(tmp_path, text, "测试公司 管理层档案 80 2026-07-01.md")
    r = score_consistency.grade(d, None)
    assert any("card_vs_total" in e.message for e in r.errors)
    assert r.score < 1.0


def test_filename_vs_total_mismatch(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 79 2026-07-01.md")
    r = score_consistency.grade(d, None)
    assert any("filename_vs_total" in e.message for e in r.errors)


def test_rating_mapping_mismatch(tmp_path):
    text = GOOD_DOC.replace("| **评级** | ⭐⭐⭐⭐ 优秀 |", "| **评级** | ⭐⭐⭐⭐⭐ 卓越 |")
    d = make_doc(tmp_path, text, "测试公司 管理层档案 80 2026-07-01.md")
    r = score_consistency.grade(d, None)
    assert any("rating_mapping" in e.message for e in r.errors)


def test_score_drift_detected(tmp_path):
    from evals.graders.common import case_from_dict
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    c = case_from_dict({"id": "management_archive_test",
                        "company": {"name": "测试公司", "ticker": "600001.SH", "market": "A"},
                        "prompt": "管理层档案 测试公司"})
    baseline = {"management_archive_test": 70}
    r = score_consistency.grade(d, c, baseline_scores=baseline)
    assert r.metrics.get("drift_explanation_required") is True


def test_pairwise_compare():
    ok, total, fails = score_consistency.pairwise_compare(
        {"A": 90, "B": 75}, [("A", "B")])
    assert ok == 1 and total == 1 and fails == []
    ok2, _, fails2 = score_consistency.pairwise_compare(
        {"A": 70, "B": 80}, [("A", "B")])
    assert ok2 == 0 and len(fails2) == 1