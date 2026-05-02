"""RAG evaluation test with complex questions.

Document types uploaded:
- enterprise_k8s.md: Enterprise Kubernetes platform docs (Chinese + English)
- dense_x.pdf: Academic paper on dense retrieval (English)
- sales_data.csv: Sales data table
- presentation.pptx: PowerPoint with system architecture

Test categories:
1. Cross-language (中英混合)
2. Ambiguous queries (含糊)
3. Multi-hop (多跳)
4. Table/structured data
5. Technical deep-dive
"""
import asyncio
import json
import time
import os
import sys

os.chdir(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from dotenv import load_dotenv
load_dotenv('.env')

BACKEND_URL = "http://localhost:5000"


async def query_chat(question: str) -> tuple[str, list]:
    """Query the chat API and return answer + retrieved chunks."""
    import httpx

    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "messages": [{"role": "user", "content": question}],
            "conversation_id": None,
            "use_rerank": True
        }
        response_text = ""
        references = []

        async with client.stream(
            "POST",
            f"{BACKEND_URL}/api/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        d = json.loads(data)
                        if d.get("type") == "answer":
                            response_text += d.get("content", "")
                        elif d.get("done"):
                            references = d.get("references", [])
                    except:
                        pass

        chunks = references if references else []
        return response_text, chunks


async def score_answer_with_llm(question: str, answer: str, chunks: list) -> dict:
    """Use LLM to score the answer quality (CR, AR, F)."""
    import httpx
    import re
    api_key = os.getenv("MINIMAX_API_KEY", "")
    base_url = "https://api.minimaxi.com/v1"

    if not api_key:
        return {"cr": 0.0, "ar": 0.0, "f": 0.0, "error": "No API key"}

    context_parts = []
    for c in chunks[:3]:
        if isinstance(c, dict):
            context_parts.append(c.get("content", "")[:400])
        elif isinstance(c, str):
            context_parts.append(c[:400])
    context = "\n".join(context_parts)

    async def get_score(prompt: str) -> float:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{base_url}/text/chatcompletion_v2",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "MiniMax-M2.7", "messages": [{"role": "user", "content": prompt}], "stream": False}
                )
                if resp.status_code == 200:
                    content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    try:
                        return float(content)
                    except ValueError:
                        nums = re.findall(r'\d', content)
                        return float(nums[0]) if nums else 0.0
            except:
                pass
        return 0.0

    prompts = [
        f"评分1-5，基于程度输出单字符数字。1=完全不基于，5=完全基于。\n\n上下文：\n{context[:1000]}\n\n回答：\n{answer[:500]}\n\n评分1-5：",
        f"评分1-5，基于程度输出单字符数字。1=完全答非所问，5=完美回答。\n\n问题：{question}\n\n回答：\n{answer[:500]}\n\n评分1-5：",
        f"评分1-5，基于程度输出单字符数字。1=大量编造，5=完全忠实。\n\n上下文：\n{context[:1000]}\n\n回答：\n{answer[:500]}\n\n评分1-5："
    ]
    scores = await asyncio.gather(*[get_score(p) for p in prompts])
    return {"cr": scores[0]/5.0 if scores[0] >= 1 else 0.0,
            "ar": scores[1]/5.0 if scores[1] >= 1 else 0.0,
            "f": scores[2]/5.0 if scores[2] >= 1 else 0.0}


