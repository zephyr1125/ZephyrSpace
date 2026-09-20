# 三件套底稿与机械检查

适用于 2026-09-19 后新启动的完整研究；不追改已冻结初稿或历史报告。调度和质量门槛以 `three-report-economy-routing.md` 为准。该底稿替代每次临时设计的评分表、计算输入及重复参数副本，不增加一个常驻角色或前置审批。

## 作者：先底稿后正文

作者在自己的 run 子目录维护 `workpaper-v1.json`：事实、规则、假设及计算先闭合，再展开三份全文。底稿与作者初稿属于评价材料，第一阶段盲审不可读；冻结初稿后两路收到同一底稿。Terra 的中性事实包不放评分或目标价。

所有路径相对 Vault 根目录；JSON 使用 UTF-8。字段的 `evidence_refs` 是非空字符串数组，写事实 ID + 原件页码/章节/行号；不得只有模糊的“年报”。来源真实性、假设合理性及 ID 是否对应原件仍须人工独立核验。

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
| `reports` | `{deep: "深度分析/本次新文件.md", management: "管理层档案/本次新文件.md", valuation: "估值分析/本次新文件.md"}` |

公司分项及管理层满分直接从仓库核心模块原表读取，不再维护一份可漂移的评分权重 JSON。规则数目/总分异常则检查失败。程序只识别明确的结构和上限；不能自动评价治理、会计质量或证据充分性，也不自动给出 Watchlist 档位。

## 运行顺序

在 Vault 根目录运行，命令中的 `<run-id>` 换成本次目录：

```powershell
python -X utf8 scripts/triplet_workpaper.py render data/reviews/<run-id>/writer/workpaper-v1.json --output data/reviews/<run-id>/writer/tables-v1.md
python -X utf8 scripts/triplet_workpaper.py check data/reviews/<run-id>/writer/workpaper-v1.json --output data/reviews/<run-id>/writer/selfcheck-v1.json
```

1. `render` 先检查底稿，再生成参数快照、评分表、两主模型情景与敏感性、综合情景。生成器只写指定**新文件**，不修改正文、历史或冻结材料；输出存在即拒绝覆盖。
2. 作者将参数快照放进三份新报告，company评分表放深度报告，management评分表放管理层报告，两模型与综合情景表放估值报告，补足叙述、证据、模型限制及反证。快照用隐藏 HTML 注释包住唯一有效数值，例如 `<!-- triplet:cScore -->69<!-- /triplet:cScore -->`；表格也有 `triplet:table:...` 起止注释，复制时保留。字段与表格格式以生成器为准，不手改生成块；解释写在块外。不要把整份 tables 原样塞入三份报告，不用空行凑篇幅。
3. `check` 检查底稿、150/150/100 行、三份报告的带标记快照及对应生成表内容；底稿有矩阵但估值正文漏贴/改错矩阵，同样失败。正文其他未标记数值、章节内容与旧数字残留仍由作者自检和双复核检查；不得声称程序已验证全文事实。
4. 修改后使用 `workpaper-v2.json`、`tables-v2.md`、`selfcheck-v2.json` 等新版本，保留冻结底稿/正文。未冻结的工作底稿可原位编辑；正式输出不覆盖旧版。没有新变更或失败不重复运行。
5. 返回码 `0` 仅代表本次机械检查通过，`1` 为检查失败，`2` 为输入/运行错误。输出状态永远不等于审核通过或准予入库。若有决定性缺证，保留 null 和“研究未完成”；不能为通过程序填假数。

### 模型适配边界

上述标量表达式覆盖简单 PE/DDM、显式展开的 DCF/RI 等，不是估值模型白名单。复杂 SOTP、分段现金流、资本约束或行业模型无法忠实表达时，**保留适用经济模型**，复用本次 `calculate.py` 做扩展机械检查；不能为迁就工具简化模型，也不能把一个外部结果作为常数假装完成敏感性。

适配时记录 `mechanical-check-scope.md`：不支持的公式、使用的计算脚本/输入/输出路径及版本、评分/权重/买入价/三情景/双变量/桥/报告快照/修复验收各检查项由哪个脚本覆盖、尚待人工验证项。可直接复用本脚本的 `score`、`scoring_rules`、`expression` 等函数。扩展程序须实际执行；没有覆盖的机械项不能记为通过，决定性未覆盖项仍按 P0/P1 关闭要求处理。无需新增角色或另开审批。

双审核员必须独立重算关键公式；运行作者的通用程序或扩展程序都不算独立计算。模板化计算不证明模型的经济合理性。

## 修复：逐条件验收，不重写无关全文

