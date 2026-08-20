# 泡泡玛特 IP 监控

> 周期：每周日运行 | 自动化等级：半自动 | 最后运行：2026-08-17

## 定位

对泡泡玛特旗下 IP（THE MONSTERS/Labubu、Molly、Skullpanda、Crybaby、Dimoo 等）进行二级市场价格、社媒热度、卖盘压力和 IP 扩散情况的周度跟踪，输出 IP 健康度评分和趋势判断。

**不分析财报，不估值建模，不给买卖建议。**

## 核心问题

1. 泡泡玛特是否仍然是单一 IP（Labubu）驱动？
2. Labubu 热度是否衰退、扩散或继续强化？
3. 非 Labubu IP 是否具备持续生命力？
4. 市场热度来自真实消费者还是黄牛投机？

## 报告索引

| 日期 | Labubu 健康度 | 多 IP 扩散度 | 核心判断 | 报告 |
|------|:---:|:---:|---|---|
| 2026-06-29 | 58/C (Labubu) / 62/C (Molly) | 0% (0/5 A/B) | 🔴 边际转弱 | [[2026-06-29\|查看]] |
| 2026-07-05 | 42/D (Labubu) / 58/C (Molly) / 48/D (Skullpanda) | 0% (0/5 A/B) | 🔴 边际转弱加速，Labubu跌入D档 | [[2026-07-05\|查看]] |
| 2026-07-12 | 40/D (Labubu) / 63/C (DIMOO) / 56/C (Molly) | 0% (0/5 A/B) | 🟡 Labubu边际走弱，多IP接力信号出现 | [[2026-07-12\|查看]] |
| 2026-07-19 | 35–40/D (Labubu) / ~58–62/C (Molly) / ~58–61/C (DIMOO) / ~55–58/C (Crybaby) / ~55–58/C (Twinkle) / ~53–56/C (Skullpanda) | 0% (0/6 A/B) | 🟡 Labubu投机退潮较强验证，多IP运营动作集中落地，接力候选信号增强 | [[2026-07-19\|查看]] |
| 2026-07-26 | ~35–40/D (Labubu) / ~62–65/C (Molly) / ~62–64/C (DIMOO) / ~58–60/C (Crybaby) / ~55–58/C (Twinkle) / ~54–56/C (Skullpanda) / ~48–52/C (HACIPUPU) | 0% (0/7 A/B) | 🟡 Labubu投机退潮强验证（产能50x扩张），DIMOO获L3流量验证+菲律宾主题店，HACIPUPU首期入榜，H1中报8/20-25为最重要催化剂 | [[2026-07-26\|查看]] |
| 2026-08-02 | ~35–38/D (Labubu) / ~62–65/C (Crybaby) / ~62–65/C (Molly) / ~60–63/C (DIMOO) / ~55–58/C (Twinkle) / ~52–55/C (Skullpanda) / ~48–52/C (HACIPUPU) | 0% (0/7 A/B) | 🟡 CRYBABY异军突起取代DIMOO成最强接力候选——特展开幕L3确认+SK-II联名；DIMOO皮克斯L4缺失2.5周进入「验证焦虑」；Labubu投机退潮进入稳定期；H1中报8/17-20为最重要催化剂 | [[2026-08-02\|查看]] |
| 2026-08-12 | ~35–38/D (Labubu) / ~66–69/**B** (DIMOO) / ~64–67/**B** (Molly) / ~64–67/**B** (Crybaby) / ~58–61/C (Twinkle) / ~58–61/C (Skullpanda) / ~48–52/C (HACIPUPU) | **43% (3/7 A/B)** 🆕 历史性突破 | 🟢 抖音7月排行榜四IP获L4销售验证(DIMOO#1/CRYBABY/星星人/SKULLPANDA TOP10)；DIMOO+Molly+Crybaby首次突破B线；多IP健康从「候选信号」升级为「L4初步验证」；城市乐园重资产开放；H1中报8/20终极检验 | [[2026-08-12\|查看]] |
| 2026-08-17 | ~34–37/D (Labubu) / ~66–69/**B** (DIMOO) / ~65–68/**B** (Crybaby) / ~64–67/**B** (Molly) / ~59–62/C (Skullpanda) / ~57–60/C (Twinkle) / ~48–52/C (HACIPUPU) | **43% (3/7 A/B)** 持平 | 🟡 整体高位稳定+H1中报前静默期。3 IP维持B线。本周增量均为供给侧L1-L2——Skullpanda MEGA产品页上线打破五周停滞、CRYBABY Care Bears确认7 SKU完整系列。Labubu进入锚点真空(Wings六周无数据降级状态未知)。段永平1亿茅台赌局+重申从没卖过一股。8/20 H1中报是分水岭 | [[2026-08-17\|查看]] |

## 快速运行

```
/popmart-ip-monitor
```

或直接说"泡泡玛特IP监控"、"popmart monitor"。

## 相关文件

- 公司页：[[泡泡玛特]]
- 管理层档案：[[泡泡玛特 管理层档案 79 2026-05-31]]
- Skill 定义：`popmart-ip-monitor/SKILL.md`
- 监控配置：`popmart-ip-monitor/config/watchlist.yaml`
