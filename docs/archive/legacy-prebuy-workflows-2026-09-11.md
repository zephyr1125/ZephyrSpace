# 已退役：旧PreBuy与全面分析流程

> 2026-09-11历史快照，仅供追溯，不是有效执行指令。旧触发、评分入库速查和提交约定不再用于新任务；个股研究唯一入口为 `skills/company-triplet/SKILL.md`，调度以 `docs/three-report-economy-routing.md` 为准。本归档不随新SOP同步维护。

## 指数分析触发指令对照表

**重要：两种指数分析流程，触发指令不同，绝不混淆。**

| 用户说的话 | 触发的流程 | 分析对象 |
|---|---|---|
| `选股 [指数名]` | **成分股 PreBuy**（见下节）| 全成分股粗筛 → 逐只深度分析 → watchlist 决策 |
| `指数估值 [指数名]` | **指数整体 PreBuy**（见 `index-prebuy.skill`）| 指数估值分位 + 赛道质量 + 买入价格区间，**不拆解个股** |
| `[指数]适合现在建仓吗` | 同上，指数整体 PreBuy | — |
| `帮我评估[指数]值不值得买ETF` | 同上，指数整体 PreBuy | — |

> 记忆口诀：**「选股」= 找人（个股）；「指数估值」= 评物（指数本身）**

---

## 标准流程：选股 [指数名]（成分股 PreBuy）

**触发关键词**：用户说"选股 [指数代码/名称]"时，**不需要二次确认**，直接按以下流程顺序执行完毕，最后给用户一份总结反馈。

> **选股逻辑说明**：不按权重取 Top 10，而是先对全成分股做量化粗筛，再对通过筛选的公司做完整 PreBuy。原因：指数权重 = 市值权重，前十大往往是涨幅最高、估值最贵的公司；真正的好买点更多出现在中小权重成分股中。

---

### 第 1 步：建立指数专题页

在 `05-A股指数/` 下创建 `[指数代码] [指数名称].md`，**必须使用模板 `[[00-首页/指数页模板（A股指数）]]`**。

**命名规则**（严格遵守）：
- 格式：`[指数代码] [指数官方全名].md`，例如 `931994 中证电网设备主题指数.md`
- 使用**指数代码**（不是 ETF 代码）；若以 ETF 为入口分析，则追踪指数代码优先
- 若存在旧名/简称（如"储能电池"），在 `aliases` 中保留，确保反链不断

**frontmatter 必填字段**：
- `aliases`（包含简称、代码）
- `指数代码`（格式：`XXXXXX.XX`）
- `指数名称`（官方全名）
- `成立日期`
- `发布机构`
- `样本数量`
- `相关ETF`（若有）
- `类别`（成长科技 / 消费医药 / 公用事业能源 / 周期材料 / 金融 / 通用混合）
- `最后更新日期`

**正文必须包含的区块**（按顺序）：
1. `## 指数简介`
2. `## 粗筛参数与结果汇总`
3. `## 通过粗筛的成分股`
4. `## 全成分股概览`
5. `## Watchlist 决策汇总`
6. `## 板块风险提示`
7. `## 相关主题`（包含 `[[00-首页/A股指数研究模块]]`）

---

### 行业参数分级表

**在执行粗筛前，先判断该指数属于哪个行业类型，选择对应参数组。**

不同行业的商业模式差异巨大，用统一参数会系统性错判：高ROE门槛会过度淘汰公用事业（重资产、低ROE是常态），低PE门槛会错误保留虚高估值的成长股。

| 行业类型 | 代表指数/主题 | 市值下限 | ROE下限 | 股息率要求 | 营收同比下限 | 候选上限排序字段 |
|---|---|---|---|---|---|---|
| **成长科技** | AI、半导体、军工、卫星通信 | 40亿 | 12% | 无 | ≥-10% | ROE降序 |
| **消费/医药** | 白酒、食品、医药生物 | 40亿 | 15% | 无 | ≥-15% | ROE降序 |
| **公用事业/能源** | 电力、水务、燃气、绿电 | 40亿 | 8% | ≥4% | ≥-15% | 股息率降序 |
| **周期/材料** | 化工、钢铁、煤炭、有色 | 40亿 | 10% | ≥3% | ≥-20% | PB升序（越低越好） |
| **金融** | 银行、保险、证券 | 100亿 | 10% | ≥4% | ≥-10% | 改用PB≤1.5x替代PE |
| **通用/混合** | 宽基或跨行业主题 | 40亿 | 12% | 无 | ≥-15% | ROE降序 |

