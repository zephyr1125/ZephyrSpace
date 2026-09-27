# 三件套交付装配规范

本规范是新任务唯一交付入口；旧workpaper的评分/公式计算继续复用，旧repair-ready/handoff只用于历史复现。模型、研究轮次和发布授权仍见[调度SOP](three-report-economy-routing.md)。不增加常驻Agent，不自动改历史报告或Watchlist。

## 单一来源与职责

| 材料 | 维护者与内容 |
|---|---|
| 证据JSON | 证据角色维护有唯一ID的事实、计算及来源记录；按原件核期别、单位、定位。只列本次有效版本，冲突不得靠覆盖ID解决 |
| workpaper.json | 作者维护唯一分项score/reason/evidence_refs、估值假设及计算；不用文稿反向生成分数 |
| decision.json | 作者初稿标pending；裁决维护获批判断、分流、验收和批准依据，不能由作者自行关闭重大问题 |
| bundle.json | 主任务列证据文件、底稿、裁决、三份源稿路径及少量跨报告共用事实 |
| 三份叙述源稿 | 作者保留公司、治理、估值各自完整分析；引用共用块，不复制维护其数值或状态 |
| 生成三稿+manifest.json | 程序装配、建立引用索引及哈希；只生成全新版本，禁止手改输出 |

`evidence_refs`分项引用必须为完整注册ID；证据JSON识别fact_id/calculation_id/id声明，来源记录还支持带url/path/file的source_id。引用字段本身不注册为声明。ID存在仅证明可定位，不证明事实真实，独立审核仍回原件。无ID的旧原件可建立有页码和来源字段的记录，不把文件名假装为证据ID。

## 装配描述与标记

```json
{
  "schema_version": 1,
  "workpaper": "data/reviews/<run>/workpaper.json",
  "decision": "data/reviews/<run>/decision.json",
  "evidence": ["data/reviews/<run>/facts.json", "data/reviews/<run>/sources.json"],
  "id_prefixes": ["NKE-"],
  "facts": {
    "executive_timeline": {
      "text": "已核主要高管任免时间线；个人动机和未披露保留率仍未知。",
      "refs": ["NKE-ORG-001"],
      "retired": ["完整主要高管离任索引尚未取得"]
    }
  },
  "templates": {
    "deep": "data/reviews/<run>/source/deep.md",
    "management": "data/reviews/<run>/source/management.md",
    "valuation": "data/reviews/<run>/source/valuation.md"
  }
}
```

源稿只在需要共用内容处使用以下标记，其余仍是独立长篇研究，不是套用同一摘要：

- `{{decision}}`：统一结论、三项总分或区间、价格状态；三稿必需。
- `{{score:company}}`、`{{score:management}}`、`{{score:combined}}`：总分显示；可用于标题及元数据。
- `{{table:company}}`、`{{table:management}}`：原始分项、理由和证据一并生成；分别是公司/管理层报告必需块。
- `{{table:model-模型ID}}`、`{{table:weighted}}`：估值情景和敏感性等沿用底稿生成器；正式定价必需，批准停止定价时不伪造表格。
- `{{fact:executive_timeline}}`：所有报告共享同一事实状态与未知边界。
- `{{ref:NKE-ORG-001}}`：验证并输出完整ID，程序附记录文件和字段位置。

共用块不允许嵌套标记。自由文字也按id_prefixes扫描完整ID；禁止`ID-001/002/003`缩写。retired仅用于已经确认失效的具体文字，不用数字或模糊词全局禁用；其余语义矛盾仍由审核检查。证据ID不能凭相似拼写自动纠正，先确认实际来源。

## 判断与交付分开记录

decision.json至少包括：

```json
{
  "decision": "defer",
  "research_state": "pending",
  "basis": "具体判断及规则依据，初稿可明确待复核事项",
  "review_refs": [],
  "issues": []
}
```

裁决批准后research_state为approved，review_refs列两路真实复核记录的Vault路径，并填写与底稿一致的score_bounds（company/management/combined各为原始上下界数组；点值上下界相同）。停止定价须quality_stop_approved=true；区间停止还须bounds_approved=true。程序核文件存在及数值一致，主任务仍需核审核覆盖、实际批准范围和红线，不能把字段自述当认证。

每个issue含id/lane/status/reason/acceptance；lane为research或delivery，status为open或closed。closed须verification_refs。delivery额外必须classified_by=adjudicator、no_decision_impact=true。未经裁决确认的断链和状态冲突不能自动降级。

- research：真实来源、事实、评分归因或估值/资格可能改变，走独立研究复查。
- delivery：实际来源及判断已经核定，只需执行确定的显示或同步修正；保留已批准研究判断，原事实审核员定向验收，主任务核版本。

