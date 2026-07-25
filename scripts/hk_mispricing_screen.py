"""港股质量错杀筛选 —— Tiger API 粗筛 + yfinance 补字段 + 量化排序.

Usage:
    python scripts/hk_mispricing_screen.py                    # 用今天的日期
    python scripts/hk_mispricing_screen.py --date 2026-07-24  # 指定日期
    python scripts/hk_mispricing_screen.py --dry-run          # 只跑 Tiger 粗筛，不补 yfinance

Output:
    data/screens/港股质量错杀初筛_YYYY-MM-DD.csv   # Tiger 粗筛结果
    data/screens/港股质量错杀二筛排序_YYYY-MM-DD.csv # 量化排序结果
"""

from __future__ import annotations

import csv
import math
import os
import sys
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
import yfinance as yf
from tigeropen.common.consts import Market
from tigeropen.common.consts.filter_fields import FinancialField, FinancialPeriod, StockField
from tigeropen.quote.domain.filter import StockFilter
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig

ROOT = Path(__file__).resolve().parents[1]

# ── 港股粗筛参数 ──────────────────────────────────────────
# 港股估值中枢低于美股，市值门槛适当提高以规避小盘流动性风险
MIN_PRICE = 5                # 最低股价 HKD
MIN_MCAP_B = 10              # 最低流通市值 HKD B（≈ USD 1.3B，港股小盘风险更高）
PE_MIN, PE_MAX = 6, 25       # PE TTM 范围（港股中枢 12-14，低于美股 18-20）
MIN_DRAWDOWN_PCT = 15        # 距 52 周高点至少跌这么多

# ── 工具函数 ─────────────────────────────────────────────

def number(value, default=float("nan")):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default

def clamp(value, low, high):
    return max(low, min(high, value))

def linear(value, bad, good):
    if not math.isfinite(value):
        return 35.0
    if good == bad:
        return 50.0
    return 100.0 * clamp((value - bad) / (good - bad), 0.0, 1.0)


# ── 港股代码转换 ─────────────────────────────────────────

def tiger_to_yahoo_hk(symbol: str) -> str:
    """将 Tiger API 返回的港股代码转换为 yfinance 格式.

    Tiger 返回格式示例: '00700', '00001', '00005'
    yfinance 需要格式:   '0700.HK', '0001.HK', '0005.HK'

    规则：提取数字部分 → 转为 4 位零填充 → 加 .HK 后缀。
    """
    if ".HK" in symbol.upper():
        return symbol.upper()
    digits = "".join(c for c in symbol if c.isdigit())
    if not digits:
        return symbol  # 异常情况，原样返回
    return f"{int(digits):04d}.HK"


# ── Tiger API ────────────────────────────────────────────

def _tiger_client():
    load_dotenv(ROOT / ".env")
    config = TigerOpenClientConfig()
    config.tiger_id = os.environ["TIGER_CLIENT_ID"]
    config.account = os.environ["TIGER_ACCOUNT"]
    config.private_key = os.environ["TIGER_RSA_PRIVATE_KEY"].replace("\\n", "\n")
    return QuoteClient(config)


