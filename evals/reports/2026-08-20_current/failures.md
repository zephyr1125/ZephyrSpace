# Failures

## management_archive_001 (PASS)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 福耀玻璃 深度分析 88 2026-05-17.md 未引用本管理层档案
- [P2] ANALYSIS_UNCERTAINTY: [management_archive_001] uncertainty 分析质量 2/5 偏低：未见信息不足标注，存在强推结论风险
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 可转债, H股, 优先股（可能遗漏摊薄工具）
- [P1] FACT_MANAGEMENT_TURNOVER: [M8] 检测到短期密集离任 {'2025': 2} 但正文未识别该模式（或否认）

## management_archive_002 (PASS)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 腾讯控股 深度分析 83 2026-05-13.md 未引用本管理层档案
- [P2] ANALYSIS_UNCERTAINTY: [management_archive_002] uncertainty 分析质量 2/5 偏低：未见信息不足标注，存在强推结论风险
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 可转债, H股, 优先股, 股权激励（可能遗漏摊薄工具）
- [P1] WORKFLOW_MISSING_TIMELINE: [M8] 高管变动时间线记录不足（仅 0 行），无法判断稳定性

## management_archive_003 (PASS)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 美的集团 深度分析 81 2026-06-28.md 未引用本管理层档案
- [P2] SCORE_INCONSISTENCY: 总分 87（>=85）但结论定位为'需要持续跟踪'，建议复核
- [P2] SCORE_INCONSISTENCY: [calibration.conclusion_type] 总分 87（>=85）但结论定位为'需要持续跟踪'，建议复核
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 优先股（可能遗漏摊薄工具）

## management_archive_004 (PASS)
- [P2] FORMAT_TICKER_FORMAT: [structure.ticker_format] 股票代码 '"002594.SZ' 不符合格式 (SH/SZ/HK/US)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 比亚迪 估值分析 2026-06-29.md 未引用本管理层档案
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 增发, 配股, 可转债, 优先股（可能遗漏摊薄工具）
- [P2] GROUNDING_QUOTE_CONTEXT: [M7] 短促摘录可能缺失限定条件（建议人工复核）：— 深刻洞察：将增长约束从需求端准确归因到供给端
- [P2] GROUNDING_QUOTE_CONTEXT: [M7] 短促摘录可能缺失限定条件（建议人工复核）：— 远期目标宣言，需要持续验证
- [P1] WORKFLOW_MISSING_TIMELINE: [M8] 高管变动时间线记录不足（仅 1 行），无法判断稳定性

## management_archive_005 (PASS)
- [P2] FORMAT_TICKER_FORMAT: [structure.ticker_format] 股票代码 '"600703.SH"' 不符合格式 (SH/SZ/HK/US)
- [P2] FORMAT_BACKLINK: [structure.backlink] 深度分析页 三安光电 深度分析 36 2026-06-19.md 未引用本管理层档案
- [P1] ANALYSIS_ACTION_VS_OUTCOME: [M3] 承诺被标为已兑现，但证据仅显示执行动作（投入/费用），无业务结果指标："InP光芯片国内领先，400G/800G将放量"
- [P1] FACT_CAPITAL_ACTION: [M4] 融资工具清单未覆盖: 增发, 配股, 可转债, H股, 优先股, 股权激励（可能遗漏摊薄工具）

