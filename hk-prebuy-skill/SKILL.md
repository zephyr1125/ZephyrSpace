---
name: hk-prebuy
description: >-
  在用户准备买入某只港股前使用，用于做买入前基本面尽调、红旗排查和买入逻辑验证。
  适用场景：个股研究、买入前排雷、基本面核查、财报质量审视、现金流质量、商业模式分析、
  治理与股东行为、监管司法风险、估值合理性判断（含历史百分位、PEG、隐含增速）、
  价格走势与买入时机分析（近60日走势、量价异动、分档价格区间建议）、买入逻辑验证、红旗识别。
  港股特有风险：同股不同权(WVR)、VIE结构、做空机构、AH溢价、美国制裁/实体清单、流动性、南向资金、配股摊薄。
  适用市场：港股（H股/红筹/真港资公司/双重上市公司）。
  不适用于：A股、美股、纯短线技术分析、K线形态、日内交易。
---

# 港股买入前审视个股（HK PreBuy）

## 概览

这个技能把「准备买入一只港股」拆成一套最小但完整的研究流程，避免只看题材、K 线、估值或他人观点就下单。

港股与 A 股的核心差异在三点：
1. **信息不对称更大**：港股没有 A 股严格的问询函/强制披露体系，信息获取需要主动挖掘
2. **特有风险更复杂**：VIE 结构、同股不同权、做空机构、美国制裁风险均为港股独有
3. **数据源完全不同**：理杏仁不支持港股，需要用 HKEXnews、yfinance、stockanalysis.com 等替代源

默认目标不是直接给出「买/不买」，而是先回答 3 个问题：
- 这家公司到底靠什么赚钱
- 现在的市场定价到底在买什么预期
- 哪些变量一旦出错，会把这笔投资变成踩雷

## 核心原则

1. 先定义买入逻辑，再查数据。不要先看 PE 或股价。
2. 先用法定披露源（披露易 HKEXnews），再用媒体和卖方材料补充。
3. 港股没有「扣非净利润」标准科目，用「经营利润（EBIT/EBITDA）」和「经营现金流」代替。
4. 不只找支持结论的证据，必须同步写出反证条件。
5. 第一次买港股时，宁可错过，也不要带着未解核心疑点下单。

## 事实/推断/未知 三分法

输出时严格区分：
- **事实**：来自法定披露文件或权威来源，必须标注来源和日期
- **推断**：基于事实做出的分析判断，标明推理依据
- **未知**：当前未查到或无法核实，标注「待核实」并下调结论置信度

## 数据源总览

| 数据类型 | 优先来源 | 接口/方法 |
|---|---|---|
| **法定披露文件（年报/公告）** | 披露易 HKEXnews | `https://www.hkexnews.hk/` |
| **财务数据（营收/利润/ROE）** | stockanalysis.com | `web_fetch https://stockanalysis.com/quote/hkex/{code}/financials/` |
| **价格历史（近60日）** | yfinance | `yf.download("{code}.HK", period="3mo")` |
| **当前估值（PE/PB/市值）** | stockanalysis.com | `web_fetch https://stockanalysis.com/quote/hkex/{code}/` |
| **PE历史分位（手算）** | yfinance + stockanalysis | 年度EPS × 当前价格 = 历史PE序列 |
| **监管/处罚** | 证监会香港 SFC | `https://www.sfc.hk/` |
| **做空数据** | 港交所官方 | `https://www.hkex.com.hk/` 短仓报告 |
| **南向资金** | 港交所沪深港通 | `https://www.hkexnews.hk/sdw/search/` |
| **红旗/近期新闻** | Tavily | `prebuy_web_research(公司名, ticker)` |
| **评级/一致预期** | stockanalysis.com analysts tab | web_fetch |

> **理杏仁说明**：理杏仁仅覆盖 A 股（`cn/` 路径），港股数据不可用。本技能全程不使用理杏仁。

### yfinance 代码示例

```python
import yfinance as yf
from datetime import datetime, timedelta

# 港股 ticker 格式：4位代码+".HK"（不足4位补零）
# 腾讯=0700.HK, 招商银行H=3968.HK, 友邦=1299.HK

def get_hk_price_data(hk_code, days=90):
    """获取港股近N日行情数据"""
    ticker = f"{str(hk_code).zfill(4)}.HK"
    data = yf.download(ticker, period=f"{days}d", auto_adjust=True, progress=False)
    if data.empty:
        return None, None
    current_price = float(data['Close'].iloc[-1])
    return data, current_price

# 示例
data, price = get_hk_price_data("0700")
high_60 = float(data['High'].max())
low_60  = float(data['Low'].min())
print(f"当前价: HK${price:.2f}，近60日高: {high_60:.2f}，低: {low_60:.2f}")
```

### stockanalysis.com 财务数据获取

```python
from scripts.tavily_search import _get_client
# 或直接 web_fetch

# 年度财务数据
url_annual = f"https://stockanalysis.com/quote/hkex/{hk_code}/financials/"
# 季度财务数据（港股只有半年报，用年度即可）
url_ratios = f"https://stockanalysis.com/quote/hkex/{hk_code}/financials/ratios/"
# 资产负债表
url_balance = f"https://stockanalysis.com/quote/hkex/{hk_code}/financials/balance-sheet/"
# 现金流量表
url_cash    = f"https://stockanalysis.com/quote/hkex/{hk_code}/financials/cash-flow-statement/"
```

---

