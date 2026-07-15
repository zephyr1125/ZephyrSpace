---
aliases:
  - Watchlist 文档审阅进度
  - Core Growth 文档审阅台账
最后更新日期: 2026-07-15
范围: watchlist_core.json + watchlist_growth.json
审阅标准: company-review-adjudication
---

# Watchlist 三文档审阅进度

## 本轮审阅口径

- 本台账已于 2026-07-15 第四次重置；此前所有“已完成”、旧分数、修改摘要和 JSON 均已归档，不作为本轮结论。
- 公司范围只取 `data/watchlist_core.json` 与 `data/watchlist_growth.json` 当前 `entries`；不读取旧 `stock_watchlist.json`，也不纳入已废弃 radar。
- 逐家公司按 `company-review-adjudication` 的顺序审阅：深度分析与公司质量评分 → 管理层档案与管理层评分 → 估值与价格区间 → 合理价值、买入价、最大仓位。
- 审阅必须校验事实新鲜度、算术、跨文档一致性、重复扣分、估值方法重叠和安全边际；低估不豁免公司质量或管理层门槛。确定最终参数后，必须全量改写三份页面，不得保留任何未标记的旧分数。
- 每家完成后在本文件追加：最终分数、合理价值/买入价/仓位、证据与实际修改；不在此重复写 JSON，也不写入 watchlist JSON，待用户确认后才可入库。

## 重扫结果（2026-07-15）

- Core：29 家；Growth：28 家；按证券代码去重后共 57 家。
- 初次重扫定位三文档47家；其余10家估值页已于2026-07-15补齐并完成裁决。
- 当前57家公司均具备深度分析、管理层档案和估值分析；不存在待补估值缺口。
- 别名映射已确认：`NVIDIA → 英伟达估值页`、`卡特彼勒(CAT) → 卡特彼勒`、`Alphabet(Google) → Alphabet/谷歌`。

## 本轮公司（57 家；已完成 57 家；待重审 0 家）

