# UTHR 中性证据增量 v1.2

- 获取日期：2026-09-12；信息截止日仍为 2026-09-12。
- 增量原因：匿名候选 C03/C04/C05/C08/C09 的决定性资料缺口；同一轮定向补证。
- 保留 v1、v1.1 及冻结原件，不覆盖原 facts.json、sources.json、market-snapshot.json。
- 下列金额除特别注明外为百万美元；事实不含评分或投资结论。

## 新增来源

| ID | 原件路径（相对本目录） | URL | SHA-256 |
|---|---|---|---|
| SProxy26 | uthr-2026-proxy-v1.2.html | https://www.sec.gov/Archives/edgar/data/1082554/000108255426000009/uthr-20260428.htm | E1EE79640164C395840ED82C083BD20FF949C10D5518606F8AFFD1CE31D0C9CD |
| SF4CEO0911 | form4-20260911-v1.2.xml | https://www.sec.gov/Archives/edgar/data/1082554/000110657826000139/primarydocument.xml | C5BDCAD63FC4B80EA9FCE2CF74D03667F5331D33FD2282BD2F9BAECC287FB9FE |
| SF4GC0903 | form4-20260903-v1.2.xml | https://www.sec.gov/Archives/edgar/data/1082554/000123158926000019/primarydocument.xml | 9EEED0266E0D6AB415646611689913648AF4B36C993B30CAAD5DA5B12B1284B1 |
| SHistory | market-history-v1.2.html | https://stockanalysis.com/stocks/uthr/history/ | 95D8EA6CC031CDB0DDC7E7599CE8CE044B29238D3AD1C6404BB85E5CFC40CA7A |
| SRatios | uthr-ratios-v1.2.html | https://stockanalysis.com/stocks/uthr/financials/ratios/ | 02C4CA46CF5C8EF7E29E73766E4520E643720F7A1334A64A95E90A29BEF790E8 |

SEC proxy 提交日 2026-04-29。Form 4 提交日分别为 2026-09-11、2026-09-03。两份行情原件为非官方补充数据；网页 Current 栏随抓取改变，历史年度栏单列使用。最初 PowerShell 请求因 User-Agent 标头格式校验失败，加入 SkipHeaderValidation 后成功，不存在首次失败原件。

## 代理文件事实

| 事实ID | 原值与口径 | 原件定位 |
|---|---|---|
| V12-G01 | Rothblatt 自 1996 年创立起任董事长兼 CEO；代理文件时董事会 13 人；Dwek 不再提名，股东会后拟减至 12 人 | SProxy26 pp.12–13、人物履历 |
| V12-G02 | 12 名非 CEO 董事被认定符合 Nasdaq 独立性标准；CEO 非独立董事 | SProxy26 p.14，Director Independence（按原件页脚核定位） |
| V12-G03 | Patusky 为首席独立董事；独立董事每年选任，可批准议程/会议安排、主持独立会议、召集执行会议及联系大股东 | SProxy26 p.22，Board Leadership Structure |
| V12-G04 | 审计委员会主席 Giltner，成员 Causey/Malcolm/Olian/Thompson；薪酬委员会主席 Patusky；提名治理主席 Causey | SProxy26 pp.23–24；人员为代理文件时点，Dwek 离任及后续董事补任须另桥 |
| V12-G05 | 现金激励四项各 25%：现金利润率、收入、制造、研发；长期激励为三年绩效期的 PSO/PSU，PSO 绑定现金利润率，PSU 绑定收入增长及研发 | SProxy26 pp.10、37–44 |
| V12-G06 | FY2025 收入目标 3,100；实际 3,182.7；制造指标包含最低库存和 GMP 检查；现金利润率指标非 GAAP，不等于 FCF | SProxy26 pp.37–40；FY2025 10-K F-6 |
| V12-G07 | CEO FY2025 Summary Compensation Table 总额 18,038,972 美元，FY2024 为 23,009,609 美元；不得与 Pay Versus Performance 的 149,876,842 美元混同 | SProxy26 Summary Compensation Table p.51、Pay Versus Performance pp.60–62 |
| V12-G08 | CEO 女儿 Jenesis FY2025 员工薪酬约 155,000 美元；总法律顾问儿子持有 50% 的服务公司获支付 145,000 美元，另向其个人支付 104,000 美元 | SProxy26 p.76，Related Party Transactions |
| V12-G09 | 关联交易书面政策审查门槛 100,000 美元；审计委员会主席可批准预计低于 500,000 美元的交易，并向委员会报告 | SProxy26 p.76，Review and Approval of Related Party Transactions |
| V12-G10 | 2026-04-10 Rothblatt 受益持股 2,867,290 股/6.5%，包含可行权期权 1,316,368+849,192 股；全体董事高管 3,916,335 股/8.6% | SProxy26 pp.77–78、脚注(1)(2)(7)；不是纯现股投票权，也不是9月持股 |
| V12-G11 | BlackRock 12.5%、Avoro 6.8% 的脚注基于 2023-12-31 披露；Wellington 5.8% 基于 2025-12-31；不得称这些均为9月最新持仓 | SProxy26 p.77、脚注(4)(5)(6) |

## Form 4 抽样

