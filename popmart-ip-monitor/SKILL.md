---
name: popmart-ip-monitor
description: >
  泡泡玛特 IP 健康度周期监控。对 THE MONSTERS/Labubu、Molly、Skullpanda、Crybaby、Dimoo
  等核心 IP 的二级市场价格、社媒热度、卖盘压力和 IP 扩散情况进行周度跟踪，与上期报告对比
  判断趋势变化。不分析财报、不估值建模、不给买卖建议——只输出 IP 健康度、风险信号和
  需要人工验证的问题。触发词：泡泡玛特监控 / Pop Mart IP 监控 / 潮玩IP跟踪 /
  Labubu监控 / 泡泡玛特IP周报 / popmart monitor。
---

# 泡泡玛特 IP 监控（Pop Mart IP Monitor）

## 1. 目标

持续监控泡泡玛特旗下不同 IP 与关键单品的二级市场表现、社媒热度、库存/卖盘压力和 IP 扩散情况，辅助判断：

1. 泡泡玛特是否仍然是单一 IP 驱动。
2. THE MONSTERS / Labubu 的热度是否衰退、扩散或继续强化。
3. Molly、Skullpanda、Crybaby、Dimoo 等非 Labubu IP 是否具备持续生命力。
4. 新品发售后的溢价是否能维持。
5. 老品是否仍有价格韧性。
6. 市场热度是来自真实消费者，还是来自黄牛和短期投机。
7. **本期相较上期发生了哪些增量变化。**

本 skill **不分析财报，不进行估值建模，不直接给出买入/卖出建议。**
只输出 IP 健康度、风险信号、趋势变化和需要进一步人工验证的问题。

---

## 1.5 方法论纪律（最重要，违反即失真）

本 skill 的价值在于"持续追踪 IP 运营边际状态"，**不在于**输出公司基本面结论或投资建议。以下纪律违反任何一条，报告即失真：

### 1.5.1 四类信号不可互相替代

每条信息必须归入且仅归入一类，跨类推导需显式标注：

| 信号类别 | 衡量什么 | 典型来源 | 能推出的结论 |
|---|---|---|---|
| **官方销售** | 终端真实需求 | 财报/官方售罄/补货后零售量/退货率/复购 | 消费需求强弱（最强证据） |
| **二手投机** | 黄牛与稀缺溢价 | 得物/闲鱼/StockX 价格与挂单 | 投机热度，≠ 需求 |
| **消费者热度** | 真实用户参与度 | 社媒 UGC/特展预约/开箱 | 产品吸引力与心智 |
| **资本市场事件** | 股东与估值预期 | 举牌/评级/股价 | 市场预期，≠ IP 健康 |

> ⚠️ **二手价格下降 ≠ IP 结构性退潮。** 二手溢价只能监测投机热度。价格下降至少来自四种不同情况，对基本面的含义完全不同：
> ① 消费者需求下降（负面）；② 公司大规模补货（收入可能仍好）；③ 黄牛退出、供需回归正常（长期可能更健康）；④ 单系列自身吸引力不足（单 SKU 问题，≠ 整个 IP 退潮）。
> 结论必须区分：**"投机退潮"已验证** vs **"消费需求退潮"未验证**。

### 1.5.2 禁止伪精确（false precision）

无精确数据时，**不得输出小数型倍数或百分比**。规则：

- ❌ 禁止：`卖盘压力 1.85x`、`成交活跃度 0.8x`、`社媒热度 75/100`、`泡沫风险 30%`（当这些数字来自新闻定性描述时）。
- ✅ 改为：`卖盘压力：高（较上周进一步上升，置信度低）`、`成交活跃度：低（定性，置信度低）`。
- §8 的公式**仅在确有成交量/挂单精确数据时使用**；否则该指标降级为 高/中/低 + 置信度标注。
- §10 的 0–100 **健康度是"综合研判分"，不是测量值**。必须在报告中明确标注「研判分，置信度低」，且不得仅凭它推出"某 IP 商业价值超过另一 IP"。

### 1.5.3 IP 评估必须拆分为两个维度

单一综合分会让小 IP 靠一次联名超过核心 IP。每个 IP 必须分别给：

| 维度 | 衡量什么 | 数据来源 |
|---|---|---|
| **商业基本盘** | 收入/销量/用户规模/复购/地域分散 | 财报、官方销售（最强） |
| **边际趋势** | 新品热度/价格变化/社媒增速/催化剂 | 二手+社媒+官宣（本 skill 主追踪） |

