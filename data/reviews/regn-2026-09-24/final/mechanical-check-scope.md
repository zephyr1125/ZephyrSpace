# REGN 终审稿机械检查范围（模型适配记录）

依 `docs/three-report-workpaper.md`「模型适配边界」：复杂或经裁决变更的模型无法由标准工具忠实表达时，保留适用经济模型，复用本次 `calculate.py` 做扩展机械检查，并记录本文件。**不为迁就工具简化模型。**

## 为什么不使用标准工具的主模型计数校验

标准工具 `scripts/triplet_score_flow.py check` 要求 `valuation.models` 至少含两个**正权重**主模型（报错原文：「缺两个主模型，不能用确定性折扣补足」「有效主模型权重必须为正」）。

终审裁决明确要求另一种结构：

- **单一赋权主模型**（M1 经营价值模型，权重 1.0）；
- **零权重诊断折现模型**（M2，置于 `valuation.diagnostic_model`，无 `weight` 字段），理由是其 2031 年起的侵蚀路径依赖 Dupixent 专利族到期节奏假设，该时点在年报中分散披露（美国核心物质专利 2031-03-28、剂型 2032-10-17、治疗方法 2034-07-10 及更晚），无可核事实依据可定价。

因此「两个正权重主模型」这一项**结构性不满足**，属已裁决的模型适配，不是遗漏。**该未覆盖项在此显式记为待人工确认，不伪装为通过。**

## 覆盖矩阵

| 检查项 | 由谁覆盖 | 结果 |
|---|---|---|
| 分项上限（25 项公司 + 7 项管理层） | `calculate.py` | 通过 |
| 显式封闭档位（A3 / D1 / F2 / C1 / C2 / C3+C4 / F2.5，含 F2.5 正面先例 +0.5） | `calculate.py` | 通过 |
| 分项证据引用已注册（facts.json 的 fact_id + sources.json 的 source_id） | `calculate.py` | 通过 |
| 公司 / 管理层总分闭合；合计 = 167 | `calculate.py` | 通过 |
| 六维度未超限且高于满分 40% 红线 | `calculate.py` | 通过 |
| M1 三情景公式复算（标量表达式求值） | `calculate.py` | 通过 |
| M1 双变量敏感性 3×3 逐格复算，含基准输入 | `calculate.py` | 通过 |
| M1 每个输入变量均有 `input_meta` 且 kind 合法 | `calculate.py` | 通过 |
| `weighted` 与 M1 一致；`target_price = round(weighted.base)`；`buy_price` 公式 | `calculate.py` | 通过 |
| M2 三情景与敏感性逐格复算 | `calculate.py` | 通过 |
| 诊断模型未参与合理价（`target_price` 仅由 M1 决定） | `calculate.py` | 通过 |
| 反向验证权重 0、代回市价、隐含变量在 inputs 内 | `calculate.py` | 通过 |
| 桥闭合（起点 + 带符号变动 = 终点）及引用已注册 | `calculate.py` | 通过 |
| **「两个赋权主模型」**（标准工具 `triplet_score_flow.py`） | **未覆盖——已裁决的模型适配** | **待人工确认** |

## 运行方式与版本

```powershell
python -X utf8 data/reviews/regn-2026-09-24/writer/calculate.py
```

- 输入：`data/reviews/regn-2026-09-24/writer/workpaper-v2.json`、`data/reviews/regn-2026-09-24/evidence/facts.json`、`data/reviews/regn-2026-09-24/evidence/sources.json`
- 输出：退出码 0（通过）；控制台打印检查项数、失败项、最终参数
- 本次结果：**检查项 281，失败 0**
- 分数与估值的语义充分性、假设合理性、引用是否真对应原件，仍由人工与两路复核负责——机械通过不等于研究通过。

## 相关版本

- `workpaper-v1.json`：两路独立复核所依据的冻结稿（公司 81.0 / 管理层 80.0，目标价 846.24）。
- `workpaper-v2.json`：终审裁决后的交付稿（公司 83.0 / 管理层 84.0，目标价 785.00，确定性 0.45，买入价 583.26）。
- 两版差异见 `decision-final.json` 与本 run 的 `final/decision-closeout.json`。
