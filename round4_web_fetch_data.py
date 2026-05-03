#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第四轮筛选 - 护城河强度评估
使用web_fetch从东方财富获取市值、财报数据
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

companies = [
    {"name": "悍高集团", "code": "001221", "market": "0", "ticker": "001221.SZ", "em_code": "0.001221"},
    {"name": "拉卡拉", "code": "300773", "market": "0", "ticker": "300773.SZ", "em_code": "0.300773"},
    {"name": "中熔电气", "code": "301031", "market": "1", "ticker": "301031.SH", "em_code": "1.301031"},
    {"name": "惠泰医疗", "code": "605990", "market": "1", "ticker": "605990.SH", "em_code": "1.605990"},
]

def get_market_data_eastmoney(ticker, code):
    """从东方财富获取市值等基础数据"""
    try:
        # 东方财富实时行情接口
        url = f"https://push2.eastmoney.com/api/qt/stock/get?fltt=2&invt=2&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f84,f85,f86&secid={code}&ut=fa5fd1943c7b386f172d6893dbfba10b&cb=jsonpCallback"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            # 提取 JSON 部分
            text = resp.text
            if "jsonpCallback(" in text:
                json_str = text.split("(", 1)[1].rsplit(")", 1)[0]
                data = json.loads(json_str)
                
                if data.get("data"):
                    data_item = data["data"]
                    # 提取市值（单位：亿元）
                    # f44 = 市价总值
                    price = data_item.get("f43")  # 最新价
                    market_cap = data_item.get("f44") / 100000000 if data_item.get("f44") else None  # 转换为亿元
                    
                    return {
                        "price": price / 100 if price else None,  # 转换回正常价格
                        "market_cap": round(market_cap, 2) if market_cap else None
                    }
    except Exception as e:
        print(f"❌ 东方财富请求失败 ({ticker}): {e}")
    
    return {"price": None, "market_cap": None}

def get_financial_data_eastmoney(code):
    """从东方财富获取财务数据（毛利率等）"""
    try:
        # 东方财富财务数据接口
        # 使用数据中心的财务报告接口
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE%3D%22{code}%22)&pageNumber=1&pageSize=5&sortTypes=1&sortFields=QDATE&pageNumber=1&pageSize=100&p=1&token=894050c76af8967873848547d44b0d1&st=QDATE&sr=-1&quoteType=0"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result", {}).get("data"):
                # 从财务数据中提取毛利率信息
                items = data["result"]["data"]
                
                margins = {}
                for item in items:
                    try:
                        qdate = item.get("QDATE")  # 报告期
                        if qdate:
                            # qdate 格式通常为 "2024-12-31" 或 "2024Q4"
                            year = qdate[:4]
                            
                            # 毛利率通常 = (收入 - 成本) / 收入
                            # 字段名称需要根据实际 API 调整
                            # 这里列举可能的字段
                            if "GROSSPROFIT" in item or "GROSSPROFIT_TTM" in item:
                                gp = item.get("GROSSPROFIT") or item.get("GROSSPROFIT_TTM")
                                if gp is not None:
                                    margins[year] = gp
                            elif "毛利率" in item:
                                margins[year] = item["毛利率"]
                    except Exception as e:
                        pass
                
                return margins if margins else None
    except Exception as e:
        print(f"❌ 东方财富财务查询失败: {e}")
    
    return None

def get_finance_data_ak(code):
    """尝试用akshare获取财务数据"""
    try:
        import akshare as ak
        
        # 获取单个股票的财务指标
        df = ak.stock_financial_analysis_indicator(symbol=code, indicator="按报告期")
        
        if df is not None and len(df) > 0:
            # 提取毛利率
            result = {}
            for idx, row in df.iterrows():
                try:
                    year = str(row.get("报告期", ""))[:4]
                    
                    # 毛利率字段
                    if "毛利率%" in row:
                        result[year] = float(row["毛利率%"])
                    elif "毛利率" in row:
                        result[year] = float(row["毛利率"])
                    elif "毛利润" in row and "营业收入" in row:
                        gp = float(row.get("毛利润", 0))
                        income = float(row.get("营业收入", 1))
                        if income > 0:
                            result[year] = round((gp / income) * 100, 2)
                except Exception as e:
                    pass
            
            return result if result else None
    except Exception as e:
        pass
    
    return None

def main():
    print("\n" + "🌐 使用web_fetch获取财务数据".center(60, "="))
    
    all_data = []
    
    for company in companies:
        print(f"\n【{company['name']}】({company['ticker']})")
        
        # 1. 获取市值
        print(f"  📊 获取市值...")
        market_data = get_market_data_eastmoney(company["ticker"], company["em_code"])
        print(f"     当前价: {market_data['price']}元，市值: {market_data['market_cap']}亿元")
        
        # 2. 获取财务数据
        print(f"  📈 获取财务数据...")
        margins = get_finance_data_ak(company["code"])
        if margins:
            print(f"     毛利率: {margins}")
        else:
            print(f"     ⚠️  毛利率获取失败，尝试其他方式...")
        
        company_data = {
            "name": company["name"],
            "code": company["ticker"],
            "market_cap": market_data["market_cap"],
            "price": market_data["price"],
            "margins": margins,
            "fetch_time": datetime.now().isoformat()
        }
        all_data.append(company_data)
    
    # 保存结果
    with open("round4_web_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存至 round4_web_data.json")

if __name__ == "__main__":
    main()
