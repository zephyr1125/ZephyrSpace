# 公司质量：评分与研究核心规则：data-access

由本模块 SKILL.md 按条件路由；不要求所有角色每次通读。来源优先级、调度、修复轮次、提交和回写权限服从统一 SOP。

<!-- migrated:part-03:start -->
### 0.3 Tavily 用量分级（**第 0 步必须判断**）

> Tavily 月度额度有限，必须按公司透明度分级管控用量。**在 0.1 完成后立即判断公司所属 Tier，后续所有 Tavily 调用均受该 Tier 上限约束。**

**分级标准**：

| Tier | 典型特征 | 上限 | 说明 |
|---|---|---|---|
| **T0 央企/大型国企** | 信息高度透明，媒体/监管全覆盖（如中国神华、招商银行、中国移动）| **1次** | 理杏仁结构化 API 已覆盖绝大多数治理事件 |
| **T1 大型民企/知名上市公司** | A股市值 > 500亿，媒体覆盖充分（如恒瑞医药、宁德时代）| **1次** | 1次合并搜索覆盖所有维度 |
| **T2 中型民企/成长股** | A股市值 100-500亿，或快速扩张期（如中小科技/医疗公司）| **2次** | 1次红旗 + 1次行业 |
| **T3 小市值/高风险行业/有历史问题** | 市值 < 100亿，或历史有处罚/诉讼，或环境高风险行业 | **3次**（现有上限）| 全量搜索 |

**Tavily 调用原则（优先级顺序）**：
1. **结构化 API 优先**：理杏仁 `measures` + `inquiry` + `senior-executive-shares-change` + `major-shareholders-shares-change` 先跑完，有结果即可不调用 Tavily
2. **兜底触发**：结构化 API 返回空 **且** Tier ≥ T2，才触发 Tavily 对应维度搜索
3. **合并搜索**：不同维度的 Tavily 查询尽量合并为 1 次（见下方代码示例）
4. **ESG 行业门控**：F4 ESG 搜索仅对制造/化工/采矿/重工业公司触发；金融/互联网/轻资产服务类**直接跳过**

### 0.4 智堡 API 深度分析集成（按证据缺口调用）

> 智堡 (`scripts/wisburg_api.py`) 提供 9 个端点，深度分析核心使用 3 个：
> `/api/reports`（投行研报）、`/api/company-reports`（企业研究）、`/api/earningscalls`（电话会纪要）。

**调用时机**：检查共享证据后，管理层声音或行业证据不足时调用适用端点；同时需要多项补充才调用 `deep_analysis_bundle()`，已有完整覆盖时不再重拉：

```python
from scripts.wisburg_api import WisburgClient
wisburg = WisburgClient()

# 一站式拉取：reports + company_reports + earnings_calls + feed + images + market_daily
bundle = wisburg.deep_analysis_bundle(company_name, ticker)
```

**维度级使用指南**：

| 维度 | 智堡端点 | 使用方式 | 产生的价值 |
|---|---|---|---|
| **A. 历史基因** | `/api/company-reports` | 搜索"公司名+历史/发展" → 卖方梳理的公司发展脉络 | 补充创始背景、关键转折点 |
| **B. 商业模式** | `/api/reports` 详情 | 研报摘要中"投资逻辑/核心观点"部分 → 商业模式定性判断 | 对定价权、可持续性、可复制性提供卖方视角 |
| **C. 竞争护城河** | `/api/reports` + `/api/images` | 研报含份额数据、壁垒分析；图片流有行业集中度图表 | 市场地位量化 + 护城河定性交叉验证 |
| **D. 战略执行力** | `/api/earningscalls` 详情 | 电话会纪要 → 管理层在Q&A中对战略目标达成情况的即兴回答 | **最重要的增强维度**——"目标→结果"验证的最佳来源 |
| **E. 财务质量** | `/api/reports` 详情 | 卖方对会计政策、FCF质量、Capex纪律的分析 | 财务预测精确数字（EPS/营收/FCF）+ 卖方对会计政策的独立判断 |
| **F. 治理结构** | `/api/earningscalls` + `/api/feed` | 电话会Q&A暴露管理层透明度；feed含质押/减持/监管事件 | 管理层可信度信号 + 治理事件实时监控 |

