"""核对证据交接覆盖和版本；不替代原件及评分判断。"""
import argparse
import json
from pathlib import Path

try:
    from scripts import triplet_delivery as delivery
except ImportError:
    import triplet_delivery as delivery


def check(data, root):
    wp = delivery.wp
    requirements = data["requirements"]
    answers = data["answers"]
    wanted = {row["id"]: row for row in requirements}
    supplied = {row["id"]: row for row in answers}
    wp.require(bool(wanted) and len(wanted) == len(requirements), "验收条件为空或重复")
    wp.require(len(supplied) == len(answers), "答复ID重复")
    wp.require(supplied.keys() == wanted.keys(), "答复必须逐一覆盖锁定条件，不得漏项或新增替代条件")
    index = delivery.evidence_index(root, data["evidence"])
    errors = []
    for key, requirement in wanted.items():
        answer = supplied[key]
        wp.require(requirement.get("scope") and type(requirement.get("decisive")) is bool,
                   key + "缺原定范围或决定性分类")
        status = answer.get("status")
        refs = answer.get("evidence_refs", [])
        if status not in ("covered", "bounded", "open"):
            errors.append(key + "状态未知")
        if not answer.get("coverage") or not answer.get("remaining"):
            errors.append(key + "缺已覆盖内容或剩余边界（无缺口也须明确）")
        if not refs or any(ref not in index for ref in refs):
            errors.append(key + "缺有效证据ID")
        if status == "open" and requirement["decisive"]:
            errors.append(key + "决定性条件仍未完成，不能交给作者当作已补齐")
        if status != "covered" and not answer.get("assessment"):
            errors.append(key + "须说明为何不妨碍评分，或具体影响哪些分项")
        if status == "bounded" and not answer.get("search_scope"):
            errors.append(key + "缺有界检索记录，不能将未完成伪装不可知")
    return {"status": "failed" if errors else "coverage_ready_for_human_check", "errors": errors,
            "inputs": {p: delivery.digest(wp.local(root, p).read_bytes()) for p in data["evidence"]},
            "limitations": "仅检查逐项覆盖、引用及版本；主任务必须对照实际内容核范围，covered自述不是实质验收。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--root", type=Path, default=delivery.wp.ROOT)
    args = parser.parse_args()
    result = check(delivery.wp.read(args.input), args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] == "failed")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