- 综合分**侧重边际趋势**（因本 skill 追踪二级市场与 IP 运营），但必须同时展示基本盘分。
- 例：THE MONSTERS 可能「基本盘最强、边际趋势转弱」；DIMOO 可能「基本盘较小、边际趋势最强」。两者不可合并为"DIMOO 比 THE MONSTERS 健康"。

### 1.5.4 资本市场事件独立成章，不计入 IP 健康度

段永平举牌、评级变动、股价涨跌是**估值与股东行为信号**，证明不了 Labubu 需求回升、DIMOO 接力成功或 IP 健康度改善。必须放在独立的「资本市场信号」章节，不混入 §10 评分输入。

### 1.5.5 联名验证目标不可偷换

DIMOO×皮克斯若成功，验证的是**全球 IP 运营/联名能力、外部授权商业化能力、供应链与渠道能力**；**不能直接证明**泡泡玛特能持续创造原创全球 IP、或 DIMOO 本身已成为全球级 IP、或 DIMOO 脱离皮克斯后仍有同等需求。措辞必须精确。

### 1.5.6 术语与计算陷阱

- **整盒 vs 单盒**：潮玩"整盒"（通常 6+1 或 12 款）与"单盒/单只"价格差异巨大。引用媒体"整盒 XX 元"时，需结合官方单盒价与单款价判断其真实指代，标注术语风险，不得直接用于破发幅度计算。
- **跨平台环比禁止**：StockX 价与跨平台聚合价（TYPA 等）口径不同，**不得直接计算环比百分比**。只能记录"较前期引用显著回落，但口径不一致，需同源验证"。

---

## 2. 使用场景

当用户要求：

- 监控泡泡玛特不同 IP 热度
- 监控得物、闲鱼、淘宝、eBay、StockX、小红书、TikTok、Instagram 等平台数据
- 比较 Labubu 与其他 IP 的市场表现
- 判断泡泡玛特是否存在单一 IP 依赖
- 生成周期性泡泡玛特 IP 跟踪报告
- 将本期结果与上一期报告做增量比较

应使用本 skill。

---

## 3. 合规原则

数据采集必须遵守目标平台的服务条款、robots 规则和访问限制。优先级：

1. 官方开放 API 或授权数据源
2. 用户手动导出的 CSV/Excel/JSON
3. 用户手动截图或页面内容
4. 低频、非侵入式的公开页面读取（`WebFetch` 单页读取）
5. **不使用**绕过登录、绕过风控、破解签名、批量刷接口、模拟异常行为等方式

如果无法合规采集某个平台的数据，在报告中标注：

- 数据源不可用
- 缺失字段
- 对结论的影响
- 可替代数据源建议

> ⚠️ **禁止为完整性而编造数据。**

---

## 4. 推荐运行频率

| 频率 | 操作 | 说明 |
|------|------|------|
| **每周** | 完整报告 | 采集数据 + 生成报告 + 与上期对比 |
| **每日**（可选） | 快照 | 仅采集保存数据，不做长报告。积累价格/成交/热度时间序列 |

如果本地 AI 只能低频运行，建议每周运行一次，但报告中标注数据密度不足。

---

## 5. 目录结构

```text
popmart-ip-monitor/
  config/
    watchlist.yaml          # 监控 IP/SKU 清单
    source_config.yaml      # 数据源配置
    scoring_config.yaml     # 评分权重配置

  data/
    raw/                    # 原始采集数据
      dewu/
      xianyu/
      taobao/
      ebay/
      stockx/
      xiaohongshu/
      tiktok/
      instagram/

    snapshots/              # 每期标准化快照
      2026-06-29.json
      2026-07-06.json

    normalized/             # 时间序列 CSVs
      sku_daily.csv
      ip_daily.csv
      social_daily.csv

  reports/                  # 周度报告（Markdown）
    2026-06-29-popmart-ip-monitor.md
    2026-07-06-popmart-ip-monitor.md

  logs/
    run.log
    missing_data.log
```

> 报告也会同步输出一份到 `02-主题/泡泡玛特IP监控/` 以便在 Obsidian 中浏览。

---

## 6. 监控对象配置

监控清单定义在 `config/watchlist.yaml`，用户按需修改。示例：