**关键使用原则**：
1. **智堡优先于 Tavily**：对于 B/C/D/E 维度的分析内容，智堡研报摘要的信息密度和结构化程度远超 Tavily 搜索结果。Tavily 仅用于智堡未覆盖的领域（红旗排查、小众公司基础信息）。
2. **详情按需拉取**：`deep_analysis_bundle()` 返回列表（仅含标题+时间），根据标题筛选 2-3 篇最相关的研报和电话会纪要，用 `get_report_detail()` / `get_earnings_call_detail()` 获取完整摘要。不要拉取所有详情。
3. **电话会纪要纵向对比**：如果 bundle 返回了多个季度的电话会纪要，选取最近 2 季对比——管理层语调、承诺兑现、风险表述的变化是 D/F 维度评分的重要输入。
4. **卖方目标价不用于估值**：深度分析不涉及价格/估值判断。卖方目标价和评级仅用于交叉验证市场预期方向，不纳入任一维度的评分。
5. **卖方分歧必须标注**：当不同卖方对同一公司存在显著分歧（目标价差异 > 30% 或评级方向相反），必须在报告中注明分歧，并说明双方假设差异的根源（如对 AI 变现速度的不同预判、对监管风险的不同权重）。**禁止简单取平均**——分歧本身是最有价值的信息，它揭示了市场对该公司的核心不确定点。
6. **Capex 必须拆分运营 vs 非运营**（E4 维度联动）：当公司 Capex 大幅变化时，优先引用卖方报告中对 Capex 的拆解（运营性维持+扩张 vs 非运营性土地/楼宇等）。若卖方未拆解，自行标注"未拆分，含非运营部分"。禁止将资产置换误判为资本消耗。

---

<!-- migrated:part-03:end -->

<!-- migrated:part-07:start -->
## 数据获取速查

### 财报 Markdown 文件（MinerU 转换，叙事/定性内容主源）

> 将原始年报/半年报 PDF 放入 `财报/_Inbox/`，说"转换财报"即可自动转为结构化 Markdown。
> 输出位置：`财报/[公司名]/[公司名]YYYY年[报告类型].md`

**MD 文件独占内容（API 无法提供）**：

| 内容 | 文件位置（典型章节标题） | SKILL.md 用途 |
|------|------------------------|-------------|
| 审计意见 + 审计机构 | `## 第十节 财务报告` → 搜索"审计报告"或"标准无保留" | 前置排除 + 坑10 |
| **关键审计事项（KAMs）** | `## 三、关键审计事项`（审计报告章节内）| **🆕 E5.5** |
| **会计政策/估计变更** | `## 25、 重要会计政策和会计估计的变更` | **🆕 E5.5** |
| 管理层讨论与分析 | `## 第三节 管理层讨论与分析` | D维度（战略执行）|
| **经营计划/年度目标** | `## (三)经营计划`（管理层讨论内）| **D2 兑现率追踪** |
| 分业务收入/成本明细 | `## (一) 主营业务分析` → 搜索"分行业"/"分产品" | B1 业务板块 |
| 行业格局和趋势 | `## 报告期内公司所处行业情况` | C维度 行业分析 |
| 核心竞争力 | `## 报告期内核心竞争力分析` | C4 护城河 |
| 关联交易 | `## 第六节 重要事项` → 搜索"关联交易" | F3 |
| **并购/重大资产交易** | `## 第六节 重要事项` → 搜索"收购"/"出售"/"重大" | **🆕 F2.5** |
| 董事/高管名单 | `## 第四节 公司治理` → 搜索"董事"/"高级管理人员" | F1 + 坑17 |
| 分红预案 | `## 五、 董事会决议通过的本报告期利润分配预案` | F2 |
| **回购计划** | `## 第六节 重要事项` → 搜索"回购" | **🆕 F2.5** |
| 财务报表附注（应收账龄/存货跌价/商誉）| `## 第十节 财务报告` → 搜索"应收账款"/"商誉"/"存货" | E5 资产质量 + E5.5 |

