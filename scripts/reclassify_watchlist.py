#!/usr/bin/env python3
"""按三层评分规则重建公司 Watchlist。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
COMPANY_DIR = ROOT / "01-公司"
TODAY = "2026-07-19"

STRATEGIC_META = {
    "长江电力": "DEFENSIVE",
    "Linde": "COMPOUNDER",
    "国电南瑞": "POLICY_INFRA",
    "万事达卡": "COMPOUNDER",
}

# S级使用最近一次完整三件套或深度分析日期，优先于可能滞后的公司页 frontmatter。
FUNDAMENTAL_REVIEW_OVERRIDES = {
    "长江电力": "2026-05-29",
    "Linde": "2026-07-07",
    "国电南瑞": "2026-07-15",
    "万事达卡": "2026-07-07",
}

PAGE_ALIASES = {
    "万事达卡": "万事达卡(MA).md",
    "台积电": "台积电(TSM).md",
    "卡特彼勒(CAT)": "卡特彼勒(CAT).md",
    "Alphabet(Google)": "Alphabet(Google).md",
}


def load_entries() -> list[dict]:
    """读取全部研究等级数据并按股票代码去重，保证脚本可重复执行。"""
    entries: dict[str, dict] = {}
    filenames = (
        "watchlist_strategic.json",
        "watchlist_core.json",
        "watchlist_growth.json",
        "watchlist_out_of_scope.json",
    )
    for filename in filenames:
        path = DATA_DIR / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["entries"]:
            entries[entry["code"]] = entry
    return list(entries.values())


def fundamental_review_date(name: str) -> str | None:
    """从公司页 frontmatter 提取最近一次基本面研究日期。"""
    if name in FUNDAMENTAL_REVIEW_OVERRIDES:
        return FUNDAMENTAL_REVIEW_OVERRIDES[name]
    filename = PAGE_ALIASES.get(name, f"{name}.md")
    path = COMPANY_DIR / filename
    if not path.exists():
        candidates = list(COMPANY_DIR.glob(f"*{name}*.md"))
        path = candidates[0] if len(candidates) == 1 else path
    if not path.exists():
        return None
    head = path.read_text(encoding="utf-8")[:2000]
    match = re.search(r"^(?:最后更新日期|分析日期):\s*[\"']?(\d{4}-\d{2}-\d{2})", head, re.MULTILINE)
    return match.group(1) if match else None


def classify(entry: dict) -> str:
    """按最高满足等级分类；S级质量门槛由最新人工复核名单约束。"""
    c_score = entry.get("cScore")
    m_score = entry.get("mScore")
    if not isinstance(c_score, (int, float)) or not isinstance(m_score, (int, float)):
        return "NONE"
    total = c_score + m_score
    certainty_raw = entry.get("valuation_certainty")
    certainty = (
        round(float(certainty_raw), 4)
        if isinstance(certainty_raw, (int, float)) and not isinstance(certainty_raw, bool)
        else -1
    )
    if (
        entry["name"] in STRATEGIC_META
        and total >= 170
        and c_score >= 82
        and m_score >= 82
        and certainty >= 0.80
    ):
        return "S_STRATEGIC"
    if total >= 160 and c_score >= 76 and m_score >= 76:
        return "A_CORE"
    if total >= 150 and c_score >= 70 and m_score >= 70:
        return "B_GROWTH"
    return "NONE"


def enrich(entry: dict, level: str) -> dict:
    """添加研究分级与跟踪字段，保留现有估值和财报数据。"""
    result = dict(entry)
    result["watchlistLevel"] = level
    result["trackingStatus"] = result.get("trackingStatus", "WATCHING")
    result["strategicCoreType"] = STRATEGIC_META.get(result["name"])
    result["lastFundamentalReviewDate"] = result.get(
        "lastFundamentalReviewDate", fundamental_review_date(result["name"])
    )
    result["lastRedFlagReviewDate"] = result.get("lastRedFlagReviewDate")
    return result


def write_group(filename: str, level: str, entries: list[dict]) -> None:
    """写出单一研究等级文件。"""
    payload = {
        "version": json.loads((DATA_DIR / filename).read_text(encoding="utf-8")).get("version", 1),
        "watchlistLevel": level,
        "updated_at": TODAY,
        "entries": entries,
        "valuation_certainty_scale": "0.00-1.00; measures target-price reliability, not company quality",
        "buy_price_formula": "target_price * (0.68 + 0.14 * valuation_certainty)",
    }
    (DATA_DIR / filename).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def promote_growth_to_core() -> None:
    """仅迁移成长池中满足最新 A 级门槛的条目，避免影响其他层级。"""
    core_path = DATA_DIR / "watchlist_core.json"
    growth_path = DATA_DIR / "watchlist_growth.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))
    growth = json.loads(growth_path.read_text(encoding="utf-8"))

    promoted = []
    retained = []
    for entry in growth["entries"]:
        if classify(entry) == "A_CORE":
            promoted_entry = dict(entry)
            promoted_entry["watchlistLevel"] = "A_CORE"
            promoted_entry["strategicCoreType"] = None
            promoted.append(promoted_entry)
        else:
            retained.append(entry)

    core["entries"].extend(promoted)
    write_group("watchlist_core.json", "A_CORE", core["entries"])
    write_group("watchlist_growth.json", "B_GROWTH", retained)
    names = "、".join(entry["name"] for entry in promoted)
    print(f"成长池升入 A 级：{len(promoted)} 家：{names}")


def promote_none_to_growth() -> None:
    """仅迁移未入池中满足最新 B 级门槛的条目，避免影响其他层级。"""
    growth_path = DATA_DIR / "watchlist_growth.json"
    none_path = DATA_DIR / "watchlist_out_of_scope.json"
    growth = json.loads(growth_path.read_text(encoding="utf-8"))
    none = json.loads(none_path.read_text(encoding="utf-8"))

    promoted = []
    retained = []
    for entry in none["entries"]:
        if classify(entry) == "B_GROWTH":
            promoted_entry = dict(entry)
            promoted_entry["watchlistLevel"] = "B_GROWTH"
            promoted_entry["strategicCoreType"] = None
            promoted.append(promoted_entry)
        else:
            retained.append(entry)

    growth["entries"].extend(promoted)
    write_group("watchlist_growth.json", "B_GROWTH", growth["entries"])
    write_group("watchlist_out_of_scope.json", "NONE", retained)
    names = "、".join(entry["name"] for entry in promoted)
    print(f"NONE 池升入 B 级：{len(promoted)} 家：{names}")


def main() -> None:
    if "--promote-growth-to-core" in sys.argv:
        promote_growth_to_core()
        return
    if "--promote-none-to-growth" in sys.argv:
        promote_none_to_growth()
        return

    groups = {level: [] for level in ("S_STRATEGIC", "A_CORE", "B_GROWTH", "NONE")}
    for raw in load_entries():
        level = classify(raw)
        groups[level].append(enrich(raw, level))

    outputs = {
        "watchlist_strategic.json": "S_STRATEGIC",
        "watchlist_core.json": "A_CORE",
        "watchlist_growth.json": "B_GROWTH",
        "watchlist_out_of_scope.json": "NONE",
    }
    for filename, level in outputs.items():
        write_group(filename, level, groups[level])

    counts = ", ".join(f"{level}={len(groups[level])}" for level in groups)
    print(f"Watchlist 重分类完成：{counts}")


if __name__ == "__main__":
    main()
