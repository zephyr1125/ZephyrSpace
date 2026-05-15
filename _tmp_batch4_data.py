#!/usr/bin/env python3
"""批次4数据拉取：中国移动/中国神华/长江电力/中国石油"""
import requests, os, json, gzip
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    resp = requests.post(f"{LX_BASE}/{path}",
                         json={**payload, "token": LX_TOKEN},
                         headers={"Accept-Encoding": "gzip"}, timeout=30)
    try:
        return json.loads(gzip.decompress(resp.content))
    except:
        return resp.json()

def last_trading_day():
    d = date(2026, 5, 15)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()

trade_date = last_trading_day()
print(f"交易日: {trade_date}")

companies = {
    "中国移动": "600941",
    "中国神华": "601088",
    "长江电力": "600900",
    "中国石油": "601857",
}
codes = list(companies.values())

# ---- 1. 估值数据（PE/PB/市值/股息率） ----
print("\n=== 估值数据 ===")
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": trade_date,
    "metricsList": ["pe_ttm", "pb", "mc", "dyr"]
})
for d_item in val_resp.get("data", []):
    code = d_item.get("stockCode")
    name = [k for k,v in companies.items() if v == code][0]
    print(f"{name}({code}): PE={d_item.get('pe_ttm')}, PB={d_item.get('pb')}, MC={d_item.get('mc')}亿, DYR={d_item.get('dyr')}%")

# ---- 2. 历史PE分位 ----
print("\n=== PE历史分位（3年） ===")
pe_hist = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": trade_date,
    "metricsList": ["pe_ttm.y3.cvpos", "pe_ttm.y3.q2v", "pe_ttm.y3.q5v", "pe_ttm.y3.q8v"]
})
for d_item in pe_hist.get("data", []):
    code = d_item.get("stockCode")
    name = [k for k,v in companies.items() if v == code][0]
    print(f"{name}: 3年分位={d_item.get('pe_ttm.y3.cvpos')}, q2v={d_item.get('pe_ttm.y3.q2v')}, q5v={d_item.get('pe_ttm.y3.q5v')}, q8v={d_item.get('pe_ttm.y3.q8v')}")

# ---- 3. 财报数据（年报ROE/营收/净利润） ----
print("\n=== 2024年报数据 ===")
last_annual = "2024-12-31"
fs_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": last_annual,
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t", "a.pr.np.t.yoy"]
})
for d_item in fs_resp.get("data", []):
    code = d_item.get("stockCode")
    name = [k for k,v in companies.items() if v == code][0]
    print(f"{name}: ROE={d_item.get('a.pr.roe.t')}%, 营收={d_item.get('a.ps.toi.t')}亿, 营收YoY={d_item.get('a.ps.toi.t.yoy')}%, 净利润={d_item.get('a.pr.np.t')}亿, 净利YoY={d_item.get('a.pr.np.t.yoy')}%")

# ---- 4. 最新股价 ----
print("\n=== 最新股价 ===")
for name, code in companies.items():
    price_resp = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-05-12",
        "endDate": "2026-05-15",
        "adjustmentType": "0"
    })
    data = price_resp.get("data", [])
    if data:
        latest = data[-1]
        print(f"{name}({code}): 收盘={latest.get('c')}, 日期={latest.get('t', '')[:10]}")
    else:
        print(f"{name}({code}): 无数据")

# ---- 5. 股息历史 ----
print("\n=== 近5年分红历史 ===")
for name, code in companies.items():
    div_resp = lx_post("cn/company/dividend", {
        "stockCode": code,
        "startDate": "2020-01-01",
        "endDate": "2026-05-15"
    })
    divs = div_resp.get("data", [])
    print(f"\n{name}({code}) 分红记录（最近6条）：")
    for item in sorted(divs, key=lambda x: x.get('recordDate',''), reverse=True)[:6]:
        print(f"  {item.get('recordDate','')[:10]} 每股:{item.get('dividend')} 元/股, 分红率:{item.get('dividendProfitRatio')}")

# ---- 6. Q1 2026财报 ----
print("\n=== 2026Q1财报 ===")
fs_q1 = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": "2026-03-31",
    "metricsList": ["a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t", "a.pr.np.t.yoy", "a.pr.roe.t"]
})
for d_item in fs_q1.get("data", []):
    code = d_item.get("stockCode")
    name = [k for k,v in companies.items() if v == code][0]
    print(f"{name}: 营收={d_item.get('a.ps.toi.t')}亿, 营收YoY={d_item.get('a.ps.toi.t.yoy')}%, 净利润={d_item.get('a.pr.np.t')}亿, 净利YoY={d_item.get('a.pr.np.t.yoy')}%, ROE={d_item.get('a.pr.roe.t')}%")

# ---- 7. 现金流数据 ----
print("\n=== 2024年报现金流 ===")
fs_cf = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": last_annual,
    "metricsList": ["a.cfs.ocf.t", "a.pr.np.t"]
})
for d_item in fs_cf.get("data", []):
    code = d_item.get("stockCode")
    name = [k for k,v in companies.items() if v == code][0]
    ocf = d_item.get("a.cfs.ocf.t")
    np = d_item.get("a.pr.np.t")
    ratio = round(ocf/np, 2) if ocf and np else "N/A"
    print(f"{name}: OCF={ocf}亿, 净利润={np}亿, OCF/净利={ratio}")

print("\n=== 完成 ===")
