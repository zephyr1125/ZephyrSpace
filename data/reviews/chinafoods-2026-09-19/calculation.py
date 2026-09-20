import json
from pathlib import Path
R=Path(__file__).resolve().parent; d=json.loads((R/'calculation-inputs.json').read_text(encoding='utf-8'))
fx=1/d['rmb_per_hkd']; eps=d['fy2025_owner_profit_rmb_m']*1_000_000/d['shares']; d0=d['fy2025_dps_rmb']
pe={k:eps*v*fx for k,v in d['static_pe_multiples'].items()}
ddm={k:d0*(1+v['g'])/(v['ke']-v['g'])*fx for k,v in d['ddm_scenarios'].items()}
combined={k:(pe[k]+ddm[k])/2 for k in pe}; target=combined['base']; certainty=d['valuation_certainty']; buy=target*(0.68+0.14*certainty)
reverse_g=(d['close_hkd']*d['ddm_scenarios']['base']['ke']-d0*fx)/(d['close_hkd']+d0*fx)
timing={str(t):ddm['base']*(1+d['ddm_scenarios']['base']['ke'])**(1-t) for t in (0.75,1.0,1.25)}
ddm_grid={str(g):{str(ke):d0*(1+g)/(ke-g)*fx for ke in (0.10,0.11,0.12)} for g in (0.01,0.025,0.04)}
pe_sens={str(s):{k:eps*s*m*fx for k,m in d['static_pe_multiples'].items()} for s in (0.9,1.0,1.1)}
o={'cscore':sum(d['cscore_components'].values()),'mscore':sum(d['mscore_components'].values()),'fy2025_actual_eps_rmb':eps,'hkd_per_rmb':fx,'pe_value_hkd':pe,'ddm_value_hkd':ddm,'combined_value_hkd':combined,'target_price_hkd':target,'valuation_certainty':certainty,'mechanical_buy_price_hkd':buy,'reverse_pe':d['close_hkd']/(eps*fx),'reverse_ddm_growth':reverse_g,'ddm_timing_sensitivity_hkd':timing,'ddm_ke_g_sensitivity_hkd':ddm_grid,'pe_sensitivity_hkd':pe_sens,'upside_target_over_price':target/d['close_hkd']-1,'premium_price_over_target':d['close_hkd']/target-1}
(R/'calculation-results.json').write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(o,ensure_ascii=False,indent=2))
