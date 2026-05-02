---
name: stock-prebuy-review
description: >-
  在用户准备买入某只上市公司股票前使用，用于做买入前基本面尽调、红旗排查和买入逻辑验证。
  适用场景：个股研究、买入前排雷、基本面核查、财报质量审视、现金流质量、商业模式分析、
  治理与股东行为、监管司法风险、估值合理性判断（含历史百分位、PEG、隐含增速）、
  价格走势与买入时机分析（近60日走势、量价异动、分档价格区间建议）、买入逻辑验证、红旗识别、
  A股特有风险（限售解禁、大股东减持、股权质押、政策突变、再融资摊薄、商誉、实控人）。
  适用市场：A股、港股中资公司。
  不适用于：纯短线技术分析、K线形态、盘口解读、日内交易、单纯预测明日涨跌。
---

# 买股前审视个股

## 概览

这个技能把「准备买入一只股票」拆成一套最小但完整的研究流程，避免只看题材、K 线、估值或他人观点就下单。

默认目标不是直接给出「买/不买」，而是先回答 3 个问题：
- 这家公司到底靠什么赚钱
- 现在的市场定价到底在买什么预期
- 哪些变量一旦出错，会把这笔投资变成踩雷

## 核心原则

1. 先定义买入逻辑，再查数据。不要先看 PE 或股价。
2. 先用法定披露源，再用媒体和卖方材料补充。
3. 不把「布局了」当成「量产了」，不把「量产了」当成「赚钱了」。
4. 不只找支持结论的证据，必须同步写出反证条件。
5. 第一次买个股时，宁可错过，也不要带着未解核心疑点下单。

## 事实/推断/未知 三分法

输出时严格区分：
- **事实**：来自披露文件或权威来源，必须标注来源和日期
- **推断**：基于事实做出的分析判断，标明推理依据
- **未知**：当前未查到或无法核实，标注「待核实」并下调结论置信度

如果无法取得法定披露文件或权威来源，不要猜测，把该项标记为「未核实 / 待补证据」。

## 市场适配

先判断标的所属市场，决定数据源：
- **A 股** → 巨潮资讯网 / 上交所 / 深交所 / 证监会
- **港股** → 披露易 HKEXnews / 港交所

详见 [references/source-map.md](references/source-map.md)。

## 默认工作流

### 第 0 步：确认标的信息

先确认：
- 股票代码 / 公司全称 / 交易市场（A 股 / 港股）
- 计划持有周期（几天 / 几周 / 几个月 / 几年）
- 想做完整研究，还是快速排雷

如果同名公司存在 A/H 双重上市，先确认交易标的。

### 第 1 步：先让用户说清楚为什么想买

先收敛成一句话：
- 用户买的是赛道、公司、估值修复，还是事件催化
- 用户最担心的是回撤、业绩爆雷，还是错过上涨

如果用户自己说不清，帮用户压缩成一句话模板：
> 我想买它，因为我认为 `___` 会在 `___` 时间内推动 `___`

没有这句话，不进入后续研究。

### 第 2 步：固定查 14 个模块

#### 模块 1：公司到底赚什么钱

必查：
- 年报/半年报里的主营业务和收入构成
- 分产品、分行业、分地区收入
- 官网产品页和解决方案页

要回答：
- 热门业务在总收入中的占比有多大
- 这家公司到底是纯标的，还是平台型公司

红旗：
- 热门业务讲得很大，但收入占比极小
- 业务分类太粗，故意模糊利润来源

#### 模块 2：行业位置与壁垒

必查：
- 主要客户、认证、量产、份额
- 行业中的角色：设备商、零部件商、平台商、运营商

要回答：
- 它是行业龙头、跟随者，还是单一客户附庸
- 护城河来自技术、客户认证、成本、规模，还是仅靠景气

红旗：
- 只说布局，不说量产和客户
- 只说未来空间，不说当前竞争位置

#### 模块 3：增长质量

必查：
- 营收、归母净利、扣非净利
- 毛利率、净利率、ROE、研发投入
- 至少看 3 年趋势

要回答：
- 增长是主营拉动，还是一次性项目拉动
- 扣非是否跟得上

红旗：
- 净利润增长明显快于扣非
- 利润依赖补贴、投资收益、公允价值变动

#### 模块 4：现金流与营运资金

必查：
- 经营现金流净额
- 应收账款、存货、合同负债
- 应付账款、短期借款

要回答：
- 账面利润是否真的变成了现金
- 公司是否靠加杠杆或拖账期撑增长

红旗：
- 利润向上但经营现金流持续变差
- 应收和存货同时大涨
- 短债快速放大

#### 模块 5：资本结构与再融资风险

必查：
- 有息负债结构（短债/长债占比）
- 利息保障倍数或财务费用趋势
- 定增、可转债、配股、频繁融资历史
- 股权质押比例

要回答：
- 扩张靠内生现金流，还是靠外部融资
- 短期偿债压力是否在放大

数据来源（质押）：**理杏仁 `/company/pledge`**，返回出质人、质押数量、占总股本比例，筛选未解除质押 `[p for p in pledges if not p.get("pledgeDischargeDate")]`

红旗：
- 经营现金流弱但持续靠融资扩张
- 短债高、滚续压力大
- 大股东高比例质押（`accumulatedPledgePercentageOfTotalEquity` > 50%）
- 融资频繁但股东回报差


#### 模块 6：资产质量

必查：
- 审计意见
- 关键审计事项
- 存货跌价、应收减值、商誉、固定资产减值
- 财务附注

优先规则：审计报告里写什么，就优先查什么。

红旗：
- 非标准审计意见（**一票否决**）
- 关键审计事项长期围绕收入确认和资产减值
- 大额「洗澡式」减值

#### 模块 7：治理与股东回报

必查：
- 实控人、董事长、董秘
- 分红、回购、增减持、股权激励
- 关联交易、对外担保

要回答：
- 管理层是否长期站在中小股东同一边
- 有没有明显的资本运作痕迹重于经营

数据来源：
- **理杏仁 `/company/senior-executive-shares-change`**（高管增减持）、**`/major-shareholders-shares-change`**（大股东增减持）
- **理杏仁 `/company/dividend`**（分红历史，含分红比例 `annualNetProfitDividendRatio`）

```python
import requests, os
from dotenv import load_dotenv
load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

# 近3年分红历史
resp = requests.post("https://open.lixinger.com/api/cn/company/dividend", json={
    "stockCode": "600036",
    "startDate": "2022-01-01",
    "endDate": "2026-05-01",
    "token": LX_TOKEN
})
dividends = resp.json().get("data", [])
# 关键字段：date, dividend（每股股息，单位分）, dividendAmount（总派现），
#            annualNetProfitDividendRatio（分红/净利润，判断分红慷慨度）
```

红旗：
- 高管频繁减持
- 分红弱但融资重（`annualNetProfitDividendRatio` < 20% 且频繁增发）
- 关联交易复杂且解释不清


#### 模块 8：监管与司法风险

必查：
- 问询函、关注函、监管函
- 行政处罚、市场禁入
- 失信被执行、股权冻结、工商异常

数据来源：**理杏仁 `/company/measures`（监管措施，含处罚/工作函/整改通知）、`/company/inquiry`（问询函，含原文PDF链接）**；司法风险（失信被执行、股权冻结）仍需查国家企业信用信息公示系统。

