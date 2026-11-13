# 每日全三有效池财报发现

每日运行必须先逐家公司核验 `data/watchlist_strategic.json`、`data/watchlist_core.json`、`data/watchlist_growth.json` 的全部有效代码。当前合计189家（A69、HK33、US87），以运行当日文件为准；不含NONE、独立买点清单或指数池。队列非空、今日已更新一家，都不能跳过发现。禁止市场轮转及跨日分批代替每日全池覆盖。

`scripts/earnings_discovery.py` 是台账、证据校验和选择闸门，**不是联网爬虫**。每日Codex执行器必须真实读取官方来源；仅运行plan、加载名单或生成空证据不算核验。可用监管/交易所官方批量或增量接口，但必须覆盖本日全部公司、完整分页，并为每家公司保留发行人身份及原件定位。来源失败、覆盖窗口不明、无可靠最新期次时记录failed，不得写成无新财报。

## 每日执行顺序（供自动化任务直接执行）

1. 检查同项目运行冲突，读取仓库AGENTS.md及本文。使用普通用户、正常审批；禁止读取或复制凭据、调用额度重置、付费接口、交易、推送、发布。
2. 用官方`account/rateLimits/read`取安全额度快照：checked_at、ordinaryUsageAllowed、rateLimits、source=`official account/rateLimits/read ordinary user`。普通模式周剩余必须严格大于20%；不满足或无法确认则停止并如实报告。仅显式登记的重置前额外轮适用文末例外，不改变普通门槛。快照最长有效1小时，长任务重新读取；结束时再次读取。可运行下面只读助手获取该官方返回。
3. 在Vault根目录执行`plan`。取得本日全部未成功公司；首次每日计划必覆盖三有效池全体，即使队列已有pending、in_progress或当天已有完成记录。已有报告更新运行锁时停止，报告冲突，不清锁。
4. 实际逐家公司核验官方最新披露，归档原件或足以复核完整目录/增量窗口的摘录至`data/reviews/earnings-discovery/evidence/YYYY-MM-DD/`。证据须注明真实取得时间、来源、发行人、最新财报与检查窗口。成功与失败均通过`record`记账；完成所有分页/批次及全部公司后才进入更新选择。当天中断重跑plan恢复失败/未查项，次日所有公司重新进入unchecked；历史未知不得补造核验时间。
5. 执行`status`。按A/HK/US输出verified/total、失败及原因、未查及原因；只有全体成功才可声称当日核验完成。完成全部尝试但有failed可进入选择，仍须突出覆盖不完整；资源耗尽导致未查时停止选择并报告未查。
6. 执行`select`，最多取得一家建议候选；它不启动研究或占用更新锁。启动前再查额度及官方期次、最新公司页/Watchlist是否已纳入。串行取得报告更新锁，记录队列in_progress；无每日或每轮数量上限；只要当前官方周剩余严格超过20%，持续按队列优先级逐家公司串行研究与验收。每家公司开始、结束和长研究/审核期间重新查额度；检测到<=20%、查询失败或必要权限不足即保存恢复状态暂停，不再开始下一步。失败重试只针对同一家公司，不切换第二家公司。仅走`skills/company-triplet/SKILL.md`及`docs/three-report-simple-routing.md`：一名Astra作者、一名Sol独审，最多一次集中修正；不得扩研究角色。
7. 按既有验收保留历史报告，成功后串行记录completed及completed_beijing_date/last_completed_beijing_day并释放本次锁。每日结果列公司评分、管理层评分、合理价值、确定性的旧值→新值及主要原因；只引用实际验收报告，未更新不虚构变化。
8. 再读官方额度，汇报覆盖、候选/更新结果、实际阻塞与开始/结束周额度。本次机制验证不执行额外公司报告更新。

```powershell
# 以下均在 E:\ObsidianVaults\ZephyrSpace；北京日期文件由脚本生成
python scripts/read_codex_quota.py --output data/reviews/earnings-discovery-quota.json
python scripts/earnings_discovery.py plan --quota data/reviews/earnings-discovery-quota.json
# 执行器完成真实官方核验，写好证据及逐公司JSON数组后：
python scripts/earnings_discovery.py record --quota data/reviews/earnings-discovery-quota.json --input <本日结果JSON路径>
python scripts/earnings_discovery.py status
python scripts/earnings_discovery.py select --quota data/reviews/earnings-discovery-quota.json
# 结束/长任务重新读取额度
python scripts/read_codex_quota.py --output data/reviews/earnings-discovery-quota.json
```

