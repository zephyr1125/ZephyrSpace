# 两家公司修复证据包

本目录保存研究过程，不是正式报告目录。正式版本位于Vault的`深度分析/`、`管理层档案/`、`估值分析/`及`01-公司/`。

- `historical-hashes.json`：9份历史报告的保护基线。
- `evidence/`：原件索引、补充来源、行情和治理检索；四份归档PDF的哈希另存`final-primary-hashes.json`。
- `frozen/`：两路初审读取的同一初稿，不代表最终结论。
- `revised-frozen/`：后续送审版本，旧送审稿保留。康臣最终通过版本为`consun-final-v3/`；华明最终通过版本为`huaming-final-v4/`。
- `reviews/`：两路独立预审、初审及定向复验，失败记录保留，不能将初审或失败版本当作最终通过。
- `adjudication/`：匿名候选、逐项裁决、最终参数与计算。
- `source-map-private.json`：仅供主Agent追溯匿名候选，裁决角色不读取。
- `published-*-manifest.json`：实际发布文件与通过复核的冻结字节对应关系。
- `writer/delivery.json`：交付清单，状态字段说明是否仍待裁决；正式结果还需匹配最终裁决、双复验和发布记录。

## 重新计算入口

最终计算按公司分别运行：

```powershell
python -X utf8 data/reviews/consun-huaming-repairs-2026-09-08/writer/consun-recalculate.py
python -X utf8 data/reviews/consun-huaming-repairs-2026-09-08/writer/huaming-recalculate.py
```

每个脚本读取同目录的`*-revision-inputs.json`，输出`*-revision-calculations.json`。**`writer/recalculate.py`、`writer/inputs.json`和`writer/calculations.json`属于首轮草稿，保留用于审计，不是最终重算入口。** 不要执行冻结目录中的脚本覆盖原冻结结果；复核员采用拦截写入或独立计算验证。

`validate_repairs.py`检查历史保护、原件及冻结哈希、六报告篇幅、文件名评分、链接、表头与机械公式；内容正确性另由复验及裁决证明，不能用结构检查替代研究审核。

## 提交边界

作者曾下载的`writer/huaming-2024-annual-temp.pdf`及同名`.txt`未用于最终结论，不属于交付或证据清单，不纳入Git；本机可能仍留有该临时文件。Python字节码缓存同样不提交。

本轮冻结目录及8份正式发布文件通过`.gitattributes`保留原始字节，避免Windows换行转换使验收哈希失效。