```python
import requests, os
from dotenv import load_dotenv
load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

# 监管措施（近5年）
resp = requests.post("https://open.lixinger.com/api/cn/company/measures", json={
    "stockCode": "600866",
    "startDate": "2021-01-01",
    "endDate": "2026-05-01",
    "token": LX_TOKEN
})
measures = resp.json().get("data", [])
# 关键字段：date, displayTypeText（措施类型）, linkText（标题），referent（对象：上市公司/董事/高管）

# 问询函（近5年）
resp2 = requests.post("https://open.lixinger.com/api/cn/company/inquiry", json={
    "stockCode": "600866",
    "startDate": "2021-01-01",
    "endDate": "2026-05-01",
    "token": LX_TOKEN
})
inquiries = resp2.json().get("data", [])
# 关键字段：date, displayTypeText（函件类型）, linkText（标题），linkUrl（原文PDF）
# 高频红旗议题：持续经营/关联交易/商誉/收入确认/重大资产重组
```
- 财务造假、信披违规、内幕交易（**一票否决**）
- 核心股东或重要子公司失信、冻结、重大诉讼


#### 模块 9：估值与买入赔率

必查：
- PE_TTM、PB、PS_TTM
- PEG（PE / 未来 2-3 年预期净利润增速）
- 历史估值区间（至少看 3 年 PE 分位）
- 当前估值对应的盈利假设（隐含增速）
- 远期 PE（基于最新季度年化 EPS 或一致预期 EPS）
- 分析师一致预期（如可获取）

要回答：
- 当前 PE 在历史区间中处于什么分位（低/中/高）
- 当前估值隐含了多高的增速预期，这个增速是否现实
- 低估值是错杀，还是低增速折价
- 高估值是在买确定性，还是在买叙事泡沫
- 远期 PE（基于下一财年预期）是否合理

数据来源：**理杏仁基本面接口**，按公司类型选择：

```python
import requests, os
from dotenv import load_dotenv
load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

# ① 判断公司类型，选择对应接口
# 银行 → /fundamental/bank（用 pb 分位）
# 证券/保险 → /fundamental/security 或 /insurance（用 pe_ttm 分位）
# 其他 → /fundamental/non_financial（用 pe_ttm 分位；PE<0亏损改用 pb 分位）

COMPANY_TYPE_ENDPOINT = {
    "bank":          "https://open.lixinger.com/api/cn/company/fundamental/bank",
    "security":      "https://open.lixinger.com/api/cn/company/fundamental/security",
    "insurance":     "https://open.lixinger.com/api/cn/company/fundamental/insurance",
    "non_financial": "https://open.lixinger.com/api/cn/company/fundamental/non_financial",
}

def get_valuation_percentile(stock_code, endpoint, use_pb=False):
    """返回当前估值和3年历史分位，用于 price_bands 计算。"""
    if use_pb:
        metrics = ["pb", "pb.y3.cvpos", "pb.y3.q2v", "pb.y3.q5v", "pb.y3.q8v"]
    else:
        metrics = ["pe_ttm", "pe_ttm.y3.cvpos", "pe_ttm.y3.q2v", "pe_ttm.y3.q5v", "pe_ttm.y3.q8v",
                   "pb", "pb.y3.cvpos"]  # 同时拉 PB 备用（PE<0 时切换）

    today = __import__('datetime').date.today().isoformat()  # 动态日期，不硬编码
    resp = requests.post(endpoint, json={
        # ⚠️ fundamental 接口必须用 stockCodes（数组），用 stockCode（字符串）返回 code=0 空数据
        "stockCodes": [stock_code],   # 纯数字代码数组，如 ["600036"]，不带后缀
        "startDate": today,
        "endDate":   today,
        "metricsList": metrics,
        "token": LX_TOKEN
    })
    data = resp.json().get("data", [])
    return data[0] if data else {}

# 示例：招商银行（银行，用 PB 分位）
d = get_valuation_percentile("600036", COMPANY_TYPE_ENDPOINT["bank"], use_pb=True)
# d["pb"] = 当前PB；d["pb.y3.cvpos"] = 3年PB分位（0~1）
# d["pb.y3.q2v"]=P20, d["pb.y3.q5v"]=P50, d["pb.y3.q8v"]=P80

# 示例：东方财富（非金融，用 PE 分位）
d = get_valuation_percentile("300059", COMPANY_TYPE_ENDPOINT["non_financial"])
# d["pe_ttm"] = 当前PE；d["pe_ttm.y3.cvpos"] = 3年PE分位（0~1）
```

> 分位解读：< 20% → 历史低位（便宜） / 20-50% → 中低 / 50-80% → 中高 / > 80% → 历史高位（贵）
> 若 `pe_ttm` ≤ 0 或 NaN（亏损），切换为 PB 分位，在分析中注明「当期亏损，改用PB分位」

红旗：
- 只拿横向 PE 比，不看业务纯度和增长质量
- 把「便宜」当成买入理由本身
- PE 处于历史 80% 分位以上且增速放缓
- 市值/市梦率与当前收入利润严重脱节

#### 模块 10：催化剂与验证时间线

必查：
- 下次财报披露时间
- 关键订单 / 新产能 / 监管审批节点
- 诉讼 / 处罚进展
- 解禁 / 减持窗口

要回答：
- 未来 2 个季度最关键的验证指标是什么
- 如果哪个指标不达标，逻辑就要修正

#### 模块 11：价格走势与买入时机

> 🔴 **执行顺序：此模块必须在模块 12（A股风险）、13（政策评估）、14（周期位置）全部完成之后执行。**
> 价格区间的最终调整依赖 PS 分数（模块13）和周期位置（模块14），若提前执行将导致 PS 加成和周期调整无法纳入，最终表格数值与后续章节不一致。

必查：
- 近 60 个交易日行情数据（开盘、最高、最低、收盘、成交量、涨跌幅）
- 近 5-10 日估值指标（PE_TTM、PB、总市值、换手率）
- 近期关键事件对应的价格反应（如财报发布日、利好公告日）

要回答：
- 近 30/60 日涨跌幅，当前价位处于近期什么位置（高位 / 中位 / 低位）
- 近期是否有急涨或急跌，涨跌是否已消化已知利好/利空
- 成交量和换手率是否异常放大（可能意味着筹码快速换手、获利盘堆积）
- 短期是否存在追高风险或恐慌抛售后的错杀机会
- 给出分档价格区间建议（红灯区 / 黄灯区 / 绿灯区），每档注明对应的大致 PE

分析框架：

1. **位置判断**：当前价 vs 近 60 日最高/最低，判断处于区间的什么位置
2. **动量判断**：近 5/10/20 日涨跌幅，判断短期趋势强度
3. **量价配合**：放量上涨还是缩量上涨，放量下跌还是缩量下跌
4. **事件消化**：最近一次重大利好（如财报）发布后的涨幅，判断利好是否已被定价
5. **价格区间建议**：基于估值合理性，划分出风险区间

价格区间输出格式：

| 价格区间 | 对应 PE 约 | 风险评估 |
|----------|-----------|----------|
| X 元以上 | xxP+ | 🔴 追高区，已反映近期利好 |
| X-Y 元 | xxP-yyP | 🟡 中性区，可关注但需等确认 |
| Y-Z 元 | yyP-zzP | 🟢 较好入场区间 |
| Z 元以下 | <zzP | 🟢🟢 安全边际充足 |

**理杏仁 price_bands 标准计算方法：**

price_bands 必须基于历史估值分位，不得直接对当前价格做±N%估算。格式：`[红线, 中性底, 最优区起点]`（数字，非文字）。