```yaml
company: Pop Mart

ips:
  - ip_name: THE MONSTERS
    aliases:
      - Labubu
      - Zimomo
      - The Monsters
    group: core_validation
    thesis_role: "验证公司是否过度依赖 Labubu / THE MONSTERS"
    skus:
      - sku_id: monsters_001
        name: "Labubu 代表款 A"
        category: "plush"
        official_price: 199
        launch_date: "2025-01-01"
        rarity: "normal"
        importance: high

      - sku_id: monsters_002
        name: "Labubu 隐藏款 B"
        category: "blind_box"
        official_price: 69
        launch_date: "2025-03-01"
        rarity: "hidden"
        importance: high

  - ip_name: MOLLY
    aliases:
      - Molly
    group: mature_ip
    thesis_role: "验证老 IP 是否仍有韧性"
    skus:
      - sku_id: molly_001
        name: "Molly 代表款 A"
        category: "blind_box"
        official_price: 69
        launch_date: "2024-06-01"
        rarity: "normal"
        importance: medium

  - ip_name: SKULLPANDA
    aliases:
      - Skullpanda
    group: mature_ip
    thesis_role: "验证非 Labubu 核心 IP 是否仍有市场热度"
    skus: []

  - ip_name: CRYBABY
    aliases:
      - Crybaby
    group: growth_ip
    thesis_role: "验证成长 IP 是否接力"
    skus: []

  - ip_name: DIMOO
    aliases:
      - Dimoo
    group: mature_ip
    thesis_role: "验证中长期 IP 留存"
    skus: []

  - ip_name: NEW_IP_POOL
    aliases: []
    group: new_ip
    thesis_role: "监控新 IP 是否出现早期爆款迹象"
    skus: []
```

### IP 分组定义

| 组名 | 说明 | 示例 |
|------|------|------|
| `core_validation` | 核心验证组 | THE MONSTERS / Labubu |
| `mature_ip` | 成熟老 IP | Molly、Skullpanda、Dimoo |
| `growth_ip` | 成长观察组 | Crybaby 或近期起量 IP |
| `new_ip` | 新 IP 观察组 | — |
| `collab_limited` | 联名/限量观察组 | — |
| `long_tail` | 长尾 IP 观察组 | — |

---

## 7. 数据源字段要求

### 7.1 二级市场价格字段

```yaml
sku_id: string
ip_name: string
platform: string
snapshot_date: YYYY-MM-DD
official_price: number
lowest_ask_price: number | null
last_trade_price: number | null
avg_trade_price_7d: number | null
avg_trade_price_30d: number | null
trade_volume_7d: number | null
trade_volume_30d: number | null
listing_count: number | null
bid_price: number | null
ask_price: number | null
bid_ask_spread: number | null
currency: CNY | USD | HKD | other
source_url: string | null
data_quality: high | medium | low
notes: string | null
```

**字段解释**：

- `official_price`：官方发售价。
- `lowest_ask_price`：当前最低挂卖价。
- `last_trade_price`：最近成交价，优先级高于挂单价。
- `avg_trade_price_7d/30d`：近 7/30 日平均成交价。
- `trade_volume_7d/30d`：近 7/30 日成交量。
- `listing_count`：当前在售数量/卖盘数量。
- `bid_ask_spread`：买卖价差。价差越大，价格可信度越低。
- `data_quality`：成交价 > 挂单价；有成交量 > 只有价格；多平台交叉验证 > 单平台。

### 7.2 社媒热度字段

```yaml
ip_name: string
platform: string
snapshot_date: YYYY-MM-DD
keyword: string
post_count_7d: number | null
view_count_7d: number | null
like_count_7d: number | null
comment_count_7d: number | null
share_count_7d: number | null
positive_mentions: number | null
negative_mentions: number | null
top_topics: list[string]
sample_posts: list[string]
data_quality: high | medium | low
notes: string | null
```

**社媒平台建议**：

| 区域 | 平台 |
|------|------|
| 国内 | 小红书、抖音、微博、B站 |
| 海外 | TikTok、Instagram、YouTube Shorts、Reddit、eBay 搜索热度、Google Trends |

如果无法自动采集社媒数据，允许 AI 进行低频人工式网页观察，报告中标注 `qualitative_only`。

---

## 8. 核心计算指标

