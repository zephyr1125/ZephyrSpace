
import json, os, re, sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

VAULT_ROOT = Path(os.environ.get("DSH_WORKSPACE", Path.cwd()))
# 若 cwd 不是 vault 根（例如在子目录运行），向上寻找包含 management-archive/SKILL.md 的目录
def _find_root() -> Path:
    p = Path.cwd()
    for cand in [p, *p.parents]:
        if (cand / "management-archive" / "SKILL.md").exists():
            return cand
    return Path.cwd()

VAULT_ROOT = _find_root()
EVALS_DIR = VAULT_ROOT / "evals"

def load_config() -> Dict[str, Any]:
    cfg_path = EVALS_DIR / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# ---------------------------------------------------------------- errors

@dataclass
class EvalError:
    severity: str            # P0 | P1 | P2
    category: str
    message: str
    location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ---------------------------------------------------------------- rating

RATING_BANDS = [
    (85, 100, "卓越"),
    (70, 84, "优秀"),
    (55, 69, "良好"),
    (40, 54, "一般"),
    (0, 39, "不达标"),
]

def rating_for_score(score: int) -> str:
    for lo, hi, name in RATING_BANDS:
        if lo <= score <= hi:
            return name
    return "不达标"

def parse_score(text: str) -> Optional[int]:
    """从文本中提取第一个整数分数。"""
    m = re.search(r"(\d{1,3})", text or "")
    return int(m.group(1)) if m else None

# ---------------------------------------------------------------- archive parsing

@dataclass
class ArchiveDocument:
    path: Path
    text: str
    lines: List[str]
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    sections: Dict[str, str] = field(default_factory=dict)  # heading -> body
    quick_ref_text: str = ""
    scores: Dict[str, int] = field(default_factory=dict)    # dimension -> score
    max_scores: Dict[str, int] = field(default_factory=dict)
    total_score: Optional[int] = None
    declared_rating: str = ""
    filename_score: Optional[int] = None
    filename_date: Optional[str] = None
    card_score: Optional[int] = None

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def section_text(self, section: str) -> str:
        return self.sections.get(section, "")

    def find(self, pattern: str) -> List[Tuple[int, str]]:
        rx = re.compile(pattern)
        return [(i + 1, ln) for i, ln in enumerate(self.lines) if rx.search(ln)]


FRONTMATTER_RE = re.compile(r"^---\s*$")

def parse_frontmatter(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    fm: Dict[str, Any] = {}
    if not lines or lines[0].strip() != "---":
        return fm
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i]
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                fm[key] = [v.strip() for v in val[1:-1].split(",")]
            elif val.startswith("[[") and val.endswith("]]"):
                fm[key] = val
            else:
                fm[key] = val
        i += 1
    return fm


SECTION_NUM_RE = re.compile(r"^#{1,6}\s+(十[一二三四五六七八九]?|[一二三四五六七八九])、(.+)$")

def parse_sections(text: str) -> Dict[str, str]:
    """解析 '## 一、管理层画像' 形式的章节；返回 {章节完整标题: 正文}。"""
    lines = text.splitlines()
    sections: Dict[str, str] = {}
    current = None
    buf: List[str] = []
    for ln in lines:
        m = SECTION_NUM_RE.match(ln.strip())
        if m:
            if current:
                sections[current] = "\n".join(buf)
            current = ln.strip().lstrip("#").strip()
            buf = []
        else:
            if current is not None:
                buf.append(ln)
    if current:
        sections[current] = "\n".join(buf)
    return sections


def extract_scores(text: str) -> Tuple[Dict[str, int], Dict[str, int], Optional[int]]:
    """从「九、管理层评分」表格提取 (维度分数, 维度满分, 总分)。

    只选含 '得分' 列且不含 '门槛/实际' 的表格块（排除 40% 阈值检查表）。
    """
    # 定位评分章节（九、管理层...）
    sections = parse_sections(text)
    score_section = None
    for key, body in sections.items():
        if key.startswith("九、") or (("评分" in key or "100 分制" in key) and not key.startswith(("十", "十一"))):
            score_section = body
            break
    if score_section is None:
        # 兜底：全文找含"维度/满分/得分"表头的表格
        score_section = text

    blocks = _table_blocks(score_section)
    target = None
    for block in blocks:
        if not block:
            continue
        header = " ".join(block[0])
        if "得分" in header and "门槛" not in header and "实际" not in header:
            target = block
            break
    if target is None and blocks:
        # 退化：取第一个含"满分"的表
        for block in blocks:
            if "满分" in " ".join(block[0]):
                target = block
                break

    scores: Dict[str, int] = {}
    maxs: Dict[str, int] = {}
    total = None
    if target:
        for row in target[1:]:
            cells = [c.strip() for c in row if c.strip()]
            if len(cells) < 3:
                continue
            name_raw = cells[0].replace("**", "").strip()
            maxv = _first_int(cells[1])
            score = _first_int(cells[2])
            if maxv is None or score is None:
                continue
            if "总分" in name_raw:
                total = score
                continue
            name = normalize_dimension(name_raw)
            if name:
                scores[name] = score
                maxs[name] = maxv
    return scores, maxs, total


