"""
财报PDF自动下载脚本 — 从巨潮资讯(CNINFO)自动下载年报/半年报/季报。

逻辑:
  年报:   回溯 5-7 年 (D2兑现率追踪 / F2资本配置跨周期 / E5会计政策逐年查)
  半年报: 回溯 2-3 年
  季报:   仅当最新已发布报告是 Q1/Q3 时下载（即中报/年报数据尚未发布时补位）

用法:
  python scripts/download_reports.py 600519           # 单只股票
  python scripts/download_reports.py 600519 600276   # 多只
  python scripts/download_reports.py --all-watchlist # watchlist 中全部标的
  python scripts/download_reports.py 600519 --dry-run # 仅列出，不下载

输出: 财报/_Inbox/[证券简称]_[年份]_[报告类型].pdf
"""

import sys
import re
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta

VAULT_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = VAULT_ROOT / "财报" / "_Inbox"

CATEGORY_MAP = {
    "年报": "category_ndbg_szsh",
    "半年报": "category_bndbg_szsh",
    "一季报": "category_yjdbg_szsh",
    "三季报": "category_sjdbg_szsh",
}

# orgId 缓存 & 名称→代码映射
_stock_org_ids = None
_name_to_code = None

def _load_stock_data():
    """加载股票列表，构建 orgId 映射和名称→代码反查"""
    global _stock_org_ids, _name_to_code
    if _stock_org_ids is None:
        r = requests.get("http://www.cninfo.com.cn/new/data/szse_stock.json", timeout=30)
        items = r.json()["stockList"]
        _stock_org_ids = {item["code"]: item["orgId"] for item in items}
        # 名称→代码：用 zwjc(中文简称) 字段，同名取沪市优先
        _name_to_code = {}
        for item in items:
            code = item["code"]
            name = item.get("zwjc", "").strip()
            if name and (name not in _name_to_code or code.startswith("6")):
                _name_to_code[name] = code
    return _stock_org_ids, _name_to_code

def resolve_scode(query):
    """输入股票代码或名称，返回标准化6位代码。返回 None 表示未匹配。"""
    org_ids, name_map = _load_stock_data()
    # 纯数字 → 代码
    if re.match(r'^\d{6}$', query):
        return query if query in org_ids else None
    # 字符串 → 名称查找
    if query in name_map:
        return name_map[query]
    # 模糊匹配（包含关系）
    for name, code in name_map.items():
        if query in name or name in query:
            return code
    return None


def search_announcements(scode, category, start_date, end_date, max_pages=3):
    """查询公告列表，返回 [{title, pdf_url, date, size_kb}, ...]"""
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
                    time.sleep(2 * (attempt + 1))  # 2s, 4s 递增等待
                else:
                    data = {"announcements": []}
        time.sleep(0.5)  # 请求间间隔，避免触发限流
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
    """排除摘要、英文版等非主报告"""
    return not re.search(r"摘要|英文|更正|修订", title)


def determine_reports_to_download(scode):
    """根据规则决定需要下载的报告列表。

    Returns: [(category_name, year, search_start, search_end), ...]
    """
    today = datetime.now()
    current_year = today.year
    to_download = []

    # ── 年报：回溯 5-7 年 ──
    # 最新可获取年报 = current_year - 1（FY2026年报要到2027年3-4月才发布）
    annual_end = current_year - 1
    if today.month <= 4 and today.day < 15:
        annual_end -= 1  # 4月中旬前可能还没发完
    for y in range(annual_end - 6, annual_end + 1):
        to_download.append(("年报", y, f"{y}-01-01", f"{y+1}-06-30"))

    # ── 半年报：回溯 2-3 年 ──
    # 最新可获取半年报 = 上一年（当年半年报通常8月发布）
    semi_end = current_year - 1 if today.month < 8 else current_year
    for y in range(semi_end - 2, semi_end + 1):
        to_download.append(("半年报", y, f"{y}-06-01", f"{y}-10-31"))

    # ── 季报：补位最新报告期之后的数据窗口 ──
    # 年报覆盖到 12/31，半年报覆盖到 6/30
    # 如果最新年报/半年报的报告期距今 > 一个季度，则下载中间的 Q1/Q3
    # 例如：2026年5月，最新年报报告期=2025-12-31（距今~5个月）→ 需要 Q1 2026
    #       2026年11月，最新半年报报告期=2026-06-30（距今~5个月）→ 需要 Q3 2026

    # 确定最新已覆盖的报告期截止日
    latest_annual_year = annual_end  # 最新年报的会计年度
    latest_semi_year = semi_end      # 最新半年报的会计年度

    # Q1: 报告期 3/31, 通常在 4 月发布
    # 如果最新年报截止于上一年 12/31 且现在已过当年 4 月底 → 补 Q1
    q1_year = current_year
    if today.month >= 4 and q1_year > latest_annual_year:
        to_download.append(("一季报", q1_year, f"{q1_year}-03-01", f"{q1_year}-06-30"))

    # Q3: 报告期 9/30, 通常在 10 月发布
    # 如果最新半年报截止于当年 6/30 且现在已过当年 10 月底 → 补 Q3
    q3_year = current_year
    if today.month >= 10 and q3_year > latest_semi_year:
        to_download.append(("三季报", q3_year, f"{q3_year}-09-01", f"{q3_year}-12-31"))

    return to_download


