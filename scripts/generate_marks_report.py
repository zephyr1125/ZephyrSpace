"""
Generate final markdown report from screening results.
"""
import json, os
from collections import Counter

VAULT_DIR = r'E:\ObsidianVaults\ZephyrSpace'
with open(os.path.join(VAULT_DIR, '_temp_results.json'), 'r', encoding='utf-8') as f:
    results = json.load(f)

def esc(s):
    return str(s).replace('|', '\\|')

lines = []
def w(s=''):
    lines.append(s)

# Title
w('# 霍华德·马克思风格 低估错杀股二筛')
w()
w(f'> 筛选日期：2026-06-27 | 候选池：{len(results)} 只 | 数据来源：同花顺 iFinD')
w()
w('---')
w()

# Summary
tc = Counter(r['tier'] for r in results)
w('## 概览')
w()
w(f'| 层级 | 数量 | 占比 |')
w(f'|---|---|---|')
w(f'| S 优先研究 | {tc.get("S",0)} | {tc.get("S",0)/len(results)*100:.0f}% |')
w(f'| A 观察池 | {tc.get("A",0)} | {tc.get("A",0)/len(results)*100:.0f}% |')
w(f'| B 低优先级 | {tc.get("B",0)} | {tc.get("B",0)/len(results)*100:.0f}% |')
w(f'| C 排除 | {tc.get("C",0)} | {tc.get("C",0)/len(results)*100:.0f}% |')
w()

# Note on missing data
w('> ⚠️ **数据说明**：PE 采用 FY2025 静态市盈率（中证发布），与 ROE 同为 FY2025 年报口径；📈=TTM盈利已超FY2025（盈利恢复）；⚠️=PE×ROE与PB偏差>25%，通常因ROE用全口径净利而PE用归母净利（少数股东权益干扰），需人工复核归母口径；🔄=周期性行业。26周基期 2025-12-26。')
w()

# ── TABLE 1: Full Rankings ──
w('---')
w('## 表1：总排名表')
w()
w('| 排名 | 代码 | 名称 | 行业 | 总分 | A估值 | B质量 | C错杀 | D风补 | E可研 | 分类 | 便宜原因 | PE(静) | PB | ROE | 26周 | 标记 |')
w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')

for i, s in enumerate(results):
    tier_icon = {'S': '🔴', 'A': '🟡', 'B': '⚪', 'C': '⚫'}.get(s['tier'], '')
    pe_str = f'{s.get("pe",0):.1f}' if s.get('pe') else '?'
    pb_str = f'{s.get("pb",0):.2f}' if s.get('pb') else '?'
    roe_str = f'{s.get("roe",0):.1f}%' if s.get('roe') else '?'
    chg_str = f'{s.get("chg_26w",0):.1f}%' if s.get('chg_26w') is not None else '?'
    # Build flag string
    flags = []
    if s.get('earnings_recovering'): flags.append('📈')
    if s.get('cyclical'): flags.append('🔄')
    if not s.get('consistency_ok', True): flags.append('⚠️')
    flag_str = ''.join(flags)
    w(f'| {i+1} | {esc(s["code"])} | {esc(s["name"])} | {esc(s.get("industry",""))} | '
      f'{s["total_score"]:.0f} | {s["score_a"]} | {s["score_b"]} | {s["score_c"]} | {s["score_d"]} | {s["score_e"]} | '
      f'{tier_icon}{s["tier"]} | {esc(s.get("cheap_reason",""))} | '
      f'{pe_str} | {pb_str} | {roe_str} | {chg_str} | {flag_str} |')

w()

# ── TABLE 2: S-Tier Deep Dive ──
w('---')
w('## 表2：S类优先研究表')
w()

s_tier = [s for s in results if s['tier'] == 'S']

def fmt(v, suffix=''):
    """Safe number formatter."""
    if v is None or v == '?':
        return '?'
    if isinstance(v, float):
        return f'{v:.1f}{suffix}'
    return f'{v}{suffix}'