**读取技巧**：
- 年报 ~4200 行，半年报 ~3000 行 → 用 `grep -n "关键词"` 定位行号，再用 `Read offset=N limit=50` 精确读取
- 表格为 HTML `<table>` 格式，数字在 `<td>` 标签内，可直接引用
- 优先读取最新一期年报；历史年份按需定位对应小节

### 深证信 CNINFO API（补充财务/评级/股东数据源）

> 官方一手 A 股数据（深交所子公司），免费 tier，143 字段财务指标 + 投资评级 + 研报摘要 + 行业PE + 分红。
> 模块：`scripts/cninfo_api.py`

```python
from scripts.cninfo_api import CninfoClient
client = CninfoClient()

# 仅当共享包/理杏仁覆盖不足且需要多项补充时调用整包
bundle = client.deep_analysis_bundle("600519", years=[2020,2021,2022,2023,2024])

# 各组件：
# bundle["financials"]   → DataFrame: 多年财务数据（51列，中文列名）
# bundle["ttm"]          → DataFrame: 最新TTM指标（消除季节性）
# bundle["ratings"]      → DataFrame: 投资评级+目标价+评级变化
# bundle["dividends"]    → DataFrame: 历史分红（每股分红/除权日）
# bundle["shareholders"] → DataFrame: 股东户数趋势
# bundle["ipo"]          → DataFrame: IPO发行概况
# bundle["profile"]      → dict: 公司概况（主营/经营范围/简介）

# 单独调用：
df = client.financial_multi_year("600519", years=[2020,2021,2022,2023,2024])
# 列名示例：营业收入(元), 归母净利润(元), 毛利率(%), 净利润率(%),
#          净资产收益率(%), 资产负债比率(%), 经营现金流/净利润(%),
#          研发费用(元), 销售费用率(%), 营业收入增长率(%) ...

ttm = client.ttm_indicators("600519")          # TTM 财务指标
ratings = client.investment_ratings("600519")  # 投资评级+目标价
reports = client.research_reports("600519")    # 研报摘要
pe = client.industry_pe()                      # 全行业PE对比
div = client.dividends("600519")               # 分红历史
holders = client.shareholder_structure("600519") # 股东户数
changes = client.share_changes("600519")       # 股本变动
ic = client.industry_classification("600519")  # 行业分类(8套标准)
ipo = client.ipo_summary("600519")             # IPO概况
profile = client.company_profile("600519")     # 公司概况
```

**生成财务全景图**（深度分析报告中使用）：

```python
from scripts.generate_financial_charts import generate_profitability_growth_chart

# 在 financial_multi_year() 之后立即调用
chart_path = generate_profitability_growth_chart(
    df,                          # financial_multi_year() 返回的 DataFrame
    company_name="贵州茅台",
    stock_code="600519",
    output_path="深度分析/贵州茅台 深度分析 2026-05-24_盈利成长能力.png",
)

# 在深度分析报告的 E维度章节顶部用 Obsidian 语法嵌入：
# ![[贵州茅台 深度分析 2026-05-24_盈利成长能力.png]]
```

> 图表包含 2x3 六面板：盈利能力趋势(ROE/毛利率/净利率)、成长能力(营收/利润增速)、
> 营收与利润规模(双轴)、现金流质量(OCF/净利)、杜邦拆解、现金流结构。
> CLI 独立使用：`python scripts/generate_financial_charts.py 600519 "贵州茅台"`

