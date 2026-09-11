param()

# 单位：金额为人民币亿元，股本为亿股，每股金额为元。
$shares = 216.89434304
$ebitdaH1 = 651.77
$depreciationH1 = 171.71
$pbtH1 = 480.28
$incomeTaxH1 = 99.64
$actualCapexH1 = 232.90
$cashInterestH1 = 27.19
$parentProfitH1 = 310.54
$totalProfitH1 = 380.64
$nciProfitShare = 1-$parentProfitH1/$totalProfitH1

# 资产基础权益桥：已付股息扣一次；养老金37.91亿元作为类债扣减。
$basicNetDebt = 402.33
$paidDividend = 223.40
$nciBook = 996.08
$associatesBook = 831.98
$leasePresented = 12.13
$leaseLongTermClass = 43.58
$miningRightsPayable = 180.80
$reclamation = 149.82
$pension = 37.91
$baseBridge = $basicNetDebt+$paidDividend+$nciBook+$leasePresented+$leaseLongTermClass+$miningRightsPayable+$reclamation+$pension-$associatesBook

$taxRate = $incomeTaxH1/$pbtH1
$ebitH1 = $ebitdaH1-$depreciationH1

$cases = @(
    [pscustomobject]@{Name='保守'; MaintenanceRatio=1.00; WorkingCapital=50; LeasePrincipal=12; NCIShare=0.22; NecessaryRetention=30; EVEBITDA=1150; EVMultiple=4.8; EVBridge=1325; RequiredYield=0.070},
    [pscustomobject]@{Name='基准'; MaintenanceRatio=0.80; WorkingCapital=20; LeasePrincipal=8; NCIShare=$nciProfitShare; NecessaryRetention=20; EVEBITDA=($ebitdaH1*2); EVMultiple=5.4; EVBridge=$baseBridge; RequiredYield=0.060},
    [pscustomobject]@{Name='乐观'; MaintenanceRatio=0.60; WorkingCapital=0; LeasePrincipal=5; NCIShare=0.147; NecessaryRetention=10; EVEBITDA=1450; EVMultiple=6.0; EVBridge=1085; RequiredYield=0.050}
)

$results = foreach($c in $cases) {
    $maintenance = $actualCapexH1*$c.MaintenanceRatio
    $fcff = $ebitH1*(1-$taxRate)+$depreciationH1-$maintenance-$c.WorkingCapital
    # 中报披露H1实际租赁本金3.77亿元，并另列租赁利息0.13亿元。
    # 5/8/12亿元是覆盖时点及租赁类偿付不确定性的正常化压力情景，不是实际支出。
    # FCFF后扣全额现金利息但未加回税盾，并忽略净借款，故结果是偏保守的归母可分现金代理，不是标准精确FCFE恒等式。
    $cashBeforeNCI = $fcff-$cashInterestH1-$c.LeasePrincipal
    # NCI使用利润归属比例代理现金归属，不能称实际少数股东分配。
    $parentCashBeforeRetention = $cashBeforeNCI*(1-$c.NCIShare)
    $parentDistributableH1 = $parentCashBeforeRetention-$c.NecessaryRetention
    $annualDistributable = $parentDistributableH1*2
    $sustainableDPS = $annualDistributable/$shares
    $dividendValue = $sustainableDPS/$c.RequiredYield

    $ev = $c.EVEBITDA*$c.EVMultiple
    $evValue = ($ev-$c.EVBridge)/$shares
    # 股息法经承载桥后保留20%，EV为80%。
    $weighted = $evValue*0.80+$dividendValue*0.20
    [pscustomobject]@{
        Scenario=$c.Name
        MaintenanceRatio=$c.MaintenanceRatio
        MaintenanceCapexH1=$maintenance
        WorkingCapitalProxyH1=$c.WorkingCapital
        FCFFH1=$fcff
        CashInterestH1=$cashInterestH1
        LeasePrincipalProxyH1=$c.LeasePrincipal
        NCIShareProxy=$c.NCIShare
        NecessaryRetentionH1=$c.NecessaryRetention
        ParentDistributableCashH1=$parentDistributableH1
        AnnualisedParentDistributableCash=$annualDistributable
        SustainableDPS=$sustainableDPS
        DividendValuePerShare=$dividendValue
        EVValuePerShare=$evValue
        WeightedValuePerShare=$weighted
    }
}

$nciSensitivity = foreach($factor in 0.8,1.0,1.2) {
    $bridge = $baseBridge-$nciBook+$nciBook*$factor
    [pscustomobject]@{
        NCIBookFactor=$factor
        NCIValue=$nciBook*$factor
        Bridge=$bridge
        EVValuePerShare=(($ebitdaH1*2)*5.4-$bridge)/$shares
    }
}

$maintenanceSensitivity = foreach($ratio in 0.60,0.80,1.00) {
    $maintenance = $actualCapexH1*$ratio
    $fcff = $ebitH1*(1-$taxRate)+$depreciationH1-$maintenance-20
    $parentCash = (($fcff-$cashInterestH1-8)*(1-$nciProfitShare)-20)*2
    [pscustomobject]@{
        MaintenanceRatio=$ratio
        MaintenanceCapexH1=$maintenance
        AnnualisedParentDistributableCash=$parentCash
        SustainableDPS=$parentCash/$shares
    }
}

$base = $results | Where-Object Scenario -eq '基准'
$targetUnrounded = $base.WeightedValuePerShare
$certainty = 0.40
$buyUnrounded = $targetUnrounded*(0.68+0.14*$certainty)

[pscustomobject]@{
    Version='fcfe-final'
    EffectiveTaxRate=$taxRate
    NCIProfitShareProxy=$nciProfitShare
    PensionDebtLike=$pension
    BaseEquityBridge=$baseBridge
    MethodWeights=[pscustomobject]@{EV_EBITDA=0.80;DividendYield=0.20;NAV=0.0;SOTP=0.0}
    Scenarios=$results
    NCISensitivity=$nciSensitivity
    MaintenanceSensitivity=$maintenanceSensitivity
    TargetPriceUnrounded=$targetUnrounded
    TargetPrice=[math]::Round($targetUnrounded,1)
    ValuationCertainty=$certainty
    MechanicalBuyPriceUnrounded=$buyUnrounded
    MechanicalBuyPrice=[math]::Round($buyUnrounded,1)
} | ConvertTo-Json -Depth 6