## 默认工作流

### 第 0 步：确认标的信息

先确认：
- 港股代码（4位数字，如 `0700`）和公司全称
- 公司类型：H 股（A+H双重上市）/ 红筹（国企在港上市） / 真港资公司 / 科技/互联网中概股
- 想做完整研究，还是快速排雷
- 是否存在 A+H 双重上市（若有，确认分析对象是 H 股）

**公司页处理规则（检查 `01-公司/` 是否已有对应页面）：**

| 用户描述 | 处理方式 |
|---|---|
| 「重新 PreBuy」/「从头 PreBuy」/「重做」 | **先删除**现有公司页，再按模板从头创建 |
| 「更新」/「刷新」/「中期业绩更新」 | **保留**现有页面，在原有章节基础上覆盖更新数据 |
| 首次分析（页面不存在） | 按模板新建 |

### 第 1 步：固定查 14 个模块

#### 模块 1：公司到底赚什么钱

必查：
- 年报/中期报告里的主营业务和收入构成
- 分产品、分行业、分地区收入（港股年报通常有分部信息）
- 官网产品页和解决方案页

要回答：
- 热门业务在总收入中的占比有多大
- 这家公司到底是纯标的，还是平台型公司
- 收入是 HKD/USD/RMB 计价（汇率影响）

红旗：
- 热门业务讲得很大，但收入占比极小
- 业务分类太粗，故意模糊利润来源
- RMB 计价收入公司，HKD 汇率变动会系统性影响折算利润

#### 模块 2：行业位置与壁垒

必查：
- 主要客户、认证、市场份额
- 行业中的角色：平台商、设备商、零部件商、运营商
- 与全球竞争对手的对比（港股公司往往面向全球竞争）

要回答：
- 它是行业龙头、跟随者，还是单一客户附庸
- 护城河来自技术、品牌、网络效应、转换成本，还是仅靠景气
- 同类公司在全球或 A 股是否有更好的替代投资标的

红旗：
- 只说布局，不说客户和市场份额
- 护城河依赖单一大客户（如政府合同、单一科技巨头采购）

#### 模块 3：增长质量

必查：
- 营收、净利润（Profit Attributable to Owners）
- 毛利率、净利率、ROE
- 至少看 3 年趋势（stockanalysis.com financials/ratios 页面）

> ⚠️ **港股无「扣非净利润」标准科目**：港股年报遵循 HKFRS，投资物业公允价值变动、金融资产收益等均可能计入利润。查「核心经营利润（Core Operating Profit）」或「除税前溢利（Profit Before Tax）」更能反映业务真实情况。

要回答：
- 增长是主营拉动，还是一次性项目拉动（公允价值变动/出售资产）
- ROE 是靠净利率、资产周转率，还是杠杆拉出来的（杜邦分解）

红旗：
- 净利润增长明显快于经营现金流
- 利润严重依赖投资物业公允价值变动（地产公司常见）
- 利润依赖出售子公司/联营公司

#### 模块 4：现金流与营运资金

必查：
- 经营活动现金流净额（Cash from Operations）
- 应收账款、存货周转天数趋势
- 自由现金流（FCF = 经营现金流 - 资本支出）

要回答：
- 账面利润是否真的变成了现金
- 公司是否靠加杠杆或拖延付款撑增长

红旗：
- 利润向上但经营现金流持续恶化
- 应收和存货同时大涨（警惕"塞货式"收入）
- FCF 连续多年为负（资本密集型以外）

#### 模块 5：资本结构与再融资风险

必查：
- 有息负债结构（短期/长期占比）
- 净负债率（Net Debt / EBITDA）
- 港股配股（Placing）、供股（Rights Issue）历史
- 可换股债券（CB）余额及转换价格

要回答：
- 扩张靠内生现金流，还是靠外部融资
- 短期偿债压力是否在放大

> ⚠️ **港股配股机制**：港交所允许上市公司在无需股东批准的情况下，用现有授权股份额度（一般不超过总股本 20%）快速配股（Placing）。这是港股摊薄风险比 A 股更隐蔽的原因——没有公告预告期，可以一夜之间完成配股。

红旗：
- 频繁配股或供股（3 年内 2 次以上大规模再融资）
- 大折价供股（折价 >20%，通常意味着公司急需现金）
- 可换股债券转换价接近当前股价（转换压力大）

#### 模块 6：资产质量

必查：
- 审计意见（港股须为核数师无保留意见）
- 商誉（Goodwill）余额及减值测试说明
- 投资物业（Investment Properties）公允价值变动方向
- 财务附注中的关键审计事项（KAMs）

优先规则：审计报告里写什么，就优先查什么。

红旗：
- 非无保留意见（**一票否决**）
- 商誉占净资产 >50%，且被收购标的所在行业景气下行
- 投资物业占资产主体（>30%），且当地房价处于下行周期（主要见于香港本地地产公司）

#### 模块 7：治理与股东回报

必查：
- 控股股东身份及持股比例（HKEXnews 权益披露）
- 分红历史（Dividend History）及派息率（Payout Ratio）
- 股份回购记录（Share Buyback）
- 独立非执行董事（INED）比例及独立性
- 关联交易（Related Party Transactions）

要回答：
- 管理层是否长期站在小股东同一边
- 有没有明显的资本运作痕迹重于经营

红旗：
- 实际控制人通过复杂控股链掌控公司（VIE 结构另见模块11）
- 连续多年不分红且无回购，但高管薪酬持续增长
- 独立非执行董事与控股股东关系密切（董事会独立性存疑）

