"""批次3数据拉取：东方财富/招商银行/中国平安/中国太保"""
import requests, os, json, gzip
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

def lx_post(path, payload):
    resp = requests.post(
        f"https://open.lixinger.com/api/{path}",
        json={**payload, "token": LX_TOKEN},
        headers={"Accept-Encoding": "gzip"},
        timeout=30
    )
    try:
        return json.loads(gzip.decompress(resp.content))
    except:
        return resp.json()

CODES = {
    "300059": "东方财富",
    "600036": "招商银行",
    "601318": "中国平安",
    "601601": "中国太保",
}
codes = list(CODES.keys())
target_date = "2026-05-15"
annual_date = "2025-12-31"

print("=" * 60)
print("1. 股价（candlestick）")
print("=" * 60)
for code in codes:
    r = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-05-14",
        "endDate": "2026-05-15",
        "adjustmentType": "qfq"
    })
    data = r.get("data", [])
    if data:
        latest = data[-1]
        print(f"{CODES[code]}（{code}）: 收盘价={latest.get('c')}, 日期={latest.get('t','')[:10]}, 成交量={latest.get('v')}")
    else:
        print(f"{CODES[code]}（{code}）: 无数据 - {r}")

print("\n" + "=" * 60)
print("2. 当前估值（fundamental/non_financial）")
print("=" * 60)
r = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": target_date,
    "metricsList": ["pe_ttm", "pb", "mc", "dyr"]
})
for d in r.get("data", []):
    code = d.get("stockCode")
    print(f"{CODES.get(code, code)}（{code}）:")
    print(f"  PE_TTM={d.get('peTtm')}, PB={d.get('pb')}, MC={d.get('mc')}亿, DYR={d.get('dyr')}%")

print("\n" + "=" * 60)
print("3. PE/PB历史分位（fundamental/non_financial，含分位）")
print("=" * 60)
r2 = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": target_date,
    "metricsList": ["pe_ttm", "pb", "pe_ttm.y3.cvpos", "pb.y3.cvpos"]
})
for d in r2.get("data", []):
    code = d.get("stockCode")
    # access nested fields
    pe_ttm = d.get("peTtm")
    pb = d.get("pb")
    # Try nested structure
    metrics = d.get("metrics", {})
    print(f"{CODES.get(code, code)}（{code}）: PE={pe_ttm}, PB={pb}")
    print(f"  Full keys: {list(d.keys())}")

print("\n" + "=" * 60)
print("4. 年报财务数据（fs/non_financial，2025-12-31）")
print("=" * 60)
r3 = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": annual_date,
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "a.pr.roe.t", "y.ps.toi.t.yoy", "y.ps.np.t.yoy"]
})
print("Raw response keys:", list(r3.keys()))
for d in r3.get("data", []):
    code = d.get("stockCode")
    name = CODES.get(code, code)
    # Try to navigate nested data
    try:
        y = d.get("y", {})
        ps = y.get("ps", {})
        toi = ps.get("toi", {}).get("t")
        np_ = ps.get("np", {}).get("t")
        toi_yoy = ps.get("toi", {}).get("t", {})
        
        a = d.get("a", {})
        pr = a.get("pr", {})
        roe = pr.get("roe", {}).get("t")
        
        print(f"{name}（{code}）: 营收={toi}, 净利={np_}, ROE={roe}")
    except Exception as e:
        print(f"{name}（{code}）: 解析出错 - {e}")
        print(f"  Keys: {list(d.keys())}")

print("\n" + "=" * 60)
print("5. 全字段查看（取第一条）")
print("=" * 60)
for d in r3.get("data", [])[:1]:
    print(json.dumps(d, ensure_ascii=False, indent=2)[:3000])

print("\n" + "=" * 60)
print("6. 近60日走势（招商银行/东方财富）")
print("=" * 60)
for code in ["300059", "600036"]:
    r4 = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-03-15",
        "endDate": "2026-05-15",
        "adjustmentType": "qfq"
    })
    data = r4.get("data", [])
    if data:
        prices = [d.get("c", 0) for d in data]
        high60 = max(prices)
        low60 = min(prices)
        latest = prices[-1]
        print(f"{CODES[code]}（{code}）: 最新={latest}, 60日高={high60}, 60日低={low60}")

print("\n完成!")