> ⚠️ **前置纪律（见 §1.5.2）**：以下公式**仅在确有成交量/挂单/社媒定量数据时使用**。当数据来自新闻定性描述、无直接平台 API 时，对应指标**不得输出小数型结果**，必须降级为 `高 / 中 / 低 + 置信度（低）` 的定性表述。禁止把定性推断包装成精确倍数/百分比。

### 8.1 SKU 级指标

```
溢价率 premium_rate = market_price / official_price - 1
```

> `market_price` 优先级：`avg_trade_price_7d > last_trade_price > lowest_ask_price`
> 只有挂单价无成交价 → 数据质量降一级。

```
7日价格变化  price_change_7d  = current_market_price / market_price_7d_ago - 1
30日价格变化 price_change_30d = current_market_price / market_price_30d_ago - 1

成交活跃度  volume_activity = current_trade_volume_7d / historical_avg_trade_volume_7d
卖盘压力    sell_pressure   = current_listing_count / historical_avg_listing_count
买卖价差率  spread_rate     = bid_ask_spread / market_price

新品回落幅度 post_launch_drawdown = current_market_price / peak_price_since_launch - 1
老品韧性     old_sku_resilience   = current_market_price / avg_market_price_90d
```

### 8.2 IP 级指标

```
IP 平均溢价率   = 该 IP 所有关键 SKU 溢价率的加权平均
IP 成交活跃度   = 该 IP 所有关键 SKU 成交活跃度的加权平均
IP 卖盘压力     = 该 IP 所有关键 SKU 卖盘压力的加权平均
IP 价格扩散度   = 溢价率 > 20% 的 SKU 数 / 该 IP 监控 SKU 总数
IP 健康SKU占比  = 健康 SKU 数 / 该 IP 监控 SKU 总数
IP 新品成功率   = 新品上市 30 天后仍有正溢价且成交活跃的新品数 / 新品监控数
IP 老品韧性     = 老品当前价格 / 老品过去 90 天均价
```

### 8.3 全公司级指标

```
Labubu 集中度代理指标 = THE MONSTERS 健康度 / 所有 IP 健康度总和
非 Labubu 扩散度      = 非 THE MONSTERS IP 中健康度为 A 或 B 的 IP 数量
多 IP 健康指数        = 健康 IP 数 / 被监控 IP 总数
泡沫风险指数          = 高溢价但低成交、卖盘上升、价差扩大、社媒热度下降的 SKU 占比
```

---

## 9. SKU 健康状态判定

| 状态 | 判断条件 |
|------|---------|
| **强势健康** | 溢价率 > 30%，成交活跃，卖盘未显著上升，价差小，未从峰值大幅回落 |
| **短期火热** | 溢价率高，上市时间短，成交活跃，但历史数据不足 |
| **投机过热** | 溢价率极高，成交量下降，挂单上升，价差扩大，社媒热度开始降温 |
| **自然回落** | 新品发售后从高点回落但仍高于发售价，成交仍存在，属正常降温 |
| **转弱** | 溢价率 < 10% 或跌破发售价，成交量下降，卖盘增加 |
| **失效** | 长期无成交，长期跌破发售价，社媒热度消失 |

---

## 10. IP 健康度评分（0–100，研判分，置信度低）

> ⚠️ **本分数为"综合研判分"，不是测量值。** 必须标注「研判分，置信度低」。无精确数据时，分数由定性推断得出，仅用于横向参考，**不得仅凭它推出某 IP 商业价值超过另一 IP**（见 §1.5.3）。

### 10.0 双维度拆分（强制）

每个 IP 必须同时给出两个独立分数，不得只报综合分：

| 维度 | 字段名 | 含义 |
|---|---|---|
| 商业基本盘 | `basic_disk_score` | 收入/销量/用户/复购/地域分散（来源：财报、官方销售） |
| 边际趋势 | `marginal_score` | 新品热度/价格变化/社媒增速/催化剂（来源：二手+社媒+官宣） |

- 综合分 `health_score` **侧重边际趋势**（因本 skill 主追踪二级市场与 IP 运营），但报告必须并列展示 `basic_disk_score`，并加注：「综合分侧重边际，基本盘更强者商业价值未必更低」。
- 评分时逐维度标注 `confidence: low/medium`。

### 权重配置（默认，可通过 `config/scoring_config.yaml` 调整）

