# Agentic Patterns in LLM Applications

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