## 逐公司结果格式

record输入为非空JSON数组。成功字段示例（占位内容须替换为实际核验，不可直接提交）：

```json
{
  "code": "AAA.US",
  "status": "verified_new_report",
  "checked_at": "实际检查时间，ISO8601含时区",
  "method": "official_document_read",
  "comparison_basis": "最新财报相对Watchlist已纳入期次的真实比较依据",
  "latest_report": {
    "period": "FY2026",
    "period_end": "2026-08-31",
    "disclosure_date": "2026-10-10",
    "official_url": "https://官方原件URL"
  },
  "official_sources": [{
    "company_code": "AAA.US",
    "url": "https://官方原件URL",
    "authority": "regulator",
    "locator": "真实发行人标识、完整目录范围及最新报告原件定位",
    "evidence_path": "data/reviews/earnings-discovery/evidence/北京日期/文件名.json",
    "sha256": "实际归档证据SHA256"
  }]
}
```

status只允许verified_new_report、verified_no_update、failed。无新财报必须核实最新期次与当前已纳入期次相同。监管/交易所域名按市场限制；公司IR使用authority=issuer并提供authority_basis说明官方身份核验依据。公开查询参数允许，凭据参数禁止。URL存在与哈希匹配只验证证据绑定，证据真实性、完整分页和官方身份仍由执行器核实，不能用生成的占位文件冒充原件。

增量检查用method=official_incremental_check、since=台账真实last_verified_at；须核验从该锚点至本次检查的连续完整官方披露窗口。没有历史成功锚点必须查完整目录与最新原件。沿用旧最新财报原件仅允许与历史锚点完全一致；有新披露仍须归档新原件。同一期修订须revision_id及比较依据，不反复入队。

失败示例：`{"code":"AAA.US","status":"failed","checked_at":"真实带时区时间","failure":"官方来源超时；未能确认最新期次"}`。没有尝试过的公司保留unchecked，不能批量伪填failed时间。成功后又发生失败的后续尝试另留failed_attempts；本日已经真实完成的成功核验保留，失败尝试须同时汇报。

## 留存、恢复与校验

每天台账为`data/reviews/earnings-discovery/YYYY-MM-DD.json`，含实时池快照哈希、逐公司状态/时间/证据/最新期次/失败及尝试历史。数据采用原子保存和操作系统进程锁。发现成功先落台账、再去重入队；中途队列冲突则停止，重跑plan可恢复。历史六条队列记录及旧scan摘要保持原义，新的daily_discovery字段是当前覆盖真值，清点名单不会改历史扫描为成功。

队列policy设discovery_before_update_selection=true、queue_before_full_scan=false、每日/每日运行数量上限均为null（无限额）、每次select仅建议一家并串行验收。select是只读建议，实际更新者仍须遵守报告锁、逐家公司串行、完成记账及严格>20%额度门槛，不能把反复调用select当作授权多家公司。

验证：`python -m unittest discover -s tests -p test_earnings_discovery.py -v`。测试全部使用临时合成证据，不能当作生产官方覆盖。生产plan验证只表示当前189家进入计划，实际核验数由status如实显示。

2026-10-21较早授权（已被随后持续处理授权取代）：每日最多两家；官方周剩余须严格超过20%。同日后续运行可复用已实际完成并留证的当日全池台账，须重新核对并发、完成数、当前官方额度及候选最新期次；不得将昨日缓存计为今日覆盖。

A股标题解析统一使用 `scripts/earnings_discovery.py:parse_cn_report_title`，同时识别“三季度/第三季度”“一季度/第一季度”。标题仅作发现线索，仍读官方原件确认期末；未识别的较新季度报告须待核，不得静默回退旧报告。

