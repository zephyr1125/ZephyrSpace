import json
from copy import deepcopy
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parent
d=json.loads((ROOT/"valuation-input.json").read_text(encoding="utf-8-sig"))
fx=d["fx"]["hkd_to_cny"]
shares=d["shares"]["external"]
valuation_date=date(2026,9,15)
def yearfrac(target): return (target-valuation_date).days/365

def forecast(s):
    revenue=d["history"]["fy2025"]["revenue"]; rows=[]
    for i,year in enumerate(range(2026,2031)):
        prev=revenue; revenue*=1+s["revenue_growth"][i]
        ebit=revenue*s["ebit_margin"][i]; nopat=ebit*(1-s["tax_rate"])
        da=revenue*s["da_pct_revenue"]; capex=revenue*s["capex_pct_revenue"][i]
        dnwc=(revenue-prev)*s["nwc_pct_incremental_revenue"]
        fcff=nopat+da-capex-dnwc
        rows.append({"year":year,"revenue":revenue,"ebit":ebit,"nopat":nopat,"da":da,"capex":capex,"delta_nwc":dnwc,"fcff":fcff})
    return rows

def dcf(s):
    rows=forecast(s); h1=d["history"]["h1_2026"]
    h1_nopat=h1["operating_ebit"]*(1-h1["tax_rate"])
    h1_fcff=h1_nopat+h1["da"]-h1["capex"]-h1["delta_nwc"]
    annual=rows[0]
    h2={k:annual[k]-v for k,v in {"nopat":h1_nopat,"da":h1["da"],"capex":h1["capex"],"delta_nwc":h1["delta_nwc"],"fcff":h1_fcff}.items()}
    pre={k:v*77/184 for k,v in h2.items()}; post={k:v*107/184 for k,v in h2.items()}
    pv=post["fcff"]/(1+s["wacc"])**yearfrac(date(2026,12,31))
    for row in rows[1:]: pv+=row["fcff"]/(1+s["wacc"])**yearfrac(date(row["year"],12,31))
    terminal_nopat=rows[-1]["nopat"]*(1+s["g"])
    terminal_fcff=terminal_nopat*(1-s["g"]/s["terminal_roic"])
    terminal=terminal_fcff/(s["wacc"]-s["g"])
    pv_terminal=terminal/(1+s["wacc"])**yearfrac(date(2030,12,31)); ev=pv+pv_terminal
    cb=d["cash_bridge_2026_06_30"]
    net=(cb["selected_assets"]-cb["debt_and_leases"]-cb["operating_buffer"]-cb["nci"]-cb["interim_dividend"]+cb["debt_in_other_noncurrent_financial_assets"]+cb["private_fund_book_value"]*(1-s["fund_haircut"])+pre["fcff"])
    equity=ev+net
    return {"rows":rows,"h1":{"nopat":h1_nopat,"da":h1["da"],"capex":h1["capex"],"delta_nwc":h1["delta_nwc"],"fcff":h1_fcff},"h2":h2,"pre_valuation_77_184":pre,"post_valuation_107_184":post,"discount_years":{str(y):yearfrac(date(y,12,31)) for y in range(2026,2031)},"pv_explicit":pv,"pv_terminal":pv_terminal,"terminal_share_ev":pv_terminal/ev,"ev":ev,"net_financial_assets":net,"equity":equity,"per_share_hkd":equity/shares/fx}

dcfs={k:dcf(v) for k,v in d["scenarios"].items()}
t=d["comparables"]["tingyi"]; u=d["comparables"]["unipresident"]
east_actual=d["comparables"]["eastroc_actual_ttm_profit"]; east_deducted=d["comparables"]["eastroc_deducted_ttm_profit"]
t_ttm=t["fy25_actual_attr"]+t["h1_26_actual_attr"]-t["h1_25_actual_attr"]; u_ttm=u["actual_ttm_profit_cny"]
t_pe=t["shares"]*t["price_hkd"]*fx/t_ttm; u_pe=u["shares"]*u["price_hkd"]*fx/u_ttm
pes={"bear":min(t_pe,u_pe),"base":(t_pe+u_pe)/2,"bull":max(t_pe,u_pe)}
pe_values={k:east_actual*v/shares/fx for k,v in pes.items()}; pe_deducted={k:east_deducted*v/shares/fx for k,v in pes.items()}
combined={k:dcfs[k]["per_share_hkd"]*.55+pe_values[k]*.45 for k in pes}; target=combined["base"]; buy=target*.7528
wacc_g={}
for w in (.09,.095,.10,.105):
    wacc_g[str(w)]={}
    for g in (.025,.03,.035):
        s=deepcopy(d["scenarios"]["base"]); s["wacc"]=w; s["g"]=g; wacc_g[str(w)][str(g)]=dcf(s)["per_share_hkd"]
original=d["cash_bridge_2026_06_30"]["operating_buffer"]; buffer={}
for bn in (1,2,3): d["cash_bridge_2026_06_30"]["operating_buffer"]=bn*1e9; buffer[str(bn)]=dcf(d["scenarios"]["base"])["per_share_hkd"]
d["cash_bridge_2026_06_30"]["operating_buffer"]=original
stress=deepcopy(d["scenarios"]["base"]); stress["capex_pct_revenue"]=[x+.01 for x in stress["capex_pct_revenue"]]; stress["nwc_pct_incremental_revenue"]=.04
interest_boundary=(178103646.35-45169719.31)*(1-.2094)*77/181
out={"actual_ttm":{"eastroc":east_actual,"tingyi":t_ttm,"unipresident":u_ttm},"comparable_pe":{"tingyi":t_pe,"unipresident":u_pe,"scenarios":pes,"eastroc_actual_ttm_values_hkd":pe_values,"eastroc_deducted_ttm_sensitivity_hkd":pe_deducted},"dcf":dcfs,"cash_roll_sensitivity":{"h1_net_interest_after_tax_scaled_77_181_plus_minus":interest_boundary,"per_share_hkd_plus_minus":interest_boundary/shares/fx},"sensitivity":{"wacc_g_hkd":wacc_g,"operating_buffer_bn_hkd":buffer,"capex_plus_1pct_and_nwc_4pct_hkd":dcf(stress)["per_share_hkd"]},"combined_hkd":combined,"target_hkd":target,"certainty":.52,"mechanical_buy_hkd":buy,"reverse_zero_weight":{"weight":0,"implied_actual_ttm_profit":d["market"]["eastroc_hkd_2026_09_15"]*fx*shares/pes["base"]},"max_weight":None}
(ROOT/"valuation-output.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"dcf":{k:v["per_share_hkd"] for k,v in dcfs.items()},"pe":pes,"pe_values":pe_values,"combined":combined,"target":target,"buy":buy,"h2":{k:v["h2"]["fcff"] for k,v in dcfs.items()}},ensure_ascii=False,indent=2))

