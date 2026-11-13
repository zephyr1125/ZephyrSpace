"""生成可按行检索的财报阅读视图；保留原件坐标，不替代原件或判断证据。"""
import argparse
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell, self.notes = [], [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            spans = [(k, v) for k, v in attrs if k in ("rowspan", "colspan") and v != "1"]
            self.cell = ["[" + ",".join(f"{k}={v}" for k, v in spans) + "] "] if spans else []
        elif self.cell is not None and tag in ("br", "p", "div"):
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
        elif data.strip():
            self.notes.append(data.strip())

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr":
            self.rows.append(self.row)
            self.row = []


def render(raw, source):
    text = raw.decode("utf-8-sig")
    output = [f"原件：{source}", f"SHA256：{hashlib.sha256(raw).hexdigest()}",
              "L为原件行号，R为该HTML表内行号；合并单元格保留span标记。须结合表头、单位、附注核验。"]
    offset = 0
    for match in re.finditer(r"<table\b[^>]*>.*?</table>", text, re.I | re.S):
        prefix = text[offset:match.start()]
        line = text.count("\n", 0, offset) + 1
        output.extend(f"L{line+i}: {s}" for i, s in enumerate(prefix.splitlines()) if s.strip())
        first = text.count("\n", 0, match.start()) + 1
        last = text.count("\n", 0, match.end()) + 1
        parser = TableRows()
        parser.feed(match.group())
        if parser.notes:
            output.append(f"L{first}-{last}:表内说明: " + " ".join(parser.notes))
        for i, row in enumerate(parser.rows, 1):
            output.append(f"L{first}-{last}:R{i}: " + " | ".join(row))
        offset = match.end()
    line = text.count("\n", 0, offset) + 1
    output.extend(f"L{line+i}: {s}" for i, s in enumerate(text[offset:].splitlines()) if s.strip())
    return "\n".join(output) + "\n"


def excerpt(raw, source, query, context=2, max_chars=12000):
    """只输出命中及定位上下文；过宽查询明确失败，禁止静默截掉单位或尾部。"""
    if context < 0 or not 1000 <= max_chars <= 20000:
        raise ValueError("context须非负，max-chars须在1000至20000之间")
    pattern = re.compile(query, re.I)
    lines = render(raw, source).splitlines()
    hits = [i for i in range(3, len(lines)) if pattern.search(lines[i])]
    chosen = set(range(3))
    tables = {}
    rows = []
    for i, line in enumerate(lines):
        match = re.match(r"(L\d+-\d+):R(\d+):", line)
        if match:
            if match[2] == "1":
                rows = []
            rows.append(i)
            tables[i] = rows
    for i in hits:
        chosen.update(range(max(3, i-context), min(len(lines), i+context+1)))
        match = re.match(r"(L\d+-\d+):R\d+:", lines[i])
        if match:
            rows = tables[i]
            # 保留前三行及合并表头覆盖的行；仍须由读者核原件列归属。
            header_count = max([3] + [int(n) for n in re.findall(r"rowspan=(\d+)", lines[rows[0]])])
            chosen.update(rows[:header_count])
            chosen.update(range(max(3, rows[0]-3), rows[0]))
            chosen.update(range(rows[-1]+1, min(len(lines), rows[-1]+3)))
    output = []
    last = -1
    for i in sorted(chosen):
        if i > last + 1:
            output.append(f"[省略{ i-last-1 }行阅读视图；原件未删改]")
        output.append(lines[i])
        last = i
    output.append(f"命中{len(hits)}行；仅为检索摘录，表头、期间、单位及合并单元格须核原件。")
    result = "\n".join(output) + "\n"
    if len(result) > max_chars:
        raise ValueError(f"查询过宽：命中{len(hits)}行，上下文共{len(result)}字符，超过{max_chars}；请缩小关键词或一次只查一个报表项目，不返回截断事实。")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--find", help="正则查询；直接输出有界摘录，不写缓存")
    parser.add_argument("--context", type=int, default=2)
    parser.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args()
    if args.find is not None:
        if args.output is not None:
            parser.error("--find不与output同时使用")
        try:
            print(excerpt(args.source.read_bytes(), str(args.source), args.find, args.context, args.max_chars), end="")
        except (ValueError, re.error) as exc:
            parser.exit(2, f"{exc}\n")
        return
    if args.output is None:
        parser.error("生成完整阅读视图须给output，或使用--find查询")
    result = render(args.source.read_bytes(), str(args.source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(result)
    print(f"阅读视图已生成：{args.output}，{len(result.splitlines())}行；原件未修改。")


if __name__ == "__main__":
    main()
