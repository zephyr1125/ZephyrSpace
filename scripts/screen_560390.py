"""
Step 2: 电网设备ETF(560390)成分股量化粗筛
使用中证电网设备主题指数(931994.CSI)的80只成分股
"""
import tushare as ts, os, time, pandas as pd, json
from dotenv import load_dotenv
load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 从 931994.CSI 获取最新成分股权重
df = pro.index_weight(index_code='931994.CSI')
latest = df['trade_date'].max()
all_stocks = df[df['trade_date'] == latest].sort_values('weight', ascending=False).copy()
print(f"指数: 931994.CSI 中证电网设备主题指数")
print(f"成分股数量: {len(all_stocks)} 只 (权重日期: {latest})")

trade_date = '20260424'

# 拉取 daily_basic
db_rows = []
print("\n正在拉取 daily_basic...")
for i, row in all_stocks.iterrows():
    code = row['con_code']
    weight = row['weight']
    try:
        r = pro.daily_basic(
            ts_code=code,
            trade_date=trade_date,
            fields='ts_code,pe_ttm,total_mv,pb,dv_ttm'
        )
        if r is not None and len(r):
            d = r.iloc[0].to_dict()
            d['weight'] = weight
            db_rows.append(d)
        else:
            print(f"  daily_basic {code}: 无数据 (停牌?)")
            db_rows.append({'ts_code': code, 'pe_ttm': None, 'total_mv': None, 'pb': None, 'dv_ttm': None, 'weight': weight})
        time.sleep(0.11)
    except Exception as e:
        print(f"  daily_basic {code}: {e}")

# 拉取 fina_indicator
fi_rows = []
print("\n正在拉取 fina_indicator...")
for i, row in all_stocks.iterrows():
    code = row['con_code']
    try:
        r = pro.fina_indicator(
            ts_code=code,
            fields='ts_code,roe,or_yoy,netprofit_yoy,ocfps,eps,bps,grossprofit_margin',
            limit=1
        )
        if r is not None and len(r):
            fi_rows.append(r.iloc[0].to_dict())
        else:
            fi_rows.append({'ts_code': code, 'roe': None, 'or_yoy': None})
        time.sleep(0.11)
    except Exception as e:
        print(f"  fina_indicator {code}: {e}")

db_df = pd.DataFrame(db_rows)
fi_df = pd.DataFrame(fi_rows)
merged = db_df.merge(fi_df, on='ts_code', how='left')

# 单位转换：total_mv 万元 -> 亿元
merged['market_cap_bn'] = merged['total_mv'] / 10000

# 粗筛条件
def screen(row):
    mv = row.get('market_cap_bn')
    if pd.isna(mv) or mv < 40:
        return f'FAIL: 市值<40亿({mv:.1f}亿)' if not pd.isna(mv) else 'FAIL: 市值无数据'
    
    pe = row.get('pe_ttm')
    if pd.isna(pe) or pe <= 0:
        return 'FAIL: 亏损/PE无效'
    if pe > 60:
        return f'FAIL: PE>{pe:.1f}x>60x'
    
    roe = row.get('roe')
    if pd.isna(roe) or roe < 9.6:
        return f'FAIL: ROE<9.6%({roe:.1f}%)' if not pd.isna(roe) else 'FAIL: ROE无数据'
    
    or_yoy = row.get('or_yoy')
    if pd.isna(or_yoy) or or_yoy < -12:
        return f'FAIL: 营收同比<-12%({or_yoy:.1f}%)' if not pd.isna(or_yoy) else 'FAIL: 营收同比无数据'
    
    warn = []
    if roe < 12:
        warn.append('⚠️ROE偏低')
    if or_yoy < -10:
        warn.append('⚠️营收同比偏低')
    return 'PASS' + (' ' + ' '.join(warn) if warn else '')

merged['screen_result'] = merged.apply(screen, axis=1)
passed = merged[merged['screen_result'].str.startswith('PASS')].copy()

print(f"\n{'='*60}")
print(f"全成分 {len(merged)} 只 -> 通过筛选 {len(passed)} 只")
print(f"{'='*60}")

if len(passed) > 0:
    show_cols = ['ts_code','weight','market_cap_bn','pe_ttm','pb','roe','or_yoy','screen_result']
    result = passed[show_cols].sort_values('roe', ascending=False)
    print("\n通过粗筛的公司（按ROE降序）:")
    print(result.to_string(index=False))
    
    # 候选上限15家
    if len(passed) > 15:
        print(f"\n候选超过15家({len(passed)})，取ROE前15家:")
        passed = passed.sort_values('roe', ascending=False).head(15)
        print(passed[show_cols].to_string(index=False))

print(f"\n{'='*60}")
print("未通过筛选的公司（前20）:")
failed = merged[~merged['screen_result'].str.startswith('PASS')]
print(failed[['ts_code','weight','market_cap_bn','pe_ttm','roe','or_yoy','screen_result']].head(20).to_string(index=False))

# 保存结果
result_data = {
    'all_stocks': merged[['ts_code','weight','market_cap_bn','pe_ttm','pb','dv_ttm','roe','or_yoy','netprofit_yoy','screen_result']].to_dict('records'),
    'passed': passed[['ts_code','weight','market_cap_bn','pe_ttm','pb','dv_ttm','roe','or_yoy','netprofit_yoy','screen_result']].to_dict('records'),
    'failed': failed[['ts_code','weight','market_cap_bn','pe_ttm','roe','or_yoy','screen_result']].to_dict('records')
}
with open(r'data\screen_560390_result.json', 'w', encoding='utf-8') as f:
    json.dump(result_data, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到 data\\screen_560390_result.json")
