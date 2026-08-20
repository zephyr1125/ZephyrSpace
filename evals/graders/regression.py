
"""M1-M8 高频错误模式 => 永久 Regression Tests（plan §15）。

每个 M 是一个确定性检查函数，输入 ArchiveDocument（+ 可选 golden facts），
输出 (ok, message, errors)。run_eval 对每个 company case 应用全部适用项；
pytest 用合成 fixture 直接测试每个函数。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import ArchiveDocument, EvalCase, EvalError, GraderResult, load_golden_facts
from .facts import parse_table_rows, strip_md

# ---------------------------------------------------------------- M1

def grade_M1(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M1: 现任管理层身份（董事长/CEO 为最新，不得用历史人物替代现任）。"""
    if not golden:
        return True, "无 golden facts，跳过", []
    cf = golden.get("critical_facts", {})
    errors: List[EvalError] = []
    text = doc.text
    ok = True
    for key, label in [("chairman", "董事长"), ("ceo", "CEO")]:
        gf = cf.get(key)
        if not gf or not gf.get("value"):
            continue
        if gf["value"] not in text:
            ok = False
            errors.append(EvalError("P0", "FACT_CURRENT_MANAGEMENT",
                                    f"[M1] {label} 应为现任 {gf['value']!r}，档案未出现（可能依赖陈旧记忆）",
                                    location=key))
    return ok, "ok" if ok else "; ".join(e.message for e in errors), errors


# ---------------------------------------------------------------- M2

