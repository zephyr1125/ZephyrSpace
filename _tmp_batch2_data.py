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

CODES = ["300750", "002594", "002475"]  # 宁德时代, 比亚迪, 立讯精密
TRADE_DATE = "2026-05-15"
LAST_ANNUAL = "2025-12-31"

# 1. 价格（K线）
print("=== 股价（收盘价）===")
for code in CODES:
    r = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-05-14",
        "endDate": TRADE_DATE,
        "fields": ["c"]
    })
    data = r.get("data", [])
    if data:
        latest = data[-1]
        print(f"{code}: {latest}")
    else:
        print(f"{code}: no data, raw={r}")

# 2. 估值（PE/PB/市值）
print("\n=== 估值 ===")
val = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": CODES,
    "date": TRADE_DATE,
    "metricsList": ["pe_ttm", "pb", "mc", "dyr"]
})
for d in val.get("data", []):
    print(f"{d['stockCode']}: PE={d.get('pe_ttm')}, PB={d.get('pb')}, MC={d.get('mc')}, DYR={d.get('dyr')}")

# 3. PE历史分位
print("\n=== PE历史分位 ===")
for code in CODES:
    r = lx_post("cn/company/fundamental/non_financial", {
        "stockCode": code,
        "startDate": "2023-05-15",
        "endDate": TRADE_DATE,
        "metricsList": ["pe_ttm"]
    })
    data = r.get("data", [])
    if data:
        pe_vals = [d["pe_ttm"] for d in data if d.get("pe_ttm") and d["pe_ttm"] > 0]
        if pe_vals:
            current = pe_vals[-1]
            sorted_pe = sorted(pe_vals)
            n = len(sorted_pe)
            pct = sum(1 for v in sorted_pe if v <= current) / n * 100
            print(f"{code}: current PE={current:.1f}, 3yr percentile={pct:.0f}%, min={min(pe_vals):.1f}, max={max(pe_vals):.1f}, median={sorted_pe[n//2]:.1f}")
    else:
        print(f"{code}: no PE hist data")

# 4. 财报数据（年报ROE/营收/净利）
print("\n=== 财报数据（2025年报）===")
fs = lx_post("cn/company/fs/non_financial", {
    "stockCodes": CODES,
    "date": LAST_ANNUAL,
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t", "a.pr.np.t.yoy", "a.pr.gpm"]
})
for d in fs.get("data", []):
    code = d["stockCode"]
    y = d.get("y", {})
    ps = y.get("ps", {})
    pr = y.get("pr", {})
    print(f"{code}:")
    # Try different key structures
    print(f"  raw keys: {list(y.keys())[:10]}")
    # ROE
    try:
        roe = pr.get("roe", {}).get("t")
        print(f"  ROE={roe}")
    except:
        pass
    try:
        toi = ps.get("toi", {}).get("t")
        toi_yoy = ps.get("toi", {}).get("t", {})
        print(f"  TOI={toi}")
    except:
        pass
    print(f"  full pr keys: {list(pr.keys())[:5] if isinstance(pr, dict) else pr}")
    print(f"  full ps keys: {list(ps.keys())[:5] if isinstance(ps, dict) else ps}")

print("\n=== 财报原始 (002475) ===")
fs2 = lx_post("cn/company/fs/non_financial", {
    "stockCode": "002475",
    "date": LAST_ANNUAL,
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t"]
})
print(json.dumps(fs2.get("data", []), ensure_ascii=False, indent=2)[:3000])
