"""One-shot installer for the missing files (seed docs, run_demo, mock LLM, etc).

Run this from your agentic-rag-mcp project root:

    py setup_missing.py

It writes (or overwrites):
  - seed/sample_docs/01_distributed_systems.md
  - seed/sample_docs/02_model_context_protocol.md
  - seed/sample_docs/03_retrieval_augmented_generation.md
  - seed/sample_docs/04_agentic_patterns.md
  - examples/run_demo.py
  - src/agentic_rag_mcp/auth.py
  - src/agentic_rag_mcp/llm.py        (overwritten — adds mock provider)
  - src/agentic_rag_mcp/embeddings.py (overwritten — stable hash fallback)
  - eval/golden_set.jsonl             (overwritten — 20 Qs keyed to seed docs)
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FILES: dict[str, str] = {}

# ---- seed docs ----

FILES["seed/sample_docs/01_distributed_systems.md"] = r"""# Distributed Systems Fundamentals

## At-least-once vs exactly-once delivery

In any distributed messaging system, you have to choose a delivery semantic.
**At-most-once** delivery means messages can be lost but never duplicated.
**At-least-once** delivery means messages will be delivered one or more times -
duplicates are possible but messages are never lost. **Exactly-once** delivery
means each message is delivered exactly one time.

In practice, exactly-once delivery across an unreliable channel like SMTP or SMS
is impossible. The achievable contract is at-least-once delivery combined with
idempotency on the receiver side. The client supplies an idempotency key, and
the server uses that key to deduplicate retries.

## Dead-letter queues (DLQ)

A dead-letter queue holds messages that have failed processing beyond a
configured retry budget. Without a DLQ, a single bad payload can wedge a worker
pool indefinitely. With a DLQ, after N failed attempts the message moves to the
dead-letter stream for manual inspection, allowing the rest of the pipeline to
continue.

A typical configuration is 3 retry attempts with exponential backoff: 5 seconds,
25 seconds, 125 seconds. After the third failure the message is dead-lettered.

## Redis Streams and consumer groups

Redis Streams are an append-only log primitive in Redis. Unlike Redis Lists,
Streams support consumer groups: multiple consumers can read from the same
stream in parallel, with each message delivered to exactly one consumer in the
group. Consumer groups also track pending messages that have been delivered but
not acknowledged, enabling automatic claim of abandoned work.

This makes Redis Streams a better choice than List + LPOP for production work
queues.

## Per-channel rate limiting

A common mistake is to apply a single global rate limit across all output
channels. In a notification system sending email via SendGrid (~100 req/s) and
SMS via Twilio (~10 req/s), a global limit must be set to the most restrictive
channel, starving the faster ones. Per-channel rate limiting with separate
token buckets allows each channel to operate at its maximum throughput.

## Graceful shutdown

The correct sequence on SIGTERM is:
1. Stop accepting new requests (close the listener).
2. Drain in-flight work (allow workers to finish their current job).
3. Close database and queue connections.
4. Flush logs and metrics.
5. Exit.

Done incorrectly you lose in-flight messages on every deploy.
"""

FILES["seed/sample_docs/02_model_context_protocol.md"] = r"""# Model Context Protocol (MCP)

## What is MCP?

Model Context Protocol is an open standard published by Anthropic in November
2024 for connecting AI models to tools and data. It defines a JSON-RPC-based
protocol over either standard input/output (stdio) or Server-Sent Events (SSE).
MCP servers expose **tools** (function-call-like operations), **resources**
(read-only data sources), and **prompts** (reusable prompt templates).

MCP is supported by Claude Desktop, Cursor, Cline, Continue, Zed, and Windsurf.

## Why stdio is the right default transport

The stdio transport runs the MCP server as a child process of the client
application. Communication is via stdin/stdout JSON-RPC frames. This is the
right default because: it requires no network configuration, gives the client
process-level isolation of the server, and works identically across operating
systems.

SSE is the right choice for remote/team deployments. SSE adds the complexity of
authentication and network setup but unlocks multi-tenant use cases.

## Tool definitions

Each MCP tool is defined with a unique name, a human-readable description, and
a JSON Schema for its input. The description matters more than developers
typically expect - the LLM uses it to decide when to call the tool. A vague
description like "search docs" produces fewer correct invocations than a
specific one like "hybrid vector and BM25 search over an ingested knowledge
collection, returning top-k chunks with scores."

## Comparison to OpenAI function calling

