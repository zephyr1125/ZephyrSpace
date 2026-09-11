param()

# 单位：金额人民币亿元、股本亿股、每股价值人民币元。
$shares = 216.89434304
$ebitdaH1 = 651.77
$depreciationH1 = 171.71
$profitBeforeTaxH1 = 480.28
$incomeTaxH1 = 99.64
$capexH1 = 232.90

# 税后FCFF校验：维护资本比例与营运资金增量均为情景假设。
$effectiveTaxRate = $incomeTaxH1/$profitBeforeTaxH1
$ebitH1 = $ebitdaH1-$depreciationH1
$maintenanceCapexRatio = 0.60
$maintenanceCapexH1 = $capexH1*$maintenanceCapexRatio
$workingCapitalIncreaseH1 = 0.0
$fcffH1 = $ebitH1*(1-$effectiveTaxRate)+$depreciationH1-$maintenanceCapexH1-$workingCapitalIncreaseH1
$fcffAnnualised = $fcffH1*2

# 6月资产基础，已知已付末期股息扣一次。
$basicNetDebt = 402.33
$paidDividend = 223.40
$nciBook = 996.08
$associatesBook = 831.98
$leasePresented = 12.13
$leaseLongTermClass = 43.58
$miningRightsPayable = 180.80
$reclamation = 149.82
$baseBridgeDeduction = $basicNetDebt+$paidDividend+$nciBook+$leasePresented+$leaseLongTermClass+$miningRightsPayable+$reclamation-$associatesBook

$cases = @(
    [pscustomobject]@{Name='保守'; EBITDA=1150; Multiple=4.8; Bridge=1250; DPS=1.70; Yield=0.065},
    [pscustomobject]@{Name='基准'; EBITDA=($ebitdaH1*2); Multiple=5.4; Bridge=$baseBridgeDeduction; DPS=2.00; Yield=0.055},
    [pscustomobject]@{Name='乐观'; EBITDA=1450; Multiple=6.0; Bridge=1050; DPS=2.20; Yield=0.048}
)

$results = foreach($c in $cases) {
    $ev = $c.EBITDA*$c.Multiple
    $evValue = ($ev-$c.Bridge)/$shares
    $dividendValue = $c.DPS/$c.Yield
    $weighted = $evValue*0.70+$dividendValue*0.30
    [pscustomobject]@{
        Scenario=$c.Name
        EBITDA=$c.EBITDA
        EVMultiple=$c.Multiple
        EnterpriseValue=$ev
        EquityBridgeDeduction=$c.Bridge
        EVValuePerShare=$evValue
        DividendValuePerShare=$dividendValue
        WeightedValuePerShare=$weighted
    }
}

$bridgeSensitivity = foreach($leaseExtra in 0,43.58) {
    foreach($associateFactor in 0.8,1.0,1.2) {
        $bridge = $basicNetDebt+$paidDividend+$nciBook+$leasePresented+$leaseExtra+$miningRightsPayable+$reclamation-$associatesBook*$associateFactor
        [pscustomobject]@{
            ExtraLease=$leaseExtra
            AssociateBookFactor=$associateFactor
            BridgeDeduction=$bridge
            EVValuePerShare=(($ebitdaH1*2)*5.4-$bridge)/$shares
        }
    }
}

$baseUnrounded = ($results | Where-Object Scenario -eq '基准').WeightedValuePerShare
$targetStored = [math]::Round($baseUnrounded,1)
$certainty = 0.42
# 机械买入价直接使用未舍入目标，最后统一存储到一位小数。
$buyUnrounded = $baseUnrounded*(0.68+0.14*$certainty)

[pscustomobject]@{
    Version='final-low-certainty'
    EffectiveTaxRate=$effectiveTaxRate
    EBITH1=$ebitH1
    MaintenanceCapexRatio=$maintenanceCapexRatio
    MaintenanceCapexH1=$maintenanceCapexH1
    FCFFH1=$fcffH1
    FCFFAnnualised=$fcffAnnualised
    BaseBridgeDeduction=$baseBridgeDeduction
    MethodWeights=[pscustomobject]@{NAV=0.0;EV_EBITDA=0.70;DividendYield=0.30;SOTP=0.0}
    Scenarios=$results
    BridgeSensitivity=$bridgeSensitivity
    TargetPriceUnrounded=$baseUnrounded
    TargetPrice=$targetStored
    ValuationCertainty=$certainty
    MechanicalBuyPriceUnrounded=$buyUnrounded
    MechanicalBuyPrice=[math]::Round($buyUnrounded,1)
} | ConvertTo-Json -Depth 6

