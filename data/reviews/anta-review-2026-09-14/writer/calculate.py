"""安踏体育2026-09-14裁决参数复算与报告自检。"""

from pathlib import Path

FX = 1.169165015220642
SHARES = 2.7966533
PUMA_COST = 12.277638425
TARGET = 80.47
CERTAINTY = 0.60

SCENARIOS = [
    dict(name="保守", earnings=14, pe=11, ocf=23, interest=1.7, capex=3.6,
         lease=5.4, sbc=0.4, nci=0.18, r=0.11, g=0.02, associate=0.75, puma=0.7),
    dict(name="基准", earnings=15, pe=13, ocf=24, interest=1.6, capex=3.3,
         lease=5.2, sbc=0.35, nci=0.165, r=0.10, g=0.02, associate=1.0, puma=1.0),
    dict(name="乐观", earnings=16, pe=15, ocf=25, interest=1.5, capex=3.1,
         lease=5.0, sbc=0.3, nci=0.15, r=0.09, g=0.02, associate=1.25, puma=1.1),
]


def calculate(row):
    tax = 0.294
    finance_cost = 0.5
    tax_unlevering = tax * (row["interest"] - finance_cost)
    cash = (row["ocf"] - row["interest"] + tax_unlevering - row["capex"]
            - row["lease"] - row["sbc"]) * (1 - row["nci"])
    net_cash = (62.601 - 0.290) * (1 - row["nci"]) - 23.488 - 1.275
    associates = 17.911 * row["associate"]
    puma = PUMA_COST * (row["puma"] - 1)
    pe_price = (row["earnings"] * row["pe"] + puma) / SHARES * FX
    cash_price = (cash / (row["r"] - row["g"]) + net_cash + associates + puma) / SHARES * FX
    return cash, net_cash, associates, puma, pe_price, cash_price, (pe_price + cash_price) / 2


def main():
    results = []
    for row in SCENARIOS:
        result = calculate(row)
        results.append(result)
        print(row["name"], *(f"{value:.6f}" for value in result))

    assert round(results[1][6], 2) == TARGET
    buy = round(TARGET * (0.68 + 0.14 * CERTAINTY), 2)
    assert buy == 61.48
    assert sum([9, 16, 14, 11, 16, 12]) == 78
    assert sum([17, 21, 13, 12, 6, 7, 4]) == 80
    assert 78 + 80 == 158
    assert round(15.596 - 1.579 - 2.090, 3) == 11.927
    assert round(11.927 - 0.198, 3) == 11.729
    assert round(13.588 - 1.203, 3) == 12.385
    assert round(9.487 - 1.549 - 0.708, 3) == 7.230

    market_value = 72.45 / FX * SHARES
    base = SCENARIOS[1]
    cash, net_cash, associates, puma, *_ = results[1]
    implied_g = base["r"] - cash / (market_value - net_cash - associates - puma)
    assert round(implied_g * 100, 5) == 0.95849

    # NCI压力必须同时作用于经营现金U和净金融现金NC。
    nci_expected = {0.10: 85.82896030662913, 0.165: 79.42331878721785, 0.25: 71.04671064644927}
    for nci, expected in nci_expected.items():
        row = dict(SCENARIOS[1], nci=nci)
        price = calculate(row)[5]
        assert abs(price - expected) < 1e-9

    # 固定评分分母的定向文本检查，防止只验加总却写错量表。
    deep_text = Path("深度分析/安踏体育 深度分析 78 2026-09-14.md").read_text(encoding="utf-8")
    score_labels = [
        "A1 公司起源与创始基因（2/3）", "A2 控制权稳定性（3/3）", "A3 资本运作清洁度（4/4）",
        "B0 早期商业模式溯源（2/2）", "B1 收入结构与品牌矩阵（4/4）",
        "B2 盈利机制与复购（3/3）", "B3 定价权与渠道（4/6）", "B4 可持续性（3/5）",
        "C1 市场地位（5/6）", "C2 渠道与供应链（4/5）", "C3+C4 品牌与整合能力（5/9）",
        "| D1战略连贯 | 4/4 |", "| D2目标兑现 | 3/5 |", "| D3外部适配 | 2/3 |", "| D5组织支撑 | 2/3 |",
        "E1 ROE与杜邦（4/5）", "E2 现金流（5/5）", "E3 增长质量（2/3）",
        "E4资本结构（1/2）", "E5资产质量与会计边界（2/2）", "E5.5披露稳健性（2/3）",
        "| F1团队与激励 | 4/5 |", "| F2股东回报 | 4/5 |",
        "| F2.5资本配置 | 2/2 |", "| F3关联与监督 | 2/3 |",
    ]
    for label in score_labels:
        assert label in deep_text, f"固定评分分母缺失：{label}"

    report_paths = [
        Path("深度分析/安踏体育 深度分析 78 2026-09-14.md"),
        Path("管理层档案/安踏体育 管理层档案 80 2026-09-14.md"),
        Path("估值分析/安踏体育 估值分析 2026-09-14.md"),
    ]
    minimum_lines = [150, 150, 100]
    # 历史值可出现在明确的版本对比表，因此这里只拦截已裁决无效的事实或方法表述。
    forbidden = ["家族CFO", "狼爪炸山", "全年全部兑现", "无造假指控", "现金无隐藏风险", "DDM保底"]
    for path, minimum in zip(report_paths, minimum_lines):
        report_text = path.read_text(encoding="utf-8")
        lines = len(report_text.splitlines())
        assert lines >= minimum, f"{path}: {lines} < {minimum}"
        for phrase in forbidden:
            assert phrase not in report_text, f"{path}: 残留禁用表述 {phrase}"
        print(f"PASS {path} lines={lines}")
    print(f"PASS target={TARGET:.2f} buy={buy:.2f} implied_g={implied_g:.8%}")


if __name__ == "__main__":
    main()
