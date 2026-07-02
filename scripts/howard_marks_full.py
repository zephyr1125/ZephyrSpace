"""
Howard Marks V5 — same-period PE/ROE with balanced calibration.
- Primary PE: FY2025 static PE (col 3) for valuation, matching ROE period
- TTM PE (col 7) used as auxiliary signal: TTM < static → earnings recovering
- Recalibrated thresholds for static-PE scoring distribution
- Cyclical & consistency flags, not penalties
"""
import json, os, time
from collections import Counter

VAULT_DIR = r'E:\ObsidianVaults\ZephyrSpace'
INPUT_FILE = r'C:\Users\zephy\OneDrive\Desktop\Table.xls'

# ── 1. Parse ──────────────────────────────────────────────────
print("=" * 60)
print("1. PARSING (FY2025 static PE primary)")

def parse_num(s):
    if not s: return None
    s = s.strip()
    if s in ('--', '--', ''): return None
    if s.startswith('--'): s = '-' + s[2:]
    s = s.replace('%', '')
    try: return float(s)
    except ValueError: return None

def parse_mcap(s):
    if not s: return None
    s = s.strip()
    is_wan = '万' in s
    s_clean = s.replace('亿', '').replace('万', '').strip()
    try: val = float(s_clean)
    except ValueError: return None
    if is_wan:
        if val < 100: val = val * 10000
        else: val = val / 10000
    return val

with open(INPUT_FILE, 'r', encoding='gbk') as f:
    lines = f.readlines()

stocks = []
for line in lines[1:]:
    cols = line.strip().split('\t')
    if len(cols) < 10: continue
    try:
        code, name = cols[0].strip(), cols[1].strip()
        price = parse_num(cols[2])
        pe_static = parse_num(cols[3])   # FY2025 static PE
        net_margin = parse_num(cols[4])
        debt_ratio = parse_num(cols[5])
        rev_growth = parse_num(cols[6])
        pe_ttm = parse_num(cols[7])      # TTM dynamic PE
        roe = parse_num(cols[8])         # FY2025 ROE
        pb = parse_num(cols[9])
        mcap = parse_mcap(cols[10]) if len(cols) > 10 else None

        # Primary PE = static (FY2025), matches ROE period
        pe = pe_static if (pe_static and pe_static > 0) else (pe_ttm if (pe_ttm and pe_ttm > 0) else None)

        # Consistency check: PB vs PE × ROE
        # Systematic positive bias (PE×ROE > PB) usually means ROE uses
        # full-company net profit (含少数股东) while PE uses parent net profit (归母).
        # Threshold 25% catches cases beyond normal avg-vs-period-end equity timing.
        implied_roe = None
        consistency_ok = True
        if pe and pe > 0 and pb and pb > 0:
            implied_roe = pb / pe * 100
            if roe and roe > 0:
                dev = abs(implied_roe - roe) / roe
                consistency_ok = dev < 0.25  # tightened from 40% → 25%
            elif roe is not None and roe <= 0:
                consistency_ok = False

        # Earnings trajectory: TTM vs FY2025
        earnings_recovering = False
        if pe_ttm and pe_static and pe_static > 0 and pe_ttm > 0:
            earnings_recovering = pe_ttm < pe_static * 0.85  # TTM PE 15%+ lower = earnings up

        s = {
            'code': code, 'name': name, 'price': price,
            'pe_static': pe_static, 'pe_ttm': pe_ttm, 'pe': pe,
            'net_margin': net_margin, 'debt_ratio': debt_ratio,
            'rev_growth': rev_growth, 'roe': roe,
            'pb': pb, 'mcap': mcap,
            'consistency_ok': consistency_ok,
            'implied_roe': implied_roe,
            'earnings_recovering': earnings_recovering,
        }
        stocks.append(s)
    except Exception as e:
        print(f"  Parse err: {cols[:3]} — {e}")

print(f"Parsed: {len(stocks)} stocks")

# ── 2. Market data ────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. FETCHING (26W base: 2025-12-26)")

import tushare as ts
pro = ts.pro_api()

ts_codes = []
code_to_ts = {}
for s in stocks:
    code = s['code']
    if code.startswith('SH'): ts_c = code[2:] + '.SH'
    elif code.startswith('SZ'): ts_c = code[2:] + '.SZ'
    else: ts_c = None
    if ts_c:
        ts_codes.append(ts_c)
        code_to_ts[s['code']] = ts_c

ind_map = {}
try:
    df_ind = pro.stock_basic(ts_code=','.join(ts_codes), fields='ts_code,industry')
    ind_map = {r['ts_code']: r.get('industry', '未知') for _, r in df_ind.iterrows()}
    print(f"Industries: {len(ind_map)}")
