"""
931897 中证绿色电力指数 粗筛脚本
行业类型：公用事业/能源
参数：市值≥40亿、ROE≥8%、股息率≥4%、营收同比≥-15%、PE>0（亏损排除）
候选排序：股息率降序，超15家则取前15
"""
import tushare as ts, os, time, json
from dotenv import load_dotenv

load_dotenv(r"E:\ObsidianVaults\ZephyrSpace\.env")
ts.set_token(os.getenv("TUSHARE_TOKEN"))
pro = ts.pro_api()

TRADE_DATE = "20260427"
INDEX_CODE = "931897.CSI"

# 行业参数（公用事业/能源）
MV_MIN = 40       # 亿元（total_mv为万元，需/10000）
ROE_MIN = 8.0     # %
DY_MIN = 4.0      # % 股息率
OR_YOY_MIN = -15  # % 营收同比
BORDER_TOLERANCE = 0.20  # 边界模糊±20%

print(f"=== 931897 粗筛 ===")
print(f"参数：市值≥{MV_MIN}亿, ROE≥{ROE_MIN}%, 股息率≥{DY_MIN}%, 营收同比≥{OR_YOY_MIN}%, PE>0")

# Step1: 拉取全成分股
print("\n[1] 拉取成分股...")
df = pro.index_weight(index_code=INDEX_CODE)
latest = df["trade_date"].max()
stocks = df[df["trade_date"] == latest].sort_values("weight", ascending=False).reset_index(drop=True)
print(f"最新权重日期：{latest}, 成分股数：{len(stocks)}")

codes = stocks["con_code"].tolist()
weights = dict(zip(stocks["con_code"], stocks["weight"]))

# Step2: 逐只拉 daily_basic（含 dv_ttm, pb）
print(f"\n[2] 拉取 daily_basic（{len(codes)}只）...")
db_map = {}
for i, code in enumerate(codes):
    r = pro.daily_basic(ts_code=code, trade_date=TRADE_DATE,
                        fields="ts_code,pe_ttm,total_mv,pb,dv_ttm")
    if len(r):
        db_map[code] = r.iloc[0].to_dict()
    time.sleep(0.11)
    if (i+1) % 10 == 0:
        print(f"  daily_basic {i+1}/{len(codes)}")

# Step3: 逐只拉 fina_indicator（优先年报）
print(f"\n[3] 拉取 fina_indicator（{len(codes)}只）...")
fi_map = {}
for i, code in enumerate(codes):
    r = pro.fina_indicator(ts_code=code,
                           fields="ts_code,end_date,roe,or_yoy",
                           limit=5)
    if len(r):
        annual = r[r["end_date"].str.endswith("1231")]
        row = annual.iloc[0] if len(annual) else r.iloc[0]
        fi_map[code] = row.to_dict()
    time.sleep(0.11)
    if (i+1) % 10 == 0:
        print(f"  fina_indicator {i+1}/{len(codes)}")

