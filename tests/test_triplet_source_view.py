"""验证财报阅读视图保留数值、表头、合并关系及原件定位。"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.triplet_source_view import render, excerpt


class SourceViewTests(unittest.TestCase):
    def test_excerpt_keeps_header_unit_note_and_original_coordinate(self):
        rows = ''.join(f'<tr><td>项目{i}</td><td>{i}</td></tr>' for i in range(20))
        raw = ('单位：万元\n<table><tr><td>项目</td><td>2025年度</td></tr>'
               + rows + '</table>\n附注：合并口径').encode()
        result = excerpt(raw, '原件.md', '项目15', context=0)
        for value in ['单位：万元', '2025年度', 'L2-2:R17: 项目15 | 15', '附注：合并口径', '省略', '命中1行']:
            self.assertIn(value, result)
        self.assertNotIn('项目10 |', result)

    def test_broad_query_fails_instead_of_silently_truncating(self):
        raw = ('\n'.join(f'经营项目{i}：' + '甲'*100 for i in range(100))).encode()
        with self.assertRaisesRegex(ValueError, '查询过宽'):
            excerpt(raw, '原件.md', '经营', max_chars=1000)

    def test_no_match_is_explicit_and_retains_source_hash(self):
        result = excerpt('无此指标'.encode(), '原件.md', '营业收入')
        self.assertIn('命中0行', result)
        self.assertIn('SHA256', result)
        self.assertNotIn('无此指标', result)

    def test_extended_merged_header_is_not_dropped(self):
        raw = ('<table><tr><td rowspan="4">期别</td><td>头1</td></tr>'
               '<tr><td>头2</td></tr><tr><td>头3</td></tr><tr><td>头4</td></tr>'
               '<tr><td>项目</td><td>123</td></tr></table>').encode()
        result = excerpt(raw, '原件.md', '123', context=0)
        self.assertIn('头4', result)

    def test_two_tables_on_same_source_line_keep_their_own_headers(self):
        first = '<table><tr><td>甲表头</td></tr>' + '<tr><td>甲数据</td></tr>'*8 + '</table>'
        second = '<table><tr><td>乙表头</td></tr>' + '<tr><td>乙数据</td></tr>'*8 + '<tr><td>目标金额</td></tr></table>'
        result = excerpt((first+second).encode(), '原件.md', '目标金额', context=0)
        self.assertIn('乙表头', result)
        self.assertNotIn('甲表头', result)

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