```yaml
premium_score_weight: 0.20
volume_score_weight: 0.20
persistence_score_weight: 0.20
breadth_score_weight: 0.20
sell_pressure_penalty_weight: 0.10
social_heat_score_weight: 0.10
```

### 计算公式

```
IP 健康度 =
  溢价得分 × 20%
+ 成交活跃得分 × 20%
+ 持续时间得分 × 20%
+ SKU 扩散得分 × 20%
+ 社媒热度得分 × 10%
- 卖盘压力惩罚 × 10%
```

### 评级映射

| 评级 | 分数 | 含义 |
|------|------|------|
| **A** | 80–100 | IP 健康，价格、成交、扩散、社媒和卖盘结构较好 |
| **B** | 65–79 | IP 有热度，但需观察持续性或扩散度 |
| **C** | 50–64 | 一般，可能只有部分 SKU 强，或成交/社媒不足 |
| **D** | 30–49 | 明显转弱，价格和成交不足 |
| **E** | 0–29 | 基本失效 |

---

## 11. 增量分析逻辑（关键）

每次运行**必须**执行增量比较。

### 11.1 查找上一期

优先读取：
- `reports/` 中日期最近且早于本期的报告
- `data/snapshots/` 中日期最近且早于本期的快照

如无上一期，输出：

> 这是首期报告，无法进行环比判断。

### 11.2 必须比较的增量字段

**每个 IP：**

| 字段 | 比较方式 |
|------|---------|
| 健康度 | 本期 vs 上期 |
| 平均溢价率 | 本期 vs 上期 |
| 成交活跃度 | 本期 vs 上期 |
| 卖盘压力 | 本期 vs 上期 |
| 健康 SKU 数量 | 本期 vs 上期 |
| 转弱 SKU 数量 | 本期 vs 上期 |
| 社媒热度 | 本期 vs 上期 |

**全公司层面：**

- THE MONSTERS 是否继续强于其他 IP
- 非 THE MONSTERS IP 是否改善
- 多 IP 扩散度是否提升
- 泡沫风险指数是否上升
- 是否出现新 IP 接力迹象
- 是否出现 Labubu 单点过热迹象

### 11.3 增量判断分类

| 判断 | 条件 |
|------|------|
| **继续强化** | 健康度上升，成交活跃，卖盘压力未恶化 |
| **高位稳定** | 健康度维持高位，价格未明显回落，成交正常 |
| **热度扩散** | 多个 SKU 或多个平台同时改善 |
| **短期过热** | 价格继续上涨，但成交下降、卖盘增加或价差扩大 |
| **边际转弱** | 健康度下降，成交减弱，卖盘上升 |
| **明显失速** | 价格下跌、成交下降、社媒热度下降同时发生 |
| **数据不足** | 关键字段缺失，不能判断 |

---

## 12. 报告格式（模板）

每期报告写入 `reports/YYYY-MM-DD-popmart-ip-monitor.md`：

