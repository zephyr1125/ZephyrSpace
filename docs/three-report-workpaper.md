# 三件套底稿与机械检查

适用于 2026-09-19 后新启动的完整研究；不追改已冻结初稿或历史报告。调度和质量门槛以 `three-report-economy-routing.md` 为准。该底稿替代每次临时设计的评分表、计算输入及重复参数副本，不增加一个常驻角色或前置审批。

## 作者：先底稿后正文

作者在自己的 run 子目录维护 `workpaper-v1.json`：事实、规则、假设及计算先闭合，再展开三份全文。底稿属于评价材料；评分阶段两路收到同一冻结底稿并独立复核，互不读对方意见。Terra 的中性事实包不放评分或目标价。

所有路径相对 Vault 根目录；JSON 使用 UTF-8。字段的 `evidence_refs` 是非空字符串数组；新任务写完整注册ID，原件页码/章节/行号保存在被引证据记录中。旧底稿的ID加定位自由文本仅兼容历史检查；不得只有模糊的“年报”。来源真实性、假设合理性及 ID 是否对应原件仍须人工独立核验。

| 字段 | 结构与约束 |
|---|---|
| `schema_version` | `1` |
| `score_display` | 新研究填 `"integer_half_up"`：仅总分标记显示整数，合计先加原始分；分项、底稿及门槛不变。缺省仅兼容历史稿。完整规则见收尾规范 |
| `scores.company` | `{items: [...], total: 数值}`；25 个子项按公司核心模块原表，C3+C4 是一个合并项，不另造权重 |
| `scores.management` | 同上；七项 ID 使用原表中文维度名 |
| 每个评分项 | `{id, score, rule_ref, reason, evidence_refs}`；理由写证据到评分的判断，不先定总分倒填；D2 另填布尔 `original_statement_found`、`strategy_drift`；F2.5 采用原规则正面先例加分时填 `positive_precedent: true` 并给证据 |
| `valuation.currency` | 所选股份的最终币种；每个主模型先转换到同币种每股价值 |
| `valuation.models` | 默认两个主模型；每项 `{id, weight, basis, shared_assumptions, output_currency, output_unit: "per_share", formula, scenarios, sensitivity}`；超过两个须补 `valuation.additional_model_reason` |
| `formula` | 显式标量表达式，支持变量、括号、`+ - * / **`；如 `d0 * (1 + g) / (ke - g) / fx`；DCF须展开显式期、终值与归母权益桥，不得把 EPS 冒充 FCF |
| `scenarios` | 严格包含 `bear/base/bull`，各为 `{inputs: {变量: 数值}, input_meta: {...}, value: 每股价值}` |
| `input_meta` | 与 inputs 变量一一对应，各为 `{unit, date, kind, evidence_refs}`；kind 仅 `actual/forecast/assumption/derived`，年度/单季/TTM、归属及实际/预测在单位/期别和证据中写明 |
| `sensitivity` | `{x, y, x_values, y_values, values}`；`values[行y][列x]`；两轴均不少于两个不同点且包含基准输入；**必须用同一模型公式重新计算各格**，其余基准输入固定；复杂联动必须写入公式或走下文模型适配，不冻结本应随敏感变量变化的派生输入 |
| 综合结果 | `valuation.weighted: {bear, base, bull}`、`target_price`、`certainty`、`certainty_reason`、`buy_price`；三情景用同一权重，买入价沿用 `target_price × (0.68 + 0.14 × certainty)` |
| `valuation.reverse` | `{weight: 0, variable, implied_value, formula, inputs, market_price, assumptions, evidence_refs}`；把隐含变量代回正向式核对市价，正文另给反向敏感性及解的适用边界；不能把市价作为第二主模型 |
| `bridges` | 桥数组：`{id, date, unit, scope, start, items, result}`；每项 `{economic_id, signed_value, evidence_refs}`，满足起点加带符号变动等于终点；同一桥内一个经济项目只计一次；跨桥复用可以，但须解释连接关系 |
| 桥不适用 | `bridges: []` 并填写 `bridges_not_applicable` 理由；不能用“不适用”跳过实际存在的现金、少数股东、负债或正常化桥 |
| `reports`（旧检查） | 新装配用bundle.templates定位源稿，本字段仅用于旧check：`{deep: "深度分析/本次新文件.md", management: "管理层档案/本次新文件.md", valuation: "估值分析/本次新文件.md"}` |

公司分项及管理层满分直接从仓库核心模块原表读取，不再维护一份可漂移的评分权重 JSON。规则数目/总分异常则检查失败。程序只识别明确的结构和上限；不能自动评价治理、会计质量或证据充分性，也不自动给出 Watchlist 档位。

