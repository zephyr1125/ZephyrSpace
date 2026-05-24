"""
深度分析数据采集脚本（CNINFO 主力 + 理杏仁补充）
=================================================
在深度公司分析执行前运行，一次性拉取所有结构化数据，
减少分析过程中的 API 等待时间。

用法:
    python scripts/collect_deep_data.py 600519 贵州茅台
    python scripts/collect_deep_data.py 600276 恒瑞医药 --years 2019-2025

输出:
    scripts/deep_data/[股票代码]/financials.csv       # 多年财务数据
    scripts/deep_data/[股票代码]/ttm.csv              # TTM指标
    scripts/deep_data/[股票代码]/ratings.csv          # 投资评级
    scripts/deep_data/[股票代码]/dividends.csv        # 分红历史
    scripts/deep_data/[股票代码]/shareholders.csv     # 股东户数
    scripts/deep_data/[股票代码]/share_changes.csv    # 股本变动
    scripts/deep_data/[股票代码]/industry_pe.csv      # 行业PE（全市场）
    scripts/deep_data/[股票代码]/industry_class.csv   # 行业分类
    scripts/deep_data/[股票代码]/ipo.csv              # IPO概况
    scripts/deep_data/[股票代码]/profile.json         # 公司概况
    scripts/deep_data/[股票代码]/research_reports.csv # 研报摘要
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add vault root to path
VAULT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(VAULT_ROOT))

from scripts.cninfo_api import CninfoClient
import pandas as pd


def collect_all(scode: str, years: list[int] = None, output_dir: str = None):
    """拉取深度分析所需全部 CNINFO 数据并保存为 CSV/JSON"""

    if years is None:
        years = [2020, 2021, 2022, 2023, 2024]

    if output_dir is None:
        output_dir = VAULT_ROOT / "scripts" / "deep_data" / scode
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = CninfoClient()
    results = {}

    print(f"=== 采集 {scode} 深度分析数据 ===\n")

    # 1. 公司概况
    print("[1/11] 公司概况...")
    profile = client.company_profile(scode)
    with open(output_dir / "profile.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    rec = profile.get("records", [{}])[0] if profile.get("records") else {}
    print(f"       {rec.get('ORGNAME','?')} | 上市:{rec.get('F006D','?')} | {rec.get('F032V','?')}")

    # 2. 多年财务数据
    print("[2/11] 多年财务数据...")
    df = client.financial_multi_year(scode, years=years)
    df.to_csv(output_dir / "financials.csv", index=False, encoding="utf-8-sig")
    results["financials"] = df
    print(f"       {len(df)} 行 × {len(df.columns)} 列")

    # 3. TTM 指标
    print("[3/11] TTM 指标...")
    ttm = client.ttm_indicators(scode)
    ttm.to_csv(output_dir / "ttm.csv", index=False, encoding="utf-8-sig")
    results["ttm"] = ttm
    print(f"       {len(ttm)} 行")

    # 4. 单季利润表
    print("[4/13] 单季利润表...")
    qi = client.quarterly_income(scode, limit=8)
    qi.to_csv(output_dir / "quarterly_income.csv", index=False, encoding="utf-8-sig")
    results["quarterly_income"] = qi
    print(f"       {len(qi)} 季度")

    # 5. 单季现金流量表
    print("[5/13] 单季现金流量表...")
    qc = client.quarterly_cashflow(scode, limit=8)
    qc.to_csv(output_dir / "quarterly_cashflow.csv", index=False, encoding="utf-8-sig")
    results["quarterly_cashflow"] = qc
    print(f"       {len(qc)} 季度")

    # 6. 投资评级
    print("[6/13] 投资评级...")
    ratings = client.investment_ratings(scode, limit=30)
    ratings.to_csv(output_dir / "ratings.csv", index=False, encoding="utf-8-sig")
    results["ratings"] = ratings
    summary = ""
    if len(ratings) > 0:
        buys = ratings[ratings["投资评级"].str.contains("买入|增持|推荐", na=False)] if "投资评级" in ratings.columns else pd.DataFrame()
        summary = f"共{len(ratings)}条, 正面{len(buys)}条"
    print(f"       {summary}")

    # 7. 研报摘要
    print("[7/13] 研报摘要...")
    reports = client.research_reports(limit=30)
    # 本地过滤
    if "SECCODE" in reports.columns:
        reports = reports[reports["SECCODE"] == scode]
    reports.to_csv(output_dir / "research_reports.csv", index=False, encoding="utf-8-sig")
    results["reports"] = reports
    print(f"       {len(reports)} 条 (过滤后)")

    # 8. 行业 PE
    print("[8/13] 行业PE...")
    pe = client.industry_pe()
    pe.to_csv(output_dir / "industry_pe.csv", index=False, encoding="utf-8-sig")
    results["industry_pe"] = pe
    print(f"       {len(pe)} 个行业")

    # 9. 分红数据
    print("[9/13] 分红数据...")
    div = client.dividends(scode)
    div.to_csv(output_dir / "dividends.csv", index=False, encoding="utf-8-sig")
    results["dividends"] = div
    print(f"       {len(div)} 条")

    # 10. 股东户数
    print("[10/13] 股东户数...")
    holders = client.shareholder_structure(scode)
    holders.to_csv(output_dir / "shareholders.csv", index=False, encoding="utf-8-sig")
    results["shareholders"] = holders
    print(f"       {len(holders)} 条")

    # 11. 股本变动
    print("[11/13] 股本变动...")
    changes = client.share_changes(scode)
    changes.to_csv(output_dir / "share_changes.csv", index=False, encoding="utf-8-sig")
    results["share_changes"] = changes
    print(f"       {len(changes)} 条")

    # 12. 行业分类
    print("[12/13] 行业分类...")
    ic = client.industry_classification(scode)
    ic.to_csv(output_dir / "industry_class.csv", index=False, encoding="utf-8-sig")
    results["industry_class"] = ic
    print(f"       {len(ic)} 条分类标准")

    # 13. IPO 概况
    print("[13/13] IPO 概况...")
    ipo = client.ipo_summary(scode)
    ipo.to_csv(output_dir / "ipo.csv", index=False, encoding="utf-8-sig")
    results["ipo"] = ipo
    print(f"       {len(ipo)} 条")

    # ── 汇总 ──
    print(f"\n=== 采集完成 ===")
    print(f"输出目录: {output_dir}")
    total_rows = sum(len(v) for v in results.values() if hasattr(v, '__len__'))
    print(f"总计: {total_rows} 行数据")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="深度分析数据采集")
    parser.add_argument("scode", help="股票代码, 如 600519")
    parser.add_argument("--years", default="2020-2025", help="年份范围, 如 2020-2025")
    parser.add_argument("--output", default=None, help="输出目录")
    args = parser.parse_args()

    year_start, year_end = map(int, args.years.split("-"))
    years = list(range(year_start, year_end + 1))

    collect_all(args.scode, years=years, output_dir=args.output)
