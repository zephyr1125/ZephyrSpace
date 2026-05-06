"""工商银行(601398) PreBuy 数据收集脚本"""
import requests, os, sys, json
from dotenv import load_dotenv
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

LX_TOKEN = os.getenv('LIXINGER_TOKEN')
LX_BASE = 'https://open.lixinger.com/api'
STOCK = '601398'
TRADE_DATE = '2026-04-30'  # 五一假期前最后交易日

def lx_post(path, payload):
    resp = requests.post(
        f'{LX_BASE}/{path}',
        json={**payload, 'token': LX_TOKEN},
        headers={'Accept-Encoding': 'gzip'}
    )
    return resp.json()

def section(title):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print('='*60)

# ── 1. 近60日K线 ─────────────────────────────────────────────
section('1. 近60日K线（当前价格/走势）')
r = lx_post('cn/company/candlestick', {
    'stockCode': STOCK,
    'startDate': '2026-02-01',
    'endDate': '2026-05-06',
    'type': 'lxr_fc_rights'
})
candles = sorted(r.get('data', []), key=lambda x: x['date'])
print(f'数据条数: {len(candles)}')
if candles:
    latest = candles[-1]
    cur = latest['close']
    high60 = max(d['high'] for d in candles)
    low60 = min(d['low'] for d in candles)
    p30 = candles[-30]['close'] if len(candles) >= 30 else None
    p60 = candles[0]['close']
    pct30 = (cur/p30 - 1)*100 if p30 else 0
    pct60 = (cur/p60 - 1)*100
    print(f'最新收盘: {cur} ({latest["date"][:10]})')
    print(f'近60日最高: {high60}  最低: {low60}')
    print(f'近30日涨跌: {pct30:.1f}%  近60日涨跌: {pct60:.1f}%')
    print('近10日行情:')
    for d in candles[-10:]:
        print(f'  {d["date"][:10]}  close={d["close"]}  vol={d.get("volume",0):.0f}')

# ── 2. PB估值分位（银行） ─────────────────────────────────────
section('2. PB估值历史分位（fundamental/bank）')
r2 = lx_post('cn/company/fundamental/bank', {
    'stockCodes': [STOCK],
    'startDate': TRADE_DATE,
    'endDate': TRADE_DATE,
    'metricsList': ['pb', 'pb.y3.cvpos', 'pb.y3.q2v', 'pb.y3.q5v', 'pb.y3.q8v', 'mc']
})
if r2.get('data'):
    d = r2['data'][0]
    pb = d.get('pb')
    mc = d.get('mc', 0) / 1e8
    cvpos = d.get('pb.y3.cvpos', 0)
    q2v = d.get('pb.y3.q2v')
    q5v = d.get('pb.y3.q5v')
    q8v = d.get('pb.y3.q8v')
    print(f'当前PB: {pb:.4f}')
    print(f'总市值: {mc:.0f}亿元')
    print(f'3年PB分位: {cvpos*100:.1f}%')
    print(f'P20(低位): {q2v}  P50(中位): {q5v}  P80(高位): {q8v}')
    # 计算price bands
    if pb and candles:
        bps = cur / pb
        print(f'每股净资产(BPS): {bps:.4f}')
        bands = [round(q8v * bps, 2), round(q5v * bps, 2), round(q2v * bps, 2)]
        print(f'price_bands(基础): {bands}')
        print(f'  红线(P80): {bands[0]}  中性底(P50): {bands[1]}  绿灯区起点(P20): {bands[2]}')

# ── 3. 财报数据（fs/bank） ────────────────────────────────────
section('3. 财报数据（fs/bank）')
fs_r = lx_post('cn/company/fs/bank', {
    'stockCode': STOCK,
    'startDate': '2022-01-01',
    'endDate': '2026-04-30'
})
fs_data = sorted(fs_r.get('data', []), key=lambda x: x.get('date',''))
print(f'财报条数: {len(fs_data)}')
# 打印最近4期关键字段
for item in fs_data[-6:]:
    dt = item.get('date','')[:10]
    # 营业收入
    rev = item.get('a.ps.toi.t')
    if rev is None:
        rev = item.get('y.ps.toi.t')
    # 净利润（归母）
    np_ = item.get('a.pr.np.t')
    if np_ is None:
        np_ = item.get('y.pr.np.t')
    # 经营现金流
    ocf = item.get('a.cf.oc.net.t')
    print(f'  {dt}: 营收={rev}  净利={np_}  OCF={ocf}')
