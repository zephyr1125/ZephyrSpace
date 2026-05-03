#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
护城河强度评估脚本 - 第四轮筛选
获取市值、毛利率、财务数据用于护城河分析
"""
import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
LX_TOKEN = os.getenv('LIXINGER_TOKEN')
LX_BASE = 'https://open.lixinger.com/api'

def lx_post(path, payload):
    """调用理杏仁API"""
    try:
        resp = requests.post(
            f'{LX_BASE}/{path}',
            json={**payload, 'token': LX_TOKEN},
            timeout=10
        )
        data = resp.json()
        if data.get('msg') == 'success':
            return data.get('data', {})
        else:
            print(f"  ⚠ API返回：{data.get('msg', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"  ✗ API调用失败：{e}")
        return None

def get_market_cap(stock_codes):
    """获取市值（单位：亿元）"""
    print("\n【第1步】获取市值数据...")
    result = {}
    try:
        resp = lx_post('cn/company/fundamental/non_financial', {
            'stockCodes': stock_codes,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'metricsList': ['mc']  # mc = 总市值（亿元）
        })
        if resp:
            for item in resp:
                code = item.get('stockCode')
                mc = item.get('mc')
                result[code] = mc
                status = '✓' if (mc and mc >= 50) else '✗'
                print(f"  {status} {code}: {mc}亿元" if mc else f"  ✗ {code}: 无数据")
        return result
    except Exception as e:
        print(f"  ✗ 获取市值失败：{e}")
        return {}

def get_gross_margin(stock_codes):
    """获取毛利率（2023/2024/2025年报）"""
    print("\n【第2步】获取毛利率数据...")
    result = {}
    
    # 获取最近三年财报数据
    years = [
        ('2023-12-31', '2023年'),
        ('2024-12-31', '2024年'),
        ('2025-12-31', '2025年')
    ]
    
    for date_str, year_label in years:
        print(f"\n  {year_label}财报数据：")
        try:
            resp = lx_post('cn/company/fs/non_financial', {
                'stockCodes': stock_codes,
                'date': date_str,
                'metricsList': ['a.pr.gross.t']  # 毛利率
            })
            if resp:
                for item in resp:
                    code = item.get('stockCode')
                    gm = item.get('a.pr.gross.t')  # 毛利率（%）
                    
                    if code not in result:
                        result[code] = {}
                    result[code][year_label] = gm
                    
                    if gm is not None:
                        print(f"    {code}: {gm:.2f}%")
                    else:
                        print(f"    {code}: 无数据")
        except Exception as e:
            print(f"  ✗ {year_label}财报查询失败：{e}")
    
    return result

def get_dividends(stock_codes):
    """获取分红数据（近3年）"""
    print("\n【第3步】获取分红政策数据...")
    result = {}
    try:
        # 理杏仁分红接口
        resp = lx_post('cn/company/dividend/dividend', {
            'stockCodes': stock_codes,
        })
        if resp:
            for item in resp:
                code = item.get('stockCode')
                divs = item.get('dividend', [])
                if divs:
                    result[code] = divs[:3]  # 最近3次分红
                    print(f"  {code}: {len(divs)}次分红记录")
        return result
    except Exception as e:
        print(f"  ✗ 分红数据查询失败：{e}")
        return {}

def get_financial_summary(stock_codes):
    """获取财务摘要（ROE、营收、净利等）"""
    print("\n【第4步】获取财务摘要数据...")
    result = {}
    try:
        resp = lx_post('cn/company/fundamental/non_financial', {
            'stockCodes': stock_codes,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'metricsList': ['roe', 'revenue_ttm', 'net_income_ttm', 'roa']
        })
        if resp:
            for item in resp:
                code = item.get('stockCode')
                result[code] = {
                    'roe': item.get('roe'),
                    'revenue_ttm': item.get('revenue_ttm'),
                    'net_income_ttm': item.get('net_income_ttm'),
                    'roa': item.get('roa')
                }
        return result
    except Exception as e:
        print(f"  ✗ 财务摘要查询失败：{e}")
        return {}

if __name__ == '__main__':
    # 4家公司
    companies = {
        '000100': 'TCL智家',
        '300015': '爱尔眼科',
        '688578': '艾力斯',
        '601899': '紫金矿业'
    }
    
    codes = list(companies.keys())
    
    print("="*60)
    print("护城河强度评估 - 数据收集阶段")
    print("="*60)
    
    # 执行数据收集
    market_caps = get_market_cap(codes)
    gross_margins = get_gross_margin(codes)
    dividends = get_dividends(codes)
    financials = get_financial_summary(codes)
    
    # 输出汇总
    print("\n" + "="*60)
    print("数据收集完成 - 生成JSON输出")
    print("="*60)
    
    output = {
        'timestamp': datetime.now().isoformat(),
        'companies': companies,
        'market_caps': market_caps,
        'gross_margins': gross_margins,
        'dividends': dividends,
        'financials': financials
    }
    
    # 保存为JSON
    output_file = os.path.join(os.path.dirname(__file__), '..', 'moat_assessment_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 数据已保存到: {output_file}")
    print(json.dumps(output, ensure_ascii=False, indent=2))