| 档位 | 公司 | 管理层档案 | 深度分析 | 估值分析 | 状态 | 本轮裁决摘要 |
|---|---|---|---|---|---|---|
| core | 国电南瑞 | 83 / 2026-07-09 | 85 / 2026-07-09 | 2026-07-09 | 已完成 | cScore 85；mScore 83；targetPrice ¥26；buyPrice ¥21；maxWeight 4% |
| core | NVIDIA | 83 / 2026-07-14 | 86 / 2026-05-22 | 英伟达 / 2026-07-14 | 已完成 | cScore 86；mScore 83；targetPrice $220；buyPrice $180；maxWeight 4% |
| core | 贵州茅台 | 80 / 2026-05-31 | 88 / 2026-05-29 | 2026-07-02 | 已完成 | cScore 88；mScore 80；targetPrice ¥1,250；buyPrice ¥1,100；maxWeight 5% |
| core | 招商银行 | 81 / 2026-07-12 | 82 / 2026-07-12 | 2026-07-12b | 已完成 | cScore 82；mScore 81；targetPrice ¥43；buyPrice ¥36；maxWeight 5% |
| core | 蜜雪集团 | 76 / 2026-05-31 | 79 / 2026-05-20 | 2026-07-14 | 已完成 | cScore 79；mScore 76；targetPrice HK$250；buyPrice HK$190；maxWeight 2%；两项低于门槛的观察性例外 |
| core | 宁德时代 | 84 / 2026-07-14 | 86 / 2026-05-22 | 2026-07-01 | 已完成 | cScore 86；mScore 84；targetPrice ¥450；buyPrice ¥360；maxWeight 3% |
| core | 创科实业 | 80 / 2026-06-03 | 82 / 2026-06-03 | 2026-07-14 | 已完成 | cScore 82；mScore 80；targetPrice HK$125；buyPrice HK$100；maxWeight 3% |
| core | 中信特钢 | 78 / 2026-06-28 | 77 / 2026-06-28 | 2026-07-14 | 已完成 | cScore 77；mScore 78；targetPrice ¥13；buyPrice ¥10；maxWeight 2%；低于门槛的周期性例外 |
| core | 久立特材 | 76 / 2026-06-28 | 76 / 2026-06-28 | 2026-07-14 | 已完成 | cScore 76；mScore 76；targetPrice ¥16；buyPrice ¥12.5；maxWeight 2%；低于门槛的明确例外 |
| core | 海尔智家 | 80 / 2026-06-28 | 82 / 2026-06-28 | 2026-07-14 | 已完成 | cScore 82；mScore 80；targetPrice ¥24；buyPrice ¥20；maxWeight 4% |
| core | 万事达卡 | 82 / 2026-07-07 | 84 / 2026-07-07 | 2026-07-07 | 已完成 | cScore 84；mScore 82；targetPrice $540；buyPrice $470；maxWeight 4% |
| core | 高通 | 78 / 2026-07-10 | 80 / 2026-07-10 | 2026-07-10 | 已完成 | cScore 80；mScore 78；targetPrice $180；buyPrice $150；maxWeight 2%；低于常规管理层门槛 |
| core | ASML | 83 / 2026-07-10 | 88 / 2026-07-10 | 2026-07-10 | 已完成 | cScore 88；mScore 83；targetPrice $1,350；buyPrice $1,050；maxWeight 3% |
| core | 台积电 | 88 / 2026-06-27 | 88 / 2026-06-27 | 2026-07-14 | 已完成 | cScore 88；mScore 88；targetPrice $400；buyPrice $350；maxWeight 3% |
| core | 福耀玻璃 | 85 / 2026-07-14 | 88 / 2026-05-17 | 2026-07-14 | 已完成 | cScore 88；mScore 85；targetPrice ¥60；buyPrice ¥52；maxWeight 3% |
| core | 海康威视 | 79 / 2026-06-02 | 78 / 2026-05-19 | 2026-07-14 | 已完成 | cScore 78；mScore 79；targetPrice ¥34；buyPrice ¥27；maxWeight 1%；低于门槛，仅观察例外 |
| core | 中国广核 | 82 / 2026-07-04 | 81 / 2026-07-04 | 2026-07-04 | 已完成 | cScore 81；mScore 82；targetPrice ¥3.61；buyPrice ¥3.40；maxWeight 3% |
| core | 瑞芯微 | 78 / 2026-06-02 | 82 / 2026-05-22 | 2026-07-14 | 已完成 | cScore 82；mScore 78；targetPrice ¥216；buyPrice ¥190；maxWeight 2%；低于常规管理层门槛 |
| core | 迈瑞医疗 | 79 / 2026-07-09 | 85 / 2026-07-09 | 2026-07-09 | 已完成 | cScore 85；mScore 79；targetPrice ¥165；buyPrice ¥150；maxWeight 2%；低于常规管理层门槛 |
| core | 吉比特 | 83 / 2026-06-15 | 78 / 2026-06-15 | 2026-07-07 | 已完成 | cScore 78；mScore 83；targetPrice ¥400；buyPrice ¥330；maxWeight 2%；低于常规公司质量门槛 |
| core | 亿联网络 | 80 / 2026-07-14 | 82 / 2026-07-14 | 2026-07-14 | 已完成 | cScore 82；mScore 80；targetPrice ¥40；buyPrice ¥34；maxWeight 3% |
| core | 乐鑫科技 | 80 / 2026-06-02 | 79 / 2026-06-02 | 2026-07-14 | 已完成 | cScore 79；mScore 80；targetPrice ¥121；buyPrice ¥100；maxWeight 2%；公司质量低于常规门槛，仅观察性例外 |
| core | 青岛啤酒 | 80 / 2026-07-12 | 82 / 2026-07-12 | 2026-07-12 | 已完成 | cScore 82；mScore 80；targetPrice ¥63；buyPrice ¥52；maxWeight 3% |
| core | 直觉外科 | 87 / 2026-07-07 | 84 / 2026-07-07 | 2026-07-14 | 已完成 | cScore 84；mScore 87；targetPrice $340；buyPrice $290；maxWeight 3% |
| core | 东鹏饮料 | 76 / 2026-07-14 | 81 / 2026-05-26 | 2026-07-14 | 已完成 | cScore 81；mScore 76；targetPrice ¥140；buyPrice ¥110；maxWeight 2%；低于管理层门槛，仅观察性例外 |
| core | 沪电股份 | 84 / 2026-07-14 | 82 / 2026-05-29 | 2026-07-14 | 已完成 | cScore 82；mScore 84；targetPrice ¥117；buyPrice ¥95；maxWeight 3% |
| core | 卡特彼勒(CAT) | 卡特彼勒 / 80 / 2026-07-14 | 卡特彼勒 / 84 / 2026-05-16 | 卡特彼勒 / 2026-07-14 | 已完成 | cScore 84；mScore 80；targetPrice $600；buyPrice $500；maxWeight 3% |
| core | 深信服 | 79 / 2026-07-14 | 79 / 2026-05-29 | 2026-07-14 | 已完成 | cScore 79；mScore 79；targetPrice ¥92；buyPrice ¥75；maxWeight 2%；双项低于门槛，仅观察性例外 |
| growth | 华润三九 | 80 / 2026-06-27 | 78 / 2026-06-27 | 2026-07-14 | 已完成 | cScore 78；mScore 80；targetPrice ¥34；buyPrice ¥26；maxWeight 2%；公司质量低于门槛，仅观察性例外 |
| growth | 中航沈飞 | 78 / 2026-06-08 | 79 / 2026-06-07 | 2026-07-14 | 已完成 | cScore 79；mScore 78；targetPrice ¥37；buyPrice ¥28；maxWeight 2%；双项低于门槛，仅观察性例外 |
| growth | 宁波银行 | 80 / 2026-06-13 | 73 / 2026-05-26 | 2026-06-30 | 已完成 | cScore 73；mScore 80；targetPrice ¥33；buyPrice ¥28；maxWeight 2%；公司质量低于门槛，仅观察性例外 |
| growth | 江苏银行 | 81 / 2026-06-13 | 72 / 2026-06-13 | 2026-07-14 | 已完成 | cScore 72；mScore 81；targetPrice ¥12；buyPrice ¥10；maxWeight 2%；公司质量低于门槛，仅观察性例外 |
| growth | 青岛港 | 76 / 2026-06-27 | 75 / 2026-06-27 | 2026-07-14 | 已完成 | cScore 75；mScore 76；targetPrice ¥8.70；buyPrice ¥7；maxWeight 2%；双项低于门槛，仅观察性例外 |
| growth | BlackBerry | 79 / 2026-06-25 | 72 / 2026-06-25 | 2026-07-14 | 已完成 | cScore 72；mScore 79；targetPrice $7.50；buyPrice $6.50；maxWeight 1%；双项低于门槛，仅观察性例外 |
| growth | 卫星化学 | 76 / 2026-06-22 | 75 / 2026-06-22 | 2026-07-14 | 已完成 | cScore 75；mScore 76；targetPrice ¥25.50；buyPrice ¥20；maxWeight 2%；双项低于门槛，仅观察性例外 |
| growth | 泸州老窖 | 73 / 2026-07-04 | 78 / 2026-07-04 | 2026-07-04 | 已完成 | cScore 78；mScore 73；targetPrice ¥100；buyPrice ¥75；maxWeight 2%；双项低于门槛，仅观察性例外 |
| growth | 顺丰控股 | 78 / 2026-07-14 | 72 / 2026-07-14 | 2026-07-14 | 已完成 | cScore 72；mScore 78；targetPrice ¥53；buyPrice ¥40；maxWeight 1%；双项低于门槛，仅观察性例外 |
| growth | 思源电气 | 78 / 2026-06-17 | 80 / 2026-06-17 | 2026-07-14 | 已完成 | cScore 80；mScore 78；targetPrice ¥156；buyPrice ¥130；maxWeight 2%；管理层低于门槛，仅观察性例外 |
| growth | 华明装备 | 79 / 2026-06-08 | 74 / 2026-06-08 | 2026-07-14 | 已完成 | cScore 74；mScore 79；targetPrice ¥18.80；buyPrice ¥16；maxWeight 1%；双项低于门槛，仅观察性例外 |
| growth | 阳光电源 | 79 / 2026-07-08 | 80 / 2026-07-08 | 2026-07-08 | 已完成 | cScore 80；mScore 79；targetPrice ¥116；buyPrice ¥105；maxWeight 2%；管理层低于门槛，仅观察性例外 |
| growth | 史丹利 | 79 / 2026-06-27 | 76 / 2026-06-27 | 2026-07-14 | 已完成 | cScore 76；mScore 79；targetPrice ¥11.80；buyPrice ¥9；maxWeight 2%；双项低于门槛，仅观察性例外 |
| growth | 华能水电 | 72 / 2026-07-06 | 81 / 2026-07-06 | 2026-07-06 | 已完成 | cScore 81；mScore 72；targetPrice ¥8.80；buyPrice ¥7.50；maxWeight 2%；管理层低于门槛，仅观察性例外 |
| growth | 豪威集团 | 79 / 2026-07-08 | 75 / 2026-07-08 | 2026-07-08 | 已完成 | cScore 75；mScore 79；targetPrice ¥88；buyPrice ¥80；maxWeight 2%；双项低于门槛，仅观察性例外 |
| growth | 分众传媒 | 77 / 2026-07-14 | 82 / 2026-05-24 | 2026-07-14 | 已完成 | cScore 82；mScore 77；targetPrice ¥6.70；buyPrice ¥5.20；maxWeight 2%；管理层低于门槛，仅观察性例外 |
| growth | 金钼股份 | 74 / 2026-07-14 | 83 / 2026-05-22 | 2026-07-14 | 已完成 | cScore 83；mScore 74；targetPrice ¥22.20；buyPrice ¥17；maxWeight 2%；管理层低于门槛，仅周期观察性例外 |
| growth | 三环集团 | 78 / 2026-07-14 | 81 / 2026-05-29 | 2026-07-14 | 已完成 | cScore 81；mScore 78；targetPrice ¥76.12；buyPrice ¥70；maxWeight 1%；管理层低于门槛且估值极高，仅观察 |
| growth | Alphabet(Google) | Alphabet / 77 / 2026-07-14 | 谷歌 / 79 / 2026-07-05 | 谷歌 / 2026-07-05 | 已完成 | cScore 79；mScore 77；targetPrice $373；buyPrice $320；maxWeight 2%；旧85分深度分析已归档，双项低于门槛，仅观察性例外 |