OpenAI's function-calling API is per-vendor and per-request: each chat request
includes the function definitions. MCP is host-application-level: tools are
registered with the host once, and every subsequent chat in any conversation
has access to them. MCP also has standardized lifecycle and discovery semantics
across vendors, which function-calling APIs lack.
"""

FILES["seed/sample_docs/03_retrieval_augmented_generation.md"] = r"""# Retrieval-Augmented Generation (RAG)

## The basic RAG pattern

RAG augments a language model's prompt with relevant context retrieved from an
external knowledge base. The simplest version: embed the question, retrieve the
top-k most similar chunks from a vector database, concatenate those chunks into
the prompt as "context", and let the LLM generate an answer conditioned on it.

## Chunking strategies

Documents must be split into chunks before embedding because most embedding
models have a maximum token limit (typically 512 or 8192 tokens). Fixed-size
chunking with overlap preserves context across boundaries. Typical values are
512 tokens per chunk with 50 tokens of overlap.

For code or structured documents, semantic chunking (at function boundaries or
section headers) typically outperforms token-based chunking.

## Hybrid retrieval

Semantic search using dense vector embeddings excels at conceptual matching but
sometimes misses exact keyword matches that traditional lexical search would
catch. The solution is hybrid retrieval: run both semantic search and a lexical
search (typically BM25) and combine the results.

The most robust combination strategy is Reciprocal Rank Fusion (RRF), which
combines ranked lists by summing the inverse of each item's rank in each list.
RRF beats linear weighted combinations because it requires no parameter tuning.

## Cross-encoder rerankers

A cross-encoder reranker takes a (query, candidate) pair and produces a single
relevance score by processing both jointly. This is more expensive than vector
similarity (10-100ms per pair) but dramatically improves ranking quality.

The standard production pattern is: retrieve top 20-50 candidates with hybrid
retrieval (cheap), then rerank to top 5 with a cross-encoder (expensive but
high quality). Empirically this lifts retrieval quality by 15-30%.

## RAGAS metrics

The four RAGAS metrics for RAG quality are:
- Faithfulness: does the generated answer follow from the retrieved context?
- Answer Relevance: does the answer address the user's question?
- Context Precision: how many of the retrieved chunks were useful?
- Context Recall: does the context contain all information needed for the
  ground-truth answer?

These metrics are typically computed via LLM-as-judge - a separate, capable LLM
scores each metric for each sample.
"""

FILES["seed/sample_docs/04_agentic_patterns.md"] = r"""# Agentic Patterns in LLM Applications

## What makes a system agentic?

An agentic LLM application is one where the model decides what to do next based
on intermediate results, rather than executing a fixed pipeline. A non-agentic
RAG system retrieves once and generates once. An agentic RAG system retrieves,
inspects results, decides whether they are sufficient, and may retrieve again
with a different query.

The defining characteristic is the loop: the model is given the ability to take
actions (tool calls), observe their outputs, and choose its next action.

## Multi-step query planning

The model receives the user's question, produces an initial query, retrieves
context, then judges whether the context contains the answer. If yes, generate.
If no, produce a reformulated query targeting the missing information.

## The judge-then-act pattern

Effective agentic loops use a separate judge step before the answer step. The
judge sees the question and retrieved context and outputs a structured decision:
`answer`, `search_again`, or `give_up`. Each decision includes a reason. This
separation makes the loop's behavior interpretable and debuggable.

A common failure mode without explicit judging is the model silently returning
empty or weak answers because retrieval was poor. With a judge step, the agent
either retries with a better query or explicitly responds "I don't have enough
information."

## Failing loudly vs failing silently

The single biggest reliability improvement in production agentic systems is
ensuring that failures are loud. When retrieval returns nothing, the agent
should emit a structured event ("retrieval_failed") that can be alerted on, and
return a clear "I don't know" response - not a confidently-incorrect synthesized
answer.

## Citation injection

Production RAG should always cite sources. The recommended pattern is to inject
chunk IDs into the prompt's context block (e.g., `[chunk_id=42]`) and instruct
the model to cite those IDs inline. The response can then be post-processed to
convert chunk IDs into clickable links to source documents.
"""

# ---- examples/run_demo.py ----

FILES["examples/run_demo.py"] = '''"""End-to-end demo runner.

Runs the FULL pipeline:
  1. Ensure schema is applied (assumes Postgres is up via docker compose).
  2. Ingest the seed documents from seed/sample_docs/ into a 'demo' collection.
  3. Run 5 representative queries through the agentic loop.
  4. Run evals on 5 golden samples.
  5. Print + save a summary report to docs/demo_output.txt.