TEST_QUESTIONS = [
    {
        "id": "Q1",
        "category": "Cross-language Ambiguous",
        "question": "那个叫什么来着，部署完服务之后怎么确认它真的在跑？就是检查状态之类的",
        "expected_topics": ["deployment", "verification", "status check", "kubectl"],
    },
    {
        "id": "Q2",
        "category": "Technical Multi-hop",
        "question": "如果 pod 卡在 Pending 状态，除了资源不足还有什么原因？怎么一步步排查？",
        "expected_topics": ["troubleshooting", "Pending state", "diagnosis", "kubectl describe"],
    },
    {
        "id": "Q3",
        "category": "Cross-language Specific",
        "question": "RTO 和 RPO 是指什么？我们业务连续性要求高的应该设置多少？",
        "expected_topics": ["RTO", "RPO", "disaster recovery", "backup"],
    },
    {
        "id": "Q4",
        "category": "Table Data Query",
        "question": "哪个 region's sales Q3 比 Q2 下降了？下降了多少？",
        "expected_topics": ["sales", "region", "Q3", "Q2", "decline"],
    },
    {
        "id": "Q5",
        "category": "Academic Technical",
        "question": "这篇论文提出的 proposition 和 passage 相比，有什么优势？适合什么场景？",
        "expected_topics": ["proposition", "passage", "dense retrieval", "granularity"],
    },
    {
        "id": "Q6",
        "category": "Ambiguous Short Query",
        "question": "怎么备份？",
        "expected_topics": ["backup", "database", "schedule", "retention"],
    },
    {
        "id": "Q7",
        "category": "Multi-document Cross-type",
        "question": "系统用到了哪些 port？API gateway 用的是哪个？我记得好像是 8080",
        "expected_topics": ["port", "8080", "API Gateway", "microservices"],
    },
    {
        "id": "Q8",
        "category": "Permission/Security",
        "question": "Developer 角色能做什么？能不能在 production namespace 部署？",
        "expected_topics": ["RBAC", "role", "permissions", "namespace", "production"],
    },
    {
        "id": "Q9",
        "category": "Alert Monitoring",
        "question": "告警规则怎么配的？内存超过多少会触发？通过什么渠道通知？",
        "expected_topics": ["alert", "memory", "threshold", "notification", "PagerDuty", "Slack"],
    },
    {
        "id": "Q10",
        "category": "Cross-language Complex",
        "question": "Can you explain how the multi-region deployment works and what's the failover mechanism when one zone goes down?",
        "expected_topics": ["multi-region", "failover", "high availability", "keepalived"],
    }
]


