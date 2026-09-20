"""修复复查独立复算；只读输入，不导入或运行作者脚本。"""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
d=json.loads((p/'repair-1/valuation-input.json').read_text(encoding='utf-8'))
n=d['shares']['external']; fx=d['fx']['hkd_to_cny']; hist=d['history']['h1_2026']
actual_h1=hist['operating_ebit']*(1-hist['tax_rate'])+hist['da']-hist['capex']-hist['delta_nwc']
def calc(s, subtract_h1=False):
    rev=d['history']['fy2025']['revenue']; flows=[]; nopats=[]
    for i in range(5):
        old=rev; rev*=1+s['revenue_growth'][i]
        no=rev*s['ebit_margin'][i]*(1-s['tax_rate']); nopats.append(no)
        flows.append(no+rev*.024-rev*s['capex_pct_revenue'][i]-(rev-old)*s['nwc_pct_incremental_revenue'])
    h2=flows[0]-actual_h1 if subtract_h1 else flows[0]/2
    before=h2*77/184; future=h2*107/184
    t=107/184/2; w=s['wacc']; g=s['g']
    exp=future/(1+w)**t+sum(flows[i]/(1+w)**(i+t) for i in range(1,5))
    tv=nopats[-1]*(1+g)*(1-g/s['terminal_roic'])/(w-g)/(1+w)**(4+t)
    c=d['cash_bridge_2026_06_30']
    cash=c['selected_assets']-c['debt_and_leases']-c['operating_buffer']-c['nci']-c['interim_dividend']+c['debt_in_other_noncurrent_financial_assets']+c['private_fund_book_value']*(1-s['fund_haircut'])+before
    return {'annual_fcff':flows[0],'h1_proxy':flows[0]/2,'h2':h2,'pre_date_fcff':before,'ev':exp+tv,'cash':cash,'hkd':(exp+tv+cash)/n/fx}
u=d['comparables']['unipresident']; uprofit=sum(sign*(u[k+'_profit']-u[k+'_other_gains']*(1-u[k+'_tax_rate'])) for k,sign in [('fy25',1),('h1_26',1),('h1_25',-1)])
t=d['comparables']['tingyi']; a=t['shares']*t['price_hkd']*fx/t['normalized_ttm_profit_cny']; b=u['shares']*u['price_hkd']*fx/uprofit
out={'h1_from_author_history_fcff':actual_h1,'unified_normalized_ttm':uprofit,'peer_pes':[a,b],'scenarios':{}}
for name,m in zip(['bear','base','bull'],[min(a,b),(a+b)/2,max(a,b)]):
    raw=calc(d['scenarios'][name]); corrected=calc(d['scenarios'][name],True)
    pe=d['comparables']['eastroc_normalized_ttm_profit']*m/n/fx
    value=.55*raw['hkd']+.45*pe
    out['scenarios'][name]={'raw':raw,'using_h1_history':corrected,'pe_hkd':pe,'combined':value,'combined_using_h1_history':.55*corrected['hkd']+.45*pe,'buy':value*(.68+.14*.52)}
out['profit_growth_fy2025']=4415263147.79/3326708852.44-1
print(json.dumps(out,ensure_ascii=False,indent=2))
