# setup_todo_scheduler.ps1 — 一键注册 Windows Task Scheduler 每15分钟轮询 To Do
# 以管理员身份运行一次即可

$TaskName   = "ZephyrSpace-PollToDo"
$ScriptPath = "E:\ObsidianVaults\ZephyrSpace\scripts\poll_todo.ps1"
$LogPath    = "E:\ObsidianVaults\ZephyrSpace\data\poll_todo.log"

# 移除旧任务（如已存在）
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "已移除旧任务"
}

$Action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -File `"$ScriptPath`" >> `"$LogPath`" 2>&1"

# 每15分钟触发一次（从开机后1分钟开始）
$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date).AddMinutes(1)

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -RunLevel  Highest `
    -Description "ZephyrSpace: 每15分钟轮询 Microsoft To Do，将股票任务写入 PreBuy 队列"

Write-Host ""
Write-Host "✅ Task Scheduler 已注册：$TaskName"
Write-Host "   轮询间隔：每15分钟"
Write-Host "   日志路径：$LogPath"
Write-Host ""
Write-Host "手动触发测试："
Write-Host "   Start-ScheduledTask -TaskName '$TaskName'"
