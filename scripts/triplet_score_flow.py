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
    scopes = ruling.get("score_repair_scope", [])
    joint = original.get("research_profile") == "joint_research_v1"
    if joint:
        try:
            from scripts import triplet_research as research
        except ImportError:
            import triplet_research as research
        cycle = research.validate_cycle(ruling, root)
        previous_cycle = original.get("research_cycle")
        if previous_cycle:
            wp.require(all(cycle[key] == previous_cycle[key] for key in
                           ("mode", "first_review_refs", "first_workpaper_sha256", "repairs_used")),
                       "裁决修复额度或初审谱系与底稿不一致，不得重置")
        else:
            wp.require(cycle["repairs_used"] == 0 and cycle["first_workpaper_sha256"] == delta["base_sha256"],
                       "首次修复须绑定初审底稿且额度从零开始")
        if ruling.get("workpaper_sha256"):
            wp.require(ruling["workpaper_sha256"] == delta["base_sha256"], "裁决未绑定本次修复底稿")
    else:
        wp.require(not delta.get("valuation_changes"), "旧评分接口不接受估值修复")
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
        metadata_fields = {"evidence_gaps", "bridges", "numeric_fact_ids", "numeric_calculations"} if joint else {"evidence_gaps"}
        wp.require(name in metadata_fields and name not in metadata_allowed, "元数据裁决范围越界或重复")
        ids = set(scope.get("acceptance_ids", []))
        wp.require(bool(ids) and ids <= acceptance_ids, "元数据范围引用不存在的原验收ID")
        metadata_allowed[name] = ids
    metadata_changes = []
    for change in delta.get("metadata_changes", []):
        name = change["field"]
        wp.require(name in metadata_allowed and name not in {r["field"] for r in metadata_changes}, "元数据修复越界或重复")
        wp.require(set(change["acceptance_ids"]) == metadata_allowed[name], "元数据修复须对应原验收ID")
        value = change["set"]
        wp.require(isinstance(value, list), "元数据修复须为数组")
        for gap in value if name == "evidence_gaps" else []:
            wp.require(isinstance(gap, dict) and all(k in gap for k in
                       ("affected_items", "kind", "impact", "search_scope", "evidence_refs")), "缺口记录字段不全")
        before = copy.deepcopy(updated.get(name))
        wp.require(value != before, "元数据修复未产生变更")
        updated[name] = copy.deepcopy(value)
        metadata_changes.append({"field": name, "before": before, "after": copy.deepcopy(value),
                                 "acceptance_ids": change["acceptance_ids"]})
    valuation_changes = []
    if joint:
        valuation_allowed = {}
        model_ids = set()
        for scope in ruling.get("valuation_repair_scope", []):
            field = scope["field"]
            wp.require(field in research.VALUATION_FIELDS and field not in valuation_allowed, "估值修复字段越界或重复")
            ids = set(scope["acceptance_ids"])
            wp.require(ids and ids <= acceptance_ids, "估值范围引用不存在的原验收ID")
            valuation_allowed[field] = ids
            if field == "models":
                model_ids = set(scope.get("model_ids", []))
                wp.require(model_ids and model_ids <= {m["id"] for m in original["valuation"]["models"]},
                           "模型修复缺明确的已有模型ID")
        used = set()
        for change in delta.get("valuation_changes", []):
            field = change["field"]
            wp.require(field in valuation_allowed and field not in used, "估值修复越界或重复")
            wp.require(set(change["acceptance_ids"]) == valuation_allowed[field], "估值修复须对应原验收ID")
            before = copy.deepcopy(updated["valuation"].get(field))
            wp.require(before != change["set"], "估值修复未产生变更")
            if field == "models":
                old = {m["id"]: m for m in before}
                new = {m["id"]: m for m in change["set"]}
                wp.require(len(new) == len(change["set"]) and set(new) == set(old), "局部模型修复不能增删模型")
                wp.require(all(new[k] == old[k] for k in set(old) - model_ids), "未授权模型发生回退或改动")
            updated["valuation"][field] = copy.deepcopy(change["set"])
            used.add(field)
            valuation_changes.append({"field": field, "before": before, "after": change["set"],
                                      "acceptance_ids": change["acceptance_ids"]})
    wp.require(bool(delta.get("changes") or metadata_changes or valuation_changes), "修复变更为空")
    for change in delta.get("changes", []):
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
    if joint:
        updated["valuation_state"] = "pending_review"
        # 只保留与当前事实、规则及评分完全匹配的裁决批准，不信作者自述。
        approved = ruling.get("approval_projections", {}).get("score")
        if ruling.get("score_state") == "approved" and approved and approved == research.projection(updated, root, evidence, "score"):
            updated["score_state"] = "approved"
            updated["score_approval"] = {"projection_sha256": approved, "decision": decision,
                                         "decision_sha256": delta["decision_sha256"]}
        updated["research_cycle"] = {**cycle, "repairs_used": cycle["repairs_used"] + 1}
    report = research.check(updated, root, evidence) if joint else check(updated, root, evidence)
    wp.require(not report["errors"], "；".join(report["errors"]))
    return {"workpaper": updated, "changes": changes, "metadata_changes": metadata_changes,
            "valuation_changes": valuation_changes, "check": report,
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
