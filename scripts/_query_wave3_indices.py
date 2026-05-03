import requests, json, os, gzip
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('LIXINGER_TOKEN')

def lx_post(path, payload):
    resp = requests.post(
        f'https://open.lixinger.com/api/{path}',
        json={**payload, 'token': TOKEN},
        headers={'Accept-Encoding': 'gzip', 'Content-Type': 'application/json'}
    )
    try:
        data = gzip.decompress(resp.content)
        return json.loads(data)
    except Exception:
        return resp.json()

td = '2026-04-30'

# 候选指数
candidates = {
    '970052': '深证数字安全',
    '970046': '深证XR',
    '970074': '深证智能穿戴',
    '980030': '消费电子',
    '970075': '深证AIGC',
    '980107': 'AI应用软件',
    '980112': 'AI应用',
    '970041': '创新消费',
    'CN5075': '国证信创',
    '980034': '工业软件',
}

print(f"{'代码':<10} {'名称':<12} {'3年分位':>8} {'中位PE':>8} {'P80PE':>8}")
print("-" * 55)
for code, name in candidates.items():
    try:
        r = lx_post('cn/index/fundamental', {
            'stockCode': code,
            'date': td,
            'metricsList': ['pe_ttm.y3.mcw.cvpos', 'pe_ttm.y3.mcw.q5v', 'pe_ttm.y3.mcw.q8v']
        })
        if r.get('data'):
            d = r['data'][0]
            cvpos = d.get('pe_ttm.y3.mcw.cvpos')
            q5v = d.get('pe_ttm.y3.mcw.q5v')
            q8v = d.get('pe_ttm.y3.mcw.q8v')
            cvpos_str = f"{cvpos:.1%}" if cvpos is not None else "N/A"
            q5v_str = f"{q5v:.1f}" if q5v is not None else "N/A"
            q8v_str = f"{q8v:.1f}" if q8v is not None else "N/A"
            print(f"{code:<10} {name:<12} {cvpos_str:>8} {q5v_str:>8} {q8v_str:>8}")
        else:
            msg = r.get('message', 'no data')
            print(f"{code:<10} {name:<12} {'---':>8}  {msg}")
    except Exception as e:
        print(f"{code:<10} {name:<12} error: {e}")