# Step4: 筛选
print("\n[4] 筛选...")
results = []
for rank, code in enumerate(codes, 1):
    db = db_map.get(code, {})
    fi = fi_map.get(code, {})
    
    mv = db.get("total_mv", 0)
    mv_yi = mv / 10000 if mv else 0
    pe = db.get("pe_ttm")
    dy = db.get("dv_ttm") or 0
    roe = fi.get("roe") or 0
    or_yoy = fi.get("or_yoy")
    end_date = fi.get("end_date", "")
    
    # 硬淘汰：PE<=0（亏损）
    if pe is None or pe <= 0:
        results.append({"rank": rank, "code": code, "weight": round(weights.get(code,0),2),
                        "mv_yi": round(mv_yi,0), "pe": pe, "dy": dy, "roe": round(roe,1),
                        "or_yoy": or_yoy, "end_date": end_date, "pass": False, "fail_reason": "PE<=0(亏损)"})
        continue
    
    fails = []
    borders = []
    
    # 市值门槛
    if mv_yi < MV_MIN:
        if mv_yi >= MV_MIN * (1 - BORDER_TOLERANCE):
            borders.append(f"市值{mv_yi:.0f}亿⚠️")
        else:
            fails.append(f"市值{mv_yi:.0f}亿<{MV_MIN}亿")
    
    # ROE门槛
    if roe < ROE_MIN:
        if roe >= ROE_MIN * (1 - BORDER_TOLERANCE):
            borders.append(f"ROE={roe:.1f}%⚠️")
        else:
            fails.append(f"ROE={roe:.1f}%<{ROE_MIN}%")
    
    # 股息率门槛
    if dy < DY_MIN:
        if dy >= DY_MIN * (1 - BORDER_TOLERANCE):
            borders.append(f"DY={dy:.2f}%⚠️")
        else:
            fails.append(f"DY={dy:.2f}%<{DY_MIN}%")
    
    # 营收同比门槛
    if or_yoy is not None and or_yoy < OR_YOY_MIN:
        if or_yoy >= OR_YOY_MIN * (1 - BORDER_TOLERANCE):
            borders.append(f"or_yoy={or_yoy:.1f}%⚠️")
        else:
            fails.append(f"or_yoy={or_yoy:.1f}%<{OR_YOY_MIN}%")
    
    passed = len(fails) == 0
    border_only = passed and len(borders) > 0
    
    results.append({
        "rank": rank, "code": code, "weight": round(weights.get(code,0),2),
        "mv_yi": round(mv_yi,0), "pe": round(pe,1) if pe else None,
        "dy": round(dy,2), "roe": round(roe,1),
        "or_yoy": round(or_yoy,1) if or_yoy is not None else None,
        "end_date": end_date,
        "pass": passed, "border": border_only,
        "fail_reason": "; ".join(fails) if fails else ("⚠️边界:" + "; ".join(borders) if borders else "")
    })

passed = [r for r in results if r["pass"]]
print(f"\n=== 粗筛结果：{len(codes)}只 → {len(passed)}只通过 ===")
print(f"{'排名':<4} {'代码':<12} {'权重%':<7} {'市值亿':<8} {'PE':<7} {'DY%':<6} {'ROE%':<7} {'营收yoy%':<10} {'状态'}")
print("-"*85)
for r in results:
    status = "✅" if r["pass"] and not r.get("border") else ("⚠️" if r.get("border") else "❌")
    print(f"{r['rank']:<4} {r['code']:<12} {r['weight']:<7.2f} {r['mv_yi']:<8.0f} "
          f"{str(r['pe']):<7} {r['dy']:<6.2f} {r['roe']:<7.1f} "
          f"{str(r['or_yoy']):<10} {status} {r['fail_reason']}")

# 候选超15家按DY降序取前15
if len(passed) > 15:
    passed_sorted = sorted(passed, key=lambda x: x["dy"], reverse=True)[:15]
    print(f"\n候选>15家，按股息率降序取前15")
else:
    passed_sorted = sorted(passed, key=lambda x: x["dy"], reverse=True)

print(f"\n=== 进入深度分析的候选（{len(passed_sorted)}家，按股息率降序）===")
for r in passed_sorted:
    border = "⚠️" if r.get("border") else ""
    print(f"  {r['code']} DY={r['dy']}% ROE={r['roe']}% PE={r['pe']} 市值={r['mv_yi']}亿 {border}")

# 保存结果
with open(r"E:\ObsidianVaults\ZephyrSpace\data\screen_931897_result.json", "w", encoding="utf-8") as f:
    json.dump({"all": results, "candidates": passed_sorted, "trade_date": TRADE_DATE,
               "latest_weight_date": latest, "total": len(codes)}, f, ensure_ascii=False, indent=2)
print("\n结果已保存到 data/screen_931897_result.json")
