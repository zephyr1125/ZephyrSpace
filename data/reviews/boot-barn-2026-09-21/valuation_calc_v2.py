import json
from pathlib import Path

root = Path(__file__).parent
data = json.loads((root / "valuation-input-v2.json").read_text(encoding="utf-8"))
shares = data["shares_m"]


def first_year_fcfe(params):
    net_income = params["eps"] * shares
    ocf = net_income * params["cash_conversion"]
    fcfe = ocf - params["gross_capex_m"] - params["sbc_m"] - params["finance_lease_principal_m"]
    return {"net_income_m": net_income, "ocf_m": ocf, "fcfe_m": fcfe}


def cashflows(params):
    first = first_year_fcfe(params)["fcfe_m"]
    values = [first]
    for year in range(2, 6):
        growth = params["growth_y2_y3"] if year <= 3 else params["growth_y4_y5"]
        values.append(values[-1] * (1 + growth))
    return values


def dcf_value(cash, ke, terminal_g):
    pv_explicit = sum(value / (1 + ke) ** year for year, value in enumerate(cash, 1))
    terminal = cash[-1] * (1 + terminal_g) / (ke - terminal_g)
    return (pv_explicit + terminal / (1 + ke) ** 5) / shares


pe = {name: params["eps"] * params["multiple"] for name, params in data["pe"].items()}
bridges = {name: first_year_fcfe(params) for name, params in data["fcfe_dcf"].items()}
paths = {name: cashflows(params) for name, params in data["fcfe_dcf"].items()}
dcf = {
    name: dcf_value(paths[name], params["ke"], params["terminal_g"])
    for name, params in data["fcfe_dcf"].items()
}
weighted = {
    name: pe[name] * data["weights"]["pe"] + dcf[name] * data["weights"]["fcfe_dcf"]
    for name in ("bear", "base", "bull")
}

base_params = data["fcfe_dcf"]["base"]
base_path = paths["base"]
dcf_sensitivity = []
for ke in (0.09, 0.0975, 0.105):
    dcf_sensitivity.append([dcf_value(base_path, ke, g) for g in (0.02, 0.025, 0.03)])

pe_sensitivity = []
for multiple in (12.0, 15.0, 18.0):
    pe_sensitivity.append([eps * multiple for eps in (8.0, 8.555, 8.9)])

lo, hi = -0.02, base_params["ke"] - 0.0001
for _ in range(200):
    mid = (lo + hi) / 2
    if dcf_value(base_path, base_params["ke"], mid) < data["market_price"]:
        lo = mid
    else:
        hi = mid

target = weighted["base"]
output = {
    "bridges": bridges,
    "cashflow_paths_m": paths,
    "models": {"pe": pe, "fcfe_dcf": dcf},
    "weighted": weighted,
    "target_price": target,
    "certainty": data["certainty"],
    "buy_price": target * (0.68 + 0.14 * data["certainty"]),
    "dcf_sensitivity": {"x": "terminal_g", "x_values": [0.02, 0.025, 0.03], "y": "ke", "y_values": [0.09, 0.0975, 0.105], "values": dcf_sensitivity},
    "pe_sensitivity": {"x": "eps", "x_values": [8.0, 8.555, 8.9], "y": "multiple", "y_values": [12.0, 15.0, 18.0], "values": pe_sensitivity},
    "reverse": {"market_price": data["market_price"], "ke": base_params["ke"], "implied_terminal_g": (lo + hi) / 2, "fixed_cashflow_path_m": base_path}
}
(root / "valuation-output-v2.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(output, ensure_ascii=False, indent=2))
