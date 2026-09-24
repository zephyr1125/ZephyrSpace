# -*- coding: utf-8 -*-
"""Apply the user's final adjudication (P1/P2) to the REGN workpaper."""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

P = "data/reviews/regn-2026-09-24/writer/workpaper-v1.json"
d = json.load(open(P, encoding="utf-8"))
ci = {i["id"]: i for i in d["scores"]["company"]["items"]}
mi = {i["id"]: i for i in d["scores"]["management"]["items"]}

# ---------- company: corrected facts ----------
ci["B1"]["reason"] = (
    "单一经营分部（公司唯一报告分部），经济实质由两条治疗领域不同的产品线构成。"
    "口径更正：Dupixent 与 Kevzara 由 Sanofi 记账全球销售，Regeneron 在合作收入中确认其利润份额——"
    "合同约定为**美国利润各 50%、美国以外按阶梯 35%–45%**；先前引用的「约 33%」是扣减开发偿还款后"
    "Regeneron 所得占相关药品销售额的比例，不是合同利润分成比例，已更正。"
    "规模：Dupixent FY2025 全球销售 $178.07 亿（+26%），BCG 定位明星；EYLEA + EYLEA HD FY2025 全球 $78.91 亿"
    "（−17.3%），BCG 定位为衰退中的现金牛；Libtayo 全球 $14.52 亿（+19%）。"
    "两条主线合计约占公司经济利益的 70% 以上。"
    "不取 4 分档的理由：(1) 现金牛一侧正在快速衰减（FY2025 −17.3%、Q2 2026 −21%），不构成稳定现金牛；"
    "(2) 免疫学一侧的销售由 Sanofi 记账并主导商业化，Regeneron 不掌握该市场的定价与渠道决策；"
    "(3) 培育中的引擎（Libtayo、Lynozyfic、Pasatru、cemdisiran）规模尚小。"
    "反证已记录：合作商业化同时降低了公司自建全球渠道的成本与风险，是该模式下合理的选择，"
    "故该项扣分针对集中度本身，不针对合作结构。"
)
ci["C2"]["score"] = 5
ci["C2"]["reason"] = (
    "**口径更正（终审 P1）**：原稿以「Regeneron 只取得约 33% 的利润份额」论证公司在商业端只能「喝汤」，该论证不成立——"
    "33% 是扣减开发偿还款后 Regeneron 所得占相关药品销售额的比例，不是合同利润分成比例；"
    "合同实际约定为**美国利润 50/50、美国以外按销售额阶梯 35%–45%**（Q2 2026 10-Q Note 3a）。"
    "按合同口径，Regeneron 是在自有分子上取得接近一半经济利益的**权利方（principal）**，而非单纯的参与者。"
    "正面证据：公司是分子的原创方（VelocImmune 平台），美国 EYLEA/EYLEA HD 与全球 Libtayo 的销售全额记账；"
    "Dupixent 美国利润对半、美国以外 35%–45%；合作安排同时免除了公司自建全球商业化渠道的资本开支与执行风险；"
    "公司口径净产品销售毛利率维持 GAAP 78–80% / 非 GAAP 84–87%。"
    "仍存在的约束（不改变档位但如实记录）：支付方（Medicare Part B / PBM）具备实质价格谈判权，"
    "UnitedHealthcare 2026 阶梯治疗清单已将 EYLEA HD 与生物类似药 Pavblu 同等优选；"
    "2026-04 MFN 协议以美国 Medicaid 价格让步换取关税豁免，公司自述将「reduce prices and reimbursement」且未量化；"
    "上游第三方灌装厂的单点依赖已两次阻断审批（EYLEA HD 预充针与 odronextamab CRL）。"
    "综合判断：价值获取端属「吃肉」主导（5/5）；上游客链冗余不足与下游支付方压力作为风险记录，不降档。"
)
ci["F2"]["reason"] = (
    "本项维持「一般（3）」档。**终审意见要求认可的正面事实已并入**：回购具备实质缩股效果——"
    "稀释加权平均股数由 2024 年 115.1 百万股降至 2026H1 106.8 百万股（−7.2%），库存股形式不应被单独惩罚；"
    "总股东回报（回购 + 股息）达 FY2025 净利润约 85%，回购收益率 4.76%、股东回报率 5.23%；"
    "近年无股权融资、无其他摊薄工具；创始人 2024 年 5-6 月后再无公开市场卖出。"
    "未达 5 分档（该档要求「高分红」为前置条件）的两项事实：股息派息率仅 9.15%、股息率 0.47%，"
    "首次派息仅两年；以及 2025 年年会 Class A（10 票/股，Schleifer 持 95%）以 0 赞成／18,081,400 反对"
    "否决了降低修改相关条款所需普通股表决门槛的章程修正案 5(a)，而普通股股东以 85,490,681 赞成对 2,279,384 反对支持该项——"
    "创始人以类别否决权推翻了普通股多数意愿。**终审明确要求「保留类别否决权约束」**，故本项不升至 5 档；"
    "认可净回购的加分改由管理层档案「对股东友好度」项体现（11→13）。"
    "去重声明：同一控制权事实不在管理层档案重复扣分。"
)

