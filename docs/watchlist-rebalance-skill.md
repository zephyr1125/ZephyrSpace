# Watchlist 存量调仓技能

创建日期：2026-09-16。

入口为仓库 `skills/watchlist-rebalance/SKILL.md`，本地发现路径 `C:/Users/zephy/.codex/skills/watchlist-rebalance` 以目录联接指向此目录，维护仓库唯一源。

默认提示词及调用示例：“检查当前调仓机会”。

市场范围：仅A股和港股。2026-09-16用户明确整个技能完全不用管美股；加载Watchlist即过滤，不拉取美股行情、不核美股持仓、不评分、不做资金配对。

用户确认：高估三档与更优的低估替代机会必须同时成立才卖出；“更优”以公司分、管理层分和价格吸引力加权统一比较，低估一档也可触发换仓，不再使用先前的二档门槛。具体权重与价格刻度保存在技能 `rules.json`，确认状态也在该文件记录。分档资金为累计目标市值，扣除已有市值补足。成长 1/2/3 万、核心 2/4/6 万、战略 4/8/12 万，统一人民币。七档公式与边界来自 Finance 个股追踪模块。

技能只生成私人方案，不改 Watchlist、Google 表或 Finance，不下单。不另加外部资金，默认仅以本次合格卖出净额筹资。完整流程、数据接入、异常处理与核算约束见技能正文和其引用文件。

验证命令：

```powershell
python -X utf8 C:/Users/zephy/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/watchlist-rebalance
python -X utf8 -m unittest discover -s skills/watchlist-rebalance/scripts -p 'test_*.py'
python skills/watchlist-rebalance/scripts/calculate.py --price 59 --target 100 --certainty 0.5 --level A_CORE --holding-cny 25000
.\scripts\manage_research_skill_entry.ps1 -Mode Check
```

创建时只校验技能与离线计算，不代表已读取实时持仓或完成当日调仓分析。实际使用需重新获取行情、Google 持仓与汇率，并核实交易单位及费用。
