#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第四轮筛选 - 护城河强度评估
收集市值、毛利率、竞争优势、负面事件
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

LIXINGER_TOKEN = os.getenv("LIXINGER_TOKEN")
TAVILY_KEY = os.getenv("TAVILY_KEY")
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

LX_BASE = "https://open.lixinger.com/api"

# 第3批公司（需要评估的4家）
companies = [
    {"name": "悍高集团", "code": "001221", "market": "SZ", "ticker": "001221.SZ", "industry": "汽车配件"},
    {"name": "拉卡拉", "code": "300773", "market": "SZ", "ticker": "300773.SZ", "industry": "支付结算"},
    {"name": "中熔电气", "code": "301031", "market": "SH", "ticker": "301031.SH", "industry": "电气设备"},
    {"name": "惠泰医疗", "code": "605990", "market": "SH", "ticker": "605990.SH", "industry": "医疗器械"},
]

def lx_post(path, payload):
    """调用理杏仁API"""
    try:
        resp = requests.post(
            f"{LX_BASE}/{path}",
            json={**payload, "token": LIXINGER_TOKEN},
            timeout=10
        )
        result = resp.json()
        if result.get("code") != "0":
            print(f"❌ 理杏仁API错误 ({path}): {result.get('msg')}")
            return None
        return result.get("data")
    except Exception as e:
        print(f"❌ 理杏仁请求失败 ({path}): {e}")
        return None

def get_market_cap(code):
    """获取当前市值（亿元）"""
    try:
        # 理杏仁 fundamental 接口获取市值
        data = lx_post("cn/company/fundamental/non_financial", {
            "stockCodes": [code],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "metricsList": ["mc"]  # mc = 总市值（亿元）
        })
        if data and len(data) > 0:
            mc = data[0].get("mc")
            return mc
        return None
    except Exception as e:
        print(f"❌ 获取市值失败 ({code}): {e}")
        return None

def get_gross_margin_trend(code):
    """获取近3年毛利率趋势"""
    try:
        # 获取最近3年的毛利率
        # fs/non_financial 返回的数据包含毛利率信息
        dates = [
            f"{datetime.now().year - 1}-12-31",  # 2024年报
            f"{datetime.now().year - 2}-12-31",  # 2023年报
            f"{datetime.now().year - 3}-12-31",  # 2022年报
        ]
        
        margins = {}
        for date_str in dates:
            data = lx_post("cn/company/fs/non_financial", {
                "stockCodes": [code],
                "date": date_str,
                "metricsList": ["a.ps.gp", "a.ps.toi"]  # gp=毛利 toi=收入
            })
            
            if data and len(data) > 0:
                gp = data[0].get("a.ps.gp")  # 毛利
                toi = data[0].get("a.ps.toi")  # 总收入
                if gp is not None and toi is not None and toi > 0:
                    margin = (gp / toi) * 100
                    year = date_str[:4]
                    margins[year] = round(margin, 2)
        
        return margins
    except Exception as e:
        print(f"❌ 获取毛利率失败 ({code}): {e}")
        return {}

def search_red_flags(company_name, ticker):
    """使用Tavily搜索负面事件"""
    try:
        if not TAVILY_KEY:
            print(f"⚠️  Tavily KEY未配置，跳过负面事件搜索")
            return {"has_issues": False, "details": []}
        
        headers = {"Content-Type": "application/json"}
        
        # 搜索处罚、诉讼、管理层变动
        queries = [
            f"{company_name} 处罚 SEC 监管",
            f"{company_name} 诉讼 违规",
            f"{company_name} 管理层 变动 离职",
            f"{company_name} 业绩下滑 风险"
        ]
        
        issues = []
        for query in queries:
            try:
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={"api_key": TAVILY_KEY, "query": query, "max_results": 3},
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("results"):
                        for result in data["results"]:
                            title = result.get("title", "")
                            if any(keyword in title for keyword in ["处罚", "诉讼", "风险", "下滑", "负面"]):
                                issues.append({
                                    "title": title,
                                    "url": result.get("url", ""),
                                    "snippet": result.get("snippet", "")[:200]
                                })
            except Exception as e:
                pass  # 继续下一个查询
        
        return {
            "has_issues": len(issues) > 0,
            "details": issues[:3]  # 只保留前3条
        }
    except Exception as e:
        print(f"⚠️  Tavily搜索失败: {e}")
        return {"has_issues": False, "details": []}