修复底稿增加 `repair`，执行 `check ... --repair --previous <上一冻结底稿.json>`。不修改上一底稿指向的冻结报告；新报告使用新路径。正文按二级标题比较，代码块内标题不参与分段：

```json
{
  "issues": [{"id": "C03", "severity": "P1", "acceptance_ids": ["C03-formula", "C03-grid"]}],
  "score_changes": [{"key": "company/A3", "issue_id": "C03", "reason": "仅示意字段结构；实际变更须按裁决", "evidence_refs": ["原件与具体定位"]}],
  "report_changes": [{"report": "valuation", "section": "DDM估值", "issue_id": "C03", "reason": "补双变量矩阵"}],
  "closures": [{
    "id": "C03",
    "locations": ["估值新版本：DDM章节"],
    "score_valuation_impact": "列受影响分项、模型和数值变化；不变也说明依据",
    "checks": [
      {"id": "C03-formula", "passed": true, "evidence": "公式和独立结果路径、定位"},
      {"id": "C03-grid", "passed": true, "evidence": "双变量网格、计算结果及正文位置"}
    ]
  }]
}
```

`issues`/`acceptance_ids` 必须从已锁定裁决原样提取，主 Agent 核对完整性；作者不得删条件以取得通过。程序拦截漏条件、重复 ID、缺关闭证据；`passed` 是作者声明，只有两路定向复查/裁决才能认定实质关闭。

`score_changes`必须与实际发生改变的评分项（含理由、来源、条件标记）一一对应；无改动填空数组，不照抄示例。`report_changes`同样列每处改变的二级章节，report取deep/management/valuation，标题前内容为`__preamble__`；章节改名时旧标题另给`replacement_section`。未声明的重写/删除会失败；三项以上相同评分理由也会失败。声明不是准许全量重写的口子：主Agent核对范围和原件，禁止把25条不同依据改成“见最终报告”。验收失败不重复全篇生成，按[明确结论收尾](three-report-closeout.md)给真实处置。

局部修复沿“事实 ID → 评分项/模型输入 → 计算表 → 正文引用 → 公司页字段”列影响清单。每个受影响处说明变更或不变依据；系统性错误可以扩大范围，按原 SOP 记录原因。公司页和 Watchlist 仍只由主 Agent 在验收后串行写入。

## 中间产物去重

- 盲审仍为一张短表，不复述公司介绍或多年度数据。重大风险不能为控制长度而省略。
- 第二阶段审核输出 `review-<role>.json`，其中 `findings` 数组每项必含 `severity/location/claim/evidence/impact/recommendation`（字符串，原文定位与关键推导写在 evidence）。可另含精简 `coverage`、盲审判断变化及 `uncovered`。通过项只记“已核/无问题”。零问题也须交覆盖记录，不重写一份长 Markdown 同义稿。
- 两路意见锁定后，由主 Agent 复用现有匿名化程序：

```powershell
python -X utf8 scripts/review_trial.py anonymize data/reviews/<run-id>/review-sources.json data/reviews/<run-id>/anonymous
```

`review-sources.json` 为 `{ "facts": "本次triplet_review_facts审核JSON路径", "reasoning": "本次triplet_review_reasoning审核JSON路径" }`。只把生成的 `anonymous/candidates.json` 明确路径交裁决；`unblinding.json` 保持私有，不向裁决提供目录枚举或来源映射。自由文本也不能包含审核员/模型身份。该工具只剥除结构化身份字段，不保证清除正文中的身份泄漏；主 Agent 交接前检查。原问题通过 reviewer + original_index 追溯，候选冻结后不重新匿名化。
- 主 Agent 按根因仅列候选 ID 组及实质分歧，不再次转述全部证据。匿名候选全文保留，不能因分组合并丢掉少数意见；裁决按原件判断。
- 裁决员只维护 `adjudication-v1.json`：`issues` 每项含 `id/candidate_ids/severity/decision/reason/evidence_refs/action/score_valuation_impact/acceptance`；`decision` 为 `valid/partial/invalid/insufficient/suggestion`，`acceptance` 是 `{id, condition}` 数组。另含 `parameters`：最终评分桥/估值参数或 null 与待定原因。部分成立明确采纳与不采纳部分；缺证仍给补证及验收条件，不能当误报关闭。
- 从同一台账生成修复包，不另写同义裁决长文：

```powershell
python -X utf8 scripts/triplet_workpaper.py repair-package data/reviews/<run-id>/adjudication-v1.json --output data/reviews/<run-id>/repair-package-v1.md
```

主 Agent 核对候选全覆盖、根因映射与验收条件后一次发作者；无修复项则按原 SOP 记不适用。机器转换不承担语义合并或裁决。

整套更新与计量沿用[调度SOP](three-report-economy-routing.md)，本文件只维护底稿与产物格式。
