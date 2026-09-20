# 耐克例外修复机械检查范围 v2

已执行 `triplet_workpaper.py check --repair --previous final/workpaper-repaired-v1.json`。防回退的评分与二级章节差异声明已通过；最终只剩三项预期schema失败：评分存在null、正式双模型为空、报告不保留数值型`cScore`快照。未为过检填入点值或恢复无效模型。

原程序结果：`triplet-check-repaired-v2-final.json`，返回码1。

扩展检查 `check_repaired_v2.py` 覆盖：32项定义/理由/证据；争议项null与规则数学上限；E2=5；已固定点值小计；正式价格null；G01–G13历史ID留存；九类精确恢复内容与行数。结果见 `selfcheck-repaired-v2.json`。

机械检查不批准争议评分、不验证原件真实性，也不等同最后两路复查。