def tiger_screen():
    """Tiger 选股器粗筛港股：价格 + 市值 + PE，返回候选清单。

    Returns
    -------
    list[dict]  每只股票的基本字段，供后续 yfinance 补全。
    """
    client = _tiger_client()

    # Tiger market_scanner 只返回 filter 字段（非 is_no_filter 的），
    # 财务字段和 52W 高点通过 yfinance 补全。
    filters = [
        StockFilter(StockField.CurPrice, filter_min=MIN_PRICE, is_no_filter=False),
        StockFilter(StockField.FloatMarketVal, filter_min=MIN_MCAP_B * 1_000_000_000, is_no_filter=False),
        StockFilter(StockField.PeTTM, filter_min=PE_MIN, filter_max=PE_MAX, is_no_filter=False),
    ]

    candidates = []
    cursor = None
    pages = 0
    while True:
        pages += 1
        result = client.market_scanner(market=Market.HK, filters=filters, cursor_id=cursor, page_size=200)
        for item in result.items:
            fd = item.field_data
            raw_symbol = item.symbol
            yahoo_symbol = tiger_to_yahoo_hk(raw_symbol)
            candidates.append({
                "代码": raw_symbol,           # Tiger 原始代码 (如 00700)
                "Yahoo代码": yahoo_symbol,    # yfinance 格式 (如 0700.HK)
                "最新价": number(fd.get(StockField.CurPrice)),
                "流通市值_亿港元": round(number(fd.get(StockField.FloatMarketVal)) / 100_000_000, 2),
                "PE_TTM": number(fd.get(StockField.PeTTM)),
                # 以下字段由 yfinance 补全
                "52周高点": "",
                "距52周高点跌幅_%": "",
            })
        cursor = result.cursor_id
        if not cursor:
            break

    print(f"[Tiger 粗筛] 港股市场 → {len(candidates)} 只候选 "
          f"(PE {PE_MIN}-{PE_MAX}, 市值≥HKD {MIN_MCAP_B}B, 价格≥HKD {MIN_PRICE})")
    return candidates


# ── yfinance 补字段 ──────────────────────────────────────

def _series_values(frame, names):
    for name in names:
        if name in frame.index:
            return [number(v) for v in frame.loc[name].tolist() if math.isfinite(number(v))]
    return []


def _cagr(values, years=3):
    if len(values) < 2:
        return float("nan")
    n = min(years, len(values) - 1)
    newest, oldest = values[0], values[n]
    if newest <= 0 or oldest <= 0:
        return float("nan")
    return (newest / oldest) ** (1 / n) - 1


