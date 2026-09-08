"""只读取康臣返修输入并写出计算结果，不生成研究报告。"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def ddm(p: dict) -> dict:
    ds=[p["d0"]*(1+p["stage1_growth"])**i for i in range(1,p["years"]+1)]
    pv1=sum(x/(1+p["discount_rate"])**i for i,x in enumerate(ds,1))
    tv=ds[-1]*(1+p["terminal_growth"])/(p["discount_rate"]-p["terminal_growth"])
    return {"dividends":ds,"pv_stage1":pv1,"terminal_value":tv,"pv_terminal":tv/(1+p["discount_rate"])**p["years"],"value":pv1+tv/(1+p["discount_rate"])**p["years"]}

def main() -> None:
    x=json.loads((ROOT/'consun-revision-inputs.json').read_text(encoding='utf-8'))
    e=x['earnings_bridge_rmb']
    after_tax_fvpl=e['remove_fvpl_gain_pre_tax']*(1-e['normalization_tax_rate'])
    normalized_profit=e['ttm_attributable_profit']-after_tax_fvpl
    eps_cny=normalized_profit/e['diluted_shares']
    eps_hkd=eps_cny*e['hkd_per_rmb_assumption']
    d={k:ddm(v) for k,v in x['ddm'].items()}
    pe=eps_hkd*x['pe_multiple']
    target_raw=pe*x['formal_weights']['normalized_pe']+d['base']['value']*x['formal_weights']['ddm']
    target=round(target_raw,1)
    buy=round(target*(.68+.14*x['valuation_certainty']),2)
    scenarios={}
    for key in ('bear','base','bull'):
        ps=x['pe_scenarios'][key]
        scenario_eps=eps_hkd if ps['eps_hkd'] is None else ps['eps_hkd']
        pe_value=scenario_eps*ps['multiple']
        scenarios[key]={"pe_value":pe_value,"ddm_value":d[key]['value'],"weighted_value":pe_value*.75+d[key]['value']*.25}
    b=x['cash_bridge_rmb']
    cash_classified=b['cash_and_equivalents']+b['bank_time_deposits']+b['restricted_cash']+b['wealth_management_products']
    partial_proxy=cash_classified-b['restricted_cash']-b['bank_loans']-b['lease_liabilities']-b['capital_commitments']-b['deferred_withholding_tax']
    cf=x['reported_cash_flow_rmb']
    company_score=sum(sum(v) if isinstance(v,list) else v for v in x['scores']['company'].values())
    out={"as_of":x['as_of'],"company":x['company'],"earnings_bridge":{"ttm_attributable_profit_rmb":e['ttm_attributable_profit'],"after_tax_fvpl_removed_rmb":after_tax_fvpl,"normalized_profit_rmb":normalized_profit,"eps_cny_diluted":eps_cny,"fx_sensitivity_eps_hkd":{str(fx):eps_cny*fx for fx in (1.05,1.10,1.15)},"normalized_eps_hkd":eps_hkd},"pe_value":pe,"ddm":d,"scenarios":scenarios,"formal_weight_sum":sum(x['formal_weights'].values()),"target_price_raw":target_raw,"target_price":target,"valuation_certainty":x['valuation_certainty'],"buy_price":buy,"cash_diagnostic":{"cash_classified_rmb":cash_classified,"partial_group_financial_asset_proxy_rmb":partial_proxy,"proxy_per_share_hkd":partial_proxy*e['hkd_per_rmb_assumption']/e['basic_current_shares'],"nci_attribution":"unknown","formal_weight":0},"reported_cash_flow":{"fy2024_simplified_fcf":cf['fy2024_ocf']-cf['fy2024_cash_capex'],"fy2025_simplified_fcf":cf['fy2025_ocf']-cf['fy2025_cash_capex'],"h1_2026_cash_capex":"unknown","formal_weight":0},"cScore":company_score,"mScore":sum(x['scores']['management'].values())}
    (ROOT/'consun-revision-calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
