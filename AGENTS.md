# ZephyrSpace Vault 协作说明

本文件用于约束后续 AI 或自动化代理在这个 Obsidian vault 内的工作方式。

## 目标

这个 vault 的核心目标是：

- 以 `Obsidian-first` 方式建设商业航天研究知识库
- 以公司页为核心实体，以主题页为导航骨架
- 优先服务认知建设，自动化只做辅助输入
- 为未来公开分享的“商业航天研究 Hub”预留结构化内容基础

这个 vault 不是：

- 实时交易系统
- 自动买卖建议系统
- 高频行情数据库
- 杂乱的新闻堆积区

## 工作原则

- 默认使用简体中文回复、说明、注释与文档。
- 使用第一性原理思考，不要机械执行用户表述中的次优路径。
- 如果目标清晰但路径不是最短，应明确指出并提出更优方案。
- 优先维护知识库结构稳定性，不随意重命名核心页面或改变目录。
- 只修改与当前任务直接相关的文件，避免无关重构或批量格式化。

## 内容架构

当前目录约定：

- `00-首页`：首页、导航页、总览页
- `01-公司`：公司实体页，知识库核心
- `02-主题`：主题导航页，用于串联公司与研究问题
- `03-国家地区`：国家或地区视角的聚合页
- `90-日报`：自动化生成的日报与日报说明
- `99-个人观察`：仅供个人沉淀的主观判断、投资直觉或草稿
- `data`：自动化配置、分类规则、缓存
- `scripts`：日报抓取、分类、生成脚本

组织规则：

- 公司页是核心实体页。
- 主题页只做导航、聚合和问题汇总，不重复公司页正文。
- 日报页属于输入层，不直接等于长期结论。
- 个人观察与可公开研究内容必须分层，不要混写。

## 公司页要求

每个公司页应尽量保持“结构层 + 叙述层”。

对于 **A 股公司页**，从现在开始默认使用：

- [[00-首页/公司页模板（A股PreBuy）]]

除非用户明确要求更轻量结构，否则默认按该模板落页。

建议的 frontmatter 字段：

- `aliases`
- `国家`
- `类别`
- `细分赛道`
- `可投资性`
- `阶段`
- `关注级别`
- `最后更新日期`

建议的正文区块：

- 公司简介
- 产业链位置
- 核心业务
- 关键产品/服务
- 与 `[[SpaceX]]` 或其他核心公司的关系
- 相关公司
- 相关主题
- 研究观察
- 待验证问题
- 参考来源

链接要求：

- 每个公司页至少链接 1 个主题页
- 每个公司页至少链接 2 个相关公司页
- 尽量链接 1 个国家/地区页

## 日报自动化要求

日报当前采用“行业新闻池 -> 规则归类 -> 写入 Obsidian”的流程，而不是“每家公司单独抓源”的流程。

默认要求：

- 优先从商业航天垂直媒体抓取
- 再按公司关键词归类到公司页标题下
- 无法归到公司的重要新闻，保留在“宏观与产业动态”
- 不自动改写公司主页面
- 不自动给出买入或卖出建议

日报中允许出现：

- 英文原标题
- 英文原摘要
- 中文标题对照
- 中文摘要对照

如果翻译或抓取失败：

- 优先保证日报能生成
- 可以降级为只保留英文原文
- 不允许因为单条新闻翻译失败导致整份日报失败

## Watchlist 管理约定

watchlist 数据已拆分为 4 个文件，放在 `data/` 目录：

| 文件 | 内容 | 大小参考 |
|---|---|---|
| `watchlist_meta.json` | schema、tier_definitions、AGENT_INSTRUCTION 等元数据 | ~10KB |
| `watchlist_core.json` | core tier 数组（核心池，约 13 家） | ~15KB |
| `watchlist_growth.json` | growth tier 数组（成长池，约 61 家） | ~72KB |
| `watchlist_radar.json` | radar tier 数组（雷达池，约 83 家） | ~114KB |

