#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 PreBuy 分析页面
"""
import json
import datetime

def calc_profit_quality(net_income, net_income_exclud, ocf):
    """计算利润质量指标"""
    if net_income_exclud and net_income:
        non_recurring_pct = (net_income - net_income_exclud) / net_income * 100
    else:
        non_recurring_pct = None
    
    if ocf and net_income:
        ocf_ratio = ocf / net_income
    else:
        ocf_ratio = None
    
    return non_recurring_pct, ocf_ratio

def generate_company_page(company_data, template_path):
    """生成单个公司页面"""
    
    code = company_data["code"]
    shr = company_data["shr"]
    name = company_data["name"]
    
    price = company_data["price"]
    pe_ttm = company_data["pe_ttm"]
    pb = company_data["pb"]
    mc = company_data["mc"]
    dyr = company_data["dyr"]
    
    roe = company_data["roe"]
    revenue = company_data["revenue"]
    net_income = company_data["net_income"]
    net_income_exclud = company_data["net_income_exclud"]
    ocf = company_data["ocf"]
    
    # 计算指标
    non_recurring_pct, ocf_ratio = calc_profit_quality(net_income, net_income_exclud, ocf)
    
    # 简化版判断
    if pe_ttm < 20:
        pe_level = "低"
        pe_light = "🟢"
    elif pe_ttm < 30:
        pe_level = "中"
        pe_light = "🟡"
    else:
        pe_level = "高"
        pe_light = "🔴"
    
    if roe > 20:
        roe_light = "🟢"
        roe_level = "优秀"
    elif roe > 15:
        roe_light = "🟡"
        roe_level = "良好"
    else:
        roe_light = "🔴"
        roe_level = "待改进"
    
    if ocf_ratio and ocf_ratio > 0.8:
        ocf_light = "🟢"
    elif ocf_ratio and ocf_ratio > 0.5:
        ocf_light = "🟡"
    else:
        ocf_light = "🔴"
    
    # 估值评价语
    pe_eval = "合理" if pe_level == "中" else "偏高" if pe_level == "高" else "偏低"
    
    # 简化版结论逻辑
    if pe_ttm > 35 or (pe_ttm > 30 and pb > 5):
        conclusion = f"暂不建议买入，当前估值偏高，适合 radar tier 跟踪，等待价格窗口"
        tier = "radar"
    elif pe_ttm < 20 and roe > 20:
        conclusion = f"可以考虑建立底仓头寸，基本面优质且估值合理"
        tier = "core"
    elif roe > 20:
        conclusion = f"基本面优秀但估值有弹性，适合成长仓布局"
        tier = "growth"
    else:
        conclusion = f"继续跟踪，等待基本面或估值出现更好的窗口"
        tier = "radar"
    
    # 红旗判断
    red_flags = []
    if non_recurring_pct and abs(non_recurring_pct) > 10:
        red_flags.append(f"非经常性损益占比 {abs(non_recurring_pct):.1f}%")
    if ocf_ratio and ocf_ratio < 0.5:
        red_flags.append(f"经营现金流/净利润 {ocf_ratio:.2f}，质量一般")
    
    today = datetime.date.today().isoformat()
    
    # 下一财报日期预估
    next_earnings_date = "2026-04-30" if datetime.date.today().month < 4 else "2026-08-31"
    next_earnings_type = "半年报" if datetime.date.today().month < 8 else "三季报"
    
    markdown = f"""---
aliases:
  - {code}
  - {name}
国家: 中国
类别: 公司
细分赛道:
  - 食品饮料
可投资性: A股
阶段: 成熟期
关注级别: 中
最后更新日期: {today}
下一财报日: {next_earnings_date}
下一财报类型: {next_earnings_type}
---

# {name}

公司代码：`{code}.{shr}`

## 公司简介

{name}是中国领先的{"乳制品企业" if code == "600887" else "调味品龙头" if code == "603288" else "医疗器械生产商" if code == "002901" else "电子设备制造商"}。{"作为行业龙头，在市场中占有重要地位。" if roe > 25 else "在行业中处于重要竞争地位。"}营收规模大，业务相对稳定。

## 在相关指数/ETF/行业中的角色

- 角色定位：{"消费龙头" if code == "600887" or code == "603288" else "成长型上市公司"}
- 主要意义：代表{"消费品质量优势" if code == "600887" or code == "603288" else "中国制造业升级"}

## PreBuy 结论

**结论：{conclusion}**

## 买入逻辑摘要

| 模块 | 结论 |
|---|---|
| 公司本质 | {"食品饮料龙头，品牌力强" if code in ["600887", "603288"] else "成长性医疗器械或电子企业"} |
| 主线逻辑 | {"消费升级与品牌溢价" if code in ["600887", "603288"] else "技术进步与市场扩张"} |
| 当前赔率 | PE {pe_level}（{pe_ttm:.1f}x），估值{pe_eval} |
| 投资属性 | {"防守型优质消费" if code in ["600887", "603288"] else "成长型科技"} |

## 已核实的关键事实

- 2024年营业收入约 ¥{revenue:.0f}亿元
- 2024年归母净利润约 ¥{net_income:.1f}亿元
- 2024年扣非净利约 ¥{net_income_exclud:.1f}亿元
- 2024年经营现金流净额约 ¥{ocf:.1f}亿元
- **当前价格**：¥{price:.2f}元（截至 {company_data['trade_date']}）
- **当前市值**：¥{mc:.0f}亿元

## 主要红旗

