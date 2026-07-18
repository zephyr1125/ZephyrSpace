---
name: stock-prebuy-review
description: >-
  在用户准备买入某只上市公司股票前使用，用于做买入前基本面尽调、红旗排查和买入逻辑验证。
  适用场景：个股研究、买入前排雷、基本面核查、财报质量审视、现金流质量、商业模式分析、
  治理与股东行为、监管司法风险、估值合理性判断（含历史百分位、PEG、隐含增速、绝对估值：DCF/EPV/RI/DDM/SOTP/反向DCF）、
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

**法定披露源（年报 / 公告 / 监管文件）**
- **A 股** → 巨潮资讯网 / 上交所 / 深交所 / 证监会
- **港股** → 披露易 HKEXnews / 港交所

**量化数据 API（估值 / 财务 / 监管措施）**
- **A 股** → 理杏仁（主力）；东方财富 web_fetch（补充 / QDATE 验证）
- **港股** → 暂无覆盖，以法定披露源为准

详见 [references/source-map.md](references/source-map.md)。

## 默认工作流

### 第 1 步：确认标的信息

先确认：
- 股票代码 / 公司全称 / 交易市场（A 股 / 港股）
- 想做完整研究，还是快速排雷

如果同名公司存在 A/H 双重上市，先确认交易标的。

**公司页处理规则（检查 `01-公司/` 是否已有对应页面）：**

| 用户描述 | 处理方式 |
|---|---|
| 「重新 PreBuy」/ 「从头 PreBuy」/ 「重做」 | **先删除**现有公司页，再按模板从头创建 |
| 「更新」/ 「刷新」/ 「季报更新」 | **保留**现有页面，在原有章节基础上覆盖更新数据 |
| 首次分析（页面不存在） | 按模板新建 |

> 删除时使用 `Remove-Item` 或 Obsidian CLI `delete` 命令，确认后再重建，避免新旧数据混用导致结论前后矛盾。

---

### 第 2 步：行业质量评分（IQS）

**目的**：在研究个股之前，先给这家公司所在的细分行业打分（100 分制）。行业质量决定了一个公司利润的天花板和护城河的可持续性——再优秀的公司，在劣质行业里也难以维持高 ROE。

IQS 评级结果会影响对公司质量的解读门槛：同样 ROE 18% 的公司，在 IQS 85 的行业里属正常，在 IQS 45 的行业里才是真正的奇迹。

---

#### 0.5a. 确认细分行业名称

- 以**最小竞争层粒度**命名（如"BOPP 电工膜"，而非"化工"；"城商行"，而非"银行"）
- 行业名称即为分析文件的核心关键词

#### 0.5b. 检查行业分析文件是否存在

**检查路径**：`04-A股行业/[细分行业名称] 行业分析.md`

```powershell
# 快速检查
Get-ChildItem "E:\ObsidianVaults\ZephyrSpace\04-A股行业\" -Filter "*[行业关键词]*"
```

| 情况 | 处理方式 |
|---|---|
| **文件已存在，更新时间 ≤ 6 个月** | 直接读取 IQS 总分和各维度，跳至 0.5d |
| **文件已存在，但 >6 个月未更新** | 重新评分后更新文件，再执行 0.5d |
| **文件不存在** | 按 `[[00-首页/行业分析模板]]` 创建新文件，执行 0.5c 后跳至 0.5d |

> ⚠️ 行业分析文件是**活文档**：由同行业第一家公司 PreBuy 时创建，此后分析同行业公司时直接复用。写得越仔细，后续复用价值越高。

---

#### 0.5c. IQS 七维评分（新建或重评时执行）

七个维度覆盖行业盈利能力的主要决定因素：

| 维度 | 满分 | 核心问题 |
|---|---|---|
| **1. 上下游定价权** | 20 | 对买方（10分）+ 对供应商（10分）双向议价能力 |
| **2. 竞争格局成熟度** | 20 | 行业集中度与胜负阶段，越往后越好 |
| **3. 规模经济方向** | 15 | 越大越容易赚钱（15）→ 中性（7）→ 越大越难赚（2） |
| **4. 进入壁垒叠加** | 15 | 监管(+4)＋技术(+4)＋资本(+3)＋认证(+3)＋网络(+4)，上限 15 |
| **5. 行业基础盈利水平** | 15 | 行业均值 ROE：>20%=15，15–20%=12，10–15%=9，5–10%=5，<5%=2 |
| **6. 周期稳定性** | 10 | 非周期=10，弱周期=7，中等=5，强周期=2，超强周期=1 |
| **7. 成长天花板** | 5 | CAGR >15%=5，5–15%=3，0–5%=2，萎缩=0 |

**评分细则——维度 2（竞争格局成熟度）参照表**：

| 格局阶段 | CR5 参考 | 特征 | 得分 |
|---|---|---|---|
| 绝对垄断（监管许可）| >90% | 近无竞争 | 18–20 |
| 寡头已定 | 70–90% | 2–3 家主导，格局稳固 | 14–17 |
| 头部收敛（整合尾声）| 50–70% | 龙头已现，整合仍推进 | 10–13 |
| 整合中（淘汰赛）| 30–50% | 明显洗牌，价格战可能存在 | 6–9 |
| 百舸争流 | <30% | 分散竞争，利润薄 | 2–5 |
| 逆向集中（反垄断压制）| 被迫分散 | 监管阻止进一步集中 | 1–3 |

**IQS 评级解读**：

| 分数段 | 评级 |
|---|---|
| 85–100 | ⭐⭐⭐⭐⭐ 稀缺优质——行业本身就是护城河（典型：白酒、银行核心业务） |
| 70–84 | ⭐⭐⭐⭐ 优质——好行业，值得深挖龙头 |
| 55–69 | ⭐⭐⭐ 普通——需要特别优秀的公司才值得持有 |
| 40–54 | ⭐⭐ 难赚钱——行业本身拖累利润，需要超强个股护城河 |
| <40 | ⭐ 劣质——规避，除非短期政策催化剂或极端低估 |

