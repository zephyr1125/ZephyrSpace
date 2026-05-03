#!/usr/bin/env python3
"""
Batch 9 PreBuy 页面生成和Tavily红旗检查
"""
import os
import json
import sys
import subprocess
from datetime import date
from dotenv import load_dotenv

# 导入Tavily搜索模块（若可用）
try:
    from scripts.tavily_search import search_red_flags
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("⚠️ Tavily模块不可用，仅做页面创建")

load_dotenv()

# 公司列表 - 按照用户要求
COMPANIES = [
    {"name": "紫金矿业", "code": "601899.SH", "type": "A股矿业"},
    {"name": "中熔电气", "code": "873527.BJ", "type": "北交所"},
    {"name": "惠泰医疗", "code": "688617.SH", "type": "科创板"},
    {"name": "羚锐制药", "code": "600285.SH", "type": "A股制药"},
]

def load_financial_data():
    """加载采集到的财务数据"""
    try:
        with open("batch9_prebuy_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def create_page_content(company, fin_data):
    """生成Markdown页面内容"""
    code = company["code"]
    name = company["name"]
    company_type = company["type"]
    
    # 获取财务数据
    fin = fin_data.get(code, {})
    roe = fin.get("roe")
    roa = fin.get("roa")
    gross_margin = fin.get("gross_margin")
    end_date = fin.get("end_date", "20251231")
    
    # 构建frontmatter
    today = date.today().isoformat()
    frontmatter = f"""---
aliases: ["{name}", "{code}"]
国家: 中国
类别: {company_type}
细分赛道: 
可投资性: 待核查
阶段: 公开上市
关注级别: 待定
最后更新日期: {today}
---

"""

    # 构建页面内容
    content = f"""## 公司简介

{name} ({code})

{company_type}公司。

## PreBuy 结论

待验证。

## 已核实的关键事实

| 指标 | 数值 |
|---|---|
| ROE | {roe:.2f}% |
| ROA | {roa:.2f}% |
| 报告期 | {end_date[:4]}-{end_date[4:6]}-{end_date[6:]} |

## 季度财报跟踪

| 期别 | ROE | ROA |
|---|---|---|
| {end_date[:4]}年报 | {roe:.2f}% | {roa:.2f}% |

## 主要红旗

网络调研中...

## 9种投资陷阱复核

| 陷阱 | 是否触发 | 说明 |
|---|---|---|
| Q1低估陷阱 | 不适用 | 使用年报数据 |
| 非经常性损益 | 待核查 | - |
| 应收账款激增 | 待核查 | - |
| 库存积压 | 待核查 | - |
| 现金流枯竭 | 待核查 | - |
| 毛利率下滑 | 待核查 | - |
| 财务数据异常 | 待核查 | - |
| 治理风险 | 待核查 | - |
| 估值陷阱 | 待核查 | - |

## 价格与时机判断

待补充当前股价数据。

## 当前操作含义

建议档位：待验证

## 相关公司

[[00-首页/首页]]

"""
    
    return frontmatter + content

def check_page_exists(name):
    """检查公司页面是否存在"""
    path = f"01-公司/{name}.md"
    return os.path.exists(path)

def create_obsidian_page(name, content):
    """使用Obsidian CLI创建页面"""
    try:
        cmd = [
            "obsidian", "create", 
            f"vault=ZephyrSpace", 
            f'path=01-公司/{name}.md',
            f"content={content}"
        ]
        # 由于content太长，改用写文件方式
        filepath = f"01-公司/{name}.md"
        os.makedirs("01-公司", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ 创建页面失败: {e}")
        return False

def search_company_red_flags(name, code):
    """搜索公司红旗"""
    if not TAVILY_AVAILABLE:
        return "网络调研模块不可用"
    
    try:
        print(f"   🔍 搜索 {name} 红旗信息...")
        flags = search_red_flags(name, code)
        if flags:
            return flags
        else:
            return "网络调研未发现重大红旗"
    except Exception as e:
        print(f"   ⚠️  Tavily搜索失败: {e}")
        return "网络调研异常"

def main():
    print("=" * 70)
    print("Batch 9 PreBuy 页面生成")
    print("=" * 70)
    
    fin_data = load_financial_data()
    created_count = 0
    
    for company in COMPANIES:
        name = company["name"]
        code = company["code"]
        
        print(f"\n📄 处理 {name} ({code})...")
        
        # 检查页面是否存在
        if check_page_exists(name):
            print(f"   ℹ️  页面已存在，跳过创建")
            # 可选：更新现有页面（这里暂不实现）
        else:
            print(f"   ✓ 创建新页面...")
            
            # 生成页面内容
            content = create_page_content(company, fin_data)
            
            # 创建页面文件
            filepath = f"01-公司/{name}.md"
            os.makedirs("01-公司", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"   ✓ 页面已创建: {filepath}")
            created_count += 1
        
        # 搜索红旗信息（可选）
        # flags = search_company_red_flags(name, code)
        # print(f"   红旗信息: {flags[:100] if flags else '无'}")
    
    print("\n" + "=" * 70)
    print(f"✅ 处理完成，新建页面 {created_count} 个")
    print("=" * 70)

if __name__ == "__main__":
    main()
