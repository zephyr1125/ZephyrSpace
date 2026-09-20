"""按任务时间窗提取本次及上次用量，只读取日志元数据，不导出会话正文。"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import triplet_run_audit as audit


def instant(value):
    value = re.sub(r"(\.\d{6})\d+", r"\1", value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def collect(logs, root_id, since, until):
    catalog = {}
    for path in logs.rglob("*.jsonl"):
        meta = audit.metadata(path)
        key = meta.get("id")
        if not key:
            continue
        if key in catalog:
            raise ValueError("重复会话日志，拒绝重复计量")
        catalog[key] = (path, meta)
    chosen = {root_id}
    while True:
        more = {key for key, (_, meta) in catalog.items() if audit.parent(meta) in chosen}
        if more <= chosen:
            break
        chosen |= more
    fields = (*audit.FIELDS, "uncached_input_tokens")
    rows = []
    for key in sorted(chosen):
        path, meta = catalog[key]
        stamps = []
        turn_contexts = []
        for event in audit.events(path):
            stamp = instant(event["timestamp"])
            stamps.append(stamp)
            if since <= stamp <= until and event.get("type") == "turn_context":
                payload = event.get("payload", {})
                turn_contexts.append({"model": payload.get("model"), "effort": payload.get("effort")})
        if not stamps or min(stamps) > until or (max(stamps) < since and key != root_id):
            continue
        end = audit.summarize(path, until)
        before = audit.summarize(path, since)
        created_after_start = min(stamps) >= since
        usage = {}
        for field in fields:
            ev = end["usage"].get(field)
            bv = 0 if created_after_start or before["usage_samples"] == 0 else before["usage"].get(field)
            usage[field] = ev - bv if ev is not None and bv is not None and ev >= bv else None
        turns = [turn for turn in end["completed_turns"] if since <= instant(turn["timestamp"]) <= until]
        source = meta.get("source", {})
        role = source.get("subagent", {}).get("thread_spawn", {}).get("agent_role") if isinstance(source, dict) else "root"
        rows.append({"thread_id": key, "parent_thread_id": audit.parent(meta), "role": role,
                     "log_path": str(path), "usage": usage, "logged_turn_contexts": turn_contexts,
                     "completed_turns": turns,
                     "completed_duration_ms": sum(t["duration_ms"] for t in turns if t.get("duration_ms") is not None),
                     "first_event": min(stamps).isoformat(), "last_observed_event": min(max(stamps), until).isoformat(),
                     "counter_decreases": end["counter_decreases"]})
    totals = {field: sum(row["usage"][field] for row in rows)
              if rows and all(row["usage"][field] is not None for row in rows) else None for field in fields}
    return {"root_thread_id": root_id, "since": since.isoformat(), "until": until.isoformat(),
            "wall_clock_seconds": (until - since).total_seconds(), "session_count": len(rows),
            "sessions": rows, "totals": totals,
            "source": "复用triplet_run_audit.summarize：时间窗累计末值减起点前末值；窗口后创建或前已结束的子任务不纳入",
            "limitations": ["输入含反复上下文，缓存输入是总输入子集；非缓存输入=总输入-缓存输入。",
                            "累计用量快照不相加，推理输出包含在输出中。",
                            "墙钟时间不等于并行子任务耗时之和；当前主任务最终回复尚未结算部分不在截止快照内。",
                            "须与调度记录核对子任务数量；模型仅为日志记录值，不是独立后端验证。",
                            "本次为已有证据上的修复，与上次完整启动范围不同，差额不代表完整三件套节省比例。"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--until", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root_id = "01a0b9c1-dd39-7a43-ad63-635504dc0fa3"
    logs = Path("C:/Users/zephy/.codex/sessions/2026/09/19")
    previous = collect(logs, root_id, instant("2026-09-19T13:01:28.835Z"), instant("2026-09-19T14:29:32.390Z"))
    current = collect(logs, root_id, instant("2026-09-19T15:10:01.258Z"), instant(args.until))
    result = {"previous": previous, "current": current,
              "delta": {key: current["totals"][key] - previous["totals"][key]
                        if current["totals"][key] is not None and previous["totals"][key] is not None else None
                        for key in current["totals"]}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"previous": {"sessions": previous["session_count"], **previous["totals"]},
                      "current": {"sessions": current["session_count"], **current["totals"]}}, ensure_ascii=False))