**字段速查**（深度分析最常用）：
| 用途 | CNINFO 字段 | 对应 SKILL.md 维度 |
|------|------------|-------------------|
| 营业总收入 | 营业收入(元) (F089N) | E3 增长质量 |
| 归母净利润 | 归母净利润(元) (F102N) | E3 增长质量 |
| 扣非净利润 | 扣非净利润(元) (F076N) | E3 扣非占比 |
| 毛利率 | 毛利率(%) (F078N) | B3 定价权 / E1 |
| 净利率 | 净利润率(%) (F017N) | E1 杜邦拆解 |
| ROE | 净资产收益率(%) (F014N) | E1 ROE质量 |
| ROE(加权) | 净资产收益率(加权)(%) (F067N) | E1 |
| 资产负债率 | 资产负债比率(%) (F041N) | E4 资本结构 |
| 流动比率 | 流动比率 (F042N) | E4 |
| 速动比率 | 速动比率 (F043N) | E4 |
| 经营现金流 | 经营活动现金流量净额(元) (F105N) | E2 现金流质量 |
| 经营现金流/净利 | 经营现金流/净利润(%) (F063N) | E2 净现比 |
| 营收增长率 | 营业收入增长率(%) (F052N) | E3 |
| 净利增长率 | 净利润增长率(%) (F053N) | E3 |
| 研发费用 | 研发费用(元) (F130N) | D5 研发强度 |
| 研发费用率 | 研发费用率(%) (F131N) | D5 |
| 销售费用率 | 销售费用率(%) (F132N) | B4 |
| 商誉 | 商誉(元) (F115N) | E5 资产质量 |
| 每股收益 | 基本每股收益(元) (F004N) | E3 |
| 每股分红 | 每股分红(元) (p_sysapi1139) | F2 股东回报 |

### 理杏仁 API（结构化主源：财务/行情/增减持/监管）

```python
import requests, os, gzip, json
from dotenv import load_dotenv
load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

def lx_post(path, payload):
    resp = requests.post(
        f"https://open.lixinger.com/api/{path}",
        json={**payload, "token": LX_TOKEN},
        headers={"Accept-Encoding": "gzip"}  # 必须带此头，否则返回 429
    )
    # ⚠️ 陷阱：即使请求了 gzip，API 有时仍返回明文 JSON，必须用 try/except 双路解码
    try:
        return json.loads(gzip.decompress(resp.content))
    except Exception:
        return resp.json()

# 基本面（批量，[M]端点）
lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": ["600036"],
    "date": "2025-04-30",  # 最近交易日（非周末/节假日）
    "metricsList": ["pe_ttm", "pb", "mc", "roe"]
})

# 年报财务（批量，[M]端点）
r = lx_post("cn/company/fs/non_financial", {
    "stockCodes": ["600036"],
    "date": "2024-12-31",  # 年末日
    # ⚠️ 有效字段：y.ps.toi.t / y.ps.np.t / y.bs.ta.t / y.bs.tl.t
    # ❌ 无效字段（返回 None）：y.ps.ocf.t / y.bs.se.t / 任何 .yoy 后缀
    # 净资产 = ta - tl（必须手算，无直接字段）
    "metricsList": ["y.ps.toi.t", "y.ps.np.t", "y.bs.ta.t", "y.bs.tl.t"]
})
# ⚠️ 陷阱：响应字段是嵌套 dict，不是扁平 key，d.get("y.ps.toi.t") 永远返回 None！
# 正确访问方式：d['y']['ps']['toi']['t']（先取 y，再逐层取）
d = r.get("data", [{}])[0]
y = d.get("y", {})
toi = y.get("ps", {}).get("toi", {}).get("t", "N/A")  # 营收
np_ = y.get("ps", {}).get("np",  {}).get("t", "N/A")  # 净利润
ta  = y.get("bs", {}).get("ta",  {}).get("t", "N/A")  # 总资产
tl  = y.get("bs", {}).get("tl",  {}).get("t", "N/A")  # 总负债
se  = (ta - tl) if isinstance(ta, (int,float)) and isinstance(tl, (int,float)) else "N/A"

# 股价历史（逐只，[S]端点）
lx_post("cn/company/candlestick", {
    "stockCode": "600036",
    "startDate": "2024-01-01",
    "endDate": "2025-05-12",
    "adjustmentType": "qfq"  # 前复权
})

# 分红历史（逐只，[S]端点）
lx_post("cn/company/dividend", {
    "stockCode": "600036",
    "startDate": "2020-01-01",
    "endDate": "2025-05-12"
})

# 高管增减持（逐只，[S]端点）
lx_post("cn/company/senior-executive-shares-change", {
    "stockCode": "600036",
    "startDate": "2022-01-01",
    "endDate": "2025-05-12"
})

# 监管措施（逐只，[S]端点）
lx_post("cn/company/measures", {
    "stockCode": "600036",
    "startDate": "2021-01-01",
    "endDate": "2025-05-12"
})
```

