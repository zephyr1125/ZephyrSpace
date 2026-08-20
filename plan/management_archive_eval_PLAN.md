# Management Archive Skill Eval Plan

> 目标：为项目内建 Skill `management-archive` 建立一套可重复、可量化、可回归、可做 A/B 对比的 Eval Harness，用于持续提升 Skill 的事实准确性、工具调用质量、证据支撑能力、评分一致性和最终产出质量。

---

## 1. 背景与目标

当前 `management-archive` Skill 已经具备完整工作流：

- 明确触发条件；
- 多数据源拉取；
- 结构化 11 章节输出；
- 100 分制管理层评分；
- 双 Agent 审核；
- P0 / P1 / P2 问题分级；
- P1 修复后的评分联动检查；
- 公司页 / 深度分析页交叉引用；
- M1-M8 高频错误模式总结。

因此本 Eval 系统不应只评价“最终报告写得好不好”，而应对整个 Skill Workflow 进行分层测试。

核心目标：

1. 能回答：一次 Skill 修改究竟有没有提升。
2. 能发现：提升发生在哪些维度、退化发生在哪些维度。
3. 能防止：历史错误重新出现。
4. 能区分：事实错误、流程遗漏、分析偏差、格式错误、评分漂移。
5. 能支持：`SKILL.md vN` vs `SKILL.md vN+1` 的 A/B 对比。
6. 能让失败 case 自动沉淀为 regression test。

---

# 2. 总体架构

建议使用：

```text
pytest
+
自定义 deterministic validators
+
DeepEval（或等价 LLM-as-a-Judge 框架）
+
Agent Trace / Tool Call Recorder
```

整体执行流程：

```text
                     ┌────────────────────┐
                     │ SKILL.md candidate │
                     └─────────┬──────────┘
                               ↓
                       Run Eval Dataset
                               ↓
        ┌──────────────────── Eval Pipeline ────────────────────┐
        │                                                       │
        │  1. Trigger Eval                                      │
        │  2. Workflow / Tool Eval                              │
        │  3. Deterministic Structure Eval                      │
        │  4. Fact Accuracy Eval                                │
        │  5. Evidence Grounding Eval                           │
        │  6. Analytical Quality Judge                          │
        │  7. Score Calibration / Consistency Eval              │
        │  8. Regression Tests                                  │
        │                                                       │
        └─────────────────────────┬─────────────────────────────┘
                                  ↓
                          Generate Eval Report
                                  ↓
                        Compare baseline / candidate
                                  ↓
                           Keep / Reject change
```

---

# 3. 推荐项目目录

```text
evals/
├── README.md
├── config.yaml
│
├── cases/
│   └── management_archive/
│       ├── trigger/
│       │   ├── positive.yaml
│       │   └── negative.yaml
│       │
│       ├── companies/
│       │   ├── case_001.yaml
│       │   ├── case_002.yaml
│       │   ├── case_003.yaml
│       │   └── ...
│       │
│       └── regression/
│           ├── M1_current_management_identity.yaml
│           ├── M2_penalty_event_separation.yaml
│           ├── M3_action_vs_outcome.yaml
│           ├── M4_financing_instruments.yaml
│           ├── M5_bidirectional_share_transactions.yaml
│           ├── M6_announced_vs_executed_buyback.yaml
│           ├── M7_quote_context_integrity.yaml
│           └── M8_management_turnover_timeline.yaml
│
├── fixtures/
│   ├── golden_facts/
│   │   ├── company_001.yaml
│   │   ├── company_002.yaml
│   │   └── ...
│   │
│   ├── frozen_sources/
│   │   └── ...
│   │
│   └── expected_outputs/
│       └── ...
│
├── graders/
│   ├── trigger.py
│   ├── workflow.py
│   ├── structure.py
│   ├── facts.py
│   ├── grounding.py
│   ├── score_consistency.py
│   ├── analytical_quality.py
│   ├── regression.py
│   └── common.py
│
├── runners/
│   ├── run_skill.py
│   ├── trace_recorder.py
│   ├── run_eval.py
│   └── compare_runs.py
│
├── schemas/
│   ├── case.schema.json
│   ├── golden_facts.schema.json
│   ├── trace.schema.json
│   └── result.schema.json
│
├── reports/
│   └── .gitkeep
│
└── tests/
    ├── test_trigger.py
    ├── test_structure.py
    ├── test_facts.py
    ├── test_grounding.py
    ├── test_workflow.py
    ├── test_score_consistency.py
    └── test_regressions.py
```