d["scores"]["company"]["total"] = sum(i["score"] for i in d["scores"]["company"]["items"])

# ---------- company: E3 corrected reasoning (score unchanged) ----------
ci["E3"]["reason"] = (
    "**口径更正（终审 P1）**：(1) 「证券投资收益未被非 GAAP 剔除」的原稿表述错误——"
    "公司 FY2025 的非 GAAP 调整表**已剔除证券投资净收益 $946.1M**；非 GAAP 同时剔除 SBC 等经常性成本，"
    "因此不能把非 GAAP 当作「干净盈利」照单全收，但批评必须针对实际口径。"
    "(2) 「主业仍在收缩」的表述遗漏了最新半年报的反转——**2026H1 合并经营利润 $1,936.4M vs 2025H1 $1,671.2M，+15.9%**。"
    "修正后的判断：**经营利润已在 2026H1 修复，但现金回款尚未同步改善（1H2026 OCF −13.6%、FCF −18.4%），EYLEA 仍承压。**"
    "保留 2/3 的理由（GAAP 口径事实）：FY2025 经营利润 $3,577.9M（−10.3%）与报表净利润 $4,504.9M（+2.1%）背离，"
    "差额来自其他收益由 FY2023 $225.2M 膨胀至 FY2025 $1,696.6M（占税前利润 32.4%），其中证券投资损益从 −$266.4M 摆动至 +$946.1M；"
    "增长分解中「价」为负贡献（公司自述美国 EYLEA 下滑含更低的净销售价格）；"
    "SBC 规模约为公司口径 FCF 的 24%（FY2026 指引 SBC 合计约 $9.7–10.3 亿），属真实经济成本。"
    "「量」（Dupixent 患者数）与「结构」（EYLEA HD 占美国体系约 60%）为正面，故不降至 1 分档。"
)