### Tavily 网络搜索（治理事件 / 红旗排查）

> ⚠️ **按 0.3 节的 Tier 控制总调用次数。** 以下代码示例已内置分级逻辑。

```python
from scripts.tavily_search import _get_client

client = _get_client()

# ========== Tier 判断（在 0.1 完成后手动填入）==========
# tier = "T0"  # 央企/大型国企 → 上限 1 次
# tier = "T1"  # 大型民企/知名上市公司 → 上限 1 次
# tier = "T2"  # 中型民企/成长股 → 上限 2 次
# tier = "T3"  # 小市值/高风险行业 → 上限 3 次

# ========== 策略A：结构化 API 先行 ====================
# 1. 先调用以下理杏仁 API（均不消耗 Tavily 配额）：
#    - cn/company/measures（监管措施）
#    - cn/company/inquiry（问询函）
#    - cn/company/senior-executive-shares-change（高管增减持）
#    - cn/company/major-shareholders-shares-change（大股东增减持）
# 2. 以上 API 有足够数据 → 可跳过对应维度的 Tavily 搜索

# ========== 策略B/C：合并搜索（T0/T1 只调用此 1 次）==
# 合并覆盖：红旗 + 治理 + 近期事件（F2/F3/F维度 全覆盖）
r1 = client.search(
    f"{公司名} {ticker} 处罚 违规 诉讼 减持 内控 治理 问题 2024 2025",
    max_results=8, search_depth="basic"  # T0/T1 用 basic 节省用量
)

# ========== 策略B：ESG 搜索（仅制造/化工/采矿/重工业，T2/T3）=
# 轻资产/金融/互联网 → 跳过此调用
r2 = client.search(
    f"{公司名} 环保处罚 违规 停产 职业病 工伤 安全事故 整改",
    max_results=8, search_depth="basic"
)

# ========== 仅 T3 追加：深度红旗搜索 ===================
r3 = client.search(
    f"{公司名} {ticker} 减持 大宗 增持 {当前年月}",
    max_results=5, search_depth="advanced"
)
```

**配额使用参考**：

| Tier | 调用方案 | 消耗次数 |
|---|---|---|
| T0 央企/国企 | r1（合并搜索，basic）| **1次** |
| T1 大型民企 | r1（合并搜索，basic）| **1次** |
| T2 中型民企 | r1 + r2（ESG，仅制造类）| **1-2次** |
| T3 高风险/小市值 | r1 + r2 + r3 | **2-3次** |

### 法定披露源

| 用途 | 来源 |
|---|---|
| A 股年报 / 招股书 | 巨潮资讯 cninfo.com.cn |
| 监管公告 | 上交所 sse.com.cn / 深交所 szse.cn |
| 问询函原文 | 理杏仁 `cn/company/inquiry` |
| 历史财报数据验证 | 东方财富 datacenter-web.eastmoney.com |

### 东方财富财报 API（OCF / 历史 ROE 必用）

理杏仁 `fundamental/non_financial` 用年末日期时历史 ROE 返回 None；OCF 字段不在 fs API 中。
**以下场景必须改用东方财富**：

```python
import requests

def ef_financials(code_6):
    """获取A股近期财报（含OCF、ROE），code_6为6位代码如'600900'"""
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        f"?reportName=RPT_LICO_FN_CPD&columns=ALL"
        f"&filter=(SECURITY_CODE%3D%22{code_6}%22)"
        "&pageNumber=1&pageSize=8"
    )
    r = requests.get(url, timeout=10)
    return r.json()["result"]["data"]

# 关键字段说明：
# WEIGHTAVG_ROE      → 加权平均ROE（%）
# MGJYXJJE           → 每股经营活动现金流量（元）← OCF核心字段
# PARENT_NETPROFIT   → 归母净利润（元）
# TOTAL_OPERATE_INCOME → 总营收（元）
# XSMLL              → 销售毛利率（%）
# QDATE              → 报告期（如 "2024Q4" = 年报）
# DATATYPE           → 报告类型文字（如 "2024年 年报"）
# BASIC_EPS          → 每股收益（元）

# OCF计算：总OCF ≈ MGJYXJJE × 总股本（需另行获取股本数）
# OCF质量 = 总OCF / PARENT_NETPROFIT（健康标准 > 1.0；水电/公用事业通常 > 1.5）
```