def _fetch_one_yahoo(yahoo_symbol):
    """用 yfinance 拉取一家港股公司的财务报表 + 52W高点 + 行业，计算质量指标。

    参数 yahoo_symbol 应为 yfinance 港股格式，如 '0700.HK'。
    """
    ticker = yf.Ticker(yahoo_symbol)

    # 52 周高点 + 行业
    high52 = float("nan")
    sector = ""
    try:
        info = ticker.info or {}
        high52 = number(info.get("fiftyTwoWeekHigh") or info.get("fiftyTwoWeekHigh"))
        sector = info.get("sector", "")
    except Exception:
        pass

    # 如果 info 没拿到 52W 高点，从历史价格取
    if not math.isfinite(high52):
        try:
            hist = ticker.history(period="1y")
            if not hist.empty and "High" in hist.columns:
                high52 = number(hist["High"].max())
        except Exception:
            pass

    income = ticker.get_income_stmt(freq="yearly")
    cash = ticker.get_cash_flow(freq="yearly")
    balance = ticker.get_balance_sheet(freq="yearly")

    rev = _series_values(income, ["TotalRevenue", "OperatingRevenue"])
    gross = _series_values(income, ["GrossProfit"])
    ni = _series_values(income, ["NetIncome", "NetIncomeCommonStockholders"])
    ebit = _series_values(income, ["EBIT", "OperatingIncome"])
    interest = _series_values(income, ["InterestExpense", "InterestExpenseNonOperating"])
    cfo = _series_values(cash, ["OperatingCashFlow", "TotalCashFromOperatingActivities"])
    fcf_vals = _series_values(cash, ["FreeCashFlow"])
    receivables = _series_values(balance, ["AccountsReceivable", "NetReceivables"])
    inventory = _series_values(balance, ["Inventory"])
    assets = _series_values(balance, ["TotalAssets"])
    equity = _series_values(balance, ["StockholdersEquity", "CommonStockEquity"])
    debt = _series_values(balance, ["TotalDebt"])
    current_assets = _series_values(balance, ["CurrentAssets", "TotalCurrentAssets"])
    current_liabilities = _series_values(balance, ["CurrentLiabilities", "TotalCurrentLiabilities"])
    shares = _series_values(balance, ["OrdinarySharesNumber", "ShareIssued"])

    rev0 = rev[0] if rev else float("nan")
    ni0 = ni[0] if ni else float("nan")
    cfo0 = cfo[0] if cfo else float("nan")
    gross0 = gross[0] if gross else float("nan")
    assets0 = assets[0] if assets else float("nan")
    equity0 = equity[0] if equity else float("nan")
    fcf0 = fcf_vals[0] if fcf_vals else float("nan")

    return {
        "行业": sector,
        "52周高点": high52 if math.isfinite(high52) else "",
        "营收5年CAGR_%": round(100 * _cagr(rev, 5), 2) if rev else "",
        "净利润5年CAGR_%": round(100 * _cagr(ni, 5), 2) if ni else "",
        "营收3年CAGR_%": round(100 * _cagr(rev, 3), 2) if rev else "",
        "净利润3年CAGR_%": round(100 * _cagr(ni, 3), 2) if ni else "",
        "经营现金流3年CAGR_%": round(100 * _cagr(cfo, 3), 2) if cfo else "",
        "应收账款3年CAGR_%": round(100 * _cagr(receivables, 3), 2) if receivables else "",
        "库存3年CAGR_%": round(100 * _cagr(inventory, 3), 2) if inventory else "",
        "毛利率_%": round(100 * gross0 / rev0, 2) if rev0 and gross0 else "",
        "净利率_%": round(100 * ni0 / rev0, 2) if rev0 and ni0 else "",
        "ROE_%": round(100 * ni0 / equity0, 2) if ni0 and equity0 else "",
        "ROA_%": round(100 * ni0 / ((assets0 + (assets[1] if len(assets) > 1 else assets0)) / 2), 2) if ni0 and assets else "",
        "资产负债率_%": round(100 * debt[0] / assets0, 2) if debt and assets0 else "",
        "长期债务权益比": round(debt[0] / equity0, 4) if debt and equity0 and equity0 else "",
        "利息保障倍数": round(abs(ebit[0] / interest[0]), 2) if ebit and interest and interest[0] else "",
        "流动比率": round(current_assets[0] / current_liabilities[0], 2) if current_assets and current_liabilities and current_liabilities[0] else "",
        "总资产周转率": round(rev0 / ((assets0 + (assets[1] if len(assets) > 1 else assets0)) / 2), 4) if rev and assets else "",
        "FCF净利润转化率": round(fcf0 / ni0, 4) if fcf0 and ni0 else "",
        "股数3年CAGR_%": round(100 * _cagr(shares, 3), 2) if shares else "",
        "经营现金流_原始值": cfo0 if math.isfinite(cfo0) else "",
    }


def yahoo_supplement(candidates, max_workers=5):
    """批量为 Tiger 候选补全 yfinance 财务字段。"""
    # 用 Yahoo代码（如 0700.HK）请求 yfinance
    yahoo_map = {c["Yahoo代码"]: c for c in candidates}
    results = {}
    done = 0
    symbols = list(yahoo_map.keys())
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_one_yahoo, s): s for s in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                results[sym] = future.result()
            except Exception as exc:
                print(f"  ⚠ {sym}: {exc}")
            done += 1
            if done % 20 == 0:
                print(f"  … yfinance {done}/{len(symbols)}")
    print(f"[yfinance] 完成 {len(results)}/{len(symbols)} 家")
    return results


# ── 量化评分 ─────────────────────────────────────────────

