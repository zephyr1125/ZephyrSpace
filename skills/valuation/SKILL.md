---
name: valuation
description: >-
  对指定公司执行多方法估值分析（PE分位/PEG/EV-EBITDA/FCF Yield/逆向DCF/SOTP等），
  完成后自动检索 watchlist JSON 文件，若标的存在则更新 price_bands、current_price、valuation_anchor，
  并同步到外部 Finance 项目。
  触发词：估值、用合适算法估值、给XX估值、valuation。
  适用市场：A股、港股、美股。
---

# 估值分析（多方法 + Watchlist 联动）

## 概览

这个技能执行「公司估值分析 → watchlist 更新 → Finance 项目同步」的完整闭环。

核心原则：
- **多方法交叉验证**：至少使用 4-6 种估值方法，加权得出合理价中枢，不依赖单一方法
- **方法选择按公司特征定**：成长型用 PEG + 逆向 DCF，成熟型用 PE 分位 + DDM，制造型用 EV/EBITDA + FCF Yield
- **分析完成后自动联动 watchlist**：检索所有 watchlist JSON，命中则更新 price_bands

---

## 第 0 步：数据拉取

执行估值前必须获取以下数据：

### 必须数据
1. **行情**：最新收盘价、市值、总股本（tushare `daily` + `daily_basic`）
2. **财务**：近 5 年收入/净利/毛利率/ROE/EPS/OCF/FCFF/EBITDA（tushare `fina_indicator` + `income` + `cashflow`）
3. **一致预期**：2026E/2027E EPS 和净利润（web_search 券商一致预期）
4. **历史估值区间**：3Y PE 分位 P20/P50/P80（理杏仁 API 或已有分析文件）

### 可选数据（用于交叉验证）
5. **分红**：近 5 年 DPS + 分红率（tushare `dividend`）
6. **资产负债表**：有息负债/净现金/商誉（已有深度分析或 tushare `balancesheet`）

### 已有资料利用
- 先 `Glob **/*公司名*` 检查 vault 中是否有深度分析、公司页、管理层档案
- 深度分析中的财务数据可直接复用，但行情和估值分位必须拉最新
- 公司页中如有 PE 分位锚点数据，优先使用

---

## 第 1 步：方法选择矩阵

根据公司特征，从以下方法中选择最合适的 4-6 种：

| 方法 | 最适用 | 需要数据 | 权重建议 |
|---|---|---|---|
| **PE 历史分位** | 盈利稳定、有 3Y+ 交易历史的公司 | EPS + 3Y PE P20/P50/P80 | 20-30% |
| **PEG** | 增速 10%+ 的成长型公司 | 2026E EPS + 增速 | 10-20% |
| **EV/EBITDA** | 有息负债显著的制造/工业公司 | EBITDA + 净债务 | 10-15% |
| **标准化 FCF Yield** | 现金流强且稳定的公司 | OCF - 维护性 capex | 20-25% |
| **DDM（股利折现）** | 高分红成熟公司（分红率>40%） | DPS + g + r | 10-15% |
| **逆向 DCF** | 所有公司，用于验证隐含预期 | EPS + 折现率 | 15-20% |
| **SOTP 分部估值** | 多元化/跨行业/有期权价值的公司 | 分部收入/利润 | 10-15% |
| **P/B-ROE** | 金融/高杠杆/周期性公司 | ROE + PB + 权益成本 | 底线验证 |

### PEG 的增速选取
- 优先使用 **2025A→2026E 一致预期增速**
- 若增速 >30%，同时用 **3Y 历史 CAGR**（去基数效应）做交叉校验
- 终端增长率 g = ROE × (1-payout)，用于 DDM 和逆向 DCF

### 逆向 DCF 标准参数
- 折现率：A 股 9-10%，港股 10-11%，美股 9-10%
- 成长期：10 年
- 终值 PE：15x（一般制造业）、18x（品牌/龙头）、20x（顶级护城河）
- 输出：「当前价格隐含 10 年 EPS CAGR ≈ X%」

---

## 第 2 步：执行多方法估值

对每个选中的方法，输出：

```
### 方法 N：XXX

| 输入参数 | 值 |
|---|---|
| ... | ... |

| 情景 | 合理价 |
|---|---|
| 保守 | XXX |
| 基准 | XXX |
| 乐观 | XXX |

**结论：合理价 ≈ XXX（+/- XX% vs 现价）**
```

