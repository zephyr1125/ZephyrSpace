import os, time, json
import tushare as ts
import akshare as ak
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv(r'E:\ObsidianVaults\ZephyrSpace\.env')
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

industries = [
    {'lx_code': '330000', 'ak_code': '801110', 'name': '家用电器'},
    {'lx_code': '350000', 'ak_code': '801130', 'name': '纺织服饰'},
    {'lx_code': '360000', 'ak_code': '801140', 'name': '轻工制造'},
    {'lx_code': '770000', 'ak_code': '801980', 'name': '美容护理'},
    {'lx_code': '460000', 'ak_code': '801210', 'name': '社会服务'},
]

roe_results = {}

for ind in industries:
    ak_code = ind['ak_code']
    name = ind['name']
    print(f"\n=== {name} ===")

    try:
        df_comp = ak.index_component_sw(symbol=ak_code)
        df_comp['最新权重'] = pd.to_numeric(df_comp['最新权重'], errors='coerce')
        total_comp = len(df_comp)

        # Top20 by weight
        top20 = df_comp.nlargest(20, '最新权重').copy()
        cr5 = df_comp.nlargest(5, '最新权重')['最新权重'].sum()
        cr10 = df_comp.nlargest(10, '最新权重')['最新权重'].sum()
        print(f"  总成分股: {total_comp}, CR5={cr5:.1f}%, CR10={cr10:.1f}%")

        total_w, roe_sum, rev_sum, rev_w = 0, 0, 0, 0
        top20_details = []

        for _, row in top20.iterrows():
            raw_code = str(row['证券代码']).zfill(6)
            # 判断交易所
            if raw_code.startswith('6'):
                code = raw_code + '.SH'
            elif raw_code.startswith(('0', '3')):
                code = raw_code + '.SZ'
            elif raw_code.startswith('4') or raw_code.startswith('8'):
                code = raw_code + '.BJ'
            else:
                code = raw_code + '.SZ'
            w = float(row['最新权重'])

            try:
                r2 = pro.fina_indicator(ts_code=code, fields='ts_code,end_date,roe,or_yoy', limit=6)
                annual = r2[r2['end_date'].str.endswith('1231')] if len(r2) else r2
                if len(annual):
                    roe_val = annual.iloc[0]['roe']
                    or_yoy = annual.iloc[0]['or_yoy']
                    end_date = annual.iloc[0]['end_date']
                    if not pd.isna(roe_val) and float(roe_val) > 0:
                        roe_sum += float(roe_val) * w
                        total_w += w
                    if not pd.isna(or_yoy):
                        rev_sum += float(or_yoy) * w
                        rev_w += w
                    top20_details.append({
                        'code': code,
                        'name': row['证券名称'],
                        'weight': round(w, 2),
                        'roe': round(float(roe_val), 1) if not pd.isna(roe_val) else None,
                        'or_yoy': round(float(or_yoy), 1) if not pd.isna(or_yoy) else None,
                        'end_date': end_date,
                    })
            except Exception as e2:
                print(f"    {code} 失败: {e2}")
            time.sleep(0.12)

        weighted_roe = roe_sum / total_w if total_w > 0 else None
        weighted_rev = rev_sum / rev_w if rev_w > 0 else None
        print(f"  加权ROE={round(weighted_roe,1) if weighted_roe else None}%")
        print(f"  加权营收同比={round(weighted_rev,1) if weighted_rev else None}%")
        print(f"  Top5: {[(d['name'], d['weight'], d['roe']) for d in top20_details[:5]]}")

        roe_results[ind['lx_code']] = {
            'name': name,
            'total_comp': int(total_comp),
            'weighted_roe': round(weighted_roe, 1) if weighted_roe else None,
            'weighted_rev_yoy': round(weighted_rev, 1) if weighted_rev else None,
            'cr5': round(cr5, 1),
            'cr10': round(cr10, 1),
            'top10': [{k: v for k, v in d.items()} for d in top20_details[:10]],
        }

    except Exception as e:
        print(f"  失败: {e}")
        roe_results[ind['lx_code']] = {'name': name, 'error': str(e)}

    time.sleep(0.5)

print("\n\n=== ROE SUMMARY ===")
for lx, v in roe_results.items():
    print(f"{v['name']}: ROE={v.get('weighted_roe')}%, 营收同比={v.get('weighted_rev_yoy')}%, CR5={v.get('cr5')}%, CR10={v.get('cr10')}%, 成分股={v.get('total_comp')}")

# 保存为文件以便后续使用
with open('scripts/_batch_b_roe_results.json', 'w', encoding='utf-8') as f:
    json.dump(roe_results, f, ensure_ascii=False, indent=2, default=str)
print("\nROE结果已保存到 scripts/_batch_b_roe_results.json")
