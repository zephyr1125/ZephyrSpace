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

- [[00-首页/公司页模板（A股PreBuy）]]（仅沿用历史页面格式，不调用PreBuy技能）

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

### 三件套固定经济组合

个股三件套新建、整套更新及修复统一从 `skills/company-triplet/SKILL.md` 进入，按 `docs/three-report-economy-routing.md` 调度固定经济组合及独立双复核。用户指定组合优先；局部请求不自动扩展，已分派角色不递归启动。模型、读取范围、证据、验收和异常收尾仅在SOP及其链接文件维护，不按日期在此重复追加。

最终总分按 `docs/three-report-closeout.md` 显示整数；分项、底稿与门槛继续用原始分。主任务在验收后串行回写公司页、索引及Watchlist，沿用下文完整性、版本与入库授权。

### 三件套文档完整性（强制）

完成“三件套分析”时，研究文档必须能够支持未来独立复核，禁止以摘要代替报告：

- `深度分析/`：不少于 **150 行**；必须覆盖商业模式、行业与护城河、至少三年或可得完整周期的经营数据、财务/资本质量、关键风险、事实/推断/未知、反证条件和来源。
- `管理层档案/`：不少于 **150 行**；必须覆盖控制结构、核心管理层和治理机制、资本配置、股东回报、关联交易/激励、历史执行证据、降级触发条件和来源。
- `估值分析/`：不少于 **100 行**；必须覆盖适合行业属性的估值方法、完整假设、至少三种情景、敏感性、估值交叉验证、统一公式下的机械买入价、价格分区、反证及来源。
- 金融、保险、交易所、上游资源等行业须使用其经济本质对应的指标和模型；不得套用制造业 OCF/净利或传统 FCF 框架。
- **入库前置条件**：三份报告、公司页和索引均已完成且通过自检后，才可写入 Watchlist；不完整时只可报告“研究未完成”，不得写入或同步。

用户明确要求压缩版，或依统一SOP准入闸门核实排除的新候选，可以突破篇幅下限，但必须在文档首部标注“压缩版，未完成完整三件套”；闸门退出不宣称完成双复核，不写入/同步Watchlist。进入完整流程后仍须满足上述篇幅与内容下限。

### 三件套版本留存（强制）

- 财报发布、重大事实变化或评分复核后更新三件套时，**不得直接覆盖历史报告**。
- 必须分别新建 `深度分析/`、`管理层档案/`、`估值分析/` 文件；文件名必须包含更新后的评分（适用时）与更新日期，例如：`潍柴动力 深度分析 69 2026-08-27.md`。
- 新报告须明确写明基于何期财报、相对上一版的评分和结论变化；旧报告保留，作为当时信息集的历史快照。
- 公司页及新报告之间的链接应切换到最新三件套；不得修改旧报告中的历史结论来追溯性改写当时判断。

### MinerU 财报归档（强制）

- MinerU 转换结果必须写入 `财报/[公司名]/`，不得写入 `E:\Download`、临时目录或 Vault 根目录。
- 主 Markdown 命名为 `[公司名][报告期].md`，图片目录命名为 `[公司名][报告期]_images/`，与现有财报结构保持一致。
- `content_list*.json`、`middle.json`、`model.json`、`layout.pdf`、`span.pdf` 等可复核辅助产物放入 `财报/[公司名]/[公司名][报告期]_mineru/`；不得丢弃。
- 更新研究文档时，引用转换稿必须使用 Vault 内 `财报/` 路径，禁止保留 `E:\Download\MinerU` 等临时路径。

watchlist 数据采用 core/growth 两档，放在 `data/` 目录：

| 文件 | 内容 | 大小参考 |
|---|---|---|
| `watchlist_meta.json` | schema、必填字段、档位定义、周期枚举等精简元数据 | ~5KB |
| `watchlist_core.json` | core tier 数组（核心池，约 13 家） | ~15KB |
| `watchlist_growth.json` | growth tier 数组（成长池，约 61 家） | ~72KB |

**读写规则（重要）**：
- 新增/更新公司时，**只改对应 tier 的文件**，不碰其他文件
- 读取 `AGENT_INSTRUCTION`、`required_fields`、`tier_definitions`、`cycle_positions` 时，读 `watchlist_meta.json`
- 每次修改后，运行 `.\scripts\sync_watchlist.ps1` 同步到外部项目

