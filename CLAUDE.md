# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

这是 ZephyrSpace 个人股市研究知识库，基于 Obsidian vault 构建。核心功能：
- A股/美股/港股标的 PreBuy 分析与 watchlist 管理
- 行业指数研究（成分股粗筛 + 深度 PreBuy）
- 商业航天研究（原有模块，现为子主题）

## 核心目录结构

| 目录 | 用途 |
|---|---|
| `01-公司/` | 公司实体页（知识库核心），每页含 frontmatter 元数据 + 结构化正文 |
| `02-主题/` | 主题导航页，仅做聚合和导航，不重复公司页正文 |
| `05-A股指数/` | A股指数专题页，含指数整体 PreBuy 结论 |
| `90-日报/` | 自动化生成的日报，不代表长期结论 |
| `99-个人观察/` | 私人判断和草稿，与公开研究内容严格分层 |
| `data/` | watchlist JSON、分类规则、缓存 |
| `scripts/` | 日报抓取/生成脚本、PreBuy 数据拉取脚本 |

## 主要工作流程

### 日报生成

```powershell
# 生成今日日报（不覆盖已有）
.\scripts\generate_daily_report.ps1

# 指定日期并覆盖
.\scripts\generate_daily_report.ps1 -Date "2026-04-18" -OverwriteExisting

# 直接用 Python
python .\scripts\generate_daily_report.py --vault-name ZephyrSpace --date 2026-04-18
```

### 财报下载（触发词：下载财报 [股票代码]）

**不需要二次确认，收到即执行。** 按年报5-7年+半年报2-3年+季报窗口补位的规则，从巨潮资讯自动下载财报PDF到 `财报/_Inbox/`。

```powershell
# 单只股票
python .\scripts\download_reports.py 600519

# 多只
python .\scripts\download_reports.py 600519 600276 300750

# 仅预览
python .\scripts\download_reports.py 600519 --dry-run
```

下载规则：
- 年报：回溯 7 年（D2 兑现率追踪 / F2 资本配置跨周期 / E5 会计政策逐年查）
- 半年报：回溯 3 年
- 季报：仅当最新已发布报告是 Q1/Q3 时补位下载
- 命名格式：`财报/_Inbox/[公司简称]_[年份]_[报告类型].pdf`

### 财报 PDF 转换（触发词：转换财报）

**不需要二次确认，收到即执行。** 将 `财报/_Inbox/` 中的原始财报 PDF 使用 MinerU 批量转换为结构化 Markdown。

```powershell
# 仅转换已有PDF
python .\scripts\convert_annual_reports.py
```

### 财报下载+转换（触发词：下载并转换 [股票代码]）

**不需要二次确认，收到即执行。** 下载财报PDF后立即转入MinerU转换，一条龙完成。

```powershell
python .\scripts\download_reports.py 600519 && python .\scripts\convert_annual_reports.py
```

### 指数成分股 PreBuy 分析（触发词：选股 [指数名]）

完整 SOP 在 `AGENTS.md`，执行摘要：

1. 在 `05-A股指数/` 建立指数专题页（使用模板）
2. 拉取全成分股 → 量化粗筛（四条硬门槛：市值、ROE/股息率、营收同比）
3. 对候选公司创建/更新 `01-公司/` 页面，执行完整 PreBuy 分析
4. 按 `data/WATCHLIST_RULES.md` 决策：core / growth / radar / 不入
5. 写入 watchlist JSON（主 Agent 执行，子 Agent 不得直接写文件）
6. 运行 `sync_watchlist.ps1` 同步到外部项目

### 全面分析 [公司名]（触发词：全面分析 XXX）

**不需要二次确认，收到即执行。** 完整 6 步 SOP 必须读取 `deep-prebuy-skill/SKILL.md`，流程顺序：

**前置步骤：先跑「下载并转换」**，等所有财报 PDF 全部转换为 MD 后，再开始写深度分析。禁止在财报转换完成前开始写分析。

1. 深度分析 → 输出 `深度分析/[公司简称] 深度分析 YYYY-MM-DD.md`（100分制评分）
2. 双 Agent 审核（逻辑 + 数据一致性）
3. P1 修复（含评分联动检查，见坑15）
4. PreBuy 公司页（引用修复后深度分析评分）
5. Watchlist 写入（主 Agent 执行，先向用户确认档位）
6. `sync_watchlist.ps1` + 清理临时文件 + Git Commit（最多3次）

