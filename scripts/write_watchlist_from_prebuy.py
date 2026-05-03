#!/usr/bin/env python3
"""将PreBuy分析结果写入watchlist（core和growth档位）"""

import json
import re
from pathlib import Path
from datetime import datetime, date, timedelta

VAULT_DIR = Path("E:\ObsidianVaults\ZephyrSpace")
COMPANIES_DIR = VAULT_DIR / "01-公司"
DATA_DIR = VAULT_DIR / "data"

# 核心和成长池的公司列表
CORE_COMPANIES = [
    "兴齐眼药",
    "大豪科技",
    "锦江航运",
    "诺普信",
    "华润三九"
]

GROWTH_COMPANIES = [
    "万辰集团",
    "盐津铺子",
    "TCL智家",
    "特宝生物",
    "悍高集团",
    "芭田股份",
    "福耀玻璃",
    "公牛集团",
    "金诚信",
    "伊之密",
    "山金国际",
    "小商品城",
    "佐力药业",
    "紫金矿业",
    "羚锐制药",
    "伊利股份",
    "爱尔眼科",
    "三美股份",
    "菜百股份",
    "赤峰黄金"
]

def last_trading_day():
    """获取最近交易日"""
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d

def extract_frontmatter(content):
    """提取yaml frontmatter（简单实现）"""
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    fm_text = match.group(1)
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line and not line.startswith('  '):
            key, val = line.split(':', 1)
            fm[key.strip()] = val.strip().strip('"\'')
    return fm

def extract_code(content):
    """从正文或frontmatter提取代码"""
    # 先从正文提取 `XXXXXX.SH` 或 `XXXXXX.SZ` 格式
    match = re.search(r'`?(\d{6}\.(SH|SZ))`?', content)
    if match:
        return match.group(1)
    return None

def extract_data_from_page(company_name, tier):
    """从公司页面提取数据"""
    page_path = COMPANIES_DIR / f"{company_name}.md"
    if not page_path.exists():
        print(f"⚠️ {company_name} 页面不存在")
        return None
    
    with open(page_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fm = extract_frontmatter(content)
    code = extract_code(content)
    
    if not code:
        print(f"⚠️ {company_name} 无法提取代码")
        return None
    
    # 提取PreBuy结论
    prebuy_match = re.search(r'## PreBuy 结论.*?\*\*([^:]*?)：([^*]*?)\*\*\n(.*?)(?=##|$)', content, re.DOTALL)
    prebuy_conclusion = ""
    if prebuy_match:
        prebuy_conclusion = prebuy_match.group(3).strip().split('\n')[0][:100]
    
    # 提取主要红旗
    flags_match = re.search(r'## 主要红旗\n(.*?)(?=##|$)', content, re.DOTALL)
    risk_flags = []
    if flags_match:
        flags_text = flags_match.group(1)
        for line in flags_text.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                risk_flags.append(line[1:].strip())
    
    # 提取财务数据
    price_match = re.search(r'当前股价\s*\|\s*([\d.]+)', content)
    current_price = float(price_match.group(1)) if price_match else None
    
    pe_match = re.search(r'PE（TTM）\s*\|\s*([\d.]+)', content)
    pe_ttm = float(pe_match.group(1)) if pe_match else None
    
    roe_match = re.search(r'ROE（最新年报）\s*\|\s*([\d.]+)%', content)
    roe = float(roe_match.group(1)) if roe_match else None
    
    # 提取价格区间
    consider_match = re.search(r'较好区间\s*\|\s*([\d.]+)', content)
    watch_match = re.search(r'中性区\s*\|\s*([\d.]+)', content)
    avoid_match = re.search(r'追高区\s*\|\s*([\d.]+)', content)
    
    consider_price = float(consider_match.group(1)) if consider_match else None
    watch_price = float(watch_match.group(1)) if watch_match else None
    avoid_price = float(avoid_match.group(1)) if avoid_match else None
    
    # 股息率（暂时设为None，应从Tushare更新）
    dv_ttm = None
    
    # 下一期财报（暂时设为估算值）
    next_earnings_type = "年报"  # 默认值，需手动更新
    today = datetime.now()
    if today.month < 4:
        next_earnings_date = f"{today.year}-04-30"
        next_earnings_type = "年报"
    elif today.month < 8:
        next_earnings_date = f"{today.year}-08-31"
        next_earnings_type = "半年报"
    elif today.month < 10:
        next_earnings_date = f"{today.year}-10-31"
        next_earnings_type = "三季报"
    else:
        next_earnings_date = f"{today.year + 1}-04-30"
        next_earnings_type = "年报"
    
    # 周期性
    cycle_is_cyclical = False
    cycle_position = None
    
    board = code[-2]  # SH or SZ
    board_map = {'H': '沪', 'Z': '深'}
    board = board_map.get(board, '深')
    
    return {
        'name': company_name,
        'code': code,
        'tier': tier,
        'source_etf': 'direct',
        'position_role': f"高ROE低PE {tier}档标的",
        'prebuy_conclusion': prebuy_conclusion,
        'watch_reason': f"ROE{roe}%+PE低估值" if roe else "ROE+PE优势",
        'current_price': current_price,
        'price_date': str(last_trading_day()),
        'board': board,
        'price_bands': [avoid_price, watch_price, consider_price] if all([avoid_price, watch_price, consider_price]) else [None, None, None],
        'risk_flags': risk_flags[:2] if risk_flags else ["待验证", "待关注"],
        'valuation_anchor': f"PE TTM {pe_ttm}x (历史低位)" if pe_ttm else "历史低位",
        'dv_ttm': dv_ttm,
        'next_earnings_date': next_earnings_date,
        'next_earnings_type': next_earnings_type,
        'cycle_is_cyclical': cycle_is_cyclical,
    }

def load_watchlist(filename):
    """加载现有watchlist"""
    path = DATA_DIR / filename
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'version': 1, 'updated_at': str(datetime.now()), 'entries': []}

