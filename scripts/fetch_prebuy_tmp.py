import tushare as ts, os, time, json
from dotenv import load_dotenv
load_dotenv(r'E:\ObsidianVaults\ZephyrSpace\.env')
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

codes = ['000596.SZ', '603369.SH']
results = {}

for code in codes:
    print(f'\n=== {code} ===')
    d = {}

    # 1. fina_indicator
    fi = pro.fina_indicator(ts_code=code, fields='ts_code,end_date,roe,or_yoy,netprofit_yoy,grossprofit_margin,ocf_to_profit,debt_to_assets,eps', limit=8)
    print('fina_indicator:')
    print(fi.to_string())
    d['fina'] = fi.to_dict('records')
    time.sleep(0.12)

    # 2. income 2025-2026
    inc = pro.income(ts_code=code, start_date='20250101', end_date='20260331',
                     fields='ts_code,end_date,revenue,n_income_attr_p', report_type=1)
    print('income (2025-2026):')
    print(inc.to_string())
    d['income'] = inc.to_dict('records')
    time.sleep(0.12)

    # income 2024
    inc2 = pro.income(ts_code=code, start_date='20240101', end_date='20241231',
                      fields='ts_code,end_date,revenue,n_income_attr_p', report_type=1)
    print('income (2024):')
    print(inc2.to_string())
    d['income2024'] = inc2.to_dict('records')
    time.sleep(0.12)

    # 3. daily_basic today
    db = pro.daily_basic(ts_code=code, trade_date='20260429',
                         fields='ts_code,pe_ttm,pb,total_mv,dv_ttm,turnover_rate')
    print('daily_basic 20260429:')
    print(db.to_string())
    d['daily_basic'] = db.to_dict('records')
    time.sleep(0.12)

    # 4. price 60days
    price = pro.daily(ts_code=code, start_date='20260210', end_date='20260429',
                      fields='ts_code,trade_date,close,pct_chg,vol')
    if len(price):
        pfirst = float(price.iloc[-1]['close'])
        plast = float(price.iloc[0]['close'])
        pdate = price.iloc[0]['trade_date']
        chg60 = round((plast - pfirst) / pfirst * 100, 2)
        print(f'price 60d: start={pfirst}, end={plast}, date={pdate}, chg={chg60}%')
        d['price_first'] = pfirst
        d['price_last'] = plast
        d['price_date_last'] = pdate
        d['price_chg60'] = chg60
        # min/max
        d['price_min60'] = float(price['close'].min())
        d['price_max60'] = float(price['close'].max())
    time.sleep(0.12)

    # 5. historical PB/PE for percentile (5y monthly - last trading day each month approx)
    pb_hist = pro.daily_basic(ts_code=code, start_date='20210101', end_date='20260429',
                               fields='ts_code,trade_date,pb,pe_ttm')
    if len(pb_hist):
        pb_hist = pb_hist.sort_values('trade_date')
        # monthly: keep last row per month
        pb_hist['month'] = pb_hist['trade_date'].str[:6]
        pb_monthly = pb_hist.groupby('month').last().reset_index()
        pe_vals = pb_monthly['pe_ttm'].dropna().tolist()
        pb_vals = pb_monthly['pb'].dropna().tolist()
        cur_pe = float(pb_hist.iloc[-1]['pe_ttm']) if not pb_hist.empty else None
        cur_pb = float(pb_hist.iloc[-1]['pb']) if not pb_hist.empty else None
        if pe_vals and cur_pe:
            pe_pct = round(sum(1 for x in pe_vals if x <= cur_pe) / len(pe_vals) * 100, 1)
        else:
            pe_pct = None
        if pb_vals and cur_pb:
            pb_pct = round(sum(1 for x in pb_vals if x <= cur_pb) / len(pb_vals) * 100, 1)
        else:
            pb_pct = None
        print(f'PE hist: cur={cur_pe}, pct={pe_pct}%, PB hist: cur={cur_pb}, pct={pb_pct}%')
        d['pe_hist_pct'] = pe_pct
        d['pb_hist_pct'] = pb_pct
        d['cur_pe'] = cur_pe
        d['cur_pb'] = cur_pb
        d['pe_min5y'] = round(min(pe_vals), 2) if pe_vals else None
        d['pe_max5y'] = round(max(pe_vals), 2) if pe_vals else None
    time.sleep(0.12)

    # 6. cashflow
    cf = pro.cashflow(ts_code=code, start_date='20240101', end_date='20260331',
                      fields='ts_code,end_date,n_cashflow_act')
    print('cashflow:')
    print(cf.to_string())
    d['cashflow'] = cf.to_dict('records')
    time.sleep(0.12)

    # 7. pledge_stat
    try:
        pledge = pro.pledge_stat(ts_code=code, fields='ts_code,end_date,pledge_ratio')
        print('pledge:')
        print(pledge.head(3).to_string())
        d['pledge'] = pledge.head(3).to_dict('records')
    except Exception as e:
        print(f'pledge error: {e}')
        d['pledge'] = []
    time.sleep(0.12)

    # 8. disclosure_date (半年报)
    try:
        disc = pro.disclosure_date(ts_code=code, end_type='2')
        print('disclosure (半年报):')
        print(disc.head(3).to_string())
        d['disclosure'] = disc.head(3).to_dict('records')
    except Exception as e:
        print(f'disclosure error: {e}')
        d['disclosure'] = []
    time.sleep(0.12)

    results[code] = d
    time.sleep(0.15)

print('\n\n=== FINAL JSON ===')
print(json.dumps(results, ensure_ascii=False, default=str))
