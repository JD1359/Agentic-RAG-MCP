"""Agentic retrieval loop: plan → search → judge → re-query or answer."""
import json
import logging
import time
from typing import Any

from agentic_rag_mcp.config import settings
from agentic_rag_mcp.llm import call_llm
from agentic_rag_mcp.observability import (
    agent_latency,
    agent_steps,
    agent_token_cost,
)
from agentic_rag_mcp.retrieval import RetrievalHit, hybrid_search

log = logging.getLogger(__name__)


PLANNER_SYSTEM = """You are an information-retrieval planner. Given a user question, decide whether
the provided context already answers it, or whether you need another retrieval step. Output strict JSON:

{
  "decision": "answer" | "search_again" | "give_up",
  "next_query": "<reformulated query>" | null,
  "reason": "<one short sentence>"
}
"""

ANSWERER_SYSTEM = """You are a careful research assistant. Answer the user's question using ONLY
the provided context. Cite sources by chunk ID in square brackets like [chunk_id=42]. If the
context is insufficient, say so explicitly — do not invent facts.
"""


async def agentic_query(
    query: str,
    collection: str,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """
    Run the agentic RAG loop:
      1. Initial retrieval.
      2. Planner judges if context is sufficient.
      3. If not, expand or reformulate the query and retrieve again.
      4. Stop at `max_steps` or when planner says "answer".
      5. Answerer produces final cited response.
    """
    started = time.perf_counter()
    max_steps = max_steps or settings.max_agent_steps

    context_chunks: list[RetrievalHit] = []
    queries_used: list[str] = [query]
    current_query = query

    for step in range(max_steps):
        log.info("agent_step", extra={"step": step, "query": current_query})
        hits = await hybrid_search(query=current_query, collection=collection,
                                   top_k=settings.top_k_rerank)
        context_chunks.extend(hits)

        # If this is the last allowed step, force an answer
        if step == max_steps - 1:
            break

        # Planner decides next move
        planner_msg = _format_planner_prompt(query, context_chunks)
        planner_out = await call_llm(system=PLANNER_SYSTEM, user=planner_msg, json_mode=True)
        try:
            plan = json.loads(planner_out.text)
        except json.JSONDecodeError:
            log.warning("planner_invalid_json", extra={"output": planner_out.text[:200]})
            break

        if plan.get("decision") == "answer":
            break
        if plan.get("decision") == "give_up":
            return {
                "answer": "I don't have enough information in the knowledge base to answer that.",
                "citations": [],
                "steps": step + 1,
                "queries_used": queries_used,
                "verdict": "give_up",
                "reason": plan.get("reason", ""),
            }
        next_q = plan.get("next_query")
        if not next_q or next_q in queries_used:
            break
        current_query = next_q
        queries_used.append(next_q)

    # Deduplicate and rank context chunks
    context_chunks = _dedupe(context_chunks)[: settings.top_k_rerank]

    # Final answer
    answer_msg = _format_answer_prompt(query, context_chunks)
    answer_out = await call_llm(system=ANSWERER_SYSTEM, user=answer_msg, json_mode=False)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    agent_steps.observe(len(queries_used))
    agent_latency.observe(elapsed_ms / 1000.0)
    agent_token_cost.observe(answer_out.cost_usd)

    return {
        "answer": answer_out.text,
        "citations": [
            {"chunk_id": c.chunk_id, "source": c.source, "score": c.score}
            for c in context_chunks
        ],
        "steps": len(queries_used),
        "queries_used": queries_used,
        "latency_ms": elapsed_ms,
        "cost_usd": round(answer_out.cost_usd, 6),
        "verdict": "answered",
    }


def _format_planner_prompt(question: str, chunks: list[RetrievalHit]) -> str:
    ctx = "\n\n".join(
        f"[chunk_id={c.chunk_id}] (score={c.score:.3f}, source={c.source})\n{c.text[:500]}"
        for c in chunks[-10:]
    )
    return f"USER QUESTION:\n{question}\n\nRETRIEVED CONTEXT (most recent first):\n{ctx}"


def _format_answer_prompt(question: str, chunks: list[RetrievalHit]) -> str:
    ctx = "\n\n".join(
        f"[chunk_id={c.chunk_id}] (source={c.source})\n{c.text}"
        for c in chunks
    )
    return f"QUESTION:\n{question}\n\nCONTEXT:\n{ctx}\n\nAnswer the question using only the context. Cite chunk IDs."


def _dedupe(chunks: list[RetrievalHit]) -> list[RetrievalHit]:
    seen = set()
    out = []
    for c in sorted(chunks, key=lambda x: x.score, reverse=True):
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        out.append(c)
    return out
