# Watchlist 数据结构规范

## 总体设计

Watchlist 由两个分层 JSON 文件组成，按档位分类：
- **watchlist_core.json** - CORE 档（强护城河底仓）
- **watchlist_growth.json** - GROWTH 档（成长机会）

## 统一必填字段模板

所有公司条目必须包含以下16个必填字段（按字母顺序）：

| # | 字段名 | 类型 | 含义 | 示例 | 备注 |
|---|---|---|---|---|---|
| 1 | `board` | string | 上市板块 | "深"、"沪"、"科"、"北" | ⚠️**严格格式**：仅允许单字符 "深"/"沪"/"科"/"北"/"港"/"美"/"纽"/"纳"。禁止 "科创板"、"沪深"、"创" 等非标格式 |
| 2 | `code` | string | 股票代码 | "300573.SZ" | 格式：6位纯数字+后缀(.SZ/.SH/.HK/.US) |
| 3 | `current_price` | number | 当前股价 | 69.45 | 浮点数，单位：人民币 |
| 4 | `cycle_is_cyclical` | boolean | 是否周期股 | false | true=周期股，false=非周期股 |
| 5 | `cycle_position` | string / null | 周期位置 | "底部" | **[NEW]**必填。枚举值：底部/复苏早期/复苏中期/景气高峰/收缩期/出清期。非周期股传 null |
| 6 | `dv_ttm` | number / null | 股息率TTM | 2.1 | 百分比后的数值（如 2.1 代表2.1%）；不分红传 null |
| 7 | `name` | string | 公司名称 | "兴齐眼药" | 中文全称 |
| 8 | `next_earnings_date` | string | 下期财报发布日期 | "2026-08-31" | 格式：YYYY-MM-DD |
| 9 | `next_earnings_type` | string | 下期财报类型 | "半年报" | 枚举值：一季报/半年报/三季报/年报 |
| 10 | `position_role` | string | 投资定位 | "高ROE低PE核心档标的" | 用一句话描述在portfolio中的角色 |
| 11 | `prebuy_conclusion` | string | 分析结论 | "眼科制药高质量成长，ROE39%，PE历史最低" | 不超过100字 |
| 12 | `price_bands` | array[number] | 价格区间 | [90, 65, 40] | ⚠️**严格格式**：必须是 **array[number]** 类型，不允许对象格式 `{"buy": {...}}`。排列顺序 [买入价, 持有价, 卖出价]（从高到低）。null 表示待补充 |
| 13 | `price_date` | string | 价格日期 | "2026-04-30" | 格式：YYYY-MM-DD，记录当前价格何时取得 |
| 14 | `risk_flags` | array[string] | 风险项 | ["阿托品集中度风险", "医保覆盖变动"] | 关键风险列表，3-5项 |
| 15 | `source_etf` | string | 数据来源 | "direct" / "980081" | "direct"=直接PreBuy，否则填入相关ETF代码 |
| 16 | `valuation_anchor` | string | 估值锚点 | "PE 22.6x (历史最低分位0%)" | 核心估值指标+历史参考 |
| 17 | `watch_reason` | string | 跟踪理由 | "ROE39%+PE低估值+阿托品放量" | 简洁关键词，3-5个要点 |

## 已废弃的 RADAR 字段（历史说明）

> RADAR 档已于2026-07-15删除。下列字段仅用于理解历史数据，不得写入当前 core/growth 文件。

RADAR 档可以（但非必须）包含以下额外字段，用于更深度的跟踪：

| 字段名 | 类型 | 含义 | 备注 |
|---|---|---|---|
| `added_date` | string | 添加到RADAR日期 | 格式：YYYY-MM-DD |
| `entry_trigger` | string | 入场触发条件 | 描述何时可升档到CORE/GROWTH |
| `industry` | string | 一级行业 | 如"医药生物" |
| `sub_sector` | string | 细分行业 | 如"医疗器械" |
| `market_cap_bn` | number | 市值（亿元） | 整数 |
| `pe_ttm` | number | PE估值 | 最新PE倍数 |
| `pb` | number | PB估值 | 最新PB倍数 |
| `roe_latest` | number | 最新ROE | 百分比后的数值 |
| `roe_year` | number | 年度ROE | 百分比后的数值 |
| `policy_score` | number | 政策支持度 | 1-10分 |
| `notes` | string | 补充备注 | 自由文本 |

## 文件顶层结构

```json
{
  "version": 1,
  "tier": "core|growth",
  "updated_at": "2026-05-03T10:56:21Z",
  "entries": [
    { /* 公司条目，必须包含所有16个必填字段 */ }
  ]
}
```

## 规范要求

### 1. 必填字段验证

写入任何watchlist文件前，**必须确保**：
- [ ] 所有16个必填字段都存在
- [ ] 没有字段为 undefined（null 只在指定字段允许）
- [ ] 字段类型与规范一致
- [ ] code 格式为 `XXXXXX.XX` 格式

### 2. cycle_position 枚举值规范

**关键规则**：`cycle_position` 必须是**单一精确枚举值**，不允许：
- ❌ 双值组合（如"底部/复苏早期"）
- ❌ 过渡描述（如"景气高峰→接近收缩期"）
- ❌ 自由文本（如"低位运行"）
- ✅ 精确单值（如"底部" 或 null）