> ⚠️ **PE 不再作为硬过滤条件**。高 PE 只代表当前价格贵，不代表公司基本面差。粗筛目的是找出**基本面优质**的公司长期跟踪；价格贵的优质公司仍按质量进入 core/growth，并通过价格区间等待窗口。PE 仅在价格区间建议中作为参考。
>
> 唯一例外：PE ≤ 0 或 NaN 视为当期亏损，直接排除。

**边界模糊规则**：若某只股票仅在**1个指标**上偏离门槛 ≤20%，则标注 ⚠️ 但不排除，进入候选后在PreBuy阶段重点关注。
- 示例：公用事业DY门槛4%，某股DY=3.5%（偏离12.5%<20%）→ 保留并标注⚠️
- 示例：消费ROE门槛15%，某股ROE=12.5%（偏离16.7%>20%）→ 排除

**新增字段**：公用事业/金融类型需额外获取 `dv_ttm`（股息率TTM）和 `pb`，在理杏仁 `fundamental/non_financial` 的 `metricsList` 中加入 `"dyr"`（年化股息率）和 `"pb"` 即可：
```python
# 公用事业/金融：在 metricsList 中加入股息率和 PB
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": trade_date,
    "metricsList": ["pe_ttm", "pb", "mc", "dyr"]  # dyr = 年化股息率（%），理杏仁已验证可用
})
```

---

### 第 2 步：获取全成分股并量化粗筛

> 🔴 **粗筛必须由主 Agent 亲自执行，不得委托给 background agent。**
> 粗筛是整个流程的信息质量关键节点——一旦漏筛，后续所有 PreBuy 都无法弥补。
> Background agent 无法感知数据缺失、Q1 陷阱、API 返回异常等常见漏筛风险；
> 主 Agent 在粗筛过程中可实时判断和修正，确保候选名单完整。
> **PreBuy 分析（第 3-5 步）可以并行委托给 background agent，但粗筛（第 2 步）不可以。**

**2a. 拉取全成分股**

使用理杏仁 API（token 见 `.env` 文件的 `LIXINGER_TOKEN`）：

```python
import requests, os, sys
from dotenv import load_dotenv
from datetime import date, timedelta
load_dotenv()

LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def last_trading_day():
    """返回最近交易日（跳过周末；节假日需人工判断）。"""
    d = date.today()
    while d.weekday() >= 5:  # 5=周六 6=周日
        d -= timedelta(days=1)
    return d.isoformat()

def lx_post(path, payload):
    resp = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN})
    return resp.json()

# 获取成分股权重：cn/index/constituent-weightings [S]
# stockCode 传纯数字代码（不带后缀），如 "399396"（深交所指数）、"000300"（上交所）
trade_date = last_trading_day()
result = lx_post("cn/index/constituent-weightings", {
    "stockCode": "399396",   # ← 替换为目标指数代码（纯数字，不带 .SZ/.SH）
    "date": trade_date
})
all_stocks = sorted(result.get("data", []), key=lambda x: x.get("weight", 0), reverse=True)
codes = [s["stockCode"] for s in all_stocks]
# 若返回空，说明理杏仁不收录该指数，降级用 cn/index/constituents（无权重）或 akshare
```

> ⚠️ **理杏仁指数代码说明**：`cn/index/constituent-weightings` 使用纯数字代码（如 `"399396"`），不带 `.SZ`/`.SH` 后缀。可先调用 `cn/index` 接口列出所有支持指数确认代码。若理杏仁不收录目标指数，降级使用 `ak.index_stock_cons_weight_csindex(symbol="XXXXXX")`。

**2b. 量化粗筛（四条硬门槛，全部满足才进入候选）**

理杏仁 `fundamental/non_financial` 为 **[M] 端点**，支持批量传入所有成分股代码，一次调用即可获取全量 PE/PB/市值数据，无需逐只调用。

