"""Fact Accuracy Eval 测试（Layer 4）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import facts
from evals.graders.common import VAULT_ROOT, load_archive, load_golden_facts, case_from_dict

GOLDEN = {
    "company": {"name": "测试公司", "ticker": "600001.SH"},
    "critical_facts": {
        "chairman": {"value": "张三", "as_of": "2026-07-01", "severity": "P0"},
        "ceo": {"value": "李四", "as_of": "2026-07-01", "severity": "P0"},
        "controller": {"value": "张三", "as_of": "2026-07-01", "severity": "P0"},
        "penalties": [
            {"date": "2023", "regulator": "证监会", "event": "信息披露违规",
             "amount_cny": 500000, "severity": "P0"},
        ],
    },
    "known_positive_cases": [
        {"id": "p1", "claim": "持续分红", "outcome": "连续分红"},
    ],
    "known_red_flags": [
        {"id": "r1", "description": "行业监管风险", "severity": "P2"},
    ],
    "forbidden_claims": [],
}


def _case(tmp_path, golden_yaml_path=None):
    return case_from_dict({
        "id": "management_archive_test",
        "company": {"name": "测试公司", "ticker": "600001.SH", "market": "A"},
        "prompt": "管理层档案 测试公司",
        "golden_facts_file": str(golden_yaml_path) if golden_yaml_path else None,
    })


def test_extract_facts_from_table(tmp_path):
    from evals.tests.conftest import GOOD_DOC, make_doc
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    f = facts.extract_facts(d)
    assert f["chairman"] == "张三"
    assert f["ceo"] == "李四"
    assert f["controller"] == "张三"
    assert f["controller_type"] == "自然人"
    assert any("信息披露违规" in p["event"] for p in f["penalties"])


def test_num_in_text_units():
    assert facts._num_in_text("罚款29.9亿元人民币", 2990000000)
    assert facts._num_in_text("罚款50万元", 500000)
    assert facts._num_in_text("回购18.3亿", 1830000000)
    assert not facts._num_in_text("罚款50万", 2990000000)


def test_golden_match_success(tmp_path):
    from evals.tests.conftest import GOOD_DOC, make_doc
    # 写入 golden yaml 供 case 引用
    gf = tmp_path / "golden.yaml"
    import yaml
    gf.write_text(yaml.safe_dump(GOLDEN, allow_unicode=True), encoding="utf-8")
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    c = _case(tmp_path, gf)
    r = facts.grade(d, c)
    assert r.score is not None and r.score >= 0.98, r.errors
    assert r.gates["critical_fact_accuracy"] is True


def test_golden_match_wrong_chairman(tmp_path):
    import yaml
    from evals.tests.conftest import GOOD_DOC, make_doc
    gf = tmp_path / "golden.yaml"
    golden = dict(GOLDEN)
    golden["critical_facts"] = dict(GOLDEN["critical_facts"])
    golden["critical_facts"]["chairman"] = {"value": "钱七", "as_of": "2026-07-01", "severity": "P0"}
    gf.write_text(yaml.safe_dump(golden, allow_unicode=True), encoding="utf-8")
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    c = _case(tmp_path, gf)
    r = facts.grade(d, c)
    assert any(e.category == "FACT_CURRENT_MANAGEMENT" and e.severity == "P0" for e in r.errors)


def test_real_fuyao_archive_golden(tmp_path):
    """集成测试：真实福耀档案 vs 真实 golden facts。"""
    arc = VAULT_ROOT / "管理层档案" / "福耀玻璃 管理层档案 93 2026-05-31.md"
    if not arc.exists():
        pytest.skip("真实档案缺失")
    gf_path = VAULT_ROOT / "evals" / "fixtures" / "golden_facts" / "600660.SH.yaml"
    if not gf_path.exists():
        pytest.skip("golden facts 缺失")
    d = load_archive(arc)
    c = case_from_dict({
        "id": "management_archive_001",
        "company": {"name": "福耀玻璃", "ticker": "600660.SH", "market": "A"},
        "prompt": "管理层档案 福耀玻璃",
        "golden_facts_file": str(gf_path.relative_to(VAULT_ROOT / "evals")),
    })
    r = facts.grade(d, c)
    assert r.metrics["critical_facts_evaluated"] >= 3
    assert r.metrics["critical_facts_correct"] >= 3
