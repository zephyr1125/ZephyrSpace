"""输出"看个股"下一个待分析的公司名

规则：
- 取「任务」清单 → 「看个股」任务 → 子任务（checklistItems）
- 第一个 isChecked=false 且标题不含 "/" 的子任务（"/" 表示已写入分数）
- 输出格式：纯公司名（一行）。无则输出 NONE 并 exit 0。

用法：
    python scripts/todo_next.py
"""

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from todo_client import find_list_by_name, list_tasks, list_subtasks  # noqa: E402

LIST_NAME = "任务"
PARENT_TITLE = "看个股"


def main():
    lst = find_list_by_name(LIST_NAME)
    if not lst:
        print(f"ERROR: 未找到清单 '{LIST_NAME}'", file=sys.stderr)
        sys.exit(2)
    tasks = list_tasks(lst["id"])
    parent = next((t for t in tasks if t.get("title") == PARENT_TITLE), None)
    if not parent:
        print(f"ERROR: 未找到任务 '{PARENT_TITLE}'", file=sys.stderr)
        sys.exit(2)
    subs = list_subtasks(lst["id"], parent["id"])
    for s in subs:
        if s.get("isChecked"):
            continue
        name = (s.get("displayName") or "").strip()
        if not name:
            continue
        if "/" in name:
            continue
        print(name)
        return
    print("NONE")


if __name__ == "__main__":
    main()
