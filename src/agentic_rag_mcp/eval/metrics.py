"""RAGAS-style metrics implemented from scratch (no ragas-pkg dependency).

Metrics:
- faithfulness:        does the answer follow from the context?
- answer_relevance:    does the answer address the question?
- context_precision:   how much of the retrieved context is useful?
- context_recall:      how much of the ground-truth answer is covered by the context?
"""
import json
import logging
from dataclasses import dataclass

from agentic_rag_mcp.llm import call_llm

log = logging.getLogger(__name__)


@dataclass
class EvalSample:
    question: str
    ground_truth: str
    answer: str
    contexts: list[str]


FAITHFULNESS_SYS = """You evaluate whether a generated answer is supported by retrieved context.
Output strict JSON: {"score": <0..1>, "reason": "<one sentence>"}.
1.0 = every claim is directly supported by context.
0.0 = answer contradicts or hallucinates beyond context.
"""

RELEVANCE_SYS = """You evaluate whether an answer addresses the user's question.
Output strict JSON: {"score": <0..1>, "reason": "<one sentence>"}.
1.0 = answer directly addresses the question; 0.0 = totally off-topic.
"""

PRECISION_SYS = """You evaluate whether each retrieved chunk was useful for answering the question.
Output strict JSON: {"score": <0..1>, "useful_count": <int>, "total": <int>}.
Score = useful_count / total.
"""

RECALL_SYS = """You evaluate whether the retrieved context contains the information needed to
produce the ground-truth answer. Output strict JSON: {"score": <0..1>, "reason": "..."}.
"""


async def faithfulness(sample: EvalSample) -> float:
    user = f"QUESTION:\n{sample.question}\n\nANSWER:\n{sample.answer}\n\nCONTEXT:\n" + \
           "\n\n".join(sample.contexts)
    return await _judge(FAITHFULNESS_SYS, user)


async def answer_relevance(sample: EvalSample) -> float:
    user = f"QUESTION:\n{sample.question}\n\nANSWER:\n{sample.answer}"
    return await _judge(RELEVANCE_SYS, user)


async def context_precision(sample: EvalSample) -> float:
    user = f"QUESTION:\n{sample.question}\n\nCHUNKS:\n" + \
           "\n---\n".join(f"[{i}] {c}" for i, c in enumerate(sample.contexts))
    return await _judge(PRECISION_SYS, user)


async def context_recall(sample: EvalSample) -> float:
    user = f"QUESTION:\n{sample.question}\n\nGROUND TRUTH:\n{sample.ground_truth}\n\n" + \
           "CONTEXT:\n" + "\n\n".join(sample.contexts)
    return await _judge(RECALL_SYS, user)


async def _judge(system: str, user: str) -> float:
    resp = await call_llm(system=system, user=user, json_mode=True)
    try:
        parsed = json.loads(resp.text)
        return float(parsed.get("score", 0.0))
    except (json.JSONDecodeError, ValueError):
        log.warning("eval_invalid_json", extra={"output": resp.text[:200]})
        return 0.0


async def evaluate_sample(sample: EvalSample) -> dict[str, float]:
    return {
        "faithfulness":      await faithfulness(sample),
        "answer_relevance":  await answer_relevance(sample),
        "context_precision": await context_precision(sample),
        "context_recall":    await context_recall(sample),
    }
