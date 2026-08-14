"""
财报PDF单文件下载脚本 — 从巨潮资讯(CNINFO)下载指定报告。

用法:
  python scripts/download_reports.py 603259 2026H1    # 药明康德 2026半年报
  python scripts/download_reports.py 600519 2025      # 贵州茅台 2025年报
  python scripts/download_reports.py 300750 2026Q1    # 宁德时代 2026一季报
  python scripts/download_reports.py 603259 2026H1 --dry-run  # 仅预览，不下载

报告类型:
  2026H1 → 半年报    2025   → 年报
  2026Q1 → 一季报    2026Q3 → 三季报

输出: 财报/_Inbox/[证券简称]_[年份]_[报告类型].pdf
"""

import sys
import re
import time
import requests
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = VAULT_ROOT / "财报" / "_Inbox"

CATEGORY_MAP = {
    "年报": "category_ndbg_szsh",
    "半年报": "category_bndbg_szsh",
    "一季报": "category_yjdbg_szsh",
    "三季报": "category_sjdbg_szsh",
}

REPORT_TYPE_MAP = {
    "H1": "半年报",
    "Q1": "一季报",
    "Q3": "三季报",
}

_stock_org_ids = None
_name_to_code = None


def _load_stock_data():
    global _stock_org_ids, _name_to_code
    if _stock_org_ids is None:
        r = requests.get("http://www.cninfo.com.cn/new/data/szse_stock.json", timeout=30)
        items = r.json()["stockList"]
        _stock_org_ids = {item["code"]: item["orgId"] for item in items}
        _name_to_code = {}
        for item in items:
            code = item["code"]
            name = item.get("zwjc", "").strip()
            if name and (name not in _name_to_code or code.startswith("6")):
                _name_to_code[name] = code
    return _stock_org_ids, _name_to_code


def resolve_scode(query):
    org_ids, name_map = _load_stock_data()
    if re.match(r'^\d{6}$', query):
        return query if query in org_ids else None
    if query in name_map:
        return name_map[query]
    for name, code in name_map.items():
        if query in name or name in query:
            return code
    return None


def parse_report_spec(spec):
    """解析报告规格。返回 (category, year, search_start, search_end) 或 None。"""
    # 纯年份 → 年报
    m = re.match(r'^(\d{4})$', spec)
    if m:
        year = int(m.group(1))
        return ("年报", year, f"{year}-01-01", f"{year+1}-06-30")

    # 年份+类型 → 半年报/季报
    m = re.match(r'^(\d{4})(H1|Q1|Q3)$', spec)
    if m:
        year = int(m.group(1))
        suffix = m.group(2)
        category = REPORT_TYPE_MAP[suffix]
        if suffix == "H1":
            return (category, year, f"{year}-06-01", f"{year}-10-31")
        elif suffix == "Q1":
            return (category, year, f"{year}-03-01", f"{year}-06-30")
        elif suffix == "Q3":
            return (category, year, f"{year}-09-01", f"{year}-12-31")

    return None


def search_announcements(scode, category, start_date, end_date, max_pages=3):
    org_ids, _ = _load_stock_data()
    org_id = org_ids.get(scode)
    if not org_id:
        print(f"  [WARN] 未找到 {scode} 的 orgId，跳过")
        return []

    results = []
    for page in range(1, max_pages + 1):
        for attempt in range(3):
            r = requests.post(
                "http://www.cninfo.com.cn/new/hisAnnouncement/query",
                data={
                    "pageNum": str(page), "pageSize": "30",
                    "column": "szse", "tabName": "fulltext",
                    "plate": "", "stock": f"{scode},{org_id}",
                    "searchkey": "", "secid": "", "category": category,
                    "trade": "",
                    "seDate": f"{start_date}~{end_date}",
                    "sortName": "", "sortType": "", "isHLtitle": "true",
                },
                headers={"Accept": "application/json", "Referer": "http://www.cninfo.com.cn/"},
                timeout=30,
            )
            try:
                data = r.json()
                break
            except Exception:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                else:
                    data = {"announcements": []}
        time.sleep(0.5)
        anns = data.get("announcements") or []
        if not anns:
            break
        for a in anns:
            results.append({
                "title": a.get("announcementTitle", ""),
                "pdf_url": f"https://static.cninfo.com.cn/{a.get('adjunctUrl', '')}",
                "date": datetime.fromtimestamp(a.get("announcementTime", 0) / 1000),
                "size_kb": a.get("adjunctSize", 0),
            })
    return results


def is_main_report(title):
    return not re.search(r"摘要|英文|更正|修订", title)


def download_report(pdf_url, save_path):
    r = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    r.raise_for_status()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    Path(save_path).write_bytes(r.content)
    return Path(save_path)


def download_single_report(query, report_spec, dry_run=False):
    """下载单份报告。返回下载路径或 None。"""
    scode = resolve_scode(query)
    if not scode:
        print(f"[ERROR] 未找到匹配的股票: {query}")
        return None

    parsed = parse_report_spec(report_spec)
    if not parsed:
        print(f"[ERROR] 报告格式错误: {report_spec}，应为 2026H1 / 2025 / 2026Q1 / 2026Q3")
        return None

    category, year, sdate, edate = parsed
    print(f"  目标: {scode} {year}年{category}")

    anns = search_announcements(scode, CATEGORY_MAP[category], sdate, edate)
    main = [a for a in anns if is_main_report(a["title"])]

    if not main:
        print(f"  [NOTFOUND] 未找到 {scode} {year}年{category}")
        return None

    best = main[0]
    title = best["title"]

    # 提取公司简称
    sec_name = scode
    if "：" in title:
        sec_name = title.split("：")[0].strip()
    elif ":" in title:
        sec_name = title.split(":")[0].strip()
    else:
        m = re.match(r'^([^：:\d]+)[：:]', title)
        if m:
            sec_name = m.group(1).strip()
        else:
            m = re.match(r'^([一-龥]{2,8})(\d{4})', title)
            if m:
                sec_name = m.group(1)

    # 从标题提取实际报告年度
    report_year = year
    ym = re.search(r'(\d{4})\s*年', title)
    if ym:
        report_year = int(ym.group(1))

    fname = f"{sec_name}_{report_year}_{category}.pdf"
    fname = re.sub(r'[\\/*?:"<>|]', "_", fname)
    save_path = INBOX_DIR / fname

    if save_path.exists():
        print(f"  [SKIP] {fname} (已存在)")
        return str(save_path)

    if dry_run:
        print(f"  [DRY-RUN] {fname}  <- {best['date'].strftime('%Y-%m-%d')} ({best['size_kb']}KB)")
        return None

    print(f"  [DOWNLOAD] {fname} ({best['size_kb']}KB)...")
    try:
        download_report(best["pdf_url"], save_path)
        print(f"    -> {save_path}")
        return str(save_path)
    except Exception as e:
        print(f"    [ERROR] {e}")
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="财报PDF单文件下载")
    parser.add_argument("scode", help="股票代码或名称")
    parser.add_argument("report", help="报告规格，如 2026H1 / 2025 / 2026Q1 / 2026Q3")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不下载")
    args = parser.parse_args()

    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    result = download_single_report(args.scode, args.report, dry_run=args.dry_run)
    if args.dry_run:
        print("\n[DONE] 预览完成（--dry-run，未实际下载）")
    elif result:
        print(f"\n[DONE] 下载完成 -> {result}")
        print(f"[INFO] 下一步: python scripts/convert_annual_reports.py {Path(result).name}")
    else:
        print("\n[DONE] 未下载任何文件")


if __name__ == "__main__":
    main()
