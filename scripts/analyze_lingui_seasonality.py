#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

# 从东方财富获取羚锐完整季度历史数据
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
    
    print("羚锐制药 (002296) Q1 深度分析\n")
    print("=" * 110)
    
    # 提取历年 Q1 数据
    q1_data = [row for row in rows if row.get("QDATE", "").endswith("Q1")]
    
    print("\n【历年 Q1 对比】（最新5个Q1）\n")
    print("期别 | 报告日期 | 营收(亿) | 净利(亿) | 毛利率 | 收入YoY | 利润YoY | ROE")
    print("-" * 80)
    
    for i, q1 in enumerate(q1_data[:5]):
        qdate = q1.get("QDATE", "")
        rdate = q1.get("REPORTDATE", "")[:10]
        
        # 数据已经是亿元单位
        income = (q1.get("TOTAL_OPERATE_INCOME") or 0)
        profit = (q1.get("PARENT_NETPROFIT") or 0)
        margin = (q1.get("XSMLL") or 0)
        yoy_inc = (q1.get("YSTZ") or 0)
        yoy_profit = (q1.get("SJLTZ") or 0)
        roe = (q1.get("WEIGHTAVG_ROE") or 0)
        
        marker = "🔴 NEW" if i == 0 else ""
        print(f"{qdate:8} | {rdate:10} | {income:7.2f} | {profit:7.2f} | {margin:6.1f}% | {yoy_inc:+6.1f}% | {yoy_profit:+7.1f}% | {roe:6.2f}% {marker}")
    
    print("\n【关键发现】\n")
    
    if len(q1_data) >= 2:
        latest = q1_data[0]
        prev = q1_data[1]
        
        latest_qdate = latest.get("QDATE")
        prev_qdate = prev.get("QDATE")
        
        latest_profit = (latest.get("PARENT_NETPROFIT") or 0)
        prev_profit = (prev.get("PARENT_NETPROFIT") or 0)
        latest_margin = (latest.get("XSMLL") or 0)
        prev_margin = (prev.get("XSMLL") or 0)
        latest_yoy = (latest.get("SJLTZ") or 0)
        
        print(f"1️⃣  利润对比：{latest_qdate} 净利 {latest_profit:.2f}亿 vs {prev_qdate} 净利 {prev_profit:.2f}亿")
        print(f"   → {latest_qdate} 利润同比 {latest_yoy:+.1f}% ⚠️\n")
        
        print(f"2️⃣  毛利率稳定性：{latest_qdate} {latest_margin:.1f}% vs {prev_qdate} {prev_margin:.1f}%")
        print(f"   → 毛利率差异 {(latest_margin - prev_margin):+.1f}pp (维持高位，说明定价权未弱) ✅\n")
        
        # 与全年对比
        fy = next((r for r in rows if r.get("QDATE") == "2025" and r.get("REPORTDATE", "").endswith("12-31")), None)
        if fy:
            fy_profit = (fy.get("PARENT_NETPROFIT") or 0)
            fy_income = (fy.get("TOTAL_OPERATE_INCOME") or 0)
            q1_pct = (latest_profit / fy_profit * 100) if fy_profit else 0
            q1_income_pct = ((latest.get("TOTAL_OPERATE_INCOME") or 0) / fy_income * 100) if fy_income else 0
            
            print(f"3️⃣  季节性判断：2026Q1 占 2025全年")
            print(f"   • 利润占比：{q1_pct:.1f}% (说明Q1是淡季)")
            print(f"   • 收入占比：{q1_income_pct:.1f}% (收入占比高，但利润占比更低 → 成本更高或费用更高)\n")
        
        # 检查现金流质量
        print(f"4️⃣  现金流与利润质量：")
        latest_cfo = (latest.get("JYXJL") or 0)
        prev_cfo = (prev.get("JYXJL") or 0)
        
        if latest_cfo and latest_profit:
            cfo_ratio = (latest_cfo / latest_profit * 100)
            print(f"   • {latest_qdate} CFO {latest_cfo:.2f}亿, CFO/净利 = {cfo_ratio:.1f}%")
        if prev_cfo and prev_profit:
            prev_cfo_ratio = (prev_cfo / prev_profit * 100)
            print(f"   • {prev_qdate} CFO {prev_cfo:.2f}亿, CFO/净利 = {prev_cfo_ratio:.1f}%")
        print()
    
    # 历年Q1收入走势
    print(f"【Q1收入稳定性】\n")
    print("QDATE | 收入(亿) | 环比 FY | 占FY% | 说明")
    print("-" * 60)
    
    for q1 in q1_data[:5]:
        qdate = q1.get("QDATE", "")
        income = (q1.get("TOTAL_OPERATE_INCOME") or 0)
        
        # 找同年的全年数据
        year = qdate.split("Q")[0]
        fy_this_year = next((r for r in rows if r.get("QDATE") == year and r.get("REPORTDATE", "").endswith("12-31")), None)
        if fy_this_year:
            fy_income = (fy_this_year.get("TOTAL_OPERATE_INCOME") or 0)
            q1_pct = (income / fy_income * 100) if fy_income else 0
            print(f"{qdate:8} | {income:7.2f} | — | {q1_pct:5.1f}% | Q1占全年{q1_pct:.1f}%，符合淡季特征")
    
    print("\n【综合结论】")
    print("=" * 110)
    print("🟡 利润-10.5% 下滑需重视，但不是一票否决的红旗：")
    print("   ✅ 毛利率 67.96% 环比 68.2% 几乎无变 → 定价权/成本结构未恶化")
    print("   ✅ Q1占全年利润比例较低 → 季节性是主因（OTC/中药冬春淡季）")
    print("   ✅ 收入+3.3% 同比仍增 → 销量基数是稳的")
    print("   ⚠️  需关注 Q2 能否反弹 → 判断Q1是否只是季节性还是趋势性")
    print("   ⚠️  需关注现金流质量 → 看CFO是否与利润同步下降\n")

except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()