```markdown
# 泡泡玛特 IP 监控报告 - YYYY-MM-DD

## 1. 本期结论摘要

用 5–10 条 bullet 总结本期最重要变化。必须回答：

- THE MONSTERS / Labubu 是否仍是绝对主驱动？
- 非 Labubu IP 是否有接力迹象？
- 本期是热度扩散、稳定、转弱，还是投机过热？
- 哪些 IP 出现正向增量？
- 哪些 IP 出现风险信号？

## 2. 全公司层面观察

| 指标 | 本期 | 上期 | 变化 | 判断 |
|---|---:|---:|---:|---|
| 多IP健康指数 | | | | |
| Labubu集中度代理指标 | | | | |
| 泡沫风险指数 | | | | |
| 非Labubu健康IP数量 | | | | |
| 监控SKU总数 | | | | |
| 数据质量 | | | | |

### 2.5 信号分类框架（四类信号不可互相替代）

每周必须显式归类本期所有信号，并说明"哪类有证据、哪类缺证据"：

| 信号类别 | 本期证据 | 能推出的结论 |
|---|---|---|
| 官方销售 | （填写，通常最缺） | 终端真实需求 |
| 二手投机 | （填写） | 投机热度，≠ 需求 |
| 消费者热度 | （填写） | 产品吸引力与心智 |
| 资本市场事件 | （填写） | 市场预期，独立成章 |

> 结论必须区分：**"投机退潮"已验证** vs **"消费需求退潮"未验证**；**"多IP接力信号出现"** vs **"多IP接力成功已验证"**。

## 3. IP 健康度排名

| 排名 | IP | 健康度 | 评级 | 环比变化 | 主要原因 |
|---:|---|---:|---|---:|---|
| 1 | THE MONSTERS | | | | |
| 2 | MOLLY | | | | |
| 3 | SKULLPANDA | | | | |
| 4 | CRYBABY | | | | |
| 5 | DIMOO | | | | |

## 4. 各 IP 详细分析

### 4.1 THE MONSTERS / Labubu

#### 本期状态（双维度，均标置信度）
- 商业基本盘（`basic_disk_score`，置信度：）：收入占比 / 全球知名度 / SKU 数 / 海外渠道 —— 定性 + 研判分
- 边际趋势（`marginal_score`，置信度：）：新品热度 / 价格变化 / 社媒增速 / 催化剂 —— 定性 + 研判分
- 综合健康度（`health_score`，研判分，置信度低）：**侧重边际趋势**，不等于商业价值
- 环比变化：
- 综合判断：

#### 正向信号（仅 IP 运营/消费者侧，不含资本市场事件）
-

#### 风险信号
-

#### 需要人工验证的问题
-

### 4.2 MOLLY

（同上）

### 4.3 SKULLPANDA

（同上）

### 4.4 CRYBABY

（同上）

### 4.5 DIMOO

（同上）

### 4.6 资本市场信号（独立章节，不计入任何 IP 健康度）

> ⚠️ 举牌、评级、股价是估值与股东行为信号，证明不了 IP 需求回升或接力成功。单独成章。

- 重要股东动作（如段永平举牌）：事实 + 对估值的含义
- 评级/目标价分歧（如德银沽售 vs 大摩建设性）
- 股价/估值位置（如 ~153 港元、PE ~14x、52 周低位）
- 明确写出：上述信号**不计入** §10 IP 评分

## 5. SKU 异动榜

### 5.1 正向异动

| SKU | IP | 平台 | 本期价格 | 环比 | 溢价率 | 成交变化 | 判断 |
|---|---:|---:|---:|---:|---:|---|

### 5.2 负向异动

| SKU | IP | 平台 | 本期价格 | 环比 | 溢价率 | 成交变化 | 判断 |
|---|---:|---:|---:|---:|---:|---|

### 5.3 疑似投机过热

| SKU | IP | 过热原因 | 需要观察 |
|---|---|---|---|

## 6. 社媒热度观察

| IP | 平台 | 热度变化 | 主要话题 | 情绪判断 |
|---:|---|---|---|

## 7. 本期核心判断

从以下六类中选择一类：

1. 多 IP 健康扩散
2. Labubu 单点强势，其他 IP 一般
3. 整体高位稳定
4. 边际转弱
5. 投机过热
6. 数据不足，暂不能判断

并说明理由。

> ⚠️ **结论必须做四态区分，不得混为一谈**：
> - 「投机退潮」已验证 / 未验证
> - 「消费需求退潮」已验证 / 未验证
> - 「多 IP 接力信号出现」是 / 否
> - 「多 IP 接力成功」已验证 / 未验证
>
> 例：可写"Labubu 最新系列二级市场投机溢价继续下降（投机退潮已较强验证），但终端需求是否结构性转弱尚未确认；DIMOO/Crybaby/Twinkle Twinkle 出现更多催化（接力信号出现），但尚不能量化替代 THE MONSTERS 收入贡献（接力成功未验证）"。

## 8. 下期重点观察

列出 3–8 个下期必须跟踪的问题。例如：

- Labubu 核心 SKU 溢价是否继续维持？
- Molly / Skullpanda 是否出现补涨？
- Crybaby 是否能持续成交？
- 新 IP 是否出现首发后 30 天仍有正溢价的单品？
- 卖盘数量是否继续上升？
- 小红书/TikTok 热度是否与成交价格背离？

## 9. 数据缺口与可信度

说明本期哪些数据缺失，哪些结论可信度较低。

## 10. 附录：本期监控 SKU 清单

列出本期实际监控的 SKU、平台、字段完整度。
```

---

## 13. 输出物

每次运行必须输出两类文件：

### 13.1 快照文件

`data/snapshots/YYYY-MM-DD.json`

包含本期所有原始标准化数据、计算指标、IP 聚合结果、数据质量说明。

### 13.2 报告文件