## 本轮补齐估值并完成裁决（10 家）

| 档位 | 公司 | 管理层档案 | 深度分析 | 估值分析 | 状态 | 本轮裁决摘要 |
|---|---|---|---|---|---|---|
| core | 特宝生物 | 83 / 2026-07-14 | 80 / 2026-05-30 | 2026-07-15 | 已完成 | cScore 80；mScore 83；targetPrice ¥70；buyPrice ¥55；maxWeight 3% |
| growth | 银河娱乐 | 77 / 2026-07-14 | 80 / 2026-05-29 | 2026-07-15 | 已完成 | cScore 80；mScore 77；targetPrice HK$38；buyPrice HK$30；maxWeight 2%；管理层低于门槛 |
| growth | 百济神州 | 79 / 2026-07-14 | 79 / 2026-05-23 | 2026-07-15 | 已完成 | cScore 79；mScore 79；targetPrice ¥300；buyPrice ¥240；maxWeight 2%；双项低于门槛 |
| growth | 国投电力 | 77 / 2026-07-14 | 78 / 2026-05-17 | 2026-07-15 | 已完成 | cScore 78；mScore 77；targetPrice ¥16.5；buyPrice ¥13；maxWeight 2%；双项低于门槛 |
| growth | 爱柯迪 | 71 / 2026-07-14 | 79 / 2026-05-22 | 2026-07-15 | 已完成 | cScore 79；mScore 71；targetPrice ¥21；buyPrice ¥17；maxWeight 1%；治理约束明显 |
| growth | 双环传动 | 71 / 2026-07-14 | 79 / 2026-05-22 | 2026-07-15 | 已完成 | cScore 79；mScore 71；targetPrice ¥36；buyPrice ¥30；maxWeight 1%；机器人期权不预付 |
| growth | 中际旭创 | 75 / 2026-07-14 | 78 / 2026-05-19 | 2026-07-15 | 已完成 | cScore 78；mScore 75；targetPrice ¥780；buyPrice ¥620；maxWeight 1%；现价追高 |
| growth | 新宙邦 | 75 / 2026-07-14 | 78 / 2026-05-21 | 2026-07-15 | 已完成 | cScore 78；mScore 75；targetPrice ¥35；buyPrice ¥28；maxWeight 2%；现价偏贵 |
| growth | IBM | 78 / 2026-07-14 | 77 / 2026-05-22 | 2026-07-15 | 已完成 | cScore 77；mScore 78；targetPrice $245；buyPrice $205；maxWeight 2%；双项低于门槛 |
| growth | 联瑞新材 | 79 / 2026-07-14 | 75 / 2026-05-29 | 2026-07-15 | 已完成 | cScore 75；mScore 79；targetPrice ¥90；buyPrice ¥70；maxWeight 1%；估值与周期约束明显 |

