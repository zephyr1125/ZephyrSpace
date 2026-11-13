"""从底稿生成无损估值审核包；引用完整不等于经济依据充分。"""
import argparse
import copy
import json
from pathlib import Path

try:
    from scripts import triplet_delivery as delivery
except ImportError:
    import triplet_delivery as delivery

wp = delivery.wp
REF_KEYS = {"evidence_refs", "source_ids", "source_id", "source_ref", "numeric_fact_id", "input_fact_ids", "calculation_id"}
QUESTIONS = {
    "normalization": "正常化盈利与披露值之间的调整是否可复算？",
    "multiple": "倍数是否有同口径比较或经营经济推导，而非仅引用股价？",
    "discount_rate": "折现率是否有可复算风险构成或有依据的替代口径？",
    "cashflow": "远期现金流是否连接增长、利润、营运资本、再投资与融资？",
    "terminal": "终值增长、回报率与再投资是否相容并说明收敛？",
    "bridges": "股数、租赁、SBC及补贴是否不重不漏？",
    "combination": "共享假设、权重与模型差异是否解释？相关性本身不禁止加权。",
    "buy_price": "机械买入价是否按所附规则复算？规则不要求等于悲观估值。",
}


def references(value):
    """只解析显式引用字段，不猜测正文中的字符串。"""
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in REF_KEYS:
                entries = child.values() if isinstance(child, dict) else child if isinstance(child, list) else [child]
                for item in entries:
                    wp.require(isinstance(item, str) and item.strip(), "引用字段含空值或非字符串")
                    found.add(item)
            else:
                found.update(references(child))
    elif isinstance(value, list):
        for child in value:
            found.update(references(child))
    return found


def build(data, root, evidence):
    valuation = data["valuation"]
    wp.require(valuation.get("status") not in wp.UNPRICED, "本命令仅用于有价格候选的估值审核")
    for key in ("models", "target_price", "certainty", "certainty_reason", "buy_price"):
        wp.require(key in valuation, "估值缺字段：" + key)
    wp.require(valuation["models"], "缺估值模型")
    for model in valuation["models"]:
        # 沿用既有模型核算器，不能让占位公式或非法元数据通过精简包入口。
        wp.calculate_model(model)
        wp.require(model.get("formula") and model.get("basis"), "模型缺公式或口径")
        wp.require(set(model.get("scenarios", {})) == set(wp.SCENARIOS), "模型缺完整三情景")
        for scenario in model["scenarios"].values():
            wp.require(scenario.get("inputs") and set(scenario["inputs"]) == set(scenario.get("input_meta", {})),
                       "情景参数与输入元数据不完整")
    wp.close(valuation["buy_price"], wp.expression(wp.BUY_PRICE_FORMULA, {
        "target_price": valuation["target_price"], "certainty": valuation["certainty"]}), "机械买入价")
    payload = {key: copy.deepcopy(data[key]) for key in (
        "company", "code", "market", "cutoff", "valuation", "bridges", "bridges_not_applicable",
        "evidence_gaps", "numeric_calculations") if key in data}
    index = delivery.evidence_index(root, evidence)
    for i, calculation in enumerate(wp.calculation_records(data)):
        key = calculation["id"]
        wp.require(key not in index, "派生计算ID与证据重复：" + key)
        index[key] = {"path": "workpaper", "pointer": f"/numeric_calculations/{i}", "record": calculation}
    pending = references(payload)
    retained = {}
    while pending:
        key = min(pending)
        pending.remove(key)
        if key in retained:
            continue
        wp.require(key in index, "审核包缺引用记录：" + key)
        retained[key] = copy.deepcopy(index[key])
        # 来源声明中的source_id是自身ID，集合去重可处理循环引用。
        pending.update(references(retained[key]["record"]) - retained.keys())
    return {
        "schema_version": 1, "scope": "valuation_only_not_full_triplet_review",
        "research": payload, "evidence": retained,
        "rules": {"buy_price_formula": wp.BUY_PRICE_FORMULA},
        "review_questions": QUESTIONS,
        "review_contract": "逐项回答适用性和依据；区分packet_missing、source_missing、unsupported_assumption。未见原文只能说本包未提供，不推断公司未披露。可按路径读取原件及索引外资料；本包不取代原件核验。缺失不能自动视为零值或永久否决。",
        "input_sha256": {path: delivery.digest(wp.local(root, path).read_bytes()) for path in evidence},
        "workpaper_projection_sha256": delivery.digest(payload),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workpaper")
    parser.add_argument("evidence", help="有效证据文件路径数组JSON")
    parser.add_argument("output")
    parser.add_argument("--root", type=Path, default=wp.ROOT)
    args = parser.parse_args()
    result = build(wp.read(wp.local(args.root, args.workpaper)), args.root,
                   wp.read(wp.local(args.root, args.evidence)))
    result["workpaper_sha256"] = delivery.digest(wp.local(args.root, args.workpaper).read_bytes())
    delivery.save_new(wp.local(args.root, args.output), json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"status": "packet_built_pending_review", "evidence_records": len(result["evidence"])}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