装配成功一律为assembled_for_review、publish_allowed=false，不等于投资判断获批。交付仍有错误或缺实质内容时不发布，即使资格答案已是reject。最终收尾同时说明决策、研究判断和交付是否完成，不能再次把“修好报告”与“公司是否合格”混成一个状态。

## 一条执行路径

```powershell
python -X utf8 scripts/triplet_delivery.py build <bundle.json> --output data/reviews/<run>/build-v1
python -X utf8 scripts/triplet_delivery.py verify data/reviews/<run>/build-v1/manifest.json
```

输出路径位于Vault内且必须不存在。build在写文件前检查完整性、引用、底稿和旧状态；失败不产生可冒充通过的报告。成功后将同一manifest和三稿交两位原评分审核员做首次完整报告审核；verify核源数据及输出字节，检查后有修改必须重新装配。不要先写三份文稿，再维护三套表格和关闭声明。

评分批准、首次完整报告审核及研究修复依SOP。裁决明确批准参数后更新唯一底稿/共用事实，程序刷新生成内容；只做受影响范围验收。主任务记录最终manifest、两路研究覆盖、裁决和交付验收，全部通过才按现有版本命名发布。发布前不修改生成稿状态；若需改变送审措辞，在源中改并重新装配、核对变化，不能伪造历史通过。

源稿标题和类型使用中性报告名称，执行状态只通过`{{decision}}`及外部验收记录维护；不得散写“本稿尚待复查”、旧handoff指令或机械校验端点。发布送审的bundle设`publication_ready=true`，装配时拦截已知流程残留；真实未知（例如未披露人才保留率）仍保留。此开关不代表验收或授权，发布归档无论开关取值均再次检查。

最终裁决须用`approved_manifest_sha256`和`approved_report_sha256`绑定实际获批字节，`release_review_refs`指向实际发布复核。主任务按字节复制为新正式版本后，生成一次可携带验收包：

```powershell
python -X utf8 scripts/triplet_delivery.py archive-release <release-config.json> --output data/reviews/<run>/final/release-v1
python -X utf8 scripts/triplet_delivery.py verify-release data/reviews/<run>/final/release-v1/release.json
```

配置包含`manifest`、`authorization`及`reports`（deep.md/management.md/valuation.md到三份正式Vault路径的映射）。归档冻结全部直接输入、裁决及递归复核引用；缺文件、版本错配、发布残留均失败。release.json记录原路径到归档快照的映射，历史原路径不改写。验证只依赖正式报告和验收包，可在没有临时构建/审核目录的环境运行，并检查必要文件未被Git忽略。公司页和索引回写前必须成功；不能把名字叫build-final的目录当作获批版本。归档校验不替代审核语义，也不写Watchlist。

确定的源稿文字补丁可以执行：

```powershell
python -X utf8 scripts/triplet_delivery.py patch <bundle.json> --plan <patch.json> --output data/reviews/<run>/source-patch-v2
```

patch.json是`{"edits":[{"path":"源稿路径","before_sha256":"冻结源稿哈希","old":"完整错误片段","new":"裁定正确片段","count":1,"issue_id":"裁决中delivery问题ID"}]}`。程序只允许源稿路径，核旧稿哈希及出现次数，产生新源和路径映射；不改证据、底稿或历史。更新bundle指向新源，重新build。补丁仍需定向验收，不能以退出码替代语义判断。

旧材料可只读查引用：scan输入含evidence/id_prefixes/files，运行`triplet_delivery.py scan <扫描描述.json>`。不存在ID和压缩写法会返回非零退出码，不能自动猜别名。

## 区间与适配

区间项填score=null、bounds=[下限,上限]、bounds_reason；该评分表total=null、bounds为所有分项汇总。不得写零分占位，不取中点或下端点作实际总分。装配器保留原始区间，展示向外取整数以免缩小外包络，门槛仍按原始端点。点值继续ROUND_HALF_UP。

区间装配支持质量否决停止定价以及 `decision=defer`、`valuation.status=deferred` 的暂缓路径；后者必须空模型、显式null价格/确定性和具体缺口，不得声明quality_stop_approved。点值评分也可与暂缓估值并存。首次送审research_state=pending明确标候选，不要求作者伪造批准；获批区间仍须bounds_approved，质量停止另须quality_stop_approved。发布归档仍强制research_state=approved，不能用装配成功规避双模型或完整研究。区间底稿同样检查桥接计算；不得塞入端点令旧程序通过。

## 验收重点

原件、评分规则、150/150/100行和完整内容、首次双复核均保留。确定性测试覆盖错误ID、来源声明与引用区分、共用事实同步、旧句残留、区间端点误用、跨报告重复、精确补丁、哈希与不覆盖。测试通过不代表真实公司研究通过，也不承诺模型不再犯错。
