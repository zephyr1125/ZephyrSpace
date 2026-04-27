"""
Step 3: 获取通过粗筛的13家公司的详细数据
"""
import tushare as ts, os, time, pandas as pd, json
from dotenv import load_dotenv
load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 通过粗筛的13家公司
candidates = [
    ('601126.SH', 1.765),
    ('000682.SZ', 0.797),
    ('300001.SZ', 1.647),
    ('300444.SZ', 0.604),
    ('002533.SZ', 0.556),
    ('002452.SZ', 0.415),
    ('300882.SZ', 0.198),
    ('001359.SZ', 0.320),
    ('600577.SH', 1.669),
    ('603556.SH', 0.523),
    ('600517.SH', 0.897),
    ('600406.SH', 8.556),
    ('301291.SZ', 0.776),
]

trade_date = '20260424'
results = {}

# 先批量获取公司基本信息（名称）
print("获取公司基本信息...")
all_codes = [c[0] for c in candidates]
# 获取所有A股基本信息
stock_basic = pro.stock_basic(fields='ts_code,name,industry,market,list_date')
name_map = dict(zip(stock_basic['ts_code'], stock_basic['name']))
industry_map = dict(zip(stock_basic['ts_code'], stock_basic['industry']))
market_map = dict(zip(stock_basic['ts_code'], stock_basic['market']))

for code, _ in candidates:
    name = name_map.get(code, '未知')
    industry = industry_map.get(code, '未知')
    market = market_map.get(code, '未知')
    print(f"  {code}: {name} ({industry}) [{market}]")

print("\n\n开始逐家获取详细财务数据...")

