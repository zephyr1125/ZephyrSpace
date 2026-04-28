"""更新 stock_watchlist.json - 931897绿电指数PreBuy后的变更"""
import json

WL_PATH = r"E:\ObsidianVaults\ZephyrSpace\data\stock_watchlist.json"

with open(WL_PATH, encoding="utf-8") as f:
    wl = json.load(f)

def find_entry(tier, code):
    for i, c in enumerate(wl["watchlists"][tier]):
        if c.get("code") == code:
            return i, c
    return -1, None

# ===== 1. 更新现有条目价格/DY/next_earnings =====
updates = [
    # (tier, code, fields_to_update)
    ("core", "600900.SH", {"last_close": 26.66, "dv_ttm": 3.54, "next_earnings_date": "2026-04-30"}),
    ("core", "600886.SH", {"last_close": 13.40, "dv_ttm": 3.41, "next_earnings_date": "2026-04-30", "prebuy_conclusion": "逻辑清晰，13.40元处于较好区间，赔率改善，可分批建仓"}),
    ("growth", "600098.SH", {"last_close": 7.14, "dv_ttm": 5.18, "next_earnings_date": "2026-04-30"}),
    ("radar", "600795.SH", {"last_close": 4.89, "dv_ttm": 4.29, "next_earnings_date": "2026-04-29"}),
    ("radar", "600027.SH", {"last_close": 4.91, "dv_ttm": 4.29, "next_earnings_date": "2026-04-29"}),
    ("radar", "600642.SH", {"last_close": 8.95, "dv_ttm": 5.03, "next_earnings_date": "2026-08-31（估算）", "next_earnings_type": "半年报",
                             "prebuy_conclusion": "Q1净利-22%压力，OCF稳健，8.95元已在理想价（DY5.03%），小仓位试探，等H1验证"}),
]

for tier, code, fields in updates:
    idx, entry = find_entry(tier, code)
    if idx >= 0:
        entry.update(fields)
        print(f"  更新 {tier}/{code}: {list(fields.keys())}")
    else:
        print(f"  ⚠️ 未找到 {tier}/{code}")

# ===== 2. 新增 growth: 浙能电力(600023.SH) =====
_, existing = find_entry("growth", "600023.SH")
if not existing:
    zhe_neng = {
        "code": "600023.SH",
        "name": "浙能电力",
        "board": "沪",
        "sector": "公用事业/电力",
        "last_close": 5.78,
        "price_bands": [11.33, 8.50, 6.80],
        "valuation_anchor": "以股息率为锚：避开>11.33元(DY<3%)，关注8.50-11.33元(DY3-4%)，较好6.80-8.50元(DY4-5%)，理想<6.80元(DY>5%)",
        "dv_ttm": 5.88,
        "prebuy_conclusion": "浙江省垄断性区域电力平台，股息率5.88%（全批次最高）已在理想价位，近60日偏高位（5.78 vs高5.87），可小批量建仓",
        "next_earnings_date": "2026-04-28",
        "next_earnings_type": "半年报",
        "tags": ["绿色电力", "公用事业", "高息", "火电+新能源"]
    }
    wl["watchlists"]["growth"].append(zhe_neng)
    print("  新增 growth/600023.SH 浙能电力")

