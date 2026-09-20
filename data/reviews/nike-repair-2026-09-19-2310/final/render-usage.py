"""把时间窗计量转为中文对照表，不将修复差额解释为完整研究节省率。"""
import json
import sys
from pathlib import Path

audit_path = Path(sys.argv[1])
output = Path(sys.argv[2])
data = json.loads(audit_path.read_text(encoding="utf-8-sig"))
labels = {
    "root": "主任务",
    "triplet_evidence": "Terra 证据",
    "triplet_writer": "Sol 作者",
    "triplet_review_sol": "Sol 独立复核",
    "triplet_review_astra": "Astra 独立复核",
    "triplet_adjudicator": "Astra 裁决",
}


def number(value):
    return "未知" if value is None else f"{value:,}"


def duration(seconds):
    return f"{int(seconds // 60)}分{seconds % 60:.1f}秒"


lines = ["# 耐克闭环修复用量对照", "", "本次为复用旧证据的修复任务；上次为完整三件套启动。范围不同，差额不能称为完整三件套节省比例。", "",
         f"计量真源：`{audit_path.as_posix()}`。本次统计截止：{data['current']['until']}。", "",
         "| 指标 | 上次耐克运行 | 本次修复 | 本次减上次 |", "|---|---:|---:|---:|"]
for key, label in (("input_tokens", "总输入 token"), ("cached_input_tokens", "缓存输入 token"),
                   ("uncached_input_tokens", "非缓存输入 token"), ("output_tokens", "输出 token")):
    lines.append(f"| {label} | {number(data['previous']['totals'][key])} | {number(data['current']['totals'][key])} | {number(data['delta'][key])} |")
lines += [f"| 主任务墙钟耗时 | {duration(data['previous']['wall_clock_seconds'])} | {duration(data['current']['wall_clock_seconds'])} | — |",
          "| 作者修复轮数 | 2 | 2（合并修复＋一次有界例外） | 0 |", ""]
for run_key, title in (("current", "本次各角色"), ("previous", "上次各角色")):
    run = data[run_key]
    lines += [f"## {title}", "", "| 角色 | 总输入 | 缓存输入 | 非缓存输入 | 输出 | 已完成轮次累计墙钟 |", "|---|---:|---:|---:|---:|---:|"]
    for row in run["sessions"]:
        u = row["usage"]
        elapsed = duration(run["wall_clock_seconds"]) + "（窗口）" if row["role"] == "root" else duration(row["completed_duration_ms"] / 1000)
        values = " | ".join(number(u[key]) for key in ("input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens"))
        lines.append(f"| {labels.get(row['role'], row['role'])} | {values} | {elapsed} |")
    lines += [""]
lines += ["## 口径", "", "- 主任务复用同一会话，使用本次起止累计计数之差；旧任务及本次各子会话仅计一次。",
          "- 缓存输入是总输入的子集；非缓存输入＝总输入－缓存输入。推理输出包含在输出中，不重复相加。",
          "- 子任务可并行，其累计轮次耗时不能相加作为总耗时；等待和排队可能计入墙钟。",
          "- 截止快照不包含主任务最后回复及未刷新的用量，因此是该时点可核实用量，不宣称最终回复后的绝对完整计数。",
          "- 模型与推理强度以会话日志记录为准，不视作独立后端认证；未推算美元费用或账户额度。", ""]
output.write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"output": str(output), "sessions": data["current"]["session_count"]}, ensure_ascii=False))
