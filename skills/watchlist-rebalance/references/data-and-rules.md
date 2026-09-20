# 接入与价格规则

## 本地真源

- Vault：`E:/ObsidianVaults/ZephyrSpace`。
- 成员及参数：`data/watchlist_strategic.json`、`data/watchlist_core.json`、`data/watchlist_growth.json`；辅助规则为 `data/watchlist_meta.json` 与 `data/WATCHLIST_RULES.md`。
- 加载后立即只保留A股及港股；美股完全跳过，不发送行情请求，不汇总其持仓或美元金额。
- Finance：`E:/Work/Python/Finance`。
- 七档公式：`api/services/stock_watchlist.py` 的 `_calculate_price_bands` 与 `_determine_current_band`。
- 累计目标金额对应页面：`app/stock-watchlist/page.tsx` 的“单标的分档建仓规则”。累计市值、人民币口径由用户于 2026-09-16 明确确认。

## 七档边界

设目标价 `T > 0`，估值确定性 `0 <= C <= 1`，机械买入价 `B = T × (0.68 + 0.14 × C)`，现价 `P > 0`；全部须为有限数值且 P、T 同币种、同股数/拆并股口径。

| 档位 | 区间 |
|---|---|
| 高估三档 | P ≥ 1.2T |
| 高估二档 | 1.1T ≤ P < 1.2T |
| 高估一档 | T ≤ P < 1.1T |
| 正常区间 | B ≤ P < T |
| 低估一档 | 0.9B ≤ P < B |
| 低估二档 | 0.8B ≤ P < 0.9B |
| 低估三档 | 0 < P < 0.8B |

边界遵循 Finance 的“从高到低，第一个 P ≥ min”。所以**等于 B 仍为正常，等于 0.9B 为低估一档，等于 0.8B 为低估二档**。分类用未四舍五入值；显示价才取小数位。确定性 80 不得自动当 0.8。

## 行情

优先复用 Finance 现有行情获取能力：`api/services/stock_watchlist.py` 的A股/港股获取函数，或只向 `refresh_price_cache_for_codes` 传入范围内代码。不要调用会连带获取美股的全市场入口。调用前读其现行实现和运行配置，避免启动整个服务或误用含副作用的入口；可用现有只读行情工具补齐。

注意 Finance 可能回退到静态 `current_price` 或磁盘缓存，甚至将缓存装入实时价格映射。单看 `price_source=realtime` 或顶层 `fetched_at` 不能证明逐只证券时效；须获取源报价时间或用独立行情源核对。市场代码必须完整匹配，不能让 A 股与港股短码相互覆盖。

此技能创建时未获取当前行情；使用时必须重新拉取，不引用创建日期的价格。不要使用旧 `scripts/portfolio_allocation.py`：它含硬编码公司与过时配置，并采用复权历史价，不是本技能的数据入口。

## Google Sheets 持仓

用户配置变量：`GOOGLE_APPLICATION_CREDENTIALS`、`SPREADSHEET_ID`，位于 Vault `.env`。在进程内用 dotenv 读取，不输出 `.env` 或凭证全文。如缺配置，再检查 Finance `api/.env` 的同名变量，不拼接不同项目的账号配置。仅允许只读访问。

凭证路径若为相对路径，依次验证配置文件所在目录及 Finance `api/` 下的路径；对应实现为 `api/services/sheets_client.py:get_credentials_path`。不在 skill 内硬编码表 ID 或服务账户文件名。

当前配置采用 `/auth/...json` 形式；在Windows上按Finance现有解析规则去掉开头斜杠，再相对 `E:/Work/Python/Finance/api/` 定位。不要把它误当作磁盘根目录的真实文件路径。

通过 Google Sheets API 的 `spreadsheets.readonly` scope 获取“核算”工作表全部所需行；也可按目标文件精确定位后使用已连接的只读 Sheets 工具。读取表头和结构后再定范围，不能固定 A:O 并假定新列永远不存在。

当前列名映射真源：`api/config/sheets_config.yaml`；标准化逻辑可参考 `api/services/sheets_service.py`。关键列：

| 语义 | 当前表头或候选名 | 注意 |
|---|---|---|
| 代码 | 代码 | 保留前导零，用市场、名称辅助确认证券 |
| 名称 | 名称 / 证券名称 | 不能仅靠简称匹配 |
| 市场 | 宏观市场 / 市场 | 不一定等同结算币种 |
| 状态 | 持仓状态 | 与份额交叉核对 |
| 数量 | 剩余份额 / 股数 | 不等同券商可卖份额 |
| 表中市值 | 当前市值 (万) / 当前市值(万) / 当前市值 / 市值 | 映射名带 wan，但无单位表头仍须验证实际单位及币种 |
| 表中单价 | 当前单价 | 不保证实时，仅供对账 |

Google 返回值选用未格式化数值时也须检查公式错误、单位与代码格式。不能把 `#N/A`、空值和非数字变成零持仓。重复代码可能是分笔持仓，也可能是快照或汇总，先确定行语义再合计。

`scripts/weekly_watchlist_scan.py:load_portfolio` 硬编码来源、只保留 A 股、只输出名单且错误返回空数组，不可直接复用为本技能持仓接口。本技能默认按用户指定的 Google 来源核对A股及港股，不接入其他账户。只在已确认范围内持仓覆盖之后把“查无此证券”视为零持仓。2026-09-16用户已确认核算表为本次全部持仓范围，并明确整个技能不用管美股。

## 本地计算辅助

`python skills/watchlist-rebalance/scripts/calculate.py --price 59 --target 100 --certainty 0.5 --level A_CORE --holding-cny 25000`

输出低估三档、目标 60,000 元、缺口 35,000 元。该缺口不是买入指令；仍需有效估值、更优判定、资金配对和费用核验。辅助程序不访问网络或私人账户。

增加 `--company-score 80 --management-score 85` 可同时输出统一评分及分项贡献。批量分析时可导入 `calculate` 和 `score` 函数；读取 skill 的 `rules.json` 使用同一组权重。金额字段和评分以十进制字符串输出，供下游精确核算，展示时再取小数位。
