"""
将 watchlist_index.json 中的 14 只行业指数代码替换为申万2021，
并删除 10 只冗余宽行业篮子指数（932077-932086）。
同步更新 05-A股指数/ 下的页面文件名和 frontmatter。

运行：python scripts/migrate_to_sw_index.py
"""
import json, os, subprocess, re
from datetime import date

VAULT = r"E:\ObsidianVaults\ZephyrSpace"
INDEX_DIR = os.path.join(VAULT, "05-A股指数")
WL_FILE = os.path.join(VAULT, "data", "watchlist_index.json")
TODAY = date.today().isoformat()

# ── 1. 要删除的 10 只宽行业篮子（932077-932086）
REMOVE_CODES = {
    "932077.CSI", "932078.CSI", "932079.CSI", "932080.CSI",
    "932081.CSI", "932082.CSI", "932083.CSI", "932084.CSI",
    "932085.CSI", "932086.CSI",
}

# ── 2. 要替换的 14 只（中证全指 → 申万2021）
# (old_code, old_name, new_code, new_name, sw_level)
RENAME_MAP = [
    ("931932.CSI", "中证全指电力设备指数",              "630000.SW", "电力设备",   "一级"),
    ("H30166.CSI", "中证全指机械制造指数",               "640000.SW", "机械设备",   "一级"),
    ("931931.CSI", "中证全指建筑装饰指数",               "620000.SW", "建筑装饰",   "一级"),
    ("931933.CSI", "中证全指环保指数",                   "760000.SW", "环保",       "一级"),
    ("932111.CSI", "中证全指化工行业指数",               "220000.SW", "基础化工",   "一级"),
    ("932116.CSI", "中证全指航空航天与国防行业指数",     "650000.SW", "国防军工",   "一级"),
    ("931940.CSI", "中证全指医疗指数",                   "370500.SW", "医疗器械",   "二级"),
    ("H30179.CSI", "中证全指医药指数",                   "370000.SW", "医药生物",   "一级"),
    ("H30177.CSI", "中证全指食品、饮料与烟草指数",       "340000.SW", "食品饮料",   "一级"),
    ("H30175.CSI", "中证全指零售业指数",                 "450000.SW", "商贸零售",   "一级"),
    ("H30164.CSI", "中证全指乘用车及零部件指数",         "280500.SW", "乘用车",     "二级"),
    ("H30186.CSI", "中证全指保险指数",                   "490200.SW", "保险",       "二级"),
    ("H30211.CSI", "中证全指资本市场指数",               "490000.SW", "非银金融",   "一级"),
    ("H30183.CSI", "中证全指电子指数",                   "270000.SW", "电子",       "一级"),
]
RENAME_DICT = {old: (new_code, new_name, sw_lvl) for old, _, new_code, new_name, sw_lvl in RENAME_MAP}

def git(*args):
    result = subprocess.run(["git", "-C", VAULT] + list(args), capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"  ⚠️  git {' '.join(args)} 失败: {result.stderr.strip()}")
    return result.returncode == 0

def find_page(code_bare, old_name):
    """在 05-A股指数/ 中找到对应页面文件（不含后缀）"""
    for fn in os.listdir(INDEX_DIR):
        if not fn.endswith(".md"):
            continue
        stem = fn[:-3]
        if stem.startswith(code_bare) or old_name.replace("、", "、") in stem:
            return fn
    return None

def update_frontmatter(filepath, new_code, new_name, sw_lvl):
    """替换文件中的 frontmatter 和一级标题"""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    old_code_bare = None
    # 找出旧代码（可能是 931932 / H30166 等）
    m = re.search(r'^指数代码:\s*"?([^"\n]+)"?', content, re.MULTILINE)
    if m:
        old_code_bare = m.group(1).split(".")[0]

    new_code_bare = new_code.split(".")[0]

    # 替换 frontmatter 字段
    content = re.sub(r'^(指数代码:\s*)"?[^"\n]+"?', f'\\1"{new_code}"', content, flags=re.MULTILINE)
    content = re.sub(r'^(指数名称:\s*)"?[^"\n]+"?', f'\\1"{new_name}"', content, flags=re.MULTILINE)

    # 替换 aliases（保留旧别名，加入新代码和简称）
    alias_repl = (
        f'aliases:\n'
        f'  - {new_name}\n'
        f'  - "{new_code_bare}"\n'
        f'  - 申万{sw_lvl}_{new_name}'
    )
    content = re.sub(r'^aliases:.*?(?=\n\S)', alias_repl, content, flags=re.MULTILINE | re.DOTALL)

    # 替换一级标题
    if old_code_bare:
        content = content.replace(
            f"# {old_code_bare} {content.split(chr(10))[0]}",  # 尝试精确匹配（可能失效）
            f"# {new_code_bare} {new_name}"
        )
    # 更通用：替换 H1 标题行（# XXXXX 任何内容）
    content = re.sub(
        r'^# (?:H\d{5}|\d{6}|H3\d{4}) .+$',
        f'# {new_code_bare} {new_name}',
        content, flags=re.MULTILINE
    )

    # 更新最后更新日期
    content = re.sub(r'^(最后更新日期:\s*)"?[^"\n]+"?', f'\\1"{TODAY}"', content, flags=re.MULTILINE)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

