"""将"看个股"中某子任务回写分数并打勾

用法：
    python scripts/todo_mark.py "宝丰能源" 75 82           # 新分析
    python scripts/todo_mark.py "宝丰能源" 75 82 --reuse   # 复用旧档案

新分析回写为   "宝丰能源 75/82"
复用回写为     "宝丰能源 75/82 ♻"
均设置 isChecked=True
"""

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from todo_client import (  # noqa: E402
    find_list_by_name,
    list_tasks,
    list_subtasks,
    update_checklist_item,
)

LIST_NAME = "任务"
PARENT_TITLE = "看个股"


def main():
    args = sys.argv[1:]
    reuse = False
    if "--reuse" in args:
        reuse = True
        args.remove("--reuse")
    if len(args) != 3:
        print(__doc__)
        sys.exit(1)
    original = args[0].strip()
    try:
        deep = int(args[1])
        mgmt = int(args[2])
    except ValueError:
        print("ERROR: 分数必须是整数", file=sys.stderr)
        sys.exit(1)

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
    target = next((s for s in subs if (s.get("displayName") or "").strip() == original), None)
    if not target:
        print(f"ERROR: 未找到子任务 '{original}'", file=sys.stderr)
        sys.exit(3)

    suffix = " ♻" if reuse else ""
    new_name = f"{original} {deep}/{mgmt}{suffix}"
    update_checklist_item(
        lst["id"], parent["id"], target["id"],
        display_name=new_name, is_checked=True,
    )
    print(f"OK: '{original}' → '{new_name}' [已打勾]")


if __name__ == "__main__":
    main()
