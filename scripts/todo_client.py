"""Microsoft To Do 客户端 — Graph API + MSAL device code flow

首次运行会弹出 device code 登录提示，token 缓存到 scripts/todo_data/token_cache.json
之后调用复用缓存中的 refresh token，无需重新登录。
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import msal
import urllib.request
import urllib.error

CLIENT_ID = os.environ.get("MS_TODO_CLIENT_ID", "96ff9305-44ba-497f-ad6b-2960d624b528")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Tasks.ReadWrite"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

CACHE_PATH = Path(__file__).parent / "todo_data" / "token_cache.json"


def _build_app() -> msal.PublicClientApplication:
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text())
    app = msal.PublicClientApplication(
        CLIENT_ID, authority=AUTHORITY, token_cache=cache
    )
    return app


def _save_cache(app: msal.PublicClientApplication) -> None:
    cache = app.token_cache
    if cache.has_state_changed:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(cache.serialize())


def get_token() -> str:
    app = _build_app()
    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"device flow init failed: {flow}")
        print("\n" + "=" * 60)
        print(flow["message"])
        print("=" * 60 + "\n", flush=True)
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"login failed: {result.get('error_description', result)}")

    _save_cache(app)
    return result["access_token"]


def graph_request(method: str, path: str, body: Optional[dict] = None) -> dict:
    token = get_token()
    url = path if path.startswith("http") else f"{GRAPH_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {msg}") from e


def list_task_lists() -> list[dict]:
    return graph_request("GET", "/me/todo/lists").get("value", [])


def find_list_by_name(name: str) -> Optional[dict]:
    for lst in list_task_lists():
        if lst.get("displayName") == name:
            return lst
    return None


def list_tasks(list_id: str) -> list[dict]:
    return graph_request("GET", f"/me/todo/lists/{list_id}/tasks?$top=200").get(
        "value", []
    )


def list_subtasks(list_id: str, task_id: str) -> list[dict]:
    return graph_request(
        "GET", f"/me/todo/lists/{list_id}/tasks/{task_id}/checklistItems"
    ).get("value", [])


def update_checklist_item(
    list_id: str, task_id: str, item_id: str, *, display_name: str = None,
    is_checked: bool = None,
) -> dict:
    body = {}
    if display_name is not None:
        body["displayName"] = display_name
    if is_checked is not None:
        body["isChecked"] = is_checked
    return graph_request(
        "PATCH",
        f"/me/todo/lists/{list_id}/tasks/{task_id}/checklistItems/{item_id}",
        body=body,
    )


def _cli():
    if len(sys.argv) < 2:
        print("usage: todo_client.py <login|lists|find NAME|subtasks NAME>")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "login":
        get_token()
        print("登录成功，token 已缓存")
    elif cmd == "lists":
        for lst in list_task_lists():
            print(f"{lst['id']}\t{lst['displayName']}")
    elif cmd == "find":
        name = sys.argv[2]
        lst = find_list_by_name(name)
        if not lst:
            print(f"未找到任务列表: {name}")
            sys.exit(2)
        print(json.dumps(lst, ensure_ascii=False, indent=2))
    elif cmd == "subtasks":
        # 用法: subtasks <list_name> <parent_task_title>
        list_name = sys.argv[2]
        parent_title = sys.argv[3]
        lst = find_list_by_name(list_name)
        if not lst:
            print(f"未找到任务列表: {list_name}")
            sys.exit(2)
        tasks = list_tasks(lst["id"])
        parent = next((t for t in tasks if t.get("title") == parent_title), None)
        if not parent:
            print(f"未找到父任务: {parent_title}")
            print("现有任务:")
            for t in tasks:
                print(f"  - {t.get('title')}")
            sys.exit(3)
        subs = list_subtasks(lst["id"], parent["id"])
        print(f"父任务: {parent_title}  ({len(subs)} 个子任务)")
        for s in subs:
            mark = "[x]" if s.get("isChecked") else "[ ]"
            print(f"  {mark} {s.get('displayName')}")
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _cli()
