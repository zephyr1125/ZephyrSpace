# BMI唯一例外定向修复关闭表

- exception_round：1。
- additional_adjudications_remaining：0。
- 依据：`exception-adjudication.md`。
- 最终状态：研究未完成。

## 关闭状态

| ID | 修复与证据 | 状态 |
|---|---|---|
| C06 | FY2025总增量90.105；SmartCover 39.7占44.06%；其余50.405占55.94%；简单基准同比6.098%，明确非严格有机增长；B14/E3=2/公司75不变 | **正文已修，待例外定向复查** |
| C07 | 按S3 Note 2写明2025-11的75m金额授权替换2023-02最多200,000股旧授权；2026-02追加75m；期末剩89.7m；授权、推算使用、实际现金与价值创造边界保留 | **正文已修，待例外定向复查** |
| NEW-P1-01 | 三份冻结稿各仅移除30字节标题注记；恢复后原始字节哈希逐项严格匹配draft-manifest | **作者侧关闭，待哈希复查** |
| C01 | 现有原件可继续建模，但完整NOPAT/FCFF历史桥仍需现金税、营运资金、合同负债与再投资量化；未将156.635冒充正式FCFF | **open P1** |
| C02 | 无合格独立市场锚；未用同源模型替代 | **open P1** |
| C04 | 95.733现金、12公允负债、50压力上限与股数口径已修；现有附注未在本轮形成足以验收的运营现金/融资租赁/SBC完整权益桥 | **open P1** |

## 冻结审计链

| 原路径 | 冻结路径 | 原清单SHA-256 | 注记版SHA-256 | 恢复后实测SHA-256 | 字节 |
|---|---|---|---|---|---:|
| 深度分析/Badger Meter 深度分析 77 2026-09-12.md | data/reviews/bmi-2026-09-12/frozen-author-draft-deep-77.md | A6F063C52D708C9EED9DEB1191B34C031FD835901F00A50A6563AD35A02DF191 | 408F3BE41AF31B240C9CC0FA6E7D3358E71221890DAD1EC2FF67EC82904049AB | A6F063C52D708C9EED9DEB1191B34C031FD835901F00A50A6563AD35A02DF191 | 19817 |
| 管理层档案/Badger Meter 管理层档案 67 2026-09-12.md | data/reviews/bmi-2026-09-12/frozen-author-draft-management-67.md | 41F70114C1A771827CE8AF7D88ED374C4C5C2C99DA7D3B467C7ADACFF24E712D | 7F7DF0715B3212D3FB08E6084C21D0D86A7206189CFB7862BC8809C05D192019 | 41F70114C1A771827CE8AF7D88ED374C4C5C2C99DA7D3B467C7ADACFF24E712D | 14380 |
| 估值分析/Badger Meter 估值分析 2026-09-12.md | data/reviews/bmi-2026-09-12/frozen-author-draft-valuation.md | AEF33DEF78097E9EC1625A7B4E54C74A02698FAC7D6252E9AC6B112959EBC585 | 2E1E212304A5DA2499CC46012FF72B98D0DB48B677E7C92FC4AACF6CEE487A33 | AEF33DEF78097E9EC1625A7B4E54C74A02698FAC7D6252E9AC6B112959EBC585 | 10504 |

说明：迁移时曾加入标题注记，造成唯一30字节变化；本轮严格恢复原标题，`draft-manifest.json`保持不变。

## 参数联动

- 公司质量：75，不变。
- 管理层：73，不变。
- 合计：148。
- 建议：NONE。
- target_price：null。
- valuation_certainty：null。
- mechanical_buy_price：null。
- 反向验证权重：0。

## 停止条件

C01、C02、C04仍为未关闭P1，且已无额外复裁轮次；本run研究未完成，不入库、不写有效价格、不修改公司页/索引/Watchlist、不提交或同步。