def _table_blocks(text: str) -> List[List[List[str]]]:
    """把连续表格行分组为块。"""
    blocks: List[List[List[str]]] = []
    current: List[List[str]] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue  # 分隔行
            current.append(cells)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    return blocks


def _first_int(s: str) -> Optional[int]:
    s = s.replace("**", "").strip()
    m = re.search(r"\d{1,3}", s)
    return int(m.group(0)) if m else None



DIMENSION_ALIASES = {
    "诚信与透明度": ["诚信", "诚信与透明"],
    "资本配置能力": ["资本配置"],
    "战略稳定性": ["战略稳定"],
    "对股东友好度": ["股东友好", "对股东友好"],
    "危机处理能力": ["危机处理"],
    "组织与人才能力": ["组织与人才", "组织人才"],
    "表达清晰度与认知质量": ["表达清晰度", "表达清晰", "认知质量"],
}

def normalize_dimension(name: str) -> Optional[str]:
    name = name.strip()
    for canon, aliases in DIMENSION_ALIASES.items():
        if name == canon or any(name.startswith(a) or a in name for a in aliases):
            return canon
    # 数字序号开头（如 "1. 诚信"）
    m = re.match(r"^\d+[.、\s]+(.+)$", name)
    if m:
        return normalize_dimension(m.group(1))
    return None




def load_archive(path: Path) -> ArchiveDocument:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    fm = parse_frontmatter(text)
    sections = parse_sections(text)
    doc = ArchiveDocument(path=path, text=text, lines=lines, frontmatter=fm, sections=sections)

    # 快速参考卡片
    qidx = text.find(CONFIG["structure"]["quick_reference_marker"])
    if qidx >= 0:
        end = text.find("\n## ", qidx)
        doc.quick_ref_text = text[qidx:end if end > 0 else qidx + 3000]

    # 文件名评分与日期: "[公司简称] 管理层档案 [评分] YYYY-MM-DD.md"
    fn = path.name
    m = re.match(r"^(.+?) 管理层档案 (\d{1,3}) (\d{4}-\d{2}-\d{2})\.md$", fn)
    if m:
        doc.filename_score = int(m.group(2))
        doc.filename_date = m.group(3)

    # 评分表（优先取详细评分章节，其次全文）
    scores, maxs, total = extract_scores(text)
    doc.scores, doc.max_scores, doc.total_score = scores, maxs, total

    # 速览卡内的总分（如 "**94 / 100**"）
    m2 = re.search(r"\*{1,2}(\d{1,3})\s*/\s*100\*{1,2}", doc.quick_ref_text)
    if m2:
        doc.card_score = int(m2.group(1))

    # 评级声明：优先从速览卡提取（排除评级标准参考表）
    doc.declared_rating = _extract_declared_rating(doc)
    return doc


def _extract_declared_rating(doc: ArchiveDocument) -> str:
    candidates = []
    if doc.quick_ref_text:
        # 速览卡评级行: | **评级** | ⭐⭐⭐⭐⭐ 卓越 |
        m = re.search(r"评级[^|]*\|\s*(⭐{1,5})\s*(卓越|优秀|良好|一般|不达标)?", doc.quick_ref_text)
        if m:
            star = len(m.group(1))
            name = m.group(2)
            return name if name else {5: "卓越", 4: "优秀", 3: "良好", 2: "一般", 1: "不达标"}.get(star, "")
    # 综合结论/正文中的评级声明
    for key, body in doc.sections.items():
        if key.startswith("十一、") or "综合结论" in key:
            m = re.search(r"评级[：:]?\s*(⭐{1,5})?\s*(卓越|优秀|良好|一般|不达标)", body)
            if m:
                return m.group(2) or ""
    m = re.search(r"评级[：:]\s*(⭐{1,5})?\s*(卓越|优秀|良好|一般|不达标)", doc.text)
    if m:
        return m.group(2) or ""
    return ""


