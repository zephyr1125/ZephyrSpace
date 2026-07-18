"""对 Tiger 初筛结果进行第二阶段质量可信度排序。"""

from __future__ import annotations

import csv
import math
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
import yfinance as yf
from tigeropen.common.consts import Market
from tigeropen.common.consts.filter_fields import FinancialField, FinancialPeriod, StockField
from tigeropen.quote.domain.filter import StockFilter
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "screens" / "美股质量错杀初筛_2026-07-17.csv"
OUTPUT = ROOT / "data" / "screens" / "美股质量错杀二筛排序_2026-07-17.csv"
EXCLUDED = {"CPRT", "FDS", "NFLX", "PTC", "ULTA"}
ALREADY_REVIEWED = {"ADBE", "META", "MSFT"}


def number(value, default=float("nan")):
    """将 API/CSV 值安全转换为浮点数。"""
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def linear(value, bad, good):
    """把指标线性映射到 0—100，并限制极端值。"""
    if not math.isfinite(value):
        return 35.0
    if good == bad:
        return 50.0
    return 100.0 * clamp((value - bad) / (good - bad), 0.0, 1.0)


def build_client():
    load_dotenv(ROOT / ".env")
    config = TigerOpenClientConfig()
    config.tiger_id = os.environ["TIGER_CLIENT_ID"]
    config.account = os.environ["TIGER_ACCOUNT"]
    config.private_key = os.environ["TIGER_RSA_PRIVATE_KEY"].replace("\\n", "\n")
    return QuoteClient(config)


def fetch_supplement_tiger(symbols):
    """尝试利用 Tiger 选股器补齐字段；实测部分账户可能不返回财务字段。"""
    client = build_client()
    fields = [
        StockFilter(StockField.CurPrice, filter_min=5, is_no_filter=False),
        StockFilter(StockField.FloatMarketVal, filter_min=2_000_000_000, is_no_filter=False),
        StockFilter(StockField.PeTTM, filter_min=8, filter_max=30, is_no_filter=False),
        *[
            StockFilter(field, is_no_filter=True, financial_period=FinancialPeriod.LTM)
            for field in (
                FinancialField.GrossProfitRate,
                FinancialField.NetProfitRate,
                FinancialField.ROATTM,
                FinancialField.TotalRevenues3YrCagr,
                FinancialField.NetIncome3YrCagr,
                FinancialField.CashFromOps3YrCagr,
                FinancialField.AccountsReceivable3YrCagr,
                FinancialField.Inventory3YrCagr,
                FinancialField.LongTermDebtToEquity,
                FinancialField.EbitToInterestExp,
                FinancialField.CurrentRatio,
                FinancialField.TotalAssetTurnover,
            )
        ],
    ]
    wanted = set(symbols)
    found = {}
    cursor = None
    while True:
        result = client.market_scanner(
            market=Market.US,
            filters=fields,
            cursor_id=cursor,
            page_size=200,
        )
        for item in result.items:
            if item.symbol in wanted:
                found[item.symbol] = {
                    field.field.name: number(item[field]) for field in fields[3:]
                }
        cursor = result.cursor_id
        if not cursor or wanted.issubset(found):
            break
    return found


def series_value(frame, names):
    for name in names:
        if name in frame.index:
            values = [number(value) for value in frame.loc[name].tolist()]
            return [value for value in values if math.isfinite(value)]
    return []


def cagr(values, years=3):
    if len(values) < 2:
        return float("nan")
    intervals = min(years, len(values) - 1)
    newest, oldest = values[0], values[intervals]
    if newest <= 0 or oldest <= 0:
        return float("nan")
    return (newest / oldest) ** (1 / intervals) - 1


