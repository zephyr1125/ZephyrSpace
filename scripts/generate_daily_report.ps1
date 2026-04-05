param(
    [string]$VaultName = "ZephyrSpace",
    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
    [switch]$OpenAfterCreate,
    [switch]$OverwriteExisting
)

$args = @(
    ".\scripts\generate_daily_report.py",
    "--vault-name", $VaultName,
    "--date", $Date
)

if ($OpenAfterCreate) {
    $args += "--open-after-create"
}

if ($OverwriteExisting) {
    $args += "--overwrite-existing"
}

python @args

