"""每日全有效池披露核验台账；不联网、不研究、不改Watchlist或报告。"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlparse, parse_qsl

BEIJING = timezone(timedelta(hours=8))
POOL_FILES = ("watchlist_strategic.json", "watchlist_core.json", "watchlist_growth.json")
SUCCESS = {"verified_no_update", "verified_new_report"}
RESULTS = SUCCESS | {"failed"}
AUTHORITIES = {
    "CN": ("cninfo.com.cn", "sse.com.cn", "szse.cn", "bse.cn"),
    "HK": ("hkexnews.hk", "hkex.com.hk"),
    "US": ("sec.gov",),
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def prioritize_candidates(candidates, priority_order):
    """Order already eligible candidates only; stale priority IDs add no candidates."""
    ranks = {}
    for item in priority_order or []:
        ranks.setdefault(item, len(ranks))
    baseline = sorted(candidates, key=lambda e: (e.get("discovered_at", ""), e["code"], e["id"]))
    return sorted(baseline, key=lambda e: ranks.get(e["id"], len(ranks)))


def preview_three_tier_order(candidates, holding_codes, paused_ids, formal_scores, *, holdings_complete=False):
    """Pure preview from eligible input and accepted scores; never reads assets or writes.

    holding_codes contains only securities in descending comparable holding value,
    never amounts. Unknown holdings must leave holdings_complete=False.
    formal_scores maps code to (accepted company score, accepted management score).
    Caller supplies filtered candidates; this helper cannot authorize selection.
    """
    import math

    baseline = prioritize_candidates(candidates, [])
    if len({e["id"] for e in baseline}) != len(baseline):
        raise ValueError("Duplicate candidate IDs")
    holding_rank = {}
    for code in holding_codes:
        holding_rank.setdefault(code, len(holding_rank))
    paused = set(paused_ids)
    held, resumed, other, missing = [], [], [], []
    totals = {}
    for entry in baseline:
        code = entry["code"]
        pair = formal_scores.get(code)
        valid = (isinstance(pair, (tuple, list)) and len(pair) == 2 and
                 all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) for n in pair))
        if valid:
            totals[entry["id"]] = sum(pair)
        if code in holding_rank:
            held.append(entry)
        elif entry["id"] in paused:
            resumed.append(entry)
        elif valid:
            other.append(entry)
        else:
            missing.append(entry)
    held.sort(key=lambda e: holding_rank[e["code"]])
    other.sort(key=lambda e: -totals[e["id"]])
    groups = {"holdings": held, "paused": resumed, "scored": other, "missing_scores": missing}
    return {"holdings_complete": bool(holdings_complete),
            "priority_order": [e["id"] for group in groups.values() for e in group],
            "groups": {key: [e["id"] for e in group] for key, group in groups.items()}}


def stamp(now):
    return now.astimezone(timezone.utc).isoformat()


def parse_time(value):
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError("核验时间必须含时区")
    return moment



def parse_cn_report_title(title):
    """Canonical full-report periods; title is discovery only, original still required."""
    title = re.sub(r"<[^>]+>", "", title)
    if any(word in title for word in ("摘要", "英文", "取消", "提示", "更正公告")):
        return None
    year = re.search(r"(20\d{2})年?", title)
    if not year:
        return None
    y = year.group(1)
    for text, period, end in (("三季度报告", "Q3", "09-30"),
                             ("半年度报告", "H1", "06-30"),
                             ("一季度报告", "Q1", "03-31"),
                             ("年度报告", "FY", "12-31")):
        if text in title:
            return y + period, y + "-" + end
    if "季度" in title and "报告" in title:
        raise ValueError("未识别季度报告标题，须核原件，不能回退旧期次")
    return None


def market(code):
    suffix = code.rsplit(".", 1)[-1]
    if suffix in {"SH", "SZ", "BJ"}:
        return "CN"
    if suffix == "HK":
        return "HK"
    if suffix == "US":
        return "US"
    raise ValueError(f"不支持的有效池代码：{code}")


def period_key(value):
    """统一明确的期次别名；不推算发布日期或跨财年口径。"""
    value = str(value).split("/")[0].strip().upper().replace(" ", "")
    patterns = [
        (r"FY(\d{4})", lambda m: ("fiscal", int(m[1]), 4)),
        (r"Q([1-4])FY(\d{4})", lambda m: ("fiscal", int(m[2]), int(m[1]))),
        (r"(\d{4})Q([1-4])", lambda m: ("calendar", int(m[1]), int(m[2]))),
        (r"(\d{4})H([12])", lambda m: ("calendar", int(m[1]), int(m[2]) * 2)),
        (r"(\d{4})(?:FY|全年|年报)", lambda m: ("calendar", int(m[1]), 4)),
    ]
    for expression, convert in patterns:
        match = re.fullmatch(expression, value)
        if match:
            return convert(match)
    return ("literal", value)


def load_pool(root):
    companies = {}
    sources = []
    for name in POOL_FILES:
        path = root / "data" / name
        document = read(path)
        sources.append({"path": "data/" + name, "sha256": digest(path), "count": len(document["entries"])})
        for entry in document["entries"]:
            code = entry["code"]
            item = {"code": code, "name": entry["name"], "market": market(code),
                    "watchlist_path": "data/" + name,
                    "incorporated_period": entry.get("lastEarningsIncorporated")}
            if code in companies and companies[code] != item:
                raise ValueError(f"重复代码的有效池信息冲突：{code}")
            companies[code] = item
    return companies, sources


def quota_gate(snapshot, now, *, mode="normal", extra_run=None):
    """Normal reserve stays strict; an explicit registered extra run is time-bound."""
    import math

    if mode not in {"normal", "pre-reset-extra"}:
        raise ValueError("未知额度模式")
    if not isinstance(snapshot, dict) or not str(snapshot.get("source", "")).startswith("official account/rateLimits/read"):
        raise ValueError("需要本次官方account/rateLimits/read快照")
    age = (now - parse_time(snapshot["checked_at"])).total_seconds()
    if not 0 <= age <= 3600 or snapshot.get("ordinaryUsageAllowed") is not True:
        raise ValueError("额度快照过期、未来时间或普通使用未获允许")
    limits = snapshot.get("rateLimits", {})
    windows = [limits.get("primary"), limits.get("secondary")]
    weekly = [x for x in windows if isinstance(x, dict) and x.get("windowDurationMins") == 10080]
    if len(weekly) != 1 or limits.get("limitId") != "codex":
        raise ValueError("官方快照没有唯一Codex周窗口")
    for window in windows:
        if isinstance(window, dict):
            usage = window.get("usedPercent")
            if (isinstance(usage, bool) or not isinstance(usage, (int, float)) or
                    not math.isfinite(usage) or not 0 <= usage <= 100):
                raise ValueError("官方额度窗口数值无效")
            if usage >= 100:
                raise ValueError("服务额度窗口耗尽；保存暂停")
    used = weekly[0].get("usedPercent")
    if isinstance(used, bool) or not isinstance(used, (int, float)) or not math.isfinite(used) or not 0 <= used <= 100:
        raise ValueError("官方周额度数值无效")
    remaining = 100 - used
    if (limits.get("spendControlReached") is True or limits.get("rateLimitReachedType") or remaining <= 0):
        raise ValueError("服务额度耗尽或服务商限制；保存暂停，不调用重置/付费")
    if mode == "normal" and remaining <= 20:
        raise ValueError("周剩余须严格大于20%，且无消费控制阻断")
    if mode == "pre-reset-extra":
        cycle = extra_cycle(snapshot, now)
        if not isinstance(extra_run, dict) or extra_run.get("state") != "active":
            raise ValueError("额外轮须先登记并续接原run_id")
        if (extra_run.get("cycle_id") != cycle["cycle_id"] or
                extra_run.get("resets_at") != cycle["resets_at"] or
                extra_run.get("window_duration_mins") != 10080 or
                extra_run.get("mode") != mode or not extra_run.get("run_id")):
            raise ValueError("额外轮与官方周窗口/reset不匹配")
        started = parse_time(extra_run["started_at"]).timestamp()
        if not cycle["resets_at"] - 14400 <= started <= now.timestamp() < cycle["resets_at"]:
            raise ValueError("额外轮启动或恢复时间越界")
    return {"checked_at": snapshot["checked_at"], "remaining_percent": remaining,
            "source": snapshot["source"], "mode": mode,
            "extra_run_id": extra_run["run_id"] if mode == "pre-reset-extra" else None}


def extra_cycle(snapshot, now):
    """Parse official Unix seconds, never infer a weekly reset from a calendar."""
    if not isinstance(snapshot, dict) or not str(snapshot.get("source", "")).startswith("official account/rateLimits/read"):
        raise ValueError("额外轮需要本次成功的官方额度读取")
    limits = snapshot.get("rateLimits", {})
    weekly = [x for x in [limits.get("primary"), limits.get("secondary")]
              if isinstance(x, dict) and x.get("windowDurationMins") == 10080]
    if len(weekly) != 1 or limits.get("limitId") != "codex":
        raise ValueError("额外轮缺少唯一官方Codex周窗口")
    reset = weekly[0].get("resetsAt")
    if isinstance(reset, bool) or not isinstance(reset, int) or reset <= 0:
        raise ValueError("额外轮必须取得有效官方resetsAt秒时间戳")
    checked = parse_time(snapshot["checked_at"]).timestamp()
    if not (reset - 14400 <= now.timestamp() < reset and reset - 14400 <= checked < reset):
        raise ValueError("额外轮仅限官方reset前四小时，过reset立即失效")
    return {"cycle_id": f"codex:10080:{reset}", "resets_at": reset,
            "window_duration_mins": 10080}


def extra_registry_path(root):
    return Path(root) / "data/reviews/earnings-extra-rounds.json"


def load_extra_run(root, run_id):
    if not run_id:
        raise ValueError("额外模式缺少原run_id，不自动新开一轮")
    path = extra_registry_path(root)
    records = read(path).get("cycles", {}) if path.exists() else {}
    matches = [r for r in records.values() if r.get("run_id") == run_id]
    if len(matches) != 1:
        raise ValueError("未找到唯一已登记额外轮")
    return matches[0]


def start_extra_round(root, snapshot, now):
    """Persist the single claim before any work; same-cycle retries must resume it."""
    import uuid

    cycle = extra_cycle(snapshot, now)
    record = {**cycle, "mode": "pre-reset-extra", "run_id": uuid.uuid4().hex,
              "state": "active", "started_at": stamp(now)}
    quota_gate(snapshot, now, mode="pre-reset-extra", extra_run=record)
    with run_lock(Path(root)):
        if ((Path(root) / "data/reviews/earnings-publication.lock.json").exists() or
                any((Path(root) / "data/reviews/earnings-research-slots").glob("*.lock.json"))):
            raise RuntimeError("已有公司槽/发布锁；不得新开额外轮")
        path = extra_registry_path(root)
        registry = read(path) if path.exists() else {"schema_version": 1, "cycles": {}}
        if cycle["cycle_id"] in registry["cycles"]:
            raise ValueError("本官方周周期额外轮已登记，不得重复；仅可续接原active run_id")
        registry["cycles"][cycle["cycle_id"]] = record
        atomic_json(path, registry)
    return record


def finish_extra_round(root, run_id, now, reason):
    """Safety closeout needs no quota; closing never releases the once-per-cycle claim."""
    if reason not in {"completed", "blocked", "quota_exhausted", "reset_elapsed", "read_failed"}:
        raise ValueError("额外轮收尾原因无效")
    with run_lock(Path(root)):
        record = load_extra_run(root, run_id)
        path = extra_registry_path(root)
        registry = read(path)
        current = registry["cycles"][record["cycle_id"]]
        if current.get("state") != "active":
            raise ValueError("额外轮已结束，不可重新激活")
        current.update(state="closed", finished_at=stamp(now), stop_reason=reason)
        atomic_json(path, registry)
    return current


@contextmanager
def run_lock(root):
    """操作系统锁随进程终止释放，不凭旧锁文件存在判定正在运行。"""
    path = root / "data/reviews/.earnings-discovery.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("另一披露发现进程正在写入；本次停止") from exc
        try:
            if (root / "data/reviews/earnings-update-active.lock.json").exists():
                raise RuntimeError("已有同项目报告更新运行锁；本次停止，勿自动清锁")
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


class Discovery:
    def __init__(self, root, now=None, *, quota_mode="normal", extra_run_id=None):
        self.root = Path(root).resolve()
        self.now = now or datetime.now(timezone.utc)
        self.day = self.now.astimezone(BEIJING).date().isoformat()
        self.directory = self.root / "data/reviews/earnings-discovery"
        self.path = self.directory / (self.day + ".json")
        self.queue_path = self.root / "data/reviews/earnings-update-queue.json"
        self.quota_mode = quota_mode
        self.extra_run_id = extra_run_id

    def check_quota(self, snapshot):
        if self.quota_mode == "normal" and self.extra_run_id is not None:
            raise ValueError("普通模式不得携带额外run_id")
        run = load_extra_run(self.root, self.extra_run_id) if self.quota_mode == "pre-reset-extra" else None
        return quota_gate(snapshot, self.now, mode=self.quota_mode, extra_run=run)

    def historical(self):
        previous = {}
        for path in sorted(self.directory.glob("????-??-??.json"), reverse=True):
            if path.stem >= self.day:
                continue
            for code, item in read(path).get("companies", {}).items():
                if code not in previous and item.get("last_verified_at"):
                    previous[code] = {"last_verified_at": item["last_verified_at"],
                                      "previous_report": item.get("latest_report") or item.get("previous_report")}
        return previous

    def reconcile(self):
        pool, sources = load_pool(self.root)
        data = read(self.path) if self.path.exists() else {
            "schema_version": 1, "date": self.day, "timezone": "Asia/Shanghai",
            "mode": "daily_full_active_pool", "created_at": stamp(self.now),
            "companies": {}, "removed_from_pool": {},
        }
        previous = self.historical() if not self.path.exists() else {}
        for code in list(data["companies"]):
            if code not in pool:
                data["removed_from_pool"][code] = data["companies"].pop(code)
        for code, identity in pool.items():
            if code not in data["companies"]:
                data["companies"][code] = {**identity, "status": "unchecked", "checked_at": None,
                    "last_verified_at": previous.get(code, {}).get("last_verified_at"),
                    "previous_report": previous.get(code, {}).get("previous_report"),
                    "latest_report": None, "official_sources": [], "failure": None, "attempts": []}
            else:
                item = data["companies"][code]
                item.update(identity)
        data["pool_sources"] = sources
        data["updated_at"] = stamp(self.now)
        return data

    @staticmethod
    def coverage(data):
        counts = {m: {"total": 0, "verified": 0, "failed": 0, "unchecked": 0} for m in ("CN", "HK", "US")}
        for item in data["companies"].values():
            group = counts[item["market"]]
            group["total"] += 1
            group["verified" if item["status"] in SUCCESS else item["status"]] += 1
        total = sum(x["total"] for x in counts.values())
        verified = sum(x["verified"] for x in counts.values())
        return {"date": data["date"], "by_market": counts, "total": total,
                "verified": verified, "complete": total > 0 and total == verified,
                "failed": [x["code"] for x in data["companies"].values() if x["status"] == "failed"],
                "unchecked": [x["code"] for x in data["companies"].values() if x["status"] == "unchecked"],
                "failure_reasons": {x["code"]: x["failure"] for x in data["companies"].values() if x["status"] == "failed"},
                "unchecked_reason": "尚未取得本日官方核验证据",
                "failed_attempts": {x["code"]: x["last_failed_attempt"]["failure"] for x in data["companies"].values() if x.get("last_failed_attempt")}}

    def save(self, data):
        data["coverage"] = self.coverage(data)
        atomic_json(self.path, data)

    def plan(self, quota):
        self.check_quota(quota)
        with run_lock(self.root):
            data = self.reconcile()
            self.save(data)
            self.enqueue(data)
            # 一次返回全部未完成项，不设置跨日批量或市场轮转游标。
            outstanding = [x for x in data["companies"].values() if x["status"] not in SUCCESS]
            return {"manifest": str(self.path), "coverage": data["coverage"], "checks_required": outstanding}

    def validate_source(self, source, code, company_market):
        if not isinstance(source, dict) or source.get("company_code") != code:
            raise ValueError("来源必须绑定正在核验的证券代码")
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("只接受无凭据的公开HTTPS官方原件/目录URL")
        if any(re.search(r"token|secret|password|credential|api.?key|authorization|signature", k, re.I) for k, _ in parse_qsl(parsed.query)):
            raise ValueError("官方来源URL不得包含凭据参数")
        authority = source.get("authority")
        if authority in {"regulator", "exchange"}:
            if not any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in AUTHORITIES[company_market]):
                raise ValueError("监管/交易所来源与市场不匹配")
        elif authority == "issuer":
            if not str(source.get("authority_basis", "")).strip():
                raise ValueError("公司IR来源须说明官方身份核验依据")
        else:
            raise ValueError("来源不是官方监管、交易所或公司IR")
        if not str(source.get("locator", "")).strip():
            raise ValueError("缺少发行人身份、目录覆盖范围和期次的原件定位")
        path = (self.root / str(source.get("evidence_path", ""))).resolve()
        evidence_root = (self.directory / "evidence" / self.day).resolve()
        if evidence_root not in path.parents or path.suffix.lower() not in {".json", ".html", ".htm", ".pdf", ".txt", ".md"}:
            raise ValueError("证据须归档在本日发现证据目录内，不能读取凭据或目录外文件")
        if not path.is_file() or digest(path) != source.get("sha256"):
            raise ValueError("原件/核验摘录不存在或SHA256不匹配")

    def validate_observation(self, observation, item):
        code = item["code"]
        if observation.get("code") != code or observation.get("status") not in RESULTS:
            raise ValueError("无效的逐公司结果")
        checked = parse_time(observation["checked_at"])
        if checked.astimezone(BEIJING).date().isoformat() != self.day or checked > self.now + timedelta(minutes=5):
            raise ValueError("非当日或未来核验不能计入当日覆盖")
        if observation["status"] == "failed":
            if not str(observation.get("failure", "")).strip():
                raise ValueError("失败须给出具体原因；不得伪称无新财报")
            return
        if observation.get("failure"):
            raise ValueError("成功结果不能同时包含核验失败原因")
        sources = observation.get("official_sources", [])
        if not sources or observation.get("method") not in {"official_document_read", "official_incremental_check"}:
            raise ValueError("成功必须实际核验官方原件/完整目录或有锚点的增量来源")
        for source in sources:
            self.validate_source(source, code, item["market"])
        if observation["method"] == "official_incremental_check":
            previous = item.get("last_verified_at")
            if not previous or observation.get("since") != previous or not (item.get("latest_report") or item.get("previous_report")) or parse_time(previous) > checked:
                raise ValueError("无真实历史成功锚点，不能用空增量推断最新期次")
        report = observation.get("latest_report")
        if not isinstance(report, dict) or not all(report.get(k) for k in ["period", "period_end", "disclosure_date", "official_url"]):
            raise ValueError("成功须记录已核最新财报期次、期末、披露日及官方原件")
        for field in ["period_end", "disclosure_date"]:
            if datetime.strptime(report[field], "%Y-%m-%d").date().isoformat() != report[field]:
                raise ValueError("财报日期须为YYYY-MM-DD")
            if report[field] > self.day:
                raise ValueError("未来财报不能作为已披露结果")
        if report["official_url"] not in [s["url"] for s in sources]:
            anchor = item.get("latest_report") or item.get("previous_report")
            if observation["method"] != "official_incremental_check" or report != anchor:
                raise ValueError("最新财报原件没有纳入已核官方来源，且不等于真实历史锚点")
        baseline = item.get("incorporated_period")
        same = baseline is not None and period_key(baseline) == period_key(report["period"])
        if observation["status"] == "verified_no_update" and not same:
            raise ValueError("最新期次未与已纳入期次匹配；不得直接宣称无需更新")
        if observation["status"] == "verified_new_report":
            if same and not observation.get("revision_id"):
                raise ValueError("同一期次只有已核修订披露才可再次入队")
            a, b = period_key(baseline), period_key(report["period"])
            if baseline and a[0] == b[0] and a[0] != "literal" and b[1:] < a[1:]:
                raise ValueError("旧期次不能作为新披露")
            if not str(observation.get("comparison_basis", "")).strip():
                raise ValueError("新财报须说明与当前已纳入期次的比较依据")

    def record(self, observations, quota):
        self.check_quota(quota)
        with run_lock(self.root):
            data = self.reconcile()
            if not isinstance(observations, list) or not observations:
                raise ValueError("输入应为非空逐公司结果数组")
            seen = set()
            # 全批先验证，错误不会部分覆盖当日记录。
            for observation in observations:
                code = observation.get("code")
                if code in seen or code not in data["companies"]:
                    raise ValueError("重复代码或代码不在三有效池")
                seen.add(code)
                self.validate_observation(observation, data["companies"][code])
                old = data["companies"][code]
                if old.get("checked_at") and parse_time(observation["checked_at"]) < parse_time(old["checked_at"]):
                    raise ValueError("不能用较旧检查覆盖较新检查")
            for observation in observations:
                item = data["companies"][observation["code"]]
                item["attempts"].append(copy.deepcopy(observation))
                if item["status"] in SUCCESS and observation["status"] == "failed":
                    item["last_failed_attempt"] = copy.deepcopy(observation)
                    continue
                item.update({k: copy.deepcopy(observation.get(k)) for k in
                             ["status", "checked_at", "official_sources", "latest_report", "failure", "method", "comparison_basis", "revision_id"]})
                if item["status"] in SUCCESS:
                    item["last_verified_at"] = item["checked_at"]
                item["recorded_at"] = stamp(self.now)
            self.save(data)
            additions = self.enqueue(data)
            return {"manifest": str(self.path), "coverage": data["coverage"], "queued_new_entries": additions}

    @staticmethod
    def same_disclosure(entry, item):
        report = item["latest_report"]
        if entry.get("code") != item["code"]:
            return False
        revision = item.get("revision_id")
        if revision:
            return entry.get("revision_id") == revision
        return (entry.get("new_report_period_end") == report["period_end"] or
                period_key(entry.get("new_report_period", "")) == period_key(report["period"]))

    def enqueue(self, data):
        queue_hash = digest(self.queue_path)
        queue = read(self.queue_path)
        additions = []
        for item in data["companies"].values():
            if item["status"] != "verified_new_report":
                continue
            if any(self.same_disclosure(e, item) for e in queue["entries"]):
                continue
            report = item["latest_report"]
            entry = {"id": item["code"] + "|" + report["period"] + ("|" + item["revision_id"] if item.get("revision_id") else ""),
                "name": item["name"], "code": item["code"], "watchlist_path": item["watchlist_path"],
                "last_earnings_incorporated": item["incorporated_period"], "new_report_period": report["period"],
                "new_report_period_end": report["period_end"], "disclosure_date": report["disclosure_date"],
                "official_sources": [s["url"] for s in item["official_sources"]],
                "discovered_at": item["checked_at"], "status": "pending", "stage": "discovered",
                "attempt_count": 0, "discovery_manifest": str(self.path.relative_to(self.root)).replace("\\", "/"),
                "revision_id": item.get("revision_id")}
            queue["entries"].append(entry)
            additions.append(entry["id"])
        policy = queue.setdefault("policy", {})
        policy.update(discovery_before_update_selection=True, discovery_scope="daily_full_active_pool",
                      discovery_independent_of_queue=True, queue_before_full_scan=False,
                      max_company_updates_per_run=None, max_company_updates_per_beijing_day=None,
                      weekly_remaining_must_exceed_percent=20)
        queue["daily_discovery"] = {"manifest": str(self.path.relative_to(self.root)).replace("\\", "/"),
                                    "coverage": data["coverage"], "updated_at": stamp(self.now)}
        queue["next_action"] = "每日先全三有效池核验并留证（队列非空亦执行）；失败/未查如实报告，额度严格超过20%时持续按队列优先级逐家公司串行研究与验收，无每日数量上限。"
        if digest(self.queue_path) != queue_hash or (self.root / "data/reviews/earnings-update-active.lock.json").exists():
            raise RuntimeError("队列被其他进程修改或更新任务启动；当日台账已保存，重跑plan恢复去重入队")
        atomic_json(self.queue_path, queue)
        return additions

    def status(self):
        # 只读状态使用实时名单；新加入公司会作为未查，不能沿用旧总数宣称完成。
        data = self.reconcile()
        return {"manifest_exists": self.path.exists(), "coverage": self.coverage(data)}

    def select(self, quota):
        self.check_quota(quota)
        if not self.path.exists():
            return {"candidate": None, "reason": "今日尚未建立全池核验计划"}
        data = self.reconcile()
        coverage = self.coverage(data)
        queue = read(self.queue_path)
        if (self.root / "data/reviews/earnings-update-active.lock.json").exists() or any(e.get("status") == "in_progress" for e in queue["entries"]):
            return {"candidate": None, "reason": "已有更新任务进行中", "coverage": coverage}
        if coverage["unchecked"]:
            return {"candidate": None, "reason": "尚有未查公司；先完成发现或如实记录失败，不能因队列非空跳过", "coverage": coverage}
        # Completed-day fields remain audit history; quota and queue govern continuation.
        verified = data["companies"]
        candidates = [e for e in queue["entries"] if e.get("status") == "pending" and
                      e.get("code") in verified and verified[e["code"]]["status"] == "verified_new_report" and
                      (verified[e["code"]].get("revision_id") or period_key(verified[e["code"]]["incorporated_period"]) != period_key(verified[e["code"]]["latest_report"]["period"])) and
                      self.same_disclosure(e, verified[e["code"]])]
        candidates = prioritize_candidates(candidates, queue.get("user_priority_order", []))
        return {"candidate": candidates[0] if candidates else None,
                "reason": "只读建议；启动前复查官方期次、最新公司页与独审流程，并再次查额度",
                "coverage": coverage, "coverage_warning": not coverage["complete"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "record", "status", "select", "check-quota", "start-extra", "finish-extra"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--quota", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--quota-mode", choices=["normal", "pre-reset-extra"], default="normal")
    parser.add_argument("--extra-run-id")
    parser.add_argument("--stop-reason", choices=["completed", "blocked", "quota_exhausted", "reset_elapsed", "read_failed"])
    args = parser.parse_args()
    discovery = Discovery(args.root, quota_mode=args.quota_mode, extra_run_id=args.extra_run_id)
    if args.command == "status":
        result = discovery.status()
    elif args.command == "finish-extra":
        if not args.extra_run_id or not args.stop_reason:
            parser.error("finish-extra需要原--extra-run-id及--stop-reason")
        result = finish_extra_round(args.root, args.extra_run_id, discovery.now, args.stop_reason)
    else:
        if not args.quota:
            parser.error("此操作需要新鲜官方--quota快照")
        quota = read(args.quota)
        if args.command == "start-extra":
            if args.quota_mode != "pre-reset-extra" or args.extra_run_id:
                parser.error("start-extra须显式--quota-mode pre-reset-extra，不接受已有run_id；恢复用check-quota")
            result = start_extra_round(args.root, quota, discovery.now)
        elif args.command == "check-quota":
            result = discovery.check_quota(quota)
        elif args.command == "record":
            if not args.input:
                parser.error("record需要--input逐公司结果JSON数组")
            result = discovery.record(read(args.input), quota)
        elif args.command == "select":
            result = discovery.select(quota)
        else:
            result = discovery.plan(quota)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, KeyError, OSError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