将评分和结论写入 `04-A股行业/[行业名] 行业分析.md`，并在"引用此分析的公司页"一节追加本公司链接。

---

#### 0.5d. 写入公司页 `## 行业质量评分（IQS）` 区块

在公司页的该区块中：
1. 填写 `> 详见 [[04-A股行业/XXX 行业分析]]`
2. 填入七维度汇总表（分数+一句话理由）
3. 标注 IQS 总分和对公司质量门槛的解读含义

---

### 第 3 步：固定查 14 个模块

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

#### 模块 2：公司竞争位置与定价权

> ℹ️ 行业整体质量已在第2步 IQS 中评估。本模块聚焦于**这家公司在行业内的具体竞争位置**，引用 IQS 结论，不重复行业级分析。

必查：
- 主要客户名单、市场份额或行业排名、关键认证/资质
- 行业中的角色定位：设备商、零部件商、平台商、运营商
- 竞争对手列表及差异化来源（技术、成本、认证、品牌）

**波特五力三问（公司层面快速应用）**：

1. **议价能力**：能向供应商压价吗？能向客户转移成本吗？（看客户集中度、供应商可替代性）
2. **竞争差异**：vs 主要竞争对手，差异化/成本领先/细分垄断体现在哪里？
3. **进入门槛**：需要哪几道门槛叠加（资本、技术、认证、品牌、规模、监管资质）才能复制这门生意？

综合评定护城河强度（⭐1–5星）及主要结构性弱点，写入公司页"波特五力分析"区块。

**定价权评估（每家公司必做，结果写入公司页"定价权评估"区块）**

| 来源类型 | 典型特征 | 常见行业 |
|---|---|---|
| 品牌溢价 | 消费者愿意为品牌支付价格差 | 白酒、奢侈消费品、医美 |
| 客户转移成本 | 切换供应商需要重新认证、培训、系统对接 | 工业软件、医疗设备、关键零部件 |
| 网络效应 | 用户越多价值越高，后来者难以替代 | 交易平台、社交、支付 |
| 监管/资质壁垒 | 牌照、GMP、军工资质等准入限制竞争 | 药品、金融、航空 |
| 成本领先 | 规模/技术优势使成本远低于竞品 | 光伏、锂电、化工 |
| 垂直整合/独家供应 | 上下游锁定，无替代来源 | 稀土、特种材料、核心部件 |
| 无（纯价格竞争） | 同质化产品，价格由市场决定 | 大宗商品、低端制造 |

验证方法：
- **毛利率趋势**：近3–5年稳定或上升 → 定价权存在；持续下滑 → 弱或正在瓦解
- **提价历史**：有过主动提价且客户不流失 → 强定价权佐证
- **成本传导**：原材料涨价时毛利率能否维持稳定 → 判断成本转嫁能力

综合评级写入公司页和 `## 必盯指标` 区块：

| 评级 | 标准 | 对结论的影响 |
|---|---|---|
| ⭐⭐⭐ 强定价权 | 有来源 + 毛利率稳定/上升 + 有提价记录 | 估值可给溢价，ROE 持续性更强 |
| ⭐⭐ 中等定价权 | 有一定壁垒但受竞争制约，毛利率波动 | 正常估值，关注竞争格局变化 |
| ⭐ 弱定价权 | 靠成本控制或量的增长，无法主动提价 | 利润天花板较低，高 PE 需谨慎 |
| ❌ 无定价权 | 纯价格竞争，行业均价决定利润 | 估值折价，周期属性强 |

要回答：
- 这家公司是行业龙头、跟随者，还是单一客户附庸
- 护城河来自技术、客户认证、成本、规模，还是仅靠景气
- IQS 评级与公司实际护城河是否相符（若行业 IQS 高但本公司护城河弱，需说明原因）

红旗：
- 只说布局，不说量产和客户
- 只说未来空间，不说当前竞争位置
- 🔴 毛利率近3年持续下滑 >5pct，同时竞争对手数量增加（定价权正在瓦解）
- 🔴 公司将提价失败归咎于"行业竞争激烈"但无法说明改善路径
- 🟡 声称品牌溢价，但终端价格与竞品差距在收窄
- 🟡 毛利率高于同行但主要依赖单一大客户（议价权实质上在对方手里）

> ⚠️ **定价权与周期的交叉判断**：周期股在景气期看似有定价权，实为价格周期红利，并非真定价权。需区分「市场价格上涨带来的被动受益」vs「公司主动提价客户不走的真定价权」。

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

**杜邦分析（每家公司必做，ROE≥10% 时必须拆解驱动因素）**

ROE = 净利率 × 资产周转率 × 权益乘数

| 年份 | 净利率（净利/营收） | 资产周转率（营收/总资产） | 权益乘数（总资产/净资产） | ROE |
|---|---|---|---|---|
| 20XX | X% | X次 | X倍 | X% |
| 20XX | X% | X次 | X倍 | X% |
| 20XX | X% | X次 | X倍 | X% |

**驱动因素判断**：
- ✅ 净利率驱动：运营效率提升、产品溢价提升，是最健康的ROE增长来源
- ✅ 资产周转率驱动：资产使用效率提升，轻资产模式红利
- ⚠️ 权益乘数驱动：主要靠加杠杆推升ROE，需结合负债率判断风险
- 🔴 ROE高但由权益乘数主导（乘数>3x）：必须在红旗中标注"高杠杆伪装高ROE"

写入公司页"杜邦分析"区块；如果三年数据不完整，至少做最近年报的截面拆解。
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


**行业横向对比估值（必做，写入公司页）**

找 3-5 家同赛道可比公司，构建对标表：

| 公司 | 代码 | PE TTM | PE 3年分位 | ROE | OCF/净利 | 市值 | 定位差异 |
|---|---|---|---|---|---|---|---|
| 本公司 | XXXX | Xx | X% | X% | X% | XX亿 | — |
| 可比A | XXXX | Xx | X% | X% | X% | XX亿 | 说明差异 |
| 可比B | XXXX | Xx | X% | X% | X% | XX亿 | 说明差异 |

