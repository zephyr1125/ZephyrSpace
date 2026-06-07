"""
Rank 52 defense/military stocks by preliminary quality using CNINFO data.
Scoring dimensions: ROE, Revenue Growth, Net Margin, Cash Flow Quality, Debt Level
"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.cninfo_api import CninfoClient
import pandas as pd
import numpy as np

# Stock mapping
STOCKS = {
    '中航沈飞': '600760', '中航西飞': '000768', '中航成飞': '002190',
    '航发动力': '600893', '航发科技': '600391', '航宇科技': '688239',
    '佳驰科技': '688629', '华秦科技': '688281', '光启技术': '002625',
    '中无人机': '688297', '航天彩虹': '002389', '洪都航空': '600316',
    '七一二': '603712', '海格通信': '002465', '新劲刚': '300629',
    '菲利华': '300395', '新雷能': '300593', '成都华微': '688709',
    '中科星图': '688568', '拓尔思': '300229', '能科科技': '603859',
    '兴图新科': '688081', '华如科技': '301302', '观想科技': '301213',
    '晶品特装': '688084', '光电股份': '600184', '建设工业': '002265',
    '中兵红箭': '000519', '北方导航': '600435', '长盈通': '688143',
    '广联航空': '300900', '芯动联科': '688582', '国泰集团': '603977',
    '北化股份': '002246', '国科军工': '688543',
    '四川九洲': '000801', '航天南湖': '688552', '四创电子': '600990',
    '锐科激光': '300747', '联创光电': '600363', '长光华芯': '688048',
    '国光电气': '688776', '六九一二': '301592',
    '湘电股份': '600416', '王子新材': '002735', '中国海防': '600764',
    '中科海讯': '300810', '集智股份': '300553', '西部材料': '002149',
    '金天钛业': '688750', '高德红外': '002414', '国睿科技': '600562',
}

# Scoring weights
W_ROE = 0.30
W_GROWTH = 0.20
W_MARGIN = 0.20
W_CFO = 0.15
W_DEBT = 0.10
W_SIZE = 0.05

client = CninfoClient()
results = []

print(f"Pulling data for {len(STOCKS)} stocks...")
print("Each dot = 1 stock, 'x' = no TTM data, '-' = failed completely")

for i, (name, code) in enumerate(STOCKS.items()):
    try:
        # Get TTM indicators (most efficient for latest snapshot)
        ttm_df = client.ttm_indicators(code, latest_only=True)

        if ttm_df.empty:
            sys.stdout.write('x')
            sys.stdout.flush()
            continue

        ttm = ttm_df.iloc[0].to_dict()

        # Get multi-year for trend analysis (last 3 years)
        fin_df = client.financial_multi_year(code, years=[2023, 2024, 2025])

        # Extract metrics
        roe_ttm = float(ttm.get('净资产收益率(%)', 0) or 0)
        revenue_growth = float(ttm.get('营业收入增长率(%)', 0) or 0)
        net_margin = float(ttm.get('净利润率(%)', 0) or 0)
        gross_margin = float(ttm.get('毛利率(%)', 0) or 0)
        cfo_ratio = float(ttm.get('经营现金流/净利润(%)', 0) or 0)
        eps = float(ttm.get('基本每股收益(元)', 0) or 0)

        # Multi-year: get average ROE and revenue growth trend
        avg_roe_3yr = roe_ttm  # default fallback
        rev_cagr = revenue_growth  # default fallback
        debt_ratio = 50  # default

        if not fin_df.empty:
            # Average ROE over available years
            roe_col = fin_df.columns[fin_df.columns.str.contains('净资产收益率')].tolist()
            if roe_col:
                roes = pd.to_numeric(fin_df[roe_col[0]], errors='coerce').dropna()
                if len(roes) >= 2:
                    avg_roe_3yr = roes.mean()

            # Revenue growth trend
            rev_col = fin_df.columns[fin_df.columns.str.contains('营业收入增长率')].tolist()
            if rev_col:
                revs = pd.to_numeric(fin_df[rev_col[0]], errors='coerce').dropna()
                if len(revs) >= 2:
                    rev_cagr = revs.mean()

            # Debt ratio
            debt_col = fin_df.columns[fin_df.columns.str.contains('资产负债率')].tolist()
            if debt_col:
                debts = pd.to_numeric(fin_df[debt_col[0]], errors='coerce').dropna()
                if len(debts) > 0:
                    debt_ratio = debts.iloc[0]

        data = {
            'name': name,
            'code': code,
            'roe_ttm': roe_ttm,
            'avg_roe_3yr': avg_roe_3yr,
            'revenue_growth': revenue_growth,
            'rev_cagr_3yr': rev_cagr,
            'net_margin': net_margin,
            'gross_margin': gross_margin,
            'cfo_ratio': cfo_ratio,
            'debt_ratio': debt_ratio,
            'eps': eps,
        }
        results.append(data)
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(0.25)  # Rate limit
    except Exception as e:
        sys.stdout.write('-')
        sys.stdout.flush()
        time.sleep(0.5)

print(f"\n\nGot data for {len(results)}/{len(STOCKS)} stocks")

# ── Scoring ──
def percentile_score(values, reverse=False):
    """Convert values to 0-100 percentile scores"""
    arr = np.array(values, dtype=float)
    arr = np.nan_to_num(arr, nan=np.nanmean(arr) if not np.all(np.isnan(arr)) else 0)
    if reverse:
        arr = -arr
    if arr.std() == 0:
        return np.full_like(arr, 50.0)
    from scipy import stats
    percentiles = stats.rankdata(arr) / len(arr) * 100
    return percentiles

# Calculate scores
names = [r['name'] for r in results]
roes = [r['avg_roe_3yr'] for r in results]
growths = [r['rev_cagr_3yr'] for r in results]
margins = [r['net_margin'] for r in results]
cfos = [r['cfo_ratio'] for r in results]
debts = [r['debt_ratio'] for r in results]
caps = [abs(r['roe_ttm']) * float(r.get('eps', 1) or 1) * 10 for r in results]  # crude size proxy

roes_s = percentile_score(roes)
growths_s = percentile_score(growths)
margins_s = percentile_score(margins)
cfos_s = percentile_score(cfos)
debts_s = percentile_score(debts, reverse=True)  # lower debt = higher score
caps_s = percentile_score(caps)

for i, r in enumerate(results):
    total = (roes_s[i] * W_ROE + growths_s[i] * W_GROWTH +
             margins_s[i] * W_MARGIN + cfos_s[i] * W_CFO +
             debts_s[i] * W_DEBT + caps_s[i] * W_SIZE)
    r['score'] = round(total, 1)
    r['score_roe'] = round(roes_s[i], 1)
    r['score_growth'] = round(growths_s[i], 1)
    r['score_margin'] = round(margins_s[i], 1)
    r['score_cfo'] = round(cfos_s[i], 1)
    r['score_debt'] = round(debts_s[i], 1)

# Sort by total score descending
results.sort(key=lambda x: x['score'], reverse=True)

# ── Output ──
print("\n" + "=" * 90)
print(f"{'Rank':<5} {'Stock':<12} {'Score':<8} {'ROE%':<8} {'RevGr%':<8} {'NetM%':<8} {'OCF/NI%':<8} {'Debt%':<7}")
print("=" * 90)

for i, r in enumerate(results):
    rank = i + 1
    score_str = f"{r['score']:.1f}"
    # Tier marker
    if r['score'] >= 70:
        tier = 'A'
    elif r['score'] >= 55:
        tier = 'B'
    elif r['score'] >= 40:
        tier = 'C'
    else:
        tier = 'D'

    print(f"{rank:<5} {r['name']:<12} {score_str:<8} {r['avg_roe_3yr']:<8.1f} {r['rev_cagr_3yr']:<8.1f} {r['net_margin']:<8.1f} {r['cfo_ratio']:<8.0f} {r['debt_ratio']:<7.1f}  [{tier}]")

print("=" * 90)
print(f"\nTiers: A>=70 (Quality)  B>=55 (Above Avg)  C>=40 (Average)  D<40 (Below Avg)")
print(f"Scoring weights: ROE {W_ROE*100:.0f}% | Growth {W_GROWTH*100:.0f}% | Margin {W_MARGIN*100:.0f}% | OCF {W_CFO*100:.0f}% | Debt {W_DEBT*100:.0f}% | Size {W_SIZE*100:.0f}%")

# Save detailed data
with open('scripts/defense_stocks_ranking.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nDetailed data saved to scripts/defense_stocks_ranking.json")