---

# 4. Eval Dataset 设计

## 4.1 第一阶段 MVP

先不要一开始做 30 家。

第一阶段建议：

```text
5 家公司
+
20-30 个 Trigger Cases
+
8 个 M1-M8 Regression Cases
```

目的：

- 先跑通 Eval Infrastructure；
- 验证 trace 能不能记录；
- 验证 grader 是否稳定；
- 验证 Golden Facts 的维护成本；
- 验证一次完整 eval 的成本和耗时。

MVP 跑通后扩展到：

```text
20-30 家公司
```

---

## 4.2 公司样本分层

完整 Dataset 建议覆盖：

| 类型 | 数量建议 | 测试重点 |
|---|---:|---|
| 大型优质公司 | 4-5 | 正常路径 |
| 管理层存在明显争议 | 4-5 | 反证、红旗识别 |
| 高管变动频繁 | 3 | 组织与人才 |
| 并购 / 融资频繁 | 3 | 资本配置 |
| 国企 / 央企 | 3 | 评分框架适配 |
| 小市值 / 资料少 | 3 | 不确定性处理 |
| 港股公司 | 3 | 数据源切换 |
| 明确监管处罚案例 | 2-3 | 合规检索 |

避免只选择“好公司”。

Dataset 必须刻意包含：

- 容易误判；
- 数据口径复杂；
- 管理层发生变化；
- 多监管机构处罚；
- 分红 / 回购 / 融资混合；
- 有明显言行不一致；
- 公开资料不足。

---

# 5. Case Schema

每个公司 Eval Case 使用 YAML。

示例：

```yaml
id: management_archive_001

company:
  name: 示例公司
  ticker: 000001.SZ
  market: A

prompt: "管理层档案 示例公司"

tags:
  - a_share
  - management_turnover
  - regulatory_penalty

expected_behavior:
  should_trigger: true
  should_generate_archive: true
  should_update_company_page: true

golden_facts_file:
  fixtures/golden_facts/000001.SZ.yaml

required_workflow:
  company_profile: true
  executive_trades: true
  dividends: true
  penalties: true
  lawsuits: true
  pledge: true
  irm_qa: true
  personnel_announcements: true
  lixinger_profile: true
  lixinger_measures: true
  lixinger_inquiry: true
  wisburg_earnings_calls: true

expected_sections:
  - 一、管理层画像
  - 二、言行一致性追踪
  - 三、资本配置记录
  - 四、对股东友好度
  - 五、危机处理记录
  - 六、组织与人才
  - 七、互动易/IR 态度
  - 八、监管与合规记录
  - 九、管理层 100 分制评分
  - 十、关键原文摘录
  - 十一、综合结论
```

---

# 6. Golden Facts 设计

Golden Facts 不需要保存“整篇标准答案”。

只维护：

- 高价值；
- 可明确核验；
- 错误代价高；
- 容易被模型写错；

的事实。

示例：

```yaml
company:
  name: 示例公司
  ticker: 000001.SZ

critical_facts:

  chairman:
    value: 张三
    as_of: 2026-08-01
    severity: P0
    source_required: true

  ceo:
    value: 李四
    as_of: 2026-08-01
    severity: P0
    source_required: true

management_changes:
  - person: 王五
    role: CTO
    event: resignation
    date: 2025-06-12
    severity: P1

penalties:
  - date: 2024-03-15
    regulator: XX监管局
    amount_cny: 500000
    event: XX违规
    severity: P0

capital_actions:
  - type: buyback
    year: 2025
    actual_amount_cny: 1830000000
    announced_upper_bound_cny: 2500000000
    severity: P1

known_positive_cases:
  - id: commitment_dividend_2022
    claim: 2022年承诺提升股东回报
    outcome: 2023年提高派息

known_red_flags:
  - id: management_turnover_2024
    description: 12个月内3名核心高管离职

forbidden_claims:
  - "近五年核心管理层完全稳定"
```

