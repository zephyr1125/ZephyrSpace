"""复算金山办公纠错版；金额为亿元、股数为亿股，不调用外部服务。"""
import json
from pathlib import Path

shares = 4.64013435
economic = {2026: 22.5 - 3.1, 2027: 27.0 - 3.7, 2028: 32.0 - 4.4}
pe = economic[2027] / shares * 42
peg = economic[2026] / shares * 44
weighted = pe * .6 + peg * .4
target = round(weighted)
def dcf(g, fcf=22.5, ke=.09):
    return (sum(fcf*(1+g)**t/(1+ke)**t for t in range(1,11)) + 22*fcf*(1+g)**10/(1+ke)**10)/shares
result = {
    'cScore':sum([9,15,16,13,15,14]),'mScore':sum([18,19,14,13,8,9,4]),
    'shares':shares,'economic_profit':economic,'pe':pe,'peg':peg,'weighted':weighted,
    'target':target,'certainty':.45,'buy':round(target*(.68+.14*.45),2),
    'single_method_examples':{'peg_bear':17.9/shares*36,'pe_bull':24.8/shares*48},
    'eps_pe_sensitivity':{str(p):[round(p/shares*m,2) for m in [35,40,42,50]] for p in [21.3,23.3,25.3]},
    'old_dcf_diagnostic':{str(g):dcf(g) for g in [.11,.15,.19]},
    'cash_like_gross':(1387776250.60+881478133.89+6754543406.71+2830152598.64)/1e8,
    'lease_debt':(33964615.56+30426909.07)/1e8,
    'h1_ocf_capex':(642693273.51-44701541.82)/1e8,
    'sbc_disclosure_difference':(2671576717.30-2517594330.93)/1e8,
    'goodwill_to_equity':184668972.58/15076742614.52,
}
result['weighted_scenarios']=[(21.3/shares*35)*.6+(17.9/shares*36)*.4,weighted,(24.8/shares*48)*.6+(20.4/shares*50)*.4]
result['scenarios']=dict(zip(['bear','base','bull'],result['weighted_scenarios']))
assert result['cScore']==82 and result['mScore']==85
assert target==200
Path(__file__).with_name('calculations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
