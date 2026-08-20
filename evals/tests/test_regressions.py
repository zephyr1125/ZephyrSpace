"""M1-M8 永久 Regression Tests（plan §15 / §30）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import regression
from evals.tests.conftest import GOOD_DOC, make_doc

SANAN_GOLDEN = {
    "critical_facts": {
        "chairman": {"value": "林志强", "as_of": "2026-08-01", "severity": "P0"},
        "ceo": {"value": "林科闯", "as_of": "2026-04-07", "severity": "P0"},
    }
}

BUYBACK_GOLDEN = {
    "critical_facts": {
        "capital_actions": [
            {"type": "buyback", "year": 2025, "actual_amount_cny": 1830000000,
             "announced_upper_bound_cny": 2500000000},
        ]
    }
}

# ---------------------------------------------------------------- M1

def test_M1_current_management_identity_ok(tmp_path):
    ok, msg, errs = regression.grade_M1(make_doc(tmp_path, GOOD_DOC, "t.md"), SANAN_GOLDEN)
    # GOOD_DOC 中无林志强 → 应为 False（测试正确性）
    assert ok is False

def test_M1_wrong_chairman_fails(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC.replace("| 董事长 | 张三 |", "| 董事长 | 林秀成 |"), "t.md")
    ok, msg, errs = regression.grade_M1(d, SANAN_GOLDEN)
    assert ok is False
    assert any(e.severity == "P0" for e in errs)

def test_M1_correct_chairman_passes(tmp_path):
    text = GOOD_DOC.replace("| 董事长 | 张三 | 2000 | 30% | 创始人 |",
                            "| 董事长 | 林志强 | 2017 | 1% | 二代接班 |")
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M1(d, {"critical_facts": {"chairman": {"value": "林志强"}}})
    assert ok is True

# ---------------------------------------------------------------- M2

def test_M2_merged_penalties_fails(tmp_path):
    text = GOOD_DOC.replace(
        "| 2023 | 处罚 | 证监会 | 信息披露违规 | 50万元 | 已结 |",
        "| 2023 | 处罚 | 证监会/央行 | 信息披露违规；2021年反洗钱违规 | 50万元/200万元 | 已结 |"
    )
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M2(d, None)
    assert ok is False

def test_M2_separated_penalties_passes(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "t.md")
    ok, msg, errs = regression.grade_M2(d, None)
    assert ok is True

# ---------------------------------------------------------------- M3

def test_M3_action_labeled_done_fails(tmp_path):
    text = GOOD_DOC.replace(
        "| 2024 | \"将加大研发投入\" | 电话会 | ⏳ 执行中 | 2025研发费用增长 |",
        "| 2024 | \"将加大研发投入\" | 电话会 | ✅ 已兑现 | 2025研发费用增长 |"
    )
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M3(d, None)
    assert ok is False
    assert any(e.category == "ANALYSIS_ACTION_VS_OUTCOME" for e in errs)

def test_M3_ongoing_marker_passes(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "t.md")
    ok, msg, errs = regression.grade_M3(d, None)
    assert ok is True

# ---------------------------------------------------------------- M4

def test_M4_missing_instruments_fails(tmp_path):
    text = GOOD_DOC.replace("| 2024 | 回购 | 18.3亿 | 低估 | 完成 | 好 |",
                            "| 2024 | 回购 | 18.3亿 | 低估 | 完成 | 好 |")
    # 移除所有可转债/配股/H股等词
    for word in ["可转债", "配股", "H股", "优先股", "股权激励"]:
        text = text.replace(word, "XX")
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M4(d, None)
    assert ok is False

def test_M4_all_instruments_passes(tmp_path):
    # GOOD_DOC 已有 股权激励；补全其他工具词
    text = GOOD_DOC.replace("### 分红与股东回报", "### 融资工具核查\n\n- A股增发：有\n- 配股：无\n- 可转债：无\n- H股增发：无\n- 优先股：无\n- 股权激励：有\n\n### 分红与股东回报")
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M4(d, None)
    assert ok is True

# ---------------------------------------------------------------- M5

def test_M5_continuous_sell_with_buy_fails(tmp_path):
    text = GOOD_DOC.replace("2024年低位回购18.3亿元并注销，公告上限25亿，实际执行18.3亿。",
                            "2024年9月大股东底部增持500万股；2025年6-9月持续减持。")
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M5(d, None)
    assert ok is False

def test_M5_no_contradiction_passes(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "t.md")
    ok, msg, errs = regression.grade_M5(d, None)
    assert ok is True

# ---------------------------------------------------------------- M6

def test_M6_announced_instead_of_actual_fails(tmp_path):
    text = GOOD_DOC.replace("2024年低位回购18.3亿元并注销，公告上限25亿，实际执行18.3亿。",
                            "2024年回购计划上限25亿元。")
    text = text.replace("| 2024 | 回购 | 18.3亿 | 低估 | 完成 | 好 |",
                            "| 2024 | 回购 | 25亿（公告上限） | 低估 | 完成 | 好 |")
    text = text.replace("资本配置克制（2024年低位回购18.3亿元）",
                            "资本配置克制（2024年回购）")
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M6(d, BUYBACK_GOLDEN)
    assert ok is False

def test_M6_actual_amount_passes(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "t.md")
    ok, msg, errs = regression.grade_M6(d, BUYBACK_GOLDEN)
    assert ok is True

# ---------------------------------------------------------------- M7

def test_M7_truncated_quote_fails(tmp_path):
    text = GOOD_DOC.replace(
        "> \"在需求恢复的条件下，我们预计收入增长20%\" —— 2024 电话会",
        "> \"我们预计收入增长20%\" —— 2024 电话会"
    )
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M7(d, None)
    assert ok is False

def test_M7_conditional_quote_passes(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "t.md")
    ok, msg, errs = regression.grade_M7(d, None)
    assert ok is True

# ---------------------------------------------------------------- M8

def test_M8_insufficient_timeline_fails(tmp_path):
    text = GOOD_DOC.replace(
        "| 2024 | 王五 | CTO | 离任 | 个人原因 | 赵六 | 内部晋升 | 可控 |\n| 2025 | 孙七 | CFO | 离任 | 任期届满 | 周八 | 内部晋升 | 可控 |",
        "| 2024 | 王五 | CTO | 离任 | 个人原因 | 赵六 | 内部晋升 | 可控 |"
    )
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M8(d, None)
    assert ok is False

def test_M8_dense_turnover_not_flagged_fails(tmp_path):
    text = GOOD_DOC.replace(
        "| 2024 | 王五 | CTO | 离任 | 个人原因 | 赵六 | 内部晋升 | 可控 |\n| 2025 | 孙七 | CFO | 离任 | 任期届满 | 周八 | 内部晋升 | 可控 |",
        "| 2024 | 王五 | CTO | 离任 | 个人原因 | 赵六 | 内部晋升 | 可控 |\n| 2024 | 孙七 | CFO | 离任 | 个人原因 | 周八 | 外部空降 | 重大 |"
    )
    d = make_doc(tmp_path, text, "t.md")
    ok, msg, errs = regression.grade_M8(d, None)
    assert ok is False

def test_M8_good_timeline_passes(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "t.md")
    ok, msg, errs = regression.grade_M8(d, None)
    assert ok is True

# ---------------------------------------------------------------- combined

def test_combined_grade_runs(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = regression.grade(d, None)
    assert r.metrics["regression_total"] == 8
    assert r.score is not None