**对比结论要回答**：
1. 本公司在对标组中估值偏高/持平/偏低？差异是否合理（成长溢价 or 折价的来源）？
2. ROE和OCF质量在同组排名如何？若估值低但质量高，是低估信号
3. 市值差异是否反映了合理的竞争地位差距？

> ⚠️ **横向PE对比的陷阱**：只比PE不比业务纯度和增长质量是无效比较。同一行业不同商业模式（OEM vs 品牌、上游vs下游）的估值体系不可直接类比，必须注明业务差异并说明对比的合理性。

### 9B. 绝对估值（补充参考）

> ⚠️ **定位说明**：
> - 绝对估值**独立于 9A 的相对估值**，不作为 `price_bands` 或 watchlist 档位的计算输入
> - 目的是提供一个不依赖市场情绪的内在价值锚点，与 9A 相对估值交叉验证
> - 所有假设必须显式声明，输出估值**区间判断**（低估/合理/高估），而非精确目标价
> - 若关键假设（增速或 WACC）微小变动（±1%）导致估值变动 >30%，标注"低置信度"
> - 本节结论写入公司页 `## 估值与买入赔率` 区块，紧接在 9A 横向对比之后

#### 9B.0 公司类型分流（决定用哪种绝对估值法）

| 公司类型 | 判断条件 | 适用方法 | 原因 |
|---|---|---|---|
| **金融类** | 银行 / 保险 / 券商 | 剩余收益模型（RI） | 金融企业无传统 FCF，存贷款即经营本身 |
| **稳定现金流** | 消费龙头/水电/公用事业；近 3 年 FCF 变异系数 < 30% | 简化两阶段 DCF | FCF 可预测，DCF 适用 |
| **周期股** | 模块 13 确认为周期股（化工/钢铁/煤炭/航运/养殖等） | 归一化盈利 EPV | 周期股利润大起大落，EPV 取跨周期均值 |
| **高成长/亏损** | PE < 0，或（营收增速 > 30% 且 PE > 60x） | 反向 DCF | 传统 DCF 对高成长公司终端价值占比过高 |
| **多元控股** | ≥ 3 个显著不同的业务板块，无单一主导 | 分部估值法（SOTP） | 整体 PE 对多元化公司无意义 |
| **高分红** | 近 3 年分红率 > 50%，且盈利稳定 | 股息折现模型（DDM） | 对"债券替代品"最简单有效 |
| **默认/其他** | 以上均不匹配 | EPV（盈利能⼒价值） | 最少假设，通用性最强 |

> 若公司同时满足多个条件（如"稳定现金流 + 高分红"），优先选更具体的类型（高分红 > 稳定现金流 > 默认）。

#### 9B.1 WACC / 要求回报率速算（所有方法共用）

```python
# ===== WACC 速算（非金融公司）=====

# 权益成本（CAPM 简化）
risk_free_rate = 0.025   # 中国 10 年期国债收益率（约 2.5%）
erp = 0.06               # A 股股权风险溢价（5-7%，默认 6%）

# Beta 估算（理杏仁 fundamental 接口不含 beta 字段，按以下规则估算）：
#   稳定消费/公用事业           beta ≈ 0.7-0.9
#   一般制造业/均衡型           beta ≈ 1.0
#   周期股（化工/钢铁/有色）     beta ≈ 1.0-1.3
#   高成长科技/小市值           beta ≈ 1.2-1.5
# 也可用 Tavily 搜索 "{ticker} beta A股 近1年" 获取更精确值
beta = 1.0  # 默认 1.0，有更精确数据后修正

cost_of_equity = risk_free_rate + beta * erp  # e.g., 0.025 + 1.0×0.06 = 8.5%

# 债务成本
cost_of_debt_pre_tax = 0.04   # 默认 4%，优质公司可更低

# WACC
# 权重从 E4 资本结构取：equity_weight = 净资产/(净资产+有息负债)
equity_weight = 0.75  # 默认值，用实际数据替换
debt_weight = 1 - equity_weight
tax_rate = 0.25  # 法定所得税率
wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt_pre_tax * (1 - tax_rate)

# 要求回报率（用于 RI / DDM / EPV，不单独计算 WACC 时用）
required_return = cost_of_equity  # 通常 8-11%
```

> ⚠️ **WACC 不是精确数字**。8% vs 10% 的差异在显式期影响有限，但在终端价值中影响巨大。当 WACC 变动 1% 导致估值变动 >20% 时，必须在结果中标注"WACC 敏感"。

#### 9B.2 执行对应估值方法

---

**方法 ①：剩余收益模型（RI）—— 金融类**

```python
# 原理：股权价值 = 当期净资产 + 未来剩余收益的现值
# 剩余收益 = (ROE - 权益成本率) × 期初净资产

# 输入
current_book_value = 净资产  # 亿元，理杏仁 fs/bank: ta - tl
current_roe = 最近年报 ROE   # 小数，银行从东方财富 WEIGHTAVG_ROE
cost_of_equity = required_return  # 从 9B.1

# 投影假设（保守）：ROE 在 3 年内从当前值线性衰减至权益成本率
# 衰减后剩余收益 = 0（ROE = 权益成本率时无超额回报，不需终值）
projection_years = 3
bv = current_book_value
pv_ri = 0

for t in range(1, projection_years + 1):
    roe_t = current_roe - (current_roe - cost_of_equity) * (t / (projection_years + 1))
    roe_t = max(roe_t, cost_of_equity * 0.8)  # 不低过权益成本的 80%
    ri = (roe_t - cost_of_equity) * bv
    pv_ri += ri / ((1 + cost_of_equity) ** t)
    dividend_payout = 0.30  # 从 F2 分红率取
    bv = bv * (1 + roe_t * (1 - dividend_payout))  # 净资产增长

equity_value = current_book_value + pv_ri       # 亿元
per_share = equity_value / 总股本（亿股）       # 元/股
```

