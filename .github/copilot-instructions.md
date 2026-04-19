# Copilot Instructions — ZephyrSpace

本仓库是一个 Obsidian vault，用于构建商业航天研究知识库。默认使用简体中文回复与注释。

详细协作约束见 `AGENTS.md`，此处不重复，仅补充 Copilot 特有的上下文。

## 架构概览

### 知识库层级

- **公司页**（`01-公司/`）是核心实体，每页包含 frontmatter 元数据 + 结构化正文区块，必须链接至少 1 个主题页和 2 个相关公司页。
- **主题页**（`02-主题/`）只做导航和聚合，不重复公司页正文。
- **日报**（`90-日报/`）是自动化输入层，不代表长期结论，不自动回写公司页。
- **个人观察**（`99-个人观察/`）与可公开研究内容严格分层。

### 日报自动化流水线

```
industry_sources.json → fetch_industry_news.py → classify(news_rules.json) → generate_daily_report.py → Obsidian CLI create
```

- `fetch_industry_news.py`：从 RSS 源抓取新闻，按 `news_rules.json` 中的公司关键词归类，翻译标题/摘要并缓存。
- `generate_daily_report.py`：调用上述模块构建日报 Markdown，通过 Obsidian CLI 的 `create` 命令写入 vault。
- `fetch_company_updates.py`：独立的公司级抓取器，支持 RSS、HTML scraping、Launch Library 2 API 等多种 `source_type`。
- `generate_daily_report.ps1`：PowerShell 入口，供 `.cmd` 快捷方式调用。

入口快捷方式：

- `生成今日日报.cmd` — 不覆盖已有日报
- `覆盖生成今日日报.cmd` — 强制覆盖

### 配置驱动

新增公司或调整归类规则时，修改 JSON 配置而非硬编码脚本：

- `data/sources/industry_sources.json` — 行业 RSS 源
- `data/sources/company_sources.json` — 公司级数据源（含 `source_type` 分发）
- `data/classification/news_rules.json` — 公司关键词 + 宏观关键词 + 主题映射

## 运行命令

### 生成日报

```powershell
# 生成今日日报（不覆盖）
.\scripts\generate_daily_report.ps1

# 指定日期并覆盖
.\scripts\generate_daily_report.ps1 -Date "2026-04-18" -OverwriteExisting

# 直接用 Python
python .\scripts\generate_daily_report.py --vault-name ZephyrSpace --date 2026-04-18
```

### 单独抓取新闻（不写入 vault）

```powershell
python .\scripts\fetch_industry_news.py --date 2026-04-18 --output-format json
python .\scripts\fetch_industry_news.py --date 2026-04-18 --output-format markdown
```

### Obsidian CLI

```powershell
obsidian create vault=ZephyrSpace path="01-公司/Example.md" content="..."
obsidian read vault=ZephyrSpace path="01-公司/SpaceX.md"
obsidian property:set vault=ZephyrSpace path="01-公司/SpaceX.md" property=关注级别 value=核心
```

## 关键约定

### 公司页 frontmatter

必须包含：`aliases`、`国家`、`类别`、`细分赛道`、`可投资性`、`阶段`、`关注级别`、`最后更新日期`。

### Git

- Commit message 格式：`<type>: <简体中文 subject>`
- `type` 限定：`feat` / `fix` / `refactor` / `docs` / `chore` / `style` / `test`
- 不提交 `.obsidian/workspace.json`、缓存、日志等临时文件。

### 决策优先级

1. 知识库结构清晰
2. 日报自动化稳定
3. 内容可长期积累、未来可发布
4. 功能扩展与视觉优化

### 禁止项

- 不自动改写公司主页面
- 不给出买入/卖出建议
- 不批量重命名目录或重写信息架构
- 单条翻译/抓取失败不得阻塞整份日报生成