关键纪律：
- **所有计算参数必须显式列出**（EPS、PE、g、r、FCF 等），方便审核
- **逆向 DCF 的 g 是"市场在定价什么"，不是你预期的 g**——要把两者分开
- PE 分位法必须以一致预期 EPS（2026E）为主锚，历史 EPS 为辅助
- FCF 必须区分"报表 FCF"和"标准化 FCF"（去除扩张性 capex、正常化 WC 波动）

---

## 第 3 步：综合加权 + 价格区间

### 加权合理价
对每个方法赋权重（按方法选择矩阵），计算加权合理价。

### 价格区间锚定
输出四级价格区间（格式参考）：

```
🔴 追高区    >XXX 元    (PE >XXx / 触发条件)
🟡 中性区    XXX-XXX    (PE XX-XXx)
🟢 较好区    XXX-XXX    (PE XX-XXx，推荐建仓)
🟢🟢 低估区  <XXX       (PE <XXx，安全边际充足)
```

### 敏感性分析
以 2027E EPS 为基准，输出 PE × EPS 矩阵。

---

## 第 4 步：Watchlist 联动（强制步骤）

估值报告输出完成后，**立即执行**以下步骤：

### 4.1 检索标的

```bash
# 用 grep 在所有 watchlist JSON 中检索股票代码或名称
grep -l "代码\|公司名" data/watchlist_*.json
```

检索范围：
- `data/watchlist_core.json`
- `data/watchlist_growth.json`
- `data/watchlist_radar.json`
- `data/watchlist_index.json`

检索关键词：股票代码（如 `600406.SH`）和公司简称（如 `国电南瑞`）。

### 4.2 更新 price_bands

若命中，用 Read 工具定位到该条目，然后 Edit 更新以下字段：

```json
"current_price": <最新收盘价>,
"price_date": "<YYYY-MM-DD>",
"price_bands": [
  <追高区边界>,
  <中性区上界>,
  <低估区下界>
],
"valuation_anchor": "<PE TTM XXx（3Y P50≈XXx），2026E EPS≈XX→Fwd PE XXx。PEG=XX，FCF Yield XX%，逆向DCF隐含g≈XX%。多方法加权合理价≈XX元(±XX%)。[估值更新YYYY-MM-DD]>"
```

**price_bands 格式约定**：
- `[0]`：追高区下界（PE >此值不宜追高）
- `[1]`：中性区上界（合理偏贵 vs 合理偏低的分界）
- `[2]`：低估区上界（PE <此值有安全边际）

### 4.3 同步到 Finance 项目

```powershell
.\scripts\sync_watchlist.ps1
```

### 4.4 告知用户

总结更新了哪些标的、在哪个 watchlist 中、新的 price_bands 是什么。

---

## 第 5 步：输出格式模板

最终输出应包含以下板块（顺序可调整）：

1. **估值快照**：一张表（PE/PB/PS/FCF Yield/股息率 + vs 历史分位）
2. **核心财务**：近 5 年收入/净利/ROE/毛利率/OCF 趋势
3. **多方法估值**：每种方法独立成段
4. **综合加权 + 价格区间**
5. **敏感性分析**：PE × EPS 矩阵
6. **风险与催化剂**
7. **一句话结论**
8. **Watchlist 更新确认**：更新了哪个文件、新的 price_bands

---

## 示例：国电南瑞

```
触发：使用合适算法对国电南瑞估值

→ 第0步：拉取 tushare 行情 + 财务 + web_search 一致预期 + 读取已有深度分析
→ 第1步：选择 PE分位/PEG/EV-EBITDA/FCF Yield/DDM/逆向DCF（6种）
→ 第2步：执行多方法估值，加权合理价 ≈ 26.7元
→ 第3步：输出价格区间 [30.00, 26.50, 22.50]
→ 第4步：grep data/watchlist_*.json → 命中 watchlist_core.json
          更新 current_price=22.83, price_bands=[30.00, 26.50, 22.50]
          运行 sync_watchlist.ps1
→ 第5步：告知用户「已更新 watchlist_core.json 国电南瑞 price_bands」
```

---

## 注意事项

- EPS 单位：tushare `total_mv` 是万元，EPS 是元，注意换算一致性
- H 股标的：额外拉取 H 股行情，A/H 溢价纳入估值参考
- 新股/次新股：若 PE 历史不足 3 年，用可比公司 + PEG + 逆向 DCF 为主，PE 分位法降权
- 亏损公司：跳过 PE/PEG/DDM，主用 EV/Sales + 逆向 DCF + SOTP
- 强周期股：PE 分位法失效，用正常化盈利（5Y 平均 EPS）替代 TTM EPS
- 深度分析未覆盖的标的：先执行完整估值，估值完成后提示用户可后续补做深度分析
