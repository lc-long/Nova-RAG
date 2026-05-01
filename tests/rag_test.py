"""
Nova-RAG 测试方案

测试文档要求：
1. 下载一份公开的技术文档（如 Kubernetes 官方文档、Python 官方文档等）
2. 上传到系统中
3. 运行测试脚本评估 RAG 效果

测试场景覆盖：
- 精确信息提取（事实性问题）
- 多文档关联（跨段落推理）
- 表格数据理解
- 否定问题（文档中不存在的信息）
- 多轮对话上下文
"""

import requests
import json
import time
from typing import Optional

API_BASE = "http://localhost:5000/api/v1"


def test_rag_quality(doc_id: Optional[str] = None):
    """测试 RAG 系统质量"""

    test_cases = [
        # 场景1: 精确信息提取
        {
            "category": "精确信息提取",
            "questions": [
                "星辰科技是什么时候成立的？",
                "公司注册资本是多少？",
                "公司有多少员工？",
            ],
        },
        # 场景2: 表格数据理解
        {
            "category": "表格数据理解",
            "questions": [
                "公司有哪些核心产品？",
                "智能客服Pro的用户数是多少？",
                "技术栈中前端用了什么？",
            ],
        },
        # 场景3: 否定问题（应该回答"未找到"）
        {
            "category": "否定问题",
            "questions": [
                "公司的竞争对手有哪些？",
                "公司的年营收是多少？",
            ],
        },
        # 场景4: 多轮对话
        {
            "category": "多轮对话",
            "conversations": [
                [
                    "公司有几个部门？",
                    "研发部有多少人？",
                    "研发部的总监是谁？",
                ]
            ],
        },
    ]

    results = {
        "total_questions": 0,
        "successful_retrievals": 0,
        "correct_answers": 0,
        "hallucination_detected": 0,
        "details": [],
    }

    print("=" * 60)
    print("Nova-RAG Quality Test")
    print("=" * 60)

    for test_group in test_cases:
        category = test_group["category"]
        print(f"\nCategory: {category}")
        print("-" * 40)

        if "questions" in test_group:
            for question in test_group["questions"]:
                result = test_single_question(question, doc_id)
                results["total_questions"] += 1
                if result["retrieved"]:
                    results["successful_retrievals"] += 1
                if result["quality"] == "good":
                    results["correct_answers"] += 1
                elif result["quality"] == "hallucination":
                    results["hallucination_detected"] += 1
                results["details"].append(result)

        elif "conversations" in test_group:
            for conversation in test_group["conversations"]:
                result = test_multi_turn(conversation, doc_id)
                results["total_questions"] += len(conversation)
                results["details"].append(result)

    # 打印总结
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Total Questions: {results['total_questions']}")
    print(f"Successful Retrievals: {results['successful_retrievals']}")
    print(f"Correct Answers: {results['correct_answers']}")
    print(f"Hallucinations Detected: {results['hallucination_detected']}")

    if results["total_questions"] > 0:
        retrieval_rate = results["successful_retrievals"] / results["total_questions"] * 100
        accuracy_rate = results["correct_answers"] / results["total_questions"] * 100
        print(f"Retrieval Rate: {retrieval_rate:.1f}%")
        print(f"Accuracy Rate: {accuracy_rate:.1f}%")

    return results


def test_single_question(question: str, doc_id: Optional[str] = None) -> dict:
    """测试单个问题"""
    print(f"\nQ: {question}")

    payload = {
        "messages": [{"role": "user", "content": question}],
        "stream": True,
    }
    if doc_id:
        payload["doc_ids"] = [doc_id]

    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE}/chat/completions",
            json=payload,
            stream=True,
            timeout=60,
        )
        elapsed = time.time() - start_time

        if response.status_code != 200:
            print(f"  [ERROR] API Error: {response.status_code}")
            return {
                "question": question,
                "retrieved": False,
                "quality": "error",
                "elapsed": elapsed,
            }

        # 解析 SSE 响应
        answer = ""
        references = []
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
                if data.get("type") == "answer":
                    answer += data.get("content", "")
                if data.get("type") == "reasoning":
                    pass  # Skip reasoning for now
                if data.get("done"):
                    references = data.get("references", [])
            except json.JSONDecodeError:
                pass

        elapsed = time.time() - start_time

        # 评估结果
        retrieved = len(references) > 0
        quality = evaluate_answer_quality(question, answer, references)

        print(f"  Time: {elapsed:.2f}s")
        print(f"  Retrieved: {len(references)} chunks")
        print(f"  Quality: {quality}")
        print(f"  Answer: {answer[:200]}...")

        return {
            "question": question,
            "answer": answer,
            "references": len(references),
            "retrieved": retrieved,
            "quality": quality,
            "elapsed": elapsed,
        }

    except Exception as e:
        print(f"  [ERROR] {e}")
        return {
            "question": question,
            "retrieved": False,
            "quality": "error",
            "error": str(e),
        }


def test_multi_turn(questions: list, doc_id: Optional[str] = None) -> dict:
    """测试多轮对话"""
    print(f"\nMulti-turn Test")
    messages = []
    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n  Turn {i}: {question}")
        messages.append({"role": "user", "content": question})

        payload = {
            "messages": messages[-5:],  # 最近 5 轮
            "stream": True,
        }
        if doc_id:
            payload["doc_ids"] = [doc_id]

        try:
            response = requests.post(
                f"{API_BASE}/chat/completions",
                json=payload,
                stream=True,
                timeout=60,
            )

            if response.status_code == 200:
                answer = ""
                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "answer":
                            answer += data.get("content", "")
                    except json.JSONDecodeError:
                        pass

                messages.append({"role": "assistant", "content": answer})
                print(f"  Answer: {answer[:150]}...")
                results.append({"question": question, "answer": answer})

        except Exception as e:
            print(f"  [ERROR] {e}")

    return {
        "type": "multi_turn",
        "turns": len(questions),
        "results": results,
    }


def evaluate_answer_quality(question: str, answer: str, references: list) -> str:
    """评估回答质量（简单规则）"""
    answer_lower = answer.lower()

    # 检查是否承认不知道
    denial_phrases = [
        "未找到", "没有找到", "无法找到", "not found",
        "不知道", "无法回答", "没有相关信息", "不在文档中",
    ]
    has_denial = any(phrase in answer_lower for phrase in denial_phrases)

    # 检查是否有引用
    has_references = len(references) > 0

    # 检查回答长度
    is_too_short = len(answer) < 20
    is_reasonable = 50 < len(answer) < 2000

    # 评估逻辑
    if has_references and is_reasonable:
        return "good"
    elif has_denial and not has_references:
        return "good"  # 正确承认不知道
    elif is_too_short:
        return "too_short"
    elif not has_references and len(answer) > 100:
        return "hallucination"  # 没有引用但回答很长，可能是幻觉
    else:
        return "acceptable"


if __name__ == "__main__":
    import sys

    doc_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not doc_id:
        print("用法: python rag_test.py <doc_id>")
        print("提示: 先上传文档获取 doc_id")
        print("\n测试将使用全局检索模式")
    
    test_rag_quality(doc_id)