# ---------- management ----------
mi["资本配置能力"]["score"] = 19
mi["资本配置能力"]["reason"] = (
    "配置主线：研发优先——R&D 由 FY2019 $24.50 亿增至 FY2025 $58.50 亿，FY2025 占收入 40.8%，"
    "同期产出 13 个 FDA 批准药物与约 50 个在研候选物。并购纪律优秀：2023-2026 无十亿美元级并购；"
    "2025 年以「对 23andMe 剩余价值的评估」为由公开放弃提高报价。回购执行：2019-2026H1 累计约 $177 亿，"
    "其中 2020 年 $50 亿直接向 Sanofi 买入为事后价值创造显著的决策；从未使用 ASR、荷兰式拍卖或特别股息等财技；"
    "FY2026 资本开支指引由 $11.0-12.0 亿主动下调至 $10.3-11.0 亿。股东回报：2025 年首次派息、2026 年上调 6.8%。"
    "**终审修正**：原稿把「五年股东总回报落后指数」直接当作资本配置能力不足的核心依据，该推断不充分——"
    "股价总回报同时受估值倍数收缩与市场对专利周期的预期影响，不等于管理层配置决策的质量。"
    "修正后保留的扣分依据（投入与回报两端）：经营性资本回报以经营性投入资本计约为 27%（优秀），"
    "但 FY2025 经营利润 −10.3% 显示当期产出承压；2020-2025 这一轮资本投放尚未产生高于行业基准的账面回报。"
    "（原稿引用的全资本口径 ROIC 13.04% 把 $188.66 亿有价证券计入投入资本，不作主要依据。）取 19/25。"
)
mi["对股东友好度"]["score"] = 13
mi["对股东友好度"]["reason"] = (
    "正面信号（终审加强）：资本回报规模化且具实质缩股效果——FY2025 回购（回购计划口径）$34.56 亿 + 现金股利 $3.70 亿，"
    "股东回报率 5.23%；稀释加权平均股数由 2024 年 115.1 百万股降至 2026H1 106.8 百万股（−7.2%）；"
    "2025 年首次派息后一年内上调 6.8%（$0.88→$0.94/季）；CEO/CSO 于 FY2025 完全不领取股权（兑现 2021 年承诺）；"
    "2020 年 PSU 为 5 年相对 TSR 业绩期 + 3 年强制持有；创始人自 2024 年 5-6 月后再无公开市场卖出（未在 2026 年低位减持）；"
    "无高位定增、无财技包装、无特别股息或荷兰式拍卖等市值管理动作。"
    "**终审修正**：原稿以「低派息率、库存股形式、无额外公开市场增持」三项作为扣分依据，终审认定均不充分——"
    "库存股回购同样具有缩股效果；股息率高低取决于公司所处生命周期而非友好度；"
    "内部人未在公开市场增持不构成不友好。上述三项已从扣分依据中删除。"
    "保留的负面记录：2020 年 PSU 单次兑现价值每人 $4.815 亿（虽经 8 年锁定期）；"
    "回购计入库存股而非注销，库藏股部分用于员工股权计划，故不能按「纯现金股东回报」满分认定。取 13/15。"
)
mi["组织与人才能力"]["score"] = 8
mi["组织与人才能力"]["reason"] = (
    "高管稳定性：核心团队 38 年稳定，近 5 年 C-suite 接任全部为内部晋升（CFO Fenimore 2003 年入职、"
    "Co-CSO Murphy 1999 年入职、SVP Controller Pitofsky 2011 年入职），无短期密集离任。"
    "核心人才保留：研发体系 >1,800 名 Ph.D./M.D.；Regeneron Genetics Center 完成百万例外显子测序并获 Truveta 全部研究测序独家权；"
    "2025 年股权授予使用率（equity grant burn rate）2.00%，为公司历史最低。"
    "激励机制：Say-on-Pay 93.3%；CEO/CSO 无股权年度与 PSU 8 年锁定的组合约束力强于同业；"
    "追回政策宽于 Nasdaq 标准；2022-04 起禁止对冲与质押。"
    "**终审修正**：原稿使用「继任真空」的表述，不准确——公司治理准则与 Lead Independent Director 职责均已明确覆盖"
    "CEO 继任规划，2025-2026 年董事会层面的继任与人才复核工作持续进行，且已有 2024 年 CFO 内部接班的成功先例；"
    "准确表述应为「**关键人风险，且继任结果尚未公开**」。据此上调 1 分。"
    "保留的风险：CEO 年龄 73 岁且无已公开的继任人或时间表；前 EVP, Research and Development Neil Stahl 约 2024 年离任公司未披露原因；"
    "13 名董事中 3 人年龄 ≥83 且不设强制退休年龄，长期任职董事持续收到 20%-30% 反对票。取 8/10。"
)
d["scores"]["management"]["total"] = sum(i["score"] for i in d["scores"]["management"]["items"])

# ---------- valuation ----------
v = d["valuation"]
NC, LIQ, SH = 15116.3, 1000.0, 106.0
def opv(oi, mult, tax=0.14):
    return (oi * (1 - tax) * mult + NC - LIQ) / SH
F = [790, 3797, 4253, 4750, 5200, 5200, 4940, 4450, 4010, 3810]
def dcf(f, w, g, scale=1.0):
    pv = sum(f[i] * scale / (1 + w) ** (0.27 + i) for i in range(10))
    tv = f[9] * scale * (1 + g) / (w - g) / (1 + w) ** 9.27
    return (pv + tv + NC - LIQ) / SH

