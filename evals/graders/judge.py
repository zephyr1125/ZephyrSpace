
"""可插拔 LLM-as-a-Judge 后端（plan §12 / §27 / §28）。

- NullJudgeBackend: 确定性启发式回退（离线可用，pytest 稳定）
- LLMJudgeBackend: OpenAI 兼容 chat completions（需设置 EVAL_LLM_BASE_URL / EVAL_LLM_API_KEY / EVAL_LLM_MODEL）
- Judge 输出统一结构化 JSON；temperature 固定 0；prompt 版本化

用法：
    from evals.graders.judge import get_backend
    backend = get_backend()
    result = backend.judge("counter_evidence", rubric, document_text)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .common import CONFIG

JUDGE_PROMPT_VERSION = "judge-v1"

JUDGE_RUBRICS: Dict[str, Dict[str, Any]] = {
    "counter_evidence": {
        "max_score": 5,
        "rubric": (
            "评估反证质量：5=主动寻找多个反例且反证实质影响结论；4=有明确、有效的反证讨论；"
            "3=有负面材料但未充分进入最终判断；2=主要是确认偏误；1=基本没有寻找反证。"
        ),
    },
    "action_vs_outcome": {
        "max_score": 5,
        "rubric": (
            "评估言行一致性分析是否正确区分'执行了承诺动作'与'承诺结果真正兑现'："
            "5=明确区分执行与兑现并给出来源与时间线；3=部分区分但存在混淆；1=把动作当兑现。"
        ),
    },
    "capital_allocation": {
        "max_score": 5,
        "rubric": (
            "评估资本配置分析质量：不能只判断分红高=好/融资多=差；应判断当时资本用途、选择理由、"
            "机会成本、执行结果、ROIC/ROI、周期位置。5=全面覆盖；3=部分覆盖；1=仅看表面。"
        ),
    },
    "strategic_consistency": {
        "max_score": 5,
        "rubric": (
            "评估战略稳定性分析：是否建立跨年战略时间线，识别战略变化是合理调整还是频繁摇摆；"
            "5=有跨年时间线且区分合理调整与摇摆；3=仅统计关键词；1=无战略分析。"
        ),
    },
    "crisis_handling": {
        "max_score": 5,
        "rubric": (
            "评估危机处理分析：是否识别危机、及时响应、承担责任、采取行动、建立后续机制；"
            "5=完整五要素；3=部分；1=未识别危机。"
        ),
    },
    "uncertainty": {
        "max_score": 5,
        "rubric": (
            "评估不确定性处理：资料不足时正确标注'信息不足/待核实'而非强推确定结论；"
            "5=诚实标注且不强行下结论；3=部分；1=根据有限信息强推确定结论。"
        ),
    },
}


@dataclass
class JudgeResult:
    dimension: str
    score: Optional[int] = None   # 1..max_score；status=error 时为 None
    max_score: int = 5
    reason: str = ""
    evidence: List[str] = field(default_factory=list)
    status: str = "success"       # success | error
    error: Optional[str] = None   # status=error 时的失败原因
    backend_name: str = "null"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "max_score": self.max_score,
            "reason": self.reason,
            "evidence": self.evidence,
            "status": self.status,
            "error": self.error,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "backend": self.backend_name,
        }


class JudgeBackend:
    name = "base"

    def judge(self, dimension: str, document_text: str, max_score: Optional[int] = None) -> JudgeResult:
        raise NotImplementedError


class NullJudgeBackend(JudgeBackend):
    """确定性启发式回退。"""
    name = "null"

    def judge(self, dimension: str, document_text: str, max_score: Optional[int] = None) -> JudgeResult:
        text = document_text or ""
        mx = max_score or JUDGE_RUBRICS.get(dimension, {}).get("max_score", 5)
        score, reason = self._heuristic(dimension, text)
        return JudgeResult(dimension=dimension, score=score, max_score=mx,
                           reason=reason, backend_name=self.name)

    def _heuristic(self, dimension: str, text: str) -> tuple:
        if dimension == "counter_evidence":
            has_negative_section = bool(("失信" in text) or ("夸大" in text) or ("反面" in text))
            placeholder = "暂未发现明显言行不一致" in text
            has_watch = bool(("警惕" in text) or ("红旗" in text))
            if has_negative_section and has_watch:
                return 4, "存在失信/夸大案例且提出警惕问题，反证进入判断"
            if has_negative_section:
                return 3, "有负面材料但未充分进入最终判断"
            if placeholder and has_watch:
                return 3, "明确说明无失信案例且提出警惕问题"
            if has_watch:
                return 3, "有警惕问题但缺少负面案例讨论"
            return 2, "主要是正面材料，缺少反证"
        if dimension == "action_vs_outcome":
            ongoing = text.count("⏳")
            partial = text.count("⚠️部分") + text.count("部分")
            failed = text.count("❌")
            if ongoing + partial + failed >= 3:
                return 4, "区分了执行中/已兑现/未兑现三态"
            if ongoing >= 1:
                return 3, "存在'执行中'标注但区分不充分"
            return 2, "多为已兑现标注，未区分动作与结果"
        if dimension == "capital_allocation":
            depth = 0
            for k in ("ROIC", "回报", "机会成本", "周期", "用途", "理由"):
                if k in text:
                    depth += 1
            if depth >= 4:
                return 4, "覆盖 ROIC/机会成本/周期等维度"
            if depth >= 2:
                return 3, "部分覆盖资本配置维度"
            return 2, "资本配置分析流于表面"
        if dimension == "strategic_consistency":
            for k in ("战略方向是否连贯", "业绩指引达成率", "归因"):
                if k in text:
                    return 4, "建立跨年战略时间线并评估连贯性/指引达成/归因诚实"
            if "战略" in text and "连贯" in text:
                return 3, "有战略连贯性讨论但未量化"
            return 2, "缺少跨年战略时间线分析"
        if dimension == "crisis_handling":
            rows = text.count("|")  # 粗指标
            elements = sum(1 for k in ("及时", "承担责任", "行动", "机制", "透明") if k in text)
            if elements >= 4:
                return 4, "覆盖响应/担责/行动/机制四要素"
            if elements >= 2:
                return 3, "部分覆盖危机处理要素"
            return 2, "危机处理分析不足"
        if dimension == "uncertainty":
            honest = text.count("待核实") + text.count("信息不足") + text.count("无法核实")
            if honest >= 2:
                return 4, "多处诚实标注信息不足/待核实"
            if honest >= 1:
                return 3, "有标注但覆盖不足"
            return 2, "未见信息不足标注，存在强推结论风险"
        return 3, "无匹配启发式"


class LLMJudgeBackend(JudgeBackend):
    """OpenAI 兼容 chat completions 后端。

    失败处理（不伪造分数）：
    - 请求异常 / 超时 / HTTP 非 2xx / JSON 解析失败 / 结构不满足 schema
      => 返回 status="error"、score=None、error=<原因>；调用方不得把该结果计入评分。
    - 瞬时错误（5xx / 429 / 连接 / 超时）按 config 的 max_retries 重试。
    """
    name = "llm"

    TRANSIENT_HTTP = (429, 500, 502, 503, 504)

    def __init__(self, base_url: str, api_key: str, model: str):
        import requests  # 延迟导入
        self._requests = requests
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = float(CONFIG["judge"]["llm"].get("temperature", 0.0))
        self.timeout = int(CONFIG["judge"]["llm"].get("timeout_seconds", 120))
        self.max_retries = int(CONFIG["judge"]["llm"].get("max_retries", 0))

    # ------------------------------------------------------------ judge

    def judge(self, dimension: str, document_text: str, max_score: Optional[int] = None) -> JudgeResult:
        mx = max_score or JUDGE_RUBRICS.get(dimension, {}).get("max_score", 5)
        meta = JUDGE_RUBRICS.get(dimension, {})
        prompt = (
            f"你是管理层档案评估的外部 Judge（prompt 版本 {JUDGE_PROMPT_VERSION}）。\n"
            f"维度：{dimension}\nRubric：{meta.get('rubric', '')}\n"
            f"满分 {mx} 分。禁止因为文章长或语气专业而加分。\n"
            f"请输出严格 JSON：{{\"score\": 1-{mx}, \"reason\": \"...\", \"evidence\": [\"...\"]}}\n"
            f"reason 必须引用报告中的具体位置或原文片段。\n\n--- 报告 ---\n{document_text[:30000]}"
        )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        last_error: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._requests.post(
                    self.base_url + "/chat/completions",
                    json=payload,
                    headers={"Authorization": "Bearer " + self.api_key},
                    timeout=self.timeout,
                )
                if resp.status_code < 200 or resp.status_code >= 300:
                    last_error = f"http_error {resp.status_code}: {resp.text[:200]}"
                    if resp.status_code in self.TRANSIENT_HTTP and attempt < self.max_retries:
                        continue
                    return self._error(dimension, mx, last_error)
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return self._validate(dimension, mx, parsed)
            except json.JSONDecodeError as e:
                return self._error(dimension, mx, f"json_parse_error: {e}")
            except (KeyError, IndexError, TypeError) as e:
                return self._error(dimension, mx, f"response_schema_error: {e}")
            except Exception as e:  # noqa: BLE001 请求异常/超时等
                last_error = f"request_failed: {e}"
                if attempt < self.max_retries:
                    continue
                return self._error(dimension, mx, last_error)
        return self._error(dimension, mx, last_error or "unknown_error")

    # ------------------------------------------------------------ helpers

    def _error(self, dimension: str, mx: int, msg: str) -> JudgeResult:
        return JudgeResult(dimension=dimension, score=None, max_score=mx,
                           reason="", evidence=[], status="error", error=msg,
                           backend_name=self.name)

    def _validate(self, dimension: str, mx: int, parsed: Any) -> JudgeResult:
        if not isinstance(parsed, dict):
            return self._error(dimension, mx, f"schema_error: 返回非 JSON 对象: {type(parsed).__name__}")
        score_raw = parsed.get("score")
        if isinstance(score_raw, bool) or not isinstance(score_raw, int):
            return self._error(dimension, mx, f"schema_error: score 非整数: {score_raw!r}")
        if not (1 <= score_raw <= mx):
            return self._error(dimension, mx, f"schema_error: score {score_raw} 超出 1..{mx}")
        reason = parsed.get("reason")
        if not isinstance(reason, str):
            return self._error(dimension, mx, f"schema_error: reason 非字符串: {reason!r}")
        evidence = parsed.get("evidence") or []
        if not isinstance(evidence, list) or not all(isinstance(x, str) for x in evidence):
            return self._error(dimension, mx, "schema_error: evidence 必须为字符串数组")
        return JudgeResult(dimension=dimension, score=score_raw, max_score=mx,
                           reason=reason, evidence=evidence, status="success",
                           backend_name=self.name)


def get_backend() -> JudgeBackend:
    cfg = CONFIG["judge"]
    if cfg.get("backend") == "llm":
        env = cfg["llm"]
        base = os.environ.get(env["base_url_env"])
        key = os.environ.get(env["api_key_env"])
        if base and key:
            model = os.environ.get(env["model_env"], env["default_model"])
            return LLMJudgeBackend(base, key, model)
    return NullJudgeBackend()