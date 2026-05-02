"""RAG evaluation test script.

Usage:
    cd tests && python test_rag_evaluation.py

Requirements:
    - Backend running at http://localhost:5000
    - At least one document uploaded and indexed
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.src.core.retriever.evaluator import RAGEvaluator


SAMPLE_QUERIES = [
    {
        "query": "什么是企业知识库？",
        "relevant_doc_ids": [],  # Fill in with actual relevant doc IDs after retrieval
    },
    {
        "query": "如何配置系统参数？",
        "relevant_doc_ids": [],
    },
    {
        "query": "上传文档的流程是什么？",
        "relevant_doc_ids": [],
    },
]


async def run_evaluation():
    print("=" * 60)
    print("Nova-RAG Evaluation Test")
    print("=" * 60)

    evaluator = RAGEvaluator()

    results = []
    for i, sample in enumerate(SAMPLE_QUERIES, 1):
        print(f"\n[Test {i}/{len(SAMPLE_QUERIES)}] Query: {sample['query']}")

        try:
            result = await evaluator.evaluate(
                query=sample["query"],
                relevant_doc_ids=sample["relevant_doc_ids"],
                context_chunks=[],
                generated_answer="",
                components=None,
            )

            if result.retrieval:
                print(f"  Retrieval - P@{result.retrieval.k}: {result.retrieval.precision_at_k:.3f}")
                print(f"  Retrieval - R@{result.retrieval.k}: {result.retrieval.recall_at_k:.3f}")
                print(f"  Retrieval - MRR: {result.retrieval.mrr:.3f}")
                print(f"  Retrieval - NDCG: {result.retrieval.ndcg:.3f}")

            if result.generation:
                print(f"  Generation - CR: {result.generation.context_relevance:.3f}")
                print(f"  Generation - AR: {result.generation.answer_relevance:.3f}")
                print(f"  Generation - F: {result.generation.faithfulness:.3f}")

            if result.system:
                print(f"  System - Latency: {result.system.latency_ms:.1f}ms")
                print(f"  System - Error Rate: {result.system.error_rate:.1%}")

            print(f"  Overall Score: {result.overall_score:.3f}")
            results.append(result)

        except Exception as e:
            print(f"  ERROR: {e}")

    if results:
        avg_overall = sum(r.overall_score for r in results) / len(results)
        print(f"\n{'=' * 60}")
        print(f"Average Overall Score: {avg_overall:.3f}")
        print(f"{'=' * 60}")

    await evaluator.close()


if __name__ == "__main__":
    asyncio.run(run_evaluation())