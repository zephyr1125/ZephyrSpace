"""只读取华明返修输入并写出计算结果，不生成研究报告。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'huaming-revision-inputs.json'
OUTPUT=ROOT/'huaming-revision-calculations.json'

def ddm_two_stage(d1,growth,years,terminal_growth,cost_of_equity):
    pv=sum(d1*(1+growth)**(year-1)/(1+cost_of_equity)**year for year in range(1,years+1))
    dn=d1*(1+growth)**(years-1)
    tv=dn*(1+terminal_growth)/(cost_of_equity-terminal_growth)
    return pv+tv/(1+cost_of_equity)**years

def main():
    x=json.loads(INPUT.read_text(encoding='utf-8-sig'))
    e=x['earnings_bridge']; sh=x['shares']['current_total']; cf=x['cash_flow_bridge']; v=x['valuation']
    ttm=e['fy2025_attributable']-e['h1_2025_attributable']+e['h1_2026_attributable']
    eps=ttm/sh
    ttm_rec=e['fy2025_recurring_attributable']-e['h1_2025_recurring_attributable']+e['h1_2026_recurring_attributable']
    ttm_rec_eps=ttm_rec/sh
    ttm_ocf=cf['fy2025_ocf']-cf['h1_2025_ocf']+cf['h1_2026_ocf']
    ttm_capex=cf['fy2025_cash_capex']-cf['h1_2025_cash_capex']+cf['h1_2026_cash_capex']
    simple_fcf=ttm_ocf-ttm_capex
    pe_value=eps*v['pe']['multiple']
    d=v['ddm']; ddm_value=ddm_two_stage(d['d1'],d['stage1_growth'],d['years'],d['terminal_growth'],d['cost_of_equity'])
    target_raw=pe_value*v['pe']['weight']+ddm_value*d['weight']
    target=round(target_raw,1); certainty=v['certainty']; buy=round(target*(.68+.14*certainty),2)
    scenarios={}
    for name,src in v['scenarios'].items():
        if name=='base':
            s={'eps':eps,'pe_multiple':v['pe']['multiple'],'d1':d['d1'],'stage1_growth':d['stage1_growth'],'years':d['years'],'terminal_growth':d['terminal_growth'],'cost_of_equity':d['cost_of_equity']}
        else: s=src
        pev=s['eps']*s['pe_multiple']; ddmv=ddm_two_stage(s['d1'],s['stage1_growth'],s['years'],s['terminal_growth'],s['cost_of_equity'])
        scenarios[name]={'inputs':s,'pe_value':pev,'ddm_value':ddmv,'weighted_value':pev*v['pe']['weight']+ddmv*d['weight']}
    if abs(scenarios['base']['weighted_value']-target_raw)>1e-12: raise ValueError('基准情景与主估值漂移')
    f=cf['h1_2026_other_financing_payments']; financing=sum(f.values()); lease=f['financing_lease_payment']+f['lease_principal_and_interest']
    h={}
    for issue_ratio in (.05,.10,.15):
        ns=sh*issue_ratio
        for pr in (.8,1.0,1.2):
            ip=target_raw*pr
            h[f'issue_{issue_ratio:.0%}_price_{pr:.0%}']=(target_raw*sh+ip*ns)/(sh+ns)
    c=x['scores']['company']; cs=sum(c['A'])+sum(c['B'])+c['C']+c['D']+sum(c['E'])+sum(c['F']); ms=sum(x['scores']['management'])
    out={'earnings_bridge':{'reported_ttm_attributable_proxy':ttm,'reported_ttm_eps_proxy':eps,'ttm_recurring_attributable_proxy':ttm_rec,'ttm_recurring_eps_proxy':ttm_rec_eps,'h1_effective_tax_rate':e['h1_2026_tax']/e['h1_2026_pbt'],'fy2025_effective_tax_rate':e['fy2025_tax']/e['fy2025_pbt'],'share_payment_policy':e['policy'],'fy2025_payout_ratio':x['dividends']['fy2025_total_dps']/(e['fy2025_attributable']/sh),'h1_2026_proposed_payout_ratio':x['dividends']['h1_2026_proposed_dps']/(e['h1_2026_attributable']/sh)},'cash_flow_diagnostic':{'ttm_ocf':ttm_ocf,'ttm_cash_long_term_asset_purchases':ttm_capex,'ttm_simplified_fcf':simple_fcf,'per_share':simple_fcf/sh,'formal_weight':0},'other_financing_payments':{**f,'total':financing,'lease_related_total':lease},'valuation':{'pe_value':pe_value,'ddm_value':ddm_value,'weights':{'pe':v['pe']['weight'],'ddm':d['weight'],'fcf':0},'weight_sum':v['pe']['weight']+d['weight'],'raw_target':target_raw,'target_price':target,'valuation_certainty':certainty,'buy_price':buy,'deep_discount_boundary':round(buy*.85,2),'base_scenario_matches_main':True},'scenarios':scenarios,'h_share_sensitivity':h,'scores':{'company':cs,'management':ms,'combined':cs+ms}}
    OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
