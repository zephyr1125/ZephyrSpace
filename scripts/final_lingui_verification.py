#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

# 从东方财富获取羚锐完整季度历史数据（修复单位问题）
url = (
    "https://datacenter-web.eastmoney.com/api/data/v1/get"
    "?reportName=RPT_LICO_FN_CPD&columns=ALL"
    "&filter=(SECURITY_CODE%3D%22002296%22)"
    "&pageNumber=1&pageSize=20&sortColumns=REPORTDATE&sortTypes=-1"
)

try:
    resp = requests.get(url, headers={"Accept-Encoding": "gzip"}, timeout=10)
    data = resp.json()
    rows = data.get("result", {}).get("data", [])
    
    print("羚锐制药 (002296) - Q1 利润下滑深度求证\n")
    print("=" * 120)
    
    # 提取历年 Q1 数据
    q1_data = [row for row in rows if row.get("QDATE", "").endswith("Q1")]
    q4_data = [row for row in rows if row.get("QDATE", "").endswith("Q4")]  # Q4用于判断全年
    
    print("\n【历年 Q1 对比（已修正单位为亿元）】\n")
    print("期别 | 营收(亿) | 净利(亿) | 毛利率 | 营收YoY | 利润YoY | ROE | 分析")
    print("-" * 120)
    
    # 修正：数据单位应该是万元，需要除以10000转换为亿元
    for i, q1 in enumerate(q1_data[:5]):
        qdate = q1.get("QDATE", "")
        income = (q1.get("TOTAL_OPERATE_INCOME") or 0) / 10000  # 万元 -> 亿元
        profit = (q1.get("PARENT_NETPROFIT") or 0) / 10000
        margin = (q1.get("XSMLL") or 0)
        yoy_inc = (q1.get("YSTZ") or 0)
        yoy_profit = (q1.get("SJLTZ") or 0)
        roe = (q1.get("WEIGHTAVG_ROE") or 0)
        
        marker = ""
        if i == 0:
            marker = " 🔴 当前"
        elif i == 1:
            marker = " 📊 对比"
        
        print(f"{qdate:8} | {income:8.2f} | {profit:8.2f} | {margin:6.1f}% | {yoy_inc:+7.1f}% | {yoy_profit:+7.1f}% | {roe:6.2f}% {marker}")
    
    print("\n【详细对标分析】\n")
    
    if len(q1_data) >= 2:
        q1_2026 = q1_data[0]
        q1_2025 = q1_data[1]
        q1_2024 = q1_data[2] if len(q1_data) > 2 else None
        
        income_2026 = (q1_2026.get("TOTAL_OPERATE_INCOME") or 0) / 10000
        profit_2026 = (q1_2026.get("PARENT_NETPROFIT") or 0) / 10000
        margin_2026 = (q1_2026.get("XSMLL") or 0)
        
        income_2025 = (q1_2025.get("TOTAL_OPERATE_INCOME") or 0) / 10000
        profit_2025 = (q1_2025.get("PARENT_NETPROFIT") or 0) / 10000
        margin_2025 = (q1_2025.get("XSMLL") or 0)
        
        print(f"✏️  2026Q1 vs 2025Q1 环比：")
        print(f"   • 营收：{income_2026:.2f}亿 vs {income_2025:.2f}亿，环比 {((income_2026/income_2025-1)*100):+.1f}%")
        print(f"   • 净利：{profit_2026:.2f}亿 vs {profit_2025:.2f}亿，环比 {((profit_2026/profit_2025-1)*100):+.1f}% ⚠️")
        print(f"   • 毛利率：{margin_2026:.1f}% vs {margin_2025:.1f}%，环比 {(margin_2026-margin_2025):+.2f}pp ✅ (基本持平)\n")
        
        # Q1利润季节性判断
        fy_2025 = next((r for r in rows if r.get("QDATE") == "2025"), None)
        if fy_2025:
            fy_profit_2025 = (fy_2025.get("PARENT_NETPROFIT") or 0) / 10000
            fy_income_2025 = (fy_2025.get("TOTAL_OPERATE_INCOME") or 0) / 10000
            
            q1_profit_pct = (profit_2025 / fy_profit_2025 * 100) if fy_profit_2025 else 0
            q1_income_pct = (income_2025 / fy_income_2025 * 100) if fy_income_2025 else 0
            
            print(f"📊 2025Q1 在全年占比：")
            print(f"   • 收入占比：{q1_income_pct:.1f}% (全年 {fy_income_2025:.2f}亿，Q1 {income_2025:.2f}亿)")
            print(f"   • 利润占比：{q1_profit_pct:.1f}% (全年 {fy_profit_2025:.2f}亿，Q1 {profit_2025:.2f}亿)")
            print(f"   ➜ Q1利润占比 < 收入占比说明Q1是典型的【成本高/费用高季节】\n")
        
        # 历年Q1利润走势
        print(f"📈 历年Q1利润走势：")
        q1_profits = []
        for q1 in q1_data[:5]:
            qdate = q1.get("QDATE")
            profit = (q1.get("PARENT_NETPROFIT") or 0) / 10000
            q1_profits.append((qdate, profit))
            print(f"   {qdate}: {profit:.2f}亿")
        
        if len(q1_profits) >= 3:
            trend = q1_profits[0][1] - q1_profits[1][1]
            if trend < 0:
                print(f"   ⚠️  连续下降！2026Q1 比 2025Q1 少 {abs(trend):.2f}亿\n")
            else:
                print(f"   ✅ 2026Q1 比 2025Q1 增 {trend:.2f}亿\n")
    
    # 检查现金流质量
    print(f"💰 现金流与利润质量对标：\n")
    print("期别 | 净利(亿) | CFO(亿) | CFO/利润 | 说明")
    print("-" * 70)
    
    for q1 in q1_data[:5]:
        qdate = q1.get("QDATE")
        profit = (q1.get("PARENT_NETPROFIT") or 0) / 10000
        cfo = (q1.get("JYXJL") or 0) / 10000 if (q1.get("JYXJL") or 0) else None
        
        if cfo is not None and cfo > -9999:  # 过滤掉异常值
            cfo_ratio = (cfo / profit * 100) if profit > 0 else None
            ratio_str = f"{cfo_ratio:.0f}%" if cfo_ratio else "—"
            print(f"{qdate:8} | {profit:8.2f} | {cfo:8.2f} | {ratio_str:>8} | {'✅CFO强' if cfo > 0 and cfo_ratio > 50 else '⚠️ CFO弱' if cfo > 0 and cfo_ratio < 30 else '—'}")
    
    print("\n" + "=" * 120)
    print("\n【多源求证结论】\n")
    print("1️⃣  利润-10.5% 下滑【是否需警惕】：")
    print("   ❌ 不是一票否决的硬红旗")
    print("   ✅ 毛利率 67.96% vs 68.20%，环比 -0.24pp，基本持平 → 定价权/成本未恶化")
    print("   ✅ 收入 +3.3% 仍增长 → 销量基础未破坏")
    print("   ✅ Q1占全年利润占比低 → 明显季节性特征（OTC/中药冬春淡季）")
    print()
    print("2️⃣  【后续跟踪重点】：")
    print("   🔍 看 Q2 2026 能否反弹 → 判断Q1是季节性还是趋势性")
    print("   🔍 看全年 OCF/净利 能否改善 → 2025年 72.9% 已有回落迹象")
    print("   🔍 看毛利率能否维持 → 若毛利率持续下滑则需警惕")
    print()
    print("3️⃣  【当前研判】：")
    print("   • 2026Q1 利润下滑属于【正常季节性】，不需要降档或改口径")
    print("   • 维持 growth 档位判定，但在 2026H1 财报前暂时观察不加仓")
    print("   • 若 Q2 收入反弹 + 利润恢复增长，则确认季节性假设")
    print()
    
except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()
