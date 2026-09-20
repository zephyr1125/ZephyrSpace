# 估值：通用约束与计算核心规则：examples

由本模块 SKILL.md 按条件路由；不要求所有角色每次通读。来源优先级、调度、修复轮次、提交和回写权限服从统一 SOP。

<!-- migrated:part-15:start -->
## 示例：国电南瑞

```
触发：使用合适算法对国电南瑞估值

→ 第0步：复用共享证据，统一理杏仁行情与财务，核官方披露及最新期别，按需补预测
→ 第1步：选择正向现金流模型 + 有独立可比依据的PE，反向DCF只验证隐含增长（权重0）
→ 第2步：两主模型各做三情景、敏感性与独立性说明；以下26.7元仅为流程演示，非真实估值
→ 第3步：确定最终加权合理估值 26.7 元
→ 第4步：grep data/watchlist_*.json → 命中 watchlist_core.json
          独立评估 valuation_certainty=0.82
          更新 target_price=26.7, valuation_certainty=0.82
          自动计算 buy_price=26.7×(0.68+0.14×0.82)=21.22（不写入Watchlist）
          运行 sync_watchlist.ps1
→ 第5步：告知用户「已更新 watchlist_core.json 国电南瑞 target_price」
```

---

<!-- migrated:part-15:end -->
