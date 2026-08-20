
"""Workflow / Tool Eval（Eval Layer 2）。

从 agent trace（tool call 列表）评价：
- Required Tool Recall：应执行的 required actions 实际完成比例（gate >= 0.95）
- Tool Argument Correctness：股票代码/市场/日期范围/接口选择等参数正确性
- Tool Efficiency：重复调用 / 冗余搜索 / 平均工具数（仅用于版本比较，不作 gate）

无 trace 时返回 N/A（score=None），不强制 gate。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import CONFIG, EvalCase, EvalError, GraderResult

# required_workflow 键 -> 工具名匹配模式（子串）
REQUIRED_ACTION_TOOLS = {
    "company_profile": ["company_profile", "company/profile", "profile"],
    "executive_trades": ["executive_trades", "senior-executive-shares-change", "esc"],
    "dividends": ["dividends", "dividend", "hot/df"],
    "penalties": ["company_penalties", "measures", "penalties"],
    "lawsuits": ["company_lawsuits", "lawsuits"],
    "pledge": ["share_pledge", "pledge", "ple"],
    "irm_qa": ["irm_qa", "irm"],
    "personnel_announcements": ["list_announcements", "announcement"],
    "lixinger_profile": ["company/profile", "cn/company/profile", "profile"],
    "lixinger_measures": ["measures"],
    "lixinger_inquiry": ["inquiry"],
    "wisburg_earnings_calls": ["search_earnings_calls", "earnings_calls", "get_earnings_call_detail", "wisburg"],
}

# 市场对应的数据源合法性
MARKET_SOURCES = {
    "A": ["cninfo", "lixinger", "wisburg", "tavily"],
    "H": ["lixinger", "wisburg", "tavily"],          # CNINFO 不覆盖港股
    "US": ["lixinger", "wisburg", "tavily"],
}


def _tool_names(trace: Dict[str, Any]) -> List[str]:
    return [s.get("tool_name", "") for s in trace.get("steps", [])]


def required_tool_recall(trace: Dict[str, Any], case: EvalCase) -> Tuple[int, int, List[str]]:
    """返回 (recalled, required, missing)。

    Live 模式下 trace 同时包含工具级步骤（Bash/Read/Write/Task...）与数据源级步骤
    （cninfo.xxx / lixinger.cn/... / wisburg.xxx / tavily.search）。required action
    匹配同时检查 tool_name 与 arguments 文本（如 Bash 命令里出现 semantic 调用名）。
    """
    names = [n.lower() for n in _tool_names(trace)]
    argtexts = []
    for s in trace.get("steps", []):
        try:
            argtexts.append(json.dumps(s.get("arguments", {}), ensure_ascii=False).lower())
        except Exception:
            argtexts.append(str(s.get("arguments", {})).lower())
    required = [k for k, v in (case.required_workflow or {}).items() if v]
    if not required:
        required = list(REQUIRED_ACTION_TOOLS.keys())
    recalled = 0
    missing = []
    for key in required:
        patterns = REQUIRED_ACTION_TOOLS.get(key, [key])
        hit = any(any(p in n for p in patterns) for n in names) or \
             any(any(p in a for p in patterns) for a in argtexts)
        if hit:
            recalled += 1
        else:
            missing.append(key)
    return recalled, len(required), missing


def _args_issues(trace: Dict[str, Any], case: EvalCase) -> List[EvalError]:
    """参数正确性检查。"""
    issues: List[EvalError] = []
    ticker = case.company.get("ticker", "")
    market = case.company.get("market", "A")
    base_code = ticker.split(".")[0]
    names = [s.get("tool_name", "").lower() for s in trace.get("steps", [])]
    argtexts = []
    for s in trace.get("steps", []):
        try:
            argtexts.append(json.dumps(s.get("arguments", {}), ensure_ascii=False).lower())
        except Exception:
            argtexts.append(str(s.get("arguments", {})).lower())

    # 1) 市场接口选择：港股/美股不得调 CNINFO（tool_name 或命令文本）
    if market in ("H", "US"):
        cninfo_hits = [n for n in names if "cninfo" in n]
        arg_hits = [a[:80] for a in argtexts if "cninfo" in a]
        if cninfo_hits or arg_hits:
            issues.append(EvalError("P1", "WORKFLOW_WRONG_MARKET",
                                    f"[{case.id}] {market} 市场使用了 CNINFO 接口: "
                                    f"{cninfo_hits[:3] or arg_hits[:1]}"))
    # 2) 电话会 detail 读取：search_earnings_calls 之后必须有 get_earnings_call_detail
    if any("search_earnings_calls" in n for n in names):
        if not any("get_earnings_call_detail" in n for n in names):
            issues.append(EvalError("P1", "WORKFLOW_MISSING_SOURCE",
                                    f"[{case.id}] 搜索到电话会纪要但未读取 detail（get_earnings_call_detail）"))
    # 3) 人事公告需要日期范围参数
    for s in trace.get("steps", []):
        tool = s.get("tool_name", "").lower()
        args = s.get("arguments", {}) or {}
        if "list_announcements" in tool or ("announcement" in tool and "cninfo" in tool):
            has_range = bool(args.get("start_date") or args.get("end_date") or args.get("date"))
            if not has_range:
                issues.append(EvalError("P2", "WORKFLOW_ARGUMENT",
                                        f"[{case.id}] 公告查询缺少日期范围参数"))
        if tool in ("cninfo.executive_trades", "executive_trades") or "senior-executive" in tool:
            code = args.get("stock_code") or args.get("stockCodes") or args.get("stockCode") or ""
            if code and base_code and str(code).split(".")[0] not in str(base_code) and base_code not in str(code):
                issues.append(EvalError("P0", "WORKFLOW_ARGUMENT",
                                        f"[{case.id}] 高管持股变动接口股票代码 {code!r} 与 case {ticker!r} 不符"))
    return issues


def _efficiency_metrics(trace: Dict[str, Any]) -> Dict[str, Any]:
    steps = trace.get("steps", [])
    seen: Dict[str, int] = {}
    duplicates = 0
    for s in steps:
        key = s.get("tool_name", "") + "::" + str(s.get("arguments", {}))
        if key in seen:
            duplicates += 1
        else:
            seen[key] = 1
    # 冗余 Tavily：已取得结构化数据后仍泛搜
    redundant_search = 0
    names = [s.get("tool_name", "") for s in steps]
    return {
        "tool_calls": len(steps),
        "duplicate_tool_calls": duplicates,
        "redundant_search_count": redundant_search,
    }


def grade(trace: Optional[Dict[str, Any]], case: EvalCase) -> GraderResult:
    r = GraderResult(name="workflow")
    if not trace:
        r.score = None
        r.gates["required_tool_recall"] = None
        r.details["skipped_reason"] = "无 trace（未记录工具调用）"
        return r

    recalled, required, missing = required_tool_recall(trace, case)
    recall = recalled / required if required else 1.0
    r.metrics["required_tool_recall"] = round(recall, 4)
    r.metrics["required_actions"] = required
    r.metrics["recalled_actions"] = recalled
    r.gates["required_tool_recall"] = recall >= CONFIG["gates"]["required_tool_recall"]["min"]
    r.details["missing_required_actions"] = missing

    # 参数正确性
    arg_issues = _args_issues(trace, case)
    r.errors.extend(arg_issues)
    total_args = max(1, len(arg_issues) + 1)  # 简化：有问题的比例
    r.metrics["argument_issues"] = len(arg_issues)
    r.details["argument_errors"] = [e.message for e in arg_issues]

    # 效率（仅记录）
    eff = _efficiency_metrics(trace)
    r.metrics.update(eff)

    # workflow 得分 = 0.7 * recall + 0.3 * (1 - 参数问题率)
    arg_ok_rate = 1.0 - min(1.0, len(arg_issues) / max(1, len(trace.get("steps", []))))
    r.score = round(0.7 * recall + 0.3 * arg_ok_rate, 4)
    for e in arg_issues:
        if e.severity == "P0":
            r.gates["workflow_no_p0_arg"] = False
    r.gates.setdefault("workflow_no_p0_arg", True)
    return r