## 已归档的先前审阅记录（不得作为本轮结论）

后续按公司追加：最新证据、事实/算术/逻辑纠正、唯一的 `cScore`、`mScore`、合理价值、买入价与最大仓位。每家公司完成前必须搜索并清除未标记的旧总分。

### NVIDIA（2026-07-15）

- 以原三份研究文档为编辑底稿：保留管理层的完整人物、言行、资本配置、组织、监管与引文结构，以及估值的六种方法、情景和敏感性分析。
- 公司质量统一为 86/100，管理层统一为 83/100；修复评分汇总、维度依据、红旗阈值、结论、frontmatter、内部链接和文件名。
- 估值将机械加权的 $232.85 明确为非目标价，保留其方法与重叠说明；唯一有效参数为目标价 $220、买入价 $180、最大仓位 4%。未修改 `watchlist_core.json`。

### 国电南瑞（2026-07-15）

- 在完整原报告中保留业务、护城河、财务、管理层履历、资本配置、风险和估值敏感性章节；修订评分理由而非以摘要替代正文。
- cScore 调整为 85，mScore 调整为 83，反映客户集中、项目回款、资本配置自主性、披露边界与换届验证期；同步修复汇总表、维度标题、结论、frontmatter、内部链接和文件名。
- 2026-07-14 收盘 ¥21.99、PE TTM 21.23x。五法的 ¥28.20 机械结果已明确为非目标价；唯一有效参数为目标价 ¥26、买入价 ¥21、最大仓位 4%。未修改 `watchlist_core.json`。