for i, s in enumerate(s_tier):
    code = s['code']
    name = s['name']
    pe = s.get('pe')
    pb = s.get('pb')
    roe = s.get('roe')
    nm = s.get('net_margin')
    dr = s.get('debt_ratio')
    rg = s.get('rev_growth')
    chg = s.get('chg_26w')
    mcap = s.get('mcap')
    ind = s.get('industry', '')
    reason = s.get('cheap_reason', '')
    ur = s.get('upside_ratio', '?')
    total = s['total_score']

    w(f'### S{i+1}. {name}（{code}）')
    w()
    w(f'| 维度 | 数据 |')
    w(f'|---|---|')
    w(f'| 行业 | {esc(ind)} |')
    w(f'| 总市值 | {fmt(mcap)} 亿 |')
    w(f'| 动态PE | {fmt(pe)}x |')
    w(f'| PB | {fmt(pb)}x |')
    w(f'| ROE | {fmt(roe, "%")} |')
    w(f'| 净利润率 | {fmt(nm, "%")} |')
    w(f'| 资产负债率 | {fmt(dr, "%")} |')
    w(f'| 营收增长率 | {fmt(rg, "%")} |')
    w(f'| 26周涨跌幅 | {fmt(chg, "%")} |')
    w(f'| 便宜原因 | {esc(reason)} |')
    w(f'| 上行/下行比 | {ur} |')
    w(f'| 总分 | {total:.0f}/100 |')
    w()

    # Three scenarios (heuristic)
    downside = round((chg * 0.5 - 10) if isinstance(chg, (int, float)) else -25, 1)
    neutral = round(abs(chg) * 0.3 + 5 if isinstance(chg, (int, float)) else 15, 1)
    upside = round(abs(chg) * 0.6 + 15 if isinstance(chg, (int, float)) else 35, 1)

    w(f'| 情景 | 预估空间 | 逻辑 |')
    w(f'|---|---|---|')
    w(f'| 🔴 悲观 | {downside:.0f}% | PE继续压缩+利润下滑 |')
    w(f'| 🟡 中性 | +{neutral:.0f}% | 利润持平+PE小幅修复 |')
    w(f'| 🟢 乐观 | +{upside:.0f}% | 利润恢复+PE回归中位 |')
    w()

    # Flags
    con_ok = s.get('consistency_ok', True)
    recovering = s.get('earnings_recovering', False)
    is_cyc = s.get('cyclical', False)
    implied_roe = s.get('implied_roe')

    w(f'**标记**：{"📈盈利恢复 " if recovering else ""}{"🔄周期性 " if is_cyc else ""}{"⚠️PE/ROE口径偏差>40% " if not con_ok else ""}')
    if not con_ok and implied_roe:
        w(f'(隐含ROE {implied_roe:.0f}% vs 报告ROE {roe:.1f}%，需查PB是否含商誉/重估)')
    w()

    # Key risks and next steps
    w(f'**最大风险**：')
    if is_cyc:
        w(f'- 🔄 周期性行业，FY2025 可能偏高景气，大宗商品价格下行将带动利润大幅下滑')
        w(f'- 静态PE基于FY2025高点盈利，景气下行时PE会被动抬升（估值陷阱）')
    if dr and isinstance(dr, (int, float)) and dr > 50:
        w(f'- 资产负债率偏高（{dr:.0f}%），财务杠杆放大周期波动')
    if isinstance(chg, (int, float)) and chg < -25:
        w(f'- 半年跌幅超25%，需确认无未披露利空')
    if not con_ok:
        w(f'- ⚠️ PE/ROE口径偏差，盈利质量需人工复核')
    w(f'- 行业资金流出可能持续，修复时间不确定')
    w()

    w(f'**需验证的问题**：')
    w(f'1. 最近一期财报中现金流是否匹配利润？')
    if is_cyc:
        w(f'2. 🔄 行业周期位置——FY2025盈利是顶部/中部/底部？normalized PE多少？')
    else:
        w(f'2. 行业周期位置——当前是底部、中部还是顶部？')
    w(f'3. 大股东近期是否有减持或质押？')
    w(f'4. 是否有未披露的诉讼、担保或债务风险？')
    w(f'5. 同行业竞争对手的经营状况对比？')
    if not con_ok:
        w(f'6. ⚠️ PB与PE×ROE偏差原因？（商誉？重估？股权融资？）')
    w()

    w(f'**初步仓位建议**：{name}属于{ind}板块，')
    if is_cyc:
        w(f'周期性行业，FY2025静态PE可能低估周期风险，建议单只 0.3%–0.8% 总资产试探，且需确认周期位置后再加仓。')
    elif not con_ok:
        w(f'盈利口径存在偏差，建议先人工复核后再考虑仓位，初步建议 0.5%–1.0% 总资产。')
    else:
        w(f'建议单只 1.0%–2.0% 总资产。')
    w()

# ── TABLE 3: Excluded ──
w('---')
w('## 表3：排除表')
w()
w('| 代码 | 名称 | 排除原因 | 可重新观察 | 触发条件 |')
w('|---|---|---|---|---|')

