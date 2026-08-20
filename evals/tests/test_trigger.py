"""Trigger Eval 测试（Layer 1）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders.common import load_cases
from evals.graders.trigger import classify_trigger, extract_trigger_rules, grade_cases

SKILL_PATH = Path(__file__).resolve().parents[2] / "management-archive" / "SKILL.md"


def _rules():
    skill = SKILL_PATH.read_text(encoding="utf-8") if SKILL_PATH.exists() else ""
    return extract_trigger_rules(skill)


def test_extract_trigger_rules_from_skill():
    rules = _rules()
    assert "管理层档案" in rules["positive"]
    assert "老板档案" in rules["positive"]
    assert "管理层尽调" in rules["positive"]
    assert "管理层评估" in rules["positive"]


def test_positive_triggers():
    rules = _rules()
    positives = [
        "管理层档案 腾讯",
        "老板档案 美的集团",
        "看看宁德时代管理层靠不靠谱",
        "管理层尽调 比亚迪",
        "全面分析 中国中免",
        "给福耀玻璃建长期管理层档案",
        "管理层评估 三安光电",
        "拉取财报并全面分析 三安光电",
        "评估一下宁德时代的管理层质量",
        "美的集团的管理层怎么样",
        "宁德时代管理层的背景资料",
    ]
    for p in positives:
        assert classify_trigger(p, rules), f"应触发: {p}"


def test_negative_non_triggers():
    rules = _rules()
    negatives = [
        "腾讯现在 PE 多少？",
        "美的最近股价为什么跌？",
        "长江电力的自由现金流是多少？",
        "宁德时代当前估值是否便宜？",
        "帮我算一下比亚迪的市盈率",
        "招商银行的股息率是多少？",
        "今天上证指数涨了多少？",
        "福耀玻璃2025年营收是多少？",
        "帮我看看美的的K线走势",
        "茅台最近的技术面怎么样？",
    ]
    for p in negatives:
        assert not classify_trigger(p, rules), f"不应触发: {p}"


def test_dataset_accuracy_gate():
    """标注数据集必须达到 >= 0.95 accuracy（Hard Gate）。"""
    cases = load_cases()
    trigger_cases = [c for c in cases.values() if c.id.startswith("trigger_")]
    assert len(trigger_cases) >= 20, "触发数据集应 >= 20 条"
    skill = SKILL_PATH.read_text(encoding="utf-8") if SKILL_PATH.exists() else ""
    r = grade_cases(trigger_cases, skill)
    assert r.score is not None and r.score >= 0.95, f"accuracy {r.score}"
    assert r.gates.get("trigger_accuracy") is True