**读写规则（重要）**：
- 新增/更新公司时，**只改对应 tier 的文件**，不碰其他三个
- 读取 `AGENT_INSTRUCTION`、`tier_definitions`、`decision_tree` 时，读 `watchlist_meta.json`
- 每次修改后，运行 `.\scripts\sync_watchlist.ps1` 同步到外部项目

> 🚫 **任何 Agent（包括主 Agent 和子 Agent）在用户确认前，均不得写入任何 watchlist 文件。**
>
> **正确流程**：
> 1. 子 Agent 完成 PreBuy 后，在输出结论中注明「建议档位：xxx」，**不写文件**
> 2. 主 Agent 汇总所有 PreBuy 结果后，向用户展示建议档位，**询问用户确认哪些公司写入**
> 3. 收到用户确认后，主 Agent 一次性写入，然后运行 `sync_watchlist.ps1`
>
> 即使技能（skill）文档中有"写入 watchlist"的指令，也必须跳过，等待用户确认。
> 多个 Agent 并发写同一文件会导致内容互相覆盖、数据丢失，这是此规则的根本原因。

**在修改任何 watchlist 文件之前，必须**：

1. 阅读 `watchlist_meta.json` 中的 `AGENT_INSTRUCTION`、`tier_definitions`、`decision_tree`
2. 只收录已完成完整 PreBuy 分析的公司（`01-公司/` 下有对应页面）
3. 完整规则见 `data/WATCHLIST_RULES.md`

新增公司时直接按 `required_fields` 中的必填字段填写（`required_fields` 在 `watchlist_meta.json` 中）。

**"不入"出口**：满足以下任意 2 条的公司直接排除，**不写入 watchlist**，在公司页和指数专题页注明"❌ 不入"：
1. OCF/净利 < 20%（或非经常性损益 > 60% 净利）——利润质量严重失真
2. 无明确有时限的修复路径（修复时间 > 3 年或无法预期）
3. 结构性治理/合规风险（如外资持股 > 50% 叠加出口管制、非标审计）

### 季报更新 SOP（对已在 watchlist 的公司）

**触发条件**：`next_earnings_type` = `一季报` / `半年报` / `三季报` / `季报`，且对应财报已发布。

**A股季报发布节点参考**：
- 一季报：4月30日前
- 半年报：8月31日前
- 三季报：10月31日前
- 年报：4月30日前（次年）

**执行步骤**：

1. **批量识别待更新公司**：筛选 `next_earnings_type` 不为半年报/年报的公司，检查财报是否已发布
2. **拉取财报数据**：优先 tushare `fina_indicator`，**若最新 end_date 不符（仍为上一期），必须用 web_fetch 外部验证**（见下方数据规范）
3. **更新公司页**：在 `## 已核实的关键事实` 或 `## 季度财报跟踪` 区块添加新一期数据，更新 `## PreBuy 结论` 加 `[Qx YYYY已验证]` 标注
4. **更新 watchlist JSON（必须同时更新以下两个字段，缺一不可）**：
   ```json
   "next_earnings_type": "半年报",
   "next_earnings_date": "2026-08-31"
   ```
   > ⚠️ **已踩坑**：只更新了 `next_earnings_type`，漏掉 `next_earnings_date`，会导致 Watchlist 视图仍显示旧的财报日期。两个字段必须在同一个脚本里一并更新。
5. 更新 `prebuy_conclusion` 纳入最新季报简评
6. **运行 `sync_watchlist.ps1`** 同步

**A股季报 → 下一期日期参考**：
| 当前类型 | 改为 | `next_earnings_date` |
|---|---|---|
| 一季报 (3月) | 半年报 | `YYYY-08-31` |
| 半年报 (6月) | 三季报 | `YYYY-10-31` |
| 三季报 (9月) | 年报 | `YYYY+1-04-30` |
| 年报 (12月) | 一季报 | `YYYY+1-04-30` |

**子 Agent 季报更新分工**：
- 子 Agent 职责：更新公司页，输出建议的 watchlist 字段更新（key-value 格式）
- 主 Agent 职责：汇总子 Agent 结果，写入 watchlist JSON（子 Agent 不得直接写文件）

---

### tushare 财报数据规范