---

# 7. Eval Layer 1：Trigger Eval

## 7.1 Positive Cases

例如：

```text
管理层档案 腾讯
老板档案 美的集团
看看 XXX 管理层靠不靠谱
管理层尽调 XXX
全面分析 XXX
给 XXX 建长期管理层档案
```

Expected：

```text
should_trigger = true
```

---

## 7.2 Negative Cases

例如：

```text
腾讯现在 PE 多少？
美的最近股价为什么跌？
长江电力的自由现金流是多少？
XXX 当前估值是否便宜？
```

Expected：

```text
should_trigger = false
```

---

## 7.3 Metrics

```text
Trigger Accuracy
Precision
Recall
False Positive Rate
False Negative Rate
```

建议 Gate：

```text
Accuracy >= 95%
False Positive Rate <= 5%
```

---

# 8. Eval Layer 2：Workflow / Tool Eval

目标：

评价 Agent 是否按照 Skill 规定真正执行工作流。

必须保存 Agent trace，包括：

```json
{
  "tool_name": "...",
  "arguments": {},
  "timestamp": "...",
  "result_status": "...",
  "parent_step": "..."
}
```

---

## 8.1 Required Tool Recall

```text
实际完成的 required actions
----------------------------
应执行的 required actions
```

例如：

```text
Required Tool Recall >= 95%
```

---

## 8.2 Tool Argument Correctness

重点检查：

- 股票代码；
- 市场；
- 日期范围；
- 人事公告时间窗口；
- 公司名；
- 港股 / A 股接口选择；
- 电话会 detail 是否真正读取；
- 行业监管关键词是否符合行业。

---

## 8.3 Tool Efficiency

避免：

- 同一个 API 无意义重复调用；
- 已经取得原始数据后重复 Tavily；
- 为简单事实进行大量泛搜索；
- 不必要地重新读取整个文件。

指标：

```text
Duplicate Tool Call Count
Redundant Search Count
Average Tool Calls / Case
Cost / Case
Latency / Case
```

这些指标不建议作为强 Gate，而用于版本比较。

---

# 9. Eval Layer 3：Deterministic Structure Eval

凡是程序可以明确判断的内容，不使用 LLM Judge。

---

## 9.1 文件命名

必须符合：

```text
[公司简称] 管理层档案 [评分] YYYY-MM-DD.md
```

Regex 示例：

```python
r"^.+ 管理层档案 ([0-9]|[1-9][0-9]|100) \d{4}-\d{2}-\d{2}\.md$"
```

---

## 9.2 行数

```python
line_count >= 150
```

---

## 9.3 章节完整性

11 个章节全部必须存在。

缺任意一个：

```text
FAIL
```

---

## 9.4 快速参考卡

检查：

```text
📊 快速参考
```

必须位于正文分析之前。

---

## 9.5 Frontmatter

检查必须字段：

```yaml
aliases:
公司:
股票代码:
分析日期:
数据截止日期:
```

---

## 9.6 股票代码格式

允许：

```text
XXXXXX.SH
XXXXXX.SZ
XXXXX.HK
TICKER.US
```

---

## 9.7 评分算术

检查：

```text
诚信与透明度 <= 20
资本配置能力 <= 25
战略稳定性 <= 15
对股东友好度 <= 15
危机处理能力 <= 10
组织与人才能力 <= 10
表达清晰度与认知质量 <= 5
```

并且：

```python
sum(dimensions) == total_score
```

---

## 9.8 红旗规则

```python
if integrity <= 8 or capital_allocation <= 10:
    assert red_flag_present
```

---

## 9.9 Rating Mapping