# ===== 3. 新增 radar: 内蒙华电, 华能国际, 福能股份, 宝新能源 =====
new_radars = [
    {
        "code": "600863.SH",
        "name": "内蒙华电",
        "board": "沪",
        "sector": "公用事业/电力",
        "last_close": 4.56,
        "price_bands": [6.10, 4.60, 3.70],
        "valuation_anchor": "以股息率为锚：避开>6.10元(DY<3%)，关注4.60-6.10元(DY3-4%)，较好3.70-4.60元(DY4-5%)，理想<3.70元(DY>5%)",
        "dv_ttm": 4.02,
        "prebuy_conclusion": "华能集团控股内蒙古煤电平台，ROE14.82%是绿电指数中最高，当前PE14.6x偏高，等回调至DY>4.5%再介入",
        "entry_trigger": "股价跌至4.0元以下（DY>4.5%），或季报净利同比由负转正",
        "next_earnings_date": "2026-08-31（估算）",
        "next_earnings_type": "半年报",
        "tags": ["绿色电力", "火电", "内蒙古", "煤电转型"]
    },
    {
        "code": "600011.SH",
        "name": "华能国际",
        "board": "沪",
        "sector": "公用事业/电力",
        "last_close": 6.95,
        "price_bands": [9.00, 6.75, 5.40],
        "valuation_anchor": "以股息率为锚：避开>9.00元(DY<3%)，关注6.75-9.00元(DY3-4%)，较好5.40-6.75元(DY4-5%)，理想<5.40元(DY>5%)",
        "dv_ttm": 3.88,
        "prebuy_conclusion": "全批次PE最低(7.57x)，OCF4.66x极强，DY⚠️3.88%略低于门槛，当前处于60日低位区间，等DY达4%（约6.75元以下）再建仓",
        "entry_trigger": "股价跌至6.75元以下（DY>4%），或煤价同比持续下降且季报净利同比转正",
        "next_earnings_date": "2026-04-29",
        "next_earnings_type": "一季报",
        "tags": ["绿色电力", "火电", "新能源转型", "大盘央企"]
    },
    {
        "code": "600483.SH",
        "name": "福能股份",
        "board": "沪",
        "sector": "公用事业/电力",
        "last_close": 9.89,
        "price_bands": [12.77, 9.58, 7.66],
        "valuation_anchor": "以股息率为锚：避开>12.77元(DY<3%)，关注9.58-12.77元(DY3-4%)，较好7.66-9.58元(DY4-5%)，理想<7.66元(DY>5%)",
        "dv_ttm": 3.87,
        "prebuy_conclusion": "福建省国资委控股水电+火电平台，ROE11.2%+OCF1.73x稳健，DY⚠️3.87%略低于门槛，60日偏低位（9.89 vs高11.30），等DY达4%",
        "entry_trigger": "股价跌至9.58元以下（DY>4%），或水电来水改善推动季报利润同比改善",
        "next_earnings_date": "2026-08-31（估算）",
        "next_earnings_type": "半年报",
        "tags": ["绿色电力", "水电", "火电", "福建省国企"]
    },
    {
        "code": "000690.SZ",
        "name": "宝新能源",
        "board": "深",
        "sector": "公用事业/新能源",
        "last_close": 5.46,
        "price_bands": [6.67, 5.00, 4.00],
        "valuation_anchor": "以股息率为锚：避开>6.67元(DY<3%)，关注5.00-6.67元(DY3-4%)，较好4.00-5.00元(DY4-5%)，理想<4.00元(DY>5%)",
        "dv_ttm": 3.66,
        "prebuy_conclusion": "批次中唯一营收正增长(+9.2%)的小市值新能源运营商，DY⚠️3.66%，市值仅119亿，等DY达4%（约5元以下）且营收增长持续验证后再建仓",
        "entry_trigger": "股价跌至5.00元以下（DY>4%），且连续2季度营收同比正增长",
        "next_earnings_date": "2026-04-28",
        "next_earnings_type": "一季报",
        "tags": ["绿色电力", "风电", "光伏", "小市值"]
    },
]

for entry in new_radars:
    _, existing = find_entry("radar", entry["code"])
    if not existing:
        wl["watchlists"]["radar"].append(entry)
        print(f"  新增 radar/{entry['code']} {entry['name']}")
    else:
        print(f"  已存在 radar/{entry['code']}")

# 版本升级
wl["schema_version"] = 17
print(f"\nschema_version: 16 → 17")

with open(WL_PATH, "w", encoding="utf-8") as f:
    json.dump(wl, f, ensure_ascii=False, indent=2)

total = [len(wl["watchlists"][t]) for t in ["core","growth","radar"]]
print(f"最终：core={total[0]}, growth={total[1]}, radar={total[2]}")
print("✅ 保存完成")