> ⚠️ **tushare 财报数据存在延迟**（通常滞后1-3天，有时更长），不能假设 `fina_indicator` 返回的就是最新季报。

**验证规则**：
1. 拉取 `fina_indicator` 后，检查返回的最新 `end_date` 是否符合预期
   - 例：4月30日后查询，若 `end_date` 最新仍为 `20251231`（年报），而非 `20260331`（Q1），说明 tushare 未更新
2. **不符合预期时，必须用 `web_fetch` 外部验证**：
   - A股：东方财富 `https://emweb.securities.eastmoney.com/PC_HSF10/FinanceAnalysis/index?code={code}`
   - A股财务摘要：`https://quote.eastmoney.com/concept/{code}.html`
   - 美股/港股：`https://stockanalysis.com/stocks/{ticker}/financials/?p=quarterly`
3. 若 tushare 与外部数据不一致，以**外部数据为准**，并在脚本注释中记录不一致情况

**tushare Q1 ROE 低估陷阱**（已在粗筛 SOP 中记录，此处补充季报更新场景）：

在季报更新时，若拉取 `roe` 字段用于 prebuy_conclusion 描述，需注意：
- Q1 ROE 因净资产是全年数，通常只有全年 ROE 的 1/4（约年化的 25%）
- 描述时应使用**年化 ROE**（Q1 ROE × 4）或写明"Q1单季 ROE=X%，年化约X%"
- 或直接用最近年报 ROE 作为参考值，季报 ROE 只做趋势判断

## 网络搜索：Tavily 集成

**Tavily 可用**，API Key 存于 `.env` 的 `TAVILY_KEY` 字段。工具模块：`scripts/tavily_search.py`。

### 何时用 Tavily vs web_fetch

| 场景 | 工具 | 原因 |
|---|---|---|
| 红旗排查（处罚/违规/诉讼/负面事件）| **Tavily** | URL 不确定，需跨来源搜索 |
| 近期重大事件（公告/并购/管理层变动）| **Tavily** | 需要聚合多个新闻来源 |
| 公司基础信息补全（行业地位/竞争格局）| **Tavily** | 自由文本查询更高效 |
| 财务数据验证（东方财富/stockanalysis）| **web_fetch** | URL 已知，结构化数据 |
| tushare 财报延迟验证 | **web_fetch** | 拼固定 URL 速度更快 |

### 调用方式

```python
from scripts.tavily_search import prebuy_web_research, search_red_flags

# 一次获取红旗 + 近期事件 + 公司信息
result = prebuy_web_research("东方财富", "300059.SZ")
print(result["red_flags"])
print(result["recent_news"])

# 仅搜索红旗
flags = search_red_flags("东方财富", "300059.SZ")
```

### PreBuy 流程中的嵌入点

在 **第 4 步（对候选公司运行 PreBuy 分析）** 中：
- 调用 `prebuy_web_research(公司名, ticker)` 获取网络调研内容
- 将 `red_flags` 结果填入页面的 `## 主要红旗` 区块
- 将 `recent_news` 结果填入 `## 已核实的关键事实` 区块（注明"网络调研"来源）
- 若结果为空或无实质内容，在页面注明"网络调研未发现重大红旗"

## 自动化相关文件

当前关键脚本与配置：

- `scripts/generate_daily_report.ps1`
- `scripts/generate_daily_report.py`
- `scripts/fetch_industry_news.py`
- `data/sources/industry_sources.json`
- `data/classification/news_rules.json`

修改这些文件时应遵守：

- 保持现有输入输出格式稳定
- 优先兼容现有日报结构
- 新增逻辑时优先通过配置驱动，而不是把规则硬编码到多个位置

## Obsidian CLI 使用约定

如需操作笔记，优先使用 `Obsidian CLI` 做以下事情：

- 创建笔记
- 读取笔记
- 设置属性
- 检查链接关系
- 校验未解析链接、孤点页、死路页

常见用途：

- `create`
- `read`
- `property:set`
- `links`
- `backlinks`
- `orphans`
- `deadends`
- `unresolved`

注意：

