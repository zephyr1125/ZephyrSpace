"""AEO 三件套作者机械复算脚本。

仅重算报告内的算术、估值和敏感性，不抓取数据、不修改报告。
"""

SHARES = 172.0
TARGET_PRICE = None
CERTAINTY = None


def dcf_per_share(start_fcf, growth_1_5, terminal_growth, cost_of_equity):
    """计算五年显式期加永续终值的每股股权价值。"""
    explicit_pv = sum(
        start_fcf * (1 + growth_1_5) ** year / (1 + cost_of_equity) ** year
        for year in range(1, 6)
    )
    year5_fcf = start_fcf * (1 + growth_1_5) ** 5
    terminal_value = year5_fcf * (1 + terminal_growth) / (
        cost_of_equity - terminal_growth
    )
    terminal_pv = terminal_value / (1 + cost_of_equity) ** 5
    return (explicit_pv + terminal_pv) / SHARES


def main():
    scores = {
        "deep": [7, 14, 12, 12, 14, 9],
        "management": [15, 17, 11, 11, 8, 6, 3],
    }
    conditional_eps = 285 / SHARES
    conditional_pe = conditional_eps * 12
    conditional_fcf_yield = 275 / 0.085 / SHARES
    conditional_ev = ((384 + 215) * 5.3 + 92.954) / SHARES
    conditional_sotp = {
        "bear": (3300 * 0.20 + 2140 * 0.75 + 0) / SHARES,
        "base": (3300 * 0.30 + 2140 * 1.10 + 150) / SHARES,
        "bull": (3300 * 0.40 + 2140 * 1.45 + 250) / SHARES,
    }

    print(f"deep_score={sum(scores['deep'])}")
    print(f"management_score={sum(scores['management'])}")
    print(f"target_price={TARGET_PRICE}")
    print(f"valuation_certainty={CERTAINTY}")
    print("mechanical_buy_price=None")
    print(f"conditional_eps={conditional_eps:.5f}")
    print(f"conditional_pe_value={conditional_pe:.5f}")
    print(f"conditional_fcf_yield_value={conditional_fcf_yield:.5f}")
    print(f"conditional_ev_value={conditional_ev:.5f}")
    print("conditional_sotp=" + ", ".join(
        f"{name}:{value:.5f}" for name, value in conditional_sotp.items()
    ))
    print("dcf_scenarios=")
    scenarios = [
        (220, 0.02, 0.01, 0.115),
        (275, 0.04, 0.02, 0.105),
        (330, 0.06, 0.025, 0.095),
    ]
    for scenario in scenarios:
        print(f"  {scenario}: {dcf_per_share(*scenario):.5f}")
    print("dcf_matrix=")
    for cost in [0.095, 0.10, 0.105, 0.11, 0.115]:
        row = [dcf_per_share(275, 0.04, growth, cost) for growth in [0.01, 0.015, 0.02, 0.025]]
        print(f"  Ke={cost:.3f}: " + ", ".join(f"{value:.2f}" for value in row))


if __name__ == "__main__":
    main()
