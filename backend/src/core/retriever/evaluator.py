"""RAG evaluation metrics for retrieval, generation, and system performance.

Retrieval Metrics:
- Precision@k, Recall@k, MRR, NDCG

Generation Metrics (LLM-based):
- CR (Context Relevance): Answer grounded in retrieved context
- AR (Answer Relevance): Answer addresses the question
- F (Faithfulness): No hallucination, facts match context

System Metrics:
- Latency, Throughput, Error Rate
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("nova_rag")


@dataclass
class RetrievalMetrics:
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    k: int = 0


@dataclass
class GenerationMetrics:
    context_relevance: float = 0.0
    answer_relevance: float = 0.0
    faithfulness: float = 0.0


@dataclass
class SystemMetrics:
    latency_ms: float = 0.0
    throughput_rps: float = 0.0
    error_rate: float = 0.0


@dataclass
class RAGEvaluationResult:
    retrieval: Optional[RetrievalMetrics] = None
    generation: Optional[GenerationMetrics] = None
    system: Optional[SystemMetrics] = None
    overall_score: float = 0.0


class RAGEvaluator:
    """Comprehensive RAG evaluation across three dimensions."""

    def __init__(self, retriever=None, llm_client=None, embedder=None):
        self.retriever = retriever
        self.llm_client = llm_client
        self.embedder = embedder
        self._http_client = None

    async def evaluate_retrieval(
        self,
        query: str,
        relevant_doc_ids: list[str],
        k: int = 8,
    ) -> RetrievalMetrics:
        """Evaluate retrieval quality.

        Args:
            query: User query
            relevant_doc_ids: Ground truth relevant document IDs
            k: Top-k results to evaluate

        Returns:
            RetrievalMetrics with Precision@k, Recall@k, MRR, NDCG
        """
        if not self.retriever:
            logger.warning("[Evaluator] No retriever configured, skipping retrieval eval")
            return RetrievalMetrics(k=k)

        try:
            results = await self.retriever.retrieve(query, top_k=k)

            retrieved_ids = [r.get("doc_id", "") for r in results]

            precision, recall = self._precision_recall(retrieved_ids, relevant_doc_ids)
            mrr = self._mrr(retrieved_ids, relevant_doc_ids)
            ndcg = self._ndcg(retrieved_ids, relevant_doc_ids)

            return RetrievalMetrics(
                precision_at_k=precision,
                recall_at_k=recall,
                mrr=mrr,
                ndcg=ndcg,
                k=k,
            )
        except Exception as e:
            logger.error(f"[Evaluator] Retrieval eval failed: {e}")
            return RetrievalMetrics(k=k)

    def _precision_recall(self, retrieved: list[str], relevant: list[str]) -> tuple[float, float]:
        """Calculate precision and recall."""
        if not retrieved:
            return 0.0, 0.0
        if not relevant:
            return 0.0, 0.0

        retrieved_set = set(retrieved)
        relevant_set = set(relevant)

        true_positives = len(retrieved_set & relevant_set)
        precision = true_positives / len(retrieved) if retrieved else 0.0
        recall = true_positives / len(relevant_set) if relevant_set else 0.0

        return precision, recall

    def _mrr(self, retrieved: list[str], relevant: list[str]) -> float:
        """Mean Reciprocal Rank - reciprocal of first relevant result rank."""
        relevant_set = set(relevant)
        for i, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant_set:
                return 1.0 / i
        return 0.0

    def _ndcg(self, retrieved: list[str], relevant: list[str], k: int = None) -> float:
        """Normalized Discounted Cumulative Gain."""
        if k is None:
            k = len(retrieved)

        relevant_set = set(relevant)
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k], start=1):
            if doc_id in relevant_set:
                dcg += 1.0 / (i ** 0.5)

        ideal_retrieved = [r for r in relevant if r in retrieved[:k]]
        idcg = sum(1.0 / ((i + 1) ** 0.5) for i in range(len(ideal_retrieved)))

        if idcg == 0:
            return 0.0
        return dcg / idcg

    async def evaluate_generation(
        self,
        query: str,
        context_chunks: list[dict],
        generated_answer: str,
    ) -> GenerationMetrics:
        """Evaluate generation quality using LLM.

        Args:
            query: User query
            context_chunks: Retrieved chunks used as context
            generated_answer: LLM generated answer

        Returns:
            GenerationMetrics with CR, AR, F scores
        """
        if not self.llm_client:
            logger.warning("[Evaluator] No LLM client configured, skipping generation eval")
            return GenerationMetrics()

        context_text = self._build_context(context_chunks)

        try:
            cr = await self._score_context_relevance(query, context_text, generated_answer)
            ar = await self._score_answer_relevance(query, generated_answer)
            f = await self._score_faithfulness(context_text, generated_answer)

            return GenerationMetrics(
                context_relevance=cr,
                answer_relevance=ar,
                faithfulness=f,
            )
        except Exception as e:
            logger.error(f"[Evaluator] Generation eval failed: {e}")
            return GenerationMetrics()

    def _build_context(self, chunks: list[dict]) -> str:
        """Build context string from chunks."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("parent_content", chunk.get("child_content", ""))
            parts.append(f"[{i}] {content}")
        return "\n\n".join(parts)

    async def _score_context_relevance(self, query: str, context: str, answer: str) -> float:
        """Score: Does answer come from context?"""
        prompt = f"""请评估以下回答是否基于提供的上下文信息。

问题：{query}

上下文信息：
{context[:2000]}

回答：
{answer}

请从1-5分评分（1=回答与上下文无关，5=完全基于上下文），只输出数字："""

        score = await self._call_llm_score(prompt)
        return score / 5.0 if score > 0 else 0.0

    async def _score_answer_relevance(self, query: str, answer: str) -> float:
        """Score: Does answer address the question?"""
        prompt = f"""请评估以下回答是否有效回答了用户问题。

问题：{query}

回答：
{answer}

请从1-5分评分（1=完全答非所问，5=完全解决用户问题），只输出数字："""

        score = await self._call_llm_score(prompt)
        return score / 5.0 if score > 0 else 0.0

    async def _score_faithfulness(self, context: str, answer: str) -> float:
        """Score: Any hallucination? Does answer match facts in context?"""
        prompt = f"""请评估以下回答是否存在幻觉（编造了上下文中没有的信息）。

上下文信息：
{context[:2000]}

回答：
{answer}

请从1-5分评分（1=大量编造信息，5=完全忠实于上下文），只输出数字："""

        score = await self._call_llm_score(prompt)
        return score / 5.0 if score > 0 else 0.0

    async def _call_llm_score(self, prompt: str) -> float:
        """Call LLM to get a score."""
        try:
            import httpx
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

            api_key = self.llm_client.api_key if self.llm_client else ""
            base_url = self.llm_client.base_url if self.llm_client else ""

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            payload = {
                "model": "MiniMax-M2.7",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }

            response = await self._http_client.post(
                f"{base_url}/text/chatcompletion_v2",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                return 0.0

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return 0.0

            content = choices[0].get("message", {}).get("content", "").strip()
            try:
                return float(content)
            except ValueError:
                for word in content.split():
                    try:
                        return float(word)
                    except ValueError:
                        continue
                return 0.0

        except Exception as e:
            logger.error(f"[Evaluator] LLM scoring failed: {e}")
            return 0.0

    async def evaluate_system(
        self,
        query: str,
        components,
        num_runs: int = 5,
    ) -> SystemMetrics:
        """Evaluate system performance metrics.

        Args:
            query: Test query
            components: System components (retriever, llm_client)
            num_runs: Number of runs for averaging

        Returns:
            SystemMetrics with latency, throughput, error rate
        """
        latencies = []
        errors = 0

        for _ in range(num_runs):
            try:
                start = time.perf_counter()

                if components.retriever:
                    await components.retriever.retrieve(query, top_k=8)

                if components.llm_client:
                    messages = [type('M', (), {'role': 'user', 'content': query})()]
                    async for _ in components.llm_client.stream_chat(messages, []):
                        pass

                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)

            except Exception as e:
                errors += 1
                logger.warning(f"[Evaluator] System eval run failed: {e}")

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        error_rate = errors / num_runs if num_runs > 0 else 0.0

        return SystemMetrics(
            latency_ms=avg_latency,
            error_rate=error_rate,
        )

    async def evaluate(
        self,
        query: str,
        relevant_doc_ids: list[str],
        context_chunks: list[dict],
        generated_answer: str,
        components,
        k: int = 8,
    ) -> RAGEvaluationResult:
        """Full RAG evaluation across all three dimensions."""
        retrieval = await self.evaluate_retrieval(query, relevant_doc_ids, k)
        generation = await self.evaluate_generation(query, context_chunks, generated_answer)
        system = await self.evaluate_system(query, components, num_runs=3)

        overall = (
            (retrieval.precision_at_k + retrieval.recall_at_k + retrieval.mrr + retrieval.ndcg) / 4 * 0.4 +
            (generation.context_relevance + generation.answer_relevance + generation.faithfulness) / 3 * 0.4 +
            max(0, 1 - system.latency_ms / 10000) * 0.2
        )

        return RAGEvaluationResult(
            retrieval=retrieval,
            generation=generation,
            system=system,
            overall_score=overall,
        )

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()