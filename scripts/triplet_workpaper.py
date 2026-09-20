"""三件套底稿机械检查与表格生成；不判断事实、模型适用性或入库资格。"""
import argparse
import ast
import hashlib
import json
import math
import operator
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("bear", "base", "bull")
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_new(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"需要有限数值，实际为 {value!r}")
    return value


def score_display(value):
    """只舍入对外显示值；原始分继续用于计算、门槛和机器字段。"""
    return str(Decimal(str(number(value))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def snapshot_values(data, result):
    values = {key: result[key] for key in ("cScore", "mScore", "target_price", "certainty", "buy_price", "currency")}
    if data.get("score_display") == "integer_half_up":
        # 合计先加原始分，不能相加已经舍入的两个显示分。
        values["combinedScore"] = result["cScore"] + result["mScore"]
    return values


def snapshot_text(data, key, value):
    if data.get("score_display") == "integer_half_up" and key in ("cScore", "mScore", "combinedScore"):
        return score_display(value)
    return value if isinstance(value, str) else f"{value:.6f}"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected, label):
    require(math.isclose(number(actual), number(expected), rel_tol=1e-9, abs_tol=1e-9),
            f"{label}不一致：{actual} != {expected}")


def expression(formula, inputs):
    """只解释标量四则和有限乘方，不执行底稿中的 Python 代码。"""
    require(isinstance(formula, str) and len(formula) <= 12000, "公式为空或过长")
    tree = ast.parse(formula, mode="eval")
    require(sum(1 for _ in ast.walk(tree)) <= 2000, "公式节点过多")

    def visit(node):
        if isinstance(node, ast.Constant):
            return number(node.value)
        if isinstance(node, ast.Name):
            return number(inputs[node.id])
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return number(visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1))
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow):
                require(abs(right) <= 100 and abs(left) <= 1e100, "乘方超出计算范围")
            return number(OPS[type(node.op)](left, right))
        raise ValueError("公式仅支持数值、变量、括号、加减乘除及乘方")

    return visit(tree.body)


def local(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), "文件必须位于指定根目录内")
    return path


def report_sections(text):
    """以二级标题划定修复边界，代码块中的标题不参与分段。"""
    sections, key, lines, fence = {}, "__preamble__", [], None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
        if fence is None and line.startswith("## "):
            require(key not in sections, "报告二级标题重复，无法可靠比较修复范围")
            sections[key] = "".join(lines)
            key, lines = line.strip()[3:], []
        lines.append(line)
    require(key not in sections, "报告二级标题重复")
    sections[key] = "".join(lines)
    return sections


def scoring_rules():
    # 满分从仓库唯一内容规则提取，避免另维护一套评分权重。
    text = (ROOT / "deep-prebuy-skill/SKILL.md").read_text(encoding="utf-8")
    company = {}
    for line in text.splitlines():
        cells = [x.strip() for x in line.strip("|").split("|")]
        if re.match(r"^[A-F]\d", cells[0]) and len(cells) == 4:
            key = cells[0].split()[0]
            company[key] = float(cells[2])
    text = (ROOT / "management-archive/SKILL.md").read_text(encoding="utf-8")
    section = text.split("## 九、管理层 100 分制评分", 1)[1].split("### 评级标准", 1)[0]
    management = {}
    for line in section.splitlines():
        cells = [x.strip() for x in line.strip("|").split("|")]
        if len(cells) == 4 and cells[1].isdigit() and not cells[0].startswith("**"):
            management[cells[0]] = float(cells[1])
    require(len(company) == 25 and sum(company.values()) == 100, "公司评分规则无法完整解析")
    require(len(management) == 7 and sum(management.values()) == 100, "管理层评分规则无法完整解析")
    return company, management


def score(sheet, limits, label):
    rows = sheet["items"]
    ids = [row["id"] for row in rows]
    require(len(ids) == len(set(ids)) and set(ids) == set(limits), f"{label}评分项遗漏、重复或未知")
    reasons = [re.sub(r"\s+", "", str(row.get("reason", ""))) for row in rows]
    require(not any(reasons.count(reason) >= 3 for reason in set(reasons)),
            f"{label}至少三个分项使用相同理由，须恢复各项事实→规则→得分证据桥，不能循环引用最终报告")
    for row in rows:
        cap = limits[row["id"]]
        # 原规则允许 F2.5 正面先例加 0.5，仍受 F 维度满分约束。
        if row["id"] == "F2.5" and row.get("positive_precedent") is True:
            cap += 0.5
        require(0 <= number(row["score"]) <= cap, f"{label}/{row['id']}超出分值")
        require(bool(row.get("rule_ref")) and bool(row.get("reason")) and bool(row.get("evidence_refs")),
                f"{label}/{row['id']}缺规则、理由或证据定位")
    total = sum(row["score"] for row in rows)
    close(sheet["total"], total, label + "总分")
    return total


