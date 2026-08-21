"""LLM Judge 失败处理测试。

覆盖：
- NullJudgeBackend 保持 deterministic（status=success，分数不因失败而变）
- LLM 成功路径（mock requests.post 返回合法 JSON）
- HTTP 非 2xx / JSON 解析失败 / schema 不满足 / 请求异常 => status=error、score=None、不伪造 3 分
- 瞬时错误重试（max_retries）
- analytical_quality / grounding 把 error 结果剔除出评分并记录 judge_error_count
- run_eval 聚合：judge 失败时 case 标记 INCOMPLETE，不进平均分
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders import analytical_quality, grounding
from evals.graders.common import CONFIG, case_from_dict
from evals.graders.judge import JUDGE_RUBRICS, LLMJudgeBackend, JudgeResult, NullJudgeBackend, get_backend
from evals.tests.conftest import GOOD_DOC, make_doc


# ---------------------------------------------------------------- 假 HTTP 层

class FakeResponse:
    def __init__(self, status_code=200, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is not None:
            return self._payload
        return {"choices": [{"message": {"content": self.text}}]}


class FakeRequests:
    """可编程 requests 替身：按调用顺序返回预设响应。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        if not self._responses:
            raise RuntimeError("no more responses")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _llm_backend(requests_obj, max_retries=0):
    b = LLMJudgeBackend("https://fake.test/v1", "sk-fake", "test-model")
    b._requests = requests_obj
    b.max_retries = max_retries
    return b


def _ok_json(score=4, reason="证据充分", evidence=None):
    return {"score": score, "reason": reason, "evidence": evidence or ["证据1"]}


# ---------------------------------------------------------------- Null backend 行为不变

def test_null_backend_always_success():
    b = NullJudgeBackend()
    for dim in JUDGE_RUBRICS:
        r = b.judge(dim, "管理层有失信案例但未充分讨论" + " 待核实" * 5)
        assert r.status == "success"
        assert r.error is None
        assert r.score is not None and 1 <= r.score <= JUDGE_RUBRICS[dim]["max_score"]


# ---------------------------------------------------------------- LLM 成功路径

def test_llm_success():
    b = _llm_backend(FakeRequests([FakeResponse(200, text=json.dumps(_ok_json(4)))]))
    r = b.judge("counter_evidence", "some doc", 5)
    assert r.status == "success"
    assert r.score == 4
    assert r.error is None
    assert r.reason == "证据充分"
    assert r.evidence == ["证据1"]


# ---------------------------------------------------------------- 失败 => error，不伪造分数

def test_llm_http_500_is_error():
    b = _llm_backend(FakeRequests([FakeResponse(500, text="server boom")]))
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert r.score is None
    assert "http_error 500" in r.error


def test_llm_http_404_is_error():
    b = _llm_backend(FakeRequests([FakeResponse(404, text="not found")]))
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert "http_error 404" in r.error


def test_llm_json_parse_failure_is_error():
    # 格式类错误最多重试 1 次 -> 提供 2 个响应，两次都非法则 error
    b = _llm_backend(FakeRequests([FakeResponse(200, text="not-json{{{"), FakeResponse(200, text="not-json{{{")]))
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert "json_parse_error" in r.error
    assert r.score is None


def test_llm_request_exception_is_error():
    b = _llm_backend(FakeRequests([ConnectionError("refused")]))
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert "request_failed" in r.error
    assert r.score is None


# ---------------------------------------------------------------- schema 校验

@pytest.mark.parametrize("bad", [
    ("score 缺失", {}),
    ("score 非整数", {"score": "4", "reason": "x"}),
    ("score 越界", {"score": 99, "reason": "x"}),
    ("score 布尔", {"score": True, "reason": "x"}),
    ("reason 非字符串", {"score": 3, "reason": 123}),
    ("evidence 非列表", {"score": 3, "reason": "x", "evidence": "nope"}),
    ("evidence 含非字符串", {"score": 3, "reason": "x", "evidence": [1]}),
    ("返回非对象", [1, 2, 3]),
])
def test_llm_schema_mismatch_is_error(bad):
    label, payload = bad
    text = json.dumps(payload)
    # 格式类错误最多重试 1 次 -> 提供 2 个相同响应，两次都失败则 error
    b = _llm_backend(FakeRequests([FakeResponse(200, text=text), FakeResponse(200, text=text)]))
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error", label
    assert r.score is None, label
    assert "schema_error" in r.error or "response_schema_error" in r.error, label
    assert r.retries == 1, label


# ---------------------------------------------------------------- 重试

def test_llm_transient_retry_then_success():
    reqs = FakeRequests([FakeResponse(500, "boom"), FakeResponse(200, text=json.dumps(_ok_json(3)))])
    b = _llm_backend(reqs, max_retries=2)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "success"
    assert r.score == 3
    assert len(reqs.calls) == 2


def test_llm_persistent_error_no_fabricated_score():
    reqs = FakeRequests([FakeResponse(500, "boom")] * 4)  # 每次都是 500
    b = _llm_backend(reqs, max_retries=3)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert r.score is None
    assert len(reqs.calls) == 4  # 1 + 3 次重试


# ---------------------------------------------------------------- grader 剔除 error 结果

class ErrorBackend:
    name = "llm"

    def judge(self, dim, doc, max_score=None):
        if dim in ("counter_evidence", "capital_allocation"):
            return JudgeResult(dimension=dim, score=None, max_score=5, status="error",
                               error="mock failure", backend_name="llm")
        mx = max_score or JUDGE_RUBRICS[dim]["max_score"]
        return JudgeResult(dimension=dim, score=mx, max_score=mx, status="success",
                           backend_name="llm")


