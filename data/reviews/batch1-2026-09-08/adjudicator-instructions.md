# 匿名裁决要求

这是匿名问题裁决。不要猜来源模型，也不要读取sources.json、unblinding.json、codex开头文件、Flash运行目录或此前试点。
仅使用本家公司blind/candidates.json、evidence.md、三份draft及共用rules.md、manifest.json。不得联网或读取原公司页面及旧报告。
主张由匿名编号表示。按证据判断，不按措辞强弱、条目数量或原提议P级别投票。
逐条核验同一期别、单位、公式、原文位置。材料不足不推定原稿错误，允许不足证据；原稿已披露的限制不自动算新缺陷。

输出本家blind/judgments.json，必须是JSON数组，每个候选ID恰好一次。每条含：
- id：候选ID；
- outcome：valid / partial / invalid / insufficient / non_defect；
- kind：error / improvement / scope_gap / confirmation；
- is_correction：布尔值，原候选是否明确主张原稿有错并要求纠正；即使你判它为证据不足或误报也保持true。纯建议/确认则false；
- group：同一真实缺陷用同一D001等组号，不同经济机制可分组；非缺陷用空串；
- severity：你裁定的P0/P1/P2；同一成立组必须相同；
- reason：具体裁决理由，部分成立时明确认可与驳回哪一部分；
- evidence：冻结证据或初稿精确定位和必要计算。

valid/partial且kind=error才进入正式缺陷覆盖并集。改进建议、仅材料缺失、正确性确认不计纠错。
同一问题不同表达不能算独立两条；多条重复建议分组，不用多数意见增强可信度。
输出本家blind/adjudication.md，概括实际成立的重要问题、主要误报、材料限制及未能充分核验项。
不改匿名池或冻结材料，不写来源映射，不改原报告/Watchlist，不提交。
裁决完成后通知主Agent，再揭盲；不要先读来源然后补裁决。
