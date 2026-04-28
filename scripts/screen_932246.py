"""932246 中证储能电池指数 粗筛脚本 - 2026-04-27"""
import tushare as ts, os, time, json
from dotenv import load_dotenv

load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

TRADE_DATE = '20260427'  # 最近交易日
INDEX_CODE = '932246.CSI'
MIN_MV = 40   # 亿元
MIN_ROE = 12  # %
MIN_OR_YOY = -10  # %

# === 1. 拉取全成分股 ===
print("=== 拉取成分股 ===")
df = pro.index_weight(index_code=INDEX_CODE)
print(f"index_weight 返回总行数: {len(df)}")
if len(df) == 0:
    print("尝试 index_member...")
    df = pro.index_member(index_code=INDEX_CODE)
    print(f"index_member 返回: {len(df)} 行")
    stocks = df[['ts_code']].rename(columns={'ts_code':'con_code'})
    stocks['weight'] = 0
else:
    latest_date = df['trade_date'].max()
    print(f"最新权重日期: {latest_date}")
    latest = df[df['trade_date'] == latest_date].sort_values('weight', ascending=False)
    print(f"成分股数量: {len(latest)}")
    stocks = latest[['con_code', 'weight']].copy()

print("\n前15成分股:")
print(stocks.head(15).to_string(index=False))

# === 2. 逐只拉取 daily_basic + fina_indicator ===
print("\n=== 开始逐只抓取数据 ===")
results = []
for i, row in stocks.iterrows():
    code = row['con_code']
    weight = row.get('weight', 0)
    
    # daily_basic
    try:
        db = pro.daily_basic(ts_code=code, trade_date=TRADE_DATE,
                              fields='ts_code,pe_ttm,total_mv,pb')
        time.sleep(0.12)
    except Exception as e:
        print(f"  {code} daily_basic error: {e}")
        db = None
    
    # fina_indicator - 优先年报
    try:
        fi = pro.fina_indicator(ts_code=code,
                                 fields='ts_code,end_date,roe,or_yoy', limit=8)
        time.sleep(0.12)
    except Exception as e:
        print(f"  {code} fina_indicator error: {e}")
        fi = None
    
    pe_ttm, total_mv_yi, pb = None, None, None
    roe, or_yoy, fin_period = None, None, None
    
    if db is not None and len(db) > 0:
        r = db.iloc[0]
        pe_ttm = r['pe_ttm']
        total_mv_yi = r['total_mv'] / 10000 if r['total_mv'] else None
        pb = r['pb']
    
    if fi is not None and len(fi) > 0:
        annual = fi[fi['end_date'].str.endswith('1231')]
        row_fi = annual.iloc[0] if len(annual) > 0 else fi.iloc[0]
        roe = row_fi['roe']
        or_yoy = row_fi['or_yoy']
        fin_period = row_fi['end_date']
    
    # 过滤条件
    skip_reason = []
    passed = True
    
    if total_mv_yi is None or total_mv_yi < MIN_MV:
        skip_reason.append(f"市值{total_mv_yi:.0f}亿<{MIN_MV}亿" if total_mv_yi else "市值无数据")
        passed = False
    if pe_ttm is None or pe_ttm <= 0:
        skip_reason.append(f"PE={pe_ttm}（亏损/无数据）")
        passed = False
    if roe is None or roe < MIN_ROE:
        skip_reason.append(f"ROE={roe:.1f}%<{MIN_ROE}%" if roe else "ROE无数据")
        passed = False
    if or_yoy is None or or_yoy < MIN_OR_YOY:
        skip_reason.append(f"营收同比={or_yoy:.1f}%<{MIN_OR_YOY}%" if or_yoy is not None else "营收同比无数据")
        passed = False
    
    # 边界模糊标注（偏离门槛<=20%）
    borderline = False
    if roe is not None and not passed and roe >= MIN_ROE * 0.8 and roe < MIN_ROE:
        borderline = True
    
    results.append({
        'con_code': code,
        'weight': weight,
        'total_mv_yi': total_mv_yi,
        'pe_ttm': pe_ttm,
        'pb': pb,
        'roe': roe,
        'or_yoy': or_yoy,
        'fin_period': fin_period,
        'passed': passed,
        'borderline': borderline,
        'skip_reason': '；'.join(skip_reason) if skip_reason else ''
    })
    
    status = "✅" if passed else ("⚠️" if borderline else "❌")
    mv_s = f"{total_mv_yi:.0f}亿" if total_mv_yi is not None else "N/A"
    pe_s = f"{pe_ttm:.1f}" if pe_ttm is not None else "N/A"
    roe_s = f"{roe:.1f}%" if roe is not None else "N/A"
    yoy_s = f"{or_yoy:.1f}%" if or_yoy is not None else "N/A"
    print(f"  {status} {code}  市值={mv_s}  PE={pe_s}  ROE={roe_s}  营收同比={yoy_s}  ({fin_period})")

# === 3. 汇总输出 ===
passed_list = [r for r in results if r['passed']]
failed_list = [r for r in results if not r['passed']]

print(f"\n=== 粗筛结果：{len(stocks)}只成分股 → {len(passed_list)}只通过 ===")
print("\n✅ 通过筛选（按ROE降序）:")
passed_sorted = sorted(passed_list, key=lambda x: x['roe'] or 0, reverse=True)
# 取前15
top15 = passed_sorted[:15]
for r in top15:
    print(f"  {r['con_code']}  权重={r['weight']:.2f}%  市值={r['total_mv_yi']:.0f}亿  PE={r['pe_ttm']:.1f}  ROE={r['roe']:.1f}%  营收同比={r['or_yoy']:.1f}%")

if len(passed_sorted) > 15:
    print(f"\n（超过15家，截取前15家进入深度分析）")

print("\n❌ 未通过筛选（前20）:")
for r in failed_list[:20]:
    print(f"  {r['con_code']}  权重={r['weight']:.2f}%  市值={r['total_mv_yi']}亿  PE={r['pe_ttm']}  ROE={r['roe']}%  营收={r['or_yoy']}%  原因: {r['skip_reason']}")

# 保存结果
with open('data/screen_932246_result.json', 'w', encoding='utf-8') as f:
    json.dump({'all': results, 'passed': top15, 'trade_date': TRADE_DATE}, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存至 data/screen_932246_result.json")
