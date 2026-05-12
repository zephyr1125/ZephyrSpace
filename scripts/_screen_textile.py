"""
纺织服饰行业 (申万 801130.SI) 量化粗筛脚本
行业分类：消费/医药 参数组（偏制造混合，ROE门槛12%+，加⚠️标注）
筛选条件：市值≥40亿，ROE年报≥12%，营收同比≥-15%，PE>0
排序：ROE降序，取前15家
"""
import os, requests, gzip, json, tushare as ts
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()
ts.set_token(os.getenv("TUSHARE_TOKEN"))
pro = ts.pro_api()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"


def lx_post(path, payload):
    resp = requests.post(
        f"{LX_BASE}/{path}",
        json=dict(**payload, token=LX_TOKEN),
        headers={"Accept-Encoding": "gzip"},
    )
    try:
        return json.loads(gzip.decompress(resp.content))
    except Exception:
        return resp.json()


def get_fs(d, *keys):
    """从嵌套FS字典中提取值，如 get_fs(d,'y','ps','toi','t')"""
    v = d
    for k in keys:
        if not isinstance(v, dict):
            return None
        v = v.get(k)
        if v is None:
            return None
    return v


def lx_post_batch(path, payload, codes_key="stockCodes", batch_size=100):
    """自动分批调用支持 stockCodes 的接口（限100只/批）"""
    all_codes = payload.get(codes_key, [])
    all_data = []
    for i in range(0, len(all_codes), batch_size):
        batch = all_codes[i:i + batch_size]
        p = dict(**payload)
        p[codes_key] = batch
        resp = lx_post(path, p)
        all_data.extend(resp.get("data", []))
    return {"data": all_data, "message": "success"}


# Step 1: Get constituents
df_m = pro.index_member(index_code="801130.SI")
current_ts = df_m[df_m["is_new"] == "Y"]["con_code"].tolist()
lx_codes = [c.split(".")[0] for c in current_ts]
print(f"Total 纺织服饰 stocks: {len(lx_codes)}")

# Step 2: Batch fetch fundamental data (PE, PB, MC)
trade_date = "2026-05-08"
last_annual = "2024-12-31"
prev_annual = "2023-12-31"

print("Fetching fundamental data (PE/PB/MC)...")
val_resp = lx_post_batch("cn/company/fundamental/non_financial", {
    "stockCodes": lx_codes,
    "date": trade_date,
    "metricsList": ["pe_ttm", "pb", "mc"],
})
print(f"  status: {val_resp.get('message','')}, count: {len(val_resp.get('data',[]))}")
val_dict = {d["stockCode"]: d for d in val_resp.get("data", [])}

# Step 3: Batch fetch 2024 annual FS (revenue, net profit, assets, liabilities)
print("Fetching 2024 annual FS data...")
fs24_resp = lx_post_batch("cn/company/fs/non_financial", {
    "stockCodes": lx_codes,
    "date": last_annual,
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "y.bs.ta.t", "y.bs.tl.t"],
})
print(f"  status: {fs24_resp.get('message','')}, count: {len(fs24_resp.get('data',[]))}")
fs24_dict = {d["stockCode"]: d for d in fs24_resp.get("data", [])}

# Step 4: Batch fetch 2023 annual FS (for revenue YoY calculation)
print("Fetching 2023 annual FS data...")
fs23_resp = lx_post_batch("cn/company/fs/non_financial", {
    "stockCodes": lx_codes,
    "date": prev_annual,
    "metricsList": ["y.ps.toi.t"],
})
print(f"  status: {fs23_resp.get('message','')}, count: {len(fs23_resp.get('data',[]))}")
fs23_dict = {d["stockCode"]: d for d in fs23_resp.get("data", [])}

# Step 5: Get stock names from tushare
print("Fetching stock names...")
name_dict = {}
for ts_code in current_ts:
    code = ts_code.split(".")[0]
    df_b = pro.stock_basic(ts_code=ts_code, fields="ts_code,name,list_status")
    if df_b is not None and len(df_b) > 0:
        row = df_b.iloc[0]
        name_dict[code] = str(row["name"])
        if str(row["list_status"]) != "L":
            name_dict[code] = f"[{row['list_status']}]{row['name']}"

print(f"  Got {len(name_dict)} names")

# Step 6: Compute metrics and apply filters
# Thresholds (消费/制造混合行业)
MC_MIN = 40.0    # 亿元
ROE_MIN = 12.0   # % (标准15%，但纺织制造偏低，用12%为硬门槛)
ROE_WARN = 15.0  # % (低于此标注⚠️)
REV_YOY_MIN = -15.0  # %

results = []
excluded = []

