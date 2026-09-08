"""Samsara 三情景股东现金流估值，金额单位为百万美元。"""
import json
from pathlib import Path

BASE_REVENUE = 2045.0
SHARES = 593.0
SURPLUS_CASH = 1325.710 - 100.0
SCENARIOS = {
    "悲观": {"growth": [.20,.18,.16,.14,.12,.10,.08,.06,.05,.04], "margin": [-.03,-.01,.01,.03,.05,.07,.09,.11,.12,.12], "r": .13, "g": .025, "weight": .30},
    "基准": {"growth": [.26,.24,.22,.20,.18,.16,.14,.12,.10,.08], "margin": [0,.03,.06,.09,.12,.15,.17,.18,.19,.20], "r": .115, "g": .03, "weight": .50},
    "乐观": {"growth": [.30,.28,.26,.24,.22,.20,.18,.16,.14,.12], "margin": [.03,.06,.10,.14,.18,.21,.24,.26,.27,.28], "r": .10, "g": .035, "weight": .20},
}

def calculate(s, r=None, g=None, margin_shift=0, growth_shift=0):
    r = s['r'] if r is None else r
    g = s['g'] if g is None else g
    rev = BASE_REVENUE
    rows = []
    for i, (growth, margin) in enumerate(zip(s['growth'], s['margin']), 1):
        rev *= 1 + growth + growth_shift
        cash = rev * (margin + margin_shift)
        # 首笔现金流约在估值日起 1.4 年后；此后逐年折现。
        exponent = i + .4
        rows.append({'fy': 2027+i, 'growth': growth+growth_shift, 'revenue': rev, 'margin': margin+margin_shift, 'cash': cash, 'pv': cash/(1+r)**exponent})
    tv = rows[-1]['cash']*(1+g)/(r-g)
    tv_pv = tv/(1+r)**10.4
    operating_value = sum(x['pv'] for x in rows)+tv_pv
    return {'rows': rows,'terminal_pv':tv_pv,'operating_value':operating_value,'equity_value':operating_value+SURPLUS_CASH,'price':(operating_value+SURPLUS_CASH)/SHARES,'terminal_weight':tv_pv/operating_value}

if __name__ == '__main__':
    out = {k: calculate(v) for k,v in SCENARIOS.items()}
    fair = sum(out[k]['price']*s['weight'] for k,s in SCENARIOS.items())
    result = {'assumptions': SCENARIOS, 'scenarios':out,'target_price':round(fair,2),'valuation_certainty':.45,'buy_price':round(round(fair,2)*(.68+.14*.45),2)}
    Path(__file__).with_name('valuation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:round(v['price'],2) for k,v in out.items()},ensure_ascii=False))
    print('加权合理价',result['target_price'],'机械买入价',result['buy_price'])
    for r in [.10,.115,.13]:
        print('折现率',r,[round(calculate(SCENARIOS['基准'],r=r,g=g)['price'],2) for g in [.025,.03,.035]])
    lo,hi=-.05,.20
    for _ in range(80):
        mid=(lo+hi)/2
        if calculate(SCENARIOS['基准'],growth_shift=mid)['price']<40.2:lo=mid
        else:hi=mid
    print('现价隐含各年增速上移百分点',round(mid*100,2))