> ⚠️ **分红单位**：理杏仁 `cn/company/dividend` 的 `dividend` 字段单位是**元/股**（不是"分"）。
> 0.79 = 0.79元/股。`dividendAmount` 是总派现金额（元），需除以1亿换算成亿元。

---

## 常见执行顺序

### 前置：确认 MD 文件可用性

默认先复用共享原件与理杏仁结构化数据；无本地MD时查可访问官方PDF/HTML。完整三件套须能核验决定性原文，必要时获取原件并按项目归档。用户要求转换或原件可读性不足时再运行下载/转换流程，不能因无MD跳过原件核验。

开始分析前，先检查 `财报/[公司名]/` 下是否存在 MinerU 转换的年报/半年报 Markdown：

```bash
ls 财报/[公司名]/*.md
```

若存在，记录可用的年份和报告类型，并在 D 维度（战略执行验证）和 F 维度（审计机构/管理层/关联交易）中优先使用。

若不存在 MD 文件（默认情况），以下维度使用替代数据源：
- **审计意见/审计机构**：巨潮资讯年报摘要首页（cninfo.com.cn）
- **管理层名单**：巨潮资讯年报摘要或东方财富/同花顺高管信息页
- **业务分部收入**：CNINFO API `branch_revenue()` + 理杏仁分部数据
- **D 维度战略验证**：巨潮资讯在线查看年报"管理层讨论与分析"章节 + 券商研报

### 执行步骤

1. **前置排除检查** → 若一票否决则终止；**判断公司 Tier（0.3）→ 确定 Tavily 用量上限**。若有 MD 文件，从 MD 读取审计意见和审计机构（搜索"标准无保留意见"/"会计师事务所"）；若无，从巨潮资讯在线查询。
2. **E维度（先行）**：共享证据/理杏仁取得5–7年或可得完整周期的适用财务指标，缺口用CNINFO/官方原件补充；核对决定性原文与期别后做杜邦及行业适用的财务质量分析。若生成财务全景图，复用这些数据，不再另拉整包。
3. **A维度**：查招股说明书 + 年报历史部分。若 MD 文件覆盖早期年份，可直接读取"公司业务概要"章节。
4. **B维度**：API 毛利率趋势 + **MD 文件**中的"管理层讨论与分析"章节（B1 业务分部、B2 盈利模式、B3 定价权验证）。
5. **C维度**：行业研报 + 理杏仁竞争对手对比。MD 文件中的"行业格局和趋势"章节可作为行业分析的直接引用来源。
6. **D维度**：**核心依赖 MD 文件**。连续 3 年年报 MD 中的"经营情况讨论与分析"对照阅读（战略陈述 vs 实际结果），填写 D2 战略执行验证表。若无 MD 文件，用巨潮资讯在线查看。
7. **F维度**：理杏仁 measures/inquiry/增减持 API **→ 有足够数据则跳过 Tavily；否则按 Tier 执行合并搜索**。**审计机构 + 管理层名单必须从 MD 文件或巨潮年报摘要提取**（防坑10/17），禁止依赖记忆。
8. **汇总评分** → 填写综合评分表 → 交叉验证 API 数字与 MD 原文（若有 MD）→ 写出最终结论
9. **写入公司页** → 提交 git

> ⏱ 预计执行时间：2–3 小时（默认无本地 MD 文件）；有 MD 文件的公司 1.5–2 小时（跳过大量在线查询和巨潮资讯查看时间）

---

<!-- migrated:part-07:end -->
