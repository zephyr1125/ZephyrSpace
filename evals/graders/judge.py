
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
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .common import CONFIG

JUDGE_PROMPT_VERSION = "judge-v2"

# ---------------------------------------------------------------- judge-v1（历史保留，仅供追溯）

JUDGE_RUBRICS_V1: Dict[str, Dict[str, Any]] = {
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


# ---------------------------------------------------------------- judge-v2（当前生效）

def _v2_dim(name: str, anchors: Dict[int, str], ceilings: List[str]) -> Dict[str, Any]:
    """构造 v2 维度：五档锚点 + ceiling rules + 渲染后的 rubric 文本（兼容旧引用）。"""
    anchors_text = "\n".join(f"{k} 分：{v}" for k, v in sorted(anchors.items()))
    ceilings_text = "\n".join(f"- {c}" for c in ceilings)
    rubric = (
        f"[{name}] 五档锚点：\n{anchors_text}\n"
        f"Ceiling rules（触发即封顶）：\n{ceilings_text}"
    )
    return {
        "max_score": 5,
        "anchors": anchors,
        "ceiling_rules": ceilings,
        "rubric": rubric,
    }


def _v2_anchors(a5, a4, a3, a2, a1):
    return {5: a5, 4: a4, 3: a3, 2: a2, 1: a1}


JUDGE_RUBRICS: Dict[str, Dict[str, Any]] = {
    "counter_evidence": _v2_dim(
        "counter_evidence",
        _v2_anchors(
            a5="主动寻找多个反例，反证实质影响最终结论（结论强度/限定词随反证调整），反例与证据链完整",
            a4="有明确、有效的反证讨论，反证进入最终判断，但反例数量或深度略有不足",
            a3="有负面材料/反例，但未充分进入最终判断（列出了，但结论未被其影响）",
            a2="主要是确认偏误；有反证迹象但被忽略或弱化，未主动寻找与主结论相反的证据",
            a1="基本没有寻找反证，全部为顺向证据",
        ),
        ["仅列负面材料但未影响最终结论 -> 最高 3",
         "未主动寻找与主结论相反证据 -> 最高 2"],
    ),
    "action_vs_outcome": _v2_dim(
        "action_vs_outcome",
        _v2_anchors(
            a5="系统区分'执行了承诺动作'与'承诺结果真正兑现'，每条言行有来源与时间线，兑现判断有结果指标支撑",
            a4="整体区分清晰，个别案例的依据略薄但不影响判断",
            a3="大部分区分正确，但存在部分'执行=兑现'的模糊，或缺少后续时间验证",
            a2="多个重要案例把执行动作直接当结果兑现（或方向反了）",
            a1="普遍混淆动作与结果，兑现判断无依据",
        ),
        ["任一重要案例把执行动作直接当结果兑现 -> 最高 2",
         "缺乏结果指标/后续时间验证 -> 最高 3"],
    ),
    "capital_allocation": _v2_dim(
        "capital_allocation",
        _v2_anchors(
            a5="覆盖全部重大资本动作（融资/并购/回购/分红/扩产），逐笔给出用途、选择理由、机会成本、执行结果（ROIC/ROI）、周期位置，评价与证据一致",
            a4="覆盖基本完整，个别动作的回报分析略简",
            a3="覆盖主要动作，但存在明显遗漏，或对某笔重大动作只记录不分析",
            a2="遗漏重大融资/并购/回购动作，或混淆公告金额与实际执行金额，或仅以分红高/融资多做表面判断",
            a1="资本配置记录严重缺失，或主要判断明显错误",
        ),
        ["遗漏重大融资/并购/回购动作 -> 最高 3",
         "混淆公告金额与实际执行金额 -> 最高 2",
         "仅以分红高/融资多做表面判断 -> 最高 2"],
    ),
    "strategic_consistency": _v2_dim(
        "strategic_consistency",
        _v2_anchors(
            a5="建立跨年（>=3 个时间点）战略时间线，明确区分'合理调整 vs 频繁摇摆'并给出判断依据",
            a4="有跨年时间线，区分基本成立，个别年份依据不足",
            a3="有跨年对照但未充分判断'合理调整 vs 摇摆'，或时间点不足 3 个",
            a2="只统计关键词/年份堆砌，无'合理调整 vs 摇摆'判断",
            a1="无战略时间线，无稳定性判断",
        ),
        ["没有跨年至少 3 个时间点的战略对照 -> 最高 3",
         "只统计关键词，无合理调整 vs 摇摆判断 -> 最高 2"],
    ),
    "crisis_handling": _v2_dim(
        "crisis_handling",
        _v2_anchors(
            a5="识别全部重大危机，逐一分析响应及时性/担责/行动/后续机制，评价有证据支撑",
            a4="主要危机识别并分析完整，次要危机略简",
            a3="有危机分析但只描述事件，未系统分析响应/责任/行动/机制",
            a2="有重大危机但报告未识别，或主要危机处理判断明显错误",
            a1="危机处理记录缺失，或判断严重错误",
        ),
        ["有重大危机但报告未识别 -> 最高 2",
         "只描述事件，不分析响应/责任/行动/后续机制 -> 最高 3"],
    ),
    "uncertainty": _v2_dim(
        "uncertainty",
        _v2_anchors(
            a5="对资料不足/待核实事项诚实标注，且不因信息不足强推结论，不确定处明确",
            a4="整体谨慎，个别不确定处未标注但未影响结论",
            a3="有'待核实/信息不足'标记但覆盖不充分，或个别地方推断略强",
            a2="对资料不足事项做确定性结论（多处强推）",
            a1="普遍以有限信息强推确定结论",
        ),
        ["对资料不足事项做确定性结论 -> 最高 2",
         "'待核实/信息不足'标记不充分但整体谨慎 -> 最高 3"],
    ),
}


@dataclass
class JudgeResult:
    dimension: str
    score: Optional[int] = None   # 1..max_score；status=error 时为 None
    max_score: int = 5
    reason: str = ""
    strengths: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    retries: int = 0              # 本次 judge 调用实际发生的重试次数
    status: str = "success"       # success | error
    error: Optional[str] = None   # status=error 时的失败原因
    backend_name: str = "null"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "max_score": self.max_score,
            "reason": self.reason,
            "strengths": self.strengths,
            "issues": self.issues,
            "evidence": self.evidence,
            "retries": self.retries,
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
    """OpenAI 兼容 chat completions 后端（judge-v2 prompt）。

    失败处理（不伪造分数）：
    - 网络异常 / 超时 / HTTP 429 / 5xx：按 max_retries 指数退避重试
    - JSON 解析失败 / schema 不满足：最多额外重试 1 次（格式类错误）
    - 4xx 参数错误（400/401/403/404/422）：不重试
    - 重试耗尽或不可重试错误 => status="error"、score=None；不降级为其它模型。
    每次重试写入 retry log（EVAL_JUDGE_LOG 或 evals/reports/judge_retries.log）。
    """
    name = "llm"

    TRANSIENT_HTTP = (429, 500, 502, 503, 504)
    NON_RETRY_4XX = (400, 401, 403, 404, 405, 422)
    MAX_FORMAT_RETRIES = 1

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout_seconds: Optional[int] = None, max_retries: Optional[int] = None,
                 profile_name: Optional[str] = None, backoff_base: float = 1.0):
        import requests  # 延迟导入
        self._requests = requests
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.profile_name = profile_name
        llm_cfg = CONFIG["judge"].get("llm", {})
        self.temperature = float(llm_cfg.get("temperature", 0.0))
        self.timeout = int(timeout_seconds if timeout_seconds is not None else llm_cfg.get("timeout_seconds", 120))
        self.max_retries = int(max_retries if max_retries is not None else llm_cfg.get("max_retries", 0))
        self._backoff_base = float(backoff_base)
        self._retry_log_path = os.environ.get("EVAL_JUDGE_LOG") or str(
            Path(__file__).resolve().parents[2] / "evals" / "reports" / "judge_retries.log")

    # ------------------------------------------------------------ judge

    def judge(self, dimension: str, document_text: str, max_score: Optional[int] = None) -> JudgeResult:
        mx = max_score or JUDGE_RUBRICS.get(dimension, {}).get("max_score", 5)
        meta = JUDGE_RUBRICS.get(dimension, {})
        anchors_text = "\n".join(f"{k} 分：{v}" for k, v in sorted(meta.get("anchors", {}).items()))
        ceilings_text = "\n".join(f"- {c}" for c in meta.get("ceiling_rules", []))
        prompt = (
            f"你是管理层档案评估的外部 Judge（prompt 版本 {JUDGE_PROMPT_VERSION}）。\n"
            f"维度：{dimension}\n"
            f"满分 {mx} 分。\n"
            f"\n"
            f"评分前必须（先找问题，再评分）：\n"
            f"1. 找出该维度的缺陷、遗漏、反例或限制条件；\n"
            f"2. 如果未发现实质问题，明确说明为什么；\n"
            f"3. 判断这些问题是否影响核心结论；\n"
            f"4. 再根据 rubric 打分。\n"
            f"\n"
            f"禁止仅因为报告提到了 rubric 中的关键词、章节或分析要素就给予高分。\n"
            f"\n"
            f"5 分（卓越）必须同时满足：关键分析正确、关键证据充分、无明显重要遗漏、"
            f"无明显因果跳跃、无与报告其他部分冲突、几乎没有实质改进空间。"
            f"只要存在重要问题，就不得给 5。\n"
            f"\n"
            f"Rubric（五档锚点）：\n{anchors_text}\n"
            f"\n"
            f"Ceiling rules（触发即封顶）：\n{ceilings_text}\n"
            f"\n"
            f"禁止因为文章长或语气专业而加分。\n"
            f"请输出严格 JSON：{{\"score\": 1-5, \"reason\": \"...\", \"strengths\": [\"...\"], "
            f"\"issues\": [\"...\"], \"evidence\": [\"...\"]}}\n"
            f"reason 必须引用报告中的具体位置或原文片段。\n\n--- 报告 ---\n{document_text[:30000]}"
        )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        retries = 0
        transient_used = 0
        format_used = 0
        while True:
            try:
                resp = self._requests.post(
                    self.base_url + "/chat/completions",
                    json=payload,
                    headers={"Authorization": "Bearer " + self.api_key},
                    timeout=self.timeout,
                )
                status = resp.status_code
                if status < 200 or status >= 300:
                    err = f"http_error {status}: {resp.text[:200]}"
                    if status in self.TRANSIENT_HTTP and transient_used < self.max_retries:
                        transient_used += 1
                        retries = transient_used + format_used
                        self._log_retry(dimension, err, delay=self._backoff(dimension, transient_used + format_used))
                        time.sleep(self._backoff(dimension, transient_used + format_used))
                        continue
                    return self._error(dimension, mx, err, retries=retries)  # 4xx/其它不重试
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                res = self._validate(dimension, mx, parsed)
                if res.status == "error" and format_used < self.MAX_FORMAT_RETRIES:
                    # 格式类错误：最多额外重试 1 次
                    format_used += 1
                    retries = transient_used + format_used
                    self._log_retry(dimension, res.error or "format_error", delay=self._backoff(dimension, transient_used + format_used))
                    time.sleep(self._backoff(dimension, transient_used + format_used))
                    continue
                res.retries = retries
                return res
            except json.JSONDecodeError as e:
                err = f"json_parse_error: {e}"
                if format_used < self.MAX_FORMAT_RETRIES:
                    format_used += 1
                    retries = transient_used + format_used
                    self._log_retry(dimension, err, delay=self._backoff(dimension, transient_used + format_used))
                    time.sleep(self._backoff(dimension, transient_used + format_used))
                    continue
                return self._error(dimension, mx, err, retries=retries)
            except (KeyError, IndexError, TypeError) as e:
                err = f"response_schema_error: {e}"
                if format_used < self.MAX_FORMAT_RETRIES:
                    format_used += 1
                    retries = transient_used + format_used
                    self._log_retry(dimension, err, delay=self._backoff(dimension, transient_used + format_used))
                    time.sleep(self._backoff(dimension, transient_used + format_used))
                    continue
                return self._error(dimension, mx, err, retries=retries)
            except Exception as e:  # noqa: BLE001 网络异常/超时等
                err = f"request_failed: {e}"
                if transient_used < self.max_retries:
                    transient_used += 1
                    retries = transient_used + format_used
                    self._log_retry(dimension, err, delay=self._backoff(dimension, transient_used + format_used))
                    time.sleep(self._backoff(dimension, transient_used + format_used))
                    continue
                return self._error(dimension, mx, err, retries=retries)

    # ------------------------------------------------------------ helpers

    def _backoff(self, dimension: str, attempt: int) -> float:
        """指数退避：base * 2^(attempt-1)，封顶 30s。"""
        return min(self._backoff_base * (2 ** max(0, attempt - 1)), 30.0)

    def _log_retry(self, dimension: str, error: str, delay: float) -> None:
        """每次失败重试写入 JSONL log（EVAL_JUDGE_LOG 或默认 reports/judge_retries.log）。"""
        import time as _t
        from datetime import datetime as _dt
        record = {
            "timestamp": _dt.now().isoformat(timespec="seconds"),
            "model": self.model,
            "profile": self.profile_name,
            "dimension": dimension,
            "error": error[:300],
            "delay_s": round(delay, 2),
        }
        try:
            with open(self._retry_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # log 失败不阻塞

    def _error(self, dimension: str, mx: int, msg: str, retries: int = 0) -> JudgeResult:
        return JudgeResult(dimension=dimension, score=None, max_score=mx,
                           reason="", evidence=[], retries=retries,
                           status="error", error=msg, backend_name=self.name)

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
        strengths = parsed.get("strengths") or []
        issues = parsed.get("issues") or []
        if not isinstance(strengths, list) or not all(isinstance(x, str) for x in strengths):
            return self._error(dimension, mx, "schema_error: strengths 必须为字符串数组")
        if not isinstance(issues, list) or not all(isinstance(x, str) for x in issues):
            return self._error(dimension, mx, "schema_error: issues 必须为字符串数组")
        return JudgeResult(dimension=dimension, score=score_raw, max_score=mx,
                           reason=reason, strengths=strengths, issues=issues,
                           evidence=evidence, status="success", backend_name=self.name)


def _resolve_judge_profile(profile: Optional[str]) -> Dict[str, Any]:
    """解析 judge profile。未指定或不存在则抛 ValueError（避免静默用错档位）。"""
    if not profile:
        return {}
    cfg = CONFIG["judge"]
    profiles = cfg.get("judge_profiles") or {}
    if profile not in profiles:
        raise ValueError(f"未知 judge profile: {profile!r}（可选：{sorted(profiles.keys())}）")
    return profiles[profile]


def get_backend(profile: Optional[str] = None) -> JudgeBackend:
    """返回 judge backend。

    - backend=llm 时：base_url / api_key 来自 .env（EVAL_LLM_BASE_URL / EVAL_LLM_API_KEY）；
      model / timeout / max_retries 优先来自 profile（judge_profiles），其次 EVAL_LLM_MODEL，
      最后 default_model。
    - profile 参数 > CONFIG["judge"]["profile"]（--judge-profile 设置）。
    - backend=null 或 key/base 缺失 => NullJudgeBackend（release profile 下调用方应视为配置错误，
      不会静默降级为其它模型）。
    """
    cfg = CONFIG["judge"]
    if cfg.get("backend") != "llm":
        return NullJudgeBackend()
    env = cfg.get("llm", {})
    base = os.environ.get(env.get("base_url_env", "EVAL_LLM_BASE_URL"))
    key = os.environ.get(env.get("api_key_env", "EVAL_LLM_API_KEY"))
    if not (base and key):
        return NullJudgeBackend()

    prof_name = profile or cfg.get("profile")
    prof = _resolve_judge_profile(prof_name) if prof_name else {}
    model = (prof.get("model")
             or os.environ.get(env.get("model_env", "EVAL_LLM_MODEL"))
             or env.get("default_model", "gpt-4o-mini"))
    return LLMJudgeBackend(
        base, key, model,
        timeout_seconds=prof.get("timeout_seconds"),
        max_retries=prof.get("max_retries"),
        profile_name=prof_name,
    )

