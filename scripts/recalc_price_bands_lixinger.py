"""
用理杏仁 API 重算 watchlist_index.json 中所有指数的 price_bands。
- 基于真实历史 PE 分位（3年 P20/P50/P80）
- 10 只走 cn/index/fundamental
- 24 只走 cn/industry/fundamental/sw_2021（需映射申万2021代码）
- price_bands = [q8v, q5v, q2v] × (当前点位 / 当前PE)

运行：python scripts/recalc_price_bands_lixinger.py
"""
import os, json, time, requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("LIXINGER_TOKEN")
BASE = "https://open.lixinger.com/api"
TRADE_DATE = "2026-04-29"  # 最近交易日

def post(endpoint, body, retries=2):
    body["token"] = TOKEN
    for i in range(retries + 1):
        try:
            r = requests.post(f"{BASE}/{endpoint}", json=body, timeout=15)
            return r.json()
        except Exception as e:
            if i == retries:
                return {"code": -1, "error": str(e)}
            time.sleep(1)

# ── 映射表：watchlist_index 中的 .SW 代码就是申万2021代码，直接使用
# （迁移后 index_code 格式：630000.SW，取 split(".")[0] 即得申万代码）
INDUSTRY_MAP = {
    "630000": "630000",   # 电力设备
    "640000": "640000",   # 机械设备
    "620000": "620000",   # 建筑装饰
    "760000": "760000",   # 环保
    "220000": "220000",   # 基础化工
    "650000": "650000",   # 国防军工
    "370500": "370500",   # 医疗器械（二级）
    "370000": "370000",   # 医药生物
    "340000": "340000",   # 食品饮料
    "450000": "450000",   # 商贸零售
    "280500": "280500",   # 乘用车（二级）
    "490200": "490200",   # 保险（二级）
    "490000": "490000",   # 非银金融
    "270000": "270000",   # 电子
}

METRICS = [
    "pe_ttm.mcw",
    "pe_ttm.y3.mcw.cvpos",
    "pe_ttm.y5.mcw.cvpos",
    "pe_ttm.y3.mcw.q2v",
    "pe_ttm.y3.mcw.q5v",
    "pe_ttm.y3.mcw.q8v",
    "dyr.mcw",
]

# index 接口额外支持 cp 字段
METRICS_INDEX = METRICS + ["cp"]

def fetch_index(code):
    """走 cn/index/fundamental"""
    resp = post("cn/index/fundamental", {
        "date": TRADE_DATE,
        "stockCodes": [code],
        "metricsList": METRICS_INDEX,
    })
    if resp.get("code") == 1 and resp.get("data"):
        return resp["data"][0]
    return None

def fetch_industry(sw_code):
    """走 cn/industry/fundamental/sw_2021"""
    resp = post("cn/industry/fundamental/sw_2021", {
        "date": TRADE_DATE,
        "stockCodes": [sw_code],
        "metricsList": METRICS,
    })
    if resp.get("code") == 1 and resp.get("data"):
        return resp["data"][0]
    return None

# ── 直接走 index 接口的代码（从探测结果得出）
INDEX_CODES = {
    "399986", "399975", "H30182", "931775",
    "H30184", "H30590", "930598", "000932", "399396", "399989"
}

def calc_bands(d, cp_override=None):
    """
    从 lixinger 返回数据计算 price_bands。
    公式：band_price = q_pe × (cp / pe_ttm.mcw)
    即：PE历史分位对应的PE值 × 每PE对应点位
    """
    pe = d.get("pe_ttm.mcw")
    cp = d.get("cp") or cp_override
    q2 = d.get("pe_ttm.y3.mcw.q2v")
    q5 = d.get("pe_ttm.y3.mcw.q5v")
    q8 = d.get("pe_ttm.y3.mcw.q8v")

    if not all([pe, cp, q2, q5, q8]) or pe <= 0:
        return None, None

    ratio = cp / pe  # 每单位PE对应的点位（≈ EPS对应点位）
    b_q2 = round(q2 * ratio)
    b_q5 = round(q5 * ratio)
    # q8 极端值截断：若 q8 > q5 × 4，使用 q5 × 2 代替（防止科技/成长行业历史PE泡沫污染上界）
    if q8 > q5 * 4:
        print(f"  ⚠️  q8极端值({q8:.1f})截断为 q5×2({q5*2:.1f})")
        q8 = q5 * 2
    b_q8 = round(q8 * ratio)
    return [b_q8, b_q5, b_q2], ratio