```python
# 验证逻辑
valid_positions = {"底部", "复苏早期", "复苏中期", "景气高峰", "收缩期", "出清期", None}
assert entry["cycle_position"] in valid_positions, f"Invalid position: {entry['cycle_position']}"
```

### 3. price_bands 排序规范

必须从高到低排列 `[buy_high, hold_mid, sell_low]`：
```python
# 示例
"price_bands": [120, 75, 40]  # ✓ 正确
"price_bands": [40, 75, 120]  # ✗ 错误
```

### 4. next_earnings_* 字段维护规范

- `next_earnings_date` 必须是**年末日期**（MM-DD 部分）对应财报类型：
  - 一季报 → YYYY-03-31
  - 半年报 → YYYY-06-30
  - 三季报 → YYYY-09-30
  - 年报 → YYYY-12-31

- 不允许使用已过期的 `next_earnings_time` 字段（已废弃）

### 5. dv_ttm 和 roe 字段规范

- 数值格式为百分比后的数值（如 2.1 代表 2.1%）
- 不分红的公司 dv_ttm 传 null（不传空字符串）
- ROE 为负时仍需正常填写数值（不传特殊值）

### 6. board 字段严格格式规范 ⭐

**必须是单字符枚举值，不允许全名或组合值**：

| board 值 | 含义 | 接受格式 | ❌ 不接受的格式 |
|---------|------|--------|---------|
| `"深"` | 深交所主板 | "深" | "深圳"、"深交"、"创" |
| `"沪"` | 上交所主板 | "沪" | "上海"、"沪交"、"沪深" |
| `"科"` | 科创板 | "科" | "科创"、"科创板" |
| `"北"` | 北交所 | "北" | "北京"、"北交" |
| `"港"` | 港交所 | "港" | "香港"、"HK" |
| `"美"` | 美股 | "美" | "纳斯达克"、"NYSE" |
| `"纽"` | 纽交所 | "纽" | "纽交" |
| `"纳"` | 纳斯达克 | "纳" | "纳指" |

**常见错误修正**：
- ❌ "沪深" → ✅ 根据 code 后缀判断：".SZ" = "深"，".SH" = "沪"
- ❌ "科创板" → ✅ "科"
- ❌ "创" → ✅ "科"

### 7. price_bands 字段严格格式规范 ⭐

**必须是数值数组，严禁对象格式**：

```python
# ❌ 错误格式（对象）
"price_bands": {
    "buy": {"price": 90, "desc": "分批建仓"},
    "hold": {"price": 65, "desc": "当前价"},
    "sell": {"price": 40, "desc": "止盈"}
}

# ✅ 正确格式（数组）
"price_bands": [90, 65, 40]

# ✅ 允许 null（待补充）
"price_bands": null
```

**数值排序必须从高到低** `[buy_high, hold_mid, sell_low]`：
```python
[120, 75, 40]   # ✓ 正确
[40, 75, 120]   # ✗ 错误排序
```

## 迁移计划

### Phase 1：修复 GROWTH（立即）
- [ ] 为所有 GROWTH 条目补充 `cycle_position` 字段
- [ ] 非周期股填 null，周期股填对应周期阶段

### Phase 2：删除 RADAR（已完成）
- [x] 删除 `watchlist_radar.json`
- [x] 当前有效档位收敛为 core/growth

### Phase 3：代码审查工具（本周末）
- [ ] 编写 Python 验证脚本 `validate_watchlist.py`
- [ ] 集成到 `sync_watchlist.ps1`，同步时自动检查
- [ ] 任何不符合规范的条目拒绝写入

## 未来写入规范

所有后续写入 watchlist 的 Agent 必须：
1. 使用 `WATCHLIST_SCHEMA.md` 作为参考
2. 在提交前运行本地验证脚本
3. 不允许自由添加新字段（需经主 Agent 审核）
4. 任何大于 1 个字段的结构调整需提交 Issue 讨论

## 检查清单

写入前必须 Pass 的检查项：

```python
def validate_watchlist_entry(entry, tier='core'):
    errors = []
    
    # 必填字段检查
    required_fields = {
        'board', 'code', 'current_price', 'cycle_is_cyclical', 'cycle_position',
        'dv_ttm', 'name', 'next_earnings_date', 'next_earnings_type', 
        'position_role', 'prebuy_conclusion', 'price_bands', 'price_date',
        'risk_flags', 'source_etf', 'valuation_anchor', 'watch_reason'
    }
    
    for field in required_fields:
        if field not in entry:
            errors.append(f"Missing required field: {field}")
    
    # cycle_position 枚举检查
    if entry.get('cycle_position') is not None:
        valid = {"底部", "复苏早期", "复苏中期", "景气高峰", "收缩期", "出清期"}
        if entry['cycle_position'] not in valid:
            errors.append(f"Invalid cycle_position: {entry['cycle_position']}")
    
    # price_bands 排序检查
    if isinstance(entry.get('price_bands'), list) and len(entry['price_bands']) == 3:
        if not (entry['price_bands'][0] > entry['price_bands'][1] > entry['price_bands'][2]):
            errors.append(f"price_bands not in descending order: {entry['price_bands']}")
    
    return errors
```

---

**最后更新**：2026-05-03  
**维护者**：Agent  
**版本**：1.0