```python
import requests, os
from dotenv import load_dotenv
load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")

def calc_price_bands(stock_code, current_price, company_type="non_financial"):
    """
    用理杏仁 PE/PB 3年历史分位计算 price_bands。
    返回 [红线(P80价格), 中性底(P50价格), 最优区(P20价格)]
    
    company_type: "non_financial" / "bank" / "security" / "insurance"
    银行/保险用 PB 分位 × BPS；其他用 PE 分位 × ratio
    """
    endpoint_map = {
        "non_financial": "https://open.lixinger.com/api/cn/company/fundamental/non_financial",
        "bank":          "https://open.lixinger.com/api/cn/company/fundamental/bank",
        "security":      "https://open.lixinger.com/api/cn/company/fundamental/security",
        "insurance":     "https://open.lixinger.com/api/cn/company/fundamental/insurance",
    }
    use_pb = company_type in ("bank", "insurance")
    metrics = (
        ["pb", "pb.y3.q2v", "pb.y3.q5v", "pb.y3.q8v"] if use_pb else
        ["pe_ttm", "pe_ttm.y3.q2v", "pe_ttm.y3.q5v", "pe_ttm.y3.q8v",
         "pb", "pb.y3.q2v", "pb.y3.q5v", "pb.y3.q8v"]  # 备用：PE<0时切PB
    )
    today = __import__('datetime').date.today().isoformat()  # 动态日期
    resp = requests.post(endpoint_map[company_type], json={
        # ⚠️ fundamental 接口必须用 stockCodes（数组），用 stockCode（字符串）返回 code=0 空数据
        "stockCodes": [stock_code],   # 纯数字代码数组，如 ["600036"]
        "startDate": today,
        "endDate":   today,
        "metricsList": metrics,
        "token": LX_TOKEN
    })
    d = resp.json().get("data", [{}])[0]

    if use_pb:
        pb = d.get("pb")
        if not pb: return None
        bps = current_price / pb          # 每股净资产
        q2v, q5v, q8v = d["pb.y3.q2v"], d["pb.y3.q5v"], d["pb.y3.q8v"]
        return [round(q8v * bps, 2), round(q5v * bps, 2), round(q2v * bps, 2)]
    else:
        pe = d.get("pe_ttm")
        if not pe or pe <= 0:            # 亏损：切换 PB
            pb = d.get("pb")
            if not pb: return None
            bps = current_price / pb
            q2v, q5v, q8v = d["pb.y3.q2v"], d["pb.y3.q5v"], d["pb.y3.q8v"]
            return [round(q8v * bps, 2), round(q5v * bps, 2), round(q2v * bps, 2)]
        ratio = current_price / pe        # 每1倍PE对应的价格（≈ EPS）
        q2v, q5v, q8v = d["pe_ttm.y3.q2v"], d["pe_ttm.y3.q5v"], d["pe_ttm.y3.q8v"]
        return [round(q8v * ratio, 2), round(q5v * ratio, 2), round(q2v * ratio, 2)]

# 使用示例：
# bands = calc_price_bands("300059", 20.26, "non_financial")
# → [31.06, 24.16, 21.00]  # [红线, 中性底, 最优区起点]
# 灯号判断：当前价 > bands[0] → 🔴；bands[1]~bands[0] → 🟡；bands[2]~bands[1] → 🟢；< bands[2] → 🟢🟢
```

红旗：
- 短期（3-4 周内）涨幅超过 30% 后仍想追入
- 利好公告后连续大涨，利好出尽风险高
- 换手率持续 >5%，筹码不稳定
- 处于解禁高峰期前 1-2 个月

注意：本模块不做技术分析预测（不画 K 线形态、不判断支撑阻力位的精确点位），只做基于估值和近期走势的买入时机风险评估。

---

#### 模块 12：A股特有风险因子（A股/港股必做）

A股市场存在若干在境外成熟市场不常见、但在国内股票投资中必须单独检查的风险点。这些风险往往在短中期内对股价产生直接、可量化的冲击，不能归并到其他模块处理。

---

**12.1 限售股解禁压力**

必查：
- 最近/未来3个月的解禁批次（规模、解禁方类型：IPO股 / 定增股 / 员工持股）
- 解禁市值 ÷ 近60日日均成交额（"卖压天数"，衡量市场能否消化供给）
- 解禁方的成本区间（成本远低于当前价 → 减持动机强）

数据来源：**理杏仁 `/company/hot/elr`（限售解禁热度，快速判断近期解禁压力强度）**；完整解禁日历补充查巨潮资讯 / 东方财富。

```python
# 理杏仁：限售解禁热度（判断近期解禁压力是否处于高位）
import requests, os
from dotenv import load_dotenv
load_dotenv()

resp = requests.post("https://open.lixinger.com/api/cn/company/hot/elr", json={
    "stockCode": "300750",       # 纯数字代码，不带后缀
    "date": "2026-04-30",
    "token": os.getenv("LIXINGER_TOKEN")
})
data = resp.json().get("data", [])
# data[0]["v"] 为综合热度得分，高热度 = 近期有解禁批次且规模大
```

红旗：
- 🔴 3个月内解禁量 > 当前流通盘 15%，或解禁市值 > 60日均成交额 30倍
- 🔴 解禁方为PE/VC等纯财务投资者，锁定期到期即面临退出压力
- 🟡 解禁量 5–15%，或解禁方为产业资本但持仓成本明显低于当前价

---

**12.2 大股东 / 管理层减持**

必查：
- 近6个月控股股东、实控人、5%以上大股东减持公告及减持计划
- 董监高减持动态（尤其集中性减持、任期届满前密集减持）
- 减持方式（竞价 / 大宗 / 协议）及折价幅度

数据来源：**理杏仁 `/company/major-shareholders-shares-change`（大股东）、`/company/senior-executive-shares-change`（高管）**，直接返回减持方、减持股数、均价、变更后持股比例，无需人工查公告。

```python
import requests, os
from dotenv import load_dotenv
load_dotenv()

# 大股东增减持（近6个月）
resp = requests.post("https://open.lixinger.com/api/cn/company/major-shareholders-shares-change", json={
    "stockCode": "300750",
    "startDate": "2025-11-01",
    "endDate": "2026-05-01",
    "token": os.getenv("LIXINGER_TOKEN")
})
major = resp.json().get("data", [])
# 关键字段：shareholderName, changeQuantity(<0=减持), sharesChangeRatio, avgPrice, sharesHeldAfterChange

# 高管增减持
resp2 = requests.post("https://open.lixinger.com/api/cn/company/senior-executive-shares-change", json={
    "stockCode": "300750",
    "startDate": "2025-11-01",
    "endDate": "2026-05-01",
    "token": os.getenv("LIXINGER_TOKEN")
})
exec_changes = resp2.json().get("data", [])
# 关键字段：executiveName, duty, changedShares(<0=减持), avgPrice, changeReason
```

红旗：
- 🔴 控股股东/实控人宣布6个月内减持 ≥1%（需提前15交易日公告）
- 🔴 近3个月多名董监高同向减持，且减持金额显著大于薪酬/激励总额
- 🟡 大宗减持折价 >5%（需有机构折价接盘才能消化，说明流通性压力较大）

---

**12.3 股权质押风险**

必查：
- 控股股东/实控人质押股数 ÷ 其持股总数（质押比例）
- 质押融资金额、到期时间、资金用途
- 估算预警线（通常为质押时股价×80%）和平仓线（×70%），与当前股价对比

数据来源：**理杏仁 `/company/pledge`（结构化质押明细）**，直接返回出质人、质权人、质押数量、占总股比例、质押起止日，无需查交易所公告。

```python
import requests, os
from dotenv import load_dotenv
load_dotenv()

resp = requests.post("https://open.lixinger.com/api/cn/company/pledge", json={
    "stockCode": "300750",
    "startDate": "2024-01-01",   # 查近2年活跃质押
    "token": os.getenv("LIXINGER_TOKEN")
})
pledges = resp.json().get("data", [])
# 关键字段：pledgor, pledgee, pledgeAmount, pledgePercentageOfTotalEquity,
#            accumulatedPledgePercentageOfTotalEquity（累计占总股比），
#            pledgeDischargeDate（已解除则有值），pledgeEndDate
# 筛选未解除质押：[p for p in pledges if not p.get("pledgeDischargeDate")]
```