for code, weight in candidates:
    name = name_map.get(code, '未知')
    print(f"\n{'='*60}")
    print(f"[{code}] {name} (权重{weight}%)")
    print(f"{'='*60}")
    data = {'code': code, 'name': name, 'weight': weight, 'market': market_map.get(code, '')}
    
    # 当前价格
    try:
        price_df = pro.daily(ts_code=code, trade_date=trade_date, fields='ts_code,close,vol,amount')
        if price_df is not None and len(price_df):
            data['close'] = float(price_df.iloc[0]['close'])
            print(f"  当前价格: {data['close']:.2f} 元")
        time.sleep(0.11)
    except Exception as e:
        print(f"  daily {code}: {e}")
    
    # 基本面估值
    try:
        basic = pro.daily_basic(ts_code=code, trade_date=trade_date,
            fields='ts_code,pe_ttm,pb,total_mv,dv_ttm,circ_mv')
        if basic is not None and len(basic):
            b = basic.iloc[0]
            data['pe_ttm'] = float(b['pe_ttm']) if not pd.isna(b['pe_ttm']) else None
            data['pb'] = float(b['pb']) if not pd.isna(b['pb']) else None
            data['total_mv'] = float(b['total_mv']) / 10000 if not pd.isna(b['total_mv']) else None
            data['dv_ttm'] = float(b['dv_ttm']) if not pd.isna(b['dv_ttm']) else None
            print(f"  PE={data['pe_ttm']:.2f}x, PB={data['pb']:.2f}x, 市值={data['total_mv']:.1f}亿, 股息率={data['dv_ttm']}%")
        time.sleep(0.11)
    except Exception as e:
        print(f"  daily_basic {code}: {e}")
    
    # 财务指标（近4期）
    try:
        fi = pro.fina_indicator(ts_code=code,
            fields='ts_code,end_date,roe,or_yoy,netprofit_yoy,ocfps,eps,bps,grossprofit_margin,dt_eps,q_roe,netprofit_margin',
            limit=4)
        if fi is not None and len(fi):
            data['fina_indicator'] = fi.to_dict('records')
            latest = fi.iloc[0]
            print(f"  ROE={latest.get('roe'):.2f}%, 营收同比={latest.get('or_yoy'):.2f}%, 净利同比={latest.get('netprofit_yoy'):.2f}%")
            print(f"  毛利率={latest.get('grossprofit_margin'):.2f}%, EPS={latest.get('eps'):.3f}")
        time.sleep(0.15)
    except Exception as e:
        print(f"  fina_indicator {code}: {e}")
    
    # 利润表（近4期）
    try:
        income = pro.income(ts_code=code,
            fields='ts_code,end_date,total_revenue,n_income_attr_p,basic_eps,ebit',
            limit=4)
        if income is not None and len(income):
            data['income'] = income.to_dict('records')
            latest = income.iloc[0]
            rev = float(latest['total_revenue'])/1e8
            ni = float(latest['n_income_attr_p'])/1e8
            print(f"  营收={rev:.2f}亿, 归母净利={ni:.2f}亿 ({latest['end_date']})")
        time.sleep(0.15)
    except Exception as e:
        print(f"  income {code}: {e}")
    
    # 现金流（近4期）
    try:
        cf = pro.cashflow(ts_code=code,
            fields='ts_code,end_date,n_cashflow_act,n_cash_flows_oper_act',
            limit=4)
        if cf is not None and len(cf):
            data['cashflow'] = cf.to_dict('records')
            latest = cf.iloc[0]
            ocf = float(latest['n_cashflow_act'])/1e8 if not pd.isna(latest['n_cashflow_act']) else None
            print(f"  经营现金流={ocf:.2f}亿 ({latest['end_date']})" if ocf else "  经营现金流: 无数据")
        time.sleep(0.15)
    except Exception as e:
        print(f"  cashflow {code}: {e}")
    
    # 资产负债表（近2期）
    try:
        balance = pro.balancesheet(ts_code=code,
            fields='ts_code,end_date,total_assets,total_hldr_eqy_exc_min_int,goodwill,accounts_receiv,money_cap,total_liab',
            limit=2)
        if balance is not None and len(balance):
            data['balance'] = balance.to_dict('records')
            b0 = balance.iloc[0]
            assets = float(b0['total_assets'])/1e8 if not pd.isna(b0['total_assets']) else None
            equity = float(b0['total_hldr_eqy_exc_min_int'])/1e8 if not pd.isna(b0['total_hldr_eqy_exc_min_int']) else None
            ar = float(b0['accounts_receiv'])/1e8 if not pd.isna(b0['accounts_receiv']) else None
            gw = float(b0['goodwill'])/1e8 if not pd.isna(b0['goodwill']) else None
            print(f"  总资产={assets:.1f}亿, 股东权益={equity:.1f}亿, 应收账款={ar:.1f}亿, 商誉={gw:.2f}亿")
        time.sleep(0.15)
    except Exception as e:
        print(f"  balancesheet {code}: {e}")
    
    # 下一期财报信息
    try:
        dd = pro.disclosure_date(ts_code=code, end_date='20260630')
        if dd is not None and len(dd):
            data['disclosure'] = dd.to_dict('records')
            print(f"  财报披露日: {dd.iloc[0].to_dict()}")
        time.sleep(0.11)
    except Exception as e:
        print(f"  disclosure_date {code}: {e}")
    
    results[code] = data

# 保存结果
with open(r'data\detail_560390_result.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
print(f"\n\n详细数据已保存到 data\\detail_560390_result.json")

# 打印汇总
print("\n\n" + "="*60)
print("13家候选公司汇总:")
print("="*60)
for code, weight in candidates:
    d = results.get(code, {})
    name = d.get('name', name_map.get(code, '?'))
    close = d.get('close', '?')
    mv = d.get('total_mv', '?')
    pe = d.get('pe_ttm', '?')
    dv = d.get('dv_ttm', '?')
    print(f"  {code} {name:<8} 权重{weight:.3f}% 价格{close} 市值{mv:.0f}亿 PE{pe:.1f}x 股息{dv}%" if isinstance(mv, float) and isinstance(pe, float) else f"  {code} {name} 权重{weight}%")
