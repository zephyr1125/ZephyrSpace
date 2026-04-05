# -*- coding: utf-8 -*-
"""生成商业航天日报，并通过 Obsidian CLI 写入 vault。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from fetch_industry_news import build_report_content as build_live_report_content  # noqa: E402
from fetch_industry_news import fetch_all_news, load_json, save_cache  # noqa: E402

RULES_PATH = ROOT_DIR / "data" / "classification" / "news_rules.json"


def run_obsidian_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["obsidian", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def build_report_content(date: str) -> str:
    items = fetch_all_news()
    save_cache(date, items)
    rules = load_json(RULES_PATH)
    return build_live_report_content(date, items, rules)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成商业航天日报")
    parser.add_argument("--vault-name", default="ZephyrSpace")
    parser.add_argument("--date", required=True)
    parser.add_argument("--open-after-create", action="store_true")
    parser.add_argument("--overwrite-existing", action="store_true")
    args = parser.parse_args()

    report_path = f"90-日报/{args.date} 商业航天日报.md"
    report_file = Path(report_path)
    if report_file.exists() and not args.overwrite_existing:
        print(f"日报已存在：{report_path}")
        return 0

    report_content = build_report_content(args.date)
    if report_file.exists():
        report_file.write_text(report_content + "\n", encoding="utf-8")
        if args.open_after_create:
            run_obsidian_command(["open", f"vault={args.vault_name}", f"path={report_path}", "newtab"])
        print(f"已覆盖日报：{report_path}")
        return 0

    obsidian_content = report_content.replace("\n", "\\n")
    create_args = [
        "create",
        f"vault={args.vault_name}",
        f"path={report_path}",
        f"content={obsidian_content}",
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
