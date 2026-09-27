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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = render(args.source.read_bytes(), str(args.source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(result)
    print(f"阅读视图已生成：{args.output}，{len(result.splitlines())}行；原件未修改。")


if __name__ == "__main__":
    main()
