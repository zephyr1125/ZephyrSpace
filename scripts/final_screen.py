"""
燃气轮机 & 数据中心供配电主题 — 最终量化粗筛
使用：
- 理杏仁 fundamental (2026-04-28) → PE / PB / 市值 / 股息率
- 理杏仁 fs 2025-12-31 → 营收 / 净利润
- 理杏仁 fs 2024-12-31 → 营收（算同比）
- tushare fina_indicator → 年报 ROE（最可靠来源）
"""
import sys, os, json, requests, gzip, tushare as ts, pandas as pd
sys.path.insert(0, r'E:\ObsidianVaults\ZephyrSpace')
os.chdir(r'E:\ObsidianVaults\ZephyrSpace')
from dotenv import load_dotenv
load_dotenv()

LX_TOKEN = os.getenv('LIXINGER_TOKEN')
H = {'Accept-Encoding': 'gzip', 'Content-Type': 'application/json'}

def lx(path, payload):
    r = requests.post(
        f'https://open.lixinger.com/api/{path}',
        json=dict(payload, token=LX_TOKEN), headers=H
    )
    try: return json.loads(gzip.decompress(r.content))
    except: return json.loads(r.content)

def nested_get(d, *keys):
    """从嵌套 dict 安全取值"""
    for k in keys:
        if not isinstance(d, dict): return None
        d = d.get(k)
    return d

# ---- 候选代码 ----
gt_codes = ['600875','601727','002353','603308','300855','300034',
            '605123','601106','603169','002204','300091','603100']
dc_codes = ['002335','002518','688676','002363','688162','300274','688390']
all_codes = list(set(gt_codes + dc_codes))
all_codes_ts = [c + ('.SH' if c.startswith('6') or c.startswith('688') else '.SZ')
                for c in all_codes]

# ---- 1. 估值/市值 ----
print("1. 拉取估值/市值 (2026-04-28) ...")
val_res = lx('cn/company/fundamental/non_financial', {
    'stockCodes': all_codes,
    'date': '2026-04-28',
    'metricsList': ['pe_ttm', 'pb', 'mc', 'dyr']
})
val_dict = {d['stockCode']: d for d in val_res.get('data', [])}
print(f"   records: {len(val_dict)}")

# ---- 2. 2025 营收/净利 ----
print("2. 拉取2025年报营收/净利 ...")
fs25_res = lx('cn/company/fs/non_financial', {
    'stockCodes': all_codes,
    'date': '2025-12-31',
    'metricsList': ['y.ps.toi.t', 'y.ps.np.t']
})
fs25_dict = {}
for d in fs25_res.get('data', []):
    toi = nested_get(d, 'y', 'ps', 'toi', 't')
    np_ = nested_get(d, 'y', 'ps', 'np', 't')
    fs25_dict[d['stockCode']] = {'toi': toi, 'np': np_}
print(f"   records: {len(fs25_dict)}")

# ---- 3. 2024 营收（YoY分母）----
print("3. 拉取2024年报营收 ...")
fs24_res = lx('cn/company/fs/non_financial', {
    'stockCodes': all_codes,
    'date': '2024-12-31',
    'metricsList': ['y.ps.toi.t']
})
fs24_dict = {}
for d in fs24_res.get('data', []):
    toi = nested_get(d, 'y', 'ps', 'toi', 't')
    fs24_dict[d['stockCode']] = toi
print(f"   records: {len(fs24_dict)}")

# ---- 4. tushare 年报 ROE ----
print("4. 拉取年报ROE (tushare fina_indicator) ...")
pro = ts.pro_api(os.getenv('TUSHARE_TOKEN'))
roe_dict = {}
name_dict = {}
df_basic = pro.stock_basic(fields='ts_code,name')
for _, row in df_basic.iterrows():
    c = row['ts_code'].split('.')[0]
    name_dict[c] = row['name']

for ts_code in all_codes_ts:
    code = ts_code.split('.')[0]
    try:
        fi = pro.fina_indicator(ts_code=ts_code, fields='ts_code,end_date,roe', limit=5)
        # 取最近年报（end_date以1231结尾）
        annual = fi[fi['end_date'].str.endswith('1231')] if len(fi) > 0 else pd.DataFrame()
        if len(annual) > 0:
            roe_dict[code] = float(annual.iloc[0]['roe'])
        else:
            roe_dict[code] = None
    except Exception as e:
        print(f"   ROE 获取失败 {ts_code}: {e}")
        roe_dict[code] = None