> ⚠️ 深度分析 Tavily 用量按 `deep-prebuy-skill/SKILL.md` 第 0.3 节 Tier 分级管控（央企上限1次，大型民企1次，中型2次，小市值/高风险3次）。
> ⚠️ 分析完成后必须用财报 MD 文件复核关键数据（审计意见、管理层名单、业务分部收入），不能仅依赖 CNINFO API。

### 周度监控（触发词：监控周报 / 扫描持仓 / 周报）

**不需要二次确认，收到即执行。** 对 Watchlist 全部标的拉取最近一周公告+高管变动+处罚诉讼+业绩预告，AI 逐条分析过滤，输出 actionable 周报。

```powershell
# 第1步：数据拉取（脚本自动完成）
python scripts/weekly_watchlist_scan.py

# 第2步：AI 分析 + 生成报告（按 skills/weekly-watchlist-monitor/SKILL.md 执行）
```

报告输出到 `02-主题/周度监控/YYYY-MM-DD.md`。AI 分析按三档分级：🔴 CRITICAL（需行动）/ 🟡 WATCH（需关注）/ ⚫ IGNORE（流程性）。

### 指数整体 PreBuy（触发词：指数估值 [指数名] / [指数]适合建仓吗）

完整 SOP 在 `index-prebuy.skill`，分析对象是指数本身（不拆解个股），输出到指数页 + `data/watchlist_index.json`，并在写入后运行 `.\scripts\sync_watchlist.ps1` 同步到 `E:\Work\Python\Finance\api\config\watchlist_index.json`。

## Watchlist 管理

三档分层：core（底仓）/ growth（成长）/ radar（跟踪）
- 档位由基本面质量决定，与当前股价无关
- 子 Agent 完成 PreBuy 后输出「建议档位：xxx」，**不写文件**
- 主 Agent 汇总后向用户确认，确认后一次性写入

**关键文件**：`watchlist_core.json`、`watchlist_growth.json`、`watchlist_radar.json`、`watchlist_meta.json`（元数据 + tier 定义）

修改任何 watchlist 文件前必须阅读 `data/WATCHLIST_RULES.md`。

## 网络搜索：Tavily

**Tavily 可用**，API Key 在 `.env` 中为 `TAVILY_KEY`，工具模块：`scripts/tavily_search.py`。

```python
from scripts.tavily_search import prebuy_web_research, search_red_flags

# PreBuy 一次性调研（红旗 + 近期事件 + 公司信息）
result = prebuy_web_research("东方财富", "300059.SZ")
# result["red_flags"] → 监管处罚/诉讼/负面事件
# result["recent_news"] → 公告/并购/管理层变动
# result["company_info"] → 主营业务/竞争格局
```

**规则**：Tavily 用于不确定 URL 的发现性搜索；财务数据验证（东方财富/stockanalysis 等已知 URL）继续用 `web_fetch`。

## tushare 数据陷阱（常见）

1. `fina_indicator` limit=1 返回最新一期（可能是 Q1 季报），Q1 ROE 被系统性低估（只有年化 1/4）
   → 优先取 end_date 以 1231 结尾的年报数据
2. `index_weight` 返回历史所有期，必须过滤 `trade_date == max`
3. `total_mv` 单位是**万元**，转亿需除以 10000
4. `daily_basic` 多只逗号分隔批量调用返回空 DataFrame，必须逐只调用

## Obsidian CLI 常用命令

```powershell
obsidian create vault=ZephyrSpace path="01-公司/Example.md" content="..."
obsidian read vault=ZephyrSpace path="01-公司/SpaceX.md"
obsidian property:set vault=ZephyrSpace path="01-公司/SpaceX.md" property=关注级别 value=核心
obsidian links vault=ZephyrSpace
obsidian orphans vault=ZephyrSpace
```

## GitHub Pages 信息图部署

`public/` 目录含自包含单文件 HTML 信息图，部署到 `space-research` 仓库：

```powershell
.\scripts\deploy_pages.ps1
# 或: git subtree push --prefix=public pages main
```

设计系统：背景 `#f5f0e6` + teal 主色 `#0e7490`、蓝色 `#2563a0`、琥珀色 `#c2770c`；字体 Newsreader/Noto Sans SC/JetBrains Mono。

## Commit 规范

- message 格式：`<type>: <简体中文 subject>`
- type：`feat` / `fix` / `refactor` / `docs` / `chore` / `style` / `test`
- 不提交 `.obsidian/workspace.json`、缓存、日志等临时文件
