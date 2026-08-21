"""Judge profile + retry 机制测试。

覆盖：
- profile 选择（fast / release）：model / timeout / max_retries 来自 profile
- 未指定 profile 保持现有行为（model 来自 EVAL_LLM_MODEL）
- timeout 生效
- 429 / 5xx 重试（exponential backoff）
- 400 不重复重试
- JSON schema 格式错误重试一次
- retry 后成功 / retry 用尽后 error
- release profile 不降级（model 固定 qwen3.5-plus，不随 .env MODEL 变）
- retry log 写入
- judge_retry_count 聚合（analytical + grounding）
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.graders.common import CONFIG
from evals.graders.judge import JudgeResult, LLMJudgeBackend, NullJudgeBackend, get_backend


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

    def json(self):
        return {"choices": [{"message": {"content": self.text}}]}


class FakeRequests:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append(time.time())
        if not self._responses:
            raise RuntimeError("no more responses")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _backend(reqs, max_retries=0, backoff_base=0.02, **kw):
    b = LLMJudgeBackend("https://fake/v1", "k", "m", backoff_base=backoff_base, **kw)
    b._requests = reqs
    b.max_retries = max_retries
    return b


def _ok_json(score=3):
    return json.dumps({"score": score, "reason": "r", "evidence": ["e"]})


# ---------------------------------------------------------------- profile 选择

def _enable_llm(monkeypatch):
    monkeypatch.setenv("EVAL_LLM_BASE_URL", "https://fake/v1")
    monkeypatch.setenv("EVAL_LLM_API_KEY", "sk-fake")
    monkeypatch.setitem(CONFIG["judge"], "backend", "llm")


def test_profile_fast(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setenv("EVAL_LLM_MODEL", "should-not-use")
    b = get_backend(profile="fast")
    assert isinstance(b, LLMJudgeBackend)
    assert b.model == "qwen-flash"
    assert b.timeout == 120
    assert b.max_retries == 1
    assert b.profile_name == "fast"


def test_profile_release(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setenv("EVAL_LLM_MODEL", "qwen-flash")  # .env 是 flash，release 不得降级
    b = get_backend(profile="release")
    assert b.model == "qwen3.5-plus"   # profile.model 优先，不随 .env 变
    assert b.timeout == 300
    assert b.max_retries == 2


def test_profile_from_config(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setitem(CONFIG["judge"], "profile", "release")
    try:
        b = get_backend()
        assert b.model == "qwen3.5-plus"
    finally:
        monkeypatch.setitem(CONFIG["judge"], "profile", None)


def test_no_profile_keeps_legacy(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setenv("EVAL_LLM_MODEL", "legacy-model")
    b = get_backend()
    assert b.model == "legacy-model"          # 未指定 profile：model 来自 env
    assert b.profile_name is None
    assert b.timeout == 120                   # 来自 llm 配置


def test_unknown_profile_raises(monkeypatch):
    _enable_llm(monkeypatch)
    with pytest.raises(ValueError):
        get_backend(profile="nope")


def test_backend_null_without_llm(monkeypatch):
    monkeypatch.setitem(CONFIG["judge"], "backend", "null")
    assert isinstance(get_backend(), NullJudgeBackend)


# ---------------------------------------------------------------- retry 语义

def test_timeout_seconds_effective(monkeypatch):
    _enable_llm(monkeypatch)
    assert get_backend(profile="release").timeout == 300


def test_429_retry_then_success():
    reqs = FakeRequests([FakeResponse(429, "limited"), FakeResponse(200, text=_ok_json(3))])
    b = _backend(reqs, max_retries=2)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "success" and r.score == 3
    assert len(reqs.calls) == 2
    assert r.retries == 1


def test_5xx_retry_then_success():
    reqs = FakeRequests([FakeResponse(503, "down"), FakeResponse(200, text=_ok_json(4))])
    b = _backend(reqs, max_retries=2)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "success" and r.score == 4
    assert r.retries == 1


def test_400_no_retry():
    reqs = FakeRequests([FakeResponse(400, "bad request")])
    b = _backend(reqs, max_retries=5)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert "http_error 400" in r.error
    assert len(reqs.calls) == 1          # 不重试
    assert r.retries == 0


def test_401_no_retry():
    reqs = FakeRequests([FakeResponse(401, "unauthorized")])
    b = _backend(reqs, max_retries=5)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error" and len(reqs.calls) == 1


def test_retry_exhausted_error():
    reqs = FakeRequests([FakeResponse(503, "down")] * 3)
    b = _backend(reqs, max_retries=2)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert len(reqs.calls) == 3          # 1 + 2 重试
    assert r.retries == 2
    assert r.score is None


def test_format_error_retry_once_then_success():
    # 第一次 schema 错误（score 越界）-> 重试 -> 合法
    bad = json.dumps({"score": 99, "reason": "x"})
    reqs = FakeRequests([FakeResponse(200, text=bad), FakeResponse(200, text=_ok_json(3))])
    b = _backend(reqs, max_retries=0)    # 格式重试独立于 max_retries
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "success" and r.score == 3
    assert r.retries == 1


def test_format_error_retry_once_then_error():
    bad = json.dumps({"score": 99, "reason": "x"})
    reqs = FakeRequests([FakeResponse(200, text=bad), FakeResponse(200, text=bad)])
    b = _backend(reqs, max_retries=0)
    r = b.judge("counter_evidence", "doc", 5)
    assert r.status == "error"
    assert "schema_error" in r.error
    assert r.retries == 1


def test_backoff_exponential():
    reqs = FakeRequests([FakeResponse(503, "d1"), FakeResponse(503, "d2"), FakeResponse(200, text=_ok_json(3))])
    b = _backend(reqs, max_retries=3, backoff_base=0.03)
    b.judge("counter_evidence", "doc", 5)
    # backoff: 0.03, 0.06 -> 调用间隔递增
    d1 = reqs.calls[1] - reqs.calls[0]
    d2 = reqs.calls[2] - reqs.calls[1]
    assert d1 >= 0.02 and d2 >= 0.05, (d1, d2)


def test_retry_log_written(monkeypatch, tmp_path):
    log = tmp_path / "judge_retries.log"
    monkeypatch.setenv("EVAL_JUDGE_LOG", str(log))
    reqs = FakeRequests([FakeResponse(503, "down"), FakeResponse(200, text=_ok_json(3))])
    b = _backend(reqs, max_retries=2)
    b.judge("counter_evidence", "doc", 5)
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["dimension"] == "counter_evidence"
    assert "http_error 503" in rec["error"]
    assert rec["delay_s"] >= 0


# ---------------------------------------------------------------- 聚合（incomplete 不降级）

def test_judge_retry_count_aggregation(tmp_path, monkeypatch):
    import evals.graders.analytical_quality as aq
    from evals.tests.conftest import GOOD_DOC, make_doc

    class RetryBackend:
        name = "llm"
        def judge(self, dim, doc, max_score=None):
            return JudgeResult(dimension=dim, score=3, max_score=5, reason="r",
                               retries=2, status="success", backend_name="llm")

    monkeypatch.setattr(aq, "get_backend", lambda: RetryBackend())
    d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
    r = aq.grade(d, None)
    assert r.metrics["judge_retry_count"] == 6 * 2   # 6 维 × 2 次重试


def test_release_failure_stays_incomplete(monkeypatch, tmp_path):
    """release profile 下 judge 最终失败：analytical 层 error，不降级、case INCOMPLETE。"""
    import evals.graders.analytical_quality as aq
    import evals.runners.run_eval as re_mod
    from evals.tests.conftest import GOOD_DOC, make_doc

    class AllFailBackend:
        name = "llm"
        def judge(self, dim, doc, max_score=None):
            return JudgeResult(dimension=dim, score=None, max_score=5, status="error",
                               error="release 模型最终失败", retries=2, backend_name="llm")

    monkeypatch.setattr(aq, "get_backend", lambda: AllFailBackend())
    monkeypatch.setitem(CONFIG["judge"], "backend", "llm")
    monkeypatch.setitem(CONFIG["judge"], "profile", "release")
    try:
        d = make_doc(tmp_path, GOOD_DOC, "测试公司 管理层档案 80 2026-07-01.md")
        r = aq.grade(d, None)
        assert r.score is None
        assert r.metrics["judge_error_count"] == 6
        assert r.metrics["judge_retry_count"] == 6 * 2
        # 不降级：backend 是 llm（失败即 error），不是 null/flash
        assert r.details["judge_backend"] == "llm"
        # INCOMPLETE 决策（llm 模式 + judge 失败）
        assert re_mod._decide_status(gates_ok=True, judge_err=r.metrics["judge_error_count"]) == "INCOMPLETE"
    finally:
        monkeypatch.setitem(CONFIG["judge"], "profile", None)
