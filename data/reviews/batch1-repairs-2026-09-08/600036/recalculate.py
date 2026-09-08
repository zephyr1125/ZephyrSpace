"""复算招行纠错版；预测其他权益分配独立假设，绝非半年机械年化。"""
import json
from pathlib import Path
shares=252.2
# 归母利润与全年其他权益分配预算，单位亿元；H1已付13.02不能代表全年。
coupons=[430*.0369,300*.0341,300*.0242,200*.0213,270*.0205]
other_distribution=sum(coupons)+3.22
eps=(1630-other_distribution)/shares
dps=eps*.33
pb=45.4
pe=eps*6.4
ddm=dps*1.04/(.09-.04)
dy=dps/.055
weighted=pb*.375+pe*.3125+ddm*.1875+dy*.125
target=round(weighted)
result={'cScore':sum([9,17,16,12,18,13]),'mScore':sum([16,22,13,12,7,8,5]),'coupons':coupons,'other_distribution':other_distribution,'eps':eps,'dps':dps,'pb':pb,'pe':pe,'ddm':ddm,'yield':dy,'weighted':weighted,'target':target,'certainty':.65,'buy':round(target*(.68+.14*.65),2),
 'h1_ordinary_eps':(764.45-3.22-9.80)/shares,
 'dividend_2025':2.016*shares,
 'ddm_sensitivity':{str(ke):[round(dps*(1+g)/(ke-g),2) for g in [.03,.04,.05]] for ke in [.08,.09,.10]},
 'other_distribution_sensitivity':{str(x):round((1630-x)/shares,4) for x in [40,50,60]},
 'eps_pe_sensitivity':{str(e):[round(e*m,2) for m in [5.5,6.4,7.1,8]] for e in [5.9,eps,6.7]},
 'method_scenarios':{'pb':[45.4*x for x in [.9,1,1.1]],'pe':[eps*x for x in [5.6,6.4,7.1]],'ddm':[dps*(1+g)/(.09-g) for g in [.03,.04,.05]],'yield':[dps/x for x in [.06,.055,.05]]},
 'impairment_bridge':[21.22,22.62,1.70],
 'migration_yoy_pp':39.94-28.66,'migration_vs_annual_pp':39.94-40.06}
result['weighted_scenarios']=[sum(result['method_scenarios'][m][i]*w for m,w in [('pb',.375),('pe',.3125),('ddm',.1875),('yield',.125)]) for i in range(3)]
assert abs(sum(result['impairment_bridge'])-45.54)<1e-9
assert target==42
Path(__file__).with_name('calculations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
