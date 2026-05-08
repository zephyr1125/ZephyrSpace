#!/usr/bin/env python3
"""国家队增持Top50 量化初筛脚本
筛选条件：PE/PB合理、ROE达标、Q1 2026财报良好、资产负债率健康

有效 fs/non_financial 指标（经实测验证）：
  年报 date=YYYY-12-31: y.ps.toi.t, y.ps.np.t, y.bs.ta.t, y.bs.tl.t, y.ps.ebit.t
  季报 date=YYYY-03-31: q.ps.toi.t, q.ps.np.t, q.bs.ta.t, q.bs.tl.t
  注：不支持 a.*, y.pr.*, y.bs.equity.t, q.ps.ni.t 等；.yoy 后缀接受但返回空值
  ROE 需自行计算：np / (ta - tl)
  YoY 需对比两期数据自行计算

注意：不要在请求头加 Accept-Encoding: gzip（会触发 ValidationError）
注意：mc 字段单位为元，需除以 1e8 换算为亿
注意：数据结构为嵌套 dict，如 d['y']['ps']['toi']['t']
"""
import requests, json, os
from dotenv import load_dotenv

load_dotenv("E:/ObsidianVaults/ZephyrSpace/.env")
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    # 不加 Accept-Encoding: gzip，否则 fs/* 会返回 ValidationError
    resp = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN}, timeout=30)
    return resp.json()

def get_nested(d, *keys, default=None):
    """安全地取嵌套 dict 的值"""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
    return d if d is not None else default

# ───────── 公司列表（部分ticker待验证） ─────────
COMPANIES = [
    ("万里石",   "002785"),
    ("海容冷链", "605050"),
    ("金橙子",   "688291"),
    ("浙江龙盛", "600352"),
    ("中国巨石", "600176"),
    ("泸州老窖", "000568"),
    # 惠华药业 - ticker不确定，跳过
    ("键邦股份", "301316"),
    ("运达股份", "300772"),
    ("久立特材", "002318"),
    ("和林微纳", "688661"),
    ("光力科技", "300480"),
    ("鱼跃医疗", "002223"),
    ("甘李药业", "688374"),   # 待验证
    ("南微医学", "688029"),
    ("四川美丰", "000731"),
    ("圣农发展", "002299"),
    ("学大教育", "000526"),
    ("建设机械", "600984"),
    ("利柏特",   "605167"),
    ("诺邦股份", "301172"),
    ("盛邦安全", "688651"),
    ("上海新阳", "300236"),   # 推测为电子化学品 上海新阳
    ("九丰能源", "605090"),
    ("明阳电气", "301291"),
    ("跃岭股份", "605266"),
    ("安徽合力", "600761"),
    ("道通科技", "688208"),
    ("万凯新材", "301216"),
    ("赛轮轮胎", "601058"),
    ("吴华科技", "603113"),   # 待验证
    ("春风动力", "603129"),
    ("恒玄科技", "688608"),
    ("航民股份", "600987"),
    ("汇成真空", "688003"),
    ("英科医疗", "300677"),
    ("宇新股份", "603910"),
    ("九华旅游", "603199"),
    ("铜牛信息", "300895"),
    ("浙海德曼", "688577"),
    ("首旅酒店", "600258"),
    # 绿昂激光 - ticker不确定，跳过
    ("锐明技术", "002970"),
    ("良信股份", "688073"),
    ("云图控股", "002539"),
    ("桐昆股份", "601233"),   # 推测桐昌=桐昆(化学纤维大厂)
    ("欣旺达",   "300207"),
    ("纳芯微",   "688052"),
    ("中颖电子", "300327"),
    ("海目星",   "688113"),
]

codes = [c[1] for c in COMPANIES]
code_to_name = {c[1]: c[0] for c in COMPANIES}

TRADE_DATE   = "2026-05-07"
ANNUAL_2025  = "2025-12-31"
ANNUAL_2024  = "2024-12-31"
Q1_2026      = "2026-03-31"
Q1_2025      = "2025-03-31"

print(f"共 {len(codes)} 家公司，开始批量拉取数据...\n")