def score_row(row, extra):
    """四维评分：增长 + 现金流质量 + 资本质量 + 估值折价 - 异常惩罚。

    港股版调整：估值折价锚点从美股 18x 下调至港股中枢 14x。
    """
    rev5 = number(row.get("营收5年CAGR_%", ""))
    ni5 = number(row.get("净利润5年CAGR_%", ""))
    roe = number(row.get("ROE_%", ""))
    debt_assets = number(row.get("资产负债率_%", ""))
    pe = number(row.get("PE_TTM", ""))
    drawdown = number(row.get("距52周高点跌幅_%", ""))

    rev3 = number(extra.get("营收3年CAGR_%", ""))
    ni3 = number(extra.get("净利润3年CAGR_%", ""))
    cfo3 = number(extra.get("经营现金流3年CAGR_%", ""))
    ar3 = number(extra.get("应收账款3年CAGR_%", ""))
    inv3 = number(extra.get("库存3年CAGR_%", ""))
    gross = number(extra.get("毛利率_%", ""))
    net_margin = number(extra.get("净利率_%", ""))
    roa = number(extra.get("ROA_%", ""))
    debt_equity = number(extra.get("长期债务权益比", ""))
    interest = number(extra.get("利息保障倍数", ""))
    fcf_conv = number(extra.get("FCF净利润转化率", ""))
    share_cagr = number(extra.get("股数3年CAGR_%", ""))

    consistency = 100 - min(abs((rev5 or 0) - (rev3 or 0)) * 4, 100) if math.isfinite(rev3) else 35
    profit_consistency = 100 - min(abs((ni5 or 0) - (ni3 or 0)) * 2.5, 100) if math.isfinite(ni3) else 35

    growth = (
        0.35 * linear(rev5, 3, 15)
        + 0.25 * linear(rev3, 2, 14)
        + 0.20 * consistency
        + 0.20 * profit_consistency
    )

    ar_gap = (rev3 - ar3) if math.isfinite(ar3) else float("nan")
    inv_gap = (rev3 - inv3) if math.isfinite(inv3) else float("nan")

    cash_quality = (
        0.25 * linear(cfo3, 0, 15)
        + 0.15 * linear(fcf_conv, 0.5, 1.2)
        + 0.20 * linear(ar_gap, -8, 4)
        + 0.10 * linear(inv_gap, -10, 5)
        + 0.20 * linear(net_margin, 5, 20)
        + 0.10 * linear(gross, 20, 60)
    )

    capital_quality = (
        0.35 * linear(roa, 4, 14)
        + 0.20 * linear(65 - (debt_assets or 65), 0, 45)
        + 0.20 * linear(interest, 2, 12)
        + 0.15 * linear(roe, 10, 25)
        + 0.10 * linear(1.5 - (debt_equity or 1.5), 0, 1.5)
    )

    # 港股估值中枢 14x（美股为 18x）
    PE_CENTER = 14
    valuation = 0.55 * (100 - abs((pe or PE_CENTER) - PE_CENTER) / 10 * 100) + 0.45 * linear(drawdown, 15, 40)
    valuation = clamp(valuation, 0, 100)

    penalty = 0.0
    flags = []
    qrev = number(row.get("最新季度营收同比_%", ""))
    qni = number(row.get("最新季度净利润同比_%", ""))
    if qrev > 60 or qni > 80:
        penalty += 12; flags.append("季度增速异常")
    if (ni5 or 0) - (rev5 or 0) > 20:
        penalty += 7; flags.append("利润增长显著快于营收")
    if (roe or 0) > 40:
        penalty += 6; flags.append("ROE>40%")
    if math.isfinite(ar_gap) and ar_gap < -8:
        penalty += 8; flags.append("应收增速>营收")
    if math.isfinite(cfo3) and cfo3 < 0:
        penalty += 10; flags.append("经营现金流3Y为负")
    if math.isfinite(fcf_conv) and fcf_conv < 0.7:
        penalty += 8; flags.append("FCF/NI<70%")
    if math.isfinite(share_cagr) and share_cagr > 2:
        penalty += 6; flags.append("股数膨胀>2%")
    if not extra:
        penalty += 10; flags.append("yfinance缺数据")

    total = round(clamp(0.30 * growth + 0.30 * cash_quality + 0.25 * capital_quality + 0.15 * valuation - penalty, 0, 100), 1)
    tier = "A-优先三件套" if total >= 72 and penalty < 12 else "B-保留观察" if total >= 58 else "C-暂缓"

    return total, tier, penalty, "；".join(flags) or "无", extra


# ── Watchlist 加载 ───────────────────────────────────────

