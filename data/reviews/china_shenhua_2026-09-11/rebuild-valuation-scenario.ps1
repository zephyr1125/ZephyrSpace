param(
    [double]$Shares = 216.89434304,
    [double]$DiscountRate = 0.10,
    [int]$ExplicitYears = 20
)

# 单位：金额为亿元，煤量为百万吨，价格/成本为元/吨，每股价值为元。
$basicNetDebt = 402.33
$minorityBook = 996.08
$associatesBook = 831.98
$leasePresented = 12.13
$leaseLongTermClass = 43.58
$miningRightsPayable = 180.80
$reclamation = 149.82

# 条件权益桥：已付末期股息不重复扣减；两类租赁均保守列为类债。
$equityBridgeDeduction = $basicNetDebt + $minorityBook + $leasePresented + $leaseLongTermClass + $miningRightsPayable + $reclamation - $associatesBook
$annuityFactor = (1-[math]::Pow(1+$DiscountRate,-$ExplicitYears))/$DiscountRate

$scenarios = @(
    [pscustomobject]@{Name='保守'; CoalPrice=340; Volume=450; AllInCashCost=300; NonCoalPBT=240; NonCoalMultiple=5.5; EBITDA=1150; EVMultiple=4.8; DPS=1.70; DividendYield=0.065},
    [pscustomobject]@{Name='基准'; CoalPrice=397; Volume=500; AllInCashCost=280; NonCoalPBT=288; NonCoalMultiple=6.5; EBITDA=1300; EVMultiple=5.5; DPS=2.00; DividendYield=0.055},
    [pscustomobject]@{Name='乐观'; CoalPrice=460; Volume=530; AllInCashCost=265; NonCoalPBT=330; NonCoalMultiple=7.5; EBITDA=1450; EVMultiple=6.2; DPS=2.20; DividendYield=0.048}
)

$results = foreach($s in $scenarios) {
    # 1百万吨×1元/吨=0.01亿元。
    $coalAnnualCash = ($s.CoalPrice-$s.AllInCashCost)*$s.Volume*0.01
    $coalPV = $coalAnnualCash*$annuityFactor
    # 非煤税前利润来自2025分部利润结构，税后率75%为情景假设。
    $nonCoalEquity = $s.NonCoalPBT*0.75*$s.NonCoalMultiple
    $navEquity = $coalPV+$nonCoalEquity-$equityBridgeDeduction
    $navPerShare = $navEquity/$Shares

    # EBITDA为集团口径；联营结果已剔除，故权益桥加回联营账面值。
    $evEquity = $s.EBITDA*$s.EVMultiple-$equityBridgeDeduction
    $evPerShare = $evEquity/$Shares
    $dividendPrice = $s.DPS/$s.DividendYield

    # 三类方法的权重均固定，避免事后迁就目标价。
    $weighted = $navPerShare*0.45+$evPerShare*0.35+$dividendPrice*0.20
    [pscustomobject]@{
        Scenario=$s.Name
        CoalPrice=$s.CoalPrice
        VolumeMt=$s.Volume
        AllInCashCost=$s.AllInCashCost
        CoalAnnualCash=[math]::Round($coalAnnualCash,2)
        CoalPV=[math]::Round($coalPV,2)
        NonCoalEquity=[math]::Round($nonCoalEquity,2)
        NAVPerShare=[math]::Round($navPerShare,2)
        EVPerShare=[math]::Round($evPerShare,2)
        DividendPrice=[math]::Round($dividendPrice,2)
        WeightedPerShare=[math]::Round($weighted,2)
    }
}

$sensitivity = foreach($priceCase in 340,397,460) {
    foreach($costCase in 260,280,300) {
        $annualCash = ($priceCase-$costCase)*500*0.01
        $valuePerShare = ($annualCash*$annuityFactor+1404-$equityBridgeDeduction)/$Shares
        [pscustomobject]@{
            CoalPrice=$priceCase
            AllInCashCost=$costCase
            NAVPerShare=[math]::Round($valuePerShare,2)
        }
    }
}

$baseTarget = ($results | Where-Object Scenario -eq '基准').WeightedPerShare
$certainty = 0.38
$buyPrice = $baseTarget*(0.68+0.14*$certainty)

[pscustomobject]@{
    Version='scenario'
    DiscountRate=$DiscountRate
    ExplicitYears=$ExplicitYears
    AnnuityFactor=[math]::Round($annuityFactor,6)
    EquityBridgeDeduction=[math]::Round($equityBridgeDeduction,2)
    MethodWeights=[pscustomobject]@{NAV=0.45;EV_EBITDA=0.35;DividendYield=0.20}
    Scenarios=$results
    NAVSensitivity=$sensitivity
    TargetPrice=[math]::Round($baseTarget,1)
    ValuationCertainty=$certainty
    MechanicalBuyPrice=[math]::Round($buyPrice,1)
} | ConvertTo-Json -Depth 6
