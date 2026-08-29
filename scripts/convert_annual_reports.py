"""
财报PDF批量转换脚本 — 使用MinerU将 财报/_Inbox/ 中的PDF转为结构化Markdown。

触发词：转换财报

用法：
  python scripts/convert_annual_reports.py                        # 转换 Inbox 中全部 PDF
  python scripts/convert_annual_reports.py 002415_2026_半年报.pdf  # 只转换指定文件

并发安全（2026-08-29 重构）：
  - 每次运行使用独立的临时目录（_mineru_temp_<pid>_<随机串>），并发运行互不干扰
  - PDF 采用「原子移动」认领：从 Inbox 移入本进程的批次目录（同卷 rename），
    其他并发进程扫描 Inbox 时不会再看到/处理同一文件
  - 中途失败时，未完成归档的 PDF 自动移回 Inbox；临时目录在 finally 中必然清理
  - 注意：GPU 显存仍是真实瓶颈，并发数受 GPU 内存限制（当前 8GB 建议 1-2 个 MinerU 并行）

流程：
  1. 扫描 财报/_Inbox/ 中所有PDF（或指定文件），按页数分批
  2. 每批原子认领 PDF 到本进程临时目录，调用MinerU转换
  3. 提取.md和图片到 财报/[公司名]/
  4. 转换成功的PDF移入 _Inbox/_archived/，失败的移回 _Inbox/
  5. 清理本进程临时目录
"""

import os
import re
import shutil
import subprocess
import sys
import requests
import tempfile
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = VAULT_ROOT / "财报" / "_Inbox"
ARCHIVE_DIR = INBOX_DIR / "_archived"
REPORTS_DIR = VAULT_ROOT / "财报"

MINERU_CMD = "mineru"
MINERU_BACKEND = "pipeline"

# ── 分批控制 ──────────────────────────────────────────
# 单批最大页数。GPU 内存有限，超过此值分批跑以免崩溃。
MAX_PAGES_PER_BATCH = 600

# ── 本进程专属临时目录（并发安全关键）─────────────────
# 每次运行 mkdtemp 生成唯一目录，绝不与其他运行共用/互相删除。
TEMP_DIR = Path(tempfile.mkdtemp(prefix="_mineru_temp_", dir=INBOX_DIR))

# ── 股票代码→公司名 映射缓存 ──────────────────────────
_code_to_name = None


def _load_code_to_name() -> dict[str, str]:
    """从 CNINFO 加载股票代码→中文简称 映射。"""
    global _code_to_name
    if _code_to_name is None:
        _code_to_name = {}
        try:
            r = requests.get(
                "http://www.cninfo.com.cn/new/data/szse_stock.json",
                timeout=30,
            )
            for item in r.json()["stockList"]:
                code = item.get("code", "")
                zwjc = (item.get("zwjc") or "").strip()
                if code and zwjc:
                    _code_to_name[code] = zwjc
        except Exception as e:
            print(f"  [WARN] 无法加载股票列表: {e}")
    return _code_to_name


def _resolve_company_name(raw_name: str) -> str:
    """如果 raw_name 是6位股票代码，反查为公司简称；否则原样返回。"""
    if re.match(r"^\d{6}$", raw_name):
        name_map = _load_code_to_name()
        resolved = name_map.get(raw_name)
        if resolved:
            return resolved
    return raw_name


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

    # 若文件名中公司部分是6位代码，反查为公司简称
    short_name = _resolve_company_name(short_name)

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


