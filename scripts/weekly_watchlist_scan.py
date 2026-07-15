"""
周度 Watchlist 公告扫描脚本
============================
从 watchlist JSON 中读取所有标的，拉取最近 N 天的 CNINFO 公告 +
高管变动 + 处罚/诉讼 + 质押/冻结 + 投资评级 + 业绩预告，
输出结构化 JSON 供 AI 分析。

用法:
    python scripts/weekly_watchlist_scan.py              # 最近 7 天
    python scripts/weekly_watchlist_scan.py --days 14    # 最近 14 天
    python scripts/weekly_watchlist_scan.py --tier core,growth  # 仅特定档位

输出: scripts/_weekly_scan/[YYYY-MM-DD].json
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

VAULT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(VAULT_ROOT))

from scripts.cninfo_api import CninfoClient
import requests
import time


# ── 公告重要性分级规则 ──────────────────────────────

CRITICAL_KEYWORDS = [
    "业绩预告", "业绩快报", "处罚", "诉讼", "冻结", "查封",
    "减持", "重大合同", "并购", "重组", "停牌", "退市",
    "审计意见", "非标", "无法表示意见", "立案调查",
    "实际控制人", "控股股东变更", "要约收购",
]

WATCH_KEYWORDS = [
    "增持", "回购", "质押", "解禁", "限售", "解除",
    "投资者关系活动记录表", "评级", "目标价",
    "权益分派", "分红", "股权激励",
    "股东大会", "担保", "经营范围变更",
    "会计师事务所变更",
]

IGNORE_PATTERNS = [
    "董事会决议公告", "监事会决议公告", "独立董事",
    "募集资金", "闲置资金", "现金管理",
    "章程", "制度", "议事规则",
]


# ── 数据拉取 ─────────────────────────────────────────

def load_watchlist(tiers=None):
    """从 watchlist JSON 加载股票列表"""
    if tiers is None:
        tiers = ["core", "growth"]

    companies = []
    tier_files = {
        "core": "data/watchlist_core.json",
        "growth": "data/watchlist_growth.json",
    }

    for tier in tiers:
        path = VAULT_ROOT / tier_files.get(tier, "")
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("entries", []):
            code = entry.get("code", "")
            if code and "." in code:
                scode = code.split(".")[0]  # 600519.SH → 600519
                market = code.split(".")[1].upper()
                companies.append({
                    "name": entry.get("name", ""),
                    "scode": scode,
                    "market": market,
                    "tier": tier,
                    "deep_score": entry.get("deep_score"),
                })
    return companies


def load_portfolio():
    """从 Google Sheet 读取实际持仓（筛掉剩余份额=0 和 ETF/基金）"""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_path = "E:/Work/Python/Finance/api/auth/aoto-finance-198a2c5c89d4.json"
        sheet_id = "1NW0f4SnDmPl-UY-JUpP_WVf8oJllmM3XhXn9dESOjVY"

        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
        service = build('sheets', 'v4', credentials=creds)

        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range='核算!A:O').execute()
        rows = result.get('values', [])
        if not rows:
            return []
        headers = rows[0]
        code_col = headers.index('代码')
        share_col = headers.index('剩余份额')
        name_col = headers.index('名称')

        companies = []
        seen = set()
        for row in rows[1:]:
            if len(row) <= max(code_col, share_col):
                continue
            code = row[code_col].strip() if code_col < len(row) else ''
            shares = row[share_col].strip() if share_col < len(row) else '0'
            name = row[name_col].strip() if name_col < len(row) else ''

            if not code:
                continue
            try:
                if float(shares.replace(',', '')) == 0:
                    continue
            except ValueError:
                pass

            # 只保留 A 股（6位数字代码）
            if not (code.isdigit() and len(code) == 6 and code.startswith(('0', '3', '6'))):
                continue

            if code not in seen:
                seen.add(code)
                companies.append({"name": name, "scode": code, "market": "A", "tier": "portfolio"})

        return companies
    except Exception as e:
        print(f"[ERROR] Google Sheet: {e}")
        return []


def fetch_all(client, companies, days_back):
    """为所有公司拉取各类数据"""
    today = datetime.now()
    start = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    start_yyyymmdd = (today - timedelta(days=days_back)).strftime("%Y%m%d")
    end_yyyymmdd = today.strftime("%Y%m%d")

    results = []

    for i, co in enumerate(companies):
        scode = co["scode"]
        print(f"[{i+1}/{len(companies)}] {co['name']} ({scode})...", end=" ")

        item = {
            "name": co["name"],
            "scode": scode,
            "tier": co["tier"],
            "deep_score": co.get("deep_score"),
            "announcements": [],
            "executive_trades": [],
            "penalties": [],
            "lawsuits": [],
            "pledges": [],
            "forecasts": [],
        }

        try:
            # 1. 公告（查全部，不分 category）
            anns = client.list_announcements(
                scode, category="", start_date=start, end_date=end,
                max_pages=1, page_size=20,
            )
            for _, row in anns.iterrows():
                item["announcements"].append({
                    "date": str(row.get("发布日期", ""))[:10],
                    "title": row.get("标题", ""),
                })
            time.sleep(0.3)

            # 2. 高管持股变动
            et = client.executive_trades(scode, sdate=start_yyyymmdd, edate=end_yyyymmdd, limit=10)
            for _, row in et.iterrows():
                qty = row.get("变动数量(股)", 0) or 0
                if qty != 0:  # 只记录有实际变动的
                    item["executive_trades"].append({
                        "date": str(row.get("公告日期", ""))[:10],
                        "name": row.get("董监高姓名", ""),
                        "position": row.get("董监高职务", ""),
                        "qty": qty,
                        "reason": row.get("持股变动原因", ""),
                    })
            time.sleep(0.2)

            # 3. 处罚
            pen = client.company_penalties(scode, sdate=start_yyyymmdd, edate=end_yyyymmdd, limit=5)
            for _, row in pen.iterrows():
                item["penalties"].append({
                    "date": str(row.get("公告日期", ""))[:10],
                    "type": row.get("处罚类型", ""),
                    "org": row.get("处罚部门", ""),
                    "reason": str(row.get("处罚原因", ""))[:200],
                    "amount": row.get("处罚金额(元)", 0),
                })
            time.sleep(0.2)

            # 4. 业绩预告
            fc = client.performance_forecast(scode, sdate=start_yyyymmdd, edate=end_yyyymmdd, limit=5)
            for _, row in fc.iterrows():
                item["forecasts"].append({
                    "date": str(row.get("公告日期", ""))[:10],
                    "type": row.get("业绩类型", ""),
                    "period": str(row.get("报告年度", ""))[:10],
                    "reason": str(row.get("业绩变化原因", ""))[:200],
                })
            time.sleep(0.2)

            # 5. 质押 (latest only)
            pl = client.share_pledge(scode, latest_only=True)
            for _, row in pl.iterrows():
                item["pledges"].append({
                    "date": str(row.get("公告日期", ""))[:10],
                    "pledgor": row.get("出质人", ""),
                    "pledgee": row.get("质权人", ""),
                    "qty": row.get("质押数量(股)", 0) or 0,
                    "ratio": row.get("占总股本比例(%)", 0) or 0,
                })

            total_items = (
                len(item["announcements"]) + len(item["executive_trades"]) +
                len(item["penalties"]) + len(item["forecasts"])
            )
            print(f"{total_items} items")
            results.append(item)

        except Exception as e:
            err_msg = str(e)
            if "orgId" in err_msg or "未找到" in err_msg:
                print(f"SKIP (非A股)")
            else:
                print(f"ERROR: {e}")
            results.append(item)

    return results


def classify_importance(item):
    """AI 预分类：给每条公告标注重要性级别"""
    for ann in item.get("announcements", []):
        title = ann.get("title", "")
        for kw in CRITICAL_KEYWORDS:
            if kw in title:
                ann["importance"] = "CRITICAL"
                ann["match"] = kw
                break
        else:
            for kw in WATCH_KEYWORDS:
                if kw in title:
                    ann["importance"] = "WATCH"
                    ann["match"] = kw
                    break
            else:
                for pat in IGNORE_PATTERNS:
                    if pat in title:
                        ann["importance"] = "IGNORE"
                        ann["match"] = pat
                        break
                else:
                    ann["importance"] = "UNKNOWN"

    # 标记其他类型的严重性
    for et in item.get("executive_trades", []):
        reason = str(et.get("reason", "") or "")
        # 分红送转导致的持股变动不是真实交易
        if "分红" in reason or "送转" in reason or "红股" in reason:
            et["importance"] = "IGNORE"
            continue
        qty = abs(et.get("qty", 0) or 0)
        if qty > 100000:
            et["importance"] = "CRITICAL"
        elif qty > 10000:
            et["importance"] = "WATCH"
        else:
            et["importance"] = "IGNORE"

    for pen in item.get("penalties", []):
        amount = pen.get("amount", 0) or 0
        if amount > 1000000:
            pen["importance"] = "CRITICAL"
        else:
            pen["importance"] = "WATCH"

    for fc in item.get("forecasts", []):
        tp = fc.get("type", "")
        if "亏" in str(tp) or "降" in str(tp):
            fc["importance"] = "CRITICAL"
        elif "增" in str(tp) or "盈" in str(tp) or "升" in str(tp):
            fc["importance"] = "WATCH"
        else:
            fc["importance"] = "WATCH"

    for pl in item.get("pledges", []):
        ratio = pl.get("ratio", 0) or 0
        if ratio > 10:
            pl["importance"] = "CRITICAL"
        elif ratio > 3:
            pl["importance"] = "WATCH"
        else:
            pl["importance"] = "IGNORE"


def main():
    parser = argparse.ArgumentParser(description="周度Watchlist公告扫描")
    parser.add_argument("--days", type=int, default=7, help="回溯天数(默认7)")
    parser.add_argument("--tier", type=str, default="core,growth", help="档位过滤, 或 portfolio")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    tiers = [t.strip() for t in args.tier.split(",")]

    if "portfolio" in tiers:
        print(f"[SCAN] 加载 Google Sheet 持仓...")
        companies = load_portfolio()
        tiers = ["portfolio"]
    else:
        print(f"[SCAN] 加载 watchlist (tiers: {tiers})...")
        companies = load_watchlist(tiers)
    print(f"[SCAN] {len(companies)} 家公司")

    client = CninfoClient()
    results = fetch_all(client, companies, args.days)

    # 分级
    print("[CLASSIFY] 标注重要性...")
    for item in results:
        classify_importance(item)

    # 统计
    critical_count = sum(
        1 for item in results
        for ann in item.get("announcements", [])
        if ann.get("importance") == "CRITICAL"
    )
    watch_count = sum(
        1 for item in results
        for ann in item.get("announcements", [])
        if ann.get("importance") == "WATCH"
    )
    print(f"[CLASSIFY] CRITICAL={critical_count}, WATCH={watch_count}")

    # 输出
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(args.output_dir) if args.output_dir else (VAULT_ROOT / "scripts" / "_weekly_scan")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{today}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "scan_date": today,
            "days_back": args.days,
            "tiers": tiers,
            "companies_scanned": len(companies),
            "critical_items": critical_count,
            "watch_items": watch_count,
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"[DONE] {output_path}")
    print(f"[INFO] 下一步: 将 {output_path} 交给 AI 分析 → 生成周报")


if __name__ == "__main__":
    main()
