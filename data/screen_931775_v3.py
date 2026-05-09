"""
931775 中证全指房地产指数 - 成分股量化粗筛 v3
修正：fs数据嵌套访问；ROE手动计算（np/(ta-tl)）
"""
import akshare as ak
import requests, os, json
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def last_trading_day():
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()

def lx_post(path, payload):
    resp = requests.post(
        f"{LX_BASE}/{path}",
        json={**payload, "token": LX_TOKEN},
        headers={"Accept-Encoding": "gzip"},
        timeout=30
    )
    return resp.json()

def get_nested(d, *keys):
    """安全访问嵌套字典"""
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d

trade_date = last_trading_day()
today = date.today()
last_annual = f"{today.year - 1}-12-31"       # 2025-12-31
last_annual_prev = f"{today.year - 2}-12-31"   # 2024-12-31

print(f"=== 931775 中证全指房地产 粗筛 v3 ===")
print(f"交易日: {trade_date} | 年报期: {last_annual} | 上年: {last_annual_prev}")

# Step 1: akshare成分股
df = ak.index_stock_cons_weight_csindex(symbol="931775")
df = df.sort_values("权重", ascending=False)
all_stocks = df.to_dict("records")
codes = [s["成分券代码"] for s in all_stocks]
weight_map = {s["成分券代码"]: s["权重"] for s in all_stocks}
name_map = {s["成分券代码"]: s["成分券名称"] for s in all_stocks}
print(f"成分股: {len(codes)} 只")

# Step 2: 批量估值（PE/PB/市值）
print("拉取估值...")
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes, "date": trade_date, "metricsList": ["pe_ttm", "pb", "mc"]
})
val_dict = {d["stockCode"]: d for d in val_resp.get("data", [])}
print(f"  返回 {len(val_dict)} 条")

# Step 3: 年报财务（营收/净利润/总资产/总负债）
print("拉取年报财务(2025)...")
fs_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes, "date": last_annual,
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "y.bs.ta.t", "y.bs.tl.t"]
})
fs_dict = {}
for d in fs_resp.get("data", []):
    code = d["stockCode"]
    if code not in fs_dict or d.get("date","") > fs_dict[code].get("date",""):
        fs_dict[code] = d
print(f"  返回 {len(fs_dict)} 条")

# Step 4: 上年营收（同比分母）
print("拉取年报财务(2024)...")
fs_prev_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes, "date": last_annual_prev,
    "metricsList": ["y.ps.toi.t"]
})
fs_prev_dict = {}
for d in fs_prev_resp.get("data", []):
    code = d["stockCode"]
    if code not in fs_prev_dict or d.get("date","") > fs_prev_dict[code].get("date",""):
        fs_prev_dict[code] = d
print(f"  返回 {len(fs_prev_dict)} 条")

# Step 5: 粗筛
MIN_MC      = 40    # 亿
MIN_ROE     = 8     # %（房地产降阈值，标准为10%）
MIN_REV_YOY = -20   # %

passed, failed = [], []
for code in codes:
    name  = name_map.get(code, code)
    weight = weight_map.get(code, 0)
    val   = val_dict.get(code, {})
    fs    = fs_dict.get(code, {})
    fs_p  = fs_prev_dict.get(code, {})

    # 估值
    mc_raw = val.get("mc")
    pe_raw = val.get("pe_ttm")
    pb_raw = val.get("pb")
    mc = float(mc_raw)/1e8 if mc_raw else None
    pe = float(pe_raw) if pe_raw else None
    pb = float(pb_raw) if pb_raw else None

    # 财务（嵌套结构）
    y = fs.get("y", {})
    toi_curr = get_nested(y, "ps", "toi", "t")
    np_      = get_nested(y, "ps", "np",  "t")
    ta       = get_nested(y, "bs", "ta",  "t")
    tl       = get_nested(y, "bs", "tl",  "t")

    y_p = fs_p.get("y", {})
    toi_prev = get_nested(y_p, "ps", "toi", "t")

    # ROE手算
    equity = (float(ta) - float(tl)) if ta and tl else None
    roe = float(np_)/equity*100 if np_ and equity and equity != 0 else None

    # 营收同比
    if toi_curr and toi_prev and float(toi_prev) != 0:
        rev_yoy = (float(toi_curr) - float(toi_prev)) / abs(float(toi_prev)) * 100
    else:
        rev_yoy = None

    # 边界模糊标注（偏离阈值<=20%则保留并标注⚠️）
    BORDER_ROE_LOW = MIN_ROE * 0.8
    BORDER_YOY_LOW = MIN_REV_YOY * 1.2  # 更负

    reasons = []
    warnings = []

    if mc is None or mc < MIN_MC:
        reasons.append(f"市值={mc:.0f}亿<{MIN_MC}亿" if mc else "市值无数据")

    if pe is None or pe <= 0:
        reasons.append("亏损(PE≤0)" if pe is not None else "PE无数据")

    if roe is None:
        reasons.append("ROE无数据")
    elif roe < BORDER_ROE_LOW:
        reasons.append(f"ROE={roe:.1f}%<{MIN_ROE}%")
    elif roe < MIN_ROE:
        warnings.append(f"⚠️ROE={roe:.1f}%偏低(阈值{MIN_ROE}%)")

    if rev_yoy is None:
        reasons.append("营收同比无数据")
    elif rev_yoy < BORDER_YOY_LOW:
        reasons.append(f"营收同比={rev_yoy:.1f}%<{MIN_REV_YOY}%")
    elif rev_yoy < MIN_REV_YOY:
        warnings.append(f"⚠️营收同比={rev_yoy:.1f}%偏弱")

    row = {
        "code": code, "name": name, "weight": weight,
        "mc": mc, "pe": pe, "pb": pb, "roe": roe, "rev_yoy": rev_yoy,
        "np_b": float(np_)/1e8 if np_ else None,
        "warnings": warnings
    }

    if reasons:
        row["reason"] = "；".join(reasons)
        failed.append(row)
    else:
        passed.append(row)