def calculate_model(model):
    require(model.get("basis") and model.get("shared_assumptions") is not None, "模型缺依据或共享假设声明")
    require(set(model["scenarios"]) == set(SCENARIOS), "模型缺保守/基准/乐观情景")
    values = {}
    for name in SCENARIOS:
        scenario = model["scenarios"][name]
        metadata = scenario["input_meta"]
        require(set(metadata) == set(scenario["inputs"]), "模型输入元数据不完整")
        for key, value in scenario["inputs"].items():
            number(value)
            info = metadata[key]
            require(info.get("unit") and info.get("date") and info.get("evidence_refs")
                    and info.get("kind") in ("actual", "forecast", "assumption", "derived"),
                    "模型输入缺单位、期别、性质或依据：" + key)
        values[name] = expression(model["formula"], scenario["inputs"])
        close(scenario["value"], values[name], model["id"] + "/" + name)
    grid = model["sensitivity"]
    x, y = grid["x"], grid["y"]
    require(x != y, "敏感性必须是两个不同变量")
    base = model["scenarios"]["base"]["inputs"]
    require(x in base and y in base, "敏感性变量不在基准输入中")
    names = {n.id for n in ast.walk(ast.parse(model["formula"], mode="eval")) if isinstance(n, ast.Name)}
    require(x in names and y in names, "敏感性变量未参与公式")
    xs, ys = grid["x_values"], grid["y_values"]
    for variable, sequence in ((x, xs), (y, ys)):
        require(len(sequence) >= 2 and len(set(sequence)) == len(sequence), "敏感性轴缺点或重复")
        for value in sequence:
            number(value)
        require(base[variable] in sequence, "敏感性矩阵缺基准输入点")
    require(len(grid["values"]) == len(ys), "敏感性矩阵行数错误")
    matrix = []
    for j, y_value in enumerate(ys):
        require(len(grid["values"][j]) == len(xs), "敏感性矩阵列数错误")
        row = []
        for i, x_value in enumerate(xs):
            result = expression(model["formula"], {**base, x: x_value, y: y_value})
            close(grid["values"][j][i], result, f"{model['id']}敏感性[{j},{i}]")
            row.append(result)
        matrix.append(row)
    return values, matrix


