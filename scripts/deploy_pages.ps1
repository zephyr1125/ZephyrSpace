<#
.SYNOPSIS
  将 public/ 文件夹部署到 GitHub Pages（space-research 仓库）
.DESCRIPTION
  使用 git subtree split + force push 的方式，将 ZephyrSpace/public/ 目录
  单独推送到 zephyr1125/space-research 仓库的 main 分支。
  GitHub Pages 从该仓库的 main 分支根目录提供服务。
.NOTES
  首次使用前需要：
  1. 在 GitHub 上创建 public repo: zephyr1125/space-research
  2. 运行本脚本
  3. 在 space-research 仓库 Settings > Pages 中启用 GitHub Pages (Source: main, / root)
#>

$ErrorActionPreference = "Stop"

$VaultRoot = Split-Path -Parent $PSScriptRoot
Set-Location $VaultRoot

$RemoteName = "pages"
$RemoteUrl = "https://github.com/zephyr1125/space-research.git"
$PublicDir = "public"

# 确保 public/ 已提交到 ZephyrSpace
$status = git status --porcelain $PublicDir
if ($status) {
    Write-Host "⚠ public/ 有未提交的改动，先自动提交..." -ForegroundColor Yellow
    git add $PublicDir
    git commit -m "docs: 更新公开发布内容"
}

# 添加 remote（如果不存在）
$existing = git remote 2>&1
if ($existing -notcontains $RemoteName) {
    Write-Host "📎 添加 remote: $RemoteName -> $RemoteUrl" -ForegroundColor Cyan
    git remote add $RemoteName $RemoteUrl
}

# 用 subtree split 提取 public/ 为独立分支，然后 force push
Write-Host "🚀 正在部署 public/ 到 space-research..." -ForegroundColor Cyan
$branch = git subtree split --prefix=$PublicDir -b pages-deploy 2>&1
git push $RemoteName pages-deploy:main --force

# 清理临时分支
git branch -D pages-deploy 2>$null

Write-Host ""
Write-Host "✅ 部署完成！" -ForegroundColor Green
Write-Host "🌐 访问: https://zephyr1125.github.io/space-research/" -ForegroundColor Green
Write-Host ""
Write-Host "如果是首次部署，请去 GitHub 仓库 Settings > Pages 启用：" -ForegroundColor Yellow
Write-Host "   Source: Deploy from a branch" -ForegroundColor Yellow
Write-Host "   Branch: main  /  / (root)" -ForegroundColor Yellow
