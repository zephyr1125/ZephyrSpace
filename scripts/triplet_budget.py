"""单一预算配置、派发预留及只读日志监测；中断须由主任务调用Agent工具执行。"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def stamp(text):
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    require(value.tzinfo is not None, "时间必须包含时区")
    return value


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate(config):
    require(config.get("schema_version") == 1, "未知预算版本")
    for key in ("total_limit", "coordinator_limit", "closeout_reserve", "inflight_reserve", "max_active", "stale_seconds"):
        require(type(config.get(key)) is int and config[key] > 0, "预算字段须为正整数：" + key)
    require(config["closeout_reserve"] < config["total_limit"], "收尾余量必须小于总预算")
    require(config["coordinator_limit"] > config["inflight_reserve"], "协调额度不足以覆盖在途余量")
    require(config.get("roles") and config.get("root_thread_id") and config.get("root_log"), "缺角色或根会话")
    require("coordinator" not in config["roles"], "coordinator保留给根任务，不得被子角色覆盖")
    stamp(config["since"])
    for role, limit in config["roles"].items():
        require(type(limit) is int and limit > config["inflight_reserve"], "角色额度必须大于在途余量：" + role)
    for group in config.get("groups", {}).values():
        require(type(group["limit"]) is int and group["limit"] > 0, "组合预算非法")
        require(group["roles"] and len(set(group["roles"])) == len(group["roles"])
                and set(group["roles"]) <= set(config["roles"]), "组合角色缺失或重复")


def usage(path, thread_id, since, now, parent_id=None):
    """累计末值减起点，未知/回退/半行日志阻断新增派发，不虚填零。"""
    baseline = latest = previous = None
    latest_at = None
    with Path(path).open(encoding="utf-8") as stream:
        first = json.loads(next(stream))
        meta = first["payload"]
        require(first["type"] == "session_meta" and meta["id"] == thread_id, "日志会话身份不匹配")
        if parent_id:
            source = meta.get("source", {})
            require(isinstance(source, dict) and source.get("subagent", {}).get("thread_spawn", {}).get("parent_thread_id") == parent_id,
                    "子会话不属于本次根任务")
        created = stamp(first["timestamp"])
        for line in stream:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # 正在写入的尾行本身没有可信计数，不能当作预算归零。
                if not line.endswith("\n"):
                    continue
                raise
            at = stamp(event["timestamp"])
            if at > now:
                continue
            payload = event.get("payload", {})
            if event.get("type") != "event_msg" or payload.get("type") != "token_count":
                continue
            total = (payload.get("info") or {}).get("total_token_usage")
            if not total:
                continue
            fields = ("input_tokens", "cached_input_tokens", "output_tokens")
            require(all(type(total.get(k)) is int and total[k] >= 0 for k in fields), "日志缺完整用量计数")
            current = tuple(total[k] for k in fields)
            require(current[0] >= current[1], "缓存计数超过输入")
            require(previous is None or all(a >= b for a, b in zip(current, previous)), "累计计数回退")
            previous = current
            if at <= since:
                baseline = current
            latest, latest_at = current, at
    require(latest is not None, "尚无可信用量快照")
    require(baseline is not None or created >= since, "旧会话缺窗口起点，不能把缺失历史当零")
    baseline = baseline or (0, 0, 0)
    delta = [a - b for a, b in zip(latest, baseline)]
    require(delta[0] >= delta[1] and all(v >= 0 for v in delta), "窗口用量回退")
    return {"metric": delta[0] - delta[1] + delta[2], "cached_input": delta[1],
            "last_sample": latest_at.isoformat(), "age_seconds": (now - latest_at).total_seconds()}


def observe(config, state, now=None):
    validate(config)
    require(state["config_sha256"] == digest(config), "预算配置已改变；不得临时放宽原上限")
    now = now or datetime.now(timezone.utc)
    limits = role_limits(config, state)
    timeout = state.get("metering_timeout", {}).get("seconds", config["stale_seconds"])
    require(type(timeout) is int and 0 < timeout <= max(300, config["stale_seconds"]), "计量等待窗口无效")
    rows, reasons, interrupts = {}, [], []
    active = {k: v for k, v in state["roles"].items() if v["status"] in ("reserved", "running")}
    sessions = {"coordinator": {"thread_id": config["root_thread_id"], "log": config["root_log"], "status": "running"},
                **{k: v for k, v in state["roles"].items() if v.get("log")}}
    for role, session in sessions.items():
        try:
            row = usage(session["log"], session["thread_id"], stamp(config["since"]), now,
                        config["root_thread_id"] if role != "coordinator" else None)
            resumed = session.get("resumed_at")
            stale_seconds = config["stale_seconds"] if role == "coordinator" else timeout
            waiting_first_sample = (resumed and stamp(row["last_sample"]) < stamp(resumed)
                                    and 0 <= (now - stamp(resumed)).total_seconds() <= stale_seconds)
            if session["status"] == "running" and row["age_seconds"] > stale_seconds and not waiting_first_sample:
                reasons.append(role + "用量快照过期，停止而非假定无消耗")
            limit = (config["coordinator_limit"] + sum(t["amount"] for t in state.get("transfers", [])
                     if t["target"] == "coordinator")) if role == "coordinator" else limits[role]
            if row["metric"] + (config["inflight_reserve"] if session["status"] == "running" else 0) >= limit:
                reasons.append(role + "达到提前停止线")
            rows[role] = row
        except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
            reasons.append(role + "计量未知：" + str(exc))
    known = sum(r["metric"] for r in rows.values())
    inflight = config["inflight_reserve"] * (1 + len(active))
    if known + inflight + config["closeout_reserve"] >= config["total_limit"]:
        reasons.append("总预算达到提前停止线（含在途与收尾）")
    groups = {}
    for name, group in config.get("groups", {}).items():
        spent = sum(rows.get(r, {}).get("metric", 0) for r in group["roles"])
        groups[name] = spent
        pending = sum(r in active for r in group["roles"])
        if spent + pending * config["inflight_reserve"] >= group["limit"]:
            reasons.append(name + "组合达到提前停止线")
    if reasons:
        interrupts = [v["thread_id"] for v in active.values() if v.get("thread_id")]
    return {"status": "stop_required" if reasons else "ready", "at": now.isoformat(), "used_known": known,
            "rows": rows, "group_used": groups, "reasons": reasons, "interrupt_thread_ids": interrupts,
            "coordinator_action": "立即调用interrupt_agent；未知先停，禁止先催写长总结" if reasons else "可检查下一次派发预留",
            "limitations": "不是平台硬限额；日志有延迟，在途中断仍可能产生费用，主任务须执行中断。"}


def compact_observation(result):
    """监控只返回决策所需字段，完整计量仍由check读取，不改停止语义。"""
    return {**{key: result[key] for key in ("status", "at", "used_known", "reasons", "interrupt_thread_ids")},
            "metrics": {role: row["metric"] for role, row in result["rows"].items()}}


def reserve(config, state, role, now=None):
    require(role in role_limits(config, state) and role not in state["roles"], "角色未知或已经预留，重试不可更名清零")
    result = observe(config, state, now)
    require(result["status"] == "ready", "；".join(result["reasons"]))
    active = [r for r, v in state["roles"].items() if v["status"] in ("reserved", "running")]
    require(len(active) < config["max_active"], "并发预留已满，先结算已有角色")
    limits = role_limits(config, state)
    pending = sum(max(0, limits[r] - result["rows"].get(r, {}).get("metric", 0)) for r in active)
    need = result["used_known"] + pending + limits[role] + config["closeout_reserve"] + config["inflight_reserve"]
    require(need <= config["total_limit"], "剩余总预算不足以预留本角色、在途与收尾")
    for name, group in config.get("groups", {}).items():
        if role in group["roles"]:
            reserved = sum(max(0, limits[r] - result["rows"].get(r, {}).get("metric", 0))
                           for r in active if r in group["roles"])
            require(result["group_used"][name] + reserved + limits[role] <= group["limit"], "组合剩余额度不足：" + name)
    state["roles"][role] = {"status": "reserved"}
    return {"status": "reserved", "role": role, "limit": limits[role],
            "stop_line": limits[role] - config["inflight_reserve"], "config_sha256": state["config_sha256"]}


def role_limits(config, state):
    """调配只转移原角色额度；不修改总额、在途余量或配置。"""
    limits = dict(config["roles"])
    for item in state.get("transfers", []):
        donor, target, amount = item["donor"], item["target"], item["amount"]
        if item.get("new_role"):
            require(target not in limits and target != "coordinator", "接手角色已存在或名称保留")
            require(not any(donor in g["roles"] for g in config.get("groups", {}).values()), "组合内额度不得转出新角色")
            require(amount > config["inflight_reserve"], "接手角色预留不足")
            limits[target] = 0
        require(donor in limits and (target in limits or target == "coordinator") and donor != target, "调配角色无效")
        require(type(amount) is int and amount > 0 and amount < limits[donor], "调配金额无效")
        limits[donor] -= amount
        if target != "coordinator":
            limits[target] += amount
    return limits


def transfer(config, state, donor, target, amount, reason, now=None, new_role=False, unstarted=False):
    require(reason.strip(), "调配须说明原因")
    require(not any(v["status"] in ("reserved", "running") for v in state["roles"].values()), "调配前须全部停止并结算")
    result = observe(config, state, now)
    allowed_reason = target + "达到提前停止线"
    require(all(r == allowed_reason for r in result["reasons"]), "；".join(result["reasons"]))
    if unstarted:
        require(not new_role and donor not in state["roles"], "未启动调配仅限从未预留的原角色")
    else:
        require(state["roles"].get(donor, {}).get("status") == "finished", "只能调出已完成角色的剩余额度")
    limits = role_limits(config, state)
    if new_role:
        require(target not in limits and target != "coordinator" and target not in state["roles"], "接手角色名称已使用")
        require(not any(donor in g["roles"] for g in config.get("groups", {}).values()), "组合内额度不得转出新角色")
        require(amount > config["inflight_reserve"], "接手角色预留不足")
        limits[target] = 0
    require((target in limits or target == "coordinator") and donor != target and type(amount) is int and amount > 0, "调配参数无效")
    if target == "coordinator":
        require(not any(donor in g["roles"] for g in config.get("groups", {}).values()), "组合内额度不得转给协调者")
    spent = 0 if unstarted else result["rows"][donor]["metric"]
    require(limits[donor] - amount > max(spent, config["inflight_reserve"] if unstarted else 0),
            "调出额度侵占已消耗部分或未启动角色的在途余量")
    record = {"donor": donor, "target": target, "amount": amount,
        "reason": reason, "new_role": new_role, "confirmed_not_started": unstarted,
        "at": (now or datetime.now(timezone.utc)).isoformat(), "used_known": result["used_known"]}
    # 只允许用原有闲余额度解除目标角色提前线，不能解除未知计量或总预算停止。
    candidate = {**state, "transfers": [*state.get("transfers", []), record]}
    checked = observe(config, candidate, now)
    require(checked["status"] == "ready", "调配后仍不可继续：" + "；".join(checked["reasons"]))
    state.setdefault("transfers", []).append(record)
    return {"status": "transferred", "limits": role_limits(config, state), "used_known": result["used_known"]}


def resume(config, state, role, now=None):
    now = now or datetime.now(timezone.utc)
    session = state["roles"].get(role, {})
    require(session.get("status") == "finished" and session.get("thread_id"), "只能恢复已确认停止的同一会话")
    result = observe(config, state, now)
    require(result["status"] == "ready", "；".join(result["reasons"]))
    limits = role_limits(config, state)
    spent = result["rows"][role]["metric"]
    require(spent + config["inflight_reserve"] < limits[role], "原角色剩余额度不足")
    active = [r for r, v in state["roles"].items() if v["status"] in ("reserved", "running")]
    require(len(active) < config["max_active"], "并发预留已满")
    pending = sum(max(0, limits[r] - result["rows"].get(r, {}).get("metric", 0)) for r in active)
    require(result["used_known"] + pending + limits[role] - spent + config["closeout_reserve"]
            + config["inflight_reserve"] <= config["total_limit"], "剩余总预算不足")
    for name, group in config.get("groups", {}).items():
        if role in group["roles"]:
            reserved = sum(max(0, limits[r] - result["rows"].get(r, {}).get("metric", 0)) for r in active if r in group["roles"])
            require(result["group_used"][name] + reserved + limits[role] - spent <= group["limit"], "组合剩余额度不足")
    session.update(status="running", resumed_at=now.isoformat())
    session.setdefault("resumes", []).append({"at": now.isoformat(), "spent": spent})
    return {"status": "resume_reserved", "role": role, "thread_id": session["thread_id"],
            "spent": spent, "limit": limits[role], "stop_line": limits[role] - config["inflight_reserve"]}


def metering_timeout(config, state, seconds, reason, now=None):
    """记录平台计量延迟校准，不改变金额、已花费或停止线。"""
    require(type(seconds) is int and 1 <= seconds <= 300 and reason.strip(), "等待窗口须为1至300秒并说明原因")
    require(not any(v["status"] in ("reserved", "running") for v in state["roles"].values()), "校准前须全部停止并结算")
    result = observe(config, state, now)
    require(result["status"] == "ready", "；".join(result["reasons"]))
    event = {"seconds": seconds, "reason": reason, "at": (now or datetime.now(timezone.utc)).isoformat(),
             "used_known": result["used_known"]}
    state.setdefault("metering_timeout_history", []).append(event)
    state["metering_timeout"] = event
    return {"status": "metering_timeout_calibrated", **event}


def bind(config, state, role, thread_id, log):
    require(state["roles"].get(role, {}).get("status") == "reserved", "须先预留再绑定会话")
    require(thread_id != config["root_thread_id"] and all(v.get("thread_id") != thread_id for v in state["roles"].values()),
            "同一会话不得重复计费或充作两个独立角色")
    state["roles"][role].update(status="running", thread_id=thread_id, log=str(Path(log).resolve()))


def initial_sample(config, state, role, seconds=0, *, observer=None, clock=None, sleeper=None):
    """仅容忍首次计量的短暂到达延迟；身份错误和任何已知停止条件立即返回。"""
    require(0 <= seconds <= 30, "首次快照等待须在0至30秒之间")
    observer, clock, sleeper = observer or observe, clock or time.monotonic, sleeper or time.sleep
    start = clock()
    while True:
        result = observer(config, state)
        elapsed = clock() - start
        if result.get("reasons") != [f"{role}计量未知：尚无可信用量快照"] or elapsed >= seconds:
            result["initial_sample_wait_seconds"] = round(elapsed, 3)
            return result
        sleeper(min(1, seconds-elapsed))


@contextmanager
def locked(path):
    marker = Path(str(path) + ".lock")
    with marker.open("x", encoding="utf-8") as stream:
        stream.write("仅主任务串行修改预算状态\n")
    try:
        yield
    finally:
        marker.unlink()


def write_state(path, value):
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("state", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("check")
    watch = sub.add_parser("watch")
    watch.add_argument("--seconds", type=int, default=30, choices=range(1, 61))
    watch.add_argument("--compact", action="store_true", help="精简监控输出，停止原因和中断清单完整保留")
    reserve_cmd = sub.add_parser("reserve")
    reserve_cmd.add_argument("role")
    register = sub.add_parser("bind")
    register.add_argument("role")
    register.add_argument("thread_id")
    register.add_argument("log")
    register.add_argument("--wait-for-first-sample", type=int, default=0, choices=range(0, 31))
    finish = sub.add_parser("finish")
    finish.add_argument("role")
    finish.add_argument("--confirmed-stopped", action="store_true", required=True)
    cancel = sub.add_parser("cancel")
    cancel.add_argument("role")
    cancel.add_argument("--confirmed-not-started", action="store_true", required=True)
    again = sub.add_parser("resume")
    again.add_argument("role")
    again.add_argument("--confirmed-stopped", action="store_true", required=True)
    move = sub.add_parser("transfer")
    move.add_argument("donor")
    move.add_argument("target")
    move.add_argument("amount", type=int)
    move.add_argument("--reason", required=True)
    move.add_argument("--confirmed-not-started", action="store_true")
    allocate = sub.add_parser("allocate")
    allocate.add_argument("donor")
    allocate.add_argument("target")
    allocate.add_argument("amount", type=int)
    allocate.add_argument("--reason", required=True)
    timeout_cmd = sub.add_parser("metering-timeout")
    timeout_cmd.add_argument("seconds", type=int)
    timeout_cmd.add_argument("--reason", required=True)
    args = parser.parse_args()
    config = load(args.config)
    validate(config)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    if args.command in ("check", "watch"):
        deadline = time.monotonic() + (args.seconds if args.command == "watch" else 0)
        while True:
            result = observe(config, load(args.state))
            if result["status"] != "ready" or time.monotonic() >= deadline:
                break
            time.sleep(1)
    else:
        with locked(args.state):
            if args.command == "init":
                require(not args.state.exists(), "预算状态已存在，禁止重置")
                state = {"config_sha256": digest(config), "roles": {}}
                result = observe(config, state)
            else:
                state = load(args.state)
                require(state["config_sha256"] == digest(config), "预算配置已改变")
                if args.command == "reserve":
                    result = reserve(config, state, args.role)
                elif args.command == "transfer":
                    result = transfer(config, state, args.donor, args.target, args.amount, args.reason,
                                      unstarted=args.confirmed_not_started)
                elif args.command == "allocate":
                    result = transfer(config, state, args.donor, args.target, args.amount, args.reason, new_role=True)
                elif args.command == "resume":
                    result = resume(config, state, args.role)
                elif args.command == "metering-timeout":
                    result = metering_timeout(config, state, args.seconds, args.reason)
                elif args.command == "bind":
                    bind(config, state, args.role, args.thread_id, args.log)
                    # 先落盘已绑定会话，进程异常时主任务仍能找到须中断的角色。
                    write_state(args.state, state)
                    result = initial_sample(config, state, args.role, args.wait_for_first_sample)
                elif args.command == "cancel":
                    require(state["roles"].get(args.role, {}).get("status") == "reserved", "仅未启动的预留可以取消")
                    state["roles"][args.role]["status"] = "cancelled"
                    result = observe(config, state)
                else:
                    require(state["roles"].get(args.role, {}).get("status") == "running", "角色未运行")
                    state["roles"][args.role]["status"] = "finished"
                    result = observe(config, state)
            write_state(args.state, state)
    if args.command == "watch" and args.compact:
        result = compact_observation(result)
    print(json.dumps(result, ensure_ascii=False))
    return int(result.get("status") == "stop_required")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"status": "stop_required", "reason": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
