"""Tavily搜索工商银行关键指标"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from scripts.tavily_search import _get_client

client = _get_client()

# 1. 核心财务指标（NIM, NPL, 资本充足率）
r1 = client.search(
    '工商银行 601398 2025年报 净息差 不良贷款率 资本充足率',
    max_results=5, search_depth='advanced'
)
print('=== 核心银行指标 ===')
for i, res in enumerate(r1.get('results', [])):
    title = res.get('title', '')
    content = res.get('content', '')[:400]
    url = res.get('url', '')
    print(f'{i+1}. [{title}]')
    print(f'   {content}')
    print()

# 2. 近期风险/监管事件
r2 = client.search(
    '工商银行 2025 2026 监管处罚 违规 罚款 不良',
    max_results=5, search_depth='advanced'
)
print('=== 监管/风险事件 ===')
for i, res in enumerate(r2.get('results', [])):
    title = res.get('title', '')
    content = res.get('content', '')[:400]
    print(f'{i+1}. [{title}]')
    print(f'   {content}')
    print()

# 3. 近期股价催化剂
r3 = client.search(
    '工商银行 2026 一季报 分红 增持 中央汇金',
    max_results=4, search_depth='advanced'
)
print('=== 近期催化剂 ===')
for i, res in enumerate(r3.get('results', [])):
    title = res.get('title', '')
    content = res.get('content', '')[:400]
    print(f'{i+1}. [{title}]')
    print(f'   {content}')
    print()
