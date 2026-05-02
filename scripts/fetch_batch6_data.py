"""Fetch financial data for Batch 6 PreBuy analysis."""
import requests
import gzip
import json
import os
import sys
import tushare as ts
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
TS_TOKEN = os.getenv("TUSHARE_TOKEN")

def lx_post(path, payload):
    resp = requests.post(
        f"https://open.lixinger.com/api/{path}",
        json={**payload, "token": LX_TOKEN},
        headers={"Accept-Encoding": "gzip"},
        timeout=30
    )
    try:
        return json.loads(gzip.decompress(resp.content))
    except Exception:
        return resp.json()

TRADE_DATE = "2026-04-30"
CODES = ["003016", "002602", "002155", "301553"]
TS_CODES = ["003016.SZ", "002602.SZ", "002155.SZ", "301553.SZ"]
NAMES = ["佐力药业", "世纪华通", "湖南黄金", "德力佳"]

print(f"Trade date: {TRADE_DATE}")
print("=" * 60)

# 1. Candlestick prices
print("\n[1] 股价 (candlestick)")
prices = {}
for code in CODES:
    result = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-04-28",
        "endDate": "2026-04-30",
        "granularity": "1d",
        "adjustmentType": "none",
        "type": "a"
    })
    if result.get("data"):
        last = result["data"][0]  # data is newest-first
        prices[code] = last.get("close", last.get("c"))
        print(f"  {code}: close={prices[code]}, date={last.get('date','')[:10]}")
    else:
        prices[code] = None
        print(f"  {code}: no data - {result.get('message', result.get('error', ''))}")

# 2. Fundamental data (PE/PB/MC + percentiles)
print("\n[2] 基本面数据 (fundamental)")
fund_result = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": CODES,
    "date": TRADE_DATE,
    "metricsList": ["pe_ttm", "pe_ttm.y3.cvpos", "pe_ttm.y3.q2v", "pe_ttm.y3.q5v", "pe_ttm.y3.q8v", "pb", "mc"]
})
fund_dict = {}
if fund_result.get("data"):
    for d in fund_result["data"]:
        fund_dict[d["stockCode"]] = d
        mc_yi = d.get("mc", 0) / 1e8
        print(f"  {d['stockCode']}: PE={d.get('pe_ttm','N/A'):.2f}, PB={d.get('pb','N/A'):.4f}, "
              f"MC={mc_yi:.2f}亿, PE_3y分位={d.get('pe_ttm.y3.cvpos',0)*100:.1f}%, "
              f"P20={d.get('pe_ttm.y3.q2v','N/A'):.2f}, P50={d.get('pe_ttm.y3.q5v','N/A'):.2f}, "
              f"P80={d.get('pe_ttm.y3.q8v','N/A'):.2f}")
else:
    print(f"  Error: {fund_result}")

# 3. Tushare financial indicators
print("\n[3] 财务指标 (tushare fina_indicator)")
pro = ts.pro_api(TS_TOKEN)

for ts_code in TS_CODES:
    print(f"\n  {ts_code}:")
    try:
        df = pro.fina_indicator(
            ts_code=ts_code,
            fields="ts_code,end_date,roe,netprofit_margin,grossprofit_margin,n_income_attr_p,total_revenue",
            limit=8
        )
        annual = df[df["end_date"].str.endswith("1231")].head(3)
        if annual.empty:
            print("    No annual data")
        else:
            for _, row in annual.iterrows():
                print(f"    {row['end_date']}: ROE={row.get('roe','N/A')}, "
                      f"毛利率={row.get('grossprofit_margin','N/A')}, "
                      f"净利率={row.get('netprofit_margin','N/A')}")
    except Exception as e:
        print(f"    Error: {e}")

# 4. OCF / Cashflow
print("\n[4] 现金流 (tushare cashflow)")
for ts_code in TS_CODES:
    print(f"\n  {ts_code}:")
    try:
        df_cf = pro.cashflow(
            ts_code=ts_code,
            fields="ts_code,end_date,n_cashflow_act",
            limit=8
        )
        annual_cf = df_cf[df_cf["end_date"].str.endswith("1231")].head(3)
        df_income = pro.income(
            ts_code=ts_code,
            fields="ts_code,end_date,n_income_attr_p,total_revenue",
            limit=8
        )
        annual_income = df_income[df_income["end_date"].str.endswith("1231")].head(3)
        for _, row in annual_cf.iterrows():
            year = row["end_date"][:4]
            ocf = row["n_cashflow_act"] / 1e8 if row["n_cashflow_act"] else None
            # find matching income row
            inc_rows = annual_income[annual_income["end_date"].str.startswith(year)]
            if not inc_rows.empty:
                net_profit = inc_rows.iloc[0]["n_income_attr_p"] / 1e8 if inc_rows.iloc[0]["n_income_attr_p"] else None
                revenue = inc_rows.iloc[0]["total_revenue"] / 1e8 if inc_rows.iloc[0]["total_revenue"] else None
            else:
                net_profit = None
                revenue = None
            ratio = (ocf / net_profit) if (ocf and net_profit and net_profit != 0) else None
            print(f"    {row['end_date']}: OCF={ocf:.3f}亿, 净利润={net_profit:.3f}亿, 营收={revenue:.3f}亿, "
                  f"OCF/净利={ratio:.2f}" if all([ocf, net_profit, revenue, ratio]) else
                  f"    {row['end_date']}: OCF={ocf}, 净利润={net_profit}, 营收={revenue}")
    except Exception as e:
        print(f"    Error: {e}")

print("\n" + "=" * 60)
print("Data fetch complete.")
