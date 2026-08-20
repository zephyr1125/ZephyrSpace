"""统一 .env 加载测试（evals/runners.ensure_env）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.runners import ensure_env


def test_ensure_env_loads_project_dotenv():
    root = Path(__file__).resolve().parents[2]
    env_file = root / ".env"
    if not env_file.exists():
        pytest.skip("项目根 .env 不存在")
    os.environ.pop("EVAL_LLM_BASE_URL", None)
    ensure_env()
    assert os.environ.get("EVAL_LLM_BASE_URL") == "https://api.openai.com/v1"
    assert "EVAL_LLM_MODEL" in os.environ


def test_ensure_env_idempotent():
    before = os.environ.get("EVAL_LLM_BASE_URL")
    ensure_env()  # 已加载过则直接返回
    ensure_env()
    assert os.environ.get("EVAL_LLM_BASE_URL") == before


def test_ensure_env_does_not_override_existing():
    os.environ["EVAL_LLM_BASE_URL"] = "https://manual.example/v1"
    try:
        ensure_env()
        assert os.environ.get("EVAL_LLM_BASE_URL") == "https://manual.example/v1"
    finally:
        os.environ.pop("EVAL_LLM_BASE_URL", None)
