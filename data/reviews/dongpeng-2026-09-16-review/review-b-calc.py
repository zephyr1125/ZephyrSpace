"""复核B独立计算；不导入或执行作者模型，金额统一人民币元。"""
import json
from pathlib import Path

shares = 734199310
outside = shares - 7122551
fx = 1 / 0.8627
cases = {
    'bear': ([.16,.10,.08,.06,.05],[.14,.14,.135,.13,.13],.105,.025,5.2e9,13),
    'base': ([.20,.14,.11,.09,.07],[.16,.165,.165,.165,.165],.095,.03,5.75e9,15.5),
    'bull': ([.23,.18,.15,.12,.09],[.17,.18,.185,.185,.185],.09,.035,6.2e9,18),
}
result = {}
for name,(growth,margins,r,g,np,pe) in cases.items():
    revenue = 20.875e9
    flows=[]
    for inc,margin in zip(growth,margins):
        revenue *= 1+inc
        flows.append(revenue*margin)
    explicit=sum(v/(1+r)**(i+1) for i,v in enumerate(flows))
    terminal=flows[-1]*(1+g)/(r-g)/(1+r)**5
    ev=explicit+terminal
    dcf=(ev+12e9)/shares*fx
    pe_value=np*pe/shares*fx
    result[name]={'ev_cny':ev,'terminal_share':terminal/ev,'dcf_hkd':dcf,'pe_hkd':pe_value,'weighted_hkd':dcf*.55+pe_value*.45,'dcf_if_text_12_yi_hkd':(ev+1.2e9)/shares*fx}

result['cash_bridge']={
    'printed_rounded_sum_yi':144.75+64.54+17.95+4.91+1.05-56.49-4.10-21.81-5.68-20,
    'exact_partial_bridge_cny':14474702969.60+6453846624.22+1794534621.13+491343850.41+105125700.19-5648703088.20-391296299.76-19044005.66-2181230277-568427482.52-2e9-8468012.25,
    'weighted_price_effect_120_vs_12_yi_hkd':(12e9-1.2e9)/shares*fx*.55,
}
result['checks']={
    'outside_shares':outside,
    'treasury_adjustment_factor':shares/outside,
    'mechanical_buy':result['base']['weighted_hkd']*.7612,
    'reverse_profit_cny':100.5*.8627/15.5*shares,
    'base_if_text_12_yi_hkd':result['base']['dcf_if_text_12_yi_hkd']*.55+result['base']['pe_hkd']*.45,
    'fy2025_simple_ocf_less_capex_cny':6174239867.75-2269157969.98,
    'h12026_simple_ocf_less_capex_cny':2492600974.20-1135160762.65,
    'revenue_cagr_23_25':(208.7527311752/112.63)**.5-1,
    'profit_cagr_23_25':(44.1526314779/20.40)**.5-1,
    'ocf_profit_ratios':[32.8126965265/20.4,57.8940850854/33.2670885244,61.7423986775/44.1526314779,24.926009742/28.6680185834],
    'nonrecurring_profit_share_h1':269202473.76/2866801858.34,
    'pe_matrix_62_yi':[6.2e9*p/shares*fx for p in [13,15.5,18]],
    'company_score':sum([8,17,16,11,16,12]),
    'management_score':sum([14,19,14,11,6,8,4]),
}
print(json.dumps(result,ensure_ascii=False,indent=2))
