"""
生成 高ROE + PE低位候选池 Markdown 页面
"""
import json

with open('data/candidate_pool_highroe_lowpe.json', encoding='utf-8') as f:
    d = json.load(f)
companies = d['companies']

# 按行业统计
by_industry = {}
for c in companies:
    ind = c['industry']
    by_industry.setdefault(ind, []).append(c)

lines = []
lines.append('---')
lines.append('tags: [候选池, 高ROE, PE低位, 策略筛选]')
lines.append('生成日期: 2026-05-02')
lines.append('---')
lines.append('')
lines.append('# 高ROE + PE历史低位候选池')
lines.append('')
lines.append('## 策略说明')
lines.append('')
lines.append('| 项目 | 说明 |')
lines.append('|---|---|')
lines.append('| 策略名称 | 高质量 + 历史低估 |')
lines.append('| PE 3年历史分位 | ≤ 20%（处于低位区间）|')
lines.append('| 年报 ROE | ≥ 15%（高质量盈利能力）|')
lines.append('| 基础池 | 全市场候选池 234 家（同花顺初筛）|')
lines.append('| 最终通过 | **46 家** |')
lines.append('| 数据文件 | `data/candidate_pool_highroe_lowpe.json` |')
lines.append('')
lines.append('> 思路：同花顺初筛保证基本面健康（PE合理 + ROE≥3单季 + 营收不大幅下滑），')
lines.append('> 理杏仁 PE 历史分位确认当前估值处于低位，Tushare 年报 ROE 筛出真正高质量公司。')
lines.append('> 特别注意：用**年报 ROE**（非 Q1 单季），避免 Q1 低估陷阱（单季≈年化 1/4）。')
lines.append('')
lines.append('## 完整候选列表（按ROE降序）')
lines.append('')
lines.append('| 公司 | 行业 | PE分位% | PE | PB | ROE% | 市值亿 | WL |')
lines.append('|---|---|---:|---:|---:|---:|---:|:---:|')
for c in companies:
    wl = '✅' if c.get('in_watchlist') else ''
    name = c['name']
    ind = c['industry']
    pct = c['pe_3y_pct']
    pe = c['pe']
    pb = c['pb']
    roe = c['roe_annual']
    mc = c['mc_亿']
    lines.append(f'| {name} | {ind} | {pct:.1f} | {pe:.1f} | {pb:.2f} | {roe:.1f} | {mc:.0f} | {wl} |')

lines.append('')
lines.append('## 按行业分组')
lines.append('')
for ind, comps in sorted(by_industry.items(), key=lambda x: -len(x[1])):
    lines.append(f'### {ind}（{len(comps)}家）')
    lines.append('')
    lines.append('| 公司 | PE分位% | PE | PB | ROE% | 市值亿 | WL |')
    lines.append('|---|---:|---:|---:|---:|---:|:---:|')
    for c in sorted(comps, key=lambda x: -x['roe_annual']):
        wl = '✅' if c.get('in_watchlist') else ''
        name = c['name']
        pct = c['pe_3y_pct']
        pe = c['pe']
        pb = c['pb']
        roe = c['roe_annual']
        mc = c['mc_亿']
        lines.append(f'| {name} | {pct:.1f} | {pe:.1f} | {pb:.2f} | {roe:.1f} | {mc:.0f} | {wl} |')
    lines.append('')

lines.append('## 相关主题')
lines.append('')
lines.append('- [[全市场候选池（沪深A股）]]')

md = '\n'.join(lines)
with open('02-主题/高ROE低PE候选池.md', 'w', encoding='utf-8') as f:
    f.write(md)
print('写入完成')
print(f'行业数: {len(by_industry)}')
for ind, comps in sorted(by_industry.items(), key=lambda x: -len(x[1])):
    wl_count = sum(1 for c in comps if c.get('in_watchlist'))
    print(f'  {ind}: {len(comps)}家（{wl_count}在WL）')
