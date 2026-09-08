"""只读取华明返修输入并写出计算结果，不生成研究报告。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'huaming-revision-inputs.json'
OUTPUT=ROOT/'huaming-revision-calculations.json'

def ddm(d1,growth,years,terminal_growth,ke):
    pv=sum(d1*(1+growth)**(year-1)/(1+ke)**year for year in range(1,years+1))
    dn=d1*(1+growth)**(years-1)
    return pv+(dn*(1+terminal_growth)/(ke-terminal_growth))/(1+ke)**years

def pe_return_value(g,payout,ke,years,terminal_pe):
    dividends=sum(payout*(1+g)**year/(1+ke)**year for year in range(1,years+1))
    terminal=terminal_pe*(1+g)**years/(1+ke)**years
    return dividends+terminal

def solve_growth(target,payout,ke,years,terminal_pe):
    lo,hi=-.2,.3
    for _ in range(200):
        mid=(lo+hi)/2
        if pe_return_value(mid,payout,ke,years,terminal_pe)<target:lo=mid
        else:hi=mid
    return (lo+hi)/2

def main():
    x=json.loads(INPUT.read_text(encoding='utf-8-sig'));e=x['earnings_bridge'];sh=x['shares']['current_total'];cf=x['cash_flow_bridge'];v=x['valuation'];dv=x['dividends']
    reported_ttm=e['fy2025_attributable']-e['h1_2025_attributable']+e['h1_2026_attributable']
    recurring_ttm=e['formal_recurring_ttm_attributable'];reported_eps=reported_ttm/sh;formal_eps=recurring_ttm/sh
    d=v['ddm'];ddm_value=ddm(d['d1'],d['stage1_growth'],d['years'],d['terminal_growth'],d['cost_of_equity'])
    pe_value=formal_eps*v['pe']['multiple'];wp=v['pe']['weight'];wd=d['weight'];raw=pe_value*wp+ddm_value*wd;target=round(raw,1);certainty=v['certainty'];buy_raw=target*(.68+.14*certainty);buy=round(buy_raw,2)
    ttm_ocf=cf['fy2025_ocf']-cf['h1_2025_ocf']+cf['h1_2026_ocf'];ttm_capex=cf['fy2025_cash_capex']-cf['h1_2025_cash_capex']+cf['h1_2026_cash_capex'];simple=ttm_ocf-ttm_capex
    scenarios={}
    for name,src in v['scenarios'].items():
        if name=='base':s={'eps':formal_eps,'pe_multiple':v['pe']['multiple'],'d1':d['d1'],'stage1_growth':d['stage1_growth'],'years':d['years'],'terminal_growth':d['terminal_growth'],'cost_of_equity':d['cost_of_equity']}
        else:s=src
        ddmv=ddm(s['d1'],s['stage1_growth'],s['years'],s['terminal_growth'],s['cost_of_equity']);scenarios[name]={'inputs':s,'ddm':ddmv,'weighted_value':s['eps']*s['pe_multiple']*wp+ddmv*wd}
    if abs(scenarios['base']['weighted_value']-raw)>1e-12:raise ValueError('基准情景与主估值漂移')
    ddm_grid={str(d1):{str(ke):ddm(d1,.04,5,.025,ke) for ke in (.09,.10,.115)} for d1 in (.42,.50,.56)}
    eps_pe={str(eps):{str(pe):eps*pe*wp+ddm_value*wd for pe in (17,20,23)} for eps in (.74,formal_eps,reported_eps,.90)}
    hs={}
    for ir in (.05,.10,.15):
        hs[str(ir)]={}
        ns=sh*ir
        for pr in (.8,1.0,1.2):
            ip=raw*pr;hs[str(ir)][str(pr)]=(raw*sh+ip*ns)/(sh+ns)
    aging=x['aging_rmb'];above=aging['one_to_two']+aging['two_to_three']+aging['above_three'];prior=aging['prior_above_one_year']
    dup=[]
    for z in x['dupont_history']:
        margin=z['parent_profit']/z['revenue'];turn=z['revenue']/z['assets_end'];lev=z['assets_end']/z['parent_equity_end'];dup.append({**z,'parent_net_margin':margin,'asset_turnover_end_proxy':turn,'assets_to_parent_equity_end_proxy':lev,'roe_end_proxy':margin*turn*lev})
    c=x['scores']['company'];cs=sum(sum(vv) for vv in c.values());ms=sum(x['scores']['management']);f=cf['h1_2026_other_financing_payments']
    payout=d['d1']/formal_eps;bridge=v['pe_return_bridge'];req=solve_growth(v['pe']['multiple'],payout,bridge['cost_of_equity'],bridge['years'],bridge['terminal_pe'])
    bs=x['balance_sheet_h1_2026']
    out={'as_of':x['as_of'],'earnings':{'reported_ttm_parent':reported_ttm,'reported_ttm_eps':reported_eps,'formal_recurring_ttm_parent':recurring_ttm,'formal_eps':formal_eps,'nonrecurring_ttm_parent':reported_ttm-recurring_ttm,'nonrecurring_share':(reported_ttm-recurring_ttm)/reported_ttm,'sbc_kept':True,'tax_nci_adjusted_in_official_recurring_bridge':True},'valuation':{'pe':v['pe']['multiple'],'pe_value':pe_value,'ddm':ddm_value,'d1':d['d1'],'stage1_growth':d['stage1_growth'],'years':d['years'],'terminal_growth':d['terminal_growth'],'ke':d['cost_of_equity'],'pe_weight':wp,'ddm_weight':wd,'fcf_weight':0,'raw_target':raw,'target_price':target,'certainty':certainty,'certainty_components':v['certainty_factors'],'buy_price_raw':buy_raw,'buy_price':buy,'deep_discount':round(buy*.85,2),'d1_payout_formal_eps':payout,'h1_2026_proposed_dps_to_recurring_eps':dv['h1_2026_proposed_dps']/(e['h1_2026_recurring_attributable']/sh)},'pe_return_bridge':{**bridge,'required_annual_growth':req,'computed_pe':pe_return_value(req,payout,bridge['cost_of_equity'],bridge['years'],bridge['terminal_pe'])},'cash_flow_diagnostic':{'ttm_ocf':ttm_ocf,'ttm_cash_long_term_asset_purchases':ttm_capex,'ttm_simplified_fcf':simple,'formal_weight':0},'other_financing_payments':{**f,'total':sum(f.values()),'lease_related_total':f['financing_lease_payment']+f['lease_principal_and_interest']},'dupont_end_balance_proxy':dup,'aging':{**aging,'above_one_year':above,'above_one_year_change':above/prior-1,'above_one_year_ratio':above/aging['gross_total'],'prior_above_one_year_ratio':prior/aging['prior_gross_total']},'scenarios':scenarios,'ddm_sensitivity_fixed_g4_gt2_5_n5':ddm_grid,'eps_pe_sensitivity':eps_pe,'h_share_sensitivity':hs,'scores':{'company':cs,'management':ms,'combined':cs+ms,'company_dimensions':[sum(c[k]) for k in ('A','B','C','D','E','F')],'management_dimensions':x['scores']['management']},'balance_sheet_checks':{**bs,'cash_to_debt':bs['cash_equivalents']/bs['total_debt_including_leases'],'debt_to_parent_equity':bs['total_debt_including_leases']/bs['parent_equity'],'current_debt_share':bs['current_interest_debt_including_current_leases']/bs['total_debt_including_leases']},'checks':{'weights_sum':wp+wd,'base_matches_main':True,'aging_net_bridge':abs(aging['gross_total']-aging['allowance']-aging['net_total'])<.01}}
    OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'scores':out['scores'],'valuation':out['valuation'],'pe_return_bridge':out['pe_return_bridge'],'checks':out['checks']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
