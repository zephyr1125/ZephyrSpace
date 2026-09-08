# 伊利本轮评分、DDM、敏感性及机械买入价复算。
import json
from pathlib import Path
def ddm(r=.095,g=.03):
 ds=[1.22,1.55]+[1.55*1.06**i for i in range(1,6)]
 rows=[{'year':2026+i,'dps':d,'pv':d/(1+r)**(i+1)} for i,d in enumerate(ds)]
 tv=ds[-1]*(1+g)/(r-g);tvpv=tv/(1+r)**7
 return {'rows':rows,'dividend_pv':sum(x['pv'] for x in rows),'terminal_value':tv,'terminal_pv':tvpv,'value':sum(x['pv'] for x in rows)+tvpv}
def reverse_value(g,eps0=2.07,r=.095,payout=.75,terminal_pe=18,n=10):
 return sum(eps0*(1+g)**t*payout/(1+r)**t for t in range(1,n+1))+eps0*(1+g)**n*terminal_pe/(1+r)**n
lo,hi=-.5,.5
for _ in range(100):
 mid=(lo+hi)/2
 if reverse_value(mid)>26.45: hi=mid
 else:lo=mid
base=ddm();pe=2.07*16;target=round(.6*pe+.4*base['value'],2);certainty=.50
out={'company_score':[8,15,17,13,16,11],'company_total':80,'management_score':[17,19,14,12,8,6,4],'management_total':80,'ddm':base,'ddm_sensitivity':{str(g):ddm(g=g)['value'] for g in [.02,.03,.04]},'pe':pe,'scenarios':{'bear':.6*(1.9*14)+.4*ddm(r=.105,g=.02)['value'],'base':.6*pe+.4*base['value'],'bull':.6*(2.2*17)+.4*ddm(r=.09,g=.035)['value']},'target_price':target,'valuation_certainty':certainty,'buy_price':round(target*(.68+.14*certainty),2),'reverse_growth':(lo+hi)/2,'reverse_prices':{str(g):reverse_value(g) for g in [0,.03,.06]},'pledge_pct':116338449/224756319*100,'fy2025_debt_lower_bound':456.30626028+4.72479633,'fy2025_debt_to_parent_equity_lower_bound':(456.30626028+4.72479633)/546.56,'related_purchase':784505.39/10000}
assert sum(out['company_score'])==out['company_total']
assert sum(out['management_score'])==out['management_total']
print(json.dumps(out,ensure_ascii=False,indent=2))
