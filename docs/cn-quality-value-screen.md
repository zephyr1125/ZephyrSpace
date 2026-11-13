# A股新候选筛选入口

仓库入口：`skills/cn-quality-value-screen/SKILL.md`。本地发现目录 `C:/Users/zephy/.codex/skills/cn-quality-value-screen` 使用目录联接指向仓库源，修改仓库源即可生效。

“查找错杀A股好公司”默认寻找新研究候选。每轮读取 `data/watchlist_core.json` 和 `data/watchlist_growth.json`，按代码排除全部已入池A股公司；最终候选、重点推荐与后续研究批次都不得包含这些公司。历史底稿重用同样适用。

排除按公司主体跨市场执行：调用 `_load_watchlist_cn(universe)` 时传入全A公司清单，匹配所有市场Watchlist名称。港股东鹏饮料入池即排除A股东鹏饮料；官方别名或名称差异须核实映射，不将母子公司视为同一主体。

`scripts/cn_mispricing_screen.py` 默认执行排除，`--skip-watchlist` 仅作为旧调用的兼容参数保留。Watchlist读取失败时停止，不降级为空集合。筛选只读Watchlist，不触发同步。

修改入口后运行 skill-creator 的 `quick_validate.py`；脚本验证包括代码归一化、跨档去重、缺失/异常文件停止以及最终候选无交集。质量与回撤计算的已知局限见技能正文。