```text
85-100 -> 卓越
70-84  -> 优秀
55-69  -> 良好
40-54  -> 一般
<40    -> 不达标
```

评分与评级不匹配：

```text
FAIL
```

---

## 9.10 Backlink

检查：

```text
01-公司/[公司简称].md
```

是否存在对应管理层档案链接。

若存在深度分析页：

检查深度分析页是否存在对应引用。

---

# 10. Eval Layer 4：Fact Accuracy Eval

这是最高优先级之一。

---

## 10.1 Fact Extraction

从最终 Markdown 抽取结构化数据：

```json
{
  "chairman": "",
  "ceo": "",
  "controller": "",
  "management_changes": [],
  "penalties": [],
  "dividends": [],
  "buybacks": [],
  "financing": [],
  "pledges": [],
  "capital_actions": []
}
```

可以：

1. 优先使用 Markdown parser + regex；
2. 无法稳定解析的部分再使用结构化 LLM extractor。

注意：

Extractor 不参与评价，只负责 extraction。

---

## 10.2 Fact Precision

```text
正确输出的事实
--------------
所有可评价输出事实
```

---

## 10.3 Fact Recall

```text
成功发现的 Golden Facts
-----------------------
Golden Facts 总数
```

---

## 10.4 Critical Fact Accuracy

单独统计：

- 董事长；
- CEO；
- 实控人；
- 处罚金额；
- 处罚机构；
- 核心融资金额；
- 核心回购实际金额；
- 重大离任事件。

建议：

```text
Critical Fact Accuracy >= 98%
```

---

# 11. Eval Layer 5：Evidence Grounding Eval

目标：

避免：

```text
事实是真的
≠
结论被事实支持
```

---

## 11.1 Claim Extraction

提取主要判断：

```text
管理层资本配置克制
管理层重视股东回报
团队稳定性较差
管理层在危机处理中透明度高
战略连续性较强
```

---

## 11.2 Evidence Binding

为每个 Claim 找到报告中绑定的：

- 原文；
- 年报；
- 电话会；
- API 数据；
- 时间线；
- 监管记录；

形成：

```json
{
  "claim": "...",
  "evidence": ["...", "..."]
}
```

---

## 11.3 Judge Rubric

```text
0 = Evidence contradicts claim
1 = Evidence unrelated / insufficient
2 = Weak support
3 = Strong support
```

计算：

```text
Grounded Claim Rate
=
score >= 2 的关键 Claim
----------------------
所有关键 Claim
```

建议 Gate：

```text
Grounded Claim Rate >= 90%
```

---

# 12. Eval Layer 6：Analytical Quality Judge

只评价无法完全 deterministic 的分析质量。

使用 LLM-as-a-Judge。

Judge Prompt 应独立于生产 Skill。

不要使用生产环境中的 Agent A / Agent B 作为外部 Judge。

---

## 12.1 反证质量

评分 1-5：

```text
5 = 主动寻找多个反例，且反证实质影响结论
4 = 有明确、有效的反证讨论
3 = 有负面材料，但没有充分进入最终判断
2 = 主要是确认偏误
1 = 基本没有寻找反证
```

---

## 12.2 言行一致性质量

重点判断：

是否正确区分：

```text
执行了承诺动作
```

与：

```text
承诺结果真正兑现
```

---

## 12.3 资本配置分析质量

不能只判断：

```text
分红高 = 好
融资多 = 差
```

应判断：

```text
当时资本用途
+
选择理由
+
机会成本
+
执行结果
+
ROIC / ROI
+
周期位置
```

---

## 12.4 战略稳定性分析

判断：

- 是否只是统计关键词；
- 是否真正建立跨年战略时间线；
- 是否识别战略变化是合理调整还是频繁摇摆。

---

## 12.5 危机处理质量

判断：

- 是否识别危机；
- 管理层是否及时响应；
- 是否承担责任；
- 是否采取行动；
- 是否建立后续机制。

---

## 12.6 不确定性处理

资料不足时：

正确：

```text
信息不足 / 待核实
```

错误：

```text
根据有限信息强推确定结论
```