def _load_watchlist_symbols():
    """从 watchlist JSON 读取已在关注列表中的港股代码（去 .HK 后缀）。"""
    import json
    symbols = set()
    for filename in ("watchlist_core.json", "watchlist_growth.json"):
        path = ROOT / "data" / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for entry in data.get("entries", []):
                code = entry.get("code", "")
                if code.endswith(".HK"):
                    # "00700.HK" → "00700"
                    symbols.add(code[:-3])
                elif code.endswith(".US"):
                    continue  # 美股不参与港股筛选
                else:
                    symbols.add(code)
        except Exception as exc:
            print(f"  ⚠ 读取 {filename} 失败: {exc}")
    return symbols


# ── 主流程 ───────────────────────────────────────────────

def main():
    parser = ArgumentParser(description="港股质量错杀筛选")
    parser.add_argument("--date", default=date.today().isoformat(), help="筛选日期 (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="只跑 Tiger 粗筛，不补 yfinance")
    parser.add_argument("--skip-watchlist", action="store_true", help="排除已在 watchlist 中的港股标的")
    args = parser.parse_args()

    # 加载 watchlist 已有港股标的
    watched = _load_watchlist_symbols() if args.skip_watchlist else set()
    if watched:
        print(f"[Watchlist] 已加载 {len(watched)} 只港股在关注标的，将自动排除")

    screen_date = args.date
    out_dir = ROOT / "data" / "screens"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Tiger 粗筛 ──
    print("=" * 60)
    print(f" 港股质量错杀筛选 — {screen_date}")
    print("=" * 60)
    candidates = tiger_screen()
    if not candidates:
        print("❌ Tiger 粗筛无结果，终止。")
        return

    # ── Step 2: yfinance 补字段 ──
    if not args.dry_run:
        supplements = yahoo_supplement(candidates)
        # 补全 52W 高点 + 跌幅，并过滤跌幅不足的候选
        for c in candidates:
            yahoo_sym = c.get("Yahoo代码", "")
            extra = supplements.get(yahoo_sym, {})
            high52 = number(extra.get("52周高点", ""))
            cur_price = number(c["最新价"])
            if high52 and cur_price and high52 > 0:
                drawdown = round((1 - cur_price / high52) * 100, 2)
            else:
                drawdown = None
            c["52周高点"] = high52 if math.isfinite(high52) else ""
            c["距52周高点跌幅_%"] = drawdown if drawdown is not None else ""
        # 过滤：跌幅 < MIN_DRAWDOWN_PCT 的去掉
        before = len(candidates)
        candidates = [c for c in candidates
                      if c["距52周高点跌幅_%"] == "" or number(c["距52周高点跌幅_%"]) >= MIN_DRAWDOWN_PCT]
        print(f"[跌幅过滤] ≥{MIN_DRAWDOWN_PCT}%: {before} → {len(candidates)} 只")
        # 标记已在 watchlist 的标的
        for c in candidates:
            c["已在Watchlist"] = "是" if c["代码"] in watched else "否"
        if args.skip_watchlist:
            before_wl = len(candidates)
            candidates = [c for c in candidates if c["已在Watchlist"] != "是"]
            print(f"[Watchlist排除] {before_wl} → {len(candidates)} 只")
    else:
        supplements = {}
        print("[dry-run] 跳过 yfinance 补字段")

    if not candidates:
        print("❌ 无候选通过跌幅过滤，终止。")
        return

    # ── 合并初筛 CSV ──
    step1_path = out_dir / f"港股质量错杀初筛_{screen_date}.csv"
    fieldnames = [
        "代码", "Yahoo代码", "行业", "最新价", "流通市值_亿港元", "PE_TTM",
        "距52周高点跌幅_%", "52周高点",
        "营收5年CAGR_%", "净利润5年CAGR_%",
        "最新季度营收同比_%", "最新季度净利润同比_%",
        "营业利润占比_%", "ROE_%", "资产负债率_%", "经营现金流_原始值",
        "数据日期", "待核验项", "已在Watchlist",
    ]
    with open(step1_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for c in candidates:
            yahoo_sym = c.get("Yahoo代码", "")
            extra = supplements.get(yahoo_sym, {})
            c["行业"] = extra.get("行业", "")
            c["数据日期"] = screen_date
            c["待核验项"] = ("毛利率≥25%；自由现金流最近一年为正；行业归类与普通股身份；"
                           "利润质量及每股增长；红筹/H股/香港本地属性确认；老千股风险排查")
            # 合并 yfinance 字段
            for k in ("营收5年CAGR_%", "净利润5年CAGR_%", "ROE_%", "资产负债率_%", "经营现金流_原始值",
                      "最新季度营收同比_%", "最新季度净利润同比_%", "营业利润占比_%",
                      "毛利率_%", "净利率_%", "利息保障倍数", "股数3年CAGR_%", "FCF净利润转化率"):
                if c.get(k) in (None, ""):
                    c[k] = extra.get(k, "")
            # 确保 52 周高点和跌幅已填入
            if c.get("52周高点") in (None, ""):
                c["52周高点"] = extra.get("52周高点", "")
            if c.get("距52周高点跌幅_%") in (None, ""):
                high52 = number(extra.get("52周高点", ""))
                cur = number(c["最新价"])
                if high52 and cur and high52 > 0:
                    c["距52周高点跌幅_%"] = round((1 - cur / high52) * 100, 2)
            w.writerow(c)
    print(f"[初筛 CSV] {step1_path} ({len(candidates)} 只)")

    if args.dry_run:
        return

    # ── Step 3: 量化排序 ──
    scored = []
    for c in candidates:
        yahoo_sym = c.get("Yahoo代码", "")
        total, tier, penalty, flags, detail = score_row(c, supplements.get(yahoo_sym, {}))
        scored.append({
            "二筛排名": 0,
            "代码": c["代码"],
            "Yahoo代码": c.get("Yahoo代码", ""),
            "行业": c.get("行业", ""),
            "二筛总分": total,
            "优先级": tier,
            "异常惩罚": penalty,
            "PE_TTM": c["PE_TTM"],
            "距52周高点跌幅_%": c["距52周高点跌幅_%"],
            "营收5年CAGR_%": c.get("营收5年CAGR_%", ""),
            "净利润5年CAGR_%": c.get("净利润5年CAGR_%", ""),
            "已在Watchlist": c.get("已在Watchlist", "否"),
            "量化警示": flags,
            **{k: (round(v, 2) if isinstance(v, float) and math.isfinite(v) else v)
               for k, v in detail.items()},
        })

    scored.sort(key=lambda x: x["二筛总分"], reverse=True)
    for i, item in enumerate(scored, 1):
        item["二筛排名"] = i

    step2_path = out_dir / f"港股质量错杀二筛排序_{screen_date}.csv"
    with open(step2_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=scored[0].keys())
        w.writeheader()
        w.writerows(scored)
    print(f"[二筛 CSV] {step2_path} ({len(scored)} 只)")

    # ── 终端摘要 ──
    tiers = {"A-优先三件套": [], "B-保留观察": [], "C-暂缓": []}
    for s in scored:
        tiers[s["优先级"]].append(s)
    print(f"\n[评级分布] A={len(tiers['A-优先三件套'])} B={len(tiers['B-保留观察'])} C={len(tiers['C-暂缓'])}")
    print("\n[A档 - 优先三件套]:")
    for s in tiers["A-优先三件套"]:
        print(f"  {s['二筛排名']:2d}. {s['代码']:<6s} {s['二筛总分']:5.1f}分  "
              f"PE={s['PE_TTM']} 跌幅={s['距52周高点跌幅_%']}%  {s['量化警示']}")
    if tiers["B-保留观察"]:
        print(f"\n[B档前10 - 保留观察]:")
        for s in tiers["B-保留观察"][:10]:
            print(f"  {s['二筛排名']:2d}. {s['代码']:<6s} {s['二筛总分']:5.1f}分  "
                  f"PE={s['PE_TTM']} 跌幅={s['距52周高点跌幅_%']}%")


if __name__ == "__main__":
    main()
