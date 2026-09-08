"""验证材料隔离、输入边界与不完整响应拒绝。"""
import importlib.util
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('review', Path(__file__).parents[1] / 'scripts/deepseek_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def test_blind_stage_excludes_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in [('rules.md', '评分规则'), ('evidence.md', '营收100'), ('draft.md', '作者目标价9876')]:
                (root / name).write_text(content, encoding='utf-8')
            cfg = dict(company='测试', cutoff='2026-09-08', rules=['rules.md'], evidence=['evidence.md'], drafts=['draft.md'])
            bundle = review.build_bundle(root, cfg)
            messages = review.first_messages(cfg, bundle)
            self.assertNotIn('9876', str(messages))
            self.assertIn('营收100', str(messages))
            cfg['evidence'] = ['draft.md']
            with self.assertRaises(ValueError):
                review.build_bundle(root, cfg)

    def test_material_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                review.read_material(root, '../escape.md')
            (root / 'secret.md').write_text('sk-' + 'a' * 24)
            with self.assertRaises(ValueError):
                review.read_material(root, 'secret.md')

    def test_truncated_response_rejected(self):
        response = Mock(status_code=200)
        response.json.return_value = {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}
        with patch('requests.post', return_value=response):
            with self.assertRaises(ValueError):
                review.call_api([], 'test', 'test', 100, 1)

    def test_invalid_findings_rejected(self):
        with self.assertRaises(ValueError):
            review.validate_result({'assessment': '正常', 'findings': [{'severity': 'P1'}], 'unknowns': []})

    def run_pipeline(self, fail_second):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['rules.md', 'evidence.md', 'draft.md']:
                (root / name).write_text('测试材料', encoding='utf-8')
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps(dict(id='test', company='测试', cutoff='2026-09-08',
                                               rules=['rules.md'], evidence=['evidence.md'], drafts=['draft.md'])), encoding='utf-8')
            result = {'result': {'assessment': '独立判断', 'findings': [], 'unknowns': []}, 'usage': {'total_tokens': 10}}
            with patch.object(review, 'ROOT', root), patch('sys.argv', ['review', '--manifest', str(manifest), '--execute']), \
                 patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test'}), \
                 patch.object(review, 'call_api', side_effect=[result, ValueError('第二阶段失败') if fail_second else result]):
                if fail_second:
                    with self.assertRaises(SystemExit):
                        review.main()
                else:
                    review.main()
            status_path = next(root.glob('data/reviews/test/*/status.json'))
            status = json.loads(status_path.read_text(encoding='utf-8'))
            self.assertEqual(status['external_review_complete'], not fail_second)
            self.assertEqual(status['status'], 'failed' if fail_second else 'awaiting_adjudication')
            self.assertTrue((status_path.parent / 'stage1-result.json').exists())
            self.assertFalse((root / 'data/watchlist_core.json').exists())

    def test_full_pipeline(self):
        self.run_pipeline(False)

    def test_partial_failure_keeps_first_result(self):
        self.run_pipeline(True)


if __name__ == '__main__':
    unittest.main()
