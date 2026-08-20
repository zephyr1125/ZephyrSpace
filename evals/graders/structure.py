
"""Deterministic Structure Eval（Eval Layer 3）。

覆盖：
- 文件名正则
- 行数 >= 150
- 11 章节完整性
- 📊 快速参考卡必须在正文分析之前
- frontmatter 必填字段
- 股票代码格式
- 评分算术（各维度 <= 满分，Σ == 总分）
- 红旗规则（诚信 <=8 或 资本配置 <=10 => 必须出现红旗）
- 评级映射
- 反链（公司页引用管理层档案；深度分析页存在时引用）
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import (
    CONFIG, ArchiveDocument, EvalCase, EvalError, GraderResult, VAULT_ROOT,
    load_archive, parse_sections, rating_for_score,
)

ST = CONFIG["structure"]


def grade(doc: ArchiveDocument, case: EvalCase) -> GraderResult:
    r = GraderResult(name="structure")
    checks: List[Tuple[str, bool, Optional[str]]] = []

    # 9.1 文件名
    fn_ok = bool(re.match(ST["filename_regex"], doc.path.name))
    checks.append(("filename", fn_ok, doc.path.name))

    # 9.2 行数
    min_lines = ST["min_lines"]
    line_ok = doc.line_count >= min_lines
    checks.append(("line_count", line_ok, f"{doc.line_count} < {min_lines}"))

    # 9.3 章节完整性
    found_sections = _match_sections(doc)
    missing = [s for s in ST["sections"] if not any(_section_equivalent(s, k) for k in doc.sections)]
    sec_ok = len(missing) == 0
    checks.append(("sections", sec_ok, "缺失: " + ", ".join(missing)))

    # 9.4 快速参考卡位于正文分析之前
    card_ok, card_loc = _quick_ref_position(doc)
    checks.append(("quick_reference_card", card_ok, card_loc))

    # 9.5 frontmatter
    fm_missing = [f for f in ST["required_frontmatter"] if f not in doc.frontmatter]
    fm_ok = len(fm_missing) == 0
    checks.append(("frontmatter", fm_ok, "缺失: " + ", ".join(fm_missing)))

    # 9.6 股票代码格式
    ticker_ok, ticker_err = _ticker_check(doc.frontmatter.get("股票代码", ""))
    checks.append(("ticker_format", ticker_ok, ticker_err))

    # 9.7 评分算术
    score_ok, score_err = _score_math_check(doc)
    checks.append(("score_math", score_ok, score_err))

    # 9.8 红旗规则
    redflag_ok, redflag_err = _red_flag_check(doc)
    checks.append(("red_flag_rule", redflag_ok, redflag_err))

    # 9.9 评级映射
    rating_ok, rating_err = _rating_check(doc)
    checks.append(("rating_mapping", rating_ok, rating_err))

    # 9.10 反链
    backlink_ok, backlink_err = _backlink_check(doc, case)
    checks.append(("backlink", backlink_ok, backlink_err))

    passed = sum(1 for _, ok, _ in checks if ok)
    r.score = round(passed / len(checks), 4)

    for name, ok, err in checks:
        r.gates[f"structure_{name}"] = ok
        if not ok:
            sev = "P1" if name in ("filename", "sections", "score_math") else "P2"
            r.add_error(sev, "FORMAT_" + name.upper(), f"[structure.{name}] {err}")

    # 硬门槛（plan §18）
    r.gates["required_sections"] = sec_ok
    r.gates["score_math"] = score_ok
    r.gates["minimum_lines"] = line_ok
    r.details["checks"] = {name: ok for name, ok, _ in checks}
    r.details["missing_sections"] = missing
    r.metrics["line_count"] = doc.line_count
    r.metrics["section_count"] = len(found_sections)
    return r


# ---------------------------------------------------------------- helpers

def _section_equivalent(a: str, b: str) -> bool:
    """章节标题关键词等价（模板章节名 + 真实档案变体）。"""
    def norm(s: str) -> str:
        s = re.sub(r"^#{1,6}\s*", "", s).strip()
        s = re.sub(r"^[一二三四五六七八九十]+、", "", s)
        return s.strip()
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    # 模板章节关键词匹配（按数字序号）
    num_a = re.match(r"^([一二三四五六七八九十]+)、", a.strip())
    num_b = re.match(r"^([一二三四五六七八九十]+)、", b.strip())
    if num_a and num_b and num_a.group(1) == num_b.group(1):
        return _keywords_overlap(na, nb)
    return False


SECTION_KEYWORDS = {
    "一": ["画像"],
    "二": ["言行"],
    "三": ["资本配置"],
    "四": ["股东友好"],
    "五": ["危机处理"],
    "六": ["组织与人才", "组织"],
    "七": ["互动", "IR"],
    "八": ["监管"],
    "九": ["评分", "100 分制"],
    "十": ["摘录"],
    "十一": ["综合结论"],
}

def _keywords_overlap(na: str, nb: str) -> bool:
    def norm_core(s: str) -> str:
        return re.sub(r"[（(].*?[)）]|[⭐*\s]", "", s)
    a, b = norm_core(na), norm_core(nb)
    # 共用字符比例（按较短的字符串）
    if not a or not b:
        return False
    shared = sum(1 for ch in set(a) if ch in b)
    return shared / max(len(set(a)), 1) >= 0.5


def _match_sections(doc: ArchiveDocument) -> List[str]:
    found = []
    for key in doc.sections:
        found.append(key)
    return found


def _quick_ref_position(doc: ArchiveDocument) -> Tuple[bool, str]:
    marker = ST["quick_reference_marker"]
    idx = doc.text.find(marker)
    if idx < 0:
        return False, "缺少 📊 快速参考 卡片"
    # 卡片须位于第一个 "## " 章节标题之前（正文分析之前）
    first_section = re.search(r"\n#{1,6}\s*[一二三四五六七八九十]、", doc.text)
    if first_section and idx > first_section.start():
        return False, "快速参考卡出现在正文分析之后"
    return True, "ok"


def _ticker_check(ticker_raw: str) -> Tuple[bool, str]:
    patterns = ST["ticker_patterns"]
    # 支持 "600660.SH / 3606.HK" 多代码（A+H）
    for part in re.split(r"[/、,，;；\s]+", ticker_raw.strip()):
        part = part.strip()
        if not part:
            continue
        if part == "N/A" or part == "-":
            continue
        if not any(re.match(p, part) for p in patterns):
            return False, f"股票代码 {part!r} 不符合格式 (SH/SZ/HK/US)"
    return True, "ok"


def _score_math_check(doc: ArchiveDocument) -> Tuple[bool, str]:
    if not doc.scores:
        return False, "无法从评分表提取维度分数"
    for dim, score in doc.scores.items():
        maxv = doc.max_scores.get(dim)
        if maxv is not None and score > maxv:
            return False, f"{dim} {score} > 满分 {maxv}"
    if doc.total_score is not None:
        s = sum(doc.scores.values())
        if s != doc.total_score:
            return False, f"维度合计 {s} != 总分 {doc.total_score}"
    else:
        return False, "评分表缺少总分行"
    return True, "ok"


def _red_flag_check(doc: ArchiveDocument) -> Tuple[bool, str]:
    thresholds = ST["red_flag_thresholds"]  # {dim: 触发阈值}
    triggered = [
        dim for dim, thr in thresholds.items()
        if doc.scores.get(dim) is not None and doc.scores[dim] <= thr
    ]
    if not triggered:
        return True, "ok"
    text = doc.text
    has_flag = bool(re.search(r"红旗|警告|扣分项|减分项", text))
    if not has_flag:
        return False, f"维度 {triggered} 触发红旗阈值但正文无红旗/警告标注"
    return True, "ok"


def _rating_check(doc: ArchiveDocument) -> Tuple[bool, str]:
    if doc.total_score is None:
        return False, "无总分，无法校验评级"
    expected = rating_for_score(doc.total_score)
    # 查找评级声明（含星星或名称）
    m = re.search(r"(⭐{1,5}|卓越|优秀|良好|一般|不达标)", doc.text)
    if not m:
        return False, "缺少评级声明"
    declared = m.group(1)
    if declared in ("卓越", "优秀", "良好", "一般", "不达标"):
        ok = declared == expected
    else:
        ok = len(declared) == len("⭐" * _stars_for(expected))
    return ok, f"总分 {doc.total_score} => 应为 {expected}，声明为 {declared}"


def _stars_for(rating: str) -> int:
    return {"卓越": 5, "优秀": 4, "良好": 3, "一般": 2, "不达标": 1}.get(rating, 1)


def _backlink_check(doc: ArchiveDocument, case: Optional[EvalCase]) -> Tuple[bool, str]:
    name = (case.company.get("name") if case else None) or doc.path.stem.split(" ")[0]
    company_page = VAULT_ROOT / "01-公司" / f"{name}.md"
    errors: List[str] = []
    if company_page.exists():
        content = company_page.read_text(encoding="utf-8")
        # 公司页应引用本档案（按文件名或 管理层档案/ 路径）
        fn = doc.path.name
        if fn not in content and "管理层档案" not in content:
            errors.append(f"公司页 01-公司/{name}.md 未引用管理层档案")
    else:
        errors.append(f"公司页 01-公司/{name}.md 不存在")
    # 深度分析页存在时检查引用
    deep_dir = VAULT_ROOT / "深度分析"
    if deep_dir.exists():
        deep_pages = list(deep_dir.glob(f"{name}*.md"))
        if deep_pages:
            linked = any(fn in p.read_text(encoding="utf-8") for p in deep_pages)
            if not linked:
                errors.append(f"深度分析页 {deep_pages[0].name} 未引用本管理层档案")
    return (len(errors) == 0), "; ".join(errors) if errors else "ok"