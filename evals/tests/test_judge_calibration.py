"""Judge v2 calibration 测试。

- 六维 rubric 结构：五档锚点（1-5）+ ceiling rules 必须齐全
- judge-v1 保留可追溯（JUDGE_RUBRICS_V1）
- v2 prompt 必须包含反 inflation 强制条款
- 人工样例 A-F（结构定义 + 预期档位 + 假 judge 传导）
- 真实 LLM 校准（默认跳过；设 RUN_LLM_CALIB=1 时跑）
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders.judge import (
    JUDGE_PROMPT_VERSION, JUDGE_RUBRICS, JUDGE_RUBRICS_V1, LLMJudgeBackend, JudgeResult,
)

DIMS = list(JUDGE_RUBRICS.keys())

# ---------------------------------------------------------------- 人工样例 A-F

CALIBRATION_CASES = [
    {
        "id": "A_excellent",
        "dim": "counter_evidence",
        "expected": (4, 5),
        "note": "明显优秀：主动寻找多个反例且反证实质影响结论",
        "doc": ("管理层承诺'不做跨界并购'。报告主动列出 2018 年曾投资 5 亿元于光伏（后减值退出）作为反例，"
                "并据此把结论修正为'大体克制但非绝对'；另引行业两起跨界失败案例，说明结论限定的依据。"),
    },
    {
        "id": "B_adequate",
        "dim": "capital_allocation",
        "expected": (3, 3),
        "note": "普通合格：主要资本动作覆盖，个别动作只记录不分析",
        "doc": ("报告列出 2021 年定增 30 亿、2023 年分红 60 亿、2024 年回购 10 亿，给出规模与年份；"
                "定增资金用途仅写'补充流动资金'，未分析机会成本或回报；分红与回购的周期位置未讨论。"),
    },
    {
        "id": "C_missing",
        "dim": "crisis_handling",
        "expected": (1, 3),
        "note": "有明显遗漏：存在重大危机但报告未识别",
        "doc": ("报告详细描述了 2020 年产品召回事件的处理流程（及时、担责、赔偿），评价为正面；"
                "但 2023 年公司因财务造假被证监会立案、CFO 被带走这一重大危机，报告中完全未提及。"),
    },
    {
        "id": "D_action_as_outcome",
        "dim": "action_vs_outcome",
        "expected": (1, 2),
        "note": "动作当兑现：'加大研发投入'被标为已兑现",
        "doc": ("言行表：2024 年管理层'将加大研发投入'，2025 年研发费用增长 30%，报告标注'✅ 已兑现'；"
                "另有 2023 年'拓展海外市场'，2024 年设立 3 家海外子公司即标'✅ 已兑现'，均无收入/份额结果指标。"),
    },
    {
        "id": "E_capital_missing",
        "dim": "capital_allocation",
        "expected": (1, 3),
        "note": "重大资本动作遗漏：未提可转债/H股增发",
        "doc": ("资本配置章节只写了 2022 年定增 20 亿与历年分红；"
                "但公司 2023 年发行 50 亿可转债、2024 年 H 股增发融资 80 亿港元，报告中完全缺失。"),
    },
    {
        "id": "F_overconfidence",
        "dim": "uncertainty",
        "expected": (1, 2),
        "note": "强推不确定结论：资料不足仍下确定判断",
        "doc": ("报告称'公司管理层从未有过任何不当行为'；对高管减持原因写'纯粹个人财务安排，无任何负面含义'；"
                "对 2026 年业绩预测'必然实现 30% 增长'——均未标注信息来源或不确定性。"),
    },
]


# ---------------------------------------------------------------- rubric 结构

def test_v1_preserved_for_traceability():
    assert set(JUDGE_RUBRICS_V1.keys()) == set(DIMS)
    assert JUDGE_PROMPT_VERSION == "judge-v2"
    assert JUDGE_RUBRICS_V1 is not JUDGE_RUBRICS


def test_v2_rubric_five_anchors_every_dimension():
    for dim in DIMS:
        anchors = JUDGE_RUBRICS[dim]["anchors"]
        assert sorted(anchors.keys()) == [1, 2, 3, 4, 5], dim
        for k in range(1, 6):
            assert anchors[k] and len(anchors[k]) >= 8, f"{dim} 锚点 {k} 缺失"


def test_v2_rubric_ceiling_rules_every_dimension():
    for dim in DIMS:
        ceilings = JUDGE_RUBRICS[dim]["ceiling_rules"]
        assert len(ceilings) >= 1, dim
        assert all(c and len(c) >= 10 for c in ceilings), dim


# ---------------------------------------------------------------- prompt 反 inflation 条款

def _render_prompt(dim):
    from evals.graders.judge import LLMJudgeBackend as _B
    b = _B("https://x/v1", "k", "m")
    # 直接复用 judge 的 prompt 构造：用 monkeypatch 掉网络不必要，这里手动渲染
    meta = JUDGE_RUBRICS[dim]
    anchors_text = "\n".join(f"{k} 分：{v}" for k, v in sorted(meta["anchors"].items()))
    ceilings_text = "\n".join(f"- {c}" for c in meta["ceiling_rules"])
    return (
        f"你是管理层档案评估的外部 Judge（prompt 版本 {JUDGE_PROMPT_VERSION}）。\n"
        f"维度：{dim}\n满分 5 分。\n"
        f"评分前必须：\n1. 找出该维度的缺陷、遗漏、反例或限制条件；\n"
        f"禁止仅因为报告提到了 rubric 中的关键词、章节或分析要素就给予高分。\n"
        f"只要存在重要问题，就不得给 5。\n"
        f"请输出严格 JSON：{{\"score\": 1-5, \"reason\": \"...\", \"strengths\": [\"...\"], "
        f"\"issues\": [\"...\"], \"evidence\": [\"...\"]}}\n"
        f"Rubric：\n{anchors_text}\nCeilings：\n{ceilings_text}"
    )


def test_prompt_contains_anti_inflation_clauses():
    p = _render_prompt("counter_evidence")
    for clause in ("judge-v2", "评分前必须", "找出该维度的缺陷", "禁止仅因为报告提到了",
                   "只要存在重要问题，就不得给 5", "strengths", "issues"):
        assert clause in p, f"prompt 缺少条款: {clause}"


def test_prompt_renders_anchors_and_ceilings():
    p = _render_prompt("capital_allocation")
    anchors = JUDGE_RUBRICS["capital_allocation"]["anchors"]
    assert "5 分：" in p and anchors[5][:12] in p
    for c in JUDGE_RUBRICS["capital_allocation"]["ceiling_rules"]:
        assert c in p


# ---------------------------------------------------------------- 假 judge 传导

class _FixedJudge:
    name = "llm"

    def __init__(self, scores):
        self._scores = scores

    def judge(self, dim, doc, max_score=None):
        s = self._scores.get(dim, 3)
        return JudgeResult(dimension=dim, score=s, max_score=5, reason="mock",
                           strengths=["s"], issues=["i"], evidence=["e"],
                           status="success", backend_name="llm")


def test_fixed_judge_conveys_v2_scores(tmp_path, monkeypatch):
    import evals.graders.analytical_quality as aq
    from evals.tests.conftest import GOOD_DOC, make_doc

    scores = {"counter_evidence": 5, "action_vs_outcome": 2, "capital_allocation": 3,
              "strategic_consistency": 4, "crisis_handling": 2, "uncertainty": 1}
    monkeypatch.setattr(aq, "get_backend", lambda: _FixedJudge(scores))
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = aq.grade(d, None)
    assert r.metrics["judge_total"] == 6
    assert r.metrics["judge_error_count"] == 0
    # (5+2+3+4+2+1)/30
    assert r.score == pytest.approx(17 / 30, abs=1e-4)
    # details 含 strengths/issues（v2 输出结构传导）
    detail = r.details["counter_evidence"]
    assert detail["strengths"] == ["s"] and detail["issues"] == ["i"]


# ---------------------------------------------------------------- 样例结构 + 真实校准（可选）

def test_calibration_cases_well_formed():
    assert len(CALIBRATION_CASES) == 6
    ids = {c["id"] for c in CALIBRATION_CASES}
    assert ids == {"A_excellent", "B_adequate", "C_missing", "D_action_as_outcome",
                   "E_capital_missing", "F_overconfidence"}
    for c in CALIBRATION_CASES:
        assert c["dim"] in DIMS
        lo, hi = c["expected"]
        assert 1 <= lo <= hi <= 5


@pytest.mark.skipif(not os.environ.get("RUN_LLM_CALIB"), reason="设 RUN_LLM_CALIB=1 才跑真实 LLM 校准")
def test_real_llm_calibration_cases():
    """真实 LLM 校准：对 A-F 样例逐维打分，断言落在预期档位（严格上限）。"""
    from evals.runners import ensure_env
    from evals.graders.judge import get_backend
    ensure_env()
    backend = get_backend()
    assert backend.name == "llm", "需要配置 EVAL_LLM_* 且 judge.backend=llm"
    for c in CALIBRATION_CASES:
        res = backend.judge(c["dim"], c["doc"], 5)
        assert res.status == "success", f"{c['id']} judge 失败: {res.error}"
        lo, hi = c["expected"]
        assert lo <= res.score <= hi, (
            f"{c['id']} ({c['dim']}) 得分 {res.score} 超出预期 {lo}..{hi}: {res.reason}")