> ✅ **自动入库授权**：只要完整三件套复核结论满足 `S_STRATEGIC`、`A_CORE` 或 `B_GROWTH` 任一档位的全部硬门槛，且未触发重大红线，主 Agent 应自动写入对应 Watchlist 文件，无需逐家公司再次确认。
>
> **正确流程**：
> 1. 子 Agent 仅完成研究、输出建议档位和字段值，**不得直接写入** Watchlist；
> 2. 主 Agent 复核分数、红线、必填字段及最高满足档位；
> 3. 符合任一档位时，主 Agent 自动写入对应文件，运行 `validate_watchlist.py` 后再运行 `sync_watchlist.ps1`；
> 4. 不满足档位或存在待核实重大红线时，不写入，并在结论中明确原因。
>
> 多个 Agent 并发写同一文件会导致内容互相覆盖、数据丢失；因此 Watchlist 写入仍只允许由主 Agent 串行执行。

**在修改任何 watchlist 文件之前，必须**：

1. 阅读 `watchlist_meta.json` 中的 `AGENT_INSTRUCTION`、`required_fields`、`tier_definitions`、`cycle_positions`
2. 新研究只收录已完成完整三件套分析的公司（`01-公司/` 下有对应页面）
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
2. **拉取财报数据**：优先理杏仁 `cn/company/fs/non_financial`（`date` 参数传最近年末日），**若返回期别落后于预期，必须用东方财富 web_fetch 外部验证**（见下方财报数据规范）
3. **更新公司页**：在 `## 已核实的关键事实` 或 `## 季度财报跟踪` 区块添加新一期数据，更新 `## PreBuy 结论` 加 `[Qx YYYY已验证]` 标注
4. **治理事件检查（必选步骤）**：每次季报更新时，必须同步用 Tavily 搜索近期治理事件，不可仅依赖理杏仁：
   ```python
   from scripts.tavily_search import _get_client, _fmt
   client = _get_client()
   result = client.search(f"{公司名} {ticker} 减持 大宗 增持 {当前年月}", max_results=5, search_depth="advanced")
   ```
   > ⚠️ **已踩坑**：理杏仁 `cn/company/senior-executive-shares-change` 接口存在数据盲区，对部分公司返回空数据而实际存在减持记录（实例：大豪科技 2026年3月集中减持被漏检）。**"接口返回空"≠"无减持"**，必须通过 Tavily 或东方财富公告二次确认。
   > 搜索结果若发现：① 大股东/高管减持公告、② 集体减持计划、③ 权益变动触及1%提示公告 → 须更新公司页"主要红旗"和"A股特有风险检查"表，并评估对 PreBuy 结论的影响。
5. **更新 watchlist JSON（必须同时更新以下两个字段，缺一不可）**：
   ```json
   "next_earnings_type": "半年报",
   "next_earnings_date": null
   ```
   > ⚠️ **`null` 规则（强制）**：若无法从公司官方公告确认具体财报日期（董事会会议通知等），`next_earnings_date` 必须写 `null`，禁止用交易所法定截止日（`08-31`/`04-30`/`10-31`）填充。`null` = 待后续通过搜索/Tavily 确认真日期后再补。
   > ⚠️ **已踩坑**：只更新了 `next_earnings_type`，漏掉 `next_earnings_date`，会导致 Watchlist 视图仍显示旧的财报日期。两个字段必须在同一个脚本里一并更新。
5. 将最新季报简评保留在公司页；Watchlist 不再保存 `prebuy_conclusion`
6. **运行 `sync_watchlist.ps1`** 同步

**A股季报 → 下一期类型参考**（`next_earnings_date` 一律写 `null`，待公司官方公告确认后再补）：
| 当前类型 | 改为 `next_earnings_type` | `next_earnings_date` |
|---|---|---|
| 一季报 (3月) | 半年报 | `null`（待确认） |
| 半年报 (6月) | 三季报 | `null`（待确认） |
| 三季报 (9月) | 年报 | `null`（待确认） |
| 年报 (12月) | 一季报 | `null`（待确认） |

