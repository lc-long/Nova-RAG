# -*- coding: utf-8 -*-
"""Enterprise RAG test with tricky real-world scenarios.

Tests various challenging scenarios that enterprise knowledge bases commonly face:
1. Conditional rules (different limits for different scenarios)
2. Numerical precision (exact values from tables)
3. Cross-page information correlation
4. Negation/exception handling
5. Similar concept disambiguation
6. Enumeration questions
7. Multi-parameter queries
8. Version comparison (V3.1 vs V3.2)
9. Implicit information (requires inference)
10. Edge case questions
"""
import json
import time
import sys
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = 'http://localhost:5000/api/v1'
DOC_ID = '74488652-1a0f-4449-8252-465a1f4d0d3c'  # enterprise_test_doc.pdf


def ask_question(question, doc_id=None, timeout=60):
    """Send a question and collect the full SSE response."""
    payload = {
        'messages': [{'role': 'user', 'content': question}],
        'stream': True,
        'doc_id': doc_id,
    }

    start = time.time()
    try:
        resp = requests.post(
            f'{API_BASE}/chat/completions',
            json=payload,
            stream=True,
            timeout=timeout,
        )
        resp.raise_for_status()

        answer = ''
        reasoning = ''
        thoughts = []
        references = []

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith('data:'):
                continue
            data = line[5:].strip()
            if data == '[DONE]':
                continue
            try:
                parsed = json.loads(data)
                if parsed.get('type') == 'thought':
                    thoughts.append(parsed.get('content', ''))
                elif parsed.get('type') == 'reasoning':
                    reasoning += parsed.get('content', '')
                elif parsed.get('type') == 'answer':
                    answer += parsed.get('content', '')
                elif parsed.get('type') == 'error':
                    answer += f'[ERROR] {parsed.get("content", "")}'
                elif parsed.get('done'):
                    references = parsed.get('references', [])
            except json.JSONDecodeError:
                pass

        elapsed = time.time() - start
        return {
            'answer': answer.strip(),
            'reasoning': reasoning.strip(),
            'thoughts': thoughts,
            'references': references,
            'time': round(elapsed, 1),
            'error': None,
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            'answer': '',
            'reasoning': '',
            'thoughts': [],
            'references': [],
            'time': round(elapsed, 1),
            'error': str(e),
        }


def check_answer(answer, expected_keywords, must_not_contain=None):
    """Check if answer contains expected keywords and not forbidden ones."""
    answer_lower = answer.lower()
    found = []
    missing = []
    for kw in expected_keywords:
        if kw.lower() in answer_lower:
            found.append(kw)
        else:
            missing.append(kw)

    forbidden_found = []
    if must_not_contain:
        for kw in must_not_contain:
            if kw.lower() in answer_lower:
                forbidden_found.append(kw)

    return {
        'found': found,
        'missing': missing,
        'forbidden_found': forbidden_found,
        'pass': len(missing) == 0 and len(forbidden_found) == 0,
    }


