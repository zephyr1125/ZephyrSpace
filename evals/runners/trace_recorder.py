
"""Agent Trace 记录器（plan §2 / §8 / §17 基础设施）。

- TraceRecorder: 记录工具调用（tool_name / arguments / timestamp / result_status / parent_step）
- 输出符合 evals/schemas/trace.schema.json
- 供 run_skill 的 agent 执行注入；也可离线读取已有 trace 文件

用法（在 agent 执行层埋点）：
    from evals.runners.trace_recorder import TraceRecorder
    rec = TraceRecorder(case_id="...", skill_version="v18")
    with rec.step("cninfo.executive_trades", {"stock_code": "000333"}):
        result = ...
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceRecorder:
    def __init__(self, case_id: str, skill_version: Optional[str] = None, model: Optional[str] = None):
        self.case_id = case_id
        self.skill_version = skill_version
        self.model = model
        self.started_at = _now()
        self.finished_at: Optional[str] = None
        self._steps: List[Dict[str, Any]] = []
        self._stack: List[Optional[str]] = []

    @contextmanager
    def step(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Iterator[None]:
        parent = self._stack[-1] if self._stack else None
        entry = {
            "tool_name": tool_name,
            "arguments": arguments or {},
            "timestamp": _now(),
            "result_status": "ok",
            "parent_step": parent,
            "_step_index": len(self._steps),
        }
        self._steps.append(entry)
        self._stack.append(f"step_{entry['_step_index']}")
        try:
            yield
        except Exception:
            entry["result_status"] = "error"
            raise
        finally:
            self._stack.pop()

    def record(self, tool_name: str, arguments: Dict[str, Any],
               result_status: str = "ok", parent_step: Optional[str] = None) -> None:
        self._steps.append({
            "tool_name": tool_name,
            "arguments": arguments,
            "timestamp": _now(),
            "result_status": result_status,
            "parent_step": parent_step,
        })

    def to_dict(self) -> Dict[str, Any]:
        self.finished_at = _now()
        steps = []
        for s in self._steps:
            steps.append({k: v for k, v in s.items() if not k.startswith("_")})
        return {
            "case_id": self.case_id,
            "skill_version": self.skill_version,
            "model": self.model,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "steps": steps,
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def load_trace(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def steps_of(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    return trace.get("steps", [])
def validate_trace(trace: Dict[str, Any]) -> List[str]:
    """用 evals/schemas/trace.schema.json 校验 trace，返回错误列表（空=合法）。"""
    import json as _json
    from pathlib import Path as _Path
    schema_path = _Path(__file__).resolve().parents[1] / "schemas" / "trace.schema.json"
    try:
        import jsonschema
        schema = _json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(trace, schema)
        return []
    except Exception as e:
        return [str(e)]
