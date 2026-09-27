import json
from pathlib import Path

root = Path(__file__).parent
data = json.loads((root / 'valuation-input-v1.json').read_text(encoding='utf-8'))
shares = data['shares_m']

def dcf(p):
    cash = p['fcfe_m']; pv = 0.0
    for year in range(1, 6):
        growth = p['growth_1_3'] if year <= 3 else p['growth_4_5']
        cash *= 1 + growth
        pv += cash / (1 + p['ke']) ** year
    terminal = cash * (1 + p['terminal_g']) / (p['ke'] - p['terminal_g'])
    return (pv + terminal / (1 + p['ke']) ** 5) / shares

pe = {k: v['eps'] * v['multiple'] for k, v in data['models']['pe'].items() if k in ('bear', 'base', 'bull')}
dcf_values = {k: dcf(v) for k, v in data['models']['fcfe_dcf'].items() if k in ('bear', 'base', 'bull')}
weighted = {k: pe[k] * 0.45 + dcf_values[k] * 0.55 for k in pe}

base = data['models']['fcfe_dcf']['base']
sensitivity = []
for ke in [0.09, 0.095, 0.10]:
    row = []
    for g in [0.02, 0.025, 0.03]:
        q = dict(base); q['ke'] = ke; q['terminal_g'] = g
        row.append(dcf(q))
    sensitivity.append(row)

market = data['market_snapshot']
price = json.loads((root / 'market-snapshot-v1.json').read_text(encoding='utf-8'))['close_price']
# Solve terminal growth holding the base five-year FCFE path and Ke fixed.
lo, hi = -0.02, base['ke'] - 0.0001
for _ in range(200):
    mid = (lo + hi) / 2
    q = dict(base); q['terminal_g'] = mid
    if dcf(q) < price: lo = mid
    else: hi = mid

out = {'models': {'pe': pe, 'fcfe_dcf': dcf_values}, 'weighted': weighted,
       'dcf_sensitivity': {'x':'terminal_g','x_values':[0.02,0.025,0.03], 'y':'ke','y_values':[0.09,0.095,0.10], 'values':sensitivity},
       'reverse': {'market_price':price,'ke':base['ke'],'implied_terminal_g':(lo+hi)/2,'formula':'solve DCF(g)=market_price with base FCFE path fixed'},
       'buy_price_if_certainty_0_55': weighted['base'] * (0.68 + 0.14 * 0.55)}
(root / 'valuation-output-v1.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=2))