except Exception as e:
    print(f"Industry error: {e}")

price_26w = {}
for i in range(0, len(ts_codes), 30):
    batch = ts_codes[i:i+30]
    try:
        df = pro.daily(ts_code=','.join(batch), trade_date='20251226')
        for _, row in df.iterrows():
            price_26w[row['ts_code']] = float(row['close'])
        time.sleep(0.3)
    except Exception as e:
        print(f"  Batch {i//30+1}: {e}")

for s in stocks:
    ts_c = code_to_ts.get(s['code'])
    s['industry'] = ind_map.get(ts_c, '未知')
    if ts_c and ts_c in price_26w and s['price'] and price_26w[ts_c] > 0:
        s['chg_26w'] = round((s['price'] - price_26w[ts_c]) / price_26w[ts_c] * 100, 2)
    else:
        s['chg_26w'] = None

print(f"26W: {sum(1 for s in stocks if s.get('chg_26w') is not None)}/{len(stocks)}")

# ── 3. Screening ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. SCREENING V5")

FINANCIAL_INDS = {'银行', '证券', '保险', '多元金融', '互联网金融'}
CYCLICAL_INDS = {'铝', '铜', '铅锌', '小金属', '黄金', '煤炭开采', '化工原料',
                 '石油加工', '石油开采', '化纤', '钢加工', '水泥', '玻璃',
                 '矿物制品', '橡胶', '塑料', '染料涂料', '船舶', '造纸', '特种钢'}
AI_HOTSPOTS = {'半导体', '元器件', '通信设备', '电脑设备', '软件服务', 'IT设备',
               '互联网', '人工智能', '云计算', '大数据'}
COMPLEX_INDS = {'半导体', '元器件', '通信设备', '软件服务', 'IT设备',
                '医疗保健', '生物制药', '化学制药', '电器仪表'}

# Hard exclusions
excluded, passed = [], []
for s in stocks:
    reasons = []
    is_fin = s.get('industry', '') in FINANCIAL_INDS
    if s['debt_ratio'] is not None and s['debt_ratio'] > 75 and not is_fin:
        reasons.append(f"资产负债率{s['debt_ratio']:.1f}%>75%")
    if s['roe'] is not None and s['roe'] < 5:
        reasons.append(f"ROE{s['roe']:.1f}%<5%")
    if s['net_margin'] is not None and s['net_margin'] < 3:
        reasons.append(f"净利润率{s['net_margin']:.1f}%<3%")
    if s['rev_growth'] is not None and s['rev_growth'] < -30:
        reasons.append(f"营收增长率{s['rev_growth']:.1f}%<-30%")
    if s['pe'] is not None and s['pe'] <= 0:
        reasons.append(f"市盈率≤0")
    if s['pb'] is not None and s['pb'] < 0.4 and (s['roe'] is None or s['roe'] < 5):
        reasons.append(f"PB{s['pb']:.2f}<0.4且ROE<5%")
    if s['chg_26w'] is not None and s['chg_26w'] < -60:
        reasons.append(f"26周跌幅{s['chg_26w']:.1f}%<-60%")
    if s['chg_26w'] is not None and s['chg_26w'] > 30:
        reasons.append(f"26周涨幅{s['chg_26w']:.1f}%>30%")
    # Non-recurring: implied ROE > 3x reported ROE
    if s.get('implied_roe') and s.get('roe') and s['roe'] > 0:
        if s['implied_roe'] > s['roe'] * 3:
            reasons.append(f'隐含ROE{s["implied_roe"]:.0f}%远超报告ROE{s["roe"]:.0f}%，疑似非经常性损益')
    if reasons:
        s['exclude_reasons'] = reasons
        excluded.append(s)
    else:
        s['exclude_reasons'] = []
        passed.append(s)

print(f"Excluded: {len(excluded)}, Passed: {len(passed)}")
for s in excluded:
    print(f"  ✗ {s['name']}: {'; '.join(s['exclude_reasons'])}")

# Cheap reason (V5.1: "冷落" requires negative 26W; "周期底部" needs cyclical industry)
NON_CYCLICAL_INDS = {'出版业', '水务', '环境保护', '路桥', '港口', '机场', '房产服务',
                     '家用电器', '家居用品', '服饰', '食品', '软饮料', '白酒', '中成药',
                     '医药商业', '化学制药', '生物制药', '医疗保健', '文教休闲', '电信运营',
                     '软件服务', 'IT设备', '互联网', '电器仪表', '商贸代理', '仓储物流',
                     '运输设备', '农用机械', '农药化肥', '农业综合'}

