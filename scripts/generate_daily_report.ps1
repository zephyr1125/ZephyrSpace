param(
    [string]$VaultName = "Fan&Zhu",
    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
    [switch]$OpenAfterCreate
)

$args = @(
    ".\scripts\generate_daily_report.py",
    "--vault-name", $VaultName,
    "--date", $Date
)

if ($OpenAfterCreate) {
    $args += "--open-after-create"
}

python @args

