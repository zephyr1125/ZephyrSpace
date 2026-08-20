
"""Skill 执行层（plan §3 runners/run_skill.py）。

统一接口：给定 (case, skill_path) 产出 RunArtifacts（输出 markdown + trace + 耗时）。

- ReplayRunner: 回放既有输出（vault 内已有档案 / 显式 output 路径 / runs 目录）
- AgentRunner: 真实 agent 执行扩展点（需要宿主 harness 注入工具调用能力与 trace 埋点；
  本模块提供接口与契约，宿主集成后即可跑 Live Eval）
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..graders.common import VAULT_ROOT, EvalCase, load_archive
from .trace_recorder import load_trace


@dataclass
class RunArtifacts:
    case_id: str
    output_path: Optional[Path] = None
    trace: Optional[Dict[str, Any]] = None
    runtime_seconds: float = 0.0
    error: Optional[str] = None


class SkillRunner:
    """基类契约。子类实现 run()。"""
    def run(self, case: EvalCase, skill_path: Path) -> RunArtifacts:
        raise NotImplementedError


class ReplayRunner(SkillRunner):
    """回放既有输出。

    输出解析优先级：
    1. case.output（显式路径）
    2. runs_dir/<case_id>/output.md（回放目录）
    3. 自动发现 vault 内 管理层档案/<公司名>* 最新文件
    """

    def __init__(self, output_dir: Optional[Path] = None, runs_dir: Optional[Path] = None):
        self.output_dir = output_dir          # 显式输出目录（如 管理层档案/）
        self.runs_dir = runs_dir              # 回放目录（含 output.md + trace.json）

    def run(self, case: EvalCase, skill_path: Path) -> RunArtifacts:
        t0 = time.time()
        output: Optional[Path] = None

        if case.output_path() and case.output_path().exists():
            output = case.output_path()
        elif self.runs_dir:
            cand = self.runs_dir / case.id / "output.md"
            if cand.exists():
                output = cand
        if output is None and self.output_dir:
            cand = self._discover_in_dir(self.output_dir, case)
            if cand:
                output = cand
        if output is None:
            cand = self._discover_in_dir(VAULT_ROOT / "管理层档案", case)
            if cand:
                output = cand

        trace = None
        if self.runs_dir:
            tpath = self.runs_dir / case.id / "trace.json"
            if tpath.exists():
                trace = load_trace(tpath)
        elif case.trace:
            tp = Path(case.trace)
            if not tp.is_absolute():
                tp = VAULT_ROOT / tp
            if tp.exists():
                trace = load_trace(tp)

        if output is None:
            return RunArtifacts(case_id=case.id, runtime_seconds=time.time() - t0,
                                error="未找到输出文件（可设 case.output 或 --output-dir）")
        return RunArtifacts(case_id=case.id, output_path=output, trace=trace,
                            runtime_seconds=time.time() - t0)

    @staticmethod
    def _discover_in_dir(d: Path, case: EvalCase) -> Optional[Path]:
        if not d.exists():
            return None
        name = case.company.get("name", "")
        candidates = sorted(d.glob(name + "*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0] if candidates else None


class AgentRunner(SkillRunner):
    """Live agent 执行扩展点。

    集成方式：宿主把自身工具调用能力 + TraceRecorder 注入，实现 run()：
        rec = TraceRecorder(case.id, skill_version)
        # 调用 agent 执行 management-archive 工作流，逐步 rec.step(...)
        # 将终稿写至临时 output.md
    """

    def run(self, case: EvalCase, skill_path: Path) -> RunArtifacts:
        raise NotImplementedError(
            "AgentRunner 是 Live Eval 扩展点：需要宿主 agent harness 注入工具调用与 trace 埋点。"
            "当前可先用 ReplayRunner 对既有档案做 Frozen Eval。"
        )


def get_runner(kind: str = "replay", **kwargs) -> SkillRunner:
    if kind == "replay":
        return ReplayRunner(**kwargs)
    if kind == "agent":
        return AgentRunner()
    raise ValueError(f"未知 runner: {kind}")
