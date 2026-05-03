#!/usr/bin/env python3
"""
简化版 Batch 9 PreBuy 数据采集
只使用最稳定的Tushare接口
"""
import os
import json
import pandas as pd
import tushare as ts
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

# 目标公司列表
COMPANIES = [
    {"name": "紫金矿业", "code": "601899.SH"},
    {"name": "中熔电气", "code": "873527.BJ"},
    {"name": "惠泰医疗", "code": "688617.SH"},
    {"name": "羚锐制药", "code": "600285.SH"},
]

def last_trading_day():
    """返回最近A股交易日"""
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")

def main():
    pro = ts.pro_api(TUSHARE_TOKEN)
    trade_date = last_trading_day()
    last_year = str(int(date.today().year) - 1)
    year_end = f"{last_year}1231"
    
    print("=" * 70)
    print("Batch 9 PreBuy 数据采集（简化版）")
    print(f"交易日: {trade_date}, 财报期: {year_end}")
    print("=" * 70)
    
    all_data = {}
    
    for company in COMPANIES:
        print(f"\n📊 采集 {company['name']} ({company['code']})...")
        result = {}
        
        try:
            # 1. 当前价格 (daily_basic)
            daily = pro.daily_basic(ts_code=company["code"], trade_date=trade_date)
            if daily is not None and not daily.empty:
                row = daily.iloc[0]
                result["current_price"] = float(row["close"]) if pd.notna(row["close"]) else None
                result["pe_ttm"] = float(row["pe"]) if pd.notna(row["pe"]) and float(row["pe"]) > 0 else None
                result["pb"] = float(row["pb"]) if pd.notna(row["pb"]) and float(row["pb"]) > 0 else None
                result["market_cap"] = float(row["total_mv"]) / 10000 if pd.notna(row["total_mv"]) and float(row["total_mv"]) > 0 else None
                print(f"   ✓ 当前价: ¥{result.get('current_price', '?'):.2f}, PE: {result.get('pe_ttm')}, PB: {result.get('pb')}")
            
            # 2. 财务指标年报数据 (fina_indicator)
            fina_all = pro.fina_indicator(ts_code=company["code"], end_date=year_end, limit=5)
            
            if fina_all is not None and not fina_all.empty:
                # 找年报（end_date 以 1231 结尾）
                annual_data = fina_all[fina_all['end_date'].str.endswith('1231')].head(1)
                
                if not annual_data.empty:
                    frow = annual_data.iloc[0]
                    result["end_date"] = frow["end_date"]
                    result["roe"] = float(frow["roe"]) if pd.notna(frow["roe"]) and float(frow["roe"]) > -9999 else None
                    result["roa"] = float(frow["roa"]) if pd.notna(frow["roa"]) and float(frow["roa"]) > -9999 else None
                    result["gross_margin"] = float(frow["gross_margin"]) if pd.notna(frow["gross_margin"]) and float(frow["gross_margin"]) > -9999 else None
                    print(f"   ✓ ROE: {result.get('roe', '?'):.2f}%, ROA: {result.get('roa', '?')}, 毛利率: {result.get('gross_margin', '?')}")
            
            all_data[company["code"]] = result
            
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            all_data[company["code"]] = {"error": str(e), "current_price": None}
    
    # 保存结果
    output_file = "batch9_prebuy_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print(f"✅ 数据采集完成，已保存到 {output_file}")
    print("=" * 70)
    print("\n数据摘要：")
    for code, data in all_data.items():
        name = [c["name"] for c in COMPANIES if c["code"] == code]
        price = data.get('current_price')
        roe = data.get('roe')
        if price:
            print(f"{name[0] if name else code}: 当前价=¥{price:.2f}, ROE={roe:.2f}%" if roe else f"{name[0] if name else code}: 当前价=¥{price:.2f}, ROE=?")
        else:
            print(f"{name[0] if name else code}: 数据异常")

if __name__ == "__main__":
    main()
