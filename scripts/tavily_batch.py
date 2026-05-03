"""Run Tavily prebuy research for all 4 companies"""
import sys, json
sys.path.insert(0, 'scripts')
from tavily_search import prebuy_web_research

companies = [
    ("万辰集团", "300972.SZ"),
    ("宏桥控股", "002379.SZ"),
    ("兴齐眼药", "300573.SZ"),
    ("盐津铺子", "002847.SZ"),
]

for name, code in companies:
    print(f"\n{'='*60}")
    print(f"=== {name} ({code}) ===")
    try:
        result = prebuy_web_research(name, code)
        print(f"RED FLAGS:\n{result.get('red_flags', 'N/A')}")
        print(f"\nRECENT NEWS:\n{result.get('recent_news', 'N/A')}")
        print(f"\nCOMPANY INFO:\n{result.get('company_info', 'N/A')[:500]}")
    except Exception as e:
        print(f"Error: {e}")
