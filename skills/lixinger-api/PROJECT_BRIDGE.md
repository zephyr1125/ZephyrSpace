# 项目适配层 (ZephyrSpace)

本项目的理杏仁数据访问以 **Python** 为核心，与官方 Skill 的 curl/PowerShell 工作流互补。

## Python 辅助函数

项目级 token 统一在 `.env` 的 `LIXINGER_TOKEN` 管理（本目录 `token.json` 为自动同步副本）。

```python
import requests, json, gzip, os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("LIXINGER_TOKEN")
BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    """理杏仁 API 通用请求封装。自动注入 token，处理 gzip 解压和错误响应。"""
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
```

## 核心端点速查

仅列出本项目高频使用的端点。完整 200+ 端点见 `APIDocs/` 目录。

| 端点 | 用途 |
|------|------|
| `cn/company/fundamental/non_financial` | A 股非金融公司估值 + 历史分位 |
| `cn/company/fs/non_financial` | A 股非金融公司三表 + 财务指标 |
| `cn/company/dividend` | 分红记录 |
| `cn/company/candlestick` | K 线（首选理杏仁前复权 `adjustmentType=3`） |
| `cn/company/pledge` | 股权质押 |
| `cn/company/senior-executive-shares-change` | 高管增减持 |
| `cn/index/fundamental` | 指数 PE/点位/分位 |
| `cn/industry/fundamental/sw_2021` | 申万 2021 行业 PE/分位 |

## 批量估值查询模板

```python
CODES = ["300476","002463","002916"]  # 最多 100
resp = lx_post("cn/company/fundamental/non_financial", {
    "date": "2026-05-29",
    "stockCodes": CODES,
    "metricsList": [
        "d_pe_ttm", "pe_ttm", "pb", "dyr", "mc", "sp",
        "d_pe_ttm.y3.cvpos",
        "d_pe_ttm.y3.q2v", "d_pe_ttm.y3.q5v", "d_pe_ttm.y3.q8v",
    ],
})
for item in resp["data"]:
    code = item["stockCode"]
    dpe = item.get("d_pe_ttm")
    mc = item.get("mc")
    cvpos = item.get("d_pe_ttm.y3.cvpos")
    print(f"{code}: PE扣非={dpe:.1f}, 市值={mc/1e8:.0f}亿, 3y分位={cvpos*100:.0f}%")
```

## 估值解读框架

| PE扣非 TTM | 3y分位 | 解读 |
|------------|--------|------|
| <0 | 任意 | 亏损，PE 无效，需看 PB 或 PS |
| >0 且 <P20 | <20% | 估值低于历史中枢，可能低估 |
| P20 ~ P50 | 20-50% | 估值偏低，合理区间下沿 |
| P50 ~ P80 | 50-80% | 估值偏高，合理区间上沿 |
| >P80 | >80% | 估值处于历史高位，需高增长支撑 |
| >P80 但绝对值低 | 任意 | 可能处于盈利周期顶部，需警惕均值回归 |

## 分位统计指标命名规则

```
{metricsName}.{granularity}.{statisticsDataType}
```

- **granularity**：`fs`(上市以来) / `y20` / `y10` / `y5` / `y3` / `y1`
- **statisticsDataType**：`cvpos`(分位点%) / `q2v`(P20) / `q5v`(P50) / `q8v`(P80) / `minv` / `maxv` / `avgv`

## 常见陷阱

1. **港股不支持**：`cn/company/` 系列只覆盖 A 股，港股需用 `hk/company/` 端点
2. **PE 扣非 vs PE**：`d_pe_ttm` 扣除非经常性损益，比 `pe_ttm` 更能反映真实经营估值
3. **MC 单位**：返回的 `mc` 是万元，转亿需 `/10000`
4. **批量限制**：100 只以内一次调用
5. **金融公司**：银行/证券/保险需用对应 `fundamental/{type}` 端点，不能用 `non_financial`

## 项目脚本

| 脚本 | 用途 |
|------|------|
| `scripts/recalc_price_bands_lixinger.py` | 用历史 PE 分位重算指数 price_bands |
| `scripts/collect_data_batch.py` | 理杏仁 + tushare 联合数据拉取 |
| `scripts/get_latest_price.py` | 理杏仁 K 线 + 估值快速查询 |
| `scripts/moat_analysis.py` | 护城河分析（含理杏仁数据拉取） |
