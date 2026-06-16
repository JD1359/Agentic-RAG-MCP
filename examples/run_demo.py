"""End-to-end demo runner.

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
    py examples\run_demo.py
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
    print(f"\n{'=' * 60}")
    print(f"  agentic-rag-mcp - end-to-end demo  (provider={provider})")
    print(f"{'=' * 60}\n")
    output_lines: list[str] = []

    if not SEED_DOCS.exists():
        print(f"  ERROR: seed docs not found at {SEED_DOCS}", file=sys.stderr)
        return 1

    print(f"[1/4] Ingesting seed documents from {SEED_DOCS.relative_to(ROOT)}...")
    t0 = time.perf_counter()
    result = await ingest_path(str(SEED_DOCS), collection="demo")
    print(f"      documents: {result.document_count}")
    print(f"      chunks:    {result.chunk_count}")
    print(f"      duration:  {result.duration_ms} ms\n")
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
        print(f"\n  Q{i}: {q}")
        t = time.perf_counter()
        try:
            res = await agentic_query(query=q, collection="demo")
        except Exception as e:
            print(f"      ERROR: {e}")
            output_lines.append(f"\nQ{i}: {q}\nERROR: {e}")
            continue
        dt = (time.perf_counter() - t) * 1000
        latencies.append(dt)
        steps.append(res.get("steps", 0))
        ans = res.get("answer", "")[:300]
        suffix = "..." if len(res.get("answer", "")) > 300 else ""
        print(f"      A: {ans}{suffix}")
        print(f"      steps={res.get('steps')}  citations={len(res.get('citations', []))}  "
              f"latency={dt:.0f}ms  cost=${res.get('cost_usd', 0):.4f}")
        output_lines.append(f"\nQ{i}: {q}")
        output_lines.append(f"A:  {res.get('answer', '')[:500]}")
        output_lines.append(
            f"steps={res.get('steps')} latency={dt:.0f}ms cost=${res.get('cost_usd', 0):.4f}"
        )

    print("\n[4/4] Summary:")
    if latencies:
        print(f"      avg latency:    {statistics.mean(latencies):.0f} ms")
        print(f"      p50 latency:    {statistics.median(latencies):.0f} ms")
        print(f"      avg steps:      {statistics.mean(steps):.1f}")
    print(f"      total wall time: {time.perf_counter() - t0:.1f}s")

    if GOLDEN_SET.exists():
        print("\n[evals] Running evals on first 5 golden samples:")
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
            print("\n      AVERAGE")
            print(f"      Faithfulness:      {avg['faithfulness']:.2f}")
            print(f"      Answer Relevance:  {avg['answer_relevance']:.2f}")
            print(f"      Context Precision: {avg['context_precision']:.2f}")
            print(f"      Context Recall:    {avg['context_recall']:.2f}")
            output_lines.append("\nEVAL AVERAGES (5 golden samples):")
            output_lines.append(f"  Faithfulness:      {avg['faithfulness']:.2f}")
            output_lines.append(f"  Answer Relevance:  {avg['answer_relevance']:.2f}")
            output_lines.append(f"  Context Precision: {avg['context_precision']:.2f}")
            output_lines.append(f"  Context Recall:    {avg['context_recall']:.2f}")
            try:
                await record_eval("demo", {**avg, "samples": len(all_metrics)})
            except Exception as e:
                print(f"      (eval persistence skipped: {e})")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(output_lines))
    print(f"\n  Wrote summary to {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"{'=' * 60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
