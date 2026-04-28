import json
with open('data/prebuy_931897_data.json', encoding='utf-8') as f:
    d = json.load(f)
for code, v in d.items():
    print(f"{v['name']}({code}): 现价{v.get('close')} PE{v.get('pe_ttm')} DY{v.get('dv_ttm')}% ROE{v.get('roe')}% 市值{v.get('total_mv_yi')}亿 OCF比{v.get('ocf_ratio')} 商誉{v.get('gw_ratio')}% 60日高{v.get('high_60')} 低{v.get('low_60')} 营收同比{v.get('or_yoy')}% next={v.get('next_earnings_date')}({v.get('next_earnings_type')})")
