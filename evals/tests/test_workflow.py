"""Workflow / Tool Eval 测试（Layer 2）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import workflow
from evals.graders.common import case_from_dict

FULL_CASE = case_from_dict({
    "id": "management_archive_workflow_test",
    "company": {"name": "测试公司", "ticker": "600001.SH", "market": "A"},
    "prompt": "管理层档案 测试公司",
    "required_workflow": {
        "company_profile": True,
        "executive_trades": True,
        "dividends": True,
        "penalties": True,
        "lawsuits": True,
        "pledge": True,
        "irm_qa": True,
        "personnel_announcements": True,
        "lixinger_profile": True,
        "lixinger_measures": True,
        "lixinger_inquiry": True,
        "wisburg_earnings_calls": True,
    },
})


def _full_trace():
    return {
        "case_id": "management_archive_workflow_test",
        "started_at": "2026-07-01T00:00:00",
        "steps": [
            {"tool_name": "cninfo.company_profile", "arguments": {"stock_code": "600001.SH"}},
            {"tool_name": "cninfo.executive_trades", "arguments": {"stock_code": "600001", "limit": 50}},
            {"tool_name": "cninfo.dividends", "arguments": {"stock_code": "600001.SH"}},
            {"tool_name": "cninfo.company_penalties", "arguments": {"stock_code": "600001.SH"}},
            {"tool_name": "cninfo.company_lawsuits", "arguments": {"stock_code": "600001.SH"}},
            {"tool_name": "cninfo.share_pledge", "arguments": {"stock_code": "600001.SH"}},
            {"tool_name": "cninfo.irm_qa", "arguments": {"stock_code": "600001.SH"}},
            {"tool_name": "cninfo.list_announcements", "arguments": {"stock_code": "600001.SH", "start_date": "2021-01-01", "end_date": "2026-07-01"}},
            {"tool_name": "lixinger.cn/company/profile", "arguments": {"stockCode": "600001"}},
            {"tool_name": "lixinger.cn/company/measures", "arguments": {"stockCode": "600001"}},
            {"tool_name": "lixinger.cn/company/inquiry", "arguments": {"stockCode": "600001"}},
            {"tool_name": "wisburg.search_earnings_calls", "arguments": {}},
            {"tool_name": "wisburg.get_earnings_call_detail", "arguments": {}},
        ],
    }


def test_required_tool_recall_full():
    r = workflow.grade(_full_trace(), FULL_CASE)
    assert r.gates["required_tool_recall"] is True
    assert r.metrics["required_tool_recall"] >= 0.95


def test_missing_required_actions():
    trace = _full_trace()
    trace["steps"] = [s for s in trace["steps"] if "penalties" not in s["tool_name"]
                      and "measures" not in s["tool_name"]]
    r = workflow.grade(trace, FULL_CASE)
    assert r.gates["required_tool_recall"] is False
    assert "penalties" in r.details["missing_required_actions"]


def test_hk_wrong_market_uses_cninfo():
    hk_case = case_from_dict({
        "id": "hk_test",
        "company": {"name": "腾讯控股", "ticker": "00700.HK", "market": "H"},
        "prompt": "管理层档案 腾讯",
        "required_workflow": {"wisburg_earnings_calls": True, "lixinger_profile": True},
    })
    trace = {
        "case_id": "hk_test",
        "started_at": "2026-07-01T00:00:00",
        "steps": [
            {"tool_name": "cninfo.company_profile", "arguments": {"stock_code": "00700.HK"}},
            {"tool_name": "wisburg.search_earnings_calls", "arguments": {}},
        ],
    }
    r = workflow.grade(trace, hk_case)
    assert any(e.category == "WORKFLOW_WRONG_MARKET" for e in r.errors)


def test_duplicate_detection():
    trace = _full_trace()
    trace["steps"].append(dict(trace["steps"][0]))
    r = workflow.grade(trace, FULL_CASE)
    assert r.metrics["duplicate_tool_calls"] >= 1


def test_no_trace_is_na():
    r = workflow.grade(None, FULL_CASE)
    assert r.score is None
    assert r.gates["required_tool_recall"] is None


def test_earnings_call_detail_required():
    trace = _full_trace()
    trace["steps"] = [s for s in trace["steps"] if "get_earnings_call_detail" not in s["tool_name"]]
    r = workflow.grade(trace, FULL_CASE)
    assert any(e.category == "WORKFLOW_MISSING_SOURCE" for e in r.errors)