# 打印原始字段（帮助识别可用字段）
if fs_data:
    sample = fs_data[-1]
    print('最新期原始字段(前30个):')
    keys = list(sample.keys())[:30]
    for k in keys:
        print(f'  {k}: {sample[k]}')

# ── 4. 分红历史 ───────────────────────────────────────────────
section('4. 分红历史（2020-2026）')
div_r = lx_post('cn/company/dividend', {
    'stockCode': STOCK,
    'startDate': '2020-01-01',
    'endDate': '2026-05-01'
})
divs = sorted(div_r.get('data', []), key=lambda x: x.get('date',''))
for d in divs:
    dt = d.get('date','')[:10]
    div_per = d.get('dividend', 0)
    ratio = d.get('annualNetProfitDividendRatio')
    total = d.get('dividendAmount')
    print(f'  {dt}: 每股{div_per}分  分红率={ratio}  总派现={total}')

# ── 5. 监管措施 ───────────────────────────────────────────────
section('5. 监管措施（measures，2021-2026）')
meas_r = lx_post('cn/company/measures', {
    'stockCode': STOCK,
    'startDate': '2021-01-01',
    'endDate': '2026-05-01'
})
measures = meas_r.get('data', [])
print(f'监管措施条数: {len(measures)}')
for m in measures[:10]:
    print(f'  {m.get("date","")[:10]} [{m.get("displayTypeText","")}] {m.get("linkText","")}')

# ── 6. 问询函 ─────────────────────────────────────────────────
section('6. 问询函（2021-2026）')
inq_r = lx_post('cn/company/inquiry', {
    'stockCode': STOCK,
    'startDate': '2021-01-01',
    'endDate': '2026-05-01'
})
inquiries = inq_r.get('data', [])
print(f'问询函条数: {len(inquiries)}')
for i in inquiries[:5]:
    print(f'  {i.get("date","")[:10]} [{i.get("displayTypeText","")}] {i.get("linkText","")}')

# ── 7. 大股东增减持 ───────────────────────────────────────────
section('7. 大股东增减持（2024-2026）')
maj_r = lx_post('cn/company/major-shareholders-shares-change', {
    'stockCode': STOCK,
    'startDate': '2024-01-01',
    'endDate': '2026-05-01'
})
major = maj_r.get('data', [])
print(f'大股东变动条数: {len(major)}')
for m in major[:10]:
    chg = m.get('changeQuantity', 0)
    action = 'REDUCE' if chg and chg < 0 else 'ADD'
    print(f'  {m.get("date","")[:10]} [{action}] {m.get("shareholderName","")} {chg} 股  均价={m.get("avgPrice")}')

# ── 8. 高管增减持 ─────────────────────────────────────────────
section('8. 高管增减持（2024-2026）')
exec_r = lx_post('cn/company/senior-executive-shares-change', {
    'stockCode': STOCK,
    'startDate': '2024-01-01',
    'endDate': '2026-05-01'
})
execs = exec_r.get('data', [])
print(f'高管变动条数: {len(execs)}')
for e in execs[:10]:
    print(f'  {e.get("date","")[:10]} {e.get("executiveName","")}({e.get("duty","")}) {e.get("changedShares","")}股  均价={e.get("avgPrice")}')

# ── 9. 股权质押 ───────────────────────────────────────────────
section('9. 股权质押')
ple_r = lx_post('cn/company/pledge', {
    'stockCode': STOCK,
    'startDate': '2023-01-01'
})
pledges = ple_r.get('data', [])
active = [p for p in pledges if not p.get('pledgeDischargeDate')]
print(f'质押记录: {len(pledges)}  未解除: {len(active)}')
for p in active[:5]:
    print(f'  出质人:{p.get("pledgor","")}  质权人:{p.get("pledgee","")}  占总股本:{p.get("pledgePercentageOfTotalEquity","")}%')

# ── 10. 限售解禁热度 ──────────────────────────────────────────
section('10. 限售解禁热度')
elr_r = lx_post('cn/company/hot/elr', {
    'stockCode': STOCK,
    'date': TRADE_DATE
})
elr = elr_r.get('data', [])
print(f'解禁热度数据: {len(elr)}条')
for e in elr[:3]:
    print(f'  {e}')

print('\n数据收集完成')
