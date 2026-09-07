import json
from pathlib import Path
P=Path(__file__).parent
N=882228900
def ddm(d,g,r,tg):
    return sum(d*(1+g)**t/(1+r)**t for t in range(1,11))+d*(1+g)**10*(1+tg)/(r-tg)/(1+r)**10
scenarios=[('保守',.74,16,650000000,.065,.60,.01,.105,.01),('基准',.86,20,760000000,.055,.70,.05,.095,.025),('乐观',.96,24,850000000,.05,.75,.08,.09,.03)]
out=[]
for name,eps,pe,fcf,y,d,g,r,tg in scenarios:
    vals=[eps*pe,fcf/N/y,ddm(d,g,r,tg)]
    out.append(dict(name=name,eps=eps,pe=pe,fcf=fcf,fcf_yield=y,dps0=d,g=g,r=r,terminal_g=tg,pe_value=vals[0],fcf_value=vals[1],ddm_value=vals[2],weighted=sum(a*b for a,b in zip(vals,[.4,.4,.2]))))
target=round(out[1]['weighted'],2)
ttmnp=719117651.30+314952587.39-302763303.99
ttmocf=962109305.17+267305297.13-393495948.73
ttmcapex=46126929.99+31002485.02-23702530.91
hist=[]
rows=[(2021,1812878651.37,511088538.35,482539884.21,578600272.94,101438701.64,3252645512.34,2505260055.55,21.70,51.1483),(2022,2117255683.31,730112737.04,702703789.75,315953616.92,75849221.70,3314919654.11,2649221170.17,29.37,52.9720),(2023,2425394367.14,744834380.64,694724965.06,675345531.69,33660199.21,3424730365.09,2759078140.59,28.77,50.7415),(2024,2310770382.50,649173516.27,628240969.70,877680664.64,19261783.88,3337783990.61,2788004792.81,24.31,50.4283),(2025,2406863327.55,719117651.30,707095126.75,962109305.17,46126929.99,3608191141.96,2926982723.57,26.05,53.9205)]
for yr,rev,np,adj,ocf,cap,ta,eq,roe,gm in rows:
    hist.append(dict(year=yr,revenue=rev,np=np,adjusted_np=adj,ocf=ocf,capex=cap,fcf=ocf-cap,ta=ta,equity=eq,roe=roe,gross_margin=gm,cash_conversion=ocf/np,net_margin=np/rev,turnover=rev/ta,leverage=ta/eq))
bars=json.loads((P/'bars.json').read_text(encoding='utf-8'))['data'][:60]
price=15.89
def implied(g):
    eps=.86;pay=.85;r=.095
    return sum(eps*(1+g)**t*pay/(1+r)**t for t in range(1,11))+eps*(1+g)**10*18/(1+r)**10
lo,hi=-.15,.30
for _ in range(100):
    m=(lo+hi)/2
    if implied(m)>price:hi=m
    else:lo=m
result=dict(shares=N,price=price,target=target,certainty=.68,buy_price=round(target*(.68+.14*.68),2),scenarios=out,historical=hist,ttm_np=ttmnp,ttm_ocf=ttmocf,ttm_capex=ttmcapex,ttm_fcf=ttmocf-ttmcapex,ttm_adjusted_np=707095126.75+293262609.32-295264362.15,implied_growth=(lo+hi)/2,price_60=dict(n=len(bars),first=bars[-1],last=bars[0],min=min(b['low'] for b in bars),max=max(b['high'] for b in bars),return_=price/bars[-1]['close']-1),ddm_sensitivity={str(r):{str(g):ddm(.70,.05,r,g) for g in [.015,.025,.035]} for r in [.085,.095,.105]})
(P/'model.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='historical'},ensure_ascii=False,indent=2))
