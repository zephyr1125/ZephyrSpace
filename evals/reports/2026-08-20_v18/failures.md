# Failures

## management_archive_001 (PASS)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 福耀玻璃 深度分析 88 2026-05-17.md 未引用本管理层档案
- [P2] ANALYSIS_UNCERTAINTY: [management_archive_001] uncertainty 分析质量 2/5 偏低：未见信息不足标注，存在强推结论风险
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："美国反倾销指控不成立，福耀将全力应诉"
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 可转债, H股, 优先股（可能遗漏摊薄工具）
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件："2026 年预计资金需求 498.62 亿元——其中经营性支出 390 亿、资本支出 77.3 亿、分红 31.32 
- [P1] FACT_MANAGEMENT_TURNOVER: [M8] 检测到短期密集离任 {'2025': 2} 但正文未识别该模式（或否认）

## management_archive_002 (FAIL)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 腾讯控股 深度分析 83 2026-05-13.md 未引用本管理层档案
- [P1] FACT_CAPITAL_ACTION: [management_archive_002] 回购实际金额 None 未在档案中出现
- [P2] ANALYSIS_UNCERTAINTY: [management_archive_002] uncertainty 分析质量 2/5 偏低：未见信息不足标注，存在强推结论风险
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："回购计划将大幅扩大"
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："FY2026 AI投资将比FY2025翻倍以上"
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："FY2026回购将低于FY2025"
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 可转债, H股, 优先股, 股权激励（可能遗漏摊薄工具）
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件："腾讯将AI视为转型性力量，一方面强化现有业务，另一方面积极开发新的AI产品。" —— Q4 2025 电话会总结（20
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件："AI应用于现有业务已看到良好ROI；新AI产品将先投入后产生收入，类似腾讯云的发展路径。" —— Q4 2025 电话
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件："2026年回购股份的价值将低于2025年，以资助AI投资。" —— Q4 2025 电话会业绩指引
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件："提议年度股息为每股5.3港元，同比增长18%。" —— Q4 2025 电话会
- [P1] WORKFLOW_MISSING_TIMELINE: [M8] 高管变动时间线记录不足（仅 0 行），无法判断稳定性

## management_archive_003 (PASS)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 美的集团 深度分析 81 2026-06-28.md 未引用本管理层档案
- [P2] SCORE_INCONSISTENCY: 总分 87（>=85）但结论定位为'需要持续跟踪'，建议复核
- [P2] SCORE_INCONSISTENCY: [calibration.conclusion_type] 总分 87（>=85）但结论定位为'需要持续跟踪'，建议复核
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标：管理层关键承诺/说法（原文摘要）
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 优先股（可能遗漏摊薄工具）
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件："美的正从传统家电企业转型为全球性工业科技集团。2B业务2025年已贡献27%收入，目标2030年提升至33%。" ——

## management_archive_004 (FAIL)
- [P2] FORMAT_TICKER_FORMAT: [structure.ticker_format] 股票代码 '"002594.SZ' 不符合格式 (SH/SZ/HK/US)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 比亚迪 估值分析 2026-06-29.md 未引用本管理层档案
- [P1] FACT_PENALTY: [management_archive_004] 处罚 2025-12 巴西劳工检察院 承包商劳工条件和解 未完整呈现 (org=True, event=False, amount=True)
- [P1] FACT_PENALTY: [M2] 检测到 1 处疑似合并的处罚记录（独立事件应分行）
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："2023年将成为全球新能源车销量第一"
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："技术为王，研发投入不设上限"
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 增发, 配股, 可转债, 优先股（可能遗漏摊薄工具）
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件：— 深刻洞察：将增长约束从需求端准确归因到供给端
- [P1] GROUNDING_QUOTE_CONTEXT: [M7] 摘录可能缺失限定条件：— 远期目标宣言，需要持续验证
- [P1] WORKFLOW_MISSING_TIMELINE: [M8] 高管变动时间线记录不足（仅 1 行），无法判断稳定性

## management_archive_005 (FAIL)
- [P2] FORMAT_TICKER_FORMAT: [structure.ticker_format] 股票代码 '"600703.SH"' 不符合格式 (SH/SZ/HK/US)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 三安光电 深度分析 36 2026-06-19.md 未引用本管理层档案
- [P2] FACT_PENALTY: [management_archive_005] 处罚 2020-01 地方监管部门 节能与消防罚款 未完整呈现 (org=True, event=False, amount=True)
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："Mini/Micro LED将成为显示技术革命，公司技术已领先"
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺（含'将/预计/目标'）被标为已兑现，但未提供结果指标："InP光芯片国内领先，400G/800G将放量"
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 增发, 配股, 可转债, H股, 优先股, 股权激励（可能遗漏摊薄工具）