---

# 13. Eval Layer 7：Score Calibration

目标：

防止：

- 报告整体偏好，但评分过低；
- 报告出现严重治理问题，但仍给 90+；
- 不同公司评分尺度漂移。

---

## 13.1 Internal Score Consistency

检查：

```text
正文证据
↓
维度评价
↓
维度分数
↓
总分
↓
评级
↓
一句话结论
↓
类型定位
```

是否一致。

---

## 13.2 Pairwise Calibration

不要要求 Golden Score 精确到个位数。

建议做相对排序：

```text
Company A 的管理层明显优于 Company B
```

Expectation：

```text
score(A) > score(B)
```

这样比：

```text
Company A 必须 = 87
```

更稳定。

---

## 13.3 Score Drift

保存 baseline：

```text
company -> baseline score
```

若新版本：

```text
abs(candidate - baseline) > threshold
```

例如：

```text
> 8 分
```

自动要求生成：

```text
Score Drift Explanation
```

判断是：

- 事实更新；
- 新证据；
- Skill 改进；
- 评分漂移。

---

# 14. P0 / P1 / P2 Eval Gate

沿用 Skill 自身问题等级。

---

## P0

典型：

- 管理层姓名错误；
- CEO / 董事长角色写反；
- 处罚金额差数量级；
- 评分算术不闭合；
- 文件指向错误公司；
- 引用不存在的事实。

规则：

```text
P0 count > 0
=> RUN FAIL
```

---

## P1

典型：

- 重要事实遗漏；
- 时间线错位；
- 评分与证据不匹配；
- 资本配置金额口径错误；
- 来源缺失；
- 高管密集离任模式遗漏；
- 行业处罚遗漏。

建议：

```text
P1 count <= predefined tolerance
```

完整版本建议最终做到：

```text
Critical P1 = 0
```

---

## P2

典型：

- 模糊表述；
- 形容词略重；
- 格式小瑕疵；
- 次要来源标记问题。

不阻塞总体 Eval。

---

# 15. M1-M8 转换为永久 Regression Tests

Skill 当前已有 M1-M8 高频坑。

必须全部转为自动 Regression Case。

---

## M1：管理层信息依赖陈旧记忆

Test：

```text
test_current_management_identity
```

验证：

- 董事长为最新；
- CEO 为最新；
- 任期正确；
- 不能使用历史人物替代现任。

---

## M2：处罚事件合并

Test：

```text
test_penalty_event_separation
```

验证：

- 独立处罚必须分行；
- 年份；
- 机构；
- 金额；
- 状态；

不得合并。

---

## M3：动作 ≠ 兑现

Test：

```text
test_action_vs_outcome
```

输入一家公司：

```text
承诺扩产
实际完成 Capex
但没有达到结果指标
```

期望：

```text
⏳ 执行中
```

不能：

```text
✅ 已兑现
```

---

## M4：融资工具遗漏

Test：

```text
test_all_financing_instruments
```

必须覆盖：

- A 股增发；
- 配股；
- 可转债；
- H 股增发；
- 优先股；
- 股权激励摊薄。

---

## M5：减持忽略增持

Test：

```text
test_bidirectional_share_transactions
```

若期间存在：

```text
增持 + 减持
```

禁止写：

```text
持续减持
```

---

## M6：公告金额 vs 实际执行金额

Test：

```text
test_announced_vs_executed_buyback
```

要求：

主要评价使用：

```text
实际执行金额
```

不能使用计划上限替代。

---

## M7：原文断章取义

Test：

```text
test_quote_context_integrity
```

若原文：

```text
在需求恢复的条件下，我们预计收入增长 20%
```

禁止摘成：

```text
我们预计收入增长 20%
```

---

## M8：高管变动未建立时间线

Test：

```text
test_management_turnover_timeline
```

检查：

- 最近 5 年；
- 离任人；
- 原因；
- 接任者；
- 接任来源；
- 12 个月内密集离任模式。

---

# 16. Production Review 与 External Eval 必须分离

现有：

