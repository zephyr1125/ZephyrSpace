import os, sys
sys.path.insert(0, "scripts")
from dotenv import load_dotenv
load_dotenv()

# 测试 Tavily 是否可用
try:
    from tavily_search import prebuy_web_research, search_red_flags
    tavily_ok = True
    print("Tavily 可用")
except Exception as e:
    tavily_ok = False
    print(f"Tavily 不可用: {e}")
    import traceback; traceback.print_exc()

if tavily_ok:
    companies = [
        ("东阿阿胶", "000423.SZ"),
        ("锦江航运", "601083.SH"),
        ("诺普信", "002215.SZ"),
        ("华润三九", "000999.SZ"),
        ("亚太股份", "002284.SZ"),
    ]
    
    results = {}
    for name, code in companies:
        print(f"\n=== {name} {code} ===")
        try:
            r = prebuy_web_research(name, code)
            rf = r.get("red_flags","")[:800]
            rn = r.get("recent_news","")[:800]
            print(f"红旗: {rf[:300]}")
            print(f"近期: {rn[:300]}")
            results[code] = r
        except Exception as e:
            print(f"ERROR: {e}")
            results[code] = {}
    
    import json
    with open("batch8_tavily.json","w",encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n结果保存到 batch8_tavily.json")
