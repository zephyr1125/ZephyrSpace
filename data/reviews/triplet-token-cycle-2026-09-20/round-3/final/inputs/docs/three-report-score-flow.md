# 评分阶段的精简交接

本页只定义工具接口；评分原规则、双复核、异常收尾和轮次仍按调度SOP。目标减少重复输入输出，不以字数或缓存量宣称节省30%。程序均不批准评分或入库。路径相对Vault，输出用本次run的新路径，禁止覆盖冻结文件。

## 默认直接形成评分依据；按需委托取证

已有完整周期可读原件时，作者同一次任务完成32项原规则核验、必要计算和底稿，直接用下文check；不单写32项计划和覆盖副本。证据缺口在底稿`evidence_gaps`数组记录`affected_items/kind/impact/search_scope/evidence_refs`，无决定性缺口可为空，不能用空数组掩盖未查事实。每项reason仍须说明事实、反证和选档理由，两路独立复核核充分性。来源取证需要独立委托时才用以下计划/coverage接口；这是可选工具，不是默认串行关卡。

```powershell
python -X utf8 scripts/triplet_score_flow.py plan data/reviews/<run>/score-plan.json
python -X utf8 scripts/triplet_score_flow.py packet score data/reviews/<run>/score-rules.md
```

需要整套委托取证时，同一作者在开始广泛取证前填32个分项的`scope`：依据原规则列公司特有的必要事实、期别、反证和适用边界，不预设分数、不复述整套标准。空模板不能通过。共用事实只收一次，各项引用相同证据ID；不得按32项重复抓取。主任务核范围后冻结计划，证据角色据此取证。新决定性问题允许修订计划新版本并记录原因，不因锁表忽略新风险。

`coverage.json`使用`plan`（计划路径）、`plan_sha256`、`evidence`（有效JSON路径数组）、`answers`；不再复制`requirements`。答复字段沿用证据规范，逐项 covered/bounded/open；新增`remaining_kind`取none/public_not_checked/unpublished/no_applicable_event/irreducible_conflict，以及布尔`supports_scoring`。决定性项公开未查或不能支持原规则选档时阻断送审，不得标bounded冒充完成。covered须无缺口；bounded须已有有界检索且可解释为何仍能支持评分。作者可按明确分工并行回看原件、补证并判断选档依据，不必空等全表；不得因执行缺口任意打分。送审前统一有效证据及32项覆盖，运行`triplet_evidence_gate.py`后主任务抽核实质，不能把自述当作事实已齐。历史补证仍兼容内嵌requirements。

## 阶段阅读与机械检查

score阅读包逐字保留公司、管理层核心及管理层review-checks，附来源哈希；不维护第二套压缩评分标准。作者和两路审核首次评分读全包；同一角色已读、哈希未变则复用。修复只回读受影响原规则及关联约束，不要求再次加载全包。估值阶段使用`packet valuation <新路径>`。明确触发的行业/市场/附录仍须加载，可用`--extra <原文路径>`加入；生成器不能自动判定附件适用性。取证角色不读作者评分包。正式报告及发布规范仅在对应阶段加载。

```powershell
python -X utf8 scripts/triplet_score_flow.py check <workpaper.json> <evidence-files.json> <check.json>
```

`evidence-files.json`是有效证据JSON路径数组，复用既有清单；不得同时登记同ID的旧新版本。检查分项、总分、原规则已支持的档位、引用是否注册，保存输入哈希。控制台只返回状态、异常及文件路径；主任务按需读错误与差异，不把完整JSON反复贴进上下文。引用对应原件的真实性、充分性、语义及关键独立重算仍由审核负责。

## 局部修复，完整底稿

唯一`decision.json`增加`score_repair_scope`数组，每项为`{group, item, acceptance_ids}`，group为company或management，item为原评分ID；验收ID须对应同一裁决台账原条件。裁决记录关联分项，不让作者自行扩范围。纯证据修订保留新ID及有效版本清单，不重写未变事实。

作者仅提交`delta.json`：

```json
{
  "base_sha256": "冻结底稿的SHA256",
  "decision_sha256": "唯一裁决文件的SHA256",
  "changes": [{
    "group": "company", "item": "E4", "acceptance_ids": ["原验收ID"],
    "set": {"score": 1.5, "reason": "证据到原规则的完整判断", "evidence_refs": ["完整证据ID"]}
  }]
}
```

```powershell
python -X utf8 scripts/triplet_score_flow.py apply-delta <base.json> <decision.json> <delta.json> <evidence-files.json> <新输出目录>
```

新目录包含可直接供既有工具读取的`workpaper.json`及`receipt.json`（逐项前后差异、哈希、检查结果、范围内未修改项）。程序复制未改内容，重算两项总分与原始分门槛候选，撤销新稿的评分/研究批准及发布许可。只输出分数门槛候选，不自动判全资格。失败或缺receipt的目录不是有效交接。原底稿不变；仅显示总分四舍五入，分项和门槛保留原值。

缺口记录需随事实修正时，裁决可加`metadata_repair_scope:[{field:"evidence_gaps",acceptance_ids:[原ID]}]`，delta对应`metadata_changes:[{field:"evidence_gaps",acceptance_ids:[原ID],set:[完整新缺口记录]}]`；仅允许该字段，差异写入receipt，仍需双路核真实边界。

此接口修评分项及上述缺口记录；估值、桥、跨模块判断变化按既有源稿流程修复，不强塞进delta。所有原验收条件仍逐一答复；未变分项若受新事实影响，应请原裁决扩定范围。双路复查差异、必要原件及联动，不能以机械通过、修改数量或receipt代替关闭问题。归档时将完整新底稿、receipt、delta、裁决、计划及实际证据版本纳入现有评分归档，不再抄一份同义检查报告。

## 效果验收

目标是在同模型、同冻结资料、同请求范围下，将非缓存输入加输出降至基线70%以内；另列缓存输入、墙钟、返工次数、重大错误检出及最终批准状态。评分和估值差异必须有证据解释；少查原件、遗漏红线、未批准评分或超过一小时都不能记为成功。局部修复回放只能证明局部效果；完整新建、更新分别计量，不把两类混比。
