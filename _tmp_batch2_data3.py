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

# --- Stock prices (already have from run above) ---
PRICES = {
    "300750": 434.05,
    "002594": 98.60,
    "002475": 80.15,
}
print("Prices (2026-05-13):", PRICES)

# --- Current valuation (already have) ---
VALS = {
    "300750": {"pe": 24.81, "pb": 6.02, "mc_yi": 19598},
    "002594": {"pe": 31.87, "pb": 3.79, "mc_yi": 8780},
    "002475": {"pe": 31.32, "pb": 6.10, "mc_yi": 5392},
}

# PE historical percentile - need stockCodes array + date range
print("\n=== PE历史分位（3年）===")
r = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": CODES,
    "startDate": "2023-05-15",
    "endDate": TRADE_DATE,
    "metricsList": ["pe_ttm"]
})
data = r.get("data", [])
if data:
    from collections import defaultdict
    pe_by_code = defaultdict(list)
    for d in data:
        pe = d.get("pe_ttm")
        if pe and pe > 0:
            pe_by_code[d["stockCode"]].append(pe)
    for code in CODES:
        pe_vals = pe_by_code[code]
        if pe_vals:
            sorted_pe = sorted(pe_vals)
            n = len(sorted_pe)
            current = VALS[code]["pe"]
            pct = sum(1 for v in sorted_pe if v <= current) / n * 100
            print(f"{code}: PE={current:.1f}x, 3yr_pct={pct:.0f}%, Q20={sorted_pe[int(n*0.2)]:.1f}, Q50={sorted_pe[n//2]:.1f}, Q80={sorted_pe[int(n*0.8)]:.1f}, min={min(pe_vals):.1f}")
else:
    print(f"No data: {r.get('error', r)}")

# Financials
print("\n=== 财报（年报）===")
r2 = lx_post("cn/company/fs/non_financial", {
    "stockCodes": CODES,
    "date": LAST_ANNUAL,
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t", "a.pr.np.t.yoy", "a.pr.gpm"]
})
data2 = r2.get("data", [])
if data2:
    for d in data2:
        print(f"\n{d['stockCode']} ({d.get('date')}): {json.dumps(d, ensure_ascii=False)[:600]}")
else:
    print(f"No data: {r2.get('error', r2)}")

# 立讯精密 extra: try fetching more details
print("\n=== 立讯精密 详情 ===")
r3 = lx_post("cn/company/fs/non_financial", {
    "stockCode": "002475",
    "startDate": "2024-06-01",
    "endDate": "2026-04-30",
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t"]
})
print(json.dumps(r3.get("data", [])[:3], ensure_ascii=False, indent=2)[:2000])