数据来源：
- HKEXnews 权益披露查询：`https://www.hkexnews.hk/sdw/search/searchsdw_c.aspx`
- 年报附注「关联方交易」章节

#### 模块 8：监管与司法风险

必查：
- 香港证监会（SFC）执法行动记录：`https://www.sfc.hk/`
- 港交所上市委员会决定（HKEXnews 公告分类）
- 内地监管风险（国家安全、反垄断、行业政策）
- 美国 SEC 相关风险（适用于 ADR 或有美国业务的公司）
- 国际制裁（OFAC / 英国 / 欧盟）

要回答：
- 公司或主要高管是否受到监管调查/处罚
- 内地业务是否面临政策强监管周期（历史教训：教育、互联网平台、房地产）

红旗：
- 🔴 SFC 对公司/高管启动正式调查（**一票否决**）
- 🔴 内地业务收到监管整改通知且未见实质改善
- 🔴 被列入美国 OFAC 制裁名单或 Entity List（**一票否决**）
- 🟡 行业处于内地首轮强监管期（政策底尚未明确）
- 🟡 内地业务依赖政策补贴，补贴续期不确定

#### 模块 9：估值与买入赔率

必查：
- 当前 PE_TTM、PB（stockanalysis.com 首页概览）
- PEG（PE ÷ 预期未来 2-3 年净利润增速）
- 历史估值区间（至少 3 年 PE/PB 分位，手算方法见下）
- 当前估值隐含的盈利假设（隐含增速）

> **港股估值历史分位手算方法**（无理杏仁，用 yfinance + 报告期 EPS）：

```python
import yfinance as yf
import pandas as pd

def calc_hk_valuation_history(hk_code, annual_eps_dict):
    """
    计算港股历史 PE 分位。
    annual_eps_dict: {年份: EPS(HKD)} 例如 {2022: 1.2, 2023: 1.8, 2024: 2.1}
    """
    ticker = f"{str(hk_code).zfill(4)}.HK"
    hist = yf.download(ticker, period="3y", auto_adjust=True, progress=False)['Close']
    
    pe_history = []
    for year, eps in annual_eps_dict.items():
        if eps <= 0:
            continue
        year_prices = hist[hist.index.year == year]
        if year_prices.empty:
            continue
        avg_price = float(year_prices.mean())
        pe_history.append(avg_price / eps)
    
    # 当前价格
    current_price = float(hist.iloc[-1])
    latest_eps = list(annual_eps_dict.values())[-1]
    current_pe = current_price / latest_eps if latest_eps > 0 else None
    
    if pe_history:
        pe_series = pd.Series(pe_history)
        percentile = (pe_series < current_pe).mean() if current_pe else None
        q20 = pe_series.quantile(0.2)
        q50 = pe_series.quantile(0.5)
        q80 = pe_series.quantile(0.8)
        return {
            "current_pe": round(current_pe, 1),
            "percentile_3y": round(percentile * 100, 0) if percentile else None,
            "q20_pe": round(q20, 1),
            "q50_pe": round(q50, 1),
            "q80_pe": round(q80, 1),
        }
    return None

# 使用示例（EPS 从 stockanalysis.com 或年报手动获取）
result = calc_hk_valuation_history("0700", {2022: 8.5, 2023: 14.2, 2024: 18.1})
# result["percentile_3y"] = 3年PE历史分位（0-100%）
```

**price_bands 港股计算方法**（基于历史 PE 分位 × EPS）：

```python
def calc_hk_price_bands(current_price, latest_eps, q20_pe, q50_pe, q80_pe):
    """
    用历史估值分位计算港股 price_bands。
    返回 [红线(P80价格), 中性底(P50价格), 最优区起点(P20价格)]
    """
    if latest_eps <= 0:
        return None  # 亏损公司改用 PB 分位，需手动计算
    return [
        round(q80_pe * latest_eps, 2),
        round(q50_pe * latest_eps, 2),
        round(q20_pe * latest_eps, 2),
    ]
# 灯号判断：当前价 > bands[0] → 🔴；bands[1]~bands[0] → 🟡；< bands[2] → 🟢🟢
```

红旗：
- 只拿横向 PE 比，不看业务纯度和增长质量
- PE 处于历史 3 年 80% 分位以上且增速放缓
- 亏损公司用 PB 分位：PB > 历史 80% 分位同样高风险

#### 模块 10：催化剂与验证时间线

必查：
- 下次财报披露时间（**先判断是否季报公司，再查日期——见下方说明**）
- 关键订单、新产能、监管审批节点
- 诉讼/处罚进展
- 大股东/机构增减持窗口

> ⚠️ **港股财报节奏**（大多数只有半年报和年报，但存在重要例外）：
>
> | 报告类型 | 财年结束后截止日 | 典型时间 |
> |---|---|---|
> | 年度业绩（Annual Results）| 财年结束后 4 个月内 | 3月（12月财年）|
> | 中期业绩（Interim Results）| 半年度结束后 3 个月内 | 8月（12月财年）|
>
> 注意：部分港股公司财年不在 12 月结束（银行常为 3/31，太古为 6/30），须查年报确认。
>
> **⚠️ 季报例外（重要）**：以下类型的港股公司会额外发布季度业绩，下次财报类型应填 `季度业绩（Q1/Q2/Q3）`，不能默认用「中期业绩」：
> 1. **自愿季报公司**：腾讯控股（00700.HK）自 2004 年起每季度发布业绩，是港股中极少数自愿季报的大型科技公司
> 2. **美股双重上市公司**：在纽交所/纳斯达克同时上市的港股（如中通快递 02057.HK/ZTO），跟随美国市场惯例发布季度财报
>
> **识别方法**：在 HKEXnews 公告历史中搜索公司过去 12 个月的「业绩公告」，若出现 4 次以上则为季报公司。
> 或者在 stockanalysis.com 该公司页面查看历史财报频率。

