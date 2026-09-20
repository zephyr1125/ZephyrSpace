# 估值：通用约束与计算核心规则：legacy-context

由本模块 SKILL.md 按条件路由；不要求所有角色每次通读。来源优先级、调度、修复轮次、提交和回写权限服从统一 SOP。

历史定位及已被统一 SOP 取代的流程，仅供追溯，不参与执行。

<!-- migrated:part-01:start -->
---
name: valuation
description: >-
  对指定公司执行多方法估值分析（PE分位/PEG/EV-EBITDA/FCF Yield/逆向DCF/SOTP等），
  完成后自动检索 watchlist JSON 文件，若标的存在则更新 target_price，并确保 valuation_certainty 存在，
  并同步到外部 Finance 项目。
  触发词：估值、用合适算法估值、给XX估值、valuation。
  适用市场：A股、港股、美股。
---

## 内部模块与唯一真值

本文件仅作为仓库 `skills/company-triplet/SKILL.md` 的内部内容规范，不再作为独立安装技能。作者直接读取此仓库原件；不得维护 `.agents/skills/` 下的模块副本。下文旧“单独执行/启动”描述不构成独立入口；本项目个股研究统一由company-triplet调度，局部追问不扩大范围。

## 三件套经济组合（ZephyrSpace）

默认触发语：用户说“三件套分析XXX”（XXX为公司名称或代码）、“分析XXX三件套”或“对XXX做三件套”时，直接执行本经济组合，无需附加“使用经济组合”，也不再次询问模型组合；只有用户明确指定其他组合时才覆盖默认。

在ZephyrSpace内，完整三件套、整套更新或修复以项目 `docs/three-report-economy-routing.md` 为唯一调度真源，并读取 `docs/three-report-evidence-contract.md`。固定角色与模型配置不变；执行准入闸门、共享证据、轻量盲审清单、完整双路复核、一次合并修复和一次定向复查，例外与停止条件按SOP。两路第二阶段仍完整覆盖三份报告；不得各skill重复启动审核或全平台重抓证据。第一阶段不接触作者/准入评价及初稿。
原有研究检查项、P0/P1关闭、完整报告篇幅、历史留存及Watchlist入库条件继续有效。完整三件套范围内的无条件重审与“每次拉全源”指令由SOP及证据规范替代；反向验证不参加估值加权。子Agent只完成分派角色；主对话串行回写，有新证据或未关闭重要问题按SOP复裁，不能靠轮次上限判定通过。
仅作三件套内部内容模块，相关数据获取遵循证据规范，按适用市场/行业回退。其他项目不加载本项目配置。目标模型不可用时报告未完成，不静默替换；实际模型无运行时证据则记未验证。已运行任务不自动切换。DeepSeek仅在用户明确要求试验时读取 `docs/deepseek-review.md`，不替换默认双复核。


# 估值分析（多方法 + Watchlist 联动）

<!-- migrated:part-01:end -->
