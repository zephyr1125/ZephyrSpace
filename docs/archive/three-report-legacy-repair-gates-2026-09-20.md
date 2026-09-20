# 旧修复闸门历史归档

仅用于历史run复现，不是新任务执行规范。新任务见 `docs/three-report-delivery.md`。

## 主任务送审入口

作者自检后，主任务重新执行统一入口；初稿与修复显式分开：

```powershell
python -X utf8 scripts/triplet_workpaper.py handoff <底稿.json> --stage initial --output <新送审检查.json>
python -X utf8 scripts/triplet_workpaper.py handoff <新底稿.json> --stage repair --previous <冻结底稿.json> --adjudication <锁定裁决.json> --preparation <修复准备.json> --output <新送审检查.json>
```

仅 `ready_for_independent_review` 表示机械送审条件通过，不表示研究通过。主任务确认检查记录的底稿、裁决及三稿SHA256与发送版本一致；检查后再改文件必须重新检查。修复入口自动启用repair检查，并强制核对裁决中全部非invalid的P0/P1问题等级及验收ID，缺漏或降级失败。普通check不作为送审凭据；含repair对象的报告不能跳过修复模式。表格render仍只校验计算，不具备送审资格。

正文检查剔除允许共用的生成表、标题及元数据；拦截85%以上正文行集合相同、占正文至少25%且至少10行的编号归一化重复、无独立正文，以及修复时原正文不少于1000字而新版丢失超过40%的情况。阈值只用于阻断明显退化，不证明语义完整；命中时恢复内容或核实误报，不能换用普通check绕过。150/150/100行下限仍保留。跨报告共享财务表不因此被拒绝。

## 改稿前：先解决缺证与评分归因

沿用同一修复包和裁决，不增加新的审核角色。主任务维护一份`修复准备.json`，按每个P0/P1验收ID列结果：

```json
{"items":[{"id":"C03-grid","kind":"reasoning","status":"resolved","resolution":"写具体计算与规则判断结果，不写泛化已处理","evidence_refs":["原件页码或计算桥路径"]}],"replacements":[{"report":"valuation","old":"取得CFO 8-K正文","new":"已核CFO 8-K正文"}]}
```

`kind`为evidence/reasoning/text；未完成记open，程序仅允许全部resolved且精确覆盖裁决后进入改稿。执行`python -X utf8 scripts/triplet_workpaper.py repair-ready <修复准备.json> --adjudication <锁定裁决.json>`。resolved是待主任务核实的声明，不是可信证据；主任务逐项核原件/计算，不能把“未知、暂给中档、以后再取得”改标resolved。缺证项只补对应资料；确实不可得时交裁决明确允许的替代判断，或维持未完成，不要求所有非决定性未知消失。

作者先修底稿中受影响的score/reason/evidence_refs，再重新生成表格并修改对应正文。分值已正确不代表理由或来源正确。replacements只列锁定修复包已明确判错的完整短句，禁止用整个事实ID或数字全局替换；handoff检查旧句消失且新句出现，历史对照保留时选择更精确上下文。缺省空数组，语义矛盾仍由人工核验。

用评分上界停止定价时，必须覆盖全部尚未确定的评分项，并说明已固定项依据和联合约束，不能只放宽一个争议项。缺证与分析未完成时不写精确“保守分”绕过门槛。

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


## 旧裁决包兼容

- 裁决员维护一份版本化裁决台账；新任务的问题分流及交付状态见交付规范。兼容旧修复包的 `adjudication-v1.json` 字段为：`issues` 每项含 `id/candidate_ids/severity/decision/reason/evidence_refs/action/score_valuation_impact/acceptance`；`decision` 为 `valid/partial/invalid/insufficient/suggestion`，`acceptance` 是 `{id, condition}` 数组。另含 `parameters`：最终评分桥/估值参数或 null 与待定原因。部分成立明确采纳与不采纳部分；缺证仍给补证及验收条件，不能当误报关闭。
- 从同一台账生成修复包，不另写同义裁决长文：

```powershell
python -X utf8 scripts/triplet_workpaper.py repair-package data/reviews/<run-id>/adjudication-v1.json --output data/reviews/<run-id>/repair-package-v1.md
```

主 Agent 核对候选全覆盖、根因映射与验收条件后一次发作者；无修复项则按原 SOP 记不适用。机器转换不承担语义合并或裁决。