要回答：
- 未来 2 个月最关键的验证指标是什么
- 如果哪个指标不达标，逻辑就要修正

#### 模块 11：港股特有风险因子（必做，A 股无对应）

港股市场存在若干在 A 股不常见、但在港股投资中必须单独检查的风险点。

---

**11.1 同股不同权（WVR / 加权投票权结构）**

必查：
- 公司章程（Articles of Association）或上市文件是否声明 WVR 结构
- WVR 持有人（通常是创始人）的投票权比例 vs 经济权益比例
- 港交所是否将该公司纳入「WVR 公司」名单

涉及公司（代表性）：腾讯（无 WVR）、美团、小米、京东健康、快手等科技公司多采用。

红旗：
- 🔴 创始人持有 <10% 股权但控制 >50% 投票权，且无良好治理记录
- 🔴 WVR 结构叠加实控人减持——实控人可以一边卖股票一边保留控制权
- 🟡 WVR 公司不符合沪深港通资格（南向资金无法介入，流动性折价）

---

**11.2 VIE 结构风险**

必查：
- 招股书/上市文件是否披露 VIE（可变利益实体）结构
- VIE 结构中境外持股人（如开曼公司）对境内运营实体的控制方式
- 中国监管层近年对 VIE 结构的态度（2021年互联网监管、数据安全法等）

> **VIE 本质风险**：境外股东对境内运营实体的控制依赖合同安排，而非股权持有。一旦合同被认定无效，或中国法律禁止外资持有该业务，境外上市主体将失去对实际业务的控制权，股票理论上价值归零。

红旗：
- 🔴 监管层明确表态规范/限制该类业务的外资持有（如 2021 年教育双减）
- 🔴 VIE 结构下境内主要运营公司发生股权纠纷或管理层变动
- 🟡 VIE 协议已超过 10 年未更新，法律风险累积

---

**11.3 大股东权益变动**

港股权益披露规则：持股 5% 以上时，每次变动超过 1% 须在 3 个业务日内公告（HKEXnews 权益披露）。

必查：
- HKEXnews 权益披露：`https://www.hkexnews.hk/sdw/search/searchsdw_c.aspx`
- 近 6 个月大股东（5% 以上）买入/卖出记录
- 创始人/管理层是否通过配售等方式减持

```python
# 权益披露查询 URL
url = "https://www.hkexnews.hk/sdw/search/searchsdw_c.aspx"
# 输入公司代码和日期范围，查询所有 5% 以上权益变动
# 也可 web_fetch 公司在 HKEXnews 的公告，按「权益披露」分类筛选
```

红旗：
- 🔴 创始人/控股股东在过去 3 个月内减持 >2% 持股
- 🔴 多名高管同期减持，且减持后持仓接近 5% 披露门槛以下
- 🟡 主要机构股东（持 >5%）连续两期减持

---

**11.4 美国制裁 / 实体清单风险**

必查：
- OFAC（美国财政部）制裁名单：`https://sanctionssearch.ofac.treas.gov/`
- BIS（美国商务部）实体清单（Entity List）
- 公司或关联方是否涉及被制裁的中国军工/技术实体

> ⚠️ 这是港股中资科技/国防/电信公司独有的重大风险。被列入实体清单后，美国技术和零部件断供，可能导致业务根本性损害，港股价格大幅下跌。历史案例：华为（非上市）、中兴（补救）、海康威视（港股估值长期折价）。

红旗：
- 🔴 公司本身或主要子公司已在 OFAC 制裁名单 / BIS 实体清单（**一票否决**）
- 🔴 公司依赖美国进口关键技术/零部件，且中美关系持续恶化
- 🟡 公司具有军民两用技术，存在未来被列入制裁名单的潜在风险

---

**11.5 港股流动性风险**

港股中小市值公司流动性可能极差，买入容易、卖出难。

必查：
- 近 20 日日均成交额（HKD）
- 主要机构股东集中度（前 10 大股东总持股比例）
- 是否纳入港股通（沪深港通）

评估标准：
| 市值规模 | 安全日均成交额 |
|---|---|
| <50亿 HKD | >2000万 HKD/日 |
| 50-200亿 HKD | >5000万 HKD/日 |
| >200亿 HKD | 通常无流动性问题 |

红旗：
- 🔴 日均成交额 < 1000万 HKD（卖出时可能大幅影响价格）
- 🔴 未纳入港股通，南向资金无法参与（缺乏重要流动性来源）
- 🟡 前 10 大股东持仓 >80%，自由流通筹码极少

---

**11.6 做空机构风险**

港股允许自由卖空，国际做空机构（浑水 Muddy Waters、Hindenburg 等）高度活跃。

必查：
- 港交所官方做空数据（每日短仓报告）：`https://www.hkex.com.hk/`
- Tavily 搜索公司名 + "short seller" / "做空报告" / "Muddy Waters"
- 短仓比例（Short Interest % of Float）