> 输出格式：`剩余收益模型：每股 XX 元（假设：ROE 从 X% 3 年衰减至 X%，权益成本 X%）`

---

**方法 ②：简化两阶段 DCF —— 稳定现金流**

```python
# 阶段 1：未来 5 年显式 FCF；阶段 2：永续增长（Gordon Growth）

# 输入
base_fcf = 近 3 年（经营现金流 - 折旧摊销）均值  # 亿元
# 或"经营现金流 × 0.7"作为近似的 FCF（仅当无 Capex 明细时）
# ⚠️ 若公司有官方 FCF 口径，以官方为准

fcf_growth = 近 3 年 FCF CAGR × 0.7  # 打 7 折保守化
fcf_growth = min(fcf_growth, 0.15)     # 上限 15%
terminal_g = 0.025                      # 永续增长率，上限 3%（≈ 名义 GDP 增速）
wacc = 9B.1 计算的 wacc

# 显式期折现
pv_explicit = 0
fcf_t = base_fcf
for t in range(1, 6):
    fcf_t = fcf_t * (1 + fcf_growth)
    pv_explicit += fcf_t / ((1 + wacc) ** t)

# 终端价值
terminal_value = fcf_t * (1 + terminal_g) / (wacc - terminal_g)
pv_terminal = terminal_value / ((1 + wacc) ** 5)

# 企业价值 → 股权价值
enterprise_value = pv_explicit + pv_terminal
equity_value = enterprise_value + 现金及等价物 - 有息负债 - 少数股东权益
per_share = equity_value / 总股本

# 置信度检查
tv_ratio = pv_terminal / enterprise_value
if tv_ratio > 0.70:
    print(f"⚠️ 终端价值占比 {tv_ratio:.0%}，>70%，标注'低置信度'")
```

> 输出格式：`DCF 估值：每股 XX 元（假设：FCF 增速 X%，WACC X%，永续增长 X%，终端占比 X%）`
> 估值区间：下界 = WACC + 1% 场景，上界 = 增速 + 1% 场景

---

**方法 ③：归一化盈利 EPV —— 周期股 / 默认**

```python
# 原理：取跨周期平均盈利，按"零增长永续"折现 → 价值地板

# 归一化经营利润（取最近一个完整周期的算术平均）
# 周期长度参考：化工 3-5 年，钢铁/煤炭 5-7 年，航运 5-7 年
op_profits = [近 N 年经营利润]  # 亿元，从理杏仁 fs/non_financial
# 取"营业利润"或"利润总额"（不含非经常性）
normalized_ebit = sum(op_profits) / len(op_profits)

# 不剔除亏损年份——亏损本身就是周期的一部分
# 但剔除单次 > 年利润 30% 的重大非经常性项目（资产出售、大额减值等）

normalized_nopat = normalized_ebit * (1 - 0.25)  # 税后

# EPV
wacc = 9B.1 计算的 wacc
epv = normalized_nopat / wacc

# 调整项
excess_cash = max(0, 现金及等价物 - 短期有息负债)
total_debt = 有息负债总额

equity_value = epv + excess_cash - total_debt
per_share = equity_value / 总股本

# 变异系数检查
import statistics
cv = statistics.stdev(op_profits) / abs(statistics.mean(op_profits))
if cv > 0.30:
    print(f"⚠️ 近 {len(op_profits)} 年经营利润变异系数 {cv:.0%}，>30%，标注'低置信度'")
```

> 输出格式：`EPV：每股 XX 元（近 N 年均盈利 XX 亿，WACC X%，变异系数 X%）`
> 解读：这是公司的"零增长地板价"——即使未来不再增长，可持续盈利也支撑这个价值。

---

**方法 ④：反向 DCF —— 高成长/亏损**

```python
# 不计算"公司值多少钱"，而是回答"当前股价隐含了多少增速"

current_market_cap = 总市值（亿元）    # 理杏仁 fundamental: mc / 1e8
wacc = 9B.1 计算的 wacc
terminal_g = 0.025

# 二分搜索：找到使 DCF ≈ 当前市值的隐含 5 年 FCF CAGR
def find_implied_growth(market_cap, base_fcf, wacc, terminal_g):
    lo, hi = 0.0, 0.50  # 搜索 0-50%
    for _ in range(50):
        mid = (lo + hi) / 2
        pv_explicit = 0
        fcf_t = base_fcf
        for t in range(1, 6):
            fcf_t *= (1 + mid)
            pv_explicit += fcf_t / ((1 + wacc) ** t)
        terminal = fcf_t * (1 + terminal_g) / (wacc - terminal_g)
        ev = pv_explicit + terminal / ((1 + wacc) ** 5)
        if ev > market_cap * 1.05:
            hi = mid
        elif ev < market_cap * 0.95:
            lo = mid
        else:
            return mid
    return (lo + hi) / 2

implied_cagr = find_implied_growth(current_market_cap, base_fcf, wacc, terminal_g)
# 若 base_fcf ≤ 0（公司亏损），反向 DCF 失效，标注"亏损公司，反向 DCF 不适用"
```

> 输出格式：`反向 DCF：当前股价隐含未来 5 年 FCF CAGR ≈ X%（WACC = X%）`
> 判断参考：隐含增速 > 20% 且公司历史上从未达到 → 偏乐观；隐含增速 < 5% 而近年增速 > 15% → 偏保守

---

**方法 ⑤：分部估值法（SOTP）—— 多元控股**

```markdown
| 业务板块 | 营收占比 | 适用方法 | 估值（亿元） | 依据 |
|---|---|---|---|---|
| 板块 A | X% | PE | XX | 可比公司 PE 中位数 Xx |
| 板块 B | X% | PB/EPV | XX | 说明 |
| 板块 C | X% | DCF | XX | 自算 |
| **分部合计** | | | **XX 亿** | |
| 减：集团费用现值 | | | -XX | 近 3 年均值 × 10 |
| 减：净债务 | | | -XX | |
| **权益价值** | | | **XX 亿** | |
| **每股价值** | | | **XX 元** | |
```

