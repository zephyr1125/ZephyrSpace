<#
.SYNOPSIS
  将 vault 中的 watchlist 分拆文件同步到外部 Finance 项目。

.DESCRIPTION
  watchlist 已拆分为 4 个文件（meta/core/growth/radar），每次修改后
  运行此脚本将其同步到 E:\Work\Python\Finance\api\config\。

.EXAMPLE
  .\scripts\sync_watchlist.ps1
#>

$src = "$PSScriptRoot\..\data"
$dst = "E:\Work\Python\Finance\api\config"

$files = @("watchlist_meta.json", "watchlist_core.json", "watchlist_growth.json", "watchlist_radar.json")

foreach ($f in $files) {
    $srcFile = Join-Path $src $f
    $dstFile = Join-Path $dst $f
    if (Test-Path $srcFile) {
        Copy-Item $srcFile $dstFile -Force
        Write-Host "  Synced: $f"
    } else {
        Write-Warning "  Missing: $srcFile"
    }
}

Write-Host "`n✅ Watchlist synced to $dst"
