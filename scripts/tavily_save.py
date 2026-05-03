"""Run Tavily prebuy research for all 4 companies - save to file"""
import sys, json
sys.path.insert(0, 'scripts')
from tavily_search import prebuy_web_research

companies = [
    ("万辰集团", "300972.SZ"),
    ("宏桥控股", "002379.SZ"),
    ("兴齐眼药", "300573.SZ"),
    ("盐津铺子", "002847.SZ"),
]

all_results = {}
for name, code in companies:
    print(f"Researching {name}...", flush=True)
    try:
        result = prebuy_web_research(name, code)
        all_results[name] = result
        print(f"Done {name}", flush=True)
    except Exception as e:
        all_results[name] = {"error": str(e)}
        print(f"Error {name}: {e}", flush=True)

with open("data/tavily_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("Saved to data/tavily_results.json")