- `vault` 名称以当前 Obsidian 注册值为准，目前应使用 `ZephyrSpace`
- 不要假设文件夹名和 vault 注册名永远自动一致

## Git 约定

- Commit message 使用简体中文，格式为 `<type>: <subject>`
- `type` 仅允许：`feat` / `fix` / `refactor` / `docs` / `chore` / `style` / `test`
- 一次提交只做一件事
- 未经明确要求，不执行破坏性 Git 操作

不应轻易提交的内容：

- `.obsidian/graph.json`
- 本地工作区状态
- 临时缓存
- 原始抓取噪音文件

## 指数分析触发指令对照表

**重要：两种指数分析流程，触发指令不同，绝不混淆。**

| 用户说的话 | 触发的流程 | 分析对象 |
|---|---|---|
| `用 prebuy 分析[指数名]` | **成分股 PreBuy**（见下节）| 全成分股粗筛 → 逐只深度分析 → watchlist 决策 |
| `对[指数]做指数PreBuy` | **指数整体 PreBuy**（见 `index-prebuy.skill`）| 指数估值分位 + 赛道质量 + 买入价格区间，**不拆解个股** |
| `[指数]适合现在建仓吗` | 同上，指数整体 PreBuy | — |
| `帮我评估[指数]值不值得买ETF` | 同上，指数整体 PreBuy | — |

---

## 标准流程：用 prebuy 分析某指数

**触发关键词**：用户说"用 prebuy 分析[指数代码/名称]"或类似表述时，**不需要二次确认**，直接按以下流程顺序执行完毕，最后给用户一份总结反馈。

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

> ⚠️ **PE 不再作为硬过滤条件**。高 PE 只代表当前价格贵，不代表公司基本面差。粗筛目的是找出**基本面优质**的公司长期跟踪，价格贵的公司纳入 radar tier，等价格窗口出现再行动。PE 仅在 watchlist 分档和价格区间建议中作为参考。
>
> 唯一例外：PE ≤ 0 或 NaN 视为当期亏损，直接排除。

**边界模糊规则**：若某只股票仅在**1个指标**上偏离门槛 ≤20%，则标注 ⚠️ 但不排除，进入候选后在PreBuy阶段重点关注。
- 示例：公用事业DY门槛4%，某股DY=3.5%（偏离12.5%<20%）→ 保留并标注⚠️
- 示例：消费ROE门槛15%，某股ROE=12.5%（偏离16.7%>20%）→ 排除

**新增字段**：公用事业/金融类型需在 `daily_basic` 中额外拉取 `dv_ttm`（股息率TTM）和 `pb`：
```python
# 公用事业/金融：额外拉 dv_ttm 和 pb
r = pro.daily_basic(ts_code=code, trade_date='20260424',
    fields='ts_code,pe_ttm,total_mv,pb,dv_ttm')  # ✅ dv_ttm已验证可用
```

---

### 第 2 步：获取全成分股并量化粗筛

> 🔴 **粗筛必须由主 Agent 亲自执行，不得委托给 background agent。**
> 粗筛是整个流程的信息质量关键节点——一旦漏筛，后续所有 PreBuy 都无法弥补。
> Background agent 无法感知数据缺失、Q1 陷阱、API 返回异常等常见漏筛风险；
> 主 Agent 在粗筛过程中可实时判断和修正，确保候选名单完整。
> **PreBuy 分析（第 3-5 步）可以并行委托给 background agent，但粗筛（第 2 步）不可以。**

**2a. 拉取全成分股**

使用 tushare API（token 见 `.env` 文件）：

```python
import tushare as ts, os, time
from dotenv import load_dotenv
load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# index_weight 返回历史所有期，需过滤最新 trade_date
# 后缀优先级：深交所指数用 .SZ，中证/国证指数用 .CSI，上交所用 .SH，申万用 .SW
df = pro.index_weight(index_code='399396.SZ')   # ✅ 已验证：返回 columns=[index_code,con_code,trade_date,weight]
latest_date = df['trade_date'].max()
all_stocks = df[df['trade_date'] == latest_date].sort_values('weight', ascending=False)
# 若 index_weight 无数据，依次降级：index_member → index_component
```

