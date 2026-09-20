[CmdletBinding()]
param(
    [ValidateSet('Check', 'Install')]
    [string]$Mode = 'Check',
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$AgentsSkillsRoot = 'C:\Users\zephy\.agents\skills',
    [string]$CodexSkillsRoot = 'C:\Users\zephy\.codex\skills',
    [string]$BackupRoot = 'C:\Users\zephy\.agents\skill-retirement-backups'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-FullPath([string]$Value) {
    return [IO.Path]::GetFullPath($Value).TrimEnd([IO.Path]::DirectorySeparatorChar)
}

function Get-ChildPath([string]$Root, [string]$Name) {
    $result = Get-FullPath (Join-Path $Root $Name)
    if ((Split-Path -Parent $result) -ne (Get-FullPath $Root)) {
        throw "目标超出指定目录：$result"
    }
    return $result
}

function Test-ExpectedJunction([string]$Path, [string]$Target) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return ($item.LinkType -eq 'Junction' -and
        (Get-FullPath ([string]$item.Target)) -eq (Get-FullPath $Target))
}

$taskWorkspace = Get-FullPath $WorkspaceRoot
$taskAgentRoot = Get-FullPath $AgentsSkillsRoot
$taskCodexRoot = Get-FullPath $CodexSkillsRoot
$taskBackupRoot = Get-FullPath $BackupRoot
$taskSource = Get-FullPath (Join-Path $taskWorkspace 'skills/company-triplet')
$taskEntry = Get-ChildPath $taskAgentRoot 'company-triplet'
$taskLegacyNames = @(
    'stock-prebuy-review', 'hk-prebuy', 'us-stock-prebuy',
    'deep-company-review', 'management-archive', 'valuation'
)

# 验证整套原件存在后，才允许迁移发现入口。
foreach ($relative in @(
    'skills/company-triplet/SKILL.md', 'deep-prebuy-skill/SKILL.md',
    'management-archive/SKILL.md', 'skills/valuation/SKILL.md',
    'docs/three-report-economy-routing.md', 'docs/three-report-evidence-contract.md',
    'docs/three-report-company-page.md', 'docs/three-report-workpaper.md',
    'docs/three-report-rule-migration.json', 'scripts/triplet_workpaper.py',
    'docs/three-report-closeout.md', 'scripts/triplet_run_audit.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskWorkspace $relative) -PathType Leaf)) {
        throw "唯一源缺失：$relative"
    }
}

# 内容模块按需附件也属于唯一源；存在入口但缺附件不能视为部署完整。
$taskRuleManifest = Get-Content -LiteralPath (Join-Path $taskWorkspace 'docs/three-report-rule-migration.json') -Raw | ConvertFrom-Json
foreach ($module in $taskRuleManifest.modules) {
    foreach ($segment in $module.segments) {
        $taskRulePath = Get-FullPath (Join-Path $taskWorkspace $segment.path)
        if (-not $taskRulePath.StartsWith($taskWorkspace + '\', [StringComparison]::OrdinalIgnoreCase) -or
            -not (Test-Path -LiteralPath $taskRulePath -PathType Leaf)) {
            throw "模块附件缺失或超出唯一源：$($segment.path)"
        }
    }
}

$taskRoots = @($taskAgentRoot, $taskCodexRoot)
foreach ($root in $taskRoots) {
    if ($taskBackupRoot -eq $root -or $taskBackupRoot.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw '备份目录不能放在技能发现目录内。'
    }
    if ((Test-Path -LiteralPath $root) -and (Get-Item -LiteralPath $root -Force).LinkType) {
        throw "发现根目录是联接，请提供实际根目录：$root"
    }
}

$taskToArchive = @()
foreach ($root in $taskRoots) {
    foreach ($name in $taskLegacyNames) {
        $path = Get-ChildPath $root $name
        if (Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue) {
            $taskToArchive += $path
        }
    }
}

# 同名第二入口也必须退役；正确的唯一入口保持不动。
$taskOtherEntry = Get-ChildPath $taskCodexRoot 'company-triplet'
if (Get-Item -LiteralPath $taskOtherEntry -Force -ErrorAction SilentlyContinue) {
    $taskToArchive += $taskOtherEntry
}
if ((Get-Item -LiteralPath $taskEntry -Force -ErrorAction SilentlyContinue) -and
    -not (Test-ExpectedJunction $taskEntry $taskSource)) {
    $taskToArchive += $taskEntry
}

if ($Mode -eq 'Check') {
    if ($taskToArchive.Count -gt 0 -or -not (Test-ExpectedJunction $taskEntry $taskSource)) {
        throw "入口不一致。旧/重复入口：$($taskToArchive -join ', ')；需安装唯一目录联接：$taskEntry"
    }
    if ((Get-FileHash -LiteralPath (Join-Path $taskEntry 'SKILL.md')).Hash -ne
        (Get-FileHash -LiteralPath (Join-Path $taskSource 'SKILL.md')).Hash) {
        throw '入口读取内容与唯一源不一致。'
    }
    Write-Output "检查通过：唯一入口 $taskEntry -> $taskSource；旧PreBuy及独立模块入口均不存在。"
    return
}

# 一次预检所有精确目标；拒绝搬动未知联接，避免移动其指向的其他目录。
foreach ($path in $taskToArchive) {
    $parent = Get-FullPath (Split-Path -Parent $path)
    $item = Get-Item -LiteralPath $path -Force
    if ($parent -notin $taskRoots -or -not $item.PSIsContainer -or $item.LinkType) {
        throw "拒绝迁移非预期普通技能目录：$path"
    }
}

$taskBackup = $null
if ($taskToArchive.Count -gt 0) {
    $taskBackup = Get-ChildPath $taskBackupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $taskBackup -Force | Out-Null
}
if (-not (Test-Path -LiteralPath $taskAgentRoot)) {
    New-Item -ItemType Directory -Path $taskAgentRoot | Out-Null
}
$taskMoved = @()
try {
    foreach ($path in $taskToArchive) {
        $prefix = if ((Split-Path -Parent $path) -eq $taskAgentRoot) { 'agents-' } else { 'codex-' }
        $destination = Get-ChildPath $taskBackup ($prefix + (Split-Path -Leaf $path))
        if (Test-Path -LiteralPath $destination) { throw "备份已存在：$destination" }
        Move-Item -LiteralPath $path -Destination $destination
        $taskMoved += [pscustomobject]@{ Original = $path; Backup = $destination }
    }
    if (-not (Test-ExpectedJunction $taskEntry $taskSource)) {
        New-Item -ItemType Junction -Path $taskEntry -Target $taskSource | Out-Null
    }
    if (-not (Test-ExpectedJunction $taskEntry $taskSource)) { throw '目录联接安装后校验失败。' }
} catch {
    # 只回滚已迁移且原位置仍为空的目录，绝不覆盖并发修改。
    for ($i = $taskMoved.Count - 1; $i -ge 0; $i--) {
        $move = $taskMoved[$i]
        if (-not (Test-Path -LiteralPath $move.Original)) {
            Move-Item -LiteralPath $move.Backup -Destination $move.Original
        }
    }
    throw
}

Write-Output "安装完成：$taskEntry -> $taskSource"
if ($taskBackup) { Write-Output "旧副本已退出发现目录，恢复备份：$taskBackup" }