def get_dividend_history(code, ticker):
    """获取分红记录（使用tushare或东方财富）"""
    try:
        # 这里需要根据实际API调整
        # 暂时返回占位符，后续通过web_fetch补充
        return {
            "years_paid": None,
            "trend": "未查证",
            "latest": None
        }
    except Exception as e:
        print(f"⚠️  获取分红历史失败: {e}")
        return {"years_paid": None, "trend": "未查证", "latest": None}

def assess_moat(company):
    """综合评估护城河强度"""
    print(f"\n{'='*60}")
    print(f"正在评估: {company['name']} ({company['ticker']})")
    print('='*60)
    
    result = {
        "company": company["name"],
        "code": company["ticker"],
        "industry": company["industry"],
        "assessment_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # 1. 获取市值
    print(f"📊 获取市值...")
    market_cap = get_market_cap(company["code"])
    result["market_cap"] = market_cap
    result["market_cap_ok"] = market_cap >= 50 if market_cap else False
    print(f"   市值: {market_cap}亿元 {'✓' if result['market_cap_ok'] else '❌'}")
    
    # 2. 获取毛利率趋势
    print(f"📈 获取毛利率趋势...")
    margins = get_gross_margin_trend(company["code"])
    result["margins"] = margins
    
    # 排序年份
    sorted_years = sorted(margins.keys())
    if sorted_years:
        margin_trend = " → ".join([f"{year} {margins[year]}%" for year in sorted_years])
        print(f"   {margin_trend}")
        
        # 判断趋势
        if len(sorted_years) >= 2:
            if margins[sorted_years[-1]] > margins[sorted_years[0]]:
                result["margin_trend"] = "上升"
            elif margins[sorted_years[-1]] < margins[sorted_years[0]]:
                result["margin_trend"] = "下降"
            else:
                result["margin_trend"] = "稳定"
        latest_margin = margins.get(sorted_years[-1]) if sorted_years else None
        result["latest_margin"] = latest_margin
    
    # 3. 搜索负面事件
    print(f"🔍 搜索负面事件...")
    red_flags = search_red_flags(company["name"], company["ticker"])
    result["red_flags"] = red_flags
    
    if red_flags["has_issues"]:
        print(f"   ⚠️  发现 {len(red_flags['details'])} 条潜在负面事件")
        for issue in red_flags["details"]:
            print(f"      - {issue['title'][:60]}")
    else:
        print(f"   ✓ 未发现重大负面事件")
    
    # 4. 获取分红历史
    print(f"💰 查询分红历史...")
    dividends = get_dividend_history(company["code"], company["ticker"])
    result["dividends"] = dividends
    print(f"   (需后续web_fetch补充详细数据)")
    
    return result

def main():
    print("\n" + "🔍 第四轮护城河强度评估 - 数据收集阶段".center(60, "="))
    
    all_results = []
    for company in companies:
        result = assess_moat(company)
        all_results.append(result)
    
    # 保存结果为JSON
    output_file = "round4_data_collected.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据收集完成，已保存至 {output_file}")
    
    # 打印汇总
    print("\n" + "数据收集汇总".center(60, "="))
    for result in all_results:
        print(f"\n【{result['company']}】")
        print(f"  市值: {result['market_cap']}亿元 {'✓' if result['market_cap_ok'] else '❌'}")
        print(f"  毛利率: {result.get('latest_margin')}% ({result.get('margin_trend')})")
        print(f"  负面事件: {'有' if result['red_flags'].get('has_issues') else '无'}")

if __name__ == "__main__":
    main()