# ---------------------------------------------------------------- case loading

@dataclass
class EvalCase:
    id: str
    company: Dict[str, Any]
    prompt: str
    tags: List[str] = field(default_factory=list)
    expected_behavior: Dict[str, Any] = field(default_factory=dict)
    golden_facts_file: Optional[str] = None
    required_workflow: Dict[str, bool] = field(default_factory=dict)
    expected_sections: List[str] = field(default_factory=list)
    output: Optional[str] = None
    trace: Optional[str] = None
    expected_score_range: Optional[List[int]] = None
    source_file: Optional[Path] = None

    def golden_facts_path(self) -> Optional[Path]:
        if not self.golden_facts_file:
            return None
        p = Path(self.golden_facts_file)
        if not p.is_absolute():
            p = EVALS_DIR / p
        return p

    def output_path(self) -> Optional[Path]:
        if not self.output:
            return None
        p = Path(self.output)
        if not p.is_absolute():
            p = VAULT_ROOT / p
        return p


def load_cases(companies_dir: Optional[Path] = None, trigger_dir: Optional[Path] = None) -> Dict[str, EvalCase]:
    cases: Dict[str, EvalCase] = {}
    base = EVALS_DIR / "cases" / CONFIG["suite"]
    companies_dir = companies_dir or (base / "companies")
    trigger_dir = trigger_dir if trigger_dir is not None else (base / "trigger")
    for f in sorted(companies_dir.glob("*.yaml")):
        for c in load_case_file(f):
            cases[c.id] = c
    if trigger_dir:
        for f in sorted(trigger_dir.glob("*.yaml")):
            for c in load_case_file(f):
                cases[c.id] = c
    reg_dir = base / "regression"
    if reg_dir.exists():
        for f in sorted(reg_dir.glob("*.yaml")):
            for c in load_case_file(f):
                cases[c.id] = c
    return cases


def load_case_file(path: Path) -> List[EvalCase]:
    """加载单个 case 文件。支持：单 dict / dict 列表 / 多 YAML 文档。"""
    out: List[EvalCase] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in yaml.safe_load_all(f):
            if raw is None:
                continue
            if isinstance(raw, list):
                out.extend(case_from_dict(d, path) for d in raw)
            else:
                out.append(case_from_dict(raw, path))
    return out


def case_from_dict(raw: Dict[str, Any], source: Optional[Path] = None) -> EvalCase:
    return EvalCase(
        id=raw["id"],
        company=raw.get("company", {"name": "", "ticker": "000000.SZ", "market": "A"}),
        prompt=raw.get("prompt", raw.get("title", "")),
        tags=raw.get("tags", []),
        expected_behavior=raw.get("expected_behavior", {}),
        golden_facts_file=raw.get("golden_facts_file"),
        required_workflow=raw.get("required_workflow", {}),
        expected_sections=raw.get("expected_sections", []),
        output=raw.get("output"),
        trace=raw.get("trace"),
        expected_score_range=raw.get("expected_score_range"),
        source_file=source,
    )


def load_golden_facts(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------- result aggregation

def weighted_score(scores: Dict[str, Optional[float]]) -> Optional[float]:
    weights = CONFIG["weights"]
    total_w = sum(weights.values())
    acc = 0.0
    for dim, w in weights.items():
        s = scores.get(dim)
        if s is None:
            continue
        acc += w * s
    return round(acc / total_w * 100, 1)


def gates_pass(gates: Dict[str, Any]) -> bool:
    return all(v is True for v in gates.values())


def p0_p1_counts(errors: List[EvalError]) -> Tuple[int, int]:
    p0 = sum(1 for e in errors if e.severity == "P0")
    p1 = sum(1 for e in errors if e.severity == "P1")
    return p0, p1


# ---------------------------------------------------------------- path helpers

def default_reports_dir() -> Path:
    return VAULT_ROOT / CONFIG["paths"]["reports_dir"]

def default_skill_path() -> Path:
    return VAULT_ROOT / CONFIG["paths"]["skill_default"]

@dataclass
class GraderResult:
    """单个 grader 的输出。score 为 0-1（None 表示不适用/跳过）。"""
    name: str
    score: Optional[float] = None
    errors: List[EvalError] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    gates: Dict[str, bool] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, severity: str, category: str, message: str, location: Optional[str] = None):
        self.errors.append(EvalError(severity, category, message, location))