"""
财报PDF批量转换脚本 — 使用MinerU将 财报/_Inbox/ 中的PDF转为结构化Markdown。

触发词：转换财报

流程：
  1. 扫描 财报/_Inbox/ 中所有PDF
  2. 复制到临时目录，调用MinerU批量转换
  3. 提取.md和图片到 财报/[公司名]/
  4. 原始PDF移入 _Inbox/_archived/
  5. 清理MinerU中间产物
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = VAULT_ROOT / "财报" / "_Inbox"
ARCHIVE_DIR = INBOX_DIR / "_archived"
REPORTS_DIR = VAULT_ROOT / "财报"
TEMP_DIR = INBOX_DIR / "_mineru_temp"

MINERU_CMD = "mineru"
MINERU_BACKEND = "pipeline"

# ── 分批控制 ──────────────────────────────────────────
# 单批最大页数。GPU 内存有限，超过此值分批跑以免崩溃。
MAX_PAGES_PER_BATCH = 600


def extract_info(filename: str) -> dict | None:
    """从PDF文件名提取公司简称、年份、报告类型。

    支持两种命名格式：
      - SSE标准: "贵州茅台：贵州茅台酒股份有限公司2024年年度报告.pdf"
      - 简式:     "贵州茅台_2024_年度报告.pdf"
    """
    name = Path(filename).stem

    short_name, rest = None, name

    # 格式1: "贵州茅台：xxx2024年年度报告.pdf"
    if "：" in name or ":" in name:
        parts = re.split(r"[：:]", name, maxsplit=1)
        short_name = parts[0].strip()
        rest = parts[1].strip()
    # 格式2: "公司_年份_类型.pdf" (download_reports.py 输出格式)
    elif re.match(r'^(.+)_(\d{4})_(.+)\.pdf$', filename, re.IGNORECASE):
        # filename has .pdf extension, name does not
        m = re.match(r'^(.+)_(\d{4})_(.+)', name)
        if m:
            short_name = m.group(1).strip()
            rest = f"{m.group(2)}年{m.group(3)}"

    if not short_name:
        print(f"  [WARN] 无法识别公司名: {filename}")
        return None

    year_match = re.search(r"(\d{4})年", rest) if rest else re.search(r"(\d{4})", name)
    year = year_match.group(1) if year_match else "unknown"

    if rest:
        if "半年度报告" in rest or "半年报" in rest:
            rtype = "半年度报告"
        elif "年度报告" in rest or "年报" in rest:
            rtype = "年度报告"
        elif "第一季度" in rest or "一季报" in rest:
            rtype = "第一季度报告"
        elif "第三季度" in rest or "三季报" in rest:
            rtype = "第三季度报告"
        else:
            rtype = "年报"
    else:
        rtype = "年报"

    return {
        "short_name": short_name,
        "year": year,
        "report_type": rtype,
        "original_filename": filename,
    }


def scan_inbox() -> list[Path]:
    if not INBOX_DIR.exists():
        print(f"[ERROR] Inbox 目录不存在: {INBOX_DIR}")
        sys.exit(1)
    pdfs = sorted(INBOX_DIR.glob("*.pdf"))
    if not pdfs:
        print("[INFO] Inbox 中没有 PDF，无需转换。")
        sys.exit(0)
    return pdfs


def count_pdf_pages(pdf_path: Path) -> int:
    """读取 PDF 页数（跨平台：优先 PyPDF2，兜底 pikepdf）"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        pass
    try:
        import pikepdf
        with pikepdf.open(str(pdf_path)) as pdf:
            return len(pdf.pages)
    except Exception:
        print(f"  [WARN] 无法读取页数: {pdf_path.name}，按 150 页估算")
        return 150


def split_into_batches(pdf_paths: list[Path]) -> list[list[Path]]:
    """将 PDF 列表按总页数分组，每组不超过 MAX_PAGES_PER_BATCH 页。"""
    pdf_info = [(p, count_pdf_pages(p)) for p in pdf_paths]
    total_pages = sum(n for _, n in pdf_info)
    print(f"\n[SCAN] {len(pdf_paths)} 个 PDF，共 {total_pages} 页")

    batches = []
    current_batch = []
    current_pages = 0
    for pdf, pages in pdf_info:
        if current_pages + pages > MAX_PAGES_PER_BATCH and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_pages = 0
        current_batch.append(pdf)
        current_pages += pages
    if current_batch:
        batches.append(current_batch)

    if len(batches) > 1:
        print(f"[BATCH] 分为 {len(batches)} 批: {', '.join(f'{len(b)}文件/{sum(count_pdf_pages(p) for p in b)}页' for b in batches)}")
    return batches


