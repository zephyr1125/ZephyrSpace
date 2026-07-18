<#
.SYNOPSIS
  将 vault 中的 watchlist 分拆文件同步到外部 Finance 项目。

.DESCRIPTION
  watchlist 采用 meta/strategic/core/growth/out_of_scope 配置，并包含独立指数列表，每次修改后
  运行此脚本将其同步到 E:\Work\Python\Finance\api\config\。

.EXAMPLE
  .\scripts\sync_watchlist.ps1
#>

$src = "$PSScriptRoot\..\data"
$dst = "E:\Work\Python\Finance\api\config"

$files = @(
    "watchlist_meta.json",
    "watchlist_strategic.json",
    "watchlist_core.json",
    "watchlist_growth.json",
    "watchlist_out_of_scope.json",
    "watchlist_index.json"
)
$deprecatedFiles = @("stock_watchlist.json", "watchlist_radar.json")

foreach ($f in $deprecatedFiles) {
    $dstFile = Join-Path $dst $f
    if (Test-Path $dstFile) {
        Remove-Item -LiteralPath $dstFile -Force
        Write-Host "  Removed deprecated: $f"
    }
}

foreach ($f in $files) {
    $srcFile = Join-Path $src $f
    $dstFile = Join-Path $dst $f
    if (Test-Path $srcFile) {
        Copy-Item $srcFile $dstFile -Force
        $text = [System.IO.File]::ReadAllText($dstFile)
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($dstFile, $text, $utf8NoBom)
        Write-Host "  Synced: $f"
    } else {
        Write-Warning "  Missing: $srcFile"
    }
}

Write-Host "`n✅ Watchlist synced to $dst"