m1 = {
    "id": "m1_operating_value_ev_nopat",
    "weight": 1.0,
    "basis": (
        "经营价值模型：以剔除利息收入与证券投资损益后的经营性税后利润（NOPAT）乘以企业价值倍数，"
        "再加回报表净现金、扣除维持经营所需的最低流动性储备，除以估值稀释股数。"
        "因分子为经营性口径，倍数须使用企业价值/经营税后利润（EV/NOPAT）而非普通同业 PE——"
        "普通同业 PE 建立在含融资与金融资产收益的每股盈利之上，两者口径不可直接互换（终审 P1 修正）。"
    ),
    "shared_assumptions": ["FY2027E 经营利润预测", "净现金", "估值稀释股数"],
    "output_currency": "USD", "output_unit": "per_share",
    "formula": "(op_income * (1 - tax) * multiple + net_cash_m - liquidity_reserve) / shares_m",
    "scenarios": {},
    "sensitivity": {
        "x": "multiple", "x_values": [13.0, 14.5, 16.0],
        "y": "op_income", "y_values": [4900.0, 5543.0, 6100.0],
        "values": [[round(opv(oi, m), 2) for oi in (4900.0, 5543.0, 6100.0)] for m in (13.0, 14.5, 16.0)],
    },
}
meta = lambda u, dt, k: {"unit": u, "date": dt, "kind": k, "evidence_refs": ["REGN-D-002", "REGN-E-001"]}
for key, mult in (("bear", 13.0), ("base", 14.5), ("bull", 16.0)):
    m1["scenarios"][key] = {
        "inputs": {"op_income": 5543.0, "tax": 0.14, "multiple": mult,
                   "net_cash_m": NC, "liquidity_reserve": LIQ, "shares_m": SH},
        "input_meta": {
            "op_income": {"unit": "USD millions; FY2027E 经营利润", "date": "FY2027E", "kind": "assumption", "evidence_refs": ["REGN-D-002"]},
            "tax": {"unit": "normalized tax rate (decimal)", "date": "FY2026E", "kind": "assumption", "evidence_refs": ["REGN-D-002"]},
            "multiple": {"unit": "x EV / operating NOPAT", "date": "2026-09-23", "kind": "assumption", "evidence_refs": ["REGN-M-005"]},
            "net_cash_m": {"unit": "USD millions", "date": "2026-06-30", "kind": "actual", "evidence_refs": ["REGN-E-006"]},
            "liquidity_reserve": {"unit": "USD millions; 维持经营的最低流动性假设", "date": "2026-09-23", "kind": "assumption", "evidence_refs": ["REGN-E-006"]},
            "shares_m": {"unit": "millions; 估值稀释股数", "date": "2026Q2", "kind": "assumption", "evidence_refs": ["REGN-M-009"]},
        },
        "value": opv(5543.0, mult),
    }

m2 = {
    "id": "m2_fcff_dcf_erosion",
    "weight": 0.0,
    "basis": (
        "修订后的 FCFF 折现交叉锚（**权重 0，仅作诊断**）。相对原模型的四项修正："
        "(1) 补齐 FCFF 推导表（经营税后利润 + 折旧摊销 − 资本开支 − 营运资金变动，SBC 已在 GAAP 经营利润中扣除，不重复扣）；"
        "(2) 估值时点由「整年 2026」改为自 2026-09-23 起的剩余期间（首期指数 0.27 年）；"
        "(3) 显式期由 5 年延长至 10 年（2027–2035），并在 2031 年起加入 Dupixent 美国核心物质专利到期后的侵蚀台阶；"
        "(4) 终值仅覆盖 2035 年之后。不赋权的理由：Dupixent 专利族到期时点分散（美国核心物质专利 2031-03-28，"
        "但剂型专利延至 2032-10-17、治疗方法专利延至 2034-07-10 及更晚），侵蚀路径无官方依据，"
        "属假设而非可核事实，不足以支撑正式权重。"
    ),
    "shared_assumptions": ["FY2027E 经营利润预测", "净现金", "估值稀释股数"],
    "output_currency": "USD", "output_unit": "per_share",
    "formula": ("(fcf1/(1+w)**0.27 + fcf2/(1+w)**1.27 + fcf3/(1+w)**2.27 + fcf4/(1+w)**3.27 + fcf5/(1+w)**4.27 "
                "+ fcf6/(1+w)**5.27 + fcf7/(1+w)**6.27 + fcf8/(1+w)**7.27 + fcf9/(1+w)**8.27 + fcf10/(1+w)**9.27 "
                "+ (fcf10*(1+g)/(w-g))/(1+w)**9.27 + net_cash_m - liquidity_reserve) / shares_m"),
    "scenarios": {},
    "sensitivity": {
        "x": "w", "x_values": [0.085, 0.09, 0.10],
        "y": "g", "y_values": [0.0, 0.01, 0.02],
        "values": [[round(dcf(F, w, g), 2) for w in (0.085, 0.09, 0.10)] for g in (0.0, 0.01, 0.02)],
    },
}
for key, (w, g, sc) in (("bear", (0.10, 0.01, 0.85)), ("base", (0.09, 0.02, 1.0)), ("bull", (0.085, 0.025, 1.10))):
    inp = {("fcf%d" % (i + 1)): round(F[i] * sc, 1) for i in range(10)}
    inp.update({"w": w, "g": g, "net_cash_m": NC, "liquidity_reserve": LIQ, "shares_m": SH})
    im = {k: {"unit": "USD millions; 经营口径 FCFF（不含利息收入与证券投资损益）", "date": "FY%dE" % (2026 + (i if i else 0)),
              "kind": "assumption", "evidence_refs": ["REGN-E-005"]} for i, k in enumerate(["fcf%d" % (j + 1) for j in range(10)])}
    im.update({
        "w": {"unit": "WACC (decimal)", "date": "2026-09-23", "kind": "assumption", "evidence_refs": ["REGN-M-005"]},
        "g": {"unit": "terminal growth (decimal)", "date": "2026-09-23", "kind": "assumption", "evidence_refs": ["REGN-S01"]},
        "net_cash_m": {"unit": "USD millions", "date": "2026-06-30", "kind": "actual", "evidence_refs": ["REGN-E-006"]},
        "liquidity_reserve": {"unit": "USD millions", "date": "2026-09-23", "kind": "assumption", "evidence_refs": ["REGN-E-006"]},
        "shares_m": {"unit": "millions", "date": "2026Q2", "kind": "assumption", "evidence_refs": ["REGN-M-009"]},
    })
    m2["scenarios"][key] = {"inputs": inp, "input_meta": im, "value": dcf(F, w, g, sc)}

