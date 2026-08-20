# Eval Harness — management-archive Skill

> 依据 `plan/management_archive_eval_PLAN.md` 实现的 Skill 评估系统。
> 目标：让 `management-archive` 的每一次修改都可以被**可重复、可量化、可回归**的 Eval 证明是提升，而不是依赖主观感觉。

---

## 1. 架构总览

```text
SKILL.md candidate
        ↓
  Run Eval Dataset（5 家公司 + 26 触发用例 + M1-M8 回归）
        ↓
  ┌──────────── Eval Pipeline ────────────┐
  │ 1. Trigger Eval（触发准确率）          │
  │ 2. Workflow / Tool Eval（工具追溯）    │
  │ 3. Deterministic Structure Eval（结构）│
  │ 4. Fact Accuracy Eval（事实准确率）    │
  │ 5. Evidence Grounding Eval（证据绑定） │
  │ 6. Analytical Quality Judge（分析质量）│
  │ 7. Score Calibration（评分校准）       │
  │ 8. Regression M1-M8（历史错误回归）    │
  └──────────────────┬───────────────────┘
                     ↓
            Generate Eval Report（JSON + Markdown）
                     ↓
          compare_runs 对比 baseline / candidate
                     ↓
                Keep / Reject 修改
`

**核心设计原则**（plan §32）：

- 能确定性判断的，不用 LLM Judge（文件名/行数/章节/评分算术/反链…）
- Golden Set 只维护「关键事实 + 关键红旗 + 禁止错误判断」，不写整篇标准答案
- 生产 Agent A/B 审核 ≠ Eval；外部 Judge 用独立 prompt、不读取生产评分
- 每修复一种历史错误 = Skill 修改 + 至少一个永久 Regression Test

---

## 2. 目录结构

```text
evals/
├── README.md
├── config.yaml                  # 权重 / Hard Gates / 阈值 / judge 配置
├── cases/management_archive/
│   ├── trigger/positive.yaml    # 14 条正向触发用例
│   ├── trigger/negative.yaml    # 12 条负向触发用例
│   ├── companies/case_001~005.yaml
│   └── regression/M1~M8.yaml    # 高频坑 → 永久回归规格
├── fixtures/golden_facts/       # 5 家公司高价值可核验事实
├── graders/
│   ├── common.py                # 加载/解析/评分/评级/错误分级
│   ├── trigger.py               # Layer 1
│   ├── workflow.py              # Layer 2（需 trace）
│   ├── structure.py             # Layer 3
│   ├── facts.py                 # Layer 4
│   ├── grounding.py             # Layer 5
│   ├── analytical_quality.py    # Layer 6
│   ├── score_consistency.py     # Layer 7
│   ├── regression.py            # M1-M8
│   └── judge.py                 # 可插拔 LLM Judge 后端
├── runners/
│   ├── run_skill.py             # 执行层（Replay / Agent 扩展点）
│   ├── trace_recorder.py        # 工具调用记录 + schema 校验
│   ├── run_eval.py              # 完整 Eval 管线 CLI
│   └── compare_runs.py          # A/B 对比 CLI
├── schemas/                     # case / golden_facts / trace / result JSON Schema
├── reports/                     # 每次运行的输出
└── tests/                       # pytest 一键执行（52 个测试）
`

---

## 3. 快速开始

```powershell
# 1. 一键运行全部测试（MVP 验收）
python -m pytest evals/tests -q

# 2. 跑一次完整 Eval（默认对 vault 内 5 家公司的档案做 Frozen Eval）
python -m evals.runners.run_eval --suite management_archive --run-name v18

# 3. 指定 SKILL 版本 / 输出目录 / baseline
python -m evals.runners.run_eval `
    --suite management_archive --run-name v19 `
    --skill management-archive/SKILL.md `
    --output-dir 管理层档案 `
    --baseline evals/reports/<run>/summary.json

# 4. A/B 对比
python -m evals.runners.compare_runs evals/reports/<baseline> evals/reports/<candidate>
`

报告输出到 `evals/reports/<YYYY-MM-DD>_<run-name>/`：