def grade_M2(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M2: 独立处罚事件必须分行，不得合并。"""
    penalty_section = ""
    for key, body in doc.sections.items():
        if key.startswith("八、") or "监管" in key:
            penalty_section = body
            break
    errors: List[EvalError] = []
    merged_count = 0
    for row in parse_table_rows(penalty_section):
        if len(row) < 4:
            continue
        cells = [strip_md(c) for c in row]
        if not re.search(r"\d{4}", cells[0]):
            continue
        event_cell = cells[3] if len(cells) > 3 else ""
        org_cell = cells[2] if len(cells) > 2 else ""
        # 合并信号（仅看年份列，不看事项正文里的年份）：
        # 1) 年份列含 >=2 个不同年份且分号连接
        year_cell_years = set(re.findall(r"\d{4}", cells[0]))
        joined = " ".join(cells)
        if len(year_cell_years) >= 2 and "；" in joined:
            merged_count += 1
        # 2) 事项列含分号连接多个独立事件 且 机构列含多个机构
        elif "；" in event_cell and ("、" in org_cell or "；" in org_cell):
            merged_count += 1
        # 3) 单一事件行内含分号分隔的多个事项（如 "罚款50万；另案罚款20万"）
        elif re.search(r"；[^|]{4,}", event_cell):
            merged_count += 1
    if merged_count:
        err = EvalError("P1", "FACT_PENALTY",
                        f"[M2] 检测到 {merged_count} 处疑似合并的处罚记录（独立事件应分行）")
        errors.append(err)
        return False, err.message, errors
    return True, "ok", errors


# ---------------------------------------------------------------- M3

def grade_M3(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M3: 动作 ≠ 兑现。进行中的承诺不得标 ✅ 已兑现。"""
    errors: List[EvalError] = []
    # 扫描言行一致性表行
    yx_section = ""
    for key, body in doc.sections.items():
        if key.startswith("二、") or "言行" in key:
            yx_section = body
            break
    # 输入类词 = 执行了动作（预算/费用/投入）；结果类词 = 创造了价值（收入/利润/市占/量产等）
    INPUT_WORDS = ("投入", "费用", "预算", "支出", "资本开支", "capex", "研发费用", "扩产", "产能")
    OUTCOME_WORDS = ("利润", "收入", "市占", "量产", "交付", "客户", "产品", "实现", "达到",
                     "盈利", "全球", "第一", "亿元", "回购", "分红", "注销", "降本")
    for row in parse_table_rows(yx_section):
        if len(row) < 4:
            continue
        cells = [strip_md(c) for c in row]
        claim = cells[1] if len(cells) > 1 else ""
        outcome = cells[3] if len(cells) > 3 else ""
        evidence = cells[4] if len(cells) > 4 else ""
        # 跳过表头行
        if claim in ("管理层关键说法", "管理层关键承诺", "关键说法", "关键承诺", "年份") or "原文摘要" in claim:
            continue
        # 承诺含未来时态/目标词 + 标注已兑现 => 检查证据是"执行动作"还是"业务结果"
        forward = any(k in claim for k in ("将", "预计", "计划", "目标", "力争", "承诺", "加大", "投入", "建设"))
        if forward and any(k in outcome for k in ("✅", "已兑现", "兑现")):
            has_input = any(k in evidence for k in INPUT_WORDS)
            has_outcome = any(k in evidence for k in OUTCOME_WORDS)
            if has_input and not has_outcome:
                errors.append(EvalError(
                    "P1", "ANALYSIS_ACTION_VS_OUTCOME",
                    f"[M3] 承诺被标为已兑现，但证据仅显示执行动作（投入/费用），无业务结果指标：{claim[:40]}"))
    if errors:
        return False, "; ".join(e.message for e in errors), errors
    return True, "ok", errors


# ---------------------------------------------------------------- M4

def grade_M4(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M4: 融资工具覆盖清单（A股增发/配股/可转债/H股增发/优先股/股权激励）。"""
    required = ["增发", "配股", "可转债", "H股", "优先股", "股权激励"]
    cap_section = ""
    for key, body in doc.sections.items():
        if key.startswith("三、") or "资本配置" in key:
            cap_section = body
            break
    text = cap_section or doc.text
    missing = [k for k in required if k not in text]
    # 全文本兜底再查一次
    if missing:
        missing = [k for k in missing if k not in doc.text]
    if missing:
        err = EvalError("P1", "FACT_CAPITAL_ACTION",
                        f"[M4] 融资工具清单未覆盖: {', '.join(missing)}（可能遗漏摊薄工具）")
        return False, err.message, [err]
    return True, "ok", []


# ---------------------------------------------------------------- M5

def grade_M5(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M5: 减持判断必须双向——若期间有增持，禁止写"持续减持"。"""
    errors: List[EvalError] = []
    has_increase = bool(re.search(r"增持|买入", doc.text))
    for m in re.finditer(r"[^。\n]*持续减持[^。\n]*。?", doc.text):
        if has_increase:
            errors.append(EvalError("P1", "FACT_SHARE_TRANSACTION",
                                    f"[M5] 存在增持记录但出现'持续减持'表述：{m.group(0).strip()[:60]}"))
    if errors:
        return False, "; ".join(e.message for e in errors), errors
    return True, "ok", errors


# ---------------------------------------------------------------- M6

def grade_M6(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M6: 回购金额使用实际执行口径，不得以公告上限替代。"""
    errors: List[EvalError] = []
    if not golden:
        return True, "无 golden facts，跳过", []
    cf = golden.get("critical_facts", {})
    for ca in cf.get("capital_actions", []):
        if ca.get("type") != "buyback":
            continue
        actual = ca.get("actual_amount_cny")
        announced = ca.get("announced_upper_bound_cny")
        if actual is None:
            continue
        from .facts import _num_in_text
        if not _num_in_text(doc.text, actual) and announced is not None and _num_in_text(doc.text, announced):
            errors.append(EvalError("P1", "FACT_CAPITAL_ACTION",
                                    f"[M6] 回购金额使用公告上限 {announced}，实际执行 {actual} 未出现"))
    if errors:
        return False, "; ".join(e.message for e in errors), errors
    return True, "ok", errors


# ---------------------------------------------------------------- M7

def grade_M7(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M7: 原文摘录不得断章取义——保留限定条件（如果/在...条件下/当...时）。"""
    errors: List[EvalError] = []
    quote_section = ""
    for key, body in doc.sections.items():
        if key.startswith("十、") or "摘录" in key:
            quote_section = body
            break
    text = quote_section or doc.text
    # 引用行: "> ..."
    for m in re.finditer(r"^>\s*([^\n]+)", text, re.M):
        q = m.group(1).strip()
        # 含 预计/增长/将 等结果性表述、缺条件限定、且短促（疑似截断）=> 提示人工复核（P2）
        has_result = any(k in q for k in ("预计", "增长", "将", "目标", "达到"))
        has_condition = any(k in q for k in ("如果", "若", "在", "条件下", "假设", "需求恢复", "市场环境", "允许", "前提"))
        short_and_open = len(q) < 30 and not re.search(r"[。？！]$", q)
        if has_result and not has_condition and short_and_open:
            errors.append(EvalError("P2", "GROUNDING_QUOTE_CONTEXT",
                                    f"[M7] 短促摘录可能缺失限定条件（建议人工复核）：{q[:60]}"))
    if errors:
        return False, f"{len(errors)} 条摘录疑似断章取义", errors
    return True, "ok", errors


# ---------------------------------------------------------------- M8

def grade_M8(doc: ArchiveDocument, golden: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[EvalError]]:
    """M8: 高管变动必须建立近5年时间线，且识别12个月内密集离任模式。"""
    errors: List[EvalError] = []
    org_section = ""
    for key, body in doc.sections.items():
        if key.startswith("六、") or "组织与人才" in key:
            org_section = body
            break
    rows = []
    for row in parse_table_rows(org_section):
        if len(row) < 4:
            continue
        cells = [strip_md(c) for c in row]
        if re.search(r"\d{4}", cells[0]) and any(k in cells[3] for k in ("离任", "辞职", "聘任", "上任", "调整")):
            rows.append(cells)
    if len(rows) < 2:
        err = EvalError("P1", "WORKFLOW_MISSING_TIMELINE",
                        f"[M8] 高管变动时间线记录不足（仅 {len(rows)} 行），无法判断稳定性")
        return False, err.message, [err]
    # 12个月内密集离任检测：任一年份离任 >= 2 且分析部分未识别模式
    year_counts: Dict[str, int] = {}
    for cells in rows:
        year = re.search(r"(\d{4})", cells[0])
        if year:
            year_counts[year.group(1)] = year_counts.get(year.group(1), 0) + 1
    dense = {y: c for y, c in year_counts.items() if c >= 2}
    if dense:
        denied = re.search(r"集中离任[^。\n]{0,20}(否|无|不|未)", doc.text)
        confirmed = re.search(r"密集离任|离职潮|集中离任", doc.text)
        if not confirmed or denied:
            err = EvalError("P1", "FACT_MANAGEMENT_TURNOVER",
                            f"[M8] 检测到短期密集离任 {dense} 但正文未识别该模式（或否认）")
            return False, err.message, [err]
    return True, "ok", errors


# ---------------------------------------------------------------- combined grader

M_CHECKS = {
    "M1": grade_M1, "M2": grade_M2, "M3": grade_M3, "M4": grade_M4,
    "M5": grade_M5, "M6": grade_M6, "M7": grade_M7, "M8": grade_M8,
}

def grade(doc: ArchiveDocument, case: Optional[EvalCase] = None) -> GraderResult:
    """对单个 company case 运行全部适用 M 检查。"""
    r = GraderResult(name="regression")
    golden = None
    gf_path = case.golden_facts_path() if case else None
    if gf_path and gf_path.exists():
        golden = load_golden_facts(gf_path)
    ok_count = 0
    per_check: Dict[str, bool] = {}
    for name, fn in M_CHECKS.items():
        ok, msg, errs = fn(doc, golden)
        per_check[name] = ok
        r.errors.extend(errs)
        if ok:
            ok_count += 1
    r.score = round(ok_count / len(M_CHECKS), 4)
    r.metrics["regression_pass"] = ok_count
    r.metrics["regression_total"] = len(M_CHECKS)
    r.details["checks"] = per_check
    r.gates["regression_stability"] = ok_count == len(M_CHECKS)
    return r