```python
from scripts.tavily_search import _get_client, _fmt
client = _get_client()
result = client.search(
    f"{公司名} {ticker} short seller muddy waters hindenburg 做空",
    max_results=5, search_depth="advanced"
)
```

红旗：
- 🔴 被知名做空机构发布报告（核实报告核心指控后判断）
- 🔴 短仓比例异常飙升（>10% 且近期明显上升）
- 🟡 历史上曾被做空但未发现实质性问题（市场有心理印象，估值长期折价）

---

**11.7 AH 溢价 / 折价（仅 A+H 双重上市公司）**

若公司同时在 A 股和港股上市（如中行、建行、招商银行等），必须分析 AH 价差。

必查：
- 当前 AH 溢价率（A 股价格 / H 股价格 - 1）
- 历史 AH 溢价率区间及当前分位
- 沪深港通南向资金近期净流入/流出

```
AH 溢价率 = (A 股价格 ÷ H 股价格) - 1
正值 = A 股贵于 H 股（常见状态，H 股享受折价）
负值 = A 股便宜于 H 股（罕见，通常为 A 股受到打压）
```

分析要点：
- AH 溢价 > 历史 80% 分位 → H 股相对更便宜，南向资金有套利动力
- AH 溢价 < 历史 20% 分位 → H 股折价优势收窄，吸引力下降
- 溢价短期大幅收窄（A 股暴跌或 H 股大涨）→ 均值回归压力

---

**11.8 港股再融资（配股/供股）风险**

港股再融资机制与 A 股不同，速度快且无需提前公告。

必查：
- 公司章程中的「一般授权」（General Mandate）额度（通常为已发行股本 20%）
- 近 3 年配股/供股历史（频率和规模）
- 可换股债券（CB）余额及转换触发条件

红旗：
- 🔴 过去 3 年 2 次以上大规模配股（频繁摊薄中小股东）
- 🔴 供股折价 >20%（急需现金的信号）
- 🟡 可换股债券转换价接近当前股价（潜在大量股份兑换压力）

---

#### 模块 12：政策顺逆风评估（H 股/内地业务为主的公司必做）

> ⚠️ **适用范围判断**：
> - **H 股 / 内地业务为主的公司**（如招商银行 H、腾讯、中国移动）：执行完整政策评估
> - **纯港资公司**（如汇丰控股、长和系、恒生银行）：内地政策影响有限，仅评估香港本地政策，可简化执行

**12.1 读取生效中的政治会议页**

读取 vault 目录 `06-政治会议/` 下所有 `.md` 文件，筛选 frontmatter 中 `生效截止` ≥ 今天的页面作为**有效政策集**。

```python
import os, re
from datetime import date

vault_dir = r"E:\ObsidianVaults\ZephyrSpace\06-政治会议"
today = date.today().isoformat()
active = []
for fname in os.listdir(vault_dir):
    if not fname.endswith('.md'): continue
    text = open(os.path.join(vault_dir, fname), encoding='utf-8').read()
    m = re.search(r'生效截止[:：]\s*(\d{4}-\d{2}-\d{2})', text)
    if m and m.group(1) >= today:
        active.append(fname)
print(active)
```

> 若目录不存在或无生效页面，跳过本模块，在输出中注明「无生效政策」。

**12.2 政策净得分（PS）计算**

对照规则同 A 股版本：
- 利好信号：⭐=+1 / ⭐⭐=+2 / ⭐⭐⭐=+3
- 利空信号：固定 -2
- 汇总 PS = Σ 利好得分 - Σ 利空得分

**12.3 港股特殊政策考量**

| 政策风险 | 触发条件 | 影响 |
|---|---|---|
| 内地监管强周期 | 行业被列为重点监管（如 2021 互联网、教育） | PS 额外 -3，结论降档 |
| 香港本地政策风险 | 如土地政策变化（影响地产/建筑） | 在港业务比例加权 |
| 中美关系恶化 | 半导体/军民两用技术相关公司 | 制裁风险升级（见模块11.4）|
| 人民币汇率 | 主要收入为 RMB 的 H 股 | 汇率折算影响每股 HKD 盈利 |

#### 模块 13：周期位置判断（周期股专属，非周期股跳过）

执行逻辑与 A 股版相同，数据来源改为：
- **PB/PE 历史数据**：yfinance 价格 + stockanalysis.com 历史 EPS/BPS 手算
- **行业产品价格**：LME（有色金属）、Platts（能源）、Bloomberg 大宗商品数据（web_fetch）
- **Capex 趋势**：公司年报资本支出科目（Cash Flow Statement）

周期位置阶段判断标准与 A 股版本相同（底部/复苏早期/复苏中期/景气高峰/收缩期/出清期）。

#### 模块 14：价格走势与买入时机

必查：
- 近 60 个交易日行情数据（yfinance）
- 近期重大事件对应的价格反应
- 港股通日均净流入（南向资金）

