
"""Fact Accuracy Eval (Eval Layer 4).

从最终 Markdown 确定性抽取结构化事实（董事长/CEO/实控人/处罚/高管变动/资本动作），
与 Golden Facts 匹配，计算：
- Fact Precision
- Fact Recall
- Critical Fact Accuracy（P0 关键事实，硬门槛 >= 0.98）
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import (
    CONFIG, ArchiveDocument, EvalCase, EvalError, GraderResult, load_golden_facts,
)

TICK = chr(96)  # 反引号

# ---------------------------------------------------------------- table parsing

def parse_table_rows(text: str) -> List[List[str]]:
    """解析 markdown 表格，返回行（每行是 cell 列表）。跳过表头分隔行。"""
    rows: List[List[str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        # 表头分隔行如 |---|---|
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def strip_md(s: str) -> str:
    s = re.sub(r"\*\*|\*|" + TICK, "", s)
    s = re.sub(r"\[\[([^|\]]+)(\|[^\]]+)?\]\]", r"\1", s)
    return s.strip()


# ---------------------------------------------------------------- fact extraction

def extract_facts(doc: ArchiveDocument) -> Dict[str, Any]:
    """确定性抽取结构事实。"""
    text = doc.text
    facts: Dict[str, Any] = {
        "chairman": None, "ceo": None, "controller": None,
        "controller_type": None, "penalties": [], "management_changes": [],
        "capital_actions": [],
    }
    # ---- 一、管理层画像 核心人物表
    person_section = ""
    for key, body in doc.sections.items():
        if key.startswith("一、") or "画像" in key:
            person_section = body
            break
    for row in parse_table_rows(person_section):
        if len(row) < 2:
            continue
        role = strip_md(row[0])
        name = strip_md(row[1]) if len(row) > 1 else ""
        if not name or name in ("姓名", "—", "-", "N/A"):
            continue
        if re.search(r"(?<!副)(董事长|董事局主席)", role):
            facts["chairman"] = name
        if re.search(r"(?<!副)(总经理|CEO|首席执行官|总裁)", role):
            facts["ceo"] = name
        if "实际控制人" in role:
            facts["controller"] = name

    # ---- 控制权结构（实控人类型）
    for m in re.finditer(r"实际控制人类型[：:]\s*([^\n\r]+)", text):
        facts["controller_type"] = m.group(1).strip()
        break

    # ---- 八、监管与合规记录
    penalty_section = ""
    for key, body in doc.sections.items():
        if key.startswith("八、") or "监管" in key:
            penalty_section = body
            break
    for row in parse_table_rows(penalty_section):
        if len(row) < 4:
            continue
        year = strip_md(row[0])
        if not re.search(r"\d{4}", year):
            continue
        org = strip_md(row[2]) if len(row) > 2 else ""
        event = strip_md(row[3]) if len(row) > 3 else ""
        amount = ""
        if len(row) > 4:
            amount = strip_md(row[4])
        facts["penalties"].append({
            "year": year, "org": org, "event": event, "amount": amount,
        })

    # ---- 六、组织与人才 高管变动时间线
    org_section = ""
    for key, body in doc.sections.items():
        if key.startswith("六、") or "组织与人才" in key:
            org_section = body
            break
    for row in parse_table_rows(org_section):
        if len(row) < 4:
            continue
        year = strip_md(row[0])
        if not re.search(r"\d{4}", year):
            continue
        person = strip_md(row[1]) if len(row) > 1 else ""
        role = strip_md(row[2]) if len(row) > 2 else ""
        change = strip_md(row[3]) if len(row) > 3 else ""
        facts["management_changes"].append({
            "year": year, "person": person, "role": role, "change": change,
        })

    # ---- 三、资本配置记录（粗略：回购/分红/定增关键词行）
    cap_section = ""
    for key, body in doc.sections.items():
        if key.startswith("三、") or "资本配置" in key:
            cap_section = body
            break
    for row in parse_table_rows(cap_section):
        if len(row) < 3:
            continue
        year = strip_md(row[0])
        if not re.search(r"\d{4}", year):
            continue
        action = strip_md(row[1]) if len(row) > 1 else ""
        amount = strip_md(row[2]) if len(row) > 2 else ""
        if any(k in action for k in ("回购", "分红", "定增", "配股", "可转债", "并购", "增发")):
            facts["capital_actions"].append({
                "year": year, "action": action, "amount": amount,
            })
    return facts


# ---------------------------------------------------------------- matching


def _num_in_text(text: str, amount_val: float) -> bool:
    """匹配金额：支持纯数字、千分位、亿/万单位三种写法。"""
    text_flat = text.replace(",", "").replace(" ", "")
    if str(int(amount_val)) in text_flat:
        return True
    # 亿/万单位表示（如 29.9亿、4000万）
    for unit, mult in (("万亿", 1e12), ("亿", 1e8), ("万", 1e4)):
        if amount_val >= mult:
            val = amount_val / mult
            for fmt in (f"{val:g}", f"{val:.1f}", f"{val:.2f}"):
                if (fmt + unit) in text_flat:
                    return True
    return False


def _match_critical(case: EvalCase, doc: ArchiveDocument, golden: Dict[str, Any],
                    extracted: Dict[str, Any]) -> Tuple[int, int, List[EvalError]]:
    """返回 (correct, evaluated, errors)。"""
    correct = 0
    evaluated = 0
    errors: List[EvalError] = []
    text = doc.text
    cf = golden.get("critical_facts", {})

    # 人物类
    for key, label in [("chairman", "董事长"), ("ceo", "CEO"), ("controller", "实控人")]:
        gf = cf.get(key)
        if not gf or not gf.get("value"):
            continue
        evaluated += 1
        value = gf["value"]
        hit = value in text
        # 别名兜底（如 全名 vs 简称）
        if not hit and extracted.get(key) and extracted[key] == value:
            hit = True
        if hit:
            correct += 1
        else:
            sev = gf.get("severity", "P0")
            errors.append(EvalError(sev, "FACT_CURRENT_MANAGEMENT",
                                    "[" + case.id + "] " + label + " 应为 " + repr(value) + "，档案未找到",
                                    location=key))

    # 处罚
    for p in cf.get("penalties", []):
        evaluated += 1
        org_ok = p.get("regulator") in text if p.get("regulator") else True
        event_ok = p.get("event") in text if p.get("event") else True
        amount_ok = True
        if p.get("amount_cny") is not None:
            amount_ok = _num_in_text(text, p["amount_cny"])
        sev = p.get("severity", "P0")
        if org_ok and event_ok and amount_ok:
            correct += 1
        else:
            errors.append(EvalError(
                sev, "FACT_PENALTY",
                "[" + case.id + "] 处罚 " + str(p.get("date")) + " " + str(p.get("regulator"))
                + " " + str(p.get("event")) + " 未完整呈现 (org=" + str(org_ok)
                + ", event=" + str(event_ok) + ", amount=" + str(amount_ok) + ")"))

    # 回购：公告上限 vs 实际执行（M6）
    for ca in cf.get("capital_actions", []):
        if ca.get("type") != "buyback":
            continue
        actual = ca.get("actual_amount_cny")
        announced = ca.get("announced_upper_bound_cny")
        if actual is None:
            continue  # golden 未给出实际金额，无法评价
        evaluated += 1
        sev = ca.get("severity", "P1")
        if actual is not None and _num_in_text(text, actual):
            correct += 1
        elif actual is not None and announced is not None and _num_in_text(text, announced):
            # 只出现公告上限 → 口径混淆
            errors.append(EvalError(sev, "FACT_CAPITAL_ACTION",
                                    "[" + case.id + "] 回购仅出现公告上限 " + str(announced)
                                    + "，未呈现实际执行金额 " + str(actual) + "（M6）"))
        else:
            errors.append(EvalError(sev, "FACT_CAPITAL_ACTION",
                                    "[" + case.id + "] 回购实际金额 " + str(actual) + " 未在档案中出现"))

    # 高管变动（重大离任）
    for mc in cf.get("management_changes", []):
        evaluated += 1
        sev = mc.get("severity", "P1")
        person = mc.get("person", "")
        if person and person in text:
            correct += 1
        else:
            errors.append(EvalError(sev, "FACT_MANAGEMENT_CHANGE",
                                    "[" + case.id + "] 高管变动 " + str(mc.get("date")) + " "
                                    + person + " (" + str(mc.get("role")) + ") 未记录"))

    return correct, evaluated, errors


# ---------------------------------------------------------------- grader

def grade(doc: ArchiveDocument, case: EvalCase) -> GraderResult:
    r = GraderResult(name="facts")
    gf_path = case.golden_facts_path()
    if not gf_path or not gf_path.exists():
        r.score = None
        r.details["skipped_reason"] = "无 golden facts 文件"
        return r

    golden = load_golden_facts(gf_path)
    extracted = extract_facts(doc)
    r.details["extracted"] = extracted

    correct, evaluated, errors = _match_critical(case, doc, golden, extracted)
    r.errors.extend(errors)
    r.metrics["critical_facts_correct"] = correct
    r.metrics["critical_facts_evaluated"] = evaluated
    if evaluated:
        acc = round(correct / evaluated, 4)
        r.metrics["critical_fact_accuracy"] = acc
        r.score = acc
        min_acc = CONFIG["gates"]["critical_fact_accuracy"]["min"]
        r.gates["critical_fact_accuracy"] = acc >= min_acc
    else:
        r.score = None
        r.gates["critical_fact_accuracy"] = None

    # Fact Recall（含非关键事实的宽松匹配）
    recall_hits = 0
    recall_total = 0
    for p in golden.get("known_positive_cases", []):
        recall_total += 1
        if p.get("claim", "") and p["claim"] in doc.text:
            recall_hits += 1
    for rf in golden.get("known_red_flags", []):
        recall_total += 1
        if rf.get("description", "") and rf["description"] in doc.text:
            recall_hits += 1
    if recall_total:
        r.metrics["fact_recall"] = round(recall_hits / recall_total, 4)

    gf = golden.get("critical_facts", {})
    r.details["golden_summary"] = {
        "critical_facts": len(gf),
        "positive_cases": len(golden.get("known_positive_cases", [])),
        "red_flags": len(golden.get("known_red_flags", [])),
        "forbidden_claims": len(golden.get("forbidden_claims", [])),
    }
    # forbidden claims 检测
    for fc in golden.get("forbidden_claims", []):
        if fc in doc.text:
            r.add_error("P1", "FACT_FORBIDDEN_CLAIM",
                        "[" + case.id + "] 出现禁止性表述: " + repr(fc))
    return r