#!/usr/bin/env python3
"""批次4数据修正：修复股价/财报字段"""
import requests, os, json, gzip
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    resp = requests.post(f"{LX_BASE}/{path}",
                         json={**payload, "token": LX_TOKEN},
                         headers={"Accept-Encoding": "gzip"}, timeout=30)
    try:
        return json.loads(gzip.decompress(resp.content))
    except:
        return resp.json()

companies = {
    "中国移动": "600941",
    "中国神华": "601088",
    "长江电力": "600900",
    "中国石油": "601857",
}
codes = list(companies.values())

# 1. 尝试不同日期的股价
print("=== 股价 (2026-05-09 ~ 2026-05-15) ===")
for name, code in companies.items():
    pr = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": "2026-05-08",
        "endDate": "2026-05-15",
        "adjustmentType": "0"
    })
    data = pr.get("data", [])
    if data:
        latest = data[-1]
        print(f"{name}({code}): 收盘={latest.get('c')}, 日期={str(latest.get('t',''))[:10]}")
    else:
        print(f"{name}({code}): 无数据, 错误={pr.get('message','')}")

# 2. 先探索财报接口可用字段
print("\n=== 探索财报字段（中国移动2024年报）===")
probe = lx_post("cn/company/fs/non_financial", {
    "stockCodes": ["600941"],
    "date": "2024-12-31",
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t", "a.pr.np.t.yoy",
                    "a.cfs.ocf.t", "a.bs.ae.t", "a.bs.ta.t"]
})
print(json.dumps(probe, ensure_ascii=False, indent=2))

# 3. 尝试Q1数据
print("\n=== Q1 2026 财报 ===")
q1 = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": "2026-03-31",
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.toi.t.yoy", "a.pr.np.t", "a.pr.np.t.yoy"]
})
print(json.dumps(q1.get("data", []), ensure_ascii=False, indent=2))
