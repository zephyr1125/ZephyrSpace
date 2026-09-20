# 耐克修复机械检查范围 v1

## 正式参数适配

本轮按裁决撤回正式定价，并允许评分区间，因此 `triplet_workpaper.py` 的原始schema无法忠实表达：它要求评分为单一有限数值、两个有效主模型、数值型目标价/确定性/买入价。为避免为过检填假数，正式底稿保留`score_range`与`null`价格。

已实际执行：

```powershell
python -X utf8 scripts/triplet_workpaper.py check data/reviews/nike-repair-2026-09-19-2310/final/workpaper-repaired-v1.json --repair --previous data/reviews/nike-repair-2026-09-19-2310/drafts/baseline-v1/workpaper.json --output data/reviews/nike-repair-2026-09-19-2310/final/triplet-check-repaired-v1.json
```

返回码为1。失败项包括：区间评分不是单一点值；正式模型撤回后不足两个；报告不再保留数值快照；加入区间/状态使未变项产生schema差异。这里的失败是工具能力边界，也提醒正式定价未闭合；未把它改写成通过。

## 扩展自检

`check_repaired_v1.py`实际覆盖：

- 32项评分均有定义、事实到评分理由、证据和点值/区间；
- 公司区间72.5–74.5、管理层区间68–70机械加总；
- 正式`target_price/certainty/buy_price`均为null，正式主模型数组为空；
- 8个稳定问题ID及其全部验收ID存在作者关闭声明；
- 三稿行数分别满足150/150/100；
- 可见正文不再把旧42.915639、34.213160、32.487138当作有效价格。

扩展自检不验证原件真实性、评分判断、模型经济合理性，也不等同两路独立复查。结果见 `selfcheck-repaired-v1.json`。
