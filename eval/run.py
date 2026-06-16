"""Standalone eval runner. Loads golden_set.jsonl, queries the agent, scores with RAGAS metrics."""
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

from agentic_rag_mcp.agentic import agentic_query
from agentic_rag_mcp.eval.metrics import EvalSample, evaluate_sample
from agentic_rag_mcp.storage import record_eval


GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"


async def main(collection: str = "demo") -> int:
    if not GOLDEN_SET.exists():
        print(f"golden set not found at {GOLDEN_SET}", file=sys.stderr)
        return 1

    samples = [json.loads(line) for line in GOLDEN_SET.read_text().splitlines() if line.strip()]
    print(f"running evals on {len(samples)} samples against collection={collection}")

    started = time.perf_counter()
    all_metrics: list[dict] = []
    latencies: list[float] = []
    costs: list[float] = []

    for i, s in enumerate(samples, 1):
        out = await agentic_query(query=s["question"], collection=collection)
        latencies.append(out.get("latency_ms", 0) / 1000.0)
        costs.append(out.get("cost_usd", 0))

        sample = EvalSample(
            question=s["question"],
            ground_truth=s["ground_truth"],
            answer=out["answer"],
            contexts=[c.get("text", "") for c in out.get("citations", [])][:5],
        )
        metrics = await evaluate_sample(sample)
        all_metrics.append(metrics)
        print(f"  [{i}/{len(samples)}] f={metrics['faithfulness']:.2f}  "
              f"r={metrics['answer_relevance']:.2f}  "
              f"cp={metrics['context_precision']:.2f}  "
              f"cr={metrics['context_recall']:.2f}")

    elapsed = time.perf_counter() - started
    avg = {k: statistics.mean(m[k] for m in all_metrics) for k in all_metrics[0]}

    print("\n" + "=" * 50)
    print(f"Faithfulness............. {avg['faithfulness']:.2f}")
    print(f"Answer Relevance......... {avg['answer_relevance']:.2f}")
    print(f"Context Precision........ {avg['context_precision']:.2f}")
    print(f"Context Recall........... {avg['context_recall']:.2f}")
    print(f"Avg latency (p50)........ {statistics.median(latencies):.2f}s")
    print(f"Avg cost per query....... ${statistics.mean(costs):.4f}")
    print(f"Total eval wall time..... {elapsed:.1f}s")
    print("=" * 50)

    await record_eval(collection, {**avg, "samples": len(samples)})
    return 0


if __name__ == "__main__":
    coll = sys.argv[1] if len(sys.argv) > 1 else "demo"
    sys.exit(asyncio.run(main(coll)))
