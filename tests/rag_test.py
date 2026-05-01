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
                "什么是 Pod？",
                "Kubernetes 中 Service 的作用是什么？",
                "ConfigMap 和 Secret 的区别是什么？",
            ],
        },
        # 场景2: 表格数据理解
        {
            "category": "表格数据理解",
            "questions": [
                "kubectl get pods 的常用参数有哪些？",
                "Kubernetes 支持哪些 Volume 类型？",
            ],
        },
        # 场景3: 否定问题（应该回答"未找到"）
        {
            "category": "否定问题",
            "questions": [
                "Kubernetes 的创始人是谁？",
                "Kubernetes 2.0 有什么新特性？",
            ],
        },
        # 场景4: 多轮对话
        {
            "category": "多轮对话",
            "conversations": [
                [
                    "什么是 Deployment？",
                    "它和 StatefulSet 有什么区别？",
                    "什么场景下应该用 StatefulSet？",
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
    print("Nova-RAG 质量测试")
    print("=" * 60)

    for test_group in test_cases:
        category = test_group["category"]
        print(f"\n📋 测试类别: {category}")
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
    print("📊 测试结果总结")
    print("=" * 60)
    print(f"总问题数: {results['total_questions']}")
    print(f"成功检索: {results['successful_retrievals']}")
    print(f"正确回答: {results['correct_answers']}")
    print(f"检测到幻觉: {results['hallucination_detected']}")

    if results["total_questions"] > 0:
        retrieval_rate = results["successful_retrievals"] / results["total_questions"] * 100
        accuracy_rate = results["correct_answers"] / results["total_questions"] * 100
        print(f"检索成功率: {retrieval_rate:.1f}%")
        print(f"回答准确率: {accuracy_rate:.1f}%")

    return results


def test_single_question(question: str, doc_id: Optional[str] = None) -> dict:
    """测试单个问题"""
    print(f"\n❓ 问题: {question}")

    payload = {
        "messages": [{"role": "user", "content": question}],
        "stream": False,
    }
    if doc_id:
        payload["doc_ids"] = [doc_id]

    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE}/chat/completions",
            json=payload,
            timeout=30,
        )
        elapsed = time.time() - start_time

        if response.status_code != 200:
            print(f"  ❌ API 错误: {response.status_code}")
            return {
                "question": question,
                "retrieved": False,
                "quality": "error",
                "elapsed": elapsed,
            }

        # 解析 SSE 响应
        answer = ""
        references = []
        for line in response.text.split("\n"):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "answer":
                        answer += data.get("content", "")
                    if data.get("done"):
                        references = data.get("references", [])
                except json.JSONDecodeError:
                    pass

        # 评估结果
        retrieved = len(references) > 0
        quality = evaluate_answer_quality(question, answer, references)

        print(f"  ⏱️  耗时: {elapsed:.2f}s")
        print(f"  📚 检索到: {len(references)} 个片段")
        print(f"  ✅ 质量: {quality}")
        print(f"  💬 回答: {answer[:200]}...")

        return {
            "question": question,
            "answer": answer,
            "references": len(references),
            "retrieved": retrieved,
            "quality": quality,
            "elapsed": elapsed,
        }

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return {
            "question": question,
            "retrieved": False,
            "quality": "error",
            "error": str(e),
        }


def test_multi_turn(questions: list, doc_id: Optional[str] = None) -> dict:
    """测试多轮对话"""
    print(f"\n🔄 多轮对话测试")
    messages = []
    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n  第 {i} 轮: {question}")
        messages.append({"role": "user", "content": question})

        payload = {
            "messages": messages[-5:],  # 最近 5 轮
            "stream": False,
        }
        if doc_id:
            payload["doc_ids"] = [doc_id]

        try:
            response = requests.post(
                f"{API_BASE}/chat/completions",
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                answer = ""
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "answer":
                                answer += data.get("content", "")
                        except json.JSONDecodeError:
                            pass

                messages.append({"role": "assistant", "content": answer})
                print(f"  💬 回答: {answer[:150]}...")
                results.append({"question": question, "answer": answer})

        except Exception as e:
            print(f"  ❌ 错误: {e}")

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