```text
初稿
↓
Agent A
↓
Agent B
↓
P1 修复
↓
终稿
```

这是：

```text
Production Workflow
```

不能当作 Eval。

必须新增独立层：

```text
             Production
                 ↓
            Final Output
                 ↓
================================
          External Eval Harness
================================
                 ↓
          Independent Graders
```

Judge：

- 使用不同 Prompt；
- 最好使用独立模型；
- 不读取生产 Agent 的评分结论；
- 独立访问最终报告、trace、golden facts。

---

# 17. Eval 总评分

建议初始权重：

| Dimension | Weight |
|---|---:|
| Trigger Correctness | 5 |
| Workflow / Tool Correctness | 15 |
| Deterministic Structure | 10 |
| Critical Fact Accuracy | 25 |
| Evidence Grounding | 20 |
| Analytical Quality | 15 |
| Score Calibration | 5 |
| Regression Stability | 5 |
| **Total** | **100** |

---

# 18. Hard Gates

综合分不代表一定 PASS。

建议：

```yaml
gates:

  p0_errors:
    max: 0

  critical_fact_accuracy:
    min: 0.98

  grounded_claim_rate:
    min: 0.90

  required_tool_recall:
    min: 0.95

  trigger_accuracy:
    min: 0.95

  score_math:
    required: true

  required_sections:
    required: true

  minimum_lines:
    value: 150
```

任何 Hard Gate 不通过：

```text
Overall Status = FAIL
```

即使：

```text
Weighted Score = 94
```

也仍然 FAIL。

---

# 19. Eval Result Schema

每个 Case 输出：

```json
{
  "case_id": "management_archive_001",
  "skill_version": "v18",

  "status": "PASS",

  "scores": {
    "trigger": 1.0,
    "workflow": 0.94,
    "structure": 1.0,
    "facts": 0.98,
    "grounding": 0.91,
    "analysis": 0.84,
    "calibration": 0.88
  },

  "weighted_score": 92.4,

  "gates": {
    "p0": true,
    "critical_fact_accuracy": true,
    "grounded_claim_rate": true
  },

  "errors": [
    {
      "severity": "P1",
      "category": "management_turnover",
      "message": "遗漏 2025 年 CTO 离任"
    }
  ],

  "metrics": {
    "tool_calls": 19,
    "duplicate_tool_calls": 1,
    "runtime_seconds": 183,
    "estimated_cost": 3.71
  }
}
```

---

# 20. Run Report

每次 Eval Run 输出：

```text
reports/
└── 2026-08-20_v18/
    ├── summary.md
    ├── summary.json
    ├── cases/
    │   ├── case_001.json
    │   ├── case_002.json
    │   └── ...
    ├── failures.md
    ├── regressions.md
    └── traces/
```

---

# 21. summary.md 内容

至少包括：

```text
Skill Version
Git Commit
Model
Judge Model
Dataset Version
Cases
Pass Rate
Weighted Score
P0 Count
P1 Count
Critical Fact Accuracy
Grounded Claim Rate
Required Tool Recall
Average Tool Calls
Average Cost
Average Runtime
```

并输出：

```text
Top Failure Categories
```

例如：

| Failure | Count |
|---|---:|
| 行业监管遗漏 | 4 |
| 高管时间线遗漏 | 3 |
| 引用不足 | 2 |
| 回购金额口径 | 2 |

---

# 22. Skill A/B Comparison

必须支持：

```bash
python -m evals.runners.run_eval \
    --skill skills/management-archive/SKILL_v17.md \
    --run-name v17
```

以及：

```bash
python -m evals.runners.run_eval \
    --skill skills/management-archive/SKILL_v18.md \
    --run-name v18
```

然后：

```bash
python -m evals.runners.compare_runs \
    reports/v17 \
    reports/v18
```

输出：

| Metric | v17 | v18 | Δ |
|---|---:|---:|---:|
| Total | 81.3 | 86.7 | +5.4 |
| Facts | 91% | 96% | +5% |
| Grounding | 88% | 92% | +4% |
| Tool Recall | 82% | 95% | +13% |
| P0 | 2 | 0 | -2 |
| P1 | 11 | 6 | -5 |
| Tool Calls | 18.2 | 21.4 | +3.2 |
| Cost | 3.8 | 4.5 | +0.7 |

