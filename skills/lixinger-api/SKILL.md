---
name: lixinger-api
description: >-
  理杏仁 API 数据查询。拉取 A 股非金融公司的 PE/PB/市值/股价等估值数据及历史分位。
  触发词：理杏仁 / lixinger / 查PE / 拉估值 / PE分位 / 批量查估值
---

# 理杏仁 API 数据查询

## 概述

理杏仁 Open API 提供 A 股公司的基本面估值数据、历史分位统计。Token 在 `.env` 的 `LIXINGER_TOKEN`。

API 文档：https://www.lixinger.com/api/open-api/html-doc/cn/company/fundamental/non_financial

## 快速使用

```python
import requests, json, gzip, os
from dotenv import load_dotenv
from datetime import date

load_dotenv()
TOKEN = os.getenv("LIXINGER_TOKEN")
BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    resp = requests.post(
        f"{BASE}/{path}",
        json={**payload, "token": TOKEN},
        headers={"Accept-Encoding": "gzip"},
        timeout=15
    )
    try:
        if resp.headers.get("Content-Encoding") == "gzip":
            return json.loads(gzip.decompress(resp.content))
    except Exception:
        pass
    return resp.json()

# 最近交易日
def last_trade_day():
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()
```

## 核心端点

### `cn/company/fundamental/non_financial` — A 股非金融公司估值

```python
resp = lx_post("cn/company/fundamental/non_financial", {
    "date": "2026-05-29",          # 指定日期（与 startDate 至少传一个）
    "stockCodes": ["300476"],      # 数组，最多 100 只
    "metricsList": [
        "d_pe_ttm",                # PE-TTM(扣非) ★ 首选
        "pe_ttm",                  # PE-TTM
        "pb",                      # PB
        "pb_wo_gw",                # PB(不含商誉)
        "ps_ttm",                  # PS-TTM
        "dyr",                     # 股息率
        "mc",                      # 总市值
        "cmc",                     # 流通市值
        "sp",                      # 股价
        "spc",                     # 涨跌幅
        "shn",                     # 总股东人数
        "ey",                      # 公司收益率(1/PE)
        "d_pe_ttm.y3.cvpos",      # PE扣非 3年 分位点%
        "d_pe_ttm.y3.q2v",        # PE扣非 3年 P20 分位值
        "d_pe_ttm.y3.q5v",        # PE扣非 3年 P50 分位值
        "d_pe_ttm.y3.q8v",        # PE扣非 3年 P80 分位值
        "d_pe_ttm.y5.cvpos",      # PE扣非 5年 分位点%
    ],
})
# resp["data"] 为数组，每项含 stockCode + 各指标值
```

### 重要约束

- `stockCodes` 长度 1 时最多 36 个指标；长度 >1 时最多 48 个指标
- `startDate` + `endDate`（间隔 ≤10 年）或 `date` 二选一
- 仅覆盖 A 股非金融公司，**不支持港股**
- 返回的 `mc` 单位是万元，转债亿需除以 10000（API 返回的已是标准单位，直接使用 `mc` 字段即可）

### 分位统计格式

```
{metricsName}.{granularity}.{statisticsDataType}
```

- **granularity**：`fs`(上市以来) / `y20` / `y10` / `y5` / `y3` / `y1`
- **statisticsDataType**：`cvpos`(分位点%) / `q2v`(P20值) / `q5v`(P50值) / `q8v`(P80值) / `minv` / `maxv` / `avgv`

```python
# 示例：查 PE扣非 TTM + 3年分位点 + 3年 P20/P50/P80 锚点值
metricsList = [
    "d_pe_ttm", "mc", "sp", "pb",
    "d_pe_ttm.y3.cvpos",
    "d_pe_ttm.y3.q2v", "d_pe_ttm.y3.q5v", "d_pe_ttm.y3.q8v",
]
```

## 批量查询模板

