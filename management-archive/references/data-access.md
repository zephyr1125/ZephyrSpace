# 管理层：研究与评分核心规则：data-access

由本模块 SKILL.md 按条件路由；不要求所有角色每次通读。来源优先级、调度、修复轮次、提交和回写权限服从统一 SOP。

<!-- migrated:part-04:start -->
## 数据源总览

### 必须覆盖的事项与可选来源

| 来源 | 工具 | 获取内容 | 用途 |
|------|------|---------|------|
| **CNINFO** | `CninfoClient` | 公司概况（董事长/总经理/法人/董秘/独董）、高管持股变动、十大股东、分红历史、股本变动、处罚/诉讼、质押/冻结、互动易问答、投资评级 | 管理层名单、增减持、资本动作、监管记录、IR 态度 |
| **CNINFO 人事公告** | `CninfoClient.list_announcements()` 关键词过滤 | 高管离任/辞职/聘任/选举公告（近 3-5 年） | **高管变动历史时间线**——谁何时上任/离任、原因、接任者 |
| **理杏仁** | 理杏仁 API Skill | 实际控制人、高管增减持汇总、大股东增减持汇总、分红融资统计、质押汇总、证监会监管措施、问询函 | 交叉验证 CNINFO 数据、获取更长历史 |
| **智堡** | `WisburgClient` | 电话会纪要（`search_earnings_calls`）、企业研究报告（`search_company_reports`）、资讯流（`search_feed`） | 管理层原始表述、卖方对管理层的评价、关键事件 |

完整三件套使用共享证据包，以下平台是来源选项，不要求每个角色/每次更新全量调用。先检查人事、控制结构、资本配置、言行兑现和监管覆盖，缺口才补查；相同原始披露不因来自两个API而算作独立验证。新治理事件必须更新，历史时间线无变化时复用并查重述。

### 原件与已有资料（优先复用）

| 来源 | 获取内容 | 用途 |
|------|---------|------|
| **年报 MD** (`财报/[公司名]/`) | 董事长致辞、MD&A 经营讨论、审计意见、管理层名单、关联交易披露 | **最重要的一手来源**——历年董事长致辞是言行一致性追踪的核心素材 |
| **深度分析报告** (`深度分析/`) | 已有的深度分析中 F 维度结论 | 复用已有判断，增量更新 |

### 兜底搜索（以上源覆盖不足时）

| 来源 | 工具 | 用途 |
|------|------|------|
| **Tavily** | `scripts/tavily_search.py` 的 `search_red_flags` + `prebuy_web_research` | 管理层负面事件、创始人背景、行业口碑 |
| **巨潮资讯** | `CninfoClient.list_announcements()` | 年报/半年报原文 PDF 下载链接 |

---

## 数据拉取执行清单

下列调用是按缺口选用的工具清单，不是逐项必调程序。完整三件套由Terra按共享数据规范统一执行；Sol和审核员直接核决定性原文，定向补缺。

### 第 0 步：基础信息获取

```python
from scripts.cninfo_api import CninfoClient
cninfo = CninfoClient()

# 公司概况（董事长、总经理、法人、董秘、独立董事、成立日期、注册资本、主营业务）
profile = cninfo.company_profile("股票代码")

# 获取 orgId（用于后续公告查询）
```

### 第 1 步：管理层行为数据（并行拉取）

```python
# CNINFO 端
exec_trades = cninfo.executive_trades("股票代码", limit=50)       # 高管持股变动
top10 = cninfo.top10_holders("股票代码")                          # 十大股东（最新）
dividends = cninfo.dividends("股票代码")                          # 分红历史
share_changes = cninfo.share_changes("股票代码")                  # 股本变动（含定增/回购）
penalties = cninfo.company_penalties("股票代码", limit=30)        # 证券监管处罚记录（证监会/交易所/央行）
# ⚠️ 行业监管处罚必须另行检索（见第八节 8.1）：银行/保险/券商→金监总局(原银保监)；
# 制造/资源→生态环境/应急管理/药监等。API 未覆盖时用 Tavily 兜底 `{公司名} 行业监管 罚单`。
lawsuits = cninfo.company_lawsuits("股票代码", limit=20)          # 诉讼记录
pledge = cninfo.share_pledge("股票代码")                          # 质押状态
freeze = cninfo.share_freeze("股票代码")                          # 冻结状态
irm = cninfo.irm_qa("股票代码", pages=3)                          # 互动易Q&A（最近150条）
ratings = cninfo.investment_ratings("股票代码", limit=30)         # 投资评级历史

# 高管人事变动公告（近5年，关键词过滤）
personnel_anns = cninfo.list_announcements(
    "股票代码", category="", start_date=start_date, end_date=end_date,
    max_pages=3, page_size=30,
)
# 人工/AI 筛选含以下关键词的公告：
# 离任/辞职/聘任/选举/任命/调整/高管/副总裁/总经理/董事长/CTO/CFO/董秘
# 过滤掉：独立董事（非核心管理层）、董事辞职（不兼任高管时影响小）
```

### 第 2 步：理杏仁主源与按缺口交叉验证

读取共享证据和理杏仁 API Skill，按覆盖缺口选择以下端点；已有同期间数据不重拉：
- `cn/company/profile` — 实际控制人、董事长、总经理
- `cn/company/senior-executive-shares-change` — 高管增减持明细
- `cn/company/major-shareholders-shares-change` — 大股东增减持明细
- `cn/company/hot/esc` — 高管增减持汇总（各周期）
- `cn/company/hot/mssc` — 大股东增减持汇总
- `cn/company/hot/df` — 上市以来分红融资统计
- `cn/company/hot/ple` — 质押汇总
- `cn/company/measures` — 证监会监管措施
- `cn/company/inquiry` — 交易所问询函
- `cn/company/dividend` — 分红明细（含派息率）
- `cn/company/announcement` — 近期公告列表

### 第 3 步：智堡端管理层声音

```python
from scripts.wisburg_api import WisburgClient
wisburg = WisburgClient()

# 电话会纪要（管理层原始表述的最重要来源）
calls = wisburg.search_earnings_calls("公司名或代码", first=10)

# 企业研究报告（往往有管理层评价章节）
company_reports = wisburg.search_company_reports("公司名或代码", first=10)

# 资讯流（高管相关快讯）
feed = wisburg.search_feed("公司名 董事长 总经理", first=10)
```

对返回的电话会纪要，**必须获取关键纪要的详情**（`get_earnings_call_detail`），提取管理层对战略/行业/竞争/资本配置的直接表述。

### 第 4 步：年报董事长致辞（如有本地 MD）

检查 `财报/[公司简称]/` 下是否存在 MinerU 转换的年报 Markdown 文件。若存在：
- 定位"董事长致辞"或"董事长报告"章节
- 提取最近 5-7 年的董事长致辞全文或关键段落
- 记录每年的关键表述（战略方向、业绩归因、未来展望、风险提示）

若无本地 MD，通过巨潮资讯在线查看年报 PDF（`list_announcements` 获取链接）。

### 第 5 步：负面事件兜底搜索

```python
from scripts.tavily_search import search_red_flags

# 红旗排查
red_flags = search_red_flags("公司全称", "股票代码")
```

仅用于发现 CNINFO/理杏仁未覆盖的管理层负面事件（如媒体调查报道、行业口碑等）。

---

<!-- migrated:part-04:end -->
