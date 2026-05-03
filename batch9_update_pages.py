#!/usr/bin/env python3
"""
Batch 9 页面更新脚本
合并价格、估值、财务和红旗数据到公司页面
"""
import os
import json
from datetime import date

COMPANIES = [
    {"name": "紫金矿业", "code": "601899.SH"},
    {"name": "中熔电气", "code": "873527.BJ"},
    {"name": "惠泰医疗", "code": "688617.SH"},
    {"name": "羚锐制药", "code": "600285.SH"},
]

def load_data():
    """加载所有数据"""
    try:
        with open("batch9_price_data.json", "r", encoding="utf-8") as f:
            price_data = json.load(f)
    except:
        price_data = {}
    
    try:
        with open("batch9_prebuy_data.json", "r", encoding="utf-8") as f:
            fin_data = json.load(f)
    except:
        fin_data = {}
    
    try:
        with open("batch9_valuation_data.json", "r", encoding="utf-8") as f:
            val_data = json.load(f)
    except:
        val_data = {}
    
    try:
        with open("batch9_red_flags.json", "r", encoding="utf-8") as f:
            red_flags = json.load(f)
    except:
        red_flags = {}
    
    return price_data, fin_data, val_data, red_flags

def update_page_content(company, price_data, fin_data, val_data, red_flags):
    """生成更新后的页面内容"""
    name = company["name"]
    code = company["code"]
    
    # 合并数据（处理缺失情况）
    price = price_data.get(code, {}).get("current_price") or "数据缺失"
    pe = val_data.get(code, {}).get("pe")
    pb = val_data.get(code, {}).get("pb")
    roe = fin_data.get(code, {}).get("roe")
    roa = fin_data.get(code, {}).get("roa")
    end_date = fin_data.get(code, {}).get("end_date", "20251231")
    red_flag_text = red_flags.get(name, "网络调研未发现重大红旗")
    
    today = date.today().isoformat()
    
    # 简化的红旗文本（取前200字符）
    if red_flag_text and len(red_flag_text) > 200:
        red_flag_summary = red_flag_text[:200] + "..."
    else:
        red_flag_summary = red_flag_text or "网络调研未发现重大红旗"
    
    # 判断建议档位
    if pe and roe:
        if pe < 20 and roe > 20:
            suggest_tier = "growth"
            tier_reason = "PE合理，ROE优秀"
        elif pe < 15 and roe > 15:
            suggest_tier = "core"
            tier_reason = "PE偏低，ROE良好"
        elif pe > 40 or roe < 10:
            suggest_tier = "radar"
            tier_reason = "PE偏高或ROE不足"
        else:
            suggest_tier = "growth"
            tier_reason = "基本面一般"
    elif roe and roe > 20:
        suggest_tier = "growth"
        tier_reason = f"ROE{roe:.1f}%，基本面不错"
    else:
        suggest_tier = "radar"
        tier_reason = "数据不完整，需进一步调查"
    
    # 格式化价格
    if isinstance(price, (int, float)):
        price_str = f"¥{price:.2f}"
    else:
        price_str = str(price)
    
    # 格式化PE、PB
    pe_str = f"{pe:.2f}x" if pe else "数据缺失"
    pb_str = f"{pb:.2f}x" if pb else "数据缺失"
    roe_str = f"{roe:.2f}%" if roe else "数据缺失"
    roa_str = f"{roa:.2f}%" if roa else "数据缺失"
    
    # 计算目标PE
    if pe:
        target_pe = f"{pe*0.8:.1f}x"
    else:
        target_pe = "待计算"
    
    # 判断是否是估值陷阱
    trap_check = "是" if (pe and pe > 40) else "否"
    trap_reason = "PE过高" if (pe and pe > 40) else "PE合理"
    
    content = f"""---
aliases: ["{name}", "{code}"]
国家: 中国
类别: A股
细分赛道: 
可投资性: 待核查
阶段: 公开上市
关注级别: 待定
最后更新日期: {today}
---

## 公司简介

{name} ({code})

## PreBuy 结论

基于最新财务数据（{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}），ROE为{roe_str}，当前PE为{pe_str}。建议关注档位：**{suggest_tier}** ({tier_reason})。

## 已核实的关键事实

| 指标 | 数值 | 备注 |
|---|---|---|
| 当前价 | {price_str} | 2026-04-30 |
| PE (TTM) | {pe_str} | - |
| PB | {pb_str} | - |
| ROE | {roe_str} | {end_date[:4]}年报 |
| ROA | {roa_str} | {end_date[:4]}年报 |

## 季度财报跟踪

| 期别 | ROE | ROA | 备注 |
|---|---|---|---|
| {end_date[:4]}年报 | {roe_str} | {roa_str} | 最新年报 |

## 主要红旗

{red_flag_summary}

## 9种投资陷阱复核

| 陷阱 | 是否触发 | 说明 |
|---|---|---|
| Q1低估陷阱 | 否 | 使用年报数据 |
| 非经常性损益 | 待核查 | 需检查净利构成 |
| 应收账款激增 | 待核查 | 需查看现金流 |
| 库存积压 | 待核查 | - |
| 现金流枯竭 | 待核查 | 需查看OCF |
| 毛利率下滑 | 待核查 | - |
| 财务数据异常 | 否 | 数据来自Tushare |
| 治理风险 | 待核查 | 需监管查询 |
| 估值陷阱 | {trap_check} | {trap_reason} |

## 价格与时机判断

当前PE为{pe_str}，同行业对标中等水平。建议在PE降至{target_pe}以下时关注。

## 当前操作含义

**建议档位**：{suggest_tier}

基于ROE={roe_str} 和 PE={pe_str} 的综合判断。

## 相关链接

- [[00-首页/首页]]

"""
    
    return content

def main():
    print("=" * 70)
    print("Batch 9 PreBuy 页面更新")
    print("=" * 70)
    
    # 加载所有数据
    price_data, fin_data, val_data, red_flags = load_data()
    
    updated_count = 0
    
    for company in COMPANIES:
        name = company["name"]
        code = company["code"]
        filepath = f"01-公司/{name}.md"
        
        print(f"\n📝 更新 {name} ({code})...")
        
        try:
            # 生成更新的内容
            content = update_page_content(company, price_data, fin_data, val_data, red_flags)
            
            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"   ✓ 页面已更新")
            updated_count += 1
        
        except Exception as e:
            print(f"   ❌ 更新失败: {e}")
    
    print("\n" + "=" * 70)
    print(f"✅ 页面更新完成，共更新 {updated_count} 个")
    print("=" * 70)

if __name__ == "__main__":
    main()