> ⚠️ **已验证陷阱**：`index_weight` 返回的是历史所有期数据（可达数千行），必须先过滤 `trade_date == max` 再使用，否则会重复统计。

**2b. 量化粗筛（四条硬门槛，全部满足才进入候选）**

用 `daily_basic` + `fina_indicator` 逐只调用，每只间隔 0.11s 防限流。

```python
# ✅ 已验证：daily_basic 多只逗号分隔批量调用返回空 DataFrame，必须逐只调用
db_rows, fi_rows = [], []
for code in all_stocks['con_code']:
    r = pro.daily_basic(
        ts_code=code,
        trade_date='20260424',          # 最近交易日，格式 YYYYMMDD（非周末）
        fields='ts_code,pe_ttm,total_mv,pb'
    )
    if len(r): db_rows.append(r.iloc[0])
    time.sleep(0.11)

# ✅ 已验证：fina_indicator limit=1 返回最新一期（通常为最近季报）
# or_yoy = 营收同比增速，直接在此接口取得，无需额外调用 income 接口
#
# ⚠️ Q1 ROE 低估陷阱：在 Q1（3-4月）跑粗筛时，limit=1 返回的是 Q1 季报（end_date=XXXX0331）。
# Q1 净利润只有全年的一小部分，但净资产是全年数，导致 ROE 被系统性低估（可能只有年化的 1/3）。
# 典型案例：思源电气 Q1 ROE=3.5%，全年约 20%；亨通光电 Q1 ROE=3.4%，全年 8.9%。
# 修正方法：优先取 end_date 以 1231 结尾的最近年报数据，而非最近一期季报。
for code in all_stocks['con_code']:
    r = pro.fina_indicator(
        ts_code=code,
        fields='ts_code,end_date,roe,or_yoy',   # roe=净资产收益率, or_yoy=营收同比(%)
        limit=5                                  # 多取几期，优先用最近年报
    )
    if len(r):
        annual = r[r['end_date'].str.endswith('1231')]  # 优先取全年数据
        row = annual.iloc[0] if len(annual) else r.iloc[0]
        fi_rows.append(row)
    time.sleep(0.11)

# 实测性能（399396，50只）：daily_basic 7.5s + fina_indicator 12.5s = 约 20s
```

> ⚠️ **已验证陷阱**：`total_mv` 单位为**万元**，转亿需除以 10000。

**过滤条件：根据上方「行业参数分级表」选择对应参数组，以下条件全部满足才通过。**

市值下限 ≥ 40亿（金融类 ≥ 100亿）；ROE/股息率/营收同比门槛查表。

**PE 不参与硬过滤**，但在粗筛结果表中保留展示，供 PreBuy 阶段做估值参考：
- PE ≤ 0 或 NaN → 当期亏损，直接排除
- PE 偏高（如 >50x）→ 通过筛选，但在 PreBuy 中标注"当前估值偏贵，建议 radar tier，等价格窗口"

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
- **tushare**：`daily`（价格）、`daily_basic`（PE/PB/市值）、`fina_indicator`（ROE/净现比）、`income`（营收/净利润）
- 公开财报、官网、行业报告

分析结果按模板填入页面以下所有章节：
- `## PreBuy 结论`（粗体结论句 + 不超过 3 句依据）
- `## 买入逻辑摘要`（表格形式）
- `## 已核实的关键事实`（含当前股价、总市值）
- `## 主要红旗`
- `## 价格与时机判断`（四档价位表 + 当前口径）
- `## 9 种投资陷阱复核`
- `## 当前操作含义`

价格使用 tushare 拉取最近交易日收盘价（`trade_date` 用最近周五或最近有数据日），并在页面记录 `记录时间`。

---

### 第 5 步：评估 Watchlist 入选资格

完成所有 PreBuy 分析后：
1. 阅读 `data/WATCHLIST_RULES.md` 和 `data/stock_watchlist.json` 头部 `AGENT_INSTRUCTION`
2. **先过"不入"出口**（满足任意2条即排除，不写入 JSON）：
   - ① OCF/净利 < 20% 或非经常性损益 > 60% 净利
   - ② 无明确有时限修复路径（超3年或不可预期）
   - ③ 结构性治理/合规风险
