import json
from datetime import datetime
from pathlib import Path
from statistics import quantiles
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parent
s=json.loads((R/'raw-S012-0506HK-monthly.json').read_text(encoding='utf-8'))['chart']['result'][0]
f=json.loads((R/'raw-S013-HKDCNY-monthly.json').read_text(encoding='utf-8'))['chart']['result'][0]
def mm(o):
    z={}
    for t,c in zip(o['timestamp'],o['indicators']['quote'][0]['close']):
        if c is not None:z[datetime.fromtimestamp(t,ZoneInfo('Asia/Hong_Kong')).strftime('%Y-%m')]=c
    return z
sm,fm=mm(s),mm(f); months=[m for m in sorted(set(sm)&set(fm)) if '2024-05'<=m<='2026-08' and m not in {'2025-03','2025-04','2026-03','2026-04'}]
p={2023:832.577,2024:860.535,2025:861.968}; sh=2797.223396; rows=[]
for m in months:
    y=2023 if m<='2025-02' else 2024 if m<='2026-02' else 2025
    rows.append({'month':m,'close_hkd':sm[m],'rmb_per_hkd':fm[m],'eps_fy':y,'static_pe':sm[m]*fm[m]/(p[y]/sh)})
q=quantiles(sorted(x['static_pe'] for x in rows),n=4,method='inclusive'); o={'count':len(rows),'rows':rows,'inclusive_q25_q50_q75':q,'locked_multiples':[8.46,9.17,11.54]}
(R/'historical-pe-sample.json').write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(o,ensure_ascii=False,indent=2))
