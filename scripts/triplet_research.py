"""联合研究的数值约束、批准依赖和不可变裁决；机械校验不替代独立审核。"""
import argparse
import ast
import copy
import json
from datetime import date
from pathlib import Path

try:
    from scripts import triplet_delivery as delivery
except ImportError:
    import triplet_delivery as delivery

wp = delivery.wp
PROFILE = "joint_research_v1"
RULES = ["deep-prebuy-skill/SKILL.md", "management-archive/SKILL.md",
         "management-archive/references/review-checks.md", "skills/valuation/SKILL.md"]
VALUATION_FIELDS = {"models", "weighted", "target_price", "certainty", "certainty_reason", "buy_price",
                    "reverse", "currency", "status", "reason", "additional_model_reason"}


def workpaper_template(company, code, currency, cutoff):
    """只生成字段骨架，不预填评分、假设或价格；避免从他公司底稿抄入判断。"""
    date.fromisoformat(cutoff)
    wp.require(all(isinstance(v, str) and v.strip() for v in (company, code, currency)), "公司、代码和币种不能为空")
    rules = wp.scoring_rules()
    scores = {}
    for group, limits, source in zip(("company", "management"), rules, RULES[:2]):
        scores[group] = {"total": None, "items": [
            {"id": key, "score": None, "rule_ref": source, "reason": "", "evidence_refs": []}
            for key in limits]}
    next(row for row in scores["company"]["items"] if row["id"] == "D2").update(
        original_statement_found=None, strategy_drift=None)
    return {"schema_version": 1, "research_profile": PROFILE, "score_display": "integer_half_up",
            "score_rule_validation": "explicit_tiers_v2", "company": company, "code": code,
            "cutoff": cutoff, "research_state": "pending", "publish_allowed": False,
            "scores": scores, "numeric_fact_ids": [], "numeric_calculations": [], "evidence_gaps": [],
            "bridges": [], "bridges_not_applicable": "", "valuation": {
                "currency": currency, "models": [{"id": "model_" + str(i), "weight": None,
                    "basis": "", "economic_basis": "", "evidence_refs": [], "shared_assumptions": [],
                    "output_currency": currency, "output_unit": "per_share", "formula": "",
                    "scenarios": {s: {"inputs": {}, "input_meta": {}, "value": None} for s in wp.SCENARIOS},
                    "sensitivity": {"x": "", "y": "", "x_values": [], "y_values": [], "values": []}}
                    for i in (1, 2)],
                "weighted": {s: None for s in wp.SCENARIOS}, "target_price": None, "certainty": None,
                "certainty_reason": "", "buy_price": None, "reverse": {"weight": 0, "variable": "",
                    "implied_value": None, "formula": "", "inputs": {}, "market_price": None,
                    "assumptions": "", "evidence_refs": []}}}


