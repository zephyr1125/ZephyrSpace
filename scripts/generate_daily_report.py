# -*- coding: utf-8 -*-
"""生成商业航天日报骨架，并通过 Obsidian CLI 写入 vault。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_obsidian_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["obsidian", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def build_report_content(date: str) -> str:
    lines = [
        "---",
        "类型: 日报",
        f"日期: {date}",
        f"最后更新日期: {date}",
        "---",
        "",
        f"# {date} 商业航天日报",
        "",
        "## 今日重点事件",
        "",
        "- 待补充",
        "",
        "## 公司动态",
        "",
        "### [[01-公司/SpaceX]]",
        "",
        "- 待补充",
        "",
        "### [[01-公司/Rocket Lab]]",
        "",
        "- 待补充",
        "",
        "### [[01-公司/Amazon Project Kuiper]]",
        "",
        "- 待补充",
        "",
        "### [[01-公司/Viasat]]",
        "",
        "- 待补充",
        "",
        "### [[01-公司/蓝箭航天]]",
        "",
        "- 待补充",
        "",
        "### [[01-公司/银河航天]]",
        "",
        "- 待补充",
        "",
        "## 值得复查的信号",
        "",
        "- 待补充",
        "",
        "## 候选补充页面",
        "",
        "- [[02-主题/商业发射]]",
        "- [[02-主题/低轨卫星互联网]]",
        "- [[02-主题/卫星通信]]",
        "",
        "## 参考来源",
        "",
        "- 待补充",
    ]
    return "\\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成商业航天日报")
    parser.add_argument("--vault-name", default="Fan&Zhu")
    parser.add_argument("--date", required=True)
    parser.add_argument("--open-after-create", action="store_true")
    args = parser.parse_args()

    report_path = f"90-日报/{args.date} 商业航天日报.md"
    report_file = Path(report_path)
    if report_file.exists():
        print(f"日报已存在：{report_path}")
        return 0

    create_args = [
        "create",
        f"vault={args.vault_name}",
        f"path={report_path}",
        f"content={build_report_content(args.date)}",
    ]
    if args.open_after_create:
        create_args.append("open")

    created = run_obsidian_command(create_args)
    if created.returncode != 0:
        sys.stderr.write(created.stderr or created.stdout)
        return created.returncode

    if not report_file.exists():
        sys.stderr.write(f"日报创建失败：{report_path}\n")
        return 1

    print(f"已创建日报：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