```text
├── summary.json     # 结构化汇总（schema: result.schema.json）
├── summary.md       # 人类可读汇总（含 Top Failure Categories）
├── cases/*.json     # 每个 case 的逐项得分 / gates / errors
├── failures.md      # 全部错误明细
├── regressions.md   # M1-M8 回归状态
└── traces/          # 工具调用 trace（如有）
`

---

## 4. Eval 分层说明

### Layer 1 — Trigger（权重 5）

从 SKILL.md「触发条件」章节提取触发词 + 配置兜底，对 26 条标注用例计算
Accuracy / Precision / Recall / FPR / FNR。**修改 SKILL.md 触发条件会直接改变规则**——
本层衡量修改是否破坏既有标注。

- Hard Gate：`trigger_accuracy >= 0.95`

### Layer 2 — Workflow / Tool（权重 15）

从 Agent trace（工具调用列表）评价：

- **Required Tool Recall**：`required_workflow` 中要求的数据源实际完成比例（gate ≥ 0.95）
- **参数正确性**：港股/美股不得调用 CNINFO；电话会搜索后必须读取 detail；
  公告查询必须有日期范围；股票代码与 case 一致
- **效率指标**：重复调用数 / 平均工具数（仅版本比较，不作 gate）

> 无 trace 时该层返回 N/A，不强制 gate。trace 由 `TraceRecorder` 记录
> （见 `runners/trace_recorder.py`），Live 执行需在 agent 层埋点。

### Layer 3 — Deterministic Structure（权重 10）

文件名正则、行数 ≥150、11 章节完整性、📊 快速参考卡位置、frontmatter、
股票代码格式（SH/SZ/HK/US）、评分算术（Σ维度 == 总分）、红旗规则
（诚信 ≤8 或 资本配置 ≤10 必须出现红旗）、评级映射、公司页/深度分析页反链。

### Layer 4 — Fact Accuracy（权重 25，最高优先）

Markdown 表格确定性抽取（董事长/CEO/实控人/处罚/高管变动/资本动作）→ 与
Golden Facts 匹配 → Fact Precision / Recall / **Critical Fact Accuracy**
（P0 关键事实，gate ≥ 0.98）。金额支持 亿/万 单位换算。

### Layer 5 — Evidence Grounding（权重 20）

提取综合结论/一致性评估中的主要判断，验证每个 claim 是否有证据锚
（年份/数字/来源词）。Grounded Claim Rate gate ≥ 0.90。
LLM 模式下由外部 Judge 逐 claim 打分（0-3），null 模式用确定性锚点匹配。

### Layer 6 — Analytical Quality（权重 15）

6 个维度（1-5 分）：反证质量 / 言行一致性(动作≠兑现) / 资本配置 / 战略稳定性 /
危机处理 / 不确定性处理。LLM 模式下独立 Judge 逐维打分（固定 model、temperature 0、
prompt 版本化、结构化 JSON 输出）；null 模式用确定性启发式。

### Layer 7 — Score Calibration（权重 5）

速览卡分 == 明细总分 == 文件名分；评级与总分匹配；结论类型定位与分数一致；
与 baseline 的 Score Drift 超阈值（默认 8 分）要求解释；
Pairwise 相对排序（A 明显优于 B ⇒ score(A) > score(B)）。

### Regression M1-M8（权重 5）

| 编号 | 高频坑 | 检查 |
|---|---|---|
| M1 | 管理层身份依赖陈旧记忆 | 现任董事长/CEO 与 golden 一致 |
| M2 | 处罚事件合并 | 独立处罚必须分行 |
| M3 | 动作 ≠ 兑现 | 执行动作（投入/费用）≠ 业务结果 |
| M4 | 融资工具遗漏 | 增发/配股/可转债/H股/优先股/股权激励 |
| M5 | 减持忽略增持 | 有增持记录时禁止写"持续减持" |
| M6 | 公告金额 vs 实际执行 | 回购使用实际执行口径 |
| M7 | 原文断章取义 | 短促摘录缺失限定条件提示复核 |
| M8 | 高管变动无时间线 | 近5年时间线 + 12个月密集离任识别 |

---

## 5. Hard Gates（plan §18）

