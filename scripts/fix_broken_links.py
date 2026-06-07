"""
Fix broken AND imprecise wiki links caused by file renames.

Phase 1 (done): Fix truly broken links (deep analysis links missing scores)
Phase 2 (now): Fix imprecise links (management archive links that only work via prefix match)
               Make ALL links use exact filenames for robustness.
"""
import os
import re
import json
from pathlib import Path
from collections import defaultdict

VAULT = Path(r"E:\ObsidianVaults\ZephyrSpace")
DIRS_TO_SCAN = ["01-公司", "深度分析", "管理层档案"]
TARGET_DIRS = ["深度分析", "管理层档案"]

def find_md_files():
    """Find all .md files in the vault directories we care about"""
    files = {}
    for d in DIRS_TO_SCAN:
        dir_path = VAULT / d
        if dir_path.exists():
            for f in dir_path.rglob("*.md"):
                rel = str(f.relative_to(VAULT)).replace('\\', '/')
                files[rel] = f
    return files

def find_target_files():
    """Build a set of all files in target directories"""
    targets = {}
    for d in TARGET_DIRS:
        dir_path = VAULT / d
        if dir_path.exists():
            for f in dir_path.rglob("*.md"):
                rel = str(f.relative_to(VAULT)).replace('\\', '/')
                targets[rel] = f
    return targets

