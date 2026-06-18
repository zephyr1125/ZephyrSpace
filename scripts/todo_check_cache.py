"""检查某公司是否可复用近 7 天内的深度分析 + 管理层档案

规则：
- 深度分析文件：`深度分析/<公司名>*.md`
- 管理层档案文件：`管理层档案/<公司名>*.md`
- 复用条件（全部满足）：
    1. 两类档案都存在
    2. 两份档案的"档案日期"都在 7 天内
       档案日期 = 文件名中的 YYYY-MM-DD（若有），否则 fallback 到文件 mtime
    3. 财报目录 `财报/<公司名>/` 不存在；或所有文件 mtime 都不晚于深度分析档案日期
- 分数提取：先从文件名 (`... 深度分析 75 2026-...md`)；否则从内容 grep
    深度分析内容：`评分总分: NN` 或 `**总分** | **100** | **NN**`
    管理层档案内容：`**管理层综合评分** | **NN / 100**` 或 `**总分** | **100** | **NN**`

用法：
    python scripts/todo_check_cache.py "宝丰能源"

输出 JSON 一行：
    {"reusable": true, "deep_score": 75, "mgmt_score": 82, ...}
或：
    {"reusable": false, "reason": "..."}
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

VAULT = Path(__file__).parent.parent
DEEP_DIR = VAULT / "深度分析"
MGMT_DIR = VAULT / "管理层档案"
REPORT_DIR = VAULT / "财报"

DATE_RX = re.compile(r"(\d{4}-\d{2}-\d{2})")
FNAME_SCORE_RX = re.compile(r"\s(\d{2,3})\s+\d{4}-\d{2}-\d{2}\.md$")

DEEP_CONTENT_RX = [
    re.compile(r"评分总分[:：]\s*(\d{2,3})"),
    re.compile(r"\*\*总分\*\*\s*\|\s*\*\*100\*\*\s*\|\s*\*\*(\d{2,3})\*\*"),
]
MGMT_CONTENT_RX = [
    re.compile(r"\*\*管理层综合评分\*\*\s*\|\s*\*\*(\d{2,3})\s*/\s*100\*\*"),
    re.compile(r"\*\*总分\*\*\s*\|\s*\*\*100\*\*\s*\|\s*\*\*(\d{2,3})\*\*"),
]


def _file_date(path: Path) -> date:
    m = DATE_RX.search(path.name)
    if m:
        return date.fromisoformat(m.group(1))
    return date.fromtimestamp(path.stat().st_mtime)


def _extract_score(path: Path, content_patterns) -> Optional[int]:
    m = FNAME_SCORE_RX.search(path.name)
    if m:
        return int(m.group(1))
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    for rx in content_patterns:
        m = rx.search(text)
        if m:
            return int(m.group(1))
    return None


def _find_latest(dirpath: Path, company: str, keyword: str):
    """找含公司名且文件名含 keyword（如「深度分析」）的最新文件
    返回 (date, path) 或 None
    """
    if not dirpath.is_dir():
        return None
    best = None
    for f in dirpath.iterdir():
        if not f.is_file() or f.suffix != ".md":
            continue
        if company not in f.name or keyword not in f.name:
            continue
        d = _file_date(f)
        if best is None or d > best[0]:
            best = (d, f)
    return best


def _has_new_report_since(company: str, since: date) -> bool:
    company_dir = REPORT_DIR / company
    if not company_dir.is_dir():
        return False
    cutoff = since + timedelta(days=1)
    for f in company_dir.rglob("*"):
        if not f.is_file():
            continue
        if date.fromtimestamp(f.stat().st_mtime) >= cutoff:
            return True
    return False


def check(company: str) -> dict:
    today = date.today()
    deep = _find_latest(DEEP_DIR, company, "深度分析")
    mgmt = _find_latest(MGMT_DIR, company, "管理层档案")
    if not deep:
        return {"reusable": False, "reason": "缺少深度分析"}
    if not mgmt:
        return {"reusable": False, "reason": "缺少管理层档案"}

    deep_age = (today - deep[0]).days
    mgmt_age = (today - mgmt[0]).days
    if deep_age > 7:
        return {"reusable": False, "reason": f"深度分析过期（{deep[0]}，{deep_age}天前）"}
    if mgmt_age > 7:
        return {"reusable": False, "reason": f"管理层档案过期（{mgmt[0]}，{mgmt_age}天前）"}
    if _has_new_report_since(company, deep[0]):
        return {"reusable": False, "reason": "深度分析后有新财报落地"}

    deep_score = _extract_score(deep[1], DEEP_CONTENT_RX)
    mgmt_score = _extract_score(mgmt[1], MGMT_CONTENT_RX)
    if deep_score is None:
        return {"reusable": False, "reason": f"无法从深度分析提取分数: {deep[1].name}"}
    if mgmt_score is None:
        return {"reusable": False, "reason": f"无法从管理层档案提取分数: {mgmt[1].name}"}

    return {
        "reusable": True,
        "deep_score": deep_score,
        "mgmt_score": mgmt_score,
        "deep_date": deep[0].isoformat(),
        "mgmt_date": mgmt[0].isoformat(),
        "deep_file": str(deep[1].relative_to(VAULT)),
        "mgmt_file": str(mgmt[1].relative_to(VAULT)),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    print(json.dumps(check(sys.argv[1].strip()), ensure_ascii=False))