v["models"] = [m1, m2]
v["additional_model_reason"] = (
    "仅一个主模型赋权（M1 权重 1.0）。M2 为修订后的现金流行生诊断，权重 0：其侵蚀路径依赖对 Dupixent 专利族"
    "到期节奏的假设，而该时点在年报中分散披露（美国核心物质专利 2031-03-28，剂型延至 2032-10-17，治疗方法延至 2034-07-10 及更晚），"
    "无官方依据可定价；按纪律不作为第二个独立依据，也不以其结果拉伸或压缩合理价。"
)
v["weighted"] = {k: m1["scenarios"][k]["value"] for k in ("bear", "base", "bull")}
v["target_price"] = 785.0
v["certainty"] = 0.45
v["certainty_reason"] = (
    "**终审指定 0.45，不作细碎加减分制造精确概率**；为保留审计轨迹，附简短闭合：\n"
    "起值 0.50\n"
    "＋0.06 资产负债表与融资需求清晰（2026-06-30 现金及有价证券 $178.23 亿对总债务 $27.07 亿，净现金 $151.16 亿；无商誉）\n"
    "＋0.03 收入可见性（1H2026 Sanofi 合作收入占收入 48%，与 Dupixent 全球销售线性挂钩；开发余额已清偿带来确定性台阶）\n"
    "−0.05 Dupixent 专利族 2031 年起陆续到期，中期盈利与专利后现金流未闭合\n"
    "−0.03 估值稀释股数假设跨度为 102.8M（基本）至 106.0M（GAAP 稀释），SBC 约相当于公司口径 FCF 的 24%，稀释路径不确定\n"
    "−0.03 多重未量化法律与政策敞口（DOJ FCA 及多州介入、两件证券集体诉讼、Dupixent 产品责任多区诉讼、MFN 协议影响未披露）\n"
    "−0.02 EYLEA 下滑速度与 2026Q4 起 6 家 aflibercept 生物类似药集群上市的时点不确定\n"
    "−0.01 单一主模型赋权，缺少第二个有独立依据的定量模型\n"
    "＝ 0.45。"
)
v["buy_price"] = v["target_price"] * (0.68 + 0.14 * v["certainty"])
IMPLIED_MULT = ((801.82 * SH) - NC + LIQ) / (5543 * 0.86)
v["reverse"] = {
    "weight": 0,
    "variable": "multiple",
    "implied_value": IMPLIED_MULT,
    "formula": "(market_price * shares_m - net_cash_m + liquidity_reserve) / (op_income * (1 - tax))",
    "inputs": {"market_price": 801.82, "shares_m": SH, "net_cash_m": NC, "liquidity_reserve": LIQ,
               "op_income": 5543.0, "tax": 0.14, "multiple": IMPLIED_MULT},
    "market_price": 801.82,
    "assumptions": (
        "沿用 M1 的 FY2027E 经营利润 5,543 百万美元、14%% 正常化税率、净现金 15,116.3 百万美元、"
        "经营流动性保留 1,000 百万美元与估值稀释股数 106 百万股，反解使模型输出等于 2026-09-23 收盘价 801.82 美元"
        "的 EV/NOPAT 倍数。解得约 " + "%.2f" % IMPLIED_MULT + " 倍。诊断：市场为公司的经营性税后利润支付约 "
        + "%.1f" % IMPLIED_MULT + " 倍企业价值倍数，略高于本次采用的 14.5 倍中枢，意味着价格已包含对 Dupixent 增长延续的温和乐观；"
        "若按 13 倍下沿对应 717.80 美元，现价高于该下沿约 11.7%%。仅作诊断，权重为 0。"
    ),
}