for s in passed:
    chg = s.get('chg_26w', 0) or 0
    roe = s.get('roe', 0) or 0
    rev_g = s.get('rev_growth', 0) or 0
    pe = s.get('pe', 99) or 99
    ind = s.get('industry', '未知')
    is_cyc_ind = ind in CYCLICAL_INDS

    if roe >= 12:
        # Healthy — not real deterioration
        if chg < -15: reason = '行业被冷落'
        elif chg < 0: reason = '行业被冷落' if pe < 18 else '短期业绩扰动'
        else: reason = '无法判断'  # price didn't drop → not "neglected"
    elif roe >= 8:
        if rev_g < -5 and chg < -10: reason = '短期业绩扰动'
        elif chg < -10: reason = '行业被冷落'
        elif chg < 0: reason = '短期业绩扰动'
        elif is_cyc_ind and rev_g < 0: reason = '周期底部'
        else: reason = '无法判断'
    else:
        if rev_g < -10: reason = '真实恶化'
        elif is_cyc_ind and rev_g < 0: reason = '周期底部'
        elif rev_g < 0: reason = '短期业绩扰动'
        else: reason = '短期业绩扰动'
    s['cheap_reason'] = reason

# Scoring (recalibrated for static PE)
for s in passed:
    pe = s.get('pe')
    pb = s.get('pb')
    roe = s.get('roe')
    nm = s.get('net_margin')
    rg = s.get('rev_growth')
    dr = s.get('debt_ratio')
    chg = s.get('chg_26w')
    ind = s.get('industry', '未知')
    is_cyclical = ind in CYCLICAL_INDS
    recovering = s.get('earnings_recovering', False)

    # A: Valuation (25 pts) — relaxed for static PE (FY2025 earnings typically weaker)
    score_a = 0
    if pe is not None and pe > 0:
        if pe <= 9: score_a += 12
        elif pe <= 13: score_a += 9
        elif pe <= 17: score_a += 6
        elif pe <= 22: score_a += 3
        elif pe <= 28: score_a += 1
    if pb is not None:
        if pb <= 0.8: score_a += 8
        elif pb <= 1.2: score_a += 6
        elif pb <= 1.6: score_a += 4
        elif pb <= 2.0: score_a += 2
    if pe is not None and pb is not None and pe <= 14 and pb <= 1.6:
        score_a += 5
    elif pe is not None and pb is not None and pe <= 17 and pb <= 2.0:
        score_a += 3
    # Bonus: earnings recovering (TTM better than FY2025)
    if recovering and pe is not None and pe <= 17:
        score_a += 2
    s['score_a'] = min(25, score_a)

    # B: Quality (25 pts)
    score_b = 0
    if roe is not None:
        if roe >= 20: score_b += 12
        elif roe >= 15: score_b += 9
        elif roe >= 12: score_b += 7
        elif roe >= 10: score_b += 4
        elif roe >= 8: score_b += 2
    if nm is not None:
        if nm >= 20: score_b += 8
        elif nm >= 12: score_b += 6
        elif nm >= 8: score_b += 4
        elif nm >= 5: score_b += 2
    if rg is not None:
        if rg >= 10: score_b += 3
        elif rg >= 5: score_b += 2
        elif rg >= 0: score_b += 1
    if dr is not None:
        if dr <= 35: score_b += 2
        elif dr <= 50: score_b += 1
    # Flag but don't penalize consistency issues heavily
    if not s.get('consistency_ok', True):
        score_b = max(0, score_b - 1)
    s['score_b'] = min(25, score_b)

    # C: Mispricing/Cold (20 pts)
    score_c = 0
    if chg is not None:
        if -35 <= chg <= -15: score_c += 10
        elif -15 < chg <= -5: score_c += 7
        elif -5 < chg <= 0: score_c += 4
        elif 0 < chg <= 5: score_c += 2
    if chg is not None and chg < -5:
        if roe is not None and roe >= 12 and rg is not None and rg >= 0:
            score_c += 3
        if dr is not None and dr <= 50 and nm is not None and nm >= 8:
            score_c += 2
    if ind not in AI_HOTSPOTS and pe is not None and pe <= 17:
        score_c += 2
    # Earnings recovering = market may be underpricing the recovery
    if recovering:
        score_c += 3
    if chg is not None and chg > 10:
        score_c = max(0, score_c - 5)
    s['score_c'] = min(20, score_c)

    # D: Risk Compensation (20 pts)
    score_d = 0
    if pe is not None and pb is not None and pe > 0:
        if pe <= 9 and pb <= 1.3: d, u = 0.25, 0.55
        elif pe <= 12 and pb <= 1.6: d, u = 0.30, 0.45
        elif pe <= 15 and pb <= 2.0: d, u = 0.33, 0.38
        elif pe <= 18: d, u = 0.38, 0.28
        elif pe <= 22: d, u = 0.40, 0.18
        else: d, u = 0.45, 0.12
        if is_cyclical: d = d * 1.25
        ratio = u / max(d, 0.01)
        if ratio >= 2.2: score_d += 10
        elif ratio >= 1.7: score_d += 7
        elif ratio >= 1.3: score_d += 4
        s['upside_ratio'] = round(ratio, 1)
    else:
        s['upside_ratio'] = 1.0

    if pe is not None and pe <= 14 and dr is not None and dr <= 50:
        score_d += 5
    elif pe is not None and pe <= 17 and dr is not None and dr <= 40:
        score_d += 3
    if dr is not None and dr <= 45 and pb is not None and pb <= 1.8:
        score_d += 5
    elif dr is not None and dr <= 55 and pb is not None and pb <= 1.5:
        score_d += 3
    s['score_d'] = min(20, score_d)

    # E: Researchability (10 pts)
    score_e = 0
    if ind not in COMPLEX_INDS: score_e += 3
    if nm is not None and roe is not None: score_e += 2
    score_e += 2
    if roe is not None and roe >= 8 and dr is not None and dr <= 55: score_e += 2
    if s.get('cheap_reason') != '治理/信披折价': score_e += 1
    s['score_e'] = min(10, score_e)

    s['total_score'] = s['score_a'] + s['score_b'] + s['score_c'] + s['score_d'] + s['score_e']
    s['cyclical'] = is_cyclical