# ────────────────────────────────────────────────────────────
# 主流程
# ────────────────────────────────────────────────────────────
with open(WL_FILE, encoding="utf-8") as f:
    wl = json.load(f)

# ── Step 1：删除 10 只宽行业篮子 ──────────────────────────
print("=== Step 1：删除 10 只宽行业篮子 ===")
before_count = len(wl["indices"])
wl["indices"] = [idx for idx in wl["indices"] if idx["index_code"] not in REMOVE_CODES]
after_count = len(wl["indices"])
print(f"  JSON：{before_count} → {after_count}（删除 {before_count - after_count} 条）")

# 删除对应页面文件
remove_old_names = {old: old_name for old, old_name, *_ in
                    [(f"{c.split('.')[0]}.CSI", n) for c, n in [
                        ("932077", "中证全指能源行业指数"),
                        ("932078", "中证全指原材料行业指数"),
                        ("932079", "中证全指工业行业指数"),
                        ("932080", "中证全指可选消费行业指数"),
                        ("932081", "中证全指主要消费行业指数"),
                        ("932082", "中证全指医药卫生行业指数"),
                        ("932083", "中证全指金融行业指数"),
                        ("932084", "中证全指信息技术行业指数"),
                        ("932085", "中证全指通信服务行业指数"),
                        ("932086", "中证全指公用事业行业指数"),
                    ]]}

for code_raw, old_name in [
    ("932077", "中证全指能源行业指数"),
    ("932078", "中证全指原材料行业指数"),
    ("932079", "中证全指工业行业指数"),
    ("932080", "中证全指可选消费行业指数"),
    ("932081", "中证全指主要消费行业指数"),
    ("932082", "中证全指医药卫生行业指数"),
    ("932083", "中证全指金融行业指数"),
    ("932084", "中证全指信息技术行业指数"),
    ("932085", "中证全指通信服务行业指数"),
    ("932086", "中证全指公用事业行业指数"),
]:
    fn = find_page(code_raw, old_name)
    if fn:
        rel_path = os.path.join("05-A股指数", fn)
        if git("rm", rel_path):
            print(f"  git rm: {fn}")
        else:
            # 尝试直接删文件
            full_path = os.path.join(INDEX_DIR, fn)
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"  os.remove: {fn}")
    else:
        print(f"  ⚠️  未找到页面文件：{code_raw} {old_name}")

# ── Step 2：重命名 14 只行业指数 ──────────────────────────
print("\n=== Step 2：重命名 14 只行业指数 ===")
for entry in wl["indices"]:
    old_code = entry["index_code"]
    if old_code not in RENAME_DICT:
        continue
    new_code, new_name, sw_lvl = RENAME_DICT[old_code]
    old_bare = old_code.split(".")[0]
    new_bare = new_code.split(".")[0]

    # 更新 JSON
    entry["index_code"] = new_code
    entry["name"]        = new_name
    entry["last_updated"] = TODAY

    print(f"  {old_code} {entry.get('name', '')} → {new_code} {new_name}")

    # 找到旧页面文件
    old_entry_name = next((nm for _, nm, *_ in RENAME_MAP if _.count(new_code) > 0 or
                            next((nm2 for oc, nm2, nc, *_ in RENAME_MAP if nc == new_code), None) == nm), None)
    # 简单方法：遍历 RENAME_MAP 找匹配
    for oc, nm, nc, nn, _ in RENAME_MAP:
        if nc == new_code:
            old_entry_name = nm
            break

    old_fn = find_page(old_bare, old_entry_name)
    if old_fn:
        new_fn = f"{new_bare} {new_name}.md"
        old_rel = os.path.join("05-A股指数", old_fn)
        new_rel = os.path.join("05-A股指数", new_fn)
        if old_fn != new_fn:
            if git("mv", old_rel, new_rel):
                print(f"    git mv: {old_fn} → {new_fn}")
            else:
                print(f"    ⚠️  git mv 失败，跳过文件重命名")
                continue
        # 更新 frontmatter
        new_full = os.path.join(INDEX_DIR, new_fn)
        update_frontmatter(new_full, new_code, new_name, sw_lvl)
        print(f"    frontmatter 已更新")
    else:
        print(f"    ⚠️  未找到旧页面：{old_bare} / {old_entry_name}")

# ── Step 3：保存 JSON ─────────────────────────────────────
with open(WL_FILE, "w", encoding="utf-8") as f:
    json.dump(wl, f, ensure_ascii=False, indent=2)
print(f"\n✅ watchlist_index.json 已更新，共 {len(wl['indices'])} 条")
