"""Read and save tavily results to a clean text file"""
import json, sys

with open("data/tavily_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

output = []
for company, result in data.items():
    output.append(f"\n{'='*60}")
    output.append(f"=== {company} ===")
    if "error" in result:
        output.append(f"ERROR: {result['error']}")
        continue
    
    rf = result.get("red_flags", "")
    rn = result.get("recent_news", "")
    ci = result.get("company_info", "")
    
    output.append(f"\n[RED FLAGS]:")
    output.append(rf[:1000] if rf else "None")
    output.append(f"\n[RECENT NEWS]:")
    output.append(rn[:1000] if rn else "None")
    output.append(f"\n[COMPANY INFO]:")
    output.append(ci[:800] if ci else "None")

text = "\n".join(output)
with open("data/tavily_clean.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("Saved to data/tavily_clean.txt", file=sys.stderr)