# ===== TEST CASES =====
TESTS = [
    {
        'id': 1,
        'category': '数值精度',
        'question': 'X-300无人机的最大飞行时间是多少？',
        'expected': ['38分钟'],
        'forbidden': ['25分钟', '52分钟'],
        'desc': '精确数值提取，不能混淆不同机型',
    },
    {
        'id': 2,
        'category': '条件查询',
        'question': '在B级区域，X-200无人机最大能飞多高？',
        'expected': ['80'],
        'forbidden': ['120'],
        'desc': '需要关联区域等级和机型限制',
    },
    {
        'id': 3,
        'category': '条件查询',
        'question': '如果风速是9m/s，A级区域的最大飞行高度是多少？',
        'expected': ['84'],
        'forbidden': ['120'],
        'desc': '需要应用风速降低30%的规则',
    },
    {
        'id': 4,
        'category': '否定/排除',
        'question': 'X-200无人机能否在夜间飞行？',
        'expected': ['不能', '不允许', '不支持', '仅限X-500', '仅X-500'],
        'forbidden': ['可以', '能够'],
        'desc': '夜间飞行仅限X-500和X-700',
    },
    {
        'id': 5,
        'category': '版本对比',
        'question': 'V3.2版本中，夜间飞行的审批权限归谁？',
        'expected': ['运营经理'],
        'forbidden': ['总经理'],
        'desc': 'V3.1是总经理，V3.2改为运营经理',
    },
    {
        'id': 6,
        'category': '枚举型',
        'question': '公司有哪些无人机型号？请列举所有型号。',
        'expected': ['X-200', 'X-300', 'X-500', 'X-700'],
        'forbidden': [],
        'desc': '需要列举全部四个型号',
    },
    {
        'id': 7,
        'category': '表格数据',
        'question': 'X-500的IP防护等级是多少？',
        'expected': ['IP55'],
        'forbidden': ['IP43', 'IP54'],
        'desc': '从表格中提取特定单元格数据',
    },
    {
        'id': 8,
        'category': '跨页面关联',
        'question': '夜间飞行时，X-500的最大飞行高度是多少？',
        'expected': ['60', '50%'],
        'forbidden': ['120'],
        'desc': '需要关联夜间飞行规定（高度降50%）和X-500的区域限制',
    },
    {
        'id': 9,
        'category': '应急响应',
        'question': '电池电量低于多少时需要立即降落？',
        'expected': ['20%'],
        'forbidden': ['35%'],
        'desc': '一级响应是20%，二级响应是35%，需要区分',
    },
    {
        'id': 10,
        'category': '资质管理',
        'question': '中级操作员可以操作哪些机型？',
        'expected': ['X-200', 'X-300'],
        'forbidden': ['X-500', 'X-700'],
        'desc': '从资质表格中提取',
    },
    {
        'id': 11,
        'category': '隐含推理',
        'question': 'X-700目前可以用于商业运营吗？',
        'expected': ['不能', '不可以', '不允许', '严禁', '研发'],
        'forbidden': ['可以', '能够'],
        'desc': '需要推理：研发中 + 无适航证 = 不能商业运营',
    },
    {
        'id': 12,
        'category': '维护规程',
        'question': '螺旋桨多少小时需要更换？',
        'expected': ['100'],
        'forbidden': ['300', '50'],
        'desc': '消耗件100小时更换，与电池300次不同',
    },
    {
        'id': 13,
        'category': '边界条件',
        'question': 'X-300在小雨天气下可以飞行吗？',
        'expected': ['可以', '能', '小雨可飞'],
        'forbidden': ['不能', '禁止'],
        'desc': 'X-300降水条件为"小雨可飞"',
    },
    {
        'id': 14,
        'category': '多条件组合',
        'question': '一个初级操作员能否在B级区域飞行X-300？为什么？',
        'expected': ['不能', '不可以'],
        'forbidden': ['可以'],
        'desc': '初级操作员仅允许X-200 + 仅A级区域，两个条件都不满足',
    },
    {
        'id': 15,
        'category': '法规引用',
        'question': '公司的无人机管理需要遵守什么法规？',
        'expected': ['民用无人驾驶航空器飞行管理暂行条例'],
        'forbidden': [],
        'desc': '法规名称的精确引用',
    },
    {
        'id': 16,
        'category': '表格数据',
        'question': 'X-500的采购价格是多少？',
        'expected': ['42,000', '42000'],
        'forbidden': ['8,500', '18,200', '85,000'],
        'desc': '精确定位表格中X-500的价格',
    },
    {
        'id': 17,
        'category': '否定问题',
        'question': 'X-200能否在降水天气飞行？',
        'expected': ['不能', '禁止', '不可以'],
        'forbidden': ['可以', '能'],
        'desc': 'X-200降水条件为"禁止"',
    },
    {
        'id': 18,
        'category': '条件推理',
        'question': '操作员资质被降级后，如何恢复原等级？',
        'expected': ['重新参加培训', '通过考核'],
        'forbidden': [],
        'desc': '需要找到降级恢复条款',
    },
    {
        'id': 19,
        'category': '跨页面关联',
        'question': '在海拔500米的山顶起飞，A级区域最大能飞到海拔多少米？',
        'expected': ['620'],
        'forbidden': ['120', '500'],
        'desc': '需要理解AGL规则：500+120=620',
    },
    {
        'id': 20,
        'category': '继续教育',
        'question': '操作员每年需要完成多少学时的继续教育？其中实操训练不少于多少学时？',
        'expected': ['24', '16'],
        'forbidden': [],
        'desc': '两个数值都需要准确回答',
    },
]