def check(data, root=ROOT, reports=True, repair=False, previous=None):
    errors, warnings, result = [], [], {}

    def run(label, function):
        try:
            function()
        except (ValueError, KeyError, TypeError, IndexError, SyntaxError, ArithmeticError, OSError, RecursionError) as exc:
            errors.append(f"{label}：{exc}")

    def check_scores():
        company, management = scoring_rules()
        result["cScore"] = score(data["scores"]["company"], company, "公司")
        result["mScore"] = score(data["scores"]["management"], management, "管理层")
        rows = {row["id"]: row for row in data["scores"]["company"]["items"]}
        for group in "ABCDEF":
            obtained = sum(row["score"] for key, row in rows.items() if key.startswith(group))
            cap = sum(value for key, value in company.items() if key.startswith(group))
            require(obtained <= cap, f"{group}维度超过满分")
            if obtained <= cap * 0.4:
                warnings.append(f"公司{group}维度触发原规则重大警告；须人工处理，程序不判入库")
        d2 = rows["D2"]
        require(type(d2.get("original_statement_found")) is bool and type(d2.get("strategy_drift")) is bool,
                "D2缺原话验证/战略漂移状态")
        if not d2["original_statement_found"]:
            require(d2["score"] <= (3 if d2["strategy_drift"] else 4), "D2违反缺原话分层上限")
        for row in data["scores"]["management"]["items"]:
            if row["id"] in ("诚信与透明度", "资本配置能力") and row["score"] <= management[row["id"]] * 0.4:
                warnings.append(f"管理层{row['id']}触发原规则红旗；须人工处理")

    def check_valuation():
        valuation = data["valuation"]
        require(bool(valuation["currency"]), "缺币种")
        models = valuation["models"]
        require(len(models) >= 2, "缺两个主模型，不能用确定性折扣补足")
        require(len({m["id"] for m in models}) == len(models), "模型ID重复")
        if len(models) > 2:
            require(bool(valuation.get("additional_model_reason")), "新增主模型缺理由")
        for model in models:
            require(number(model["weight"]) > 0, "有效主模型权重必须为正")
            require(model["output_currency"] == valuation["currency"] and model["output_unit"] == "per_share",
                    "主模型必须先统一到所选股份的同币种每股价值")
        close(sum(m["weight"] for m in models), 1, "主模型权重")
        calculated = {m["id"]: calculate_model(m) for m in models}
        weighted = {s: sum(m["weight"] * calculated[m["id"]][0][s] for m in models) for s in SCENARIOS}
        for scenario in SCENARIOS:
            close(valuation["weighted"][scenario], weighted[scenario], "加权" + scenario)
        close(valuation["target_price"], weighted["base"], "合理价")
        certainty = number(valuation["certainty"])
        require(0 <= certainty <= 1 and valuation.get("certainty_reason"), "确定性越界或无依据")
        close(valuation["buy_price"], weighted["base"] * (0.68 + 0.14 * certainty), "机械买入价")
        reverse = valuation["reverse"]
        close(reverse["weight"], 0, "反向验证权重")
        require(reverse.get("variable") and reverse.get("assumptions") and reverse.get("evidence_refs"), "反向验证缺口径或依据")
        number(reverse["implied_value"])
        close(expression(reverse["formula"], reverse["inputs"]), reverse["market_price"], "反向代回市价")
        require(reverse["variable"] in reverse["inputs"], "反向变量未纳入输入")
        close(reverse["inputs"][reverse["variable"]], reverse["implied_value"], "反向隐含变量")
        result.update(target_price=weighted["base"], certainty=certainty,
                      buy_price=valuation["buy_price"], currency=valuation["currency"],
                      weighted=weighted, models=calculated)

    def check_bridges():
        require("bridges" in data, "缺桥接清单；不适用可用空数组并说明")
        require(data["bridges"] or data.get("bridges_not_applicable"), "桥接不适用缺理由")
        ids = set()
        for bridge in data["bridges"]:
            require(bridge["id"] not in ids, "桥接ID重复")
            ids.add(bridge["id"])
            parts = bridge["items"]
            keys = [p["economic_id"] for p in parts]
            require(len(keys) == len(set(keys)), "同一桥内经济项目重复，检查现金/资产重复计入")
            require(bridge.get("unit") and bridge.get("date") and bridge.get("scope"), "桥缺单位、日期或归属")
            for part in parts:
                require(part.get("evidence_refs"), "桥接项目缺来源")
                number(part["signed_value"])
            close(bridge["result"], number(bridge["start"]) + sum(p["signed_value"] for p in parts), "桥接" + bridge["id"])

    def check_reports():
        snapshots = snapshot_values(data, result)
        generated = render(data)
        table_keys = {"deep": ["company"], "management": ["management"],
                      "valuation": ["model-" + m["id"] for m in data["valuation"]["models"]] + ["weighted"]}
        for kind, minimum in (("deep", 150), ("management", 150), ("valuation", 100)):
            text = local(root, data["reports"][kind]).read_text(encoding="utf-8-sig")
            require(len(text.splitlines()) >= minimum, f"{kind}少于{minimum}行")
            for key, value in snapshots.items():
                matches = re.findall(r"<!-- triplet:" + key + r" -->(.*?)<!-- /triplet:" + key + r" -->", text)
                expected = snapshot_text(data, key, value)
                require(matches and all(m.strip() == expected for m in matches), f"{kind}/{key}缺快照标记或值不一致")
            for key in table_keys[kind]:
                pattern = r"<!-- triplet:table:" + re.escape(key) + r" -->(.*?)<!-- /triplet:table:" + re.escape(key) + r" -->"
                expected = re.search(pattern, generated, re.S).group(1).strip()
                actual = re.findall(pattern, text, re.S)
                require(actual and all(part.strip() == expected for part in actual), f"{kind}/{key}缺生成表或表格已漂移")

    def check_repairs():
        issues, closures = data["repair"]["issues"], data["repair"]["closures"]
        require(len({i["id"] for i in issues}) == len(issues), "修复问题ID重复")
        require(len({c["id"] for c in closures}) == len(closures), "关闭表ID重复")
        by_id = {c["id"]: c for c in closures}
        require(set(by_id) <= {i["id"] for i in issues}, "关闭表有未知问题")
        for issue in issues:
            require(issue["severity"] in ("P0", "P1", "P2"), "未知问题等级")
            if issue["severity"] == "P2":
                continue
            closure = by_id.get(issue["id"], {})
            acceptance = issue["acceptance_ids"]
            require(acceptance and len(set(acceptance)) == len(acceptance), "缺验收条件或ID重复")
            checks = closure.get("checks", [])
            require({c["id"] for c in checks} == set(acceptance) and len(checks) == len(acceptance), "验收条件未逐项覆盖")
            require(closure.get("locations") and closure.get("score_valuation_impact"), "缺修复位置或评分估值联动")
            require(all(c.get("passed") is True and c.get("evidence") for c in checks), "重要问题未关闭或缺验收证据")

    def check_regression():
        require(previous is not None, "修复须提供--previous冻结底稿，不能只核新版自称通过")
        declarations = data["repair"]["score_changes"]
        declared = {change["key"]: change for change in declarations}
        require(len(declared) == len(declarations), "评分变更声明重复")
        issues = {issue["id"] for issue in data["repair"]["issues"]}
        actual = set()
        for kind in ("company", "management"):
            old = {row["id"]: row for row in previous["scores"][kind]["items"]}
            new = {row["id"]: row for row in data["scores"][kind]["items"]}
            require(set(old) == set(new), "修复删除或增加了评分项")
            for item_id in old:
                key = kind + "/" + item_id
                if old[item_id] == new[item_id]:
                    continue
                actual.add(key)
                change = declared.get(key, {})
                require(change.get("issue_id") in issues and change.get("reason") and change.get("evidence_refs"),
                        f"{key}变动未映射到裁决ID、原因和新证据；未受影响项应原样保留")
        require(set(declared) == actual, "评分变更声明与实际差异不一致")
        if reports:
            changes = data["repair"]["report_changes"]
            declared_sections = {(item["report"], item["section"]): item for item in changes}
            require(len(declared_sections) == len(changes), "正文变更声明重复")
            actual_sections = set()
            for kind in ("deep", "management", "valuation"):
                old = report_sections(local(root, previous["reports"][kind]).read_text(encoding="utf-8-sig"))
                new = report_sections(local(root, data["reports"][kind]).read_text(encoding="utf-8-sig"))
                for section in old.keys() | new.keys():
                    if old.get(section) == new.get(section):
                        continue
                    key = (kind, section)
                    actual_sections.add(key)
                    change = declared_sections.get(key, {})
                    require(change.get("issue_id") in issues and change.get("reason"),
                            f"{kind}/{section}发生未声明重写或删除，须保留无关已核内容")
                    if section in old and section not in new:
                        require(change.get("replacement_section") in new, "删除旧章节必须指向保留其内容的新章节")
            require(set(declared_sections) == actual_sections, "正文变更声明与实际差异不一致")

    run("版本", lambda: require(data["schema_version"] == 1, "不支持的底稿版本"))
    run("评分显示", lambda: require(data.get("score_display") in (None, "integer_half_up"), "未知的评分显示模式"))
    run("评分", check_scores)
    run("估值", check_valuation)
    run("桥接", check_bridges)
    if reports:
        run("报告", check_reports)
    if repair:
        run("修复", check_repairs)
        run("防回退", check_regression)
    return {"status": "failed" if errors else "mechanical_checks_passed", "errors": errors,
            "warnings": warnings, "computed": result,
            "scope": {"reports": reports, "repair": repair},
            "limitations": "不验证证据真实性、行业适用性、假设合理性、正文全部数值或人工关闭判断；不代表双复核通过或允许入库。"}


