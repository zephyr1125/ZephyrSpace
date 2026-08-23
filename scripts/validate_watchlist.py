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
    'cScore',
    'cycle_is_cyclical',
    'cycle_position',
    'dv_ttm',
    'mScore',
    'name',
    'next_earnings_date',
    'next_earnings_type',
    'target_price',
    'valuation_certainty',
    'watchlistLevel',
    'trackingStatus',
    'strategicCoreType',
    'lastFundamentalReviewDate',
    'lastRedFlagReviewDate'
}

REMOVED_FIELDS = {
    'position', 'position_role', 'source_etf', 'watch_reason',
    'current_price', 'price_date', 'price_bands', 'price_bands_basis',
    'price_bands_date', 'valuation_anchor', 'risk_flags',
    'prebuy_conclusion', 'targetPrice', 'buyPrice', 'maxWeight',
    'entry_trigger', 'tier', 'deep_rating', 'deep_score', 'mgmt_score',
    'last_updated', 'market', 'deep_analysis', 'mgmt_archive'
}

OPTIONAL_FIELDS = {
    # 已纳入三件套分析的最后一份财报（如 2026H1/2026Q1/2025FY/FY2026/Q3 FY2026）；
    # 可 null；NONE 档允许缺省。
    'lastEarningsIncorporated',
}

CANONICAL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

