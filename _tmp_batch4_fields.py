#!/usr/bin/env python3
"""探索理杏仁财报字段名"""
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

# 先用fetchDoc获取可用字段
print("=== fetchDoc for fs/non_financial ===")
doc = lx_post("cn/company/fs/non_financial", {
    "fetchDoc": True
})
print(json.dumps(doc, ensure_ascii=False, indent=2)[:3000])