d["qualification"] = {
    "highest_score_gate": "A_CORE",
    "status": "pending_review",
    "reason": (
        "公司分原始 83.0、管理层分原始 84.0，合计 167.0：满足 A_CORE（合计≥160 且两项均≥76），"
        "未达 S_STRATEGIC（需合计≥170、两项均≥82 且 valuation_certainty≥0.80；本项确定性 0.45 远低于 0.80 门槛）。"
        "无单维度低于满分 40% 的警告；管理层诚信 18/20 与资本配置 19/25 均高于 40% 红线。"
        "门槛余量：合计高于 A_CORE 门槛 7.0 分，较初稿的 1.0 分余量显著扩大。"
        "**机械档位约束说明**：终审建议的 C 维度 15 分与 F 维度 13 分在本框架的封闭档位下不可实现——"
        "C2 产业链话语权仅允许 5/3/0-1，F2 股东利益对齐仅允许 5/3/0-1，故 C 只能取 14 或 16、F 只能取 12 或 14。"
        "本次按终审的实体理由落地：C2 由 3 升 5（终审认定「喝汤」论证不成立，方向向上，取可达的上档 → 公司 C=16）；"
        "F2 维持 3（终审明确要求「保留类别否决权约束」，即不取 5 档 → 公司 F=12）；"
        "净回购的认可改由管理层「对股东友好度」11→13 体现。最终公司分 83.0，与终审目标一致。"
    ),
}

d["evidence_gaps"] = [
    {"affected_items": ["D3", "F3", "估值"],
     "kind": "2026-04 MFN 美国政府采购协议对价格与报销的美元影响未披露；协议覆盖的产品范围未逐项列明",
     "impact": "政策负面影响的量级无法进入基准情景，仅在风险与敏感性中按方向处理。",
     "search_scope": "Q2 2026 10-Q、2026-04 公司公告与白宫事实清单、公司风险因素章节",
     "evidence_refs": ["REGN-D-006", "REGN-F-011"]},
    {"affected_items": ["D2", "组织与人才能力"],
     "kind": "CEO 继任的具体安排与时间表未公开（董事会继任审查机制已披露）；前 EVP, Research and Development Neil Stahl 的离任原因未披露",
     "impact": "组织维度按「关键人风险 + 继任结果未公开」做有限扣分，不推断更严重情形。",
     "search_scope": "2024-2026 DEF 14A 高管名单与治理章节、FY2025 10-K、EDGAR 8-K 全文、Web 检索",
     "evidence_refs": ["REGN-F-013", "REGN-F-014"]},
    {"affected_items": ["估值", "资本配置能力"],
     "kind": "Dupixent 专利族到期后的收入侵蚀路径无可核事实依据（美国核心物质专利 2031-03-28，剂型/治疗方法专利分别延至 2032-10-17、2034-07-10 及更晚）",
     "impact": "导致 M2 折现模型不赋权、确定性维持在中低区间；正文以情景而非点值处理。",
     "search_scope": "FY2025 10-K 专利到期表、Sanofi 与 Regeneron 披露",
     "evidence_refs": ["REGN-S01"]},
]

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("company", d["scores"]["company"]["total"], "management", d["scores"]["management"]["total"],
      "combined", d["scores"]["company"]["total"] + d["scores"]["management"]["total"])
print("target", v["target_price"], "certainty", v["certainty"], "buy", round(v["buy_price"], 2))
print("M1 scenarios", [round(m1["scenarios"][k]["value"], 2) for k in ("bear", "base", "bull")])
print("M2 scenarios", [round(m2["scenarios"][k]["value"], 2) for k in ("bear", "base", "bull")])
print("implied multiple", round(IMPLIED_MULT, 3))