VALID_LEVELS = {'S_STRATEGIC', 'A_CORE', 'B_GROWTH', 'NONE'}
VALID_TRACKING_STATUSES = {'WATCHING', 'ARCHIVED'}
VALID_STRATEGIC_TYPES = {
    'COMPOUNDER', 'DEFENSIVE', 'GROWTH', 'POLICY_INFRA', 'CYCLICAL_QUALITY'
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

# board 有效值
VALID_BOARDS = {
    '深',
    '创',
    '沪',
    '科',
    '北',
    '港',
    '纽',
    '纳'
}


def validate_entry(entry, entry_idx=0, tier='unknown'):
    """验证单条 watchlist 条目"""
    errors = []
    warnings = []
    
    # 1. 必填字段检查
    for field in REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"  [字段缺失] {field}")
        elif entry[field] is None and field not in [
            'cycle_position', 'dv_ttm', 'next_earnings_date', 'next_earnings_type',
            'strategicCoreType', 'lastFundamentalReviewDate', 'lastRedFlagReviewDate',
            'target_price', 'valuation_certainty'
        ]:
            errors.append(f"  [字段为空] {field} 不允许为 null")

    extra_fields = set(entry) - CANONICAL_FIELDS
    if extra_fields:
        errors.append(f"  [额外字段] {sorted(extra_fields)}")

    # 2. 已废弃字段检查
    for field in REMOVED_FIELDS:
        if field in entry:
            errors.append(f"  [废弃字段] {field} 不应继续存在")

    # 3. 新估值字段检查
    level = entry.get('watchlistLevel')
    target_price = entry.get('target_price')
    certainty = entry.get('valuation_certainty')
    # NONE因质量门槛停止正式估值时，两个估值字段必须同时为空。
    valuation_paused = level == 'NONE' and target_price is None and certainty is None
    if level == 'NONE' and (target_price is None) != (certainty is None):
        errors.append("  [估值字段] NONE停止正式估值时 target_price 与 valuation_certainty 必须同时为 null")
    elif not valuation_paused and (not isinstance(target_price, (int, float)) or isinstance(target_price, bool) or target_price <= 0):
        errors.append(f"  [类型错误] target_price 必须是大于 0 的数字，当前为 {target_price!r}")

    if not valuation_paused and (not isinstance(certainty, (int, float)) or isinstance(certainty, bool)):
        errors.append(f"  [类型错误] valuation_certainty 必须是数字，当前为 {certainty!r}")
    elif not valuation_paused and not 0 <= certainty <= 1:
        errors.append(f"  [范围错误] valuation_certainty 必须在 0.00-1.00，当前为 {certainty!r}")
    elif not valuation_paused and round(certainty, 2) != certainty:
        errors.append(f"  [精度错误] valuation_certainty 最多保留两位小数，当前为 {certainty!r}")

    # 4. 三层分级与跟踪状态检查
    if level not in VALID_LEVELS:
        errors.append(f"  [等级错误] watchlistLevel = {level!r}")
    tracking_status = entry.get('trackingStatus')
    if tracking_status not in VALID_TRACKING_STATUSES:
        errors.append(f"  [跟踪状态错误] trackingStatus = {tracking_status!r}；HOLDING 由消费端动态生成")
    strategic_type = entry.get('strategicCoreType')
    if level == 'S_STRATEGIC' and strategic_type not in VALID_STRATEGIC_TYPES:
        errors.append(f"  [战略类型错误] S级必须填写 strategicCoreType，当前为 {strategic_type!r}")
    if level != 'S_STRATEGIC' and strategic_type is not None:
        errors.append("  [战略类型错误] 非S级 strategicCoreType 必须为 null")

    c_score = entry.get('cScore')
    m_score = entry.get('mScore')
    if isinstance(c_score, (int, float)) and isinstance(m_score, (int, float)):
        total = c_score + m_score
        if level == 'S_STRATEGIC' and not (
            total >= 170 and c_score >= 82 and m_score >= 82 and certainty >= 0.80
        ):
            errors.append("  [等级门槛] S级评分或估值确定性不达标")
        elif level == 'A_CORE' and not (total >= 160 and c_score >= 76 and m_score >= 76):
            errors.append("  [等级门槛] A级评分不达标")
        elif level == 'B_GROWTH' and not (total >= 150 and c_score >= 70 and m_score >= 70):
            errors.append("  [等级门槛] B级评分不达标")

    # 5. cycle_position 枚举检查
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
    
    # 6. next_earnings_type 枚举检查
    if entry.get('next_earnings_type') is not None and not isinstance(entry['next_earnings_type'], str):
        errors.append("  [类型错误] next_earnings_type 必须是字符串或 null")

    # 6b. lastEarningsIncorporated 类型检查（可 null；NONE 档允许缺省）
    lie = entry.get('lastEarningsIncorporated')
    if lie is not None and not isinstance(lie, str):
        errors.append("  [类型错误] lastEarningsIncorporated 必须是字符串或 null")
    
    # 7. board 格式检查
    if 'board' in entry:
        board = entry['board']
        if board is None:
            errors.append(f"  [格式错误] board = null （必须指定上市板块）")
        elif board not in VALID_BOARDS:
            errors.append(f"  [格式错误] board = '{board}' （无效值，应为 {VALID_BOARDS}）")
    
    # 8. code 格式检查
    if 'code' in entry:
        code = entry['code']
        if not isinstance(code, str) or not code.endswith(('.SH', '.SZ', '.HK', '.US')):
            errors.append(f"  [格式错误] code = '{code}' （必须带 .SH/.SZ/.HK/.US 后缀）")

    # 9. 日期格式检查
    for date_field in ['next_earnings_date', 'lastFundamentalReviewDate', 'lastRedFlagReviewDate']:
        if date_field in entry:
            date_val = entry[date_field]
            if date_val is None:
                continue
            if isinstance(date_val, str):
                if not _is_valid_date(date_val):
                    errors.append(f"  [日期格式] {date_field} = '{date_val}' （应为 YYYY-MM-DD）")
            else:
                errors.append(f"  [类型错误] {date_field} 必须是字符串或 null")

    # 10. next_earnings_date 过期检查（"next"财报日早于今天 = 财报已发布，字段未清场）
    ned = entry.get('next_earnings_date')
    if isinstance(ned, str) and _is_valid_date(ned):
        if datetime.strptime(ned, '%Y-%m-%d').date() < datetime.now().date():
            errors.append(
                f"  [日期过期] next_earnings_date = '{ned}' 已早于今天，财报应已发布；"
                f"请清为 null 或写入官方公告确认的下一期具体日期"
            )

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
    
    tier = data.get('watchlistLevel', data.get('tier', 'unknown'))
    entries = data['entries']

    if tier not in VALID_LEVELS:
        print(f"❌ 顶层 watchlistLevel 无效：{tier!r}")
        return False
    
    print(f"📊 基本信息：tier={tier}, entries={len(entries)}")
    
    total_errors = 0
    total_warnings = 0
    error_entries = []
    
    for idx, entry in enumerate(entries, 1):
        errors, warnings = validate_entry(entry, idx, tier)
        if entry.get('watchlistLevel') != tier:
            errors.append(f"  [等级不一致] entry={entry.get('watchlistLevel')!r}, file={tier!r}")
        
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
        data_dir / 'watchlist_strategic.json',
        data_dir / 'watchlist_core.json',
        data_dir / 'watchlist_growth.json',
        data_dir / 'watchlist_out_of_scope.json'
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
