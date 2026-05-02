"""
931994成分股粗筛复查（使用理杏仁API + 用户提供的成分股JSON）
- 成分股来源：用户提供JSON中2026-03-31的完整80只名单
- 估值数据：理杏仁fundamental（2026-04-30）
- 财务数据：理杏仁fundamental分位 + 东方财富年报ROE
"""
import json, requests, os, time
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    resp = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN}, timeout=20)
    return resp.json()

# Step 1: 从用户提供的JSON提取成分股（用2026-03-31完整列表）
print("Step 1: 加载成分股数据（2026-03-31）...")
with open(r'C:\Users\zephy\.copilot\session-state\187bb1a3-92ae-4144-96de-043d3106c633\files\paste-1777725802487.txt', 'r', encoding='utf-8') as f:
    constituent_data = json.load(f)

records = constituent_data['data']
# 用2026-03-31完整80只
full_list = [r for r in records if r['date'].startswith('2026-03-31')]
full_list.sort(key=lambda x: x.get('weighting', 0), reverse=True)
# 用2026-04-30的top10权重覆盖（更新权重）
latest_weights = {r['stockCode']: r['weighting'] for r in records if r['date'].startswith('2026-04-30')}
# 合并权重：有最新权重用最新，否则用3月31日权重
for s in full_list:
    if s['stockCode'] in latest_weights:
        s['weighting'] = latest_weights[s['stockCode']]

codes = [s['stockCode'] for s in full_list]
weight_dict = {s['stockCode']: s['weighting'] for s in full_list}
print(f"  成分股数: {len(codes)}")

# Step 2: 批量获取估值数据（PE/PB/市值），分批100只
TRADE_DATE = "2026-04-30"
print(f"Step 2: 批量获取估值数据（{TRADE_DATE}）...")
val_dict = {}
for i in range(0, len(codes), 100):
    batch = codes[i:i+100]
    r = lx_post("cn/company/fundamental/non_financial", {
        "stockCodes": batch,
        "date": TRADE_DATE,
        "metricsList": ["pe_ttm", "pb", "mc", "dyr", "pe_ttm.y3.cvpos", "pe_ttm.y5.cvpos"]
    })
    for d in r.get("data", []):
        val_dict[d["stockCode"]] = d
    time.sleep(0.1)
print(f"  获取到: {len(val_dict)} 只")

# Step 3: 东方财富批量获取年报ROE和营收同比
# 使用东方财富RPT_LICO_FN_CPD API（已验证可用）
import urllib.request, urllib.parse
print("Step 3: 东方财富获取年报ROE（2025年报）...")

roe_dict = {}
rev_yoy_dict = {}
for code in codes:
    try:
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE%3D%22{code}%22)&pageNumber=1&pageSize=5"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        rows = data.get("result", {}).get("data", []) or []
        # 找最新年报（DATEMMDD=年报 或 QDATE以Q4结尾）
        annual = [r for r in rows if r.get("DATEMMDD") == "年报" or (r.get("QDATE", "").endswith("Q4"))]
        if annual:
            a = annual[0]
            roe = a.get("WEIGHTAVG_ROE")
            roe_dict[code] = float(roe) if roe else None
            # 营收同比
            rev_yoy = a.get("TOTALOPERATEREVE_YOY")
            rev_yoy_dict[code] = float(rev_yoy) if rev_yoy else None
        time.sleep(0.08)
    except Exception as e:
        roe_dict[code] = None
        rev_yoy_dict[code] = None

print(f"  获取ROE: {sum(1 for v in roe_dict.values() if v is not None)} 只")

# 同时从理杏仁获取营收同比（y.ps.toi.t模式）
print("Step 3b: 理杏仁获取年度营收（y.ps.toi.t）...")
fs_dict = {}
for i in range(0, len(codes), 100):
    batch = codes[i:i+100]
    r = lx_post("cn/company/fs/non_financial", {
        "stockCodes": batch,
        "date": "2025-12-31",
        "metricsList": ["y.ps.toi.t"]
    })
    for d in r.get("data", []):
        fs_dict[d["stockCode"]] = d
    time.sleep(0.1)
# 同期上年营收
fs_dict_2024 = {}
for i in range(0, len(codes), 100):
    batch = codes[i:i+100]
    r = lx_post("cn/company/fs/non_financial", {
        "stockCodes": batch,
        "date": "2024-12-31",
        "metricsList": ["y.ps.toi.t"]
    })
    for d in r.get("data", []):
        fs_dict_2024[d["stockCode"]] = d
    time.sleep(0.1)
print(f"  2025营收: {len(fs_dict)} 只, 2024营收: {len(fs_dict_2024)} 只")

