import json
from pathlib import Path

root = Path(__file__).parent
base = json.loads((root / "repair-v2" / "workpaper.json").read_text(encoding="utf-8"))
inputs = json.loads((root / "valuation-input-v2.json").read_text(encoding="utf-8"))
outputs = json.loads((root / "valuation-output-v2.json").read_text(encoding="utf-8"))


def meta(unit, date, kind, refs):
    return {"unit": unit, "date": date, "kind": kind, "evidence_refs": refs}


pe_scenarios = {}
for name in ("bear", "base", "bull"):
    p = inputs["pe"][name]
    pe_scenarios[name] = {
        "inputs": {"eps": p["eps"], "multiple": p["multiple"]},
        "input_meta": {
            "eps": meta("USD/share; FY2027 normalized", "FY2027", "assumption", ["BOOT-VAL-F-GUIDANCE-001"]),
            "multiple": meta("x forward normalized EPS", "2026-09-21", "assumption", ["BOOT-VAL-F-MARKET-001"]),
        },
        "value": outputs["models"]["pe"][name],
    }

dcf_scenarios = {}
formula = "fcfe1/(1+ke)+fcfe2/(1+ke)**2+fcfe3/(1+ke)**3+fcfe4/(1+ke)**4+fcfe5/(1+ke)**5+(fcfe5*(1+terminal_g)/(ke-terminal_g))/(1+ke)**5"
for name in ("bear", "base", "bull"):
    p = inputs["fcfe_dcf"][name]
    path = outputs["cashflow_paths_m"][name]
    scenario_inputs = {f"fcfe{i}": value / inputs["shares_m"] for i, value in enumerate(path, 1)}
    scenario_inputs.update({"ke": p["ke"], "terminal_g": p["terminal_g"]})
    scenario_meta = {
        f"fcfe{i}": meta("USD/share owner FCFE", f"FY{2026+i}", "forecast", ["BOOT-VAL-C-FY27-FCFE-BRIDGE"])
        for i in range(1, 6)
    }
    scenario_meta["ke"] = meta("decimal", "2026-09-21", "assumption", ["BOOT-VAL-F-MARKET-001"])
    scenario_meta["terminal_g"] = meta("decimal", "terminal after FY2031", "assumption", ["BOOT-VAL-F-OWNERCASH-001"])
    dcf_scenarios[name] = {"inputs": scenario_inputs, "input_meta": scenario_meta, "value": outputs["models"]["fcfe_dcf"][name]}

base["valuation"] = {
    "status": "candidate_pending_review",
    "reason": "评分底稿已闭合后形成的正式估值候选；参数、权重和估值结论仍待两路全文审核及裁决。",
    "currency": "USD",
    "models": [
        {
            "id": "pe_forward_normalized",
            "weight": inputs["weights"]["pe"],
            "basis": "FY2027剔除关税退款后的正常化EPS乘前瞻倍数；倍数反映专业零售盈利持续性和增长，但与DCF共享盈利预期。",
            "shared_assumptions": ["FY2027正常化盈利", "扩店与同店增长可持续性"],
            "output_currency": "USD",
            "output_unit": "per_share",
            "formula": "eps * multiple",
            "scenarios": pe_scenarios,
            "sensitivity": outputs["pe_sensitivity"],
        },
        {
            "id": "fcfe_owner_cash_dcf",
            "weight": inputs["weights"]["fcfe_dcf"],
            "basis": "以净利润、现金转化、毛Capex、SBC及融资租赁本金桥接的owner FCFE；保留扩店再投资，不把持续SBC视为免费融资。",
            "shared_assumptions": ["FY2027正常化盈利", "扩店与同店增长可持续性"],
            "output_currency": "USD",
            "output_unit": "per_share",
            "formula": formula,
            "scenarios": dcf_scenarios,
            "sensitivity": outputs["dcf_sensitivity"],
        },
    ],
    "weighted": outputs["weighted"],
    "target_price": outputs["target_price"],
    "certainty": outputs["certainty"],
    "certainty_reason": "现金流受库存和扩店Capex影响较大，维持/扩张Capex及成熟门店cohort回报未披露；两模型基准值差异约61.6美元，当前价格隐含的终端增长偏高，因此确定性取0.52。",
    "buy_price": outputs["buy_price"],
    "reverse": {
        "weight": 0,
        "variable": "terminal_g",
        "implied_value": outputs["reverse"]["implied_terminal_g"],
        "formula": formula,
        "inputs": {
            "fcfe1": outputs["reverse"]["fixed_cashflow_path_m"][0] / inputs["shares_m"],
            "fcfe2": outputs["reverse"]["fixed_cashflow_path_m"][1] / inputs["shares_m"],
            "fcfe3": outputs["reverse"]["fixed_cashflow_path_m"][2] / inputs["shares_m"],
            "fcfe4": outputs["reverse"]["fixed_cashflow_path_m"][3] / inputs["shares_m"],
            "fcfe5": outputs["reverse"]["fixed_cashflow_path_m"][4] / inputs["shares_m"],
            "ke": outputs["reverse"]["ke"],
            "terminal_g": outputs["reverse"]["implied_terminal_g"],
        },
        "market_price": inputs["market_price"],
        "assumptions": "固定基准五年owner FCFE路径及9.75%权益成本，只反解终值增长；结果仅是市场隐含假设。",
        "evidence_refs": ["BOOT-VAL-F-MARKET-001", "BOOT-VAL-C-FY27-FCFE-BRIDGE"],
    },
}

base["bridges"] = [
    {
        "id": "VAL-BRIDGE-FY26-OWNER-FCFE",
        "date": "FY2026",
        "unit": "USD million",
        "scope": "actual owner FCFE",
        "start": 304.903,
        "items": [
            {"economic_id": "cash_capex", "signed_value": -178.561, "evidence_refs": ["BOOT-VAL-F-OWNERCASH-001"]},
            {"economic_id": "sbc_economic_cost", "signed_value": -16.103, "evidence_refs": ["BOOT-VAL-F-OWNERCASH-001"]},
        ],
        "result": 110.239,
    },
]
for name in ("bear", "base", "bull"):
    p = inputs["fcfe_dcf"][name]
    b = outputs["bridges"][name]
    base["bridges"].append({
        "id": f"VAL-BRIDGE-FY27-{name.upper()}",
        "date": "FY2027",
        "unit": "USD million",
        "scope": f"{name} forecast owner FCFE",
        "start": b["net_income_m"],
        "items": [
            {"economic_id": "cash_conversion_adjustment", "signed_value": b["ocf_m"] - b["net_income_m"], "evidence_refs": ["BOOT-VAL-C-FY27-FCFE-BRIDGE"]},
            {"economic_id": "gross_capex", "signed_value": -p["gross_capex_m"], "evidence_refs": ["BOOT-VAL-C-FY27-FCFE-BRIDGE"]},
            {"economic_id": "sbc_economic_cost", "signed_value": -p["sbc_m"], "evidence_refs": ["BOOT-VAL-F-SBCLEASE-001"]},
            {"economic_id": "finance_lease_principal", "signed_value": -p["finance_lease_principal_m"], "evidence_refs": ["BOOT-VAL-F-SBCLEASE-001"]},
        ],
        "result": b["fcfe_m"],
    })
base.pop("bridges_not_applicable", None)
base["score_state"] = "approved"
base["research_state"] = "pending"
base["publish_allowed"] = False

(root / "workpaper-v2.json").write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(root / "workpaper-v2.json")
