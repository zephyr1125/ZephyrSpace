"""Deterministic Structure Eval 测试（Layer 3）。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import structure
from evals.graders.common import CONFIG
from evals.tests.conftest import GOOD_DOC, make_doc


def test_good_doc_passes_sections(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = structure.grade(d, None)
    assert r.gates["structure_sections"] is True
    assert r.gates["required_sections"] is True


def test_filename_regex():
    rx = re.compile(CONFIG["structure"]["filename_regex"])
    assert rx.match("长江电力 管理层档案 96 2026-05-31.md")
    assert rx.match("测试公司 管理层档案 80 2026-07-01.md")
    assert not rx.match("测试公司 管理层档案 2026-07-01.md")   # 漏评分
    assert not rx.match("测试公司 管理层档案.md")               # 漏评分+日期


def test_missing_section_fails(tmp_path):
    text = GOOD_DOC.replace("## 十、关键原文摘录", "## 十（已删除）", 1)
    text = text.replace("### 关于战略\\n\\n> \"在需求恢复的条件下，我们预计收入增长20%\" —— 2024 电话会\\n", "")
    d = make_doc(tmp_path, text, "测试公司 管理层档案 80 2026-07-01.md")
    r = structure.grade(d, None)
    assert r.gates["structure_sections"] is False
    assert r.gates["required_sections"] is False


def test_score_math_ok(tmp_path):
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = structure.grade(d, None)
    assert r.gates["structure_score_math"] is True
    assert d.total_score == 80


def test_score_math_broken(tmp_path):
    text = GOOD_DOC.replace("| **总分** | **100** | **80** |", "| **总分** | **100** | **85** |")
    d = make_doc(tmp_path, text, "测试公司 管理层档案 80 2026-07-01.md")
    r = structure.grade(d, None)
    assert r.gates["structure_score_math"] is False


def test_red_flag_rule(tmp_path):
    # 诚信 16/20 不触发；构造 诚信 6/20 且无红旗标注 → FAIL
    text = GOOD_DOC.replace("| 诚信与透明度 | 20 | 16 | 无重大失信 |", "| 诚信与透明度 | 20 | 6 | 有失信 |")
    text = text.replace("| **总分** | **100** | **80** |", "| **总分** | **100** | **70** |")
    d = make_doc(tmp_path, text, "测试公司 管理层档案 70 2026-07-01.md")
    r = structure.grade(d, None)
    assert r.gates["structure_red_flag_rule"] is False


def test_ticker_format():
    from evals.graders.structure import _ticker_check
    assert _ticker_check("600660.SH")[0]
    assert _ticker_check("000333.SZ")[0]
    assert _ticker_check("00700.HK")[0]
    assert _ticker_check("3606.HK")[0]
    assert _ticker_check("NVDA.US")[0]
    assert not _ticker_check("600660")[0]
    assert not _ticker_check("00700")[0]
    assert not _ticker_check("V")[0]


def test_frontmatter_required(tmp_path):
    text = GOOD_DOC.replace("分析日期: 2026-07-01", "")
    d = make_doc(tmp_path, text, "测试公司 管理层档案 80 2026-07-01.md")
    r = structure.grade(d, None)
    assert r.gates["structure_frontmatter"] is False


def test_quick_ref_before_analysis(tmp_path):
    # 把快速参考移到正文之后 → FAIL
    lines = GOOD_DOC.splitlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith("## 一、"))
    card_start = next(i for i, l in enumerate(lines) if l.startswith("## 📊"))
    # 找到卡片结束（下一个 '## ' 标题）
    end = next(i for i in range(card_start + 1, len(lines)) if lines[i].startswith("## "))
    block = lines[card_start:end]
    rest = lines[:card_start] + lines[end:idx] + lines[idx:]
    text = "\n".join(rest + block)
    d = make_doc(tmp_path, text, "测试公司 管理层档案 80 2026-07-01.md")
    r = structure.grade(d, None)
    assert r.gates["structure_quick_reference_card"] is False