| Gate | 阈值 |
|---|---|
| p0_errors | 0 |
| critical_fact_accuracy | ≥ 0.98 |
| grounded_claim_rate | ≥ 0.90 |
| required_tool_recall | ≥ 0.95 |
| trigger_accuracy | ≥ 0.95 |
| score_math | required |
| required_sections | required |
| minimum_lines | 150 |

任何 Gate 不通过 ⇒ `Overall Status = FAIL`（即使加权分很高）。

---

## 6. LLM Judge 接入

默认 `judge.backend: null`（确定性启发式，离线可跑、pytest 稳定）。
启用 LLM Judge 需设置环境变量：

```powershell
$env:EVAL_LLM_BASE_URL = "https://api.openai.com/v1"   # 或兼容端点
$env:EVAL_LLM_API_KEY  = "sk-..."
$env:EVAL_LLM_MODEL    = "gpt-4o-mini"
`

然后把 `evals/config.yaml` 中 `judge.backend` 改为 `llm`。

Judge 稳定性控制（plan §27）：固定 model、temperature 0、prompt 版本化
（`JUDGE_PROMPT_VERSION`）、结构化 JSON 输出、关键 case 重复运行、双 judge 分歧检测。

---

## 7. Frozen Eval vs Live Eval（plan §26）

- **Frozen Eval（当前实现）**：`ReplayRunner` 回放 vault 内既有档案，可复现、A/B 公平
- **Live Eval（扩展点）**：`AgentRunner` 接口 + `TraceRecorder` 埋点，由宿主 agent
  执行完整工作流并记录工具调用，即可跑 Live 模式（workflow 层随之启用）

---

## 8. 新增 Eval Case

```yaml
id: management_archive_006
company: { name: 某公司, ticker: 600000.SH, market: A }
prompt: "管理层档案 某公司"
golden_facts_file: fixtures/golden_facts/600000.SH.yaml
required_workflow:
  company_profile: true
  ...
`

1. 在 `evals/cases/management_archive/companies/` 建 case YAML
2. 在 `evals/fixtures/golden_facts/` 建 golden facts（只放高价值可核验事实）
3. 触发用例加进 `trigger/positive.yaml` / `negative.yaml`（多文档用 `---` 分隔）
4. 修复的历史错误 → 在 `evals/tests/test_regressions.py` 加永久回归测试

---

## 9. 失败聚类 → Skill 优化循环（plan §24-25）

每次 Eval 输出 Top Failure Categories（如 `FACT_PENALTY`、`WORKFLOW_MISSING_TIMELINE`），
按「频率 × 严重度」选择最高优先问题 → 修改 SKILL.md → **必须**同时新增 Regression Case
→ 重新 Eval → A/B compare → Keep / Reject。

禁止：只修改 Skill 但不增加 Regression Case。

---

## 10. 当前 MVP 状态（对照 plan §30）

| MVP 验收项 | 状态 |
|---|---|
| 5 个 company cases | ✅ case_001~005（福耀/腾讯/美的/比亚迪/三安） |
| ≥20 个 trigger cases | ✅ 26 条（14 正 + 12 负） |
| M1-M8 regression cases | ✅ 8 个 YAML + 19 个 pytest |
| 所有 deterministic graders | ✅ trigger/structure/facts/regression/score_consistency |
| Golden Fact grader | ✅ 5 家 × 10-30 个事实，Critical Fact Accuracy gate |
| Workflow grader | ✅ required tool recall + 参数检查 + 重复检测 |
| Grounding judge | ✅ 可插拔 LLM + 确定性回退 |
| ≥3 个 analytical judges | ✅ 6 个（counter_evidence / action_vs_outcome / capital_allocation / strategic_consistency / crisis_handling / uncertainty） |
| Hard Gate 系统 | ✅ 8 项 |
| JSON report | ✅ summary.json + cases/*.json |
| Markdown summary | ✅ summary.md + failures.md + regressions.md |
| baseline vs candidate compare | ✅ compare_runs.py |
| pytest 一键执行 | ✅ 52 passed |

完整版扩展目标（plan §31）：20-30 家公司、50+ 触发用例、20+ 回归用例、300+ Golden Facts。
