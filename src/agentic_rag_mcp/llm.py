"""LLM provider abstraction. Supports OpenAI, Anthropic, and a deterministic
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
        sys_lower = system.lower()
        is_eval = any(k in sys_lower for k in (
            "score", "faithfulness", "relevance", "precision", "recall",
            "judge", "evaluate"
        ))
        if is_eval:
            q_terms = set(re.findall(r"\w{4,}", user.lower()))
            score = min(0.95, 0.55 + 0.00005 * len(user) + 0.002 * len(q_terms))
            payload = {"score": round(score, 2), "reason": "mock score"}
        elif "RETRIEVED CONTEXT" in user and len(user) > 500:
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
    parts = re.split(r"\n*CONTEXT:\n", user, maxsplit=1)
    if len(parts) != 2:
        return user, ""
    return parts[0].replace("QUESTION:\n", "").strip(), parts[1].strip()


def _extract_topic(user: str) -> str:
    m = re.search(r"USER QUESTION:\n(.+?)\n", user)
    return m.group(1).strip() if m else "expanded query"


def _extract_answer(question: str, context: str) -> str:
    q_terms = {w.lower() for w in re.findall(r"\w{4,}", question)}
    if not context or not q_terms:
        return "I don't have enough information in the available context to answer that confidently."

    sentences = re.split(r"(?<=[.!?])\s+", context)
    sentences = [s.strip() for s in sentences if 30 < len(s) < 400]
    if not sentences:
        return "No clear answer in the context."

    def score(s: str) -> int:
        s_terms = {w.lower() for w in re.findall(r"\w{4,}", s)}
        return len(q_terms & s_terms)

    top = sorted(sentences, key=score, reverse=True)[:3]
    return " ".join(f"{s} [chunk_id={i+1}]" for i, s in enumerate(top))


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    p = _PRICES.get(model)
    if not p:
        return 0.0
    return (in_tok / 1000) * p["in"] + (out_tok / 1000) * p["out"]