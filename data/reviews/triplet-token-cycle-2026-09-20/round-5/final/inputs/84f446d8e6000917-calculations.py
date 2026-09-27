import json
from pathlib import Path
b=json.loads(Path(__file__).parents[1].joinpath('inputs.json').read_text(encoding='utf-8'))
a=b['annual']; x=b['balance_sheet']; x['2025']['equity_consolidated']=253959253909.07
o={}
for y in ('2023','2024','2025'):
 p=str(int(y)-1); aa=(x[y]['assets']+x[p]['assets'])/2; ae=(x[y]['equity_consolidated']+x[p]['equity_consolidated'])/2; n=a[y]['net_profit_consolidated']; r=a[y]['revenue']; o[y]={'formula':'合并净利/收入×收入/平均资产×平均资产/平均合并权益','net_margin':n/r,'asset_turnover':r/aa,'equity_multiplier':aa/ae,'roe':n/ae}
z=json.loads(Path(__file__).with_name('inputs-addendum.json').read_text(encoding='utf-8'))
for y,v in z['targets_vs_actual'].items(): v['target_gap']=v['actual_total_revenue']-v['target_total_revenue']
for y,v in z['dividend_implementation'].items():
 if isinstance(v.get('per10'),list) and isinstance(v.get('share_base'),int): v['cash_dividend']=sum(v['per10'])/10*v['share_base']
Path(__file__).with_name('calculations.json').write_text(json.dumps({'dupont':o,'targets_vs_actual':z['targets_vs_actual'],'dividends':z['dividend_implementation']},ensure_ascii=False,indent=2),encoding='utf-8')