```python
# ⚠️ fundamental/* 接口日期必须用最近交易日（非周末/节假日），否则静默返回空数据
# ⚠️ fundamental/* 接口必须用 stockCodes（数组），不能用 stockCode（字符串）

# 一次批量获取所有成分股估值（PE/PB/市值）
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,      # 纯数字代码数组，如 ["600036", "300059", ...]
    "date": trade_date,       # 最近交易日
    "metricsList": ["pe_ttm", "pb", "mc"]  # mc = 总市值（亿元）
})
val_dict = {d["stockCode"]: d for d in val_resp.get("data", [])}

# Q1 ROE 低估陷阱：优先取最近年报数据（期末日以 12-31 结尾），避免 Q1 ROE 被系统性低估
# 年报 ROE 通常在 3-4 月之前已全部披露；若处于 4 月披露密集期，需逐只验证 QDATE
last_annual_end = f"{date.today().year - (1 if date.today().month < 5 else 0)}-12-31"

# fs/* 用 date 参数时为 [M] 端点，支持批量
# ⚠️ 财报字段名以 fetch_doc("cn/company/fs/non_financial") 返回的 metricsList 为准
# 常用字段示例（需用 lixinger-query skill 的 fetch_doc 确认）：
#   ROE：可能在 fundamental 中（如 "roe"）或 fs 中（如 "a.pr.roe.t"）
#   营收同比：可能为 "a.ps.toi.t.yoy" 等
# 建议：先用 fetch_doc 查一次合法字段名，再填入 metricsList
fs_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": last_annual_end,   # 传最近年末日，返回最近年报数据
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t.yoy"]  # 示例，需用 fetch_doc 确认
})
fs_dict = {d["stockCode"]: d for d in fs_resp.get("data", [])}

# 实测性能（50只）：两次批量调用 约 2-3s（对比原 tushare 逐只调用约 20s）
```

> ⚠️ **理杏仁 [M] 端点批量说明**：`fundamental/*` 和 `fs/*`（传 `date` 参数时）均支持批量传入 `stockCodes` 数组，大幅提升效率。若成分股超过 100 只，分两批次调用。

**过滤条件：根据上方「行业参数分级表」选择对应参数组，以下条件全部满足才通过。**

市值下限 ≥ 40亿（金融类 ≥ 100亿）；ROE/股息率/营收同比门槛查表。

**PE 不参与硬过滤**，但在粗筛结果表中保留展示，供 PreBuy 阶段做估值参考：
- PE ≤ 0 或 NaN → 当期亏损，直接排除
- PE 偏高（如 >50x）→ 通过筛选，但在 PreBuy 中标注“当前估值偏贵，等待价格窗口”；档位仍按公司质量判断

> 粗筛阶段**不写页面**，只输出候选名单，并标注 ⚠️ 边界模糊公司。

**2c. 候选名单上限**

- 候选名单 ≤ 15 家时：全部进入第 3 步
- 候选名单 > 15 家时：按行业参数分级表中对应的「候选上限排序字段」取前 15 家

---

### 第 3 步：为每家候选公司建立专题页

对候选名单中每家公司：
1. 检查 `01-公司/[公司简称].md` 是否已存在：
   - **已存在**：跳过创建，直接进入第 4 步
   - **不存在**：以 `00-首页/公司页模板（A股PreBuy）.md` 为模板新建页面
2. 填入 frontmatter（`aliases`、`国家:中国`、`类别`、`细分赛道`、`可投资性`、`阶段`、`关注级别`、`最后更新日期`）
3. 填入公司简介、产业链位置等基础信息

---

### 第 4 步：对每家候选公司运行 PreBuy 分析

对每家公司逐一执行完整 PreBuy 分析，使用以下数据来源：
- **理杏仁**：`cn/company/candlestick`（当前价格）、`cn/company/fundamental/non_financial`（PE/PB/市值历史分位）、`cn/company/fs/non_financial`（ROE/营收/净利润）
- 公开财报、官网、行业报告

分析结果按模板填入页面以下所有章节：
- `## PreBuy 结论`（粗体结论句 + 不超过 3 句依据）
- `## 买入逻辑摘要`（表格形式）
- `## 已核实的关键事实`（含当前股价、总市值）
- `## 主要红旗`
- `## 价格与时机判断`（四档价位表 + 当前口径）
- `## 9 种投资陷阱复核`
- `## 当前操作含义`

价格使用理杏仁 `cn/company/candlestick` 拉取最近交易日收盘价（`endDate` 传 `last_trading_day()` 返回的日期），并在页面记录 `记录时间`。

---

### 第 5 步：评估 Watchlist 入选资格

