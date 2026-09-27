"""评分取证计划、原文阅读包及局部修复；机械通过不代表研究批准。"""
import argparse
import copy
import json
import re
from pathlib import Path

try:
    from scripts import triplet_delivery as delivery
except ImportError:
    import triplet_delivery as delivery

wp = delivery.wp
CORE = ["deep-prebuy-skill/SKILL.md", "management-archive/SKILL.md"]
CHECKS = "management-archive/references/review-checks.md"
FIELDS = {"score", "reason", "rule_ref", "evidence_refs", "original_statement_found",
          "strategy_drift", "positive_precedent", "capex_check"}


def keys():
    company, management = wp.scoring_rules()
    return {(group, key) for group, rules in (("company", company), ("management", management)) for key in rules}


def plan_template():
    # 空问题有意不能通过验收，防止模板被误当成完成的取证计划。
    return {"schema_version": 1, "kind": "score_evidence_plan", "requirements": [
        {"id": group + ":" + key, "group": group, "item": key, "scope": "", "decisive": True}
        for group, key in sorted(keys())]}


def validate_plan(plan):
    rows = plan["requirements"]
    wp.require(plan.get("kind") == "score_evidence_plan", "取证计划类型错误")
    wp.require(len(rows) == len(keys()) and {(r["group"], r["item"]) for r in rows} == keys(),
               "取证计划须覆盖全部32个分项且不得重复")
    for row in rows:
        wp.require(row["id"] == row["group"] + ":" + row["item"], "计划ID与分项不一致")
        wp.require(isinstance(row["scope"], str) and row["scope"].strip() and type(row["decisive"]) is bool,
                   "取证问题为空或缺决定性分类")
    return rows


def packet(stage, root, extra=()):
    # 全文逐字复制，不另造压缩评分标准；已读的同哈希包无需再次加载。
    paths = CORE + [CHECKS] if stage == "score" else ["skills/valuation/SKILL.md"]
    paths = list(dict.fromkeys(paths + list(extra)))
    chunks, inputs = [], {}
    for name in paths:
        path = wp.local(root, name)
        raw = path.read_bytes()
        inputs[name] = delivery.digest(raw)
        chunks.append(f"<!-- 原文 {name} sha256={inputs[name]} -->\n" + raw.decode("utf-8-sig"))
    return {"stage": stage, "inputs": inputs, "text": "\n\n".join(chunks)}


def check(sheet, root, evidence):
    checked = wp.check(sheet, root=root, reports=False)
    errors, warnings, result = checked["errors"], checked["warnings"], checked["computed"]
    index = delivery.evidence_index(root, evidence)
    for group in ("company", "management"):
        for row in sheet["scores"][group]["items"]:
            refs = row["evidence_refs"] + row.get("capex_check", {}).get("evidence_refs", [])
            missing = [ref for ref in refs if ref not in index]
            if missing:
                errors.append(f"{group}/{row['id']}未注册引用：{missing}")
    for gap in sheet.get("evidence_gaps", []):
        missing = [ref for ref in gap.get("evidence_refs", []) if ref not in index]
        if missing:
            errors.append(f"证据缺口未注册引用：{missing}")
    return {"status": "failed" if errors else "mechanically_checked_pending_review",
            "errors": errors, "warnings": warnings, "scores": {k: result.get(k) for k in ("cScore", "mScore")},
            "inputs": {p: delivery.digest(wp.local(root, p).read_bytes()) for p in evidence}}


def score_gate(sheet, root):
    meta = wp.read(wp.local(root, "data/watchlist_meta.json"))
    c, m = (sheet["scores"][g]["total"] for g in ("company", "management"))
    for tier in ("S_STRATEGIC", "A_CORE", "B_GROWTH"):
        rule = meta["tier_definitions"][tier]["entry_criteria"][0]
        match = re.search(r"合计不低于(\d+).*两项均不低于(\d+)", rule)
        wp.require(match is not None, "门槛原文格式变化，须人工核对解析器")
        total, minimum = map(int, match.groups())
        if c + m >= total and min(c, m) >= minimum:
            return tier
    return "NONE"