```python
CODES = ["300476","002463","002916","600183","300395","301377"]  # 最多 100
NAMES = {
    "300476":"胜宏科技","002463":"沪电股份","002916":"深南电路",
    "600183":"生益科技","300395":"菲利华","301377":"鼎泰高科",
}

resp = lx_post("cn/company/fundamental/non_financial", {
    "date": last_trade_day(),
    "stockCodes": CODES,
    "metricsList": [
        "d_pe_ttm", "pe_ttm", "mc", "sp", "pb", "dyr",
        "d_pe_ttm.y3.cvpos",
        "d_pe_ttm.y3.q2v", "d_pe_ttm.y3.q5v", "d_pe_ttm.y3.q8v",
    ],
})

for item in resp["data"]:
    code = item["stockCode"]
    name = NAMES.get(code, code)
    dpe = item.get("d_pe_ttm")
    mc = item.get("mc")
    cvpos = item.get("d_pe_ttm.y3.cvpos")
    p20 = item.get("d_pe_ttm.y3.q2v")
    p50 = item.get("d_pe_ttm.y3.q5v")
    p80 = item.get("d_pe_ttm.y3.q8v")
    print(f"{name}({code}): PE扣非={dpe:.1f}, 市值={mc/1e8:.0f}亿, 3y分位={cvpos*100:.0f}%, P20/P50/P80={p20:.1f}/{p50:.1f}/{p80:.1f}")
```

## 其他常用端点

### 日 K 线

```python
lx_post("cn/company/candlestick", {
    "stockCode": "300476",
    "startDate": "2026-01-01",
    "endDate": "2026-05-29",
    "adjustmentType": "1",  # 前复权
    "type": "day",
})
```

### 分红记录

```python
lx_post("cn/company/dividend", {
    "stockCode": "300476",
    "startDate": "2022-01-01",
    "endDate": "2026-05-29",
})
```

### 股权质押

```python
lx_post("cn/company/pledge", {
    "stockCode": "300476",
    "startDate": "2023-01-01",
    "endDate": "2026-05-29",
})
```

### 高管增减持

```python
lx_post("cn/company/senior-executive-shares-change", {
    "stockCode": "300476",
    "startDate": "2025-01-01",
    "endDate": "2026-05-29",
})
```

## 现有脚本参考

| 脚本 | 用途 |
|------|------|
| `scripts/collect_data_batch.py` | 理杏仁 + Tushare 联合数据拉取模板 |
| `scripts/recalc_price_bands_lixinger.py` | 用历史 PE 分位重算指数 price_bands |
| `scripts/get_latest_price.py` | 理杏仁 K 线 + 估值快速查询 |
| `scripts/moat_analysis.py` | 护城河分析（含理杏仁数据拉取） |
| `scripts/portfolio_allocation.py` | 组合配置分析（含理杏仁数据拉取） |

## 常见陷阱

1. **港股不支持**：`cn/company/fundamental/non_financial` 只覆盖 A 股，01888/00148 等港股代码返回空数据
2. **PE 扣非 vs PE**：`d_pe_ttm` 扣除非经常性损益，比 `pe_ttm` 更能反映真实经营估值。亏损公司两者均为负值
3. **分位值可能为负**：历史 PE 分位值（q2v/q5v/q8v）在历史亏损期可能为负数，这是正常的，但分位点% (cvpos) 始终有效
4. **批量查询限制**：100 只以内一次调用，超过需分批

## 估值解读辅助规则

拿到 PE 扣非和分位后，按以下框架解读：

| PE扣非 TTM | 3y分位 | 解读 |
|------------|--------|------|
| <0 | 任意 | 亏损，PE 无效，需看 PB 或 PS |
| >0 且 <P20 | <20% | 估值低于历史中枢，可能低估 |
| P20 ~ P50 | 20-50% | 估值偏低，合理区间下沿 |
| P50 ~ P80 | 50-80% | 估值偏高，合理区间上沿 |
| >P80 | >80% | 估值处于历史高位，需高增长支撑 |
| >P80 但绝对值低 | 任意 | 可能处于盈利周期顶部，需警惕均值回归 |