`reports/YYYY-MM-DD-popmart-ip-monitor.md`

内容为自然语言分析报告。

如果本地系统支持，还可更新：

- `data/normalized/sku_daily.csv`
- `data/normalized/ip_daily.csv`
- `data/normalized/social_daily.csv`

---

## 14. 报告语气

- 克制
- 数据优先
- **明确区分事实、推断和假设**
- 不夸大单期变化
- 不因单个 SKU 暴涨判断公司变好
- 不因单个 SKU 回落判断 IP 失效
- 始终关注多 IP 扩散度，不只关注 Labubu

**禁止：**

- 直接说"可以买入"或"应该卖出"
- 用单一平台价格代表全部市场
- 把挂单价当成真实成交
- 忽略成交量和卖盘压力
- 编造缺失数据
- 忽略数据质量

---

## 15. 最终判断框架

每期报告结尾必须包含：

```markdown
## 本期一句话判断

本期泡泡玛特 IP 侧面数据呈现为：

【多 IP 健康扩散 / Labubu 单点强势 / 高位稳定 / 边际转弱 / 投机过热 / 数据不足】

核心理由是：

1. 
2. 
3. 

对"泡泡玛特是否具备持续制造全球 IP 的组织能力"的验证程度：

【增强 / 持平 / 减弱 / 暂无法判断】

> ⚠️ 措辞精确：区分"全球 IP **运营/联名**能力"（如 DIMOO×皮克斯可验证）与"全球**原创** IP 制造能力"（不能直接由联名证明）。不得偷换验证目标。

下期最重要观察点：

1. 
2. 
3. 
```

---

## 16. 核心思想

不要把泡泡玛特看成单纯的"盲盒公司"。

本 skill 真正要验证的是：

> 泡泡玛特到底是在吃一个超级爆款的红利，
> 还是已经具备持续创造、运营、放大多个全球消费 IP 的组织能力。

因此最重要的不是某一个单品涨了多少，而是：

- 多个 IP 是否同时健康
- 新品是否能接力
- 老品是否有韧性
- 二级市场价格是否有真实成交支撑
- 社媒热度是否和交易数据一致
- 卖盘压力是否可控
- Labubu 之外是否有第二、第三增长曲线

---

## 17. 执行流程（每期运行）

### 第 1 步：加载配置

读 `config/watchlist.yaml` 获取本期监控的 IP 和 SKU 清单。

### 第 2 步：数据采集

对每个 SKU 采集二级市场价格字段（§7.1），对每个 IP 采集社媒热度字段（§7.2）。

采集方式优先级：
1. 用户提供的 CSV/Excel/JSON → 直接解析
2. `WebFetch` 读取公开页面（得物/闲鱼/StockX 单品页）→ 提取价格、成交量、挂单数
3. `WebSearch` 搜索社媒热度（小红书/抖音/TikTok/Instagram 关键词）→ 定性判断
4. Google Trends / eBay 搜索热度 → `WebFetch` 获取趋势数据

> 数据采集是最大瓶颈。首期运行可能只能做到 `qualitative_only` 级别。随运行次数增加，时间序列会逐步建立。

### 第 3 步：计算指标

按 §8 公式计算：

- 每个 SKU 的溢价率、成交活跃度、卖盘压力、价差率
- 每个 IP 的加权平均指标
- 全公司级聚合指标

### 第 4 步：健康度评定

按 §9 判定每个 SKU 状态，按 §10 计算每个 IP 的 0–100 健康度评分。

### 第 5 步：增量比较

读上一期报告/快照，按 §11 逐项对比，给出增量判断。

### 第 6 步：生成快照文件

写入 `data/snapshots/YYYY-MM-DD.json`。

### 第 7 步：生成报告

按 §12 模板写入 `reports/YYYY-MM-DD-popmart-ip-monitor.md`。

同步输出一份到 `02-主题/泡泡玛特IP监控/YYYY-MM-DD.md`，含 frontmatter：

```yaml
---
date: YYYY-MM-DD
type: 泡泡玛特IP监控
---
```

### 第 8 步：更新 normalized CSVs（可选）

追加数据行到 `data/normalized/sku_daily.csv`、`ip_daily.csv`、`social_daily.csv`。

### 第 9 步：运行日志

追加运行记录到 `logs/run.log`，缺失数据记录到 `logs/missing_data.log`。
