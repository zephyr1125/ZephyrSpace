import os
import re
import json
import gzip
from pathlib import Path
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

ROOT = Path(r"E:\ObsidianVaults\ZephyrSpace")
load_dotenv(ROOT / '.env')
LX_TOKEN = os.getenv('LIXINGER_TOKEN')

HEADERS = {
    'Accept-Encoding': 'gzip',
    'User-Agent': 'Mozilla/5.0'
}


def lx_post(path, payload):
    resp = requests.post(
        f'https://open.lixinger.com/api/{path}',
        json={**payload, 'token': LX_TOKEN},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    try:
        return json.loads(gzip.decompress(resp.content))
    except Exception:
        return resp.json()


def last_trading_day():
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def get_cninfo_announcements(page_size=50):
    url = 'https://www.cninfo.com.cn/new/hisAnnouncement/query'
    data = {
        'pageNum': 1,
        'pageSize': page_size,
        'column': 'szse',
        'tabName': 'fulltext',
        'plate': 'sz',
        'stock': '300442,gssh06000442',
        'searchkey': '',
        'secid': '',
        'category': '',
        'trade': '',
        'seDate': '2021-01-01~2026-05-22',
        'sortName': '',
        'sortType': '',
        'isHLtitle': 'true'
    }
    r = requests.post(url, data=data, headers={**HEADERS, 'Referer': 'https://www.cninfo.com.cn/'}, timeout=30)
    r.raise_for_status()
    return r.json()


def download_text(url, path):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def extract_pdf_text(pdf_path):
    try:
        from pypdf import PdfReader
    except Exception as e:
        return f'PYPDF_IMPORT_ERROR: {e}'
    reader = PdfReader(str(pdf_path))
    texts = []
    for p in reader.pages[:30]:
        try:
            texts.append(p.extract_text() or '')
        except Exception:
            texts.append('')
    return '\n'.join(texts)


trade_date = last_trading_day()
out_dir = ROOT / 'scripts' / 'runze_deep_data'
out_dir.mkdir(exist_ok=True)

result = {'trade_date': trade_date}

val = lx_post('cn/company/fundamental/non_financial', {
    'stockCodes': ['300442'],
    'date': trade_date,
    'metricsList': ['pe_ttm', 'pb', 'mc']
})
result['val'] = val

annuals = {}
for yr in ['2024-12-31', '2023-12-31', '2022-12-31']:
    fs = lx_post('cn/company/fs/non_financial', {
        'stockCodes': ['300442'],
        'date': yr,
        'metricsList': ['y.ps.toi.t', 'y.ps.np.t', 'y.bs.ta.t', 'y.bs.tl.t']
    })
    annuals[yr] = fs
result['annuals'] = annuals

candle = lx_post('cn/company/candlestick', {
    'stockCode': '300442',
    'startDate': trade_date,
    'endDate': trade_date,
    'adjustmentType': '1',
    'type': 'day'
})
result['candle'] = candle

result['dividend'] = lx_post('cn/company/dividend', {
    'stockCode': '300442',
    'startDate': '2019-01-01',
    'endDate': trade_date
})
result['mgr_change'] = lx_post('cn/company/senior-executive-shares-change', {
    'stockCode': '300442',
    'startDate': '2022-01-01',
    'endDate': trade_date
})
result['major_change'] = lx_post('cn/company/major-shareholders-shares-change', {
    'stockCode': '300442',
    'startDate': '2022-01-01',
    'endDate': trade_date
})
try:
    result['pledge'] = lx_post('cn/company/pledge', {
        'stockCode': '300442',
        'startDate': '2021-01-01',
        'endDate': trade_date
    })
except Exception as e:
    result['pledge_error'] = str(e)
result['measures'] = lx_post('cn/company/measures', {
    'stockCode': '300442',
    'startDate': '2021-01-01',
    'endDate': trade_date
})
try:
    result['inquiry'] = lx_post('cn/company/inquiry', {
        'stockCode': '300442',
        'startDate': '2021-01-01',
        'endDate': trade_date
    })
except Exception as e:
    result['inquiry_error'] = str(e)

em_url = (
    'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL'
    '&filter=(SECURITY_CODE%3D%22300442%22)&pageNumber=1&pageSize=8'
)
result['eastmoney'] = requests.get(em_url, timeout=30, headers=HEADERS).json()

annual_report = {
    'title': '2025年年度报告',
    'announcementId': '1225090821',
    'url': 'http://static.cninfo.com.cn/finalpage/2026-04-10/1225090821.PDF'
}
summary_report = {
    'title': '2025年年度报告摘要',
    'announcementId': '1225091631',
    'url': 'http://static.cninfo.com.cn/finalpage/2026-04-10/1225091631.PDF'
}
audit_report = {
    'title': '2025年年度审计报告',
    'announcementId': '1225090823',
    'url': 'http://static.cninfo.com.cn/finalpage/2026-04-10/1225090823.PDF'
}
result['annual_report_meta'] = annual_report
result['annual_summary_meta'] = summary_report
result['audit_report_meta'] = audit_report

for key, meta, filename in [
    ('annual_report', annual_report, 'runze_2025_annual_report.pdf'),
    ('annual_summary', summary_report, 'runze_2025_annual_summary.pdf'),
    ('audit_report', audit_report, 'runze_2025_audit_report.pdf'),
]:
    pdf_path = out_dir / filename
    download_text(meta['url'], pdf_path)
    text = extract_pdf_text(pdf_path)
    result[f'{key}_pdf'] = str(pdf_path)
    result[f'{key}_text_head'] = text[:40000]

annual_text = result.get('annual_report_text_head', '')
audit_text = result.get('audit_report_text_head', '')
patterns = {
    'audit_firm': r'会计师事务所名称[\s:：]*([^\n]{2,120})',
    'audit_opinion': r'审计意见类型[\s:：]*([^\n]{2,40})',
    'chairman': r'法定代表人[\s:：]*([^\n]{2,20})',
    'chairman2': r'董事长[\s:：]*([^\n]{2,20})',
    'gm': r'总经理[\s:：]*([^\n]{2,20})',
    'controller': r'实际控制人[\s:：]*([^\n]{2,60})',
}
extracted = {}
for k, p in patterns.items():
    m = re.search(p, annual_text)
    if m:
        extracted[k] = m.group(1).strip()
for k, p in {
    'audit_firm_audit_report': r'我们审计了[^\n]*?会计师事务所[（(][^\n]{0,30}[)）]?',
    'audit_date': r'二〇二六年[一二三四五六七八九十]+月[一二三四五六七八九十]+日'
}.items():
    m = re.search(p, audit_text)
    if m:
        extracted[k] = m.group(0).strip()
result['annual_report_extracted'] = extracted

# basic formatted summary
print('交易日:', trade_date)
val_data = (val.get('data') or [{}])[0]
print('VAL:', json.dumps(val_data, ensure_ascii=False, indent=2))
for yr, fs in annuals.items():
    d = (fs.get('data') or [{}])[0]
    y = d.get('y', {})
    toi = y.get('ps', {}).get('toi', {}).get('t')
    np_ = y.get('ps', {}).get('np', {}).get('t')
    ta = y.get('bs', {}).get('ta', {}).get('t')
    tl = y.get('bs', {}).get('tl', {}).get('t')
    se = (ta - tl) if isinstance(ta, (int, float)) and isinstance(tl, (int, float)) else None
    print(f'{yr}: 营收={toi}, 净利={np_}, 总资产={ta}, 总负债={tl}, 净资产={se}')
print('CANDLE:', json.dumps(candle, ensure_ascii=False)[:800])
print('DIV count:', len(result['dividend'].get('data') or []))
print('MGR_CHANGE count:', len(result['mgr_change'].get('data') or []))
print('MAJOR_CHANGE count:', len(result['major_change'].get('data') or []))
print('MEASURES count:', len(result['measures'].get('data') or []))
print('INQUIRY count:', len((result.get('inquiry') or {}).get('data') or []))
for d in (result['eastmoney'].get('result') or {}).get('data', []):
    print('EM:', d.get('QDATE'), 'ROE=', d.get('WEIGHTAVG_ROE'), 'OCF/股=', d.get('MGJYXJJE'), '净利=', d.get('PARENT_NETPROFIT'), '营收=', d.get('TOTAL_OPERATE_INCOME'), '毛利率=', d.get('XSMLL'), '资产负债率=', d.get('ZCFZL'))
print('CNINFO annual report meta:', json.dumps(annual_report, ensure_ascii=False, indent=2))
print('CNINFO annual summary meta:', json.dumps(summary_report, ensure_ascii=False, indent=2))
print('CNINFO audit report meta:', json.dumps(audit_report, ensure_ascii=False, indent=2))
print('EXTRACTED:', json.dumps(result.get('annual_report_extracted', {}), ensure_ascii=False, indent=2))

(ROOT / 'scripts' / 'runze_deep_data' / 'runze_deep_data.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('JSON saved to', ROOT / 'scripts' / 'runze_deep_data' / 'runze_deep_data.json')