**子 Agent 季报更新分工**：
- 子 Agent 职责：更新公司页（含财报数据 + 治理事件检查），输出建议的 watchlist 字段更新（key-value 格式）
- 主 Agent 职责：汇总子 Agent 结果，写入 watchlist JSON（子 Agent 不得直接写文件）

---

### 财报数据规范（理杏仁 + 东方财富备用）

> ⚠️ **理杏仁与东方财富财报数据均可能存在延迟**（通常滞后1-3天，有时更长），必须验证期别后再使用。

**验证规则**：
1. 用理杏仁 `cn/company/fs/non_financial` 拉取后，检查返回的最新期别是否符合预期（用 SKILL 中的 `expected_latest_qdate()` 函数推算应有的最新报告期）
2. **不符合预期时，用东方财富 web_fetch 外部验证**：
   - A股：`https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE%3D%22{6位代码}%22)&pageNumber=1&pageSize=3`
   - 关注字段：`ISNEW="1"` + `QDATE`（如 `"2026Q1"`）+ `REPORTDATE`（如 `"2026-03-31"`）
   - 美股/港股：`https://stockanalysis.com/stocks/{ticker}/financials/?p=quarterly`
3. 若理杏仁与东方财富同口径数据不一致，暂以东方财富作校验并记录差异，最终回到公司官方披露原件；决定性冲突未解不进入正式估值。统一规范见 `docs/three-report-evidence-contract.md`

**Q1 ROE 低估陷阱**（与数据源无关，季报更新时同样适用）：

在季报更新时，若取 Q1 季报的 ROE 字段用于 prebuy_conclusion 描述，需注意：
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
| 财报期别验证（理杏仁延迟时）| **web_fetch** 东方财富 | 已知 URL，直接验证 QDATE |

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

### 三件套流程中的嵌入点

在Terra共享证据整理阶段，按三件套证据规范处理：
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

## 研究技能唯一真值

仓库是唯一可编辑源。仅安装一个研究入口 `company-triplet`，生效路径 `C:/Users/zephy/.agents/skills/company-triplet/` 必须为指向本仓库 `skills/company-triplet/` 的目录联接；禁止维护独立副本或双向合并。

深度分析 `deep-prebuy-skill/SKILL.md`、管理层 `management-archive/SKILL.md` 和估值 `skills/valuation/SKILL.md` 是仓库内的内容模块，由三件套直接读取，不再单独安装。历史目录名不代表继续使用PreBuy。A股/港股/美股旧PreBuy入口全部退出发现目录；旧源码、历史报告和目录外备份仅供追溯，不参与执行。

每次修改入口/内部模块/关联规则后运行：

```powershell
.\scripts\manage_research_skill_entry.ps1 -Mode Check
```

首次部署或发现副本漂移时，先审查差异并将需要保留的内容合并到仓库唯一源，再执行 `-Mode Install`；脚本备份旧目录到技能发现范围之外并建立唯一联接。禁止复制SKILL.md、只同步部分段落或直接编辑生效路径；联接使正文和附录均即时读取仓库文件。

部署与已知旧版差异见 `docs/research-skill-single-source.md`。其他无关技能不在本迁移范围。

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

## 研究请求路由

- 个股“三件套”“全面分析”“买入前尽调”及旧“PreBuy”说法，统一读取 `skills/company-triplet/SKILL.md`，不再调用任何PreBuy技能。
- “选股 [指数]”仍以成分股筛选为对象，主Agent完成全成分与期别验证；通过筛选的候选逐家走三件套，不能用旧PreBuy直接入库。筛选本身不等于完整研究，不因市值权重直接取前十。
- “指数估值/ETF是否值得买”是指数整体问题，不能机械套用单公司三件套；按用户限定的指数范围分析，目标不清时先厘清，不再加载 `index-prebuy.skill`。
- 仅查资料、解释报告、修改笔记等操作保持用户原范围，不自动扩成新研究。用户明确要求局部研究时标注未完成完整三件套，不恢复旧PreBuy流程。
- 旧PreBuy SOP与旧单分入池速查已移到 `docs/archive/legacy-prebuy-workflows-2026-09-11.md`，仅为历史留档，不能执行。新研究以三件套SOP与当前Watchlist分级规则为准。

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
