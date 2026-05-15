import requests, os, json, gzip
from dotenv import load_dotenv
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

CODES = ["300750", "002594", "002475"]
TRADE_DATE = "2026-05-15"
LAST_ANNUAL = "2025-12-31"

# 1. 股价 - use type="qfq" for forward adjusted prices
print("=== 股价 ===")
for code in CODES:
    r = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-05-13",
        "endDate": TRADE_DATE,
        "type": "not_adjusted",
        "fields": ["c", "t"]
    })
    data = r.get("data", [])
    if data:
        print(f"{code}: {data[-1]}")
    else:
        print(f"{code}: no data, {r.get('error', r)}")

# 2. PE历史分位 - try with type
print("\n=== PE历史分位（3年）===")
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
            sorted_pe = sorted(pe_vals)
            n = len(sorted_pe)
            current = pe_vals[-1]
            pct = sum(1 for v in sorted_pe if v <= current) / n * 100
            print(f"{code}: PE={current:.1f}x, 3yr={pct:.0f}%, Q20={sorted_pe[int(n*0.2)]:.1f}, Q50={sorted_pe[n//2]:.1f}, Q80={sorted_pe[int(n*0.8)]:.1f}")
    else:
        print(f"{code}: error {r.get('error', 'unknown')}")

# 3. Financials - correct structure
print("\n=== 财报 ===")
for code in CODES:
    r = lx_post("cn/company/fs/non_financial", {
        "stockCode": code,
        "startDate": "2025-01-01",
        "endDate": "2026-04-30",
        "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t", "a.pr.np.t.yoy", "a.pr.gpm"]
    })
    data = r.get("data", [])
    if data:
        # Find the latest year-end report (date ending in -12-31)
        annual = [d for d in data if d.get("date", "").endswith("-12-31")]
        if annual:
            latest = annual[-1]
            print(f"\n{code} ({latest.get('date')}): keys={list(latest.keys())[:8]}")
            print(f"  full data: {json.dumps(latest, ensure_ascii=False)[:800]}")
        else:
            latest = data[-1]
            print(f"\n{code} ({latest.get('date')}, NON-ANNUAL): {json.dumps(latest, ensure_ascii=False)[:400]}")
    else:
        print(f"\n{code}: no data, {r.get('error', r)}")
