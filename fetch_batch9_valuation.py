#!/usr/bin/env python3
"""
获取PE/PB并运行Tavily红旗搜索
"""
import os
import json
import tushare as ts
from datetime import date
from dotenv import load_dotenv

load_dotenv()
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

COMPANIES = [
    {"name": "紫金矿业", "code": "601899.SH"},
    {"name": "中熔电气", "code": "873527.BJ"},
    {"name": "惠泰医疗", "code": "688617.SH"},
    {"name": "羚锐制药", "code": "600285.SH"},
]

def main():
    pro = ts.pro_api(TUSHARE_TOKEN)
    
    # 加载已有数据
    with open("batch9_price_data.json", "r", encoding="utf-8") as f:
        price_data = json.load(f)
    
    with open("batch9_prebuy_data.json", "r", encoding="utf-8") as f:
        fin_data = json.load(f)
    
    # 获取PE/PB
    valuation_data = {}
    
    for company in COMPANIES:
        code = company["code"]
        name = company["name"]
        
        print(f"\n📊 获取 {name} 的PE/PB...")
        
        try:
            # 从daily_basic获取最新PE/PB
            basic = pro.daily_basic(ts_code=code, trade_date="20260430")
            
            if basic is not None and not basic.empty:
                row = basic.iloc[0]
                
                pe = float(row["pe"]) if row["pe"] > 0 else None
                pb = float(row["pb"]) if row["pb"] > 0 else None
                
                valuation_data[code] = {
                    "pe": pe,
                    "pb": pb,
                    "price": price_data.get(code, {}).get("current_price"),
                    "roe": fin_data.get(code, {}).get("roe"),
                    "roa": fin_data.get(code, {}).get("roa"),
                }
                
                print(f"   ✓ PE: {pe}, PB: {pb}")
            
        except Exception as e:
            print(f"   ⚠️  {e}")
            valuation_data[code] = {"error": str(e)}
    
    # 保存
    with open("batch9_valuation_data.json", "w", encoding="utf-8") as f:
        json.dump(valuation_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print("✅ 估值数据采集完成")
    print("=" * 70)
    
    # 现在运行Tavily搜索（若可用）
    try:
        from scripts.tavily_search import search_red_flags
        print("\n🔍 运行Tavily红旗搜索...")
        
        red_flags_data = {}
        
        for company in COMPANIES:
            name = company["name"]
            code = company["code"]
            
            print(f"\n   搜索 {name} 的红旗...")
            try:
                flags = search_red_flags(name, code)
                red_flags_data[name] = flags if flags else "网络调研未发现重大红旗"
                print(f"   ✓ 完成")
            except Exception as e:
                print(f"   ⚠️  Tavily搜索失败: {e}")
                red_flags_data[name] = f"搜索异常: {e}"
        
        with open("batch9_red_flags.json", "w", encoding="utf-8") as f:
            json.dump(red_flags_data, f, indent=2, ensure_ascii=False)
        
        print("\n✅ 红旗搜索完成")
        
    except ImportError:
        print("⚠️  Tavily模块不可用")

if __name__ == "__main__":
    main()
