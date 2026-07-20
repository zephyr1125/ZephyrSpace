"""Update next_earnings_date for watchlist companies with confirmed official dates.
Sources: workflow wf_490b78ba-36a — official company press releases, exchange calendars, company IR confirmations.
"""

import json
import os

VAULT = r"E:\ObsidianVaults\ZephyrSpace"

# === CONFIRMED DATES (official sources only) ===

# US companies — confirmed via company press release / SEC filing / IR page
us_dates = {
    "CME.US":     ("2026-07-22", "Q2 2026季报"),
    "LECO.US":    ("2026-07-30", "Q2 2026季报"),
    "SPGI.US":    ("2026-07-28", "Q2 2026季报"),
    "FSLR.US":    ("2026-07-30", "Q2 2026季报"),
    "EME.US":     ("2026-07-30", "Q2 2026季报"),
    "CACI.US":    ("2026-08-05", "FQ4 FY2026季报"),
    "CBOE.US":    ("2026-07-31", "Q2 2026季报"),
    "TW.US":      ("2026-07-30", "Q2 2026季报"),
    "STN.US":     ("2026-08-12", "Q2 2026季报"),
    "CRUS.US":    ("2026-08-05", "Q1 FY2027季报"),
    "ACN.US":     ("2026-09-24", "Q4 FY2026季报"),
    "EXLS.US":    ("2026-07-28", "Q2 2026季报"),
    "MSA.US":     ("2026-07-30", "Q2 2026季报"),
    "GIB.US":     ("2026-07-29", "Q3 FY2026季报"),
    "NXPI.US":    ("2026-07-28", "Q2 2026季报"),
    "MMS.US":     ("2026-08-06", "Q3 FY2026季报"),
    "GMED.US":    ("2026-08-06", "Q2 2026季报"),
    "SKHY.US":    ("2026-07-29", "Q2 2026季报"),
    "NXT.US":     ("2026-07-30", "Q1 FY2027季报"),
}

# A-share companies — confirmed via exchange scheduled calendar + some company IR confirmations
ashare_dates = {
    "000333.SZ":  ("2026-08-29", "半年报"),
    "300124.SZ":  ("2026-08-29", "半年报"),
    "688188.SH":  ("2026-08-18", "半年报"),
    "688018.SH":  ("2026-07-31", "半年报"),  # company confirmed via 互动易
    "600036.SH":  ("2026-08-29", "半年报"),
    "002463.SZ":  ("2026-08-26", "半年报"),
    "002318.SZ":  ("2026-08-25", "半年报"),  # company change notice
    "688278.SH":  ("2026-08-19", "半年报"),
    "000708.SZ":  ("2026-08-21", "半年报"),
    "300760.SZ":  ("2026-08-29", "半年报"),  # company confirmed via 互动易 2026-07-14
    "603893.SH":  ("2026-08-22", "半年报"),  # company confirmed via 互动易 2026-07-15
    "300454.SZ":  ("2026-08-22", "半年报"),
    "300274.SZ":  ("2026-08-29", "半年报"),
    "002027.SZ":  ("2026-08-19", "半年报"),
    "300408.SZ":  ("2026-08-28", "半年报"),
    "000999.SZ":  ("2026-08-22", "半年报"),
    "688235.SH":  ("2026-08-27", "半年报"),
    "600885.SH":  ("2026-07-30", "半年报"),
    "600760.SH":  ("2026-08-28", "半年报"),
    "600887.SH":  ("2026-08-27", "半年报"),
    "601958.SH":  ("2026-08-21", "半年报"),
    "603195.SH":  ("2026-08-28", "半年报"),
    "600886.SH":  ("2026-08-28", "半年报"),
    "603501.SH":  ("2026-08-25", "半年报"),
    "688300.SH":  ("2026-08-15", "半年报"),
    "605499.SH":  ("2026-07-31", "半年报"),  # board meeting July 30
    "300308.SZ":  ("2026-08-24", "半年报"),  # company confirmed IR call July 12
    "300037.SZ":  ("2026-08-25", "半年报"),  # 董秘 confirmed
    "002142.SZ":  ("2026-08-20", "半年报"),
    "600919.SH":  ("2026-08-20", "半年报"),
    "002270.SZ":  ("2026-08-29", "半年报"),
    "600025.SH":  ("2026-08-26", "半年报"),
    "002032.SZ":  ("2026-08-28", "半年报"),
    "600285.SH":  ("2026-08-12", "半年报"),
    "601298.SH":  ("2026-08-29", "半年报"),
    "000568.SZ":  ("2026-08-26", "半年报"),
    "603345.SH":  ("2026-08-25", "半年报"),
    "002352.SZ":  ("2026-08-29", "半年报"),
    "600933.SH":  ("2026-08-28", "半年报"),
    "002472.SZ":  ("2026-08-26", "半年报"),
    "300729.SZ":  ("2026-08-29", "半年报"),
}

# HK companies — confirmed via HKEX announcement / company IR page
hk_dates = {
    "00388.HK":   ("2026-08-19", "中期业绩"),
    "0669.HK":    ("2026-08-04", "中期业绩"),
    "02020.HK":   ("2026-08-26", "中期业绩"),  # board meeting notice July 20
}

# Progressive, Netflix, Adobe — already reported Q2, next Q date not yet announced → keep null
# PGR reported 2026-07-15, NFLX reported 2026-07-16, ADBE reported 2026-06-11

# === UPDATE FUNCTION ===

def update_file(filepath, date_map):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = 0
    for entry in data.get("entries", []):
        code = entry.get("code")
        if code in date_map:
            old_date = entry.get("next_earnings_date")
            old_type = entry.get("next_earnings_type")
            new_date, new_type = date_map[code]
            entry["next_earnings_date"] = new_date
            entry["next_earnings_type"] = new_type
            print(f"  {entry['name']} ({code}): {old_date} → {new_date} | {new_type}")
            updated += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return updated


# === MAIN ===

all_dates = {}
all_dates.update(us_dates)
all_dates.update(ashare_dates)
all_dates.update(hk_dates)

files = [
    os.path.join(VAULT, "data", "watchlist_core.json"),
    os.path.join(VAULT, "data", "watchlist_growth.json"),
    os.path.join(VAULT, "data", "watchlist_out_of_scope.json"),
]

total = 0
for fp in files:
    print(f"\n=== {os.path.basename(fp)} ===")
    n = update_file(fp, all_dates)
    total += n
    print(f"  Updated: {n} entries")

print(f"\n=== TOTAL UPDATED: {total} ===")

# Show still-null count
print("\n=== REMAINING NULL (no official date yet) ===")
for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nulls = [f"{e['name']} ({e['code']})" for e in data.get("entries", []) if e.get("next_earnings_date") is None]
    if nulls:
        print(f"\n{os.path.basename(fp)}: {len(nulls)} companies")
        for n in nulls:
            print(f"  - {n}")