def test_analytical_quality_excludes_error_dims(tmp_path, monkeypatch):
    monkeypatch.setattr(analytical_quality, "get_backend", lambda: ErrorBackend())
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = analytical_quality.grade(d, None)
    # 6 维中 2 维失败 -> 4 维成功，各拿满分
    assert r.metrics["judge_error_count"] == 2
    assert r.metrics["judge_total"] == 6
    assert r.metrics["judge_success_rate"] == pytest.approx(round(4 / 6, 4))
    # 失败维度不计入总分/平均：4 个成功维度都是满分 -> score = 1.0
    assert r.score == 1.0
    assert any(e.category == "JUDGE_ERROR" for e in r.errors)


def test_analytical_quality_all_error_score_none(tmp_path, monkeypatch):
    class AllErrorBackend:
        name = "llm"
        def judge(self, dim, doc, max_score=None):
            return JudgeResult(dimension=dim, score=None, max_score=5, status="error",
                               error="all fail", backend_name="llm")
    monkeypatch.setattr(analytical_quality, "get_backend", lambda: AllErrorBackend())
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = analytical_quality.grade(d, None)
    assert r.score is None
    assert r.metrics["judge_error_count"] == 6


def test_grounding_excludes_error_claims(tmp_path, monkeypatch):
    class HalfErrorBackend:
        name = "llm"
        def __init__(self):
            self._n = 0
        def judge(self, dim, doc, max_score=None):
            self._n += 1
            if self._n % 2 == 1:
                return JudgeResult(dimension=dim, score=None, max_score=3, status="error",
                                   error="mock", backend_name="llm")
            return JudgeResult(dimension=dim, score=3, max_score=3, status="success",
                               backend_name="llm")
    monkeypatch.setattr(grounding, "get_backend", lambda: HalfErrorBackend())
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = grounding.grade(d, None)
    assert r.metrics["judge_error_count"] > 0
    assert r.metrics["judge_total"] == r.metrics["claims_total"]
    # 成功 claim 全部 grounded -> rate 基于「已评估」claim 计算，应为 1.0
    assert r.score == 1.0


def test_grounding_all_error_score_none(tmp_path, monkeypatch):
    class AllErrorBackend:
        name = "llm"
        def judge(self, dim, doc, max_score=None):
            return JudgeResult(dimension=dim, score=None, max_score=3, status="error",
                               error="all fail", backend_name="llm")
    monkeypatch.setattr(grounding, "get_backend", lambda: AllErrorBackend())
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = grounding.grade(d, None)
    assert r.score is None
    assert r.metrics["judge_error_count"] == r.metrics["claims_total"]
    assert r.gates["grounded_claim_rate"] is None


# ---------------------------------------------------------------- run_eval 聚合

def test_aggregate_excludes_incomplete(monkeypatch):
    import evals.runners.run_eval as re_mod
    results = [
        {"status": "PASS", "scores": {"analysis": 1.0}, "metrics": {"p0": 0, "p1": 0, "judge_error_count": 0, "judge_total": 6}, "errors": []},
        {"status": "INCOMPLETE", "scores": {"analysis": 1.0}, "metrics": {"p0": 0, "p1": 0, "judge_error_count": 2, "judge_total": 6}, "errors": []},
        {"status": "FAIL", "scores": {"analysis": 0.5}, "metrics": {"p0": 0, "p1": 0, "judge_error_count": 0, "judge_total": 6}, "errors": []},
    ]
    agg = re_mod._aggregate(results)
    # INCOMPLETE 不进 pass_rate 与 mean
    assert agg["cases_total"] == 2
    assert agg["cases_incomplete"] == 1
    assert agg["pass_rate"] == 0.5
    assert agg["mean_scores"]["analysis"] == 0.75
    # judge 统计含全部 case
    assert agg["judge_error_count"] == 2
    assert agg["judge_success_rate"] == pytest.approx(round((18 - 2) / 18, 4))


def test_get_backend_returns_null_without_env(monkeypatch):
    monkeypatch.delenv("EVAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("EVAL_LLM_API_KEY", raising=False)
    old = CONFIG["judge"]["backend"]
    CONFIG["judge"]["backend"] = "llm"
    try:
        assert isinstance(get_backend(), NullJudgeBackend)
    finally:
        CONFIG["judge"]["backend"] = old
# ---------------------------------------------------------------- INCOMPLETE 决策

def test_decide_status_incomplete_only_in_llm_mode(monkeypatch):
    import evals.runners.run_eval as re_mod
    old = CONFIG["judge"]["backend"]
    try:
        CONFIG["judge"]["backend"] = "llm"
        assert re_mod._decide_status(gates_ok=True, judge_err=1) == "INCOMPLETE"
        assert re_mod._decide_status(gates_ok=True, judge_err=0) == "PASS"
        assert re_mod._decide_status(gates_ok=False, judge_err=0) == "FAIL"
        CONFIG["judge"]["backend"] = "null"
        # null 模式下 judge 失败不会标 incomplete（null 不可能失败，防御性验证）
        assert re_mod._decide_status(gates_ok=False, judge_err=0) == "FAIL"
    finally:
        CONFIG["judge"]["backend"] = old


def test_result_schema_allows_incomplete():
    import json, jsonschema
    schema = json.loads(Path(Path(__file__).resolve().parents[2] / "evals" / "schemas" / "result.schema.json").read_text(encoding="utf-8"))
    assert "INCOMPLETE" in schema["properties"]["status"]["enum"]