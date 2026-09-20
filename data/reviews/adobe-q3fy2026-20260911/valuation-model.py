"""Adobe FY2026 Q3 三件套估值与敏感性机械复算。"""

from __future__ import annotations


SHARES_M = 395.0
ALT_SHARES_M = 400.0
NET_DEBT_M = 6363 - 4359 - 1280
FY26_GAAP_EPS = (18.12 + 18.17) / 2
FY26_NON_GAAP_EPS = (24.45 + 24.50) / 2
CERTAINTY = 0.68
OWNER_EARNINGS_M = (2523 - 85 - 539) * 4
NORMALIZED_EBIT_M = ((26.576 + 26.626) / 2) * 1000 * 0.35


def dcf_per_share(
    owner_earnings_m: float,
    growth_1_5: float,
    growth_6_10: float,
    discount: float,
    terminal_growth: float,
) -> float:
    cashflows = []
    cash = owner_earnings_m
    for year in range(1, 11):
        cash *= 1 + (growth_1_5 if year <= 5 else growth_6_10)
        cashflows.append(cash / ((1 + discount) ** year))
    terminal = cash * (1 + terminal_growth) / (discount - terminal_growth)
    # 权益所有者收益以Ke折现，假设债务滚续且融资成本已嵌入现金流代理，故不再扣净债务。
    equity_value = sum(cashflows) + terminal / ((1 + discount) ** 10)
    return equity_value / SHARES_M


def main() -> None:
    methods = {
        "GAAP_PE": (FY26_GAAP_EPS * 14.0, 0.25),
        "NON_GAAP_PE": (FY26_NON_GAAP_EPS * 11.5, 0.15),
        "EV_EBIT": (((NORMALIZED_EBIT_M * 12.5) - NET_DEBT_M) / SHARES_M, 0.15),
        "SBC_ADJ_OWNER_EARNINGS": (OWNER_EARNINGS_M / 0.07 / SHARES_M, 0.25),
        "DCF": (dcf_per_share(OWNER_EARNINGS_M, 0.07, 0.04, 0.095, 0.025), 0.15),
        "PVGO": ((FY26_GAAP_EPS / 0.095) / (1 - 0.30), 0.05),
    }
    weighted = sum(value * weight for value, weight in methods.values())
    formal_target = 286.0
    mechanical_buy = formal_target * (0.68 + 0.14 * CERTAINTY)
    print(f"shares_m={SHARES_M:.1f} net_debt_m={NET_DEBT_M:.0f}")
    print(f"FY26_GAAP_EPS_mid={FY26_GAAP_EPS:.3f}")
    print(f"FY26_NON_GAAP_EPS_mid={FY26_NON_GAAP_EPS:.3f}")
    print(f"owner_earnings_m={OWNER_EARNINGS_M:.0f} normalized_ebit_m={NORMALIZED_EBIT_M:.2f}")
    for name, (value, weight) in methods.items():
        print(f"{name}: value={value:.2f} weight={weight:.0%} contribution={value*weight:.2f}")
    print(f"weighted_value={weighted:.2f}")
    print(f"mechanical_buy={mechanical_buy:.2f}")
    four_method = sum(methods[name][0] * methods[name][1] for name in ("GAAP_PE", "NON_GAAP_PE", "EV_EBIT", "SBC_ADJ_OWNER_EARNINGS")) / 0.80
    print(f"four_method_ex_dcf_pvgo={four_method:.4f}")
    print("400m share sensitivity for enterprise/cash-flow methods:")
    ev_ebit_400 = (NORMALIZED_EBIT_M * 12.5 - NET_DEBT_M) / ALT_SHARES_M
    owner_400 = OWNER_EARNINGS_M / 0.07 / ALT_SHARES_M
    dcf_395 = methods["DCF"][0]
    dcf_400 = dcf_395 * SHARES_M / ALT_SHARES_M
    print(f"EV_EBIT={ev_ebit_400:.2f} OWNER={owner_400:.2f} DCF={dcf_400:.2f}")
    print("PE sensitivity on FY26 GAAP EPS:")
    for eps in (17.5, FY26_GAAP_EPS, 18.8):
        print(eps, [round(eps * pe, 2) for pe in (11, 13, 15, 17)])
    print("DCF sensitivity (growth1-5 x discount):")
    for g in (0.04, 0.07, 0.10):
        print(g, [round(dcf_per_share(OWNER_EARNINGS_M, g, 0.04, r, 0.025), 2) for r in (0.085, 0.095, 0.105)])


if __name__ == "__main__":
    main()