# ── 1. 估值：PE/PB/市值（当前）──────────────
print("► 拉取估值数据 (PE/PB/MC)...")
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes, "date": TRADE_DATE, "metricsList": ["pe_ttm", "pb", "mc"]
})
val_data = {d["stockCode"]: d for d in val_resp.get("data", [])}
print(f"  返回 {len(val_data)} 条")

# ── 2. FY2025 年报：营收/净利/总资产/总负债 ──
print("► 拉取FY2025年报...")
ann25_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes, "date": ANNUAL_2025,
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "y.bs.ta.t", "y.bs.tl.t"]
})
ann25 = {d["stockCode"]: d for d in ann25_resp.get("data", [])}
print(f"  返回 {len(ann25)} 条")

# ── 3. FY2024 年报：营收/净利（用于 YoY）──
print("► 拉取FY2024年报（用于YoY基准）...")
ann24_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes, "date": ANNUAL_2024,
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "y.bs.ta.t", "y.bs.tl.t"]
})
ann24 = {d["stockCode"]: d for d in ann24_resp.get("data", [])}
print(f"  返回 {len(ann24)} 条")

# ── 4. Q1 2026 季报 ──────────────────────────
print("► 拉取Q1 2026季报...")
q126_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes, "date": Q1_2026,
    "metricsList": ["q.ps.toi.t", "q.ps.np.t", "q.bs.ta.t", "q.bs.tl.t"]
})
q126 = {d["stockCode"]: d for d in q126_resp.get("data", [])}
print(f"  返回 {len(q126)} 条")

# ── 5. Q1 2025 季报（用于 YoY）────────────
print("► 拉取Q1 2025季报（用于YoY基准）...")
q125_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes, "date": Q1_2025,
    "metricsList": ["q.ps.toi.t", "q.ps.np.t"]
})
q125 = {d["stockCode"]: d for d in q125_resp.get("data", [])}
print(f"  返回 {len(q125)} 条\n")

def yoy(cur, prev):
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100, 1)

# ── 筛选 ─────────────────────────────────────
THRESHOLDS = {
    "pe_max": 60,          # PE TTM 上限（<=0 代表亏损，直接排除）
    "pb_max": 8,           # PB 上限
    "mc_min": 15,          # 市值下限（亿）
    "roe_min": 8,          # ROE % 下限（年报，自算）
    "q1_rev_yoy_min": -20, # Q1营收同比下限 %
    "q1_np_yoy_min": -40,  # Q1净利同比下限 %
    "alr_max": 75,         # 资产负债率上限 %
}

print("=" * 125)
header = (f"{'代码':<8} {'名称':<8} {'PE':>7} {'PB':>6} {'市值亿':>8} "
          f"{'ROE%':>7} {'Q1营收YoY':>10} {'Q1利润YoY':>10} {'Q1ALR%':>7}  结论")
print(header)
print("-" * 125)

passed = []
failed = []

def fmt(v, spec=".1f", unit=""):
    return f"{v:{spec}}{unit}" if v is not None else "N/A"

