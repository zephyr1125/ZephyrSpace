"""
Howard Marks style A-share second screening - V2 with calibrated scoring.
Goal: S-tier ~15-20% of passed pool, not 70%.
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.dirname(SCRIPT_DIR)

with open(os.path.join(VAULT_DIR, '_temp_stocks.json'), 'r', encoding='utf-8') as f:
    stocks = json.load(f)

FINANCIAL_INDUSTRIES = {'银行', '证券', '保险', '多元金融', '互联网金融'}

# Industry classifications
CYCLICAL_INDS = {'铝', '铜', '铅锌', '小金属', '黄金', '煤炭开采', '化工原料',
                 '石油加工', '石油开采', '化纤', '钢加工', '水泥', '玻璃',
                 '矿物制品', '橡胶', '塑料', '染料涂料', '船舶', '造纸'}

AI_HOTSPOTS = {'半导体', '元器件', '通信设备', '电脑设备', '软件服务', 'IT设备',
               '互联网', '人工智能', '云计算', '大数据'}

COMPLEX_INDS = {'半导体', '元器件', '通信设备', '软件服务', 'IT设备',
                '医疗保健', '生物制药', '化学制药', '电器仪表'}

# ===== STEP 2: Hard Exclusions =====
excluded = []
passed = []

for s in stocks:
    reasons = []
    is_fin = s.get('industry', '') in FINANCIAL_INDUSTRIES

    # Financial danger
    if s['debt_ratio'] is not None and s['debt_ratio'] > 75 and not is_fin:
        reasons.append(f"资产负债率{s['debt_ratio']:.1f}%>75%")
    if s['roe_annual'] is not None and s['roe_annual'] < 5:
        reasons.append(f"ROE(年化){s['roe_annual']:.1f}%<5%")
    if s['net_margin'] is not None and s['net_margin'] < 3:
        reasons.append(f"净利润率{s['net_margin']:.1f}%<3%")
    if s['rev_growth'] is not None and s['rev_growth'] < -30:
        reasons.append(f"营收增长率{s['rev_growth']:.1f}%<-30%")
    if s['pe'] is not None and s['pe'] <= 0 and s['pe_static'] is not None and s['pe_static'] <= 0:
        reasons.append(f"市盈率为负")
    if s['pb'] is not None and s['pb'] < 0.4 and (s['roe_annual'] is None or s['roe_annual'] < 5):
        reasons.append(f"PB{s['pb']:.2f}<0.4且ROE<5%")

    # Price anomaly
    if s['chg_26w'] is not None and s['chg_26w'] < -60:
        reasons.append(f"26周跌幅{s['chg_26w']:.1f}%<-60%")
    if s['chg_26w'] is not None and s['chg_26w'] > 30:
        reasons.append(f"26周涨幅{s['chg_26w']:.1f}%>30%")

    if reasons:
        s['exclude_reasons'] = reasons
        excluded.append(s)
    else:
        s['exclude_reasons'] = []
        passed.append(s)

print(f"STEP 2: Excluded {len(excluded)}, Passed {len(passed)}")
for s in excluded:
    print(f"  ✗ {s['name']}: {'; '.join(s['exclude_reasons'])}")

# ===== STEP 3: Cheap Reason Classification =====
for s in passed:
    chg = s.get('chg_26w', 0)
    roe_a = s.get('roe_annual', 0)
    rev_g = s.get('rev_growth', 0)
    debt = s.get('debt_ratio', 0)
    nm = s.get('net_margin', 0)
    pe = s.get('pe', 99)
    ind = s.get('industry', '未知')

    # More nuanced classification
    if rev_g is not None and rev_g < -10 and chg is not None and chg < -20:
        reason = '真实恶化'
    elif chg is not None and chg < -15:
        if ind in AI_HOTSPOTS:
            reason = '无法判断'  # tech stocks dropping could be real
        elif roe_a is not None and roe_a >= 10 and rev_g is not None and rev_g >= 0:
            reason = '行业被冷落'  # decent business but price hit hard
        else:
            reason = '短期业绩扰动'
    elif chg is not None and -15 <= chg < 0:
        if pe is not None and pe < 12 and ind not in AI_HOTSPOTS:
            reason = '行业被冷落'  # cheap and neglected
        else:
            reason = '短期业绩扰动'
    elif chg is not None and chg >= 0 and pe is not None and pe < 10:
        reason = '行业被冷落'  # very cheap but market doesn't care
    elif chg is not None and chg >= 5:
        reason = '无法判断'  # not really "neglected"
    else:
        reason = '无法判断'

    s['cheap_reason'] = reason

# ===== STEP 4: Calibrated Scoring =====
for s in passed:
    pe = s.get('pe')
    pb = s.get('pb')
    roe_a = s.get('roe_annual')
    nm = s.get('net_margin')
    rg = s.get('rev_growth')
    dr = s.get('debt_ratio')
    chg = s.get('chg_26w')
    ind = s.get('industry', '未知')
    is_cyclical = ind in CYCLICAL_INDS

    # --- A. Valuation (25 pts) ---
    # Tightened: only deep value gets top marks
    score_a = 0
    if pe is not None and pe > 0:
        if pe <= 8: score_a += 12
        elif pe <= 12: score_a += 9
        elif pe <= 16: score_a += 6
        elif pe <= 20: score_a += 3
        elif pe <= 25: score_a += 1
    if pb is not None:
        if pb <= 0.8: score_a += 8
        elif pb <= 1.2: score_a += 6
        elif pb <= 1.6: score_a += 4
        elif pb <= 2.0: score_a += 2
    # Both cheap
    if pe is not None and pb is not None and pe <= 12 and pb <= 1.5:
        score_a += 5
    elif pe is not None and pb is not None and pe <= 15 and pb <= 1.8:
        score_a += 3
    s['score_a'] = score_a

    # --- B. Quality (25 pts) ---
    score_b = 0
    # ROE (use stricter bands)
    if roe_a is not None:
        if roe_a >= 20: score_b += 12
        elif roe_a >= 15: score_b += 9
        elif roe_a >= 12: score_b += 7
        elif roe_a >= 10: score_b += 4
        elif roe_a >= 8: score_b += 2
    # Net margin
    if nm is not None:
        if nm >= 20: score_b += 8
        elif nm >= 12: score_b += 6
        elif nm >= 8: score_b += 4
        elif nm >= 5: score_b += 2
    # Revenue growth
    if rg is not None:
        if rg >= 10: score_b += 3
        elif rg >= 5: score_b += 2
        elif rg >= 0: score_b += 1
    # Debt discipline
    if dr is not None:
        if dr <= 35: score_b += 2
        elif dr <= 50: score_b += 1
    s['score_b'] = score_b

    # --- C. Mispricing/Cold (20 pts) ---
    score_c = 0
    # 26W drop: significant decline = higher potential mispricing
    if chg is not None:
        if -35 <= chg <= -15: score_c += 10
        elif -15 < chg <= -5: score_c += 7
        elif -5 < chg <= 0: score_c += 4
        elif 0 < chg <= 5: score_c += 2

    # Mispricing quality check: price fell but business OK → likely mispriced
    if chg is not None and chg < -5:
        if roe_a is not None and roe_a >= 12 and rg is not None and rg >= 0:
            score_c += 3  # strong business, selloff likely overdone
        if dr is not None and dr <= 50 and nm is not None and nm >= 8:
            score_c += 2  # balance sheet safe, margins intact

    # Industry cold-shoulder: non-hot industry + cheap valuation
    if ind not in AI_HOTSPOTS and pe is not None and pe <= 12:
        score_c += 2

    # If price rose significantly, reduce score (not neglected)
    if chg is not None and chg > 10:
        score_c = max(0, score_c - 5)

    s['score_c'] = min(20, score_c)

    # --- D. Risk Compensation (20 pts) ---
    score_d = 0

    # Calculate realistic upside/downside
    # Downside: assume PE compresses 30%, earnings drop 20% → ~44% decline
    if pe is not None and pb is not None:
        if pe <= 8 and pb <= 1.2:
            downside = -0.25  # already very cheap, limited downside
            upside = 0.60     # PE reverts to 12, earnings flat
        elif pe <= 10 and pb <= 1.5:
            downside = -0.30
            upside = 0.50
        elif pe <= 12 and pb <= 1.8:
            downside = -0.35
            upside = 0.40
        elif pe <= 15:
            downside = -0.38
            upside = 0.30
        elif pe <= 18:
            downside = -0.40
            upside = 0.20
        else:
            downside = -0.45
            upside = 0.15

        ratio = upside / max(downside, 0.01)
        if ratio >= 2.5: score_d += 10
        elif ratio >= 2.0: score_d += 7
        elif ratio >= 1.5: score_d += 4
        s['upside_ratio'] = round(ratio, 1)
    else:
        s['upside_ratio'] = 1.0

    # Neutral scenario: modest PE expansion + flat earnings
    if pe is not None and pe <= 12 and dr is not None and dr <= 50:
        score_d += 5
    elif pe is not None and pe <= 15 and dr is not None and dr <= 40:
        score_d += 3

    # Pessimistic scenario: won't destroy capital
    if dr is not None and dr <= 45 and pb is not None and pb <= 1.8:
        score_d += 5
    elif dr is not None and dr <= 55 and pb is not None and pb <= 1.5:
        score_d += 3

    s['score_d'] = min(20, score_d)

    # --- E. Researchability (10 pts) ---
    score_e = 0
    if ind not in COMPLEX_INDS:
        score_e += 3
    if nm is not None and roe_a is not None:
        score_e += 2
    score_e += 2  # most A-share industries have trackable data
    if roe_a is not None and roe_a >= 8 and dr is not None and dr <= 55:
        score_e += 2
    if s.get('cheap_reason') != '治理/信披折价':
        score_e += 1
    s['score_e'] = min(10, score_e)

    # --- Total ---
    s['total_score'] = s['score_a'] + s['score_b'] + s['score_c'] + s['score_d'] + s['score_e']

# ===== STEP 5: Tier Assignment =====
for s in passed:
    ts = s['total_score']
    if ts >= 73:
        s['tier'] = 'S'
    elif ts >= 60:
        s['tier'] = 'A'
    elif ts >= 48:
        s['tier'] = 'B'
    else:
        s['tier'] = 'C'

for s in excluded:
    s['tier'] = 'C'
    for field in ['total_score', 'score_a', 'score_b', 'score_c', 'score_d', 'score_e']:
        s[field] = 0
    s['cheap_reason'] = '真实恶化'

all_results = passed + excluded
all_results.sort(key=lambda x: x['total_score'], reverse=True)

from collections import Counter
tc = Counter(s['tier'] for s in all_results)
print(f"\nSTEP 5: S:{tc.get('S',0)} A:{tc.get('A',0)} B:{tc.get('B',0)} C:{tc.get('C',0)}")

# Print all results compactly
print("\n===== FULL RANKINGS =====")
for i, s in enumerate(all_results):
    if s['tier'] in ('S', 'A'):
        print(f" {i+1:2d}. [{s['tier']}] {s['name']:<6s} {s['total_score']:3.0f}分 "
              f"A:{s['score_a']:2d} B:{s['score_b']:2d} C:{s['score_c']:2d} D:{s['score_d']:2d} E:{s['score_e']:2d} | "
              f"PE:{s.get('pe','?')} PB:{s.get('pb','?')} ROE(ann):{s.get('roe_annual','?')}% | "
              f"26W:{s.get('chg_26w','?')}% | {s.get('cheap_reason','')}")

print("\n===== C TIER =====")
for s in all_results:
    if s['tier'] == 'C':
        r = s.get('exclude_reasons', [])
        ts = s['total_score']
        print(f"  {s['name']}: {'; '.join(r) if r else f'总分{ts:.0f}<48'}")

with open(os.path.join(VAULT_DIR, '_temp_results.json'), 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"\nSaved to _temp_results.json")