---

# 23. Candidate Skill 接受条件

建议：

```text
candidate 必须：
```

1. 所有 Hard Gates PASS；
2. P0 不增加；
3. Regression 不退化；
4. Critical Facts 不退化；
5. 总分提升或保持；
6. 如果成本明显增加，必须有对应质量收益；
7. 如果某一高权重维度退化 > 3%，必须人工 review。

---

# 24. Failure Clustering

每次 Eval 后自动把问题分类：

```text
FACT_CURRENT_MANAGEMENT
FACT_PENALTY
FACT_CAPITAL_ACTION
FACT_DIVIDEND
FACT_SHARE_TRANSACTION

WORKFLOW_MISSING_SOURCE
WORKFLOW_WRONG_MARKET
WORKFLOW_REDUNDANT_SEARCH

GROUNDING_UNSUPPORTED_CLAIM
GROUNDING_QUOTE_CONTEXT

ANALYSIS_CONFIRMATION_BIAS
ANALYSIS_ACTION_VS_OUTCOME
ANALYSIS_CAPITAL_ALLOCATION

SCORE_INCONSISTENCY
SCORE_DRIFT

FORMAT_SECTION_MISSING
FORMAT_FILENAME
FORMAT_BACKLINK
```

输出：

```text
Failure Frequency
×
Severity
```

用于决定下一次修改 Skill 的优先级。

---

# 25. Skill Optimizer Loop

长期工作方式：

```text
Eval
 ↓
失败聚类
 ↓
选择最高频 / 最高严重度问题
 ↓
修改 SKILL.md
 ↓
新增 regression case
 ↓
重新 Eval
 ↓
A/B compare
 ↓
Keep / Reject
```

核心原则：

```text
每修复一种历史错误
=
Skill 修改
+
至少一个永久 Regression Test
```

禁止：

```text
只修改 Skill
但不增加 Regression Case
```

否则未来极易复发。

---

# 26. Frozen Eval 与 Live Eval

建议未来拆成两套。

---

## Frozen Eval

数据源固定。

用途：

```text
纯测试 Skill Prompt / Workflow 改动
```

优点：

- 可复现；
- A/B 公平；
- 不受最新公告影响。

---

## Live Eval

直接使用当前 API / Web。

用途：

```text
测试真实生产表现
```

缺点：

- 数据会变化；
- 公司管理层会变化；
- 搜索结果会变化。

建议：

```text
开发阶段：Frozen Eval 为主
发布前：Frozen + Live
```

---

# 27. Judge 稳定性控制

LLM Judge 自身会波动。

建议：

1. Judge 使用固定 model；
2. temperature 尽量低；
3. Judge Prompt version 化；
4. 所有 Judge 输出结构化 JSON；
5. 关键 Judge Case 重复运行 2-3 次；
6. 记录 Judge disagreement。

对于高风险 Case：

```text
2 个 Judge 独立评分
```

若差异过大：

```text
manual_review = true
```

---

# 28. Judge Prompt 原则

Judge Prompt 必须：

- 明确 rubric；
- 不要求“总体感觉”；
- 每个维度单独评分；
- 必须引用具体输出位置；
- 必须说明 fail reason；
- 不允许因为文章写得长而加分；
- 不允许因为语气专业而加分。

Judge 输出示例：

```json
{
  "dimension": "counter_evidence_quality",
  "score": 3,
  "max_score": 5,
  "reason": "...",
  "evidence": [
    "..."
  ]
}
```

---

# 29. MVP 实施顺序

## Phase 1：Infrastructure

实现：

```text
eval runner
trace recorder
result schema
report writer
```

验收：

```text
可以对 1 个 case 完整跑通
```

---

## Phase 2：Deterministic Graders

实现：

```text
trigger
filename
line_count
sections
frontmatter
score_math
rating_mapping
red_flag
backlink
```