- V12-T01：SF4CEO0911，periodOfReport=2026-09-10；Rothblatt 行权 9,500 股，行权价 117.76 美元；同日 S 代码合计出售 9,500 股。
- S 行逐笔股数×披露加权价格合计 4,772,295.2024 美元（四舍五入 4.7723 百万美元），是毛出售额，不是净收益；不得再次计入 M 代码。
- F1 明确为 2025-11-07 预设 10b5-1 计划；上限 1,734,410 份期权；2026-12-31 或完成行权孰早结束；期权 2027-03-15 到期。
- V12-T02：SF4GC0903 报告人为 Paul Mahon（不是 CFO）；2026-09-03 行权并出售 8,300 股；行权价 146.03 美元；S 行毛额 4,000,836.3786 美元；F1 为 2025-08-11 计划。
- 抽样不能推出年度累计出售额，也不能推出完整剩余经济敞口。本轮没有归档全部 Form 4，不核认旧稿 274 百万美元。

## 行情与倍数原始观测

- V12-P01：SHistory 的历史表 2026-09-11 行 Close/Adj.Close 均列 497.11，成交量 359,153。
- 同源网页的浏览解析头部同时列“502.92，Sep 11 4:00 PM EDT close”及“497.11，7:30 PM EDT after-hours”；它与历史表存在时段冲突。不能将检索日 9 月 12 日当交易日。
- V12-P02：SRatios 的 FY2025/FY2024/FY2023 年末价格分别为 487.25/352.84/219.89；其 PE Ratio 分别 15.72/13.18/10.49，Market Capitalization 分别 20,979/15,752/10,333。
- 该 PE Ratio 是市值/净利润近似：20,979/1,334.7=15.718；与价格/全年加权稀释 EPS 不同。
- 结合 S10K25 F-6 已披露稀释 EPS 27.86/24.64/19.81，年末价格/同年稀释 EPS 重算分别为 17.4892/14.3198/11.0999 倍。它们是三个历史截面，不是连续历史分位，也不是 2027E 一致预期 PE。
- SRatios FY2021/FY2022 的 PE Ratio 为20.45/17.43；未经稀释 EPS 重桥，不与上行三项混为同口径序列。

## 既有原件补定位（不是新增公司事件）

| 事实ID | 原值/日期/口径 | 来源定位 |
|---|---|---|
| V12-F01 | 2026-06-30现金1,803.2、流动证券859.1、非流动证券1,141.1；合计3,803.4 | S10Q26Q2 p.3、Note 3 |
| V12-F02 | 流动证券中 AFS 债券780.4，其余78.7；非流动AFS1,141.1 | S10Q26Q2 Note 3；不能将所有证券等同现金 |
| V12-F03 | 2026-06-30 循环信贷已提款余额零；授信2,500、到期延至2031年4月 | S10Q26Q2 Note 7 Debt |
| V12-F04 | 2026H1 收入1,564.8/上年同期1,593.0；营业利润656.6/747.3；净利607.9/631.7；利息收入73.3/102.4 | S10Q26Q2 p.4 |
| V12-F05 | H1有效税率12%/24%，下降主因为SBC超额税收利益 | S10Q26Q2 Note 10 |
| V12-F06 | H1 OCF776.9、Capex208.8、SBC77.3；同期为652.9、137.1、69.6 | S10Q26Q2 p.8 |
| V12-F07 | FY2025 OCF1,561.2、Capex520.5、SBC147.7、利息收入192.0、税379.2、税前利1713.9 | S10K25 F-6及Consolidated Statements of Cash Flows |
| V12-F08 | 7月1日Thymmune首付约140，里程碑上限160（60截至2028年首次患者给药；100截至2031年BLA受理）；预期按资产收购计入Q3研发费用 | S10Q26Q2 Note 13 |
| V12-F09 | 2026年3月ASR预付1,500，总收股2,759,343，其中8月最后交付215,948股；9月新ASR约477.6、拟约9月10日首交719,376股、Q4终结算 | S10Q26Q2 Note 9；S8K0908 Item 1.01（后者为will，非已完成证明） |
| V12-F10 | H1 Tyvaso DPI656.9/617.7、雾化253.2/318.2、Remodulin252.9/272.9、Orenitram261.3/244.6、Unituxin118.8/116.6、Adcirca9.6/12.5、Other12.1/10.5 | S10Q26Q2 Note 11 pp.20–21 |
| V12-F11 | H1两分销商占比50%与36%；H1商业供应协议估计损失34.3，包含在库存准备费用64.1内，不能相加 | S10Q26Q2 Note 11 |
| V12-F12 | Yutrepia于2025年5月获PAH/PH-ILD最终批准、6月上市；剩余327专利诉讼涉及PH-ILD标签，并非禁止全部商业销售的既成结果 | S10Q26Q2 Note 12 |
| V12-F13 | Nebulized Tyvaso IPF TETON-1/2已成功并提交sNDA；ralinepag ADVANCE OUTCOMES已成功并于2026年6月提交NDA | S10Q26Q2 Item 2 Development Pipeline；均不等于获批 |
| V12-F14 | Sandoz反垄断等请求已判公司胜诉；合同请求2024-11-01判赔61.6+判前利息9.0+判后利息，双方上诉中 | S10Q26Q2 Note 12 |

## 既有 SEC Company Facts 的历史可得性

- V12-H01：FY2021 收入1,685.5、净利475.8、OCF598.2、Capex120.8；FY2022分别1,936.3、727.3、802.5、138.8。
- SFACTS 的 us-gaap tags：RevenueFromContractWithCustomerExcludingAssessedTax、NetIncomeLoss、NetCashProvidedByUsedInOperatingActivities、PaymentsToAcquirePropertyPlantAndEquipment；单位USD原值/1,000,000。
- 年度 start/end 必须同年1月1日至12月31日；2021可用accn 0001082554-24-000005，2022可用0001082554-25-000005。属于官方结构化历史值，相关更早年报本轮未另下载，不能称已全文核过历史原件。
- 本增量仅提供可得性和中性事实，决定性正常化调整仍须原件核对。
