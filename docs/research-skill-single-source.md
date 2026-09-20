# 研究技能唯一真值与入口退役

2026-09-11起，本项目只使用 `company-triplet` 作为个股研究入口。仓库是唯一可编辑真值，生效目录仅提供路径联接；旧PreBuy与三个模块的安装副本全部退出技能发现范围。

## 有效文件

| 职责 | 唯一源 |
|---|---|
| 可发现的研究入口 | `skills/company-triplet/SKILL.md` |
| 调度 | `docs/three-report-economy-routing.md` |
| 数据/证据规范 | `docs/three-report-evidence-contract.md` |
| 公司质量内容模块 | `deep-prebuy-skill/SKILL.md` |
| 管理层内容模块 | `management-archive/SKILL.md` |
| 估值内容模块 | `skills/valuation/SKILL.md` |
| 公司页收尾/市场检查 | `docs/three-report-company-page.md` |
| 固定角色配置 | `.codex/agents/triplet_*.toml` |
| 底稿、自检与中间产物格式 | `docs/three-report-workpaper.md`、`scripts/triplet_workpaper.py` |
| 2026-09-19规则迁移定位 | `docs/three-report-rule-migration.json` |
| 明确处置、防回退与真实计量 | `docs/three-report-closeout.md`、`scripts/triplet_run_audit.py` |

`C:/Users/zephy/.agents/skills/company-triplet/` 使用Windows目录联接指向仓库入口目录。它与仓库读取的是同一份文件，正文及附录不需要复制同步。三个内部模块直接从仓库读取，历史目录名deep-prebuy-skill保持兼容，不表示恢复PreBuy。

2026-09-19起，三个内容模块保留核心规则，数据接口、输出示例、历史案例及行业专属说明移到各模块自己的 `references/`。全部原段落按迁移清单保留并可重建校验，旧调度段落仅供追溯。入口Check同时检查清单中所有附件存在；新增任务按核心中的触发索引读取，不能只复制SKILL.md而漏掉附件。质量门槛、评分标准与模型组合保持不变；工作底稿用于减少重复计算和返工，不替代独立核验。

## 差异裁定

迁移前已核对完整目录及非正文资源。深度分析生效副本是较早的简化版本，缺少仓库中的D2长期兑现率、E5.5会计政策审计、F2.5资本配置、廉洁历史检查及评分文件名规范，并使用旧E/F子项权重。本次采用仓库已有完整版本及本轮六项经济调整；旧副本没有需要另行合并的新研究要求。新规则只作用于未来研究，不追溯覆盖历史报告或改写已有评分。

PreBuy来源附录也存在仓库比安装版更完整的差异；由于PreBuy已退役，保留仓库历史源码及目录外原副本，不重新启用该附录作为新流程入口。其市场风险覆盖由公司页收尾规范承接。

## 安装与检查

```powershell
# 已审查差异后执行，旧普通目录移到发现范围外备份。
.\scripts\manage_research_skill_entry.ps1 -Mode Install

# 每次修改入口/模块/相关规则后及三件套启动前执行。
.\scripts\manage_research_skill_entry.ps1 -Mode Check
```

检查要求：唯一company-triplet入口是正确目录联接，读取内容一致，两个已知用户技能目录中均无stock-prebuy-review、hk-prebuy、us-stock-prebuy、deep-company-review、management-archive、valuation的独立入口，也没有第二个company-triplet入口。

安装脚本只处理列明的目录，不动其他技能。默认备份根为 `C:/Users/zephy/.agents/skill-retirement-backups/`，每次迁移使用独立目录；备份仅作历史恢复，不参与技能发现。未知联接或目标异常时停止，先查明而不强制覆盖；迁移失败时尽可能恢复原目录且不覆盖并发修改。

仓库移动或驱动器不可用会使入口失效，应更新部署目标与入口定位后重新检查；不得为绕过失败复制一套新权威文件。已打开任务中的旧指令快照不靠移动文件追溯改变，新任务读取统一入口。

## 停用范围

- A股、港股、美股PreBuy不再作为独立技能，旧“全面分析→单报告审核→PreBuy→入池”流程停用。
- 旧PreBuy源码、打包文件及 `index-prebuy.skill` 仅作历史留档，不删除研究报告；旧SOP见 `docs/archive/legacy-prebuy-workflows-2026-09-11.md`。
- 深度/管理层/估值仍参与完整三件套，但不独立安装、调度或维护副本。
- 纯行情、资料检索、笔记编辑及其他无关技能不受此迁移影响。指数/ETF整体问题不自动拆为个股研究，也不恢复旧PreBuy。

## 本次迁移验证

2026-09-20提示词去重与整数总分显示见 `docs/three-report-prompt-refactor-2026-09-20.md`；调度继续仅以三件套SOP为准。维护记录不属于每家公司研究输入。

- 2026-09-11已安装唯一目录联接；仓库入口与生效入口的文件ID一致，验证为同一物理文件。
- 六个旧入口目录均已移出发现范围，原件备份在 `C:/Users/zephy/.agents/skill-retirement-backups/20260911-201249-a685d769/`；其中三个为已退役PreBuy，三个为不再独立安装的内部模块。
- 隔离目录验证已覆盖：旧副本检查失败、首次迁移、迁移后检查、重复安装幂等；实际目录检查与技能格式检查通过。
- 本次只统一研究入口和规则，未重跑历史研究、重算评分或改写Watchlist数据。
