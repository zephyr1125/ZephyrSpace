"""931994 指数整体PreBuy数据获取"""
import requests, os, json
from dotenv import load_dotenv

load_dotenv(r"E:\ObsidianVaults\ZephyrSpace\.env")
TOKEN = os.getenv("LIXINGER_TOKEN")
BASE = "https://open.lixinger.com/api"

def post(path, body):
    body["token"] = TOKEN
    r = requests.post(f"{BASE}/{path}", json=body, timeout=15)
    return r.json()

# 1. PE分位
pe = post("cn/index/fundamental", {
    "stockCodes": ["931994"],
    "date": "2026-04-30",
    "metricsList": ["pe_ttm.mcw", "pe_ttm.y3.mcw.cvpos",
                    "pe_ttm.y3.mcw.q2v", "pe_ttm.y3.mcw.q5v", "pe_ttm.y3.mcw.q8v",
                    "pe_ttm.y5.mcw.cvpos", "pe_ttm.y5.mcw.q5v", "pe_ttm.y5.mcw.q8v",
                    "dyr.mcw"]
})
d = pe["data"][0] if pe.get("data") else {}
print("=== PE分位 ===")
print(f"  当前PE(mcw): {d.get('pe_ttm.mcw', 'N/A'):.2f}x")
print(f"  3年分位: {d.get('pe_ttm.y3.mcw.cvpos', 0)*100:.1f}%")
print(f"  3年P20: {d.get('pe_ttm.y3.mcw.q2v', 0):.2f}x")
print(f"  3年P50: {d.get('pe_ttm.y3.mcw.q5v', 0):.2f}x")
print(f"  3年P80: {d.get('pe_ttm.y3.mcw.q8v', 0):.2f}x")
print(f"  5年分位: {d.get('pe_ttm.y5.mcw.cvpos', 0)*100:.1f}%")
print(f"  5年P50: {d.get('pe_ttm.y5.mcw.q5v', 0):.2f}x")
print(f"  5年P80: {d.get('pe_ttm.y5.mcw.q8v', 0):.2f}x")
print(f"  股息率(mcw): {d.get('dyr.mcw', 0)*100:.2f}%")

# 2. 价格
price = post("cn/index/candlestick", {
    "stockCode": "931994",
    "startDate": "2026-04-28",
    "endDate": "2026-04-30",
    "type": "normal",
    "fields": ["t", "c"]
})
if price.get("data"):
    latest = price["data"][-1]
    close = latest.get("c", "N/A")
    print(f"\n=== 价格 ===")
    print(f"  2026-04-30 收盘: {close}")

# 3. 成分股权重
weights = post("cn/index/constituent-weightings", {
    "stockCode": "931994",
    "startDate": "2026-04-30"
})
if weights.get("data"):
    stocks = sorted(weights["data"], key=lambda x: x.get("weighting", 0), reverse=True)
    cr5 = sum(s.get("weighting", 0) for s in stocks[:5]) * 100
    cr10 = sum(s.get("weighting", 0) for s in stocks[:10]) * 100
    print(f"\n=== 权重 ===")
    print(f"  CR5: {cr5:.1f}%, CR10: {cr10:.1f}%")
    for s in stocks[:10]:
        print(f"  {s.get('stockName','?'):10s} {s.get('stockCode','?')} {s.get('weighting',0)*100:.2f}%")
    top5_codes = [s.get("stockCode") for s in stocks[:5]]
    print(f"\n  前5代码: {top5_codes}")
