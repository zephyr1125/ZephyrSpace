"""只读取目标任务及其子任务的日志元数据，汇总真实用量；不导出提示词或推理正文。"""
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")


def events(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def metadata(path):
    event = next(events(path))
    return event.get("payload", {}) if event.get("type") == "session_meta" else {}


def parent(meta):
    source = meta.get("source", {})
    if not isinstance(source, dict):
        return None
    return source.get("subagent", {}).get("thread_spawn", {}).get("parent_thread_id")


def summarize(path, until=None):
    last = None
    samples = 0
    changes = 0
    decreases = []
    models, calls = set(), Counter()
    turns = []
    for event in events(path):
        if until and datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")) > until:
            continue
        payload = event.get("payload", {})
        if event.get("type") == "turn_context" and payload.get("model"):
            models.add(payload["model"])
        if event.get("type") == "response_item" and payload.get("type") == "function_call":
            calls[payload.get("name", "unknown")] += 1
        if event.get("type") != "event_msg":
            continue
        if payload.get("type") == "task_complete":
            turns.append({"timestamp": event["timestamp"], "duration_ms": payload.get("duration_ms"),
                          "error": bool(payload.get("error"))})
        if payload.get("type") != "token_count" or not payload.get("info"):
            continue
        usage = payload["info"].get("total_token_usage")
        if not usage:
            continue
        samples += 1
        if last != usage:
            changes += 1
        if last and any(usage.get(k, 0) < last.get(k, 0) for k in FIELDS):
            decreases.append(event["timestamp"])
        last = usage
    usage = {k: last.get(k) for k in FIELDS} if last else {k: None for k in FIELDS}
    # 累计快照只取末值；不得把每次快照重复相加。计数器回退时拒绝给出总量。
    if decreases:
        usage = {k: None for k in FIELDS}
    usage["uncached_input_tokens"] = (usage["input_tokens"] - usage["cached_input_tokens"]
                                        if usage["input_tokens"] is not None and usage["cached_input_tokens"] is not None else None)
    return {"usage": usage, "usage_samples": samples, "distinct_counter_updates": changes,
            "counter_decreases": decreases, "logged_models": sorted(models), "completed_turns": turns,
            "tool_calls": dict(calls)}


def audit(log_directory, root_id, until=None):
    catalog = {}
    for path in Path(log_directory).rglob("*.jsonl"):
        meta = metadata(path)
        if meta.get("id"):
            if meta["id"] in catalog:
                raise ValueError("同一会话出现多个日志，需先核对重叠，不能重复计量")
            catalog[meta["id"]] = (path, meta)
    if root_id not in catalog:
        raise ValueError("未找到目标任务日志")
    chosen = {root_id}
    while True:
        extra = {key for key, (_, meta) in catalog.items() if parent(meta) in chosen}
        if extra <= chosen:
            break
        chosen |= extra
    rows = []
    for key in sorted(chosen):
        path, meta = catalog[key]
        source = meta.get("source", {})
        role = source.get("subagent", {}).get("thread_spawn", {}).get("agent_role") if isinstance(source, dict) else "root"
        rows.append({"thread_id": key, "parent_thread_id": parent(meta), "role": role,
                     "log_path": str(path), **summarize(path, until)})
    fields = (*FIELDS, "uncached_input_tokens")
    totals = {field: sum(row["usage"][field] for row in rows)
              if all(row["usage"][field] is not None for row in rows) else None for field in fields}
    return {"root_thread_id": root_id, "until": until.isoformat() if until else None,
            "source": "本地session_meta/turn_context与event_msg.token_count累计末值；含主任务及可定位的所有后代",
            "sessions": rows, "totals": totals,
            "limitations": ["累计输入包含重复上下文；缓存输入是其子集，不等于新增阅读量或账户额度扣减。",
                            "reasoning_output_tokens是output_tokens子项，不能再次相加；无价格信息，不计算费用。",
                            "不同公司不是冻结证据配对试验，不能把总量差异直接归因为流程修改。",
                            "日志目录若缺子任务文件会低估；用角色数和调度记录核对完整性。",
                            "模型字段为日志记录，不声称独立验证后端实际模型。"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path)
    parser.add_argument("root_id")
    parser.add_argument("--until")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.logs, args.root_id, datetime.fromisoformat(args.until.replace("Z", "+00:00")) if args.until else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"sessions": len(result["sessions"]), "totals": result["totals"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
