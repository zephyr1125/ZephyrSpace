"""美的本轮估值、股本和评分的可执行复算。"""
import json
def ddm(r=.09,g=.035,d1=4.5):
    rows=[{'t':t,'year':2025+t,'dps':d1*1.06**(t-1),'pv':d1*1.06**(t-1)/(1+r)**t} for t in range(1,6)]
    tv=rows[-1]['dps']*(1+g)/(r-g)
    return {'rows':rows,'dividend_pv':sum(x['pv'] for x in rows),'terminal':tv,'terminal_pv':tv/(1+r)**5,'value':sum(x['pv'] for x in rows)+tv/(1+r)**5}
def reverse(g,eps=6.2,payout=4.5/6.2):
    return sum(eps*(1+g)**t*payout/1.09**t for t in range(1,11))+eps*(1+g)**10*15/1.09**10
lo,hi=-.5,.5
for _ in range(100):
    mid=(lo+hi)/2
    if reverse(mid)>86.05:hi=mid
    else:lo=mid
base=ddm();target=round(.6*83.7+.4*base['value'],2)
out={'company_score':[8,14,16,12,18,13],'company_total':81,'management_score':[19,21,14,14,8,7,5],'management_total':88,'ddm':base,'sensitivity':{str(g):ddm(g=g)['value'] for g in [.03,.035,.04]},'scenario_values':{'bear':.6*6.0*12.5+.4*ddm(r=.10,g=.03)['value'],'base':.6*83.7+.4*base['value'],'bull':.6*6.8*14.5+.4*ddm(r=.085,g=.035)['value']},'target_price':target,'valuation_certainty':.6,'buy_price':round(target*(.68+.14*.6),2),'goodwill_provision':{'opening':5.56411,'ending':10.96473,'change':10.96473-5.56411},'gross_margin_pct':(260042490-194366771)/260042490*100,'book_value_per_share':2128.61055/76.28798092,'pb_a_share_reference':86.05*76.28798092/2128.61055,'eps_profit_bridge':{'2026':6.2*76.28798092,'2027':6.8*76.28798092},'convertible_new_share_pct':172480006/7628798092*100,'convertible_dilution_pct':172480006/(7628798092+172480006)*100,'related_purchase_bn_cny':(784897+2741725)/1000000,'related_purchase_100m_cny':(784897+2741725)/100000,'related_sales_100m_cny':2687367/100000,'interim_dividend_ratio_pct':3724298992/26446037000*100,'reverse_growth':(lo+hi)/2}
# 半年报单位为千元，一亿元=100,000千元；不得与伊利万元表混用。
assert sum(out['company_score'])==out['company_total']
assert sum(out['management_score'])==out['management_total']
print(json.dumps(out,ensure_ascii=False,indent=2))
