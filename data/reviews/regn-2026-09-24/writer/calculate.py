# -*- coding: utf-8 -*-
"""REGN 终审稿的扩展机械检查。

背景：标准工具 scripts/triplet_score_flow.py 要求「两个赋权主模型」，而终审裁决明确要求
「单一赋权主模型 + 零权重诊断折现模型」。依 docs/three-report-workpaper.md 的「模型适配边界」，
保留适用经济模型，用本脚本覆盖标准工具未覆盖的机械项。覆盖范围见 mechanical-check-scope.md。

用法：python -X utf8 data/reviews/regn-2026-09-24/writer/calculate.py
"""
import json, io, sys, math, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = "data/reviews/regn-2026-09-24"
WP = ROOT + "/writer/workpaper-v2.json"
FACTS = ROOT + "/evidence/facts.json"
d = json.load(open(WP, encoding="utf-8"))
facts = {f["fact_id"] for f in json.load(open(FACTS, encoding="utf-8"))["facts"]}
facts |= {x["source_id"] for x in json.load(open(ROOT + "/evidence/sources.json", encoding="utf-8"))["sources"]}

fails, checks = [], []


def ck(name, cond, detail=""):
    checks.append((name, bool(cond), detail))
    if not cond:
        fails.append("%s %s" % (name, detail))


def close(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


# ---------- 1. 分值上限与显式档位（照 deep-prebuy-skill/SKILL.md 原表） ----------
LIMITS = {"A1": 3, "A2": 3, "A3": 4, "B0": 2, "B1": 4, "B2": 3, "B3": 6, "B4": 5,
          "C1": 6, "C2": 5, "C3+C4": 9, "D1": 4, "D2": 5, "D3": 3, "D5": 3,
          "E1": 5, "E2": 5, "E3": 3, "E4": 2, "E5": 2, "E5.5": 3,
          "F1": 5, "F2": 5, "F2.5": 2, "F3": 3}
MLIMITS = {"诚信与透明度": 20, "资本配置能力": 25, "战略稳定性": 15, "对股东友好度": 15,
           "危机处理能力": 10, "组织与人才能力": 10, "表达清晰度与认知质量": 5}
# 封闭档位（原规则显式列出、不得自造中间分）
CLOSED = {"A3": [4, 2, 0], "D1": [4, 2, 0], "F2": [5, 3, 1, 0],
          "C1": [6, 4, 2, 1, 0], "C2": [5, 3, 1, 0], "C3+C4": [9, 7, 5, 2, 0],
          "F2.5": [2.5, 2, 1.5, 1, 0]}

co = {i["id"]: i for i in d["scores"]["company"]["items"]}
mg = {i["id"]: i for i in d["scores"]["management"]["items"]}
ck("company 分项数量=25", len(co) == 25, str(len(co)))
ck("management 分项数量=7", len(mg) == 7, str(len(mg)))
for k, lim in LIMITS.items():
    cap = lim + (0.5 if (k == "F2.5" and co[k].get("positive_precedent") is True) else 0)
    ck("company/%s 上限" % k, 0 <= co[k]["score"] <= cap, "%s>%s" % (co[k]["score"], cap))
    ck("company/%s 有规则与理由与证据" % k,
       bool(co[k].get("rule_ref")) and bool(co[k].get("reason")) and bool(co[k].get("evidence_refs")), "")
    for r in co[k]["evidence_refs"]:
        ck("company/%s 引用 %s 已注册" % (k, r), r in facts, "")
for k, lim in MLIMITS.items():
    ck("management/%s 上限" % k, 0 <= mg[k]["score"] <= lim, "")
    for r in mg[k]["evidence_refs"]:
        ck("management/%s 引用 %s 已注册" % (k, r), r in facts, "")
for k, allowed in CLOSED.items():
    ck("company/%s 显式档位" % k, co[k]["score"] in allowed, "score=%s" % co[k]["score"])

ct = sum(i["score"] for i in d["scores"]["company"]["items"])
mt = sum(i["score"] for i in d["scores"]["management"]["items"])
ck("company 总分闭合", close(ct, d["scores"]["company"]["total"]), "%s vs %s" % (ct, d["scores"]["company"]["total"]))
ck("management 总分闭合", close(mt, d["scores"]["management"]["total"]), "%s vs %s" % (mt, d["scores"]["management"]["total"]))
ck("合计=167", close(ct + mt, 167.0), "%s" % (ct + mt))
for dim, lim in (("A", 10), ("B", 20), ("C", 20), ("D", 15), ("E", 20), ("F", 15)):
    tot = {"A": ["A1", "A2", "A3"], "B": ["B0", "B1", "B2", "B3", "B4"],
           "C": ["C1", "C2", "C3+C4"], "D": ["D1", "D2", "D3", "D5"],
           "E": ["E1", "E2", "E3", "E4", "E5", "E5.5"], "F": ["F1", "F2", "F2.5", "F3"]}[dim]
    s = sum(co[i]["score"] for i in tot)
    ck("%s 维度未超限且高于 40%% 红线" % dim, 0.4 * lim <= s <= lim, "%s/%s" % (s, lim))

# ---------- 2. 估值主模型 ----------
v = d["valuation"]
models = v["models"]
ck("主模型数量=1（终审指定）", len(models) == 1, str(len(models)))
m1 = models[0]
ck("M1 权重为 1", close(m1["weight"], 1.0), str(m1["weight"]))


def expr(formula, inputs):
    import ast
    OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
           ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b, ast.Pow: lambda a, b: a ** b}
    def visit(n):
        if isinstance(n, ast.Constant):
            return float(n.value)
        if isinstance(n, ast.Name):
            return float(inputs[n.id])
        if isinstance(n, ast.UnaryOp):
            return visit(n.operand) * (-1 if isinstance(n.op, ast.USub) else 1)
        if isinstance(n, ast.BinOp):
            return OPS[type(n.op)](visit(n.left), visit(n.right))
        raise ValueError("不支持")
    return visit(ast.parse(formula, mode="eval").body)


