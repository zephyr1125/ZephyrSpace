---
name: us-high-score-discovery
description: >-
  美股「未收录高分企业」筛查。Run A 建池：Tiger 选股器(仅市值≥USD300亿，无价格/PE门槛，~531家) → yfinance ~5年年报
  → 企业质量分(去估值；重盈利/现金流轻成长+高周转薄利豁免+ROE上限防回购失真) + 排金融/REIT + 覆盖标签 → 持久候选池；
  Run B 复核：每次只对池头未复核前 5~8 家做 AI+Web 精筛并写回状态。美股无批量管理层红旗 → 治理核在 Run B 逐家做。
  触发词：寻找高分美股 / 美股高分企业普查 / 未收录优质美股 / 不看价格找美股好公司
---

# 美股未收录高分企业筛查（us-high-score-discovery）

## 定位

A股/港股 `*-high-score-discovery` 的美股同款：**完全不看当前股价**，只从「企业质量能否支撑
B_GROWTH/A_CORE 级（深分≥70/76 + 管档≥70/76）」角度，粗排美股大中盘中尚未被本知识库深度覆盖的优质公司，
作为未来开「全面分析（三件套）」的上游候选清单。持久候选池 + 分批复核（无时间衰减 → 分批消化大列表）。

## 美股数据层 / 口径

| 项 | 美股做法 |
|---|---|
| 宇宙 | Tiger 选股器 `Market.US` 仅 `流通市值 ≥ USD 300亿`（实测 ~531 家），无价格/PE 门槛 |
| 财务 | yfinance 逐只 ~5 年年报（缓存 `data/cache/us_high_score_fs_cache.json`） |
| 行业 | yfinance `sector` 排金融 + `-REIT`；sector 缺失不剔 |
| 覆盖 | watchlist `.US`(81) + 低分登记 `.US`(14) 硬排；公司页/旧研究打标=「index 美股节 ticker ∪ 文件名 ticker」集合命中 |
| 管理层 | 无批量源 → 池内 `RunB核`，Run B 逐家 Web/Tavily 核 |
| 代码 | 池内 `TICKER.US`（board 纽/纳不在本池作用域，不臆断） |

沿用既定决策：宽松口径（有旧研究打标不排除）、分数≈深分 E 维粗排、不写 watchlist、不自动开三件套。

## 池文件

`data/screens/美股高分候选池.json`（状态源，review_status）+ `_YYYY-MM-DD.csv` + 上述 fs 缓存。

## Run A：建池 / 刷池（少跑，财报季后或半年）

```bash
python scripts/us_high_score_pool.py
# 参数：--min-cap 50 / --min-score 50 / --codes MAR,TJX / --limit 60 / --no-cache
```

- Tiger 现扫 + yfinance 缓存增量；首次 ~531 家 ~15-25 分钟后台，之后近零。
- 初值阈值 ≥70 Ⅰ候选 / 60–70 Ⅱ候选（首跑校准后回填）。

## Run B：分批复核（每次调用实际动作）

> 每次只精筛池头 pending 前 5~8 家（Ⅰ优先、全新优先）；美股管理层面每家都需 Web 核。

1. **取批**：读池 JSON，`pending` 且质量分最高 N 家。
2. **逐家**：读池快照校验 → **管理层/红旗 Web 核** → 有旧研究选跳过/更新，全新认真评。
   **美股管理核清单**：DEF 14A 控制权（B类股/受控公司/同股不同权/创始人超级投票权）；审计师是否四大/保留意见/
   频繁换所；**非 GAAP vs GAAP 盈利质量**（SBC、一次性收益，Forward 与 TTM 背离即信号）；被做空/沽空史；
   大股东减持/质押；处罚/诉讼；回购与派息史（高回购+负权益要注意 ROE 失真）。
3. **判定**：建议开三件套 / 疑点需深挖 / 排除（红旗证据实）。
4. **主 Agent 写回** review_status/reviewed_date/notes。
5. 对话小摘要 + 强推 2~3 家「建议全面分析 XXX」。

## 质量分口径（脚本 quality_score，与港股共享）

growth20 + profit28 + cash27 + capital20 + 股本5 − 惩罚。要点：
- 重盈利/现金流轻成长 + **高周转薄利豁免**（ROE≥18 且现金转化好且无 OCF 负年 → 低毛利/低净利不拖累）；
- **ROE 均值/最差年，分母仅取正权益、上限 45%**（回购致负/极小权益失真，TJX 名义 ROE 57%、Marriott 可上千仍按 45 封顶计分）；
- NaN→中性 35（严禁泄漏进 clamp 假满分）；无审计/分红史维度。

惩罚：增速异常、利润增速脱节、ROE>40、应收增速>营收、OCF3Y萎缩>5%、多数年FCF为负、股本膨胀>2%、OCF负年数≥3。

## 注意事项

1. **覆盖标签非硬排**：纯中文页名（如 微软.md）无法反推 ticker → 已研究且不在 watchlist 的名字可能被标「全新」。
   Run B 复核前可 `grep 01-公司/` 简称兜底；被推荐后开三件套前也自查有无美股旧档。
2. **REIT/金融已排除**；伯克希尔等控股投资公司 sector 可能归 Insurance/Financial → 也被剔除（可接受，需研究走单独路径）。
3. **SBC 与调整后 EPS**：池内指标用 GAAP 净利；Run B 务必核对调整后口径差异再判质量分可信度。
4. **高 ROE 失真名**（如 Marriott ROE 415%）评分已封顶，但 CSV 展示原始 ROE 会吓人——看分数别被原始列误导。

## 与三件套的关系

上游候选生成器。Run B 推荐 → 用户触发「全面分析 XXX」。本 skill 不写 watchlist、不自动开三件套。