验收：

```text
所有 deterministic test 可 pytest 自动运行
```

---

## Phase 3：Golden Facts

选择 5 家公司。

每家公司维护：

```text
10-30 个 high-value facts
```

实现：

```text
fact extractor
fact matcher
critical fact gate
```

---

## Phase 4：Trace / Workflow

实现：

```text
tool call logging
required action checking
argument checking
duplicate detection
```

---

## Phase 5：Grounding Judge

实现：

```text
claim extraction
evidence binding
claim-evidence judge
grounded claim rate
```

---

## Phase 6：Analytical Judge

实现：

```text
counter-evidence
action-vs-outcome
capital allocation
uncertainty
strategic consistency
```

---

## Phase 7：Regression

将：

```text
M1-M8
```

全部转为测试。

---

## Phase 8：A/B Runner

实现：

```text
baseline
candidate
comparison report
```

---

# 30. MVP 验收标准

第一阶段完成定义：

```text
[ ] 5 个 company cases
[ ] >= 20 个 trigger cases
[ ] M1-M8 regression cases
[ ] 所有 deterministic graders
[ ] Golden Fact grader
[ ] Workflow grader
[ ] Grounding judge
[ ] 至少 3 个 analytical judges
[ ] Hard Gate 系统
[ ] JSON report
[ ] Markdown summary
[ ] baseline vs candidate compare
[ ] pytest 一键执行
```

期望命令：

```bash
pytest evals/tests
```

完整 Eval：

```bash
python -m evals.runners.run_eval \
  --suite management_archive \
  --skill skills/management-archive/SKILL.md
```

A/B：

```bash
python -m evals.runners.compare_runs \
  reports/baseline \
  reports/candidate
```

---

# 31. 完整版验收标准

MVP 稳定后扩展到：

```text
20-30 家公司
50+ Trigger Cases
20+ Regression Cases
300+ Golden Facts
```

目标：

```text
Trigger Accuracy >= 95%
Required Tool Recall >= 95%
Critical Fact Accuracy >= 98%
Grounded Claim Rate >= 90%
P0 = 0
Structure Pass Rate = 100%
Regression Pass Rate = 100%
```

---

# 32. 不建议做的事情

## 不要 1：只做一个 LLM Judge

错误：

```text
请给这篇管理层档案打 0-100 分
```

这无法诊断 Skill。

---

## 不要 2：把生产 Agent A / Agent B 当 Eval

它们属于 workflow 内部质量控制。

必须建立独立 External Eval。

---

## 不要 3：给每家公司写一整篇 Golden Answer

维护成本极高。

Golden Set 应以：

```text
关键事实
+
关键红旗
+
关键反例
+
禁止错误判断
```

为主。

---

## 不要 4：只看综合分

必须同时看：

```text
Hard Gates
P0
P1
Fact Accuracy
Grounding
Regression
```

---

## 不要 5：修改 Skill 后不增加 Regression

任何已确认的 Skill Bug 都应转为永久 Test。

---

# 33. 推荐优先级

如果本地 Agent 一次只能先实现一部分，按以下顺序：

```text
P0
1. Deterministic Validators
2. Golden Fact Accuracy
3. Workflow / Tool Trace
4. Regression M1-M8

P1
5. Evidence Grounding
6. Score Calibration

P2
7. Analytical Quality Judge
8. Cost / Latency Optimization
```

原因：

```text
事实正确
>
证据充分
>
分析漂亮
```

---

# 34. 最终目标

完成后，Skill 开发流程应从：

```text
修改 SKILL.md
↓
跑几个公司
↓
感觉不错
↓
提交
```

升级为：

```text
修改 SKILL.md
↓
运行固定 Eval Suite
↓
生成结构化指标
↓
查看 Failure Clusters
↓
与 Baseline 对比
↓
确认无 Regression
↓
决定是否 Merge
```

最终要求：

> `management-archive` 的每一次修改，都可以被可重复的 Eval 证明是提升，而不是依赖主观感觉判断。
