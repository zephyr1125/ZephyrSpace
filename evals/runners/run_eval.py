
"""run_eval：完整 Eval 管线 CLI（plan §17 / §20 / §30）。

用法：
    # Frozen Eval（默认）：回放既有档案
    python -m evals.runners.run_eval --suite management_archive --run-name v18

    # Live Eval：通过 Claude Code CLI 真实执行 SKILL.md
    python -m evals.runners.run_eval --mode live \
        --skill management-archive/SKILL.md --case management_archive_005 --run-name live_sanan

    # A/B
    python -m evals.runners.compare_runs evals/reports/<baseline> evals/reports/<candidate>

Live 模式参数：
    --mode live|frozen（默认 frozen）
    --cli <path>             claude CLI 路径（默认 "claude"）
    --cli-timeout <s>        Live 运行超时（默认 1800s）
    --model <name>           claude 会话模型
    --skill <SKILL.md 路径>
    --case <case_id>

输出：reports/<YYYY-MM-DD>_<run-name>/{summary.json, summary.md, cases/*.json,
      failures.md, regressions.md, traces/, live/<case_id>/{output.md, trace.json,
      claude_stream.jsonl, trace_sources.jsonl}}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ..graders import analytical_quality, facts, grounding, regression, score_consistency, structure, workflow
from ..graders import trigger as trigger_grader
from ..graders.common import (
    CONFIG, VAULT_ROOT, EvalCase, EvalError, GraderResult, default_reports_dir,
    default_skill_path, gates_pass, load_archive, load_cases, p0_p1_counts, weighted_score,
)
from . import ensure_env
from .run_skill import ClaudeAgentRunner, ReplayRunner, get_runner
from .trace_recorder import load_trace

WEIGHTS = CONFIG["weights"]
GATES = CONFIG["gates"]


# ---------------------------------------------------------------- pipeline

def _run_single(case: EvalCase, skill_text: str, skill_version: str,
                runner: SkillRunner, skill_path: Path, baseline_scores: Dict[str, float],
                trigger_accuracy: float) -> Dict[str, Any]:
    artifacts = runner.run(case, skill_path)
    result: Dict[str, Any] = {
        "case_id": case.id,
        "skill_version": skill_version,
        "status": "PASS",
        "scores": {d: None for d in WEIGHTS},
        "weighted_score": None,
        "gates": {},
        "errors": [],
        "metrics": {},
        "judge_disagreements": [],
        "manual_review": False,
    }
    if artifacts.error or artifacts.output_path is None:
        result["status"] = "SKIP" if CONFIG.get("allow_missing_output") else "FAIL"
        result["errors"].append(EvalError("P1", "WORKFLOW_MISSING_OUTPUT",
                                          f"[{case.id}] {artifacts.error or '无输出文件'}").to_dict())
        return result

    doc = load_archive(artifacts.output_path)
    result["metrics"]["runtime_seconds"] = round(artifacts.runtime_seconds, 2)
    result["output"] = str(artifacts.output_path.relative_to(VAULT_ROOT))
    result["output_markdown"] = artifacts.final_markdown
    result["live"] = {
        "exit_code": artifacts.exit_code,
        "stream_path": str(artifacts.stream_path) if artifacts.stream_path else None,
        "sources_path": str(artifacts.sources_path) if artifacts.sources_path else None,
        "tool_steps": len(artifacts.trace["steps"]) if artifacts.trace else 0,
        "source_steps": sum(1 for s in (artifacts.trace["steps"] if artifacts.trace else []) if s.get("source_level")),
    }

    # --- 各 grader ---
    layers: Dict[str, GraderResult] = {
        "structure": structure.grade(doc, case),
        "facts": facts.grade(doc, case),
        "grounding": grounding.grade(doc, case),
        "analysis": analytical_quality.grade(doc, case),
        "calibration": score_consistency.grade(doc, case, baseline_scores),
        "regression": regression.grade(doc, case),
    }
    if artifacts.trace:
        layers["workflow"] = workflow.grade(artifacts.trace, case)
    else:
        layers["workflow"] = workflow.grade(None, case)

    # trigger：套件级结果注入每个 case
    layers["trigger"] = GraderResult(name="trigger", score=trigger_accuracy,
                                     gates={"trigger_accuracy": trigger_accuracy >= GATES["trigger_accuracy"]["min"]})

    all_errors: List[EvalError] = []
    for name, gr in layers.items():
        result["scores"][name] = gr.score
        result["gates"].update({f"{name}.{k}" if not k.startswith(name) else k: v for k, v in gr.gates.items()})
        all_errors.extend(gr.errors)
        for k, v in gr.metrics.items():
            result["metrics"].setdefault(k, v)
        if name == "analysis":
            dim_scores = gr.details.get("dimension_scores", {})
            result["judge_disagreements"] = [{"dimension": k, "score": v} for k, v in dim_scores.items()]
            result["manual_review"] = bool(gr.metrics.get("manual_review", False))

    # --- 错误与权重 ---
    result["errors"] = [e.to_dict() for e in all_errors]
    p0, p1 = p0_p1_counts(all_errors)
    result["metrics"]["p0"] = p0
    result["metrics"]["p1"] = p1
    result["weighted_score"] = weighted_score(result["scores"])

    # --- Judge 统计（analytical + grounding 层的 LLM judge 结果）---
    # judge_total = grounding claims + analytical 维度 的 LLM judge 调用总数（如 20 + 6 = 26）
    judge_err = sum(gr.metrics.get("judge_error_count", 0) for gr in layers.values())
    judge_total = sum(gr.metrics.get("judge_total", 0) for gr in layers.values())
    judge_retry = sum(gr.metrics.get("judge_retry_count", 0) for gr in layers.values())
    result["metrics"]["judge_error_count"] = judge_err
    result["metrics"]["judge_total"] = judge_total  # 显式覆盖各层 setdefault 的局部值
    result["metrics"]["judge_retry_count"] = judge_retry
    result["metrics"]["judge_profile"] = CONFIG["judge"].get("profile")
    result["metrics"]["judge_model"] = _effective_judge_model()
    if judge_total:
        result["metrics"]["judge_success_rate"] = round((judge_total - judge_err) / judge_total, 4)

    # --- Hard Gates ---
    gate_results = _evaluate_gates(result, layers, trigger_accuracy)
    result["gates"].update(gate_results)
    result["status"] = _decide_status(all(v is True for v in gate_results.values()), judge_err)
    if result["status"] == "INCOMPLETE":
        result["incomplete_reason"] = f"{judge_err} 个 judge 维度失败（analytical/grounding 已剔除错误结果）"
    return result, artifacts


def _effective_judge_model() -> str:
    """返回实际生效的 judge model：profile.model > EVAL_LLM_MODEL > default_model。"""
    jc = CONFIG["judge"]
    if jc.get("backend") != "llm":
        return "null(确定性)"
    prof_name = jc.get("profile")
    if prof_name:
        prof = (jc.get("judge_profiles") or {}).get(prof_name)
        if prof and prof.get("model"):
            return prof["model"]
    return (os.environ.get(jc["llm"].get("model_env", "EVAL_LLM_MODEL"))
            or jc["llm"].get("default_model", "gpt-4o-mini"))


def _decide_status(gates_ok: bool, judge_err: int) -> str:
    """正式 LLM Judge 模式下 judge 有失败 => INCOMPLETE（不进 pass/fail 与平均）；否则按 gates。"""
    if judge_err > 0 and CONFIG["judge"].get("backend") == "llm":
        return "INCOMPLETE"
    return "PASS" if gates_ok else "FAIL"


def _evaluate_gates(result: Dict[str, Any], layers: Dict[str, GraderResult],
                    trigger_accuracy: float) -> Dict[str, bool]:
    g: Dict[str, bool] = {}
    g["p0_errors"] = result["metrics"].get("p0", 0) <= GATES["p0_errors"]["max"]
    # critical fact accuracy
    fa = layers["facts"]
    g["critical_fact_accuracy"] = fa.gates.get("critical_fact_accuracy", True) is not False
    # grounded claim rate
    gr = layers["grounding"]
    g["grounded_claim_rate"] = gr.gates.get("grounded_claim_rate", True) is not False
    # required tool recall
    wf = layers["workflow"]
    g["required_tool_recall"] = wf.gates.get("required_tool_recall", True) is not False
    # trigger accuracy
    g["trigger_accuracy"] = trigger_accuracy >= GATES["trigger_accuracy"]["min"]
    # structure 硬门槛
    st = layers["structure"]
    g["score_math"] = st.gates.get("score_math", False) is True
    g["required_sections"] = st.gates.get("required_sections", False) is True
    g["minimum_lines"] = st.gates.get("minimum_lines", False) is True
    return g


# ---------------------------------------------------------------- trigger layer

def _run_trigger(trigger_cases: List[EvalCase], skill_text: str) -> GraderResult:
    return trigger_grader.grade_cases(trigger_cases, skill_text)


# ---------------------------------------------------------------- summary / report

def _aggregate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    # INCOMPLETE（LLM judge 有失败）不进 pass/fail 与平均分
    evaluated = [r for r in results if r["status"] not in ("SKIP", "INCOMPLETE")]
    passed = [r for r in evaluated if r["status"] == "PASS"]
    scores = {d: [] for d in WEIGHTS}
    for r in evaluated:
        for d, v in r["scores"].items():
            if v is not None:
                scores[d].append(v)
    mean = {d: (round(sum(v) / len(v), 4) if v else None) for d, v in scores.items()}

    p0 = sum(r["metrics"].get("p0", 0) for r in evaluated)
    p1 = sum(r["metrics"].get("p1", 0) for r in evaluated)
    tool_calls = [r["metrics"].get("tool_calls") for r in evaluated if r["metrics"].get("tool_calls") is not None]
    runtimes = [r["metrics"].get("runtime_seconds") for r in evaluated if r["metrics"].get("runtime_seconds") is not None]

    # Judge 统计（含 incomplete 在内的全部 case）
    judge_err = sum(r["metrics"].get("judge_error_count", 0) for r in results)
    judge_total = sum(r["metrics"].get("judge_total", 0) for r in results)
    judge_retry = sum(r["metrics"].get("judge_retry_count", 0) for r in results)
    incomplete = sum(1 for r in results if r["status"] == "INCOMPLETE")

    # 失败聚类
    fail_cats: Counter = Counter()
    for r in evaluated:
        for e in r["errors"]:
            fail_cats[e["category"]] += 1

    return {
        "cases_total": len(evaluated),
        "cases_passed": len(passed),
        "cases_incomplete": incomplete,
        "pass_rate": round(len(passed) / len(evaluated), 4) if evaluated else 0.0,
        "mean_scores": mean,
        "p0_total": p0,
        "p1_total": p1,
        "judge_error_count": judge_err,
        "judge_retry_count": judge_retry,
        "judge_success_rate": round((judge_total - judge_err) / judge_total, 4) if judge_total else None,
        "avg_tool_calls": round(sum(tool_calls) / len(tool_calls), 2) if tool_calls else None,
        "avg_runtime_seconds": round(sum(runtimes) / len(runtimes), 2) if runtimes else None,
        "top_failure_categories": fail_cats.most_common(10),
    }


def _write_report(run_dir: Path, meta: Dict[str, Any], summary: Dict[str, Any],
                  results: List[Dict[str, Any]], trigger_res: GraderResult,
                  traces: Dict[str, Dict[str, Any]], pairwise: Dict[str, Any]) -> Dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    cases_dir = run_dir / "cases"
    cases_dir.mkdir(exist_ok=True)
    traces_dir = run_dir / "traces"
    traces_dir.mkdir(exist_ok=True)

    for r in results:
        (cases_dir / (r["case_id"] + ".json")).write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    for cid, t in traces.items():
        (traces_dir / (cid + ".json")).write_text(
            json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")

    overall = {
        "meta": meta,
        "summary": summary,
        "trigger": {
            "accuracy": trigger_res.score,
            "metrics": trigger_res.metrics,
            "gates": trigger_res.gates,
        },
        "pairwise": pairwise,
    }
    summary_json_path = run_dir / "summary.json"
    summary_json_path.write_text(json.dumps(overall, ensure_ascii=False, indent=2), encoding="utf-8")

    (run_dir / "summary.md").write_text(_summary_md(meta, summary, trigger_res, pairwise), encoding="utf-8")
    (run_dir / "failures.md").write_text(_failures_md(results), encoding="utf-8")
    (run_dir / "regressions.md").write_text(_regressions_md(results), encoding="utf-8")
    return overall


def _summary_md(meta: Dict[str, Any], summary: Dict[str, Any], trigger_res: GraderResult,
                pairwise: Dict[str, Any]) -> str:
    lines = [
        "# Eval Run Summary",
        "",
        f"- Skill Version: {meta['skill_version']}",
        f"- Git Commit: {meta['git_commit']}",
        f"- Model: {meta['model']}",
        f"- Judge Model: {meta['judge_model']}",
        f"- Dataset Version: {meta['dataset_version']}",
        f"- Cases: {summary['cases_total']}",
        f"- Pass Rate: {summary['pass_rate']:.1%}",
        f"- Weighted Score: {summary.get('weighted_score_avg')}",
        f"- P0 Count: {summary['p0_total']}",
        f"- P1 Count: {summary['p1_total']}",
        f"- Trigger Accuracy: {trigger_res.score if trigger_res.score is not None else 'N/A'}",
        f"- Critical Fact Accuracy: {summary['mean_scores'].get('facts')}",
        f"- Grounded Claim Rate: {summary['mean_scores'].get('grounding')}",
        f"- Required Tool Recall: {summary['mean_scores'].get('workflow')}",
        f"- Judge Profile: {meta.get('judge_profile') or '(未指定)'}",
        f"- Judge Success Rate: {summary.get('judge_success_rate')}",
        f"- Judge Error Count: {summary.get('judge_error_count')}",
        f"- Judge Retry Count: {summary.get('judge_retry_count')}",
        f"- Incomplete Cases: {summary.get('cases_incomplete')}",
        f"- Average Tool Calls: {summary.get('avg_tool_calls')}",
        f"- Average Runtime (s): {summary.get('avg_runtime_seconds')}",
        "",
        "## Dimension Mean Scores",
        "",
        "| Dimension | Score |",
        "|---|---|",
    ]
    for d, s in summary["mean_scores"].items():
        lines.append(f"| {d} | {s if s is not None else 'N/A'} |")
    lines += ["", "## Top Failure Categories", "", "| Failure | Count |", "|---|---|"]
    for cat, cnt in summary["top_failure_categories"]:
        lines.append(f"| {cat} | {cnt} |")
    if pairwise.get("pairs"):
        lines += ["", "## Pairwise Calibration", ""]
        for p in pairwise["pairs"]:
            lines.append(f"- {p.get('result', '?')} : {p.get('a')} vs {p.get('b')}")
    return "\n".join(lines) + "\n"


def _failures_md(results: List[Dict[str, Any]]) -> str:
    lines = ["# Failures", ""]
    any_fail = False
    for r in results:
        errs = r.get("errors", [])
        if not errs:
            continue
        any_fail = True
        lines.append(f"## {r['case_id']} ({r['status']})")
        for e in errs:
            lines.append(f"- [{e['severity']}] {e['category']}: {e['message']}")
        lines.append("")
    if not any_fail:
        lines.append("无错误。")
    return "\n".join(lines) + "\n"


def _regressions_md(results: List[Dict[str, Any]]) -> str:
    lines = ["# Regression (M1-M8)", ""]
    for r in results:
        gates = r.get("gates", {})
        metrics = r.get("metrics", {})
        p = metrics.get("regression_pass")
        t = metrics.get("regression_total")
        passed = gates.get("regression_stability") is True or (p is not None and t is not None and p == t)
        status = "PASS" if passed else "FAIL"
        detail = f" (M-pass {p}/{t})" if p is not None else ""
        lines.append(f"- {r['case_id']}: {status}{detail}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="management-archive Skill Eval Runner")
    ap.add_argument("--suite", default=CONFIG["suite"])
    ap.add_argument("--run-name", default="local")
    ap.add_argument("--skill", default=str(default_skill_path()))
    ap.add_argument("--skill-version", default=None)
    ap.add_argument("--cases", default=None, help="逗号分隔的 case id 子集")
    ap.add_argument("--case", dest="case", default=None, help="单个 case id（等价于 --cases <id>）")
    ap.add_argument("--output-dir", default=None, help="档案输出目录（相对 vault 根）")
    ap.add_argument("--runs-dir", default=None, help="回放目录（含 <case_id>/output.md + trace.json）")
    ap.add_argument("--baseline", default=None, help="baseline summary.json 路径")
    ap.add_argument("--judge", default=None, choices=["null", "llm"])
    ap.add_argument("--judge-profile", default=None, choices=["fast", "release"],
                    help="Judge 档位：fast=qwen-flash / release=qwen3.5-plus（model/timeout/retry 来自 profile）")
    ap.add_argument("--allow-missing-output", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mode", default="frozen", choices=["frozen", "live"])
    ap.add_argument("--cli", default="claude")
    ap.add_argument("--cli-timeout", type=int, default=1800)
    ap.add_argument("--model", default=None)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ensure_env()  # 启动即加载项目根 .env（幂等；不覆盖已有环境变量）
    args = build_parser().parse_args(argv)

    if args.judge:
        CONFIG["judge"]["backend"] = args.judge
    if args.judge_profile:
        CONFIG["judge"]["profile"] = args.judge_profile
    CONFIG["allow_missing_output"] = args.allow_missing_output

    skill_path = Path(args.skill)
    if not skill_path.is_absolute():
        skill_path = VAULT_ROOT / skill_path
    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""
    skill_version = args.skill_version or _detect_skill_version(skill_path)

    # 加载 cases
    cases = load_cases()
    company_cases = [c for c in cases.values() if c.id.startswith("management_archive_")]
    trigger_cases = [c for c in cases.values() if c.id.startswith("trigger_")]
    if args.case:
        args.cases = args.case
    if args.cases:
        wanted = set(args.cases.split(","))
        company_cases = [c for c in company_cases if c.id in wanted]
        trigger_cases = [c for c in trigger_cases if c.id in wanted]

    # run 目录（live workspace 放其下）
    run_dir = default_reports_dir() / (datetime.now().strftime("%Y-%m-%d") + "_" + args.run_name)

    # runner（frozen / live）
    if args.mode == "live":
        live_dir = run_dir / "live"
        live_dir.mkdir(parents=True, exist_ok=True)
        runner = ClaudeAgentRunner(
            cli=args.cli, runs_dir=live_dir, timeout_s=args.cli_timeout, model=args.model,
        )
    else:
        runner = ReplayRunner(
            output_dir=Path(args.output_dir) if args.output_dir else None,
            runs_dir=Path(args.runs_dir) if args.runs_dir else None,
        )

    # trigger layer
    trigger_res = _run_trigger(trigger_cases, skill_text) if trigger_cases else GraderResult(name="trigger", score=None)

    # baseline scores
    baseline_scores: Dict[str, float] = {}
    if args.baseline:
        bp = Path(args.baseline)
        if not bp.is_absolute():
            bp = VAULT_ROOT / bp
        if bp.exists():
            bl = json.loads(bp.read_text(encoding="utf-8"))
            bl_dir = bp.parent / "cases"
            if bl_dir.exists():
                for cf in bl_dir.glob("*.json"):
                    cr = json.loads(cf.read_text(encoding="utf-8"))
                    if cr.get("weighted_score") is not None:
                        baseline_scores[cr["case_id"]] = cr["weighted_score"]

    results: List[Dict[str, Any]] = []
    traces: Dict[str, Dict[str, Any]] = {}
    for case in company_cases:
        r, art = _run_single(case, skill_text, skill_version, runner, skill_path,
                             baseline_scores,
                             trigger_res.score if trigger_res.score is not None else 1.0)
        results.append(r)
        if art.trace:
            traces[case.id] = art.trace
        if art.output_path and art.final_markdown and args.mode == "live":
            # Live 产物归档：output.md + trace.json 保留在 live/<case_id>/
            wscase = run_dir / "live" / case.id
            wscase.mkdir(parents=True, exist_ok=True)
            (wscase / "output.md").write_text(art.final_markdown, encoding="utf-8")
            if art.trace:
                (wscase / "trace.json").write_text(
                    json.dumps(art.trace, ensure_ascii=False, indent=2), encoding="utf-8")

    # pairwise calibration（config 中 pairs 或 golden 顺序）
    pairwise = _pairwise(results)

    # suite 级加权
    mean = {d: (round(sum(x["scores"][d] for x in results if x["scores"][d] is not None) / max(1, sum(1 for x in results if x["scores"][d] is not None)), 4) if any(x["scores"][d] is not None for x in results) else None) for d in WEIGHTS}
    suite_weighted = weighted_score(mean)

    summary = _aggregate(results)
    summary["weighted_score_avg"] = suite_weighted

    meta = {
        "skill_version": skill_version,
        "git_commit": _git_commit(),
        "model": args.model or ("claude-cli" if args.mode == "live" else "n/a (replay)"),
        "mode": args.mode,
        "judge_model": _effective_judge_model(),
        "judge_profile": CONFIG["judge"].get("profile"),
        "dataset_version": CONFIG["dataset_version"],
        "run_name": args.run_name,
        "suite": args.suite,
        "run_at": datetime.now().isoformat(timespec="seconds"),
    }

    if args.dry_run:
        print(json.dumps({"meta": meta, "summary": summary, "trigger": trigger_res.metrics}, ensure_ascii=False, indent=2))
        return 0
    _write_report(run_dir, meta, summary, results, trigger_res, traces, pairwise)
    print(f"report -> {run_dir}")
    print(json.dumps({"pass_rate": summary["pass_rate"], "weighted_score": suite_weighted,
                      "p0": summary["p0_total"], "p1": summary["p1_total"]}, ensure_ascii=False))
    return 0


def _pairwise(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = {r["case_id"]: r["weighted_score"] for r in results if r["weighted_score"] is not None}
    pairs_cfg = CONFIG["calibration"].get("pairs", [])
    out: Dict[str, Any] = {"pairs": [], "pass": True}
    for pr in pairs_cfg:
        a, b = pr.get("a"), pr.get("b")
        if a in total and b in total:
            ok = total[a] > total[b]
            out["pairs"].append({"a": a, "b": b, "score_a": total[a], "score_b": total[b],
                                 "expected": pr.get("expected", "gt"), "result": "PASS" if ok else "FAIL"})
            if not ok:
                out["pass"] = False
    return out


def _detect_skill_version(skill_path: Path) -> str:
    try:
        import subprocess
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", str(skill_path)],
            capture_output=True, text=True, cwd=str(VAULT_ROOT))
        return "v-" + (out.stdout.strip() or "local")
    except Exception:
        return "v-local"


def _git_commit() -> str:
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, cwd=str(VAULT_ROOT))
        return out.stdout.strip() or "n/a"
    except Exception:
        return "n/a"


if __name__ == "__main__":
    sys.exit(main())