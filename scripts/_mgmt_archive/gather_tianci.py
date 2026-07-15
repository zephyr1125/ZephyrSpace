"""
Gather comprehensive management data for 天赐材料 (002709.SZ)
Runs all CNINFO API queries.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cninfo_api import CninfoClient

client = CninfoClient()
SCODE = "002709"
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tianci_data")
os.makedirs(OUTDIR, exist_ok=True)

def save_json(filename, data):
    path = os.path.join(OUTDIR, filename)
    if hasattr(data, 'to_dict'):
        data = data.to_dict(orient='records')
    elif hasattr(data, 'to_json'):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data.to_json(orient='records', force_ascii=False, indent=2))
        print(f"  Saved {len(data)} records to {filename}")
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    if isinstance(data, list):
        print(f"  Saved {len(data)} records to {filename}")
    else:
        print(f"  Saved to {filename}")

# ============================================================
# BATCH 1: Simple queries (no date params needed)
# ============================================================

print("=== BATCH 1: Basic Info ===")

# 1. Company Profile
print("\n[1/12] company_profile...")
profile = client.company_profile(SCODE)
save_json("01_company_profile.json", profile)
print(f"  Keys: {list(profile.keys()) if isinstance(profile, dict) else 'N/A'}")

# 2. Top 10 shareholders
print("\n[3/12] top10_holders...")
top10 = client.top10_holders(SCODE)
save_json("03_top10_holders.json", top10)

# 3. Dividends
print("\n[4/12] dividends...")
divs = client.dividends(SCODE)
save_json("04_dividends.json", divs)

# 4. Share changes (股本变动)
print("\n[5/12] share_changes...")
shares = client.share_changes(SCODE)
save_json("05_share_changes.json", shares)

# 5. Share pledge (all records, not just latest)
print("\n[8/12] share_pledge (all)...")
pledge = client.share_pledge(SCODE, latest_only=False)
save_json("08_share_pledge.json", pledge)

# 6. Share freeze (all records, not just latest)
print("\n[9/12] share_freeze (all)...")
freeze = client.share_freeze(SCODE, latest_only=False)
save_json("09_share_freeze.json", freeze)

print("\n=== BATCH 1 Complete ===\n")

# ============================================================
# BATCH 2: Queries with limits
# ============================================================

print("=== BATCH 2: Limited Records ===")

# 7. Executive trades (max 50)
print("\n[2/12] executive_trades (limit=50)...")
trades = client.executive_trades(SCODE, limit=50)
save_json("02_executive_trades.json", trades)

# 8. Company penalties (max 30)
print("\n[6/12] company_penalties (limit=30)...")
penalties = client.company_penalties(SCODE, limit=30)
save_json("06_company_penalties.json", penalties)

# 9. Company lawsuits (max 20)
print("\n[7/12] company_lawsuits (limit=20)...")
lawsuits = client.company_lawsuits(SCODE, limit=20)
save_json("07_company_lawsuits.json", lawsuits)

# 10. Investment ratings (max 30)
print("\n[11/12] investment_ratings (limit=30)...")
ratings = client.investment_ratings(SCODE, limit=30)
save_json("11_investment_ratings.json", ratings)

# 11. IRM Q&A (3 pages)
print("\n[10/12] irm_qa (pages=3)...")
irm = client.irm_qa(SCODE, pages=3, answered_only=True)
save_json("10_irm_qa.json", irm)

print("\n=== BATCH 2 Complete ===\n")

# ============================================================
# BATCH 3: Personnel announcements (5 years, broad search)
# ============================================================

print("=== BATCH 3: Personnel Announcements ===")

# Search all announcements from last 5 years, filter for personnel-related
print("\n[12/12] Personnel announcements search (2021-2026)...")

# We'll search broad categories and filter by title keywords
personnel_keywords = ['离任', '辞职', '聘任', '选举', '高管', '副总裁', '总经理', '董事长', 'CTO', 'CFO', '董秘',
                       '董事会', '监事会', '独立董事', '副总裁', '财务总监', '人事', '变更', '任命', '免职', '增补',
                       '监事', '董事', '换届', '离休', '退休']

all_personnel = []
seen_titles = set()

# Try multiple categories to maximize coverage
categories = [
    'category_ndbg_szsh',      # 年报
    'category_bndbg_szsh',     # 半年报
    # General announcements without specific category
]

# Search with general category (empty or broad)
for cat in ['']:  # empty = all categories
    print(f"  Searching category='{cat}' (2021-01-01~2026-12-31)...")
    try:
        df = client.list_announcements(
            SCODE, category=cat if cat else '',
            start_date="2021-01-01", end_date="2026-12-31",
            max_pages=5, page_size=50
        )
        if len(df) == 0:
            print(f"    No results for this category")
            continue
        print(f"    Got {len(df)} total announcements")

        for _, row in df.iterrows():
            title = str(row['标题'])
            # Check if any personnel keyword is in the title
            if any(kw in title for kw in personnel_keywords):
                if title not in seen_titles:
                    seen_titles.add(title)
                    all_personnel.append({
                        '发布日期': str(row['发布日期']),
                        '标题': title,
                        'PDF_URL': row['PDF_URL'],
                        '文件大小KB': row['文件大小KB'],
                    })
    except Exception as e:
        print(f"    Error: {e}")

# Also try with specific CNINFO personnel-related categories
personnel_cats = [
    'category_rsxxts_szsh',    # 人事信息提示
    'category_gdmz_szsh',      # 股东名册/高管持股变动
    'category_dshgghy_szsh',   # 董事会/股东大会
]

for cat in personnel_cats:
    print(f"  Searching category='{cat}' (2021-01-01~2026-12-31)...")
    try:
        df = client.list_announcements(
            SCODE, category=cat,
            start_date="2021-01-01", end_date="2026-12-31",
            max_pages=3, page_size=50
        )
        if len(df) == 0:
            print(f"    No results")
            continue
        print(f"    Got {len(df)} total announcements")
        for _, row in df.iterrows():
            title = str(row['标题'])
            if title not in seen_titles:
                seen_titles.add(title)
                all_personnel.append({
                    '发布日期': str(row['发布日期']),
                    '标题': title,
                    'PDF_URL': row['PDF_URL'],
                    '文件大小KB': row['文件大小KB'],
                })
    except Exception as e:
        print(f"    Error: {e}")

all_personnel.sort(key=lambda x: x['发布日期'], reverse=True)
save_json("12_personnel_announcements.json", all_personnel)
print(f"  Total personnel-related announcements found: {len(all_personnel)}")

print("\n=== ALL DONE ===")
print(f"All data saved to: {OUTDIR}")
