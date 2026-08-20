"""Live Eval 基础设施测试：
- build_live_prompt / _build_command
- parse_claude_stream（stream-json -> 工具级 trace）
- parse_source_trace（api_tracker JSONL -> 数据源级 trace）
- api_tracker 转发器（EVAL_TRACE_PATH）
- workflow grader 对 merged live trace 的 required recall / HK 禁 CNINFO / 重复调用
- run_eval --mode live/frozen 参数
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import workflow
from evals.graders.common import case_from_dict
from evals.runners.run_eval import build_parser
from evals.runners.run_skill import (
    ClaudeAgentRunner, ReplayRunner, build_live_prompt, parse_claude_stream, parse_source_trace,
)
from evals.runners.trace_recorder import load_trace

CASE = case_from_dict({
    "id": "management_archive_005",
    "company": {"name": "三安光电", "ticker": "600703.SH", "market": "A"},
    "prompt": "管理层档案 三安光电",
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


# ---------------------------------------------------------------- prompt / command

def test_build_live_prompt_contains_skill_and_company(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text("# skill", encoding="utf-8")
    p = build_live_prompt(CASE, skill)
    assert "三安光电" in p
    assert "600703.SH" in p
    assert str(skill) in p
    assert "管理层档案" in p


def test_build_command_flags(tmp_path):
    r = ClaudeAgentRunner(model="sonnet")
    cmd = r._build_command("test prompt")
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--output-format" in cmd and "stream-json" in cmd
    assert "--permission-mode" in cmd and "bypassPermissions" in cmd
    assert "--model" in cmd and "sonnet" in cmd


# ---------------------------------------------------------------- stream parsing

def _stream_jsonl(tmp_path, n_tools=3, with_error=False):
    path = tmp_path / "stream.jsonl"
    lines = []
    # init
    lines.append(json.dumps({"type": "system", "subtype": "init", "session_id": "s1",
                             "model": "test-model", "tools": []}))
    for i in range(n_tools):
        tid = f"toolu_{i}"
        lines.append(json.dumps({
            "type": "assistant",
            "message": {
                "id": f"msg_{i}",
                "content": [{"type": "tool_use", "id": tid, "name": "Bash",
                             "input": {"command": f"python -c 'from scripts.cninfo_api import CninfoClient; c=CninfoClient(); print(c.company_profile(\"600703\"))'"}}],
                "timestamp": f"2026-08-20T10:0{i}:00.000Z",
            },
        }))
        err = i == 0 and with_error
        lines.append(json.dumps({
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "tool_use_id": tid,
                             "content": "data", "is_error": err}],
                "timestamp": f"2026-08-20T10:0{i}:01.000Z",
            },
        }))
    lines.append(json.dumps({"type": "result", "subtype": "success", "result": "done",
                             "total_cost_usd": 0.42}))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_parse_claude_stream(tmp_path):
    steps = parse_claude_stream(_stream_jsonl(tmp_path, 3))
    assert len(steps) == 3
    assert all(s["tool_name"] == "Bash" for s in steps)
    assert all(s["result_status"] == "ok" for s in steps)
    assert all("command" in s["arguments"] for s in steps)
    assert all(s["duration_ms"] == 1000.0 for s in steps)


def test_parse_claude_stream_with_error(tmp_path):
    steps = parse_claude_stream(_stream_jsonl(tmp_path, 2, with_error=True))
    assert steps[0]["result_status"] == "error"
    assert "error" in steps[0]
    assert steps[1]["result_status"] == "ok"


def test_parse_claude_stream_missing_file(tmp_path):
    assert parse_claude_stream(tmp_path / "nope.jsonl") == []


# ---------------------------------------------------------------- source trace parsing

def _source_jsonl(tmp_path):
    path = tmp_path / "sources.jsonl"
    lines = [
        {"event": "call", "tool_name": "cninfo.company_profile",
         "arguments": {"api": "cninfo", "endpoint": "p_sysapi1133"}, "timestamp": "t1"},
        {"event": "result", "tool_name": "cninfo.company_profile",
         "result_status": "ok", "duration_ms": 812.5, "timestamp": "t2"},
        {"event": "call", "tool_name": "tavily.search",
         "arguments": {"context": "query=三安光电 处罚"}, "timestamp": "t3"},
        {"event": "result", "tool_name": "tavily.search",
         "result_status": "error", "duration_ms": 300, "error": "rate limited", "timestamp": "t4"},
    ]
    path.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lines), encoding="utf-8")
    return path


def test_parse_source_trace(tmp_path):
    steps = parse_source_trace(_source_jsonl(tmp_path))
    assert len(steps) == 2
    assert steps[0]["tool_name"] == "cninfo.company_profile"
    assert steps[0]["result_status"] == "ok"
    assert steps[0]["duration_ms"] == 812.5
    assert steps[1]["tool_name"] == "tavily.search"
    assert steps[1]["result_status"] == "error"
    assert steps[1]["error"] == "rate limited"


# ---------------------------------------------------------------- api_tracker forwarder

def test_api_tracker_forwarder_writes_trace(tmp_path, monkeypatch):
    import scripts.api_tracker as at
    out = tmp_path / "eval_trace.jsonl"
    monkeypatch.setenv("EVAL_TRACE_PATH", str(out))
    # NoOpTracker（无 active run 时）也应转发
    t = at.get_tracker()
    with t.track("tavily", "search", context="query=test"):
        pass
    records = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(records) == 2
    assert records[0]["event"] == "call" and records[0]["tool_name"] == "tavily.search"
    assert records[1]["event"] == "result" and records[1]["result_status"] == "ok"


def test_api_tracker_forwarder_noop_without_env(tmp_path, monkeypatch):
    import scripts.api_tracker as at
    monkeypatch.delenv("EVAL_TRACE_PATH", raising=False)
    t = at.get_tracker()
    out = tmp_path / "nope.jsonl"
    with t.track("tavily", "search"):
        pass
    assert not out.exists()  # 未设置 env 时零副作用


def test_api_tracker_cninfo_semantic_name(monkeypatch, tmp_path):
    import scripts.api_tracker as at
    out = tmp_path / "t.jsonl"
    monkeypatch.setenv("EVAL_TRACE_PATH", str(out))
    t = at.get_tracker()
    t.record_call("cninfo", "p_stock2218")
    t.record_result("cninfo", "p_stock2218", success=True, duration_ms=100)
    recs = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert recs[0]["tool_name"] == "cninfo.executive_trades"


# ---------------------------------------------------------------- workflow grader on live trace

def _merged_live_trace():
    """模拟 live trace：工具级（Bash 命令含 semantic 调用）+ 数据源级。"""
    return {
        "case_id": "management_archive_005",
        "steps": [
            # 数据源级（api_tracker 转发器）
            {"tool_name": "cninfo.company_profile", "arguments": {"api": "cninfo", "endpoint": "p_sysapi1133"}, "result_status": "ok"},
            {"tool_name": "cninfo.executive_trades", "arguments": {"api": "cninfo", "endpoint": "p_stock2218"}, "result_status": "ok"},
            {"tool_name": "cninfo.dividends", "arguments": {"api": "cninfo", "endpoint": "p_sysapi1139"}, "result_status": "ok"},
            {"tool_name": "cninfo.company_penalties", "arguments": {"api": "cninfo", "endpoint": "p_stock2248"}, "result_status": "ok"},
            {"tool_name": "cninfo.company_lawsuits", "arguments": {"api": "cninfo", "endpoint": "p_stock2246"}, "result_status": "ok"},
            {"tool_name": "cninfo.share_pledge", "arguments": {"api": "cninfo", "endpoint": "p_stock2220"}, "result_status": "ok"},
            {"tool_name": "cninfo.irm_qa", "arguments": {"api": "cninfo", "endpoint": "irm"}, "result_status": "ok"},
            {"tool_name": "lixinger.cn/company/profile", "arguments": {}, "result_status": "ok"},
            {"tool_name": "lixinger.cn/company/measures", "arguments": {}, "result_status": "ok"},
            {"tool_name": "lixinger.cn/company/inquiry", "arguments": {}, "result_status": "ok"},
            {"tool_name": "wisburg.search_earnings_calls", "arguments": {}, "result_status": "ok"},
            {"tool_name": "wisburg.get_earnings_call_detail", "arguments": {}, "result_status": "ok"},
            # 工具级（Bash 命令含 personnel announcements 语义）
            {"tool_name": "Bash", "arguments": {"command": "python -c 'from scripts.cninfo_api import CninfoClient; c=CninfoClient(); print(c.list_announcements(\"600703\", start_date=\"2021-01-01\", end_date=\"2026-08-20\"))'"}, "result_status": "ok"},
            # 重复调用检测
            {"tool_name": "cninfo.dividends", "arguments": {"api": "cninfo", "endpoint": "p_sysapi1139"}, "result_status": "ok"},
        ],
    }


def test_workflow_grader_live_trace_recall():
    r = workflow.grade(_merged_live_trace(), CASE)
    assert r.gates["required_tool_recall"] is True
    assert r.metrics["required_tool_recall"] >= 0.95
    assert r.metrics["duplicate_tool_calls"] >= 1


def test_workflow_grader_hk_no_cninfo():
    hk = case_from_dict({
        "id": "hk_test", "company": {"name": "腾讯控股", "ticker": "00700.HK", "market": "H"},
        "prompt": "x", "required_workflow": {"wisburg_earnings_calls": True},
    })
    trace = {"case_id": "hk_test", "steps": [
        {"tool_name": "cninfo.company_profile", "arguments": {"api": "cninfo"}, "result_status": "ok"},
        {"tool_name": "wisburg.search_earnings_calls", "arguments": {}, "result_status": "ok"},
    ]}
    r = workflow.grade(trace, hk)
    assert any(e.category == "WORKFLOW_WRONG_MARKET" for e in r.errors)


def test_workflow_grader_missing_earnings_detail():
    trace = {"case_id": "x", "steps": [
        {"tool_name": "wisburg.search_earnings_calls", "arguments": {}, "result_status": "ok"},
    ]}
    c = case_from_dict({"id": "x", "company": {"name": "a", "ticker": "000001.SZ", "market": "A"},
                        "prompt": "p", "required_workflow": {"wisburg_earnings_calls": True}})
    r = workflow.grade(trace, c)
    assert any(e.category == "WORKFLOW_MISSING_SOURCE" for e in r.errors)


# ---------------------------------------------------------------- run_eval CLI

def test_run_eval_parser_modes():
    p = build_parser()
    frozen = p.parse_args(["--mode", "frozen", "--run-name", "f1"])
    assert frozen.mode == "frozen"
    live = p.parse_args(["--mode", "live", "--run-name", "l1", "--case", "management_archive_005",
                         "--skill", "management-archive/SKILL.md", "--cli", "claude",
                         "--cli-timeout", "600", "--model", "sonnet"])
    assert live.mode == "live"
    assert live.case == "management_archive_005"
    assert live.cli_timeout == 600
    assert live.model == "sonnet"


def test_get_runner_kinds():
    from evals.runners.run_skill import get_runner
    assert isinstance(get_runner("frozen"), ReplayRunner)
    assert isinstance(get_runner("replay"), ReplayRunner)
    assert isinstance(get_runner("live"), ClaudeAgentRunner)
    assert isinstance(get_runner("agent"), ClaudeAgentRunner)
    with pytest.raises(ValueError):
        get_runner("nope")