# 官方资料索引

## A 股

### 1. 法定披露源

- **巨潮资讯网**：https://www.cninfo.com.cn/
  - A 股上市公司公告、年报、半年报、季报、临时公告、审计报告、财务附注
- **上交所**：https://www.sse.com.cn/
  - 信息披露、规则、路演、互动入口（上证 e 互动）
- **深交所**：https://www.szse.cn/
  - 信息披露、规则、路演、互动入口（互动易）

用途：
- 查年报、半年报、季报
- 查并购、担保、回购、减持、股权激励、重大合同
- 查审计报告和财务附注

### 2. 互动平台与路演

- **互动易**（深交所）：https://irm.cninfo.com.cn/
- **上证 e 互动**（上交所）：https://sns.sseinfo.com/
- 交易所路演中心
- 业绩说明会公告和问答

用途：
- 查市场最关心问题的管理层回答
- 验证前后口径是否一致

### 3. 监管与处罚

- **证监会**：http://www.csrc.gov.cn/
  - 行政处罚、市场禁入
- **交易所**：问询函、监管函、关注函（在上交所/深交所官网的监管信息栏目）

用途：
- 判断是否存在信披、财务、治理层面的硬伤

### 4. 工商与司法

- **国家企业信用信息公示系统**：https://www.gsxt.gov.cn/
- **中国执行信息公开网**：http://zxgk.court.gov.cn/
- 必要时补充裁判文书网：https://wenshu.court.gov.cn/

用途：
- 查异常经营、严重违法失信、被执行、股权冻结

### 5. 公司官网

用途：
- 核对产品、解决方案、客户类型、量产口径
- 防止把概念叙事当成真实业务

## 港股

### 1. 法定披露源

- **披露易 HKEXnews**：https://www1.hkexnews.hk/
  - 港股上市公司公告、年报、中报、通函
- **港交所**：https://www.hkex.com.hk/
  - 上市规则、监管信息

用途：
- 查年报、中报、公告
- 查关联交易、股份变动、须予披露交易

### 2. 监管

- **香港证监会 SFC**：https://www.sfc.hk/
  - 执法行动、纪律处分

## 检索策略

1. 优先用公司全称 + 股票代码搜索
2. 同名公司时先确认交易市场（A 股 / 港股）
3. 先查最新年报，再看最新中报/季报，再回看过去 3 年
4. 如果某个数据在披露文件中找不到，标注「待核实」，不要猜测

## 使用顺序

1. 先法定披露
2. 再互动问答
3. 再监管与司法
4. 最后用官网和媒体补充

---

## 理杏仁 Lixinger API

> **优先级：理杏仁 > tushare**（数据质量更高、字段更完整、含历史分位）

- **API总目录**：https://www.lixinger.com/api/open-api/url-doc
- **Token配置**：`.env` 文件中的 `LIXINGER_TOKEN` 字段
- **股票代码格式**：纯数字，不带后缀（`600036`，非 `600036.SH`）

### 常用个股接口

| 接口 | 用途 | URL |
|---|---|---|
| 非金融基本面 | PE/PB历史分位（成长/周期股）| `POST /api/cn/company/fundamental/non_financial` |
| 银行基本面 | PB历史分位（银行股）| `POST /api/cn/company/fundamental/bank` |
| 证券基本面 | PE历史分位（证券股）| `POST /api/cn/company/fundamental/security` |
| 监管措施 | 处罚/工作函/整改通知 | `POST /api/cn/company/measures` |
| 问询函 | 问询函/关注函/监管函（含PDF链接）| `POST /api/cn/company/inquiry` |
| 大股东增减持 | 控股股东/5%以上股东变动 | `POST /api/cn/company/major-shareholders-shares-change` |
| 高管增减持 | 董监高增减持 | `POST /api/cn/company/senior-executive-shares-change` |
| 股权质押 | 质押明细、比例（含未解除过滤）| `POST /api/cn/company/pledge` |
| 分红历史 | 每股股息、分红比例 | `POST /api/cn/company/dividend` |
| 限售解禁热度 | 近期解禁压力初筛信号 | `POST /api/cn/company/hot/elr` |
| K线数据 | 当前价、历史价格 | `POST /api/cn/company/candlestick` |

### 关键字段速查（基本面接口 metricsList）

| 字段 | 含义 |
|---|---|
| `pe_ttm` | 当前PE（滚动）|
| `pe_ttm.y3.cvpos` | PE 3年历史分位（0~1，如0.15=15%分位）|
| `pe_ttm.y3.q2v` / `q5v` / `q8v` | P20 / P50 / P80 对应的PE值 |
| `pb` | 当前PB |
| `pb.y3.cvpos` | PB 3年历史分位 |
| `pb.y3.q2v` / `q5v` / `q8v` | P20 / P50 / P80 对应的PB值 |
| `dyr` | 当前股息率（TTM）|

### Price Bands 计算方法（按公司类型）

| 公司类型 | 分位锚 | 公式 |
|---|---|---|
| 非金融成长/周期 | PE分位 | `bands = [q8v × ratio, q5v × ratio, q2v × ratio]`，`ratio = 当前价/当前PE` |
| 银行/保险 | PB分位 | `bands = [q8v × BPS, q5v × BPS, q2v × BPS]`，`BPS = 当前价/当前PB` |
| 公用事业 | 股息率分位 | 保留股息率反算，理杏仁 `dyr.y3.cvpos` 作验证 |
| PE<0亏损 | PB分位 | `price_bands = null`，改用PB分位描述 |

