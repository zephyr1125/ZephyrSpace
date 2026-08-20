"""Eval runners: run_skill, run_eval, compare_runs."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_dotenv_loaded = False


def ensure_env() -> None:
    """Eval CLI 统一入口：加载项目根 .env（幂等）。

    - 显式传 vault 根目录的 .env 路径，不依赖 cwd；
    - override=False：已存在的环境变量（如 PowerShell $env:... 手工设置）优先，.env 只是兜底；
    - 仅由 Eval CLI（run_eval / compare_runs）启动时调用一次，不在各 grader 中重复调用。
    """
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    root = Path(__file__).resolve().parents[2]  # evals/runners -> vault 根
    load_dotenv(root / ".env", override=False)
    _dotenv_loaded = True