print(f"   ROE obtained for {sum(1 for v in roe_dict.values() if v is not None)} companies")

# ---- 5. 合并数据 ----
result = {}
for code in all_codes:
    v  = val_dict.get(code, {})
    f25 = fs25_dict.get(code, {})
    toi24 = fs24_dict.get(code)
    toi25 = f25.get('toi')
    np25  = f25.get('np')

    mc  = v.get('mc')
    if mc: mc = mc / 1e8  # 转亿元

    pe  = v.get('pe_ttm')
    pb  = v.get('pb')
    dyr = v.get('dyr')
    if dyr: dyr = dyr * 100  # 转百分比

    roe = roe_dict.get(code)

    if toi25 and toi24 and toi24 != 0:
        yoy = (toi25 - toi24) / abs(toi24) * 100
    else:
        yoy = None

    result[code] = {
        'name': name_dict.get(code, code),
        'mc':   mc,
        'pe':   pe,
        'pb':   pb,
        'roe':  roe,
        'yoy':  yoy,
        'dyr':  dyr,
        'toi25': toi25,
        'np25':  np25,
    }

# ---- 6. 粗筛 ----
CONGLOMERATE = {
    '600875': '燃气轮机仅为部分业务',
    '601727': '燃气轮机仅为部分业务',
    '601106': '燃气轮机仅为部分业务',
    '002204': '燃气轮机仅为部分业务',
}
FLAG_EXISTING = {
    '002335': '已有公司页（需验证日期）',
    '688676': '已在931994电网设备指数中出现',
}

def screen(code, mc_min=40, roe_min=12, yoy_min=-10):
    r = result[code]
    mc, pe, roe, yoy = r['mc'], r['pe'], r['roe'], r['yoy']
    fails, warns = [], []

    if pe is None or pe <= 0:
        fails.append('PE≤0/亏损')
    if mc is None:
        fails.append('市值N/A')
    elif mc < mc_min:
        fails.append(f'市值{mc:.0f}亿<{mc_min}亿')
    if roe is None:
        fails.append('ROE缺失')
    elif roe < roe_min * 0.8:
        fails.append(f'ROE{roe:.1f}%不达标')
    elif roe < roe_min:
        warns.append(f'ROE{roe:.1f}%⚠️')
    if yoy is None:
        warns.append('营收同比N/A')
    elif yoy < yoy_min * 1.2:
        fails.append(f'营收同比{yoy:.1f}%不达标')
    elif yoy < yoy_min:
        warns.append(f'营收同比{yoy:.1f}%⚠️')

    status = '❌ 排除' if fails else ('⚠️ 边界' if warns else '✅ 通过')
    return status, fails + warns

def fmt(v, d=1):
    return f'{v:.{d}f}' if v is not None else 'N/A'

HDR = f"{'代码':<8}{'公司名':<10}{'市值亿':<8}{'PE':<7}{'ROE%':<7}{'营收同比%':<10}{'结果':<12}备注"
SEP = '-' * 95

def print_table(codes, title):
    print(f'\n{"="*95}')
    print(f'  {title}')
    print(f'{"="*95}')
    print(HDR)
    print(SEP)
    rows = []
    for code in codes:
        r = result[code]
        status, reasons = screen(code)
        notes = []
        if code in CONGLOMERATE: notes.append(CONGLOMERATE[code])
        if code in FLAG_EXISTING: notes.append(FLAG_EXISTING[code])
        if status != '✅ 通过': notes.extend(reasons)
        note = '; '.join(notes)
        rows.append((code, r, status, note))
        print(f"{code:<8}{r['name']:<10}{fmt(r['mc'],0):<8}{fmt(r['pe'],1):<7}"
              f"{fmt(r['roe'],1):<7}{fmt(r['yoy'],1):<10}{status:<12}{note}")
    return rows

gt_rows = print_table(gt_codes, '【燃气轮机】粗筛结果（2025年报 / 2026-04-28估值）')
dc_rows = print_table(dc_codes, '【数据中心供配电】粗筛结果（2025年报 / 2026-04-28估值）')

# 保存结果
with open('_tmp_screen_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('\n已保存至 _tmp_screen_result.json')