def scan_links(file_path):
    """Extract all [[wiki links]] from a file with line numbers"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return []

    pattern = r'\[\[([^\]|#]+)(?:[#][^\]|]*)?(?:\|[^\]]*)?\]\]'
    links = []
    for line_num, line in enumerate(content.split('\n'), 1):
        for m in re.finditer(pattern, line):
            target = m.group(1).strip()
            if target.endswith('.md'):
                target = target[:-3]
            links.append((target, line_num, m.group(0)))
    return links

def resolve_exact(target, all_files_set):
    """Check if target has an exact match"""
    target_lower = target.lower()
    for f_path in all_files_set:
        f_no_ext = f_path[:-3].lower() if f_path.endswith('.md') else f_path.lower()
        if f_no_ext == target_lower:
            return f_path
    return None

def resolve_prefix(target, all_files_set):
    """
    Try to resolve a wiki link target to an actual file using Obsidian prefix matching.
    Returns (matched_file_relpath, is_exact) or (None, False)
    """
    parts = target.rsplit('/', 1)
    if len(parts) == 2:
        target_dir, target_name = parts
    else:
        target_dir, target_name = '', target

    target_name_lower = target_name.lower()
    target_dir_lower = target_dir.lower()

    # First: exact match
    exact = resolve_exact(target, all_files_set)
    if exact:
        return (exact, True)

    # Second: prefix match in same directory
    best = None
    best_score = 0
    for f_path in all_files_set:
        f_parts = f_path.rsplit('/', 1)
        if len(f_parts) == 2:
            f_dir, f_name = f_parts
        else:
            f_dir, f_name = '', f_path

        f_name_no_ext = f_name[:-3] if f_name.endswith('.md') else f_name

        if f_dir.lower() != target_dir_lower:
            continue

        if not f_name_no_ext.lower().startswith(target_name_lower):
            continue

        prefix_len = len(target_name)
        extra_len = len(f_name_no_ext) - prefix_len
        score = prefix_len * 10 - extra_len

        if score > best_score:
            best_score = score
            best = f_path

    return (best, False)

def fuzzy_match(target_name, target_dir, target_files_dict, keyword):
    """
    Fuzzy match when Obsidian prefix match fails.
    For deep analysis files that now include scores.
    """
    company = target_name.split(keyword)[0].strip()
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', target_name)
    date = date_match.group(1) if date_match else None

    candidates = []
    for f_path, f_abs in target_files_dict.items():
        f_parts = f_path.rsplit('/', 1)
        if len(f_parts) == 2:
            f_dir, f_name = f_parts
        else:
            f_dir, f_name = '', f_path

        f_name_no_ext = f_name[:-3] if f_name.endswith('.md') else f_name

        if f_dir != target_dir:
            continue
        if keyword not in f_name_no_ext:
            continue
        if company not in f_name_no_ext:
            continue

        score = 0
        if date and date in f_name_no_ext:
            score += 100
        score -= len(f_name_no_ext) * 0.01
        candidates.append((score, f_path))

    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]
    return None

def main():
    all_files = find_md_files()
    all_files_set = set(all_files.keys())
    target_files_dict = find_target_files()

    truly_broken = []
    imprecise = []

    for file_rel, file_abs in sorted(all_files.items()):
        links = scan_links(file_abs)
        for target, line_num, full_link in links:
            # Only process links targeting TARGET_DIRS
            target_lower = target.lower()
            is_target = False
            for td in TARGET_DIRS:
                if target_lower.startswith(td.lower() + '/'):
                    is_target = True
                    break

            if not is_target:
                continue

            matched, is_exact = resolve_prefix(target, all_files_set)

            if matched and is_exact:
                continue  # Perfect, no fix needed

            if matched and not is_exact:
                # Works via prefix, but imprecise - fix to exact
                imprecise.append({
                    'file': file_rel,
                    'line': line_num,
                    'old_link': full_link,
                    'old_target': target,
                    'new_target': matched,
                })
                continue

            # Genuinely broken - try fuzzy match
            parts = target.rsplit('/', 1)
            if len(parts) == 2:
                t_dir, t_name = parts
            else:
                t_dir, t_name = '', target

            kw = None
            if '深度分析' in target:
                kw = ' 深度分析'
            elif '管理层档案' in target:
                kw = ' 管理层档案'

            if kw:
                fuzzy_result = fuzzy_match(t_name, t_dir, target_files_dict, kw)
                if fuzzy_result:
                    truly_broken.append({
                        'file': file_rel,
                        'line': line_num,
                        'old_link': full_link,
                        'old_target': target,
                        'new_target': fuzzy_result,
                    })
                else:
                    truly_broken.append({
                        'file': file_rel,
                        'line': line_num,
                        'old_link': full_link,
                        'old_target': target,
                        'new_target': None,
                    })

    return truly_broken, imprecise


def apply_fixes(items):
    """Apply fixes to files"""
    by_file = defaultdict(list)
    for item in items:
        if item['new_target']:
            by_file[item['file']].append(item)

    fixed_count = 0
    files_modified = set()

    for file_rel, file_items in sorted(by_file.items()):
        file_path = VAULT / file_rel
        if not file_path.exists():
            print(f"WARNING: File not found: {file_path}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')

        items_sorted = sorted(file_items, key=lambda x: -x['line'])
        modified = False

        for item in items_sorted:
            line_idx = item['line'] - 1
            if line_idx < 0 or line_idx >= len(lines):
                continue

            old_line = lines[line_idx]
            old_full = item['old_link']

            if old_full not in old_line:
                continue

            new_target = item['new_target']
            if new_target.endswith('.md'):
                new_target = new_target[:-3]

            alias_match = re.search(r'\[\[[^\]|]+\|([^\]]*)\]\]', old_full)
            if alias_match:
                alias = alias_match.group(1)
                new_link = f"[[{new_target}|{alias}]]"
            else:
                new_link = f"[[{new_target}]]"

            new_line = old_line.replace(old_full, new_link)
            lines[line_idx] = new_line
            modified = True
            fixed_count += 1

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            files_modified.add(file_rel)

    return fixed_count, files_modified


if __name__ == '__main__':
    import sys

    print("Scanning for broken and imprecise links...")
    truly_broken, imprecise = main()

    # Dedup
    def dedup(items):
        seen = set()
        result = []
        for b in items:
            key = (b['file'], b['line'], b['old_link'])
            if key not in seen:
                seen.add(key)
                result.append(b)
        return result

    truly_broken = dedup(truly_broken)
    imprecise = dedup(imprecise)

    broken_fixable = [b for b in truly_broken if b['new_target']]
    broken_unfixable = [b for b in truly_broken if not b['new_target']]

    # Write combined report
    all_items = truly_broken + imprecise
    txt_path = VAULT / "scripts" / "broken_links_report.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"Link Fix Report - Phase 1+2\n")
        f.write(f"{'='*60}\n")
        f.write(f"Truly Broken (missing score in filename): {len(truly_broken)}\n")
        f.write(f"  Fixable: {len(broken_fixable)}\n")
        f.write(f"  Unfixable: {len(broken_unfixable)}\n")
        f.write(f"Imprecise (prefix-match only, need exact): {len(imprecise)}\n")
        f.write(f"Total to fix: {len(broken_fixable) + len(imprecise)}\n\n")

        f.write("="*60 + "\n")
        f.write("TRULY BROKEN LINKS\n")
        f.write("="*60 + "\n")
        for item in truly_broken:
            status = "[FIXABLE]" if item['new_target'] else "[UNMATCHED]"
            f.write(f"{status} {item['file']}:{item['line']}\n")
            f.write(f"  BROKEN: {item['old_link']}\n")
            if item['new_target']:
                f.write(f"  FIX TO: [[{item['new_target']}]]\n")
            else:
                f.write(f"  NO MATCH FOUND\n")
            f.write("\n")

        f.write("="*60 + "\n")
        f.write("IMPRECISE LINKS (make exact)\n")
        f.write("="*60 + "\n")
        for item in imprecise:
            f.write(f"[IMPRECISE] {item['file']}:{item['line']}\n")
            f.write(f"  CURRENT: {item['old_link']}\n")
            f.write(f"  EXACT:   [[{item['new_target']}]]\n")
            f.write("\n")

    print(f"Truly broken: {len(truly_broken)} (fixable: {len(broken_fixable)}, unfixable: {len(broken_unfixable)})")
    print(f"Imprecise (prefix-only): {len(imprecise)}")
    print(f"Report: {txt_path}")

    all_fixable = broken_fixable + imprecise

    if '--fix' in sys.argv and all_fixable:
        print("\nApplying fixes for both broken and imprecise links...")
        count, files = apply_fixes(all_fixable)
        print(f"Fixed {count} links in {len(files)} files")
    elif all_fixable:
        print(f"\nRun with --fix to apply all {len(all_fixable)} fixes:")
        print(f"  python scripts/fix_broken_links.py --fix")