def fetch_one_yahoo(symbol):
    """从公开报表聚合数据构造可复算的财务质量指标。"""
    ticker = yf.Ticker(symbol)
    income = ticker.get_income_stmt(freq="yearly")
    cash = ticker.get_cash_flow(freq="yearly")
    balance = ticker.get_balance_sheet(freq="yearly")
    revenue = series_value(income, ["TotalRevenue", "OperatingRevenue"])
    gross = series_value(income, ["GrossProfit"])
    net_income = series_value(income, ["NetIncome", "NetIncomeCommonStockholders"])
    ebit = series_value(income, ["EBIT", "OperatingIncome"])
    interest = series_value(income, ["InterestExpense", "InterestExpenseNonOperating"])
    cfo = series_value(cash, ["OperatingCashFlow", "TotalCashFromOperatingActivities"])
    fcf = series_value(cash, ["FreeCashFlow"])
    receivables = series_value(balance, ["AccountsReceivable", "NetReceivables"])
    inventory = series_value(balance, ["Inventory"])
    assets = series_value(balance, ["TotalAssets"])
    equity = series_value(balance, ["StockholdersEquity", "CommonStockEquity"])
    debt = series_value(balance, ["TotalDebt"])
    current_assets = series_value(balance, ["CurrentAssets", "TotalCurrentAssets"])
    current_liabilities = series_value(balance, ["CurrentLiabilities", "TotalCurrentLiabilities"])
    shares = series_value(balance, ["OrdinarySharesNumber", "ShareIssued"])
    result = {
        "TotalRevenues3YrCagr": cagr(revenue),
        "NetIncome3YrCagr": cagr(net_income),
        "CashFromOps3YrCagr": cagr(cfo),
        "AccountsReceivable3YrCagr": cagr(receivables),
        "Inventory3YrCagr": cagr(inventory),
        "GrossProfitRate": gross[0] / revenue[0] if gross and revenue and revenue[0] else float("nan"),
        "NetProfitRate": net_income[0] / revenue[0] if net_income and revenue and revenue[0] else float("nan"),
        "ROATTM": net_income[0] / ((assets[0] + assets[1]) / 2) if net_income and len(assets) > 1 else float("nan"),
        "LongTermDebtToEquity": debt[0] / equity[0] if debt and equity and equity[0] else float("nan"),
        "EbitToInterestExp": abs(ebit[0] / interest[0]) if ebit and interest and interest[0] else float("nan"),
        "CurrentRatio": current_assets[0] / current_liabilities[0] if current_assets and current_liabilities and current_liabilities[0] else float("nan"),
        "TotalAssetTurnover": revenue[0] / ((assets[0] + assets[1]) / 2) if revenue and len(assets) > 1 else float("nan"),
        "FcfToNetIncome": fcf[0] / net_income[0] if fcf and net_income and net_income[0] else float("nan"),
        "ShareCount3YrCagr": cagr(shares),
    }
    return symbol, result


def fetch_supplement(symbols):
    """并发获取报表指标；单家公司失败不阻断整批二筛。"""
    found = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_one_yahoo, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                key, value = future.result()
                found[key] = value
            except Exception as exc:
                print(f"WARN {symbol}: {exc}")
    return found