完成所有 PreBuy 分析后：
1. 阅读 `data/WATCHLIST_RULES.md` 和 `data/watchlist_meta.json` 中的 `AGENT_INSTRUCTION`
2. **先过"不入"出口**（满足任意2条即排除，不写入 JSON）：
   - ① OCF/净利 < 20% 或非经常性损益 > 60% 净利
   - ② 无明确有时限修复路径（超3年或不可预期）
   - ③ 结构性治理/合规风险
3. 对剩余公司按决策树判断：是否入选、应放哪个档位（core/growth）
4. **已在 watchlist 的**：确认档位是否仍正确；若重做估值则更新 `target_price`
5. **新入选的**：按 `required_fields` 填入必填字段
6. **不入选的（含"不入"出口）**：在总结中说明原因（红旗过多 / 逻辑未验证 / 不满足质量门槛 / 触发"不入"规则）

---

### 第 6 步：提交与总结反馈

> ⚠️ **此步骤必须由主 Agent 亲自执行，不可委托给子 Agent。**

1. **更新公司索引页**（`00-首页/公司索引.md`）：

   所有分支 agent 完成公司页创建后，由主 Agent 统一补充索引——**这是批量流程中索引更新的唯一正确时机**，不依赖子 agent 自行更新。

   - 在对应市场区块（A股/港股）中按拼音首字母插入 `[[公司名]]` 链接
   - 每新增一家公司，顶部总数 +1
   - 更新日期为今天：`> 共 **XXX** 个公司页（更新于 YYYY-MM-DD）`

   > ⚠️ 此步骤不可省略。子 agent 创建公司页时不负责更新索引，必须由主 Agent 在汇总阶段统一完成。漏掉会导致新页面游离于索引之外。

2. `git add` 所有新建/修改的文件
3. 分两次提交：
   - `feat: 建立[指数名称]指数专题页及候选成分股PreBuy页面`
   - `feat: 按WATCHLIST_RULES将[N]家公司纳入watchlist` （如有新增）
4. **若 watchlist 有任何变更**（新增、档位调整、字段更新），同步至外部项目：
   ```powershell
   .\scripts\sync_watchlist.ps1
   ```
   > 此步在 git commit **之后**执行，确保同步的是已提交的最终版本。
5. 向用户输出总结，包含：

```
## [指数名称] PreBuy 分析总结

### 指数概览
[指数定位一句话]

### 粗筛结果
全成分 N 只 → 通过筛选 M 只 → 深度分析 K 只
| 未入选公司 | 淘汰原因（ROE不足/估值过高/营收下滑） |

### 深度分析结果
| 公司 | 权重 | 当前价 | 当前档位 | PreBuy结论摘要 |
|---|---|---|---|---|
| ... |

### Watchlist 入选结果
| 公司 | 入选档位 | 入选理由 |
| 公司 | 未入选 | 原因 |

### 需要关注的风险
[跨公司的共性风险，如行业集中度、政策等]
```

---

### 注意事项

- **并行执行**：第 3~4 步可多家公司同时开 agent 处理，提高效率（每批 最多 6 家）
- **已有页面**：若公司页已存在且有完整 PreBuy 分析，应更新价格和结论，而非重写整页
- **价格日期**：记录在公司页或估值报告中；Watchlist 不再保存 `price_date`
- **粗筛门槛可调**：若指数整体估值偏高（如科技主题），可适当放宽 PE 上限，但需在总结中注明

---


## 标准流程：指数估值 [指数名]（指数整体 PreBuy）

**触发关键词**：用户说"指数估值 [指数名]"、"[指数]适合现在建仓吗"、"帮我评估[指数]值不值得买ETF"等，**不需要二次确认**，直接按本流程执行。

完整 SOP、代码示例、数据来源、输出规范见 `index-prebuy.skill`，以下为执行摘要。

### 核心约束

- **分析对象是指数本身**，不拆解个股，不逐只 PreBuy
- **不给 ETF 适投性评估**（规模、流动性、追踪误差等），只评估指数

### 执行步骤（6步）

