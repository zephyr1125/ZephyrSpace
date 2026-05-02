"""
高ROE + PE历史低位 交叉筛选脚本
从67家PE低位候选中，筛出年报ROE >= 15%的公司
"""
import json, os, time
import tushare as ts
from dotenv import load_dotenv

load_dotenv()
pro = ts.pro_api(os.getenv('TUSHARE_TOKEN'))

with open('data/candidate_pool_pe_pct.json', encoding='utf-8') as f:
    data = json.load(f)

low_pe = [d for d in data if d.get('pe_3y_pct') is not None and d['pe_3y_pct'] <= 20]
print(f'PE低位: {len(low_pe)} 家，开始拉取年报ROE...')

results = []
errors = []

for i, company in enumerate(low_pe):
    ts_code = company['code']
    try:
        df = pro.fina_indicator(ts_code=ts_code, fields='ts_code,end_date,roe', limit=8)
        annual = df[df['end_date'].str.endswith('1231')]
        if len(annual) > 0:
            latest = annual.iloc[0]
            roe = float(latest['roe']) if latest['roe'] is not None else None
            end_date = latest['end_date']
        else:
            roe, end_date = None, None
        results.append({**company, 'roe_annual': roe, 'roe_date': end_date})
        if (i+1) % 10 == 0:
            print(f'  进度: {i+1}/{len(low_pe)}')
        time.sleep(0.05)
    except Exception as e:
        errors.append(ts_code)
        results.append({**company, 'roe_annual': None, 'roe_date': None})

# 筛出 ROE >= 15%
high_roe = [r for r in results if r['roe_annual'] is not None and r['roe_annual'] >= 15]
high_roe.sort(key=lambda x: -x['roe_annual'])

print(f'\n【高ROE + PE低位候选】 ROE年报>=15% 共 {len(high_roe)} 家\n')
print(f"{'公司':<12}{'行业':<16}{'PE分位%':>8}{'PE':>6}{'PB':>6}{'ROE%':>8}{'市值亿':>8}{'在WL':>6}")
print('-' * 70)
for r in high_roe:
    wl = '✅' if r.get('in_watchlist') else ''
    print(f"{r['name']:<12}{r['industry']:<16}{r['pe_3y_pct']:>8.1f}{r['pe']:>6.1f}{r['pb']:>6.2f}{r['roe_annual']:>8.1f}{r['mc_亿']:>8.0f}{wl:>6}")

if errors:
    print(f'\n拉取失败: {errors}')

# 保存结果
output = {
    'strategy': '高ROE + PE历史低位',
    'criteria': {
        'pe_3y_pct_max': 20,
        'roe_annual_min': 15,
        'source_pool': '全市场候选池(234家同花顺初筛)'
    },
    'count': len(high_roe),
    'companies': high_roe
}
with open('data/candidate_pool_highroe_lowpe.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f'\n已保存到 data/candidate_pool_highroe_lowpe.json')