passed_sorted = sorted(passed, key=lambda x: x["roe"] or 0, reverse=True)

print(f"\n{'='*70}")
print(f"粗筛结果：{len(codes)}只 → 通过 {len(passed)} 只 → 淘汰 {len(codes)-len(passed)} 只")
print(f"筛选参数: 市值≥{MIN_MC}亿, ROE≥{MIN_ROE}%(边界{BORDER_ROE_LOW:.0f}%), 营收同比≥{MIN_REV_YOY}%, PE>0")
print(f"{'='*70}")

if passed_sorted:
    print(f"\n✅ 通过粗筛（按ROE降序）:")
    print(f"{'公司':<12}{'代码':<12}{'权重%':>6}{'市值亿':>8}{'PE':>7}{'PB':>6}{'ROE%':>7}{'营收同比%':>10}  备注")
    print("-"*80)
    for r in passed_sorted:
        pe_s  = f"{r['pe']:.1f}" if r['pe'] else "N/A"
        pb_s  = f"{r['pb']:.2f}" if r['pb'] else "N/A"
        roe_s = f"{r['roe']:.1f}" if r['roe'] is not None else "N/A"
        yoy_s = f"{r['rev_yoy']:+.1f}" if r['rev_yoy'] is not None else "N/A"
        mc_s  = f"{r['mc']:.0f}" if r['mc'] else "N/A"
        warn  = " ".join(r.get("warnings", []))
        print(f"{r['name']:<12}{r['code']:<12}{r['weight']:>6.2f}{mc_s:>8}{pe_s:>7}{pb_s:>6}{roe_s:>7}{yoy_s:>10}  {warn}")
else:
    print("\n⚠️ 无公司通过粗筛（行业整体ROE极低）")

print(f"\n--- 未通过 (权重≥0.8%) ---")
failed_top = [f for f in sorted(failed, key=lambda x: x["weight"], reverse=True) if f["weight"] >= 0.8]
print(f"{'公司':<12}{'代码':<12}{'权重%':>6}{'ROE%':>7}  淘汰原因")
print("-"*85)
for r in failed_top:
    roe_s = f"{r['roe']:.1f}%" if r['roe'] is not None else "N/A"
    print(f"{r['name']:<12}{r['code']:<12}{r['weight']:>6.2f}{roe_s:>7}  {r['reason']}")

# 额外：显示所有ROE>0的公司（用于参考）
print(f"\n--- 参考：ROE>0的公司（按ROE降序，含未通过粗筛）---")
all_stocks_with_data = [r for r in passed + failed if r.get("roe") is not None and r["roe"] > 0]
all_roe_sorted = sorted(all_stocks_with_data, key=lambda x: x["roe"], reverse=True)
print(f"{'公司':<12}{'代码':<12}{'权重%':>6}{'ROE%':>7}{'PE':>7}  状态")
print("-"*65)
for r in all_roe_sorted[:20]:
    pe_s = f"{r['pe']:.1f}" if r['pe'] else "N/A"
    status = "✅通过" if r in passed_sorted else f"❌{r.get('reason','')[:30]}"
    print(f"{r['name']:<12}{r['code']:<12}{r['weight']:>6.2f}{r['roe']:>7.1f}{pe_s:>7}  {status}")

with open("data/931775_screen.json", "w", encoding="utf-8") as f:
    json.dump({
        "trade_date": trade_date, "annual_date": last_annual,
        "total": len(codes), "passed": passed_sorted,
        "failed_top": [f for f in sorted(failed, key=lambda x: x["weight"], reverse=True) if f["weight"] >= 0.5],
        "all_roe_ranked": all_roe_sorted
    }, f, ensure_ascii=False, indent=2)
print("\n已保存 data/931775_screen.json")
