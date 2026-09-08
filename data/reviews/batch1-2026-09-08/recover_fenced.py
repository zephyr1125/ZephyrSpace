"""本批次手动恢复完整围栏响应；复用原第一阶段，不重新生成。"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from deepseek_review import call_api, parse_result, save
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument('run')
args = parser.parse_args()
out = (ROOT / args.run).resolve()
if not out.is_relative_to(ROOT / 'data' / 'reviews') or not out.parent.name.startswith('batch1-'):
    raise ValueError('仅允许本批次运行目录')
if (out / 'stage2-response.json').exists() or (out / 'status-before-recovery.json').exists():
    raise ValueError('已经尝试恢复，不重复执行')
load_dotenv(ROOT / '.env', encoding='utf-8-sig')
key = os.getenv('DEEPSEEK_API_KEY') or os.getenv('DEEPSEEK_KEY')
if not key:
    raise ValueError('缺少密钥')
raw = json.loads((out / 'stage1-response.json').read_text(encoding='utf-8'))
if raw['finish_reason'] != 'stop':
    raise ValueError('第一阶段不是完整响应')
first = {k: raw.get(k) for k in ('model', 'usage', 'request_id', 'elapsed_seconds')}
first['result'] = parse_result(raw['content'])
status = json.loads((out / 'status.json').read_text(encoding='utf-8'))
save(out / 'status-before-recovery.json', status)
save(out / 'stage1-result.json', first)
status['recovery'] = '只移除外层围栏，复用既有第一阶段；原失败状态另存'
messages = json.loads((out / 'stage1-request.json').read_text(encoding='utf-8'))
bundle = json.loads((out / 'input.json').read_text(encoding='utf-8'))['bundle']
messages += [{'role': 'assistant', 'content': json.dumps(first['result'], ensure_ascii=False)},
             {'role': 'user', 'content': '现在对照初稿，列出证据支持的分歧与修正，保留合理异议。\n' + json.dumps(bundle['drafts'], ensure_ascii=False)}]
if sum(len(m['content']) for m in messages) > status['parameters']['max_chars']:
    raise ValueError('第二阶段超过预算')
save(out / 'stage2-request.json', messages)
try:
    second = call_api(messages, key, 'deepseek-v4-flash', 12000, 300,
                      out / 'stage2-response.json', 'disabled')
    save(out / 'stage2-result.json', second)
    status.update(status='awaiting_adjudication', external_review_complete=True, error=None)
except Exception as exc:
    status.update(status='failed', error=type(exc).__name__)
    raise
finally:
    save(out / 'status.json', status)
print('恢复并完成第二阶段：' + str(out))