3. 对剩余公司按决策树判断：是否入选、应放哪个档位（core/growth/radar）
4. **已在 watchlist 的**：确认档位是否仍正确，如需则更新 `prebuy_conclusion`
5. **新入选的**：按 `required_fields` 填入必填字段
6. **不入选的（含"不入"出口）**：在总结中说明原因（红旗过多 / 逻辑未验证 / 不满足质量门槛 / 触发"不入"规则）

---

### 第 6 步：提交与总结反馈

1. `git add` 所有新建/修改的文件
2. 分两次提交：
   - `feat: 建立[指数名称]指数专题页及候选成分股PreBuy页面`
   - `feat: 按WATCHLIST_RULES将[N]家公司纳入watchlist` （如有新增）
3. **若 watchlist 有任何变更**（新增、档位调整、字段更新），同步至外部项目：
   ```powershell
   .\scripts\sync_watchlist.ps1
   ```
   > 此步在 git commit **之后**执行，确保同步的是已提交的最终版本。
4. 向用户输出总结，包含：

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

- **并行执行**：第 3~4 步可多家公司同时开 agent 处理，提高效率（每批 3~4 家）
- **已有页面**：若公司页已存在且有完整 PreBuy 分析，应更新价格和结论，而非重写整页
- **价格日期**：统一用最近的 A 股交易日（非周末），`price_date` 格式 `YYYY-MM-DD`
- **不给买卖建议**：PreBuy 结论只描述赔率和区间，不说"应该买多少钱"
- **粗筛门槛可调**：若指数整体估值偏高（如科技主题），可适当放宽 PE 上限，但需在总结中注明

---

## 修改边界

未经明确要求，不要主动做这些事：

- 批量重命名所有目录
- 重写整套信息架构
- 把日报内容自动写回公司页
- 引入复杂数据库或网站框架
- 把投资观察升级成交易建议

## 决策优先级

遇到取舍时，优先级如下：

1. 保证知识库结构清晰
2. 保证日报自动化稳定
3. 保证内容可长期积累与未来可发布
4. 再考虑功能扩展与视觉优化

## 输出偏好

- 先给结论，再给必要细节
- 优先给推荐方案，不要平铺多个方案不做判断
- 说明改动时，重点写清楚影响、边界和未验证风险

---

## 标准流程：对指数做指数PreBuy

**触发关键词**：用户说"对[指数]做指数PreBuy"、"[指数]适合现在建仓吗"、"帮我评估[指数]值不值得买ETF"等，**不需要二次确认**，直接按本流程执行。

完整 SOP、代码示例、数据来源、输出规范见 `index-prebuy.skill`，以下为执行摘要。

### 核心约束

- **分析对象是指数本身**，不拆解个股，不逐只 PreBuy
- **不给 ETF 适投性评估**（规模、流动性、追踪误差等），只评估指数
- **不给具体买卖建议**，只给价格区间和节奏参考

### 执行步骤（6步）

1. **确认基本信息**：指数代码、名称、编制类型（市值加权 vs 策略型）
2. **获取当前估值**：`ak.stock_zh_index_value_csindex(symbol)` → 当前 PE / 股息率
3. **计算历史分位**：`pro.index_daily` 拉5年价格 → 近似 PE 历史分位（3年/5年）
4. **成分股质量**：`index_weight` + `fina_indicator` → 加权平均 ROE + 集中度 CR5/CR10；若策略型指数，额外检查前10大成分的 ROE 和营收同比
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
| 价格历史（~5年）| tushare | `pro.index_daily`，后缀优先 `.CSI` |
| 历史 PE 分位（近似）| 两者计算 | 当前PE × (历史价/当前价) |
| 成分股权重 | tushare | `pro.index_weight` |
| 成分股 ROE | tushare | `pro.fina_indicator`，优先取年报（end_date 以 1231 结尾）|
| 沪深300 PE（基准）| 中证官网（akshare）| `ak.stock_zh_index_value_csindex("000300")` |