def get_rev(d_dict, code):
    d = d_dict.get(code, {})
    y = d.get("y", {})
    if isinstance(y, dict):
        return y.get("ps", {}).get("toi", {}).get("t")
    return None

def calc_yoy(code):
    r2025 = get_rev(fs_dict, code)
    r2024 = get_rev(fs_dict_2024, code)
    if r2025 and r2024 and r2024 != 0:
        return (r2025 - r2024) / abs(r2024) * 100
    return None

# Step 4: 粗筛（成长科技类）
MIN_MC = 40
MIN_ROE = 12.0
ROE_BOUNDARY = 9.6
MIN_REV_YOY = -10.0
REV_BOUNDARY = -12.0

print()
print("=" * 110)
hdr = f"{'#':3} {'代码':10} {'权重':7} {'市值亿':8} {'PE':7} {'PB':6} {'ROE':7} {'营收同比':9} {'PE3yr%':8} {'结论'}"
print(hdr)
print("=" * 110)

passed = []
failed_list = []

for i, code in enumerate(codes, 1):
    val = val_dict.get(code, {})
    mc_raw = val.get("mc")
    mc = mc_raw / 1e8 if mc_raw else None  # 转换为亿
    pe = val.get("pe_ttm")
    pb = val.get("pb")
    pe3_pos = val.get("pe_ttm.y3.cvpos")
    dyr = val.get("dyr")
    weight = weight_dict.get(code, 0) * 100

    roe = roe_dict.get(code)
    # 营收同比：优先东方财富，备用理杏仁自算
    rev_yoy = rev_yoy_dict.get(code)
    if rev_yoy is None:
        rev_yoy = calc_yoy(code)

    # 粗筛
    reasons = []
    status = "PASS"

    if mc is None or mc < MIN_MC:
        reasons.append(f"市值{'N/A' if mc is None else f'{mc:.0f}亿'}<{MIN_MC}亿")
        status = "FAIL"

    if pe is not None and pe <= 0:
        reasons.append("PE≤0亏损")
        status = "FAIL"

    if roe is None:
        reasons.append("ROE无数据")
        status = "FAIL"
    elif roe < ROE_BOUNDARY:
        reasons.append(f"ROE{roe:.1f}%<{ROE_BOUNDARY}%")
        status = "FAIL"
    elif roe < MIN_ROE:
        reasons.append(f"ROE{roe:.1f}%BORDER")
        if status == "PASS":
            status = "BORDER"

    if rev_yoy is not None:
        if rev_yoy < REV_BOUNDARY:
            reasons.append(f"营收{rev_yoy:.1f}%<{REV_BOUNDARY}%")
            status = "FAIL"
        elif rev_yoy < MIN_REV_YOY:
            reasons.append(f"营收{rev_yoy:.1f}%边界")
            if status == "PASS":
                status = "BORDER"

    mc_s = f"{mc:.0f}" if mc else "N/A"
    pe_s = f"{pe:.1f}x" if pe else "N/A"
    pb_s = f"{pb:.2f}" if pb else "N/A"
    roe_s = f"{roe:.1f}%" if roe is not None else "N/A"
    yoy_s = f"{rev_yoy:.1f}%" if rev_yoy is not None else "N/A"
    pe3_s = f"{pe3_pos*100:.0f}%" if pe3_pos else "N/A"
    reason_s = " ".join(reasons)

    print(f"{i:3} {code:10} {weight:6.2f}% {mc_s:8} {pe_s:7} {pb_s:6} {roe_s:7} {yoy_s:9} {pe3_s:8} {status} {reason_s}")

    info = {"code": code, "weight": weight, "mc": mc, "pe": pe, "pb": pb,
            "roe": roe, "rev_yoy": rev_yoy, "pe3_pos": pe3_pos, "status": status, "reasons": reasons}
    if "FAIL" not in status:
        passed.append(info)
    else:
        failed_list.append(info)

print("=" * 110)
print(f"\n✅ 通过粗筛: {len(passed)} 只（含BORDER）")
print(f"FAIL 排除: {len(failed_list)} 只")
print()
print("=== 通过粗筛成分股汇总 ===")
for s in sorted(passed, key=lambda x: x['weight'], reverse=True):
    roe_s = f"{s['roe']:.1f}%" if s['roe'] is not None else "N/A"
    yoy_s = f"{s['rev_yoy']:.1f}%" if s['rev_yoy'] is not None else "N/A"
    pe_s = f"{s['pe']:.1f}x" if s['pe'] else "N/A"
    mc_s = f"{s['mc']:.0f}亿" if s['mc'] else "N/A"
    border = " ⚠️" if "⚠️" in s['status'] else ""
    print(f"  {s['code']:10} 权重{s['weight']:.2f}% 市值{mc_s} PE={pe_s} ROE={roe_s} 营收同比={yoy_s}{border}")