def render(data):
    checked = check(data, reports=False)
    require(not checked["errors"], "底稿未通过机械检查：" + "；".join(checked["errors"]))
    result = checked["computed"]
    lines = ["<!-- 由 triplet_workpaper.py 生成；作者复制到新版本对应章节，禁止覆盖冻结稿。 -->", "", "| 参数 | 值 |", "|---|---|"]
    for key, raw in snapshot_values(data, result).items():
        value = snapshot_text(data, key, raw)
        lines.append(f"| {key} | <!-- triplet:{key} -->{value}<!-- /triplet:{key} --> |")
    if data.get("score_display") == "integer_half_up":
        lines += ["", "总分四舍五入显示；分项、机器底稿与门槛使用原始分。合计先加原始分再舍入。"]
    for name, sheet in data["scores"].items():
        lines += ["", f"<!-- triplet:table:{name} -->", f"### {name} 评分表", "", "| 分项 | 得分 | 理由 | 证据 |", "|---|---:|---|---|"]
        for row in sheet["items"]:
            reason = row['reason'].replace('|', '\\|').replace('\n', '<br>')
            evidence = '；'.join(row['evidence_refs']).replace('|', '\\|').replace('\n', '<br>')
            lines.append(f"| {row['id']} | {row['score']} | {reason} | {evidence} |")
        lines.append(f"<!-- /triplet:table:{name} -->")
    for model in data["valuation"]["models"]:
        values, matrix = result["models"][model["id"]]
        grid = model["sensitivity"]
        lines += ["", f"<!-- triplet:table:model-{model['id']} -->", f"### {model['id']} 情景与敏感性", "", "| 情景 | 合理价 |", "|---|---:|"]
        lines += [f"| {name} | {values[name]:.6f} |" for name in SCENARIOS]
        lines += ["", f"| {grid['y']} / {grid['x']} | " + " | ".join(map(str, grid["x_values"])) + " |",
                  "|---|" + "---:|" * len(grid["x_values"])]
        lines += [f"| {y} | " + " | ".join(f"{v:.6f}" for v in row) + " |" for y, row in zip(grid["y_values"], matrix)]
        lines.append(f"<!-- /triplet:table:model-{model['id']} -->")
    lines += ["", "<!-- triplet:table:weighted -->", "### 综合情景", "", "| 情景 | 加权合理价 |", "|---|---:|"]
    lines += [f"| {name} | {result['weighted'][name]:.6f} |" for name in SCENARIOS]
    lines.append("<!-- /triplet:table:weighted -->")
    return "\n".join(lines) + "\n"


