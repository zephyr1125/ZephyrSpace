param(
    [double]$Shares = 216.89434304,
    [double]$Price = 47.28
)

# 所有金额均为亿元；股本为亿股；每股价值自然得到元/股。
$cash = 516.73
$timeDeposits = 657.22
$borrowings = 1576.28
$associatesBook = 831.98
$minorityBook = 996.08
$leasePresented = 12.13
$leaseInLongTermLiabilities = 43.58
$miningRightsPayable = 180.80
$reclamation = 149.82
$approvedDividend = 223.40
$ebitdaH1 = 651.77
$unusedFacilities = 1079.00
$netCurrentLiabilities = 316.19

$basicNetDebt = $borrowings - $cash - $timeDeposits
$priceImpliedEquity = $Shares * $Price

# 6月30日资产负债表含应付股利。已批准末期股息在批准报告时已支付，
# 但从6月期点到9月行情缺完整现金桥，故不把223.40亿元机械追加到净债务。
# 以下EV只是“未完成权益桥的条件结果”。
# 尚待调整/裁定项目：联营权益公允价值、已付股息的估值日现金桥、
# 表列租赁负债与长期负债内租赁类项目、矿权应付款、复垦义务。
# 这些项目可能进入资产加回、类债扣减或NAV现金流，当前不得机械全加全减。
$conditionalIncompleteEquityBridgeEV = $priceImpliedEquity + $basicNetDebt + $minorityBook
$annualisedEbitda = $ebitdaH1 * 2
$evEbitda = $conditionalIncompleteEquityBridgeEV / $annualisedEbitda

$evScenarios = @(
    [pscustomobject]@{ Scenario='保守'; EBITDA=1150; Multiple=6.5 },
    [pscustomobject]@{ Scenario='基准'; EBITDA=1300; Multiple=7.5 },
    [pscustomobject]@{ Scenario='乐观'; EBITDA=1450; Multiple=8.5 }
) | ForEach-Object {
    $enterpriseValue = $_.EBITDA * $_.Multiple
    [pscustomobject]@{
        Scenario = $_.Scenario
        EBITDA = $_.EBITDA
        Multiple = $_.Multiple
        EnterpriseValue = [math]::Round($enterpriseValue,2)
        EquityPerShareBeforeAssociatesFairValueAdjustment = [math]::Round(($enterpriseValue-$basicNetDebt-$minorityBook)/$Shares,2)
    }
}

$dividendScenarios = @(
    [pscustomobject]@{ Scenario='保守'; DPS=1.70; Yield=0.065 },
    [pscustomobject]@{ Scenario='基准'; DPS=2.00; Yield=0.055 },
    [pscustomobject]@{ Scenario='乐观'; DPS=2.20; Yield=0.048 }
) | ForEach-Object {
    [pscustomobject]@{
        Scenario = $_.Scenario
        DPS = $_.DPS
        RequiredYield = $_.Yield
        IndicatedPrice = [math]::Round($_.DPS/$_.Yield,2)
    }
}

# NAV只做参数化演示，不形成正式权重。
$navDemo = foreach($rent in 40,65,90) {
    foreach($factor in 0.45,0.55,0.65) {
        [pscustomobject]@{
            RentPerTonne = $rent
            RealisationFactor = $factor
            CoalValue = [math]::Round(225.9*$rent*$factor,2)
        }
    }
}

[pscustomobject]@{
    BasicNetDebt = [math]::Round($basicNetDebt,2)
    PriceImpliedEquity = [math]::Round($priceImpliedEquity,2)
    ConditionalEV_IncompleteEquityBridge = [math]::Round($conditionalIncompleteEquityBridgeEV,2)
    ConditionalEVWarning = '未完成权益桥的条件结果；联营、已付股息、两类租赁、矿权应付款和复垦义务待调整'
    AnnualisedEBITDA = [math]::Round($annualisedEbitda,2)
    PriceImpliedEV_EBITDA = [math]::Round($evEbitda,2)
    AssociatesBook = $associatesBook
    MinorityBook = $minorityBook
    LeasePresented = $leasePresented
    LeaseInLongTermLiabilities = $leaseInLongTermLiabilities
    MiningRightsPayable = $miningRightsPayable
    Reclamation = $reclamation
    ApprovedDividend = $approvedDividend
    NetCurrentLiabilities = $netCurrentLiabilities
    UnusedFacilities = $unusedFacilities
    FormalTargetPrice = $null
    ValuationCertainty = $null
    MechanicalBuyPrice = $null
    EVScenarios = $evScenarios
    DividendScenarios = $dividendScenarios
    NAVParameterDemo = $navDemo
} | ConvertTo-Json -Depth 6
