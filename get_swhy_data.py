import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    resp = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN})
    return resp.json()

code = "000166"
print(f"=== 申万宏源 ({code}) 财务数据获取 ===\n")

# 获取当前市值
print("=" * 50)
print("1. 当前市值（2025-01-17）")
print("=" * 50)
mcap_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": [code],
    "date": "2025-01-17",
    "metricsList": ["mc", "pe_ttm", "pb"]
})

if mcap_resp.get("data"):
    mcap_data = mcap_resp["data"][0]
    print(f"市值: {mcap_data.get('mc')}亿元")
    print(f"PE(TTM): {mcap_data.get('pe_ttm')}")
    print(f"PB: {mcap_data.get('pb')}")
else:
    print("未获取到数据")

# 获取近3年财报数据
print("\n" + "=" * 50)
print("2. 近3年财报数据（毛利率、ROE等）")
print("=" * 50)

years = ["2022-12-31", "2023-12-31", "2024-12-31"]
for year in years:
    fs_resp = lx_post("cn/company/fs/non_financial", {
        "stockCodes": [code],
        "date": year,
        "metricsList": ["a.pr.mgr.t", "a.pr.roe.t", "a.ps.toi.t", "a.ps.ni.t"]
    })
    if fs_resp.get("data"):
        data = fs_resp["data"][0]
        year_str = year.split('-')[0]
        print(f"\n{year_str}年:")
        print(f"  毛利率: {data.get('a.pr.mgr.t')}%")
        print(f"  ROE: {data.get('a.pr.roe.t')}%")
        print(f"  营收: {data.get('a.ps.toi.t')}亿")
        print(f"  净利润: {data.get('a.ps.ni.t')}亿")

print("\n" + "=" * 50)
print("3. 分红数据（历史分红记录）")
print("=" * 50)
# 获取分红记录
div_resp = lx_post("cn/company/dividend/dividend", {
    "stockCode": code,
    "pageNumber": 1,
    "pageSize": 10
})

if div_resp.get("data"):
    print("\n最近分红记录：")
    for div in div_resp["data"][:5]:
        print(f"  {div.get('exDate')}: {div.get('divPerShare')}元/10股")
else:
    print("未获取到分红数据")

print("\n" + "=" * 50)
print("完成数据获取")
print("=" * 50)
