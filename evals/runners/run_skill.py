"""Skill 执行层（plan §3 runners/run_skill.py）。

统一接口：给定 (case, skill_path) 产出 RunArtifacts（输出 markdown + trace + 耗时）。

- ReplayRunner: Frozen Eval —— 回放既有输出（vault 内已有档案 / 显式 output 路径 / runs 目录）
- ClaudeAgentRunner: Live Eval —— 通过 Claude Code CLI（项目现有 agent 执行入口）真实运行
  management-archive Skill，工具级 trace 来自 stream-json，数据源级 trace 来自
  api_tracker 转发器（EVAL_TRACE_PATH）写出的 JSONL。
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..graders.common import VAULT_ROOT, EvalCase, load_archive
from .trace_recorder import load_trace


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunArtifacts:
    case_id: str
    output_path: Optional[Path] = None
    trace: Optional[Dict[str, Any]] = None
    runtime_seconds: float = 0.0
    error: Optional[str] = None
    final_markdown: str = ""
    exit_code: Optional[int] = None
    stream_path: Optional[Path] = None
    sources_path: Optional[Path] = None


class SkillRunner:
    """基类契约。子类实现 run()。"""
    def run(self, case: EvalCase, skill_path: Path) -> RunArtifacts:
        raise NotImplementedError


# ---------------------------------------------------------------- ReplayRunner（Frozen）

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


# ---------------------------------------------------------------- ClaudeAgentRunner（Live）

MARKET_LABELS = {"A": "A股", "H": "港股", "US": "美股"}


def build_live_prompt(case: EvalCase, skill_path: Path) -> str:
    """构造 Live 运行提示词：指示 Claude Code 阅读 SKILL.md 并按其执行。"""
    company = case.company
    market = MARKET_LABELS.get(company.get("market", ""), company.get("market", ""))
    sp = skill_path
    if not sp.is_absolute():
        sp = VAULT_ROOT / sp
    return (
        "你是一个管理层档案分析执行 agent（Eval 沙盒运行）。\n"
        f"任务：为公司 {company.get('name')}（{company.get('ticker')}，{market}）建立管理层档案。\n"
        "\n"
        "执行要求：\n"
        f"1. 首先阅读 SKILL 文件：{sp}\n"
        "2. 严格按该 SKILL 的「数据拉取执行清单」拉取数据"
        "（CNINFO / 理杏仁 / 智堡 / Tavily / 本地年报 MD），并按「档案页面模板」撰写档案。\n"
        "3. 完成 SKILL 强制的双 Agent 审核与 P1 修复（可启动子 agent 审核）。\n"
        "4. 档案输出到 vault 的 管理层档案/ 目录，文件命名严格遵循 SKILL 规定："
        "[公司简称] 管理层档案 [评分] YYYY-MM-DD.md。\n"
        "\n"
        "沙盒约束（必须遵守）：\n"
        "- 只输出管理层档案文件；不要修改 01-公司/ 公司页、深度分析页，不要 git 提交，"
        "不要修改任何其他文件。\n"
        "- 不要执行任务以外的操作。\n"
        "\n"
        "最后，用一条消息报告：输出的档案文件完整路径 + 一句话总结。"
    )


def parse_claude_stream(path: Path) -> List[Dict[str, Any]]:
    """解析 claude --output-format stream-json 输出，提取工具调用 trace。"""
    steps: List[Dict[str, Any]] = []
    pending: Dict[str, int] = {}   # tool_use_id -> step index
    if not path.exists():
        return steps
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        mtype = msg.get("type")
        if mtype == "assistant":
            content = msg.get("message", {}).get("content", []) or []
            ts = msg.get("message", {}).get("timestamp") or _now_utc()
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                idx = len(steps)
                steps.append({
                    "tool_name": str(block.get("name", "Tool")),
                    "arguments": block.get("input", {}) or {},
                    "timestamp": ts,
                    "result_status": "pending",
                })
                if block.get("id"):
                    pending[str(block["id"])] = idx
        elif mtype == "user":
            content = msg.get("message", {}).get("content", []) or []
            ts = msg.get("message", {}).get("timestamp") or _now_utc()
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tid = block.get("tool_use_id")
                if tid and str(tid) in pending:
                    idx = pending.pop(str(tid))
                    steps[idx]["result_status"] = "error" if block.get("is_error") else "ok"
                    if steps[idx]["timestamp"] and ts:
                        try:
                            from datetime import datetime as _dt
                            t0p = _dt.fromisoformat(str(steps[idx]["timestamp"]).replace("Z", "+00:00"))
                            t1p = _dt.fromisoformat(str(ts).replace("Z", "+00:00"))
                            steps[idx]["duration_ms"] = round((t1p - t0p).total_seconds() * 1000, 1)
                        except Exception:
                            pass
                    if block.get("is_error"):
                        steps[idx]["error"] = str(block.get("content", ""))[:300]
    return steps


def parse_source_trace(path: Path) -> List[Dict[str, Any]]:
    """解析 api_tracker 转发器写出的数据源级 trace JSONL（call/result 事件）。"""
    steps: List[Dict[str, Any]] = []
    if not path.exists():
        return steps
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        tool = str(rec.get("tool_name", "source"))
        if rec.get("event") == "call":
            steps.append({
                "tool_name": tool,
                "arguments": rec.get("arguments", {}) or {},
                "timestamp": rec.get("timestamp"),
                "result_status": "pending",
                "source_level": True,
            })
        elif rec.get("event") == "result":
            for idx in reversed(range(len(steps))):
                if (steps[idx].get("tool_name") == tool
                        and steps[idx].get("result_status") == "pending"
                        and steps[idx].get("source_level")):
                    steps[idx]["result_status"] = rec.get("result_status", "ok")
                    steps[idx]["duration_ms"] = rec.get("duration_ms", 0)
                    if rec.get("error"):
                        steps[idx]["error"] = rec["error"]
                    break
    return steps


class ClaudeAgentRunner(SkillRunner):
    """Live Eval：通过 Claude Code CLI 真实执行 management-archive Skill。

    调用链：
      run_eval --mode live
        -> ClaudeAgentRunner.run(case, skill_path)
          -> claude -p <prompt> --output-format stream-json --include-partial-messages
                 --permission-mode bypassPermissions
          -> parse_claude_stream  -> 工具级 trace（Bash/Read/Write/Task/Edit...）
          -> parse_source_trace   -> 数据源级 trace（cninfo/lixinger/wisburg/tavily，经 api_tracker 转发器）
          -> 发现输出档案文件 -> RunArtifacts（含 final_markdown / trace / runtime / error）
    """

    def __init__(self, cli: str = "claude", runs_dir: Optional[Path] = None,
                 timeout_s: int = 1800, model: Optional[str] = None,
                 permission_mode: str = "bypassPermissions",
                 extra_flags: Optional[List[str]] = None):
        self.cli = cli
        self.runs_dir = runs_dir
        self.timeout_s = timeout_s
        self.model = model
        self.permission_mode = permission_mode
        self.extra_flags = extra_flags or []

    def run(self, case: EvalCase, skill_path: Path) -> RunArtifacts:
        t0 = time.time()
        ws = (self.runs_dir / case.id) if self.runs_dir else (VAULT_ROOT / "evals" / "reports" / ".live" / case.id)
        ws.mkdir(parents=True, exist_ok=True)
        stream_path = ws / "claude_stream.jsonl"
        sources_path = ws / "trace_sources.jsonl"

        prompt = build_live_prompt(case, skill_path)
        cmd = self._build_command(prompt)
        env = dict(os.environ)
        env["EVAL_TRACE_PATH"] = str(sources_path)
        env["PYTHONIOENCODING"] = "utf-8"

        exit_code: Optional[int] = None
        error: Optional[str] = None
        try:
            with open(stream_path, "wb") as out:
                proc = subprocess.run(
                    cmd, stdout=out, stderr=subprocess.STDOUT,
                    cwd=str(VAULT_ROOT), env=env, timeout=self.timeout_s,
                )
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            error = f"claude CLI 超时（>{self.timeout_s}s），输出保留在 {stream_path}"
        except Exception as e:  # noqa: BLE001
            error = f"claude CLI 启动失败: {e}"

        tool_steps = parse_claude_stream(stream_path)
        source_steps = parse_source_trace(sources_path)
        trace = {
            "case_id": case.id,
            "skill_version": "live",
            "model": self.model,
            "started_at": _now_utc(),
            "finished_at": _now_utc(),
            "steps": tool_steps + source_steps,
        }

        output = self._discover_output(case, t0)
        final_md = output.read_text(encoding="utf-8") if output else ""
        return RunArtifacts(
            case_id=case.id,
            output_path=output,
            trace=trace,
            runtime_seconds=round(time.time() - t0, 2),
            error=error,
            final_markdown=final_md,
            exit_code=exit_code,
            stream_path=stream_path,
            sources_path=sources_path,
        )

    def _build_command(self, prompt: str) -> List[str]:
        cmd = [self.cli, "-p", prompt,
               "--output-format", "stream-json",
               "--include-partial-messages",
               "--verbose",
               "--permission-mode", self.permission_mode]
        if self.model:
            cmd += ["--model", self.model]
        if self.extra_flags:
            cmd += self.extra_flags
        return cmd

    def _discover_output(self, case: EvalCase, since: float) -> Optional[Path]:
        d = VAULT_ROOT / "管理层档案"
        if not d.exists():
            return None
        name = case.company.get("name", "")
        candidates = sorted(d.glob(name + "*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        # 只接受本次运行期间创建/更新的文件，避免误评旧档案
        fresh = [c for c in candidates if c.stat().st_mtime >= since - 5]
        return fresh[0] if fresh else None


def get_runner(kind: str = "replay", **kwargs) -> SkillRunner:
    if kind in ("replay", "frozen"):
        return ReplayRunner(**kwargs)
    if kind in ("agent", "live"):
        return ClaudeAgentRunner(**kwargs)
    raise ValueError(f"未知 runner: {kind}")