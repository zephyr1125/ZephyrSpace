# -*- coding: utf-8 -*-
"""Apply review-driven fact corrections to the neutral fact registry."""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
P = "data/reviews/regn-2026-09-24/evidence/facts.json"
d = json.load(open(P, encoding="utf-8"))
F = {f["fact_id"]: f for f in d["facts"]}

F["REGN-D-001"]["value"] = (
    "R&D 费用（10-K 利润表口径）：FY2019 $2,450.0M → FY2020 $2,735.0M → FY2021 $2,860.1M → FY2022 $3,592.5M → "
    "FY2023 $4,439.0M → FY2024 $5,132.0M → FY2025 $5,850.2M；FY2025 占收入 40.8%。"
    "（更正说明：原稿引用的 FY2019 $3,036.6M 与 FY2021 $2,908.1M 系混入当年 acquired IPR&D 的口径，"
    "FY2020 10-K 审计后利润表与 Q4 2022 业绩发布原件分别为 $2,450.0M 与 $2,860.1M。）"
)
F["REGN-D-001"]["source_id"] = "REGN-S01"
F["REGN-D-003"]["value"] = (
    "FY2025 年末约 45 个候选产品；Q2 2026 业绩发布约 50 个候选产品（clinical development）；"
    "Q2 2026 电话会逐字稿口径同样为「approximately 50 active clinical programs」。"
    "（更正说明：原稿并列的「电话会称 35+ 个临床阶段项目」经全文复核不存在——逐字稿中无 35+ programs 表述，"
    "仅出现一次数字 35 且属行情条。两处口径一致，不构成表述不一致。）"
)
F["REGN-C-001"]["item"] = "EYLEA 体系与美国眼科竞争地位"
F["REGN-C-001"]["value"] = (
    "EYLEA 体系（原研 2mg + EYLEA HD）美国净销售：Q4 2025 合计 $1,083.2M（原研 $576.9M + HD $506.3M），"
    "H1 2026 合计 $1,950.0M；Vabysmo（Roche）美国 H1 2026 CHF 1,333M、H1 2025 CHF 1,450M（CER +1%），"
    "Roche 自述「despite a competitive pricing environment」。EYLEA 体系美国销售额仍居首位，但原研单品已明显落后："
    "美国 EYLEA 2mg 由 FY2024 $4,767.1M 降至 FY2025 $2,747.8M，Q2 2026 同比 -45%。"
    "（更正说明：原稿「EYLEA 体系已让出美国视网膜市场销售第一」不成立——该比较误将 Vabysmo 全产品美国销售与原研 EYLEA 单品对比，"
    "未计 EYLEA HD；Roche 报告与 Regeneron 8-K Table 5 均显示体系销售额仍领先。）"
)
F["REGN-C-001"]["source_id"] = "REGN-S03"
F["REGN-E-003"]["item"] = "其他收益构成（已完整拆解）"
F["REGN-E-003"]["value"] = (
    "FY2025 其他收益（费用）净额 $1,696.6M 的 10-K MD&A 拆解：证券及其他投资损益净额 $946.1M + 利息收入 $716.8M + 其他 $33.7M。"
    "对照年份：FY2024 $118.3M + $711.4M + $14.7M = $844.4M；FY2023 -$266.4M + $495.9M - $4.3M = $225.2M。"
    "现金流量表间接法首行同列示「(Gains) losses on marketable and other securities, net (946.1)」。"
    "（更正说明：原稿所称「除利息收入外约 $979.8M 未获公司拆解」不成立——公司已完整拆解，$946.1M 为证券损益、$33.7M 为其他；"
    "其中 $946.1M 为已实现与未实现合计，未再细分，故仍按非经常性处理。）"
)
F["REGN-E-005"]["value"] = (
    "OCF/归母净利润：FY2022 115.6%、FY2023 116.2%、FY2024 100.2%、FY2025 110.5%。"
    "公司口径自由现金流（OCF − 资本性支出）：FY2022 $4,424.8M、FY2023 $3,875.4M、FY2024 $3,664.6M、FY2025 $4,080.5M，连续为正。"
    "1H2026 OCF $1,891.9M（1H2025 $2,189.5M，-13.6%）、1H2026 公司口径 FCF $1,421.1M（1H2025 $1,741.2M，-18.4%）；"
    "TTM（截至 2026-06-30）FCF $3,760M。"
    "（更正说明：原稿引用的 FY2022 $3,398.0M / FY2023 $3,667.6M / FY2024 $3,538.9M 实为「OCF − capex − 无形资产付款」口径"
    "（含 FY2022 Libtayo 无形资产付款 $1,026.8M 等），与 FY2025 所用口径不一致；已统一为公司口径。）"
)
F["REGN-M-002"]["item"] = "股数口径（已选定基准）"
F["REGN-M-002"]["value"] = (
    "估值统一采用 102.95 百万股：2026-07-23 10-Q 封面普通股 101,137,842 股 + Class A 1,817,146 股 = 102,954,988 股，"
    "与 yfinance impliedSharesOutstanding 102,954,988 一致，亦与 Robinhood 市值 $82.53B ÷ $801.82 反推的约 102.9M 一致。"
    "另列多源分歧以供披露：stockanalysis 99.85M、Markets Insider 101.14M（2026-09-11）、10-Q 资产负债表净发行在外推算约 103.4M"
    "（发行 138.0M − 库存 36.4M，含 Class A）；稀释加权平均 1H2026 为 106.8M。每股价值口径误差约 ±2%。"
)
d["_corrections"] = {
    "applied": "2026-09-24",
    "basis": "两路独立审核（facts lane / reasoning lane）后的裁决修复",
    "items": ["REGN-D-001", "REGN-D-003", "REGN-C-001", "REGN-E-003", "REGN-E-005", "REGN-M-002"],
}
json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("facts corrected:", d["_corrections"]["items"])