for code in lx_codes:
    name = name_dict.get(code, code)

    # Skip delisted
    if name.startswith("[") and not name.startswith("[L]"):
        excluded.append({"code": code, "name": name, "reason": "已退市/停牌"})
        continue

    v = val_dict.get(code, {})
    f24 = fs24_dict.get(code, {})
    f23 = fs23_dict.get(code, {})

    mc = v.get("mc")        # 元，需转换为亿元
    pe = v.get("pe_ttm")
    pb = v.get("pb")

    # Extract FS fields from nested structure, values are in 元 (yuan)
    rev24_y = get_fs(f24, "y", "ps", "toi", "t")
    np24_y  = get_fs(f24, "y", "ps", "np", "t")
    ta24_y  = get_fs(f24, "y", "bs", "ta", "t")
    tl24_y  = get_fs(f24, "y", "bs", "tl", "t")
    rev23_y = get_fs(f23, "y", "ps", "toi", "t")

    # Convert to 亿元
    rev24 = rev24_y / 1e8 if rev24_y else None
    np24  = np24_y / 1e8 if np24_y else None
    ta24  = ta24_y / 1e8 if ta24_y else None
    tl24  = tl24_y / 1e8 if tl24_y else None
    rev23 = rev23_y / 1e8 if rev23_y else None

    # Compute derived metrics
    equity = (ta24 - tl24) if (ta24 is not None and tl24 is not None) else None
    roe = (np24 / equity * 100) if (np24 is not None and equity and equity > 0) else None
    rev_yoy = ((rev24 - rev23) / abs(rev23) * 100) if (rev24 and rev23 and rev23 != 0) else None

    # Convert mc from 元 to 亿元
    mc_yi = mc / 1e8 if mc is not None else None

    # Check missing critical data
    if mc_yi is None:
        excluded.append({"code": code, "name": name, "reason": "缺市值数据"})
        continue

    # Hard filters
    flags = []

    if mc_yi < MC_MIN:
        excluded.append({"code": code, "name": name, "mc": round(mc_yi, 1),
                         "reason": f"市值{round(mc_yi,1)}亿 < 40亿"})
        continue

    if pe is not None and pe <= 0:
        excluded.append({"code": code, "name": name, "pe": pe,
                         "reason": f"PE={round(pe,1) if pe else 'N/A'}亏损"})
        continue

    if roe is not None and roe < ROE_MIN:
        excluded.append({"code": code, "name": name, "roe": round(roe,1),
                         "reason": f"ROE={round(roe,1)}% < {ROE_MIN}%"})
        continue

    if rev_yoy is not None and rev_yoy < REV_YOY_MIN:
        excluded.append({"code": code, "name": name, "rev_yoy": round(rev_yoy,1),
                         "reason": f"营收同比={round(rev_yoy,1)}% < {REV_YOY_MIN}%"})
        continue

    # Warnings for boundary cases
    if roe is not None and roe < ROE_WARN:
        flags.append(f"⚠️ROE偏低({round(roe,1)}%<15%)")

    results.append({
        "code": code,
        "name": name,
        "mc": round(mc_yi, 1) if mc_yi else None,
        "pe": round(pe, 1) if pe else None,
        "pb": round(pb, 2) if pb else None,
        "roe": round(roe, 1) if roe else None,
        "rev_yoy": round(rev_yoy, 1) if rev_yoy else None,
        "flags": " ".join(flags),
    })

# Sort by ROE descending
results.sort(key=lambda x: x.get("roe") or 0, reverse=True)

print(f"\n=== 粗筛结果 ===")
print(f"通过筛选: {len(results)} 家 | 未通过: {len(excluded)} 家")
print()
print(f"{'排名':<4} {'代码':<8} {'名称':<14} {'市值亿':<8} {'PE':<7} {'PB':<6} {'ROE%':<8} {'营收同比%':<10} 标注")
print("-" * 85)
for i, r in enumerate(results[:20], 1):
    mc_s = f"{r['mc']:.1f}" if r['mc'] is not None else "N/A"
    pe_s = f"{r['pe']:.1f}" if r['pe'] is not None else "N/A"
    pb_s = f"{r['pb']:.2f}" if r['pb'] is not None else "N/A"
    roe_s = f"{r['roe']:.1f}" if r['roe'] is not None else "N/A"
    yoy_s = f"{r['rev_yoy']:.1f}" if r['rev_yoy'] is not None else "N/A"
    print(f"{i:<4} {r['code']:<8} {r['name']:<14} {mc_s:<8} {pe_s:<7} {pb_s:<6} {roe_s:<8} {yoy_s:<10} {r['flags']}")

print()
print("=== 排除原因统计 ===")
from collections import Counter
reason_counts = Counter(e["reason"].split()[0] for e in excluded)
for reason, cnt in reason_counts.most_common():
    print(f"  {reason}: {cnt}只")

# Save full results
output = {"pass": results, "excluded": excluded}
with open("scripts/_screen_textile_result.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print("\nResults saved to scripts/_screen_textile_result.json")
