import json
with open('data/stock_watchlist.json', encoding='utf-8') as f:
    wl = json.load(f)

print('=== CORE ===')
for c in wl['watchlists']['core']:
    print(f"  {c.get('code')} {c.get('name')}: close={c.get('last_close')} dv={c.get('dv_ttm')} next={c.get('next_earnings_date')} bands={c.get('price_bands')}")
print('=== GROWTH sample (绿电) ===')
green_growth = {'600023.SH','600098.SH','600642.SH'}
for c in wl['watchlists']['growth']:
    if c.get('code') in green_growth or '电' in c.get('name','') or '能' in c.get('name',''):
        print(f"  {c.get('code')} {c.get('name')}: close={c.get('last_close')} dv={c.get('dv_ttm')} next={c.get('next_earnings_date')} bands={c.get('price_bands')}")
print('=== RADAR (绿电相关) ===')
green_radar = {'600642.SH','600795.SH','600027.SH'}
for c in wl['watchlists']['radar']:
    if c.get('code') in green_radar:
        print(f"  {c.get('code')} {c.get('name')}: close={c.get('last_close')} dv={c.get('dv_ttm')} next={c.get('next_earnings_date')} bands={c.get('price_bands')}")
        print(f"    trigger: {c.get('entry_trigger')}")
print('total core/growth/radar:', len(wl['watchlists']['core']), len(wl['watchlists']['growth']), len(wl['watchlists']['radar']))
print('schema_version:', wl['schema_version'])