2026-10-21最新用户授权：取消每日及每轮数量上限，周剩余严格超过20%即持续串行处理队列。每完成一家立即保存可通知结果；队列清空、额度触线/读取失败或真实阻塞时停止，不并行研究公司。

## 2026-11-02用户新增：官方周重置前额外轮

本节是对普通20%保留额度的特定例外。默认`--quota-mode normal`，普通调用及普通select仍严格要求周剩>20%；不能把额外轮许可改成全局豁免。最新并行及排序规则继续有效：最多3家公司隔离研究，每家公司原作者、唯一独审、最多一次集中修正；共享发布串行，写前读最新基线，沿`user_priority_order`；不重置已有角色和修正次数。

每个官方Codex周窗口仅可登记一次额外轮。必须以成功的新鲜官方`account/rateLimits/read`确认唯一10080分钟周窗口及有效整数`resetsAt`（Unix秒）；实际启动时刻和快照读取时刻都须在`[resetsAt-4小时, resetsAt)`内。不得猜固定星期、使用旧周reset或以套餐通知代替读取。登记操作不调用额度重置、不买额度、不接触凭据。

`start-extra`在现有发现操作系统写锁内先持久登记`data/reviews/earnings-extra-rounds.json`，以`codex:10080:resetsAt`为周期键，返回唯一run_id。该周期任何重复start均拒绝，包括已结束/失败的额外轮；临时掉线或容量恢复只能携原active run_id续接。登记成功是工作前置条件，不能先研究后补登记。真正的执行和调度由主协调负责，登记本身不启动公司。

示例仅供将来获调度的额外轮执行；**不得在窗口外或本次适配时运行生产登记**：

```powershell
python scripts/read_codex_quota.py --output <本轮官方快照.json>
python scripts/earnings_discovery.py start-extra --quota <本轮官方快照.json> --quota-mode pre-reset-extra
# 将返回run_id持久保存到本轮恢复记录；以下每步均显式传入同一id：
python scripts/earnings_discovery.py check-quota --quota <新鲜官方快照.json> --quota-mode pre-reset-extra --extra-run-id <原run_id>
python scripts/earnings_discovery.py plan --quota <新鲜官方快照.json> --quota-mode pre-reset-extra --extra-run-id <原run_id>
# 真实逐公司官方查询留证后用相同mode/id执行record、status、select。
# status仍只读且不启动研究；不能用status替代check-quota。
python scripts/earnings_discovery.py finish-extra --extra-run-id <原run_id> --stop-reason completed
```

额外模式仅允许不再预留20%，周剩>0且全部服务限制允许时可继续。短窗口或周窗口耗尽、ordinaryUsageAllowed非true、消费控制或服务限额阻断、权限不足、离线、官方读取失败仍必须保存并暂停；不调用额外付费、额度重置或其他服务绕过。不得为消耗额度无意义研究；队列空或真实阻塞即停止。每家始末及长阶段重新官方读取并用相同mode/id检查；每个不可逆/耗时步骤前还须核对实际时钟，不能拿旧check结果跨越reset继续。

例外在官方reset瞬间失效，`pre-reset-extra`检查会拒绝旧run_id。新周只能用新鲜官方快照切回普通门槛>20%，不能自动把旧额外轮迁移到新周。下一官方周也只有进入其新reset前4小时才可另登记一次额外轮。关闭原因可为`completed/blocked/quota_exhausted/reset_elapsed/read_failed`；安全收尾`finish-extra`不要求额度，但不删除历史周期占用记录，也不释放他人研究锁。

当天全池真实披露核验仍是前置：可复用同北京日完整有效台账，不能复用跨日覆盖；失败/未查须如实报告，原覆盖及候选筛选闸门不变。长研究要在安全边界尽早保存证据、模型、正文及审核进度，接近服务耗尽时优先落盘；不把未验收候选写成正式评分或完成。用户旧拒绝、手工任务排除、历史版本留存及权限边界全部保留。

授权来源：公司追踪线程`1793590606.636269`，用户消息`1793609498.008469`：“在额度重置前四个小时进行一次额外的三件套分析。在这次分析中，不受额度限制。可以完全用完。”调度由父线程维护；本机不在本次适配中创建自动化或启动研究。
