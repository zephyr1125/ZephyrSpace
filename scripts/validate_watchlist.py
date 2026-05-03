#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watchlist 数据结构验证脚本
用于检查 watchlist JSON 文件是否符合规范

使用方式：
  python validate_watchlist.py
  python validate_watchlist.py --fix  # 自动修复可修复的问题
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 定义必填字段
REQUIRED_FIELDS = {
    'board',
    'code',
    'current_price',
    'cycle_is_cyclical',
    'cycle_position',
    'dv_ttm',
    'name',
    'next_earnings_date',
    'next_earnings_type',
    'position_role',
    'prebuy_conclusion',
    'price_bands',
    'price_date',
    'risk_flags',
    'source_etf',
    'valuation_anchor',
    'watch_reason'
}

# cycle_position 有效值
VALID_CYCLE_POSITIONS = {
    '底部',
    '复苏早期',
    '复苏中期',
    '景气高峰',
    '收缩期',
    '出清期',
    None  # 非周期股可为 null
}

# next_earnings_type 有效值
VALID_EARNINGS_TYPES = {
    '一季报',
    '半年报',
    '三季报',
    '年报'
}


def validate_entry(entry, entry_idx=0, tier='unknown'):
    """验证单条 watchlist 条目"""
    errors = []
    warnings = []
    
    # 1. 必填字段检查
    for field in REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"  [字段缺失] {field}")
        elif entry[field] is None and field not in ['cycle_position', 'dv_ttm']:
            errors.append(f"  [字段为空] {field} 不允许为 null")
    
    # 2. cycle_position 枚举检查
    if 'cycle_position' in entry:
        val = entry['cycle_position']
        if val is not None and val not in VALID_CYCLE_POSITIONS:
            # 检查是否是双值组合或过渡描述
            if '/' in str(val) or '→' in str(val) or '接近' in str(val):
                errors.append(f"  [枚举错误] cycle_position = '{val}' （禁止组合值或过渡描述！）")
            elif val == '待评估':
                warnings.append(f"  [需补充] cycle_position = '{val}' （需确定具体周期位置）")
            else:
                errors.append(f"  [枚举错误] cycle_position = '{val}' （无效枚举值）")
    
    # 3. next_earnings_type 枚举检查
    if 'next_earnings_type' in entry:
        if entry['next_earnings_type'] not in VALID_EARNINGS_TYPES:
            errors.append(f"  [枚举错误] next_earnings_type = '{entry['next_earnings_type']}'")
    
    # 4. price_bands 排序检查
    if 'price_bands' in entry:
        pb = entry['price_bands']
        if isinstance(pb, list):
            if len(pb) != 3:
                errors.append(f"  [格式错误] price_bands 应为3个元素，但有 {len(pb)} 个")
            elif not (pb[0] > pb[1] > pb[2]):
                errors.append(f"  [排序错误] price_bands {pb} 不是降序 (应为 [买入高, 持有中, 卖出低])")
        else:
            errors.append(f"  [类型错误] price_bands 应为数组，但是 {type(pb)}")
    
    # 5. code 格式检查
    if 'code' in entry:
        code = entry['code']
        if not isinstance(code, str) or '.' not in code:
            errors.append(f"  [格式错误] code = '{code}' （应为 XXXXXX.XX 格式）")
    
    # 6. risk_flags 检查
    if 'risk_flags' in entry:
        rf = entry['risk_flags']
        if not isinstance(rf, list):
            errors.append(f"  [类型错误] risk_flags 应为数组，但是 {type(rf)}")
        elif len(rf) == 0:
            warnings.append(f"  [缺内容] risk_flags 为空数组")
    
    # 7. 日期格式检查
    for date_field in ['price_date', 'next_earnings_date']:
        if date_field in entry:
            date_val = entry[date_field]
            if isinstance(date_val, str):
                if not _is_valid_date(date_val):
                    errors.append(f"  [日期格式] {date_field} = '{date_val}' （应为 YYYY-MM-DD）")
    
    return errors, warnings


def _is_valid_date(date_str):
    """检查日期格式是否为 YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_file(filepath):
    """验证整个 watchlist 文件"""
    print(f"\n{'='*80}")
    print(f"📋 验证文件：{os.path.basename(filepath)}")
    print(f"{'='*80}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 文件加载失败：{e}")
        return False
    
    # 检查顶层结构
    if 'entries' not in data:
        print(f"❌ 缺失顶层 'entries' 字段")
        return False
    
    tier = data.get('tier', 'unknown')
    entries = data['entries']
    
    print(f"📊 基本信息：tier={tier}, entries={len(entries)}")
    
    total_errors = 0
    total_warnings = 0
    error_entries = []
    
    for idx, entry in enumerate(entries, 1):
        errors, warnings = validate_entry(entry, idx, tier)
        
        if errors or warnings:
            name = entry.get('name', f'Entry {idx}')
            code = entry.get('code', 'N/A')
            
            if errors:
                total_errors += len(errors)
                print(f"\n❌ [{idx}] {name} ({code})")
                for error in errors:
                    print(error)
                error_entries.append((idx, name, code, errors))
            
            if warnings:
                total_warnings += len(warnings)
                print(f"\n⚠️  [{idx}] {name} ({code})")
                for warning in warnings:
                    print(warning)
    
    # 总结
    print(f"\n{'-'*80}")
    print(f"✅ 总计 {len(entries)} 条")
    print(f"❌ 错误 {total_errors} 个")
    print(f"⚠️  警告 {total_warnings} 个")
    print(f"{'-'*80}")
    
    return total_errors == 0


def main():
    data_dir = Path(__file__).parent.parent / 'data'
    
    files_to_check = [
        data_dir / 'watchlist_core.json',
        data_dir / 'watchlist_growth.json',
        data_dir / 'watchlist_radar.json'
    ]
    
    all_passed = True
    for filepath in files_to_check:
        if filepath.exists():
            if not validate_file(str(filepath)):
                all_passed = False
        else:
            print(f"⚠️  文件不存在：{filepath}")
    
    print(f"\n{'='*80}")
    if all_passed:
        print("✅ 所有文件都通过验证！")
    else:
        print("❌ 发现结构问题，请按上述错误修复")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