def score(row, extra):
    rev5 = number(row["营收5年CAGR_%"])
    ni5 = number(row["净利润5年CAGR_%"])
    qrev = number(row["最新季度营收同比_%"])
    qni = number(row["最新季度净利润同比_%"])
    roe = number(row["ROE_%"])
    debt_assets = number(row["资产负债率_%"])
    pe = number(row["PE_TTM"])
    drawdown = number(row["距52周高点跌幅_%"])

    rev3 = 100 * extra.get("TotalRevenues3YrCagr", float("nan"))
    ni3 = 100 * extra.get("NetIncome3YrCagr", float("nan"))
    cfo3 = 100 * extra.get("CashFromOps3YrCagr", float("nan"))
    ar3 = 100 * extra.get("AccountsReceivable3YrCagr", float("nan"))
    inv3 = 100 * extra.get("Inventory3YrCagr", float("nan"))
    gross = 100 * extra.get("GrossProfitRate", float("nan"))
    net_margin = 100 * extra.get("NetProfitRate", float("nan"))
    roa = 100 * extra.get("ROATTM", float("nan"))
    debt_equity = extra.get("LongTermDebtToEquity", float("nan"))
    interest = extra.get("EbitToInterestExp", float("nan"))
    fcf_conversion = extra.get("FcfToNetIncome", float("nan"))
    share_cagr = 100 * extra.get("ShareCount3YrCagr", float("nan"))

    consistency = 100 - min(abs(rev5 - rev3) * 4, 100) if math.isfinite(rev3) else 35
    profit_consistency = 100 - min(abs(ni5 - ni3) * 2.5, 100) if math.isfinite(ni3) else 35
    growth = (
        0.35 * linear(rev5, 3, 15)
        + 0.25 * linear(rev3, 2, 14)
        + 0.20 * consistency
        + 0.20 * profit_consistency
    )

    ar_gap = rev3 - ar3 if math.isfinite(ar3) else float("nan")
    inv_gap = rev3 - inv3 if math.isfinite(inv3) else float("nan")
    cash_quality = (
        0.25 * linear(cfo3, 0, 15)
        + 0.15 * linear(fcf_conversion, 0.5, 1.2)
        + 0.20 * linear(ar_gap, -8, 4)
        + 0.10 * linear(inv_gap, -10, 5)
        + 0.20 * linear(net_margin, 5, 20)
        + 0.10 * linear(gross, 20, 60)
    )

    capital_quality = (
        0.35 * linear(roa, 4, 14)
        + 0.20 * linear(65 - debt_assets, 0, 45)
        + 0.20 * linear(interest, 2, 12)
        + 0.15 * linear(roe, 10, 25)
        + 0.10 * linear(1.5 - debt_equity, 0, 1.5)
    )

    valuation = (
        0.55 * (100 - abs(pe - 18) / 12 * 100)
        + 0.45 * linear(drawdown, 15, 40)
    )
    valuation = clamp(valuation, 0, 100)

    penalty = 0.0
    flags = []
    if qrev > 60 or qni > 80:
        penalty += 12
        flags.append("季度增速异常，优先核查并购/处置/低基数")
    if ni5 - rev5 > 20:
        penalty += 7
        flags.append("利润增长显著快于营收")
    if roe > 40:
        penalty += 6
        flags.append("ROE>40%，核查回购/低权益基数")
    if math.isfinite(ar_gap) and ar_gap < -8:
        penalty += 8
        flags.append("应收增速明显快于营收")
    if math.isfinite(cfo3) and cfo3 < 0:
        penalty += 10
        flags.append("经营现金流三年趋势为负")
    if math.isfinite(fcf_conversion) and fcf_conversion < 0.7:
        penalty += 8
        flags.append("FCF/净利润低于70%")
    if math.isfinite(share_cagr) and share_cagr > 2:
        penalty += 6
        flags.append("股数三年CAGR高于2%")
    if not extra:
        penalty += 10
        flags.append("Tiger补充字段缺失")

    total = 0.30 * growth + 0.30 * cash_quality + 0.25 * capital_quality + 0.15 * valuation - penalty
    total = round(clamp(total, 0, 100), 1)
    tier = "A-优先三件套" if total >= 72 and penalty < 12 else "B-保留观察" if total >= 58 else "C-暂缓"
    return total, tier, penalty, "；".join(flags) or "无明显量化异常", {
        "营收3年CAGR_%": rev3,
        "净利润3年CAGR_%": ni3,
        "经营现金流3年CAGR_%": cfo3,
        "应收账款3年CAGR_%": ar3,
        "库存3年CAGR_%": inv3,
        "毛利率_%": gross,
        "净利率_%": net_margin,
        "ROA_%": roa,
        "长期债务权益比": debt_equity,
        "利息保障倍数": interest,
        "FCF净利润转化率": fcf_conversion,
        "股数3年CAGR_%": share_cagr,
        "增长一致性分": round(growth, 1),
        "现金流质量分": round(cash_quality, 1),
        "资本质量分": round(capital_quality, 1),
        "估值折价分": round(valuation, 1),
    }


def main():
    with INPUT.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["代码"] not in EXCLUDED]
    supplements = fetch_supplement([row["代码"] for row in rows])
    output = []
    for row in rows:
        total, tier, penalty, flags, detail = score(row, supplements.get(row["代码"], {}))
        output.append({
            "二筛排名": 0,
            "代码": row["代码"],
            "行业": row["行业"],
            "二筛总分": total,
            "优先级": tier,
            "研究状态": "已有三件套，优先复核" if row["代码"] in ALREADY_REVIEWED else "待新做三件套",
            "异常惩罚": penalty,
            **{key: round(value, 2) if math.isfinite(value) else "" for key, value in detail.items()},
            "PE_TTM": row["PE_TTM"],
            "距52周高点跌幅_%": row["距52周高点跌幅_%"],
            "营收5年CAGR_%": row["营收5年CAGR_%"],
            "净利润5年CAGR_%": row["净利润5年CAGR_%"],
            "量化警示": flags,
        })
    output.sort(key=lambda item: item["二筛总分"], reverse=True)
    for index, item in enumerate(output, 1):
        item["二筛排名"] = index
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output[0].keys())
        writer.writeheader()
        writer.writerows(output)
    print(f"已输出 {len(output)} 家：{OUTPUT}")
    for item in output[:15]:
        print(item["二筛排名"], item["代码"], item["二筛总分"], item["优先级"], item["量化警示"])


if __name__ == "__main__":
    main()
