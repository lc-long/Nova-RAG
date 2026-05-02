# -*- coding: utf-8 -*-
"""Diagnose chunking and retrieval for the enterprise test document."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

API_BASE = 'http://localhost:5000/api/v1'
DOC_ID = '74488652-1a0f-4449-8252-465a1f4d0d3c'

# Get document content
resp = requests.get(f'{API_BASE}/docs/{DOC_ID}/content')
data = resp.json()

print(f'Document: {data["name"]}')
print(f'Status: {data["status"]}')
print(f'Content length: {len(data["content"])} chars')
print()

# Search for key content that should be in the document
content = data['content']
keywords = [
    '夜间飞行',
    '审批权限',
    '运营经理',
    '总经理',
    '降级',
    '恢复',
    '继续教育',
    '24学时',
    '16学时',
    '风速',
    '8m/s',
    '30%',
    '84',
    '50%',
    '60',
]

print('Content search:')
for kw in keywords:
    count = content.count(kw)
    if count > 0:
        # Find context
        idx = content.find(kw)
        start = max(0, idx - 30)
        end = min(len(content), idx + len(kw) + 30)
        context = content[start:end].replace('\n', ' ')
        print(f'  [{count:2d}] "{kw}" -> ...{context}...')
    else:
        print(f'  [ 0] "{kw}" -> NOT FOUND')

# Also try a retrieval query
print()
print('Testing retrieval for "夜间飞行规定":')
resp = requests.post(
    f'{API_BASE}/chat/completions',
    json={
        'messages': [{'role': 'user', 'content': '夜间飞行规定是什么？'}],
        'stream': True,
        'doc_id': DOC_ID,
    },
    stream=True,
    timeout=60,
)
answer = ''
for line in resp.iter_lines(decode_unicode=True):
    if not line or not line.startswith('data:'):
        continue
    data_str = line[5:].strip()
    if data_str == '[DONE]':
        continue
    try:
        parsed = json.loads(data_str)
        if parsed.get('type') == 'answer':
            answer += parsed.get('content', '')
    except json.JSONDecodeError:
        pass

print(f'Answer: {answer[:500]}')
