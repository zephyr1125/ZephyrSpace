"""解析用户提供的931994成分股JSON并输出全量成分股列表"""
import json

with open(r'C:\Users\zephy\.copilot\session-state\187bb1a3-92ae-4144-96de-043d3106c633\files\paste-1777725802487.txt', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['data']
print(f'Total records: {len(records)}')

dates = sorted(set(r['date'][:10] for r in records))
print(f'Unique dates ({len(dates)}): {dates[:3]} ... {dates[-3:]}')

latest_date = dates[-1]
latest = [r for r in records if r['date'].startswith(latest_date)]
latest.sort(key=lambda x: x.get('weighting', 0), reverse=True)
print(f'Latest date: {latest_date}, 成分股数: {len(latest)}')
print()
print('全量成分股（按权重降序）:')
for i, s in enumerate(latest, 1):
    print(f'{i:3}. {s["stockCode"]:10} {s["weighting"]*100:.4f}%')

all_codes = [s['stockCode'] for s in latest]
print(f'\nCodes list ({len(all_codes)}):', all_codes)
