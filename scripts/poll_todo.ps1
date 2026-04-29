# poll_todo.ps1 — Task Scheduler 调用入口，轮询 To Do → 写入 prebuy_queue.json
# 用法：直接运行，或设置为每 15 分钟自动执行

Set-Location "E:\ObsidianVaults\ZephyrSpace"
python scripts\poll_todo.py