### 贵州茅台（2026-07-15）

- 保留深度分析的品牌、渠道、战略、财务、治理与风险章节，以及管理层档案的言行、资本配置、危机和组织记录；在原章节内将公司质量统一为 88、管理层统一为 80。
- 对行业调整、目标兑现、腐败反复、行政更替、批价和渠道风险做了独立扣分；不再以品牌护城河或低 PE 直接推导超过 10% 的仓位。
- 2026-07-14 收盘 ¥1,214.88、PE TTM 18.36x。五法的 ¥1,347 明确为非目标价；唯一有效参数为目标价 ¥1,250、买入价 ¥1,100、最大仓位 5%。未修改 `watchlist_core.json`。

### 招商银行（2026-07-15）

- 在原三文档中保留零售战略、资产质量、息差、资本回报、历史治理事件、银行估值方法与敏感性；公司质量调整为 82，管理层调整为 81。
- PB-ROE、DDM、逆向 DCF、PE 与 FCF Yield 共享盈利、ROE、分红和信用成本假设，原 ¥46 仅保留为机械敏感性结果。
- 唯一有效参数为目标价 ¥43、买入价 ¥36、最大仓位 5%；未修改 `watchlist_core.json`。

### 蜜雪集团（2026-07-15）

- 保留原报告对加盟供应链、门店、海外、食品安全、组织和估值敏感性的完整分析；公司质量调整为 79，管理层调整为 76。
- 将六法的 HK$284 标记为共享同店、门店和前瞻盈利假设的机械结果，不再作为目标价。
- 唯一有效参数为目标价 HK$250、买入价 HK$190、最大仓位 4%；未修改 `watchlist_core.json`。

### 卡特彼勒（2026-07-15）

- 保留原报告的经销商网络、服务生态、周期、Cat Financial、资本回报、合规和继任分析；公司质量调整为 84，管理层调整为 80。
- 将多法约 $580 标记为共享周期利润、订单和终值假设的机械结果；唯一有效参数为目标价 $600、买入价 $500、最大仓位 3%。
- 未修改 `watchlist_core.json`。
