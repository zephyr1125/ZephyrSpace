#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询正确的API字段名"""

import sys
sys.path.insert(0, r"C:\Users\zephy\.agents\skills\lixinger-query\scripts")

from lixinger_client import fetch_doc
import json

# 查询财报字段名
print("=== 财报字段文档 ===")
try:
    fs_doc = fetch_doc("cn/company/fs/non_financial")
    print("财报可用指标（metricsList）：")
    if "metricsList" in fs_doc:
        for metric in fs_doc["metricsList"][:50]:  # 只显示前50个
            print(f"  - {metric}")
    print(f"... 共 {len(fs_doc.get('metricsList', []))} 个指标")
except Exception as e:
    print(f"获取失败：{e}")

# 查询估值字段名
print("\n=== 估值字段文档 ===")
try:
    val_doc = fetch_doc("cn/company/fundamental/non_financial")
    print("估值可用指标（metricsList）：")
    if "metricsList" in val_doc:
        for metric in val_doc["metricsList"][:30]:  # 只显示前30个
            print(f"  - {metric}")
    print(f"... 共 {len(val_doc.get('metricsList', []))} 个指标")
except Exception as e:
    print(f"获取失败：{e}")