红旗：
- 🔴 控股股东质押比例 >70%（强平风险随股价下行急剧上升）
- 🔴 当前股价已接近预估预警线，且近期基本面有下行压力
- 🟡 质押比例 50–70%，但质押资金用途为偿还非经营性债务（地产、P2P等）

---

**12.4 监管政策突变风险**

必查：
- 主管部门近1年出台的行业政策（发改委、工信部、银保监等）
- 行业是否处于政策强监管周期（互联网、教育、游戏版号、医疗耗材集采是历史案例）
- 核心业务依赖政策补贴或政府指令性采购的比例
- 是否被列入国产替代、自主可控、新质生产力等政策顺风赛道

红旗：
- 🔴 行业处于首轮强监管期（方向未明，估值底部难测）
- 🔴 收到主管部门警示函或整改通知（6个月内）
- 🟡 核心收入中政策驱动部分 >30%，且补贴政策有到期风险

---

**12.5 再融资 / 股权摊薄风险**

必查：
- 已公告的定向增发、配股、可转债方案（规模、定价基准、进度）
- 滚动3年融资总额 ÷ 同期累计净利润（融资依赖度）
- 定增底价 vs 当前股价的空间（底价倒挂 → 方案可能终止或修改）
- 可转债转股价 vs 当前价（转股压力区间）

红旗：
- 🔴 滚动3年融资总额 >3倍同期净利润（外部输血型，持续稀释）
- 🔴 定增方案正在推进但底价高于当前股价（方案不确定性压制股价）
- 🟡 历史上"分红少融资多"（3年分红总额 < 最近一次融资额）

---

**12.6 商誉减值风险**

必查：
- 商誉余额 ÷ 净资产（商誉占比）
- 主要商誉来源的被收购标的近1–2年业绩承诺完成情况
- 并购是否处于减值测试高风险区间（并购后3–5年，景气下行期）

数据来源：资产负债表"商誉"科目、年报"商誉明细"附注

红旗：
- 🔴 商誉/净资产 >50%（高风险型），且并购标的所在行业景气下行
- 🔴 并购标的已连续2年未完成业绩承诺，或业绩补偿方案存争议
- 🟡 商誉/净资产 30–50%，原管理层离职（承诺人出走 → 业绩承诺履行风险上升）

---

**12.7 实控人 / 大股东行为风险**

必查：
- 实控人近1年是否有司法/行政调查相关公告（工商异常、失信被执行人名单）
- 是否存在同业竞争（实控人另有同类业务主体）
- 历史上有无大股东资金占用（"其他应收款-关联方"异常）
- 国企背景：分红政策是否受考核任务或政治任务主导（非利润最大化目标）

数据来源：企查查/天眼查（穿透实控人）、法院被执行公告、交易所临时公告

红旗：
- 🔴 实控人被刑事立案调查（一票否决级）
- 🔴 大股东资金占用有历史记录，或"其他应收款-关联方"金额异常增大
- 🟡 同业竞争长期存在且无明确解决方案，国企分红严重受制于政策任务

---

**12.8 信息披露质量风险**

必查：
- 近2年是否收到交易所问询函/关注函（巨潮"问询函"专栏）
- 问询函涉及议题（持续经营、关联交易、商誉、收入确认是高频红旗议题）
- 问询函回复是否实质性（泛泛而谈、回避具体数据 → 质量差）
- 审计师是否更换，是否出现非标意见（保留意见/无法表示意见）

红旗：
- 🔴 连续2年被问询同一议题但无实质改善
- 🔴 审计师更换为规模明显下降的小所，或出现非标意见
- 🟡 单次问询函回复内容高度模糊，未直接回答监管问题

---

#### 模块 13：政策顺逆风评估（政治会议加权）

**目的**：将当前生效的政治会议信号纳入估值锚和结论口径，避免在政策明确利好/利空时用纯基本面视角得出反向结论。

---

**13.1 读取生效中的会议页**

读取 vault 目录 `06-政治会议/` 下所有 `.md` 文件，筛选 frontmatter 中 `生效截止` ≥ 今天的页面作为**有效政策集**。

```python
# 示例：列出所有生效中会议页
import os, re
from datetime import date

vault_dir = r"E:\ObsidianVaults\ZephyrSpace\06-政治会议"
today = date.today().isoformat()  # e.g., '2026-04-28'
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

---

**13.2 对照利好/利空信号**

对每个有效会议页，提取其「利好行业/板块」和「利空行业/板块」以及「利好/利空企业特征」四张表，与被分析公司做对照：

| 对照维度 | 做法 |
|---|---|
| 行业匹配 | 判断公司主营业务/所属行业是否出现在会议「利好行业」或「利空行业」中 |
| 企业特征匹配 | 判断公司特征（国央企/自主可控/重资产/出口依赖等）是否与「利好特征」或「利空特征」吻合 |
| 优先级加权 | 利好行业的 ⭐ 数即为分值（⭐=+1 / ⭐⭐=+2 / ⭐⭐⭐=+3）；利空行业固定 -2 |

汇总得到**政策净得分**（Policy Score，简称 PS）：

```
PS = Σ 利好得分 - Σ 利空得分
```

若同一公司在不同会议页中重复出现（如同时受十五五和季度政治局会议利好），分值**叠加**。

---

**13.3 政策加权对结论的影响**

PS 影响三个输出维度：

**① PreBuy 结论口径（可升降一档）**

| PS 值 | 调整方向 |
|---|---|
| PS ≥ +4 | 结论口径可升一档（但不能跨过「无硬红旗」的前提） |
| PS +1 ~ +3 | 在结论中注明「政策顺风，赔率改善」，价格区间绿灯区上界+10% |
| PS 0 | 无调整 |
| PS -1 ~ -2 | 在结论中注明「政策逆风，需等行业政策明朗」，价格区间绿灯区收窄 10% |
| PS ≤ -3 | 结论口径降一档，并在核心雷点中添加「政策逆风」红旗 |

**② 价格区间（调整绿灯/黄灯区间边界）**

- PS ≥ +4：绿灯区上界整体上移 15%（政策催化剂尚未完全定价时）
- PS +1 ~ +3：绿灯区上界上移 10%
- PS -1 ~ -2：绿灯区上界下移 10%（政策风险折价）
- PS ≤ -3：绿灯区上界下移 15%，并标注「需等政策明朗再入场」

**③ Watchlist 档位建议**

| 情形 | 建议 |
|---|---|
| PS ≥ +3 且基本面达 growth 标准 | 可考虑从 radar 升至 growth |
| PS ≥ +3 且基本面达 core 标准 | 政策加分可作为升 core 的辅助条件之一（不能替代护城河判断） |
| PS ≤ -3 | 不升档；若已在 growth，注明「政策逆风，建议观察不加仓」 |

> ⚠️ **政策加权不能覆盖基本面硬红旗**。出现一票否决型红旗时，无论 PS 多高，结论必须维持「不建议买入」。

---

#### 模块 14：周期位置判断（周期股专属，非周期股跳过）

**目的**：周期股用 PE 判断估值天然失真（景气顶部 PE 最低，底部 PE 最高或亏损），必须先识别周期属性、再定位周期阶段，才能正确锚定买卖区间。

---

**14.1 判断是否为周期股**

满足以下任意一条，进入周期分析：

| 判定维度 | 周期股信号 |
|---|---|
| 行业归属 | 化工、有色金属、钢铁、煤炭、航运、造纸、化纤/涤纶、猪肉/农业、玻璃/水泥、半导体存储（DRAM/NAND）、航空 |
| 盈利波动 | 近 10 年 ROE 标准差 > 5%（利润周期性明显） |
| 主要驱动 | 产品价格（大宗商品/化工品/纺织原料价格）主导利润，而非定价权 |
| 资本开支周期 | 行业供需由大规模扩/去产能驱动，周期约 3-7 年 |

> 如果是**成长型公司兼具周期特征**（如高端制造，成长弹性>周期弹性），标注「弱周期属性」，仍执行本模块但结论权重减半。

---

**14.2 确定周期类型**

| 类型 | 典型行业 | 主要驱动变量 |
|---|---|---|
| 商品价格周期 | 化工、化纤、有色、煤炭、钢铁 | 大宗/化工品现货价格、库存水平 |
| 资本开支周期 | 半导体设备、工程机械、航运 | 行业 Capex 规模、供需缺口 |
| 农业/养殖周期 | 生猪、水产、禽类 | 存栏量、饲料成本、产品价格 |
| 利率/信用周期 | 银行、地产、保险 | 利率、信用扩张、资产质量 |

---

**14.3 评估当前周期位置（五步法）**

依次查以下 5 个维度，每个维度给出信号方向（↑上行/→企稳/↓下行）：

**① PB 历史分位**（最重要指标）

```python
import requests, os
from dotenv import load_dotenv
load_dotenv()

