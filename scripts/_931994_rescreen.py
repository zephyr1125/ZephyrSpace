"""
931994中证电网设备主题指数 — 成分股粗筛复查脚本
使用理杏仁API，以2025年报ROE为基准，避免tushare Q1陷阱
"""
import requests, os, json
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    resp = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN})
    return resp.json()

# 最近交易日（2026-04-30，周三）
TRADE_DATE = "2026-04-30"
# 年报日期（2025年报）
ANNUAL_DATE = "2025-12-31"

# Step 1: 获取931994全成分股（带权重）
print("Step 1: 获取931994成分股权重...")
r = lx_post("cn/index/constituent-weightings", {
    "stockCode": "931994",
    "startDate": TRADE_DATE
})
all_stocks = sorted(r.get("data", []), key=lambda x: x.get("weighting", 0), reverse=True)
codes = [s["stockCode"] for s in all_stocks]
weight_dict = {s["stockCode"]: s.get("weighting", 0) for s in all_stocks}
print(f"  共 {len(codes)} 只成分股")

# Step 2: 批量获取PE/PB/市值（估值日：最近交易日）
print("Step 2: 批量获取估值数据...")
val_r = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": TRADE_DATE,
    "metricsList": ["pe_ttm", "pb", "mc"]
})
val_dict = {d["stockCode"]: d for d in val_r.get("data", [])}

# Step 3: 批量获取年报财务数据（ROE、营收同比）
print("Step 3: 批量获取2025年报财务数据...")
fs_r = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": ANNUAL_DATE,
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t.yoy", "a.ps.toi.t", "a.pr.np.t", "a.cr.cfi.oa.t"]
})
fs_dict = {d["stockCode"]: d for d in fs_r.get("data", [])}

# Step 4: 粗筛（成长科技类参数）
# 行业参数：市值≥40亿，ROE≥12%（边界±20%即≥9.6%标⚠️），营收同比≥-10%（边界≥-12%标⚠️）
# PE≤0或NaN → 亏损排除；PE高只影响档位不排除
MIN_MC = 40          # 市值下限(亿)
MIN_ROE = 12.0       # ROE下限(%)
ROE_BOUNDARY = 9.6   # ROE边界(%)  = 12 * 0.8
MIN_REV_YOY = -10.0  # 营收同比下限(%)
REV_BOUNDARY = -12.0 # 营收同比边界(%)

print("\n" + "="*100)
print(f"{'排名':4} {'公司代码':12} {'权重':7} {'市值(亿)':9} {'PE':8} {'ROE':8} {'营收同比':9} {'营收(亿)':9} {'净利(亿)':9} {'净现比':8} {'粗筛'}")
print("="*100)

passed = []
failed = []
borderline = []

for i, code in enumerate(codes, 1):
    val = val_dict.get(code, {})
    fs = fs_dict.get(code, {})

    mc = val.get("mc")
    pe = val.get("pe_ttm")
    pb = val.get("pb")
    roe = fs.get("a.pr.roe.t")
    rev_yoy = fs.get("a.ps.toi.t.yoy")
    rev = fs.get("a.ps.toi.t")
    np_ = fs.get("a.pr.np.t")
    ocf = fs.get("a.cr.cfi.oa.t")
    weight = weight_dict.get(code, 0) * 100

    # 净现比
    net_cash_r = (ocf / np_ * 100) if ocf and np_ and np_ > 0 else None

    # 粗筛逻辑
    reasons = []
    status = "✅PASS"
    is_border = False

    # 市值
    if mc is None or mc < MIN_MC:
        reasons.append(f"市值{mc:.1f}亿<{MIN_MC}亿" if mc else "市值N/A")
        status = "❌"
    # PE亏损排除
    if pe is not None and pe <= 0:
        reasons.append("PE≤0亏损")
        status = "❌"
    # ROE
    if roe is None:
        reasons.append("ROE无数据")
        status = "❌"
    elif roe < ROE_BOUNDARY:
        reasons.append(f"ROE={roe:.1f}%<{ROE_BOUNDARY}%")
        status = "❌"
    elif roe < MIN_ROE:
        reasons.append(f"ROE={roe:.1f}%⚠️边界")
        is_border = True
        if status == "✅PASS":
            status = "⚠️边界"
    # 营收同比
    if rev_yoy is not None:
        rev_yoy_pct = rev_yoy * 100
        if rev_yoy_pct < REV_BOUNDARY:
            reasons.append(f"营收{rev_yoy_pct:.1f}%<{REV_BOUNDARY}%")
            status = "❌"
        elif rev_yoy_pct < MIN_REV_YOY:
            reasons.append(f"营收{rev_yoy_pct:.1f}%⚠️边界")
            is_border = True
            if status == "✅PASS":
                status = "⚠️边界"

    pe_str = f"{pe:.1f}x" if pe else "N/A"
    roe_str = f"{roe:.1f}%" if roe is not None else "N/A"
    rev_yoy_str = f"{rev_yoy*100:.1f}%" if rev_yoy is not None else "N/A"
    rev_str = f"{rev/1e8:.1f}" if rev else "N/A"
    np_str = f"{np_/1e8:.1f}" if np_ else "N/A"
    ncr_str = f"{net_cash_r:.0f}%" if net_cash_r else "N/A"
    mc_str = f"{mc:.0f}" if mc else "N/A"

    reason_str = " ".join(reasons) if reasons else ""
    print(f"{i:4} {code:12} {weight:6.2f}% {mc_str:9} {pe_str:8} {roe_str:8} {rev_yoy_str:9} {rev_str:9} {np_str:9} {ncr_str:8} {status} {reason_str}")

    stock_info = {
        "code": code, "weight": weight, "mc": mc, "pe": pe, "pb": pb,
        "roe": roe, "rev_yoy_pct": rev_yoy * 100 if rev_yoy is not None else None,
        "rev": rev, "np": np_, "ocf": ocf, "net_cash_r": net_cash_r,
        "status": status, "reasons": reasons
    }
    if "✅" in status:
        passed.append(stock_info)
    elif "⚠️" in status:
        borderline.append(stock_info)
        passed.append(stock_info)  # 边界也进候选
    else:
        failed.append(stock_info)

print("="*100)
print(f"\n通过粗筛（含边界）：{len(passed)} 只")
print(f"  其中明确通过：{sum(1 for s in passed if '✅' in s['status'])} 只")
print(f"  边界通过⚠️：{len(borderline)} 只")
print(f"排除：{len(failed)} 只")

print("\n=== 通过粗筛的成分股汇总 ===")
for s in passed:
    roe_str = f"{s['roe']:.1f}%" if s['roe'] is not None else "N/A"
    rev_str = f"{s['rev_yoy_pct']:.1f}%" if s['rev_yoy_pct'] is not None else "N/A"
    mc_str = f"{s['mc']:.0f}亿" if s['mc'] else "N/A"
    pe_str = f"{s['pe']:.1f}x" if s['pe'] else "N/A"
    ncr_str = f"{s['net_cash_r']:.0f}%" if s['net_cash_r'] else "N/A"
    border_tag = " ⚠️" if "⚠️" in s['status'] else ""
    print(f"  {s['code']}: 权重{s['weight']:.2f}% 市值{mc_str} PE={pe_str} ROE={roe_str} 营收同比={rev_str} 净现比={ncr_str}{border_tag}")