1. **确认基本信息**：指数代码、名称、编制类型（市值加权 vs 策略型）
2. **获取当前估值**：`ak.stock_zh_index_value_csindex(symbol)` → 当前 PE / 股息率
3. **计算历史分位**：理杏仁 `cn/index/fundamental`，`metricsList` 含 `pe_ttm.y3.cvpos`/`q2v`/`q5v`/`q8v`，直接返回3年历史分位，无需手工计算
4. **成分股质量**：理杏仁 `cn/index/constituent-weightings` + `cn/company/fs/non_financial` [M] → 加权平均 ROE + 集中度 CR5/CR10；若策略型指数，额外检查前10大成分的 ROE 和营收同比
5. **赛道周期判断**：综合判断产业周期阶段、政策面、景气信号
6. **写入并同步 watchlist_index.json**：所有完成分析的指数无条件写入（主Agent执行），随后运行 `.\scripts\sync_watchlist.ps1` 同步到 `E:\Work\Python\Finance\api\config\watchlist_index.json`

### 输出写入位置

分析结果写入两处：

**① 指数页** `05-A股指数/[代码] [名称].md` 中的以下区块：
- `## 指数整体PreBuy结论`
- `## 估值历史分位`
- `## 成分股整体质量`
- `## 赛道周期判断`
- `## 买入价格区间`

若指数页不存在，先按 `[[00-首页/指数页模板（A股指数）]]` 创建基础页面再填入。

**② `data/watchlist_index.json`** 的 `indices` 数组：
- 所有完成指数整体 PreBuy 的指数**无条件纳入**，不分档位，不判断是否值得
- 若已存在则整条更新（重新分析即更新）
- `index_code` 为唯一键，写入前确认不重复
- **主Agent负责写入，禁止子Agent直接写入**
- **写入后必须运行** `.\scripts\sync_watchlist.ps1`，同步到 `E:\Work\Python\Finance\api\config\watchlist_index.json`
- 写入格式见 `index-prebuy.skill` 第 6 步模板

### 数据来源速查

| 数据 | 来源 | 接口 |
|---|---|---|
| 当前 PE / 股息率 | 中证官网（akshare）| `ak.stock_zh_index_value_csindex` |
| 价格历史（~5年）| 理杏仁 | `cn/index/candlestick`，`stockCode` 传纯数字代码 |
| 历史 PE 分位 | 理杏仁 | `cn/index/fundamental`，`metricsList` 含 `pe_ttm.y3.cvpos`/`q2v`/`q5v`/`q8v` |
| 成分股权重 | 理杏仁 | `cn/index/constituent-weightings` [S]，`stockCode` 传纯数字代码 |
| 成分股 ROE | 理杏仁 | `cn/company/fs/non_financial` [M]，`date` 传最近年末日（以 12-31 结尾）|
| 沪深300 PE（基准）| 中证官网（akshare）| `ak.stock_zh_index_value_csindex("000300")` |


---

## 标准流程：全面分析 [公司名]（个股深度尽调完整流程）

**触发关键词**：用户说"全面分析 [公司名/代码]"时，**不需要二次确认**，直接按本流程执行。

> **流程定位**：深度分析 + 审核修复 + PreBuy + Watchlist + Commit，是最完整的个股研究流程。适用于打算重仓建仓前的全面尽调，或初次覆盖某公司时建立完整知识页。

### 流程顺序

1. 深度分析（deep-company-review）
2. **双 agent 审核（深度分析报告）**
3. **事实核查与修复**（含评分调整）
4. PreBuy 公司页（stock-prebuy-review / us-stock-prebuy / hk-prebuy）**基于修复后的深度分析**，引用护城河/财务/治理评分
5. Watchlist 写入（主 Agent 统一执行，子 Agent 禁止直接写文件）
6. Git Commit

> ⚠️ **审核在 PreBuy 之前**：深度分析数据错误若在 PreBuy 之后才发现，会导致 PreBuy 引用了错误的评分和结论。先审核修复、确认评分无误，再用最终版深度分析作为 PreBuy 的输入。
>
> ⚠️ **审核发现问题必须调整评分**：若审核发现数据方向错误、业务增速写反、融资工具遗漏等影响判断的 P1 问题，必须同步修正对应维度的子项得分，并重新加总总分，确保最终评分反映修复后的事实。

---

### 第 1 步：深度分析

技能文件：`deep-prebuy-skill/SKILL.md`（A股/港股/美股通用框架）

输出路径：`深度分析/[公司简称] 深度分析 YYYY-MM-DD.md`

提交前必查（11项检查清单）：
- 审计机构从当年年报官方摘要核实（坑10）
- 评分算术自校验 A+B+C+D+E+F == 总分（坑11）
- 业务分部增减速方向经年报原文核实（坑12）
- 上市主体合并范围核清（坑13）
- 融资工具覆盖可转债/H股可转债/优先股（坑14）