# 优先用理杏仁基本面接口（非金融）获取PB历史分位
# ⚠️ fundamental 接口必须用 stockCodes（数组），用 stockCode（字符串）返回 code=0 空数据
today = __import__('datetime').date.today().isoformat()
resp = requests.post("https://open.lixinger.com/api/cn/company/fundamental/non_financial", json={
    "stockCodes": ["000002"],        # 纯数字代码数组，不带后缀
    "startDate": today,
    "endDate": today,
    "metricsList": ["pb", "pb.y3.cvpos", "pb.y3.q2v", "pb.y3.q5v", "pb.y3.q8v"],
    "token": os.getenv("LIXINGER_TOKEN")
})
d = resp.json()["data"][0]
# d["pb"] = 当前PB；d["pb.y3.cvpos"] = 3年历史分位（0~1）
# d["pb.y3.q2v"] = P20对应PB值，q5v=P50，q8v=P80
# 银行/保险：改用 /fundamental/bank 或 /fundamental/insurance
# 分位 < 20%：低位 / 20-50%：中低位 / 50-80%：中高位 / > 80%：高位
```

**② ROE 趋势**（利润周期的直接体现）

- 近 4 期 ROE 连续改善 → 复苏/扩张信号
- ROE 处于近 10 年高点附近 → 景气顶部信号
- ROE 近 2 期连续恶化 → 收缩信号
- ROE 处于近 10 年低点附近 → 接近底部信号

**③ 行业产品价格趋势**（查公开市场价格/行业协会数据/公司年报披露）

- 产品现货价格近 3 个月环比上涨 → 上行
- 价格企稳/小幅波动 → 企稳
- 产品价格创近 2 年新低 → 下行

**④ 在建工程 / Capex 趋势**（资本开支判断供给扩张期）

- 行业整体新增产能/在建工程持续增长 → 供给扩张，景气峰值已过或将到顶
- 行业 Capex 大幅收缩 → 供给出清，景气底部信号

**⑤ 库存周期**（若有公开数据）

- 主动去库存（量价齐跌）→ 衰退期
- 被动去库存（量跌价稳）→ 接近底部
- 主动补库存（量价齐升）→ 复苏/扩张期
- 被动补库存（量升价跌）→ 接近顶部

---

**14.4 综合判定周期位置**

汇总 5 个维度，判断当前所处阶段：

| 阶段 | 特征 | 操作含义 |
|---|---|---|
| **底部/复苏早期** | PB低分位，ROE触底回升，价格企稳，Capex收缩中 | ✅ 最佳买入窗口；用 PB 锚定而非 PE |
| **复苏中期** | PB中低位，ROE持续改善，价格上行，Capex尚未大扩 | ✅ 仍可买入，但要关注景气持续性验证点 |
| **景气高峰** | PB高分位，ROE历史高位，价格高位，Capex大扩 | ⚠️ 此时 PE 最低但是卖点；严格控制仓位 |
| **收缩/衰退期** | PB高位回落，ROE恶化，价格下行，产能过剩 | ❌ 避免，等待出清信号 |
| **出清期** | PB极低，ROE亏损/极低，弱势企业退出，Capex大幅收缩 | ⏳ 研究关注，等待反转信号 |

---

**14.5 周期位置对 PreBuy 结论和价格区间的影响**

| 周期位置 | 结论口径调整 | 价格区间调整 |
|---|---|---|
| 底部/复苏早期 | 可升一档（叠加 PS 后最多升两档） | 切换为 **PB分位定价**，PB < 1.0x 或历史 20% 分位以下作为绿灯区底 |
| 复苏中期 | 维持，标注「周期顺风」 | PB/PE 混合定价，不调整 |
| 景气高峰 | 强制降一档，标注「周期高位警告」 | 追高区下移 20%（即使 PE 低也不能简单判断便宜） |
| 收缩/衰退期 | 降一档，标注「周期逆风，不适合建仓」 | 追高区下移 30% |
| 出清期 | 维持「继续研究」，等确认反转 | 不设绿灯区，等待 PB 极值 + ROE 触底两个条件同时出现 |

> ⚠️ **景气顶部低PE陷阱**：周期股在盈利最高时 PE 最低，若此时因「便宜」买入，将在利润回落时承受双杀（估值+利润双下行）。**本模块的结论必须优先于模块9的PE估值结论。**

---

**14.6 写入 Watchlist（模块 14 完成后立即执行）**

确认为周期股后，在 `stock_watchlist.json` 对应条目写入以下两个字段：

```json
"cycle_is_cyclical": true,
"cycle_position": "景气高峰"   // 取值见 cycle_position_schema：底部/复苏早期/复苏中期/景气高峰/收缩期/出清期
```

规则：
- **非周期股**：省略这两个字段，不写 `false` 占位
- **弱周期（成长弹性 > 周期弹性）**：仍写 `cycle_is_cyclical: true`，并在 `notes` 补注「弱周期，结论权重减半」
- **每次 PreBuy 更新时同步刷新** `cycle_position`，不允许字段值过期停留
- 取值必须与 `cycle_position_schema` 中的 6 个枚举严格一致，不得自造其他表述

---

### 第 3 步：固定查这些资料

优先顺序：
1. 法定披露文件：年报、半年报、季报、临时公告
2. 审计报告与财务附注
3. 互动平台、业绩说明会、路演纪要
4. 监管处罚、问询函、司法与工商信用
5. 公司官网产品资料

**数据 API 优先顺序（估值/财务/监管）：**
> 理杏仁（Lixinger）为唯一主力数据源；理杏仁无数据时用东方财富 web_fetch 补充；不再使用 tushare。

| 数据类型 | 优先数据源 | 接口 |
|---|---|---|
| PE/PB历史分位 | 理杏仁 | `/fundamental/non_financial`（银行→`/bank`，证券→`/security`）|
| price_bands 计算 | 理杏仁 | 同上，用 `q2v/q5v/q8v` × ratio/BPS |
| 监管措施/问询函 | 理杏仁 | `/company/measures`、`/company/inquiry` |
| 大股东/高管增减持 | 理杏仁 | `/company/major-shareholders-shares-change`、`/senior-executive-shares-change` |
| 股权质押 | 理杏仁 | `/company/pledge` |
| 分红历史 | 理杏仁 | `/company/dividend` |
| 限售解禁（初筛） | 理杏仁热度 | `/company/hot/elr` |
| 财报营收/净利润（非金融）| 理杏仁 | `/company/fs/non_financial`（证券→`/fs/security`，保险→`/fs/insurance`）|
| 财报营收/净利润（银行）| 理杏仁 | `/company/fs/bank`（**注：fs/bank 无 ROE 字段**，见下方陷阱）|
| 银行 ROE（加权）| 东方财富 | `RPT_LICO_FN_CPD` 接口，字段 `WEIGHTAVG_ROE`（理杏仁 fs/bank 不支持）|
| 当前价格 / 近60日走势 | 理杏仁 | `/company/candlestick` |
| 前十大股东 | 理杏仁 | `/company/majority-shareholders` |
| 财报QDATE验证（备用）| 东方财富 web_fetch | `datacenter-web.eastmoney.com/api/...` |

> ⚠️ **理杏仁 API 关键陷阱（已实测验证）**
>
> | 接口类型 | 参数名 | ✅ 正确 | ❌ 错误 |
> |---|---|---|---|
> | `fundamental/bank`、`fundamental/non_financial` 等基本面接口 | 股票代码字段 | `"stockCodes": ["600036"]`（**数组**） | `"stockCode": "600036"`（字符串，返回 code=0 空数据）|
> | `dividend`、`pledge`、`measures`、`inquiry`、增减持、`hot/elr` 等非基本面接口 | 股票代码字段 | `"stockCode": "600036"`（**字符串**） | `"stockCodes": ["600036"]` |
> | `candlestick` K线接口 | 复权类型 | `"type": "lxr_fc_rights"` 必须传 | 不传 type → 返回 `ValidationError` |
> | `fs/bank`、`fundamental/bank` | ROE字段 | 不支持（会导致整个请求报错） | 不可在 `metricsList` 或字段列表中包含 `roe`、`roe.wa` 等字段；**银行ROE必须从东方财富 `WEIGHTAVG_ROE` 字段获取** |
>
> **一句话记法**：`fundamental/*` 系列用数组，其他接口用字符串；candlestick 必须加 type；银行ROE不在理杏仁。

**candlestick 接口示例（当前价格 + 近60日走势）：**

```python
import requests, os
from dotenv import load_dotenv
from datetime import date, timedelta
load_dotenv()

today = date.today().isoformat()
sixty_days_ago = (date.today() - timedelta(days=90)).isoformat()  # 多取几天确保60交易日

resp = requests.post("https://open.lixinger.com/api/cn/company/candlestick", json={
    "stockCode": "600036",          # 纯数字代码，字符串（非数组）
    "startDate": sixty_days_ago,
    "endDate":   today,
    "type": "lxr_fc_rights",        # ⚠️ 必须指定复权类型，否则返回 ValidationError
    "token": os.getenv("LIXINGER_TOKEN")
})
data = resp.json().get("data", [])

# ⚠️ candlestick 数据返回无序，必须先排序
data = sorted(data, key=lambda x: x["date"])

# ⚠️ 字段名是完整英文（非缩写）：close / open / high / low / volume
latest = data[-1]
current_price = latest["close"]
high_60 = max(d["high"] for d in data)
low_60  = min(d["low"]  for d in data)
print(f"当前价={current_price}, 近60日高={high_60}, 近60日低={low_60}")
```

官方资料入口和用途见 [references/source-map.md](references/source-map.md)。

> ⚠️ **财报数据获取（理杏仁 fs/* 接口）**
>
> 财报数据优先用理杏仁 `/company/fs/non_financial`（非金融）或 `/company/fs/bank`（银行），返回标准化财务数据。
> 理杏仁同样可能存在数据延迟，**当运行 PreBuy 的日期位于财报密集发布期间（一季报：4月，半年报：8月，三季报：10月，年报：3-4月），必须用东方财富 web_fetch 进行QDATE二次确认：**
>
> 1. **确认财报是否已发布**：用东方财富 API 查最新报告期
>    ```
>    URL: https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE%3D%22{6位代码}%22)&pageNumber=1&pageSize=3
>    确认字段：ISNEW="1"（最新一期）、QDATE（如"2026Q1"）、REPORTDATE（如"2026-03-31"）
>    ```
> 2. **若理杏仁数据期别落后于预期**，改用东方财富返回的以下字段作为财报来源：
>    - `TOTAL_OPERATE_INCOME`（营业总收入）
>    - `PARENT_NETPROFIT`（归母净利润）
>    - `YSTZ`（营收同比 %）
>    - `SJLTZ`（净利同比 %）
>    - `WEIGHTAVG_ROE`（加权 ROE）
>    - `XSMLL`（毛利率）
>    - `JYXJL`（经营现金流净额）
>
> 若两者数据不一致，**以东方财富为准**，并在结论中注明数据来源。

> 🔴 **财报QDATE强制验证（每次取财报数据后必做，不可跳过）**
>
> **问题根源**：理杏仁/东方财富 API 都可能静默返回上一期数据，不报错、不提示。若不验证期别，分析者会把 2025Q1 数据误标为"Q1 2026"，或把 2024Q3 数据误标为最新三季报，导致结论完全错误。这在批量 PreBuy 中尤其危险。
>
> **第一步：根据当天日期推算「应有的最新报告期」**
>
> A股披露截止日规则：Q1→4/30、半年报→8/31、三季报→10/31、年报→次年4/30。
>
> ```python
> from datetime import date
>
> def expected_latest_qdate(today=None):
>     """根据今天日期，返回应已发布的最新报告期 QDATE。"""
>     if today is None:
>         today = date.today()
>     y, m = today.year, today.month
>     if 4 <= m <= 7:
>         return f"{y}Q1"      # 一季报披露期（截止4/30）
>     elif 8 <= m <= 9:
>         return f"{y}Q2"      # 半年报披露期（截止8/31）
>     elif m >= 10:
>         return f"{y}Q3"      # 三季报披露期（截止10/31）
>     else:                    # 1-3月：年报尚未全部披露
>         return f"{y-1}Q3"   # 最新已确保发布的是去年三季报
> ```
>
> **第二步：验证 API 返回的 QDATE 不早于预期**
>
> ```python
> # QDATE 比较辅助：将 "2026Q3" 转为可比整数
> def qdate_to_int(qdate):
>     # "2026Q1"→20261, "2026Q2"→20262, "2026Q3"→20263, "2026Q4"→20264
>     year, q = qdate.split('Q')
>     return int(year) * 10 + int(q)
>
> expected = expected_latest_qdate()           # e.g., "2026Q1"
> actual   = row.get('QDATE')                  # e.g., "2025Q1" ← 危险！
>
> if qdate_to_int(actual) < qdate_to_int(expected):
>     # ❌ 数据期别落后于预期！该公司本期报告尚未发布（或 API 返回旧数据）
>     # 处理方式：
>     #   a) 在公司页标注："本期报告（{expected}）尚未披露，以 {actual} 数据作参考"
>     #   b) 不得将此数据的同比增速标注为 "{expected} 同比+X%"
>     #   c) PreBuy 结论口径需单独注明数据截至日期
>     print(f"⚠️ {ts_code}: 实际QDATE={actual}，预期≥{expected}，当期报告尚未发布")
> else:
>     # ✅ 期别匹配（或已发布更新一期），可正常使用
>     pass
> ```
>
> **错误示例**（已发生的真实事故）：
> - ❌ 4月运行，`QDATE="2025Q1"` 但写入分析时标注为"Q1 2026 营收同比+23.35%"（横店东磁等3家）
> - ✅ 正确写法：验证 `qdate_to_int(actual) >= qdate_to_int(expected)` 后才写入；否则注明"当期报告未披露，以 {actual} 数据作参考"
>
> **注意**：财报密集期内各公司陆续发布，截止日前仍有10-30%公司未发布。批量分析时**必须逐条验证**，不可假设所有公司已发布当期报告。

### 第 3.5 步：确认下一期财报日期（A股必做，结果写入公司页和 watchlist）

**目的**：随时知道这家公司下一次「成绩单」在什么时候发布，以便在财报窗口期前评估仓位风险，也方便跟踪买入逻辑是否得到验证。

**操作流程**：

1. **直接用法定截止日估算**（理杏仁无 disclosure_date 接口，tushare 不再使用）：

```python
from datetime import date

def get_next_earnings_estimate(today=None):
    """
    根据A股法定披露截止日规则，估算下一期财报日期和类型。
    返回 (date_str: str "YYYY-MM-DD", report_type: str)
    """
    if today is None:
        today = date.today()
    y, m = today.year, today.month
    if m < 4:
        return f"{y}-04-30", "一季报"      # 等待本年Q1
    elif m < 8:
        return f"{y}-08-31", "半年报"      # 等待本年H1
    elif m < 10:
        return f"{y}-10-31", "三季报"      # 等待本年Q3
    else:
        return f"{y+1}-04-30", "年报"      # 等待次年年报/一季报
        # 注：10-12月若年报已披露则下一期为次年一季报，用04-30通用

next_date, next_type = get_next_earnings_estimate()
# e.g., ("2026-08-31", "半年报")
```

> 📌 若需精确到实际预约披露日（而非法定截止日），可用东方财富财经日历 web_fetch 补充：
> `https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_PUBLIC_OP_NEWREPORT&filter=(SECURITY_CODE%3D%22{6位代码}%22)&pageNumber=1&pageSize=5`

2. 将结果（格式转为 YYYY-MM-DD）写入两个地方：

   a. **公司页 frontmatter**：

   ```yaml
   下一财报日: 2026-08-20
   下一财报类型: 半年报
   ```

   b. **watchlist JSON** 对应条目：

   ```json
   "next_earnings_date": "2026-08-20",
   "next_earnings_type": "半年报",
   "cycle_is_cyclical": true,        // 周期股必填；非周期股省略此字段
   "cycle_position": "景气高峰"       // 枚举值见 cycle_position_schema；每次 PreBuy 更新时同步刷新
   ```

3. 若估算日期与公司实际预约日有出入，用法定截止日标注「估算」：
   - 一季报：`YYYY-04-30`
   - 半年报：`YYYY-08-31`
   - 三季报：`YYYY-10-31`
   - 年报：`YYYY+1-04-30`

4. **每次财报发布后须更新**此字段为下下期日期，确保始终指向未来。

> ⚠️ 财报发布前 2 周是高风险窗口：不在此窗口新建仓（信息不对称风险高），已持仓者评估是否需要减仓或加止损。

### 第 3.6 步：计算 price_bands 并写入 watchlist（A股必做）

**目的**：每次完成 PreBuy 分析后，将基于历史分位计算（并含政策/周期调整）的 price_bands 写入 watchlist JSON，替代旧的手工拍估或与当前价强绑定的数值。

**计算方法**：调用上方模块11中的 `calc_price_bands()` 函数，再叠加模块13（政策PS）和模块14（周期）的调整。

**price_bands 写入规则**：
- `price_bands[0]`（追高线）= 基础 P80 对应价格，**若 PS ≥ +1，叠加 PS 加成**（+10% 对应 ×1.10，+15% 对应 ×1.15），写入最终调整后数值
- `price_bands[1]`（中性底）= 基础 P50 对应价格，不做 PS 调整
- `price_bands[2]`（最优区起点）= 基础 P20 对应价格，不做调整

> ⚠️ **price_bands 存最终值，不存原始 P80**。若 PS=+3 使追高线从 46.47 变为 47.4，watchlist 应写 47.4，便于外部系统直接判断区间，无需二次计算。

**写入格式**：

```json
{
  "price_bands": [47.4, 43.12, 40.05],
  "price_bands_basis": "pb.y3+ps3",
  "price_bands_date": "2026-04-30"
}
```

`price_bands_basis` 后缀说明：`pb.y3` = 纯PB分位；`pb.y3+ps3` = PB分位+PS+3加成；`pe_ttm.y3+ps2` = PE分位+PS+2加成；以此类推。

字段说明：

| 字段 | 含义 |
|---|---|
| `price_bands[0]` | 追高线（最终调整后），当前价超过此值 → 🔴 |
| `price_bands[1]` | 中性底（P50历史估值），当前价在[1]~[0] → 🟡 |
| `price_bands[2]` | 最优区起点（P20历史估值），当前价 < [2] → 🟢🟢 |
| `price_bands_basis` | 分位来源+PS加成标注 |
| `price_bands_date` | 计算时使用的估值数据日期，格式 YYYY-MM-DD |

**注意事项**：
- 数字数组，不填文字描述字符串
- 银行/保险：`price_bands_basis` 以 `pb.y3` 为前缀，公式为 `q值 × BPS`
- PE < 0（亏损）：`price_bands = null`，在 notes 注明「当期亏损，price_bands暂不适用」
- 每次做 PreBuy 更新时同步刷新这三个字段，不允许保留旧值

---

### 价格区间表：页面内必须放最终调整值，位置在最后

**公司页「价格与时机判断」章节的最终价格区间表，必须遵守：**

1. **内容为最终值**：表格数值须已叠加所有调整（PS政策加成、周期位置调整），不展示调整前的原始P80/P50/P20值（原始分位数据可在表格前以参考形式列出，但最终表格必须是调整后的最终区间）

2. **位置在章节最后**：表格放在「近60日走势概述」「当前口径」「政策加成调整说明」之后，作为整节的最终结论

3. **表格标题**必须注明「最终价格区间（含[调整原因]）」，如：「最终价格区间（含PS+3政策顺风加成）」

4. **与 watchlist 保持一致**：`price_bands[0]` 对应表格红/黄分界，`price_bands[1]` 对应黄/绿分界，`price_bands[2]` 对应绿/双绿分界

### 第 4 步：把公司压缩成一句话

输出时必须写一句「公司本质」：
- 它是什么公司
- 真正的利润引擎是什么
- 当前市场为什么愿意给它这个估值

如果一句话说不清，说明研究还没完成。

### 第 5 步：写反证条件

每次都要写至少 3 条「我为什么可能错」。

反证条件通常来自：
- 业绩不兑现
- 现金流恶化
- 并购整合失败
- 行业景气回落
- 热门业务收入占比远低于想象

### 第 6 步：最后才讨论买不买

不要直接把「喜欢这家公司」翻译成「应该马上买」。

综合基本面结论（模块 1–12）和政策加权结果（模块 13），选择最终口径。若模块 13 的 PS 触发了升降档，在结论中明确写出加权理由，不能静默调整。

## 红旗分级

- **一票否决型**：财务造假、非标审计意见、重大行政处罚、持续经营疑虑
- **高风险型**：经营现金流持续背离利润、商誉减值风险大、客户高度集中、大股东高比例质押
- **观察型**：估值偏高、催化剂不确定、主题叙事过强

出现一票否决型红旗时，结论必须为「核心疑点未解，不建议买入」。

## 价值投资常见认知陷阱

在输出分析结论时，主动对照以下陷阱进行自查。如用户的买入逻辑触发了某条陷阱，**必须在核心雷点中明确点出**。

### 陷阱 1：低 PE 等于便宜（价值陷阱）

低 PE 可能是市场已定价未来利润下滑，而非错杀。常见于：
- **周期股景气顶部**：钢铁/猪肉/煤炭在利润最高时 PE 最低，但此时往往是卖点
- **基本面持续恶化**：市场提前反映利润萎缩，表观 PE 低但前向 PE 已不低
- **资本配置差**：赚的钱回报率极低，市场给折价

> 检查项：这家公司的低 PE 是错杀，还是行业景气/利润下行的折价？

### 陷阱 2：护城河被当成免死金牌

护城河是会被侵蚀的，不是永久有效的护盾。必须评估：
- 技术护城河是否面临颠覆性替代
- 渠道/品牌护城河是否被新兴平台绕开
- 客户粘性是否依赖政策或历史惯性（容易被反转）

> 检查项：这家公司的护城河在过去 3 年是加深了，还是在变浅？

### 陷阱 3：只看利润，不看现金流

> "利润是意见，现金流是事实。"

触发条件：净利润增长 + 经营现金流下滑 + 应收快速扩张 → 利润质量存疑，必须列为高风险红旗。

### 陷阱 4：把「长期持有」当成「不用止损」

「长期持有」的前提是基本面没有根本性变化。如果：
- 买入逻辑已经被证伪（核心业务失去竞争力、行业格局逆转）
- 出现一票否决型红旗（财务造假、非标审计）

则必须重新评估，不能以「长期视角」为由回避结论。

### 陷阱 5：用静态估值判断周期股

周期股应用 **PB** 而非 PE 判断低位：
- PE 最低时（景气顶部）往往是卖点
- PE 最高或亏损时（景气底部）往往是买点
- 适用行业：钢铁、煤炭、化工、猪产业、航运

> 检查项：这是不是周期股？如果是，应切换为 PB 分位判断。

### 陷阱 6：高杠杆伪装的高 ROE

对 ROE ≥ 20% 的公司必须做杜邦分解：

```
ROE = 净利率 × 资产周转率 × 财务杠杆
```

如果高 ROE 主要来自财务杠杆（而非净利率或周转率），则是高风险结构。房地产、部分金融类公司的高 ROE 应打折评估。

### 陷阱 7：叙事强度 ≠ 投资价值

热门赛道（AI、新能源、机器人等）叙事越强，估值泡沫风险越高。检查：
- 热门业务在总收入中占比有多大？
- 当前估值隐含的增速是否现实（反推隐含增速）？
- 市场是在买确定性业绩，还是在买想象空间？

> 触发条件：用户的买入理由以「赛道空间大」为核心，而无法描述公司当前的盈利节奏 → 标注「主题叙事过强」观察红旗。

### 陷阱 8：仓位管理缺失

如果用户未说明仓位计划，必须主动询问或在结论中提示：
- 单只个股建议仓位上限：无历史验证者 ≤ 10-15%
- 有硬红旗但用户仍想买：最多「可试错小仓位」口径，且必须写明退出条件
- 首次买个股：执行首次买股特别规则（见下方）

### 陷阱 9：把「读懂逻辑」等同于「有能力估值」

能描述护城河 ≠ 能判断当前价格是否已反映这一护城河。每次分析必须回答：
- 当前 PE 隐含的未来增速是多少？
- 这个增速在历史上该公司是否实现过？
- 即使逻辑正确，赔率是否足够？

## 标准输出格式

### A. 公司一句话

一句话说明公司本质，不要写成宣传文案。

### B. 买入逻辑

只写 2-4 条，且每条必须可验证。每条附来源（文件名 / 平台名 + 日期）。

### C. 必盯指标

至少包含：
- 收入或订单
- 扣非利润或毛利率
- 经营现金流或营运资金

### D. 核心雷点

至少写 3 条，按红旗分级（一票否决 / 高风险 / 观察）排序。

### E. 催化剂与时间线

列出未来 2 个季度的关键验证节点。

### F. A股特有风险检查（A股/港股必做）

灯号说明：🟢 无明显风险 / 🟡 需跟踪，有一定压力 / 🔴 重大负面信号

| 风险项 | 灯号 | 说明 |
|---|---|---|
| 限售解禁（3个月内） | 🟢/🟡/🔴 | 解禁规模/流通盘比例、解禁方类型与成本 |
| 大股东/管理层减持 | 🟢/🟡/🔴 | 是否有进行中的减持计划或近期集中减持 |
| 股权质押 | 🟢/🟡/🔴 | 控股股东质押比例及与预警线/平仓线的距离 |
| 监管政策突变 | 🟢/🟡/🔴 | 行业政策方向、近期监管动作及整改通知 |
| 再融资/摊薄 | 🟢/🟡/🔴 | 在途定增/配股/可转债方案及历史融资依赖度 |
| 商誉减值 | 🟢/🟡/🔴 | 商誉/净资产占比及并购标的业绩达成情况 |
| 实控人/大股东行为 | 🟢/🟡/🔴 | 实控人稳定性、资用占用历史、同业竞争 |
| 信披质量 | 🟢/🟡/🔴 | 问询函历史、审计师变更、是否有非标意见 |

> 任何一项为 🔴 须在「D. 核心雷点」中同步列出，并说明是否构成一票否决。

### G. 政策顺逆风评估

列出本次分析所依据的生效中政治会议，及对照结果：

| 会议 | 生效截止 | 匹配信号 | 得分 |
|---|---|---|---|
| [会议名] | YYYY-MM-DD | 利好：xxx；无利空匹配 | +N |

**政策净得分（PS）**：`+N`

**加权影响**：
- 结论口径：[升一档 / 无调整 / 降一档，说明原因]
- 价格区间：[绿灯区上界 +10% / 无调整 / 收窄 10%]
- Watchlist：[可升档 / 无调整 / 注明逆风不加仓]

> 若无生效政策页或 PS = 0，注明「无政策加权，依纯基本面判断」。

### H. 周期位置判断（周期股必做，非周期股标注「不适用」）

**是否为周期股**：是 / 否（理由）

**周期类型**：[商品价格周期 / 资本开支周期 / 农业周期 / 不适用]

| 维度 | 当前信号 | 说明 |
|---|---|---|
| PB历史分位 | XX% 分位 | 具体数值 |
| ROE趋势 | ↑/→/↓ | 近4期变化 |
| 产品价格趋势 | ↑/→/↓ | 数据来源+日期 |
| Capex/产能趋势 | 扩张/收缩 | 行业层面 |
| 库存周期 | 主动补/被动补/主动去/被动去 | 若有数据 |

**当前周期阶段**：[底部/复苏早期 / 复苏中期 / 景气高峰 / 收缩期 / 出清期]

**对结论和价格区间的影响**：
- 结论口径：[升一档 / 维持 / 降一档，说明]
- 价格区间：[切换PB定价 / 无调整 / 追高区下移XX%]
- 关键警告：[如「当前PE低是景气顶部假象，实为卖点」]

### I. 价格走势与买入时机

> ⚠️ **此节在 F/G/H 完成之后填写，确保 PS 分数和周期位置已确定，价格表为最终调整值。**

必须包含：
- 近期走势概述（近 30/60 日涨跌幅、当前价在区间中的位置）
- 近期重大事件对股价的影响（如财报发布后涨幅）
- 成交量/换手率异常信号
- 政策加成调整说明（PS 取值来自 G 节，周期调整来自 H 节）
- **最终价格区间表**（含所有调整后的最终数值，标题注明调整来源）
- 明确的时机判断：当前价位适合买入 / 等回调 / 不急

### J. 当前结论

只允许下列口径之一，并附判定理由：

| 口径 | 判定条件 |
|---|---|
| 适合继续研究，不适合立刻买 | 有明确逻辑，但至少 2 个关键问题未核实 |
| 可以试错，但只能小仓位 | 无硬红旗、已有 1-2 个可验证催化剂，但仍有重要不确定性 |
| 逻辑清晰，等待更合适价格或验证点 | 基本面较清晰，但赔率不够或验证点未到 |
| 逻辑清晰，当前价格合理，可按计划买入 | 无硬红旗、基本面清晰、估值合理、价格处于绿灯区间 |
| 核心疑点未解，不建议买入 | 存在审计、现金流、监管、治理等一票否决型红旗 |

---

## 首次买股特别规则

如果用户是第一次买个股，执行以下硬约束：
- 默认不给「立即买入」口径
- 必须要求用户写出：一句买入逻辑、3 条反证条件、仓位上限、退出条件
- 特别强调仓位管理

## 额外要求

- 默认使用简体中文输出
- 默认优先引用法定披露源
- 每个核心结论必须附来源（文件名 / 平台名 + 日期），无法核实的标注「待核实」
- 如果用户要求教学，解释要围绕「为什么查这个模块」展开，而不是只报结论