c_tier = [s for s in results if s['tier'] == 'C']
for s in c_tier:
    reasons = s.get('exclude_reasons', [])
    if not reasons:
        # Low score
        reasons = [f'总分{s["total_score"]:.0f}<48，估值/质量/赔率不满足']
    reason_str = '; '.join(reasons)
    # Determine if re-observable
    if 'ROE' in reason_str or '资产负债率' in reason_str:
        reobs = '是'
        trigger = 'ROE恢复至8%以上'
    elif '26周涨幅>30%' in reason_str:
        reobs = '是'
        trigger = '价格回落至合理区间'
    elif '26周跌幅<-60%' in reason_str:
        reobs = '否'
        trigger = '—'
    else:
        reobs = '是'
        trigger = '价格进一步下跌或基本面明确改善'
    w(f'| {esc(s["code"])} | {esc(s["name"])} | {esc(reason_str)} | {reobs} | {esc(trigger)} |')

w()

# ── TABLE 4: Industry Distribution ──
w('---')
w('## 表4：行业分布表')
w()
w('| 行业 | 候选数 | S类 | A类 | 平均PE | 平均PB | 平均ROE | 平均26周 |')
w('|---|---|---|---|---|---|---|---|')

ind_data = {}
for s in results:
    ind = s.get('industry', '未知')
    if ind not in ind_data:
        ind_data[ind] = {'count': 0, 'S': 0, 'A': 0, 'pes': [], 'pbs': [], 'roes': [], 'chgs': []}
    d = ind_data[ind]
    d['count'] += 1
    if s['tier'] == 'S': d['S'] += 1
    if s['tier'] == 'A': d['A'] += 1
    if s.get('pe'): d['pes'].append(s['pe'])
    if s.get('pb'): d['pbs'].append(s['pb'])
    if s.get('roe'): d['roes'].append(s['roe'])
    if s.get('chg_26w') is not None: d['chgs'].append(s['chg_26w'])

for ind in sorted(ind_data.keys()):
    d = ind_data[ind]
    avg_pe = sum(d['pes'])/len(d['pes']) if d['pes'] else 0
    avg_pb = sum(d['pbs'])/len(d['pbs']) if d['pbs'] else 0
    avg_roe = sum(d['roes'])/len(d['roes']) if d['roes'] else 0
    avg_chg = sum(d['chgs'])/len(d['chgs']) if d['chgs'] else 0
    w(f'| {esc(ind)} | {d["count"]} | {d["S"]} | {d["A"]} | {avg_pe:.1f} | {avg_pb:.2f} | {avg_roe:.1f}% | {avg_chg:.1f}% |')

w()

# ── S-class Research Questions ──
w('---')
w('## S类研究问题模板')
w()
w('对每只 S 类公司，在进入深度研究前必须回答：')
w()
for i in range(1, 11):
    questions = [
        '市场为什么不喜欢它？是行业冷落、周期恐惧还是公司特定问题？',
        '悲观预期是否已经充分反映在当前价格中？',
        '它是真的变差了，还是只是短期被冷落？',
        '未来 1–3 年，如果利润不增长，仅靠估值修复能不能赚钱？',
        '如果利润继续下滑 20%，最大亏损可能是多少？',
        '资产负债表（有息负债/现金流/短期偿债能力）是否足够安全？',
        '现金流（经营现金流/净利润比）是否支持利润质量？',
        '行业有没有永久性衰退风险（如被技术替代、需求永久消失）？',
        '是否适合进入卫星仓而非核心仓？（换手率/流动性/仓位弹性）',
        '如果买入，什么条件下必须卖出？（利润恶化/估值修复完成/行业逻辑破坏）',
    ]
    w(f'{i}. {questions[i-1]}')
w()

# ── Final Notes ──
w('---')
w('## 筛选说明')
w()
w('- **评分框架**：A估值25 + B质量25 + C错杀冷落20 + D风险补偿20 + E可研究性10 = 100分')
w('- **筛选逻辑**：不因便宜而买，重视价格隐含预期，赔率优先于胜率，逆向但不接飞刀')
w('- **最终目标**：找到"市场因短期恐慌/行业冷落/资金偏好给出低价，但公司长期竞争力未同步恶化"的标的')
w('- **本报告不构成投资建议**，仅输出**研究优先级名单**，每只 S 类公司仍需独立深度分析')
w()
w(f'> 生成时间：2026-06-27 | 工具：Howard Marks Second Screen v2 | 数据源：同花顺 iFinD + tushare')

# Write
output_path = os.path.join(VAULT_DIR, '02-主题', '低估错杀二筛', '2026-06-27.md')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'Report written to {output_path}')
print(f'Lines: {len(lines)}')
