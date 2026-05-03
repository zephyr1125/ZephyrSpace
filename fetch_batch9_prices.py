#!/usr/bin/env python3
"""
获取当前股价数据
"""
import os
import json
import tushare as ts
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

COMPANIES = [
    {"name": "紫金矿业", "code": "601899.SH"},
    {"name": "中熔电气", "code": "873527.BJ"},
    {"name": "惠泰医疗", "code": "688617.SH"},
    {"name": "羚锐制药", "code": "600285.SH"},
]

def get_last_trading_date_range():
    """获取最近若干个交易日期范围"""
    today = date.today()
    dates = []
    for i in range(1, 10):  # 查询最近9天
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # 工作日
            dates.append(d.strftime("%Y%m%d"))
    return dates

def main():
    pro = ts.pro_api(TUSHARE_TOKEN)
    
    # 查询最近几个交易日的数据
    recent_dates = get_last_trading_date_range()
    print(f"最近交易日: {recent_dates[:3]}")
    
    price_data = {}
    
    for company in COMPANIES:
        code = company["code"]
        name = company["name"]
        
        print(f"\n查询 {name} ({code})...")
        
        try:
            # 查询最近5天的daily数据
            daily_df = pro.daily(ts_code=code, start_date="20260420", end_date="20260501")
            
            if daily_df is not None and not daily_df.empty:
                # 取最新的交易日
                latest = daily_df.iloc[0]
                
                price_data[code] = {
                    "current_price": float(latest["close"]),
                    "trade_date": latest["trade_date"],
                    "open": float(latest["open"]),
                    "high": float(latest["high"]),
                    "low": float(latest["low"]),
                    "vol": float(latest["vol"]),
                    "amount": float(latest["amount"])
                }
                
                print(f"   ✓ 当前价: ¥{price_data[code]['current_price']:.2f} ({latest['trade_date']})")
            else:
                print(f"   ❌ 无数据")
        
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    # 保存价格数据
    with open("batch9_price_data.json", "w", encoding="utf-8") as f:
        json.dump(price_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print("✅ 价格数据采集完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