def download_report(pdf_url, save_path):
    """下载单个PDF"""
    r = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    r.raise_for_status()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    Path(save_path).write_bytes(r.content)
    return Path(save_path)


def download_for_stock(query, dry_run=False):
    """为单只股票下载所有应下载的报告。支持代码或名称。"""
    scode = resolve_scode(query)
    if not scode:
        print(f"[ERROR] 未找到匹配的股票: {query}")
        return []
    org_ids, _ = _load_stock_data()
    org_id = org_ids.get(scode)
    if not org_id:
        print(f"[ERROR] 未找到 {scode} 的 orgId")
        return []

    print(f"\n{'='*60}")
    print(f"[{scode}] 分析报告需求...")
    print(f"{'='*60}")

    targets = determine_reports_to_download(scode)
    downloaded = []
    seen_years = set()  # 按 (category, year) 去重

    for category, year, sdate, edate in targets:
        anns = search_announcements(scode, CATEGORY_MAP[category], sdate, edate)
        main = [a for a in anns if is_main_report(a["title"])]

        if main:
            best = main[0]
            title = best["title"]

            # 从标题提取公司简称: "贵州茅台：xxx" 或 "贵州茅台xxx年年度报告"
            sec_name = scode
            if "：" in title:
                sec_name = title.split("：")[0].strip()
            elif ":" in title:
                sec_name = title.split(":")[0].strip()
            else:
                # 尝试从标题提取公司名（覆盖"2019年年度报告"这类老格式）
                # 先查"xxx：2020年"格式
                m = re.match(r'^([^：:\d]+)[：:]', title)
                if m:
                    sec_name = m.group(1).strip()
                else:
                    # 再查"贵州茅台2020年"格式 (中文名后紧跟4位年份)
                    m = re.match(r'^([一-龥]{2,8})(\d{4})', title)
                    if m:
                        sec_name = m.group(1)

            # 从标题提取实际报告年度（而非搜索范围年度）
            report_year = year
            ym = re.search(r'(\d{4})\s*年', title)
            if ym:
                report_year = int(ym.group(1))

            dedup_key = (category, report_year)
            if dedup_key in seen_years:
                continue
            seen_years.add(dedup_key)

            fname = f"{sec_name}_{report_year}_{category}.pdf"
            fname = re.sub(r'[\\/*?:"<>|]', "_", fname)
            save_path = INBOX_DIR / fname

            if save_path.exists():
                print(f"  [SKIP] {fname} (已存在)")
                continue

            if dry_run:
                print(f"  [DRY-RUN] {fname}  <- {best['date'].strftime('%Y-%m-%d')} ({best['size_kb']}KB)")
            else:
                print(f"  [DOWNLOAD] {fname} ({best['size_kb']}KB)...")
                try:
                    download_report(best["pdf_url"], save_path)
                    downloaded.append(str(save_path))
                    print(f"    -> {save_path}")
                except Exception as e:
                    print(f"    [ERROR] {e}")
        else:
            print(f"  [NOTFOUND] {scode} {year}年{category}")

    return downloaded


def main():
    import argparse
    parser = argparse.ArgumentParser(description="财报PDF自动下载")
    parser.add_argument("scodes", nargs="*", help="股票代码列表")
    parser.add_argument("--dry-run", action="store_true", help="仅列出，不下载")
    parser.add_argument("--years-annual", type=int, default=7, help="年报回溯年数(默认7)")
    parser.add_argument("--years-semi", type=int, default=3, help="半年报回溯年数(默认3)")
    args = parser.parse_args()

    if not args.scodes:
        print("用法: python download_reports.py 600519 贵州茅台 [--dry-run]")
        print("      python download_reports.py 600519 --dry-run  # 预览")
        sys.exit(1)

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    total = 0

    # 解析名称+去重
    resolved = []
    seen = set()
    for query in args.scodes:
        scode = resolve_scode(query)
        if scode and scode not in seen:
            resolved.append(scode)
            seen.add(scode)

    for scode in resolved:
        downloaded = download_for_stock(scode, dry_run=args.dry_run)
        total += len(downloaded)

    if args.dry_run:
        print(f"\n[DONE] 预览完成（--dry-run，未实际下载）")
    else:
        print(f"\n[DONE] 共下载 {total} 份报告 -> {INBOX_DIR}")
        print(f"[INFO] 下一步: python scripts/convert_annual_reports.py")


if __name__ == "__main__":
    main()
