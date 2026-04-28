"""拉取932246候选11家公司完整PreBuy数据"""
import tushare as ts, os, time, json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

TRADE_DATE = '20260427'
TODAY = datetime.today().strftime('%Y%m%d')

COMPANIES = [
    ('300274.SZ', '阳光电源'),
    ('605117.SH', '德业股份'),
    ('300750.SZ', '宁德时代'),
    ('300827.SZ', '上能电气'),
    ('001301.SZ', '尚太科技'),
    ('002850.SZ', '科达利'),
    ('002150.SZ', '正泰电源'),
    ('300953.SZ', '震裕科技'),
    ('002518.SZ', '科士达'),
    ('300450.SZ', '先导智能'),
    ('603659.SH', '璞泰来'),
]

results = {}
for code, name in COMPANIES:
    print(f"\n{'='*50}")
    print(f"=== {name} ({code}) ===")
    d = {'code': code, 'name': name}

    # 1. 当前行情
    r = pro.daily(ts_code=code, start_date='20260421', end_date=TRADE_DATE,
                  fields='ts_code,trade_date,close,vol,pct_chg')
    time.sleep(0.12)
    if len(r):
        latest = r.sort_values('trade_date', ascending=False).iloc[0]
        d['close'] = latest['close']
        d['trade_date'] = latest['trade_date']
        # 近60日
        r60 = pro.daily(ts_code=code, start_date='20260120', end_date=TRADE_DATE,
                        fields='ts_code,trade_date,close,high,low,vol')
        time.sleep(0.12)
        if len(r60):
            d['high_60'] = r60['high'].max()
            d['low_60'] = r60['low'].min()
            d['pct_from_high'] = round((latest['close'] - r60['high'].max()) / r60['high'].max() * 100, 1)
        print(f"  价格: {d.get('close')}元  60日高/低: {d.get('high_60')}/{d.get('low_60')}  距高点: {d.get('pct_from_high')}%")
    
    # 2. 估值指标
    r2 = pro.daily_basic(ts_code=code, trade_date=TRADE_DATE,
                         fields='ts_code,pe_ttm,pb,total_mv,turnover_rate,dv_ttm')
    time.sleep(0.12)
    if len(r2):
        row = r2.iloc[0]
        d['pe_ttm'] = row['pe_ttm']
        d['pb'] = row['pb']
        d['total_mv_yi'] = round(row['total_mv']/10000, 0) if row['total_mv'] else None
        d['turnover_rate'] = row['turnover_rate']
        d['dv_ttm'] = row['dv_ttm']
        print(f"  PE={d['pe_ttm']:.1f}  PB={d['pb']:.2f}  市值={d['total_mv_yi']}亿  股息率={d['dv_ttm']}%")

    # 3. 财务指标（近3年）
    fi = pro.fina_indicator(ts_code=code,
                            fields='ts_code,end_date,roe,or_yoy,netprofit_yoy,dt_netprofit_yoy,ocfps,eps',
                            limit=10)
    time.sleep(0.12)
    if len(fi):
        annual = fi[fi['end_date'].str.endswith('1231')].head(3)
        d['fina_annual'] = annual.to_dict('records')
        latest_a = annual.iloc[0] if len(annual) else fi.iloc[0]
        d['roe'] = latest_a['roe']
        d['or_yoy'] = latest_a['or_yoy']
        d['netprofit_yoy'] = latest_a['netprofit_yoy']
        d['dt_netprofit_yoy'] = latest_a['dt_netprofit_yoy']
        print(f"  ROE={d['roe']:.1f}%  营收同比={d['or_yoy']:.1f}%  净利同比={d['netprofit_yoy']:.1f}%  扣非同比={d['dt_netprofit_yoy']:.1f}%  ({latest_a['end_date']})")

    # 4. 利润表（营收、净利润）
    inc = pro.income(ts_code=code, period='20251231',
                     fields='ts_code,end_date,total_revenue,n_income_attr_p,ebit')
    time.sleep(0.12)
    if len(inc):
        row = inc.iloc[0]
        d['revenue_2025'] = round(row['total_revenue']/1e8, 2) if row['total_revenue'] else None
        d['net_profit_2025'] = round(row['n_income_attr_p']/1e8, 2) if row['n_income_attr_p'] else None
        print(f"  2025营收={d['revenue_2025']}亿  归母净利={d['net_profit_2025']}亿")

    # 5. 现金流
    cf = pro.cashflow(ts_code=code, period='20251231',
                      fields='ts_code,end_date,n_cashflow_act,free_cashflow')
    time.sleep(0.12)
    if len(cf):
        row = cf.iloc[0]
        d['ocf_2025'] = round(row['n_cashflow_act']/1e8, 2) if row['n_cashflow_act'] else None
        d['fcf_2025'] = round(row['free_cashflow']/1e8, 2) if row['free_cashflow'] else None
        # 净现比
        if d.get('net_profit_2025') and d.get('ocf_2025') and d['net_profit_2025'] != 0:
            d['ocf_ratio'] = round(d['ocf_2025'] / d['net_profit_2025'], 2)
        print(f"  经营现金流={d['ocf_2025']}亿  净现比={d.get('ocf_ratio','N/A')}")

    # 6. 资产负债（商誉、有息负债）
    bal = pro.balancesheet(ts_code=code, period='20251231',
                           fields='ts_code,end_date,goodwill,total_assets,total_liab,total_hldr_eqy_exc_min_int')
    time.sleep(0.12)
    if len(bal):
        row = bal.iloc[0]
        gw = row['goodwill']/1e8 if row['goodwill'] else 0
        equity = row['total_hldr_eqy_exc_min_int']/1e8 if row['total_hldr_eqy_exc_min_int'] else None
        d['goodwill_yi'] = round(gw, 2)
        d['equity_yi'] = round(equity, 2) if equity else None
        d['gw_ratio'] = round(gw / equity * 100, 1) if equity and equity > 0 else None
        print(f"  商誉={d['goodwill_yi']}亿  净资产={d['equity_yi']}亿  商誉/净资产={d['gw_ratio']}%")

    # 7. 下一财报日
    end_types = {'1': '一季报', '2': '半年报', '3': '三季报', '4': '年报'}
    candidates = []
    for et, et_name in end_types.items():
        try:
            df = pro.disclosure_date(ts_code=code, end_type=et)
            time.sleep(0.12)
            if df is None or len(df) == 0:
                continue
            future = df[df['pre_date'] >= TODAY]
            not_out = future[future['actual_date'].isna() | (future['actual_date'] == '')]
            rows = not_out if len(not_out) > 0 else future
            if len(rows) > 0:
                row = rows.sort_values('pre_date').iloc[0]
                candidates.append({'pre_date': row['pre_date'], 'type': et_name})
        except Exception as e:
            pass
    if candidates:
        candidates.sort(key=lambda x: x['pre_date'])
        best = candidates[0]
        d['next_earnings_date'] = f"{best['pre_date'][:4]}-{best['pre_date'][4:6]}-{best['pre_date'][6:]}"
        d['next_earnings_type'] = best['type']
        print(f"  下一财报: {d['next_earnings_date']} {d['next_earnings_type']}")
    else:
        # 法定截止日估算
        import calendar
        year = datetime.today().year
        month = datetime.today().month
        if month <= 4:
            d['next_earnings_date'] = f"{year}-04-30"
            d['next_earnings_type'] = "一季报（估算）"
        elif month <= 8:
            d['next_earnings_date'] = f"{year}-08-31"
            d['next_earnings_type'] = "半年报（估算）"
        elif month <= 10:
            d['next_earnings_date'] = f"{year}-10-31"
            d['next_earnings_type'] = "三季报（估算）"
        else:
            d['next_earnings_date'] = f"{year+1}-04-30"
            d['next_earnings_type'] = "年报（估算）"
        print(f"  下一财报（估算）: {d['next_earnings_date']} {d['next_earnings_type']}")

    results[code] = d

with open('data/prebuy_932246_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
print(f"\n\n数据已保存至 data/prebuy_932246_data.json")
print("\n=== 汇总 ===")
for code, d in results.items():
    print(f"{d['name']} {code}  市值={d.get('total_mv_yi')}亿  PE={d.get('pe_ttm')}  ROE={d.get('roe')}%  净现比={d.get('ocf_ratio')}  下一财报={d.get('next_earnings_date')} {d.get('next_earnings_type')}")
