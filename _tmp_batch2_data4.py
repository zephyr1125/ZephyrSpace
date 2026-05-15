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

# Find valid fs metrics by doc
r = lx_post("doc", {"path": "cn/company/fs/non_financial"})
doc = r.get("data", {})
metrics = doc.get("metricsList", [])
print("Valid FS metrics sample:")
for m in metrics[:30]:
    print(f"  {m.get('key')} - {m.get('name')}")

# PE historical - single code, time range
print("\n=== PE历史 per-code ===")
for code in ["300750", "002594", "002475"]:
    r2 = lx_post("cn/company/fundamental/non_financial", {
        "stockCode": code,
        "startDate": "2023-05-15",
        "endDate": "2026-05-15",
        "metricsList": ["pe_ttm"]
    })
    data = r2.get("data", [])
    if data:
        pe_vals = [d["pe_ttm"] for d in data if d.get("pe_ttm") and d["pe_ttm"] > 0]
        sorted_pe = sorted(pe_vals)
        n = len(sorted_pe)
        current_val = {"300750": 24.81, "002594": 31.87, "002475": 31.32}[code]
        pct = sum(1 for v in sorted_pe if v <= current_val) / n * 100
        print(f"{code}: n={n}, current={current_val:.1f}, pct={pct:.0f}%, Q20={sorted_pe[int(n*0.2)]:.1f}, Q50={sorted_pe[n//2]:.1f}, Q80={sorted_pe[int(n*0.8)]:.1f}")
    else:
        print(f"{code}: {r2.get('error', r2)}")
