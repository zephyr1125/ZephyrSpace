import json
from pathlib import Path
d=json.loads(Path(__file__).with_name('inputs.json').read_text(encoding='utf-8'))
out={'schema_version':1,'unit':'yuan','calculations':{}}
for y in ('2023','2024','2025'):
    p=str(int(y)-1); b=d['balance_sheet']; a=d['annual']
    if b[y]['equity_consolidated'] is None:
        out['calculations'][f'MT-R5-CALC-DUPONT-{y}']={'status':'not_calculated','reason':'合并权益期末原值未提取，禁止以归母权益替代'}; continue
    aa=(b[y]['assets']+b[p]['assets'])/2; ae=(b[y]['equity_consolidated']+b[p]['equity_consolidated'])/2; n=a[y]['net_profit_consolidated']; r=a[y]['revenue']
    out['calculations'][f'MT-R5-CALC-DUPONT-{y}']={'formula':'合并净利/营业收入×营业收入/平均合并资产×平均合并资产/平均合并权益','net_margin':n/r,'asset_turnover':r/aa,'equity_multiplier':aa/ae,'roe':n/ae}
for y,v in d['operating'].items(): out['calculations'][f'MT-R5-CALC-REV-EMP-{y}']={'formula':'营业收入/员工数','value':d['annual'][y]['revenue']/v['employees']}
Path(__file__).with_name('calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
