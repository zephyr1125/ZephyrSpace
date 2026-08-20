
"""Evidence Grounding Eval（Eval Layer 5）。

- Claim Extraction：从综合结论/一致性评估提取主要判断
- Evidence Binding：为每个 claim 找到证据锚（年份/数字/来源词）
- Grounded Claim Rate：score >= 2 的关键 claim 比例（gate >= 0.90）

LLM 模式下：用结构化 judge 对每个 claim 打分（0-3）；
Null 模式下：确定性启发式（claim 自身或所在章节含年份/数字/来源锚即视为 grounded）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import CONFIG, ArchiveDocument, EvalCase, EvalError, GraderResult
from .judge import get_backend

SOURCE_WORDS = ("年报", "电话会", "互动易", "公告", "CNINFO", "理杏仁", "智堡", "来源", "巨潮", "港交所")

CLAIM_CATEGORIES = [
    "资本配置克制", "资本配置", "重视股东回报", "股东回报", "团队稳定性", "团队稳定",
    "稳定性较差", "危机处理", "透明度", "战略连续性", "战略连贯", "言行一致", "兑现",
    "管理层", "接班", "治理", "诚信", "减持", "回购", "分红",
]


def extract_claims(doc: ArchiveDocument) -> List[Dict[str, str]]:
    """提取主要判断（综合结论 + 一致性评估）。"""
    claims: List[Dict[str, str]] = []
    # 十一、综合结论
    conclusion = ""
    for key, body in doc.sections.items():
        if key.startswith("十一、") or "综合结论" in key:
            conclusion = body
            break
    if conclusion:
        for line in conclusion.splitlines():
            line = line.strip()
            if line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.", "6.")):
                cleaned = line.lstrip("-* 0123456789.").strip()
                if 6 <= len(cleaned) <= 120:
                    claims.append({"claim": cleaned, "section": "conclusion"})
        m = re.search(r">\s*([^>\n]{6,})", conclusion)
        if m:
            claims.append({"claim": m.group(1).strip(), "section": "conclusion"})
    # 二、言行一致性 一致性评估
    for key, body in doc.sections.items():
        if key.startswith("二、") or "言行" in key:
            for line in body.splitlines():
                line = line.strip()
                if "：" in line and 6 <= len(line) <= 120 and "|" not in line:
                    claims.append({"claim": line, "section": "consistency"})
    # 过滤：只保留与 CLAIM_CATEGORIES 相关的主要判断
    filtered = [c for c in claims if any(k in c["claim"] for k in CLAIM_CATEGORIES)]
    return filtered or claims[:8]


def _has_evidence_anchor(claim: str, section_text: str) -> bool:
    ctx = claim + " " + section_text[:4000]
    has_year = bool(re.search(r"(?:19|20)\d{2}", ctx))
    has_num = bool(re.search(r"\d+(?:\.\d+)?\s*(?:亿|万|元|%|倍)", ctx))
    has_source = any(w in ctx for w in SOURCE_WORDS)
    return has_year or (has_num and has_source)


def grade(doc: ArchiveDocument, case: EvalCase) -> GraderResult:
    r = GraderResult(name="grounding")
    claims = extract_claims(doc)
    if not claims:
        r.score = None
        r.details["skipped_reason"] = "未提取到关键 claim"
        return r

    backend = get_backend()
    r.details["judge_backend"] = backend.name
    grounded = 0
    per_claim: List[Dict[str, Any]] = []
    for c in claims:
        section_text = ""
        if c["section"] == "conclusion":
            for key, body in doc.sections.items():
                if key.startswith("十一、") or "综合结论" in key:
                    section_text = body
                    break
        else:
            for key, body in doc.sections.items():
                if key.startswith("二、") or "言行" in key:
                    section_text = body
                    break
        if backend.name == "llm":
            res = backend.judge("grounding_claim", doc.text)
            bound = res.score >= 2
            detail = {"score": res.score, "reason": res.reason}
        else:
            bound = _has_evidence_anchor(c["claim"], section_text)
            detail = {"score": 3 if bound else 1, "reason": "确定性锚点匹配" if bound else "无年份/数字/来源锚"}
        if bound:
            grounded += 1
        per_claim.append({"claim": c["claim"], "bound": bound, **detail})

    rate = round(grounded / len(claims), 4)
    r.score = rate
    r.metrics["claims_total"] = len(claims)
    r.metrics["claims_grounded"] = grounded
    r.metrics["grounded_claim_rate"] = rate
    r.gates["grounded_claim_rate"] = rate >= CONFIG["gates"]["grounded_claim_rate"]["min"]
    r.details["claims"] = per_claim
    for pc in per_claim:
        if not pc["bound"]:
            r.add_error("P2", "GROUNDING_UNSUPPORTED_CLAIM",
                        f"[{case.id}] 判断缺乏证据绑定：{pc['claim'][:50]}")
    return r
