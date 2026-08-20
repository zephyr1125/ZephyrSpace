
"""compare_runs：Skill A/B 对比（plan §22 / §23）。

用法：
    python -m evals.runners.compare_runs reports/<baseline_run> reports/<candidate_run>

输出：对比表（Markdown + JSON）写入 candidate 运行目录。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.runners import ensure_env


def load_run(run_dir: Path) -> Dict[str, Any]:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    cases: Dict[str, Dict[str, Any]] = {}
    cases_dir = run_dir / "cases"
    if cases_dir.exists():
        for f in sorted(cases_dir.glob("*.json")):
            c = json.loads(f.read_text(encoding="utf-8"))
            cases[c["case_id"]] = c
    return {"summary": summary, "cases": cases}


def _agg(d: Dict[str, Any], key: str) -> Any:
    s = d["summary"]["summary"]
    return s.get(key)


def compare(base: Dict[str, Any], cand: Dict[str, Any]) -> Dict[str, Any]:
    bs, cs = base["summary"]["summary"], cand["summary"]["summary"]
    out: Dict[str, Any] = {
        "weighted_score": {"baseline": bs.get("weighted_score_avg"),
                           "candidate": cs.get("weighted_score_avg")},
        "pass_rate": {"baseline": bs.get("pass_rate"), "candidate": cs.get("pass_rate")},
        "p0": {"baseline": bs.get("p0_total"), "candidate": cs.get("p0_total")},
        "p1": {"baseline": bs.get("p1_total"), "candidate": cs.get("p1_total")},
        "dimensions": {},
        "case_deltas": [],
    }
    for d in ("trigger", "workflow", "structure", "facts", "grounding", "analysis", "calibration", "regression"):
        b = bs.get("mean_scores", {}).get(d)
        c = cs.get("mean_scores", {}).get(d)
        if b is not None or c is not None:
            out["dimensions"][d] = {"baseline": b, "candidate": c}
    # 逐 case 对比
    for cid, ccase in cand["cases"].items():
        bcase = base["cases"].get(cid)
        if bcase:
            out["case_deltas"].append({
                "case_id": cid,
                "baseline_score": bcase.get("weighted_score"),
                "candidate_score": ccase.get("weighted_score"),
                "delta": round((ccase.get("weighted_score") or 0) - (bcase.get("weighted_score") or 0), 2),
                "baseline_status": bcase.get("status"),
                "candidate_status": ccase.get("status"),
            })
    return out


def render_md(meta: Dict[str, Any], cmp: Dict[str, Any]) -> str:
    def fmt(v: Any) -> str:
        if v is None:
            return "N/A"
        if isinstance(v, float):
            return f"{v:.1f}"
        return str(v)

    lines = [
        "# Skill A/B Comparison",
        "",
        f"- Baseline: {meta['baseline']}",
        f"- Candidate: {meta['candidate']}",
        "",
        "| Metric | Baseline | Candidate | Δ |",
        "|---|---:|---:|---:|",
        f"| Weighted Score | {fmt(cmp['weighted_score']['baseline'])} | {fmt(cmp['weighted_score']['candidate'])} | {fmt(_delta(cmp['weighted_score']))} |",
        f"| Pass Rate | {fmt(cmp['pass_rate']['baseline'])} | {fmt(cmp['pass_rate']['candidate'])} | {fmt(_delta(cmp['pass_rate']))} |",
        f"| P0 | {fmt(cmp['p0']['baseline'])} | {fmt(cmp['p0']['candidate'])} | {fmt(_delta(cmp['p0']))} |",
        f"| P1 | {fmt(cmp['p1']['baseline'])} | {fmt(cmp['p1']['candidate'])} | {fmt(_delta(cmp['p1']))} |",
        "",
        "## Dimension Comparison",
        "",
        "| Dimension | Baseline | Candidate | Δ |",
        "|---|---:|---:|---:|",
    ]
    for d, v in cmp["dimensions"].items():
        lines.append(f"| {d} | {fmt(v['baseline'])} | {fmt(v['candidate'])} | {fmt(_delta(v))} |")
    lines += ["", "## Per-Case Deltas", "", "| Case | Baseline | Candidate | Δ |", "|---|---:|---:|---:|"]
    for cd in cmp["case_deltas"]:
        lines.append(f"| {cd['case_id']} | {fmt(cd['baseline_score'])} | {fmt(cd['candidate_score'])} | {fmt(cd['delta'])} |")
    return "\n".join(lines) + "\n"


def _delta(v: Dict[str, Any]) -> Optional[float]:
    b, c = v.get("baseline"), v.get("candidate")
    if b is None or c is None:
        return None
    return round(c - b, 2)


def main(argv: Optional[List[str]] = None) -> int:
    ensure_env()  # 启动即加载项目根 .env（幂等）
    ap = argparse.ArgumentParser(description="Compare two eval runs")
    ap.add_argument("baseline", help="baseline run 目录")
    ap.add_argument("candidate", help="candidate run 目录")
    args = ap.parse_args(argv)
    base_dir, cand_dir = Path(args.baseline), Path(args.candidate)
    base, cand = load_run(base_dir), load_run(cand_dir)
    cmp = compare(base, cand)
    md = render_md({"baseline": args.baseline, "candidate": args.candidate}, cmp)
    (cand_dir / "comparison.md").write_text(md, encoding="utf-8")
    (cand_dir / "comparison.json").write_text(json.dumps(cmp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())