## 计算与装配

新任务不再先运行render后手工把表格复制到三稿；按[交付规范](three-report-delivery.md)直接build。装配器复用本脚本的评分、估值及桥接函数，检查失败不生成送审产物。原render/check命令及返回码保留给历史复现和计算调试，旧顺序见[历史闸门](archive/three-report-legacy-repair-gates-2026-09-20.md)。

### 模型适配边界

上述标量表达式覆盖简单 PE/DDM、显式展开的 DCF/RI 等，不是估值模型白名单。复杂 SOTP、分段现金流、资本约束或行业模型无法忠实表达时，**保留适用经济模型**，复用本次 `calculate.py` 做扩展机械检查；不能为迁就工具简化模型，也不能把一个外部结果作为常数假装完成敏感性。

适配时记录 `mechanical-check-scope.md`：不支持的公式、使用的计算脚本/输入/输出路径及版本、评分/权重/买入价/三情景/双变量/桥/报告快照/修复验收各检查项由哪个脚本覆盖、尚待人工验证项。可直接复用本脚本的 `score`、`scoring_rules`、`expression` 等函数。扩展程序须实际执行；没有覆盖的机械项不能记为通过，决定性未覆盖项仍按 P0/P1 关闭要求处理。无需新增角色或另开审批。

双审核员必须独立重算关键公式；运行作者的通用程序或扩展程序都不算独立计算。模板化计算不证明模型的经济合理性。

## 新任务交付与历史兼容

新任务统一使用[交付装配规范](three-report-delivery.md)：证据注册、共用事实、分项底稿和独立叙述源稿分别维护，由程序生成三份送审报告。底稿的评分、公式、三情景和敏感性规则沿用本文件；普通`check`与`render`仍是计算函数，不等于交付或研究验收。

旧`repair-ready`、`handoff`及`repair`变更声明保留用于已冻结run复现，字段见[历史闸门](archive/three-report-legacy-repair-gates-2026-09-20.md)。新任务不再维护preparation多版本、逐句replacement清单或在三份输出稿中手工同步评分表；不能同时执行新旧两套交接流程。

## 中间产物去重

评分前置阶段使用 `triplet_workpaper.py check <workpaper.json> --no-reports` 核分项、估值状态及桥接计算；新底稿声明 `score_rule_validation: "explicit_tiers_v1"`，额外从原规则检查A3/D1/F2封闭档位，不对开放的专业判断自动插值。输出scope明确reports=false，不要求为了脚本先生成三份长报告。该检查不批准评分；完整报告仍走装配及独立验收。历史底稿缺新字段保留原机械检查范围，不追改获批快照。

- 不单设盲审风险卡；评分审核覆盖全部分项、反证和决定性原件，重大风险不能为控制长度而省略。
- 评分或完整报告审核输出 `review-<role>.json`，其中 `findings` 数组每项必含 `severity/location/claim/evidence/impact/recommendation`（字符串，原文定位与关键推导写在 evidence）。可另含精简 `coverage`、评分或结论变化及 `uncovered`。通过项只记“已核/无问题”。零问题也须交覆盖记录，不重写一份长 Markdown 同义稿。
- 两路意见锁定后，由主 Agent 复用现有匿名化程序：

```powershell
python -X utf8 scripts/review_trial.py anonymize data/reviews/<run-id>/review-sources.json data/reviews/<run-id>/anonymous
```

`review-sources.json` 为 `{ "facts": "本次triplet_review_facts审核JSON路径", "reasoning": "本次triplet_review_reasoning审核JSON路径" }`。只把生成的 `anonymous/candidates.json` 明确路径交裁决；`unblinding.json` 保持私有，不向裁决提供目录枚举或来源映射。自由文本也不能包含审核员/模型身份。该工具只剥除结构化身份字段，不保证清除正文中的身份泄漏；主 Agent 交接前检查。原问题通过 reviewer + original_index 追溯，候选冻结后不重新匿名化。
- 主 Agent 按根因仅列候选 ID 组及实质分歧，不再次转述全部证据。匿名候选全文保留，不能因分组合并丢掉少数意见；裁决按原件判断。
- 新任务裁决只维护交付规范的decision.json：额外保留candidate_dispositions（全部候选ID、成立/部分成立/误报/缺证/建议、理由及原件），参数和逐问题验收；不另转录同义修复长文。主任务核候选全覆盖、评分桥及原验收条件后一次交作者。旧repair-package格式仅供历史run复现，见历史闸门。

整套更新与计量沿用[调度SOP](three-report-economy-routing.md)，本文件只维护底稿与产物格式。