> 每个板块选最合适的估值法（复用 9B.0 分流逻辑），至少 2 个板块有可比公司锚定。

---

**方法 ⑥：股息折现模型（DDM）—— 高分红**

```python
# 仅适用于分红率 > 50%、盈利稳定的"债券替代品"

current_dps = 最近一年每股分红（元）   # 理杏仁 dividend 接口
dividend_growth = 近 3 年股息 CAGR × 0.8  # 8 折保守化
dividend_growth = min(dividend_growth, 0.05)  # 上限 5%
required_return = 9B.1 的 cost_of_equity

if dividend_growth >= required_return:
    print("⚠️ 股息增速 ≥ 折现率，戈登模型失效，改用 EPV")

per_share = current_dps * (1 + dividend_growth) / (required_return - dividend_growth)

# 支付能力验证
payout_ratio = current_dps / eps
if payout_ratio > 0.80:
    print("⚠️ 分红率 > 80%，可持续性存疑")
```

> 输出格式：`DDM：每股 XX 元（股息增速 X%，要求回报 X%，分红率 X%）`

---

#### 9B.3 估值三角验证

将绝对估值与相对估值做交叉验证，写入公司页 `## 估值与买入赔率` 区块：

| 估值来源 | 方法 | 参考区间（元/股） | 置信度 |
|---|---|---|---|
| 绝对估值（9B） | [方法名] | XX - YY | 高/中/低 |
| 相对估值（9A） | price_bands（历史分位） | [bands[2]] - [bands[0]] | — |
| 当前股价 | — | XX 元 | — |

**三角验证判断**：

| 信号 | 含义 | 处理 |
|---|---|---|
| ✅ 方向一致 | 绝对估值和相对估值结论同向（都便宜/合理/贵） | 高置信度，可据此调整仓位判断 |
| ⚠️ 方向矛盾 | 一个说便宜一个说贵 | 标注"估值信号矛盾"，分析矛盾来源（如周期股 PE"虚假低位"） |
| 🔴 区间过宽 | 绝对估值上界/下界 > 1.5 倍 | 标注"低置信度"，不做仓位参考 |

> ⚠️ **硬约束**：
> 1. 绝对估值结果**不修改** `price_bands`（price_bands 始终基于历史分位）
> 2. 绝对估值结果**不改变** watchlist 档位
> 3. 若 9B 和 9A 方向矛盾，在最终结论 J 节中注明分歧及原因
> 4. 禁止输出"目标价 87.3 元"式的精确数字——绝对估值只做区间判断，结论只表述为"当前价格低于/接近/高于内在价值估算区间"

红旗：
- 只拿横向 PE 比，不看业务纯度和增长质量
- 把「便宜」当成买入理由本身
- PE 处于历史 80% 分位以上且增速放缓
- 市值/市梦率与当前收入利润严重脱节

#### 模块 10：催化剂与验证时间线

必查：
- 下次财报披露时间（见下方「下一期财报日期」确认方法）
- 关键订单 / 新产能 / 监管审批节点
- 诉讼 / 处罚进展
- 解禁 / 减持窗口

要回答：
- 未来 2 个季度最关键的验证指标是什么
- 如果哪个指标不达标，逻辑就要修正

**下一期财报日期（必做，结果写入公司页 frontmatter 和 watchlist）**

目的：掌握下次「成绩单」发布时间，在财报窗口期前评估仓位风险，并跟踪买入逻辑是否得到验证。

> 🔴 **关键规则：`null` = 未知。** 若无法从公司官方公告（董事会会议通知等）确认具体披露日期，`next_earnings_date` 必须写 `null`。
> **禁止使用以下值填充：**
> - 交易所法定截止日（`08-31`、`04-30`、`10-31`）
> - 平台默认预约日（东方财富/同花顺常以截止日填充）
> - 历史规律推算或同类公司类推
>
> **正确做法**：
> 1. 先用 Tavily 搜索 `"[公司名] [当前年月] 董事会 业绩披露 预告"` 查找公司官方公告
> 2. 搜到官方公告确认的日期 → 写入 `next_earnings_date`
> 3. 搜不到 → 写 `null`，在 `next_earnings_type` 中标注预期财报类型

```python
# 辅助：确定下一期财报类型（不改日期）
from datetime import date

def get_next_earnings_type(today=None):
    """根据A股披露周期，返回下一期财报类型。日期不填。"""
    if today is None:
        today = date.today()
    y, m = today.year, today.month
    if m < 4:
        return "一季报"
    elif m < 8:
        return "半年报"
    elif m < 10:
        return "三季报"
    else:
        return "年报"

next_type = get_next_earnings_type()
```

> 📌 若需查找公司实际预约日期（非截止日），可用东方财富财经日历辅助：
> `https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_PUBLIC_OP_NEWREPORT&filter=(SECURITY_CODE%3D%22{6位代码}%22)&pageNumber=1&pageSize=5`
> ⚠️ 东方财富返回的预约日有时也是平台默认填充的截止日（尤其在披露季早期），不可直接采信。必须用 Tavily 搜索公司公告二次确认。

**A股法定披露截止日供参考（不可写入 watchlist）**：

| 财报类型 | 法定截止 |
|---|---|
| 一季报 | 4月30日 |
| 半年报 | 8月31日 |
| 三季报 | 10月31日 |
| 年报 | 次年4月30日 |

写入两处：

**a. 公司页 frontmatter**：
```yaml
下一财报日:  # 已确认填日期，未确认留空
下一财报类型: 半年报
```

**b. watchlist JSON（两个字段必须同时存在，类型可填、日期未确认则 null）**：
```json
"next_earnings_date": null,
"next_earnings_type": "半年报"
```
> `next_earnings_date` 为 `null` 时 `next_earnings_type` 可填预期类型（半年报/年报等），方便后续按类型批量检索待确认项。