def run_tests():
    """Run all test cases and produce a report."""
    print('=' * 70)
    print('Nova-RAG Enterprise Knowledge Base Test')
    print(f'Document: enterprise_test_doc.pdf (doc_id: {DOC_ID})')
    print(f'Total test cases: {len(TESTS)}')
    print('=' * 70)

    results = []
    total_time = 0

    for tc in TESTS:
        print(f'\n[{tc["id"]:02d}] [{tc["category"]}] {tc["question"]}')
        print(f'     {tc["desc"]}')

        resp = ask_question(tc['question'], doc_id=DOC_ID)
        total_time += resp['time']

        if resp['error']:
            print(f'     ERROR: {resp["error"]}')
            results.append({**tc, 'result': 'ERROR', 'time': resp['time'], 'detail': resp['error']})
            continue

        check = check_answer(resp['answer'], tc['expected'], tc.get('forbidden'))

        status = 'PASS' if check['pass'] else 'FAIL'
        print(f'     [{status}] ({resp["time"]}s)')
        print(f'     Answer: {resp["answer"][:200]}...' if len(resp['answer']) > 200 else f'     Answer: {resp["answer"]}')

        if check['missing']:
            print(f'     Missing keywords: {check["missing"]}')
        if check['forbidden_found']:
            print(f'     Forbidden keywords found: {check["forbidden_found"]}')
        if check['found']:
            print(f'     Found keywords: {check["found"]}')

        results.append({
            **tc,
            'result': status,
            'time': resp['time'],
            'answer': resp['answer'],
            'found': check['found'],
            'missing': check['missing'],
            'forbidden_found': check['forbidden_found'],
        })

    # Summary
    passed = sum(1 for r in results if r['result'] == 'PASS')
    failed = sum(1 for r in results if r['result'] == 'FAIL')
    errors = sum(1 for r in results if r['result'] == 'ERROR')

    print('\n' + '=' * 70)
    print('SUMMARY')
    print('=' * 70)
    print(f'Passed:  {passed}/{len(TESTS)} ({passed/len(TESTS)*100:.1f}%)')
    print(f'Failed:  {failed}/{len(TESTS)}')
    print(f'Errors:  {errors}/{len(TESTS)}')
    print(f'Avg time: {total_time/len(TESTS):.1f}s')
    print(f'Total time: {total_time:.1f}s')

    # Failed details
    if failed > 0:
        print('\nFAILED TESTS:')
        for r in results:
            if r['result'] == 'FAIL':
                print(f'  [{r["id"]:02d}] {r["question"]}')
                if r['missing']:
                    print(f'       Missing: {r["missing"]}')
                if r['forbidden_found']:
                    print(f'       Forbidden found: {r["forbidden_found"]}')
                print(f'       Answer: {r.get("answer", "")[:150]}')

    # Category breakdown
    categories = {}
    for r in results:
        cat = r['category']
        categories.setdefault(cat, {'pass': 0, 'fail': 0})
        if r['result'] == 'PASS':
            categories[cat]['pass'] += 1
        else:
            categories[cat]['fail'] += 1

    print('\nCATEGORY BREAKDOWN:')
    for cat, stats in sorted(categories.items()):
        total = stats['pass'] + stats['fail']
        print(f'  {cat}: {stats["pass"]}/{total}')

    return results


if __name__ == '__main__':
    results = run_tests()