Works WITHOUT API keys via the deterministic mock LLM (LLM_PROVIDER=mock).
With OPENAI_API_KEY or ANTHROPIC_API_KEY set, runs against the real model.

Usage:
    $env:LLM_PROVIDER="mock"
    py examples\\run_demo.py
"""
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_DOCS = ROOT / "seed" / "sample_docs"
GOLDEN_SET = ROOT / "eval" / "golden_set.jsonl"
OUTPUT_FILE = ROOT / "docs" / "demo_output.txt"

sys.path.insert(0, str(ROOT / "src"))

from agentic_rag_mcp.agentic import agentic_query
from agentic_rag_mcp.eval.metrics import EvalSample, evaluate_sample
from agentic_rag_mcp.ingestion import ingest_path
from agentic_rag_mcp.storage import list_collections, record_eval


DEMO_QUERIES = [
    "What is the difference between at-least-once and exactly-once delivery?",
    "Why use a dead-letter queue?",
    "What is Model Context Protocol and what is its default transport?",
    "What is hybrid retrieval and why does it beat vector-only search?",
    "What makes an agentic LLM system different from a non-agentic one?",
]


async def main() -> int:
    provider = os.environ.get("LLM_PROVIDER", "openai")
    print(f"\\n{'=' * 60}")
    print(f"  agentic-rag-mcp - end-to-end demo  (provider={provider})")
    print(f"{'=' * 60}\\n")
    output_lines: list[str] = []

    if not SEED_DOCS.exists():
        print(f"  ERROR: seed docs not found at {SEED_DOCS}", file=sys.stderr)
        return 1

    print(f"[1/4] Ingesting seed documents from {SEED_DOCS.relative_to(ROOT)}...")
    t0 = time.perf_counter()
    result = await ingest_path(str(SEED_DOCS), collection="demo")
    print(f"      documents: {result.document_count}")
    print(f"      chunks:    {result.chunk_count}")
    print(f"      duration:  {result.duration_ms} ms\\n")
    output_lines.append(
        f"INGESTION: {result.document_count} docs -> {result.chunk_count} chunks in {result.duration_ms} ms"
    )

    print("[2/4] Listing collections:")
    cols = await list_collections()
    for c in cols:
        line = f"      {c['name']}: {c['documents']} docs, {c['chunks']} chunks"
        print(line)
        output_lines.append(line)
    print()

    print("[3/4] Running representative agentic queries:")
    latencies: list[float] = []
    steps: list[int] = []
    for i, q in enumerate(DEMO_QUERIES, 1):
        print(f"\\n  Q{i}: {q}")
        t = time.perf_counter()
        try:
            res = await agentic_query(query=q, collection="demo")
        except Exception as e:
            print(f"      ERROR: {e}")
            output_lines.append(f"\\nQ{i}: {q}\\nERROR: {e}")
            continue
        dt = (time.perf_counter() - t) * 1000
        latencies.append(dt)
        steps.append(res.get("steps", 0))
        ans = res.get("answer", "")[:300]
        suffix = "..." if len(res.get("answer", "")) > 300 else ""
        print(f"      A: {ans}{suffix}")
        print(f"      steps={res.get('steps')}  citations={len(res.get('citations', []))}  "
              f"latency={dt:.0f}ms  cost=${res.get('cost_usd', 0):.4f}")
        output_lines.append(f"\\nQ{i}: {q}")
        output_lines.append(f"A:  {res.get('answer', '')[:500]}")
        output_lines.append(
            f"steps={res.get('steps')} latency={dt:.0f}ms cost=${res.get('cost_usd', 0):.4f}"
        )

    print("\\n[4/4] Summary:")
    if latencies:
        print(f"      avg latency:    {statistics.mean(latencies):.0f} ms")
        print(f"      p50 latency:    {statistics.median(latencies):.0f} ms")
        print(f"      avg steps:      {statistics.mean(steps):.1f}")
    print(f"      total wall time: {time.perf_counter() - t0:.1f}s")

    if GOLDEN_SET.exists():
        print("\\n[evals] Running evals on first 5 golden samples:")
        samples_raw = [
            json.loads(line)
            for line in GOLDEN_SET.read_text().splitlines()
            if line.strip()
        ][:5]
        all_metrics: list[dict] = []
        for s in samples_raw:
            out = await agentic_query(query=s["question"], collection="demo")
            sample = EvalSample(
                question=s["question"],
                ground_truth=s["ground_truth"],
                answer=out["answer"],
                contexts=[c.get("text", "") for c in out.get("citations", [])][:5],
            )
            metrics = await evaluate_sample(sample)
            all_metrics.append(metrics)
            print(f"      f={metrics['faithfulness']:.2f}  "
                  f"r={metrics['answer_relevance']:.2f}  "
                  f"cp={metrics['context_precision']:.2f}  "
                  f"cr={metrics['context_recall']:.2f}")
        if all_metrics:
            avg = {k: statistics.mean(m[k] for m in all_metrics) for k in all_metrics[0]}
            print("\\n      AVERAGE")
            print(f"      Faithfulness:      {avg['faithfulness']:.2f}")
            print(f"      Answer Relevance:  {avg['answer_relevance']:.2f}")
            print(f"      Context Precision: {avg['context_precision']:.2f}")
            print(f"      Context Recall:    {avg['context_recall']:.2f}")
            output_lines.append("\\nEVAL AVERAGES (5 golden samples):")
            output_lines.append(f"  Faithfulness:      {avg['faithfulness']:.2f}")
            output_lines.append(f"  Answer Relevance:  {avg['answer_relevance']:.2f}")
            output_lines.append(f"  Context Precision: {avg['context_precision']:.2f}")
            output_lines.append(f"  Context Recall:    {avg['context_recall']:.2f}")
            try:
                await record_eval("demo", {**avg, "samples": len(all_metrics)})
            except Exception as e:
                print(f"      (eval persistence skipped: {e})")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\\n".join(output_lines))
    print(f"\\n  Wrote summary to {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"{'=' * 60}\\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
'''

# ---- src/agentic_rag_mcp/auth.py ----

FILES["src/agentic_rag_mcp/auth.py"] = '''"""Optional API-key middleware for the SSE transport.