> ⚠️ 财报发布前 2 周是高风险窗口：不在此窗口内新建仓，已持仓者评估是否需要减仓或加止损。每次财报发布后须更新为下下期。

#### 模块 11：A股特有风险因子（A股/港股必做）

A股市场存在若干在境外成熟市场不常见、但在国内股票投资中必须单独检查的风险点。这些风险往往在短中期内对股价产生直接、可量化的冲击，不能归并到其他模块处理。

---

**11.1 限售股解禁压力**

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

**11.2 大股东 / 管理层减持**

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

**11.3 股权质押风险**

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

**11.4 监管政策突变风险**

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

**11.5 再融资 / 股权摊薄风险**

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

**11.6 商誉减值风险**

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

**11.7 实控人 / 大股东行为风险**

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

**11.8 信息披露质量风险**

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

#### 模块 12：政策顺逆风评估（政治会议加权）

**目的**：将当前生效的政治会议信号纳入估值锚和结论口径，避免在政策明确利好/利空时用纯基本面视角得出反向结论。

---

**12.1 读取生效中的会议页**

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

**12.2 对照利好/利空信号**

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

**12.3 政策加权对结论的影响**

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

> ⚠️ **档位由公司质量决定，与当前股价无关。** 估值偏贵只影响估值报告中的操作判断，不影响公司应属哪个档位。Watchlist 仅保存估值报告的加权合理估值 `target_price` 与 `valuation_certainty`。

| 情形 | 建议 |
|---|---|
| PS ≥ +3 且基本面达 growth 标准 | 可考虑纳入 growth；此前仅研究页观察的公司需重新完成准入判断 |
| PS ≥ +3 且基本面达 core 标准 | 政策加分可作为升 core 的辅助条件之一（不能替代护城河判断） |
| PS ≤ -3 | 不升档；若已在 growth，注明「政策逆风，建议观察不加仓」 |

> ⚠️ **政策加权不能覆盖基本面硬红旗**。出现一票否决型红旗时，无论 PS 多高，结论必须维持「不建议买入」。

---

#### 模块 13：周期位置判断（周期股专属，非周期股跳过）

**目的**：周期股用 PE 判断估值天然失真（景气顶部 PE 最低，底部 PE 最高或亏损），必须先识别周期属性、再定位周期阶段，才能正确锚定买卖区间。

---

**13.1 判断是否为周期股**

满足以下任意一条，进入周期分析：

| 判定维度 | 周期股信号 |
|---|---|
| 行业归属 | 化工、有色金属、钢铁、煤炭、航运、造纸、化纤/涤纶、猪肉/农业、玻璃/水泥、半导体存储（DRAM/NAND）、航空 |
| 盈利波动 | 近 10 年 ROE 标准差 > 5%（利润周期性明显） |
| 主要驱动 | 产品价格（大宗商品/化工品/纺织原料价格）主导利润，而非定价权 |
| 资本开支周期 | 行业供需由大规模扩/去产能驱动，周期约 3-7 年 |

> 如果是**成长型公司兼具周期特征**（如高端制造，成长弹性>周期弹性），标注「弱周期属性」，仍执行本模块但结论权重减半。

---

**13.2 确定周期类型**

| 类型 | 典型行业 | 主要驱动变量 |
|---|---|---|
| 商品价格周期 | 化工、化纤、有色、煤炭、钢铁 | 大宗/化工品现货价格、库存水平 |
| 资本开支周期 | 半导体设备、工程机械、航运 | 行业 Capex 规模、供需缺口 |
| 农业/养殖周期 | 生猪、水产、禽类 | 存栏量、饲料成本、产品价格 |
| 利率/信用周期 | 银行、地产、保险 | 利率、信用扩张、资产质量 |

---

**13.3 评估当前周期位置（五步法）**

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

**13.4 综合判定周期位置**

汇总 5 个维度，判断当前所处阶段：

| 阶段 | 特征 | 操作含义 |
|---|---|---|
| **底部/复苏早期** | PB低分位，ROE触底回升，价格企稳，Capex收缩中 | ✅ 最佳买入窗口；用 PB 锚定而非 PE |
| **复苏中期** | PB中低位，ROE持续改善，价格上行，Capex尚未大扩 | ✅ 仍可买入，但要关注景气持续性验证点 |
| **景气高峰** | PB高分位，ROE历史高位，价格高位，Capex大扩 | ⚠️ 此时 PE 最低但是卖点；严格控制仓位 |
| **收缩/衰退期** | PB高位回落，ROE恶化，价格下行，产能过剩 | ❌ 避免，等待出清信号 |
| **出清期** | PB极低，ROE亏损/极低，弱势企业退出，Capex大幅收缩 | ⏳ 研究关注，等待反转信号 |

---

**13.5 周期位置对 PreBuy 结论和价格区间的影响**

| 周期位置 | 结论口径调整 | 价格区间调整 |
|---|---|---|
| 底部/复苏早期 | 可升一档（叠加 PS 后最多升两档） | 切换为 **PB分位定价**，PB < 1.0x 或历史 20% 分位以下作为绿灯区底 |
| 复苏中期 | 维持，标注「周期顺风」 | PB/PE 混合定价，不调整 |
| 景气高峰 | 强制降一档，标注「周期高位警告」 | 追高区下移 20%（即使 PE 低也不能简单判断便宜） |
| 收缩/衰退期 | 降一档，标注「周期逆风，不适合建仓」 | 追高区下移 30% |
| 出清期 | 维持「继续研究」，等确认反转 | 不设绿灯区，等待 PB 极值 + ROE 触底两个条件同时出现 |

> ⚠️ **景气顶部低PE陷阱**：周期股在盈利最高时 PE 最低，若此时因「便宜」买入，将在利润回落时承受双杀（估值+利润双下行）。**本模块的结论必须优先于模块9的PE估值结论。**

---

**13.6 写入 Watchlist（模块 14 完成后立即执行）**