def apply_delta(base, decision, delta, root, evidence):
    base_path, decision_path = wp.local(root, base), wp.local(root, decision)
    wp.require(delivery.digest(base_path.read_bytes()) == delta["base_sha256"], "底稿版本已变化")
    wp.require(delivery.digest(decision_path.read_bytes()) == delta["decision_sha256"], "裁决版本已变化")
    original = wp.read(base_path)
    ruling = wp.read(decision_path)
    # 裁决在唯一台账中列作用范围，作者不能自行扩大修复范围。
    scopes = ruling["score_repair_scope"]
    acceptance_ids = set()
    for issue in ruling.get("issues", []):
        acceptance = issue.get("acceptance")
        if isinstance(acceptance, list):
            acceptance_ids.update(row["id"] for row in acceptance if isinstance(row, dict) and row.get("id"))
        elif isinstance(acceptance, str) and acceptance.strip():
            acceptance_ids.add(issue["id"])
    allowed = {}
    for scope in scopes:
        key = (scope["group"], scope["item"])
        wp.require(key in keys() and key not in allowed, "裁决范围含未知或重复分项")
        wp.require(scope.get("acceptance_ids"), "裁决范围缺原验收ID")
        wp.require(set(scope["acceptance_ids"]) <= acceptance_ids, "裁决范围引用不存在的原验收ID")
        allowed[key] = set(scope["acceptance_ids"])
    updated = copy.deepcopy(original)
    changes, seen = [], set()
    metadata_allowed = {}
    for scope in ruling.get("metadata_repair_scope", []):
        name = scope["field"]
        wp.require(name == "evidence_gaps" and name not in metadata_allowed, "元数据裁决范围越界或重复")
        ids = set(scope.get("acceptance_ids", []))
        wp.require(bool(ids) and ids <= acceptance_ids, "元数据范围引用不存在的原验收ID")
        metadata_allowed[name] = ids
    metadata_changes = []
    for change in delta.get("metadata_changes", []):
        name = change["field"]
        wp.require(name in metadata_allowed and not metadata_changes, "元数据修复越界或重复")
        wp.require(set(change["acceptance_ids"]) == metadata_allowed[name], "元数据修复须对应原验收ID")
        value = change["set"]
        wp.require(isinstance(value, list), "evidence_gaps须为数组")
        for gap in value:
            wp.require(isinstance(gap, dict) and all(k in gap for k in
                       ("affected_items", "kind", "impact", "search_scope", "evidence_refs")), "缺口记录字段不全")
        before = copy.deepcopy(updated.get(name))
        wp.require(value != before, "元数据修复未产生变更")
        updated[name] = copy.deepcopy(value)
        metadata_changes.append({"field": name, "before": before, "after": copy.deepcopy(value),
                                 "acceptance_ids": change["acceptance_ids"]})
    wp.require(bool(delta["changes"] or metadata_changes), "修复变更为空")
    for change in delta["changes"]:
        key = (change["group"], change["item"])
        wp.require(key in allowed and key not in seen, "修复越界或重复分项")
        seen.add(key)
        wp.require(set(change["acceptance_ids"]) == allowed[key], "修复须对应原验收ID")
        fields = change["set"]
        wp.require(bool(fields) and set(fields) <= FIELDS, "修复字段越界")
        rows = updated["scores"][key[0]]["items"]
        row = next(r for r in rows if r["id"] == key[1])
        before = copy.deepcopy(row)
        row.update(copy.deepcopy(fields))
        wp.require(row != before, "修复未产生变更")
        changes.append({"group": key[0], "item": key[1], "before": before, "after": copy.deepcopy(row),
                        "acceptance_ids": change["acceptance_ids"]})
    for group in ("company", "management"):
        updated["scores"][group]["total"] = sum(wp.number(r["score"]) for r in updated["scores"][group]["items"])
    # 旧审批与资格只留在冻结原稿，不能随新评分继承为有效批准。
    for name in ("qualification", "approval", "repair", "score_approval"):
        updated.pop(name, None)
    updated.update(score_state="pending_review", research_state="pending_review", publish_allowed=False)
    updated["qualification"] = {"highest_score_gate": score_gate(updated, root),
                                "status": "pending_review", "reason": "仅重算评分门槛，须复核红线和全部入池条件"}
    report = check(updated, root, evidence)
    wp.require(not report["errors"], "；".join(report["errors"]))
    return {"workpaper": updated, "changes": changes, "metadata_changes": metadata_changes, "check": report,
            "base": base, "base_sha256": delta["base_sha256"], "decision": decision,
            "decision_sha256": delta["decision_sha256"],
            "unmodified_scope_items": [list(k) for k in sorted(set(allowed) - seen)],
            "limitations": "未修改的验收项仍须逐项答复；引用存在不证明语义正确，须双路复核变更及联动。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=wp.ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("output")
    read = sub.add_parser("packet")
    read.add_argument("stage", choices=("score", "valuation"))
    read.add_argument("output")
    read.add_argument("--extra", action="append", default=[])
    preflight = sub.add_parser("check")
    preflight.add_argument("workpaper")
    preflight.add_argument("evidence", help="证据文件相对路径数组的JSON")
    preflight.add_argument("output")
    repair = sub.add_parser("apply-delta")
    for arg in ("base", "decision", "delta", "evidence", "output"):
        repair.add_argument(arg)
    args = parser.parse_args()
    output = wp.local(args.root, args.output)
    if args.command == "plan":
        result = plan_template()
    elif args.command == "packet":
        result = packet(args.stage, args.root, args.extra)
    else:
        evidence = wp.read(wp.local(args.root, args.evidence))
        if args.command == "check":
            result = check(wp.read(wp.local(args.root, args.workpaper)), args.root, evidence)
        else:
            result = apply_delta(args.base, args.decision, wp.read(wp.local(args.root, args.delta)), args.root, evidence)
    if args.command == "packet":
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(result["text"].encode("utf-8"))
    elif args.command == "apply-delta":
        output.mkdir(parents=True, exist_ok=False)
        sheet = result.pop("workpaper")
        wp.save_new(output / "workpaper.json", json.dumps(sheet, ensure_ascii=False, indent=2) + "\n")
        result["workpaper_sha256"] = delivery.digest((output / "workpaper.json").read_bytes())
        wp.save_new(output / "receipt.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        wp.save_new(output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    summary = result.get("check", result)
    print(json.dumps({"output": str(output), "status": summary.get("status", "created"),
                      "errors": summary.get("errors", []), "warnings": summary.get("warnings", [])}, ensure_ascii=False))
    return int(summary.get("status") == "failed")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, StopIteration, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
