"""验证财报阅读视图保留数值、表头、合并关系及原件定位。"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.triplet_source_view import render


class SourceViewTests(unittest.TestCase):
    def test_single_line_table_keeps_units_headers_spans_and_values(self):
        raw = ('单位：万元\n<table><caption>合并现金流</caption><tr><th rowspan="2">项目</th>'
               '<th colspan="2">年度</th></tr><tr><td>2025</td><td>2024</td></tr>'
               '<tr><td>经营净额</td><td>-1,234.50</td><td>—</td></tr></table>\n附注：受存款变化影响').encode()
        result = render(raw, '原报告.md')
        for value in ('单位：万元', '合并现金流', '[rowspan=2]', '[colspan=2]', '2025 | 2024',
                      'L2-2:R3: 经营净额 | -1,234.50 | —', 'L3: 附注：受存款变化影响'):
            self.assertIn(value, result)

    def test_multiline_tables_and_plain_markdown_keep_original_line_coordinates(self):
        raw = b'# Title\n<table>\n<tr><td>A&amp;B</td><td>0</td></tr>\n</table>\nAfter\n'
        result = render(raw, 'source.md')
        self.assertIn('L2-4:R1: A&B | 0', result)
        self.assertIn('L5: After', result)
        self.assertIn('L1: # Title', result)


if __name__ == '__main__':
    unittest.main()