Set the `MCP_API_KEY` env var to require clients to send `X-API-Key: <value>` on
every request. If unset, the server runs open (suitable for local dev and stdio).
"""
import os

from fastapi import HTTPException, Request


API_KEY_HEADER = "X-API-Key"


def require_api_key(request: Request) -> None:
    expected = os.environ.get("MCP_API_KEY")
    if not expected:
        return
    provided = request.headers.get(API_KEY_HEADER)
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
'''

# ---- src/agentic_rag_mcp/embeddings.py (overwrite) ----

FILES["src/agentic_rag_mcp/embeddings.py"] = '''"""Embedding service. Uses local sentence-transformers by default; falls back to
a deterministic hash-based embedding when the model is not available so the
pipeline still runs offline."""
import hashlib
import logging
from functools import lru_cache

import numpy as np

from agentic_rag_mcp.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    try:
        from sentence_transformers import SentenceTransformer
        log.info("loading_embedding_model", extra={"model": settings.embedding_model})
        return SentenceTransformer(settings.embedding_model)
    except Exception as e:
        log.warning("embedding_model_load_failed", extra={"error": str(e)})
        return None


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    if model is not None:
        vecs = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return [v.tolist() for v in vecs]
    log.warning("using_hash_embedding_fallback", extra={"count": len(texts)})
    return [_hash_embed(t) for t in texts]


def _hash_embed(text: str) -> list[float]:
    """Content-addressable deterministic embedding using BLAKE2b (stable across runs)."""
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    seed = int.from_bytes(digest, "big") % (2**32)
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(settings.embedding_dim).astype(np.float32)
    v /= np.linalg.norm(v) + 1e-9
    return v.tolist()
'''

# ---- src/agentic_rag_mcp/llm.py (overwrite) ----

FILES["src/agentic_rag_mcp/llm.py"] = '''"""LLM provider abstraction. Supports OpenAI, Anthropic, and a deterministic
mock provider for offline development and CI."""
import json
import logging
import re
from dataclasses import dataclass

from agentic_rag_mcp.config import settings

log = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


_PRICES = {
    "gpt-4o-mini":               {"in": 0.00015, "out": 0.0006},
    "gpt-4o":                    {"in": 0.0025,  "out": 0.01},
    "claude-3-5-sonnet-latest":  {"in": 0.003,   "out": 0.015},
    "claude-3-5-haiku-latest":   {"in": 0.0008,  "out": 0.004},
}


async def call_llm(system: str, user: str, json_mode: bool = False) -> LLMResponse:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        if not settings.openai_api_key:
            log.warning("openai_key_missing_falling_back_to_mock")
            return _mock_response(system, user, json_mode)
        return await _call_openai(system, user, json_mode)
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            log.warning("anthropic_key_missing_falling_back_to_mock")
            return _mock_response(system, user, json_mode)
        return await _call_anthropic(system, user)
    if provider == "mock":
        return _mock_response(system, user, json_mode)
    raise RuntimeError(f"unknown LLM_PROVIDER: {provider}")


async def _call_openai(system: str, user: str, json_mode: bool) -> LLMResponse:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    kwargs: dict = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await client.chat.completions.create(**kwargs)
    usage = resp.usage
    return LLMResponse(
        text=resp.choices[0].message.content or "",
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        cost_usd=_cost(settings.llm_model,
                       usage.prompt_tokens if usage else 0,
                       usage.completion_tokens if usage else 0),
    )


async def _call_anthropic(system: str, user: str) -> LLMResponse:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in resp.content if hasattr(block, "text"))
    return LLMResponse(
        text=text,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        cost_usd=_cost(settings.anthropic_model, resp.usage.input_tokens, resp.usage.output_tokens),
    )


def _mock_response(system: str, user: str, json_mode: bool) -> LLMResponse:
    if json_mode:
        ctx_chars = len(user)
        if "RETRIEVED CONTEXT" in user and ctx_chars > 500:
            payload = {"decision": "answer", "next_query": None, "reason": "sufficient context"}
        else:
            payload = {
                "decision": "search_again",
                "next_query": _extract_topic(user),
                "reason": "context insufficient",
            }
        return LLMResponse(
            text=json.dumps(payload),
            input_tokens=len(user) // 4,
            output_tokens=40,
            cost_usd=0.0,
        )

    question, context = _split_qa_prompt(user)
    answer = _extract_answer(question, context)
    return LLMResponse(
        text=answer,
        input_tokens=len(user) // 4,
        output_tokens=len(answer) // 4,
        cost_usd=0.0,
    )


def _split_qa_prompt(user: str) -> tuple[str, str]:
    parts = re.split(r"\\n*CONTEXT:\\n", user, maxsplit=1)
    if len(parts) != 2:
        return user, ""
    return parts[0].replace("QUESTION:\\n", "").strip(), parts[1].strip()


def _extract_topic(user: str) -> str:
    m = re.search(r"USER QUESTION:\\n(.+?)\\n", user)
    return m.group(1).strip() if m else "expanded query"


def _extract_answer(question: str, context: str) -> str:
    q_terms = {w.lower() for w in re.findall(r"\\w{4,}", question)}
    if not context or not q_terms:
        return "I don't have enough information in the available context to answer that confidently."

    sentences = re.split(r"(?<=[.!?])\\s+", context)
    sentences = [s.strip() for s in sentences if 30 < len(s) < 400]
    if not sentences:
        return "No clear answer in the context."

    def score(s: str) -> int:
        s_terms = {w.lower() for w in re.findall(r"\\w{4,}", s)}
        return len(q_terms & s_terms)

    top = sorted(sentences, key=score, reverse=True)[:3]
    return " ".join(f"{s} [chunk_id={i+1}]" for i, s in enumerate(top))


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    p = _PRICES.get(model)
    if not p:
        return 0.0
    return (in_tok / 1000) * p["in"] + (out_tok / 1000) * p["out"]
'''

# ---- eval/golden_set.jsonl ----

FILES["eval/golden_set.jsonl"] = '''{"question": "What is the difference between at-least-once and exactly-once delivery?", "ground_truth": "At-least-once delivery means messages will be delivered one or more times. Exactly-once delivery means each message is delivered exactly one time. In practice exactly-once is impossible across unreliable channels; the achievable contract is at-least-once combined with idempotency."}
{"question": "Why use a dead-letter queue?", "ground_truth": "A dead-letter queue holds messages that have failed processing beyond a configured retry budget. Without a DLQ a single bad payload can wedge a worker pool indefinitely; with a DLQ the rest of the pipeline continues while bad messages are inspected separately."}
{"question": "What are Redis Streams and why are they better than Lists for work queues?", "ground_truth": "Redis Streams are an append-only log primitive in Redis. They support consumer groups: multiple consumers read from the same stream in parallel, each message delivered to exactly one consumer, with automatic claim of abandoned work. Lists do not have these features."}
{"question": "Why per-channel rate limiting instead of global?", "ground_truth": "Different output channels have different rate limits (SendGrid ~100 req/s, Twilio ~10 req/s). A global limit must be set to the most restrictive channel, starving faster ones. Per-channel limits let each channel run at its max throughput."}
{"question": "What is Model Context Protocol?", "ground_truth": "Model Context Protocol is an open standard published by Anthropic in November 2024 for connecting AI models to tools and data. It defines a JSON-RPC protocol over stdio or SSE. MCP servers expose tools, resources, and prompts."}
{"question": "Why is stdio the right default MCP transport?", "ground_truth": "stdio runs the MCP server as a child process of the client. It requires no network configuration, gives process-level isolation, and works identically across operating systems."}
{"question": "How does MCP compare to OpenAI function calling?", "ground_truth": "OpenAI function calling is per-vendor and per-request. MCP is host-application-level: tools are registered once and every chat has access. MCP has standardized lifecycle and discovery across vendors."}
{"question": "What is hybrid retrieval in RAG?", "ground_truth": "Hybrid retrieval combines semantic vector search with lexical BM25 search. Semantic excels at conceptual matching; BM25 catches exact keyword matches. Reciprocal Rank Fusion is the parameter-free way to combine them."}
{"question": "Why use a cross-encoder reranker?", "ground_truth": "A cross-encoder processes query and candidate jointly to produce a single relevance score. More expensive than vector similarity but much higher quality. Standard pattern is retrieve top 20-50 with hybrid retrieval then rerank to top 5, lifting retrieval quality 15-30 percent."}
{"question": "What are the four RAGAS metrics?", "ground_truth": "Faithfulness, Answer Relevance, Context Precision, Context Recall."}
{"question": "What makes an LLM application agentic?", "ground_truth": "An agentic LLM application is one where the model decides what to do next based on intermediate results rather than executing a fixed pipeline. The defining feature is a loop of tool calls and observations until confident."}
{"question": "What is the judge-then-act pattern?", "ground_truth": "A separate judge step in the agentic loop sees question and context, outputs a structured decision (answer, search_again, give_up) with a reason. Makes loop behavior interpretable, prevents silent failures."}
{"question": "Why should agentic systems fail loudly?", "ground_truth": "When retrieval fails, the system should emit a structured event and return a clear 'I don't know' response rather than synthesizing a confidently-incorrect answer."}
{"question": "How does citation injection work in RAG?", "ground_truth": "Inject chunk IDs into the context block (e.g., [chunk_id=42]) and instruct the model to cite those IDs inline. Post-process to convert chunk IDs into links to source documents."}
{"question": "What chunk size and overlap are typical for RAG?", "ground_truth": "512 tokens per chunk with 50 tokens of overlap. Fixed-size with overlap preserves context across boundaries."}
{"question": "What is the correct shutdown sequence for a production service?", "ground_truth": "Stop accepting new requests, drain in-flight work, close database and queue connections, flush logs and metrics, exit."}
{"question": "What is multi-step query planning?", "ground_truth": "An agentic RAG pattern: the model produces an initial query, retrieves, judges whether context is sufficient, and if not produces a reformulated query targeting missing information."}
{"question": "Why does the description of an MCP tool matter?", "ground_truth": "The LLM uses the description to decide when to call the tool. A vague description produces fewer correct invocations than a specific one."}
{"question": "What is Reciprocal Rank Fusion?", "ground_truth": "A method for combining multiple ranked lists by summing the inverse of each item's rank in each list. Used in hybrid retrieval to combine semantic and BM25 results. Parameter-free."}
{"question": "Why are RAGAS metrics computed via LLM-as-judge?", "ground_truth": "A capable LLM scores each metric per sample. Noisy at the per-sample level but stable in aggregate over 30+ samples."}
'''


# ---- write files ----

def write_all() -> None:
    written = 0
    for rel_path, content in FILES.items():
        path = ROOT / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        # Strip leading newlines so files don't start with a blank line
        path.write_text(content.lstrip("\n"), encoding="utf-8")
        written += 1
        print(f"  wrote: {rel_path}  ({path.stat().st_size} bytes)")
    print(f"\nWrote {written} files. Done.")


if __name__ == "__main__":
    if not (ROOT / "pyproject.toml").exists():
        print(f"ERROR: pyproject.toml not found at {ROOT}", file=sys.stderr)
        print("Run this script from the agentic-rag-mcp project root.", file=sys.stderr)
        sys.exit(1)
    write_all()