# Tiers (recalibrated)
for s in passed:
    ts = s['total_score']
    if ts >= 70: s['tier'] = 'S'
    elif ts >= 58: s['tier'] = 'A'
    elif ts >= 46: s['tier'] = 'B'
    else: s['tier'] = 'C'

for s in excluded:
    s['tier'] = 'C'
    for f in ['total_score','score_a','score_b','score_c','score_d','score_e']:
        s[f] = 0
    s['cheap_reason'] = '真实恶化'
    s['cyclical'] = False

all_results = passed + excluded
all_results.sort(key=lambda x: x['total_score'], reverse=True)

tc = Counter(s['tier'] for s in all_results)
print(f"\nTiers: S:{tc.get('S',0)} A:{tc.get('A',0)} B:{tc.get('B',0)} C:{tc.get('C',0)}")

print("\n── S TIER ──")
for i, s in enumerate([x for x in all_results if x['tier'] == 'S']):
    cyc = '🔄周期' if s.get('cyclical') else ''
    rec = '📈盈利恢复' if s.get('earnings_recovering') else ''
    con = '⚠️口径' if not s.get('consistency_ok', True) else ''
    print(f" {i+1:2d}. {s['name']:<8s} {s['code']:<10s} {s['total_score']:.0f}分 "
          f"PE:{s.get('pe','?'):>5.1f} PB:{s.get('pb','?'):>5.2f} ROE:{s.get('roe','?'):>5.1f}% "
          f"26W:{s.get('chg_26w','?'):>6.1f}% | {s.get('cheap_reason','')} {cyc} {rec} {con}")

print("\n── A TIER ──")
for s in [x for x in all_results if x['tier'] == 'A']:
    cyc = '🔄周期' if s.get('cyclical') else ''
    rec = '📈' if s.get('earnings_recovering') else ''
    con = '⚠️' if not s.get('consistency_ok', True) else ''
    print(f"   {s['name']:<8s} {s['code']:<10s} {s['total_score']:.0f}分 "
          f"PE:{s.get('pe','?'):>5.1f} PB:{s.get('pb','?'):>5.2f} ROE:{s.get('roe','?'):>5.1f}% "
          f"26W:{s.get('chg_26w','?'):>6.1f}% | {s.get('cheap_reason','')} {cyc} {rec} {con}")

print("\n── ⚠️ 口径不一致 ——")
bad = [s for s in all_results if not s.get('consistency_ok', True) and s['tier'] in ('S', 'A', 'B')]
for s in bad:
    print(f"   {s['name']}: PE={s.get('pe')} PB={s.get('pb')} ROE={s.get('roe')}% "
          f"→ 隐含ROE={s.get('implied_roe',0):.0f}%")

print("\n── C TIER ──")
for s in [x for x in all_results if x['tier'] == 'C']:
    rs = s.get('exclude_reasons', [f'总分{s["total_score"]:.0f}<46'])
    print(f"   {s['name']}: {'; '.join(rs)}")

with open(os.path.join(VAULT_DIR, '_temp_results.json'), 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"\n✓ Saved {len(all_results)} results")
