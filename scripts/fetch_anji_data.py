import tushare as ts
import pandas as pd
import json
from datetime import datetime

ts.set_token('bad7e5f40886c65f210a5256551b7ba8c34d1b2099b65e81cee81b04')
pro = ts.pro_api()

results = {}

# 1. 基本信息
try:
    df = pro.stock_basic(ts_code='688019.SH', fields='ts_code,symbol,name,area,industry,market,list_date')
    results['basic'] = df.to_dict('records')
    print("=== 基本信息 ===")
    print(df.to_string())
except Exception as e:
    print(f"基本信息失败: {e}")
    results['basic'] = []

# 2. 近60天日行情
try:
    df = pro.daily(ts_code='688019.SH', start_date='20250226', end_date='20260426')
    results['daily'] = df.to_dict('records')
    print(f"\n=== 近60天日行情 (共{len(df)}条) ===")
    print(df.head(5).to_string())
    print(f"最新: {df.iloc[0]['trade_date']} close={df.iloc[0]['close']}")
except Exception as e:
    print(f"日行情失败: {e}")
    results['daily'] = []

# 3. 财务指标
try:
    df = pro.fina_indicator(ts_code='688019.SH', start_date='20200101', end_date='20260426',
        fields='ann_date,end_date,roe,roa,grossprofit_margin,netprofit_margin,current_ratio,quick_ratio,debt_to_assets,inv_turn,ar_turn,assets_turn,op_to_pr,n_cashflow_act,ocf_to_or')
    # 只取年报（end_date以1231结尾）
    df_annual = df[df['end_date'].str.endswith('1231')].drop_duplicates('end_date').sort_values('end_date', ascending=False)
    results['fina_indicator'] = df_annual.to_dict('records')
    print(f"\n=== 财务指标（年报）===")
    print(df_annual[['end_date','roe','roa','grossprofit_margin','netprofit_margin','debt_to_assets']].head(5).to_string())
except Exception as e:
    print(f"财务指标失败: {e}")
    results['fina_indicator'] = []

# 4. 利润表
try:
    df = pro.income(ts_code='688019.SH', start_date='20200101', end_date='20260426',
        fields='ann_date,end_date,total_revenue,revenue,n_income_attr_p,ebit,operate_profit,total_profit')
    df_annual = df[df['end_date'].str.endswith('1231')].drop_duplicates('end_date').sort_values('end_date', ascending=False)
    results['income'] = df_annual.to_dict('records')
    print(f"\n=== 利润表（年报）===")
    print(df_annual[['end_date','revenue','n_income_attr_p','operate_profit']].head(5).to_string())
except Exception as e:
    print(f"利润表失败: {e}")
    results['income'] = []

# 5. 资产负债表
try:
    df = pro.balancesheet(ts_code='688019.SH', start_date='20200101', end_date='20260426',
        fields='ann_date,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int,goodwill,fix_assets,notes_receiv,accounts_receiv,inventories,money_cap')
    df_annual = df[df['end_date'].str.endswith('1231')].drop_duplicates('end_date').sort_values('end_date', ascending=False)
    results['balancesheet'] = df_annual.to_dict('records')
    print(f"\n=== 资产负债表（年报）===")
    print(df_annual[['end_date','total_assets','total_liab','total_hldr_eqy_exc_min_int','accounts_receiv','inventories']].head(5).to_string())
except Exception as e:
    print(f"资产负债表失败: {e}")
    results['balancesheet'] = []

# 6. 现金流量表
try:
    df = pro.cashflow(ts_code='688019.SH', start_date='20200101', end_date='20260426',
        fields='ann_date,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,capex,free_cash_flow')
    df_annual = df[df['end_date'].str.endswith('1231')].drop_duplicates('end_date').sort_values('end_date', ascending=False)
    results['cashflow'] = df_annual.to_dict('records')
    print(f"\n=== 现金流量表（年报）===")
    print(df_annual[['end_date','n_cashflow_act','capex','free_cash_flow']].head(5).to_string())
except Exception as e:
    print(f"现金流量表失败: {e}")
    results['cashflow'] = []

# 7. 股息
try:
    df = pro.dividend(ts_code='688019.SH', fields='ann_date,div_proc,stk_div,cash_div_tax,record_date,ex_date,pay_date,end_date')
    results['dividend'] = df.to_dict('records')
    print(f"\n=== 股息 ===")
    print(df.head(10).to_string())
except Exception as e:
    print(f"股息失败: {e}")
    results['dividend'] = []

# 8. PE/PB历史
try:
    df = pro.daily_basic(ts_code='688019.SH', start_date='20220101', end_date='20260426',
        fields='trade_date,close,turnover_rate,pe_ttm,pb,ps_ttm,dv_ttm,total_mv')
    results['daily_basic'] = df.to_dict('records')
    print(f"\n=== PE/PB历史（{len(df)}条）===")
    print(df.head(3).to_string())
    # 计算PE历史分位
    pe_values = df['pe_ttm'].dropna()
    current_pe = df.iloc[0]['pe_ttm']
    pe_pct = (pe_values < current_pe).sum() / len(pe_values) * 100
    print(f"当前PE TTM: {current_pe:.2f}")
    print(f"PE历史分位（3年）: {pe_pct:.1f}%")
    results['pe_percentile'] = float(pe_pct)
    results['current_pe'] = float(current_pe)
except Exception as e:
    print(f"PE/PB历史失败: {e}")
    results['daily_basic'] = []

# 9. 最新每日指标
try:
    df = pro.daily_basic(ts_code='688019.SH', trade_date='20260425',
        fields='ts_code,trade_date,close,pe_ttm,pb,ps_ttm,dv_ttm,total_mv')
    results['latest_basic'] = df.to_dict('records')
    print(f"\n=== 最新指标（20260425）===")
    print(df.to_string())
except Exception as e:
    print(f"最新指标失败: {e}")
    results['latest_basic'] = []

# 保存到JSON
with open(r'E:\ObsidianVaults\ZephyrSpace\scripts\anji_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, default=str)
print("\n数据已保存到 anji_data.json")
