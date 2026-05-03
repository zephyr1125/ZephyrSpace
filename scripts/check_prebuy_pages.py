"""检查哪些公司页面存在及其更新日期"""
import json, os, re
from pathlib import Path

with open('data/candidate_pool_highroe_lowpe.json', encoding='utf-8') as f:
    d = json.load(f)
companies = d['companies']

company_dir = Path('01-公司')
results = []

for c in companies:
    name = c['name'].replace(' ', '')
    matches = list(company_dir.glob(f'*{name}*.md')) + list(company_dir.glob(f'{name}.md'))
    # 去重
    matches = list(set(matches))
    found = None
    found_date = None
    skip = False
    
    if matches:
        found = matches[0].name
        content = matches[0].read_text(encoding='utf-8', errors='ignore')
        m = re.search(r'最后更新日期[：:]\s*(\d{4}-\d{2}-\d{2})', content)
        if m:
            found_date = m.group(1)
            if found_date.startswith('2026-05'):
                skip = True
    
    results.append({
        'code': c['code'],
        'name': name,
        'found': found,
        'found_date': found_date,
        'skip': skip,
        'roe': c['roe_annual'],
        'pe_pct': c['pe_3y_pct'],
        'in_wl': c.get('in_watchlist', False)
    })

skip_list = [r for r in results if r['skip']]
todo_list = [r for r in results if not r['skip']]
has_page = [r for r in todo_list if r['found']]
no_page = [r for r in todo_list if not r['found']]

print(f'总计: {len(results)} 家')
print(f'跳过（5月已更新）: {len(skip_list)} 家')
print(f'需要处理: {len(todo_list)} 家')
print(f'  有页面需删除重跑: {len(has_page)} 家')
print(f'  无页面新建: {len(no_page)} 家')
print()

if skip_list:
    print('=== 跳过 ===')
    for r in skip_list:
        print(f'  {r["name"]} ({r["found_date"]})')
print()

if has_page:
    print('=== 有页面需删除重跑 ===')
    for r in has_page:
        print(f'  {r["name"]} -> {r["found"]} (更新: {r["found_date"]})')
print()

print('=== 无页面新建 ===')
for r in no_page:
    print(f'  {r["name"]} ({r["code"]}) ROE={r["roe"]:.1f}%')

# 保存任务列表
import json as j2
with open('data/prebuy_tasks_highroe.json', 'w', encoding='utf-8') as f:
    j2.dump({'skip': skip_list, 'todo': todo_list}, f, ensure_ascii=False, indent=2)
print('\n任务列表已保存到 data/prebuy_tasks_highroe.json')