确认为周期股后，在 `watchlist_core.json` 或 `watchlist_growth.json` 对应条目写入以下两个字段：

```json
"cycle_is_cyclical": true,
"cycle_position": "景气高峰"   // 取值见 watchlist_meta.json 的 cycle_positions
```

规则：
- **非周期股**：省略这两个字段，不写 `false` 占位
- **弱周期（成长弹性 > 周期弹性）**：仍写 `cycle_is_cyclical: true`，并在 `notes` 补注「弱周期，结论权重减半」
- **每次 PreBuy 更新时同步刷新** `cycle_position`，不允许字段值过期停留
- 取值必须与 `watchlist_meta.json` 的 `cycle_positions` 中6个枚举严格一致，不得自造其他表述

---

#### 模块 14：价格走势与买入时机

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

**价格区间与 Watchlist 写入规则**

**① 公司页内的价格区间表**

1. **内容为最终值**：表格数值已叠加所有调整（PS 政策加成、周期位置调整），不展示原始 P80/P50/P20（原始分位可在表格前参考列出）
2. **位置在章节最后**：「近60日走势概述」→「政策加成说明」→「最终价格区间表」（顺序固定）
3. **表格标题**注明调整来源：如「最终价格区间（含PS+3政策顺风加成）」
4. **与估值报告保持一致**：价格带只保留在公司页或估值报告中，不写入 Watchlist

**② 写入 Watchlist JSON**

Watchlist 不写入价格带，只写入估值报告最终加权合理估值和独立认定的估值确定性：

```json
{
  "target_price": 100.0,
  "valuation_certainty": 0.72
}
```

`valuation_certainty` 范围为 `0.00–1.00`，最多两位小数。它只衡量目标价误差范围，不评价公司或管理层质量。认定时必须检查盈利和现金流可预测性、商业模式和资本强度、资产负债表与融资需求、不同估值方法收敛度，以及周期、客户、监管、技术、商品、临床和资本开支等尾部风险。

参考区间：`0.80–0.90` 极高、`0.70–0.79` 较高、`0.60–0.69` 中等、`0.50–0.59` 中低、`0.40–0.49` 较低、`<0.40` 很低。不得因偏好公司而上调；主要假设变化时必须重评。

买入价自动计算但不写入 Watchlist：

```text
buy_price = target_price × (0.68 + 0.14 × valuation_certainty)
```

---

### 第 4 步：固定查这些资料

优先顺序：
1. 法定披露文件：年报、半年报、季报、临时公告
2. 审计报告与财务附注
3. 互动平台、业绩说明会、路演纪要
4. 监管处罚、问询函、司法与工商信用
5. 公司官网产品资料

**数据 API 优先顺序（估值/财务/监管）：**
> 理杏仁（Lixinger）为唯一主力数据源；理杏仁无数据时用东方财富 web_fetch 补充；不再使用 tushare。
> **调用理杏仁 API 时，优先使用 `lixinger-query` skill 中的 `query()` 函数和端点目录（`references/endpoints.md`），不要手工拼 requests.post。若对某端点的 metricsList 合法字段不确定，调用 `fetch_doc(path)` 查询后再调用，避免字段名猜测导致 ValidationError。**

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
> | **所有 `fundamental/*` 接口** | `startDate` / `endDate` | **必须用最近交易日**（如 `2026-04-30`） | 传当天日期若为周末/节假日 → 返回空数据/None，不报错 |
>
> **一句话记法**：`fundamental/*` 系列用数组，其他接口用字符串；candlestick 必须加 type；银行ROE不在理杏仁；日期必须是最近交易日。
>
> **最近交易日辅助函数**（在周末/节假日运行时必用）：
>
> ```python
> from datetime import date, timedelta
>
> def last_trading_day(today=None):
>     """返回最近一个 A 股交易日（简化版：跳过周六日，不处理法定节假日）。
>     若需处理五一/国庆/春节等长假，建议 web_fetch 查询理杏仁最新一条 candlestick 的日期。"""
>     if today is None:
>         today = date.today()
>     d = today
>     while d.weekday() >= 5:   # 5=Saturday, 6=Sunday
>         d -= timedelta(days=1)
>     return d.isoformat()
>
> # 使用示例：
> trade_date = last_trading_day()   # e.g., "2026-04-30"（若今天是周六/日则自动回退）
> ```

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

> 🔴 **Q1 ROE 低估陷阱（批量粗筛必读）**
>
> **问题根源**：批量粗筛时若使用 tushare `fina_indicator` 且 `limit=1`，返回的往往是最新一期季报（如 Q1 2026，`end_date=20260331`）。Q1 季报的 ROE 字段是当期累计净利/期末净资产，约等于全年 ROE 的 1/4，会系统性低估真实盈利能力，造成大量优质公司被误判为 FAIL。
>
> **实测案例（931994 指数 2026-05-01 复查）**：
>
> | 公司 | tushare Q1 ROE | 东方财富 2025年报 ROE | 误判结果 |
> |---|---|---|---|
> | 思源电气(002028) | 3.5% | **18.1%** | FAIL → ✅ PASS（差5.2倍！权重9.44%！） |
> | 东方电缆(603606) | 4.4% | **15.3%** | FAIL → ✅ PASS（差3.5倍） |
> | 三星电气(601567) | 10.8% | **19.6%** | BORDER → ✅ PASS |
>
> **修复规则（粗筛时强制执行）**：
> 1. ROE 必须取**最近年报**（`end_date` 以 `1231` 结尾），不得取 Q1/Q3 季报
> 2. 最近年末日估算：`f"{date.today().year - (1 if date.today().month < 5 else 0)}-12-31"`
> 3. 描述时若用 Q1 ROE，必须注明"Q1单季，年化约 Q1×4"或改用年报 ROE
> 4. 若年报数据未更新（4月前新年报尚未披露），用东方财富 `RPT_LICO_FN_CPD` 中 `QDATE.endswith("Q4")` 识别年报并取 `WEIGHTAVG_ROE`
>
> **东方财富批量获取年报 ROE 代码片段**：
>
> ```python
> import requests
>
> def get_annual_roe(stock_code_6digit):
>     """从东方财富获取最近年报ROE（通过QDATE.endswith('Q4')识别）"""
>     url = (
>         "https://datacenter-web.eastmoney.com/api/data/v1/get"
>         f"?reportName=RPT_LICO_FN_CPD&columns=ALL"
>         f"&filter=(SECURITY_CODE%3D%22{stock_code_6digit}%22)"
>         f"&pageNumber=1&pageSize=5&sortColumns=REPORTDATE&sortTypes=-1"
>     )
>     resp = requests.get(url, headers={"Accept-Encoding": "gzip"})
>     rows = resp.json().get("result", {}).get("data", [])
>     for row in rows:
>         if row.get("QDATE", "").endswith("Q4"):  # 年报识别
>             return float(row.get("WEIGHTAVG_ROE") or 0)
>     return None
> ```

