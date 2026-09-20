"""装配三件套交付物；研究判断由独立复核与裁决负责，本工具不写Watchlist。"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

try:
    from . import triplet_workpaper as wp
except ImportError:
    import triplet_workpaper as wp

KINDS = ("deep", "management", "valuation")
TOKEN = re.compile(r"\{\{(ref|fact|table|score):([^{}]+)\}\}|\{\{decision\}\}")


def publication_errors(texts):
    """发布态只拦截流程残留，不把真实研究未知误判为未验收。"""
    errors = []
    patterns = (r"类型\s*[:：].*草稿", r"例外修复稿", r"handoff\s+--stage",
                r"(?:本稿|本报告|交付装配)[^\n。]*?(?:尚待|仍待)[^\n。]*?(?:验收|复查|检查)",
                r"机械校验端点", r"机械(?:校验|表)[^\n。；]*下端点", r"标记引用核验")
    for name, text in texts.items():
        for n, line in enumerate(text.splitlines(), 1):
            if any(re.search(pattern, line) for pattern in patterns):
                errors.append(f"{name}:{n}残留发布流程文字：{line}")
    return errors


def interval_display_errors(texts, data):
    errors = []
    for sheet in data["scores"].values():
        for row in sheet["items"]:
            if row.get("score") is None:
                pattern = re.escape(row["id"]) + r"\s*(?:为|得分为|评分为)\s*\d+(?:\.\d+)?\s*分"
                for kind, text in texts.items():
                    if re.search(pattern, text):
                        errors.append(f"{kind}将区间项{row['id']}表述为点值")
    return errors


def require_release_approval(authorization):
    wp.require(authorization.get("publish_allowed") is True and
               authorization.get("delivery_state") == "approved" and
               authorization.get("research_state") == "approved", "未获研究及发布批准")
    for issue in authorization["issues"]:
        wp.require(issue["status"] == "closed", "仍有未关闭问题")
        conditions = issue.get("acceptance", [])
        if isinstance(conditions, list):
            for condition in conditions:
                if isinstance(condition, dict) and "status" in condition:
                    wp.require(condition["status"] in ("closed", "pass", "passed"), "仍有未通过验收条件")
    wp.require(authorization.get("release_review_refs"), "缺最终发布复核记录")


def check_release(manifest_path, authorization_path, root):
    """核验实际送审版本与裁决绑定；字段存在不能替代独立语义复核。"""
    verify(manifest_path, root)
    manifest = wp.read(manifest_path)
    authorization = wp.read(authorization_path)
    require_release_approval(authorization)
    wp.require(authorization.get("approved_manifest_sha256") == digest(Path(manifest_path).read_bytes()), "获批manifest不一致")
    wp.require(authorization.get("approved_report_sha256") == manifest["reports"], "获批报告不一致")
    for key in ("decision", "research_state", "score_bounds"):
        wp.require(authorization[key] == manifest[key], "发布裁决与装配判断不一致：" + key)
    texts = {name: (Path(manifest_path).parent / name).read_text(encoding="utf-8") for name in manifest["reports"]}
    errors = publication_errors(texts) + interval_display_errors(texts, wp.read(wp.local(root, manifest["frozen_bundle"]["workpaper"])))
    wp.require(not errors, "；".join(errors))
    return manifest, authorization


def archive_release(config, root, output):
    """只生成可携带的验收包；不发布报告、不覆盖旧包、不改变投资判断。"""
    manifest_path = wp.local(root, config["manifest"])
    auth_path = wp.local(root, config["authorization"])
    manifest, authorization = check_release(manifest_path, auth_path, root)
    wp.require(set(config["reports"]) == set(manifest["reports"]), "正式报告映射不完整")
    files = dict(manifest["inputs"])
    files[config["manifest"]] = digest(manifest_path.read_bytes())
    files[config["authorization"]] = digest(auth_path.read_bytes())
    # 将复核引用递归冻结，避免只保存声称通过的裁决而丢失实际验收。
    pending = [authorization, *[wp.read(wp.local(root, p)) for p in files if p.endswith('.json')]]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("refs") and isinstance(value, list):
                    for ref in value:
                        if not isinstance(ref, str) or not ref.startswith("data/"):
                            continue
                        path = ref.split("#", 1)[0]
                        raw = wp.local(root, path).read_bytes()
                        if path not in files:
                            files[path] = digest(raw)
                            if path.endswith('.json'):
                                pending.append(json.loads(raw))
                elif isinstance(value, (dict, list)):
                    pending.append(value)
        elif isinstance(node, list):
            pending.extend(x for x in node if isinstance(x, (dict, list)))
    for name, path in config["reports"].items():
        wp.require(digest(wp.local(root, path).read_bytes()) == manifest["reports"][name], "正式报告与获批稿不一致：" + path)
    target = wp.local(root, output)
    wp.require(not target.exists(), "验收包目录必须全新")
    # 先完整读取，缺引用不得留下看似完整的验收包。
    payloads = {p: wp.local(root, p).read_bytes() for p in files}
    target.mkdir(parents=True)
    entries = {}
    for i, (path, raw) in enumerate(sorted(payloads.items())):
        name = f"inputs/{i:03d}-{Path(path).name}"
        destination = target / name
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(raw)
        entries[path] = {"archive": name, "sha256": files[path]}
    receipt = {"schema_version": 1, "manifest": config["manifest"], "authorization": config["authorization"],
               "files": entries, "reports": {path: manifest["reports"][name] for name, path in config["reports"].items()},
               "scope": "发布版本与验收证据归档；不授权Watchlist操作"}
    save_new(target / "release.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return verify_release(target / "release.json", root)


def verify_release(receipt_path, root):
    """仅依赖正式报告与保留的验收包，临时构建目录可不存在。"""
    receipt = wp.read(receipt_path)
    archive = Path(receipt_path).parent
    retained = [Path(receipt_path).resolve()]
    for entry in receipt["files"].values():
        path = wp.local(archive, entry["archive"])
        wp.require(digest(path.read_bytes()) == entry["sha256"], "归档依据哈希不符：" + entry["archive"])
        retained.append(path)
    manifest = wp.read(wp.local(archive, receipt["files"][receipt["manifest"]]["archive"]))
    auth = wp.read(wp.local(archive, receipt["files"][receipt["authorization"]]["archive"]))
    require_release_approval(auth)
    for key in ("decision", "research_state", "score_bounds"):
        wp.require(auth[key] == manifest[key], "归档裁决与装配判断不一致：" + key)
    for ref in auth["release_review_refs"]:
        wp.require(ref.split("#", 1)[0] in receipt["files"], "归档缺最终发布复核文件")
    wp.require(auth["approved_manifest_sha256"] == receipt["files"][receipt["manifest"]]["sha256"], "归档manifest并非获批版本")
    wp.require(auth["approved_report_sha256"] == manifest["reports"], "归档报告并非获批版本")
    wp.require(sorted(receipt["reports"].values()) == sorted(manifest["reports"].values()), "归档缺正式报告或版本错配")
    for original, expected in manifest["inputs"].items():
        wp.require(receipt["files"][original]["sha256"] == expected, "归档源依赖错配：" + original)
    texts = {}
    for relative, expected in receipt["reports"].items():
        path = wp.local(root, relative)
        wp.require(digest(path.read_bytes()) == expected, "正式报告已变化：" + relative)
        retained.append(path)
        texts[relative] = path.read_text(encoding="utf-8")
    workpaper_entry = receipt["files"][manifest["frozen_bundle"]["workpaper"]]
    errors = publication_errors(texts) + interval_display_errors(texts, wp.read(wp.local(archive, workpaper_entry["archive"])))
    wp.require(not errors, "；".join(errors))
    if (Path(root) / ".git").exists():
        paths = [p.relative_to(Path(root).resolve()).as_posix() for p in retained]
        result = subprocess.run(["git", "check-ignore", "--no-index", "--stdin"], input="\n".join(paths) + "\n",
                                cwd=root, text=True, capture_output=True, encoding="utf-8")
        wp.require(result.returncode == 1, "必要归档被Git忽略或检查失败：" + result.stdout + result.stderr)
    return {"status": "release_verified", "reports": len(texts), "archived_inputs": len(receipt["files"])}


def save_new(path, text):
    # 固定换行使生成字节与清单一致，Windows也不隐式转换为CRLF。
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else
                          json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def evidence_index(root, paths):
    """仅索引声明，不将事实记录里的source_id引用误认成新来源。"""
    index = {}

    def walk(value, path, pointer):
        if isinstance(value, dict):
            keys = [k for k in ("fact_id", "calculation_id", "id") if isinstance(value.get(k), str)]
            if not keys and isinstance(value.get("source_id"), str) and any(k in value for k in ("url", "path", "file")):
                keys = ["source_id"]
            for key in keys:
                identifier = value[key]
                wp.require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", identifier), "证据声明必须是单个完整ID：" + identifier)
                if identifier in index:
                    raise ValueError(f"证据ID重复：{identifier}，须显式选择有效版本")
                index[identifier] = {"path": path, "pointer": pointer, "record": value}
            for key, child in value.items():
                walk(child, path, pointer + "/" + str(key))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, path, pointer + "/" + str(i))

    for path in paths:
        walk(wp.read(wp.local(root, path)), path, "")
    return index


def referenced_ids(text, prefixes):
    """历史材料按明确命名空间扫描；新源稿推荐ref标记，禁用压缩ID写法。"""
    result = set(re.findall(r"\{\{ref:([^{}]+)\}\}", text))
    for prefix in prefixes:
        result.update(re.findall(r"(?<![\w-])" + re.escape(prefix) + r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", text))
    return result


def scan_references(texts, index, prefixes):
    errors, uses = [], {}
    for name, text in texts.items():
        for identifier in sorted(referenced_ids(text, prefixes)):
            uses.setdefault(identifier, []).append(name)
            if identifier not in index:
                errors.append(f"{name}引用不存在的证据ID：{identifier}")
        if re.search(r"[A-Z][A-Z0-9-]+-\d+(?:/\d+)+", text):
            errors.append(f"{name}含压缩证据ID，请逐个完整列出")
    return errors, uses


def score_ranges(data):
    """区间直接从分项汇总，绝不把下端点写成实得分。"""
    limits = wp.scoring_rules()
    result = {}
    for name, caps in zip(("company", "management"), limits):
        sheet = data["scores"][name]
        lows, highs = [], []
        for row in sheet["items"]:
            if row.get("score") is None:
                bound = row["bounds"]
                wp.require(len(bound) == 2 and wp.number(bound[0]) <= wp.number(bound[1]) and
                           row.get("bounds_reason"), "评分区间缺有据上下界")
                low, high = bound
            else:
                wp.require("bounds" not in row, "同一分项不能同时提供点值和区间")
                low = high = wp.number(row["score"])
            lows.append(low)
            highs.append(high)
        for values in (lows, highs):
            sample = copy.deepcopy(sheet)
            for row, value in zip(sample["items"], values):
                row["score"] = value
            sample["total"] = sum(values)
            wp.score(sample, caps, name)
            if name == "company":
                for group in "ABCDEF":
                    wp.require(sum(r["score"] for r in sample["items"] if r["id"].startswith(group)) <=
                               sum(v for k, v in caps.items() if k.startswith(group)), "区间超出维度满分")
                d2 = next(r for r in sample["items"] if r["id"] == "D2")
                wp.require(type(d2.get("original_statement_found")) is bool and type(d2.get("strategy_drift")) is bool,
                           "D2缺原话/漂移标记")
                if not d2["original_statement_found"]:
                    wp.require(d2["score"] <= (3 if d2["strategy_drift"] else 4), "D2区间违反分层上限")
        bounds = [sum(lows), sum(highs)]
        if bounds[0] == bounds[1]:
            wp.close(sheet["total"], bounds[0], name + "总分")
        else:
            wp.require(sheet.get("total") is None, "区间评分不得将端点作为total")
            wp.require(sheet.get("bounds") == bounds, "总分区间与所有分项汇总不一致")
        result[name] = bounds
    result["combined"] = [result["company"][i] + result["management"][i] for i in (0, 1)]
    return result


def display(bounds):
    if bounds[0] == bounds[1]:
        return wp.score_display(bounds[0])
    # 外包络显示向外取整，避免舍入后缩小范围；门槛仍用原始端点。
    import math
    return f"{math.floor(bounds[0])}–{math.ceil(bounds[1])}"


def validate_decision(ledger):
    wp.require(ledger["decision"] in ("eligible", "reject", "defer"), "决策值未知")
    wp.require(ledger["research_state"] in ("approved", "pending"), "研究状态未知")
    wp.require(ledger.get("basis") and isinstance(ledger.get("review_refs"), list), "决策缺依据或复核清单")
    seen = set()
    for issue in ledger["issues"]:
        wp.require(issue["id"] not in seen, "处置问题ID重复")
        seen.add(issue["id"])
        wp.require(issue["lane"] in ("research", "delivery") and issue["status"] in ("open", "closed"), "问题分流或状态未知")
        wp.require(issue.get("reason") and issue.get("acceptance"), "问题缺影响说明或验收条件")
        if issue["lane"] == "delivery":
            wp.require(issue.get("classified_by") == "adjudicator" and issue.get("no_decision_impact") is True,
                       "交付问题须由裁决确认不影响判断，不能自动降级")
        if issue["status"] == "closed":
            wp.require(issue.get("verification_refs"), "关闭问题缺验收记录")
    if ledger["research_state"] == "approved":
        wp.require(ledger.get("research_status") != "execution_incomplete", "执行未完成不能声称完整研究获批；评分批准单列score_state")
        wp.require(len(set(ledger["review_refs"])) >= 2, "研究获批缺两路独立复核记录路径")
        wp.require(not any(i["lane"] == "research" and i["status"] == "open" for i in ledger["issues"]),
                   "有未关闭研究问题不能声称研究判断获批")


def assemble(bundle, root):
    """只读源数据，在内存中完成检查；失败不生成半成品。"""
    wp.require(bundle["schema_version"] == 1, "交付描述版本未知")
    wp.require(set(bundle["templates"]) == set(KINDS), "必须提供三份独立源稿")
    wp.require(bundle.get("id_prefixes") and all(isinstance(p, str) and p for p in bundle["id_prefixes"]),
               "必须显式列出需要扫描的证据ID命名空间")
    index = evidence_index(root, bundle["evidence"])
    data = wp.read(wp.local(root, bundle["workpaper"]))
    ledger = wp.read(wp.local(root, bundle["decision"]))
    validate_decision(ledger)
    for path in ledger["review_refs"]:
        wp.require(wp.local(root, path).is_file(), "复核记录不存在：" + path)
    bounds = score_ranges(data)
    interval = any(b[0] != b[1] for b in bounds.values())
    stopped = data["valuation"].get("status") == "stopped_quality_gate_after_full_research"
    deferred = data["valuation"].get("status") == "deferred"
    unpriced = stopped or deferred
    approved = ledger["research_state"] == "approved"
    if interval:
        wp.require(((stopped and ledger["decision"] == "reject") or
                    (deferred and ledger["decision"] == "defer")) and
                   (not approved or ledger.get("bounds_approved") is True),
                   "区间须为否决停止定价或暂缓定价；获批后须有区间批准，不能伪造点值估值")
        wp.require(ledger.get("score_bounds") == bounds, "裁决评分区间与分项外包络不一致")
        wp.require(data["valuation"].get("models") == [] and all(k in data["valuation"] and data["valuation"][k] is None
                   for k in ("target_price", "certainty", "buy_price")), "停止定价须空模型和显式null字段")
        wp.validate_bridges(data)
    else:
        checked = wp.check(data, reports=False)
        wp.require(not checked["errors"], "底稿：" + "；".join(checked["errors"]))
    wp.require(not stopped or ledger["decision"] == "reject", "停止定价必须有否决决策")
    if deferred:
        wp.require(ledger["decision"] == "defer" and data["valuation"].get("reason"), "暂缓定价须有defer决策及具体原因")
        wp.require(ledger.get("quality_stop_approved") is not True, "暂缓不得冒充质量否决")
    if stopped and approved:
        wp.require(ledger.get("quality_stop_approved") is True, "停止定价缺裁决批准")
    if ledger["research_state"] == "approved":
        wp.require(ledger.get("score_bounds") == bounds, "获批评分与底稿不一致")
    blocks = {}
    for kind in ("company", "management"):
        lines = ["| 分项 | 原始分或区间 | 依据 | 来源 |", "|---|---:|---|---|"]
        for row in data["scores"][kind]["items"]:
            value = row["score"] if row.get("score") is not None else f"[{row['bounds'][0]}, {row['bounds'][1]}]"
            reason = row["reason"].replace("|", "\\|").replace("\n", "<br>")
            refs = "；".join(row["evidence_refs"])
            lines.append(f"| {row['id']} | {value} | {reason} | {refs} |")
        blocks[kind] = "\n".join(lines)
    if not unpriced:
        rendered = wp.render(data)
        for match in re.finditer(r"<!-- triplet:table:([^>]+) -->(.*?)<!-- /triplet:table:\1 -->", rendered, re.S):
            if match[1] not in blocks:
                blocks[match[1]] = match[2].strip()
    decision_text = f"决策：{ledger['decision']}；研究判断：{ledger['research_state']}。\n公司：{display(bounds['company'])}；管理层：{display(bounds['management'])}；合计：{display(bounds['combined'])}。"
    if not approved:
        decision_text = "候选判断，仅供独立复核，尚未获研究批准。\n" + decision_text
    decision_text += "\n" + ledger["basis"]
    if stopped:
        decision_text += "\n" + ("停止正式定价" if approved else "候选方案为停止正式定价") + "；目标价、确定性、买入价均为null，不代表零价值。"
    elif deferred:
        decision_text += "\n正式估值暂缓；目标价、确定性、买入价均为null，不代表零价值或质量否决。"
        decision_text += "\n估值缺口：" + data["valuation"]["reason"]
    else:
        v = data["valuation"]
        decision_text += f"\n目标价：{v['target_price']}；确定性：{v['certainty']}；机械买入价：{v['buy_price']}；币种：{v['currency']}。"
    facts = bundle.get("facts", {})
    for key, fact in facts.items():
        wp.require(fact.get("text") and fact.get("refs"), f"共用事实{key}缺正文或依据")
        wp.require(all(identifier in index for identifier in fact["refs"]), f"共用事实{key}含未知证据ID")
    texts, token_refs, fact_uses = {}, {}, {}
    for kind, relative in bundle["templates"].items():
        source = wp.local(root, relative).read_text(encoding="utf-8-sig")
        token_refs[kind] = set()
        wp.require("{{decision}}" in source, f"{kind}缺统一结论占位")
        required_tables = ["company"] if kind == "deep" else ["management"] if kind == "management" else ([] if unpriced else ["model-" + m["id"] for m in data["valuation"]["models"]] + ["weighted"])
        for key in required_tables:
            wp.require("{{table:" + key + "}}" in source, f"{kind}缺生成表{key}")

        def replace(match):
            if match[0] == "{{decision}}":
                return decision_text
            token, key = match[1], match[2]
            if token == "ref":
                wp.require(key in index, f"未知证据ID：{key}")
                token_refs[kind].add(key)
                return f"[{key}]"
            if token == "fact":
                fact = facts[key]
                token_refs[kind].update(fact["refs"])
                fact_uses.setdefault(key, []).append(kind)
                return fact["text"] + " [" + "；".join(fact["refs"]) + "]"
            if token == "score":
                return display(bounds[key])
            return "<!-- triplet:table:" + key + " -->\n" + blocks[key] + "\n<!-- /triplet:table:" + key + " -->"

        text = TOKEN.sub(replace, source)
        wp.require(not re.search(r"\{\{.*?\}\}", text), "存在未解析标记或嵌套标记")
        texts[kind] = text
    checked_texts = {**texts, "workpaper": json.dumps(data, ensure_ascii=False)}
    errors, uses = scan_references(checked_texts, index, bundle.get("id_prefixes", []))
    for kind, identifiers in token_refs.items():
        for identifier in sorted(identifiers):
            if kind not in uses.setdefault(identifier, []):
                uses[identifier].append(kind)
    # 底稿分项必须使用完整ID，不能靠自由文本或附近可猜测的来源冒充引用闭合。
    for sheet in data["scores"].values():
        for row in sheet["items"]:
            for identifier in row["evidence_refs"]:
                if identifier not in index:
                    errors.append(f"评分{row['id']}引用未注册：{identifier}")
    for key, fact in facts.items():
        for old in fact.get("retired", []):
            wp.require(old and old not in fact["text"], "过期文字清单与当前事实冲突")
            for kind, text in texts.items():
                if old in text:
                    errors.append(f"{kind}残留过期事实{key}：{old}")
    errors += wp.report_integrity(texts)
    if bundle.get("publication_ready"):
        errors += publication_errors(texts)
        errors += interval_display_errors(texts, data)
    for kind, minimum in zip(KINDS, (150, 150, 100)):
        if len(texts[kind].splitlines()) < minimum:
            errors.append(f"{kind}少于{minimum}行")
    wp.require(not errors, "；".join(errors))
    # 每份报告携带本地证据记录及字段位置，脱离任务上下文仍可追溯。
    for kind, text in texts.items():
        identifiers = (referenced_ids(text, bundle.get("id_prefixes", [])) | token_refs[kind]) & index.keys()
        if identifiers:
            text += "\n\n## 生成的证据定位\n\n| ID | 记录文件 | 字段位置 |\n|---|---|---|\n"
            for identifier in sorted(identifiers):
                record = index[identifier]
                text += f"| {identifier} | [[{record['path']}]] | `{record['pointer']}` |\n"
            texts[kind] = text
    dependencies = {path: digest(wp.local(root, path).read_bytes()) for path in
                    [bundle["workpaper"], bundle["decision"], *bundle["evidence"], *bundle["templates"].values(), *ledger["review_refs"]]}
    return texts, {"schema_version": 1, "status": "assembled_for_review", "decision": ledger["decision"],
                   "research_state": ledger["research_state"], "delivery_state": "mechanically_checked",
                   "publish_allowed": False, "score_bounds": bounds,
                   "inputs": dependencies, "bundle_sha256": digest(bundle), "frozen_bundle": bundle,
                   "reports": {kind + ".md": digest(text.encode()) for kind, text in texts.items()},
                   "reference_uses": uses, "fact_uses": fact_uses,
                   "limitations": "仅装配及机械验证；发表仍须独立全文验收和裁决。未知不得转为实际零分。"}


def build(bundle, root, output, bundle_path=None):
    output = wp.local(root, output)
    wp.require(not output.exists(), "输出目录必须全新，不覆盖冻结材料")
    texts, manifest = assemble(bundle, root)
    if bundle_path is not None:
        path = wp.local(root, bundle_path)
        manifest["inputs"][path.relative_to(Path(root).resolve()).as_posix()] = digest(path.read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    for kind, text in texts.items():
        save_new(output / (kind + ".md"), text)
    save_new(output / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def verify(manifest_path, root):
    manifest = wp.read(manifest_path)
    wp.require(digest(manifest["frozen_bundle"]) == manifest["bundle_sha256"], "装配描述快照已变化")
    for path, expected in manifest["inputs"].items():
        wp.require(digest(wp.local(root, path).read_bytes()) == expected, f"源文件已变化：{path}")
    for path, expected in manifest["reports"].items():
        wp.require(digest(wp.local(Path(manifest_path).parent, path).read_bytes()) == expected, f"交付稿已被手改：{path}")
    return {"status": "version_verified", "publish_allowed": False}


def patch_templates(bundle, plan, root, output):
    """执行裁决确认的交付补丁；精确计数和旧稿哈希阻止模糊替换及覆盖历史。"""
    ledger = wp.read(wp.local(root, bundle["decision"]))
    validate_decision(ledger)
    issues = {issue["id"]: issue for issue in ledger["issues"]}
    paths = set(bundle["templates"].values())
    changed = {}
    for edit in plan["edits"]:
        path = edit["path"]
        wp.require(path in paths, "交付补丁仅允许修改源稿，不改证据或评分估值参数")
        issue = issues[edit["issue_id"]]
        wp.require(issue["lane"] == "delivery" and issue["no_decision_impact"] is True,
                   "未被裁决分流为交付问题，须研究复查")
        raw = wp.local(root, path).read_bytes()
        wp.require(digest(raw) == edit["before_sha256"], "补丁基线已变化")
        text = changed.get(path, raw.decode("utf-8-sig"))
        wp.require(edit["old"] and edit["old"] != edit["new"] and type(edit["count"]) is int and edit["count"] > 0,
                   "补丁缺精确新旧文本或正整数出现次数")
        wp.require(text.count(edit["old"]) == edit["count"], "补丁出现次数不符，禁止漏改或扩大替换")
        changed[path] = text.replace(edit["old"], edit["new"])
    wp.require(changed, "补丁为空")
    target = wp.local(root, output)
    wp.require(not target.exists(), "补丁输出目录必须全新")
    target.mkdir(parents=True, exist_ok=False)
    mapping = {}
    for i, (path, text) in enumerate(changed.items()):
        destination = target / f"source-{i}.md"
        save_new(destination, text)
        mapping[path] = destination.relative_to(Path(root).resolve()).as_posix()
    result = {"status": "patched_pending_delivery_verification", "mapping": mapping,
              "plan_sha256": digest(plan), "decision_sha256": digest(wp.local(root, bundle["decision"]).read_bytes()),
              "publish_allowed": False}
    save_new(target / "patch-result.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "check", "verify", "scan", "patch", "archive-release", "verify-release"))
    parser.add_argument("input")
    parser.add_argument("--root", type=Path, default=wp.ROOT)
    parser.add_argument("--output")
    parser.add_argument("--plan")
    args = parser.parse_args()
    if args.command == "verify-release":
        result = verify_release(args.input, args.root)
    elif args.command == "archive-release":
        wp.require(args.output, "archive-release缺--output")
        result = archive_release(wp.read(args.input), args.root, args.output)
    elif args.command == "verify":
        result = verify(args.input, args.root)
    else:
        bundle = wp.read(args.input)
        if args.command == "patch":
            wp.require(args.output and args.plan, "patch缺--plan或--output")
            result = patch_templates(bundle, wp.read(args.plan), args.root, args.output)
        elif args.command == "scan":
            index = evidence_index(args.root, bundle["evidence"])
            texts = {p: wp.local(args.root, p).read_text(encoding="utf-8-sig") for p in bundle["files"]}
            errors, uses = scan_references(texts, index, bundle["id_prefixes"])
            result = {"status": "failed" if errors else "references_resolved", "errors": errors, "reference_uses": uses}
        elif args.command == "build":
            wp.require(args.output, "build缺--output")
            result = build(bundle, args.root, args.output, args.input)
        else:
            result = assemble(bundle, args.root)[1]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result.get("status") == "failed")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