# ── 主流程
with open("data/watchlist_index.json", encoding="utf-8") as f:
    wl = json.load(f)

today = date.today().isoformat()
updated = 0
errors = []

for idx in wl["indices"]:
    code = idx["index_code"].split(".")[0]
    name = idx["name"]
    print(f"\n处理：{code}  {name}")

    d = None
    source_label = ""

    if code in INDEX_CODES:
        d = fetch_index(code)
        source_label = f"lixinger cn/index/fundamental ({code})"
    elif code in INDUSTRY_MAP:
        sw_code = INDUSTRY_MAP[code]
        d = fetch_industry(sw_code)
        source_label = f"lixinger cn/industry/fundamental/sw_2021 ({sw_code}，近似映射自 {code})"
    else:
        print(f"  ⚠️  未知代码，跳过")
        errors.append(code)
        time.sleep(0.3)
        continue

    time.sleep(0.35)  # 限流

    if not d:
        print(f"  ❌  无数据返回")
        errors.append(code)
        continue

    pe    = d.get("pe_ttm.mcw")
    cp    = d.get("cp")
    cvpos3 = d.get("pe_ttm.y3.mcw.cvpos")
    cvpos5 = d.get("pe_ttm.y5.mcw.cvpos")
    q2    = d.get("pe_ttm.y3.mcw.q2v")
    q5    = d.get("pe_ttm.y3.mcw.q5v")
    q8    = d.get("pe_ttm.y3.mcw.q8v")
    dyr   = d.get("dyr.mcw")

    # cp 字段行业接口可能不返回，需要从 watchlist 取当前点位作 fallback
    if not cp:
        cp = idx.get("current_index_price")
        print(f"  ⚠️  cp 未返回，使用 watchlist 存档点位 {cp}")

    bands, ratio = calc_bands(d, cp_override=cp)

    if not bands:
        print(f"  ❌  数据不完整，无法计算 bands：pe={pe} cp={cp} q2={q2}")
        errors.append(code)
        continue

    pct3 = f"{cvpos3*100:.1f}%" if cvpos3 is not None else "N/A"
    pct5 = f"{cvpos5*100:.1f}%" if cvpos5 is not None else "N/A"
    print(f"  PE={pe:.2f}  点位={cp:.1f}  3y分位={pct3}  5y分位={pct5}")
    print(f"  PE锚 q2={q2:.2f} q5={q5:.2f} q8={q8:.2f}")
    print(f"  price_bands = {bands}")

    # ── 更新 watchlist 字段
    idx["current_pe"]        = round(pe, 2) if pe else idx.get("current_pe")
    idx["current_dy"]        = round(dyr, 2) if dyr else idx.get("current_dy")
    idx["pe_3y_percentile"]  = round(cvpos3 * 100, 1) if cvpos3 is not None else idx.get("pe_3y_percentile")
    idx["pe_5y_percentile"]  = round(cvpos5 * 100, 1) if cvpos5 is not None else idx.get("pe_5y_percentile")
    idx["price_bands"]       = bands
    idx["valuation_anchor"]  = (
        f"3年历史PE分位锚点（{TRADE_DATE}）："
        f"P80对应PE={q8:.1f}→点位{bands[0]}（偏贵区），"
        f"P50对应PE={q5:.1f}→点位{bands[1]}（历史中位），"
        f"P20对应PE={q2:.1f}→点位{bands[2]}（积极买入区）。"
        f"数据来源 {source_label}。"
    )
    idx["price_date"]        = TRADE_DATE
    idx["last_updated"]      = today
    updated += 1

# ── 保存
with open("data/watchlist_index.json", "w", encoding="utf-8") as f:
    json.dump(wl, f, ensure_ascii=False, indent=2)

print(f"\n{'='*50}")
print(f"✅ 完成：{updated} 只更新，{len(errors)} 只失败")
if errors:
    print(f"   失败：{errors}")
print(f"已写入 data/watchlist_index.json")
