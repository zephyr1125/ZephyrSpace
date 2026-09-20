# 估值：通用约束与计算核心规则：watchlist-closeout

由本模块 SKILL.md 按条件路由；不要求所有角色每次通读。来源优先级、调度、修复轮次、提交和回写权限服从统一 SOP。

<!-- migrated:part-11:start -->
## 第 4 步：Watchlist 联动（强制步骤）

估值完成且重要问题关闭后执行以下步骤。完整三件套仅由主对话在三份报告、公司页和索引全部验收后统一执行；子Agent只提交建议字段，准入退出或研究未完成不得写入/同步。

### 4.1 检索标的

```bash
# 用 grep 在所有 watchlist JSON 中检索股票代码或名称
grep -l "代码\|公司名" data/watchlist_*.json
```

检索范围：
- `data/watchlist_core.json`
- `data/watchlist_growth.json`
- `data/watchlist_index.json`

检索关键词：股票代码（如 `600406.SH`）和公司简称（如 `国电南瑞`）。

### 4.2 更新精简估值字段

若命中，用 Read 工具定位到该条目，然后 Edit 更新以下字段：

```json
"target_price": <最终加权合理估值>,
"valuation_certainty": <0.00-1.00，最多两位小数>
```

`target_price` 必须取报告最终结论中的加权合理估值，不得取买入价、乐观情景价或区间上沿。Watchlist 不再保存实时价格、价格带、估值锚和风险摘要。

> ⚠️ **估值分析不修改 `next_earnings_date` / `next_earnings_type`**。这两个字段由公司 PreBuy 分析或专门的财报日期扫描流程维护。若发现该条目日期为 `null`，在告知用户的总结中提醒"财报日期待确认"即可，不要自行估算填入。
>
> 🔴 **唯一例外——财报消费后清场**：当本次估值是基于**刚发布的财报**（半年报/中期业绩/季报/年报，即该条目的 `next_earnings_date` 已过期）时，收尾阶段必须把过期的 `next_earnings_date` 清为 `null`，并把 `next_earnings_type` 改为下一期报告类型（A股→`三季报`/`年报`，港交所→`第三季度业绩`/`末期业绩`）。只有官方公告确认的下一期具体日期才允许写入非 `null` 值，否则一律 `null`。此"清场"动作随 `sync_watchlist.ps1` 一并同步到 Finance 项目。
>
> 🆕 **同步更新 `lastEarningsIncorporated`**：清场的同时，把该条目的 `lastEarningsIncorporated` 更新为本次估值所纳入的那份财报期（A股半年报→`2026H1`、一季报→`2026Q1`、年报→`2025FY`；美股自然季度→`2026Q2`；美股非自然财年→`FY2026`/`Q3 FY2026` 等）。规范值见 `data/WATCHLIST_SCHEMA.md`。此字段用于筛查「已发布财报但尚未更新分析」的公司。

<!-- migrated:part-11:end -->

<!-- migrated:part-13:start -->
### 4.3 同步到 Finance 项目

```powershell
.\scripts\sync_watchlist.ps1
```

### 4.4 告知用户

总结更新了哪些标的、在哪个 watchlist 中、新的 `target_price`、`valuation_certainty` 和自动计算的 `buy_price`。

---

<!-- migrated:part-13:end -->
