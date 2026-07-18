# Watchlist 数据结构规范

## 总体设计

Watchlist 由四个研究等级文件组成：

- `watchlist_strategic.json`：战略核心 `S_STRATEGIC`
- `watchlist_core.json`：核心关注 `A_CORE`
- `watchlist_growth.json`：成长关注 `B_GROWTH`
- `watchlist_out_of_scope.json`：未入池 `NONE`，保留研究和持仓跟踪入口

旧版 Watchlist 与 Radar 均已废弃。公司研究、风险描述、当前行情和价格带保留在公司页及估值报告中，不再复制进 Watchlist。

## 条目规范字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 公司简称，与公司页标题一致 |
| `code` | string | 股票代码，包含市场后缀 |
| `board` | string | 上市板块简称 |
| `target_price` | number | 最新估值报告中的加权合理估值；币种与股票交易币种一致 |
| `valuation_certainty` | number | `target_price` 的可靠程度，范围 `0.00–1.00`，最多两位小数 |
| `dv_ttm` | number / null | 股息率 TTM，单位 `%` |
| `next_earnings_date` | string / null | 下一期财报日期，格式 `YYYY-MM-DD`。**必须来自公司官方公告确认的真实日期**；未确认时务必写 `null`。禁止用交易所法定截止日（08-31/04-30/10-31）或历史推算值填充 |
| `next_earnings_type` | string / null | 下一期财报类型。`next_earnings_date` 为 `null` 时此字段也必须为 `null` |
| `cycle_is_cyclical` | boolean | 是否为周期股 |
| `cycle_position` | string / null | 周期位置；非周期股可为 `null` |
| `cScore` | number | 公司深度分析评分 |
| `mScore` | number | 管理层评分 |
| `watchlistLevel` | string | `S_STRATEGIC` / `A_CORE` / `B_GROWTH` / `NONE` |
| `trackingStatus` | string | 静态值仅允许 `WATCHING` / `ARCHIVED`；消费端发现真实持仓时动态输出 `HOLDING` |
| `strategicCoreType` | string / null | S级战略类型，非S级必须为 `null` |
| `lastFundamentalReviewDate` | string / null | 最近完整基本面复核日期 |
| `lastRedFlagReviewDate` | string / null | 最近治理、诉讼、审计和管理层红线复核日期 |

每条 entry 必须且只能包含以上17个字段。允许为空的字段必须显式填写 `null`，不得省略。

## 三层分级规则

按红线、S、A、B、NONE的顺序判断，同一公司只进入最高满足等级：

- `S_STRATEGIC`：总分≥170，两项均≥82，`valuation_certainty`≥0.80，现金流质量与盈利稳定性通过，且无重大红线。
- `A_CORE`：总分≥160，两项均≥80。
- `B_GROWTH`：总分≥150，两项均≥75。
- `NONE`：不满足以上条件或触发重大治理、财务异常、投资逻辑证伪红线。

阈值均包含边界。关键字段缺失时不得推断或补高分。

## 战略核心类型

`strategicCoreType` 仅用于S级公司的投资功能分类，不改变等级：

- `COMPOUNDER`：稳定复利型
- `DEFENSIVE`：防御现金流型
- `GROWTH`：高成长型
- `POLICY_INFRA`：政策基础设施型
- `CYCLICAL_QUALITY`：优质周期型

## 研究有效期

- S级红线复核超过90天：消费端显示“待复核”。
- S级红线复核超过180天：消费端显示“S级—资料过期”。
- 财报、管理层变动、重大诉讼、监管调查或资本运作发生后，应立即重新复核。
- 资料过期不自动修改研究等级，但不得显示为无条件S级。

## 跟踪状态

`watchlistLevel` 与 `trackingStatus` 相互独立。静态配置记录研究跟踪意图；Finance 后端根据核算表实时持仓覆盖为 `HOLDING`。因此，`NONE + HOLDING` 是合法且必须支持的组合。

## 已移除字段

以下字段不得再写入 `core` 或 `growth`：

- `position`
- `position_role`
- `source_etf`
- `watch_reason`
- `current_price`
- `price_date`
- `price_bands`
- `price_bands_basis`
- `price_bands_date`
- `valuation_anchor`
- `risk_flags`
- `prebuy_conclusion`
- `targetPrice`（由 `target_price` 取代）
- `buyPrice`
- `maxWeight`
- `entry_trigger`
- entry 级 `tier`
- `deep_rating`
- `deep_score`
- `mgmt_score`
- entry 级 `last_updated`
- `market`（由标准化后的 `code` 推导）
- `deep_analysis`
- `mgmt_archive`

## 估值字段规则

1. `target_price` 必须直接取最新估值报告的最终“加权合理估值”，不得取买入价、乐观情景价或价格区间上沿。
2. 同一条目只允许一个有效目标价字段，即 `target_price`。
3. `target_price` 必须为大于 `0` 的数字。
4. `valuation_certainty` 衡量目标价误差范围，不评价公司或管理层质量，不得与 `cScore`、`mScore` 重复计分。
5. 认定时依次检查盈利和现金流可预测性、商业模式和资本强度、资产负债表和融资需求、估值方法收敛度，以及周期、客户、监管、技术、商品、临床和资本开支等尾部风险。
6. 参考区间：`0.80–0.90` 极高，`0.70–0.79` 较高，`0.60–0.69` 中等，`0.50–0.59` 中低，`0.40–0.49` 较低，低于 `0.40` 很低。
7. 高质量公司也可能估值确定性低；低增长但现金流稳定的公司可能估值确定性高。不得因偏好公司而上调。
8. 财报、商业模式、资本结构或主要估值假设变化时，必须重新评估。

买入价由使用方自动计算，不写入 Watchlist：

```text
buy_price = target_price × (0.68 + 0.14 × valuation_certainty)
```

## 周期字段规则

`cycle_position` 的有效值为：`底部`、`复苏早期`、`复苏中期`、`景气高峰`、`收缩期`、`出清期` 或 `null`。禁止组合值和自由文本。

## 验证

修改后运行：

```powershell
$env:PYTHONUTF8='1'
python .\scripts\validate_watchlist.py
```

验证通过后再运行 `scripts/sync_watchlist.ps1`。

---

**最后更新**：2026-07-17
**Schema 版本**：23
