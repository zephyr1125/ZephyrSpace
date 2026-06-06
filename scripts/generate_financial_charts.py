"""
财务全景图生成工具
================
为深度公司分析报告生成 2x3 六面板"盈利与成长能力全景图"PNG。

用法:
    # CLI 独立使用
    python scripts/generate_financial_charts.py 600519 "贵州茅台"

    # 指定输出路径
    python scripts/generate_financial_charts.py 600519 "贵州茅台" -o "深度分析/茅台_图表.png"

    # 代码调用
    from scripts.generate_financial_charts import generate_profitability_growth_chart
    from scripts.cninfo_api import CninfoClient

    client = CninfoClient()
    df = client.financial_multi_year("600519", years=[2019,2020,2021,2022,2023,2024])
    path = generate_profitability_growth_chart(df, "贵州茅台", "600519",
                "深度分析/贵州茅台_盈利成长能力.png")
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import os
import argparse
import warnings
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# 字体配置
# ══════════════════════════════════════════════════════════════

def _setup_chinese_font():
    """配置中文字体，返回实际使用的字体名。"""
    preferred = ["Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei",
                 "PingFang SC", "Noto Sans CJK SC", "DejaVu Sans"]
    available = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    for font in preferred:
        if font in available:
            matplotlib.rcParams["font.sans-serif"] = [font, "DejaVu Sans"]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return font
    # Fallback: suppress warnings and continue
    warnings.warn("未找到中文字体，图表中文可能显示为方框。请安装 Microsoft YaHei 或 SimHei。")
    matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    return "DejaVu Sans"

_FONT_NAME = _setup_chinese_font()

# ══════════════════════════════════════════════════════════════
# 配色方案
# ══════════════════════════════════════════════════════════════

COLORS = {
    "roe":           "#1f3a5f",  # 深海军蓝
    "gross_margin":  "#2d8659",  # 森林绿
    "net_margin":    "#d4a017",  # 暖琥珀
    "rev_growth":    "#4e79a7",  # 钢蓝
    "profit_growth": "#e15759",  # 珊瑚红
    "revenue":       "#76b7b2",  # 浅钢蓝
    "net_profit":    "#edc948",  # 暖金
    "ocf_healthy":   "#59a14f",  # 翡翠绿
    "ocf_warning":   "#f28e2b",  # 琥珀橙
    "ocf_danger":    "#e15759",  # 红
    "ocf":           "#4e79a7",  # 钢蓝
    "icf":           "#e15759",  # 珊瑚红
    "fcf":           "#79706e",  # 紫灰
    "dupont_nm":     "#1f3a5f",  # 深蓝
    "dupont_at":     "#2d8659",  # 绿
    "dupont_em":     "#d4a017",  # 琥珀
    "grid":          "#e0e0e0",
    "bg":            "#ffffff",
    "title":         "#1f3a5f",
    "threshold":     "#e15759",
}

# ══════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════

def _to_yi(series):
    """元 -> 亿元"""
    return pd.to_numeric(series, errors="coerce") / 1e8

def _safe_float(series):
    return pd.to_numeric(series, errors="coerce")

REQUIRED_COLUMNS = [
    "报告年度",
    "净资产收益率(%)",           # F014N
    "毛利率(%)",                 # F078N
    "净利润率(%)",               # F017N
    "营业收入增长率(%)",          # F052N
    "归母净利润同比变化率(%)",    # F142N
    "营业收入(元)",              # F089N
    "归母净利润(元)",            # F102N
    "经营活动现金流量净额(元)",   # F105N
    "经营活动现金净流量与净利润比率(%)",  # F063N
]

OPTIONAL_COLUMNS = [
    "净资产收益率(加权)(%)",     # F067N — 优先于 F014N 用于展示
    "总资产周转率(次)",          # F025N — 杜邦拆解
    "资产总计(元)",              # F118N — 计算权益乘数
    "归母所有者权益(元)",        # F129N — 计算权益乘数
    "投资活动现金流量净额(元)",   # F106N — 现金流结构
    "筹资活动现金流量净额(元)",   # F107N — 现金流结构
]


def _validate_dataframe(df):
    """检查 DataFrame 是否包含必要字段，不足3年则报错。
    同时按年份升序排序（确保图表时间轴从左到右是旧→新）。"""
    if df.empty or len(df) < 3:
        raise ValueError(
            f"至少需要3年数据才能生成趋势图，当前仅 {len(df)} 行"
        )

    # 提取年份
    if "报告年度" in df.columns:
        df = df.copy()
        df["报告年度"] = pd.to_datetime(df["报告年度"])
        df = df.sort_values("报告年度", ascending=True).reset_index(drop=True)
        years = df["报告年度"].dt.year
    else:
        raise KeyError("缺少必要字段: 报告年度")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(
            f"缺少必要字段: {', '.join(missing)}。"
            f"请确认 financial_multi_year() 的 fields 参数包含这些字段。"
        )

    return df, years


# ══════════════════════════════════════════════════════════════
# 面板绘制函数
# ══════════════════════════════════════════════════════════════

def _draw_profitability(ax, df, years):
    """面板 (0,0): ROE / 毛利率 / 净利率 三折线"""
    # 优先使用加权ROE
    roe_col = "净资产收益率(加权)(%)" if "净资产收益率(加权)(%)" in df.columns else "净资产收益率(%)"
    metrics = [
        (roe_col, COLORS["roe"], "ROE"),
        ("毛利率(%)", COLORS["gross_margin"], "毛利率"),
        ("净利润率(%)", COLORS["net_margin"], "净利率"),
    ]

    for col, color, label in metrics:
        if col not in df.columns:
            continue
        vals = _safe_float(df[col])
        ax.plot(years, vals, color=color, linewidth=2, marker="o",
                markersize=7, label=label, zorder=3)
        # 数据标签
        for x, y in zip(years, vals):
            if pd.notna(y):
                ax.annotate(f"{y:.1f}%", (x, y), textcoords="offset points",
                           xytext=(0, 10), fontsize=7, ha="center",
                           color=color, fontweight="bold")

    ax.set_title("盈利能力趋势", fontsize=13, fontweight="bold", color=COLORS["title"])
    ax.set_ylabel("%")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(True, linestyle="--", alpha=0.3, color=COLORS["grid"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xticks(years)
    ax.set_xticklabels([str(int(y)) for y in years], fontsize=9)


def _draw_growth(ax, df, years):
    """面板 (0,1): 营收增速 / 归母净利增速 分组柱状图"""
    metrics = [
        ("营业收入增长率(%)", COLORS["rev_growth"], "营收增速"),
        ("归母净利润同比变化率(%)", COLORS["profit_growth"], "归母净利增速"),
    ]

    x = np.arange(len(years))
    width = 0.35
    bars = []
    for i, (col, color, label) in enumerate(metrics):
        if col not in df.columns:
            continue
        vals = _safe_float(df[col])
        b = ax.bar(x + i * width, vals, width, color=color, label=label,
                   zorder=3, alpha=0.9)
        bars.append(b)
        # 数据标签
        for xi, yi in zip(x + i * width, vals):
            if pd.notna(yi):
                va = "bottom" if yi >= 0 else "top"
                offset = 1.5 if yi >= 0 else -1.5
                ax.annotate(f"{yi:.1f}%", (xi, yi),
                           textcoords="offset points",
                           xytext=(0, offset), fontsize=7, ha="center",
                           color=color, fontweight="bold")

    ax.axhline(y=0, color="#666666", linewidth=0.8, linestyle="-", zorder=2)

    ax.set_title("成长能力", fontsize=13, fontweight="bold", color=COLORS["title"])
    ax.set_ylabel("%")
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels([str(int(y)) for y in years], fontsize=9)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(True, linestyle="--", alpha=0.3, color=COLORS["grid"], axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _draw_scale(ax, df, years):
    """面板 (0,2): 营收柱状 + 归母净利折线 (双Y轴)"""
    rev = _to_yi(df["营业收入(元)"])
    profit = _to_yi(df["归母净利润(元)"])

    bars = ax.bar(years, rev, color=COLORS["revenue"], label="营业收入",
                  zorder=3, alpha=0.85, width=0.6)
    for x, y in zip(years, rev):
        if pd.notna(y):
            ax.annotate(f"{y:.0f}亿", (x, y), textcoords="offset points",
                       xytext=(0, 6), fontsize=7, ha="center",
                       color=COLORS["revenue"], fontweight="bold")

    ax2 = ax.twinx()
    ax2.plot(years, profit, color=COLORS["net_profit"], linewidth=2.5,
             marker="s", markersize=8, label="归母净利", zorder=4)
    for x, y in zip(years, profit):
        if pd.notna(y):
            ax2.annotate(f"{y:.0f}亿", (x, y), textcoords="offset points",
                        xytext=(0, -14), fontsize=7, ha="center",
                        color=COLORS["net_profit"], fontweight="bold")

    ax.set_title("营收与利润规模", fontsize=13, fontweight="bold", color=COLORS["title"])
    ax.set_ylabel("营业收入 (亿元)")
    ax2.set_ylabel("归母净利 (亿元)")
    ax.set_xticks(years)
    ax.set_xticklabels([str(int(y)) for y in years], fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.grid(True, linestyle="--", alpha=0.3, color=COLORS["grid"], axis="y")

    # 合并图例
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left",
             fontsize=8, framealpha=0.9)


def _draw_cashflow_quality(ax, df, years):
    """面板 (1,0): OCF/净利 比率柱状图 (绿/橙/红) + 100%基准线"""
    col = "经营活动现金净流量与净利润比率(%)"
    vals = _safe_float(df[col])

    for i, (x, y) in enumerate(zip(years, vals)):
        if pd.isna(y):
            continue
        if y >= 100:
            color = COLORS["ocf_healthy"]
        elif y >= 80:
            color = COLORS["ocf_warning"]
        else:
            color = COLORS["ocf_danger"]
        ax.bar(x, y, color=color, zorder=3, alpha=0.85, width=0.6)
        ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points",
                   xytext=(0, 6), fontsize=8, ha="center",
                   color=color, fontweight="bold")

    ax.axhline(y=100, color=COLORS["threshold"], linewidth=1.5,
              linestyle="--", label="100% 安全线", zorder=2, alpha=0.7)

    ax.set_title("现金流质量 (OCF/净利)", fontsize=13, fontweight="bold",
                color=COLORS["title"])
    ax.set_ylabel("%")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_xticks(years)
    ax.set_xticklabels([str(int(y)) for y in years], fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.3, color=COLORS["grid"], axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _draw_dupont(ax, df, years):
    """面板 (1,1): 杜邦拆解 — 净利率 + 资产周转率 + 权益乘数"""
    nm = _safe_float(df["净利润率(%)"])

    # 资产周转率
    at_col = "总资产周转率(次)" if "总资产周转率(次)" in df.columns else None
    at = _safe_float(df[at_col]) if at_col else None

    # 权益乘数 = 总资产 / 归母权益
    em = None
    if "资产总计(元)" in df.columns and "归母所有者权益(元)" in df.columns:
        ta = _safe_float(df["资产总计(元)"])
        eq = _safe_float(df["归母所有者权益(元)"])
        em = ta / eq

    ax.plot(years, nm, color=COLORS["dupont_nm"], linewidth=2, marker="o",
            markersize=7, label="净利率 %", zorder=3)
    for x, y in zip(years, nm):
        if pd.notna(y):
            ax.annotate(f"{y:.1f}%", (x, y), textcoords="offset points",
                       xytext=(0, 10), fontsize=7, ha="center",
                       color=COLORS["dupont_nm"], fontweight="bold")

    ax2 = ax.twinx()
    if at is not None and not at.isna().all():
        ax2.plot(years, at, color=COLORS["dupont_at"], linewidth=2, marker="s",
                markersize=7, label="资产周转率(次)", zorder=3)
        for x, y in zip(years, at):
            if pd.notna(y):
                ax2.annotate(f"{y:.2f}", (x, y), textcoords="offset points",
                           xytext=(0, -14), fontsize=7, ha="center",
                           color=COLORS["dupont_at"], fontweight="bold")

    if em is not None and not em.isna().all():
        ax2.plot(years, em, color=COLORS["dupont_em"], linewidth=2, marker="^",
                markersize=7, label="权益乘数", zorder=3)
        for x, y in zip(years, em):
            if pd.notna(y):
                ax2.annotate(f"{y:.2f}", (x, y), textcoords="offset points",
                           xytext=(0, -14), fontsize=7, ha="center",
                           color=COLORS["dupont_em"], fontweight="bold")

    ax.set_title("杜邦拆解", fontsize=13, fontweight="bold", color=COLORS["title"])
    ax.set_ylabel("净利率 (%)")
    ax2.set_ylabel("周转率 (次) / 权益乘数")
    ax.set_xticks(years)
    ax.set_xticklabels([str(int(y)) for y in years], fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.grid(True, linestyle="--", alpha=0.3, color=COLORS["grid"], axis="y")

    # 合并图例
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left",
             fontsize=8, framealpha=0.9)


def _draw_cashflow_structure(ax, df, years):
    """面板 (1,2): 经营/投资/筹资 现金流净额 分组柱状图"""
    ocf = _to_yi(df["经营活动现金流量净额(元)"])
    icf_col = "投资活动现金流量净额(元)"
    fcf_col = "筹资活动现金流量净额(元)"

    has_icf = icf_col in df.columns
    has_fcf = fcf_col in df.columns

    x = np.arange(len(years))
    n_groups = 1 + int(has_icf) + int(has_fcf)
    width = 0.7 / n_groups

    offset = 0
    ax.bar(x + offset * width, ocf, width, color=COLORS["ocf"],
           label="经营活动", zorder=3, alpha=0.85)
    for xi, yi in zip(x + offset * width, ocf):
        if pd.notna(yi):
            va = "bottom" if yi >= 0 else "top"
            off = 1.5 if yi >= 0 else -1.5
            ax.annotate(f"{yi:.0f}", (xi, yi), textcoords="offset points",
                       xytext=(0, off), fontsize=6, ha="center",
                       color=COLORS["ocf"], fontweight="bold")
    offset += 1

    if has_icf:
        icf = _to_yi(df[icf_col])
        ax.bar(x + offset * width, icf, width, color=COLORS["icf"],
               label="投资活动", zorder=3, alpha=0.85)
        for xi, yi in zip(x + offset * width, icf):
            if pd.notna(yi):
                va = "bottom" if yi >= 0 else "top"
                off = 1.5 if yi >= 0 else -1.5
                ax.annotate(f"{yi:.0f}", (xi, yi), textcoords="offset points",
                           xytext=(0, off), fontsize=6, ha="center",
                           color=COLORS["icf"], fontweight="bold")
        offset += 1

    if has_fcf:
        fcf = _to_yi(df[fcf_col])
        ax.bar(x + offset * width, fcf, width, color=COLORS["fcf"],
               label="筹资活动", zorder=3, alpha=0.85)
        for xi, yi in zip(x + offset * width, fcf):
            if pd.notna(yi):
                va = "bottom" if yi >= 0 else "top"
                off = 1.5 if yi >= 0 else -1.5
                ax.annotate(f"{yi:.0f}", (xi, yi), textcoords="offset points",
                           xytext=(0, off), fontsize=6, ha="center",
                           color=COLORS["fcf"], fontweight="bold")

    ax.axhline(y=0, color="#666666", linewidth=0.8, linestyle="-", zorder=2)
    ax.set_title("现金流结构 (亿元)", fontsize=13, fontweight="bold",
                color=COLORS["title"])
    ax.set_ylabel("亿元")
    ax.set_xticks(x + (offset - 1) * width / 2)
    ax.set_xticklabels([str(int(y)) for y in years], fontsize=9)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(True, linestyle="--", alpha=0.3, color=COLORS["grid"], axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ══════════════════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════════════════

def generate_profitability_growth_chart(
    df,
    company_name,
    stock_code,
    output_path,
    years_column="报告年度",
    figsize=(18, 12),
    dpi=150,
    show_data_labels=True,
):
    """生成盈利与成长能力综合全景图 (2x3 六面板)。

    Args:
        df: CninfoClient.financial_multi_year() 返回的 DataFrame，
            列名已转为中文。
        company_name: 公司全称。
        stock_code: 股票代码。
        output_path: 输出 PNG 文件的完整路径。
        years_column: 年份列名 (默认 "报告年度")。
        figsize: 图表尺寸 (英寸)。
        dpi: 输出分辨率。
        show_data_labels: 是否显示数据标签。

    Returns:
        str: 输出 PNG 文件的绝对路径。

    Raises:
        ValueError: 数据不足 3 年。
        KeyError: 必填字段缺失。
    """
    # 验证数据 + 按年份升序排序
    df, years = _validate_dataframe(df)
    year_list = years.astype(int).tolist()

    # 创建图形
    fig, axes = plt.subplots(2, 3, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor(COLORS["bg"])
    axes = axes.flatten()

    # 总标题
    fig.suptitle(
        f"{company_name} ({stock_code})  盈利与成长能力全景图",
        fontsize=18, fontweight="bold", color=COLORS["title"], y=0.98
    )

    # 绘制六个面板
    _draw_profitability(axes[0], df, year_list)
    _draw_growth(axes[1], df, year_list)
    _draw_scale(axes[2], df, year_list)
    _draw_cashflow_quality(axes[3], df, year_list)
    _draw_dupont(axes[4], df, year_list)
    _draw_cashflow_structure(axes[5], df, year_list)

    # 数据来源脚注
    fig.text(0.5, 0.01, "数据来源：深证信 CNINFO | 制图：ZephyrSpace Deep Analysis",
             ha="center", fontsize=9, color="#999999", style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 0.94])

    # 确保输出目录存在
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out), dpi=dpi, bbox_inches="tight",
                facecolor=COLORS["bg"], edgecolor="none")
    plt.close(fig)

    return str(out.resolve())


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="生成深度分析用财务全景图"
    )
    parser.add_argument("stock_code", help="股票代码，如 600519")
    parser.add_argument("company_name", help="公司全称，如 贵州茅台")
    parser.add_argument("-o", "--output", default=None,
                       help="输出 PNG 路径 (默认: 深度分析/[公司名]_盈利成长能力.png)")
    parser.add_argument("--years", default=None,
                       help="年份范围，如 2019-2025 (默认: 7年，截止到当前年份)")
    parser.add_argument("--dpi", type=int, default=150,
                       help="输出分辨率 (默认 150)")

    args = parser.parse_args()

    # 默认年份范围：回溯7年，截止到当前年份
    if args.years is None:
        this_year = datetime.now().year
        y_start, y_end = this_year - 6, this_year
        args.years = f"{y_start}-{y_end}"
    else:
        y_start, y_end = args.years.split("-")
        y_start, y_end = int(y_start), int(y_end)

    years = list(range(int(y_start), int(y_end) + 1))

    # 默认输出路径
    if args.output is None:
        args.output = f"深度分析/{args.company_name}_盈利成长能力.png"

    # 拉取数据
    vault_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(vault_root))

    from scripts.cninfo_api import CninfoClient

    client = CninfoClient()
    print(f"正在拉取 {args.stock_code} {args.company_name} 的财务数据 ({args.years})...")

    # 请求所有图表需要的字段
    chart_fields = [
        "F069D", "F014N", "F067N", "F078N", "F017N",
        "F052N", "F142N", "F089N", "F102N",
        "F105N", "F063N", "F025N",
        "F118N", "F129N", "F106N", "F107N",
    ]

    df = client.financial_multi_year(
        args.stock_code, years=years, fields=chart_fields
    )

    if df.empty:
        print(f"错误：未获取到 {args.stock_code} 在 {args.years} 期间的财务数据。")
        sys.exit(1)

    print(f"已获取 {len(df)} 年数据，正在生成图表...")

    # 生成图表
    try:
        path = generate_profitability_growth_chart(
            df, args.company_name, args.stock_code,
            args.output, dpi=args.dpi,
        )
        print(f"图表已保存: {path}")
    except (ValueError, KeyError) as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