def verify_migration(path, root=ROOT):
    for module in read(path)["modules"]:
        chunks = []
        for segment in module["segments"]:
            text = local(root, segment["path"]).read_text(encoding="utf-8-sig")
            key = segment["id"]
            matches = re.findall(r"<!-- migrated:" + key + r":start -->\n(.*?)<!-- migrated:" + key + r":end -->", text, re.S)
            require(len(matches) == 1, "迁移段缺失或重复：" + key)
            require(hashlib.sha256(matches[0].encode()).hexdigest() == segment["sha256"], "原段落发生变化：" + segment["path"] + "/" + key)
            chunks.append(matches[0])
        require(hashlib.sha256("".join(chunks).encode()).hexdigest() == module["original_sha256"], "原模块无法完整还原")
    return {"status": "migration_verified", "modules": len(read(path)["modules"])}


def repair_package(data):
    """仅转换裁决员签发的字段，不合并争议、不代裁决、不判关闭。"""
    issues = data["issues"]
    require(len({row["id"] for row in issues}) == len(issues), "裁决问题ID重复")
    lines = ["# 唯一修复包", "", "由已锁定裁决台账生成；裁决台账是唯一判断来源，本文不构成修复完成。", ""]
    for row in issues:
        require(row["decision"] in ("valid", "partial", "invalid", "insufficient", "suggestion"), "未知裁决结论")
        require(row["severity"] in ("P0", "P1", "P2"), "未知问题级别")
        require(row.get("candidate_ids") and row.get("reason") and row.get("evidence_refs"), "裁决缺候选映射或证据理由")
        if row["decision"] == "invalid":
            continue
        conditions = row["acceptance"]
        require(conditions and len({c['id'] for c in conditions}) == len(conditions), "验收条件缺失或ID重复")
        lines += [f"## {row['id']} · {row['severity']} · {row['decision']}", "",
                  f"候选：{', '.join(row['candidate_ids'])}", "",
                  f"裁决理由：{row['reason']}", "", f"原件：{'；'.join(row['evidence_refs'])}", "",
                  f"动作：{row['action']}", "", f"联动：{row['score_valuation_impact']}", ""]
        lines += [f"- {condition['id']}：{condition['condition']}" for condition in conditions]
        lines.append("")
    lines += ["## 最终参数或待定原因", "", "```json", json.dumps(data["parameters"], ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "render", "verify-migration", "repair-package"):
        command = sub.add_parser(name)
        command.add_argument("input")
        command.add_argument("--root", type=Path, default=ROOT)
        command.add_argument("--output")
        if name == "check":
            command.add_argument("--repair", action="store_true")
            command.add_argument("--previous", help="修复前冻结底稿；与--repair一起使用")
    args = parser.parse_args()
    if args.command in ("render", "repair-package"):
        require(args.output, "必须指定新输出文件")
        save_new(args.output, (render if args.command == "render" else repair_package)(read(args.input)))
        print("已生成新文件；不代表独立复核通过或修复关闭。")
        return 0
    result = verify_migration(args.input, args.root) if args.command == "verify-migration" else check(
        read(args.input), args.root, repair=args.repair, previous=read(args.previous) if args.previous else None)
    if args.output:
        save_new(args.output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "computed"}, ensure_ascii=False, indent=2))
    return int(result["status"] == "failed")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError) as error:
        print("检查未完成：" + str(error))
        raise SystemExit(2)