```python
import yfinance as yf
from datetime import date, timedelta

hk_code = "0700"  # 替换为目标代码
ticker = f"{str(hk_code).zfill(4)}.HK"

# 近90日数据（确保取到60个交易日）
end = date.today().isoformat()
start = (date.today() - timedelta(days=130)).isoformat()
data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)

# ⚠️ yfinance 返回的日期索引已按升序排列，无需再排序
current_price = float(data['Close'].iloc[-1])
high_60 = float(data['High'].tail(60).max())
low_60  = float(data['Low'].tail(60).min())
ret_30d = (float(data['Close'].iloc[-1]) / float(data['Close'].iloc[-30]) - 1) * 100
ret_60d = (float(data['Close'].iloc[-1]) / float(data['Close'].iloc[-60]) - 1) * 100

print(f"当前价: HK${current_price:.2f}")
print(f"60日高: {high_60:.2f}  60日低: {low_60:.2f}")
print(f"近30日涨跌: {ret_30d:.1f}%  近60日涨跌: {ret_60d:.1f}%")
```

价格区间输出格式：

| 价格区间 (HKD) | 对应 PE 约 | 风险评估 |
|---|---|---|
| X 以上 | xx倍+ | 🔴 追高区 |
| X-Y | xx-yy倍 | 🟡 中性区，可关注但需等确认 |
| Y-Z | yy-zz倍 | 🟢 较好入场区间 |
| Z 以下 | <zz倍 | 🟢🟢 安全边际充足 |

---

### 第 2 步：固定查这些资料

优先顺序：
1. **法定披露文件**：年报、中期报告、临时公告（披露易 HKEXnews）
2. **核数师报告与财务附注**（HKFRS，注意投资物业/金融工具处理）
3. **公司业绩说明会纪要、路演资料**
4. **SFC 执法通报、港交所上市委员会决定**
5. **公司官网产品资料**
6. **Tavily 网络调研**（红旗/近期新闻/竞争格局）

```python
from scripts.tavily_search import prebuy_web_research

# 一次性获取红旗 + 近期事件 + 公司信息
result = prebuy_web_research(公司名, f"{hk_code}.HK")
# result["red_flags"]      → 监管处罚/做空报告/负面事件
# result["recent_news"]    → 业绩发布/并购/管理层变动
# result["company_info"]   → 主营业务/竞争格局
```

### 第 3.5 步：确认下一期财报日期（港股版）

> ⚠️ **踩坑记录（2026-05）**：腾讯控股和中通快递的 `next_earnings_type` 曾被错误填为「中期业绩」，实际均为季报公司，应为「季度业绩（Q1）」。
> **原因**：Skill 曾硬编码「港股无季报」，导致所有公司统一套用半年/年报逻辑，完全漏掉季报例外。
> **教训**：对任何双重上市公司或知名大型科技公司，必须先验证财报频率，不可默认套用常规逻辑。

**第一步：先判断是否季报公司（必做，不可跳过）**

已知季报公司列表（持续维护，遇到新的随时补充）：

| 公司 | 代码 | 季报原因 |
|---|---|---|
| 腾讯控股 | 00700.HK | 自愿季报，自2004年起每季披露 |
| 中通快递 | 02057.HK | 在NYSE(ZTO)双重上市，遵循美国季报惯例 |
| 阿里巴巴（港股） | 09988.HK | 在NYSE(BABA)双重上市 |
| 京东集团（港股） | 09618.HK | 在NASDAQ(JD)双重上市 |
| 百度集团（港股） | 09888.HK | 在NASDAQ(BIDU)双重上市 |
| 网易（港股） | 09999.HK | 在NASDAQ(NTES)双重上市 |

**若公司不在以上列表**，通过以下方式快速判断：

```python
# 方法1：检查 stockanalysis.com 历史财报频率
# web_fetch https://stockanalysis.com/quote/hkex/{4位代码}/financials/?p=quarterly
# 如果有季度财务数据，即为季报公司

# 方法2：搜索 HKEXnews 近12个月公告标题含 "季度"/"quarterly"
# https://www.hkexnews.hk/listedco/listconews/search/search_active_main_c.aspx
```

**第二步：根据频率调用对应函数**

```python
from datetime import date

# ===== 季报公司（美股双重上市 or 腾讯等自愿季报）=====
KNOWN_QUARTERLY_REPORTERS = {
    "00700", "02057", "09988", "09618", "09888", "09999"
}

def get_hk_next_earnings(hk_code_4digit, fiscal_year_end_month=12, today=None):
    """
    估算港股下一期业绩发布时间。
    hk_code_4digit: 4位数字代码（不带.HK），如 "0700"
    fiscal_year_end_month: 财年结束月份（大多数为12月）
    返回 (date_str, report_type)
    """
    if today is None:
        today = date.today()
    y, m = today.year, today.month

    # 季报公司：按季度估算下一期
    if hk_code_4digit.lstrip("0") in {c.lstrip("0") for c in KNOWN_QUARTERLY_REPORTERS}:
        # Q1 约5月，Q2（中期）约8月，Q3 约11月，Q4（年报）约3月
        if m < 5:
            return f"{y}-05-15", "季度业绩（Q1）"   # 具体日期查公司公告确认
        elif m < 8:
            return f"{y}-08-15", "季度业绩（Q2/中期）"
        elif m < 11:
            return f"{y}-11-15", "季度业绩（Q3）"
        else:
            return f"{y+1}-03-31", "年度业绩"

    # 普通半年报/年报公司
    if fiscal_year_end_month == 12:
        # 年报：3月31日前；中期：8月31日前
        if m < 4:
            return f"{y}-03-31", "年度业绩"
        elif m < 9:
            return f"{y}-08-31", "中期业绩"
        else:
            return f"{y+1}-03-31", "年度业绩"
    else:
        # 非12月财年：需查公司年报确认，此处仅做粗略估算
        return "待确认（非12月财年）", "请查年报确认财年结束月份"

# 使用示例
next_date, next_type = get_hk_next_earnings("0700")  # 腾讯 → 季报
next_date, next_type = get_hk_next_earnings("1299")  # 友邦 → 半年报
```