for name, code in COMPANIES:
    vd  = val_data.get(code, {})
    a25 = ann25.get(code, {})
    a24 = ann24.get(code, {})
    q26 = q126.get(code, {})
    q25 = q125.get(code, {})

    pe  = vd.get("pe_ttm")
    pb  = vd.get("pb")
    mc  = vd.get("mc")
    mc_yi = round(mc / 1e8, 1) if mc else None  # 元→亿

    # ROE 自算：FY2025 净利 / (FY2025 总资产 - FY2025 总负债)
    np25 = get_nested(a25, 'y', 'ps', 'np', 't')
    ta25 = get_nested(a25, 'y', 'bs', 'ta', 't')
    tl25 = get_nested(a25, 'y', 'bs', 'tl', 't')
    equity25 = (ta25 - tl25) if (ta25 and tl25) else None
    roe = round(np25 / equity25 * 100, 1) if (np25 is not None and equity25 and equity25 > 0) else None

    # Q1 2026 营收 / 净利
    q26_rev = get_nested(q26, 'q', 'ps', 'toi', 't')
    q26_np  = get_nested(q26, 'q', 'ps', 'np', 't')
    q26_ta  = get_nested(q26, 'q', 'bs', 'ta', 't')
    q26_tl  = get_nested(q26, 'q', 'bs', 'tl', 't')
    alr = round(q26_tl / q26_ta * 100, 1) if (q26_ta and q26_tl and q26_ta > 0) else None

    # Q1 YoY（手动对比）
    q25_rev = get_nested(q25, 'q', 'ps', 'toi', 't')
    q25_np  = get_nested(q25, 'q', 'ps', 'np', 't')
    q1_rev_yoy = yoy(q26_rev, q25_rev)
    q1_np_yoy  = yoy(q26_np,  q25_np)

    reasons = []
    if pe is None or pe <= 0:
        reasons.append("亏损/无PE")
    elif pe > THRESHOLDS["pe_max"]:
        reasons.append(f"PE={pe:.0f}偏高")

    if pb is None or pb <= 0:
        reasons.append("无PB")
    elif pb > THRESHOLDS["pb_max"]:
        reasons.append(f"PB={pb:.1f}偏高")

    if mc_yi is None or mc_yi < THRESHOLDS["mc_min"]:
        reasons.append(f"市值{mc_yi:.0f}亿过小" if mc_yi else "无市值")

    if roe is None:
        reasons.append("无ROE数据")
    elif roe < THRESHOLDS["roe_min"]:
        reasons.append(f"ROE={roe:.1f}%不足")

    if q1_rev_yoy is not None and q1_rev_yoy < THRESHOLDS["q1_rev_yoy_min"]:
        reasons.append(f"Q1营收YoY={q1_rev_yoy:.1f}%")

    if q1_np_yoy is not None and q1_np_yoy < THRESHOLDS["q1_np_yoy_min"]:
        reasons.append(f"Q1利润YoY={q1_np_yoy:.1f}%")

    if alr is not None and alr > THRESHOLDS["alr_max"]:
        reasons.append(f"ALR={alr:.1f}%偏高")

    if q26_np is not None and q26_np <= 0:
        reasons.append("Q1亏损")

    ok = len(reasons) == 0
    verdict = "✓" if ok else f"✗ {', '.join(reasons[:2])}"

    row = (f"{code:<8} {name:<8} {fmt(pe):>7} {fmt(pb,'.2f'):>6} {fmt(mc_yi,'.0f'):>8} "
           f"{fmt(roe):>7} {fmt(q1_rev_yoy,'.1f','%'):>10} {fmt(q1_np_yoy,'.1f','%'):>10} "
           f"{fmt(alr,'.1f','%'):>7}  {verdict}")
    print(row)

    if ok:
        passed.append({
            "code": code, "name": name,
            "pe": pe, "pb": pb, "mc_yi": mc_yi, "roe": roe,
            "q1_rev_yoy": q1_rev_yoy, "q1_np_yoy": q1_np_yoy, "alr": alr,
        })
    else:
        failed.append({"code": code, "name": name, "reasons": reasons})

print("=" * 125)
print(f"\n✓ 通过筛选：{len(passed)} 家 | ✗ 淘汰：{len(failed)} 家\n")

print("═" * 70)
print("通过筛选的公司（按ROE降序）：")
print("═" * 70)
passed.sort(key=lambda x: -(x["roe"] or 0))
for i, c in enumerate(passed, 1):
    print(f"{i:2}. {c['code']} {c['name']:8}  PE={fmt(c['pe'])}, PB={fmt(c['pb'],'.2f')}, "
          f"MC={fmt(c['mc_yi'],'.0f')}亿, ROE={fmt(c['roe'])}%, "
          f"Q1营收YoY={fmt(c['q1_rev_yoy'],'.1f','%')}, "
          f"Q1利润YoY={fmt(c['q1_np_yoy'],'.1f','%')}, ALR={fmt(c['alr'],'.1f','%')}")

print(f"\n将对以上 {len(passed)} 家公司进行 PreBuy 分析。")