> ⚠️ **理杏仁指数成分股接口额外陷阱（批量指数分析时必读）**
>
> | 接口 | 正确参数 | 错误写法 | 后果 |
> |---|---|---|---|
> | `cn/index/constituent-weightings` | `"startDate": "2026-03-31"` | `"date": "2026-03-31"` | date参数静默返回空数据 |
> | `cn/index/constituent-weightings` | 成分股完整名单**仅季末更新**（3/31、6/30、9/30、12/31） | 使用非季末日期 | 仅返回 top-10，漏掉其余成分股 |
> | `cn/company/fs/non_financial` | 年度营收字段 `y.ps.toi.t` | `a.ps.toi.t` | 找不到字段，返回空 |
> | `cn/company/fs/non_financial` | 营收YOY需手工算：`(rev2025-rev2024)/rev2024` | `y.ps.toi.t.yoy` | 触发MongoDB路径冲突，整批报错 |
> | `cn/company/fundamental/non_financial` | 市值字段 `mc` 单位是**元**，需 `/1e8` 转亿 | 直接使用 mc 值 | 所有公司市值被高估1亿倍 |
> | `cn/company/profile` | 公司名在 `companyName` 字段 | `cnName`（永远为空） | 获取不到公司中文名 |
>
> **ROE 在理杏仁的位置说明**：ROE 既不在 `fundamental/non_financial`，也不在 `fs/non_financial` 的常规字段中。**批量粗筛时，ROE 统一从东方财富 `WEIGHTAVG_ROE` 字段获取年报数据**，不要在理杏仁接口中寻找。

> ⚠️ **PowerShell 调用 Python 脚本编码陷阱**
>
> 在 Windows PowerShell 中运行含 emoji 字符的 Python 脚本时，会触发 GBK 编码错误：
> `UnicodeEncodeError: 'gbk' codec can't encode character '\u274c'`
>
> **解决方案**：脚本中所有输出改用纯 ASCII 替代符号：
> - `❌` → `FAIL`
> - `✅` → `PASS`
> - `⚠️` → `BORDER` 或 `WARN`
>
> 或在脚本顶部强制设置编码（不如直接去掉emoji稳）：
> ```python
> import sys; sys.stdout.reconfigure(encoding='utf-8')
> ```

### 第 5 步：把公司压缩成一句话

输出时必须写一句「公司本质」：
- 它是什么公司
- 真正的利润引擎是什么
- 当前市场为什么愿意给它这个估值

如果一句话说不清，说明研究还没完成。

### 第 6 步：写反证条件

每次都要写至少 3 条「我为什么可能错」。

反证条件通常来自：
- 业绩不兑现
- 现金流恶化
- 并购整合失败
- 行业景气回落
- 热门业务收入占比远低于想象

### 第 7 步：最后才讨论买不买

不要直接把「喜欢这家公司」翻译成「应该马上买」。

综合基本面结论（模块 1–12）和政策加权结果（模块 13），选择最终口径。若模块 13 的 PS 触发了升降档，在结论中明确写出加权理由，不能静默调整。

### 第 8 步：写入公司索引页

每次完成 PreBuy 分析并创建/重建公司页后，必须同步更新 `00-首页/公司索引.md`：

1. **新建公司页**：在对应市场区块（A股/港股/美股）中按拼音/字母顺序插入 `[[公司名]]` 链接，并将总数 +1
2. **重写公司页**（删后重建）：公司名未变则不用重复添加，但检查链接格式是否正确
3. **更新统计行**：同步修改文件顶部的总计数和日期

```
> 共 **XXX** 个公司页（更新于 YYYY-MM-DD）。
```

> ⚠️ 此步骤不可省略。公司索引是知识库唯一的全量导航入口，漏掉会导致新页面游离于索引之外，难以发现。

> ⚠️ **批量 PreBuy 场景（多个子 agent 并行创建公司页）**：子 agent 创建公司页时**不负责**更新公司索引。索引更新必须由**主 Agent 在所有子 agent 完成后统一执行**，逐一将新建公司名加入索引。此规则是防止多个 agent 并发写同一文件导致冲突的必要措施。

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
- 扣非利润或毛利率（**含定价权信号：毛利率趋势稳定/上升 → 定价权尚存；持续下滑 → 需警惕**）
- 经营现金流或营运资金
- 定价权评级（⭐⭐⭐强 / ⭐⭐中 / ⭐弱 / ❌无）及依据

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

必须包含：
- 近期走势概述（近 30/60 日涨跌幅、当前价在区间中的位置）
- 近期重大事件对股价的影响（如财报发布后涨幅）
- 成交量/换手率异常信号
- 政策加成调整说明（PS 取值来自 G 节，周期调整来自 H 节）
- **最终价格区间表**（含所有调整后的最终数值，标题注明调整来源）
- **绝对估值三角验证**（9B.3 的交叉验证表，仅当 9B 与 9A 方向矛盾或一致时有分析价值，正常一带而过）
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
