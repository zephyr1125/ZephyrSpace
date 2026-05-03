#!/usr/bin/env python3
"""
生成Batch 9 PreBuy 最终汇总表格
"""
import json
from datetime import date

def main():
    # 加载所有数据
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
    
    companies = [
        {"name": "紫金矿业", "code": "601899.SH"},
        {"name": "中熔电气", "code": "873527.BJ"},
        {"name": "惠泰医疗", "code": "688617.SH"},
        {"name": "羚锐制药", "code": "600285.SH"},
    ]
    
    print("\n" + "=" * 100)
    print("Batch 9 PreBuy 分析总结")
    print("=" * 100)
    
    print("\n## Batch 9 PreBuy 分析总结\n")
    print("| 公司 | 代码 | 当前价 | PE | ROE | PB | 建议档位 | 核心结论 |")
    print("|---|---|---|---|---|---|---|---|")
    
    for company in companies:
        name = company["name"]
        code = company["code"]
        
        price = price_data.get(code, {}).get("current_price", "N/A")
        pe = val_data.get(code, {}).get("pe")
        pb = val_data.get(code, {}).get("pb", "N/A")
        roe = fin_data.get(code, {}).get("roe", "N/A")
        
        # 判断建议档位
        if pe and roe:
            if pe < 20 and roe > 20:
                tier = "growth"
                reason = "PE合理，ROE优秀"
            elif pe < 15 and roe > 15:
                tier = "core"
                reason = "PE偏低，ROE良好"
            elif pe > 40 or roe < 10:
                tier = "radar"
                reason = "PE偏高或ROE不足"
            else:
                tier = "growth"
                reason = "基本面一般"
        elif roe and roe > 20:
            tier = "growth"
            reason = f"ROE{roe:.1f}%优秀"
        else:
            tier = "radar"
            reason = "数据不完整"
        
        # 格式化数据
        price_str = f"¥{price:.2f}" if isinstance(price, (int, float)) else str(price)
        pe_str = f"{pe:.2f}x" if pe else "N/A"
        pb_str = f"{pb:.2f}x" if isinstance(pb, (int, float)) else str(pb)
        roe_str = f"{roe:.2f}%" if roe else "N/A"
        
        print(f"| {name} | {code} | {price_str} | {pe_str} | {roe_str} | {pb_str} | **{tier}** | {reason} |")
    
    print("\n" + "=" * 100)
    print("✅ PreBuy 分析完成")
    print("=" * 100)
    
    # 输出建议
    print("\n## 档位定义\n")
    print("- **core**: 长期底仓，基本面优秀（ROE>20%，PE<20x），当前价格合理")
    print("- **growth**: 成长观察，基本面良好（ROE>15%，PE<30x），值得长期持有")
    print("- **radar**: 雷达跟踪，基本面有待验证或估值偏高，需等待入场机会")
    print("\n")

if __name__ == "__main__":
    main()
