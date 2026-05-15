"""批次3数据拉取 v2：修复API参数"""
import requests, os, json, gzip
from dotenv import load_dotenv

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

print("=" * 60)
print("1. 股价（candlestick，type=k_day）")
print("=" * 60)
for code in codes:
    r = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-05-12",
        "endDate": "2026-05-15",
        "type": "k_day",
        "adjustmentType": "qfq"
    })
    data = r.get("data", [])
    if data:
        latest = data[-1]
        print(f"{CODES[code]}（{code}）: 收盘价={latest.get('c')}, 日期={str(latest.get('t',''))[:10]}")
    else:
        print(f"{CODES[code]}（{code}）: 错误 - {r}")

print("\n" + "=" * 60)
print("2. 估值（fundamental/non_financial，含PE/PB分位）")
print("=" * 60)
r2 = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": "2026-05-15",
    "metricsList": ["pe_ttm", "pb", "mc", "dyr", "pe_ttm.y3.cvpos", "pb.y3.cvpos"]
})
for d in r2.get("data", []):
    code = d.get("stockCode")
    mc_yuan = d.get("mc", 0)
    mc_yi = round(mc_yuan / 1e8, 0) if mc_yuan else None
    pe = d.get("pe_ttm")
    pb = d.get("pb")
    dyr_raw = d.get("dyr")
    dyr = round(dyr_raw * 100, 2) if dyr_raw else None
    pe_pos = d.get("pe_ttm.y3.cvpos")
    pb_pos = d.get("pb.y3.cvpos")
    print(f"{CODES.get(code,code)}（{code}）:")
    print(f"  PE={pe}, PB={pb}, MC={mc_yi}亿, DYR={dyr}%, PE3年分位={pe_pos}, PB3年分位={pb_pos}")

print("\n" + "=" * 60)
print("3. 尝试fs/non_financial（先查可用字段）")
print("=" * 60)
# 先查文档
doc_r = lx_post("cn/company/fs/non_financial", {
    "stockCode": "600036",
    "date": "2025-12-31",
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "a.pr.roe.t", "y.ps.toi.t.yoy", "y.ps.np.t.yoy"]
})
print("单只查询:", doc_r.get("code"), doc_r.get("error"))
if doc_r.get("data"):
    print(json.dumps(doc_r["data"][0], ensure_ascii=False, indent=2)[:2000])

print("\n" + "=" * 60)
print("4. 批量fs/non_financial")
print("=" * 60)
r3 = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": "2025-12-31",
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "a.pr.roe.t", "y.ps.toi.t.yoy", "y.ps.np.t.yoy"]
})
print("Code:", r3.get("code"), "Error:", r3.get("error"))
for d in r3.get("data", []):
    code = d.get("stockCode")
    name = CODES.get(code, code)
    y = d.get("y", {})
    ps = y.get("ps", {}) if y else {}
    a = d.get("a", {})
    pr = a.get("pr", {}) if a else {}
    toi = ps.get("toi", {}).get("t") if ps else None
    np_ = ps.get("np", {}).get("t") if ps else None
    toi_yoy = ps.get("toi", {}).get("t.yoy") if ps else None
    roe = pr.get("roe", {}).get("t") if pr else None
    print(f"{name}（{code}）: 营收={toi}亿, 净利={np_}亿, 营收YoY={toi_yoy}%, ROE={roe}%")

print("\n" + "=" * 60)
print("5. 近60日价格区间")
print("=" * 60)
for code in codes:
    r4 = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-03-14",
        "endDate": "2026-05-15",
        "type": "k_day",
        "adjustmentType": "qfq"
    })
    data = r4.get("data", [])
    if data:
        prices = [d.get("c", 0) for d in data if d.get("c")]
        high60 = max(prices)
        low60 = min(prices)
        latest = prices[-1]
        pos = round((latest - low60) / (high60 - low60) * 100, 1) if high60 != low60 else 0
        print(f"{CODES[code]}（{code}）: 最新={latest}, 60日高={high60}, 60日低={low60}, 位置={pos}%")

print("\n完成!")
