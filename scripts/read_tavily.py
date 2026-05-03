"""Read and print tavily results properly"""
import json

with open("data/tavily_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for company, result in data.items():
    print(f"\n{'='*60}")
    print(f"=== {company} ===")
    if "error" in result:
        print(f"ERROR: {result['error']}")
        continue
    
    rf = result.get("red_flags", "")
    rn = result.get("recent_news", "")
    ci = result.get("company_info", "")
    
    # Print first 800 chars of each
    print(f"\n[RED FLAGS] (first 800 chars):")
    print(rf[:800] if rf else "None")
    print(f"\n[RECENT NEWS] (first 800 chars):")
    print(rn[:800] if rn else "None")
    print(f"\n[COMPANY INFO] (first 600 chars):")
    print(ci[:600] if ci else "None")
