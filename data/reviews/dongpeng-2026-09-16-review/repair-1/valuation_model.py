import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "valuation-input.json").read_text(encoding="utf-8"))
fx = data["fx"]["hkd_to_cny"]
shares = data["shares"]["external"]

def normalized_unipresident(c):
    fy = c["fy25_profit"] - c["fy25_other_gains"] * (1-c["fy25_tax_rate"])
    h126 = c["h1_26_profit"] - c["h1_26_other_gains"] * (1-c["h1_26_tax_rate"])
    h125 = c["h1_25_profit"] - c["h1_25_other_gains"] * (1-c["h1_25_tax_rate"])
    return fy + h126 - h125

def dcf(name, s):
    revenue = data["history"]["fy2025"]["revenue"]
    rows=[]
    for i, year in enumerate(range(2026,2031)):
        prev=revenue
        revenue *= 1+s["revenue_growth"][i]
        ebit=revenue*s["ebit_margin"][i]
        nopat=ebit*(1-s["tax_rate"])
        da=revenue*s["da_pct_revenue"]
        capex=revenue*s["capex_pct_revenue"][i]
        dnwc=(revenue-prev)*s["nwc_pct_incremental_revenue"]
        fcff=nopat+da-capex-dnwc
        rows.append({"year":year,"revenue":revenue,"ebit":ebit,"nopat":nopat,"da":da,"capex":capex,"delta_nwc":dnwc,"fcff":fcff})
    # 估值日为9月15日：H2均匀发生，7月1日至9月15日占77/184；已发生估计进入金融资产桥，剩余部分才折现。
    elapsed=77/184
    remaining=1-elapsed
    pre_date_fcff=rows[0]["fcff"]*0.5*elapsed
    remaining_h2=rows[0]["fcff"]*0.5*remaining
    pv=remaining_h2/(1+s["wacc"])**(remaining/2)
    for row in rows[1:]:
        t=(row["year"]-2026)+remaining/2
        pv += row["fcff"]/(1+s["wacc"])**t
    terminal_nopat=rows[-1]["nopat"]*(1+s["g"])
    terminal_fcff=terminal_nopat*(1-s["g"]/s["terminal_roic"])
    terminal=terminal_fcff/(s["wacc"]-s["g"])
    terminal_t=4+remaining/2
    pv_terminal=terminal/(1+s["wacc"])**terminal_t
    ev=pv+pv_terminal
    cb=data["cash_bridge_2026_06_30"]
    # 9月15日已除息，扣中期股息；承诺已在未来Capex中，不重复扣。
    net_assets=(cb["selected_assets"]-cb["debt_and_leases"]-cb["operating_buffer"]-cb["nci"]-cb["interim_dividend"]
                +cb["debt_in_other_noncurrent_financial_assets"]
                +cb["private_fund_book_value"]*(1-s["fund_haircut"])+pre_date_fcff)
    equity=ev+net_assets
    per_share_hkd=equity/shares/fx
    return {"rows":rows,"pre_date_fcff":pre_date_fcff,"pv_explicit":pv,"pv_terminal":pv_terminal,"terminal_share_ev":pv_terminal/ev,"ev":ev,"net_financial_assets":net_assets,"equity":equity,"per_share_hkd":per_share_hkd}

u=data["comparables"]["unipresident"]
u_norm=normalized_unipresident(u)
t=data["comparables"]["tingyi"]
t_pe=t["shares"]*t["price_hkd"]*fx/t["normalized_ttm_profit_cny"]
u_pe=u["shares"]*u["price_hkd"]*fx/u_norm
pes={"bear":min(t_pe,u_pe),"base":(t_pe+u_pe)/2,"bull":max(t_pe,u_pe)}
east_profit=data["comparables"]["eastroc_normalized_ttm_profit"]
pe_values={k:east_profit*v/shares/fx for k,v in pes.items()}
dcfs={k:dcf(k,v) for k,v in data["scenarios"].items()}
combined={k:dcfs[k]["per_share_hkd"]*data["weights"]["fcff_dcf"]+pe_values[k]*data["weights"]["comparable_pe"] for k in ("bear","base","bull")}
target=combined["base"]
buy=target*(0.68+0.14*data["certainty"])
current=data["market"]["eastroc_hkd_2026_09_15"]
reverse_profit=current*fx*shares/pes["base"]
wacc_g={}
for w in (0.09,0.095,0.10,0.105):
    wacc_g[str(w)]={}
    for g in (0.025,0.03,0.035):
        s=dict(data["scenarios"]["base"]); s["wacc"]=w; s["g"]=g
        wacc_g[str(w)][str(g)]=dcf("base",s)["per_share_hkd"]
buffer_sensitivity={}
original_buffer=data["cash_bridge_2026_06_30"]["operating_buffer"]
for bn in (1,2,3):
    data["cash_bridge_2026_06_30"]["operating_buffer"]=bn*1_000_000_000
    buffer_sensitivity[str(bn)]=dcf("base",data["scenarios"]["base"])["per_share_hkd"]
data["cash_bridge_2026_06_30"]["operating_buffer"]=original_buffer
stress=dict(data["scenarios"]["base"])
stress["capex_pct_revenue"]=[x+0.01 for x in stress["capex_pct_revenue"]]
stress["nwc_pct_incremental_revenue"]=0.04
out={"comparable_normalization":{"tingyi_ttm":t["normalized_ttm_profit_cny"],"unipresident_ttm":u_norm,"eastroc_ttm":east_profit},"comparable_pe":{"tingyi":t_pe,"unipresident":u_pe,"scenarios":pes,"eastroc_values_hkd":pe_values},"dcf":dcfs,"sensitivity":{"wacc_g_hkd":wacc_g,"operating_buffer_bn_hkd":buffer_sensitivity,"capex_plus_1pct_and_nwc_4pct_hkd":dcf("base",stress)["per_share_hkd"]},"combined_hkd":combined,"target_hkd":target,"certainty":data["certainty"],"mechanical_buy_hkd":buy,"current_hkd":current,"reverse_zero_weight":{"weight":0,"implied_profit_at_base_comparable_pe":reverse_profit},"max_weight":None}
(ROOT/"valuation-output.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"target":target,"buy":buy,"combined":combined,"dcf":{k:v["per_share_hkd"] for k,v in dcfs.items()},"pe_values":pe_values,"pe":pes,"u_norm":u_norm},ensure_ascii=False,indent=2))