> ⚠️ **季报公司的具体日期必须核实**：`KNOWN_QUARTERLY_REPORTERS` 只提供类型判断，具体日期（如腾讯2026年Q1是5月13日）必须通过 Tavily 搜索或 HKEXnews 公告确认，函数返回值只是参考区间，不可直接写入 watchlist。

将结果写入公司页 frontmatter：
```yaml
下一财报日: 2026-08-31
下一财报类型: 中期业绩
```

# 季报公司示例：
```yaml
下一财报日: 2026-05-13
下一财报类型: 季度业绩（Q1）
```

### 第 3.6 步：计算 price_bands 并写入 watchlist

**港股 price_bands 计算方法**（用历史 PE/PB 分位 × 每股盈利/净资产）：

```
price_bands[0]（追高线）= Q80 PE × 最新年化 EPS
price_bands[1]（中性底）= Q50 PE × 最新年化 EPS
price_bands[2]（最优区）= Q20 PE × 最新年化 EPS
```

银行/保险改用 PB 分位：
```
price_bands[0] = Q80 PB × 最新每股净资产（BPS）
```

写入格式：
```json
{
  "price_bands": [HKD数字, HKD数字, HKD数字],
  "price_bands_basis": "pe_ttm.manual_3y",
  "price_bands_date": "2026-05-09"
}
```

`price_bands_basis` 取值说明：
- `pe_ttm.manual_3y`：手算3年PE分位
- `pb.manual_3y`：手算3年PB分位（银行/保险）
- 政策加成后追加 `+psN`，如 `pe_ttm.manual_3y+ps2`

### 第 4 步：写反证条件

每次都要写至少 3 条「我为什么可能错」。

港股常见反证来源：
- 内地政策超预期收紧
- VIE 结构被迫重组
- 人民币大幅贬值（影响 H 股 HKD 折算利润）
- 做空报告发布，短期流动性崩溃
- 美国制裁升级
- AH 溢价快速收窄（A 股大跌拖累 H 股）

### 第 5 步：最后才讨论买不买

综合基本面结论（模块 1-12）和政策加权结果（模块 13），选择最终口径。若模块 13 的 PS 触发了升降档，在结论中明确写出加权理由，不能静默调整。

### 第 6 步：写入公司索引页

> ⚠️ **此步骤为必做步骤，不得跳过。** 每次完成 PreBuy 分析并创建/重建公司页后，必须同步更新 `00-首页/公司索引.md`，否则公司页将无法被索引发现。

具体操作：
1. 打开 `00-首页/公司索引.md`
2. 在「港股」区块中，按 **4 位代码升序**插入 `[[公司名]]（XXXXX）` 链接
3. 同步修改文件顶部的总计数（+1）和日期

**代码示例（Python 读写）**：
```python
index_path = r"E:\ObsidianVaults\ZephyrSpace\00-首页\公司索引.md"
with open(index_path, "r", encoding="utf-8") as f:
    content = f.read()

# 在「港股」区块的代码排序位置插入新行（找到插入锚点）
new_entry = "- [[公司名]]（XXXXX）\n"
# 手动定位到正确位置插入（按代码升序）
# 或在「## 港股」后的第一个代码高于本公司的条目前插入
with open(index_path, "w", encoding="utf-8") as f:
    f.write(updated_content)
```

---

## 红旗分级（港股版）

- **一票否决型**：SFC/OFAC 制裁、财务造假、非无保留审计意见、VIE 结构被中国监管明确叫停
- **高风险型**：经营现金流长期背离利润、大股东频繁减持、被知名做空机构发布报告、高比例配股/供股
- **观察型**：估值偏高、WVR 结构存在但创始人信誉良好、AH 溢价处于高位、流动性偏低

出现一票否决型红旗时，结论必须为「核心疑点未解，不建议买入」。

---

## 价值投资常见认知陷阱（港股补充版）

### 陷阱 1–9（同 A 股版本）

低 PE 等于便宜 / 护城河免死金牌 / 只看利润不看现金流 / 把长期持有当不止损 / 静态估值判断周期股 / 高杠杆伪装高ROE / 叙事强度≠投资价值 / 仓位管理缺失 / 读懂逻辑≠有能力估值

### 陷阱 10：把「H 股折价」当成安全边际

H 股长期折价于 A 股（AH 溢价为正），但折价有其原因：
- 港股流动性较 A 股差（部分公司）
- 南向资金进出有限制
- 国际投资者对中国风险要求更高回报

> 检查项：这家公司的 H 股折价是真实的低估，还是 A 股高估？H 股折价是在收窄还是扩大？

### 陷阱 11：忽视 HKFRS 与 A 股会计准则差异

HKFRS 下投资物业公允价值变动计入损益，A 股会计不允许。地产公司在港股报告的净利润中，公允价值收益可能占据大头——当楼市下行，这部分利润可以快速反转。

> 检查项：该公司利润中有多少来自投资物业公允价值变动？剔除后的经营利润是多少？

### 陷阱 12：做空机构报告恐慌性卖出

做空报告发布后股价暴跌，但并非每次都意味着公司有实质问题。

> 检查项：做空报告的核心指控是什么？是会计造假（高风险）还是商业模式质疑（可辩驳）？公司是否在合理时间内给出了实质性回应？

