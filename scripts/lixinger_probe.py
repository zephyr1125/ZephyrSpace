"""
探测 watchlist_index.json 中 34 只指数在理杏仁的接口归属。
优先走 cn/index/fundamental，不行则走 cn/industry/fundamental/sw_2021。
输出：每只指数的接口归属 + 建议的 lixinger stockCode。
"""
import os, json, time, requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("LIXINGER_TOKEN")
BASE = "https://open.lixinger.com/api"

def post(endpoint, body):
    body["token"] = TOKEN
    r = requests.post(f"{BASE}/{endpoint}", json=body, timeout=15)
    return r.json()

# ── 1. 拉取 lixinger 所有合法 index 代码
print("=== 拉取 cn/index 列表 ===")
index_resp = post("cn/index", {})
valid_index_codes = set()
if index_resp.get("code") == 1:
    for item in index_resp["data"]:
        valid_index_codes.add(item["stockCode"])
    print(f"  合法指数代码数：{len(valid_index_codes)}")
else:
    print("  ❌ 获取失败：", index_resp)

time.sleep(0.5)

# ── 2. 拉取 sw_2021 所有行业代码（一级+二级）
print("\n=== 拉取 cn/industry sw_2021 列表 ===")
sw_index = {}  # name → stockCode
for level in ["one", "two"]:
    resp = post("cn/industry", {"source": "sw_2021", "level": level})
    if resp.get("code") == 1:
        for item in resp["data"]:
            sw_index[item["name"]] = item["stockCode"]
        print(f"  level={level}，共 {len(resp['data'])} 条")
    time.sleep(0.3)

print(f"\n  申万2021 行业名称（二级，部分）：")
for name, code in list(sw_index.items())[:20]:
    print(f"    {code}  {name}")

# ── 3. 加载我们的 34 只指数
with open("data/watchlist_index.json", encoding="utf-8") as f:
    wl = json.load(f)

# 去掉 .CSI 后缀，得到纯代码
indices = [(idx["index_code"].split(".")[0], idx["index_code"], idx["name"])
           for idx in wl["indices"]]

# ── 4. 逐只测试能否走 cn/index/fundamental
print("\n=== 探测各指数接口归属 ===")
results = []
for code, full_code, name in indices:
    in_index_list = code in valid_index_codes
    results.append({
        "code": code,
        "full_code": full_code,
        "name": name,
        "in_index_list": in_index_list,
    })
    status = "✅ index" if in_index_list else "❓ 需走industry"
    print(f"  {status}  {code}  {name}")

# ── 5. 输出不在 index 列表里的，需要手动映射
missing = [r for r in results if not r["in_index_list"]]
print(f"\n共 {len(missing)} 只不在 cn/index 列表，需要走 cn/industry/fundamental/sw_2021：")
for r in missing:
    print(f"  {r['code']}  {r['name']}")

# ── 6. 保存结果供后续使用
out = {
    "valid_index_codes": list(valid_index_codes),
    "sw_2021_industry": sw_index,
    "probe_results": results,
}
with open("data/lixinger_probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n✅ 结果已保存到 data/lixinger_probe.json")