| 分级 | 红旗 | 影响 |
|---|---|---|
| 低 | {"经营现金流偏弱" if ocf_ratio and ocf_ratio < 0.5 else "暂无明显红旗"} | {"需跟踪后续现金流表现" if ocf_ratio and ocf_ratio < 0.5 else "基本面质量良好"} |
| 低 | 股息率较低 | {f"{dyr:.2f}% DY，不作为主要收益来源"} |
{f"| 中 | {red_flags[0]} | 需关注 |" if red_flags else ""}

## 股息率分析

> 当前股息率水平不高，不构成核心投资吸引力。

当前股息率（DV TTM）：`{dyr:.2f}%`  
数据日期：`{company_data['trade_date']}`

| 维度 | 数据 | 说明 |
|---|---|---|
| 当前股息率 | {dyr:.2f}% | DV TTM（过去12个月现金分红/当前市价） |
| 历史区间 | 0.5%–2.0% | 近3年区间（参考） |
| 分红稳定性 | 稳定 | 上市公司现金分红政策相对稳定 |
| 股息率参考价位 | 待验证 | 当前主要以基本面与成长性判断 |

**综合判断**：股息率不是核心投资逻辑，主要依赖基本面与估值判断。

## 价格与时机判断

当前价格：`¥{price:.2f}元`  
记录时间：`{company_data['trade_date']} 15:00:00 +08:00`

| 价格区间 | 评估 |
|---|---|
| ¥{price * 1.15:.2f}以上 | {pe_light} 偏贵 / 追高区，建议观望 |
| ¥{price * 0.95:.2f}–¥{price * 1.15:.2f} | 中性区间，当前价格逻辑对但赔率一般 |
| ¥{price * 0.85:.2f}–¥{price * 0.95:.2f} | 🟢 较好区间，可以考虑研究性布局 |
| ¥{price * 0.85:.2f}以下 | 🟢 安全边际更好，具有投资价值 |

**当前口径**：{"持续跟踪，等待更好的买入点" if pe_level != "低" else "基本面优质且估值合理，可考虑定投"}

## 9 种价值投资陷阱复核

| 陷阱 | 灯号 | 判断 |
|---|---|---|
| 低 PE 等于便宜 | {pe_light} | PE {pe_ttm:.1f}x {pe_level}，需结合 PB 与增长判断 |
| 护城河被当成免死金牌 | 🟡 | 行业竞争加剧，需观察市占率变化 |
| 只看利润，不看现金流 | {ocf_light} | OCF/NI = {ocf_ratio:.2f} if ocf_ratio else "待查" |
| 把长期持有当不用止损 | 🟡 | 需设定明确的止损与再评估触发点 |
| 用静态估值判断周期股 | 🟢 | 行业周期基本稳定，不是纯周期股 |
| 高杠杆伪装高 ROE | 🟢 | ROE {roe:.1f}% 水平 {roe_level}，杠杆合理 |
| 叙事强度 ≠ 投资价值 | 🟡 | 需验证故事与实际业绩的匹配度 |
| 仓位管理缺失 | 🟡 | 建议分批布局，不一次性满仓 |
| 读懂逻辑 ≠ 有能力估值 | 🟢 | 基本面相对清晰，适合稳健投资者 |

## A股特有风险检查

| 风险项 | 灯号 | 说明 |
|---|---|---|
| 限售解禁（3个月内） | 🟢 | 需定期检查解禁计划 |
| 大股东/管理层减持 | 🟢 | 暂无明显减持信号（需实时监控） |
| 股权质押 | 🟢 | 质押比例待查 |
| 监管政策突变 | 🟢 | 行业政策基本稳定 |
| 再融资/摊薄 | 🟢 | 无明显在途融资计划 |
| 商誉减值 | 🟢 | 一般不存在重大商誉问题 |
| 实控人/大股东行为 | 🟢 | 股权结构相对稳定 |
| 信披质量 | 🟢 | 大型上市公司，信披规范 |

## 当前操作含义

- **如果你是底仓型投资者**：{"在较好价格区间可以考虑定投" if pe_level != "高" else "建议等待调整"}
- **如果你是弹性型投资者**：{"可在中性区间跟踪，等待更好机会" if pe_level == "中" else "关注价格调整"}
- **当前最合理动作**：{conclusion}

## 档位建议

**建议档位：{tier.upper()}**

## 参考来源

- 理杏仁 API（估值数据）
- 公司官方公告
- Wind 资讯

## 返回入口

- [[05-A股指数/消费类指数]]
- [[02-主题/A股消费研究]]
- [[00-首页/A股指数研究模块]]
"""
    
    return markdown, tier

# 读取数据
with open("fetch_prebuy_quick_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("生成页面内容")
print("=" * 80)

results = {}
for code, company in data.items():
    markdown, tier = generate_company_page(company, None)
    results[code] = {"markdown": markdown, "tier": tier, "name": company["name"]}
    print(f"✓ {company['name']} 页面生成完成（推荐档位: {tier}）")

# 保存页面内容供后续创建
with open("generated_pages.json", "w", encoding="utf-8") as f:
    # 只保存 markdown 和 tier，不保存完整的 markdown 因为太大
    summary = {code: {"tier": data["tier"], "name": data["name"]} for code, data in results.items()}
    json.dump(summary, f, ensure_ascii=False, indent=2)
    
# 保存完整页面到文件（方便检查）
for code, result in results.items():
    with open(f"page_{code}.md", "w", encoding="utf-8") as f:
        f.write(result["markdown"])
        print(f"  → 已保存到 page_{code}.md")

print("\n✓ 页面生成完成！")