---

## 标准输出格式

### A. 公司一句话

一句话说明公司本质（含 HK 代码、公司类型：H 股/红筹/港资/中概科技）。

### B. 买入逻辑

只写 2-4 条，且每条必须可验证。每条附来源（文件名 / 平台名 + 日期）。

### C. 必盯指标

至少包含：
- 营收或核心经营收入
- 经营利润或毛利率（HKFRS 框架下剔除公允价值变动）
- 经营现金流（FCF）

### D. 核心雷点

至少写 3 条，按红旗分级排序。必须包含港股特有风险中最高等级的项目。

### E. 催化剂与时间线

列出未来 2 个月的关键验证节点（下次中期/年度业绩时间）。

### F. 港股特有风险检查（必做）

灯号说明：🟢 无明显风险 / 🟡 需跟踪，有一定压力 / 🔴 重大负面信号

| 风险项 | 灯号 | 说明 |
|---|---|---|
| 同股不同权（WVR） | 🟢/🟡/🔴 | 是否存在，创始人投票权vs经济权益比 |
| VIE 结构 | 🟢/🟡/🔴 | 是否存在，监管风险评估 |
| 大股东权益变动 | 🟢/🟡/🔴 | 近6个月披露，买入/卖出方向 |
| 美国制裁/实体清单 | 🟢/🟡/🔴 | OFAC/BIS 名单核查结果 |
| 港股流动性 | 🟢/🟡/🔴 | 日均成交额，港股通资格 |
| 做空机构风险 | 🟢/🟡/🔴 | 是否有活跃做空报告，短仓比例 |
| AH 溢价/折价 | 🟢/🟡/🔴 | 仅双重上市公司，当前分位 |
| 配股/供股风险 | 🟢/🟡/🔴 | 近3年历史，可换股债券情况 |

> 任何一项为 🔴 须在「D. 核心雷点」中同步列出，并说明是否构成一票否决。

### G. 政策顺逆风评估

| 会议 | 生效截止 | 匹配信号 | 得分 |
|---|---|---|---|
| [会议名] | YYYY-MM-DD | 利好：xxx；无利空匹配 | +N |

**政策净得分（PS）**：`+N`

**港股特殊注记**：
- 公司类型：H 股（内地政策全量适用）/ 纯港资（仅香港本地政策）
- 人民币汇率影响：HKD 折算因子 ±N%
- 加权影响：[升一档 / 无调整 / 降一档]

### H. 周期位置判断（周期股必做，非周期股标注「不适用」）

同 A 股版本格式，数据来源改为 yfinance + stockanalysis.com。

### I. 价格走势与买入时机

必须包含：
- 近期走势概述（近 30/60 日涨跌幅、当前价在区间中的位置），货币单位 **HKD**
- 近期重大事件对股价的影响
- 南向资金近期净流入趋势（如可查）
- 政策加成调整说明
- **最终价格区间表**（HKD 计价，含所有调整后最终数值）
- 明确的时机判断

### J. 当前结论

| 口径 | 判定条件 |
|---|---|
| 适合继续研究，不适合立刻买 | 有明确逻辑，但至少 2 个关键问题未核实 |
| 可以试错，但只能小仓位 | 无硬红旗、已有 1-2 个可验证催化剂，但仍有重要不确定性 |
| 逻辑清晰，等待更合适价格或验证点 | 基本面较清晰，但赔率不够或验证点未到 |
| 逻辑清晰，当前价格合理，可按计划买入 | 无硬红旗、基本面清晰、估值合理、价格处于绿灯区间 |
| 核心疑点未解，不建议买入 | 存在审计、VIE/WVR、制裁、做空等一票否决型红旗 |

---

## Watchlist 港股特有字段

在标准 watchlist 字段基础上，港股条目须额外填写：

```json
{
  "ticker": "1299.HK",
  "hk_code": "1299",
  "market": "HK",
  "company_type": "港资",
  "vie_structure": false,
  "wvr_structure": false,
  "us_sanction_risk": false,
  "dual_listing": "HK only",
  "hk_connect": true,
  "price_currency": "HKD",
  "next_earnings_date": "2026-08-31",
  "next_earnings_type": "中期业绩"
}
```

> ⚠️ **季报公司示例**（不要用「中期业绩」，用 `"季度业绩（Q1）"`）：
> ```json
> {
>   "ticker": "0700.HK",
>   "next_earnings_date": "2026-05-13",
>   "next_earnings_type": "季度业绩（Q1）"
> }
> ```
>
> **季报公司 `next_earnings_type` 枚举值**：`季度业绩（Q1）` / `季度业绩（Q2/中期）` / `季度业绩（Q3）` / `年度业绩`

`dual_listing` 取值：`"A+H"` / `"HK only"` / `"HK+US ADR"`

---

## 首次买港股特别规则

如果用户是第一次买港股，执行以下硬约束：
- 默认不给「立即买入」口径
- 必须要求用户写出：一句买入逻辑、3 条反证条件、仓位上限、退出条件
- 特别强调港股流动性风险（中小市值）和做空机构风险

## 额外要求

- 默认使用简体中文输出
- 价格单位默认 **港元（HKD）**，若公司 RMB 计价须注明换算
- 每个核心结论必须附来源（文件名 / 平台名 + 日期），无法核实的标注「待核实」
- 分析结束后更新 `00-首页/公司索引.md` 港股区块
