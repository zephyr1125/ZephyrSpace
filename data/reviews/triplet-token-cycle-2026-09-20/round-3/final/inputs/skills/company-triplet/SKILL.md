---
name: company-triplet
description: 建立、更新或修复A股、港股、美股公司的完整三件套（公司质量、管理层、估值）；承接个股全面分析与买入前尽调。不用于指数/ETF整体估值、行情查询或单纯笔记编辑。
---

# 公司三件套

仓库 `skills/company-triplet/` 是唯一可编辑入口；安装目录仅为联接。启动前运行 `scripts/manage_research_skill_entry.ps1 -Mode Check`；失败先修入口，部署说明见 `docs/research-skill-single-source.md`。

完整研究按 `docs/three-report-economy-routing.md` 执行。该SOP定义固定经济组合、角色读取范围、阶段交接和交付要求；新任务用 `docs/three-report-delivery.md` 的源稿装配流程，历史修复闸门仅供复现；不在本入口重复维护流程。已分派角色只执行当前职责，不递归启动整套。

内容模块由SOP路由至 `deep-prebuy-skill/SKILL.md`、`management-archive/SKILL.md` 和 `skills/valuation/SKILL.md`，不单独安装。旧PreBuy名称统一映射到本入口，不恢复旧流程。

单纯查阅、局部研究或笔记操作保持用户范围，不自动扩成三件套；局部产物标注未完成完整研究。指数筛选与个股研究分开，候选完整研究才走本入口。
