"""
poll_todo.py — 监控 Microsoft To Do，自动将未完成的股票任务写入 PreBuy 队列

用法：
    python scripts/poll_todo.py            # 正常轮询
    python scripts/poll_todo.py --auth     # 首次运行，触发浏览器授权
    python scripts/poll_todo.py --list     # 列出当前待处理队列

首次必须用 --auth 完成授权，之后 token 缓存到 .todo_token_cache 自动续期。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

try:
    import msal
    import requests
except ImportError:
    print("缺少依赖，请先运行：pip install msal requests")
    sys.exit(1)

# ── 配置 ────────────────────────────────────────────────────────────────────
VAULT_DIR      = Path(__file__).parent.parent
QUEUE_FILE     = VAULT_DIR / "data" / "prebuy_queue.json"
TOKEN_CACHE    = VAULT_DIR / ".todo_token_cache"      # 不提交到 git
CLIENT_ID      = os.getenv("MS_TODO_CLIENT_ID", "")   # Azure app client_id
TODO_LIST_NAME = os.getenv("MS_TODO_LIST_NAME", "任务")  # To Do 列表名称
SCOPES         = ["Tasks.ReadWrite", "User.Read"]
AUTHORITY      = "https://login.microsoftonline.com/consumers"

# 股票代码正则（6位纯数字或"名称+6位数字"格式）
STOCK_PATTERN = re.compile(r'[\u4e00-\u9fff]*(\d{6})')

# ── Token 管理 ───────────────────────────────────────────────────────────────
def _build_app():
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE.exists():
        cache.deserialize(TOKEN_CACHE.read_text(encoding="utf-8"))
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    return app, cache


def _save_cache(cache):
    if cache.has_state_changed:
        TOKEN_CACHE.write_text(cache.serialize(), encoding="utf-8")


def acquire_token(force_auth=False):
    if not CLIENT_ID:
        print("[错误] 未配置 MS_TODO_CLIENT_ID，请先在 .env 中填写 Azure App 的 client_id")
        sys.exit(1)

    app, cache = _build_app()
    accounts = app.get_accounts()

    if not force_auth and accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache)
            return result["access_token"]

    # Device code flow（兼容无浏览器服务器）
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        print("[错误] 无法初始化设备授权流")
        sys.exit(1)
    print(f"\n请在手机或浏览器打开：{flow['verification_uri']}")
    print(f"输入代码：{flow['user_code']}\n")
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        print(f"[错误] 授权失败：{result.get('error_description')}")
        sys.exit(1)
    _save_cache(cache)
    print("✅ 授权成功，token 已缓存")
    return result["access_token"]


# ── Graph API ────────────────────────────────────────────────────────────────
def graph_get(token, url, params=None):
    resp = requests.get(
        url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def graph_patch(token, url, body):
    resp = requests.patch(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()


def get_list_id(token, list_name):
    data = graph_get(token, "https://graph.microsoft.com/v1.0/me/todo/lists")
    for lst in data.get("value", []):
        if lst["displayName"] == list_name:
            return lst["id"]
    names = [l["displayName"] for l in data.get("value", [])]
    print(f"[警告] 未找到列表「{list_name}」，已有列表：{names}")
    return None


def get_pending_tasks(token, list_id):
    url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks"
    data = graph_get(token, url, params={"$filter": "status ne 'completed'", "$top": 100})
    return data.get("value", [])


def mark_task_completed(token, list_id, task_id):
    url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}"
    graph_patch(token, url, {"status": "completed"})


# ── 队列管理 ─────────────────────────────────────────────────────────────────
def load_queue():
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return []


def save_queue(queue):
    QUEUE_FILE.parent.mkdir(exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def company_page_exists(code):
    """检查 01-公司/ 下是否有包含该代码的公司页（简单扫描文件名）"""
    company_dir = VAULT_DIR / "01-公司"
    if not company_dir.exists():
        return False
    # 先扫文件名，再扫 frontmatter aliases
    for f in company_dir.glob("*.md"):
        if code in f.name:
            return True
        text = f.read_text(encoding="utf-8", errors="ignore")[:500]
        if code in text:
            return True
    return False


# ── 主逻辑 ───────────────────────────────────────────────────────────────────
def poll(mark_done_after_queue=False):
    """
    轮询 To Do，将新股票任务写入队列。
    mark_done_after_queue=True 时：写入队列后立即在 To Do 打勾（表示"已录入分析队列"）
    """
    token = acquire_token()
    list_id = get_list_id(token, TODO_LIST_NAME)
    if not list_id:
        return

    tasks = get_pending_tasks(token, list_id)
    queue = load_queue()
    existing_codes = {item["code"] for item in queue}

    new_count = 0
    for task in tasks:
        title = task["displayName"]
        m = STOCK_PATTERN.search(title)
        if not m:
            continue  # 不是股票任务，跳过

        code = m.group(1)
        if code in existing_codes:
            continue  # 已在队列中

        # 判断是否已有完整公司页（避免重复分析）
        already_done = company_page_exists(code)

        entry = {
            "code": code,
            "name": title,
            "task_id": task["id"],
            "list_id": list_id,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "done" if already_done else "pending",
        }
        queue.append(entry)
        existing_codes.add(code)
        new_count += 1

        if already_done:
            print(f"  ✅ {title} — 公司页已存在，跳过分析，标记完成")
            mark_task_completed(token, list_id, task["id"])
        else:
            print(f"  📥 {title} — 已加入 PreBuy 队列")
            if mark_done_after_queue:
                mark_task_completed(token, list_id, task["id"])

    save_queue(queue)

    pending = [x for x in queue if x["status"] == "pending"]
    if new_count == 0:
        print(f"[{datetime.now():%H:%M}] 无新任务，队列中 {len(pending)} 个待分析")
    else:
        print(f"\n✨ 新增 {new_count} 个股票到队列，当前待分析 {len(pending)} 个：")
        for item in pending:
            print(f"   • {item['name']} ({item['code']})")
        # Windows 气泡通知
        _notify(f"PreBuy 队列更新：{new_count} 个新股票", "\n".join(x["name"] for x in pending[:5]))


def list_queue():
    queue = load_queue()
    pending = [x for x in queue if x["status"] == "pending"]
    done    = [x for x in queue if x["status"] == "done"]
    print(f"\n📋 PreBuy 队列状态")
    print(f"   待分析：{len(pending)} 个")
    for item in pending:
        print(f"   • {item['name']} ({item['code']})  加入时间：{item['added_at']}")
    print(f"   已完成：{len(done)} 个")


def _notify(title, message):
    """Windows 10/11 气泡通知（可选依赖）"""
    try:
        import subprocess
        ps = (
            f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;'
            f'$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);'
            f'$template.GetElementsByTagName("text")[0].AppendChild($template.CreateTextNode("{title}")) | Out-Null;'
            f'$template.GetElementsByTagName("text")[1].AppendChild($template.CreateTextNode("{message[:80]}")) | Out-Null;'
            f'$notif = [Windows.UI.Notifications.ToastNotification]::new($template);'
            f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ZephyrSpace").Show($notif);'
        )
        subprocess.run(["powershell", "-c", ps], capture_output=True, timeout=5)
    except Exception:
        pass  # 通知失败不影响主流程


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Microsoft To Do → PreBuy 队列监控")
    parser.add_argument("--auth",  action="store_true", help="首次授权（会打开浏览器/设备码）")
    parser.add_argument("--list",  action="store_true", help="列出当前队列状态")
    parser.add_argument("--mark-done", action="store_true",
                        help="写入队列后立即在 To Do 打勾（不等分析完成）")
    args = parser.parse_args()

    if args.auth:
        acquire_token(force_auth=True)
    elif args.list:
        list_queue()
    else:
        poll(mark_done_after_queue=args.mark_done)
