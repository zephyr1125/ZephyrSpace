"""PreBuy data collection for 3 stocks: 601058, 688029, 605090"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os, requests, json
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()
LX_TOKEN = os.getenv('LIXINGER_TOKEN')
LX_BASE = 'https://open.lixinger.com/api'

def lx_post(path, payload):
    r = requests.post(f'{LX_BASE}/{path}', json={**payload, 'token': LX_TOKEN})
    return r.json()

trade_date = "2026-05-07"  # Known good trading day
print(f'Trade date: {trade_date}')

codes = ['601058', '688029', '605090']

# ---- 1. Valuation (PE/PB percentiles) ----
val = lx_post('cn/company/fundamental/non_financial', {
    'stockCodes': codes,
    'startDate': trade_date,
    'endDate': trade_date,
    'metricsList': [
        'pe_ttm', 'pe_ttm.y3.cvpos', 'pe_ttm.y3.q2v', 'pe_ttm.y3.q5v', 'pe_ttm.y3.q8v',
        'pb', 'pb.y3.cvpos', 'pb.y3.q2v', 'pb.y3.q5v', 'pb.y3.q8v', 'mc'
    ]
})
print('\n=== Valuation ===')
val_dict = {}
for d in val.get('data', []):
    code = d.get('stockCode')
    val_dict[code] = d
    print(f"  {code}: pe={d.get('pe_ttm')}, pe_pos={d.get('pe_ttm.y3.cvpos')}, pe_q2v={d.get('pe_ttm.y3.q2v')}, pe_q5v={d.get('pe_ttm.y3.q5v')}, pe_q8v={d.get('pe_ttm.y3.q8v')}")
    print(f"         pb={d.get('pb')}, pb_pos={d.get('pb.y3.cvpos')}, pb_q2v={d.get('pb.y3.q2v')}, pb_q5v={d.get('pb.y3.q5v')}, pb_q8v={d.get('pb.y3.q8v')}")
    print(f"         mc={d.get('mc')} (yuan, /1e8={round(d.get('mc',0)/1e8,1)}yi)")

# ---- 2. Candlestick (recent 90 days for 60 trading days) ----
sixty_ago = (date.today() - timedelta(days=90)).isoformat()
print('\n=== Price (last 60 days) ===')
price_dict = {}
for code in codes:
    r = lx_post('cn/company/candlestick', {
        'stockCode': code,
        'startDate': sixty_ago,
        'endDate': trade_date,
        'type': 'lxr_fc_rights'
    })
    data = sorted(r.get('data', []), key=lambda x: x['date'])
    if data:
        latest = data[-1]
        prices = [d['close'] for d in data]
        high60 = max(d['high'] for d in data)
        low60 = min(d['low'] for d in data)
        price_dict[code] = {
            'price': latest['close'],
            'date': latest['date'],
            'high60': high60,
            'low60': low60,
            'data': data
        }
        print(f"  {code}: price={latest['close']}, date={latest['date']}, high60={high60}, low60={low60}")
        # 30-day change
        if len(data) >= 20:
            p30 = data[-21]['close']
            chg30 = round((latest['close']-p30)/p30*100, 2)
            print(f"         30d_change={chg30}%")

# ---- 3. Financials (annual 2025-12-31 and 2024-12-31 for YoY) ----
print('\n=== Annual Financials (2025) ===')
fs2025 = lx_post('cn/company/fs/non_financial', {
    'stockCodes': codes,
    'date': '2025-12-31',
    'metricsList': ['y.ps.toi.t', 'y.ps.np.t', 'y.bs.ta.t', 'y.bs.tl.t', 'y.ps.cfo.t', 'y.ps.gp.t']
})
fs2024 = lx_post('cn/company/fs/non_financial', {
    'stockCodes': codes,
    'date': '2024-12-31',
    'metricsList': ['y.ps.toi.t', 'y.ps.np.t', 'y.bs.ta.t', 'y.bs.tl.t', 'y.ps.cfo.t', 'y.ps.gp.t']
})
fs2025_dict = {}
fs2024_dict = {}

def get_nested(d, path):
    """Get nested value: d['y']['ps']['toi']['t']"""
    parts = path.split('.')
    cur = d
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur

for d in fs2025.get('data', []):
    code = d.get('stockCode')
    fs2025_dict[code] = d
    rev = get_nested(d, 'y.ps.toi.t')
    np_ = get_nested(d, 'y.ps.np.t')
    ta = get_nested(d, 'y.bs.ta.t')
    tl = get_nested(d, 'y.bs.tl.t')
    cfo = get_nested(d, 'y.ps.cfo.t')
    gp = get_nested(d, 'y.ps.gp.t')
    eq = (ta - tl) if ta and tl else None
    roe = round(np_/eq*100, 2) if np_ and eq else None
    alr = round(tl/ta*100, 2) if ta and tl else None
    gpm = round(gp/rev*100, 2) if gp and rev else None
    print(f"  {code} 2025: rev={rev}, np={np_}, cfo={cfo}, eq={eq}, roe={roe}%, alr={alr}%, gpm={gpm}%")

for d in fs2024.get('data', []):
    code = d.get('stockCode')
    fs2024_dict[code] = d
    rev = get_nested(d, 'y.ps.toi.t')
    np_ = get_nested(d, 'y.ps.np.t')
    ta = get_nested(d, 'y.bs.ta.t')
    tl = get_nested(d, 'y.bs.tl.t')
    eq = (ta - tl) if ta and tl else None
    roe = round(np_/eq*100, 2) if np_ and eq else None
    print(f"  {code} 2024: rev={rev}, np={np_}")

# YoY
print('\n=== YoY Calc ===')
for code in codes:
    d25 = fs2025_dict.get(code, {})
    d24 = fs2024_dict.get(code, {})
    r25 = get_nested(d25, 'y.ps.toi.t')
    r24 = get_nested(d24, 'y.ps.toi.t')
    n25 = get_nested(d25, 'y.ps.np.t')
    n24 = get_nested(d24, 'y.ps.np.t')
    if r25 and r24:
        rev_yoy = round((r25-r24)/abs(r24)*100, 2)
        print(f"  {code} rev_yoy_2025={rev_yoy}%")
    if n25 and n24:
        np_yoy = round((n25-n24)/abs(n24)*100, 2)
        print(f"  {code} np_yoy_2025={np_yoy}%")

# ---- 4. Governance: dividends, pledges, major shareholder changes ----
print('\n=== Dividends ===')
for code in codes:
    r = lx_post('cn/company/dividend', {
        'stockCode': code,
        'startDate': '2022-01-01',
        'endDate': trade_date
    })
    divs = r.get('data', [])
    print(f"  {code}: {len(divs)} dividend records")
    for dv in divs[-3:]:
        print(f"    date={dv.get('date')}, div={dv.get('dividend')}, ratio={dv.get('annualNetProfitDividendRatio')}")

print('\n=== Pledges ===')
for code in codes:
    r = lx_post('cn/company/pledge', {
        'stockCode': code,
        'startDate': '2024-01-01'
    })
    pledges = r.get('data', [])
    active = [p for p in pledges if not p.get('pledgeDischargeDate')]
    print(f"  {code}: {len(pledges)} total pledges, {len(active)} active")
    for p in active[:3]:
        print(f"    pledgor={p.get('pledgor')}, pct={p.get('accumulatedPledgePercentageOfTotalEquity')}, amt={p.get('pledgeAmount')}")

print('\n=== Major Shareholder Changes (6m) ===')
six_months_ago = (date.today() - timedelta(days=180)).isoformat()
for code in codes:
    r = lx_post('cn/company/major-shareholders-shares-change', {
        'stockCode': code,
        'startDate': six_months_ago,
        'endDate': trade_date
    })
    changes = r.get('data', [])
    print(f"  {code}: {len(changes)} major shareholder changes")
    for c in changes[:3]:
        print(f"    name={c.get('shareholderName')}, chg={c.get('changeQuantity')}, ratio={c.get('sharesChangeRatio')}")

print('\n=== Senior Executive Changes (6m) ===')
for code in codes:
    r = lx_post('cn/company/senior-executive-shares-change', {
        'stockCode': code,
        'startDate': six_months_ago,
        'endDate': trade_date
    })
    changes = r.get('data', [])
    print(f"  {code}: {len(changes)} exec changes")
    for c in changes[:3]:
        print(f"    name={c.get('executiveName')}, duty={c.get('duty')}, chg={c.get('changedShares')}, price={c.get('avgPrice')}")

print('\n=== Regulatory Measures ===')
for code in codes:
    r = lx_post('cn/company/measures', {
        'stockCode': code,
        'startDate': '2022-01-01',
        'endDate': trade_date
    })
    items = r.get('data', [])
    print(f"  {code}: {len(items)} measures")
    for m in items[:3]:
        print(f"    date={m.get('date')}, type={m.get('displayTypeText')}, text={m.get('linkText')[:50] if m.get('linkText') else ''}")

print('\n=== Inquiry Letters ===')
for code in codes:
    r = lx_post('cn/company/inquiry', {
        'stockCode': code,
        'startDate': '2022-01-01',
        'endDate': trade_date
    })
    items = r.get('data', [])
    print(f"  {code}: {len(items)} inquiries")
    for i in items[:3]:
        print(f"    date={i.get('date')}, type={i.get('displayTypeText')}, text={i.get('linkText','')[:60]}")

print('\n=== ELR (Unlock Heat) ===')
for code in codes:
    r = lx_post('cn/company/hot/elr', {
        'stockCode': code,
        'date': trade_date
    })
    data = r.get('data', [])
    if data:
        print(f"  {code}: elr_heat={data[0].get('v')}")
    else:
        print(f"  {code}: no elr data")

# ---- 5. Q1 2026 data ----
print('\n=== Q1 2026 Financials ===')
fs_q1 = lx_post('cn/company/fs/non_financial', {
    'stockCodes': codes,
    'date': '2026-03-31',
    'metricsList': ['q.ps.toi.t', 'q.ps.np.t', 'q.bs.ta.t', 'q.bs.tl.t', 'q.ps.cfo.t']
})
for d in fs_q1.get('data', []):
    code = d.get('stockCode')
    rev = get_nested(d, 'q.ps.toi.t')
    np_ = get_nested(d, 'q.ps.np.t')
    ta = get_nested(d, 'q.bs.ta.t')
    tl = get_nested(d, 'q.bs.tl.t')
    cfo = get_nested(d, 'q.ps.cfo.t')
    eq = (ta - tl) if ta and tl else None
    print(f"  {code} Q1 2026: rev={rev}, np={np_}, cfo={cfo}, equity={eq}")

print('\nDONE')
