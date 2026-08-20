"""Evidence Grounding Eval 测试（Layer 5）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import grounding
from evals.graders.common import case_from_dict
from evals.tests.conftest import GOOD_DOC, make_doc


def _case():
    return case_from_dict({
        "id": "management_archive_test",
        "company": {"name": "测试公司", "ticker": "600001.SH", "market": "A"},
        "prompt": "管理层档案 测试公司",
    })


def test_good_doc_claims_grounded(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = grounding.grade(d, _case())
    assert r.score is not None
    assert r.gates["grounded_claim_rate"] is True, r.errors


def test_bare_claims_lower_rate(tmp_path):
    # 综合结论只有无锚定断言（无年份/数字/来源）
    text = GOOD_DOC.replace(
        "> 该管理层资本配置克制（2022-2025年回购+分红）、重视股东回报，值得信任。",
        "> 该管理层很优秀。"
    )
    text = text.replace(
        """### 最突出的优点

1. 资本配置克制（2024年低位回购18.3亿元）
2. 重视股东回报（2023-2025连续分红，来源：年报）
3. 团队稳定（近5年无C-suite密集离任）""",
        """### 最突出的优点

1. 资本配置很克制
2. 很重视股东回报
3. 团队非常稳定"""
    )
    text = text.replace(
        """### 最需要警惕的问题

1. 行业监管风险（2023年证监会处罚50万元）""",
        """### 最需要警惕的问题

1. 危机处理有隐患"""
    )
    text = text.replace(
        """### 一句话评价

> 该管理层资本配置克制（2022-2025年回购+分红）、重视股东回报，值得信任。""",
        """### 一句话评价

> 该管理层整体优秀。"""
    )
    d = make_doc(tmp_path, text, "测试公司 管理层档案 80 2026-07-01.md")
    r = grounding.grade(d, _case())
    assert r.score < 0.9


def test_claim_extraction_finds_claims(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    claims = grounding.extract_claims(d)
    assert len(claims) >= 3
    assert any("资本配置" in c["claim"] for c in claims)