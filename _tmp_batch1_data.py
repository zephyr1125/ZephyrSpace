"""批次1 PreBuy数据拉取：贵州茅台、美的集团、恒瑞医药"""
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

STOCKS = {
    "600519": "贵州茅台",
    "000333": "美的集团",
    "600276": "恒瑞医药",
}
codes = list(STOCKS.keys())

TRADE_DATE = "2026-05-15"
ANNUAL_END = "2025-12-31"

print("=" * 60)
print("1. 获取最新价格 (candlestick)")
print("=" * 60)
for code in codes:
    r = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-05-14",
        "endDate": "2026-05-15",
        "adjustmentType": "none",
    })
    data = r.get("data", [])
    if data:
        last = data[-1]
        print(f"{STOCKS[code]} ({code}): 收盘={last.get('c')} 日期={last.get('t','')[:10]}")
    else:
        print(f"{STOCKS[code]} ({code}): 无数据, raw={json.dumps(r)[:200]}")

print()
print("=" * 60)
print("2. 获取估值数据 (fundamental/non_financial)")
print("=" * 60)
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": TRADE_DATE,
    "metricsList": ["pe_ttm", "pb", "mc", "dyr",
                    "pe_ttm.y3.cvpos", "pe_ttm.y3.q2v", "pe_ttm.y3.q5v", "pe_ttm.y3.q8v"]
})
val_data = val_resp.get("data", [])
for d in val_data:
    code = d.get("stockCode", "")
    name = STOCKS.get(code, code)
    print(f"\n{name} ({code}):")
    print(f"  PE_TTM={d.get('pe_ttm')}, PB={d.get('pb')}, MC={d.get('mc')}亿, DYR={d.get('dyr')}%")
    print(f"  PE 3年历史分位: cvpos={d.get('pe_ttm.y3.cvpos')}")
    print(f"  Q2v={d.get('pe_ttm.y3.q2v')}, Q5v={d.get('pe_ttm.y3.q5v')}, Q8v={d.get('pe_ttm.y3.q8v')}")

print()
print("=" * 60)
print("3. 获取财务数据 (fs/non_financial) - 年报")
print("=" * 60)
fs_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": ANNUAL_END,
    "metricsList": [
        "a.pr.roe.t",        # ROE
        "a.ps.toi.t",        # 营业收入
        "a.ps.toi.t.yoy",    # 营收同比
        "a.pr.np.t",         # 净利润
        "a.pr.np.t.yoy",     # 净利润同比
        "a.pr.gpm",          # 毛利率
        "a.pr.npm",          # 净利率
        "a.bs.tae",          # 总资产
        "a.bs.te",           # 净资产/权益
        "a.cf.cfi",          # 经营现金流净额
        "a.pr.np.deducted.t" # 扣非净利润
    ]
})
for d in fs_resp.get("data", []):
    code = d.get("stockCode", "")
    name = STOCKS.get(code, code)
    print(f"\n{name} ({code}) FY2025:")
    # nested dict access
    a = d.get("a", {})
    pr = a.get("pr", {})
    ps = a.get("ps", {})
    bs = a.get("bs", {})
    cf = a.get("cf", {})
    
    roe = pr.get("roe", {}).get("t")
    toi = ps.get("toi", {}).get("t")
    toi_yoy = ps.get("toi", {}).get("t", {})
    np_val = pr.get("np", {}).get("t")
    np_yoy = pr.get("np", {}).get("t")
    gpm = pr.get("gpm")
    npm = pr.get("npm")
    tae = bs.get("tae")
    te = bs.get("te")
    cfi = cf.get("cfi")
    np_deducted = pr.get("np", {}).get("deducted", {}).get("t")
    
    print(f"  ROE={roe}")
    # Try flat access
    print(f"  营收={d.get('a.ps.toi.t')}, 同比={d.get('a.ps.toi.t.yoy')}")
    print(f"  净利润={d.get('a.pr.np.t')}, 同比={d.get('a.pr.np.t.yoy')}")
    print(f"  扣非净利={d.get('a.pr.np.deducted.t')}")
    print(f"  毛利率={d.get('a.pr.gpm')}, 净利率={d.get('a.pr.npm')}")
    print(f"  经营现金流={d.get('a.cf.cfi')}")
    print(f"  总资产={d.get('a.bs.tae')}, 净资产={d.get('a.bs.te')}")
    print(f"  ROE(flat)={d.get('a.pr.roe.t')}")

print()
print("=" * 60)
print("4. 查看fs返回结构（第一条原始数据）")
print("=" * 60)
if fs_resp.get("data"):
    first = fs_resp["data"][0]
    print(json.dumps(first, ensure_ascii=False, indent=2)[:3000])

print()
print("=" * 60)
print("5. 获取Q1 2026财务数据")
print("=" * 60)
fs_q1 = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": "2026-03-31",
    "metricsList": [
        "a.pr.roe.t",
        "a.ps.toi.t",
        "a.ps.toi.t.yoy",
        "a.pr.np.t",
        "a.pr.np.t.yoy",
        "a.cf.cfi"
    ]
})
print(f"Q1数据条数: {len(fs_q1.get('data', []))}")
if fs_q1.get("data"):
    for d in fs_q1["data"]:
        code = d.get("stockCode", "")
        name = STOCKS.get(code, code)
        print(f"\n{name} 原始结构(部分):")
        print(json.dumps(d, ensure_ascii=False)[:500])
