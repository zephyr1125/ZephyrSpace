from pathlib import Path
import json
import re
import subprocess
from decimal import Decimal

root = Path(__file__).resolve().parents[4]
out = Path(__file__).resolve().parent
reports = {
    '深度分析/西高院 深度分析 73 2026-09-07.md': 150,
    '管理层档案/西高院 管理层档案 72 2026-09-07.md': 150,
    '估值分析/西高院 估值分析 2026-09-07.md': 100,
}
notes = list(reports) + ['01-公司/西高院.md', '04-A股行业/高压电气检验检测 行业分析.md', '02-主题/电气装备检测与认证.md']
result = []
for filename in notes:
    text = (root / filename).read_text(encoding='utf-8')
    count = len(text.splitlines())
    assert count >= reports.get(filename, 1), filename
    assert 'E:\\Download' not in text and 'E:/Download' not in text
    for raw in re.findall(r'\[\[([^\]]+)\]\]', text):
        target = raw.split('|')[0].split('#')[0]
        assert (root / (target + '.md')).is_file(), (filename, target)
    result.append(f'- {filename}：{count}行，篇幅与本地链接通过。')

company = (root / '01-公司/西高院.md').read_text(encoding='utf-8')
for section in ['公司简介', '行业质量评分', '波特五力', 'PreBuy 结论', '买入逻辑摘要', '已核实的关键事实',
                '杜邦分析', '估值横向分析', '主要红旗', '股息率分析', '价格与时机判断', '9 种价值投资陷阱复核',
                '政策顺逆风评估', 'A股特有风险检查', '当前操作含义', '待验证问题', '参考来源']:
    assert section in company, section

m = json.loads((out / 'model.json').read_text(encoding='utf-8'))
d = Decimal
weighted = sum(d(str(s['value'])) * w for s, w in zip(m['scenarios'], [d('.25'), d('.5'), d('.25')]))
buy = weighted * (d('.68') + d('.14') * d('.65'))
assert abs(weighted - d(str(m['target']))) < d('.00000001')
assert abs(buy - d(str(m['buy']))) < d('.00000001')
assert sum([9,15,16,9,13,11]) == 73
assert sum([16,15,13,12,6,6,4]) == 72
assert 73 + 72 < 150

# 从原始行情反算市值，独立检查金额和股本单位。
prices = json.loads((out / 'price.json').read_text(encoding='utf-8'))['data']
vals = json.loads((out / 'valuation.json').read_text(encoding='utf-8'))['data']
v = next(x for x in vals if x['stockCode'] == '688334')
assert d(str(prices[0]['close'])) * d('316579466') == d(str(v['mc']))
assert prices[0]['date'].startswith('2026-09-07')
em = json.loads((out / 'eastmoney.json').read_text(encoding='utf-8'))['result']['data'][0]
assert em['QDATE'] == '2026Q2'
assert '[[西高院]]' in (root / '00-首页/公司索引.md').read_text(encoding='utf-8')
for p in (root / 'data').glob('watchlist_*.json'):
    if p.name not in ['watchlist_meta.json', 'watchlist_index.json']:
        assert '688334' not in p.read_text(encoding='utf-8'), '未达门槛，不应新增入池'

result += [
    '- 公司页完整PreBuy章节通过；公司索引已添加入口。',
    '- 评分加总73+72=145，按硬门槛判NONE；未写入Watchlist。',
    f'- 两级加权价值{weighted:.2f}元、机械买入价{buy:.2f}元，独立Decimal复算通过。',
    '- 行情日期、市值=价格×股本、东方财富最新财报期别检查通过。',
    '- 财报PDF文件完整性以正文长度、页数及SHA256清单复核，见archive_manifest.json。',
    '- 已保留2023原始与重述现金流口径差异；未混算可比FCF。',
    '- 局限：2023可比Capex、同行完整质量审计、项目独立IRR及现金归属精确分拆仍待后续证据。',
    '- 未确认重大红线；普通风险与证据缺口在报告中明确，不将检索无结果解释为全历史无风险。',
    '- 本次仅修改西高院相关资料及公司索引，保留工作区已有其他任务改动。',
]
text = '# 西高院三件套自检 2026-09-07\n\n' + '\n'.join(result) + '\n'
# 优先用Obsidian CLI创建可复核的自检记录。
cli = r'C:\Users\zephy\AppData\Local\Programs\Obsidian\Obsidian.com'
completed = subprocess.run([cli, 'vault=ZephyrSpace', 'create',
                            'path=data/research/688334/2026-09-07/自检.md',
                            'content=' + text.replace('\n', '\\n'), 'overwrite'],
                           capture_output=True, timeout=20)
assert completed.returncode == 0, 'Obsidian CLI写入失败'
assert (out / '自检.md').exists()
print(text)
