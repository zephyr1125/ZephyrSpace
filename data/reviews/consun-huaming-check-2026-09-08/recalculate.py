"""复算旧报告明示公式，仅用于定位错误，不生成正式估值。"""
import json

def consun_ddm():
    dividends = [.78*1.05**t/1.08**t for t in range(1,6)]
    terminal = .78*1.05**5*1.03/(.08-.03)/1.08**5
    return dict(dividend_pv=sum(dividends), terminal_pv=terminal, total=sum(dividends)+terminal)

def huaming_value(g, payout=1):
    interim=sum(.90*(1+g)**t*payout/1.09**t for t in range(1,11))
    terminal=.90*(1+g)**10*15/1.09**10
    return dict(interim=interim,terminal=terminal,total=interim+terminal)

def root(payout):
    lo,hi=-.5,.5
    for _ in range(100):
        mid=(lo+hi)/2
        if huaming_value(mid,payout)['total']>19.01:hi=mid
        else:lo=mid
    return (lo+hi)/2

result={'consun_ddm':consun_ddm(),'consun_exclude_cash_pe_keep_other_inputs':(.35*20+.35*19.5+.20*18)/.90,'huaming_ddm_report_formula':{str(g):.58*(1+g)/(.08-g) for g in [.035,.045,.055]},'huaming_ddm_if_058_is_next_year_dividend':.58/(.08-.045),'huaming_reverse_at_report_growth':huaming_value(.073),'huaming_reverse_full_eps_growth':root(1),'huaming_reverse_60pct_payout_growth':root(.6),'huaming_weighted_report_values':.45*19.35+.30*17.69+.25*15.95,'huaming_management_listed_capital_positive_sum':6+3+3+4+3,'huaming_management_listed_strategy_net':6+5+2-1-1,'huaming_management_listed_shareholder_net':6+3+3+1-1-1-1,'huaming_lease_cash_difference':459367140.41-421905084.21}
if __name__=='__main__':print(json.dumps(result,ensure_ascii=False,indent=2))
