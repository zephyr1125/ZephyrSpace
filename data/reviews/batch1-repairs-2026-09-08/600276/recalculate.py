"""恒瑞校准修复估值复算；金额亿元、每股港元，参数为明确研究假设。"""
import json
from pathlib import Path
H1_ADJUSTED=37.295890287
H1_LICENSE=14.22
SHARES=66.37199874
FX=1.10
TAX=0.15
CERTAINTY=0.40
rows=[]
for name,license,pe in [('保守',15,27),('基准',20,30),('乐观',25,33)]:
    profit=H1_ADJUSTED*2-(H1_LICENSE*2-license)*(1-TAX)
    eps=profit*FX/SHARES
    rows.append(dict(scenario=name,license_revenue=license,normal_profit=profit,eps_hkd=eps,pe=pe,value=eps*pe))
target=round(rows[1]['value'],2)
eps=rows[1]['eps_hkd']
def value(g,payout):
    return sum(eps*(1+g)**t*payout/1.1**t for t in range(1,11))+18*eps*(1+g)**10/1.1**10
roots={}
for payout in [0,0.172,0.30]:
    lo,hi=-0.5,1.0
    for _ in range(100):
        mid=(lo+hi)/2
        if value(mid,payout)>46.32:hi=mid
        else:lo=mid
    roots[str(payout)]=(lo+hi)/2
result=dict(scenarios=rows,target_price=target,valuation_certainty=CERTAINTY,buy_price=round(target*(.68+.14*CERTAINTY),2),inverse_growth=roots)
if __name__=='__main__':
    print(json.dumps(result,ensure_ascii=False,indent=2))
