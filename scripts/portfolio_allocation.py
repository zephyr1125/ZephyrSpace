#!/usr/bin/env python3
import requests, os
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

# 最终持仓公司代码
stocks = {
    "福耀玻璃": ("600660", 92, "A组"),
    "东鹏饮料": ("605499", 87, "A组"),
    "大豪科技": ("603025", 89, "A组"),
    "小商品城": ("600415", 88, "A组"),
    "伊利股份": ("600887", 85, "A组"),
    "悍高集团": ("301022", 81, "B组"),
    "盐津铺子": ("002847", 80, "B组"),
    "羚锐制药": ("600285", 79, "B组"),
}

def last_trading_day(today=None):
    if today is None:
        today = date.today()
    d = today
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()

trade_date = last_trading_day()

# 获取最新价格
print("="*80)
print("【当前价格数据】")
print("="*80)
print(f"数据日期：{trade_date}\n")

prices = {}
for name, (code, score, group) in stocks.items():
    try:
        resp = requests.post("https://open.lixinger.com/api/cn/company/candlestick", json={
            "stockCode": code,
            "startDate": trade_date,
            "endDate": trade_date,
            "type": "lxr_fc_rights",
            "token": LX_TOKEN
        }, timeout=10)
        data = resp.json().get("data", [])
        if data:
            price = data[0]["close"]
            prices[name] = price
            print(f"{name:12} ({code}): {price:8.2f}元 | {group} | 总分{score}")
        else:
            print(f"{name:12} ({code}): 数据获取失败")
    except Exception as e:
        print(f"{name:12} ({code}): 错误 - {str(e)}")

print("\n" + "="*80)
print("【持仓分级】根据最终综合排序表：")
print("="*80)
print("✓ A组（5家，优先配置）：福耀(92), 东鹏(87), 大豪(89), 小商品(88), 伊利(85)")
print("▪ B组（3家，次级配置）：悍高(81), 盐津(80), 羚锐(79)\n")

print("="*80)
print("【建议持仓占比】")
print("="*80)
print("""
A组：目标持仓比 10-15%/家（共50-75%）
  - 福耀玻璃：15%（龙头，排名#1）
  - 东鹏饮料：12%（成长，排名#6，初始仓位较低）
  - 大豪科技：13%（高分位，排名#7）
  - 小商品城：10%（供应链）
  - 伊利股份：10%（乳业龙头）

B组：目标持仓比 5-8%/家（共15-24%）
  - 悍高集团：8%（汽配龙头）
  - 盐津铺子：8%（Q1改善明显）
  - 羚锐制药：8%（季节性确认）

合计目标仓位：约 70-77%（留出20-30%调整空间和现金储备）
""")

print("="*80)
print("【初始建仓比例】根据当前价格与历史价格曲线位置：")
print("="*80)
print("""
根据各公司页面的价格评估：

✓ A组中价格合理/略低：
  - 福耀玻璃（沪主板）：初始 60%（历史低位附近）
  - 大豪科技：初始 70%（PE 7%分位，极低）
  - 小商品城：初始 70%（PE底部）
  - 伊利股份：初始 50%（低位但无特殊驱动）

✗ A组中价格偏强（建议低仓位初始）：
  - 东鹏饮料（605499）：初始 30%（PE 26.1x，已在合理偏强）

▪ B组较好区间（可正常仓位）：
  - 悍高集团：初始 70%
  - 盐津铺子：初始 75%（Q1验证改善，且持仓关键）
  - 羚锐制药：初始 75%（季节性已验证）
""")

print("\n总金额：500,000元\n")
