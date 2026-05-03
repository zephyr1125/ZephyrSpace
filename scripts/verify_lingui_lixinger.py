#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import os
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

# 用理杏仁获取羚锐的季度财务数据
url = "https://open.lixinger.com/api/cn/company/fs/non_financial"

# 分两个时间点查询：年报期和Q1期
payloads = [
    {"stockCodes": ["002296"], "startDate": "2024-01-01", "endDate": "2026-05-03", "metricsList": ["a.ps.toi.t", "a.pr.np.p"]},
]

try:
    resp = requests.post(url, json={**payloads[0], "token": LX_TOKEN})
    data = resp.json()
    
    rows = data.get("data", [])
    print(f"共获取 {len(rows)} 条数据\n")
    
    if rows:
        # 按日期排序
        rows = sorted(rows, key=lambda x: x.get("date", ""), reverse=True)
        
        print("日期 | 营业收入 | 归母净利 | 收入同比 | 利润同比 | 说明")
        print("-" * 80)
        
        for row in rows[:16]:  # 前16条
            date = row.get("date", "—")
            toi = row.get("a.ps.toi.t", None)  # 营业总收入
            np = row.get("a.pr.np.p", None)  # 归母净利
            
            toi_str = f"{toi/1e8:.2f}亿" if toi else "—"
            np_str = f"{np/1e8:.2f}亿" if np else "—"
            
            print(f"{date:12} | {toi_str:>8} | {np_str:>8} | — | — | —")
    else:
        print("❌ 无数据返回")
        print("响应:", data)
        
except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()
