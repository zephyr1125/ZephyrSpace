"""统计本次交付迁移时间窗内主任务及子角色用量。"""
import importlib.util
import json
from pathlib import Path

source = Path("data/reviews/nike-directed-repair-2026-09-20/writer/audit-current.py")
spec = importlib.util.spec_from_file_location("nike_audit", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

result = module.collect(
    Path("C:/Users/zephy/.codex/sessions"),
    "01a0b9c1-dd39-7a43-ad63-635504dc0fa3",
    module.instant("2026-09-20T09:00:14.235Z"),
    module.instant("2026-09-20T09:22:45.1636826Z"),
)
result["limitations"].append("本次是交付迁移回归，不是完整三件套研究；用量不可与完整研究直接比较为节省比例。")
target = Path("data/reviews/nike-delivery-migration-2026-09-20/final/usage-audit-v2.json")
target.parent.mkdir(parents=True, exist_ok=True)
with target.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps(result["totals"], ensure_ascii=False))
