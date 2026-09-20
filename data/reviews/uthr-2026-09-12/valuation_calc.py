"""UTHR冻结初稿审计算术；输出不得视为正式估值参数。"""

SHARES = 46.5
NET_CASH = 2662.3


def dcf(fcf, growth, discount, terminal_growth):
    """五年FCFE近似模型；终值采用永续增长。"""
    value = 0.0
    cash = fcf
    for year in range(1, 6):
        cash *= 1 + growth
        value += cash / (1 + discount) ** year
    terminal = cash * (1 + terminal_growth) / (discount - terminal_growth)
    return (value + terminal / (1 + discount) ** 5 + NET_CASH) / SHARES


dcf_cases = {
    "保守": dcf(900, 0.04, 0.105, 0.020),
    "基准": dcf(1040, 0.08, 0.095, 0.025),
    "乐观": dcf(1120, 0.12, 0.085, 0.030),
}
pe_cases = {"保守": 28 * 13, "基准": 33 * 15, "乐观": 38 * 17}
combined = {k: 0.55 * dcf_cases[k] + 0.45 * pe_cases[k] for k in dcf_cases}
certainty = 0.58
buy_price = combined["基准"] * (0.68 + 0.14 * certainty)

if __name__ == "__main__":
    print("状态：仅审计已撤销冻结试算；正式target/certainty/buy均为null")
    for name in dcf_cases:
        print(name, round(dcf_cases[name], 2), round(pe_cases[name], 2), round(combined[name], 2))
    print("withdrawn_trial_center", round(combined["基准"], 2))
    print("withdrawn_trial_buy", round(buy_price, 2))
    print("formal_target=None")
    print("formal_certainty=None")
    print("formal_buy=None")
    assert round(combined["基准"], 2) == 481.38
    assert round(buy_price, 2) == 366.43