def merge_entries(existing, new_entries):
    """合并条目（新的覆盖旧的，根据code判重）"""
    existing_codes = {e['code'] for e in existing}
    result = existing.copy()
    
    for new in new_entries:
        # 删除旧的同code条目
        result = [e for e in result if e['code'] != new['code']]
        result.append(new)
    
    return result

def write_watchlist():
    """主逻辑：提取数据并写入watchlist"""
    print("=" * 60)
    print("开始写入watchlist (Core + Growth)")
    print("=" * 60)
    
    # Core
    print("\n📍 处理 CORE 档位 (5家)...")
    core_entries = []
    for name in CORE_COMPANIES:
        data = extract_data_from_page(name, 'core')
        if data:
            core_entries.append(data)
            print(f"  ✓ {name} ({data['code']})")
    
    # Growth
    print("\n📍 处理 GROWTH 档位 (20家)...")
    growth_entries = []
    for name in GROWTH_COMPANIES:
        data = extract_data_from_page(name, 'growth')
        if data:
            growth_entries.append(data)
            print(f"  ✓ {name} ({data['code']})")
    
    # 写入Core
    print("\n💾 写入 watchlist_core.json...")
    core_watchlist = load_watchlist('watchlist_core.json')
    core_watchlist['entries'] = merge_entries(core_watchlist.get('entries', []), core_entries)
    core_watchlist['updated_at'] = str(datetime.now())
    
    with open(DATA_DIR / 'watchlist_core.json', 'w', encoding='utf-8') as f:
        json.dump(core_watchlist, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Core池现有 {len(core_watchlist['entries'])} 家公司")
    
    # 写入Growth
    print("\n💾 写入 watchlist_growth.json...")
    growth_watchlist = load_watchlist('watchlist_growth.json')
    growth_watchlist['entries'] = merge_entries(growth_watchlist.get('entries', []), growth_entries)
    growth_watchlist['updated_at'] = str(datetime.now())
    
    with open(DATA_DIR / 'watchlist_growth.json', 'w', encoding='utf-8') as f:
        json.dump(growth_watchlist, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Growth池现有 {len(growth_watchlist['entries'])} 家公司")
    
    print("\n" + "=" * 60)
    print(f"✅ 完成！共写入：")
    print(f"   • Core: {len(core_entries)} 家")
    print(f"   • Growth: {len(growth_entries)} 家")
    print("=" * 60)

if __name__ == '__main__':
    write_watchlist()