def claim_pdfs(pdf_paths: list[Path], dest_dir: Path) -> list[Path]:
    """原子认领：把 PDF 从 Inbox 移动到 dest_dir（同卷 rename，原子操作）。

    移动后其他并发进程的 scan_inbox 不会再看到这些文件，保证单份 PDF 只被转换一次。
    文件已被别的进程抢先移走时静默跳过。
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    claimed = []
    for pdf in pdf_paths:
        if not pdf.exists():
            print(f"  [SKIP] 文件不存在（可能已被其他进程认领/转换）: {pdf.name}")
            continue
        dest = dest_dir / pdf.name
        try:
            shutil.move(str(pdf), str(dest))
            claimed.append(dest)
        except OSError as e:
            print(f"  [WARN] 认领失败（可能被并发进程抢先）: {pdf.name} — {e}")
    return claimed


def run_mineru(input_dir: Path) -> bool:
    """对 input_dir 中的 PDF 批量跑 MinerU，输出写入 TEMP_DIR/out。

    输出目录必须与输入目录分离（MinerU 会递归扫描输入目录中的 PDF，
    若输出内嵌在输入里，会把输出的 _origin.pdf 当成新输入，陷入死循环）。
    多批转换共用 TEMP_DIR/out 是安全的：每个 PDF 的输出目录按文件名隔离，
    organize_outputs 按 expected_names 过滤，只取本批产物。
    """
    output_dir = TEMP_DIR / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(input_dir.glob("*.pdf")))
    pages = sum(count_pdf_pages(p) for p in input_dir.glob("*.pdf"))
    print(f"\n[MINERU] {n} 个文件, ~{pages} 页")
    cmd = [MINERU_CMD, "-p", str(input_dir), "-o", str(output_dir), "-b", MINERU_BACKEND]
    print(f"[CMD] {' '.join(cmd)}")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n[ERROR] MinerU 退出码: {result.returncode}")
        return False
    return True


def organize_outputs(batch_claimed: list[Path], out_root: Path) -> list[dict]:
    """从 MinerU 输出中提取 .md + images 到公司目录。

    MinerU 输出目录结构: <out_root>/<PDF文件名去扩展名>/auto/<stem>.md
    用 rglob 定位而非硬编码路径，兼容不同 MinerU 版本的结构差异。
    """
    if not out_root.exists():
        return []

    md_files = list(out_root.rglob("*.md"))
    expected_names = {p.name for p in batch_claimed}
    results = []

    for md in md_files:
        pdf_dir = md.parent.parent  # auto/ -> PDF名目录
        pdf_name = pdf_dir.name
        if not pdf_name.lower().endswith(".pdf"):
            pdf_name = f"{pdf_name}.pdf"
        if pdf_name not in expected_names:
            continue  # 非本批 PDF 的输出（理论上不会发生，防御）

        info = extract_info(pdf_name)
        if not info:
            print(f"  [WARN] 无法识别公司名: {pdf_name}")
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


def archive_originals(claimed: list[Path]):
    """将转换成功的原始 PDF 移入归档目录（处理重名）。"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for src in claimed:
        if not src.exists():
            continue
        dest = ARCHIVE_DIR / src.name
        if dest.exists():
            dest = ARCHIVE_DIR / f"{src.stem}_{datetime.now().strftime('%H%M%S')}{src.suffix}"
        shutil.move(str(src), str(dest))
        print(f"  [ARCHIVE] {src.name}")


def restore_unclaimed(claimed: list[Path]):
    """把未成功归档的 PDF 移回 Inbox（失败回滚）。"""
    moved = 0
    for src in claimed:
        if not src.exists():
            continue
        dest = INBOX_DIR / src.name
        if dest.exists():
            dest = INBOX_DIR / f"{src.stem}_restored{src.suffix}"
        shutil.move(str(src), str(dest))
        moved += 1
    if moved:
        print(f"  [RESTORE] {moved} 个 PDF 移回 Inbox")


def cleanup():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="财报PDF批量转换（MinerU）")
    parser.add_argument("files", nargs="*", help="指定要转换的PDF文件名（在 _Inbox 下），不指定则转换全部")
    args = parser.parse_args()

    print(f"[START] 财报 PDF 转换 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[INFO] Inbox: {INBOX_DIR}")
    print(f"[INFO] 本次临时目录: {TEMP_DIR.name}")

    if args.files:
        pdf_files = [INBOX_DIR / f for f in args.files]
        missing = [f for f in pdf_files if not f.exists()]
        if missing:
            print(f"[ERROR] 以下文件不存在: {', '.join(f.name for f in missing)}")
            sys.exit(1)
    else:
        pdf_files = scan_inbox()

    batches = split_into_batches(pdf_files)
    if not batches:
        print("[INFO] Inbox 中没有 PDF，无需转换。")
        return

    all_results = []
    all_claimed = []
    archived_names: set[str] = set()
    failed = False

    try:
        for i, batch in enumerate(batches):
            if len(batches) > 1:
                print(f"\n{'='*60}")
                print(f"[BATCH {i+1}/{len(batches)}]")
                print(f"{'='*60}")

            # 原子认领本批 PDF 到本进程临时目录下的批次子目录
            batch_dir = TEMP_DIR / f"batch_{i}"
            claimed = claim_pdfs(batch, batch_dir)
            if not claimed:
                print("  [WARN] 本批无可认领文件，跳过。")
                continue
            all_claimed.extend(claimed)

            if not run_mineru(batch_dir):
                raise RuntimeError(f"第 {i+1} 批 MinerU 转换失败")

            out_root = TEMP_DIR / "out"
            results = organize_outputs(claimed, out_root)
            all_results.extend(results)

            # 仅归档转换成功的 PDF；其余留待 finally 移回 Inbox
            ok_names = {r["original_filename"] for r in results}
            to_archive = [p for p in claimed if p.name in ok_names]
            archive_originals(to_archive)
            archived_names.update(p.name for p in to_archive)
    except Exception as e:
        failed = True
        print(f"\n[ERROR] {e}")
    finally:
        # 未成功归档的 PDF 一律移回 Inbox，避免丢失
        restore_unclaimed([p for p in all_claimed if p.name not in archived_names])
        cleanup()
        print(f"  [CLEAN] 已删除本次临时目录 {TEMP_DIR.name}")

    if failed:
        sys.exit(1)

    if not all_results:
        print("[WARN] 没有成功提取任何文件。")
        sys.exit(1)

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