def save_draft(source, root, output):
    """允许保存真实未知和撤回状态；保存不执行研究验收，也不生成批准。"""
    source = wp.local(root, source)
    output = wp.local(root, output)
    wp.require(not output.exists(), "草稿目录已存在，禁止覆盖")
    data = wp.read(source)
    wp.require(isinstance(data, dict) and isinstance(data.get("scores"), dict)
               and isinstance(data.get("valuation"), dict), "草稿须包含scores和valuation")
    wp.require(not data.get("publish_allowed") and data.get("research_state") != "approved",
               "草稿保存不能携带完整研究或发布批准")
    output.mkdir(parents=True)
    wp.save_new(output / "workpaper.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    receipt = {"status": "draft_saved_not_reviewed", "research_approved": False,
               "input_sha256": delivery.digest(source.read_bytes()),
               "output_sha256": delivery.digest((output / "workpaper.json").read_bytes())}
    wp.save_new(output / "receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def numeric_check(data, index):
    """读取已有证据记录；口径核对与重算不能证明原件抄录真实。"""
    ids = data["numeric_fact_ids"]
    wp.require(isinstance(ids, list) and ids and len(ids) == len(set(ids)), "关键数值ID清单为空、重复或不是数组")
    facts = {}
    for key in ids:
        row = index[key]["record"]
        for name in ("entity", "metric", "unit", "currency", "consolidation", "actual_or_plan", "source_ref", "locator"):
            wp.require(isinstance(row.get(name), str) and row[name].strip(), key + "缺" + name)
        wp.require(row["source_ref"] in index, key + "来源未注册")
        start, end, as_of = (date.fromisoformat(row[name]) for name in ("period_start", "period_end", "as_of"))
        wp.require(start <= end, key + "期别倒置")
        wp.require(row["actual_or_plan"] in ("actual", "plan", "forecast", "assumption"), key + "实际/计划口径未知")
        if row["actual_or_plan"] == "actual":
            wp.require(end <= as_of, key + "实际值晚于信息截止日")
        wp.number(row["value"])
        if row["metric"] == "dividend":
            wp.require(type(row.get("profit_attribution_year")) is int, key + "缺分红归属年")
            date.fromisoformat(row["declaration_date"])
            wp.require(row["payment_status"] in ("paid", "unpaid", "unknown"), key + "支付状态未知")
            if row["payment_status"] == "paid":
                paid = date.fromisoformat(row["payment_date"])
                wp.require(paid <= as_of, key + "支付日晚于截止日")
        facts[key] = row
    for calc in wp.calculation_records(data):
        wp.require(calc["id"] not in facts, "派生计算ID重复")
        mapping = calc["input_fact_ids"]
        wp.require(mapping and set(mapping.values()) <= set(facts), "计算包含未声明关键数值")
        rows = [facts[key] for key in mapping.values()]
        wp.require(calc.get("unit") and calc.get("basis"), "派生值缺单位或口径说明")
        # 同口径计算显式声明约束字段；跨单位换算须在公式与basis中写明。
        same = calc["same_basis"]
        wp.require(set(same) <= {"unit", "currency", "consolidation", "period_start", "period_end", "actual_or_plan"},
                   "未知同口径约束")
        for field in same:
            wp.require(all(row.get(field) is not None for row in rows), "派生计算缺同口径元数据：" + field)
            wp.require(len({row[field] for row in rows}) == 1, "计算混用" + field)
        if calc.get("dividend_basis"):
            basis = calc["dividend_basis"]
            wp.require(basis in ("profit_attribution_year", "payment_year"), "分红累计口径未知")
            for row in rows:
                wp.require(row["metric"] == "dividend", "分红累计含非分红输入")
                year = row["profit_attribution_year"] if basis == "profit_attribution_year" else (
                    date.fromisoformat(row["payment_date"]).year if row["payment_status"] == "paid" else None)
                wp.require(year in calc["years"], "分红归属/支付年份不在累计范围")
        inputs = {name: facts[key]["value"] for name, key in mapping.items()}
        wp.close(calc["result"], wp.expression(calc["formula"], inputs), "派生数值" + calc["id"])
        inherited = {}
        for field in ("currency", "consolidation", "period_start", "period_end", "actual_or_plan"):
            values = {row.get(field) for row in rows}
            inherited[field] = calc.get(field, next(iter(values)) if len(values) == 1 else None)
        facts[calc["id"]] = {**inherited, "value": calc["result"], "unit": calc["unit"],
                             "metric": calc.get("metric", "derived")}


def recompute(data, root, evidence):
    """只生成已有公式的结果；不猜输入、不改分项、不继承研究批准。"""
    wp.require(data.get("research_state") != "approved" and not data.get("publish_allowed"),
               "获批底稿不能直接重算，请按原裁决建立修复草稿")
    wp.require(not data.get("approval_projections") and not data.get("frozen_inputs"),
               "冻结批准不能带入计算草稿")
    result = copy.deepcopy(data)
    changes = []

    def assign(row, key, value, path):
        if row.get(key) != value:
            changes.append({"path": path, "before": row.get(key), "after": value})
        row[key] = value

    index = delivery.evidence_index(root, evidence)
    ids = result["numeric_fact_ids"]
    wp.require(isinstance(ids, list) and len(ids) == len(set(ids)), "关键数值ID重复或不是数组")
    values = {key: wp.number(index[key]["record"]["value"]) for key in ids}
    rows = wp.calculation_records(result)
    original_order = [row["id"] for row in rows]
    wp.require(len(original_order) == len(set(original_order)), "派生计算ID重复")
    wp.require(not set(original_order) & set(index), "派生计算ID与证据重复")
    pending, ordered = list(rows), []
    while pending:
        ready = [row for row in pending if set(row["input_fact_ids"].values()) <= values.keys()]
        wp.require(ready, "计算依赖成环或引用未声明数值：" + ", ".join(row["id"] for row in pending))
        for row in ready:
            inputs = {name: values[key] for name, key in row["input_fact_ids"].items()}
            value = wp.expression(row["formula"], inputs)
            assign(row, "result", value, "numeric_calculations/" + row["id"] + "/result")
            values[row["id"]] = value
            ordered.append(row)
            pending.remove(row)
    result["numeric_calculations"] = ordered
    if original_order != [row["id"] for row in ordered]:
        changes.append({"path": "numeric_calculations/order", "before": original_order,
                        "after": [row["id"] for row in ordered]})
    # 先查事实、口径和依赖，不能用正确算术掩盖错期、混币种或缺失依据。
    numeric_check(result, index)
    valuation = result["valuation"]
    if valuation.get("status") not in wp.UNPRICED:
        models = valuation["models"]
        wp.require(models, "缺估值模型")
        wp.require(len({model["id"] for model in models}) == len(models), "模型ID重复")
        for model in models:
            prefix = "valuation/models/" + model["id"]
            for name in wp.SCENARIOS:
                scenario = model["scenarios"][name]
                # 发现输入与绑定值冲突时交作者处理，不自动改经济假设或注册新事实。
                for variable, meta in scenario["input_meta"].items():
                    binding = meta.get("calculation_id") or meta.get("numeric_fact_id")
                    if binding:
                        wp.require(binding in values, "模型输入绑定未声明：" + binding)
                        wp.close(scenario["inputs"][variable], values[binding], "模型输入绑定" + variable)
                value = wp.expression(model["formula"], scenario["inputs"])
                assign(scenario, "value", value, prefix + "/scenarios/" + name + "/value")
            grid = model["sensitivity"]
            base = model["scenarios"]["base"]["inputs"]
            matrix = [[wp.expression(model["formula"], {**base, grid["x"]: x, grid["y"]: y})
                       for x in grid["x_values"]] for y in grid["y_values"]]
            assign(grid, "values", matrix, prefix + "/sensitivity/values")
            wp.calculate_model(model)
        wp.require(all(wp.number(model["weight"]) > 0 for model in models), "模型权重必须为正")
        wp.close(sum(model["weight"] for model in models), 1, "主模型权重")
        weighted = {s: sum(m["weight"] * m["scenarios"][s]["value"] for m in models) for s in wp.SCENARIOS}
        assign(valuation, "weighted", weighted, "valuation/weighted")
        assign(valuation, "target_price", weighted["base"], "valuation/target_price")
        certainty = wp.number(valuation["certainty"])
        wp.require(0 <= certainty <= 1, "确定性越界")
        buy = wp.expression(wp.BUY_PRICE_FORMULA, {"target_price": weighted["base"], "certainty": certainty})
        assign(valuation, "buy_price", buy, "valuation/buy_price")
    return result, changes


def prepare_calculations(workpaper, evidence_path, root, output):
    """输出新目录及可追溯差异；校验失败仍明确保留为待修草稿。"""
    output = wp.local(root, output)
    wp.require(not output.exists(), "计算输出目录已存在，禁止覆盖")
    evidence = wp.read(wp.local(root, evidence_path))
    data, changes = recompute(wp.read(wp.local(root, workpaper)), root, evidence)
    report = check(data, root, evidence)
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    receipt = {"status": "failed" if report["errors"] else "mechanically_checked_pending_review",
               "input_sha256": {p: delivery.digest(wp.local(root, p).read_bytes())
                                for p in [workpaper, evidence_path, *evidence]},
               "changes": changes,
               "research_approved": False, "errors": report["errors"], "warnings": report.get("warnings", [])}
    output.mkdir(parents=True)
    wp.save_new(output / "workpaper.json", serialized)
    receipt["output_sha256"] = delivery.digest((output / "workpaper.json").read_bytes())
    wp.save_new(output / "receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def check(data, root, evidence):
    try:
        from scripts import triplet_score_flow as flow
    except ImportError:
        import triplet_score_flow as flow
    result = flow.check(data, root, evidence)
    try:
        wp.require(data.get("research_profile") == PROFILE, "联合研究缺profile")
        index = delivery.evidence_index(root, evidence)
        numeric_check(data, index)
        # 已验证派生记录可以支撑模型与桥接，避免要求把结果重复抄进事实表。
        for calculation in wp.calculation_records(data):
            key = calculation["id"]
            wp.require(key not in index, "派生计算ID与证据重复：" + key)
            index[key] = {"record": calculation}
        def refs(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "evidence_refs":
                        wp.require(child and all(ref in index for ref in child), "估值或桥接引用未注册")
                    else:
                        refs(child)
            elif isinstance(value, list):
                for child in value:
                    refs(child)
        refs(data["valuation"])
        refs(data["bridges"])
        valuation = data["valuation"]
        wp.require(valuation.get("status") != "deferred", "完整首审不能用待估值占位；缺证须记录未就绪")
        if valuation.get("status") not in wp.UNPRICED:
            for model in valuation["models"]:
                wp.require(model.get("economic_basis") and model.get("evidence_refs"), "模型缺经济依据及引用")
                for scenario in model["scenarios"].values():
                    for variable, meta in scenario["input_meta"].items():
                        if meta["kind"] == "actual":
                            key = meta.get("numeric_fact_id")
                            wp.require(key in data["numeric_fact_ids"], "实际模型输入缺关键数值绑定：" + variable)
                            fact = index[key]["record"]
                            wp.require(meta["unit"] == fact["unit"] and fact["actual_or_plan"] == "actual",
                                       "实际模型输入单位或实际/预测口径不一致")
                            wp.close(scenario["inputs"][variable], fact["value"], "实际模型输入" + variable)
    except (ValueError, KeyError, TypeError) as exc:
        result["errors"].append("联合研究：" + str(exc))
    result["status"] = "failed" if result["errors"] else "mechanically_checked_pending_review"
    return result


def projection(data, root, evidence, scope):
    wp.require(scope in ("score", "valuation"), "未知批准范围")
    # 第一版保守绑定全部有效证据及规则；依赖不明时宁可重审，不遗漏共享事实。
    paths = list(dict.fromkeys([*evidence, *RULES]))
    inputs = {p: delivery.digest(wp.local(root, p).read_bytes()) for p in paths}
    shared = {key: data.get(key) for key in ("company", "code", "market", "cutoff", "evidence_gaps",
              "bridges", "bridges_not_applicable", "numeric_fact_ids", "numeric_calculations", "score_rule_validation")}
    payload = data["scores"] if scope == "score" else {"scores": data["scores"], "valuation": data["valuation"]}
    return delivery.digest({"scope": scope, "payload": payload, "shared": shared, "inputs": inputs})


def validate_cycle(ruling, root):
    cycle = ruling["research_cycle"]
    wp.require(cycle["mode"] == "joint", "完整请求只能使用联合研究修复额度")
    refs = cycle["first_review_refs"]
    wp.require(len(refs) == 2 and len(set(refs)) == 2, "缺两路联合初审")
    for path in refs:
        review = wp.read(wp.local(root, path))
        wp.require(review["workpaper_sha256"] == cycle["first_workpaper_sha256"], "初审底稿版本不一致")
        wp.require(review["coverage"].get("score") is True and review["coverage"].get("valuation") is True,
                   "评分和估值尚未同时首审，不得消耗合并修复额度")
    wp.require(type(cycle["repairs_used"]) is int and 0 <= cycle["repairs_used"] < 2, "研究修复额度已耗尽")
    if cycle["repairs_used"] == 1:
        wp.require(cycle.get("exception_reason"), "例外修复缺裁决理由")
    return cycle


def freeze(config, root, output):
    """保存新版本；current只作指针，不成为旧裁决或构建依赖。"""
    output = wp.local(root, output)
    wp.require(not output.exists(), "冻结版本已存在")
    data = wp.read(wp.local(root, config["workpaper"]))
    ruling = copy.deepcopy(wp.read(wp.local(root, config["decision"])))
    delivery.validate_decision(ruling)
    if data.get("research_cycle"):
        wp.require(all(ruling.get("research_cycle", {}).get(key) == data["research_cycle"][key] for key in
                       ("mode", "first_review_refs", "first_workpaper_sha256", "repairs_used")),
                   "冻结裁决不得重置底稿修复计数或初审谱系")
    report = check(data, root, config["evidence"])
    wp.require(not report["errors"], "；".join(report["errors"]))
    if ruling.get("mechanical_requirements"):
        acceptance = check_acceptance(data, ruling, root, config["evidence"])
        wp.require(not acceptance["errors"], "裁决验收：" + "；".join(acceptance["errors"]))
    inputs = list(dict.fromkeys([*config["evidence"], *RULES, *ruling["review_refs"]]))
    wp.require(all(Path(p).name != "current.json" for p in inputs), "状态指针不得成为冻结输入")
    # 先验证旧批准，不能把状态字符串当成给新证据重新盖章的授权。
    for path, expected in ruling.get("frozen_inputs", {}).items():
        wp.require(delivery.digest(wp.local(root, path).read_bytes()) == expected, "旧裁决依赖已变化：" + path)
    projections = {scope: projection(data, root, config["evidence"], scope) for scope in ("score", "valuation")}
    for scope, expected in ruling.get("approval_projections", {}).items():
        wp.require(scope in projections and projections[scope] == expected, "旧批准依赖已变化：" + scope)
    approved_scopes = [scope for scope in projections if ruling.get(scope + "_state") == "approved"]
    if approved_scopes:
        wp.require(len(set(ruling["review_refs"])) >= 2, "批准缺两路审核")
        expected_inputs = {p: delivery.digest(wp.local(root, p).read_bytes()) for p in [*config["evidence"], *RULES]}
        for path in ruling["review_refs"]:
            review = wp.read(wp.local(root, path))
            wp.require(all(review.get("input_sha256", {}).get(p) == h for p, h in expected_inputs.items()),
                       "批准审核未绑定当前证据与规则：" + path)
            for scope in approved_scopes:
                wp.require(review.get("coverage", {}).get(scope) is True, "批准缺相应审核覆盖：" + scope)
                wp.require(review.get("workpaper_sha256") == delivery.digest(wp.local(root, config["workpaper"]).read_bytes())
                           or review.get("approval_projections", {}).get(scope) == projections[scope],
                           "批准审核未绑定当前底稿或对应批准投影：" + scope)
    ruling["research_profile"] = PROFILE
    ruling["frozen_inputs"] = {p: delivery.digest(wp.local(root, p).read_bytes()) for p in inputs}
    ruling["workpaper_sha256"] = delivery.digest(wp.local(root, config["workpaper"]).read_bytes())
    ruling["approval_projections"] = {scope: projections[scope] for scope in approved_scopes}
    if ruling["research_state"] == "approved":
        wp.require(set(ruling["approval_projections"]) == {"score", "valuation"}, "完整研究批准缺评分或估值批准")
    previous = config.get("previous_decision")
    if previous:
        ruling["previous_decision"] = {"path": previous, "sha256": delivery.digest(wp.local(root, previous).read_bytes())}
        ruling["frozen_inputs"][previous] = ruling["previous_decision"]["sha256"]
    output.mkdir(parents=True)
    (output / "workpaper.json").write_bytes(wp.local(root, config["workpaper"]).read_bytes())
    wp.save_new(output / "decision.json", json.dumps(ruling, ensure_ascii=False, indent=2) + "\n")
    pointer = {name: {"path": (output / (name + ".json")).relative_to(Path(root)).as_posix(),
                      "sha256": delivery.digest((output / (name + ".json")).read_bytes())}
               for name in ("workpaper", "decision")}
    current = output.parent / "current.json"
    temporary = output.parent / "current.json.tmp"
    temporary.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(current)
    return pointer


def verify_binding(data, ruling, root, evidence):
    wp.require(ruling.get("research_profile") == PROFILE, "联合底稿缺冻结裁决")
    for path, expected in ruling["frozen_inputs"].items():
        wp.require(Path(path).name != "current.json", "状态指针不能成为冻结依赖")
        wp.require(delivery.digest(wp.local(root, path).read_bytes()) == expected, "冻结依赖已变化：" + path)
    for scope, expected in ruling["approval_projections"].items():
        wp.require(projection(data, root, evidence, scope) == expected, scope + "批准依赖已变化")


def check_acceptance(data, ruling, root, evidence):
    """裁决指定驱动项必须连到受影响估值输入；不代替经济合理性验收。"""
    result = {"status": "mechanically_checked_pending_review", "checks": [], "errors": [],
              "limitations": "只核裁决声明的依赖与数值；不证明来源真实、假设合理或研究获批。"}
    try:
        rules = ruling.get("mechanical_requirements")
        wp.require(isinstance(rules, list) and rules, "未提供裁决机械验收映射")
        issues = set()
        for row in ruling["issues"]:
            issues.add(row["id"])
            # 新裁决使用分项验收ID，历史裁决仍可绑定问题ID。
            acceptance = row.get("acceptance", [])
            if isinstance(acceptance, list):
                issues.update(item["id"] for item in acceptance if isinstance(item, dict) and "id" in item)
        index = delivery.evidence_index(root, evidence)
        for i, calculation in enumerate(wp.calculation_records(data)):
            key = calculation["id"]
            wp.require(key not in index, "派生计算ID重复：" + key)
            index[key] = {"record": calculation, "pointer": f"/numeric_calculations/{i}"}
        models = {m["id"]: m for m in data["valuation"]["models"]}
        seen = set()
        for rule in rules:
            key = rule["id"]
            wp.require(key not in seen and rule["acceptance_id"] in issues, "验收ID重复或未绑定原问题")
            seen.add(key)
            try:
                required = rule["required_metrics"]
                wp.require(isinstance(required, list) and required and all(isinstance(v, str) and v for v in required), "缺必需经营驱动")
                model = models[rule["model_id"]]
                scenarios = rule["scenarios"]
                wp.require(scenarios and set(scenarios) <= set(wp.SCENARIOS), "验收情景无效")
                for name in scenarios:
                    scenario = model["scenarios"][name]
                    parameter = rule["input"]
                    model_names = {node.id for node in ast.walk(ast.parse(model["formula"], mode="eval"))
                                   if isinstance(node, ast.Name)}
                    wp.require(parameter in model_names, "经营驱动输入未参与估值公式：" + parameter)
                    calc = scenario["input_meta"][parameter]["calculation_id"]
                    wp.require(index[calc]["record"].get("formula"), "模型输入没有可复算推导")
                    value, refs = delivery.resolve_number(calc, index)
                    wp.close(value, scenario["inputs"][parameter], "驱动桥与模型输入" + parameter)
                    wp.require(index[calc]["record"]["unit"] == scenario["input_meta"][parameter]["unit"], "驱动桥与模型输入单位不一致")
                    metrics = {index[ref]["record"].get("metric") for ref in refs}
                    wp.require(set(required) <= metrics, "计算依赖缺经营驱动：" + ",".join(sorted(set(required) - metrics)))
                    # 声明但未参与表达式的变量不能伪装成已闭合的经营桥。
                    for ref in refs:
                        record = index[ref]["record"]
                        if record.get("formula"):
                            names = {node.id for node in ast.walk(ast.parse(record["formula"], mode="eval")) if isinstance(node, ast.Name)}
                            wp.require(set(record["input_fact_ids"]) <= names, "驱动仅列入映射但未参与公式：" + ref)
                result["checks"].append({"id": key, "acceptance_id": rule["acceptance_id"], "status": "pass"})
            except (ValueError, KeyError, TypeError, SyntaxError) as exc:
                result["errors"].append(key + "：" + str(exc))
                result["checks"].append({"id": key, "acceptance_id": rule["acceptance_id"], "status": "fail"})
    except (ValueError, KeyError, TypeError) as exc:
        result["errors"].append(str(exc))
    if result["errors"]:
        result["status"] = "failed"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=wp.ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    template = sub.add_parser("init-workpaper", help="创建未完成的空底稿，不生成研究结论")
    for name in ("company", "code", "currency", "cutoff", "output"):
        template.add_argument(name)
    validate = sub.add_parser("check")
    for name in ("workpaper", "evidence", "output"):
        validate.add_argument(name)
    compute = sub.add_parser("recompute", help="按原公式生成计算草稿与差异，不改变输入或批准研究")
    for name in ("workpaper", "evidence", "output"):
        compute.add_argument(name)
    draft = sub.add_parser("save-draft", help="保存未知或撤回状态，不进行验收或批准")
    draft.add_argument("workpaper")
    draft.add_argument("output")
    frozen = sub.add_parser("freeze")
    frozen.add_argument("config")
    frozen.add_argument("output")
    acceptance = sub.add_parser("check-acceptance")
    for name in ("workpaper", "ruling", "evidence", "output"):
        acceptance.add_argument(name)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "init-workpaper":
        result = workpaper_template(args.company, args.code, args.currency, args.cutoff)
        wp.save_new(wp.local(root, args.output), json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    elif args.command == "save-draft":
        result = save_draft(args.workpaper, root, args.output)
    elif args.command == "recompute":
        result = prepare_calculations(args.workpaper, args.evidence, root, args.output)
    elif args.command == "freeze":
        result = freeze(wp.read(wp.local(root, args.config)), root, args.output)
    elif args.command == "check-acceptance":
        evidence = wp.read(wp.local(root, args.evidence))
        result = check_acceptance(wp.read(wp.local(root, args.workpaper)), wp.read(wp.local(root, args.ruling)), root, evidence)
        result["input_sha256"] = {path: delivery.digest(wp.local(root, path).read_bytes()) for path in
                                  [args.workpaper, args.ruling, args.evidence, *evidence]}
        wp.save_new(wp.local(root, args.output), json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        result = check(wp.read(wp.local(root, args.workpaper)), root, wp.read(wp.local(root, args.evidence)))
        wp.save_new(wp.local(root, args.output), json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": args.output, "status": result.get("status"), "errors": result.get("errors", [])}, ensure_ascii=False))
    return int(bool(result.get("errors")))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