def run_mineru(pdf_paths: list[Path]) -> bool:
    """将 PDF 复制到临时目录，一次性批量跑 MinerU。"""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    temp_input = TEMP_DIR / "_input"
    temp_input.mkdir(parents=True, exist_ok=True)

    for pdf in pdf_paths:
        shutil.copy2(pdf, temp_input / pdf.name)

    print(f"\n[MINERU] {len(pdf_paths)} 个文件, ~{sum(count_pdf_pages(p) for p in pdf_paths)} 页")
    cmd = [MINERU_CMD, "-p", str(temp_input), "-o", str(TEMP_DIR), "-b", MINERU_BACKEND]
    print(f"[CMD] {' '.join(cmd)}")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n[ERROR] MinerU 退出码: {result.returncode}")
        return False
    return True


def organize_outputs() -> list[dict]:
    """扫描 MinerU 输出，提取 .md + images 到公司目录。"""
    md_files = list(TEMP_DIR.rglob("*.md"))
    results = []

    for md in md_files:
        parent_dir = md.parent.parent  # auto/ -> PDF名目录
        pdf_name = parent_dir.name
        info = extract_info(pdf_name + ".pdf")
        if not info:
            continue

        company_dir = REPORTS_DIR / info["short_name"]
        company_dir.mkdir(parents=True, exist_ok=True)

        clean = f"{info['short_name']}{info['year']}{info['report_type']}.md"
        dest_md = company_dir / clean
        shutil.copy2(md, dest_md)
        print(f"  [MD]  {clean}")

        # 复制图片目录（如果存在）
        img_src = md.parent / "images"
        if img_src.is_dir():
            img_dest = company_dir / f"{Path(clean).stem}_images"
            if img_dest.exists():
                shutil.rmtree(img_dest)
            shutil.copytree(img_src, img_dest)
            img_count = len(list(img_dest.iterdir()))
            print(f"  [IMG] {img_count} 张图片 -> {img_dest.name}/")

        results.append({**info, "dest": str(dest_md), "company_dir": str(company_dir)})

    return results


def archive_originals(results: list[dict]):
    """将已转换的原始 PDF 移入归档目录。"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for r in results:
        src = INBOX_DIR / r["original_filename"]
        if src.exists():
            shutil.move(str(src), str(ARCHIVE_DIR / r["original_filename"]))
            print(f"  [ARCHIVE] {r['original_filename']}")


def cleanup():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        print(f"  [CLEAN] 已删除临时目录")


def main():
    print(f"[START] 年报 PDF 转换 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[INFO] Inbox: {INBOX_DIR}")

    pdf_files = scan_inbox()
    for f in pdf_files:
        print(f"  - {f.name} ({count_pdf_pages(f)} 页)")

    batches = split_into_batches(pdf_files)

    all_results = []
    for i, batch in enumerate(batches):
        if len(batches) > 1:
            print(f"\n{'='*60}")
            print(f"[BATCH {i+1}/{len(batches)}]")
            print(f"{'='*60}")

        if not run_mineru(batch):
            if i < len(batches) - 1:
                print(f"[WARN] 第 {i+1} 批失败，继续下一批...")
                continue
            else:
                sys.exit(1)

        results = organize_outputs()
        all_results.extend(results)

        # 清理临时目录，准备下一批
        if i < len(batches) - 1:
            if TEMP_DIR.exists():
                shutil.rmtree(TEMP_DIR)

    if not all_results:
        print("[WARN] 没有成功提取任何文件。")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"[ARCHIVE] 归档原始 PDF...")
    print(f"{'='*60}")
    archive_originals(all_results)

    print(f"\n{'='*60}")
    print(f"[CLEANUP]")
    print(f"{'='*60}")
    cleanup()

    # 汇总
    print(f"\n{'='*60}")
    print(f"[DONE] {len(all_results)} 份报告转换完成")
    print(f"{'='*60}")
    by_company = {}
    for r in all_results:
        by_company.setdefault(r["short_name"], []).append(r)
    for name, reports in by_company.items():
        print(f"\n  {name}/")
        for r in reports:
            print(f"    {r['year']} {r['report_type']}")

    print(f"\n[INFO] 原始 PDF 归档: {ARCHIVE_DIR}")
    print(f"[INFO] 下一步: review 输出质量，然后 git add && git commit")


if __name__ == "__main__":
    main()