---

### 第 2 步：双 agent 审核（深度分析报告）

agent-review-deep：审核深度分析报告（算术 + 来源 + 增速方向 + 审计机构）

重点检查项：
- 审计机构是否从当年年报摘要核实
- 评分汇总表算术 A+B+C+D+E+F == 总分
- 业务分部增减速方向与年报一致
- FCF 口径已注明
- 融资工具覆盖完整（含可转债/H股可转债）
- 监管处罚逐条记录（金额单位、事件不合并）

---

### 第 3 步：事实核查与修复（**含评分调整**）

- P1（必改）：数据方向错误、审计机构错误、评分算术不符 → **同步修正对应维度子项得分，重新加总总分**
- P2（补充）：遗漏数据点、引用不完整
- P3（可选）：表述优化、格式问题

> ⚠️ **评分联动规则**：审核发现某维度事实有误，必须评估该错误是否影响当时的打分逻辑：
> - 若业务增速方向写反 → 重新评估 B4 可持续性子项
> - 若融资工具遗漏（如遗漏可转债）→ 重新评估 F2 股东利益对齐子项
> - 若审计机构错误（标准→非标）→ 触发前置排除；若仅名称错误不影响评分性质 → 记录修正，不调整分值
> - 评分调整后必须同步更新：①各维度子项得分表；②综合评分汇总表；③最终总分；④公司页末尾深度分析链接注释中的评分行

---

### 第 4 步：PreBuy 公司页（引用**修复后**的深度分析）

市场分工：
- A股：stock-prebuy-review
- 美股：us-stock-prebuy
- 港股：hk-prebuy

公司页中引用深度分析的位置：
- 护城河分析 → 注明"参见深度分析报告 C 维度（X/20）"
- 财务质量 → 引用 E 维度得分和关键结论
- 治理结构 → 引用 F 维度得分

公司页末尾追加（在 PreBuy 结论之后）：

```
## 深度分析报告
[[深度分析/[公司简称] 深度分析 YYYY-MM-DD|[公司简称] 深度分析（YYYY-MM-DD）]]
- 评分：XX / 100（已审核，YYYY-MM-DD）
- 评级：⭐⭐⭐
- 核心结论：一句话摘要
```

---

### 第 5 步：Watchlist 写入

- 新公司：深度总分（审核后最终版）≥85→Core；70-84→Growth；<70→不建议入
- 已有公司：根据最新完整估值报告更新 `target_price`，并独立重评 `valuation_certainty`
- `valuation_certainty` 取值 `0.00–1.00`（最多两位小数），只衡量目标价可靠程度，不得与 `cScore`、`mScore` 重复计分；必须评估盈利/现金流可预测性、商业模式和资本强度、资产负债表和融资需求、估值方法收敛度及主要尾部风险
- 参考区间：`0.80–0.90` 极高、`0.70–0.79` 较高、`0.60–0.69` 中等、`0.50–0.59` 中低、`0.40–0.49` 较低、`<0.40` 很低；不得因偏好公司而上调，主要估值假设变化时必须重评
- 自动计算 `buy_price = target_price × (0.68 + 0.14 × valuation_certainty)`；`buy_price` 仅作为使用端派生值，不写入 Watchlist
- Watchlist 不再保存 `prebuy_conclusion`、实时价格、价格日期、价格带、估值锚或风险摘要
- 所有 watchlist JSON 必须用 UTF-8 **无 BOM** 写入；BOM 会导致外部 `/stock-watchlist` 解析异常
- 写入后运行 `sync_watchlist.ps1` 同步
- 档位由公司基本面质量决定，与当前股价无关

---

### 第 6 步：Git Commit（最多3次）

1. feat: 新增[公司简称]深度分析报告（YYYY-MM-DD）
2. feat: 更新[公司简称]公司页PreBuy分析（全面分析版）
3. feat: 更新watchlist（[公司简称]入[档位]）（若有变更）

---

### 深度评分 → Watchlist 档位速查

| 深度分析总分 | 推荐档位 | 仓位建议 |
|---|---|---|
| 85-100 | Core | 核心仓位 >10% |
| 70-84 | Growth | 成长仓位 5-10% |
| <70 | 不建议入 | 仅保留研究页，不进入 watchlist |
