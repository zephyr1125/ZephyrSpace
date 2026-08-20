
"""Trigger Eval（Eval Layer 1）。

从 SKILL.md 的「触发条件」章节提取触发词规则，对标注数据集（positive/negative）
计算 Accuracy / Precision / Recall / FPR / FNR。

若 SKILL.md 修改了触发条件，规则随之变化——本层衡量修改是否破坏既有标注。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .common import CONFIG, EvalCase, EvalError, GraderResult

# ---------------------------------------------------------------- rule extraction

def extract_trigger_rules(skill_text: str) -> Dict[str, List[str]]:
    """从 SKILL.md 提取触发词。返回 {positive_keywords: [...], negative_hints: [...]}。"""
    pos: List[str] = []
    neg: List[str] = []
    if skill_text:
        # 触发条件 章节
        m = re.search(r"##+\s*触发条件(.*?)(?=\n##+\s*[^触]|\Z)", skill_text, re.S)
        section = m.group(1) if m else skill_text[:4000]
        for kw in re.findall(r'["“”]([^"“”]{2,30})["“”]', section):
            # 斜杠分隔的触发词列表拆开（如 "管理层档案 / 老板档案 / 管理层尽调"）
            for seg in re.split(r"\s*/\s*|/", kw):
                seg = seg.strip().strip("，,。 ")
                if len(seg) < 2:
                    continue
                if any(x in seg for x in ("PE", "估值", "股价", "市盈率", "市净率", "现金流")):
                    neg.append(seg)
                else:
                    pos.append(seg)
    # 配置兜底
    cfg = CONFIG.get("trigger", {})
    pos = list(dict.fromkeys(pos + cfg.get("positive_keywords", [])))
    neg = list(dict.fromkeys(neg + cfg.get("negative_hint_keywords", [])))
    return {"positive": pos, "negative": neg}



def classify_trigger(prompt: str, rules: Dict[str, List[str]]) -> bool:
    p = prompt.lower()
    pos = rules["positive"]
    neg = rules["negative"]
    for kw in pos:
        if kw.lower() in p:
            # 估值类提示词且仅命中宽泛词时仍视为负面
            if any(n.lower() in p for n in neg) and kw in ("管理层",):
                continue
            return True
    # 结构性触发句
    if re.search(r"看看.*管理层", p) or re.search(r"评估.*管理层", p) or re.search(r"尽调.*管理层", p):
        return True
    if re.search(r"管理层.{0,6}(怎么样|靠不靠谱|靠谱吗|评估|尽调|档案|质量|历史|背景|记录)", p):
        return True
    if "全面分析" in p or "拉取财报并全面分析" in p:
        return True
    return False


# ---------------------------------------------------------------- grader


def grade_cases(
    cases: List[EvalCase],
    skill_text: Optional[str] = None,
) -> GraderResult:
    """对 trigger cases 打分。cases 需含 expected_behavior.should_trigger。"""
    r = GraderResult(name="trigger")
    rules = extract_trigger_rules(skill_text or "")
    r.details["rules"] = rules
    tp = fp = tn = fn = 0
    per_case: List[Dict] = []
    for c in cases:
        expected = bool(c.expected_behavior.get("should_trigger", False))
        predicted = classify_trigger(c.prompt, rules)
        if expected and predicted:
            tp += 1
        elif expected and not predicted:
            fn += 1
            r.add_error("P1", "TRIGGER_FALSE_NEGATIVE", f"[{c.id}] 应触发但未触发: {c.prompt}")
        elif not expected and predicted:
            fp += 1
            r.add_error("P2", "TRIGGER_FALSE_POSITIVE", f"[{c.id}] 不应触发但触发了: {c.prompt}")
        else:
            tn += 1
        per_case.append({
            "case_id": c.id, "prompt": c.prompt,
            "expected": expected, "predicted": predicted,
        })
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    r.score = round(accuracy, 4)
    r.metrics = {
        "total": total, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": round(accuracy, 4), "precision": round(precision, 4),
        "recall": round(recall, 4), "fpr": round(fpr, 4), "fnr": round(fnr, 4),
    }
    r.gates["trigger_accuracy"] = accuracy >= CONFIG["gates"]["trigger_accuracy"]["min"]
    r.details["cases"] = per_case
    return r