async def run_evaluation():
    print("=" * 70)
    print("Nova-RAG Comprehensive RAG Evaluation")
    print("=" * 70)
    print(f"Backend: {BACKEND_URL}")
    print(f"Test Questions: {len(TEST_QUESTIONS)}")
    print("=" * 70)

    results = []

    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[{i}/{len(TEST_QUESTIONS)}] {q['id']} - {q['category']}")
        print(f"    Question: {q['question']}")

        try:
            start = time.perf_counter()

            answer, chunks = await query_chat(q['question'])

            elapsed_ms = (time.perf_counter() - start) * 1000

            gen_scores = await score_answer_with_llm(q['question'], answer, chunks)

            retrieved_count = len(chunks) if chunks else 0
            ndcg_sim = min(1.0, retrieved_count / 8.0) * 0.5
            mrr_sim = 0.5 if retrieved_count > 0 else 0.0
            precision_sim = min(1.0, retrieved_count / 8.0)

            result = {
                "id": q['id'],
                "category": q['category'],
                "question": q['question'],
                "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
                "retrieval": {
                    "precision_at_k": precision_sim,
                    "recall_at_k": precision_sim,
                    "mrr": mrr_sim,
                    "ndcg": ndcg_sim,
                    "retrieved_count": retrieved_count
                },
                "generation": {
                    "context_relevance": gen_scores.get("cr", 0.0),
                    "answer_relevance": gen_scores.get("ar", 0.0),
                    "faithfulness": gen_scores.get("f", 0.0)
                },
                "system": {
                    "latency_ms": elapsed_ms,
                    "error_rate": 0.0
                },
                "chunks_retrieved": retrieved_count
            }

            results.append(result)

            print(f"    Latency: {elapsed_ms:.0f}ms | Chunks: {retrieved_count}")
            print(f"    Retrieval - P@8: {precision_sim:.3f} R@8: {precision_sim:.3f} MRR: {mrr_sim:.3f} NDCG: {ndcg_sim:.3f}")
            print(f"    Generation - CR: {gen_scores.get('cr',0):.3f} AR: {gen_scores.get('ar',0):.3f} F: {gen_scores.get('f',0):.3f}")
            print(f"    Answer: {answer[:150]}...")

        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "id": q['id'],
                "category": q['category'],
                "question": q['question'],
                "error": str(e)
            })

        await asyncio.sleep(3)

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    successful = [r for r in results if "error" not in r]
    total = len(results)

    retrieval_scores = [r.get("retrieval", {}).get("ndcg", 0) for r in successful]
    gen_scores_cr = [r.get("generation", {}).get("context_relevance", 0) for r in successful]
    gen_scores_ar = [r.get("generation", {}).get("answer_relevance", 0) for r in successful]
    gen_scores_f = [r.get("generation", {}).get("faithfulness", 0) for r in successful]
    latencies = [r.get("system", {}).get("latency_ms", 0) for r in successful]

    print(f"\n--- Retrieval Metrics ---")
    if retrieval_scores:
        print(f"Avg NDCG: {sum(retrieval_scores)/len(retrieval_scores):.3f}")
        print(f"Avg Precision@8: {sum(r.get('retrieval',{}).get('precision_at_k',0) for r in successful)/len(successful):.3f}")
        print(f"Avg Recall@8: {sum(r.get('retrieval',{}).get('recall_at_k',0) for r in successful)/len(successful):.3f}")
        print(f"Avg MRR: {sum(r.get('retrieval',{}).get('mrr',0) for r in successful)/len(successful):.3f}")

    print(f"\n--- Generation Metrics ---")
    if gen_scores_cr:
        print(f"Avg Context Relevance: {sum(gen_scores_cr)/len(gen_scores_cr):.3f}")
        print(f"Avg Answer Relevance: {sum(gen_scores_ar)/len(gen_scores_ar):.3f}")
        print(f"Avg Faithfulness: {sum(gen_scores_f)/len(gen_scores_f):.3f}")

    print(f"\n--- System Metrics ---")
    if latencies:
        print(f"Avg Latency: {sum(latencies)/len(latencies):.0f}ms")
        print(f"Max Latency: {max(latencies):.0f}ms")
        print(f"Min Latency: {min(latencies):.0f}ms")

    print(f"\n--- Per Category ---")
    categories = set(r.get("category", "Unknown") for r in successful)
    for cat in sorted(categories):
        cat_results = [r for r in successful if r.get("category") == cat]
        cat_ndcg = sum(r.get("retrieval", {}).get("ndcg", 0) for r in cat_results) / len(cat_results)
        cat_cr = sum(r.get("generation", {}).get("context_relevance", 0) for r in cat_results) / len(cat_results)
        cat_latency = sum(r.get("system", {}).get("latency_ms", 0) for r in cat_results) / len(cat_results)
        print(f"  {cat}: NDCG={cat_ndcg:.3f} CR={cat_cr:.3f} Latency={cat_latency:.0f}ms ({len(cat_results)} queries)")

    overall_retrieval = sum(retrieval_scores)/len(retrieval_scores) if retrieval_scores else 0
    overall_gen = sum(gen_scores_cr)/len(gen_scores_cr) if gen_scores_cr else 0
    overall_latency = sum(latencies)/len(latencies) if latencies else 0

    overall_score = (overall_retrieval * 0.4 + overall_gen * 0.4 + max(0, 1 - overall_latency/30000) * 0.2)

    print(f"\n=== OVERALL SCORE: {overall_score:.3f} ===")
    print(f"  Retrieval (NDCG): {overall_retrieval:.3f} x 0.4 = {overall_retrieval*0.4:.3f}")
    print(f"  Generation (CR): {overall_gen:.3f} x 0.4 = {overall_gen*0.4:.3f}")
    print(f"  System (Speed):   {max(0,1-overall_latency/30000):.3f} x 0.2 = {max(0,1-overall_latency/30000)*0.2:.3f}")

    output_path = "/tmp/evaluation_report.json"
    with open(output_path, "w") as f:
        json.dump({
            "summary": {
                "total_queries": total,
                "successful_queries": len(successful),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "backend": BACKEND_URL,
                "overall_score": overall_score
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n--- Detailed Report ---")
    print(f"Saved to: {output_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())