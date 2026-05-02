"""Fetch financial data for Batch 6 PreBuy analysis - corrected codes."""
import requests
import gzip
import json
import os
import tushare as ts
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
TS_TOKEN = os.getenv("TUSHARE_TOKEN")
pro = ts.pro_api(TS_TOKEN)

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
# NOTE: User provided wrong codes - corrected here
# 003016.SZ = 欣贺股份 (not 佐力药业); 佐力药业 = 300181.SZ
# 301553.SZ = doesn't exist; 德力佳 = 603092.SH
LX_CODES = ["300181", "002602", "002155", "603092"]
TS_CODES = ["300181.SZ", "002602.SZ", "002155.SZ", "603092.SH"]
NAMES = ["佐力药业", "世纪华通", "湖南黄金", "德力佳"]
LAST_ANNUAL = "2024-12-31"

print("=" * 60)
print("BATCH 6 DATA FETCH - CORRECTED CODES")
print("=" * 60)

# 1. Prices
print("\n[1] PRICES")
prices = {}
for code in LX_CODES:
    r = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-04-28",
        "endDate": "2026-04-30",
        "granularity": "1d",
        "adjustmentType": "none",
        "type": "a"
    })
    if r.get("data"):
        d = r["data"][0]
        prices[code] = d.get("close")
        print(f"  {code}: close={prices[code]}, date={d.get('date','')[:10]}")
    else:
        prices[code] = None
        print(f"  {code}: no data - {r.get('message', r.get('error', ''))}")

# 2. Fundamental PE/PB/MC
print("\n[2] FUNDAMENTAL (PE/PB/MC/Percentiles)")
r2 = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": LX_CODES,
    "date": TRADE_DATE,
    "metricsList": ["pe_ttm", "pe_ttm.y3.cvpos", "pe_ttm.y3.q2v", "pe_ttm.y3.q5v", "pe_ttm.y3.q8v", "pb", "mc"]
})
fund_dict = {}
if r2.get("data"):
    for d in r2["data"]:
        fund_dict[d["stockCode"]] = d
        mc_yi = d.get("mc", 0) / 1e8
        pe_pct = d.get("pe_ttm.y3.cvpos", 0) * 100
        print(f"  {d['stockCode']}: PE={d.get('pe_ttm', 0):.2f}x, PB={d.get('pb', 0):.3f}x, "
              f"MC={mc_yi:.2f}亿, PE3y分位={pe_pct:.1f}%, "
              f"P20={d.get('pe_ttm.y3.q2v', 0):.2f}, P50={d.get('pe_ttm.y3.q5v', 0):.2f}, "
              f"P80={d.get('pe_ttm.y3.q8v', 0):.2f}")
else:
    print(f"  Error: {r2}")

# 3. Tushare financial indicators (multi-year)
print("\n[3] TUSHARE FINA_INDICATOR (ROE/margins, 3 annual)")
fina_data = {}
for ts_code in TS_CODES:
    print(f"\n  {ts_code}:")
    try:
        df = pro.fina_indicator(
            ts_code=ts_code,
            fields="ts_code,end_date,roe,netprofit_margin,grossprofit_margin",
            limit=20
        )
        annual = df[df["end_date"].str.endswith("1231")].head(4)
        fina_data[ts_code] = annual
        if annual.empty:
            print("    No annual data")
        else:
            for _, row in annual.iterrows():
                print(f"    {row['end_date']}: ROE={row.get('roe', 'N/A')}, "
                      f"毛利率={row.get('grossprofit_margin', 'N/A')}, "
                      f"净利率={row.get('netprofit_margin', 'N/A')}")
    except Exception as e:
        print(f"    Error: {e}")

# 4. Income + Cashflow
print("\n[4] INCOME + CASHFLOW (3 annual)")
for ts_code in TS_CODES:
    print(f"\n  {ts_code}:")
    try:
        df_cf = pro.cashflow(
            ts_code=ts_code,
            fields="ts_code,end_date,n_cashflow_act",
            limit=20
        )
        annual_cf = df_cf[df_cf["end_date"].str.endswith("1231")].head(3)

        df_income = pro.income(
            ts_code=ts_code,
            fields="ts_code,end_date,n_income_attr_p,total_revenue",
            limit=20
        )
        annual_income = df_income[df_income["end_date"].str.endswith("1231")].head(3)

        for _, row in annual_cf.iterrows():
            year = row["end_date"][:4]
            ocf_val = row.get("n_cashflow_act")
            ocf = ocf_val / 1e8 if ocf_val else None
            inc_rows = annual_income[annual_income["end_date"].str.startswith(year)]
            if not inc_rows.empty:
                np_val = inc_rows.iloc[0].get("n_income_attr_p")
                rev_val = inc_rows.iloc[0].get("total_revenue")
                net_profit = np_val / 1e8 if np_val else None
                revenue = rev_val / 1e8 if rev_val else None
            else:
                net_profit = None
                revenue = None
            if ocf is not None and net_profit is not None and net_profit != 0:
                ratio = ocf / net_profit
                print(f"    {row['end_date']}: OCF={ocf:.3f}亿, 净利润={net_profit:.3f}亿, "
                      f"营收={revenue:.3f}亿 OCF/净利={ratio:.2f}")
            else:
                print(f"    {row['end_date']}: OCF={ocf}, 净利润={net_profit}, 营收={revenue}")
    except Exception as e:
        print(f"    Error: {e}")

print("\n" + "=" * 60)
print("DATA FETCH COMPLETE")