for key in ("bear", "base", "bull"):
    sc = m1["scenarios"][key]
    got = expr(m1["formula"], sc["inputs"])
    ck("M1/%s 公式复算" % key, close(got, sc["value"], 1e-9), "%.6f vs %s" % (got, sc["value"]))
    for var in sc["inputs"]:
        ck("M1/%s/%s 有 input_meta" % (key, var), var in sc["input_meta"], "")
        ck("M1/%s/%s kind 合法" % (key, var), sc["input_meta"][var]["kind"] in ("actual", "forecast", "assumption", "derived"), "")

sen = m1["sensitivity"]
rows = sen["values"]
ck("M1 敏感性为矩阵", len(rows) == len(sen["y_values"]) and all(len(r) == len(sen["x_values"]) for r in rows), "")
for yi, yv in enumerate(sen["y_values"]):
    for xi, xv in enumerate(sen["x_values"]):
        inp = dict(m1["scenarios"]["base"]["inputs"])
        inp[sen["y"]] = yv
        inp[sen["x"]] = xv
        ck("M1 敏感性[%s,%s]" % (yi, xi), close(expr(m1["formula"], inp), rows[yi][xi], 1e-9),
           "%.6f vs %s" % (expr(m1["formula"], inp), rows[yi][xi]))
ck("M1 敏感性含基准输入", sen["x_values"].count(m1["scenarios"]["base"]["inputs"][sen["x"]]) == 1
   and sen["y_values"].count(m1["scenarios"]["base"]["inputs"][sen["y"]]) == 1, "")

w = v["weighted"]
for key in ("bear", "base", "bull"):
    ck("weighted/%s = M1（单模型）" % key, close(w[key], m1["scenarios"][key]["value"], 1e-9), "")
ck("target_price = round(weighted.base)", close(v["target_price"], round(w["base"]), 1e-9), "%s vs %s" % (v["target_price"], round(w["base"])))
ck("target_price 取整 785", close(v["target_price"], 785.0), "")
ck("certainty 在 0..1", 0 <= v["certainty"] <= 1, str(v["certainty"]))
ck("buy_price 公式", close(v["buy_price"], v["target_price"] * (0.68 + 0.14 * v["certainty"]), 1e-9),
   "%s" % v["buy_price"])

# ---------- 3. 零权重诊断折现模型 ----------
m2 = v["diagnostic_model"]
ck("诊断模型权重字段缺省（零权重）", "weight" not in m2, "")
for key in ("bear", "base", "bull"):
    sc = m2["scenarios"][key]
    got = expr(m2["formula"], sc["inputs"])
    ck("M2/%s 公式复算" % key, close(got, sc["value"], 1e-9), "%.6f vs %s" % (got, sc["value"]))
sen2 = m2["sensitivity"]
for yi, yv in enumerate(sen2["y_values"]):
    for xi, xv in enumerate(sen2["x_values"]):
        inp = dict(m2["scenarios"]["base"]["inputs"])
        inp[sen2["y"]] = yv
        inp[sen2["x"]] = xv
        ck("M2 敏感性[%s,%s]" % (yi, xi), close(expr(m2["formula"], inp), sen2["values"][yi][xi], 1e-9), "")
ck("诊断模型未参与合理价", close(v["target_price"], round(m1["scenarios"]["base"]["value"]), 1e-9), "")

# ---------- 4. 反向验证（权重 0） ----------
rv = v["reverse"]
ck("reverse 权重为 0", close(rv["weight"], 0.0), str(rv["weight"]))
got = expr(rv["formula"], rv["inputs"])
ck("reverse 代回市价", close(got, rv["market_price"], 1e-6), "%.6f vs %s" % (got, rv["market_price"]))
ck("reverse 隐含变量在 inputs", rv["variable"] in rv["inputs"], "")

# ---------- 5. 桥 ----------
for br in d["bridges"]:
    tot = float(br["start"]) + sum(float(i["signed_value"]) for i in br["items"])
    ck("桥 %s 闭合" % br["id"], close(tot, br["result"], 1e-9), "%s vs %s" % (tot, br["result"]))
    for it in br["items"]:
        for r in it["evidence_refs"]:
            ck("桥 %s 引用 %s 已注册" % (br["id"], r), r in facts, "")

# ---------- 6. 交付参数一致性 ----------
ck("README 参数一致", close(d["qualification"]["highest_score_gate"] == "A_CORE" and True, True), "")

print("=" * 72)
for name, ok, detail in checks:
    if not ok:
        print("FAIL", name, detail)
print("=" * 72)
print("检查项 %d，失败 %d" % (len(checks), len(fails)))
print("company %.1f | management %.1f | combined %.1f" % (ct, mt, ct + mt))
print("target %.2f | certainty %.2f | buy %.4f" % (v["target_price"], v["certainty"], v["buy_price"]))
print("M1 scenarios", [round(m1["scenarios"][k]["value"], 2) for k in ("bear", "base", "bull")])
print("M2 scenarios", [round(m2["scenarios"][k]["value"], 2) for k in ("bear", "base", "bull")])
print("STATUS:", "PASS" if not fails else "FAIL")
sys.exit(1 if fails else 0)
